from pathlib import Path
p=Path('frontend/src/main.tsx');s=p.read_text(encoding='utf-8')
s=s.replace("model:'tiny',language:'en'", "model:'tiny',language:'en',engine:'human'")
pos=s.index(' const avatar=useRef')
s=s[:pos]+''' const [neural,setNeural]=useState<{status:string;phase?:string;progress?:number;error?:string}|null>(null),[generated,setGenerated]=useState<Sequence|null>(null),[modelReady,setModelReady]=useState(false);
 useEffect(()=>{api<{ready:boolean}>('/neural/health').then(h=>setModelReady(h.ready)).catch(()=>{})},[]);
 useEffect(()=>{setNeural(null);setGenerated(null);if(!job)return;let active=true;const load=()=>api<any>('/jobs/'+job.id+'/neural').then(async state=>{if(!active)return;setNeural(state);if(state.status==='ready'){const plan=await api<Sequence>('/jobs/'+job.id+'/neural/plan');if(active)setGenerated(plan)}}).catch(()=>{});load();const timer=setInterval(load,2000);return()=>{active=false;clearInterval(timer)}},[job?.id]);
 async function generateMotion(){if(!job)return;setError('');try{setNeural(await api('/jobs/'+job.id+'/neural',json({})));setSettings(s=>({...s,engine:'neural'}))}catch(e){setError(String(e))}}
'''+s[pos:]
s=s.replace("const items=page==='library'", "const items=settings.engine==='neural'&&page==='studio'&&!demo?generated?.items||EMPTY:page==='library'")
s=s.replace("settings.language==='en'&&!demo&&page==='studio'?<HumanSigner", "settings.language==='en'&&settings.engine==='human'&&!demo&&page==='studio'?<HumanSigner")
s=s.replace("settings.language==='en'&&!demo?'ASL tarjimon videosi':'3D tarjimon'", "settings.engine==='neural'?'Tajribaviy ML avatari':settings.language==='en'&&!demo?'ASL tarjimon videosi':'3D tarjimon'")
s=s.replace("job.translation?.items||[]", "items")
s=s.replace("disabled={!ready||!job.translation}", "disabled={!ready||!job.translation||(settings.engine==='neural'&&!generated)}")
needle=" const coverage=mode==='text'?sequence:job?.translation;"
s=s.replace(needle," const coverage=settings.engine==='neural'?null:mode==='text'?sequence:job?.translation;")
pos=s.index(" {page==='studio'&&settings.language==='en'&&<section")
s=s[:pos]+''' {page==='studio'&&job?.translation&&settings.language==='en'&&<section className="card coverage"><div className="section-head"><h2>Ijro usuli</h2><span>{modelReady?'MaDiS CPU tayyor':'ML modeli tayyor emas'}</span></div><div className="actions"><button className={settings.engine==='human'?'primary':''} onClick={()=>setSettings(s=>({...s,engine:'human'}))}>How2Sign inson videolari</button><button disabled={!modelReady||['queued','processing'].includes(neural?.status||'')} onClick={generateMotion}>ML harakatini tayyorlash</button>{generated&&<button onClick={()=>setSettings(s=>({...s,engine:'neural'}))}>ML ijrosini ko‘rish</button>}{['queued','processing'].includes(neural?.status||'')&&<button onClick={()=>api('/jobs/'+job.id+'/neural/cancel',json({}))}>ML ni bekor qilish</button>}</div>{neural&&<p>{neural.status==='ready'?'ML harakati yaratildi':neural.phase} · {neural.progress||0}%</p>}{neural?.error&&<p role="alert">{neural.error}</p>}{settings.engine==='neural'&&<p className="notice">Tayyor MaDiS modelidan tajribaviy 3D harakat. Bu haqiqiy inson videosi emas va ASL ma’nosi tasdiqlanmagan. Yuz/qo‘l moslashuvi taxminiy. Nutq vaqtiga moslashda harakat siqilishi mumkin. Ushbu datasetda qayta o‘qitilmadi.</p>}</section>}
'''+s[pos:]
p.write_text(s,encoding='utf-8')
