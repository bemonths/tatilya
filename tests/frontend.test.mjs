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
  const source=readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
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

import {regionOptions, familyOptions, warnings, runRow, candidateList, candidateDetail, videoCard} from '../studio/web/videos.js';
import {claudeSection} from '../studio/web/claude.js';
import {storedVideo, persistVideo, progressText, videoOptions, stepOfHash, stepNav, toolNav, nextTask} from '../studio/web/workflow.js';
import {usageHtml, claudeProgress, progressText as claudeProgressText, durationText, claudeBar} from '../studio/web/usage.js';
import {editorHtml, versionRows, fileButtons} from '../studio/web/instructions.js';
import {suffixSection} from '../studio/web/claude.js';
import {instructionLine} from '../studio/web/videos.js';
import {editProblems, editForm, reviewSummary, runRow as videoRunRow, videoCard as videoCardOf} from '../studio/web/videos.js';
import {packHead} from '../studio/web/workflow.js';

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
    /href="#videos\/run\/r1".*Onay bekliyor.*Opus 5.5 · Yüksek.*9 tur/s);
});

test('titles are listed first; a chosen title opens its details with the evidence values and the select button', () => {
  const view={params:{bolge:'Rosemary Beach'},actions:{select:true},candidates:[titleCandidate,{...titleCandidate,sira:1,baslik_en:'Second',sorunlar:[{seviye:'hata',metin:'Var olmayan kanıt'}],secilebilir:false}]};
  const closed=candidateList(view,null);
  assert.match(closed,/Why &lt;People&gt; Pay So Much<\/span><span class="title-tr">Neden bu kadar ödeniyor<\/span>.*Deneyim/s);
  assert.doesNotMatch(closed,/Neden önerildi/);
  assert.match(closed,/doğrulama hatası/);
  const open=candidateList(view,0);
  assert.match(open,/Neden önerildi.*İzleyicinin sorusu.*Kanca.*K0034.*3,727 USD \(7 gece\).*İçerik planı.*Fiyat.*Eksik veri.*Yorum yok.*mahalle-rehberi.*mahalle = rosemary-beach.*Kapak fikri.*Bu başlığı seç/s);
  assert.match(candidateDetail(view.candidates[1],view),/Hata: Var olmayan kanıt.*data-select-candidate="1" disabled/s);
  assert.match(candidateDetail({...titleCandidate,video_id:'v1'},view),/Bu başlık seçildi/);
});

test('a video record without a template still produces its plan pack (GÖREV-14); the Claude settings section shows path, version and inherit choices', () => {
  const video={id:'v1',title_en:'T',title_tr:'B',family:'Deneyim',region_name:'Rosemary Beach',status:'baslik_secildi',status_label:'başlık seçildi',created_at:'',template_key:null,params:{},analysis:{},packs:[]};
  assert.match(videoCard(video),/yeni şablon gerekir \(bilgi\).*data-video-pack="v1">Kanıt paketi üret.*içerik planından kurulur/s);
  assert.match(videoCard({...video,template_key:'mahalle-rehberi',packs:[{id:'p1'}]}),/data-video-pack="v1">.*yazar-ozeti/s);
  const section=claudeSection({settings:{claude_path:'',claude_model:'',claude_effort:'',claude_model_baslik:'claude-opus-5-5',claude_effort_baslik:'high',claude_max_turns_baslik:30},
    notes:[],info:{found:true,path:'D:/programs/claude.exe',version:'2.1.284',api_key_warning:'ANTHROPIC_API_KEY uyarısı'},
    options:{models:[{value:'',label:'Claude Code varsayılanı'},{value:'claude-opus-5-5',label:'Opus 5.5'}],efforts:[{value:'',label:'Otomatik'},{value:'high',label:'Yüksek'}],
      inherit:{value:'inherit',label:'Genel varsayılan'},steps:[{key:'baslik',label:'Konu ve başlık',model_field:'claude_model_baslik',effort_field:'claude_effort_baslik',max_turns_field:'claude_max_turns_baslik'}],
      max_turns:{min:1,max:200,help:'Tur'}}});
  assert.ok(section.includes('Bulunan program: D:/programs/claude.exe<br>Sürüm: 2.1.284'));
  assert.match(section,/ANTHROPIC_API_KEY uyarısı/);
  assert.match(section,/data-field="claude_model_baslik".*<option value="inherit" >Genel varsayılan<\/option>.*<option value="claude-opus-5-5" selected>Opus 5.5/s);
  assert.match(section,/data-field="claude_max_turns_baslik" min="1" max="200" value="30"/);
});

// GÖREV-14: workflow sidebar helpers.

const flow={video:null,videos:[{id:'v1',title_en:'Rosemary <Beach> Guide',title_tr:'Rehber',region_name:'Rosemary Beach'}],completed:2,total:8,dots:'●●○○○○○○',
  steps:[{id:'veri',number:1,title:'Veri',status:'done',label:'güncel',next:'Veri güncel.',href:'#adim/veri',planned:false,detail:null},
    {id:'baslik',number:2,title:'Konu ve başlık',status:'awaiting_approval',label:'onay bekliyor',next:'Başlık seçilmedi: onay bekleyen öneriden bir başlık seç ya da yeni öneri al.',href:'#videos',planned:false,detail:'1 çalışma onay bekliyor'},
    {id:'metin',number:4,title:'Video metni',status:'planned',label:'planlanan',next:'Bu adım henüz kurulmadı.',href:'#adim/metin',planned:true,detail:null}]};

