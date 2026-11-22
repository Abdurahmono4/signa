import assert from 'node:assert/strict';
import {startTranscriptionOnce} from '../frontend/src/transcriptionRequest.ts';
const original={id:'one',status:'uploaded',transcript_revision:0};
const accepted={...original,status:'queued',transcript_revision:1};
let posts=0,reads=0;
assert.deepEqual(await startTranscriptionOnce(original,async()=>{posts++;return accepted},async()=>{reads++;return accepted}),accepted);
assert.equal(posts,1);assert.equal(reads,0);
posts=0;reads=0;
const lost=new Error('POST response lost');
assert.deepEqual(await startTranscriptionOnce(original,async()=>{posts++;throw lost},async()=>{reads++;return accepted}),accepted);
assert.equal(posts,1,'Never repeat a possibly accepted POST');assert.equal(reads,1);
for(const current of [original,{...accepted,id:'another-job'},{...original,status:'ready'}]){
 await assert.rejects(startTranscriptionOnce(original,async()=>{throw lost},async()=>current),error=>error===lost);
}
await assert.rejects(startTranscriptionOnce(original,async()=>{throw lost},async()=>{throw Error('GET failed')}),error=>error===lost);
const retry={...original,status:'failed',transcript_revision:4};
assert.equal((await startTranscriptionOnce(retry,async()=>{throw lost},async()=>({...retry,status:'processing',transcript_revision:5}))).status,'processing');
console.log('PASS: accepted POST recovery, no duplicate submission, matching job/revision, original failure preservation.');
