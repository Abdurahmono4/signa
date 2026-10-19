// Read-only measurement of captured motion. This never rewrites animations or
// manifests and never removes internal holds, repeats, or transitions.
// node scripts/measure-motion-windows.mjs --out C:\path\motion-windows.json
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {clone} from '../frontend/node_modules/three/examples/jsm/utils/SkeletonUtils.js';

const project=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const args=process.argv.slice(2),outFlag=args.indexOf('--out');
const out=path.resolve(outFlag>=0?args[outFlag+1]:path.join(project,'work','motion-windows.json'));
const assetRoot=path.join(project,'frontend','public','avatar');
const manifest=JSON.parse(fs.readFileSync(path.join(assetRoot,'corpus.json'),'utf8'));
const bytes=fs.readFileSync(path.join(assetRoot,'galtis.glb'));
const base=(await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'')).scene;
const settings={sample_rate:60,reference_time:1/30,padding_seconds:.15,
 wrist_position_cm:.8,finger_position_cm:.35,joint_angle_degrees:1.5,
 face_influence_delta:.02,velocity_window_seconds:1/15,
 wrist_speed_cm_s:5,finger_speed_cm_s:4,joint_speed_degrees_s:15,face_speed_per_second:.35};
const radians=degrees=>degrees*Math.PI/180;
const wrists=['l','r'].map(side=>`hand_${side}_1`);
const fingers=['l','r'].flatMap(side=>['thumb','index','middle','ring','pinky'].flatMap(finger=>[1,2,3].map(joint=>`${finger}_0${joint}_${side}_1`)));
const names=[...wrists,...fingers];
const results=[];

function snapshot(model){
 return {
  joints:names.map(name=>{
   const bone=model.getObjectByName(name);assert.ok(bone?.isBone,`Missing captured joint ${name}`);
   return {position:bone.getWorldPosition(new THREE.Vector3()),quaternion:bone.getWorldQuaternion(new THREE.Quaternion())};
  }),
  face:['GaltisHead','GaltisBody'].flatMap(name=>Array.from(model.getObjectByName(name)?.morphTargetInfluences||[]))
 };
}
function difference(a,b,seconds=1){
 let wrist=0,finger=0,angle=0,face=0;
 a.joints.forEach((joint,index)=>{
  const delta=joint.position.distanceTo(b.joints[index].position)/seconds;
  if(index<wrists.length)wrist=Math.max(wrist,delta);else finger=Math.max(finger,delta);
  angle=Math.max(angle,joint.quaternion.angleTo(b.joints[index].quaternion)/seconds);
 });
 a.face.forEach((value,index)=>face=Math.max(face,Math.abs(value-b.face[index])/seconds));
 return {wrist_cm:wrist,finger_cm:finger,joint_radians:angle,face};
}
function poseChanged(delta){
 return delta.wrist_cm>settings.wrist_position_cm||delta.finger_cm>settings.finger_position_cm||
  delta.joint_radians>radians(settings.joint_angle_degrees)||delta.face>settings.face_influence_delta;
}
function moving(delta){
 return delta.wrist_cm>settings.wrist_speed_cm_s||delta.finger_cm>settings.finger_speed_cm_s||
  delta.joint_radians>radians(settings.joint_speed_degrees_s)||delta.face>settings.face_speed_per_second;
}
const round=value=>+value.toFixed(6);

function exactFlatPadding(clip,referenceTime){
 // Examine every original recorded key in every channel, including face,
 // helpers, trunk, legs, position, quaternion and scale. Requiring all numeric
 // components to stay within 0.0001 is deliberately stricter than pose identity.
 const tolerance=.0001;
 let leadingEnd=clip.duration,trailingStart=referenceTime,movingTracks=0;
 for(const track of clip.tracks){
  const interpolant=track.createInterpolant(),start=Array.from(interpolant.evaluate(referenceTime)),end=Array.from(interpolant.evaluate(clip.duration));
  const width=track.getValueSize();
  const changed=(index,baseline)=>baseline.some((value,component)=>Math.abs(track.values[index*width+component]-value)>tolerance);
  let before=referenceTime,trackLeadingEnd=clip.duration,trackMoving=false;
  for(let index=0;index<track.times.length;index++){
   const time=track.times[index];if(time<referenceTime||time>clip.duration)continue;
   if(changed(index,start)){trackLeadingEnd=before;trackMoving=true;break}
   before=time;
  }
  let after=clip.duration,trackTrailingStart=referenceTime;
  for(let index=track.times.length-1;index>=0;index--){
   const time=track.times[index];if(time>clip.duration||time<referenceTime)continue;
   if(changed(index,end)){trackTrailingStart=after;trackMoving=true;break}
   after=time;
  }
  leadingEnd=Math.min(leadingEnd,trackLeadingEnd);trailingStart=Math.max(trailingStart,trackTrailingStart);
  if(trackMoving)movingTracks++;
 }
 const start=movingTracks?Math.max(referenceTime,leadingEnd-settings.padding_seconds):referenceTime;
 const end=movingTracks?Math.min(clip.duration,trailingStart+settings.padding_seconds):clip.duration;
 return {method:'Every original key in every recorded track; <=0.0001 numeric deviation, then keep 150ms of each flat boundary.',
  tolerance,tracks_checked:clip.tracks.length,nonconstant_tracks:movingTracks,
  leading_flat_end:round(leadingEnd),trailing_flat_start:round(trailingStart),
  source_start:round(start),source_end:round(end),
  removable_padding_seconds:round(Math.max(0,start-referenceTime)+Math.max(0,clip.duration-end)),
  verified:false,note:'Measurement only. No automatic linguistic approval or playback_window publication.'};
}

