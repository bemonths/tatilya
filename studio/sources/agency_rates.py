"""Rental company prices for Book>Direct listings, asked on each company's own website for the destination's date windows.

Generic core: which company sites are read, with which platform adapter (studio.sources.agency_adapters), whether the site is
protected, the guest count rule, the company's own listing list and an own-inventory community all come from the destination
configuration in SQLite; the input is the destination's latest Book>Direct lodging run and the date windows are the
destination's lodging windows. Every response is kept gzip-compressed with its SHA-256.

A Book>Direct listing is tied to a company page first through the url Book>Direct gives ("link"). When that link does not reach
a listing (404, home page, general list, another site) and the company's own listing list is configured, the strict address or
location rule of studio.sources.agency_matching may tie it ("address" / "location"); titles are never compared. A company that
runs the official rental program of one community (configured with that community and the name its site uses) also has the
homes Book>Direct does not show read from its own list ("own inventory"); they are stored and summarized apart. A site that
publishes a seasonal rent range instead of a working price display has it stored apart as a published rent, never as a quote.

Requests to one company are sequential and spaced; a few companies are read side by side. A protected company (e.g. behind
Cloudflare), and any company whose host once showed a verification page (browser_hosts), is read only through the computer's own
browser (studio.sources.browser_verification: the installed Chrome started as an ordinary application with one persistent
profile, reached over CDP), at most one at a time, PROTECTED_GAP seconds apart, and stops at its first refusal (403/429/block
page) without retrying. A site still showing a verification page after a short grace period is left for the end: when every
other company is done, the waiting sites are opened in tabs, the job lists them once and waits up to VERIFY_TIMEOUT for the user;
a site still not verified then is skipped and recorded. Nobody here solves a verification.
"""
import gzip
import hashlib
import json
import re
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import date, datetime, timezone
from urllib.parse import urljoin, urlsplit

import httpx

from .agency_adapters import ADAPTERS, DEFAULT_GUESTS, AdapterError
from .agency_matching import address_match, json_ld_unit, location_match, normalize_address, same_rooms
from .base import CollectionCanceled, CollectionResult, SourceError
from .browser_verification import GRACE_SECONDS, host_key, mark_hosts
from .bookdirect_lodging import is_front_host, quartiles
from .climate_http import check, pause
from .price_history import annotate_windows, compare, season_groups
from .windows import monthly_windows

CONNECTOR_VERSION = "agency-lodging-rates/2"
SOURCE_QUERY = "kaynak=kiralama-sirketleri"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36 "
              "30AStudio/0.12 (+https://github.com/bemonths/tatilya)")
REQUEST_GAP = 2.0           # seconds between two requests to the same company site
PROTECTED_GAP = 6.0         # the same for a protected site (Cloudflare and kin)
WORKERS = 3                 # companies read side by side; each company is sequential; protected companies one at a time
RETRY_PAUSE = 5.0
BLOCK_LIMIT = 3             # consecutive refusals (401/403/429, no verification page) that stop a company; see site_answers()
ERROR_LIMIT = 5             # consecutive unreachable/failed requests that stop a company
VERIFY_TIMEOUT = 15 * 60
MAX_BYTES = 8_000_000
MAX_REDIRECTS = 5
MAX_INVENTORY_PAGES = 400   # listing pages read from one company's sitemap
PROGRESS_EVERY = 2.0
# Interstitial human-verification pages only (Cloudflare, PerimeterX). An ordinary page that merely contains a CAPTCHA widget
# (a contact form, a Drupal "Access denied" page) is not a verification page.
CHALLENGE = re.compile(r"<title>\s*Just a moment\.\.\.|cf_chl_opt|/cdn-cgi/challenge-platform/h/[a-z]/orchestrate/|Checking your browser before|"
                       r"Checking if the site connection is secure|px-captcha|Press &amp; Hold|Press & Hold", re.I)
BLOCK_PAGE = re.compile(r"Sorry, you have been blocked|You are unable to access|Attention Required! \| Cloudflare", re.I)
SOFT_404 = re.compile(r"\bpages? not found\b|\b404\b|\bnot found\b", re.I)    # a "not found" page served with HTTP 200
PAGE_STATUSES = ("matched", "not_found", "no_listing", "off_site", "blocked", "error", "not_queried", "no_adapter", "no_url")
FALLBACK_STATUSES = ("not_found", "no_listing", "off_site")      # the link did not reach a listing: the company's list may
MATCH_METHODS = ("link", "address", "location")
COMPANY_STATUSES = ("done", "stopped_blocked", "stopped_errors", "verification_timeout", "verification_unavailable", "failed")
QUOTE_STATUSES = ("priced", "unavailable", "restricted", "no_price", "error")
GUEST_RULES = ("two_adults", "bedrooms_x2")
BEDROOM_BUCKETS = (("1-2", 0, 2), ("3", 3, 3), ("4", 4, 4), ("5+", 5, 1000))
SCOPE = ("Kiralama şirketlerinin kendi sitelerinde, Book>Direct ilanıyla bağlantı, adres veya konum kuralıyla eşlenen ilanlar ve "
         "tek bir topluluğun resmî kiralama programında şirketin kendi listesindeki evler için tarih pencerelerinde sorgulanan fiyat "
         "ve müsaitlik. Yalnız yapılandırılmış şirketler ve sitenin gösterdiği alanlar; tam envanter değildir.")
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


def same_url(a, b):
    """Two listing urls that name the same page (scheme, www., trailing slash and query ignored)."""
    def key(url):
        parts = urlsplit(url or "")
        return (parts.hostname or "").lower().removeprefix("www."), parts.path.rstrip("/").lower()
    return bool(a and b) and key(a) == key(b)


def guests_for(site, bedrooms, sleeps):
    """The guest count asked for one listing: two adults, or (rule bedrooms_x2) two adults per bedroom without exceeding the
    capacity the listing gives; never fewer than two adults."""
    if site.get("guest_rule") != "bedrooms_x2" or not bedrooms:
        return dict(DEFAULT_GUESTS)
    adults = int(bedrooms) * 2
    if sleeps:
        adults = min(adults, int(sleeps))
    return {"adults": max(2, adults), "children": 0}


class VerificationNeeded(Exception):
    def __init__(self, url):
        super().__init__(url)
        self.url = url


