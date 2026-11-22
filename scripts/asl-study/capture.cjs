/* Export silent comprehension stimuli from the production Rocketbox/Three.js scene.
 * Usage: node scripts/asl-study/capture.cjs <output-folder> [motion-corpus]
 * Requires the local Vite/backend servers, playwright-core, Chrome and project FFmpeg.
 */
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright-core');
const root = path.resolve(__dirname, '../..');
const frontend = path.join(root, 'frontend');
const samplesDir = process.argv[3] ? path.resolve(process.argv[3]) : path.join(root, 'docs/asl-comparison-10');
const base = 'http://127.0.0.1:5174';
const read = file => JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const harness = `
import React from 'react';
import {createRoot} from 'react-dom/client';
import {AvatarStage} from '../src/NaturalAvatarTimeline';
import {validateNeuralMotion} from '../src/neuralMotion';
const root=createRoot(document.getElementById('scene'));
window.loadStimulus=motion=>new Promise((resolve,reject)=>{
 const timer=setTimeout(()=>reject(Error('Avatar capture was not ready')),30000);
 const frames=validateNeuralMotion(motion);
 const duration=frames.length/motion.fps;
 const items=[{start:0,end:duration,duration,text:'',motion}];
 root.render(React.createElement(AvatarStage,{key:motion.id,items,time:0,onCapture:fn=>{
  if(fn){window.captureAt=fn;clearTimeout(timer);resolve();}
 }}));
});
`;
async function main() {
 if (!process.argv[2]) throw Error('Specify the output folder for silent clips.');
 const out = path.resolve(process.argv[2]);
 fs.mkdirSync(out, {recursive:true});
 const toolsDir = path.join(root, 'tools/ffmpeg');
 const ffBin = path.join(toolsDir, fs.readdirSync(toolsDir).find(d => fs.existsSync(path.join(toolsDir,d,'bin/ffmpeg.exe'))), 'bin');
 const pageDir = fs.mkdtempSync(path.join(frontend, 'study-capture-'));
 const pngDir = fs.mkdtempSync(path.join(os.tmpdir(),'signbridge-study-'));
 const pageFile = path.join(pageDir,'index.html'), moduleFile = path.join(pageDir,'capture.jsx');
 let browser;
 try {
  fs.writeFileSync(pageFile,'<!doctype html><meta charset=utf-8><div id="scene"></div><script type="module" src="./capture.jsx"></script>');
  fs.writeFileSync(moduleFile,harness);
  browser=await chromium.launch({executablePath:process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
   headless:true,args:['--enable-webgl','--enable-unsafe-swiftshader','--disable-background-timer-throttling']});
  const page=await browser.newPage({viewport:{width:1080,height:840}});
  page.on('pageerror',error=>console.error(error.message));
  await page.goto(base+'/'+path.basename(pageDir)+'/index.html');
  await page.waitForFunction(()=>typeof window.loadStimulus==='function');
  for (const [index,sample] of read(path.join(samplesDir,'samples.json')).entries()) {
   const motion=read(path.join(samplesDir,'model',String(index).padStart(4,'0'),'motion.json'));
   if(motion.id!==sample.id || motion.text!==sample.text || motion.frame_count!==motion.features.length)
    throw Error('Source caption and stored motion do not match');
   await page.evaluate(m=>window.loadStimulus(m),motion);
   const file=path.join(out,'avatar-'+sample.id+'.mp4');
   for(let k=0;k<motion.frame_count;k++){
    const png=await page.evaluate(async time=>{
     const blob=await window.captureAt(time);
     const reader=new FileReader();
     return new Promise((resolve,reject)=>{
      reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(reader.error);
      reader.readAsDataURL(blob);
     });
    },k/motion.fps);
    fs.writeFileSync(path.join(pngDir,String(k).padStart(5,'0')+'.png'),Buffer.from(png,'base64'));
   }
   const temp=path.join(pngDir,'review.mp4');
   execFileSync(path.join(ffBin,'ffmpeg.exe'),['-v','error','-y','-framerate',String(motion.fps),
    '-i',path.join(pngDir,'%05d.png'),'-f','lavfi','-i','color=c=0x111318:s=1024x768:r='+motion.fps,
    '-filter_complex','[1:v][0:v]overlay=shortest=1,scale=768:576,format=yuv420p[v]','-map','[v]',
    '-frames:v',String(motion.frame_count),'-an','-sn','-map_metadata','-1','-c:v','libx264','-crf','17','-movflags','+faststart',temp]);
   const probe=JSON.parse(execFileSync(path.join(ffBin,'ffprobe.exe'),['-v','error','-show_streams','-of','json',temp]));
   if (probe.streams.length!==1 || probe.streams[0].codec_type!=='video' ||
       Number(probe.streams[0].nb_frames)!==motion.frame_count) throw Error('Stimulus validation failed');
   fs.copyFileSync(temp,file);
   for(const name of fs.readdirSync(pngDir))fs.unlinkSync(path.join(pngDir,name));
   console.log('Rendered stimulus',sample.id,motion.frame_count);
  }
 } finally {
  if(browser)await browser.close();
  for(const name of fs.readdirSync(pngDir))fs.unlinkSync(path.join(pngDir,name));
  fs.rmdirSync(pngDir);
  for(const file of [pageFile,moduleFile])if(fs.existsSync(file))fs.unlinkSync(file);
  fs.rmdirSync(pageDir);
 }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
