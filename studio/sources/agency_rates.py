"""Rental company prices for Book>Direct listings, asked on each company's own website for the destination's date windows.

Generic core: which company sites are read and with which platform adapter (studio.sources.agency_adapters) comes from the
destination configuration in SQLite; the input is the destination's latest Book>Direct lodging run and the date windows are the
destination's lodging windows. A Book>Direct listing is tied to a company page only through the url Book>Direct gives (the
company's own listing page); titles or addresses are never compared. Every response is kept gzip-compressed with its SHA-256.

Requests to one company are sequential and spaced; a few companies are read side by side. A company that refuses (repeated
403/429), cannot be reached or fails stops on its own; the others go on, and each company's result is recorded. When a site
shows a human-verification page, the configured verifier opens it in a visible browser with a persistent profile, the job shows
which site waits for the user, and after the user completes it the same browser session continues. Nobody here solves it.
"""
import gzip
import hashlib
import json
import re
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from urllib.parse import urljoin, urlsplit

import httpx

from .agency_adapters import ADAPTERS, AdapterError
from .base import CollectionCanceled, CollectionResult, SourceError
from .bookdirect_lodging import is_front_host, quartiles
from .climate_http import check, pause

CONNECTOR_VERSION = "agency-lodging-rates/1"
SOURCE_QUERY = "kaynak=kiralama-sirketleri"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36 "
              "30AStudio/0.11 (+https://github.com/bemonths/tatilya)")
REQUEST_GAP = 2.0           # seconds between two requests to the same company site
WORKERS = 3                 # companies read side by side; each company is sequential
RETRY_PAUSE = 5.0
BLOCK_LIMIT = 3             # consecutive refusals (401/403/429, no verification page) that stop a company; see site_answers()
ERROR_LIMIT = 5             # consecutive unreachable/failed requests that stop a company
VERIFY_TIMEOUT = 15 * 60
MAX_BYTES = 6_000_000
MAX_REDIRECTS = 5
PROGRESS_EVERY = 2.0
# Interstitial human-verification pages only (Cloudflare, PerimeterX). An ordinary page that merely contains a CAPTCHA widget
# (a contact form, a Drupal "Access denied" page) is not a verification page.
CHALLENGE = re.compile(r"Just a moment\.\.\.|cf-chl-|/cdn-cgi/challenge-platform|Verify you are human|Checking your browser before|"
                       r"Checking if the site connection is secure|px-captcha|Press &amp; Hold|Press & Hold", re.I)
PAGE_STATUSES = ("matched", "not_found", "no_listing", "off_site", "blocked", "error", "not_queried", "no_adapter", "no_url")
COMPANY_STATUSES = ("done", "stopped_blocked", "stopped_errors", "verification_timeout", "verification_unavailable", "failed")
QUOTE_STATUSES = ("priced", "unavailable", "restricted", "no_price", "error")
BEDROOM_BUCKETS = (("1-2", 0, 2), ("3", 3, 3), ("4", 4, 4), ("5+", 5, 1000))
SCOPE = ("Kiralama şirketlerinin kendi sitelerinde, Book>Direct ilanındaki şirket bağlantısıyla bulunan ilan için tarih pencerelerinde "
         "sorgulanan fiyat ve müsaitlik. Yalnız yapılandırılmış şirketler ve sitenin gösterdiği alanlar; tam envanter değildir.")
WEEKDAYS = {1: "Pazartesi", 2: "Salı", 3: "Çarşamba", 4: "Perşembe", 5: "Cuma", 6: "Cumartesi", 7: "Pazar"}


def source_host(url):
    """The Book>Direct clone host of an agency-rate source URL like https://<clone>.bookdirect.net/?kaynak=kiralama-sirketleri, or None.

    The listings and their company links come from that Book>Direct front end; the query only tells this source apart from the
    lodging search source on the same host."""
    match = re.fullmatch(r"https://([a-z0-9.-]+)/\?" + re.escape(SOURCE_QUERY), url or "")
    return match.group(1) if match and is_front_host(match.group(1)) else None


def site_domain(url):
    try:
        parts = urlsplit(url or "")
        host = (parts.hostname or "").lower()
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not host:
        return None
    return host.removeprefix("www.")