class CompanyDeferred(Exception):
    """The company's site shows a verification page: it is left for the end of the run."""

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
    """Sequential, spaced requests to one company site; requests and redirects stay inside the company's domains (its own, the
    configured aliases its links redirect to, and the platform's API hosts). A protected site stops at its first refusal."""

    def __init__(self, store, domain, transport, canceled, *, allowed=(), gap=None, protected=False):
        self.store, self.domain, self.transport, self.canceled = store, domain, transport, canceled
        self.allowed = (domain, *allowed)
        self.gap = REQUEST_GAP if gap is None else gap
        self.protected = protected
        self.last = None
        self.requests = 0

    def allows(self, url):
        return any(on_domain(url, domain) for domain in self.allowed)

    def request(self, method, url, *, note, params=None, data=None, json=None, headers=None):
        if not self.allows(url):
            raise AdapterError("Uyarlayıcı şirketin alan adı dışındaki bir adrese istek yapmak istedi; yapılmadı.")
        current, hops = url, 0
        while True:
            check(self.canceled)
            if self.last is not None:
                pause(max(0.0, self.gap - (time.monotonic() - self.last)), self.canceled)
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
                if not self.allows(target):
                    reply.location = target
                    return reply
                hops += 1
                if hops > MAX_REDIRECTS:
                    raise AdapterError("Yönlendirme sınırı aşıldı.")
                if status in (301, 302, 303):
                    method, data, json = "GET", None, None
                current, params = target, None
                continue
            head = reply.text[:30000] if status in (403, 429, 503) or self.protected else ""
            if status in (403, 429, 503) and (lowered.get("cf-mitigated") == "challenge" or CHALLENGE.search(head)):
                raise VerificationNeeded(current)
            if self.protected and (status in (403, 429) or BLOCK_PAGE.search(head)):
                raise CompanyStopped("stopped_blocked", f"Korumalı site isteği reddetti (HTTP {status}{', engel sayfası' if BLOCK_PAGE.search(head) else ''}); "
                                                        "şirket hemen durduruldu, yeniden denenmedi.")
            return reply

    def send(self, method, url, *, headers=None, **kwargs):
        merged = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9", **(headers or {})}
        for attempt in range(1 if self.protected else 2):
            try:
                return self.transport.send(method, url, headers=merged, **kwargs)
            except httpx.TransportError as exc:
                if attempt == 1 or self.protected:
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


def site_options(site):
    """Configuration of one company with defaults for the columns added in v12 (aliases, protected, guest rule, own listing list,
    own-inventory community)."""
    def loaded(value, default):
        if value is None:
            return default
        return json.loads(value) if isinstance(value, str) else value
    return {**site, "aliases": loaded(site.get("aliases"), []), "protected": int(site.get("protected") or 0),
            "guest_rule": site.get("guest_rule") or "two_adults", "inventory": loaded(site.get("inventory"), None),
            "own_region_id": site.get("own_region_id"), "own_city": site.get("own_city")}


def collect(raw_path, progress, canceled, *, config, client=None, verifier=None, waiting=None, today=None):
    """Ask every configured company site the price of every future window for each listing tied to it (and for its own inventory).
    Companies whose site waits for a human verification are read last, after one shared wait (see the module text)."""
    if not config or not config.get("sites"):
        raise SourceError("Bu destinasyon için kiralama şirketi yapılandırması yok.")
    lodging = config.get("input")
    if not lodging or not lodging.get("listings"):
        raise SourceError("Önce konaklama aramaları toplanmalı: kiralama şirketi fiyatları son Book>Direct çekimindeki ilanlardan sorulur.")
    today = today or datetime.now(timezone.utc).date()
    # the same window rule as the lodging collector (the windows of the run day); otherwise the configured fixed windows
    windows = active_windows(monthly_windows(today, config["window_rule"]) if config.get("window_rule") else config["windows"], today)
    active = [w for w in windows if w["status"] == "queried"]
    if not active:
        raise SourceError("Bütün tarih pencereleri geçmişte kaldı; yapılandırmaya yeni tarihler eklenmeli.")
    sites = {site["domain"]: site_options(site) for site in config["sites"] if site["enabled"]}
    browser_hosts = {host_key(h) for h in config.get("browser_hosts") or ()}
    for site in sites.values():
        if any(host_key(h) in browser_hosts for h in (site["domain"], *site["aliases"])):
            site["protected"], site["browser_host"] = 1, True       # once showed a verification page: browser only
    unknown = sorted({site["adapter"] for site in sites.values()} - set(ADAPTERS))
    if unknown:
        raise SourceError(f"Yapılandırmada bilinmeyen uyarlayıcı: {', '.join(unknown)}.")

    listings, groups, everyone = {}, {d: [] for d in sites}, []
    for item in lodging["listings"]:
        row = {"lodging_id": item["lodging_id"], "title": item["title"], "bedrooms": item.get("bedrooms"), "region_ids": sorted(item["region_ids"]),
               "listing_url": item["url"], "url_host": site_domain(item["url"]), "domain": None, "page_status": "no_url", "page_url": None,
               "http_status": None, "site_listing_id": None, "message": None, "link_status": None, "match_method": None, "match_note": None}
        everyone.append({"lodging_id": item["lodging_id"], "address": item.get("address"), "latitude": item.get("latitude"),
                         "longitude": item.get("longitude"), "bedrooms": item.get("bedrooms"), "bathrooms": item.get("bathrooms"),
                         "sleeps": item.get("sleeps"), "url": item["url"]})
        if row["url_host"]:
            domain = next((d for d, s in sites.items()
                           if any(row["url_host"] == h or row["url_host"].endswith("." + h) for h in (d, *s["aliases"]))), None)
            row["page_status"] = "not_queried" if domain else "no_adapter"
            if domain:
                row["domain"] = domain
                groups[domain].append(row)
        listings[row["lodging_id"]] = row
    order = sorted((d for d in sites if groups[d] or sites[d]["own_region_id"]), key=lambda d: (-len(groups[d]), d))
    store = RawStore(raw_path)
    owns = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(45, connect=15), verify=True)
    shared = Shared(store=store, client=client, canceled=canceled, verifier=verifier, waiting=waiting, active=active, everyone=everyone,
                    tracker=Progress(progress, sum(max(1, len(groups[d])) for d in order)), marks={})
    progress(1, f"{len(order)} kiralama şirketinin sitesi için {sum(len(groups[d]) for d in order)} ilan sorgulanacak.")
    try:
        with ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="30a-agency") as pool:
            futures = [pool.submit(CompanyRun(shared, sites[domain], groups[domain]).run) for domain in order]
            failures = [future.exception() for future in futures]
        if any(isinstance(error, CollectionCanceled) for error in failures) or canceled():
            raise CollectionCanceled()
        for error in failures:
            if error is not None:
                raise error
        store.flush()
        runs = [future.result() for future in futures]
        deferred = [index for index, run in enumerate(runs) if run.deferred]
        if deferred:
            runs = finish_deferred(shared, runs, deferred)
            store.flush()
        companies = [run.result for run in runs]
        quotes = [q for run in runs for q in run.quotes]
        own_rows = [r for run in runs for r in run.own_rows]
        own_quotes = [q for run in runs for q in run.own_quotes]
        published = [p for run in runs for p in run.published]
        windows_rows = [{k: w[k] for k in ("window_key", "label", "checkin", "checkout", "nights", "status")} for w in windows]
        snapshot = {"lodging_run_id": lodging["run_id"], "queried_on": today.isoformat(), "request_count": store.count, "listing_count": len(listings)}
        statuses = {name: sum(r["page_status"] == name for r in listings.values()) for name in PAGE_STATUSES}
        priced = sorted({q["lodging_id"] for q in quotes if q["status"] == "priced"})
        metadata = {"lodging_run_id": lodging["run_id"], "lodging_searched_on": lodging.get("searched_on"), "queried_on": today.isoformat(),
                    "window_rule": config.get("window_rule"), "windows": windows_rows, "skipped_past_windows": [w["window_key"] for w in windows if w["status"] == "skipped_past"],
                    "request_count": store.count, "listing_count": len(listings), "page_statuses": statuses,
                    "match_methods": {m: sum(r["match_method"] == m for r in listings.values()) for m in MATCH_METHODS},
                    "priced_listings": len(priced), "quote_count": len(quotes), "own_listings": len(own_rows),
                    "own_priced": len({(q["domain"], q["site_listing_id"]) for q in own_quotes if q["status"] == "priced"}),
                    "published_rents": len(published), "companies": companies, "scope": SCOPE,
                    "browser_hosts": sorted(shared.marks.values(), key=lambda m: m["host"])}
        progress(97, f"{len(listings)} ilan, {len(quotes)} fiyat sorgusu, kendi envanterinden {len(own_rows)} ev ve {len(order)} şirket sonucu kaydediliyor.")
        related = {"snapshot": snapshot, "windows": windows_rows, "companies": companies, "quotes": quotes, "own_listings": own_rows,
                   "own_quotes": own_quotes, "published": published, "browser_hosts": metadata["browser_hosts"]}
        return CollectionResult([listings[i] for i in sorted(listings)], len(listings), statuses["no_url"] + statuses["no_adapter"], None,
                                metadata, related)
    finally:
        try:
            store.flush()
        except OSError:
            pass
        if owns:
            client.close()


