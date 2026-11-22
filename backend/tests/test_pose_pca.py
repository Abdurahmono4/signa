import numpy as np
import pytest
from backend.app.pose_pca import fit,reconstruct

def test_rank_one_reconstruction_and_missing_observations():
    xy=np.arange(12,dtype=float)[:,None,None]*np.ones((1,120,2));mask=np.ones((12,120),dtype=bool)
    model=fit(xy,mask);prediction=reconstruct(model,xy,mask,1)
    np.testing.assert_allclose(prediction,xy,atol=1e-10)
    mask[:,0]=False;xy[:,0]=999999
    masked=fit(xy,mask)
    assert np.all(masked['mean'][:2]==0)
    assert np.isfinite(reconstruct(masked,xy,mask,1)).all()
    with pytest.raises(ValueError):reconstruct(model,xy,mask,0)
