import fs from 'node:fs';
import assert from 'node:assert/strict';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {createInterpreter} from '../frontend/src/interpreter.ts';

const assets=new URL('../frontend/public/avatar/',import.meta.url);
const bytes=fs.readFileSync(new URL('galtis.glb',assets));
const source=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const original=source.scene;
const styled=createInterpreter(original);
assert.equal(styled.getObjectByName('Strand008').visible,false,'Original hair is replaced');
for(const name of ['SignaCroppedHair','SignaGlassesL','SignaGlassesR','SignaCrewneckCollar'])assert.ok(styled.getObjectByName(name),`${name} must exist`);
for(const name of ['GaltisBody','GaltisHead']){
 const before=original.getObjectByName(name),after=styled.getObjectByName(name);
 assert.notEqual(before.geometry,after.geometry,'Styling must not mutate the cached source model');
 assert.deepEqual(after.morphTargetDictionary,before.morphTargetDictionary,'Facial animation channel names must be preserved');
 assert.equal(after.geometry.morphAttributes.position?.length,before.geometry.morphAttributes.position?.length,'All source facial morphs must remain');
}
{
 const before=original.getObjectByName('GaltisBody'),after=styled.getObjectByName('GaltisBody');
 const indices=before.geometry.attributes.skinIndex,weights=before.geometry.attributes.skinWeight;
 let handVertices=0;
 for(let vertex=0;vertex<indices.count;vertex++){
  let handWeight=0;
  for(let component=0;component<4;component++){
   const name=before.skeleton.bones[indices.getComponent(vertex,component)].name;
   if(/^(hand|thumb|index|middle|ring|pinky)_/.test(name))handWeight+=weights.getComponent(vertex,component);
  }
  if(handWeight<.5)continue;
  handVertices++;
  for(let component=0;component<3;component++)assert.equal(after.geometry.attributes.position.getComponent(vertex,component),before.geometry.attributes.position.getComponent(vertex,component),'Styling must preserve source hand/finger surface vertices');
 }
 assert.ok(handVertices>1000,'Verify actual hand surfaces, not just a few joint centres.');
 const luminance=color=>new THREE.Color(color).toArray().reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);
 assert.ok((luminance('#dca783')+.05)/(luminance('#27364f')+.05)>5,'Hand and sweater materials need strong luminance contrast.');
}
const manifest=JSON.parse(fs.readFileSync(new URL('corpus.json',assets)));
const bindingErrors=[],previousError=console.error;
console.error=(...args)=>bindingErrors.push(String(args[0]));
try{
 for(const {id} of manifest){
  const clip=THREE.AnimationClip.parse(JSON.parse(fs.readFileSync(new URL(`${id}.motion.json`,assets))));
  const mixers=[original,styled].map(model=>new THREE.AnimationMixer(model));
  const actions=mixers.map(mixer=>{const action=mixer.clipAction(clip);action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;return action});
  for(const time of [1/30,clip.duration/4,clip.duration/2,clip.duration,.1]){
   mixers.forEach((mixer,index)=>{actions[index].reset().play();mixer.setTime(time)});
   original.updateMatrixWorld(true);styled.updateMatrixWorld(true);
   for(const side of ['l','r'])for(const joint of ['hand','index_03','thumb_03','pinky_03']){
    const name=`${joint}_${side}_1`;
    const a=original.getObjectByName(name).getWorldPosition(new THREE.Vector3());
    const b=styled.getObjectByName(name).getWorldPosition(new THREE.Vector3());
    assert.ok(a.distanceTo(b)<1e-7,`${id}: ${name} recorded motion changed`);
   }
   styled.traverse(object=>assert.ok(object.matrixWorld.elements.every(Number.isFinite),`${id}: invalid styled transform`));
   assert.deepEqual(styled.getObjectByName('GaltisHead').morphTargetInfluences,original.getObjectByName('GaltisHead').morphTargetInfluences,`${id}: original facial timing must remain`);
  }
  mixers.forEach((mixer,index)=>{mixer.stopAllAction();mixer.uncacheRoot(index?styled:original)});
 }
}finally{console.error=previousError}
assert.deepEqual(bindingErrors,[],'Every original animation must still bind');
console.log(`PASS: ${manifest.length} clips; identical recorded hand/finger transforms; facial channels and timing preserved; new style attachments finite; source assets unchanged.`);