def finish_deferred(shared, runs, deferred):
    """The end of the run for the companies whose site waited for a verification: their sites are opened in tabs, the job lists
    them once and waits up to VERIFY_TIMEOUT; the verified ones are then read (one at a time), the others skipped and recorded."""
    sites = {runs[i].site["domain"]: runs[i].deferred for i in deferred}
    progress = shared.tracker
    progress.step(0, f"Doğrulama bekleyen siteler: {', '.join(sorted(sites))}.")
    if shared.verifier is not None and hasattr(shared.verifier, "wait_all"):
        cleared = shared.verifier.wait_all(sites, shared.canceled, VERIFY_TIMEOUT, shared.waiting)
        final_timeout = GRACE_SECONDS
    else:
        cleared, final_timeout = set(sites), VERIFY_TIMEOUT       # a plain verifier waits per site
        if shared.waiting:
            shared.waiting(", ".join(sorted(sites)))
    try:
        for index in deferred:
            check(shared.canceled)
            first = runs[index]
            domain = first.site["domain"]
            for row in first.members:          # the first attempt's partial rows are dropped; the company is read again
                row.update({"page_status": "not_queried", "page_url": None, "http_status": None, "site_listing_id": None, "message": None,
                            "link_status": None, "match_method": None, "match_note": None})
            again = CompanyRun(shared, first.site, first.members, final_timeout=final_timeout)
            if domain not in cleared:
                again.skip("verification_timeout", "timeout", "Kullanıcı doğrulaması süresinde tamamlanmadı; şirket atlandı.")
            else:
                again.run()
                if again.deferred:
                    again.skip("verification_timeout", "timeout", "Kullanıcı doğrulaması süresinde tamamlanmadı; şirket atlandı.")
            runs[index] = again
    finally:
        if shared.waiting and not hasattr(shared.verifier, "wait_all"):
            shared.waiting(None)
    return runs


class Shared:
    """What every company of one run shares: the raw store, the http client, the verifier and the locks."""

    def __init__(self, **values):
        self.__dict__.update(values)
        self.verify_lock, self.protected_lock = threading.Lock(), threading.Lock()


