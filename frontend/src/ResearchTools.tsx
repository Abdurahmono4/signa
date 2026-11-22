import {useEffect,useState} from 'react';
import {validateNeuralMotion} from './neuralMotion';
import type {NeuralMotion} from './neuralMotion';
type Source={id:string;name:string;url:string;language:string;license:string;integration:string;missing:string};
export default function ResearchTools({onImport,disabled,onBusy}:{onImport:(motion:NeuralMotion,label:string)=>void;disabled:boolean;onBusy:(busy:boolean)=>void}){
 const [sources,setSources]=useState<Source[]>([]),[error,setError]=useState(''),[busy,setLocalBusy]=useState(false),[original,setOriginal]=useState(''),[candidate,setCandidate]=useState(''),[audit,setAudit]=useState<{original:{coverage:number};candidate:{coverage:number};alerts:string[];notice:string}|null>(null);
 const setBusy=(value:boolean)=>{setLocalBusy(value);onBusy(value)};
 useEffect(()=>()=>onBusy(false),[onBusy]);
 useEffect(()=>{const c=new AbortController();fetch('/api/research/sources',{signal:c.signal}).then(r=>{if(!r.ok)throw Error('Manbalar olinmadi.');return r.json()}).then(d=>setSources(d.sources)).catch(e=>{if(!c.signal.aborted)setError(String(e))});return()=>c.abort()},[]);
 async function importMotion(file:File){
  if(file.size>16*1024*1024){setError('JSON 16 MB dan oshmasin.');return}setBusy(true);setError('');
  try{const r=await fetch('/api/research/motions/convert',{method:'POST',headers:{'Content-Type':'application/json'},body:await file.text()});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Konversiya bajarilmadi.');if(validateNeuralMotion(d).length>10000)throw Error('Ko‘rik uchun 10 000 kadrdan oshmasin.');onImport(d,`${file.name} · ${d.language||'Til ko‘rsatilmagan'}`)}catch(e){setError(String(e))}finally{setBusy(false)}
 }
 async function checkText(){setBusy(true);setError('');try{const r=await fetch('/api/research/audit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({original,candidate})});const d=await r.json();if(!r.ok)throw Error('Matn tekshiruvi bajarilmadi.');setAudit(d)}catch(e){setError(String(e))}finally{setBusy(false)}}
 return <details className="research-tools"><summary>GitHub manbalari va tadqiqot vositalari</summary>
 <p>To‘rtta manba tekshirildi. Tayyorlik va litsenziyalar quyida ko‘rsatilgan.</p>
 {sources.map(s=><article key={s.id}><h3><a href={s.url} target="_blank" rel="noreferrer">{s.name}</a></h3><p>{s.language} · {s.license}</p><p>{s.integration}</p><p className="muted">{s.missing}</p></article>)}
 <h3>3D harakat JSON importi</h3><p>SignAvatars: «smplx» massivida 182 kanal, «fps» va «language» kerak. Dong SignAvatar: «format»: «signavatar-rot6d-53», «normalized»: false, «fps» va T×53×6 «frames». Faqat bitta kesilgan klipni eksport qiling. PKL fayl ishlatilmaydi.</p>
 <input aria-label="Tadqiqot harakati JSON" type="file" accept=".json" disabled={disabled||busy} onChange={e=>{const f=e.target.files?.[0];if(f)void importMotion(f);e.target.value=''}}/>
 <p>Import faqat oldindan ko‘rish uchun. Uni joriy videoning tarjimasi deb hisoblamang.</p>
 <h3>Inglizcha ibora qamrovini solishtirish</h3><label>Asl matn<textarea value={original} maxLength={20000} onChange={e=>{setOriginal(e.target.value);setAudit(null)}}/></label><label>Taklif etilgan matn<textarea value={candidate} maxLength={20000} onChange={e=>{setCandidate(e.target.value);setAudit(null)}}/></label>
 <button disabled={disabled||busy||!original.trim()||!candidate.trim()} onClick={checkText}>{busy?'Tekshirilmoqda…':'Qamrov va muhim o‘zgarishlarni tekshirish'}</button>
 {audit&&<div role="status"><p>Asl matn: {audit.original.coverage}% · Taklif: {audit.candidate.coverage}%</p>{audit.alerts.map(a=><p key={a}>{a}</p>)}<p>{audit.notice}</p></div>}
 <p><a href="/api/research/grammar" download>Faol How2Sign iboralari uchun GBNF grammatikani olish</a></p><p>Grammatika keyingi mahalliy LLM tajribasi uchun. U o‘zi matn yaratmaydi yoki ma’noni tasdiqlamaydi.</p>
 {error&&<p role="alert">{error}</p>}</details>;
}
