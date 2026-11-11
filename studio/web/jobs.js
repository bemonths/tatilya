import {esc, date} from "./api.js";
import {claudeBar} from "./usage.js";
import {textBar} from "./text.js";
import {skipButton} from "./extension.js";
import {linkSettingsMentions} from "./settings.js";

// GÖREV-17 (Adım 2 and 4): the job panel. Finished jobs can be taken off the panel one by one ("Kaldır") or all at once ("Bitenleri
// kaldır"); removing only hides (the record, the log and the result stay in the database) and "Gizlenen işleri göster (N)" at the
// bottom lists them with "Geri getir". A running job names the browser window that is open for it ("Eklentinin penceresi: …").

export const STATUS_LABELS={queued:"Sırada", running:"Çalışıyor", done:"Tamamlandı", failed:"Hata", canceled:"İptal edildi", interrupted:"Yarıda kaldı"};
export const active=job=>["queued","running"].includes(job.status);
export const WINDOW_LABELS={eklenti:"Eklentinin penceresi", program:"Programın tarayıcısı", proxy:"Programın proxy tarayıcısı"};

/** The jobs shown on the panel: everything that is not hidden. */
export function visibleJobs(jobs) {
  return (jobs||[]).filter(job=>!job.hidden_at);
}

/** What "Bitenleri kaldır" takes off: finished jobs on the panel; a job whose Claude run still waits for the user's approval stays. */
export function removableJobs(jobs) {
  return visibleJobs(jobs).filter(job=>!active(job) && !job.awaiting_approval);
}

/** The browser windows open for a running job, one line each: "Eklentinin penceresi: realjoy.com · sayfa okunuyor". */
export function windowLines(job) {
  if(!active(job)) return [];
  const info=job.progress_info || {}, lines=[];
  if(info.tur==="eklenti" && info.asama && !info.devredildi) lines.push(`${WINDOW_LABELS.eklenti}: ${info.asama}`);
  for(const key of ["program","proxy"]) if(info.pencereler?.[key]) lines.push(`${WINDOW_LABELS[key]}: ${info.pencereler[key]}`);
  return lines;
}

export function panelHead(jobs) {
  const count=removableJobs(jobs).length;
  return `<div class="jobs-tools"><button type="button" class="quiet" data-hide-finished ${count?"":"disabled"} title="Tamamlanan, hata veren ve iptal edilen işleri panelden kaldırır. Kayıtları ve günlükleri silinmez.">Bitenleri kaldır${count?` (${count})`:""}</button></div>`;
}

export function jobCard(job, {resultLink=""}={}) {
  const running=active(job);
  const bar=claudeBar(job) || textBar(job) || `<progress max="100" value="${job.progress}" aria-label="İş ilerlemesi"></progress>`;
  const waiting=job.waiting_for?`<p class="job-waiting"><span class="tag warm">Kullanıcı doğrulaması bekleniyor</span> ${esc(job.waiting_for)}</p>`:"";
  const message=job.message && job.message===job.progress_info?.bekleme?.metin?"":`<p>${linkSettingsMentions(esc(job.message))}</p>`;
  const windows=windowLines(job).map(line=>`<p class="job-window"><span class="tag">Açık pencere</span> ${esc(line)}</p>`).join("");
  const handover=running && job.progress_info?.tur==="eklenti" && job.progress_info.bekliyor?`<button data-handover-job="${esc(job.id)}">Programın tarayıcısına devret</button> `:"";
  const buttons=running?`${handover}${skipButton(job)}<button class="quiet" data-cancel-job="${esc(job.id)}">İptal et</button>`
    :`<button class="quiet job-remove" data-hide-job="${esc(job.id)}" title="İşi panelden kaldırır; kaydı ve günlüğü silinmez.">Kaldır</button>`;
  return `<article class="job" data-job="${esc(job.id)}"><div class="job-meta"><span class="tag ${job.status==="done"?"green":"warm"}">${esc(STATUS_LABELS[job.status] || job.status)}</span>${job.awaiting_approval?'<span class="tag warm">Onay bekliyor</span>':""}<time>${esc(date(job.created_at))}</time></div>
    <h3>${esc(job.title)}</h3>${job.source_name?`<p>Kaynak: ${esc(job.source_name)}</p>`:""}${bar}${waiting}${windows}${message}${buttons}
    <details><summary>İş günlüğü (${job.log.length})</summary>${job.log.map(entry=>`<div class="log-line"><time>${esc(date(entry.at))}</time>${esc(entry.text)}</div>`).join("")}</details>${resultLink}</article>`;
}

/** The bottom of the panel: "Gizlenen işleri göster (N)" and, opened, the hidden jobs with "Geri getir". */
export function hiddenSection(hidden, open) {
  const list=hidden||[];
  if(!list.length) return "";
  const rows=open?`<ul class="hidden-jobs">${list.map(job=>`<li><div><strong>${esc(job.title)}</strong><small class="muted">${esc(STATUS_LABELS[job.status] || job.status)} · ${esc(date(job.created_at))} · günlük ${job.log_count ?? 0} satır</small></div>
    <button type="button" data-unhide-job="${esc(job.id)}">Geri getir</button></li>`).join("")}</ul>
    <p class="muted hidden-note">Gizlenen işlerin kayıtları, günlükleri ve sonuçları silinmedi; “Geri getir” işi panele döndürür.</p>`:"";
  return `<div class="jobs-hidden"><button type="button" class="link-button" data-toggle-hidden aria-expanded="${open?"true":"false"}">${open?"Gizlenen işleri sakla":"Gizlenen işleri göster"} (${list.length})</button>${rows}</div>`;
}

export function emptyPanel(hiddenCount) {
  return hiddenCount
    ? '<div class="empty"><div class="empty-icon">⌁</div><h3>Panelde iş yok</h3><p>Biten işler panelden kaldırıldı. Aşağıdaki “Gizlenen işleri göster” ile görebilir ve geri getirebilirsin.</p></div>'
    : '<div class="empty"><div class="empty-icon">⌁</div><h3>Henüz iş yok</h3><p>Kaynak ekranında “Kayıtları kontrol et” düğmesine bastığında işin durumu ve sonucu burada görünür.</p></div>';
}

/** The whole panel. `resultLink(job)` gives the "… verilerini aç" link of a finished collection. */
export function jobsPanel(jobs, hidden, {open=false, resultLink=()=>""}={}) {
  const shown=visibleJobs(jobs);
  const cards=shown.length?shown.map(job=>jobCard(job,{resultLink:resultLink(job)})).join(""):emptyPanel((hidden||[]).length);
  return panelHead(jobs)+cards+hiddenSection(hidden,open);
}
