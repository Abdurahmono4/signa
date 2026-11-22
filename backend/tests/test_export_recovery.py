import uuid,threading
import asyncio
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from backend.app.core import STORE,save_job,get_job
from backend.app.main import app

def test_two_tabs_cannot_claim_same_ready_export(monkeypatch):
    from backend.app import main
    with TestClient(app) as client:
        id=uuid.uuid4().hex;(STORE/id).mkdir()
        save_job({'id':id,'status':'ready','language':'en','duration':1,'segments':[],'translation':{'items':[]}})
        original=main.job_of;barrier=threading.Barrier(2);seen=threading.local()
        def snapshot(ident):
            job=original(ident)
            if ident==id and not getattr(seen,'read',False):
                seen.read=True;barrier.wait(timeout=5)
            return job
        monkeypatch.setattr(main,'job_of',snapshot)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _:client.post(f'/api/jobs/{id}/render/start',json={}),range(2)))
        assert sorted(r.status_code for r in responses)==[200,409]
        winner=next(r.json() for r in responses if r.status_code==200)
        assert get_job(id)['render_token']==winner['token']
        assert len([p for p in (STORE/id).iterdir() if p.is_dir()])==1

def test_restart_marks_orphan_frames_failed_but_preserves_files():
    from backend.app.core import initialize
    initialize();id=uuid.uuid4().hex;token=uuid.uuid4().hex
    folder=STORE/id/token;folder.mkdir(parents=True);(folder/'000000.png').write_bytes(b'partial fixture')
    save_job({'id':id,'status':'frames','render_token':token,'segments':[]})
    with TestClient(app):
        assert get_job(id)['status']=='failed'
        assert (folder/'000000.png').exists()

def test_old_cancel_and_finish_do_not_change_new_session():
    with TestClient(app) as client:
        id=uuid.uuid4().hex;old=uuid.uuid4().hex;new=uuid.uuid4().hex
        (STORE/id/new).mkdir(parents=True)
        save_job({'id':id,'status':'frames','render_token':new,'frame_count':0,'segments':[]})
        for endpoint in ['cancel','render/finish']:
            response=client.post(f'/api/jobs/{id}/{endpoint}',json={'token':old})
            assert response.status_code==409
            assert get_job(id)['status']=='frames' and get_job(id)['render_token']==new
        assert client.post(f'/api/jobs/{id}/cancel',json={'token':new}).status_code==200

def test_finish_claims_a_session_only_once(monkeypatch):
    from backend.app import main
    submissions=[];monkeypatch.setattr(main,'pool',SimpleNamespace(submit=lambda *args:submissions.append(args)))
    with TestClient(app) as client:
        id=uuid.uuid4().hex;token=uuid.uuid4().hex;(STORE/id/token).mkdir(parents=True)
        save_job({'id':id,'status':'frames','render_token':token,'frame_count':0,'segments':[]})
        start=threading.Barrier(2)
        def finish(_):
            start.wait(5);return client.post(f'/api/jobs/{id}/render/finish',json={'token':token})
        with ThreadPoolExecutor(max_workers=2) as workers:responses=list(workers.map(finish,range(2)))
        assert sorted(r.status_code for r in responses)==[200,409]
        assert len(submissions)==1 and submissions[0][2]==token

def test_stale_workers_leave_new_job_untouched():
    from backend.app import main
    with TestClient(app):
        id=uuid.uuid4().hex;old=uuid.uuid4().hex;new=uuid.uuid4().hex
        save_job({'id':id,'status':'frames','render_token':new,'segments':[]})
        main.render_job(id,old);main.render_human_job(id,old)
        assert get_job(id)['status']=='frames' and get_job(id)['render_token']==new


