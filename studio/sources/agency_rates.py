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

GÖREV-22: a company whose site gives no street address and only rounded coordinates cannot be tied to Book>Direct listings; its
homes are read as "the company's own inventory" across the neighbourhoods (`inventory.own` of the company's configuration): the
neighbourhood is only the one the site itself names for the home, a home whose site names none stays without a neighbourhood
(counted apart, never in a neighbourhood's medians), and a home that is also a Book>Direct listing is not counted twice. A company
whose old Book>Direct links are known to be dead (`inventory.dead_links`) is not asked for them. A Book>Direct link that names a
unit number the company's own list gives for exactly one home (its present or former number) ties the listing to that home
("link"). Of a region-blocked company only the listed domains go through the user's US proxy; its other domains go directly.

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
from .browser_verification import GRACE_SECONDS, host_key, mark_hosts, record_methods
from .bookdirect_lodging import is_front_host, quartiles
from .climate_http import check, pause
from .price_history import annotate_windows, compare, season_groups
from .windows import monthly_windows

CONNECTOR_VERSION = "agency-lodging-rates/2"
SOURCE_QUERY = "kaynak=kiralama-sirketleri"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36 "
              "30AStudio/0.12 (+https://github.com/bemonths/tatilya)")
REQUEST_GAP = 8.0           # HEDEF-01: seconds between two requests of one worker to the same company site (at least 8 s)
PROTECTED_GAP = 8.0         # the same for a protected site (Cloudflare and kin), read in the browser lane
WORKERS = 3                 # GÖREV-22 estimate only (the old three companies side by side); runs use studio/sources/agency_workers.py
RETRY_PAUSE = 5.0
BLOCK_LIMIT = 3             # consecutive refusals (401/403/429, no verification page) that stop a company; see site_answers()
ERROR_LIMIT = 5             # consecutive unreachable/failed requests that stop a company
# HEDEF-03: inside the extension a site may ask again for its verification during a long read (RealJoy, 27 Nov 2026: Cloudflare after
# 30 minutes). The extension's tab then opens the company's page again (the user passes the check there if it asks them; the extension
# waits for them as on the first page) and the question is asked once more; at most this many times per company and run.
REVERIFY_LIMIT = 12
VERIFY_TIMEOUT = 15 * 60
RETRY_AFTER_MAX = 60 * 60   # GÖREV-25: the longest Retry-After a 429 rule waits
EXTENSION_ONLY_SKIP = ("Eklenti bağlı değil: bu şirket yalnız tarayıcı eklentisiyle (sitenin kendi sorgularıyla) okunur; programın kendi "
                       "tarayıcısı bu sorguları göndermez. Şirket bu çekimde atlandı.")
MAX_BYTES = 8_000_000
MAX_REDIRECTS = 5
MAX_INVENTORY_PAGES = 400   # listing pages read from one company's sitemap
PROGRESS_EVERY = 2.0
# Interstitial human-verification pages only (Cloudflare, PerimeterX). An ordinary page that merely contains a CAPTCHA widget
# (a contact form, a Drupal "Access denied" page) is not a verification page.
CHALLENGE = re.compile(r"<title>\s*Just a moment\.\.\.|cf_chl_opt|/cdn-cgi/challenge-platform/h/[a-z]/orchestrate/|Checking your browser before|"
                       r"Checking if the site connection is secure|px-captcha|Press &amp; Hold|Press & Hold"
                       r"|<title>\s*Quick security check|challenge\.icoastalnet\.com", re.I)      # HEDEF-01: the Track sites' own check (26 Nov 2026)
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
        self.hops = []                 # GÖREV-22: every address asked on the way to this answer (the first one and each redirect)

    @property
    def text(self):
        return self.body.decode("utf-8", errors="replace")


class HttpTransport:
    """Plain HTTPS with httpx; redirects are followed by the session so every hop is kept."""

    kind = "http"

    def __init__(self, client, kind=None, proxied=None):
        self.client = client
        self.base_kind = self.kind
        if kind:
            self.kind = self.base_kind = kind     # GÖREV-16: "proxy" for a region-blocked company through the user's US proxy
        self.proxied = proxied                    # GÖREV-22: url -> True when this request goes through the proxy (the listed domains only)

    def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
        if self.proxied is not None:              # a request to a domain off the list (an alias the links start at) goes directly
            self.kind = self.base_kind if self.proxied(url) else HttpTransport.kind
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

    def save(self, *, company, transport, method, requested, status, final_url, headers, body, note, request_body, location=None):
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
            if location:
                self.manifest["responses"][-1]["location"] = location     # HEDEF-02: a redirect's target (the replay follows it)
            if "proxy" in str(transport):
                self.manifest["responses"][-1]["proxy"] = True        # GÖREV-16: read through the user's US proxy
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

    def __init__(self, store, domain, transport, canceled, *, allowed=(), gap=None, protected=False, retry_429=None):
        self.store, self.domain, self.transport, self.canceled = store, domain, transport, canceled
        self.allowed = (domain, *allowed)
        self.gap = REQUEST_GAP if gap is None else gap
        self.protected = protected
        self.retry_429 = retry_429 if isinstance(retry_429, dict) else None    # GÖREV-25: {"wait_s", "retries"} from the configuration
        self.last = None
        self.requests = 0
        self.on_event = None       # HEDEF-01: (kind) -> None; a 429, a block page or a verification page slows every worker of the site
        self.on_request = None     # HEDEF-01: () -> None; the worker's "last seen" for the stall check

    def event(self, kind):
        if self.on_event is not None:
            self.on_event(kind)

    def allows(self, url):
        return any(on_domain(url, domain) for domain in self.allowed)

    def wait(self, seconds):
        """The pacing and a 429's wait; a replay from the raw copy (HEDEF-02) goes to no site and does not wait."""
        if getattr(self.store, "replay", False):
            check(self.canceled)
            return
        pause(seconds, self.canceled)

    def request(self, method, url, *, note, params=None, data=None, json=None, headers=None):
        if not self.allows(url):
            raise AdapterError("Uyarlayıcı şirketin alan adı dışındaki bir adrese istek yapmak istedi; yapılmadı.")
        current, hops, asked, refused = url, 0, [], 0
        while True:
            asked.append(str(httpx.URL(current, params=params)) if params else current)
            check(self.canceled)
            if self.last is not None:
                self.wait(max(0.0, self.gap - (time.monotonic() - self.last)))
            try:
                status, final, response_headers, body = self.send(method, current, params=params, data=data, json_body=json, headers=headers)
            finally:
                self.last = time.monotonic()
            self.requests += 1
            if self.on_request is not None:
                self.on_request()
            requested = str(httpx.URL(current, params=params)) if params else current
            lowered = {k.lower(): v for k, v in response_headers.items()}
            digest, _ = self.store.save(company=self.domain, transport=self.transport.kind, method=method, requested=requested,
                                        status=status, final_url=final, headers=response_headers, body=body, note=note,
                                        request_body=data if data is not None else json,
                                        location=urljoin(final, lowered["location"]) if status in (301, 302, 303, 307, 308)
                                        and lowered.get("location") else None)
            reply = Reply(status, final, lowered, body, digest)
            reply.hops = list(asked)
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
                self.event("doğrulama sayfası")
                raise VerificationNeeded(current)
            if status == 429:
                self.event("HTTP 429")
            elif status in (403, 503) and BLOCK_PAGE.search(head):
                self.event("engel sayfası")
            if status == 429 and self.retry_429:
                # GÖREV-25: wait what the site asks (Retry-After) or at least wait_s, ask again at most `retries` times; a 429 after
                # that stops the company for this run (what it gave so far is kept)
                if refused < int(self.retry_429.get("retries", 2)):
                    refused += 1
                    self.wait(retry_after(lowered.get("retry-after"), float(self.retry_429.get("wait_s", 60))))
                    self.last = time.monotonic() - self.gap
                    continue
                raise CompanyStopped("stopped_blocked", f"Site art arda {refused + 1} kez HTTP 429 (çok fazla istek) döndü; her seferinde "
                                                        "beklenip yeniden sorulduktan sonra şirket bu çekimde durduruldu, o ana kadarki "
                                                        "sonuçlar saklandı.")
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
                self.wait(RETRY_PAUSE)


def retry_after(value, least):
    """Seconds to wait after a 429: the site's Retry-After (seconds or an HTTP date), else `least` (GÖREV-25)."""
    text = str(value or "").strip()
    if text.isdigit():
        return min(float(text), RETRY_AFTER_MAX)
    if text:
        from email.utils import parsedate_to_datetime
        try:
            return min(max(0.0, (parsedate_to_datetime(text) - datetime.now(timezone.utc)).total_seconds()), RETRY_AFTER_MAX)
        except (TypeError, ValueError):
            pass
    return least


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
            "protected_config": int(site.get("protected") or 0),
            "guest_rule": site.get("guest_rule") or "two_adults", "inventory": loaded(site.get("inventory"), None),
            "own_region_id": site.get("own_region_id"), "own_city": site.get("own_city")}


