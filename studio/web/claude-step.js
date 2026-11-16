import {esc, date} from "./api.js";
import {tokens, estimateBox} from "./estimate.js";
import {claudeProgress, progressText as claudeProgressText} from "./usage.js";

// GÖREV-21: the parts every Claude step's screen shares, so the cost and the decision are in the same place and look the same
// everywhere (the topic bank's proposal and evaluation, 1 · Başlık ve vaat, 3 · Plan, 4 · Yazım, 5 · Kontrol ve ton seçimi). After
// Rota Stüdyo's rota/web/js/claude-step.js (estimate line, progress panel with the spending so far and "İptal", decision card,
// staleness warning, versions), written for this program's string templates.
//
// - costLine: above the start button — how many calls, how many tokens are read and written, which model.
// - estimateBox (estimate.js): the same estimate in full with "Başlat"; nothing starts before it.
// - runningPanel: while the job runs — the spending so far (calls and tokens) and "İptal".
// - spentLine: after the job — the actual beside the estimate; red when the actual is over 1.5 × the estimate.
// - chainTable: steps made of many calls (3 and 4) — every link's status, calls, actual and estimated tokens; total and estimate below.
// - decisionCard: the one approval component — the note and Onayla, Düzeltme iste, Reddet.
// - staleBox: "Bu adım eskidi: <sebep>" with "Bu değişiklik etkilemiyor".
// - versionsCard: "Sürümler" — every output the step has written; nothing is deleted.

const models=estimate=>[...new Set((estimate?.satirlar || []).flatMap(row=>row.modeller?.length?row.modeller.map(m=>`${m.model_adi} · ${m.efor_adi}`):
  row.model_adi?[`${row.model_adi}${row.efor_adi?` · ${row.efor_adi}`:""}`]:[]))];

/** "Tahmin: 2 çağrı · okunacak ≈ 85 bin · yazılacak ≈ 26 bin token · model: Opus · Yüksek". */
export function costText(estimate) {
  if(!estimate) return "";
  const total=estimate.toplam, names=models(estimate);
  return `${total.cagri} çağrı · okunacak ≈ ${tokens(total.okunan)} · yazılacak ≈ ${tokens(total.yazilan)} token (toplam ≈ ${tokens(total.toplam)})${names.length?` · model: ${names.join("; ")}`:""}`;
}

/** The estimate above a start button. `state`: {estimate, error, loading, hint}. */
export function costLine(state={}) {
  if(state.error) return `<p class="cost-line cost-error" role="status"><span class="tag warm">Tahmin</span> ${esc(state.error)}</p>`;
  if(state.estimate) {
    const over=state.estimate.baslatilabilir===false;
    return `<p class="cost-line ${over?"over":""}" data-cost-line><span class="tag ${over?"error":""}">Tahmin</span> ${esc(costText(state.estimate))}${over?" · sınırı aşıyor; başlatılamaz":""}</p>`;
  }
  return `<p class="cost-line muted" data-cost-line><span class="tag">Tahmin</span> ${esc(state.loading?"hesaplanıyor…":state.hint || "Düğmeye basınca hesaplanır; Claude “Başlat” demeden çalışmaz.")}</p>`;
}

export {estimateBox};

/** "3 çağrı · 120 bin token (okunan 95 bin, yazılan 25 bin)" of an actual spending ({cagri, okunan, yazilan, toplam}). */
export function spentText(actual) {
  if(!actual) return "henüz biten çağrı yok (token, çağrı bitince sayılır)";
  if(!actual.cagri && !actual.toplam) return "0 çağrı bitti (token, çağrı bitince sayılır)";
  return `${actual.cagri} çağrı · ${tokens(actual.toplam)} token (okunan ${tokens(actual.okunan)}, yazılan ${tokens(actual.yazilan)})`;
}

