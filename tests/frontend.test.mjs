import test from 'node:test';
import assert from 'node:assert/strict';
import {connectorState, jobResultTarget, collectionTabs} from '../studio/web/connectors.js';
import {weatherDate, WeatherScreen} from '../studio/web/weather.js';

test('registry method overrides editable planning method',()=>{
  assert.equal(connectorState({enabled:1,method:'Belirlenecek',connector:{name:'nws-weather',method:'API'}}).method,'API · bağlı');
  assert.equal(connectorState({enabled:1,connector:{name:'future-domain',method:'API'}}).label,'Toplayıcı hazır');
  assert.equal(connectorState({enabled:1,connector:null}).label,'Bağlantı bekliyor');
});
test('weather and beaches target distinct collection tabs',()=>{
  assert.deepEqual(jobResultTarget({kind:'source_collection',result:{connector_name:'nws-weather'}}),{href:'#collect/weather',label:'Hava verilerini aç'});
  assert.deepEqual(jobResultTarget({kind:'source_collection',result:{connector_name:'south-walton-beaches'}}),{href:'#collect',label:'Plaj verilerini aç'});
  assert.equal(jobResultTarget({kind:'source_collection',result:{connector_name:'unknown'}}),null);
  assert.equal(jobResultTarget({kind:'source_collection',result:null}),null);
  assert.equal(jobResultTarget({kind:'source_collection',result:{connector_name:'toString'}}),null);
  assert.match(collectionTabs(true),/href="#collect\/weather" aria-current="page"/);
});
test('weather dates use supplied NWS zone, never browser default',()=>{
  const time='2026-09-30T15:00:00Z';
  assert.match(weatherDate(time,'America/Chicago'),/10:00/);
  assert.match(weatherDate(time,'Europe/Istanbul'),/18:00/);
  assert.equal(weatherDate(time,null),time);
  assert.match(weatherDate(time,'not-a-zone'),/kaynak zamanı/);
});
test('table preserves zero versus null and escapes external text',()=>{
  const table=new WeatherScreen().table([{start_time:'2026-09-30T15:00:00Z',end_time:'2026-09-30T16:00:00Z',temperature:0,temperature_unit:'F',precipitation_probability:0,short_forecast:'<script>bad</script>',wind_speed:null}], 'America/Chicago', false);
  assert.match(table,/0 °F/);assert.match(table,/0%/);assert.match(table,/Belirtilmemiş/);
  assert.ok(!table.includes('<script>'));assert.match(table,/&lt;script&gt;/);
});
import {filterRestaurants, restaurantAddress, restaurantLink} from '../studio/web/restaurants.js';

const restaurant={name:'Coast & Table',description:'Fresh seafood by the shore',address_line_1:'10 Coast Lane',address_line_2:'Suite 2',city:'Santa Rosa Beach',state:'FL',postal_code:'32459',source_neighborhoods:['Dune Allen','Gulf Place'],cuisines:['Seafood','American'],meals_served:['Lunch','Dinner']};
test('restaurant jobs and tabs route to the third domain',()=>{
  assert.deepEqual(jobResultTarget({kind:'source_collection',result:{connector_name:'south-walton-restaurants'}}),{href:'#collect/restaurants',label:'Restoran verilerini aç'});
  assert.match(collectionTabs('restaurants'),/href="#collect\/restaurants" aria-current="page"/);
  assert.equal((collectionTabs('restaurants').match(/aria-current="page"/g)||[]).length,1);
  assert.equal(connectorState({enabled:1,method:'Belirlenecek',connector:{name:'south-walton-restaurants',method:'HTML'}}).method,'HTML · bağlı');
});
test('restaurant search includes name, all address fields and description',()=>{
  for(const query of ['TABLE',' coast lane ','suite 2','32459','fresh SEAFOOD']) assert.equal(filterRestaurants([restaurant],{search:query}).length,1);
  assert.equal(filterRestaurants([restaurant],{search:'unmatched'}).length,0);
  assert.equal(restaurantAddress({...restaurant,address_line_2:null}),'10 Coast Lane, Santa Rosa Beach, FL, 32459');
});
test('restaurant neighborhood, cuisine and meal filters combine without losing multi-region records',()=>{
  assert.equal(filterRestaurants([restaurant],{neighborhood:'Gulf Place',cuisine:'Seafood',meal:'Lunch'}).length,1);
  for(const filters of [{neighborhood:'Seaside'},{cuisine:'Thai'},{meal:'Breakfast'}]) assert.equal(filterRestaurants([restaurant],filters).length,0);
  assert.equal(filterRestaurants([{...restaurant,description:null,address_line_1:null,cuisines:[],meals_served:[]}]).length,1);
});
test('restaurant external links escape text, isolate tabs and reject unsafe schemes',()=>{
  const link=restaurantLink('https://restaurant.example/?q="','<unsafe>');
  assert.match(link,/target="_blank" rel="noopener noreferrer"/);
  assert.match(link,/&lt;unsafe&gt;/);assert.match(link,/&quot;/);
  for(const url of [null,'javascript:alert(1)','data:text/html,bad','bad']) assert.equal(restaurantLink(url,'test'),'Belirtilmemiş');
});
