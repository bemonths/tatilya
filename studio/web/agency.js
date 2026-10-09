import {destinationRows} from "./destinations.js";
import {api, esc, date} from "./api.js";
import {usd, percent, windowHeader, companyLink} from "./lodging.js";

export const AGENCY_CONNECTOR="agency-lodging-rates";
export const PAGE_LABELS={matched:"şirket sitesinde ilan bulundu",not_found:"şirket sitesi sayfayı bulamadı (404)",no_listing:"bağlantı ilan sayfasına gitmiyor",
  off_site:"bağlantı başka siteye yönlendi",blocked:"site isteği reddetti",error:"siteye ulaşılamadı",not_queried:"sorulmadı (şirket durduruldu)",
  no_adapter:"bu şirketin sitesi için uyarlayıcı yok",no_url:"Book>Direct'te şirket bağlantısı yok"};
export const QUOTE_LABELS={priced:"fiyat alındı",unavailable:"müsait değil",restricted:"konaklama kuralına takıldı",no_price:"site fiyat göstermedi",error:"hata"};
export const COMPANY_LABELS={done:"tamamlandı",stopped_blocked:"site reddetti; durduruldu",stopped_errors:"siteye ulaşılamadı; durduruldu",
  verification_timeout:"doğrulama süresi doldu; atlandı",verification_unavailable:"doğrulama gerekti; atlandı",failed:"hata"};
export const METHOD_LABELS={link:"bağlantı",address:"adres",location:"konum"};
export const GUEST_RULES={two_adults:"2 yetişkin",bedrooms_x2:"oda × 2 yetişkin"};
const DAYS={1:"Pazartesi",2:"Salı",3:"Çarşamba",4:"Perşembe",5:"Cuma",6:"Cumartesi",7:"Pazar"};
const BUCKETS=[["1-2","1–2 oda"],["3","3 oda"],["4","4 oda"],["5+","5+ oda"]];
const active=job=>["queued","running"].includes(job.status);

