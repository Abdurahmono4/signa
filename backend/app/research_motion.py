"""Numeric interoperability with Dong SignAvatar's documented 53-joint output.

Own implementation; no checkpoint, pickle or upstream executable is loaded.
"""
import math
import numpy as np
from .signavatars_bridge import convert_smplx

SOURCE='https://github.com/dongludeeplearning/SignAvatar'

def rotation6d_to_axis_angle(values):
    a=np.asarray(values,dtype=float)
    x,y=a[:3],a[3:]
    if np.linalg.norm(x)<1e-8:raise ValueError('6D aylanish vektori nol.')
    x=x/np.linalg.norm(x);y=y-np.dot(x,y)*x
    if np.linalg.norm(y)<1e-8:raise ValueError('6D aylanish vektorlari parallel.')
    y=y/np.linalg.norm(y);m=np.stack((x,y,np.cross(x,y)))
    # PyTorch3D convention: orthonormal vectors are matrix rows, not columns.
    tr=np.trace(m)
    if tr>0:
        s=math.sqrt(tr+1)*2;q=np.array([(m[2,1]-m[1,2])/s,(m[0,2]-m[2,0])/s,(m[1,0]-m[0,1])/s,s/4])
    else:
        i=int(np.argmax(np.diag(m)));j=(i+1)%3;k=(i+2)%3
        s=math.sqrt(max(0,1+m[i,i]-m[j,j]-m[k,k]))*2
        q=np.zeros(4);q[i]=s/4;q[j]=(m[j,i]+m[i,j])/s;q[k]=(m[k,i]+m[i,k])/s;q[3]=(m[k,j]-m[j,k])/s
    q=q/np.linalg.norm(q)
    if q[3]<0:q=-q
    n=np.linalg.norm(q[:3])
    return (q[:3]*(2*math.atan2(n,q[3])/n)).tolist() if n>1e-10 else [0.,0.,0.]

def convert_dong(data):
    if data.get('format')!='signavatar-rot6d-53':raise ValueError('Format signavatar-rot6d-53 bo‘lsin.')
    if data.get('normalized') is not False:raise ValueError('Avval model natijasini denormalize qiling va normalized=false yozing.')
    frames=data.get('frames')
    if not isinstance(frames,list) or not 1<=len(frames)<=3000:raise ValueError('1–3000 kadr talab qilinadi.')
    rows=[]
    for frame in frames:
        if not isinstance(frame,list) or len(frame)!=53:raise ValueError('Har kadr 53 bo‘g‘imdan iborat bo‘lsin.')
        poses=[]
        for joint in frame:
            if not isinstance(joint,list) or len(joint)!=6 or any(type(v) not in (int,float) or not math.isfinite(v) for v in joint):raise ValueError('Bo‘g‘imda 6 ta chekli son bo‘lsin.')
            poses.extend(rotation6d_to_axis_angle(joint))
        rows.append(poses+[0.]*23) # 159 pose + 10 shape + 10 expression + 3 camera
    out=convert_smplx({'smplx':rows},data.get('fps'))
    out.update(source=SOURCE,source_format='signavatar-rot6d-53',language='asl',name=str(data.get('name','Import qilingan ASL harakati'))[:160])
    out['limitations'].append('Expression coefficients are absent in this input and zero-filled; no facial signs are inferred.')
    return out
