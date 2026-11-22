"""Explicit research tools; none of these silently rewrites a transcript."""
import json,re
from collections import Counter
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel,Field
from . import how2sign
from .signavatars_bridge import convert_smplx,status as annotation_status
from .research_motion import convert_dong
from .vendor.constrained_gbnf import word_rules

router=APIRouter(prefix='/api/research')
SOURCES=[
 {'id':'constrained','name':'Vocabulary-constrained translation','url':'https://github.com/ntantaroudas/constrained-translation-sign-avatar','commit':'457e46fbbc9b7c775b44fee8f3fa1041d61399df','language':'International Sign','license':'MIT (code)','integration':'GBNF grammatika va matn qamrovini tekshirish','missing':'EuroLLM/NLLB o‘rnatilmagan; avtomatik qayta yozish yoqilmagan.'},
 {'id':'dong','name':'SignAvatar · Lu Dong','url':'https://github.com/dongludeeplearning/SignAvatar','commit':'1fe3dedc446b4b6eb7ef7af57fc318250cf213c0','language':'ASL','license':'CC BY-NC 4.0','integration':'53 bo‘g‘imli 6D harakatni JSON orqali moslashtirish','missing':'ASL3DWord va checkpointlar alohida so‘raladi; bu model hozir ishlamaydi.'},
 {'id':'signkit','name':'Sign-Kit','url':'https://github.com/spectre900/Sign-Kit-An-Avatar-based-ISL-Toolkit','commit':'cbb3491d2514b1b908658808cfffb497d020ff9d','language':'Indian Sign Language','license':'Repo ildizida litsenziya ko‘rsatilmagan','integration':'Ijro tezligini boshqarish usuli o‘rganildi; bizda mustaqil yozildi','missing':'Kod, XBOT/YBOT va ISL animatsiyalari mahsulotga ko‘chirilmagan.'},
 {'id':'signavatars','name':'SignAvatars · ECCV 2024','url':'https://github.com/ZhengdiYu/SignAvatars','commit':'bbfb35056aaad252ae67c60b44eb91618506d4a8','language':'ASL / DGS / boshqa to‘plamlar','license':'Dataset: notijoriy ruxsat; viewer GPL-3.0; SMPL-X alohida','integration':'182 → 133 kanal adapteri va How2Sign metadata bog‘lanishi','missing':'Ruxsatli 3D annotatsiyalar hali yo‘q.'},
]

@router.get('/sources')
def sources():return {'sources':SOURCES,'annotations':annotation_status(),'linguistically_verified':False}

def grammar(records):
    # Whole existing phrases only. Word-level IS vocabulary is not an ASL dictionary.
    phrases=sorted({re.sub(r'\s+',' ',c['text']).strip() for c in records if c.get('review_decision')!='rejected' and c.get('text') and not any(ord(ch)<32 for ch in c['text'])})
    if not phrases:raise ValueError('Faol iboralar kutubxonasi bo‘sh.')
    return 'root ::= phrase\n'+'\n'.join(word_rules(phrases,'phrase'))+'\n'

@router.get('/grammar',response_class=PlainTextResponse)
def download_grammar():
    try:return PlainTextResponse(grammar(how2sign.catalog()),headers={'Content-Disposition':'attachment; filename="how2sign-phrases.gbnf"'})
    except ValueError as e:raise HTTPException(409,str(e))

class Audit(BaseModel):
    original:str=Field(min_length=1,max_length=20000)
    candidate:str=Field(min_length=1,max_length=20000)

def audit_text(original,candidate):
    before=how2sign.translate_asl(original);after=how2sign.translate_asl(candidate)
    alerts=[]
    if Counter(re.findall(r'\d+(?:[.,]\d+)*',original))!=Counter(re.findall(r'\d+(?:[.,]\d+)*',candidate)):alerts.append('Sonlar o‘zgargan: ma’no tekshiruvi kerak.')
    neg=r"\b(?:no|not|never|cannot|without|neither|nor|\w+n['’]t)\b"
    if Counter(re.findall(neg,original.casefold()))!=Counter(re.findall(neg,candidate.casefold())):alerts.append('Inkor shakli o‘zgargan: ma’no tekshiruvi kerak.')
    return {'original':before,'candidate':after,'alerts':alerts,'meaning_verified':False,'applied':False,'notice':'Qamrov ortishi ma’no saqlanganini bildirmaydi. Asl matn o‘zgartirilmadi.'}

@router.post('/audit')
def audit(data:Audit):return audit_text(data.original,data.candidate)

@router.post('/motions/convert')
async def convert(request:Request):
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>16*1024*1024:raise HTTPException(413,'JSON 16 MB dan oshmasin.')
    try:
        data=json.loads(raw)
        if not isinstance(data,dict):raise ValueError('JSON obyekt talab qilinadi.')
        if data.get('format')=='signavatar-rot6d-53':return convert_dong(data)
        if 'smplx' in data:
            language=data.get('language')
            if language not in ['asl','dgs','isl','uz_sign','other']:raise ValueError('language: asl, dgs, isl, uz_sign yoki other bo‘lsin.')
            out=convert_smplx(data,data.get('fps'));out['language']=language;return out
        raise ValueError('SignAvatar 53×6 yoki SignAvatars 182 kanalli JSON kerak.')
    except (ValueError,TypeError) as e:raise HTTPException(422,str(e))
