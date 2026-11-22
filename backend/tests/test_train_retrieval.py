"""Synthetic media tests validate retrieval plumbing, not sign-language accuracy."""
import csv, subprocess, zipfile
import pytest
import json
from fastapi.testclient import TestClient
from backend.app import how2sign, train_catalog, main
from backend.app.core import binary

@pytest.fixture
def corpus(tmp_path, monkeypatch):
    base=tmp_path/'corpus';base.mkdir()
    monkeypatch.setattr(how2sign,'BASE',base)
    monkeypatch.setattr(how2sign,'catalog',lambda:[])
    video=tmp_path/'synthetic.mp4'
    subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=blue:s=160x120:r=12','-t','1','-c:v','libx264',str(video)],check=True)
    with (base/'how2sign_train.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['START','END','SENTENCE_NAME','SENTENCE'],delimiter='\t');writer.writeheader()
        for name,text in [('fixture','Synthetic retrieval test only.'),('missing','Absent source video.')]:
            writer.writerow(dict(START=0,END=99,SENTENCE_NAME=name,SENTENCE=text))
    with zipfile.ZipFile(base/'train_rgb_front_clips.zip','w') as z:
        z.write(video,'nested/fixture.mp4');z.write(video,'../unsafe.mp4')
    return base,video

def test_index_is_lazy_and_counts_missing(corpus):
    base,_=corpus
    status=train_catalog.status(base)
    assert status['records']==1 and status['missing_rows']==1
    assert not status['training_performed'] and not status['verified']
    assert status['cached_clips']==0 and not (base/'unsafe.mp4').exists()

def test_exact_phrase_uses_probed_duration_not_csv_hint(corpus):
    result=how2sign.translate_asl('Synthetic retrieval test only!')
    assert result['coverage']==100
    item=result['items'][0]
    assert item['split']=='train' and item['verified'] is False
    assert 900<=item['duration_ms']<=1100
    assert how2sign.translate_asl('Synthetic different test only')['coverage']==0
    assert how2sign.translate_asl('',[{'text':'Synthetic retrieval test only','start':0,'end':.1}])['coverage']==0

def test_clip_route_and_path_safety(corpus):
    base,video=corpus
    ident=next(iter(train_catalog.index(base)['byid']))
    client=TestClient(main.app)
    assert client.get('/api/how2sign/train/status').json()['records']==1
    response=client.get('/api/how2sign/train/clips/'+ident)
    assert response.status_code==200 and response.content==video.read_bytes()
    assert client.get('/api/how2sign/train/clips/'+'0'*24).status_code==404
    with pytest.raises(ValueError):train_catalog.resolve(base,'../outside')

def test_cache_limit_refuses_extraction(corpus,monkeypatch):
    base,_=corpus
    ident=next(iter(train_catalog.index(base)['byid']))
    monkeypatch.setattr(train_catalog,'MAX_CACHE',1)
    with pytest.raises(ValueError,match='2 GB'):train_catalog.resolve(base,ident)
    assert not list((base/'train-cache').rglob('*.mp4'))

def test_corrupt_clip_exclusion_refreshes_index_and_rejects_lookup(corpus):
    base,_=corpus;data=train_catalog.index(base);ident=next(iter(data['byid']))
    record=data['byid'][ident];stat=(base/'train_rgb_front_clips.zip').stat()
    (base/'train-exclusions.json').write_text(json.dumps({'archive_bytes':stat.st_size,'archive_mtime_ns':stat.st_mtime_ns,'members':[record['member']]}))
    assert train_catalog.status(base)['excluded_corrupt_clips']==1
    assert train_catalog.status(base)['records']==0
    assert how2sign.translate_asl('Synthetic retrieval test only')['coverage']==0
    with pytest.raises(ValueError):train_catalog.resolve(base,ident)


def test_saved_index_survives_memory_cache_reset_with_exclusions(corpus,monkeypatch):
    base,_=corpus
    stat=(base/'train_rgb_front_clips.zip').stat()
    (base/'train-exclusions.json').write_text(json.dumps({
        'archive_bytes':stat.st_size,'archive_mtime_ns':stat.st_mtime_ns,'members':[]}))
    expected=train_catalog.index(base)['lookup']
    train_catalog._load.cache_clear()
    def forbidden(*args,**kwargs):
        raise AssertionError('An unchanged persisted index must not reopen the ZIP')
    monkeypatch.setattr(train_catalog.zipfile,'ZipFile',forbidden)
    reloaded=train_catalog.index(base)
    assert reloaded['lookup']==expected
    assert reloaded['first_lengths']=={'synthetic':frozenset({4})}


def test_repeated_phrase_resolves_once_but_checks_each_time_slot(corpus,monkeypatch):
    original=train_catalog.resolve;calls=[]
    def counted(base,ident):
        calls.append(ident)
        return original(base,ident)
    monkeypatch.setattr(train_catalog,'resolve',counted)
    phrase='Synthetic retrieval test only.'
    result=how2sign.translate_asl('',[
        {'text':phrase,'start':0,'end':1},
        {'text':phrase,'start':1,'end':1.1},
        {'text':phrase,'start':2,'end':3}])
    assert len(calls)==1
    assert result['supported_words']==8 and result['total_words']==12
    supported=[item for item in result['items'] if item['supported']]
    assert [(item['start'],item['end']) for item in supported]==[(0,1),(2,3)]
