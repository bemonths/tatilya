import {destinationOptions, storedDestination, persistDestination, resetDestinationState} from "./destinations.js";
import {api, esc, host, date, setDestination, destinationRevision, destinationPath, startHeartbeat} from "./api.js";
import {roadmap} from "./roadmap.js";
import {connectorState, jobResultTarget, domainTarget} from "./connectors.js";
import {RestaurantScreen, SITE_CONNECTOR} from "./restaurants.js";
import {NeighborhoodScreen} from "./neighborhoods.js";
import {LodgingScreen, LODGING_CONNECTOR} from "./lodging.js";
import {AgencyPrices, AGENCY_CONNECTOR} from "./agency.js";
import {ClimateScreen, CLIMATE_ACTIONS, CLIMATE_BUTTONS, CLIMATE_CONNECTORS} from "./climate.js";
import {ReferencesScreen} from "./references.js";
import {WeatherScreen} from "./weather.js";
import {BeachScreen} from "./collection.js";
import {refreshSection} from "./refresh.js";
import {EvidenceScreen} from "./evidence.js";
import {VideosScreen, videoCard} from "./videos.js";
import {storedVideo, persistVideo, progressText, videoOptions, stepOfHash, stepNav, toolNav, nextTask, packHead} from "./workflow.js";
import {renderClaudeSettings, renderSuffixSettings} from "./claude.js";
import {UsagePanel, claudeBar, claudeProgress, progressText as claudeProgressText} from "./usage.js";
import {InstructionEditor} from "./instructions.js";
import {ExtensionSettings} from "./extension.js";

const $ = selector => document.querySelector(selector);
const state = {data:null, page:"sources", selected:null, search:"", category:"", region:"", archived:false, editing:null, workflow:null, videoId:""};
const statusLabels = {queued:"Sırada", running:"Çalışıyor", done:"Tamamlandı", failed:"Hata", canceled:"İptal edildi", interrupted:"Yarıda kaldı"};
const active = job => ["queued", "running"].includes(job.status);
let toastTimer;
let events=null;
let lastCollectionId=null;
let lastJobKey="";
const beachScreen=new BeachScreen();
const weatherScreen=new WeatherScreen();
let lastWeatherId=null;
let lastRestaurantId=null;
const restaurantScreen=new RestaurantScreen();
let lastNeighborhoodId=null;
const neighborhoodScreen=new NeighborhoodScreen();
let lastLodgingId=null, lastAgencyId=null, lastSiteId=null, lastDailyId=null;
const agencyPrices=new AgencyPrices();
const lodgingScreen=new LodgingScreen(agencyPrices);
// The three climate jobs can be queued together; refresh on every newly finished one, not only the newest.
let climateDoneIds=new Set();
const climateDone=jobs=>jobs.filter(j=>j.kind==="source_collection" && j.status==="done" && Object.values(CLIMATE_CONNECTORS).includes(j.result?.connector_name)).map(j=>j.id);
const climateScreen=new ClimateScreen();
const referencesScreen=new ReferencesScreen();
const evidenceScreen=new EvidenceScreen();
const videosScreen=new VideosScreen();
let lastClaudeKey="";
const usagePanel=new UsagePanel(document.querySelector("#usage-panel"));
let lastUsageLoad=0;
let lastWorkflowKey="";
let workflowSequence=0;
let packSequence=0;
const collectionScreens={"#collect":beachScreen,"#collect/weather":weatherScreen,"#collect/restaurants":restaurantScreen,"#collect/neighborhoods":neighborhoodScreen,"#collect/lodging":lodgingScreen,"#collect/climate":climateScreen,"#collect/references":referencesScreen};
const collectionActions={"collect-daily-needs":"openstreetmap-daily-needs","collect-beaches":"south-walton-beaches","collect-weather":"nws-weather","collect-restaurants":"south-walton-restaurants","collect-neighborhoods":"south-walton-neighborhoods","collect-lodging":LODGING_CONNECTOR,"collect-agency-rates":AGENCY_CONNECTOR,"collect-restaurant-sites":SITE_CONNECTOR,
  ...Object.fromEntries(Object.entries(CLIMATE_ACTIONS).map(([action,key])=>[action,CLIMATE_CONNECTORS[key]]))};

function toast(text) {
  if(!text) return;
  clearTimeout(toastTimer);
  $("#toast").textContent = text;
  $("#toast").hidden = false;
  toastTimer = setTimeout(() => { $("#toast").hidden = true; }, 5000);
}

function options(values, selected="", empty=null) {
  return (empty !== null ? `<option value="">${esc(empty)}</option>` : "") + values.map(value =>
    `<option value="${esc(value)}" ${value === selected ? "selected" : ""}>${esc(value)}</option>`).join("");
}

// GÖREV-14: ADIMLAR (the selected video's eight steps with live statuses) and VERİ (the tool screens).
function navigation() {
  $("#navigation").innerHTML = stepNav(state.workflow, stepOfHash(location.hash)) + toolNav(state.data.steps, state.page);
}

function currentStep() {
  return state.workflow?.steps.find(step=>step.id===stepOfHash(location.hash)) || null;
}

function nextTaskSlot(step) {
  return `<div id="next-task-slot">${nextTask(step)}</div>`;
}

async function loadWorkflow() {
  const ticket=++workflowSequence, first=!state.workflow;
  const result=await api(state.videoId?`workflow?video_id=${encodeURIComponent(state.videoId)}`:"workflow");
  if(ticket!==workflowSequence) return;
  state.workflow=result;
  if(state.videoId && !result.video) {state.videoId="";persistVideo(localStorage,state.data.selected_destination.id,"");}
  $("#video-select").innerHTML=videoOptions(result,state.videoId);
  $("#workflow-progress").textContent=progressText(result);
  $("#workflow-progress").title=result.video?`${result.video.title_en} · ${result.video.region_name}`:"Video seçilmedi";
  navigation();
  if(first && ["adim","videos"].includes(state.page)) {render();return;}
  const slot=document.querySelector("#next-task-slot");
  if(slot) slot.innerHTML=nextTask(currentStep());
}

function selectVideo(videoId) {
  state.videoId=videoId || "";
  persistVideo(localStorage,state.data.selected_destination.id,state.videoId);
  return loadWorkflow().then(()=>{if(["adim","videos"].includes(state.page)) render();});
}

