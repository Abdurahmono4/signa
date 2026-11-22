import {requestSignal} from './flowGuards.ts';
/** PUT to the same session/frame is idempotent; retry temporary transport failures only. */
export async function uploadFrame(url:string,blob:Blob,signal:AbortSignal){
 for(let attempt=0;attempt<4;attempt++){
  signal.throwIfAborted();
  try{
   const response=await fetch(url,{method:'PUT',body:blob,signal:requestSignal(signal)});
   if(response.ok)return;
   const detail=await response.json().catch(()=>({}));
   const message=typeof detail.detail==='string'?detail.detail:`Server kadrni qabul qilmadi (HTTP ${response.status}).`;
   if(![408,429,500,502,503,504].includes(response.status))throw Object.assign(Error(message),{terminal:true});
   throw Error(message);
  }catch(error){
   signal.throwIfAborted();
   if(attempt===3||(error as {terminal?:boolean}).terminal)throw error;
  }
  await new Promise<void>((resolve,reject)=>{
   const abort=()=>{clearTimeout(timer);reject(signal.reason)};
   const timer=setTimeout(()=>{signal.removeEventListener('abort',abort);resolve()},500*2**attempt);
   signal.addEventListener('abort',abort,{once:true});if(signal.aborted)abort();
  });
 }
}
