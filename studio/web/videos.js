import {api, esc, date, destinationPath} from "./api.js";

// GÖREV-13: the "Videolar" screen: topic and title proposals from Claude, the approval view (list of titles, then the chosen title's
// details), video records and their evidence packs.
export const RUN_STATUS = {running:"Çalışıyor", awaiting_approval:"Onay bekliyor", approved:"Seçildi", rejected:"Reddedildi", error:"Hata"};
const LABELS = {"kaynak gerçeği":"KG", "bizim hesabımız":"BH", "türetilmiş":"T", "yaklaşık":"Y"};

export function regionOptions(options, selected="") {
  const items=[options.whole_region, ...options.regions.map(r=>r.name)].filter(Boolean);
  return `<option value="">Bölge seçin…</option>`+items.map(name=>`<option value="${esc(name)}" ${name===selected?"selected":""}>${esc(name)}</option>`).join("");
}

export function familyOptions(options, selected="hepsi") {
  return [options.all_families, ...options.families].map(name=>`<option value="${esc(name)}" ${name===selected?"selected":""}>${esc(name)}</option>`).join("");
}

export function warnings(options) {
  const claude=options.claude || {};
  const lines=[];
  if(!claude.found) lines.push("Claude Code bulunamadı. Ayarlar → Claude bölümünden claude.exe'nin yolunu yazın.");
  if(claude.api_key_warning) lines.push(claude.api_key_warning);
  return lines.map(text=>`<p class="stage-note claude-warning" role="alert"><span class="note-mark">!</span><span>${esc(text)}</span></p>`).join("");
}

export function metricsText(run) {
  const m=run.metrics || {};
  const tokens=m.tokens?Math.round(((m.tokens.input||0)+(m.tokens.cache_creation||0)+(m.tokens.cache_read||0))/1000)+" bin girdi / "+Math.round((m.tokens.output||0)/1000)+" bin çıktı token":"";
  const parts=[m.turns!=null?`${m.turns} tur`:"", m.elapsed_s!=null?`${Math.round(m.elapsed_s)} sn`:"", tokens];
  return parts.filter(Boolean).join(" · ");
}

export function runRow(run) {
  const params=run.params || {};
  const review=run.step==="baslik_degerlendirme";
  return `<tr><td>${review?'<span class="tag">değerlendirme</span> ':""}<a class="source-name" href="#videos/run/${esc(run.id)}">${esc(params.bolge || "—")}${params.aile && params.aile!=="hepsi"?` · ${esc(params.aile)}`:""}</a>
    ${review?`<small class="source-host">“${esc(params.kullanici_basligi || "")}”</small>`:""}
    <small class="source-host">${run.correction_of?"düzeltme · ":""}${params.kaynak?"düzenlenen adaydan · ":""}${esc(String(params.not || params.duzeltme_notu || "not yok").split("\n")[0])}</small></td>
    <td>${esc(date(run.created_at))}</td><td><span class="tag ${run.status==="error"?"warm":run.status==="approved"?"green":""}">${esc(RUN_STATUS[run.status] || run.status)}</span>
    ${run.error?`<small class="source-host">${esc(run.error)}</small>`:""}</td>
    <td>${esc(run.model_label || run.model || "—")} · ${esc(run.effort_label || run.effort || "—")}<small class="source-host">${esc(metricsText(run))}</small></td></tr>`;
}

/** GÖREV-14: which version of each instruction file the run used (hash and the file's date), and whether the file still is that version. */
export function instructionLine(view) {
  const items=view.instruction_versions || [];
  if(!items.length) return "";
  return `<div class="run-meta instruction-versions">Talimat sürümü: ${items.map(i=>`${esc(i.name)} <code>${esc(i.short)}</code>${i.modified_at?` (${esc(date(i.modified_at))})`:""}${i.current?"":' <span class="tag warm">dosya o zamandan beri değişti</span>'}`).join(" · ")}</div>`;
}

