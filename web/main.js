import {createViewer} from './app.js';
// All records here are fictional. Real personal records must never enter this file.
const id=n=>`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`;
const dataset={schema_version:1,
 coffees:[{id:id(1),name:'Демо · Эфиопия',roaster:'Вымышленный обжарщик',origin:'Эфиопия',process:'Натуральная',labeled_notes:'Цветы, ягоды'},{id:id(2),name:'Демо · Колумбия',origin:'Колумбия',process:'Мытая'}],
 batches:[{id:id(3),coffee_id:id(1),roast_date:'2026-09-20'},{id:id(4),coffee_id:id(2),roast_date:null}],
 equipment:[{id:id(5),name:'V60',kind:'brewer'},{id:id(6),name:'Аэропресс',kind:'brewer'},{id:id(7),name:'Демо-кофемолка',kind:'grinder'}],
 recipes:[{id:id(8),name:'Демо · три вливания',brewer_id:id(5),steps:[{name:'Предсмачивание',instruction:'Равномерно смочить',duration_s:30,water_g:45},{name:'Основное вливание',instruction:'Долить до общего веса',duration_s:120,water_g:180}]}],
 brews:[
 {id:id(10),batch_id:id(3),brewer_id:id(5),grinder_id:id(7),recipe_id:id(8),brewed_at:'2026-10-01T08:00:00+04:00',temperature_c:92,grind_setting:'8.5',coffee_g:15,water_g:225,duration_s:150,rating:80,taste_notes:'Демо: ягоды, приятная кислотность.',recipe_notes:'Три вливания.'},
 {id:id(11),batch_id:id(3),brewer_id:id(5),grinder_id:id(7),brewed_at:'2026-10-02T08:00:00+04:00',temperature_c:94,grind_setting:'7.5',coffee_g:15,water_g:240,duration_s:180,rating:74,taste_notes:'Демо: плотнее, суховатое послевкусие.'},
 {id:id(12),batch_id:id(3),brewer_id:id(6),grinder_id:id(7),brewed_at:'2026-10-03T08:00:00+04:00',temperature_c:90,grind_setting:'9',coffee_g:16,water_g:220,duration_s:120,rating:85,taste_notes:'Демо: сладкий, мягкий.'},
 {id:id(13),batch_id:id(4),brewer_id:id(5),temperature_c:93,coffee_g:15,water_g:250,duration_s:165,rating:82,taste_notes:'Демо: карамель.'},
 {id:id(14),batch_id:id(4),brewer_id:id(6),temperature_c:null,coffee_g:15,water_g:225,duration_s:null,rating:null,taste_notes:'Демо: оценка пока не выставлена.'}
 ]};
createViewer(document.getElementById('app')).loadDataset(dataset);