class CompanyRun:
    """One company: link phase, then (when configured) the company's own list for address/location matches and own inventory,
    then published rents. Any failure here is recorded on the company and never stops the others."""

    def __init__(self, shared, site, members, final_timeout=None):
        self.shared, self.site, self.members = shared, site, members
        self.final_timeout = final_timeout      # None: the first round (a verification page is left for the end)
        self.deferred = None
        self.adapter = ADAPTERS[site["adapter"]]
        self.protected = bool(site["protected"])
        self.session = SiteSession(shared.store, site["domain"], HttpTransport(shared.client), shared.canceled,
                                   allowed=(*site["aliases"], *getattr(self.adapter, "api_hosts", ())),
                                   gap=PROTECTED_GAP if self.protected else REQUEST_GAP, protected=self.protected)
        self.result = {"domain": site["domain"], "company": site["company"], "adapter": site["adapter"], "status": "done",
                       "listing_count": len(members), "verification": None, "message": None, "protected": int(self.protected),
                       "guest_rule": site["guest_rule"], "inventory_count": None, "inventory_raw_sha256": None, "own_count": 0,
                       "own_outside": None, "own_on_bookdirect": None}
        self.browser, self.pages, self.cache = None, {}, {}
        self.blocked = self.errors = 0
        self.quotes, self.own_rows, self.own_quotes, self.published = [], [], [], []
        self.facts = {f["lodging_id"]: f for f in shared.everyone}

    # --- browser and verification ---------------------------------------------------------------------------------------

    def open_browser(self, url):
        """The computer's browser for this company (one tab). A verification page still on screen after the grace period leaves the
        company for the end of the run; at the end the user has had the one shared wait."""
        shared, domain = self.shared, self.site["domain"]
        if shared.verifier is None:
            self.result["verification"] = "unavailable"
            raise CompanyStopped("verification_unavailable",
                                 "Site doğrulama ekranı gösterdi veya korumalı; bu bilgisayarda tarayıcı kullanılamıyor.")
        timeout = GRACE_SECONDS if self.final_timeout is None else self.final_timeout
        with shared.verify_lock:
            try:
                browser = shared.verifier(domain, url, shared.canceled, timeout)
            except CollectionCanceled:
                raise
            except Exception as exc:
                if type(exc).__name__ == "SiteBlocked":
                    raise CompanyStopped("stopped_blocked", f"Site engel sayfası gösterdi ({exc}); şirket durduruldu, yeniden denenmedi.") from None
                if type(exc).__name__ == "BrowserUnavailable":
                    self.result["verification"] = "unavailable"
                    raise CompanyStopped("verification_unavailable", f"Tarayıcı kullanılamıyor: {exc}") from None
                raise
        if browser is None:
            if self.final_timeout is None:
                shared.marks[self.site["domain"]] = {"host": self.site["domain"], "url": url, "reason": "doğrulama sayfası"}
                raise CompanyDeferred(url)
            self.result["verification"] = "timeout"
            raise CompanyStopped("verification_timeout", "Kullanıcı doğrulaması süresinde tamamlanmadı; şirket atlandı.")
        self.browser = browser
        self.session.transport = browser

    def ask(self, call):
        while True:
            try:
                return call()
            except VerificationNeeded as need:
                if self.browser is not None:
                    raise CompanyStopped("stopped_blocked", "Doğrulamadan sonra site yine doğrulama ekranı gösterdi; şirket durduruldu.") from None
                self.shared.marks[self.site["domain"]] = {"host": self.site["domain"], "url": need.url, "reason": "doğrulama sayfası"}
                self.open_browser(need.url)
                self.result["verification"] = "completed"

    # --- phases ------------------------------------------------------------------------------------------------------------

    def run(self):
        site, members, shared = self.site, self.members, self.shared
        try:
            with shared.protected_lock if self.protected else nullcontext():
                if self.protected:
                    first = next((m["listing_url"] for m in members if self.session.allows(m["listing_url"])), None)
                    self.open_browser(first or (site["inventory"] or {}).get("origin") or f"https://www.{site['domain']}/")
                for index, row in enumerate(members):
                    check(shared.canceled)
                    self.link(row)
                    shared.tracker.step(1, f"{site['company']}: {index + 1}/{len(members)} ilan.")
                waiting_rows = [r for r in members if r["page_status"] in FALLBACK_STATUSES]
                if site["inventory"] and (waiting_rows or site["own_region_id"]):
                    units, hashes = read_inventory(self.session, self.adapter, site, self.ask)
                    self.result["inventory_count"], self.result["inventory_raw_sha256"] = len(units), hashes
                    shared.tracker.step(0, f"{site['company']}: şirketin listesinde {len(units)} ilan.")
                    self.fallback(waiting_rows, units)
                    if site["own_region_id"]:
                        self.own_inventory(units)
                if hasattr(self.adapter, "published"):
                    self.published_rents()
        except CompanyDeferred as wait:
            self.deferred = wait.url
            self.result["status"], self.result["message"] = "verification_timeout", "Doğrulama bekleniyor; şirket sona bırakıldı."
        except CompanyStopped as stop:
            self.result["status"], self.result["message"] = stop.status, stop.message
            for row in members:
                if row["page_status"] == "not_queried":
                    row["message"] = stop.message
        except CollectionCanceled:
            raise
        except Exception as exc:      # one company's unexpected failure never stops the others
            self.result["status"], self.result["message"] = "failed", f"Beklenmeyen hata: {type(exc).__name__}: {str(exc)[:200]}"
        finally:
            if self.browser is not None:
                try:
                    self.browser.close()
                except Exception:
                    pass
        self.result.update({"matched_count": sum(r["page_status"] == "matched" for r in members), "quote_count": len(self.quotes),
                            "priced_count": sum(q["status"] == "priced" for q in self.quotes), "request_count": self.session.requests,
                            "own_count": len(self.own_rows),
                            "match_counts": {m: sum(r["match_method"] == m for r in members) for m in MATCH_METHODS}})
        if not self.deferred:
            shared.tracker.step(0, f"{site['company']}: bitti ({self.result['status']}).")
        else:
            shared.tracker.step(0, f"{site['company']}: doğrulama bekliyor, sona bırakıldı.")
        return self

    def skip(self, status, verification, message):
        """A deferred company the user did not verify: nothing is read, the rows say why."""
        self.result.update({"status": status, "verification": verification, "message": message, "matched_count": 0, "quote_count": 0,
                            "priced_count": 0, "request_count": 0, "own_count": 0, "match_counts": {m: 0 for m in MATCH_METHODS}})
        for row in self.members:
            row["message"] = message
        self.deferred = None
        return self

    def quote_once(self, info, window, guests):
        key = (info["site_id"], window["window_key"], guests["adults"], guests["children"])
        if key not in self.cache:
            self.cache[key] = ask_quote(self.session, self.adapter, info, window, self.ask, guests)
            self.errors = self.errors + 1 if self.cache[key]["status"] == "error" else 0
            if self.errors >= ERROR_LIMIT:
                raise CompanyStopped("stopped_errors", f"Fiyat isteği art arda {ERROR_LIMIT} kez başarısız oldu; şirket durduruldu.")
        return self.cache[key]

    def price(self, row, info):
        guests = guests_for(self.site, row["bedrooms"], self.facts[row["lodging_id"]]["sleeps"])
        for window in self.shared.active:
            self.quotes.append({**self.quote_once(info, window, guests), "lodging_id": row["lodging_id"], "window_key": window["window_key"]})

    def link(self, row):
        url = row["listing_url"]
        if url not in self.pages:
            self.pages[url] = open_listing(self.session, self.adapter, url, self.ask)
        page = self.pages[url]
        row.update({k: page[k] for k in ("page_status", "page_url", "http_status", "site_listing_id", "message")})
        row["link_status"] = page["page_status"]
        if page["page_status"] == "blocked":
            # A refused listing page can be one unpublished listing (Drupal answers its themed "Access denied" page)
            # or the whole site refusing us. One look at the site's home page tells them apart.
            if site_answers(self.session, url, self.ask):
                self.blocked = 0
                page["message"] = (f"Bu ilan sayfası erişime kapalı (HTTP {page['http_status']}); sitenin ana sayfası normal yanıt "
                                   "veriyor (ilan yayından kaldırılmış olabilir).")
                row["message"] = page["message"]
            else:
                self.blocked += 1
                if self.blocked >= BLOCK_LIMIT:
                    raise CompanyStopped("stopped_blocked", f"Site art arda {BLOCK_LIMIT} isteği reddetti (HTTP {page['http_status']}); "
                                                            "şirket durduruldu.")
        else:
            self.blocked = 0
        if page["page_status"] == "error":
            self.errors += 1
            if self.errors >= ERROR_LIMIT:
                raise CompanyStopped("stopped_errors", f"Siteye art arda {ERROR_LIMIT} kez ulaşılamadı; şirket durduruldu.")
        elif page["page_status"] != "blocked":
            self.errors = 0
        if page["page_status"] == "matched":
            row["match_method"] = "link"
            self.price(row, page["info"])

    def fallback(self, rows, units):
        """Listings whose link did not reach a listing, tied by the address rule (or, when the company's list has no street
        addresses, by the location rule)."""
        by_address = sum(bool(u.get("address")) for u in units) * 2 >= max(1, len(units))
        for row in rows:
            check(self.shared.canceled)
            facts = self.facts[row["lodging_id"]]
            if by_address:
                kind, unit, note = address_match(facts, units)
                method = "address"
            else:
                kind, unit, note = location_match(facts, units, self.shared.everyone)
                method = "location"
            row["match_note"] = note
            if kind != "matched":
                continue
            page = unit.get("page") or open_listing(self.session, self.adapter, unit["url"], self.ask)
            if page["page_status"] != "matched":
                row["match_note"] = f"{note} Eşleşen şirket ilanının sayfası açılamadı: {page['message']}"
                continue
            row.update({k: page[k] for k in ("page_status", "page_url", "http_status", "site_listing_id")})
            row["message"], row["match_method"] = None, method
            self.price(row, page["info"])

    def own_inventory(self, units):
        """The community's homes from the company's own list that Book>Direct does not show: the community is the configured name
        the site itself gives (its City field); a home the site places elsewhere is left out, and a home already on Book>Direct
        (same company page, same url or the address rule) is not counted twice."""
        site, everyone = self.site, self.shared.everyone
        city = (site["own_city"] or "").strip().lower()
        community = [u for u in units if (u.get("city") or "").strip().lower() == city]
        self.result["own_outside"] = len(units) - len(community)
        matched = {r["site_listing_id"] for r in self.members if r["page_status"] == "matched"}
        on_bookdirect = 0
        for unit in community:
            check(self.shared.canceled)
            if unit["site_id"] in matched or any(same_url(unit["url"], f["url"]) for f in everyone) or any(same_home(unit, f) for f in everyone):
                on_bookdirect += 1
                continue
            page = unit.get("page") or open_listing(self.session, self.adapter, unit["url"], self.ask)
            row = {"domain": site["domain"], "site_listing_id": unit["site_id"], "title": unit.get("title") or unit["url"], "page_url": page["page_url"] or unit["url"],
                   "address": unit.get("address"), "city": unit.get("city"), "region_id": site["own_region_id"], "bedrooms": unit.get("bedrooms"),
                   "bathrooms": unit.get("bathrooms"), "sleeps": unit.get("sleeps"), "latitude": unit.get("latitude"), "longitude": unit.get("longitude"),
                   "page_status": page["page_status"], "message": page["message"]}
            self.own_rows.append(row)
            if page["page_status"] != "matched":
                continue
            guests = guests_for(site, unit.get("bedrooms"), unit.get("sleeps"))
            for window in self.shared.active:
                answer = self.quote_once(page["info"], window, guests)
                self.own_quotes.append({**answer, "domain": site["domain"], "site_listing_id": unit["site_id"], "window_key": window["window_key"]})
        self.result["own_on_bookdirect"] = on_bookdirect

    def published_rents(self):
        """Published seasonal rents for the matched listings of an adapter that reads them (kept apart from the quotes)."""
        seen = {}
        for row in self.members:
            if row["page_status"] != "matched":
                continue
            info = (self.pages.get(row["listing_url"]) or {}).get("info")
            if info is None or info.get("site_id") != row["site_listing_id"]:
                continue
            if info["site_id"] not in seen:
                try:
                    seen[info["site_id"]] = self.ask(lambda: self.adapter.published(self.session, info, self.shared.active))
                except AdapterError as exc:
                    seen[info["site_id"]] = {}
                    row["message"] = f"Yayımlanmış kira okunamadı: {exc}"
            for window_key, entry in seen[info["site_id"]].items():
                self.published.append({**entry, "lodging_id": row["lodging_id"], "window_key": window_key})


