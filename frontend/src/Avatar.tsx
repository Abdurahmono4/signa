import {Suspense,useEffect,useMemo,useRef} from 'react';
import {Canvas,useFrame,useLoader,useThree} from '@react-three/fiber';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as THREE from 'three';
import {createInterpreter} from './interpreter';
import {createNeuralClip,validateNeuralMotion} from './neuralMotion';
export type Item={text:string;start:number;end:number;supported:boolean;animation_path:string|null;duration_ms:number|null;sign_id:string|null;reason:string;neural_asset?:string|null;video_url?:string|null;timing_source?:string|null};
export type AvatarHandle={capture:(time:number,items:Item[])=>Promise<Blob>};
const clips=new Map<string,Promise<THREE.AnimationClip>>();
async function clip(path:string){
 if(!clips.has(path))clips.set(path,fetch(path).then(r=>{if(!r.ok)throw Error('Animatsiya ochilmadi');return r.json()}).then(data=>THREE.AnimationClip.parse(data)).catch(e=>{clips.delete(path);throw e}));
 return clips.get(path)!;
}
function Scene({time,items,demo,onReady,onError}:{time:number;items:Item[];demo:boolean;onReady:(h:AvatarHandle|null)=>void;onError:(s:string)=>void}){
 const {gl,scene,camera,invalidate}=useThree();
 const source=useLoader(GLTFLoader,'/assets/avatars/galtis.glb');
 const model=useMemo(()=>createInterpreter(source.scene),[source]);
 const mixer=useMemo(()=>new THREE.AnimationMixer(model),[model]);
 const current=useRef('');const action=useRef<THREE.AnimationAction|null>(null);const ticket=useRef(0);
 async function pose(t:number,sequence:Item[],forceDemo=false){
  const turn=++ticket.current;
  const item=sequence.find(s=>s.supported&&t>=s.start&&t<s.end);
  const path=item?.neural_asset||item?.animation_path||'/assets/animations/demo-asl-hello.json';
  if(item?.neural_asset&&!clips.has(path))clips.set(path,fetch(path).then(r=>{if(!r.ok)throw Error('ML harakati ochilmadi');return r.json()}).then(data=>{validateNeuralMotion(data);return createNeuralClip(model,data)}).catch(e=>{clips.delete(path);throw e}));
  const loaded=await clip(path);if(turn!==ticket.current)return;
  if(current.current!==path){mixer.stopAllAction();action.current=mixer.clipAction(loaded);action.current.setLoop(THREE.LoopOnce,1);action.current.clampWhenFinished=true;current.current=path;}
  const at=item?Math.max(1/30,Math.min(loaded.duration,(t-item.start)/(item.end-item.start)*loaded.duration)):forceDemo?t%loaded.duration:1/30;
  action.current!.reset().play();mixer.setTime(at);model.updateMatrixWorld(true);invalidate();
 }
 useEffect(()=>{pose(time,items).catch(e=>onError(String(e)))},[time,items]);
 useFrame(({clock})=>{if(demo)void pose(clock.elapsedTime,[],true)});
 useEffect(()=>{
  let active=true;
  pose(0,[]).then(()=>{if(active)onReady({capture:async(t,sequence)=>{
   await pose(t,sequence);
   const previous=gl.getSize(new THREE.Vector2());
   const aspect=camera instanceof THREE.PerspectiveCamera?camera.aspect:null;
   try{
    gl.setSize(384,512,false);
    if(camera instanceof THREE.PerspectiveCamera){camera.aspect=384/512;camera.updateProjectionMatrix()}
    gl.render(scene,camera);
    return await new Promise<Blob>((resolve,reject)=>gl.domElement.toBlob(b=>b?resolve(b):reject(Error('Kadr yozilmadi')),'image/png'));
   }finally{
    gl.setSize(previous.x,previous.y,false);
    if(camera instanceof THREE.PerspectiveCamera&&aspect!==null){camera.aspect=aspect;camera.updateProjectionMatrix()}
    invalidate();
   }
  }})}).catch(e=>onError(String(e)));
  return()=>{active=false;onReady(null);mixer.stopAllAction();};
 },[mixer,gl,scene,camera]);
 return <primitive object={model} scale={.01}/>;
}
export function Avatar({time=0,items=[],demo=false,onReady,onError}:{time?:number;items?:Item[];demo?:boolean;onReady:(h:AvatarHandle|null)=>void;onError:(s:string)=>void}){
 return <div className="avatar-canvas" role="img" aria-label="Barmoqlari va qo‘llari harakatlanuvchi 3D avatar"><Canvas frameloop={demo?'always':'demand'} dpr={1} gl={{alpha:true,antialias:true,preserveDrawingBuffer:true}} camera={{position:[0,1.48,2.2],fov:34}} onCreated={({camera,gl})=>{camera.lookAt(0,1.48,0);gl.setClearColor(0x000000,0)}}><ambientLight intensity={1.5}/><hemisphereLight args={['#fff4ed','#7b88c0',1]}/><directionalLight position={[2,3,4]} intensity={2}/><Suspense fallback={null}><Scene time={time} items={items} demo={demo} onReady={onReady} onError={onError}/></Suspense></Canvas></div>;
}
