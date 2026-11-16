import {esc} from "./api.js";
import {STATUS_TONE} from "./workflow.js";

// GÖREV-21: the two layers of the program and where every screen is (after Rota Stüdyo, TASARIM 13 "Arayüz").
//
// The project layer holds what is done once and used by every video: Veri, Konu bankası, Kanal, Videolar. The video layer holds one
// video's eight steps. They do not mix: with no video open the sidebar shows only the four project screens (and Ayarlar at the bottom);
// with a video open it shows only that video's steps, the video's name with "Videoyu kapat" and one collapsed row, "← Proje".
//
// Addresses:  #sources · #collect[/…] · #quality · #evidence · #veri/okuma   (Veri and its tabs)
//             #konu · #konu/calisma/<id>                                      (Konu bankası)
//             #kanal · #kanal/<bölüm>                                         (Kanal)
//             #videolar · #videolar/arsiv                                     (Videolar)
//             #video/<video>/<adım>[/<görünüm>/<kimlik>]                      (a step of the open video)
//             #settings · #settings/<bölüm>                                   (Ayarlar)
// Old addresses (#videos, #adim/…, #settings/tonlar …) go to their new places (redirectOf).

export const PROJECT_SCREENS=Object.freeze([
  {id:"veri", title:"Veri", sub:"Kaynaklar, toplama, kalite, kanıt", href:"#sources", icon:"▤"},
  {id:"konu", title:"Konu bankası", sub:"Başlık önerileri ve adaylar", href:"#konu", icon:"✦"},
  {id:"kanal", title:"Kanal", sub:"Talimatlar, tonlar, içerik kuralları", href:"#kanal", icon:"♪"},
  {id:"videolar", title:"Videolar", sub:"Projenin videoları", href:"#videolar", icon:"▶"},
].map(Object.freeze));

export const VERI_TABS=Object.freeze([
  {id:"sources", title:"Kaynaklar", href:"#sources"},
  {id:"collect", title:"Toplama", href:"#collect"},
  {id:"quality", title:"Kalite", href:"#quality"},
  {id:"evidence", title:"Kanıt paketi", href:"#evidence"},
  {id:"okuma", title:"Okuma denemeleri", href:"#veri/okuma"},
].map(Object.freeze));

export const KANAL_SECTIONS=Object.freeze([
  {slug:"talimatlar", title:"Talimatlar", icon:"☰"},
  {slug:"tonlar", title:"Tonlar", icon:"♪"},
  {slug:"uyari-ifadeleri", title:"Uyarı ifadeleri", icon:"⚑"},
  {slug:"baslik-eki", title:"Başlık eki", icon:"✎"},
].map(Object.freeze));

const VERI_PAGES=["sources","collect","quality","evidence","veri"];
const SETTINGS_PAGES=["settings","ayarlar"];
/** The Settings sections that moved to the project layer (GÖREV-21) and where they are now. */
export const MOVED_SETTINGS=Object.freeze({talimatlar:"#kanal/talimatlar", tonlar:"#kanal/tonlar", "uyari-ifadeleri":"#kanal/uyari-ifadeleri",
  "baslik-eki":"#kanal/baslik-eki"});
const OLD_STEPS={paket:"paket", kontrol:"kontrol", gorsel:"kurgu", uretim:"kurgu", yayin:"yayin"};