def on_domain(url, domain):
    host = site_domain(url)
    return host is not None and (host == domain or host.endswith("." + domain))


class VerificationNeeded(Exception):
    def __init__(self, url):
        super().__init__(url)
        self.url = url


class CompanyStopped(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status, self.message = status, message


class Reply:
    def __init__(self, status, url, headers, body, sha256, *, location=None):
        self.status, self.url, self.headers, self.body, self.sha256, self.location = status, url, headers, body, sha256, location

    @property
    def text(self):
        return self.body.decode("utf-8", errors="replace")


class HttpTransport:
    """Plain HTTPS with httpx; redirects are followed by the session so every hop is kept."""

    kind = "http"

    def __init__(self, client):
        self.client = client

    def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
        request = self.client.build_request(method, url, params=params, data=data, json=json_body, headers=headers)
        response = self.client.send(request, stream=True, follow_redirects=False)
        try:
            chunks, size = [], 0
            for part in response.iter_bytes():
                size += len(part)
                if size > MAX_BYTES:
                    raise SourceError("Şirket sitesinin yanıtı boyut sınırını aştı.")
                chunks.append(part)
            return response.status_code, str(response.request.url), dict(response.headers), b"".join(chunks)
        finally:
            response.close()

    def close(self):
        pass


class RawStore:
    """Thread-safe manifest of every response (gzip bodies); request bodies are kept so each price question can be repeated."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.manifest = {"connector": CONNECTOR_VERSION, "responses": []}
        self.unsaved = 0

    def save(self, *, company, transport, method, requested, status, final_url, headers, body, note, request_body):
        digest = hashlib.sha256(body).hexdigest()
        with self.lock:
            sequence = len(self.manifest["responses"]) + 1
            relative = f"responses/{sequence:06d}.gz"
            target = self.path.parent / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(gzip.compress(body, mtime=0))
            stamp = datetime.now(timezone.utc).isoformat()
            self.manifest["fetched_at"] = stamp
            self.manifest["responses"].append({
                "sequence": sequence, "company": company, "transport": transport, "note": note, "method": method, "requested_url": requested,
                "request_body": request_body, "final_url": final_url, "status": status, "content_type": headers.get("content-type"),
                "fetched_at": stamp, "raw_file": relative, "compression": "gzip", "raw_sha256": digest, "bytes": len(body)})
            self.unsaved += 1
            if self.unsaved >= 25:
                self._flush()
        return digest, stamp

    def flush(self):
        with self.lock:
            self._flush()

    def _flush(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        temporary.replace(self.path)
        self.unsaved = 0

    @property
    def count(self):
        with self.lock:
            return len(self.manifest["responses"])


class SiteSession:
    """Sequential, spaced requests to one company site; redirects are followed only inside the company's domain."""

    def __init__(self, store, domain, transport, canceled):
        self.store, self.domain, self.transport, self.canceled = store, domain, transport, canceled
        self.last = None
        self.requests = 0

    def request(self, method, url, *, note, params=None, data=None, json=None, headers=None):
        if not on_domain(url, self.domain):
            raise AdapterError("Uyarlayıcı şirketin alan adı dışındaki bir adrese istek yapmak istedi; yapılmadı.")
        current, hops = url, 0
        while True:
            check(self.canceled)
            if self.last is not None:
                pause(max(0.0, REQUEST_GAP - (time.monotonic() - self.last)), self.canceled)
            try:
                status, final, response_headers, body = self.send(method, current, params=params, data=data, json_body=json, headers=headers)
            finally:
                self.last = time.monotonic()
            self.requests += 1
            requested = str(httpx.URL(current, params=params)) if params else current
            digest, _ = self.store.save(company=self.domain, transport=self.transport.kind, method=method, requested=requested,
                                        status=status, final_url=final, headers=response_headers, body=body, note=note,
                                        request_body=data if data is not None else json)
            lowered = {k.lower(): v for k, v in response_headers.items()}
            reply = Reply(status, final, lowered, body, digest)
            if status in (301, 302, 303, 307, 308) and lowered.get("location"):
                target = urljoin(final, lowered["location"])
                if not on_domain(target, self.domain):
                    reply.location = target
                    return reply
                hops += 1
                if hops > MAX_REDIRECTS:
                    raise AdapterError("Yönlendirme sınırı aşıldı.")
                if status in (301, 302, 303):
                    method, data, json = "GET", None, None
                current, params = target, None
                continue
            if status in (403, 429, 503) and (lowered.get("cf-mitigated") == "challenge" or CHALLENGE.search(reply.text[:30000])):
                raise VerificationNeeded(current)
            return reply

    def send(self, method, url, *, headers=None, **kwargs):
        merged = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9", **(headers or {})}
        for attempt in range(2):
            try:
                return self.transport.send(method, url, headers=merged, **kwargs)
            except httpx.TransportError as exc:
                if attempt == 1:
                    raise AdapterError("Şirket sitesine bağlanılamadı veya zaman aşımı oluştu.") from exc
                pause(RETRY_PAUSE, self.canceled)


class Progress:
    def __init__(self, progress, total):
        self.progress, self.total, self.done = progress, max(1, total), 0
        self.lock = threading.Lock()
        self.last = 0.0

    def step(self, amount, message):
        with self.lock:
            self.done += amount
            now = time.monotonic()
            if now - self.last < PROGRESS_EVERY and self.done < self.total:
                return
            self.last = now
            percent = 2 + int(93 * self.done / self.total)
        self.progress(min(95, percent), message)


def active_windows(windows, today):
    result = []
    for window in windows:
        checkin, checkout = date.fromisoformat(window["checkin"]), date.fromisoformat(window["checkout"])
        result.append({**window, "checkin_date": checkin, "checkout_date": checkout, "nights": (checkout - checkin).days,
                       "status": "skipped_past" if checkin < today else "queried"})
    return result


def collect(raw_path, progress, canceled, *, config, client=None, verifier=None, waiting=None, today=None):
    """Ask every configured company site, for each listing linked to it, the price of every future window."""
    if not config or not config.get("sites"):
        raise SourceError("Bu destinasyon için kiralama şirketi yapılandırması yok.")
    lodging = config.get("input")
    if not lodging or not lodging.get("listings"):
        raise SourceError("Önce konaklama aramaları toplanmalı: kiralama şirketi fiyatları son Book>Direct çekimindeki ilanlardan sorulur.")
    today = today or datetime.now(timezone.utc).date()
    windows = active_windows(config["windows"], today)
    active = [w for w in windows if w["status"] == "queried"]
    if not active:
        raise SourceError("Bütün tarih pencereleri geçmişte kaldı; yapılandırmaya yeni tarihler eklenmeli.")
    sites = {site["domain"]: site for site in config["sites"] if site["enabled"]}
    unknown = sorted({site["adapter"] for site in sites.values()} - set(ADAPTERS))
    if unknown:
        raise SourceError(f"Yapılandırmada bilinmeyen uyarlayıcı: {', '.join(unknown)}.")

    listings, groups = {}, {}
    for item in lodging["listings"]:
        row = {"lodging_id": item["lodging_id"], "title": item["title"], "bedrooms": item["bedrooms"], "region_ids": sorted(item["region_ids"]),
               "listing_url": item["url"], "url_host": site_domain(item["url"]), "domain": None, "page_status": "no_url", "page_url": None,
               "http_status": None, "site_listing_id": None, "message": None}
        if row["url_host"]:
            domain = next((d for d in sites if row["url_host"] == d or row["url_host"].endswith("." + d)), None)
            row["page_status"] = "not_queried" if domain else "no_adapter"
            if domain:
                row["domain"] = domain
                groups.setdefault(domain, []).append(row)
        listings[row["lodging_id"]] = row
    order = sorted(groups, key=lambda d: (-len(groups[d]), d))
    store = RawStore(raw_path)
    owns = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(45, connect=15), verify=True)
    tracker = Progress(progress, sum(len(groups[d]) for d in order))
    verify_lock = threading.Lock()
    quotes, companies = [], {}
    progress(1, f"{len(order)} kiralama şirketinin sitesi için {sum(len(v) for v in groups.values())} ilan sorgulanacak.")

    def company(domain):
        site, members = sites[domain], groups[domain]
        adapter = ADAPTERS[site["adapter"]]
        session = SiteSession(store, domain, HttpTransport(client), canceled)
        result = {"domain": domain, "company": site["company"], "adapter": site["adapter"], "status": "done", "listing_count": len(members),
                  "verification": None, "message": None}
        pages, cache, blocked, errors = {}, {}, 0, 0
        browser = None

        def ask(call):
            nonlocal browser
            while True:
                try:
                    return call()
                except VerificationNeeded as need:
                    if verifier is None:
                        result["verification"] = "unavailable"
                        raise CompanyStopped("verification_unavailable",
                                             "Site doğrulama ekranı gösterdi; görünür tarayıcıyla doğrulama bu bilgisayarda kullanılamıyor.") from None
                    if browser is not None:
                        raise CompanyStopped("stopped_blocked", "Doğrulamadan sonra site yine doğrulama ekranı gösterdi; şirket durduruldu.") from None
                    with verify_lock:
                        if waiting:
                            waiting(domain)
                        try:
                            browser = verifier(domain, need.url, canceled, VERIFY_TIMEOUT)
                        finally:
                            if waiting:
                                waiting(None)
                    if browser is None:
                        result["verification"] = "timeout"
                        raise CompanyStopped("verification_timeout", "Kullanıcı doğrulaması süresinde tamamlanmadı; şirket atlandı.") from None
                    result["verification"] = "completed"
                    session.transport = browser

        try:
            for index, row in enumerate(members):
                check(canceled)
                url = row["listing_url"]
                if url not in pages:
                    pages[url] = open_listing(session, adapter, url, ask)
                page = pages[url]
                row.update({k: page[k] for k in ("page_status", "page_url", "http_status", "site_listing_id", "message")})
                if page["page_status"] == "blocked":
                    # A refused listing page can be one unpublished listing (Drupal answers its themed "Access denied" page)
                    # or the whole site refusing us. One look at the site's home page tells them apart.
                    if site_answers(session, url, ask):
                        blocked = 0
                        page["message"] = (f"Bu ilan sayfası erişime kapalı (HTTP {page['http_status']}); sitenin ana sayfası normal yanıt "
                                           "veriyor (ilan yayından kaldırılmış olabilir).")
                        row["message"] = page["message"]
                    else:
                        blocked += 1
                        if blocked >= BLOCK_LIMIT:
                            raise CompanyStopped("stopped_blocked", f"Site art arda {BLOCK_LIMIT} isteği reddetti (HTTP {page['http_status']}); "
                                                                    "şirket durduruldu.")
                else:
                    blocked = 0
                if page["page_status"] == "error":
                    errors += 1
                    if errors >= ERROR_LIMIT:
                        raise CompanyStopped("stopped_errors", f"Siteye art arda {ERROR_LIMIT} kez ulaşılamadı; şirket durduruldu.")
                elif page["page_status"] != "blocked":
                    errors = 0
                if page["page_status"] == "matched":
                    for window in active:
                        key = (page["site_listing_id"], window["window_key"])
                        if key not in cache:
                            cache[key] = ask_quote(session, adapter, page["info"], window, ask)
                            errors = errors + 1 if cache[key]["status"] == "error" else 0
                            if errors >= ERROR_LIMIT:
                                quotes.append({**cache[key], "lodging_id": row["lodging_id"], "window_key": window["window_key"]})
                                raise CompanyStopped("stopped_errors", f"Fiyat isteği art arda {ERROR_LIMIT} kez başarısız oldu; şirket durduruldu.")
                        quotes.append({**cache[key], "lodging_id": row["lodging_id"], "window_key": window["window_key"]})
                tracker.step(1, f"{site['company']}: {index + 1}/{len(members)} ilan.")
        except CompanyStopped as stop:
            result["status"], result["message"] = stop.status, stop.message
            for row in members:
                if row["page_status"] == "not_queried":
                    row["message"] = stop.message
        except CollectionCanceled:
            raise
        except Exception as exc:      # one company's unexpected failure never stops the others
            result["status"], result["message"] = "failed", f"Beklenmeyen hata: {type(exc).__name__}: {str(exc)[:200]}"
        finally:
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
        own = [q for q in quotes if listings[q["lodging_id"]]["domain"] == domain]
        result.update({"matched_count": sum(r["page_status"] == "matched" for r in members), "quote_count": len(own),
                       "priced_count": sum(q["status"] == "priced" for q in own), "request_count": session.requests})
        companies[domain] = result
        tracker.step(0, f"{site['company']}: bitti ({result['status']}).")

    try:
        with ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="30a-agency") as pool:
            futures = [pool.submit(company, domain) for domain in order]
            failures = [future.exception() for future in futures]
        if any(isinstance(error, CollectionCanceled) for error in failures) or canceled():
            raise CollectionCanceled()
        for error in failures:
            if error is not None:
                raise error
        store.flush()
        windows_rows = [{k: w[k] for k in ("window_key", "label", "checkin", "checkout", "nights", "status")} for w in windows]
        snapshot = {"lodging_run_id": lodging["run_id"], "queried_on": today.isoformat(), "request_count": store.count, "listing_count": len(listings)}
        statuses = {name: sum(r["page_status"] == name for r in listings.values()) for name in PAGE_STATUSES}
        priced = sorted({q["lodging_id"] for q in quotes if q["status"] == "priced"})
        metadata = {"lodging_run_id": lodging["run_id"], "lodging_searched_on": lodging.get("searched_on"), "queried_on": today.isoformat(),
                    "windows": windows_rows, "skipped_past_windows": [w["window_key"] for w in windows if w["status"] == "skipped_past"],
                    "request_count": store.count, "listing_count": len(listings), "page_statuses": statuses,
                    "priced_listings": len(priced), "quote_count": len(quotes),
                    "companies": [companies[d] for d in order], "scope": SCOPE}
        progress(97, f"{len(listings)} ilan, {len(quotes)} fiyat sorgusu ve {len(order)} şirket sonucu kaydediliyor.")
        related = {"snapshot": snapshot, "windows": windows_rows, "companies": [companies[d] for d in order], "quotes": quotes}
        return CollectionResult([listings[i] for i in sorted(listings)], len(listings), statuses["no_url"] + statuses["no_adapter"], None,
                                metadata, related)
    finally:
        try:
            store.flush()
        except OSError:
            pass
        if owns:
            client.close()


