"""Experimental generative ASL, explicitly separate from recorded phrase retrieval."""
import json,os,threading,pickle
from pathlib import Path
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from .core import ROOT,STORE,get_job
from . import neural_engine as engine
from .timing import motion_time_scale
from . import neural_preflight
from .neural_limits import limits,check_chunks
router=APIRouter(prefix='/api')
worker_lock=threading.Lock()
_local_backend = ROOT / 'backend'
_previous_backend = Path.home() / 'Documents/Codex/2026-10-16/ya/outputs/signa/backend'
_default_backend = _local_backend if (_local_backend / 'models/MaDiS/runtime/.signa-ready.json').exists() or not _previous_backend.is_dir() else _previous_backend
MODEL_ROOT = Path(os.environ.get('SIGNBRIDGE_MADIS_BACKEND', _default_backend))
def row_for(id):
    import re
    if not re.fullmatch('[a-f0-9]{32}',id):raise HTTPException(404,'Ish topilmadi.')
    job=get_job(id)
    if not job:raise HTTPException(404,'Ish topilmadi.')
    return {'id':id,'revision':1,'duration':job['duration'],'segments':json.dumps(job['segments'])}
@router.get('/neural/health')
def neural_health():return engine.readiness(MODEL_ROOT)
@router.post('/jobs/{id}/neural')
def generate(id:str):
    row=row_for(id);job=get_job(id)
    if job.get('language')!='en':raise HTTPException(422,'ML modeliga inglizcha nutq kerak.')
    if job['status'] not in ['ready','done','failed','cancelled'] or not job['segments'] or job.get('translation') is None:raise HTTPException(409,'Avval nutq matnini tayyorlang.')
    if job['duration']>1200:raise HTTPException(422,'Media 20 daqiqadan oshmasin.')
    if not engine.readiness(MODEL_ROOT)['ready']:raise HTTPException(503,'MaDiS modeli yoki alohida CPU muhiti tayyor emas.')
    try:compatibility=neural_preflight.inspect(MODEL_ROOT,engine.chunks(job['segments']))
    except (OSError,ValueError,pickle.UnpicklingError) as exc:raise HTTPException(503,'Model matn lug‘atini tekshirib bo‘lmadi.') from exc
    unsupported=compatibility['unsupported_chunks']
    try:check_chunks(compatibility['checked_chunks']-len(unsupported))
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    if unsupported and len(unsupported)>=compatibility['checked_chunks']:raise HTTPException(422,'Bu matn avatar modelining lug‘atiga mos emas. Matn va subtitrni yuklab olishingiz mumkin; ishonchli avatar ijrosi tayyorlanmadi.')
    try:return engine.enqueue(MODEL_ROOT,STORE,row,worker_lock,lambda:None,unsupported_chunks=unsupported)
    except ValueError as e:raise HTTPException(422,str(e))
    except RuntimeError as e:raise HTTPException(409,str(e))
@router.get('/jobs/{id}/neural')
def state(id:str):return engine.status(STORE,row_for(id))
@router.post('/jobs/{id}/neural/cancel')
def cancel(id:str):return {'cancelled':engine.cancel(row_for(id))}
@router.get('/jobs/{id}/neural/plan')
def plan(id:str):
    row=row_for(id);path=engine.folder(STORE,row)/'plan.json'
    if not path.exists():raise HTTPException(409,'ML harakati hali tayyor emas.')
    raw=json.loads(path.read_text(encoding='utf-8'));items=[]
    for item in raw['items']:
        clip=item['clip']
        items.append({'text':item['text'],'start':item['start'],'end':item['end'],
                      'supported':bool(clip),'sign_id':clip['id'] if clip else None,
                      'duration_ms':round(clip['duration']*1000) if clip else None,
                      'animation_path':None,'neural_asset':clip['neural_asset'] if clip else None,
                      'reason':'ML yaratgan tajribaviy 3D harakat; lingvistik tasdiqsiz' if clip else 'Mos avatar ijrosi yo‘q; subtitr bilan beriladi' if item.get('status')=='unsupported' else 'Nutq pauzasi',
                      'unsupported':item.get('status')=='unsupported',
                      'verified':False,'generated':bool(clip)})
    try:scale=motion_time_scale(items)
    except ValueError as e:raise HTTPException(422,str(e))
    for item in items:
        item.update(source_start=item['start'],source_end=item['end'])
        item['start']*=scale;item['end']*=scale
    return {'items':items,'coverage':0,'supported_words':0,'total_words':raw['total_words'],
            'timing_scale':scale,'output_duration':row.get('duration',raw.get('media_duration',0))*scale,
            'generated_phrases':raw['playable_signs'],'kind':'model_generated',
            'unsupported_phrases':raw.get('unsupported_phrases',0),'caption_words':raw.get('caption_words',0),
            'limits':limits(),
            'warning':'3D retarget taxminiy; til va qo‘l shakllari tasdiqlanmagan. Harakat 1.25× dan tezlashtirilmaydi; zarur bo‘lsa original video/audio birga sekinlashadi.'}
@router.get('/jobs/{id}/neural/motions/{motion_id}')
def motion(id:str,motion_id:int,key:str):
    row=row_for(id)
    if key!=engine.key_for(row):raise HTTPException(409,'Harakat versiyasi mos emas.')
    base=engine.folder(STORE,row)/'motion';index=base/'index.json'
    if not index.exists():raise HTTPException(404,'Harakat topilmadi.')
    record=next((m for m in json.loads(index.read_text())['motions'] if str(m['id'])==str(motion_id)),None)
    if not record:raise HTTPException(404,'Harakat topilmadi.')
    path=Path(record['motion_json']);path=path if path.is_absolute() else base/path;path=path.resolve()
    if not path.is_relative_to(base.resolve()) or not path.exists():raise HTTPException(404,'Harakat topilmadi.')
    return FileResponse(path,media_type='application/json')
