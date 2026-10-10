// 30A Studio Yardımcısı — arka plan (Manifest V3 service worker).
//
// Ne yapar: bilgisayardaki 30A Studio programını 127.0.0.1 üzerinde 8830–8849 aralığında bulur, birkaç saniyede bir iş sorar; bir iş
// gelirse kendi açtığı ayrı ve öne gelmeyen bir pencerede programın verdiği adresleri teker teker açar, sayfanın işlenmiş hâlini
// (outerHTML, son adres, başlık, HTTP durumu) programa verir, sekmeyi ve pencereyi kapatır. Kullanıcının sekmelerine dokunmaz.
// Ne yapmaz: tıklamaz, yazı yazmaz, form doldurmaz, çerez/geçmiş/yer imi/indirme okumaz, CDP (debugger) kullanmaz. İzin verilmemiş bir
// siteye gitmez; giriş ve ödeme sayfalarını okumadan atlar. Doğrulama sayfasında pencereyi öne getirir, bildirim gösterir ve kullanıcıyı
// en çok 15 dk bekler; geçilmezse sayfayı atlar.

import * as L from "./logic.js";

const VERSION = chrome.runtime.getManifest().version;
const LOOP_MS = 25000;            // a wake-up asks for work this long (the alarm wakes the worker every 30 s)
const LOAD_TIMEOUT_MS = 60000;
let looping = false;

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

chrome.runtime.onInstalled.addListener(start);
chrome.runtime.onStartup.addListener(start);
chrome.alarms.onAlarm.addListener(alarm => { if (alarm.name === "sor") loop(); });
chrome.permissions.onAdded.addListener(() => loop());

function start() {
  chrome.alarms.create("sor", {periodInMinutes: 0.5});
  loop();
}

async function settings() {
  return chrome.storage.local.get(["kod", "port", "durum"]);
}

async function note(state) {
  await chrome.storage.local.set({durum: {...state, zaman: Date.now()}});
}

async function call(port, path, body, code) {
  const response = await fetch(`http://127.0.0.1:${port}${path}`, {
    method: "POST", headers: {"Content-Type": "application/json", "X-Studio-Eklenti": code || ""}, body: JSON.stringify(body || {}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Program ${response.status} döndü.`);
  return data;
}

/** The program's port: the remembered one first, then 8830–8849 (`/api/health` says app "thirtya-studio"). */
async function findProgram(remembered) {
  for (const port of L.portOrder(remembered)) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/health`, {signal: AbortSignal.timeout(800)});
      if (response.ok && L.healthOk(await response.json())) {
        if (port !== remembered) await chrome.storage.local.set({port});
        return port;
      }
    } catch { /* not this port */ }
  }
  return null;
}

async function grantedOrigins() {
  const all = await chrome.permissions.getAll();
  return all.origins || [];
}

async function permitted(domain) {
  if (L.isLocal(domain)) return true;          // the program's own pages (the trial page) are under the required 127.0.0.1 permission
  return chrome.permissions.contains({origins: L.originPatterns(domain)});
}

async function loop() {
  if (looping) return;
  looping = true;
  try {
    const end = Date.now() + LOOP_MS;
    while (Date.now() < end) {
      const worked = await askOnce().catch(async error => { await note({program: "hata", mesaj: String(error.message || error)}); return false; });
      if (!worked) await sleep(L.ASK_EVERY_MS);
    }
  } finally {
    looping = false;
  }
}

async function askOnce() {
  const {kod, port: remembered} = await settings();
  if (!kod) { await note({program: "eslesmedi"}); return false; }
  const port = await findProgram(remembered);
  if (!port) { await note({program: "bulunamadi"}); return false; }
  const origins = await grantedOrigins();
  const answer = await call(port, "/api/eklenti/sor", {surum: VERSION, izinli: L.permittedDomains(origins)}, kod);
  await chrome.storage.local.set({izinBekleyen: answer.izin_bekleyen || []});
  await note({program: "bagli", port});
  if (!answer.is) return false;
  await runJob(port, kod, answer.is);
  return true;
}

async function runJob(port, kod, job) {
  if (!(await permitted(job.alan_adi))) {
    await call(port, `/api/eklenti/is/${job.id}/durum`, {izin_yok: job.alan_adi}, kod);
    return;
  }
  await chrome.storage.local.set({sonIs: {alan_adi: job.alan_adi, amac: job.amac, durum: "çalışıyor", zaman: Date.now()}});
  const pacer = new L.Pacer(job.aralik_saniye);
  const win = await chrome.windows.create({url: "about:blank", focused: false, type: "normal", width: 1280, height: 900});
  const tabId = win.tabs[0].id;
  let failure = null;
  try {
    for (;;) {
      const next = await call(port, `/api/eklenti/is/${job.id}/sonraki`, {}, kod);
      if (next.bitti) break;
      if (next.bekle) { await sleep(1000); continue; }
      const item = next.oge;
      let result;
      try {
        result = item.tur === "istek" ? await doRequest(tabId, item, pacer) : await doPage(port, kod, win.id, tabId, item, pacer, job);
      } catch (error) {
        result = {durum: "hata", not: String(error?.message || error).slice(0, 300)};
      }
      await call(port, `/api/eklenti/is/${job.id}/sonuc`, {oge_id: item.id, ...result}, kod);
    }
  } catch (error) {
    failure = String(error?.message || error).slice(0, 300);
  } finally {
    await chrome.windows.remove(win.id).catch(() => {});
  }
  await call(port, `/api/eklenti/is/${job.id}/bitti`, failure ? {hata: failure} : {}, kod).catch(() => {});
  await chrome.storage.local.set({sonIs: {alan_adi: job.alan_adi, amac: job.amac, durum: failure ? "hata" : "bitti", zaman: Date.now()}});
}

