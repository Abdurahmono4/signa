"""Small, attributed research subset. Original recordings, never synthetic translations."""
import csv,hashlib,json,re,threading,zipfile,os
from functools import lru_cache
from copy import deepcopy
from pathlib import Path
from .core import ROOT,probe,db
from .translation import normalize
from .clip_alignment import original_clip_conflicts
from . import realigned_clips
BASE=Path(os.environ.get('SIGNBRIDGE_DATASET',str(ROOT/'datasets'/'how2sign')))
CLIPS=BASE/'clips'
guard=threading.Lock()
state={'phase':'ZIP kutilmoqda','error':None}

@lru_cache(maxsize=2)
def _catalog_file(path,mtime,size):
    return json.loads(Path(path).read_text(encoding='utf-8'))

@lru_cache(maxsize=8192)
def _phrase_tokens(text):
    return tuple(normalize(text).split())

def catalog():
    path=BASE/'catalog.json'
    if path.exists():
        stat=path.stat()
        records=deepcopy(_catalog_file(str(path.resolve()),stat.st_mtime_ns,stat.st_size))
    else:records=[]
    import sqlite3
    try:
        with db() as c:reviews={r['id']:dict(r) for r in c.execute('SELECT * FROM corpus_reviews')}
    except sqlite3.OperationalError:reviews={}
    for record in records:
        review=reviews.get(record['id'])
        record.update(review_decision=review['decision'] if review else 'unreviewed',reviewer=review['reviewer'] if review else None,review_notes=review['notes'] if review else None)
        record['verified']=bool(review and review['decision']=='approved')
    return records

def import_available():
    if not guard.acquire(blocking=False):return
    try:
        BASE.mkdir(parents=True,exist_ok=True);CLIPS.mkdir(exist_ok=True)
        metadata=BASE/'how2sign_val.csv'
        if not metadata.exists():return
        archives=list(BASE.glob('val_rgb_front_clips*.zip'))+list((Path.home()/'Downloads').glob('val_rgb_front_clips*.zip'))
        if not archives:
            state.update(phase='ZIP kutilmoqda',error=None);return
        archive=archives[0]
        # Chrome partial files are not considered; an incomplete ZIP is retried.
        if not zipfile.is_zipfile(archive):
            state.update(phase='ZIP hali tayyor emas',error=None);return
        signature={'archive_bytes':archive.stat().st_size,'archive_mtime':archive.stat().st_mtime_ns,'metadata_bytes':metadata.stat().st_size,'version':2}
        marker=BASE/'import-complete.json'
        if marker.exists() and json.loads(marker.read_text())==signature:
            state.update(phase=f'{len(catalog())} ta manba klipi tayyor',error=None,progress=100);return
        state.update(phase='Barcha kliplar import qilinmoqda',error=None,progress=0)
        with metadata.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter='\t'))
        previous={c['id']:c for c in catalog()};output=[];issues=[]
        from concurrent.futures import ThreadPoolExecutor
        with zipfile.ZipFile(archive) as z:
            members={Path(x.filename).name:x for x in z.infolist() if not x.is_dir() and x.filename.lower().endswith('.mp4')}
            state['archive_videos']=len(members)
            matched=[r for r in rows if r['SENTENCE_NAME']+'.mp4' in members]
            def prepare(row):
                name=row['SENTENCE_NAME']+'.mp4';member=members[name]
                id=hashlib.sha256(name.encode()).hexdigest()[:24];target=CLIPS/f'{id}.mp4'
                try:
                    if member.file_size>200*1024*1024:raise ValueError('Klip 200 MB dan katta')
                    if not target.exists() or target.stat().st_size!=member.file_size:
                        raw=z.read(member)
                        if len(raw)!=member.file_size:raise ValueError('ZIP CRC yoki hajm mos emas')
                        target.write_bytes(raw)
                    info=probe(target);actual=float(info['format']['duration'])
                    stream=next(s for s in info['streams'] if s['codec_type']=='video')
                    if not .05<actual<=300:raise ValueError('Davomiylik yaroqsiz')
                    expected=float(row['END'])-float(row['START'])
                    return {'id':id,'text':row['SENTENCE'],'sentence_name':row['SENTENCE_NAME'],
                        'duration':actual,'language':'asl','verified':False,'source':'https://how2sign.github.io/',
                        'license':'CC-BY-NC-4.0','video_url':f'/api/how2sign/clips/{id}',
                        'width':stream['width'],'height':stream['height'],'technical_valid':True,
                        'alignment_delta':round(abs(actual-expected),3),
                        'alignment':'Original timestamp; manual review required'},None
                except Exception as e:return None,{'sentence_name':row['SENTENCE_NAME'],'reason':str(e)[:160]}
            with ThreadPoolExecutor(max_workers=4) as workers:
                for index,(record,issue) in enumerate(workers.map(prepare,matched)):
                    if record:output.append(record)
                    if issue:issues.append(issue)
                    state.update(progress=round(100*(index+1)/max(1,len(matched))),processed=index+1,imported=len(output),rejected=len(issues),total=len(matched))
                    if (index+1)%50==0:
                        temporary=BASE/'catalog.tmp';temporary.write_text(json.dumps(output,ensure_ascii=False),encoding='utf-8');temporary.replace(BASE/'catalog.json')
            names={r['SENTENCE_NAME']+'.mp4' for r in matched}
            unmatched=sorted(set(members)-names)
        temporary=BASE/'catalog.tmp';temporary.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(BASE/'catalog.json')
        (BASE/'technical-audit.json').write_text(json.dumps({'archive_videos':len(members),'csv_rows':len(rows),'matched_rows':len(matched),'valid_clips':len(output),'issues':issues,'unmatched_files':unmatched,'linguistic_verified':0},ensure_ascii=False,indent=2),encoding='utf-8')
        marker.write_text(json.dumps(signature),encoding='utf-8')
        state.update(phase=f'{len(output)} ta manba klipi tayyor',error=None,progress=100)
    except (OSError,ValueError,zipfile.BadZipFile,RuntimeError):
        state.update(phase='Import qayta tekshiriladi',error='ZIP yuklanishi tugaganini va fayl nomini tekshiring.')
    finally:guard.release()

