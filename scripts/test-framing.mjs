import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {createInterpreter} from '../frontend/src/interpreter.ts';
import {INTERPRETER_FOV,INTERPRETER_TARGET_Y,interpreterCameraDistance} from '../frontend/src/framing.ts';

const assets=new URL('../frontend/public/avatar/',import.meta.url);
const bytes=fs.readFileSync(new URL('galtis.glb',assets));
const source=(await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'')).scene;
const model=createInterpreter(source),head=model.getObjectByName('GaltisHead');
const headStyle=model.getObjectByName('SignaInterpreterHeadStyle');
const decorations=[];headStyle.traverse(object=>{if(object.isMesh){object.geometry.computeBoundingBox();decorations.push(object)}});
const manifest=JSON.parse(fs.readFileSync(new URL('corpus.json',assets)));
const points=[];
for(const {id} of manifest){
 const clip=THREE.AnimationClip.parse(JSON.parse(fs.readFileSync(new URL(`${id}.motion.json`,assets))));
 const mixer=new THREE.AnimationMixer(model),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;
 for(let frame=0;frame<=60;frame++){
  action.reset().play();mixer.setTime(Math.max(1/30,clip.duration*frame/60));model.updateMatrixWorld(true);
  for(const side of ['l','r'])for(const joint of ['hand','thumb_03','index_03','middle_03','ring_03','pinky_03']){
   const name=`${joint}_${side}_1`,bone=model.getObjectByName(name);assert.ok(bone,`Missing ${name}`);
   const point=bone.getWorldPosition(new THREE.Vector3()).multiplyScalar(.01);
   // Joint centres alone miss the fingertip surface. Test a 5 cm margin cube.
   for(const x of [-.05,.05])for(const y of [-.05,.05])for(const z of [-.05,.05])points.push({id,frame,name,point:point.clone().add(new THREE.Vector3(x,y,z))});
  }
  for(let vertex=0;vertex<head.geometry.attributes.position.count;vertex+=128){
   points.push({id,frame,name:'face',point:head.getVertexPosition(vertex,new THREE.Vector3()).applyMatrix4(head.matrixWorld).multiplyScalar(.01)});
  }
  for(const object of decorations){
   const box=object.geometry.boundingBox;
   for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){
    points.push({id,frame,name:object.name,point:new THREE.Vector3(x,y,z).applyMatrix4(object.matrixWorld).multiplyScalar(.01)});
   }
  }
 }
 mixer.stopAllAction();mixer.uncacheRoot(model);
}
const aspects=[160/285,160/220,200/340,240/340,1,1.5,2.5],projected=new THREE.Vector3();
let worstX=0,worstY=0;
for(const aspect of aspects)for(const angle of [-.65,0,.65]){
 const camera=new THREE.PerspectiveCamera(INTERPRETER_FOV,aspect,.1,100);
 camera.position.set(0,INTERPRETER_TARGET_Y,interpreterCameraDistance(aspect,angle));camera.lookAt(0,INTERPRETER_TARGET_Y,0);camera.updateMatrixWorld(true);
 const rotation=new THREE.Matrix4().makeRotationY(angle);
 for(const {id,frame,name,point} of points){
  projected.copy(point).applyMatrix4(rotation).project(camera);
  worstX=Math.max(worstX,Math.abs(projected.x));worstY=Math.max(worstY,Math.abs(projected.y));
  assert.ok(Math.abs(projected.x)<=.91,`${id} frame${frame} ${name} outside horizontal signing area at aspect ${aspect}, angle ${angle}: ${projected.x}`);
  assert.ok(Math.abs(projected.y)<=.88,`${id} frame${frame} ${name} outside vertical signing area at aspect ${aspect}, angle ${angle}: ${projected.y}`);
  assert.ok(projected.z>-1&&projected.z<1,`${id}: source hand/head behind camera or clip plane`);
 }
}
for(const invalid of [0,-1,NaN,Infinity])assert.ok(Number.isFinite(interpreterCameraDistance(invalid)));
assert.ok(interpreterCameraDistance(.56)>interpreterCameraDistance(1),'A portrait panel must move the camera back to fit both hands');
console.log(`PASS: ${manifest.length} actual clips × 61 sampled poses; hand/finger surfaces, face and hair fit ${aspects.length} portrait/desktop aspects and 3 view angles. Worst projected extent x=${worstX.toFixed(3)}, y=${worstY.toFixed(3)}.`);
