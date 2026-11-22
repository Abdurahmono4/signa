"""Bounded local inspection of How2Sign train OpenPose data; never trains a model."""
import argparse,csv,json,math,re,struct,tarfile,zlib
from pathlib import Path,PurePosixPath
import numpy as np

FIELDS={'pose_keypoints_2d':25,'hand_left_keypoints_2d':21,'hand_right_keypoints_2d':21,'face_keypoints_2d':70}
BODY_EDGES=[(0,1),(1,2),(2,3),(3,4),(1,5),(5,6),(6,7)]
HAND_EDGES=[(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),(13,17),(0,17),(17,18),(18,19),(19,20)]

def parse_frame(data):
    people=data.get('people')
    if not isinstance(people,list):raise ValueError('Missing people array')
    # Ambiguous detections are kept as missing, never silently assigned to a signer.
    if len(people)!=1:return {key:np.zeros((n,3),dtype=np.float32) for key,n in FIELDS.items()},len(people)
    out={}
    for key,n in FIELDS.items():
        values=people[0].get(key,[])
        if len(values)!=n*3 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):raise ValueError('Malformed '+key)
        points=np.asarray(values,dtype=np.float32).reshape(n,3)
        if not np.isfinite(points).all() or np.any(points[:,2]<0):raise ValueError('Invalid confidence')
        out[key]=points
    return out,1

def png(path,pixels):
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    h,w,_=pixels.shape
    raw=b''.join(b'\0'+row.tobytes() for row in pixels)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))

def contact_sheet(clips,path):
    """Rows follow manifest order; eight uniformly sampled frames per row."""
    image=np.full((len(clips)*240,8*220,3),[17,24,39],dtype=np.uint8)
    def point(x,y,color,radius=2):
        x,y=int(x),int(y)
        if 0<=x<image.shape[1] and 0<=y<image.shape[0]:image[max(0,y-radius):y+radius+1,max(0,x-radius):x+radius+1]=color
    def line(a,b,color):
        for p in np.linspace(a,b,max(2,int(np.linalg.norm(b-a)))):point(*p,color,1)
    for row,arrays in enumerate(clips):
        body=arrays['pose_keypoints_2d'][:,:8,:];parts=[body,*[arrays[k] for k in list(FIELDS)[1:]]]
        valid=np.concatenate([p[p[:,:,2]>.2][:,:2] for p in parts])
        if not len(valid):continue
        lo=np.min(valid,axis=0);hi=np.max(valid,axis=0);scale=min(190/max(1,hi[0]-lo[0]),210/max(1,hi[1]-lo[1]))
        for col,index in enumerate(np.linspace(0,len(body)-1,8).astype(int)):
            for key,color,edges in [('pose_keypoints_2d',[100,180,250],BODY_EDGES),('hand_left_keypoints_2d',[64,220,170],HAND_EDGES),('hand_right_keypoints_2d',[250,170,75],HAND_EDGES),('face_keypoints_2d',[170,180,200],[])]:
                points=arrays[key][index]
                if key=='pose_keypoints_2d':points=points[:8]
                projected=(points[:,:2]-lo)*scale+[col*220+15,row*240+15]
                for a,b in edges:
                    if points[a,2]>.2 and points[b,2]>.2:line(projected[a],projected[b],color)
                for p,q in zip(projected,points):
                    if q[2]>.2:point(*p,color,1 if key.startswith('face') else 2)
    png(path,image)
    if len(clips):png(path.with_name('first-clip.png'),image[:240])

