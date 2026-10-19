import * as THREE from 'three';
import {clone} from 'three/examples/jsm/utils/SkeletonUtils.js';

const skin=new THREE.Color('#dca783');
// A dark, unpatterned top keeps small hand contours distinct in the inset.
const knit=new THREE.Color('#27364f');
const hairColor=new THREE.Color('#302b3f');

function sculptFace(point:THREE.Vector3){
 const blend=THREE.MathUtils.smoothstep(point.z,166,173);
 point.x*=1+.34*blend;
 // Enlarge around the eye line: the chin drops, shortening the exposed neck.
 point.z+=(point.z-180)*.10*blend;
 if(point.y< -10)point.y=-10+(point.y+10)*.88;
 return point;
}

function restyleMesh(mesh:THREE.Mesh){
 const geometry=mesh.geometry.clone();
 mesh.geometry=geometry;
 const colors=geometry.getAttribute('color');
 const positions=geometry.getAttribute('position');
 if(colors){
  for(let index=0;index<colors.count;index++){
   const red=colors.getX(index),green=colors.getY(index),blue=colors.getZ(index);
   let color:THREE.Color;
   if(mesh.name==='GaltisBody'){
    const x=positions.getX(index),z=positions.getZ(index);
    // Source hand/forearm skin stays distinct against a matte interpreter top.
    const sourceClothes=red<.04&&green<.1;
    const torso=z>105&&z<159&&Math.abs(x)<21;
    color=sourceClothes||torso?knit:skin;
   }else if(red>.7&&green>.6){
    color=new THREE.Color('#fff5e8');
   }else if(red>.3&&green<.13&&blue<.15){
    color=new THREE.Color('#9c5151');
   }else if(red<.1){
    color=new THREE.Color('#302b3f');
   }else{
    color=skin;
   }
   colors.setXYZ(index,color.r,color.g,color.b);
  }
  colors.needsUpdate=true;
 }
 if(mesh.name==='GaltisHead'){
  const before=new THREE.Vector3(),after=new THREE.Vector3(),delta=new THREE.Vector3();
  const morphs=geometry.morphAttributes.position||[];
  for(let index=0;index<positions.count;index++){
   before.fromBufferAttribute(positions,index);
   after.copy(before);sculptFace(after);
   for(const morph of morphs){
    delta.fromBufferAttribute(morph,index);
    if(geometry.morphTargetsRelative)delta.add(before);
    sculptFace(delta);
    if(geometry.morphTargetsRelative)delta.sub(after);
    morph.setXYZ(index,delta.x,delta.y,delta.z);
   }
   positions.setXYZ(index,after.x,after.y,after.z);
  }
 }else if(mesh.name==='GaltisBody'){
  // A flatter, looser knit silhouette instead of the original fitted outfit.
  for(let index=0;index<positions.count;index++){
   const x=positions.getX(index),y=positions.getY(index),z=positions.getZ(index);
   if(Math.abs(x)<19&&z>118&&z<157){
    const blend=THREE.MathUtils.smoothstep(z,118,133)*(1-THREE.MathUtils.smoothstep(Math.abs(x),12,19));
    positions.setY(index,Math.max(y*(1-.18*blend),-11.2));
   }
  }
 }
 positions.needsUpdate=true;
 geometry.computeVertexNormals();
 geometry.computeBoundingSphere();
 mesh.material=new THREE.MeshStandardMaterial({vertexColors:true,roughness:.86,metalness:0});
 mesh.frustumCulled=false;
}

function sweatshirt(body:THREE.SkinnedMesh){
 const source=body.geometry,sourcePositions=source.getAttribute('position');
 const sourceIndices=source.getAttribute('skinIndex'),sourceWeights=source.getAttribute('skinWeight');
 const candidates:number[]=[];
 for(let index=0;index<sourcePositions.count;index++)if(Math.abs(sourcePositions.getX(index))<24&&sourcePositions.getZ(index)>105&&sourcePositions.getZ(index)<167)candidates.push(index);
 // A straight, relaxed garment replaces the fitted torso silhouette. Each
 // new vertex inherits real skin weights from its nearest source torso point.
 const profiles=[
  [109,18.4,10.5,-4],[111,18.7,10.5,-4],[115,18.8,10.3,-4],
  [123,18.5,10.2,-4],[134,18.4,10.1,-4],[144,18.5,10,-4],
  [152,18.3,9.4,-3.8],[157,16.9,8.2,-3.3],[160,12.9,6.8,-2.8],
  [163,7,5,-2.4],[165.8,4.9,4.1,-2.3],
 ];
 const points:number[]=[],indices:number[]=[],weights:number[]=[],triangles:number[]=[];
 const sides=48;
 for(const [height,width,depth,center]of profiles){
  for(let side=0;side<sides;side++){
   const angle=side/sides*Math.PI*2,x=Math.cos(angle)*width,y=center+Math.sin(angle)*depth;
   points.push(x,y,height);
   let nearest=candidates[0],distance=Infinity;
   for(const candidate of candidates){
    const dx=sourcePositions.getX(candidate)-x,dy=sourcePositions.getY(candidate)-y,dz=sourcePositions.getZ(candidate)-height;
    const squared=dx*dx+dy*dy+dz*dz;
    if(squared<distance){distance=squared;nearest=candidate}
   }
   for(let component=0;component<4;component++){
    indices.push(sourceIndices.getComponent(nearest,component));
    weights.push(sourceWeights.getComponent(nearest,component));
   }
  }
 }
 for(let ring=0;ring<profiles.length-1;ring++)for(let side=0;side<sides;side++){
  const a=ring*sides+side,b=ring*sides+(side+1)%sides,c=a+sides,d=b+sides;
  triangles.push(a,b,c,b,d,c);
 }
 const geometry=new THREE.BufferGeometry();
 geometry.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
 geometry.setAttribute('skinIndex',new THREE.Uint16BufferAttribute(indices,4));
 geometry.setAttribute('skinWeight',new THREE.Float32BufferAttribute(weights,4));
 geometry.setIndex(triangles);geometry.computeVertexNormals();
 const shell=new THREE.SkinnedMesh(geometry,new THREE.MeshStandardMaterial({color:knit,roughness:1,side:THREE.DoubleSide}));
 shell.name='SignaRelaxedSweatshirt';shell.frustumCulled=false;
 shell.position.copy(body.position);shell.quaternion.copy(body.quaternion);shell.scale.copy(body.scale);
 shell.bindMode=body.bindMode;shell.bind(body.skeleton,body.bindMatrix);
 body.parent?.add(shell);
}

