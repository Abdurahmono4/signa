import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const bytes=fs.readFileSync(new URL('../assets/avatars/galtis.glb',import.meta.url));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const clip=THREE.AnimationClip.parse(JSON.parse(fs.readFileSync(new URL('../assets/animations/demo-asl-hello.json',import.meta.url))));
const mixer=new THREE.AnimationMixer(gltf.scene);const action=mixer.clipAction(clip);
const poses=[];let fingers=0;
gltf.scene.traverse(o=>{if(o.isBone&&/finger|thumb|index|middle|ring|pinky/i.test(o.name))fingers++});
for(const t of [.04,clip.duration*.5,clip.duration-.01]){
 action.reset().play();mixer.setTime(t);gltf.scene.updateMatrixWorld(true);
 const pose=[];gltf.scene.traverse(o=>{assert.ok(o.matrixWorld.elements.every(Number.isFinite));if(o.isBone)pose.push(...o.quaternion.toArray())});poses.push(pose);
}
assert.ok(fingers>10,'Individual finger bones required');
assert.notDeepEqual(poses[0],poses[1],'Animation must change skeletal poses');
console.log(JSON.stringify({fingerBones:fingers,tracks:clip.tracks.length,duration:clip.duration,posesChanged:true,visualBrowserValidation:false}));
