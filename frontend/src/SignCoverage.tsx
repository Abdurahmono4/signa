import {lazy,memo,Suspense,useEffect,useRef,useState} from 'react';
import {ArrowDownToLine,Hand,Play,X} from 'lucide-react';
import type {Motion} from './Avatar3D';

const Avatar=lazy(()=>import('./Avatar3D').then(m=>({default:m.Avatar3D})));
export type SignItem={segment_index:number;start:number;end:number;text:string;status:string;clip:Motion|null;word_count:number;timing:'aligned'|'estimated'};
export type SignPlan={mode:string;source_previews:number;matched:number;total:number;covered_words:number;total_words:number;coverage:number;missing_words:string[];items:SignItem[]};
const states:Record<string,string>={matched:'Tekshirilgan klip',source_preview:'Manba namunasi',missing:'Klip yo‘q',timing_review:'Vaqt mos emas',unsupported_rig:'Rig mos emas'};
const stamp=(s:number)=>`${Math.floor(s/60).toString().padStart(2,'0')}:${Math.floor(s%60).toString().padStart(2,'0')}`;

export const SignCoverage=memo(function SignCoverage({plan,error,filename,onSeek,onPause,onRetry}:{plan:SignPlan|null;error:string;filename:string;onSeek:(time:number)=>void;onPause:()=>void;onRetry:()=>void}){
 const [preview,setPreview]=useState<SignItem|null>(null),[filter,setFilter]=useState('all');
 const dialog=useRef<HTMLElement>(null);
 useEffect(()=>{setPreview(null);setFilter('all')},[plan]);
 useEffect(()=>{
  if(!preview)return;
  const previous=document.activeElement as HTMLElement|null;
  const focusable=()=>Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input,select')||[]);
  focusable()[0]?.focus();
  const keydown=(event:KeyboardEvent)=>{
   if(event.key==='Escape')setPreview(null);
   if(event.key==='Tab'){
    const controls=focusable(),first=controls[0],last=controls.at(-1);
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}
   }
  };
  document.addEventListener('keydown',keydown);
  return()=>{document.removeEventListener('keydown',keydown);if(previous?.isConnected)previous.focus()};
 },[preview]);
 function exportPlan(){
  if(!plan)return;
  const result={schema:'signa-asl-coverage-v1',media:filename,exported_at:new Date().toISOString(),interpretation:'Timed ASL dictionary assistance; coverage is not translation accuracy.',...plan};
  const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='signa-asl-report.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 const timed=plan?.items.filter(item=>item.status==='timing_review').length||0;
 const missing=plan?.items.filter(item=>item.status==='missing').length||0;
 const shown=plan?.items.filter(item=>filter==='all'||(filter==='available'?!!item.clip:item.status==='missing'||item.status==='timing_review'||item.status==='unsupported_rig'))||[];
 return <section className="card sign-coverage"><div className="card-heading"><h2><Hand size={18}/>ASL lug‘at yordami</h2>{plan&&<button className="icon-button" aria-label="ASL qamrov hisobotini yuklab olish" onClick={exportPlan}><ArrowDownToLine size={18}/></button>}</div>
  {error?<div className="sign-plan-error"><p className="inline-error" role="alert">{error}</p><button className="secondary" onClick={onRetry}>Qayta yuklash</button></div>:!plan?<p className="quality-note" role="status">Ishoralar rejasi yuklanmoqda…</p>:<>
   <div className="sign-summary"><div><strong>{plan.coverage}%</strong><span>Sinxron klip bilan qoplangan so‘zlar</span></div><progress aria-label="ASL kliplari qamrovi" max="100" value={plan.coverage}/><p>{plan.covered_words} / {plan.total_words} so‘z · {plan.matched} tekshirilgan klip · {plan.source_previews} manba namunasi</p></div>
   <p className="quality-note">Bu mavjud ishoralarni topuvchi lug‘at yordami. Qamrov foizi tarjima aniqligi emas; inglizcha gapning ASL grammatikasiga tarjimasi hali bajarilmaydi.</p>
   {timed>0&&<p className="quality-note warning">{timed} klipning davomiyligi nutq vaqtiga mos emas. Ularni «Alohida ko‘rish» orqali tabiiy tezlikda tekshiring.</p>}
   {missing>0&&<p className="quality-note">{missing} so‘z yoki ibora uchun klip yo‘q. Ularning matni subtitrda saqlanadi.</p>}
   {plan.items.some(item=>item.timing==='estimated')&&<p className="quality-note">Qo‘lda tahrirlangan yoki so‘z vaqti bo‘lmagan satrlar vaqti taxminiy taqsimlangan.</p>}
   <div className="sign-filter"><label>Ko‘rsatish<select aria-label="ASL rejasini filtrlash" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">Barchasi ({plan.total})</option><option value="available">Klipi bor</option><option value="attention">Tekshirish kerak</option></select></label></div>
   <div className="sign-items">{shown.map((item,index)=><article className={`sign-item sign-${item.status}`} key={`${item.segment_index}-${item.start}-${index}`}><button className="sign-seek" onClick={()=>onSeek(item.start)} aria-label={`${item.text}: ${stamp(item.start)} vaqtiga o‘tish`}><time>{stamp(item.start)}</time><strong>{item.text}</strong><span>{states[item.status]||item.status}{item.timing==='estimated'?' · taxminiy vaqt':''}</span></button>{item.clip?.animation_asset&&<button className="text-button" onClick={()=>{onPause();setPreview(item)}} aria-label={`${item.text} ishorasini alohida ko‘rish`}><Play size={14}/>Alohida ko‘rish</button>}</article>)}{!shown.length&&<p className="quality-note">Bu guruhda yozuvlar yo‘q.</p>}</div>
  </>}
  {preview?.clip&&<div className="modal-backdrop" onClick={()=>setPreview(null)}><section ref={dialog} className="card sign-preview-dialog" role="dialog" aria-modal="true" aria-labelledby="sign-preview-title" onClick={e=>e.stopPropagation()}><div className="card-heading"><h2 id="sign-preview-title">{preview.text} · alohida ko‘rish</h2><button className="icon-button" aria-label="Ishora oynasini yopish" onClick={()=>setPreview(null)}><X size={20}/></button></div><p className="quality-note">Media pauzada. Klip o‘z davomiyligida ijro etiladi: {preview.clip.duration.toFixed(2)} soniya. {preview.status==='timing_review'?'Asl nutq vaqtiga siqib ijro etilmadi.':''}</p><Suspense fallback={<p className="quality-note">Avatar yuklanmoqda…</p>}><Avatar motion={preview.clip} preview/></Suspense></section></div>}
 </section>;
});
