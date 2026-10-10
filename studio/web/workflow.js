import {esc} from "./api.js";

// GÖREV-14: the sidebar's workflow. The unit is a video record (Housing Atlas uses a state): a video selector in the top bar, the
// selected video's eight steps (ADIMLAR) with live statuses computed by the server from the records, and the tool screens (VERİ).

export const STATUS_TONE={waiting:"",ready:"ready",running:"running",awaiting_approval:"warm",approved:"green",done:"green",error:"error",
  stale:"warm",due:"warm",planned:"planned"};
const VIDEO_KEY="studio.video.";

/** The selected video of a destination, remembered in this browser (a convenience; an unknown id simply means no video). */
export function storedVideo(storage, destinationId) {
  try { return storage?.getItem(VIDEO_KEY+destinationId) || ""; } catch { return ""; }
}

export function persistVideo(storage, destinationId, videoId) {
  try {
    if(videoId) storage?.setItem(VIDEO_KEY+destinationId, videoId);
    else storage?.removeItem(VIDEO_KEY+destinationId);
  } catch { /* private window: the selection lasts until the page closes */ }
}

/** "●●○○○○○○ 2/8 adım" */
export function progressText(workflow) {
  if(!workflow) return "";
  return `${workflow.dots} ${workflow.completed}/${workflow.total} adım`;
}

export function videoOptions(workflow, selected="") {
  const videos=workflow?.videos || [];
  return `<option value="">Video seçilmedi</option>`+videos.map(v=>`<option value="${esc(v.id)}" ${v.id===selected?"selected":""}>${esc(v.title_en)}</option>`).join("");
}

/** The step key of a workflow route: "#adim/paket" → "paket"; the Videolar screen is the topic and title step. */
export function stepOfHash(hash) {
  const route=String(hash || "").replace(/^#/,"");
  if(route.startsWith("adim/")) return route.slice(5).split("/")[0];
  if(route==="videos" || route.startsWith("videos/")) return "baslik";
  return null;
}

export function stepNav(workflow, activeStep) {
  if(!workflow) return "";
  return `<div class="group-label">ADIMLAR${workflow.video?"":" · video seçilmedi"}</div>`+workflow.steps.map(step=>{
    const current=step.id===activeStep;
    return `<a href="${esc(step.href)}" class="workflow-step ${current?"active":""} ${step.planned?"planned-step":""}" ${current?'aria-current="page"':""}>
      <span class="step-no">${step.number}</span><span><span class="nav-title">${esc(step.title)}</span>
      <span class="nav-sub step-status ${STATUS_TONE[step.status] || ""}" style="display:block">${esc(step.label)}</span></span></a>`;
  }).join("");
}

export function toolNav(tools, page) {
  return `<div class="group-label">VERİ</div>`+tools.map(tool=>`<a href="#${esc(tool.id)}" class="${page===tool.id?"active":""}" ${page===tool.id?'aria-current="page"':""}>
    <span class="step-no tool-no" aria-hidden="true">${{sources:"▤",collect:"⇣",quality:"✓",evidence:"▦"}[tool.id] || "·"}</span><span><span class="nav-title">${esc(tool.title)}</span>
    <span class="nav-sub" style="display:block">${tool.state==="planned"?"Planlanan aşama":esc(tool.subtitle)}</span></span></a>`).join("");
}

/** The head of a pack's writer's summary: everything before its first section ("## 1. …"), for the Veri paketi step. */
export function packHead(text) {
  const value=String(text || "");
  const end=value.search(/\n## 1\. /);
  return (end>0?value.slice(0,end):value).trim();
}

/** The line every step screen starts with: what has to be done next and which button does it. */
export function nextTask(step) {
  if(!step) return "";
  return `<p class="next-task" role="status"><span class="next-task-label">Sıradaki iş</span><span>${esc(step.next)}</span>
    <span class="tag ${STATUS_TONE[step.status] || ""}">${esc(step.label)}</span></p>${step.detail?`<p class="next-task-detail muted">${esc(step.detail)}</p>`:""}`;
}
