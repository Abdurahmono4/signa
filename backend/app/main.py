import hashlib
import asyncio,json,logging,math,os,re,shutil,subprocess,threading,uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI,UploadFile,File,Form,HTTPException,Request
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from typing import Literal
from .core import ROOT,STORE,ASSETS,db,initialize,save_job,get_job,signs,binary,probe
from .translation import translate
from . import how2sign
from .neural_api import router as neural_router
from .timing import tempo_filters, rocketbox_capture_fps
from .speech_audio import decode_speech_audio
from .frame_validation import validate_png_frame
from .render_resources import ensure_render_space
from .video_captions import make_ass

logging.basicConfig(level=logging.INFO)
pool=ThreadPoolExecutor(max_workers=1); cancelled=set(); models={};lock=threading.Lock()
LIMIT=100*1024*1024; FPS=12
@asynccontextmanager
async def lifespan(app):
    initialize()
    with db() as c:
        for row in c.execute('SELECT data FROM jobs').fetchall():
            job=json.loads(row[0])
            if job['status'] in ['processing','rendering','queued','frames']:
                job.update(resume_frames=job['status']=='frames',status='failed',error='Server qayta ishga tushdi. Qayta urinib ko‘ring.');save_job(job)
    async def scan_dataset():
        while True:
            await asyncio.to_thread(how2sign.import_available)
            await asyncio.sleep(15)
    scanner=asyncio.create_task(scan_dataset())
    yield
    scanner.cancel()
    from . import neural_engine
    neural_engine.shutdown()
app=FastAPI(title='SignBridge UZ',lifespan=lifespan)
app.include_router(neural_router)
from .research_api import router as research_router
app.include_router(research_router)
from .train_api import router as train_router
app.include_router(train_router)
from .dataset_status import router as dataset_router
app.include_router(dataset_router)
@app.get('/api/signavatars')
def signavatars_status():
    from .signavatars_bridge import status
    return status()
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5174','http://127.0.0.1:5174'],allow_methods=['*'],allow_headers=['*'])
app.mount('/assets',StaticFiles(directory=ASSETS),name='assets')
def job_of(id):
    if not re.fullmatch('[a-f0-9]{32}',id):raise HTTPException(404,'Ish topilmadi.')
    job=get_job(id)
    if not job:raise HTTPException(404,'Ish topilmadi.')
    return job
class StaleRender(Exception):pass

def update(id,expected_render_token=None,**values):
    with lock:
        job=job_of(id)
        if expected_render_token is not None and job.get('render_token')!=expected_render_token:raise StaleRender()
        job.update(values);save_job(job)
    return job
def check(id,render_token=None):
    if render_token is not None and job_of(id).get('render_token')!=render_token:raise StaleRender()
    if id in cancelled:raise InterruptedError('Bekor qilindi.')
def fail(id,e,render_token=None):
    if isinstance(e,StaleRender):return
    logging.exception('Job %s failed',id)
    try:update(id,expected_render_token=render_token,status='cancelled' if isinstance(e,InterruptedError) else 'failed',error='Bekor qilindi.' if isinstance(e,InterruptedError) else 'Jarayon bajarilmadi. Mahalliy server jurnalini tekshiring va qayta urinib ko‘ring.')
    except StaleRender:return
@app.get('/api/health')
def health():
    try:binary('ffmpeg');binary('ffprobe');ff=True
    except RuntimeError:ff=False
    return {'ok':True,'ffmpeg':ff,'device':'cpu','verified_signs':sum(s['verified'] and s['language']=='uz_sign' for s in signs())}
@app.get('/api/signs')
def get_signs():return signs()
@app.get('/api/how2sign')
def dataset_status():return {**how2sign.state,'clips':how2sign.catalog(),'metadata_ready':(how2sign.BASE/'how2sign_val.csv').exists()}
@app.get('/api/how2sign/clips/{id}')
def dataset_clip(id:str):
    if not re.fullmatch('[a-f0-9]{24}',id) or not any(c['id']==id for c in how2sign.catalog()):raise HTTPException(404,'Klip topilmadi.')
    return FileResponse(how2sign.CLIPS/f'{id}.mp4',media_type='video/mp4')
@app.get('/api/how2sign/realigned/clips/{ident}')
def realigned_clip(ident:str):
    record=how2sign.realigned_clips.cached(how2sign.BASE,ident)
    if record is None:raise HTTPException(404,'Tuzatilgan ASL klipi topilmadi.')
    return FileResponse(record['_local_path'],media_type='video/mp4')
class CorpusReview(BaseModel):
    decision:Literal['approved','rejected','needs_review']
    reviewer:str=Field(min_length=3,max_length=100)
    notes:str=Field(min_length=15,max_length=2000)
@app.post('/api/how2sign/clips/{id}/review')
def review_corpus(id:str,data:CorpusReview):
    if not any(c['id']==id for c in how2sign.catalog()):raise HTTPException(404,'Klip topilmadi.')
    if len(data.reviewer.strip())<3 or len(data.notes.strip())<15:raise HTTPException(422,'Tekshiruvchi va asoslangan izoh kerak.')
    with db() as c:
        values=(id,data.decision,data.reviewer.strip(),data.notes.strip())
        c.execute('INSERT INTO corpus_reviews (id,decision,reviewer,notes) VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET decision=excluded.decision,reviewer=excluded.reviewer,notes=excluded.notes,updated_at=CURRENT_TIMESTAMP',values)
        c.execute('INSERT INTO corpus_review_history (id,decision,reviewer,notes) VALUES (?,?,?,?)',values)
    return {'id':id,'review_decision':data.decision,'verified':data.decision=='approved'}
