import test from 'node:test';
import assert from 'node:assert/strict';
import * as model from '../model.js';

test('joins by batch, filters device and sorts missing ratings last without mutation', () => {
  const data = {schema_version:1,coffees:[{id:'c'}],batches:[{id:'b',coffee_id:'c'}],equipment:[],recipes:[],brews:[
    {id:'a',batch_id:'b',brewer_id:'v',rating:null,brewed_at:'2026-02-01T10:00:00Z'},
    {id:'b',batch_id:'b',brewer_id:'v',rating:0,brewed_at:null},
    {id:'c',batch_id:'b',brewer_id:'p',rating:90,brewed_at:'2026-01-01T10:00:00Z'}]};
  assert.deepEqual(model.selectBrews(data,{coffeeId:'c',sort:'rating'}).map(x=>x.id), ['c','b','a']);
  assert.deepEqual(model.selectBrews(data,{coffeeId:'c',deviceId:'v',sort:'recent'}).map(x=>x.id), ['a','b']);
  assert.deepEqual(data.brews.map(x=>x.id), ['a','b','c']);
  assert.throws(()=>model.validateDataset({schema_version:2}), /schema/);
});

test('compact brew line preserves zero and distinguishes missing values', () => {
  assert.equal(model.brewLine({temperature_c:0,grind_setting:'0',coffee_g:0,water_g:0,duration_s:0,rating:0}, 'Тест'), 'Тест / 0 °C / 0 / 0 г / 0 г / — / 0:00 / 0');
  assert.equal(model.ratio({coffee_g:20,water_g:300}), '1:15');
  assert.equal(model.ratio({coffee_g:null,water_g:300}), '—');
});
