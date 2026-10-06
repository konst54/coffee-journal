import test from 'node:test';
import assert from 'node:assert/strict';
import {mountAuthBar} from '../authbar.js';

class El { constructor(t){this.tagName=t;this.children=[];this.listeners={};this._t='';}
  set textContent(s){this._t=String(s);} get textContent(){return this._t+this.children.map(c=>c.textContent).join('');}
  replaceChildren(...n){this.children=n;} setAttribute(k,v){this[k]=v;} addEventListener(k,f){this.listeners[k]=f;} }
const doc={createElement:t=>new El(t)};
const find=(n,t)=>[...(n.tagName===t?[n]:[]),...n.children.flatMap(c=>find(c,t))];
const demo={schema_version:1,coffees:[],batches:[],equipment:[],recipes:[],brews:[]};

test('signed out: only an e-mail field and a button, no forms or password fields', async () => {
  const root=new El('div'); let sent;
  const auth={loadOwnJournal:async()=>null, sendMagicLink:async e=>{sent=e;}};
  const viewer={loadDataset(){}, loadAuthenticated(){}};
  await mountAuthBar(root,{auth,viewer,demo,doc}).refresh('');
  const inputs=find(root,'input');
  assert.equal(inputs.length,1); assert.equal(inputs[0].type,'email');
  assert.equal(find(root,'form').length,0);
  inputs[0].value='me@example.org'; await find(root,'button')[0].listeners.click();
  assert.equal(sent,'me@example.org'); assert.match(root.textContent,/Ссылка отправлена/);
});

test('signed in shows private data and logout returns to demo', async () => {
  const root=new El('div'); const calls=[];
  const auth={loadOwnJournal:async()=>({authenticated:true,dataset:demo}), logout:async()=>calls.push('logout')};
  const viewer={loadDataset:d=>calls.push('demo'), loadAuthenticated:async f=>{calls.push((await f()).authenticated);}};
  await mountAuthBar(root,{auth,viewer,demo,doc}).refresh('');
  assert.deepEqual(calls,[true]);
  await find(root,'button')[0].listeners.click();
  assert.deepEqual(calls,[true,'logout','demo']);
  assert.match(root.textContent,/Вы вышли/);
});

test('load failure falls back to demo with a message', async () => {
  const root=new El('div'); const calls=[];
  const auth={loadOwnJournal:async()=>{throw new Error('x');}};
  const viewer={loadDataset:()=>calls.push('demo')};
  await mountAuthBar(root,{auth,viewer,demo,doc}).refresh('');
  assert.deepEqual(calls,['demo']); assert.match(root.textContent,/Показана демонстрация/);
});
