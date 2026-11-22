"""Prepare corpus mapping or convert explicit JSON; preserves working corpus."""
import argparse,json,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.signavatars_bridge import BASE,REPOSITORY,build_manifest,convert_smplx

def main():
    parser=argparse.ArgumentParser()
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('prepare')
    converter=commands.add_parser('convert-json')
    converter.add_argument('--input',required=True,type=Path)
    converter.add_argument('--output',required=True,type=Path)
    converter.add_argument('--fps',type=float,default=24)
    args=parser.parse_args()
    if args.command=='prepare':
        manifest=build_manifest()
        manifest['commit']=subprocess.check_output(['git','-C',str(REPOSITORY),'rev-parse','HEAD'],text=True).strip()
        BASE.mkdir(parents=True,exist_ok=True)
        (BASE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in manifest.items() if k!='records'},ensure_ascii=False))
    else:
        if args.input.stat().st_size>100*1024*1024:raise ValueError('JSON 100 MB dan oshmasin.')
        output=convert_smplx(json.loads(args.input.read_text(encoding='utf-8')),args.fps)
        # Avoid replacing an existing motion or user file.
        with args.output.open('x',encoding='utf-8') as f:json.dump(output,f,ensure_ascii=False)
        print(json.dumps({'frames':len(output['frames']),'channels':133,'verified':False}))

if __name__=='__main__':main()
