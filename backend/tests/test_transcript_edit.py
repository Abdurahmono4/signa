import json,uuid
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core import STORE,save_job,get_job
from backend.app.neural_engine import key_for

def fixture_job(status='done'):
    id=uuid.uuid4().hex;folder=STORE/id;folder.mkdir()
    (folder/'input.wav').write_bytes(b'original media fixture')
    token=uuid.uuid4().hex;(folder/token).mkdir();(folder/token/'result.mp4').write_bytes(b'previous export fixture')
    job={'id':id,'status':status,'language':'en','duration':2,'ext':'.wav','kind':'audio','name':'fixture.wav',
         'segments':[{'text':'Hello wrong','start':0,'end':2,'words':[{'word':'wrong','start':1,'end':2}]}],
         'result_token':token,'translation':{'coverage':0,'items':[]}}
    save_job(job);return job,folder,token

def motion_key(job):
    return key_for({'id':job['id'],'revision':1,'segments':json.dumps(job['segments'])})

def test_edit_preserves_originals_replans_and_invalidates_motion(monkeypatch):
    from backend.app import how2sign
    monkeypatch.setattr(how2sign,'catalog',lambda:[{'id':'hello','text':'Hello there','duration':2,'video_url':'/fixture'}])
    with TestClient(app) as client:
        job,folder,token=fixture_job();old_key=motion_key(job)
        r=client.put(f"/api/jobs/{job['id']}/transcript",json={'segments':[{'text':'Hello there','start':0,'end':2}]})
        assert r.status_code==200
        new=r.json();assert new['translation']['coverage']==100 and new['status']=='ready'
        assert 'words' not in new['segments'][0] and motion_key(new)!=old_key
        assert new['result_token'] is None and new['previous_results'][0]['token']==token
        assert (folder/'input.wav').read_bytes()==b'original media fixture'
        assert (folder/token/'result.mp4').read_bytes()==b'previous export fixture'
        assert client.get(f"/api/jobs/{job['id']}/download").status_code==409
        assert client.get(f"/api/jobs/{job['id']}/download?v={token}").content==b'previous export fixture'
        assert client.put(f"/api/jobs/{job['id']}/transcript",json={'segments':new['segments']}).json()['transcript_revision']==1

def test_edit_rejects_changed_timestamps_blank_text_and_active_export():
    with TestClient(app) as client:
        job,_,_=fixture_job('ready');url=f"/api/jobs/{job['id']}/transcript"
        for segment in [{'text':'Changed','start':.5,'end':2},{'text':'  ','start':0,'end':2}]:
            assert client.put(url,json={'segments':[segment]}).status_code==422
            assert get_job(job['id'])['segments']==job['segments']
        job['status']='frames';save_job(job)
        assert client.put(url,json={'segments':[{'text':'Changed','start':0,'end':2}]}).status_code==409
        assert client.post('/api/jobs',json={'job_id':job['id'],'language':'en'}).status_code==409

def test_stale_editor_cannot_overwrite_newer_transcript():
    with TestClient(app) as client:
        job,_,_=fixture_job('ready');url=f"/api/jobs/{job['id']}/transcript"
        def edit(text,revision):return client.put(url,json={'expected_revision':revision,'segments':[{'text':text,'start':0,'end':2}]})
        assert edit('First correction',0).status_code==200
        assert edit('Stale correction',0).status_code==409
        assert get_job(job['id'])['segments'][0]['text']=='First correction'
        assert edit('Second correction',1).status_code==200

def test_transcript_download_uses_current_text_original_clock_and_safe_attachment():
    with TestClient(app) as client:
        job,_,_=fixture_job('ready');id=job['id'];job['timing_scale']=2
        job['segments']=[{'text':'First\n\nline → test','start':0,'end':.9996},{'text':'Second line','start':1,'end':3}]
        save_job(job)
        response=client.get(f'/api/jobs/{id}/transcript/download?format=srt')
        assert response.status_code==200
        text=response.content.decode('utf-8-sig')
        assert '00:00:00,000 --> 00:00:01,000\nFirst line → test' in text
        assert '00:00:01,000 --> 00:00:02,000\nSecond line' in text
        assert 'attachment;' in response.headers['content-disposition']
        assert response.headers['cache-control']=='no-store'
        job['segments'][0]['text']='Corrected text';job['transcript_revision']=3;save_job(job)
        response=client.get(f'/api/jobs/{id}/transcript/download?format=txt')
        assert response.headers['x-transcript-revision']=='3' and 'Corrected text' in response.content.decode('utf-8-sig')
        assert client.get(f'/api/jobs/{id}/transcript/download?format=exe').status_code==422
        job['status']='processing';save_job(job)
        assert client.get(f'/api/jobs/{id}/transcript/download?format=txt').status_code==409
