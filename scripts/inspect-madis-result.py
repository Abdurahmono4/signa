import json,subprocess,shutil
from backend.app.core import STORE,get_job,binary
j=get_job('39710d364fc14fa4abb2e465b10c88dd');p=STORE/j['id']/j['result_token']/'result.mp4'
assert j['status']=='done' and j['settings']['engine']=='neural',j['settings']
shutil.copyfile(p,'examples/madis-result.mp4')
subprocess.run([binary('ffmpeg'),'-y','-v','error','-ss','0.6','-i',str(p),'-frames:v','1','docs/madis-result-frame.png'],check=True)
print(json.dumps({'engine':j['settings']['engine'],'probe':j['probe'],'bytes':p.stat().st_size}))

