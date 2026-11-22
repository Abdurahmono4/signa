"""Bounded validation/test inspection; no training, retrieval import or full extraction."""
import argparse,csv,hashlib,json,math,sys,zipfile
from pathlib import Path,PurePosixPath
import av
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.core import probe
from scripts.prepare_keypoint_sample import prepare

def inspect(base,output,clips=3):
    if output.exists():raise ValueError('Choose a new inspection folder')
    if not 1<=clips<=5:raise ValueError('Choose 1–5 samples')
    output.mkdir(parents=True)
    report={'training_started':False,'full_archives_extracted':False,'splits':{},'csv_root_comparison':{}}
    for source in Path(base.anchor).glob('how2sign*.csv'):
        target=base/source.name
        if target.is_file():report['csv_root_comparison'][source.name]=hashlib.sha256(source.read_bytes()).hexdigest()==hashlib.sha256(target.read_bytes()).hexdigest()
    for split in ['val','test']:
        with (base/f'how2sign_{split}.csv').open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream,delimiter='\t'))
        metadata={r['SENTENCE_NAME']:r for r in rows};folder=output/split;folder.mkdir()
        keypoints=prepare(base/f'{split}_2D_keypoints.tar.gz',base/f'how2sign_{split}.csv',folder/'keypoints',limit=clips,split=split,max_scan_bytes=4*1024**3)
        sampled={r['sentence_name']:r for r in keypoints['clips']}
        result={'csv_rows':len(rows),'keypoint_sample':{'clips':len(sampled),'frames':sum(r['frames'] for r in sampled.values()),'issues':len(keypoints['issues']),'full_archive_scanned':keypoints['full_archive_scanned']},'views':{}}
        for view in ['front','side']:
            archive=base/f'{split}_rgb_{view}_clips.zip'
            if not archive.is_file():archive=Path.home()/'Downloads'/archive.name
            if not archive.is_file():result['views'][view]={'available':False};continue
            entries={};duplicates=set();unsafe=[]
            with zipfile.ZipFile(archive) as bundle:
                for member in bundle.infolist():
                    if member.is_dir() or not member.filename.lower().endswith('.mp4'):continue
                    name=PurePosixPath(member.filename)
                    if name.is_absolute() or '..' in name.parts or ':' in member.filename or '\\' in member.filename or member.flag_bits&1:
                        unsafe.append(member.filename);continue
                    if name.name in entries:duplicates.add(name.name)
                    else:entries[name.name]=member
                filenames={name:name.removesuffix('-rgb_front')+f'-rgb_{view}.mp4' for name in metadata}
                wanted=set(filenames.values());available=set(entries)-duplicates
                summary={'available':True,'archive_name':archive.name,'archive_bytes':archive.stat().st_size,'unique_videos':len(entries),'matched_csv':len(wanted&available),
                         'missing_csv_names':sorted(wanted-available),'extra_names':sorted(available-wanted),'duplicate_names':sorted(duplicates),'unsafe_members':unsafe,'full_crc_checked':False,'samples':[]}
                selected=[name for name in sampled if filenames[name] in available]
                selected+= [name for name in metadata if name not in selected and filenames[name] in available]
                view_folder=folder/view;view_folder.mkdir()
                for name in selected[:clips]:
                    item=entries[filenames[name]];record={'sentence_name':name,'csv_text':metadata[name]['SENTENCE'],'crc_checked':False,'decoded':False}
                    try:
                        if item.file_size>128*1024*1024:raise ValueError('Sample exceeds 128 MiB')
                        target=view_folder/(hashlib.sha256(name.encode()).hexdigest()[:24]+'.mp4')
                        with bundle.open(item) as source,target.open('xb') as dest:
                            total=0
                            while block:=source.read(1024*1024):
                                total+=len(block)
                                if total>item.file_size or total>128*1024*1024:raise ValueError('Sample byte limit exceeded')
                                dest.write(block)
                        if total!=item.file_size:raise ValueError('Sample size mismatch')
                        record['crc_checked']=True
                        info=probe(target);duration=float(info['format']['duration'])
                        if not math.isfinite(duration) or not 0<duration<=300:raise ValueError('Sample duration invalid')
                        count=0;last=None
                        with av.open(str(target)) as container:
                            stream=container.streams.video[0];fps=float(stream.average_rate)
                            for frame in container.decode(video=0):
                                count+=1
                                if count>10000:raise ValueError('Sample frame limit exceeded')
                                if frame.pts is None:raise ValueError('Frame PTS absent')
                                at=float(frame.pts*frame.time_base)
                                if last is not None and at<=last:raise ValueError('Non-increasing PTS')
                                last=at
                        if not count:raise ValueError('No decoded frames')
                        record.update(decoded=True,frames=count,fps=fps,duration=duration,file=str(target.resolve()))
                        if name in sampled:record.update(keypoint_frames=sampled[name]['frames'],same_frame_count=count==sampled[name]['frames'])
                    except (OSError,ValueError,RuntimeError,zipfile.BadZipFile) as exc:record['error']=str(exc)
                    summary['samples'].append(record)
            result['views'][view]=summary
        report['splits'][split]=result
    report['limitations']=['ZIP central directories and CSV names compared; full-archive CRC not performed.','Only selected videos fully decoded. Tar/keypoints are bounded-prefix samples.','Equal frame counts do not establish temporal or linguistic alignment.','Test data stays held out; no model fitting or retrieval import performed.']
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--clips',type=int,default=3);args=parser.parse_args()
    result=inspect(ROOT/'datasets/how2sign',args.output,args.clips)
    for split,data in result['splits'].items():
        print(json.dumps({'split':split,'csv_rows':data['csv_rows'],'keypoints':data['keypoint_sample'],'views':{v:{'matched_csv':r.get('matched_csv'),'missing':len(r.get('missing_csv_names',[])),'decoded':sum(s['decoded'] for s in r.get('samples',[]))} for v,r in data['views'].items()}},ensure_ascii=False))
