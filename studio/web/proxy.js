import {api, esc, date} from "./api.js";

// GÖREV-16 (Adım 3): Settings → "ABD proxy'si (bölge engeli için)". The user's own US proxy is used only for the domains on the
// region-blocked list (sites that serve only visitors inside the United States); never to get past bot protection, a rate limit or a
// ban. The address and the user name are kept in the data folder's settings; the password in Windows Credential Manager (the screen
// shows only "kayıtlı"). "Proxy'yi dene" shows the exit address and its country. The list: added by the program (date and the page's
// title) or by the user; any row can be removed.

const ADDED_BY={program:"program",kullanici:"siz"};

export function testResult(result) {
  if(!result) return "";
  if(result.error) return `<p class="stage-note claude-warning" role="status">${esc(result.error)}</p>`;
  const lines=(result.satirlar||[]).map(line=>`<li>${esc(line)}</li>`).join("");
  const head=result.ok?`<p><span class="tag ${result.uyari?"warm":"green"}">Çıkış adresi ${esc(result.ip)} · ülke ${esc(result.ulke || "bilinmiyor")}</span></p>`
    :`<p><span class="tag warm">Proxy denemesi başarısız</span></p>`;
  const warning=result.uyari?`<p class="stage-note claude-warning">${esc(result.uyari)}.</p>`:"";
  return `<div class="proxy-test-result" role="status">${head}${warning}<ul class="muted">${lines}</ul></div>`;
}

export function regionRows(hosts) {
  if(!hosts?.length) return '<p class="muted">Listede alan adı yok.</p>';
  return `<div class="table-scroll"><table class="reference-table region-table"><thead><tr><th>ALAN ADI</th><th>EKLENDİ</th><th>EKLEYEN</th><th>SAYFA BAŞLIĞI / KANIT</th><th></th></tr></thead><tbody>
    ${hosts.map(h=>`<tr><td><strong>${esc(h.host)}</strong>${h.url?`<small class="source-host">${esc(h.url)}</small>`:""}</td><td>${esc(date(h.first_seen_at))}${h.last_seen_at && h.last_seen_at!==h.first_seen_at?`<small class="source-host">son görülme ${esc(date(h.last_seen_at))}</small>`:""}</td>
      <td>${esc(ADDED_BY[h.added_by] || h.added_by)}</td><td>${esc(h.title || "—")}${h.evidence && h.evidence!==h.title?`<small class="source-host">${esc(h.evidence)}</small>`:""}</td>
      <td><button class="quiet" data-region-remove="${esc(h.host)}">Listeden çıkar</button></td></tr>`).join("")}
    </tbody></table></div>`;
}

export function proxySection(view, {message="", test=null}={}) {
  const notes=(view.notlar||[]).map(n=>`<p class="stage-note claude-warning">${esc(n)}</p>`).join("");
  return `<section class="info-card proxy-settings" id="abd-proxy"><span class="eyebrow">ABD PROXY'Sİ</span><h2 style="margin-top:12px">ABD proxy'si (bölge engeli için)</h2>
    <p>Bazı siteler (ör. CVS, Publix, HCA) yalnız ABD içinden gelen ziyaretçiye hizmet veriyor; bu bilgisayardan da, eklentiyle de okunamıyor. Kendi ABD proxy'nizi buraya girerseniz program yalnız aşağıdaki listedeki alan adlarını bu proxy üzerinden okur; öbür bütün istekler doğrudan gider. Proxy bot korumasını, hız sınırını ya da yasağı aşmak için kullanılmaz; adres döndürme yoktur. Hız kuralı aynıdır: aynı sitede iki sayfa arası en az 8 saniye. Proxy üzerinden doğrulama sayfası çıkarsa onu yine siz geçersiniz.</p>
    <form id="proxy-form" class="video-form proxy-form" autocomplete="off">
      <label>Proxy adresi<input id="proxy-url" value="${esc(view.adres)}" placeholder="http://sunucu:port" spellcheck="false"><small class="muted">Şema http, https ya da socks5; ör. http://sunucu:8080. Kullanıcı adı ve parola adrese yazılmaz.</small></label>
      <label>Kullanıcı adı<input id="proxy-user" value="${esc(view.kullanici)}" spellcheck="false"></label>
      <label>Parola<input id="proxy-password" type="password" placeholder="${view.parola_kayitli?"kayıtlı (değiştirmek için yazın)":""}" autocomplete="new-password"><small class="muted">${view.parola_kayitli?'<span class="tag green">kayıtlı</span> Windows Kimlik Bilgisi Yöneticisi\'nde; burada gösterilmez.':"Parola Windows Kimlik Bilgisi Yöneticisi'ne kaydedilir; hiçbir dosyaya yazılmaz."}</small></label>
      <div class="decision-actions"><button type="submit" class="primary">Kaydet</button>${view.parola_kayitli?'<button type="button" class="quiet" id="proxy-forget">Parolayı sil</button>':""}<button type="button" id="proxy-test"${view.tanimli?"":" disabled"}>Proxy'yi dene</button></div>
    </form>
    ${notes}
    ${testResult(test)}
    <h3>Bölge engelli alan adları</h3>
    <p class="muted">Program bir sitede ABD dışı erişim engeli görünce alan adını bu listeye kendisi ekler (tarih ve engel sayfasının başlığıyla). Bu alan adları eklentiyle okunmaz; ABD proxy'si tanımlıysa önce proxy üzerinden doğrudan, olmazsa programın kendi tarayıcısıyla proxy üzerinden okunur; proxy yoksa atlanır ve kaydedilir.</p>
    ${regionRows(view.bolge_engelli)}
    <form id="region-form" class="toolbar video-form"><label>Alan adı ekle<input id="region-host" placeholder="ör. winndixie.com" spellcheck="false"></label><button type="submit">Listeye ekle</button></form>
    ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
  </section>`;
}