/** ISO weekday numbers (1 = Monday) as Turkish day names. */
export function weekdays(days) {
  return (days || []).map(day=>DAYS[day] || String(day)).join(", ");
}
/** One region x window cell: how many listings were asked, how many got a price, availability and the 7-night total. */
export function agencyCell(cell) {
  if(!cell || cell.status==="skipped_past") return '<span class="muted">Geçmiş tarih; sorulmadı</span>';
  if(!cell.queried_count) return `<span class="muted">Sorgulanan ilan yok</span><small>${cell.listing_count} ilan · ${cell.linked_count} bağlantılı</small>${ownLine(cell)}`;
  const total=cell.total_median==null?'<small>Fiyat alınamadı</small>':
    `<strong>${usd(cell.total_median)}</strong><small>toplam ortanca · ${usd(cell.total_q1)}–${usd(cell.total_q3)}</small>${cell.nightly_median==null?"":`<small>kira gecelik ${usd(cell.nightly_median)}</small>`}`;
  return `<span class="lodging-count">${cell.queried_count} ilan soruldu</span><small>fiyatlı ${cell.priced_count} (${percent(cell.priced_share)}) · müsait ${cell.available_share==null?"—":percent(cell.available_share)}</small>${total}${methodLine(cell)}${ownLine(cell)}${publishedLine(cell)}`;
}
/** Priced listings by how they were tied to the company page (link, address, location); shown only when a non-link method priced one. */
export function methodLine(cell) {
  const by=cell?.by_method;
  if(!by || !(by.address || by.location)) return "";
  return `<small>eşleme: ${Object.entries(METHOD_LABELS).filter(([key])=>by[key]).map(([key,label])=>`${label} ${by[key]}`).join(" · ")}</small>`;
}
/** The community's homes from a company's own list (not on Book>Direct), counted apart. */
export function ownLine(cell) {
  const own=cell?.own;
  if(!cell?.own_listing_count || !own) return "";
  return `<small class="own-inventory">kendi envanteri: ${cell.own_listing_count} ev · fiyatlı ${own.priced_count}${own.total_median==null?"":` · ortanca ${usd(own.total_median)}`}</small>`;
}
/** A site's published seasonal rent (taxes and fees excluded); never mixed into the totals above. */
export function publishedLine(cell) {
  const rent=cell?.published;
  if(!rent?.count) return "";
  return `<small class="published-rent">yayımlanmış kira (vergi ve ücret hariç): ${rent.count} ilan · ortanca ${usd(rent.low_median)}–${usd(rent.high_median)}</small>`;
}
export function bedroomCell(cell) {
  if(!cell?.bedrooms) return '<span class="muted">—</span>';
  return BUCKETS.map(([key,label])=>{const b=cell.bedrooms[key];return `<small>${label}: ${b?.median==null?"—":`${usd(b.median)} (${b.count})`}</small>`;}).join("");
}
export function quoteTag(quote) {
  if(!quote) return '<span class="muted">Sorulmadı</span>';
  if(quote.status==="priced") return `${usd(quote.total ?? quote.rent)}<small>${quote.total==null?"kira":"toplam"}</small>`;
  return `<span class="muted">${esc(QUOTE_LABELS[quote.status] || quote.status)}</span>${quote.min_stay?`<small>en az ${quote.min_stay} gece</small>`:""}`;
}
/** The site's own price lines for one window; fields the site did not give are left out, never shown as zero. */
export function quoteBreakdown(quote, window) {
  if(!quote) return `<p class="muted">${esc(window?.label || "")}: sorulmadı.</p>`;
  const rows=[];
  if(quote.rent!=null) rows.push(["Kira",quote.rent]);
  for(const fee of quote.fees || []) rows.push([fee.name,fee.amount]);
  for(const tax of quote.tax_items || []) rows.push([tax.name,tax.amount]);
  if(quote.total!=null) rows.push(["<strong>Toplam (sitenin)</strong>",quote.total,true]);
  const rules=[quote.min_stay?`en az ${quote.min_stay} gece`:"",quote.checkin_days?.length?`giriş günü: ${weekdays(quote.checkin_days)}`:""].filter(Boolean).join(" · ");
  const excluded=(quote.excluded_items || []).map(item=>`${esc(item.name)} ${usd(item.amount)} (${esc(item.reason)})`).join("; ");
  return `<h3 class="climate-subtitle">${windowHeader(window)}</h3><p><span class="tag ${quote.status==="priced"?"green":"warm"}">${esc(QUOTE_LABELS[quote.status] || quote.status)}</span></p>
    ${rows.length?`<table class="lodging-table"><tbody>${rows.map(([name,amount,strong])=>`<tr><td>${strong?name:esc(name)}</td><td>${usd(amount)}</td></tr>`).join("")}</tbody></table>`:""}
    ${quote.status==="priced" && quote.total!=null?`<p class="source-stamp">${quote.total_includes_taxes===1?`Toplam = kira + ${quote.total_includes_fees?"ücretler + ":""}vergiler (kalemlerin toplamı sitenin toplamını tuttu; bizim kontrolümüz).`:"Sitenin toplamı kalemlerin toplamıyla doğrulanamadı."}</p>`:""}
    ${excluded?`<p class="source-stamp">Toplama dahil edilmeyen: ${excluded}</p>`:""}
    ${rules?`<p>Kural: ${esc(rules)} <small>(${quote.rule_source==="yanıt"?"sitenin yanıtından":"ilan sayfasının takviminden"})</small></p>`:""}
    ${quote.message?`<p class="muted">Site: ${esc(quote.message)}</p>`:""}
    <p class="source-stamp">Sorgu ${esc(date(quote.queried_at))} · ${esc(quote.currency || "para birimi belirtilmemiş")}</p>`;
}

function companyMethods(company) {
  const counts=company.match_counts;
  if(!counts || !(counts.address || counts.location)) return "";
  return `<small>${Object.entries(METHOD_LABELS).filter(([key])=>counts[key]).map(([key,label])=>`${label} ${counts[key]}`).join(" · ")}</small>`;
}
function companyList(company) {
  if(company.inventory_count==null) return '<span class="muted">—</span>';
  const own=company.own_count?`<small>kendi envanteri ${company.own_count} ev${company.own_outside?` · topluluk dışı ${company.own_outside} ev alınmadı`:""}${company.own_on_bookdirect?` · Book>Direct'te olan ${company.own_on_bookdirect} ev tekrar sayılmadı`:""}</small>`:"";
  return `${company.inventory_count} ilan${own}`;
}