function renderStep() {
  const key=stepOfHash(location.hash);
  if(key==="baslik") {location.hash="#videos";return;}
  const step=currentStep();
  if(!step) {$("#main").innerHTML='<p role="status" class="loading">İş akışı yükleniyor…</p>';return;}
  if(key==="veri") renderDataStep(step);
  else if(key==="paket") renderPackStep(step);
  else renderPlannedStep(step);
}

function renderDataStep(step) {
  $("#main").innerHTML = pageHeading("Veri", `${state.data.selected_destination.name} için toplanan verinin durumu: hangi kaynağın güncelleme zamanı geldi, hangisi güncel.`) +
    nextTaskSlot(step) + `<div id="refresh-section">${refreshSection(state.data.refresh,state.data.jobs.some(active))}</div>
    <div class="planned-grid tool-links">${state.data.steps.map(tool=>`<a class="planned-card" href="#${esc(tool.id)}"><span class="eyebrow">VERİ ARACI</span><h3>${esc(tool.title)}</h3><p>${esc(tool.subtitle)}</p></a>`).join("")}</div>`;
  updateRefresh().catch(()=>{});
}

async function renderPackStep(step) {
  const ticket=++packSequence;
  $("#main").innerHTML = pageHeading("Veri paketi", "Seçilen başlığın içerik planından kurulan kanıt paketi: bölümler planın sırasıyla gelir, her bölümde dayandığı satırlar ve blokları bulunur.") +
    nextTaskSlot(step) + '<div id="pack-step-body" aria-live="polite"><p>Yükleniyor…</p></div>';
  const body=$("#pack-step-body");
  if(!state.videoId) {body.innerHTML='<section class="quality-result empty"><h2>Video seçilmedi</h2><p>Üst çubuktaki video seçiciden bir video seçin ya da 2. adımda (Konu ve başlık) bir başlık seçin.</p><a class="return-link" href="#videos">Konu ve başlık →</a></section>';return;}
  try {
    const videos=await api("videos");
    if(ticket!==packSequence) return;
    const video=videos.find(v=>v.id===state.videoId);
    body.innerHTML=video?`<section class="library"><div class="library-title"><h2>Seçili video</h2><small>${esc(video.region_name)}</small></div><div class="video-list">${videoCard(video)}</div></section><div id="pack-head-slot"></div>`:'<p class="muted">Seçili video bulunamadı.</p>';
    const pack=video?.packs?.[0];
    if(pack) {
      fetch(`/api/${destinationPath(`evidence-packs/${encodeURIComponent(pack.id)}/yazar-ozeti`)}`).then(r=>r.ok?r.text():Promise.reject(new Error("Paket okunamadı."))).then(text=>{
        if(ticket!==packSequence) return;
        const slot=$("#pack-head-slot");
        if(slot) slot.innerHTML=`<section class="library pack-head"><div class="library-title"><h2>Paketin başı</h2><small>yazar özeti · paket ${esc(pack.id.slice(0,8))} · ${esc(date(pack.created_at))}</small></div><pre class="path pack-head-text">${esc(packHead(text))}</pre></section>`;
      }).catch(error=>{const slot=$("#pack-head-slot");if(slot) slot.textContent=error.message;});
    }
    body.querySelectorAll("[data-video-pack]").forEach(button=>button.addEventListener("click",async()=>{
      button.disabled=true;
      try {
        await api(`videos/${encodeURIComponent(button.dataset.videoPack)}/evidence-pack`,{method:"POST",body:"{}"});
        toast("Video için kanıt paketi üretildi.");
        await loadWorkflow();renderPackStep(currentStep());
      } catch(error) {if(!error.stale) toast(error.message);button.disabled=false;}
    }));
  } catch(error) {if(!error.stale && ticket===packSequence) body.textContent=error.message;}
}

const PLANNED_ROADMAP={metin:"article",kontrol:"check",gorsel:"visuals",uretim:"video",yayin:"publish"};

function renderPlannedStep(step) {
  const plan=roadmap[PLANNED_ROADMAP[step.id]];
  $("#main").innerHTML = `<div class="planned-layout">${pageHeading(step.title, "Bu adım geliştirme planında; henüz kurulmadı.")}${nextTaskSlot(step)}
    ${plan?`<section class="planned-hero"><span class="tag warm">Planlanan adım · Henüz bağlı değil</span><h2>${esc(plan.headline)}</h2><p>${esc(plan.description)}</p><a class="return-link" href="#videos">← Konu ve başlık</a></section>
    <div class="planned-grid">${plan.cards.map(([label,title,description])=>`<section class="planned-card"><span class="eyebrow">${esc(label)}</span><h3>${esc(title)}</h3><p>${esc(description)}</p></section>`).join("")}</div>`:""}</div>`;
}

function pageHeading(title, description, actions="") {
  return `<div class="breadcrumb">30A STUDIO <span>/</span> ÇALIŞMA ALANI <span>/ ${esc(title.toLocaleUpperCase("tr"))}</span></div>
    <div class="page-heading"><div><h1>${esc(title)}</h1><p>${esc(description)}</p></div>${actions ? `<div class="heading-actions">${actions}</div>` : ""}</div>`;
}

function render() {
  if (!state.data) return;
  state.page = location.hash.slice(1).split("/")[0] || "sources";
  if (![...state.data.steps.map(step=>step.id),"settings","videos","adim"].includes(state.page)) state.page="sources";
  navigation();
  beachScreen.invalidate();
  weatherScreen.invalidate();
  restaurantScreen.invalidate();
  neighborhoodScreen.invalidate();
  lodgingScreen.invalidate();
  climateScreen.invalidate();
  referencesScreen.invalidate();
  evidenceScreen.invalidate();
  videosScreen.invalidate();
  const title = currentStep()?.title || state.data.steps.find(step=>step.id===state.page)?.title || (state.page==="videos"?"Konu ve başlık":"Ayarlar");
  document.title = `30A Studio · ${title}`;
  if (state.page === "sources") renderSources();
  else if (state.page === "collect") (collectionScreens[location.hash] || beachScreen).render($("#main"),state.data,pageHeading);
  else if (state.page === "quality") renderQuality();
  else if (state.page === "evidence") evidenceScreen.render($("#main"),state.data,pageHeading);
  else if (state.page === "videos") videosScreen.render($("#main"),state.data,(title,description,actions)=>pageHeading(title,description,actions)+nextTaskSlot(currentStep()));
  else if (state.page === "adim") renderStep();
  else if (state.page === "settings") renderSettings();
  updateAuditButtons();
}

