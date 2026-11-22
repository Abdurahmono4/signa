import {useEffect,useRef,useState} from 'react';

export type SubtitleInterval={start:number;end:number};
export type TimedCaption=SubtitleInterval&{text:string};
type Recording=TimedCaption&{supported:boolean;video_url?:string|null;timing_source?:string|null};
type PlayerProps={src:string;className?:string;subtitleIntervals?:readonly SubtitleInterval[];
 sourceCaptions?:readonly TimedCaption[];sourceRecordings?:readonly Recording[];timingScale?:number;
 avatarReview?:{panelWidth:number;figureHeight:number;fps:number}};

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
   const width=Math.round(media.videoWidth*avatarReview.panelWidth);
   const height=Math.round(media.videoHeight*avatarReview.figureHeight);
   if(width<1||height<1)return;
   if(canvas.width!==width)canvas.width=width;
   if(canvas.height!==height)canvas.height=height;
   context.drawImage(media,media.videoWidth-width,Math.round((media.videoHeight-height)/2),
    width,height,0,0,width,height);
  };
  const redraw=()=>{draw();callback=media.requestVideoFrameCallback(redraw)};
  const events=['loadeddata','seeked','timeupdate'] as const;
  for(const event of events)media.addEventListener(event,draw);
  draw();
  if(typeof media.requestVideoFrameCallback==='function')callback=media.requestVideoFrameCallback(redraw);
  return ()=>{
   if(callback!==undefined)media.cancelVideoFrameCallback(callback);
   for(const event of events)media.removeEventListener(event,draw);
  };
 },[zoom,avatarReview]);

 function stepFrame(direction:number){
  const media=video.current;
  if(!media||!avatarReview||!duration)return;
  media.pause();
  const {fps}=avatarReview;
  const frame=Math.floor(media.currentTime*fps+1e-4)+direction;
  media.currentTime=Math.max(0,Math.min(duration-.5/fps,(frame+.5)/fps));
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
  onTimeUpdate={e=>{if(expanded)setCurrentTime(e.currentTarget.currentTime)}}
  onError={()=>{setDuration(0);setRetrying(false);setError(video.current?.error?.code===3||video.current?.error?.code===4?'Brauzer videoni ijro eta olmadi. MP4 faylini yuklab olib oching yoki qayta urinib ko‘ring.':'Video yuklanayotganda aloqa uzildi. Tayyor natijani qayta oching.')}}/>
  <div className="actions" role="group" aria-label="Harakatni batafsil ko‘rish">
   <label>Ko‘rish tezligi <select aria-label="Ko‘rish tezligi" value={rate} onChange={e=>setReviewRate(Number(e.target.value))}>
    {![.5,.75,1].includes(rate)&&<option value={rate}>{rate}×</option>}<option value={.5}>0,5× — juda sekin</option><option value={.75}>0,75× — sekin</option><option value={1}>1× — asl tezlik</option>
   </select></label>
   <button type="button" onClick={()=>{const v=video.current;if(v&&Number.isFinite(v.duration)){v.currentTime=Math.max(0,v.currentTime-3)}}}>3 soniya orqaga</button>
   {avatarReview&&<button type="button" aria-expanded={zoom} disabled={!duration}
    onClick={()=>{if(!zoom)video.current?.pause();setZoom(!zoom)}}>Qo‘llarni yaqindan ko‘rish</button>}
  </div>
  {zoom&&avatarReview&&<div className="avatar-frame-review">
   <canvas ref={zoomCanvas} role="img" aria-label="Avatar qo‘llari va yuzi yaqin ko‘rinishda"/>
   <div className="actions" role="group" aria-label="Kadrma-kadr ko‘rish">
    <button type="button" disabled={!duration} onClick={()=>stepFrame(-1)}>← Oldingi kadr</button>
    <button type="button" disabled={!duration} onClick={()=>stepFrame(1)}>Keyingi kadr →</button>
   </div>
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
