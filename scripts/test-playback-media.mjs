import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
import * as playback from '../frontend/src/playback.ts';

// Exercise the real hook against a deterministic HTMLMediaElement/RAF boundary.
// A minimal hook host keeps the test independent of a browser or a DOM emulator.
function host(plan){
 const cells=[],frames=new Map(),seeks=[];let cursor=0,dirty=true,clock=0,nextFrame=0,result,sourceTime=0;
 const media=new EventTarget();
 Object.assign(media,{readyState:4,seeking:false,ended:false,paused:true,
  play(){this.paused=false;return Promise.resolve()},pause(){this.paused=true}});
 Object.defineProperty(media,'currentTime',{get(){return sourceTime},set(value){
  seeks.push({from:sourceTime,to:value,time:clock/1000});sourceTime=value;
  if(value<(plan?.media_duration??Infinity))media.ended=false;
 }});
 const ref={current:media};
 const same=(left,right)=>left&&right&&left.length===right.length&&left.every((value,index)=>Object.is(value,right[index]));
 const pending=[];
 const hooks={
  useRef(value){const index=cursor++;return cells[index]??(cells[index]={current:value})},
  useState(value){const index=cursor++;if(!cells[index])cells[index]={value};return [cells[index].value,next=>{
   const resolved=typeof next==='function'?next(cells[index].value):next;
   if(!Object.is(cells[index].value,resolved)){cells[index].value=resolved;dirty=true}
  }]},
  useCallback(callback,deps){const index=cursor++;if(!same(cells[index]?.deps,deps))cells[index]={callback,deps};return cells[index].callback},
  useEffect(effect,deps){const index=cursor++;if(!same(cells[index]?.deps,deps)){
   const previous=cells[index];cells[index]={deps,cleanup:previous?.cleanup};
   pending.push(()=>{cells[index].cleanup?.();cells[index].cleanup=effect()});
  }},
 };
 const compiled=ts.transpileModule(fs.readFileSync(new URL('../frontend/src/useInterpreterPlayback.ts',import.meta.url),'utf8'),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS},
 }).outputText;
 const module={exports:{}};
 vm.runInNewContext(compiled,{exports:module.exports,module,
  require(name){if(name==='react')return hooks;if(name==='./playback')return playback;throw new Error(`Unexpected dependency: ${name}`)},
  performance:{now:()=>clock},requestAnimationFrame(callback){const id=++nextFrame;frames.set(id,callback);return id},
  cancelAnimationFrame(id){frames.delete(id)},
 });
 function flush(){
  let turns=0;
  while(dirty){assert.ok(++turns<30,'Hook state must settle');dirty=false;cursor=0;
   result=module.exports.useInterpreterPlayback(plan,ref);
   for(const effect of pending.splice(0))effect();
  }
  return result;
 }
 async function settle(){for(let turn=0;turn<8;turn++){await Promise.resolve();flush()}}
 async function advance(seconds,{frameStep=.025,mediaRate=1}={}){
  for(let remaining=seconds;remaining>1e-8;){
   const delta=Math.min(frameStep,remaining);remaining-=delta;
   if(!media.paused&&!media.seeking&&media.readyState>=3&&!media.ended){
    // The media hardware clock advances independently of RAF and never seeks.
    sourceTime=Math.min(plan?.media_duration??Infinity,sourceTime+delta*mediaRate);
    if(sourceTime>=(plan?.media_duration??Infinity)){
     media.ended=true;media.paused=true;media.dispatchEvent(new Event('ended'));
    }
   }
   clock+=delta*1000;
   const callbacks=[...frames.values()];frames.clear();for(const callback of callbacks)callback(clock);
   flush();await settle();
  }
  return result;
 }
 flush();
 return {media,seeks,get value(){return flush()},call(name,...args){result[name](...args);flush()},advance,settle,
  emit(name){media.dispatchEvent(new Event(name));flush()},
  changePlan(next){plan=next;dirty=true;flush()},
  dispose(){for(const cell of cells)cell?.cleanup?.();frames.clear()},
 };
}

const clip={id:'hello',phrase:'Hello',duration:1,animation_asset:'hello',keyframes:[],status:'source',source:'Scheduling fixture',license:'CC0'};
const item=(sourceStart,sourceEnd,start,clipValue=null)=>{
 const duration=clipValue?.duration??sourceEnd-sourceStart,slot=Math.max(duration,sourceEnd-sourceStart);
 return {segment_index:0,start:sourceStart,end:sourceEnd,text:clipValue?'Hello':'unknown',status:clipValue?'source_preview':'missing',sync_status:'missing',
  timing:'aligned',word_count:1,clip:clipValue,media_start:sourceStart,media_end:sourceEnd,media_play_start:sourceStart,media_play_end:sourceEnd,
  duration,slot_duration:slot,hold_duration:slot-(sourceEnd-sourceStart),playback_start:start,playback_end:start+slot};
};
const plan={job_id:'fixture',revision:1,mode:'dictionary_assistance',playback:'paced',language:'ASL',input_language:'en',complete_translation:false,
 source_preview_enabled:true,media_duration:1.25,playback_duration:2,hold_duration:.75,items:[item(0,.25,0,clip),item(.25,1.25,1)],
 playable_signs:1,matched:0,source_previews:1,total_words:2,signed_words:1,missing_words:['unknown'],limitations:[]};

