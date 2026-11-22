"""Compare text-generated and recording-token motion on the same avatar and real video."""
import argparse
import json
from pathlib import Path
from statistics import median

from visual_retrieval import evaluate, features, file_sha


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def load_clips(study, kinds, ids, filename='landmarks.json'):
    data = read(study / filename)
    clips = {}
    for clip in data['clips']:
        kind, ident = clip['kind'], clip['id']
        key = (kind, ident)
        if kind not in kinds or ident not in ids or key in clips:
            raise ValueError(f'Unexpected clip {key}')
        if kind == 'human':
            path = study.parent / 'human' / f'{ident}.mp4'
        elif kind == 'published':
            path = study / 'published' / f'{ident}.mp4'
        else:
            path = study / 'avatar' / f'avatar-{ident}.mp4'
        if file_sha(path) != clip['sha256']:
            raise ValueError(f'Video changed since landmark extraction: {key}')
        clips[key] = clip
    if set(clips) != {(kind, ident) for kind in kinds for ident in ids}:
        raise ValueError('Missing comparison clips')
    return data, clips


def compare(original, reconstructed):
    samples = read(original.parent / 'samples.json')
    if samples != read(reconstructed / 'samples.json'):
        raise ValueError('Recording identities or realignment changed')
    ids = [sample['id'] for sample in samples]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate sample')
    baseline, clips = load_clips(original, ('human', 'avatar'), ids)
    rebuilt, more = load_clips(reconstructed, ('reference',), ids)
    published, released = load_clips(reconstructed, ('published',), ids, 'published-landmarks.json')
    intervals = read(reconstructed / 'published' / 'manifest.json')
    if ([r['id'] for r in intervals] != ids
            or any(r['sentence_name'] != s['sentence_id'] for r, s in zip(intervals, samples))):
        raise ValueError('Published and realigned material must use the same recording identifiers')
    detector = {key: baseline[key] for key in ('package', 'detector', 'model_sha256')}
    if any(d[k] != v for d in (rebuilt, published) for k, v in detector.items()):
        raise ValueError('Landmark models or settings differ')
    clips.update(more)
    clips.update(released)
    embeddings = {kind: {i: features(clips[kind, i]['frames']) for i in ids}
                  for kind in ('human', 'avatar', 'reference', 'published')}
    runs = {kind: evaluate(embeddings[kind], embeddings['human']) for kind in ('avatar', 'reference')}
    original_time = {kind: evaluate(embeddings[kind], embeddings['published']) for kind in runs}
    decoder = read(reconstructed / 'decoder-check.json')
    if ([r['id'] for r in decoder] != ids
            or any(r['recording'] != s['sentence_id'] for r, s in zip(decoder, samples))):
        raise ValueError('Decoder control corpus differs')
    paired = []
    for index, sample in enumerate(samples):
        ident = sample['id']
        result = dict(id=ident, recording=sample['sentence_id'], text=sample['text'])
        for kind in runs:
            row = runs[kind]['records'][index]
            clip = clips[kind, ident]
            if row['target'] != ident or row['id'] != ident:
                raise ValueError('Mismatched scoring target')
            frames = clip['frames']
            expected = decoder[index]['reference_frames' if kind == 'reference' else 'generated_frames']
            if len(frames) != expected:
                raise ValueError(f'Decoder and rendered frame counts differ for {kind} {ident}')
            result[kind] = {
                'distance_to_source': row['distances'][ident], 'rank': row['ranks'],
                'wrist_offset_y_L_R': row['wrist_y_offset_shoulder_widths_L_R'],
                'frames': len(frames), 'fps': clip['fps'],
                'detected_L_R': [sum(f[side] is not None for f in frames) for side in ('left', 'right')],
                'video_sha256': clip['sha256'],
                'distance_to_published_clip': original_time[kind]['records'][index]['distances'][ident],
                'published_rank': original_time[kind]['records'][index]['ranks'],
            }
        result['human_sha256'] = clips['human', ident]['sha256']
        result['published_sha256'] = clips['published', ident]['sha256']
        result['timing'] = intervals[index]
        paired.append(result)
    measures = {}
    for metric in ('wrists', 'fingers', 'combined'):
        pairs = [(p['avatar']['distance_to_source'][metric], p['reference']['distance_to_source'][metric])
                 for p in paired]
        valid = [(a, b) for a, b in pairs if a is not None and b is not None]
        measures[metric] = {
            'eligible': len(valid), 'reference_closer': sum(b < a - 1e-10 for a, b in valid),
            'text_closer': sum(a < b - 1e-10 for a, b in valid),
            'median_text_distance': median(a for a, b in valid) if valid else None,
            'median_reference_distance': median(b for a, b in valid) if valid else None,
            'median_paired_reduction': median(a - b for a, b in valid) if valid else None,
        }
    output = {
        'method': 'same-rig-recording-token-control-v1', 'split': 'test', **detector,
        'candidate_count': len(samples), 'paired': measures,
        'rank_summary': {k: v['summary'] for k, v in runs.items()}, 'records': paired,
        'published_rank_summary': {k: v['summary'] for k, v in original_time.items()},
        'linguistic_comprehension': 'unmeasured',
    }
    (reconstructed / 'comparison.json').write_text(json.dumps(output, indent=2, allow_nan=False),
                                                  encoding='utf-8')
    print(json.dumps({'paired': measures, 'ranks': output['rank_summary']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('reconstructed', type=Path)
    args = parser.parse_args()
    compare(args.original, args.reconstructed)
