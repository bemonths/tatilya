import {esc} from "./api.js";

// GÖREV-17 (Adım 3): the layout of the Settings screen, after Housing Atlas (atlas/web/js/screens/settings.js: SECTIONS, sectionNav).
// A row of section buttons under the heading; a button takes the page straight to its section and the address names the section
// (#settings/tonlar), so links on other screens ("Tonları yönet", the proxy notes, the extension warnings) open the section itself.
// Every section is a card with its own title and icon. Only the layout lives here: each section's content, its save, trial and
// version buttons are drawn by its own module exactly as before, and no setting's value is touched.

/** slug: the address part; main: the selector of the section's main button (or, where it has none, its main line). */
export const SECTIONS=Object.freeze([
  {slug:"klasor", title:"Kayıt klasörü", icon:"▤", main:".path"},
  {slug:"claude", title:"Claude", icon:"✦", main:"#claude-form button[type=submit]"},
  {slug:"baslik-eki", title:"Başlık eki", icon:"✎", main:"#suffix-form button[type=submit]"},
  {slug:"kullanim", title:"Claude kullanımı", icon:"◔", main:".usage-settings-text"},
  {slug:"talimatlar", title:"Talimatlar", icon:"☰", main:"#instruction-save"},
  {slug:"tonlar", title:"Tonlar", icon:"♪", main:"#tone-form button[type=submit]"},
  {slug:"uyari-ifadeleri", title:"Uyarı ifadeleri", icon:"⚑", main:"#warnings-save"},
  {slug:"eklenti", title:"Tarayıcı eklentisi", icon:"▣", main:"#extension-trial"},
  {slug:"proxy", title:"ABD proxy'si", icon:"⇄", main:"#proxy-form button[type=submit]"},
  {slug:"hakkinda", title:"Hakkında", icon:"ⓘ", main:".about-version"},
].map(Object.freeze));

const ROUTES=["settings","ayarlar"];       // "#ayarlar/tonlar" opens the same section as "#settings/tonlar"

