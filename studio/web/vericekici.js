import {api, esc, date} from "./api.js";

// HEDEF-04: Veri → Okuma denemeleri → "Veri Çekici ile okuma". Veri Çekici is the projects' shared reading tool (its own program,
// "İşçi paneli"): 30A writes the list of the sites that need a browser (2–4 pages a site), Veri Çekici reads them with its workers
// and gives back one zip; the zip is imported here as it is (the raw copy) and read with 30A's own readers.

/** The sites that need a browser, from the configuration. */
export function siteTable(sites) {
  if(!sites?.length) return '<p class="muted">Tarayıcı isteyen site yok.</p>';
  return `<details><summary>Tarayıcı isteyen siteler (${esc(sites.length)})</summary><div class="table-scroll"><table class="reference-table vc-sites"><thead><tr><th>SİTE</th><th>TÜR</th><th>SEBEP</th></tr></thead><tbody>
    ${sites.map(s=>`<tr><td>${esc(s.site)}</td><td>${esc(s.tur)}</td><td>${esc(s.sebep)}</td></tr>`).join("")}</tbody></table></div></details>`;
}

/** One import: the per-site table (pages read, errors, price questions, priced) and its buttons. */
export function importCard(item) {
  const rows=(item.siteler||[]).map(s=>`<tr><td>${esc(s.site)}</td><td class="number">${esc(s.okunan)}</td><td class="number">${esc(s.hata)}</td><td class="number">${esc(s.sorgu)}</td><td class="number">${esc(s.fiyatli)}</td><td>${esc((s.isciler||[]).join(", "))}</td></tr>`).join("");
  const records=(item.kayitlar||[]).map(r=>`<tr><td>${esc(r.proje_site)}</td><td>${esc(r.kimlik)}</td><td>${esc(r.baslik || "—")}</td><td class="number">${esc(r.sayfa_durumu ?? "—")}</td><td>${esc((r.fiyatlar||[]).map(f=>f.durum==="priced"?`${f.toplam ?? f.kira} $`:(f.mesaj||f.durum)).join(" · ") || r.not || "")}</td></tr>`).join("");
  const errors=(item.hatalar||[]).map(e=>`<li>${esc(e.site)} · ${esc(e.kimlik)}: ${esc(e.sebep)}</li>`).join("");
  return `<article class="vc-import" data-import="${esc(item.kimlik)}"><h4>${esc(item.dosya)}</h4>
    <p class="muted">İçe alındı: ${esc(date(item.ice_alindi))}${item.yeniden_kuruldu?` · ham kopyadan yeniden kuruldu: ${esc(date(item.yeniden_kuruldu))}`:""} · ${esc(item.okunan)} sayfa okundu, ${esc(item.hata)} hata, ${esc(item.fiyatli)} fiyatlı soru · Veri Çekici ${esc(item.paket?.arac_surumu || "")}, işçiler: ${esc((item.paket?.isciler||[]).join(", "))}</p>
    <div class="table-scroll"><table class="reference-table vc-import-sites"><thead><tr><th>SİTE</th><th>OKUNAN SAYFA</th><th>HATA</th><th>FİYAT SORUSU</th><th>FİYATLI</th><th>İŞÇİ</th></tr></thead><tbody>${rows}</tbody></table></div>
    <details><summary>Okunan sayfalar (${esc((item.kayitlar||[]).length)})</summary><div class="table-scroll"><table class="reference-table vc-records"><thead><tr><th>SİTE</th><th>KİMLİK</th><th>SAYFA BAŞLIĞI</th><th>HTTP</th><th>FİYAT / NOT</th></tr></thead><tbody>${records}</tbody></table></div></details>
    ${errors?`<details><summary>Okunamayanlar</summary><ul>${errors}</ul></details>`:""}
    <div class="decision-actions"><button type="button" class="vc-rebuild" data-import="${esc(item.kimlik)}">Ham kopyadan yeniden kur</button><small class="muted">Saklanan zip'ten aynı çözümü yeniden yapar; siteye gidilmez.</small></div></article>`;
}

