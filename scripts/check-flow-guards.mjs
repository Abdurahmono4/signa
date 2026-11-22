import assert from 'node:assert/strict';
import {assertExportOwnership,requestSignal,neuralPollAction,assertMotionBudget} from '../frontend/src/flowGuards.ts';

const own='a'.repeat(32),other='b'.repeat(32);
assert.doesNotThrow(()=>assertExportOwnership({status:'frames',render_token:own},own));
assert.doesNotThrow(()=>assertExportOwnership({status:'rendering',render_token:own},own));
assert.doesNotThrow(()=>assertExportOwnership({status:'done',render_token:own,result_token:own},own));
for(const status of ['frames','queued','rendering','done']){
 assert.throws(()=>assertExportOwnership({status,render_token:other,result_token:other},own),/boshqa oynada/);
}
assert.throws(()=>assertExportOwnership({status:'done',render_token:own,result_token:other},own),/ushbu eksportga/);
assert.throws(()=>assertExportOwnership({status:'done',render_token:own},own),/ushbu eksportga/);
assert.throws(()=>assertExportOwnership({status:'ready'},own),/boshqa oynada/);

assert.equal(neuralPollAction('ready'),'load');
for(const status of ['queued','running','processing'])assert.equal(neuralPollAction(status),'continue');
for(const status of ['idle','failed','cancelled','unknown',''])assert.equal(neuralPollAction(status),'retry');

const controller=new AbortController();
const owned=requestSignal(controller.signal,1000);
assert.equal(owned.aborted,false);controller.abort(new Error('user cancelled'));
assert.equal(owned.aborted,true);assert.equal(owned.reason.message,'user cancelled');
const cancelled=new AbortController();cancelled.abort('already cancelled');
assert.equal(requestSignal(cancelled.signal,1000).reason,'already cancelled');
for(const invalid of [0,-1,Infinity,NaN])assert.throws(()=>requestSignal(undefined,invalid));
const timed=requestSignal(undefined,10);
await new Promise(resolve=>setTimeout(resolve,30));
assert.equal(timed.aborted,true);assert.equal(timed.reason.name,'TimeoutError');
console.log('Flow guards passed: export ownership, neural restart recovery, request cancellation and deadline.');
const budget={max_chunks:75,max_frames:30000};
assert.doesNotThrow(()=>assertMotionBudget(31,10001,budget));
assert.doesNotThrow(()=>assertMotionBudget(75,30000,budget));
assert.throws(()=>assertMotionBudget(76,30000,budget));
assert.throws(()=>assertMotionBudget(75,30001,budget));
assert.throws(()=>assertMotionBudget(NaN,10,budget));
assert.throws(()=>assertMotionBudget(1,1,{max_chunks:100,max_frames:30000}));
console.log('Motion budgets passed: expanded boundary, excess chunks/frames and invalid limits.');