export function evidenceItem(item) {
  if(item.durum==="bulunamadi") return `<li class="evidence-missing">${esc(item.kimlik)} · ${esc(item.dosya)}: bu kimlik özette yok</li>`;
  return `<li><span class="tag">${esc(item.kimlik)}</span> <span class="tag">${esc(LABELS[item.etiket] || "—")}</span> ${esc(item.ifade || "")}
    ${item.deger_metni && item.deger_metni!=="—"?`<strong>— ${esc(item.deger_metni)}</strong>`:""}<small class="source-host">${esc(item.dosya)} · paket ${esc(String(item.paket_id || "").slice(0,8))}</small></li>`;
}

export function problemList(problems) {
  if(!problems || !problems.length) return "";
  return `<ul class="problem-list">${problems.map(p=>`<li class="${p.seviye==="hata"?"problem-error":"problem-warning"}">${p.seviye==="hata"?"Hata":"Uyarı"}: ${esc(p.metin)}</li>`).join("")}</ul>`;
}

export function candidateList(view, open, edit=null) {
  return `<ol class="candidate-list">${view.candidates.map(c=>`<li class="${c.sira===open?"open":""}"><button class="candidate-title" data-open-candidate="${c.sira}" aria-expanded="${c.sira===open}">
    <span class="title-en">${esc(c.baslik_en)}</span><span class="title-tr">${esc(c.baslik_tr)}</span>
    <span class="candidate-tags"><span class="tag">${esc(c.aile)}</span>${c.bolge!==view.params?.bolge?`<span class="tag">${esc(c.bolge)}</span>`:""}${c.video_id?'<span class="tag green">seçildi</span>':""}${c.sorunlar.some(p=>p.seviye==="hata")?'<span class="tag warm">doğrulama hatası</span>':""}</span></button>
    ${c.sira===open?candidateDetail(c, view, edit && edit.index===c.sira?edit:null):""}</li>`).join("")}</ol>`;
}

/** The length and suffix rules of an edited title (the server checks the same; studio/ai/title.py title_problems). */
export function editProblems(en, tr, suffix={}) {
  const found=[];
  if(en.length>100) found.push(`İngilizce başlık 100 karakteri aşıyor (${en.length} karakter).`);
  if(!en.trim()) found.push("İngilizce başlık boş.");
  if(!tr.trim()) found.push("Türkçe karşılık boş.");
  if(suffix?.en && en && !en.endsWith(suffix.en)) found.push(`İngilizce başlık "${suffix.en}" ekiyle bitmiyor.`);
  if(suffix?.tr && tr && !tr.endsWith(suffix.tr)) found.push(`Türkçe karşılık "${suffix.tr}" ekiyle bitmiyor.`);
  return found;
}

/** GÖREV-14 Adım 5b: "Başlığı düzenle". When only the Turkish title changed, Claude can write the English one. */
export function editForm(c, edit, suffix={}) {
  const problems=editProblems(edit.en, edit.tr, suffix);
  const onlyTurkish=edit.en===c.baslik_en && edit.tr.trim()!==c.baslik_tr.trim();
  return `<div class="title-edit" data-edit-for="${c.sira}"><h3>Başlığı düzenle</h3>
    <label>İngilizce başlık<input id="edit-en" value="${esc(edit.en)}" maxlength="200"></label>
    <label>Türkçe karşılığı<input id="edit-tr" value="${esc(edit.tr)}" maxlength="300"></label>
    <p class="muted form-note">İngilizce başlık "${esc(suffix?.en || "")}" ekiyle, Türkçe karşılığı "${esc(suffix?.tr || "")}" ekiyle biter; İngilizce başlık en çok 100 karakter. <span id="edit-count">${edit.en.length}</span>/100</p>
    <ul class="problem-list" id="edit-problems">${problems.map(p=>`<li class="problem-error">${esc(p)}</li>`).join("")}</ul>
    <div class="decision-actions"><button class="primary" id="edit-select" ${problems.length?"disabled":""}>Düzenlenmiş başlığı seç</button>
      <button id="edit-translate" ${onlyTurkish?"":"hidden"}>İngilizcesini Claude yazsın</button>
      <button class="quiet" id="edit-cancel">Vazgeç</button></div>
    <p class="muted form-note">Yalnız Türkçe karşılığı değiştirdiyseniz “İngilizcesini Claude yazsın” bu Türkçe başlıkla bir değerlendirme çalışması başlatır; adayın analizi Claude'a not olarak verilir.</p></div>`;
}

