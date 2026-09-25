import test from 'node:test';
import assert from 'node:assert/strict';
import {createStepReader} from '../frontend/speech.js';

function setup() {
  const states=[], errors=[], spoken=[];
  let cancellations=0;
  const host={navigator:{language:'en-IN'},SpeechSynthesisUtterance:class{constructor(text){this.text=text;}},speechSynthesis:{
    getVoices:()=>[{lang:'fr-FR',name:'French'},{lang:'en-IN',name:'English Natural'}],
    speak:utterance=>spoken.push(utterance),cancel:()=>cancellations++
  }};
  return {host,states,errors,spoken,get cancellations(){return cancellations;},reader:createStepReader(host,state=>states.push(state),()=>errors.push(true))};
}
test('reads only the selected instruction with English voice and a measured pace',()=>{
  const s=setup();s.reader.toggle('Simmer for 5 minutes.',3);
  assert.equal(s.spoken[0].text,'Step 3. Simmer for 5 minutes.');
  assert.equal(s.spoken[0].voice.lang,'en-IN');assert.equal(s.spoken[0].rate,0.9);
  s.spoken[0].onend();assert.equal(s.states.at(-1),true);
});
test('stop prevents stale callbacks from changing a newer read',()=>{
  const s=setup();s.reader.toggle('First.',1);const old=s.spoken[0];
  s.reader.stop();s.reader.toggle('Second.',2);
  old.onend();old.onerror({error:'audio-busy'});
  assert.equal(s.states.at(-1),true);assert.equal(s.errors.length,0);
  s.reader.toggle('Second.',2);assert.equal(s.states.at(-1),false);assert.equal(s.spoken.length,2);
});
test('reports speech engine errors and permits retry',()=>{
  const s=setup();s.reader.toggle('Stir.',1);s.spoken[0].onerror({error:'not-allowed'});
  assert.equal(s.errors.length,1);assert.equal(s.states.at(-1),false);
  s.reader.toggle('Stir.',1);assert.equal(s.spoken.length,2);
});
test('works before voices load and handles an unsupported browser',()=>{
  const s=setup();s.host.speechSynthesis.getVoices=()=>[];s.reader.toggle('Stir.',1);
  assert.equal(s.spoken[0].lang,'en-IN');
  const reader=createStepReader({},()=>{},()=>assert.fail());
  assert.equal(reader.supported,false);reader.toggle('Stir.',1);reader.stop();
});
test('listening continues after completion and stops only when disabled',()=>{
  const s=setup();s.reader.next('Silent.',1);assert.equal(s.spoken.length,0);
  s.reader.toggle('First.',1);s.spoken[0].onend();
  s.reader.next('Second.',2);assert.equal(s.spoken[1].text,'Step 2. Second.');
  s.reader.next('Third.',3);assert.equal(s.spoken[2].text,'Step 3. Third.');
  s.spoken[1].onerror({error:'interrupted'});assert.equal(s.states.at(-1),true);
  s.reader.toggle('Third.',3);s.reader.next('Fourth.',4);
  assert.equal(s.spoken.length,3);assert.equal(s.states.at(-1),false);
});
