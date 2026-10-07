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

import {NeighborhoodScreen, westToEast, introParagraphs, sourcePageLink, sourceStamp} from '../studio/web/neighborhoods.js';

const hood=(name,longitude,extra={})=>({external_id:`${name}-id`,name,longitude,latitude:30.3,canonical_region_id:name.toLowerCase(),canonical_region_name:name,tags:[],summary:null,page_intro:null,page_url:'https://www.visitsouthwalton.com/neighborhoods/x/',source_modified:null,...extra});
test('neighborhood jobs and tabs route to the fourth domain',()=>{
  assert.deepEqual(jobResultTarget({kind:'source_collection',result:{connector_name:'south-walton-neighborhoods'}}),{href:'#collect/neighborhoods',label:'Mahalle verilerini aç'});
  const tabs=collectionTabs('neighborhoods');
  assert.match(tabs,/href="#collect\/neighborhoods" aria-current="page">Mahalleler</);
  assert.equal((tabs.match(/aria-current="page"/g)||[]).length,1);
  assert.equal((tabs.match(/class="tab/g)||[]).length,4);
});
test('neighborhoods list west to east by representative point',()=>{
  const ordered=westToEast([hood('Inlet Beach',-86.0),hood('Dune Allen',-86.25),hood('Seaside',-86.13),hood('Alpha',-86.13)]);
  assert.deepEqual(ordered.map(r=>r.name),['Dune Allen','Alpha','Seaside','Inlet Beach']);
});
test('intro paragraphs escape source text and keep a missing intro visible',()=>{
  assert.equal(introParagraphs('First <b>.\n\nSecond.'),'<details class="neighborhood-intro"><summary>Sayfadaki tanıtım metni · 2 paragraf</summary><p>First &lt;b&gt;.</p><p>Second.</p></details>');
  assert.equal(sourceStamp('2025-05-09T16:26:46+0000'),'2025-05-09 16:26:46 UTC');
  assert.equal(sourceStamp('2025-05-09T16:26:46-0500'),'2025-05-09 16:26:46-0500');
  assert.equal(sourceStamp(null),'Belirtilmemiş');assert.equal(sourceStamp('<x>'),'&lt;x&gt;');
  for(const missing of [null,'','  \n\n ']) assert.match(introParagraphs(missing),/tanıtım metni bulunamadı/);
  assert.match(sourcePageLink('https://www.visitsouthwalton.com/neighborhoods/seaside/'),/target="_blank" rel="noopener noreferrer"/);
  for(const url of [null,'http://www.visitsouthwalton.com/','javascript:alert(1)','bad']) assert.equal(sourcePageLink(url),'');
});
test('neighborhood detail shows source fields, null placeholders and the representative-point note',()=>{
  const elements=Object.fromEntries(['#neighborhood-count','#neighborhood-rows','#neighborhood-detail'].map(id=>[id,{innerHTML:'',textContent:''}]));
  const screen=new NeighborhoodScreen();
  screen.snapshot={records:[hood('Seaside',-86.13,{tags:['Walkable','<Tag>'],summary:'Short <line>',page_intro:'One.\n\nTwo.'}),hood('Dune Allen',-86.25)],run:{fetched_at:'2026-10-07T12:00:00Z'}};
  screen.rows({querySelector:id=>elements[id]});
  assert.equal(elements['#neighborhood-count'].textContent,'2 kayıt');
  assert.ok(elements['#neighborhood-rows'].innerHTML.indexOf('Dune Allen')<elements['#neighborhood-rows'].innerHTML.indexOf('Seaside'));
  let html=elements['#neighborhood-detail'].innerHTML;
  assert.match(html,/Dune Allen/);assert.match(html,/<p>Belirtilmemiş<\/p>/);assert.match(html,/Etiket listelenmemiş/);
  assert.match(html,/tanıtım metni bulunamadı/);assert.match(html,/mahalle merkezi değildir/);
  assert.doesNotMatch(html,/null|undefined/);
  screen.selectedRecord='Seaside-id';screen.rows({querySelector:id=>elements[id]});
  html=elements['#neighborhood-detail'].innerHTML;
  assert.match(html,/Short &lt;line&gt;/);assert.match(html,/&lt;Tag&gt;/);assert.match(html,/<p>One\.<\/p><p>Two\.<\/p>/);
  assert.ok(!html.includes('<Tag>'));
});
test('bound neighborhood source enables collection and a running job disables it',()=>{
  const source={id:'hoods',destination_id:'30a',name:'South Walton · Mahalleler',url:'https://www.visitsouthwalton.com/neighborhoods/',enabled:1,connector:{name:'south-walton-neighborhoods',method:'HTML'}};
  const main={innerHTML:''};
  new NeighborhoodScreen().render(main,{selected_destination:{id:'30a',name:'30A'},neighborhood_runs:[],sources:[source],jobs:[],canonical_regions:[{}],neighborhood_connector:{scope:'Scope.'}},(title,description,actions)=>actions);
  assert.match(main.innerHTML,/<button[^>]*data-action="collect-neighborhoods"[^>]*>↓ Mahalle verilerini topla<\/button>/);
  assert.doesNotMatch(main.innerHTML.match(/<button[^>]*data-action="collect-neighborhoods"[^>]*>/)[0],/disabled/);
  assert.match(main.innerHTML,/İlk mahalle çekimi hazır/);assert.match(main.innerHTML,/videoda aynen kullanılmaz/);
  const busy={innerHTML:''};
  new NeighborhoodScreen().render(busy,{selected_destination:{id:'30a',name:'30A'},neighborhood_runs:[],sources:[source],jobs:[{id:'j',destination_id:'30a',source_id:'hoods',status:'running'}]},(title,description,actions)=>actions);
  assert.match(busy.innerHTML,/disabled>Toplama sürüyor…/);
});
test('neighborhood screen never shows another destination runs',()=>{
  const data={selected_destination:{id:'other',name:'Other'},sources:[{id:'source',destination_id:'30a',enabled:1,connector:{name:'south-walton-neighborhoods'}}],jobs:[],neighborhood_runs:[{id:'old-run',destination_id:'30a'}]};
  const main={innerHTML:''};new NeighborhoodScreen().render(main,data,(_title,description)=>description);
  assert.match(main.innerHTML,/Bu destinasyon için mahalle kaynağı bağlı değil/);
  assert.ok(!main.innerHTML.includes('old-run'));
  const screen=new NeighborhoodScreen();screen.selectedRun='old';screen.selectedRecord='old';screen.snapshot={records:['old']};screen.sequence=4;
  resetDestinationState({},[screen]);
  assert.equal(screen.selectedRun,null);assert.equal(screen.snapshot,null);assert.equal(screen.sequence,5);
});

import {UNMAPPED, SOURCED_METHODS, beachMapping, beachNeighborhood, mappingCell, mappingDetail, mappingNote, filterBeaches} from '../studio/web/collection.js';

const layer={available:true,rows:[
  {external_id:'official',region_id:'seagrove',region_name:'Seagrove',method:'resmi_rehber',method_label:'resmî rehber',source:'https://www.visitsouthwalton.com/blog/guide-beach-parking-transportation/ (yayın 2023-05-04)',note:'başlık: Seagrove',ambiguous:false},
  {external_id:'derived',region_id:'seaside',region_name:'<Seaside>',method:'turetim_en_yakin_mahalle_noktasi',method_label:'program türetimi',source:'4473ae75f66b40d49c75f5fa2444c6db',note:'En yakın temsilî nokta',ambiguous:true}]};
const access=(external_id,extra={})=>({external_id,name:`${external_id} access`,address:'1 Test Rd',city:'Santa Rosa Beach',access_type:'neighborhood',features:[],latitude:30.3,longitude:-86.1,...extra});
test('beach mapping labels official, derived, ambiguous and unmapped accesses',()=>{
  const mapping=beachMapping(layer);
  assert.equal(beachMapping({available:false,rows:layer.rows}).size,0);assert.equal(beachMapping(undefined).size,0);
  assert.deepEqual(beachNeighborhood(access('unknown'),mapping),{regionId:UNMAPPED,label:'eşlenmemiş',method:null,ambiguous:false,row:null});
  const official=mappingCell(beachNeighborhood(access('official'),mapping));
  assert.match(official,/Seagrove/);assert.match(official,/tag green">resmî rehber/);assert.doesNotMatch(official,/belirsiz/);
  const derived=mappingCell(beachNeighborhood(access('derived'),mapping));
  assert.match(derived,/&lt;Seaside&gt;/);assert.match(derived,/program türetimi/);assert.match(derived,/belirsiz/);
  assert.match(mappingCell(beachNeighborhood(access('unknown'),mapping)),/eşlenmemiş/);
});
test('beach mapping detail links only the official guide and keeps derived provenance as a run id',()=>{
  const mapping=beachMapping(layer);
  const official=mappingDetail(beachNeighborhood(access('official'),mapping));
  assert.match(official,/href="https:\/\/www\.visitsouthwalton\.com\/blog\/guide-beach-parking-transportation\/" target="_blank" rel="noopener noreferrer"/);
  const derived=mappingDetail(beachNeighborhood(access('derived'),mapping));
  assert.match(derived,/Mahalle çekimi 4473ae75f66b40d49c75f5fa2444c6db/);assert.doesNotMatch(derived,/<a /);assert.match(derived,/<dd>evet<\/dd>/);
  assert.match(mappingDetail(beachNeighborhood(access('unknown'),mapping)),/eşlenmemiş/);
  assert.match(mappingNote(layer),/yalnız yaklaşık konumdur/);
  assert.equal(mappingNote({available:false,reason:'<broken>'}),'&lt;broken&gt;');
});
test('beach neighborhood filter combines with existing filters and selects unmapped accesses',()=>{
  const mapping=beachMapping(layer);
  const records=[access('official'),access('derived',{features:['parking']}),access('unknown')];
  assert.deepEqual(filterBeaches(records,{neighborhood:'seaside'},mapping).map(r=>r.external_id),['derived']);
  assert.deepEqual(filterBeaches(records,{neighborhood:UNMAPPED},mapping).map(r=>r.external_id),['unknown']);
  assert.deepEqual(filterBeaches(records,{neighborhood:'seaside',feature:'toilets'},mapping),[]);
  assert.equal(filterBeaches(records,{},mapping).length,3);
  assert.deepEqual(filterBeaches(records,{search:' official '},mapping).map(r=>r.external_id),['official']);
});
test('beach rows show the mapping column and an unmapped access stays visible',()=>{
  const elements=Object.fromEntries(['#beach-count','#beach-rows','#beach-detail'].map(id=>[id,{innerHTML:'',textContent:''}]));
  const screen=new BeachScreen();
  screen.data={beach_connector:{feature_labels:{}}};screen.mapping=beachMapping(layer);
  screen.snapshot={records:[access('official'),access('unknown')],run:{fetched_at:'2026-10-07T12:00:00Z',source_url:'https://www.visitsouthwalton.com/beach-bay-access-locations/'}};
  screen.rows({querySelector:id=>elements[id]});
  const rows=elements['#beach-rows'].innerHTML;
  assert.match(rows,/class="mapping-cell">Seagrove/);assert.match(rows,/eşlenmemiş/);
  assert.match(elements['#beach-detail'].innerHTML,/Mahalle eşlemesi/);
  screen.neighborhood=UNMAPPED;screen.rows({querySelector:id=>elements[id]});
  assert.equal(elements['#beach-count'].textContent,'1 / 2 kayıt');
  assert.match(elements['#beach-detail'].innerHTML,/Bu erişim eşleme dosyasında yok/);
});
test('county subdivision mappings are labelled, linked to the layer and shown as sourced',()=>{
  const county={external_id:'county',region_id:'seagrove',region_name:'Seagrove',method:'ilce_alt_bolum',method_label:'ilçe alt bölüm verisi',
    source:'https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/ArcGIS/rest/services/EnerGov_Additional/FeatureServer/13 (sorgu 2026-10-07)',note:"Walton County Subdivision Boundaries: 'SEAGROVE HORIZONS'",ambiguous:false};
  const mapping=beachMapping({available:true,rows:[...layer.rows,county]});
  assert.deepEqual(SOURCED_METHODS,['resmi_rehber','ilce_alt_bolum','ilce_alt_bolum_yakin']);
  const cell=mappingCell(beachNeighborhood(access('county'),mapping));
  assert.match(cell,/Seagrove/);assert.match(cell,/tag green">ilçe alt bölüm verisi/);
  assert.match(mappingCell(beachNeighborhood(access('derived'),mapping)),/class="tag ">program türetimi/);
  const detail=mappingDetail(beachNeighborhood(access('county'),mapping));
  assert.match(detail,/href="https:\/\/services1\.arcgis\.com\/TaXHPwWfIMuzJ7Ov\/ArcGIS\/rest\/services\/EnerGov_Additional\/FeatureServer\/13" target="_blank" rel="noopener noreferrer"/);
  assert.match(detail,/&#39;SEAGROVE HORIZONS&#39;/);
  assert.match(mappingNote(layer),/Walton County subdivision verisine göre/);
  assert.deepEqual(filterBeaches([access('county'),access('derived')],{neighborhood:'seagrove'},mapping).map(r=>r.external_id),['county']);
});
test('v3 labels: adjacent county mappings are sourced, neighbour consistency is approximate',()=>{
  const adjacent={external_id:'adj',region_id:'seagrove',region_name:'Seagrove',method:'ilce_alt_bolum_yakin',method_label:'ilçe alt bölüm verisi (bitişik)',
    source:'https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/ArcGIS/rest/services/EnerGov_Additional/FeatureServer/13 (sorgu 2026-10-07)',note:'poligonuna 18.6 m',ambiguous:false};
  const neighbours={external_id:'nb',region_id:'seagrove',region_name:'Seagrove',method:'komsu_tutarliligi',method_label:'komşu erişimlerle tutarlı',
    source:'komşu erişimler aaaaaaaaaaaaaaaaaaaaaaaa ve bbbbbbbbbbbbbbbbbbbbbbbb',note:'Batıdaki en yakın kaynaklı erişim',ambiguous:false};
  const mapping=beachMapping({available:true,rows:[adjacent,neighbours]});
  assert.match(mappingCell(beachNeighborhood(access('adj'),mapping)),/tag green">ilçe alt bölüm verisi \(bitişik\)/);
  assert.match(mappingCell(beachNeighborhood(access('nb'),mapping)),/class="tag ">komşu erişimlerle tutarlı/);
  const detail=mappingDetail(beachNeighborhood(access('nb'),mapping));
  assert.match(detail,/<p>komşu erişimler aaaaaaaaaaaaaaaaaaaaaaaa ve bbbbbbbbbbbbbbbbbbbbbbbb<\/p>/);
  assert.doesNotMatch(detail,/Mahalle çekimi/);
  assert.match(mappingNote({available:true,rows:[]}),/“komşu erişimlerle tutarlı” ve “program türetimi” yalnız yaklaşık konumdur/);
});
