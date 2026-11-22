"""Prepare the distributor's original-time sentence clips as a second visual control."""
import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.core import binary, probe


def prepare(study):
    base = ROOT / 'datasets' / 'how2sign'
    samples = json.loads((study / 'samples.json').read_text(encoding='utf-8-sig'))
    destination = study / 'published'
    destination.mkdir(parents=True, exist_ok=True)
    manifest = []
    with (base / 'how2sign_test.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = {r['SENTENCE_NAME']: r for r in csv.DictReader(f, delimiter='\t')}
    with ZipFile(base / 'test_rgb_front_clips.zip') as archive, tempfile.TemporaryDirectory() as scratch:
        for sample in samples:
            name = sample['sentence_id']
            row = rows[name]
            if row['SENTENCE'] != sample['text'] or '/' in name or '\\' in name:
                raise ValueError(f'Inconsistent source: {name}')
            member = 'raw_videos/' + name + '.mp4'
            original = Path(scratch) / 'source.mp4'
            output = destination / (sample['id'] + '.mp4')
            with archive.open(member) as source, original.open('wb') as out:
                shutil.copyfileobj(source, out)
            subprocess.run([binary('ffmpeg'), '-v', 'error', '-y', '-i', str(original),
                            '-map', '0:v:0', '-an', '-sn', '-map_metadata', '-1',
                            '-vf', 'scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,setsar=1',
                            '-fps_mode', 'passthrough', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
                            '-movflags', '+faststart', str(output)], check=True)
            before = next(s for s in probe(original)['streams'] if s['codec_type'] == 'video')
            after = probe(output)['streams']
            if (len(after) != 1 or before['nb_frames'] != after[0]['nb_frames']
                    or abs(float(before['duration']) - float(after[0]['duration'])) > .05):
                raise ValueError(f'Published clip was retimed: {name}')
            first, last = float(row['START']), float(row['END'])
            overlap = max(0, min(last, sample['end']) - max(first, sample['start']))
            manifest.append(dict(id=sample['id'], sentence_name=name, member=member,
                                 original=[first, last], realigned=[sample['start'], sample['end']],
                                 overlap_seconds=round(overlap, 3), duration=float(after[0]['duration']),
                                 frames=int(after[0]['nb_frames']), fps=after[0]['avg_frame_rate']))
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'{len(manifest)} published clips; {sum(r["overlap_seconds"] == 0 for r in manifest)} disjoint ranges.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path)
    prepare(parser.parse_args().study)
