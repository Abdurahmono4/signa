import {lazy,Suspense,useCallback,useEffect,useRef,useState} from 'react';
import type {CSSProperties} from 'react';
import {ArrowRight,AudioLines,Check,ChevronRight,Captions as ClosedCaptions,Download,FileVideo,Hand,Headphones,LoaderCircle,Maximize2,Pause,Play,RotateCcw,ShieldCheck,Upload,Volume2,VolumeX,X} from 'lucide-react';
import type {Job} from './QualityPanel';
import {getPlaybackFrame} from './playback';
import type {PlaybackPlan} from './playback';
import {createCompositeRecording,primeRecordingAudio} from './compositeExport';
import type {CompositeFrame} from './compositeExport';
import type {AvatarFrame} from './Avatar3D';
import {useInterpreterPlayback} from './useInterpreterPlayback';
import './style.css';

const Avatar=lazy(()=>import('./Avatar3D').then(module=>({default:module.Avatar3D})));
type MediaSource={name:string;kind:'audio'|'video';url:string;duration:number;demo:boolean};
type Operation={id:number;signal:AbortSignal};
type NeuralStatus={status:'idle'|'queued'|'processing'|'ready'|'failed'|'cancelled';phase:string;progress:number;error?:string};
type NeuralReadiness={ready:boolean;installing:boolean;downloaded_bytes:number;total_bytes:number};
function rememberJob(id:string){
 try{sessionStorage.setItem('signa:current-job',id)}catch{ /* Storage is optional. */ }
 const url=new URL(window.location.href);
 if(url.searchParams.has('job')){url.searchParams.set('job',id);window.history.replaceState(null,'',url.pathname+url.search+url.hash)}
}
const formatTime=(seconds:number)=>`${Math.floor(Math.max(0,seconds)/60).toString().padStart(2,'0')}:${Math.floor(Math.max(0,seconds)%60).toString().padStart(2,'0')}`;
const messages:Record<string,string>={queued:'Navbat kutilmoqda',loading:'Ovoz tahlilga tayyorlanmoqda',decoding:'Ovoz o‘qilmoqda',transcribing:'Nutq aniqlanmoqda',auditing:'Matn tekshirilmoqda',recovering:'Matn aniqlashtirilmoqda',avatar:'Avatar tayyorlanmoqda',installing_model:'ASL modeli o‘rnatilmoqda',verifying_model:'ASL modeli tekshirilmoqda',loading_model:'ASL modeli yuklanmoqda',generating_motion:'Gaplar imo-ishoraga aylantirilmoqda',generating_segment:'Avatar ishoralarni tayyorlayapti'};

class ApiError extends Error{status:number;constructor(message:string,status:number){super(message);this.name='ApiError';this.status=status}}
async function request<T>(path:string,options?:RequestInit):Promise<T>{
 const response=await fetch(`/api${path}`,options);
 if(!response.ok){const body=await response.json().catch(()=>({}));throw new ApiError(typeof body.detail==='string'?body.detail:'Server bilan aloqa uzildi. Qayta urinib ko‘ring.',response.status)}
 return response.status===204?undefined as T:response.json();
}
function waitForAudio(promise:Promise<void>,signal:AbortSignal){return new Promise<void>((resolve,reject)=>{
 const timer=setTimeout(()=>finish(new Error('Ovoz yozuviga ruxsat olinmadi. Ijro tugmasini bosib, keyin qayta tayyorlang.')),8000);
 const abort=()=>finish(new DOMException('Bekor qilindi','AbortError'));
 function finish(error?:unknown){clearTimeout(timer);signal.removeEventListener('abort',abort);if(error)reject(error);else resolve()}
 if(signal.aborted)abort();else signal.addEventListener('abort',abort,{once:true});
 promise.then(()=>finish(),finish);
})}
function waitForUpdate(signal:AbortSignal){return new Promise<void>((resolve,reject)=>{
 const timer=setTimeout(()=>{signal.removeEventListener('abort',abort);resolve()},900);
 const abort=()=>{clearTimeout(timer);reject(new DOMException('Cancelled','AbortError'))};
 if(signal.aborted)abort();else signal.addEventListener('abort',abort,{once:true});
})}