test('workflow: progress, video selector, routes and the remembered video', () => {
  assert.equal(progressText(flow),'●●○○○○○○ 2/8 adım');
  assert.equal(progressText(null),'');
  const options=videoOptions(flow,'v1');
  assert.match(options,/^<option value="">Video seçilmedi<\/option><option value="v1" selected>Rosemary &lt;Beach&gt; Guide<\/option>$/);
  assert.equal(videoOptions(null),'<option value="">Video seçilmedi</option>');
  assert.equal(stepOfHash('#adim/paket'),'paket');
  assert.equal(stepOfHash('#videos'),'baslik');
  assert.equal(stepOfHash('#videos/run/abc'),'baslik');
  assert.equal(stepOfHash('#sources'),null);
  const memory=new Map(), storage={getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,v),removeItem:k=>memory.delete(k)};
  assert.equal(storedVideo(storage,'30a'),'');
  persistVideo(storage,'30a','v1');assert.equal(storedVideo(storage,'30a'),'v1');assert.equal(storedVideo(storage,'other'),'');
  persistVideo(storage,'30a','');assert.equal(storedVideo(storage,'30a'),'');
  const broken={getItem(){throw new Error('kapalı');},setItem(){throw new Error('kapalı');},removeItem(){throw new Error('kapalı');}};
  assert.equal(storedVideo(broken,'30a'),'');persistVideo(broken,'30a','v1');
});

test('workflow: ADIMLAR shows each step with its live status, VERİ the tool screens; every step screen starts with the next task', () => {
  const nav=stepNav(flow,'baslik');
  assert.match(nav,/ADIMLAR · video seçilmedi.*href="#adim\/veri".*Veri.*step-status green.*güncel.*href="#videos" class="workflow-step active.*aria-current="page".*onay bekliyor.*planned-step.*planlanan/s);
  assert.equal(stepNav(null,'veri'),'');
  assert.match(stepNav({...flow,video:{id:'v1'}},null),/^<div class="group-label">ADIMLAR<\/div>/);
  const tools=toolNav([{id:'sources',title:'Veri kaynakları',subtitle:'Kaynak kütüphanesi',state:'active'},{id:'evidence',title:'Kanıt paketi',subtitle:'Şablondan kanıt',state:'active'}],'evidence');
  assert.match(tools,/VERİ.*href="#sources".*Veri kaynakları.*href="#evidence" class="active"/s);
  assert.ok(!tools.includes('Rakip analizi') && !tools.includes('İçerik briefi'));
  const line=nextTask(flow.steps[1]);
  assert.match(line,/Sıradaki iş.*Başlık seçilmedi: onay bekleyen öneriden bir başlık seç ya da yeni öneri al\..*onay bekliyor.*1 çalışma onay bekliyor/s);
  assert.equal(nextTask(null),'');
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
  const video={id:'v1',title_en:'Edited | 30A Florida Vacation',title_tr:'Düzenli | 30A Florida Tatili',family:'Deneyim',region_name:'Seaside',status:'baslik_secildi',status_label:'başlık seçildi',created_at:'',template_key:'mahalle-rehberi',params:{},analysis:{},packs:[],
    user_edited:true,proposed_title_en:'Proposed | 30A Florida Vacation',proposed_title_tr:'Önerilen | 30A Florida Tatili'};
  assert.match(videoCardOf(video),/kullanıcı düzenledi.*Önerilen başlık: Proposed \| 30A Florida Vacation · Önerilen \| 30A Florida Tatili/s);
  assert.ok(!videoCardOf({...video,user_edited:false}).includes('kullanıcı düzenledi'));
});

test('app.js imports every name once (a repeated import name stops the whole page)', () => {
  const source=readFileSync(new URL('../studio/web/app.js', import.meta.url),'utf8');
  const names=[...source.matchAll(/^import\s*\{([^}]*)\}\s*from/gm)].flatMap(m=>m[1].split(',').map(part=>part.trim().split(/\s+as\s+/).pop()).filter(Boolean));
  const repeated=names.filter((name,index)=>names.indexOf(name)!==index);
  assert.deepEqual(repeated,[]);
  assert.ok(names.includes('claudeProgressText') && names.includes('progressText'));
});

// GÖREV-14 Adım 6: the head of a video pack's writer's summary on the Veri paketi step.

test('pack head: everything before the first plan section', () => {
  const text='# Başlık — yazar özeti\n\n## Video\n\nkanca\n\n## Bilinen boşluklar\n\n- boşluk\n\n## 1. Bölüm\n\nsatırlar';
  assert.equal(packHead(text),'# Başlık — yazar özeti\n\n## Video\n\nkanca\n\n## Bilinen boşluklar\n\n- boşluk');
  assert.equal(packHead('# Yalnız baş'),'# Yalnız baş');
});
