import {esc} from "./api.js";

// GÖREV-21: the statuses of a video's steps as the sidebar and the step screens show them. The statuses are stored on the server
// (studio/workflow.py): bekliyor, hazır, çalışıyor, onay bekliyor, onaylandı, tamamlandı, hata, eskidi. The sidebar itself (the
// project layer and the video layer) is studio/web/layers.js.

export const STATUS_TONE={waiting:"",ready:"ready",running:"running",awaiting_approval:"warm",approved:"green",done:"green",error:"error",
  stale:"warm"};
export const STATUS_LABELS={waiting:"bekliyor",ready:"hazır",running:"çalışıyor",awaiting_approval:"onay bekliyor",approved:"onaylandı",
  done:"tamamlandı",error:"hata",stale:"eskidi"};
const VIDEO_KEY="studio.video.";

/** The open video of a destination as this browser remembers it (the server remembers it too; this only bridges a first paint). */
export function storedVideo(storage, destinationId) {
  try { return storage?.getItem(VIDEO_KEY+destinationId) || ""; } catch { return ""; }
}

export function persistVideo(storage, destinationId, videoId) {
  try {
    if(videoId) storage?.setItem(VIDEO_KEY+destinationId, videoId);
    else storage?.removeItem(VIDEO_KEY+destinationId);
  } catch { /* private window: the choice lasts until the page closes */ }
}

/** "3/8" */
export function progressText(workflow) {
  if(!workflow || !workflow.video) return "";
  return `${workflow.completed}/${workflow.total}`;
}

/** The status tag of a step ("onay bekliyor"); a step that is not built yet says "sonraki görevde gelecek". */
export function statusTag(step) {
  return `<span class="tag ${step.planned?"planned":STATUS_TONE[step.status] || ""}">${esc(step.label)}</span>`;
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
    ${statusTag(step)}</p>`;
}
