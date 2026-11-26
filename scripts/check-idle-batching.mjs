import fs from 'node:fs';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
const source=fs.readFileSync('frontend/src/avatarTimeline.ts','utf8');
const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {presentationAt}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const job=process.argv[2];
if(!job||!/^[a-f0-9]{32}$/.test(job))throw Error('Usage: node scripts/check-idle-batching.mjs <job-id>');
const response=await fetch('http://127.0.0.1:8001/api/jobs/'+job+'/neural/plan');
const plan=await response.json();
if(!response.ok)throw Error('Motion plan: '+response.status+' '+plan.detail);
let blockedBefore=false;
const items=plan.items.flatMap(item=>{
 if(!item.neural_asset){if(item.unsupported)blockedBefore=true;return []}
 const interval={...item,duration:item.duration_ms/1000,blockedBefore};
 blockedBefore=false;
 return [interval];
});
const fps=Number(process.argv[3]??30);
if(!Number.isSafeInteger(fps)||fps<1||fps>120)throw Error('Invalid export FPS');
const count=Math.ceil(plan.output_duration*fps);
let captures=0,skipped=0;
for(let n=0;n<count;n++){
 const idle=i=>{const p=presentationAt(items,i/fps);return !p.from&&!p.to};
 let repeat=1;
 if(idle(n))while(repeat<48&&n+repeat<count&&idle(n+repeat))repeat++;
 for(let i=1;i<repeat;i++)if(!idle(n+i))throw Error('Skipped animation');
 captures++;skipped+=repeat-1;n+=repeat-1;
}
console.log(JSON.stringify({frames:count,captures,staticFramesReused:skipped,reductionPercent:100*skipped/count}));
