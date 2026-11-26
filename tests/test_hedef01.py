"""HEDEF-01: the workers of a rental price run (studio/workers.py, studio/sources/agency_workers.py), the proxy list
(studio/proxy_list.py), the worker estimate and the trial run. Fake HTTP only (httpx.MockTransport); every worker's way out is a
separate mock client that records which worker asked what; no real site, no real proxy.

What is shown: the tasks are spread over the workers; a worker whose proxy drops stops and its task goes to another worker; at most
`site_limit` workers on one site; a 429 slows every worker of that site and a second one leaves it one worker; a region-blocked
company only on US proxies; browser companies (protected, extension only) are never split and run in their lanes beside the workers;
a proxy added to the list during a run joins it."""
import json
import threading
import time
from datetime import date

import httpx
import pytest

from studio import proxy as P
from studio import proxy_list as PL
from studio import workers as W
from studio.sources import agency_adapters as aa
from studio.sources import agency_rates as ar
from studio.sources import agency_workers as AW

TODAY = date(2026, 10, 8)
WINDOWS = [{"window_key": "fall", "label": "Sonbahar", "checkin": "2026-10-17", "checkout": "2026-10-24"},
           {"window_key": "winter", "label": "Kış", "checkin": "2027-01-16", "checkout": "2027-01-23"}]


class Fake:
    """A synthetic platform: the listing page gives `site_id`, the price is one GET."""

    name = "fake"

    def parse_page(self, text, url):
        if "LISTING" not in text:
            return None
        return {"site_id": url.rstrip("/").rsplit("/", 1)[-1], "page_url": url}

    def quote(self, session, info, window, guests):
        reply = session.request("GET", f"https://{session.domain}/quote/{info['site_id']}/{window['window_key']}", note="fake-quote")
        if reply.status != 200:
            return {"status": "error", "available": None, "message": f"HTTP {reply.status}", "replies": [reply]}
        return {"status": "priced", "available": True, "rent": 100.0, "total": 120.0, "total_includes_taxes": 1, "total_includes_fees": 1,
                "currency": "USD", "replies": [reply]}


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setitem(ar.ADAPTERS, "fake", Fake())
    for name in ("REQUEST_GAP", "PROTECTED_GAP", "PROXY_GAP", "RETRY_PAUSE"):
        monkeypatch.setattr(ar, name, 0.0)
    monkeypatch.setattr(AW, "IDLE_WAIT_S", 0.02)


def site(domain, **options):
    return {"domain": domain, "company": domain.split(".")[0].title(), "adapter": "fake", "enabled": 1, **options}


def bd(lodging_id, url):
    return {"lodging_id": lodging_id, "title": f"Listing {lodging_id}", "url": url, "bedrooms": 3, "bathrooms": 2, "sleeps": 8,
            "address": None, "latitude": None, "longitude": None, "region_ids": ["seaside"]}


def listings_for(domain, count, start=0):
    return [bd(start + i, f"https://www.{domain}/rentals/{start + i}") for i in range(count)]


class Net:
    """The sites, and every request with the worker that sent it (`via`: "doğrudan" or the proxy's label)."""

    def __init__(self, delay=0.0, answer=None):
        self.lock = threading.Lock()
        self.seen, self.delay, self.answer = [], delay, answer
        self.active, self.peak = {}, {}

    def handler(self, via):
        def handle(request):
            host = request.url.host.removeprefix("www.")
            with self.lock:
                self.seen.append((via, host, request.url.path))
                self.active[host] = self.active.get(host, 0) + 1
                self.peak[host] = max(self.peak.get(host, 0), self.active[host])
            try:
                if self.delay:
                    time.sleep(self.delay)
                if self.answer is not None:
                    special = self.answer(via, host, request)
                    if special is not None:
                        return special
                if request.url.path.startswith("/rentals/"):
                    return httpx.Response(200, text="<html>LISTING</html>", headers={"content-type": "text/html"})
                return httpx.Response(200, text="ok")
            finally:
                with self.lock:
                    self.active[host] -= 1
        return handle

    def via(self, host=None):
        return {v for v, h, _ in self.seen if host is None or h == host}


def proxy_exit(order, country="US", health=None, **kw):
    return W.Exit(f"proxy:{order}", order, P.ProxySettings(f"http://p{order}.test:8080"), country, health=health, row_id=f"r{order}", **kw)


