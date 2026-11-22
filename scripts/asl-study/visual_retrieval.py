"""Visual reference retrieval; this metric has no model of ASL or English."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

PHASES = 24
MIN_OVERLAP = PHASES // 2
SIDES = ('left', 'right')


def features(frames):
    """Wrists in shoulder widths; finger points in units of typical visible palm size."""
    wrists = np.full((len(frames), 2, 1, 2), np.nan)
    hands = np.full((len(frames), 2, 20, 2), np.nan)
    widths = []
    palm_sizes = [[], []]
    for i, frame in enumerate(frames):
        body = np.array(frame['body'], dtype=float) if frame['body'] is not None else None
        shoulders = body is not None and np.all(body[:2, 2] >= .5)
        if shoulders:
            center = body[:2, :2].mean(axis=0)
            widths.append(np.linalg.norm(body[0, :2] - body[1, :2]))
        for side, name in enumerate(SIDES):
            hand = frame[name]
            if hand is not None:
                p = np.asarray(hand, dtype=float)
                hands[i, side] = p[1:] - p[0]
                palm_sizes[side].append(np.linalg.norm(p[[5, 9, 17]] - p[0], axis=1).mean())
            if shoulders:
                if hand is not None:
                    wrists[i, side, 0] = np.asarray(hand[0]) - center
                elif body[2 + side, 2] >= .5:
                    wrists[i, side, 0] = body[2 + side, :2] - center
    width = np.median(widths) if widths else 0
    wrists = wrists / width if width > 2 else np.full_like(wrists, np.nan)
    for side, sizes in enumerate(palm_sizes):
        size = np.median(sizes) if sizes else 0
        hands[:, side] = hands[:, side] / size if size > 2 else np.nan
    indices = np.rint(np.linspace(0, len(frames) - 1, PHASES)).astype(int)
    return wrists[indices], hands[indices]


def distance(a, b):
    # Equal weight per observable phase. Missing paired hands do not count as agreement.
    d = np.linalg.norm(a - b, axis=-1).mean(axis=-1)
    visible = np.isfinite(d)
    counts = visible.sum(axis=1)
    keep = counts > 0
    if keep.sum() < MIN_OVERLAP:
        return None
    phase = np.nansum(d[keep], axis=1) / counts[keep]
    return float(phase.mean())


def scores(query, refs):
    def both(w, h):
        return (w + h) / 2 if w is not None and h is not None else None
    result = {}
    for ref_id, ref in refs.items():
        w, h = [distance(a, b) for a, b in zip(query, ref)]
        result[ref_id] = dict(wrists=w, fingers=h, combined=both(w, h))
    return result


def evaluate(queries, refs, targets=None):
    if targets is None:
        assert set(queries) == set(refs)
        targets = {k: k for k in queries}
    assert set(queries) == set(targets) and set(targets.values()) <= set(refs)
    details = []
    for query_id, query in queries.items():
        target = targets[query_id]
        matrix_row = scores(query, refs)
        # y grows down in both frontal views. Use matched phase and physical side.
        height_offsets = []
        for side in range(2):
            delta = query[0][:, side, 0, 1] - refs[target][0][:, side, 0, 1]
            valid = delta[np.isfinite(delta)]
            height_offsets.append(float(np.median(valid)) if len(valid) >= MIN_OVERLAP else None)
        row = {'id': query_id, 'target': target, 'distances': matrix_row, 'ranks': {},
               'wrist_y_offset_shoulder_widths_L_R': height_offsets}
        for metric in ('wrists', 'fingers', 'combined'):
            distances = {k: v[metric] for k, v in matrix_row.items()}
            if any(value is None for value in distances.values()):
                row['ranks'][metric] = None
                continue
            # Count ties against the target. Candidate list order cannot improve its rank.
            row['ranks'][metric] = 1 + sum(v <= distances[target] + 1e-10
                                          for k, v in distances.items() if k != target)
        details.append(row)
    summary = {}
    for metric in ('wrists', 'fingers', 'combined'):
        ranks = [r['ranks'][metric] for r in details if r['ranks'][metric] is not None]
        summary[metric] = dict(eligible=len(ranks), total=len(details), top1=ranks.count(1),
                               top3=sum(r <= 3 for r in ranks),
                               median_rank=float(np.median(ranks)) if ranks else None)
    return dict(summary=summary, records=details)


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(study_dir):
    data = json.loads((study_dir/'landmarks.json').read_text())
    samples = json.loads((study_dir.parent/'samples.json').read_text(encoding='utf-8-sig'))
    ids = {s['id'] for s in samples}
    records = {(c['kind'], c['id']): c for c in data['clips']}
    if len(records) != len(data['clips']) or set(records) != {(k, i) for i in ids for k in ('human', 'avatar')}:
        raise ValueError('Incomplete or duplicate stimuli')
    coverage = []
    for (kind, i), c in records.items():
        file = study_dir/'avatar'/f'avatar-{i}.mp4' if kind == 'avatar' else study_dir.parent/'human'/f'{i}.mp4'
        if file_sha(file) != c['sha256']:
            raise ValueError(f'Stimulus changed: {kind} {i}')
        frames = c['frames']
        coverage.append(dict(kind=kind, id=i, frames=len(frames), body=sum(f['body'] is not None for f in frames),
                             **{side: sum(f[side] is not None for f in frames) for side in SIDES}))
    def extract(kind, selection):
        return {s['id']: features(records[kind, s['id']]['frames'][selection]) for s in samples}
    human = extract('human', slice(None))
    avatar = extract('avatar', slice(None))
    cross = evaluate(avatar, human)
    shuffled = evaluate(avatar, dict(reversed(list(human.items()))))
    assert [r['ranks'] for r in shuffled['records']] == [r['ranks'] for r in cross['records']]
    control = evaluate(extract('human', slice(0, None, 2)), extract('human', slice(1, None, 2)))
    report = {'method':'front-view-2d-reference-retrieval-v1', 'phases': PHASES,
              'minimum_visible_phases_per_pair': MIN_OVERLAP, 'candidate_count': len(human),
              'model_sha256':data['model_sha256'], 'detector':data['detector'], 'package':data['package'],
              'coverage':coverage, 'avatar_to_human':cross, 'human_odd_even_control':control,
              'human_comprehension':'unmeasured'}
    alt_file = study_dir/'alternate-landmarks.json'
    if alt_file.exists():
        extra = json.loads(alt_file.read_text())
        manifest = json.loads((study_dir/'alternate-human/manifest.json').read_text())
        targets = {row['id']: row['target'] for row in manifest['complete']}
        if (extra['model_sha256'], extra['package']) != (data['model_sha256'], data['package']):
            raise ValueError('Different detector in cross-recording control')
        queries = {}
        for clip in extra['clips']:
            file = study_dir/'alternate-human'/(clip['id']+'.mp4')
            if file_sha(file) != clip['sha256'] or clip['id'] in queries:
                raise ValueError('Changed or duplicate alternate recording')
            queries[clip['id']] = features(clip['frames'])
        report['alternate_human_control'] = evaluate(queries, human, targets)
        report['excluded_alternates'] = manifest['excluded']
    (study_dir/'visual-test.json').write_text(json.dumps(report, indent=2, allow_nan=False),encoding='utf-8')
    print(json.dumps({k: report[k]['summary'] for k in ('avatar_to_human','human_odd_even_control','alternate_human_control') if k in report}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('study', type=Path)
    run(p.parse_args().study)