def same_home(unit, listing):
    """The address rule between a company list entry and a Book>Direct listing (used so an own-inventory home is not counted twice)."""
    one, two = normalize_address(unit.get("address")), normalize_address(listing.get("address"))
    return one is not None and two is not None and one == two and same_rooms(unit.get("bedrooms"), listing.get("bedrooms"))


def read_inventory(session, adapter, site, ask):
    """The company's own listing list, read again on every run: the platform's list service, or the listing pages its sitemap
    names. Returns (units, raw SHA-256 of every response read for it)."""
    options = site["inventory"]
    before = session.store.count
    if options.get("source") == "platform":
        if not hasattr(adapter, "inventory"):
            raise AdapterError(f"{adapter.name} uyarlayıcısı şirket listesini okuyamıyor.")
        units, _ = ask(lambda: adapter.inventory(session, options["origin"].rstrip("/"), options))
    elif options.get("source") == "sitemap":
        units = sitemap_inventory(session, adapter, options, ask)
    else:
        raise AdapterError(f"Bilinmeyen şirket listesi kaynağı: {options.get('source')}.")
    with session.store.lock:
        hashes = [entry["raw_sha256"] for entry in session.store.manifest["responses"][before:] if entry["company"] == session.domain]
    return units, hashes


def sitemap_inventory(session, adapter, options, ask):
    """Listing pages named by the sitemap (a sitemap index is followed one level), filtered by the configured url pattern; each
    page gives the platform identity (parse_page) and the listing's details (unit_fields, else schema.org JSON-LD)."""
    pattern = re.compile(options["pattern"])
    urls, queue, seen_maps = [], [options["url"]], set()
    while queue and len(seen_maps) < 12:
        current = queue.pop(0)
        if current in seen_maps:
            continue
        seen_maps.add(current)
        reply = ask(lambda: session.request("GET", current, note="inventory-sitemap", headers={"Accept": "application/xml,text/xml,*/*"}))
        if reply.status != 200:
            raise AdapterError(f"Site haritası HTTP {reply.status} döndü.")
        locations = [loc.strip() for loc in re.findall(r"<loc>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</loc>", reply.text, re.S)]
        if "<sitemapindex" in reply.text:
            queue.extend(loc for loc in locations if re.search(options.get("sitemap_pattern") or ".", loc))
            continue
        urls.extend(loc for loc in locations if pattern.search(loc) and loc not in urls)
    units = []
    for url in urls[:MAX_INVENTORY_PAGES]:
        check(session.canceled)
        page = open_listing(session, adapter, url, ask, keep_html=True)
        if page["page_status"] != "matched":
            continue
        html = page.pop("html", "")
        fields = adapter.unit_fields(html) if hasattr(adapter, "unit_fields") else json_ld_unit(html)
        units.append({"site_id": page["site_listing_id"], "url": page["page_url"], "title": fields.get("title"), "address": fields.get("address"),
                      "city": fields.get("city"), "latitude": fields.get("latitude"), "longitude": fields.get("longitude"),
                      "bedrooms": fields.get("bedrooms"), "bathrooms": fields.get("bathrooms"), "sleeps": fields.get("sleeps"), "page": page})
    return units


def open_listing(session, adapter, url, ask, keep_html=False):
    """GET the company listing page and let the adapter find its platform identity there (keep_html: also return the page text)."""
    base = {"page_url": None, "http_status": None, "site_listing_id": None, "message": None, "info": None}
    if not session.allows(url):
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
        title = re.search(r"<title[^>]*>([^<]*)</title>", reply.text[:200_000], re.I)
        if title and SOFT_404.search(title.group(1)):
            return {**base, "page_status": "not_found", "message": f"Şirket sitesi 'sayfa bulunamadı' sayfası döndürdü (HTTP 200, başlık: "
                                                                   f"{title.group(1).strip()[:80]})."}
        return {**base, "page_status": "no_listing", "message": "Sayfada bu altyapının ilan kimliği yok; bağlantı ilan sayfasına gitmiyor olabilir."}
    info["page_sha256"] = reply.sha256          # an answer read from the page itself (e.g. its calendar) cites this response
    info.setdefault("page_url", reply.url)
    return {**base, "page_status": "matched", "site_listing_id": info["site_id"], "info": info, **({"html": reply.text} if keep_html else {})}


