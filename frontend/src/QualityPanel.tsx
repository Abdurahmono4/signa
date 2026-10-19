import { AlertCircle, CheckCircle2, LoaderCircle, Square, WandSparkles } from 'lucide-react';

export type Word = {start:number;end:number;word:string;probability:number;needs_review:boolean};
export type Segment = {start:number;end:number;text:string;needs_review:boolean;words?:Word[];edited?:boolean};
export type Report = {model?:string;processed_seconds?:number;timeline_seconds?:number;chunks?:number;retry_count?:number;word_count?:number;review_words?:number;recovered_words?:number;suspect_spans?:{start:number;end:number;reason:string}[];warnings?:string[];audit_stale?:boolean;manual_edit?:boolean};
export type Job = {id:string;name:string;kind:'video'|'audio';size:number;duration:number;status:string;error:string|null;segments:Segment[];created_at:string;report:Report;settings:{profile?:string;mode?:string};progress:number;phase:string;revision:number};
export type Health = {model_ready:boolean;asl_ready:boolean;profiles:{id:string;model:string;ready:boolean}[]};
const phases:Record<string,string>={queued:'Navbat kutilmoqda',loading:'Model xotiraga yuklanmoqda',decoding:'Audio to‘liq o‘qilmoqda',transcribing:'Bo‘laklar ketma-ket tinglanmoqda',auditing:'Matnsiz oraliqlar tekshirilmoqda',recovering:'Shubhali oraliqlar qayta tinglanmoqda',done:'Tahlil tugadi'};
const stamp=(s:number)=>`${Math.floor(s/60).toString().padStart(2,'0')}:${Math.floor(s%60).toString().padStart(2,'0')}`;

export function RecognitionSettings({profile,mode,onProfile,onMode,health,disabled}:{profile:string;mode:string;onProfile:(v:string)=>void;onMode:(v:string)=>void;health:Health|null;disabled:boolean}){
 return <div className="recognition-settings"><div className="setting-title"><WandSparkles size={16}/><strong>Nutqni aniqlash sozlamalari</strong><span>v0.2</span></div><div className="setting-fields"><label>Model<select aria-label="Nutq modeli" value={profile} disabled={disabled} onChange={e=>onProfile(e.target.value)}><option value="accurate">Aniqlikka ustuvorlik · medium.en{health?.profiles?.find(p=>p.id==='accurate')?.ready?'':' · yuklanmagan'}</option><option value="balanced">Muvozanatli · small.en{health?.profiles?.find(p=>p.id==='balanced')?.ready?'':' · yuklanmagan'}</option></select></label><label>Kontent turi<select aria-label="Nutq turi" value={mode} disabled={disabled} onChange={e=>onMode(e.target.value)}><option value="speech">Nutq / suhbat</option><option value="music">Qo‘shiq / musiqa</option></select></label></div><p>Audio qismlari sukut filtri bilan kesilmaydi. Kuchliroq model ko‘proq vaqt oladi; musiqa rejimi matnsiz faol oraliqlarni ham tekshiradi.</p></div>;
}

export function QualityPanel({job,onSeek,onCancel,cancelling}:{job:Job;onSeek:(t:number)=>void;onCancel:()=>void;cancelling:boolean}){
 const running=['queued','processing'].includes(job.status);
 const report=job.report||{};
 const spans=report.suspect_spans||[];
 return <section className="card quality-card"><div className="card-heading"><h2>{running?<LoaderCircle size={18} className="spin"/>:<CheckCircle2 size={18}/>}Tahlil nazorati</h2>{report.model&&<span className="badge">{report.model}</span>}</div>
 {running?<div className="progress-area" aria-live="polite"><div><strong>{phases[job.phase]||'Ishlanmoqda'}</strong><b>{job.progress||0}%</b></div><progress max="100" value={job.progress||0}/><p>Bu ishlov berish foizi, matn aniqligi emas. Natija tayyor bo‘lgan sari quyida chiqadi.</p><button className="text-button" disabled={cancelling} onClick={onCancel}><Square size={13}/>{cancelling?'Joriy bo‘lak tugagach to‘xtaydi…':'Jarayonni to‘xtatish'}</button></div>:<>
 {report.processed_seconds!=null?<div className="quality-stats"><div><b>{stamp(report.processed_seconds)} / {stamp(report.timeline_seconds||job.duration)}</b><span>Tahlildan o‘tgan audio</span></div><div><b>{report.word_count??'—'}</b><span>{report.audit_stale?'Avvalgi avtomatik so‘zlar':'Aniqlangan so‘zlar'}</span></div><div><b>{report.retry_count||0}</b><span>Qo‘shimcha tahlil</span></div></div>:<p className="quality-note">Bu natijada yangi to‘liqlik auditi yo‘q. Yangilangan model bilan qayta tahlil qiling.</p>}
 {report.audit_stale&&<p className="quality-note">Matn qo‘lda tahrirlangan. Audit ko‘rsatkichlari oldingi avtomatik natijaga tegishli.</p>}
 <p className="quality-note">Butun audio qayta ishlangani barcha so‘zlar to‘g‘ri tanilganini anglatmaydi. Past ishonchli so‘zlar: {report.review_words||0}. Qayta topilgan so‘zlar: {report.recovered_words||0}.</p>
 {spans.length>0&&<div className="gap-list"><strong><AlertCircle size={16}/>Tinglab tekshiriladigan oraliqlar ({spans.length})</strong>{spans.map((s,i)=><button key={i} onClick={()=>onSeek(s.start)}><time>{stamp(s.start)}–{stamp(s.end)}</time><span>{s.reason}</span></button>)}</div>}
 {report.warnings?.map((w,i)=><p key={i} className="quality-note warning">{w}</p>)}
 {job.status==='cancelled'&&<p className="quality-note warning">Jarayon to‘xtatilgan. Quyidagi matn qisman natija; qayta boshlashingiz mumkin.</p>}
 </>}
 </section>;
}
