import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {createInterpreter} from '../frontend/src/interpreter.ts';
import {createNeuralClip,validateNeuralMotion} from '../frontend/src/neuralMotion.ts';
import {sampleNeuralSigningEnvelope} from '../frontend/src/neuralFraming.ts';
import {INTERPRETER_FOV,interpreterCameraDistance,neuralInterpreterCamera} from '../frontend/src/framing.ts';

const directory=process.argv[2];assert.ok(directory,'Pass the directory of actual generated motion chunks.');
const files=fs.readdirSync(directory,{withFileTypes:true}).filter(entry=>entry.isDirectory()).map(entry=>path.join(directory,entry.name,'motion.json')).filter(file=>fs.existsSync(file));
assert.ok(files.length,'Actual generated motion files are required.');
const motions=files.map(file=>JSON.parse(fs.readFileSync(file,'utf8')));motions.forEach(motion=>assert.equal(motion.format,'signa-madis-133-v1'));
const bytes=fs.readFileSync(new URL('../frontend/public/avatar/galtis.glb',import.meta.url));
const model=createInterpreter((await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'')).scene);
const before=model.getObjectByName('head').matrixWorld.toArray();
const envelope=sampleNeuralSigningEnvelope(model,motions);assert.deepEqual(model.getObjectByName('head').matrixWorld.toArray(),before,'Camera sampling must not modify the visible rig.');
// Reproduce the browser failure: R3F previously set the primitive's scale to
// .01 before camera sampling. Offline asset-only checks missed the second
// centimetre conversion and incorrectly passed while the camera aimed at feet.
model.scale.setScalar(.01);model.updateMatrixWorld(true);
const mountedBefore=model.getObjectByName('head').matrixWorld.toArray();
assert.deepEqual(sampleNeuralSigningEnvelope(model,motions),envelope,'An already displayed .01 root must produce the same metre envelope as the native asset.');
assert.deepEqual(model.scale.toArray(),[.01,.01,.01],'Sampling must not rescale the visible avatar.');
assert.deepEqual(model.getObjectByName('head').matrixWorld.toArray(),mountedBefore,'Sampling must not alter mounted world matrices.');
// Match the corrected JSX hierarchy: scale/angle live on a display parent,
// while the animation asset itself keeps its original local coordinates.
model.scale.setScalar(1);
const stage=new THREE.Group();stage.scale.setScalar(.01);stage.rotation.y=.65;stage.add(model);stage.updateMatrixWorld(true);
assert.deepEqual(sampleNeuralSigningEnvelope(model,motions),envelope,'Display parent scale and angle must not enter asset-space camera bounds.');
stage.rotation.y=0;stage.updateMatrixWorld(true);
const points=[],head=model.getObjectByName('GaltisHead'),mixer=new THREE.AnimationMixer(model);let frameCount=0;
const decorations=[];model.getObjectByName('SignaInterpreterHeadStyle').traverse(object=>{if(object.isMesh){object.geometry.computeBoundingBox();decorations.push(object)}});
for(const motion of motions){
 const frames=validateNeuralMotion(motion),clip=createNeuralClip(model,motion),action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;
 for(let frame=0;frame<frames.length;frame++){
  action.reset().play();mixer.setTime(frame/motion.fps);stage.updateMatrixWorld(true);head.skeleton.update();frameCount++;
  for(const side of ['l','r'])for(const joint of ['upperarm','lowerarm','hand','thumb_03','index_03','middle_03','ring_03','pinky_03']){
   const point=model.getObjectByName(`${joint}_${side}_1`).getWorldPosition(new THREE.Vector3());
   for(const x of [-.05,.05])for(const y of [-.05,.05])for(const z of [-.05,.05])points.push(point.clone().add(new THREE.Vector3(x,y,z)));
  }
  for(let vertex=0;vertex<head.geometry.attributes.position.count;vertex+=32)points.push(head.getVertexPosition(vertex,new THREE.Vector3()).applyMatrix4(head.matrixWorld));
  for(const object of decorations){const box=object.geometry.boundingBox;for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z])points.push(new THREE.Vector3(x,y,z).applyMatrix4(object.matrixWorld))}
 }
 mixer.stopAllAction();mixer.uncacheClip(clip);
}
let worstX=0,worstY=0;const projected=new THREE.Vector3(),aspects=[160/285,160/220,200/340,240/340,1,1.5,2.5];
for(const aspect of aspects)for(const angle of [-.65,0,.65]){
 const fit=neuralInterpreterCamera(envelope,aspect,angle),camera=new THREE.PerspectiveCamera(INTERPRETER_FOV,aspect,.1,100);
 camera.position.set(fit.x,fit.targetY,fit.distance);camera.lookAt(fit.x,fit.targetY,0);camera.updateMatrixWorld(true);
 const rotation=new THREE.Matrix4().makeRotationY(angle);
 for(const point of points){
  projected.copy(point).applyMatrix4(rotation).project(camera);worstX=Math.max(worstX,Math.abs(projected.x));worstY=Math.max(worstY,Math.abs(projected.y));
  assert.ok(Math.abs(projected.x)<=.880001&&Math.abs(projected.y)<=.880001&&projected.z>-1&&projected.z<1,'Every actual generated signing surface must fit the stable neural camera.');
 }
}
const fit=neuralInterpreterCamera(envelope,.75),previous=interpreterCameraDistance(.75);
assert.ok(fit.targetY>1.3&&fit.targetY<1.9,'The actual mounted camera must aim at the signing area, not the floor.');
assert.ok(fit.distance<previous*.8,'The actual generated sequence should use a materially closer camera than the captured-corpus envelope.');
for(const invalid of [null,{}, {min:[0,0,0],max:[0,0,0]},{min:[1,0,0],max:[0,1,1]},{min:[NaN,0,0],max:[1,1,1]},{min:[0,0,0],max:[1,1,Infinity]}])assert.throws(()=>neuralInterpreterCamera(invalid,1));
for(const aspect of [0,-1,NaN,Infinity])assert.ok(Number.isFinite(neuralInterpreterCamera(envelope,aspect).distance));
assert.throws(()=>sampleNeuralSigningEnvelope(model,[]));
console.log(JSON.stringify({result:'PASS',actualClips:motions.length,actualFrames:frameCount,envelope,worstX,worstY,aspects:aspects.length,angles:3,neuralDistance:fit.distance,capturedDistance:previous,cameraTargetY:fit.targetY,mountedScaleRegression:true,displayParentRegression:true,visibleRigUnchanged:true}));
