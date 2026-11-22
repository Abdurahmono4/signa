/** Reject state from another tab's export before using its progress or result. */
export function assertExportOwnership(state:{render_token?:string;result_token?:string;status:string},token:string):void{
 if(!token||state.render_token!==token)throw Error('Eksport boshqa oynada o‘zgargan. Holatni yangilang va qayta urinib ko‘ring.');
 if(state.status==='done'&&state.result_token!==token)throw Error('Tayyor video ushbu eksportga tegishli emas. Holatni yangilang.');
}

/** A request can be cancelled by its owner and must also finish by its deadline. */
export function requestSignal(parent?:AbortSignal,ms=30000):AbortSignal{
 if(!Number.isFinite(ms)||ms<=0)throw Error('So‘rov vaqti musbat son bo‘lishi kerak.');
 const deadline=AbortSignal.timeout(ms);
 return parent?AbortSignal.any([parent,deadline]):deadline;
}

/** An idle worker after enqueue usually means the server restarted; stop waiting. */
export function neuralPollAction(status:string):'load'|'continue'|'retry'{
 if(status==='ready')return 'load';
 if(['queued','processing','running'].includes(status))return 'continue';
 return 'retry';
}

export type MotionBudget={max_chunks:number;max_frames:number};
export function assertMotionBudget(chunks:number,frames:number,budget:MotionBudget):void{
 if(![chunks,frames,budget.max_chunks,budget.max_frames].every(Number.isSafeInteger)||chunks<0||frames<0||budget.max_chunks<1||budget.max_frames<1||budget.max_chunks>75||budget.max_frames>30000)throw Error('Harakat chegarasi yaroqsiz.');
 if(chunks>budget.max_chunks||frames>budget.max_frames)throw Error('Harakat hajmi ushbu ish chegarasidan oshdi. Videoni qisqaroq bo‘laklarga ajrating.');
}