@app.get('/api/jobs/{id}/report')
def job_report(id:str):
    job=job_of(id)
    return {'id':id,'name':job['name'],'language':job.get('language'),'segments':job['segments'],'translation':job.get('translation'),
            'export_settings':job.get('settings'),'timing_scale':job.get('timing_scale',1),'probe':job.get('probe'),
            'neural_summary':job.get('neural_summary'),
            'notice':'Qamrov tarjima aniqligi bahosi emas. ML va manba kliplari alohida ekspert bahosini talab qiladi.'}
class TextRequest(BaseModel):
    text:str=Field(min_length=1,max_length=20000)
    language:Literal['en','uz']='en'
@app.post('/api/translate')
def text_translate(data:TextRequest):return how2sign.translate_asl(data.text) if data.language=='en' else translate(data.text,None,signs())
class TranscriptSegment(BaseModel):
    text:str=Field(min_length=1,max_length=8000)
    start:float=Field(ge=0,allow_inf_nan=False)
    end:float=Field(gt=0,allow_inf_nan=False)
class TranscriptEdit(BaseModel):
    segments:list[TranscriptSegment]=Field(min_length=1,max_length=10000)
    expected_revision:int|None=Field(default=None,ge=0)
@app.put('/api/jobs/{id}/transcript')
def edit_transcript(id:str,data:TranscriptEdit):
    job=job_of(id)
    if data.expected_revision is not None and data.expected_revision!=job.get('transcript_revision',0):
        raise HTTPException(409,'Matn boshqa oynada yangilangan. Sahifani yangilab, so‘ng qayta tahrirlang.')
    if job['status'] not in ['ready','done','failed','cancelled'] or not job.get('segments'):raise HTTPException(409,'Avval nutq tahlilini tugating.')
    if job.get('language')!='en':raise HTTPException(422,'Bu tahrir inglizcha nutq uchun.')
    # Text correction must preserve the original ASR intervals. It cannot move
    # speech onto another part of the media or keep obsolete word timestamps.
    if len(data.segments)!=len(job['segments']):raise HTTPException(422,'Nutq bo‘laklari soni o‘zgarmasin.')
    segments=[]
    for segment,original in zip(data.segments,job['segments']):
        text=segment.text.strip()
        if not text or segment.end<=segment.start or abs(segment.start-original['start'])>1e-6 or abs(segment.end-original['end'])>1e-6:
            raise HTTPException(422,'Matn bo‘sh bo‘lmasin; original nutq vaqtlari saqlansin.')
        if text==original['text']:segments.append(original)
        else:segments.append({'text':text,'start':segment.start,'end':segment.end})
    if segments==job['segments']:return how2sign.refresh_human_timing(job)
    if sum(len(s['text']) for s in segments)>100000:raise HTTPException(413,'Matn juda katta.')
    from . import neural_engine
    neural_engine.cancel({'id':id,'revision':1,'duration':job['duration'],'segments':json.dumps(job['segments'])})
    translation=how2sign.translate_asl('',segments,job['duration'])
    history=job.get('previous_results',[])
    if job.get('result_token'):history=[*history,{'token':job['result_token'],'settings':job.get('settings')}]
    with lock:
        latest=job_of(id)
        if latest.get('transcript_revision',0)!=job.get('transcript_revision',0) or latest['segments']!=job['segments'] or latest['status'] not in ['ready','done','failed','cancelled']:
            raise HTTPException(409,'Ish boshqa oynada o‘zgargan. Sahifani yangilang.')
        latest.update(segments=segments,translation=translation,status='ready',phase='Tahrirlangan matn va qamrov tayyor',progress=100,error=None,
                      transcript_revision=job.get('transcript_revision',0)+1,result_token=None,previous_results=history)
        save_job(latest)
        return latest
@app.get('/api/jobs/{id}/transcript/download')
def download_transcript(id:str,format:Literal['txt','srt']='txt'):
    job=job_of(id)
    if not job.get('segments') or job['status'] in ['uploaded','queued','processing']:
        raise HTTPException(409,'Avval nutq tahlilini tugating.')
    # Always reference original media time, independent of an optional paced MP4.
    if format=='txt':
        content='\n'.join(s['text'].strip() for s in job['segments'])+'\n'
    else:
        cues=[]
        for segment in job['segments']:
            start=max(0,round(segment['start']*1000));end=min(round(job['duration']*1000),round(segment['end']*1000))
            if end<=start:continue
            text=' '.join(segment['text'].split())
            if text:cues.append(f"{len(cues)+1}\n{timestamp(start/1000)} --> {timestamp(end/1000)}\n{text}")
        content='\n\n'.join(cues)+'\n'
    return Response(content.encode('utf-8-sig'),media_type='text/plain',headers={
        'Content-Disposition':f'attachment; filename="SignBridge-{id[:8]}-original.{format}"',
        'Cache-Control':'no-store','X-Transcript-Revision':str(job.get('transcript_revision',0))})
