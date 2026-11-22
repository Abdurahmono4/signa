"""Find original-time sentence clips that cannot support their revised caption interval."""
import csv
import hashlib
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _windows(path, start, end):
    windows = {}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream, delimiter='\t'):
            name = row.get('SENTENCE_NAME')
            if not name:
                continue
            # A duplicated ID has no unique interval even if a later row seems valid.
            if name in windows:
                windows[name] = None
                continue
            try:
                a, b = float(row[start]), float(row[end])
                span = (row['VIDEO_NAME'], row['SENTENCE'], a, b)
                windows[name] = span if math.isfinite(b) and 0 <= a < b else None
            except (KeyError, TypeError, ValueError):
                windows[name] = None
    return windows


@dataclass(frozen=True)
class CorrectedWindow:
    sentence: str
    video: str
    text: str
    start: float
    end: float


@lru_cache(maxsize=6)
def _comparison(original, revised, original_stat, revised_stat):
    first = _windows(original, 'START', 'END')
    second = _windows(revised, 'START_REALIGNED', 'END_REALIGNED')
    conflicts = {}
    for name in first.keys() & second.keys():
        a, b = first[name], second[name]
        if a is None or b is None or a[:2] != b[:2]:
            correction = None
        elif min(a[3], b[3]) <= max(a[2], b[2]):
            correction = CorrectedWindow(name, b[0], b[1], b[2], b[3])
        else:
            continue
        ident = hashlib.sha256((name + '.mp4').encode()).hexdigest()[:24]
        conflicts[ident] = correction
    return conflicts


def original_clip_conflicts(base: Path, split: str):
    original = base / f'how2sign_{split}.csv'
    revised = base / f'how2sign_realigned_{split}.csv'
    try:
        orig_stat, rev_stat = original.stat(), revised.stat()
    except FileNotFoundError:
        # Older catalogs can operate without the optional realignment metadata.
        return {}
    return _comparison(original, revised, (orig_stat.st_size, orig_stat.st_mtime_ns),
                       (rev_stat.st_size, rev_stat.st_mtime_ns))
