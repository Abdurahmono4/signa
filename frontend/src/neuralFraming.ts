import * as THREE from 'three';
import {clone} from 'three/examples/jsm/utils/SkeletonUtils.js';
import {createNeuralClip,validateNeuralMotion} from './neuralMotion.ts';
import type {NeuralMotion} from './neuralMotion.ts';
import type {SigningEnvelope} from './framing.ts';

export function sampleNeuralSigningEnvelope(source:THREE.Object3D,motions:readonly NeuralMotion[]):SigningEnvelope{
 if(!motions.length)throw new Error('Neural camera framing needs a generated motion.');
 const model=clone(source);
 // The asset is authored in centimetres; all samples below convert to metres.
 // R3F may already have applied the .01 display scale to the visible root.
 // Restore native units on this private clone so that conversion happens once.
 // Otherwise the camera targets ~.016 m above the floor instead of the face.
 model.scale.setScalar(1);model.updateMatrixWorld(true);
 const mixer=new THREE.AnimationMixer(model),bounds=new THREE.Box3(),point=new THREE.Vector3();
 const names=['head','neck_01'];
 for(const side of ['l','r'])for(const joint of ['upperarm','lowerarm','hand','thumb_03','index_03','middle_03','ring_03','pinky_03'])names.push(`${joint}_${side}_1`);
 const joints=names.map(name=>{const joint=model.getObjectByName(name);if(!joint)throw new Error(`Neural camera joint missing: ${name}`);return joint});
 const head=model.getObjectByName('GaltisHead');
 if(!(head instanceof THREE.SkinnedMesh))throw new Error('Neural camera needs the interpreter head.');
 const decorations:THREE.Mesh[]=[];
 model.getObjectByName('SignaInterpreterHeadStyle')?.traverse(object=>{if(object instanceof THREE.Mesh){object.geometry.computeBoundingBox();decorations.push(object)}});
 function include(value:THREE.Vector3,padding=0){
  if(!value.toArray().every(Number.isFinite))throw new Error('Generated camera bounds are non-finite.');
  bounds.expandByPoint(value.clone().addScalar(padding));bounds.expandByPoint(value.clone().addScalar(-padding));
 }
 try{
  for(const motion of motions){
   const frames=validateNeuralMotion(motion),clip=createNeuralClip(model,motion),action=mixer.clipAction(clip);
   action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;
   for(let frame=0;frame<frames.length;frame++){
    action.reset().play();mixer.setTime(frame/motion.fps);model.updateMatrixWorld(true);head.skeleton.update();
    for(const joint of joints)include(joint.getWorldPosition(point).multiplyScalar(.01),.05);
    for(let vertex=0;vertex<head.geometry.attributes.position.count;vertex++)include(head.getVertexPosition(vertex,point).applyMatrix4(head.matrixWorld).multiplyScalar(.01));
    for(const mesh of decorations){
     const box=mesh.geometry.boundingBox!;
     for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z])include(point.set(x,y,z).applyMatrix4(mesh.matrixWorld).multiplyScalar(.01));
    }
   }
   mixer.stopAllAction();mixer.uncacheClip(clip);
  }
 }finally{mixer.stopAllAction();mixer.uncacheRoot(model)}
 if(bounds.isEmpty())throw new Error('Generated signing bounds are empty.');
 return {min:bounds.min.toArray(),max:bounds.max.toArray()};
}