def translate_asl(text,segments=None,media_duration=None):
    from . import train_catalog
    val_conflicts=original_clip_conflicts(BASE,'val')
    train_conflicts=original_clip_conflicts(BASE,'train')
    lookup={}
    for record in catalog():
        if record.get('review_decision')=='rejected' or record.get('technical_valid') is False:continue
        key=_phrase_tokens(record['text'])
        if key:lookup.setdefault(key,[]).append(record)
    tokens=[]
    for segment in segments or [{'text':text,'start':0,'end':max(3,len(text.split())*.5)}]:
        words=segment.get('words') or []
        if words and normalize(' '.join(w['word'] for w in words))==normalize(segment['text']):
            for word in words:
                for token in normalize(word['word']).split():tokens.append((token,word['start'],word['end']))
        else:
            parts=normalize(segment['text']).split();step=(segment['end']-segment['start'])/max(1,len(parts))
            tokens.extend((word,segment['start']+i*step,segment['start']+(i+1)*step) for i,word in enumerate(parts))
    # Train metadata remains separate from the validation-only browser catalog.
    # Read its cached index once, then resolve only exact candidate recordings.
    try:train=train_catalog.index(BASE)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile):train=None
    train_lookup=train['lookup'] if train else {}
    # Only consider lengths of phrases that actually start with this word.
    # Keep longest-first matching and the same timing/review selection rules.
    first_lengths=dict(train['first_lengths']) if train else {}
    for key in lookup:
        first_lengths[key[0]]=first_lengths.get(key[0],frozenset())|{len(key)}
    first_lengths={word:sorted(lengths,reverse=True) for word,lengths in first_lengths.items()}
    resolved={};items=[];i=0;covered=0;preview_cursor=0.;conflict_end=0
    def corrected(split,ident,window,slot,available):
        if window is None:
            return None
        if segments and not .5*slot-.1 <= window.end-window.start <= 2*available+.1:
            return None
        key=(split,ident)
        if key not in resolved:resolved[key]=realigned_clips.recover(BASE,split,window)
        return resolved[key]
    while i<len(tokens):
        found=None;count=1;signing_length=None
        for n in first_lengths.get(tokens[i][0],()):
            if n>len(tokens)-i:continue
            key=tuple(t[0] for t in tokens[i:i+n])
            if len(key)!=n or key not in lookup and key not in train_lookup:continue
            slot=max(.001,tokens[i+n-1][2]-tokens[i][1])
            # A recording may finish in silence. Stop at the next spoken word or media end.
            boundary=tokens[i+n][1] if i+n<len(tokens) else media_duration
            if media_duration is not None and boundary is not None:boundary=min(boundary,media_duration)
            available=max(slot,boundary-tokens[i][1]) if boundary is not None else slot
            candidates=[]
            def consider(record):
                if record is None:return
                length=slot
                if record.get('timing_source')=='manual_realignment':
                    length=max(slot,min(available,record['duration']))
                rate=record['duration']/length
                if segments is None or .5<=rate<=2:
                    candidates.append((record,length,abs(rate-1)))
            for record in lookup.get(key,()):
                if record['id'] in val_conflicts and not record.get('verified'):
                    conflict_end=max(conflict_end,i+n)
                    record=corrected('val',record['id'],val_conflicts[record['id']],slot,available)
                consider(record)
            # Existing suitable validation media wins; do not extract train
            # duplicates when a working recording is already available.
            if not candidates:
                for candidate in train_lookup.get(key,()):
                    ident=candidate['id']
                    if ident in train_conflicts:
                        conflict_end=max(conflict_end,i+n)
                        record=corrected('train',ident,train_conflicts[ident],slot,available)
                    else:
                        if ident not in resolved:
                            try:resolved[ident]=train_catalog.resolve(BASE,ident)
                            except (OSError,ValueError,KeyError,zipfile.BadZipFile,RuntimeError):resolved[ident]=None
                        record=resolved[ident]
                    consider(record)
            if candidates:
                # Prefer expert-reviewed recordings, then the closest natural pace.
                found,signing_length,_=min(candidates,key=lambda c:(not c[0].get('verified',False),c[2],c[0]['id']))
                count=n;break
        start=tokens[i][1];end=tokens[i+count-1][2]
        # Text-only preview uses the recorded clip's natural speed.
        if segments is None:
            start=preview_cursor;end=start+(found['duration'] if found else count*.5);preview_cursor=end
        elif found and found.get('timing_source')=='manual_realignment':
            end=start+signing_length
        safe=bool(found and .5<=found['duration']/max(.001,end-start)<=2)
        covered+=count if safe else 0
        items.append({'text':' '.join(t[0] for t in tokens[i:i+count]),'start':start,'end':end,
            'supported':safe,'sign_id':found['id'] if safe else None,'animation_path':None,
            'video_url':found['video_url'] if safe else None,'duration_ms':round(found['duration']*1000) if safe else None,
            'verified':bool(safe and found.get('verified')),'language':'asl','source':'How2Sign' if safe else None,
            'timing_source':found.get('timing_source','original_clip') if safe else None,
            'split':found.get('split','validation') if safe else None,'license':found.get('license','CC-BY-NC-4.0') if safe else None,
            'reason':'ASL manba videosi tuzatilgan vaqt bo‘yicha kesilgan.' if safe and found.get('timing_source')=='manual_realignment' else
                     'ASL manba videosi · vaqt va ma’no tekshiruvi kerak' if safe else
                     'Manba klipi tuzatilgan vaqt yoki matnga mos kelmadi. Subtitr ko‘rsatiladi.' if i<conflict_end else
                     'Mos to‘liq ibora yoki mos ijro tezligi yo‘q; subtitr'} )
        i+=count
    return {'items':items,'coverage':round(100*covered/max(1,len(tokens))),'supported_words':covered,
        'total_words':len(tokens),'confidence_kind':'Manba iborasi mosligi; mustaqil lingvistik tasdiq emas','language':'asl'}


