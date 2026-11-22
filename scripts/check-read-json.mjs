import assert from 'node:assert/strict';
import {readJson,waitForRetry} from '../frontend/src/readJson.ts';
const original=globalThis.fetch;
const json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json'}});
try{
 let calls=0;
 globalThis.fetch=async(_url,options)=>{assert.equal(options.method,'GET');if(++calls===1)throw new TypeError('offline');if(calls===2)return new Response('gateway offline',{status:503});return json({status:'done',result_token:'same-export'})};
 assert.deepEqual(await readJson('/api/job',{delayMs:1}),{status:'done',result_token:'same-export'});assert.equal(calls,3);
 for(const status of [401,403,404,409,422]){
  calls=0;globalThis.fetch=async()=>{calls++;return json({detail:'terminal'},status)};
  await assert.rejects(readJson('/api/job',{delayMs:1}),/terminal/);assert.equal(calls,1);
 }
 calls=0;globalThis.fetch=async()=>{calls++;return new Response('<html>SPA fallback</html>',{headers:{'content-type':'text/html'}})};
 await assert.rejects(readJson('/api/job',{delayMs:1}),/Backend/);assert.equal(calls,1);
 calls=0;globalThis.fetch=async()=>{calls++;return new Response('{invalid',{headers:{'content-type':'application/json'}})};
 await assert.rejects(readJson('/api/job',{delayMs:1}),SyntaxError);assert.equal(calls,1);
 calls=0;globalThis.fetch=async()=>{calls++;return json({detail:'unavailable'},503)};
 await assert.rejects(readJson('/api/job',{delayMs:1}),/unavailable/);assert.equal(calls,3);
 const stopped=new AbortController();stopped.abort(new Error('user stopped'));calls=0;
 await assert.rejects(readJson('/api/job',{signal:stopped.signal}),/user stopped/);assert.equal(calls,0);
 await assert.rejects(waitForRetry(1,stopped.signal),/user stopped/);
 const during=new AbortController();calls=0;
 globalThis.fetch=async()=>{calls++;return json({},503)};
 const pending=readJson('/api/job',{signal:during.signal,delayMs:100});
 setTimeout(()=>during.abort(new Error('cancel backoff')),10);
 await assert.rejects(pending,/cancel backoff/);assert.equal(calls,1);
 calls=0;globalThis.fetch=async(_url,options)=>{calls++;if(calls===2)return json({recovered:true});return new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(options.signal.reason),{once:true}))};
 // Keep Node alive while AbortSignal.timeout's unreferenced timer expires.
 const hold=setTimeout(()=>{},1000);
 try{assert.deepEqual(await readJson('/api/job',{timeoutMs:5,delayMs:1}),{recovered:true});assert.equal(calls,2)}finally{clearTimeout(hold)}
 console.log('PASS: network/503/timeout recovery, bounded GET retries, terminal errors, HTML/malformed JSON, cancellation.');
}finally{globalThis.fetch=original}
