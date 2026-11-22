import numpy as np
import pytest
from backend.app.keypoint_features import normalize_keypoints

def arrays():
    result={k:np.tile([100,120,.9],(4,n,1)).astype(np.float32) for k,n in [('pose_keypoints_2d',25),('hand_left_keypoints_2d',21),('hand_right_keypoints_2d',21),('face_keypoints_2d',70)]}
    result['pose_keypoints_2d'][:,2,0]=70;result['pose_keypoints_2d'][:,5,0]=130
    result['hand_left_keypoints_2d'][:,0,0]=[100,110,120,130]
    return result

def test_invariant_to_translation_scale_and_reversible_for_valid_points():
    data=arrays();first=normalize_keypoints(data,np.arange(4))
    other={k:v.copy() for k,v in data.items()}
    for value in other.values():value[:,:,:2]=value[:,:,:2]*2+[500,20]
    second=normalize_keypoints(other,np.arange(4))
    np.testing.assert_allclose(first['xy'],second['xy'],atol=1e-6)
    recovered=first['xy'][:,8:29]*first['scale_px']+first['origin_xy']
    np.testing.assert_allclose(recovered,data['hand_left_keypoints_2d'][:,:,:2])
    assert first['xy'].shape==(4,120,2)

def test_missing_points_and_frame_gaps_never_become_motion_targets():
    data=arrays();data['hand_left_keypoints_2d'][1,0]=[999,999,.1]
    data['face_keypoints_2d'][0,0,2]=1.01
    result=normalize_keypoints(data,np.array([0,1,4,5]))
    assert not result['valid'][1,8] and not result['xy'][1,8].any()
    assert not result['delta_valid'][1,8] and not result['delta_valid'][2].any()
    assert result['delta_valid'][3,8] and result['scores'][0,50]>1
    assert not result['delta_xy_per_frame'][2].any()

def test_missing_reference_and_invalid_order_rejected():
    data=arrays()
    with pytest.raises(ValueError):normalize_keypoints(data,np.array([0,2,1,3]))
    data['pose_keypoints_2d'][:,1,2]=0
    with pytest.raises(ValueError):normalize_keypoints(data,np.arange(4))
