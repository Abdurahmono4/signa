"""Isolate the text generator by decoding released poses of the same ten recordings."""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend/app/inference'))
from madis_runner import (_check_source, _verify_checkpoint, _load_state, _load_stats, decode_pose_streams,
                          load_motion_decoders, FEATURE_FORMAT, FEATURE_LAYOUT, HF_REVISION, CHECKPOINT_SHA256)
from reference_tokens import ARCHIVE_NAME, ARCHIVE_SHA256, open_verified, read_tokens


def decode(model_root, corpus, output):
    import numpy as np
    import torch
    _check_source(model_root/'source')
    sys.path.insert(0,str(model_root/'source'))
    checkpoint=model_root/'assets/sft_how2sign.ckpt'
    _verify_checkpoint(checkpoint)
    torch.set_num_threads(8)
    torch.set_num_interop_threads(2)
    decoders=load_motion_decoders(_load_state(checkpoint,torch,np))
    mean,std=[_load_stats(model_root/'assets'/name,torch) for name in ('mean.pt','std.pt')]
    samples=json.loads((corpus/'samples.json').read_text(encoding='utf-8-sig'))
    base=ROOT/'datasets/how2sign'
    with (base/'how2sign_realigned_test.csv').open(encoding='utf-8-sig') as f:
        test={r['SENTENCE_NAME']:r for r in csv.DictReader(f,delimiter='\t')}
    controls=[]
    with torch.inference_mode(), open_verified(base/'madis-reference'/ARCHIVE_NAME) as archive:
        for index,s in enumerate(samples):
            name=s['sentence_id']; original=test[name]
            if original['SENTENCE']!=s['text'] or float(original['START_REALIGNED'])!=s['start'] or float(original['END_REALIGNED'])!=s['end']:
                raise ValueError('Realigned test recording and caption disagree')
            target=output/'model'/f'{index:04d}'
            target.mkdir(parents=True,exist_ok=True)
            codes=read_tokens(archive,name)
            streams=[torch.from_numpy(a.copy()).long() for a in codes.T]
            _,features,tails=decode_pose_streams(decoders,streams,mean,std)
            if any(tails.values()) or features.shape!=(4*len(codes),133) or not torch.isfinite(features).all():
                raise ValueError('Invalid reference motion')
            metadata={'id':s['id'],'text':s['text'],'format':FEATURE_FORMAT,'feature_layout':FEATURE_LAYOUT,
                'fps':24,'frame_count':len(features),'duration':len(features)/24,'features':features.tolist(),
                'source_kind':'recording_token_reconstruction','sentence_name':name,'split':'test',
                'model_revision':HF_REVISION,'checkpoint_sha256':CHECKPOINT_SHA256,
                'archive_sha256':ARCHIVE_SHA256,'linguistically_verified':False}
            (target/'motion.json').write_text(json.dumps(metadata,separators=(',',':')),encoding='utf-8')
            # Old experiments sometimes zero-padded a shorter hand. Only compare the
            # shared, decoded prefix so presentation/padding choices cannot change the control.
            with np.load(corpus/'model'/f'{index:04d}'/'motion.npz',allow_pickle=False) as prior:
                replay_streams=[torch.tensor(prior[k],dtype=torch.long) for k in ('body_tokens','left_hand_tokens','right_hand_tokens')]
                common=4*min(map(len,replay_streams))
                _,replayed,_=decode_pose_streams(decoders,replay_streams,mean,std)
                difference=float(np.abs(replayed[:common].numpy()-prior['features'][:common]).max())
                if difference>1e-4:
                    raise ValueError(f'Cannot reproduce stored decoder output for {name}: {difference}')
            controls.append({'id':s['id'],'recording':name,'reference_frames':len(features),
                'generated_frames':len(replayed),'control_frames':common,'control_max_error':difference})
    (output/'samples.json').write_text(json.dumps(samples,indent=2),encoding='utf-8')
    (output/'decoder-check.json').write_text(json.dumps(controls,indent=2),encoding='utf-8')
    print(json.dumps(controls,ensure_ascii=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('model_root',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--corpus',type=Path,default=ROOT/'docs/asl-comparison-10')
    args=p.parse_args();decode(args.model_root,args.corpus,args.output)