const player=host(plan);player.call('setAvatarReady',true);player.call('play');await player.settle();
assert.equal(player.media.paused,false,'A user play request starts source media');
await player.advance(.15);assert.ok(player.value.position>.1);
player.call('pause');const pausedAt=player.value.position;await player.advance(.2);
assert.equal(player.value.position,pausedAt);assert.equal(player.media.paused,true,'Pause stops both source and avatar clock');
player.call('seek',.8);assert.equal(player.media.currentTime,.25);assert.equal(player.media.paused,true);
player.call('play');await player.advance(.1);assert.equal(player.value.isHolding,true);assert.equal(player.media.paused,true);
await player.advance(.2);assert.ok(player.value.position>=1);assert.equal(player.media.paused,false,'Media resumes after a sign hold');

player.media.readyState=4;player.emit('stalled');const stalledAt=player.value.position;
await player.advance(.1);assert.ok(player.value.position>stalledAt,'Network stalled must not freeze an already buffered file');
player.media.readyState=2;player.emit('waiting');const waitingAt=player.value.position;
await player.advance(.1);assert.equal(player.value.position,waitingAt,'A real buffer wait freezes the shared clock');
player.media.readyState=4; // Recovery must work even if a browser omits a second canplay event.
await player.advance(.1);assert.ok(player.value.position>waitingAt,'Ready data releases a previous wait without an event latch');

player.call('seek',.1);player.call('setAvatarReady',false);const loadingAt=player.value.position;
await player.advance(.1);assert.equal(player.value.position,loadingAt);assert.equal(player.media.paused,true);
player.call('setAvatarReady',true);await player.advance(.1);assert.ok(player.value.position>loadingAt,'Avatar loading gates media until the motion is ready');
player.call('reset');assert.equal(player.value.position,0);assert.equal(player.value.playing,false);assert.equal(player.media.currentTime,0);

player.media.play=()=>Promise.reject(Object.assign(new Error('Activation required'),{name:'NotAllowedError'}));
player.call('play');await player.settle();assert.equal(player.value.playing,false);assert.match(player.value.error,/bloklandi/);
player.call('clearError');assert.equal(player.value.error,'');
let rejectPrevious;
player.media.play=()=>new Promise((resolve,reject)=>{rejectPrevious=reject});
player.call('play');player.call('pause');rejectPrevious(new Error('Play interrupted by pause'));await player.settle();
assert.equal(player.value.error,'','A stale play rejection must not replace the current state');

player.media.play=function(){this.paused=false;return Promise.resolve()};
player.call('play');await player.settle();player.call('seek',1.95);await player.advance(.15);
assert.equal(player.value.position,2);assert.equal(player.value.playing,false);assert.equal(player.media.paused,true);
player.call('play');await player.settle();assert.equal(player.value.position,0,'Replay resets the completed schedule');
player.changePlan(null);assert.equal(player.value.playing,false);assert.equal(player.value.position,0);assert.equal(player.media.paused,true);
player.dispose();

// A real media clock keeps running while the main thread misses RAF callbacks.
// The old capped RAF clock fell behind, then repeatedly sought source audio
// backwards. Exercise a 21.0155-second source across many caption boundaries.
const sourceDuration=21.0155,wordCount=160;
const continuous={...plan,media_duration:sourceDuration,playback_duration:sourceDuration,hold_duration:0,
 items:Array.from({length:wordCount},(_,i)=>item(sourceDuration*i/wordCount,sourceDuration*(i+1)/wordCount,sourceDuration*i/wordCount))};
const delayed=host(continuous);delayed.call('setAvatarReady',true);delayed.call('play');await delayed.settle();
await delayed.advance(10.5,{frameStep:.35});
assert.ok(Math.abs(delayed.value.position-delayed.media.currentTime)<1e-9,'Delayed RAF must follow source time across multiple word boundaries');
await delayed.advance(sourceDuration-10.5,{frameStep:.35});
assert.equal(delayed.value.position,sourceDuration,'A 21.0155-second source completes without RAF-induced extra duration');
assert.equal(delayed.value.playing,false);assert.deepEqual(delayed.seeks,[],'Ordinary continuous playback never seeks or repeats source audio');
delayed.dispose();

const stoppedClock=host(continuous);stoppedClock.call('play');await stoppedClock.settle();
await stoppedClock.advance(.6,{mediaRate:0});
assert.equal(stoppedClock.value.position,0,'Ready media with an unchanged hardware clock must not advance or trigger a seek');
assert.deepEqual(stoppedClock.seeks,[]);
await stoppedClock.advance(.4,{frameStep:.2});
assert.ok(Math.abs(stoppedClock.value.position-.4)<1e-9,'Advancement resumes from the real media time');
stoppedClock.dispose();

const holdClock=host(plan);holdClock.call('setAvatarReady',true);holdClock.call('play');await holdClock.settle();
await holdClock.advance(.3,{frameStep:.15});
assert.equal(holdClock.media.currentTime,.25,'An intentional hold aligns the source boundary once');
assert.equal(holdClock.media.paused,true);assert.equal(holdClock.value.position,.25);
const holdSeeks=holdClock.seeks.length;
await holdClock.advance(.5,{frameStep:.25});
assert.equal(holdClock.value.position,.75,'Only a deliberate hold uses elapsed wall time');
assert.equal(holdClock.media.currentTime,.25);assert.equal(holdClock.seeks.length,holdSeeks,'A hold does not issue repeated seeks');
await holdClock.advance(.25,{frameStep:.25});
assert.equal(holdClock.value.position,1);assert.equal(holdClock.media.paused,false,'Source resumes after the whole sign hold');
holdClock.dispose();
console.log('PASS: media-master timing across 21.0155s/160 words with delayed RAF and zero seeks, stopped hardware clock, deliberate hold clock, lifecycle, pause/seek/reset, buffering, readiness, rejected play, completion and replay.');
