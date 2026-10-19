"""Local, reviewed motion corpus. Never fabricate sign-language translations."""
import json
import math
import unicodedata
from typing import Literal
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

router = APIRouter(prefix='/api/signs')
MAX_SPELLING_WORD_LENGTH = 30
MAX_SPELLING_LETTERS = 10000
MAX_SPELLING_HOLD_SECONDS = 3600
QUICK_SIGN_RATE = 1.25
JOINTS = {'head','shoulderL','shoulderR','elbowL','elbowR','wristL','wristR'} | {
    f'finger{side}{finger}{joint}' for side in 'LR' for finger in range(5) for joint in range(3)}


def corpus():
    return json.loads((Path(__file__).parent / 'assets' / 'corpus.json').read_text(encoding='utf-8'))


class Keyframe(BaseModel):
    time: float = Field(ge=0,le=30)
    rotations: dict[str,list[float]] = Field(max_length=50)

    @model_validator(mode='after')
    def validate_pose(self):
        for name, angles in self.rotations.items():
            if name not in JOINTS or len(angles)!=3 or not all(-3.142<=v<=3.142 for v in angles):
                raise ValueError('Unknown joint or invalid XYZ radians')
        return self


class MotionClip(BaseModel):
    purpose: Literal['sign','calibration'] = 'sign'
    phrase: str = Field(min_length=1,max_length=300)
    language: Literal['ASL'] = 'ASL'
    source: str = Field(min_length=3,max_length=500)
    license: str = Field(min_length=2,max_length=150)
    duration: float = Field(gt=0,le=30)
    keyframes: list[Keyframe] = Field(default_factory=list,max_length=1800)
    animation_asset: str | None = None
    kind: Literal['sign','fingerspelling'] = 'sign'
    letter: str | None = Field(default=None,pattern=r'^[A-Z]$')

    @model_validator(mode='after')
    def validate_timeline(self):
        if not self.phrase.strip() or not self.source.strip() or not self.license.strip():
            raise ValueError('Metadata must not be blank')
        if self.animation_asset:
            asset=next((c for c in corpus() if c['id']==self.animation_asset),None)
            if not asset or abs(asset['duration']-self.duration)>.001 or self.keyframes:
                raise ValueError('Unknown motion asset, mixed rig, or incorrect duration')
            self.source=asset['source']
            self.license=asset['license']
            self.kind=asset.get('kind','sign')
            self.letter=asset.get('letter')
            return self
        if self.kind=='fingerspelling' and not self.letter:
            raise ValueError('Fingerspelling requires one ASL alphabet letter')
        if len(self.keyframes)<2:
            raise ValueError('At least two keyframes are required')
        times=[k.time for k in self.keyframes]
        if times[0]!=0 or any(a>=b for a,b in zip(times,times[1:])) or abs(times[-1]-self.duration)>.001:
            raise ValueError('Keyframes must cover 0..duration and strictly increase')
        keys=set(self.keyframes[0].rotations)
        if not keys or any(set(k.rotations)!=keys for k in self.keyframes):
            raise ValueError('Every keyframe must specify the same nonempty set of joints')
        return self


class Review(BaseModel):
    reviewer: str = Field(min_length=2,max_length=120)
    decision: Literal['approved','rejected']
    notes: str = Field(min_length=10,max_length=2000)


def connection():
    from .main import connect
    return connect()


def init_signs(db):
    db.execute('''CREATE TABLE IF NOT EXISTS signs (
        id TEXT PRIMARY KEY, clip TEXT, status TEXT DEFAULT 'draft', reviewer TEXT,
        review_notes TEXT, created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    )''')


def serialize(row):
    return {'id':row['id'],**json.loads(row['clip']),'status':row['status'],
            'reviewer':row['reviewer'],'review_notes':row['review_notes']}


@router.get('')
def list_clips():
    with connection() as db:
        return [serialize(row) for row in db.execute('SELECT * FROM signs ORDER BY created_at DESC')]


@router.get('/corpus')
def list_corpus():
    return corpus()


