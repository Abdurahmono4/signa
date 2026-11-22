"""Read-only motion diagnostics. No linguistic accuracy score is inferred."""
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
import numpy as np


def assess(data):
    rows = np.asarray(data.get('features', data.get('frames')), dtype=float)
    if rows.ndim != 2 or rows.shape[1] != 133 or not np.isfinite(rows).all():
        raise ValueError('Expected finite 133-feature motion')
    result = {'frames': len(rows), 'fps': data['fps'], 'text': data.get('text'),
              'sha256': hashlib.sha256(rows.tobytes()).hexdigest()}
    for label, start, end in [('arms', 12, 30), ('left_hand', 30, 75), ('right_hand', 75, 120)]:
        values = rows[:, start:end]
        still = np.max(np.abs(np.diff(values, axis=0)), axis=1) < 1e-6
        run = longest = 0
        for same in still:
            run = run + 1 if same else 0
            longest = max(longest, run)
        result[label] = {'mean_temporal_std_rad': float(values.std(axis=0).mean()),
                         'unchanged_intervals': int(still.sum()),
                         'longest_static_seconds': longest / data['fps']}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job_id')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if len(args.job_id) != 32 or any(c not in '0123456789abcdef' for c in args.job_id):
        parser.error('Invalid job identifier')
    base = 'http://127.0.0.1:8001'
    def get(path):
        with urllib.request.urlopen(base + path, timeout=30) as response:
            return json.load(response)
    plan = get('/api/jobs/' + args.job_id + '/neural/plan')
    motions = []
    for item in plan['items']:
        path = item.get('neural_asset')
        if not path:
            continue
        if not path.startswith('/api/') or '..' in path or '\\' in path:
            raise ValueError('Unsafe motion path')
        result = assess(get(path))
        result['speech_slot_seconds'] = item['end'] - item['start']
        result['native_seconds'] = result['frames'] / result['fps']
        motions.append(result)
    report = {'job_id': args.job_id, 'linguistically_verified': False,
              'note': 'Static holds can be meaningful signs. Different arrays do not prove different meanings. No automatic rejection.',
              'exact_duplicate_clips': len(motions) - len({m['sha256'] for m in motions}),
              'motions': motions}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
    print(json.dumps({'clips': len(motions), 'exact_duplicates': report['exact_duplicate_clips'], 'report': str(args.output)}))


if __name__ == '__main__':
    main()
