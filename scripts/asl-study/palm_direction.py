"""Compare paired 2D hand landmarks before and after aligning the visible palm axis."""
import argparse
import json
from pathlib import Path

import numpy as np

from visual_retrieval import MIN_OVERLAP, SIDES, features


def align_palm(hand):
    # Wrist-relative points omit the wrist; index 8 is the middle finger MCP.
    x, y = hand[8]
    length = np.hypot(x, y)
    if not np.isfinite(length) or length < 0.1:
        return None
    return hand @ (np.array([[x, -y], [y, x]]) / length)


def compare(avatar, human):
    rows = []
    for a, h in zip(avatar, human):
        aligned_a, aligned_h = align_palm(a), align_palm(h)
        if aligned_a is None or aligned_h is None:
            continue
        rows.append([np.linalg.norm(a-h, axis=1).mean(),
                     np.linalg.norm(aligned_a-aligned_h, axis=1).mean()])
    result = {'paired_phases': len(rows)}
    if len(rows) >= MIN_OVERLAP:
        raw, aligned = np.mean(rows, axis=0)
        result.update(raw=round(float(raw), 3), aligned=round(float(aligned), 3))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('landmarks', type=Path)
    args = parser.parse_args()
    clips = json.loads(args.landmarks.read_text())['clips']
    hands = {(c['id'], c['kind']): features(c['frames'])[1] for c in clips}
    for clip_id, kind in hands:
        if kind == 'avatar':
            print(json.dumps({'id': clip_id, **{
                name: compare(hands[clip_id, kind][:, side], hands[clip_id, 'human'][:, side])
                for side, name in enumerate(SIDES)}}))
