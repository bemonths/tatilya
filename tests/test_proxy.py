"""GÖREV-16 Adım 3: the user's US proxy for region-blocked sites. The address check (Housing Atlas `proxy_url_error`); the password only
in Credential Manager (a memory keyring here) and never in a file, the log or an API answer; "Proxy'yi dene" through a local fake proxy
to a fake IP service and the country warning; the region-blocked list (added by the program, added and removed in Settings, the first
rows from the extension's raw copies); the reading order; skipping without a proxy; the program's browser using the proxy only for the
listed domains (PAC); the SOCKS5 limit on screen; no proxy address in raw copies; the collectors. No real site and no real proxy."""
import base64
import json
import logging
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import keyring
import pytest
from fastapi.testclient import TestClient

from studio import credentials, logs
from studio import proxy as P
from studio.app import create_app
from studio.database import Database
from studio.sources import agency_rates as ar
from studio.sources import region_reader as R
from studio.sources import restaurant_sites as rs
from studio.sources.base import SourceError
from tests.legacy import V18_TABLES, drop_v18
from tests.test_beaches import HEADERS

FIXTURES = Path(__file__).parent / "fixtures" / "sayfa_turleri"
SECRET = "Gizli-Parola-7781"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        client.data = tmp_path
        yield client


# ---- the address and the password ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("address, error", [
    ("http://proxy.example:8080", None), ("https://proxy.example:443", None), ("socks5://proxy.example:1080", None),
    ("socks4://proxy.example:1080", "Desteklenmeyen şema: socks4 (http, https, socks5)."),
    ("http://kullanici:parola@proxy.example:8080", "Kullanıcı adı ve parolayı adrese değil, ayrı kutulara yazın."),
    ("http://proxy.example", "Adreste port yok (ör. http://sunucu:8080)."),
    ("proxy.example:8080", "Adres http://sunucu:port, https://sunucu:port ya da socks5://sunucu:port biçiminde olmalı."),
    ("http://proxy.example:8080/yol", "Adres http://sunucu:port, https://sunucu:port ya da socks5://sunucu:port biçiminde olmalı."),
    ("http://proxy.example:99999", "Adres http://sunucu:port, https://sunucu:port ya da socks5://sunucu:port biçiminde olmalı."),
])
def test_the_proxy_address_is_checked(address, error):
    assert P.proxy_url_error(address) == error


def test_the_password_lives_only_in_credential_manager(client, memory_keyring, tmp_path):
    saved = client.put("/api/abd-proxy", json={"adres": "http://proxy.example:8080", "kullanici": "abd-kullanici", "parola": SECRET})
    assert saved.status_code == 200
    view = saved.json()
    assert view["parola_kayitli"] and view["adres"] == "http://proxy.example:8080" and view["etiket"] == "http://proxy.example"
    assert memory_keyring.values[("30AStudio", "abd_proxy_parolasi")] == SECRET
    settings = json.loads((client.data / "ayarlar.json").read_text(encoding="utf-8"))
    assert settings["abd_proxy"] == {"adres": "http://proxy.example:8080", "kullanici": "abd-kullanici"}
    for path in client.data.rglob("*"):
        if path.is_file():
            assert SECRET.encode("utf-8") not in path.read_bytes(), path
    for answer in (view, client.get("/api/abd-proxy").json(),
                   client.put("/api/abd-proxy", json={"adres": "http://proxy.example:8080", "kullanici": "abd-kullanici"}).json()):
        assert SECRET not in json.dumps(answer, ensure_ascii=False) and answer["parola_kayitli"]       # saving without a password keeps it
    assert P.load(client.data).password == SECRET and "Gizli" not in repr(P.load(client.data))
    forgotten = client.delete("/api/abd-proxy/parola").json()
    assert not forgotten["parola_kayitli"] and ("30AStudio", "abd_proxy_parolasi") not in memory_keyring.values
    assert P.NO_PASSWORD in forgotten["notlar"]
    refused = client.put("/api/abd-proxy", json={"adres": "http://a:b@proxy.example:8080", "kullanici": ""})
    assert refused.status_code == 422 and refused.json()["detail"] == "Kullanıcı adı ve parolayı adrese değil, ayrı kutulara yazın."


