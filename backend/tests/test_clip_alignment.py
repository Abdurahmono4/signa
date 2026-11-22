import csv
import hashlib
import subprocess
import uuid
from zipfile import ZipFile

import av
import pytest
from fastapi.testclient import TestClient

from backend.app import how2sign, realigned_clips
from backend.app.clip_alignment import original_clip_conflicts
from backend.app.core import binary, get_job, save_job
from backend.app.main import app


def timings(base, split, name, text, span, revised):
    for suffix, window, fields in [('', span, ('START', 'END')),
                                   ('realigned_', revised, ('START_REALIGNED', 'END_REALIGNED'))]:
        path = base / f'how2sign_{suffix}{split}.csv'
        with path.open('w', newline='', encoding='utf8') as output:
            writer = csv.DictWriter(output, ['VIDEO_NAME', 'SENTENCE_NAME', 'SENTENCE', *fields], delimiter='\t')
            writer.writeheader()
            writer.writerow({'VIDEO_NAME': 'demo-rgb_front', 'SENTENCE_NAME': name, 'SENTENCE': text,
                             fields[0]: window[0], fields[1]: window[1]})


@pytest.fixture
def disjoint(tmp_path, monkeypatch):
    monkeypatch.setattr(how2sign, 'BASE', tmp_path)
    monkeypatch.setenv('SIGNBRIDGE_RAW_DATA', str(tmp_path))
    name, text = 'demo_1-1-rgb_front', 'Demo phrase'
    ident = hashlib.sha256((name + '.mp4').encode()).hexdigest()[:24]
    timings(tmp_path, 'val', name, text, (0, .5), (1.1, 1.9))
    record = {'id': ident, 'text': text, 'duration': .5, 'video_url': '/original'}
    monkeypatch.setattr(how2sign, 'catalog', lambda: [record])
    return tmp_path, name, record


def test_disjoint_both_splits_original_fallback_and_review(disjoint, monkeypatch):
    base, name, record = disjoint
    assert record['id'] in original_clip_conflicts(base, 'val')
    result = how2sign.translate_asl(record['text'])
    assert result['coverage'] == 0 and all(not i['video_url'] for i in result['items'])
    assert 'vaqt' in result['items'][0]['reason']
    record['verified'] = True
    assert how2sign.translate_asl(record['text'])['items'][0]['video_url'] == '/original'
    monkeypatch.setattr(how2sign, 'catalog', lambda: [])
    timings(base, 'train', name, record['text'], (0, .5), (1.1, 1.9))
    with ZipFile(base / 'train_rgb_front_clips.zip', 'w') as archive:
        archive.writestr(name + '.mp4', b'original-clip-must-never-be-read')
    assert how2sign.translate_asl(record['text'])['coverage'] == 0
    assert not (base / 'train-cache').exists()
    # Merely touching endpoints shares zero frames. A genuinely overlapping interval
    # retains the earlier unreviewed workflow and is not called manually realigned.
    timings(base, 'val', name, record['text'], (0, .5), (.5, .9))
    assert record['id'] in original_clip_conflicts(base, 'val')
    timings(base, 'val', name, record['text'], (0, .5), (.4, .9))
    assert record['id'] not in original_clip_conflicts(base, 'val')


def test_realigned_source_plays_correct_frames_and_inherits_no_review(disjoint, monkeypatch):
    base, _, original = disjoint
    video = base / 'fixture.mp4'
    subprocess.run([binary('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'color=red:s=128x96:r=24:d=1',
                    '-f', 'lavfi', '-i', 'color=blue:s=128x96:r=24:d=1',
                    '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0', '-c:v', 'libx264', str(video)], check=True)
    with ZipFile(base / 'val_raw_videos.zip', 'w') as archive:
        archive.write(video, 'raw_videos/demo-rgb_front.mp4')
    client = TestClient(app)
    item = client.post('/api/translate', json={'text': original['text']}).json()['items'][0]
    assert item['supported'] and not item['verified']
    assert item['sign_id'] != original['id'] and item['timing_source'] == 'manual_realignment'
    actual = how2sign.resolve_clip(item['sign_id'])
    assert client.get(item['video_url']).content == actual.read_bytes()
    assert client.get('/api/how2sign/realigned/clips/unknown').status_code == 404
    assert client.get('/api/how2sign/train/clips/' + item['sign_id']).status_code == 404
    with av.open(str(actual)) as container:
        assert not container.streams.audio
        frames = list(container.decode(video=0))
        for f in frames:
            rgb = f.to_ndarray(format='rgb24').mean(axis=(0, 1))
            assert rgb[2] > 200 and rgb[0] < 20, 'Every realigned frame must be blue'
    assert len(frames) / 24 == pytest.approx(.8, abs=1/24)
    def no_reencode(*args):
        raise AssertionError('A cached aligned clip must not be cut again')
    monkeypatch.setattr(realigned_clips, '_cut', no_reencode)
    short = [{'text': original['text'], 'start': 0, 'end': .3}]
    assert how2sign.translate_asl('', short)['coverage'] == 0
    assert how2sign.translate_asl('', short, .8)['items'][0]['end'] <= .8
    assert how2sign.translate_asl('', short, .8)['coverage'] == 100
    assert how2sign.translate_asl('', [*short, {'text': 'Next', 'start': .32, 'end': 1}], 1)['coverage'] == 0
    ident = uuid.uuid4().hex
    stale = {'items': [{**item, 'sign_id': original['id'], 'video_url': '/original'}]}
    save_job({'id': ident, 'language': 'en', 'status': 'ready', 'duration': .8, 'segments': short, 'translation': stale})
    assert client.get('/api/jobs/' + ident).json()['translation']['items'][0]['sign_id'] == item['sign_id']
    assert get_job(ident)['translation'] == stale
    assert realigned_clips.recover(base, 'test', original_clip_conflicts(base, 'val')[original['id']]) is None


def test_incomplete_or_out_of_range_recording_falls_back(disjoint):
    base, _, record = disjoint
    (base / 'val_raw_videos.zip').write_bytes(b'incomplete')
    assert how2sign.translate_asl(record['text'])['coverage'] == 0
    source = base / 'short.mp4'
    subprocess.run([binary('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'color=blue:s=64x64:r=24:d=1',
                    '-c:v', 'libx264', str(source)], check=True)
    with ZipFile(base / 'val_raw_videos.zip', 'w') as archive:
        archive.write(source, 'raw_videos/demo-rgb_front.mp4')
    assert how2sign.translate_asl(record['text'])['coverage'] == 0
    assert not list((base / 'realigned-cache').glob('*.mp4'))