export function candidateDetail(c, view, edit=null) {
  const plan=(c.icerik_plani || []).map(p=>`<li><strong>${esc(p.bolum)}</strong> — ${esc(p.ne_anlatir)}<ul class="evidence-list">${(p.kanitlar||[]).map(evidenceItem).join("") || "<li>kanıt yok</li>"}</ul></li>`).join("");
  const params=Object.entries(c.parametreler || {}).map(([k,v])=>`${k} = ${v}`).join(", ") || "yok";
  const canSelect=view.actions.select && c.secilebilir;
  return `<div class="candidate-detail">
    ${problemList(c.sorunlar)}
    <h3>Neden önerildi</h3><p>${esc(c.neden_onerildi)}</p>
    <h3>İzleyicinin sorusu</h3><p>${esc(c.izleyici_sorusu)}</p>
    <h3>Kanca</h3><p>${esc(c.kanca?.metin)}</p><ul class="evidence-list">${(c.kanca?.kanitlar||[]).map(evidenceItem).join("") || "<li>kanıt yok</li>"}</ul>
    <h3>İçerik planı</h3><ol class="plan-list">${plan}</ol>
    <h3>Eksik veri</h3>${(c.eksik_veri||[]).length?`<ul>${c.eksik_veri.map(m=>`<li>${esc(m)}</li>`).join("")}</ul>`:"<p>Yok.</p>"}
    <h3>Şablon ve parametreler</h3><p>${c.sablon?`<code>${esc(c.sablon)}</code> · parametreler: ${esc(params)}`:"Şablon yok: yeni şablon gerekir."}${c.yeni_sablon_gerekir&&c.sablon?" (yeni şablon da gerektiği yazılmış)":""}</p>
    <h3>Kapak fikri</h3><p>${esc(c.kapak_fikri)}</p>
    ${c.video_id?'<p class="stage-note">Bu başlık seçildi; video kaydı aşağıdaki listede.</p>':edit?editForm(c,edit,view.params?.baslik_eki):`<div class="decision-actions"><button class="primary" data-select-candidate="${c.sira}" ${canSelect?"":"disabled"}>Bu başlığı seç</button>
      <button data-edit-candidate="${c.sira}" ${canSelect?"":"disabled"}>Başlığı düzenle</button></div>`}
    ${!c.secilebilir && !c.video_id?'<p class="muted">Bu adayda doğrulama hatası var; seçilemez.</p>':""}
  </div>`;
}

/** GÖREV-14 Adım 5a: the evaluation of the user's own title, shown before its candidates. */
export function reviewSummary(view) {
  const r=view.review;
  if(!r) return "";
  const fill=r.doluluk || {};
  return `<div class="review-summary"><h3>Değerlendirme</h3>
    <p><strong>Kullanıcının fikri:</strong> “${esc(r.kullanici_fikri)}”</p>
    <p><strong>Veriyle doluyor mu:</strong> <span class="tag ${fill.dolar_mi?"green":"warm"}">${fill.dolar_mi?"Evet":"Hayır"}</span> ${esc(fill.aciklama || "")}</p>
    <p><strong>Eksik veri:</strong> ${(fill.eksik_veri||[]).length?esc(fill.eksik_veri.join("; ")):"yok"}</p>
    <p><strong>İfadedeki sorunlar:</strong> ${(r.sorunlar||[]).length?esc(r.sorunlar.join("; ")):"yok"}</p>
    ${view.params?.kaynak?`<p class="muted">Bu değerlendirme düzenlenen bir adaydan başladı: “${esc(view.params.kaynak.baslik_en)}”.</p>`:""}</div>`;
}

