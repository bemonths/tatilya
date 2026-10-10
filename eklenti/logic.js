// 30A Studio Yardımcısı — saf mantık (DOM ve chrome.* kullanmaz; Node testleri bu dosyayı doğrudan sınar).
//
// Eklenti yalnız programın istediği adresleri, kendi açtığı pencerede açar ve sayfanın içeriğini programa verir. Tıklamaz, yazı yazmaz,
// form doldurmaz; giriş ve ödeme sayfalarını okumadan atlar. Doğrulama sayfasında kullanıcıyı bekler (en çok 15 dk).

export const PROGRAM_ID = "thirtya-studio";
export const PORTS = Array.from({length: 20}, (_, i) => 8830 + i);      // 8830–8849 (Housing Atlas 8790–8809 kullanır)
export const ASK_EVERY_MS = 3000;
export const DEFAULT_GAP_S = 8;
export const VERIFY_WAIT_S = 15 * 60;
export const MAX_WAIT_S = 60;

// Doğrulama ve engel sayfası işaretleri: programın studio/sources/browser_verification.py dosyasındaki CHALLENGE ve BLOCKED ile aynıdır
// (bir Python testi bu iki metnin aynı kaldığını denetler).
export const CHALLENGE_SOURCE = String.raw`<title>\s*Just a moment\.\.\.|cf_chl_opt|/cdn-cgi/challenge-platform/h/[a-z]/orchestrate/|Checking your browser before|Checking if the site connection is secure|px-captcha|Press &amp; Hold|Press & Hold`;
export const BLOCKED_SOURCE = String.raw`Sorry, you have been blocked|You are unable to access`;
const CHALLENGE = new RegExp(CHALLENGE_SOURCE, "i");
const BLOCKED = new RegExp(BLOCKED_SOURCE, "i");
const CHALLENGE_TITLES = /^(just a moment|attention required|access denied|verify you are human|bir dakika)/i;

