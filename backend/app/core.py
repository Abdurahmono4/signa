import json,os,sqlite3,shutil,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ASSETS=Path(os.environ.get('SIGNBRIDGE_ASSETS',str(ROOT/'assets')))
STORE=Path(os.environ.get('SIGNBRIDGE_STORAGE',str(ROOT/'storage')))
STORE.mkdir(parents=True,exist_ok=True)
def db():
    c=sqlite3.connect(STORE/'metadata.db',timeout=30);c.row_factory=sqlite3.Row;return c
def initialize():
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS signs (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS corpus_reviews (id TEXT PRIMARY KEY, decision TEXT, reviewer TEXT, notes TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        c.execute('CREATE TABLE IF NOT EXISTS corpus_review_history (event_id INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT, decision TEXT, reviewer TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        demo={'id':'demo-asl-hello','label':'Hello — ASL texnik namuna','gloss':'HELLO','language':'asl','verified':False,
              'animation_path':'/assets/animations/demo-asl-hello.json','duration_ms':2200,
              'source':'https://github.com/StudioGalt/Sign-Language-Mocap-Archive','license':'CC0-1.0',
              'reviewer':None,'keypoint_reference':None,'notes':'O‘zbek tarjimasi uchun qo‘llanmaydi.'}
        c.execute('INSERT OR IGNORE INTO signs VALUES (?,?)',(demo['id'],json.dumps(demo)))
def save_job(job):
    with db() as c:c.execute('INSERT OR REPLACE INTO jobs VALUES (?,?)',(job['id'],json.dumps(job,ensure_ascii=False)))
def get_job(id):
    with db() as c:r=c.execute('SELECT data FROM jobs WHERE id=?',(id,)).fetchone()
    return json.loads(r[0]) if r else None
def signs():
    with db() as c:return [json.loads(r[0]) for r in c.execute('SELECT data FROM signs')]
def binary(name):
    path=shutil.which(name)
    if path:return path
    files=list((ROOT/'tools').glob(f'**/{name}.exe'))
    if not files:raise RuntimeError(f'{name} o‘rnatilmagan. tools papkasini tekshiring.')
    return str(files[0])
def probe(path):
    r=subprocess.run([binary('ffprobe'),'-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if r.returncode:raise ValueError('Media ochilmadi yoki buzilgan.')
    return json.loads(r.stdout)
