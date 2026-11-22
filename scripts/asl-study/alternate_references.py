"""Extract all available alternate test recordings of the exact ten source sentences."""
import argparse
import csv
import json
import math
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.core import ROOT, binary, probe


def extract(study, archive):
    with (ROOT/'datasets/how2sign/how2sign_realigned_test.csv').open(encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    samples = json.loads((study.parent/'samples.json').read_text(encoding='utf-8-sig'))
    dest = study/'alternate-human'
    dest.mkdir(parents=True, exist_ok=True)
    records, excluded = [], []
    with zipfile.ZipFile(archive) as z, tempfile.TemporaryDirectory() as scratch:
        raw = Path(scratch)/'raw.mp4'
        for s in samples:
            source = next(r for r in rows if r['SENTENCE_NAME'] == s['sentence_id'])
            if source['SENTENCE'] != s['text'] or abs(float(source['START_REALIGNED'])-s['start']) > .001:
                raise ValueError('Primary reference and realigned CSV differ')
            others = sorted((r for r in rows if r['VIDEO_ID'] == source['VIDEO_ID']
                             and r['SENTENCE_ID'] == source['SENTENCE_ID'] and r['SENTENCE'] == source['SENTENCE']
                             and r['VIDEO_NAME'] != source['VIDEO_NAME']), key=lambda r: r['SENTENCE_NAME'])
            for n, r in enumerate(others, 1):
                member = 'raw_videos/'+r['VIDEO_NAME']+'.mp4'
                take = s['id']+'-'+str(n)
                first, last = float(r['START_REALIGNED']), float(r['END_REALIGNED'])
                if not math.isfinite(last-first) or not (0 <= first < last) or last-first > 60:
                    raise ValueError('Invalid sentence timestamps')
                with z.open(member) as src, raw.open('wb') as dst:
                    shutil.copyfileobj(src, dst, 2**20)
                raw_video = next(t for t in probe(raw)['streams'] if t['codec_type']=='video')
                source_length = float(raw_video['duration'])
                if last > source_length + .05:
                    excluded.append(dict(id=take,target=s['id'],member=member,start=first,end=last,
                                         source_duration=source_length,reason='realigned interval extends past video'))
                    continue
                output = dest/f'{take}.mp4' 
                subprocess.run([binary('ffmpeg'),'-v','error','-y','-ss',str(first),'-i',str(raw),
                                '-t',str(last-first),'-map','0:v:0','-an','-sn','-map_metadata','-1',
                                '-vf','scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,setsar=1',
                                '-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output)], check=True)
                streams = probe(output)['streams']
                if len(streams)!=1 or abs(float(streams[0]['duration'])-(last-first))>.1:
                    raise ValueError('Realigned control clip failed duration validation')
                records.append(dict(id=take,target=s['id'],sentence_name=r['SENTENCE_NAME'],
                                    member=member,start=first,end=last))
    (dest/'manifest.json').write_text(json.dumps(dict(complete=records,excluded=excluded),indent=2),encoding='utf-8')
    print(f'{len(records)} alternate human recordings for {len({r["target"] for r in records})} sentences. Excluded: {excluded}')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study',type=Path)
    parser.add_argument('archive',type=Path)
    args=parser.parse_args();extract(args.study,args.archive)