def test_a_secret_seen_by_the_process_is_masked_in_the_log(tmp_path):
    handler = logs.setup_logging(tmp_path)
    try:
        credentials.set_secret("abd_proxy_parolasi", SECRET)
        logging.getLogger("studio.deneme").warning("Proxy hatası: %s ile bağlanılamadı", SECRET)
        try:
            raise RuntimeError(f"bağlantı {SECRET} reddedildi")
        except RuntimeError:
            logging.getLogger("studio.deneme").exception("Beklenmeyen hata")
        handler.flush()
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()
    text = logs.log_path(tmp_path).read_text(encoding="utf-8")
    assert SECRET not in text and "Proxy hatası: *** ile bağlanılamadı" in text and "bağlantı *** reddedildi" in text
    assert keyring.get_password("30AStudio", "abd_proxy_parolasi") == SECRET          # the memory keyring of the tests, never the real one


def test_a_socks5_proxy_with_a_user_name_is_said_on_screen(client):
    view = client.put("/api/abd-proxy", json={"adres": "socks5://proxy.example:1080", "kullanici": "abd", "parola": SECRET}).json()
    assert P.SOCKS_AUTH in view["notlar"] and not view["tarayici_kullanilabilir"]
    proxy = P.load(client.data)
    reader = R.RegionReader(proxy, ["cvs.com"], client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403, text="x"))),
                            browser_factory=lambda: pytest.fail("the browser cannot use this proxy"), sleep=lambda s: None)
    result = reader.read("https://www.cvs.com/")
    assert result["durum"] == "bolge_engeli" and "kullanıcı adlı SOCKS5" in result["not"]
    assert client.put("/api/abd-proxy", json={"adres": "socks5://proxy.example:1080", "kullanici": ""}).json()["tarayici_kullanilabilir"]


# ---- "Proxy'yi dene" with a local fake proxy and a fake IP service -------------------------------------------------------------------

class FakeProxy:
    """A local HTTP proxy that answers by itself (it never forwards): the IP service at ip-servisi.test and a few region-blocked pages.
    It asks for the credentials (407) when `credentials` is set."""

    def __init__(self, country="US", credentials=None):
        self.country, self.credentials, self.seen = country, credentials, []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                owner.seen.append((self.path, self.headers.get("Proxy-Authorization")))
                expected = "Basic " + base64.b64encode(owner.credentials.encode()).decode() if owner.credentials else None
                if expected and self.headers.get("Proxy-Authorization") != expected:
                    self.send_response(407)
                    self.send_header("Proxy-Authenticate", 'Basic realm="abd"')
                    self.end_headers()
                    return
                if self.path.startswith("http://ip-servisi.test/"):
                    body, kind = json.dumps({"ip": "203.0.113.7", "country": owner.country}).encode(), "application/json"
                elif self.path.startswith("http://www.cvs.test/"):
                    body, kind = b"<html><title>CVS locations</title><body>" + b"Pharmacy list. " * 50 + b"</body></html>", "text/html"
                else:
                    body, kind = b"proxy: bilinmeyen adres", "text/plain"
                self.send_response(200 if kind != "text/plain" else 502)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake_proxy(local_network):
    proxy = FakeProxy(credentials=f"abd:{SECRET}")
    yield proxy
    proxy.close()


def test_proxyyi_dene_shows_the_exit_address_and_country(client, fake_proxy, monkeypatch):
    client.put("/api/abd-proxy", json={"adres": fake_proxy.url, "kullanici": "abd", "parola": SECRET})
    monkeypatch.setattr(client.app.state, "proxy_test", lambda proxy: P.test(proxy, service="http://ip-servisi.test/json"))
    result = client.post("/api/abd-proxy/dene").json()
    assert result["ok"] and result["ip"] == "203.0.113.7" and result["ulke"] == "US" and result["uyari"] is None
    assert result["satirlar"][0] == "Proxy: http://127.0.0.1 (kullanıcı adıyla)"
    port = fake_proxy.url.rsplit(":", 1)[1]
    assert port not in json.dumps(result) and SECRET not in json.dumps(result)
    assert fake_proxy.seen[-1][0] == "http://ip-servisi.test/json"                     # through the proxy, with the user's credentials
    fake_proxy.country = "TR"
    warned = client.post("/api/abd-proxy/dene").json()
    assert warned["ok"] and warned["ulke"] == "TR" and warned["uyari"] == "Proxy'nin çıkış adresi ABD'de görünmüyor"
    client.delete("/api/abd-proxy/parola")
    client.put("/api/abd-proxy", json={"adres": fake_proxy.url, "kullanici": ""})
    failed = client.post("/api/abd-proxy/dene").json()                                  # without the credentials the proxy says 407
    assert not failed["ok"] and failed["satirlar"][-1].startswith("BAŞARISIZ") and port not in json.dumps(failed)
    client.put("/api/abd-proxy", json={"adres": "", "kullanici": ""})
    assert client.post("/api/abd-proxy/dene").json()["detail"] == "ABD proxy'si tanımlı değil: önce adresini kaydedin."


