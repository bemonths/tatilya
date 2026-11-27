"""HEDEF-02: a rental price run rebuilt from its own raw copy, without going to the sites.

Every answer of a run is kept in its raw folder (`raw/<job>/manifest.json` and `responses/*.gz`: the method, the address, the fields
sent and the body of each answer). The replay runs the same collector code again (`agency_rates.collect`, the same companies, the same
Book>Direct listings, the same run day) but every request is answered from that copy:

- a request is looked up by method, address and the fields sent; an answer used once is not given again (a request asked twice that
  night has two answers, given in their order);
- a request the copy does not have (that night it failed before any answer: a time-out, a dropped connection) fails the same way
  (a connection error);
- a redirect's target was not kept before HEDEF-02 (only the answers): for those older copies the target is the next answer of the same
  company and kind that no listing link asks by itself (the hop the session asked right after it). Copies made from HEDEF-02 on keep
  the target (`location`), and it is used as it is;
- no waiting: the pacing between requests, a 429's wait and the user's verification wait are skipped (nothing goes to a site);
- the browser and the extension are not opened: their answers come from the copy the same way.

The result says how faithful the replay was: every answer used exactly once and no request missing means the run was rebuilt as it
went. The counts are compared with the run's last log line ("N ilan, M fiyat sorgusu, kendi envanterinden K ev ve C şirket").
"""
import gzip
import hashlib
import json
import re
import threading
from collections import Counter, defaultdict, deque
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl

import httpx

REDIRECTS = (301, 302, 303, 307, 308)
SUMMARY_LINE = re.compile(r"(\d+) ilan, (\d+) fiyat sorgusu, kendi envanterinden (\d+) ev ve (\d+) şirket sonucu kaydediliyor")


def canonical(body):
    """The fields of a request in one comparable form (form fields and JSON alike)."""
    if body is None or body == "" or body == b"":
        return ""
    if isinstance(body, (bytes, bytearray)):
        text = bytes(body).decode("utf-8", errors="replace")
        try:
            return "json:" + json.dumps(json.loads(text), sort_keys=True, ensure_ascii=False)
        except ValueError:
            return "form:" + json.dumps(sorted(parse_qsl(text, keep_blank_values=True)), ensure_ascii=False)
    if isinstance(body, dict) and all(not isinstance(v, (dict, list)) for v in body.values()):
        return "form:" + json.dumps(sorted((str(k), "" if v is None else str(v)) for k, v in body.items()), ensure_ascii=False)
    return "json:" + json.dumps(body, sort_keys=True, ensure_ascii=False)


def way_of(kind):
    """How a request went: the extension, a browser (the program's own, also through the proxy), or plain HTTP (directly or a proxy)."""
    kind = str(kind or "")
    if kind == "eklenti":
        return "eklenti"
    if "browser" in kind or "tarayici" in kind:
        return "tarayici"
    return "http"


def keys_of(record):
    """A recorded request's keys: its fields could have gone as form fields or as JSON (the manifest keeps the dict either way)."""
    body = record.get("request_body")
    out = {canonical(body)}
    if isinstance(body, dict) and all(not isinstance(v, (dict, list)) for v in body.values()):
        out.add("json:" + json.dumps(body, sort_keys=True, ensure_ascii=False))
    return [(way_of(record["transport"]), record["method"].upper(), record["requested_url"], key) for key in out]


GAP_WINDOWS = ((7.5, 14.0), (15.5, 22.0), (31.5, 38.0))    # seconds from a redirect to its hop: the 8 s gap, twice, four times


def stamp(record):
    return datetime.fromisoformat(record["fetched_at"]).timestamp()


def likeness(a, b):
    """How alike two addresses are (0..1): the same host (without www) and the last part of the path (a page renamed or moved keeps
    most of its name; the shared folders of a site say nothing)."""
    from difflib import SequenceMatcher

    def parts(url):
        u = httpx.URL(url)
        path = u.path.rstrip("/").lower()
        return (u.host or "").removeprefix("www."), path.rsplit("/", 1)[-1]
    (ha, sa), (hb, sb) = parts(a), parts(b)
    return (0.2 if ha == hb else 0.0) + 0.8 * SequenceMatcher(None, sa, sb).ratio()


def summary_counts(log):
    """The counts of a run's last "… kaydediliyor" log line: listings, price questions, own homes, companies."""
    for entry in reversed(log or []):
        found = SUMMARY_LINE.search(entry.get("text") or "")
        if found:
            listings, quotes, own, companies = (int(n) for n in found.groups())
            return {"ilan": listings, "fiyat_sorgusu": quotes, "kendi_evi": own, "sirket": companies}
    return None


