import assert from 'node:assert/strict';
import {mapMotionAssets} from '../frontend/src/motionLoading.ts';
import {waitForRetry} from '../frontend/src/readJson.ts';
let active=0,peak=0;
const values=Array.from({length:9},(_,index)=>index);
const result=await mapMotionAssets(values,async(value,_index,signal)=>{
 active++;peak=Math.max(peak,active);
 try{await waitForRetry(value%3===0?20:2,signal);return {index:value,frame:[value,0,1]}}
 finally{active--}
});
assert.deepEqual(result,values.map(value=>({index:value,frame:[value,0,1]})));
assert.equal(peak,3);assert.equal(active,0);
let started=0,aborted=0;
await assert.rejects(mapMotionAssets(values,async(value,_index,signal)=>{
 started++;
 if(value===0){await waitForRetry(2,signal);throw Error('corrupt motion')}
 try{await waitForRetry(100,signal)}catch(error){aborted++;throw error}
 return value;
}),/corrupt motion/);
assert.equal(started,3);assert.equal(aborted,2,'Sibling downloads must stop on invalid motion');
const controller=new AbortController();started=0;
const pending=mapMotionAssets(values,async(value,_index,signal)=>{started++;await waitForRetry(100,signal);return value},{signal:controller.signal});
controller.abort(new Error('cancel motion load'));
await assert.rejects(pending,/cancel motion load/);assert.equal(started,3);
await assert.rejects(mapMotionAssets([],async x=>x,{signal:controller.signal}),/cancel motion load/);
for(const concurrency of [0,5,NaN,1.5])await assert.rejects(mapMotionAssets(values,async x=>x,{concurrency}));
assert.deepEqual(await mapMotionAssets([],async x=>x),[]);
console.log('PASS: bounded parallel motion downloads, preserved order/data, failure cleanup and cancellation.');