def test_the_mounts_send_only_the_listed_domains_through_the_proxy(fake_proxy):
    proxy = P.ProxySettings(fake_proxy.url, "abd", SECRET)
    page = ThreadingHTTPServer(("127.0.0.1", 0), type("Page", (BaseHTTPRequestHandler,), {
        "do_GET": lambda self: (self.send_response(200), self.send_header("Content-Length", "6"), self.end_headers(), self.wfile.write(b"direkt")),
        "log_message": lambda self, *a: None}))
    threading.Thread(target=page.serve_forever, daemon=True).start()
    try:
        with httpx.Client(mounts=proxy.mounts(["cvs.test"])) as client:
            assert "CVS locations" in client.get("http://www.cvs.test/x").text
            assert client.get(f"http://127.0.0.1:{page.server_address[1]}/").text == "direkt"
    finally:
        page.shutdown()
        page.server_close()
    assert [path for path, _ in fake_proxy.seen] == ["http://www.cvs.test/x"]


# ---- the region-blocked list ------------------------------------------------------------------------------------------------------------

def test_the_list_is_edited_in_settings(client):
    assert client.get("/api/abd-proxy").json()["bolge_engelli"] == []
    added = client.post("/api/abd-proxy/bolge-engelli", json={"alan_adi": "https://www.WinnDixie.com/locator"})
    assert added.status_code == 201 and [h["host"] for h in added.json()["bolge_engelli"]] == ["winndixie.com"]
    assert added.json()["bolge_engelli"][0]["added_by"] == "kullanici"
    assert client.post("/api/abd-proxy/bolge-engelli", json={"alan_adi": "winndixie.com"}).status_code == 409
    for bad in ("", "yerel", "127.0.0.1"):
        assert client.post("/api/abd-proxy/bolge-engelli", json={"alan_adi": bad}).status_code == 422
    with client.app.state.db.connect() as con:
        assert P.mark(con, "www.cvs.com", title=None, url="https://www.cvs.com/x", evidence="outside of the United States")
        assert not P.mark(con, "localhost")
    region = client.app.state.region_access()
    assert region.listed("https://shop.cvs.com/a") and region.listed("winndixie.com") and not region.listed("publix.com")
    region.mark("publix.com", title="International | Publix Super Markets", url="https://www.publix.com/locations")
    assert region.listed("www.publix.com")
    assert client.delete("/api/abd-proxy/bolge-engelli/winndixie.com").status_code == 200
    assert client.delete("/api/abd-proxy/bolge-engelli/winndixie.com").status_code == 404
    assert [h["host"] for h in client.get("/api/abd-proxy").json()["bolge_engelli"]] == ["cvs.com", "publix.com"]


def write_raw(folder, stem, record, page):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{stem}.json").write_text(json.dumps(record), encoding="utf-8")
    (folder / f"{stem}.html").write_text(page, encoding="utf-8")


