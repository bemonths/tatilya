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
  return `<tr><td><a class="source-name" href="#videos/run/${esc(run.id)}">${esc(params.bolge || "—")}${params.aile && params.aile!=="hepsi"?` · ${esc(params.aile)}`:""}</a>
    <small class="source-host">${run.correction_of?"düzeltme · ":""}${esc(params.not || params.duzeltme_notu || "not yok")}</small></td>
    <td>${esc(date(run.created_at))}</td><td><span class="tag ${run.status==="error"?"warm":run.status==="approved"?"green":""}">${esc(RUN_STATUS[run.status] || run.status)}</span>
    ${run.error?`<small class="source-host">${esc(run.error)}</small>`:""}</td>
    <td>${esc(run.model_label || run.model || "—")} · ${esc(run.effort_label || run.effort || "—")}<small class="source-host">${esc(metricsText(run))}</small></td></tr>`;
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

export function candidateList(view, open) {
  return `<ol class="candidate-list">${view.candidates.map(c=>`<li class="${c.sira===open?"open":""}"><button class="candidate-title" data-open-candidate="${c.sira}" aria-expanded="${c.sira===open}">
    <span class="title-en">${esc(c.baslik_en)}</span><span class="title-tr">${esc(c.baslik_tr)}</span>
    <span class="candidate-tags"><span class="tag">${esc(c.aile)}</span>${c.bolge!==view.params?.bolge?`<span class="tag">${esc(c.bolge)}</span>`:""}${c.video_id?'<span class="tag green">seçildi</span>':""}${c.sorunlar.some(p=>p.seviye==="hata")?'<span class="tag warm">doğrulama hatası</span>':""}</span></button>
    ${c.sira===open?candidateDetail(c, view):""}</li>`).join("")}</ol>`;
}

