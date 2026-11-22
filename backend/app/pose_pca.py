"""Small CPU pose-reconstruction baseline, never a sign-language translator."""
import numpy as np

def flatten(xy,valid):
    xy=np.asarray(xy,dtype=np.float64);valid=np.asarray(valid,dtype=bool)
    if xy.ndim!=3 or xy.shape[2]!=2 or valid.shape!=xy.shape[:2] or not np.isfinite(xy).all():raise ValueError('Invalid pose arrays')
    return xy.reshape(len(xy),-1),np.repeat(valid,2,axis=1)

def fit(xy,valid):
    values,mask=flatten(xy,valid)
    if len(values)<2:raise ValueError('Need multiple frames')
    mean=np.divide(np.sum(np.where(mask,values,0),axis=0),mask.sum(axis=0),out=np.zeros(values.shape[1]),where=mask.sum(axis=0)>0)
    centered=np.where(mask,values-mean,0)
    _,singular,components=np.linalg.svd(centered,full_matrices=False)
    return {'mean':mean,'components':components,'singular_values':singular}

def reconstruct(model,xy,valid,rank):
    values,mask=flatten(xy,valid)
    if not 1<=rank<=len(model['components']):raise ValueError('Invalid PCA rank')
    basis=model['components'][:rank]
    centered=np.where(mask,values-model['mean'],0)
    return ((centered@basis.T)@basis+model['mean']).reshape(np.asarray(xy).shape)

def metrics(prediction,target,valid):
    error=np.asarray(prediction)-target;mask=np.asarray(valid,dtype=bool)
    result={}
    for label,subset in [('all',slice(None)),('hands',slice(8,50)),('left_hand',slice(8,29)),('right_hand',slice(29,50))]:
        selected=error[:,subset][mask[:,subset]]
        result[label+'_rmse']=float(np.sqrt(np.mean(selected**2))) if selected.size else None
    return result