@app.post('/api/signs/import',status_code=201)
async def import_sign(metadata:str=Form(...),animation:UploadFile=File(...)):
    try:
        data=json.loads(metadata)
        for key in ['label','gloss','source','license','language']:
            if not isinstance(data.get(key),str) or not 1<=len(data[key])<=500:raise ValueError('Metadata maydonlari to‘liq bo‘lishi kerak.')
        if data['language'] not in ['uz_sign','asl','demo']:raise ValueError('Til yaroqsiz.')
        raw=await animation.read(8*1024*1024+1)
        if len(raw)>8*1024*1024:raise ValueError('Animatsiya 8 MB dan oshmasin.')
        clip=json.loads(raw);duration=float(clip['duration'])
        if not 0<duration<=30 or not 1<=len(clip['tracks'])<=2000:raise ValueError('Animatsiya davomiyligi yoki treklar yaroqsiz.')
        # Target names and lengths validated; importing never approves a sign.
        rig=json.loads((ROOT/'datasets'/'rig-targets.json').read_text())
        for t in clip['tracks']:
            target=t['name'].split('.')[0]
            if target not in rig or not re.fullmatch(r'[\w-]+\.(position|quaternion|scale|morphTargetInfluences\[\d+\])',t['name']):raise ValueError('Rigga mos bo‘lmagan trek.')
            if len(t['times'])>4000 or not t['times'] or len(t['values'])!=len(t['times'])*{'vector':3,'quaternion':4,'number':1}[t['type']]:raise ValueError('Trek o‘lchami yaroqsiz.')
            if not all(math.isfinite(v) for v in t['times']+t['values']):raise ValueError('Trek qiymati yaroqsiz.')
            if any(a>b for a,b in zip(t['times'],t['times'][1:])):raise ValueError('Vaqt ketma-ketligi yaroqsiz.')
        id=uuid.uuid4().hex;path=f'/assets/animations/{id}.json'
        (ASSETS/'animations'/f'{id}.json').write_bytes(raw)
        record={k:data[k] for k in ['label','gloss','source','license','language']}
        record.update(id=id,animation_path=path,duration_ms=round(duration*1000),verified=False,reviewer=None,keypoint_reference=None)
        with db() as c:c.execute('INSERT INTO signs VALUES (?,?)',(id,json.dumps(record)))
        return record
    except (ValueError,KeyError,TypeError) as e:raise HTTPException(422,str(e))
class Review(BaseModel):
    reviewer:str=Field(min_length=3,max_length=100)
    notes:str=Field(min_length=15,max_length=2000)
    verified:bool
@app.post('/api/signs/{id}/review')
def review(id:str,data:Review):
    record=next((s for s in signs() if s['id']==id),None)
    if not record:raise HTTPException(404,'Ishora topilmadi.')
    record.update(data.model_dump())
    with db() as c:c.execute('UPDATE signs SET data=? WHERE id=?',(json.dumps(record),id))
    return record
def reusable_export(digest, ext, model):
    with db() as connection:
        rows = connection.execute(
            "SELECT data FROM jobs WHERE json_extract(data,'$.status')='done' "
            "AND json_extract(data,'$.source_sha256')=? ORDER BY rowid DESC",
            (digest,),
        ).fetchall()
    for row in rows:
        job = json.loads(row[0])
        settings = job.get('settings') or {}
        if ((job.get('probe') or {}).get('validation') != 'streams-v1'
                or job.get('language') != 'en' or job.get('speech_model') != model
                or job.get('ext') != ext or job.get('transcript_revision') != 1
                or settings.get('resolution') != 1080 or not settings.get('subtitles')
                or settings.get('layout') != 'side_by_side'
                or settings.get('close_panel') != (job.get('kind') == 'video')
                or settings.get('size') != (.30 if job.get('kind') == 'video' else .40)
                or settings.get('motion_revision') != 'wrist-transition-v9'
                or settings.get('capture_quality') != 'high'
                or settings.get('appearance') != 'navy-v1' or settings.get('engine') != 'neural'):
            continue
        folder = STORE / job['id']
        output = folder / job['result_token'] / 'result.mp4'
        if output.is_file() and output.stat().st_size and (folder / f'input{ext}').is_file():
            return job
    return None

