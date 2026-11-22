import assert from 'node:assert/strict';
import {uploadFrame} from '../frontend/src/frameUpload.ts';
const original=globalThis.fetch,blob=new Blob(['frame']),signal=new AbortController().signal;
try{
 let calls=0;const bodies=[];
 globalThis.fetch=async(url,options)=>{calls++;bodies.push(options.body);if(calls===1)throw new TypeError('network lost');return new Response('',{status:200})};
 await uploadFrame('/same/session/frame/1',blob,signal);assert.equal(calls,2);assert.ok(bodies.every(b=>b===blob));
 calls=0;globalThis.fetch=async()=>{calls++;return new Response('',{status:calls===1?503:200})};
 await uploadFrame('/same',blob,signal);assert.equal(calls,2);
 for(const status of [409,413,422]){
  calls=0;globalThis.fetch=async()=>{calls++;return new Response(JSON.stringify({detail:'invalid frame'}),{status})};
  await assert.rejects(uploadFrame('/same',blob,signal),/invalid frame/);assert.equal(calls,1);
 }
 const cancelled=new AbortController();cancelled.abort(new Error('cancelled'));calls=0;
 await assert.rejects(uploadFrame('/same',blob,cancelled.signal),/cancelled/);assert.equal(calls,0);
 console.log('Frame upload: network/503 recovery, identical frame body, terminal validation errors and cancellation passed.');
}finally{globalThis.fetch=original}