def open_listing(session, adapter, url, ask):
    """GET the company listing page Book>Direct links to and let the adapter find its platform identity there."""
    base = {"page_url": None, "http_status": None, "site_listing_id": None, "message": None, "info": None}
    if not on_domain(url, session.domain):
        return {**base, "page_status": "off_site", "message": "Bağlantı şirketin alan adında değil."}
    try:
        reply = ask(lambda: session.request("GET", url, note="listing-page", headers={"Accept": "text/html,application/xhtml+xml"}))
    except AdapterError as exc:
        return {**base, "page_status": "error", "message": str(exc)}
    base.update({"page_url": reply.url, "http_status": reply.status})
    if reply.location:
        return {**base, "page_status": "off_site", "page_url": reply.location, "message": "Bağlantı başka bir siteye yönlendi."}
    if reply.status in (404, 410):
        return {**base, "page_status": "not_found", "message": f"Şirket sitesi bu bağlantı için HTTP {reply.status} döndü."}
    if reply.status in (401, 403, 429):
        return {**base, "page_status": "blocked", "message": f"Site isteği reddetti (HTTP {reply.status})."}
    if reply.status != 200:
        return {**base, "page_status": "error", "message": f"Şirket sitesi HTTP {reply.status} döndü."}
    info = adapter.parse_page(reply.text, reply.url)
    if not info:
        return {**base, "page_status": "no_listing", "message": "Sayfada bu altyapının ilan kimliği yok; bağlantı ilan sayfasına gitmiyor olabilir."}
    return {**base, "page_status": "matched", "site_listing_id": info["site_id"], "info": info}


