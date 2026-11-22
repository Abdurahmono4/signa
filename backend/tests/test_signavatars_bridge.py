import pytest
from backend.app.signavatars_bridge import convert_smplx

def test_182_channel_mapping_preserves_hands_jaw_and_expression():
    # Numeric sentinel fixture, not human motion or a linguistic test.
    row=list(range(182));out=convert_smplx({'smplx':[row,row],'total_valid_index':[4,5]})
    frame=out['frames'][0]
    assert len(frame)==133
    assert frame[:3]==row[36:39] # neck joint 11 after root orientation
    assert frame[30:120]==row[66:156]
    assert frame[120:123]==row[156:159]
    assert frame[123:]==row[169:179]
    assert out['source_start_frame']==4 and not out['verified'] and not out['retarget_validated']

def test_missing_frames_or_invalid_values_are_not_silently_accepted():
    row=[0.]*182
    for data in [{'smplx':[row[:-1]]},{'smplx':[[float('nan')]*182]},
                 {'smplx':[row,row],'total_valid_index':[0,2]}]:
        with pytest.raises(ValueError):convert_smplx(data)
