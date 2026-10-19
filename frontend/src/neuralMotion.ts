import * as THREE from 'three';
import {clone} from 'three/examples/jsm/utils/SkeletonUtils.js';

// MaDiS official sign_loader._pose_features / H2S.feats2joints layout:
// 10 upper-body axis angles, 15 left-hand, 15 right-hand, jaw, 10 expression
// coefficients. These are DENORMALIZED axis-angle radians, not 6D rotations.
export type NeuralMotion={frames?:readonly (readonly number[])[];features?:readonly (readonly number[])[];fps:number;name?:string;normalized?:boolean;format?:string};
export const NEURAL_FEATURES=133;
export function validateNeuralMotion(motion:NeuralMotion){
 if(motion.normalized===true)throw new Error('Denormalize MaDiS features with the official mean/std before rendering.');
 if(motion.format&&!['madis-axis-angle-133','signa-madis-133-v1'].includes(motion.format))throw new Error('Unsupported neural motion format.');
 const frames=motion.frames||motion.features;
 if(!Array.isArray(frames)||frames.length<1||frames.length>30000)throw new Error('Neural motion needs 1–30000 frames.');
 if(!Number.isFinite(motion.fps)||motion.fps<1||motion.fps>120)throw new Error('Neural motion FPS must be between 1 and 120.');
 frames.forEach(validateFrame);
 return frames;
}
export function neuralMotionAssetUrl(asset:string){
 if(!asset.startsWith('/api/')||asset.startsWith('//')||/[\\\s#]/.test(asset)||asset.includes('..'))throw new Error('Neural motion asset must use a relative /api/ path.');
 return asset;
}
export const NEURAL_RETARGET_LIMITATIONS=Object.freeze([
 'SMPL-X rotation deltas are retargeted onto the CC0 Galtis bind skeleton; this is an approximation requiring visual validation.',
 'SMPL-X learned hand-mean offsets are not bundled because the licensed model assets are not present.',
 'Jaw and ten SMPL-X expression coefficients have no verified mapping to this avatar and are not synthesized.',
 'Root and lower-body motion are absent from the 133-feature output and remain at the destination bind pose.',
]);

type Joint={key:string;parent:string|null;offset:number;target:string};
const JOINTS:Joint[]=[
 {key:'neck',parent:null,offset:0,target:'neck_01'},
 {key:'left_collar',parent:null,offset:3,target:'clavicle_l'},
 {key:'right_collar',parent:null,offset:6,target:'clavicle_r'},
 {key:'head',parent:'neck',offset:9,target:'head'},
 {key:'left_shoulder',parent:'left_collar',offset:12,target:'upperarm_l'},
 {key:'right_shoulder',parent:'right_collar',offset:15,target:'upperarm_r'},
 {key:'left_elbow',parent:'left_shoulder',offset:18,target:'lowerarm_l'},
 {key:'right_elbow',parent:'right_shoulder',offset:21,target:'lowerarm_r'},
 {key:'left_wrist',parent:'left_elbow',offset:24,target:'hand_l'},
 {key:'right_wrist',parent:'right_elbow',offset:27,target:'hand_r'},
];
for(const [side,offset] of [['left',30],['right',75]] as const){
 for(const [fingerIndex,finger] of ['index','middle','pinky','ring','thumb'].entries()){
  for(let joint=1;joint<=3;joint++)JOINTS.push({
   key:`${side}_${finger}${joint}`,parent:joint===1?`${side}_wrist`:`${side}_${finger}${joint-1}`,
   offset:offset+fingerIndex*9+(joint-1)*3,target:`${finger}_0${joint}_${side==='left'?'l':'r'}`,
  });
 }
}
export const NEURAL_JOINT_LAYOUT=Object.freeze(JOINTS.map(joint=>Object.freeze({...joint})));

function validateFrame(frame:readonly number[],index:number){
 if(!Array.isArray(frame)||frame.length!==NEURAL_FEATURES||!frame.every(value=>typeof value==='number'&&Number.isFinite(value)))throw new Error(`Neural frame ${index} must contain exactly 133 finite denormalized values.`);
}
function axisAngle(frame:readonly number[],offset:number){
 const x=frame[offset],y=frame[offset+1],z=frame[offset+2],angle=Math.hypot(x,y,z);
 if(angle<1e-12)return new THREE.Quaternion();
 const scale=Math.sin(angle/2)/angle;
 return new THREE.Quaternion(x*scale,y*scale,z*scale,Math.cos(angle/2)).normalize();
}
export function neuralSourceRotations(frame:readonly number[]){
 validateFrame(frame,0);
 const rotations=new Map<string,THREE.Quaternion>();
 for(const joint of JOINTS){
  const local=axisAngle(frame,joint.offset),parent=joint.parent?rotations.get(joint.parent):null;
  rotations.set(joint.key,parent?parent.clone().multiply(local).normalize():local);
 }
 return rotations;
}

// The shipped GLB's initial nodes are a captured pose, not the skin bind pose.
// Its head/body also use two interleaved skeletons (canonical and *_1). Restore
// all inverse-bind matrices together before deriving any local transform.
function targetBind(model:THREE.Object3D){
 const working=clone(model),bindMatrices=new Map<THREE.Bone,THREE.Matrix4>();
 working.traverse(object=>{
  if(!(object instanceof THREE.SkinnedMesh))return;
  object.skeleton.bones.forEach((bone,index)=>{
   const inverse=object.skeleton.boneInverses[index];
   if(!inverse||!inverse.elements.every(Number.isFinite))throw new Error(`Invalid inverse bind for ${bone.name}.`);
   const matrix=inverse.clone().invert(),previous=bindMatrices.get(bone);
   if(previous&&previous.elements.some((value,i)=>Math.abs(value-matrix.elements[i])>1e-4))throw new Error(`Conflicting inverse binds for ${bone.name}.`);
   bindMatrices.set(bone,matrix);
  });
 });
 if(!bindMatrices.size)throw new Error('Neural retargeting needs a skinned destination with inverse-bind matrices.');
 for(const [bone,matrix] of bindMatrices)bone.matrixWorld.copy(matrix);
 const local=new THREE.Matrix4();
 for(const [bone,matrix] of bindMatrices){
  if(bone.parent instanceof THREE.Bone){
   const parent=bindMatrices.get(bone.parent);
   if(!parent)throw new Error(`Bind parent ${bone.parent.name} is absent for ${bone.name}.`);
   local.copy(parent).invert().multiply(matrix);
  }else local.copy(matrix);
  local.decompose(bone.position,bone.quaternion,bone.scale);
 }
 working.updateMatrixWorld(true);
 return {working,bones:new Set(bindMatrices.keys())};
}

export function createNeuralClip(model:THREE.Object3D,motion:NeuralMotion):THREE.AnimationClip{
 const frames=validateNeuralMotion(motion);
 const {working,bones}=targetBind(model),nodes:THREE.Object3D[]=[];
 working.traverse(node=>nodes.push(node));
 const restGlobal=new Map<THREE.Object3D,THREE.Quaternion>(),restLocal=new Map<THREE.Object3D,THREE.Quaternion>();
 for(const node of nodes){restGlobal.set(node,node.getWorldQuaternion(new THREE.Quaternion()));restLocal.set(node,node.quaternion.clone())}
 const targets=new Map<THREE.Object3D,Joint>(),names=new Set<string>();
 for(const joint of JOINTS){
  const target=working.getObjectByName(joint.target);
  if(!(target instanceof THREE.Bone)||!bones.has(target))throw new Error(`Missing Galtis neural target ${joint.target}.`);
  targets.set(target,joint);
 }
 for(const bone of bones){if(!bone.name||names.has(bone.name))throw new Error(`Ambiguous neural target name ${bone.name}.`);names.add(bone.name)}
 const duration=frames.length/motion.fps,times=frames.map((_,index)=>index/motion.fps);
 times.push(duration); // Retain the final decoded frame for its full interval.
 const lanes=new Map<THREE.Object3D,number[]>();for(const target of targets.keys())lanes.set(target,[]);
 for(const frame of frames){
  const source=neuralSourceRotations(frame),currentGlobal=new Map<THREE.Object3D,THREE.Quaternion>();
  for(const node of nodes){
   const parent=node.parent?currentGlobal.get(node.parent):null,joint=targets.get(node);
   if(joint){
    // Both rigs use Y-up world axes. Source rest joint orientations are the
    // identity convention; the destination's real bind orientation is kept.
    const global=source.get(joint.key)!.clone().multiply(restGlobal.get(node)!).normalize();
    const local=parent?parent.clone().invert().multiply(global).normalize():global.clone();
    const values=lanes.get(node)!;
    if(values.length){const last=new THREE.Quaternion().fromArray(values,values.length-4);if(last.dot(local)<0)local.set(-local.x,-local.y,-local.z,-local.w)}
    values.push(local.x,local.y,local.z,local.w);currentGlobal.set(node,global);
   }else currentGlobal.set(node,parent?parent.clone().multiply(restLocal.get(node)!).normalize():restLocal.get(node)!.clone());
  }
 }
 const tracks:THREE.KeyframeTrack[]=[];
 for(const bone of bones){
  const values=lanes.get(bone);
  if(values){values.push(...values.slice(-4));tracks.push(new THREE.QuaternionKeyframeTrack(`${bone.name}.quaternion`,times,values))}
  else tracks.push(new THREE.QuaternionKeyframeTrack(`${bone.name}.quaternion`,[0,duration],[...bone.quaternion.toArray(),...bone.quaternion.toArray()]));
  tracks.push(new THREE.VectorKeyframeTrack(`${bone.name}.position`,[0,duration],[...bone.position.toArray(),...bone.position.toArray()]));
  tracks.push(new THREE.VectorKeyframeTrack(`${bone.name}.scale`,[0,duration],[...bone.scale.toArray(),...bone.scale.toArray()]));
 }
 // Clear stale recorded facial weights, without inventing a conversion from
 // SMPL-X's learned expression basis to this avatar's action-unit morphs.
 working.traverse(node=>{
  if(!(node instanceof THREE.Mesh)||!node.morphTargetInfluences)return;
  node.morphTargetInfluences.forEach((_,index)=>tracks.push(new THREE.NumberKeyframeTrack(`${node.name}.morphTargetInfluences[${index}]`,[0,duration],[0,0])));
 });
 const clip=new THREE.AnimationClip(motion.name||'MaDiS ASL generated motion',duration,tracks).optimize();
 return Object.assign(clip,{retargeting:{method:'smplx-axis-angle-delta-to-galtis-bind',fps:motion.fps,frames:frames.length,trackedJoints:JOINTS.length,limitations:[...NEURAL_RETARGET_LIMITATIONS]}});
}
