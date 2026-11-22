from pathlib import Path
p=Path('frontend/src/main.tsx');s=p.read_text(encoding='utf-8').replace("page==='studio'?'Studiya':page==='library'?'Kutubxona':'Sozlamalar'", "page==='studio'?'Studiya':page==='corpus'?'ASL video kutubxonasi':page==='library'?'Animatsiya importi':'Sozlamalar'")
s=s.replace("page==='studio'?'Har bir ovoz tushunarli bo‘lsin.':page==='library'", "page==='studio'?'Har bir ovoz tushunarli bo‘lsin.':page==='corpus'?'1 739 video. Qidiriladigan ASL kutubxonasi.':page==='library'")
s=s.replace("api<Sequence>('/jobs/'+job.id+'/neural/plan')", "api<Sequence>('/jobs/'+job.id+'/neural/plan')")
p.write_text(s,encoding='utf-8')
