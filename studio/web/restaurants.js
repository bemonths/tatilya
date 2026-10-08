import {destinationRows} from "./destinations.js";
import {api, esc, date} from "./api.js";
import {collectionTabs} from "./connectors.js";

export const SITE_CONNECTOR="restaurant-sites";
export const RESERVATION_LABELS={online:"çevrim içi",phone:"telefonla",not_taken:"alınmıyor",waitlist:"bekleme listesi"};
export const YES_NO={yes:"evet",no:"hayır"};
export const SITE_STATUS_LABELS={working:"site çalışıyor",not_found:"site bulunamadı",closed_permanently:"site kalıcı olarak kapandığını söylüyor",
  closed_season:"site sezon için kapalı olduğunu söylüyor",other_business:"alan adı başka işletmeye/satışa ait",unreachable:"siteye ulaşılamadı",
  social_login:"sosyal medya sayfası; girişsiz okunamadı",no_site:"web sitesi yok"};
export const MENU_TYPE_LABELS={dinner:"akşam",lunch:"öğle",general:"genel",brunch:"brunch",breakfast:"kahvaltı",kids:"çocuk",drinks:"içecek",dessert:"tatlı",happy_hour:"happy hour"};
export const FORMAT_LABELS={html:"web sayfası",pdf:"PDF",image:"görüntü",platform:"platform"};
export const SECTION_LABELS={ana_yemek:"ana yemek",baslangic:"başlangıç",salata_corba:"salata/çorba",tatli:"tatlı",icecek:"içecek",cocuk:"çocuk",yan_urun:"yan ürün",diger:"diğer"};
const FACT_LABELS={hours:"Çalışma saatleri",reservation:"Rezervasyon",kids_menu:"Çocuk menüsü",outdoor_seating:"Açık hava oturma",water_view:"Su kenarı / manzara",
  dog_friendly:"Köpek dostu",site_price_range:"Sitenin kendi fiyat aralığı ifadesi"};
const usd=value=>value==null?"—":`$${Number(value).toLocaleString("en-US",{minimumFractionDigits:value%1?2:0,maximumFractionDigits:2})}`;

export function restaurantAddress(record) {
  return [record.address_line_1,record.address_line_2,record.city,record.state,record.postal_code].filter(Boolean).join(", ");
}
/** Directory filters plus, when the business-site run is loaded, price level, reservation and kids menu ("" = all, "none" = unknown). */
export function filterRestaurants(records, {search="",neighborhood="",cuisine="",meal="",level="",reservation="",kids=""}={}, sites={}) {
  const query=search.trim().toLocaleLowerCase("en-US");
  return records.filter(record=>{
    const site=sites[record.external_id] || {};
    return (!neighborhood || record.source_neighborhoods.includes(neighborhood)) &&
      (!cuisine || record.cuisines.includes(cuisine)) && (!meal || record.meals_served.includes(meal)) &&
      (!level || (level==="none"?!site.price_level:site.price_level===level)) &&
      (!reservation || (reservation==="none"?!site.reservation:site.reservation===reservation)) &&
      (!kids || (kids==="none"?!site.kids_menu:site.kids_menu===kids)) &&
      `${record.name} ${restaurantAddress(record)} ${record.description || ""}`.toLocaleLowerCase("en-US").includes(query);
  });
}
export function restaurantLink(url, label) {
  try { if(!["http:","https:"].includes(new URL(url).protocol)) return "Belirtilmemiş"; }
  catch { return "Belirtilmemiş"; }
  return `<a class="source-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`;
}
const shown=value=>esc(value || "Belirtilmemiş");
const pills=values=>values.length?values.map(v=>`<span class="feature-pill">${esc(v)}</span>`).join(""):"<p>Belirtilmemiş</p>";

