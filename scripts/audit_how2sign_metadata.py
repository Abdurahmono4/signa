"""Audit original/realigned CSVs and local archive inventories without mixing splits."""
import argparse,csv,json,math,hashlib,zipfile
from pathlib import Path,PurePosixPath

def read_rows(path,realigned=False):
    start,end=('START_REALIGNED','END_REALIGNED') if realigned else ('START','END')
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f,delimiter='\t');rows=list(reader)
    result={};issues=[]
    for i,row in enumerate(rows,2):
        try:
            a,b=float(row[start]),float(row[end]);name=row['SENTENCE_NAME']
            if not name or not all(map(math.isfinite,[a,b])) or a<0 or b<=a:raise ValueError('Invalid interval')
            if name in result:raise ValueError('Duplicate sentence identifier')
            result[name]={**row,'start_seconds':a,'end_seconds':b}
        except (ValueError,KeyError) as e:issues.append({'row':i,'reason':str(e)})
    return result,issues,len(rows)

def compare(original,realigned):
    shared=original.keys()&realigned.keys();changed=0;outside=0;text_changed=0
    for name in shared:
        a,b=original[name],realigned[name]
        if abs(a['start_seconds']-b['start_seconds'])>1e-6 or abs(a['end_seconds']-b['end_seconds'])>1e-6:changed+=1
        if b['start_seconds']<a['start_seconds']-1e-6 or b['end_seconds']>a['end_seconds']+1e-6:outside+=1
        if a['SENTENCE']!=b['SENTENCE']:text_changed+=1
    return {'shared_ids':len(shared),'timing_changed':changed,'realigned_interval_extends_outside_original_clip':outside,'text_changed':text_changed,
            'missing_realigned_ids':sorted(original.keys()-realigned.keys()),'extra_realigned_ids':sorted(realigned.keys()-original.keys())}

def audit(base):
    splits={};report={'splits':{},'cross_split_overlap':{},'archives':{},'training_started':False}
    for split in ['train','val','test']:
        path=base/f'how2sign_{split}.csv';aligned=base/f'how2sign_realigned_{split}.csv'
        rows,issues,count=read_rows(path);fixed,fixed_issues,fixed_count=read_rows(aligned,True);splits[split]=rows
        report['splits'][split]={'original_rows':count,'realigned_rows':fixed_count,'original_issues':issues,'realigned_issues':fixed_issues,
            'original_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'realigned_sha256':hashlib.sha256(aligned.read_bytes()).hexdigest(),**compare(rows,fixed)}
    for a,b in [('train','val'),('train','test'),('val','test')]:
        va={r['VIDEO_NAME'] for r in splits[a].values()};vb={r['VIDEO_NAME'] for r in splits[b].values()}
        report['cross_split_overlap'][f'{a}/{b}']={'sentence_ids':len(splits[a].keys()&splits[b].keys()),'source_video_names':len(va&vb)}
    for split in splits:
        for view in ['front','side']:
            paths=list(base.glob(f'{split}_rgb_{view}_clips*.zip'))
            if not paths:report['archives'][f'{split}/{view}']={'available':False};continue
            path=paths[0]
            with zipfile.ZipFile(path) as z:
                entries=[m for m in z.infolist() if not m.is_dir() and m.filename.lower().endswith('.mp4')]
                names=[PurePosixPath(m.filename).name for m in entries]
            expected={name.removesuffix('-rgb_front')+f'-rgb_{view}.mp4' for name in splits[split]}
            report['archives'][f'{split}/{view}']={'available':True,'file':path.name,'bytes':path.stat().st_size,'videos':len(names),
                'duplicate_basenames':len(names)-len(set(names)),'matched':len(expected&set(names)),
                'missing_names':sorted(expected-set(names)),'unmatched_names':sorted(set(names)-expected),'full_crc_checked':False}
    catalog=base/'catalog.json'
    report['existing_product_catalog_records']=len(json.loads(catalog.read_text(encoding='utf-8'))) if catalog.exists() else 0
    report['limitations']=['Archive availability refers only to ZIP files inside this dataset folder; extracted product clips and Downloads are separate.','CSV identity overlap checks are not semantic duplicate checks.','Archive catalog checks do not decode all videos or check all CRCs.','Realigned intervals are on the original source timeline; existing clips must not be blindly relabeled or stretched.','Test CSV alone does not supply test media; no final test results are claimed.']
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,default=Path(__file__).resolve().parents[1]/'datasets/how2sign');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Choose a new output file')
    report=audit(args.base);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'splits':report['splits'],'cross_split_overlap':report['cross_split_overlap'],'archives':{k:{n:v for n,v in r.items() if n not in ['missing_names','unmatched_names']} for k,r in report['archives'].items()}}))
