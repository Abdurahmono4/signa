import {useEffect,useRef,useState} from 'react';
import {flushSync} from 'react-dom';

export type SubtitleInterval={start:number;end:number};
export type TimedCaption=SubtitleInterval&{text:string};
type Recording=TimedCaption&{supported:boolean;video_url?:string|null;timing_source?:string|null};
type PlayerProps={src:string;className?:string;subtitleIntervals?:readonly SubtitleInterval[];
 sourceCaptions?:readonly TimedCaption[];sourceRecordings?:readonly Recording[];timingScale?:number;
 avatarReview?:{panelWidth:number;centered:boolean;close:boolean;fps?:number;frames?:number}};

function formatTime(time:number){
 const seconds=Math.floor(time);
 return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
}

function Player({src,className,subtitleIntervals=[],sourceCaptions=[],sourceRecordings=[],timingScale=1,avatarReview}:PlayerProps){
 const video=useRef<HTMLVideoElement|null>(null),resume=useRef(0);
 const zoomCanvas=useRef<HTMLCanvasElement>(null);
 const [zoom,setZoom]=useState(false);
 const [error,setError]=useState(''),[retrying,setRetrying]=useState(false);
 const [rate,setRate]=useState(1);
 const [duration,setDuration]=useState(0);
 const [expanded,setExpanded]=useState(false);
 const [currentTime,setCurrentTime]=useState(0);
 const fps=avatarReview?.fps;
 const measuredFrames=avatarReview?.frames;
 const frameCount=fps&&duration?(measuredFrames&&Number.isSafeInteger(measuredFrames)&&measuredFrames>0
  ?measuredFrames:Math.max(1,Math.round(duration*fps))):0;
 const frameAt=(time:number)=>Math.max(0,Math.min(frameCount-1,Math.floor(time*(fps||0)+1e-6)));
 const referenceVideo=useRef<HTMLVideoElement>(null);
 const [showReference,setShowReference]=useState(false);
 const [selectedReference,setSelectedReference]=useState(0);
 const [referenceError,setReferenceError]=useState(false);
 const recordings=sourceRecordings.filter(r=>r.supported&&r.timing_source==='manual_realignment'&&
  /^\/api\/how2sign\/realigned\/clips\/[a-f0-9]{24}$/.test(r.video_url||''));
 const reference=recordings[selectedReference]??recordings[0];
 const scale=Number.isFinite(timingScale)&&timingScale>0?timingScale:1;
 const intervals=subtitleIntervals.filter(({start,end})=>
  Number.isFinite(start)&&Number.isFinite(end)&&start>=0&&end>start);
 useEffect(()=>{
  const media=video.current,canvas=zoomCanvas.current;
  if(!zoom||!avatarReview||!media||!canvas)return;
  const context=canvas.getContext('2d');
  if(!context)return;
  let callback:number|undefined;
  const draw=()=>{
   if(media.readyState<2)return;
   const width=2*Math.round(media.videoWidth*avatarReview.panelWidth/2);
   const figureWidth=avatarReview.close?Math.max(width,2*Math.round(media.videoWidth*.4/2)):width;
   const height=Math.min(media.videoHeight,2*Math.round(figureWidth*.75/2));
   if(width<1||height<1)return;
   if(canvas.width!==width)canvas.width=width;
   if(canvas.height!==height)canvas.height=height;
   const x=avatarReview.centered?(media.videoWidth-width)/2:media.videoWidth-width;
   context.drawImage(media,x,Math.round((media.videoHeight-height)/2),
    width,height,0,0,width,height);
  };
  const tracksFrames=typeof media.requestVideoFrameCallback==='function';
  const redraw:VideoFrameRequestCallback=(_,frame)=>{
   draw();
   // Commit the counter in the same paint as the canvas, including on slow playback.
   if(fps&&!media.paused&&!media.seeking)flushSync(()=>setCurrentTime(Math.round(frame.mediaTime*fps)/fps));
   callback=media.requestVideoFrameCallback(redraw);
  };
  const events=tracksFrames?['loadeddata','seeked']:['loadeddata','seeked','timeupdate'];
  for(const event of events)media.addEventListener(event,draw);
  draw();
  if(tracksFrames)callback=media.requestVideoFrameCallback(redraw);
  return ()=>{
   if(callback!==undefined)media.cancelVideoFrameCallback(callback);
   for(const event of events)media.removeEventListener(event,draw);
  };
 },[zoom,avatarReview,fps]);

 function stepFrame(direction:number){
  const media=video.current;
  if(!media||!fps||!frameCount)return;
  media.pause();
  const frame=Math.max(0,Math.min(frameCount-1,frameAt(media.currentTime)+direction));
  media.currentTime=Math.min(duration,(frame+.5)/fps);
  setCurrentTime(media.currentTime);
 }
 function retry(){
  if(!video.current)return;
  resume.current=Number.isFinite(video.current.currentTime)?video.current.currentTime:0;
  setError('');setRetrying(true);setDuration(0);video.current.load();
 }
 function setReviewRate(next:number){
  setRate(next);
  for(const media of [video.current,referenceVideo.current]){
   if(media&&media.playbackRate!==next)media.playbackRate=next;
  }
 }
 return <><video ref={video} className={className} controls playsInline preload="metadata" aria-label="Tarjimonli natija" src={src}
  onPlay={()=>referenceVideo.current?.pause()}
  onLoadedMetadata={e=>{const media=e.currentTarget;setRetrying(false);setError('');media.playbackRate=rate;
   if(Number.isFinite(media.duration)){setDuration(media.duration);if(resume.current>0)media.currentTime=Math.min(resume.current,media.duration)}
   resume.current=0;
  }}
  onRateChange={e=>setReviewRate(e.currentTarget.playbackRate)}
  onTimeUpdate={e=>{
   const media=e.currentTarget;
   if((expanded||zoom)&&(!zoom||!fps||media.paused||typeof media.requestVideoFrameCallback!=='function'))setCurrentTime(media.currentTime);
  }}
  onSeeked={e=>{if(expanded||zoom)setCurrentTime(e.currentTarget.currentTime)}}
  onError={()=>{setDuration(0);setRetrying(false);setError(video.current?.error?.code===3||video.current?.error?.code===4?'Brauzer videoni ijro eta olmadi. MP4 faylini yuklab olib oching yoki qayta urinib ko‘ring.':'Video yuklanayotganda aloqa uzildi. Tayyor natijani qayta oching.')}}/>
  <div className="actions" role="group" aria-label="Harakatni batafsil ko‘rish">
   <label>Ko‘rish tezligi <select aria-label="Ko‘rish tezligi" value={rate} onChange={e=>setReviewRate(Number(e.target.value))}>
    {![.5,.75,1].includes(rate)&&<option value={rate}>{rate}×</option>}<option value={.5}>0,5× — juda sekin</option><option value={.75}>0,75× — sekin</option><option value={1}>1× — asl tezlik</option>
   </select></label>
   <button type="button" onClick={()=>{const v=video.current;if(v&&Number.isFinite(v.duration)){v.currentTime=Math.max(0,v.currentTime-3)}}}>3 soniya orqaga</button>
   {avatarReview&&<button type="button" aria-expanded={zoom} disabled={!duration}
    onClick={()=>{if(!zoom&&video.current){video.current.pause();setCurrentTime(video.current.currentTime)}setZoom(!zoom)}}>Qo‘llarni yaqindan ko‘rish</button>}
  </div>
  {zoom&&avatarReview&&<div className="avatar-frame-review">
   <canvas ref={zoomCanvas} role="img" aria-label="Avatar qo‘llari va yuzi yaqin ko‘rinishda"/>
   {avatarReview.fps&&<div className="actions" role="group" aria-label="Kadrma-kadr ko‘rish">
    <button type="button" disabled={!frameCount||frameAt(currentTime)===0} onClick={()=>stepFrame(-1)}>← Oldingi kadr</button>
    {frameCount>0&&<span>Kadr {frameAt(currentTime)+1} / {frameCount}</span>}
    <button type="button" disabled={!frameCount||frameAt(currentTime)>=frameCount-1} onClick={()=>stepFrame(1)}>Keyingi kadr →</button>
   </div>}
  </div>}
  {reference&&<details className="result-source-recording" onToggle={e=>{
    if(e.currentTarget.open&&video.current){
     video.current.pause();
     const sourceTime=video.current.currentTime/scale;
     const index=recordings.findIndex(r=>r.start<=sourceTime&&sourceTime<r.end);
     if(index>=0)setSelectedReference(index);
    }
    setShowReference(e.currentTarget.open);setReferenceError(false);
  }}>
   <summary>Haqiqiy tarjimon ijrosini solishtirish</summary>
   {showReference&&<>
    {recordings.length>1?<label>Jumlani tanlang
     <select value={selectedReference} onChange={e=>{setSelectedReference(Number(e.target.value));setReferenceError(false)}}>
      {recordings.map((r,index)=><option key={index} value={index}>{formatTime(r.start*scale)} · {r.text}</option>)}
     </select></label>:<p lang="en">{reference.text}</p>}
    <video key={reference.start+'-'+reference.video_url} ref={referenceVideo} aria-label="How2Sign tarjimon yozuvi" controls playsInline
     preload="metadata" src={reference.video_url!} onLoadedMetadata={e=>{e.currentTarget.playbackRate=rate}}
     onRateChange={e=>{if(e.currentTarget.readyState>=1)setReviewRate(e.currentTarget.playbackRate)}}
     onPlay={()=>video.current?.pause()} onError={()=>setReferenceError(true)}/>
    {referenceError&&<p role="alert">Tarjimon yozuvi ochilmadi.</p>}
    <div className="actions"><button type="button" disabled={duration<=reference.start*scale} onClick={()=>{
     referenceVideo.current?.pause();
     if(video.current){video.current.pause();video.current.currentTime=reference.start*scale}
    }}>Avatardagi shu jumlaga qaytish</button></div>
    <small>ASL tarjimonining manba yozuvi · <a href="https://how2sign.github.io/" target="_blank" rel="noreferrer">How2Sign</a></small>
   </>}
  </details>}
  {intervals.length>0&&<details className="result-subtitle-intervals" onToggle={e=>{
   setExpanded(e.currentTarget.open);
   if(video.current)setCurrentTime(video.current.currentTime);
  }}>
   <summary>Faqat subtitr bilan berilgan joylar ({intervals.length})</summary>
   {expanded&&<ul>{intervals.map(({start,end},index)=>{
    // The exported MP4 uses the scaled media clock, while the transcript uses source time.
    const caption=sourceCaptions.filter(s=>s.start*scale<end&&s.end*scale>start)
     .map(s=>s.text.trim()).filter(Boolean).join(' ');
    return <li key={`${start}-${index}`}>
    <button type="button" disabled={duration<=start} aria-current={currentTime>=start&&currentTime<end?'true':undefined}
     onClick={()=>{if(video.current){video.current.currentTime=start;setCurrentTime(start)}}}>
     <strong>{formatTime(start)} – {formatTime(end)}</strong>
     {caption&&<span lang="en">{caption}</span>}
    </button>
   </li>})}</ul>}
  </details>}
  {retrying&&<p role="status">Tayyor video qayta yuklanmoqda…</p>}
  {error&&<div className="result-playback-error" role="alert"><p>{error}</p><button onClick={retry}>Videoni qayta ochish</button></div>}
 </>;
}
/** A changed export gets fresh playback/error state; retry never regenerates the MP4. */
export default function ResultVideo(props:PlayerProps){return <Player key={props.src} {...props}/>}
