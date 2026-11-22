from copy import deepcopy
import math
import subprocess
import time

import pytest
from fastapi.testclient import TestClient
from backend.app.export_validation import validate_export
from backend.app import main
from backend.app.core import STORE, binary, get_job, probe, save_job
from scripts.smoke_pipeline import png


@pytest.mark.parametrize(('fast','audio'), [(False,False),(True,False),(True,True)])
def test_slow_source_video_preserves_each_avatar_frame(tmp_path, monkeypatch, fast, audio):
    # Two background frames, twelve alternating avatar frames, 24 output frames.
    source = tmp_path / 'screen.mp4'
    ffmpeg = binary('ffmpeg')
    run = lambda args: subprocess.run([ffmpeg,'-v','error',*args],capture_output=True,check=True).stdout
    run(['-f','lavfi','-i','color=black:s=160x90:r=2:d=1',
         '-f','lavfi','-i','sine=duration=1','-c:v','libx264','-c:a','aac',str(source)])
    if audio:
        source=tmp_path/'speech.wav'
        run(['-f','lavfi','-i','sine=duration=1',str(source)])
    size='512x384' if fast else '384x512'
    pictures = [run(['-f','lavfi','-i',f'color={color}:s={size}',
                     '-frames:v','1','-c:v','png','-f','image2pipe','pipe:1']) for color in ['red','blue']]
    with TestClient(main.app) as client:
        with source.open('rb') as media:
            job=client.post('/api/upload',files={'file':(source.name,media)}).json()
        job.update(status='ready',language='en',segments=[],translation={'items':[]})
        save_job(job)
        url=f"/api/jobs/{job['id']}"
        settings={'subtitles':False}
        if fast:
            from backend.app import neural_api
            monkeypatch.setattr(neural_api,'plan',lambda _:dict(timing_scale=1,items=[
                dict(start=0,end=1,supported=True,duration_ms=1250)]))
            settings.update(engine='neural',avatar_model='rocketbox',motion_revision='adaptive-cadence-v8')
        session=client.post(url+'/render/start',json=settings).json()
        assert session['fps']==(30 if fast else 12)
        token=session['token']
        for i in range(session['frames']):
            assert client.put(f'{url}/frames/{token}/{i}',content=pictures[i%2]).is_success
        assert client.post(url+'/render/finish',json={'token':token}).is_success
        output=STORE/job['id']/token/'result.mp4'
        deadline=time.monotonic()+30
        while get_job(job['id'])['status'] in ['queued','rendering'] and time.monotonic()<deadline:
            time.sleep(.05)
        assert get_job(job['id'])['status']=='done'
        sample_x=640 if audio else 1100
        pixels=run(['-i',str(output),'-an','-vf',f'crop=4:4:{sample_x}:360,scale=1:1',
                    '-pix_fmt','rgb24','-f','rawvideo','pipe:1'])
        assert len(pixels)==(30 if fast else 24)*3
        assert [pixels[i]>pixels[i+2] for i in range(0,len(pixels),3)]==([True,False]*15 if fast else [True,True,False,False]*6)


def valid_probe():
    return {'format':{'duration':'3'}, 'streams':[
        {'codec_type':'video','codec_name':'h264','width':1280,'height':720,'pix_fmt':'yuv420p',
         'avg_frame_rate':'24/1','nb_frames':'72','duration':'3'},
        {'codec_type':'audio','codec_name':'aac','duration':'3'}]}


def test_stream_checks_accept_complete_video_and_short_original_audio():
    info=valid_probe()
    summary=validate_export(info,3,1280,720,info)
    assert summary['frames']==72 and summary['validation']=='streams-v1'
    short=deepcopy(info);short['streams'][1]['duration']='1'
    assert validate_export(short,3,1280,720,short)['audio_duration']==1
    missing=deepcopy(info);missing['streams'][1].pop('duration')
    assert validate_export(short,3,1280,720,missing)['audio_duration_reference']=='container-upper-bound'


@pytest.mark.parametrize('index,field,value',[
    (0,'duration','1'),(0,'nb_frames','24'),(1,'duration','1'),
    (0,'width',640),(0,'height',360),(0,'pix_fmt','yuv444p'),
    (0,'avg_frame_rate','30/1'),(0,'avg_frame_rate','0/0'),
    (0,'duration','NaN'),(1,'duration','inf'),(0,'nb_frames','N/A'),
    (0,'codec_name','hevc'),(1,'codec_name','mp3')])
def test_reject_incomplete_or_incompatible_stream_even_when_container_is_full(index,field,value):
    source=valid_probe();output=deepcopy(source);output['streams'][index][field]=value
    with pytest.raises(RuntimeError):validate_export(output,3,1280,720,source)


def test_audio_validation_respects_timing_scale():
    source=valid_probe();source['streams'][1]['duration']='1.5'
    assert validate_export(valid_probe(),3,1280,720,source,2)['audio_duration']==3


@pytest.mark.parametrize('native',[False,True])
def test_real_export_keeps_video_until_longer_audio_ends(tmp_path,native):
    """Colour + sine fixtures only: this is NOT a signing-quality evaluation."""
    source=tmp_path/'short-video-long-audio.mp4'
    subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=blue:s=320x180:r=24:d=1',
                    '-f','lavfi','-i','sine=frequency=440:sample_rate=16000:duration=3',
                    '-c:v','libx264','-c:a','aac',str(source)],check=True)
    source_probe=probe(source)
    assert float(source_probe['streams'][0]['duration'])<1.1
    with TestClient(main.app) as client:
        with source.open('rb') as f:
            response=client.post('/api/upload',files={'file':(source.name,f)})
        assert response.status_code==201
        job=response.json();job.update(status='ready',language='en',segments=[],translation={'items':[]})
        save_job(job);ident=job['id']
        start=client.post(f'/api/jobs/{ident}/render/start',json={'native_human':native,'subtitles':False})
        assert start.status_code==200
        session=start.json();token=session['token']
        if not native:
            fixture=png(384,512)
            for index in range(0,session['frames'],48):
                repeated=min(48,session['frames']-index)
                assert client.put(f'/api/jobs/{ident}/frames/{token}/{index}?repeat={repeated}',content=fixture).status_code==200
            assert client.post(f'/api/jobs/{ident}/render/finish',json={'token':token}).status_code==200
        deadline=time.monotonic()+30
        while get_job(ident)['status'] not in ['done','failed'] and time.monotonic()<deadline:time.sleep(.1)
        saved=get_job(ident)
        assert saved['status']=='done',saved.get('error')
        assert saved['probe']['validation']=='streams-v1'
        assert saved['probe']['frames']>=math.floor(job['duration']*24)-1
        assert saved['probe']['audio_duration']>2.9
        output=STORE/ident/token/'result.mp4'
        # Decode all frames/audio, not only the MP4 headers.
        decoded=subprocess.run([binary('ffmpeg'),'-v','error','-xerror','-i',str(output),'-f','null','-'],capture_output=True)
        assert decoded.returncode==0,decoded.stderr.decode(errors='replace')
        ranged=client.get(f'/api/jobs/{ident}/result?v={token}',headers={'Range':'bytes=0-1023'})
        assert ranged.status_code==206 and len(ranged.content)==1024
