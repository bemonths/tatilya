import {destinationRows} from "./destinations.js";
import {api, esc, date} from "./api.js";

export const DAILY_NEEDS_CONNECTOR="openstreetmap-daily-needs";
export const SOURCE_LABELS={"openstreetmap":"OpenStreetMap","zincirin kendi sitesi":"zincirin kendi sitesi"};
export const OUTCOME_LABELS={osm_ile_ayni:"OpenStreetMap'te de var",eklendi:"OpenStreetMap'te yok; zincirin sitesinden eklendi",
  osmde_var_zincirde_kapali:"OpenStreetMap'te var; zincirin sitesinde kapalı",bolgede_yok:"zincirin bölgede mağazası yok",okunamadi:"zincirin sitesi okunamadı"};
const active=job=>["queued","running"].includes(job.status);

/** Great-circle distance in miles and metres; a missing value stays visibly missing. */
export function miles(measure) {
  if(!measure || measure.median_km==null) return '<span class="muted">—</span>';
  const metres=Math.round(measure.median_km*1000);
  return `<strong>${new Intl.NumberFormat("tr-TR",{maximumFractionDigits:2}).format(measure.median_mi)} mil</strong><small>${new Intl.NumberFormat("tr-TR").format(metres)} m · 1 mil içinde %${Math.round((measure.within_1mi_share || 0)*100)}</small>`;
}
export function pointSource(point) {
  const label=SOURCE_LABELS[point.source] || point.source;
  try {
    const url=new URL(point.source_url || "");
    if(["https:","http:"].includes(url.protocol)) return `<a class="source-link" href="${esc(point.source_url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`;
  } catch { /* plain label below */ }
  return esc(label);
}