QUOTE_REQUESTS = 2          # requests assumed per price question on a company no run has measured yet (availability, then price)
ANSWER_SECONDS = 1.0        # time assumed for one answer besides the gap between two requests


def own_everywhere(site):
    """The `inventory.own` options of a company read as its own inventory across the neighbourhoods (GÖREV-22), else None."""
    own = (site.get("inventory") or {}).get("own")
    return own if isinstance(own, dict) else None


def new_site_estimate(sites, listings, read_domains, window_count, region_hosts=()):
    """What the enabled companies no earlier run read add to a run (GÖREV-20): per company its Book>Direct listings, the requests
    (per listing the adapter's `page_requests` to open its link — none when the company's links are known to be dead — and its
    `listing_requests`, e.g. a calendar; per listing and window its `quote_requests`; one page, none and QUOTE_REQUESTS unless the
    adapter says otherwise) and the seconds at the company's own pace. GÖREV-22: a region-blocked company is paced as the proxy is
    (PROXY_GAP); a company read as its own inventory adds the homes its configuration expects (`inventory.own.expected_homes`, one
    page each); a company whose prices are not asked adds no price request; where the configuration says how many of the
    listings are expected to tie to a home (`inventory.expected_matches`, from a trial against the company's list), only that many
    ask the calendar and the prices. Our estimate, an upper bound: a listing that ties to no home asks nothing more,
    a window the site's calendar shows as taken is not asked, and a company may be stopped at its first refusal."""
    listed = {host_key(h) for h in region_hosts or ()}
    added = []
    for site in sites:
        if not site["enabled"] or site["domain"] in read_domains:
            continue
        options = site_options(site)
        adapter = ADAPTERS.get(options["adapter"])
        hosts = (options["domain"], *options["aliases"])
        count = sum(1 for item in listings if (host := site_domain(item.get("url"))) and any(host == h or host.endswith("." + h) for h in hosts))
        own = own_everywhere(options)
        asked = not own or own.get("quotes", True)
        pages = 0 if (options["inventory"] or {}).get("dead_links") else getattr(adapter, "page_requests", 1)
        extra = getattr(adapter, "listing_requests", 0) if asked else 0
        per_window = getattr(adapter, "quote_requests", QUOTE_REQUESTS) if asked else 0
        tied = min(count, int((options["inventory"] or {}).get("expected_matches", count)))
        requests = count * pages + tied * (extra + window_count * per_window)
        homes = int(own.get("expected_homes") or 0) if own else 0
        requests += homes * (1 + extra + window_count * per_window)
        if has_list(options["inventory"]) and (count or homes):      # GÖREV-25: the company's own list read on the run (e.g. RealJoy's parts of 12)
            requests += getattr(adapter, "inventory_requests", 0)
        region = any(host_key(h) in listed for h in hosts)
        gap = max(PROTECTED_GAP if options["protected"] else REQUEST_GAP, PROXY_GAP if region else 0,
                  float((options["inventory"] or {}).get("gap_s") or 0))
        added.append({"domain": options["domain"], "company": options["company"], "listings": count, "own_homes": homes, "requests": requests,
                      "seconds": int(requests * (gap + ANSWER_SECONDS)), "protected": bool(options["protected"]), "proxy": region})
    return added


def added_run_seconds(last_seconds, last_companies, added, workers=None):
    """The seconds the added companies add to a run (GÖREV-22). Companies are read side by side (WORKERS at a time, protected ones
    one at a time), so a new company does not simply lengthen the run by its own time: the last run's companies (their requests at
    their own pace, in the run's order) are laid out on the workers with and without the new ones, and the last run's real duration
    is scaled by the ratio of the two. `last_companies`: rows with domain, listing_count, request_count, protected. Our estimate;
    the plain sum when the last run gives nothing to scale."""
    workers = workers or WORKERS

    def span(jobs):
        free, lock, end = [0.0] * workers, 0.0, 0.0
        for _, _, seconds, protected in sorted(jobs, key=lambda job: (-job[0], job[1])):
            slot = min(range(workers), key=free.__getitem__)
            start = max(free[slot], lock) if protected else free[slot]
            free[slot] = start + seconds
            lock = free[slot] if protected else lock
            end = max(end, free[slot])
        return end

    old = [(c["listing_count"], c["domain"], c["request_count"] * ((PROTECTED_GAP if c.get("protected") else REQUEST_GAP) + ANSWER_SECONDS),
            bool(c.get("protected"))) for c in last_companies]
    new = old + [(a["listings"], a["domain"], a["seconds"], a["protected"]) for a in added]
    before = span(old)
    if not last_seconds or before <= 0:
        return sum(a["seconds"] for a in added)
    return max(0, int(last_seconds * span(new) / before) - int(last_seconds))


def worker_companies(sites, last_companies, added, region_hosts=(), window_ratio=1.0):
    """The companies of a run as the worker estimate sees them (HEDEF-01): per company its requests (the last run's, scaled by the
    window ratio; a company configured since then: `new_site_estimate`), a worker's gap on its site, its tasks (listings), its lane
    (browser companies are not split) and whether it is region-blocked."""
    listed = {host_key(h) for h in region_hosts or ()}
    configured = {s["domain"]: site_options(s) for s in sites if s.get("enabled", 1)}
    out = []

    def shape(domain, requests, units, protected):
        options = configured.get(domain) or {"aliases": [], "inventory": None, "protected": protected, "domain": domain}
        inventory = options.get("inventory") or {}
        hosts = (domain, *options.get("aliases", []))
        region = any(host_key(h) in listed for h in hosts)
        gap = max(REQUEST_GAP, PROTECTED_GAP if protected else 0, PROXY_GAP if region else 0, float(inventory.get("gap_s") or 0))
        lane = "eklenti" if inventory.get("extension_only") else "tarayici" if protected else None
        return {"domain": domain, "requests": int(requests), "gap": gap, "units": max(1, int(units or 1)), "lane": lane, "region": region}
    for company in last_companies:
        if company["domain"] in configured:
            out.append(shape(company["domain"], company["request_count"] * window_ratio, company["listing_count"], bool(company.get("protected"))))
    for item in added:
        out.append(shape(item["domain"], item["requests"], (item.get("listings") or 0) + (item.get("own_homes") or 0), item.get("protected")))
    return out


