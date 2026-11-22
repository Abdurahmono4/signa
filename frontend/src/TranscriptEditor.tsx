import {useState} from 'react';
import {requestSignal} from './flowGuards';
type Segment={text:string;start:number;end:number};
export default function TranscriptEditor({jobId,segments,revision,disabled,onSaved}:{jobId:string;segments:Segment[];revision:number;disabled:boolean;onSaved:()=>Promise<void>}){
 const [draft,setDraft]=useState(()=>segments.map(s=>s.text)),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const changed=draft.some((t,i)=>t.trim()!==segments[i].text);
 async function save(){setBusy(true);setError('');try{
  const response=await fetch(`/api/jobs/${jobId}/transcript`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_revision:revision,segments:segments.map((s,i)=>({start:s.start,end:s.end,text:draft[i].trim()}))}),signal:requestSignal()});
  const value=await response.json();if(!response.ok)throw Error(typeof value.detail==='string'?value.detail:'Matn saqlanmadi.');await onSaved();
 }catch(e){setError(String(e))}finally{setBusy(false)}}
 return <details className="transcript-editor"><summary>Nutq matnidagi xatoni tuzatish</summary><p>Inglizcha matnni audio bilan solishtiring. Saqlagach qamrov yangilanadi; avatar harakati va MP4ni qayta tayyorlash kerak bo‘ladi.</p>
 {segments.map((s,i)=><label key={i}>{s.start.toFixed(2)}–{s.end.toFixed(2)} s<textarea aria-label={`${i+1}-bo‘lak matni`} maxLength={8000} disabled={busy||disabled} value={draft[i]} onChange={e=>setDraft(d=>d.map((v,n)=>n===i?e.target.value:v))}/></label>)}
 <button disabled={disabled||busy||!changed||draft.some(t=>!t.trim())} onClick={save}>{busy?'Saqlanmoqda…':'Matnni saqlash va qamrovni yangilash'}</button>{error&&<p role="alert">{error}</p>}</details>;
}