@router.post('/corpus/{asset_id}/import',status_code=201)
def import_corpus(asset_id: str):
    asset=next((c for c in corpus() if c['id']==asset_id),None)
    if not asset:
        raise HTTPException(404,'Harakat topilmadi.')
    # Import never certifies linguistic quality; review remains an explicit step.
    return import_clip(MotionClip(**{k:asset[k] for k in
        ('phrase','language','source','license','duration','animation_asset')}))


@router.post('',status_code=201)
def import_clip(clip: MotionClip):
    clip_id=uuid.uuid4().hex
    with connection() as db:
        db.execute('INSERT INTO signs (id,clip) VALUES (?,?)',(clip_id,clip.model_dump_json()))
    return {'id':clip_id,'status':'draft'}


@router.post('/{clip_id}/review')
def review_clip(clip_id: str, review: Review):
    if len(review.reviewer.strip())<2 or len(review.notes.strip())<10:
        raise HTTPException(422,'Tekshiruvchi va tekshirish izohini to‘ldiring.')
    with connection() as db:
        row=db.execute('SELECT * FROM signs WHERE id=?',(clip_id,)).fetchone()
        if not row:
            raise HTTPException(404,'Klip topilmadi.')
        if review.decision=='approved' and json.loads(row['clip']).get('purpose')=='calibration':
            raise HTTPException(422,'Kalibrlash klipi ASL tarjimasi sifatida tasdiqlanmaydi.')
        db.execute('UPDATE signs SET status=?,reviewer=?,review_notes=? WHERE id=?',
                   (review.decision,review.reviewer.strip(),review.notes.strip(),clip_id))
    return {'id':clip_id,'status':review.decision}


def normalized(text, casefold=True):
    # Keep unknown names/scripts in the coverage denominator. Punctuation is a
    # token boundary, while internal apostrophes are normalized consistently.
    text=unicodedata.normalize('NFKC',text)
    if casefold:
        text=text.casefold()
    text=text.translate(str.maketrans({
        '\u2018':"'",'\u2019':"'",'\u02bc':"'",'\uff07':"'"}))
    is_word=lambda char: unicodedata.category(char)[0] in {'L','N','M'}
    tokens=[]
    token=[]
    for index,char in enumerate(text):
        if is_word(char) or (char=="'" and token and index+1<len(text) and is_word(text[index+1])):
            token.append(char)
        elif token:
            tokens.append(''.join(token));token=[]
    if token:
        tokens.append(''.join(token))
    return ' '.join(tokens)


def available_clips(include_source=False, include_fingerspelling=False):
    """Load reviewed ASL entries; legacy calibration rows are never translations."""
    with connection() as db:
        clips=[serialize(row) for row in db.execute("SELECT * FROM signs WHERE status='approved' ORDER BY created_at DESC")]
    if include_source:
        clips += corpus()
    return [clip for clip in clips if clip.get('purpose', 'sign')=='sign'
            and clip.get('language', 'ASL')=='ASL'
            and (include_fingerspelling or (clip.get('kind')!='fingerspelling'
                 and not str(clip.get('animation_asset','')).startswith('asl-letter-')))]


def fingerspelling_alphabet(include_source=False):
    alphabet={}
    canonical={asset['id']:asset for asset in corpus() if asset.get('kind')=='fingerspelling'}
    for clip in available_clips(include_source,include_fingerspelling=True):
        asset=canonical.get(clip.get('animation_asset'))
        if not asset:
            continue
        letter=asset.get('letter')
        duration=asset.get('duration',0)
        if (isinstance(letter,str) and len(letter)==1
                and 'A'<=letter<='Z' and clip.get('animation_asset')
                and isinstance(duration,(int,float)) and math.isfinite(duration) and 0<duration<=30):
            alphabet.setdefault(letter,{**clip,'kind':'fingerspelling','letter':letter,'duration':duration})
    return alphabet


