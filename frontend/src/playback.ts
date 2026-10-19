import type {Motion} from './Avatar3D';

export type PlaybackItem={
 rendering:'sign'|'fingerspelling'|'caption'|'gap';word_text:string;letter:string|null;letter_index?:number;letter_count?:number;
 segment_index:number|null;start:number;end:number;text:string;status:string;sync_status:string;
 timing:'aligned'|'estimated'|'gap';word_count:number;clip:Motion|null;
 media_start:number;media_end:number;media_play_start:number;media_play_end:number;
 duration:number;slot_duration:number;hold_duration:number;playback_start:number;playback_end:number;
 clip_start:number;clip_end:number;playback_rate:number;
};
export type PlaybackPlan={
 job_id:string;revision:number;mode:'dictionary_assistance'|'neural_asl';playback:'paced';language:'ASL';input_language:string;
 presentation:'words'|'fingerspelling'|'sentences';fingerspelling_enabled:boolean;
 complete_translation:false;source_preview_enabled:boolean;media_duration:number;playback_duration:number;
 hold_duration:number;items:PlaybackItem[];playable_signs:number;matched:number;source_previews:number;
 total_words:number;signed_words:number;spelled_words:number;caption_words:number;fingerspelling_letters:number;
 dictionary_missing_words:string[];missing_words:string[];limitations:string[];
 spelling_limits:{max_word_length:number;max_letters:number;max_added_seconds:number;limited_words:string[]};
};
export type PlaybackFrame={
 position:number;total:number;itemIndex:number;activeItem:PlaybackItem|null;mediaTime:number;
 activeMotion:Motion|null;motionTime:number;isHolding:boolean;mediaShouldPlay:boolean;
 finished:boolean;nextBoundary:number;
};

export function clampPlaybackPosition(plan:PlaybackPlan|null,position:number){
 const total=Math.max(0,plan?.playback_duration||0);
 return Math.min(total,Math.max(0,Number.isFinite(position)?position:0));
}

export function getPlaybackFrame(plan:PlaybackPlan|null,position:number):PlaybackFrame{
 const total=Math.max(0,plan?.playback_duration||0),at=clampPlaybackPosition(plan,position);
 const itemIndex=plan&&at<total?plan.items.findIndex(item=>at>=item.playback_start&&at<item.playback_end):-1;
 const item=itemIndex>=0?plan!.items[itemIndex]:null;
 if(!item)return {position:at,total,itemIndex:-1,activeItem:null,mediaTime:at>=total?plan?.media_duration||0:0,
  activeMotion:null,motionTime:0,isHolding:false,mediaShouldPlay:false,finished:at>=total,nextBoundary:total};
 const elapsed=Math.max(0,at-item.playback_start),mediaSpan=Math.max(0,item.media_play_end-item.media_play_start);
 const clipStart=Number.isFinite(item.clip_start)?Math.max(0,item.clip_start):0;
 const clipEnd=Number.isFinite(item.clip_end)?Math.max(clipStart,item.clip_end):item.clip?.duration||0;
 const playbackRate=Number.isFinite(item.playback_rate)?Math.max(.01,Math.min(1.25,item.playback_rate)):1;
 const activeMotion=item.clip&&elapsed<item.duration?item.clip:null;
 const boundaries=[item.playback_end];
 if(item.clip&&item.duration<item.slot_duration)boundaries.push(item.playback_start+item.duration);
 if(mediaSpan<item.slot_duration)boundaries.push(item.playback_start+mediaSpan);
 return {position:at,total,itemIndex,activeItem:item,
  mediaTime:item.media_play_start+Math.min(elapsed,mediaSpan),
  activeMotion,motionTime:activeMotion?Math.min(clipEnd,clipStart+elapsed*playbackRate):0,
  isHolding:!!activeMotion&&elapsed>=mediaSpan,
  mediaShouldPlay:elapsed<mediaSpan,finished:false,
  nextBoundary:Math.min(...boundaries.filter(boundary=>boundary>at+1e-9))};
}

export function advancePlaybackPosition(plan:PlaybackPlan|null,position:number,elapsed:number){
 const frame=getPlaybackFrame(plan,position);
 return Math.min(frame.total,frame.nextBoundary,frame.position+Math.max(0,Number.isFinite(elapsed)?elapsed:0));
}
