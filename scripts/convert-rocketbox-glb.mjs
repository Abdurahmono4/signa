import fs from 'node:fs';
import * as THREE from '../frontend/node_modules/three/build/three.module.js';
import {FBXLoader} from '../frontend/node_modules/three/examples/jsm/loaders/FBXLoader.js';
import {GLTFExporter} from '../frontend/node_modules/three/examples/jsm/exporters/GLTFExporter.js';
globalThis.FileReader=class{readAsArrayBuffer(blob){blob.arrayBuffer().then(result=>{this.result=result;this.onloadend?.()})}readAsDataURL(blob){blob.arrayBuffer().then(result=>{this.result=`data:${blob.type};base64,${Buffer.from(result).toString('base64')}`;this.onloadend?.()})}};
THREE.TextureLoader.prototype.load=function(){return new THREE.Texture()};
const base=new URL('../assets/avatars/rocketbox-female-01/',import.meta.url);
const bytes=fs.readFileSync(new URL('female.fbx',base));
const model=new FBXLoader().parse(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
model.traverse(o=>{if(o.isMesh){o.material=(Array.isArray(o.material)?o.material:[o.material]).map(m=>new THREE.MeshStandardMaterial({name:m.name,roughness:.82,metalness:0,side:THREE.DoubleSide}));}});
model.traverse(o=>{if(!o.isMesh)return;
 const keep=Object.entries(o.morphTargetDictionary||{}).filter(([name])=>name.includes('.AK_'));
 for(const key of Object.keys(o.geometry.morphAttributes))o.geometry.morphAttributes[key]=keep.map(([,index])=>o.geometry.morphAttributes[key][index]);
 o.morphTargetDictionary=Object.fromEntries(keep.map(([name],i)=>[name.replace('blendShape1.',''),i]));o.morphTargetInfluences=keep.map(()=>0);
 const uv=o.geometry.attributes.uv;if(uv)for(let i=0;i<uv.count;i++)uv.setY(i,1-uv.getY(i));
});
model.animations=[];model.scale.setScalar(.01);model.updateMatrixWorld(true);
const raw=await new GLTFExporter().parseAsync(model,{binary:true,onlyVisible:true});
const input=Buffer.from(raw),jsonLength=input.readUInt32LE(12);
const doc=JSON.parse(input.subarray(20,20+jsonLength).toString());
const binStart=20+jsonLength,binLength=input.readUInt32LE(binStart);
const parts=[input.subarray(binStart+8,binStart+8+binLength)];let offset=binLength;
doc.images=[];doc.textures=[];doc.samplers=[{magFilter:9729,minFilter:9987,wrapS:10497,wrapT:10497}];
for(const name of ['f001_body_color.png','f001_head_color.png','f001_opacity_color.png']){
 const image=fs.readFileSync(new URL(name,base));
 const pad=(4-offset%4)%4;if(pad){parts.push(Buffer.alloc(pad));offset+=pad}
 const view=doc.bufferViews.length;doc.bufferViews.push({buffer:0,byteOffset:offset,byteLength:image.length});parts.push(image);offset+=image.length;
 doc.images.push({bufferView:view,mimeType:'image/png'});doc.textures.push({sampler:0,source:doc.images.length-1});
}
for(const material of doc.materials){
 const index=material.name.includes('head')?1:material.name.includes('opacity')?2:0;
 material.pbrMetallicRoughness.baseColorTexture={index};
 if(index===2){material.alphaMode='MASK';material.alphaCutoff=.45}
}
doc.buffers[0].byteLength=offset;
doc.asset.copyright='Microsoft Rocketbox, MIT. Source: https://github.com/microsoft/Microsoft-Rocketbox';
doc.asset.extras={adaptation:'FBX converted to GLB with original diffuse textures; no sign-language animation supplied.'};
let json=Buffer.from(JSON.stringify(doc));json=Buffer.concat([json,Buffer.alloc((4-json.length%4)%4,32)]);
let bin=Buffer.concat(parts);bin=Buffer.concat([bin,Buffer.alloc((4-bin.length%4)%4)]);
const header=Buffer.alloc(12);header.writeUInt32LE(0x46546c67,0);header.writeUInt32LE(2,4);header.writeUInt32LE(12+8+json.length+8+bin.length,8);
const j=Buffer.alloc(8);j.writeUInt32LE(json.length);j.writeUInt32LE(0x4e4f534a,4);
const b=Buffer.alloc(8);b.writeUInt32LE(bin.length);b.writeUInt32LE(0x004e4942,4);
fs.writeFileSync(new URL('female.glb',base),Buffer.concat([header,j,json,b,bin]));
console.log(JSON.stringify({bytes:header.readUInt32LE(8),skins:doc.skins.length,images:doc.images.length,meshes:doc.meshes.length}));
