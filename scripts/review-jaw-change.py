"""Render before/after from saved and candidate production bone matrices."""
import sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import importlib.util
spec=importlib.util.spec_from_file_location('review_renderer',Path(__file__).with_name('render-asl-review.py'))
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
avatar,load,OUT,F=renderer.avatar,renderer.load,renderer.OUT,renderer.F

old=Path(tempfile.gettempdir())/'signbridge-asl10-bones'
new=Path(tempfile.gettempdir())/'signbridge-asl10-jaw-v6'
dest=OUT/'jaw-v6';dest.mkdir(exist_ok=True)
sheet=Image.new('RGB',(960,1800),'#0b1523')
metrics=[]
for i in range(10):
    motion=load(OUT/'model'/f'{i:04}'/'motion.json');a=np.array(motion['features'])
    frame=int(np.linalg.norm(a[:,120:123],axis=1).argmax())
    bones=[np.fromfile(d/f'{i+1}.bin',dtype='f4').reshape(len(a),80,16) for d in (old,new)]
    for j,b in enumerate(bones):
        im=avatar(b[frame]).crop((170,5,310,145)).resize((240,240))
        x=(i%2)*480+j*240;y=(i//2)*360
        sheet.paste(im,(x,y+65))
        draw=ImageDraw.Draw(sheet);draw.text((x+8,y+35),'Oldin' if not j else 'Jag‘ ulangan',font=F[18],fill='white')
    draw.text(((i%2)*480+8,(i//2)*360+5),f'{i+1:02} / {frame} kadr · jag‘ burchagi {np.linalg.norm(a[frame,120:123]):.3f} rad',font=F[16],fill='white')
    metrics.append({'sample':i+1,'frame':frame,'jaw_radians':a[frame,120:123].tolist()})
sheet.save(dest/'oldin-keyin.jpg',quality=95)
(dest/'frames.json').write_text(__import__('json').dumps(metrics,indent=2),encoding='utf-8')