def test_the_first_rows_come_from_the_extensions_raw_copies_and_v17_files_upgrade(tmp_path):
    folder = tmp_path / "raw" / "eklenti" / "20261011"
    cvs = (FIXTURES / "cvs-bolge-403.html").read_text(encoding="utf-8")
    write_raw(folder, "113414-a", {"adres": "https://www.cvs.com/store-locator", "baslik": "", "http_durumu": 403, "durum": "tamam",
                                   "okundu": "2026-10-11T11:34:14+00:00"}, cvs)
    write_raw(folder, "113401-b", {"adres": "https://www.hcafloridahealthcare.com/locations/x", "baslik": "", "http_durumu": None, "durum": "hata",
                                   "not": "Cannot access contents of url \"https://geo-blocked-site.dpxmedcity.net/\". Extension manifest must request "
                                          "permission to access this host.", "okundu": "2026-10-11T11:34:01+00:00"}, "")
    write_raw(folder, "113355-c", {"adres": "https://order.online/business/x", "baslik": "Cupcakes", "http_durumu": 200, "durum": "tamam"},
              "<html><title>Cupcakes</title>" + "menu " * 900 + "</html>")
    write_raw(folder, "113231-d", {"adres": "http://127.0.0.1:8830/eklenti-deneme", "baslik": "deneme", "http_durumu": 200, "durum": "tamam"},
              "<p>This site is not available in your country.</p>")
    path = tmp_path / "studio.sqlite3"
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        rows = {r[0]: r for r in con.execute("SELECT host, title, evidence, added_by, first_seen_at FROM region_blocked_hosts")}
        assert set(rows) == {"cvs.com", "hcafloridahealthcare.com"}
        assert rows["hcafloridahealthcare.com"][2] == "geo-blocked-site.dpxmedcity.net adresine yönlendi"
        assert rows["cvs.com"][3] == "program" and rows["cvs.com"][4] == "2026-10-11T11:34:14+00:00"
        drop_v18(con)
        con.execute("PRAGMA user_version=17")
        before = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in
                  con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 18
        assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        after = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in
                 con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    assert after == {**before, **V18_TABLES, "region_blocked_hosts": 2}
    assert list((tmp_path / "backups").glob("studio-v17-*.sqlite3"))


# ---- the reading order ------------------------------------------------------------------------------------------------------------------

class FakeBrowser:
    def __init__(self, kind="tamam", html=b"<html><title>Tarayici</title>drawn</html>"):
        self.kind, self.html, self.reads, self.hosts = kind, html, [], ["cvs.com"]

    def page_read(self, url, canceled, waiting):
        self.reads.append(url)
        return 200, url, "Tarayici", self.html, self.kind

    def close(self):
        pass


def reader_for(handler, browser=None, proxy=P.ProxySettings("http://abd-proxy.test:8080", "abd", SECRET)):
    slept, clock = [], [0.0]
    return R.RegionReader(proxy, ["cvs.com"], client=httpx.Client(transport=httpx.MockTransport(handler)),
                          browser_factory=(lambda: browser) if browser is not None else None, sleep=slept.append,
                          clock=lambda: clock[0]), slept


def test_the_reading_order_proxy_then_the_browser_with_the_proxy_then_skip():
    ordinary = "<html><title>CVS stores</title><body>" + "Pharmacy hours and address. " * 40 + "</body></html>"
    reader, slept = reader_for(lambda r: httpx.Response(200, html=ordinary))
    first = reader.read("https://www.cvs.com/a")
    assert (first["durum"], first["yontem"], first["proxy"], first["baslik"]) == ("tamam", "proxy", True, "CVS stores")
    second = reader.read("https://www.cvs.com/b")
    assert second["yontem"] == "proxy" and slept == [8.0]                                  # 8 s between two pages of a site
    browser = FakeBrowser()
    blocked, _ = reader_for(lambda r: httpx.Response(403, html=(FIXTURES / "akamai-access-denied.html").read_text(encoding="utf-8")), browser)
    result = blocked.read("https://www.cvs.com/a")
    assert result["durum"] == "tamam" and result["yontem"] == "tarayici+proxy" and browser.reads == ["https://www.cvs.com/a"]
    drawn_browser = FakeBrowser()
    drawn, _ = reader_for(lambda r: httpx.Response(200, html="<html><body><div id=root></div><script src=app.js></script></body></html>"), drawn_browser)
    assert drawn.read("https://www.cvs.com/a")["yontem"] == "tarayici+proxy"               # drawn by JavaScript: the browser
    failing, _ = reader_for(lambda r: httpx.Response(403, html=(FIXTURES / "cvs-bolge-403.html").read_text(encoding="utf-8")),
                            FakeBrowser(kind="bolge_engeli"))
    skipped = failing.read("https://www.cvs.com/a")
    assert skipped["durum"] == "bolge_engeli" and skipped["not"].startswith("bölge engeli: proxy'yle de okunamadı")
    assert "bölge engeli, HTTP 403" in skipped["not"] and "programın tarayıcısı: bölge engeli" in skipped["not"]
    unavailable, _ = reader_for(lambda r: httpx.Response(403, text=""))
    assert "bu bilgisayarda tarayıcı kullanılamıyor" in unavailable.read("https://www.cvs.com/a")["not"]
    nothing = R.RegionReader(None, ["cvs.com"])
    assert nothing.read("https://www.cvs.com/a")["not"] == "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)"
    pdf, _ = reader_for(lambda r: httpx.Response(200, content=b"%PDF-1.7", headers={"content-type": "application/pdf"}))
    document = pdf.read("https://www.cvs.com/menu.pdf")
    assert document["yontem"] == "proxy" and document["content_type"] == "application/pdf" and document["html"] == b"%PDF-1.7"


