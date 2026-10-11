// 30A Studio Yardımcısı — saf mantık (DOM ve chrome.* kullanmaz; Node testleri bu dosyayı doğrudan sınar).
//
// Eklenti yalnız programın istediği adresleri, kendi açtığı pencerede açar ve sayfanın içeriğini programa verir. Tıklamaz, yazı yazmaz,
// form doldurmaz; giriş ve ödeme sayfalarını okumadan atlar. Doğrulama sayfasında kullanıcıyı bekler (en çok 15 dk); kimsenin
// geçemeyeceği engelde (erişim reddedildi) ve ABD dışı erişim engelinde (bölge engeli) beklemez, hemen atlar (GÖREV-16).

export const PROGRAM_ID = "thirtya-studio";
export const PORTS = Array.from({length: 20}, (_, i) => 8830 + i);      // 8830–8849 (Housing Atlas 8790–8809 kullanır)
export const ASK_EVERY_MS = 3000;
export const REPORT_EVERY_MS = 4000;     // iş sürerken programa en çok 5 sn arayla canlılık ve durum bildirilir
export const STUCK_AFTER_MS = 3 * 60 * 1000;
export const DEFAULT_GAP_S = 8;
export const VERIFY_WAIT_S = 15 * 60;
export const MAX_WAIT_S = 60;

// Sayfa türü işaretleri: programın studio/sources/page_kinds.py dosyasındakilerle aynıdır (bir Python testi bu metinlerin ve
// sayıların aynı kaldığını, iki taraf aynı fikstürlerde aynı sonucu verdiğini denetler).
export const CHALLENGE_SOURCE = String.raw`<title>\s*Just a moment\.\.\.|cf_chl_opt|/cdn-cgi/challenge-platform/h/[a-z]/orchestrate/|Checking your browser before|Checking if the site connection is secure|px-captcha|Press &amp; Hold|Press & Hold`;
export const CHALLENGE_TITLES_SOURCE = String.raw`^(just a moment|attention required|verify you are human|bir dakika)`;
export const DENIED_SOURCE = String.raw`Sorry, you have been blocked|You are unable to access|You don(?:'|’|&#39;|&#x27;)t have permission to access|You do not have permission to access`;
export const DENIED_TITLES_SOURCE = String.raw`^(access denied|403 forbidden|forbidden|error 403)\b`;
export const REGION_SOURCE = String.raw`outside of the United States|outside the United States|outside the U\.S\.|not available in your country|not available in your region|unable to service customers outside`;
export const REGION_TITLES_SOURCE = String.raw`^International \| Publix`;
export const REGION_ADDRESS_SOURCE = String.raw`geo-?block`;
export const HEAD = 40000;
export const SHORT_TEXT = 4000;
export const EMPTY_TEXT = 300;
const CHALLENGE = new RegExp(CHALLENGE_SOURCE, "i");
const CHALLENGE_TITLES = new RegExp(CHALLENGE_TITLES_SOURCE, "i");
const DENIED = new RegExp(DENIED_SOURCE, "i");
const DENIED_TITLES = new RegExp(DENIED_TITLES_SOURCE, "i");
const REGION = new RegExp(REGION_SOURCE, "i");
const REGION_TITLES = new RegExp(REGION_TITLES_SOURCE, "i");
const REGION_ADDRESS = new RegExp(REGION_ADDRESS_SOURCE, "i");
const INVISIBLE = /<(script|style|noscript|template)\b[^>]*>[\s\S]*?<\/\1\s*>|<!--[\s\S]*?-->/gi;
const NAMED = {amp: "&", lt: "<", gt: ">", quot: "\"", apos: "'", nbsp: " ", reg: "®", copy: "©", trade: "™", rsquo: "’", lsquo: "‘",
  rdquo: "”", ldquo: "“", ndash: "–", mdash: "—", hellip: "…"};

export const KIND_LABELS = {tamam: "tamam", dogrulama: "doğrulama", erisim_reddedildi: "erişim reddedildi", bolge_engeli: "bölge engeli",
  yonlendi: "başka siteye yönlendi"};
export const STAGE_LABELS = {aciliyor: "sayfa açılıyor", okunuyor: "sayfa okunuyor", dogrulama: "doğrulama bekleniyor", bekleme: "bekleme (hız kuralı)"};

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

function decodeEntities(text) {
  return text.replace(/&(#x[0-9a-f]+|#[0-9]+|[a-z]+);/gi, (whole, name) => {
    if (name[0] === "#") {
      const code = name[1] === "x" || name[1] === "X" ? parseInt(name.slice(2), 16) : parseInt(name.slice(1), 10);
      return Number.isFinite(code) && code > 0 && code < 0x110000 ? String.fromCodePoint(code) : whole;
    }
    return NAMED[name.toLowerCase()] ?? whole;
  });
}

