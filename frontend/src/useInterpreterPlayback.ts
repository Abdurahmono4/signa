import {useCallback,useEffect,useRef,useState} from 'react';
import type {RefObject} from 'react';
import {advancePlaybackPosition,clampPlaybackPosition,getPlaybackFrame} from './playback';
import type {PlaybackFrame,PlaybackPlan} from './playback';

// Source media owns the clock while audio is playing. Walk across consecutive
// source slots in one frame, but stop at a deliberate sign hold: its remaining
// animation uses wall time while the source is paused.
function positionAtMediaTime(plan:PlaybackPlan|null,position:number,mediaTime:number){
 if(!plan||!Number.isFinite(mediaTime))return position;
 let frame=getPlaybackFrame(plan,position);
 for(let count=0;count<=plan.items.length&&frame.mediaShouldPlay;count++){
  const item=frame.activeItem!;
  const mediaSpan=Math.max(0,item.media_play_end-item.media_play_start);
  const boundary=Math.min(item.playback_end,item.playback_start+mediaSpan);
  const next=Math.max(frame.position,item.playback_start+mediaTime-item.media_play_start);
  if(next<boundary)return next;
  position=boundary;
  frame=getPlaybackFrame(plan,position);
 }
 return position;
}

export function useInterpreterPlayback(plan:PlaybackPlan|null,mediaRef:RefObject<HTMLMediaElement|null>){
 const [position,setPosition]=useState(0),[playing,setPlaying]=useState(false),[error,setError]=useState('');
 const planRef=useRef(plan),positionRef=useRef(0),playingRef=useRef(false),avatarReady=useRef(false);
 const buffering=useRef(false),playPending=useRef(false),playToken=useRef(0),lastItem=useRef(-2),lastMediaPlaying=useRef<boolean|null>(null);
 planRef.current=plan;

 const stopMedia=useCallback(()=>{
  const media=mediaRef.current;
  if(media&&(!media.paused||playPending.current)){playToken.current++;playPending.current=false;media.pause()}
 },[mediaRef]);
 const pause=useCallback(()=>{
  const media=mediaRef.current;
  if(playingRef.current&&media){
   const next=positionAtMediaTime(planRef.current,positionRef.current,media.currentTime);
   positionRef.current=next;setPosition(next);
  }
  playingRef.current=false;setPlaying(false);stopMedia();
 },[mediaRef,stopMedia]);
 const startMedia=useCallback(()=>{
  const media=mediaRef.current;
  if(!media||!media.paused||media.ended||playPending.current)return;
  const token=++playToken.current;
  playPending.current=true;
  try{
   const result=media.play();
   Promise.resolve(result).then(()=>{if(token===playToken.current)playPending.current=false}).catch(cause=>{
    if(token!==playToken.current)return;
    playPending.current=false;
    if(!playingRef.current)return;
    playingRef.current=false;setPlaying(false);media.pause();
    setError(cause?.name==='NotAllowedError'?'Media ijrosi bloklandi. Ijro tugmasini yana bosing.':'Media ijro etilmadi. Faylni tekshiring va qayta urinib ko‘ring.');
   });
  }catch{
   playPending.current=false;playingRef.current=false;setPlaying(false);
   setError('Media ijro etilmadi. Faylni tekshiring va qayta urinib ko‘ring.');
  }
 },[mediaRef]);
 const syncMedia=useCallback((frame:PlaybackFrame,force=false)=>{
  const media=mediaRef.current;if(!media)return;
  const changed=lastItem.current!==frame.itemIndex;lastItem.current=frame.itemIndex;
  const enterHold=!frame.mediaShouldPlay&&(changed||lastMediaPlaying.current!==false);
  lastMediaPlaying.current=frame.mediaShouldPlay;
  // Never chase a RAF clock with currentTime seeks during ordinary playback.
  // A seek is needed only for a user action or to enter an intentional hold.
  if((force||enterHold)&&Math.abs(media.currentTime-frame.mediaTime)>.035){
   try{media.currentTime=frame.mediaTime}catch{ /* Metadata may still be loading. */ }
  }
  const frozen=!!frame.activeMotion&&!avatarReady.current;
  if(playingRef.current&&frame.mediaShouldPlay&&!frozen)startMedia();else stopMedia();
 },[mediaRef,startMedia,stopMedia]);
 const seek=useCallback((seconds:number)=>{
  const next=clampPlaybackPosition(planRef.current,seconds);
  positionRef.current=next;setPosition(next);buffering.current=false;
  playToken.current++;playPending.current=false;
  const frame=getPlaybackFrame(planRef.current,next);
  if(frame.finished){playingRef.current=false;setPlaying(false)}
  syncMedia(frame,true);
 },[syncMedia]);
 const reset=useCallback(()=>{pause();setError('');seek(0)},[pause,seek]);
 const clearError=useCallback(()=>setError(''),[]);
 const play=useCallback(()=>{
  if(!planRef.current||!planRef.current.playback_duration)return;
  if(getPlaybackFrame(planRef.current,positionRef.current).finished)seek(0);
  setError('');playingRef.current=true;setPlaying(true);
  // Request playback within the user's click, preserving browser activation.
  syncMedia(getPlaybackFrame(planRef.current,positionRef.current),true);
 },[seek,syncMedia]);
 const setAvatarReady=useCallback((ready:boolean)=>{
  avatarReady.current=ready;
  if(!ready&&getPlaybackFrame(planRef.current,positionRef.current).activeMotion)stopMedia();
 },[stopMedia]);

 useEffect(()=>{
  reset();lastItem.current=-2;lastMediaPlaying.current=null;
  return()=>{playingRef.current=false;playToken.current++;playPending.current=false;mediaRef.current?.pause()};
 },[plan,reset,mediaRef]);
 useEffect(()=>{
  const media=mediaRef.current;if(!media)return;
  // `stalled` describes network delivery, not whether buffered data can play.
  // Latching it unconditionally can stop a fully buffered file forever because
  // a browser already at HAVE_ENOUGH_DATA need not emit `canplay` again.
  const waiting=()=>{buffering.current=media.readyState<3};
  const ready=()=>{if(media.readyState>=3)buffering.current=false};
  const ended=()=>{buffering.current=false};
  const failed=()=>{pause();setError('Media faylini brauzer o‘qiy olmadi. Boshqa audio yoki video tanlang.')};
  for(const event of ['waiting','stalled','seeking'])media.addEventListener(event,waiting);
  for(const event of ['canplay','canplaythrough','playing','seeked','loadeddata'])media.addEventListener(event,ready);
  media.addEventListener('ended',ended);media.addEventListener('error',failed);
  buffering.current=false;
  return()=>{
   for(const event of ['waiting','stalled','seeking'])media.removeEventListener(event,waiting);
   for(const event of ['canplay','canplaythrough','playing','seeked','loadeddata'])media.removeEventListener(event,ready);
   media.removeEventListener('ended',ended);media.removeEventListener('error',failed);
  };
 },[plan,mediaRef,pause]);
 useEffect(()=>{
  if(!playing)return;
  let handle=0,last=performance.now();
  const tick=(now:number)=>{
   const delta=Math.max(0,(now-last)/1000);last=now;
   if(!playingRef.current)return;
   const before=getPlaybackFrame(planRef.current,positionRef.current),media=mediaRef.current;
   if(media&&(media.readyState>=3||media.ended))buffering.current=false;
   const avatarBlocked=!!before.activeMotion&&!avatarReady.current;
   // A media hold needs no audio data; an ended source must still allow its
   // final sign to finish. Buffering only blocks a slot that consumes media.
   const mediaBlocked=before.mediaShouldPlay&&(!media||(!media.ended&&
    (media.seeking||media.readyState<2||buffering.current)));
   if(avatarBlocked||mediaBlocked){stopMedia()}
   else{
    syncMedia(before);
    // Let the browser's play request settle before advancing the shared clock.
    if(before.mediaShouldPlay&&playPending.current){handle=requestAnimationFrame(tick);return}
    const sourceTime=media?.ended?Math.max(media.currentTime,planRef.current?.media_duration||0):media?.currentTime||0;
    const next=before.mediaShouldPlay
     ? positionAtMediaTime(planRef.current,positionRef.current,sourceTime)
     : advancePlaybackPosition(planRef.current,positionRef.current,delta);
    positionRef.current=next;setPosition(next);
    const after=getPlaybackFrame(planRef.current,next);
    syncMedia(after);
    if(after.finished){pause();return}
   }
   handle=requestAnimationFrame(tick);
  };
  handle=requestAnimationFrame(tick);
  return()=>cancelAnimationFrame(handle);
 },[playing,mediaRef,pause,stopMedia,syncMedia]);

 const frame=getPlaybackFrame(plan,position);
 return {position:frame.position,total:frame.total,mediaTime:frame.mediaTime,playing,play,pause,seek,reset,
  activeMotion:frame.activeMotion,motionTime:frame.motionTime,activeItem:frame.activeItem,
  isHolding:frame.isHolding,setAvatarReady,error,clearError};
}
