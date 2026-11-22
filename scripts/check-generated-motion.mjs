import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {createNeuralClip,validateNeuralMotion} from '../frontend/src/neuralMotion.ts';
const root=new URL('../',import.meta.url);
const plan=JSON.parse(fs.readFileSync(new URL('storage/neural/10afdbda8fc3fb38eb33b374a6157440/motion/index.json',root)));
const motion=JSON.parse(fs.readFileSync(plan.motions[0].motion_json));
const frames=validateNeuralMotion(motion);
const bytes=fs.readFileSync(new URL('assets/avatars/galtis.glb',root));
const model=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const clip=createNeuralClip(model.scene,motion),mixer=new THREE.AnimationMixer(model.scene),action=mixer.clipAction(clip);const poses=[];
for(const t of [0,clip.duration*.5,clip.duration-.01]){
 action.reset().play();mixer.setTime(t);model.scene.updateMatrixWorld(true);let pose=[];
 model.scene.traverse(o=>{assert.ok(o.matrixWorld.elements.every(Number.isFinite));if(o.isBone)pose.push(...o.quaternion.toArray())});poses.push(pose);
}
assert.notDeepEqual(poses[0],poses[1]);
console.log(JSON.stringify({generatedFrames:frames.length,fps:motion.fps,duration:clip.duration,tracks:clip.tracks.length,posesChanged:true,linguisticallyVerified:false}));