function renderSources() {
  const sources = state.data.sources.filter(source=>source.enabled);
  const categories = new Set(sources.map(source=>source.category));
  $("#main").innerHTML = pageHeading("Veri kaynakları", `${state.data.selected_destination.name} hakkında bildiğimiz her şeyin başlangıç noktası. Kaynakları seç, düzenle ve veri toplamaya hazırla.`,
    `<button data-action="audit">✓ Kayıtları kontrol et</button><button data-action="add" class="primary"><span class="plus">+</span> Kaynak ekle</button>`) +
    `<section class="overview" aria-label="Kaynak özeti">
      <div class="metric"><span class="metric-icon" aria-hidden="true">▤</span><div><div class="metric-number"><strong>${sources.length.toLocaleString("tr")}</strong><span class="metric-label">etkin kaynak</span></div><small>Kütüphaneye eklenen kaynak adayları</small></div></div>
      <div class="metric"><span class="metric-icon" aria-hidden="true">▦</span><div><div class="metric-number"><strong>${categories.size}</strong><span class="metric-label">kategoride kaynak</span></div><small>Konaklamadan etkinliklere</small></div></div>
      <div class="metric"><span class="metric-icon" aria-hidden="true">⇣</span><div><div class="metric-number"><strong>${state.data.collections[0]?.included_count || 0}</strong><span class="metric-label">son çekimde veri kaydı</span></div><small>${state.data.collections.length?"Plaj erişimleri · "+esc(date(state.data.collections[0].fetched_at)):"Henüz plaj verisi yok"}</small></div></div>
    </section>
    <div id="refresh-section">${refreshSection(state.data.refresh,state.data.jobs.some(active))}</div>
    <div class="workspace-grid"><section class="library" aria-label="Kaynak kütüphanesi">
      <div class="library-title"><h2>Kaynak kütüphanesi</h2><small>${esc(state.data.selected_destination.name)} / ${esc(state.data.selected_destination.subtitle)}</small></div>
      <div class="toolbar"><div class="search-wrap"><span aria-hidden="true">⌕</span><input type="search" id="source-search" aria-label="Kaynak ara" placeholder="Kaynak adı, adres veya not ara…" value="${esc(state.search)}"></div>
        <select id="category-filter" aria-label="Kategori filtresi">${options(state.data.categories,state.category,"Tüm kategoriler")}</select>
        <select id="region-filter" aria-label="Bölge filtresi">${options(state.data.regions,state.region,"Tüm bölgeler")}</select></div>
      <div class="filter-row"><button class="tab ${!state.archived?"active":""}" data-action="active" aria-pressed="${!state.archived}">Etkin kaynaklar</button><button class="tab ${state.archived?"active":""}" data-action="archived" aria-pressed="${state.archived}">Arşiv</button><span id="filter-count" class="filter-count"></span></div>
      <div class="table-scroll"><table><thead><tr><th scope="col">KAYNAK</th><th scope="col">KATEGORİ</th><th scope="col">YÖNTEM</th><th scope="col">SIKLIK</th><th scope="col">DURUM</th></tr></thead><tbody id="source-rows"></tbody></table></div>
      <div class="table-note"><span aria-hidden="true">ⓘ</span> Kaynak kaydı eklemek veri çekme işlemini başlatmaz.</div>
    </section><section id="source-detail" class="detail" aria-label="Seçili kaynak ayrıntıları"></section></div>
    <div class="stage-note"><span class="note-mark" aria-hidden="true">↳</span><p><strong>Destinasyonun bağlı kaynakları.</strong> <a href="#collect">Veri toplama</a> ekranından hazır kaynakları çekebilir, kayıtları ve önceki sürümleri inceleyebilirsin.</p></div>`;
  $("#source-search").addEventListener("input", event=>{state.search=event.target.value; renderRows();});
  $("#category-filter").addEventListener("change", event=>{state.category=event.target.value; renderRows();});
  $("#region-filter").addEventListener("change", event=>{state.region=event.target.value; renderRows();});
  renderRows();
}

function sourceDomainLink(source) {
  const target=domainTarget(source.connector?.name);
  return target?`<a href="${target.href}">${target.label} →</a>`:source.connector?"Toplayıcı hazır.":"Bu kaynak için veri toplayıcısı henüz bağlı değil.";
}

function renderRows() {
  const query = state.search.toLocaleLowerCase("tr").trim();
  const sources = state.data.sources.filter(source=>Boolean(source.enabled)!==state.archived)
    .filter(source=>!state.category || source.category===state.category)
    .filter(source=>!state.region || source.region===state.region)
    .filter(source=>`${source.name} ${source.url} ${source.notes}`.toLocaleLowerCase("tr").includes(query));
  if (!sources.some(source=>source.id===state.selected)) state.selected=sources[0]?.id || null;
  $("#filter-count").textContent = `${sources.length} kaynak`;
  $("#source-rows").innerHTML = sources.length ? sources.map(source=>
    `<tr class="${source.id===state.selected?"selected":""}"><td><button class="source-name" data-action="select" data-id="${source.id}" aria-pressed="${source.id===state.selected}">${esc(source.name)}</button><div class="source-host">${esc(host(source.url))}</div></td><td><span class="tag">${esc(source.category)}</span></td><td class="method">${esc(connectorState(source).method)}</td><td class="method">${esc(source.cadence)}</td><td><span class="tag ${source.connector != null && source.enabled?"green":"warm"}">${connectorState(source).label}</span></td></tr>`).join("") :
    `<tr class="empty-row"><td colspan="5">${state.archived?"Bu filtrelerde arşivlenmiş kaynak yok.":"Bu filtrelerde kaynak bulunamadı."}<br><button data-action="clear" class="quiet" style="margin-top:15px;font-size:11px">Filtreleri temizle</button></td></tr>`;
  const source = sources.find(source=>source.id===state.selected);
  $("#source-detail").innerHTML = source ? `<div class="detail-icon" aria-hidden="true">↗</div><span class="eyebrow">KAYNAK AYRINTISI</span><h2>${esc(source.name)}</h2><p>${esc(source.notes || "Bu kaynak için henüz açıklama eklenmedi.")}</p>
    <dl><div><dt>Kategori</dt><dd>${esc(source.category)}</dd></div><div><dt>Bölge</dt><dd>${esc(source.region)}</dd></div><div><dt>Yöntem</dt><dd>${esc(connectorState(source).method)}</dd></div>${source.connector?`<div><dt>Toplayıcı</dt><dd>${esc(source.connector.name)}</dd></div><div><dt>Toplayıcı sürümü</dt><dd>${esc(source.connector.version || "Belirtilmemiş")}</dd></div>`:""}<div><dt>Planlanan sıklık</dt><dd>${esc(source.cadence)}</dd></div><div><dt>Son düzenleme</dt><dd>${esc(date(source.updated_at))}</dd></div></dl>
    <a class="source-link" href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">Kaynağın sitesini aç ↗</a>
    <div class="detail-actions"><button data-action="edit" data-id="${source.id}">Düzenle</button><button class="quiet" data-action="archive" data-id="${source.id}">${source.enabled?"Arşivle":"Geri al"}</button></div><div class="detail-foot">${sourceDomainLink(source)}</div>` :
    `<div class="empty"><span class="empty-icon">▤</span><h3>Kaynak ayrıntıları</h3><p>Listedeki bir kaynağı seçerek açıklamasını ve toplama planını görebilirsin.</p></div>`;
}

