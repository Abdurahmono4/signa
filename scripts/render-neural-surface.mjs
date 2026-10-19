import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import assert from 'node:assert/strict';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {GLTFLoader} from '../frontend/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
import {createInterpreter} from '../frontend/src/interpreter.ts';
import {createNeuralClip,validateNeuralMotion} from '../frontend/src/neuralMotion.ts';
import {sampleNeuralSigningEnvelope} from '../frontend/src/neuralFraming.ts';
import {INTERPRETER_FOV,neuralInterpreterCamera} from '../frontend/src/framing.ts';

// Offline software rasterization for inspecting actual deformed mesh geometry.
// No WebGL, browser, fabricated motion, or external model assets are used.
const [input,output,requestedFrame='0',requestedAngle='0']=process.argv.slice(2);
assert.ok(input&&output,'Usage: node scripts/render-neural-surface.mjs actual-motion.json output.png [frame] [angleRadians]');
const motion=JSON.parse(fs.readFileSync(input,'utf8'));assert.equal(motion.format,'signa-madis-133-v1');
const frames=validateNeuralMotion(motion),frame=Number(requestedFrame),angle=Number(requestedAngle);
assert.ok(Number.isInteger(frame)&&frame>=0&&frame<frames.length&&Number.isFinite(angle));
const bytes=fs.readFileSync(new URL('../frontend/public/avatar/galtis.glb',import.meta.url));
const source=(await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'')).scene;
const model=createInterpreter(source),clip=createNeuralClip(model,motion),mixer=new THREE.AnimationMixer(model),action=mixer.clipAction(clip);
// Use the same mounted hierarchy as Avatar3D, including its unit conversion.
// Rendering only an unmounted asset hid a double-scale camera bug in the UI.
const stage=new THREE.Group();stage.scale.setScalar(.01);stage.rotation.y=angle;stage.add(model);
action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();mixer.setTime(frame/motion.fps);stage.updateMatrixWorld(true);
const batchRoot=path.dirname(path.dirname(input));
const batch=fs.readdirSync(batchRoot,{withFileTypes:true}).filter(entry=>entry.isDirectory()).map(entry=>path.join(batchRoot,entry.name,'motion.json')).filter(file=>fs.existsSync(file)).map(file=>JSON.parse(fs.readFileSync(file,'utf8')));
const envelope=sampleNeuralSigningEnvelope(model,batch.length?batch:[motion]);
const width=900,height=1200,camera=new THREE.PerspectiveCamera(INTERPRETER_FOV,width/height,.1,100);
const fit=neuralInterpreterCamera(envelope,width/height,angle);
camera.position.set(fit.x,fit.targetY,fit.distance);camera.lookAt(fit.x,fit.targetY,0);camera.updateMatrixWorld(true);
const pixels=new Uint8Array(width*height*4),depth=new Float64Array(width*height).fill(Infinity);
for(let pixel=0;pixel<width*height;pixel++){pixels[pixel*4]=21;pixels[pixel*4+1]=26;pixels[pixel*4+2]=43;pixels[pixel*4+3]=255}
const light=new THREE.Vector3(-.4,.8,1).normalize(),v1=new THREE.Vector3(),v2=new THREE.Vector3(),normal=new THREE.Vector3(),color=new THREE.Color();let triangles=0;
const srgb=value=>Math.round(THREE.MathUtils.clamp(value<=.0031308?value*12.92:1.055*Math.pow(value,1/2.4)-.055,0,1)*255);
function drawTriangle(points,shade){
 const projected=points.map(point=>point.clone().project(camera));if(projected.some(point=>point.z<-1||point.z>1))return;
 const screen=projected.map(point=>({x:(point.x+1)*width/2,y:(1-point.y)*height/2,z:point.z}));
 const [a,b,c]=screen,area=(b.y-c.y)*(a.x-c.x)+(c.x-b.x)*(a.y-c.y);if(Math.abs(area)<1e-9)return;
 const x0=Math.max(0,Math.floor(Math.min(a.x,b.x,c.x))),x1=Math.min(width-1,Math.ceil(Math.max(a.x,b.x,c.x)));
 const y0=Math.max(0,Math.floor(Math.min(a.y,b.y,c.y))),y1=Math.min(height-1,Math.ceil(Math.max(a.y,b.y,c.y)));
 for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){
  const p=((b.y-c.y)*(x+.5-c.x)+(c.x-b.x)*(y+.5-c.y))/area,q=((c.y-a.y)*(x+.5-c.x)+(a.x-c.x)*(y+.5-c.y))/area,r=1-p-q;
  if(p<0||q<0||r<0)continue;const z=p*a.z+q*b.z+r*c.z,index=y*width+x;if(z>=depth[index])continue;depth[index]=z;
  pixels[index*4]=shade[0];pixels[index*4+1]=shade[1];pixels[index*4+2]=shade[2];
 }
 triangles++;
}
model.traverse(object=>{
 if(!object.isMesh||!object.visible)return;
 if(object.isSkinnedMesh)object.skeleton.update();
 const geometry=object.geometry,attribute=geometry.attributes.position,colors=geometry.attributes.color,indices=geometry.index;
 const transformed=Array.from({length:attribute.count},(_,vertex)=>object.getVertexPosition(vertex,new THREE.Vector3()).applyMatrix4(object.matrixWorld));
 const count=indices?indices.count:attribute.count;
 for(let index=0;index<count;index+=3){
  const ids=[0,1,2].map(offset=>indices?indices.getX(index+offset):index+offset),points=ids.map(id=>transformed[id]);
  normal.crossVectors(v1.subVectors(points[1],points[0]),v2.subVectors(points[2],points[0])).normalize();
  const brightness=.34+.66*Math.max(0,normal.dot(light));
  color.copy((Array.isArray(object.material)?object.material[0]:object.material)?.color||new THREE.Color('#aaaaaa'));
  if(colors){const mean=ids.map(id=>new THREE.Color().fromBufferAttribute(colors,id));color.multiply(mean[0].add(mean[1]).add(mean[2]).multiplyScalar(1/3))}
  drawTriangle(points,color.multiplyScalar(brightness).toArray().map(srgb));
 }
});
function crc32(bytes){let crc=-1;for(const byte of bytes){crc^=byte;for(let bit=0;bit<8;bit++)crc=(crc>>>1)^((crc&1)?0xedb88320:0)}return (crc^-1)>>>0}
function chunk(type,data){const tag=Buffer.from(type),length=Buffer.alloc(4),crc=Buffer.alloc(4);length.writeUInt32BE(data.length);crc.writeUInt32BE(crc32(Buffer.concat([tag,data])));return Buffer.concat([length,tag,data,crc])}
const raw=Buffer.alloc((width*4+1)*height);for(let row=0;row<height;row++)Buffer.from(pixels.buffer,row*width*4,width*4).copy(raw,row*(width*4+1)+1);
const ihdr=Buffer.alloc(13);ihdr.writeUInt32BE(width,0);ihdr.writeUInt32BE(height,4);ihdr[8]=8;ihdr[9]=6;
fs.writeFileSync(output,Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',ihdr),chunk('tEXt',Buffer.from(`Description\0Actual MaDiS generated features; frame ${frame}/${frames.length}; approximate Galtis retarget. Missing SMPL-X hand means and face mapping. Not linguistic validation.`)),chunk('IDAT',zlib.deflateSync(raw)),chunk('IEND',Buffer.alloc(0))]));
console.log(JSON.stringify({output,frame,time:frame/motion.fps,triangles,method:'offline software rasterization of actual skinned vertices; technical inspection only'}));