const LOGIN_PATH = /\/(log-?in|sign-?in|signin|account\/login|auth\/login|oturum-ac|giris)(\/|$|\?|\.)/i;
const LOGIN_TITLE = /^(sign in|log in|login|giriş yap|oturum aç)\b/i;
const PASSWORD_FIELD = /<input\b[^>]*\btype\s*=\s*["']?password\b/i;
const PAYMENT_PATH = /\/(checkout|payment|pay|odeme|cart\/checkout)(\/|$|\?)/i;
const CARD_FIELD = /autocomplete\s*=\s*["']?cc-(number|csc|exp)/i;

export function domainOf(url) {
  let host = "";
  try { host = new URL(url).hostname; } catch { host = String(url || ""); }
  host = host.toLowerCase().replace(/\.$/, "");
  return host.startsWith("www.") ? host.slice(4) : host;
}

/** The program's own local address: covered by the extension's one required host permission (http://127.0.0.1/*). */
export function isLocal(domain) {
  return ["127.0.0.1", "localhost"].includes(domainOf(domain));
}

/** The site's permission patterns: the domain and its subdomains, https and http (asked together, granted together). */
export function originPatterns(domain) {
  const d = domainOf(domain);
  return [`https://${d}/*`, `https://*.${d}/*`, `http://${d}/*`, `http://*.${d}/*`];
}

/** Is a domain covered by the granted origin patterns ("https://*.example.com/*")? */
export function isPermitted(domain, origins) {
  const d = domainOf(domain);
  return (origins || []).some(pattern => {
    const match = /^(\*|https?):\/\/(\*\.)?([^/:]+)/i.exec(pattern);
    if (!match) return false;
    const host = match[3].toLowerCase();
    if (host === "127.0.0.1" || host === "localhost") return d === host;
    return d === host || (Boolean(match[2]) && d.endsWith("." + host)) || d === domainOf(host);
  });
}

/** The granted site domains for the program (the local program's own 127.0.0.1 permission is left out). */
export function permittedDomains(origins) {
  const found = new Set();
  for (const pattern of origins || []) {
    const match = /^(?:\*|https?):\/\/(?:\*\.)?([^/:]+)/i.exec(pattern);
    if (match && !["127.0.0.1", "localhost"].includes(match[1].toLowerCase())) found.add(domainOf(match[1]));
  }
  return [...found].sort();
}

export function healthOk(body) {
  return Boolean(body) && body.app === PROGRAM_ID;
}

/** Ports to try: the remembered one first, then the program's range. */
export function portOrder(remembered) {
  const first = Number.isInteger(remembered) ? [remembered] : [];
  return [...first, ...PORTS.filter(p => p !== remembered)];
}

export function isVerification(html, title = "") {
  const head = String(html || "").slice(0, 40000);
  return CHALLENGE.test(head) || CHALLENGE_TITLES.test(String(title || "").trim());
}

export function isBlocked(html) {
  return BLOCKED.test(String(html || "").slice(0, 40000));
}

/** A page that asks the visitor to sign in: a password field, or a sign-in address or title. Such a page is not read. */
export function isLogin({html = "", url = "", title = ""} = {}) {
  let path = "";
  try { path = new URL(url).pathname; } catch { path = ""; }
  return PASSWORD_FIELD.test(String(html).slice(0, 200000)) || LOGIN_PATH.test(path) || LOGIN_TITLE.test(String(title).trim());
}

/** A payment page: a checkout address or a card number field. Such a page is not read. */
export function isPayment({html = "", url = ""} = {}) {
  let path = "";
  try { path = new URL(url).pathname; } catch { path = ""; }
  return PAYMENT_PATH.test(path) || CARD_FIELD.test(String(html).slice(0, 200000));
}

/** The wait rule of a page: at least `saniye` seconds after loading, or until the element `oge` is on the page (at most MAX_WAIT_S). */
export function normalizeWait(wait) {
  const seconds = Number(wait?.saniye);
  const selector = typeof wait?.oge === "string" && wait.oge.trim() ? wait.oge.trim().slice(0, 200) : null;
  return {seconds: Number.isFinite(seconds) ? Math.max(0, Math.min(MAX_WAIT_S, seconds)) : (selector ? 0 : 2), selector, maxSeconds: MAX_WAIT_S};
}

/** At least `gap` seconds between two page loads on the same domain; one page at a time (the caller waits for each page). */
export class Pacer {
  constructor(gapSeconds = DEFAULT_GAP_S) {
    this.gapMs = Math.max(0, Number(gapSeconds) || DEFAULT_GAP_S) * 1000;
    this.last = new Map();
  }
  delayFor(domain, now = Date.now()) {
    const last = this.last.get(domainOf(domain));
    return last === undefined ? 0 : Math.max(0, last + this.gapMs - now);
  }
  mark(domain, now = Date.now()) {
    this.last.set(domainOf(domain), now);
  }
}

/** The extension's own queue of jobs from the program: first come, first served; a job already queued or done is not taken twice. */
export class JobQueue {
  constructor() { this.items = []; this.seen = new Set(); }
  add(job) {
    if (!job || !job.id || this.seen.has(job.id)) return false;
    this.seen.add(job.id);
    this.items.push(job);
    return true;
  }
  take() { return this.items.shift() || null; }
  get size() { return this.items.length; }
  forget(id) { this.seen.delete(id); }     // the program may hand the same job again (after the service worker was stopped)
}

/** What is sent to the program for one page. */
export function pageResult(state, page = {}, note = null) {
  const result = {durum: state, son_adres: page.url || null, baslik: page.title || "", http_durumu: page.status ?? null, not: note};
  if (state === "tamam" || state === "dogrulama") result.html = page.html ?? null;
  return result;
}

/** The decision for a page that has loaded (before its wait rule): verification, block, login, payment or read it. */
export function classify(page) {
  if (isVerification(page.html, page.title)) return "dogrulama";
  if (isLogin(page)) return "giris";
  if (isPayment(page)) return "odeme";
  return "oku";
}

export function bytesToBase64(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(binary);
}
