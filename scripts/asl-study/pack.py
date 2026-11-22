"""Build an offline participant form and a separate organizer-only answer key."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.core import probe


def build(study):
    samples = json.loads((study.parent/'samples.json').read_text(encoding='utf-8-sig'))
    forms = {'A': [], 'B': []}
    media, answers = {}, {}
    for i, s in enumerate(samples):
        motion = json.loads((study.parent/'model'/f'{i:04d}'/'motion.json').read_text())
        if (s['text'], s['id']) != (motion['text'], motion['id']):
            raise ValueError('Manifest does not match model input')
        for kind in ('avatar', 'human'):
            path = study/'avatar'/f"avatar-{s['id']}.mp4" if kind=='avatar' else study.parent/'human'/f"{s['id']}.mp4"
            info = probe(path)
            streams = info['streams']
            if len(streams)!=1 or streams[0]['codec_type']!='video' or streams[0]['codec_name']!='h264':
                raise ValueError(f'Expected one silent H.264 stream: {path.name}')
            if kind=='avatar' and int(streams[0]['nb_frames'])!=motion['frame_count']:
                raise ValueError('Incomplete avatar')
            tags = json.dumps([streams[0].get('tags',{}),info['format'].get('tags',{})]).casefold()
            if any(s['text'].strip('.?!').casefold() in tags for s in samples):
                raise ValueError('Source caption exposed in media metadata')
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            code = digest[:16]
            if code in media:
                raise ValueError('Duplicate blinded stimulus')
            media[code] = base64.b64encode(raw).decode('ascii')
            answers[code] = dict(kind=kind, sample=s['id'], text=s['text'], sha256=digest)
            form = 'A' if (i%2==0)==(kind=='avatar') else 'B'
            forms[form].append(code)
    signature = hashlib.sha256(json.dumps(answers,sort_keys=True).encode()).hexdigest()[:12]
    protocol = 'signbridge-asl-v9-10-'+signature
    bundle = dict(protocol=protocol, forms=forms, media=media)
    template = Path(__file__).with_name('study-template.html').read_text(encoding='utf-8-sig')
    if template.count('__STUDY_DATA__')!=1:
        raise ValueError('Participant template marker missing or repeated')
    page = template.replace('__STUDY_DATA__',json.dumps(bundle,separators=(',',':')))
    if any(s['text'].strip('.?!').casefold() in page.casefold() for s in samples):
        raise ValueError('Answer text leaked into participant form')
    (study/'ASL-sinov.html').write_text(page, encoding='utf-8')
    (study/'organizer-key.json').write_text(json.dumps(dict(protocol=protocol,forms=forms,items=answers),indent=2),encoding='utf-8')
    print(protocol,len(samples),'sentences; balanced forms:',[len(f) for f in forms.values()])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('study',type=Path);build(p.parse_args().study)