def test_the_programs_browser_uses_the_proxy_only_for_the_listed_domains(tmp_path, monkeypatch):
    proxy = P.ProxySettings("http://abd-proxy.test:8080", "abd", SECRET)
    pac = P.pac_script(proxy, ["www.cvs.com", "publix.com"])
    assert 'host === "cvs.com" || dnsDomainIs(host, ".cvs.com")' in pac and 'host === "publix.com"' in pac
    assert 'return "PROXY abd-proxy.test:8080";' in pac and 'return "DIRECT";' in pac and SECRET not in pac and "abd\"" not in pac
    assert 'return "SOCKS5 abd-proxy.test:1080"' in P.pac_script(P.ProxySettings("socks5://abd-proxy.test:1080"), ["cvs.com"])
    assert 'return "HTTPS abd-proxy.test:443"' in P.pac_script(P.ProxySettings("https://abd-proxy.test:443"), ["cvs.com"])
    command = R.launch_command("chrome.exe", tmp_path / "profil", pac)
    joined = " ".join(command)
    assert command[3].startswith("--proxy-pac-url=data:application/x-ns-proxy-autoconfig;base64,")
    assert base64.b64decode(command[3].split(",", 1)[1]).decode("utf-8") == pac
    assert SECRET not in joined and "--proxy-server" not in joined and "abd:" not in joined          # no credentials on the command line
    started = []

    def spawn(command):
        started.append(command)
        (Path(command[1].split("=", 1)[1]) / "DevToolsActivePort").write_text("9555\n/devtools/browser/x", encoding="utf-8")
    monkeypatch.setattr(R.bv, "find_browser", lambda: Path("chrome.exe"))
    monkeypatch.setattr(R.ProxyBrowser, "close_running", lambda self, endpoint: (self.profile / "DevToolsActivePort").unlink())
    profile = tmp_path / "proxy-profil"
    assert R.ProxyBrowser(proxy, ["cvs.com"], profile=profile, spawn=spawn, check=lambda e: True).endpoint() == "http://127.0.0.1:9555"
    R.ProxyBrowser(proxy, ["cvs.com"], profile=profile, spawn=spawn, check=lambda e: True).endpoint()
    assert len(started) == 1                                                                   # the same PAC script: the running one is used
    R.ProxyBrowser(proxy, ["cvs.com", "publix.com"], profile=profile, spawn=spawn, check=lambda e: True).endpoint()
    assert len(started) == 2 and "publix.com" in base64.b64decode(started[1][3].split(",", 1)[1]).decode()    # the list changed: started again
    assert R.proxy_profile_root().name.endswith("-proxy")


def test_the_proxy_credentials_are_answered_once_over_cdp():
    asked = set()
    first = R.auth_answer({"requestId": "1", "authChallenge": {"source": "Proxy"}}, "abd", SECRET, asked)
    assert first == {"requestId": "1", "authChallengeResponse": {"response": "ProvideCredentials", "username": "abd", "password": SECRET}}
    assert R.auth_answer({"requestId": "1", "authChallenge": {"source": "Proxy"}}, "abd", SECRET, asked)["authChallengeResponse"] == {"response": "CancelAuth"}
    assert R.auth_answer({"requestId": "2", "authChallenge": {"source": "Server"}}, "abd", SECRET, asked)["authChallengeResponse"] == {"response": "Default"}
    assert "***" in repr(R.ProxyAuth.__new__(R.ProxyAuth))


