import assert from 'node:assert/strict';
import {advancePlaybackPosition,clampPlaybackPosition,getPlaybackFrame} from '../frontend/src/playback.ts';

const clip={id:'hello',phrase:'Hello',duration:2,animation_asset:'hello',keyframes:[],status:'source',source:'Synthetic scheduling fixture',license:'CC0'};
function item(sourceStart,sourceEnd,playbackStart,clipValue=null,text=''){
 const mediaSpan=sourceEnd-sourceStart,duration=clipValue?.duration??mediaSpan,slot=Math.max(mediaSpan,duration);
 return {segment_index:0,start:sourceStart,end:sourceEnd,text,status:clipValue?'source_preview':text?'missing':'gap',sync_status:'missing',
  timing:'aligned',word_count:text?1:0,clip:clipValue,media_start:sourceStart,media_end:sourceEnd,
  media_play_start:sourceStart,media_play_end:sourceEnd,duration,slot_duration:slot,hold_duration:Math.max(0,duration-mediaSpan),
  playback_start:playbackStart,playback_end:playbackStart+slot};
}
const plan={job_id:'fixture',revision:1,mode:'dictionary_assistance',playback:'paced',language:'ASL',input_language:'en',
 complete_translation:false,source_preview_enabled:true,media_duration:3,playback_duration:4,hold_duration:1,
 items:[item(0,.5,0),item(.5,1.5,.5,clip,'Hello'),item(1.5,2,2.5,null,'unknown'),item(2,3,3)],
 playable_signs:1,matched:0,source_previews:1,total_words:2,signed_words:1,missing_words:['unknown'],limitations:[]};

const leading=getPlaybackFrame(plan,.25);
assert.equal(leading.activeItem.status,'gap');assert.equal(leading.mediaTime,.25);assert.equal(leading.activeMotion,null);
const sign=getPlaybackFrame(plan,1);
assert.equal(sign.activeMotion,clip);assert.equal(sign.motionTime,.5);assert.equal(sign.mediaTime,1);assert.equal(sign.isHolding,false);
const hold=getPlaybackFrame(plan,2);
assert.equal(hold.motionTime,1.5);assert.equal(hold.mediaTime,1.5);assert.equal(hold.isHolding,true);assert.equal(hold.mediaShouldPlay,false);
const unknown=getPlaybackFrame(plan,2.75);
assert.equal(unknown.activeItem.text,'unknown');assert.equal(unknown.activeMotion,null);assert.equal(unknown.mediaTime,1.75);
const trailing=getPlaybackFrame(plan,3.5);
assert.equal(trailing.activeItem.status,'gap');assert.equal(trailing.mediaTime,2.5);

assert.equal(getPlaybackFrame(plan,.5).activeItem.text,'Hello','An exact boundary belongs to the next slot');
assert.equal(getPlaybackFrame(plan,2.5).activeItem.text,'unknown','The previous sign ends before the next slot');
assert.equal(advancePlaybackPosition(plan,1,.25),1.25,'One second of wall clock is one second of recorded sign motion');
assert.equal(advancePlaybackPosition(plan,1,10),1.5,'Do not skip the source-to-hold boundary');
assert.equal(advancePlaybackPosition(plan,1.5,10),2.5,'Do not skip the sign-to-next-slot boundary');
assert.equal(advancePlaybackPosition(plan,2,-1),2);

const shorter={...clip,duration:1};
const slowSource={...plan,media_duration:2,playback_duration:2,items:[item(0,2,0,shorter,'Hello')]};
const afterShortClip=getPlaybackFrame(slowSource,1.5);
assert.equal(afterShortClip.activeMotion,null,'A short clip must not be stretched over long speech');
assert.equal(afterShortClip.mediaShouldPlay,true);assert.equal(afterShortClip.mediaTime,1.5);

for(const seek of [3.9,.75,2,0,2.5,.5]){
 const frame=getPlaybackFrame(plan,seek);
 assert.equal(frame.position,seek,'Forward/backward paused seeking uses the requested virtual position');
 assert.ok(frame.mediaTime>=0&&frame.mediaTime<=plan.media_duration);
}
const end=getPlaybackFrame(plan,4);
assert.equal(end.finished,true);assert.equal(end.mediaTime,3);assert.equal(end.activeMotion,null);assert.equal(end.activeItem,null);
assert.equal(clampPlaybackPosition(plan,-2),0);assert.equal(clampPlaybackPosition(plan,99),4);assert.equal(clampPlaybackPosition(plan,NaN),0);
assert.equal(getPlaybackFrame(null,20).finished,true);assert.equal(advancePlaybackPosition(null,0,1),0);
const a={...clip,id:'asl-letter-a',phrase:'A',duration:1},b={...a,id:'asl-letter-b',phrase:'B'};
const spelled={...plan,media_duration:.5,playback_duration:3.2,items:[
 {...item(0,.3,0,a,'ABA'),rendering:'fingerspelling',letter:'A'},
 {...item(.3,.3,1,b,'ABA'),rendering:'fingerspelling',letter:'B'},
 {...item(.3,.3,2,a,'ABA'),rendering:'fingerspelling',letter:'A'},item(.3,.5,3),
]};
const middleLetter=getPlaybackFrame(spelled,1.5);
assert.equal(middleLetter.activeMotion,b);assert.equal(middleLetter.motionTime,.5);
assert.equal(middleLetter.mediaTime,.3);assert.equal(middleLetter.mediaShouldPlay,false);assert.equal(middleLetter.isHolding,true);
assert.equal(advancePlaybackPosition(spelled,1.9,.5),2,'A zero-source-span letter still finishes before the next recorded letter');
assert.equal(getPlaybackFrame(spelled,2).activeMotion,a,'Repeated letters must start a fresh motion time');
assert.equal(getPlaybackFrame(spelled,2).motionTime,0);
assert.equal(getPlaybackFrame(spelled,3.1).mediaShouldPlay,true,'Source resumes after the complete spelled word');
assert.ok(Math.abs(getPlaybackFrame(spelled,3.1).mediaTime-.4)<1e-9);
const quickClip={...clip,duration:4};
const quickItem={...item(0,.25,0,quickClip,'Hello'),duration:2.4,slot_duration:2.4,hold_duration:2.15,playback_end:2.4,
 clip_start:.5,clip_end:3.5,playback_rate:1.25};
const quick={...plan,media_duration:.25,playback_duration:2.4,items:[quickItem]};
assert.equal(getPlaybackFrame(quick,0).motionTime,.5,'Quick word mode starts at the validated source window');
assert.equal(getPlaybackFrame(quick,1).motionTime,1.75,'Quick word time maps to recorded clip time at 1.25x');
assert.equal(getPlaybackFrame(quick,2).motionTime,3);
assert.equal(getPlaybackFrame(quick,2.4).activeMotion,null,'The entire preserved source window finishes before the next slot');
assert.ok(getPlaybackFrame({...quick,items:[{...quickItem,playback_rate:99}]},1).motionTime<=1.75,'Defensive client timing never exceeds the 1.25x rate cap');
console.log('PASS: natural/quick clip timing, validated source windows, rate cap, media holds, gaps, seeks, boundaries and optional sequential fingerspelling.');