/** While the step's job runs: its message, the bar, the spending so far beside the estimate, and "İptal". */
export function runningPanel(job, now=Date.now()) {
  if(!job || !["queued","running"].includes(job.status)) return "";
  const info=job.progress_info || {}, spending=info.harcama || {};
  const estimate=typeof spending.tahmin==="number"?spending.tahmin:spending.tahmin?.toplam;
  const claude=claudeProgress(job,now);
  const percent=claude?claude.percent:Math.max(0,Math.min(99,Number(info.yuzde ?? job.progress) || 0));
  const stage=claude?claudeProgressText(claude):[`%${percent}`,info.asama].filter(Boolean).join(" · ");
  const wait=info.bekleme?`<p class="text-wait" role="status"><span class="tag warm">Bekliyor</span> ${esc(info.bekleme.metin)}</p>`:"";
  return `<section class="run-panel" data-run-panel="${esc(job.id)}" aria-live="polite"><div class="run-panel-head"><strong>Claude çalışıyor</strong>
      <button type="button" class="quiet" data-step-cancel="${esc(job.id)}">İptal</button></div>
    <p class="run-panel-message">${esc(job.status==="queued"?"Sırada: önceki iş bitince başlayacak.":job.message || "Hazırlanıyor…")}</p>
    <div class="claude-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><span style="width:${percent}%"></span></div>
    <p class="claude-progress-text">${esc(stage)}</p>${wait}
    <p class="run-panel-spent" data-run-spent><span class="tag">Şu ana kadar</span> ${esc(spentText(spending.gercek))}${estimate!=null?` · tahmin ${esc(tokens(estimate))} token`:""}</p>
    <p class="muted form-note">İptal edilen iş kayda “iptal edildi” diye düşer; o ana kadarki harcaması sayılır ve biten parçalar saklanır.</p></section>`;
}

/** After the job: the actual beside the estimate; the red warning when the actual is over 1.5 × the estimate. */
export function spentLine(spending) {
  if(!spending) return "";
  const comparison=spending.karsilastirma, actual=spending.gercek;
  const estimate=typeof spending.tahmin==="number"?spending.tahmin:spending.tahmin?.toplam;
  if(!actual && estimate==null) return "";
  const parts=[];
  if(actual) parts.push(`gerçek ${spentText(actual)}`);
  if(estimate!=null) parts.push(`tahmin ${tokens(estimate)} token`);
  return `<p class="spend-line ${comparison?.fazla?"over":""}" data-spent-line><span class="tag">Harcama</span> ${esc(parts.join(" · "))}</p>${
    comparison?.fazla?`<p class="spend-over" role="alert"><span class="tag error">Beklenenden fazla</span> ${esc(comparison.uyari)}</p>`:""}`;
}

const LINK_TONE={done:"green", running:"running", partial:"warm", waiting:""};

/** The link table of 3 · Plan and 4 · Yazım (view.halkalar of a text run): rows grouped by the plan or the tone. */
export function chainTable(chain, {title="Zincirin halkaları"}={}) {
  const rows=chain?.halkalar || [];
  if(!rows.length) return "";
  let group=null;
  const body=rows.map(row=>{
    const head=row.grup!==group?`<tr class="chain-group"><td colspan="5">${esc(row.grup_adi)}</td></tr>`:"";
    group=row.grup;
    return `${head}<tr data-link="${esc(row.adim)}"><td>${esc(row.baslik)}${row.ayrinti?`<small class="source-host">${esc(row.ayrinti)}</small>`:""}</td>
      <td><span class="tag ${LINK_TONE[row.durum] || ""}">${esc(row.durum_adi)}</span></td><td>${row.cagri}${row.tahmini_cagri?` / ${row.tahmini_cagri}`:""}</td>
      <td>${row.cagri?esc(tokens(row.gercek)):"—"}</td><td>${row.tahmin?esc(tokens(row.tahmin)):"—"}</td></tr>`;
  }).join("");
  const total=chain.toplam || {};
  return `<section class="library chain-table"><div class="library-title"><h2>${esc(title)}</h2><small>her halka bir ya da birkaç Claude çağrısıdır</small></div>
    <div class="table-scroll"><table class="reference-table"><thead><tr><th>HALKA</th><th>DURUM</th><th>ÇAĞRI (YAPILAN / TAHMİN)</th><th>GERÇEK TOKEN</th><th>TAHMİNİ TOKEN</th></tr></thead>
      <tbody>${body}</tbody><tfoot><tr><td>Toplam</td><td></td><td>${total.cagri ?? 0}</td><td><strong>${esc(tokens(total.gercek))}</strong></td><td>${total.tahmin!=null?esc(tokens(total.tahmin)):"—"}</td></tr></tfoot></table></div>
    ${chain.fazla?`<p class="spend-over" role="alert"><span class="tag error">Beklenenden fazla</span> ${esc(chain.uyari)}</p>`:""}</section>`;
}

/** "Bu adım eskidi: Plan onayı değişti." with "Bu değişiklik etkilemiyor"; nothing when the step is not stale. */
export function staleBox(step, actions={}) {
  if(step?.status!=="stale") return "";
  return `<section class="stale-box" role="status"><p><strong>Bu adım eskidi:</strong> ${esc(step.stale_reason || "girdiler değişti.")} Çıktısı silinmedi. Adımı yeniden çalıştırın ya da değişiklik bu adımı etkilemiyorsa eskimeyi kaldırın; adım önceki durumuna (${esc(BEFORE[step.status_before_stale] || "hazır")}) döner ve notunuz durum günlüğüne yazılır.</p>
    <div class="decision-actions"><input id="stale-note" maxlength="4000" placeholder="İsteğe bağlı not" aria-label="Eskime notu"><button type="button" data-clear-stale ${actions.clear_stale?"":"disabled"}>Bu değişiklik etkilemiyor</button></div></section>`;
}
const BEFORE={awaiting_approval:"onay bekliyor", approved:"onaylandı", done:"tamamlandı"};

