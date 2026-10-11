// 30A Studio Yardımcısı — arka plan (Manifest V3 service worker).
//
// Ne yapar: bilgisayardaki 30A Studio programını 127.0.0.1 üzerinde 8830–8849 aralığında bulur, birkaç saniyede bir iş sorar; bir iş
// gelirse kendi açtığı ayrı ve öne gelmeyen bir pencerede programın verdiği adresleri teker teker açar, sayfanın işlenmiş hâlini
// (outerHTML, son adres, başlık, HTTP durumu) programa verir, sekmeyi ve pencereyi kapatır. Kullanıcının sekmelerine dokunmaz.
// İş sürerken programa en çok 5 sn arayla ne yaptığını bildirir (sayfa açılıyor, sayfa okunuyor, doğrulama bekleniyor, bekleme).
// Ne yapmaz: tıklamaz, yazı yazmaz, form doldurmaz, çerez/geçmiş/yer imi/indirme okumaz, CDP (debugger) kullanmaz, proxy kullanmaz ve
// Chrome'un proxy ayarına dokunmaz. İzin verilmemiş bir siteye gitmez; giriş ve ödeme sayfalarını okumadan atlar. Doğrulama sayfasında
// pencereyi öne getirir, bildirim gösterir ve kullanıcıyı en çok 15 dk bekler (kullanıcı "Bu sayfayı atla" diyebilir); erişim reddedildi
// ve bölge engeli sayfalarında beklemez. İzin verilmemiş başka bir siteye yönlenen sayfa "başka siteye yönlendi" diye bildirilir.

import * as L from "./logic.js";

const VERSION = chrome.runtime.getManifest().version;
const LOOP_MS = 25000;            // a wake-up asks for work this long (the alarm wakes the worker every 30 s)
const LOAD_TIMEOUT_MS = 60000;
let looping = false;
let current = null;               // the job at hand: {port, kod, jobId, job, stage: {asama, adres, bitis}, skip}

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

/** Every few seconds while a job runs: alive, and what is being done. The answer may ask to skip the page ("Bu sayfayı atla"). */
async function report() {
  const job = current;
  if (!job) return;
  const stage = job.stage || {};
  const left = Number.isFinite(stage.bitis) ? Math.max(0, Math.round((stage.bitis - Date.now()) / 1000)) : null;
  try {
    const answer = await call(job.port, `/api/eklenti/is/${job.jobId}/durum`, {asama: {asama: stage.asama, adres: stage.adres || null, kalan_s: left}}, job.kod);
    if (answer.atla) job.skip = true;
  } catch { /* the program may be busy; the next report follows */ }
  await chrome.storage.local.set({canli: Date.now()}).catch(() => {});     // an extension call: the worker stays awake during the job
}

async function setStage(asama, adres, extra = {}) {
  if (!current) return;
  current.stage = {asama, adres, ...extra};
  const job = current.job;
  await chrome.storage.local.set({sonIs: {alan_adi: job.alan_adi, amac: job.amac, durum: "çalışıyor", asama, adres, bitis: extra.bitis ?? null,
                                          zaman: current.started, ilerleme: Date.now()}});
  report();
}

