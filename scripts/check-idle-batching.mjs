import fs from 'node:fs';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
const source=fs.readFileSync('frontend/src/avatarTimeline.ts','utf8');
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {presentationAt}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const plan=await (await fetch('http://127.0.0.1:8001/api/jobs/d77a812112ce40eb89e346e2b912b9dc/neural/plan')).json();
const items=plan.items.filter(i=>i.neural_asset).map(i=>({...i,duration:i.end-i.start}));
const count=Math.ceil(plan.output_duration*24);
let captures=0,skipped=0;
for(let n=0;n<count;n++){
 const idle=i=>{const p=presentationAt(items,i/24);return !p.from&&!p.to};
 let repeat=1;
 if(idle(n))while(repeat<48&&n+repeat<count&&idle(n+repeat))repeat++;
 for(let i=1;i<repeat;i++)if(!idle(n+i))throw Error('Skipped animation');
 captures++;skipped+=repeat-1;n+=repeat-1;
}
console.log(JSON.stringify({frames:count,captures,staticFramesReused:skipped,reductionPercent:100*skipped/count}));