export function errorBox(step) {
  if(step?.status!=="error" || !step.error) return "";
  return `<p class="stage-note claude-warning" role="alert"><span class="note-mark">!</span><span>${esc(step.error)}</span></p>`;
}

/** The one approval component of the steps with approval (1, 3 and 5): the note and the three buttons.
 *  options: {description, extra (HTML between the note and the buttons, e.g. the tone to go on with), approveLabel, pending (an
 *  estimate waiting for "Başlat", drawn in the card), message, busy}. */
export function decisionCard(step, actions={}, options={}) {
  if(!step?.approval) return "";
  const open=actions.approve || actions.correct || actions.reject;
  if(!open) return "";
  const off=flag=>flag && !options.busy?"":"disabled";
  return `<section class="library decision-card" id="decision-card" aria-label="Karar"><div class="library-title"><h2>Karar</h2><small>${esc(options.description || "Onayla, düzeltme iste ya da reddet")}</small></div>
    <div class="decision"><label>Not<textarea id="decision-note" rows="3" maxlength="4000" placeholder="Türkçe not: neyi beğendiniz, neyin değişmesini istiyorsunuz? “Düzeltme iste” için zorunlu.">${esc(options.note || "")}</textarea></label>
      ${options.extra || ""}
      ${options.pending || ""}
      ${options.message?`<p class="stage-note" role="status">${esc(options.message)}</p>`:""}
      <div class="decision-actions"><button type="button" class="primary" data-decision="onayla" ${off(actions.approve)}>${esc(options.approveLabel || "Onayla")}</button>
        <button type="button" data-decision="duzeltme" ${off(actions.correct)}>Düzeltme iste</button>
        <button type="button" class="quiet" data-decision="reddet" ${off(actions.reject)}>Reddet</button></div>
      <p class="muted form-note">${esc(options.help || "Düzeltme iste: notunuz adım yeniden çalıştırılırken Claude'a “kullanıcının düzeltme notu” olarak verilir; talimat dosyaları değişmez. Reddet: adım hazır durumuna döner.")}</p></div></section>`;
}

/** "Sürümler": every output the step has written, newest first. `link(item)` gives the address that shows an item (or ""). */
export function versionsCard(items, link=()=>"") {
  if(!items?.length) return "";
  return `<details class="library versions-card"><summary class="library-title"><h2>Sürümler</h2><small>${items.length} kayıt · hiçbiri silinmez</small></summary>
    <ul class="version-list">${items.map(item=>{
      const href=link(item);
      return `<li><time>${esc(date(item.zaman))}</time> ${href?`<a href="${esc(href)}">${esc(item.baslik || item.id)}</a>`:`<strong>${esc(item.baslik || item.id)}</strong>`}${item.ayrinti?`<small class="source-host">${esc(item.ayrinti)}</small>`:""}</li>`;
    }).join("")}</ul></details>`;
}

/** The last lines of the status log that concern the step (decisions with their notes, status changes). */
export function logCard(lines) {
  if(!lines?.length) return "";
  return `<details class="library versions-card"><summary class="library-title"><h2>Durum günlüğü</h2><small>son ${lines.length} satır</small></summary>
    <ul class="version-list">${lines.map(line=>`<li><time>${esc(date(line.at))}</time> ${esc(line.text)}</li>`).join("")}</ul></details>`;
}

/** Wires the shared parts of a step screen. handlers: {decide(kind, note), clearStale(note), cancel(jobId)}. */
export function bindStep(root, handlers={}) {
  root.querySelectorAll("[data-decision]").forEach(button=>button.addEventListener("click",()=>
    handlers.decide?.(button.dataset.decision, root.querySelector("#decision-note")?.value || "")));
  root.querySelector("[data-clear-stale]")?.addEventListener("click",()=>handlers.clearStale?.(root.querySelector("#stale-note")?.value || ""));
  root.querySelectorAll("[data-step-cancel]").forEach(button=>button.addEventListener("click",()=>{
    if(globalThis.confirm && !globalThis.confirm("Claude durdurulsun mu? Biten parçalar saklanır; o ana kadarki harcama sayılır.")) return;
    button.disabled=true;handlers.cancel?.(button.dataset.stepCancel);
  }));
}
