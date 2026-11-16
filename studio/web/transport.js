import {destinationRows} from "./destinations.js";
import {api, esc, date} from "./api.js";

export const ROAD_CONNECTOR="openstreetmap-road-network";
export const AIRFARE_CONNECTOR="bts-airport-fares";
const active=job=>["queued","running"].includes(job.status);
const number=(value,digits=2)=>new Intl.NumberFormat("tr-TR",{maximumFractionDigits:digits}).format(value);
const money=value=>value==null?'<span class="muted">—</span>':`$${new Intl.NumberFormat("en-US",{minimumFractionDigits:2,maximumFractionDigits:2}).format(value)}`;

/** One road cell: road miles and estimated minutes, the great-circle median of the same listings under it; missing stays visibly missing. */
export function roadCell(measure, crow=true) {
  if(!measure || !measure.count) return '<span class="muted">—</span>';
  const minutes=Math.max(1,Math.round(measure.minutes_median));
  return `<strong>${number(measure.road_median_mi)} mil · ${minutes} dk</strong>${crow?`<small>kuş uçuşu ${number(measure.crow_median_mi)} mil · 1 yol mili içinde %${Math.round((measure.within_1mi_share || 0)*100)}</small>`:""}`;
}
export function speedList(speeds) {
  return Object.entries(speeds || {}).map(([kind,mph])=>`${esc(kind)} ${mph}`).join(" · ");
}
export function checkLine(check) {
  if(check.difference_percent==null) return `${esc(check.label)}: OpenStreetMap'te bu adla yol bulunamadı`;
  return `${esc(check.label)}: OpenStreetMap ${number(check.osm_miles,3)} mil · ${esc(check.source || "bilinen uzunluk")} ${number(check.expected_miles,3)} mil · fark %${number(check.difference_percent,1)}`;
}

