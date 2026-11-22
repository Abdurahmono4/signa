// Regression: transfer the actual jaw rotation, without perturbing signing.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {clone} from '../frontend/node_modules/three/examples/jsm/utils/SkeletonUtils.js';
import {naturalModel} from './check-natural-avatar.mjs';
const root=new URL('../',import.meta.url),three=new URL('frontend/node_modules/three/build/three.module.js',root).href;
function compile(file,subs={}){let s=fs.readFileSync(new URL('frontend/src/'+file,root),'utf8');for(const [a,b] of Object.entries(subs))s=s.replaceAll("'"+a+"'",JSON.stringify(b));return 'data:text/javascript;base64,'+Buffer.from(ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText).toString('base64')}
const neural=compile('neuralMotion.ts',{three,'three/examples/jsm/utils/SkeletonUtils.js':new URL('frontend/node_modules/three/examples/jsm/utils/SkeletonUtils.js',root).href});
const {createNeuralClip}=await import(neural);
const {createRocketboxClip,createRocketboxIdleClip,ROCKETBOX_TARGETS,rocketboxReference}=await import(compile('rocketboxMotion.ts',{three,'./neuralMotion':neural}));
const {AvatarPlayback}=await import(compile('avatarPlayback.ts',{three}));
const model=clone(naturalModel),player=new AvatarPlayback(new THREE.AnimationMixer(model),createRocketboxIdleClip(naturalModel));
const position=name=>model.getObjectByName(name).getWorldPosition(new THREE.Vector3());
const zero=Array(133).fill(0);
player.sample(createRocketboxClip(naturalModel,{fps:24,frames:[zero]}),0);model.updateMatrixWorld(true);
// Use actual landmark positions, independent of quaternion track names.
function palmGeometry(side){
 const point=suffix=>position('Bip01_'+side+'_'+suffix);
 const along=point('Finger2').sub(point('Hand')).normalize();
 const across=point('Finger1').sub(point('Finger4'));
 across.addScaledVector(along,-across.dot(along)).normalize();
 const normal=along.clone().cross(across).multiplyScalar(side==='L'?1:-1).normalize();
 const thumb=point('Finger0').sub(point('Hand')).dot(across);
 return {normal,thumb};
}
const palms={};
for(const [side,other,offset] of [['L','R',24],['R','L',27]]){
 player.sample(createRocketboxClip(naturalModel,{fps:24,frames:[zero]}),0);
 const before=palmGeometry(side),stationary=palmGeometry(other);
 assert.ok(before.thumb>0,'Thumb base must be on the index side');
 const twist=zero.slice();twist[offset]=Math.PI/3;
 player.sample(createRocketboxClip(naturalModel,{fps:24,frames:[twist]}),0);
 const after=palmGeometry(side);
 const expected=before.normal.clone().applyAxisAngle(new THREE.Vector3(1,0,0),Math.PI/3);
 assert.ok(after.normal.angleTo(expected)<1e-4,'Palm plane must follow wrist roll');
 assert.ok(palmGeometry(other).normal.angleTo(stationary.normal)<1e-4,'Opposite wrist moved');
 palms[side]={neutralTiltFromDownDegrees:THREE.MathUtils.radToDeg(before.normal.angleTo(new THREE.Vector3(0,-1,0))),thumbOffsetMm:before.thumb*1000,rollDegrees:THREE.MathUtils.radToDeg(before.normal.angleTo(after.normal))};
}
player.sample(createRocketboxClip(naturalModel,{fps:24,frames:[zero]}),0);
const closed=position('Bip01_MBottomLip'),upper=position('Bip01_MUpperLip'),pivot=position('Bip01_MJaw');
const open=zero.slice();open[120]=.15;
player.sample(createRocketboxClip(naturalModel,{fps:24,frames:[open]}),0);model.updateMatrixWorld(true);
assert.ok(position('Bip01_MBottomLip').y<closed.y-.001,'Positive source pitch must lower lower lip');
assert.ok(position('Bip01_MUpperLip').distanceTo(upper)<1e-7,'Upper lip must not rotate with the jaw');
assert.ok(position('Bip01_MJaw').distanceTo(pivot)<1e-7,'Jaw pivot must not translate');
const legacyTargets={...ROCKETBOX_TARGETS};delete legacyTargets.jaw;
let frames=0,changing=0;
// Recover each finger rotation from the played skeleton, relative to its
// moving parent. Compare with the original MaDiS channel at the same frame.
const reference=rocketboxReference(naturalModel);
const fingerSegments=[];
for(const [side,start] of [['L',30],['R',75]]){
 for(const [finger,rigIndex] of [1,2,4,3,0].entries()){
  let parent=model.getObjectByName('Bip01_'+side+'_Hand');
  for(let segment=0;segment<3;segment++){
   const bone=model.getObjectByName('Bip01_'+side+'_Finger'+rigIndex+(segment||''));
   fingerSegments.push({bone,parent,offset:start+finger*9+segment*3});
   parent=bone;
  }
 }
}
const inverseRest=new Map([...reference].map(([name,q])=>[name,q.clone().invert()]));
function delta(bone){
 return bone.getWorldQuaternion(new THREE.Quaternion()).multiply(inverseRest.get(bone.name)).normalize();
}
let checkedFingerRotations=0,maxFingerErrorDegrees=0;
for(let i=0;i<10;i++){
 const motion=JSON.parse(fs.readFileSync(new URL('docs/asl-comparison-10/model/'+String(i).padStart(4,'0')+'/motion.json',root)));
 const old=createNeuralClip(naturalModel,motion,legacyTargets,true,rocketboxReference(naturalModel)),next=createRocketboxClip(naturalModel,motion);
 for(const track of old.tracks){const replacement=next.tracks.find(t=>t.name===track.name);assert.ok(replacement);assert.deepEqual(replacement.values,track.values,'Existing hand/head tracks must remain bit-identical')}
 const track=next.tracks.find(t=>t.name==='Bip01_MJaw.quaternion');assert.ok(track);
 const jawPoses=[];
 for(let k=0;k<motion.frame_count;k++){
  player.sample(next,k/motion.fps);model.updateMatrixWorld(true);
  model.traverse(n=>assert.ok(n.matrixWorld.elements.every(Number.isFinite)));
  const frame=(motion.frames||motion.features)[k];
  for(const {bone,parent,offset} of fingerSegments){
   const axis=new THREE.Vector3().fromArray(frame,offset);
   const expected=new THREE.Quaternion().setFromAxisAngle(axis.clone().normalize(),axis.length());
   const played=delta(parent).invert().multiply(delta(bone)).normalize();
   const degrees=THREE.MathUtils.radToDeg(played.angleTo(expected));
   assert.ok(degrees<0.01,`Finger rotation drift: clip ${i} frame ${k} ${bone.name} ${degrees} degrees`);
   maxFingerErrorDegrees=Math.max(maxFingerErrorDegrees,degrees);
   checkedFingerRotations++;
  }
  jawPoses.push(model.getObjectByName('Bip01_MJaw').quaternion.toArray());frames++;
 }
 assert.ok(jawPoses.some(q=>q.some((v,k)=>Math.abs(v-jawPoses[0][k])>1e-6)));changing++;
 player.sample(null);model.updateMatrixWorld(true);
 const rest=model.getObjectByName('Bip01_MJaw').quaternion;
 assert.ok(rest.angleTo(naturalModel.getObjectByName('Bip01_MJaw').quaternion)<1e-6,'Idle must close the jaw');
}
player.dispose();
console.log(JSON.stringify({clips:10,frames,palms,checkedFingerRotations,maxFingerErrorDegrees,changingJawClips:changing,positivePitchOpensDown:true,upperLipPreserved:true,existingSigningTracksBitIdentical:true,linguisticValidation:false}));
