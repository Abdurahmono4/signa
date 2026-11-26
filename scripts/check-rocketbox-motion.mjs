import fs from 'node:fs';
import assert from 'node:assert/strict';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {naturalModel} from './check-natural-avatar.mjs';
const root=new URL('../',import.meta.url);
const three=new URL('frontend/node_modules/three/build/three.module.js',root).href;
const skeleton=new URL('frontend/node_modules/three/examples/jsm/utils/SkeletonUtils.js',root).href;
function compile(path,replacements){let code=fs.readFileSync(new URL(path,root),'utf8');for(const [a,b] of replacements)code=code.replaceAll(a,b);return 'data:text/javascript;base64,'+Buffer.from(ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText).toString('base64')}
const neural=compile('frontend/src/neuralMotion.ts',[["'three'",JSON.stringify(three)],["'three/examples/jsm/utils/SkeletonUtils.js'",JSON.stringify(skeleton)]]);
const rocket=compile('frontend/src/rocketboxMotion.ts',[["'three'",JSON.stringify(three)],["'./neuralMotion'",JSON.stringify(neural)]]);
const {createRocketboxClip,createRocketboxIdleClip,ROCKETBOX_TARGETS}=await import(rocket);
const {AvatarPlayback}=await import(compile('frontend/src/avatarPlayback.ts',[["'three'",JSON.stringify(three)]]));
assert.equal(Object.keys(ROCKETBOX_TARGETS).length,41);
const index=JSON.parse(fs.readFileSync(new URL('storage/neural/10afdbda8fc3fb38eb33b374a6157440/motion/index.json',root)));
const motion=JSON.parse(fs.readFileSync(index.motions[0].motion_json));
// Synthetic rotations validate geometry only; they are not sign records.
const calibrationMixer=new THREE.AnimationMixer(naturalModel);
const bindPositions=new Map(),bindLengths=new Map();
naturalModel.updateMatrixWorld(true);
naturalModel.traverse(n=>{if(n.isBone){bindPositions.set(n.name,n.position.clone());if(n.parent?.isBone)bindLengths.set(n.name,n.getWorldPosition(new THREE.Vector3()).distanceTo(n.parent.getWorldPosition(new THREE.Vector3())))}});
const neutral=createRocketboxClip(naturalModel,{fps:24,frames:[Array(133).fill(0)]});
calibrationMixer.clipAction(neutral).play();calibrationMixer.update(0);naturalModel.updateMatrixWorld(true);
const pos=name=>naturalModel.getObjectByName(name).getWorldPosition(new THREE.Vector3());
for(const side of ['L','R']){
 const p=`Bip01_${side}_`,axis=new THREE.Vector3(side==='L'?1:-1,0,0);
 for(const [a,b] of [['UpperArm','Forearm'],['Forearm','Hand'],['Hand','Finger2']]){
  const direction=pos(p+b).sub(pos(p+a)).normalize();
  assert.ok(direction.dot(axis)>.999,`${side} ${a} must match the extended-arm reference`);
 }
}
calibrationMixer.stopAllAction();calibrationMixer.uncacheRoot(naturalModel);
const raised=Array(133).fill(0);raised[20]=.65;raised[23]=-.65;
const elbowClip=createRocketboxClip(naturalModel,{fps:24,frames:[raised]});
calibrationMixer.clipAction(elbowClip).play();calibrationMixer.update(0);naturalModel.updateMatrixWorld(true);
for(const side of ['L','R']){
 assert.ok(pos(`Bip01_${side}_Hand`).y>pos(`Bip01_${side}_Forearm`).y+.08,`${side} elbow rotation must lift its wrist`);
}
calibrationMixer.stopAllAction();calibrationMixer.uncacheRoot(naturalModel);
// Independent FK control: turn the shoulder out of the image plane, then
// bend the elbow in its local plane. Swapping the rotations changes the wrist.
let maxWristError=0;
for(const side of ['L','R']){
 const frame=Array(133).fill(0),left=side==='L';
 const yaw=left?.43:-.37,bend=left?.82:-.71;
 frame[left?13:16]=yaw;frame[left?20:23]=bend;
 const control=createRocketboxClip(naturalModel,{fps:24,frames:[frame]});
 calibrationMixer.clipAction(control).play();calibrationMixer.update(0);naturalModel.updateMatrixWorld(true);
 for(const arm of ['L','R']){
  const prefix='Bip01_'+arm+'_',sign=arm==='L'?1:-1;
  const u=bindLengths.get(prefix+'Forearm'),v=bindLengths.get(prefix+'Hand');
  const y=arm===side?yaw:0,z=arm===side?bend:0;
  const reach=sign*(u+v*Math.cos(z));
  const expected=new THREE.Vector3(reach*Math.cos(y),sign*v*Math.sin(z),-reach*Math.sin(y));
  const actual=pos(prefix+'Hand').sub(pos(prefix+'UpperArm'));
  const error=actual.distanceTo(expected);
  assert.ok(error<.001,arm+' wrist FK error in meters: '+error);
  maxWristError=Math.max(maxWristError,error);
 }
 calibrationMixer.stopAllAction();calibrationMixer.uncacheRoot(naturalModel);
}
console.log('Shoulder/elbow FK maximum wrist error (mm):',maxWristError*1000);
const clip=createRocketboxClip(naturalModel,motion);const mixer=new THREE.AnimationMixer(naturalModel);
const playback=new AvatarPlayback(mixer),poses=[];
const rest=[];naturalModel.traverse(node=>{if(node.isBone)rest.push(...node.quaternion.toArray())});
for(const time of Array.from({length:28},(_,i)=>i/motion.fps)){
 playback.sample(clip,time);naturalModel.updateMatrixWorld(true);
 const pose=[];naturalModel.traverse(node=>{assert.ok(node.matrixWorld.elements.every(Number.isFinite));if(node.isBone){
  pose.push(...node.quaternion.toArray());
  assert.ok(node.position.distanceTo(bindPositions.get(node.name))<1e-7,`${node.name} local offset must remain intact`);
  if(bindLengths.has(node.name))assert.ok(Math.abs(node.getWorldPosition(new THREE.Vector3()).distanceTo(node.parent.getWorldPosition(new THREE.Vector3()))-bindLengths.get(node.name))<1e-5,`${node.name} must preserve bone length`);
 }});poses.push(pose);
 const head=naturalModel.getObjectByName('Bip01_Head').getWorldPosition(new THREE.Vector3());
 assert.ok(head.y>1.3&&head.y<1.8,'Head must remain at human height after retargeting');
 const pelvis=naturalModel.getObjectByName('Bip01_Pelvis').getWorldPosition(new THREE.Vector3());
 assert.ok(pelvis.y>.85&&pelvis.y<1.05,'Pelvis translation must not be applied twice');
 naturalModel.traverse(n=>{if(n.isSkinnedMesh)n.computeBoundingBox()});
 const box=new THREE.Box3().setFromObject(naturalModel);const height=box.max.y-box.min.y;
 assert.ok(height>.8&&height<3,`Retarget must preserve meter-scale body; got ${height}`);
}
assert.notDeepEqual(poses[0],poses[1]);
playback.sample(null);
const restored=[];naturalModel.traverse(node=>{if(node.isBone)restored.push(...node.quaternion.toArray())});
assert.deepEqual(restored,rest,'A gap must restore the original rig, including fingers');
playback.sample(clip,clip.duration*.5);
const replay=[];naturalModel.traverse(node=>{if(node.isBone)replay.push(...node.quaternion.toArray())});
assert.deepEqual(replay,poses[14],'Seeking after a gap must reproduce the same pose');
playback.dispose();
const idle=createRocketboxIdleClip(naturalModel),restPlayer=new AvatarPlayback(mixer,idle);
const bonePose=()=>{const values=[];naturalModel.traverse(n=>{if(n.isBone)values.push(...n.quaternion.toArray())});return values};
restPlayer.sample(null);naturalModel.updateMatrixWorld(true);
const relaxed=bonePose();
for(const side of ['L','R']){
 const shoulder=pos(`Bip01_${side}_UpperArm`),hand=pos(`Bip01_${side}_Hand`);
 assert.ok(hand.y<shoulder.y-.35,`${side} resting hand should be lowered`);
 assert.ok(Math.abs(hand.x-shoulder.x)<.18,`${side} resting hand should stay near the torso`);
}
restPlayer.sample(clip,clip.duration*.5);
assert.deepEqual(bonePose(),poses[14],'Idle must not change active sign frames');
restPlayer.transition({clip,time:clip.duration*.5},null,.5);
const halfway=bonePose();assert.notDeepEqual(halfway,relaxed);assert.notDeepEqual(halfway,poses[14]);
restPlayer.transition({clip,time:clip.duration*.5},null,1);
assert.deepEqual(bonePose(),relaxed,'Completed transition must match relaxed rest');
restPlayer.sample(clip,clip.duration*.5);assert.deepEqual(bonePose(),poses[14],'Seeking from rest must preserve the source pose');
restPlayer.dispose();assert.deepEqual(bonePose(),rest,'Disposal must restore the asset bind pose');
assert.ok(clip.tracks.some(t=>t.name==='Bip01_L_Finger11.quaternion'));
assert.ok(clip.tracks.every(t=>Array.from(t.values).every(Number.isFinite)));
console.log(JSON.stringify({motionFrames:(motion.frames||motion.features).length,tracks:clip.tracks.length,posesChanged:true,relaxedRest:true,activeSignFramesPreserved:true,source:'existing MaDiS output',visualValidation:false,linguisticValidation:false}));