def site_answers(session, url, ask):
    """True when the company's home page still answers 200, i.e. a refused listing page is not the whole site refusing us."""
    parts = urlsplit(url)
    try:
        reply = ask(lambda: session.request("GET", f"{parts.scheme}://{parts.netloc}/", note="site-check", headers={"Accept": "text/html"}))
    except AdapterError:
        return False
    return reply.status == 200 and not reply.location


def ask_quote(session, adapter, info, window, ask, guests=DEFAULT_GUESTS):
    started = datetime.now(timezone.utc).isoformat()
    try:
        answer = ask(lambda: adapter.quote(session, info, window, guests))
    except AdapterError as exc:
        answer = {"status": "error", "available": None, "message": str(exc), "replies": []}
    replies = answer.pop("replies", [])
    sent = getattr(adapter, "sends_guests", True)
    row = {"status": answer["status"], "available": answer.get("available"), "nightly_rates": answer.get("nightly_rates"),
           "rent": answer.get("rent"), "cleaning_fee": answer.get("cleaning_fee"), "other_fees": answer.get("other_fees"),
           "fees": answer.get("fees"), "taxes": answer.get("taxes"), "tax_items": answer.get("tax_items"), "total": answer.get("total"),
           "total_includes_fees": answer.get("total_includes_fees"), "total_includes_taxes": answer.get("total_includes_taxes"),
           "excluded_items": answer.get("excluded_items"), "currency": answer.get("currency"), "min_stay": answer.get("min_stay"),
           "checkin_days": answer.get("checkin_days"), "rule_source": answer.get("rule_source"), "message": answer.get("message"),
           "adults": guests["adults"] if sent else None, "children": guests["children"] if sent else None,
           "queried_at": started, "queried_url": replies[-1].url if replies else info.get("page_url"),
           "raw_sha256": [reply.sha256 for reply in replies] or ([info["page_sha256"]] if info.get("page_sha256") else [])}
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


def guest_label(companies):
    """How many guests the prices were asked for, from the company rows of the run."""
    doubled = sorted(c["company"] for c in companies if c.get("guest_rule") == "bedrooms_x2")
    if not doubled:
        return "Fiyatlar 2 yetişkin için soruldu (sitenin fiyat isteği misafir sayısı sormuyorsa misafir sayısı boş kalır)."
    return (f"Fiyatlar 2 yetişkin için soruldu; {', '.join(doubled)} sitelerinde misafir sayısı fiyatı değiştirdiği için "
            "'yatak odası × 2 yetişkin, ilan kapasitesini aşmadan' soruldu.")


def cell_stats(pairs, nights):
    """pairs: [(bedrooms, quote)] of one region x window -> counts, total quartiles, nightly rent quartiles and bedroom medians."""
    priced = [(b, q) for b, q in pairs if q["status"] == "priced" and q["total"] is not None]
    known = [q for _, q in pairs if q["available"] is not None]
    totals = [q["total"] for _, q in priced]
    nightly = [round(q["rent"] / nights, 2) for _, q in priced if q["rent"] is not None]
    q1, median, q3 = quartiles(totals)
    n1, nmedian, n3 = quartiles(nightly)
    buckets = {}
    for name, _, _ in BEDROOM_BUCKETS:
        values = [q["total"] for b, q in priced if bucket_of(b) == name]
        buckets[name] = {"count": len(values), "median": round(statistics.median(values), 2) if values else None}
    return {"queried_count": len(pairs), "priced_count": len(priced), "priced_share": round(len(priced) / len(pairs), 3) if pairs else None,
            "available_known": len(known), "available_share": round(sum(q["available"] for q in known) / len(known), 3) if known else None,
            "total_q1": q1, "total_median": median, "total_q3": q3, "nightly_q1": n1, "nightly_median": nmedian, "nightly_q3": n3,
            "bedrooms": buckets}