function reportStale(report) {
  const current = state.data.sources.filter(source=>source.enabled);
  return current.length !== report.findings.length || report.findings.some(finding=>!current.some(source=>source.id===finding.source_id && source.version===finding.version));
}

function renderQuality() {
  const completed = state.data.jobs.find(job=>job.kind==="catalog_audit" && job.status==="done" && job.result);
  const report = completed?.result;
  $("#main").innerHTML = pageHeading("Veri kontrolü", "Kaynak kayıtlarındaki hazırlık eksikleri. Toplama sırasında plaj kayıtlarının alan, kimlik ve koordinatları; hava verilerinin NWS yanıtları, restoranların kimlik, mahalle ve detay alanları ve mahallelerin kimlik, ad ve sayfa eşleşmesi doğrulanır.", '<button class="primary" data-action="audit">✓ Kayıtları kontrol et</button>') +
    (report ? `<section class="quality-result">${reportStale(report)?'<div class="stale-notice">Kaynak kayıtları bu kontrolden sonra değişti. Güncel sonuç için kontrolü yeniden çalıştır.</div>':""}
      <div class="quality-summary"><span class="eyebrow">SON KATALOG KONTROLÜ · ${esc(date(completed.finished_at))}</span><h2 style="margin-top:10px">${report.checked} kayıt incelendi · ${report.needs_attention} kayıtta eksik bilgi</h2><p>${esc(report.scope)}</p></div>
      ${report.findings.map(finding=>`<div class="quality-row"><strong>${esc(finding.name)}</strong><span>${finding.issues.length?finding.issues.map(esc).join(" "):"Kayıt bilgileri tamam."}</span></div>`).join("")}</section>` :
      `<section class="quality-result empty"><div class="empty-icon">✓</div><h3>Henüz kontrol yapılmadı</h3><p>Kaynak kayıtlarındaki toplama yöntemi ve açıklama alanlarını kontrol ederek eksik hazırlıkları listeleyebilirsin.</p></section>`);
}

function renderSettings() {
  $("#main").innerHTML = pageHeading("Ayarlar", "30A Studio’nun sürümü, kayıt konumu ve Claude ayarları.") +
    `<div class="info-grid"><section class="info-card"><span class="eyebrow">BU BİLGİSAYARDA</span><h2 style="margin-top:12px">Destinasyonların kayıt alanı</h2><p>Kaynaklar, düzenleme geçmişi ve iş sonuçları aşağıdaki klasörde saklanır.</p><div class="path">${esc(state.data.data_path)}</div><p style="margin-top:15px">Uygulamayı kapatıp açınca kayıtların korunur. Yedek almak için uygulamayı kapattıktan sonra bu klasörün tamamını kopyalayabilirsin.</p></section>
    <section class="info-card"><span class="eyebrow">SÜRÜM ${esc(state.data.version)}</span><h2 style="margin-top:12px">Veri, kanıt paketi ve konu önerisi hazır</h2><p>Kaynak kütüphanesi, plaj, hava, restoran, mahalle, iklim, konaklama ve günlük ihtiyaç verisi toplama; kanıt paketi ve yazar özeti; Videolar ekranında Claude ile konu ve başlık önerisi ve video kaydı kullanılabilir.</p><span class="tag warm">Sonraki aşama</span><p style="margin-top:12px">Claude ile video metni ve metnin kontrolü. Görsel plan, video üretimi ve yayın hazırlığı aşamalı olarak eklenecek.</p><a href="#collect" class="return-link">Toplanan verileri gör →</a></section></div><div class="info-grid claude-grid" id="claude-settings-slot"><p class="muted">Claude ayarları yükleniyor…</p></div>
    <div class="info-grid claude-grid"><div id="suffix-settings-slot"><p class="muted">Başlık eki yükleniyor…</p></div><div id="usage-settings-slot"></div></div>
    <div class="info-grid claude-grid" id="instructions-slot"><p class="muted">Talimatlar yükleniyor…</p></div>
    <div class="info-grid claude-grid" id="extension-slot"><p class="muted">Tarayıcı eklentisi yükleniyor…</p></div>`;
  new ExtensionSettings($("#extension-slot")).load();
  renderClaudeSettings($("#claude-settings-slot"));
  renderSuffixSettings($("#suffix-settings-slot"));
  api("claude/usage").then(view=>{const slot=$("#usage-settings-slot");if(slot) slot.innerHTML=`<section class="info-card"><span class="eyebrow">CLAUDE KULLANIMI</span><h2 style="margin-top:12px">Kullanım paneli</h2><p>${esc(view.refresh.text)}</p><p class="muted">Model: <code>${esc(view.refresh.model)}</code> · efor: ${view.refresh.effort==="low"?"düşük":esc(view.refresh.effort)}</p></section>`;}).catch(()=>{});
  new InstructionEditor($("#instructions-slot")).load();
}

