import {api, esc} from "./api.js";

// GÖREV-14 (Adım 4a): the Claude usage panel at the bottom of the sidebar, and (4b) the bar of a Claude run in the job panel.

const time=iso=>new Date(iso).toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit"});
const dayTime=iso=>`${new Date(iso).toLocaleDateString("tr-TR",{weekday:"short"})} ${time(iso)}`;

/** "6 dk 12 sn", "45 sn", "1 sa 5 dk" */
export function durationText(seconds) {
  if(seconds==null || !Number.isFinite(seconds)) return "—";
  const s=Math.max(0,Math.round(seconds));
  if(s<60) return `${s} sn`;
  const minutes=Math.floor(s/60), rest=s%60;
  if(minutes<60) return rest?`${minutes} dk ${rest} sn`:`${minutes} dk`;
  const hours=Math.floor(minutes/60), m=minutes%60;
  return m?`${hours} sa ${m} dk`:`${hours} sa`;
}

function windowRow(window, kind) {
  if(!window) return "";
  const reset=window.resets_at?(kind==="seven_day"?dayTime(window.resets_at):time(window.resets_at)):null;
  const value=window.reset_passed?"sıfırlandı":window.percent==null?"—":`%${window.percent}`;
  const width=window.percent==null?0:Math.min(100,window.percent);
  return `<div class="usage-row"><span>${esc(window.label)}</span><strong>${esc(value)}</strong></div>
    <div class="usage-bar ${width>=80?"high":""}" aria-hidden="true"><span style="width:${width}%"></span></div>
    <small>${reset?`sıfırlanma ${esc(reset)}`:"sıfırlanma bilinmiyor"}</small>`;
}

export function usageHtml(view, busy=false, message="") {
  const head=`<div class="usage-head"><span class="eyebrow">CLAUDE KULLANIMI</span><button class="quiet usage-refresh" id="usage-refresh" ${busy?"disabled":""}>${busy?"Yenileniyor…":"Yenile"}</button></div>`;
  const week=view?.week?`<p class="usage-meta">Bu hafta ${view.week.count} çalışma · ${esc(durationText(view.week.total_s))}</p>`:"";
  const note=message?`<p class="usage-meta usage-message" role="status">${esc(message)}</p>`:"";
  if(!view || !view.measured) return `${head}<p class="usage-empty">henüz ölçüm yok</p>${week}${note}`;
  return `${head}<div class="usage-body ${view.stale?"stale":""}">${windowRow(view.windows.five_hour,"five_hour")}${windowRow(view.windows.seven_day,"seven_day")}
    <p class="usage-meta">son ölçüm ${esc(time(view.measured_at))}${view.stale?' · <span class="tag warm">eski ölçüm</span>':""}</p></div>${week}${note}`;
}

export class UsagePanel {
  constructor(container) {this.container=container;this.view=null;this.busy=false;this.message="";this.sequence=0;}
  draw() {
    if(!this.container) return;
    this.container.innerHTML=usageHtml(this.view,this.busy,this.message);
    this.container.querySelector("#usage-refresh")?.addEventListener("click",()=>this.refresh());
  }
  async load() {
    const ticket=++this.sequence;
    try { const view=await api("claude/usage"); if(ticket===this.sequence && !this.busy) {this.view=view;this.draw();} }
    catch(error) { /* the next event tries again */ }
  }
  async refresh() {
    this.busy=true;this.message="";this.draw();
    try { this.view=await api("claude/usage/refresh",{method:"POST",body:"{}"});this.message="Kullanım yenilendi."; }
    catch(error) { if(!error.stale) this.message=error.message; }
    finally { this.busy=false;this.sequence++;this.draw(); }
  }
}

/** A Claude run's bar (Adım 4b): inputs 0–10 %, Claude 10–90 % by elapsed time over the expected duration, validation 90–100 %. */
export function claudeProgress(job, now=Date.now()) {
  const info=job?.progress_info;
  if(!info || info.tur!=="claude") return null;
  const activeJob=["queued","running"].includes(job.status);
  const started=Date.parse(info.baslangic || job.created_at);
  const elapsed=Number.isFinite(started)?Math.max(0,(now-started)/1000):null;
  if(!activeJob) return {percent:job.status==="done"?100:Math.max(0,Math.min(100,job.progress||0)),stage:"bitti",elapsed:null,remaining:null,over:false,basis:info.dayanak||null};
  if(info.asama==="claude") {
    const claudeStart=Date.parse(info.claude_baslangic);
    const ran=Number.isFinite(claudeStart)?Math.max(0,(now-claudeStart)/1000):0;
    const expected=Math.max(1,Number(info.beklenen_s)||1);
    const percent=10+Math.min(80,Math.floor(80*ran/expected));
    return {percent,stage:"Claude çalışıyor",elapsed,remaining:Math.max(0,expected-ran),over:ran>expected,basis:info.dayanak||null};
  }
  if(info.asama==="dogrulama") return {percent:Math.max(90,Math.min(99,job.progress||90)),stage:"Doğrulama ve Markdown",elapsed,remaining:null,over:false,basis:info.dayanak||null};
  return {percent:Math.min(10,Math.max(0,job.progress||0)),stage:"Girdiler hazırlanıyor",elapsed,remaining:null,over:false,basis:null};
}

export function progressText(progress) {
  if(!progress) return "";
  if(progress.stage==="bitti") return `%${progress.percent}`;
  const parts=[`%${progress.percent}`,progress.stage];
  if(progress.elapsed!=null) parts.push(`geçen ${durationText(progress.elapsed)}`);
  if(progress.over) parts.push("tahminden uzun sürüyor");
  else if(progress.remaining!=null) parts.push(`tahmini kalan ~${durationText(progress.remaining)}`);
  return parts.join(" · ");
}

export function claudeBar(job, now=Date.now()) {
  const progress=claudeProgress(job,now);
  if(!progress) return "";
  return `<div class="claude-progress" data-progress-job="${esc(job.id)}" title="${esc(progress.basis?`Tahmin: ${progress.basis}`:"")}">
    <div class="claude-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress.percent}"><span style="width:${progress.percent}%"></span></div>
    <p class="claude-progress-text">${esc(progressText(progress))}</p></div>`;
}