# ---- the collectors -----------------------------------------------------------------------------------------------------------------

class FakeRegion:
    def __init__(self, hosts, proxy=None, reader=None):
        self.hosts, self.proxy, self._reader, self.marked = set(hosts), proxy, reader, []

    def listed(self, url_or_host):
        return P.is_listed(self.hosts, url_or_host)

    def mark(self, host, **values):
        self.marked.append((P.host_key(host), values))
        self.hosts.add(P.host_key(host))
        return True

    def reader(self, canceled=lambda: False, waiting=None):
        return self._reader


class StubReader:
    def __init__(self):
        self.urls = []

    def read(self, url):
        self.urls.append(url)
        return {"durum": "tamam", "son_adres": url, "http_durumu": 200, "html": b"<html><title>Menu</title>menu</html>", "yontem": "proxy",
                "proxy": True, "content_type": "text/html; charset=utf-8", "not": None}

    def close(self):
        pass


def fetcher(tmp_path, handler, region):
    store = rs.RawStore(tmp_path / "raw" / "manifest.json")
    return rs.Fetcher(httpx.Client(transport=httpx.MockTransport(handler)), store, rs.HostPacer(), lambda: False, region=region), store


def test_the_restaurant_collector_reads_a_listed_domain_only_through_the_proxy(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "REQUEST_GAP", 0)
    direct = []
    no_proxy, _ = fetcher(tmp_path, lambda r: direct.append(str(r.url)) or httpx.Response(200, text="x"), FakeRegion({"grill.test"}))
    with pytest.raises(SourceError) as skipped:
        no_proxy.get("https://www.grill.test/menu", restaurant="r1", note="menü")
    assert str(skipped.value) == "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)" and direct == []
    reader = StubReader()
    through, store = fetcher(tmp_path, lambda r: pytest.fail("a listed domain never goes directly"),
                             FakeRegion({"grill.test"}, P.ProxySettings("http://abd-proxy.test:8080"), reader))
    document = through.get("https://www.grill.test/menu", restaurant="r1", note="menü")
    assert document.status == 200 and b"menu" in document.body and reader.urls == ["https://www.grill.test/menu"]
    entry = store.manifest["responses"][-1]
    assert entry["yontem"] == "proxy" and entry["proxy"] is True and "abd-proxy" not in json.dumps(store.manifest)
    region = FakeRegion(set())
    found, _ = fetcher(tmp_path, lambda r: httpx.Response(403, html=(FIXTURES / "cvs-bolge-403.html").read_text(encoding="utf-8")), region)
    with pytest.raises(SourceError) as blocked:
        found.get("https://www.pharmacy.test/", restaurant="r2", note="ana sayfa")
    assert region.marked[0][0] == "pharmacy.test" and "outside of the United States" in region.marked[0][1]["evidence"]
    assert str(blocked.value) == "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)"


def test_the_rental_collector_skips_a_listed_company_without_a_proxy(tmp_path, monkeypatch):
    monkeypatch.setattr(ar, "REQUEST_GAP", 0)
    config = {"sites": [{"domain": "kira.test", "company": "Kira", "adapter": next(iter(ar.ADAPTERS)), "enabled": 1}],
              "windows": [{"window_key": "winter", "label": "Kış", "checkin": "2027-01-16", "checkout": "2027-01-23"}],
              "input": {"run_id": "lodging-run", "searched_on": "2026-10-07", "listings": [
                  {"lodging_id": 1, "title": "Ev", "url": "https://www.kira.test/rental/1", "bedrooms": 3, "bathrooms": 2, "sleeps": 8,
                   "address": None, "latitude": None, "longitude": None, "region_ids": ["seaside"]}]}}
    with httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail("a listed company never goes directly"))) as client:
        result = ar.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config, client=client,
                            today=__import__("datetime").date(2026, 10, 8), region=FakeRegion({"kira.test"}))
    company = result.related["companies"][0]
    assert company["status"] == "stopped_blocked" and company["message"] == "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)"