export class DailyNeeds {
  constructor() {this.selectedRun=null;this.snapshot=null;this.sequence=0;this.category=null;}
  invalidate() {this.sequence++;}
  render(target,data) {
    if(!target) return;
    const runs=destinationRows(data.daily_needs_runs || [],data.selected_destination);
    const source=data.sources.find(s=>s.enabled && s.connector?.name===DAILY_NEEDS_CONNECTOR);
    if(!source && !runs.length) {target.innerHTML="";return;}
    const busy=data.jobs.some(j=>j.source_id===source?.id && active(j));
    if(!runs.some(r=>r.id===this.selectedRun)) {this.selectedRun=runs[0]?.id || null;this.snapshot=null;}
    const run=runs.find(r=>r.id===this.selectedRun), sequence=++this.sequence;
    const attribution=data.daily_needs_connector?.attribution || "© OpenStreetMap katkıcıları, ODbL";
    target.innerHTML=`<section class="connector-strip agency-strip"><div><span class="eyebrow">OPENSTREETMAP · GÜNLÜK İHTİYAÇ</span><h2>Market, eczane, acil sağlık, bisiklet kiralama</h2>
      <p>${esc(attribution)} · süpermarketler zincirlerin kendi mağaza bulucularıyla gözden geçirildi · mesafeler kuş uçuşu</p></div>
      <button class="primary" data-action="collect-daily-needs" ${!source || busy?"disabled":""}>${busy?"Toplama sürüyor…":"↓ Günlük ihtiyaç noktalarını topla"}</button></section>`+
      (run?`<div class="collection-version"><label>Sürüm <select id="daily-needs-version" aria-label="Günlük ihtiyaç sürümü">${runs.map((r,i)=>`<option value="${esc(r.id)}" ${r.id===run.id?"selected":""}>${i===0?"Son çekim · ":""}${esc(date(r.fetched_at))} · ${r.record_count} nokta · ${esc(r.id.slice(0,6))}</option>`).join("")}</select></label><a class="download-link" href="/api/daily-needs-runs/${esc(run.id)}/raw" download>↓ Ham Overpass yanıtını indir</a></div><div id="daily-needs-body"><p>Özet yükleniyor…</p></div>`:
      `<section class="quality-result empty"><h2>Henüz günlük ihtiyaç çekimi yok</h2><p>“Günlük ihtiyaç noktalarını topla” OpenStreetMap'e tek bir küçük Overpass sorgusu gönderir ve sonucu ham kopyasıyla kaydeder. Mesafeler son konaklama çekimindeki ilanlardan okuma anında hesaplanır.</p></section>`);
    if(!run) return;
    target.querySelector("#daily-needs-version").addEventListener("change",event=>{this.selectedRun=event.target.value;this.snapshot=null;this.render(target,data);});
    if(this.snapshot?.run?.id===run.id) {this.draw(target);return;}
    api(`daily-needs-runs/${run.id}`).then(snapshot=>{if(sequence!==this.sequence) return;this.snapshot=snapshot;this.draw(target);})
      .catch(error=>{if(sequence===this.sequence) {const box=target.querySelector("#daily-needs-body");if(box) box.textContent=error.message;}});
  }
  draw(target) {
    const box=target.querySelector("#daily-needs-body"), snap=this.snapshot;
    if(!box || !snap) return;
    const keys=[...snap.categories.map(c=>c.category_key),"beach"];
    const counts=Object.fromEntries(snap.categories.map(c=>[c.category_key,snap.points.filter(p=>p.category_key===c.category_key).length]));
    if(!snap.categories.some(c=>c.category_key===this.category)) this.category=snap.categories[0]?.category_key;
    const points=snap.points.filter(p=>p.category_key===this.category);
    box.innerHTML=`<div class="stage-note lodging-label"><p><strong>${esc(snap.note)}</strong></p><p>${esc(snap.beach_note)}</p><p>${esc(snap.attribution)} · OpenStreetMap verisi ${esc(snap.snapshot.osm_timestamp || "")} · sorgu ${esc(snap.snapshot.queried_on)} · konaklama çekimi ${esc((snap.lodging_run_id || "").slice(0,6))} (${esc(snap.lodging_searched_on || "—")}) · koordinatı olmayan ${snap.missing_coordinates} ilan ölçülmedi</p></div>
      <section class="library climate-block"><div class="library-title"><h2>Mahalle başına günlük ihtiyaç</h2><small>İlanlardan en yakın noktaya ${esc(snap.distance_label)} mesafenin ortancası ve 1 mil (1.609 m) içinde kalan ilan payı; bizim hesabımız.</small></div>
      <div class="table-scroll"><table class="lodging-table"><thead><tr><th>MAHALLE</th><th>İLAN</th><th>RESTORAN (dizin)</th>${keys.map(k=>`<th>${esc(snap.labels[k])}</th>`).join("")}</tr></thead>
      <tbody>${snap.regions.map(r=>`<tr><td>${esc(r.region_name)}</td><td>${r.measured_count}<small>${r.listing_count} ilan</small></td><td>${r.restaurant_count ?? "—"}</td>${keys.map(k=>`<td>${miles(r.measures[k])}</td>`).join("")}</tr>`).join("")}</tbody></table></div></section>
      <section class="library climate-block"><div class="library-title"><h2>Noktalar</h2><small>${snap.categories.map(c=>`<button class="tab ${c.category_key===this.category?"active":""}" data-daily-category="${esc(c.category_key)}">${esc(c.label)} · ${counts[c.category_key]}</button>`).join(" ")}</small></div>
      <div class="table-scroll"><table class="lodging-table"><thead><tr><th>NOKTA</th><th>ADRES</th><th>KOORDİNAT</th><th>KAYNAK</th></tr></thead>
      <tbody>${points.map(p=>`<tr><td>${esc(p.name || "adı yok")}${p.brand && p.brand!==p.name?`<small>${esc(p.brand)}</small>`:""}${p.note?`<small>${esc(p.note)}</small>`:""}</td><td>${esc(p.address || "—")}</td><td>${p.latitude.toFixed(5)}, ${p.longitude.toFixed(5)}</td><td>${pointSource(p)}${p.checked_on?`<small>kontrol ${esc(p.checked_on)}</small>`:""}</td></tr>`).join("") || '<tr><td colspan="4">Bu kategoride nokta yok.</td></tr>'}</tbody></table></div></section>
      ${snap.checks.length?`<section class="library climate-block"><div class="library-title"><h2>Zincir mağaza kontrolü</h2><small>Süpermarket zincirlerinin kendi mağaza bulucuları (elle gözden geçirildi).</small></div>
      <div class="table-scroll"><table class="lodging-table"><thead><tr><th>ZİNCİR</th><th>MAĞAZA</th><th>SONUÇ</th><th>KONTROL</th></tr></thead>
      <tbody>${snap.checks.map(c=>`<tr><td>${esc(c.chain)}</td><td>${esc(c.store)}${c.address?`<small>${esc(c.address)}</small>`:""}</td><td>${esc(OUTCOME_LABELS[c.outcome] || c.outcome)}${c.note?`<small>${esc(c.note)}</small>`:""}</td><td>${esc(c.checked_on)}${c.store_url?`<small><a class="source-link" href="${esc(c.store_url)}" target="_blank" rel="noopener noreferrer">mağaza sayfası ↗</a></small>`:""}</td></tr>`).join("")}</tbody></table></div></section>`:""}`;
    box.querySelectorAll("[data-daily-category]").forEach(button=>button.addEventListener("click",()=>{this.category=button.dataset.dailyCategory;this.draw(target);}));
  }
}
