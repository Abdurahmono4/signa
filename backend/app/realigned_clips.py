"""Recover a caption's manually timed signer footage from a local full recording."""
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import threading
from fractions import Fraction
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from .core import ROOT, binary, probe

CACHE_LIMIT = 2 * 1024**3
SOURCE_LIMIT = 1024**3
_lock = threading.Lock()


def _archive(base, split):
    roots = [base]
    if configured := os.getenv('SIGNBRIDGE_RAW_DATA'):
        roots.append(Path(configured))
    elif base.resolve() == (ROOT / 'datasets/how2sign').resolve():
        roots.extend((Path.home() / 'Downloads', Path(base.anchor)))
    for root in roots:
        for name in (f'{split}_raw_videos.zip', f'{split}_rgb_front_raw_videos.zip'):
            path = root / name
            if path.is_file() and not any(Path(str(path) + suffix).is_file() for suffix in ('.part', '.crdownload')):
                return path
    return None


def cached(base, ident):
    if not isinstance(ident, str) or not re.fullmatch(r'[a-f0-9]{24}', ident):
        return None
    folder = base / 'realigned-cache'
    try:
        record = json.loads((folder / f'{ident}.json').read_text(encoding='utf-8'))
        file = folder / f'{ident}.mp4'
        if (record['id'] == ident and record['timing_source'] == 'manual_realignment'
                and file.stat().st_size == record['bytes'] > 0):
            return {**record, '_local_path': str(file)}
    except (OSError, KeyError, TypeError, ValueError):
        pass
    return None


def recover(base, split, window):
    if (split not in ('val', 'train') or not window or not re.fullmatch(r'[a-zA-Z0-9_-]+-rgb_front', window.video)
            or not 0 < window.end - window.start <= 300):
        return None
    archive = _archive(base, split)
    if not archive:
        return None
    try:
        with ZipFile(archive) as z:
            info = z.getinfo('raw_videos/' + window.video + '.mp4')
            if info.flag_bits & 1 or not 0 < info.file_size <= SOURCE_LIMIT:
                return None
            fingerprint = [split, window.sentence, window.text, window.start, window.end,
                           info.filename, info.file_size, info.CRC, 'realigned-frontal-v1']
            ident = hashlib.sha256(json.dumps(fingerprint).encode()).hexdigest()[:24]
            if ready := cached(base, ident):
                return ready
            with _lock:
                if ready := cached(base, ident):
                    return ready
                return _cut(base, z, info, ident, window, split)
    except (OSError, BadZipFile, KeyError, ValueError, RuntimeError, subprocess.SubprocessError, ZeroDivisionError):
        # The caller can still choose a different recording or the original subtitle.
        return None


def _cut(base, archive, info, ident, window, split):
    folder = base / 'realigned-cache'
    folder.mkdir(exist_ok=True)
    used = sum(path.stat().st_size for path in folder.glob('*.mp4'))
    if used >= CACHE_LIMIT or shutil.disk_usage(folder).free <= info.file_size + 128 * 1024**2:
        return None
    with tempfile.TemporaryDirectory(dir=folder) as work:
        original = Path(work) / 'source.mp4'
        clip = Path(work) / 'clip.mp4'
        with archive.open(info) as source, original.open('wb') as out:
            shutil.copyfileobj(source, out, 1024**2)
        if original.stat().st_size != info.file_size:
            return None
        source_video = next((s for s in probe(original)['streams'] if s['codec_type'] == 'video'), None)
        if source_video is None:
            return None
        duration = float(source_video['duration'])
        rate = float(Fraction(source_video['avg_frame_rate']))
        if not (math.isfinite(duration) and 0 < rate <= 240 and 0 <= window.start < window.end <= duration):
            return None
        target = window.end - window.start
        subprocess.run([binary('ffmpeg'), '-nostdin', '-v', 'error', '-ss', str(window.start),
                        '-i', str(original), '-t', str(target), '-map', '0:v:0', '-an', '-sn',
                        '-map_metadata', '-1', '-fps_mode', 'passthrough', '-c:v', 'libx264',
                        '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p',
                        '-movflags', '+faststart', str(clip)], check=True, timeout=180,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        streams = probe(clip)['streams']
        size = clip.stat().st_size
        if len(streams) != 1 or streams[0]['codec_name'] != 'h264' or used + size > CACHE_LIMIT:
            return None
        seconds = float(streams[0]['duration'])
        if not math.isfinite(seconds) or seconds <= 0 or abs(seconds - target) > 1 / rate + .01:
            return None
        record = {
            'id': ident, 'split': 'validation' if split == 'val' else split, 'language': 'asl',
            'text': window.text, 'sentence_name': window.sentence, 'duration': seconds, 'bytes': size,
            'technical_valid': True, 'verified': False, 'timing_source': 'manual_realignment',
            'source_start': window.start, 'source_end': window.end, 'source_crc32': f'{info.CRC:08x}',
            'video_url': f'/api/how2sign/realigned/clips/{ident}', 'source': 'https://how2sign.github.io/',
            'license': 'CC-BY-NC-4.0', 'width': streams[0]['width'], 'height': streams[0]['height'],
        }
        manifest = Path(work) / 'clip.json'
        manifest.write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
        os.replace(clip, folder / f'{ident}.mp4')
        os.replace(manifest, folder / f'{ident}.json')
    return {**record, '_local_path': str(folder / f'{ident}.mp4')}
