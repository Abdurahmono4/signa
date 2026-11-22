"""Exact phrase index over a local train ZIP, with selected clips cached lazily.

Indexing is not model training. Durations are probed only when a clip is selected;
original CSV intervals are hints and are never claimed to be video durations.
"""
import csv,hashlib,json,math,os,re,threading,zipfile
from functools import lru_cache
from pathlib import Path,PurePosixPath
from .core import probe
from .translation import normalize

MAX_CLIP=200*1024*1024
MAX_CACHE=2*1024*1024*1024
_guard=threading.RLock()

def exclusions(base,archive):
    path=base/'train-exclusions.json'
    if not path.is_file():return frozenset(),None
    stat=path.stat()
    if stat.st_size>2*1024*1024:raise ValueError('Integrity exclusions exceed size limit')
    data=json.loads(path.read_text(encoding='utf-8'));source=archive.stat()
    if data.get('archive_bytes')!=source.st_size or data.get('archive_mtime_ns')!=source.st_mtime_ns:return frozenset(),(stat.st_size,stat.st_mtime_ns)
    members=data.get('members')
    if not isinstance(members,list) or len(members)>100000 or not all(isinstance(m,str) for m in members):raise ValueError('Invalid integrity exclusions')
    return frozenset(members),(stat.st_size,stat.st_mtime_ns)

def _inputs(base):
    base=Path(base).resolve();archive=base/'train_rgb_front_clips.zip';metadata=base/'how2sign_train.csv'
    if not archive.is_file() or not metadata.is_file():return None
    stat=archive.stat();csv_stat=metadata.stat()
    _,excluded_signature=exclusions(base,archive)
    return base,archive,metadata,(str(base),stat.st_size,stat.st_mtime_ns,csv_stat.st_size,csv_stat.st_mtime_ns,excluded_signature)

def _safe_member(member):
    name=PurePosixPath(member.filename)
    return (not member.is_dir() and not name.is_absolute() and '..' not in name.parts and '\\' not in member.filename
            and ':' not in member.filename and member.filename.lower().endswith('.mp4') and 0<member.file_size<=MAX_CLIP
            and not (member.flag_bits&1))

@lru_cache(maxsize=2)
def _load(signature):
    base=Path(signature[0]);archive=base/'train_rgb_front_clips.zip';metadata=base/'how2sign_train.csv'
    fingerprint=hashlib.sha256(json.dumps(signature).encode()).hexdigest()[:20]
    path=base/'train-index-v1.json';records=None
    try:
        if path.stat().st_size<=32*1024*1024:
            cached=json.loads(path.read_text(encoding='utf-8'))
            # JSON turns the nested exclusions tuple into a list as well.
            # Compare the serialized form so a new process can reuse the index.
            if cached.get('signature')==json.loads(json.dumps(signature)):records=cached['records']
    except (OSError,ValueError,KeyError):pass
    missing=0;duplicates=set()
    if records is None:
        with zipfile.ZipFile(archive) as z:
            members={}
            for member in z.infolist():
                if not _safe_member(member):continue
                name=PurePosixPath(member.filename).name
                if name in members:duplicates.add(name)
                else:members[name]=member
        records=[];seen=set()
        with metadata.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f,delimiter='\t'):
                name=row['SENTENCE_NAME']+'.mp4';member=members.get(name)
                if not member or name in duplicates:missing+=1;continue
                ident=hashlib.sha256(name.encode()).hexdigest()[:24]
                if ident in seen:continue
                text=row['SENTENCE'].strip();hint=float(row['END'])-float(row['START'])
                if not text or not math.isfinite(hint) or hint<=0:continue
                records.append({'id':ident,'text':text,'sentence_name':row['SENTENCE_NAME'],
                                'member':member.filename,'bytes':member.file_size,'duration_hint':hint})
                seen.add(ident)
        payload={'signature':list(signature),'records':records,'missing_rows':missing,'duplicate_names':len(duplicates)}
        temp=path.with_suffix('.tmp')
        with temp.open('w',encoding='utf-8') as f:
            json.dump(payload,f,ensure_ascii=False,separators=(',',':'));f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    else:
        missing=cached.get('missing_rows',0);duplicates=set(range(cached.get('duplicate_names',0)))
    denied,_=exclusions(base,archive)
    byid={};lookup={}
    for record in records:
        if record.get('member') in denied:continue
        if not re.fullmatch('[a-f0-9]{24}',record.get('id','')):continue
        key=tuple(normalize(record['text']).split())
        if not key:continue
        byid[record['id']]=record;lookup.setdefault(key,[]).append(record)
    first_lengths={}
    for key in lookup:first_lengths.setdefault(key[0],set()).add(len(key))
    return {'byid':byid,'lookup':lookup,'lengths':frozenset(map(len,lookup)),
            'first_lengths':{word:frozenset(lengths) for word,lengths in first_lengths.items()},
            'fingerprint':fingerprint,'missing_rows':missing,'duplicate_names':len(duplicates),'archive':archive,'base':base,'excluded_corrupt_clips':sum(r.get('member') in denied for r in records)}