export class ProxySettings {
  constructor(container) {this.container=container;this.view=null;this.message="";this.test=null;}
  async load(message="") {
    try {this.view=await api("abd-proxy");this.message=message;this.draw();}
    catch(error) {if(!error.stale) this.container.textContent=error.message;}
  }
  draw() {
    this.container.innerHTML=proxySection(this.view,{message:this.message,test:this.test});
    this.container.querySelector("#proxy-form").addEventListener("submit",event=>{event.preventDefault();this.save();});
    this.container.querySelector("#proxy-forget")?.addEventListener("click",()=>this.forget());
    this.container.querySelector("#proxy-test").addEventListener("click",()=>this.runTest());
    this.container.querySelector("#region-form").addEventListener("submit",event=>{event.preventDefault();this.add();});
    this.container.querySelectorAll("[data-region-remove]").forEach(button=>button.addEventListener("click",()=>this.remove(button.dataset.regionRemove)));
  }
  async call(path, options, done) {
    try {this.view=await api(path,options);this.message=done;}
    catch(error) {if(error.stale) return;this.message=error.message;}
    this.draw();
  }
  async save() {
    const body={adres:this.container.querySelector("#proxy-url").value,kullanici:this.container.querySelector("#proxy-user").value};
    const password=this.container.querySelector("#proxy-password").value;
    if(password) body.parola=password;
    this.test=null;
    await this.call("abd-proxy",{method:"PUT",body:JSON.stringify(body)},password?"Kaydedildi; parola Kimlik Bilgisi Yöneticisi'ne yazıldı.":"Kaydedildi.");
  }
  async forget() {
    if(!globalThis.confirm?.("Proxy parolası Windows Kimlik Bilgisi Yöneticisi'nden silinsin mi?")) return;
    await this.call("abd-proxy/parola",{method:"DELETE"},"Parola silindi.");
  }
  async runTest() {
    this.test=null;this.message="Proxy deneniyor…";this.draw();
    try {this.test=await api("abd-proxy/dene",{method:"POST",body:"{}"});this.message="";}
    catch(error) {if(error.stale) return;this.test={error:error.message};this.message="";}
    this.draw();
  }
  async add() {
    const host=this.container.querySelector("#region-host").value;
    await this.call("abd-proxy/bolge-engelli",{method:"POST",body:JSON.stringify({alan_adi:host})},"Alan adı listeye eklendi.");
  }
  async remove(host) {
    if(!globalThis.confirm?.(`${host} bölge engelli listeden çıkarılsın mı? Çıkarılan alan adı yeniden doğrudan (ve gerekirse eklentiyle) okunur.`)) return;
    await this.call(`abd-proxy/bolge-engelli/${encodeURIComponent(host)}`,{method:"DELETE"},`${host} listeden çıkarıldı.`);
  }
}
