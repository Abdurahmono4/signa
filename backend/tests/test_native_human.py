"""Native composition tests use coloured fixtures, never claimed to be signs."""
import json,time,subprocess
import pytest
import av,numpy as np
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app import how2sign
from backend.app.core import STORE,binary,save_job,get_job,probe

@pytest.mark.parametrize('remove_green',[False,True])
@pytest.mark.parametrize('kind',['audio','video'])
def test_native_clip_timing_audio_and_no_browser_frames(tmp_path,monkeypatch,remove_green,kind):
    ident='abcd'*6
    subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=red:s=384x512:r=24','-t','0.5',str(tmp_path/f'{ident}.mp4')],check=True)
    record={'id':ident,'text':'synthetic test','duration':.5,'video_url':f'/api/how2sign/clips/{ident}'}
    (tmp_path/'catalog.json').write_text(json.dumps([record]))
    monkeypatch.setattr(how2sign,'BASE',tmp_path);monkeypatch.setattr(how2sign,'CLIPS',tmp_path)
    audio=tmp_path/'tone.wav'
    subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','2',str(audio)],check=True)
    source=audio
    if kind=='video':
        source=tmp_path/'source.mp4'
        subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=blue:s=640x360:r=24','-i',str(audio),'-shortest','-c:v','libx264','-c:a','aac',str(source)],check=True)
    with TestClient(app) as c:
        with source.open('rb') as f:job=c.post('/api/upload',files={'file':(source.name,f)}).json()
        job.update(status='ready',language='en',segments=[],translation={'items':[{'supported':True,'video_url':record['video_url'],'sign_id':ident,'start':.5,'end':1,'duration_ms':500}]})
        save_job(job);id=job['id']
        r=c.post(f'/api/jobs/{id}/render/start',json={'native_human':True,'removeGreen':remove_green,'subtitles':False})
        assert r.status_code==200 and r.json()['mode']=='native' and r.json()['frames']==0
        deadline=time.monotonic()+25
        while get_job(id)['status'] not in ['done','failed'] and time.monotonic()<deadline:time.sleep(.1)
        assert get_job(id)['status']=='done'
        output=tmp_path/'native.mp4';output.write_bytes(c.get(f'/api/jobs/{id}/download').content)
        info=probe(output);assert abs(float(info['format']['duration'])-2)<.1
        with av.open(str(output)) as container:
            frames=list(container.decode(video=0));assert len(frames)==48
            left,right=(530,750) if kind=='audio' else (950,1200)
            samples=[frames[n].to_ndarray(format='rgb24')[220:400,left:right].mean(axis=(0,1)) for n in [3,18,36]]
            assert samples[0][0]<30 and samples[1][0]>180 and samples[2][0]<30,'Signer must appear only in its speech interval, centered for audio and on the right for video'
        with av.open(str(output)) as container:
            rate=container.streams.audio[0].rate
            samples=np.concatenate([f.to_ndarray().flatten() for f in container.decode(audio=0)])
            peak=np.argmax(abs(np.fft.rfft(samples)))*rate/len(samples)
            assert abs(peak-440)<3
