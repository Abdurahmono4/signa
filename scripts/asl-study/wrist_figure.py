"""Create a comparison image from actual rendered/reference frames and their detected wrists."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def draw(study, sample, take):
    root = Path(__file__).resolve().parents[2]
    ffmpeg = next((root/'tools/ffmpeg').rglob('ffmpeg.exe'))
    def clips(name):
        return json.loads((study/name).read_text(encoding='utf-8'))['clips']
    main = clips('landmarks.json')
    extra = clips('alternate-landmarks.json')
    manifests = json.loads((study/'alternate-human/manifest.json').read_text())['complete']
    assert next(r['target'] for r in manifests if r['id']==take)==sample
    def get(items, kind, id):
        return next(r for r in items if r['kind']==kind and r['id']==id)
    sources = [
        (get(main,'human',sample), study.parent/'human'/f'{sample}.mp4','Tarjimon · birinchi yozuv'),
        (get(main,'avatar',sample), study/'avatar'/f'avatar-{sample}.mp4','SignBridge avatari'),
        (get(extra,'alternate',take), study/'alternate-human'/f'{take}.mp4','Tarjimon · boshqa yozuv')]
    font_dir = Path(os.environ['WINDIR'])/'Fonts'
    def font(size,bold=False):
        return ImageFont.truetype(str(font_dir/('segoeuib.ttf' if bold else 'segoeui.ttf')),size)
    canvas=Image.new('RGB',(1176,614),'#0f1825')
    text=ImageDraw.Draw(canvas)
    text.text((22,12),'Bir jumlada bilaklar qayerda turibdi?',font=font(27,True),fill='#f7f8fd')
    text.text((22,53),f'{sample}-namuna   ·   Har bir ijroning o‘rtasidagi kadr   ·   Ekranda yelka kengligi tenglashtirilgan',font=font(17),fill='#c5d6e6')
    for i,(clip,file,label) in enumerate(sources):
        k=round((len(clip['frames'])-1)*.5)
        frame=clip['frames'][k]
        body=np.asarray(frame['body'])
        pixels=subprocess.check_output([str(ffmpeg),'-v','error','-i',str(file),'-vf',f'select=eq(n\\,{k})',
                                        '-frames:v','1','-f','image2pipe','-c:v','png','pipe:1'])
        raw=Image.open(io.BytesIO(pixels)).convert('RGB')
        center=body[:2,:2].mean(axis=0)
        scale=124/np.linalg.norm(body[0,:2]-body[1,:2])
        box=(center[0]-188/scale,center[1]-163/scale,center[0]+188/scale,center[1]+253/scale)
        panel=raw.transform((376,416),Image.Transform.EXTENT,box,Image.Resampling.BICUBIC)
        points=ImageDraw.Draw(panel)
        for si,(side,color) in enumerate([('left','#83f3cd'),('right','#ffd877')]):
            wrist=np.array(frame[side][0]) if frame[side] else body[2+si,:2]
            px,py=(wrist-np.asarray(box[:2]))*scale
            points.ellipse((px-6,py-6,px+6,py+6),outline='#142838',width=4)
            points.ellipse((px-6,py-6,px+6,py+6),outline=color,width=2)
        x=12+388*i
        text.text((x+10,89),label,font=font(20,True),fill='#d4e4fa')
        canvas.paste(panel,(x,125))
    text.text((22,552),'Yashil — chap bilak.   Sariq — o‘ng bilak.   Belgilar video orqali avtomatik aniqlangan.',font=font(16),fill='#e8f3ff')
    text.text((22,582),'How2Sign test yozuvlari  ·  MaDiS / Rocketbox  ·  Bir xil nisbiy vaqt bir xil ishora paytiga to‘g‘ri kelmasligi mumkin.',font=font(14),fill='#b8c9d8')
    canvas.save(study/f'bilak-{sample}.jpg',quality=94)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('study',type=Path);p.add_argument('sample');p.add_argument('take')
    a=p.parse_args();draw(a.study,a.sample,a.take)