def collect(tmp_path, net, sites, listings, *, exits=None, pool=None, site_limit=4, region=None, verifier=None, exit_client=None, board=None,
            trial=None, windows=WINDOWS):
    config = {"sites": sites, "windows": windows, "input": {"run_id": "lodging-run", "searched_on": "2026-10-07", "listings": listings}}
    exits = exits if exits is not None else [W.direct_exit()]
    pool = pool or StaticPool(exits)
    clients = exit_client or (lambda exit_, hosts: httpx.Client(transport=httpx.MockTransport(net.handler(exit_.label))))
    with httpx.Client(transport=httpx.MockTransport(net.handler("doğrudan"))) as client:
        return ar.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config, client=client, today=TODAY,
                          pool=pool, site_limit=site_limit, region=region, verifier=verifier, exit_client=clients, board=board, trial=trial)


class StaticPool:
    def __init__(self, exits):
        self.items, self.down = list(exits), []

    def exits(self):
        return list(self.items)

    def mark_down(self, row_id, note):
        self.down.append((row_id, note))


def priced(result):
    return {(q["lodging_id"], q["window_key"]) for q in result.related["quotes"] if q["status"] == "priced"}


# ---- distribution ---------------------------------------------------------------------------------------------------------------

def test_the_tasks_are_spread_over_every_worker_and_nothing_is_asked_twice(tmp_path):
    net = Net(delay=0.01)
    listings = listings_for("alpha.test", 12) + listings_for("beta.test", 12, start=100)
    result = collect(tmp_path, net, [site("alpha.test"), site("beta.test")], listings,
                     exits=[W.direct_exit(), proxy_exit(1), proxy_exit(2)])
    assert len(priced(result)) == 24 * 2
    assert net.via() == {"doğrudan", "proxy 1", "proxy 2"}                     # every worker had work
    pages = [(h, p) for _, h, p in net.seen if p.startswith("/rentals/")]
    assert len(pages) == len(set(pages)) == 24                                  # each listing page once
    summary = result.metadata["isciler"]
    assert set(summary["sirketler"]["alpha.test"]["cikislar"]) <= {"doğrudan", "proxy 1", "proxy 2"}
    companies = {c["domain"]: c for c in result.related["companies"]}
    assert companies["alpha.test"]["request_count"] == 12 * 3 and companies["alpha.test"]["status"] == "done"
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["responses"]) == 72
    assert sum(1 for e in manifest["responses"] if e.get("proxy")) == sum(1 for v, _, _ in net.seen if v != "doğrudan")
    assert "p1.test" not in json.dumps(result.metadata, ensure_ascii=False)     # never a proxy's address


def test_a_worker_whose_proxy_drops_stops_and_its_task_goes_to_another_worker(tmp_path):
    net = Net(delay=0.005)
    asked = {"n": 0}

    def clients(exit_, hosts):
        handle = net.handler(exit_.label)
        def maybe_drop(request):
            if exit_.label == "proxy 1":
                asked["n"] += 1
                if asked["n"] > 3:
                    raise httpx.ConnectError("proxy gone", request=request)
            return handle(request)
        return httpx.Client(transport=httpx.MockTransport(maybe_drop))
    pool = StaticPool([W.direct_exit(), proxy_exit(1, health=lambda: False)])
    board = W.Board()
    result = collect(tmp_path, net, [site("alpha.test")], listings_for("alpha.test", 10), pool=pool, exit_client=clients, board=board)
    assert len(priced(result)) == 20                                             # nothing lost
    assert pool.down and pool.down[0][0] == "r1" and "düştü" in pool.down[0][1]   # marked "çalışmıyor" for the next run
    workers = {w["cikis"]: w["durum"] for w in result.metadata["isciler"]["isciler"]}
    assert workers["proxy 1"] == "düştü" and workers["doğrudan"] == "bitti"
    assert any("proxy 1" in e["metin"] and "başka işçiye" in e["metin"] for e in result.metadata["isciler"]["olaylar"])
    rows = {r["lodging_id"]: r for r in result.records}
    assert all(r["page_status"] == "matched" for r in rows.values())


def test_at_most_site_limit_workers_read_one_site_at_once(tmp_path):
    net = Net(delay=0.03)
    exits = [W.direct_exit()] + [proxy_exit(i) for i in range(1, 6)]
    result = collect(tmp_path, net, [site("alpha.test")], listings_for("alpha.test", 18), exits=exits, site_limit=2)
    assert len(priced(result)) == 36
    assert net.peak["alpha.test"] == 2
    net = Net(delay=0.03)
    collect(tmp_path / "b", net, [site("alpha.test")], listings_for("alpha.test", 18), exits=exits, site_limit=4)
    assert net.peak["alpha.test"] == 4