/** Road distances and driving times (OpenStreetMap road network) and airport average fares (BTS), under the neighborhood screen. */
export class Transport {
  constructor() {this.roadRun=null;this.road=null;this.fareRun=null;this.fare=null;this.sequence=0;}
  invalidate() {this.sequence++;}
  render(target,data) {
    if(!target) return;
    const sequence=++this.sequence;
    const roadRuns=destinationRows(data.road_runs || [],data.selected_destination), fareRuns=destinationRows(data.airfare_runs || [],data.selected_destination);
    const roadSource=data.sources.find(s=>s.enabled && s.connector?.name===ROAD_CONNECTOR), fareSource=data.sources.find(s=>s.enabled && s.connector?.name===AIRFARE_CONNECTOR);
    if(!roadSource && !fareSource && !roadRuns.length && !fareRuns.length) {target.innerHTML="";return;}
    const roadBusy=data.jobs.some(j=>j.source_id===roadSource?.id && active(j)), fareBusy=data.jobs.some(j=>j.source_id===fareSource?.id && active(j));
    if(!roadRuns.some(r=>r.id===this.roadRun)) {this.roadRun=roadRuns[0]?.id || null;this.road=null;}
    if(!fareRuns.some(r=>r.id===this.fareRun)) {this.fareRun=fareRuns[0]?.id || null;this.fare=null;}
    const road=roadRuns.find(r=>r.id===this.roadRun), fare=fareRuns.find(r=>r.id===this.fareRun);
    target.innerHTML=`<section class="connector-strip agency-strip"><div><span class="eyebrow">OPENSTREETMAP · YOL AĞI</span><h2>Yol üzerinden mesafe ve tahmini sürüş süresi</h2>
      <p>${esc(data.road_connector?.attribution || "© OpenStreetMap katkıcıları, ODbL")} · ilanlardan günlük ihtiyaç noktalarına, plaj erişimlerine ve havalimanlarına · süre trafik hesaba katılmadan tahmindir</p></div>
      <button class="primary" data-action="collect-roads" ${!roadSource || roadBusy?"disabled":""}>${roadBusy?"Hesap sürüyor…":"↓ Yol mesafelerini hesapla"}</button></section>`+
      (road?`<div class="collection-version"><label>Sürüm <select id="road-version" aria-label="Yol mesafesi sürümü">${roadRuns.map((r,i)=>`<option value="${esc(r.id)}" ${r.id===road.id?"selected":""}>${i===0?"Son çekim · ":""}${esc(date(r.fetched_at))} · ${esc(r.id.slice(0,6))}</option>`).join("")}</select></label><a class="download-link" href="/api/road-runs/${esc(road.id)}/raw" download>↓ Ham yol ağı manifestini indir</a></div><div id="road-body"><p>Özet yükleniyor…</p></div>`:
      `<section class="quality-result empty"><h2>Henüz yol mesafesi çekimi yok</h2><p>“Yol mesafelerini hesapla” OpenStreetMap yol ağını tek bir Overpass sorgusuyla indirir, ham kopyasını saklar ve yolları programın içinde hesaplar (yaklaşık 1 dakika). Önce konaklama ve günlük ihtiyaç çekimleri gerekir.</p></section>`)+
      `<section class="connector-strip agency-strip"><div><span class="eyebrow">BTS · UÇAK BİLETİ</span><h2>Havalimanından başlayan iç hat yolculuklarının ortalama bilet ücreti</h2>
      <p>ABD Ulaştırma İstatistikleri Bürosu · Average Domestic Airline Itinerary Fares · çeyreklik · belirli bir şehirden bilet fiyatı değildir</p></div>
      <button class="primary" data-action="collect-airfare" ${!fareSource || fareBusy?"disabled":""}>${fareBusy?"Toplama sürüyor…":"↓ Uçak bileti ortalamalarını topla"}</button></section>`+
      (fare?`<div class="collection-version"><label>Sürüm <select id="airfare-version" aria-label="Uçak bileti sürümü">${fareRuns.map((r,i)=>`<option value="${esc(r.id)}" ${r.id===fare.id?"selected":""}>${i===0?"Son çekim · ":""}${esc(date(r.fetched_at))} · ${esc(r.id.slice(0,6))}</option>`).join("")}</select></label><a class="download-link" href="/api/airfare-runs/${esc(fare.id)}/raw" download>↓ Ham BTS manifestini indir</a></div><div id="airfare-body"><p>Özet yükleniyor…</p></div>`:
      `<section class="quality-result empty"><h2>Henüz uçak bileti çekimi yok</h2><p>“Uçak bileti ortalamalarını topla” BTS sayfasını son beş çeyrek için okur (5 istek, yaklaşık 1 dakika).</p></section>`);
    target.querySelector("#road-version")?.addEventListener("change",event=>{this.roadRun=event.target.value;this.road=null;this.render(target,data);});
    target.querySelector("#airfare-version")?.addEventListener("change",event=>{this.fareRun=event.target.value;this.fare=null;this.render(target,data);});
    const load=(run,kept,path,store,draw,box)=>{
      if(!run) return;
      if(kept?.run?.id===run.id) {draw.call(this,target);return;}
      api(`${path}/${run.id}`).then(snapshot=>{if(sequence!==this.sequence) return;store(snapshot);draw.call(this,target);})
        .catch(error=>{if(sequence===this.sequence) {const node=target.querySelector(box);if(node) node.textContent=error.message;}});
    };
    load(road,this.road,"road-runs",snapshot=>{this.road=snapshot;},this.drawRoad,"#road-body");
    load(fare,this.fare,"airfare-runs",snapshot=>{this.fare=snapshot;},this.drawFare,"#airfare-body");
  }
  drawRoad(target) {
    const box=target.querySelector("#road-body"), snap=this.road;
    if(!box || !snap) return;
    const points=snap.categories.filter(k=>!k.startsWith("extra:")), extras=snap.categories.filter(k=>k.startsWith("extra:"));
    const s=snap.snapshot;
    const stale=snap.stale_inputs?.length?`<p><strong>Bu çekimden sonra yeni bir ${esc(snap.stale_inputs.join(" ve "))} yapıldı; yol mesafeleri önceki ilan ve noktalarladır. Yeniden hesaplayın.</strong></p>`:"";
    box.innerHTML=`<div class="stage-note lodging-label"><p><strong>${esc(snap.note)}</strong></p>${stale}
      <p>${esc(snap.attribution)} · OpenStreetMap verisi ${esc(s.osm_timestamp || "")} · sorgu ${esc(s.queried_on)} · ${number(s.way_count,0)} yol, ${number(s.network_km,0)} km (hız sınırı etiketli ${number(s.maxspeed_km,0)} km) · ${s.measured_count} / ${s.listing_count} ilan ölçüldü (yol ağına ${s.settings.snap_limit_m} m içinde bağlanamayan ya da alan dışında kalan ${snap.unmeasured_count} ilan ölçülmedi)</p>
      <p>Varsayılan hızlar (mil/saat; yalnız hız sınırı etiketi olmayan yollarda): ${speedList(snap.speeds_mph)}</p>
      ${s.checks.length?`<p>Sağlama · ${s.checks.map(checkLine).join(" · ")}</p>`:""}</div>
      <section class="library climate-block"><div class="library-title"><h2>Mahalle başına yol mesafesi ve tahmini sürüş</h2><small>${esc(snap.distance_label)}; ${esc(snap.time_label)}. İlanların yol mesafesine göre en yakın noktaya ortancası; altında aynı ilanların kuş uçuşu ortancası. Bizim hesabımız.</small></div>
      <div class="table-scroll"><table class="lodging-table"><thead><tr><th>MAHALLE</th><th>İLAN</th>${points.map(k=>`<th>${esc(snap.labels[k])}</th>`).join("")}</tr></thead>
      <tbody>${snap.regions.map(r=>`<tr><td>${esc(r.region_name)}</td><td>${r.measured_count}<small>${r.listing_count} ilan</small></td>${points.map(k=>`<td>${roadCell(r.measures[k])}</td>`).join("")}</tr>`).join("")}</tbody></table></div></section>
      ${extras.length?`<section class="library climate-block"><div class="library-title"><h2>Havalimanlarına yol mesafesi ve tahmini sürüş</h2><small>İlanlardan yolcu terminaline; trafik hesaba katılmadan tahmini süre.</small></div>
      <div class="table-scroll"><table class="lodging-table"><thead><tr><th>MAHALLE</th>${extras.map(k=>`<th>${esc(snap.labels[k])}</th>`).join("")}</tr></thead>
      <tbody>${snap.regions.map(r=>`<tr><td>${esc(r.region_name)}</td>${extras.map(k=>`<td>${roadCell(r.measures[k],false)}</td>`).join("")}</tr>`).join("")}</tbody></table></div></section>`:""}`;
  }
  drawFare(target) {
    const box=target.querySelector("#airfare-body"), snap=this.fare;
    if(!box || !snap) return;
    const periods=[...new Set(snap.airports.flatMap(a=>a.quarters.map(q=>`${q.year} Q${q.quarter}`)))];
    const cell=(airport,period)=>{const q=airport.quarters.find(item=>`${item.year} Q${item.quarter}`===period);return q?(q.listed?money(q.average_fare):'<span class="muted">tabloda yok</span>'):'<span class="muted">—</span>';};
    box.innerHTML=`<div class="stage-note lodging-label"><p><strong>${esc(snap.label)}.</strong></p><p>${esc(snap.note)}</p>
      <p>Sorgu ${esc(snap.snapshot.queried_on)} · son yayımlanan çeyrek ${snap.snapshot.latest_year} Q${snap.snapshot.latest_quarter} · <a class="source-link" href="${esc(snap.source_url)}" target="_blank" rel="noopener noreferrer">BTS sayfası ↗</a></p>
      ${snap.snapshot.fare_note?`<p><small>Kaynağın tanımı (İngilizce): ${esc(snap.snapshot.fare_note)}</small></p>`:""}</div>
      <section class="library climate-block"><div class="library-title"><h2>Çeyreklik ortalama bilet ücreti</h2><small>Kaynak gerçeği; bir yıl önceki aynı çeyrekle fark bizim hesabımız (nominal dolar).</small></div>
      <div class="table-scroll"><table class="lodging-table"><thead><tr><th>HAVALİMANI</th>${periods.map(p=>`<th>${esc(p)}</th>`).join("")}<th>BİR YIL ÖNCEYE GÖRE</th></tr></thead>
      <tbody>${snap.airports.map(a=>`<tr><td>${esc(a.label)}</td>${periods.map(p=>`<td>${cell(a,p)}</td>`).join("")}<td>${a.change?`${a.change.amount>=0?"+":"−"}${money(Math.abs(a.change.amount))}<small>%${number(a.change.percent,1)}</small>`:'<span class="muted">—</span>'}</td></tr>`).join("")}</tbody></table></div></section>`;
  }
}