export function candidateDetail(c, view) {
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
    ${c.video_id?'<p class="stage-note">Bu başlık seçildi; video kaydı aşağıdaki listede.</p>':`<button class="primary" data-select-candidate="${c.sira}" ${canSelect?"":"disabled"}>Bu başlığı seç</button>`}
    ${!c.secilebilir && !c.video_id?'<p class="muted">Bu adayda doğrulama hatası var; seçilemez.</p>':""}
  </div>`;
}

export function runView(view, open, message="", busy=false) {
  const params=view.params || {};
  const summary=view.summary || {};
  return `<section class="library claude-run"><div class="library-title"><h2>Konu ve başlık önerileri · ${esc(params.bolge)}${params.aile && params.aile!=="hepsi"?` · ${esc(params.aile)}`:""}</h2>
      <small><span class="tag ${view.status==="error"?"warm":view.status==="approved"?"green":""}">${esc(RUN_STATUS[view.status] || view.status)}</span> ${esc(date(view.created_at))}</small></div>
    <div class="run-meta">${esc(view.model_label || "—")} · efor: ${esc(view.effort_label || "—")}${view.claude_version?` · Claude Code ${esc(view.claude_version)}`:""} · ${esc(metricsText(view))}${summary.total_cost_usd?` · maliyet karşılığı ${summary.total_cost_usd.toFixed(2).replace(".",",")} $`:""}
      ${params.not?`<br>Not: ${esc(params.not)}`:""}${params.duzeltme_notu?`<br>Düzeltme notu: ${esc(params.duzeltme_notu)}`:""}</div>
    ${view.error?`<p class="stage-note claude-warning" role="alert"><span class="note-mark">!</span><span>${esc(view.error)}</span></p>`:""}
    ${view.general_problems?.length?`<div class="run-problems"><h3>Doğrulama sorunları</h3>${problemList(view.general_problems)}</div>`:""}
    ${view.status==="error" && (view.problems||[]).length?`<div class="run-problems"><h3>Doğrulama sorunları</h3>${problemList(view.problems)}</div>`:""}
    ${view.candidates.length?candidateList(view, open):'<p class="muted run-empty">Bu çalışmada gösterilecek öneri yok.</p>'}
    <div class="decision"><label>Not<textarea id="decision-note" rows="3" maxlength="4000" placeholder="Seçim ya da düzeltme için notunuz"></textarea></label>
      ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}
      <div class="decision-actions"><button id="run-correct" ${view.actions.correct && !busy?"":"disabled"}>Düzeltme iste</button>
      <button id="run-reject" class="quiet" ${view.actions.reject && !busy?"":"disabled"}>Reddet</button>
      <a class="source-link" href="/api/${destinationPath(`claude/runs/${view.id}/files/baslik.md`)}" download>Markdown ↓</a></div></div>
  </section>`;
}

export function videoCard(video) {
  const a=video.analysis || {};
  const pack=video.packs?.[0];
  return `<article class="video-card"><div class="video-head"><div><strong>${esc(video.title_en)}</strong><small>${esc(video.title_tr)}</small></div>
    <span class="tag ${video.status==="paket_hazir"?"green":""}">${esc(video.status_label || video.status)}</span></div>
    <p class="muted">${esc(video.region_name)} · ${esc(video.family)} · ${esc(date(video.created_at))} · ${video.template_key?`şablon <code>${esc(video.template_key)}</code>`:"yeni şablon gerekir"}</p>
    <details><summary>Analiz</summary><p><strong>İzleyicinin sorusu:</strong> ${esc(a.izleyici_sorusu)}</p><p><strong>Neden önerildi:</strong> ${esc(a.neden_onerildi)}</p>
      <p><strong>Kanca:</strong> ${esc(a.kanca?.metin)}</p><ol>${(a.icerik_plani||[]).map(p=>`<li>${esc(p.bolum)} — ${esc(p.ne_anlatir)}</li>`).join("")}</ol></details>
    <div class="video-actions"><button data-video-pack="${esc(video.id)}" ${video.template_key?"":"disabled"}>Kanıt paketi üret</button>
      ${video.template_key?"":'<small class="muted">Bu başlık için yeni şablon gerekir; paket üretilemez.</small>'}
      ${pack?`<a class="source-link" href="/api/${destinationPath(`evidence-packs/${pack.id}/yazar-ozeti`)}" download>Yazar özeti ↓</a><a class="source-link" href="/api/${destinationPath(`evidence-packs/${pack.id}/markdown`)}" download>Tam paket ↓</a>`:""}</div>
  </article>`;
}

export class VideosScreen {
  constructor() {this.options=null;this.runs=null;this.videos=null;this.view=null;this.open=null;this.busy=false;this.message="";this.form={bolge:"",aile:"hepsi",not:""};this.sequence=0;this.runId=null;}
  invalidate() {this.sequence++;}
  runFromHash() { return location.hash.startsWith("#videos/run/") ? decodeURIComponent(location.hash.slice("#videos/run/".length)) : null; }
  render(main, data, heading) {
    const sequence=++this.sequence;
    const runId=this.runFromHash();
    if(runId!==this.runId) {this.open=null;this.message="";}
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
    const runs=`<section class="library"><div class="library-title"><h2>Öneri çalışmaları</h2><small>${(this.runs||[]).length} çalışma</small></div>
      ${(this.runs||[]).length?`<div class="table-scroll"><table class="reference-table"><thead><tr><th>BÖLGE · AİLE</th><th>ZAMAN</th><th>DURUM</th><th>MODEL · ÖLÇÜM</th></tr></thead><tbody>${this.runs.map(runRow).join("")}</tbody></table></div>`:'<p class="muted run-empty">Henüz öneri çalışması yok.</p>'}</section>`;
    const videos=`<section class="library"><div class="library-title"><h2>Video kayıtları</h2><small>${(this.videos||[]).length} video</small></div>
      ${(this.videos||[]).length?`<div class="video-list">${this.videos.map(videoCard).join("")}</div>`:'<p class="muted run-empty">Henüz seçilmiş başlık yok.</p>'}</section>`;
    body.innerHTML=this.view?`<a href="#videos" class="return-link">← Konu ve başlık</a>${runView(this.view,this.open,this.message,this.busy)}${videos}`:`${form}${runs}${videos}`;
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
  async decide(main, kind, index=null) {
    const note=main.querySelector("#decision-note")?.value || "";
    const id=this.view.id;
    this.busy=true;this.draw(main);
    try {
      const result=await api(`claude/runs/${encodeURIComponent(id)}/${kind}`,{method:"POST",body:JSON.stringify(kind==="select"?{aday:index,not:note}:{not:note})});
      this.message=kind==="select"?`Video kaydı oluşturuldu: ${result.title_en}`:kind==="reject"?"Çalışma reddedildi.":"Düzeltme için yeni bir Claude çalışması başladı; ilerleme İşler panelinde.";
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