def site_answers(session, url, ask):
    """True when the company's home page still answers 200, i.e. a refused listing page is not the whole site refusing us."""
    parts = urlsplit(url)
    try:
        reply = ask(lambda: session.request("GET", f"{parts.scheme}://{parts.netloc}/", note="site-check", headers={"Accept": "text/html"}))
    except AdapterError:
        return False
    return reply.status == 200 and not reply.location


def ask_quote(session, adapter, info, window, ask):
    started = datetime.now(timezone.utc).isoformat()
    try:
        answer = ask(lambda: adapter.quote(session, info, window))
    except AdapterError as exc:
        answer = {"status": "error", "available": None, "message": str(exc), "replies": []}
    replies = answer.pop("replies", [])
    row = {"status": answer["status"], "available": answer.get("available"), "nightly_rates": answer.get("nightly_rates"),
           "rent": answer.get("rent"), "cleaning_fee": answer.get("cleaning_fee"), "other_fees": answer.get("other_fees"),
           "fees": answer.get("fees"), "taxes": answer.get("taxes"), "tax_items": answer.get("tax_items"), "total": answer.get("total"),
           "total_includes_fees": answer.get("total_includes_fees"), "total_includes_taxes": answer.get("total_includes_taxes"),
           "excluded_items": answer.get("excluded_items"), "currency": answer.get("currency"), "min_stay": answer.get("min_stay"),
           "checkin_days": answer.get("checkin_days"), "rule_source": answer.get("rule_source"), "message": answer.get("message"),
           "queried_at": started, "queried_url": replies[-1].url if replies else info.get("page_url"),
           "raw_sha256": [reply.sha256 for reply in replies]}
    if row["status"] == "priced" and row["total"] is None and row["rent"] is None:
        row["status"] = "no_price"
    return row


