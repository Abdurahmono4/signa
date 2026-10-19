"""Local research API. Speech transcription is real; ASL production is not enabled."""
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from threading import Lock, Event
from typing import Literal
import gc
import json
import logging
import os
import sqlite3
import uuid

import av
from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from . import asr
from . import signs
from . import neural

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("SIGNA_DATA_DIR", str(ROOT / "data")))
MODEL_PROFILES = {'balanced':'small.en', 'accurate':'medium.en'}
MAX_BYTES = 100 * 1024 * 1024
MAX_SECONDS = 20 * 60
EXTENSIONS = {".mp4", ".mov", ".webm", ".mp3", ".wav", ".m4a", ".ogg", ".flac"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
worker_lock = Lock()
model = None
loaded_profile = None
cancel_events = {}
logger = logging.getLogger("signa")


@contextmanager
def connect():
    db = sqlite3.connect(DATA / "jobs.sqlite3", timeout=20)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def init_db():
    DATA.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, name TEXT, path TEXT, kind TEXT, size INTEGER,
            duration REAL, status TEXT, error TEXT, segments TEXT,
            created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )""")
        existing = {row[1] for row in db.execute('PRAGMA table_info(jobs)')}
        for name, declaration in {'progress':'INTEGER DEFAULT 0','phase':"TEXT DEFAULT 'idle'",
                                  'report':"TEXT DEFAULT '{}'",'settings':"TEXT DEFAULT '{}'",
                                  'revision':'INTEGER DEFAULT 0'}.items():
            if name not in existing:
                db.execute(f'ALTER TABLE jobs ADD COLUMN {name} {declaration}')
        db.execute('''CREATE TABLE IF NOT EXISTS revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, segments TEXT, report TEXT,
            settings TEXT, reason TEXT, created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )''')
        signs.init_signs(db)
        db.execute("UPDATE jobs SET status='failed', error=? WHERE status IN ('queued','processing')",
                   ("Server qayta ishga tushdi. Qayta ishlashni yana boshlang.",))


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield
    neural.shutdown()


app = FastAPI(title="Signa research API", version="0.2.0", lifespan=lifespan)
app.include_router(signs.router)


def model_ready(profile='accurate'):
    path = ROOT / 'models' / MODEL_PROFILES[profile]
    return all((path/name).is_file() for name in ['model.bin','config.json','tokenizer.json'])


def public_job(row):
    result = dict(row)
    result.pop("path", None)
    # Correct old cover-art classifications in API responses without rewriting
    # the uploaded file or its stored job history.
    if Path(result.get('name') or '').suffix.lower() in AUDIO_EXTENSIONS:
        result['kind'] = 'audio'
    result["segments"] = json.loads(result["segments"] or "[]")
    result['report'] = json.loads(result.get('report') or '{}')
    result['settings'] = json.loads(result.get('settings') or '{}')
    result["asl_status"] = neural.status(DATA, row)['status'] if row['status'] == 'ready' else 'not_available'
    return result


def media_kind(media, extension):
    # MP3/M4A album covers are exposed by FFmpeg as video streams. They must
    # keep the audio player; a still attached picture is never a video track.
    if extension.lower() in AUDIO_EXTENSIONS:
        return 'audio'
    attached_picture = av.stream.Disposition.attached_pic
    return 'video' if any(not (stream.disposition & attached_picture)
                          for stream in media.streams.video) else 'audio'


def get_row(job_id):
    with connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Fayl topilmadi.")
    return row


def ensure_avatar_idle(row):
    if neural.status(DATA, row)['status'] in {'queued', 'processing'}:
        raise HTTPException(409, 'Avval avatar tayyorlanishini yakunlang yoki bekor qiling.')


@app.get("/api/health")
def health():
    return {"status": "ok", "model_ready": any(model_ready(p) for p in MODEL_PROFILES),
            "model": "Whisper medium.en / small.en", 'version':'0.2.0',
            'profiles':[{'id':p,'model':name,'ready':model_ready(p)} for p,name in MODEL_PROFILES.items()],
            "input_language": "en", "asl_ready": neural.readiness(ROOT)['ready'],
            "neural": neural.readiness(ROOT), "max_mb": 100, "max_minutes": 20}


def release_speech_model():
    global model, loaded_profile
    model = None
    loaded_profile = None
    gc.collect()


@app.get('/api/neural/status')
def neural_status():
    return neural.readiness(ROOT)


@app.get('/api/jobs/{job_id}/neural')
def neural_job_status(job_id: str):
    return neural.status(DATA, get_row(job_id))


@app.post('/api/jobs/{job_id}/neural', status_code=202)
def generate_neural(job_id: str):
    row = get_row(job_id)
    if row['status'] != 'ready':
        raise HTTPException(409, 'Avval nutq matnini tayyorlang.')
    if not neural.readiness(ROOT)['ready']:
        raise HTTPException(503, 'ASL modeli hali o‘rnatilmoqda. Yuklash tugagach qayta ijro eting.')
    try:
        return neural.enqueue(ROOT, DATA, row, worker_lock, release_speech_model)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post('/api/jobs/{job_id}/neural/cancel')
def cancel_neural(job_id: str):
    if not neural.cancel(get_row(job_id)):
        raise HTTPException(409, 'Avatar hozir tayyorlanmayapti.')
    return {'status': 'cancelling'}


@app.get('/api/jobs/{job_id}/neural/plan')
def neural_plan(job_id: str):
    row = get_row(job_id)
    path = neural.folder(DATA, row) / 'plan.json'
    if not path.is_file():
        raise HTTPException(409, 'Avatar ijrosi hali tayyor emas.')
    return FileResponse(path, media_type='application/json')


@app.get('/api/jobs/{job_id}/neural/motions/{motion_id}')
def neural_motion(job_id: str, motion_id: int, key: str):
    row = get_row(job_id)
    if key != neural.key_for(row):
        raise HTTPException(409, 'Nutq o‘zgargan. Avatarni qayta tayyorlang.')
    base = neural.folder(DATA, row) / 'motion'
    index_path = base / 'index.json'
    if not index_path.is_file():
        raise HTTPException(404, 'Harakat hali tayyor emas.')
    index = json.loads(index_path.read_text(encoding='utf-8'))
    motion = next((item for item in index['motions'] if str(item['id']) == str(motion_id)), None)
    if not motion:
        raise HTTPException(404, 'Harakat topilmadi.')
    path = Path(motion['motion_json'])
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise HTTPException(404, 'Harakat fayli topilmadi.')
    return FileResponse(path, media_type='application/json')


@app.get("/api/jobs")
def list_jobs():
    with connect() as db:
        rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100").fetchall()
    return [public_job(row) for row in rows]


@app.get("/api/jobs/{job_id}")
def read_job(job_id: str):
    return public_job(get_row(job_id))


@app.get('/api/jobs/{job_id}/sign-plan')
def sign_plan(job_id: str, include_source: bool = False):
    row=get_row(job_id)
    if row['status']!='ready':
        raise HTTPException(409,'Avval matnni tayyorlang.')
    return signs.lexical_plan(json.loads(row['segments']), include_source=include_source)


@app.get('/api/jobs/{job_id}/playback-plan')
def playback_plan(job_id: str, include_source: bool = False, fingerspelling: bool = False):
    row=get_row(job_id)
    if row['status']!='ready':
        raise HTTPException(409,'Avval matnni tayyorlang.')
    return {'job_id':job_id,'revision':row['revision'],
            **signs.playback_plan(json.loads(row['segments']),row['duration'],include_source=include_source,
                                  fingerspelling=fingerspelling)}


@app.post("/api/jobs", status_code=201)
async def upload(file: UploadFile):
    name = (file.filename or "media").replace("\\", "/").split("/")[-1][:200]
    extension = Path(name).suffix.lower()
    if extension not in EXTENSIONS:
        raise HTTPException(415, "MP4, MOV, WEBM, MP3, WAV, M4A, OGG yoki FLAC fayl tanlang.")
    job_id = uuid.uuid4().hex
    path = DATA / (job_id + extension)
    size = 0
    try:
        with path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, "Fayl hajmi 100 MB dan oshmasligi kerak.")
                target.write(chunk)
        if size == 0:
            raise HTTPException(400, "Fayl bo‘sh.")
        try:
            with av.open(str(path)) as media:
                if not media.streams.audio:
                    raise ValueError("no audio")
                duration = (media.duration or 0) / av.time_base
                if duration <= 0:
                    raise ValueError("unknown duration")
                if duration > MAX_SECONDS:
                    raise HTTPException(413, "Fayl davomiyligi 20 daqiqadan oshmasligi kerak.")
                kind = media_kind(media, extension)
                next(media.decode(audio=0))
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(422, "Audio yo‘lagi o‘qilmadi. Haqiqiy, buzilmagan media fayl yuklang.") from exc
        with connect() as db:
            db.execute("INSERT INTO jobs (id,name,path,kind,size,duration,status,segments) VALUES (?,?,?,?,?,?,?,?)",
                       (job_id, name, str(path), kind, size, duration, "uploaded", "[]"))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return public_job(get_row(job_id))


def snapshot(db, row, reason):
    if json.loads(row['segments'] or '[]'):
        db.execute('INSERT INTO revisions (job_id,segments,report,settings,reason) VALUES (?,?,?,?,?)',
                   (row['id'],row['segments'],row['report'],row['settings'],reason))


def transcribe(job_id, options):
    global model, loaded_profile
    with worker_lock:
        with connect() as db:
            db.execute("UPDATE jobs SET status='processing',phase='loading',error=NULL WHERE id=?", (job_id,))
        try:
            if model is None or loaded_profile != options.profile:
                from faster_whisper import WhisperModel
                model = None
                gc.collect()
                path = ROOT / 'models' / MODEL_PROFILES[options.profile]
                model = WhisperModel(str(path), device="cpu", compute_type="int8", cpu_threads=6,
                                     local_files_only=True)
                loaded_profile = options.profile
            row = get_row(job_id)
            def update(phase, percent, segments, report):
                with connect() as db:
                    db.execute('UPDATE jobs SET phase=?,progress=?,segments=?,report=? WHERE id=?',
                               (phase,percent,json.dumps(segments),json.dumps(report),job_id))
            result, report = asr.run_pipeline(model, row['path'], options.mode, progress=update,
                                              cancelled=cancel_events[job_id].is_set)
            if cancel_events[job_id].is_set():
                raise asr.Cancelled()
            report['model'] = MODEL_PROFILES[options.profile]
            with connect() as db:
                db.execute("UPDATE jobs SET status='ready',phase='done',progress=100,segments=?,report=? WHERE id=?",
                           (json.dumps(result),json.dumps(report),job_id))
        except asr.Cancelled:
            with connect() as db:
                db.execute("UPDATE jobs SET status='cancelled',phase='cancelled' WHERE id=?", (job_id,))
        except Exception:
            logger.exception("Transcription failed for %s", job_id)
            with connect() as db:
                db.execute("UPDATE jobs SET status='failed',error=? WHERE id=?",
                           ("Nutqni aniqlash tugamadi. Qisman natija saqlandi; qayta urinib ko‘ring.", job_id))
        finally:
            cancel_events.pop(job_id,None)


class TranscriptionOptions(BaseModel):
    profile: Literal['balanced','accurate'] = 'accurate'
    mode: Literal['speech','music'] = 'speech'


@app.post("/api/jobs/{job_id}/transcribe", status_code=202)
def start_transcription(job_id: str, background: BackgroundTasks, options: TranscriptionOptions = TranscriptionOptions()):
    ensure_avatar_idle(get_row(job_id))
    if not model_ready(options.profile):
        raise HTTPException(503, "Tanlangan model o‘rnatilmagan. scripts/setup-model.ps1 faylini ishga tushiring.")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM jobs WHERE status IN ('queued','processing')").fetchone():
            raise HTTPException(409, "Boshqa fayl qayta ishlanmoqda. Yakunlanishini kuting.")
        row = db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        snapshot(db,row,'before_transcription')
        db.execute("UPDATE jobs SET status='queued',phase='queued',progress=0,error=NULL,segments='[]',report='{}',settings=?,revision=revision+1 WHERE id=?",
                   (options.model_dump_json(),job_id))
    cancel_events[job_id] = Event()
    background.add_task(transcribe, job_id, options)
    return public_job(get_row(job_id))


@app.post('/api/jobs/{job_id}/cancel')
def cancel(job_id: str):
    row = get_row(job_id)
    if row['status'] not in {'queued','processing'} or job_id not in cancel_events:
        raise HTTPException(409,'Bu ish hozir qayta ishlanmayapti.')
    cancel_events[job_id].set()
    return {'message':'Joriy bo‘lak tugagach to‘xtaydi. Qisman natija saqlanadi.'}


class SegmentEdit(BaseModel):
    start: float = Field(ge=0,le=MAX_SECONDS)
    end: float = Field(gt=0,le=MAX_SECONDS+1)
    text: str = Field(min_length=1,max_length=4000)


class TranscriptEdit(BaseModel):
    revision: int = Field(ge=0)
    segments: list[SegmentEdit] = Field(min_length=1,max_length=10000)


@app.put('/api/jobs/{job_id}/transcript')
def edit_transcript(job_id: str, payload: TranscriptEdit):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if row is None:
            raise HTTPException(404,'Fayl topilmadi.')
        ensure_avatar_idle(row)
        if row['status'] in {'queued','processing'} or row['revision'] != payload.revision:
            raise HTTPException(409,'Natija o‘zgargan yoki qayta ishlanmoqda. Yangilang.')
        previous_end = 0
        segments = []
        for item in payload.segments:
            if not item.text.strip() or item.end <= item.start or item.start < previous_end or item.end > row['duration']+.5:
                raise HTTPException(422,'Vaqtlar ketma-ket, matn bo‘sh bo‘lmasin va oraliq fayl davomiyligidan oshmasin.')
            previous_end = item.end
            segments.append({**item.model_dump(),'text':item.text.strip(),'words':[], 'needs_review':False,'edited':True})
        snapshot(db,row,'before_edit')
        report = json.loads(row['report'] or '{}')
        report['manual_edit'] = True
        report['audit_stale'] = True
        db.execute("UPDATE jobs SET segments=?,report=?,revision=revision+1,status='ready',phase='edited',error=NULL WHERE id=?",
                   (json.dumps(segments),json.dumps(report),job_id))
    return public_job(get_row(job_id))


@app.get('/api/jobs/{job_id}/revisions')
def revisions(job_id: str):
    get_row(job_id)
    with connect() as db:
        return [dict(row) for row in db.execute('SELECT id,reason,created_at FROM revisions WHERE job_id=? ORDER BY id DESC',(job_id,))]


@app.post('/api/jobs/{job_id}/revisions/{revision_id}/restore')
def restore(job_id: str, revision_id: int):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        old = db.execute('SELECT * FROM revisions WHERE id=? AND job_id=?',(revision_id,job_id)).fetchone()
        if row is None or old is None:
            raise HTTPException(404,'Versiya topilmadi.')
        ensure_avatar_idle(row)
        if row['status'] in {'queued','processing'}:
            raise HTTPException(409,'Avval qayta ishlash tugashini kuting.')
        snapshot(db,row,'before_restore')
        db.execute("UPDATE jobs SET segments=?,report=?,settings=?,status='ready',phase='restored',error=NULL,revision=revision+1 WHERE id=?",
                   (old['segments'],old['report'],old['settings'],job_id))
    return public_job(get_row(job_id))


@app.get("/api/jobs/{job_id}/media")
def media_file(job_id: str):
    row = get_row(job_id)
    return FileResponse(row["path"])


def timestamp(seconds, separator=","):
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{milliseconds:03}"


@app.get("/api/jobs/{job_id}/subtitles")
def subtitles(job_id: str, format: str = "srt"):
    if format not in {"srt", "vtt", "txt"}:
        raise HTTPException(400, "srt, vtt yoki txt formatini tanlang.")
    row = get_row(job_id)
    if row["status"] != "ready":
        raise HTTPException(409, "Subtitr hali tayyor emas.")
    segments = json.loads(row["segments"])
    if format == "txt":
        content = "\n".join(s["text"] for s in segments)
    else:
        separator = "." if format == "vtt" else ","
        content = "WEBVTT\n\n" if format == "vtt" else ""
        for index, segment in enumerate(segments, 1):
            content += f"{index}\n{timestamp(segment['start'], separator)} --> {timestamp(segment['end'], separator)}\n{segment['text']}\n\n"
    return Response(content, media_type="text/vtt" if format == "vtt" else "text/plain",
                    headers={"Content-Disposition": f'attachment; filename="signa-{job_id}.{format}"'})


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(job_id: str):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Fayl topilmadi.")
        ensure_avatar_idle(row)
        if row["status"] in {"queued", "processing"}:
            raise HTTPException(409, "Avval qayta ishlash tugashini kuting.")
        Path(row["path"]).unlink(missing_ok=True)
        db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        db.execute('DELETE FROM revisions WHERE job_id=?',(job_id,))
