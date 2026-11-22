import * as THREE from 'three';
import {clone} from 'three/examples/jsm/utils/SkeletonUtils.js';

/** Keep the authored face, hair, morph targets and human proportions. */
export function createInterpreter(source:THREE.Object3D){
 const model=clone(source);
 model.traverse(object=>{
  if(!(object instanceof THREE.Mesh))return;
  object.geometry=object.geometry.clone();
  const colors=object.geometry.getAttribute('color');
  if(colors&&object.name==='GaltisBody'){
   const shirt=new THREE.Color('#294a84');
   for(let i=0;i<colors.count;i++){
    if(colors.getX(i)<.04&&colors.getY(i)<.1)colors.setXYZ(i,shirt.r,shirt.g,shirt.b);
   }
   colors.needsUpdate=true;
  }
  object.material=new THREE.MeshStandardMaterial({vertexColors:!!colors,roughness:.78,metalness:0});
  object.frustumCulled=false;
 });
 return model;
}
