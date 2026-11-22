import json
from backend.app.neural_engine import reuse_motion_request, MODEL_REVISION, DECODER_GUARD

def test_request_cache_rejects_mismatches_and_invalid_paths(tmp_path):
    source = tmp_path / 'neural' / 'previous'
    motion = source / 'motion'
    motion.mkdir(parents=True)
    payload = dict(segments=[dict(id='0', text='Hello.')], seed=1234)
    (source / 'request.json').write_text(json.dumps(payload))
    (motion / 'pose.json').write_text(json.dumps(dict(features=[[0]*133]*4)))
    record = dict(id='0', text='Hello.', model_revision=MODEL_REVISION,
                  decoder_guard=DECODER_GUARD,
                  input_normalization_version='terminal-punctuation-compact-vocabulary-v1',
                  motion_json='pose.json', frame_count=4)
    index = dict(status='ready', motions=[record])
    (motion / 'index.json').write_text(json.dumps(index))
    target = tmp_path / 'neural' / 'next'
    target.mkdir()
    assert reuse_motion_request(tmp_path, target, payload)
    assert json.loads((target/'motion/index.json').read_text())['motions'][0]['motion_json']=='0000.json'
    assert not reuse_motion_request(tmp_path, target, dict(payload, seed=999))
    record['motion_json'] = str(tmp_path/'outside.json')
    (tmp_path/'outside.json').write_text(json.dumps(dict(features=[[0]*133]*4)))
    (motion/'index.json').write_text(json.dumps(index))
    assert not reuse_motion_request(tmp_path, target, payload)
