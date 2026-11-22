import numpy as np
import pytest
from scripts.attach_pose_timing import frame_times

def test_decoded_timestamps_preserve_gaps_without_guessing_fps():
    np.testing.assert_allclose(frame_times([0,2,3],[10,10.04,10.1,10.15]),[0,.1,.15])
    for indices,times in [([0,4],[0,.1]),([1,0],[0,.1]),([0,1],[0,0]),([0,1],[0,float('nan')])]:
        with pytest.raises(ValueError):frame_times(indices,times)