# --- Summaries computed when read --------------------------------------------------------------------------------------

def bucket_of(bedrooms):
    if bedrooms is None:
        return None
    return next((name for name, low, high in BEDROOM_BUCKETS if low <= bedrooms <= high or name == "1-2" and bedrooms < 1), None)


def total_label(quotes, queried_on):
    priced = [q for q in quotes if q["status"] == "priced" and q["total"] is not None]
    taxed = sum(q["total_includes_taxes"] == 1 for q in priced)
    fees = sum(q["total_includes_fees"] == 1 for q in priced)
    head = f"Kiralama şirketlerinin kendi sitelerinde {queried_on} tarihinde sorgulanan fiyatlar"
    if not priced:
        return f"{head}; fiyat alınamadı."
    if taxed == len(priced):
        fee_text = ("sitenin gösterdiği zorunlu ücretleri ve vergileri içerir" if fees == len(priced) else
                    f"vergileri içerir; zorunlu ücretler {fees} fiyatta ayrı kalem olarak gösterildi ve toplama dahil, diğerlerinde site ayrı ücret göstermedi")
        return f"{head}; toplam fiyat {fee_text} (isteğe bağlı sigorta gibi kalemler hariç)."
    return (f"{head}; toplam fiyat {taxed}/{len(priced)} fiyatta vergileri ve sitenin gösterdiği ücretleri içerir, kalanında sitenin toplamı "
            "kalemlerin toplamıyla doğrulanamadı.")