def index(base):
    inputs=_inputs(base)
    if inputs is None:return None
    with _guard:return _load(inputs[3])

def status(base):
    try:
        data=index(base)
        if data is None:return {'available':False,'records':0,'split':'train','training_performed':False}
        cache=data['base']/'train-cache'/data['fingerprint']
        cached=list(cache.glob('*.mp4')) if cache.exists() else []
        return {'available':True,'records':len(data['byid']),'missing_rows':data['missing_rows'],'excluded_corrupt_clips':data['excluded_corrupt_clips'],
                'duplicate_names':data['duplicate_names'],'split':'train','language':'asl','verified':False,
                'source':'https://how2sign.github.io/','license':'CC-BY-NC-4.0','training_performed':False,
                'cached_clips':len(cached),'cache_bytes':sum(p.stat().st_size for p in cached),
                'cache_limit_bytes':MAX_CACHE,'full_archive_extracted':False}
    except (OSError,ValueError,KeyError,zipfile.BadZipFile):
        return {'available':False,'records':0,'error':'Train ZIP/CSV indeksi olinmadi. Mahalliy fayllarni tekshiring.','training_performed':False}

def candidates(base,key):
    data=index(base)
    return data['lookup'].get(key,()) if data else ()

def lengths(base):
    data=index(base)
    return data['lengths'] if data else frozenset()

def contains(base,ident):
    data=index(base)
    return bool(data and ident in data['byid'])

def resolve(base,ident):
    if not re.fullmatch('[a-f0-9]{24}',ident):raise ValueError('Klip identifikatori yaroqsiz.')
    data=index(base)
    if not data or ident not in data['byid']:raise ValueError('Train klipi topilmadi.')
    record=data['byid'][ident]
    with _guard:
        cache=data['base']/'train-cache'/data['fingerprint'];cache.mkdir(parents=True,exist_ok=True)
        path=cache/f'{ident}.mp4'
        if not path.resolve().is_relative_to(cache.resolve()):raise ValueError('Klip yo‘li yaroqsiz.')
        if not path.exists():
            used=sum(p.stat().st_size for p in cache.glob('*.mp4'))
            if used+record['bytes']>MAX_CACHE:raise ValueError('Train keshining 2 GB chegarasi to‘ldi; administrator tekshiruvi kerak.')
            temporary=path.with_suffix('.tmp')
            try:
                with zipfile.ZipFile(data['archive']) as z:
                    member=z.getinfo(record['member'])
                    expected=hashlib.sha256(PurePosixPath(member.filename).name.encode()).hexdigest()[:24]
                    if not _safe_member(member) or expected!=ident or member.file_size!=record['bytes']:raise ValueError('ZIP klipi indeks bilan mos emas.')
                    with z.open(member) as source,temporary.open('wb') as target:
                        total=0
                        while chunk:=source.read(1024*1024):
                            total+=len(chunk)
                            if total>MAX_CLIP or total>member.file_size:raise ValueError('ZIP klipi juda katta.')
                            target.write(chunk)
                    if total!=member.file_size:raise ValueError('ZIP klipi to‘liq emas.')
                os.replace(temporary,path)
            finally:temporary.unlink(missing_ok=True)
        return _probed(str(path),path.stat().st_size,path.stat().st_mtime_ns,record['id'],record['text'],record['sentence_name'])

@lru_cache(maxsize=2048)
def _probed(path,size,mtime,ident,text,sentence_name):
    info=probe(path);duration=float(info['format']['duration'])
    stream=next((s for s in info['streams'] if s['codec_type']=='video'),None)
    if stream is None or not .05<duration<=300:raise ValueError('Train klipi video/davomiyligi yaroqsiz.')
    return {'id':ident,'text':text,'sentence_name':sentence_name,'duration':duration,'language':'asl','split':'train',
            'verified':False,'source':'https://how2sign.github.io/','license':'CC-BY-NC-4.0',
            'video_url':f'/api/how2sign/train/clips/{ident}','technical_valid':True,
            'width':stream['width'],'height':stream['height'],'alignment':'Original clip; manual review required',
            '_local_path':path}
