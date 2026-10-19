import {useEffect,useRef,useState} from 'react';
import {Plus,Save,Trash2,X} from 'lucide-react';
import type {Job} from './QualityPanel';

export function TranscriptEditor({job,onClose,onSave}:{job:Job;onClose:()=>void;onSave:(segments:{start:number;end:number;text:string}[])=>Promise<void>}){
 const [rows,setRows]=useState(job.segments.map(s=>({start:s.start,end:s.end,text:s.text})));
 const [error,setError]=useState('');const [saving,setSaving]=useState(false);
 const dialog=useRef<HTMLElement>(null);const close=useRef(onClose);close.current=onClose;
 useEffect(()=>{
  const previous=document.activeElement as HTMLElement|null;
  const focusable=()=>Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input,textarea')||[]);
  focusable()[0]?.focus();
  const keydown=(event:KeyboardEvent)=>{
   if(event.key==='Escape'){event.preventDefault();close.current()}
   if(event.key==='Tab'){const items=focusable();const first=items[0],last=items.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}}
  };
  document.addEventListener('keydown',keydown);
  return()=>{document.removeEventListener('keydown',keydown);previous?.focus()};
 },[]);
 const update=(i:number,key:'start'|'end'|'text',value:string)=>setRows(rows.map((row,n)=>n===i?{...row,[key]:key==='text'?value:Number(value)}:row));
 async function save(){setSaving(true);try{await onSave(rows);onClose()}catch(e){setError((e as Error).message)}finally{setSaving(false)}}
 return <div className="modal-backdrop"><section ref={dialog} className="card transcript-editor" role="dialog" aria-modal="true" aria-labelledby="editor-title"><div className="card-heading"><h2 id="editor-title">Matn va vaqtlarni tahrirlash</h2><button className="icon-button" aria-label="Tahrirlashni yopish" onClick={onClose}><X/></button></div><p>Vaqtlar soniyada. Eski natija versiyalar tarixida saqlanadi. O‘zgartirilgan satrlarda so‘zma-so‘z vaqtlar qayta hisoblanmaydi.</p><div className="editor-rows">{rows.map((row,i)=><div className="editor-row" key={i}><span>{i+1}</span><label>Boshlanish<input type="number" min="0" step="0.01" aria-label={`${i+1}-satr boshlanishi`} value={row.start} onChange={e=>update(i,'start',e.target.value)}/></label><label>Tugash<input type="number" min="0" step="0.01" aria-label={`${i+1}-satr tugashi`} value={row.end} onChange={e=>update(i,'end',e.target.value)}/></label><textarea aria-label={`${i+1}-satr matni`} value={row.text} onChange={e=>update(i,'text',e.target.value)}/><button className="icon-button" aria-label={`${i+1}-satrni olib tashlash`} onClick={()=>setRows(rows.filter((_,n)=>n!==i))}><Trash2 size={16}/></button></div>)}</div>{error&&<p role="alert" className="inline-error">{error}</p>}<div className="editor-actions"><button className="secondary" onClick={()=>setRows([...rows,{start:rows.at(-1)?.end||0,end:Math.min(job.duration,(rows.at(-1)?.end||0)+1),text:''}])}><Plus size={14}/> Satr qo‘shish</button><button className="primary" disabled={saving} onClick={save}><Save size={15}/>{saving?'Saqlanmoqda…':'Saqlash'}</button></div></section></div>;
}
