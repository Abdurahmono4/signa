"""Pacing and human review tests; fixtures are not linguistic data."""
import json,time,subprocess
import pytest
import test_pipeline
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import how2sign,neural_api
from backend.app.core import STORE,db,save_job,get_job,binary,probe
from backend.app.timing import motion_time_scale,tempo_filters

def test_test_storage_is_not_live_project_data():
    from backend.app.core import ROOT,ASSETS
    assert STORE.resolve()!=(ROOT/'storage').resolve()
    assert ASSETS.resolve()!=(ROOT/'assets').resolve()
    assert how2sign.BASE.resolve()!=(ROOT/'datasets'/'how2sign').resolve()

def test_motion_speed_bound_and_audio_tempo_chain():
    items=[{'supported':True,'start':0,'end':2,'duration_ms':7500}]
    scale=motion_time_scale(items)
    assert scale==3
    assert 7.5/(2*scale)==1.25
    assert tempo_filters(3)=='atempo=0.5,atempo=0.6666666667'
    with pytest.raises(ValueError):motion_time_scale([{'supported':True,'start':0,'end':1,'duration_ms':10000}])

def test_review_persistence_audit_and_rejected_exclusion(tmp_path,monkeypatch):
    id='1234567890abcdef12345678'
    (tmp_path/'catalog.json').write_text(json.dumps([{'id':id,'text':'Synthetic fixture only','duration':2,'video_url':'/fixture','verified':False}]))
    monkeypatch.setattr(how2sign,'BASE',tmp_path)
    with TestClient(app) as client:
        assert not how2sign.catalog()[0]['verified']
        data={'decision':'approved','reviewer':'Automated fixture','notes':'Technical automated fixture, not ASL verification.'}
        assert client.post(f'/api/how2sign/clips/{id}/review',json=data).status_code==200
        assert how2sign.catalog()[0]['verified']
        data['decision']='rejected'
        assert client.post(f'/api/how2sign/clips/{id}/review',json=data).status_code==200
        assert how2sign.translate_asl('Synthetic fixture only')['coverage']==0
        with db() as c:assert c.execute('SELECT count(*) FROM corpus_review_history WHERE id=?',(id,)).fetchone()[0]==2
        data['reviewer']='   '
        assert client.post(f'/api/how2sign/clips/{id}/review',json=data).status_code==422

@pytest.mark.parametrize('avatar_model,expected_fps,dimensions,quality',[('legacy',12,(384,512),'standard'),('rocketbox',24,(512,384),'standard'),('rocketbox',24,(1024,768),'high')])
def test_paced_export_has_real_extended_video_and_audio(monkeypatch,avatar_model,expected_fps,dimensions,quality):
    from scripts.smoke_pipeline import png
    import av,numpy as np
    fixture=STORE/'paced-tone.wav'
    subprocess.run([binary('ffmpeg'),'-y','-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','1',str(fixture)],check=True)
    monkeypatch.setattr(neural_api,'plan',lambda id:{'timing_scale':2})
    with TestClient(app) as client:
        with fixture.open('rb') as f:r=client.post('/api/upload',files={'file':('paced-tone.wav',f)})
        job=r.json();id=job['id'];job.update(status='ready',segments=[],translation={'items':[]});save_job(job)
        session=client.post(f'/api/jobs/{id}/render/start',json={'engine':'neural','avatar_model':avatar_model,'subtitles':False,'capture_quality':quality}).json()
        assert session['frames']==expected_fps*2 and session['fps']==expected_fps
        assert get_job(id)['render_fps']==expected_fps
        for i in range(session['frames']):assert client.put(f"/api/jobs/{id}/frames/{session['token']}/{i}",content=png(*dimensions)).status_code==200
        assert client.post(f'/api/jobs/{id}/render/finish').status_code==200
        deadline=time.monotonic()+30
        while get_job(id)['status'] not in ['done','failed'] and time.monotonic()<deadline:time.sleep(.1)
        assert get_job(id)['status']=='done'
        output=STORE/'paced-result.mp4';output.write_bytes(client.get(f'/api/jobs/{id}/download').content)
        assert abs(float(probe(output)['format']['duration'])-2)<.1
        with av.open(str(output)) as container:
            rate=container.streams.audio[0].rate
            samples=np.concatenate([f.to_ndarray().flatten() for f in container.decode(audio=0)])
            peak=np.argmax(abs(np.fft.rfft(samples)))*rate/len(samples)
            assert abs(peak-440)<4,'Pacing must preserve test audio pitch'
        with av.open(str(output)) as container:
            frame=next(container.decode(video=0)).to_ndarray(format='rgb24')
            assert (frame[10:60,10:430].mean(axis=2)>180).sum()>80,'Research label stays visible at the top even with subtitles off'
            assert (frame[600:710].mean(axis=2)>180).sum()<50,'Research label must not consume the subtitle area'

def test_stale_rejected_clip_blocks_export_until_replan(monkeypatch):
    import uuid
    id=uuid.uuid4().hex;(STORE/id).mkdir()
    (STORE/id/'input.wav').write_bytes(b'isolated history fixture')
    save_job({'id':id,'name':'fixture.wav','kind':'audio','duration':2,'language':'en','status':'ready',
              'segments':[{'text':'Rejected fixture','start':0,'end':2}],
              'translation':{'items':[{'sign_id':'rejected-fixture','supported':True}]},'ext':'.wav'})
    monkeypatch.setattr(how2sign,'catalog',lambda:[{'id':'rejected-fixture','text':'Rejected fixture','duration':2,'video_url':'/fixture','review_decision':'rejected'}])
    with TestClient(app) as client:
        assert client.post(f'/api/jobs/{id}/render/start',json={}).status_code==409
        r=client.post(f'/api/jobs/{id}/replan')
        assert r.status_code==200 and r.json()['translation']['coverage']==0
        history=client.get('/api/jobs').json()
        summary=next(j for j in history if j['id']==id)
        assert 'ext' not in summary and 'segments' not in summary
        report=client.get(f'/api/jobs/{id}/report').json()
        assert report['translation']['coverage']==0 and report['notice']
