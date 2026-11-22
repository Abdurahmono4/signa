import json,os,sys,tempfile,uuid
import subprocess,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
os.environ.setdefault('SIGNBRIDGE_STORAGE',tempfile.mkdtemp(prefix='signbridge-tests-'))
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core import STORE,save_job
from backend.app.translation import normalize,translate

def test_real_mp4_subtitles_and_audio_content():
    """Isolated synthetic render fixture; not ASR or avatar visual validation."""
    from backend.app.core import binary,probe,get_job
    from scripts.smoke_pipeline import png
    import av
    import numpy as np
    fixture=STORE/'tone.wav'
    subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','2',str(fixture)],check=True)
    with TestClient(app) as client:
        with fixture.open('rb') as f:r=client.post('/api/upload',files={'file':('tone.wav',f)})
        assert r.status_code==201
        job=r.json();id=job['id']
        job.update(status='ready',segments=[{'start':0,'end':2,'text':"O‘zbekcha subtitr — texnik sinov"}],translation={'items':[],'coverage':0})
        save_job(job)
        session=client.post(f'/api/jobs/{id}/render/start',json={'subtitles':True}).json()
        for n in range(session['frames']):
            assert client.put(f"/api/jobs/{id}/frames/{session['token']}/{n}",content=png()).status_code==200
        assert client.post(f'/api/jobs/{id}/render/finish').status_code==200
        deadline=time.monotonic()+30
        while get_job(id)['status'] not in ['done','failed'] and time.monotonic()<deadline:time.sleep(.1)
        assert get_job(id)['status']=='done'
        result=client.get(f'/api/jobs/{id}/download');assert result.status_code==200
        path=STORE/'tone-result.mp4';path.write_bytes(result.content)
        info=probe(path);assert {s['codec_name'] for s in info['streams']}=={'aac','h264'}
        assert abs(float(info['format']['duration'])-2)<.1
        with av.open(str(path)) as container:
            stream=container.streams.audio[0];rate=stream.rate
            samples=np.concatenate([frame.to_ndarray().flatten() for frame in container.decode(audio=0)])
            peak=np.argmax(abs(np.fft.rfft(samples)))*rate/len(samples)
            assert abs(peak-440)<3,'Original test audio frequency must remain present'
        with av.open(str(path)) as container:
            frame=next(container.decode(video=0)).to_ndarray(format='rgb24')
            assert (frame[600:710].mean(axis=2)>180).sum()>100,'Subtitle should be visibly burned in'

def test_uzbek_normalization():
    assert normalize(' OʻZBEKCHA, g‘alaba! ')=="o'zbekcha g'alaba"

def test_no_asl_or_unverified_substitution():
    base={'id':'test','label':'sinov iborasi','language':'uz_sign','verified':False,'animation_path':'test.json','duration_ms':2000}
    assert translate('Sinov iborasi!',None,[base])['coverage']==0
    assert translate('Sinov iborasi!',None,[{**base,'verified':True,'language':'asl'}])['coverage']==0
    result=translate('Sinov iborasi!',None,[{**base,'verified':True}])
    assert result['coverage']==100
    assert translate('Sinov iborasi boshqa',None,[{**base,'verified':True}])['coverage']==0

def test_api_text_and_paths():
    with TestClient(app) as client:
        assert client.get('/api/health').status_code==200
        r=client.post('/api/translate',json={'text':'Assalomu alaykum.'})
        assert r.status_code==200 and r.json()['coverage']==0
        assert client.get('/api/jobs/not-an-id').status_code==404
        assert client.post('/api/upload',files={'file':('bad.exe',b'bad')}).status_code==415
        assert client.post('/api/upload',files={'file':('bad.wav',b'bad')}).status_code==422

def test_unsafe_sign_speed_is_not_translated():
    sign={'id':'fixture','label':'sinov','language':'uz_sign','verified':True,'animation_path':'fixture.json','duration_ms':5000}
    result=translate('sinov',[{'text':'sinov','start':0,'end':.2}],[sign])
    assert result['coverage']==0
    assert 'tezligi' in result['items'][0]['reason']

def test_import_never_approves_and_rejects_invalid_tracks():
    metadata={'label':'Synthetic fixture','gloss':'TEST','language':'demo','source':'Automated test only','license':'Test-only'}
    with TestClient(app) as client:
        raw={'duration':1,'tracks':[{'name':'private.position','type':'vector','times':[0],'values':[0,0,0]}]}
        assert client.post('/api/signs/import',data={'metadata':json.dumps(metadata)},files={'animation':('test.json',json.dumps(raw))}).status_code==422
        raw['tracks'][0]['name']='root.position'
        r=client.post('/api/signs/import',data={'metadata':json.dumps(metadata)},files={'animation':('test.json',json.dumps(raw))})
        assert r.status_code==201 and not r.json()['verified']

def test_render_rejects_missing_frames_and_bad_png():
    with TestClient(app) as client:
        id=uuid.uuid4().hex;(STORE/id).mkdir()
        save_job({'id':id,'duration':1,'status':'ready','segments':[],'translation':{'items':[]}})
        r=client.post(f'/api/jobs/{id}/render/start',json={});assert r.status_code==200
        token=r.json()['token']
        assert client.put(f'/api/jobs/{id}/frames/{token}/0',content=b'not png').status_code==422
        assert client.post(f'/api/jobs/{id}/render/finish').status_code==409
        assert client.post(f'/api/jobs/{id}/cancel').json()['status']=='cancelled'
