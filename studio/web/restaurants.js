import {api, esc, date} from "./api.js";
import {collectionTabs} from "./connectors.js";

export function restaurantAddress(record) {
  return [record.address_line_1,record.address_line_2,record.city,record.state,record.postal_code].filter(Boolean).join(", ");
}
export function filterRestaurants(records, {search="",neighborhood="",cuisine="",meal=""}={}) {
  const query=search.trim().toLocaleLowerCase("en-US");
  return records.filter(record=>(!neighborhood || record.source_neighborhoods.includes(neighborhood)) &&
    (!cuisine || record.cuisines.includes(cuisine)) && (!meal || record.meals_served.includes(meal)) &&
    `${record.name} ${restaurantAddress(record)} ${record.description || ""}`.toLocaleLowerCase("en-US").includes(query));
}
export function restaurantLink(url, label) {
  try { if(!["http:","https:"].includes(new URL(url).protocol)) return "Belirtilmemiş"; }
  catch { return "Belirtilmemiş"; }
  return `<a class="source-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`;
}
const shown=value=>esc(value || "Belirtilmemiş");
const pills=values=>values.length?values.map(v=>`<span class="feature-pill">${esc(v)}</span>`).join(""):"<p>Belirtilmemiş</p>";

export class RestaurantScreen {
  constructor() {this.selectedRun=null;this.selectedRecord=null;this.filters={search:"",neighborhood:"",cuisine:"",meal:""};this.sequence=0;}
  invalidate() {this.sequence++;}
  render(main,data,heading) {
    const sequence=++this.sequence;
    const runs=data.restaurant_runs || [];
    if(!runs.some(r=>r.id===this.selectedRun)) this.selectedRun=runs[0]?.id || null;
    const run=runs.find(r=>r.id===this.selectedRun);
    const source=data.sources.find(s=>s.enabled && s.connector?.name==="south-walton-restaurants");
    const busy=data.jobs.some(j=>j.source_id===source?.id && ["queued","running"].includes(j.status));
    main.innerHTML=collectionTabs("restaurants")+heading("Veri toplama","30A boyunca restoranları, kaynakta listelenen mutfak türlerini ve iletişim bilgilerini incele.",
      `<button class="primary" data-action="collect-restaurants" ${!source || busy?"disabled":""}>${busy?"Toplama sürüyor…":"↓ Restoran verilerini topla"}</button>`)+
      `<section class="connector-strip"><div><span class="eyebrow">BAĞLI KAYNAK</span><h2>${esc(source?.name || "South Walton · Restoranlar")}</h2><p>Visit South Walton · 13 mahalle · Yalnızca Restaurants</p></div><span class="tag ${source?"green":"warm"}">${source?"HTML · bağlı":"Kaynak etkin değil"}</span></section>`+
      (run?`<section class="overview collection-overview">${[[run.record_count,"restoran","Seçili veri sürümünde"],[run.metadata.represented_neighborhood_count,"temsil edilen mahalle","13 hedef mahalle tarandı"],[run.metadata.cuisine_count,"mutfak türü","Kaynakta listelenen"]].map(([n,label,note])=>`<div class="metric"><div><div class="metric-number"><strong>${esc(n)}</strong><span class="metric-label">${label}</span></div><small>${note}</small></div></div>`).join("")}</section>
      <div class="collection-version"><label>Sürüm <select id="restaurant-version" aria-label="Restoran veri sürümü">${runs.map((r,i)=>`<option value="${esc(r.id)}" ${r.id===run.id?"selected":""}>${i===0?"Son çekim · ":""}${esc(date(r.fetched_at))} · ${r.record_count} kayıt · ${r.id.slice(0,6)}</option>`).join("")}</select></label><a class="download-link" href="/api/restaurant-runs/${run.id}/raw" download>↓ Ham kaynak manifestini indir</a></div>
      <p class="source-stamp">Son çekim: ${esc(date(runs[0].fetched_at))} · Seçili çekim: ${esc(date(run.fetched_at))}<br>Kaynak güncellemesi: ${shown(run.source_updated)}</p>
      <div class="stage-note" id="restaurant-diff" role="status"><p>Sürüm farkı yükleniyor…</p></div>
      <div class="workspace-grid"><section class="library" aria-label="Toplanan restoran verileri"><div class="library-title"><h2>Restoran dizini</h2><small id="restaurant-count">Yükleniyor…</small></div>
      <div class="toolbar restaurant-toolbar"><div class="search-wrap"><span aria-hidden="true">⌕</span><input id="restaurant-search" type="search" aria-label="Restoran ara" placeholder="Ad, adres veya açıklama ara…" value="${esc(this.filters.search)}"></div><select id="restaurant-neighborhood" aria-label="Mahalle filtresi"></select><select id="restaurant-cuisine" aria-label="Mutfak türü filtresi"></select><select id="restaurant-meal" aria-label="Öğün filtresi"></select></div>
      <div class="table-scroll"><table><thead><tr><th>RESTORAN</th><th>KAYNAK MAHALLE</th><th>MUTFAK TÜRÜ</th></tr></thead><tbody id="restaurant-rows"><tr><td colspan="3">Kayıtlar yükleniyor…</td></tr></tbody></table></div></section><section class="detail" id="restaurant-detail" aria-label="Restoran ayrıntıları"></section></div>`:
      `<section class="quality-result empty"><h2>İlk restoran çekimi hazır</h2><p>“Restoran verilerini topla” ile 13 mahallenin restoran dizinini kaydet. Her başarılı çekim ayrı sürüm olarak korunur.</p></section>`)+
      `<div class="stage-note"><p>Miramar Beach, Seascape ve Sandestin kapsam dışında. Mahalle bilgisi, restoranın bulunduğu kaynak filtresinden gelir; adresinden tahmin edilmez. Menü, fiyat ve değerlendirme puanı toplanmaz. İşletmelerin kendi siteleri ziyaret edilmez.</p></div>`;
    if(!run) return;
    main.querySelector('#restaurant-version').addEventListener('change',e=>{this.selectedRun=e.target.value;this.render(main,data,heading);});
    api(`restaurant-runs/${run.id}`).then(snapshot=>{
      if(sequence!==this.sequence) return;
      this.snapshot=snapshot;
      const diff=snapshot.diff;
      main.querySelector('#restaurant-diff').textContent=diff.available?`Önceki başarılı sürüme göre: ${diff.added} eklendi · ${diff.removed} kaldırıldı · ${diff.changed} değişti · ${diff.unchanged} aynı${diff.connector_version_changed?" · Toplayıcı sürümü değişti; bazı farklar ayrıştırmadan kaynaklanabilir.":""}`:diff.reason;
      for(const [key,field,label] of [["neighborhood","source_neighborhoods","Tüm mahalleler"],["cuisine","cuisines","Tüm mutfak türleri"],["meal","meals_served","Tüm öğünler"]]) {
        const values=[...new Set(snapshot.records.flatMap(r=>r[field]))].sort();
        if(!values.includes(this.filters[key])) this.filters[key]="";
        const select=main.querySelector(`#restaurant-${key}`);
        select.innerHTML=`<option value="">${label}</option>`+values.map(v=>`<option value="${esc(v)}" ${v===this.filters[key]?"selected":""}>${esc(v)}</option>`).join("");
        select.addEventListener('change',e=>{this.filters[key]=e.target.value;this.rows(main);});
      }
      main.querySelector('#restaurant-search').addEventListener('input',e=>{this.filters.search=e.target.value;this.rows(main);});
      main.querySelector('#restaurant-rows').addEventListener('click',e=>{const b=e.target.closest('[data-restaurant-id]');if(b){this.selectedRecord=b.dataset.restaurantId;this.rows(main);}});
      this.rows(main);
    }).catch(e=>{if(sequence===this.sequence) main.querySelector('#restaurant-rows').innerHTML=`<tr><td colspan="3">${esc(e.message)}</td></tr>`;});
  }
  rows(main) {
    const records=filterRestaurants(this.snapshot.records,this.filters);
    if(!records.some(r=>r.external_id===this.selectedRecord)) this.selectedRecord=records[0]?.external_id || null;
    main.querySelector('#restaurant-count').textContent=`${records.length} / ${this.snapshot.records.length} kayıt`;
    main.querySelector('#restaurant-rows').innerHTML=records.length?records.map(r=>`<tr class="${r.external_id===this.selectedRecord?"selected":""}"><td><button class="source-name" data-restaurant-id="${esc(r.external_id)}" aria-pressed="${r.external_id===this.selectedRecord}">${esc(r.name)}</button><div class="source-host">${shown(r.address_line_1)}</div></td><td>${esc(r.source_neighborhoods.join(", "))}</td><td>${shown(r.cuisines.join(", "))}</td></tr>`).join(""):'<tr><td colspan="3">Bu filtrelere uyan restoran yok.</td></tr>';
    const r=records.find(r=>r.external_id===this.selectedRecord);
    main.querySelector('#restaurant-detail').innerHTML=r?`<span class="eyebrow">RESTORAN</span><h2>${esc(r.name)}</h2>${restaurantLink(r.listing_url,"Visit South Walton detay sayfası")}<p>${shown(r.description)}</p>
      <dl><div><dt>Kaynak mahalle / bölge kimliği</dt><dd>${r.regions.map(region=>`${esc(region.source_neighborhood)} / ${shown(region.canonical_region_id)}`).join("<br>")}</dd></div><div><dt>Adres</dt><dd>${shown(restaurantAddress(r))}</dd></div><div><dt>Telefon</dt><dd>${shown(r.phone)}</dd></div><div><dt>E-posta</dt><dd>${shown(r.email)}</dd></div><div><dt>Web sitesi</dt><dd>${restaurantLink(r.website_url,r.website_url)}</dd></div></dl>
      <div class="features-detail"><h3>Mutfak türü · Cuisine</h3>${pills(r.cuisines)}<h3>Öğünler · Meals served</h3>${pills(r.meals_served)}<h3>Diğer olanaklar</h3>${pills(r.amenities)}</div><div class="detail-foot">Kaynak kimliği: ${esc(r.external_id)}<br>Çekim: ${esc(date(this.snapshot.run.fetched_at))}<br>Kaynakta yayımlanan bilgiler aktarılmıştır.</div>`:'<div class="empty"><h3>Kayıt bulunamadı</h3><p>Diğer restoranları görmek için filtreleri değiştir.</p></div>';
  }
}
