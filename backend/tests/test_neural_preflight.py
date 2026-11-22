import io,pickle,uuid
import pytest
from backend.app.neural_preflight import check_segments,DataOnly

def test_checks_every_chunk_without_dropping_unsupported_words():
    segments=[{'id':'0','text':'Hello','start':0,'end':1},{'id':'1','text':'Unknown phrase','start':1,'end':2}]
    result=check_segments(segments,lambda text:text.split(),{'hello.'})
    assert result['compatible'] is False and result['checked_chunks']==2
    assert result['unsupported_chunks']==[{'segment_index':1,'chunk_id':'1','start':1,'end':2}]
    assert segments[0]['text']=='Hello' and segments[1]['text']=='Unknown phrase'

def test_mapping_rejects_python_object_construction():
    assert DataOnly(io.BytesIO(pickle.dumps({12:0,15:1}))).load()=={12:0,15:1}
    with pytest.raises(ValueError):DataOnly(io.BytesIO(pickle.dumps(Exception('unsafe')))).load()

def test_incompatible_input_is_rejected_before_enqueue(monkeypatch):
    from backend.app import neural_api
    from backend.app.core import save_job
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as client:
        ident=uuid.uuid4().hex
        save_job({'id':ident,'status':'ready','translation':{'items':[]},'language':'en','duration':2,'segments':[{'text':'Fixture','start':0,'end':1}]})
        monkeypatch.setattr(neural_api.engine,'readiness',lambda root:{'ready':True})
        monkeypatch.setattr(neural_api.neural_preflight,'inspect',lambda *args:{'compatible':False,'checked_chunks':1,'unsupported_chunks':[{'chunk_id':'0'}]})
        def forbidden(*args):raise AssertionError('No model worker should be enqueued')
        monkeypatch.setattr(neural_api.engine,'enqueue',forbidden)
        response=client.post(f'/api/jobs/{ident}/neural',json={})
        assert response.status_code==422

def test_partial_input_passes_unsupported_ids_without_rewriting_transcript(monkeypatch):
    from backend.app import neural_api
    from backend.app.core import save_job,get_job
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as client:
        ident=uuid.uuid4().hex;segments=[{'text':'Good.','start':0,'end':1},{'text':'Unknown.','start':1,'end':2}]
        save_job({'id':ident,'status':'ready','translation':{'items':[]},'language':'en','duration':2,'segments':segments})
        monkeypatch.setattr(neural_api.engine,'readiness',lambda root:{'ready':True})
        unsupported=[{'chunk_id':'1'}]
        monkeypatch.setattr(neural_api.neural_preflight,'inspect',lambda *args:{'compatible':False,'checked_chunks':2,'unsupported_chunks':unsupported})
        calls=[]
        def enqueue(*args,**kwargs):calls.append(kwargs);return {'status':'queued','unsupported_phrases':1}
        monkeypatch.setattr(neural_api.engine,'enqueue',enqueue)
        response=client.post(f'/api/jobs/{ident}/neural',json={})
        assert response.status_code==200 and response.json()['unsupported_phrases']==1
        assert calls==[{'unsupported_chunks':unsupported}]
        assert get_job(ident)['segments']==segments
