"""Read-only, bounded inventory. Never extracts or trains on evaluation media."""
import csv
import zipfile
from functools import lru_cache
from pathlib import Path, PurePosixPath
from fastapi import APIRouter
from . import how2sign

router=APIRouter(prefix='/api/how2sign')
MAX_ROWS=100_000

@lru_cache(maxsize=12)
def metadata(path,size,mtime):
    if size>24*1024*1024:raise ValueError('CSV hajmi chegaradan katta.')
    names=set();rows=0
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream,delimiter='\t')
        if not {'SENTENCE_NAME','SENTENCE'}.issubset(reader.fieldnames or []):raise ValueError('CSV ustunlari mos emas.')
        for row in reader:
            rows+=1
            if rows>MAX_ROWS:raise ValueError('CSV qator chegarasi oshdi.')
            name=row['SENTENCE_NAME']
            if not name or '/' in name or '\\' in name or ':' in name or name in names:raise ValueError('CSV klip nomlari takrorlangan yoki yaroqsiz.')
            names.add(name+'.mp4')
    return frozenset(names)

@lru_cache(maxsize=12)
def archive(path,size,mtime):
    names=set();duplicates=0
    with zipfile.ZipFile(path) as bundle:
        if len(bundle.infolist())>MAX_ROWS*2:raise ValueError('ZIP yozuvlari chegarasi oshdi.')
        for item in bundle.infolist():
            p=PurePosixPath(item.filename)
            if item.is_dir() or p.suffix.lower()!='.mp4':continue
            if p.is_absolute() or '..' in p.parts or '\\' in item.filename or ':' in item.filename or item.flag_bits&1:raise ValueError('ZIP klip yo‘li yaroqsiz yoki shifrlangan.')
            if p.name in names:duplicates+=1
            names.add(p.name)
    return frozenset(names),duplicates

def signature(path):
    stat=path.stat()
    return str(path.resolve()),stat.st_size,stat.st_mtime_ns

def inspect_split(base,roots,split):
    result={'split':split,'state':'missing','csv_rows':None,'archive_clips':None,
            'matched_clips':None,'missing_clips':None,'extra_clips':None,'downloads_in_progress':0,
            'training_performed':False,'crc_checked':False,'role':'held_out_evaluation' if split=='test' else 'retrieval_reference'}
    csv_path=base/f'how2sign_{split}.csv'
    names=None
    try:
        if csv_path.is_file():names=metadata(*signature(csv_path));result['csv_rows']=len(names)
        candidates=[]
        for root in roots:
            if not root.is_dir():continue
            result['downloads_in_progress']+=sum(1 for p in root.glob(f'{split}_rgb_front_clips*.zip.*') if p.suffix.lower() in {'.crdownload','.part','.partial','.download'})
            candidates.extend(sorted(root.glob(f'{split}_rgb_front_clips*.zip'))[:20])
        # A partial sibling means the writer may still be modifying this file.
        candidates=[p for p in candidates if p.is_file() and not any(Path(str(p)+ext).exists() for ext in ['.crdownload','.part','.partial','.download'])]
        if not candidates:
            result['state']='downloading' if result['downloads_in_progress'] else 'metadata_only' if names is not None else 'missing'
            return result
        last_error=None
        for path in candidates:
            try:
                sig=signature(path);videos,duplicates=archive(*sig)
                if sig!=signature(path):raise ValueError('ZIP hali o‘zgarayapti.')
                result.update(archive_name=path.name,archive_bytes=sig[1],archive_clips=len(videos),duplicate_names=duplicates)
                if names is None:result['state']='metadata_missing'
                else:
                    missing=len(names-videos);extra=len(videos-names)
                    result.update(matched_clips=len(names&videos),missing_clips=missing,extra_clips=extra,
                                  state='incomplete' if missing or duplicates else 'indexed')
                return result
            except (OSError,ValueError,zipfile.BadZipFile):last_error='ZIP ochilmadi yoki uning katalogi yaroqsiz. Yuklanish tugashini tekshiring.'
        result.update(state='invalid',message=last_error)
    except (OSError,ValueError,csv.Error,UnicodeError):result.update(state='invalid',message='CSV yoki dataset fayllari tekshirilishi kerak.')
    return result

def inventory(base=None,roots=None):
    base=Path(base) if base is not None else how2sign.BASE
    roots=list(dict.fromkeys([base,*([Path.home()/'Downloads',base.anchor and Path(base.anchor)] if roots is None else roots)]))
    return {'splits':[inspect_split(base,roots,s) for s in ['train','val','test']],
            'checks':'zip_directory_and_csv_names_only','extracted':False,'training_performed':False}

@router.get('/dataset/status')
def status():return inventory()