async function runJob(port, kod, job) {
  if (!(await permitted(job.alan_adi))) {
    await call(port, `/api/eklenti/is/${job.id}/durum`, {izin_yok: job.alan_adi}, kod);
    return;
  }
  current = {port, kod, jobId: job.id, job, stage: {asama: "aciliyor", adres: null}, skip: false, started: Date.now()};
  await setStage("aciliyor", null);
  const timer = setInterval(report, L.REPORT_EVERY_MS);
  const pacer = new L.Pacer(job.aralik_saniye);
  let win = null;
  let failure = null;
  try {
    win = await chrome.windows.create({url: "about:blank", focused: false, type: "normal", width: 1280, height: 900});
    const tabId = win.tabs[0].id;
    for (;;) {
      const next = await call(port, `/api/eklenti/is/${job.id}/sonraki`, {}, kod);
      if (next.bitti) break;
      if (next.bekle) { await sleep(1000); continue; }
      const item = next.oge;
      current.skip = false;
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
    clearInterval(timer);
    if (win) await chrome.windows.remove(win.id).catch(() => {});
  }
  current = null;
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

/** The tab went on to a site the extension may not open (it cannot read that page): the result says where it went. */
async function elsewhere(tabId, domain) {
  const tab = await chrome.tabs.get(tabId).catch(() => null);
  const landed = tab?.url || "";
  const there = L.domainOf(landed);
  if (!landed || landed === "about:blank" || there === domain || await permitted(there)) return null;
  const kind = L.redirectKind(landed);
  const page = {url: landed, title: tab.title || "", status: null};
  return L.pageResult(kind, page, kind === "bolge_engeli" ? `bölge engeli: ${there} adresine yönlendi` : L.stopNote("yonlendi", page));
}

async function readOrElsewhere(tabId, domain) {
  try {
    return {page: await readPage(tabId)};
  } catch (error) {
    const moved = await elsewhere(tabId, domain);
    if (moved) return {moved};
    throw error;
  }
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
  if (delay) {
    await setStage("bekleme", url);
    await sleep(delay);
  }
  pacer.mark(domain);
}

async function doPage(port, kod, windowId, tabId, item, pacer, job) {
  const domain = L.domainOf(item.adres);
  if (!(await permitted(domain))) return L.pageResult("izin_yok", {url: item.adres}, `${domain} için izin yok.`);
  await pace(pacer, item.adres);
  await setStage("aciliyor", item.adres);
  await navigate(tabId, item.adres);
  const moved = await elsewhere(tabId, domain);
  if (moved) return moved;
  await setStage("okunuyor", item.adres);
  let read = await readOrElsewhere(tabId, domain);
  if (read.moved) return read.moved;
  let page = read.page;
  let kind = L.classify(page);
  if (kind === "dogrulama") {
    const waitMs = (job.dogrulama_bekleme_saniye || L.VERIFY_WAIT_S) * 1000;
    const deadline = Date.now() + waitMs;
    await call(port, `/api/eklenti/is/${job.id}/durum`, {dogrulama: page.url || item.adres}, kod).catch(() => {});
    await setStage("dogrulama", page.url || item.adres, {bitis: deadline});
    await chrome.windows.update(windowId, {focused: true, state: "normal"}).catch(() => {});
    chrome.notifications.create({type: "basic", iconUrl: "icons/128.png", title: "30A Studio: doğrulama bekleniyor",
      message: `${domain} sayfasında doğrulamayı siz tamamlayın ya da eklenti penceresinde “Bu sayfayı atla”ya basın (en çok ${Math.round(waitMs / 60000)} dk).`});
    while (Date.now() < deadline && kind === "dogrulama" && !current?.skip) {
      await sleep(3000);
      read = await readOrElsewhere(tabId, domain).catch(() => ({page}));
      if (read.moved) return read.moved;
      page = read.page;
      kind = L.classify(page);
    }
    if (current?.skip) {
      current.skip = false;
      return L.pageResult("atlandi", page, "Kullanıcı bu sayfayı atladı (doğrulama beklenirken).");
    }
    if (kind === "dogrulama") return L.pageResult("dogrulama", page, "Doğrulama süresinde tamamlanmadı; sayfa atlandı.");
    await setStage("okunuyor", page.url || item.adres);
  }
  if (kind === "erisim_reddedildi" || kind === "bolge_engeli") return L.pageResult(kind, page, L.stopNote(kind, page));
  if (kind === "giris") return L.pageResult("giris", page, "Sayfa giriş istiyor; okunmadı (giriş gerekiyor).");
  if (kind === "odeme") return L.pageResult("odeme", page, "Ödeme sayfası; okunmadı.");
  await applyWait(tabId, item.bekle);
  read = await readOrElsewhere(tabId, domain);
  if (read.moved) return read.moved;
  page = read.page;
  kind = L.pageKind(page.html, page.title, page.url, page.status);
  if (kind === "erisim_reddedildi" || kind === "bolge_engeli") return L.pageResult(kind, page, L.stopNote(kind, page));
  return L.pageResult(kind === "dogrulama" ? "dogrulama" : "tamam", page);
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
    await setStage("aciliyor", target.origin + "/");
    await navigate(tabId, target.origin + "/");
  }
  await setStage("okunuyor", item.adres);
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

// The popup asks the worker to pair (the code is checked by the program), to look for work now, or to skip the page waiting for
// verification ("Bu sayfayı atla").
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
  if (message?.tur === "atla") {
    const waiting = current && current.stage?.asama === "dogrulama";
    if (waiting) current.skip = true;
    reply({ok: Boolean(waiting)});
    return false;
  }
  return false;
});

start();
