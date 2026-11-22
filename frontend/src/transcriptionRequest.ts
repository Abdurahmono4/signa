type RevisionedJob={id:string;transcript_revision?:number;status:string};
/** A lost POST response may still mean the server accepted the job. Never replay it. */
export async function startTranscriptionOnce<T extends RevisionedJob>(job:T,submit:()=>Promise<T>,read:()=>Promise<T>):Promise<T>{
 try{return await submit()}
 catch(error){
  try{
   const current=await read();
   if(current.id===job.id&&(current.transcript_revision??0)>(job.transcript_revision??0))return current;
  }catch{/* Preserve the original failure if recovery also loses its connection. */}
  throw error;
 }
}
