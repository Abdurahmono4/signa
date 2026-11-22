import csv,io,json,tarfile
import numpy as np
import pytest
from scripts.prepare_keypoint_sample import FIELDS,parse_frame,prepare

def person():return {k:[10,20,.8]*n for k,n in FIELDS.items()}

def test_keypoints_preserve_detector_scores_and_mask_ambiguous_people():
    p=person();p['face_keypoints_2d'][2]=1.01007
    points,count=parse_frame({'people':[p]})
    assert count==1 and points['face_keypoints_2d'][0,2]==pytest.approx(1.01007)
    for people in [[],[p,p]]:
        arrays,count=parse_frame({'people':people})
        assert count==len(people) and all(not a.any() for a in arrays.values())
    p['hand_left_keypoints_2d'][2]=-1
    with pytest.raises(ValueError):parse_frame({'people':[p]})

def test_bounded_sample_orders_frames_and_matches_csv_without_training(tmp_path):
    archive=tmp_path/'test.tar.gz';metadata=tmp_path/'test.csv'
    with metadata.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['SENTENCE_NAME','SENTENCE','VIDEO_NAME','START','END'],delimiter='\t');writer.writeheader()
        for clip in ['fixture','second']:writer.writerow({'SENTENCE_NAME':clip,'SENTENCE':'Technical fixture only','VIDEO_NAME':'source','START':0,'END':1})
    with tarfile.open(archive,'w:gz') as t:
        for clip,index in [('fixture',3),('fixture',1),('fixture',2),('second',0)]:
            raw=json.dumps({'people':[person()]}).encode();entry=tarfile.TarInfo(f'json/{clip}/{clip}_{index:012}_keypoints.json');entry.size=len(raw);t.addfile(entry,io.BytesIO(raw))
    output=tmp_path/'sample';report=prepare(archive,metadata,output,limit=1)
    assert report['stop_reason']=='sample_limit' and not report['training_started']
    clip=report['clips'][0];assert clip['frames']==3 and clip['missing_frame_numbers']==0 and clip['fps'] is None and not clip['training_ready']
    with np.load(output/clip['sample_file'],allow_pickle=False) as data:
        assert data['frame_numbers'].tolist()==[1,2,3] and data['hand_left_keypoints_2d'].shape==(3,21,3)
    assert (output/'contact-sheet.png').read_bytes().startswith(b'\x89PNG')
    with pytest.raises(ValueError):prepare(archive,metadata,output,limit=1)
    evaluation=prepare(archive,metadata,tmp_path/'evaluation',limit=1,split='test')
    assert evaluation['split']=='test' and not evaluation['training_started']
    with pytest.raises(ValueError):prepare(archive,metadata,tmp_path/'invalid',split='unknown')