def worker_estimate(companies, exits, site_limit=4):
    """Seconds of a run for these workers (studio.workers.simulate); region-blocked companies count only when a US proxy is among them."""
    from .. import workers as W
    pairs = exits if isinstance(exits, list) else [(True, False)] + [(True, True)] * max(0, int(exits) - 1)
    usable = companies if any(r for _, r in pairs) else [c for c in companies if not c["region"] or c["lane"]]
    return W.simulate(usable, pairs, site_limit, ANSWER_SECONDS)


def collect(raw_path, progress, canceled, *, config, client=None, verifier=None, waiting=None, today=None, region=None, pool=None,
            site_limit=None, exit_client=None, board=None, trial=None, store=None):
    """Ask every configured company site the price of every future window for each listing tied to it (and for its own inventory).
    Companies whose site waits for a human verification are read last, after one shared wait (see the module text)."""
    if not config or not config.get("sites"):
        raise SourceError("Bu destinasyon için kiralama şirketi yapılandırması yok.")
    lodging = config.get("input")
    if not lodging or not lodging.get("listings"):
        raise SourceError("Önce konaklama aramaları toplanmalı: kiralama şirketi fiyatları son Book>Direct çekimindeki ilanlardan sorulur.")
    today = today or datetime.now(timezone.utc).date()
    selected = config.get("selected")          # HEDEF-03: "Seçili şirketleri yeniden oku" (the chosen companies and the base version)
    if selected:
        check_selection(selected, config, lodging)
    # the same window rule as the lodging collector (the windows of the run day); otherwise the configured fixed windows. HEDEF-03: a
    # selected-companies run asks the windows of the version it completes, so every company of the new version has the same weeks.
    if selected:
        windows = active_windows([{k: w[k] for k in ("window_key", "label", "checkin", "checkout")} for w in selected["base"]["windows"]], today)
    else:
        windows = active_windows(monthly_windows(today, config["window_rule"]) if config.get("window_rule") else config["windows"], today)
    active = [w for w in windows if w["status"] == "queried"]
    if not active:
        raise SourceError("Bütün tarih pencereleri geçmişte kaldı; yapılandırmaya yeni tarihler eklenmeli.")
    if trial:          # HEDEF-01: the trial run asks one week (the first window ahead)
        active = active[:int(trial.get("windows", 1))]
        windows = list(active)
    sites = {site["domain"]: site_options(site) for site in config["sites"] if site["enabled"]}
    if trial:          # HEDEF-01: a few pages of a company's sitemap list
        for site in sites.values():
            if has_list(site["inventory"]):
                site["inventory"] = {**site["inventory"], "max_pages": int(trial.get("inventory_pages", 3))}
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
    if trial:          # HEDEF-01: the trial run asks a few listings of every company (trial["listings"]; the ones tied last time first)
        for domain in groups:
            preferred = set(trial.get("preferred", {}).get(domain) or ())
            groups[domain] = sorted(groups[domain], key=lambda r: (r["lodging_id"] not in preferred, r["lodging_id"]))[:int(trial.get("listings", 2))]
        kept = {r["lodging_id"] for rows in groups.values() for r in rows}
        listings = {k: v for k, v in listings.items() if k in kept or v["domain"] is None}
    order = sorted((d for d in sites if groups[d] or sites[d]["own_region_id"] or own_everywhere(sites[d])), key=lambda d: (-len(groups[d]), d))
    if selected:          # HEDEF-03: only the chosen companies are asked; the others are carried from the base version below
        order = [d for d in order if d in set(selected["domains"])]
    store = store if store is not None else RawStore(raw_path)      # HEDEF-02: a replay's store writes nothing
    owns = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(45, connect=15), verify=True)
    shared = Shared(store=store, client=client, canceled=canceled, verifier=verifier, waiting=waiting, active=active, everyone=everyone, region=region,
                    tracker=Progress(progress, sum(max(1, len(groups[d])) for d in order)), marks={})
    progress(1, f"{len(order)} kiralama şirketinin sitesi için {sum(len(groups[d]) for d in order)} ilan sorgulanacak.")
    try:
        from . import agency_workers as AW
        from .. import workers as W
        runs = [CompanyRun(shared, sites[domain], groups[domain]) for domain in order]
        if trial:
            for run in runs:
                run.trial = trial
        exits = pool.exits() if pool is not None else default_exits(region)
        scheduler = AW.Scheduler(shared, runs, exits=exits, site_limit=site_limit or 4, board=board, pool=pool,
                                 exit_client=exit_client or (lambda exit_, hosts: proxy_client(exit_.proxy, hosts)),
                                 extension_paired=bool(getattr(verifier, "extension_ready", lambda: False)()))
        progress(1, f"{len(order)} kiralama şirketinin sitesi için {sum(len(groups[d]) for d in order)} ilan, "
                    f"{sum(1 for e in exits)} işçiyle ({', '.join(e.label for e in exits)}) sorgulanacak.")
        scheduler.start()
        scheduler.wait()
        summary = scheduler.summary()
        for state in scheduler.states:
            state.run.finalize(sum(s.requests for s in state.sessions))
        store.flush()
        deferred = [index for index, run in enumerate(runs) if run.deferred]
        if deferred:
            runs = finish_deferred(shared, runs, deferred)
            store.flush()
        companies = [{**run.result, "queried_on": today.isoformat(), "carried_from": None} for run in runs]
        quotes = [q for run in runs for q in run.quotes]
        own_rows = [r for run in runs for r in run.own_rows]
        own_quotes = [q for run in runs for q in run.own_quotes]
        published = [p for run in runs for p in run.published]
        carried = None
        if selected:
            companies, quotes, own_rows, own_quotes, published, carried = carry_over(selected, listings, companies, quotes, own_rows,
                                                                                    own_quotes, published)
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
                    "browser_hosts": sorted(shared.marks.values(), key=lambda m: m["host"]),
                    "okuma_yontemleri": dict(getattr(shared.verifier, "methods", None) or {}),
                    "isciler": summary, "deneme": bool(trial), **({"secili_okuma": carried} if carried else {})}
        progress(97, f"{len(listings)} ilan, {len(quotes)} fiyat sorgusu, kendi envanterinden {len(own_rows)} ev ve {len(order)} şirket sonucu kaydediliyor.")
        related = {"snapshot": snapshot, "windows": windows_rows, "companies": companies, "quotes": quotes, "own_listings": own_rows,
                   "own_quotes": own_quotes, "published": published, "browser_hosts": metadata["browser_hosts"],
                   "okuma_yontemleri": metadata["okuma_yontemleri"]}
        return CollectionResult([listings[i] for i in sorted(listings)], len(listings), statuses["no_url"] + statuses["no_adapter"], None,
                                metadata, related)
    finally:
        try:
            store.flush()
        except OSError:
            pass
        if owns:
            client.close()


# --- HEDEF-03: "Seçili şirketleri yeniden oku" ----------------------------------------------------------------------------------
# A rental price run may ask only the companies the user chose. The result is a new, whole version: the chosen companies as read now,
# every other company exactly as in the base version (the last successful one): its company row (with its own query day and the version
# it came from), its listings' rows, price answers, own-inventory homes and published rents, unchanged. The windows are the base
# version's (the weeks of every company are the same). Nothing of the base version is changed.

SELECTION_FILE = "secim.json"       # beside the run's raw copy: the chosen companies and the base version (a rebuild reads it)


def latest_version(con, destination_id):
    """The last successful rental price version of the destination (its run id), or None."""
    row = con.execute("""SELECT r.id FROM source_runs r JOIN agency_rate_snapshots s ON s.run_id=r.id
        WHERE r.status='done' AND r.destination_id=? ORDER BY r.finished_at DESC, r.id DESC LIMIT 1""", (destination_id,)).fetchone()
    return row[0] if row else None


