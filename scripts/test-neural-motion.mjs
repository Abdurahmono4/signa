import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {clone} from '../frontend/node_modules/three/examples/jsm/utils/SkeletonUtils.js';
import {createNeuralClip,neuralSourceRotations,NEURAL_JOINT_LAYOUT,validateNeuralMotion,neuralMotionAssetUrl} from '../frontend/src/neuralMotion.ts';
import {sampleAvatarMotion} from '../frontend/src/avatarMotion.ts';

const bytes=fs.readFileSync(new URL('../frontend/public/avatar/galtis.glb',import.meta.url));
const original=(await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'')).scene;
original.updateMatrixWorld(true);
const snapshot=new Map();original.traverse(node=>snapshot.set(node.uuid,[...node.position.toArray(),...node.quaternion.toArray(),...node.scale.toArray()]));
const zero=()=>Array(133).fill(0),identity=createNeuralClip(original,{frames:[zero(),zero()],fps:24});
assert.equal(identity.duration,2/24);assert.equal(identity.retargeting.trackedJoints,40);
assert.ok(identity.retargeting.limitations.some(text=>text.includes('hand-mean')));
assert.ok(identity.retargeting.limitations.some(text=>text.includes('expression')));
assert.equal(new Set(identity.tracks.map(track=>track.name)).size,identity.tracks.length,'No ambiguous duplicate binding lanes');
original.traverse(node=>assert.deepEqual([...node.position.toArray(),...node.quaternion.toArray(),...node.scale.toArray()],snapshot.get(node.uuid),'Conversion never mutates the cached avatar'));
const errors=[],oldError=console.error;console.error=(...parts)=>errors.push(parts.join(' '));
function sample(clip,time=0){const model=clone(original),mixer=new THREE.AnimationMixer(model),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();mixer.setTime(time);model.updateMatrixWorld(true);return{model,mixer}}
try{
 const {model:bind}=sample(identity,.01);
 let checkedBones=0;
 bind.traverse(object=>{
  if(!object.isSkinnedMesh)return;
  object.skeleton.bones.forEach((bone,index)=>{
   let root=bone;while(root.parent?.isBone)root=root.parent;
   const expected=new THREE.Matrix4().multiplyMatrices(root.parent.matrixWorld,object.skeleton.boneInverses[index].clone().invert());
   assert.ok(bone.matrixWorld.elements.every((value,i)=>Math.abs(value-expected.elements[i])<3e-4),`Identity must restore true inverse-bind pose: ${bone.name}`);
   checkedBones++;
  });
 });
 assert.equal(checkedBones,782,'Both head and body skeletons are restored');
 const leftRest=bind.getObjectByName('hand_l').getWorldQuaternion(new THREE.Quaternion()).normalize();
 const rightRest=bind.getObjectByName('hand_r').getWorldQuaternion(new THREE.Quaternion()).normalize();
 function rotationFixture(offset,axis='z'){
  const frame=zero();frame[offset+{x:0,y:1,z:2}[axis]]=Math.PI/4;
  return createNeuralClip(original,{frames:[zero(),frame],fps:24});
 }
 const leftClip=rotationFixture(18),{model:left}=sample(leftClip,1/24);
 const sourceLeft=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),Math.PI/4);
 assert.ok(left.getObjectByName('hand_l').getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(sourceLeft.clone().multiply(leftRest))<1e-5,'Left elbow rotation reaches the left wrist in source world axes');
 assert.ok(left.getObjectByName('hand_r').getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(rightRest)<1e-5,'Left elbow does not drive the right hand');
 const rightClip=rotationFixture(21,'x'),{model:right}=sample(rightClip,1/24);
 const sourceRight=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),Math.PI/4);
 assert.ok(right.getObjectByName('hand_r').getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(sourceRight.clone().multiply(rightRest))<1e-5,'Right elbow rotation reaches the right wrist');
 assert.ok(right.getObjectByName('hand_l').getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(leftRest)<1e-5);

 const chained=zero();chained[5]=.2;chained[12]=.3;chained[19]=-.4;chained[26]=.15;
 const {model:chain}=sample(createNeuralClip(original,{features:[chained],fps:24,format:'signa-madis-133-v1'}),.01);
 const qz=angle=>new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),angle);
 const qx=angle=>new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),angle);
 const qy=angle=>new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),angle);
 const expectedChain=qz(.2).multiply(qx(.3)).multiply(qy(-.4)).multiply(qz(.15)).multiply(leftRest).normalize();
 assert.ok(chain.getObjectByName('hand_l').getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(expectedChain)<1e-5,'Noncommuting collar→shoulder→elbow→wrist rotations preserve source order');
 assert.ok(chain.getObjectByName('head').getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(bind.getObjectByName('head').getWorldQuaternion(new THREE.Quaternion()).normalize())<1e-5,'Collar motion does not incorrectly enter the neck/head chain');

 for(const [offset,name,other] of [[30,'index_01_l','index_01_r'],[48,'pinky_01_l','ring_01_l'],[57,'ring_01_l','pinky_01_l'],[66,'thumb_01_l','thumb_01_r'],[75,'index_01_r','index_01_l'],[111,'thumb_01_r','thumb_01_l']]){
  const {model}=sample(rotationFixture(offset,'x'),1/24);
  assert.ok(model.getObjectByName(name).getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(bind.getObjectByName(name).getWorldQuaternion(new THREE.Quaternion()).normalize())>.7,`Correct hand order: ${name}`);
  assert.ok(model.getObjectByName(other).getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(bind.getObjectByName(other).getWorldQuaternion(new THREE.Quaternion()).normalize())<1e-5,`No hand/finger swap into ${other}`);
 }
 // Check all three source axes on every actual finger target, including both
 // thumbs. Testing merely non-zero movement cannot detect an axis swap.
 for(const joint of NEURAL_JOINT_LAYOUT.filter(joint=>joint.offset>=30)){
  const axes=[new THREE.Vector3(1,0,0),new THREE.Vector3(0,1,0),new THREE.Vector3(0,0,1)];
  const fixtures=axes.map((_,axis)=>{const frame=zero();frame[joint.offset+axis]=.4;return frame});
  const clip=createNeuralClip(original,{frames:fixtures,fps:24});
  const rest=bind.getObjectByName(joint.target).getWorldQuaternion(new THREE.Quaternion()).normalize();
  for(let axis=0;axis<3;axis++){
   const {model}=sample(clip,axis/24),expected=new THREE.Quaternion().setFromAxisAngle(axes[axis],.4).multiply(rest).normalize();
   const actual=model.getObjectByName(joint.target).getWorldQuaternion(new THREE.Quaternion()).normalize();
   assert.ok(actual.angleTo(expected)<1e-5,`${joint.target}: preserve source axis ${axis} without mirroring/swapping`);
  }
 }
 const face=zero();face[120]=.6;for(let i=123;i<133;i++)face[i]=i-125;
 const faceOnly=createNeuralClip(original,{frames:[face],fps:24});
 const {model:faceModel}=sample(faceOnly,.01);
 assert.ok(faceModel.getObjectByName('GaltisHead').morphTargetInfluences.every(value=>value===0),'Unsupported expression basis is not fabricated into arbitrary morphs');
 assert.ok(faceModel.getObjectByName('head').getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(bind.getObjectByName('head').getWorldQuaternion(new THREE.Quaternion()).normalize())<1e-5,'Jaw coefficients are not mislabeled as head rotation');

 const varied=Array.from({length:16},(_,frame)=>Array.from({length:133},(_,i)=>Math.sin(frame*.27+i*.13)*.25));
 const variedClip=createNeuralClip(original,{frames:varied,fps:24});
 assert.ok(variedClip.tracks.every(track=>Array.from(track.times).every(Number.isFinite)&&Array.from(track.values).every(Number.isFinite)));
 for(const time of [0,.125,.25,.5,variedClip.duration]){
  const {model}=sample(variedClip,time);model.traverse(node=>assert.ok(node.matrixWorld.elements.every(Number.isFinite),`Finite generated transform: ${node.name}`));
  assert.ok(model.getObjectByName('pelvis').getWorldPosition(new THREE.Vector3()).distanceTo(bind.getObjectByName('pelvis').getWorldPosition(new THREE.Vector3()))<1e-5,'No invented root translation');
 }
 assert.deepEqual(neuralSourceRotations(zero()).get('left_index1').toArray(),[0,0,0,1]);
 assert.equal(NEURAL_JOINT_LAYOUT.find(joint=>joint.key==='right_thumb3').offset,117);
 assert.throws(()=>createNeuralClip(original,{frames:[zero()],fps:24,normalized:true}),/Denormalize/);
 assert.throws(()=>createNeuralClip(original,{frames:[Array(132).fill(0)],fps:24}),/133 finite/);
 const invalid=zero();invalid[30]=NaN;
 assert.throws(()=>createNeuralClip(original,{frames:[invalid],fps:24}),/133 finite/);
 assert.throws(()=>createNeuralClip(original,{frames:[zero()],fps:0}),/FPS/);
 assert.throws(()=>createNeuralClip(original,{frames:[zero()],fps:24,format:'rotation6d'}),/Unsupported/);
 assert.equal(neuralMotionAssetUrl('/api/jobs/123/neural-motion'),'/api/jobs/123/neural-motion');
 for(const url of ['https://example.com/motion.json','//example.com/motion.json','/api/../private','/avatar/hello.motion.json','/api/a\\b'])assert.throws(()=>neuralMotionAssetUrl(url),/relative/);
 assert.equal(validateNeuralMotion({features:[zero()],fps:24,format:'signa-madis-133-v1'}).length,1);
 const samplerModel=clone(original),samplerMixer=new THREE.AnimationMixer(samplerModel),samplerAction=samplerMixer.clipAction(leftClip);
 samplerAction.setLoop(THREE.LoopOnce,1);samplerAction.clampWhenFinished=true;
 assert.equal(sampleAvatarMotion(samplerMixer,samplerAction,0,true,0),0,'Neural frame zero is real data, not a mocap calibration frame');
 const first=samplerModel.getObjectByName('hand_l').getWorldQuaternion(new THREE.Quaternion()).normalize();
 sampleAvatarMotion(samplerMixer,samplerAction,1/24,true,0);samplerModel.updateMatrixWorld(true);
 assert.ok(samplerModel.getObjectByName('hand_l').getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(first)>.7);
 sampleAvatarMotion(samplerMixer,samplerAction,leftClip.duration,true,0);samplerModel.updateMatrixWorld(true);
 sampleAvatarMotion(samplerMixer,samplerAction,0,true,0);samplerModel.updateMatrixWorld(true);
 assert.ok(samplerModel.getObjectByName('hand_l').getWorldQuaternion(new THREE.Quaternion()).normalize().angleTo(first)<1e-5,'Neural replay after a clamped finish returns to frame zero');
 assert.deepEqual(errors,[],'All output animation tracks bind without errors');
 console.log(`PASS: ${checkedBones} true-bind skeleton entries, 40 joint axis-angle layout, left/right/finger isolation, world-axis composition, finite generated frames, unsupported-face handling, input validation and source immutability. Retarget approximation, not linguistic validation.`);
}finally{console.error=oldError}
