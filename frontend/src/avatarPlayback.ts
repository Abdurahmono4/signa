import * as THREE from 'three';

/** Sample an action without restarting its bindings on every media frame. */
export class AvatarPlayback {
 private active:THREE.AnimationClip[]=[];
 constructor(private mixer:THREE.AnimationMixer,private idle:THREE.AnimationClip|null=null){}
 sample(clip:THREE.AnimationClip|null,time=0){
  this.apply([{clip:clip||this.idle,time,weight:1}]);
 }
 /** Deterministic clock-based blending: seeking and export get identical poses. */
 transition(from:{clip:THREE.AnimationClip;time:number}|null,to:{clip:THREE.AnimationClip;time:number}|null,mix:number){
  const w=Math.min(1,Math.max(0,Number.isFinite(mix)?mix:0));
  this.apply([{clip:from?.clip||this.idle,time:from?.time||0,weight:1-w},{clip:to?.clip||this.idle,time:to?.time||0,weight:w}]);
 }
 private apply(samples:{clip:THREE.AnimationClip|null;time:number;weight:number}[]){
  const merged=new Map<THREE.AnimationClip,{time:number;weight:number}>();
  for(const s of samples){if(!s.clip||s.weight<=0)continue;const previous=merged.get(s.clip);merged.set(s.clip,previous?{time:(previous.time*previous.weight+s.time*s.weight)/(previous.weight+s.weight),weight:previous.weight+s.weight}:{time:s.time,weight:s.weight})}
  const next=[...merged.keys()];
  if(next.length!==this.active.length||next.some((c,i)=>c!==this.active[i])){
   this.mixer.stopAllAction();this.active=next;
   for(const clip of next){const action=this.mixer.clipAction(clip);action.reset().setLoop(THREE.LoopOnce,1).play();action.paused=true;action.clampWhenFinished=true}
  }
  for(const [clip,s] of merged){const action=this.mixer.clipAction(clip);action.setEffectiveWeight(s.weight);action.time=Math.min(clip.duration,Math.max(0,Number.isFinite(s.time)?s.time:0))}
  if(next.length)this.mixer.update(0);
 }
 dispose(){this.mixer.stopAllAction();this.active=[]}
}
