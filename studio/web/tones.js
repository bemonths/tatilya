import {api, esc, date} from "./api.js";

// GÖREV-15 (Adım 3): Settings → Tonlar. Tones are files in the repository's tone folder (single source); a save is refused when the file
// changed on disk after it was opened; every save keeps the previous content; a deleted tone goes to the archive and can be taken back.
// The warning phrases of the program's check are edited at the bottom with the same rules (they are never given to Claude).

export function toneRows(list) {
  if(!list.tonlar?.length) return '<p class="muted">Ton yok.</p>';
  return `<div class="table-scroll"><table class="reference-table tone-table"><thead><tr><th>TON</th><th>METNİN İLK SATIRI</th><th>SON DEĞİŞİKLİK</th><th>VARSAYILAN</th><th>KULLANIM</th><th></th></tr></thead><tbody>
    ${list.tonlar.map(t=>`<tr data-tone-row="${esc(t.dosya)}"><td><strong>${esc(t.ad)}</strong><small class="source-host">${esc(t.dosya)}.md</small></td>
      <td class="tone-first">${esc(t.ilk_satir)}</td><td>${esc(date(t.degisti))}</td>
      <td>${t.varsayilan?'<span class="tag green">varsayılan</span>':`<button type="button" class="quiet" data-tone-default="${esc(t.dosya)}">Varsayılan yap</button>`}</td>
      <td>${t.kullanim} metin sürümü</td>
      <td class="tone-actions"><button type="button" data-tone-edit="${esc(t.dosya)}">Düzenle</button> <button type="button" class="quiet" data-tone-delete="${esc(t.dosya)}" ${list.tonlar.length<2?"disabled":""}>Sil</button></td></tr>`).join("")}
    </tbody></table></div>`;
}

export function archiveRows(list) {
  if(!list.arsiv?.length) return '<p class="muted">Arşivde ton yok.</p>';
  return `<div class="table-scroll"><table class="reference-table"><thead><tr><th>TON</th><th>İLK SATIR</th><th>ARŞİVLENDİ</th><th>KULLANIM</th><th></th></tr></thead><tbody>
    ${list.arsiv.map(a=>`<tr><td><strong>${esc(a.ad)}</strong><small class="source-host">${esc(a.dosya)}.md</small></td><td class="tone-first">${esc(a.ilk_satir)}</td>
      <td>${esc(date(a.arsivlendi))}</td><td>${a.kullanim} metin sürümü</td><td><button type="button" data-tone-unarchive="${esc(a.id)}">Geri al</button></td></tr>`).join("")}</tbody></table></div>`;
}

/** The form of a new tone or of an edited one (with its versions). */
export function toneForm(form, limits) {
  const editing=Boolean(form.dosya);
  const length=(form.metin||"").length;
  const long=length>(limits?.uzun_metin ?? 1200);
  return `<form id="tone-form" class="tone-form"><h3>${editing?`Tonu düzenle · <code>${esc(form.dosya)}.md</code>`:"Yeni ton"}</h3>
    <label>Tonun adı<input id="tone-name" maxlength="${limits?.ad_en_cok ?? 40}" value="${esc(form.ad||"")}" placeholder="Örn. Sakin rehber" required></label>
    <label>Tonun metni<textarea id="tone-text" rows="7" maxlength="${limits?.en_cok ?? 6000}" placeholder="Anlatıcının kişiliğini birkaç cümleyle anlatın: nasıl konuşur, neye önem verir.">${esc(form.metin||"")}</textarea></label>
    <p class="muted form-note"><span id="tone-count">${length}</span> / ${(limits?.en_cok ?? 6000).toLocaleString("tr")} karakter. Başlık satırını program yazar (<code># Ton: Ad</code>); adı değiştirmek dosya adını değiştirmez.</p>
    <p class="stage-note tone-long" id="tone-long" ${long?"":"hidden"}>${esc(limits?.uzun_not || "Ton metni uzun. Kısa ve niyet anlatan metinler genellikle daha iyi sonuç verir.")}</p>
    ${form.message?`<p class="stage-note" role="status">${esc(form.message)}</p>`:""}
    <div class="decision-actions"><button class="primary" type="submit">${editing?"Kaydet":"Tonu ekle"}</button>${editing?'<button type="button" id="tone-reload">Yeniden yükle</button> <button type="button" class="quiet" id="tone-cancel">Vazgeç</button>':""}</div>
    ${editing?`<h3 style="margin-top:16px">Önceki sürümler</h3>${(form.surumler||[]).length?`<div class="table-scroll"><table class="reference-table"><thead><tr><th>KAYDEDİLDİĞİ ZAMAN</th><th>AD</th><th>İLK SATIR</th><th></th></tr></thead><tbody>
      ${form.surumler.map(v=>`<tr><td>${esc(date(v.saklandi))}</td><td>${esc(v.ad||"—")}</td><td class="tone-first">${esc(v.ilk_satir)}</td><td><button type="button" data-tone-version="${esc(v.id)}">Bu sürüme dön</button></td></tr>`).join("")}
      </tbody></table></div>`:'<p class="muted">Bu ton program içinden henüz kaydedilmedi; önceki sürüm yok.</p>'}`:""}</form>`;
}

