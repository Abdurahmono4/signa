"""Real HTTP/FFmpeg integration test. Transparent test frames are NOT avatar validation."""
import json,struct,subprocess,sys,time,zlib
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.core import binary,probe

def png(width=384,height=512):
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    # Entirely transparent fixture, never presented as a rendered avatar.
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\0'*(width*4))*height))+chunk(b'IEND',b'')

def wait(client,id,terminal):
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        response=client.get('/api/jobs/'+id);response.raise_for_status();job=response.json()
        if job['status'] in terminal:return job
        if job['status'] in ['failed','cancelled']:raise RuntimeError(job)
        time.sleep(.3)
    raise TimeoutError(id)

def main():
    folder=ROOT/'storage'/'integration-evidence';folder.mkdir(exist_ok=True)
    results=[]
    with httpx.Client(base_url='http://127.0.0.1:8001',timeout=60) as client:
        assert client.get('/api/health').json()['ffmpeg']
        for kind in ['audio','video']:
            path=folder/('silent.wav' if kind=='audio' else 'silent.mp4')
            args=[binary('ffmpeg'),'-y','-v','error','-f','lavfi','-i','anullsrc=r=16000:cl=mono']
            if kind=='video':args+=['-f','lavfi','-i','color=c=0x172440:s=640x360:r=24','-c:v','libx264','-c:a','aac']
            args+=['-t','2',str(path)]
            subprocess.run(args,check=True,capture_output=True)
            with path.open('rb') as f:r=client.post('/api/upload',files={'file':(path.name,f)})
            r.raise_for_status();id=r.json()['id'];assert r.json()['kind']==kind
            r=client.post('/api/jobs',json={'job_id':id,'model':'tiny'});r.raise_for_status()
            job=wait(client,id,['ready']);assert job['translation']['coverage']==0
            session=client.post(f'/api/jobs/{id}/render/start',json={'resolution':720}).json()
            for n in range(session['frames']):
                r=client.put(f"/api/jobs/{id}/frames/{session['token']}/{n}",content=png());r.raise_for_status()
            r=client.post(f'/api/jobs/{id}/render/finish');r.raise_for_status()
            job=wait(client,id,['done'])
            download=client.get(f'/api/jobs/{id}/download');download.raise_for_status()
            output=folder/f'{kind}-pipeline.mp4';output.write_bytes(download.content)
            info=probe(output);streams=info['streams']
            assert any(s['codec_name']=='h264' and s['height']==720 for s in streams)
            assert any(s['codec_name']=='aac' for s in streams)
            assert abs(float(info['format']['duration'])-2)<.5
            results.append({'kind':kind,'job_id':id,'bytes':len(download.content),'duration':info['format']['duration'],'codecs':[s['codec_name'] for s in streams],'avatar_validation':False,'speech_validation':'silence-only, not Uzbek accuracy'})
    (folder/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
if __name__=='__main__':main()
