import re
import unicodedata

def normalize(text):
    text=unicodedata.normalize('NFKC',text).lower()
    for char in 'ʻʼ‘’`´': text=text.replace(char,"'")
    return ' '.join(re.findall(r"[a-zа-яё0-9]+(?:'[a-z]+)*",text))

def translate(text, timestamps, signs):
    # Only whole verified phrases; concatenating isolated glosses is not grammar.
    available={normalize(s['label']):s for s in signs if s['language']=='uz_sign' and s['verified'] and s.get('animation_path')}
    segments=timestamps or [{'text':text,'start':0,'end':max(2,len(text.split())*.7)}]
    items=[]; supported=0; total=0
    for segment in segments:
        key=normalize(segment['text']); count=len(key.split());total+=count
        sign=available.get(key)
        timing_issue=False
        if sign:
            rate=(sign.get('duration_ms') or 0)/1000/max(.001,segment['end']-segment['start'])
            if not .5<=rate<=2:
                sign=None;timing_issue=True
        supported+=count if sign else 0
        items.append({**segment,'sign_id':sign['id'] if sign else None,
                      'animation_path':sign['animation_path'] if sign else None,
                      'duration_ms':sign['duration_ms'] if sign else None,
                      'supported':bool(sign),'confidence':1.0 if sign else 0.0,
                      'reason':'Tekshirilgan to‘liq ibora' if sign else 'Ishora va nutq tezligi mos emas; subtitr ko‘rsatiladi' if timing_issue else 'Tekshirilgan to‘liq ibora topilmadi; subtitr ko‘rsatiladi'})
    return {'items':items,'coverage':round(100*supported/max(1,total)), 'supported_words':supported,'total_words':total,
            'confidence_kind':'Lug‘at mosligi; lingvistik aniqlik o‘lchovi emas'}
