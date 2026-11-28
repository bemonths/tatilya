import {api, esc, date} from "./api.js";
import {settingsHref} from "./settings.js";

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
  if((result.sonuclar||[]).length>1) return `<div class="proxy-test-result" role="status">${resultRows(result.sonuclar)}</div>`;
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

const STATE_TAGS={calisiyor:"green",calismiyor:"warm",denenmedi:""};

/** HEDEF-01: one row per tested proxy ("Proxy'yi dene" of every row): works or not, exit country. */
export function resultRows(results) {
  return `<ul class="proxy-results">${(results||[]).map(r=>`<li><strong>${esc(r.sira)}. ${esc(r.etiket)}</strong> <span class="tag ${r.ok?(r.uyari?"warm":"green"):"warm"}">${r.ok?`çalışıyor · ülke ${esc(r.ulke || "bilinmiyor")}`:"çalışmıyor"}</span>${r.ok?"":`<small class="muted"> ${esc((r.satirlar||[]).slice(1).join(" "))}</small>`}${r.uyari?`<small class="muted"> ${esc(r.uyari)}</small>`:""}</li>`).join("")}</ul>`;
}

/** HEDEF-01: the proxy list; each row is one worker unless it is marked "çalışmıyor". Never an address with its port or a password. */
export function proxyRows(rows) {
  if(!rows?.length) return '<p class="muted">Listede proxy yok. Program yalnız doğrudan bağlantıyla (tek işçi) çalışır; bölge engelli siteler atlanır.</p>';
  return `<div class="table-scroll"><table class="reference-table proxy-table"><thead><tr><th>SIRA</th><th>PROXY</th><th>KULLANICI</th><th>PAROLA</th><th>DURUM</th><th>ÜLKE</th><th>İŞÇİ</th><th></th></tr></thead><tbody>
    ${rows.map(r=>`<tr><td>${esc(r.sira)}</td><td><strong>${esc(r.etiket)}</strong>${r.denendi?`<small class="source-host">denendi ${esc(date(r.denendi))}</small>`:""}</td><td>${esc(r.kullanici || "—")}</td>
      <td>${r.kullanici?(r.parola_kayitli?'<span class="tag green">kasada</span>':'<span class="tag warm">yok</span>'):"—"}</td>
      <td><span class="tag ${STATE_TAGS[r.durum] ?? ""}">${esc(r.durum_metni || r.durum)}</span>${r.not?`<small class="source-host">${esc(r.not)}</small>`:""}</td><td>${esc(r.ulke || "—")}</td>
      <td>${r.isci?"evet":"hayır"}</td>
      <td><button type="button" class="quiet" data-proxy-test="${esc(r.id)}">Dene</button> <button type="button" class="quiet" data-proxy-remove="${esc(r.id)}">Listeden çıkar</button></td></tr>`).join("")}
    </tbody></table></div>`;
}