function renderJobResultLink(job) {
  const target=jobResultTarget(job,state.data.beach_connector.name);
  return target?`<a href="${target.href}" class="return-link" data-view-report>${target.label} →</a>`:"";
}

function renderJobs() {
  const jobs = state.data.jobs;
  $("#jobs-count").textContent = jobs.filter(active).length;
  $("#jobs-content").innerHTML = jobs.length ? jobs.map(job=>`<article class="job"><div class="job-meta"><span class="tag ${job.status==="done"?"green":"warm"}">${esc(statusLabels[job.status] || job.status)}</span><time>${esc(date(job.created_at))}</time></div><h3>${esc(job.title)}</h3>${job.source_name?`<p>Kaynak: ${esc(job.source_name)}</p>`:""}${claudeBar(job) || `<progress max="100" value="${job.progress}" aria-label="İş ilerlemesi"></progress>`}${job.waiting_for?`<p class="job-waiting"><span class="tag warm">Kullanıcı doğrulaması bekleniyor</span> ${esc(job.waiting_for)}</p>`:""}<p>${esc(job.message)}</p>${active(job) && job.progress_info?.tur==="eklenti" && job.progress_info.bekliyor?`<button data-handover-job="${job.id}">Programın tarayıcısına devret</button> `:""}${active(job)?`<button class="quiet" data-cancel-job="${job.id}">İptal et</button>`:""}<details><summary>İş günlüğü (${job.log.length})</summary>${job.log.map(entry=>`<div class="log-line"><time>${esc(date(entry.at))}</time>${esc(entry.text)}</div>`).join("")}</details>${renderJobResultLink(job)}</article>`).join("") :
    '<div class="empty"><div class="empty-icon">⌁</div><h3>Henüz iş yok</h3><p>Kaynak ekranında “Kayıtları kontrol et” düğmesine bastığında işin durumu ve sonucu burada görünür.</p></div>';
  updateAuditButtons();
}

function updateAuditButtons() {
  updateWeatherButton();
  const restaurantSource=state.data.sources.find(s=>s.enabled && s.connector?.name==="south-walton-restaurants");
  const restaurantBusy=state.data.jobs.some(j=>j.source_id===restaurantSource?.id && active(j));
  document.querySelectorAll('[data-action="collect-restaurants"]').forEach(button=>{button.disabled=!restaurantSource || restaurantBusy;button.textContent=restaurantBusy?"Toplama sürüyor…":"↓ Restoran verilerini topla";});
  const siteSource=state.data.sources.find(s=>s.enabled && s.connector?.name===SITE_CONNECTOR);
  const siteBusy=state.data.jobs.some(j=>j.source_id===siteSource?.id && active(j));
  document.querySelectorAll('[data-action="collect-restaurant-sites"]').forEach(button=>{button.disabled=!siteSource || siteBusy;button.textContent=siteBusy?"Siteler okunuyor…":"↓ İşletme sitelerinden bilgi topla";});
  const lodgingSource=state.data.sources.find(s=>s.enabled && s.connector?.name===LODGING_CONNECTOR);
  const lodgingBusy=state.data.jobs.some(j=>j.source_id===lodgingSource?.id && active(j));
  document.querySelectorAll('[data-action="collect-lodging"]').forEach(button=>{button.disabled=!lodgingSource || lodgingBusy;button.textContent=lodgingBusy?"Toplama sürüyor…":"↓ Konaklama aramalarını topla";});
  const agencySource=state.data.sources.find(s=>s.enabled && s.connector?.name===AGENCY_CONNECTOR);
  const agencyBusy=state.data.jobs.some(j=>j.source_id===agencySource?.id && active(j));
  document.querySelectorAll('[data-action="collect-agency-rates"]').forEach(button=>{button.disabled=!agencySource || agencyBusy;button.textContent=agencyBusy?"Fiyatlar soruluyor…":"↓ Kiralama şirketi fiyatlarını topla";});
  const neighborhoodSource=state.data.sources.find(s=>s.enabled && s.connector?.name==="south-walton-neighborhoods");
  const neighborhoodBusy=state.data.jobs.some(j=>j.source_id===neighborhoodSource?.id && active(j));
  document.querySelectorAll('[data-action="collect-neighborhoods"]').forEach(button=>{button.disabled=!neighborhoodSource || neighborhoodBusy;button.textContent=neighborhoodBusy?"Toplama sürüyor…":"↓ Mahalle verilerini topla";});
  for(const [action,key] of Object.entries(CLIMATE_ACTIONS)) {
    const climateSource=state.data.sources.find(s=>s.enabled && s.connector?.name===CLIMATE_CONNECTORS[key]);
    const climateBusy=state.data.jobs.some(j=>j.source_id===climateSource?.id && active(j));
    document.querySelectorAll(`[data-action="${action}"]`).forEach(button=>{button.disabled=!climateSource || climateBusy;button.textContent=climateBusy?"Toplama sürüyor…":CLIMATE_BUTTONS[key];});
  }
  const busy = state.data.jobs.some(job=>job.kind==="catalog_audit" && active(job));
  document.querySelectorAll('[data-action="audit"]').forEach(button=>{
    button.disabled=busy || !state.data.sources.some(source=>source.enabled);
    button.textContent=busy?"Kontrol sürüyor…":"✓ Kayıtları kontrol et";
  });
  const collecting=state.data.jobs.some(job=>job.kind==="source_collection" && active(job) && state.data.sources.some(source=>source.id===job.source_id && source.connector?.name===state.data.beach_connector.name));
  document.querySelectorAll('[data-action="collect-beaches"]').forEach(button=>{
    button.disabled=collecting || !state.data.sources.some(source=>source.enabled && source.connector?.name===state.data.beach_connector.name);
    button.textContent=collecting?"Toplama sürüyor…":"↓ Plaj verilerini topla";
  });
}

function updateWeatherButton() {
  const source=state.data.sources.find(source=>source.enabled && source.connector?.name===state.data.weather_connector.name);
  const busy=state.data.jobs.some(job=>job.source_id===source?.id && active(job));
  document.querySelectorAll('[data-action="collect-weather"]').forEach(button=>{
    button.disabled=!source || busy;
    button.textContent=busy?"Toplama sürüyor…":"↓ Hava verilerini topla";
  });
}

