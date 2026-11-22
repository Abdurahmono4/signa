import json,zipfile
from pathlib import Path
from backend.app.how2sign import BASE,catalog
archives=list(BASE.glob('val_rgb_front_clips*.zip'))+list((Path.home()/'Downloads').glob('val_rgb_front_clips*.zip'))
for path in archives:
 with zipfile.ZipFile(path) as z:
  vids=[f for f in z.infolist() if f.filename.lower().endswith('.mp4')]
  print(json.dumps({'archive':str(path),'zip_videos':len(vids),'imported':len(catalog()),'extracted_bytes':sum(p.stat().st_size for p in (BASE/'clips').glob('*.mp4'))}))