export function isSettingsHash(hash) {
  return ROUTES.includes(String(hash || "").replace(/^#/,"").split("/")[0]);
}

/** "#settings/tonlar" → "tonlar"; null for the Settings screen itself, another screen or an unknown section. */
export function sectionOfHash(hash) {
  const [page,slug]=String(hash || "").replace(/^#/,"").split("/");
  if(!ROUTES.includes(page) || !slug) return null;
  return SECTIONS.some(section=>section.slug===slug)?slug:null;
}

export const sectionId=slug=>`ayar-${slug}`;
export const settingsHref=slug=>`#settings/${slug}`;

/** A link from another screen straight to a Settings section. */
export function settingsLink(slug, text) {
  return `<a href="${settingsHref(slug)}">${esc(text)}</a>`;
}

/** The section buttons under the heading; the section named by the address is marked. */
export function settingsNav(current=null) {
  return `<nav class="section-nav" id="settings-nav-bar" aria-label="Ayar bölümleri">${SECTIONS.map(section=>
    `<a class="section-nav-item ${section.slug===current?"active":""}" href="${settingsHref(section.slug)}" data-settings-section="${section.slug}" ${section.slug===current?'aria-current="true"':""}><span aria-hidden="true">${section.icon}</span> ${esc(section.title)}</a>`).join("")}</nav>`;
}

/** One section: an anchor the buttons scroll to, the section's icon for its card title, and the slot its own module draws into. */
export function sectionCard(slug, inner) {
  const section=SECTIONS.find(item=>item.slug===slug);
  return `<section class="settings-section" id="${sectionId(slug)}" data-section="${slug}" aria-label="${esc(section.title)}" style="--section-icon:'${section.icon}'">${inner}</section>`;
}

export function folderCard(dataPath) {
  return `<div class="info-card"><span class="eyebrow">BU BİLGİSAYARDA</span><h2 style="margin-top:12px">Destinasyonların kayıt alanı</h2><p>Kaynaklar, düzenleme geçmişi ve iş sonuçları aşağıdaki klasörde saklanır.</p><div class="path">${esc(dataPath)}</div><p style="margin-top:15px">Uygulamayı kapatıp açınca kayıtların korunur. Yedek almak için uygulamayı kapattıktan sonra bu klasörün tamamını kopyalayabilirsin.</p></div>`;
}

export function aboutCard(version) {
  return `<div class="info-card"><span class="eyebrow about-version">SÜRÜM ${esc(version)}</span><h2 style="margin-top:12px">Veri, kanıt paketi ve konu önerisi hazır</h2><p>Kaynak kütüphanesi, plaj, hava, restoran, mahalle, iklim, konaklama ve günlük ihtiyaç verisi toplama; kanıt paketi ve yazar özeti; Videolar ekranında Claude ile konu ve başlık önerisi ve video kaydı kullanılabilir.</p><span class="tag warm">Sonraki aşama</span><p style="margin-top:12px">Claude ile video metni ve metnin kontrolü. Görsel plan, video üretimi ve yayın hazırlığı aşamalı olarak eklenecek.</p><a href="#collect" class="return-link">Toplanan verileri gör →</a></div>`;
}

export function usageCard(view) {
  if(!view) return '<div class="info-card"><span class="eyebrow">CLAUDE KULLANIMI</span><h2 style="margin-top:12px">Kullanım paneli</h2><p class="muted usage-settings-text">Yükleniyor…</p></div>';
  const effort=view.refresh.effort==="low"?"düşük":esc(view.refresh.effort);
  return `<div class="info-card"><span class="eyebrow">CLAUDE KULLANIMI</span><h2 style="margin-top:12px">Kullanım paneli</h2><p class="usage-settings-text">${esc(view.refresh.text)}</p><p class="muted">Model: <code>${esc(view.refresh.model)}</code> · efor: ${effort}</p></div>`;
}

/** The whole screen's frame: heading text, the buttons and one empty slot per section, in the order of SECTIONS. */
export function settingsFrame(dataPath, version, current=null) {
  const slot=(slug,id,text)=>sectionCard(slug,`<div class="settings-slot" id="${id}"><p class="muted">${esc(text)}</p></div>`);
  return `<div id="settings-screen">${settingsNav(current)}
    ${sectionCard("klasor",folderCard(dataPath))}
    ${slot("claude","claude-settings-slot","Claude ayarları yükleniyor…")}
    ${slot("baslik-eki","suffix-settings-slot","Başlık eki yükleniyor…")}
    ${sectionCard("kullanim",`<div class="settings-slot" id="usage-settings-slot">${usageCard(null)}</div>`)}
    ${slot("talimatlar","instructions-slot","Talimatlar yükleniyor…")}
    ${slot("tonlar","tones-slot","Tonlar yükleniyor…")}
    ${slot("uyari-ifadeleri","warnings-slot","Uyarı ifadeleri yükleniyor…")}
    ${slot("eklenti","extension-slot","Tarayıcı eklentisi yükleniyor…")}
    ${slot("proxy","proxy-slot","ABD proxy'si yükleniyor…")}
    ${sectionCard("hakkinda",aboutCard(version))}</div>`;
}

export const SETTINGS_INTRO="30A Studio’nun ayarları. Aşağıdaki düğmelerden birine basınca sayfa o bölüme gider.";

const MENTION_SLUGS={"Claude":"claude","Tarayıcı eklentisi":"eklenti","Tonlar":"tonlar","Talimatlar":"talimatlar"};

/** Turns "Ayarlar → Claude", "Ayarlar → Tarayıcı eklentisi" … and the proxy note's "(Ayarlar)" inside an already escaped text into
 *  links to that section, so a warning on another screen or in the job panel opens the section itself. */
export function linkSettingsMentions(escaped) {
  return String(escaped ?? "")
    .replace(/Ayarlar → (Claude|Tarayıcı eklentisi|Tonlar|Talimatlar)/g,(whole,name)=>`<a href="${settingsHref(MENTION_SLUGS[name])}">${whole}</a>`)
    .replace(/Ayarlar → ABD proxy(&#39;|&#x27;|'|’)si/g,whole=>`<a href="${settingsHref("proxy")}">${whole}</a>`)
    .replace(/tanımlı değil \(Ayarlar\)/g,`tanımlı değil (<a href="${settingsHref("proxy")}">Ayarlar → ABD proxy'si</a>)`);
}