def test_a_429_slows_every_worker_of_the_site_and_a_second_one_leaves_it_one_worker(tmp_path, monkeypatch):
    monkeypatch.setattr(ar, "REQUEST_GAP", 1.0)
    pauses = []
    monkeypatch.setattr(ar, "pause", lambda seconds, canceled: pauses.append(round(seconds, 1)))
    refused = {"n": 0}

    def answer(via, host, request):
        if host == "alpha.test" and request.url.path.startswith("/quote/") and refused["n"] < 2:
            refused["n"] += 1
            return httpx.Response(429, text="slow down")
        return None
    net = Net(delay=0.02, answer=answer)
    exits = [W.direct_exit()] + [proxy_exit(i) for i in range(1, 4)]
    result = collect(tmp_path, net, [site("alpha.test"), site("beta.test")], listings_for("alpha.test", 16) + listings_for("beta.test", 4, 50),
                     exits=exits, site_limit=4)
    events = [e["metin"] for e in result.metadata["isciler"]["olaylar"]]
    assert any("alpha.test: HTTP 429" in e and "bütün işçiler yavaşladı" in e for e in events)
    assert any("alpha.test: yine HTTP 429" in e and "işçi sayısı bire indi" in e for e in events)
    assert not any("beta.test" in e for e in events)                            # the other site keeps its pace and its workers
    assert 2.0 in pauses and max(pauses) <= 2.0                                  # the gap of the slowed site doubled (1 s → 2 s)
    assert len(priced(result)) == 40 - 2                                         # the two refused prices are errors, the rest priced


def test_a_region_blocked_company_goes_only_to_us_proxies(tmp_path):
    class Region:
        hosts = {"blocked.test"}
        proxy = P.ProxySettings("http://p1.test:8080")
        def listed(self, url_or_host):
            return P.is_listed(self.hosts, url_or_host)
        def mark(self, *a, **k):
            return True
    net = Net(delay=0.005)
    exits = [W.direct_exit(), proxy_exit(1, "US"), proxy_exit(2, "TR")]
    result = collect(tmp_path, net, [site("blocked.test"), site("open.test")], listings_for("blocked.test", 6) + listings_for("open.test", 6, 50),
                     exits=exits, region=Region())
    assert net.via("blocked.test") == {"proxy 1"}
    assert len(priced(result)) == 24
    no_us = collect(tmp_path / "b", Net(), [site("blocked.test")], listings_for("blocked.test", 2), exits=[W.direct_exit(), proxy_exit(2, "TR")],
                    region=Region())
    company = no_us.related["companies"][0]
    assert company["status"] == "stopped_blocked" and company["message"] == P.NO_PROXY_SKIP


def test_browser_companies_are_not_split_and_run_in_their_lanes_beside_the_workers(tmp_path):
    lanes = []

    class Browser:
        kind = "browser"
        def __init__(self, domain):
            self.domain = domain
        def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
            lanes.append((self.domain, threading.current_thread().name))
            path = httpx.URL(url).path
            body = "<html>LISTING</html>" if path.startswith("/rentals/") else "ok"
            return 200, url, {"content-type": "text/html"}, body.encode()
        def close(self):
            pass

    class Verifier:
        methods = {}
        fallback = None
        def __call__(self, domain, url, canceled, timeout):
            return Browser(domain)
        def extension_ready(self):
            return True
        def without_fallback(self, domain, url, canceled, timeout):
            return Browser(domain)

    def answer(via, host, request):
        if host == "guarded.test" and request.url.path.startswith("/rentals/"):
            return httpx.Response(403, text="<title>Just a moment...</title>", headers={"cf-mitigated": "challenge"})
        return None
    net = Net(delay=0.005, answer=answer)
    sites = [site("oversee.test", protected=1), site("joy.test", protected=1, inventory={"extension_only": True}), site("guarded.test"), site("open.test")]
    listings = listings_for("oversee.test", 4) + listings_for("joy.test", 3, 20) + listings_for("guarded.test", 3, 40) + listings_for("open.test", 8, 60)
    result = collect(tmp_path, net, sites, listings, exits=[W.direct_exit(), proxy_exit(1)], verifier=Verifier())
    threads = {}
    for domain, thread in lanes:
        threads.setdefault(domain, set()).add(thread)
    assert threads["oversee.test"] == {"30a-isci-tarayıcı"} and threads["joy.test"] == {"30a-isci-eklenti"}    # whole, one lane each
    assert threads["guarded.test"] == {"30a-isci-eklenti"}            # a verification page moved it to the extension lane
    assert not net.via("oversee.test") and not net.via("joy.test")    # never asked by the workers
    assert {h for _, h, _ in net.seen} == {"guarded.test", "open.test"}
    assert len([p for v, h, p in net.seen if h == "guarded.test"]) == 1        # one challenge, then the browser
    assert len(priced(result)) == (4 + 3 + 3 + 8) * 2
    summary = result.metadata["isciler"]["sirketler"]
    assert summary["oversee.test"]["sira"] == "tarayici" and summary["joy.test"]["sira"] == "eklenti" and summary["guarded.test"]["sira"] == "eklenti"
    assert any("guarded.test" in e["metin"] and "eklenti sırasına" in e["metin"] for e in result.metadata["isciler"]["olaylar"])


