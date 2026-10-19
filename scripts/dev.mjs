import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const python = path.join(root,'backend','.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const vite = path.join(root,'frontend','node_modules','vite','bin','vite.js');
if (!existsSync(python) || !existsSync(vite)) {
  console.error('Avval npm run setup buyrug‘ini bajaring.'); process.exit(1);
}
const children = [];
let stopping = false;
function stop(code=0){
  if(stopping)return; stopping=true;
  for(const child of children){
    if(process.platform==='win32' && child.pid) spawn('taskkill',['/pid',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});
    else child.kill('SIGTERM');
  }
  setTimeout(()=>process.exit(code),600);
}
for (const [command,args,cwd] of [
  [python,['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],path.join(root,'backend')],
  [process.execPath,[vite,'--host','127.0.0.1'],path.join(root,'frontend')]
]) {
  const child=spawn(command,args,{cwd,stdio:'inherit',windowsHide:true});children.push(child);
  child.on('error',error=>{console.error(error.message);stop(1)});
  child.on('exit',code=>{if(!stopping)stop(code??1)});
}
process.on('SIGINT',()=>stop());process.on('SIGTERM',()=>stop());
console.log('\nSigna: http://127.0.0.1:5173 | API: http://127.0.0.1:8000/docs\nTo‘xtatish: Ctrl+C\n');
