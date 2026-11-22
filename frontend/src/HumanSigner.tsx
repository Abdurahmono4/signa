import {useEffect,useRef,useState} from 'react';
import type {AvatarHandle,Item} from './Avatar';
export type HumanItem=Item&{video_url?:string|null};
type Props={time:number;items:HumanItem[];playing:boolean;onReady:(h:AvatarHandle|null)=>void;onError:(s:string)=>void;cropMode?:'center'|'full';removeGreen?:boolean};
function drawSigner(ctx:CanvasRenderingContext2D,v:HTMLVideoElement,cropMode='center',removeGreen=true){
 ctx.clearRect(0,0,384,512);
 if(v.readyState<2)return;
 // Front-facing recordings have a wide green-screen surround. Center crop
 // preserves the vertical signing space while making the signer readable.
 if(cropMode==='full'){
  const scale=Math.min(384/v.videoWidth,512/v.videoHeight),w=v.videoWidth*scale,h=v.videoHeight*scale;
  ctx.drawImage(v,(384-w)/2,(512-h)/2,w,h);
 }else{
  const cropWidth=Math.min(v.videoWidth,v.videoHeight*384/512);
  ctx.drawImage(v,(v.videoWidth-cropWidth)/2,0,cropWidth,v.videoHeight,0,0,384,512);
 }
 if(!removeGreen)return;
 const image=ctx.getImageData(0,0,384,512),d=image.data;
 for(let i=0;i<d.length;i+=4){
  const green=d[i+1]-Math.max(d[i],d[i+2]);
  if(d[i+1]>60&&green>8)d[i+3]=Math.round(255*Math.max(0,1-(green-8)/12));
 }
 ctx.putImageData(image,0,0);
}
export function HumanSigner({time,items,playing,onReady,onError,cropMode='center',removeGreen=true}:Props){
 const video=useRef<HTMLVideoElement|null>(null),exporting=useRef(false);
 const preview=useRef<HTMLCanvasElement|null>(null);
 const [active,setActive]=useState(false);
 const item=items.find(s=>s.supported&&s.video_url&&time>=s.start&&time<s.end);
 useEffect(()=>{
  let frame=0,lastTime=-1,lastSource='',lastDraw=0;
  const draw=(now:number)=>{const v=video.current,ctx=preview.current?.getContext('2d',{willReadFrequently:true});if(v&&v.readyState>=2&&ctx&&!exporting.current&&now-lastDraw>=1000/24&&(v.currentTime!==lastTime||v.currentSrc!==lastSource)){drawSigner(ctx,v,cropMode,removeGreen);lastTime=v.currentTime;lastSource=v.currentSrc;lastDraw=now}frame=requestAnimationFrame(draw)};
  frame=requestAnimationFrame(draw);return()=>cancelAnimationFrame(frame);
 },[cropMode,removeGreen]);
 useEffect(()=>{
  const v=video.current;if(!v||exporting.current)return;
  if(!item?.video_url){v.pause();setActive(false);return}
  setActive(true);
  const target=Math.max(0,(time-item.start)/(item.end-item.start)*(item.duration_ms||0)/1000);
  const sync=()=>{
   if(Math.abs(v.currentTime-target)>.15)v.currentTime=Math.min(target,Math.max(0,v.duration-.04));
   v.playbackRate=Math.max(.5,Math.min(2,(item.duration_ms||1000)/1000/(item.end-item.start)));
   if(playing)void v.play().catch(()=>{});else v.pause();
  };
  if(v.getAttribute('src')!==item.video_url){v.src=item.video_url;v.addEventListener('loadeddata',sync,{once:true});v.load()}else if(v.readyState>=2)sync();
 },[item?.video_url,time,playing]);
 useEffect(()=>{
  const canvas=document.createElement('canvas');canvas.width=384;canvas.height=512;
  const ctx=canvas.getContext('2d',{willReadFrequently:true})!;
  onReady({capture:async(t,sequence)=>{
   const v=video.current;if(!v)throw Error('Tarjimon oynasi ochilmadi');
   exporting.current=true;v.pause();ctx.clearRect(0,0,384,512);
   try{
    const source=(sequence as HumanItem[]).find(s=>s.supported&&s.video_url&&t>=s.start&&t<s.end);
    if(source?.video_url){
     if(v.getAttribute('src')!==source.video_url||v.readyState<2){
      await new Promise<void>((resolve,reject)=>{
       const timer=setTimeout(()=>{cleanup();reject(Error('Tarjimon klipi yuklanmadi'))},15000);
       const loaded=()=>{cleanup();resolve()};const failed=()=>{cleanup();reject(Error('Tarjimon klipi ochilmadi'))};
       const cleanup=()=>{clearTimeout(timer);v.removeEventListener('loadeddata',loaded);v.removeEventListener('error',failed)};
       v.addEventListener('loadeddata',loaded);v.addEventListener('error',failed);v.src=source.video_url!;v.load();
      });
     }
     const target=Math.max(0,Math.min(v.duration-.04,(t-source.start)/(source.end-source.start)*(source.duration_ms||0)/1000));
     if(Math.abs(v.currentTime-target)>.015)await new Promise<void>((resolve,reject)=>{
      const timer=setTimeout(()=>{v.removeEventListener('seeked',done);reject(Error('Video vaqti tanlanmadi'))},10000);
      const done=()=>{clearTimeout(timer);resolve()};v.addEventListener('seeked',done,{once:true});v.currentTime=target;
     });
     drawSigner(ctx,v,cropMode,removeGreen);
    }
    return await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(Error('Kadr yozilmadi')),'image/png'));
   }finally{exporting.current=false}
  }});
  return()=>onReady(null);
 },[onReady,cropMode,removeGreen]);
 return <div className="human-signer"><video ref={video} muted playsInline preload="auto" style={{position:'absolute',width:1,height:1,opacity:0}} onError={()=>onError('Tarjimon manba videosi ochilmadi.')}/><canvas ref={preview} width={384} height={512} style={{width:'100%',height:'100%',visibility:active?'visible':'hidden'}}/>{!active&&<div className="signer-placeholder"><span>ASL</span><strong>Tarjimon videosi</strong><p>Mos to‘liq ibora aniqlanganda shu yerda ko‘rsatiladi.</p></div>}</div>;
}
