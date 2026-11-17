import test from 'node:test';
import {readFileSync} from 'node:fs';
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
  const source={id:'legacy-food',name:'My source',url:'https://visitsouthwalton.com/listings/culinary-experiences',enabled:1,method:'HTML',connector:{name:'south-walton-restaurants',version:'south-walton-restaurants/2',method:'HTML'}};
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
  assert.equal((tabs.match(/class="tab/g)||[]).length,7);
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

import {ClimateScreen, CLIMATE_CONNECTORS, number, fToC, inToMm, normalCell, waterCell, flagSummary, stormMonthlyCounts, closestStorms} from '../studio/web/climate.js';

const climateSource=(key,extra={})=>({id:`src-${key}`,destination_id:'30a',name:`Source ${key}`,enabled:1,connector:{name:CLIMATE_CONNECTORS[key],method:key==='normals'?'API':'Dosya'},...extra});
const passage=(storm_id,name,season,radius_nmi,first_entry_month,storm_class,closest_km,extra={})=>({storm_id,name,season,radius_nmi,first_entry_month,storm_class,closest_km,closest_nmi:closest_km/1.852,first_entry_time:`${season}-0${Math.min(first_entry_month,9)}-01T00:00Z`,max_wind_kt:storm_class?70:null,status_at_max:'HU',...extra});
test('climate jobs and tabs route to the fifth domain',()=>{
  for(const name of Object.values(CLIMATE_CONNECTORS)) assert.deepEqual(jobResultTarget({kind:'source_collection',result:{connector_name:name}}),{href:'#collect/climate',label:'İklim verilerini aç'});
  const tabs=collectionTabs('climate');
  assert.match(tabs,/href="#collect\/climate" aria-current="page">İklim</);
  assert.equal((tabs.match(/aria-current="page"/g)||[]).length,1);
});
test('climate cells keep source units, add our metric conversion and never turn missing into zero',()=>{
  assert.equal(number(90),'90,0');assert.equal(number(null),null);assert.equal(number(4.524,2),'4,52');
  assert.equal(fToC(212),100);assert.equal(inToMm(1),25.4);
  assert.equal(normalCell({value:90,unit:'°F'}),'90,0 °F<small>32,2 °C</small>');
  assert.equal(normalCell({value:4.52,unit:'inç'}),'4,52 inç<small>115 mm</small>');
  assert.equal(normalCell({value:0,unit:'gün'}),'0,0 gün');
  for(const missing of [null,undefined,{value:null,unit:'°F'}]) assert.match(normalCell(missing),/Kaynakta yok/);
  assert.equal(waterCell({mean_c:21.3}),'21,3 °C<small>70,3 °F</small>');
  assert.match(waterCell({mean_c:null}),/20 günlük veri yok/);
});
test('flag summary lists published flags, measurement flags by month, year counts and missing months',()=>{
  const values=[{station_id:'A',element:'MLY-TMAX-NORMAL',month:1,value:60,completeness_flag:'R',measurement_flag:null,years:19},
    {station_id:'A',element:'MLY-TMAX-NORMAL',month:11,value:70,completeness_flag:'S',measurement_flag:'<X>',years:22},
    {station_id:'A',element:'MLY-PRCP-NORMAL',month:2,value:null,completeness_flag:null,measurement_flag:null,years:null},
    {station_id:'B',element:'MLY-TMAX-NORMAL',month:1,value:60,completeness_flag:'P',measurement_flag:null,years:10}];
  const lines=flagSummary(values,'A');
  assert.equal(lines[0],'Ort. en yüksek: tamlık R/S · ölçüm bayrağı &lt;X&gt; (Kasım) · 19–22 yıl');
  assert.equal(lines[3],'Yağış: tamlık yok · 1 ay kaynakta yok');
  assert.ok(!lines.join('').includes(' P'));
});
test('storm monthly counts filter radius and seasons, count each passage once and keep unknown wind separate',()=>{
  const passages=[passage('AL1','A',1990,50,8,'HU',20),passage('AL2','B',1995,50,8,'MH',10),passage('AL2','B',1995,100,7,'MH',10),
    passage('AL3','C',2005,50,9,null,40),passage('AL4','D',2020,50,9,'TS',5),passage('AL5','E',2026,50,6,'TD',1)];
  const table=stormMonthlyCounts(passages,50,1991,2025);
  assert.deepEqual(table[7],{TD:0,TS:0,HU:0,MH:1,bilinmiyor:0});
  assert.deepEqual(table[8],{TD:0,TS:1,HU:0,MH:0,bilinmiyor:1});
  assert.equal(table.flatMap(row=>Object.values(row)).reduce((a,b)=>a+b,0),3);
  assert.deepEqual(stormMonthlyCounts(passages,100,null,null)[6],{TD:0,TS:0,HU:0,MH:1,bilinmiyor:0});
  assert.deepEqual(closestStorms(passages,50,1991,2025).map(p=>p.name),['D','B','C']);
  assert.deepEqual(closestStorms(passages,50,null,null,2).map(p=>p.name),['E','D']);
});
test('climate screen shows three collectors, disables a running one and never shows another destination runs',()=>{
  const sources=['normals','water','storms'].map(key=>climateSource(key));
  const main={innerHTML:''};
  new ClimateScreen().render(main,{selected_destination:{id:'30a',name:'30A'},climate_runs:[],sources,jobs:[{id:'j',destination_id:'30a',source_id:'src-water',status:'running'}]},(title,description,actions='')=>description+actions);
  assert.match(main.innerHTML,/<button class="primary" data-action="collect-climate-normals" >↓ İklim normallerini topla<\/button>/);
  assert.match(main.innerHTML,/data-action="collect-water-temperature" disabled>Toplama sürüyor…/);
  assert.match(main.innerHTML,/data-action="collect-storms" >↓ Kasırga izlerini topla/);
  assert.match(main.innerHTML,/İlk iklim çekimi hazır/);assert.match(main.innerHTML,/bizim hesabımız/);
  const other={innerHTML:''};
  new ClimateScreen().render(other,{selected_destination:{id:'other',name:'Other'},climate_runs:[{id:'old-run',destination_id:'30a',connector_name:'ncei-climate-normals'}],sources,jobs:[]},(_title,description)=>description);
  assert.match(other.innerHTML,/Bu destinasyon için iklim kaynağı bağlı değil/);
  assert.ok(!other.innerHTML.includes('old-run'));
  const screen=new ClimateScreen();screen.snapshot={};screen.compare='x';screen.radius=50;screen.sequence=3;
  resetDestinationState({},[screen]);
  assert.equal(screen.snapshot,null);assert.equal(screen.compare,'');assert.equal(screen.radius,null);assert.equal(screen.sequence,4);
});
test('climate tables label sources and our calculations, compare stations and filter storms',()=>{
  const months=Array.from({length:12},(_,i)=>i+1);
  const values=['C','I'].flatMap(id=>months.flatMap(month=>[
    {station_id:id,month,element:'MLY-TMAX-NORMAL',value:month===7?(id==='C'?90:92.3):70,unit:'°F',completeness_flag:'R',measurement_flag:null,years:19},
    {station_id:id,month,element:'MLY-PRCP-NORMAL',value:id==='C' && month===2?null:4,unit:'inç',completeness_flag:'R',measurement_flag:null,years:22}]));
  const summary=months.map(month=>({month,mean_c:month===5?24.6:null,years_used:month===5?17:0,first_year:month===5?2005:null,last_year:month===5?2025:null,excluded_year_months:0}));
  const snapshot={config:{stations:[{station_id:'C',kind:'normals',distance_basis:'Koridora uzaklık'},{station_id:'I',kind:'normals',distance_basis:'Koridora uzaklık'},{station_id:'W',kind:'water_temperature',distance_basis:'Koridora uzaklık'}]},
    normals:{stations:[{station_id:'C',label:'Coast <Airport>',role:'kıyı referansı',distance_km:20.5},{station_id:'I',label:'Inland',role:'iç kesim karşılaştırması',distance_km:44.1}],values},
    water:{stations:[{station_id:'W',label:'Buoy',distance_km:12.9,first_year:2005,last_year:2025,years_found:[2005],years_missing:[2006]}],summary:{W:summary},min_days:20},
    storms:{corridor:{radii_nmi:[50,100],first_season:1851,last_season:2025,hurdat_file:'hurdat2-1851-2025-092326.txt',storm_count:1988,west_reference:'West',east_reference:'East'},class_labels:{HU:'kasırga',MH:'büyük kasırga',TS:'tropikal fırtına',TD:'tropikal depresyon'},
      passages:[passage('AL142018','<Michael>',2018,50,10,'MH',56.4),passage('AL011980','OLD',1980,50,8,'HU',30),passage('AL012000','WIDE',2000,100,9,'TS',150)]}};
  const body={innerHTML:'',querySelector:()=>null};
  const screen=new ClimateScreen();screen.snapshot=snapshot;screen.radius=50;screen.from=1991;screen.to=2025;
  screen.draw({querySelector:()=>body});
  let html=body.innerHTML;
  assert.match(html,/Aylık tablo · Coast &lt;Airport&gt;/);assert.match(html,/90,0 °F<small>32,2 °C<\/small>/);
  assert.match(html,/Kaynakta yok/);assert.doesNotMatch(html,/class="climate-compare"/);
  assert.match(html,/24,6 °C<small>76,3 °F<\/small><\/td><td>17<small>2005–2025<\/small>/);
  assert.match(html,/kıyı referansı Coast &lt;Airport&gt; · C; Koridora uzaklık: 20,5 km/);
  assert.match(html,/°C ve mm dönüşümleri bizim hesabımız/);
  assert.match(html,/Buoy · W ölçümlerinden hesaplanan aylık ortalama; NOAA verisinden bizim hesabımız/);
  assert.match(html,/dosyası olmayan yıllar: 2006/);
  assert.match(html,/R temsilî \(en az 10 yıl; eksik aylar çevredeki istasyonlardan tahminle doldurulmuş\)/);
  assert.match(html,/X sıfır olmayan değer sıfıra yuvarlandı/);
  assert.match(html,/Kasırga geçmişi · 50 deniz mili · 1991–2025<\/h2><small>1 fırtına<\/small>/);
  assert.match(html,/&lt;Michael&gt;<\/strong> 2018/);assert.doesNotMatch(html,/OLD|WIDE|<Michael>/);
  assert.match(html,/büyük kasırga/);assert.match(html,/dosya hurdat2-1851-2025-092326\.txt/);assert.match(html,/NOAA verisinden bizim hesabımız: izler 1 saatlik/);
  screen.compare='I';screen.radius=100;screen.from=null;screen.to=null;screen.draw({querySelector:()=>body});
  html=body.innerHTML;
  assert.match(html,/<div class="climate-compare">Inland: 92,3 °F<small>33,5 °C<\/small><\/div>/);
  assert.match(html,/Karşılaştırma: iç kesim karşılaştırması Inland · I, 44,1 km/);
  assert.match(html,/Kasırga geçmişi · 100 deniz mili · 1851–2025/);assert.match(html,/WIDE/);
  assert.doesNotMatch(html,/null|undefined|NaN/);
});
test('storms inside a radius only in non-tropical stages are listed separately and never counted',()=>{
  const passages=[passage('AL1','TROP',2000,50,9,'HU',30),passage('AL2','<EXTRA>',2001,50,10,null,5,{non_tropical_only:1,status_at_max:'EX'}),
    passage('AL3','OLD',1950,50,8,null,4,{non_tropical_only:1,status_at_max:'LO'})];
  assert.equal(stormMonthlyCounts(passages,50,1991,2025).flatMap(row=>Object.values(row)).reduce((a,b)=>a+b,0),1);
  assert.deepEqual(closestStorms(passages,50,null,null).map(p=>p.name),['TROP']);
  const storms={corridor:{radii_nmi:[50],first_season:1851,last_season:2025,hurdat_file:'f.txt',storm_count:3,west_reference:'W',east_reference:'E'},
    class_labels:{HU:'kasırga'},passages,run:{connector_version:'hurdat2-storm-proximity/2'}};
  const body={innerHTML:'',querySelector:()=>null};
  const screen=new ClimateScreen();screen.snapshot={config:{stations:[]},normals:null,water:null,storms};screen.radius=50;screen.from=1991;screen.to=2025;
  screen.draw({querySelector:()=>body});
  assert.match(body.innerHTML,/Sayılmayan: bu daireye yalnız tropikal olmayan bir evrede giren 1 fırtına \(&lt;EXTRA&gt; 2001, evre EX\)/);
  assert.doesNotMatch(body.innerHTML,/OLD 1950/);
  assert.match(body.innerHTML,/Yalnız fırtınanın tropikal veya subtropikal olduğu evreler sayılır \(HURDAT2 durum kodları TD, TS, HU, SD, SS\)/);
  storms.run.connector_version='hurdat2-storm-proximity/1';screen.draw({querySelector:()=>body});
  assert.match(body.innerHTML,/Bu çekim eski kuralla \(hurdat2-storm-proximity\/1\) yapıldı/);
});

import {ReferencesScreen, groupByTopic, statusCounts, filterReferences, referenceLink, referenceRow, VIDEO_RULE} from '../studio/web/references.js';

const ref=(id,konu,durum,extra={})=>({id,konu,durum,ifade:`Statement ${id}.`,deger:'5',birim:'USD',kapsam:'30A',kaynak_adi:'Source',kaynak_sahibi:'Owner',
  kaynak_url:'https://example.gov/doc',belge_konumu:'Sec. 1',kisa_alinti:'quoted words',belge_tarihi:'2025',erisim_tarihi:'2026-10-07',belge_sha256:'a'.repeat(64),
  guven:'birincil',celiski_notu:'',yeniden_kontrol_tarihi:'2027-10-07',not:'',overdue:false,...extra});
const TOPICS={'plaj-kurallari':'Plaj kuralları','guvenlik':'Güvenlik','parklar':'Parklar'};
const STATUSES={dogrulandi:'doğrulandı',celiskili:'çelişkili',dogrulanamadi:'doğrulanamadı',yerine_gecildi:'yerine geçildi'};
test('reference tab routes to the sixth collection tab',()=>{
  const tabs=collectionTabs('references');
  assert.match(tabs,/href="#collect\/references" aria-current="page">Referanslar</);
  assert.equal((tabs.match(/aria-current="page"/g)||[]).length,1);
});
test('references group by topic order, count statuses and overdue rows, and filter',()=>{
  const rows=[ref('b','guvenlik','celiskili',{overdue:true}),ref('a','plaj-kurallari','dogrulandi'),ref('c','parklar','dogrulanamadi',{ifade:'Grayton fee'}),ref('d','yeni-konu','dogrulandi'),ref('e','guvenlik','yerine_gecildi',{replaced_by:'a'})];
  assert.deepEqual(groupByTopic(rows,TOPICS).map(g=>[g.label,g.rows.map(r=>r.id)]),[['Plaj kuralları',['a']],['Güvenlik',['b','e']],['Parklar',['c']],['yeni-konu',['d']]]);
  assert.deepEqual(statusCounts(rows),{dogrulandi:2,celiskili:1,dogrulanamadi:1,yerine_gecildi:1,overdue:1});
  assert.deepEqual(filterReferences(rows,{status:'yerine_gecildi'}).map(r=>r.id),['e']);
  assert.deepEqual(filterReferences(rows,{status:'overdue'}).map(r=>r.id),['b']);
  assert.deepEqual(filterReferences(rows,{status:'dogrulandi',search:''}).map(r=>r.id),['a','d']);
  assert.deepEqual(filterReferences(rows,{search:'GRAYTON'}).map(r=>r.id),['c']);
});
test('reference rows link only https sources, escape text and mark overdue rechecks',()=>{
  assert.match(referenceLink('https://example.gov/a','<Doc>'),/href="https:\/\/example.gov\/a" target="_blank" rel="noopener noreferrer">&lt;Doc&gt; ↗<\/a>/);
  for(const url of ['http://example.gov','javascript:alert(1)','','bad']) assert.equal(referenceLink(url,'<Doc>'),'&lt;Doc&gt;');
  const html=referenceRow(ref('x','guvenlik','celiskili',{ifade:'<b>bold</b>',celiski_notu:'Other page says 31 October.',overdue:true}),STATUSES);
  assert.match(html,/class="reference-overdue"/);assert.match(html,/tarihi geçti/);assert.match(html,/tag warm">çelişkili/);
  assert.match(html,/&lt;b&gt;bold&lt;\/b&gt;/);assert.match(html,/Çelişki:<\/strong> Other page says 31 October\./);
  assert.match(html,/doğrulama için, videoda kullanılmaz/);
  const blank=referenceRow(ref('y','parklar','dogrulanamadi',{deger:'',birim:'',belge_sha256:'',kisa_alinti:''}),STATUSES);
  assert.match(blank,/<span class="muted">—<\/span>/);assert.doesNotMatch(blank,/SHA-256|null|undefined/);
  const superseded=referenceRow(ref('z','guvenlik','yerine_gecildi',{replaced_by:'cankurtaran-2026'}),STATUSES);
  assert.match(superseded,/Yerine geçen satır:<\/strong> cankurtaran-2026/);assert.match(superseded,/tag ">yerine geçildi/);
  assert.doesNotMatch(referenceRow(ref('w','guvenlik','dogrulandi',{replaced_by:null}),STATUSES),/Yerine geçen/);
});
test('references screen shows counts, the video rule and an unavailable table',()=>{
  const body={innerHTML:'',querySelector(selector){return selector==='#reference-groups'?(this.groupsElement ??= {innerHTML:''}):null;}};
  const screen=new ReferencesScreen();
  screen.snapshot={available:true,file:'thirty_a_references.csv',today:'2026-10-07',topics:TOPICS,statuses:STATUSES,problems:[],
    rows:[ref('a','plaj-kurallari','dogrulandi'),ref('b','guvenlik','celiskili',{overdue:true})]};
  screen.draw({querySelector:()=>body});
  assert.match(body.innerHTML,/<strong>1<\/strong><span class="metric-label">doğrulandı/);
  assert.match(body.innerHTML,/<strong>1<\/strong><span class="metric-label">yeniden kontrol/);
  assert.match(body.innerHTML,/<strong>0<\/strong><span class="metric-label">yerine geçildi/);assert.match(VIDEO_RULE,/yerine geçildi/);
  assert.ok(body.innerHTML.includes(VIDEO_RULE.slice(0,40)));
  assert.match(body.groupsElement.innerHTML,/<h2>Plaj kuralları<\/h2><small>1 satır/);
  screen.snapshot={...screen.snapshot,problems:['2. satır: <bad>']};screen.draw({querySelector:()=>body});
  assert.match(body.innerHTML,/Tablo doğrulamadan geçmedi:<\/strong> 2\. satır: &lt;bad&gt;/);
  const empty={innerHTML:'',querySelector:()=>null};screen.snapshot={available:false,reason:'Bu destinasyon için referans tablosu yok.',rows:[]};
  screen.draw({querySelector:()=>empty});
  assert.match(empty.innerHTML,/Referans tablosu yok<\/h2><p>Bu destinasyon için referans tablosu yok\./);
});

import {LodgingScreen, summaryCell, usd, percent, listingCategories, priceTag, regionMonthly, monthLabel, sourceCounts, bedroomText, companyLink} from '../studio/web/lodging.js';
test('lodging jobs and the tab route to the lodging screen',()=>{
  assert.deepEqual(jobResultTarget({kind:'source_collection',result:{connector_name:'bookdirect-lodging'}}),{href:'#collect/lodging',label:'Konaklama verilerini aç'});
  assert.match(collectionTabs('lodging'),/href="#collect\/lodging" aria-current="page">Konaklama</);
});
test('lodging cells keep missing prices and skipped windows visible',()=>{
  assert.equal(usd(1234.4),'$1,234');assert.equal(usd(null),null);assert.equal(percent(0.05),'%5');assert.equal(percent(null),null);
  assert.match(summaryCell({status:'skipped_past'}),/Geçmiş tarih; aranmadı/);
  assert.match(summaryCell({status:'searched',listing_count:0}),/Aramada ilan görünmedi/);
  const cell=summaryCell({status:'searched',listing_count:60,priced_count:3,priced_share:0.05,price_q1:225,price_median:250,price_q3:280});
  assert.match(cell,/60 ilan/);assert.match(cell,/fiyatlı 3 \(%5\)/);assert.match(cell,/\$250<\/strong><small>gecelik ortanca · \$225–\$280/);
  assert.match(summaryCell({status:'searched',listing_count:3,priced_count:0,priced_share:0,price_median:null}),/Fiyat bilgisi yok/);
  assert.equal(sourceCounts({liste:1,canli:2}),'liste 1 · canlı 2 · takvim 0');
  assert.match(bedroomText({bedrooms_known:0}),/Kaynakta yok/);
  assert.match(bedroomText({bedrooms_known:2,listing_count:3,bedrooms_median:4.5,bedrooms_4_plus_share:0.5}),/ortanca 4,5 · 4\+ oda %50 <small>2\/3 ilanda/);
});
test('lodging listing helpers drop the default category and escape source text',()=>{
  assert.equal(listingCategories({category_ids:[103,849],category_names:['All Lodging','<b>Homes</b>']},103),'&lt;b&gt;Homes&lt;/b&gt;');
  assert.match(listingCategories({category_ids:[103],category_names:['All Lodging']},103),/Belirtilmemiş/);
  assert.match(priceTag(undefined),/Bu pencerede görünmedi/);assert.match(priceTag({price:null}),/Fiyat yok/);
  assert.match(priceTag({price:310,price_source:'canli',los:3}),/\$310<small>canlı · en az 3 gece/);
  assert.deepEqual(regionMonthly([{region_id:'a',month:'2027-07'},{region_id:'b',month:'2027-07'}],'a'),[{region_id:'a',month:'2027-07'}]);
  assert.equal(monthLabel('2027-07'),'Tem 2027');
});
test('lodging screen draws the region x window table with the scope label',()=>{
  const nodes={};const node=()=>({innerHTML:'',textContent:'',addEventListener(){}});
  const body={...node(),querySelector:selector=>nodes[selector] ??= node()};
  const main={querySelector:selector=>selector==='#lodging-body'?body:(nodes[selector] ??= node())};
  const screen=new LodgingScreen();
  screen.snapshot={run:{id:'r1'},snapshot:{listing_count:64,request_count:120,searched_on:'2026-10-07',default_category_id:103},
    windows:[{window_key:'fall',label:'Sonbahar 2026',checkin:'2026-10-17',checkout:'2026-10-24',nights:7,status:'searched'},
             {window_key:'old',label:'<Eski>',checkin:'2026-01-01',checkout:'2026-01-08',nights:7,status:'skipped_past'}],
    regions:[{region_id:'seaside',region_name:'Seaside',filters:['Seaside']}],
    cells:[{region_id:'seaside',window_key:'fall',status:'searched',listing_count:60,priced_count:0,priced_share:0,price_median:null},
           {region_id:'seaside',window_key:'old',status:'skipped_past',listing_count:0}],monthly:[],label:'2026-10-07 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir.'};
  screen.draw(main);
  assert.match(body.innerHTML,/<strong>64<\/strong><span class="metric-label">benzersiz ilan/);
  assert.match(body.innerHTML,/1 geçmiş pencere atlandı/);
  assert.match(body.innerHTML,/tam envanter değildir/);
  assert.match(body.innerHTML,/&lt;Eski&gt;<small>2026-01-01 → 2026-01-08 · 7 gece/);
  assert.match(body.innerHTML,/data-lodging-region="seaside">Seaside<\/button>/);
  assert.match(body.innerHTML,/60 ilan/);assert.match(body.innerHTML,/Geçmiş tarih; aranmadı/);
});
test('company listing links open only http(s) addresses and escape text',()=>{
  assert.match(companyLink('https://www.360blue.com/rentals/x'),/href="https:\/\/www.360blue.com\/rentals\/x"[^>]*>Şirketin ilan sayfası · 360blue.com ↗<\/a>/);
  assert.equal(companyLink('javascript:alert(1)'),'javascript:alert(1)');
  assert.equal(companyLink('<b>'),'&lt;b&gt;');
});
import {AgencyPrices, agencyCell, bedroomCell, quoteTag, quoteBreakdown, weekdays, PAGE_LABELS, AGENCY_CONNECTOR} from '../studio/web/agency.js';
test('agency price cells keep missing prices, skipped windows and availability visible',()=>{
  assert.equal(AGENCY_CONNECTOR,'agency-lodging-rates');
  assert.deepEqual(jobResultTarget({kind:'source_collection',result:{connector_name:'agency-lodging-rates'}}),{href:'#collect/lodging',label:'Konaklama fiyatlarını aç'});
  assert.match(agencyCell({status:'skipped_past'}),/Geçmiş tarih; sorulmadı/);
  assert.match(agencyCell({status:'queried',queried_count:0,listing_count:5,linked_count:2}),/Sorgulanan ilan yok<\/span><small>5 ilan · 2 bağlantılı/);
  assert.match(agencyCell({status:'queried',queried_count:0,listing_count:7,linked_count:7,own_listing_count:73,own:{priced_count:69,total_median:12000}}),/kendi envanteri: 73 ev · fiyatlı 69 · ortanca \$12,000/);   // Alys Beach: no Book>Direct listing asked, own homes priced
  const cell=agencyCell({status:'queried',queried_count:4,priced_count:3,priced_share:0.75,available_share:1,total_q1:1666.43,total_median:1936.65,total_q3:2637.9,nightly_median:247.02});
  assert.match(cell,/4 ilan soruldu/);assert.match(cell,/fiyatlı 3 \(%75\) · müsait %100/);
  assert.match(cell,/<strong>\$1,937<\/strong><small>toplam ortanca · \$1,666–\$2,638<\/small><small>kira gecelik \$247/);
  assert.match(agencyCell({status:'queried',queried_count:2,priced_count:0,priced_share:0,available_share:null,total_median:null}),/müsait —.*Fiyat alınamadı/);
  assert.match(bedroomCell({bedrooms:{'1-2':{count:0,median:null},'3':{count:2,median:1500},'4':{count:0,median:null},'5+':{count:1,median:3000}}}),/1–2 oda: —<\/small><small>3 oda: \$1,500 \(2\)/);
  assert.equal(weekdays([6,7]),'Cumartesi, Pazar');assert.equal(weekdays(null),'');
});
test('agency quote tags and breakdown show only what the site gave',()=>{
  assert.match(quoteTag(undefined),/Sorulmadı/);
  assert.match(quoteTag({status:'priced',total:3339.16}),/\$3,339<small>toplam/);
  assert.match(quoteTag({status:'restricted',min_stay:4}),/konaklama kuralına takıldı<\/span><small>en az 4 gece/);
  const window={label:'Kış <2027>',checkin:'2027-01-16',checkout:'2027-01-23',nights:7};
  const html=quoteBreakdown({status:'priced',rent:705.99,fees:[{name:'Cleaning <Fee>',amount:325}],tax_items:[{name:'Tax',amount:149.59}],total:1396.21,
    total_includes_taxes:1,total_includes_fees:1,excluded_items:[{name:'Insurance',amount:100.34,reason:'sitede isteğe bağlı, seçilmemiş'}],
    min_stay:3,checkin_days:[6],rule_source:'sayfa',message:null,queried_at:'2027-01-01T00:00:00Z',currency:'USD'},window);
  assert.match(html,/Kış &lt;2027&gt;/);assert.match(html,/<td>Cleaning &lt;Fee&gt;<\/td><td>\$325<\/td>/);
  assert.match(html,/Toplam = kira \+ ücretler \+ vergiler/);assert.match(html,/Toplama dahil edilmeyen: Insurance \$100/);
  assert.match(html,/en az 3 gece · giriş günü: Cumartesi/);assert.match(html,/ilan sayfasının takviminden/);
  const empty=quoteBreakdown({status:'unavailable',rent:null,fees:null,tax_items:null,total:null,message:'Not <Available>',queried_at:null,currency:null},window);
  assert.doesNotMatch(empty,/<table/);assert.match(empty,/Site: Not &lt;Available&gt;/);assert.match(empty,/müsait değil/);
  assert.match(quoteBreakdown(undefined,window),/sorulmadı/);
  assert.equal(PAGE_LABELS.no_url,"Book>Direct'te şirket bağlantısı yok");
});
test('agency section draws the price table, bedroom medians and company results',()=>{
  const nodes={};const node=()=>({innerHTML:'',textContent:'',addEventListener(){},querySelector:selector=>nodes[selector] ??= node()});
  const body=node();const target={querySelector:selector=>selector==='#agency-body'?body:(nodes[selector] ??= node())};
  const prices=new AgencyPrices();
  prices.snapshot={run:{id:'a1'},snapshot:{lodging_run_id:'lodging1',queried_on:'2026-10-08',request_count:120},
    windows:[{window_key:'w',label:'Kış',checkin:'2027-01-16',checkout:'2027-01-23',nights:7,status:'queried'},{window_key:'p',label:'Eski',checkin:'2026-01-03',checkout:'2026-01-10',nights:7,status:'skipped_past'}],
    regions:[{region_id:'seaside',region_name:'Seaside'}],
    cells:[{region_id:'seaside',window_key:'w',status:'queried',listing_count:5,linked_count:4,queried_count:4,priced_count:3,priced_share:0.75,available_share:1,total_median:1936.65,total_q1:1666,total_q3:2637,nightly_median:247,bedrooms:{'1-2':{count:0,median:null},'3':{count:1,median:1396},'4':{count:1,median:1936},'5+':{count:1,median:3339}}},
           {region_id:'seaside',window_key:'p',status:'skipped_past',listing_count:5,linked_count:4}],
    companies:[{company:'<Benchmark>',domain:'benchmark30a.com',adapter:'rescms',listing_count:241,matched_count:200,priced_count:150,quote_count:800,request_count:900,status:'stopped_blocked',message:'Site reddetti'}],
    coverage:{listings:2389,matched:600,priced_listings:400,regions:13,regions_with_price:12,no_url:10,no_adapter:1500,not_found:100,no_listing:0},
    label:'Kiralama şirketlerinin kendi sitelerinde 2026-10-08 tarihinde sorgulanan fiyatlar; toplam fiyat vergileri içerir.',nightly_note:'Gecelik ortalama = kira ÷ gece.',bedroom_note:'Oda sayısı Book>Direct ilanından.'};
  prices.draw(target);
  assert.match(body.innerHTML,/<strong>2389<\/strong><span class="metric-label">Book&gt;Direct ilanı/);
  assert.match(body.innerHTML,/879 ilan yapılandırılmış şirketlere bağlı/);
  assert.match(body.innerHTML,/2026-10-08 tarihinde sorgulanan fiyatlar/);
  assert.match(body.innerHTML,/data-agency-region="seaside">Seaside<\/button>/);
  assert.match(body.innerHTML,/Geçmiş tarih; sorulmadı/);assert.match(body.innerHTML,/5\+ oda: \$3,339 \(1\)/);
  assert.match(body.innerHTML,/&lt;Benchmark&gt;<small>benchmark30a.com/);assert.match(body.innerHTML,/site reddetti; durduruldu<\/span><small>Site reddetti/);
  assert.match(body.innerHTML,/şirket sitesi sayfayı bulamadı \(404\) 100/);
});
test('the lodging screen keeps drawing its price section after a destination reset',()=>{
  const calls=[];const agency={render:(target,data)=>calls.push([target,data.agency_runs]),invalidate(){}};
  const screen=new LodgingScreen(agency);
  const nodes={};const main={innerHTML:'',querySelector:selector=>nodes[selector] ??= {id:selector,innerHTML:'',addEventListener(){}}};
  const data={sources:[{enabled:1,connector:{name:'bookdirect-lodging'},id:'s'}],jobs:[],lodging_runs:[],agency_runs:['a'],selected_destination:null,lodging_connector:{config:null}};
  screen.render(main,data,()=>'');
  assert.equal(calls.length,1);assert.equal(calls[0][0].id,'#agency-prices');assert.deepEqual(calls[0][1],['a']);
  resetDestinationState({}, [screen]);
  assert.equal(screen.agency,null);                                  // why app.js attaches the section again after a reset
  const source=readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
  assert.match(source,/resetDestinationState\(state,\[[^\]]*agencyPrices[^\]]*\]\);\s*lodgingScreen\.agency=agencyPrices;/);
});
test('jobs panel names the site waiting for the user verification',async()=>{
  const {readFileSync}=await import('node:fs');
  const source=readFileSync(new URL('../studio/web/jobs.js',import.meta.url),'utf8');     // GÖREV-17: the panel is drawn by jobs.js
  assert.match(source,/job\.waiting_for\?`<p class="job-waiting"><span class="tag warm">Kullanıcı doğrulaması bekleniyor<\/span> \$\{esc\(job\.waiting_for\)\}/);
});
import {methodLine, ownLine, publishedLine, ownTable, publishedTag, publishedBreakdown, METHOD_LABELS} from '../studio/web/agency.js';
test('agency v2 cells name the match method, own inventory and published rents apart from the totals',()=>{
  assert.equal(methodLine({by_method:{link:3,address:0,location:0}}),'');
  assert.match(methodLine({by_method:{link:3,address:2,location:1}}),/eşleme: bağlantı 3 · adres 2 · konum 1/);
  assert.equal(METHOD_LABELS.location,'konum');
  assert.equal(ownLine({own_listing_count:0,own:{priced_count:0}}),'');
  assert.match(ownLine({own_listing_count:12,own:{priced_count:9,total_median:14768.32}}),/kendi envanteri: 12 ev · fiyatlı 9 · ortanca \$14,768/);
  assert.match(publishedLine({published:{count:4,low_median:1925,high_median:4536}}),/yayımlanmış kira \(vergi ve ücret hariç\): 4 ilan · ortanca \$1,925–\$4,536/);
  assert.equal(publishedLine({published:{count:0}}),'');
  assert.match(publishedTag({rent_low:1925,rent_high:4536}),/yayımlanmış kira \$1,925–\$4,536/);
  assert.match(publishedBreakdown({rent_low:1925,rent_high:4536,basis:'Sitenin <sezon> aralığı'}),/toplam fiyata karışmaz[^]*Sitenin &lt;sezon&gt; aralığı/);
  const own=ownTable([{title:'103 <North>',address:'103 North Charles Street',bedrooms:4,company:'Alys',domain:'alysbeach.com',page_url:'https://vacation.alysbeach.com/vrp/unit/x',quotes:{w:{status:'priced',total:14768.32}}}],[{window_key:'w',label:'Kış'}]);
  assert.match(own,/Şirketin kendi envanteri/);assert.match(own,/103 &lt;North&gt;/);assert.match(own,/\$14,768<small>toplam/);
  assert.equal(ownTable([],[]),'');
});
import {levelCell, reservationCell, kidsCell, factLine, siteDetail, regionSummary, filterRestaurants as filterWithSites, SITE_CONNECTOR} from '../studio/web/restaurants.js';
test('restaurant business-site cells keep unknown values unknown and label our price level',()=>{
  assert.equal(SITE_CONNECTOR,'restaurant-sites');
  assert.match(levelCell({price_level:'$$$',main:{median:34,count:5}}),/<strong>\$\$\$<\/strong><small>ana yemek ortancası \$34 · 5 kalem/);
  assert.match(levelCell({price_level:null,main:{count:3},level_reason:"5'ten az fiyatlı ana yemek (3)"}),/hesaplanmadı<\/span><small>5&#39;ten az fiyatlı ana yemek \(3\)/);
  assert.match(levelCell({price_level:null,main:{count:0},level_reason:'tapas',small_plates:{count:6,median:14}}),/küçük tabak ortancası \$14 · 6 kalem/);
  assert.equal(levelCell({price_level:null,main:{count:0}}),'<span class="muted">hesaplanmadı</span>');
  assert.match(reservationCell({reservation:'online',reservation_platform:'OpenTable'}),/çevrim içi<small>OpenTable/);
  assert.match(reservationCell({}),/bilinmiyor/);assert.match(kidsCell({kids_menu:'yes'}),/evet/);assert.match(kidsCell(undefined),/bilinmiyor/);
  const hours=factLine('hours',{value:'stated',detail:'Mon - Thu 11am - 9pm',data:{Mon:'11:00–21:00'},source_url:'https://x.example/contact',fetched_at:'2026-10-08T10:00:00Z',method:'sayfa metni',raw_sha256:'abcdef1234567890'});
  assert.match(hours,/işletmenin sitesinde yazan/);assert.match(hours,/<td>Mon<\/td><td>11:00–21:00<\/td>/);assert.match(hours,/sayfa metni · SHA-256 abcdef1234/);
  assert.match(factLine('dog_friendly',undefined),/bilinmiyor/);
  const records=[{external_id:'a',name:'A',source_neighborhoods:[],cuisines:[],meals_served:[]},{external_id:'b',name:'B',source_neighborhoods:[],cuisines:[],meals_served:[]}];
  const sites={a:{price_level:'$$',reservation:'online',kids_menu:'yes'},b:{price_level:null}};
  assert.deepEqual(filterWithSites(records,{level:'$$'},sites).map(r=>r.name),['A']);
  assert.deepEqual(filterWithSites(records,{level:'none'},sites).map(r=>r.name),['B']);
  assert.deepEqual(filterWithSites(records,{reservation:'none',kids:'none'},sites).map(r=>r.name),['B']);
  const detail=siteDetail({site_status:'working',site_url:'https://x.example/',final_url:'https://x.example/',site_source:'review',price_level:'$$',main:{median:18,min:12,max:30,count:9},
    main_menu_id:1,menus:[{menu_id:1,url:'https://x.example/menu',title:'Dinner',menu_type:'dinner',format:'pdf',status:'read',item_count:20,method:'PDF metni'}],
    items:[{menu_id:1,section_class:'ana_yemek',name:'Grouper <b>',section:'ENTREES',price_text:'$28',price_rule:'single'}],facts:{}},'Fiyat seviyesi bizim sınıflamamızdır');
  assert.match(detail,/resmî site \(web aramasıyla bulundu\)/);assert.match(detail,/akşam menüsünden/);assert.match(detail,/Grouper &lt;b&gt;/);
  assert.match(detail,/fiyat seviyesi bu menüden/);assert.match(detail,/bizim sınıflamamızdır/);
  const summary=regionSummary({level_note:'n',hours_note:'h',regions:[{region_name:'Seaside',restaurant_count:12,levels:{'$':1,'$$':5,'$$$':2,'$$$$':0},median_of_medians:21.5,online_reservation:4,kids_menu:6,no_information:3}]});
  assert.match(summary,/<td>Seaside<\/td><td>12<\/td><td>1<\/td><td>5<\/td><td>2<\/td><td>0<\/td><td>\$21\.50<\/td><td>4<\/td><td>6<\/td><td>3<\/td>/);
  assert.equal(regionSummary(null),'');
});
import {refreshSection, duration, STEP_LABELS} from '../studio/web/refresh.js';
test('refresh section lists every collector, the due ones, the estimate and a running batch with its stop button',()=>{
  assert.equal(duration(null),'bilinmiyor');assert.equal(duration(20),'~1 dk');assert.equal(duration(3*3600+20*60),'~3 sa 20 dk');assert.equal(duration(7200),'~2 sa');
  const items=[{connector:'bookdirect-lodging',source_name:'Book>Direct <konaklama>',interval_months:1,due:true,due_reason:'hiç çekilmedi',last_done_on:null,estimate_seconds:null},
    {connector:'restaurant-sites',source_name:'İşletme siteleri',interval_months:3,due:false,last_done_on:'2026-10-09',next_due_on:'2027-01-09',estimate_seconds:3600},
    {connector:'nws-weather',source_name:'NWS',interval_months:null,due:false,last_done_on:'2026-10-01'}];
  const html=refreshSection({items,note:'kendiliğinden çalışmaz',estimate_seconds:null,estimate_complete:false,batch:null});
  assert.match(html,/<h2>Güncelleme zamanı gelenler<\/h2>/);assert.match(html,/Book&gt;Direct &lt;konaklama&gt;/);
  assert.match(html,/zamanı geldi<\/span><small>hiç çekilmedi/);assert.match(html,/güncel<\/span><small>sonraki: 9 Ocak 2027/);
  assert.match(html,/aralık tanımlı değil/);assert.match(html,/<span>1 toplayıcı · tahmini süre bilinmiyor<\/span>/);
  assert.match(refreshSection({items,note:'',estimate_seconds:3600,estimate_complete:false,batch:null}),/tahmini süre ~1 sa \(bazılarının süresi bilinmiyor; yalnız bilinenler toplandı\)/);
  assert.match(html,/data-action="refresh-start" >Zamanı gelenleri başlat/);assert.match(html,/son 6 yedek saklanır/);
  assert.match(refreshSection({items,note:'',batch:null},true),/data-action="refresh-start" disabled/);
  const running=refreshSection({items,note:'',estimate_seconds:60,estimate_complete:true,batch:{id:'b1',status:'running',created_at:'2026-10-09T10:00:00+00:00',backup_file:'backups/toplu-1.sqlite3',
    message:'Uygulamanın yedeği alındı',plan:[{source_name:'Book>Direct',status:'done'},{source_name:'Kiralama',status:'skipped',message:'girdisi yok'}]}});
  assert.match(running,/data-action="refresh-start" disabled/);assert.match(running,/Son toplu çalıştırma: Sürüyor/);assert.match(running,/yedek: backups\/toplu-1\.sqlite3/);
  assert.match(running,/<li>Book&gt;Direct · tamamlandı<\/li>/);assert.match(running,/Kiralama · atlandı <small>\(girdisi yok\)/);
  assert.match(running,/data-action="refresh-cancel" data-batch="b1">Toplu çalıştırmayı durdur/);
  assert.match(refreshSection({items:[],note:'',batch:null}),/Zamanı gelen toplayıcı yok\./);assert.equal(refreshSection(null),'');
  assert.equal(STEP_LABELS.skipped,'atlandı');
});
import {windowHeader, seasonTable, comparisonTable} from '../studio/web/lodging.js';
test('monthly windows show the days from the query, our season groups and the same-week comparison with matched counts',()=>{
  assert.match(windowHeader({label:'Temmuz 2027 · 10–17 Temmuz',checkin:'2027-07-10',checkout:'2027-07-17',nights:7,lead_days:274}),/Temmuz 2027 · 10–17 Temmuz<small>2027-07-10 → 2027-07-17 · 7 gece · sorgudan 274 gün sonra/);
  const regions=[{region_id:'seaside',region_name:'Seaside'},{region_id:'alys',region_name:'Alys Beach'}];
  const seasons=seasonTable({note:'bizim gruplamamızdır',rows:[{region_id:'seaside',season:'yaz',window_count:3,priced_count:9,median:450},{region_id:'alys',season:'yaz',window_count:3,priced_count:0,median:null}]},regions,'gecelik fiyat');
  assert.match(seasons,/Mevsimlere göre \(bizim gruplamamız\)/);assert.match(seasons,/<th>YAZ<\/th>/);assert.ok(!seasons.includes('KIŞ'));
  assert.match(seasons,/\$450<\/strong><small>9 fiyat · 3 pencere/);assert.match(seasons,/fiyat yok<\/span><small>3 pencere/);
  assert.equal(seasonTable(null,regions,'x'),'');
  assert.match(comparisonTable(null,regions),/karşılaştırma ikinci aylık çekimden sonra oluşur/);
  const comparison=comparisonTable({label:'aynı evlerin aynı hafta için 2026-10-09 ve 2026-11-09 tarihlerinde sorgulanan fiyatları; bizim hesabımız',basis:'gecelik fiyat (Book>Direct)',
    windows:[{window_key:'ay-2027-07',label:'Temmuz 2027 · 10–17 Temmuz',earlier_label:'Yaz',checkin:'2027-07-10',checkout:'2027-07-17'}],
    rows:[{region_id:'seaside',window_key:'ay-2027-07',matched_count:4,median_change:0.05,median_amount:20},{region_id:'alys',window_key:'ay-2027-07',matched_count:0,median_change:null}]},regions);
  assert.match(comparison,/aynı evlerin aynı hafta için 2026-10-09 ve 2026-11-09/);assert.match(comparison,/önceki: Yaz/);
  assert.match(comparison,/<strong>\+%5<\/strong><small>\+\$20 · 4 eşleşen ilan/);assert.match(comparison,/eşleşen ilan yok/);
});
import {miles, pointSource, OUTCOME_LABELS} from '../studio/web/dailyneeds.js';
import {fixedMenuLine} from '../studio/web/restaurants.js';
test('daily needs show great-circle miles, the share within a mile and the source of each point',()=>{
  assert.match(miles({median_km:1.2345,median_mi:0.77,within_1mi_share:0.625}),/<strong>0,77 mil<\/strong><small>1\.235 m · 1 mil içinde %63/);
  assert.equal(miles({median_km:null}),'<span class="muted">—</span>');assert.equal(miles(undefined),'<span class="muted">—</span>');
  assert.match(pointSource({source:'openstreetmap',source_url:'https://www.openstreetmap.org/node/1'}),/href="https:\/\/www\.openstreetmap\.org\/node\/1"[^>]*>OpenStreetMap ↗/);
  assert.equal(pointSource({source:'zincirin kendi sitesi',source_url:'javascript:alert(1)'}),'zincirin kendi sitesi');
  assert.equal(OUTCOME_LABELS.eklendi,"OpenStreetMap'te yok; zincirin sitesinden eklendi");
  assert.match(fixedMenuLine({fixed_menus:[{name:'Chef <Menu>',price_text:'$95',price:95}]}),/Sabit menü fiyatı: Chef &lt;Menu&gt; \$95 <small>\(ana yemek ortancasına karışmaz/);
  assert.equal(fixedMenuLine({}),'');
});

import {paramsText, packLink, packRow, attachedLinks, EvidenceScreen} from '../studio/web/evidence.js';

test('evidence pack rows show parameters, size, missing rows and both downloads with their SHA-256', () => {
  setDestination('30a');
  assert.equal(paramsText({mahalle:'rosemary-beach'},{'rosemary-beach':'Rosemary Beach'}), 'mahalle: Rosemary Beach');
  assert.equal(paramsText({}), '');
  assert.equal(packLink('abc','markdown'), '/api/evidence-packs/abc/markdown?destination_id=30a');
  const pack={id:'abc',title:'Mahalle <rehberi>',template_key:'mahalle-rehberi',template_version:'1',params:{mahalle:'seaside'},created_at:'2026-10-10T12:00:00+00:00',
    section_count:8,evidence_count:172,number_count:549,missing_count:3,markdown_sha256:'a'.repeat(64),json_sha256:'b'.repeat(64)};
  const html=packRow(pack,{seaside:'Seaside'});
  assert.match(html,/Mahalle &lt;rehberi&gt;/);
  assert.match(html,/mahalle: Seaside/);
  assert.match(html,/172 kanıt satırı · 549 sayı/);
  assert.match(html,/3 'veri yok' satırı/);
  assert.match(html,/evidence-packs\/abc\/json\?destination_id=30a/);
  assert.match(html,/SHA-256 aaaaaaaaaaaaaaaa…/);
  assert.doesNotMatch(packRow({...pack,missing_count:0}),/veri yok/);
  setDestination(null);
});

test('writer summary and number list links appear only for packs that have them (GÖREV-12)', () => {
  setDestination('30a');
  const both=attachedLinks({id:'abc',ekler:{yazar_ozeti:true,sayilar:true}});
  assert.match(both,/href="\/api\/evidence-packs\/abc\/yazar-ozeti\?destination_id=30a" download>Yazar özeti ↓/);
  assert.match(both,/href="\/api\/evidence-packs\/abc\/sayilar\?destination_id=30a" download>Sayı listesi \(CSV\) ↓/);
  const onlySummary=attachedLinks({id:'abc',ekler:{yazar_ozeti:true,sayilar:false}});
  assert.match(onlySummary,/Yazar özeti ↓/);
  assert.doesNotMatch(onlySummary,/Sayı listesi/);
  for(const old of [{id:'abc'},{id:'abc',ekler:{yazar_ozeti:false,sayilar:false}}]) {
    assert.equal(attachedLinks(old),'<small class="muted">Yazar özeti ve sayı listesi yok (eski üretim)</small>');
  }
  const row=packRow({id:'abc',title:'T',template_key:'ilk-video',template_version:'1',params:{},created_at:'2026-10-10T12:00:00+00:00',section_count:11,
    evidence_count:843,number_count:1723,missing_count:0,markdown_sha256:'a'.repeat(64),json_sha256:'b'.repeat(64),ekler:{yazar_ozeti:true,sayilar:true}});
  assert.ok(row.indexOf('Yazar özeti ↓')<row.indexOf('Markdown ↓'));                  // the writing column comes before the full pack
  setDestination(null);
});

test('evidence screen asks for every template parameter before generating', async () => {
  const screen=new EvidenceScreen();
  screen.templates=[{key:'mahalle-rehberi',title:'Mahalle rehberi',question:'?',parameters:[{key:'mahalle',label:'Mahalle',kind:'region',choices:[]}],sections:[]}];
  screen.selected='mahalle-rehberi';screen.packs=[];
  let drawn=0;screen.draw=()=>{drawn++;};
  await screen.generate(null);
  assert.equal(screen.message,'Önce Mahalle seçin.');
  assert.equal(screen.busy,false);
  assert.equal(drawn,1);
});

import {choiceNames} from '../studio/web/evidence.js';

test('a pack lists its neighborhood by name whichever template is selected (GÖREV-13)', () => {
  const templates=[{key:'ilk-video',parameters:[]},{key:'mahalle-rehberi',parameters:[{key:'mahalle',choices:[{id:'rosemary-beach',name:'Rosemary Beach'}]}]}];
  assert.deepEqual(choiceNames(templates),{'rosemary-beach':'Rosemary Beach'});
  assert.match(packRow({id:'x',title:'Mahalle rehberi',template_key:'mahalle-rehberi',template_version:'1',params:{mahalle:'rosemary-beach'},created_at:'',
    section_count:8,evidence_count:1,number_count:1,missing_count:0,markdown_sha256:'a'.repeat(64),json_sha256:'b'.repeat(64)},choiceNames(templates)),/mahalle: Rosemary Beach/);
});

import {regionOptions, familyOptions, warnings, runRow, candidateList, candidateDetail, bankRuns} from '../studio/web/videos.js';
import {claudeSection} from '../studio/web/claude.js';
import {storedVideo, persistVideo, progressText, nextTask, statusTag} from '../studio/web/workflow.js';
import {PROJECT_SCREENS, VERI_TABS, routeOf as layerRoute, redirectOf, projectNav, videoNav, sidebar, veriTabs, projectLabel, stepHref} from '../studio/web/layers.js';
import {usageHtml, claudeProgress, progressText as claudeProgressText, durationText, claudeBar} from '../studio/web/usage.js';
import {editorHtml, versionRows, fileButtons} from '../studio/web/instructions.js';
import {suffixSection} from '../studio/web/claude.js';
import {instructionLine} from '../studio/web/videos.js';
import {editProblems, editForm, reviewSummary, runRow as videoRunRow} from '../studio/web/videos.js';
import {packHead} from '../studio/web/workflow.js';
import * as E from '../eklenti/logic.js';
import {connectionText, extensionSection, extensionReading, warmUpSection, trialRows} from '../studio/web/extension.js';

const titleOptions={available:true,whole_region:'30A geneli',regions:[{id:'rosemary-beach',name:'Rosemary Beach'}],families:['Genel planlama','Deneyim'],all_families:'hepsi',
  claude:{found:true,api_key_warning:null}};
const titleCandidate={sira:0,baslik_en:'Why <People> Pay So Much',baslik_tr:'Neden bu kadar ödeniyor',bolge:'Rosemary Beach',aile:'Deneyim',neden_onerildi:'Çünkü',
  izleyici_sorusu:'Değer mi?',kanca:{metin:'Kanca',kanitlar:[{dosya:'veri_ozeti_mahalle.md',kimlik:'K0034',paket_id:'abcdef1234',ifade:'Ortanca fiyat',deger_metni:'3,727 USD (7 gece)',etiket:'bizim hesabımız'}]},
  icerik_plani:[{bolum:'Fiyat',ne_anlatir:'Ay ay',kanitlar:[]}],eksik_veri:['Yorum yok'],sablon:'mahalle-rehberi',parametreler:{mahalle:'rosemary-beach'},
  yeni_sablon_gerekir:false,kapak_fikri:'Kapak',sorunlar:[],secilebilir:true,video_id:null};

test('the Videolar form offers the region (required), the families and warns about the API key (GÖREV-13)', () => {
  assert.match(regionOptions(titleOptions,''),/<option value="">Bölge seçin…<\/option><option value="30A geneli" >30A geneli<\/option><option value="Rosemary Beach" >/);
  assert.match(familyOptions(titleOptions,'Deneyim'),/<option value="hepsi" >hepsi<\/option>.*<option value="Deneyim" selected>/s);
  assert.equal(warnings(titleOptions),'');
  assert.match(warnings({...titleOptions,claude:{found:false,api_key_warning:'ANTHROPIC_API_KEY ortam değişkeni tanımlı'}}),/Claude Code bulunamadı.*ANTHROPIC_API_KEY/s);
  assert.match(runRow({id:'r1',params:{bolge:'Rosemary Beach',aile:'hepsi',not:''},status:'awaiting_approval',created_at:'2026-10-10T12:00:00Z',model_label:'Opus 5.5',effort_label:'Yüksek',metrics:{turns:9,elapsed_s:120}}),
    /href="#konu\/calisma\/r1".*Havuzda.*Opus 5.5 · Yüksek.*9 tur/s);
});

test('titles are listed first; a chosen title opens its details with the evidence values and the select button', () => {
  const view={params:{bolge:'Rosemary Beach'},actions:{select:true},candidates:[titleCandidate,{...titleCandidate,sira:1,baslik_en:'Second',sorunlar:[{seviye:'hata',metin:'Var olmayan kanıt'}],secilebilir:false}]};
  const closed=candidateList(view,null);
  // GÖREV-21: the Turkish title large, the English one small and pale
  assert.match(closed,/<span class="title-tr-big small">Neden bu kadar ödeniyor<\/span><span class="title-en-small" lang="en">Why &lt;People&gt; Pay So Much<\/span>.*Deneyim/s);
  assert.doesNotMatch(closed,/Neden önerildi/);
  assert.match(closed,/doğrulama hatası/);
  const open=candidateList(view,0);
  assert.match(open,/Neden önerildi.*İzleyicinin sorusu.*Kanca.*K0034.*3,727 USD \(7 gece\).*İçerik planı.*Fiyat.*Eksik veri.*Yorum yok.*mahalle-rehberi.*mahalle = rosemary-beach.*Kapak fikri.*Bu başlıkla video aç/s);
  assert.match(candidateDetail(view.candidates[1],view),/Hata: Var olmayan kanıt.*data-select-candidate="1" disabled/s);
  assert.match(candidateDetail({...titleCandidate,video_id:'v1',video_adi:'Rehber'},view),/Kullanıldı: “Rehber” videosunda\..*href="#video\/v1\/baslik"/s);
  assert.doesNotMatch(candidateDetail({...titleCandidate,video_id:'v1'},view),/Bu başlıkla video aç/);
});

test('a video record without a template still produces its plan pack (GÖREV-14); the Claude settings section shows path, version and inherit choices', () => {
  const section=claudeSection({settings:{claude_path:'',claude_model:'',claude_effort:'',claude_model_baslik:'claude-opus-5-5',claude_effort_baslik:'high',claude_output_guess_baslik:60000,
      claude_call_limit:250000,claude_job_limit:1500000},
    notes:[],info:{found:true,path:'D:/programs/claude.exe',version:'2.1.284',api_key_warning:'ANTHROPIC_API_KEY uyarısı'},
    harcama:[{adim:'baslik',baslik:'Konu ve başlık',yeni:{sayi:0},eski:{sayi:3,ortanca:460000,en_yuksek:470000}}],
    options:{models:[{value:'',label:'Claude Code varsayılanı'},{value:'claude-opus-5-5',label:'Opus 5.5'}],efforts:[{value:'',label:'Otomatik'},{value:'high',label:'Yüksek'}],
      inherit:{value:'inherit',label:'Genel varsayılan'},steps:[{key:'baslik',label:'Konu ve başlık',screen:'Öneri al (başlık önerisi)',place:'Proje · Konu bankası',model_field:'claude_model_baslik',effort_field:'claude_effort_baslik',output_guess_field:'claude_output_guess_baslik'}],
      output_guess:{min:500,max:128000,help:'Çıktı varsayımı'},limits:[{field:'claude_call_limit',min:20000,max:1000000,default:250000,help:'tek'},{field:'claude_job_limit',min:100000,max:10000000,default:1500000,help:'iş'}]}});
  assert.ok(section.includes('Bulunan program: D:/programs/claude.exe<br>Sürüm: 2.1.284'));
  assert.match(section,/ANTHROPIC_API_KEY uyarısı/);
  assert.match(section,/data-field="claude_model_baslik".*<option value="inherit" >Genel varsayılan<\/option>.*<option value="claude-opus-5-5" selected>Opus 5.5/s);
  // GÖREV-18: no turn limit; the median spending of the step's runs (old ones marked) and the output guess; the two token limits
  assert.doesNotMatch(section,/claude_max_turns|EN FAZLA TUR/);
  assert.match(section,/SON ÇALIŞMALARIN ORTANCASI.*460 bin \(eski düzen, 3\)/s);
  assert.match(section,/data-field="claude_output_guess_baslik" min="500" max="128000" step="500" value="60000"/);
  assert.match(section,/Tek çağrı sınırı \(token\)<input type="number" data-field="claude_call_limit" min="20000" max="1000000" step="1000" value="250000"/);
  assert.match(section,/İş başına toplam sınır \(token\)<input type="number" data-field="claude_job_limit"[^>]*value="1500000"/);
  assert.match(section,/Her adım tek bir çağrıdır/);
  // GÖREV-21: one table for every Claude step — its name on the screen and the video step (or project screen) it belongs to
  assert.match(section,/CLAUDE ADIMI \(EKRANDAKİ ADI\)<\/th><th>AİT OLDUĞU YER/);
  assert.match(section,/data-claude-step="baslik"><td><strong>Öneri al \(başlık önerisi\)<\/strong><\/td><td class="step-place">Proje · Konu bankası<\/td>/);
  assert.doesNotMatch(section,/Plandan sonra dur|claude_stop_after_plan/);
});

// GÖREV-21: the two layers. The statuses come from the server (studio/workflow.py); the sidebar shows one layer at a time.

const STEP_NAMES=[['baslik','Başlık ve vaat'],['paket','Veri paketi'],['plan','Plan'],['yazim','Yazım'],['kontrol','Kontrol ve ton seçimi'],['yayin','Yayın paketi'],['ses','Seslendirme'],['kurgu','Kurgu paketi']];
const STEP_STATUS={baslik:['approved','onaylandı'],paket:['done','tamamlandı'],plan:['awaiting_approval','onay bekliyor'],yazim:['waiting','bekliyor'],kontrol:['waiting','bekliyor']};
const flow={video:{id:'v1',display_name:'Rosemary <Beach> rehberi',title_en:'Rosemary Beach Guide',title_tr:'Rosemary <Beach> rehberi'},completed:2,total:8,
  steps:STEP_NAMES.map(([id,title],index)=>({id,number:index+1,title,status:(STEP_STATUS[id]||['waiting'])[0],label:(STEP_STATUS[id]||[null,'sonraki görevde gelecek'])[1],
    next:id==='plan'?'Planı oku; uygunsa “Onayla”. Onaylanmadan yazım başlamaz.':'',planned:index>4,approval:['baslik','plan','kontrol'].includes(id),detail:null}))};
const noVideo={video:null,steps:[],completed:0,total:8};

test('GÖREV-21 menü, video açık değilken: yalnız dört proje ekranı (Ayarlar en altta, index.html\'de); adım yok', () => {
  const nav=sidebar(noVideo,layerRoute('#konu'));
  assert.deepEqual(PROJECT_SCREENS.map(s=>s.title),['Veri','Konu bankası','Kanal','Videolar']);
  assert.match(nav,/^<div class="group-label">PROJE<\/div>/);
  assert.deepEqual([...nav.matchAll(/data-screen="([a-z]+)"/g)].map(m=>m[1]),['veri','konu','kanal','videolar']);
  assert.equal((nav.match(/<a /g)||[]).length,4);                                 // nothing else: no step, no tool, no "video seçilmedi"
  assert.doesNotMatch(nav,/ADIMLAR|workflow-step|video seçilmedi|Videoyu kapat|← Proje/);
  assert.match(nav,/href="#konu" class="project-screen active" data-screen="konu" aria-current="page"/);
  assert.equal(sidebar(null,layerRoute('#sources')),projectNav('veri'));
  const index=readFileSync(new URL('../studio/web/index.html',import.meta.url),'utf8');
  assert.doesNotMatch(index,/video-select|Video seçilmedi|workflow-progress/);       // the top bar has no video selector any more
  assert.match(index,/id="project-control"/);
  assert.ok(index.indexOf('id="navigation"')<index.indexOf('id="settings-nav"'));   // Ayarlar stays at the bottom of the sidebar
});

test('GÖREV-21 menü, video açıkken: videonun adı ve "Videoyu kapat", daraltılmış "← Proje" ve yalnız o videonun sekiz adımı', () => {
  const nav=sidebar(flow,layerRoute('#video/v1/plan'));
  assert.match(nav,/AÇIK VİDEO<\/span><strong class="video-name"[^>]*>Rosemary &lt;Beach&gt; rehberi<\/strong>\s*<button type="button" class="quiet" id="video-close" data-video-close>Videoyu kapat<\/button>/);
  assert.match(nav,/data-project-toggle aria-expanded="false" aria-controls="project-collapsed">← Proje<\/button>\s*<div id="project-collapsed" class="project-collapsed" hidden><\/div>/);
  assert.deepEqual([...nav.matchAll(/data-step="([a-z]+)"/g)].map(m=>m[1]),STEP_NAMES.map(n=>n[0]));     // the eight steps, in order
  assert.equal((nav.match(/<a /g)||[]).length,8);                                 // and nothing but them
  assert.doesNotMatch(nav,/data-screen=/);
  assert.match(nav,/ADIMLAR <span class="steps-progress">2\/8<\/span>/);
  assert.match(nav,/href="#video\/v1\/plan" class="workflow-step active " data-step="plan" aria-current="page">\s*<span class="step-no">3<\/span><span><span class="nav-title">Plan<\/span>\s*<span class="nav-sub step-status warm" style="display:block">onay bekliyor/);
  assert.match(nav,/data-step="kurgu"[^>]*>\s*<span class="step-no">8<\/span>.*step-status planned" style="display:block">sonraki görevde gelecek/s);
  // "← Proje" opened (or a project screen shown while the video stays open): the four project screens under the row, the steps stay
  const open=videoNav(flow,null,{projectOpen:true,activeScreen:'kanal'});
  assert.match(open,/aria-expanded="true"[^>]*>← Proje<\/button>\s*<div id="project-collapsed" class="project-collapsed" >.*data-screen="kanal" aria-current="page"/s);
  assert.equal((open.match(/data-step=/g)||[]).length,8);
  assert.match(sidebar(flow,layerRoute('#konu')),/aria-expanded="true"/);
  // "Videoyu kapat" → the workflow has no video → the menu is the project view again
  assert.equal(sidebar(noVideo,layerRoute('#videolar')),projectNav('videolar'));
  const app=readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
  assert.match(app,/if\(event\.target\.closest\("\[data-video-close\]"\)\) \{closeVideo\(\)/);
  assert.match(app,/async function closeVideo\(\) \{\s*state\.videoId="";[\s\S]*?api\("videolar\/kapat",\{method:"POST"/);
});

test('GÖREV-21 adresler: katmanlar, Veri sekmeleri, proje adı ve hatırlanan video', () => {
  assert.deepEqual(layerRoute('#video/v1/yazim/surum/s9'),{layer:'video',screen:'video',page:'video',videoId:'v1',step:'yazim',view:'surum',id:'s9'});
  assert.equal(layerRoute('#video/v1').step,'baslik');
  assert.deepEqual(layerRoute('#konu/calisma/r1'),{layer:'proje',screen:'konu',page:'konu',runId:'r1'});
  assert.deepEqual(layerRoute('#kanal/tonlar'),{layer:'proje',screen:'kanal',page:'kanal',section:'tonlar'});
  assert.equal(layerRoute('#videolar/arsiv').archived,true);
  for(const [hash,tab] of [['#sources','sources'],['#collect/weather','collect'],['#quality','quality'],['#evidence','evidence'],['#veri/okuma','okuma'],['','sources']])
    assert.deepEqual([layerRoute(hash).screen,layerRoute(hash).tab],['veri',tab],hash);
  assert.equal(layerRoute('#settings/claude').layer,'ayarlar');assert.equal(layerRoute('#bilinmeyen'),null);
  assert.deepEqual(VERI_TABS.map(t=>t.title),['Kaynaklar','Toplama','Kalite','Kanıt paketi','Okuma denemeleri']);   // the tab names are written on the screen
  const tabs=veriTabs('collect');
  assert.match(tabs,/aria-label="Veri sekmeleri"/);assert.match(tabs,/class="section-nav-item active" href="#collect" data-tab="collect" aria-current="page">Toplama</);
  assert.match(tabs,/href="#veri\/okuma" data-tab="okuma" >Okuma denemeleri</);
  assert.equal(stepHref('v 1','plan'),'#video/v%201/plan');
  // one project: only its name; more: a selector
  const d={id:'30a',name:'30A',subtitle:'South Walton, Florida'};
  assert.equal(projectLabel([d],d),'<span class="project-name" id="project-name">30A / South Walton</span>');
  assert.match(projectLabel([d,{id:'x',name:'Destin',subtitle:''}],d),/<select id="destination-select" aria-label="Proje"><option value="30a" selected>30A \/ South Walton<\/option><option value="x" >Destin<\/option>/);
  assert.equal(progressText(flow),'2/8');assert.equal(progressText(null),'');assert.equal(progressText(noVideo),'');
  const memory=new Map(), storage={getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,v),removeItem:k=>memory.delete(k)};
  assert.equal(storedVideo(storage,'30a'),'');
  persistVideo(storage,'30a','v1');assert.equal(storedVideo(storage,'30a'),'v1');assert.equal(storedVideo(storage,'other'),'');
  persistVideo(storage,'30a','');assert.equal(storedVideo(storage,'30a'),'');
  const broken={getItem(){throw new Error('kapalı');},setItem(){throw new Error('kapalı');},removeItem(){throw new Error('kapalı');}};
  assert.equal(storedVideo(broken,'30a'),'');persistVideo(broken,'30a','v1');
  // the open video is the server's to remember (bootstrap gives it back at the next start)
  const app=readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
  assert.match(app,/state\.videoId=data\.open_video_id \|\| "";/);
});

test('GÖREV-21 taşıma: Ayarlar\'dan taşınan bölümlerin eski adresleri ve eski adım adresleri yeni yerlerine yönlenir', () => {
  assert.equal(redirectOf('#settings/tonlar'),'#kanal/tonlar');
  assert.equal(redirectOf('#settings/talimatlar'),'#kanal/talimatlar');
  assert.equal(redirectOf('#settings/uyari-ifadeleri'),'#kanal/uyari-ifadeleri');
  assert.equal(redirectOf('#settings/baslik-eki'),'#kanal/baslik-eki');
  assert.equal(redirectOf('#ayarlar/tonlar'),'#kanal/tonlar');
  for(const kept of ['#settings','#settings/claude','#settings/eklenti','#settings/proxy','#settings/klasor','#kanal/tonlar','#konu','#sources','#video/v1/plan','']) assert.equal(redirectOf(kept),null,kept);
  assert.equal(redirectOf('#videos'),'#konu');assert.equal(redirectOf('#videos/run/r 1'),'#konu/calisma/r%201');
  assert.equal(redirectOf('#adim/veri'),'#sources');assert.equal(redirectOf('#adim/baslik','v1'),'#konu');
  assert.equal(redirectOf('#adim/paket'),'#videolar');                         // no video open: the list of videos
  assert.equal(redirectOf('#adim/paket','v1'),'#video/v1/paket');
  assert.equal(redirectOf('#adim/metin','v1'),'#video/v1/plan');
  assert.equal(redirectOf('#adim/metin/karsilastirma/r1','v1'),'#video/v1/kontrol');
  assert.equal(redirectOf('#adim/metin/surum/s1','v1'),'#video/v1/yazim/surum/s1');
  assert.equal(redirectOf('#adim/uretim','v1'),'#video/v1/kurgu');
  const app=readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
  assert.match(app,/const moved=redirectOf\(location\.hash,state\.videoId\);[^\n]*\n\s*if\(moved\) \{location\.replace\(moved\);return;\}/);
  // the sections are drawn on the Kanal screen by the same modules, with their own addresses
  assert.deepEqual(CHANNEL_SECTIONS.map(s=>s.slug),['talimatlar','tonlar','uyari-ifadeleri','baslik-eki']);
  const frame=channelFrame('tonlar');
  for(const slot of ['instructions-slot','tones-slot','warnings-slot','suffix-settings-slot']) assert.ok(frame.includes(`id="${slot}"`),slot);
  assert.match(frame,/class="section-nav-item active" href="#kanal\/tonlar"/);
  assert.equal(channelSectionOfHash('#kanal/baslik-eki'),'baslik-eki');assert.equal(channelSectionOfHash('#kanal'),null);assert.equal(channelSectionOfHash('#settings/tonlar'),null);
});

test('GÖREV-21 her adım ekranı "Sıradaki iş" satırı ve durumuyla başlar', () => {
  const line=nextTask(flow.steps[2]);
  assert.match(line,/Sıradaki iş.*Planı oku; uygunsa “Onayla”\. Onaylanmadan yazım başlamaz\..*<span class="tag warm">onay bekliyor<\/span>/s);
  assert.equal(nextTask(null),'');
  assert.equal(statusTag(flow.steps[7]),'<span class="tag planned">sonraki görevde gelecek</span>');
});

// GÖREV-14 Adım 4: usage panel, Claude progress bar, instruction editor, title suffix, the run's instruction versions.

test('usage panel: no measurement, a fresh one, an old one and this week', () => {
  assert.match(usageHtml({measured:false,week:{count:0,total_s:0}}),/CLAUDE KULLANIMI.*Yenile.*henüz ölçüm yok.*Bu hafta 0 çalışma · 0 sn/s);
  const view={measured:true,stale:false,measured_at:'2026-10-10T18:17:00+00:00',week:{count:3,total_s:842},
    windows:{five_hour:{label:'5 saatlik',percent:44,resets_at:'2026-10-10T21:00:00+00:00',reset_passed:false},
             seven_day:{label:'Haftalık',percent:82,resets_at:'2026-10-14T14:00:00+00:00',reset_passed:false}}};
  const html=usageHtml(view);
  assert.match(html,/5 saatlik<\/span><strong>%44<\/strong>.*width:44%.*sıfırlanma \d\d:\d\d.*Haftalık<\/span><strong>%82.*usage-bar high.*sıfırlanma \S+ \d\d:\d\d.*son ölçüm \d\d:\d\d.*Bu hafta 3 çalışma · 14 dk 2 sn/s);
  assert.ok(!html.includes('eski ölçüm'));
  assert.match(usageHtml({...view,stale:true}),/usage-body stale.*eski ölçüm/s);
  assert.match(usageHtml({...view,windows:{...view.windows,five_hour:{...view.windows.five_hour,reset_passed:true,percent:null}}}),/5 saatlik<\/span><strong>sıfırlandı/);
  assert.match(usageHtml(view,true,'Kullanım yenilendi.'),/disabled>Yenileniyor….*Kullanım yenilendi\./s);
  assert.equal(durationText(45),'45 sn');assert.equal(durationText(372),'6 dk 12 sn');assert.equal(durationText(3900),'1 sa 5 dk');assert.equal(durationText(null),'—');
});

test('Claude bar: inputs, Claude by time over the expected duration, validation, finished; collector jobs keep their own bar', () => {
  const start=Date.parse('2026-10-10T18:00:00Z');
  const job={id:'j1',status:'running',progress:10,created_at:'2026-10-10T18:00:00Z',
    progress_info:{tur:'claude',asama:'claude',baslangic:'2026-10-10T18:00:00Z',claude_baslangic:'2026-10-10T18:00:20Z',beklenen_s:400,dayanak:'önceki 3 başarılı çalışmanın ortancası (7 dk)'}};
  const half=claudeProgress(job,start+220000);
  assert.deepEqual([half.percent,Math.round(half.elapsed),Math.round(half.remaining),half.over],[50,220,200,false]);
  assert.equal(claudeProgressText(half),'%50 · Claude çalışıyor · geçen 3 dk 40 sn · tahmini kalan ~3 dk 20 sn');
  const late=claudeProgress(job,start+900000);
  assert.equal(late.percent,90);assert.match(claudeProgressText(late),/%90 · Claude çalışıyor · geçen 15 dk · tahminden uzun sürüyor/);
  assert.equal(claudeProgress({...job,progress:2,progress_info:{tur:'claude',asama:'girdiler',baslangic:'2026-10-10T18:00:00Z'}},start+3000).percent,2);
  assert.equal(claudeProgress({...job,progress:92,progress_info:{...job.progress_info,asama:'dogrulama'}},start+500000).percent,92);
  assert.equal(claudeProgress({...job,status:'done',progress:100},start).percent,100);
  assert.equal(claudeProgress({id:'c',status:'running',progress:40,progress_info:null}),null);
  assert.equal(claudeBar({id:'c',status:'running',progress:40}),'');
  assert.match(claudeBar(job,start+220000),/data-progress-job="j1".*Tahmin: önceki 3 başarılı.*aria-valuenow="50".*width:50%.*%50 · Claude çalışıyor/s);
});

test('instruction editor: files, metadata, versions with going back; the run shows the versions it used; the suffix card', () => {
  const files=[{key:'ortak',name:'ortak.md',kind:'talimat'},{key:'kanal_arastirmasi',name:'kanal_arastirmasi.md',kind:'bilgi'}];
  assert.match(fileButtons(files,'ortak'),/data-instruction="ortak" aria-pressed="true".*kanal_arastirmasi\.md <span class="tag">bilgi<\/span>/s);
  assert.match(versionRows([]),/önceki sürüm yok/);
  const rows=versionRows([{id:'20261010-181700-000001',saved_at:'2026-10-10T18:17:00+00:00',sha256:'abcdef0123456789',size:2048}]);
  assert.match(rows,/<code>abcdef01<\/code>.*2,0 KB.*data-version-view="20261010-181700-000001".*Bu sürüme dön/s);
  const html=editorHtml({files,file:{key:'ortak',name:'ortak.md',title:'Ortak kurallar',sha256:'1234567890ab',modified_at:'2026-10-10T18:00:00+00:00',size:1024,text:'Kural <b>',versions:[]},message:'Kaydedildi.',viewing:null});
  assert.match(html,/Tek kaynak depodaki dosyadır.*karma <code>12345678<\/code>.*Kural &lt;b&gt;<\/textarea>.*Kaydedildi\..*instruction-save.*instruction-reload/s);
  const line=instructionLine({instruction_versions:[{name:'ortak.md',short:'1a2b3c4d',modified_at:'2026-10-10T18:00:00+00:00',current:true},{name:'baslik.md',short:'9f8e7d6c',modified_at:null,current:false}]});
  assert.match(line,/Talimat sürümü: ortak\.md <code>1a2b3c4d<\/code> \(.+\) · baslik\.md <code>9f8e7d6c<\/code> <span class="tag warm">dosya o zamandan beri değişti/);
  assert.equal(instructionLine({}),'');
  assert.match(suffixSection({en:' | 30A Florida Vacation',tr:' | 30A Florida Tatili',defaults:{en:' | 30A Florida Vacation',tr:' | 30A Florida Tatili'}}),/data-suffix="en" value=" \| 30A Florida Vacation".*data-suffix="tr".*Başlangıç değerleri: İngilizce " \| 30A Florida Vacation"/s);
});

// GÖREV-14 Adım 5: own title evaluation and editing a title before choosing it.

test('title edit: the same rules as the server, and "İngilizcesini Claude yazsın" only when the Turkish title alone changed', () => {
  const suffix={en:' | 30A Florida Vacation',tr:' | 30A Florida Tatili'};
  assert.deepEqual(editProblems('Rosemary with a dog | 30A Florida Vacation','Köpekle Rosemary | 30A Florida Tatili',suffix),[]);
  assert.deepEqual(editProblems('Rosemary with a dog','Köpekle',suffix),['İngilizce başlık " | 30A Florida Vacation" ekiyle bitmiyor.','Türkçe karşılık " | 30A Florida Tatili" ekiyle bitmiyor.']);
  assert.deepEqual(editProblems('x'.repeat(101),'y',{}),['İngilizce başlık 100 karakteri aşıyor (101 karakter).']);
  const c={sira:2,baslik_en:'Rosemary Beach | 30A Florida Vacation',baslik_tr:'Rosemary Beach | 30A Florida Tatili'};
  const same=editForm(c,{index:2,en:c.baslik_en,tr:c.baslik_tr},suffix);
  assert.match(same,/id="edit-select" >.*id="edit-translate" hidden/s);
  const turkish=editForm(c,{index:2,en:c.baslik_en,tr:'Köpekle Rosemary Beach | 30A Florida Tatili'},suffix);
  assert.match(turkish,/id="edit-translate" >İngilizcesini Claude yazsın/);
  const both=editForm(c,{index:2,en:'Dogs at Rosemary | 30A Florida Vacation',tr:'Köpekle Rosemary Beach | 30A Florida Tatili'},suffix);
  assert.match(both,/id="edit-translate" hidden/);
  assert.match(editForm(c,{index:2,en:'Dogs',tr:c.baslik_tr},suffix),/ekiyle bitmiyor.*id="edit-select" disabled/s);
});

test('evaluation: the summary comes first; runs and video records show what kind they are', () => {
  const view={params:{bolge:'Rosemary Beach',kaynak:{baslik_en:'Old | 30A Florida Vacation'}},review:{kullanici_fikri:"Rosemary Beach'e köpeğimizle gitsek nasıl olur?",
    doluluk:{dolar_mi:false,aciklama:'Mahalleye özgü kural yok.',eksik_veri:['Köpek kuralı']},sorunlar:['Ek yok.']}};
  assert.match(reviewSummary(view),/Kullanıcının fikri:<\/strong> “Rosemary Beach&#39;e köpeğimizle gitsek nasıl olur\?”.*tag warm">Hayır.*Mahalleye özgü kural yok\..*Eksik veri:<\/strong> Köpek kuralı.*İfadedeki sorunlar:<\/strong> Ek yok\..*düzenlenen bir adaydan/s);
  assert.equal(reviewSummary({}),'');
  const row=videoRunRow({id:'r9',step:'baslik_degerlendirme',status:'awaiting_approval',created_at:'',params:{bolge:'Seaside',kullanici_basligi:'Seaside fikri',not:'Bu aday düzenlendi\nikinci satır',kaynak:{}},metrics:{}});
  assert.match(row,/tag">değerlendirme<\/span>.*“Seaside fikri”.*düzenlenen adaydan · Bu aday düzenlendi</s);
  assert.ok(!row.includes('ikinci satır'));
});

test('app.js imports every name once (a repeated import name stops the whole page)', () => {
  const source=readFileSync(new URL('../studio/web/app.js', import.meta.url),'utf8');
  const names=[...source.matchAll(/^import\s*\{([^}]*)\}\s*from/gm)].flatMap(m=>m[1].split(',').map(part=>part.trim().split(/\s+as\s+/).pop()).filter(Boolean));
  const repeated=names.filter((name,index)=>names.indexOf(name)!==index);
  assert.deepEqual(repeated,[]);
  assert.ok(names.includes('claudeProgressText'));
});

// GÖREV-14 Adım 6: the head of a video pack's writer's summary on the Veri paketi step.

test('pack head: everything before the first plan section', () => {
  const text='# Başlık — yazar özeti\n\n## Video\n\nkanca\n\n## Bilinen boşluklar\n\n- boşluk\n\n## 1. Bölüm\n\nsatırlar';
  assert.equal(packHead(text),'# Başlık — yazar özeti\n\n## Video\n\nkanca\n\n## Bilinen boşluklar\n\n- boşluk');
  assert.equal(packHead('# Yalnız baş'),'# Yalnız baş');
});

// GÖREV-14 Adım 7: the browser extension's pure logic (eklenti/logic.js) and Settings → Tarayıcı eklentisi.

test('extension: finds the program on 8830–8849, remembered port first, and knows it by its health answer', () => {
  assert.deepEqual([E.PORTS[0], E.PORTS.at(-1), E.PORTS.length], [8830, 8849, 20]);
  assert.deepEqual(E.portOrder(8833).slice(0, 3), [8833, 8830, 8831]);
  assert.equal(E.portOrder(undefined)[0], 8830);
  assert.ok(E.healthOk({app: 'thirtya-studio', pid: 1}));
  assert.ok(!E.healthOk({app: 'housing-atlas'}) && !E.healthOk(null));
});

test('extension: the job queue takes jobs first come first served and never the same one twice', () => {
  const queue = new E.JobQueue();
  assert.ok(queue.add({id: 'a'}) && queue.add({id: 'b'}));
  assert.ok(!queue.add({id: 'a'}) && !queue.add({}) && !queue.add(null));
  assert.equal(queue.size, 2);
  assert.equal(queue.take().id, 'a');
  assert.equal(queue.take().id, 'b');
  assert.equal(queue.take(), null);
  queue.forget('a');
  assert.ok(queue.add({id: 'a'}));
});

test('extension: at least the gap between two pages of one domain, other domains not held back', () => {
  const pacer = new E.Pacer(8);
  assert.equal(pacer.delayFor('ornek.test', 1000), 0);
  pacer.mark('www.ornek.test', 1000);
  assert.equal(pacer.delayFor('ornek.test', 3000), 6000);
  assert.equal(pacer.delayFor('https://ornek.test/a', 9000), 0);
  assert.equal(pacer.delayFor('baska.test', 3000), 0);
  assert.equal(new E.Pacer().gapMs, 8000);
});

test('extension: verification and block pages are known by the program\'s own markers', () => {
  assert.ok(E.isVerification('<html><head><title>Just a moment...</title>', ''));
  assert.ok(E.isVerification('<script>window._cf_chl_opt={}</script>', ''));
  assert.ok(E.isVerification('<div id="px-captcha"></div>', ''));
  assert.ok(E.isVerification('<p>Press &amp; Hold</p>', ''));
  assert.ok(E.isVerification('<html></html>', 'Just a moment...'));
  assert.ok(!E.isVerification('<html><title>Menu</title><script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>', 'Menu'));
  assert.ok(!E.isVerification('<form><div class="cf-turnstile"></div></form>', 'Contact'));
  assert.ok(E.isBlocked('<h1>Sorry, you have been blocked</h1>') && !E.isBlocked('<h1>Hello</h1>'));
  assert.equal(E.classify({html: '<title>Just a moment...</title>', title: 'Just a moment...', url: 'https://a.test/'}), 'dogrulama');
});

test('extension: a login or payment page is not read; an ordinary page with a sign-in link is', () => {
  assert.ok(E.isLogin({html: '<form><input type="password" name="p"></form>', url: 'https://a.test/'}));
  assert.ok(E.isLogin({html: '<p>x</p>', url: 'https://a.test/account/login?next=/'}));
  assert.ok(E.isLogin({html: '', url: 'https://a.test/x', title: 'Sign in to continue'}));
  assert.ok(!E.isLogin({html: '<a href="/login">Sign in</a><h1>Menu</h1>', url: 'https://a.test/menu', title: 'Menu'}));
  assert.ok(E.isPayment({html: '', url: 'https://a.test/checkout/'}));
  assert.ok(E.isPayment({html: '<input autocomplete="cc-number">', url: 'https://a.test/order'}));
  assert.ok(!E.isPayment({html: '<p>Pay at the door</p>', url: 'https://a.test/menu'}));
  assert.equal(E.classify({html: '<input type=password>', url: 'https://a.test/'}), 'giris');
  assert.equal(E.classify({html: '<p>ok</p>', url: 'https://a.test/payment'}), 'odeme');
  assert.equal(E.classify({html: '<p>ok</p>', url: 'https://a.test/menu'}), 'oku');
  assert.deepEqual(E.pageResult('giris', {url: 'https://a.test/login', title: 'Log in', html: '<secret>'}, 'giriş gerekiyor'),
    {durum: 'giris', son_adres: 'https://a.test/login', baslik: 'Log in', http_durumu: null, not: 'giriş gerekiyor'});
  assert.equal(E.pageResult('tamam', {url: 'u', html: '<p>x</p>', status: 200}).html, '<p>x</p>');
});

test('extension: permissions are per site (and its subdomains); the local program needs none of its own', () => {
  assert.deepEqual(E.originPatterns('www.order.online'), ['https://order.online/*', 'https://*.order.online/*', 'http://order.online/*', 'http://*.order.online/*']);
  const granted = ['http://127.0.0.1/*', ...E.originPatterns('cvs.com')];
  assert.ok(E.isPermitted('www.cvs.com', granted) && E.isPermitted('shop.cvs.com', granted));
  assert.ok(!E.isPermitted('publix.com', granted) && !E.isPermitted('notcvs.com', granted));
  assert.deepEqual(E.permittedDomains(granted), ['cvs.com']);
  assert.ok(E.isLocal('127.0.0.1') && E.isLocal('http://127.0.0.1:8830/eklenti-deneme') && !E.isLocal('cvs.com'));
  assert.equal(E.domainOf('https://WWW.Publix.com/locations'), 'publix.com');
});

test('extension: wait rules are seconds or an element, with limits', () => {
  assert.deepEqual(E.normalizeWait({saniye: 5}), {seconds: 5, selector: null, maxSeconds: 60});
  assert.deepEqual(E.normalizeWait({oge: '#icerik'}), {seconds: 0, selector: '#icerik', maxSeconds: 60});
  assert.deepEqual(E.normalizeWait({saniye: 500}).seconds, 60);
  assert.deepEqual(E.normalizeWait(undefined), {seconds: 2, selector: null, maxSeconds: 60});
  assert.equal(E.bytesToBase64(new Uint8Array([104, 105])), 'aGk=');
});

test('Ayarlar → Tarayıcı eklentisi: yalnız eşleşme kodu ve bağlantı; siteler, hız ve denemeler Veri → Okuma denemeleri\'nde (GÖREV-21)', () => {
  const view = {eslesti: true, bagli: true, surum: '0.16.0', son_gorulme: '2026-10-10T20:00:00+00:00', kod: 'K7QM-3XRA', izinli_alan_adlari: ['cvs.com'],
    izin_bekleyen_alan_adlari: ['publix.com'], aralik_saniye: 8, aralik_sinirlari: [3, 120], kurulum: ['Bir', 'İki'], klasor: 'C:/30a-studio/eklenti',
    sorunlu_siteler: [{alan_adi: 'realjoy.com'}, {alan_adi: 'order.online'}]};
  assert.equal(connectionText(view).tone, 'green');
  assert.match(connectionText({...view, bagli: false}).text, /^Bağlı değil/);
  assert.match(connectionText({eslesti: false}).text, /^Eşleşmedi/);
  const settings = extensionSection(view);
  assert.match(settings, /id="extension-connection".*K7QM-3XRA.*Kodu yenile.*<li>Bir<\/li><li>İki<\/li>/s);
  assert.doesNotMatch(settings, /id="extension-trial"|id="extension-problems"|id="extension-speed"|İzin verilen siteler/);      // no data work in Ayarlar
  assert.match(settings, /<a href="#veri\/okuma">Veri → Okuma denemeleri<\/a>/);
  const html = extensionReading(view, {trial: {durum: 'tamam', baslik: 'Deneme', bayt: 2048, sha256: 'abc', dosya: 'raw/eklenti/x.html'}});
  assert.match(html, /cvs\.com.*publix\.com.*min="3" max="120" value="8".*id="extension-trial">Deneme.*okundu.*realjoy\.com, order\.online.*Sorunlu sitelerden birer sayfa dene/s);
  assert.doesNotMatch(html, /Kodu yenile|id="extension-code"/);
  assert.match(warmUpSection({siteler:[{alan_adi:'oversee.us',adres:'https://www.oversee.us/',sebep:'korumalı kiralama sitesi',ilk:null,son:null}]}), /Isınma listesi.*oversee\.us.*korumalı kiralama sitesi/s);
  assert.match(warmUpSection({siteler:[]}), /Listede site yok/);
  assert.match(trialRows([{alan_adi: 'cvs.com', durum: 'dogrulama', bayt: 4096, not: 'süre doldu'}]), /cvs\.com.*doğrulama geçilmedi.*4 KB.*süre doldu/s);
  assert.equal(trialRows([]), '');
});
import {runStatusTag, runView as runViewOf} from '../studio/web/videos.js';
test('GÖREV-15 1d: an evaluation without candidates is information, not "Onay bekliyor"',()=>{
  const run={id:'r1',step:'baslik_degerlendirme',status:'awaiting_approval',adaysiz:true,bilgi:'Değerlendirildi: veriyle dolmuyor',params:{bolge:'Rosemary Beach',kullanici_basligi:'köpek'},created_at:'2026-10-11T10:00:00Z'};
  assert.match(runStatusTag(run),/Değerlendirildi: veriyle dolmuyor/);
  assert.doesNotMatch(runStatusTag(run),/Havuzda/);
  assert.match(runStatusTag({...run,adaysiz:false}),/Havuzda/);
  assert.match(runStatusTag({...run,adaysiz:false,canceled:true,status:'error'}),/İptal edildi/);      // GÖREV-21: a canceled run says so
  const view={...run,candidates:[],actions:{select:true,reject:true,correct:true},review:{kullanici_fikri:'köpek',doluluk:{dolar_mi:false,eksik_veri:['x']},sorunlar:[]},summary:{}};
  const html=runViewOf(view,null);
  assert.match(html,/onay beklemiyor/);assert.match(html,/id="run-reject" class="quiet" >/);
});
import {toneRows, toneForm, archiveRows, warningsBox} from '../studio/web/tones.js';
import {toneChoice, planView, compareView, versionView, textBar} from '../studio/web/text.js';
import {textSettings, formValues as claudeFormValues} from '../studio/web/claude.js';

const TONES={tonlar:[{dosya:'arastirmaci_dost',ad:'Araştırmacı dost',ilk_satir:'Anlatıcı, 30A yı iyi tanıyan…',degisti:'2026-10-11T00:00:00+00:00',varsayilan:true,kullanim:2},
  {dosya:'vlogger',ad:'Vlogger',ilk_satir:'Anlatıcı, kameraya konuşan…',degisti:'2026-10-11T00:00:00+00:00',varsayilan:false,kullanim:0}],
  arsiv:[{id:'belgesel-20261011-000000-000000',dosya:'belgesel',ad:'Belgesel anlatıcı',ilk_satir:'Anlatıcı…',arsivlendi:'2026-10-11T00:00:00+00:00',kullanim:1}],
  uzun_metin:1200,en_cok:6000,ad_en_cok:40,uzun_not:'Ton metni uzun. Kısa ve niyet anlatan metinler genellikle daha iyi sonuç verir.'};

test('GÖREV-15 Tonlar: the list, the default, usage, delete and the archive',()=>{
  const html=toneRows(TONES);
  assert.match(html,/Araştırmacı dost/);assert.match(html,/<span class="tag green">varsayılan<\/span>/);
  assert.match(html,/data-tone-default="vlogger"/);assert.doesNotMatch(html,/data-tone-default="arastirmaci_dost"/);
  assert.match(html,/2 metin sürümü/);assert.match(html,/data-tone-delete="vlogger" >/);
  assert.match(toneRows({tonlar:[TONES.tonlar[0]]}),/data-tone-delete="arastirmaci_dost" disabled/);
  assert.match(archiveRows(TONES),/data-tone-unarchive="belgesel-20261011-000000-000000"/);
  assert.match(archiveRows({arsiv:[]}),/Arşivde ton yok/);
});
test('GÖREV-15 Tonlar: the new tone form, the long text note and the edit form with versions',()=>{
  const blank=toneForm({},TONES);
  assert.match(blank,/Yeni ton/);assert.match(blank,/id="tone-name"/);assert.match(blank,/maxlength="40"/);assert.match(blank,/id="tone-long" hidden/);
  const long=toneForm({ad:'Uzun',metin:'a'.repeat(1300)},TONES);
  assert.doesNotMatch(long,/id="tone-long" hidden/);assert.match(long,/Kısa ve niyet anlatan/);
  const edit=toneForm({dosya:'vlogger',ad:'Vlogger',metin:'x',sha256:'a'.repeat(64),surumler:[{id:'20261011-000000-000001',saklandi:'2026-10-11T00:00:00+00:00',ad:'Vlogger',ilk_satir:'eski'}]},TONES);
  assert.match(edit,/Tonu düzenle/);assert.match(edit,/data-tone-version="20261011-000000-000001"/);assert.match(edit,/Yeniden yükle/);
  assert.match(warningsBox({name:'uyari_ifadeleri.txt',sha256:'b'.repeat(64),modified_at:'2026-10-11T00:00:00+00:00',text:'amazing\nI\n',versions:[]}),/Denetim: uyarı ifadeleri/);
});

const OPTIONS={video:{id:'v1',title_en:'Deneme | 30A Florida Vacation'},tonlar:[{dosya:'arastirmaci_dost',ad:'Araştırmacı dost',ilk_cumle:'Anlatıcı, iyi tanıyan bir dost.',varsayilan:true},
  {dosya:'hikaye_anlaticisi',ad:'Hikâye anlatıcısı',ilk_cumle:'Anlatıcı, izleyiciyi tutan sesi.',varsayilan:false}],paket:{var:false,eski:false,metin:'Paket önce yeniden üretilecek (bu videonun paketi yok).'},
  calismalar:[],surumler:[],mesgul:false,claude_mesgul:false};
test('4 · Yazım: tone choice with the default ticked and "Tonları yönet" (Kanal → Tonlar)',()=>{
  const html=toneChoice(OPTIONS.tonlar,['arastirmaci_dost']);
  assert.match(html,/data-tone="arastirmaci_dost" checked/);assert.match(html,/data-tone="hikaye_anlaticisi" >/);
  assert.match(html,/Anlatıcı, iyi tanıyan bir dost\./);assert.match(html,/href="#kanal\/tonlar">Tonları yönet \(Kanal → Tonlar\)/);
  assert.match(toneChoice(OPTIONS.tonlar,[]),/varsayılan/);
});
test('3 · Plan: the plan in readable Turkish (sections, concepts, the promise check, the program\'s warnings, the critic\'s notes)',()=>{
  const plan=planView({plan:{bolumler:[{no:1,ic_adi:'Bir',tek_fikir:'Tek',en_carpici_an:'An',kanitlar:['K0001'],kelime_butcesi:350,acilis_bicimi:'gecmis',acilis_notu:'Not'}],
    kavramlar:[{kavram:'customary use',bolum:1}],yeniden_kancalar:[{bolumden_sonra:1,uzerine:'kanca'}],vaat_kontrolu:{karsilanan:[{vaat:'Soru',bolumler:[1]}],karsilanamayan:['Fiyat']},notlar:[]},
    plan_uyarilari:['1. ve 2. bölüm aynı biçimde açılıyor (soru).'],elestiri:{notlar:['Plan iyi.'],yeniden_yap:false},plan_turu:1});
  assert.match(plan,/geçmiş/);assert.match(plan,/customary use → 1\. bölüm/);assert.match(plan,/Karşılanamayan: Fiyat/);assert.match(plan,/aynı biçimde açılıyor/);assert.match(plan,/Plan iyi\./);
});
const COMPARE={sutunlar:[{id:'s1',number:1,tone_file:'arastirmaci_dost',tone_name:'Araştırmacı dost',words:2300,dakika:15.3,red:1,yellow:2,cost_usd:0.42,tokens:{input:1000,output:2000},elapsed_s:300,secili:false,ton_var:true,
    parcalar:{giris:{baslik:'Giriş',tr:['Merhaba.'],en:['Hello.'],isaretler:0},'bolum-1':{baslik:'1. Bir',tr:['Bir.'],en:['One.'],isaretler:1}}},
  {id:'s2',number:2,tone_file:'vlogger',tone_name:'Vlogger',words:2250,dakika:15,red:0,yellow:0,cost_usd:0.4,tokens:{},elapsed_s:280,secili:true,ton_var:false,
    parcalar:{giris:{baslik:'Giriş',tr:['Selam.'],en:['Hi.'],isaretler:0}}}],satirlar:['giris','bolum-1']};
test('5 · Kontrol ve ton seçimi: the comparison — columns, header numbers, Turkish first and the language switch; the tone is chosen in the approval component',()=>{
  const tr=compareView(COMPARE,'tr',id=>`#video/v1/yazim/surum/${id}`);
  assert.match(tr,/repeat\(2, minmax\(320px, 1fr\)\)/);assert.match(tr,/2\.300 kelime · ~15,3 dk/);assert.match(tr,/1 kırmızı/);assert.match(tr,/0,42 \$/);
  assert.match(tr,/<p>Merhaba\.<\/p>/);assert.doesNotMatch(tr,/<p>Hello\.<\/p>/);assert.match(tr,/<span class="tag green">seçili ton<\/span>/);
  assert.doesNotMatch(tr,/data-choose|Bu tonla devam et/);                          // GÖREV-21: no button of its own; "Onayla" picks the tone
  assert.match(tr,/href="#video\/v1\/yazim\/surum\/s1">Metnin tamamı/);
  assert.match(tr,/silinmiş ton/);assert.match(tr,/compare-cell empty/);assert.match(tr,/data-lang="tr" aria-pressed="true"/);
  const en=compareView(COMPARE,'en');assert.match(en,/<p>Hello\.<\/p>/);assert.doesNotMatch(en,/<p>Merhaba\.<\/p>/);
  const both=compareView(COMPARE,'both');assert.match(both,/<p>Merhaba\.<\/p><p class="en">Hello\.<\/p>/);
});
test('GÖREV-15 Video metni: a version — numbers, both languages, marks of the check, evidence on hover, terms and downloads',()=>{
  const html=versionView({id:'s1',number:1,tone_name:'Araştırmacı dost',tone_file:'arastirmaci_dost',text_run_id:'r1',words:2300,sentences:2,red:1,yellow:1,created_at:'2026-10-11T00:00:00+00:00',secili:false,
    not:'Türkçe düzeltme ve İngilizceye uyarlama bu görevde yok',denetim_md:'# Program denetimi',metin:{parcalar:[{kimlik:'bolum-1',baslik:'1. Bir',paragraflar:[{cumleler:[
      {no:1,en:'It is within walking distance.',tr:'Yürüme mesafesinde.',kanitlar:['K0001'],uyarilar:[{tur:'denetim',seviye:'kirmizi',kural:'mesafe',metin:'Mesafe kuralı.'}]},
      {no:2,en:'Amazing view.',tr:'Harika manzara.',kanitlar:[],uyarilar:[{tur:'denetim',seviye:'sari',kural:'ses',metin:'Uyarı ifadesi.'},{tur:'cevirmen',metin:'Belirsiz.'}]}]}]}],
      terimler:[{en:'walkover',tr:'walkover',aciklama:'Geçit.'}],surum_bilgisi:{ton:{ad:'Araştırmacı dost',dosya:'arastirmaci_dost',sha256:'c'.repeat(64)},oturumlar:[{}]}}});
  assert.match(html,/sentence-row has-red/);assert.match(html,/sentence-row has-yellow/);assert.match(html,/title="Kanıt: K0001"/);assert.match(html,/title="Kanıt işareti yok"/);
  assert.match(html,/sentence-mark red" title="Mesafe kuralı\."/);assert.match(html,/Çevirmen: Belirsiz\./);assert.match(html,/<strong>walkover<\/strong>/);
  assert.match(html,/dosya\/en" download>İngilizce/);assert.match(html,/dosya\/tr" download>Türkçe/);assert.match(html,/dosya\/seslendirme" download>Seslendirme/);
  assert.doesNotMatch(html,/data-choose/);assert.match(html,/Türkçe düzeltme ve İngilizceye uyarlama bu görevde yok/);
});
test('GÖREV-15 İşler: the text run bar — stage text, elapsed and remaining time, and the usage limit wait',()=>{
  const now=Date.parse('2026-10-11T10:10:00Z');
  const job={id:'j1',kind:'claude_metin',status:'running',progress:40,created_at:'2026-10-11T10:00:00Z',progress_info:{tur:'metin',yuzde:40,asama:'Araştırmacı dost (1/2 ton) · bölümler 4/6 bitti',baslangic:'2026-10-11T10:00:00Z',kalan_s:900,bekleme:null}};
  const html=textBar(job,now);
  assert.match(html,/aria-valuenow="40"/);assert.match(html,/%40 · Araştırmacı dost \(1\/2 ton\) · bölümler 4\/6 bitti · geçen 10 dk · tahmini kalan ~15 dk/);
  const waiting=textBar({...job,progress_info:{...job.progress_info,bekleme:{bitis:'2026-10-11T11:02:00Z',metin:'Claude kullanım sınırı: 14:02 te kendiliğinden sürecek.'}}},now);
  assert.match(waiting,/<span class="tag warm">Bekliyor<\/span> Claude kullanım sınırı: 14:02 te kendiliğinden sürecek\./);
  assert.match(textBar({...job,status:'done'},now),/aria-valuenow="100"/);
  assert.equal(textBar({...job,progress_info:{tur:'claude'}},now),"");
});
test('Ayarlar → Claude: sessions at once and the thresholds; "Plandan sonra dur" is gone (GÖREV-21)',()=>{
  const html=textSettings({claude_max_sessions:3,claude_limit_five_hour:90,claude_limit_week:95},
    {fields:[{field:'claude_max_sessions',min:1,max:6,default:3,help:'h'},{field:'claude_limit_five_hour',min:1,max:100,default:90,help:'h'},{field:'claude_limit_week',min:1,max:100,default:95,help:'h'}]});
  assert.match(html,/Aynı anda en çok Claude oturumu/);assert.match(html,/min="1" max="6" value="3"/);
  assert.doesNotMatch(html,/Plandan sonra dur|claude_stop_after_plan|type="checkbox"/);
  assert.match(html,/Yazım, plan onaylanmadan başlamaz/);
  const form={querySelectorAll:()=>[{dataset:{field:'claude_max_sessions'},type:'number',value:'4'}]};
  assert.deepEqual(claudeFormValues(form),{claude_max_sessions:4});
});

// GÖREV-16: the extension's page kinds (the same fixtures as the Python test), "Son iş", the trial table with kinds, "Eklenti çalışıyor",
// "Bu sayfayı atla", Settings → ABD proxy'si, and the video text's "seçildi" and plan usage.
import {skipButton} from '../studio/web/extension.js';
import {proxySection, proxyReading, testResult, regionRows} from '../studio/web/proxy.js';
import {usageText} from '../studio/web/text.js';

const KINDS_DIR=new URL('./fixtures/sayfa_turleri/', import.meta.url);
test('GÖREV-16 eklenti: the page kinds of the shared fixtures, as in page_kinds.py',()=>{
  const expected=JSON.parse(readFileSync(new URL('beklenen.json',KINDS_DIR),'utf8'));
  assert.ok(expected.length>=10);
  for(const c of expected) {
    const html=readFileSync(new URL(c.dosya,KINDS_DIR),'utf8');
    assert.equal(E.pageKind(html,c.baslik,c.adres,c.http),c.tur,c.dosya);
  }
  assert.equal(E.redirectKind('https://geo-blocked-site.dpxmedcity.net/'),'bolge_engeli');
  assert.equal(E.redirectKind('https://login.other.test/'),'yonlendi');
  assert.equal(E.isVerification('<title>Access Denied</title>','Access Denied'),false);          // "access denied" is not a verification any more
  assert.equal(E.classify({html:'<h1>Access Denied</h1>',title:'Access Denied',url:'https://x.test/',status:403}),'erisim_reddedildi');
  const region=E.pageResult('bolge_engeli',{url:'https://www.publix.com/',title:'International | Publix',html:'<p>x</p>'},E.stopNote('bolge_engeli'));
  assert.equal(region.html,'<p>x</p>');assert.match(region.not,/beklenmedi, atlandı/);
  assert.equal(E.stopNote('yonlendi',{url:'https://geo.other.test/a'}),'başka siteye yönlendi: geo.other.test');
  assert.equal(E.pageResult('yonlendi',{url:'https://a.test/'}).html,undefined);
});
test('GÖREV-16 eklenti: "Son iş" says the stage and when a job stopped moving',()=>{
  const now=Date.parse('2026-10-11T12:00:00Z');
  assert.equal(E.lastJobText(null),'Henüz iş yok.');
  assert.match(E.lastJobText({alan_adi:'cvs.com',amac:'deneme',durum:'çalışıyor',asama:'okunuyor',zaman:now-60000,ilerleme:now-20000},now),/^cvs\.com · deneme · sayfa okunuyor · son ilerleme az önce$/);
  assert.match(E.lastJobText({alan_adi:'cvs.com',amac:'deneme',durum:'çalışıyor',asama:'okunuyor',zaman:now-900000,ilerleme:now-600000},now),/takılmış görünüyor: 10 dk'dır ilerlemiyor \(son adım: sayfa okunuyor\)/);
  assert.match(E.lastJobText({alan_adi:'cvs.com',amac:'deneme',durum:'çalışıyor',asama:'dogrulama',zaman:now-900000,ilerleme:now-600000,bitis:now+300000},now),/doğrulama bekleniyor \(kalan 5 dk\)/);
  assert.match(E.lastJobText({alan_adi:'cvs.com',amac:'deneme',durum:'bitti',zaman:now},now),/cvs\.com · deneme · bitti/);
  assert.ok(E.REPORT_EVERY_MS<=5000);
});
test('GÖREV-16 Ayarlar → Tarayıcı eklentisi: "Eklenti çalışıyor", the old version and the trial table with kinds',()=>{
  const base={eslesti:true,bagli:true,surum:'0.18.0',son_gorulme:'2026-10-11T12:00:00+00:00'};
  assert.equal(connectionText({...base,calisiyor:'cvs.com · sayfa okunuyor'}).text,'Eklenti çalışıyor: cvs.com · sayfa okunuyor');
  assert.match(connectionText({...base,bagli:false}).text,/^Bağlı değil \(Chrome kapalı olabilir\)/);
  const view={...base,kod:'ABCD-EFGH',izinli_alan_adlari:[],izin_bekleyen_alan_adlari:[],aralik_saniye:8,aralik_sinirlari:[3,120],kurulum:[],klasor:'x',
    sorunlu_siteler:[{alan_adi:'cvs.com'}],eski_surum:true,beklenen_surum:'0.18.0',surum:'0.16.0'};
  assert.match(extensionSection(view),/eklenti eski sürüm \(0\.16\.0; programın klasöründeki 0\.18\.0\)/);
  assert.match(extensionSection(view),/id="extension-connection"/);
  const html=trialRows([{alan_adi:'publix.com',durum:'tamam',tur:'tamam',yontem:'proxy',bayt:2048},{alan_adi:'cvs.com',durum:'bolge_engeli',tur:'bolge_engeli',not:"bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)"},
    {alan_adi:'winndixie.com',durum:'erisim_reddedildi',tur:'erisim_reddedildi'},{alan_adi:'hca.test',durum:'yonlendi',tur:'yonlendi',not:'başka siteye yönlendi: geo.test'},
    {alan_adi:'order.online',durum:'dogrulama',tur:'dogrulama'}]);
  assert.match(html,/<th>TÜR<\/th>/);
  assert.match(html,/publix\.com.*>tamam<\/span><small class="source-host">proxy<\/small>/s);
  assert.match(html,/cvs\.com.*bölge engeli.*ABD proxy&#39;si tanımlı değil|cvs\.com.*bölge engeli.*ABD proxy'si tanımlı değil/s);
  assert.match(html,/erişim reddedildi/);assert.match(html,/başka siteye yönlendi/);assert.match(html,/doğrulama geçilmedi/);
  assert.equal(skipButton({id:'j1',progress_info:{tur:'eklenti'},waiting_for:'cvs.com'}),'<button data-skip-job="j1">Bu sayfayı atla</button> ');
  assert.equal(skipButton({id:'j1',progress_info:{tur:'eklenti'},waiting_for:''}),'');
  assert.equal(skipButton({id:'j1',progress_info:{tur:'claude'},waiting_for:'x'}),'');
});
test('Ayarlar → ABD proxy\'si: yalnız bağlantı bilgileri ve parolanın kasada olup olmadığı; deneme ve liste Veri → Okuma denemeleri\'nde (GÖREV-21)',()=>{
  const empty=proxySection({adres:'',kullanici:'',parola_kayitli:false,tanimli:false,notlar:[],bolge_engelli:[]});
  assert.match(empty,/ABD proxy'si \(bölge engeli için\)/);assert.match(empty,/<span class="tag">kasada yok<\/span>/);
  assert.doesNotMatch(empty,/id="proxy-test"|id="region-form"|Bölge engelli alan adları<\/h3>/);          // no data work in Ayarlar
  assert.match(empty,/<a href="#veri\/okuma">Veri → Okuma denemeleri<\/a>/);
  const view={adres:'http://proxy.example:8080',kullanici:'abd',parola_kayitli:true,tanimli:true,notlar:["Chrome, kullanıcı adı ve parola isteyen SOCKS5 proxy'yi desteklemiyor"],
    bolge_engelli:[{host:'cvs.com',title:null,evidence:'CVS.com is not available outside of the United States',added_by:'program',first_seen_at:'2026-10-11T11:34:14+00:00',last_seen_at:'2026-10-11T11:34:14+00:00',url:'https://www.cvs.com/x'},
      {host:'winndixie.com',added_by:'kullanici',first_seen_at:'2026-10-11T12:00:00+00:00',last_seen_at:'2026-10-11T12:00:00+00:00'}]};
  const saved=proxySection(view);
  assert.match(saved,/<span class="tag green">kasada kayıtlı<\/span>/);assert.match(saved,/placeholder="kayıtlı \(değiştirmek için yazın\)"/);
  assert.match(saved,/id="proxy-password" type="password"/);assert.doesNotMatch(saved,/id="proxy-password"[^>]*value=/);
  assert.match(saved,/id="proxy-forget"/);assert.match(saved,/SOCKS5 proxy&#39;yi desteklemiyor/);assert.doesNotMatch(saved,/data-region-remove/);
  const reading=proxyReading(view);
  assert.match(reading,/id="proxy-test">Proxy'yi dene/);assert.match(reading,/bot korumasını, hız sınırını ya da yasağı aşmak için kullanılmaz/);
  assert.match(reading,/data-region-remove="cvs.com"/);assert.match(reading,/<td>program<\/td>/);assert.match(reading,/<td>siz<\/td>/);assert.match(reading,/outside of the United States/);
  assert.doesNotMatch(reading,/id="proxy-password"|id="proxy-form"/);
  assert.match(proxyReading({...view,tanimli:false,bolge_engelli:[]}),/id="proxy-test" disabled>.*Listede alan adı yok\./s);
  const ok=testResult({ok:true,ip:'203.0.113.7',ulke:'US',uyari:null,satirlar:['Proxy: http://proxy.example (kullanıcı adıyla)','Çıkış adresi 203.0.113.7, ülke US.']});
  assert.match(ok,/tag green">Çıkış adresi 203\.0\.113\.7 · ülke US/);assert.doesNotMatch(ok,/ABD'de görünmüyor/);
  const tr=testResult({ok:true,ip:'198.51.100.2',ulke:'TR',uyari:"Proxy'nin çıkış adresi ABD'de görünmüyor",satirlar:[]});
  assert.match(tr,/tag warm">Çıkış adresi 198\.51\.100\.2 · ülke TR/);assert.match(tr,/claude-warning">Proxy&#39;nin çıkış adresi ABD&#39;de görünmüyor\./);
  assert.match(testResult({error:"ABD proxy'si tanımlı değil"}),/claude-warning/);assert.equal(testResult(null),'');
  assert.match(regionRows([]),/Listede alan adı yok/);
});
test('GÖREV-16 Video metni: the usage text and the plan usage above the comparison',()=>{
  assert.equal(usageText({oturum:2,sure_s:60,token:20000,maliyet_usd:0.1}),'2 oturum · 1 dk · 20 bin token · 0,10 $');
  const compare=compareView({...COMPARE,planlar:[{metin_calismasi:'r1',surumler:[1,2],kullanim:{oturum:2,sure_s:60,token:20000,maliyet_usd:0.1}}]},'tr');
  assert.match(compare,/Planın kullanımı \(bütün tonlar için bir kez\): <span class="tag">plan: 2 oturum/);
  assert.match(compare,/title="Yalnız bu tonun oturumları; planın kullanımı yukarıda"/);
  assert.match(compareView({...COMPARE,planlar:[{surumler:[1],kullanim:{oturum:2,sure_s:60,token:1,maliyet_usd:0.1}},{surumler:[2],kullanim:{oturum:2,sure_s:60,token:1,maliyet_usd:0.1}}]},'tr'),/plan \(1\. sürüm\)/);
});

// ---- GÖREV-17: the job panel (hiding finished jobs), the Settings layout, one window for a job, the proxy words ----
import {jobsPanel, jobCard, panelHead, hiddenSection, visibleJobs, removableJobs, windowLines, emptyPanel} from '../studio/web/jobs.js';
import {SECTIONS, CHANNEL_SECTIONS, channelFrame, channelSectionOfHash, sectionOfHash, isSettingsHash, sectionId, settingsHref, settingsNav, sectionCard, settingsFrame, folderCard, aboutCard, usageCard, linkSettingsMentions} from '../studio/web/settings.js';
import {kindText} from '../studio/web/extension.js';
import {tonesHtml} from '../studio/web/tones.js';

const job17=(id,status,extra={})=>({id,kind:'eklenti_deneme',title:`İş ${id}`,status,progress:status==='done'?100:40,message:'mesaj',created_at:'2026-11-11T10:00:00Z',
  log:[{at:'2026-11-11T10:00:01Z',text:'satır 1'},{at:'2026-11-11T10:00:02Z',text:'satır 2'}],hidden_at:null,awaiting_approval:0,progress_info:null,waiting_for:null,...extra});

test('GÖREV-17 İşler: a finished job has "Kaldır", a running one does not; the log comes closed',()=>{
  const done=jobCard(job17('d1','done'));
  assert.match(done,/data-job="d1"/);assert.match(done,/data-hide-job="d1"[^>]*>Kaldır<\/button>/);assert.doesNotMatch(done,/data-cancel-job/);
  assert.match(done,/<details><summary>İş günlüğü \(2\)<\/summary>/);assert.doesNotMatch(done,/<details open/);
  for(const status of ['failed','canceled','interrupted']) assert.match(jobCard(job17('x',status)),/data-hide-job="x"/);
  for(const status of ['running','queued']) {
    const card=jobCard(job17('r1',status));
    assert.doesNotMatch(card,/data-hide-job/);assert.match(card,/data-cancel-job="r1">İptal et/);
  }
  assert.match(jobCard(job17('a1','done',{awaiting_approval:1})),/Onay bekliyor.*data-hide-job="a1"/s);
  assert.match(jobCard(job17('w1','running',{waiting_for:'cvs.com'})),/Kullanıcı doğrulaması bekleniyor<\/span> cvs\.com/);
});

test('GÖREV-17 İşler: "Bitenleri kaldır" counts only finished jobs on the panel; hidden jobs leave it and are listed at the bottom',()=>{
  const jobs=[job17('r1','running'),job17('q1','queued'),job17('d1','done'),job17('f1','failed'),job17('c1','canceled'),
    job17('a1','done',{awaiting_approval:1}),job17('h1','done',{hidden_at:'2026-11-11T11:00:00Z'})];
  assert.deepEqual(visibleJobs(jobs).map(j=>j.id),['r1','q1','d1','f1','c1','a1']);
  assert.deepEqual(removableJobs(jobs).map(j=>j.id),['d1','f1','c1']);            // not the running, queued, awaiting or hidden ones
  assert.match(panelHead(jobs),/data-hide-finished\s+title="[^"]*silinmez[^"]*">Bitenleri kaldır \(3\)</);
  assert.match(panelHead([job17('r1','running')]),/data-hide-finished disabled/);
  const hidden=[{id:'h1',title:'Gizli <iş>',status:'done',created_at:'2026-09-20T10:00:00Z',log_count:1480}];
  const panel=jobsPanel(jobs,hidden,{open:false});
  assert.ok(panel.indexOf('data-hide-finished')<panel.indexOf('data-job="r1"'));    // the button is at the head of the panel
  assert.doesNotMatch(panel,/data-job="h1"/);
  assert.match(panel,/data-toggle-hidden aria-expanded="false">Gizlenen işleri göster \(1\)</);assert.doesNotMatch(panel,/data-unhide-job/);
  const opened=jobsPanel(jobs,hidden,{open:true});
  assert.ok(opened.indexOf('data-toggle-hidden')>opened.indexOf('data-job="a1"'));  // at the bottom
  assert.match(opened,/Gizli &lt;iş&gt;.*günlük 1480 satır.*data-unhide-job="h1">Geri getir<.*silinmedi/s);
  assert.equal(hiddenSection([],true),'');
  assert.match(jobsPanel([job17('h1','done',{hidden_at:'x'})],hidden),/Panelde iş yok.*Gizlenen işleri göster \(1\)/s);
  assert.match(emptyPanel(0),/Henüz iş yok/);
  assert.match(jobsPanel(jobs,[],{resultLink:job=>job.id==='d1'?'<a class="return-link">Aç →</a>':''}),/data-job="d1".*Aç →/s);
});

test('GÖREV-17 İşler: a running job names the browser window that is open for it',()=>{
  const ext=job17('e1','running',{progress_info:{tur:'eklenti',bekliyor:false,asama:'realjoy.com · sayfa okunuyor',pencereler:{proxy:'cvs.com okunuyor'}}});
  assert.deepEqual(windowLines(ext),['Eklentinin penceresi: realjoy.com · sayfa okunuyor','Programın proxy tarayıcısı: cvs.com okunuyor']);
  assert.match(jobCard(ext),/Açık pencere<\/span> Eklentinin penceresi: realjoy\.com · sayfa okunuyor/);
  assert.deepEqual(windowLines(job17('p1','running',{progress_info:{pencereler:{program:'oversee.us okunuyor'}}})),['Programın tarayıcısı: oversee.us okunuyor']);
  assert.deepEqual(windowLines({...ext,status:'done'}),[]);                          // a finished job has no open window
  assert.deepEqual(windowLines(job17('h1','running',{progress_info:{tur:'eklenti',devredildi:true,asama:'x'}})),[]);
  assert.deepEqual(windowLines(job17('b1','running',{progress_info:{tur:'eklenti',bekliyor:true}})),[]);
});

const view17={
  claude:{settings:{claude_path:'',claude_model:'',claude_effort:''},notes:[],info:{found:true,path:'c',version:'1'},
    options:{models:[{value:'',label:'v'}],efforts:[{value:'',label:'o'}],inherit:{value:'inherit',label:'Genel varsayılan'},steps:[],output_guess:{min:500,max:128000,help:'Ç'},limits:[]}},
  suffix:{en:' | A',tr:' | B',defaults:{en:' | A',tr:' | B'}},
  usage:{refresh:{text:'Kullanım birkaç dakikada bir yenilenir.',model:'haiku',effort:'low'}},
  instructions:{files:[{key:'ortak',name:'ortak.md',kind:'talimat'}],file:{key:'ortak',name:'ortak.md',title:'Ortak',sha256:'1234567890ab',modified_at:'2026-10-10T18:00:00+00:00',size:1024,text:'x',versions:[]},message:'',viewing:null},
  warnings:{name:'uyari_ifadeleri.txt',sha256:'b'.repeat(64),modified_at:'2026-10-11T00:00:00+00:00',text:'amazing\n',versions:[]},
  extension:{eslesti:true,bagli:true,surum:'0.19.0',son_gorulme:'2026-11-11T12:00:00+00:00',kod:'ABCD-EFGH',izinli_alan_adlari:[],izin_bekleyen_alan_adlari:[],aralik_saniye:8,aralik_sinirlari:[3,120],kurulum:[],klasor:'x',sorunlu_siteler:[{alan_adi:'cvs.com'}]},
  proxy:{adres:'',kullanici:'',parola_kayitli:false,tanimli:false,notlar:[],bolge_engelli:[]},
};
// each section's own module draws it; `main` is the text of its main button (or, where it has none, its main line)
const sectionHtml17={
  'klasor':[folderCard('C:/veri/30a'),/class="path">C:\/veri\/30a</],
  'claude':[claudeSection(view17.claude),/<button class="primary" type="submit">Claude ayarlarını kaydet<\/button>/],
  'kullanim':[usageCard(view17.usage),/usage-settings-text">Kullanım birkaç dakikada bir yenilenir\./],
  'eklenti':[extensionSection(view17.extension),/id="extension-renew" class="quiet">Kodu yenile</],
  'proxy':[proxySection(view17.proxy),/<button type="submit" class="primary">Kaydet<\/button>/],
  'hakkinda':[aboutCard('0.19.0'),/about-version">SÜRÜM 0\.19\.0</],
};

test('GÖREV-17 Ayarlar: a button for every section; the address names the section',()=>{
  // GÖREV-21: only the program's settings are left — no content rule of the channel, no data work
  assert.deepEqual(SECTIONS.map(s=>s.slug),['klasor','claude','kullanim','eklenti','proxy','hakkinda']);
  assert.deepEqual(SECTIONS.map(s=>s.title),['Kayıt klasörü','Claude','Claude kullanımı','Tarayıcı eklentisi',"ABD proxy'si",'Hakkında']);
  for(const moved of ['talimatlar','tonlar','uyari-ifadeleri','baslik-eki']) assert.equal(sectionOfHash(`#settings/${moved}`),null,moved);
  assert.deepEqual(Object.keys(sectionHtml17),SECTIONS.map(s=>s.slug));
  const nav=settingsNav('claude');
  for(const section of SECTIONS) {
    assert.ok(nav.includes(`href="#settings/${section.slug}" data-settings-section="${section.slug}"`),section.slug);
    assert.ok(nav.includes(`</span> ${section.title.replace("'","&#39;")}</a>`),section.title);
    assert.equal(sectionOfHash(`#settings/${section.slug}`),section.slug);
    assert.equal(sectionOfHash(`#ayarlar/${section.slug}`),section.slug);          // the Turkish address opens the same section
    assert.equal(settingsHref(section.slug),`#settings/${section.slug}`);
  }
  assert.equal((nav.match(/class="section-nav-item active"/g)||[]).length,1);
  assert.match(nav,/class="section-nav-item active" href="#settings\/claude"[^>]*aria-current="true"/);
  assert.equal(sectionOfHash('#settings'),null);assert.equal(sectionOfHash('#settings/yok'),null);assert.equal(sectionOfHash('#collect/weather'),null);
  assert.ok(isSettingsHash('#settings') && isSettingsHash('#settings/proxy') && isSettingsHash('#ayarlar') && !isSettingsHash('#sources') && !isSettingsHash(''));
});

for(const section of SECTIONS) {
  test(`GÖREV-17 Ayarlar → ${section.title}: the button goes to its card and the section's main button is there`,()=>{
    const [inner,main]=sectionHtml17[section.slug];
    const frame=settingsFrame('C:/veri/30a','0.19.0',section.slug);
    // the button's address and the card's anchor are the same section
    assert.ok(frame.includes(`href="#settings/${section.slug}"`));
    assert.equal((frame.match(new RegExp(`id="${sectionId(section.slug)}"`,'g'))||[]).length,1);
    const card=sectionCard(section.slug,inner);
    assert.match(card,new RegExp(`^<section class="settings-section" id="ayar-${section.slug}" data-section="${section.slug}"`));
    assert.ok(card.includes(`--section-icon:'${section.icon}'`));                    // the card's title carries the section's icon
    assert.match(card,/<h2[ >]/);                                                    // every section is a card with its own title
    assert.match(card,main);                                                         // the main button (save, trial) is drawn as before
  });
}

test('GÖREV-17 Ayarlar: the frame keeps every slot the section modules draw into, in the order of the buttons',()=>{
  const frame=settingsFrame('C:/veri/30a','0.19.0');
  const slots=['claude-settings-slot','usage-settings-slot','extension-slot','proxy-slot'];
  for(const gone of ['suffix-settings-slot','instructions-slot','tones-slot','warnings-slot']) assert.ok(!frame.includes(`id="${gone}"`),gone);      // GÖREV-21: these are on the Kanal screen
  let last=-1;
  for(const slot of slots) {const at=frame.indexOf(`id="${slot}"`);assert.ok(at>last,slot);last=at;}
  assert.ok(frame.indexOf('id="settings-nav-bar"')<frame.indexOf('id="ayar-klasor"'));
  assert.match(frame,/^<div id="settings-screen">/);
  const order=SECTIONS.map(s=>frame.indexOf(`id="ayar-${s.slug}"`));
  assert.deepEqual([...order].sort((a,b)=>a-b),order);
});

// the Kanal screen's sections are drawn by the same modules as before (GÖREV-21: they were Settings sections)
const channelHtml21={
  'talimatlar':[editorHtml(view17.instructions),/id="instruction-save">Kaydet</],
  'tonlar':[tonesHtml({list:TONES,form:{},message:''}),/<button class="primary" type="submit">Tonu ekle<\/button>/],
  'uyari-ifadeleri':[warningsBox(view17.warnings),/id="warnings-save">Kaydet</],
  'baslik-eki':[suffixSection(view17.suffix),/<button class="primary" type="submit">Başlık ekini kaydet<\/button>/],
};
for(const section of CHANNEL_SECTIONS) {
  test(`GÖREV-21 Kanal → ${section.title}: the section's card and its main button are on the Kanal screen`,()=>{
    const [inner,main]=channelHtml21[section.slug];
    const card=sectionCard(section.slug,inner,CHANNEL_SECTIONS);
    assert.match(card,new RegExp(`^<section class="settings-section" id="ayar-${section.slug}" data-section="${section.slug}"`));
    assert.match(card,main);
    assert.ok(channelFrame().includes(`href="#kanal/${section.slug}"`));
  });
}

test('GÖREV-17/21: links on other screens open the section itself, in the layer it lives in now',()=>{
  assert.match(toneChoice(OPTIONS.tonlar,[]),/href="#kanal\/tonlar">Tonları yönet/);
  assert.match(warnings({...titleOptions,claude:{found:false}}),/<a href="#settings\/claude">Ayarlar → Claude<\/a> bölümünden/);
  assert.match(extensionReading(view17.extension),/<a href="#settings\/eklenti">Ayarlar → Tarayıcı eklentisi<\/a>/);
  assert.match(proxyReading(view17.proxy),/<a href="#settings\/proxy">Ayarlar → ABD proxy'si<\/a>/);
  assert.match(trialRows([{alan_adi:'cvs.com',durum:'bolge_engeli',tur:'bolge_engeli',not:"bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)"}]),/tanımlı değil \(<a href="#settings\/proxy">Ayarlar → ABD proxy'si<\/a>\)/);
  assert.equal(linkSettingsMentions('Eşleşme kodu geçersiz; Ayarlar → Tarayıcı eklentisi ekranındaki kodu yazın.'),
    'Eşleşme kodu geçersiz; <a href="#settings/eklenti">Ayarlar → Tarayıcı eklentisi</a> ekranındaki kodu yazın.');
  // a text that still says "Ayarlar → Tonlar" is led to where the tones are now
  assert.equal(linkSettingsMentions('Tonu Ayarlar → Tonlar ekranından geri alın.'),'Tonu <a href="#kanal/tonlar">Kanal → Tonlar</a> ekranından geri alın.');
  assert.equal(linkSettingsMentions('Kanal → Talimatlar'),'<a href="#kanal/talimatlar">Kanal → Talimatlar</a>');
  assert.match(jobCard(job17('c1','failed',{message:"Ayarlar → Claude'dan tur sınırını artırın <b>"})),/<a href="#settings\/claude">Ayarlar → Claude<\/a>&#39;dan tur sınırını artırın &lt;b&gt;/);
  assert.equal(linkSettingsMentions('düz metin'),'düz metin');
});

test('GÖREV-17 Ayarlar: the sidebar has one Settings item; an address change inside Settings does not draw the screen again',()=>{
  const index=readFileSync(new URL('../studio/web/index.html',import.meta.url),'utf8');
  assert.match(index,/<nav class="nav-footer" aria-label="Ayarlar"><a href="#settings" id="settings-nav"[^>]*><span class="step-no tool-no" aria-hidden="true">⚙<\/span><span class="nav-title">Ayarlar<\/span><\/a><\/nav>/);
  assert.equal((index.match(/href="#settings"/g)||[]).length,1);assert.doesNotMatch(index,/class="settings-link"/);
  assert.ok(index.indexOf('id="usage-panel"')<index.indexOf('id="settings-nav"'));       // the usage box stays where it was, above it
  assert.doesNotMatch(index,/Yardım/);                                                   // the program has no help screen; none is invented
  const app=readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
  assert.match(app,/if\(!document\.getElementById\("settings-screen"\)\) renderSettings\(\);\s*else if\(location\.hash!==lastSettingsHash\) goToSettingsSection\(sectionOfHash\(location\.hash\)\);/);
  assert.match(app,/settings\.classList\.toggle\("active",state\.page==="settings"\)/);
  const css=readFileSync(new URL('../studio/web/style.css',import.meta.url),'utf8');
  const block=css.slice(css.indexOf('/* GÖREV-17'));
  assert.ok(block.length>500);assert.doesNotMatch(block,/#[0-9a-fA-F]{3,8}\b/);          // colours only from the variables
  assert.match(block,/\.nav-footer a\.active::before\{[^}]*background:var\(--accent\)/);assert.match(block,/\.settings-section \.info-card>h2::before\{content:var\(--section-icon\)/);
});

test('GÖREV-17 deneme tablosu: a region-blocked site says how it ended',()=>{
  assert.equal(kindText({tur:'bolge_engeli',durum:'tamam',proxy:true}),"bölge engeli · proxy'yle okundu");
  assert.equal(kindText({tur:'bolge_engeli',durum:'bolge_engeli',not:"bölge engeli: proxy'yle de okunamadı (HTTP 403)"}),"bölge engeli · proxy'yle de okunamadı");
  assert.equal(kindText({tur:'bolge_engeli',durum:'bolge_engeli',not:"bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)"}),"bölge engeli · ABD proxy'si tanımlı değil");
  assert.equal(kindText({tur:'bolge_engeli',durum:'bolge_engeli'}),'bölge engeli');assert.equal(kindText({durum:'tamam'}),'tamam');
  const html=trialRows([{alan_adi:'publix.com',durum:'tamam',tur:'bolge_engeli',proxy:true,yontem:'proxy',bayt:2048}]);
  assert.match(html,/<span class="tag green">bölge engeli · proxy&#39;yle okundu<\/span><small class="source-host">proxy<\/small>.*<span class="tag green">okundu</s);
});

test('GÖREV-17 eşleşme kodu: the screen shows a renewed code at once and refreshes a code changed elsewhere',()=>{
  const source=readFileSync(new URL('../studio/web/extension.js',import.meta.url),'utf8');
  assert.match(source,/if\(ticket!==this\.sequence\) return;/);                           // an older answer cannot bring the old code back
  assert.match(source,/const code=this\.container\.querySelector\("#extension-code"\);[^\n]*\n\s*if\(code && code\.textContent!==this\.view\.kod\) code\.textContent=this\.view\.kod;/);
  assert.match(source,/async renew\(\) \{[\s\S]*?this\.sequence\+\+;[\s\S]*?kod-yenile[\s\S]*?this\.sequence\+\+;\s*this\.draw\(\);/);
  assert.match(source,/setInterval\(\(\)=>this\.refresh\(\),5000\)/);
});

test('GÖREV-17 eklenti: one window for a job, opened without the focus and not minimized',()=>{
  assert.deepEqual({...E.WINDOW_OPTIONS},{url:'about:blank',focused:false,type:'normal',width:1280,height:900});
  assert.equal(E.windowKey({id:'s1',pencere:'job-7'}),'job-7');assert.equal(E.windowKey({id:'s1'}),'s1');assert.equal(E.windowKey(null),'');
  assert.equal(E.keepWindow('job-7',['job-7','job-8']),true);
  assert.equal(E.keepWindow('job-7',[]),false);                    // the job ended or was cancelled
  assert.equal(E.keepWindow('job-7',undefined),false);             // an older program: the window closes after each piece of work
  assert.equal(E.keepWindow('',['']),false);
});
// --- GÖREV-18: the estimate before a job, estimate beside actual, title marks, business names, the usage box, the About card ------------
import {estimateBox as estimateBox18, spendingLine as spendingLine18, tokens as tokens18} from '../studio/web/estimate.js';
import {markList as markList18, metricsText as metricsText18} from '../studio/web/videos.js';
import {businessBox as businessBox18} from '../studio/web/tones.js';
import {usageHtml as usageHtml18} from '../studio/web/usage.js';
import {jobCard as jobCard18} from '../studio/web/jobs.js';
import {aboutCard as aboutCard18, spendingTable as spendingTable18} from '../studio/web/settings.js';

const estimate18={satirlar:[{baslik:'Plan',cagri:2,okunan:70000,yazilan:26000,toplam:96000,en_buyuk_cagri:60000,modeller:[{adim:'metin_plan',model_adi:'Opus (en yeni sürüm)',efor_adi:'Yüksek'}]},
  {baslik:'Araştırmacı dost',cagri:10,okunan:150000,yazilan:70000,toplam:220000,en_buyuk_cagri:40000,modeller:[{adim:'metin_bolum',model_adi:'Opus (en yeni sürüm)',efor_adi:'Yüksek'},{adim:'metin_ceviri',model_adi:'Sonnet (en yeni sürüm)',efor_adi:'Orta'}]}],
  toplam:{cagri:12,okunan:220000,yazilan:96000,toplam:316000},sinirlar:{cagri:250000,is:1500000},asiyor:[],baslatilabilir:true,
  metin:'Plan: 2 çağrı, yaklaşık 96 bin token · Araştırmacı dost: 10 çağrı, yaklaşık 220 bin token · Toplam: yaklaşık 316 bin token'};

test('GÖREV-18 tahmin: lines per part, the total, models, the limits and Başlat; over a limit there is no Başlat', () => {
  const box=estimateBox18(estimate18,{id:'text-estimate',startLabel:'Metni yaz: başlat'});
  assert.match(box,/Başlamadan önce: tahmin/);
  assert.match(box,/Plan: 2 çağrı, yaklaşık 96 bin token · Araştırmacı dost: 10 çağrı/);
  assert.match(box,/<td>Araştırmacı dost<\/td><td>10<\/td><td>150 bin<\/td><td>70 bin<\/td>.*Opus \(en yeni sürüm\) · Yüksek; Sonnet \(en yeni sürüm\) · Orta/s);
  assert.match(box,/<tfoot><tr><td>Toplam<\/td><td>12<\/td>.*316 bin/s);
  assert.match(box,/tek çağrı 250 bin, iş başına 1,5 milyon token/);
  assert.match(box,/data-estimate-start>Metni yaz: başlat<\/button>/);
  const over=estimateBox18({...estimate18,baslatilabilir:false,asiyor:['İşin toplam tahmini yaklaşık 2 milyon token; iş başına sınır 1,5 milyon.']});
  assert.doesNotMatch(over,/data-estimate-start/);
  assert.match(over,/problem-error">İşin toplam tahmini yaklaşık 2 milyon token/);
  assert.match(over,/Tahmin bir sınırı aşıyor; iş başlatılmaz/);
  assert.equal(tokens18(1200000),'1,2 milyon');assert.equal(tokens18(85400),'85 bin');assert.equal(tokens18(800),'800');
});

test('GÖREV-18 harcama: estimate beside actual on the job card; the red warning over 1.5 × the estimate', () => {
  const fine={tahmin:{toplam:90000},gercek:{toplam:85000,cagri:1},karsilastirma:{fazla:false,uyari:null}};
  assert.match(spendingLine18(fine),/Harcama<\/span> tahmin 90 bin · gerçek 85 bin token \(1 çağrı\)/);
  assert.doesNotMatch(spendingLine18(fine),/Beklenenden fazla/);
  const over={tahmin:316000,gercek:{toplam:602000,cagri:12},karsilastirma:{fazla:true,uyari:'Beklenenden fazla harcandı: tahmin 316 bin, gerçek 602 bin token.'}};
  assert.match(spendingLine18(over),/spend-line over/);
  assert.match(spendingLine18(over),/tag error">Beklenenden fazla<\/span> Beklenenden fazla harcandı: tahmin 316 bin, gerçek 602 bin token\./);
  const job={id:'j1',kind:'claude_metin',status:'done',title:'Video metni',created_at:'2026-11-11T10:00:00+00:00',progress:100,log:[],result:{harcama:over}};
  assert.match(jobCard18(job),/Beklenenden fazla harcandı/);
  assert.equal(spendingLine18(null),'');
});

test('GÖREV-18 kullanım kutusu: the last job’s actual spending, red when over', () => {
  const view={measured:false,son_is:{baslik:'Claude · Başlık',gercek:{toplam:602000},karsilastirma:{tahmin:316000,fazla:true}}};
  assert.match(usageHtml18(view),/Son iş: 602 bin token · tahmin 316 bin <span class="tag error">fazla<\/span>/);
  assert.doesNotMatch(usageHtml18({measured:false}),/Son iş/);
});

test('GÖREV-18 başlık işaretleri and the call count of a run (old runs keep their turns)', () => {
  const marks=markList18([{seviye:'kirmizi',kod:'isletme',metin:'İngilizce başlıkta işletme adı: Modica Market'},{seviye:'sari',kod:'ilk_40',metin:'Telefonda yalnız ilk yaklaşık 40 karakter görünür; konu orada olmalı'}]);
  assert.match(marks,/mark-red.*İngilizce başlıkta işletme adı: Modica Market.*mark-yellow.*Telefonda yalnız ilk yaklaşık 40 karakter/s);
  assert.equal(markList18([]),'');
  assert.match(metricsText18({metrics:{duzen:'tek_cagri',cagri:2,elapsed_s:61}}),/^2 çağrı · 61 sn/);
  assert.match(metricsText18({metrics:{turns:6,elapsed_s:78}}),/^6 tur \(eski düzen\)/);
});

test('GÖREV-18 Ayarlar: business names beside the warning phrases, the spending table, the About card', () => {
  const box=businessBox18({name:'isletme_adlari.txt',sha256:'c'.repeat(64),modified_at:'2026-11-11T00:00:00+00:00',text:'+ Örnek Kafe\n'},{sayi:2,adlar:['Modica Market','Target']});
  assert.match(box,/İşletme adları: ekle \/ hariç tut/);
  assert.match(box,/Şu an veriden kurulan liste: 2 ad — Modica Market · Target/);
  assert.match(box,/id="business-save">Kaydet</);
  const table=spendingTable18([{adim:'baslik',baslik:'Konu ve başlık',yeni:{sayi:2,ortanca:120000,en_yuksek:140000,okunan_ortanca:90000,yazilan_ortanca:30000},eski:{sayi:3,ortanca:460000,en_yuksek:470000}}]);
  assert.match(table,/Adım başına harcama.*<td>Konu ve başlık<\/td><td>120 bin · en çok 140 bin \(2\)<\/td><td>90 bin \/ 30 bin<\/td><td>460 bin · en çok 470 bin \(3\)<\/td>/s);
  const about=aboutCard18('0.20.0');
  assert.doesNotMatch(about,/Sonraki aşama<\/span><p style="margin-top:12px">Claude ile video metni/);
  assert.match(about,/video metni, Türkçe karşılığı ve programın denetimi kullanılabilir/);
});

// --- GÖREV-20: road distances, airport fares, new companies in the estimate ------------------------------------------------------
import {roadCell, checkLine, speedList, Transport} from '../studio/web/transport.js';
test('road cell shows road miles with estimated minutes and the great-circle value under it',()=>{
  const cell=roadCell({count:113,road_median_mi:3.13,minutes_median:5.8,crow_median_mi:2.35,within_1mi_share:0.042});
  assert.match(cell,/<strong>3,13 mil · 6 dk<\/strong><small>kuş uçuşu 2,35 mil · 1 yol mili içinde %4<\/small>/);
  assert.equal(roadCell({count:0}),'<span class="muted">—</span>');assert.equal(roadCell(undefined),'<span class="muted">—</span>');
  assert.match(roadCell({count:5,road_median_mi:0.2,minutes_median:0.4,crow_median_mi:0.1,within_1mi_share:1}),/· 1 dk/);   // under a minute is written as 1
  assert.ok(!roadCell({count:7,road_median_mi:45.2,minutes_median:57.3},false).includes('kuş uçuşu'));                      // airports: no straight line
});
test('length check and default speeds are shown as the run stored them',()=>{
  assert.equal(checkLine({label:'CR 30A',osm_miles:19.057,expected_miles:18.561,difference_percent:2.7,source:'FDOT'}),'CR 30A: OpenStreetMap 19,057 mil · FDOT 18,561 mil · fark %2,7');
  assert.match(checkLine({label:'<b>',difference_percent:null}),/&lt;b&gt;: OpenStreetMap'te bu adla yol bulunamadı/);
  assert.equal(speedList({trunk:55,service:10}),'trunk 55 · service 10');
});
test('transport section offers both collectors, names missing runs and draws the fare table',()=>{
  const sources=[{id:'s1',enabled:1,destination_id:'30a',connector:{name:'openstreetmap-road-network'}},{id:'s2',enabled:1,destination_id:'30a',connector:{name:'bts-airport-fares'}}];
  const target={innerHTML:'',querySelector(){return null;}};
  new Transport().render(target,{sources,jobs:[{source_id:'s1',status:'running',destination_id:'30a'}],road_runs:[],airfare_runs:[],selected_destination:{id:'30a'}});
  assert.match(target.innerHTML,/data-action="collect-roads" disabled>Hesap sürüyor…/);
  assert.match(target.innerHTML,/data-action="collect-airfare" >↓ Uçak bileti ortalamalarını topla/);
  assert.match(target.innerHTML,/Henüz yol mesafesi çekimi yok/);assert.match(target.innerHTML,/trafik hesaba katılmadan tahmindir/);
  const box={innerHTML:''};
  const screen=new Transport();
  screen.fare={label:'BTS etiketi',note:'başlayan yolculuklar',source_url:'https://www.transtats.bts.gov/AverageFare/',snapshot:{queried_on:'2026-11-16',latest_year:2026,latest_quarter:2,fare_note:'<i>'},
    airports:[{label:'VPS',quarters:[{year:2026,quarter:2,listed:1,average_fare:376.1},{year:2025,quarter:2,listed:0,average_fare:null}],change:{amount:-16.48,percent:-4.6}}]};
  screen.drawFare({querySelector:selector=>selector==='#airfare-body'?box:null});
  assert.match(box.innerHTML,/<th>2026 Q2<\/th><th>2025 Q2<\/th><th>BİR YIL ÖNCEYE GÖRE<\/th>/);
  assert.match(box.innerHTML,/<td>\$376\.10<\/td><td><span class="muted">tabloda yok<\/span><\/td><td>−\$16\.48<small>%-4,6<\/small>/);
  assert.ok(!box.innerHTML.includes('<i>'));
});
test('refresh table names the companies added since the last run under the estimate',()=>{
  const items=[{connector:'agency-lodging-rates',source_name:'Kiralama',interval_months:1,due:true,due_reason:'önerilen aralık doldu',estimate_seconds:30000,last_done_on:'2026-10-10',
    added_companies:[{company:'Yeni <Şirket>',listings:61,requests:1525}]}];
  const html=refreshSection({items,note:'',estimate_seconds:30000,estimate_complete:true,batch:null});
  assert.match(html,/yeni şirketler dahil: Yeni &lt;Şirket&gt; 61 ilan, en çok \+1525 istek/);
});

// --- GÖREV-21: the shared parts of every Claude step (cost in the same place, one approval component), the step screens, the topic bank
// and the video list --------------------------------------------------------------------------------------------------------------------
import {costText, costLine, runningPanel, spentText, spentLine, chainTable, staleBox, errorBox, decisionCard, versionsCard, logCard, bindStep} from '../studio/web/claude-step.js';
import {titleCard, titleChooser, packCard, planCard, writingCard, versionList, checkCards, toneRadios, plannedBody} from '../studio/web/steps.js';
import {videoRow, videoList} from '../studio/web/videolist.js';

const estimate21={satirlar:[{baslik:'Plan',cagri:2,okunan:82000,yazilan:26000,toplam:108000,modeller:[{adim:'metin_plan',model_adi:'Opus',efor_adi:'Yüksek'},{adim:'metin_plan_elestiri',model_adi:'Opus',efor_adi:'Orta'}]}],
  toplam:{cagri:2,okunan:82000,yazilan:26000,toplam:108000},sinirlar:{cagri:250000,is:1500000},asiyor:[],baslatilabilir:true,metin:'Plan: 2 çağrı, yaklaşık 108 bin token'};

test('GÖREV-21 maliyet: düğmenin üstünde tahmin — kaç çağrı, okunan ve yazılan token, model',()=>{
  assert.equal(costText(estimate21),'2 çağrı · okunacak ≈ 82 bin · yazılacak ≈ 26 bin token (toplam ≈ 108 bin) · model: Opus · Yüksek; Opus · Orta');
  assert.match(costLine({estimate:estimate21}),/^<p class="cost-line " data-cost-line><span class="tag ">Tahmin<\/span> 2 çağrı · okunacak ≈ 82 bin/);
  assert.match(costLine({estimate:{...estimate21,baslatilabilir:false}}),/cost-line over.*tag error">Tahmin.*sınırı aşıyor; başlatılamaz/s);
  assert.match(costLine({loading:true}),/hesaplanıyor…/);assert.match(costLine({}),/Claude “Başlat” demeden çalışmaz/);
  assert.match(costLine({error:'Önce paket'}),/cost-error.*Önce paket/s);
  // the same line above every start button: the plan, the writing, the bank's forms and the own title of step 1
  const view={adim:{id:'plan',status:'ready'},eylemler:{run:true},calisma:null,is:null,mesgul:null};
  const card=planCard(view,{estimate:estimate21},'',false);
  assert.ok(card.indexOf('data-cost-line')<card.indexOf('id="plan-start"'));
  assert.match(card,/<button type="button" class="primary" id="plan-start" >Planı çıkar<\/button>/);
  const writing=writingCard({adim:{id:'yazim',status:'ready'},eylemler:{run:true},tonlar:[{dosya:'a',ad:'A',ilk_cumle:'c',varsayilan:true}],calisma:null,is:null},['a'],{estimate:estimate21},'',false);
  assert.ok(writing.indexOf('data-cost-line')<writing.indexOf('id="writing-start"'));
  assert.match(writing,/id="writing-start" >Yazımı başlat</);
  const chooser=titleChooser({adaylar:[],degerlendirmeler:[],secenekler:{available:true,whole_region:'30A geneli',regions:[],claude:{found:true}}},{baslik:'',bolge:'',not:''},{},'',false);
  assert.ok(chooser.indexOf('data-cost-line')<chooser.indexOf('id="own-title-start"'));
  const source=readFileSync(new URL('../studio/web/videos.js',import.meta.url),'utf8');
  assert.equal((source.match(/\$\{costLine\(\{hint\}\)\}<button class="primary" id="(title|review)-start"/g)||[]).length,2);
});

test('GÖREV-21 maliyet: iş sürerken o ana kadarki harcama (çağrı ve token) ve "İptal"; bitince gerçek ile tahmin yan yana',()=>{
  const job={id:'j1',kind:'claude_metin',status:'running',progress:40,message:'Bölüm yazılıyor',created_at:'2026-11-16T10:00:00Z',
    progress_info:{tur:'metin',yuzde:40,asama:'bölümler 2/6 bitti',harcama:{tahmin:540000,gercek:{cagri:3,okunan:95000,yazilan:25000,toplam:120000}}}};
  const panel=runningPanel(job);
  assert.match(panel,/data-run-panel="j1"/);assert.match(panel,/<button type="button" class="quiet" data-step-cancel="j1">İptal<\/button>/);
  assert.match(panel,/Şu ana kadar<\/span> 3 çağrı · 120 bin token \(okunan 95 bin, yazılan 25 bin\) · tahmin 540 bin token/);
  assert.match(panel,/aria-valuenow="40"/);assert.match(panel,/iptal edildi” diye düşer; o ana kadarki harcaması sayılır/);
  assert.match(runningPanel({...job,progress_info:{tur:'metin',yuzde:5}}),/henüz biten çağrı yok/);
  assert.equal(runningPanel({...job,status:'done'}),'');assert.equal(runningPanel(null),'');
  assert.equal(spentText({cagri:0,toplam:0}),'0 çağrı bitti (token, çağrı bitince sayılır)');
  const line=spentLine({tahmin:100000,gercek:{cagri:4,okunan:150000,yazilan:20000,toplam:170000},karsilastirma:{fazla:true,uyari:'Gerçek harcama tahminin 1,5 katını geçti.'}});
  assert.match(line,/spend-line over.*gerçek 4 çağrı · 170 bin token.*tahmin 100 bin token.*Beklenenden fazla<\/span> Gerçek harcama tahminin 1,5 katını geçti\./s);
  assert.doesNotMatch(spentLine({tahmin:{toplam:100000},gercek:{cagri:2,okunan:80000,yazilan:10000,toplam:90000},karsilastirma:{fazla:false}}),/Beklenenden fazla/);
  assert.equal(spentLine(null),'');
  // "İptal" asks for the job's cancellation; the screen then says how it was recorded
  let canceled=null;
  const button={dataset:{stepCancel:'j1'},addEventListener(_,fn){this.click=fn;},disabled:false};
  const root={querySelectorAll:selector=>selector==='[data-step-cancel]'?[button]:[],querySelector:()=>null};
  globalThis.confirm=()=>true;
  bindStep(root,{cancel:id=>{canceled=id;}});button.click();
  delete globalThis.confirm;
  assert.equal(canceled,'j1');assert.equal(button.disabled,true);
  const steps=readFileSync(new URL('../studio/web/steps.js',import.meta.url),'utf8');
  assert.match(steps,/await api\(`jobs\/\$\{encodeURIComponent\(jobId\)\}\/cancel`,\{method:"POST"\}\);this\.message="İptal edildi; iş kayda “iptal edildi” diye düştü, harcaması sayıldı\."/);
});

test('GÖREV-21 maliyet: çok parçalı adımlarda halka tablosu — durum, çağrı, gerçek ve tahmini token; altında toplam ve tahmin',()=>{
  const chain={halkalar:[
    {grup:'plan',grup_adi:'Plan',adim:'metin_plan',baslik:'Planlayıcı',durum:'done',durum_adi:'Tamamlandı',ayrinti:null,cagri:1,gercek:70000,tahmin:80000,tahmini_cagri:1},
    {grup:'plan',grup_adi:'Plan',adim:'metin_plan_elestiri',baslik:'Plan eleştirmeni',durum:'running',durum_adi:'Çalışıyor',ayrinti:null,cagri:0,gercek:0,tahmin:28000,tahmini_cagri:1},
    {grup:'a',grup_adi:'Araştırmacı dost',adim:'metin_bolum',baslik:'Bölümler',durum:'partial',durum_adi:'Yarıda kaldı',ayrinti:'2/6 bölüm',cagri:2,gercek:50000,tahmin:150000,tahmini_cagri:6},
    {grup:'a',grup_adi:'Araştırmacı dost',adim:'denetim',baslik:'Program denetimi',durum:'waiting',durum_adi:'Bekliyor',ayrinti:'Claude çağrısı yok',cagri:0,gercek:0,tahmin:null,tahmini_cagri:null}],
    toplam:{cagri:3,gercek:120000,tahmin:258000},fazla:false,uyari:null};
  const html=chainTable(chain,{title:'Yazımın halkaları'});
  assert.match(html,/<h2>Yazımın halkaları<\/h2>/);
  assert.match(html,/<th>HALKA<\/th><th>DURUM<\/th><th>ÇAĞRI \(YAPILAN \/ TAHMİN\)<\/th><th>GERÇEK TOKEN<\/th><th>TAHMİNİ TOKEN<\/th>/);
  assert.equal((html.match(/class="chain-group"/g)||[]).length,2);
  assert.match(html,/data-link="metin_plan"><td>Planlayıcı<\/td>\s*<td><span class="tag green">Tamamlandı<\/span><\/td><td>1 \/ 1<\/td>\s*<td>70 bin<\/td><td>80 bin<\/td>/);
  assert.match(html,/Bölümler<small class="source-host">2\/6 bölüm<\/small><\/td>\s*<td><span class="tag warm">Yarıda kaldı<\/span><\/td><td>2 \/ 6<\/td>/);
  assert.match(html,/Program denetimi<small class="source-host">Claude çağrısı yok<\/small>.*Bekliyor<\/span><\/td><td>0<\/td>\s*<td>—<\/td><td>—<\/td>/s);
  assert.match(html,/<tfoot><tr><td>Toplam<\/td><td><\/td><td>3<\/td><td><strong>120 bin<\/strong><\/td><td>258 bin<\/td>/);
  assert.match(chainTable({...chain,fazla:true,uyari:'Gerçek harcama tahminin 1,5 katını geçti.'}),/Beklenenden fazla<\/span> Gerçek harcama tahminin 1,5 katını geçti\./);
  assert.equal(chainTable({halkalar:[]}),'');assert.equal(chainTable(null),'');
});

test('GÖREV-21 onay bileşeni: 1, 3 ve 5. adımlarda aynı bileşen — not alanı ve üç düğme; onaysız adımda yok',()=>{
  const all={approve:true,correct:true,reject:true};
  for(const id of ['baslik','plan','kontrol']) {
    const card=decisionCard({id,approval:true,status:'awaiting_approval'},all);
    assert.match(card,/id="decision-card" aria-label="Karar"/,id);assert.match(card,/<textarea id="decision-note"/,id);
    assert.deepEqual([...card.matchAll(/data-decision="([a-z]+)"/g)].map(m=>m[1]),['onayla','duzeltme','reddet'],id);
    assert.match(card,/>Onayla<\/button>\s*<button type="button" data-decision="duzeltme" >Düzeltme iste<\/button>\s*<button type="button" class="quiet" data-decision="reddet" >Reddet<\/button>/,id);
    assert.match(card,/kullanıcının düzeltme notu/,id);
  }
  assert.equal(decisionCard({id:'paket',approval:false,status:'done'},all),'');                 // a step without approval has no decision
  assert.equal(decisionCard({id:'yazim',approval:false,status:'done'},all),'');
  assert.equal(decisionCard({id:'plan',approval:true,status:'ready'},{approve:false,correct:false,reject:false}),'');
  const approved=decisionCard({id:'plan',approval:true,status:'approved'},{approve:false,correct:true,reject:true});
  assert.match(approved,/data-decision="onayla" disabled/);assert.match(approved,/data-decision="duzeltme" >/);
  // 5 · Kontrol: the tone to go on with is chosen next to "Onayla"
  const tones=toneRadios({tonlar:[{id:'s1',tone_name:'Araştırmacı dost',number:1,red:1,yellow:2},{id:'s2',tone_name:'Vlogger',number:2,red:0,yellow:0}]},'s2');
  const check=decisionCard({id:'kontrol',approval:true,status:'awaiting_approval'},all,{extra:tones,approveLabel:'Onayla ve bu tonla devam et'});
  assert.match(check,/Devam edilecek ton.*name="go-on-tone" value="s1" >.*name="go-on-tone" value="s2" checked>.*Onayla ve bu tonla devam et/s);
  assert.ok(check.indexOf('go-on-tone')<check.indexOf('data-decision="onayla"'));
  // the buttons reach the handler with the note
  const calls=[];
  const buttons=['onayla','duzeltme','reddet'].map(kind=>({dataset:{decision:kind},addEventListener(_,fn){this.click=fn;}}));
  const root={querySelectorAll:selector=>selector==='[data-decision]'?buttons:[],querySelector:selector=>selector==='#decision-note'?{value:'kısalt'}:null};
  bindStep(root,{decide:(kind,note)=>calls.push([kind,note])});
  buttons.forEach(button=>button.click());
  assert.deepEqual(calls,[['onayla','kısalt'],['duzeltme','kısalt'],['reddet','kısalt']]);
  // the old buttons are gone from the screens
  for(const file of ['steps.js','text.js','videos.js','claude-step.js']) {
    const source=readFileSync(new URL(`../studio/web/${file}`,import.meta.url),'utf8');
    assert.doesNotMatch(source,/Bu başlığı seç<|Bu tonla devam et<|>Devam<\/button>|Plandan sonra dur</,file);
  }
});

test('GÖREV-21 eskime: sebep Türkçe yazılır, "Bu değişiklik etkilemiyor" adımı önceki durumuna döndürür; hata ve sürümler',()=>{
  const stale=staleBox({status:'stale',stale_reason:'Plan onayı değişti.',status_before_stale:'done'},{clear_stale:true});
  assert.match(stale,/<strong>Bu adım eskidi:<\/strong> Plan onayı değişti\..*önceki durumuna \(tamamlandı\) döner.*<button type="button" data-clear-stale >Bu değişiklik etkilemiyor<\/button>/s);
  assert.equal(staleBox({status:'done'},{}),'');
  let note=null;
  const root={querySelectorAll:()=>[],querySelector:selector=>selector==='[data-clear-stale]'?{addEventListener(_,fn){this.click=fn;root.button=this;}}:selector==='#stale-note'?{value:'veri aynı'}:null};
  bindStep(root,{clearStale:text=>{note=text;}});root.button.click();
  assert.equal(note,'veri aynı');
  assert.match(errorBox({status:'error',error:'Program kapanırken yarıda kaldı; kaldığı yerden sürdürebilirsiniz.'}),/claude-warning.*kaldığı yerden sürdürebilirsiniz/s);
  assert.equal(errorBox({status:'ready',error:null}),'');
  const resumable=planCard({adim:{id:'plan',status:'error'},eylemler:{run:true,resume:true},calisma:null,is:null},{},'',false);
  assert.match(resumable,/data-resume>Kaldığı yerden sürdür</);
  const versions=versionsCard([{id:'r2',zaman:'2026-11-16T10:00:00Z',baslik:'6 bölümlü plan · onaylı',ayrinti:'Düzeltme notu: kısalt'},{id:'r1',zaman:'2026-11-15T10:00:00Z',baslik:'5 bölümlü plan'}],item=>item.id==='r2'?'#x':'');
  assert.match(versions,/<h2>Sürümler<\/h2><small>2 kayıt · hiçbiri silinmez<\/small>.*<a href="#x">6 bölümlü plan · onaylı<\/a><small class="source-host">Düzeltme notu: kısalt<\/small>.*<strong>5 bölümlü plan<\/strong>/s);
  assert.equal(versionsCard([]),'');
  assert.match(logCard([{at:'2026-11-16T10:00:00Z',text:'3 · Plan onaylandı. Not: yok'}]),/Durum günlüğü.*3 · Plan onaylandı\. Not: yok/s);
});

test('GÖREV-21 adım ekranları: başlık (Türkçe büyük, İngilizce küçük), plan onaylanmadan yazım yok, kontrol, henüz kurulmayan adımlar',()=>{
  const title=titleCard({baslik_tr:'Çiftler için <Rosemary>',baslik_en:'Rosemary for Couples',bolge:'Rosemary Beach',aile:'Deneyim',izleyici_sorusu:'Uygun mu?',vaat:'Evet, çünkü…',neden_onerildi:'Boşluk var.',
    icerik_plani:[{bolum:'Fiyat',ne_anlatir:'Ne tutar?'}],eksik_veri:['Yorum yok'],kapak_fikri:'İki sandalye',isaretler:[]});
  assert.match(title,/<p class="title-tr-big">Çiftler için &lt;Rosemary&gt;<\/p><p class="title-en-small" lang="en">Rosemary for Couples<\/p>/);
  assert.match(title,/İzleyicinin sorusu<\/h3><p>Uygun mu\?<\/p>\s*<h3>Vaat<\/h3><p>Evet, çünkü…<\/p>/);assert.match(title,/<strong>Fiyat<\/strong> — Ne tutar\?/);
  assert.equal(titleCard(null),'');
  const chooser=titleChooser({adaylar:[{calisma:'r1',sira:2,baslik_tr:'Başlık',baslik_en:'Title',aile:'Deneyim',bolge:'Seaside',bu_video:true}],degerlendirmeler:[],secenekler:{available:false}},{baslik:'',bolge:'',not:''},{},'',false);
  assert.match(chooser,/Konu bankasından seç.*title-tr-big small">Başlık<\/span><span class="title-en-small" lang="en">Title<\/span>.*bu video için değerlendirildi.*data-use-candidate="r1:2" >Bu başlığı kullan/s);
  assert.match(packCard({adim:{id:'paket',status:'ready'},eylemler:{run:true},surumler:[],paket:null},false),/Claude çalışmaz · token harcamaz.*id="pack-build" >Veri paketini üret</s);
  // 4 · Yazım never starts before the plan is approved: the step waits, its button is off and the screen says why
  const waiting=writingCard({adim:{id:'yazim',status:'waiting'},eylemler:{run:false},tonlar:[{dosya:'a',ad:'A',ilk_cumle:'c',varsayilan:true}],calisma:null,is:null},['a'],{},'',false);
  assert.match(waiting,/id="writing-start" disabled>Yazımı başlat</);assert.match(waiting,/Plan onaylanmadan yazım başlamaz: önce 3 · Plan adımında planı onaylayın\./);
  const note=writingCard({adim:{id:'yazim',status:'ready'},eylemler:{run:true},tonlar:[{dosya:'a',ad:'A',ilk_cumle:'c',varsayilan:true}],calisma:null,is:null,duzeltme_notu:'Girişi kısalt'},['a'],{},'',false);
  assert.match(note,/Kullanıcının düzeltme notu<\/strong> \(5 · Kontrol ve ton seçimi adımından\): Girişi kısalt.*Claude&#39;a malzeme olarak verilir|Kullanıcının düzeltme notu<\/strong> \(5 · Kontrol ve ton seçimi adımından\): Girişi kısalt.*Claude'a malzeme olarak verilir/s);
  assert.match(note,/>Düzeltme notuyla yeniden yaz</);
  const list=versionList({calisma:{surumler:[{id:'s1',number:1,tone_name:'Araştırmacı dost',words:2300,dakika:15.3,red:1,yellow:2,created_at:'2026-11-16T10:00:00Z',secili:true}]}},'v1');
  assert.match(list,/Araştırmacı dost<\/strong> <span class="tag green">seçili ton<\/span>.*2\.300 kelime · ~15,3 dk.*href="#video\/v1\/yazim\/surum\/s1">Metni oku/s);
  const cards=checkCards({tonlar:[{id:'s1',tone_name:'Araştırmacı dost',number:1,red:2,yellow:1,words:2300,dakika:15.3,secili:false,isletme_adi:1,
    bulgular:[{kural:'isletme',ad:'işletme adı',kirmizi:1,sari:0,ornekler:[{no:12,metin:'Modica Market adı geçiyor.',seviye:'kirmizi'}]},{kural:'ses',ad:'ses',kirmizi:0,sari:1,ornekler:[{no:3,metin:'amazing',seviye:'sari'}]}]}]});
  assert.match(cards,/Programın denetimi.*Araştırmacı dost.*2 kırmızı.*tag error">İşletme adı denetimi: 1 bulgu.*işletme adı<\/strong>.*12\. cümle: Modica Market adı geçiyor\..*ses<\/strong>/s);
  assert.match(checkCards({tonlar:[{id:'s1',tone_name:'A',number:1,red:0,yellow:0,words:10,dakika:0.1,isletme_adi:0,bulgular:[]}]}),/tag green">İşletme adı denetimi: bulgu yok/);
  assert.match(plannedBody({adim:{title:'Kurgu paketi'},aciklama:'Kurgu Motoru\'na gidecek paket.'}),/Sonraki görevde gelecek.*Kurgu paketi.*Kurgu Motoru&#39;na gidecek paket\./s);
});

test('GÖREV-21 konu bankası: çalışmalar ve adayları (Türkçe büyük, İngilizce küçük), "Bu başlıkla video aç", kullanılan adayda video',()=>{
  const bank={calismalar:[{id:'r1',step:'baslik',status:'approved',created_at:'2026-10-10T19:57:00Z',params:{bolge:'30A geneli',aile:'hepsi'},model_label:'Opus 5.5',metrics:{},
      adaylar:[{sira:0,baslik_tr:'Kış videosu',baslik_en:'Winter Video',aile:'Sezon ve zamanlama',bolge:'30A geneli',video_id:'v1',video_adi:'Kış videosu',secilebilir:false},
        {sira:1,baslik_tr:'Bütçe <rehberi>',baslik_en:'Budget Guide',aile:'Masraf ve bütçe',bolge:'Seaside',video_id:null,video_adi:null,secilebilir:true}]},
    {id:'r2',step:'baslik_degerlendirme',status:'awaiting_approval',adaysiz:true,bilgi:'Değerlendirildi: veriyle dolmuyor',created_at:'2026-10-10T23:32:00Z',params:{bolge:'Rosemary Beach',kullanici_basligi:'köpek'},metrics:{},adaylar:[]}],aday_sayisi:2,kullanilan:1,kullanilabilir:1};
  const html=bankRuns(bank);
  assert.match(html,/data-bank-run="r1".*Öneri · 30A geneli/s);
  assert.match(html,/<li class="used">.*title-tr-big small">Kış videosu<\/span><span class="title-en-small" lang="en">Winter Video<\/span>.*<span class="tag green">kullanıldı<\/span> <a class="source-link" href="#video\/v1\/baslik">Kış videosu →<\/a>/s);
  assert.match(html,/title-tr-big small">Bütçe &lt;rehberi&gt;<\/span>.*<span class="tag">Seaside<\/span>\s*<button type="button" class="primary" data-open-video="r1:1">Bu başlıkla video aç<\/button>/s);
  assert.equal((html.match(/data-open-video=/g)||[]).length,1);                    // a used candidate cannot open a second video
  assert.match(html,/Değerlendirme · “köpek”.*Fikir veriyle dolmuyor; aday yok/s);
  assert.match(bankRuns({calismalar:[]}),/Henüz öneri çalışması yok/);
  const source=readFileSync(new URL('../studio/web/videos.js',import.meta.url),'utf8');      // "Bu başlıkla video aç" opens the video
  assert.match(source,/api\(`claude\/runs\/\$\{encodeURIComponent\(runId\)\}\/select`[\s\S]{0,200}studio:video-opened",\{detail:\{id:video\.id,step:"baslik"\}\}/);
  assert.match(source,/<h2>Öneri al<\/h2>/);assert.match(source,/Önceki öneriler \(/);
});

test('GÖREV-21 Videolar: başlığın Türkçesi büyük, İngilizcesi küçük; tarih; adım ilerlemesi; "Yeni video", "Arşive kaldır", "Arşivdekileri göster"; silme yok',()=>{
  const video={id:'v1',ad:'Kış videosu',calisma_adi:'kış',baslik_tr:'Kış videosu',baslik_en:'Winter Video',bolge:'30A geneli',olusturuldu:'2026-11-16T10:00:00Z',arsivlendi:null,ilerleme:'3/8',completed:3,total:8,
    siradaki:{id:'yazim',ad:'4 · Yazım',durum:'ready',durum_adi:'hazır'}};
  const row=videoRow(video,{open:true});
  assert.match(row,/data-open-video="v1".*<span class="title-tr-big">Kış videosu<\/span>\s*<span class="title-en-small" lang="en">Winter Video<\/span>/s);
  assert.match(row,/oluşturuldu /);assert.match(row,/<span class="video-progress"[^>]*>3\/8<\/span>/);assert.match(row,/4 · Yazım: hazır/);
  assert.match(row,/<span class="tag green">açık<\/span>/);assert.match(row,/data-archive="v1">Arşive kaldır</);
  const untitled=videoRow({...video,baslik_tr:null,baslik_en:null,ilerleme:'0/8',siradaki:{id:'baslik',ad:'1 · Başlık ve vaat',durum:'ready',durum_adi:'hazır'}});
  assert.match(untitled,/<span class="title-tr-big">kış<\/span>\s*<span class="title-en-small">Başlık henüz seçilmedi \(1 · Başlık ve vaat\)/);
  assert.match(videoRow({...video,arsivlendi:'2026-11-16T12:00:00Z'},{archived:true}),/data-open-video="v1" disabled.*data-unarchive="v1">Arşivden çıkar/s);
  const list=videoList({videolar:[video],arsiv:false,arsivdeki:2,acik:'v1'},{name:''});
  assert.match(list,/<h2>Yeni video<\/h2>.*Çalışma adı \(isteğe bağlı\).*id="new-video">Yeni video<\/button>.*Projenin videoları.*id="show-archived">Arşivdekileri göster \(2\)/s);
  assert.doesNotMatch(list+row,/>Sil<|data-delete/);                                 // nothing is deleted
  assert.match(videoList({videolar:[],arsiv:true,arsivdeki:0,acik:null},{name:''}),/Arşivdeki videolar.*Arşivde video yok\..*← Projenin videoları/s);
});

// GÖREV-22: the estimate names the new companies (listings, own homes, the proxy); the company's own inventory across the neighbourhoods
import {addedCompany} from '../studio/web/refresh.js';
import {ownCompanies} from '../studio/web/agency.js';
test('the estimate line of a new company says its listings, its own homes and the proxy',()=>{
  assert.equal(addedCompany({company:'360 Blue',listings:256,own_homes:0,requests:3840,proxy:true}),"360 Blue 256 ilan, en çok +3840 istek (ABD proxy'siyle)");
  assert.equal(addedCompany({company:'30A Beach Girls',listings:48,own_homes:145,requests:145,proxy:false}),'30A Beach Girls 48 ilan, kendi sitesinde 145 ev, en çok +145 istek');
  assert.equal(addedCompany({company:'Yeni',listings:0,own_homes:0,requests:5}),'Yeni 0 ilan, en çok +5 istek');
});
test('homes on a company\'s own site are shown apart, with the ones the site gives no neighbourhood',()=>{
  assert.equal(ownCompanies([]),'');
  assert.equal(ownCompanies([{company:'Alys Beach',domain:'alysbeach.com',homes:73,with_region:73,unassigned:0,priced:73,regions:[{region_name:'Alys Beach',homes:73}]}]),'');   // one community's program: shown in its neighbourhood
  const html=ownCompanies([{company:'30A Beach Girls',domain:'30a-beachgirls.com',homes:120,with_region:40,unassigned:80,outside:25,on_bookdirect:2,priced:0,
    regions:[{region_name:'Seagrove',homes:30},{region_name:'Seacrest',homes:10}]}]);
  assert.match(html,/Şirketin kendi sitesindeki evler/);
  assert.match(html,/Book>Direct ilanlarına bağlanmadı/);
  assert.match(html,/<td>120<small>30A bölgesi dışında 25 ev alınmadı<\/small><small>Book>Direct ilanına bağlanan 2 ev ayrıca sayılmadı<\/small><\/td><td>40<small>Seagrove 30 · Seacrest 10<\/small><\/td><td>80<\/td><td>0<\/td>/);
  assert.match(html,/MAHALLESİ BELİRTİLMEMİŞ/);
});

// GÖREV-23: a company whose site prices by rent alone (its calendar's nightly rates summed) shows the weekly rent medians as rent, never as a total
import {ownRents} from '../studio/web/agency.js';
test('the own-homes table shows the weekly rent medians of a rent-only company and says what they leave out',()=>{
  assert.equal(ownRents({windows:[{window_key:'a',rent_count:0,rent_median:null,priced_count:3,total_median:5000}]}),'—');
  assert.equal(ownRents({}),'—');
  const cell=ownRents({windows:[{window_key:'a',rent_count:40,rent_median:1468},{window_key:'b',rent_count:35,rent_median:3210.5},{window_key:'c',rent_count:0,rent_median:null}]});
  assert.match(cell,/\$1,468.*–\$3,21\d/);
  assert.match(cell,/2 haftanın ortancaları · yalnız kira; ücret ve vergi hariç/);
  const html=ownCompanies([{company:'30A Beach Girls',domain:'30a-beachgirls.com',homes:120,with_region:40,unassigned:80,priced:75,
    regions:[{region_name:'Seagrove',homes:30},{region_name:'Seacrest',homes:10}],windows:[{window_key:'a',rent_count:40,rent_median:1468}]}]);
  assert.match(html,/HAFTALIK KİRA ORTANCASI/);
  assert.match(html,/<td>75<\/td><td>\$1,468[^<]*<small>1 haftanın ortancaları · yalnız kira; ücret ve vergi hariç<\/small><\/td>/);
});