class ReplayBook:
    """The answers of one raw copy, given once each."""

    def __init__(self, manifest_path, listing_urls=()):
        """listing_urls: every Book>Direct listing's link (one entry per listing; a link two listings share is given twice)."""
        self.path = Path(manifest_path)
        self.folder = self.path.parent
        manifest = json.loads(self.path.read_text(encoding="utf-8"))
        self.records = manifest["responses"]
        self.lock = threading.Lock()
        self.index = defaultdict(deque)
        for record in self.records:
            for key in keys_of(record):
                self.index[key].append(record)
        self.used = set()
        self.missing = []
        self.locations = self.redirect_targets(list(listing_urls))
        self.kinds = defaultdict(set)
        for record in self.records:
            self.kinds[record["company"]].add(record["transport"])

    def redirect_targets(self, listing_urls):
        """Each redirect's target: the kept `location`, or (older copies) the hop the same worker asked right after it. A worker waits
        its gap (8 s; twice after a refusal) before its next request, so the hop is an answer of the same company and note that came
        GAP_WINDOWS seconds later, is not a listing link of its own and is no other redirect's hop; among several, the one nearest the
        usual delay, the more alike address counting for about two seconds."""
        targets, claimed = {}, set()
        later = defaultdict(list)
        for record in self.records:
            later[(record["company"], record["note"])].append(record)
        # a listing link asked more often than there are listings with it was also some redirect's hop (the extra answers)
        asked = Counter(r["requested_url"] for r in self.records if r["method"] == "GET")
        extra = {url: asked[url] - n for url, n in Counter(listing_urls).items() if asked[url] > n}
        for record in self.records:
            if record["status"] not in REDIRECTS:
                continue
            if record.get("location"):
                targets[record["sequence"]] = record["location"]
                continue
            at = stamp(record)
            found = None
            for low, high in GAP_WINDOWS:
                options = []
                for candidate in later[(record["company"], record["note"])]:
                    if candidate["sequence"] <= record["sequence"] or candidate["sequence"] in claimed:
                        continue
                    delay = stamp(candidate) - at
                    if delay > high:
                        break
                    if delay < low or candidate["method"] != "GET" or candidate["requested_url"] == record["requested_url"]:
                        continue
                    if candidate["requested_url"] in listing_urls and extra.get(candidate["requested_url"], 0) <= 0:
                        continue
                    expected = low + 1.2         # the gap and a usual answer time
                    options.append((abs(delay - expected) - 2.0 * likeness(record["requested_url"], candidate["requested_url"]),
                                    candidate["sequence"], candidate))
                if options:
                    found = min(options, key=lambda o: (o[0], o[1]))[2]
                    break
            if found is not None:
                targets[record["sequence"]] = found["requested_url"]
                claimed.add(found["sequence"])
                if found["requested_url"] in extra:
                    extra[found["requested_url"]] -= 1
        return targets

    def body(self, record):
        return gzip.decompress((self.folder / record["raw_file"]).read_bytes())

    def take(self, way, method, url, body_key):
        with self.lock:
            queue = self.index.get((way, method.upper(), url, body_key))
            while queue:
                record = queue.popleft()
                if record["sequence"] in self.used:
                    continue
                self.used.add(record["sequence"])
                return record
            self.missing.append({"method": method.upper(), "url": url, "yol": way})
            return None

    def answer(self, way, method, url, body_key):
        """(status, final url, headers, body), or a connection error when the copy has no answer for it."""
        record = self.take(way, method, url, body_key)
        if record is None:
            raise httpx.ConnectError("Ham kopyada bu isteğin cevabı yok (o gece cevap alınamamış).")
        headers = {"content-type": record.get("content_type") or ""}
        location = self.locations.get(record["sequence"])
        if record["status"] in REDIRECTS and location:
            headers["location"] = location
        return record["status"], record.get("final_url") or url, headers, self.body(record)

    def report(self):
        unused = [r for r in self.records if r["sequence"] not in self.used]
        given = {key for r in self.records if r["sequence"] in self.used for key in keys_of(r)}
        repeats = [r for r in unused if any(key in given for key in keys_of(r))]
        redirects = [r for r in self.records if r["status"] in REDIRECTS]
        return {"cevap": len(self.records), "kullanilan": len(self.used), "kullanilmayan": len(unused),
                "kullanilmayan_ornek": [{"sira": r["sequence"], "sirket": r["company"], "adres": r["requested_url"][:200]} for r in unused[:100]],
                "kullanilmayan_sirket": dict(Counter(r["company"] for r in unused)),
                "kullanilmayan_tekrar": len(repeats),
                "eksik_istek": len(self.missing), "eksik_ornek": self.missing[:100],
                "eksik_sirket": dict(Counter(httpx.URL(m["url"]).host.removeprefix("www.") for m in self.missing)),
                "yonlendirme": len(redirects), "hedefi_kayitli": sum(bool(r.get("location")) for r in redirects),
                "hedefi_cikarilan": sum(1 for r in redirects if not r.get("location") and r["sequence"] in self.locations)}

    def faithful(self):
        return not self.missing and len(self.used) == len(self.records)

    def mock(self):
        """An httpx transport answering from the copy (for the plain and the proxy requests)."""
        def handler(request):
            status, _final, headers, body = self.answer("http", request.method, str(request.url), canonical(request.content))
            return httpx.Response(status, headers=headers, content=body)
        return httpx.MockTransport(handler)