def test_resume_after_restart_reuses_only_valid_prefix_and_revokes_old_writer():
    from backend.app.main import RenderSettings
    from scripts.smoke_pipeline import png
    ident,token=uuid.uuid4().hex,uuid.uuid4().hex
    folder=STORE/ident/token;folder.mkdir(parents=True)
    frame=png();(folder/'000000.png').write_bytes(frame)
    (folder/'000001.png').write_bytes(frame[:-12])
    (folder/'000002.png').write_bytes(frame)
    from backend.app.core import initialize
    initialize();settings=RenderSettings().model_dump()
    save_job({'id':ident,'status':'frames','render_token':token,'settings':settings,
              'frame_count':3,'render_fps':12,'segments':[]})
    with TestClient(app) as client:
        url=f'/api/jobs/{ident}';body={**settings,'token':token}
        assert get_job(ident)['resume_frames']
        assert client.post(url+'/render/resume',json={**body,'resolution':1080}).status_code==409
        response=client.post(url+'/render/resume',json=body)
        assert response.status_code==200
        resumed=response.json();current=resumed['token']
        assert current!=token and resumed['next_frame']==1
        assert (STORE/ident/current/'000000.png').read_bytes()==frame
        assert client.put(f'{url}/frames/{token}/1',content=frame).status_code==409
        assert client.post(url+'/cancel',json={'token':token}).status_code==409
        assert client.put(f'{url}/frames/{current}/1',content=frame).status_code==200
        assert client.post(url+'/cancel',json={'token':current}).status_code==200
        assert client.post(url+'/render/resume',json={**body,'token':current}).status_code==409

def test_frame_upload_rechecks_session_after_body_arrives():
    from backend.app import main
    from fastapi import HTTPException
    from scripts.smoke_pipeline import png
    with TestClient(app):
        id=uuid.uuid4().hex;(STORE/id).mkdir()
        save_job({'id':id,'status':'ready','duration':1,'segments':[],'translation':{'items':[]}})
        old=main.render_start(id,main.RenderSettings())['token']
        async def scenario():
            arrived=asyncio.Event();release=asyncio.Event()
            async def body():
                arrived.set();await release.wait();yield png()
            upload=asyncio.create_task(main.frame(id,old,0,SimpleNamespace(stream=body)))
            await arrived.wait()
            main.cancel(id,main.RenderSessionRequest(token=old))
            new=main.render_start(id,main.RenderSettings())['token'];release.set()
            try:await upload
            except HTTPException as exc:assert exc.status_code==409
            else:raise AssertionError('Stale frame upload accepted')
            assert get_job(id)['render_token']==new
            assert not (STORE/id/old/'000000.png').exists()
        asyncio.run(scenario())

def test_png_header_without_valid_image_is_rejected_before_write():
    from scripts.smoke_pipeline import png
    with TestClient(app) as client:
        id=uuid.uuid4().hex;(STORE/id).mkdir()
        save_job({'id':id,'status':'ready','duration':1,'segments':[],'translation':{'items':[]}})
        session=client.post(f'/api/jobs/{id}/render/start',json={}).json()
        token=session['token'];broken=png()[:24]
        assert client.put(f'/api/jobs/{id}/frames/{token}/0',content=broken).status_code==422
        assert not (STORE/id/token/'000000.png').exists()
        assert client.put(f'/api/jobs/{id}/frames/{token}/0',content=png()).status_code==200


def test_late_cancel_without_token_cannot_hide_completed_output():
    from backend.app import main
    with TestClient(app) as client:
        ident,token=uuid.uuid4().hex,uuid.uuid4().hex
        folder=STORE/ident/token;folder.mkdir(parents=True)
        (folder/'result.mp4').write_bytes(b'completed export fixture')
        original={'id':ident,'status':'done','segments':[], 'render_token':token,'result_token':token}
        save_job(original)
        assert client.post(f'/api/jobs/{ident}/cancel',json={}).status_code==409
        assert get_job(ident)==original
        assert ident not in main.cancelled
        assert client.get(f'/api/jobs/{ident}/download').content==b'completed export fixture'


def test_retry_export_clears_previous_failure_without_losing_completed_version():
    with TestClient(app) as client:
        ident,previous=uuid.uuid4().hex,uuid.uuid4().hex
        folder=STORE/ident/previous;folder.mkdir(parents=True)
        (folder/'result.mp4').write_bytes(b'previous result')
        save_job({'id':ident,'status':'failed','duration':1,'segments':[],
                  'translation':{'items':[]},'error':'Old cancelled export',
                  'result_token':previous})
        response=client.post(f'/api/jobs/{ident}/render/start',json={})
        assert response.status_code==200
        assert get_job(ident)['status']=='frames' and get_job(ident)['error'] is None
        assert client.get(f'/api/jobs/{ident}/download?v={previous}').content==b'previous result'