export function runView(view, open, message="", busy=false, edit=null) {
  const params=view.params || {};
  const summary=view.summary || {};
  const heading=view.step==="baslik_degerlendirme"?`Başlık değerlendirmesi · ${esc(params.bolge)}`:`Konu ve başlık önerileri · ${esc(params.bolge)}${params.aile && params.aile!=="hepsi"?` · ${esc(params.aile)}`:""}`;
  return `<section class="library claude-run"><div class="library-title"><h2>${heading}</h2>
      <small><span class="tag ${view.status==="error"?"warm":view.status==="approved"?"green":""}">${esc(RUN_STATUS[view.status] || view.status)}</span> ${esc(date(view.created_at))}</small></div>
    <div class="run-meta">${esc(view.model_label || "—")} · efor: ${esc(view.effort_label || "—")}${view.claude_version?` · Claude Code ${esc(view.claude_version)}`:""} · ${esc(metricsText(view))}${summary.total_cost_usd?` · maliyet karşılığı ${summary.total_cost_usd.toFixed(2).replace(".",",")} $`:""}
      ${params.not?`<br>Not: ${esc(params.not)}`:""}${params.duzeltme_notu?`<br>Düzeltme notu: ${esc(params.duzeltme_notu)}`:""}</div>
    ${instructionLine(view)}
    ${view.error?`<p class="stage-note claude-warning" role="alert"><span class="note-mark">!</span><span>${esc(view.error)}</span></p>`:""}
    ${view.general_problems?.length?`<div class="run-problems"><h3>Doğrulama sorunları</h3>${problemList(view.general_problems)}</div>`:""}
    ${view.status==="error" && (view.problems||[]).length?`<div class="run-problems"><h3>Doğrulama sorunları</h3>${problemList(view.problems)}</div>`:""}
    ${reviewSummary(view)}
    ${view.candidates.length?candidateList(view, open, edit):'<p class="muted run-empty">Bu çalışmada gösterilecek öneri yok.</p>'}
    <div class="decision"><label>Not<textarea id="decision-note" rows="3" maxlength="4000" placeholder="Seçim ya da düzeltme için notunuz"></textarea></label>
      ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
      <div class="decision-actions"><button id="run-correct" ${view.actions.correct && !busy?"":"disabled"}>Düzeltme iste</button>
      <button id="run-reject" class="quiet" ${view.actions.reject && !busy?"":"disabled"}>Reddet</button>
      <a class="source-link" href="/api/${destinationPath(`claude/runs/${view.id}/files/${view.markdown_file || "baslik.md"}`)}" download>Markdown ↓</a></div></div>
  </section>`;
}

export function videoCard(video) {
  const a=video.analysis || {};
  const pack=video.packs?.[0];
  return `<article class="video-card"><div class="video-head"><div><strong>${esc(video.title_en)}</strong><small>${esc(video.title_tr)}</small></div>
    <span><span class="tag ${video.status==="paket_hazir"?"green":""}">${esc(video.status_label || video.status)}</span>${video.user_edited?' <span class="tag warm">kullanıcı düzenledi</span>':""}</span></div>
    ${video.user_edited?`<p class="muted">Önerilen başlık: ${esc(video.proposed_title_en)} · ${esc(video.proposed_title_tr)}</p>`:""}
    <p class="muted">${esc(video.region_name)} · ${esc(video.family)} · ${esc(date(video.created_at))} · ${video.template_key?`şablon <code>${esc(video.template_key)}</code>`:"yeni şablon gerekir (bilgi)"}</p>
    <details><summary>Analiz</summary><p><strong>İzleyicinin sorusu:</strong> ${esc(a.izleyici_sorusu)}</p><p><strong>Neden önerildi:</strong> ${esc(a.neden_onerildi)}</p>
      <p><strong>Kanca:</strong> ${esc(a.kanca?.metin)}</p><ol>${(a.icerik_plani||[]).map(p=>`<li>${esc(p.bolum)} — ${esc(p.ne_anlatir)}</li>`).join("")}</ol></details>
    <div class="video-actions"><button data-video-pack="${esc(video.id)}">Kanıt paketi üret</button>
      <small class="muted">Paket seçilen başlığın içerik planından kurulur.</small>
      ${pack?`<a class="source-link" href="/api/${destinationPath(`evidence-packs/${pack.id}/yazar-ozeti`)}" download>Yazar özeti ↓</a><a class="source-link" href="/api/${destinationPath(`evidence-packs/${pack.id}/markdown`)}" download>Tam paket ↓</a>`:""}</div>
  </article>`;
}

