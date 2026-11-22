// Bake production joint transforms (not mesh vertices) for a local research review.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {naturalModel as source} from './check-natural-avatar.mjs';
const root=new URL('../',import.meta.url),three=new URL('frontend/node_modules/three/build/three.module.js',root).href;
function compile(file,subs={}){let s=fs.readFileSync(new URL('frontend/src/'+file,root),'utf8');for(const [a,b] of Object.entries(subs))s=s.replaceAll("'"+a+"'",JSON.stringify(b));return 'data:text/javascript;base64,'+Buffer.from(ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText).toString('base64')}
const skeleton=new URL('frontend/node_modules/three/examples/jsm/utils/SkeletonUtils.js',root).href;
const neural=compile('neuralMotion.ts',{three,'three/examples/jsm/utils/SkeletonUtils.js':skeleton});
const {createRocketboxClip}=await import(compile('rocketboxMotion.ts',{three,'./neuralMotion':neural}));
const {AvatarPlayback}=await import(compile('avatarPlayback.ts',{three}));
const folder=path.resolve(process.argv[2]||'docs/asl-comparison-10'),out=process.argv[3]||path.join(os.tmpdir(),'signbridge-asl10-bones');
fs.mkdirSync(out,{recursive:true});const samples=JSON.parse(fs.readFileSync(path.join(folder,'samples.json')));
for(const [i,s] of samples.entries()){
 const motion=JSON.parse(fs.readFileSync(path.join(folder,'model',String(i).padStart(4,'0'),'motion.json')));
 if(motion.text!==s.text||String(motion.id)!==s.id)throw Error('Text / motion identity mismatch');
 const model=(await import(skeleton)).clone(source),clip=createRocketboxClip(source,motion);
 const player=new AvatarPlayback(new THREE.AnimationMixer(model));let mesh;model.traverse(n=>{if(n.isSkinnedMesh&&!mesh)mesh=n});
 const count=mesh.skeleton.bones.length,frames=new Float32Array(motion.frame_count*count*16);
 const extra=[],m=new THREE.Matrix4(),v=new THREE.Vector3();
 for(let k=0;k<motion.frame_count;k++){
  player.sample(clip,k/motion.fps);model.updateMatrixWorld(true);mesh.skeleton.update();
  for(let j=0;j<count;j++){m.fromArray(mesh.skeleton.boneMatrices,j*16).multiply(mesh.bindMatrix).premultiply(mesh.bindMatrixInverse).premultiply(mesh.matrixWorld);m.toArray(frames,(k*count+j)*16)}
  extra.push(['L','R'].map(side=>model.getObjectByName('Bip01_'+side+'_Hand').getWorldPosition(v).toArray()));
 }
 if(!frames.every(Number.isFinite))throw Error('Invalid transform');
 fs.writeFileSync(path.join(out,s.id+'.bin'),Buffer.from(frames.buffer));
 fs.writeFileSync(path.join(out,s.id+'.json'),JSON.stringify({boneCount:count,wrist:extra,faceTracks:clip.tracks.filter(t=>t.name.includes('morphTargetInfluences')).length}));
 player.dispose();
}