/** Open an address in the extension's own tab and wait until it has loaded. */
async function navigate(tabId, url) {
  await chrome.tabs.update(tabId, {url});
  const deadline = Date.now() + LOAD_TIMEOUT_MS;
  await sleep(300);
  while (Date.now() < deadline) {
    const tab = await chrome.tabs.get(tabId);
    if (tab.status === "complete" && tab.url && tab.url !== "about:blank") return;
    await sleep(300);
  }
}

/** The page as the browser shows it now (read from the extension's own tab only). */
async function readPage(tabId) {
  const [{result}] = await chrome.scripting.executeScript({target: {tabId}, func: () => {
    const nav = performance.getEntriesByType("navigation")[0];
    return {html: document.documentElement.outerHTML, url: location.href, title: document.title, status: (nav && nav.responseStatus) || null};
  }});
  return result;
}

async function applyWait(tabId, wait) {
  const rule = L.normalizeWait(wait);
  if (rule.selector) {
    const deadline = Date.now() + rule.maxSeconds * 1000;
    while (Date.now() < deadline) {
      const [{result}] = await chrome.scripting.executeScript({target: {tabId}, func: selector => Boolean(document.querySelector(selector)),
                                                              args: [rule.selector]});
      if (result) break;
      await sleep(500);
    }
  }
  if (rule.seconds) await sleep(rule.seconds * 1000);
}

async function pace(pacer, url) {
  const domain = L.domainOf(url);
  const delay = pacer.delayFor(domain);
  if (delay) await sleep(delay);
  pacer.mark(domain);
}

async function doPage(port, kod, windowId, tabId, item, pacer, job) {
  const domain = L.domainOf(item.adres);
  if (!(await permitted(domain))) return L.pageResult("izin_yok", {url: item.adres}, `${domain} için izin yok.`);
  await pace(pacer, item.adres);
  await navigate(tabId, item.adres);
  let page = await readPage(tabId);
  if (L.classify(page) === "dogrulama") {
    await call(port, `/api/eklenti/is/${job.id}/durum`, {dogrulama: page.url || item.adres}, kod).catch(() => {});
    await chrome.windows.update(windowId, {focused: true, state: "normal"}).catch(() => {});
    chrome.notifications.create({type: "basic", iconUrl: "icons/128.png", title: "30A Studio: doğrulama bekleniyor",
      message: `${domain} sayfasında doğrulamayı siz tamamlayın; eklenti bekliyor (en çok ${Math.round((job.dogrulama_bekleme_saniye || L.VERIFY_WAIT_S) / 60)} dk).`});
    const deadline = Date.now() + (job.dogrulama_bekleme_saniye || L.VERIFY_WAIT_S) * 1000;
    while (Date.now() < deadline && L.isVerification(page.html, page.title)) {
      await sleep(3000);
      page = await readPage(tabId).catch(() => page);
    }
    if (L.isVerification(page.html, page.title)) {
      return L.pageResult("dogrulama", page, "Doğrulama süresinde tamamlanmadı; sayfa atlandı.");
    }
  }
  const kind = L.classify(page);
  if (kind === "giris") return L.pageResult("giris", page, "Sayfa giriş istiyor; okunmadı (giriş gerekiyor).");
  if (kind === "odeme") return L.pageResult("odeme", page, "Ödeme sayfası; okunmadı.");
  await applyWait(tabId, item.bekle);
  page = await readPage(tabId);
  return L.pageResult(L.isVerification(page.html, page.title) ? "dogrulama" : "tamam", page);
}

/** A request with the page's own fetch from the extension's tab on that site (the tab is first opened on the site if it is elsewhere). */
async function doRequest(tabId, item, pacer) {
  const target = new URL(item.adres);
  if (!(await permitted(L.domainOf(target.href)))) return {durum: "izin_yok", not: `${target.hostname} için izin yok.`};
  const tab = await chrome.tabs.get(tabId);
  let here = null;
  try { here = new URL(tab.url).origin; } catch { here = null; }
  if (here !== target.origin) {
    await pace(pacer, target.origin);
    await navigate(tabId, target.origin + "/");
  }
  const [{result}] = await chrome.scripting.executeScript({target: {tabId}, world: "MAIN", args: [item.adres, item.yontem || "GET", item.basliklar || {}, item.govde ?? null],
    func: async (url, method, headers, body) => {
      const response = await fetch(url, {method, headers, body: body === null ? undefined : body, credentials: "include", redirect: "follow"});
      const bytes = new Uint8Array(await response.arrayBuffer());
      let binary = "";
      for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
      return {status: response.status, url: response.url, headers: Object.fromEntries(response.headers.entries()), body: btoa(binary)};
    }});
  return {durum: "tamam", http_durumu: result.status, son_adres: result.url, basliklar: result.headers, govde_base64: result.body};
}

// The popup asks the worker to pair (the code is checked by the program) and to look for work now.
chrome.runtime.onMessage.addListener((message, sender, reply) => {
  if (sender.id !== chrome.runtime.id) return false;
  if (message?.tur === "eslestir") {
    (async () => {
      const code = String(message.kod || "").trim().toUpperCase();
      const {port: remembered} = await settings();
      const port = await findProgram(remembered);
      if (!port) return reply({ok: false, mesaj: "30A Studio programı bulunamadı. Program açık mı?"});
      try {
        await call(port, "/api/eklenti/eslestir", {surum: VERSION}, code);
        await chrome.storage.local.set({kod: code, port});
        await note({program: "bagli", port});
        loop();
        reply({ok: true, port});
      } catch (error) {
        reply({ok: false, mesaj: String(error.message || error)});
      }
    })();
    return true;
  }
  if (message?.tur === "sor") { loop(); reply({ok: true}); return false; }
  return false;
});

start();