def summarize(con, run_id, region_order=(), region_names=None):
    snapshot = con.execute("SELECT * FROM agency_rate_snapshots WHERE run_id=?", (run_id,)).fetchone()
    if not snapshot:
        return None
    windows = [dict(r) for r in con.execute("SELECT * FROM agency_rate_windows WHERE run_id=? ORDER BY checkin", (run_id,))]
    listings = {r["lodging_id"]: decode_listing(r) for r in con.execute("SELECT * FROM agency_rate_listings WHERE run_id=?", (run_id,))}
    quotes = [decode_quote(r) for r in con.execute("SELECT * FROM agency_rate_quotes WHERE run_id=?", (run_id,))]
    companies = [decode_company(r) for r in con.execute("SELECT * FROM agency_rate_companies WHERE run_id=? ORDER BY listing_count DESC, domain", (run_id,))]
    own = [dict(r) for r in con.execute("SELECT * FROM agency_rate_own_listings WHERE run_id=?", (run_id,))]
    own_quotes = [decode_quote(r) for r in con.execute("SELECT * FROM agency_rate_own_quotes WHERE run_id=?", (run_id,))]
    published = [dict(r) for r in con.execute("SELECT * FROM agency_rate_published WHERE run_id=?", (run_id,))]
    by_window, own_by_window, published_by_window = {}, {}, {}
    for quote in quotes:
        by_window.setdefault(quote["window_key"], {})[quote["lodging_id"]] = quote
    for quote in own_quotes:
        own_by_window.setdefault(quote["window_key"], {})[(quote["domain"], quote["site_listing_id"])] = quote
    for row in published:
        published_by_window.setdefault(row["window_key"], {})[row["lodging_id"]] = row
    region_ids = {region for listing in listings.values() for region in listing["region_ids"]} | {o["region_id"] for o in own}
    order = {region: index for index, region in enumerate(region_order)}
    regions = sorted(region_ids, key=lambda r: (order.get(r, len(order)), r))
    names = region_names or {}
    cells = []
    for region in regions:
        members = [l for l in listings.values() if region in l["region_ids"]]
        homes = [o for o in own if o["region_id"] == region]
        for window in windows:
            cell = {"region_id": region, "window_key": window["window_key"], "status": window["status"], "listing_count": len(members),
                    "linked_count": sum(m["domain"] is not None for m in members), "own_listing_count": len(homes)}
            if window["status"] == "queried":
                asked = [(m, by_window.get(window["window_key"], {}).get(m["lodging_id"])) for m in members]
                asked = [(m, q) for m, q in asked if q is not None]
                cell.update(cell_stats([(m["bedrooms"], q) for m, q in asked], window["nights"]))
                cell["by_method"] = {method: sum(1 for m, q in asked if m["match_method"] == method and q["status"] == "priced" and q["total"] is not None)
                                     for method in MATCH_METHODS}
                own_pairs = [(o["bedrooms"], own_by_window.get(window["window_key"], {}).get((o["domain"], o["site_listing_id"]))) for o in homes]
                own_stats = cell_stats([(b, q) for b, q in own_pairs if q is not None], window["nights"])
                cell["own"] = {k: own_stats[k] for k in ("queried_count", "priced_count", "total_q1", "total_median", "total_q3", "available_share")}
                rents = [published_by_window.get(window["window_key"], {}).get(m["lodging_id"]) for m in members]
                rents = [r for r in rents if r is not None]
                cell["published"] = {"count": len(rents),
                                     "low_median": round(statistics.median(r["rent_low"] for r in rents), 2) if rents else None,
                                     "high_median": round(statistics.median(r["rent_high"] for r in rents), 2) if rents else None}
            cells.append(cell)
    windows = annotate_windows(windows, snapshot["queried_on"])
    totals = {}
    for region in regions:
        for window in windows:
            totals[(region, window["window_key"])] = [q["total"] for q in by_window.get(window["window_key"], {}).values()
                                                      if q["status"] == "priced" and q["total"] is not None
                                                      and region in listings.get(q["lodging_id"], {}).get("region_ids", ())]
    seasons = season_groups(regions, windows, totals)
    comparison = previous_comparison(con, run_id, regions, listings, windows, by_window, snapshot["queried_on"])
    coverage = {name: sum(l["page_status"] == name for l in listings.values()) for name in PAGE_STATUSES}
    methods = {method: sum(l["match_method"] == method for l in listings.values()) for method in MATCH_METHODS}
    priced_ids = {q["lodging_id"] for q in quotes if q["status"] == "priced"}
    regions_priced = {r for l in listings.values() if l["lodging_id"] in priced_ids for r in l["region_ids"]}
    own_priced = {(q["domain"], q["site_listing_id"]) for q in own_quotes if q["status"] == "priced"}
    return {"snapshot": dict(snapshot), "windows": windows, "regions": [{"region_id": r, "region_name": names.get(r, r)} for r in regions],
            "cells": cells, "companies": companies, "seasons": seasons, "comparison": comparison,
            "coverage": {**coverage, "listings": len(listings), "priced_listings": len(priced_ids), "regions": len(regions),
                         "regions_with_price": len(regions_priced), "methods": methods, "own_listings": len(own), "own_priced": len(own_priced),
                         "published": len({r["lodging_id"] for r in published})},
            "label": total_label(quotes + own_quotes, snapshot["queried_on"]), "guest_label": guest_label(companies),
            "source_note": ("Fiyatlı ilanlar Book>Direct ilanlarıdır (eşleme yöntemi: bağlantı, adres veya konum); 'kendi envanteri' "
                            "sütunu tek bir topluluğun resmî kiralama programında Book>Direct'te olmayan evleri ayrı sayar."),
            "published_note": "Yayımlanmış kira: sitenin sezon için yayımladığı kira aralığı × gece sayısı; vergi ve ücretler hariç, toplam fiyat ortancalarına karışmaz.",
            "nightly_note": "Gecelik ortalama = sitenin kira tutarı ÷ gece sayısı (bizim hesabımız; ücret ve vergiler hariç).",
            "bedroom_note": "Oda sayısı Book>Direct ilanından; 1–2 grubuna stüdyolar dahildir. Ortancalar 7 gecelik toplam fiyattandır."}


def run_totals(con, run_id):
    """Windows and the priced 7-night totals {(lodging_id, window_key): total} of one run."""
    windows = [dict(r) for r in con.execute("SELECT * FROM agency_rate_windows WHERE run_id=? AND status='queried' ORDER BY checkin", (run_id,))]
    prices = {(r["lodging_id"], r["window_key"]): r["total"] for r in con.execute(
        "SELECT lodging_id, window_key, total FROM agency_rate_quotes WHERE run_id=? AND status='priced' AND total IS NOT NULL", (run_id,))}
    return windows, prices


def previous_comparison(con, run_id, regions, listings, windows, by_window, queried_on):
    """The same-week comparison with the latest earlier successful run of the destination that asked at least one same week."""
    current = con.execute("SELECT rowid, destination_id FROM source_runs WHERE id=?", (run_id,)).fetchone()
    if not current:
        return None
    dates = {(w["checkin"], w["checkout"]) for w in windows if w["status"] == "queried"}
    for row in con.execute("""SELECT s.run_id, s.queried_on FROM agency_rate_snapshots s JOIN source_runs r ON r.id=s.run_id
            WHERE r.status='done' AND r.destination_id=? AND r.rowid<? ORDER BY r.rowid DESC""", (current["destination_id"], current["rowid"])):
        earlier_windows, earlier_prices = run_totals(con, row["run_id"])
        if not dates & {(w["checkin"], w["checkout"]) for w in earlier_windows}:
            continue
        later_prices = {(lodging_id, key): q["total"] for key, quotes in by_window.items() for lodging_id, q in quotes.items()
                        if q["status"] == "priced" and q["total"] is not None}
        members = {region: {l["lodging_id"] for l in listings.values() if region in l["region_ids"]} for region in regions}
        result = compare(regions, {"windows": earlier_windows, "prices": earlier_prices},
                         {"windows": [w for w in windows if w["status"] == "queried"], "prices": later_prices, "members": members},
                         row["queried_on"], queried_on)
        return {**result, "earlier_run_id": row["run_id"], "earlier_queried_on": row["queried_on"], "basis": "7 gecelik toplam (sitenin)"}
    return None


def region_listings(con, run_id, region_id):
    if not con.execute("SELECT 1 FROM agency_rate_snapshots WHERE run_id=?", (run_id,)).fetchone():
        return None
    quotes, published = {}, {}
    for row in con.execute("SELECT * FROM agency_rate_quotes WHERE run_id=?", (run_id,)):
        quotes.setdefault(row["lodging_id"], {})[row["window_key"]] = decode_quote(row)
    for row in con.execute("SELECT * FROM agency_rate_published WHERE run_id=?", (run_id,)):
        published.setdefault(row["lodging_id"], {})[row["window_key"]] = decode_published(row)
    result = []
    for row in con.execute("SELECT l.*, c.company, c.adapter FROM agency_rate_listings l LEFT JOIN agency_rate_companies c ON c.run_id=l.run_id AND c.domain=l.domain "
                           "WHERE l.run_id=? ORDER BY l.title, l.lodging_id", (run_id,)):
        listing = decode_listing(row)
        if region_id in listing["region_ids"]:
            result.append({**listing, "quotes": quotes.get(listing["lodging_id"], {}), "published": published.get(listing["lodging_id"], {})})
    own_quotes = {}
    for row in con.execute("SELECT * FROM agency_rate_own_quotes WHERE run_id=?", (run_id,)):
        own_quotes.setdefault((row["domain"], row["site_listing_id"]), {})[row["window_key"]] = decode_quote(row)
    own = [{**dict(row), "quotes": own_quotes.get((row["domain"], row["site_listing_id"]), {})}
           for row in con.execute("SELECT o.*, c.company, c.adapter FROM agency_rate_own_listings o LEFT JOIN agency_rate_companies c "
                                  "ON c.run_id=o.run_id AND c.domain=o.domain WHERE o.run_id=? AND o.region_id=? ORDER BY o.title", (run_id, region_id))]
    return {"listings": result, "own": own}


