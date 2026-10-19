export type CompositeFrame={caption:string;label:string;position:number;total:number;playing:boolean;error:string};
export type CompositeRecording={result:Promise<Blob>;finish:()=>void;cancel:()=>void};

const audioGraphs=new WeakMap<HTMLMediaElement,{context:AudioContext;source:MediaElementAudioSourceNode}>();
const MAX_RECORD_BYTES=256*1024*1024;

function requireRecordingSupport(){
 if(typeof MediaRecorder==='undefined'||typeof HTMLCanvasElement.prototype.captureStream!=='function'||typeof AudioContext==='undefined')throw new Error('Bu brauzer video yozishni qo‘llamaydi. Chrome yoki Edge orqali oching.');
}
// Call from the export click before awaiting a seek/paint. Browsers may require
// that audio activation starts while the click's user activation is still live.
export async function primeRecordingAudio(media:HTMLMediaElement):Promise<void>{
 requireRecordingSupport();
 let graph=audioGraphs.get(media);
 if(!graph){
  const context=new AudioContext();
  try{const source=context.createMediaElementSource(media);source.connect(context.destination);graph={context,source};audioGraphs.set(media,graph)}
  catch(cause){void context.close().catch(()=>{});throw cause}
 }
 if(graph.context.state!=='running')await graph.context.resume();
}

export function outputDimensions(media:HTMLMediaElement){
 const video=media instanceof HTMLVideoElement?media:null;
 const width=video?.videoWidth||1280,height=video?.videoHeight||720;
 const scale=Math.min(1,1280/Math.max(width,height));
 return {width:Math.max(2,Math.round(width*scale/2)*2),height:Math.max(2,Math.round(height*scale/2)*2)};
}
export function compositeLayout(width:number,height:number){
 const margin=Math.min(Math.max(8,Math.round(Math.min(width,height)*.025)),Math.min(width,height)*.1);
 const panelWidth=Math.max(1,Math.min(width-margin*2,Math.round(width*(width/height<1?.48:.32))));
 const panelHeight=Math.max(1,Math.min(height-margin*2,Math.round(panelWidth*1.10)));
 return {x:width-margin-panelWidth,y:height-margin-panelHeight,width:panelWidth,height:panelHeight,margin};
}
function contain(ctx:CanvasRenderingContext2D,image:CanvasImageSource,sw:number,sh:number,x:number,y:number,w:number,h:number){
 const scale=Math.min(w/sw,h/sh),dw=sw*scale,dh=sh*scale;
 ctx.drawImage(image,x+(w-dw)/2,y+(h-dh)/2,dw,dh);
}
function fitText(ctx:CanvasRenderingContext2D,text:string,width:number){
 let result=text;
 while(result.length>1&&ctx.measureText(result).width>width)result=result.slice(0,-1);
 return result===text?text:`${result.slice(0,-1)}…`;
}
export function drawComposite(ctx:CanvasRenderingContext2D,media:HTMLMediaElement,avatar:HTMLCanvasElement,frame:CompositeFrame){
 const {width,height}=ctx.canvas,box=compositeLayout(width,height);
 ctx.fillStyle='#1e1b2b';ctx.fillRect(0,0,width,height);
 if(media instanceof HTMLVideoElement&&media.readyState>=2){
  contain(ctx,media,media.videoWidth,media.videoHeight,0,0,width,height);
 }else{
  const gradient=ctx.createRadialGradient(width*.4,height*.4,0,width*.4,height*.4,width*.8);
  gradient.addColorStop(0,'#4b3965');gradient.addColorStop(1,'#1e1b2b');ctx.fillStyle=gradient;ctx.fillRect(0,0,width,height);
  ctx.textAlign='left';ctx.fillStyle='#e3d5ff';ctx.font=`600 ${Math.max(18,width*.035)}px Arial`;
  ctx.fillText('signa.',box.margin*2,height*.4);
  ctx.font=`${Math.max(12,width*.018)}px Arial`;ctx.fillStyle='#b9a6d1';ctx.fillText('Audio · ASL avatar',box.margin*2,height*.4+height*.06);
 }
 ctx.save();ctx.fillStyle='#f0effb';ctx.beginPath();ctx.roundRect(box.x,box.y,box.width,box.height,Math.max(6,width*.008));ctx.fill();ctx.clip();
 contain(ctx,avatar,avatar.width,avatar.height,box.x,box.y,box.width,box.height);
 ctx.restore();ctx.strokeStyle='#ffffff99';ctx.lineWidth=2;ctx.beginPath();ctx.roundRect(box.x,box.y,box.width,box.height,Math.max(6,width*.008));ctx.stroke();
 ctx.textAlign='center';ctx.font=`600 ${Math.max(9,width*.012)}px Arial`;
 if(frame.label){
  const label=fitText(ctx,frame.label,box.width-18),tw=ctx.measureText(label).width;
  ctx.fillStyle='#faf8fff2';ctx.beginPath();ctx.roundRect(box.x+(box.width-tw)/2-7,box.y+box.height-Math.max(24,height*.045),tw+14,Math.max(18,height*.032),8);ctx.fill();
  ctx.fillStyle='#564369';ctx.fillText(label,box.x+box.width/2,box.y+box.height-Math.max(11,height*.022));
 }
 if(frame.caption){
  const area=box.x-box.margin*2;
  ctx.font=`600 ${Math.max(13,width*.026)}px Arial`;const text=fitText(ctx,frame.caption,area-24),tw=ctx.measureText(text).width;
  const cx=area/2+box.margin,cy=height-box.margin-height*.045;
  ctx.fillStyle='#101018dc';ctx.beginPath();ctx.roundRect(cx-tw/2-12,cy-height*.04,tw+24,height*.065,7);ctx.fill();ctx.fillStyle='#fff';ctx.fillText(text,cx,cy+height*.007);
 }
 ctx.textAlign='left';ctx.font=`${Math.max(9,width*.011)}px Arial`;ctx.fillStyle='#ffffffb0';ctx.fillText('Signa · ASL avatar · tajribaviy ijro',box.margin,box.margin+Math.max(11,height*.02));
}