export function veriCekiciSection(view, {message=""}={}) {
  const last=view?.listeler?.[0];
  const listLine=last?`<p class="muted">Son liste: ${esc(date(last.olusturuldu))} · ${esc(last.satir)} sayfa, ${esc(last.site_sayisi)} site, ${esc(last.isci_sayisi)} işçi · <code>${esc(last.dosya)}</code>${last.isci_dosyalari?.length>1?` (işçi başına: ${esc(last.isci_dosyalari.join(", "))})`:""}</p>${(last.uyarilar||[]).length?`<ul class="muted">${last.uyarilar.map(u=>`<li>${esc(u)}</li>`).join("")}</ul>`:""}`:"";
  const imports=(view?.ice_aktarmalar||[]).map(importCard).join("") || '<p class="muted">Henüz içe alınmış Veri Çekici sonucu yok.</p>';
  return `<section class="info-card veri-cekici" id="veri-cekici"><span class="eyebrow">VERİ ÇEKİCİ</span><h2 style="margin-top:12px">Veri Çekici ile okuma</h2>
    <p>Tarayıcı isteyen siteler (korumalı ya da doğrulama gösteren kiralama, restoran ve market siteleri) Veri Çekici'nin işçileriyle okunur. Önce buradan liste üretin, listeyi Veri Çekici'nin <strong>İşçi paneli</strong>nde "Listeyi yükle ve işçilere böl" ile yükleyip "Hepsini başlat"a basın; bitince "Sonuçları tek zip'e paketle" ile çıkan zip'i aşağıdan içe alın. Bir site en çok ${esc(view?.site_basina_isci ?? 4)} işçiye verilir. Tarayıcı eklentisi kapalı bir yedek yol olarak yerinde durur.</p>
    ${siteTable(view?.siteler)}
    <div class="decision-actions"><label>Her siteden <select id="vc-pages"><option>2</option><option selected>3</option><option>4</option></select> sayfa</label>
      <label>İşçi sayısı <input id="vc-workers" type="number" min="1" max="21" value="${esc(view?.isci_sayisi ?? 1)}" style="width:4em"></label>
      <button type="button" class="primary" id="vc-list">Veri Çekici listesini üret</button></div>
    ${listLine}
    <h3>Sonuç zip'ini içe al</h3>
    <div class="decision-actions"><input type="file" id="vc-zip" accept=".zip"><button type="button" class="primary" id="vc-import">Sonuç zip'ini içe aktar</button></div>
    ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
    <h3>İçe alınan sonuçlar</h3>${imports}
  </section>`;
}

export class VeriCekiciSection {
  constructor(container) {this.container=container;this.view=null;this.message="";}
  async load(message="") {
    try {this.view=await api("veri-cekici");this.message=message;this.draw();}
    catch(error) {if(!error.stale) this.container.textContent=error.message;}
  }
  draw() {
    this.container.innerHTML=veriCekiciSection(this.view,{message:this.message});
    this.container.querySelector("#vc-list")?.addEventListener("click",()=>this.makeList());
    this.container.querySelector("#vc-import")?.addEventListener("click",()=>this.importZip());
    this.container.querySelectorAll(".vc-rebuild").forEach(b=>b.addEventListener("click",()=>this.rebuild(b.dataset.import)));
  }
  async run(action) {
    try {const message=await action();await this.load(message);}
    catch(error) {if(error.stale) return;this.message=error.message;this.draw();}
  }
  makeList() {
    const sayfa=Number(this.container.querySelector("#vc-pages").value), isci_sayisi=Number(this.container.querySelector("#vc-workers").value);
    return this.run(async()=>{const d=await api("veri-cekici/liste",{method:"POST",body:JSON.stringify({sayfa,isci_sayisi})});return `Liste hazır: ${d.satir} sayfa, ${d.site_sayisi} site. Dosya: ${d.dosya}`;});
  }
  importZip() {
    const file=this.container.querySelector("#vc-zip").files?.[0];
    if(!file) {this.message="Önce Veri Çekici'nin sonuç zip'ini seçin.";this.draw();return;}
    return this.run(async()=>{const d=await api("veri-cekici/ice-aktar",{method:"POST",body:file,headers:{"Content-Type":"application/zip","X-Dosya-Adi":encodeURIComponent(file.name)}});return `İçe alındı: ${d.okunan} sayfa, ${d.hata} hata, ${d.fiyatli} fiyatlı soru.`;});
  }
  rebuild(id) {
    return this.run(async()=>{const d=await api(`veri-cekici/ice-aktarma/${encodeURIComponent(id)}/yeniden-kur`,{method:"POST",body:"{}"});return `Ham kopyadan yeniden kuruldu: ${d.okunan} sayfa, ${d.fiyatli} fiyatlı soru.`;});
  }
}