def version_rows(con, run_id):
    """Every row of one rental price version, as the store wrote it (decoded)."""
    snapshot = con.execute("SELECT * FROM agency_rate_snapshots WHERE run_id=?", (run_id,)).fetchone()
    if snapshot is None:
        raise SourceError("Kiralama fiyat sürümü bulunamadı.")
    snapshot = dict(snapshot)
    companies = []
    for row in con.execute("SELECT * FROM agency_rate_companies WHERE run_id=?", (run_id,)):
        company = decode_company(row)
        company["queried_on"] = company.get("queried_on") or snapshot["queried_on"]
        companies.append(company)
    return {"run_id": run_id, "snapshot": snapshot,
            "windows": [dict(r) for r in con.execute("SELECT window_key,label,checkin,checkout,nights,status FROM agency_rate_windows WHERE run_id=? "
                                                      "ORDER BY checkin, window_key", (run_id,))],
            "companies": companies,
            "listings": {r["lodging_id"]: decode_listing(r) for r in con.execute("SELECT * FROM agency_rate_listings WHERE run_id=?", (run_id,))},
            "quotes": [decode_quote(r) for r in con.execute("SELECT * FROM agency_rate_quotes WHERE run_id=?", (run_id,))],
            "own_listings": [dict(r) for r in con.execute("SELECT * FROM agency_rate_own_listings WHERE run_id=?", (run_id,))],
            "own_quotes": [decode_quote(r) for r in con.execute("SELECT * FROM agency_rate_own_quotes WHERE run_id=?", (run_id,))],
            "published": [decode_published(r) for r in con.execute("SELECT * FROM agency_rate_published WHERE run_id=?", (run_id,))]}


def selection_context(con, destination_id, domains):
    """{"domains": [...], "base": version_rows(...)} for a run of the chosen companies, completing the last successful version."""
    base = latest_version(con, destination_id)
    if base is None:
        raise SourceError("Önce bir kiralama fiyat sürümü olmalı: seçili şirketler son başarılı sürümü tamamlar.")
    return {"domains": sorted({str(d) for d in domains}), "base": version_rows(con, base)}


def check_selection(selected, config, lodging):
    chosen = selected.get("domains") or []
    if not chosen:
        raise SourceError("Yeniden okunacak şirket seçilmedi.")
    enabled = {s["domain"] for s in config["sites"] if s.get("enabled", 1)}
    unknown = sorted(set(chosen) - enabled)
    if unknown:
        raise SourceError(f"Seçilen şirket yapılandırmada yok ya da kapalı: {', '.join(unknown)}.")
    base = selected["base"]
    if base["snapshot"]["lodging_run_id"] != lodging["run_id"]:
        raise SourceError("Son Book>Direct çekimi son kiralama fiyat sürümünden sonra yenilenmiş: seçili şirketler aynı ilanlarla "
                          "okunamaz; bütün kiralama çekimi gerekir.")


