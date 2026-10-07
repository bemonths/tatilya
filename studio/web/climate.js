import {destinationRows} from "./destinations.js";
import {api, esc, date} from "./api.js";
import {collectionTabs} from "./connectors.js";

export const CLIMATE_CONNECTORS={normals:"ncei-climate-normals",water:"ndbc-water-temperature",storms:"hurdat2-storm-proximity"};
export const CLIMATE_ACTIONS={"collect-climate-normals":"normals","collect-water-temperature":"water","collect-storms":"storms"};
export const CLIMATE_BUTTONS={normals:"↓ İklim normallerini topla",water:"↓ Deniz suyu sıcaklığını topla",storms:"↓ Kasırga izlerini topla"};
const ACTION_OF=Object.fromEntries(Object.entries(CLIMATE_ACTIONS).map(([action,key])=>[key,action]));
const CARDS={
  normals:["NOAA NCEI · İklim normalleri","1991–2020 aylık normaller · anahtarsız veri API'si","değer"],
  water:["NOAA NDBC · Deniz suyu sıcaklığı","Tarihî yıllık ölçüm dosyaları · aylık ortalama bizim hesabımız","yıl-ay ortalaması"],
  storms:["NOAA NHC · HURDAT2","Atlantik fırtına izleri · koridor geçişleri bizim hesabımız","fırtına geçişi"]};
const MONTHS=["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"];
export const NORMAL_COLUMNS=[["MLY-TMAX-NORMAL","Ort. en yüksek"],["MLY-TMIN-NORMAL","Ort. en düşük"],["MLY-TAVG-NORMAL","Ortalama"],
  ["MLY-PRCP-NORMAL","Yağış"],["MLY-PRCP-AVGNDS-GE010HI","Yağışlı gün (≥0,10 inç)"],["MLY-TMAX-AVGNDS-GRTH090","≥90°F gün"],["MLY-TMIN-AVGNDS-LSTH032","≤32°F gün"]];
export const STORM_CLASSES=[["TD","TD","<34 kt"],["TS","TS","34–63 kt"],["HU","HU","64–95 kt"],["MH","MH","≥96 kt"],["bilinmiyor","Rüzgâr yok",""]];
// Flag meanings as defined in NCEI's 1991–2020 monthly normals documentation (Table 1).
export const FLAG_LEGEND="NCEI belgesine göre tamlık bayrakları: S standart (en az 24 yıl veri), R temsilî (en az 10 yıl; eksik aylar çevredeki istasyonlardan tahminle doldurulmuş), P geçici (en az 10 yıl; çevrede istasyon olmadığı için eksik aylar doldurulamamış), E tahmini (en az 2 yıl; çevre istasyonlardan istatistiksel tahmin). Ölçüm bayrakları: X sıfır olmayan değer sıfıra yuvarlandı, M eksik.";
const active=job=>["queued","running"].includes(job.status);

