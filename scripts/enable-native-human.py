from pathlib import Path
p=Path(r'D:\SignBridge-UZ\frontend\src\main.tsx');s=p.read_text(encoding='utf-8')
a="api<{token:string;frames:number;fps:number}>(`/jobs/${job.id}/render/start`,json(settings));"
b="api<{token:string;frames:number;fps:number;mode?:string}>(`/jobs/${job.id}/render/start`,json({...settings,native_human:true}));if(session.mode==='native'){setJob(await api<Job>('/jobs/'+job.id));return}"
assert a in s;s=s.replace(a,b,1)
p.write_text(s,encoding='utf-8')