def test_a_proxy_added_to_the_list_during_the_run_joins_it(tmp_path, monkeypatch):
    monkeypatch.setattr(AW, "POOL_REFRESH_S", 0.05)
    net = Net(delay=0.03)

    class Growing(StaticPool):
        def __init__(self):
            super().__init__([W.direct_exit()])
            self.calls = 0
        def exits(self):
            self.calls += 1
            return [W.direct_exit()] + ([proxy_exit(1)] if self.calls > 1 else [])
    result = collect(tmp_path, net, [site("alpha.test")], listings_for("alpha.test", 20), pool=Growing())
    assert "proxy 1" in net.via() and len(priced(result)) == 40
    assert any("proxy 1: yeni işçi" in e["metin"] for e in result.metadata["isciler"]["olaylar"])


def test_a_proxy_taken_out_of_the_list_stops_its_worker_and_its_work_goes_on(tmp_path, monkeypatch):
    monkeypatch.setattr(AW, "POOL_REFRESH_S", 0.05)
    net = Net(delay=0.03)

    class Shrinking(StaticPool):
        def __init__(self):
            super().__init__([W.direct_exit(), proxy_exit(1)])
            self.calls = 0
        def exits(self):
            self.calls += 1
            return [W.direct_exit(), proxy_exit(1)] if self.calls == 1 else [W.direct_exit()]
    result = collect(tmp_path, net, [site("alpha.test")], listings_for("alpha.test", 20), pool=Shrinking())
    assert len(priced(result)) == 40
    workers = {w["cikis"]: w["durum"] for w in result.metadata["isciler"]["isciler"]}
    assert workers["proxy 1"] == "çıkarıldı"


def test_the_trial_run_asks_two_listings_of_each_company_and_one_week(tmp_path):
    net = Net()
    result = collect(tmp_path, net, [site("alpha.test"), site("beta.test")], listings_for("alpha.test", 9) + listings_for("beta.test", 9, 50),
                     trial={"listings": 2, "windows": 1, "preferred": {"alpha.test": [7, 8]}})
    asked = {(q["lodging_id"], q["window_key"]) for q in result.related["quotes"]}
    assert asked == {(7, "fall"), (8, "fall"), (50, "fall"), (51, "fall")}
    assert result.metadata["deneme"] is True and [w["window_key"] for w in result.metadata["windows"]] == ["fall"]


# ---- the estimate ---------------------------------------------------------------------------------------------------------------

def test_the_estimate_follows_the_number_of_workers_the_site_limit_and_the_lanes():
    companies = [{"domain": "big.test", "requests": 900, "gap": 8.0, "units": 300, "lane": None, "region": False},
                 {"domain": "small.test", "requests": 90, "gap": 8.0, "units": 30, "lane": None, "region": False},
                 {"domain": "guard.test", "requests": 100, "gap": 8.0, "units": 50, "lane": "tarayici", "region": False},
                 {"domain": "blue.test", "requests": 90, "gap": 8.0, "units": 30, "lane": None, "region": True}]
    one = ar.worker_estimate(companies, 1)
    assert one == pytest.approx((900 + 90) * 9.0)                      # one direct worker; no US proxy: the region company is left out
    two = ar.worker_estimate(companies, 2)
    four = ar.worker_estimate(companies, 5)
    many = ar.worker_estimate(companies, 40)
    assert one > two > four >= many
    assert many == pytest.approx(900 * 9.0 / 4, rel=0.02)               # the biggest site at its limit of 4 workers
    assert W.simulate([companies[2]], 3) == pytest.approx(900.0)       # a lane is read alone, whatever the number of workers
    assert ar.worker_estimate(companies, 40, site_limit=1) == pytest.approx(900 * 9.0, rel=0.01)