/** Our price level with the main-dish median it comes from; nothing when the site gave fewer than five main-dish prices. */
export function levelCell(site) {
  if(!site) return '<span class="muted">—</span>';
  if(!site.price_level) return `<span class="muted">${site.main?.count?`hesaplanmadı (${site.main.count} ana yemek fiyatı)`:"bilinmiyor"}</span>`;
  return `<strong>${esc(site.price_level)}</strong><small>ana yemek ortancası ${usd(site.main.median)} · ${site.main.count} kalem</small>`;
}
export function reservationCell(site) {
  if(!site?.reservation) return '<span class="muted">bilinmiyor</span>';
  return `${esc(RESERVATION_LABELS[site.reservation] || site.reservation)}${site.reservation==="online" && site.reservation_platform?`<small>${esc(site.reservation_platform)}</small>`:""}`;
}
export function kidsCell(site) {
  return site?.kids_menu?esc(YES_NO[site.kids_menu] || site.kids_menu):'<span class="muted">bilinmiyor</span>';
}
function stamp(fact) {
  return `<small class="source-stamp">${restaurantLink(fact.source_url,"kaynak")} · ${esc(date(fact.fetched_at))} · ${esc(fact.method)} · SHA-256 ${esc((fact.raw_sha256 || "").slice(0,10))}</small>`;
}
export function factLine(field, fact) {
  if(!fact) return `<div><dt>${FACT_LABELS[field]}</dt><dd class="muted">bilinmiyor</dd></div>`;
  let value=fact.value;
  if(field==="reservation") value=RESERVATION_LABELS[fact.value] || fact.value;
  else if(["kids_menu","outdoor_seating","water_view","dog_friendly"].includes(field)) value=YES_NO[fact.value] || fact.value;
  else if(field==="hours") value="işletmenin sitesinde yazan";
  const days=fact.data && field==="hours"?`<table class="hours-table"><tbody>${Object.entries(fact.data).map(([day,span])=>`<tr><td>${esc(day)}</td><td>${esc(span)}</td></tr>`).join("")}</tbody></table>`:"";
  const link=fact.link_url?` ${restaurantLink(fact.link_url,fact.detail || "bağlantı")}`:"";
  return `<div><dt>${FACT_LABELS[field]}</dt><dd>${esc(value)}${link}${fact.detail && !fact.link_url?`<br><small>“${esc(fact.detail)}”</small>`:""}${days}${stamp(fact)}</dd></div>`;
}
/** Everything read from the business's own site, each value with its source. */
export function siteDetail(detail, levelNote="") {
  if(!detail) return "";
  const menus=detail.menus || [], items=detail.items || [];
  const main=detail.main_menu_id?menus.find(m=>m.menu_id===detail.main_menu_id):null;
  const mainLine=detail.price_level?`<p><strong>${esc(detail.price_level)}</strong> · ana yemek ortancası ${usd(detail.main.median)} (${usd(detail.main.min)}–${usd(detail.main.max)}, ${detail.main.count} kalem) · ${esc(MENU_TYPE_LABELS[main?.menu_type] || "")} menüsünden</p>`:
    `<p class="muted">Fiyat seviyesi hesaplanmadı${detail.main?.count?` (ana yemek menüsünde ${detail.main.count} fiyat; en az 5 gerekir)`:""}.</p>`;
  return `<section class="site-facts"><h3>İşletmenin kendi sitesi</h3><p>${esc(SITE_STATUS_LABELS[detail.site_status] || detail.site_status)}${detail.site_url?` · ${restaurantLink(detail.final_url || detail.site_url,detail.site_source==="review"?"resmî site (web aramasıyla bulundu)":"resmî site")}`:""}${detail.status_note?`<br><small>${esc(detail.status_note)}</small>`:""}</p>
    ${mainLine}<p class="source-stamp">${esc(levelNote)}</p>
    <dl>${Object.keys(FACT_LABELS).map(field=>factLine(field,detail.facts?.[field])).join("")}</dl>
    <h3>Menüler</h3>${menus.length?`<ul class="menu-list">${menus.map(m=>`<li>${restaurantLink(m.url,m.title || MENU_TYPE_LABELS[m.menu_type] || "menü")} <small>${esc(MENU_TYPE_LABELS[m.menu_type] || m.menu_type)} · ${esc(FORMAT_LABELS[m.format] || m.format)}${m.platform?` (${esc(m.platform)})`:""} · ${m.status==="read"?`${m.item_count} kalem · ${esc(m.method || "")}`:esc(m.message || m.status)}${m.menu_id===detail.main_menu_id?" · fiyat seviyesi bu menüden":""}</small></li>`).join("")}</ul>`:'<p class="muted">Sitede menü bulunamadı.</p>'}
    ${main?`<details><summary>${esc(MENU_TYPE_LABELS[main.menu_type] || "")} menüsündeki ana yemekler</summary><table class="lodging-table"><tbody>${items.filter(i=>i.menu_id===main.menu_id && i.section_class==="ana_yemek").map(i=>`<tr><td>${esc(i.name)}<small>${esc(i.section || "")}</small></td><td>${esc(i.price_text || "")}${i.price_rule==="lowest"?" <small>(en düşük)</small>":""}</td></tr>`).join("")}</tbody></table></details>`:""}</section>`;
}
/** Neighborhood summary of the business-site run. */
export function regionSummary(summary) {
  if(!summary?.regions?.length) return "";
  return `<section class="library climate-block"><div class="library-title"><h2>Mahalle özeti · işletme siteleri</h2><small>${esc(summary.level_note)}</small></div>
    <div class="table-scroll"><table class="lodging-table"><thead><tr><th>MAHALLE</th><th>RESTORAN</th><th>$</th><th>$$</th><th>$$$</th><th>$$$$</th><th>ANA YEMEK ORTANCALARININ ORTANCASI</th><th>ÇEVRİM İÇİ REZERVASYON</th><th>ÇOCUK MENÜSÜ</th><th>BİLGİ BULUNAMADI</th></tr></thead>
    <tbody>${summary.regions.map(r=>`<tr><td>${esc(r.region_name)}</td><td>${r.restaurant_count}</td>${["$","$$","$$$","$$$$"].map(l=>`<td>${r.levels[l]}</td>`).join("")}<td>${usd(r.median_of_medians)}</td><td>${r.online_reservation}</td><td>${r.kids_menu}</td><td>${r.no_information}</td></tr>`).join("")}</tbody></table></div>
    <p class="source-stamp">${esc(summary.hours_note)} · Bir mahalledeki restoran sayısı, dizinin o mahalle filtresinde gösterdiği restoranlardır.</p></section>`;
}

