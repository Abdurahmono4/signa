// Import source motions, never synthesize or linguistically approve signs.
// node scripts/import-corpus.mjs selected.json --workdir C:\path\to\work [--write]
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {FBXLoader} from '../frontend/node_modules/three/examples/jsm/loaders/FBXLoader.js';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {clone} from '../frontend/node_modules/three/examples/jsm/utils/SkeletonUtils.js';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';

const project=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const args=process.argv.slice(2),selection=args[0];
assert.ok(selection&&!selection.startsWith('--'),'Pass a JSON list of verified official source assets.');
const workFlag=args.indexOf('--workdir');
const work=path.resolve(workFlag>=0?args[workFlag+1]:path.join(project,'work','corpus-import'));
const write=args.includes('--write');
const records=JSON.parse(fs.readFileSync(selection,'utf8'));
assert.ok(Array.isArray(records)&&records.length>0&&records.length<=30,'Import 1–30 source assets per batch.');
fs.mkdirSync(work,{recursive:true});
const avatar=path.join(project,'frontend','public','avatar');
const glb=fs.readFileSync(path.join(avatar,'galtis.glb'));
const base=(await new GLTFLoader().parseAsync(glb.buffer.slice(glb.byteOffset,glb.byteOffset+glb.byteLength),'')).scene;
const ids=new Set(),results=[],failures=[];
const originalWarn=console.warn;
const blobSha=bytes=>crypto.createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
const matrixDifference=(a,b)=>Math.max(...a.elements.map((value,index)=>Math.abs(value-b.elements[index])));

async function loadVerified(record){
 assert.match(record.sha,/^[a-f0-9]{40}$/);
 const url=new URL(record.download);
 assert.ok(url.protocol==='https:'&&url.hostname==='raw.githubusercontent.com'&&url.pathname.startsWith('/StudioGalt/Sign-Language-Mocap-Archive/'),'Use the official archive.');
 const cache=path.join(work,`${record.id}.fbx`);
 let bytes=fs.existsSync(cache)?fs.readFileSync(cache):null;
 if(!bytes){
  const response=await fetch(url,{signal:AbortSignal.timeout(120_000)});assert.ok(response.ok,`Download HTTP ${response.status}`);
  assert.ok(Number(response.headers.get('content-length')||0)<=20*1024*1024,'Source exceeds 20 MB.');
  bytes=Buffer.from(await response.arrayBuffer());assert.ok(bytes.length<=20*1024*1024,'Source exceeds 20 MB.');
  assert.equal(blobSha(bytes),record.sha,'Downloaded Git blob SHA does not match.');fs.writeFileSync(cache,bytes);
 }
 assert.equal(blobSha(bytes),record.sha,'Cached Git blob SHA does not match.');
 const warnings=[];console.warn=(...parts)=>warnings.push(parts.join(' '));
 let source;try{source=new FBXLoader().parse(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'')}finally{console.warn=originalWarn}
 return {source,warnings};
}

// The shipped GLB was exported from this exact official Hello FBX. Compare skin
// bindings against its source, because GLTFExporter adds unique helper names and
// changes the representation of bind matrices. This reference is SHA checked too.
const referenceRecord=JSON.parse(fs.readFileSync(path.join(avatar,'corpus.json'),'utf8')).find(item=>item.id==='hello');
assert.ok(referenceRecord,'The shipped Hello reference is required.');
const reference=(await loadVerified(referenceRecord)).source;

