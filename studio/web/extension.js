import {api, esc, date} from "./api.js";
import {linkSettingsMentions} from "./settings.js";

// The browser extension (GÖREV-14) opens, in the user's own Chrome, the pages the program asks for and hands back only their content.
// GÖREV-21 split its screen by layer: Ayarlar → Tarayıcı eklentisi keeps only the pairing code and the connection (a program setting);
// the sites it may open, its speed, the trial with the program's own local page, the trial of the problem sites and the warm-up list are
// data work and live in Veri → Okuma denemeleri.

const STATE_LABELS={tamam:"okundu",dogrulama:"doğrulama geçilmedi",giris:"giriş gerekiyor",odeme:"ödeme sayfası",izin_yok:"izin yok",hata:"hata",
  erisim_reddedildi:"erişim reddedildi",bolge_engeli:"bölge engeli",yonlendi:"başka siteye yönlendi",atlandi:"kullanıcı atladı",
  reddedildi:"sorgu reddedildi"};
// GÖREV-16: the page's kind in the trial table
export const KIND_LABELS={tamam:"tamam",dogrulama:"doğrulama",erisim_reddedildi:"erişim reddedildi",bolge_engeli:"bölge engeli",yonlendi:"başka siteye yönlendi",
  sorgu:"sayfanın kendi sorgusu"};
const METHOD_LABELS={eklenti:"eklenti",proxy:"proxy","tarayici+proxy":"tarayıcı + proxy"};

/** GÖREV-25: the page's own queries the extension may send (the program's allowed list; read-only here). */
export function queryList(queries) {
  if(!queries?.length) return "";
  return `<p><strong>İzinli sorgular</strong> <small class="muted">Eklenti yalnız bu sorguları, sitenin kendi sekmesinden ve yalnız bu alanlarla gönderir; giriş, hesap, ödeme, rezervasyon, sepet ve iletişim adresleri her zaman reddedilir.</small></p>
    <ul class="extension-queries">${queries.map(q=>`<li><span class="tag">${esc(q.alan_adi)}</span> <code>${esc(q.yontem)} ${esc(q.yol)}</code> · ${esc(q.amac || "")}${q.alanlar?`<small class="source-host">alanlar: ${esc(q.alanlar.join(", "))}</small>`:""}</li>`).join("")}</ul>`;
}

/** GÖREV-17: the kind of a trial row in words. A region-blocked site says how it ended: "bölge engeli · proxy'yle okundu",
 *  "bölge engeli · proxy'yle de okunamadı" or "bölge engeli · ABD proxy'si tanımlı değil" (the same words as the job log). */