def clip_status(clip, start, end):
    if clip is None:
        return 'missing'
    if not clip.get('animation_asset'):
        return 'unsupported_rig'
    rate=clip['duration']/max(.001,end-start)
    if not .5<=rate<=2:
        return 'timing_review'
    return 'source_preview' if clip.get('status')=='source' else 'matched'


def lexical_plan(segments, include_source=False):
    """Timed dictionary aid, not a grammatical English-to-ASL translator.

    Longest phrase wins. Never silently discard unknown words. Edited transcripts
    have no reliable word alignment, so explicitly mark interpolated timings.
    """
    lookup={}
    for clip in available_clips(include_source):
        key=tuple(normalized(clip['phrase']).split())
        # A playable asset takes precedence over a legacy geometric rig. Within
        # each rig type, approved/newer entries precede source previews.
        previous=lookup.get(key)
        if key and (previous is None or not previous.get('animation_asset') and clip.get('animation_asset')):
            lookup[key]=clip
    lengths=sorted({len(key) for key in lookup if key}, reverse=True)
    items=[]
    for si, segment in enumerate(segments):
        words=[]
        raw=segment.get('words') or []
        aligned=not segment.get('edited') and normalized(' '.join(w['word'] for w in raw))==normalized(segment['text'])
        if aligned and raw:
            for word in raw:
                tokens=normalized(word['word']).split()
                display_tokens=normalized(word['word'],casefold=False).split()
                for j, token in enumerate(tokens):
                    width=(word['end']-word['start'])/len(tokens)
                    words.append((token,word['start']+j*width,word['start']+(j+1)*width,
                                  display_tokens[j] if len(display_tokens)==len(tokens) else token))
        else:
            tokens=normalized(segment['text']).split()
            display_tokens=normalized(segment['text'],casefold=False).split()
            width=(segment['end']-segment['start'])/max(1,len(tokens))
            words=[(t,segment['start']+i*width,segment['start']+(i+1)*width,
                    display_tokens[i] if len(display_tokens)==len(tokens) else t) for i,t in enumerate(tokens)]
        i=0
        while i<len(words):
            match=None
            count=1
            for length in lengths:
                key=tuple(w[0] for w in words[i:i+length])
                if len(key)==length and key in lookup:
                    match=lookup[key];count=length;break
            start=max(segment['start'],words[i][1])
            end=min(segment['end'],words[i+count-1][2])
            if end<=start:
                end=min(segment['end'],start+.01)
            items.append({'segment_index':si,'start':start,'end':end,
                          'text':' '.join(w[0] for w in words[i:i+count]),
                          'word_text':' '.join(w[3] for w in words[i:i+count]),
                          'status':clip_status(match,start,end),
                          'clip':match,'word_count':count,'timing':'aligned' if aligned and raw else 'estimated'})
            i+=count
    total_words=sum(x['word_count'] for x in items)
    covered=sum(x['word_count'] for x in items if x['status'] in {'matched','source_preview'})
    return {'mode':'dictionary_assistance','items':items,'total':len(items),
            'matched':sum(x['status']=='matched' for x in items),
            'source_previews':sum(x['status']=='source_preview' for x in items),
            'timing_review':sum(x['status']=='timing_review' for x in items),
            'unsupported_rig':sum(x['status']=='unsupported_rig' for x in items),
            'missing':sum(x['status']=='missing' for x in items),
            'covered_words':covered,'total_words':total_words,
            'coverage':round(100*covered/max(1,total_words)),
            'missing_words':list(dict.fromkeys(x['text'] for x in items if not x['clip']))}


