import * as THREE from 'three';
import {createNeuralClip} from './neuralMotion';
import type {NeuralMotion} from './neuralMotion';
/** Presentation-only rest pose. This is never a dictionary entry or an ASL sign. */
export function createRocketboxIdleClip(model:THREE.Object3D){
 const frame=Array(133).fill(0);
 // Lower the extended-arm reference, with a little elbow flexion forward.
 frame[14]=-1.36;frame[17]=1.36;
 frame[19]=-.12;frame[22]=.12;
 const clip=createRocketboxClip(model,{fps:24,frames:[frame],name:'Relaxed presentation rest (not a sign)'});
 clip.name='Relaxed presentation rest (not a sign)';
 return clip;
}
export const ROCKETBOX_TARGETS:Readonly<Record<string,string>>=Object.freeze(Object.fromEntries([
 ['neck_01','Bip01_Neck'],['head','Bip01_Head'],['jaw','Bip01_MJaw'],
 ...(['l','r'] as const).flatMap(side=>{
  const prefix=`Bip01_${side.toUpperCase()}_`;
  return [['clavicle','Clavicle'],['upperarm','UpperArm'],['lowerarm','Forearm'],['hand','Hand']].map(([from,to])=>[`${from}_${side}`,prefix+to]).concat(
   ['thumb','index','middle','ring','pinky'].flatMap((finger,index)=>[1,2,3].map(joint=>[`${finger}_0${joint}_${side}`,`${prefix}Finger${index}${joint===1?'':joint-1}`])));
 }),
]));
export function createRocketboxClip(model:THREE.Object3D,motion:NeuralMotion){
 const clip=createNeuralClip(model,motion,ROCKETBOX_TARGETS,true,rocketboxReference(model));
 return Object.assign(clip,{retargeting:{method:'smplx-to-rocketbox-jaw-v6',verified:false,
  warning:'Arm rest directions are calibrated geometrically. Palm roll, source hand mean and facial semantics still require validation.'}});
}

/** Match arm rest directions before applying source rotation deltas.
 * The destination's A pose is not the source's extended-arm reference.
 * Keep skin bind matrices and bone lengths intact; only emitted rotations change.
 */
export function rocketboxReference(model:THREE.Object3D){
 model.updateMatrixWorld(true);
 const refs=new Map<string,THREE.Quaternion>();
 for(const side of ['L','R']){
  const prefix=`Bip01_${side}_`,axis=new THREE.Vector3(side==='L'?1:-1,0,0);
  const get=(suffix:string)=>{const bone=model.getObjectByName(prefix+suffix);if(!(bone instanceof THREE.Bone))throw Error(`Missing calibration joint ${prefix+suffix}`);return bone};
  const position=(bone:THREE.Object3D)=>bone.getWorldPosition(new THREE.Vector3());
  const align=(bone:THREE.Bone,child:THREE.Bone)=>{
   const direction=position(child).sub(position(bone));
   if(direction.lengthSq()<1e-10)throw Error('Arm reference has a zero-length segment.');
   return new THREE.Quaternion().setFromUnitVectors(direction.normalize(),axis);
  };
  for(const [from,to] of [['UpperArm','Forearm'],['Forearm','Hand']]){
   const bone=get(from),q=align(bone,get(to));
   refs.set(bone.name,q.multiply(bone.getWorldQuaternion(new THREE.Quaternion())).normalize());
  }
  const hand=get('Hand'),handCorrection=align(hand,get('Finger2'));
  const fingerNames=new Set(Array.from({length:5},(_,f)=>['','1','2'].map(s=>prefix+`Finger${f}${s}`)).flat());
  model.traverse(bone=>{if(bone instanceof THREE.Bone&&(bone===hand||fingerNames.has(bone.name)))refs.set(bone.name,handCorrection.clone().multiply(bone.getWorldQuaternion(new THREE.Quaternion())).normalize())});
 }
 return refs;
}
