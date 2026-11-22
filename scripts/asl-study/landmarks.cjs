/* Run the same independent image-mode detector on EVERY decoded RGB frame.
 * No audio, captions, motion arrays or filenames are passed to MediaPipe.
 * Usage: node scripts/asl-study/landmarks.cjs <study-dir> <holistic_landmarker.task>
 */
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const http=require('node:http');
const crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {chromium}=require('playwright-core');
const root=path.resolve(__dirname,'../..');
const corpus=path.join(root,'docs/asl-comparison-10');
const vision=path.dirname(require.resolve('@mediapipe/tasks-vision'));
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
async function main(){
 const dir=path.resolve(process.argv[2]),task=path.resolve(process.argv[3]);
 const ffDir=path.join(root,'tools/ffmpeg');
 const ff=path.join(ffDir,fs.readdirSync(ffDir).find(n=>fs.existsSync(path.join(ffDir,n,'bin/ffmpeg.exe'))),'bin');
 const resources=new Map([['/vision.mjs',[path.join(vision,'vision_bundle.mjs'),'text/javascript']],['/model.task',[task,'application/octet-stream']]]);
 for(const n of fs.readdirSync(path.join(vision,'wasm'))){
  resources.set('/wasm/'+n,[path.join(vision,'wasm',n),n.endsWith('.wasm')?'application/wasm':'text/javascript']);
 }
 const framesDir=fs.mkdtempSync(path.join(os.tmpdir(),'signbridge-landmarks-'));
 const homePage='<!doctype html><meta charset="utf-8"><title>Offline landmark extraction</title>';
 let current=[];
 const server=http.createServer((req,res)=>{
  const p=req.url.split('?')[0];
  res.setHeader('Cache-Control','no-store');
  if(p==='/'){res.setHeader('Content-Type','text/html');return res.end(homePage)}
  const resource=resources.get(p);
  if(!resource){res.writeHead(404);return res.end()}
  res.setHeader('Content-Type',resource[1]);fs.createReadStream(resource[0]).on('error',()=>res.destroy()).pipe(res);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port;
 let browser;
 try{
  browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,
   args:['--enable-webgl','--enable-unsafe-swiftshader','--disable-background-timer-throttling']});
  const page=await browser.newPage();
  await page.goto(url);
  await page.evaluate(async()=>{
   const {FilesetResolver,HolisticLandmarker}=await import('/vision.mjs');
   const files=await FilesetResolver.forVisionTasks('/wasm');
   const detector=await HolisticLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:'/model.task',delegate:'CPU'},runningMode:'IMAGE'});
   window.extract=async payloads=>{
    const frames=[];
    for(const base64 of payloads){
     const image=new Blob([Uint8Array.fromBase64(base64)],{type:'image/png'});
     const img=await createImageBitmap(image);
     try{
      const result=detector.detect(img);
      const body=result.poseLandmarks[0];
      const landmark=(p)=>[p.x*img.width,p.y*img.height,p.visibility??1];
      const hand=group=>group[0]?.map(p=>landmark(p).slice(0,2))??null;
      frames.push({body:body?[11,12,15,16].map(j=>landmark(body[j])):null,
       left:hand(result.leftHandLandmarks),right:hand(result.rightHandLandmarks)});
     }finally{img.close()}
    }
    return frames;
   };
  });
  const samples=JSON.parse(fs.readFileSync(path.join(corpus,'samples.json'),'utf8'));
  const record={model_sha256:sha(task),package:JSON.parse(fs.readFileSync(path.join(vision,'package.json'),'utf8')).version,
   detector:'MediaPipe HolisticLandmarker, CPU, IMAGE, default thresholds',clips:[]};
  const alternates=process.argv[4]==='--alternates';
  const reference=process.argv[4]==='--reference';
  const published=process.argv[4]==='--published';
  const inputs=published?samples.map(s=>({kind:'published',id:s.id,video:path.join(dir,'published',s.id+'.mp4')})):alternates
   ?JSON.parse(fs.readFileSync(path.join(dir,'alternate-human/manifest.json'),'utf8')).complete.map(s=>({
     kind:'alternate',id:s.id,video:path.join(dir,'alternate-human',s.id+'.mp4')
   }))
   :(reference?['reference']:['human','avatar']).flatMap(kind=>samples.map(s=>({kind,id:s.id,
     video:kind==='human'?path.join(corpus,'human',s.id+'.mp4'):path.join(dir,'avatar','avatar-'+s.id+'.mp4')
   })));
  for(const {kind,id,video} of inputs){
    const probe=JSON.parse(execFileSync(path.join(ff,'ffprobe.exe'),['-v','error','-select_streams','v:0','-show_streams','-of','json',video])).streams[0];
    execFileSync(path.join(ff,'ffmpeg.exe'),['-v','error','-i',video,'-map','0:v:0','-an','-sn','-fps_mode','passthrough','-start_number','0',path.join(framesDir,'%05d.png')]);
    current=fs.readdirSync(framesDir).sort().map(n=>path.join(framesDir,n));
    if(current.length!==Number(probe.nb_frames))throw Error('Decoded frame count mismatch');
    const frames=[];
    for(let k=0;k<current.length;k+=6){
     const payloads=current.slice(k,k+6).map(file=>fs.readFileSync(file).toString('base64'));
     frames.push(...await page.evaluate(batch=>window.extract(batch),payloads));
    }
    record.clips.push({id,kind,sha256:sha(video),width:probe.width,height:probe.height,fps:probe.avg_frame_rate,frames});
    console.log(kind,id,frames.length,'frames, hands detected:',frames.filter(f=>f.left).length,frames.filter(f=>f.right).length);
    for(const f of current)fs.unlinkSync(f);
    current=[];
  }
  fs.writeFileSync(path.join(dir,published?'published-landmarks.json':alternates?'alternate-landmarks.json':'landmarks.json'),JSON.stringify(record));
 }finally{
  if(browser)await browser.close();
  server.close();
  for(const f of fs.readdirSync(framesDir))fs.unlinkSync(path.join(framesDir,f));
  fs.rmdirSync(framesDir);
 }
}
main().catch(e=>{console.error(e);process.exitCode=1});
