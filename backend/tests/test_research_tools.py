import math
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.research_motion import convert_dong,rotation6d_to_axis_angle
from backend.app.research_api import grammar,audit_text

IDENTITY=[1,0,0,0,1,0]

def test_rotation_convention_and_half_turn():
    assert rotation6d_to_axis_angle(IDENTITY)==[0,0,0]
    assert rotation6d_to_axis_angle([0,-1,0,1,0,0])==pytest.approx([0,0,math.pi/2])
    assert rotation6d_to_axis_angle([1,0,0,0,-1,0])==pytest.approx([math.pi,0,0])
    with pytest.raises(ValueError):rotation6d_to_axis_angle([1,0,0,2,0,0])

def test_53_joint_mapping_and_no_verification_claim():
    frame=[IDENTITY.copy() for _ in range(53)];frame[12]=[0,-1,0,1,0,0];frame[22]=[1,0,0,0,-1,0]
    out=convert_dong({'format':'signavatar-rot6d-53','normalized':False,'fps':30,'frames':[frame]})
    assert out['frames'][0][:3]==pytest.approx([0,0,math.pi/2])
    assert out['frames'][0][30:33]==pytest.approx([math.pi,0,0])
    assert len(out['frames'][0])==133 and out['fps']==30 and not out['verified']
    assert out['frames'][0][123:]==[0]*10

def test_import_endpoint_rejects_unsafe_and_ambiguous_input():
    client=TestClient(app)
    assert client.post('/api/research/motions/convert',content=b'not json').status_code==422
    assert client.post('/api/research/motions/convert',json={'smplx':[[0]*182],'fps':24}).status_code==422
    result=client.post('/api/research/motions/convert',json={'smplx':[[0]*182],'fps':24,'language':'dgs'})
    assert result.status_code==200 and result.json()['language']=='dgs' and not result.json()['verified']
    bad={'format':'signavatar-rot6d-53','normalized':True,'fps':24,'frames':[[IDENTITY]*53]}
    assert client.post('/api/research/motions/convert',json=bad).status_code==422

def test_grammar_uses_whole_active_phrases_and_escapes_quotes():
    text=grammar([{'text':'hello "friend"'},{'text':'bye','review_decision':'rejected'}])
    assert text.startswith('root ::= phrase\n') and '\\"friend\\"' in text and 'bye' not in text
    with pytest.raises(ValueError):grammar([])

def test_coverage_gain_does_not_approve_changed_meaning(monkeypatch):
    from backend.app import how2sign
    monkeypatch.setattr(how2sign,'translate_asl',lambda t:{'coverage':100})
    out=audit_text('Do not give 10 tablets.','Give 20 tablets.')
    assert len(out['alerts'])==2 and not out['meaning_verified'] and not out['applied']