def carry_over(selected, listings, companies, quotes, own_rows, own_quotes, published):
    """The whole version: the chosen companies as read now, every other company's rows from the base version unchanged. `listings` is
    changed in place (a listing of a company not chosen gets its base row). Returns the merged lists and the note for the metadata."""
    base, chosen = selected["base"], set(selected["domains"])
    strip = lambda row: {k: v for k, v in row.items() if k != "run_id"}
    for lodging_id, row in list(listings.items()):
        old = base["listings"].get(lodging_id)
        if row["domain"] not in chosen and old is not None:
            listings[lodging_id] = strip(old)
    kept = {lid for lid, row in base["listings"].items() if row["domain"] not in chosen}
    carried_companies = [{**strip(c), "carried_from": c.get("carried_from") or base["run_id"]} for c in base["companies"] if c["domain"] not in chosen]
    merged = sorted(carried_companies + companies, key=lambda c: (-int(c.get("listing_count") or 0), c["domain"]))
    domains_of = {lid: row["domain"] for lid, row in base["listings"].items()}
    carried_quotes = [{**strip(q), "domain": domains_of.get(q["lodging_id"])} for q in base["quotes"] if q["lodging_id"] in kept]
    carried_own = [strip(o) for o in base["own_listings"] if o["domain"] not in chosen]
    carried_own_quotes = [strip(q) for q in base["own_quotes"] if q["domain"] not in chosen]
    carried_published = [strip(p) for p in base["published"] if p["lodging_id"] in kept]
    note = {"sirketler": sorted(chosen), "taban_surum": base["run_id"], "taban_sorgu_gunu": base["snapshot"]["queried_on"],
            "tasinan_sirket": len(carried_companies), "tasinan_fiyat": len(carried_quotes) + len(carried_own_quotes),
            "tasinan_istek": sum(int(c.get("request_count") or 0) for c in carried_companies)}
    return (merged, carried_quotes + quotes, carried_own + own_rows, carried_own_quotes + own_quotes, carried_published + published, note)


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
            failed = [e for e in getattr(shared.verifier, "errors", None) or () if e.get("alan_adi") == domain]
            if domain not in cleared and failed:          # HEDEF-03: the extension could not read the first page (not a verification)
                again.skip("verification_unavailable", "unavailable", f"Eklenti şirketin ilk sayfasını iki denemede de okuyamadı "
                                                                        f"({(failed[-1].get('not') or 'hata')[:160]}); şirket atlandı.")
            elif domain not in cleared:
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
        region = getattr(shared, "region", None)
        self.region = region if region is not None and region.listed(site["domain"]) else None     # GÖREV-16
        transport, gap = HttpTransport(shared.client), PROTECTED_GAP if self.protected else REQUEST_GAP
        if self.region is not None and self.region.proxy is not None:
            from ..proxy import is_listed
            hosts = sorted(self.region.hosts)      # GÖREV-22: only the listed domains through the proxy, the company's other domains directly
            transport, gap = HttpTransport(proxy_client(self.region.proxy, hosts), kind="proxy",
                                           proxied=lambda url: is_listed(hosts, url)), max(gap, PROXY_GAP)
        options = site["inventory"] or {}
        gap = max(gap, float(options.get("gap_s") or 0))      # GÖREV-25: a company's own pace (RealJoy: 20 s)
        self.extension_only = bool(options.get("extension_only"))
        self.session = SiteSession(shared.store, site["domain"], transport, shared.canceled,
                                   allowed=(*site["aliases"], *getattr(self.adapter, "api_hosts", ())), gap=gap, protected=self.protected,
                                   retry_429=options.get("retry_429"))
        self.result = {"domain": site["domain"], "company": site["company"], "adapter": site["adapter"], "status": "done",
                       "listing_count": len(members), "verification": None, "message": None, "protected": int(self.protected),
                       "guest_rule": site["guest_rule"], "inventory_count": None, "inventory_raw_sha256": None, "own_count": 0,
                       "own_outside": None, "own_on_bookdirect": None}
        self.browser, self.pages, self.cache = None, {}, {}
        self.counts = {"blocked": 0, "errors": 0}     # HEDEF-01: shared by every worker's view of the company (consecutive refusals/errors)
        self.reverify_lock = threading.Lock()
        self.quotes, self.own_rows, self.own_quotes, self.published = [], [], [], []
        self.facts = {f["lodging_id"]: f for f in shared.everyone}

    # --- browser and verification ---------------------------------------------------------------------------------------

    def open_browser(self, url):
        """The computer's browser for this company (one tab). A verification page still on screen after the grace period leaves the
        company for the end of the run; at the end the user has had the one shared wait. GÖREV-16: a region-blocked company goes to the
        program's own browser through the user's US proxy (never to the extension); a region block met now lists the domain."""
        shared, domain = self.shared, self.site["domain"]
        verifier = shared.verifier
        if self.extension_only:        # GÖREV-25: only the user's extension; never the program's own browser
            verifier = getattr(verifier, "without_fallback", None)
            if verifier is None:
                raise CompanyStopped("verification_unavailable", EXTENSION_ONLY_SKIP)
        elif self.site["protected_config"] and getattr(verifier, "fallback", None) is not None:
            verifier = verifier.through_fallback      # HEDEF-01: oversee.us, exclusive30a.com: the program's own browser (its lane)
        if self.region is not None:
            from ..proxy import PROXY_FAILED_SKIP
            if self.region.proxy is None or self.region.proxy.browser_problem:
                raise CompanyStopped("stopped_blocked", f"{PROXY_FAILED_SKIP} (programın tarayıcısı bu proxy'yle kullanılamıyor)"
                                     if self.region.proxy is not None else self.region_skip_text())
            from .region_reader import proxy_verifier
            verifier = proxy_verifier(self.region.proxy, sorted(self.region.hosts))
        if verifier is None:
            self.result["verification"] = "unavailable"
            raise CompanyStopped("verification_unavailable",
                                 "Site doğrulama ekranı gösterdi veya korumalı; bu bilgisayarda tarayıcı kullanılamıyor.")
        timeout = GRACE_SECONDS if self.final_timeout is None else self.final_timeout
        with shared.verify_lock:
            try:
                browser = verifier(domain, url, shared.canceled, timeout)
            except CollectionCanceled:
                raise
            except Exception as exc:
                if type(exc).__name__ == "RegionBlocked":
                    region = getattr(shared, "region", None)
                    if region is not None:
                        region.mark(domain, title=getattr(exc, "title", None) or None, url=getattr(exc, "url", None) or url,
                                    evidence=getattr(exc, "evidence", None))
                    raise CompanyStopped("stopped_blocked", f"bölge engeli: {domain} ABD dışından gelen ziyaretçiye hizmet vermiyor; alan adı "
                                         "bölge engelli listeye eklendi (sonraki çekimde ABD proxy'si tanımlıysa onunla okunur).") from None
                if type(exc).__name__ == "SiteBlocked":
                    raise CompanyStopped("stopped_blocked", f"Site engel sayfası gösterdi ({exc}); şirket durduruldu, yeniden denenmedi.") from None
                if type(exc).__name__ == "ExtensionMissing":
                    self.result["verification"] = "unavailable"
                    raise CompanyStopped("verification_unavailable", str(exc)) from None
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
        self.browser, self.browser_url = browser, url
        self.session.transport = browser

    def ask(self, call):
        while True:
            try:
                return call()
            except VerificationNeeded as need:
                if self.browser is not None:
                    if self.reverify():
                        continue
                    raise CompanyStopped("stopped_blocked", "Doğrulamadan sonra site yine doğrulama ekranı gösterdi; şirket durduruldu.") from None
                self.shared.marks[self.site["domain"]] = {"host": self.site["domain"], "url": need.url, "reason": "doğrulama sayfası"}
                self.open_browser(need.url)
                self.result["verification"] = "completed"

    def reverify(self):
        """HEDEF-03: the site asked again for its verification inside the extension: the extension's tab opens the company's page (the
        first page of the run), the check is passed there (by the site itself or by the user; the extension waits as on the first page),
        and the caller asks its question once more. False when the transport is not the extension, the limit is reached or the page
        is still a verification page."""
        again = getattr(self.browser, "reverify", None)
        if again is None:
            return False
        with self.reverify_lock:
            done = self.result.get("reverified", 0)
            if done >= REVERIFY_LIMIT:
                return False
            self.result["reverified"] = done + 1
            url = getattr(self, "browser_url", None) or self.first_url()
            self.shared.tracker.step(0, f"{self.site['company']}: site doğrulamayı yeniden istedi; eklentinin sekmesinde yeniden açılıyor ({done + 1}. kez).")
            return bool(again(url))

    # --- phases ------------------------------------------------------------------------------------------------------------

    def region_skip_text(self):
        from ..proxy import NO_PROXY_SKIP
        return NO_PROXY_SKIP

    def run(self):
        site, members, shared = self.site, self.members, self.shared
        try:
            if self.region is not None and self.region.proxy is None:
                raise CompanyStopped("stopped_blocked", self.region_skip_text())      # GÖREV-16: region-blocked and no US proxy
            if self.extension_only and not getattr(shared.verifier, "extension_ready", lambda: False)():
                self.result["verification"] = "unavailable"
                raise CompanyStopped("verification_unavailable", EXTENSION_ONLY_SKIP)     # GÖREV-25: skipped, nothing asked
            options = site["inventory"] or {}
            dead = options.get("dead_links")
            with shared.protected_lock if self.protected else nullcontext():
                if self.protected:
                    first = next((m["listing_url"] for m in members if self.session.allows(m["listing_url"])), None)
                    if dead and options.get("origin"):      # GÖREV-25: the old links do not work; the company's list page is the way in
                        first = options["origin"].rstrip("/") + (options.get("list_path") or "/")
                    self.open_browser(first or options.get("origin") or f"https://www.{site['domain']}/")
                for index, row in enumerate(members):
                    check(shared.canceled)
                    if dead:        # GÖREV-22: the company's old listing addresses are known not to work; none is asked
                        row.update({"page_status": "not_found", "link_status": "not_found",
                                    "message": f"Book>Direct bağlantısı sorulmadı: şirketin eski ilan adresleri çalışmıyor ({dead} ölçümü); "
                                               "ilan şirketin kendi listesinden eşlenir."})
                    else:
                        self.link(row)
                    shared.tracker.step(1, f"{site['company']}: {index + 1}/{len(members)} ilan.")
                waiting_rows = [r for r in members if r["page_status"] in FALLBACK_STATUSES]
                own = own_everywhere(site)
                if has_list(site["inventory"]) and (waiting_rows or site["own_region_id"] or own):
                    units, hashes = read_inventory(self.session, self.adapter, site, self.ask)
                    self.result["inventory_count"], self.result["inventory_raw_sha256"] = len(units), hashes
                    shared.tracker.step(0, f"{site['company']}: şirketin listesinde {len(units)} ilan.")
                    self.fallback(waiting_rows, units)
                    if site["own_region_id"] or own:
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

    # --- HEDEF-01: the pieces the workers' scheduler (agency_workers.py) uses -------------------------------------------

    def precheck(self):
        """Before any task: a company read only through the extension is skipped when the extension cannot take it (GÖREV-25)."""
        if self.extension_only and not getattr(self.shared.verifier, "extension_ready", lambda: False)():
            self.result["verification"] = "unavailable"
            raise CompanyStopped("verification_unavailable", EXTENSION_ONLY_SKIP)

    def stopped(self, stop):
        self.result["status"], self.result["message"] = stop.status, stop.message
        for row in self.members:
            if row["page_status"] == "not_queried":
                row["message"] = stop.message

    def mark_dead(self, row, dead):
        row.update({"page_status": "not_found", "link_status": "not_found",
                    "message": f"Book>Direct bağlantısı sorulmadı: şirketin eski ilan adresleri çalışmıyor ({dead} ölçümü); "
                               "ilan şirketin kendi listesinden eşlenir."})

    def first_url(self):
        options = self.site["inventory"] or {}
        first = next((m["listing_url"] for m in self.members if self.session.allows(m["listing_url"])), None)
        if options.get("dead_links") and options.get("origin"):
            first = options["origin"].rstrip("/") + (options.get("list_path") or "/")
        return first or options.get("origin") or f"https://www.{self.site['domain']}/"

    def open_lane(self):
        """The first task of a protected company in its lane opens the browser (as `run` does)."""
        if self.protected:
            self.open_browser(self.first_url())

    def finalize(self, extra_requests=0):
        """The company row's counts at the end of the run (as `run` writes them); the browser it opened is closed."""
        if self.browser is not None:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None
        members = self.members
        self.result.update({"matched_count": sum(r["page_status"] == "matched" for r in members), "quote_count": len(self.quotes),
                            "priced_count": sum(q["status"] == "priced" for q in self.quotes),
                            "request_count": self.session.requests + extra_requests, "own_count": len(self.own_rows),
                            "match_counts": {m: sum(r["match_method"] == m for r in members) for m in MATCH_METHODS}})
        self.shared.tracker.step(0, f"{self.site['company']}: bitti ({self.result['status']}).")

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
            self.counts["errors"] = self.counts["errors"] + 1 if self.cache[key]["status"] == "error" else 0
            if self.counts["errors"] >= ERROR_LIMIT:
                raise CompanyStopped("stopped_errors", f"Fiyat isteği art arda {ERROR_LIMIT} kez başarısız oldu; şirket durduruldu.")
        return self.cache[key]

    def price(self, row, info):
        own = own_everywhere(self.site)
        if own and not own.get("quotes", True):      # GÖREV-22: this company's prices are not asked yet; the tie is still recorded
            row["message"] = own.get("quotes_note") or "Bu şirketin fiyatı sorulmuyor (yapılandırma)."
            return
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
                self.counts["blocked"] = 0
                page["message"] = (f"Bu ilan sayfası erişime kapalı (HTTP {page['http_status']}); sitenin ana sayfası normal yanıt "
                                   "veriyor (ilan yayından kaldırılmış olabilir).")
                row["message"] = page["message"]
            else:
                self.counts["blocked"] += 1
                if self.counts["blocked"] >= BLOCK_LIMIT:
                    raise CompanyStopped("stopped_blocked", f"Site art arda {BLOCK_LIMIT} isteği reddetti (HTTP {page['http_status']}); "
                                                            "şirket durduruldu.")
        else:
            self.counts["blocked"] = 0
        if page["page_status"] == "error":
            self.counts["errors"] += 1
            if self.counts["errors"] >= ERROR_LIMIT:
                raise CompanyStopped("stopped_errors", f"Siteye art arda {ERROR_LIMIT} kez ulaşılamadı; şirket durduruldu.")
        elif page["page_status"] != "blocked":
            self.counts["errors"] = 0
        if page["page_status"] == "matched":
            row["match_method"] = "link"
            self.price(row, page["info"])

    def fallback(self, rows, units):
        """Listings whose link did not reach a listing, tied by the address rule (or, when the company's list has no street
        addresses, by the location rule)."""
        for row in rows:
            check(self.shared.canceled)
            self.fallback_one(row, units)

    def fallback_one(self, row, units):
        """One listing of `fallback` (HEDEF-01: one worker task)."""
        by_address = sum(bool(u.get("address")) for u in units) * 2 >= max(1, len(units))
        linker = getattr(self.adapter, "link_unit", None)
        facts = self.facts[row["lodging_id"]]
        unit, note = (linker([row["listing_url"], *(self.pages.get(row["listing_url"]) or {}).get("hops", ())], units)
                      if linker else (None, None))
        if unit is not None:        # GÖREV-22: the link names a unit number the company's own list gives for exactly one home
            kind, method = "matched", "link"
        elif by_address:
            kind, unit, note = address_match(facts, units, address_without_unit=self.address_without_unit())
            method = "address"
        else:
            kind, unit, note = location_match(facts, units, self.shared.everyone)
            method = "location"
        row["match_note"] = note
        if kind != "matched":
            return
        page = unit.get("page") or open_listing(self.session, self.adapter, unit["url"], self.ask)
        if page["page_status"] != "matched":
            row["match_note"] = f"{note} Eşleşen şirket ilanının sayfası açılamadı: {page['message']}"
            return
        row.update({k: page[k] for k in ("page_status", "page_url", "http_status", "site_listing_id")})
        row["message"], row["match_method"] = None, method
        self.price(row, page["info"])

    def address_without_unit(self):
        """GÖREV-25: the company's list writes a building's homes under the building's address without their unit (the configuration's
        `inventory.address_without_unit`, else what the adapter knows of its site, e.g. RealJoy)."""
        options = self.site["inventory"] or {}
        return bool(options.get("address_without_unit", getattr(self.adapter, "address_without_unit", False)))

    def own_inventory(self, units):
        """The community's homes from the company's own list that Book>Direct does not show: the community is the configured name
        the site itself gives (its City field); a home the site places elsewhere is left out, and a home already on Book>Direct
        (same company page, same url or the address rule) is not counted twice. GÖREV-22 (`inventory.own`): the same for a
        company's homes in every neighbourhood, each under the neighbourhood the site itself names for it, or under none."""
        plan = self.own_plan(units)
        for unit in plan["homes"]:
            check(self.shared.canceled)
            self.own_one(unit, plan)

    def own_plan(self, units):
        """What `own_inventory` reads (HEDEF-01: each home then is one worker task): the community's homes not already on Book>Direct,
        and the counts written on the company row."""
        site, everyone = self.site, self.shared.everyone
        own = own_everywhere(site)
        if own:
            # GÖREV-22: the company's own inventory across the neighbourhoods. A home belongs here when the site places it in the
            # configured region of the site (`site_region`); its neighbourhood is the one the configuration maps the site's own
            # place name to (`regions`), else none. Never taken from the coordinates.
            wanted = (own.get("site_region") or "").strip().lower()
            names = {str(name).strip().lower(): region for name, region in (own.get("regions") or {}).items()}
            community = [u for u in units if not wanted or (u.get("site_region") or "").strip().lower() == wanted]
            region_of = lambda unit: names.get((unit.get("city") or "").strip().lower())
        else:
            city = (site["own_city"] or "").strip().lower()
            community = [u for u in units if (u.get("city") or "").strip().lower() == city]
            region_of = lambda unit: site["own_region_id"]
        ask_prices = not own or own.get("quotes", True)
        self.result["own_outside"] = len(units) - len(community)
        matched = {r["site_listing_id"] for r in self.members if r["page_status"] == "matched"}
        on_bookdirect, homes = 0, []
        for unit in community:
            if unit["site_id"] in matched or any(same_url(unit["url"], f["url"]) for f in everyone) or any(same_home(unit, f) for f in everyone):
                on_bookdirect += 1
                continue
            homes.append(unit)
        self.result["own_on_bookdirect"] = on_bookdirect
        return {"homes": homes, "region_of": region_of, "ask_prices": ask_prices, "own": own}

    def own_one(self, unit, plan):
        """One home of the company's own inventory (HEDEF-01: one worker task)."""
        site, own, ask_prices, region_of = self.site, plan["own"], plan["ask_prices"], plan["region_of"]
        if True:
            page = unit.get("page") or open_listing(self.session, self.adapter, unit["url"], self.ask)
            row = {"domain": site["domain"], "site_listing_id": unit["site_id"], "title": unit.get("title") or unit["url"], "page_url": page["page_url"] or unit["url"],
                   "address": unit.get("address"), "city": unit.get("city"), "region_id": region_of(unit), "bedrooms": unit.get("bedrooms"),
                   "bathrooms": unit.get("bathrooms"), "sleeps": unit.get("sleeps"), "latitude": unit.get("latitude"), "longitude": unit.get("longitude"),
                   "page_status": page["page_status"], "message": page["message"]}
            self.own_rows.append(row)
            if page["page_status"] != "matched":
                return
            if not ask_prices:
                row["message"] = own.get("quotes_note") or "Bu şirketin fiyatı sorulmuyor (yapılandırma)."
                return
            guests = guests_for(site, unit.get("bedrooms"), unit.get("sleeps"))
            for window in self.shared.active:
                answer = self.quote_once(page["info"], window, guests)
                self.own_quotes.append({**answer, "domain": site["domain"], "site_listing_id": unit["site_id"], "window_key": window["window_key"]})

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


