import json,subprocess
from pathlib import Path
from backend.app.core import binary
r=Path(r'D:\SignBridge-UZ');clips=json.loads((r/'datasets/how2sign/catalog.json').read_text(encoding='utf-8'))
seen=set();selected=[]
for c in clips:
    key=c['sentence_name'].split('_')[0]
    if key not in seen:seen.add(key);selected.append(c)
    if len(selected)==6:break
for i,c in enumerate(selected):
    subprocess.run([binary('ffmpeg'),'-v','error','-y','-ss','0.4','-i',str(r/'datasets/how2sign/clips'/(c['id']+'.mp4')),'-frames:v','1','-vf','scale=480:-1',str(r/'docs'/f'presenter-candidate-{i}.png')],check=True)
print(json.dumps([{'i':i,'id':c['id'],'text':c['text'],'duration':c['duration']} for i,c in enumerate(selected)]))