/** Ayarlar → ABD proxy'si (HEDEF-01): the proxy list, the bulk add box and the workers' site limit. */
export function proxySection(view, {message="", outcome=null}={}) {
  const notes=(view.notlar||[]).map(n=>`<p class="stage-note claude-warning">${esc(n)}</p>`).join("");
  const rows=view.liste||[];
  const workers=1+rows.filter(r=>r.isci).length;
  const range=view.site_basina_aralik||[1,8];
  const added=outcome?`<p class="stage-note" role="status">${esc(outcome.eklenen)} proxy eklendi, ${esc(outcome.guncellenen)} güncellendi.${(outcome.hatalar||[]).length?` Okunamayan satırlar: ${outcome.hatalar.map(e=>`${e.satir}. satır (${e.hata})`).join("; ")}.`:""}</p>${(outcome.sonuclar||[]).length?resultRows(outcome.sonuclar):""}`:"";
  return `<section class="info-card proxy-settings" id="abd-proxy"><span class="eyebrow">ABD PROXY'Sİ</span><h2 style="margin-top:12px">ABD proxy'si (bölge engeli ve işçiler için)</h2>
    <p>Bazı siteler yalnız ABD içinden gelen ziyaretçiye hizmet veriyor; bu siteler yalnız proxy'yle okunur. Kiralama fiyatı çekiminde her çalışan proxy bir <strong>işçi</strong>dir, doğrudan bağlantı da bir işçidir; işçiler aynı anda çalışır, işçi arttıkça çekim kısalır. Proxy'nin denemesi ve bölge engelli alan adları listesi <a href="#veri/okuma">Veri → Okuma denemeleri</a> sekmesindedir.</p>
    <h3>Proxy listesi</h3>
    <p class="muted">Şu an <strong>${workers} işçi</strong>: doğrudan bağlantı ve ${workers-1} proxy. "Çalışmıyor" işaretli proxy işçi olmaz. Çekim sürerken listeye eklenen proxy birkaç dakika içinde çekime katılır; çıkarılan proxy'nin işi başka işçiye geçer.</p>
    ${proxyRows(rows)}
    <form id="proxy-bulk-form" class="video-form proxy-form" autocomplete="off">
      <label>Toplu ekleme (her satıra bir proxy)<textarea id="proxy-bulk" rows="6" spellcheck="false" placeholder="sunucu:port:kullanıcı:parola"></textarea><small class="muted">Kabul edilen biçimler: sunucu:port:kullanıcı:parola · sunucu:port · kullanıcı:parola@sunucu:port · http://sunucu:port. Kaydedince parolalar hemen Windows Kimlik Bilgisi Yöneticisi'ne yazılır, kutu temizlenir; dosyada yalnız adres, port, kullanıcı adı ve tür kalır. Her satır tek tek denenir.</small></label>
      <label>Tür<select id="proxy-kind"><option value="http">HTTP</option><option value="socks5">SOCKS5</option></select><small class="muted">Satırda http:// ya da socks5:// yazmıyorsa bu tür kullanılır.</small></label>
      <div class="decision-actions"><button type="submit">Listeye ekle ve dene</button></div>
    </form>
    ${added}
    <h3>Sitenin korunması</h3>
    <form id="proxy-workers-form" class="video-form proxy-form" autocomplete="off">
      <label>Aynı siteye aynı anda çalışan en çok işçi<input id="proxy-site-limit" type="number" min="${esc(range[0])}" max="${esc(range[1])}" value="${esc(view.site_basina ?? 4)}"><small class="muted">Başlangıç değeri 4. Her işçi aynı siteye en az 8 saniye arayla istek yapar. Bir site 429, engel ya da doğrulama sayfası verirse o sitedeki bütün işçiler yavaşlar; tekrar ederse o site tek işçiyle okunur.</small></label>
      <div class="decision-actions"><button type="submit" class="primary">Kaydet</button></div>
    </form>
    ${notes}
    ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
  </section>`;
}

/** Veri → Okuma denemeleri (GÖREV-21): the proxy's trial reading and the region-blocked domains (these were in Ayarlar → ABD proxy'si). */
export function proxyReading(view, {message="", test=null}={}) {
  return `<section class="info-card proxy-settings" id="proxy-reading"><span class="eyebrow">PROXY'YLE OKUMA</span><h2 style="margin-top:12px">Proxy'nin deneme okuması ve bölge engelli alan adları</h2>
    <p>Proxy bot korumasını, hız sınırını ya da yasağı aşmak için kullanılmaz; adres döndürme yoktur. Hız kuralı aynıdır: aynı sitede iki sayfa arası en az 8 saniye. Bağlantı bilgileri <a href="${settingsHref("proxy")}">Ayarlar → ABD proxy'si</a> bölümündedir${view.tanimli?"":" (henüz tanımlı değil)"}.</p>
    <div class="decision-actions"><button type="button" id="proxy-test"${view.tanimli?"":" disabled"}>Proxy'yi dene</button><small class="muted">Proxy üzerinden çıkış adresini ve ülkesini gösterir.</small></div>
    ${testResult(test)}
    <h3>Bölge engelli alan adları</h3>
    <p class="muted">Program bir sitede ABD dışı erişim engeli görünce alan adını bu listeye kendisi ekler (tarih ve engel sayfasının başlığıyla). Bu alan adları tarayıcı eklentisiyle okunmaz; ABD proxy'si tanımlıysa önce proxy üzerinden doğrudan, olmazsa programın kendi tarayıcısıyla proxy üzerinden okunur; proxy yoksa atlanır ve kaydedilir.</p>
    ${regionRows(view.bolge_engelli)}
    <form id="region-form" class="toolbar video-form"><label>Alan adı ekle<input id="region-host" placeholder="ör. winndixie.com" spellcheck="false"></label><button type="submit">Listeye ekle</button></form>
    ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
  </section>`;
}