def has_list(inventory):
    """HEDEF-03: the company's own listing list is configured (a source); options with only the allowed queries are not a list."""
    return bool((inventory or {}).get("source"))


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
    for url in urls[:int(options.get("max_pages") or MAX_INVENTORY_PAGES)]:
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
    base.update({"page_url": reply.url, "http_status": reply.status, "hops": list(getattr(reply, "hops", ()) or ())})
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


def total_counts(quotes):
    """Priced totals and how many of them include the site's taxes and fees (the evidence pack writes the share, GÖREV-12)."""
    priced = [q for q in quotes if q["status"] == "priced" and q["total"] is not None]
    return {"priced": len(priced), "taxed": sum(q["total_includes_taxes"] == 1 for q in priced),
            "fees": sum(q["total_includes_fees"] == 1 for q in priced)}


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
    region_ids = {region for listing in listings.values() for region in listing["region_ids"]} | {o["region_id"] for o in own if o["region_id"]}
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
    own_companies = own_company_summary(own, own_by_window, windows, companies, names)
    return {"snapshot": dict(snapshot), "windows": windows, "regions": [{"region_id": r, "region_name": names.get(r, r)} for r in regions],
            "cells": cells, "companies": companies, "seasons": seasons, "comparison": comparison,
            "coverage": {**coverage, "listings": len(listings), "priced_listings": len(priced_ids), "regions": len(regions),
                         "regions_with_price": len(regions_priced), "methods": methods, "own_listings": len(own), "own_priced": len(own_priced),
                         "own_unassigned": sum(o["region_id"] is None for o in own),
                         "published": len({r["lodging_id"] for r in published})},
            "own_companies": own_companies,
            "label": total_label(quotes + own_quotes, snapshot["queried_on"]), "total_counts": total_counts(quotes + own_quotes),
            "guest_label": guest_label(companies),
            "source_note": ("Fiyatlı ilanlar Book>Direct ilanlarıdır (eşleme yöntemi: bağlantı, adres veya konum); 'kendi envanteri' "
                            "sütunu tek bir topluluğun resmî kiralama programında Book>Direct'te olmayan evleri ve sitesi adres vermediği için "
                            "Book>Direct ilanlarına bağlanamayan şirketin kendi sitesindeki evleri ayrı sayar."),
            "published_note": "Yayımlanmış kira: sitenin sezon için yayımladığı kira aralığı × gece sayısı; vergi ve ücretler hariç, toplam fiyat ortancalarına karışmaz.",
            "nightly_note": "Gecelik ortalama = sitenin kira tutarı ÷ gece sayısı (bizim hesabımız; ücret ve vergiler hariç).",
            "bedroom_note": "Oda sayısı Book>Direct ilanından; 1–2 grubuna stüdyolar dahildir. Ortancalar 7 gecelik toplam fiyattandır."}


