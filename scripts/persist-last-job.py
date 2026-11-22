from pathlib import Path
p=Path('frontend/src/main.tsx');s=p.read_text(encoding='utf-8')
needle=' const coverage=mode'
pos=s.index(needle)
s=s[:pos]+''' useEffect(()=>{const id=new URLSearchParams(location.search).get('job')||sessionStorage.getItem('signbridge-last-job');if(id&&/^[a-f0-9]{32}$/.test(id))api<Job>('/jobs/'+id).then(setJob).catch(()=>{})},[]);
 useEffect(()=>{if(job)sessionStorage.setItem('signbridge-last-job',job.id)},[job?.id]);
'''+s[pos:]
s=s.replace('so‘z tekshirilgan to‘liq ibora tarkibida.', 'so‘z mos to‘liq ibora tarkibida.')
s=s.replace("{ready?'AVATAR TAYYOR':'YUKLANMOQDA'}", "{ready?'IJRO TAYYOR':'YUKLANMOQDA'}")
s=s.replace('<p className="muted">Barmoqli skelet animatsiyasi. O‘zbekcha ishoralar faqat tekshirilgan kutubxonadan ijro etiladi.</p>', '<p className="muted">{settings.language===\'en\'&&!demo?\'How2Sign haqiqiy inson videosi · ASL · tadqiqot namunasi.\':\'Barmoqli skelet animatsiyasi · 3D texnik namuna.\'}</p>')
p.write_text(s,encoding='utf-8')
