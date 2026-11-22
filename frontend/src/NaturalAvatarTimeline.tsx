import {positionAvatarCamera} from './avatarCamera';
import {ROCKETBOX_MOTION_REVISION} from './motionRevision';
import {mapMotionAssets} from './motionLoading';
import {readJson,waitForRetry} from './readJson';
import ResultVideo from './ResultVideo';
import {uploadFrame} from './frameUpload';
import {Suspense,useMemo,useState,useEffect,useLayoutEffect,useRef,useCallback,Component} from 'react';
import type {ReactNode} from 'react';
import {Canvas,useLoader,useThree} from '@react-three/fiber';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as THREE from 'three';
import {clone} from 'three/examples/jsm/utils/SkeletonUtils.js';
import {createRocketboxClip,createRocketboxIdleClip} from './rocketboxMotion';
import {validateNeuralMotion,neuralMotionAssetUrl} from './neuralMotion';
import type {NeuralMotion} from './neuralMotion';
import {motionAt,presentationAt,validateIntervals} from './avatarTimeline';
import {AvatarPlayback} from './avatarPlayback';
import ResearchTools from './ResearchTools';
import {assertExportOwnership,requestSignal,neuralPollAction,assertMotionBudget} from './flowGuards';
import TranscriptRecovery from './TranscriptRecovery';
type Interval={start:number;end:number;duration:number;text:string;motion:NeuralMotion};
type Plan={items:{start:number;end:number;text:string;neural_asset?:string;unsupported?:boolean}[];timing_scale:number;output_duration:number;unsupported_phrases?:number;caption_words?:number;limits?:{max_chunks:number;max_frames:number}};
type MediaInfo={kind:string;name:string;duration:number;status?:string;result_token?:string;render_token?:string;resume_frames?:boolean;settings?:{avatar_model?:string;motion_revision?:string}};
class Boundary extends Component<{children:ReactNode},{error:string}>{
 state={error:''};static getDerivedStateFromError(error:Error){return {error:error.message}}
 render(){return this.state.error?<p role="alert">Model ochilmadi: {this.state.error}</p>:this.props.children}
}
function PortraitCamera(){
 const {camera,size,invalidate}=useThree();
 useLayoutEffect(()=>{
  // R3F may reset the default camera after Canvas.onCreated; apply framing
  // inside the scene and after every resize instead.
  positionAvatarCamera(camera);
  if(camera instanceof THREE.PerspectiveCamera){camera.fov=28;camera.aspect=size.width/size.height;camera.updateProjectionMatrix()}
  camera.updateMatrixWorld(true);invalidate();
 },[camera,size.width,size.height,invalidate]);
 return null;
}
type Capture=(time:number)=>Promise<Blob>;
function Woman({items,time,onCapture}:{items:Interval[];time:number;onCapture:(capture:Capture|null)=>void}){
 const latestTime=useRef(time);latestTime.current=time;
 const source=useLoader(GLTFLoader,'/assets/avatars/rocketbox-female-01/female.glb');
 const {invalidate,gl,scene,camera}=useThree();
 const model=useMemo(()=>{
  const avatar=clone(source.scene);
  avatar.traverse(node=>{
   if(!(node instanceof THREE.Mesh))return;
   node.frustumCulled=false;
   if(node.material.name!=='f001_body')return;
   const shirt=node.material.clone() as THREE.MeshStandardMaterial;
   // The body atlas shares one material for skin, denim and rose fabric.
   // Select fabric by its rose hue, preserving the atlas folds and seams.
   shirt.onBeforeCompile=shader=>{
    shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>', `
     #include <map_fragment>
     vec3 fabric = diffuseColor.rgb;
     float rose = smoothstep(-0.008, 0.012, (fabric.b - fabric.g) / max(fabric.r, 0.001))
                * smoothstep(1.08, 1.24, fabric.r / max(fabric.g, 0.001));
     float weave = dot(fabric, vec3(0.2126, 0.7152, 0.0722));
     diffuseColor.rgb = mix(fabric, weave * vec3(0.12, 0.28, 0.72), rose);
    `);
   };
   node.material=shirt;
  });
  return avatar;
 },[source]);
 useEffect(()=>()=>model.traverse(node=>{
  if(node instanceof THREE.Mesh && node.material.name==='f001_body')node.material.dispose();
 }),[model]);
 const mixer=useMemo(()=>new THREE.AnimationMixer(model),[model]);
 const idle=useMemo(()=>createRocketboxIdleClip(source.scene),[source]);
 const playback=useMemo(()=>new AvatarPlayback(mixer,idle),[mixer,idle]);
 const clips=useMemo(()=>new Map(items.map(i=>[i,createRocketboxClip(source.scene,i.motion)])),[source,items]);
 const sample=useCallback((at:number)=>{
  const pose=presentationAt(items,at);
  playback.transition(pose.from?{clip:clips.get(pose.from.item)!,time:pose.from.localTime}:null,pose.to?{clip:clips.get(pose.to.item)!,time:pose.to.localTime}:null,pose.mix);
  model.updateMatrixWorld(true);
 },[items,playback,clips,model]);
 useLayoutEffect(()=>{
  sample(time);invalidate();
 },[time,sample,invalidate]);
 useEffect(()=>()=>{playback.dispose();mixer.uncacheClip(idle)},[idle,mixer,playback]);
 useEffect(()=>()=>{for(const c of clips.values())mixer.uncacheClip(c)},[clips,mixer]);
 useEffect(()=>{
  const width=1024,height=768;
  const exportCamera=new THREE.PerspectiveCamera(28,width/height,.1,100);positionAvatarCamera(exportCamera);
  const target=new THREE.WebGLRenderTarget(width,height,{samples:Math.min(4,gl.capabilities.maxSamples)});
  target.texture.colorSpace=THREE.SRGBColorSpace;
  const pixels=new Uint8Array(width*height*4),canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;
  const ctx=canvas.getContext('2d');if(!ctx){target.dispose();onCapture(null);return}
  const image=ctx.createImageData(width,height);
  onCapture(async (at:number)=>{
   sample(at);
   const previous=gl.getRenderTarget(),alpha=gl.getClearAlpha(),color=gl.getClearColor(new THREE.Color()).clone();
   try{
    gl.setRenderTarget(target);gl.setClearColor(0,0);gl.clear();model.traverse(n=>{if(n instanceof THREE.SkinnedMesh)n.skeleton.update()});gl.render(scene,exportCamera);
    gl.readRenderTargetPixels(target,0,0,width,height,pixels);
   }finally{gl.setRenderTarget(previous);gl.setClearColor(color,alpha);sample(latestTime.current);invalidate()}
   let visible=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i]>32)visible++;
   if(visible<5000)throw Error(`Avatar kadrda ko‘rinmay qoldi (${at.toFixed(2)} s). Eksport to‘xtatildi.`);
   for(let y=0;y<height;y++)image.data.set(pixels.subarray((height-1-y)*width*4,(height-y)*width*4),y*width*4);
   ctx.putImageData(image,0,0);
   return await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('PNG kadr olinmadi.')),'image/png'));
  });return()=>{onCapture(null);target.dispose()};
 },[sample,gl,scene,camera,invalidate,onCapture]);
 return <primitive object={model}/>;
}
/** The offline comprehension study uses the same scene and capture function as MP4 export. */
export function AvatarStage({items,time,angle=0,onCapture}:{
 items:Interval[];time:number;angle?:number;onCapture:(capture:Capture|null)=>void
}){
 const portrait=useMemo(()=>{const c=new THREE.PerspectiveCamera(28,4/3,.1,100);positionAvatarCamera(c);return c},[]);
 return <div style={{width:'100%',aspectRatio:'4 / 3',maxWidth:640,margin:'auto',background:'#111318',borderRadius:14,overflow:'hidden'}}><Canvas frameloop="demand" camera={portrait} dpr={[1,2]}><PortraitCamera/><ambientLight intensity={0.75}/><hemisphereLight args={['#fff8ef','#99a6bb',1.0]}/><directionalLight position={[-2,3,4]} intensity={2.1}/><directionalLight position={[2,1,2]} intensity={0.7}/><Suspense fallback={null}><group rotation={[0,angle,0]}><Woman items={items} time={time} onCapture={onCapture}/></group></Suspense></Canvas></div>;
}
export default function NaturalAvatarTimeline({jobId,autoPrepare=false,autoExport=false,onExportStart,onBusy,onJobChanged,onTime,seekRequest,compact=false,forceNewRender=false}:{jobId?:string;autoExport?:boolean;onExportStart?:()=>void;forceNewRender?:boolean;autoPrepare?:boolean;onBusy?:(busy:boolean)=>void;onJobChanged?:()=>void|Promise<void>;onTime?:(time:number)=>void;seekRequest?:{time:number;nonce:number};compact?:boolean}){
 const [researchBusy,setResearchBusy]=useState(false);
 const [loadProgress,setLoadProgress]=useState({done:0,total:0});
 const [unsupportedPhrases,setUnsupportedPhrases]=useState(0);
 const [captions,setCaptions]=useState<Plan['items']>([]);
 const retryAction=useRef<'load'|'generate'|'export'>('generate');
 const loadedJob=useRef('');
 const [previewRate,setPreviewRate]=useState(1),[imported,setImported]=useState('');
 const [angle,setAngle]=useState(0),[items,setItems]=useState<Interval[]>([]),[playing,setPlaying]=useState(false),[time,setTime]=useState(0),[error,setError]=useState(''),[loading,setLoading]=useState(false);
 const [media,setMedia]=useState<MediaInfo|null>(null),[duration,setDuration]=useState(0),[scale,setScale]=useState(1);
 const capture=useRef<Capture|null>(null),exportAbort=useRef<AbortController|null>(null);
 const [captureReady,setCaptureReady]=useState(false);
 const onCapture=useCallback((c:Capture|null)=>{capture.current=c;setCaptureReady(c!==null)},[]);
 const [exporting,setExporting]=useState(false),[exportProgress,setExportProgress]=useState(''),[exportResult,setExportResult]=useState('');
 useEffect(()=>{setExportProgress('');setExportResult('');return()=>{exportAbort.current?.abort()}},[jobId]);
 const [generating,setGenerating]=useState(false),[generation,setGeneration]=useState('');
 const [generationProgress,setGenerationProgress]=useState(0),[exportPercent,setExportPercent]=useState(0);
 useEffect(()=>{onBusy?.(loading||generating||exporting||researchBusy);return()=>onBusy?.(false)},[loading,generating,exporting,researchBusy,onBusy]);
 useEffect(()=>{onTime?.(time/scale)},[time,scale,onTime]);
 useEffect(()=>{if(seekRequest&&!exporting)seek(seekRequest.time*scale)},[seekRequest]);
 const el=useRef<HTMLMediaElement|null>(null),request=useRef<AbortController|null>(null),generationRequest=useRef<AbortController|null>(null);
 useEffect(()=>{request.current?.abort();generationRequest.current?.abort();el.current?.pause();setUnsupportedPhrases(0);setCaptions([]);setImported('');setItems([]);setMedia(null);setDuration(0);setTime(0);setScale(1);setPlaying(false);setLoading(false);setGenerating(false);setGeneration('');setError('');return()=>{request.current?.abort();generationRequest.current?.abort()}},[jobId]);
 useEffect(()=>{
  if(!jobId||!generating)return;const c=new AbortController();let timer:ReturnType<typeof setTimeout>;
  const poll=async()=>{try{const state=await readJson<any>(`/api/jobs/${jobId}/neural`,{signal:c.signal});if(c.signal.aborted)return;
   setUnsupportedPhrases(state.unsupported_phrases||0);setGenerationProgress(Number.isFinite(state.progress)?Math.max(0,Math.min(100,state.progress)):0);
   setGeneration(state.status==='ready'?'ML harakati tayyor':state.status==='failed'?'ML hisoblashda xato':state.status==='cancelled'?'ML bekor qilindi':state.phase==='loading_model'?'Avatar modeli yuklanmoqda…':state.total_segments>0?`Avatar ijrosi: ${state.completed_segments||0} / ${state.total_segments} ibora tayyor`:`Avatar ijrosi tayyorlanmoqda · ${state.progress||0}%`);
   if(neuralPollAction(state.status)==='load'){setGenerating(false);void load();return}
   if(neuralPollAction(state.status)==='retry'){setGenerating(false);retryAction.current='generate';setError(state.error||'Avatar hisoblash to‘xtagan. Qayta urinib ko‘ring.');return}
   timer=setTimeout(poll,2000);
  }catch(e){if(!c.signal.aborted){setError(String(e));setGenerating(false)}}};void poll();return()=>{c.abort();clearTimeout(timer)};
 },[jobId,generating]);
 useEffect(()=>{if(!playing)return;let f=0;const start=performance.now(),from=time;const tick=()=>{const next=el.current?el.current.currentTime*scale:from+(performance.now()-start)/1000*previewRate;setTime(Math.min(duration,next));if(next>=duration){setPlaying(false);return}f=requestAnimationFrame(tick)};f=requestAnimationFrame(tick);return()=>cancelAnimationFrame(f)},[playing,scale,duration,previewRate]);
 useEffect(()=>{if(el.current)el.current.playbackRate=previewRate/scale},[previewRate,scale]);
 async function load(){
  if(!jobId)return;retryAction.current='load';request.current?.abort();const c=new AbortController();request.current=c;
  setLoadProgress({done:0,total:0});setLoading(true);setError('');setImported('');setPlaying(false);el.current?.pause();setItems([]);setMedia(null);setTime(0);
  function get<T>(path:string):Promise<T>{return readJson<T>(path,{signal:c.signal})}
  try{
   const [plan,info]=await Promise.all([get<Plan>(`/api/jobs/${jobId}/neural/plan`),get<MediaInfo>(`/api/jobs/${jobId}`)]);
   if(!Number.isFinite(plan.timing_scale)||plan.timing_scale<1||plan.timing_scale>4||!Number.isFinite(info.duration)||info.duration<=0)throw Error('Ijro tezligi yoki davomiylik yaroqsiz.');
   if(!Number.isFinite(plan.output_duration)||Math.abs(plan.output_duration-info.duration*plan.timing_scale)>.1)throw Error('Media va harakat rejasining davomiyligi mos emas.');
   let blockedBefore=false;
   const sources=plan.items.flatMap(item=>{
    if(!item.neural_asset){if(item.unsupported)blockedBefore=true;return []}
    const source={...item,blockedBefore};
    blockedBefore=false;
    return [source];
   });
   if(!sources.length)throw Error('Harakat bo‘lagi topilmadi.');
   const budget=plan.limits||{max_chunks:75,max_frames:30000};assertMotionBudget(sources.length,0,budget);
   let frames=0,completed=0;setLoadProgress({done:0,total:sources.length});
   const loaded=await mapMotionAssets(sources,async(i,_index,signal)=>{
    const data=await readJson<NeuralMotion>(neuralMotionAssetUrl(i.neural_asset!),{signal});signal.throwIfAborted();
    const rows=validateNeuralMotion(data);frames+=rows.length;assertMotionBudget(sources.length,frames,budget);
    setLoadProgress({done:++completed,total:sources.length});
    return {...i,motion:data,duration:rows.length/data.fps};
   },{signal:c.signal,concurrency:3});
   validateIntervals(loaded,plan.output_duration);if(c.signal.aborted)return;
   loadedJob.current=jobId;setCaptions(plan.items.filter(i=>i.text.trim()));setUnsupportedPhrases(plan.unsupported_phrases||0);setItems(loaded);setMedia(info);setDuration(plan.output_duration);setScale(plan.timing_scale);if(!forceNewRender&&info.status==='done'&&info.settings?.avatar_model==='rocketbox'&&info.result_token&&info.settings?.motion_revision===ROCKETBOX_MOTION_REVISION)setExportResult(info.result_token);
  }catch(e){if(!c.signal.aborted)setError(String(e))}finally{if(!c.signal.aborted)setLoading(false)}
 }
 function seek(value:number){setPlaying(false);el.current?.pause();if(el.current)el.current.currentTime=value/scale;setTime(value)}
 async function toggle(){const m=el.current;if(!m){if(time>=duration-.02)setTime(0);setPlaying(!playing);return}if(playing){m.pause();setPlaying(false);return}try{if(time>=duration-.02){m.currentTime=0;setTime(0)}m.playbackRate=previewRate/scale;await m.play();setPlaying(true)}catch{setPlaying(false);setError('Media ijrosi boshlanmadi. Audio/video boshqaruvidan urinib ko‘ring.')}}
 async function generate(){if(!jobId)return;retryAction.current='generate';generationRequest.current?.abort();const c=new AbortController();generationRequest.current=c;setError('');setGeneration('ML so‘rovi yuborilmoqda');setLoading(true);try{const r=await fetch(`/api/jobs/${jobId}/neural`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',signal:requestSignal(c.signal)});const state=await r.json();if(c.signal.aborted)return;if(!r.ok)throw Error(typeof state.detail==='string'?state.detail:'ML tayyorlash boshlanmadi.');setUnsupportedPhrases(state.unsupported_phrases||0);setGenerating(true)}catch(e){if(!c.signal.aborted){setError(String(e));setGeneration('');setGenerating(false)}}finally{if(!c.signal.aborted)setLoading(false)}}
 async function cancelGeneration(){try{const r=await fetch(`/api/jobs/${jobId}/neural/cancel`,{method:'POST',signal:requestSignal(undefined,10000)});if(!r.ok)throw Error('Bekor qilish so‘rovi bajarilmadi.');setGeneration('Bekor qilish so‘rovi yuborildi')}catch(e){setError(String(e))}}
 const canResume=!!(media?.settings?.motion_revision===ROCKETBOX_MOTION_REVISION&&media?.render_token&&(media.status==='frames'||media.status==='failed'&&media.resume_frames));
 async function exportVideo(){
  if(!jobId||!capture.current||exportAbort.current)return;
  const c=new AbortController();exportAbort.current=c;onExportStart?.();
  retryAction.current='export';setExporting(true);setExportPercent(0);setError('');setExportResult('');setPlaying(false);el.current?.pause();
  let started=false,finishRequested=false,sessionToken:string|undefined;
  async function call(path:string,body?:unknown){if(body===undefined)return readJson<any>(`/api/jobs/${jobId}${path}`,{signal:c.signal});const r=await fetch(`/api/jobs/${jobId}${path}`,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:requestSignal(c.signal,path==='/render/resume'?300000:30000)});const value=await r.json();if(!r.ok)throw Error(typeof value.detail==='string'?value.detail:'Eksport so‘rovi bajarilmadi.');return value}
  try{
   setExportProgress('Eksport boshlanmoqda');
   const settings={engine:'neural',avatar_model:'rocketbox',motion_revision:ROCKETBOX_MOTION_REVISION,capture_quality:'high',appearance:'navy-v1',resolution:1080,layout:'side_by_side',size:media?.kind==='video'?.30:.40,close_panel:media?.kind==='video',subtitles:true};
   if(canResume)setExportProgress('Saqlangan avatar kadrlari tekshirilmoqda…');
   const session=canResume?await call('/render/resume',{...settings,token:media!.render_token}):await call('/render/start',settings);started=true;sessionToken=session.token;
   setMedia(previous=>previous?{...previous,status:'frames',render_token:session.token,resume_frames:false,settings:{...previous.settings,...settings}}:previous);
   let previousUpload:Promise<void>=Promise.resolve();
   for(let n=session.next_frame??0;n<session.frames;n++){
    c.signal.throwIfAborted();if(!capture.current)throw Error('Avatar oynasi yopildi.');
    const isIdle=(frame:number)=>{
     const pose=presentationAt(items,frame/session.fps);
     return !pose.from && !pose.to;
    };
    let repeat=1;
    if(isIdle(n)){
     while(repeat<48 && n+repeat<session.frames && isIdle(n+repeat))repeat++;
    }
    // One capture and one upload can overlap. Captures never share a canvas concurrently.
    const [,blob]=await Promise.all([previousUpload,capture.current(n/session.fps)]);
    const first=n;
    const completed=n+repeat;
    previousUpload=uploadFrame(`/api/jobs/${jobId}/frames/${session.token}/${first}?repeat=${repeat}`,blob,c.signal).then(()=>{
     setExportProgress(`Avatar kadrlari: ${completed} / ${session.frames}`);setExportPercent(Math.round(80*completed/session.frames));
    },error=>{throw Error(`Kadr ${first+1}/${session.frames}: ${error instanceof Error?error.message:String(error)}`)});
    n+=repeat-1;
   }
   await previousUpload;
   finishRequested=true;await call('/render/finish',{token:sessionToken});
   while(true){
    const state=await call('');assertExportOwnership(state,session.token);setExportPercent(80+Math.round(Math.max(0,Math.min(100,Number(state.progress)||0))*.2));setExportProgress(`${state.phase} · ${state.progress}%`);
    if(state.status==='done'){setExportResult(session.token);setMedia(previous=>previous?{...previous,settings:state.settings}:previous);try{await onJobChanged?.()}catch{setError('Video tayyor. Holatni yangilash uchun sahifani qayta oching.');retryAction.current='load'}break}
    if(['failed','cancelled'].includes(state.status))throw Error(state.error||'Eksport bekor qilindi.');
    await waitForRetry(1000,c.signal);
   }
  }catch(e){if(started&&sessionToken&&c.signal.aborted)await fetch(`/api/jobs/${jobId}/cancel`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:sessionToken}),signal:requestSignal(undefined,10000)}).catch(()=>{});if(c.signal.aborted)setMedia(previous=>previous?{...previous,status:'cancelled',resume_frames:false}:previous);if(finishRequested&&!c.signal.aborted)retryAction.current='load';setError(c.signal.aborted?'Eksport bekor qilindi.':finishRequested?'Eksport holatini olishda xato. Serverdagi ish bekor qilinmadi; holatni qayta tekshiring. '+String(e):String(e));await Promise.resolve(onJobChanged?.()).catch(()=>{})}
  finally{exportAbort.current=null;setExporting(false);setTime(0);if(el.current)el.current.currentTime=0}
 }
 // Start once for a new public upload after both the motion and the capture canvas are ready.
 useEffect(()=>{
  if(autoExport && captureReady && items.length && media && !loading && !generating && !error && !exportResult){
   void exportVideo();
  }
 },[autoExport,captureReady,items,media,loading,generating,error,exportResult]);
 async function retry(){if(retryAction.current==='load')await load();else if(retryAction.current==='export')await exportVideo();else await generate()}
 function cancelLoading(){request.current?.abort();generationRequest.current?.abort();setLoading(false);setError('Yuklash bekor qilindi. Davom etish uchun qayta urinib ko‘ring.');void fetch(`/api/jobs/${jobId}/neural/cancel`,{method:'POST',signal:requestSignal(undefined,10000)}).catch(()=>{})}
 const current=motionAt(items,time);
 const caption=captions.find(i=>time>=i.start&&time<i.end);
 useEffect(()=>{
  if(!jobId||(!autoPrepare&&loadedJob.current===jobId))return;const c=new AbortController();
  void readJson<any>(`/api/jobs/${jobId}/neural`,{signal:c.signal}).then(state=>{
   if(c.signal.aborted)return;
   if(neuralPollAction(state.status)==='load')void load();
   else if(['queued','running','processing'].includes(state.status))setGenerating(true);
   else if(autoPrepare&&state.status==='idle')void generate();
   else if(['failed','cancelled'].includes(state.status)){retryAction.current='generate';setError(state.error||'Avatar hisoblash yakunlanmagan. Qayta urinib ko‘ring.')}
   else {retryAction.current='generate';setError('Avatar harakati hali tayyorlanmagan. Davom etish uchun qayta urinib ko‘ring.');}
  }).catch(e=>{if(!c.signal.aborted)setError(String(e))});
  return()=>c.abort();
 },[jobId,autoPrepare]);
 const mediaEvents={onLoadedMetadata:(e:React.SyntheticEvent<HTMLMediaElement>)=>{e.currentTarget.playbackRate=previewRate/scale},onPlay:()=>setPlaying(true),onPause:()=>setPlaying(false),onEnded:()=>{setPlaying(false);setTime(duration)},onTimeUpdate:(e:React.SyntheticEvent<HTMLMediaElement>)=>setTime(e.currentTarget.currentTime*scale),onError:()=>{setPlaying(false);setError('Asl media ochilmadi.')}};
 const modelView=<Boundary key={jobId||'empty'}><AvatarStage items={items} time={time} angle={angle} onCapture={onCapture}/></Boundary>;
 if(compact)return <section className="card focused-result"><div className="focused-result-heading"><h2>{exportResult?'Video tayyor':'Avatar ijrosi'}</h2>{exportResult&&<a className="primary" href={`/api/jobs/${jobId}/download?v=${exportResult}`}>MP4 yuklab olish ↓</a>}</div>
 <div className={exportResult?'focused-capture-only':'focused-preview'}>{media?.kind==='video'&&!exportResult&&<div className="focused-source"><video controls playsInline src={`/api/jobs/${jobId}/media`} ref={m=>{el.current=m}} {...mediaEvents}/></div>}<div className="focused-avatar">{modelView}</div></div>
 {exportResult?<ResultVideo className="focused-final" src={`/api/jobs/${jobId}/result?v=${exportResult}`}/>:<>{media?.kind==='audio'&&<audio className="focused-audio" controls src={`/api/jobs/${jobId}/media`} ref={m=>{el.current=m}} {...mediaEvents}/>}<div className="actions">{items.length>0&&<button disabled={exporting} onClick={toggle}>{playing?'Pauza':'Ijro etish'}</button>}<button className="primary" disabled={!captureReady||!items.length||loading||generating||exporting} onClick={exportVideo}>{canResume&&!exporting?'MP4 eksportini davom ettirish':'MP4 tayyorlash'}</button>{loading&&<button onClick={cancelLoading}>Bekor qilish</button>}{generating&&<button onClick={cancelGeneration}>Bekor qilish</button>}{exporting&&<button onClick={()=>exportAbort.current?.abort()}>Bekor qilish</button>}</div></>}
 {!exportResult&&caption&&<p className="focused-caption">{caption.text}{caption.unsupported&&<small>Avatar ijrosi yo‘q — subtitr</small>}</p>}
 {(loading||generating||exporting)&&<p role="status">{exporting?exportProgress:loading?(loadProgress.total?`Avatar harakatlari yuklanmoqda · ${loadProgress.done}/${loadProgress.total}`:'Tarjimon tayyorlanmoqda…'):generation}</p>}
 {(generating||exporting)&&<progress aria-label={exporting?'Video tayyorlash':'Avatar tayyorlash'} max={100} value={exporting?exportPercent:generationProgress}/>}
 {error&&<p role="alert">{error} <button disabled={loading||generating||exporting} onClick={retry}>Qayta urinish</button></p>}
 {error&&jobId&&<div className="actions"><a href={`/api/jobs/${jobId}/transcript/download?format=txt`}>Nutq matnini yuklab olish</a><a href={`/api/jobs/${jobId}/transcript/download?format=srt`}>Subtitrni yuklab olish</a></div>}
 {jobId&&(!!error||unsupportedPhrases>0)&&<TranscriptRecovery key={jobId} jobId={jobId} disabled={loading||generating||exporting} onUpdated={onJobChanged}/>}
 <p className="focused-note">{unsupportedPhrases>0&&`${unsupportedPhrases} ta ibora uchun avatar ijrosi yo‘q — matn va subtitr saqlangan. `}Avatar ijrosi tajribaviy. Ishoralar mutaxassis tomonidan tasdiqlanmagan.</p></section>;
 return <section className="card"><div className="section-head"><h2>Avatar ijrosi</h2><span className="pill">TAJRIBAVIY IJRO</span></div>
 {modelView}
 <label>Ko‘rik tezligi: {previewRate.toFixed(2)}×<input type="range" min=".5" max="1.5" step=".05" value={previewRate} disabled={exporting} onChange={e=>setPreviewRate(Number(e.target.value))}/></label>
 <label>Qiyofani burish<input type="range" min="-.65" max=".65" step=".01" disabled={exporting} value={angle} onChange={e=>setAngle(Number(e.target.value))}/></label>
 <div className="actions"><button disabled={!jobId||loading||generating||exporting||researchBusy} onClick={load}>{loading?'Harakatlar yuklanmoqda…':'Saqlangan ML harakatini yuklash'}</button><button disabled={!jobId||loading||generating||exporting||researchBusy} onClick={generate}>Yangi ML harakatini tayyorlash</button>{generating&&<button onClick={cancelGeneration}>ML ni bekor qilish</button>}{items.length>0&&<><button disabled={exporting} onClick={toggle}>{playing?'Pauza':'Media bilan ijro etish'}</button><button disabled={exporting} onClick={()=>seek(0)}>Boshidan</button></>}</div>
 <div className="actions"><button className="primary" disabled={!captureReady||researchBusy||!!imported||!items.length||loading||generating||exporting} onClick={exportVideo}>Yangi avatar bilan MP4 yaratish</button>{exporting&&<button onClick={()=>exportAbort.current?.abort()}>Eksportni bekor qilish</button>}</div>
 {exportProgress&&<p role="status">{exportProgress}</p>}{exportResult&&<div className="result"><h3>Tajribaviy 3D video tayyor</h3>{media?.settings?.motion_revision!==ROCKETBOX_MOTION_REVISION&&<p role="status">Bu MP4 avatarning oldingi qo‘l va kutish holati bilan yaratilgan. Yangilangan ijro uchun «Yangi avatar bilan MP4 yaratish» tugmasini bosing.</p>}<ResultVideo src={`/api/jobs/${jobId}/result?v=${exportResult}`}/><a href={`/api/jobs/${jobId}/download?v=${exportResult}`}>MP4 yuklab olish</a></div>}
 {generation&&<p role="status">{generation}</p>}{jobId&&media&&<div className="actions"><a href={`/api/jobs/${jobId}/transcript/download?format=txt`}>Inglizcha matn · TXT</a><a href={`/api/jobs/${jobId}/transcript/download?format=srt`}>Asl media subtitri · SRT</a></div>}<p>ML uchun inglizcha nutq tahlili tayyor bo‘lishi kerak. CPU hisoblash vaqt oladi; bu tugma avatarni yoki modelni qayta o‘qitmaydi.</p>
 {!jobId&&<p>Mening fayllarim bo‘limidan tayyor ML harakati bor ishni oching.</p>}
 {media&&<div className="media"><h3>{media.name}</h3>{media.kind==='video'?<video controls src={`/api/jobs/${jobId}/media`} ref={m=>{el.current=m}} {...mediaEvents}/>:<audio controls src={`/api/jobs/${jobId}/media`} ref={m=>{el.current=m}} {...mediaEvents}/>}<p>{items.length} harakat bo‘lagi · vaqt koeffitsiyenti {scale.toFixed(2)}×</p><p>{current?.item.text||'Bu vaqt uchun harakat yo‘q — neytral holat'}</p><label>Harakat vaqti {time.toFixed(2)} / {duration.toFixed(2)} s<input type="range" disabled={exporting} min="0" max={duration} step=".01" value={Math.min(time,duration)} onChange={e=>seek(Number(e.target.value))}/></label><div className="segments">{items.map((i,n)=><button disabled={exporting} key={n} onClick={()=>seek(i.start)}>{i.start.toFixed(2)} s · {i.text}</button>)}</div></div>}
 {imported&&<div><h3>{imported}</h3><p>Import qilingan texnik ko‘rik · til va harakat ekspert tekshiruvidan o‘tmagan.</p><label>Import vaqti {time.toFixed(2)} / {duration.toFixed(2)} s<input type="range" min="0" max={duration} step=".01" value={time} onChange={e=>seek(Number(e.target.value))}/></label></div>}
 <ResearchTools onBusy={setResearchBusy} disabled={exporting||loading||generating} onImport={(motion,label)=>{const rows=validateNeuralMotion(motion),length=rows.length/motion.fps;request.current?.abort();el.current?.pause();setPlaying(false);setMedia(null);setExportResult('');setImported(label);setItems([{start:0,end:length,duration:length,text:label,motion}]);setDuration(length);setScale(1);setTime(0);setError('')}}/>
 {error&&<p role="alert">{error}</p>}<p>Microsoft Rocketbox · MIT. Harakatni moslashtirish tajribaviy: bilak, qo‘l shakli va yuzning ASL belgilari tasdiqlanmagan. MP4 tajribaviy 3D natija sifatida belgilanadi; lingvistik tasdiqni anglatmaydi.</p><p>Asosiy studiyadagi haqiqiy inson videolari ishlashda davom etadi.</p></section>;
}