function validateRig(source){
 const problems=[],seen=new Set(),tracks=new Set(source.animations[0]?.tracks.map(track=>track.name));
 source.traverse(bone=>{
  if(!bone.isBone)return;
  // FBX carries repeated helper skeletons with duplicate names. Three's track
  // bindings and the shipped GLB resolve the first canonical named node.
  if(seen.has(bone.name))return;seen.add(bone.name);
  const target=base.getObjectByName(bone.name);
  if(!target?.isBone){problems.push(`Missing bone ${bone.name}`);return}
  if(bone.parent?.name!==target.parent?.name)problems.push(`Different parent for ${bone.name}`);
  // Every canonical animated transform must be supplied in full. Static source
  // transforms may be the exported first pose and therefore differ per take.
  for(const [property,diff] of [['position',bone.position.distanceTo(target.position)],['quaternion',bone.quaternion.angleTo(target.quaternion)],['scale',bone.scale.distanceTo(target.scale)]]){
   if(!tracks.has(`${bone.name}.${property}`)&&diff>1e-5)problems.push(`Missing ${property} channel for changed bone ${bone.name}`);
  }
 });
 source.traverse(mesh=>{
  if(!mesh.isSkinnedMesh)return;
  const ref=reference.getObjectByName(mesh.name),target=base.getObjectByName(mesh.name);
  if(!ref?.isSkinnedMesh||!target?.isSkinnedMesh){problems.push(`Missing skinned mesh ${mesh.name}`);return}
  if(mesh.skeleton.bones.length!==ref.skeleton.bones.length||mesh.skeleton.bones.length!==target.skeleton.bones.length){problems.push(`Different bone count for ${mesh.name}`);return}
  if(matrixDifference(mesh.bindMatrix,ref.bindMatrix)>1e-5||matrixDifference(mesh.bindMatrixInverse,ref.bindMatrixInverse)>1e-5)problems.push(`Different mesh bind matrix for ${mesh.name}`);
  mesh.skeleton.bones.forEach((bone,index)=>{
   const refBone=ref.skeleton.bones[index],targetBone=target.skeleton.bones[index];
   if(bone.name!==refBone.name||(targetBone.name!==bone.name&&targetBone.name!==`${bone.name}_1`))problems.push(`Different skin order for ${mesh.name}:${bone.name}`);
   if(matrixDifference(mesh.skeleton.boneInverses[index],ref.skeleton.boneInverses[index])>1e-5)problems.push(`Different inverse bind for ${mesh.name}:${bone.name}`);
  });
 });
 assert.ok(!problems.length,`Source rig differs from the shipped GLB (${problems.length} mismatches): ${problems.slice(0,8).join('; ')}. No guessed retargeting.`);
}

function convert(source){
 assert.equal(source.animations.length,1,'Expected exactly one recorded source motion.');
 validateRig(source);
 const clip=source.animations[0].clone();
 assert.ok(Number.isFinite(clip.duration)&&clip.duration>0&&clip.duration<=30,'Invalid clip duration.');
 const remapped=[];
 for(const track of clip.tracks){
  const binding=THREE.PropertyBinding.parseTrackName(track.name);
  const sourceNode=source.getObjectByName(binding.nodeName),target=base.getObjectByName(binding.nodeName);
  assert.ok(sourceNode&&target,`Unmapped animated node ${binding.nodeName}`);
  assert.ok(Array.from(track.times).every(Number.isFinite)&&Array.from(track.values).every(Number.isFinite),`Invalid values in ${track.name}`);
  if(binding.propertyName==='morphTargetInfluences'){
   const key=Object.keys(sourceNode.morphTargetDictionary||{}).find(name=>sourceNode.morphTargetDictionary[name]===Number(binding.propertyIndex));
   const index=target.morphTargetDictionary?.[key];
   assert.ok(index!==undefined,`Unmapped face morph ${binding.nodeName}:${key}`);
   const previous=track.name;
   track.name=`${binding.nodeName}.morphTargetInfluences[${index}]`;
   if(previous!==track.name)remapped.push({from:previous,to:track.name,morph:key});
  }
 }
 clip.optimize();
 const model=clone(base),captured=clone(source),mixer=new THREE.AnimationMixer(model),sourceMixer=new THREE.AnimationMixer(captured),errors=[];
 let maxBoneMatrixDifference=0,maxMorphDifference=0;
 const previousError=console.error;console.error=(...parts)=>errors.push(parts.join(' '));
 try{
  const action=mixer.clipAction(clip).setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
  const sourceAction=sourceMixer.clipAction(source.animations[0]).setLoop(THREE.LoopOnce,1);sourceAction.clampWhenFinished=true;sourceAction.play();
  for(let sample=0;sample<=20;sample++){
   const time=clip.duration*sample/20;
   mixer.setTime(time);sourceMixer.setTime(time);model.updateMatrixWorld(true);captured.updateMatrixWorld(true);
   model.traverse(object=>{
    assert.ok(object.matrixWorld.elements.every(Number.isFinite),`Invalid pose ${object.name}`);
    if(object.morphTargetInfluences)assert.ok(object.morphTargetInfluences.every(Number.isFinite),`Invalid face ${object.name}`);
   });
   captured.traverse(mesh=>{
    if(!mesh.isSkinnedMesh)return;
    const target=model.getObjectByName(mesh.name);
    mesh.skeleton.bones.forEach((bone,index)=>{
     const difference=matrixDifference(bone.matrixWorld,target.skeleton.bones[index].matrixWorld);
     maxBoneMatrixDifference=Math.max(maxBoneMatrixDifference,difference);
     assert.ok(difference<1e-4,`Recorded skin pose changed: ${mesh.name}:${bone.name} at ${time}`);
    });
    for(const [name,index] of Object.entries(mesh.morphTargetDictionary||{})){
     const targetIndex=target.morphTargetDictionary?.[name];
     assert.ok(targetIndex!==undefined,`Missing face morph ${mesh.name}:${name}`);
     const difference=Math.abs(mesh.morphTargetInfluences[index]-target.morphTargetInfluences[targetIndex]);
     maxMorphDifference=Math.max(maxMorphDifference,difference);
     assert.ok(difference<1e-6,`Captured face morph changed: ${mesh.name}:${name}`);
    }
   });
  }
 }finally{console.error=previousError;mixer.stopAllAction();mixer.uncacheRoot(model);sourceMixer.stopAllAction();sourceMixer.uncacheRoot(captured)}
 assert.deepEqual(errors,[],'Every animated source track must bind.');
 return {clip,remapped,maxBoneMatrixDifference,maxMorphDifference};
}

