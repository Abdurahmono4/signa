import {useState} from 'react';
import TranscriptEditor from './TranscriptEditor';
import {requestSignal} from './flowGuards';
type Transcript={segments:{text:string;start:number;end:number}[];transcript_revision?:number};
export default function TranscriptRecovery({jobId,disabled,onUpdated}:{jobId:string;disabled:boolean;onUpdated?:()=>void|Promise<void>}){
 const [data,setData]=useState<Transcript|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false),[open,setOpen]=useState(false);
 async function load(){setLoading(true);setError('');try{const r=await fetch(`/api/jobs/${jobId}`,{signal:requestSignal()});if(!r.ok)throw Error('Matn ochilmadi.');const value=await r.json();setData(value);setOpen(true)}catch(e){setError(e instanceof Error?e.message:String(e))}finally{setLoading(false)}}
 if(!open)return <div className="transcript-recovery"><button disabled={disabled||loading} onClick={load}>{loading?'Matn olinmoqda…':'Nutq matnini tekshirish'}</button>{error&&<p role="alert">{error}</p>}</div>;
 return <div className="transcript-recovery"><div className="section-head"><strong>Nutq matni</strong><button disabled={disabled} onClick={()=>setOpen(false)}>Yopish</button></div><p>Faqat audio bilan solishtirib xatolarni tuzating. So‘zlarni modelga moslash uchun ma’nosini o‘zgartirmang. Saqlagach avatar qayta tayyorlanadi.</p>{data&&<><p className="recovery-transcript">{data.segments.map(s=>s.text).join(' ')}</p><TranscriptEditor jobId={jobId} segments={data.segments} revision={data.transcript_revision||0} disabled={disabled||!onUpdated} onSaved={async()=>{await onUpdated?.();setOpen(false);setData(null)}}/></>}</div>;
}