class ReplayTransport:
    """The browser's or the extension's transport, answered from the copy (redirects were followed by the browser that night). The
    extension's own query rule is applied as the extension applies it (a refused query was never sent, so it has no answer)."""

    def __init__(self, book, kind, domain=None, allowed=()):
        self.book, self.kind, self.domain, self.allowed = book, kind, domain, allowed

    def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
        if params:
            url = str(httpx.URL(url, params=params))
        if self.kind == "eklenti" and str(method).upper() != "GET":
            self.refuse(method, url, data, json_body)
        return self.book.answer(way_of(self.kind), method, url, canonical(data if data is not None else json_body))

    def refuse(self, method, url, data, json_body):
        """ExtensionTransport.query's and Session.query's checks, with the same texts."""
        from .. import extension_queries as eq
        from ..extension import domain_of
        from .agency_adapters import AdapterError
        parts = httpx.URL(url)
        if json_body is not None or parts.query or domain_of(parts.host) != domain_of(self.domain or parts.host):
            raise AdapterError("Eklenti yalnız izinli sorguyu (sitenin kendi adresine, form alanlarıyla) gönderir; bu istek gönderilmedi.")
        fields = {str(k): str(v) for k, v in (data or {}).items()}
        refused = eq.refusal({"alan_adi": domain_of(self.domain or parts.host), "yol": parts.path, "yontem": str(method).upper(),
                              "alanlar": fields}, self.allowed)
        if refused:
            raise AdapterError(f"Sorgu gönderilmedi: {refused}")

    def close(self):
        pass


class ReplayVerifier:
    """The verifier of a replay: every company's browser or extension "opens" at once, answered from the copy."""

    def __init__(self, book, allowed=()):
        self.book, self.allowed = book, list(allowed)
        self.methods = {}

    def kind(self, domain):
        kinds = self.book.kinds.get(domain) or set()
        return "eklenti" if "eklenti" in kinds else "browser"

    def __call__(self, domain, url, canceled, timeout):
        kind = self.kind(domain)
        self.methods[domain] = "eklenti" if kind == "eklenti" else "tarayici"
        return ReplayTransport(self.book, kind, domain, self.allowed)

    def extension_ready(self):
        return True

    def without_fallback(self, domain, url, canceled, timeout):
        return self(domain, url, canceled, timeout)

    def through_fallback(self, domain, url, canceled, timeout):
        return self(domain, url, canceled, timeout)

    fallback = None

    def wait_all(self, sites, canceled, timeout, waiting=None):
        return set(sites)


class ReplayProxy:
    """Stands for the user's US proxy in a replay (nothing leaves the computer)."""

    browser_problem = None

    def __init__(self, book):
        self.book = book

    def transport(self, **kwargs):
        return self.book.mock()

    def mounts(self, hosts, **kwargs):
        return {"all://": self.book.mock()}

    def sanitize(self, text):
        return text


class ReplayPool:
    def __init__(self, exits):
        self._exits = exits

    def exits(self):
        return list(self._exits)

    def mark_down(self, row_id, note):
        pass

    def site_limit(self):
        return 4


class ReplayRegion:
    """The region-blocked list as it is now (that night's list), with the replay's proxy."""

    def __init__(self, hosts, proxy, pool):
        from ..proxy import host_key
        self.hosts = {host_key(h) for h in hosts}
        self.proxy, self.pool = proxy, pool

    def listed(self, url_or_host):
        from ..proxy import is_listed
        return is_listed(self.hosts, url_or_host)

    def mark(self, host, **kwargs):
        return False

    def mounts(self, **kwargs):
        return self.proxy.mounts(self.hosts)


