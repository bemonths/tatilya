import {destinationRows} from "./destinations.js";
import {collectionTabs} from "./connectors.js";
import {api, esc, date} from "./api.js";

export const UNMAPPED="__unmapped__";
/** Methods backed by a citable source (official guide, county subdivision data); derived ones are approximate. */
export const SOURCED_METHODS=["resmi_rehber","ilce_alt_bolum","ilce_alt_bolum_yakin"];
/** Reviewed mapping rows (committed file, read by the server) keyed by beach access id. */
export function beachMapping(layer) {
  return new Map((layer?.available?layer.rows:[]).map(row=>[row.external_id,row]));
}
export function beachNeighborhood(record, mapping) {
  const row=mapping.get(record.external_id);
  return row?{regionId:row.region_id,label:row.region_name,method:row.method_label,ambiguous:row.ambiguous,row}:{regionId:UNMAPPED,label:"eşlenmemiş",method:null,ambiguous:false,row:null};
}
export function mappingCell(info) {
  if(!info.row) return '<span class="tag warm">eşlenmemiş</span>';
  return `${esc(info.label)}<div class="mapping-tags"><span class="tag ${SOURCED_METHODS.includes(info.row.method)?"green":""}">${esc(info.method)}</span>${info.ambiguous?'<span class="tag warm">belirsiz</span>':""}</div>`;
}
export function mappingDetail(info) {
  if(!info.row) return '<div class="features-detail"><h3>Mahalle eşlemesi</h3><p class="muted">Bu erişim eşleme dosyasında yok: eşlenmemiş.</p></div>';
  const url=info.row.source.split(" ")[0];
  const source=/^https:\/\//.test(url)?`<a class="source-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(info.row.source)} ↗</a>`
    :info.row.method==="turetim_en_yakin_mahalle_noktasi"?`Mahalle çekimi ${esc(info.row.source)}`:esc(info.row.source);
  return `<div class="features-detail"><h3>Mahalle eşlemesi</h3><dl><div><dt>Mahalle</dt><dd>${esc(info.label)}</dd></div><div><dt>Yöntem</dt><dd>${esc(info.method)}</dd></div><div><dt>Belirsiz</dt><dd>${info.ambiguous?"evet":"hayır"}</dd></div></dl><p>${source}</p>${info.row.note?`<p class="muted">${esc(info.row.note)}</p>`:""}</div>`;
}
export function mappingNote(layer) {
  if(!layer?.available) return esc(layer?.reason || "Plaj–mahalle eşleme dosyası yok.");
  return "Mahalle bilgisi plaj kaynağında yoktur; ayrı ve gözden geçirilebilir eşleme dosyasından gelir. “Resmî rehber”, “ilçe alt bölüm verisi” ve “ilçe alt bölüm verisi (bitişik)” eşlemeleri kaynak gösterilerek söylenebilir (“Walton County subdivision verisine göre”, bitişikte “erişimin bitiştiği alt bölüm”); “komşu erişimlerle tutarlı” ve “program türetimi” yalnız yaklaşık konumdur.";
}
export function filterBeaches(records, {search="",city="",feature="",neighborhood=""}, mapping) {
  const query=search.toLocaleLowerCase('tr').trim();
  return records.filter(record=>(!city || record.city===city) && (!feature || record.features.includes(feature)))
    .filter(record=>!neighborhood || beachNeighborhood(record,mapping).regionId===neighborhood)
    .filter(record=>`${record.name} ${record.address}`.toLocaleLowerCase('tr').includes(query));
}

