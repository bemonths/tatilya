import {esc, date} from "./api.js";
import {durationText} from "./usage.js";

// The views of the video text (GÖREV-15), used by the step screens of GÖREV-21 (studio/web/steps.js): the tone choice of 4 · Yazım, the
// plan of 3 · Plan (read only), the comparison of tones of 5 · Kontrol ve ton seçimi (Turkish first, English, or both), a version
// (numbered sentences in both languages, the check's marks, terms, the report, downloads) and the job panel's bar of a text run.

export const OPENING_WORDS={rakam:"rakam", sahne:"sahne", soru:"soru", gecmis:"geçmiş", karsilastirma:"karşılaştırma", diger:"diğer"};
const LANGS={tr:"Türkçe", en:"İngilizce", both:"Alt alta"};

function money(value) {return value==null?"—":`${Number(value).toFixed(2).replace(".",",")} $`;}
function thousands(value) {return Number(value||0).toLocaleString("tr");}

/** Tone choice: checkboxes, the default ticked, each tone's first sentence, "Tonları yönet". */
export function toneChoice(tones, chosen) {
  return `<fieldset class="tone-choice"><legend>Tonlar</legend>${tones.map(t=>`<label class="tone-option"><input type="checkbox" data-tone="${esc(t.dosya)}" ${chosen.includes(t.dosya)?"checked":""}>
    <span><strong>${esc(t.ad)}</strong>${t.varsayilan?' <span class="tag green">varsayılan</span>':""}<small>${esc(t.ilk_cumle)}</small></span></label>`).join("")}
    <a class="return-link" href="#kanal/tonlar">Tonları yönet (Kanal → Tonlar) →</a></fieldset>`;
}

/** "N oturum · süre · bin token · $" of a usage (GÖREV-16: the run's total, its plan's share, a tone's share). */
export function usageText(u) {
  return `${u.oturum} oturum · ${durationText(u.sure_s)} · ${thousands(Math.round((u.token||0)/1000))} bin token · ${money(u.maliyet_usd)}`;
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
export function compareView(compare, lang="tr", versionHref=id=>`#${id}`) {
  const columns=compare.sutunlar;
  if(!columns.length) return '<p class="muted">Karşılaştırılacak sürüm yok.</p>';
  const head=columns.map(c=>`<div class="compare-head ${c.secili?"chosen":""}"><h3>${esc(c.tone_name)}${c.ton_var?"":' <span class="tag">silinmiş ton</span>'}</h3>
    <p>${thousands(c.words)} kelime · ~${String(c.dakika).replace(".",",")} dk · <span class="mark-count red">${c.red} kırmızı</span> · <span class="mark-count yellow">${c.yellow} sarı</span></p>
    <p class="muted" title="Yalnız bu tonun oturumları; planın kullanımı yukarıda">${thousands(Math.round((Object.values(c.tokens||{}).reduce((a,b)=>a+(Number(b)||0),0))/1000))} bin token · ${money(c.cost_usd)} · ${durationText(c.elapsed_s||0)} · ${c.number}. sürüm</p>
    <div class="decision-actions">${c.secili?'<span class="tag green">seçili ton</span>':""}<a class="source-link" href="${esc(versionHref(c.id))}">Metnin tamamı</a></div></div>`).join("");
  const rows=compare.satirlar.map(key=>{
    const title=columns.map(c=>c.parcalar[key]?.baslik).find(Boolean) || key;
    return `<div class="compare-row-title">${esc(title)}</div>`+columns.map(c=>{
      const part=c.parcalar[key];
      if(!part) return '<div class="compare-cell empty">—</div>';
      const body=lang==="both"?part.tr.map((p,i)=>`<p>${esc(p)}</p><p class="en">${esc(part.en[i]||"")}</p>`).join(""):part[lang].map(p=>`<p>${esc(p)}</p>`).join("");
      return `<div class="compare-cell">${part.isaretler?`<span class="mark-count red" title="Bu parçada kırmızı denetim bulgusu">${part.isaretler} kırmızı</span>`:""}${body}</div>`;
    }).join("");
  }).join("");
  const plans=(compare.planlar||[]).filter(p=>p.kullanim?.oturum).map(p=>`<span class="tag">plan${(compare.planlar||[]).length>1?` (${p.surumler.join(", ")}. sürüm)`:""}: ${esc(usageText(p.kullanim))}</span>`).join(" ");
  return `${plans?`<p class="compare-plan-usage muted">Planın kullanımı (bütün tonlar için bir kez): ${plans} · sütun başlarında yalnız o tonun kullanımı yazar.</p>`:""}<div class="compare-tools"><div class="lang-switch" role="group" aria-label="Dil">${Object.entries(LANGS).map(([key,label])=>`<button type="button" class="${key===lang?"primary":""}" data-lang="${key}" aria-pressed="${key===lang}">${label}</button>`).join("")}</div>
</div>
    <div class="compare-scroll"><div class="compare-grid" style="grid-template-columns:150px repeat(${columns.length}, minmax(320px, 1fr))"><div class="compare-corner"></div>${head}${rows}</div></div>`;
}

export function findingMarks(sentence) {
  const marks=(sentence.uyarilar||[]).filter(w=>w.tur==="denetim");
  return marks.map(w=>`<span class="sentence-mark ${w.seviye==="kirmizi"?"red":"yellow"}" title="${esc(w.metin)}">●</span>`).join("");
}

/** A version: numbered sentences side by side, marks of the check, translator warnings, evidence ids on hover. */
export function versionView(version, backHref="") {
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
      ${backHref?`<a class="source-link" href="${esc(backHref)}">← 4 · Yazım</a>`:""}</div>
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