@app.post('/api/upload',status_code=201)
async def upload(file:UploadFile, reuse_model:Literal['small','base','tiny']|None=None):
    ext=Path(file.filename or '').suffix.lower()
    if ext not in ['.mp4','.mov','.webm','.mp3','.wav','.m4a','.ogg','.flac']:raise HTTPException(415,'Media formati qo‘llanmaydi.')
    id=uuid.uuid4().hex;folder=STORE/id;folder.mkdir();path=folder/f'input{ext}';size=0
    try:
        digest = hashlib.sha256()
        with path.open('wb') as out:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>LIMIT:raise HTTPException(413,'100 MB chegaradan oshdi.')
                digest.update(chunk)
                out.write(chunk)
        if reuse_model:
            cached = reusable_export(digest.hexdigest(), ext, reuse_model)
            if cached:
                path.unlink()
                folder.rmdir()
                return await asyncio.to_thread(how2sign.refresh_human_timing,cached)
        info=await asyncio.to_thread(probe,path)
        duration=float(info['format']['duration'])
        if not 0<duration<=1200:raise HTTPException(422,'Media 20 daqiqadan oshmasin.')
        if not any(s['codec_type']=='audio' for s in info['streams']):raise HTTPException(422,'Audio yo‘lagi topilmadi.')
        kind='video' if any(s['codec_type']=='video' and not s.get('disposition',{}).get('attached_pic') for s in info['streams']) else 'audio'
        job={'id':id,'name':Path(file.filename or 'media').name,'ext':ext,'kind':kind,'duration':duration,'status':'uploaded','progress':0,'phase':'Yuklandi','source_sha256':digest.hexdigest(),'segments':[],'translation':None,'error':None}
        save_job(job);return job
    except (ValueError,KeyError) as e:
        shutil.rmtree(folder);raise HTTPException(422,'Media fayli yaroqsiz yoki davomiyligi aniqlanmadi.') from e
    except Exception:
        shutil.rmtree(folder);raise
class ProcessRequest(BaseModel):
    job_id:str
    model:Literal['tiny','base','small']='small'
    language:Literal['en','uz']='en'
class StaleTranscription(Exception):pass

def reusable_transcript(job, model, language):
    digest = job.get('source_sha256')
    if not digest or job.get('transcript_revision') != 1:
        return None
    with db() as connection:
        row = connection.execute("""
            SELECT json_extract(data,'$.segments') FROM jobs
            WHERE id != ? AND json_extract(data,'$.source_sha256') = ?
              AND json_extract(data,'$.language') = ?
              AND json_extract(data,'$.speech_model') = ?
              AND json_extract(data,'$.transcript_revision') = 1
              AND json_extract(data,'$.status') IN ('ready','done','frames','rendering')
              AND json_type(data,'$.translation') = 'object'
              AND json_array_length(data,'$.segments') > 0
            ORDER BY rowid DESC LIMIT 1
        """, (job['id'], digest, language, model)).fetchone()
    return json.loads(row[0]) if row else None

def transcribe_job(id,model_name,language='en',token=None):
    def write(require_active=True,**values):
        with lock:
            latest=job_of(id)
            if token is not None and latest.get('transcribe_token')!=token:raise StaleTranscription()
            if require_active:check(id)
            latest.update(values);save_job(latest)
            return latest
    try:
        job=write(status='processing',phase='Nutq modeli yuklanmoqda',progress=5,error=None,language=language,speech_model=model_name)
        cached = reusable_transcript(job, model_name, language)
        if cached is not None:
            sequence = how2sign.translate_asl('', cached, job['duration']) if language == 'en' else translate('', cached, signs())
            write(status='ready', phase='Saqlangan nutq matni tayyor', progress=100,
                  segments=cached, translation=sequence)
            return
        audio=decode_speech_audio(STORE/id/f"input{job['ext']}")
        if audio is None:
            write(status='failed',phase='Nutq topilmadi',progress=100,segments=[],translation=None,error='Faylda ovoz yo‘q. Nutq bor audio yoki video yuklang.')
            return
        from faster_whisper import WhisperModel
        if model_name not in models:models[model_name]=WhisperModel(model_name,device='cpu',compute_type='int8',cpu_threads=6,num_workers=1)
        write(phase='Inglizcha nutq aniqlanmoqda' if language=='en' else 'O‘zbekcha nutq aniqlanmoqda',progress=10)
        segments,info=models[model_name].transcribe(audio,language=language,beam_size=5,word_timestamps=True,vad_filter=False)
        result=[]
        for seg in segments:
            check(id)
            if not seg.text.strip():continue
            result.append({'start':seg.start,'end':seg.end,'text':seg.text.strip(),'words':[{'start':w.start,'end':w.end,'word':w.word} for w in seg.words or []]})
            write(progress=min(85,10+int(75*seg.end/job['duration'])),segments=result)
        check(id)
        if not result:
            write(status='failed',phase='Nutq topilmadi',progress=100,segments=[],translation=None,error='Faylda tushunarli nutq aniqlanmadi. Nutq bor audio yoki video bilan qayta urinib ko‘ring.')
            return
        sequence=how2sign.translate_asl('',result,job['duration']) if language=='en' else translate('',result,signs())
        write(status='ready',phase='Matn va qamrov tayyor',progress=100,segments=result,translation=sequence)
    except StaleTranscription:return
    except Exception as e:
        logging.exception('Transcription %s failed',id)
        try:write(require_active=False,status='cancelled' if isinstance(e,InterruptedError) else 'failed',error='Bekor qilindi.' if isinstance(e,InterruptedError) else 'Nutqni aniqlash bajarilmadi. Qayta urinib ko‘ring.')
        except StaleTranscription:return
