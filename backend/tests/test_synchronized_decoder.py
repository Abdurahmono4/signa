import pytest
from backend.app.inference.synchronized_decoder import decode_aligned

MAPS = {'body': {10:0, 11:1}, 'left_hand': {20:0, 21:1}, 'right_hand': {30:0, 31:1}}
VALID = {'body': [10,11,99,99], 'left_hand': [20,21,99,99], 'right_hand': [30,31,99,99]}

def test_aligned_decode_preserves_each_timestep():
    assert decode_aligned(VALID,MAPS,99)=={'body':[0,1],'left_hand':[0,1],'right_hand':[0,1]}

def test_early_hand_end_preserves_valid_prefix():
    assert decode_aligned({**VALID,'left_hand':[20,99,99,99]},MAPS,99)['left_hand']==[0]

@pytest.mark.parametrize('stream',[[99,21,99,99],[20,22,99,99],[20,21,99,20],[20,21,99]])
def test_no_silent_hand_holes_clamping_or_tail_padding(stream):
    with pytest.raises(ValueError):decode_aligned({**VALID,'left_hand':stream},MAPS,99)

def test_empty_and_truncated_outputs_are_not_translations():
    with pytest.raises(ValueError):decode_aligned({k:[99]*4 for k in MAPS},MAPS,99)
    with pytest.raises(ValueError):decode_aligned({k:v[:2] for k,v in VALID.items()},MAPS,99)
