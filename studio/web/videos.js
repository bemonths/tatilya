import {api, esc, date, destinationPath} from "./api.js";
import {linkSettingsMentions} from "./settings.js";
import {estimateBox, spendingLine} from "./estimate.js";
import {costLine} from "./claude-step.js";

// GÖREV-21: the topic bank ("Konu bankası", project layer). Title proposals from Claude ("Öneri al") and the evaluation of the user's
// own title; every run with its candidates (Turkish large, English small and pale); "Bu başlıkla video aç" on every free candidate.
// A candidate a video uses is marked "kullanıldı" with the video; the others stay in the pool. (GÖREV-13's "Videolar" screen was
// this and the video records together; the videos are now their own screen, studio/web/videolist.js.)
export const RUN_STATUS = {running:"Çalışıyor", awaiting_approval:"Havuzda", approved:"Aday kullanıldı", rejected:"Reddedildi", error:"Hata"};
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
  return lines.map(text=>`<p class="stage-note claude-warning" role="alert"><span class="note-mark">!</span><span>${linkSettingsMentions(esc(text))}</span></p>`).join("");
}

export function metricsText(run) {
  const m=run.metrics || {};
  const tokens=m.tokens?Math.round(((m.tokens.input||0)+(m.tokens.cache_creation||0)+(m.tokens.cache_read||0))/1000)+" bin girdi / "+Math.round((m.tokens.output||0)/1000)+" bin çıktı token":"";
  const calls=m.duzen==="tek_cagri"?`${m.cagri || 1} çağrı`:m.turns!=null?`${m.turns} tur (eski düzen)`:"";   // GÖREV-18: one call, no turns
  const parts=[calls, m.elapsed_s!=null?`${Math.round(m.elapsed_s)} sn`:"", tokens];
  return parts.filter(Boolean).join(" · ");
}

/** GÖREV-15 Adım 1d: an evaluation that wrote no candidate ("veriyle dolmuyor") is information, not waiting for approval. */
export function runStatusTag(run) {
  if(run.adaysiz) return `<span class="tag">${esc(run.bilgi || "Değerlendirildi: veriyle dolmuyor")}</span>`;
  if(run.canceled) return '<span class="tag warm">İptal edildi</span>';
  return `<span class="tag ${run.status==="error"?"warm":run.status==="approved"?"green":""}">${esc(RUN_STATUS[run.status] || run.status)}</span>`;
}