# ---- the proxy list ---------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("line, scheme, expected", [
    ("1.2.3.4:8080:ali:gizli-1", "http", ("http://1.2.3.4:8080", "ali", "gizli-1")),
    ("1.2.3.4:8080", "socks5", ("socks5://1.2.3.4:8080", "", "")),
    ("ali:gi:zli@proxy.test:3128", "http", ("http://proxy.test:3128", "ali", "gi:zli")),
    ("socks5://ali:p@proxy.test:1080", "http", ("socks5://proxy.test:1080", "ali", "p")),
    ("https://proxy.test:443", "http", ("https://proxy.test:443", "", "")),
    ("proxy.test:8080:ali:pa:ss", "http", ("http://proxy.test:8080", "ali", "pa:ss")),
])
def test_a_pasted_line_is_read_in_every_accepted_form(line, scheme, expected):
    assert PL.parse_line(line, scheme) == expected


@pytest.mark.parametrize("line", ["proxy.test", "proxy.test:port", "a:b:c", "ftp://proxy.test:21", "proxy.test:99999", "ali@proxy.test:80"])
def test_a_line_that_cannot_be_read_is_refused_without_repeating_it(line):
    with pytest.raises(ValueError) as error:
        PL.parse_line(line)
    assert line not in str(error.value)


def test_bulk_add_keeps_passwords_only_in_credential_manager_tests_each_line_and_lists_the_workers(tmp_path, memory_keyring):
    tested = []

    def tester(proxy):
        tested.append(proxy.label)
        ok = "dead" not in proxy.host
        return {"ok": ok, "ip": "203.0.113.9" if ok else None, "ulke": "US" if ok else None, "uyari": None,
                "satirlar": [f"Proxy: {proxy.label}", "Çıkış adresi" if ok else "BAŞARISIZ: zaman aşımı."]}
    text = "a.test:8080:ali:Parola-Bir-1\n\n# not\nb.test:9090:veli:Parola-Iki-2\ndead.test:80:x:Parola-Uc-3\nbozuk satır\n"
    outcome = PL.add_lines(tmp_path, text, "http", tester=tester)
    assert (outcome["eklenen"], outcome["guncellenen"]) == (3, 0) and [e["satir"] for e in outcome["hatalar"]] == [6]
    assert "bozuk" not in outcome["hatalar"][0]["hata"]
    assert sorted(tested) == ["http://a.test", "http://b.test", "http://dead.test"]
    saved = (tmp_path / "ayarlar.json").read_text(encoding="utf-8")
    for secret in ("Parola-Bir-1", "Parola-Iki-2", "Parola-Uc-3"):
        assert secret not in saved and secret not in json.dumps(outcome, ensure_ascii=False)
    assert memory_keyring.values[("30AStudio", "abd_proxy_parolasi")] == "Parola-Bir-1"         # the first row keeps the old name
    rows = PL.view(tmp_path)
    assert [(r["sira"], r["etiket"], r["durum"], r["ulke"], r["isci"]) for r in rows] == [
        (1, "http://a.test", "calisiyor", "US", True), (2, "http://b.test", "calisiyor", "US", True), (3, "http://dead.test", "calismiyor", None, False)]
    exits = W.exits_from_settings(tmp_path)
    assert [e.label for e in exits] == ["doğrudan", "proxy 1", "proxy 2"] and exits[2].proxy.password == "Parola-Iki-2"
    assert json.loads(saved)["abd_proxy"] == {"adres": "http://a.test:8080", "kullanici": "ali"}  # the region-blocked reading's proxy
    assert P.load(tmp_path).password == "Parola-Bir-1"
    # removing the first row: the second becomes the first and takes the old password name
    assert PL.remove(tmp_path, rows[0]["id"])
    assert memory_keyring.values[("30AStudio", "abd_proxy_parolasi")] == "Parola-Iki-2"
    assert [r["etiket"] for r in PL.view(tmp_path)] == ["http://b.test", "http://dead.test"] and P.load(tmp_path).host == "b.test"


def test_the_single_proxy_of_earlier_versions_is_the_first_row(tmp_path, memory_keyring):
    (tmp_path / "ayarlar.json").write_text(json.dumps({"abd_proxy": {"adres": "http://eski.test:8080", "kullanici": "eski"}}), encoding="utf-8")
    memory_keyring.values[("30AStudio", "abd_proxy_parolasi")] = "Eski-Parola-9"
    rows = PL.view(tmp_path)
    assert [(r["id"], r["etiket"], r["parola_kayitli"], r["isci"]) for r in rows] == [("1", "http://eski.test", True, True)]
    assert [e.label for e in W.exits_from_settings(tmp_path)] == ["doğrudan", "proxy 1"]


