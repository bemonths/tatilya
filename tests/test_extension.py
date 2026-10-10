"""GÖREV-14 Adım 7, the program's side of the browser extension: pairing, the origin check, refusing state-changing requests from other
sites, the job (session) lifecycle with a simulated extension, raw copies of the trials, the hand-over to the program's own browser, the
collectors' extension reader and the record of what worked for a host."""
import base64
import json
import re
import threading
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from studio import extension as ext
from studio.app import create_app
from studio.sources import browser_verification as bv
from studio.sources.extension_reader import ExtensionPages, ExtensionTransport, ExtensionVerifier
from tests.test_beaches import HEADERS

ORIGIN = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"
OTHER = "chrome-extension://ponmlkjihgfedcbaponmlkjihgfedcba"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        client.data = tmp_path
        yield client


def as_extension(client, path, body=None, *, origin=ORIGIN, code=None):
    code = client.app.state.extension.code() if code is None else code
    return client.post(path, json=body or {}, headers={"Origin": origin, ext.HEADER: code})


def paired(client):
    assert as_extension(client, "/api/eklenti/eslestir", {"surum": "0.16.0"}).status_code == 200
    return client.app.state.extension


# --- pairing and origins ---------------------------------------------------------------------------------------------------------

def test_pairing_binds_the_first_extension_origin_and_the_code_lives_in_the_data_folder(client):
    bridge = client.app.state.extension
    stored = json.loads((client.data / "eklenti.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}", stored["kod"]) and stored["koken"] is None and stored["aralik_saniye"] == 8
    assert as_extension(client, "/api/eklenti/eslestir", code="YANL-ISKO").status_code == 403
    assert as_extension(client, "/api/eklenti/eslestir", origin="https://kotu.example").status_code == 403
    answer = as_extension(client, "/api/eklenti/eslestir", {"surum": "0.16.0"})
    assert answer.status_code == 200 and answer.json()["eslesti"] and answer.headers["access-control-allow-origin"] == ORIGIN
    assert json.loads((client.data / "eklenti.json").read_text(encoding="utf-8"))["koken"] == ORIGIN
    assert as_extension(client, "/api/eklenti/eslestir", origin=OTHER).status_code == 403          # another extension is refused
    status = client.get("/api/tarayici-eklentisi").json()
    assert status["eslesti"] and status["bagli"] and status["surum"] == "0.16.0" and len(status["kurulum"]) == 6
    assert [s["alan_adi"] for s in status["sorunlu_siteler"]][:2] == ["realjoy.com", "order.online"]
    assert status["kurulum_resimleri"] == ["1-uzantilar.png", "2-gelistirici-modu.png", "3-eklenti-penceresi.png"]
    assert client.get("/eklenti-kurulum/2-gelistirici-modu.png").headers["content-type"] == "image/png"
    assert client.get("/eklenti-kurulum/..%2Fmanifest.json").status_code == 404
    renewed = client.post("/api/tarayici-eklentisi/kod-yenile").json()
    assert renewed["kod"] != stored["kod"] and not renewed["eslesti"]
    assert as_extension(client, "/api/eklenti/sor", code=stored["kod"]).status_code == 403          # the old pairing is gone
    assert as_extension(client, "/api/eklenti/eslestir", origin=OTHER).status_code == 200 and bridge.config["koken"] == OTHER


def test_the_extension_api_answers_only_the_paired_origin_with_its_code(client):
    paired(client)
    assert as_extension(client, "/api/eklenti/sor", {"surum": "0.16.0", "izinli": []}).status_code == 200
    assert as_extension(client, "/api/eklenti/sor", origin=OTHER).status_code == 403
    assert as_extension(client, "/api/eklenti/sor", code="AAAA-BBBB").status_code == 403
    assert client.post("/api/eklenti/sor", json={}).status_code == 403                                 # the program's own page cannot either
    assert client.post("/api/eklenti/sor", json={}, headers={"Origin": "https://kotu.example", ext.HEADER: "x"}).status_code == 403
    preflight = client.options("/api/eklenti/sor", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"})
    assert preflight.status_code == 204 and preflight.headers["access-control-allow-origin"] == ORIGIN
    assert ext.HEADER in preflight.headers["access-control-allow-headers"]
    assert client.options("/api/eklenti/sor", headers={"Origin": "https://kotu.example"}).status_code == 403
    assert client.get("/api/eklenti/sor", headers={"Origin": ORIGIN}).status_code == 403
    assert "access-control-allow-origin" not in client.get("/api/health").headers                     # no CORS on the program's API


def test_state_changing_requests_from_other_sites_are_refused(client):
    for headers in ({"Origin": "https://kotu.example"}, {"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"}):
        refused = client.post("/api/jobs", json={"kind": "catalog_audit"}, headers=headers)
        assert refused.status_code == 403
    assert client.post("/api/tarayici-eklentisi/kod-yenile", headers={"Origin": ORIGIN}).status_code == 403
    assert client.post("/api/tarayici-eklentisi/kod-yenile", headers={"Sec-Fetch-Site": "same-origin"}).status_code == 200
    trial = client.get("/eklenti-deneme").text
    assert "p.id = 'deneme-sonuc'" in trial and "gerçek bir site değildir" in trial


# --- the job lifecycle with a simulated extension ----------------------------------------------------------------------------------

class FakeExtension(threading.Thread):
    """Does what background.js does, over the extension API: asks for a session, takes its items, posts results."""

    def __init__(self, client, pages, *, stop_after=None):
        super().__init__(daemon=True)
        self.client, self.pages, self.stop_after = client, pages, stop_after
        self.seen, self.done = [], threading.Event()
        self.reported = []

    def run(self):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not self.done.is_set():
            answer = as_extension(self.client, "/api/eklenti/sor", {"surum": "0.16.0", "izinli": ["testserver", "ornek.test"]}).json()
            job = answer["is"]
            if not job:
                time.sleep(0.05)
                continue
            while True:
                step = as_extension(self.client, f"/api/eklenti/is/{job['id']}/sonraki").json()
                if step.get("bitti"):
                    as_extension(self.client, f"/api/eklenti/is/{job['id']}/bitti")
                    break
                if step.get("bekle"):
                    time.sleep(0.05)
                    continue
                item = step["oge"]
                self.seen.append((job["alan_adi"], job["aralik_saniye"], item))
                result = self.pages(item)
                if result.get("durum") == "dogrulama-sonra":
                    as_extension(self.client, f"/api/eklenti/is/{job['id']}/durum", {"dogrulama": item["adres"]})
                    self.reported.append(item["adres"])
                    result = {"durum": "tamam", "html": "<html><title>Geçti</title>ok</html>", "son_adres": item["adres"], "baslik": "Geçti"}
                as_extension(self.client, f"/api/eklenti/is/{job['id']}/sonuc", {"oge_id": item["id"], **result})


def page_server(item):
    url = item["adres"]
    if item["tur"] == "istek":
        return {"durum": "tamam", "http_durumu": 200, "son_adres": url, "basliklar": {"content-type": "application/json"},
                "govde_base64": base64.b64encode(b'{"ok": true}').decode()}
    if url.endswith("/giris"):
        return {"durum": "giris", "son_adres": url, "baslik": "Sign in", "not": "Sayfa giriş istiyor; okunmadı (giriş gerekiyor)."}
    if url.endswith("/dogrulama"):
        return {"durum": "dogrulama-sonra"}
    return {"durum": "tamam", "son_adres": url + "#son", "baslik": "Örnek", "http_durumu": 200, "html": f"<html><title>Örnek</title>{url}</html>"}


def test_a_session_goes_page_by_page_through_the_extension(client):
    bridge = paired(client)
    fake = FakeExtension(client, page_server)
    fake.start()
    session = bridge.open("www.ornek.test", purpose="deneme")
    first = session.page("https://ornek.test/a", {"oge": "#icerik"})
    assert first["durum"] == "tamam" and first["html"] == "<html><title>Örnek</title>https://ornek.test/a</html>".encode("utf-8")
    assert first["son_adres"] == "https://ornek.test/a#son" and first["yontem"] == "eklenti" and len(first["sha256"]) == 64
    login = session.page("https://ornek.test/giris")
    assert login["durum"] == "giris" and login["html"] is None
    verified = session.page("https://ornek.test/dogrulama")
    assert verified["durum"] == "tamam" and fake.reported == ["https://ornek.test/dogrulama"]
    status, final, headers, body = session.request("POST", "https://ornek.test/api", headers={"Accept": "application/json"}, body="{}")
    assert (status, body) == (200, b'{"ok": true}') and headers["content-type"] == "application/json"
    session.close()
    fake.done.set()
    fake.join(5)
    domains = {d for d, _, _ in fake.seen}
    assert domains == {"ornek.test"} and {gap for _, gap, _ in fake.seen} == {8}
    assert [i["bekle"] for _, _, i in fake.seen if i["tur"] == "sayfa"][0] == {"oge": "#icerik"}
    assert [i["sira"] for _, _, i in fake.seen] == [0, 1, 2, 3]


def test_a_site_without_permission_waits_and_is_listed_for_the_user(client):
    bridge = paired(client)
    session = bridge.open("izinsiz.test")
    as_extension(client, "/api/eklenti/sor", {"surum": "0.16.0", "izinli": []})
    assert bridge.take() is None and "izinsiz.test" in client.get("/api/tarayici-eklentisi").json()["izin_bekleyen_alan_adlari"]
    as_extension(client, "/api/eklenti/sor", {"surum": "0.16.0", "izinli": ["izinsiz.test"]})
    assert client.get("/api/tarayici-eklentisi").json()["izin_bekleyen_alan_adlari"] == []
    session.close()
    assert bridge.permitted("127.0.0.1") and bridge.permitted("localhost")                       # the program's own trial page


def test_the_trial_reads_the_local_page_and_keeps_a_raw_copy(client):
    paired(client)
    fake = FakeExtension(client, lambda item: {"durum": "tamam", "son_adres": item["adres"], "baslik": "30A Studio · eklenti deneme sayfası",
                                               "http_durumu": 200, "html": "<p id='deneme-sonuc'>hazır</p>"})
    fake.start()
    result = client.post("/api/tarayici-eklentisi/deneme").json()
    fake.done.set()
    assert result["durum"] == "tamam" and result["yontem"] == "eklenti" and result["adres"].endswith("/eklenti-deneme")
    raw = client.data / result["dosya"]
    assert raw.read_bytes() == b"<p id='deneme-sonuc'>hazir</p>".replace(b"hazir", "hazır".encode("utf-8"))
    record = json.loads(raw.with_suffix(".json").read_text(encoding="utf-8"))
    assert record["sha256"] == result["sha256"] and record["yontem"] == "eklenti"
    assert fake.seen[0][2]["bekle"] == {"oge": "#deneme-sonuc"}


def test_trials_and_jobs_say_when_the_extension_is_missing(client):
    assert client.post("/api/tarayici-eklentisi/deneme").json()["detail"].startswith("Eklenti eşleşmemiş")
    bridge = paired(client)
    bridge.last_seen = time.time() - 60
    assert "Eklenti bağlı değil" in client.post("/api/tarayici-eklentisi/deneme").json()["detail"]
    assert client.put("/api/tarayici-eklentisi/ayarlar", json={"aralik_saniye": 2}).status_code == 422
    assert client.put("/api/tarayici-eklentisi/ayarlar", json={"aralik_saniye": 12}).json()["aralik_saniye"] == 12


def test_a_job_waiting_for_the_extension_can_be_handed_to_the_programs_browser(client):
    bridge = paired(client)
    db = client.app.state.db
    job = db.add_job("source_collection", "Restoranlar")
    db.update_job(job, status="running", message="Çalışıyor")
    bridge.last_seen = time.time() - 60                                               # Chrome is closed
    access = ext.JobAccess(bridge, db, job)
    session = access.open("ornek.test")
    outcome = []
    worker = threading.Thread(target=lambda: outcome.append(pytest.raises(ext.HandedOver, session.page, "https://ornek.test/")), daemon=True)
    worker.start()
    deadline = time.monotonic() + 5
    while not (db.job(job)["progress_info"] or {}).get("bekliyor"):
        assert time.monotonic() < deadline
        time.sleep(0.05)
    assert db.job(job)["message"].startswith("Eklenti bekleniyor")
    assert client.post(f"/api/tarayici-eklentisi/devret/{job}").status_code == 200
    worker.join(5)
    assert outcome and not worker.is_alive()
    assert db.job(job)["progress_info"]["devredildi"] is True
    with pytest.raises(ext.HandedOver):
        access.open("baska.test")


# --- the collectors' reader ----------------------------------------------------------------------------------------------------

class FakeSession:
    def __init__(self, answers):
        self.answers, self.closed, self.requests = answers, False, []

    def page(self, url, wait=None, canceled=None, timeout=None):
        answer = self.answers[url]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def request(self, method, url, headers=None, body=None, canceled=None, timeout=None):
        self.requests.append((method, url, headers, body))
        return 200, url, {"Content-Type": "application/pdf"}, b"%PDF"

    def close(self):
        self.closed = True


class FakeAccess:
    paired = True

    def __init__(self, answers):
        self.answers, self.opened = answers, []

    def open(self, domain, purpose=""):
        session = FakeSession(self.answers)
        self.opened.append((domain, session))
        return session


def test_extension_pages_give_the_restaurant_collector_pages_and_fall_back_after_a_hand_over():
    ok = {"durum": "tamam", "son_adres": "https://a.test/menu", "http_durumu": 200, "html": b"<html>menu</html>"}
    access = FakeAccess({"https://a.test/menu": ok, "https://a.test/giris": {"durum": "giris"}, "https://b.test/": ext.HandedOver("devredildi"),
                         "https://a.test/dogrulama": {"durum": "dogrulama", "son_adres": "https://a.test/dogrulama", "html": b"<title>Just a moment...</title>"}})

    class Fallback:
        def goto(self, url):
            return 200, url, "text/html", b"<html>cdp</html>"

        def wait_all(self, sites, canceled, timeout, waiting):
            return set(sites)

        def close(self):
            pass

    pages = ExtensionPages(access, fallback=Fallback)
    assert pages.goto("https://a.test/menu") == (200, "https://a.test/menu", "text/html; charset=utf-8", b"<html>menu</html>")
    assert pages.method_note == "eklenti" and pages.current()[3] == b"<html>menu</html>"
    with pytest.raises(Exception, match="giriş gerekiyor"):
        pages.goto("https://a.test/giris")
    assert pages.goto("https://a.test/dogrulama")[0] == 403                                       # left for the end; not waited again
    assert pages.wait_all({"a.test": "https://a.test/dogrulama"}, lambda: False, 900, None) == set()
    assert pages.request("https://a.test/menu.pdf")[2:] == ("application/pdf", b"%PDF")
    assert pages.goto("https://b.test/")[3] == b"<html>cdp</html>" and pages.method_note == "tarayıcı"
    assert pages.wait_all({"b.test": "https://b.test/"}, lambda: False, 900, None) == {"b.test"}
    assert pages.methods == {"a.test": "eklenti", "b.test": "tarayici"}
    assert [d for d, _ in access.opened] == ["a.test", "b.test"]                                   # one session per domain, reused


def test_extension_verifier_and_transport_for_the_rental_collector():
    page = {"durum": "tamam", "son_adres": "https://kira.test/", "html": b"<html>kira</html>"}
    blocked = {"durum": "tamam", "son_adres": "https://engel.test/", "html": b"Sorry, you have been blocked", "baslik": "Engel"}
    access = FakeAccess({"https://kira.test/": page, "https://engel.test/": blocked, "https://giris.test/": {"durum": "giris"},
                         "https://bekle.test/": {"durum": "dogrulama"}})
    verifier = ExtensionVerifier(access)
    transport = verifier("kira.test", "https://kira.test/", lambda: False, 20)
    assert isinstance(transport, ExtensionTransport) and transport.kind == "eklenti"
    status, final, headers, body = transport.send("POST", "https://kira.test/api", params={"a": "1"}, json_body={"q": 2},
                                                  headers={"User-Agent": "x", "Accept": "application/json"})
    method, url, sent_headers, sent_body = access.opened[0][1].requests[0]
    assert (method, url, sent_body) == ("POST", "https://kira.test/api?a=1", '{"q": 2}') and "User-Agent" not in sent_headers
    with pytest.raises(bv.SiteBlocked):
        verifier("engel.test", "https://engel.test/", lambda: False, 20)
    with pytest.raises(bv.SiteBlocked, match="giriş gerekiyor"):
        verifier("giris.test", "https://giris.test/", lambda: False, 20)
    assert verifier("bekle.test", "https://bekle.test/", lambda: False, 20) is None
    assert verifier.wait_all({"bekle.test": "https://bekle.test/"}, lambda: False, 900) == set()
    assert verifier.methods == {"kira.test": "eklenti"}


def test_what_worked_for_a_host_is_kept_in_browser_hosts(client):
    db = client.app.state.db
    with db.connect() as con:
        bv.mark_hosts(con, [{"host": "www.order.online", "url": "https://order.online/x", "reason": "doğrulama sayfası"}], "deneme/1")
        bv.record_methods(con, {"order.online": "eklenti", "yok.test": "eklenti", "kotu.test": "baska"})
        rows = [dict(r) for r in con.execute("SELECT host, method, method_at FROM browser_hosts")]
    assert len(rows) == 1 and rows[0]["host"] == "order.online" and rows[0]["method"] == "eklenti" and rows[0]["method_at"]


def test_the_extension_uses_the_programs_verification_markers():
    logic = (ROOT / "eklenti" / "logic.js").read_text(encoding="utf-8")
    source = re.search(r"CHALLENGE_SOURCE = String\.raw`([^`]*)`", logic).group(1)
    blocked = re.search(r"BLOCKED_SOURCE = String\.raw`([^`]*)`", logic).group(1)
    assert source == bv.CHALLENGE.pattern and blocked == bv.BLOCKED.pattern


def test_the_manifest_asks_only_for_the_narrow_permissions():
    manifest = json.loads((ROOT / "eklenti" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3 and manifest["name"] == "30A Studio Yardımcısı"
    assert sorted(manifest["permissions"]) == ["alarms", "notifications", "scripting", "storage", "tabs"]
    assert manifest["host_permissions"] == ["http://127.0.0.1/*"] and manifest["optional_host_permissions"] == ["https://*/*", "http://*/*"]
    text = json.dumps(manifest)
    for forbidden in ("cookies", "history", "bookmarks", "downloads", "debugger", "webRequest", "<all_urls>"):
        assert forbidden not in text
    code = "".join((ROOT / "eklenti" / name).read_text(encoding="utf-8") for name in ("background.js", "popup.js", "logic.js"))
    for forbidden in ("chrome.debugger", "chrome.cookies", "chrome.history", ".click()", "dispatchEvent", "chrome.downloads"):
        assert forbidden not in code
    assert all(len(line) < 400 for line in code.splitlines())                                       # readable, not minified
