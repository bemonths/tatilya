import {destinationRows} from "./destinations.js";
import {api, esc, date} from "./api.js";
import {collectionTabs} from "./connectors.js";

const CONNECTOR="south-walton-neighborhoods";
const shown=value=>esc(value ?? "Belirtilmemiş");

/** West to east by the source's representative point; equal longitudes keep a stable name order. */
export function westToEast(records) {
  return [...records].sort((a,b)=>a.longitude-b.longitude || a.name.localeCompare(b.name,"en"));
}
/** Page intro paragraphs as escaped HTML; a missing intro stays visibly missing. */
export function introParagraphs(text) {
  const parts=(text || "").split(/\n{2,}/).map(part=>part.trim()).filter(Boolean);
  return parts.length?parts.map(part=>`<p>${esc(part)}</p>`).join(""):'<p class="muted">Kaynak sayfada tanıtım metni bulunamadı.</p>';
}
export function sourcePageLink(url) {
  try { if(new URL(url).protocol!=="https:") return ""; } catch { return ""; }
  return `<a class="source-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Visit South Walton mahalle sayfası ↗</a>`;
}

export class NeighborhoodScreen {
  constructor() {this.selectedRun=null;this.selectedRecord=null;this.snapshot=null;this.sequence=0;}
  invalidate() {this.sequence++;}
  render(main,data,heading) {
    data={...data,sources:destinationRows(data.sources,data.selected_destination),jobs:destinationRows(data.jobs,data.selected_destination),neighborhood_runs:destinationRows(data.neighborhood_runs || [],data.selected_destination)};
    const sequence=++this.sequence;
    const runs=data.neighborhood_runs;
    if(!runs.some(r=>r.id===this.selectedRun)) this.selectedRun=runs[0]?.id || null;
    const run=runs.find(r=>r.id===this.selectedRun);
    const source=data.sources.find(s=>s.enabled && s.connector?.name===CONNECTOR);
    const busy=data.jobs.some(j=>j.source_id===source?.id && ["queued","running"].includes(j.status));
    if(!source && !runs.length) {
      main.innerHTML=collectionTabs("neighborhoods")+heading("Veri toplama", "Bu destinasyon için mahalle kaynağı bağlı değil.");return;
    }
    const scope=data.neighborhood_connector?.scope || "";
    main.innerHTML=collectionTabs("neighborhoods")+heading("Veri toplama",`${data.selected_destination?.name || "Seçili destinasyon"} mahallelerinin kaynak kimliğini, temsilî noktasını, etiketlerini ve tanıtım metinlerini batıdan doğuya incele.`,
      `<button class="primary" data-action="collect-neighborhoods" ${!source || busy?"disabled":""}>${busy?"Toplama sürüyor…":"↓ Mahalle verilerini topla"}</button>`)+
      `<section class="connector-strip"><div><span class="eyebrow">BAĞLI KAYNAK</span><h2>${esc(source?.name || "South Walton · Mahalleler")}</h2><p>Visit South Walton · Mahalle dizini ve mahalle sayfaları · ${data.canonical_regions?.length ?? 0} kanonik mahalle</p></div><span class="tag ${source?"green":"warm"}">${source?"HTML · bağlı":"Kaynak etkin değil"}</span></section>`+
      (run?`<section class="overview collection-overview">${[[run.record_count,"mahalle","Seçili veri sürümünde"],[run.metadata.source_record_count,"kaynakta mahalle kaydı",`${run.excluded_count} kayıt kapsam dışında`],[run.metadata.tag_count,"etiket","Kaynakta listelenen"]].map(([n,label,note])=>`<div class="metric"><div><div class="metric-number"><strong>${esc(n)}</strong><span class="metric-label">${label}</span></div><small>${esc(note)}</small></div></div>`).join("")}</section>
      <div class="collection-version"><label>Sürüm <select id="neighborhood-version" aria-label="Mahalle veri sürümü">${runs.map((r,i)=>`<option value="${esc(r.id)}" ${r.id===run.id?"selected":""}>${i===0?"Son çekim · ":""}${esc(date(r.fetched_at))} · ${r.record_count} kayıt · ${esc(r.id.slice(0,6))}</option>`).join("")}</select></label><a class="download-link" href="/api/neighborhood-runs/${esc(run.id)}/raw" download>↓ Ham kaynak manifestini indir</a></div>
      <p class="source-stamp">Son çekim: ${esc(date(runs[0].fetched_at))} · Seçili çekim: ${esc(date(run.fetched_at))}<br>Kayıtlardaki en yeni kaynak değişikliği: ${shown(run.source_updated)}</p>
      <div class="stage-note" id="neighborhood-diff" role="status"><p>Sürüm farkı yükleniyor…</p></div>
      <div class="workspace-grid"><section class="library" aria-label="Toplanan mahalle verileri"><div class="library-title"><h2>Mahalleler · batıdan doğuya</h2><small id="neighborhood-count">Yükleniyor…</small></div>
      <div class="table-scroll"><table><thead><tr><th>MAHALLE</th><th>KANONİK BÖLGE</th><th>KAYNAK ETİKETLERİ</th></tr></thead><tbody id="neighborhood-rows"><tr><td colspan="3">Kayıtlar yükleniyor…</td></tr></tbody></table></div></section><section class="detail" id="neighborhood-detail" aria-label="Mahalle ayrıntıları"></section></div>`:
      `<section class="quality-result empty"><h2>İlk mahalle çekimi hazır</h2><p>“Mahalle verilerini topla” ile mahalle dizinini ve her mahallenin sayfasını kaydet. Her başarılı çekim ayrı sürüm olarak korunur.</p></section>`)+
      `<div class="stage-note"><p>${esc(scope)} Kaynak adı tam eşleşmeyle veya açık yazım tablosuyla kanonik mahalleye bağlanır; adres veya koordinattan mahalle çıkarılmaz. Kaynak metinleri iç araştırma kanıtıdır; videoda aynen kullanılmaz, kendi cümlelerimizle ve atıfla kullanılır.</p></div>`;
    if(!run) return;
    main.querySelector('#neighborhood-version').addEventListener('change',e=>{this.selectedRun=e.target.value;this.render(main,data,heading);});
    api(`neighborhood-runs/${run.id}`).then(snapshot=>{
      if(sequence!==this.sequence) return;
      this.snapshot=snapshot;
      const diff=snapshot.diff;
      main.querySelector('#neighborhood-diff').textContent=diff?.available?`Önceki başarılı sürüme göre: ${diff.added} eklendi · ${diff.removed} kaldırıldı · ${diff.changed} değişti · ${diff.unchanged} aynı${diff.connector_version_changed?" · Toplayıcı sürümü değişti; bazı farklar ayrıştırmadan kaynaklanabilir.":""}`:(diff?.reason || "Önceki başarılı sürüm yok.");
      main.querySelector('#neighborhood-rows').addEventListener('click',e=>{const b=e.target.closest('[data-neighborhood-id]');if(b){this.selectedRecord=b.dataset.neighborhoodId;this.rows(main);}});
      this.rows(main);
    }).catch(e=>{if(sequence===this.sequence) main.querySelector('#neighborhood-rows').innerHTML=`<tr><td colspan="3">${esc(e.message)}</td></tr>`;});
  }
  rows(main) {
    const records=westToEast(this.snapshot.records);
    if(!records.some(r=>r.external_id===this.selectedRecord)) this.selectedRecord=records[0]?.external_id || null;
    main.querySelector('#neighborhood-count').textContent=`${records.length} kayıt`;
    main.querySelector('#neighborhood-rows').innerHTML=records.length?records.map(r=>`<tr class="${r.external_id===this.selectedRecord?"selected":""}"><td><button class="source-name" data-neighborhood-id="${esc(r.external_id)}" aria-pressed="${r.external_id===this.selectedRecord}">${esc(r.name)}</button><div class="source-host">${esc(r.latitude)}, ${esc(r.longitude)}</div></td><td>${shown(r.canonical_region_name || r.canonical_region_id)}</td><td class="feature-cell">${r.tags.length?r.tags.slice(0,2).map(tag=>`<span>${esc(tag)}</span>`).join("")+(r.tags.length>2?`<small>+${r.tags.length-2} etiket</small>`:""):'<span class="muted">Etiket listelenmemiş</span>'}</td></tr>`).join(""):'<tr><td colspan="3">Bu sürümde mahalle kaydı yok.</td></tr>';
    const r=records.find(r=>r.external_id===this.selectedRecord);
    main.querySelector('#neighborhood-detail').innerHTML=r?`<span class="eyebrow">MAHALLE</span><h2>${esc(r.name)}</h2>${sourcePageLink(r.page_url)}<p>${shown(r.summary)}</p>
      <dl><div><dt>Kanonik bölge</dt><dd>${shown(r.canonical_region_name)} / ${esc(r.canonical_region_id)}</dd></div><div><dt>Temsilî nokta</dt><dd>${esc(r.latitude)}, ${esc(r.longitude)}</dd></div><div><dt>Kaynak kaydı değişikliği</dt><dd>${shown(r.source_modified)}</dd></div></dl>
      <p class="source-stamp">Koordinat mahalle merkezi değildir; kaynağın temsilî noktasıdır.</p>
      <div class="features-detail"><h3>Kaynak etiketleri</h3>${r.tags.length?r.tags.map(tag=>`<span class="feature-pill">${esc(tag)}</span>`).join(""):'<p class="muted">Etiket listelenmemiş.</p>'}<h3>Sayfadaki tanıtım metni</h3>${introParagraphs(r.page_intro)}</div>
      <div class="detail-foot">Kaynak kimliği: ${esc(r.external_id)}<br>Çekim: ${esc(date(this.snapshot.run.fetched_at))}<br>Metinler iç araştırma kanıtıdır; videoda aynen kullanılmaz.</div>`:'<div class="empty"><h3>Kayıt seç</h3><p>Ayrıntıları görmek için listeden bir mahalle seç.</p></div>';
  }
}