for(const record of records){
 try{
  assert.match(record.id,/^[a-z][a-z0-9-]{0,63}$/);assert.ok(!ids.has(record.id),'Duplicate id');ids.add(record.id);
  assert.ok(typeof record.phrase==='string'&&record.phrase.trim());
  if(record.kind==='fingerspelling'){
   assert.match(record.letter,/^[A-Z]$/,'A captured fingerspelling asset must identify one Latin letter.');
   assert.equal(record.phrase,record.letter,'Letter assets must not pretend to be dictionary words.');
   assert.equal(record.id,`asl-letter-${record.letter.toLowerCase()}`,'Keep letter IDs deterministic.');
  }
  assert.equal(record.license,'CC0-1.0','The source must have verified reusable licensing.');
  const {source,warnings}=await loadVerified(record);
  const {clip,remapped,maxBoneMatrixDifference,maxMorphDifference}=convert(source);
  const metadata={...record,duration:clip.duration,animation_asset:record.id,keyframes:[],status:'source',purpose:'sign',language:'ASL',
   dropped_tracks:0,validation:{method:'reference-skin-bind-and-recorded-pose-equivalence',samples:21,source_tracks:source.animations[0].tracks.length,
    exported_tracks:clip.tracks.length,remapped_morph_tracks:remapped.length,max_bone_matrix_difference:maxBoneMatrixDifference,max_morph_difference:maxMorphDifference,warnings}};
  results.push({metadata,motion:THREE.AnimationClip.toJSON(clip)});
  console.log(`VERIFIED ${record.id}: ${clip.duration.toFixed(3)}s; ${clip.tracks.length} tracks; no dropped motion; ${remapped.length} morph remaps.`);
 }catch(error){console.warn=originalWarn;failures.push({id:record.id,error:error.message});console.error(`REJECTED ${record.id}: ${error.message}`)}
}
fs.writeFileSync(path.join(work,'validation.json'),JSON.stringify({verified:results.map(result=>result.metadata),rejected:failures},null,2));
assert.equal(failures.length,0,'No corpus files were published; remove rejected candidates and retry.');
if(write){
 const manifestPath=path.join(avatar,'corpus.json'),manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
 for(const result of results){
  assert.ok(!manifest.some(item=>item.id===result.metadata.id),`Refuse to overwrite existing source ${result.metadata.id}`);
 }
 for(const result of results){fs.writeFileSync(path.join(avatar,`${result.metadata.id}.motion.json`),JSON.stringify(result.motion));manifest.push(result.metadata)}
 const content=JSON.stringify(manifest,null,2)+'\n';
 fs.writeFileSync(manifestPath,content);fs.writeFileSync(path.join(project,'backend','app','assets','corpus.json'),content);
 console.log(`PUBLISHED ${results.length} new source previews; corpus now has ${manifest.length}. No expert approval was added.`);
}else console.log('Check only. Pass --write to publish the verified batch.');