export class RestaurantScreen {
  constructor() {this.selectedRun=null;this.selectedRecord=null;this.filters={search:"",neighborhood:"",cuisine:"",meal:"",level:"",reservation:"",kids:""};this.sequence=0;
    this.siteSummary=null;this.sites={};this.details={};}
  invalidate() {this.sequence++;}
  render(main,data,heading) {
    data={...data,sources:destinationRows(data.sources,data.selected_destination),jobs:destinationRows(data.jobs,data.selected_destination),restaurant_runs:destinationRows(data.restaurant_runs,data.selected_destination),
      restaurant_site_runs:destinationRows(data.restaurant_site_runs || [],data.selected_destination)};
    const sequence=++this.sequence;
    const runs=data.restaurant_runs || [];
    if(!runs.some(r=>r.id===this.selectedRun)) this.selectedRun=runs[0]?.id || null;
    const run=runs.find(r=>r.id===this.selectedRun);
    const siteRun=data.restaurant_site_runs[0] || null;
    const source=data.sources.find(s=>s.enabled && s.connector?.name==="south-walton-restaurants");
    const siteSource=data.sources.find(s=>s.enabled && s.connector?.name===SITE_CONNECTOR);
    const busy=data.jobs.some(j=>j.source_id===source?.id && ["queued","running"].includes(j.status));
    const siteBusy=data.jobs.some(j=>j.source_id===siteSource?.id && ["queued","running"].includes(j.status));
    if(!source && !runs.length) {
      main.innerHTML=collectionTabs()+heading("Veri toplama", "Bu destinasyon için restoran kaynağı bağlı değil.");return;
    }
    main.innerHTML=collectionTabs("restaurants")+heading("Veri toplama",`${data.selected_destination?.name || "Seçili destinasyon"} boyunca restoranları, kaynakta listelenen mutfak türlerini ve iletişim bilgilerini; işletmelerin kendi sitelerinden menü fiyatlarını, saatleri ve rezervasyonu incele.`,
      `<button class="primary" data-action="collect-restaurants" ${!source || busy?"disabled":""}>${busy?"Toplama sürüyor…":"↓ Restoran verilerini topla"}</button>
       <button data-action="collect-restaurant-sites" ${!siteSource || siteBusy || !runs.length?"disabled":""}>${siteBusy?"Siteler okunuyor…":"↓ İşletme sitelerinden bilgi topla"}</button>`)+
      `<section class="connector-strip"><div><span class="eyebrow">BAĞLI KAYNAK</span><h2>${esc(source?.name || "South Walton · Restoranlar")}</h2><p>Visit South Walton · ${data.canonical_regions?.length ?? 0} mahalle · Yalnızca Restaurants${siteRun?` · İşletme siteleri ${esc(date(siteRun.fetched_at))} tarihinde okundu`:""}</p></div><span class="tag ${source?"green":"warm"}">${source?"HTML · bağlı":"Kaynak etkin değil"}</span></section>`+
      (run?`<section class="overview collection-overview">${[[run.record_count,"restoran","Seçili veri sürümünde"],[run.metadata.represented_neighborhood_count,"temsil edilen mahalle",`${run.metadata.target_neighborhood_count} hedef mahalle tarandı`],[run.metadata.cuisine_count,"mutfak türü","Kaynakta listelenen"]].map(([n,label,note])=>`<div class="metric"><div><div class="metric-number"><strong>${esc(n)}</strong><span class="metric-label">${label}</span></div><small>${note}</small></div></div>`).join("")}<div class="metric" id="restaurant-site-metric"></div></section>
      <div class="collection-version"><label>Sürüm <select id="restaurant-version" aria-label="Restoran veri sürümü">${runs.map((r,i)=>`<option value="${esc(r.id)}" ${r.id===run.id?"selected":""}>${i===0?"Son çekim · ":""}${esc(date(r.fetched_at))} · ${r.record_count} kayıt · ${r.id.slice(0,6)}</option>`).join("")}</select></label><a class="download-link" href="/api/restaurant-runs/${run.id}/raw" download>↓ Ham kaynak manifestini indir</a>${siteRun?`<a class="download-link" href="/api/restaurant-site-runs/${esc(siteRun.id)}/raw" download>↓ İşletme siteleri ham manifesti</a>`:""}</div>
      <p class="source-stamp">Son çekim: ${esc(date(runs[0].fetched_at))} · Seçili çekim: ${esc(date(run.fetched_at))}<br>Kaynak güncellemesi: ${shown(run.source_updated)}</p>
      <div class="stage-note" id="restaurant-diff" role="status"><p>Sürüm farkı yükleniyor…</p></div>
      <div class="workspace-grid"><section class="library" aria-label="Toplanan restoran verileri"><div class="library-title"><h2>Restoran dizini</h2><small id="restaurant-count">Yükleniyor…</small></div>
      <div class="toolbar restaurant-toolbar"><div class="search-wrap"><span aria-hidden="true">⌕</span><input id="restaurant-search" type="search" aria-label="Restoran ara" placeholder="Ad, adres veya açıklama ara…" value="${esc(this.filters.search)}"></div><select id="restaurant-neighborhood" aria-label="Mahalle filtresi"></select><select id="restaurant-cuisine" aria-label="Mutfak türü filtresi"></select><select id="restaurant-meal" aria-label="Öğün filtresi"></select>
        <select id="restaurant-level" aria-label="Fiyat seviyesi filtresi">${[["","Tüm fiyat seviyeleri"],["$","$"],["$$","$$"],["$$$","$$$"],["$$$$","$$$$"],["none","Hesaplanmadı"]].map(([v,l])=>`<option value="${v}" ${this.filters.level===v?"selected":""}>${l}</option>`).join("")}</select>
        <select id="restaurant-reservation" aria-label="Rezervasyon filtresi">${[["","Tüm rezervasyon durumları"],...Object.entries(RESERVATION_LABELS),["none","Bilinmiyor"]].map(([v,l])=>`<option value="${v}" ${this.filters.reservation===v?"selected":""}>${esc(l)}</option>`).join("")}</select>
        <select id="restaurant-kids" aria-label="Çocuk menüsü filtresi">${[["","Çocuk menüsü: tümü"],["yes","Çocuk menüsü var"],["none","Çocuk menüsü bilinmiyor"]].map(([v,l])=>`<option value="${v}" ${this.filters.kids===v?"selected":""}>${l}</option>`).join("")}</select></div>
      <div class="table-scroll"><table><thead><tr><th>RESTORAN</th><th>KAYNAK MAHALLE</th><th>MUTFAK TÜRÜ</th><th>FİYAT SEVİYESİ</th><th>REZERVASYON</th><th>ÇOCUK MENÜSÜ</th></tr></thead><tbody id="restaurant-rows"><tr><td colspan="6">Kayıtlar yükleniyor…</td></tr></tbody></table></div></section><section class="detail" id="restaurant-detail" aria-label="Restoran ayrıntıları"></section></div>
      <div id="restaurant-regions"></div>`:
      `<section class="quality-result empty"><h2>İlk restoran çekimi hazır</h2><p>“Restoran verilerini topla” ile yapılandırılmış mahallelerin restoran dizinini kaydet. Her başarılı çekim ayrı sürüm olarak korunur.</p></section>`)+
      `<div class="stage-note"><p>Miramar Beach, Seascape ve Sandestin kapsam dışında. Mahalle bilgisi, restoranın bulunduğu kaynak filtresinden gelir; adresinden tahmin edilmez. Değerlendirme puanı ve yorum platformları kullanılmaz. Menü, saat ve rezervasyon bilgileri yalnız işletmenin kendi sitesinden (ve yayımladığı menü/sipariş sayfalarından) alınır; sitenin söylemediği bilgi “bilinmiyor” kalır. Fiyat seviyesi bizim sınıflamamızdır.</p></div>`;
    if(!run) return;
    main.querySelector('#restaurant-version').addEventListener('change',e=>{this.selectedRun=e.target.value;this.render(main,data,heading);});
    const sitePromise=siteRun?(this.siteSummary?.run?.id===siteRun.id?Promise.resolve(this.siteSummary):api(`restaurant-site-runs/${siteRun.id}`)):Promise.resolve(null);
    Promise.all([api(`restaurant-runs/${run.id}`),sitePromise.catch(()=>null)]).then(([snapshot,summary])=>{
      if(sequence!==this.sequence) return;
      this.snapshot=snapshot;this.siteSummary=summary;
      this.sites=Object.fromEntries((summary?.restaurants || []).map(r=>[r.external_id,r]));
      const metric=main.querySelector('#restaurant-site-metric');
      if(metric) metric.innerHTML=summary?`<div><div class="metric-number"><strong>${summary.coverage.with_level}</strong><span class="metric-label">restoranda fiyat seviyesi</span></div><small>${summary.coverage.with_menu} restoranda menü · ${summary.coverage.with_hours} restoranda saat · ${summary.coverage.with_reservation} restoranda rezervasyon bilgisi</small></div>`:
        `<div><div class="metric-number"><strong>—</strong><span class="metric-label">işletme sitesi bilgisi yok</span></div><small>“İşletme sitelerinden bilgi topla” ile okunur</small></div>`;
      const regions=main.querySelector('#restaurant-regions');
      if(regions) regions.innerHTML=regionSummary(summary);
      const diff=snapshot.diff;
      main.querySelector('#restaurant-diff').textContent=diff.available?`Önceki başarılı sürüme göre: ${diff.added} eklendi · ${diff.removed} kaldırıldı · ${diff.changed} değişti · ${diff.unchanged} aynı${diff.connector_version_changed?" · Toplayıcı sürümü değişti; bazı farklar ayrıştırmadan kaynaklanabilir.":""}`:diff.reason;
      for(const [key,field,label] of [["neighborhood","source_neighborhoods","Tüm mahalleler"],["cuisine","cuisines","Tüm mutfak türleri"],["meal","meals_served","Tüm öğünler"]]) {
        const values=[...new Set(snapshot.records.flatMap(r=>r[field]))].sort();
        if(!values.includes(this.filters[key])) this.filters[key]="";
        const select=main.querySelector(`#restaurant-${key}`);
        select.innerHTML=`<option value="">${label}</option>`+values.map(v=>`<option value="${esc(v)}" ${v===this.filters[key]?"selected":""}>${esc(v)}</option>`).join("");
        select.addEventListener('change',e=>{this.filters[key]=e.target.value;this.rows(main);});
      }
      for(const key of ["level","reservation","kids"]) main.querySelector(`#restaurant-${key}`).addEventListener('change',e=>{this.filters[key]=e.target.value;this.rows(main);});
      main.querySelector('#restaurant-search').addEventListener('input',e=>{this.filters.search=e.target.value;this.rows(main);});
      main.querySelector('#restaurant-rows').addEventListener('click',e=>{const b=e.target.closest('[data-restaurant-id]');if(b){this.selectedRecord=b.dataset.restaurantId;this.rows(main);}});
      this.rows(main);
    }).catch(e=>{if(sequence===this.sequence) main.querySelector('#restaurant-rows').innerHTML=`<tr><td colspan="6">${esc(e.message)}</td></tr>`;});
  }
  rows(main) {
    const records=filterRestaurants(this.snapshot.records,this.filters,this.sites);
    if(!records.some(r=>r.external_id===this.selectedRecord)) this.selectedRecord=records[0]?.external_id || null;
    main.querySelector('#restaurant-count').textContent=`${records.length} / ${this.snapshot.records.length} kayıt`;
    main.querySelector('#restaurant-rows').innerHTML=records.length?records.map(r=>`<tr class="${r.external_id===this.selectedRecord?"selected":""}"><td><button class="source-name" data-restaurant-id="${esc(r.external_id)}" aria-pressed="${r.external_id===this.selectedRecord}">${esc(r.name)}</button><div class="source-host">${shown(r.address_line_1)}</div></td><td>${esc(r.source_neighborhoods.join(", "))}</td><td>${shown(r.cuisines.join(", "))}</td><td>${levelCell(this.sites[r.external_id])}</td><td>${reservationCell(this.sites[r.external_id])}</td><td>${kidsCell(this.sites[r.external_id])}</td></tr>`).join(""):'<tr><td colspan="6">Bu filtrelere uyan restoran yok.</td></tr>';
    const r=records.find(r=>r.external_id===this.selectedRecord);
    main.querySelector('#restaurant-detail').innerHTML=r?`<span class="eyebrow">RESTORAN</span><h2>${esc(r.name)}</h2>${restaurantLink(r.listing_url,"Visit South Walton detay sayfası")}<p>${shown(r.description)}</p>
      <dl><div><dt>Kaynak mahalle / bölge kimliği</dt><dd>${r.regions.map(region=>`${esc(region.source_neighborhood)} / ${shown(region.canonical_region_id)}`).join("<br>")}</dd></div><div><dt>Adres</dt><dd>${shown(restaurantAddress(r))}</dd></div><div><dt>Telefon</dt><dd>${shown(r.phone)}</dd></div><div><dt>E-posta</dt><dd>${shown(r.email)}</dd></div><div><dt>Web sitesi</dt><dd>${restaurantLink(r.website_url,r.website_url)}</dd></div></dl>
      <div class="features-detail"><h3>Mutfak türü · Cuisine</h3>${pills(r.cuisines)}<h3>Öğünler · Meals served</h3>${pills(r.meals_served)}<h3>Diğer olanaklar</h3>${pills(r.amenities)}</div><div id="restaurant-site-detail">${this.siteSummary?'<p>İşletme sitesi bilgileri yükleniyor…</p>':""}</div><div class="detail-foot">Kaynak kimliği: ${esc(r.external_id)}<br>Çekim: ${esc(date(this.snapshot.run.fetched_at))}<br>Kaynakta yayımlanan bilgiler aktarılmıştır.</div>`:'<div class="empty"><h3>Kayıt bulunamadı</h3><p>Diğer restoranları görmek için filtreleri değiştir.</p></div>';
    if(r && this.siteSummary) this.siteDetail(main,r.external_id);
  }
  siteDetail(main,externalId) {
    const box=main.querySelector('#restaurant-site-detail'), runId=this.siteSummary.run.id, key=`${runId}|${externalId}`;
    const draw=detail=>{if(box && this.selectedRecord===externalId) box.innerHTML=detail?siteDetail(detail,this.siteSummary.level_note):'<p class="muted">Bu restoran işletme sitesi sürümünde yok.</p>';};
    if(this.details[key]!==undefined) {draw(this.details[key]);return;}
    api(`restaurant-site-runs/${runId}/restaurant?external_id=${encodeURIComponent(externalId)}`).then(detail=>{this.details[key]=detail;draw(detail);})
      .catch(()=>{this.details[key]=null;draw(null);});
  }
}
