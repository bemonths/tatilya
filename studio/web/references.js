import {api, esc} from "./api.js";
import {collectionTabs} from "./connectors.js";

export const STATUS_TAGS={dogrulandi:"green",celiskili:"warm",dogrulanamadi:""};
export const VIDEO_RULE="Video dili: “doğrulandı” satırlar kaynak gösterilerek söylenebilir; “çelişkili” satırlar ancak çelişki açıkça söylenerek ya da daha güncel resmî bir kaynakla çözülerek kullanılır; “doğrulanamadı” satırlar videoda kullanılmaz.";

/** Rows grouped by topic in the table's topic order; unknown topics keep their key as label and come last. */
export function groupByTopic(rows, topics={}) {
  const order=[...Object.keys(topics),...new Set((rows||[]).map(r=>r.konu).filter(k=>!(k in topics)))];
  return order.map(key=>({key,label:topics[key] || key,rows:(rows||[]).filter(r=>r.konu===key)})).filter(group=>group.rows.length);
}
export function statusCounts(rows) {
  const counts={dogrulandi:0,celiskili:0,dogrulanamadi:0,overdue:0};
  for(const row of rows || []) { if(row.durum in counts) counts[row.durum]++; if(row.overdue) counts.overdue++; }
  return counts;
}
export function filterReferences(rows, {status="", search=""}={}) {
  const query=search.trim().toLocaleLowerCase("tr");
  return (rows || []).filter(row=>(!status || (status==="overdue"?row.overdue:row.durum===status)) &&
    (!query || [row.id,row.ifade,row.deger,row.kaynak_adi,row.not].join(" ").toLocaleLowerCase("tr").includes(query)));
}
/** External source link only for https addresses; anything else stays plain text. */
export function referenceLink(url, label) {
  try { if(new URL(url).protocol==="https:") return `<a class="source-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`; } catch { /* plain text below */ }
  return esc(label);
}
export function referenceRow(row, statuses={}) {
  const value=row.deger?`${esc(row.deger)}${row.birim?` <small>${esc(row.birim)}</small>`:""}`:'<span class="muted">—</span>';
  const details=[row.kisa_alinti?`<p>Kaynaktan alıntı (doğrulama için, videoda kullanılmaz): “${esc(row.kisa_alinti)}”</p>`:"",
    row.belge_konumu?`<p>Belgedeki yeri: ${esc(row.belge_konumu)}</p>`:"", row.celiski_notu?`<p><strong>Çelişki:</strong> ${esc(row.celiski_notu)}</p>`:"",
    row.not?`<p>Not: ${esc(row.not)}</p>`:"", row.belge_sha256?`<p class="source-host">SHA-256 ${esc(row.belge_sha256)}</p>`:""].join("");
  return `<tr class="${row.overdue?"reference-overdue":""}"><td><strong>${esc(row.id)}</strong><div class="reference-statement">${esc(row.ifade)}</div>${details?`<details class="reference-details"><summary>Alıntı ve notlar</summary>${details}</details>`:""}</td>
    <td>${value}</td><td>${esc(row.kapsam)}</td>
    <td>${referenceLink(row.kaynak_url,row.kaynak_adi)}<small>${esc(row.kaynak_sahibi)}${row.belge_tarihi?` · belge ${esc(row.belge_tarihi)}`:""} · ${esc(row.guven)}</small></td>
    <td>${esc(row.erisim_tarihi)}</td><td><span class="tag ${STATUS_TAGS[row.durum] ?? ""}">${esc(statuses[row.durum] || row.durum)}</span></td>
    <td>${esc(row.yeniden_kontrol_tarihi)}${row.overdue?'<small class="reference-late">tarihi geçti</small>':""}</td></tr>`;
}

