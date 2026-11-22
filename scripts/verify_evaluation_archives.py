"""Read all validation/test archive payloads for CRC integrity, without extraction."""
import argparse,gzip,json,time,zipfile,zlib
from pathlib import Path

def verify(base,output,splits=('val','test'),suffixes=('rgb_front_clips.zip','rgb_side_clips.zip','2D_keypoints.tar.gz')):
    if not splits or any(s not in {'train','val','test'} for s in splits):raise ValueError('Unknown dataset split')
    if output.exists():raise ValueError('Choose a new report filename')
    report={'extracted':False,'training_started':False,'archives':[]}
    for split in splits:
        for suffix in suffixes:
            path=base/f'{split}_{suffix}';started=time.monotonic()
            record={'file':path.name,'complete':False,'uncompressed_bytes_read':0}
            def account(amount):
                record['uncompressed_bytes_read']+=amount
                if record['uncompressed_bytes_read']>64*1024**3:raise ValueError('64 GiB uncompressed limit exceeded')
                if time.monotonic()-started>600:raise TimeoutError('10 minute per-archive limit exceeded')
            try:
                record['archive_bytes']=path.stat().st_size;record['archive_mtime_ns']=path.stat().st_mtime_ns
                if path.suffix=='.zip':
                    with zipfile.ZipFile(path) as bundle:
                        members=bundle.infolist()
                        if len(members)>200000:raise ValueError('Too many ZIP entries')
                        record['files_read']=0
                        record['failed_entries']=[]
                        for member in members:
                            if member.is_dir():continue
                            try:
                                with bundle.open(member) as stream:
                                    while block:=stream.read(1024*1024):account(len(block))
                            except (zipfile.BadZipFile,EOFError,zlib.error) as exc:
                                record['failed_entries'].append({'member':member.filename,'error':str(exc)})
                            record['files_read']+=1
                    record['check']='ZIP per-entry CRC, all file payloads'
                else:
                    with gzip.open(path,'rb') as stream:
                        while block:=stream.read(8*1024*1024):account(len(block))
                    record['check']='Full gzip stream CRC; tar JSON schemas not fully parsed'
                record['all_payloads_checked']=True
                record['complete']=not record.get('failed_entries')
            except (OSError,ValueError,RuntimeError,zipfile.BadZipFile,EOFError,TimeoutError,zlib.error) as exc:record['error']=str(exc)
            record['elapsed_seconds']=round(time.monotonic()-started,3);report['archives'].append(record)
            partial=output.with_suffix('.progress.json')
            partial.parent.mkdir(parents=True,exist_ok=True)
            partial.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(record),flush=True)
    report['all_complete']=all(r['complete'] for r in report['archives'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--splits',nargs='+',choices=['train','val','test'],default=['val','test']);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    result=verify(root/'datasets/how2sign',args.output,args.splits)
    raise SystemExit(0 if result['all_complete'] else 1)