class ProxyBase {
  constructor(container) {this.container=container;this.view=null;this.message="";this.test=null;}
  async load(message="") {
    try {this.view=await api("abd-proxy");this.message=message;this.draw();}
    catch(error) {if(!error.stale) this.container.textContent=error.message;}
  }
  async call(path, options, done) {
    try {this.view=await api(path,options);this.message=done;}
    catch(error) {if(error.stale) return;this.message=error.message;}
    this.draw();
  }
}

/** Ayarlar → ABD proxy'si: the proxy list, bulk add, one row's test and removal, the site limit (HEDEF-01). */
export class ProxySettings extends ProxyBase {
  draw() {
    this.container.innerHTML=proxySection(this.view,{message:this.message,outcome:this.outcome});
    this.container.querySelector("#proxy-bulk-form").addEventListener("submit",event=>{event.preventDefault();this.addLines();});
    this.container.querySelector("#proxy-workers-form").addEventListener("submit",event=>{event.preventDefault();this.saveLimit();});
    this.container.querySelectorAll("[data-proxy-test]").forEach(button=>button.addEventListener("click",()=>this.testRow(button.dataset.proxyTest)));
    this.container.querySelectorAll("[data-proxy-remove]").forEach(button=>button.addEventListener("click",()=>this.removeRow(button.dataset.proxyRemove)));
  }
  async addLines() {
    const box=this.container.querySelector("#proxy-bulk");
    const body={satirlar:box.value,tur:this.container.querySelector("#proxy-kind").value};
    box.value="";              // the passwords leave the screen at once
    this.outcome=null;this.message="Proxy'ler kaydediliyor ve tek tek deneniyor…";this.draw();
    try {const answer=await api("abd-proxy/liste",{method:"POST",body:JSON.stringify(body)});this.view=answer;this.outcome=answer.ekleme;this.message="";}
    catch(error) {if(error.stale) return;this.message=error.message;}
    this.draw();
  }
  async testRow(id) {
    this.outcome=null;this.message="Proxy deneniyor…";this.draw();
    try {const answer=await api(`abd-proxy/liste/${encodeURIComponent(id)}/dene`,{method:"POST",body:"{}"});this.view=answer;this.outcome={eklenen:0,guncellenen:0,hatalar:[],sonuclar:[answer.deneme]};this.message="";}
    catch(error) {if(error.stale) return;this.message=error.message;}
    this.draw();
  }
  async removeRow(id) {
    if(!globalThis.confirm?.("Bu proxy listeden çıkarılsın mı? Parolası da Windows Kimlik Bilgisi Yöneticisi'nden silinir.")) return;
    this.outcome=null;
    await this.call(`abd-proxy/liste/${encodeURIComponent(id)}`,{method:"DELETE"},"Proxy listeden çıkarıldı.");
  }
  async saveLimit() {
    const value=Number(this.container.querySelector("#proxy-site-limit").value);
    this.outcome=null;
    await this.call("abd-proxy/isciler",{method:"PUT",body:JSON.stringify({site_basina:value})},"Kaydedildi.");
  }
}

/** Veri → Okuma denemeleri: "Proxy'yi dene" and the region-blocked list. */
export class ProxyReading extends ProxyBase {
  draw() {
    this.container.innerHTML=proxyReading(this.view,{message:this.message,test:this.test});
    this.container.querySelector("#proxy-test").addEventListener("click",()=>this.runTest());
    this.container.querySelector("#region-form").addEventListener("submit",event=>{event.preventDefault();this.add();});
    this.container.querySelectorAll("[data-region-remove]").forEach(button=>button.addEventListener("click",()=>this.remove(button.dataset.regionRemove)));
  }
  async runTest() {
    this.test=null;this.message="Proxy deneniyor…";this.draw();
    try {this.test=await api("abd-proxy/dene",{method:"POST",body:"{}"});this.message="";}
    catch(error) {if(error.stale) return;this.test={error:error.message};this.message="";}
    this.draw();
  }
  async add() {
    const host=this.container.querySelector("#region-host").value;
    if(!host.trim()) {this.message="Bir alan adı yazın (ör. cvs.com).";return this.draw();}
    await this.call("abd-proxy/bolge-engelli",{method:"POST",body:JSON.stringify({alan_adi:host})},"Alan adı listeye eklendi.");
  }
  async remove(host) {
    if(!globalThis.confirm?.(`${host} bölge engelli listeden çıkarılsın mı? Çıkarılan alan adı yeniden doğrudan (ve gerekirse eklentiyle) okunur.`)) return;
    await this.call(`abd-proxy/bolge-engelli/${encodeURIComponent(host)}`,{method:"DELETE"},`${host} listeden çıkarıldı.`);
  }
}
