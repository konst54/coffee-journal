import test from 'node:test';
import assert from 'node:assert/strict';
import * as view from '../app.js';

class Element {
  constructor(tag) {this.tagName=tag;this.children=[];this.dataset={};this.listeners={};this.hidden=false;this._text='';}
  set textContent(s){this._text=String(s);this.children=[];}
  get textContent(){return this._text+this.children.map(x=>x.textContent).join('');}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this._text='';this.children=nodes;}
  setAttribute(k,v){this[k]=v;}
  addEventListener(k,f){this.listeners[k]=f;}
}
const doc={createElement:tag=>new Element(tag)};
const all=(node,tag)=>[...(node.tagName===tag?[node]:[]),...node.children.flatMap(c=>all(c,tag))];
const data={schema_version:1,coffees:[{id:'c',name:'<img src=x onerror=alert(1)>'}],batches:[{id:'b',coffee_id:'c',roast_date:null}],equipment:[],recipes:[],brews:Array.from({length:4},(_,i)=>({id:String(i),batch_id:'b',taste_notes:'Нота',rating:i}))};

test('read-only viewer labels demo, renders literal strings and limits comparison to three', () => {
 const root=new Element('main'); const api=view.createViewer(root,doc);
 api.loadDataset(data);
 assert.match(root.textContent,/Вымышленные/);
 assert.match(root.textContent,/<img src=x onerror=alert\(1\)>/);
 assert.equal(all(root,'img').length,0);
 assert.equal(all(root,'form').length,0);
 assert.equal(all(root,'article').length,4);
 let checks=all(root,'input');
 checks[0].checked=true;checks[0].listeners.change();
 checks=all(root,'input');checks[1].checked=true;checks[1].listeners.change();
 checks=all(root,'input');checks[2].checked=true;checks[2].listeners.change();
 checks=all(root,'input');assert.equal(checks[3].disabled,true);
 assert.match(root.textContent,/Сравнение · 3/);
 api.loadDataset(data,{mode:'live'});
 assert.match(root.textContent,/Вымышленные/);
});

test('banner only changes after an authenticated adapter resolves valid data',async()=>{
 const root=new Element('main');const api=view.createViewer(root,doc);api.loadDataset(data);
 await assert.rejects(api.loadAuthenticated(async()=>{throw new Error('Denied');}));
 assert.match(root.textContent,/Вымышленные/);
 await api.loadAuthenticated(async()=>({dataset:data,authenticated:true}));
 assert.doesNotMatch(root.textContent,/Вымышленные/);
 assert.match(root.textContent,/Личные данные/);
});