export class VideosScreen {
  constructor() {this.options=null;this.runs=null;this.videos=null;this.view=null;this.open=null;this.busy=false;this.message="";this.form={bolge:"",aile:"hepsi",not:""};this.review={bolge:"",baslik:"",not:""};this.edit=null;this.sequence=0;this.runId=null;}
  invalidate() {this.sequence++;}
  runFromHash() { return location.hash.startsWith("#videos/run/") ? decodeURIComponent(location.hash.slice("#videos/run/".length)) : null; }
  render(main, data, heading) {
    const sequence=++this.sequence;
    const runId=this.runFromHash();
    if(runId!==this.runId) {this.open=null;this.message="";this.edit=null;}
    this.runId=runId;
    main.innerHTML=heading("Konu ve başlık", `${data.selected_destination?.name || "Destinasyon"} için Claude'dan konu ve başlık önerisi alın; seçtiğiniz başlık bir video kaydı olur ve kanıt paketi bu kayıtla kurulur.`)+
      `<div id="videos-body" aria-live="polite"><p>Yükleniyor…</p></div>`;
    Promise.all([api("claude/options"),api("claude/runs"),api("videos"),runId?api(`claude/runs/${encodeURIComponent(runId)}`):Promise.resolve(null)]).then(([options,runs,videos,view])=>{
      if(sequence!==this.sequence) return;
      Object.assign(this,{options,runs,videos,view});
      this.draw(main);
    }).catch(error=>{if(sequence===this.sequence && !error.stale) main.querySelector("#videos-body").textContent=error.message;});
  }
  draw(main) {
    const body=main.querySelector("#videos-body");
    if(!body || !this.options) return;
    if(!this.options.available) {body.innerHTML='<section class="quality-result empty"><h2>Kanal tanımı yok</h2><p>Bu destinasyon için Claude adımları tanımlanmamış.</p></section>';return;}
    const running=(this.runs || []).some(r=>r.status==="running");
    const form=`<section class="library evidence-form"><div class="library-title"><h2>Konu ve başlık önerisi al</h2><small>Claude, kanal planı ve verinin yazar özetiyle 8–12 başlık önerir; seçim sizindir.</small></div>
      ${warnings(this.options)}
      <div class="toolbar video-form"><label>Bölge <select id="title-region" required>${regionOptions(this.options,this.form.bolge)}</select></label>
      <label>İçerik ailesi <select id="title-family">${familyOptions(this.options,this.form.aile)}</select></label>
      <label class="grow">Not <input id="title-note" maxlength="4000" value="${esc(this.form.not)}" placeholder="İsteğe bağlı kısa yönlendirme"></label>
      <button class="primary" id="title-start" ${this.busy || running?"disabled":""}>${running?"Claude çalışıyor…":"Konu ve başlık önerisi al"}</button></div>
      ${this.message && !this.view?`<p class="stage-note" role="status">${esc(this.message)}</p>`:""}</section>`;
    const own=`<section class="library evidence-form" id="own-title"><div class="library-title"><h2>Kendi başlığını yaz</h2><small>Aklınızdaki başlığı ya da fikri yazın (Türkçe ya da İngilizce); Claude kanalın ölçüleriyle değerlendirir, veri yetmiyorsa açıkça söyler ve en çok 3 başlık önerir.</small></div>
      <div class="toolbar video-form"><label class="grow">Başlık ya da fikir <input id="review-title" maxlength="500" value="${esc(this.review.baslik)}" placeholder="Örn. Rosemary Beach'e köpeğimizle gitsek nasıl olur?"></label>
      <label>Bölge <select id="review-region" required>${regionOptions(this.options,this.review.bolge)}</select></label>
      <label class="grow">Not <input id="review-note" maxlength="4000" value="${esc(this.review.not)}" placeholder="İsteğe bağlı"></label>
      <button class="primary" id="review-start" ${this.busy || running?"disabled":""}>${running?"Claude çalışıyor…":"Claude değerlendirsin"}</button></div></section>`;
    const runs=`<section class="library"><div class="library-title"><h2>Öneri ve değerlendirme çalışmaları</h2><small>${(this.runs||[]).length} çalışma</small></div>
      ${(this.runs||[]).length?`<div class="table-scroll"><table class="reference-table"><thead><tr><th>BÖLGE · AİLE</th><th>ZAMAN</th><th>DURUM</th><th>MODEL · ÖLÇÜM</th></tr></thead><tbody>${this.runs.map(runRow).join("")}</tbody></table></div>`:'<p class="muted run-empty">Henüz öneri çalışması yok.</p>'}</section>`;
    const videos=`<section class="library"><div class="library-title"><h2>Video kayıtları</h2><small>${(this.videos||[]).length} video</small></div>
      ${(this.videos||[]).length?`<div class="video-list">${this.videos.map(videoCard).join("")}</div>`:'<p class="muted run-empty">Henüz seçilmiş başlık yok.</p>'}</section>`;
    body.innerHTML=this.view?`<a href="#videos" class="return-link">← Konu ve başlık</a>${runView(this.view,this.open,this.message,this.busy,this.edit)}${videos}`:`${form}${own}${runs}${videos}`;
    body.querySelector("#review-title")?.addEventListener("input",e=>{this.review.baslik=e.target.value;});
    body.querySelector("#review-region")?.addEventListener("change",e=>{this.review.bolge=e.target.value;});
    body.querySelector("#review-note")?.addEventListener("input",e=>{this.review.not=e.target.value;});
    body.querySelector("#review-start")?.addEventListener("click",()=>this.startReview(main));
    body.querySelectorAll("[data-edit-candidate]").forEach(b=>b.addEventListener("click",()=>{const n=Number(b.dataset.editCandidate);const c=this.view.candidates.find(x=>x.sira===n);this.edit={index:n,en:c.baslik_en,tr:c.baslik_tr};this.draw(main);}));
    const editBox=body.querySelector(".title-edit");
    if(editBox) {
      const c=this.view.candidates.find(x=>x.sira===this.edit.index), suffix=this.view.params?.baslik_eki || {};
      const update=()=>{
        const problems=editProblems(this.edit.en,this.edit.tr,suffix);
        editBox.querySelector("#edit-problems").innerHTML=problems.map(p=>`<li class="problem-error">${esc(p)}</li>`).join("");
        editBox.querySelector("#edit-count").textContent=String(this.edit.en.length);
        editBox.querySelector("#edit-select").disabled=problems.length>0 || this.busy;
        editBox.querySelector("#edit-translate").hidden=!(this.edit.en===c.baslik_en && this.edit.tr.trim()!==c.baslik_tr.trim());
      };
      editBox.querySelector("#edit-en").addEventListener("input",e=>{this.edit.en=e.target.value;update();});
      editBox.querySelector("#edit-tr").addEventListener("input",e=>{this.edit.tr=e.target.value;update();});
      editBox.querySelector("#edit-cancel").addEventListener("click",()=>{this.edit=null;this.draw(main);});
      editBox.querySelector("#edit-select").addEventListener("click",()=>this.decide(main,"select",this.edit.index,{baslik_en:this.edit.en,baslik_tr:this.edit.tr}));
      editBox.querySelector("#edit-translate").addEventListener("click",()=>this.translate(main));
    }
    body.querySelector("#title-region")?.addEventListener("change",e=>{this.form.bolge=e.target.value;});
    body.querySelector("#title-family")?.addEventListener("change",e=>{this.form.aile=e.target.value;});
    body.querySelector("#title-note")?.addEventListener("input",e=>{this.form.not=e.target.value;});
    body.querySelector("#title-start")?.addEventListener("click",()=>this.start(main));
    body.querySelectorAll("[data-open-candidate]").forEach(b=>b.addEventListener("click",()=>{const n=Number(b.dataset.openCandidate);this.open=this.open===n?null:n;this.draw(main);}));
    body.querySelectorAll("[data-select-candidate]").forEach(b=>b.addEventListener("click",()=>this.decide(main,"select",Number(b.dataset.selectCandidate))));
    body.querySelector("#run-correct")?.addEventListener("click",()=>this.decide(main,"correct"));
    body.querySelector("#run-reject")?.addEventListener("click",()=>this.decide(main,"reject"));
    body.querySelectorAll("[data-video-pack]").forEach(b=>b.addEventListener("click",()=>this.pack(main,b.dataset.videoPack)));
  }
  async start(main) {
    if(!this.form.bolge) {this.message="Önce bölge seçin.";this.draw(main);return;}
    if(this.options?.claude?.api_key_warning && !globalThis.confirm?.(this.options.claude.api_key_warning+" Yine de çalıştırılsın mı?")) return;
    this.busy=true;this.message="";this.draw(main);
    try {
      await api("claude/title-runs",{method:"POST",body:JSON.stringify({bolge:this.form.bolge,aile:this.form.aile,not:this.form.not})});
      this.message="Claude çalışması başladı; ilerleme İşler panelinde. Bitince öneriler listede onay bekler.";
      this.runs=await api("claude/runs");
    } catch(error) {if(error.stale) return;this.message=error.message;}
    finally {this.busy=false;this.draw(main);}
  }
  async startReview(main) {
    if(!this.review.baslik.trim()) {this.message="Önce başlığı ya da fikri yazın.";this.draw(main);return;}
    if(!this.review.bolge) {this.message="Önce bölge seçin.";this.draw(main);return;}
    if(this.options?.claude?.api_key_warning && !globalThis.confirm?.(this.options.claude.api_key_warning+" Yine de çalıştırılsın mı?")) return;
    this.busy=true;this.message="";this.draw(main);
    try {
      const run=await api("claude/review-runs",{method:"POST",body:JSON.stringify({bolge:this.review.bolge,baslik:this.review.baslik,not:this.review.not})});
      this.message="Claude başlığınızı değerlendiriyor; ilerleme İşler panelinde. Bitince değerlendirme ve adaylar burada onay bekler.";
      this.runs=await api("claude/runs");
      document.dispatchEvent(new CustomEvent("studio:workflow-changed"));
      void run;
    } catch(error) {if(error.stale) return;this.message=error.message;}
    finally {this.busy=false;this.draw(main);}
  }
  async translate(main) {
    const id=this.view.id;
    this.busy=true;this.draw(main);
    try {
      const run=await api(`claude/runs/${encodeURIComponent(id)}/translate`,{method:"POST",body:JSON.stringify({aday:this.edit.index,baslik_tr:this.edit.tr})});
      this.edit=null;this.message="İngilizce başlık için bir değerlendirme çalışması başladı; ilerleme İşler panelinde.";
      location.hash=`#videos/run/${run.id}`;
    } catch(error) {if(error.stale) return;this.message=error.message;this.busy=false;this.draw(main);}
  }
  async decide(main, kind, index=null, edited=null) {
    const note=main.querySelector("#decision-note")?.value || "";
    const id=this.view.id;
    this.busy=true;this.draw(main);
    try {
      const result=await api(`claude/runs/${encodeURIComponent(id)}/${kind}`,{method:"POST",body:JSON.stringify(kind==="select"?{aday:index,not:note,...(edited||{})}:{not:note})});
      if(kind==="select") this.edit=null;
      this.message=kind==="select"?`Video kaydı oluşturuldu: ${result.title_en}${result.user_edited?" (düzenlenmiş başlık)":""}`:kind==="reject"?"Çalışma reddedildi.":"Düzeltme için yeni bir Claude çalışması başladı; ilerleme İşler panelinde.";
      if(kind==="correct") {location.hash=`#videos/run/${result.id}`;return;}
      if(kind==="select") document.dispatchEvent(new CustomEvent("studio:video-chosen",{detail:result.id}));
      else document.dispatchEvent(new CustomEvent("studio:workflow-changed"));
      [this.view,this.videos,this.runs]=await Promise.all([api(`claude/runs/${encodeURIComponent(id)}`),api("videos"),api("claude/runs")]);
    } catch(error) {if(error.stale) return;this.message=error.message;}
    finally {this.busy=false;this.draw(main);}
  }
  async pack(main, videoId) {
    this.busy=true;
    try {
      await api(`videos/${encodeURIComponent(videoId)}/evidence-pack`,{method:"POST",body:"{}"});
      this.message="Video için kanıt paketi üretildi.";this.videos=await api("videos");
      document.dispatchEvent(new CustomEvent("studio:workflow-changed"));
    } catch(error) {if(error.stale) return;this.message=error.message;}
    finally {this.busy=false;this.draw(main);}
  }
  async refresh(main) {
    try {
      const runId=this.runFromHash();
      [this.runs,this.videos,this.view]=await Promise.all([api("claude/runs"),api("videos"),runId?api(`claude/runs/${encodeURIComponent(runId)}`):Promise.resolve(null)]);
      this.draw(main);
    } catch(error) {/* the next event refreshes */}
  }
}