def summarize(con, run_id, region_order=(), region_names=None):
    snapshot = con.execute("SELECT * FROM agency_rate_snapshots WHERE run_id=?", (run_id,)).fetchone()
    if not snapshot:
        return None
    windows = [dict(r) for r in con.execute("SELECT * FROM agency_rate_windows WHERE run_id=? ORDER BY checkin", (run_id,))]
    listings = {r["lodging_id"]: decode_listing(r) for r in con.execute("SELECT * FROM agency_rate_listings WHERE run_id=?", (run_id,))}
    quotes = [decode_quote(r) for r in con.execute("SELECT * FROM agency_rate_quotes WHERE run_id=?", (run_id,))]
    companies = [dict(r) for r in con.execute("SELECT * FROM agency_rate_companies WHERE run_id=? ORDER BY listing_count DESC, domain", (run_id,))]
    by_window = {}
    for quote in quotes:
        by_window.setdefault(quote["window_key"], {})[quote["lodging_id"]] = quote
    region_ids = {region for listing in listings.values() for region in listing["region_ids"]}
    order = {region: index for index, region in enumerate(region_order)}
    regions = sorted(region_ids, key=lambda r: (order.get(r, len(order)), r))
    names = region_names or {}
    cells = []
    for region in regions:
        members = [l for l in listings.values() if region in l["region_ids"]]
        for window in windows:
            cell = {"region_id": region, "window_key": window["window_key"], "status": window["status"], "listing_count": len(members),
                    "linked_count": sum(m["domain"] is not None for m in members)}
            if window["status"] == "queried":
                asked = [by_window.get(window["window_key"], {}).get(m["lodging_id"]) for m in members]
                asked = [(m, q) for m, q in zip(members, asked) if q is not None]
                priced = [(m, q) for m, q in asked if q["status"] == "priced" and q["total"] is not None]
                known = [q for _, q in asked if q["available"] is not None]
                totals = [q["total"] for _, q in priced]
                nightly = [round(q["rent"] / window["nights"], 2) for _, q in priced if q["rent"] is not None]
                q1, median, q3 = quartiles(totals)
                n1, nmedian, n3 = quartiles(nightly)
                buckets = {}
                for name, _, _ in BEDROOM_BUCKETS:
                    values = [q["total"] for m, q in priced if bucket_of(m["bedrooms"]) == name]
                    buckets[name] = {"count": len(values), "median": round(statistics.median(values), 2) if values else None}
                cell.update({"queried_count": len(asked), "priced_count": len(priced),
                             "priced_share": round(len(priced) / len(asked), 3) if asked else None,
                             "available_known": len(known), "available_share": round(sum(q["available"] for q in known) / len(known), 3) if known else None,
                             "total_q1": q1, "total_median": median, "total_q3": q3,
                             "nightly_q1": n1, "nightly_median": nmedian, "nightly_q3": n3, "bedrooms": buckets})
            cells.append(cell)
    coverage = {name: sum(l["page_status"] == name for l in listings.values()) for name in PAGE_STATUSES}
    priced_ids = {q["lodging_id"] for q in quotes if q["status"] == "priced"}
    regions_priced = {r for l in listings.values() if l["lodging_id"] in priced_ids for r in l["region_ids"]}
    return {"snapshot": dict(snapshot), "windows": windows, "regions": [{"region_id": r, "region_name": names.get(r, r)} for r in regions],
            "cells": cells, "companies": companies, "coverage": {**coverage, "listings": len(listings), "priced_listings": len(priced_ids),
                                                                 "regions": len(regions), "regions_with_price": len(regions_priced)},
            "label": total_label(quotes, snapshot["queried_on"]),
            "nightly_note": "Gecelik ortalama = sitenin kira tutarı ÷ gece sayısı (bizim hesabımız; ücret ve vergiler hariç).",
            "bedroom_note": "Oda sayısı Book>Direct ilanından; 1–2 grubuna stüdyolar dahildir. Ortancalar 7 gecelik toplam fiyattandır."}


