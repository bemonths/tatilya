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

import {RestaurantScreen} from '../studio/web/restaurants.js';

test('restaurant detail renders missing description and keeps null-safe search',()=>{
  const record={...restaurant,description:null,external_id:'/listing/coast-table/',listing_url:'https://www.visitsouthwalton.com/listing/coast-table/',regions:[],amenities:[]};
  const elements=Object.fromEntries(['#restaurant-count','#restaurant-rows','#restaurant-detail'].map(id=>[id,{innerHTML:'',textContent:''}]));
  const screen=new RestaurantScreen();
  screen.snapshot={records:[record],run:{fetched_at:'2026-09-30T12:00:00Z'}};
  screen.rows({querySelector:id=>elements[id]});
  const html=elements['#restaurant-detail'].innerHTML;
  assert.match(html,/<p>Belirtilmemiş<\/p>/);
  assert.doesNotMatch(html,/<p>(?:null|None|undefined)?<\/p>/);
  assert.equal(filterRestaurants([record],{search:'coast',neighborhood:'Gulf Place'}).length,1);
  assert.equal(filterRestaurants([record],{search:'null'}).length,0);
  assert.equal(filterRestaurants([record],{search:'fresh seafood'}).length,0);
});

test('bound existing restaurant source enables collection regardless of display name or URL spelling',()=>{
  const source={id:'legacy-food',name:'My source',url:'https://visitsouthwalton.com/listings/culinary-experiences',enabled:1,method:'HTML',connector:{name:'south-walton-restaurants',version:'south-walton-restaurants/1',method:'HTML'}};
  assert.equal(connectorState(source).method,'HTML · bağlı');
  assert.equal(connectorState(source).label,'Toplayıcı hazır');
  const main={innerHTML:''};
  new RestaurantScreen().render(main,{restaurant_runs:[],sources:[source],jobs:[]},(title,description,actions)=>actions);
  assert.match(main.innerHTML,/HTML · bağlı/);
  assert.doesNotMatch(main.innerHTML,/Kaynak etkin değil/);
  assert.match(main.innerHTML,/<button[^>]*data-action="collect-restaurants"[^>]*>↓ Restoran verilerini topla<\/button>/);
  assert.doesNotMatch(main.innerHTML.match(/<button[^>]*data-action="collect-restaurants"[^>]*>/)[0],/disabled/);
});

import {destinationOptions, storedDestination, persistDestination, resetDestinationState, destinationRows} from '../studio/web/destinations.js';
import {api, setDestination, destinationPath, StaleDestinationResponse} from '../studio/web/api.js';
import {BeachScreen} from '../studio/web/collection.js';

test('destination dropdown renders stable IDs and escapes names',()=>{
  const html=destinationOptions([{id:'a',name:'<Coast>',subtitle:'North'},{id:'b',name:'Bay'}],'b');
  assert.match(html,/value="b" selected/);assert.match(html,/&lt;Coast&gt;/);
});
test('destination selection persists per client storage',()=>{
  const store=new Map(),storage={getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v)};
  assert.equal(storedDestination(storage),null);persistDestination(storage,'test-coast');
  assert.equal(storedDestination(storage),'test-coast');
  assert.equal(storedDestination({getItem:()=>null}),null);
});
test('selected destination is used for bootstrap lists and source creation',async()=>{
  const original=globalThis.fetch,calls=[];
  globalThis.fetch=async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>[]};};
  try {
    setDestination('test-coast');
    for(const path of ['bootstrap','sources','jobs','collections','weather-runs','restaurant-runs']) await api(path);
    await api('sources',{method:'POST',body:JSON.stringify({name:'Test'})});
    assert.ok(calls.every(([url])=>url.includes('destination_id=test-coast')));
    assert.equal(JSON.parse(calls.at(-1)[1].body).destination_id,'test-coast');
    assert.equal(destinationPath('events'), 'events?destination_id=test-coast');
  } finally {globalThis.fetch=original;setDestination(null);}
});
test('stale async responses cannot overwrite another destination',async()=>{
  const original=globalThis.fetch;let resolve;
  globalThis.fetch=()=>new Promise(r=>{resolve=r;});
  try {
    setDestination('a');const pending=api('bootstrap');setDestination('b');
    resolve({ok:true,json:async()=>({selected_destination:{id:'a'}})});
    await assert.rejects(pending,StaleDestinationResponse);
  } finally {globalThis.fetch=original;setDestination(null);}
});
test('switching resets screen selections filters snapshots without resetting request generations',()=>{
  const screens=[new BeachScreen(),new WeatherScreen(),new RestaurantScreen()];
  for(const s of screens){s.selectedRun='old';s.selectedRecord='old';s.sequence=8;s.snapshot={records:['old']};}
  const state={page:'collect',data:{},selected:'old',search:'old'};
  resetDestinationState(state,screens);
  assert.equal(state.data,null);assert.equal(state.page,'collect');assert.equal(state.search,'');
  for(const s of screens){assert.equal(s.selectedRun,null);assert.equal(s.sequence,9);}
  assert.equal(screens[0].snapshot,null);assert.equal(screens[2].snapshot,null);
});
test('source and job rows are destination filtered',()=>{
  const rows=[{id:'1',destination_id:'a'},{id:'2',destination_id:'b'}];
  assert.deepEqual(destinationRows(rows,{id:'b'}),[rows[1]]);
});
for(const [Screen,field,label,connector] of [[BeachScreen,'collections','plaj','beach_connector'],[WeatherScreen,'weather_runs','hava','weather_connector'],[RestaurantScreen,'restaurant_runs','restoran','restaurant_connector']]) {
  test(`${field} same-route destination switch renders empty state and never wrong destination records`,()=>{
    const data={selected_destination:{id:'other',name:'Other'},sources:[{id:'source',destination_id:'30a',enabled:1,connector:{name:'test'}}],jobs:[],[field]:[{id:'old-run',destination_id:'30a'}],[connector]:{name:'test'}};
    const main={innerHTML:''};new Screen().render(main,data,(_title,description)=>description);
    assert.match(main.innerHTML,new RegExp(`Bu destinasyon için ${label} kaynağı bağlı değil`));
    assert.ok(!main.innerHTML.includes('old-run'));
  });
}