/** Turkish number with fixed decimals; null stays null so callers can show "missing" instead of zero. */
export function number(value, digits=1) {
  return value==null || !Number.isFinite(Number(value))?null:new Intl.NumberFormat("tr-TR",{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(Number(value));
}
export const fToC=f=>(f-32)*5/9;
export const cToF=c=>c*9/5+32;
export const inToMm=inches=>inches*25.4;

/** One normals value in the source unit with our metric conversion underneath; a missing value never becomes 0. */
export function normalCell(record) {
  if(!record || record.value==null) return '<span class="muted">Kaynakta yok</span>';
  const v=record.value;
  if(record.unit==="°F") return `${number(v)} °F<small>${number(fToC(v))} °C</small>`;
  if(record.unit==="inç") return `${number(v,2)} inç<small>${number(inToMm(v),0)} mm</small>`;
  return `${number(v)} ${esc(record.unit)}`;
}
export function waterCell(row) {
  return row?.mean_c==null?'<span class="muted">20 günlük veri yok</span>':`${number(row.mean_c)} °C<small>${number(cToF(row.mean_c))} °F</small>`;
}
export function normalsIndex(values) {
  const index=new Map();
  for(const v of values || []) index.set(`${v.station_id}|${v.month}|${v.element}`,v);
  return index;
}
/** Distinct flags and year counts per variable for one station, as published (no interpretation). */
export function flagSummary(values, stationId) {
  return NORMAL_COLUMNS.map(([code,label])=>{
    const rows=(values || []).filter(v=>v.station_id===stationId && v.element===code);
    const flags=[...new Set(rows.map(v=>v.completeness_flag).filter(Boolean))].sort();
    const measured=rows.filter(v=>v.measurement_flag).map(v=>`${v.measurement_flag} (${MONTHS[v.month-1]})`);
    const years=rows.map(v=>v.years).filter(v=>v!=null);
    const missing=rows.filter(v=>v.value==null).length;
    return `${esc(label)}: tamlık ${flags.length?esc(flags.join("/")):"yok"}${measured.length?` · ölçüm bayrağı ${esc(measured.join(", "))}`:""}${years.length?` · ${Math.min(...years)}–${Math.max(...years)} yıl`:""}${missing?` · ${missing} ay kaynakta yok`:""}`;
  });
}
/** Storms per first-entry month and class for one radius and season range; mirrors storm_proximity.monthly_counts. */
/** Passages inside a radius only while extratropical, a low, wave or disturbance are kept but never counted. */
export const counted=p=>!p.non_tropical_only;
export function stormMonthlyCounts(passages, radius, from, to) {
  const table=Array.from({length:12},()=>({TD:0,TS:0,HU:0,MH:0,bilinmiyor:0}));
  for(const p of passages || []) {
    if(!counted(p) || p.radius_nmi!==radius || (from && p.season<from) || (to && p.season>to)) continue;
    table[p.first_entry_month-1][p.storm_class || "bilinmiyor"]++;
  }
  return table;
}
export function closestStorms(passages, radius, from, to, limit=10) {
  return (passages || []).filter(p=>counted(p) && p.radius_nmi===radius && (!from || p.season>=from) && (!to || p.season<=to))
    .sort((a,b)=>a.closest_km-b.closest_km || a.season-b.season || a.storm_id.localeCompare(b.storm_id)).slice(0,limit);
}
const stationName=station=>`${esc(station.label)} · ${esc(station.station_id)}`;

export class ClimateScreen {
  constructor() {this.snapshot=null;this.compare="";this.radius=null;this.from=null;this.to=null;this.sequence=0;}
  invalidate() {this.sequence++;}
  render(main, data, heading) {
    data={...data,sources:destinationRows(data.sources,data.selected_destination),jobs:destinationRows(data.jobs,data.selected_destination),climate_runs:destinationRows(data.climate_runs || [],data.selected_destination)};
    const sequence=++this.sequence;
    const sources=Object.fromEntries(Object.entries(CLIMATE_CONNECTORS).map(([key,name])=>[key,data.sources.find(s=>s.enabled && s.connector?.name===name)]));
    const runs=Object.fromEntries(Object.entries(CLIMATE_CONNECTORS).map(([key,name])=>[key,data.climate_runs.find(r=>r.connector_name===name)]));
    const destination=data.selected_destination?.name || "Seçili destinasyon";
    if(!Object.values(sources).some(Boolean) && !data.climate_runs.length) {
      main.innerHTML=collectionTabs("climate")+heading("Veri toplama","Bu destinasyon için iklim kaynağı bağlı değil.");return;
    }
    main.innerHTML=collectionTabs("climate")+heading("Veri toplama",`${destination} için iklim kanıtı: yakındaki istasyonların 1991–2020 normalleri, deniz suyu sıcaklığı ve geçmiş fırtına geçişleri. Her değer kaynağıyla etiketlenir.`)+
      `<section class="climate-sources" aria-label="İklim kaynakları">${Object.keys(CLIMATE_CONNECTORS).map(key=>this.sourceCard(key,sources[key],runs[key],data.jobs)).join("")}</section>`+
      (data.climate_runs.length?`<div id="climate-body" aria-live="polite"><p>İklim verileri yükleniyor…</p></div>`:
      `<section class="quality-result empty"><h2>İlk iklim çekimi hazır</h2><p>Yukarıdaki düğmelerle normalleri, deniz suyu ölçümlerini ve HURDAT2 izlerini kaydet. Her başarılı çekim ayrı sürüm olarak korunur.</p></section>`)+
      `<div class="stage-note"><p>Bu ekran destinasyonun içinden ölçüm vermez: değerler yakındaki istasyonlara ve kıyı koridoruna göredir, istasyon adı ve uzaklığıyla okunmalıdır. “Bizim hesabımız” etiketli değerler NOAA verisinden bu programın hesapladığı değerlerdir, NOAA ürünü değildir.</p></div>`;
    if(!data.climate_runs.length) return;
    api("climate").then(snapshot=>{
      if(sequence!==this.sequence) return;
      this.snapshot=snapshot;
      const radii=snapshot.storms?.corridor?.radii_nmi || [];
      if(!radii.includes(this.radius)) this.radius=radii[0] ?? null;
      const lastSeason=snapshot.storms?.corridor?.last_season;
      if(this.to==null && lastSeason) this.to=lastSeason;
      if(this.from==null) this.from=Math.min(1991,this.to || 1991);
      this.draw(main);
    }).catch(error=>{if(sequence===this.sequence) main.querySelector("#climate-body").textContent=error.message;});
  }
  sourceCard(key, source, run, jobs) {
    const [title,subtitle,unit]=CARDS[key];
    const busy=jobs.some(j=>j.source_id===source?.id && active(j));
    return `<article class="climate-source"><span class="eyebrow">BAĞLI KAYNAK</span><h2>${esc(source?.name || title)}</h2><p>${esc(subtitle)}</p>
      <span class="tag ${source?"green":"warm"}">${source?`${esc(source.connector.method)} · bağlı`:"Kaynak etkin değil"}</span>
      <p class="source-stamp">${run?`Son çekim: ${esc(date(run.fetched_at))} · ${esc(run.record_count)} ${unit} · <a href="/api/climate-runs/${esc(run.id)}/raw" download>↓ ham manifest</a>`:"Henüz çekim yok."}</p>
      <button class="primary" data-action="${ACTION_OF[key]}" ${!source || busy?"disabled":""}>${busy?"Toplama sürüyor…":CLIMATE_BUTTONS[key]}</button></article>`;
  }
  draw(main) {
    const body=main.querySelector("#climate-body");
    if(!body || !this.snapshot) return;
    body.innerHTML=`${this.monthly()}${this.storms()}`;
    body.querySelector("#climate-compare")?.addEventListener("change",e=>{this.compare=e.target.value;this.draw(main);});
    body.querySelector("#storm-radius")?.addEventListener("change",e=>{this.radius=Number(e.target.value);this.draw(main);});
    for(const id of ["from","to"]) body.querySelector(`#storm-${id}`)?.addEventListener("change",e=>{const v=Number.parseInt(e.target.value,10);this[id]=Number.isFinite(v)?v:null;this.draw(main);});
  }
  monthly() {
    const {normals,water}=this.snapshot;
    const stations=normals?.stations || [];
    const configOrder=(this.snapshot.config?.stations || []).filter(s=>s.kind==="normals").map(s=>s.station_id);
    const primary=stations.find(s=>s.station_id===configOrder[0]) || stations[0];
    const others=stations.filter(s=>s!==primary);
    if(!others.some(s=>s.station_id===this.compare)) this.compare="";
    const comparison=others.find(s=>s.station_id===this.compare);
    const index=normalsIndex(normals?.values);
    const buoy=water?.stations?.[0];
    const summary=buoy?water.summary[buoy.station_id]:null;
    const rows=MONTHS.map((month,i)=>`<tr><th scope="row">${month}</th>${NORMAL_COLUMNS.map(([code])=>`<td>${primary?normalCell(index.get(`${primary.station_id}|${i+1}|${code}`)):'<span class="muted">Çekim yok</span>'}${comparison?`<div class="climate-compare">${esc(comparison.label)}: ${normalCell(index.get(`${comparison.station_id}|${i+1}|${code}`))}</div>`:""}</td>`).join("")}
      <td>${summary?waterCell(summary[i]):'<span class="muted">Çekim yok</span>'}</td><td>${summary?.[i]?.years_used?`${summary[i].years_used}<small>${summary[i].first_year}–${summary[i].last_year}</small>`:'<span class="muted">0</span>'}</td></tr>`).join("");
    const basis=id=>esc((this.snapshot.config?.stations || []).find(s=>s.station_id===id)?.distance_basis || "Uzaklık");
    const normalsLabel=primary?`Kaynak: NOAA NCEI 1991–2020 aylık iklim normalleri, ${esc(primary.role)} ${stationName(primary)}; ${basis(primary.station_id)}: ${number(primary.distance_km)} km.${comparison?` Karşılaştırma: ${esc(comparison.role)} ${stationName(comparison)}, ${number(comparison.distance_km)} km.`:""} Birimler kaynaktaki gibi °F ve inç; °C ve mm dönüşümleri bizim hesabımız.`:"İklim normalleri henüz toplanmadı.";
    const waterLabel=buoy?`Deniz suyu: ${stationName(buoy)} ölçümlerinden hesaplanan aylık ortalama; NOAA verisinden bizim hesabımız. Her ay için kullanılan yıllar tabloda. Bir yıl-ay en az ${esc(water.min_days)} günü ölçümlü ise ortalamaya girer; çok yıllı değer bu yıl-ay ortalamalarının ortalamasıdır. Denenen yıllar ${esc(buoy.first_year)}–${esc(buoy.last_year)}; dosyası bulunan ${buoy.years_found.length} yıl${buoy.years_missing.length?`, dosyası olmayan yıllar: ${esc(buoy.years_missing.join(", "))}`:""}. ${basis(buoy.station_id)}: ${number(buoy.distance_km)} km.`:"Deniz suyu sıcaklığı henüz toplanmadı.";
    return `<section class="library climate-block"><div class="library-title"><h2>Aylık tablo${primary?` · ${esc(primary.label)}`:""}</h2>
      ${others.length?`<label class="climate-control">Karşılaştırma <select id="climate-compare" aria-label="Karşılaştırma istasyonu"><option value="">Karşılaştırma yok</option>${others.map(s=>`<option value="${esc(s.station_id)}" ${s.station_id===this.compare?"selected":""}>${esc(s.role)} · ${esc(s.label)}</option>`).join("")}</select></label>`:""}</div>
      <div class="table-scroll"><table class="climate-table"><thead><tr><th>AY</th>${NORMAL_COLUMNS.map(([,label])=>`<th>${esc(label.toLocaleUpperCase("tr"))}</th>`).join("")}<th>DENİZ SUYU${buoy?` · ${esc(buoy.station_id)}`:""}</th><th>KULLANILAN YIL</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="source-stamp">${normalsLabel}</p><p class="source-stamp">${waterLabel}</p>
      ${primary?`<details class="climate-flags"><summary>Bayraklar ve normale giren yıl sayıları (kaynaktaki gibi)</summary>${[primary,comparison].filter(Boolean).map(s=>`<p><strong>${stationName(s)}</strong><br>${flagSummary(normals.values,s.station_id).join("<br>")}</p>`).join("")}<p>${esc(FLAG_LEGEND)}</p></details>`:""}</section>`;
  }
  storms() {
    const storms=this.snapshot.storms;
    if(!storms) return `<section class="library climate-block"><div class="library-title"><h2>Kasırga geçmişi</h2></div><p class="muted">HURDAT2 izleri henüz toplanmadı.</p></section>`;
    const c=storms.corridor, radius=this.radius;
    const counts=stormMonthlyCounts(storms.passages,radius,this.from,this.to);
    const total=counts.reduce((sum,row)=>sum+Object.values(row).reduce((a,b)=>a+b,0),0);
    const closest=closestStorms(storms.passages,radius,this.from,this.to);
    const period=`${this.from ?? c.first_season}–${this.to ?? c.last_season}`;
    const v1=String(storms.run?.connector_version || "").endsWith("/1");
    const excluded=(storms.passages || []).filter(p=>!counted(p) && p.radius_nmi===radius && (!this.from || p.season>=this.from) && (!this.to || p.season<=this.to));
    const rule=v1?"Bu çekim eski kuralla (hurdat2-storm-proximity/1) yapıldı: fırtınanın bütün evreleri sayıldı; yeni çekim yalnız tropikal ve subtropikal evreleri sayar."
      :"Yalnız fırtınanın tropikal veya subtropikal olduğu evreler sayılır (HURDAT2 durum kodları TD, TS, HU, SD, SS); EX, LO, WV ve DB evreleri daireye giriş, en yakın mesafe ve en yüksek rüzgâr hesabına girmez. İki iz noktası arasındaki saatlik noktalar aralığın başındaki noktanın evresini taşır.";
    return `<section class="library climate-block"><div class="library-title"><h2>Kasırga geçmişi · ${esc(radius)} deniz mili · ${esc(period)}</h2><small>${total} fırtına</small></div>
      <div class="climate-controls"><label class="climate-control">Yarıçap <select id="storm-radius" aria-label="Yarıçap">${c.radii_nmi.map(r=>`<option value="${esc(r)}" ${r===radius?"selected":""}>${esc(r)} deniz mili (${number(r*1.852,0)} km)</option>`).join("")}</select></label>
      <label class="climate-control">İlk sezon <input id="storm-from" type="number" min="${esc(c.first_season)}" max="${esc(c.last_season)}" value="${esc(this.from ?? "")}"></label>
      <label class="climate-control">Son sezon <input id="storm-to" type="number" min="${esc(c.first_season)}" max="${esc(c.last_season)}" value="${esc(this.to ?? "")}"></label></div>
      <div class="table-scroll"><table class="climate-table storm-table"><thead><tr><th>İLK GİRİŞ AYI</th>${STORM_CLASSES.map(([,label,limit])=>`<th>${esc(label)}${limit?`<small>${esc(limit)}</small>`:""}</th>`).join("")}<th>TOPLAM</th></tr></thead>
      <tbody>${counts.map((row,i)=>`<tr><th scope="row">${MONTHS[i]}</th>${STORM_CLASSES.map(([key])=>`<td>${row[key]||'<span class="muted">0</span>'}</td>`).join("")}<td><strong>${Object.values(row).reduce((a,b)=>a+b,0)}</strong></td></tr>`).join("")}</tbody></table></div>
      <h3 class="climate-subtitle">Koridora en yakın geçen fırtınalar</h3>
      <div class="table-scroll"><table class="climate-table"><thead><tr><th>FIRTINA</th><th>İLK GİRİŞ (UTC)</th><th>EN YAKIN MESAFE</th><th>DAİREDEKİ EN YÜKSEK RÜZGÂR</th><th>SINIF</th></tr></thead><tbody>${closest.length?closest.map(p=>`<tr><td><strong>${esc(p.name)}</strong> ${esc(p.season)}<div class="source-host">${esc(p.storm_id)}</div></td><td>${esc(p.first_entry_time.replace("T"," ").replace("Z",""))}</td><td>${number(p.closest_km)} km<small>${number(p.closest_nmi)} deniz mili</small></td><td>${p.max_wind_kt==null?'<span class="muted">Kaynakta yok</span>':`${esc(p.max_wind_kt)} kt`}${p.status_at_max?`<small>evre: ${esc(p.status_at_max)}</small>`:""}</td><td>${p.storm_class?esc(storms.class_labels[p.storm_class] || p.storm_class):'<span class="muted">Belirlenemedi</span>'}</td></tr>`).join(""):'<tr><td colspan="5">Bu yarıçap ve dönemde geçiş yok.</td></tr>'}</tbody></table></div>
      ${excluded.length?`<p class="source-stamp">Sayılmayan: bu daireye yalnız tropikal olmayan bir evrede giren ${excluded.length} fırtına (${excluded.map(p=>`${esc(p.name)} ${esc(p.season)}, evre ${esc(p.status_at_max || "?")}`).join("; ")}).</p>`:""}
      <p class="source-stamp">Kaynak: NOAA NHC HURDAT2 Atlantik izleri, dosya ${esc(c.hurdat_file)} (${esc(c.first_season)}–${esc(c.last_season)}, ${esc(c.storm_count)} sistem). Koridor: ${esc(c.west_reference)} – ${esc(c.east_reference)}. NOAA verisinden bizim hesabımız: izler 1 saatlik doğrusal ara değerlemeyle sıklaştırılır; ay, fırtınanın daireye ilk girdiği ay (UTC); sınıf, daire içindeki en yüksek sürekli rüzgâr; her fırtına bir yarıçapta bir kez sayılır. ${rule}</p></section>`;
  }
}
