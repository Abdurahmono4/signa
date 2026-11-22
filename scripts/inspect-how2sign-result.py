import json,subprocess,shutil
from pathlib import Path
from backend.app.core import get_job,STORE,binary,probe
job=get_job('39710d364fc14fa4abb2e465b10c88dd')
p=STORE/job['id']/job['result_token']/'result.mp4'
shutil.copyfile(p,Path('examples/how2sign-result.mp4'))
subprocess.run([binary('ffmpeg'),'-y','-v','error','-ss','0.6','-i',str(p),'-frames:v','1','docs/how2sign-result-frame.png'],check=True)
print(json.dumps({'job_id':job['id'],'result':str(p),'probe':job['probe'],'coverage':job['translation']['coverage'],'bytes':p.stat().st_size}))