OWN_SOURCE = "şirketin kendi sitesindeki evler; Book>Direct ilanlarına bağlanmadı"


def own_company_summary(own, own_by_window, windows, companies, names):
    """Per company its own-inventory homes (GÖREV-22): how many, how many the site places in a neighbourhood and in which, how many
    in none, and per asked window the priced homes and the median total of all of them and of the homes without a neighbourhood.
    The medians are ours, from the site's own totals; homes without a neighbourhood enter no neighbourhood's medians. GÖREV-23: a
    week priced by rent alone (the calendar's nightly rates summed; no fees, taxes or total) is counted and its median given apart
    (`rent_count`, `rent_median`); it never enters a total median."""
    result = []
    for company in companies:
        homes = [o for o in own if o["domain"] == company["domain"]]
        if not homes:
            continue
        by_region = {}
        for home in homes:
            if home["region_id"]:
                by_region[home["region_id"]] = by_region.get(home["region_id"], 0) + 1
        loose = [h for h in homes if not h["region_id"]]
        rows = []
        for window in windows:
            if window["status"] != "queried":
                continue
            asked = own_by_window.get(window["window_key"], {})
            def totals(group):
                found = [asked.get((h["domain"], h["site_listing_id"])) for h in group]
                return [q["total"] for q in found if q is not None and q["status"] == "priced" and q["total"] is not None]
            def rents(group):       # GÖREV-23: weeks a site prices by rent alone (no total without a cart), kept apart from the totals
                found = [asked.get((h["domain"], h["site_listing_id"])) for h in group]
                return [q["rent"] for q in found if q is not None and q["status"] == "priced" and q["total"] is None and q["rent"] is not None]
            everything, apart, rent_only = totals(homes), totals(loose), rents(homes)
            rows.append({"window_key": window["window_key"], "priced_count": len(everything),
                         "total_median": round(statistics.median(everything), 2) if everything else None,
                         "unassigned_priced": len(apart), "unassigned_median": round(statistics.median(apart), 2) if apart else None,
                         "rent_count": len(rent_only), "rent_median": round(statistics.median(rent_only), 2) if rent_only else None})
        result.append({"domain": company["domain"], "company": company["company"], "homes": len(homes), "with_region": len(homes) - len(loose),
                       "unassigned": len(loose), "outside": company.get("own_outside"), "on_bookdirect": company.get("own_on_bookdirect"),
                       "priced": sum(1 for h in homes if any((h["domain"], h["site_listing_id"]) in own_by_window.get(w["window_key"], {})
                                                              and own_by_window[w["window_key"]][(h["domain"], h["site_listing_id"])]["status"] == "priced"
                                                              for w in windows)),
                       "regions": [{"region_id": region, "region_name": names.get(region, region), "homes": count}
                                   for region, count in sorted(by_region.items(), key=lambda item: (-item[1], item[0]))],
                       "unassigned_label": "mahallesi belirtilmemiş", "source": OWN_SOURCE, "windows": rows})
    return result


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


RULE_SOURCES = ("sayfa", "yanıt")      # where a stay rule was read: the listing page (its calendar too) or the price answer
RULE_SOURCE_ALIASES = {"takvim": "sayfa"}   # HEDEF-02: RealJoy's calendar answers said "takvim" before the fix (a kept result may)