def decode_listing(row):
    result = dict(row)
    result["region_ids"] = json.loads(result["region_ids"])
    return result


def decode_quote(row):
    result = dict(row)
    for key in ("nightly_rates", "fees", "tax_items", "excluded_items", "checkin_days", "raw_sha256"):
        result[key] = json.loads(result[key]) if result.get(key) is not None else None
    return result


def decode_company(row):
    result = dict(row)
    result["inventory_raw_sha256"] = json.loads(result["inventory_raw_sha256"]) if result.get("inventory_raw_sha256") else None
    result["match_counts"] = json.loads(result["match_counts"]) if result.get("match_counts") else None
    return result


def decode_published(row):
    result = dict(row)
    result["raw_sha256"] = json.loads(result["raw_sha256"])
    return result


def dumps(value):
    return None if value is None else json.dumps(value, ensure_ascii=False)


QUOTE_COLUMNS = ("status", "available", "nightly_rates", "rent", "cleaning_fee", "other_fees", "fees", "taxes", "tax_items", "total",
                 "total_includes_fees", "total_includes_taxes", "excluded_items", "currency", "min_stay", "checkin_days", "rule_source", "message",
                 "adults", "children", "queried_at", "queried_url", "raw_sha256")
JSON_QUOTE_COLUMNS = {"nightly_rates", "fees", "tax_items", "excluded_items", "checkin_days"}


def quote_values(quote):
    return tuple(json.dumps(quote[c]) if c == "raw_sha256" else dumps(quote[c]) if c in JSON_QUOTE_COLUMNS else quote[c] for c in QUOTE_COLUMNS)


class AgencyRatesConnector:
    name = "agency-lodging-rates"
    version = CONNECTOR_VERSION
    raw_filename = "manifest.json"
    method = "HTML/JSON"
    diff_enabled = False
    diff_reason = "Kiralama şirketi fiyatları tarihe bağlı sorgulardır; sürümler arası fark envanter değişikliği sayılmamalı."
    inputs = ("lodging_listings",)
    uses_verification = True
    verify_minutes = VERIFY_TIMEOUT // 60

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
        return collect(raw_path, progress, canceled, config={**agency, "windows": lodging["windows"], "window_rule": lodging.get("window_rule"), "browser_hosts": context.browser_hosts},
                       verifier=verifier, waiting=waiting)

    def store_records(self, con, run_id, records, related=None):
        snapshot = related["snapshot"]
        con.execute("INSERT INTO agency_rate_snapshots (run_id,lodging_run_id,queried_on,request_count,listing_count) VALUES (?,?,?,?,?)",
                    (run_id, snapshot["lodging_run_id"], snapshot["queried_on"], snapshot["request_count"], snapshot["listing_count"]))
        con.executemany("INSERT INTO agency_rate_windows (run_id,window_key,label,checkin,checkout,nights,status) VALUES (?,?,?,?,?,?,?)",
                        [(run_id, w["window_key"], w["label"], w["checkin"], w["checkout"], w["nights"], w["status"]) for w in related["windows"]])
        con.executemany("""INSERT INTO agency_rate_companies (run_id,domain,company,adapter,status,listing_count,matched_count,quote_count,priced_count,
            request_count,verification,message,protected,guest_rule,inventory_count,inventory_raw_sha256,own_count,own_outside,own_on_bookdirect,
            match_counts) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, c["domain"], c["company"], c["adapter"], c["status"], c["listing_count"], c["matched_count"], c["quote_count"], c["priced_count"],
              c["request_count"], c["verification"], c["message"], c["protected"], c["guest_rule"], c["inventory_count"],
              dumps(c["inventory_raw_sha256"]), c["own_count"], c["own_outside"], c["own_on_bookdirect"], dumps(c["match_counts"]))
             for c in related["companies"]])
        con.executemany("""INSERT INTO agency_rate_listings (run_id,lodging_id,title,bedrooms,region_ids,listing_url,url_host,domain,page_status,page_url,
            http_status,site_listing_id,message,link_status,match_method,match_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, r["lodging_id"], r["title"], r["bedrooms"], json.dumps(r["region_ids"]), r["listing_url"], r["url_host"], r["domain"],
              r["page_status"], r["page_url"], r["http_status"], r["site_listing_id"], r["message"], r["link_status"], r["match_method"],
              r["match_note"]) for r in records])
        con.executemany(f"INSERT INTO agency_rate_quotes (run_id,lodging_id,window_key,{','.join(QUOTE_COLUMNS)}) VALUES (?,?,?{',?' * len(QUOTE_COLUMNS)})",
                        [(run_id, q["lodging_id"], q["window_key"], *quote_values(q)) for q in related["quotes"]])
        con.executemany("""INSERT INTO agency_rate_own_listings (run_id,domain,site_listing_id,title,page_url,address,city,region_id,bedrooms,bathrooms,
            sleeps,latitude,longitude,page_status,message) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, o["domain"], o["site_listing_id"], o["title"], o["page_url"], o["address"], o["city"], o["region_id"], o["bedrooms"],
              o["bathrooms"], o["sleeps"], o["latitude"], o["longitude"], o["page_status"], o["message"]) for o in related.get("own_listings", [])])
        con.executemany(f"INSERT INTO agency_rate_own_quotes (run_id,domain,site_listing_id,window_key,{','.join(QUOTE_COLUMNS)}) "
                        f"VALUES (?,?,?,?{',?' * len(QUOTE_COLUMNS)})",
                        [(run_id, q["domain"], q["site_listing_id"], q["window_key"], *quote_values(q)) for q in related.get("own_quotes", [])])
        con.executemany("""INSERT INTO agency_rate_published (run_id,lodging_id,window_key,season_start,season_end,rate_text,rate_period,rent_low,rent_high,
            basis,source_url,raw_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, p["lodging_id"], p["window_key"], p["season_start"], p["season_end"], p["rate_text"], p["rate_period"], p["rent_low"],
              p["rent_high"], p["basis"], p["source_url"], json.dumps(p["raw_sha256"])) for p in related.get("published", [])])
        mark_hosts(con, related.get("browser_hosts", []), CONNECTOR_VERSION)

    def read_records(self, con, run_id):
        return [decode_listing(r) for r in con.execute("SELECT * FROM agency_rate_listings WHERE run_id=? ORDER BY title, lodging_id", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Agency rate diff is disabled.")


def default_verifier():
    """The computer's browser when Playwright and Chrome/Edge are installed; None otherwise (a verification page then skips that
    company)."""
    from .browser_verification import BrowserVerifier, available
    return BrowserVerifier() if available() else None