export function warningsBox(file, message="") {
  if(!file) return "";
  return `<section class="info-card warnings-card" id="warning-phrases"><span class="eyebrow">PROGRAM DENETİMİ</span><h2 style="margin-top:12px">Denetim: uyarı ifadeleri</h2>
    <p>Program yazılan her metinde bu ifadeleri arar ve bulduğu cümleye sarı işaret koyar; liste Claude'a verilmez. Her satırda bir ifade; büyük-küçük harf fark etmez, kelime sınırına bakılır. Tek istisna “I”: yalnız büyük harfle ve tek kelime olarak eşleşir.</p>
    <p class="instruction-meta"><code>${esc(file.name)}</code> · karma <code>${esc(file.sha256.slice(0,8))}</code> · son değişiklik ${esc(date(file.modified_at))}</p>
    <textarea id="warnings-text" class="instruction-text warnings-text" spellcheck="false" aria-label="Uyarı ifadeleri">${esc(file.text)}</textarea>
    ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
    <div class="decision-actions"><button type="button" class="primary" id="warnings-save">Kaydet</button><button type="button" id="warnings-reload">Yeniden yükle</button></div>
    ${(file.versions||[]).length?`<h3 style="margin-top:14px">Önceki sürümler</h3><div class="table-scroll"><table class="reference-table"><thead><tr><th>KAYDEDİLDİĞİ ZAMAN</th><th>KARMA</th><th></th></tr></thead><tbody>
      ${file.versions.map(v=>`<tr><td>${esc(date(v.saved_at))}</td><td><code>${esc(v.sha256.slice(0,8))}</code></td><td><button type="button" data-warning-version="${esc(v.id)}">Bu sürüme dön</button></td></tr>`).join("")}</tbody></table></div>`:""}</section>`;
}

export function tonesHtml(view) {
  const list=view.list||{tonlar:[],arsiv:[]};
  return `<section class="info-card tones-card" id="tonlar"><span class="eyebrow">TONLAR</span><h2 style="margin-top:12px">Tonlar</h2>
    <p>Video metni seçilen her ton için ayrı yazılır. Bir ton, anlatıcının kişiliğini birkaç cümleyle anlatan bir metindir; anlatıcının sesi (bütün tonlarda aynı) Talimatlar'daki <code>ses_ortak.md</code> dosyasındadır. Tonlar depodaki <code>tonlar</code> klasöründe durur; eklediğiniz ya da değiştirdiğiniz ton git'te kaydedilmemiş değişiklik olarak görünür ve bir sonraki görevin başında kaydedilir.</p>
    ${view.message?`<p class="stage-note" role="status">${esc(view.message)}</p>`:""}
    ${toneRows(list)}
    <div class="tone-form-slot">${toneForm(view.form||{}, list)}</div>
    <h3 style="margin-top:20px">Arşiv</h3><p class="muted form-note">Silinen tonlar burada durur; hiçbir şey silinmez. Silinmiş bir tonla yazılmış metin sürümleri yerinde kalır ve ton adıyla görünür.</p>${archiveRows(list)}</section>`;
}

