import {api, esc, date} from "./api.js";

// GÖREV-14 (Adım 7): Settings → Tarayıcı eklentisi. The extension opens, in the user's own Chrome, the pages the program asks for and hands
// back only their content; this section shows its connection, the pairing code, the sites it may open, the speed, the install steps,
// a trial with the program's own local page and the trial of the problem sites (the user presses it).

const STATE_LABELS={tamam:"okundu",dogrulama:"doğrulama geçilmedi",giris:"giriş gerekiyor",odeme:"ödeme sayfası",izin_yok:"izin yok",hata:"hata"};

export function connectionText(view) {
  if(!view.eslesti) return {tone:"warm",text:"Eşleşmedi: eklentiyi kurup bu ekrandaki kodu eklentiye yazın."};
  if(view.bagli) return {tone:"green",text:`Bağlı · eklenti sürümü ${view.surum || "—"} · son görülme ${date(view.son_gorulme)}`};
  return {tone:"warm",text:`Bağlı değil (Chrome kapalı olabilir) · son görülme ${view.son_gorulme?date(view.son_gorulme):"—"}`};
}

export function trialRows(rows) {
  if(!rows?.length) return "";
  return `<div class="table-scroll"><table class="reference-table"><thead><tr><th>SİTE</th><th>DURUM</th><th>BAŞLIK</th><th>BOYUT</th><th>NOT</th></tr></thead><tbody>
    ${rows.map(r=>`<tr><td>${esc(r.alan_adi)}<small class="source-host">${esc(r.aciklama || "")}</small></td><td><span class="tag ${r.durum==="tamam"?"green":"warm"}">${esc(STATE_LABELS[r.durum] || r.durum)}</span></td>
      <td>${esc(r.baslik || "—")}</td><td>${r.bayt!=null?`${Math.round(r.bayt/1024)} KB`:"—"}</td><td>${esc(r.not || "")}${r.sha256?`<small class="source-host">SHA-256 ${esc(r.sha256.slice(0,12))}…</small>`:""}</td></tr>`).join("")}
    </tbody></table></div>`;
}