export function kindText(row) {
  const kind=row.tur || row.durum;
  if(kind!=="bolge_engeli") return KIND_LABELS[kind] || "—";
  if(row.proxy && row.durum==="tamam") return "bölge engeli · proxy'yle okundu";
  if(/tanımlı değil/.test(row.not || "")) return "bölge engeli · ABD proxy'si tanımlı değil";
  if(/proxy'yle de okunamadı/.test(row.not || "")) return "bölge engeli · proxy'yle de okunamadı";
  return "bölge engeli";
}

export function connectionText(view) {
  if(!view.eslesti) return {tone:"warm",text:"Eşleşmedi: eklentiyi kurup bu ekrandaki kodu eklentiye yazın."};
  if(view.bagli && view.calisiyor) return {tone:"green",text:`Eklenti çalışıyor: ${view.calisiyor}`};
  if(view.bagli) return {tone:"green",text:`Bağlı · eklenti sürümü ${view.surum || "—"} · son görülme ${date(view.son_gorulme)}`};
  return {tone:"warm",text:`Bağlı değil (Chrome kapalı olabilir) · son görülme ${view.son_gorulme?date(view.son_gorulme):"—"}`};
}

/** The job panel's "Bu sayfayı atla" while the extension waits for the user on a verification page (GÖREV-16). */
export function skipButton(job) {
  return job?.progress_info?.tur==="eklenti" && job.waiting_for ? `<button data-skip-job="${esc(job.id)}">Bu sayfayı atla</button> ` : "";
}

export function trialRows(rows) {
  if(!rows?.length) return "";
  return `<div class="table-scroll"><table class="reference-table"><thead><tr><th>SİTE</th><th>TÜR</th><th>DURUM</th><th>BAŞLIK</th><th>BOYUT</th><th>NOT</th></tr></thead><tbody>
    ${rows.map(r=>`<tr><td>${esc(r.alan_adi)}<small class="source-host">${esc(r.aciklama || "")}</small></td><td><span class="tag ${(r.tur||r.durum)==="tamam" || (r.proxy && r.durum==="tamam")?"green":"warm"}">${esc(kindText(r))}</span>${r.yontem?`<small class="source-host">${esc(METHOD_LABELS[r.yontem] || r.yontem)}</small>`:""}</td><td><span class="tag ${r.durum==="tamam"?"green":"warm"}">${esc(STATE_LABELS[r.durum] || r.durum)}</span></td>
      <td>${esc(r.baslik || "—")}</td><td>${r.bayt!=null?`${Math.round(r.bayt/1024)} KB`:"—"}</td><td>${linkSettingsMentions(esc(r.not || ""))}${r.sha256?`<small class="source-host">SHA-256 ${esc(r.sha256.slice(0,12))}…</small>`:""}</td></tr>`).join("")}
    </tbody></table></div>`;
}

/** Ayarlar → Tarayıcı eklentisi (GÖREV-21): only the pairing code and the connection (with the one-time install steps the pairing
 *  needs). What the extension reads and the trial readings are data work: Veri → Okuma denemeleri (extensionReading). */
export function extensionSection(view, {message=""}={}) {
  const state=connectionText(view);
  return `<section class="info-card extension-settings" id="extension-settings"><span class="eyebrow">TARAYICI EKLENTİSİ</span><h2 style="margin-top:12px">Tarayıcı eklentisi</h2>
    <p>“30A Studio Yardımcısı” eklentisi, programın istediği sayfaları sizin Chrome'unuzda kendi açtığı ayrı pencerede açar ve yalnız sayfanın içeriğini programa verir. Burada yalnız eşleştirme ve bağlantı durumu vardır; eklentinin okuduğu siteler, hızı ve deneme okumaları <a href="#veri/okuma">Veri → Okuma denemeleri</a> sekmesindedir.</p>
    <p class="stage-note"><span class="note-mark">●</span><span><strong>Bağlantı:</strong> <span class="tag ${state.tone}" id="extension-connection">${esc(state.text)}</span></span></p>
    ${view.eski_surum?`<p class="stage-note claude-warning">Chrome'daki eklenti eski sürüm (${esc(view.surum)}; programın klasöründeki ${esc(view.beklenen_surum)}). chrome://extensions sayfasında “30A Studio Yardımcısı”nın yenile düğmesine basın.</p>`:""}
    <div class="extension-code"><span class="eyebrow">EŞLEŞME KODU</span><strong id="extension-code">${esc(view.kod)}</strong>
      <button id="extension-renew" class="quiet">Kodu yenile</button><small class="muted">Kodu yenileyince eklentiye yeni kodu yeniden yazmanız gerekir.</small></div>
    <details class="extension-guide"><summary>Kurulum ve eşleştirme adımları (bir kez)</summary>
      <ol class="extension-steps">${view.kurulum.map(step=>`<li>${esc(step)}</li>`).join("")}</ol>
      <p class="path">${esc(view.klasor)}</p>
      ${(view.kurulum_resimleri||[]).map(name=>`<img src="/eklenti-kurulum/${encodeURIComponent(name)}" alt="${esc(name)}" loading="lazy">`).join("")}
      <p class="muted">Rehberin tamamı eklenti klasöründeki KURULUM.md dosyasında.</p></details>
    ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
  </section>`;
}

/** Veri → Okuma denemeleri (GÖREV-21): the sites the extension may open, its speed, the trial with the program's own local page and the
 *  trial of the problem sites (the user presses it). These were in Ayarlar → Tarayıcı eklentisi. */
export function extensionReading(view, {message="", trial=null, problems=null}={}) {
  const state=connectionText(view);
  const list=items=>items?.length?items.map(d=>`<span class="tag">${esc(d)}</span>`).join(" "):'<span class="muted">yok</span>';
  return `<section class="info-card extension-settings" id="extension-reading"><span class="eyebrow">EKLENTİYLE OKUMA</span><h2 style="margin-top:12px">Eklentinin deneme okuması</h2>
    <p>Programın kendi tarayıcısının giremediği bazı sitelere sizin günlük Chrome'unuz girebiliyor. Eklenti tıklamaz, yazı yazmaz, sekmelerinize, çerezlerinize, parolalarınıza ve geçmişinize erişmez; izin vermediğiniz siteye gitmez.</p>
    <p class="stage-note"><span class="note-mark">●</span><span><strong>Bağlantı:</strong> <span class="tag ${state.tone}" id="extension-connection">${esc(state.text)}</span> · eşleştirme kodu <a href="#settings/eklenti">Ayarlar → Tarayıcı eklentisi</a> bölümünde.</span></p>
    <p><strong>İzin verilen siteler:</strong> ${list(view.izinli_alan_adlari)}</p>
    <p><strong>İzin bekleyen siteler:</strong> ${list(view.izin_bekleyen_alan_adlari)} <small class="muted">İzni Chrome'da eklenti simgesine tıklayıp “İzin ver” ile siz verirsiniz.</small></p>
    ${queryList(view.izinli_sorgular)}
    <form id="extension-speed" class="toolbar video-form"><label>Aynı sitede iki sayfa arası en az (saniye)<input type="number" id="extension-gap" min="${view.aralik_sinirlari[0]}" max="${view.aralik_sinirlari[1]}" value="${esc(view.aralik_saniye)}"></label><button type="submit">Hızı kaydet</button></form>
    <div class="decision-actions"><button class="primary" id="extension-trial">Deneme</button><small class="muted">Eklentiyle programın kendi yerel deneme sayfasını açar (gerçek bir site değildir).</small></div>
    ${trial?`<div class="extension-trial-result">${trial.error?`<p class="stage-note claude-warning">${esc(trial.error)}</p>`:`<p><span class="tag ${trial.durum==="tamam"?"green":"warm"}">${esc(STATE_LABELS[trial.durum] || trial.durum)}</span> ${esc(trial.baslik || "")} · ${Math.round((trial.bayt||0)/1024)} KB · SHA-256 <code>${esc((trial.sha256||"").slice(0,16))}</code><small class="source-host">${esc(trial.dosya || "")}</small></p>`}</div>`:""}
    <h3>Sorunlu siteler</h3>
    <p class="muted">Raporlarda bu bilgisayardan okunamayan siteler: ${view.sorunlu_siteler.map(s=>esc(s.alan_adi)).join(", ")}. Düğme her siteden tek bir sayfayı eklentiyle okur ve sonucu tabloda gösterir; bölge engelli listedeki siteler eklentiyle değil, ABD proxy'si tanımlıysa onunla denenir (aşağıdaki bölüm). Bu düğmeye siz basarsınız.</p>
    <div class="decision-actions"><button id="extension-problems">Sorunlu sitelerden birer sayfa dene</button></div>
    ${problems?trialRows(problems):""}
    ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
  </section>`;
}

/** Veri → Okuma denemeleri: the warm-up list — the sites opened in the program's browser before a long collection (read only). */
export function warmUpSection(list) {
  const sites=list?.siteler || [];
  return `<section class="info-card" id="warm-up-list"><span class="eyebrow">ISINMA LİSTESİ</span><h2 style="margin-top:12px">Isınma listesi</h2>
    <p>Uzun bir çekimden önce programın tarayıcısında ayrı sekmelerde açılan siteler: bir kez doğrulama sayfası gösteren alan adları ve korumalı kiralama siteleri. Doğrulamayı siz geçersiniz; sonra çekim başlar. Liste veriden çıkar, elle değişmez.</p>
    ${sites.length?`<div class="table-scroll"><table class="reference-table"><thead><tr><th>ALAN ADI</th><th>SEBEP</th><th>İLK GÖRÜLME</th><th>SON GÖRÜLME</th></tr></thead><tbody>
      ${sites.map(s=>`<tr><td><strong>${esc(s.alan_adi)}</strong><small class="source-host">${esc(s.adres)}</small></td><td>${esc(s.sebep)}</td><td>${esc(s.ilk?date(s.ilk):"—")}</td><td>${esc(s.son?date(s.son):"—")}</td></tr>`).join("")}</tbody></table></div>`
      :'<p class="muted">Listede site yok.</p>'}
  </section>`;
}

class ExtensionBase {
  constructor(container) {this.container=container;this.view=null;this.message="";this.trial=null;this.problems=null;this.timer=null;this.sequence=0;}
  async load(message="") {
    try {
      const [view,jobs]=await Promise.all([api("tarayici-eklentisi"),api("jobs")]);
      const last=(jobs||[]).find(j=>j.kind==="eklenti_deneme" && j.result?.siteler);
      Object.assign(this,{view,message,problems:last?.result?.siteler || null});
      this.draw();
      if(!this.timer) this.timer=setInterval(()=>this.refresh(),5000);
    } catch(error) {if(!error.stale) this.container.textContent=error.message;}
  }
  /** The connection line every 5 s ("Eklenti çalışıyor: <site> · <durum>" while a job runs); stops when the section is gone. */
  async refresh() {
    if(!this.container.isConnected) {clearInterval(this.timer);this.timer=null;return;}
    const ticket=this.sequence;
    try {
      const fresh=await api("tarayici-eklentisi");
      if(ticket!==this.sequence) return;            // GÖREV-17: an answer that set out before "Kodu yenile" must not bring the old code back
      this.view={...this.view,...fresh};
      const tag=this.container.querySelector("#extension-connection");
      const state=connectionText(this.view);
      if(tag) {tag.textContent=state.text;tag.className=`tag ${state.tone}`;}
      const code=this.container.querySelector("#extension-code");       // a code renewed elsewhere shows here within seconds
      if(code && code.textContent!==this.view.kod) code.textContent=this.view.kod;
    } catch(error) { /* the next refresh tries again */ }
  }
}

/** Ayarlar → Tarayıcı eklentisi: the pairing code and the connection. */
export class ExtensionSettings extends ExtensionBase {
  draw() {
    this.container.innerHTML=extensionSection(this.view,{message:this.message});
    this.container.querySelector("#extension-renew").addEventListener("click",()=>this.renew());
  }
  async renew() {
    if(!globalThis.confirm?.("Eşleşme kodu yenilensin mi? Eklentiye yeni kodu yeniden yazmanız gerekecek.")) return;
    this.sequence++;
    try {this.view={...this.view,...await api("tarayici-eklentisi/kod-yenile",{method:"POST",body:"{}"})};this.message="Yeni kod üretildi; eklentiye bu kodu yazın.";}
    catch(error) {if(error.stale) return;this.message=error.message;}
    this.sequence++;
    this.draw();
  }
}

/** Veri → Okuma denemeleri: the extension's sites, speed and trial readings. */
export class ExtensionReading extends ExtensionBase {
  draw() {
    this.container.innerHTML=extensionReading(this.view,{message:this.message,trial:this.trial,problems:this.problems});
    this.container.querySelector("#extension-speed").addEventListener("submit",event=>{event.preventDefault();this.speed();});
    this.container.querySelector("#extension-trial").addEventListener("click",()=>this.runTrial());
    this.container.querySelector("#extension-problems").addEventListener("click",()=>this.runProblems());
  }
  async speed() {
    const value=Number(this.container.querySelector("#extension-gap").value);
    try {this.view={...this.view,...await api("tarayici-eklentisi/ayarlar",{method:"PUT",body:JSON.stringify({aralik_saniye:value})})};this.message="Hız kaydedildi.";}
    catch(error) {if(error.stale) return;this.message=error.message;}
    this.draw();
  }
  async runTrial() {
    this.trial=null;this.message="Eklenti deneme sayfasını açıyor…";this.draw();
    try {this.trial=await api("tarayici-eklentisi/deneme",{method:"POST",body:"{}"});this.message="";}
    catch(error) {if(error.stale) return;this.trial={error:error.message};this.message="";}
    await this.load(this.message);
  }
  async runProblems() {
    try {await api("tarayici-eklentisi/sorunlu-siteler",{method:"POST",body:"{}"});this.message="Sorunlu sitelerin denemesi başladı; ilerlemesi İşler panelinde, sonucu bu ekranda.";}
    catch(error) {if(error.stale) return;this.message=error.message;}
    this.draw();
  }
}
