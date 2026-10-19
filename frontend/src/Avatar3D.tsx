import {Component,Suspense,useCallback,useEffect,useMemo,useRef,useState} from 'react';
import type {ReactNode} from 'react';
import {Canvas,useFrame,useLoader,useThree} from '@react-three/fiber';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as THREE from 'three';
import {createInterpreter} from './interpreter';
import {INTERPRETER_FOV,INTERPRETER_TARGET_Y,interpreterCameraDistance,neuralInterpreterCamera,studioInterpreterCamera} from './framing';
import type {SigningEnvelope} from './framing';
import {sampleNeuralSigningEnvelope} from './neuralFraming';
import {AVATAR_REST_TIME,sampleAvatarMotion} from './avatarMotion';
import {createNeuralClip,neuralMotionAssetUrl,validateNeuralMotion} from './neuralMotion';
import type {NeuralMotion} from './neuralMotion';

export type Motion={id:string;phrase:string;duration:number;keyframes:{time:number;rotations:Record<string,number[]>}[];status:string;source:string;license:string;reviewer?:string;animation_asset?:string;neural_asset?:string;purpose?:string};
export type AvatarFrame={asset:string|null;time:number;ready:boolean};
const MODEL_URL='/avatar/galtis.glb?v=3';
class CanvasBoundary extends Component<{children:ReactNode;onError:(error:Error)=>void},{failed:boolean}>{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true}}
 componentDidCatch(error:Error){this.props.onError(error)}
 render(){return this.state.failed?<p className="webgl-fallback">3D avatar hozir ko‘rsatilmayapti. Matn va subtitrlar mavjud.</p>:this.props.children}
}
const clipCache=new Map<string,Promise<THREE.AnimationClip>>();
const neuralDataCache=new Map<string,Promise<NeuralMotion>>();
const neuralBatchByAsset=new Map<string,string[]>();
const neuralEnvelopeCache=new Map<string,Promise<SigningEnvelope>>();
function loadNeuralData(asset:string){
 const url=neuralMotionAssetUrl(asset);
 if(!neuralDataCache.has(url))neuralDataCache.set(url,fetch(url)
  .then(response=>{if(!response.ok)throw new Error('Neyron model harakati ochilmadi. Qayta urinib ko‘ring.');return response.json()})
  .then((data:NeuralMotion)=>{validateNeuralMotion(data);return data})
  .catch(error=>{neuralDataCache.delete(url);throw error}));
 return neuralDataCache.get(url)!;
}
function loadNeuralEnvelope(asset:string,model:THREE.Object3D){
 const batch=neuralBatchByAsset.get(asset)||[asset],key=JSON.stringify(batch);
 if(!neuralEnvelopeCache.has(key))neuralEnvelopeCache.set(key,Promise.all(batch.map(loadNeuralData))
  .then(motions=>sampleNeuralSigningEnvelope(model,motions))
  .catch(error=>{neuralEnvelopeCache.delete(key);throw error}));
 return neuralEnvelopeCache.get(key)!;
}
function loadClip(key:string){
 if(!clipCache.has(key)){
  clipCache.set(key,fetch(`/avatar/${encodeURIComponent(key)}.motion.json`)
   .then(response=>{if(!response.ok)throw new Error('Harakat fayli ochilmadi. Qayta yuklashni bosing.');return response.json()})
   .then(data=>{
    const clip=THREE.AnimationClip.parse(data);
    if(!Number.isFinite(clip.duration)||clip.duration<=0||!clip.tracks.length)throw new Error('Harakat yozuvi yaroqsiz. Boshqa klipni tanlang.');
    return clip;
   })
   .catch(error=>{clipCache.delete(key);throw error}));
 }
 return clipCache.get(key)!;
}
export async function prepareMotions(motions:Motion[]){
 const assets=[...new Set(motions.map(motion=>motion.animation_asset).filter((asset):asset is string=>!!asset))];
 const neural=[...new Set(motions.map(motion=>motion.neural_asset).filter((asset):asset is string=>!!asset))];
 neural.sort();for(const asset of neural)neuralBatchByAsset.set(asset,neural);
 await Promise.all([...assets.map(loadClip),...neural.map(loadNeuralData)]);
}
function CanvasUnavailable(){
 return <p className="webgl-fallback">Brauzer 3D WebGL oynasini ocha olmadi. Matn va subtitrlar mavjud.</p>;
}
function CanvasBridge({onCanvas}:{onCanvas?:(canvas:HTMLCanvasElement|null)=>void}){
 const gl=useThree(state=>state.gl);
 useEffect(()=>{onCanvas?.(gl.domElement);return()=>onCanvas?.(null)},[gl,onCanvas]);
 return null;
}
function InterpreterCamera({angle,envelope,minimal}:{angle:number;envelope:SigningEnvelope|null;minimal:boolean}){
 const camera=useThree(state=>state.camera),size=useThree(state=>state.size),invalidate=useThree(state=>state.invalidate);
 useEffect(()=>{
  if(!(camera instanceof THREE.PerspectiveCamera)||!size.width||!size.height)return;
  camera.aspect=size.width/size.height;camera.fov=INTERPRETER_FOV;
  const framing=envelope?neuralInterpreterCamera(envelope,camera.aspect,angle):minimal?studioInterpreterCamera(camera.aspect,angle):{x:0,targetY:INTERPRETER_TARGET_Y,distance:interpreterCameraDistance(camera.aspect,angle)};
  camera.position.set(framing.x,framing.targetY,framing.distance);
  camera.lookAt(framing.x,framing.targetY,0);camera.updateProjectionMatrix();invalidate();
 },[camera,size.width,size.height,angle,envelope,minimal,invalidate]);
 return null;
}
function Character({motion,time,angle,onModelReady,onModelProgress,onModelError,onMotionLoading,onMotionError,onFrame,onEnvelope}:{
 motion:Motion|null;time:number;angle:number;onModelReady:()=>void;onModelProgress:(event:ProgressEvent)=>void;
 onModelError:(message:string)=>void;onMotionLoading:(value:boolean)=>void;onMotionError:(value:string)=>void;
 onFrame?:(frame:AvatarFrame)=>void;
 onEnvelope:(envelope:SigningEnvelope)=>void;
}){
 const invalidate=useThree(state=>state.invalidate);
 const gl=useThree(state=>state.gl);
 const get=useThree(state=>state.get);
 const gltf=useLoader(GLTFLoader,MODEL_URL,undefined,onModelProgress);
 const model=useMemo(()=>createInterpreter(gltf.scene),[gltf]);
 const mixer=useMemo(()=>new THREE.AnimationMixer(model),[model]);
 const action=useRef<THREE.AnimationAction|null>(null);
 const readyToPaint=useRef(false),loadedAsset=useRef<string|null>(null);
 // Frame zero is a calibration T-pose in this archive; frame one is recorded rest.
 const neural=motion?.neural_asset||null,asset=neural||motion?.animation_asset||'hello';
 useEffect(()=>{invalidate()},[time,angle,motion,invalidate]);
 useEffect(()=>{
  onModelReady();
  const canvas=gl.domElement;
  const lost=(event:Event)=>{
   // R3F deliberately releases WebGL when a Canvas is removed or retried.
   if(!get().internal.active||!canvas.isConnected)return;
   event.preventDefault();onModelError('3D grafik aloqasi uzildi. Tiklanmasa, qayta yuklashni bosing.');
  };
  const restored=()=>{onModelReady();invalidate()};
  canvas.addEventListener('webglcontextlost',lost);
  canvas.addEventListener('webglcontextrestored',restored);
  return()=>{canvas.removeEventListener('webglcontextlost',lost);canvas.removeEventListener('webglcontextrestored',restored)};
 },[gl,get,invalidate,onModelReady,onModelError]);
 useEffect(()=>{
  let active=true;
  action.current=null;readyToPaint.current=false;loadedAsset.current=null;
  mixer.stopAllAction();
  onMotionError('');
  onMotionLoading(true);
  invalidate();
  const pending=neural?Promise.all([loadNeuralData(neural),loadNeuralEnvelope(neural,model)]).then(([data,envelope])=>{
   if(active)onEnvelope(envelope);return createNeuralClip(model,data);
  }):loadClip(asset);
  pending.then(clip=>{
   if(!active)return;
   const next=mixer.clipAction(clip);
   next.setLoop(THREE.LoopOnce,1);
   next.clampWhenFinished=true;
   next.play();
   action.current=next;
   loadedAsset.current=asset;
   sampleAvatarMotion(mixer,next,neural?0:AVATAR_REST_TIME,true,neural?0:AVATAR_REST_TIME);
   readyToPaint.current=true;
   invalidate();
  }).catch(error=>{
   if(!active)return;
   // Do not leave the previous sign visible after a failed or stale request.
   action.current=null;loadedAsset.current=null;readyToPaint.current=false;
   mixer.stopAllAction();
   onMotionLoading(false);
   onMotionError(error instanceof Error?error.message:'Harakat fayli yuklanmadi. Qayta yuklashni bosing.');
   invalidate();
  });
  return()=>{active=false;action.current=null;loadedAsset.current=null;readyToPaint.current=false;mixer.stopAllAction()};
 },[asset,neural,model,mixer,invalidate,onMotionLoading,onMotionError,onEnvelope]);
 useEffect(()=>()=>{mixer.stopAllAction();mixer.uncacheRoot(model)},[mixer,model]);
 useFrame(state=>{
  const loaded=!!action.current&&loadedAsset.current===asset;
  const sampled=loaded?sampleAvatarMotion(mixer,action.current!,time,!!(motion?.neural_asset||motion?.animation_asset),neural?0:AVATAR_REST_TIME):neural?0:AVATAR_REST_TIME;
  // A positive priority takes responsibility for drawing. Readiness and export
  // observers now run only after the requested recorded pose reached WebGL.
  state.gl.render(state.scene,state.camera);
  if(loaded&&readyToPaint.current){readyToPaint.current=false;onMotionLoading(false)}
  onFrame?.({asset:motion?.neural_asset||motion?.animation_asset||null,time:sampled,ready:loaded});
 },1);
 // Keep the asset root in native centimetres for motion/framing calculations.
 // Only the display parent converts it to the scene's metre coordinates.
 return <group rotation={[0,angle,0]} scale={.01}><primitive object={model}/></group>;
}
export function Avatar3D({motion=null,time=0,preview=false,minimal=!preview,onReady,onCanvas,onFrame,capture=false}:{motion?:Motion|null;time?:number;preview?:boolean;minimal?:boolean;onReady?:(ready:boolean)=>void;onCanvas?:(canvas:HTMLCanvasElement|null)=>void;onFrame?:(frame:AvatarFrame)=>void;capture?:boolean}){
 const [angle,setAngle]=useState(0),[playing,setPlaying]=useState(true),[speed,setSpeed]=useState('1'),[position,setPosition]=useState(0),[background,setBackground]=useState('studio');
 const [modelLoading,setModelLoading]=useState(true),[modelProgress,setModelProgress]=useState<number|null>(null),[motionLoading,setMotionLoading]=useState(true);
 const [modelError,setModelError]=useState(''),[motionError,setMotionError]=useState(''),[retry,setRetry]=useState(0);
 const [neuralEnvelope,setNeuralEnvelope]=useState<SigningEnvelope|null>(null);
 const length=motion?.duration||0;
 const error=modelError||motionError;
 const loading=!error&&(modelLoading||motionLoading);
 const modelReady=useCallback(()=>{setModelLoading(false);setModelError('')},[]);
 const modelFailed=useCallback((cause:Error)=>setModelError(`Avatar ochilmadi${cause?.message?`: ${cause.message}`:'.'} 3D fayllarni qayta yuklashni bosing.`),[]);
 const modelProgressed=useCallback((event:ProgressEvent)=>setModelProgress(event.lengthComputable?Math.round(event.loaded/event.total*100):null),[]);
 useEffect(()=>{onReady?.(!loading&&!error)},[loading,error,onReady]);
 useEffect(()=>{setPosition(0);setPlaying(true)},[motion?.id]);
 // Keep one sequence envelope through gaps. Captured assets keep their
 // original camera; they never inherit a neural close-up.
 useEffect(()=>{if(motion?.animation_asset&&!motion.neural_asset)setNeuralEnvelope(null)},[motion?.animation_asset,motion?.neural_asset]);
 useEffect(()=>{
  if(!preview||!playing||!length||loading||error)return;
  let frame=0,last=performance.now();
  const step=(now:number)=>{
   const delta=Math.min((now-last)/1000,.1);last=now;
   setPosition(value=>(value+delta*Number(speed))%(length+.65));
   frame=requestAnimationFrame(step);
  };
  frame=requestAnimationFrame(step);
  return()=>cancelAnimationFrame(frame);
 },[preview,playing,speed,length,loading,error]);
 function reload(){
  if(motion?.neural_asset){neuralDataCache.delete(motion.neural_asset);neuralEnvelopeCache.delete(JSON.stringify(neuralBatchByAsset.get(motion.neural_asset)||[motion.neural_asset]))}
  clipCache.delete(motion?.animation_asset||'hello');
  useLoader.clear(GLTFLoader,MODEL_URL);
  setModelError('');setMotionError('');setModelLoading(true);setMotionLoading(true);setModelProgress(null);
  setRetry(value=>value+1);
 }
 const legacy=!!motion&&!motion.animation_asset&&!motion.neural_asset;
 const initialFraming=minimal?studioInterpreterCamera(1):{x:0,targetY:INTERPRETER_TARGET_Y,distance:interpreterCameraDistance(1)};
 return <div className={`avatar-3d interpreter-stage ${minimal?'interpreter-minimal':'interpreter-preview'} ${background==='contrast'?'avatar-contrast':''}`}>
   <div className="three-canvas" role="img" aria-label="ASL avatari — tana, qo‘l va barmoq harakatlari" aria-busy={loading}>
    <CanvasBoundary key={retry} onError={modelFailed}><Suspense fallback={null}>
     <Canvas key={capture?'capture':'preview'} frameloop="demand" fallback={<CanvasUnavailable/>} camera={{position:[initialFraming.x,initialFraming.targetY,initialFraming.distance],fov:INTERPRETER_FOV}} dpr={[1,2]} gl={{antialias:true,alpha:true,preserveDrawingBuffer:capture}} onCreated={({camera})=>camera.lookAt(initialFraming.x,initialFraming.targetY,0)}>
      <CanvasBridge onCanvas={onCanvas}/>
      <InterpreterCamera angle={angle} envelope={neuralEnvelope} minimal={minimal}/>
      <color attach="background" args={[background==='contrast'?'#242842':'#f0effb']}/>
      <ambientLight intensity={.35}/><hemisphereLight args={['#fff8f2','#7b86a0',.8]}/>
      <directionalLight position={[-3,5,6]} intensity={2.3}/><directionalLight position={[3,3,4]} intensity={.8}/>
      <Character motion={legacy?null:motion} time={preview?Math.min(position,length):time} angle={angle} onModelReady={modelReady} onModelProgress={modelProgressed} onModelError={setModelError} onMotionLoading={setMotionLoading} onMotionError={setMotionError} onFrame={onFrame} onEnvelope={setNeuralEnvelope}/>
     </Canvas>
    </Suspense></CanvasBoundary>
   </div>
  {loading&&<div className="quality-note interpreter-status" role="status"><p>{modelLoading?`Avatar tayyorlanmoqda${modelProgress===null?'…':` · ${modelProgress}%`}`:'Harakat tayyorlanmoqda…'}</p><progress max="100" value={modelLoading?modelProgress??undefined:undefined} aria-label={modelLoading?'3D avatarni yuklash':'Harakat yozuvini yuklash'}/></div>}
  {error&&<div className="quality-note interpreter-status"><p role="alert" className="inline-error">{error}</p><button className="secondary" onClick={reload}>Qayta yuklash</button></div>}
  {legacy&&<p className="quality-note">Bu eski geometrik rig klipi. Yangi avatarda ko‘rsatish uchun mos harakat yozuvini tanlang.</p>}
  {!minimal&&preview&&(motion?.animation_asset||motion?.neural_asset)&&<div className="motion-transport">
   <div><button className="secondary" disabled={loading||!!error} onClick={()=>setPlaying(!playing)}>{playing?'Pauza':'Ijro etish'}</button><button className="icon-button" aria-label="Harakatni boshidan boshlash" disabled={loading||!!error} onClick={()=>setPosition(0)}>↺</button>
    <label>Tezlik<select aria-label="Ishora tezligi" value={speed} onChange={event=>setSpeed(event.target.value)}><option value="0.5">0.5×</option><option value="0.75">0.75×</option><option value="1">1×</option></select></label>
    <span>{Math.min(position,length).toFixed(1)} / {length.toFixed(1)}s</span>
   </div>
   <input aria-label="Ishora vaqti" type="range" min="0" max={length} step=".01" value={Math.min(position,length)} disabled={loading||!!error} onChange={event=>{setPlaying(false);setPosition(Number(event.target.value))}}/>
  </div>}
  {!minimal&&<div className="avatar-view-controls"><label>Burchak<input type="range" aria-label="Avatar ko‘rish burchagi" min="-.65" max=".65" step=".01" value={angle} onChange={event=>setAngle(Number(event.target.value))}/></label><button className="secondary" onClick={()=>{setAngle(0);setBackground(background==='studio'?'contrast':'studio')}}>{background==='studio'?'To‘q fon':'Yorug‘ fon'}</button></div>}
 </div>;
}
