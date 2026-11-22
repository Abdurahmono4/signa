"""Masked 2D research features; not a 3D animation or trained translator."""
import numpy as np

LAYOUT=[*[f'body_{i}' for i in range(8)],*[f'left_hand_{i}' for i in range(21)],*[f'right_hand_{i}' for i in range(21)],*[f'face_{i}' for i in range(70)]]

def normalize_keypoints(arrays,frame_numbers,threshold=.2):
    if not 0<threshold<=1:raise ValueError('Invalid detector threshold')
    parts=[];length=None
    for key,count in [('pose_keypoints_2d',25),('hand_left_keypoints_2d',21),('hand_right_keypoints_2d',21),('face_keypoints_2d',70)]:
        values=np.asarray(arrays[key],dtype=np.float32)
        if values.ndim!=3 or values.shape[1:]!=(count,3) or not np.isfinite(values).all() or np.any(values[:,:,2]<0):raise ValueError('Malformed '+key)
        if length is None:length=len(values)
        if len(values)!=length:raise ValueError('Frame counts differ')
        parts.append(values[:,:8] if count==25 else values)
    indices=np.asarray(frame_numbers)
    if not length or indices.shape!=(length,) or indices.dtype.kind not in 'iu' or np.any(indices<0) or np.any(np.diff(indices.astype(np.int64))<=0):raise ValueError('Frame numbers must increase')
    raw=np.concatenate(parts,axis=1);valid=raw[:,:,2]>=threshold
    neck=valid[:,1];shoulders=valid[:,2]&valid[:,5]
    widths=np.linalg.norm(raw[:,2,:2]-raw[:,5,:2],axis=1);shoulders&=widths>1e-6
    if neck.sum()<min(3,length) or shoulders.sum()<min(3,length):raise ValueError('Insufficient reliable neck/shoulder observations')
    origin=np.median(raw[neck,1,:2],axis=0).astype(np.float32)
    scale=np.float32(np.median(widths[shoulders]))
    xy=(raw[:,:,:2]-origin)/scale
    xy=np.where(valid[:,:,None],xy,0).astype(np.float32)
    # No interpolation over missing points or absent frame numbers.
    delta_mask=np.zeros_like(valid)
    delta_mask[1:]=valid[1:]&valid[:-1]&(np.diff(indices)==1)[:,None]
    delta=np.zeros_like(xy);delta[1:]=xy[1:]-xy[:-1];delta[~delta_mask]=0
    return {'xy':xy,'valid':valid,'scores':raw[:,:,2].copy(),
            'delta_xy_per_frame':delta,'delta_valid':delta_mask,
            'origin_xy':origin,'scale_px':scale,'frame_numbers':indices.astype(np.int64),
            'point_names':np.asarray(LAYOUT,dtype='U24')}
