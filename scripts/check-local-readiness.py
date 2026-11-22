"""Read-only local launch audit. Does not download, extract or train anything."""
import argparse,csv,json,shutil,subprocess,sys,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def endpoint(path,port=8001):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=4) as response:
            body=response.read()
            return {'ok':response.status==200,'status':response.status,'data':json.loads(body) if port==8001 else {'signbridge_page':b'SignBridge' in body}}
    except Exception as e:return {'ok':False,'error':type(e).__name__}

def binary_status(name):
    found=shutil.which(name)
    if not found:found=next((str(p) for p in (ROOT/'tools').glob(f'**/{name}.exe')),None)
    if not found:return {'ok':False,'reason':'not_found'}
    try:
        proc=subprocess.run([found,'-version'],capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return {'ok':proc.returncode==0,'version':proc.stdout.splitlines()[0] if proc.stdout else ''}
    except Exception as e:return {'ok':False,'reason':type(e).__name__}

def audit():
    dataset=ROOT/'datasets/how2sign';metadata={}
    for split in ['train','val','test']:
        file=dataset/f'how2sign_{split}.csv'
        if file.is_file():
            with file.open(encoding='utf-8-sig',newline='') as stream:metadata[split]=sum(1 for _ in csv.DictReader(stream,delimiter='\t'))
    catalog=dataset/'catalog.json'
    count=len(json.loads(catalog.read_text(encoding='utf-8'))) if catalog.is_file() else 0
    report={'python':sys.version.split()[0],'venv_present':(ROOT/'.venv/Scripts/python.exe').is_file(),
        'node_present':bool(shutil.which('node')),'frontend_dependencies':(ROOT/'frontend/node_modules/vite/bin/vite.js').is_file(),
        'frontend':endpoint('/',5174),'backend':endpoint('/api/health'),'neural':endpoint('/api/neural/health'),
        'ffmpeg':binary_status('ffmpeg'),'ffprobe':binary_status('ffprobe'),
        'dataset':{'csv_rows':metadata,'validation_catalog_records':count,
            'train_archives':[{'name':p.name,'bytes':p.stat().st_size} for p in sorted(dataset.glob('train*')) if p.is_file() and p.name.endswith(('.zip','.tar.gz'))]},
        'avatar_glb_present':(ROOT/'assets/avatars/rocketbox-female-01/female.glb').is_file(),
        'limitations':['Service checks do not establish speech accuracy or sign-language correctness.','Archive presence does not establish CRC validity or training completion.']}
    report['core_ready']=all([report['venv_present'],report['node_present'],report['frontend_dependencies'],report['frontend']['ok'],report['backend']['ok'],report['ffmpeg']['ok'],report['ffprobe']['ok']])
    report['ml_ready']=bool(report['neural']['ok'] and report['neural'].get('data',{}).get('ready') and report['avatar_glb_present'])
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args();report=audit()
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        if args.output.exists():raise ValueError('Output exists; choose a new report name')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text,encoding='utf-8')
    print(text);sys.exit(0 if report['core_ready'] else 1)
