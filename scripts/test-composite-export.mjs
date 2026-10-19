import assert from 'node:assert/strict';
import {outputDimensions,compositeLayout,createCompositeRecording,primeRecordingAudio} from '../frontend/src/compositeExport.ts';

// Exercise geometry and recording orchestration without substituting an actual
// browser encode/decode test. The latter remains a separate acceptance check.
const saved=new Map();
function install(key,value){saved.set(key,globalThis[key]);globalThis[key]=value}
let now=0,nextRaf=1,raf=new Map(),captureFails=false,drawFails=false,constructorFails=false;
const allTracks=[],allGraphs=[],recorders=[];
class Track {constructor(kind){this.kind=kind;this.stopped=false;allTracks.push(this)}stop(){this.stopped=true}}
class Stream {constructor(tracks=[]){this.tracks=tracks}getTracks(){return this.tracks}getVideoTracks(){return this.tracks.filter(track=>track.kind==='video')}getAudioTracks(){return this.tracks.filter(track=>track.kind==='audio')}}
class Video {constructor(width=1920,height=1080){this.videoWidth=width;this.videoHeight=height;this.readyState=4}}
const context={canvas:null,fillRect(){},createRadialGradient(){return{addColorStop(){}}},fillText(){},save(){},restore(){},beginPath(){},roundRect(){},fill(){},clip(){},stroke(){},measureText(text){return{width:text.length*7}},drawImage(){if(drawFails)throw new DOMException('Unreadable surface','SecurityError')}};
class Canvas {constructor(){this.width=400;this.height=400}getContext(){return{...context,canvas:this}}captureStream(){if(captureFails)throw new DOMException('Capture blocked','SecurityError');return new Stream([new Track('video')])}}
class AudioContextMock {constructor(){this.destination={speaker:true};this.source=null;this.state='suspended';this.resumes=0;allGraphs.push(this)}createMediaElementSource(){this.source={destinations:new Set(),connect(destination){this.destinations.add(destination)},disconnect(destination){this.destinations.delete(destination)}};return this.source}resume(){this.state='running';this.resumes++;return Promise.resolve()}close(){this.state='closed';return Promise.resolve()}createMediaStreamDestination(){return{stream:new Stream([new Track('audio')])}}}
class Recorder {static isTypeSupported(){return true}constructor(stream,options){if(constructorFails)throw new Error('Unsupported codec');this.stream=stream;this.mimeType=options.mimeType;this.state='inactive';recorders.push(this)}start(){this.state='recording'}pause(){assert.equal(this.state,'recording');this.state='paused'}resume(){assert.equal(this.state,'paused');this.state='recording'}stop(){this.state='inactive';queueMicrotask(()=>{this.ondataavailable?.({data:new Blob(['encoded mock'])});this.onstop?.()})}}
const documentMock=new EventTarget();documentMock.visibilityState='visible';documentMock.createElement=()=>new Canvas();
install('HTMLVideoElement',Video);install('HTMLCanvasElement',Canvas);install('MediaStream',Stream);install('AudioContext',AudioContextMock);install('MediaRecorder',Recorder);install('document',documentMock);install('performance',{now:()=>now});
install('requestAnimationFrame',callback=>{const id=nextRaf++;raf.set(id,callback);return id});install('cancelAnimationFrame',id=>raf.delete(id));
function step(time){now=time;const callbacks=[...raf.values()];raf.clear();callbacks.forEach(callback=>callback(now))}
function parameters(media=new Video()){
 const state={caption:'Hello',label:'Hello',position:0,total:2,playing:false,error:''},controller=new AbortController(),avatar=new Canvas();
 return {state,controller,options:{media,avatar:()=>avatar,frame:()=>state,onProgress(){},signal:controller.signal}};
}
try{
 for(const [w,h] of [[1920,1080],[1080,1920],[640,480],[160,90],[4,2],[2,1280],[1280,2],[3840,2160],[0,0]]){
  const dimensions=outputDimensions(new Video(w,h));
  assert.ok(dimensions.width>=2&&dimensions.height>=2);assert.equal(dimensions.width%2,0);assert.equal(dimensions.height%2,0);
  assert.ok(Math.max(dimensions.width,dimensions.height)<=1280);
  const box=compositeLayout(dimensions.width,dimensions.height);
  assert.ok(Object.values(box).every(Number.isFinite));assert.ok(box.x>=0&&box.y>=0&&box.width>0&&box.height>0);
  assert.ok(box.x+box.width<=dimensions.width&&box.y+box.height<=dimensions.height);
 }
 assert.deepEqual(outputDimensions({}),{width:1280,height:720},'Audio has a 16:9 video surface');

 const sample=parameters(),graphsBefore=allGraphs.length;
 await primeRecordingAudio(sample.options.media);await primeRecordingAudio(sample.options.media);
 const recording=await createCompositeRecording(sample.options),recorder=recorders.at(-1),graph=allGraphs.at(-1);
 assert.equal(allGraphs.length,graphsBefore+1,'Priming and recording reuse the same media-element source');
 assert.equal(graph.resumes,1,'The click-prime resumes audio once; a running context stays active');
 const result=recording.result;
 step(16);assert.equal(recorder.state,'paused','Wait for shared playback startup without recording idle preroll');
 sample.state.playing=true;sample.state.position=.02;step(32);assert.equal(recorder.state,'recording');
 step(400);assert.equal(recorder.state,'paused','A frozen virtual clock pauses the recorder');
 sample.state.position=.04;step(416);assert.equal(recorder.state,'recording','An advancing virtual clock resumes recording');
 sample.state.position=.08;step(450);assert.equal(recorder.state,'recording','A deliberate media hold still advances the shared clock');
 sample.state.position=2;sample.state.playing=false;step(500);
 const blob=await result;assert.ok(blob.size>0);assert.equal(recorder.state,'inactive');
 assert.equal(graph.source.destinations.size,1,'Release only the recording destination, retaining normal speaker routing');
 assert.ok(recorder.stream.getTracks().every(track=>track.stopped));assert.equal(raf.size,0);

 const tracksBefore=allTracks.length;captureFails=true;
 await assert.rejects(createCompositeRecording(parameters().options),/Capture blocked/);captureFails=false;
 assert.ok(allTracks.slice(tracksBefore).every(track=>track.stopped),'Failed capture releases the already-created audio track');
 assert.equal(allGraphs.at(-1).source.destinations.size,1);

 const setupTracks=allTracks.length;constructorFails=true;
 await assert.rejects(createCompositeRecording(parameters().options),/Unsupported codec/);constructorFails=false;
 assert.ok(allTracks.slice(setupTracks).every(track=>track.stopped),'Failed codec construction releases both capture tracks');

 const broken=parameters(),brokenRecording=await createCompositeRecording(broken.options);
 const brokenResult=assert.rejects(brokenRecording.result,/Unreadable surface/);drawFails=true;step(520);drawFails=false;await brokenResult;
 assert.equal(raf.size,0);assert.ok(recorders.at(-1).stream.getTracks().every(track=>track.stopped));

 const aborted=parameters(),abortRecording=await createCompositeRecording(aborted.options);
 const abortResult=assert.rejects(abortRecording.result,error=>error.name==='AbortError');aborted.controller.abort();await abortResult;
 assert.equal(raf.size,0);assert.ok(recorders.at(-1).stream.getTracks().every(track=>track.stopped));

 const halted=parameters(),haltRecording=await createCompositeRecording(halted.options);
 const haltResult=assert.rejects(haltRecording.result,/Ijro to‘xtadi/);halted.state.playing=true;halted.state.position=.1;step(540);halted.state.playing=false;step(560);await haltResult;
 assert.equal(raf.size,0);
 console.log('PASS: output dimensions/layout, startup and frozen-clock recorder pause/resume, intentional holds, final chunks, setup/draw/abort/playback-stop cleanup. Mock lifecycle only; browser encoding requires separate verification.');
}finally{for(const [key,value] of saved){if(value===undefined)delete globalThis[key];else globalThis[key]=value}}
