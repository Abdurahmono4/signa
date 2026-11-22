/** Bounded downloads retain timeline order and cancel sibling requests on failure. */
export async function mapMotionAssets<T,R>(items:readonly T[],load:(item:T,index:number,signal:AbortSignal)=>Promise<R>,options:{signal?:AbortSignal;concurrency?:number}={}):Promise<R[]>{
 const concurrency=options.concurrency??3;
 if(!Number.isInteger(concurrency)||concurrency<1||concurrency>4)throw Error('Yuklash chegarasi 1–4 bo‘lishi kerak.');
 const controller=new AbortController(),parent=options.signal;
 const abort=()=>controller.abort(parent?.reason);
 if(parent?.aborted)abort();else parent?.addEventListener('abort',abort,{once:true});
 const result=new Array<R>(items.length);let next=0;
 async function worker(){
  while(true){
   controller.signal.throwIfAborted();
   const index=next++;
   if(index>=items.length)return;
   result[index]=await load(items[index],index,controller.signal);
   controller.signal.throwIfAborted();
  }
 }
 const workers=Array.from({length:Math.min(concurrency,items.length)},()=>worker());
 try{controller.signal.throwIfAborted();await Promise.all(workers);return result}
 catch(error){controller.abort(error);await Promise.allSettled(workers);throw error}
 finally{parent?.removeEventListener('abort',abort)}
}
