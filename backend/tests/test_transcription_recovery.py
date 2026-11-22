import uuid,threading
import pytest,numpy as np
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from backend.app import main
from backend.app.core import STORE,save_job,get_job

@pytest.fixture(autouse=True)
def speech_fixture(monkeypatch):
    monkeypatch.setattr(main,'decode_speech_audio',lambda path:np.ones(16,dtype=np.float32))

def fixture_job(**values):
    ident=uuid.uuid4().hex;(STORE/ident).mkdir()
    job=dict(id=ident,status='done',duration=2,ext='.wav',segments=[{'text':'Old words','start':0,'end':1}],translation={'items':[]},transcript_revision=3,result_token=uuid.uuid4().hex)
    job.update(values);save_job(job);return job

def test_retry_has_one_atomic_claim_and_preserves_previous_export(monkeypatch):
    submitted=[]
    monkeypatch.setattr(main,'pool',SimpleNamespace(submit=lambda *args:submitted.append(args)))
    with TestClient(main.app) as client:
        job=fixture_job();start=threading.Barrier(2)
        def call(_):
            start.wait(timeout=5)
            return client.post('/api/jobs',json={'job_id':job['id'],'model':'tiny','language':'en'})
        with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(call,range(2)))
        assert sorted(r.status_code for r in responses)==[200,409]
        assert len(submitted)==1
        saved=get_job(job['id'])
        assert saved['segments']==[] and saved['translation'] is None and saved['result_token'] is None
        assert saved['transcript_revision']==4
        assert saved['previous_results'][0]['token']==job['result_token']

def test_no_recognized_speech_finishes_with_actionable_error(monkeypatch):
    monkeypatch.setitem(main.models,'tiny',SimpleNamespace(transcribe=lambda *args,**kwargs:(iter([]),None)))
    with TestClient(main.app):
        job=fixture_job(status='queued',segments=[],translation=None)
        main.transcribe_job(job['id'],'tiny','en')
        saved=get_job(job['id'])
        assert saved['status']=='failed' and saved['phase']=='Nutq topilmadi'
        assert saved['translation'] is None and saved['segments']==[]
        assert 'nutq' in saved['error']

def test_whitespace_segments_do_not_create_an_empty_avatar_plan(monkeypatch):
    segment=SimpleNamespace(text='  ',start=0,end=1,words=[])
    monkeypatch.setitem(main.models,'tiny',SimpleNamespace(transcribe=lambda *args,**kwargs:(iter([segment]),None)))
    with TestClient(main.app):
        job=fixture_job(status='queued',segments=[],translation=None)
        main.transcribe_job(job['id'],'tiny','en')
        assert get_job(job['id'])['status']=='failed'

def test_same_media_reuses_only_completed_unedited_matching_asr(monkeypatch):
    def must_not_decode(path):
        pytest.fail('Identical media was decoded again')
    monkeypatch.setattr(main,'decode_speech_audio',must_not_decode)
    with TestClient(main.app):
        common=dict(source_sha256='a'*64, transcript_revision=1, language='en', speech_model='small')
        source=fixture_job(status='ready',**common)
        target=fixture_job(status='queued',segments=[],translation=None,**common)
        assert main.reusable_transcript(target,'base','en') is None
        assert main.reusable_transcript(target,'small','uz') is None
        for override in [dict(status='processing'),dict(transcript_revision=2),dict(translation=None)]:
            save_job({**source,**override})
            assert main.reusable_transcript(target,'small','en') is None
        save_job(source)
        main.transcribe_job(target['id'],'small','en')
        result=get_job(target['id'])
        assert result['status']=='ready' and result['segments']==source['segments']

def test_cancel_then_retry_rejects_late_old_worker_writes(monkeypatch):
    started=threading.Event();release=threading.Event();submitted=[]
    segment=SimpleNamespace(text='Obsolete result',start=0,end=1,words=[])
    def delayed():
        started.set();assert release.wait(5)
        yield segment
    monkeypatch.setitem(main.models,'tiny',SimpleNamespace(transcribe=lambda *args,**kwargs:(delayed(),None)))
    monkeypatch.setattr(main,'pool',SimpleNamespace(submit=lambda *args:submitted.append(args)))
    with TestClient(main.app) as client:
        old=uuid.uuid4().hex
        job=fixture_job(status='ready',segments=[],translation=None,transcribe_token=old)
        with ThreadPoolExecutor(max_workers=1) as workers:
            task=workers.submit(main.transcribe_job,job['id'],'tiny','en',old)
            assert started.wait(5)
            assert client.post(f"/api/jobs/{job['id']}/cancel").status_code==200
            response=client.post('/api/jobs',json={'job_id':job['id'],'model':'tiny','language':'en'})
            assert response.status_code==200
            new=response.json()['transcribe_token'];assert new!=old
            release.set();task.result(timeout=5)
        saved=get_job(job['id'])
        assert saved['status']=='queued' and saved['transcribe_token']==new and saved['segments']==[]
        assert len(submitted)==1
