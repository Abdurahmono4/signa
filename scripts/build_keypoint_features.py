"""Convert a bounded sample into masked 2D features without training or resampling."""
import argparse,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.keypoint_features import normalize_keypoints

def build(source,output):
    source=source.resolve();report=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    if report.get('split')!='train':raise ValueError('This preparation command accepts train samples only')
    if output.exists():raise ValueError('Output folder already exists')
    output.mkdir(parents=True);clips=[]
    for clip in report['clips']:
        path=(source/clip['sample_file']).resolve()
        if not path.is_relative_to(source) or path.suffix!='.npz':raise ValueError('Unsafe sample path')
        with np.load(path,allow_pickle=False) as data:features=normalize_keypoints(data,data['frame_numbers'])
        np.savez_compressed(output/path.name,**features)
        n=len(features['xy']);clips.append({'sentence_name':clip['sentence_name'],'video_name':clip['video_name'],'text':clip['text'],'sample_file':path.name,
            'frames':n,'points':features['xy'].shape[1],'valid_point_fraction':float(features['valid'].mean()),
            'left_hand_valid_fraction':float(features['valid'][:,8:29].mean()),'right_hand_valid_fraction':float(features['valid'][:,29:50].mean()),
            'fps':clip.get('fps'),'training_ready':False,'verified':False})
    result={'split':'train','language':'ASL','source_manifest':str(source/'manifest.json'),'format':'masked-body-hands-face-2d-v1','clips':clips,
        'normalization':{'origin':'per-clip median reliable neck','scale':'per-clip median reliable shoulder width','axes':'image x right, y down','threshold':.2},
        'time_unit':'source frame index; FPS unresolved','missing_points':'zero coordinates plus explicit mask; no interpolation',
        'training_started':False,'limitations':['2D features only, not MaDiS 133/SMPL-X/GLB rotations.','Complete sample membership, frame rate and linguistic alignment remain unverified.','Confidence masks are detector quality indicators, not ASL accuracy.']}
    (output/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    report=build(args.source,args.output)
    print(json.dumps({'clips':len(report['clips']),'frames':sum(c['frames'] for c in report['clips']),'points_per_frame':120,'output':str(args.output.resolve()),'training_started':False}))
