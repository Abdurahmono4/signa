import {requestSignal} from './flowGuards.ts';

export class HttpReadError extends Error {
 status:number;
 constructor(status:number,message:string){super(message);this.name='HttpReadError';this.status=status}
}
const transient=new Set([408,429,500,502,503,504]);
export function waitForRetry(ms:number,signal?:AbortSignal):Promise<void>{
 return new Promise((resolve,reject)=>{
  if(signal?.aborted){reject(signal.reason);return}
  const aborted=()=>{clearTimeout(timer);signal?.removeEventListener('abort',aborted);reject(signal?.reason)};
  const timer=setTimeout(()=>{signal?.removeEventListener('abort',aborted);resolve()},ms);
  signal?.addEventListener('abort',aborted,{once:true});
 });
}
/** Retry reads only. Mutations must never be replayed without an idempotency contract. */
export async function readJson<T>(path:string,options:{signal?:AbortSignal;attempts?:number;delayMs?:number;timeoutMs?:number}={}):Promise<T>{
 const {signal,attempts=3,delayMs=500,timeoutMs=30000}=options;
 if(!Number.isInteger(attempts)||attempts<1||attempts>4||!Number.isFinite(delayMs)||delayMs<0)throw Error('Qayta urinish chegarasi yaroqsiz.');
 for(let attempt=0;attempt<attempts;attempt++){
  signal?.throwIfAborted();
  try{
   const response=await fetch(path,{method:'GET',signal:requestSignal(signal,timeoutMs)});
   if(!response.ok){
    const body=await response.json().catch(()=>null);
    throw new HttpReadError(response.status,typeof body?.detail==='string'?body.detail:`Server javob bermadi (HTTP ${response.status}).`);
   }
   if(!/\bapplication\/(?:[\w.-]+\+)?json\b/i.test(response.headers.get('content-type')||''))throw Error('Server ma’lumot o‘rniga veb-sahifa qaytardi. Backend ulanishini tekshiring.');
   return await response.json() as T;
  }catch(error){
   signal?.throwIfAborted();
   const retryable=error instanceof HttpReadError?transient.has(error.status):error instanceof TypeError||(error instanceof Error&&error.name==='TimeoutError');
   if(!retryable||attempt===attempts-1)throw error;
   await waitForRetry(delayMs*2**attempt,signal);
  }
 }
 throw Error('Server ma’lumoti olinmadi.');
}