export class ToneSettings {
  constructor(container, warningsContainer) {this.container=container;this.warnings=warningsContainer;this.list=null;this.form={};this.message="";this.warningFile=null;this.warningMessage="";}
  draw() {
    this.container.innerHTML=tonesHtml(this);
    const box=this.container;
    box.querySelectorAll("[data-tone-default]").forEach(b=>b.addEventListener("click",()=>this.makeDefault(b.dataset.toneDefault)));
    box.querySelectorAll("[data-tone-edit]").forEach(b=>b.addEventListener("click",()=>this.edit(b.dataset.toneEdit)));
    box.querySelectorAll("[data-tone-delete]").forEach(b=>b.addEventListener("click",()=>this.remove(b.dataset.toneDelete)));
    box.querySelectorAll("[data-tone-unarchive]").forEach(b=>b.addEventListener("click",()=>this.unarchive(b.dataset.toneUnarchive)));
    box.querySelectorAll("[data-tone-version]").forEach(b=>b.addEventListener("click",()=>this.restoreVersion(b.dataset.toneVersion)));
    const text=box.querySelector("#tone-text");
    text?.addEventListener("input",()=>{const n=text.value.length;box.querySelector("#tone-count").textContent=n;box.querySelector("#tone-long").hidden=n<=(this.list?.uzun_metin ?? 1200);});
    box.querySelector("#tone-form")?.addEventListener("submit",event=>{event.preventDefault();this.save();});
    box.querySelector("#tone-reload")?.addEventListener("click",()=>this.edit(this.form.dosya,"Tonun diskteki güncel hâli yüklendi."));
    box.querySelector("#tone-cancel")?.addEventListener("click",()=>{this.form={};this.draw();});
    if(this.warnings) this.drawWarnings();
  }
  drawWarnings() {
    this.warnings.innerHTML=warningsBox(this.warningFile,this.warningMessage);
    this.warnings.querySelector("#warnings-save")?.addEventListener("click",()=>this.saveWarnings());
    this.warnings.querySelector("#warnings-reload")?.addEventListener("click",()=>this.loadWarnings("Dosyanın diskteki güncel hâli yüklendi."));
    this.warnings.querySelectorAll("[data-warning-version]").forEach(b=>b.addEventListener("click",()=>this.restoreWarnings(b.dataset.warningVersion)));
  }
  async load(message="") {
    try {this.list=await api("tonlar");this.message=message;} catch(error) {if(error.stale) return;this.message=error.message;}
    this.draw();
    if(this.warnings && !this.warningFile) this.loadWarnings();
  }
  async loadWarnings(message="") {
    try {this.warningFile=await api("claude/instructions/uyari_ifadeleri");this.warningMessage=message;} catch(error) {if(error.stale) return;this.warningMessage=error.message;}
    this.drawWarnings();
  }
  values() {return {ad:this.container.querySelector("#tone-name").value, metin:this.container.querySelector("#tone-text").value};}
  async save() {
    const {ad,metin}=this.values();
    try {
      if(this.form.dosya) {
        const saved=await api(`tonlar/${encodeURIComponent(this.form.dosya)}`,{method:"PUT",body:JSON.stringify({ad,metin,base_sha256:this.form.sha256})});
        this.form={...saved,message:saved.degismedi?"Değişiklik yok.":`Kaydedildi; önceki hâl sürümlere eklendi.${saved.not?" "+saved.not:""}`};
        await this.load();
      } else {
        const made=await api("tonlar",{method:"POST",body:JSON.stringify({ad,metin})});
        this.form={};await this.load(`“${made.ad}” tonu eklendi (${made.dosya}.md).${made.not?" "+made.not:""}`);
      }
    } catch(error) {
      if(error.stale) return;
      this.form={...this.form,ad,metin,message:error.message};this.draw();
    }
  }
  async edit(stem, message="") {
    try {this.form={...await api(`tonlar/${encodeURIComponent(stem)}`),message};} catch(error) {if(error.stale) return;this.message=error.message;}
    this.draw();
    this.container.querySelector("#tone-name")?.focus();
  }
  async remove(stem) {
    if(!globalThis.confirm?.("Bu ton arşive taşınacak; istediğiniz zaman geri alabilirsiniz.")) return;
    try {const done=await api(`tonlar/${encodeURIComponent(stem)}`,{method:"DELETE"});this.form={};await this.load(done.not || "Ton arşive taşındı.");}
    catch(error) {if(!error.stale) {this.message=error.message;this.draw();}}
  }
  async unarchive(id) {
    try {const back=await api(`ton-arsivi/${encodeURIComponent(id)}/geri-al`,{method:"POST",body:"{}"});await this.load(`“${back.ad}” tonu geri alındı (${back.dosya}.md).`);}
    catch(error) {if(!error.stale) {this.message=error.message;this.draw();}}
  }
  async makeDefault(stem) {
    try {await api(`tonlar/${encodeURIComponent(stem)}/varsayilan`,{method:"POST",body:"{}"});await this.load("Varsayılan ton değişti.");}
    catch(error) {if(!error.stale) {this.message=error.message;this.draw();}}
  }
  async restoreVersion(version) {
    if(!globalThis.confirm?.("Bu sürüm tona geri yazılsın mı? Şimdiki hâl de sürümlere eklenir.")) return;
    try {const saved=await api(`tonlar/${encodeURIComponent(this.form.dosya)}/surumler/${encodeURIComponent(version)}/geri-don`,{method:"POST",body:JSON.stringify({base_sha256:this.form.sha256})});
      this.form={...saved,message:"Eski sürüm geri yazıldı."};await this.load();}
    catch(error) {if(!error.stale) {this.form={...this.form,message:error.message};this.draw();}}
  }
  async saveWarnings() {
    const text=this.warnings.querySelector("#warnings-text").value;
    try {const saved=await api("claude/instructions/uyari_ifadeleri",{method:"PUT",body:JSON.stringify({text,base_sha256:this.warningFile.sha256})});
      this.warningFile=saved;this.warningMessage=saved.unchanged?"Değişiklik yok.":"Kaydedildi; bundan sonraki denetimler bu listeyi kullanır.";this.drawWarnings();}
    catch(error) {if(error.stale) return;this.warningMessage=error.message;this.drawWarnings();this.warnings.querySelector("#warnings-text").value=text;}
  }
  async restoreWarnings(version) {
    if(!globalThis.confirm?.("Bu sürüm geri yazılsın mı? Şimdiki hâl de sürümlere eklenir.")) return;
    try {this.warningFile=await api(`claude/instructions/uyari_ifadeleri/versions/${encodeURIComponent(version)}/restore`,{method:"POST",body:JSON.stringify({base_sha256:this.warningFile.sha256})});
      this.warningMessage="Eski sürüm geri yazıldı.";this.drawWarnings();}
    catch(error) {if(!error.stale) {this.warningMessage=error.message;this.drawWarnings();}}
  }
}
