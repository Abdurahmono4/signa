export type MotionInterval={start:number;end:number;duration:number;blockedBefore?:boolean};
// Do not stretch a short decoded movement into several seconds of slow motion.
// Speech slots stay intact; unused time is a presentation pause, never a loop.
export function motionEnd(item:MotionInterval){return Math.min(item.end,item.start+item.duration/.85)}
export function motionAt<T extends MotionInterval>(items:readonly T[],time:number):{item:T;localTime:number}|null{
 if(!Number.isFinite(time)||time<0)return null;
 const item=items.find(i=>time>=i.start&&time<motionEnd(i));
 return item?{item,localTime:Math.min(item.duration-.0001,Math.max(0,(time-item.start)/(motionEnd(item)-item.start)*item.duration))}:null;
}
/** Add presentation transitions only in gaps, preserving every timed sign frame. */
export function presentationAt<T extends MotionInterval>(items:readonly T[],time:number,fade=.24){
 const active=motionAt(items,time);
 if(active)return {from:active,to:null,mix:0};
 if(!Number.isFinite(time)||time<0||!Number.isFinite(fade)||fade<=0)return {from:null,to:null,mix:0};
 const previous=[...items].reverse().find(i=>motionEnd(i)<=time),next=items.find(i=>i.start>time);
 const previousEnd=previous?motionEnd(previous):0;
 const end=previous?{item:previous,localTime:Math.max(0,previous.duration-.0001)}:null;
 const start=next?{item:next,localTime:0}:null;
 const smooth=(x:number)=>{const w=Math.max(0,Math.min(1,x));return w*w*(3-2*w)};
 // For a brief pause, travel directly between the two endpoint poses.
 // A trip down to idle and back adds two wrist excursions to a single pause.
 const gap=next?next.start-previousEnd:Infinity;
 if(previous&&next&&!next.blockedBefore&&gap<=Math.max(fade*2,.9))return {from:end,to:start,mix:smooth((time-previousEnd)/(next.start-previousEnd))};
 // In a short blocked gap both transitions must meet at rest. Overlapping
 // full-length fades would switch abruptly from one handshape to the next.
 const window=previous&&next?Math.min(fade,gap/2):fade;
 if(previous&&time-previousEnd<window)return {from:end,to:null,mix:smooth((time-previousEnd)/window)};
 if(next&&next.start-time<window)return {from:null,to:start,mix:smooth(1-(next.start-time)/window)};
 return {from:null,to:null,mix:0};
}
export function validateIntervals(items:readonly MotionInterval[],outputDuration:number){
 if(!Number.isFinite(outputDuration)||outputDuration<=0)throw Error('Media davomiyligi yaroqsiz.');
 let previous=0;
 for(const item of items){
  if(![item.start,item.end,item.duration].every(Number.isFinite)||item.start<previous||item.end<=item.start||item.duration<=0||item.end>outputDuration+.05)throw Error('Harakat vaqtlari yaroqsiz yoki ustma-ust.');
  previous=item.end;
 }
}