function toggleJobs(open) {
  $("#jobs-panel").hidden=!open;
  $("#jobs-toggle").setAttribute("aria-expanded", String(open));
  if(open) $("#jobs-close").focus();
  else $("#jobs-toggle").focus();
}

function openEditor(source=null) {
  state.editing=source;
  const form=$("#source-form");
  form.reset();
  $("#dialog-title").textContent=source?"Kaynağı düzenle":"Kaynak ekle";
  const fields={category:"categories",region:"regions",method:"methods",cadence:"cadences"};
  for(const [name,key] of Object.entries(fields)) form.elements[name].innerHTML=options(state.data[key],source?.[name] || ({cadence:"Haftalık"}[name] || state.data[key][0]));
  for(const name of ["name","url","notes"]) form.elements[name].value=source?.[name] || "";
  $("#form-error").hidden=true;
  $("#source-dialog").showModal();
  form.elements.name.focus();
}

async function updateRefresh() {
  state.data.refresh=await api("refresh");
  const box=document.querySelector("#refresh-section");
  if(box) box.innerHTML=refreshSection(state.data.refresh,state.data.jobs.some(active));
}

async function refreshSources() {
  const sources=await api("sources");
  state.data.sources=sources;
  render();
}

$("#source-form").addEventListener("submit", async event=>{
  event.preventDefault();
  const button=$("#save-source");
  button.disabled=true;
  $("#form-error").hidden=true;
  const payload=Object.fromEntries(new FormData(event.target));
  payload.destination_id=state.data.selected_destination.id;
  payload.enabled=state.editing?Boolean(state.editing.enabled):true;
  if(state.editing) payload.expected_version=state.editing.version;
  try {
    const result=await api(state.editing?`sources/${state.editing.id}`:"sources",{method:state.editing?"PUT":"POST",body:JSON.stringify(payload)});
    state.selected=result.id;
    $("#source-dialog").close();
    state.archived=!result.enabled;
    state.search="";state.category="";state.region="";
    await refreshSources();
    toast("Kaynak kaydedildi.");
  } catch(error) {
    $("#form-error").textContent=error.message;
    $("#form-error").hidden=false;
  } finally {button.disabled=false;}
});

$("#main").addEventListener("click", async event=>{
  const button=event.target.closest("[data-action]");
  if(!button) return;
  const source=state.data?.sources.find(source=>source.id===button.dataset.id);
  try {
    switch(button.dataset.action) {
      case "select": state.selected=source.id; renderRows(); break;
      case "add": openEditor(); break;
      case "edit": openEditor(source); break;
      case "active": state.archived=false; renderSources(); updateAuditButtons(); break;
      case "archived": state.archived=true; renderSources(); updateAuditButtons(); break;
      case "clear": state.search="";state.region="";state.category="";renderSources();updateAuditButtons();break;
      case "archive": {
        button.disabled=true;
        const payload=Object.fromEntries(["name","url","category","region","method","cadence","notes"].map(key=>[key,source[key]]));
        await api(`sources/${source.id}`,{method:"PUT",body:JSON.stringify({...payload,enabled:!source.enabled,expected_version:source.version})});
        await refreshSources(); toast(source.enabled?"Kaynak arşivlendi. Arşiv sekmesinden geri alabilirsin.":"Kaynak yeniden etkin."); break;
      }
      case "audit": {
        button.disabled=true;
        await api("jobs",{method:"POST",body:JSON.stringify({kind:"catalog_audit"})});
        state.data.jobs=await api("jobs");renderJobs();toggleJobs(true);
        if(state.page==="quality") renderQuality();
        break;
      }
      case "collect-climate-normals":
      case "collect-water-temperature":
      case "collect-storms":
      case "collect-neighborhoods":
      case "collect-daily-needs":
      case "collect-lodging":
      case "collect-agency-rates":
      case "collect-restaurant-sites":
      case "collect-restaurants":
      case "collect-weather":
      case "collect-beaches": {
        button.disabled=true;
        const connectorName=collectionActions[button.dataset.action];
        const source=state.data.sources.find(source=>source.enabled && source.connector?.name===connectorName);
        if(!source) throw new Error("Veri kaynağı etkin değil.");
        await api("jobs",{method:"POST",body:JSON.stringify({kind:"source_collection",source_id:source.id})});
        state.data.jobs=await api("jobs");renderJobs();toggleJobs(true);break;
      }
      case "refresh-start": {
        button.disabled=true;
        const batch=await api("refresh-batches",{method:"POST",body:JSON.stringify({destination_id:state.data.selected_destination.id})});
        toast(`Toplu çalıştırma başladı. ${batch.message || ""}`);
        await updateRefresh();state.data.jobs=await api("jobs");renderJobs();break;
      }
      case "refresh-cancel": {
        button.disabled=true;
        await api(`refresh-batches/${button.dataset.batch}/cancel`,{method:"POST"});
        await updateRefresh();toast("Toplu çalıştırma durduruldu.");break;
      }
      case "reload": location.reload();break;
    }
  } catch(error) {toast(error.message);button.disabled=false;}
});

$("#jobs-content").addEventListener("click",async event=>{
  const cancel=event.target.closest("[data-cancel-job]");
  if(cancel) {
    cancel.disabled=true;
    try {await api(`jobs/${cancel.dataset.cancelJob}/cancel`,{method:"POST"});state.data.jobs=await api("jobs");renderJobs();}
    catch(error){toast(error.message);cancel.disabled=false;}
  }
  const handover=event.target.closest("[data-handover-job]");
  if(handover) {
    handover.disabled=true;
    try {await api(`tarayici-eklentisi/devret/${handover.dataset.handoverJob}`,{method:"POST"});state.data.jobs=await api("jobs");renderJobs();toast("İş programın kendi tarayıcısına devredildi.");}
    catch(error){toast(error.message);handover.disabled=false;}
  }
  if(event.target.closest("[data-view-report]")) toggleJobs(false);
});

