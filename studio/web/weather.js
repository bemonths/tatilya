import {api, esc} from "./api.js";
import {collectionTabs} from "./connectors.js";

export function weatherDate(value, timeZone) {
  if(!value) return "Belirtilmemiş";
  if(!timeZone) return value; // Never silently use the browser's timezone.
  try {
    return new Intl.DateTimeFormat("tr-TR", {timeZone, dateStyle:"medium", timeStyle:"short"}).format(new Date(value));
  } catch { return `${value} (kaynak zamanı)`; }
}
const value = (input, suffix="") => input == null?"Belirtilmemiş":`${input}${suffix}`;

export class WeatherScreen {
  constructor() { this.selectedRun=null;this.anchor="west";this.sequence=0; }
  invalidate() { this.sequence++; }
  render(main, data, heading) {
    const sequence=++this.sequence;
    const runs=data.weather_runs;
    if(!runs.some(run=>run.id===this.selectedRun)) this.selectedRun=runs[0]?.id || null;
    const run=runs.find(run=>run.id===this.selectedRun);
    const source=data.sources.find(source=>source.enabled && source.connector?.name===data.weather_connector.name);
    const busy=data.jobs.some(job=>job.source_id===source?.id && ["queued","running"].includes(job.status));
    main.innerHTML=collectionTabs(true)+heading("Veri toplama", "30A koridoru için üç hava örnek noktası. NWS’nin noktasal/grid tahminleri ve aktif uyarıları.",
      `<button class="primary" data-action="collect-weather" ${!source || busy?"disabled":""}>${busy?"Toplama sürüyor…":"↓ Hava verilerini topla"}</button>`)+
      `<section class="connector-strip"><div><span class="eyebrow">BAĞLI KAYNAK</span><h2>National Weather Service</h2><p>Resmî API · Tahminler değişkendir; canlı durum bildirimi değildir.</p></div><span class="tag ${source?"green":"warm"}">${source?"API · bağlı":"Kaynak etkin değil"}</span></section>`+
      (run?`<section class="overview collection-overview"><div class="metric"><div><div class="metric-number"><strong>${run.metadata.anchors}</strong><span class="metric-label">örnek nokta</span></div><small>Batı / Orta / Doğu 30A</small></div></div><div class="metric"><div><div class="metric-number"><strong>${run.record_count}</strong><span class="metric-label">tahmin kaydı</span></div><small>${run.metadata.forecast_period_count} dönem · ${run.metadata.hourly_period_count} saatlik</small></div></div><div class="metric"><div><div class="metric-number"><strong>${run.metadata.alert_count}</strong><span class="metric-label">çekimde aktif uyarı</span></div><small>Üç noktada tekilleştirildi</small></div></div></section>
      <div class="collection-version"><label>Sürüm <select id="weather-version" aria-label="Hava veri sürümü">${runs.map((r,i)=>`<option value="${r.id}" ${r.id===run.id?"selected":""}>${i===0?"Son çekim · ":""}${esc(weatherDate(r.fetched_at,"UTC"))} UTC · ${r.id.slice(0,6)}</option>`).join("")}</select></label><a class="download-link" href="/api/weather-runs/${run.id}/raw" download>↓ Ham NWS yanıtlarını indir</a></div>
      <p class="source-stamp">Son çekim: ${esc(weatherDate(runs[0].fetched_at,"UTC"))} UTC · Seçili çekim: ${esc(weatherDate(run.fetched_at,"UTC"))} UTC</p>
      <div class="filter-row" aria-label="Hava örnek noktası">${data.weather_connector.anchors.map(a=>`<button class="tab ${a.anchor_key===this.anchor?"active":""}" data-weather-anchor="${a.anchor_key}" aria-pressed="${a.anchor_key===this.anchor}">${a.label}</button>`).join("")}</div>
      <div id="weather-snapshot" aria-live="polite"><p>Hava verileri yükleniyor…</p></div>`:
      `<section class="quality-result empty"><h2>İlk hava çekimi hazır</h2><p>“Hava verilerini topla” ile üç örnek noktanın tahminlerini ve aktif uyarılarını kaydet.</p></section>`)+
      `<div class="stage-note"><p>Koordinatlar Visit South Walton plaj erişim verisinden, 53 kıyı kaydının boylam sıralamasına göre seçildi. Bunlar canonical mahalle merkezleri değildir. Tahminler NWS nokta/grid verisidir; güvenlik kararları için güncel resmî uyarıları kontrol edin.</p></div>`;
    if(!run) return;
    main.querySelector('#weather-version').addEventListener('change',event=>{this.selectedRun=event.target.value;this.render(main,data,heading);});
    main.querySelectorAll('[data-weather-anchor]').forEach(button=>button.addEventListener('click',()=>{this.anchor=button.dataset.weatherAnchor;this.render(main,data,heading);}));
    api(`weather-runs/${run.id}`).then(snapshot=>{
      if(sequence!==this.sequence) return;
      this.drawSnapshot(main.querySelector('#weather-snapshot'),snapshot);
    }).catch(error=>{if(sequence===this.sequence) main.querySelector('#weather-snapshot').textContent=error.message;});
  }
  drawSnapshot(container, snapshot) {
    const loc=snapshot.locations.find(location=>location.anchor_key===this.anchor);
    if(!loc) {container.textContent="Bu sürümde örnek nokta bulunamadı.";return;}
    const periods=snapshot.forecast_periods.filter(r=>r.anchor_key===this.anchor);
    const hourly=snapshot.hourly_periods.filter(r=>r.anchor_key===this.anchor);
    const alerts=snapshot.alerts.filter(r=>r.anchor_keys.includes(this.anchor));
    const stamps=snapshot.run.metadata.source_timestamps?.[this.anchor];
    container.innerHTML=`<section class="info-card weather-location"><span class="eyebrow">${esc(loc.label)} · ${esc(loc.time_zone)}</span><h2>${esc(loc.source_beach_name)}</h2><p>Örnek nokta: ${loc.latitude}, ${loc.longitude} · NWS ${esc(loc.cwa)} / grid ${loc.grid_x}, ${loc.grid_y}</p><p>Kaynak plaj kimliği: ${esc(loc.source_beach_external_id)}</p><p>Kaynak güncellemesi: ${esc(weatherDate(stamps?.period?.updateTime || stamps?.period?.generatedAt,loc.time_zone))}<br>Tüm dönem saatleri ${esc(loc.time_zone)} saat dilimindedir. Çekim zamanı kaynak güncelleme zamanı değildir.</p></section>
      <section class="library weather-block"><div class="library-title"><h2>12 saatlik tahmin dönemleri</h2><small>${periods.length} dönem</small></div>${this.table(periods,loc.time_zone,true)}</section>
      <section class="library weather-block"><div class="library-title"><h2>Saatlik tahmin</h2><small>İlk ${Math.min(24,hourly.length)} / ${hourly.length} saatlik kayıt</small></div>${this.table(hourly.slice(0,24),loc.time_zone,false)}</section>
      <section class="info-card weather-block"><h2>Aktif NWS uyarıları</h2><p>Seçili çekim ve örnek nokta için geçerlidir; canlı yenilenmez.</p>${alerts.length?alerts.map(a=>`<article class="weather-alert"><span class="tag warm">${esc(a.severity || "Belirtilmemiş")}</span><h3>${esc(a.event)}</h3><p>${esc(a.headline || "")}</p><p>Bitiş: ${esc(weatherDate(a.expires,loc.time_zone))}</p><details><summary>Uyarı ayrıntıları</summary><p>${esc(a.description || "")}</p><p>${esc(a.instruction || "")}</p></details></article>`).join(""):"<p>Aktif NWS uyarısı yok.</p>"}</section>
      <p class="source-stamp">${esc(snapshot.diff.reason)}</p>`;
  }
  table(rows,zone,period) {
    return `<div class="table-scroll"><table><thead><tr><th>DÖNEM / SAAT</th><th>SICAKLIK</th><th>YAĞIŞ OLASILIĞI</th><th>TAHMİN</th><th>RÜZGÂR</th></tr></thead><tbody>${rows.map(row=>`<tr><td>${period?`<strong>${esc(row.name || "")}</strong><br>`:""}${esc(weatherDate(row.start_time,zone))}<br><small>${esc(weatherDate(row.end_time,zone))}</small></td><td>${esc(value(row.temperature,row.temperature_unit?` °${row.temperature_unit}`:""))}</td><td>${esc(value(row.precipitation_probability,"%"))}</td><td>${esc(row.short_forecast)}${period && row.detailed_forecast?`<details><summary>Ayrıntı</summary><p>${esc(row.detailed_forecast)}</p></details>`:""}</td><td>${esc(value(row.wind_speed))}<br>${esc(row.wind_direction || "")}</td></tr>`).join("")}</tbody></table></div>`;
  }
}
