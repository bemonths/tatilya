import {api, esc, destinationPath} from "./api.js";

/** Short label of a stored pack's parameters ("mahalle: rosemary-beach"); empty when the template has none. */
export function paramsText(params, names={}) {
  const entries=Object.entries(params || {});
  return entries.length ? entries.map(([key,value])=>`${key}: ${names[value] || value}`).join(" · ") : "";
}
/** The download address of a stored pack file (markdown, json, yazar-ozeti, sayilar) for the selected destination. */
export function packLink(id, kind) {
  return `/api/${destinationPath(`evidence-packs/${encodeURIComponent(id)}/${kind}`)}`;
}
/** Writer's summary and number checklist links; packs made before GÖREV-12 have neither and say so. */
export function attachedLinks(pack) {
  const extras=pack.ekler || {};
  if(!extras.yazar_ozeti && !extras.sayilar) return '<small class="muted">Yazar özeti ve sayı listesi yok (eski üretim)</small>';
  return `${extras.yazar_ozeti?`<a class="source-link" href="${esc(packLink(pack.id,"yazar-ozeti"))}" download>Yazar özeti ↓</a>`:""}
    ${extras.sayilar?`<a class="source-link" href="${esc(packLink(pack.id,"sayilar"))}" download>Sayı listesi (CSV) ↓</a>`:""}`;
}
// every template's parameter choices: a pack's region shows by name whichever template is selected (GÖREV-13)
export function choiceNames(templates) {
  return Object.fromEntries((templates || []).flatMap(t=>(t.parameters || []).flatMap(p=>(p.choices || []).map(c=>[c.id,c.name]))));
}
export function packRow(pack, names={}) {
  const params=paramsText(pack.params,names);
  return `<tr><td><strong>${esc(pack.title)}</strong>${params?`<small>${esc(params)}</small>`:""}<small class="source-host">${esc(pack.template_key)} · sürüm ${esc(pack.template_version)}</small></td>
    <td>${esc((pack.created_at || "").replace("T"," ").slice(0,19))}</td>
    <td>${pack.section_count} bölüm<small>${pack.evidence_count} kanıt satırı · ${pack.number_count} sayı</small>${pack.missing_count?`<small class="reference-late">${pack.missing_count} 'veri yok' satırı</small>`:""}</td>
    <td>${attachedLinks(pack)}</td>
    <td><a class="source-link" href="${esc(packLink(pack.id,"markdown"))}" download>Markdown ↓</a><small class="source-host">SHA-256 ${esc(pack.markdown_sha256.slice(0,16))}…</small>
    <a class="source-link" href="${esc(packLink(pack.id,"json"))}" download>JSON ↓</a><small class="source-host">SHA-256 ${esc(pack.json_sha256.slice(0,16))}…</small></td></tr>`;
}

export class EvidenceScreen {
  constructor() {this.templates=null;this.packs=null;this.selected="";this.values={};this.busy=false;this.message="";this.sequence=0;}
  invalidate() {this.sequence++;}
  render(main, data, heading) {
    const sequence=++this.sequence;
    main.innerHTML=heading("Kanıt paketi",`${data.selected_destination?.name || "Seçili destinasyon"} için şablondan kanıt paketi: her satır kaynağı, etiketi ve kullanım notuyla. Aynı üretimden yazım için kısa yazar özeti ve ayrı sayı listesi (CSV) çıkar. Paket yorum ve tavsiye içermez.`)+
      `<div id="evidence-body" aria-live="polite"><p>Şablonlar yükleniyor…</p></div>`;
    Promise.all([api("evidence-templates"),api("evidence-packs")]).then(([templates,packs])=>{
      if(sequence!==this.sequence) return;
      this.templates=templates.templates;this.packs=packs;
      if(!this.templates.some(t=>t.key===this.selected)) this.selected=this.templates[0]?.key || "";
      this.draw(main);
    }).catch(error=>{if(sequence===this.sequence) main.querySelector("#evidence-body").textContent=error.message;});
  }
  template() { return (this.templates || []).find(t=>t.key===this.selected); }
  draw(main) {
    const body=main.querySelector("#evidence-body");
    if(!body || !this.templates) return;
    if(!this.templates.length) {body.innerHTML='<section class="quality-result empty"><h2>Şablon yok</h2><p>Bu destinasyon için kanıt paketi şablonu tanımlanmamış.</p></section>';return;}
    const template=this.template();
    const names=choiceNames(this.templates);
    body.innerHTML=`<section class="library evidence-form"><div class="library-title"><h2>Paket üret</h2><small>Son başarılı çekimlerden üretilir; dosyalar veri klasörüne tarihli ve SHA-256'lı kaydedilir.</small></div>
      <div class="toolbar"><label>Şablon <select id="evidence-template">${this.templates.map(t=>`<option value="${esc(t.key)}" ${t.key===this.selected?"selected":""}>${esc(t.title)}</option>`).join("")}</select></label>
      ${(template?.parameters || []).map(p=>`<label>${esc(p.label || p.key)} <select data-param="${esc(p.key)}"><option value="">Seçin…</option>${p.choices.map(c=>`<option value="${esc(c.id)}" ${this.values[p.key]===c.id?"selected":""}>${esc(c.name)}</option>`).join("")}</select></label>`).join("")}
      <button class="primary" id="evidence-generate" ${this.busy?"disabled":""}>${this.busy?"Üretiliyor…":"Paketi üret"}</button></div>
      ${this.message?`<p class="stage-note" role="status">${esc(this.message)}</p>`:""}
      ${template?`<p><strong>Ana soru:</strong> ${esc(template.question)}</p><ol class="evidence-sections">${template.sections.map(s=>`<li><strong>${esc(s.title)}</strong> — ${esc(s.question)}</li>`).join("")}</ol>`:""}</section>
      <section class="library"><div class="library-title"><h2>Üretilmiş paketler</h2><small>${this.packs.length} paket</small></div>
      ${this.packs.length?`<div class="table-scroll"><table class="reference-table"><thead><tr><th>PAKET</th><th>ÜRETİM</th><th>BOYUT</th><th>YAZIM İÇİN</th><th>TAM PAKET</th></tr></thead><tbody>${this.packs.map(p=>packRow(p,names)).join("")}</tbody></table></div>`:'<p class="muted">Henüz paket üretilmedi.</p>'}</section>`;
    body.querySelector("#evidence-template")?.addEventListener("change",event=>{this.selected=event.target.value;this.values={};this.message="";this.draw(main);});
    body.querySelectorAll("[data-param]").forEach(select=>select.addEventListener("change",event=>{this.values[event.target.dataset.param]=event.target.value;}));
    body.querySelector("#evidence-generate")?.addEventListener("click",()=>this.generate(main));
  }
  async generate(main) {
    const template=this.template();
    const missing=(template?.parameters || []).filter(p=>!this.values[p.key]);
    if(missing.length) {this.message=`Önce ${missing.map(p=>p.label || p.key).join(", ")} seçin.`;this.draw(main);return;}
    const sequence=this.sequence;
    this.busy=true;this.message="";this.draw(main);
    try {
      const pack=await api("evidence-packs",{method:"POST",body:JSON.stringify({template_key:this.selected,params:this.values})});
      if(sequence!==this.sequence) return;
      this.packs=[pack,...this.packs];
      this.message=`Paket üretildi: ${pack.evidence_count} kanıt satırı, ${pack.number_count} sayı, ${pack.missing_count} 'veri yok' satırı.`;
    } catch(error) {
      if(error.stale) return;
      this.message=error.message;
    } finally {
      if(sequence===this.sequence) {this.busy=false;this.draw(main);}
    }
  }
}
