"""Prepare a group-blind grading sheet and count reviewed ASL comprehension sessions."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def validate(key, answer):
    if answer.get('purpose') != 'review':
        raise ValueError('Mashq javoblari inson tushunarliligi bahosiga kiritilmaydi.')
    if answer.get('protocol') != key['protocol'] or answer.get('form') not in key['forms']:
        raise ValueError('Sinov versiyasi yoki shakli mos emas.')
    if not re.fullmatch(r'[a-f0-9]{24}', str(answer.get('session',''))):
        raise ValueError('Sessiya identifikatori yaroqsiz.')
    expected = key['forms'][answer['form']]
    rows = answer['responses']
    if len(rows)!=len(expected) or {r['stimulus'] for r in rows}!=set(expected):
        raise ValueError('Stimullar takrorlangan yoki to‘liq emas.')
    for r in rows:
        status, text, plays = r['status'], r['meaning'], r['completed_plays']
        if status not in ('not_understood','paraphrase','playback_failure') or not isinstance(text,str) or len(text)>1500:
            raise ValueError('Javob yaroqsiz.')
        if (status=='paraphrase') != bool(text.strip()):
            raise ValueError('Javob holati va matni mos emas.')
        if not isinstance(plays,int) or plays < 0:
            raise ValueError('Ijro soni yaroqsiz.')
        if status!='playback_failure' and (plays < 1 or r['hand_clarity'] not in ('clear','partly','unclear','unsure')):
            raise ValueError('Ijro yoki qo‘l aniqligi bahosi yetishmaydi.')
    return rows


def prepare(key, answer, dest):
    rows=validate(key,answer)
    items=[]
    for r in rows:
        code=r['stimulus']
        fixed=r['status'] if r['status']!='paraphrase' else None
        items.append({'stimulus':code,'intended_meaning':key['items'][code]['text'],
                      'participant_meaning':r['meaning'],'grade':fixed})
    sheet={'protocol':key['protocol'],'session':answer['session'],'items':items}
    with dest.open('x',encoding='utf-8') as f:
        json.dump(sheet,f,ensure_ascii=False,indent=2)
    return sheet


def tally(key, pairs):
    sessions=set()
    forms=Counter()
    meaning={k:Counter() for k in ('avatar','human')}
    hands={k:Counter() for k in meaning}
    for answer, sheet in pairs:
        rows=validate(key,answer)
        session=answer['session']
        if session in sessions or sheet.get('session')!=session or sheet.get('protocol')!=key['protocol']:
            raise ValueError('Takroriy sessiya yoki boshqa javobga tegishli baho.')
        sessions.add(session);forms[answer['form']]+=1
        by_code={r['stimulus']:r for r in sheet['items']}
        if len(sheet['items'])!=len(rows) or set(by_code)!={r['stimulus'] for r in rows}:
            raise ValueError('Baholar va javoblar mos emas.')
        for r in rows:
            code=r['stimulus'];record=by_code[code];grade=record['grade'];item=key['items'][code]
            if record['participant_meaning']!=r['meaning'] or record['intended_meaning']!=item['text']:
                raise ValueError('Baholashdagi matn o‘zgargan.')
            allowed=('full','partial','different','indeterminate') if r['status']=='paraphrase' else (r['status'],)
            if grade not in allowed:raise ValueError('Har bir erkin javobni inson baholovchi baholashi kerak.')
            meaning[item['kind']][grade]+=1
            if r['status']!='playback_failure':hands[item['kind']][r['hand_clarity']]+=1
    cohorts={}
    for k,counts in meaning.items():
        denominator=counts.total()-counts['playback_failure']
        cohorts[k]={'meaning_grades':dict(counts),'hand_clarity':dict(hands[k]),
                    'fully_correct':counts['full'],'played_responses':denominator,
                    'fully_correct_fraction':counts['full']/denominator if denominator else None}
    return {'protocol':key['protocol'],'reviewed_sessions':len(sessions),'forms':dict(forms),'outcomes':cohorts}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--key',type=Path,required=True)
    commands=p.add_subparsers(dest='action',required=True)
    create=commands.add_parser('prepare');create.add_argument('answer',type=Path);create.add_argument('output',type=Path)
    count=commands.add_parser('tally');count.add_argument('--pair',action='append',nargs=2,type=Path,required=True,metavar=('ANSWER','GRADES'))
    args=p.parse_args()
    try:
        key=read(args.key)
        if args.action=='prepare':
            prepare(key,read(args.answer),args.output);print('Baholash fayli yaratildi.')
        else:
            print(json.dumps(tally(key,[(read(a),read(g)) for a,g in args.pair]),ensure_ascii=False,indent=2))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        p.exit(2,str(exc)+'\n')
