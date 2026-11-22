"""Train a small PCA on train clips; select rank on another clip and test on a third.

Reconstruction targets are detector observations, not verified motion ground truth.
No text-to-sign generation, 3D reconstruction or product animation is performed.
"""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[name]='2'
import argparse,json,sys,time,tracemalloc,hashlib,platform
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.pose_pca import fit,reconstruct,metrics

def peak_process_mb():
    if os.name!='nt':return None
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),*[(k,ctypes.c_size_t) for k in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi=ctypes.WinDLL('psapi');psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
    if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):return round(counters.PeakWorkingSetSize/1024**2,2)
    return None

def run(source,output):
    source=source.resolve()
    if output.exists():raise ValueError('Choose a new output directory')
    raw=(source/'manifest.json').read_bytes();manifest=json.loads(raw)
    if manifest.get('split')!='train' or len(manifest['clips'])!=5:raise ValueError('This bounded benchmark needs exactly five train sample clips')
    tracemalloc.start();start=time.perf_counter();groups={'train':[],'validation':[],'test':[]};names={k:[] for k in groups};videos={k:set() for k in groups}
    for i,clip in enumerate(manifest['clips']):
        split='validation' if i==1 else 'test' if i==4 else 'train'
        path=(source/clip['sample_file']).resolve()
        if not path.is_relative_to(source):raise ValueError('Unsafe file path')
        with np.load(path,allow_pickle=False) as data:
            groups[split].append((data['xy'].copy(),data['valid'].copy()))
        names[split].append(clip['sentence_name']);videos[split].add(clip['video_name'])
    if any(videos[a]&videos[b] for a,b in [('train','validation'),('train','test'),('validation','test')]):raise ValueError('Source video leakage')
    groups={k:(np.concatenate([p[0] for p in v]),np.concatenate([p[1] for p in v])) for k,v in groups.items()}
    trained=time.perf_counter();model=fit(*groups['train']);fit_seconds=time.perf_counter()-trained
    rng=np.random.default_rng(20261031);sigma=.03
    noisy={k:xy+rng.normal(0,sigma,xy.shape)*mask[:,:,None] for k,(xy,mask) in groups.items() if k!='train'}
    trials=[]
    for rank in [1,4,8,16,32,64]:
        prediction=reconstruct(model,noisy['validation'],groups['validation'][1],rank)
        trials.append({'rank':rank,**metrics(prediction,*groups['validation'])})
    chosen=min(trials,key=lambda r:r['hands_rmse'])['rank']
    at=time.perf_counter();prediction=reconstruct(model,noisy['test'],groups['test'][1],chosen);inference_seconds=time.perf_counter()-at
    test=metrics(prediction,*groups['test']);baseline=metrics(noisy['test'],*groups['test'])
    elapsed=time.perf_counter()-start;_,tracked_peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    output.mkdir(parents=True)
    np.savez_compressed(output/'pose-pca.npz',mean=model['mean'],components=model['components'][:chosen],rank=np.array(chosen))
    np.savez_compressed(output/'test-reconstruction.npz',observed=groups['test'][0],valid=groups['test'][1],noisy=noisy['test'],reconstructed=prediction)
    report={'experiment':'CPU PCA reconstruction of synthetically perturbed detector observations','model_trained':True,'text_to_sign_trained':False,
        'python':platform.python_version(),'numpy':np.__version__,'source_manifest_sha256':hashlib.sha256(raw).hexdigest(),'seed':20261031,'noise_sigma_shoulder_widths':sigma,
        'split_clips':names,'split_frames':{k:len(v[0]) for k,v in groups.items()},'source_videos_disjoint':True,'validation_trials':trials,'selected_rank':chosen,
        'test_pca':test,'test_no_processing_baseline':baseline,'test_hand_rmse_improvement_percent':100*(1-test['hands_rmse']/baseline['hands_rmse']),
        'fit_seconds':fit_seconds,'test_inference_seconds':inference_seconds,'elapsed_seconds':elapsed,'peak_process_working_set_mb':peak_process_mb(),'python_tracked_peak_mb':round(tracked_peak/1024**2,2),
        'model_bytes':(output/'pose-pca.npz').stat().st_size,'integrated_into_platform':False,'linguistic_verified':False,
        'limitations':['Only five clips from the training split; these internal splits are not official validation/test results.','Synthetic Gaussian noise; targets are detector outputs, not accurate human pose ground truth.','Per-clip normalization uses the whole clip; this is offline reconstruction, not a streaming evaluation.','No timing/FPS, text translation, neural motion generation or 3D avatar training.','PCA may damage signing details; compare held-out hand error before any integration.']}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=run(a.source,a.output)
    print(json.dumps(report,indent=2))
