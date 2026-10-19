import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {createInterpreter} from '../frontend/src/interpreter.ts';
import {AVATAR_REST_TIME,sampleAvatarMotion} from '../frontend/src/avatarMotion.ts';

const assets=new URL('../frontend/public/avatar/',import.meta.url);
const bytes=fs.readFileSync(new URL('galtis.glb',assets));
const source=(await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'')).scene;
const model=createInterpreter(source),manifest=JSON.parse(fs.readFileSync(new URL('corpus.json',assets)));
const body=model.getObjectByName('GaltisBody'),handVertices=[];
const skinIndices=body.geometry.getAttribute('skinIndex'),skinWeights=body.geometry.getAttribute('skinWeight');
for(let vertex=0;vertex<skinIndices.count;vertex++){
 let handWeight=0;
 for(let component=0;component<4;component++){
  const bone=body.skeleton.bones[skinIndices.getComponent(vertex,component)];
  if(/^(hand|thumb|index|middle|ring|pinky)_/.test(bone?.name||''))handWeight+=skinWeights.getComponent(vertex,component);
 }
 if(handWeight>.9)handVertices.push(vertex);
}
assert.ok(handVertices.length>100,'Regression must observe rendered hand surface vertices');
const sampleVertices=handVertices.filter((_,index)=>index%Math.max(1,Math.floor(handVertices.length/40))===0);
const surface=()=>{
 model.updateMatrixWorld(true);body.skeleton.update();
 return sampleVertices.map(index=>body.getVertexPosition(index,new THREE.Vector3()).applyMatrix4(body.matrixWorld));
};
let moved=0;
for(const {id} of manifest){
 const clip=THREE.AnimationClip.parse(JSON.parse(fs.readFileSync(new URL(`${id}.motion.json`,assets))));
 const mixer=new THREE.AnimationMixer(model),action=mixer.clipAction(clip);
 action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;
 sampleAvatarMotion(mixer,action,AVATAR_REST_TIME);const rest=surface();
 let maxMovement=0;
 for(const time of [.2,.4,.6,.8].map(fraction=>clip.duration*fraction)){
  sampleAvatarMotion(mixer,action,time);const current=surface();
  for(let index=0;index<current.length;index++)maxMovement=Math.max(maxMovement,current[index].distanceTo(rest[index]));
 }
 assert.ok(maxMovement>1,`${id}: captured sign must change the skinned hand surface by more than 1 cm`);moved++;
 const seekTime=Math.max(AVATAR_REST_TIME,clip.duration*.35);
 sampleAvatarMotion(mixer,action,seekTime);const expected=surface();
 sampleAvatarMotion(mixer,action,clip.duration);surface();
 sampleAvatarMotion(mixer,action,seekTime);const backwards=surface();
 for(let index=0;index<expected.length;index++)assert.ok(expected[index].distanceTo(backwards[index])<1e-7,`${id}: backward seek must repaint the same hand surface`);
 sampleAvatarMotion(mixer,action,0);const replay=surface();
 for(let index=0;index<rest.length;index++)assert.ok(rest[index].distanceTo(replay[index])<1e-7,`${id}: replay must reset the recorded pose`);
 sampleAvatarMotion(mixer,action,clip.duration*.5,false);const idle=surface();
 for(let index=0;index<rest.length;index++)assert.ok(rest[index].distanceTo(idle[index])<1e-7,`${id}: idle must use recorded rest instead of calibration T-pose`);
 mixer.stopAllAction();mixer.uncacheRoot(model);
}
console.log(`PASS: ${moved} captured clips change actual skinned hand vertices; backward seek, replay, idle rest and end-clamped sampling remain deterministic.`);
