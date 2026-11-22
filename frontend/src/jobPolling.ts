/** One in-flight request; late responses from a previous job are discarded. */
export function pollJob<T>(load:(signal:AbortSignal)=>Promise<T>,receive:(value:T)=>void,fail:(error:unknown)=>void,delay=1000):()=>void{
 const controller=new AbortController();
 let timer:ReturnType<typeof setTimeout>|undefined;
 async function tick(){
  try{const value=await load(controller.signal);if(!controller.signal.aborted)receive(value)}
  catch(error){if(!controller.signal.aborted)fail(error)}
  finally{if(!controller.signal.aborted)timer=setTimeout(tick,delay)}
 }
 void tick();
 return()=>{controller.abort();if(timer!==undefined)clearTimeout(timer)};
}
