import {useEffect,useState} from 'react';
export type SavedJob={id:string;name:string;kind:string;duration:number;status:string};
const names:Record<string,string>={uploaded:'Yuklangan',ready:'Matn tayyor',processing:'Tahlil qilinmoqda',queued:'Navbatda',frames:'Kadrlar kutilmoqda',rendering:'MP4 yig‘ilmoqda',done:'MP4 tayyor',failed:'Xato',cancelled:'Bekor qilingan'};
export function JobHistory({onOpen}:{onOpen:(j:SavedJob)=>void}){
 const [jobs,setJobs]=useState<SavedJob[]>([]),[error,setError]=useState('');
 useEffect(()=>{fetch('/api/jobs').then(r=>{if(!r.ok)throw Error('Fayllar ro‘yxati ochilmadi.');return r.json()}).then(setJobs).catch(e=>setError(e.message))},[]);
 return <section className="card"><div className="section-head"><h2>Saqlangan fayllar</h2><span>Oxirgi {jobs.length} ish · mahalliy</span></div><p>Oldingi faylni qayta yuklamasdan matn, tarjima va eksportga qayting.</p>{error&&<p role="alert">{error}</p>}<div className="segments">{jobs.map(j=><button key={j.id} onClick={()=>onOpen(j)}><strong>{j.name||'Saqlangan ish'}</strong><small>{j.kind==='video'?'Video':'Audio'} · {j.duration.toFixed(1)} s · {names[j.status]||j.status}</small></button>)}</div>{!jobs.length&&!error&&<p>Hali fayl yuklanmagan.</p>}</section>;
}
