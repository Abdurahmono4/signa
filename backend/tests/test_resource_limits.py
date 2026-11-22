import uuid,threading,json
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from backend.app import main,neural_api,neural_engine,render_resources
from backend.app.core import STORE,save_job,get_job
from backend.app.neural_limits import limits,check_chunks

def test_limit_boundary_and_engine_rejects_before_worker_start(tmp_path,monkeypatch):
    assert limits()=={'max_chunks':75,'max_frames':30000}
    check_chunks(75)
    segments=[{'text':f'Synthetic fixture {i}.','start':i,'end':i+1} for i in range(76)]
    row={'id':uuid.uuid4().hex,'revision':1,'duration':76,'segments':json.dumps(segments)}
    monkeypatch.setattr(neural_engine.threading,'Thread',lambda *args,**kwargs:pytest.fail('Worker started above budget'))
    with pytest.raises(ValueError,match='75'):neural_engine.enqueue(tmp_path,tmp_path,row,threading.Lock(),lambda:None)

def test_render_disk_budget_rejects_without_session_or_status_change(monkeypatch):
    monkeypatch.setattr(render_resources.shutil,'disk_usage',lambda path:SimpleNamespace(free=1))
    with TestClient(main.app) as client:
        ident=uuid.uuid4().hex;(STORE/ident).mkdir()
        job={'id':ident,'status':'ready','translation':{'items':[]},'language':'en','duration':1,'segments':[],'translation':{'items':[]}}
        save_job(job)
        r=client.post(f'/api/jobs/{ident}/render/start',json={})
        assert r.status_code==507 and 'disk' in r.json()['detail']
        assert get_job(ident)==job and not list((STORE/ident).iterdir())

def test_disk_estimate_includes_png_encoded_video_and_free_margin(monkeypatch,tmp_path):
    needed=render_resources.required_render_bytes(24,1)
    assert needed==(24+2+512)*1024**2
    monkeypatch.setattr(render_resources.shutil,'disk_usage',lambda path:SimpleNamespace(free=needed))
    assert render_resources.ensure_render_space(tmp_path,24,1)==needed
    monkeypatch.setattr(render_resources.shutil,'disk_usage',lambda path:SimpleNamespace(free=needed-1))
    with pytest.raises(ValueError):render_resources.ensure_render_space(tmp_path,24,1)
    assert render_resources.required_render_bytes(0,1)<needed

def test_api_does_not_enqueue_too_many_compatible_chunks(monkeypatch):
    with TestClient(main.app) as client:
        ident=uuid.uuid4().hex
        save_job({'id':ident,'status':'ready','translation':{'items':[]},'language':'en','duration':100,'segments':[{'text':'Synthetic.','start':0,'end':1}]})
        monkeypatch.setattr(neural_api.engine,'readiness',lambda root:{'ready':True})
        monkeypatch.setattr(neural_api.neural_preflight,'inspect',lambda *args:{'checked_chunks':76,'unsupported_chunks':[]})
        monkeypatch.setattr(neural_api.engine,'enqueue',lambda *args,**kwargs:pytest.fail('Enqueued over budget'))
        assert client.post(f'/api/jobs/{ident}/neural',json={}).status_code==422
