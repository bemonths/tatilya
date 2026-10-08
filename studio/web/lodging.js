import {destinationRows} from "./destinations.js";
import {api, esc, date} from "./api.js";
import {collectionTabs} from "./connectors.js";

export const LODGING_CONNECTOR="bookdirect-lodging";
export const SOURCE_LABELS={liste:"liste",canli:"canlı",takvim:"takvim"};
const MONTHS=["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];
const active=job=>["queued","running"].includes(job.status);

/** US dollars without cents; a missing price stays visibly missing. */
export function usd(value) {
  return value==null || !Number.isFinite(Number(value))?null:`$${new Intl.NumberFormat("en-US",{maximumFractionDigits:0}).format(Number(value))}`;
}
export function percent(share) {
  return share==null?null:`%${new Intl.NumberFormat("tr-TR",{maximumFractionDigits:0}).format(share*100)}`;
}
export function plain(value, digits=1) {
  return value==null?null:new Intl.NumberFormat("tr-TR",{maximumFractionDigits:digits}).format(Number(value));
}
export function monthLabel(month) {
  const [year,number]=String(month).split("-");
  return `${MONTHS[Number(number)-1] || number} ${year}`;
}
export function windowHeader(window) {
  return `${esc(window.label)}<small>${esc(window.checkin)} → ${esc(window.checkout)} · ${window.nights} gece</small>`;
}
/** One region x window cell: listing count, priced share and the nightly price median with its quartiles. */
export function summaryCell(cell) {
  if(!cell || cell.status==="skipped_past") return '<span class="muted">Geçmiş tarih; aranmadı</span>';
  if(!cell.listing_count) return '<span class="muted">Aramada ilan görünmedi</span>';
  const price=cell.price_median==null?'<small>Fiyat bilgisi yok</small>':
    `<strong>${usd(cell.price_median)}</strong><small>gecelik ortanca · ${usd(cell.price_q1)}–${usd(cell.price_q3)}</small>`;
  return `<span class="lodging-count">${cell.listing_count} ilan</span><small>fiyatlı ${cell.priced_count} (${percent(cell.priced_share)})</small>${price}`;
}
export function sourceCounts(sources) {
  return Object.entries(SOURCE_LABELS).map(([key,label])=>`${label} ${sources?.[key] ?? 0}`).join(" · ");
}
export function categoryList(categories) {
  const entries=Object.entries(categories || {});
  return entries.length?entries.map(([name,count])=>`${esc(name)} ${count}`).join(" · "):'<span class="muted">Kaynakta tür belirtilmemiş</span>';
}
export function bedroomText(cell) {
  if(!cell?.bedrooms_known) return '<span class="muted">Kaynakta yok</span>';
  return `ortanca ${plain(cell.bedrooms_median)} · 4+ oda ${percent(cell.bedrooms_4_plus_share)} <small>${cell.bedrooms_known}/${cell.listing_count} ilanda belirtilmiş</small>`;
}
/** Source categories of a listing without the clone's catch-all default category. */
export function listingCategories(listing, defaultCategory) {
  const names=(listing.category_names || []).filter((_,index)=>listing.category_ids?.[index]!==defaultCategory);
  return names.length?names.map(esc).join(", "):'<span class="muted">Belirtilmemiş</span>';
}
export function priceTag(window) {
  if(!window) return '<span class="muted">Bu pencerede görünmedi</span>';
  if(window.price==null) return '<span class="muted">Fiyat yok</span>';
  return `${usd(window.price)}<small>${esc(SOURCE_LABELS[window.price_source] || window.price_source)}${window.los?` · en az ${window.los} gece`:""}</small>`;
}
/** The rental company's own listing page (https or http as published); anything else stays plain text. */
export function companyLink(url) {
  try {
    const parsed=new URL(url);
    if(["https:","http:"].includes(parsed.protocol)) return `<a class="source-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Şirketin ilan sayfası · ${esc(parsed.hostname.replace(/^www\./,""))} ↗</a>`;
  } catch { /* plain text below */ }
  return esc(url || "");
}
export function regionMonthly(monthly, regionId) {
  return (monthly || []).filter(row=>row.region_id===regionId);
}

export class LodgingScreen {
  constructor(agency=null) {this.agency=agency;this.selectedRun=null;this.selectedRegion=null;this.selectedListing=null;this.snapshot=null;this.listings=null;this.sequence=0;}
  invalidate() {this.sequence++;this.agency?.invalidate();}
  render(main,data,heading) {
    data={...data,sources:destinationRows(data.sources,data.selected_destination),jobs:destinationRows(data.jobs,data.selected_destination),
      lodging_runs:destinationRows(data.lodging_runs || [],data.selected_destination)};
    const sequence=++this.sequence;
    const runs=data.lodging_runs;
    if(!runs.some(r=>r.id===this.selectedRun)) {this.selectedRun=runs[0]?.id || null;this.snapshot=null;this.listings=null;}
    const run=runs.find(r=>r.id===this.selectedRun);
    const source=data.sources.find(s=>s.enabled && s.connector?.name===LODGING_CONNECTOR);
    const busy=data.jobs.some(j=>j.source_id===source?.id && active(j));
    const config=data.lodging_connector?.config;
    if(!source && !runs.length) {
      main.innerHTML=collectionTabs("lodging")+heading("Veri toplama","Bu destinasyon için konaklama kaynağı (Book>Direct) bağlı değil.");return;
    }
    const windows=(config?.windows || []).map(w=>`${esc(w.label)} (${esc(w.checkin)} → ${esc(w.checkout)})`).join(" · ");
    main.innerHTML=collectionTabs("lodging")+heading("Veri toplama",`${data.selected_destination?.name || "Seçili destinasyon"} mahallelerinde belirli tarihlerdeki aramalarda görünen konaklamalar: tür, büyüklük ve kaynağın verdiği fiyatlar.`,
      `<button class="primary" data-action="collect-lodging" ${!source || busy?"disabled":""}>${busy?"Toplama sürüyor…":"↓ Konaklama aramalarını topla"}</button>`)+
      `<section class="connector-strip"><div><span class="eyebrow">BAĞLI KAYNAK</span><h2>${esc(source?.name || "Konaklama (Book>Direct)")}</h2><p>${esc(config?.clone_host || "")} · ${Object.keys(config?.locations || {}).length} konum filtresi · ${windows || "tarih penceresi yok"}</p></div><span class="tag ${source?"green":"warm"}">${source?"JSON · bağlı":"Kaynak etkin değil"}</span></section>`+
      (run?`<div class="collection-version"><label>Sürüm <select id="lodging-version" aria-label="Konaklama veri sürümü">${runs.map((r,i)=>`<option value="${esc(r.id)}" ${r.id===run.id?"selected":""}>${i===0?"Son çekim · ":""}${esc(date(r.fetched_at))} · ${r.record_count} ilan · ${esc(r.id.slice(0,6))}</option>`).join("")}</select></label><a class="download-link" href="/api/lodging-runs/${esc(run.id)}/raw" download>↓ Ham kaynak manifestini indir</a></div>
      <div id="lodging-body" aria-live="polite"><p>Özet yükleniyor…</p></div>`:
      `<section class="quality-result empty"><h2>İlk konaklama çekimi hazır</h2><p>“Konaklama aramalarını topla” her tarih penceresinde her mahalle filtresinin bütün sayfalarını, canlı fiyatları ve her ilanın fiyat takvimini okur. İstekler sıralıdır ve aralıklıdır; çekim uzun sürebilir. Her başarılı çekim ayrı sürüm olarak korunur.</p></section>`)+
      `<div class="stage-note"><p>${esc(data.lodging_connector?.scope || "")} Kaynağın istemci anahtarı her çekimde ön yüz paketinden okunur ve hiçbir yere yazılmaz. Mahalle, kaynağın konum filtresinin adından gelir; adres veya koordinattan mahalle çıkarılmaz.</p></div>`+
      '<div id="agency-prices"></div>';
    this.agency?.render(main.querySelector("#agency-prices"),data);
    if(!run) return;
    main.querySelector("#lodging-version").addEventListener("change",event=>{this.selectedRun=event.target.value;this.snapshot=null;this.selectedRegion=null;this.listings=null;this.render(main,data,heading);});
    const draw=()=>this.draw(main);
    if(this.snapshot?.run?.id===run.id) {draw();return;}
    api(`lodging-runs/${run.id}`).then(snapshot=>{
      if(sequence!==this.sequence) return;
      this.snapshot=snapshot;draw();
    }).catch(error=>{if(sequence===this.sequence) main.querySelector("#lodging-body").textContent=error.message;});
  }
  draw(main) {
    const body=main.querySelector("#lodging-body"), snap=this.snapshot;
    if(!body || !snap) return;
    const searched=snap.windows.filter(w=>w.status==="searched");
    const cells=Object.fromEntries(snap.cells.map(c=>[`${c.region_id}|${c.window_key}`,c]));
    const skipped=snap.windows.filter(w=>w.status==="skipped_past");
    body.innerHTML=`<section class="overview collection-overview">${[[snap.snapshot.listing_count,"benzersiz ilan","Bütün pencere ve filtrelerde"],[searched.length,"tarih penceresi aranıyor",skipped.length?`${skipped.length} geçmiş pencere atlandı`:"Geçmiş pencere yok"],
        [snap.regions.length,"mahalle","Konum filtresi adıyla"],[snap.snapshot.request_count,"istek",`Arama günü ${snap.snapshot.searched_on}`]].map(([n,label,note])=>`<div class="metric"><div><div class="metric-number"><strong>${esc(n)}</strong><span class="metric-label">${esc(label)}</span></div><small>${esc(note)}</small></div></div>`).join("")}</section>
      <div class="stage-note lodging-label"><p><strong>${esc(snap.label)}</strong></p></div>
      <section class="library climate-block"><div class="library-title"><h2>Mahalle × tarih penceresi</h2><small>Bir mahalleye tıklayınca ilanları ve aylık takvim fiyatları açılır.</small></div>
      <div class="table-scroll"><table class="lodging-table"><thead><tr><th>MAHALLE</th>${snap.windows.map(w=>`<th>${windowHeader(w)}</th>`).join("")}</tr></thead>
      <tbody>${snap.regions.map(region=>`<tr class="${region.region_id===this.selectedRegion?"selected":""}"><td><button class="source-name" data-lodging-region="${esc(region.region_id)}">${esc(region.region_name)}</button><small>${region.filters.map(esc).join(", ")}</small></td>
        ${snap.windows.map(w=>`<td>${summaryCell(cells[`${region.region_id}|${w.window_key}`])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
      <p class="source-stamp">Fiyat önceliği: güncel canlı fiyat (ön yüz arama fiyatını bununla değiştirir), yoksa aramadaki liste fiyatı, yoksa diğer canlı yanıt, yoksa pencerenin bütün geceleri fiyatlıysa takvimin gecelik ortalaması. Çeyrekler arası aralık fiyatı olan ilanlardan hesaplanır (bizim hesabımız).</p></section>
      <div id="lodging-region"></div>`;
    body.querySelector(".lodging-table").addEventListener("click",event=>{
      const button=event.target.closest("[data-lodging-region]");
      if(button) {this.selectedRegion=button.dataset.lodgingRegion;this.selectedListing=null;this.listings=null;this.draw(main);}
    });
    if(this.selectedRegion) this.region(main);
  }
  region(main) {
    const target=main.querySelector("#lodging-region"), snap=this.snapshot, regionId=this.selectedRegion;
    const region=snap.regions.find(r=>r.region_id===regionId);
    if(!target || !region) return;
    const cells=snap.cells.filter(c=>c.region_id===regionId && c.status==="searched");
    const monthly=regionMonthly(snap.monthly,regionId);
    target.innerHTML=`<section class="library climate-block"><div class="library-title"><h2>${esc(region.region_name)}</h2><small>Konum filtreleri: ${region.filters.map(esc).join(", ")}</small></div>
      <div class="table-scroll"><table class="lodging-table"><thead><tr><th>PENCERE</th><th>İLAN</th><th>TÜR DAĞILIMI (kaynağın kategorileri)</th><th>YATAK ODASI</th><th>KAPASİTE ORTANCASI</th><th>FİYAT KAYNAĞI</th></tr></thead>
      <tbody>${cells.map(c=>{const w=snap.windows.find(x=>x.window_key===c.window_key);return `<tr><td>${windowHeader(w)}</td><td>${c.listing_count}</td><td>${categoryList(c.categories)}${c.no_category?`<small>${c.no_category} ilanda tür yok</small>`:""}</td><td>${bedroomText(c)}</td><td>${c.sleeps_median==null?'<span class="muted">Kaynakta yok</span>':`${plain(c.sleeps_median)} kişi`}</td><td>${sourceCounts(c.price_sources)}</td></tr>`;}).join("")}</tbody></table></div>
      <h3 class="climate-subtitle">Takvimden aylık ortanca gecelik fiyat (ilanların aylık ortancalarının ortancası; bizim hesabımız)</h3>
      ${monthly.length?`<div class="table-scroll"><table class="lodging-table"><thead><tr>${monthly.map(m=>`<th>${esc(monthLabel(m.month))}</th>`).join("")}</tr></thead><tbody><tr>${monthly.map(m=>`<td>${usd(m.median_rate)}<small>${m.listing_count} ilan</small></td>`).join("")}</tr></tbody></table></div>`:'<p class="muted">Bu mahallede fiyat takvimi dolu ilan yok.</p>'}
      <div id="lodging-listings"><p>İlanlar yükleniyor…</p></div></section>`;
    if(this.listings?.region_id===regionId) {this.listingTable(main);return;}
    const sequence=this.sequence;
    api(`lodging-runs/${snap.run.id}/listings?region_id=${encodeURIComponent(regionId)}`).then(result=>{
      if(sequence!==this.sequence || this.selectedRegion!==regionId) return;
      this.listings=result;this.listingTable(main);
    }).catch(error=>{const box=main.querySelector("#lodging-listings");if(box) box.textContent=error.message;});
  }
  listingTable(main) {
    const box=main.querySelector("#lodging-listings"), snap=this.snapshot;
    if(!box || !this.listings) return;
    const def=snap.snapshot.default_category_id, listings=this.listings.listings;
    box.innerHTML=`<h3 class="climate-subtitle">İlanlar · ${listings.length}</h3><div class="workspace-grid"><div class="table-scroll"><table class="lodging-table"><thead><tr><th>İLAN</th><th>TÜR</th><th>ODA / BANYO / KİŞİ</th>${snap.windows.filter(w=>w.status==="searched").map(w=>`<th>${esc(w.label)}</th>`).join("")}</tr></thead>
      <tbody>${listings.map(l=>`<tr class="${l.lodging_id===this.selectedListing?"selected":""}"><td><button class="source-name" data-lodging-listing="${l.lodging_id}">${esc(l.title)}</button><small>#${l.lodging_id} · ${l.filters.map(esc).join(", ")}</small></td><td>${listingCategories(l,def)}</td>
        <td>${[l.bedrooms,l.bathrooms,l.sleeps].map(v=>v==null?"—":plain(v)).join(" / ")}</td>${snap.windows.filter(w=>w.status==="searched").map(w=>`<td>${priceTag(l.windows[w.window_key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
      <section class="detail" id="lodging-detail" aria-label="İlan ayrıntısı"></section></div>`;
    box.querySelector("tbody").addEventListener("click",event=>{
      const button=event.target.closest("[data-lodging-listing]");
      if(button) {this.selectedListing=Number(button.dataset.lodgingListing);this.listingTable(main);}
    });
    this.detail(main);
  }
  detail(main) {
    const target=main.querySelector("#lodging-detail"), listing=this.listings?.listings.find(l=>l.lodging_id===this.selectedListing);
    if(!target) return;
    if(!listing) {target.innerHTML='<p class="muted">Ayrıntı için bir ilan seçin.</p>';return;}
    const def=this.snapshot.snapshot.default_category_id;
    const live=Object.entries(listing.windows).map(([key,w])=>`${esc(this.snapshot.windows.find(x=>x.window_key===key)?.label || key)}: ${w.live_status==="answered"?`canlı yanıt${w.live_average_rate_usd!=null?` ${usd(w.live_average_rate_usd)}`:" (fiyatsız)"}`:w.live_status==="no_answer"?"canlı fiyat sorulmuş, yanıt yok":"canlı fiyat sorulmadı"}`).join(" · ");
    target.innerHTML=`<span class="eyebrow">İLAN #${listing.lodging_id}</span><h2>${esc(listing.title)}</h2>
      <p>${[listing.address,listing.city,listing.state,listing.zip_code].filter(Boolean).map(esc).join(", ") || '<span class="muted">Adres kaynakta yok</span>'}</p>
      <p>Tür: ${listingCategories(listing,def)}<br>Yatak odası ${listing.bedrooms==null?"—":plain(listing.bedrooms)} · banyo ${listing.bathrooms==null?"—":plain(listing.bathrooms)} · kapasite ${listing.sleeps==null?"—":`${listing.sleeps} kişi`}</p>
      <p>Olanaklar (kaynakta listelenen): ${listing.amenities.length?listing.amenities.map(esc).join(", "):'<span class="muted">listelenmemiş</span>'}</p>
      <p>Rezervasyon sistemi: ${esc(listing.res_engine || "belirtilmemiş")}<br>${live}</p>
      ${listing.url?`<p>${companyLink(listing.url)}</p>`:'<p class="muted">Kaynakta şirket ilan sayfası yok</p>'}
      <p>Fiyat takvimi: ${listing.hide_rate_calendar?"kaynakta gizli (istenmedi)":listing.calendar?.status==="read"?`${listing.calendar.priced_days} fiyatlı gün (${esc(listing.calendar.requested_from)} → ${esc(listing.calendar.requested_to)})`:"kaynak takvim vermedi"}</p>
      ${listing.months.length?`<table class="lodging-table"><thead><tr><th>AY</th><th>FİYATLI GÜN</th><th>EN DÜŞÜK</th><th>ORTANCA</th><th>EN YÜKSEK</th><th>EN SIK MİN. GECE</th></tr></thead><tbody>${listing.months.map(m=>`<tr><td>${esc(monthLabel(m.month))}</td><td>${m.priced_days}</td><td>${usd(m.min_rate)}</td><td>${usd(m.median_rate)}</td><td>${usd(m.max_rate)}</td><td>${m.common_los ?? "—"}</td></tr>`).join("")}</tbody></table>`:""}`;
  }
}