/** The page's readable text: scripts, styles and comments dropped, tags removed, entities decoded, spaces collapsed. */
export function visibleText(html) {
  const text = String(html || "").replace(INVISIBLE, " ").replace(/<[^>]+>/g, " ");
  return decodeEntities(text).replace(/\s+/g, " ").trim();
}

/** "tamam", "dogrulama", "erisim_reddedildi" or "bolge_engeli" (the same order and rules as page_kinds.classify). */
export function pageKind(html = "", title = "", url = "", status = null) {
  const head = String(html || "").slice(0, HEAD);
  const name = String(title || "").trim();
  const text = visibleText(head);
  const code = Number.isFinite(Number(status)) && status !== null && status !== "" ? Number(status) : null;
  if (REGION_TITLES.test(name) || REGION_ADDRESS.test(String(url || ""))) return "bolge_engeli";
  if (REGION.test(text) && (code === 403 || code === 451 || text.length < SHORT_TEXT)) return "bolge_engeli";
  if (DENIED.test(head)) return "erisim_reddedildi";
  if (CHALLENGE.test(head) || CHALLENGE_TITLES.test(name)) return "dogrulama";
  if (DENIED_TITLES.test(name) || (code === 403 && text.length < EMPTY_TEXT)) return "erisim_reddedildi";
  return "tamam";
}

/** A page that went on to a site the extension may not open: "bolge_engeli" for a geo-block address, else "yonlendi". */
export function redirectKind(finalUrl) {
  return REGION_ADDRESS.test(String(finalUrl || "")) ? "bolge_engeli" : "yonlendi";
}

export function isVerification(html, title = "") {
  return pageKind(html, title) === "dogrulama";
}

export function isBlocked(html) {
  return DENIED.test(String(html || "").slice(0, HEAD));
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

const KEEP_HTML = ["tamam", "dogrulama", "erisim_reddedildi", "bolge_engeli"];

/** What is sent to the program for one page (the page itself for an ordinary page and, as evidence, for a refusal or a block). */
export function pageResult(state, page = {}, note = null) {
  const result = {durum: state, son_adres: page.url || null, baslik: page.title || "", http_durumu: page.status ?? null, not: note};
  if (KEEP_HTML.includes(state)) result.html = page.html ?? null;
  return result;
}

/** The decision for a page that has loaded (before its wait rule): a page kind that stops it, login, payment, or read it. */
export function classify(page) {
  const kind = pageKind(page.html, page.title, page.url, page.status);
  if (kind !== "tamam") return kind;
  if (isLogin(page)) return "giris";
  if (isPayment(page)) return "odeme";
  return "oku";
}

/** The note sent with a page that is not waited for. */
export function stopNote(kind, page = {}) {
  if (kind === "erisim_reddedildi") return "Erişim reddedildi (kimsenin geçemeyeceği engel sayfası); beklenmedi, atlandı.";
  if (kind === "bolge_engeli") return "Bölge engeli: site ABD dışından gelen ziyaretçiye hizmet vermiyor; beklenmedi, atlandı.";
  if (kind === "yonlendi") return `başka siteye yönlendi: ${domainOf(page.url)}`;
  return null;
}

/** The extension window's "Son iş" line: the site, the purpose, the stage and, for a job that stopped moving, since when (GÖREV-16). */
export function lastJobText(last, now = Date.now()) {
  if (!last) return "Henüz iş yok.";
  const head = `${last.alan_adi} · ${last.amac || "iş"}`;
  const when = new Date(last.zaman || now).toLocaleString("tr-TR");
  if (last.durum !== "çalışıyor") return `${head} · ${last.durum} · ${when}`;
  const stage = STAGE_LABELS[last.asama] || "çalışıyor";
  const moved = Number(last.ilerleme || last.zaman || now);
  const minutes = Math.floor((now - moved) / 60000);
  const waiting = last.asama === "dogrulama" && Number.isFinite(last.bitis) ? ` (kalan ${Math.max(0, Math.round((last.bitis - now) / 60000))} dk)` : "";
  if (last.asama !== "dogrulama" && now - moved > STUCK_AFTER_MS) {
    return `${head} · takılmış görünüyor: ${minutes} dk'dır ilerlemiyor (son adım: ${stage})`;
  }
  return `${head} · ${stage}${waiting} · son ilerleme ${minutes < 1 ? "az önce" : `${minutes} dk önce`}`;
}

export function bytesToBase64(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(binary);
}