@app.post('/api/transcribe')
@app.post('/api/jobs')
def process(data:ProcessRequest):
    with lock:
        job=job_of(data.job_id)
        if job['status'] in ['processing','queued','rendering','frames']:raise HTTPException(409,'Jarayon ishlayapti.')
        from . import neural_engine
        neural_engine.cancel({'id':job['id'],'revision':1,'duration':job['duration'],'segments':json.dumps(job['segments'])})
        history=job.get('previous_results',[])
        previous=job.get('result_token')
        if previous and not any(record.get('token')==previous for record in history):
            history=[*history,{'token':previous,'settings':job.get('settings'),'transcript_revision':job.get('transcript_revision',0)}]
        cancelled.discard(job['id'])
        job.update(status='queued',progress=0,phase='Navbatda',error=None,language=data.language,
                   segments=[],translation=None,result_token=None,previous_results=history,
                   transcript_revision=job.get('transcript_revision',0)+1,transcribe_token=uuid.uuid4().hex,render_token=None,frame_count=0)
        save_job(job)
    pool.submit(transcribe_job,job['id'],data.model,data.language,job['transcribe_token']);return job_of(job['id'])
@app.get('/api/jobs/{id}')
def status(id:str):return how2sign.refresh_human_timing(job_of(id))
@app.get('/api/jobs')
def list_jobs():
    with db() as c:jobs=[json.loads(r['data']) for r in c.execute('SELECT data FROM jobs ORDER BY rowid DESC LIMIT 100')]
    return [{k:job.get(k) for k in ['id','name','kind','duration','status']} for job in jobs
            if job.get('name') and job.get('ext') and (STORE/job['id']/f"input{job['ext']}").is_file()]
@app.post('/api/jobs/{id}/replan')
def replan(id:str):
    job=job_of(id)
    if job['status'] not in ['ready','done','failed','cancelled'] or not job['segments']:raise HTTPException(409,'Avval nutqni tayyorlang.')
    result=how2sign.translate_asl('',job['segments'],job['duration']) if job.get('language')=='en' else translate('',job['segments'],signs())
    return update(id,translation=result)
@app.get('/api/jobs/{id}/media')
def media(id:str):
    job=job_of(id);path=STORE/id/f"input{job.get('ext','')}"
    if not path.is_file():raise HTTPException(404,'Original media fayli topilmadi.')
    return FileResponse(path)
class RenderSessionRequest(BaseModel):
    token:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')

@app.post('/api/jobs/{id}/cancel')
def cancel(id:str,data:RenderSessionRequest|None=None):
    with lock:
        job=job_of(id)
        if data and data.token and (job.get('render_token')!=data.token or job['status'] not in ['frames','rendering','queued']):raise HTTPException(409,'Eksport sessiyasi o‘zgargan yoki yakunlangan.')
        if job['status'] not in ['queued','processing','frames','rendering']:raise HTTPException(409,'Faol jarayon yo‘q. Tayyor natija saqlandi.')
        cancelled.add(id);job.update(status='cancelled',phase='Bekor qilindi');save_job(job)
    return job
class RenderSettings(BaseModel):
    avatar_model:Literal['legacy','rocketbox']='legacy'
    motion_revision:Literal['arm-reference-v2','relaxed-idle-v3','bounded-cadence-v4','signing-frame-v5','jaw-retarget-v6','aligned-motion-v7','adaptive-cadence-v8','wrist-transition-v9']|None=None
    appearance:Literal['navy-v1']|None=None
    close_panel:bool=False
    native_human:bool=False
    cropMode:Literal['center','full']='center'
    removeGreen:bool=True
    engine:Literal['human','neural']='human'
    layout:Literal['side_by_side','overlay']='side_by_side'
    resolution:Literal[720,1080]=720
    size:float=Field(default=.3,ge=.2,le=.45)
    position:Literal['right','left']='right'
    subtitles:bool=True
    capture_quality:Literal['standard','high']='standard'
