import test_pipeline
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.mark.parametrize('status',['failed','cancelled','ready','done'])
def test_saved_transcript_can_prepare_motion_after_export_interruption(monkeypatch,status):
    from backend.app import neural_api
    job={'status':status,'language':'en','segments':[{'start':0,'end':1,'text':'Test.'}],'duration':1,'translation':{}}
    monkeypatch.setattr(neural_api,'row_for',lambda ident:{'id':ident})
    monkeypatch.setattr(neural_api,'get_job',lambda ident:job)
    monkeypatch.setattr(neural_api.engine,'readiness',lambda root:{'ready':True})
    monkeypatch.setattr(neural_api.neural_preflight,'inspect',lambda *args:{'checked_chunks':1,'unsupported_chunks':[]})
    monkeypatch.setattr(neural_api.engine,'enqueue',lambda *args,**kwargs:{'status':'queued'})
    assert neural_api.generate('fixture')['status']=='queued'

@pytest.mark.parametrize('status',['processing','frames','rendering','queued'])
def test_motion_does_not_start_during_active_media_operation(monkeypatch,status):
    from backend.app import neural_api
    from fastapi import HTTPException
    monkeypatch.setattr(neural_api,'row_for',lambda ident:{'id':ident})
    monkeypatch.setattr(neural_api,'get_job',lambda ident:{'status':status,'language':'en','segments':[{'text':'Test.'}]})
    with pytest.raises(HTTPException) as error:neural_api.generate('fixture')
    assert error.value.status_code==409

def test_neural_routes_validate_jobs_and_report_readiness():
    with TestClient(app) as client:
        r=client.get('/api/neural/health')
        assert r.status_code==200 and r.json()['device']=='cpu'
        assert client.post('/api/jobs/not-an-id/neural').status_code==404
        assert client.get('/api/jobs/not-an-id/neural/motions/0?key=bad').status_code==404

def test_model_plan_keeps_generated_distinct_from_verified(monkeypatch,tmp_path):
    import json
    from backend.app import neural_api
    monkeypatch.setattr(neural_api,'row_for',lambda id:{'id':id})
    monkeypatch.setattr(neural_api.engine,'folder',lambda store,row:tmp_path)
    (tmp_path/'plan.json').write_text(json.dumps({'items':[{'text':'Synthetic fixture','start':0,'end':2,'clip':{'id':'fixture','duration':2,'neural_asset':'/api/fixture'}}],'total_words':2,'playable_signs':1}))
    result=neural_api.plan('fixture')
    assert result['kind']=='model_generated' and result['coverage']==0
    assert result['items'][0]['generated'] and not result['items'][0]['verified']

def test_partial_plan_marks_caption_interval_and_keeps_original_clock(monkeypatch,tmp_path):
    import json
    from backend.app import neural_api
    monkeypatch.setattr(neural_api,'row_for',lambda id:{'id':id,'duration':4})
    monkeypatch.setattr(neural_api.engine,'folder',lambda store,row:tmp_path)
    (tmp_path/'plan.json').write_text(json.dumps({'items':[
        {'text':'Supported fixture','start':0,'end':1,'clip':{'id':'fixture','duration':1,'neural_asset':'/api/fixture'}},
        {'text':'Untranslated fixture','start':1,'end':3,'clip':None,'status':'unsupported'},
        {'text':'','start':3,'end':4,'clip':None,'status':'gap'}],
        'total_words':4,'playable_signs':1,'unsupported_phrases':1,'caption_words':2}))
    result=neural_api.plan('fixture')
    assert result['unsupported_phrases']==1 and result['caption_words']==2
    assert result['coverage']==0 and result['output_duration']==4
    assert result['items'][1]['unsupported'] and not result['items'][1]['generated']
    assert result['items'][1]['text']=='Untranslated fixture' and result['items'][1]['start']==1
    assert not result['items'][2]['unsupported']
