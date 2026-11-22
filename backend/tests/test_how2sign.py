import csv,json,subprocess,zipfile
from backend.app import how2sign
from backend.app.core import binary

def test_phrase_matches_across_asr_segments_without_fuzzy_substitution(monkeypatch):
    entry={'id':'fixture','text':'This is a test.','duration':2,'video_url':'/fixture.mp4'}
    monkeypatch.setattr(how2sign,'catalog',lambda:[entry])
    result=how2sign.translate_asl('',[{'text':'This is','start':0,'end':1},{'text':'a test!','start':1,'end':2}])
    assert result['coverage']==100
    assert result['items'][0]['video_url']=='/fixture.mp4'
    assert result['items'][0]['verified'] is False
    assert how2sign.translate_asl('This is another test')['coverage']==0
    assert how2sign.translate_asl('',[{'text':'This is a test','start':0,'end':.1}])['coverage']==0

def test_safe_small_import_uses_real_metadata_and_probe(tmp_path,monkeypatch):
    base=tmp_path/'dataset';base.mkdir();clips=base/'clips'
    monkeypatch.setattr(how2sign,'BASE',base);monkeypatch.setattr(how2sign,'CLIPS',clips)
    video=tmp_path/'fixture.mp4'
    subprocess.run([binary('ffmpeg'),'-v','error','-y','-f','lavfi','-i','color=blue:s=160x120:r=12','-t','2','-c:v','libx264',str(video)],check=True)
    with (base/'how2sign_val.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['START','END','SENTENCE_NAME','SENTENCE'],delimiter='\t');writer.writeheader()
        writer.writerow({'START':0,'END':2,'SENTENCE_NAME':'fixture','SENTENCE':'Synthetic importer test only.'})
    with zipfile.ZipFile(base/'val_rgb_front_clips.zip','w') as z:
        z.write(video,'nested/fixture.mp4');z.writestr('../outside.txt','must not extract')
    how2sign.import_available()
    records=how2sign.catalog()
    assert len(records)==1 and not records[0]['verified']
    assert records[0]['language']=='asl' and records[0]['license']=='CC-BY-NC-4.0'
    assert (clips/f"{records[0]['id']}.mp4").exists()
    assert not (tmp_path/'outside.txt').exists()

def test_duplicate_phrase_selects_safe_recording_not_last_entry(monkeypatch):
    base={'text':'This is a test','video_url':'/safe.mp4','duration':2}
    monkeypatch.setattr(how2sign,'catalog',lambda:[dict(base,id='safe'),dict(base,id='slow',duration=20,video_url='/slow.mp4')])
    result=how2sign.translate_asl('',[{'text':base['text'],'start':0,'end':2}])
    assert result['coverage']==100 and result['items'][0]['sign_id']=='safe'

def test_unsafe_long_phrase_does_not_hide_safe_whole_phrase(monkeypatch):
    records=[{'id':'long','text':'Hello there friend','duration':30,'video_url':'/long'},
             {'id':'short','text':'Hello there','duration':1,'video_url':'/short'}]
    monkeypatch.setattr(how2sign,'catalog',lambda:records)
    result=how2sign.translate_asl('',[{'text':'Hello there friend','start':0,'end':1.5}])
    assert result['supported_words']==2 and result['items'][0]['sign_id']=='short'
    assert result['items'][1]['supported'] is False
    records[1]['review_decision']='rejected'
    assert how2sign.translate_asl('Hello there')['coverage']==0

def test_catalog_cache_does_not_leak_mutation_and_refreshes(tmp_path,monkeypatch):
    monkeypatch.setattr(how2sign,'BASE',tmp_path)
    path=tmp_path/'catalog.json'
    path.write_text(json.dumps([{'id':'one','text':'Original'}]))
    how2sign.catalog()[0]['text']='Mutated'
    assert how2sign.catalog()[0]['text']=='Original'
    path.write_text(json.dumps([{'id':'two','text':'Changed contents'}]))
    assert how2sign.catalog()[0]['id']=='two'
