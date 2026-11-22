from pathlib import Path
p=Path('backend/app/how2sign.py');s=p.read_text(encoding='utf-8');a=s.index('        existing=catalog()');b=s.index('    except (OSError',a)
s=s[:a]+'''        signature={'archive_bytes':archive.stat().st_size,'archive_mtime':archive.stat().st_mtime_ns,'metadata_bytes':metadata.stat().st_size,'version':2}
        marker=BASE/'import-complete.json'
        if marker.exists() and json.loads(marker.read_text())==signature:
            state.update(phase=f'{len(catalog())} ta manba klipi tayyor',error=None,progress=100);return
        state.update(phase='Barcha kliplar import qilinmoqda',error=None,progress=0)
        with metadata.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter='\\t'))
        previous={c['id']:c for c in catalog()};output=[];issues=[]
        from concurrent.futures import ThreadPoolExecutor
        with zipfile.ZipFile(archive) as z:
            members={Path(x.filename).name:x for x in z.infolist() if not x.is_dir() and x.filename.lower().endswith('.mp4')}
            state['archive_videos']=len(members)
            matched=[r for r in rows if r['SENTENCE_NAME']+'.mp4' in members]
            def prepare(row):
                name=row['SENTENCE_NAME']+'.mp4';member=members[name]
                id=hashlib.sha256(name.encode()).hexdigest()[:24];target=CLIPS/f'{id}.mp4'
                try:
                    if member.file_size>200*1024*1024:raise ValueError('Klip 200 MB dan katta')
                    if not target.exists() or target.stat().st_size!=member.file_size:
                        raw=z.read(member)
                        if len(raw)!=member.file_size:raise ValueError('ZIP CRC yoki hajm mos emas')
                        target.write_bytes(raw)
                    info=probe(target);actual=float(info['format']['duration'])
                    stream=next(s for s in info['streams'] if s['codec_type']=='video')
                    if not .05<actual<=300:raise ValueError('Davomiylik yaroqsiz')
                    expected=float(row['END'])-float(row['START'])
                    return {'id':id,'text':row['SENTENCE'],'sentence_name':row['SENTENCE_NAME'],
                        'duration':actual,'language':'asl','verified':False,'source':'https://how2sign.github.io/',
                        'license':'CC-BY-NC-4.0','video_url':f'/api/how2sign/clips/{id}',
                        'width':stream['width'],'height':stream['height'],'technical_valid':True,
                        'alignment_delta':round(abs(actual-expected),3),
                        'alignment':'Original timestamp; manual review required'},None
                except Exception as e:return None,{'sentence_name':row['SENTENCE_NAME'],'reason':str(e)[:160]}
            with ThreadPoolExecutor(max_workers=4) as workers:
                for index,(record,issue) in enumerate(workers.map(prepare,matched)):
                    if record:output.append(record)
                    if issue:issues.append(issue)
                    state.update(progress=round(100*(index+1)/max(1,len(matched))),processed=index+1,imported=len(output),rejected=len(issues),total=len(matched))
                    if (index+1)%50==0:
                        temporary=BASE/'catalog.tmp';temporary.write_text(json.dumps(output,ensure_ascii=False),encoding='utf-8');temporary.replace(BASE/'catalog.json')
            names={r['SENTENCE_NAME']+'.mp4' for r in matched}
            unmatched=sorted(set(members)-names)
        temporary=BASE/'catalog.tmp';temporary.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(BASE/'catalog.json')
        (BASE/'technical-audit.json').write_text(json.dumps({'archive_videos':len(members),'csv_rows':len(rows),'matched_rows':len(matched),'valid_clips':len(output),'issues':issues,'unmatched_files':unmatched,'linguistic_verified':0},ensure_ascii=False,indent=2),encoding='utf-8')
        marker.write_text(json.dumps(signature),encoding='utf-8')
        state.update(phase=f'{len(output)} ta manba klipi tayyor',error=None,progress=100)
'''+s[b:];p.write_text(s,encoding='utf-8')
