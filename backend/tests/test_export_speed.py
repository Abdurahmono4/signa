import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app import main
from backend.app.core import STORE, save_job
from backend.tests.test_frame_validation import png

def test_repeated_frames_are_bounded_and_retryable():
    with TestClient(main.app) as client:
        ident, token = uuid.uuid4().hex, uuid.uuid4().hex
        directory = STORE / ident / token
        directory.mkdir(parents=True)
        save_job(dict(id=ident, status='frames', render_token=token, frame_count=50, settings={}))
        url = f'/api/jobs/{ident}/frames/{token}/0'
        raw = png()
        for _ in range(2):
            assert client.put(url + '?repeat=48', content=raw).status_code == 200
        assert len(list(directory.glob('*.png'))) == 48
        assert all(p.read_bytes() == raw for p in directory.glob('*.png'))
        for index, repeat in [(0, 0), (0, 49), (49, 2)]:
            assert client.put(f'/api/jobs/{ident}/frames/{token}/{index}?repeat={repeat}', content=raw).status_code == 422
        assert client.put(url.replace(token, uuid.uuid4().hex), content=raw).status_code == 409

def test_export_cache_requires_same_content_model_revision_and_existing_result():
    with TestClient(main.app):
        ident, token = uuid.uuid4().hex, uuid.uuid4().hex
        directory = STORE / ident / token
        directory.mkdir(parents=True)
        (directory / 'result.mp4').write_bytes(b'test fixture')
        (STORE / ident / 'input.mp4').write_bytes(b'test input')
        job = dict(id=ident, result_token=token, status='done', source_sha256='test-digest',
                   language='en', speech_model='small', ext='.mp4', kind='video',
                   transcript_revision=1, probe={'validation':'streams-v1'},
                   settings=dict(resolution=1080, subtitles=True, layout='side_by_side',
                                 close_panel=True, size=.30, appearance='navy-v1', engine='neural', motion_revision='rest-transition-v10', capture_quality='high'))
        save_job(job)
        assert main.reusable_export('test-digest', '.mp4', 'small')['id'] == ident
        job['settings']['motion_revision'] = 'jaw-retarget-v6'
        save_job(job)
        assert main.reusable_export('test-digest', '.mp4', 'small') is None
        job['settings']['motion_revision'] = 'rest-transition-v10'
        save_job(job)
        assert main.reusable_export('different', '.mp4', 'small') is None
        assert main.reusable_export('test-digest', '.mp4', 'base') is None
        job['probe'] = {}
        save_job(job)
        assert main.reusable_export('test-digest', '.mp4', 'small') is None
        job['probe'] = {'validation':'streams-v1'}
        job['transcript_revision'] = 2
        save_job(job)
        assert main.reusable_export('test-digest', '.mp4', 'small') is None
        job['transcript_revision'] = 1
        save_job(job)
        (directory / 'result.mp4').unlink()
        assert main.reusable_export('test-digest', '.mp4', 'small') is None