class ReplayStore:
    """The raw store of a replay: nothing is written (the answers are the night's own files); the count and the digests are the same."""

    replay = True

    def __init__(self):
        self.lock = threading.Lock()
        self.manifest = {"responses": []}       # the digests only (what the inventory's hashes read)

    def save(self, *, company, transport, method, requested, status, final_url, headers, body, note, request_body, location=None):
        digest, stamp = hashlib.sha256(body).hexdigest(), datetime.now(timezone.utc).isoformat()
        with self.lock:
            self.manifest["responses"].append({"company": company, "raw_sha256": digest, "status": status})
        return digest, stamp

    def flush(self):
        pass

    @property
    def count(self):
        with self.lock:
            return len(self.manifest["responses"])


def run_day(job):
    """The day the run's windows were counted from (the run's start, UTC, as `collect` takes it)."""
    stamp = (job.get("created_at") or "").replace("Z", "+00:00")
    return datetime.fromisoformat(stamp).astimezone(timezone.utc).date() if stamp else date.today()


EXTENSION_LINE = re.compile(r"Eklenti çalışıyor: ([a-z0-9.-]+) ·")


def replay(db, job, source, connector, progress, canceled, raw_path=None):
    """The run of `job` rebuilt from its raw copy: (CollectionResult, report). `raw_path`: the copy's manifest (default: the job's own
    raw folder beside the database). The Book>Direct listings are the ones the run had (the latest run finished before it started)."""
    from . import agency_rates as ar
    from .. import workers as W
    from ..database import Database
    from ..proxy import listed_hosts
    raw_path = Path(raw_path) if raw_path else db.path.parent / "raw" / job["id"] / connector.raw_filename
    if not raw_path.is_file():
        raise ar.SourceError("Bu işin ham kopyası (manifest.json) yok; sonuç kurulamaz.")
    context = db.context(source["destination_id"], inputs=connector.inputs)
    lodging, agency = context.lodging, context.agency
    if not lodging or not agency:
        raise ar.SourceError("Bu destinasyon için kiralama şirketi fiyat yapılandırması yok.")
    with db.connect() as con:
        agency = {**agency, "input": Database.lodging_input(con, source["destination_id"], before=job.get("created_at"))}
        hosts = listed_hosts(con)
    listing_urls = [item["url"] for item in (agency.get("input") or {}).get("listings") or []]
    book = ReplayBook(raw_path, listing_urls)
    for entry in job.get("log") or []:            # the companies the extension read that night (their pages are not in the copy)
        found = EXTENSION_LINE.search(entry.get("text") or "")
        if found:
            book.kinds[found.group(1)].add("eklenti")
    proxy = ReplayProxy(book)
    client = httpx.Client(transport=book.mock(), follow_redirects=False)
    exits = [W.direct_exit(), W.Exit("proxy:yeniden", 1, proxy, "US", health=lambda: True)]
    pool = ReplayPool(exits)
    region = ReplayRegion(hosts, proxy, pool)
    config = {**agency, "windows": lodging["windows"], "window_rule": lodging.get("window_rule"), "browser_hosts": context.browser_hosts}
    try:
        batch = ar.collect(raw_path, progress, canceled, config=config, client=client, verifier=ReplayVerifier(book, db.extension_queries()),
                           today=run_day(job), region=region, pool=pool, site_limit=4,
                           exit_client=lambda exit_, hosts: httpx.Client(transport=book.mock()), store=ReplayStore())
    finally:
        client.close()
    report = book.report()
    report["sadik"] = book.faithful()
    report["gun"] = run_day(job).isoformat()
    report["ham_kopya"] = str(raw_path)
    batch.metadata = {**batch.metadata, "yeniden_kurma": {"kaynak_is": job["id"], "gun": report["gun"],
                                                          "kullanilan_cevap": report["kullanilan"], "cevap": report["cevap"],
                                                          "eksik_istek": report["eksik_istek"]}}
    return batch, report


def compare(batch, expected):
    """The rebuilt result against the run's own last log line."""
    related = batch.related or {}
    got = {"ilan": len(batch.records), "fiyat_sorgusu": len(related.get("quotes") or []), "kendi_evi": len(related.get("own_listings") or []),
           "sirket": len(related.get("companies") or [])}
    return {"beklenen": expected, "kurulan": got, "ayni": expected is not None and got == expected}
