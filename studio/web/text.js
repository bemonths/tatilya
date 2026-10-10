import {api, esc, date} from "./api.js";
import {durationText} from "./usage.js";

// GÖREV-15 (Adım 8): the Video metni step. Tone choice and "Metni yaz"; text runs (status, usage, versions, "Devam", "Durdur", "Bu tonla
// da yaz", "Planı yeniden yap"); the plan (read only); the comparison of tones side by side (Turkish first, English, or both); a version
// (numbered sentences in both languages, the check's marks, terms, the report, downloads). The job panel's bar of a text run.

export const OPENING_WORDS={rakam:"rakam", sahne:"sahne", soru:"soru", gecmis:"geçmiş", karsilastirma:"karşılaştırma", diger:"diğer"};
const LANGS={tr:"Türkçe", en:"İngilizce", both:"Alt alta"};

function money(value) {return value==null?"—":`${Number(value).toFixed(2).replace(".",",")} $`;}
function thousands(value) {return Number(value||0).toLocaleString("tr");}

export function routeOf(hash) {
  const parts=String(hash||"").replace(/^#/,"").split("/");
  if(parts[0]!=="adim" || parts[1]!=="metin") return null;
  return {view:parts[2]||"main", id:parts[3]?decodeURIComponent(parts[3]):null};
}

/** Tone choice: checkboxes, the default ticked, each tone's first sentence, "Tonları yönet". */
export function toneChoice(tones, chosen) {
  return `<fieldset class="tone-choice"><legend>Tonlar</legend>${tones.map(t=>`<label class="tone-option"><input type="checkbox" data-tone="${esc(t.dosya)}" ${chosen.includes(t.dosya)?"checked":""}>
    <span><strong>${esc(t.ad)}</strong>${t.varsayilan?' <span class="tag green">varsayılan</span>':""}<small>${esc(t.ilk_cumle)}</small></span></label>`).join("")}
    <a class="return-link" href="#settings/tonlar">Tonları yönet →</a></fieldset>`;
}

export function writeBox(options, chosen, busy, message="") {
  const blocked=options.mesgul?"Bir video metni çalışması sürüyor; bitmesini bekleyin.":options.claude_mesgul?"Bir Claude çalışması sürüyor; bitmesini bekleyin.":"";
  return `<section class="library text-write"><div class="library-title"><h2>Metni yaz</h2><small>${esc(options.video.title_en)}</small></div>
    <div class="text-write-body">${toneChoice(options.tonlar, chosen)}
    <div class="decision-actions"><button class="primary" id="text-start" ${busy || blocked || !chosen.length?"disabled":""}>Metni yaz</button>
      <span class="muted">Seçilen her ton için ayrı metin yazılır; plan bir kez yapılır ve bütün tonlar aynı planı kullanır.</span></div>
    ${options.paket?.metin?`<p class="muted form-note pack-note">${esc(options.paket.metin)}</p>`:""}
    ${blocked?`<p class="stage-note" role="status">${esc(blocked)}</p>`:""}
    ${message?`<p class="stage-note" role="status">${esc(message)}</p>`:""}</div></section>`;
}

export function runRows(runs, tones=[]) {
  if(!runs.length) return '<p class="muted run-empty">Henüz metin çalışması yok.</p>';
  return `<div class="table-scroll"><table class="reference-table text-runs"><thead><tr><th>TARİH</th><th>TONLAR</th><th>DURUM</th><th>KULLANIM</th><th>SÜRÜMLER</th><th></th></tr></thead><tbody>
    ${runs.map(run=>{
      const written=new Set(run.surumler.map(v=>v.tone_file));
      const more=tones.filter(t=>!run.tones.some(r=>r.dosya===t.dosya));
      const u=run.kullanim;
      return `<tr data-run="${esc(run.id)}"><td>${esc(date(run.created_at))}${run.replan_of?'<small class="source-host">planı yeniden yapıldı</small>':""}</td>
      <td>${run.tones.map(t=>`<span class="tag ${written.has(t.dosya)?"green":""}">${esc(t.ad)}</span>`).join(" ")}</td>
      <td><span class="tag ${run.status==="error"?"error":["paused","interrupted"].includes(run.status)?"warm":run.status==="awaiting_comparison"?"green":"running"}">${esc(run.status_label)}</span>
        ${run.reason_text?`<small class="source-host">${esc(run.reason_text)}</small>`:""}</td>
      <td>${u.oturum} oturum · ${durationText(u.sure_s)} · ${thousands(Math.round(u.token/1000))} bin token · ${money(u.maliyet_usd)}</td>
      <td>${run.surumler.map(v=>`<a href="#adim/metin/surum/${encodeURIComponent(v.id)}">${v.number}. ${esc(v.tone_name)}</a>`).join("<br>") || "—"}</td>
      <td class="run-actions">${run.eylemler.devam?`<button data-text-resume="${esc(run.id)}">Devam</button>`:""}${run.eylemler.durdur?`<button class="quiet" data-text-stop="${esc(run.id)}">Durdur</button>`:""}
        ${run.eylemler.plani_goster?`<a class="source-link" href="#adim/metin/plan/${encodeURIComponent(run.id)}">Planı göster</a>`:""}
        ${run.surumler.length?`<a class="source-link" href="#adim/metin/karsilastirma/${encodeURIComponent(run.id)}">Karşılaştır</a>`:""}
        ${run.eylemler.ton_ekle && more.length?`<span class="add-tone"><select data-add-tone-select="${esc(run.id)}" aria-label="Eklenecek ton">${more.map(t=>`<option value="${esc(t.dosya)}">${esc(t.ad)}</option>`).join("")}</select><button data-add-tone="${esc(run.id)}">Bu tonla da yaz</button></span>`:""}
        ${run.eylemler.plani_yeniden_yap?`<button class="quiet" data-replan="${esc(run.id)}">Planı yeniden yap</button>`:""}</td></tr>`;}).join("")}
    </tbody></table></div>`;
}

export function planView(view) {
  const plan=view.plan;
  if(!plan) return '<p class="muted">Bu çalışmanın planı henüz kesinleşmedi.</p>';
  const sections=plan.bolumler.map(s=>`<tr><td>${s.no}</td><td><strong>${esc(s.ic_adi)}</strong><small class="source-host">${esc(s.tek_fikir)}</small></td>
    <td>${esc(s.en_carpici_an)}</td><td>${s.kelime_butcesi}</td><td><span class="tag">${esc(OPENING_WORDS[s.acilis_bicimi] || s.acilis_bicimi)}</span><small class="source-host">${esc(s.acilis_notu)}</small></td>
    <td>${s.kanitlar.map(k=>`<code>${esc(k)}</code>`).join(" ")}</td></tr>`).join("");
  const total=plan.bolumler.reduce((sum,s)=>sum+(s.kelime_butcesi||0),0);
  const promise=plan.vaat_kontrolu||{karsilanan:[],karsilanamayan:[]};
  return `<section class="library text-plan"><div class="library-title"><h2>Plan</h2><small>${plan.bolumler.length} bölüm · ${thousands(total)} kelime bütçesi · ${view.plan_turu||1}. tur · salt okunur</small></div>
    <div class="table-scroll"><table class="reference-table"><thead><tr><th>NO</th><th>BÖLÜM · TEK FİKİR</th><th>EN ÇARPICI AN</th><th>BÜTÇE</th><th>AÇILIŞ</th><th>KANITLAR</th></tr></thead><tbody>${sections}</tbody></table></div>
    <div class="plan-notes"><h3>Kavramların yeri</h3>${(plan.kavramlar||[]).length?`<ul>${plan.kavramlar.map(c=>`<li>${esc(c.kavram)} → ${c.bolum}. bölüm</li>`).join("")}</ul>`:"<p class=\"muted\">Yok.</p>"}
    <h3>Yeniden kancalar</h3>${(plan.yeniden_kancalar||[]).length?`<ul>${plan.yeniden_kancalar.map(h=>`<li>${h.bolumden_sonra}. bölümden sonra: ${esc(h.uzerine)}</li>`).join("")}</ul>`:"<p class=\"muted\">Yok.</p>"}
    <h3>Vaat kontrolü</h3><ul>${promise.karsilanan.map(p=>`<li>${esc(p.vaat)} → ${p.bolumler.join(", ")}. bölüm</li>`).join("")}${promise.karsilanamayan.map(p=>`<li class="problem-warning">Karşılanamayan: ${esc(p)}</li>`).join("")}</ul>
    <h3>Program uyarıları</h3>${view.plan_uyarilari?.length?`<ul class="problem-list">${view.plan_uyarilari.map(w=>`<li class="problem-warning">${esc(w)}</li>`).join("")}</ul>`:"<p class=\"muted\">Yok.</p>"}
    <h3>Eleştirmenin notları</h3>${view.elestiri?`<ul>${view.elestiri.notlar.map(n=>`<li>${esc(n)}</li>`).join("")}</ul><p class="muted">${view.elestiri.yeniden_yap?"Eleştirmen planın yeniden yapılmasını istedi; plan notlarla bir kez daha yazıldı.":"Eleştirmen planı yeniden yaptırmadı."}</p>`:"<p class=\"muted\">Yok.</p>"}
    ${(plan.notlar||[]).length?`<h3>Planlayıcının notları</h3><ul>${plan.notlar.map(n=>`<li>${esc(n)}</li>`).join("")}</ul>`:""}</div></section>`;
}

/** The comparison: tones side by side, rows are the parts (introduction, sections, transitions, closing). */
export function compareView(compare, lang="tr", tones=[], runId=null) {
  const columns=compare.sutunlar;
  if(!columns.length) return '<p class="muted">Karşılaştırılacak sürüm yok.</p>';
  const head=columns.map(c=>`<div class="compare-head ${c.secili?"chosen":""}"><h3>${esc(c.tone_name)}${c.ton_var?"":' <span class="tag">silinmiş ton</span>'}</h3>
    <p>${thousands(c.words)} kelime · ~${String(c.dakika).replace(".",",")} dk · <span class="mark-count red">${c.red} kırmızı</span> · <span class="mark-count yellow">${c.yellow} sarı</span></p>
    <p class="muted">${thousands(Math.round((Object.values(c.tokens||{}).reduce((a,b)=>a+(Number(b)||0),0))/1000))} bin token · ${money(c.cost_usd)} · ${durationText(c.elapsed_s||0)} · ${c.number}. sürüm</p>
    <div class="decision-actions">${c.secili?'<span class="tag green">seçili</span>':`<button class="primary" data-choose="${esc(c.id)}">Bu tonla devam et</button>`}<a class="source-link" href="#adim/metin/surum/${encodeURIComponent(c.id)}">Tek göster</a></div></div>`).join("");
  const rows=compare.satirlar.map(key=>{
    const title=columns.map(c=>c.parcalar[key]?.baslik).find(Boolean) || key;
    return `<div class="compare-row-title">${esc(title)}</div>`+columns.map(c=>{
      const part=c.parcalar[key];
      if(!part) return '<div class="compare-cell empty">—</div>';
      const body=lang==="both"?part.tr.map((p,i)=>`<p>${esc(p)}</p><p class="en">${esc(part.en[i]||"")}</p>`).join(""):part[lang].map(p=>`<p>${esc(p)}</p>`).join("");
      return `<div class="compare-cell">${part.isaretler?`<span class="mark-count red" title="Bu parçada kırmızı denetim bulgusu">${part.isaretler} kırmızı</span>`:""}${body}</div>`;
    }).join("");
  }).join("");
  const more=tones.filter(t=>!columns.some(c=>c.tone_file===t.dosya));
  return `<div class="compare-tools"><div class="lang-switch" role="group" aria-label="Dil">${Object.entries(LANGS).map(([key,label])=>`<button type="button" class="${key===lang?"primary":""}" data-lang="${key}" aria-pressed="${key===lang}">${label}</button>`).join("")}</div>
    ${runId && more.length?`<span class="add-tone"><select id="compare-add-tone" aria-label="Eklenecek ton">${more.map(t=>`<option value="${esc(t.dosya)}">${esc(t.ad)}</option>`).join("")}</select><button id="compare-add" data-run="${esc(runId)}">Bu tonla da yaz</button></span>`:""}</div>
    <div class="compare-scroll"><div class="compare-grid" style="grid-template-columns:150px repeat(${columns.length}, minmax(320px, 1fr))"><div class="compare-corner"></div>${head}${rows}</div></div>`;
}

export function findingMarks(sentence) {
  const marks=(sentence.uyarilar||[]).filter(w=>w.tur==="denetim");
  return marks.map(w=>`<span class="sentence-mark ${w.seviye==="kirmizi"?"red":"yellow"}" title="${esc(w.metin)}">●</span>`).join("");
}

/** A version: numbered sentences side by side, marks of the check, translator warnings, evidence ids on hover. */
export function versionView(version) {
  const doc=version.metin;
  const rows=doc.parcalar.map(part=>`<tr class="part-row"><td colspan="4">${esc(part.baslik || part.kimlik)}</td></tr>`+part.paragraflar.map(p=>p.cumleler.map(s=>{
    const notes=(s.uyarilar||[]).filter(w=>w.tur!=="denetim");
    const findings=(s.uyarilar||[]).filter(w=>w.tur==="denetim");
    return `<tr class="sentence-row ${findings.some(w=>w.seviye==="kirmizi")?"has-red":findings.length?"has-yellow":""}"><td class="sentence-no">${s.no}</td>
      <td class="sentence-en" title="${esc(s.kanitlar.length?`Kanıt: ${s.kanitlar.join(", ")}`:"Kanıt işareti yok")}">${esc(s.en)}</td><td class="sentence-tr">${esc(s.tr)}
      ${notes.map(w=>`<small class="sentence-note">${esc({cevirmen:"Çevirmen",rakam:"Rakam",son_okuma:"Son okuma"}[w.tur] || w.tur)}: ${esc(w.metin)}</small>`).join("")}</td>
      <td class="sentence-marks">${findingMarks(s)}${findings.map(w=>`<small class="sentence-finding ${w.seviye==="kirmizi"?"red":"yellow"}">${esc(w.metin)}</small>`).join("")}</td></tr>`;}).join("")).join("")).join("");
  const info=doc.surum_bilgisi||{};
  const terms=(doc.terimler||[]).map(t=>`<li><strong>${esc(t.en)}</strong> (${esc(t.tr || t.en)}): ${esc(t.aciklama)}</li>`).join("");
  return `<section class="library text-version"><div class="library-title"><h2>${version.number}. sürüm · ${esc(version.tone_name)}${version.secili?' <span class="tag green">seçili</span>':""}</h2>
      <small>${thousands(version.words)} kelime · ${version.sentences} cümle · <span class="mark-count red">${version.red} kırmızı</span> · <span class="mark-count yellow">${version.yellow} sarı</span> · ${esc(date(version.created_at))}</small></div>
    <div class="decision-actions version-downloads">${["en","tr","seslendirme"].map(kind=>`<a class="source-link" href="/api/metin/surumler/${encodeURIComponent(version.id)}/dosya/${kind}" download>${{en:"İngilizce",tr:"Türkçe",seslendirme:"Seslendirme"}[kind]} ↓</a>`).join("")}
      ${version.secili?"":`<button class="primary" data-choose="${esc(version.id)}">Bu tonla devam et</button>`}<a class="source-link" href="#adim/metin/karsilastirma/${encodeURIComponent(version.text_run_id)}">← Karşılaştırma</a></div>
    <p class="stage-note">${esc(version.not)}</p>
    <div class="table-scroll"><table class="reference-table sentence-table"><thead><tr><th>NO</th><th>İNGİLİZCE</th><th>TÜRKÇE</th><th>DENETİM</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="plan-notes"><h3>Terimler</h3>${terms?`<ul>${terms}</ul>`:'<p class="muted">Yok.</p>'}
    <h3>Ton ve oturumlar</h3><p class="muted">${esc(info.ton?.ad || version.tone_name)} · <code>${esc(info.ton?.dosya || version.tone_file)}.md</code> · karma <code>${esc((info.ton?.sha256||"").slice(0,8))}</code> · ${(info.oturumlar||[]).length} oturum</p>
    <details><summary>Denetim raporunun tamamı</summary><pre class="path audit-report">${esc(version.denetim_md)}</pre></details></div></section>`;
}

/** The job panel's bar of a text run: percent, the stage, elapsed and remaining time; while waiting for the usage limit, when it goes on. */
export function textBar(job, now=Date.now()) {
  const info=job?.progress_info;
  if(!info || info.tur!=="metin") return "";
  const activeJob=["queued","running"].includes(job.status);
  const percent=activeJob?Math.max(0,Math.min(99,Number(info.yuzde)||0)):job.status==="done"?100:Math.max(0,Math.min(100,job.progress||0));
  const started=Date.parse(info.baslangic||job.created_at);
  const elapsed=Number.isFinite(started)?Math.max(0,(now-started)/1000):null;
  const parts=[`%${percent}`, info.asama];
  if(activeJob && elapsed!=null) parts.push(`geçen ${durationText(elapsed)}`);
  if(activeJob && info.kalan_s) parts.push(`tahmini kalan ~${durationText(info.kalan_s)}`);
  const wait=activeJob && info.bekleme?`<p class="text-wait" role="status"><span class="tag warm">Bekliyor</span> ${esc(info.bekleme.metin)}</p>`:"";
  return `<div class="claude-progress text-progress" data-progress-job="${esc(job.id)}"><div class="claude-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><span style="width:${percent}%"></span></div>
    <p class="claude-progress-text">${esc(parts.filter(Boolean).join(" · "))}</p>${wait}</div>`;
}

export class TextScreen {
  constructor() {this.options=null;this.chosen=null;this.videoId=null;this.message="";this.busy=false;this.sequence=0;this.lang="tr";this.lastJobs="";}
  async render(main, ctx) {
    this.main=main;this.ctx=ctx;
    const route=routeOf(location.hash) || {view:"main"};
    const ticket=++this.sequence;
    const {step, heading, nextTaskSlot}=ctx;
    const titles={main:"Video metni", plan:"Video metni · plan", karsilastirma:"Video metni · tonların karşılaştırması", surum:"Video metni · sürüm"};
    main.innerHTML=heading(titles[route.view]||"Video metni", "Seçilen başlık ve video paketiyle program Claude'u adım adım çağırarak İngilizce metni yazdırır; her tonun metni ayrı yazılır ve Türkçesi cümle cümle verilir.")
      + nextTaskSlot(step) + '<div id="text-body" aria-live="polite"><p class="loading">Yükleniyor…</p></div>';
    const body=main.querySelector("#text-body");
    if(!ctx.videoId) {body.innerHTML='<section class="quality-result empty"><h2>Video seçilmedi</h2><p>Üst çubuktaki video seçiciden bir video seçin.</p><a class="return-link" href="#videos">Konu ve başlık →</a></section>';return;}
    try {
      if(this.videoId!==ctx.videoId) {this.chosen=null;this.videoId=ctx.videoId;}
      this.options=await api(`videos/${encodeURIComponent(ctx.videoId)}/metin`);
      if(ticket!==this.sequence) return;
      if(this.chosen===null) this.chosen=this.options.tonlar.filter(t=>t.varsayilan).map(t=>t.dosya);
      if(route.view==="plan" && route.id) {
        const view=await api(`metin/calismalar/${encodeURIComponent(route.id)}`);
        if(ticket!==this.sequence) return;
        body.innerHTML=`<a class="return-link" href="#adim/metin">← Video metni</a>${planView(view)}`;
      } else if(route.view==="karsilastirma") {
        const compare=await api(`videos/${encodeURIComponent(ctx.videoId)}/metin/karsilastirma${route.id?`?calisma=${encodeURIComponent(route.id)}`:""}`);
        if(ticket!==this.sequence) return;
        body.innerHTML=`<a class="return-link" href="#adim/metin">← Video metni</a><p class="stage-note">${esc(compare.not)}</p>${compareView(compare,this.lang,this.options.tonlar,route.id)}`;
      } else if(route.view==="surum" && route.id) {
        const version=await api(`metin/surumler/${encodeURIComponent(route.id)}`);
        if(ticket!==this.sequence) return;
        body.innerHTML=`<a class="return-link" href="#adim/metin">← Video metni</a>${versionView(version)}`;
      } else {
        body.innerHTML=writeBox(this.options,this.chosen,this.busy,this.message)+`<section class="library"><div class="library-title"><h2>Metin çalışmaları</h2><small>${this.options.calismalar.length} çalışma · ${this.options.surumler.length} sürüm</small></div>${runRows(this.options.calismalar,this.options.tonlar)}</section>
          ${this.options.surumler.length?`<p class="return-link"><a href="#adim/metin/karsilastirma">Bütün sürümleri karşılaştır →</a></p>`:""}<p class="stage-note">${esc(this.options.not)}</p>`;
      }
      this.bind(body);
    } catch(error) {if(!error.stale && ticket===this.sequence) body.textContent=error.message;}
  }
  rerender() {if(this.main) return this.render(this.main,this.ctx);}
  bind(body) {
    body.querySelectorAll("[data-tone]").forEach(box=>box.addEventListener("change",()=>{this.chosen=[...body.querySelectorAll("[data-tone]:checked")].map(b=>b.dataset.tone);body.querySelector("#text-start").disabled=!this.chosen.length || this.busy;}));
    body.querySelector("#text-start")?.addEventListener("click",()=>this.act(()=>api(`videos/${encodeURIComponent(this.videoId)}/metin`,{method:"POST",body:JSON.stringify({tonlar:this.chosen})}),"Metin çalışması başladı; ilerlemesi İşler panelinde."));
    body.querySelectorAll("[data-text-resume]").forEach(b=>b.addEventListener("click",()=>this.act(()=>api(`metin/calismalar/${encodeURIComponent(b.dataset.textResume)}/devam`,{method:"POST",body:"{}"}),"Çalışma sürüyor.")));
    body.querySelectorAll("[data-text-stop]").forEach(b=>b.addEventListener("click",()=>this.act(()=>api(`metin/calismalar/${encodeURIComponent(b.dataset.textStop)}/durdur`,{method:"POST",body:"{}"}),"Durduruluyor; biten adımlar saklanır.")));
    body.querySelectorAll("[data-add-tone]").forEach(b=>b.addEventListener("click",()=>{const tone=body.querySelector(`[data-add-tone-select="${CSS.escape(b.dataset.addTone)}"]`).value;
      this.act(()=>api(`metin/calismalar/${encodeURIComponent(b.dataset.addTone)}/ton`,{method:"POST",body:JSON.stringify({ton:tone})}),"Aynı planla bir ton daha yazılıyor.");}));
    body.querySelectorAll("[data-replan]").forEach(b=>b.addEventListener("click",()=>{if(!globalThis.confirm?.("Yeni bir metin çalışması açılır ve plan yeniden yapılır; eski çalışma ve sürümleri saklanır. Devam edilsin mi?")) return;
      this.act(()=>api(`metin/calismalar/${encodeURIComponent(b.dataset.replan)}/yeniden-planla`,{method:"POST",body:"{}"}),"Plan yeniden yapılıyor (yeni çalışma).");}));
    body.querySelectorAll("[data-choose]").forEach(b=>b.addEventListener("click",()=>this.act(()=>api(`metin/surumler/${encodeURIComponent(b.dataset.choose)}/sec`,{method:"POST",body:"{}"}),"Bu tonla devam ediliyor: seçilen metin videonun metni oldu.",true)));
    body.querySelectorAll("[data-lang]").forEach(b=>b.addEventListener("click",()=>{this.lang=b.dataset.lang;this.rerender();}));
    body.querySelector("#compare-add")?.addEventListener("click",event=>{const tone=body.querySelector("#compare-add-tone").value;
      this.act(()=>api(`metin/calismalar/${encodeURIComponent(event.currentTarget.dataset.run)}/ton`,{method:"POST",body:JSON.stringify({ton:tone})}),"Aynı planla bir ton daha yazılıyor; bitince karşılaştırmaya eklenir.");});
  }
  async act(call, message, reloadWorkflow=false) {
    this.busy=true;
    try {await call();this.message=message;} catch(error) {if(error.stale) return;this.message=error.message;}
    finally {this.busy=false;}
    if(reloadWorkflow || true) await this.ctx.reload?.();
    this.rerender();
  }
  /** The job panel changed: the screen follows the text runs (a run ended, a version was saved). */
  jobsChanged(jobs) {
    const key=jobs.filter(j=>j.kind==="claude_metin").map(j=>`${j.id}:${j.status}:${(j.log||[]).length}`).join("|");
    if(key===this.lastJobs) return false;
    this.lastJobs=key;
    return true;
  }
}