export async function createCompositeRecording(options:{media:HTMLMediaElement;avatar:()=>HTMLCanvasElement|null;frame:()=>CompositeFrame;onProgress:(fraction:number)=>void;signal:AbortSignal}):Promise<CompositeRecording>{
 requireRecordingSupport();
 const {media,avatar,frame,signal}=options;
 if(signal.aborted)throw new DOMException('Bekor qilindi','AbortError');
 const surface=document.createElement('canvas');Object.assign(surface,outputDimensions(media));
 const ctx=surface.getContext('2d',{alpha:false});if(!ctx)throw new Error('Video oynasi ochilmadi.');
 let graph=audioGraphs.get(media);
 let destination:MediaStreamAudioDestinationNode|undefined,videoStream:MediaStream|undefined,stream:MediaStream|undefined;
 let recorder:MediaRecorder,initialPosition=0;
 // Every setup stage can throw: canvas readback, audio routing, captureStream,
 // codec selection and recorder construction. Release whichever stage exists.
 function releaseResources(){
  if(graph&&destination){try{graph.source.disconnect(destination)}catch{ /* Already disconnected. */ }}
  const tracks=new Set([...videoStream?.getTracks()||[],...destination?.stream.getTracks()||[],...stream?.getTracks()||[]]);
  tracks.forEach(track=>{try{track.stop()}catch{ /* A failed track is already ended. */ }});
 }
 try{
  const initialAvatar=avatar();if(!initialAvatar)throw new Error('Avatar hali tayyor emas.');
  const initial=frame();initialPosition=initial.position;
  drawComposite(ctx,media,initialAvatar,initial);
  await primeRecordingAudio(media);graph=audioGraphs.get(media)!;
  if(signal.aborted)throw new DOMException('Bekor qilindi','AbortError');
  destination=graph.context.createMediaStreamDestination();graph.source.connect(destination);
  videoStream=surface.captureStream(30);
  stream=new MediaStream([...videoStream.getVideoTracks(),...destination.stream.getAudioTracks()]);
  const mime=['video/webm;codecs=vp9,opus','video/webm;codecs=vp8,opus','video/webm'].find(value=>MediaRecorder.isTypeSupported(value));
  recorder=new MediaRecorder(stream,{...(mime?{mimeType:mime}:{}),videoBitsPerSecond:3500000,audioBitsPerSecond:128000});
 }catch(cause){releaseResources();throw cause}
 let resolve!:(blob:Blob)=>void,reject!:(error:Error)=>void,raf=0,bytes=0,finished=false,settled=false;
 const startedAt=performance.now();let lastAdvanceAt=startedAt,lastPosition=initialPosition,hasPlayed=false;
 const chunks:BlobPart[]=[];
 const result=new Promise<Blob>((yes,no)=>{resolve=yes;reject=no});
 function cleanup(){cancelAnimationFrame(raf);signal.removeEventListener('abort',cancel);document.removeEventListener('visibilitychange',visibility);releaseResources()}
 function fail(error:Error){if(settled)return;settled=true;finished=true;cleanup();if(recorder.state!=='inactive'){try{recorder.stop()}catch{ /* Cleanup must still reject. */ }}reject(error)}
 function cancel(){fail(new DOMException('Video tayyorlash bekor qilindi.','AbortError'))}
 function finish(){if(finished||settled)return;finished=true;cancelAnimationFrame(raf);if(recorder.state==='inactive')fail(new Error('Video yozuvi boshlanmadi.'));else{try{recorder.stop()}catch(cause){fail(cause instanceof Error?cause:new Error('Video yozuvi yakunlanmadi.'))}}}
 function visibility(){if(document.visibilityState==='hidden')fail(new Error('Video yozuvi to‘xtadi. Sahifani ochiq qoldirib qayta tayyorlang.'))}
 recorder.ondataavailable=event=>{if(settled||!event.data.size)return;bytes+=event.data.size;if(bytes>MAX_RECORD_BYTES){fail(new Error('Video 256 MB chegarasiga yetdi. Qisqaroq fayl tanlang.'));return}chunks.push(event.data)};
 recorder.onerror=()=>fail(new Error('Brauzer videoni yoza olmadi. Qayta urinib ko‘ring.'));
 recorder.onstop=()=>{if(settled)return;settled=true;cleanup();try{const blob=new Blob(chunks,{type:recorder.mimeType||'video/webm'});if(!blob.size)reject(new Error('Video yozuvi bo‘sh chiqdi.'));else resolve(blob)}catch(cause){reject(cause instanceof Error?cause:new Error('Video fayli yaratilmadi.'))}};
 signal.addEventListener('abort',cancel,{once:true});document.addEventListener('visibilitychange',visibility);
 function tick(now:number){
  if(finished||settled)return;
  try{
   const current=frame(),canvas=avatar();
   if(current.error)throw new Error(current.error);
   if(!canvas)throw new Error('Avatar oynasi yopildi. Videoni qayta tayyorlang.');
   const atEnd=current.total>0&&current.position>=current.total-.002;
   if(current.playing)hasPlayed=true;
   if(!current.playing&&!atEnd&&(hasPlayed||now-startedAt>1000))throw new Error('Ijro to‘xtadi. Videoni qayta tayyorlang.');
   const advanced=current.position>lastPosition+.000001;
   if(advanced){lastAdvanceAt=now;lastPosition=current.position}
   // Deliberate source holds keep the virtual clock advancing. Only a frozen
   // shared clock (asset loading/buffering) pauses the recording itself.
   const waiting=!current.playing||(!advanced&&now-lastAdvanceAt>=300);
   if(waiting&&recorder.state==='recording')recorder.pause();
   else if(!waiting&&recorder.state==='paused')recorder.resume();
   drawComposite(ctx!,media,canvas,current);
   options.onProgress(current.total?Math.min(1,current.position/current.total):0);
   if(atEnd){finish();return}
   raf=requestAnimationFrame(tick);
  }catch(cause){fail(cause instanceof Error?cause:new Error('Video kadrini chizib bo‘lmadi.'))}
 }
 try{
  if(signal.aborted)throw new DOMException('Bekor qilindi','AbortError');
  if(document.visibilityState==='hidden')throw new Error('Video tayyorlash uchun sahifani ochiq qoldiring.');
  recorder.start(1000);raf=requestAnimationFrame(tick);
 }catch(cause){fail(cause instanceof Error?cause:new Error('Video yozuvi boshlanmadi.'))}
 return {result,finish,cancel};
}