for(const item of manifest){
 const model=clone(base),clip=THREE.AnimationClip.parse(JSON.parse(fs.readFileSync(path.join(assetRoot,`${item.id}.motion.json`),'utf8')));
 const mixer=new THREE.AnimationMixer(model),action=mixer.clipAction(clip).setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
 const referenceTime=Math.min(settings.reference_time,clip.duration);
 const times=[];
 for(let time=referenceTime;time<clip.duration;time+=1/settings.sample_rate)times.push(time);
 times.push(clip.duration);
 const samples=times.map(time=>{mixer.setTime(time);model.updateMatrixWorld(true);return {time,pose:snapshot(model)}});
 const reference=samples[0].pose,velocityRadius=Math.max(1,Math.round(settings.velocity_window_seconds*settings.sample_rate/2));
 const measurements=samples.map((sample,index)=>{
  const before=samples[Math.max(0,index-velocityRadius)],after=samples[Math.min(samples.length-1,index+velocityRadius)];
  const offset=difference(sample.pose,reference),speed=difference(after.pose,before.pose,Math.max(1/settings.sample_rate,after.time-before.time));
  return {time:sample.time,offset,speed,active:poseChanged(offset)||moving(speed),pose_active:poseChanged(offset),velocity_active:moving(speed)};
 });
 const active=measurements.filter(sample=>sample.active);
 // Keep the complete source when no meaningful activity was detected; a quiet
 // static letter/face hold is not grounds to discard its captured duration.
 const first=active[0]?.time??referenceTime,last=active.at(-1)?.time??clip.duration;
 const sourceStart=active.length?Math.max(referenceTime,first-settings.padding_seconds):referenceTime;
 const sourceEnd=active.length?Math.min(clip.duration,last+settings.padding_seconds):clip.duration;
 const leading=measurements.filter(sample=>sample.time<sourceStart),trailing=measurements.filter(sample=>sample.time>sourceEnd);
 assert.ok([...leading,...trailing].every(sample=>!sample.active),'A proposed boundary cannot cut measured activity.');
 const paddingSaved=Math.max(0,sourceStart-referenceTime)+Math.max(0,clip.duration-sourceEnd);
 const reasons=measurements.filter(sample=>sample.active&&sample.time<=referenceTime+settings.padding_seconds).map(sample=>({time:round(sample.time),pose:sample.pose_active,velocity:sample.velocity_active,offset:sample.offset,speed:sample.speed})).slice(0,3);
 results.push({id:item.id,phrase:item.phrase,kind:item.kind||'dictionary',letter:item.letter??null,
  source_duration:round(clip.duration),source_start:round(sourceStart),source_end:round(sourceEnd),candidate_duration:round(sourceEnd-sourceStart),
  removable_neutral_padding_seconds:round(paddingSaved),calibration_frame_skipped_seconds:round(referenceTime),
  first_measured_activity:round(first),last_measured_activity:round(last),sample_count:samples.length,
  leading_neutral_samples:leading.length,trailing_neutral_samples:trailing.length,
  exact_flat_padding:exactFlatPadding(clip,referenceTime),
  status:paddingSaved>=1/settings.sample_rate?'conservative_kinematic_candidate':'no_meaningful_neutral_padding',
  early_activity_evidence:reasons});
 mixer.stopAllAction();mixer.uncacheRoot(model);
}
const report={
 method:'Conservative first/last captured activity envelope relative to the take’s captured neutral entry, with full face/finger checks and 150ms padding.',
 limitations:['Kinematic candidate only; it does not certify linguistic boundaries.','Only leading/trailing near-neutral stationary samples are candidates. Internal pauses, dynamic letters and repeats are retained.','No source motion, manifests, playback speeds or product defaults were changed.','The first source frame may be a calibration T-pose; the existing interpreter already samples at least 1/30s. Its exclusion is reported separately from idle-padding savings.'],
 settings,clip_count:results.length,
 total_source_seconds:round(results.reduce((sum,item)=>sum+item.source_duration,0)),
 total_removable_neutral_padding_seconds:round(results.reduce((sum,item)=>sum+item.removable_neutral_padding_seconds,0)),
 total_removable_exact_flat_padding_seconds:round(results.reduce((sum,item)=>sum+item.exact_flat_padding.removable_padding_seconds,0)),
 results};
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
for(const item of results.filter(item=>['hello','book','bring'].includes(item.id)))console.log(`${item.id}: source ${item.source_duration}s; candidate ${item.source_start}–${item.source_end}s; neutral padding saved ${item.removable_neutral_padding_seconds}s.`);
console.log(`Read-only report: ${results.length} clips; ${report.total_removable_neutral_padding_seconds}s near-neutral candidate savings; ${report.total_removable_exact_flat_padding_seconds}s exact-flat candidate savings. ${out}`);