def test_the_api_adds_tests_removes_and_sets_the_site_limit(tmp_path, memory_keyring):
    from fastapi.testclient import TestClient
    from studio.app import create_app
    from tests.test_beaches import HEADERS
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        client.app.state.proxy_test = lambda proxy: {"ok": True, "ip": "203.0.113.1", "ulke": "US", "uyari": None, "satirlar": [f"Proxy: {proxy.label}"]}
        answer = client.post("/api/abd-proxy/liste", json={"satirlar": "a.test:1:u:Gizli-Bir-11\nb.test:2:v:Gizli-Iki-22", "tur": "socks5"}).json()
        assert answer["ekleme"]["eklenen"] == 2 and [r["etiket"] for r in answer["liste"]] == ["socks5://a.test", "socks5://b.test"]
        assert "Gizli" not in json.dumps(answer, ensure_ascii=False)
        tested = client.post("/api/abd-proxy/dene", json={}).json()
        assert [r["sira"] for r in tested["sonuclar"]] == [1, 2] and all(r["ok"] for r in tested["sonuclar"])
        one = client.post(f"/api/abd-proxy/liste/{answer['liste'][1]['id']}/dene", json={}).json()
        assert one["deneme"]["sira"] == 2 and one["deneme"]["ulke"] == "US"
        assert client.put("/api/abd-proxy/isciler", json={"site_basina": 3}).json()["site_basina"] == 3
        assert client.put("/api/abd-proxy/isciler", json={"site_basina": 99}).status_code == 422
        left = client.delete(f"/api/abd-proxy/liste/{answer['liste'][1]['id']}").json()
        assert [r["etiket"] for r in left["liste"]] == ["socks5://a.test"]
        assert client.post("/api/abd-proxy/liste", json={"satirlar": "  "}).status_code == 422


# ---- the trial run --------------------------------------------------------------------------------------------------------------

def test_the_trial_run_works_on_a_copy_with_the_limits_and_never_touches_the_real_database(tmp_path, monkeypatch):
    from studio import trial_run as T
    from studio.database import Database
    from studio.sources.base import CollectionResult
    monkeypatch.setattr(T, "POLL_S", 0.05)
    seen = []

    class FakeConnector:
        name, version, raw_filename, method, diff_enabled = "fake", "fake/1", "raw.json", "API", False
        def supports(self, source):
            return bool(source.get("url"))
        def collect(self, source, raw_path, progress, canceled, *, context):
            seen.append((source["name"], context.trial, len((context.lodging or {}).get("windows") or []), raw_path))
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text("{}", encoding="utf-8")
            return CollectionResult([], 0, 0, None, {"deneme": True}, {})
        def store_records(self, con, run_id, records, related=None):
            pass

    class Registry:
        connectors = [FakeConnector()]
        def for_source(self, source):
            return self.connectors[0] if self.connectors[0].supports(source) else None
        def by_name(self, name):
            return self.connectors[0]
    db = Database(tmp_path / "studio.sqlite3", registry=Registry())
    db.initialize()
    with db.connect() as con:
        runs_before = con.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0]
    job = db.add_job("deneme_cekimi", "Deneme çekimi")
    trial = T.TrialRun(db, job["id"] if isinstance(job, dict) else job)
    trial.run()
    with db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0] == runs_before      # the real database has no new run
    done = db.job(trial.job_id)
    assert done["status"] == "done" and "Deneme çekimi bitti" in done["message"]
    assert seen and all(trial_limits["listings"] == 2 and trial_limits["windows"] == 1 for _, trial_limits, _, _ in seen)
    assert all(windows <= 1 for _, _, windows, _ in seen)
    assert all(str(raw).startswith(str(tmp_path / "deneme")) for _, _, _, raw in seen)           # raw files beside the copy
    result = T.latest(tmp_path)
    assert result["klasor"].startswith("deneme/") and len(result["toplayicilar"]) == len(seen)
    assert {r["durum"] for r in result["toplayicilar"]} == {"done"}
    copy = Database(tmp_path / result["klasor"] / "studio.sqlite3", registry=Registry())
    with copy.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM source_runs").fetchone()[0] == runs_before + len(seen)