def region_listings(con, run_id, region_id):
    if not con.execute("SELECT 1 FROM agency_rate_snapshots WHERE run_id=?", (run_id,)).fetchone():
        return None
    quotes = {}
    for row in con.execute("SELECT * FROM agency_rate_quotes WHERE run_id=?", (run_id,)):
        quotes.setdefault(row["lodging_id"], {})[row["window_key"]] = decode_quote(row)
    result = []
    for row in con.execute("SELECT l.*, c.company, c.adapter FROM agency_rate_listings l LEFT JOIN agency_rate_companies c ON c.run_id=l.run_id AND c.domain=l.domain "
                           "WHERE l.run_id=? ORDER BY l.title, l.lodging_id", (run_id,)):
        listing = decode_listing(row)
        if region_id in listing["region_ids"]:
            result.append({**listing, "quotes": quotes.get(listing["lodging_id"], {})})
    return result


def decode_listing(row):
    result = dict(row)
    result["region_ids"] = json.loads(result["region_ids"])
    return result


def decode_quote(row):
    result = dict(row)
    for key in ("nightly_rates", "fees", "tax_items", "excluded_items", "checkin_days", "raw_sha256"):
        result[key] = json.loads(result[key]) if result[key] is not None else None
    return result


def dumps(value):
    return None if value is None else json.dumps(value, ensure_ascii=False)