def checked_quote(quote, where):
    """A price answer ready for its row: a value the schema does not take stops the storing with the company, the listing and the
    week named (HEDEF-02: the night of 27 November 2026 failed with only the constraint's text)."""
    source = RULE_SOURCE_ALIASES.get(quote.get("rule_source"), quote.get("rule_source"))
    if source is not None and source not in RULE_SOURCES:
        raise SourceError(f"{where}: kural kaynağı \"{source}\" tanınmıyor (yalnız {', '.join(RULE_SOURCES)}); sonuç kaydedilmedi.")
    if quote.get("status") not in QUOTE_STATUSES:
        raise SourceError(f"{where}: fiyat cevabının durumu \"{quote.get('status')}\" tanınmıyor; sonuç kaydedilmedi.")
    return {**quote, "rule_source": source} if source != quote.get("rule_source") else quote


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

    uses_extension = True
    uses_region = True          # GÖREV-16: region-blocked company sites only through the user's US proxy

    uses_workers = True         # HEDEF-01: the run is split among workers (the direct connection and the proxies of the list)
    selectable = True           # HEDEF-03: "Seçili şirketleri yeniden oku"

    def collect(self, source, raw_path, progress, canceled, *, context, waiting=None, extension=None, region=None, board=None):
        lodging, agency = context.lodging, context.agency
        if not lodging or not agency:
            raise SourceError("Bu destinasyon için kiralama şirketi fiyat yapılandırması yok.")
        if lodging["clone_host"] != source_host(source["url"]):
            raise SourceError("Kaynağın Book>Direct adresi destinasyonun konaklama yapılandırmasıyla uyuşmuyor.")
        verifier = self.verifier_factory() if self.verifier_factory else default_verifier()
        if extension is not None and extension.paired:        # GÖREV-14: the user's own Chrome first, the program's browser after a hand-over
            from .extension_reader import ExtensionVerifier
            verifier = ExtensionVerifier(extension, fallback=verifier)
        pool = getattr(region, "pool", None)
        config = {**agency, "windows": lodging["windows"], "window_rule": lodging.get("window_rule"), "browser_hosts": context.browser_hosts}
        if getattr(context, "selected", None):
            config["selected"] = context.selected         # HEDEF-03: "Seçili şirketleri yeniden oku"
        return collect(raw_path, progress, canceled, config=config,
                       verifier=verifier, waiting=waiting, region=region, pool=pool, site_limit=pool.site_limit() if pool is not None else None,
                       board=board, trial=getattr(context, "trial", None))

    def store_records(self, con, run_id, records, related=None):
        snapshot = related["snapshot"]
        con.execute("INSERT INTO agency_rate_snapshots (run_id,lodging_run_id,queried_on,request_count,listing_count) VALUES (?,?,?,?,?)",
                    (run_id, snapshot["lodging_run_id"], snapshot["queried_on"], snapshot["request_count"], snapshot["listing_count"]))
        con.executemany("INSERT INTO agency_rate_windows (run_id,window_key,label,checkin,checkout,nights,status) VALUES (?,?,?,?,?,?,?)",
                        [(run_id, w["window_key"], w["label"], w["checkin"], w["checkout"], w["nights"], w["status"]) for w in related["windows"]])
        con.executemany("""INSERT INTO agency_rate_companies (run_id,domain,company,adapter,status,listing_count,matched_count,quote_count,priced_count,
            request_count,verification,message,protected,guest_rule,inventory_count,inventory_raw_sha256,own_count,own_outside,own_on_bookdirect,
            match_counts,queried_on,carried_from) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, c["domain"], c["company"], c["adapter"], c["status"], c["listing_count"], c["matched_count"], c["quote_count"], c["priced_count"],
              c["request_count"], c["verification"], c["message"], c["protected"], c["guest_rule"], c["inventory_count"],
              dumps(c["inventory_raw_sha256"]), c["own_count"], c["own_outside"], c["own_on_bookdirect"], dumps(c["match_counts"]),
              c.get("queried_on") or snapshot["queried_on"], c.get("carried_from"))
             for c in related["companies"]])
        con.executemany("""INSERT INTO agency_rate_listings (run_id,lodging_id,title,bedrooms,region_ids,listing_url,url_host,domain,page_status,page_url,
            http_status,site_listing_id,message,link_status,match_method,match_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, r["lodging_id"], r["title"], r["bedrooms"], json.dumps(r["region_ids"]), r["listing_url"], r["url_host"], r["domain"],
              r["page_status"], r["page_url"], r["http_status"], r["site_listing_id"], r["message"], r["link_status"], r["match_method"],
              r["match_note"]) for r in records])
        con.executemany(f"INSERT INTO agency_rate_quotes (run_id,lodging_id,window_key,{','.join(QUOTE_COLUMNS)}) VALUES (?,?,?{',?' * len(QUOTE_COLUMNS)})",
                        [(run_id, q["lodging_id"], q["window_key"],
                          *quote_values(checked_quote(q, f"{q.get('domain') or 'ilan'} {q['lodging_id']} · {q['window_key']}")))
                         for q in related["quotes"]])
        con.executemany("""INSERT INTO agency_rate_own_listings (run_id,domain,site_listing_id,title,page_url,address,city,region_id,bedrooms,bathrooms,
            sleeps,latitude,longitude,page_status,message) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, o["domain"], o["site_listing_id"], o["title"], o["page_url"], o["address"], o["city"], o["region_id"], o["bedrooms"],
              o["bathrooms"], o["sleeps"], o["latitude"], o["longitude"], o["page_status"], o["message"]) for o in related.get("own_listings", [])])
        con.executemany(f"INSERT INTO agency_rate_own_quotes (run_id,domain,site_listing_id,window_key,{','.join(QUOTE_COLUMNS)}) "
                        f"VALUES (?,?,?,?{',?' * len(QUOTE_COLUMNS)})",
                        [(run_id, q["domain"], q["site_listing_id"], q["window_key"],
                          *quote_values(checked_quote(q, f"{q['domain']} {q['site_listing_id']} · {q['window_key']}")))
                         for q in related.get("own_quotes", [])])
        con.executemany("""INSERT INTO agency_rate_published (run_id,lodging_id,window_key,season_start,season_end,rate_text,rate_period,rent_low,rent_high,
            basis,source_url,raw_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, p["lodging_id"], p["window_key"], p["season_start"], p["season_end"], p["rate_text"], p["rate_period"], p["rent_low"],
              p["rent_high"], p["basis"], p["source_url"], json.dumps(p["raw_sha256"])) for p in related.get("published", [])])
        mark_hosts(con, related.get("browser_hosts", []), CONNECTOR_VERSION)
        record_methods(con, related.get("okuma_yontemleri"))

    def rebuild(self, db, job, source, progress, canceled):
        """HEDEF-02: the run of `job` rebuilt from its raw copy (studio/sources/agency_replay.py): (batch, report, comparison)."""
        from . import agency_replay
        batch, report = agency_replay.replay(db, job, source, self, progress, canceled)
        return batch, report, agency_replay.compare(batch, agency_replay.summary_counts(job.get("log")))

    def read_records(self, con, run_id):
        return [decode_listing(r) for r in con.execute("SELECT * FROM agency_rate_listings WHERE run_id=? ORDER BY title, lodging_id", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Agency rate diff is disabled.")


PROXY_GAP = 8.0             # GÖREV-16: through the US proxy the extension's pacing rule holds (8 s between two pages of a site)


def proxy_client(proxy, hosts=None):
    """A client for one region-blocked company; redirects are followed by the session. With `hosts` (GÖREV-22) only requests to the
    region-blocked domains (and their subdomains) go through the user's US proxy and every other request of the company (a domain its
    links start at, a platform's API host) goes directly; without it every request goes through the proxy."""
    timeout = httpx.Timeout(45, connect=15)
    if hosts is None:
        return httpx.Client(transport=proxy.transport(), timeout=timeout, follow_redirects=False)
    return httpx.Client(mounts=proxy.mounts(hosts), timeout=timeout, follow_redirects=False)


def default_exits(region):
    """Without a pool (older call paths and tests): the direct connection, and the GÖREV-16 single proxy for region-blocked sites only."""
    from .. import workers as W
    exits = [W.direct_exit()]
    if region is not None and getattr(region, "proxy", None) is not None:
        exits.append(W.Exit("proxy:1", 1, region.proxy, None, general=False))
    return exits


def default_verifier():
    """The computer's browser when Playwright and Chrome/Edge are installed; None otherwise (a verification page then skips that
    company)."""
    from .browser_verification import BrowserVerifier, available
    return BrowserVerifier() if available() else None
