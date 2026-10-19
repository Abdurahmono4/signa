"""Download only pinned CPU/ASL assets, resume exact ranges, verify SHA-256."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import threading
import time
import urllib.parse
import urllib.request
import zipfile

MANIFEST_PATH=Path(__file__).with_name('neural-model-manifest.json')
CHUNK=16*1024*1024
_log_lock=threading.Lock()


def log(*values):
    with _log_lock:
        print(*values,flush=True)


def verified(path,record):
    if not path.is_file() or path.stat().st_size!=record['size']:
        return False
    digest=hashlib.sha256()
    with path.open('rb') as handle:
        for data in iter(lambda:handle.read(8*1024*1024),b''):
            digest.update(data)
    return digest.hexdigest()==record['sha256']


def download_file(directory,record,url,workers):
    target=directory/record['path']
    if verified(target,record):
        log('VERIFIED',target.name,record['size']);return target
    directory.mkdir(parents=True,exist_ok=True)
    parts=directory/'range-parts'/record['path']
    parts.mkdir(parents=True,exist_ok=True)
    jobs=[(index,start,min(record['size'],start+CHUNK)-1)
          for index,start in enumerate(range(0,record['size'],CHUNK))]

    def fetch(job):
        index,start,end=job
        part=parts/f'{index:04}.part'
        length=end-start+1
        if part.is_file() and part.stat().st_size==length:
            return
        for attempt in range(5):
            try:
                offset=part.stat().st_size if part.is_file() else 0
                if offset>=length:
                    offset=0
                request=urllib.request.Request(url,headers={
                    'Range':f'bytes={start+offset}-{end}',
                    'User-Agent':'Signa-verified-model-setup/1'})
                with urllib.request.urlopen(request,timeout=90) as response:
                    actual=response.headers.get('Content-Range','')
                    expected=f'bytes {start+offset}-{end}/{record["size"]}'
                    # Tiny files may be returned as one complete 200 response.
                    whole=response.status==200 and start==0 and offset==0 and end+1==record['size']
                    if not whole and (response.status!=206 or actual!=expected):
                        raise RuntimeError(f'Unexpected HTTP range: {response.status} {actual}')
                    with part.open('ab' if offset else 'wb') as handle:
                        remaining=length-offset
                        while remaining:
                            data=response.read(min(256*1024,remaining))
                            if not data:
                                break
                            handle.write(data);remaining-=len(data)
                if part.stat().st_size!=length:
                    raise RuntimeError('Incomplete download range')
                log('RANGE',target.name,index+1,'/',len(jobs));return
            except Exception as error:
                log('RETRY',target.name,index,attempt+1,type(error).__name__)
                if attempt==4:
                    raise
                time.sleep(min(8,attempt+1))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for result in as_completed([pool.submit(fetch,job) for job in jobs]):
            result.result()
    assembled=target.with_name(target.name+'.assembled')
    with assembled.open('wb') as output:
        for index,_,_ in jobs:
            with (parts/f'{index:04}.part').open('rb') as handle:
                for data in iter(lambda:handle.read(4*1024*1024),b''):
                    output.write(data)
    if not verified(assembled,record):
        raise RuntimeError(f'{target.name}: size/SHA-256 verification failed; no model was activated')
    assembled.replace(target)
    log('VERIFIED',target.name,record['sha256'])
    return target


def extract_qwen(archive,destination):
    root=destination.resolve()
    with zipfile.ZipFile(archive) as handle:
        for entry in handle.infolist():
            logical=PurePosixPath(entry.filename.replace('\\','/'))
            target=(root/Path(*logical.parts)).resolve()
            if (logical.is_absolute() or '..' in logical.parts or ':' in entry.filename
                    or not target.is_relative_to(root)
                    or stat.S_ISLNK(entry.external_attr>>16)):
                raise ValueError('Unsafe language-model archive path')
        handle.extractall(root)
    qwen=root/'Qwen3-0.6B-Base-en-zh-de'
    if not (qwen/'config.json').is_file() or not (qwen/'map_ids.pkl').is_file():
        raise ValueError('The extracted language-model package is incomplete')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-root',type=Path,default=Path(__file__).resolve().parents[1]/'backend/models/MaDiS')
    parser.add_argument('--torch',action='store_true',help='Fetch the pinned Windows Python3.11 CPU wheel only')
    parser.add_argument('--workers',type=int,default=6,choices=range(1,17))
    parser.add_argument('--verify-only',action='store_true',help='Read-only asset/hash validation; never downloads')
    args=parser.parse_args()
    manifest=json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    root=args.model_root.resolve()
    if args.torch:
        record=manifest['torch'];directory=root/'runtime/wheels'
        if args.verify_only:
            if not verified(directory/record['path'],record):
                raise SystemExit('Pinned CPU wheel is missing or invalid')
        else:
            download_file(directory,record,record['url'],args.workers)
        return
    assets=root/'assets'
    base=f'https://huggingface.co/{manifest["repository"]}/resolve/{manifest["revision"]}/'
    for record in manifest['files']:
        if args.verify_only:
            if not verified(assets/record['path'],record):
                raise SystemExit(f'Model asset missing or invalid: {record["path"]}')
        else:
            download_file(assets,record,base+urllib.parse.quote(record['path'])+'?download=true',args.workers)
    if not args.verify_only:
        extract_qwen(assets/'Qwen3-0.6B-Base-en-zh-de.zip',assets)
        (assets/'download-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    log('ALL REQUIRED ASL FILES VERIFIED; no SMPL-X model assets downloaded')


if __name__=='__main__':
    main()