export function extensionSection(view, {message="", trial=null, problems=null}={}) {
  const state=connectionText(view);
  const list=items=>items?.length?items.map(d=>`<span class="tag">${esc(d)}</span>`).join(" "):'<span class="muted">yok</span>';
  return `<section class="info-card extension-settings" id="extension-settings"><span class="eyebrow">TARAYICI EKLENTİSİ</span><h2 style="margin-top:12px">Tarayıcı eklentisi</h2>
    <p>Programın kendi tarayıcısının giremediği bazı sitelere sizin günlük Chrome'unuz girebiliyor. “30A Studio Yardımcısı” eklentisi, programın istediği sayfaları Chrome'da kendi açtığı ayrı pencerede açar ve yalnız sayfanın içeriğini programa verir. Tıklamaz, yazı yazmaz, sekmelerinize, çerezlerinize, parolalarınıza ve geçmişinize erişmez; izin vermediğiniz siteye gitmez.</p>
    <p class="stage-note"><span class="note-mark">●</span><span><strong>Bağlantı:</strong> <span class="tag ${state.tone}">${esc(state.text)}</span></span></p>
    <div class="extension-code"><span class="eyebrow">EŞLEŞME KODU</span><strong id="extension-code">${esc(view.kod)}</strong>
      <button id="extension-renew" class="quiet">Kodu yenile</button><small class="muted">Kodu yenileyince eklentiye yeni kodu yeniden yazmanız gerekir.</small></div>
    <p><strong>İzin verilen siteler:</strong> ${list(view.izinli_alan_adlari)}</p>
    <p><strong>İzin bekleyen siteler:</strong> ${list(view.izin_bekleyen_alan_adlari)} <small class="muted">İzni Chrome'da eklenti simgesine tıklayıp “İzin ver” ile siz verirsiniz.</small></p>
    <form id="extension-speed" class="toolbar video-form"><label>Aynı sitede iki sayfa arası en az (saniye)<input type="number" id="extension-gap" min="${view.aralik_sinirlari[0]}" max="${view.aralik_sinirlari[1]}" value="${esc(view.aralik_saniye)}"></label><button type="submit">Hızı kaydet</button></form>
    <h3>Kurulum (bir kez)</h3>
    <ol class="extension-steps">${view.kurulum.map(step=>`<li>${esc(step)}</li>`).join("")}</ol>
    <p class="path">${esc(view.klasor)}</p>
    ${(view.kurulum_resimleri||[]).length?`<details class="extension-guide"><summary>Resimli kurulum rehberi</summary>${view.kurulum_resimleri.map(name=>`<img src="/eklenti-kurulum/${encodeURIComponent(name)}" alt="${esc(name)}" loading="lazy">`).join("")}<p class="muted">Rehberin tamamı eklenti klasöründeki KURULUM.md dosyasında.</p></details>`:""}
    <div class="decision-actions"><button class="primary" id="extension-trial">Deneme</button><small class="muted">Eklentiyle programın kendi yerel deneme sayfasını açar (gerçek bir site değildir).</small></div>
    ${trial?`<div class="extension-trial-result">${trial.error?`<p class="stage-note claude-warning">${esc(trial.error)}</p>`:`<p><span class="tag ${trial.durum==="tamam"?"green":"warm"}">${esc(STATE_LABELS[trial.durum] || trial.durum)}</span> ${esc(trial.baslik || "")} · ${Math.round((trial.bayt||0)/1024)} KB · SHA-256 <code>${esc((trial.sha256||"").slice(0,16))}</code><small class="source-host">${esc(trial.dosya || "")}</small></p>`}</div>`:""}
    <h3>Sorunlu siteler</h3>
    <p class="muted">Raporlarda bu bilgisayardan okunamayan siteler: ${view.sorunlu_siteler.map(s=>esc(s.alan_adi)).join(", ")}. Düğme her siteden tek bir sayfayı eklentiyle okur ve sonucu tabloda gösterir. Bu düğmeye siz basarsınız.</p>
    <div class="decision-actions"><button id="extension-problems">Sorunlu sitelerden birer sayfa dene</button></div>
    ${problems?trialRows(problems):""}
    ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
  </section>`;
}

export class ExtensionSettings {
  constructor(container) {this.container=container;this.view=null;this.message="";this.trial=null;this.problems=null;}
  async load(message="") {
    try {
      const [view,jobs]=await Promise.all([api("tarayici-eklentisi"),api("jobs")]);
      const last=(jobs||[]).find(j=>j.kind==="eklenti_deneme" && j.result?.siteler);
      Object.assign(this,{view,message,problems:last?.result?.siteler || null});
      this.draw();
    } catch(error) {if(!error.stale) this.container.textContent=error.message;}
  }
  draw() {
    this.container.innerHTML=extensionSection(this.view,{message:this.message,trial:this.trial,problems:this.problems});
    this.container.querySelector("#extension-renew").addEventListener("click",()=>this.renew());
    this.container.querySelector("#extension-speed").addEventListener("submit",event=>{event.preventDefault();this.speed();});
    this.container.querySelector("#extension-trial").addEventListener("click",()=>this.runTrial());
    this.container.querySelector("#extension-problems").addEventListener("click",()=>this.runProblems());
  }
  async renew() {
    if(!globalThis.confirm?.("Eşleşme kodu yenilensin mi? Eklentiye yeni kodu yeniden yazmanız gerekecek.")) return;
    try {this.view=await api("tarayici-eklentisi/kod-yenile",{method:"POST",body:"{}"});this.message="Yeni kod üretildi; eklentiye bu kodu yazın.";}
    catch(error) {if(error.stale) return;this.message=error.message;}
    this.draw();
  }
  async speed() {
    const value=Number(this.container.querySelector("#extension-gap").value);
    try {this.view=await api("tarayici-eklentisi/ayarlar",{method:"PUT",body:JSON.stringify({aralik_saniye:value})});this.message="Hız kaydedildi.";}
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
