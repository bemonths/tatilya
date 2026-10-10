import {api, esc, date} from "./api.js";

// GÖREV-14 (Adım 4c): Settings → Talimatlar. The repository file is the single source; a save is refused when the file changed on disk after
// it was opened (its SHA-256); every save keeps the previous content in the data folder, and an old version can be written back.

export function fileButtons(files, selected) {
  return files.map(f=>`<button type="button" class="tab ${f.key===selected?"active":""}" data-instruction="${esc(f.key)}" aria-pressed="${f.key===selected}">
    ${esc(f.name)}${f.kind==="bilgi"?' <span class="tag">bilgi</span>':""}</button>`).join("");
}

export function versionRows(versions) {
  if(!versions?.length) return '<p class="muted">Bu dosya program içinden henüz kaydedilmedi; önceki sürüm yok.</p>';
  return `<div class="table-scroll"><table class="reference-table"><thead><tr><th>KAYDEDİLDİĞİ ZAMAN</th><th>KARMA</th><th>BOYUT</th><th></th></tr></thead><tbody>
    ${versions.map(v=>`<tr><td>${esc(date(v.saved_at))}</td><td><code>${esc(v.sha256.slice(0,8))}</code></td><td>${(v.size/1024).toFixed(1).replace(".",",")} KB</td>
      <td><button type="button" class="quiet" data-version-view="${esc(v.id)}">Görüntüle</button> <button type="button" data-version-restore="${esc(v.id)}">Bu sürüme dön</button></td></tr>`).join("")}
    </tbody></table></div><p class="muted form-note">Her satır, o zamanda yapılan kayıttan önceki hâldir. “Bu sürüme dön” onu yeni bir kayıt olarak geri yazar; şimdiki hâl de sürümlere eklenir.</p>`;
}

export function editorHtml(state) {
  const {files, file, message, viewing}=state;
  const selected=file?.key;
  const meta=file?`<p class="instruction-meta">${esc(file.title)} · <code>${esc(file.name)}</code> · karma <code>${esc(file.sha256.slice(0,8))}</code> · son değişiklik ${esc(date(file.modified_at))} · ${(file.size/1024).toFixed(1).replace(".",",")} KB</p>`:"";
  return `<section class="info-card instructions-card" id="instructions"><span class="eyebrow">TALİMATLAR</span><h2 style="margin-top:12px">Talimatlar</h2>
    <p>Claude'a her çalışmada verilen talimat dosyaları. Tek kaynak depodaki dosyadır: burada kaydedince o dosya değişir. Dosya siz açtıktan sonra dışarıda değiştiyse kayıt yapılmaz; önce yeniden yükleyin. Her kayıttan önce önceki hâl veri klasöründe saklanır.</p>
    <div class="filter-row instruction-files">${fileButtons(files||[],selected)}</div>
    ${file?`${meta}<textarea id="instruction-text" class="instruction-text" spellcheck="false" aria-label="${esc(file.name)} metni">${esc(file.text)}</textarea>
      ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
      <div class="decision-actions"><button type="button" class="primary" id="instruction-save">Kaydet</button><button type="button" id="instruction-reload">Yeniden yükle</button></div>
      <h3 style="margin-top:18px">Önceki sürümler</h3>${versionRows(file.versions)}
      ${viewing?`<h3 style="margin-top:14px">Sürüm ${esc(date(viewing.saved_at))}</h3><pre class="path instruction-version">${esc(viewing.text)}</pre>`:""}`
      :`<p class="muted">${esc(message || "Bir dosya seçin.")}</p>`}</section>`;
}

export class InstructionEditor {
  constructor(container) {this.container=container;this.files=[];this.file=null;this.message="";this.viewing=null;this.dirty=false;}
  draw() {
    this.container.innerHTML=editorHtml(this);
    const area=this.container.querySelector("#instruction-text");
    area?.addEventListener("input",()=>{this.dirty=true;});
    this.container.querySelectorAll("[data-instruction]").forEach(b=>b.addEventListener("click",()=>this.open(b.dataset.instruction)));
    this.container.querySelector("#instruction-save")?.addEventListener("click",()=>this.save());
    this.container.querySelector("#instruction-reload")?.addEventListener("click",()=>this.open(this.file.key,"Dosyanın diskteki güncel hâli yüklendi."));
    this.container.querySelectorAll("[data-version-view]").forEach(b=>b.addEventListener("click",()=>this.view(b.dataset.versionView)));
    this.container.querySelectorAll("[data-version-restore]").forEach(b=>b.addEventListener("click",()=>this.restore(b.dataset.versionRestore)));
  }
  async load() {
    try { this.files=await api("claude/instructions"); await this.open(this.files[0]?.key); }
    catch(error) { if(!error.stale) {this.message=error.message;this.draw();} }
  }
  async open(key, message="") {
    if(!key) {this.draw();return;}
    if(this.dirty && this.file && !globalThis.confirm?.("Kaydedilmemiş değişiklik var. Yine de başka hâle geçilsin mi?")) return;
    try { this.file=await api(`claude/instructions/${encodeURIComponent(key)}`);this.message=message;this.viewing=null;this.dirty=false; }
    catch(error) { if(error.stale) return; this.message=error.message; }
    this.draw();
  }
  async save() {
    const text=this.container.querySelector("#instruction-text").value;
    try {
      const saved=await api(`claude/instructions/${encodeURIComponent(this.file.key)}`,{method:"PUT",body:JSON.stringify({text,base_sha256:this.file.sha256})});
      this.file=saved;this.dirty=false;this.viewing=null;
      this.message=saved.unchanged?"Değişiklik yok; dosya olduğu gibi kaldı.":"Kaydedildi. Önceki hâl sürümlere eklendi; bundan sonraki çalışmalar bu metni kullanır.";
      this.draw();
    } catch(error) {
      if(error.stale) return;
      this.message=error.message;
      const area=this.container.querySelector("#instruction-text");
      this.draw();
      const again=this.container.querySelector("#instruction-text");
      if(again) again.value=text;        // the user's edit stays in the box; nothing was written
      void area;
    }
  }
  async view(version) {
    try {
      const found=await api(`claude/instructions/${encodeURIComponent(this.file.key)}/versions/${encodeURIComponent(version)}`);
      const meta=this.file.versions.find(v=>v.id===version);
      const text=this.container.querySelector("#instruction-text")?.value;
      this.viewing={...found,saved_at:meta?.saved_at};this.draw();
      if(this.dirty && text!=null) this.container.querySelector("#instruction-text").value=text;
    } catch(error) { if(!error.stale) {this.message=error.message;this.draw();} }
  }
  async restore(version) {
    if(!globalThis.confirm?.("Bu sürüm dosyaya geri yazılsın mı? Şimdiki hâl de sürümlere eklenir.")) return;
    try {
      this.file=await api(`claude/instructions/${encodeURIComponent(this.file.key)}/versions/${encodeURIComponent(version)}/restore`,{method:"POST",body:JSON.stringify({base_sha256:this.file.sha256})});
      this.dirty=false;this.viewing=null;this.message="Eski sürüm geri yazıldı.";this.draw();
    } catch(error) { if(!error.stale) {this.message=error.message;this.draw();} }
  }
}
