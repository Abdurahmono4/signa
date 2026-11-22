// Read actual API motion data, retarget in CPU Three.js and verify caption gaps.
// This is geometry/timeline validation, not a rendered browser or ASL quality test.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {naturalModel} from './check-natural-avatar.mjs';
const id=process.argv[2];assert.match(id||'',/^[a-f0-9]{32}$/);
const root=new URL('../',import.meta.url),three=new URL('frontend/node_modules/three/build/three.module.js',root).href;
function compile(path,replacements=[]){let code=fs.readFileSync(new URL(path,root),'utf8');for(const [a,b] of replacements)code=code.replaceAll(a,b);return 'data:text/javascript;base64,'+Buffer.from(ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText).toString('base64')}
const neural=compile('frontend/src/neuralMotion.ts',[["'three'",JSON.stringify(three)],["'three/examples/jsm/utils/SkeletonUtils.js'",JSON.stringify(new URL('frontend/node_modules/three/examples/jsm/utils/SkeletonUtils.js',root).href)]]);
const {validateNeuralMotion,neuralMotionAssetUrl}=await import(neural);
const {createRocketboxClip,createRocketboxIdleClip}=await import(compile('frontend/src/rocketboxMotion.ts',[["'three'",JSON.stringify(three)],["'./neuralMotion'",JSON.stringify(neural)]]));
const {AvatarPlayback}=await import(compile('frontend/src/avatarPlayback.ts',[["'three'",JSON.stringify(three)]]));
const {motionAt,presentationAt,validateIntervals}=await import(compile('frontend/src/avatarTimeline.ts'));
const base='http://127.0.0.1:8001';
async function get(path){const r=await fetch(base+path,{signal:AbortSignal.timeout(20000)});assert.equal(r.status,200);return r.json()}
const plan=await get(`/api/jobs/${id}/neural/plan`),job=await get(`/api/jobs/${id}`);
const mixer=new THREE.AnimationMixer(naturalModel),playback=new AvatarPlayback(mixer,createRocketboxIdleClip(naturalModel));
const intervals=[];let frames=0,sampledPoses=0,framingPoses=0;
const camera=new THREE.PerspectiveCamera(28,4/3,.1,100);
camera.position.set(0,1.32,2.2);camera.lookAt(0,1.32,0);camera.updateMatrixWorld(true);
const frameBounds={minX:Infinity,maxX:-Infinity,minY:Infinity,maxY:-Infinity};
const signingJoints=[];
naturalModel.traverse(n=>{if(n.isBone&&(/Bip01_[LR]_(Hand|Finger)/.test(n.name)||n.name==='Bip01_Head'))signingJoints.push(n)});
assert.ok(signingJoints.length>=33);
for(const item of plan.items.filter(i=>i.neural_asset)){
 const motion=await get(neuralMotionAssetUrl(item.neural_asset));const rows=validateNeuralMotion(motion);frames+=rows.length;
 const clip=createRocketboxClip(naturalModel,motion);assert.ok(clip.tracks.every(t=>Array.from(t.values).every(Number.isFinite)));
 for(const at of [0,clip.duration*.5,Math.max(0,clip.duration-.001)]){
  playback.sample(clip,at);naturalModel.updateMatrixWorld(true);
  naturalModel.traverse(n=>{assert.ok(n.matrixWorld.elements.every(Number.isFinite))});sampledPoses++;
 }
 for(let n=0;n<rows.length;n++){
  playback.sample(clip,n/motion.fps);naturalModel.updateMatrixWorld(true);
  for(const joint of signingJoints){
   const p=joint.getWorldPosition(new THREE.Vector3()).project(camera);
   assert.ok([p.x,p.y,p.z].every(Number.isFinite));
   frameBounds.minX=Math.min(frameBounds.minX,p.x);frameBounds.maxX=Math.max(frameBounds.maxX,p.x);
   frameBounds.minY=Math.min(frameBounds.minY,p.y);frameBounds.maxY=Math.max(frameBounds.maxY,p.y);
  }
  framingPoses++;
 }
 const skinBox=new THREE.Box3();naturalModel.traverse(n=>{if(n.isSkinnedMesh){n.skeleton.update();n.computeBoundingBox();skinBox.union(n.boundingBox.clone().applyMatrix4(n.matrixWorld))}});console.log('skin bounds',skinBox.min.toArray(),skinBox.max.toArray());
 intervals.push({...item,duration:rows.length/motion.fps});mixer.uncacheClip(clip);
}
validateIntervals(intervals,plan.output_duration);
const unsupported=plan.items.filter(i=>i.unsupported);
for(const item of unsupported){
 assert.equal(item.generated,false);assert.equal(item.neural_asset,null);assert.ok(item.text.trim());
 const midpoint=(item.start+item.end)/2;assert.equal(motionAt(intervals,midpoint),null);
 if(item.end-item.start>.48){const presentation=presentationAt(intervals,midpoint);assert.equal(presentation.from,null);assert.equal(presentation.to,null)}
 assert.ok(job.segments.some(s=>s.start<=item.source_start+.05&&s.end>=item.source_end-.05));
}
assert.equal(plan.generated_phrases,intervals.length);assert.equal(plan.unsupported_phrases,unsupported.length);assert.equal(plan.coverage,0);
playback.dispose();
console.log(JSON.stringify({job_id:id,generated_phrases:intervals.length,unsupported_phrases:unsupported.length,motion_frames:frames,sampled_poses:sampledPoses,framing_poses:framingPoses,signing_joint_bounds_ndc:frameBounds,full_transcript_segments:job.segments.length,timing_scale:plan.timing_scale,visualBrowserValidation:false,linguisticValidation:false}));
assert.ok(frameBounds.minX>-.95&&frameBounds.maxX<.95&&frameBounds.minY>-.95&&frameBounds.maxY<.95,'Hands/head approach or exceed the portrait frame.');
