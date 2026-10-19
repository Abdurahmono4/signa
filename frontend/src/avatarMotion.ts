import type {AnimationAction,AnimationMixer} from 'three';

export const AVATAR_REST_TIME=1/30;

/** Sample a recorded pose deterministically, including backwards seeks/replay. */
export function sampleAvatarMotion(mixer:AnimationMixer,action:AnimationAction,time:number,active=true,minimum=AVATAR_REST_TIME){
 const lower=Math.max(0,Math.min(Number.isFinite(minimum)?minimum:AVATAR_REST_TIME,action.getClip().duration));
 const requested=active&&Number.isFinite(time)?time:lower;
 const sampled=Math.max(lower,Math.min(requested,action.getClip().duration));
 action.reset().play();
 mixer.setTime(sampled);
 return sampled;
}