export function runRow(run) {
  const params=run.params || {};
  const review=run.step==="baslik_degerlendirme";
  return `<tr><td>${review?'<span class="tag">değerlendirme</span> ':""}<a class="source-name" href="#konu/calisma/${esc(run.id)}">${esc(params.bolge || "—")}${params.aile && params.aile!=="hepsi"?` · ${esc(params.aile)}`:""}</a>
    ${review?`<small class="source-host">“${esc(params.kullanici_basligi || "")}”</small>`:""}
    <small class="source-host">${run.correction_of?"düzeltme · ":""}${params.kaynak?"düzenlenen adaydan · ":""}${esc(String(params.not || params.duzeltme_notu || "not yok").split("\n")[0])}</small></td>
    <td>${esc(date(run.created_at))}</td><td>${runStatusTag(run)}
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

/** GÖREV-18 Adım 6: a title's marks — business names red, the phone's 40 characters, the cover text and capitals yellow. Information only. */
export function markList(marks) {
  if(!marks || !marks.length) return "";
  return `<ul class="mark-list">${marks.map(m=>`<li class="${m.seviye==="kirmizi"?"mark-red":"mark-yellow"}"><span class="sentence-mark ${m.seviye==="kirmizi"?"red":"yellow"}">●</span> ${esc(m.metin)}</li>`).join("")}</ul>`;
}

export function problemList(problems) {
  if(!problems || !problems.length) return "";
  return `<ul class="problem-list">${problems.map(p=>`<li class="${p.seviye==="hata"?"problem-error":"problem-warning"}">${p.seviye==="hata"?"Hata":"Uyarı"}: ${esc(p.metin)}</li>`).join("")}</ul>`;
}

export function candidateList(view, open, edit=null) {
  return `<ol class="candidate-list">${view.candidates.map(c=>`<li class="${c.sira===open?"open":""}"><button class="candidate-title" data-open-candidate="${c.sira}" aria-expanded="${c.sira===open}">
    <span class="title-tr-big small">${esc(c.baslik_tr)}</span><span class="title-en-small" lang="en">${esc(c.baslik_en)}</span>
    <span class="candidate-tags"><span class="tag">${esc(c.aile)}</span>${c.bolge!==view.params?.bolge?`<span class="tag">${esc(c.bolge)}</span>`:""}${c.video_id?'<span class="tag green">kullanıldı</span>':""}${c.sorunlar.some(p=>p.seviye==="hata")?'<span class="tag warm">doğrulama hatası</span>':""}${(c.isaretler||[]).some(m=>m.seviye==="kirmizi")?'<span class="tag error">işletme adı</span>':""}${(c.isaretler||[]).some(m=>m.seviye==="sari")?'<span class="tag warm">başlık uyarısı</span>':""}</span></button>
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
    <div id="edit-marks">${markList(edit.marks)}</div>
    <div class="decision-actions"><button class="primary" id="edit-select" ${problems.length?"disabled":""}>Düzenlenmiş başlıkla video aç</button>
      <button id="edit-translate" ${onlyTurkish?"":"hidden"}>İngilizcesini Claude yazsın</button>
      <button class="quiet" id="edit-cancel">Vazgeç</button></div>
    <p class="muted form-note">Yalnız Türkçe karşılığı değiştirdiyseniz “İngilizcesini Claude yazsın” bu Türkçe başlıkla bir değerlendirme çalışması başlatır; adayın analizi Claude'a not olarak verilir.</p></div>`;
}

export function candidateDetail(c, view, edit=null) {
  const plan=(c.icerik_plani || []).map(p=>`<li><strong>${esc(p.bolum)}</strong> — ${esc(p.ne_anlatir)}<ul class="evidence-list">${(p.kanitlar||[]).map(evidenceItem).join("") || "<li>kanıt yok</li>"}</ul></li>`).join("");
  const params=Object.entries(c.parametreler || {}).map(([k,v])=>`${k} = ${v}`).join(", ") || "yok";
  const canSelect=view.actions.select && c.secilebilir;
  return `<div class="candidate-detail">
    ${problemList(c.sorunlar)}${markList(c.isaretler)}
    <h3>Neden önerildi</h3><p>${esc(c.neden_onerildi)}</p>
    <h3>İzleyicinin sorusu</h3><p>${esc(c.izleyici_sorusu)}</p>
    <h3>Kanca</h3><p>${esc(c.kanca?.metin)}</p><ul class="evidence-list">${(c.kanca?.kanitlar||[]).map(evidenceItem).join("") || "<li>kanıt yok</li>"}</ul>
    <h3>İçerik planı</h3><ol class="plan-list">${plan}</ol>
    <h3>Eksik veri</h3>${(c.eksik_veri||[]).length?`<ul>${c.eksik_veri.map(m=>`<li>${esc(m)}</li>`).join("")}</ul>`:"<p>Yok.</p>"}
    <h3>Şablon ve parametreler</h3><p>${c.sablon?`<code>${esc(c.sablon)}</code> · parametreler: ${esc(params)}`:"Şablon yok: yeni şablon gerekir."}${c.yeni_sablon_gerekir&&c.sablon?" (yeni şablon da gerektiği yazılmış)":""}</p>
    <h3>Kapak fikri</h3><p>${esc(c.kapak_fikri)}</p>
    ${c.video_id?`<p class="stage-note">Kullanıldı: “${esc(c.video_adi || "video")}” videosunda. <a href="#video/${encodeURIComponent(c.video_id)}/baslik">Videoyu aç →</a></p>`:edit?editForm(c,edit,view.params?.baslik_eki):`<div class="decision-actions"><button class="primary" data-select-candidate="${c.sira}" ${canSelect?"":"disabled"}>Bu başlıkla video aç</button>
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
  const heading=view.step==="baslik_degerlendirme"?`Başlık değerlendirmesi · ${esc(params.bolge)}`:`Başlık önerileri · ${esc(params.bolge)}${params.aile && params.aile!=="hepsi"?` · ${esc(params.aile)}`:""}`;
  return `<section class="library claude-run"><div class="library-title"><h2>${heading}</h2>
      <small>${runStatusTag(view)} ${esc(date(view.created_at))}</small></div>
    <div class="run-meta">${esc(view.model_label || "—")} · efor: ${esc(view.effort_label || "—")}${view.claude_version?` · Claude Code ${esc(view.claude_version)}`:""} · ${esc(metricsText(view))}${summary.total_cost_usd?` · maliyet karşılığı ${summary.total_cost_usd.toFixed(2).replace(".",",")} $`:""}
      ${params.not?`<br>Not: ${esc(params.not)}`:""}${params.duzeltme_notu?`<br>Düzeltme notu: ${esc(params.duzeltme_notu)}`:""}</div>
    ${instructionLine(view)}
    ${spendingLine(view.harcama)}
    ${view.error?`<p class="stage-note claude-warning" role="alert"><span class="note-mark">!</span><span>${esc(view.error)}</span></p>`:""}
    ${view.general_problems?.length?`<div class="run-problems"><h3>Doğrulama sorunları</h3>${problemList(view.general_problems)}</div>`:""}
    ${view.status==="error" && (view.problems||[]).length?`<div class="run-problems"><h3>Doğrulama sorunları</h3>${problemList(view.problems)}</div>`:""}
    ${reviewSummary(view)}
    ${view.candidates.length?candidateList(view, open, edit):view.adaysiz?'<p class="stage-note run-empty">Değerlendirildi: fikir veriyle dolmuyor; seçilecek başlık yok. Bu bir bilgidir, onay beklemiyor. İsterseniz “Reddet” ile kapatabilirsiniz.</p>':'<p class="muted run-empty">Bu çalışmada gösterilecek öneri yok.</p>'}
    <div class="decision"><label>Çalışmanın bütünü için not<textarea id="decision-note" rows="3" maxlength="4000" placeholder="Bu öneri çalışması notunuzla yeniden çalıştırılsın istiyorsanız yazın"></textarea></label>
      ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
      <div class="decision-actions"><button id="run-correct" ${view.actions.correct && !busy?"":"disabled"}>Düzeltme iste</button>
      <button id="run-reject" class="quiet" ${view.actions.reject && !busy?"":"disabled"}>Reddet</button>
      <a class="source-link" href="/api/${destinationPath(`claude/runs/${view.id}/files/${view.markdown_file || "baslik.md"}`)}" download>Markdown ↓</a></div></div>
  </section>`;
}

/** The topic bank's list: every run with its candidates (Turkish large, English small and pale); a used candidate names its video. */
export function bankRuns(bank) {
  const runs=bank?.calismalar || [];
  if(!runs.length) return '<p class="muted run-empty">Henüz öneri çalışması yok. Yukarıdan “Öneri al” ile başlayın.</p>';
  return runs.map(run=>{
    const params=run.params || {}, review=run.step==="baslik_degerlendirme";
    const title=review?`Değerlendirme · “${esc(params.kullanici_basligi || "")}”`:`Öneri · ${esc(params.bolge || "—")}${params.aile && params.aile!=="hepsi"?` · ${esc(params.aile)}`:""}`;
    const candidates=(run.adaylar || []).map(c=>`<li class="${c.video_id?"used":""}"><a class="bank-candidate" href="#konu/calisma/${encodeURIComponent(run.id)}/${c.sira}">
        <span class="title-tr-big small">${esc(c.baslik_tr)}</span><span class="title-en-small" lang="en">${esc(c.baslik_en)}</span></a>
      <span class="candidate-tags"><span class="tag">${esc(c.aile || "—")}</span>${c.bolge && c.bolge!==params.bolge?`<span class="tag">${esc(c.bolge)}</span>`:""}
        ${c.video_id?`<span class="tag green">kullanıldı</span> <a class="source-link" href="#video/${encodeURIComponent(c.video_id)}/baslik">${esc(c.video_adi || "video")} →</a>`
          :c.secilebilir?`<button type="button" class="primary" data-open-video="${esc(run.id)}:${c.sira}">Bu başlıkla video aç</button>`:'<span class="tag warm">seçilemez</span>'}</span></li>`).join("");
    return `<article class="bank-run" data-bank-run="${esc(run.id)}"><div class="bank-run-head"><h3><a href="#konu/calisma/${encodeURIComponent(run.id)}">${title}</a></h3>
        <span>${runStatusTag(run)} <small class="muted">${esc(date(run.created_at))} · ${esc(run.model_label || run.model || "—")} · ${esc(metricsText(run))}</small></span></div>
      ${run.error && !run.canceled?`<p class="muted bank-run-error">${esc(run.error)}</p>`:""}
      ${candidates?`<ol class="bank-candidates">${candidates}</ol>`:run.status==="running"?'<p class="muted run-empty">Claude çalışıyor…</p>':run.adaysiz?'<p class="muted run-empty">Fikir veriyle dolmuyor; aday yok (bilgi).</p>':'<p class="muted run-empty">Bu çalışmada aday yok.</p>'}</article>`;
  }).join("");
}

export class BankScreen {
  constructor() {this.options=null;this.bank=null;this.view=null;this.open=null;this.busy=false;this.message="";this.form={bolge:"",aile:"hepsi",not:""};this.review={bolge:"",baslik:"",not:""};this.edit=null;this.sequence=0;this.runId=null;this.pending=null;this.markTimer=null;this.old=false;}
  /** The estimate first; the job starts only after "Başlat" (the same box on every Claude step). */
  async confirm(main, estimateCall, startCall, where="title") {
    this.busy=true;this.message="";this.pending=null;this.draw(main);
    try {
      const estimate=await estimateCall();
      this.pending={estimate, start:startCall, where};
    } catch(error) {if(error.stale) return;this.message=error.message;}
    finally {this.busy=false;this.draw(main);}
    main.querySelector("#title-estimate")?.scrollIntoView?.({block:"nearest"});
  }
  invalidate() {this.sequence++;}
  route() {
    const parts=location.hash.replace(/^#/,"").split("/");
    return parts[0]==="konu" && parts[1]==="calisma" && parts[2]?{runId:decodeURIComponent(parts[2]), candidate:parts[3]!=null?Number(parts[3]):null}:{runId:null, candidate:null};
  }
  render(main, data, heading) {
    const sequence=++this.sequence;
    const {runId, candidate}=this.route();
    if(runId!==this.runId) {this.open=candidate;this.message="";this.edit=null;this.pending=null;}
    else if(candidate!=null) this.open=candidate;
    this.runId=runId;
    main.innerHTML=heading("Konu bankası", `${data.selected_destination?.name || "Proje"} için başlık önerileri ve adayları. Her öneri çalışması bir konu havuzudur: bir adayla video açılınca o aday “kullanıldı” olur, ötekiler havuzda kalır.`)+
      `<div id="videos-body" aria-live="polite"><p>Yükleniyor…</p></div>`;
    Promise.all([api("claude/options"),api("konu-bankasi"),runId?api(`claude/runs/${encodeURIComponent(runId)}`):Promise.resolve(null)]).then(([options,bank,view])=>{
      if(sequence!==this.sequence) return;
      Object.assign(this,{options,bank,view});
      this.draw(main);
    }).catch(error=>{if(sequence===this.sequence && !error.stale) main.querySelector("#videos-body").textContent=error.message;});
  }
  draw(main) {
    const body=main.querySelector("#videos-body");
    if(!body || !this.options) return;
    if(!this.options.available) {body.innerHTML='<section class="quality-result empty"><h2>Kanal tanımı yok</h2><p>Bu proje için Claude adımları tanımlanmamış.</p></section>';return;}
    const runs=this.bank?.calismalar || [];
    const running=runs.some(r=>r.status==="running");
    const pending=where=>this.pending && this.pending.where===where?estimateBox(this.pending.estimate,{id:"title-estimate"}):"";
    const hint=running?"Bir Claude çalışması sürüyor; bitince yeni çalışma başlatabilirsiniz.":"Bölgeyi seçip düğmeye basınca hesaplanır; Claude “Başlat” demeden çalışmaz.";
    const form=`<section class="library evidence-form run-card"><div class="library-title"><h2>Öneri al</h2><small>Claude, kanal planı ve verinin yazar özetiyle 8–12 başlık önerir; hepsi havuza girer</small></div>
      ${warnings(this.options)}
      <div class="toolbar video-form"><label>Bölge <select id="title-region" required>${regionOptions(this.options,this.form.bolge)}</select></label>
      <label>İçerik ailesi <select id="title-family">${familyOptions(this.options,this.form.aile)}</select></label>
      <label class="grow">Not <input id="title-note" maxlength="4000" value="${esc(this.form.not)}" placeholder="İsteğe bağlı kısa yönlendirme"></label></div>
      <div class="run-card-foot">${costLine({hint})}<button class="primary" id="title-start" ${this.busy || running?"disabled":""}>${running?"Claude çalışıyor…":"Öneri al"}</button></div>
      ${pending("title")}${this.message && !this.view?`<p class="stage-note" role="status">${esc(this.message)}</p>`:""}</section>`;
    const own=`<section class="library evidence-form run-card" id="own-title"><div class="library-title"><h2>Kendi başlığını değerlendir</h2><small>Aklınızdaki başlığı ya da fikri yazın; Claude kanalın ölçüleriyle değerlendirir ve en çok 3 aday önerir</small></div>
      <div class="toolbar video-form"><label class="grow">Başlık ya da fikir <input id="review-title" maxlength="500" value="${esc(this.review.baslik)}" placeholder="Örn. Rosemary Beach'e köpeğimizle gitsek nasıl olur?"></label>
      <label>Bölge <select id="review-region" required>${regionOptions(this.options,this.review.bolge)}</select></label>
      <label class="grow">Not <input id="review-note" maxlength="4000" value="${esc(this.review.not)}" placeholder="İsteğe bağlı"></label></div>
      <div class="run-card-foot">${costLine({hint})}<button class="primary" id="review-start" ${this.busy || running?"disabled":""}>${running?"Claude çalışıyor…":"Claude değerlendirsin"}</button></div>${pending("review")}</section>`;
    const split=runs.length>4 && !this.old;
    const shown=split?{...this.bank,calismalar:runs.slice(0,4)}:this.bank;
    const list=`<section class="library"><div class="library-title"><h2>Öneri çalışmaları ve adayları</h2><small>${runs.length} çalışma · ${this.bank?.aday_sayisi ?? 0} aday · ${this.bank?.kullanilan ?? 0} kullanıldı · ${this.bank?.kullanilabilir ?? 0} havuzda</small></div>
      <div class="bank-runs">${bankRuns(shown)}</div>${split?`<p class="run-empty"><button type="button" class="link-button" id="bank-older">Önceki öneriler (${runs.length-4} çalışma daha)</button></p>`:""}</section>`;
    body.innerHTML=this.view?`<a href="#konu" class="return-link">← Konu bankası</a>${pending("run")}${runView(this.view,this.open,this.message,this.busy,this.edit)}`:`${form}${own}${list}`;
    body.querySelector("[data-estimate-start]")?.addEventListener("click",()=>{const job=this.pending;this.pending=null;job.start();});
    body.querySelector("[data-estimate-cancel]")?.addEventListener("click",()=>{this.pending=null;this.message="Vazgeçildi; Claude çalıştırılmadı.";this.draw(main);});
    body.querySelector("#bank-older")?.addEventListener("click",()=>{this.old=true;this.draw(main);});
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
      editBox.querySelector("#edit-en").addEventListener("input",e=>{this.edit.en=e.target.value;update();this.checkMarks(main,c);});
      editBox.querySelector("#edit-tr").addEventListener("input",e=>{this.edit.tr=e.target.value;update();});
      editBox.querySelector("#edit-cancel").addEventListener("click",()=>{this.edit=null;this.draw(main);});
      editBox.querySelector("#edit-select").addEventListener("click",()=>this.openVideo(main,this.view.id,this.edit.index,{baslik_en:this.edit.en,baslik_tr:this.edit.tr}));
      editBox.querySelector("#edit-translate").addEventListener("click",()=>this.translate(main));
    }
    body.querySelector("#title-region")?.addEventListener("change",e=>{this.form.bolge=e.target.value;});
    body.querySelector("#title-family")?.addEventListener("change",e=>{this.form.aile=e.target.value;});
    body.querySelector("#title-note")?.addEventListener("input",e=>{this.form.not=e.target.value;});
    body.querySelector("#title-start")?.addEventListener("click",()=>this.start(main));
    body.querySelectorAll("[data-open-candidate]").forEach(b=>b.addEventListener("click",()=>{const n=Number(b.dataset.openCandidate);this.open=this.open===n?null:n;this.draw(main);}));
    body.querySelectorAll("[data-select-candidate]").forEach(b=>b.addEventListener("click",()=>this.openVideo(main,this.view.id,Number(b.dataset.selectCandidate))));
    body.querySelectorAll("[data-open-video]").forEach(b=>b.addEventListener("click",()=>{const [run,index]=b.dataset.openVideo.split(":");this.openVideo(main,run,Number(index));}));
    body.querySelector("#run-correct")?.addEventListener("click",()=>this.decide(main,"correct"));
    body.querySelector("#run-reject")?.addEventListener("click",()=>this.decide(main,"reject"));
  }
  /** The marks of the edited English title, asked from the server while the user types (the business list is the data's). */
  checkMarks(main, c) {
    clearTimeout(this.markTimer);
    this.markTimer=setTimeout(async()=>{
      try {
        const found=await api("claude/title-check",{method:"POST",body:JSON.stringify({baslik_en:this.edit.en,kapak_fikri:c.kapak_fikri,bolge:c.bolge})});
        if(!this.edit) return;
        this.edit.marks=found.isaretler;
        const box=main.querySelector("#edit-marks");
        if(box) box.innerHTML=markList(found.isaretler);
      } catch(error) {/* the next keystroke asks again */}
    },300);
  }
  async start(main) {
    if(!this.form.bolge) {this.message="Önce bölge seçin.";this.draw(main);return;}
    if(this.options?.claude?.api_key_warning && !globalThis.confirm?.(this.options.claude.api_key_warning+" Yine de çalıştırılsın mı?")) return;
    const body=JSON.stringify({bolge:this.form.bolge,aile:this.form.aile,not:this.form.not});
    return this.confirm(main,()=>api("claude/title-runs/tahmin",{method:"POST",body}),()=>this.run(main,"claude/title-runs",body,"Claude çalışması başladı; ilerleme İşler panelinde. Bitince adaylar aşağıdaki listeye eklenir."),"title");
  }
  async startReview(main) {
    if(!this.review.baslik.trim()) {this.message="Önce başlığı ya da fikri yazın.";this.draw(main);return;}
    if(!this.review.bolge) {this.message="Önce bölge seçin.";this.draw(main);return;}
    if(this.options?.claude?.api_key_warning && !globalThis.confirm?.(this.options.claude.api_key_warning+" Yine de çalıştırılsın mı?")) return;
    const body=JSON.stringify({bolge:this.review.bolge,baslik:this.review.baslik,not:this.review.not});
    return this.confirm(main,()=>api("claude/review-runs/tahmin",{method:"POST",body}),()=>this.run(main,"claude/review-runs",body,"Claude başlığınızı değerlendiriyor; ilerleme İşler panelinde. Bitince değerlendirme ve adayları listeye eklenir."),"review");
  }
  async run(main, path, body, message) {
    this.busy=true;this.message="";this.draw(main);
    try {
      await api(path,{method:"POST",body});
      this.message=message;
      this.bank=await api("konu-bankasi");
    } catch(error) {if(error.stale) return;this.message=error.message;}
    finally {this.busy=false;this.draw(main);}
  }
  async translate(main) {
    const id=this.view.id, body=JSON.stringify({aday:this.edit.index,baslik_tr:this.edit.tr});
    return this.confirm(main,()=>api(`claude/runs/${encodeURIComponent(id)}/translate/tahmin`,{method:"POST",body}),()=>this.translateNow(main),"run");
  }
  async translateNow(main) {
    const id=this.view.id;
    this.busy=true;this.draw(main);
    try {
      const run=await api(`claude/runs/${encodeURIComponent(id)}/translate`,{method:"POST",body:JSON.stringify({aday:this.edit.index,baslik_tr:this.edit.tr})});
      this.edit=null;this.message="İngilizce başlık için bir değerlendirme çalışması başladı; ilerleme İşler panelinde.";
      location.hash=`#konu/calisma/${run.id}`;
    } catch(error) {if(error.stale) return;this.message=error.message;this.busy=false;this.draw(main);}
  }
  /** "Bu başlıkla video aç": the candidate becomes a video (marked used), the video opens and its first step waits for approval. */
  async openVideo(main, runId, index, edited=null) {
    this.busy=true;this.draw(main);
    try {
      const video=await api(`claude/runs/${encodeURIComponent(runId)}/select`,{method:"POST",body:JSON.stringify({aday:index,...(edited||{})})});
      this.edit=null;this.busy=false;
      document.dispatchEvent(new CustomEvent("studio:video-opened",{detail:{id:video.id,step:"baslik"}}));
    } catch(error) {if(error.stale) return;this.message=error.message;this.busy=false;this.draw(main);}
  }
  /** The bank's tools of a whole run: "Düzeltme iste" (a new run with the note; its estimate first) and "Reddet" (the run is closed). */
  async decide(main, kind, confirmed=false) {
    const note=main.querySelector("#decision-note")?.value || "";
    const id=this.view.id;
    if(kind==="correct" && !confirmed && !note.trim()) {this.message="“Düzeltme iste” için önce nota neyin değişmesini istediğinizi yazın.";return this.draw(main);}
    if(kind==="correct" && !confirmed) {
      return this.confirm(main,()=>api(`claude/runs/${encodeURIComponent(id)}/correct/tahmin`,{method:"POST",body:JSON.stringify({not:note})}),
        ()=>{this.correctNote=note;return this.decide(main,"correct",true);},"run");
    }
    this.busy=true;this.draw(main);
    try {
      const sent=kind==="correct" && confirmed?(this.correctNote ?? note):note;
      const result=await api(`claude/runs/${encodeURIComponent(id)}/${kind}`,{method:"POST",body:JSON.stringify({not:sent})});
      this.message=kind==="reject"?"Çalışma reddedildi.":"Düzeltme için yeni bir Claude çalışması başladı; ilerleme İşler panelinde.";
      if(kind==="correct") {location.hash=`#konu/calisma/${result.id}`;return;}
      [this.view,this.bank]=await Promise.all([api(`claude/runs/${encodeURIComponent(id)}`),api("konu-bankasi")]);
    } catch(error) {if(error.stale) return;this.message=error.message;}
    finally {this.busy=false;this.draw(main);}
  }
  async refresh(main) {
    try {
      const {runId}=this.route();
      [this.bank,this.view]=await Promise.all([api("konu-bankasi"),runId?api(`claude/runs/${encodeURIComponent(runId)}`):Promise.resolve(null)]);
      this.draw(main);
    } catch(error) {/* the next event refreshes */}
  }
}