class AgencyRatesConnector:
    name = "agency-lodging-rates"
    version = CONNECTOR_VERSION
    raw_filename = "manifest.json"
    method = "HTML/JSON"
    diff_enabled = False
    diff_reason = "Kiralama şirketi fiyatları tarihe bağlı sorgulardır; sürümler arası fark envanter değişikliği sayılmamalı."
    inputs = ("lodging_listings",)
    uses_verification = True

    def __init__(self, verifier_factory=None):
        self.verifier_factory = verifier_factory

    def supports(self, source):
        return source_host(source.get("url")) is not None

    def collect(self, source, raw_path, progress, canceled, *, context, waiting=None):
        lodging, agency = context.lodging, context.agency
        if not lodging or not agency:
            raise SourceError("Bu destinasyon için kiralama şirketi fiyat yapılandırması yok.")
        if lodging["clone_host"] != source_host(source["url"]):
            raise SourceError("Kaynağın Book>Direct adresi destinasyonun konaklama yapılandırmasıyla uyuşmuyor.")
        verifier = self.verifier_factory() if self.verifier_factory else default_verifier()
        return collect(raw_path, progress, canceled, config={**agency, "windows": lodging["windows"]}, verifier=verifier, waiting=waiting)

    def store_records(self, con, run_id, records, related=None):
        snapshot = related["snapshot"]
        con.execute("INSERT INTO agency_rate_snapshots (run_id,lodging_run_id,queried_on,request_count,listing_count) VALUES (?,?,?,?,?)",
                    (run_id, snapshot["lodging_run_id"], snapshot["queried_on"], snapshot["request_count"], snapshot["listing_count"]))
        con.executemany("INSERT INTO agency_rate_windows (run_id,window_key,label,checkin,checkout,nights,status) VALUES (?,?,?,?,?,?,?)",
                        [(run_id, w["window_key"], w["label"], w["checkin"], w["checkout"], w["nights"], w["status"]) for w in related["windows"]])
        con.executemany("""INSERT INTO agency_rate_companies (run_id,domain,company,adapter,status,listing_count,matched_count,quote_count,priced_count,
            request_count,verification,message) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, c["domain"], c["company"], c["adapter"], c["status"], c["listing_count"], c["matched_count"], c["quote_count"], c["priced_count"],
              c["request_count"], c["verification"], c["message"]) for c in related["companies"]])
        con.executemany("""INSERT INTO agency_rate_listings (run_id,lodging_id,title,bedrooms,region_ids,listing_url,url_host,domain,page_status,page_url,
            http_status,site_listing_id,message) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, r["lodging_id"], r["title"], r["bedrooms"], json.dumps(r["region_ids"]), r["listing_url"], r["url_host"], r["domain"],
              r["page_status"], r["page_url"], r["http_status"], r["site_listing_id"], r["message"]) for r in records])
        con.executemany("""INSERT INTO agency_rate_quotes (run_id,lodging_id,window_key,status,available,nightly_rates,rent,cleaning_fee,other_fees,fees,
            taxes,tax_items,total,total_includes_fees,total_includes_taxes,excluded_items,currency,min_stay,checkin_days,rule_source,message,
            queried_at,queried_url,raw_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, q["lodging_id"], q["window_key"], q["status"], q["available"], dumps(q["nightly_rates"]), q["rent"], q["cleaning_fee"],
              q["other_fees"], dumps(q["fees"]), q["taxes"], dumps(q["tax_items"]), q["total"], q["total_includes_fees"], q["total_includes_taxes"],
              dumps(q["excluded_items"]), q["currency"], q["min_stay"], dumps(q["checkin_days"]), q["rule_source"], q["message"], q["queried_at"],
              q["queried_url"], json.dumps(q["raw_sha256"])) for q in related["quotes"]])

    def read_records(self, con, run_id):
        return [decode_listing(r) for r in con.execute("SELECT * FROM agency_rate_listings WHERE run_id=? ORDER BY title, lodging_id", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Agency rate diff is disabled.")


def default_verifier():
    """The visible-browser verifier when Playwright is installed; None otherwise (a verification page then skips that company)."""
    from .browser_verification import BrowserVerifier, available
    return BrowserVerifier() if available() else None
