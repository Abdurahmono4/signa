import fs from 'node:fs';
import assert from 'node:assert/strict';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
const root=new URL('../frontend/public/avatar/',import.meta.url);
const b=fs.readFileSync(new URL('galtis.glb',root));const g=await new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),'');
const meshes=[];g.scene.traverse(o=>{if(o.isMesh)meshes.push(o)});assert.equal(meshes.length,3,'Export must not create thousands of material primitives');
for(const mesh of meshes.filter(m=>m.isSkinnedMesh)){for(const bone of mesh.skeleton.bones)assert.equal(g.scene.getObjectByName(bone.name),bone,`Ambiguous animated bone ${bone.name}`)}
const manifest=JSON.parse(fs.readFileSync(new URL('corpus.json',root)));const errors=[];const original=console.error;console.error=(...args)=>errors.push(String(args[0]));
for(const item of manifest){const mixer=new THREE.AnimationMixer(g.scene);const clip=THREE.AnimationClip.parse(JSON.parse(fs.readFileSync(new URL(`${item.id}.motion.json`,root))));assert.ok(Math.abs(clip.duration-item.duration)<.001);mixer.clipAction(clip).play();for(const time of [0,clip.duration/2,clip.duration,.1]){mixer.setTime(time);g.scene.updateMatrixWorld(true);g.scene.traverse(o=>assert.ok(o.matrixWorld.elements.every(Number.isFinite),`${item.id}: invalid transform`));}mixer.stopAllAction();mixer.uncacheRoot(g.scene)}
console.error=original;assert.deepEqual(errors,[],'Every animation track must bind to the exported mesh');console.log(`PASS: ${manifest.length} clips; 3 meshes; unambiguous bones; finite start/middle/end/seek poses; no missing bindings.`);
