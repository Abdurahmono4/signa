import gzip,zipfile,json
from scripts.verify_evaluation_archives import verify

def test_full_read_reports_bad_crc_and_continues_other_entries(tmp_path):
    front=tmp_path/'train_rgb_front_clips.zip'
    with zipfile.ZipFile(front,'w',compression=zipfile.ZIP_STORED) as z:
        z.writestr('bad.mp4',b'bad payload');z.writestr('good.mp4',b'good payload')
    raw=front.read_bytes();assert raw.count(b'bad payload')==1
    front.write_bytes(raw.replace(b'bad payload',b'BAD payload'))
    with zipfile.ZipFile(tmp_path/'train_rgb_side_clips.zip','w') as z:z.writestr('side.mp4',b'side')
    with gzip.open(tmp_path/'train_2D_keypoints.tar.gz','wb') as f:f.write(b'fixture stream only')
    report=verify(tmp_path,tmp_path/'report.json',('train',))
    assert not report['all_complete']
    first=report['archives'][0]
    assert first['files_read']==2 and first['all_payloads_checked'] and not first['complete']
    assert first['failed_entries'][0]['member']=='bad.mp4'
    assert report['archives'][1]['complete'] and report['archives'][2]['complete']
    assert json.loads((tmp_path/'report.json').read_text())==report

def test_broken_gzip_records_failure_without_losing_report(tmp_path):
    path=tmp_path/'train_2D_keypoints.tar.gz'
    path.write_bytes(b'\x1f\x8b\x08\x00'+bytes(6)+b'\xff'*30)
    output=tmp_path/'report.json'
    result=verify(tmp_path,output,('train',),('2D_keypoints.tar.gz',))
    assert not result['all_complete'] and result['archives'][0]['error']
    assert output.is_file()
