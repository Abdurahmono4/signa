// Read actual API motion data, retarget in CPU Three.js and verify caption gaps.
// This is geometry/timeline validation, not a rendered browser or ASL quality test.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {clone} from '../frontend/node_modules/three/examples/jsm/utils/SkeletonUtils.js';
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
const posed=clone(naturalModel);
const mixer=new THREE.AnimationMixer(posed),playback=new AvatarPlayback(mixer,createRocketboxIdleClip(naturalModel));
const intervals=[];let frames=0,sampledPoses=0,framingPoses=0;
const camera=new THREE.PerspectiveCamera(28,4/3,.1,100);
const {positionAvatarCamera}=await import(compile('frontend/src/avatarCamera.ts'));
positionAvatarCamera(camera);
const frameBounds={minX:Infinity,maxX:-Infinity,minY:Infinity,maxY:-Infinity};
const signingJoints=[];
posed.traverse(n=>{if(n.isBone&&(/Bip01_[LR]_(Hand|Finger)/.test(n.name)||n.name==='Bip01_Head'))signingJoints.push(n)});
assert.ok(signingJoints.length>=33);
for(const item of plan.items.filter(i=>i.neural_asset)){
 const motion=await get(neuralMotionAssetUrl(item.neural_asset));const rows=validateNeuralMotion(motion);frames+=rows.length;
 const clip=createRocketboxClip(naturalModel,motion);assert.ok(clip.tracks.every(t=>Array.from(t.values).every(Number.isFinite)));
 for(const at of [0,clip.duration*.5,Math.max(0,clip.duration-.001)]){
  playback.sample(clip,at);posed.updateMatrixWorld(true);
  posed.traverse(n=>{assert.ok(n.matrixWorld.elements.every(Number.isFinite))});sampledPoses++;
 }
 for(let n=0;n<rows.length;n++){
  playback.sample(clip,n/motion.fps);posed.updateMatrixWorld(true);
  for(const joint of signingJoints){
   const p=joint.getWorldPosition(new THREE.Vector3()).project(camera);
   assert.ok([p.x,p.y,p.z].every(Number.isFinite));
   frameBounds.minX=Math.min(frameBounds.minX,p.x);frameBounds.maxX=Math.max(frameBounds.maxX,p.x);
   frameBounds.minY=Math.min(frameBounds.minY,p.y);frameBounds.maxY=Math.max(frameBounds.maxY,p.y);
  }
  framingPoses++;
 }
 const previous=intervals.at(-1);
 const blockedBefore=plan.items.some(p=>p.unsupported&&p.end> (previous?.end??0)&&p.start<item.start);
 intervals.push({...item,duration:rows.length/motion.fps,clip,blockedBefore});
}
validateIntervals(intervals,plan.output_duration);
const unsupported=plan.items.filter(i=>i.unsupported);
for(const item of unsupported){
 assert.equal(item.generated,false);assert.equal(item.neural_asset,null);assert.ok(item.text.trim());
 const midpoint=(item.start+item.end)/2;assert.equal(motionAt(intervals,midpoint),null);
 if(item.end-item.start>.48){const presentation=presentationAt(intervals,midpoint);assert.equal(presentation.from,null);assert.equal(presentation.to,null)}
 const captions=job.segments.filter(s=>s.end>item.source_start&&s.start<item.source_end);
 assert.ok(captions.length&&captions[0].start<=item.source_start+.05&&captions.at(-1).end>=item.source_end-.05);
 const normalize=s=>s.toLowerCase().replace(/\s+/g,' ').trim();
 assert.ok(normalize(captions.map(s=>s.text).join(' ')).includes(normalize(item.text)),'Caption-only phrase must remain in the transcript');
}
assert.equal(plan.generated_phrases,intervals.length);assert.equal(plan.unsupported_phrases,unsupported.length);assert.equal(plan.coverage,0);
// Compare wrist travel on the same rig and frames. Suppressing the direct
// bridge reproduces the old two-stage return to idle in these medium gaps.
const wristNames=['Bip01_L_Hand','Bip01_R_Hand'];
let changedGaps=0,oldMeters=0,newMeters=0;
for(let i=1;i<intervals.length;i++){
 const prev=intervals[i-1],next=intervals[i],begin=Math.min(prev.end,prev.start+prev.duration/.85);
 const gap=next.start-begin;
 if(gap<=.48||gap>.9||next.blockedBefore)continue;
 changedGaps++;
 for(const blockedBefore of [true,false]){
  const pair=[prev,{...next,blockedBefore}];
  let previousPositions=null,travel=0;
  for(let k=0;k<=60;k++){
   const pose=presentationAt(pair,begin+gap*k/60);
   const sample=x=>x?{clip:x.item.clip,time:x.localTime}:null;
   playback.transition(sample(pose.from),sample(pose.to),pose.mix);
   const positions=wristNames.map(n=>posed.getObjectByName(n).getWorldPosition(new THREE.Vector3()));
   if(previousPositions)travel+=positions.reduce((s,p,j)=>s+p.distanceTo(previousPositions[j]),0);
   previousPositions=positions;
  }
  if(blockedBefore)oldMeters+=travel;else newMeters+=travel;
 }
}
console.log(JSON.stringify({changedGaps,oldMeters,newMeters}));
playback.dispose();
console.log(JSON.stringify({job_id:id,generated_phrases:intervals.length,unsupported_phrases:unsupported.length,motion_frames:frames,sampled_poses:sampledPoses,framing_poses:framingPoses,signing_joint_bounds_ndc:frameBounds,full_transcript_segments:job.segments.length,timing_scale:plan.timing_scale,visualBrowserValidation:false,linguisticValidation:false}));
assert.ok(frameBounds.minX>-.70&&frameBounds.maxX<.70&&frameBounds.minY>-.95&&frameBounds.maxY<.95,'Hands/head approach or exceed the cropped side panel.');