export class ReferencesScreen {
  constructor() {this.snapshot=null;this.status="";this.search="";this.sequence=0;}
  invalidate() {this.sequence++;}
  render(main, data, heading) {
    const sequence=++this.sequence;
    main.innerHTML=collectionTabs("references")+heading("Veri toplama",`${data.selected_destination?.name || "Seçili destinasyon"} için elle doğrulanmış referans tablosu: toplayıcıyla alınamayan kurallar, güvenlik, ulaşım, park ve sezon bilgileri; her satır kaynağı, alıntısı ve doğrulama tarihiyle.`)+
      `<div id="references-body" aria-live="polite"><p>Referanslar yükleniyor…</p></div>`;
    api("references").then(snapshot=>{
      if(sequence!==this.sequence) return;
      this.snapshot=snapshot;this.draw(main);
    }).catch(error=>{if(sequence===this.sequence) main.querySelector("#references-body").textContent=error.message;});
  }
  draw(main) {
    const body=main.querySelector("#references-body"), snapshot=this.snapshot;
    if(!body || !snapshot) return;
    if(!snapshot.available) {body.innerHTML=`<section class="quality-result empty"><h2>Referans tablosu yok</h2><p>${esc(snapshot.reason || "")}</p></section>`;return;}
    const counts=statusCounts(snapshot.rows);
    body.innerHTML=`<section class="overview collection-overview">${[[counts.dogrulandi,"doğrulandı","Kaynak gösterilerek söylenebilir"],[counts.celiskili,"çelişkili","Çelişki söylenmeden kullanılmaz"],
      [counts.dogrulanamadi,"doğrulanamadı","Videoda kullanılmaz"],[counts.overdue,"yeniden kontrol","Tarihi geçmiş satır"]].map(([n,label,note])=>`<div class="metric"><div><div class="metric-number"><strong>${n}</strong><span class="metric-label">${label}</span></div><small>${note}</small></div></div>`).join("")}</section>
      ${snapshot.problems?.length?`<div class="stage-note reference-problems" role="alert"><p><strong>Tablo doğrulamadan geçmedi:</strong> ${snapshot.problems.map(esc).join(" · ")}</p></div>`:""}
      <div class="toolbar reference-toolbar"><div class="search-wrap"><span aria-hidden="true">⌕</span><input type="search" id="reference-search" aria-label="Referanslarda ara" placeholder="Kimlik, ifade veya kaynak ara…" value="${esc(this.search)}"></div>
      <select id="reference-status" aria-label="Durum filtresi"><option value="">Bütün durumlar</option>${[...Object.entries(snapshot.statuses || {}),["overdue","yeniden kontrol tarihi geçmiş"]].map(([key,label])=>`<option value="${esc(key)}" ${key===this.status?"selected":""}>${esc(label)}</option>`).join("")}</select></div>
      <div id="reference-groups"></div>
      <div class="stage-note"><p>${esc(VIDEO_RULE)} Tablo ${esc(snapshot.file)} dosyasından okunur; uygulama yalnız gösterir. Belgeler repoya girmez, SHA-256 ile tanınır. Bugün: ${esc(snapshot.today)}.</p></div>`;
    body.querySelector("#reference-search")?.addEventListener("input",event=>{this.search=event.target.value;this.groups(body);});
    body.querySelector("#reference-status")?.addEventListener("change",event=>{this.status=event.target.value;this.groups(body);});
    this.groups(body);
  }
  groups(body) {
    const rows=filterReferences(this.snapshot.rows,{status:this.status,search:this.search});
    const groups=groupByTopic(rows,this.snapshot.topics || {});
    body.querySelector("#reference-groups").innerHTML=groups.length?groups.map(group=>`<section class="library reference-group"><div class="library-title"><h2>${esc(group.label)}</h2><small>${group.rows.length} satır</small></div>
      <div class="table-scroll"><table class="reference-table"><thead><tr><th>OLGU</th><th>DEĞER</th><th>KAPSAM</th><th>KAYNAK</th><th>ERİŞİM</th><th>DURUM</th><th>YENİDEN KONTROL</th></tr></thead>
      <tbody>${group.rows.map(row=>referenceRow(row,this.snapshot.statuses)).join("")}</tbody></table></div></section>`).join(""):'<p class="muted">Bu filtreyle eşleşen satır yok.</p>';
  }
}