export class AgencyPrices {
  constructor() {this.selectedRun=null;this.snapshot=null;this.selectedRegion=null;this.listings=null;this.selectedListing=null;this.sequence=0;}
  invalidate() {this.sequence++;}
  render(target,data) {
    if(!target) return;
    const runs=destinationRows(data.agency_runs || [],data.selected_destination);
    const source=data.sources.find(s=>s.enabled && s.connector?.name===AGENCY_CONNECTOR);
    if(!source && !runs.length) {target.innerHTML="";return;}
    const busy=data.jobs.some(j=>j.source_id===source?.id && active(j));
    if(!runs.some(r=>r.id===this.selectedRun)) {this.selectedRun=runs[0]?.id || null;this.snapshot=null;this.listings=null;}
    const run=runs.find(r=>r.id===this.selectedRun), sites=data.agency_connector?.sites || [];
    const sequence=++this.sequence;
    target.innerHTML=`<section class="connector-strip agency-strip"><div><span class="eyebrow">KİRALAMA ŞİRKETLERİNİN KENDİ SİTELERİ</span><h2>Konaklama fiyatları</h2>
      <p>${sites.filter(s=>s.enabled).length} şirket sitesi yapılandırılmış · ilan, Book>Direct'teki şirket bağlantısıyla bulunur; ad benzerliğiyle eşleme yapılmaz.</p></div>
      <button class="primary" data-action="collect-agency-rates" ${!source || busy?"disabled":""}>${busy?"Fiyatlar soruluyor…":"↓ Kiralama şirketi fiyatlarını topla"}</button></section>`+
      (run?`<div class="collection-version"><label>Fiyat sürümü <select id="agency-version" aria-label="Kiralama şirketi fiyat sürümü">${runs.map((r,i)=>`<option value="${esc(r.id)}" ${r.id===run.id?"selected":""}>${i===0?"Son sorgu · ":""}${esc(date(r.fetched_at))} · ${esc(r.id.slice(0,6))}</option>`).join("")}</select></label><a class="download-link" href="/api/agency-rate-runs/${esc(run.id)}/raw" download>↓ Ham yanıt manifestini indir</a></div><div id="agency-body" aria-live="polite"><p>Fiyat özeti yükleniyor…</p></div>`:
      `<section class="quality-result empty"><h2>Henüz fiyat sorgusu yok</h2><p>“Kiralama şirketi fiyatlarını topla”, son konaklama çekimindeki ilanların şirket bağlantılarını açar ve her tarih penceresi için sitenin kendi fiyat gösterimini sorar. Aynı siteye istekler sıralı ve aralıklıdır; çekim uzun sürebilir. Bir site insan doğrulaması isterse açılan tarayıcı penceresinde doğrulamayı sen tamamlarsın; İşler panelinde hangi sitenin beklediği görünür.</p></section>`);
    if(!run) return;
    target.querySelector("#agency-version").addEventListener("change",event=>{this.selectedRun=event.target.value;this.snapshot=null;this.selectedRegion=null;this.listings=null;this.render(target,data);});
    if(this.snapshot?.run?.id===run.id) {this.draw(target);return;}
    api(`agency-rate-runs/${run.id}`).then(snapshot=>{
      if(sequence!==this.sequence) return;
      this.snapshot=snapshot;this.draw(target);
    }).catch(error=>{if(sequence===this.sequence) {const body=target.querySelector("#agency-body");if(body) body.textContent=error.message;}});
  }
  draw(target) {
    const body=target.querySelector("#agency-body"), snap=this.snapshot;
    if(!body || !snap) return;
    const cov=snap.coverage, cells=Object.fromEntries(snap.cells.map(c=>[`${c.region_id}|${c.window_key}`,c]));
    const queried=snap.windows.filter(w=>w.status==="queried");
    const methods=cov.methods?Object.entries(METHOD_LABELS).map(([key,label])=>`${label} ${cov.methods[key] || 0}`).join(" · "):"";
    const metrics=[[cov.listings,"Book>Direct ilanı",`Girdi çekimi ${snap.snapshot.lodging_run_id.slice(0,6)}`],[cov.matched,"ilan şirket sitesinde bulundu",`${cov.listings-cov.no_url-cov.no_adapter} ilan yapılandırılmış şirketlere bağlı${methods?` · ${methods}`:""}`],
        [cov.priced_listings,"ilana fiyat alındı",`${cov.regions_with_price}/${cov.regions} mahallede`],[snap.snapshot.request_count,"istek",`Sorgu günü ${snap.snapshot.queried_on}`]];
    if(cov.own_listings) metrics.splice(3,0,[cov.own_listings,"ev şirketin kendi envanterinden",`${cov.own_priced} evde fiyat · Book>Direct'te olmayanlar`]);
    body.innerHTML=`<section class="overview collection-overview">${metrics.map(([n,label,note])=>`<div class="metric"><div><div class="metric-number"><strong>${esc(n)}</strong><span class="metric-label">${esc(label)}</span></div><small>${esc(note)}</small></div></div>`).join("")}</section>
      <div class="stage-note lodging-label"><p><strong>${esc(snap.label)}</strong> ${esc(snap.nightly_note)}</p>${snap.guest_label?`<p>${esc(snap.guest_label)}</p>`:""}${snap.source_note?`<p>${esc(snap.source_note)} ${esc(snap.published_note || "")}</p>`:""}</div>
      <section class="library climate-block"><div class="library-title"><h2>Fiyat · mahalle × tarih penceresi</h2><small>7 gecelik toplamın ortancası ve çeyrekler aralığı; bir mahalleye tıklayınca ilanlar açılır.</small></div>
      <div class="table-scroll"><table class="lodging-table agency-table"><thead><tr><th>MAHALLE</th>${snap.windows.map(w=>`<th>${windowHeader(w)}</th>`).join("")}</tr></thead>
      <tbody>${snap.regions.map(region=>`<tr class="${region.region_id===this.selectedRegion?"selected":""}"><td><button class="source-name" data-agency-region="${esc(region.region_id)}">${esc(region.region_name)}</button></td>${snap.windows.map(w=>`<td>${agencyCell(cells[`${region.region_id}|${w.window_key}`])}</td>`).join("")}</tr>`).join("")}</tbody></table></div></section>
      <section class="library climate-block"><div class="library-title"><h2>Oda sayısına göre ortanca toplam</h2><small>${esc(snap.bedroom_note)}</small></div>
      <div class="table-scroll"><table class="lodging-table"><thead><tr><th>MAHALLE</th>${queried.map(w=>`<th>${windowHeader(w)}</th>`).join("")}</tr></thead>
      <tbody>${snap.regions.map(region=>`<tr><td>${esc(region.region_name)}</td>${queried.map(w=>`<td>${bedroomCell(cells[`${region.region_id}|${w.window_key}`])}</td>`).join("")}</tr>`).join("")}</tbody></table></div></section>
      <section class="library climate-block"><div class="library-title"><h2>Şirket bazında sonuç</h2><small>Her şirket kendi sırasıyla sorulur; birinin hatası diğerlerini durdurmaz.</small></div>
      <div class="table-scroll"><table class="lodging-table"><thead><tr><th>ŞİRKET</th><th>ALTYAPI</th><th>İLAN</th><th>BULUNAN</th><th>FİYATLI SORGU</th><th>ŞİRKET LİSTESİ</th><th>İSTEK</th><th>DURUM</th></tr></thead>
      <tbody>${snap.companies.map(c=>`<tr><td>${esc(c.company)}<small>${esc(c.domain)}</small></td><td>${esc(c.adapter)}${c.protected?'<small><span class="tag warm">korumalı site</span></small>':""}${c.guest_rule?`<small>${esc(GUEST_RULES[c.guest_rule] || c.guest_rule)}</small>`:""}</td><td>${c.listing_count}</td><td>${c.matched_count}${companyMethods(c)}</td><td>${c.priced_count}/${c.quote_count}</td><td>${companyList(c)}</td><td>${c.request_count}</td><td><span class="tag ${c.status==="done"?"green":"warm"}">${esc(COMPANY_LABELS[c.status] || c.status)}</span>${c.message?`<small>${esc(c.message)}</small>`:""}</td></tr>`).join("")}</tbody></table></div>
      <p class="source-stamp">Eşlenemeyen ilanlar: ${Object.entries(PAGE_LABELS).filter(([key])=>key!=="matched" && cov[key]).map(([key,label])=>`${esc(label)} ${cov[key]}`).join(" · ") || "yok"}.</p></section>
      <div id="agency-region"></div>`;
    body.querySelector(".agency-table").addEventListener("click",event=>{
      const button=event.target.closest("[data-agency-region]");
      if(button) {this.selectedRegion=button.dataset.agencyRegion;this.selectedListing=null;this.listings=null;this.draw(target);}
    });
    if(this.selectedRegion) this.region(target);
  }
  region(target) {
    const box=target.querySelector("#agency-region"), snap=this.snapshot, regionId=this.selectedRegion;
    const region=snap.regions.find(r=>r.region_id===regionId);
    if(!box || !region) return;
    if(this.listings?.region_id!==regionId) {
      box.innerHTML="<p>İlan fiyatları yükleniyor…</p>";
      const sequence=this.sequence;
      api(`agency-rate-runs/${snap.run.id}/listings?region_id=${encodeURIComponent(regionId)}`).then(result=>{
        if(sequence!==this.sequence || this.selectedRegion!==regionId) return;
        this.listings=result;this.region(target);
      }).catch(error=>{box.textContent=error.message;});
      return;
    }
    const queried=snap.windows.filter(w=>w.status==="queried"), listings=this.listings.listings.filter(l=>l.domain);
    box.innerHTML=`<section class="library climate-block"><div class="library-title"><h2>${esc(region.region_name)} · şirket sitesi fiyatları</h2><small>${listings.length} ilan yapılandırılmış şirketlere bağlı (${this.listings.listings.length} ilanın)</small></div>
      <div class="workspace-grid"><div class="table-scroll"><table class="lodging-table"><thead><tr><th>İLAN</th><th>ŞİRKET</th>${queried.map(w=>`<th>${esc(w.label)}</th>`).join("")}</tr></thead>
      <tbody>${listings.map(l=>`<tr class="${l.lodging_id===this.selectedListing?"selected":""}"><td><button class="source-name" data-agency-listing="${l.lodging_id}">${esc(l.title)}</button><small>#${l.lodging_id} · ${l.bedrooms==null?"oda —":`${l.bedrooms} oda`}</small></td>
        <td>${esc(l.company || l.domain)}<small>${esc(PAGE_LABELS[l.page_status] || l.page_status)}${l.match_method?` · eşleme: ${esc(METHOD_LABELS[l.match_method] || l.match_method)}`:""}</small></td>${queried.map(w=>`<td>${quoteTag(l.quotes[w.window_key])}${publishedTag(l.published?.[w.window_key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
      <section class="detail" id="agency-detail" aria-label="Fiyat dökümü"></section></div></section>${ownTable(this.listings.own || [],queried)}`;
    box.querySelector("tbody").addEventListener("click",event=>{
      const button=event.target.closest("[data-agency-listing]");
      if(button) {this.selectedListing=Number(button.dataset.agencyListing);this.region(target);}
    });
    this.detail(target);
  }
  detail(target) {
    const box=target.querySelector("#agency-detail"), listing=this.listings?.listings.find(l=>l.lodging_id===this.selectedListing);
    if(!box) return;
    if(!listing) {box.innerHTML='<p class="muted">Fiyat dökümü için bir ilan seçin.</p>';return;}
    const windows=this.snapshot.windows.filter(w=>w.status==="queried");
    box.innerHTML=`<span class="eyebrow">İLAN #${listing.lodging_id}</span><h2>${esc(listing.title)}</h2>
      <p>${esc(listing.company || listing.domain)} · ${esc(PAGE_LABELS[listing.page_status] || listing.page_status)}${listing.match_method?` · eşleme yöntemi: ${esc(METHOD_LABELS[listing.match_method] || listing.match_method)}`:""}${listing.message?`<br><small>${esc(listing.message)}</small>`:""}${listing.match_note?`<br><small>${esc(listing.match_note)}</small>`:""}</p>
      ${listing.page_url?`<p>${companyLink(listing.page_url)}</p>`:listing.listing_url?`<p>${companyLink(listing.listing_url)}</p>`:""}
      ${windows.map(w=>quoteBreakdown(listing.quotes[w.window_key],w)+publishedBreakdown(listing.published?.[w.window_key])).join("")}`;
  }
}
export function publishedTag(rent) {
  return rent?`<small class="published-rent">yayımlanmış kira ${usd(rent.rent_low)}–${usd(rent.rent_high)}</small>`:"";
}
export function publishedBreakdown(rent) {
  return rent?`<p class="source-stamp">Yayımlanmış kira (vergi ve ücret hariç; toplam fiyata karışmaz): ${usd(rent.rent_low)}–${usd(rent.rent_high)}. ${esc(rent.basis)}</p>`:"";
}
/** Homes from a community's official rental program that Book>Direct does not show, with their prices; counted apart. */
export function ownTable(own, windows) {
  if(!own.length) return "";
  return `<section class="library climate-block"><div class="library-title"><h2>Şirketin kendi envanteri</h2><small>${own.length} ev · tek topluluğun resmî kiralama programı; Book>Direct'te olmayan evler, mahalle özetinde ayrı sayılır</small></div>
    <div class="table-scroll"><table class="lodging-table"><thead><tr><th>EV</th><th>ŞİRKET</th>${windows.map(w=>`<th>${esc(w.label)}</th>`).join("")}</tr></thead>
    <tbody>${own.map(o=>`<tr><td>${esc(o.title)}<small>${esc(o.address || "adres yok")} · ${o.bedrooms==null?"oda —":`${o.bedrooms} oda`}</small></td><td>${esc(o.company || o.domain)}<small>${companyLink(o.page_url)}</small></td>${windows.map(w=>`<td>${quoteTag(o.quotes?.[w.window_key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div></section>`;
}
