import {destinationOptions, storedDestination, persistDestination, resetDestinationState} from "./destinations.js";
import {api, esc, host, date, setDestination, destinationRevision, destinationPath} from "./api.js";
import {roadmap} from "./roadmap.js";
import {connectorState, jobResultTarget, domainTarget} from "./connectors.js";
import {RestaurantScreen} from "./restaurants.js";
import {NeighborhoodScreen} from "./neighborhoods.js";
import {LodgingScreen, LODGING_CONNECTOR} from "./lodging.js";
import {ClimateScreen, CLIMATE_ACTIONS, CLIMATE_BUTTONS, CLIMATE_CONNECTORS} from "./climate.js";
import {ReferencesScreen} from "./references.js";
import {WeatherScreen} from "./weather.js";
import {BeachScreen} from "./collection.js";

const $ = selector => document.querySelector(selector);
const state = {data:null, page:"sources", selected:null, search:"", category:"", region:"", archived:false, editing:null};
const statusLabels = {queued:"Sırada", running:"Çalışıyor", done:"Tamamlandı", failed:"Hata", canceled:"İptal edildi", interrupted:"Yarıda kaldı"};
const active = job => ["queued", "running"].includes(job.status);
let toastTimer;
let events=null;
let lastCollectionId=null;
const beachScreen=new BeachScreen();
const weatherScreen=new WeatherScreen();
let lastWeatherId=null;
let lastRestaurantId=null;
const restaurantScreen=new RestaurantScreen();
let lastNeighborhoodId=null;
const neighborhoodScreen=new NeighborhoodScreen();
let lastLodgingId=null;
const lodgingScreen=new LodgingScreen();
// The three climate jobs can be queued together; refresh on every newly finished one, not only the newest.
let climateDoneIds=new Set();
const climateDone=jobs=>jobs.filter(j=>j.kind==="source_collection" && j.status==="done" && Object.values(CLIMATE_CONNECTORS).includes(j.result?.connector_name)).map(j=>j.id);
const climateScreen=new ClimateScreen();
const referencesScreen=new ReferencesScreen();
const collectionScreens={"#collect":beachScreen,"#collect/weather":weatherScreen,"#collect/restaurants":restaurantScreen,"#collect/neighborhoods":neighborhoodScreen,"#collect/lodging":lodgingScreen,"#collect/climate":climateScreen,"#collect/references":referencesScreen};
const collectionActions={"collect-beaches":"south-walton-beaches","collect-weather":"nws-weather","collect-restaurants":"south-walton-restaurants","collect-neighborhoods":"south-walton-neighborhoods","collect-lodging":LODGING_CONNECTOR,
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

function navigation() {
  const groups = {0:"VERİ MERKEZİ", 3:"İÇERİK ATÖLYESİ", 7:"ÜRETİM & YAYIN"};
  $("#navigation").innerHTML = state.data.steps.map((step,index) => `${groups[index] ? `<div class="group-label">${groups[index]}</div>` : ""}
    <a href="#${step.id}" class="${state.page === step.id ? "active" : ""}" ${state.page === step.id ? 'aria-current="page"' : ""}>
    <span class="step-no">${String(index+1).padStart(2,"0")}</span><span><span class="nav-title">${esc(step.title)}</span><span class="nav-sub" style="display:block">${step.state === "planned" ? "Planlanan aşama" : esc(step.subtitle)}</span></span></a>`).join("");
}

function pageHeading(title, description, actions="") {
  return `<div class="breadcrumb">30A STUDIO <span>/</span> ÇALIŞMA ALANI <span>/ ${esc(title.toLocaleUpperCase("tr"))}</span></div>
    <div class="page-heading"><div><h1>${esc(title)}</h1><p>${esc(description)}</p></div>${actions ? `<div class="heading-actions">${actions}</div>` : ""}</div>`;
}

function render() {
  if (!state.data) return;
  state.page = location.hash.slice(1).split("/")[0] || "sources";
  if (![...state.data.steps.map(step=>step.id),"settings"].includes(state.page)) state.page="sources";
  navigation();
  beachScreen.invalidate();
  weatherScreen.invalidate();
  restaurantScreen.invalidate();
  neighborhoodScreen.invalidate();
  lodgingScreen.invalidate();
  climateScreen.invalidate();
  referencesScreen.invalidate();
  const title = state.data.steps.find(step=>step.id===state.page)?.title || "Çalışma alanı bilgisi";
  document.title = `30A Studio · ${title}`;
  if (state.page === "sources") renderSources();
  else if (state.page === "collect") (collectionScreens[location.hash] || beachScreen).render($("#main"),state.data,pageHeading);
  else if (state.page === "quality") renderQuality();
  else if (state.page === "settings") renderSettings();
  else renderPlanned();
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

function renderPlanned() {
  const step = state.data.steps.find(step=>step.id===state.page);
  const plan = roadmap[state.page];
  $("#main").innerHTML = `<div class="planned-layout">${pageHeading(step.title, "Bu aşama geliştirme planında. Kaynak kütüphanesi ile plaj, hava, restoran ve mahalle verisi toplama kullanılabilir.")}
    <section class="planned-hero"><span class="tag warm">Planlanan aşama · Henüz bağlı değil</span><h2>${esc(plan.headline)}</h2><p>${esc(plan.description)}</p><a class="return-link" href="#sources">← Kaynak kütüphanesine dön</a></section>
    <div class="planned-grid">${plan.cards.map(([label,title,description])=>`<section class="planned-card"><span class="eyebrow">${esc(label)}</span><h3>${esc(title)}</h3><p>${esc(description)}</p></section>`).join("")}</div></div>`;
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
  $("#main").innerHTML = pageHeading("Çalışma alanı bilgisi", "30A Studio’nun sürümü ve kayıt konumu.") +
    `<div class="info-grid"><section class="info-card"><span class="eyebrow">BU BİLGİSAYARDA</span><h2 style="margin-top:12px">Destinasyonların kayıt alanı</h2><p>Kaynaklar, düzenleme geçmişi ve iş sonuçları aşağıdaki klasörde saklanır.</p><div class="path">${esc(state.data.data_path)}</div><p style="margin-top:15px">Uygulamayı kapatıp açınca kayıtların korunur. Yedek almak için uygulamayı kapattıktan sonra bu klasörün tamamını kopyalayabilirsin.</p></section>
    <section class="info-card"><span class="eyebrow">SÜRÜM ${esc(state.data.version)}</span><h2 style="margin-top:12px">Plaj, hava, restoran ve mahalle verisi hazır</h2><p>Kaynak kütüphanesi, gerçek plaj, restoran, mahalle ve NWS hava verisi toplama, filtreleme, CSV dışa aktarma, önceki sürümler ve iş geçmişi kullanılabilir. Plaj erişimleri, gözden geçirilebilir bir eşleme dosyasıyla mahallelere bağlanır.</p><span class="tag warm">Sonraki aşama</span><p style="margin-top:12px">Diğer kaynaklar ve genişletilmiş veri kontrolü. Bölge ve işletme kimliği tabloları hazır; otomatik eşleştirme, mahalle sınırları ve zamanlayıcı henüz yok. İçerik, görsel ve video üretimi aşamalı olarak eklenecek.</p><a href="#collect" class="return-link">Toplanan verileri gör →</a></section></div>`;
}

function renderJobResultLink(job) {
  const target=jobResultTarget(job,state.data.beach_connector.name);
  return target?`<a href="${target.href}" class="return-link" data-view-report>${target.label} →</a>`:"";
}

function renderJobs() {
  const jobs = state.data.jobs;
  $("#jobs-count").textContent = jobs.filter(active).length;
  $("#jobs-content").innerHTML = jobs.length ? jobs.map(job=>`<article class="job"><div class="job-meta"><span class="tag ${job.status==="done"?"green":"warm"}">${esc(statusLabels[job.status] || job.status)}</span><time>${esc(date(job.created_at))}</time></div><h3>${esc(job.title)}</h3>${job.source_name?`<p>Kaynak: ${esc(job.source_name)}</p>`:""}<progress max="100" value="${job.progress}" aria-label="İş ilerlemesi"></progress><p>${esc(job.message)}</p>${active(job)?`<button class="quiet" data-cancel-job="${job.id}">İptal et</button>`:""}<details><summary>İş günlüğü (${job.log.length})</summary>${job.log.map(entry=>`<div class="log-line"><time>${esc(date(entry.at))}</time>${esc(entry.text)}</div>`).join("")}</details>${renderJobResultLink(job)}</article>`).join("") :
    '<div class="empty"><div class="empty-icon">⌁</div><h3>Henüz iş yok</h3><p>Kaynak ekranında “Kayıtları kontrol et” düğmesine bastığında işin durumu ve sonucu burada görünür.</p></div>';
  updateAuditButtons();
}

function updateAuditButtons() {
  updateWeatherButton();
  const restaurantSource=state.data.sources.find(s=>s.enabled && s.connector?.name==="south-walton-restaurants");
  const restaurantBusy=state.data.jobs.some(j=>j.source_id===restaurantSource?.id && active(j));
  document.querySelectorAll('[data-action="collect-restaurants"]').forEach(button=>{button.disabled=!restaurantSource || restaurantBusy;button.textContent=restaurantBusy?"Toplama sürüyor…":"↓ Restoran verilerini topla";});
  const lodgingSource=state.data.sources.find(s=>s.enabled && s.connector?.name===LODGING_CONNECTOR);
  const lodgingBusy=state.data.jobs.some(j=>j.source_id===lodgingSource?.id && active(j));
  document.querySelectorAll('[data-action="collect-lodging"]').forEach(button=>{button.disabled=!lodgingSource || lodgingBusy;button.textContent=lodgingBusy?"Toplama sürüyor…":"↓ Konaklama aramalarını topla";});
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
      case "collect-lodging":
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
  resetDestinationState(state,[beachScreen,weatherScreen,restaurantScreen,neighborhoodScreen,lodgingScreen,climateScreen,referencesScreen]);
  lastCollectionId=lastWeatherId=lastRestaurantId=lastNeighborhoodId=lastLodgingId=null;climateDoneIds=new Set();
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
    climateDoneIds=new Set(climateDone(state.data.jobs));
    $("#app-version").textContent=`v${state.data.version}`;
    render();renderJobs();
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
      const restaurantLatest=state.data.jobs.find(j=>j.kind==="source_collection" && j.status==="done" && j.result?.connector_name==="south-walton-restaurants");
      if(restaurantLatest && restaurantLatest.id!==lastRestaurantId) {
        try {
          state.data.restaurant_runs=await api("restaurant-runs");lastRestaurantId=restaurantLatest.id;restaurantScreen.selectedRun=null;
          if(location.hash==="#collect/restaurants") render();
          toast("Restoran verileri kaydedildi. Restoranlar sekmesinden inceleyebilirsin.");
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
      const lodgingLatest=state.data.jobs.find(j=>j.kind==="source_collection" && j.status==="done" && j.result?.connector_name===LODGING_CONNECTOR);
      if(lodgingLatest && lodgingLatest.id!==lastLodgingId) {
        try {
          state.data.lodging_runs=await api("lodging-runs");lastLodgingId=lodgingLatest.id;lodgingScreen.selectedRun=null;lodgingScreen.snapshot=null;
          if(location.hash==="#collect/lodging") render();
          toast("Konaklama verileri kaydedildi. Konaklama sekmesinden inceleyebilirsin.");
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
start();
