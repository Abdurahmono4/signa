"""Own adapter for the documented SignAvatars schema; no upstream code executed."""
import csv,json,math,os
from pathlib import Path
from .core import ROOT
from . import how2sign

BASE=Path(os.environ.get('SIGNBRIDGE_SIGNAVATARS',str(ROOT/'datasets'/'signavatars')))
REPOSITORY=ROOT/'third_party'/'SignAvatars'
SOURCE_URL='https://github.com/ZhengdiYu/SignAvatars'
# SMPL-X 21 body joint order, excluding the global orientation.
UPPER_BODY=(11,12,13,14,15,16,17,18,19,20)

def build_manifest():
    metadata=REPOSITORY/'datasets/language2motion/text/how2sign_realigned_val.csv'
    if not metadata.exists():raise ValueError('SignAvatars metadata fayli yo‘q.')
    with metadata.open(encoding='utf-8-sig',newline='') as f:
        rows={r['SENTENCE_NAME']:r for r in csv.DictReader(f,delimiter='\t')}
    mapped=[]
    for clip in how2sign.catalog():
        row=rows.get(clip['sentence_name'])
        if row is None:continue
        start,end=float(row['START_REALIGNED']),float(row['END_REALIGNED'])
        if not all(math.isfinite(x) for x in (start,end)) or not 0<=start<end:continue
        mapped.append({'id':clip['id'],'sentence_name':clip['sentence_name'],'text':clip['text'],
                       'video_url':clip['video_url'],'rgb_duration':clip['duration'],
                       'realigned_start':start,'realigned_end':end,
                       'annotation_path':None,'verified':False,'alignment_verified':False})
    return {'repository':SOURCE_URL,'metadata_records':len(rows),'matched_clips':len(mapped),
            'motion_annotations':0,'natural_avatar_available':False,'records':mapped,
            'notice':'Metadata bog‘landi. 3D annotatsiyalar va tabiiy avatar hali olinmagan. Realigned vaqtlar original klipga avtomatik qo‘llanmaydi.'}

def status():
    path=BASE/'manifest.json'
    if not path.exists():return {'prepared':False,'repository':SOURCE_URL,'matched_clips':0,'motion_annotations':0,'natural_avatar_available':False}
    manifest=json.loads(path.read_text(encoding='utf-8'))
    return {k:v for k,v in manifest.items() if k!='records'}|{'prepared':True}

def convert_smplx(data,fps=24):
    """Map 182 channels into the existing 133-channel upper-body convention.

    This converts numeric representation, not sign language or avatar identity.
    Input must be an explicitly exported JSON object, never an uploaded pickle.
    """
    if not isinstance(data,dict):raise ValueError('Annotatsiya JSON obyekt bo‘lsin.')
    if isinstance(fps,bool) or not isinstance(fps,(int,float)) or not math.isfinite(fps) or not 1<=fps<=120:
        raise ValueError('FPS 1–120 oralig‘ida bo‘lsin.')
    rows=data.get('smplx')
    if not isinstance(rows,list) or not 1<=len(rows)<=30000:raise ValueError('1–30000 ta SMPL-X kadr talab qilinadi.')
    indices=data.get('total_valid_index')
    if indices is not None:
        if not isinstance(indices,list) or len(indices)!=len(rows) or any(type(v)!=int or v<0 for v in indices):
            raise ValueError('Kadr indekslari yaroqsiz.')
        if any(b!=a+1 for a,b in zip(indices,indices[1:])):
            raise ValueError('Kadrlar orasida bo‘shliq bor; vaqtni siqmasdan moslashtirish kerak.')
    frames=[]
    for row in rows:
        if not isinstance(row,list) or len(row)!=182 or any(type(v) not in (int,float) or not math.isfinite(v) for v in row):
            raise ValueError('Har bir SMPL-X kadr 182 ta chekli sondan iborat bo‘lsin.')
        body=row[3:66]
        frame=[v for joint in UPPER_BODY for v in body[joint*3:joint*3+3]]+row[66:159]+row[169:179]
        assert len(frame)==133
        frames.append(frame)
    return {'format':'madis-axis-angle-133','normalized':False,'fps':fps,'frames':frames,
            'source':SOURCE_URL,'source_format':'signavatars-smplx-182',
            'source_start_frame':indices[0] if indices else 0,
            'verified':False,'retarget_validated':False,
            'limitations':['Global orientation, lower-body motion, shape and camera translation are not in this upper-body output.',
                           'SMPL-X hand mean and destination bind pose must be calibrated before production use.',
                           'Face coefficients are preserved numerically, not mapped to a natural avatar face.',
                           'Numeric conversion does not establish sign-language correctness.']}