def playback_plan(segments, media_duration, include_source=False, fingerspelling=False):
    """Schedule quick dictionary words or optional natural-rate fingerspelling.

    start/end and media_start/media_end retain the transcript's source timing.
    media_play_start/media_play_end partition that timeline without replaying
    overlapping aligned words. playback_start/playback_end are a separate,
    sequential wall-clock schedule, including holds and all media gaps. Quick
    word mode never adds spelling holds; recorded sign speed is capped at 1.25x.
    """
    lexical=lexical_plan(segments,include_source=include_source)
    alphabet=fingerspelling_alphabet(include_source) if fingerspelling else {}
    canonical_assets={asset['id']:asset for asset in corpus()}
    media_duration=max(0,float(media_duration))
    items=[]
    media_cursor=0.0
    playback_cursor=0.0
    spelling_letters=0
    spelling_holds=0.0
    limited_words=[]
    limit_reasons={}

    def append_item(item, media_start, media_end, clip=None, rendering=None, **metadata):
        nonlocal playback_cursor
        media_span=max(0,media_end-media_start)
        clip_start=0.0
        clip_end=float(clip['duration']) if clip else 0.0
        playback_rate=1.0 if fingerspelling or not clip else QUICK_SIGN_RATE
        if clip and not fingerspelling:
            # Only the canonical asset may supply a validated source window;
            # never take trimming instructions from a user-imported clip.
            asset=canonical_assets.get(clip.get('animation_asset'),{})
            window=asset.get('playback_window')
            if isinstance(window,dict) and window.get('verified') is True:
                start,end=window.get('start'),window.get('end')
                if (isinstance(start,(int,float)) and isinstance(end,(int,float))
                        and math.isfinite(start) and math.isfinite(end) and 0<=start<end<=clip_end):
                    clip_start,clip_end=float(start),float(end)
        duration=(clip_end-clip_start)/playback_rate if clip else media_span
        slot=max(media_span,duration)
        status=('source_preview' if clip.get('status')=='source' else 'matched') if clip else item['status']
        if clip:
            # Keep provenance and playback metadata, without repeating poses.
            clip={key:clip[key] for key in ('id','phrase','duration','animation_asset',
                'status','source','license','purpose','language','kind','letter') if key in clip}
            clip['keyframes']=[]
        items.append({**item,'status':status,'sync_status':item['status'],
                      'rendering':rendering or ('sign' if clip else 'caption'),
                      'word_text':item.get('word_text',item['text']),'letter':None,**metadata,
                      'media_start':item['start'],'media_end':item['end'],
                      'media_play_start':media_start,'media_play_end':media_end,
                      'duration':duration,'slot_duration':slot,
                      'clip_start':clip_start,'clip_end':clip_end,'playback_rate':playback_rate,
                      'hold_duration':max(0,duration-media_span),
                      'playback_start':playback_cursor,'playback_end':playback_cursor+slot,
                      'clip':clip})
        playback_cursor+=slot

    def append_gap(start,end):
        if end>start:
            append_item({'segment_index':None,'start':start,'end':end,'text':'',
                         'status':'gap','timing':'gap','word_count':0},start,end,rendering='gap')

    for item in sorted(lexical['items'],key=lambda item:(item['start'],item['segment_index'])):
        source_start=max(0,min(media_duration,item['start']))
        source_end=max(source_start,min(media_duration,item['end']))
        append_gap(media_cursor,source_start)
        play_start=max(media_cursor,source_start)
        play_end=max(play_start,source_end)
        clip=item['clip']
        if clip and clip.get('animation_asset'):
            append_item(item,play_start,play_end,clip)
        else:
            # ASL's recorded manual alphabet is a fallback for one Latin word.
            # Never imply that fingerspelling supplies ASL grammar or invent a
            # pose. A missing letter rejects the entire word, not just a part.
            source_letters=item.get('word_text',item['text']).replace("'",'')
            letters=source_letters.upper()
            eligible=(item['word_count']==1 and letters and
                      all('A'<=letter<='Z' or 'a'<=letter<='z' for letter in source_letters) and
                      all(letter in alphabet for letter in letters))
            reason=None
            if eligible:
                if len(letters)>MAX_SPELLING_WORD_LENGTH:
                    reason='word_length'
                elif spelling_letters+len(letters)>MAX_SPELLING_LETTERS:
                    reason='letter_budget'
                else:
                    span=play_end-play_start
                    added=max(0,alphabet[letters[0]]['duration']-span)+sum(alphabet[letter]['duration'] for letter in letters[1:])
                    if spelling_holds+added>MAX_SPELLING_HOLD_SECONDS:
                        reason='duration_budget'
            if eligible and reason is None:
                for index,letter in enumerate(letters):
                    append_item({**item,'word_count':1 if index==0 else 0},
                                play_start if index==0 else play_end,play_end,alphabet[letter],
                                rendering='fingerspelling',letter=letter,letter_index=index,letter_count=len(letters))
                spelling_letters+=len(letters)
                spelling_holds+=added
            else:
                append_item(item,play_start,play_end)
                if reason:
                    limited_words.append(item['text']);limit_reasons[item['text']]=reason
        media_cursor=play_end
    append_gap(media_cursor,media_duration)
    playable=[item for item in items if item['clip']]
    dictionary=[item for item in playable if item['rendering']=='sign']
    spelled=[item for item in playable if item['rendering']=='fingerspelling']
    limitations=[
        'English speech recognition only; ASL dictionary assistance is not full sentence translation.',
        ('Optional recorded ASL fingerspelling is enabled; this is not a sentence translation.' if fingerspelling else
         'Quick word mode uses dictionary signs and captions; automatic fingerspelling is disabled.'),
        'Words with unsupported characters or missing letters remain in subtitles; no motion is invented.',
        ('Recorded ASL clips play at natural speed. Media may pause to let a sign finish.' if fingerspelling else
         'Recorded dictionary signs play at no more than 1.25x. Unknown words do not add media holds.'),
    ]
    if include_source:
        limitations.append('Source corpus motions are unreviewed previews, not expert-approved translations.')
    if any(item['timing']=='estimated' for item in items):
        limitations.append('Some word timings are estimated from the transcript interval.')
    if limited_words:
        limitations.append('Some words remain in subtitles because bounded spelling limits were reached.')
    return {'mode':'dictionary_assistance','playback':'paced','language':'ASL','input_language':'en',
            'presentation':'fingerspelling' if fingerspelling else 'words','fingerspelling_enabled':fingerspelling,
            'complete_translation':False,'source_preview_enabled':include_source,
            'media_duration':media_duration,'playback_duration':playback_cursor,
            'hold_duration':sum(item['hold_duration'] for item in items),
            'items':items,'playable_signs':len(playable),
            'matched':sum(item['status']=='matched' for item in playable),
            'source_previews':sum(item['status']=='source_preview' for item in playable),
            'total_words':lexical['total_words'],
            'signed_words':sum(item['word_count'] for item in dictionary),
            'spelled_words':sum(item['word_count'] for item in spelled),
            'fingerspelling_letters':len(spelled),'dictionary_signs':len(dictionary),
            'caption_words':sum(item['word_count'] for item in items if item['rendering']=='caption'),
            'dictionary_missing_words':lexical['missing_words'],
            'missing_words':list(dict.fromkeys(item['text'] for item in items if item['rendering']=='caption')),
            'spelling_limits':{'max_word_length':MAX_SPELLING_WORD_LENGTH,'max_letters':MAX_SPELLING_LETTERS,
                               'max_added_seconds':MAX_SPELLING_HOLD_SECONDS,
                               'limited_words':list(dict.fromkeys(limited_words)),'limit_reasons':limit_reasons},
            'limitations':limitations}


def plan(segments, include_source=False):
    clips=available_clips(include_source)
    result=[]
    for index,segment in enumerate(segments):
        # Full utterance match only; no word-by-word concatenation pretending to be ASL.
        match=next((c for c in clips if normalized(c['phrase'])==normalized(segment['text'])),None)
        status=clip_status(match,segment['start'],segment['end'])
        result.append({'segment_index':index,'start':segment['start'],'end':segment['end'],
                       'text':segment['text'],'status':status,
                       'clip':match})
    return {'items':result,'matched':sum(x['status']=='matched' for x in result),
            'source_previews':sum(x['status']=='source_preview' for x in result),'total':len(result)}