export class BeachScreen {
  constructor() {
    this.selectedRun=null;this.selectedRecord=null;this.search="";this.city="";this.feature="";this.neighborhood="";
    this.snapshot=null;this.sequence=0;
  }
  invalidate() {this.sequence++;}
  render(main, data, heading) {
    data={...data,sources:destinationRows(data.sources,data.selected_destination),jobs:destinationRows(data.jobs,data.selected_destination),collections:destinationRows(data.collections,data.selected_destination)};
    const sequence=++this.sequence;
    this.data=data;
    this.mapping=beachMapping(data.beach_neighborhoods);
    const runs=data.collections;
    const source=data.sources.find(source=>source.connector?.name===data.beach_connector.name && source.enabled);
    if(!runs.some(run=>run.id===this.selectedRun)) this.selectedRun=runs[0]?.id || null;
    const run=runs.find(run=>run.id===this.selectedRun);
    const busy=data.jobs.some(job=>job.kind==="source_collection" && job.source_id===source?.id && ["queued","running"].includes(job.status));
    if(!source && !runs.length) {
      main.innerHTML=collectionTabs()+heading("Veri toplama", "Bu destinasyon için plaj kaynağı bağlı değil.");return;
    }
    main.innerHTML=collectionTabs()+heading("Veri toplama", "Plaj erişimlerini kaynağından al. Adresleri, olanakları ve her çekimin önceki sürümlerini birlikte incele.",
      `<button class="primary" data-action="collect-beaches" ${!source || busy?"disabled":""}>${busy?"Toplama sürüyor…":"↓ Plaj verilerini topla"}</button>`) +
      `<section class="connector-strip"><div><span class="eyebrow">BAĞLI KAYNAK</span><h2>${esc(source?.name || "South Walton · Plaj erişimleri")}</h2><p>Resmî turizm kaynağının harita noktaları · Sayfa içindeki JSON</p></div><span class="tag ${source?"green":"warm"}">${source?"Veri toplayıcı hazır":"Kaynak etkin değil"}</span></section>` +
      (!source?'<div class="stage-note"><p>Plaj erişim kaynağı arşivlenmiş veya adresi değişmiş. Kaynak kütüphanesinden doğru adresli kaydı etkinleştir.</p></div>':"") +
      (run ? `<section class="overview collection-overview"><div class="metric"><div><div class="metric-number"><strong>${run.included_count}</strong><span class="metric-label">kıyı erişim noktası</span></div><small>Seçili veri sürümünde</small></div></div><div class="metric"><div><div class="metric-number"><strong>${run.total_count}</strong><span class="metric-label">kaynakta harita noktası</span></div><small>${run.excluded_count} kayıt kapsam dışında</small></div></div><div class="metric"><div><div class="metric-number"><strong>${runs.length}</strong><span class="metric-label">saklanan veri sürümü</span></div><small>Çekim: ${esc(date(run.fetched_at))}</small></div></div></section>
      <div class="collection-version"><label>Sürüm <select id="collection-version" aria-label="Veri sürümü">${runs.map((entry,index)=>`<option value="${entry.id}" ${entry.id===run.id?"selected":""}>${index===0?"Son çekim · ":""}${esc(date(entry.fetched_at))} · ${entry.included_count} kayıt · ${entry.id.slice(0,6)}</option>`).join("")}</select></label><div><a class="download-link" href="/api/collections/${run.id}/export.csv" download>↓ CSV indir</a><a class="download-link muted" href="/api/collections/${run.id}/raw" download>Ham kaynağı indir</a></div></div>
      <div class="stage-note" id="run-diff" role="status" style="margin:0 0 20px"><p>Sürüm farkı yükleniyor…</p></div><p id="diff-version-warning" class="source-stamp" style="color:var(--yellow)" hidden></p><div class="workspace-grid"><section class="library" aria-label="Toplanan plaj verileri"><div class="library-title"><h2>Plaj erişim noktaları</h2><small id="beach-count">Yükleniyor…</small></div>
      <div class="toolbar"><div class="search-wrap"><span aria-hidden="true">⌕</span><input type="search" id="beach-search" aria-label="Plaj kaydı ara" placeholder="Erişim noktası veya adres ara…" value="${esc(this.search)}"></div><select id="beach-city" aria-label="Kaynak yerleşimi filtresi"><option value="">Tüm yerleşimler</option></select><select id="beach-neighborhood" aria-label="Mahalle filtresi"><option value="">Tüm mahalleler</option></select><select id="beach-feature" aria-label="Olanak filtresi"><option value="">Tüm olanaklar</option></select></div>
      <div class="table-scroll"><table class="beach-table"><thead><tr><th>ERİŞİM NOKTASI</th><th>MAHALLE (EŞLEME)</th><th>KAYNAKTA YERLEŞİM</th><th>TÜR</th><th>LİSTELENEN OLANAK</th></tr></thead><tbody id="beach-rows"><tr><td colspan="5">Kayıtlar yükleniyor…</td></tr></tbody></table></div></section><section class="detail" id="beach-detail" aria-label="Plaj kaydı ayrıntıları"></section></div>
      <div class="stage-note"><span class="note-mark">ⓘ</span><p>${esc(data.beach_connector.scope)}<br>Olanaklar kaynakta listelendiği haliyle gösterilir; bir olanağın listede bulunmaması olmadığı anlamına gelmez.<br>${mappingNote(data.beach_neighborhoods)}</p></div><p class="source-stamp">Kaynağın güncelleme metni: ${esc(run.source_updated || "Belirtilmemiş")} · Zaman dilimi kaynakta belirtilmiyor.</p>` :
      `<section class="quality-result empty collection-empty"><div class="empty-icon">⇣</div><h3>İlk gerçek veri çekimi hazır</h3><p>“Plaj verilerini topla” düğmesiyle kaynak sayfasını oku. Çekim tamamlanınca adresler, koordinatlar ve olanaklar burada görünecek.</p><p>Her çekim ayrı saklanır; önceki kayıtlar korunur.</p></section><div class="stage-note"><span class="note-mark">ⓘ</span><p>${esc(data.beach_connector.scope)}</p></div>`);
    if(!run) return;
    main.querySelector('#collection-version').addEventListener('change',event=>{this.selectedRun=event.target.value;this.render(main,data,heading);});
    api(`collections/${run.id}`).then(snapshot=>{
      if(sequence!==this.sequence) return;
      this.snapshot=snapshot;
      const diff=snapshot.diff;
      main.querySelector('#run-diff').textContent=diff?.available
        ? `Önceki başarılı sürüme göre: ${diff.added} eklendi · ${diff.removed} kaldırıldı · ${diff.changed} değişti · ${diff.unchanged} aynı`
        : (diff?.reason || "Önceki başarılı sürüm yok.");
      const warning=main.querySelector('#diff-version-warning');
      warning.hidden=!(diff?.available && diff.connector_version_changed);
      warning.textContent=warning.hidden?"":"Veri toplayıcı sürümü değişti; görülen farkların bir kısmı ayrıştırma değişikliğinden kaynaklanabilir.";
      const cities=[...new Set(snapshot.records.map(record=>record.city))].sort();
      const features=[...new Set(snapshot.records.flatMap(record=>record.features))].sort((a,b)=>this.label(a).localeCompare(this.label(b),'tr'));
      if(!cities.includes(this.city)) this.city="";
      if(!features.includes(this.feature)) this.feature="";
      main.querySelector('#beach-city').innerHTML='<option value="">Tüm yerleşimler</option>'+cities.map(city=>`<option ${city===this.city?"selected":""}>${esc(city)}</option>`).join("");
      main.querySelector('#beach-feature').innerHTML='<option value="">Tüm olanaklar</option>'+features.map(feature=>`<option value="${esc(feature)}" ${feature===this.feature?"selected":""}>${esc(this.label(feature))}</option>`).join("");
      const mapped=new Set(snapshot.records.map(record=>beachNeighborhood(record,this.mapping).regionId));
      const neighborhoods=[...(data.canonical_regions || []).filter(region=>mapped.has(region.id)).map(region=>[region.id,region.name]),...(mapped.has(UNMAPPED)?[[UNMAPPED,"Eşlenmemiş"]]:[])];
      if(!neighborhoods.some(([id])=>id===this.neighborhood)) this.neighborhood="";
      main.querySelector('#beach-neighborhood').innerHTML='<option value="">Tüm mahalleler</option>'+neighborhoods.map(([id,name])=>`<option value="${esc(id)}" ${id===this.neighborhood?"selected":""}>${esc(name)}</option>`).join("");
      main.querySelector('#beach-search').addEventListener('input',event=>{this.search=event.target.value;this.rows(main);});
      main.querySelector('#beach-city').addEventListener('change',event=>{this.city=event.target.value;this.rows(main);});
      main.querySelector('#beach-feature').addEventListener('change',event=>{this.feature=event.target.value;this.rows(main);});
      main.querySelector('#beach-neighborhood').addEventListener('change',event=>{this.neighborhood=event.target.value;this.rows(main);});
      main.querySelector('#beach-rows').addEventListener('click',event=>{const button=event.target.closest('[data-beach-id]');if(button){this.selectedRecord=button.dataset.beachId;this.rows(main);}});
      this.rows(main);
    }).catch(error=>{if(sequence===this.sequence) main.querySelector('#beach-rows').innerHTML=`<tr><td colspan="5">${esc(error.message)}</td></tr>`;});
  }
  label(feature) {return this.data.beach_connector.feature_labels[feature] || feature;}
  rows(main) {
    const mapping=this.mapping || new Map();
    const records=filterBeaches(this.snapshot.records,{search:this.search,city:this.city,feature:this.feature,neighborhood:this.neighborhood},mapping);
    if(!records.some(record=>record.external_id===this.selectedRecord)) this.selectedRecord=records[0]?.external_id || null;
    main.querySelector('#beach-count').textContent=`${records.length} / ${this.snapshot.records.length} kayıt`;
    main.querySelector('#beach-rows').innerHTML=records.length ? records.map(record=>`<tr class="${record.external_id===this.selectedRecord?"selected":""}"><td><button class="source-name" data-beach-id="${esc(record.external_id)}" aria-pressed="${record.external_id===this.selectedRecord}">${esc(record.name)}</button><div class="source-host">${esc(record.address)}</div></td><td class="mapping-cell">${mappingCell(beachNeighborhood(record,mapping))}</td><td>${esc(record.city)}</td><td><span class="tag">${record.access_type==="regional"?"Bölgesel":"Mahalle"}</span></td><td class="feature-cell">${record.features.length ? record.features.slice(0,2).map(feature=>`<span>${esc(this.label(feature))}</span>`).join("")+(record.features.length>2?`<small>+${record.features.length-2} olanak</small>`:"") : '<span class="muted">Bilgi listelenmemiş</span>'}</td></tr>`).join("") : '<tr class="empty-row"><td colspan="5">Bu filtrelere uyan kayıt yok.</td></tr>';
    const record=records.find(record=>record.external_id===this.selectedRecord);
    main.querySelector('#beach-detail').innerHTML=record ? `<div class="detail-icon">⌖</div><span class="eyebrow">ERİŞİM NOKTASI</span><h2>${esc(record.name)}</h2><p>${esc(record.address)}<br>${esc(record.city)}</p><dl><div><dt>Erişim türü</dt><dd>${record.access_type==="regional"?"Bölgesel":"Mahalle"}</dd></div><div><dt>Enlem</dt><dd>${record.latitude}</dd></div><div><dt>Boylam</dt><dd>${record.longitude}</dd></div></dl>${mappingDetail(beachNeighborhood(record,mapping))}<div class="features-detail"><h3>Kaynakta listelenen olanaklar</h3>${record.features.length?record.features.map(feature=>`<span class="feature-pill">${esc(this.label(feature))}</span>`).join(""):'<p class="muted">Olanak bilgisi listelenmemiş.</p>'}</div><a class="source-link" href="${esc(this.snapshot.run.source_url)}" target="_blank" rel="noopener noreferrer">Orijinal kaynak sayfası ↗</a><div class="detail-foot">Çekim: ${esc(date(this.snapshot.run.fetched_at))}<br>Kaynak kimliği: ${esc(record.external_id)}<br>Kaynak kaydı aktarıldı; yerinde doğrulama yapılmadı.</div>` : '<div class="empty"><h3>Kayıt seç</h3><p>Filtreleri değiştirerek diğer erişim noktalarını görebilirsin.</p></div>';
  }
}
