import json,subprocess
from pathlib import Path
import httpx
from backend.app.core import binary,probe
id='b25deaef34ec466b9462d216002329db'
with httpx.Client(base_url='http://127.0.0.1:8001',timeout=30) as client:
 r=client.get(f'/api/jobs/{id}/download');r.raise_for_status()
 target=Path('examples/madis-unseen-result.mp4');target.write_bytes(r.content)
 report=client.get(f'/api/jobs/{id}/report');report.raise_for_status()
 Path('examples/madis-unseen-report.json').write_text(json.dumps(report.json(),ensure_ascii=False,indent=2),encoding='utf-8')
 subprocess.run([binary('ffmpeg'),'-y','-v','error','-ss','0.6','-i',str(target),'-frames:v','1','docs/madis-unseen-result-frame.png'],check=True)
 info=probe(target)
 print(json.dumps({'bytes':len(r.content),'duration':info['format']['duration'],'codecs':[s['codec_name'] for s in info['streams']]}))
