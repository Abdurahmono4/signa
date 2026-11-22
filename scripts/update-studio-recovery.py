from pathlib import Path
p=Path(r'D:\SignBridge-UZ\frontend\src\main.tsx')
s=p.read_text(encoding='utf-8')
def swap(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b,1)
swap("phase:string;language?:'en'|'uz';", "phase:string;settings?:{engine?:string;layout?:string;resolution?:number;size?:number;position?:string;subtitles?:boolean;cropMode?:'center'|'full';removeGreen?:boolean};language?:'en'|'uz';")
swap("useEffect(()=>{api<{ok:boolean}>('/health').then(h=>setHealth(h.ok)).catch(()=>setHealth(false));refresh()},[]);", "useEffect(()=>{let active=true;const check=()=>api<{ok:boolean}>('/health',{signal:AbortSignal.timeout(4000)}).then(h=>{if(active)setHealth(h.ok)}).catch(()=>{if(active)setHealth(false)});void check();refresh();const timer=setInterval(check,5000);return()=>{active=false;clearInterval(timer)}},[]);")
swap("const onError=useCallback((s:string)=>setError(s),[]);", """const onError=useCallback((s:string)=>setError(s),[]);
 const restoreJob=useCallback((saved:Job)=>{setJob(saved);setMode(saved.kind==='video'?'video':'audio');setSettings(s=>({...s,...saved.settings,language:saved.language||s.language}));setTime(0);setPlaying(false);setDemo(false)},[]);""")
swap("api<Job>('/jobs/'+id).then(setJob).catch(()=>{})", "api<Job>('/jobs/'+id).then(restoreJob).catch(()=>setError('Saqlangan ishni ochib bo‘lmadi. Mening fayllarim bo‘limidan qayta tanlang.'))")
swap("setJob(await api<Job>('/jobs/'+j.id));setPage('studio');setMode(j.kind==='video'?'video':'audio');setTime(0);setPlaying(false);setSettings(s=>({...s,engine:'human'}))", "restoreJob(await api<Job>('/jobs/'+j.id));setPage('studio')")
swap("{health?'● Server ulangan':'○ Server tekshirilmoqda'}", "{health?'● Server ulangan':'○ Server bilan aloqa yo‘q · qayta tekshirilmoqda'}")
swap("{settings.language==='en'&&!demo?'How2Sign haqiqiy inson videosi · ASL · tadqiqot namunasi.':'Barmoqli skelet animatsiyasi · 3D texnik namuna.'}", "{settings.engine==='neural'&&!demo?'MaDiS yaratgan 3D harakat · ASL ma’nosi tasdiqlanmagan.':settings.language==='en'&&!demo?'How2Sign haqiqiy inson videosi · ASL · tadqiqot namunasi.':'Barmoqli skelet animatsiyasi · 3D texnik namuna.'}")
# Reapply the playback rate whenever a new media element is mounted or loaded.
s=s.replace("onPlay={()=>setPlaying(true)}", "onLoadedMetadata={e=>{e.currentTarget.playbackRate=1/playbackScale}} onEnded={()=>setPlaying(false)} onPlay={()=>setPlaying(true)}")
needle=" {page==='studio'&&mode!=='text'&&job?.translation&&settings.language==='en'&&"
panel=""" {page==='studio'&&mode!=='text'&&job&&job.segments.length>0&&<section className="card transcript-panel"><div className="section-head"><h2>Aniqlangan nutq matni</h2><span>{job.segments.length} bo‘lak · {job.language==='uz'?'O‘zbekcha':'Inglizcha'}</span></div><p>Vaqt ustiga bosing va asl audiodagi gapni tekshiring. Bu matn nutq aniqlagich natijasi.</p><div className="transcript-list">{job.segments.map((segment,index)=><button key={index} className={time/playbackScale>=segment.start&&time/playbackScale<segment.end?'transcript-line current':'transcript-line'} onClick={()=>{if(media.current)media.current.currentTime=segment.start;setTime(segment.start*playbackScale)}}><span>{Math.floor(segment.start/60)}:{String(Math.floor(segment.start%60)).padStart(2,'0')}</span><strong>{segment.text}</strong></button>)}</div></section>}
"""
swap(needle,panel+needle)
p.write_text(s,encoding='utf-8')
css=Path(r'D:\SignBridge-UZ\frontend\src\style.css')
css.write_text(css.read_text(encoding='utf-8')+"\n.transcript-panel{margin-top:24px}.transcript-list{display:grid;gap:8px;max-height:360px;overflow:auto}.transcript-line{display:flex;gap:16px;text-align:left;align-items:flex-start;background:#101a2c}.transcript-line>span{color:#abb6ff;font-variant-numeric:tabular-nums;font-size:12px;min-width:42px}.transcript-line>strong{font-size:14px;font-weight:400;overflow-wrap:anywhere;line-height:1.5}.transcript-line.current{background:#222e4c;border-color:#7386cd}\n",encoding='utf-8')
