"""Attach decoded local frontal-video timestamps to inspected 2D sample features."""
import argparse,json,sys
from pathlib import Path
import av,numpy as np

def frame_times(indices,timestamps):
    indices=np.asarray(indices);times=np.asarray(timestamps,dtype=np.float64)
    if indices.ndim!=1 or not len(indices) or indices.dtype.kind not in 'iu' or np.any(indices<0) or np.any(np.diff(indices.astype(np.int64))<=0):raise ValueError('Invalid frame indices')
    if times.ndim!=1 or not len(times) or not np.isfinite(times).all() or np.any(np.diff(times)<=0):raise ValueError('Invalid video timestamps')
    if indices[-1]>=len(times):raise ValueError('Keypoint index exceeds decoded video')
    return times[indices]-times[0]

def attach(base,output):
    if output.exists():raise ValueError('Choose a new output directory')
    manifest=json.loads((base/'train-features-001/manifest.json').read_text(encoding='utf-8'))
    inspected=json.loads((base/'train-front-inspection.json').read_text(encoding='utf-8'))
    videos={r['sentence_name']:r for r in inspected['samples'] if r.get('decode_passed')}
    if manifest['split']!='train':raise ValueError('Train features required')
    output.mkdir(parents=True);clips=[]
    for clip in manifest['clips']:
        record=videos[clip['sentence_name']];path=Path(record['file']).resolve()
        if not path.is_relative_to(base.resolve()):raise ValueError('Video outside dataset')
        pts=[]
        with av.open(path) as container:
            for frame in container.decode(video=0):
                if frame.pts is None:raise ValueError('Video frame lacks PTS')
                pts.append(float(frame.pts*frame.time_base))
        with np.load(base/'train-features-001'/clip['sample_file'],allow_pickle=False) as data:arrays={k:data[k] for k in data.files}
        if len(pts)!=record['keypoint_frames'] or len(pts)!=len(arrays['frame_numbers']):raise ValueError('Sample frame counts differ')
        arrays['time_seconds']=frame_times(arrays['frame_numbers'],pts)
        np.savez_compressed(output/clip['sample_file'],**arrays)
        clips.append({**clip,'fps':record['fps'],'local_video_times_attached':True,'source_video':path.name,'last_frame_seconds':float(arrays['time_seconds'][-1]),'training_ready':False})
    report={**manifest,'clips':clips,'format':'masked-body-hands-face-2d-timed-v1','time_unit':'seconds from decoded original frontal clip PTS, first video frame = 0',
        'source_inspection':str((base/'train-front-inspection.json').resolve()),'linguistic_alignment_verified':False,'training_started':False,
        'limitations':['Only five inspected train clips; one frame overlay visually checked.','Local video timing is not English word-to-sign alignment.','Original vs realigned CSV source intervals were not substituted; no absent frames synthesized.','Not 3D joint rotations, not text-to-ASL model training.']}
    (output/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=Path(__file__).resolve().parents[1]/'datasets/how2sign');p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    report=attach(a.base,a.output);print(json.dumps({'clips':len(report['clips']),'frames':sum(c['frames'] for c in report['clips']),'fps':[c['fps'] for c in report['clips']],'training_started':False}))