$("#jobs-toggle").addEventListener("click",()=>toggleJobs($("#jobs-panel").hidden));
$("#jobs-close").addEventListener("click",()=>toggleJobs(false));
for(const id of ["#dialog-close","#dialog-cancel"]) $(id).addEventListener("click",()=>$("#source-dialog").close());
document.addEventListener("keydown",event=>{if(event.key==="Escape" && !$("#jobs-panel").hidden && !$("#source-dialog").open) toggleJobs(false);});
window.addEventListener("hashchange",render);

async function start(destinationId=storedDestination(localStorage)) {
  events?.close();events=null;
  const ticket=setDestination(destinationId);
  resetDestinationState(state,[beachScreen,weatherScreen,restaurantScreen,neighborhoodScreen,lodgingScreen,agencyPrices,climateScreen,referencesScreen,evidenceScreen,videosScreen]);
  lodgingScreen.agency=agencyPrices;   // the reset rebuilds each screen from its constructor; the price section is attached again
  lastCollectionId=lastWeatherId=lastRestaurantId=lastNeighborhoodId=lastLodgingId=lastAgencyId=lastSiteId=null;climateDoneIds=new Set();
  $("#source-dialog").close();
  $("#main").innerHTML='<p role="status">Destinasyon yükleniyor…</p>';
  $("#jobs-content").innerHTML='';
  try {
    let data;
    try { data=await api("bootstrap"); }
    catch(error) {
      if(error.stale) return;
      if(error.status===404 && destinationId && ticket===destinationRevision()) return start(null);
      throw error;
    }
    if(ticket!==destinationRevision()) return;
    state.data=data;
    // Resolve the server default before opening requests and event stream.
    if(!destinationId) { setDestination(data.selected_destination.id); return start(data.selected_destination.id); }
    persistDestination(localStorage,data.selected_destination.id);
    $("#destination-subtitle").textContent=data.selected_destination.subtitle || data.selected_destination.name;
    $("#destination-workspace").textContent=`${data.selected_destination.name} İçerik Stüdyosu`;
    $("#destination-select").innerHTML=destinationOptions(data.destinations,data.selected_destination.id);
    lastCollectionId=state.data.collections[0]?.id || null;
    lastWeatherId=state.data.weather_runs[0]?.id || null;
    lastRestaurantId=state.data.restaurant_runs?.[0]?.id || null;
    lastNeighborhoodId=state.data.neighborhood_runs?.[0]?.id || null;
    lastLodgingId=state.data.lodging_runs?.[0]?.id || null;
    lastAgencyId=state.data.agency_runs?.[0]?.id || null;
    lastSiteId=state.data.restaurant_site_runs?.[0]?.id || null;
    lastDailyId=state.data.daily_needs_runs?.[0]?.id || null;
    climateDoneIds=new Set(climateDone(state.data.jobs));
    $("#app-version").textContent=`v${state.data.version}`;
    state.workflow=null;state.videoId=storedVideo(localStorage,data.selected_destination.id);lastWorkflowKey="";
    $("#video-select").innerHTML=videoOptions(null,"");$("#workflow-progress").textContent="";
    render();renderJobs();
    loadWorkflow().catch(error=>{if(!error.stale) toast(error.message);});
    events=new EventSource(`/api/${destinationPath("events")}`);
    events.addEventListener("open",()=>{
      if(ticket!==destinationRevision()) return;
      $("#connection").textContent="Yerel bağlantı";$("#connection").classList.remove("offline");
      refreshSources().catch(()=>{});
    });
    events.addEventListener("jobs",async event=>{
      if(ticket!==destinationRevision()) return;
      state.data.jobs=JSON.parse(event.data).filter(job=>job.destination_id===state.data.selected_destination.id);renderJobs();
      if(state.page==="quality") {renderQuality();updateAuditButtons();}
      const jobKey=state.data.jobs.map(j=>`${j.id}:${j.status}`).join(",");     // the section changes only when a job starts or ends
      if(["sources","adim"].includes(state.page) && jobKey!==lastJobKey) {lastJobKey=jobKey;updateRefresh().catch(()=>{});}
      if(jobKey!==lastWorkflowKey) {lastWorkflowKey=jobKey;loadWorkflow().catch(()=>{});}   // statuses come from the records
      const claudeJobs=state.data.jobs.filter(j=>j.kind==="claude_run");
      if(claudeJobs.some(active) && Date.now()-lastUsageLoad>15000) {lastUsageLoad=Date.now();usagePanel.load();}   // measurements come live
      const claudeKey=claudeJobs.map(j=>`${j.id}:${j.status}`).join(",");          // a Claude run started or ended: the Videolar screen reloads
      if(claudeKey!==lastClaudeKey) {
        const finished=lastClaudeKey && claudeJobs.find(j=>!active(j) && !lastClaudeKey.includes(`${j.id}:${j.status}`));
        lastClaudeKey=claudeKey;
        usagePanel.load();
        if(state.page==="videos") videosScreen.refresh($("#main"));
        if(finished) toast(finished.status==="done"?"Claude bitti: başlık önerileri Konu ve başlık ekranında onay bekliyor.":`Claude çalışması bitmedi: ${finished.message}`);
      }
      const restaurantLatest=state.data.jobs.find(j=>j.kind==="source_collection" && j.status==="done" && j.result?.connector_name==="south-walton-restaurants");
      if(restaurantLatest && restaurantLatest.id!==lastRestaurantId) {
        try {
          state.data.restaurant_runs=await api("restaurant-runs");lastRestaurantId=restaurantLatest.id;restaurantScreen.selectedRun=null;
          if(location.hash==="#collect/restaurants") render();
          toast("Restoran verileri kaydedildi. Restoranlar sekmesinden inceleyebilirsin.");
        } catch(error) {toast(error.message);}
      }
      const siteLatest=state.data.jobs.find(j=>j.kind==="source_collection" && j.status==="done" && j.result?.connector_name===SITE_CONNECTOR);
      if(siteLatest && siteLatest.id!==lastSiteId) {
        try {
          state.data.restaurant_site_runs=await api("restaurant-site-runs");lastSiteId=siteLatest.id;restaurantScreen.siteSummary=null;
          if(location.hash==="#collect/restaurants") render();
          toast("İşletme sitelerinden restoran bilgileri kaydedildi. Restoranlar sekmesinden inceleyebilirsin.");
        } catch(error) {toast(error.message);}
      }
      const neighborhoodLatest=state.data.jobs.find(j=>j.kind==="source_collection" && j.status==="done" && j.result?.connector_name==="south-walton-neighborhoods");
      if(neighborhoodLatest && neighborhoodLatest.id!==lastNeighborhoodId) {
        try {
          state.data.neighborhood_runs=await api("neighborhood-runs");lastNeighborhoodId=neighborhoodLatest.id;neighborhoodScreen.selectedRun=null;
          if(location.hash==="#collect/neighborhoods") render();
          toast("Mahalle verileri kaydedildi. Mahalleler sekmesinden inceleyebilirsin.");
        } catch(error) {toast(error.message);}
      }
      const dailyLatest=state.data.jobs.find(j=>j.kind==="source_collection" && j.status==="done" && j.result?.connector_name==="openstreetmap-daily-needs");
      if(dailyLatest && dailyLatest.id!==lastDailyId) {
        try {
          state.data.daily_needs_runs=await api("daily-needs-runs");lastDailyId=dailyLatest.id;neighborhoodScreen.daily.selectedRun=null;neighborhoodScreen.daily.snapshot=null;
          if(location.hash==="#collect/neighborhoods") render();
          toast("Günlük ihtiyaç noktaları kaydedildi. Mahalleler sekmesinden inceleyebilirsin.");
        } catch(error) {toast(error.message);}
      }
      const lodgingLatest=state.data.jobs.find(j=>j.kind==="source_collection" && j.status==="done" && j.result?.connector_name===LODGING_CONNECTOR);
      if(lodgingLatest && lodgingLatest.id!==lastLodgingId) {
        try {
          state.data.lodging_runs=await api("lodging-runs");lastLodgingId=lodgingLatest.id;lodgingScreen.selectedRun=null;lodgingScreen.snapshot=null;
          if(location.hash==="#collect/lodging") render();
          toast("Konaklama verileri kaydedildi. Konaklama sekmesinden inceleyebilirsin.");
        } catch(error) {toast(error.message);}
      }
      const agencyLatest=state.data.jobs.find(j=>j.kind==="source_collection" && j.status==="done" && j.result?.connector_name===AGENCY_CONNECTOR);
      if(agencyLatest && agencyLatest.id!==lastAgencyId) {
        try {
          state.data.agency_runs=await api("agency-rate-runs");lastAgencyId=agencyLatest.id;agencyPrices.selectedRun=null;agencyPrices.snapshot=null;
          if(location.hash==="#collect/lodging") render();
          toast("Kiralama şirketi fiyatları kaydedildi. Konaklama sekmesinden inceleyebilirsin.");
        } catch(error) {toast(error.message);}
      }
      const climateFinished=climateDone(state.data.jobs);
      if(climateFinished.some(id=>!climateDoneIds.has(id))) {
        try {
          state.data.climate_runs=await api("climate-runs");climateFinished.forEach(id=>climateDoneIds.add(id));climateScreen.snapshot=null;
          if(location.hash==="#collect/climate") render();
          toast("İklim verileri kaydedildi. İklim sekmesinden inceleyebilirsin.");
        } catch(error) {toast(error.message);}
      }
      const weatherLatest=state.data.jobs.find(job=>job.kind==="source_collection" && job.status==="done" && job.result?.connector_name===state.data.weather_connector.name);
      if(weatherLatest && weatherLatest.id!==lastWeatherId) {
        try {
          state.data.weather_runs=await api("weather-runs");
          lastWeatherId=weatherLatest.id; weatherScreen.selectedRun=null;
          if(state.page==="collect" && location.hash==="#collect/weather") render();
          toast("Hava verileri kaydedildi. Hava sekmesinden inceleyebilirsin.");
        } catch(error) {toast(error.message);}
      }
      const latest=state.data.jobs.find(job=>job.kind==="source_collection" && job.status==="done" && (job.result?.connector_name===state.data.beach_connector.name || state.data.sources.some(source=>source.id===job.source_id && source.connector?.name===state.data.beach_connector.name)));
      if(latest && latest.id!==lastCollectionId) {
        try {
          state.data.collections=await api("collections");
          lastCollectionId=latest.id;
          beachScreen.selectedRun=null;
          if(["sources","collect"].includes(state.page)) render();
          toast("Plaj verileri kaydedildi. Veri toplama ekranından inceleyebilirsin.");
        } catch(error) {toast(error.message);}
      }
    });
    events.addEventListener("error",()=>{if(ticket!==destinationRevision())return;$("#connection").textContent="Yeniden bağlanıyor";$("#connection").classList.add("offline");});
  } catch(error) {
    if(error.stale || ticket!==destinationRevision()) return;
    $("#connection").textContent="Bağlantı kurulamadı";$("#connection").classList.add("offline");
    $("#main").innerHTML=`<section class="error-page"><h1>Çalışma alanı açılamadı</h1><p>${esc(error.message)}</p><p>Başlatma penceresinin açık olduğundan emin olup yeniden dene.</p><button class="primary" data-action="reload">Yeniden dene</button></section>`;
  }
}

$("#destination-select").addEventListener("change",event=>start(event.target.value));
$("#video-select").addEventListener("change",event=>selectVideo(event.target.value).catch(error=>{if(!error.stale) toast(error.message);}));
// GÖREV-14: the Claude bar moves every second between job events; the usage panel fades an old measurement without a reload.
setInterval(()=>{
  if($("#jobs-panel").hidden || !state.data) return;
  for(const job of state.data.jobs.filter(j=>active(j) && j.progress_info)) {
    const box=document.querySelector(`[data-progress-job="${job.id}"]`), progress=claudeProgress(job);
    if(!box || !progress) continue;
    box.querySelector(".claude-bar span").style.width=`${progress.percent}%`;
    box.querySelector(".claude-bar").setAttribute("aria-valuenow",String(progress.percent));
    box.querySelector(".claude-progress-text").textContent=claudeProgressText(progress);
  }
},1000);
setInterval(()=>usagePanel.load(),60000);
usagePanel.draw();usagePanel.load();
document.addEventListener("studio:video-chosen",event=>selectVideo(event.detail).catch(()=>{}));
document.addEventListener("studio:workflow-changed",()=>loadWorkflow().catch(()=>{}));
startHeartbeat();
start();