@app.post('/api/jobs/{id}/render/start')
def render_start(id:str,settings:RenderSettings):
    job=job_of(id)
    if job['status'] not in ['ready','done','failed','cancelled'] or job.get('translation') is None:raise HTTPException(409,'Avval nutqni tahlil qiling.')
    if settings.engine=='human' and job.get('language')=='en':
        rejected={c['id'] for c in how2sign.catalog() if c.get('review_decision')=='rejected'}
        if any(i.get('sign_id') in rejected for i in job['translation']['items']):
            raise HTTPException(409,'Qamrovdagi klip keyinroq rad etilgan. Qamrovni yangilash tugmasini bosing.')
        job=how2sign.refresh_human_timing(job)
    use_native=False
    if settings.engine=='human' and settings.native_human:
        from .human_render import native_items
        try:use_native=len(native_items(job))<=24
        except ValueError as e:raise HTTPException(409,str(e))
    if settings.avatar_model=='rocketbox' and settings.engine!='neural':raise HTTPException(422,'Yangi avatar uchun ML harakati kerak.')
    if settings.capture_quality=='high' and settings.avatar_model!='rocketbox':raise HTTPException(422,'Yuqori aniqlik hozirgi 3D avatar uchun qo‘llanadi.')
    scale=1.;neural_summary=None;unsupported_intervals=[]
    if settings.engine=='neural':
        from .neural_api import plan
        motion_plan=plan(id);scale=motion_plan['timing_scale']
        unsupported_intervals=[{'start':item['start'],'end':item['end']} for item in motion_plan.get('items',[]) if item.get('unsupported')]
        neural_summary={key:motion_plan.get(key,0) for key in ['generated_phrases','unsupported_phrases','caption_words','total_words']}
        neural_summary['partial']=bool(neural_summary['unsupported_phrases'])
    render_fps=24 if settings.avatar_model=='rocketbox' else FPS
    if settings.avatar_model=='rocketbox' and settings.motion_revision in ('adaptive-cadence-v8','wrist-transition-v9'):
        render_fps=rocketbox_capture_fps(motion_plan.get('items', []))
    count=math.ceil(job['duration']*scale*render_fps)
    # Claim a session only after validation; two tabs must not both start from
    # the same ready snapshot and overwrite each other's render token.
    with lock:
        latest=job_of(id)
        if latest['status'] not in ['ready','done','failed','cancelled'] or latest.get('segments')!=job.get('segments') or latest.get('transcript_revision',0)!=job.get('transcript_revision',0):
            raise HTTPException(409,'Ish boshqa oynada o‘zgargan yoki eksport boshlangan. Sahifani yangilang.')
        try:ensure_render_space(STORE,0 if use_native else count,job['duration']*scale)
        except ValueError as exc:raise HTTPException(507,str(exc)) from exc
        cancelled.discard(id);token=uuid.uuid4().hex;folder=STORE/id/token;folder.mkdir()
        history=latest.get('previous_results',[])
        previous=latest.get('result_token')
        if previous and not any(record.get('token')==previous for record in history):
            history=[*history,{'token':previous,'settings':latest.get('settings'),'transcript_revision':latest.get('transcript_revision',0)}]
        latest.update(error=None,resume_frames=False,status='queued' if use_native else 'frames',phase='Inson videosi bevosita yig‘ilmoqda' if use_native else 'Avatar kadrlari tayyorlanmoqda',progress=0,render_token=token,frame_count=count,render_fps=render_fps,settings=settings.model_dump(),timing_scale=scale,output_duration=job['duration']*scale,previous_results=history)
        latest['neural_summary']=neural_summary
        if settings.engine=='human':
            latest['translation']=job['translation']
        latest['render_unsupported_intervals']=unsupported_intervals
        save_job(latest)
    if use_native:
        pool.submit(render_human_job,id,token)
        return {'token':token,'frames':0,'fps':24,'mode':'native'}
    return {'token':token,'frames':count,'fps':render_fps}

class ResumeRenderRequest(RenderSettings):
    token:str=Field(pattern=r'^[a-f0-9]{32}$')

def frame_size(job):
    settings=job.get('settings',{})
    return ((1024,768) if settings.get('capture_quality')=='high' else (512,384)) if settings.get('avatar_model')=='rocketbox' else (384,512)

@app.post('/api/jobs/{id}/render/resume')
def render_resume(id:str,data:ResumeRenderRequest):
    settings=data.model_dump(exclude={'token'})
    def eligible(job):
        return (job.get('render_token')==data.token and job.get('settings')==settings
                and (job['status']=='frames' or job['status']=='failed' and job.get('resume_frames') is True))
    job=job_of(id)
    if not eligible(job):raise HTTPException(409,'Davom ettirish sozlamalari yoki eksport sessiyasi mos emas.')
    if settings.get('engine')=='human' and how2sign.has_stale_timing(job):
        raise HTTPException(409,'Manba klipi vaqti yangilangan. Qamrovni yangilab, MP4 eksportini boshidan boshlang.')
    count=job.get('frame_count',0);fps=job.get('render_fps',0)
    if not isinstance(count,int) or not 0<count<=144000 or fps not in (12,24,30):
        raise HTTPException(409,'Saqlangan kadr sessiyasi yaroqsiz. Qayta eksport qiling.')
    folder=STORE/id/data.token
    if not folder.is_dir():raise HTTPException(409,'Saqlangan kadrlar topilmadi. Qayta eksport qiling.')
    # A stopped server may have left a partial write. Validate the contiguous
    # prefix outside the job lock; the first missing/corrupt frame is recaptured.
    next_frame=0
    for index in range(count):
        path=folder/f'{index:06d}.png'
        try:
            if path.stat().st_size>1024*1024:break
            validate_png_frame(path.read_bytes(),frame_size(job))
        except (OSError,ValueError):break
        next_frame=index+1
    with lock:
        latest=job_of(id)
        if not eligible(latest):raise HTTPException(409,'Eksport boshqa oynada o‘zgargan.')
        # Transfer ownership before admitting new uploads. Late writes, finish
        # and cancel from the disconnected tab must not touch the resumed job.
        token=uuid.uuid4().hex
        root=(STORE/id).resolve();destination=root/token
        if folder.resolve().parent!=root or destination.resolve().parent!=root:
            raise HTTPException(409,'Kadr sessiyasining yo‘li yaroqsiz.')
        folder.rename(destination)
        cancelled.discard(id)
        latest.update(render_token=token,status='frames',resume_frames=False,error=None,phase='Avatar kadrlari davom ettirilmoqda')
        save_job(latest)
    return {'token':token,'frames':count,'fps':fps,'next_frame':next_frame}