function ellipsoid(parent:THREE.Group,name:string,position:number[],scale:number[],material:THREE.Material){
 const mesh=new THREE.Mesh(new THREE.SphereGeometry(1,32,24),material);
 mesh.name=name;
 mesh.position.set(position[0],position[1],position[2]);
 mesh.scale.set(scale[0],scale[1],scale[2]);
 parent.add(mesh);
 return mesh;
}

function line(parent:THREE.Group,name:string,from:number[],to:number[],width:number,material:THREE.Material){
 const a=new THREE.Vector3(...from),b=new THREE.Vector3(...to);
 const mesh=new THREE.Mesh(new THREE.CylinderGeometry(width,width,a.distanceTo(b),12),material);
 mesh.name=name;
 mesh.position.copy(a).add(b).multiplyScalar(.5);
 mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),b.sub(a).normalize());
 parent.add(mesh);
}

function attachInWorld(root:THREE.Object3D,bone:THREE.Object3D,decoration:THREE.Group){
 root.add(decoration);
 root.updateMatrixWorld(true);
 bone.attach(decoration);
}

/** New interpreter styling on the unmodified source animation skeleton.
 * Head morph channels and every bone/track name remain available.
 */
export function createInterpreter(source:THREE.Object3D){
 const model=clone(source);
 model.traverse(object=>{
  if(object instanceof THREE.Mesh){
   if(object.name==='Strand008')object.visible=false;
   else restyleMesh(object);
  }
 });
 model.updateMatrixWorld(true);
 const body=model.getObjectByName('GaltisBody');
 if(body instanceof THREE.SkinnedMesh)sweatshirt(body);
 const head=model.getObjectByName('head');
 const chest=model.getObjectByName('spine_05_1');
 if(head){
  const style=new THREE.Group();style.name='SignaInterpreterHeadStyle';
  const hair=new THREE.MeshStandardMaterial({color:hairColor,roughness:.72});
  const softHair=new THREE.MeshStandardMaterial({color:'#3f354c',roughness:.78});
  const cap=new THREE.Mesh(new THREE.SphereGeometry(1,48,32,0,Math.PI*2,0,Math.PI*.59),hair);
  cap.name='SignaCroppedHair';cap.position.set(0,183.5,2.5);cap.scale.set(10.5,9.8,9.3);style.add(cap);
  ellipsoid(style,'SignaHairSweepA',[-6.4,190.1,7.7],[4.4,3.5,3.9],hair).rotation.z=-.3;
  ellipsoid(style,'SignaHairSweepB',[-2.7,191.7,8.6],[5,3.4,3.4],softHair).rotation.z=-.2;
  ellipsoid(style,'SignaHairSweepC',[2.1,191.3,8.5],[4.7,3,3.2],hair).rotation.z=-.2;
  ellipsoid(style,'SignaHairSweepD',[5.9,189.3,7.1],[3.8,3,3.8],hair);
  ellipsoid(style,'SignaSideburnL',[8.9,181.6,3.8],[1.4,4.2,3.9],hair);
  ellipsoid(style,'SignaSideburnR',[-8.9,181.6,3.8],[1.4,4.2,3.9],hair);
  const frameMaterial=new THREE.MeshStandardMaterial({color:'#34364b',roughness:.5,metalness:.1});
  for(const side of [-1,1]){
   const frame=new THREE.Mesh(new THREE.TorusGeometry(2.8,.14,12,48),frameMaterial);
   frame.name=side<0?'SignaGlassesR':'SignaGlassesL';
   frame.position.set(side*3.7,181.4,12.8);frame.scale.y=.87;style.add(frame);
   line(style,`SignaGlassesTemple${side}`,[side*6.5,181.4,12.8],[side*8,181.4,4],.12,frameMaterial);
  }
  line(style,'SignaGlassesBridge',[-.9,181.9,12.8],[.9,181.9,12.8],.12,frameMaterial);
  attachInWorld(model,head,style);
 }
 if(chest){
  const details=new THREE.Group();details.name='SignaInterpreterKnitDetails';
  const collar=new THREE.Mesh(new THREE.TorusGeometry(4.8,.56,12,64),new THREE.MeshStandardMaterial({color:'#3a4a65',roughness:1}));
  collar.name='SignaCrewneckCollar';collar.position.set(0,166.1,2.6);collar.rotation.x=Math.PI/2;collar.scale.set(1,.8,1);details.add(collar);
  attachInWorld(model,chest,details);
 }
 return model;
}
