import zipfile
from fastapi.testclient import TestClient
from backend.app import dataset_status,how2sign,main

def csv_file(base,split='test'):
    (base/f'how2sign_{split}.csv').write_text('SENTENCE_NAME\tSENTENCE\na\tFirst phrase\nb\tSecond phrase\n',encoding='utf-8')

def test_metadata_and_held_out_split_never_extract(tmp_path):
    csv_file(tmp_path)
    result=dataset_status.inventory(tmp_path,[])
    test=result['splits'][2]
    assert test['state']=='metadata_only' and test['csv_rows']==2
    assert test['role']=='held_out_evaluation' and not result['training_performed']
    assert not result['extracted']

def test_partial_archive_is_not_opened(tmp_path,monkeypatch):
    csv_file(tmp_path)
    (tmp_path/'test_rgb_front_clips.zip').write_bytes(b'incomplete')
    (tmp_path/'test_rgb_front_clips.zip.crdownload').write_bytes(b'partial')
    def forbidden(*args):raise AssertionError('Partial ZIP must not be read')
    monkeypatch.setattr(dataset_status,'archive',forbidden)
    result=dataset_status.inventory(tmp_path,[])['splits'][2]
    assert result['state']=='downloading' and result['downloads_in_progress']==1

def test_catalog_reports_missing_without_extract_or_false_crc(tmp_path):
    csv_file(tmp_path)
    with zipfile.ZipFile(tmp_path/'test_rgb_front_clips.zip','w') as z:
        z.writestr('nested/a.mp4',b'synthetic inventory entry, not real video')
        z.writestr('nested/extra.mp4',b'inventory only')
    result=dataset_status.inventory(tmp_path,[])['splits'][2]
    assert result['state']=='incomplete'
    assert result['matched_clips']==1 and result['missing_clips']==1 and result['extra_clips']==1
    assert result['crc_checked'] is False and not (tmp_path/'nested').exists()

def test_unsafe_zip_and_bad_metadata_are_reported(tmp_path):
    csv_file(tmp_path)
    with zipfile.ZipFile(tmp_path/'test_rgb_front_clips.zip','w') as z:z.writestr('../a.mp4',b'unsafe')
    assert dataset_status.inventory(tmp_path,[])['splits'][2]['state']=='invalid'
    (tmp_path/'how2sign_test.csv').write_text('wrong\tcolumns\n')
    assert dataset_status.inventory(tmp_path,[])['splits'][2]['state']=='invalid'

def test_endpoint_no_local_paths_and_cache_refresh(tmp_path,monkeypatch):
    csv_file(tmp_path)
    archive=tmp_path/'test_rgb_front_clips.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('a.mp4',b'one')
    assert dataset_status.inventory(tmp_path,[])['splits'][2]['missing_clips']==1
    with zipfile.ZipFile(archive,'a') as z:z.writestr('b.mp4',b'two')
    monkeypatch.setattr(how2sign,'BASE',tmp_path)
    response=TestClient(main.app).get('/api/how2sign/dataset/status')
    assert response.status_code==200
    assert response.json()['splits'][2]['state']=='indexed'
    assert str(tmp_path) not in response.text