def render_human_job(id,token=None):
    from .human_render import compose
    try:
        token=token or job_of(id)['render_token'];check(id,token)
        job=update(id,expected_render_token=token,status='rendering',phase='Inson videosi yig‘ilmoqda',progress=1)
        info=compose(job,lambda ident:check(ident,token),lambda p:update(id,expected_render_token=token,progress=p))
        check(id,token);update(id,expected_render_token=token,status='done',error=None,phase='Inson tarjimonli MP4 tayyor',progress=100,result_token=token,probe=info)
    except Exception as e:fail(id,e,token)
@app.put('/api/jobs/{id}/frames/{token}/{index}')
async def frame(id:str,token:str,index:int,request:Request,repeat:int=1):
    job=job_of(id)
    if job['status']!='frames' or job.get('render_token')!=token or not 0<=index<job['frame_count']:raise HTTPException(409,'Kadr sessiyasi yaroqsiz.')
    if not 1 <= repeat <= 48 or index + repeat > job['frame_count']:
        raise HTTPException(422,'Kadr oralig‘i yaroqsiz.')
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>1024*1024:raise HTTPException(413,'Kadr juda katta.')
    expected=frame_size(job)
    try:validate_png_frame(raw,expected)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    with lock:
        latest=job_of(id)
        if latest['status']!='frames' or latest.get('render_token')!=token:raise HTTPException(409,'Kadr sessiyasi o‘zgargan.')
        for frame_index in range(index, index + repeat):
            target=STORE/id/token/f'{frame_index:06d}.png'
            temporary=target.with_suffix('.tmp');temporary.write_bytes(raw);os.replace(temporary,target)
    return {'ok':True}
def timestamp(t):
    ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
