"""Caption-only fallback plumbing; synthetic motions are never linguistic data."""
import copy,json,threading,uuid
from pathlib import Path
import pytest
from backend.app import neural_engine as engine


def segments():
    return [
        {'id':'0','text':'First supported phrase.','start':0.,'end':1.,'segment_index':0},
        {'id':'1','text':'Unsupported complete phrase.','start':2.,'end':4.,'segment_index':1},
        {'id':'2','text':'Last supported phrase.','start':5.,'end':6.,'segment_index':2},
    ]


def row_for(parts):
    return {'id':uuid.uuid4().hex,'revision':1,'duration':7.,
            'segments':json.dumps([{'text':s['text'],'start':s['start'],'end':s['end']} for s in parts])}


def test_partial_plan_preserves_full_text_timing_and_word_accounting():
    parts=segments();before=copy.deepcopy(parts);row=row_for(parts)
    plan=engine.build_plan(row,parts,[{'id':'0','duration':1.},{'id':'2','duration':1.}],
                           'fixture',[{'chunk_id':'1'}])
    assert parts==before
    assert not plan['complete_translation'] and plan['partial_motion']
    assert plan['playable_signs']==2 and plan['total_phrases']==3
    assert plan['total_words']==9 and plan['signed_words']==6
    assert plan['caption_words']==3 and plan['unsupported_words']==3
    assert plan['unsupported_phrases']==1
    unsupported=next(i for i in plan['items'] if i['status']=='unsupported')
    assert unsupported['text']=='Unsupported complete phrase.'
    assert (unsupported['start'],unsupported['end'])==(2.,4.)
    assert unsupported['clip'] is None and unsupported['rendering']=='unsupported'
    assert unsupported['unsupported_reason']=='tokenizer_unsupported'
    # Every source interval remains on the original media clock, including pauses.
    assert [(i['start'],i['end']) for i in plan['items']]==[(0,1),(1,2),(2,4),(4,5),(5,6),(6,7)]
    assert plan['playback_duration']==7.


def test_rejected_motion_keeps_original_caption_interval():
    parts=segments()
    plan=engine.build_plan(row_for(parts),parts,
        [{'id':'0','duration':1.},{'id':'2','duration':1.}],
        'fixture',[{'chunk_id':'1','reason':'invalid_motion'}])
    item=next(i for i in plan['items'] if i['status']=='unsupported')
    assert item['unsupported_reason']=='invalid_motion'
    assert item['text']==parts[1]['text']
    assert (item['start'],item['end'])==(2.,4.)
    assert plan['caption_words']==3 and plan['playable_signs']==2


def test_only_explicit_preflight_failure_can_become_caption_only():
    parts=segments();row=row_for(parts)
    with pytest.raises(ValueError):engine.build_plan(row,parts,[{'id':'0','duration':1.}], 'fixture',[{'chunk_id':'1'}])
    with pytest.raises(ValueError):engine.build_plan(row,parts,[], 'fixture',[{'chunk_id':'unknown'}])
    with pytest.raises(ValueError):engine.build_plan(row,parts,[], 'fixture',[{'chunk_id':'1'},{'chunk_id':'1'}])
    with pytest.raises(ValueError):engine.build_plan(row,parts,[{'id':'0','duration':1.},{'id':'1','duration':1.},{'id':'2','duration':1.}], 'fixture',[{'chunk_id':'1'}])


def test_no_supported_chunks_never_starts_a_worker(tmp_path,monkeypatch):
    parts=segments();row=row_for(parts)
    def forbidden(*args,**kwargs):raise AssertionError('No worker should start')
    monkeypatch.setattr(engine.threading,'Thread',forbidden)
    with pytest.raises(ValueError,match='avatar ijrosi mavjud emas'):
        engine.enqueue(tmp_path,tmp_path,row,threading.Lock(),lambda:None,
                       unsupported_chunks=[{'chunk_id':s['id']} for s in parts])


def test_runner_receives_only_compatible_chunks_and_full_plan_is_saved(tmp_path,monkeypatch):
    parts=segments();parts[0]['text']='First supported phrase,';row=row_for(parts);key=engine.key_for(row)
    selected=[]
    class Process:
        returncode=0
        def __init__(self,command,**kwargs):
            request=Path(command[command.index('--request')+1]);value=json.loads(request.read_text())
            selected.extend(value['segments'])
            output=Path(command[command.index('--output-dir')+1]);output.mkdir(parents=True)
            (output/'index.json').write_text(json.dumps({'status':'ready','motions':[{'id':s['id'],'duration':1.} for s in value['segments']]}))
            self.stdout=iter([])
        def poll(self):return 0
    monkeypatch.setattr(engine.subprocess,'Popen',Process)
    with engine._guard:engine._states[key]={'status':'queued','progress':0}
    try:
        engine._generate(tmp_path,tmp_path,row,threading.Lock(),lambda:None,threading.Event(),[{'chunk_id':'1'}])
        assert [s['id'] for s in selected]==['0','2']
        assert selected[0]['text']=='First supported phrase.'
        assert all('Unsupported' not in s['text'] for s in selected)
        plan=json.loads((engine.folder(tmp_path,row)/'plan.json').read_text())
        assert next(i for i in plan['items'] if i['clip'])['text']=='First supported phrase,'
        assert plan['unsupported_phrases']==1 and plan['playable_signs']==2
        assert engine.status(tmp_path,row)['status']=='ready'
        assert engine.status(tmp_path,row)['generated_phrases']==2
    finally:
        with engine._guard:engine._states.pop(key,None)
    # Persisted plans report the same fallback after process restart.
    assert engine.status(tmp_path,row)['partial_motion'] is True
    assert engine.status(tmp_path,row)['unsupported_phrases']==1


def test_partial_generation_cancelled_before_model_load_has_no_ready_plan(tmp_path,monkeypatch):
    row=row_for(segments());key=engine.key_for(row);stop=threading.Event();stop.set()
    def forbidden(*args,**kwargs):raise AssertionError('Cancelled request must not load model')
    monkeypatch.setattr(engine.subprocess,'Popen',forbidden)
    with engine._guard:engine._states[key]={'status':'queued','progress':0}
    try:
        engine._generate(tmp_path,tmp_path,row,threading.Lock(),forbidden,stop,[{'chunk_id':'1'}])
        assert engine.status(tmp_path,row)['status']=='cancelled'
        assert not (engine.folder(tmp_path,row)/'plan.json').exists()
    finally:
        with engine._guard:engine._states.pop(key,None)