def test_only_the_last_trials_keep_their_copies(tmp_path):
    from studio import trial_run as T
    root = tmp_path / "deneme"
    for name in ("20261101-000000", "20261102-000000", "20261103-000000", "20261104-000000"):
        (root / name / "raw").mkdir(parents=True)
        (root / name / "studio.sqlite3").write_text("x")
        (root / name / "sonuc.json").write_text("{}")
    T.prune(root, keep=3)
    assert not (root / "20261101-000000" / "studio.sqlite3").exists() and not (root / "20261101-000000" / "raw").exists()
    assert (root / "20261101-000000" / "sonuc.json").exists()
    assert all((root / n / "studio.sqlite3").exists() for n in ("20261102-000000", "20261103-000000", "20261104-000000"))


def test_the_track_sites_own_security_check_is_a_verification_page_and_moves_the_company_to_a_browser_lane(tmp_path):
    """26 Nov 2026 (the trial run): 30A Escapes, Ocean Reef and Panhandle Getaways answered every request with HTTP 429 "Quick security
    check" (a Turnstile frame from challenge.icoastalnet.com). It is a verification the user passes, not a refusal."""
    from pathlib import Path
    from studio.sources import page_kinds
    page = (Path(__file__).parent / "fixtures" / "hedef01" / "track-guvenlik-kontrolu.html").read_text(encoding="utf-8")
    assert ar.CHALLENGE.search(page) and page_kinds.classify(page, "Quick security check", "https://www.oceanreefresorts.com/x", 429) == "dogrulama"
    browsed = []

    class Browser:
        kind = "browser"
        def send(self, method, url, **kwargs):
            browsed.append(url)
            body = "<html>LISTING</html>" if "/rentals/" in url else "ok"
            return 200, url, {"content-type": "text/html"}, body.encode()
        def close(self):
            pass

    class Verifier:
        methods, fallback = {}, None
        def __call__(self, domain, url, canceled, timeout):
            return Browser()
        def extension_ready(self):
            return True

    def answer(via, host, request):
        return httpx.Response(429, text=page, headers={"content-type": "text/html; charset=utf-8"}) if host == "track.test" else None
    net = Net(answer=answer)
    result = collect(tmp_path, net, [site("track.test")], listings_for("track.test", 3), verifier=Verifier())
    company = result.related["companies"][0]
    assert company["status"] == "done" and company["verification"] == "completed"
    assert len([1 for _, h, _ in net.seen if h == "track.test"]) == 1 and len(priced(result)) == 6


def test_the_rebuilt_visit_south_walton_site_gives_the_beach_accesses_from_its_static_query(tmp_path, monkeypatch):
    """26 Nov 2026 (the trial run): visitsouthwalton.com was rebuilt with Gatsby; the map's markers are the static query
    `allBeachAccess` (page-data.json names the template and its static queries; the template's script names the query's hash).
    Fixtures cut from that day's answers (six of the 70 points)."""
    from pathlib import Path
    from studio.sources import beaches
    monkeypatch.setattr(beaches, "GATSBY_GAP", 0)
    folder = Path(__file__).parent / "fixtures" / "hedef01"
    asked = []

    def handler(request):
        asked.append(request.url.path)
        path = request.url.path
        if path == "/beach-bay-access-locations/":
            return httpx.Response(200, content=(folder / "vsw-plaj-sayfasi.html").read_bytes(), headers={"content-type": "text/html"})
        if path == "/page-data/beach-bay-access-locations/page-data.json":
            return httpx.Response(200, content=(folder / "vsw-plaj-page-data.json").read_bytes(), headers={"content-type": "application/json"})
        if path.startswith("/component---src-templates-beach-access-map-js"):
            return httpx.Response(200, content=(folder / "vsw-plaj-bileseni.js").read_bytes())
        if path == "/page-data/sq/d/2083699297.json":
            return httpx.Response(200, content=(folder / "vsw-plaj-sq.json").read_bytes(), headers={"content-type": "application/json"})
        return httpx.Response(200, content=b'{"data": {"other": {}}}')
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        batch = beaches.collect(tmp_path / "source.html", lambda *a: None, lambda: False, client=client)
    assert asked[:4] == ["/beach-bay-access-locations/", "/page-data/beach-bay-access-locations/page-data.json",
                         asked[2], "/page-data/sq/d/2083699297.json"] and len(asked) == 4          # the template names the hash: no other query asked
    assert batch.total_count == 6 and len(batch.records) == 4 and batch.excluded_count == 2          # Miramar and the bay access left out
    assert {r["city"] for r in batch.records} == {"Santa Rosa Beach", "Inlet Beach"} and {r["access_type"] for r in batch.records} == {"neighborhood"}
    assert batch.source_updated == "Nov 26, 2026 9:06:32 AM" and batch.metadata["kaynak_bicimi"] == "gatsby-statik-sorgu"
    assert all(len(r["external_id"]) == 24 for r in batch.records)                                   # the same Simpleview ids as before
    assert sorted(p.name for p in tmp_path.glob("gatsby-*")) == ["gatsby-01-page-data.json", f"gatsby-02-{Path(asked[2]).name}",
                                                                 "gatsby-03-2083699297.json"]        # every answer kept beside the page