export default function App(){
 const [source,setSource]=useState<MediaSource|null>(null),[job,setJob]=useState<Job|null>(null),[plan,setPlan]=useState<PlaybackPlan|null>(null);
 const [exporting,setExporting]=useState(false),[exportProgress,setExportProgress]=useState(0),[exportFile,setExportFile]=useState<{url:string;name:string}|null>(null);
 const [uploading,setUploading]=useState(false),[preparing,setPreparing]=useState(false),[phase,setPhase]=useState(''),[progress,setProgress]=useState(0);
 const [error,setError]=useState(''),[dragging,setDragging]=useState(false),[captions,setCaptions]=useState(true),[muted,setMuted]=useState(false);
 const media=useRef<HTMLMediaElement|null>(null),input=useRef<HTMLInputElement>(null),viewer=useRef<HTMLElement>(null);
 const generation=useRef(0),controller=useRef<AbortController|null>(null),autoPlay=useRef(false),currentJob=useRef<Job|null>(null);
 const playback=useInterpreterPlayback(plan,media);
 const avatarCanvas=useRef<HTMLCanvasElement|null>(null),avatarPaint=useRef<AvatarFrame|null>(null),exportController=useRef<AbortController|null>(null);
 const exportFrame=useRef<CompositeFrame>({caption:'',label:'',position:0,total:0,playing:false,error:''});
 const receiveCanvas=useCallback((canvas:HTMLCanvasElement|null)=>{avatarCanvas.current=canvas},[]);
 const receiveFrame=useCallback((frame:AvatarFrame)=>{avatarPaint.current=frame},[]);
 const busy=uploading||preparing||exporting;
 const sourceKind=source&&/\.(mp3|wav|m4a|ogg|flac)$/i.test(source.name)?'audio':source?.kind;
 const currentSegment=job?.segments.find(segment=>playback.mediaTime>=segment.start&&playback.mediaTime<segment.end);
 const currentWord=currentSegment?.words?.find(word=>playback.mediaTime>=word.start&&playback.mediaTime<word.end);
 const subtitle=plan?.mode==='neural_asl'?(currentSegment?.words?.length?currentWord?.word.trim()||'':currentSegment?.text||''):
  playback.activeItem?(playback.activeItem.word_text||playback.activeItem.text||''):'';
 const playbackError=error||playback.error;
 const completed=!!plan&&playback.position>=playback.total-.02;
 const fingerspelling=playback.activeItem?.rendering==='fingerspelling';
 exportFrame.current={caption:captions?subtitle:'',label:playback.activeMotion?(plan?.mode==='neural_asl'?'ASL · model ijrosi':fingerspelling?`${playback.activeItem?.word_text} · ${playback.activeItem?.letter}`:playback.activeMotion.phrase):'ASL avatar',position:playback.position,total:playback.total,playing:playback.playing,error:playbackError};
 useEffect(()=>()=>{exportController.current?.abort()},[]);
 useEffect(()=>{const url=exportFile?.url;return()=>{if(url)URL.revokeObjectURL(url)}},[exportFile?.url]);

 useEffect(()=>{currentJob.current=job},[job]);
 useEffect(()=>{
  const linked=new URLSearchParams(window.location.search).get('job')||'';
  let remembered=/^[a-f0-9]{32}$/.test(linked)?linked:'';
  if(!remembered)try{remembered=sessionStorage.getItem('signa:current-job')||''}catch{ /* Storage is optional. */ }
  if(!remembered)return;
  const operation=startOperation();setUploading(true);
  void request<Job>(`/jobs/${encodeURIComponent(remembered)}`,{signal:operation.signal}).then(item=>{
   if(operation.id!==generation.current)return;
   rememberJob(item.id);setJob(item);setSource({name:item.name,kind:item.kind,url:`/api/jobs/${encodeURIComponent(item.id)}/media`,duration:item.duration,demo:false});
  }).catch(cause=>{if(operation.id===generation.current&&(cause as Error).name!=='AbortError'){if(cause instanceof ApiError&&cause.status===404){try{sessionStorage.removeItem('signa:current-job')}catch{ /* Storage is optional. */ }}else setError((cause as Error).message)}})
   .finally(()=>{if(operation.id===generation.current)setUploading(false)});
 },[]);
 useEffect(()=>()=>{generation.current++;controller.current?.abort()},[]);
 useEffect(()=>{const url=source?.url;return()=>{if(url?.startsWith('blob:'))URL.revokeObjectURL(url)}},[source?.url]);
 useEffect(()=>{if(plan&&autoPlay.current){autoPlay.current=false;void playback.play()}},[plan,playback.play]);
 useEffect(()=>{if(media.current)media.current.muted=muted},[muted,source?.url]);

 function startOperation(){
  generation.current++;controller.current?.abort();controller.current=new AbortController();autoPlay.current=false;
  playback.reset();setPlan(null);setError('');setProgress(0);setExportFile(null);
  return {id:generation.current,signal:controller.current.signal};
 }
 async function prepare(item:Job,id:number,signal:AbortSignal,beginPlayback=true){
  setPreparing(true);setPhase('loading');
  try{
   let latest=item;
   if(latest.status!=='ready')latest=await request<Job>(`/jobs/${item.id}/transcribe`,{method:'POST',signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({profile:'balanced',mode:'speech'})});
   while(['queued','processing'].includes(latest.status)){
    if(id!==generation.current)return;
    setJob(latest);setPhase(latest.phase||'transcribing');setProgress(latest.progress||0);
    await waitForUpdate(signal);latest=await request<Job>(`/jobs/${item.id}`,{signal});
   }
   if(id!==generation.current)return;
   setJob(latest);
   if(latest.status!=='ready')throw new Error(latest.error||'Nutqni tayyorlash yakunlanmadi. Qayta urinib ko‘ring.');
   let model=await request<NeuralReadiness>('/neural/status',{signal});
   while(!model.ready&&model.installing){
    if(id!==generation.current)return;
    setPhase('installing_model');setProgress(Math.floor(model.downloaded_bytes/model.total_bytes*100));
    await waitForUpdate(signal);await waitForUpdate(signal);await waitForUpdate(signal);
    model=await request<NeuralReadiness>('/neural/status',{signal});
   }
   if(id!==generation.current)return;
   if(!model.ready)throw new Error('ASL modeli to‘liq o‘rnatilmagan. Model yuklanishini yakunlash kerak.');
   setPhase('loading_model');setProgress(0);
   let neural=await request<NeuralStatus>(`/jobs/${item.id}/neural`,{method:'POST',signal});
   while(['queued','processing'].includes(neural.status)){
    if(id!==generation.current)return;
    setPhase(neural.phase);setProgress(neural.progress);
    await waitForUpdate(signal);neural=await request<NeuralStatus>(`/jobs/${item.id}/neural`,{signal});
   }
   if(id!==generation.current)return;
   if(neural.status!=='ready')throw new Error(neural.error||'Avatar ijrosi tayyorlanmadi. Qayta urinib ko‘ring.');
   setPhase('avatar');setProgress(100);
   const next=await request<PlaybackPlan>(`/jobs/${item.id}/neural/plan`,{signal});
   const avatar=await import('./Avatar3D');
   await avatar.prepareMotions(next.items.flatMap(entry=>entry.clip?[entry.clip]:[]));
   if(id!==generation.current)return;
   autoPlay.current=beginPlayback;setPlan(next);
  }catch(cause){if(id===generation.current&&(cause as Error).name!=='AbortError')setError((cause as Error).message)}
  finally{if(id===generation.current){setPreparing(false);setPhase('')}}
 }
 async function upload(file?:File,demo=false,beginPlayback=false,preparedOperation?:Operation){
  if(!file||busy&&!preparedOperation)return;
  if(preparedOperation&&preparedOperation.id!==generation.current)return;
  if(file.size>100*1024*1024){setError('100 MB gacha bo‘lgan faylni tanlang.');return}
  if(!/\.(mp4|mov|webm|mp3|wav|m4a|ogg|flac)$/i.test(file.name)){setError('MP4, MOV, WEBM, MP3, WAV, M4A, OGG yoki FLAC fayl tanlang.');return}
  const operation=preparedOperation||startOperation();setUploading(true);setJob(null);
  const url=URL.createObjectURL(file);
  setSource({name:file.name,kind:/\.(mp4|mov|webm)$/i.test(file.name)?'video':'audio',url,duration:0,demo});
  const form=new FormData();form.append('file',file);
  try{
   const item=await request<Job>('/jobs',{method:'POST',body:form,signal:operation.signal});
   if(operation.id!==generation.current)return;
   rememberJob(item.id);setJob(item);setSource({name:item.name,kind:item.kind,url,duration:item.duration,demo});setUploading(false);
   if(beginPlayback)await prepare(item,operation.id,operation.signal);
  }catch(cause){if(operation.id===generation.current&&(cause as Error).name!=='AbortError'){setError((cause as Error).message);setSource(null)}}
  finally{if(operation.id===generation.current)setUploading(false);if(input.current)input.current.value=''}
 }
 async function demo(){
  if(busy)return;
  const operation=startOperation();setUploading(true);
  try{
   const response=await fetch('/avatar/demo.wav',{signal:operation.signal});if(!response.ok)throw new Error('Namuna ochilmadi. Qayta urinib ko‘ring.');
   const file=new File([await response.blob()],'Signa-namuna.wav',{type:'audio/wav'});
   if(operation.id!==generation.current)return;
   await upload(file,true,true,operation);
  }catch(cause){if(operation.id===generation.current&&(cause as Error).name!=='AbortError')setError((cause as Error).message)}
  finally{if(operation.id===generation.current)setUploading(false)}
 }
 async function primaryAction(){
  if(busy)return;
  setError('');
  if(!source||!job){input.current?.click();return}
  if(playback.playing){playback.pause();return}
  if(plan){await playback.play();return}
  const operation=startOperation();await prepare(job,operation.id,operation.signal);
 }
 async function exportVideo(){
  if(busy||!source||!plan||!media.current)return;
  if(!plan.playable_signs){setError('Avval avatar ijrosini tayyorlang.');return}
  const originalMedia=media.current,previousMuted=originalMedia.muted,previousVolume=originalMedia.volume;
  const abort=new AbortController();exportController.current=abort;setError('');setExportFile(null);setExporting(true);setExportProgress(0);playback.reset();
  try{
   const audioReady=primeRecordingAudio(originalMedia);
   originalMedia.muted=false;originalMedia.volume=1;setMuted(false);
   await waitForAudio(audioReady,abort.signal);
   const start=getPlaybackFrame(plan,0),deadline=performance.now()+20000;
   while(true){
    if(abort.signal.aborted)throw new DOMException('Bekor qilindi','AbortError');
    const painted=avatarPaint.current,element=media.current;
    const poseReady=painted?.ready&&painted.asset===(start.activeMotion?.neural_asset||start.activeMotion?.animation_asset||null)&&Math.abs(painted.time-Math.max(1/30,start.motionTime))<.08;
    if(avatarCanvas.current&&element&&!element.seeking&&element.readyState>=2&&Math.abs(element.currentTime-start.mediaTime)<.12&&poseReady&&exportFrame.current.position<.01)break;
    if(performance.now()>deadline)throw new Error('Avatar yoki media video yozuviga tayyor bo‘lmadi. Qayta urinib ko‘ring.');
    await new Promise<void>(resolve=>requestAnimationFrame(()=>resolve()));
   }
   const recording=await createCompositeRecording({media:media.current!,avatar:()=>avatarCanvas.current,frame:()=>exportFrame.current,onProgress:setExportProgress,signal:abort.signal});
   playback.play();
   const blob=await recording.result;
   if(abort.signal.aborted)return;
   const name=source.name.replace(/\.[^.]+$/,'')+'-ASL-avatar.webm';
   setExportFile({url:URL.createObjectURL(blob),name});setExportProgress(1);
  }catch(cause){if((cause as Error).name!=='AbortError')setError((cause as Error).message)}
  finally{playback.pause();originalMedia.muted=previousMuted;originalMedia.volume=previousVolume;setMuted(previousMuted);setExporting(false);exportController.current=null}
 }
 async function cancel(){
  const cancellation=++generation.current;
  controller.current?.abort();autoPlay.current=false;setPreparing(false);setUploading(false);setPhase('');playback.pause();
  const item=currentJob.current;
  if(item&&preparing&&item.status==='ready')void request(`/jobs/${item.id}/neural/cancel`,{method:'POST'}).catch(()=>{});
  if(uploading&&!preparing){setSource(null);setJob(null)}
  if(item&&['queued','processing'].includes(item.status)){
   try{await request(`/jobs/${item.id}/cancel`,{method:'POST'});if(cancellation===generation.current)setJob({...item,status:'cancelled'})}
   catch(cause){if(cancellation===generation.current)setError((cause as Error).message)}
  }
 }
 const status=uploading?'Fayl yuklanmoqda…':preparing?`${messages[phase]||'Tayyorlanmoqda'}…`:playback.playing?(fingerspelling?`Harflab ko‘rsatilmoqda: ${playback.activeItem?.word_text||''}`:playback.isHolding?'Avatar ishorani yakunlayapti':playback.activeMotion?'Imo-ishora ijro etilmoqda':['missing','unsupported_rig'].includes(playback.activeItem?.status||'')?'Mos ishora yo‘q — subtitrni kuzating':'Media ijro etilmoqda'):plan?(completed?'Ijro yakunlandi':'Ijroga tayyor'):source?'Fayl yuklandi. Ijro tugmasini bosing.':'Video yoki audio yuklang — qolganini shu yerda bajaring.';

 return <div className="signa-app">
  <header className="site-header"><a className="wordmark" href="#" onClick={event=>event.preventDefault()} aria-label="Signa bosh sahifa"><span className="brand-mark"><Hand size={23} strokeWidth={1.7}/></span>signa<span className="brand-period">.</span></a><span className="language-pill"><span/>English <ArrowRight size={13}/> ASL</span></header>
  <main className="app-main">
   <section className="intro"><div><div className="eyebrow"><span/>OVOZDAN ISHORAGA</div><h1>Ovozni <span>ko‘ring.</span></h1><p>Video yoki audio yuklang.<br className="mobile-break"/> Imo-ishorani yonidagi avatarda kuzating.</p></div><div className="intro-detail"><span className="detail-line"/><span>Ko‘proq tushunish.<br/><strong>Birga, bir ekranda.</strong></span></div></section>
   <section ref={viewer} className={`translation-studio ${dragging?'is-dragging':''}`} aria-label="Media va imo-ishora studiyasi" onDragOver={event=>{event.preventDefault();if(!busy)setDragging(true)}} onDragLeave={event=>{if(!event.currentTarget.contains(event.relatedTarget as Node))setDragging(false)}} onDrop={event=>{event.preventDefault();setDragging(false);if(!busy)void upload(event.dataTransfer.files[0])}}>
    <div className="studio-topline"><div className="studio-title"><span className="tiny-symbol"><FileVideo size={15}/></span><span>{source?source.name:'Sizning kontentingiz'}</span>{source?.demo&&<em>Namuna</em>}</div><div className="studio-tools">{source&&<button className="replace-file" disabled={busy} onClick={()=>input.current?.click()}><Upload size={14}/><span>Boshqa fayl</span></button>}<span className="studio-language">Amerika imo-ishora tili</span></div></div>
    <div className={`screen-layout ${source?'overlay-layout':''}`}>
     <div className={`media-screen ${!source?'empty-screen':''}`}>
      {!source?<button className="upload-surface" disabled={busy} onClick={()=>input.current?.click()} aria-label="Video yoki audio fayl yuklash"><div className="upload-art"><span className="upload-orbit orbit-one"/><span className="upload-orbit orbit-two"/><span className="upload-main-icon"><Upload size={30} strokeWidth={1.5}/></span><span className="floating-icon floating-video"><FileVideo size={18}/></span><span className="floating-icon floating-audio"><AudioLines size={19}/></span></div><h2>Video yoki audio yuklang</h2><p>Faylni shu yerga tashlang yoki tanlang</p><span className="choose-file">Fayl tanlash <ChevronRight size={16}/></span><small>MP4, MOV, WEBM · MP3, WAV va boshqalar<br/>100 MB gacha · 20 daqiqagacha</small></button>:<>
       {sourceKind==='video'?<video ref={element=>{media.current=element}} src={source.url} preload="auto" playsInline muted={muted} aria-label={source.name} onError={()=>setError('Bu video brauzerda ochilmadi. MP4 formatini sinab ko‘ring.')}/>:<div className="audio-screen"><div className={`audio-disc ${playback.playing?'is-playing':''}`}><Headphones size={48} strokeWidth={1.2}/></div><span className="audio-type">AUDIO</span><h2>{source.name}</h2><div className={`sound-bars ${playback.playing?'is-playing':''}`} aria-hidden="true">{Array.from({length:34},(_,index)=><i key={index} style={{height:`${12+((index*19+7)%45)}px`,animationDelay:`${index*-.07}s`}}/>)}</div><audio ref={element=>{media.current=element}} src={source.url} preload="auto" muted={muted} aria-label={source.name} onError={()=>setError('Audio ochilmadi. Boshqa faylni sinab ko‘ring.')}/></div>}
       <div className="media-corner-label">{sourceKind==='video'?<FileVideo size={12}/>:<Headphones size={12}/>}<span>{sourceKind==='video'?'VIDEO':'AUDIO'}</span><i/>{formatTime(source.duration)}</div>
       {captions&&subtitle&&<div className="caption-overlay" aria-live="off"><span>{subtitle}</span></div>}
       {!plan&&!busy&&<button className="stage-play" onClick={primaryAction} aria-label="Nutqni imo-ishorada ijro etish"><Play size={26} fill="currentColor"/></button>}
      </>}
      {(uploading||preparing)&&<div className="processing-overlay"><div className="processing-card"><LoaderCircle size={27} className="spin"/><strong>{uploading?'Fayl yuklanmoqda':messages[phase]||'Tayyorlanmoqda'}</strong><p>{phase==='avatar'?'Harakatlar ijroga tayyorlanmoqda':'Biroz kuting. Tayyor bo‘lgach ijro boshlanadi.'}</p><progress max="100" value={uploading||phase==='avatar'?undefined:progress} aria-label="Nutqni tayyorlash"/><button onClick={cancel}>Bekor qilish</button></div></div>}
     </div>
     <aside className="interpreter-panel" aria-label="ASL tarjimon avatari"><div className="interpreter-top"><span className={`interpreter-dot ${playback.playing?'active':''}`}/><strong>ASL avatar</strong><span className="avatar-mode">{playback.playing?(fingerspelling?'HARFLAB':playback.activeMotion?'ISHORA':'SUBTITR'):busy?'TAYYORLANMOQDA':plan?'TAYYOR':'KUTISH'}</span></div><div className="avatar-viewport"><Suspense fallback={<div className="avatar-placeholder"><LoaderCircle size={23} className="spin"/><span>Avatar yuklanmoqda</span></div>}><Avatar motion={playback.activeMotion} time={playback.motionTime} onReady={playback.setAvatarReady} onCanvas={receiveCanvas} onFrame={receiveFrame} capture/></Suspense></div>{playback.activeMotion&&plan?.mode!=='neural_asl'&&<div className="interpreter-bottom"><span className="interpreter-wave"><Hand size={15}/></span><span>{fingerspelling?`${playback.activeItem?.word_text} · ${playback.activeItem?.letter}`:playback.activeMotion.phrase}</span></div>}</aside>
    </div>
    <div className="playback-bar"><button className="restart-button" onClick={playback.reset} disabled={!plan||busy} aria-label="Boshidan boshlash"><RotateCcw size={16}/></button><span className="time-label">{formatTime(playback.position)}</span><input className="timeline" type="range" min="0" max={playback.total||1} step=".01" value={playback.position} disabled={!plan||busy} onChange={event=>playback.seek(Number(event.target.value))} aria-label="Ijro vaqti" style={{'--played':`${playback.total?playback.position/playback.total*100:0}%`} as CSSProperties}/><span className="time-label total-time">{formatTime(playback.total||source?.duration||0)}</span><div className="transport-divider"/><button className={captions?'tool-button active':'tool-button'} disabled={exporting} onClick={()=>setCaptions(value=>!value)} aria-label="Subtitr" aria-pressed={captions}><ClosedCaptions size={18}/></button><button className="tool-button" disabled={exporting} onClick={()=>setMuted(value=>!value)} aria-label={muted?'Ovozni yoqish':'Ovozni o‘chirish'} aria-pressed={muted}>{muted?<VolumeX size={18}/>:<Volume2 size={18}/>}</button><button className="tool-button fullscreen-button" onClick={()=>{void viewer.current?.requestFullscreen?.().catch(()=>setError('To‘liq ekran ochilmadi.'))}} aria-label="To‘liq ekran"><Maximize2 size={17}/></button></div>
    <div className="action-row"><div className="action-status" role="status"><span className={busy?'status-dot preparing':playback.playing?'status-dot live':'status-dot'}/><span>{status}</span></div><button className="primary-action" disabled={busy} onClick={primaryAction}>{busy?<LoaderCircle size={19} className="spin"/>:playback.playing?<Pause size={18} fill="currentColor"/>:completed?<RotateCcw size={18}/>:<Play size={18} fill="currentColor"/>}<span>{busy?'Tayyorlanmoqda…':playback.playing?'Pauza':completed?'Qayta ijro etish':'Imo-ishorada ijro etish'}</span>{!busy&&!playback.playing&&<ArrowRight size={17}/>}</button></div>
    {source&&<div className="export-row">{exporting?<><span role="status">Video tayyorlanmoqda · {Math.round(exportProgress*100)}%<small>Yozuv tugaguncha sahifani ochiq qoldiring.</small></span><button className="export-cancel" onClick={()=>exportController.current?.abort()}>Bekor qilish</button></>:<><span>{plan?'Avatar videoning burchagida chiqadi.':'Avval imo-ishora ijrosini tayyorlang.'}</span><div className="export-actions">{exportFile&&<a className="export-download" href={exportFile.url} download={exportFile.name}><Download size={15}/>Videoni yuklab olish</a>}<button className="export-button" disabled={!plan||busy} onClick={exportVideo}><Download size={15}/>{exportFile?'Qayta tayyorlash':'Avatarli video tayyorlash'}</button></div></>}</div>}
   </section>
   {exportFile&&<div className="export-preview"><strong>Avatarli video tayyor</strong><video src={exportFile.url} controls playsInline aria-label="Tayyor avatarli video"/><a href={exportFile.url} download={exportFile.name}><Download size={15}/> {exportFile.name}</a></div>}
   <input ref={input} className="file-input" type="file" accept=".mp4,.mov,.webm,.mp3,.wav,.m4a,.ogg,.flac" aria-label="Media fayl tanlash" onChange={event=>void upload(event.target.files?.[0])}/>
   {playbackError&&<div className="error-notice" role="alert"><span>{playbackError}</span><button aria-label="Xabarni yopish" onClick={()=>{setError('');playback.clearError()}}><X size={16}/></button></div>}
   <div className="below-studio"><span className="privacy-note"><ShieldCheck size={14}/>Fayllaringiz ushbu kompyuterda qoladi.</span>{!source?<button className="demo-link" disabled={busy} onClick={demo}><Play size={13}/>Namunani sinash <ArrowRight size={13}/></button>:<span className="scope-note">{plan?'ASL modelining tajribaviy ijrosi':'Inglizcha nutq → ASL avatar'}</span>}</div>
  </main>
  <footer className="site-footer"><span>signa<span>.</span></span><p>Mazmun hammaga yetib borsin.</p><div><Check size={12}/>Oddiy. Qulay. Birga.</div></footer>
 </div>;
}