def render_job(id,token=None):
    folder=None;proc=None
    try:
        job=job_of(id);token=token or job['render_token'];check(id,token)
        folder=STORE/id/token
        check(id,token);settings=job['settings'];h=settings['resolution'];w=h*16//9;aw=round(w*settings['size']/2)*2
        scale=job.get('timing_scale',1.);out_duration=job.get('output_duration',job['duration'])
        srt='\n\n'.join(f"{i+1}\n{timestamp(s['start']*scale)} --> {timestamp(s['end']*scale)}\n{s['text'].replace(chr(10),' ')}" for i,s in enumerate(job['segments']))
        if settings.get('engine')=='neural':
            # Keep provenance visible in the output, independently of subtitle toggle.
            srt=f"1\n00:00:00,000 --> {timestamp(out_duration)}\nML yaratgan ASL harakati - tasdiqlanmagan\n\n"+srt
            for item in job.get('render_unsupported_intervals',[]):
                srt+=f"\n\n1\n{timestamp(item['start'])} --> {timestamp(item['end'])}\nAvatar ijrosi yo‘q — subtitr bilan beriladi"
        (folder/'captions.srt').write_text(srt,encoding='utf-8')
        (folder/'captions.ass').write_text(make_ass(job,w,h),encoding='utf-8')
        args=[binary('ffmpeg'),'-y','-hide_banner','-loglevel','error','-i',str(STORE/id/f"input{job['ext']}")]
        output_fps=max(24,job.get('render_fps',FPS))
        if job['kind']=='audio':args+=['-f','lavfi','-i',f'color=c=0x101629:s={w}x{h}:r={output_fps}']
        ai=2 if job['kind']=='audio' else 1
        args+=['-framerate',str(job.get('render_fps',FPS)),'-i',str(folder/'%06d.png')]
        base='1:v' if job['kind']=='audio' else '0:v'
        x='W-w-24' if settings['position']=='right' else '24'
        if job['kind']=='audio':
            ratio=384/512 if settings.get('avatar_model')=='rocketbox' else 512/384
            avatar_h=min(h,round(aw*ratio/2)*2)
            graph=f'[{base}]setsar=1[bg];[{ai}:v]scale={aw}:{avatar_h}[av];[bg][av]overlay=(W-w)/2:(H-h)/2:eof_action=repeat'
        elif settings.get('layout','side_by_side')=='side_by_side':
            main_width=w-aw
            ratio=384/512 if settings.get('avatar_model')=='rocketbox' else 512/384
            avatar_h=min(h,round(aw*ratio/2)*2)
            # Keep the signing figure at its established scale inside a narrower panel.
            figure_width = aw
            if settings.get('avatar_model') == 'rocketbox' and settings.get('close_panel'):
                figure_width = max(aw, round(w * .4 / 2) * 2)
                avatar_h = round(figure_width * ratio / 2) * 2
            graph=f'[{base}]scale={main_width}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:({main_width}-iw)/2:(oh-ih)/2:color=black,setsar=1[bg];[{ai}:v]scale={figure_width}:{avatar_h},crop={aw}:ih[av];[bg][av]overlay={main_width}:(H-h)/2:eof_action=repeat'
        else:
            graph=f'[{base}]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1[bg];[{ai}:v]scale={aw}:-1[av];[bg][av]overlay={x}:H-h-24:eof_action=repeat'
        if settings['subtitles'] or settings.get('engine')=='neural':graph+=',ass=captions.ass'
        graph+='[out]'
        # Normalize the source clock. If its video track ends before its audio,
        # retain the last source frame while the avatar and original audio finish.
        pace=f'[{base}]setpts={scale:.10f}*(PTS-STARTPTS)'
        if job['kind']=='video':
            # Overlay runs on its background clock. Rate-converting only after
            # overlay used to discard hand poses from low-FPS screen recordings.
            pace+=f',tpad=stop_mode=clone:stop_duration={out_duration:.10f},fps={output_fps}'
        graph=pace+'[paced];'+graph.replace(f'[{base}]','[paced]')
        args+=['-filter_complex',graph,'-map','[out]','-map','0:a:0']
        if scale!=1:args+=['-af',tempo_filters(scale)]
        credit='SignBridge UZ local research composite; original audio preserved/re-encoded.'
        if settings.get('engine')=='neural':
            credit+=' Avatar: Microsoft Rocketbox Female Adult 01, MIT; https://github.com/microsoft/Microsoft-Rocketbox .' if settings.get('avatar_model')=='rocketbox' else ''
            if settings.get('motion_revision'):credit+=f" Retargeting revision: {settings['motion_revision']}."
            credit+=' Motion model: MaDiS / How2Sign; https://github.com/2000ZRL/MaDiS ; model license CC-BY-NC-ND-4.0. Experimental retargeted 3D output, unverified.'
        elif any(i.get('video_url') for i in (job.get('translation') or {}).get('items',[])):
            credit+=' ASL recordings: How2Sign, Amanda Duarte et al., CVPR 2021; https://how2sign.github.io/ ; CC-BY-NC-4.0. Changes: crop, chroma key, temporal alignment, video composition.'
        args+=['-metadata','title=SignBridge UZ research result','-metadata',f'comment={credit}']
        args+=['-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-r',str(output_fps),'-c:a','aac','-b:a','160k','-t',str(out_duration),'-movflags','+faststart','-progress','pipe:1',str(folder/'result.mp4')]
        update(id,expected_render_token=token,status='rendering',phase='MP4 yig‘ilmoqda',progress=70)
        with (folder/'ffmpeg.log').open('w') as log:
            proc=subprocess.Popen(args,cwd=folder,stdout=subprocess.PIPE,stderr=log,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            for line in proc.stdout:
                check(id,token)
                if line.startswith('out_time_us='):
                    try:update(id,expected_render_token=token,progress=min(99,70+int(29*int(line.split('=')[1])/1e6/out_duration)))
                    except ValueError:pass
            if proc.wait()!=0:raise RuntimeError('FFmpeg eksporti bajarilmadi; ish jurnalini tekshiring.')
        check(id,token);info=probe(folder/'result.mp4')
        from .export_validation import validate_export
        verified=validate_export(info,out_duration,w,h,probe(STORE/id/f"input{job['ext']}"),scale,expected_fps=output_fps)
        check(id,token)
        update(id,expected_render_token=token,status='done',error=None,phase='MP4 tayyor',progress=100,result_token=job['render_token'],probe=verified)
    except Exception as e:fail(id,e,token)
    finally:
        if proc and proc.poll() is None:proc.kill();proc.wait()
        if folder is not None:
            for png in folder.glob('*.png'):png.unlink()
@app.post('/api/jobs/{id}/render/finish')
def render_finish(id:str,data:RenderSessionRequest|None=None):
    with lock:
        job=job_of(id)
        if job['status']!='frames' or data and data.token and data.token!=job.get('render_token'):raise HTTPException(409,'Kadr sessiyasi faol emas yoki o‘zgargan.')
        if (job.get('settings') or {}).get('engine')=='human' and how2sign.has_stale_timing(job):
            raise HTTPException(409,'Manba klipi vaqti yangilangan. Joriy eksportni bekor qilib, MP4 eksportini boshidan boshlang.')
        folder=STORE/id/job['render_token']
        if any(not (folder/f'{i:06d}.png').exists() for i in range(job['frame_count'])):raise HTTPException(409,'Barcha kadrlar yuklanmagan.')
        job.update(status='queued',phase='Eksport navbatda');save_job(job)
    pool.submit(render_job,id,job['render_token']);return job_of(id)
@app.get('/api/jobs/{id}/result')
@app.get('/api/jobs/{id}/download')
def result(id:str,v:str|None=None):
    job=job_of(id)
    if v is None:
        if job['status']!='done':raise HTTPException(409,'MP4 hali tayyor emas.')
        token=job.get('result_token')
    else:
        allowed={r.get('token') for r in job.get('previous_results',[])}
        # result_token is assigned only after a successful export. render_token
        # alone does not grant access to a partial output.
        if job.get('result_token'):allowed.add(job['result_token'])
        if v not in allowed:raise HTTPException(404,'Eksport versiyasi topilmadi.')
        token=v
    if not isinstance(token,str) or not re.fullmatch('[a-f0-9]{32}',token):raise HTTPException(404,'Eksport versiyasi topilmadi.')
    base=(STORE/id).resolve();path=(base/token/'result.mp4').resolve()
    if not path.is_relative_to(base) or not path.is_file():raise HTTPException(404,'MP4 fayli topilmadi. Qayta eksport qiling.')
    return FileResponse(path,media_type='video/mp4',filename=f'SignBridge-{id[:8]}-{token[:8]}.mp4',headers={'Cache-Control':'no-store','X-Export-Version':token})
