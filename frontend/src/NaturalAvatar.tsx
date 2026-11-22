import {Suspense,useMemo,useState,useEffect,Component} from 'react';
import type {ReactNode} from 'react';
import {Canvas,useLoader,useFrame} from '@react-three/fiber';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as THREE from 'three';
import {clone} from 'three/examples/jsm/utils/SkeletonUtils.js';
import {createRocketboxClip} from './rocketboxMotion';
import {validateNeuralMotion} from './neuralMotion';
import type {NeuralMotion} from './neuralMotion';

const ROOT='/assets/avatars/rocketbox-female-01/';
class PreviewBoundary extends Component<{children:ReactNode},{error:string}>{
 state={error:''};static getDerivedStateFromError(error:Error){return {error:error.message}}
 render(){return this.state.error?<p role="alert">Model ochilmadi: {this.state.error}</p>:this.props.children}
}
function Woman({motion,playing,time,onTime}:{motion:NeuralMotion|null;playing:boolean;time:number;onTime:(t:number)=>void}){
 const source=useLoader(GLTFLoader,ROOT+'female.glb');
 const model=useMemo(()=>{
  const object=clone(source.scene);
  object.traverse(node=>{
   if(!(node instanceof THREE.Mesh))return;
   node.frustumCulled=false;
  });
  return object;
 },[source]);
 const mixer=useMemo(()=>new THREE.AnimationMixer(model),[model]);
 const clip=useMemo(()=>motion?createRocketboxClip(source.scene,motion):null,[source,motion]);
 useEffect(()=>{mixer.stopAllAction();if(clip){const action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();mixer.setTime(time)}return()=>{mixer.stopAllAction()}},[clip,mixer]);
 useEffect(()=>{if(clip)mixer.setTime(Math.min(time,clip.duration-.0001))},[time,mixer,clip]);
 useFrame((_,delta)=>{if(clip&&playing){const next=Math.min(mixer.time+delta,clip.duration-.0001);mixer.setTime(next);onTime(next)}});
 return <primitive object={model}/>;
}
export default function NaturalAvatar({jobId}:{jobId?:string}){
 const [angle,setAngle]=useState(0);
 const [motion,setMotion]=useState<NeuralMotion|null>(null),[playing,setPlaying]=useState(false),[time,setTime]=useState(0),[error,setError]=useState(''),[label,setLabel]=useState(''),[loading,setLoading]=useState(false);
 const duration=motion?(motion.frames||motion.features||[]).length/motion.fps:0;
 const updateTime=(t:number)=>{setTime(t);if(t>=duration-.001)setPlaying(false)};
 async function loadExisting(){
  if(!jobId)return;setLoading(true);setError('');setPlaying(false);
  try{
   const response=await fetch(`/api/jobs/${jobId}/neural/plan`);if(!response.ok)throw Error('Bu ish uchun tayyor ML harakati yo‘q.');
   const plan=await response.json();const item=plan.items.find((i:{neural_asset?:string})=>i.neural_asset);
   if(!item)throw Error('Harakat bo‘lagi topilmadi.');
   const r=await fetch(item.neural_asset);if(!r.ok)throw Error('Harakat fayli yuklanmadi.');
   const data=await r.json();validateNeuralMotion(data);setMotion(data);setLabel(item.text);setTime(0);
  }catch(e){setError(String(e))}finally{setLoading(false)}
 }
 return <section className="card"><div className="section-head"><h2>Yangi ayol modeli</h2><span className="pill">QIYOFA SINOVI</span></div>
 <PreviewBoundary><div style={{height:560,maxWidth:520,margin:'auto',background:'#81cbd0',borderRadius:14,overflow:'hidden'}}>
 <Canvas camera={{position:[0,1.36,2.1],fov:32}} dpr={[1,1.5]} onCreated={({camera})=>camera.lookAt(0,1.32,0)}>
 <ambientLight intensity={1.5}/><hemisphereLight args={['#fff6ef','#789ba6',1]}/><directionalLight position={[2,3,4]} intensity={2.2}/>
 <Suspense fallback={null}><group rotation={[0,angle,0]}><Woman motion={motion} playing={playing} time={time} onTime={updateTime}/></group></Suspense>
 </Canvas></div></PreviewBoundary>
 <label>Qiyofani burish<input type="range" min="-.65" max=".65" step=".01" value={angle} onChange={e=>setAngle(Number(e.target.value))}/></label>
 <div className="actions"><button disabled={!jobId||loading} onClick={loadExisting}>{loading?'Harakat yuklanmoqda…':'Saqlangan ML harakatini yuklash'}</button>{motion&&<><button onClick={()=>{if(time>=duration-.001)setTime(0);setPlaying(p=>!p)}}>{playing?'Pauza':'Tajribaviy ijroni boshlash'}</button><button onClick={()=>{setPlaying(false);setTime(0)}}>Boshidan</button></>}</div>
 {motion&&<><p>{label}</p><label>Harakat vaqti {time.toFixed(2)} / {duration.toFixed(2)} s<input type="range" min="0" max={Math.max(0,duration-.001)} step=".01" value={time} onChange={e=>{setPlaying(false);setTime(Number(e.target.value))}}/></label></>}
 {error&&<p role="alert">{error}</p>}
 <p>Microsoft Rocketbox · MIT · barcha barmoqlar va 52 yuz kanali. Harakatni moslashtirish tajribaviy: bilak, qo‘l shakli va yuzning ASL belgilari hali tasdiqlanmagan. Bu oyna tayyor tarjimon sifatida eksport qilinmaydi.</p>
 <p>Asosiy studiyadagi haqiqiy inson videolari ishlashda davom etadi.</p>
 </section>;
}
