"""Actual FFmpeg export with synthetic frames: never an avatar visual test."""
import time,subprocess
from fastapi.testclient import TestClient
from backend.app import main,neural_api
from backend.app.core import STORE,binary,save_job,get_job,probe
from scripts.smoke_pipeline import png

def test_partial_export_preserves_full_transcript_and_labels_unsupported_time(tmp_path,monkeypatch):
    plan={'timing_scale':1,'generated_phrases':1,'unsupported_phrases':1,'caption_words':2,'total_words':4,
          'items':[{'text':'Unsupported phrase','start':.5,'end':1.5,'unsupported':True}]}
    monkeypatch.setattr(neural_api,'plan',lambda id:plan)
    source=tmp_path/'tone.wav'
    subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','2',str(source)],check=True)
    with TestClient(main.app) as client:
        with source.open('rb') as f:job=client.post('/api/upload',files={'file':(source.name,f)}).json()
        job.update(status='ready',name='Synthetic partial export fixture',language='en',segments=[{'start':0,'end':2,'text':'Original complete transcript remains.'}],translation={'items':[]})
        save_job(job);ident=job['id']
        r=client.post(f'/api/jobs/{ident}/render/start',json={'engine':'neural','avatar_model':'rocketbox','subtitles':True});assert r.status_code==200
        session=r.json();token=session['token']
        for n in range(session['frames']):assert client.put(f'/api/jobs/{ident}/frames/{token}/{n}',content=png(512,384)).status_code==200
        assert client.post(f'/api/jobs/{ident}/render/finish',json={'token':token}).status_code==200
        deadline=time.monotonic()+20
        while get_job(ident)['status'] not in ['done','failed'] and time.monotonic()<deadline:time.sleep(.1)
        saved=get_job(ident);assert saved['status']=='done'
        assert saved['segments']==job['segments'] and saved['neural_summary']['partial'] is True
        captions=(STORE/ident/token/'captions.srt').read_text(encoding='utf-8')
        assert 'Original complete transcript remains.' in captions
        assert '00:00:00,500 --> 00:00:01,500' in captions and 'Avatar ijrosi yo‘q' in captions
        output=tmp_path/'result.mp4';output.write_bytes(client.get(f'/api/jobs/{ident}/download?v={token}').content)
        info=probe(output);assert abs(float(info['format']['duration'])-2)<.1
        assert {s['codec_name'] for s in info['streams']}=={'h264','aac'}
        assert client.get(f'/api/jobs/{ident}/report').json()['neural_summary']['unsupported_phrases']==1
