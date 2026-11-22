"""Pixel checks use a plain red fixture, never a sign-language animation."""
import subprocess,time
import av,pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core import binary,save_job,get_job

@pytest.mark.parametrize('kind,layout',[('audio','side_by_side'),('audio','overlay'),('video','side_by_side')])
def test_png_export_audio_center_and_video_side_panel(tmp_path,kind,layout):
    wav=tmp_path/'tone.wav';image=tmp_path/'red.png'
    subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','1',str(wav)],check=True)
    subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=red:s=384x512','-frames:v','1',str(image)],check=True)
    source=wav
    if kind=='video':
        source=tmp_path/'video.mp4'
        subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=blue:s=640x360:r=24','-i',str(wav),'-shortest','-c:v','libx264','-c:a','aac',str(source)],check=True)
    with TestClient(app) as client:
        with source.open('rb') as f:response=client.post('/api/upload',files={'file':(source.name,f)})
        assert response.status_code==201
        job=response.json();job.update(status='ready',segments=[],translation={'items':[]});save_job(job)
        id=job['id'];session=client.post(f'/api/jobs/{id}/render/start',json={'subtitles':False,'layout':layout}).json()
        for n in range(session['frames']):assert client.put(f"/api/jobs/{id}/frames/{session['token']}/{n}",content=image.read_bytes()).status_code==200
        assert client.post(f'/api/jobs/{id}/render/finish',json={}).status_code==200
        deadline=time.monotonic()+20
        while get_job(id)['status'] not in ['done','failed'] and time.monotonic()<deadline:time.sleep(.1)
        assert get_job(id)['status']=='done'
        output=tmp_path/'result.mp4';output.write_bytes(client.get(f'/api/jobs/{id}/download').content)
        with av.open(str(output)) as container:
            assert {s.codec_context.name for s in container.streams}=={'h264','aac'}
            frame=next(container.decode(video=0)).to_ndarray(format='rgb24')
        center=frame[250:350,600:680].mean(axis=(0,1));right=frame[250:350,1020:1100].mean(axis=(0,1))
        if kind=='audio':assert center[0]>200 and right[0]<30
        else:assert right[0]>200 and center[0]<30