def test_a_lane_closes_a_companys_browser_in_its_own_thread_before_the_next_company_opens_one(tmp_path):
    """HEDEF-01 trial run (26 Nov 2026): exclusive30a.com's browser stayed open and oversee.us, next in the same lane, failed to start
    its own (Playwright's sync API belongs to one thread at a time)."""
    events = []

    class Browser:
        kind = "browser"
        def __init__(self, domain):
            self.domain = domain
            events.append(("open", domain, threading.current_thread().name))
        def send(self, method, url, **kwargs):
            assert not [e for e in events if e[0] == "open" and e[1] != self.domain and ("close", e[1]) not in [(x[0], x[1]) for x in events]]
            body = "<html>LISTING</html>" if "/rentals/" in url else "ok"
            return 200, url, {"content-type": "text/html"}, body.encode()
        def close(self):
            events.append(("close", self.domain, threading.current_thread().name))

    class Verifier:
        methods, fallback = {}, None
        def __call__(self, domain, url, canceled, timeout):
            return Browser(domain)
        def extension_ready(self):
            return False
    result = collect(tmp_path, Net(), [site("guard-a.test", protected=1), site("guard-b.test", protected=1)],
                     listings_for("guard-a.test", 3) + listings_for("guard-b.test", 2, 10), verifier=Verifier())
    assert {c["status"] for c in result.related["companies"]} == {"done"} and len(priced(result)) == 10
    kinds = [(e[0], e[1]) for e in events]
    first = kinds[0][1]
    second = "guard-b.test" if first == "guard-a.test" else "guard-a.test"
    assert kinds == [("open", first), ("close", first), ("open", second), ("close", second)]
    assert {e[2] for e in events} == {"30a-isci-tarayıcı"}


def test_a_stalled_worker_is_given_up_once_and_its_task_is_never_counted_twice(tmp_path, monkeypatch):
    """Review of HEDEF-01: a stalled worker's task was requeued twice (once by the stall check, once by its own ExitDown) and its
    prices were committed twice."""
    monkeypatch.setattr(AW, "STALL_S", 0.3)
    slow = {"done": False}

    def answer(via, host, request):
        if via == "proxy 1" and request.url.path.startswith("/quote/") and not slow["done"]:
            slow["done"] = True
            time.sleep(1.0)          # longer than the stall limit
        return None
    net = Net(delay=0.01, answer=answer)
    result = collect(tmp_path, net, [site("alpha.test")], listings_for("alpha.test", 6), exits=[W.direct_exit(), proxy_exit(1)])
    pairs = [(q["lodging_id"], q["window_key"]) for q in result.related["quotes"]]
    assert len(pairs) == len(set(pairs)) == 12 and len(priced(result)) == 12
    assert any("yanıt yok" in e["metin"] for e in result.metadata["isciler"]["olaylar"])


def test_a_failure_around_a_task_never_leaves_the_run_waiting_forever(tmp_path):
    """Review of HEDEF-01: an exception outside the task itself (here the proxy's client cannot be made) killed the worker thread and
    left its task in flight: the run never ended."""
    net = Net(delay=0.005)

    def clients(exit_, hosts):
        if exit_.label == "proxy 1":
            raise RuntimeError("no client")
        return httpx.Client(transport=httpx.MockTransport(net.handler(exit_.label)))
    box = {}
    thread = threading.Thread(target=lambda: box.setdefault("r", collect(tmp_path, net, [site("alpha.test"), site("beta.test")],
                                                                          listings_for("alpha.test", 4) + listings_for("beta.test", 4, 20),
                                                                          exits=[W.direct_exit(), proxy_exit(1)], exit_client=clients)))
    thread.start()
    thread.join(timeout=30)
    assert not thread.is_alive(), "the run did not end"
    companies = {c["domain"]: c for c in box["r"].related["companies"]}
    assert all(c["status"] in ("done", "failed") for c in companies.values())
    assert any(c["status"] == "failed" and "no client" in (c["message"] or "") for c in companies.values())
