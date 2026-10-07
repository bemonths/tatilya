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
  assert.equal((tabs.match(/class="tab/g)||[]).length,5);
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