def prepare(archive,metadata,output,limit=5,max_members=12000,max_bytes=64*1024*1024,split='train',max_scan_bytes=None):
    max_scan_bytes=max_bytes*4 if max_scan_bytes is None else max_scan_bytes
    if not 0<max_scan_bytes<=4*1024**3:raise ValueError('Scan limit must be within 4 GiB')
    if split not in {'train','val','test'}:raise ValueError('Unknown dataset split')
    if not 1<=limit<=10:raise ValueError('Use 1–10 sample clips')
    if output.exists():raise ValueError('Output already exists; choose a new folder')
    with metadata.open(encoding='utf-8-sig',newline='') as f:
        rows={r['SENTENCE_NAME']:r for r in csv.DictReader(f,delimiter='\t')}
    groups={};read_bytes=0;members=0;issues=[];reason='archive_end'
    with tarfile.open(archive,'r|gz') as tar:
        for member in tar:
            members+=1
            if members>max_members:reason='member_limit';break
            if member.offset_data+member.size>max_scan_bytes:reason='scan_byte_limit';break
            if not member.isfile():continue
            name=PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts:raise ValueError('Unsafe archive member')
            match=re.search(r'_(\d+)_keypoints\.json$',name.name)
            if not match or name.parent.name not in rows:continue
            clip=name.parent.name
            if clip not in groups and len(groups)>=limit:reason='sample_limit';break
            if member.size>2_000_000 or read_bytes+member.size>max_bytes:reason='byte_limit';break
            read_bytes+=member.size
            try:
                frame,people=parse_frame(json.load(tar.extractfile(member)))
                number=int(match[1]);frames=groups.setdefault(clip,{})
                if number in frames:raise ValueError('Duplicate frame number')
                frames[number]=(frame,people)
            except (ValueError,TypeError,KeyError) as e:issues.append({'member':member.name,'reason':str(e)})
    output.mkdir(parents=True);manifest=[];visuals=[]
    for number,(clip,frames) in enumerate(groups.items()):
        if not frames:continue
        order=sorted(frames);arrays={key:np.stack([frames[n][0][key] for n in order]) for key in FIELDS};visuals.append(arrays)
        target=f'clip-{number:03d}.npz'
        np.savez_compressed(output/target,frame_numbers=np.asarray(order,dtype=np.int64),person_counts=np.asarray([frames[n][1] for n in order]),**arrays)
        row=rows[clip];quality={key:round(float(np.mean(a[:,:,2]>=.2)),4) for key,a in arrays.items()}
        manifest.append({'sentence_name':clip,'text':row['SENTENCE'],'video_name':row['VIDEO_NAME'],'csv_start':float(row['START']),'csv_end':float(row['END']),
                         'sample_file':target,'frames':len(order),'first_frame':order[0],'last_frame':order[-1],'missing_frame_numbers':sum(max(0,b-a-1) for a,b in zip(order,order[1:])),
                         'ambiguous_or_empty_frames':sum(frames[n][1]!=1 for n in order),'confidence_coverage_at_0_2':quality,
                         'scores_above_one':{k:int(np.sum(a[:,:,2]>1)) for k,a in arrays.items()},'fps':None,'verified':False,'training_ready':False})
    report={'archive':str(archive.resolve()),'archive_bytes':archive.stat().st_size,'split':split,'language':'ASL','kind':'OpenPose 2D pixel coordinates with confidence',
            'source':'https://how2sign.github.io/','license':'CC-BY-NC-4.0','members_visited':members,'json_bytes_read':read_bytes,'stop_reason':reason,'clips':manifest,'issues':issues,
            'full_archive_scanned':reason=='archive_end','training_started':False,'limitations':['Bounded archive prefix; complete clip membership is not guaranteed.','Frame rate not verified. CSV intervals do not establish FPS.','Detector confidence scores are preserved, including values above one; they are not translation accuracy.','2D points are not 3D joint rotations; no GLB/SMPL-X conversion or linguistic approval.']}
    (output/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if visuals:contact_sheet(visuals,output/'contact-sheet.png')
    return report

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1];parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--clips',type=int,default=5)
    parser.add_argument('--split',choices=['train','val','test'],default='train')
    args=parser.parse_args();base=root/'datasets/how2sign'
    report=prepare(base/f'{args.split}_2D_keypoints.tar.gz',base/f'how2sign_{args.split}.csv',args.output,args.clips,split=args.split)
    print(json.dumps({'output':str(args.output.resolve()),'clips':len(report['clips']),'frames':sum(c['frames'] for c in report['clips']),'issues':len(report['issues']),'stop_reason':report['stop_reason'],'training_started':False}))