function partsOf(hash) {
  return String(hash || "").replace(/^#\/?/,"").split("/").map(part=>{try {return decodeURIComponent(part);} catch {return part;}});
}

/** Where an address is: {layer: "proje"|"video"|"ayarlar", screen, …}; null for an unknown address. */
export function routeOf(hash) {
  const parts=partsOf(hash), page=parts[0] || "sources";
  if(VERI_PAGES.includes(page)) return {layer:"proje", screen:"veri", page, tab:page==="veri"?"okuma":page};
  if(page==="konu") return {layer:"proje", screen:"konu", page, runId:parts[1]==="calisma" && parts[2]?parts[2]:null};
  if(page==="kanal") return {layer:"proje", screen:"kanal", page, section:KANAL_SECTIONS.some(s=>s.slug===parts[1])?parts[1]:null};
  if(page==="videolar") return {layer:"proje", screen:"videolar", page, archived:parts[1]==="arsiv"};
  if(page==="video" && parts[1]) return {layer:"video", screen:"video", page, videoId:parts[1], step:parts[2] || "baslik", view:parts[3] || null, id:parts[4] || null};
  if(SETTINGS_PAGES.includes(page)) return {layer:"ayarlar", screen:"settings", page:"settings", section:parts[1] || null};
  return null;
}

/** The new address of an old one, or null when the address is current. `openVideo`: the open video's id (old step addresses had none). */
export function redirectOf(hash, openVideo="") {
  const parts=partsOf(hash), page=parts[0];
  if(SETTINGS_PAGES.includes(page) && MOVED_SETTINGS[parts[1]]) return MOVED_SETTINGS[parts[1]];
  if(page==="videos") return parts[1]==="run" && parts[2]?`#konu/calisma/${encodeURIComponent(parts[2])}`:"#konu";
  if(page==="adim") {
    const step=parts[1];
    if(step==="veri") return "#sources";
    if(step==="baslik") return "#konu";
    if(!openVideo) return "#videolar";
    const video=encodeURIComponent(openVideo);
    if(step==="metin") {
      if(parts[2]==="karsilastirma") return `#video/${video}/kontrol`;
      if(parts[2]==="surum" && parts[3]) return `#video/${video}/yazim/surum/${encodeURIComponent(parts[3])}`;
      return `#video/${video}/plan`;
    }
    return `#video/${video}/${OLD_STEPS[step] || "baslik"}`;
  }
  return null;
}

export function stepHref(videoId, step, ...rest) {
  return `#video/${encodeURIComponent(videoId)}/${step}${rest.filter(Boolean).map(part=>`/${encodeURIComponent(part)}`).join("")}`;
}

function projectLinks(active) {
  return PROJECT_SCREENS.map(screen=>`<a href="${screen.href}" class="project-screen ${screen.id===active?"active":""}" data-screen="${screen.id}" ${screen.id===active?'aria-current="page"':""}>
    <span class="step-no tool-no" aria-hidden="true">${screen.icon}</span><span><span class="nav-title">${esc(screen.title)}</span>
    <span class="nav-sub" style="display:block">${esc(screen.sub)}</span></span></a>`).join("");
}

/** No video open: only the four project screens. */
export function projectNav(active=null) {
  return `<div class="group-label">PROJE</div>${projectLinks(active)}`;
}

/** A video is open: its name and "Videoyu kapat", the collapsed "← Proje" row and only this video's eight steps (number, name, status). */
export function videoNav(workflow, activeStep=null, {projectOpen=false, activeScreen=null}={}) {
  const video=workflow.video;
  const steps=workflow.steps.map(step=>{
    const current=step.id===activeStep;
    return `<a href="${stepHref(video.id,step.id)}" class="workflow-step ${current?"active":""} ${step.planned?"planned-step":""}" data-step="${step.id}" ${current?'aria-current="page"':""}>
      <span class="step-no">${step.number}</span><span><span class="nav-title">${esc(step.title)}</span>
      <span class="nav-sub step-status ${step.planned?"planned":STATUS_TONE[step.status] || ""}" style="display:block">${esc(step.label)}</span></span></a>`;
  }).join("");
  return `<div class="video-open"><span class="eyebrow">AÇIK VİDEO</span><strong class="video-name" title="${esc(video.title_en || video.display_name)}">${esc(video.display_name)}</strong>
      <button type="button" class="quiet" id="video-close" data-video-close>Videoyu kapat</button></div>
    <button type="button" class="project-row" id="project-toggle" data-project-toggle aria-expanded="${projectOpen?"true":"false"}" aria-controls="project-collapsed">← Proje</button>
    <div id="project-collapsed" class="project-collapsed" ${projectOpen?"":"hidden"}>${projectOpen?projectLinks(activeScreen):""}</div>
    <div class="group-label">ADIMLAR <span class="steps-progress">${workflow.completed}/${workflow.total}</span></div>${steps}`;
}

/** The sidebar for where the user is: the project's screens, or the open video's steps. */
export function sidebar(workflow, route, projectOpen=false) {
  if(!workflow?.video) return projectNav(route?.layer==="proje"?route.screen:null);
  const onProject=route?.layer==="proje";
  return videoNav(workflow, route?.layer==="video"?route.step:null, {projectOpen:projectOpen || onProject, activeScreen:onProject?route.screen:null});
}

/** The tab row under the heading of a screen that has tabs; the tab names are written on the screen. */
export function tabBar(tabs, active, label) {
  return `<nav class="section-nav layer-tabs" aria-label="${esc(label)}">${tabs.map(tab=>
    `<a class="section-nav-item ${tab.id===active?"active":""}" href="${tab.href}" data-tab="${tab.id}" ${tab.id===active?'aria-current="page"':""}>${esc(tab.title)}</a>`).join("")}</nav>`;
}

export const veriTabs=active=>tabBar(VERI_TABS, active, "Veri sekmeleri");

/** The top bar's project: with one project only its name; with more a selector. */
export function projectLabel(destinations, selected) {
  const name=d=>`${d.name}${d.subtitle?` / ${String(d.subtitle).split(",")[0]}`:""}`;
  const current=(destinations || []).find(d=>d.id===selected?.id) || selected;
  if(!current) return "";
  if((destinations || []).length<2) return `<span class="project-name" id="project-name">${esc(name(current))}</span>`;
  return `<label class="destination-control">Proje <select id="destination-select" aria-label="Proje">${destinations.map(d=>
    `<option value="${esc(d.id)}" ${d.id===current.id?"selected":""}>${esc(name(d))}</option>`).join("")}</select></label>`;
}