def has_stale_timing(job):
    if job.get('language')!='en' or not job.get('translation'):
        return False
    selected={i['sign_id'] for i in job['translation']['items'] if i.get('supported') and i.get('sign_id')}
    if not selected:
        return False
    train=original_clip_conflicts(BASE,'train')
    val=original_clip_conflicts(BASE,'val')
    if selected.intersection(train):
        return True
    flagged=selected.intersection(val)
    if not flagged:
        return False
    approved={r['id'] for r in catalog() if r.get('verified')}
    return bool(flagged-approved)


def refresh_human_timing(job):
    if not has_stale_timing(job):
        return job
    captions=job.get('segments') or [i for i in job['translation']['items']
                                      if i.get('text') and 'start' in i and 'end' in i]
    return {**job,'translation':translate_asl('',captions,job.get('duration'))}

def resolve_record(ident):
    """Resolve an existing validation or exact indexed train recording."""
    if not re.fullmatch('[a-f0-9]{24}',ident):raise ValueError('Klip identifikatori yaroqsiz.')
    if corrected:=realigned_clips.cached(BASE,ident):
        return corrected
    record=next((c for c in catalog() if c['id']==ident),None)
    if record:
        if record.get('review_decision')=='rejected':raise ValueError('Klip mutaxassis tomonidan rad etilgan.')
        return {**record,'split':'validation'}
    from . import train_catalog
    return dict(train_catalog.resolve(BASE,ident))

def resolve_clip(ident):
    record=resolve_record(ident)
    if '_local_path' in record:return Path(record['_local_path'])
    path=CLIPS/f'{ident}.mp4'
    if not path.is_file():raise ValueError('Tarjimon klipi fayli yo‘q.')
    return path
