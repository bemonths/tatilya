"""GÖREV-16 Adım 2, the program's side: every call of the extension counts as "seen"; while it works it reports its stage and Settings
and the job panel say "Eklenti çalışıyor: <site> · <durum>"; "Bağlı değil" only after 60 s of silence during a job (20 s otherwise);
"Bu sayfayı atla" from the job panel; the new page results; the trial table with the page kinds, the region-blocked domains kept away
from the extension (read through the proxy, or skipped without one) and the trial list's realjoy.com page."""
import json
import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from studio import extension as ext
from studio import proxy as P
from studio.app import create_app
from studio.destinations import thirty_a
from studio.sources import region_reader as R
from tests.test_beaches import HEADERS
from tests.test_extension import ORIGIN, as_extension, paired

PUBLIX = "<html><head><title>International | Publix Super Markets</title></head><body>We are unable to service customers outside of the United States.</body></html>"


class Clock:
    def __init__(self, now=1_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        client.data = tmp_path
        yield client


def test_every_call_of_the_extension_counts_and_a_job_gets_60_seconds(client):
    bridge = paired(client)
    clock = Clock()
    bridge.clock = clock
    bridge.last_seen = clock.now - 100
    assert not bridge.connected
    as_extension(client, "/api/eklenti/is/yok/sonuc", {"oge_id": "x"})            # even a call about an unknown job is a sign of life
    assert bridge.last_seen == clock.now and bridge.connected
    clock.now += 30
    assert not bridge.connected and client.get("/api/tarayici-eklentisi").json()["bagli_esigi_saniye"] == 20
    session = bridge.open("ornek.test")
    bridge.allowed = ["ornek.test"]
    assert bridge.take()["alan_adi"] == "ornek.test"                                 # the extension took the job: it may be busy with a page
    assert bridge.busy and bridge.connected and client.get("/api/tarayici-eklentisi").json()["bagli_esigi_saniye"] == 60
    clock.now += 31
    assert not bridge.connected                                                        # 61 s without a word while a job runs
    session.close()


def test_the_stage_is_shown_in_settings_and_in_the_job_panel(client):
    bridge = paired(client)
    db = client.app.state.db
    job_id = db.add_job("eklenti_deneme", "deneme")
    access = ext.JobAccess(bridge, db, job_id)
    session = access.open("cvs.com", purpose="deneme")
    bridge.allowed = ["cvs.com"]
    taken = bridge.take()
    answer = as_extension(client, f"/api/eklenti/is/{taken['id']}/durum", {"asama": {"asama": "okunuyor", "adres": "https://www.cvs.com/x"}})
    assert answer.json() == {"alindi": True, "atla": False}
    view = client.get("/api/tarayici-eklentisi").json()
    assert view["calisiyor"] == "cvs.com · sayfa okunuyor" and view["acik_oturumlar"][0]["asama"] == "sayfa okunuyor"
    assert db.job(job_id)["message"] == "Eklenti çalışıyor: cvs.com · sayfa okunuyor"
    as_extension(client, f"/api/eklenti/is/{taken['id']}/durum", {"asama": {"asama": "bekleme", "adres": "https://www.cvs.com/y"}})
    assert db.job(job_id)["message"] == "Eklenti çalışıyor: cvs.com · bekleme (hız kuralı)"
    as_extension(client, f"/api/eklenti/is/{taken['id']}/durum", {"dogrulama": "https://www.cvs.com/y"})
    as_extension(client, f"/api/eklenti/is/{taken['id']}/durum", {"asama": {"asama": "dogrulama", "adres": "https://www.cvs.com/y", "kalan_s": 600}})
    job = db.job(job_id)
    assert job["waiting_for"] == "cvs.com" and "Bu sayfayı atla" in job["message"]           # the verification message stays
    assert client.get("/api/tarayici-eklentisi").json()["calisiyor"] == "cvs.com · doğrulama bekleniyor (kalan 10 dk)"
    assert ext.stage_text({"asama": "dogrulama", "bitis": 1045.0}, now=1000.0) == "doğrulama bekleniyor (kalan 45 sn)"
    assert ext.stage_text({"asama": "aciliyor"}) == "sayfa açılıyor"
    session.close()


def test_bu_sayfayi_atla_from_the_job_panel_reaches_the_extension(client):
    bridge = paired(client)
    db = client.app.state.db
    job_id = db.add_job("eklenti_deneme", "deneme")
    session = ext.JobAccess(bridge, db, job_id).open("ornek.test")
    bridge.allowed = ["ornek.test"]
    taken = bridge.take()
    refused = client.post(f"/api/tarayici-eklentisi/atla/{job_id}")
    assert refused.status_code == 409 and refused.json()["detail"] == "Bu işte doğrulama bekleyen sayfa yok."
    assert client.post("/api/tarayici-eklentisi/atla/yok").status_code == 404
    as_extension(client, f"/api/eklenti/is/{taken['id']}/durum", {"dogrulama": "https://ornek.test/a"})
    assert client.post(f"/api/tarayici-eklentisi/atla/{job_id}").json() == {"atlaniyor": True}
    assert as_extension(client, f"/api/eklenti/is/{taken['id']}/durum", {"asama": {"asama": "dogrulama"}}).json()["atla"] is True
    assert as_extension(client, f"/api/eklenti/is/{taken['id']}/durum", {"asama": {"asama": "dogrulama"}}).json()["atla"] is False
    session.close()


def test_the_new_page_results_are_kept_with_their_page(client):
    bridge = paired(client)
    session = bridge.open("ornek.test")
    bridge.allowed = ["ornek.test"]
    taken = bridge.take()
    results = {}
    for state, html in (("bolge_engeli", PUBLIX), ("erisim_reddedildi", "<h1>Access Denied</h1>"), ("yonlendi", None), ("atlandi", None)):
        item = {"tur": "sayfa", "adres": f"https://ornek.test/{state}", "bekle": {"saniye": 1}, "id": state, "sira": 0}
        session.in_flight[state] = item
        assert bridge.deliver(taken["id"], state, {"durum": state, "html": html, "baslik": "b", "not": f"not {state}"})
        results[state] = session.results.pop(state)
    assert results["bolge_engeli"]["durum"] == "bolge_engeli" and results["bolge_engeli"]["html"] == PUBLIX
    assert results["erisim_reddedildi"]["durum"] == "erisim_reddedildi" and results["yonlendi"]["not"] == "not yonlendi"
    assert results["atlandi"]["durum"] == "atlandi"
    session.close()


class TrialExtension(threading.Thread):
    """The extension for the trial job: every domain is permitted; `pages(url)` gives the result."""

    def __init__(self, client, pages):
        super().__init__(daemon=True)
        self.client, self.pages, self.asked, self.done = client, pages, [], threading.Event()

    def run(self):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not self.done.is_set():
            job = as_extension(self.client, "/api/eklenti/sor", {"surum": ext.EXPECTED_VERSION,
                                                                  "izinli": ["ornek.test", "publix.com", "cvs.com", "winndixie.com"]}).json()["is"]
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
                self.asked.append(item["adres"])
                as_extension(self.client, f"/api/eklenti/is/{job['id']}/sonuc", {"oge_id": item["id"], **self.pages(item["adres"])})


def trial_pages(url):
    if "publix" in url:
        return {"durum": "bolge_engeli", "son_adres": url, "baslik": "International | Publix Super Markets", "http_durumu": 200, "html": PUBLIX,
                "not": "Bölge engeli: site ABD dışından gelen ziyaretçiye hizmet vermiyor; beklenmedi, atlandı."}
    if "winndixie" in url:
        return {"durum": "erisim_reddedildi", "son_adres": url, "baslik": "Access Denied", "http_durumu": 403,
                "html": "<h1>Access Denied</h1>You don't have permission to access", "not": "Erişim reddedildi"}
    return {"durum": "tamam", "son_adres": url, "baslik": "Örnek", "http_durumu": 200, "html": "<html><title>Örnek</title>içerik</html>"}


def run_trial(client, monkeypatch, sites, pages=trial_pages):
    monkeypatch.setattr(thirty_a, "EXTENSION_TRIAL_SITES", sites)
    fake = TrialExtension(client, pages)
    fake.start()
    job = client.post("/api/tarayici-eklentisi/sorunlu-siteler").json()
    deadline = time.monotonic() + 30
    while client.app.state.db.job(job["id"])["status"] in ("queued", "running"):
        assert time.monotonic() < deadline
        time.sleep(0.05)
    fake.done.set()
    fake.join(5)
    return client.app.state.db.job(job["id"]), fake


SITES = (("ornek.test", "https://ornek.test/a", "örnek"), ("publix.com", "https://www.publix.com/locations", "süpermarket"),
         ("cvs.com", "https://www.cvs.com/store-locator", "eczane"), ("winndixie.com", "https://www.winndixie.com/locator", "süpermarket"))


def test_the_trial_table_has_the_kinds_and_keeps_region_blocked_sites_away_from_the_extension(client, monkeypatch):
    paired(client)
    assert client.post("/api/abd-proxy/bolge-engelli", json={"alan_adi": "cvs.com"}).status_code == 201
    job, fake = run_trial(client, monkeypatch, SITES)
    rows = {r["alan_adi"]: r for r in job["result"]["siteler"]}
    assert rows["ornek.test"]["tur"] == "tamam" and rows["ornek.test"]["yontem"] == "eklenti"
    assert rows["publix.com"]["tur"] == "bolge_engeli" and rows["publix.com"]["not"] == P.NO_PROXY_SKIP
    assert rows["cvs.com"]["tur"] == "bolge_engeli" and rows["cvs.com"]["not"] == P.NO_PROXY_SKIP and rows["cvs.com"]["yontem"] is None
    assert rows["winndixie.com"]["tur"] == "erisim_reddedildi"
    assert not [u for u in fake.asked if "cvs.com" in u]                    # a listed domain is never given to the extension
    listed = {h["host"]: h for h in client.get("/api/abd-proxy").json()["bolge_engelli"]}
    assert set(listed) == {"cvs.com", "publix.com"} and listed["publix.com"]["added_by"] == "program"
    assert listed["publix.com"]["title"] == "International | Publix Super Markets" and listed["cvs.com"]["added_by"] == "kullanici"
    assert "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)" in " ".join(e["text"] for e in job["log"])


class ProxyRegion(R.RegionAccess):
    """The app's region access with a proxy and a client that answers like the proxy (no network)."""

    def __init__(self, db, data_dir, handler):
        super().__init__(db, data_dir, proxy_loader=lambda d: P.ProxySettings("http://abd-proxy.test:8080", "kullanici", "parola-gizli-123"),
                         browser_factory=lambda: None)
        self.handler = handler

    def reader(self, canceled=lambda: False, waiting=None, **kwargs):
        return R.RegionReader(self.proxy, sorted(self.hosts), client=httpx.Client(transport=httpx.MockTransport(self.handler)),
                              canceled=canceled, waiting=waiting, sleep=lambda s: None)


def test_with_a_proxy_the_region_blocked_sites_are_read_through_it(client, monkeypatch):
    paired(client)
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, html="<html><title>Publix locations</title><body>" + "Store list. " * 60 + "</body></html>")
    db = client.app.state.db
    client.app.state.region_access = lambda: ProxyRegion(db, client.data, handler)
    job, fake = run_trial(client, monkeypatch, SITES[:2])
    rows = {r["alan_adi"]: r for r in job["result"]["siteler"]}
    assert rows["publix.com"]["tur"] == "tamam" and rows["publix.com"]["yontem"] == "proxy" and rows["publix.com"]["proxy"] is True
    assert rows["publix.com"]["eklenti"] == "bölge engeli gördü; alan adı listeye eklendi" and seen == ["https://www.publix.com/locations"]
    record = json.loads((client.data / rows["publix.com"]["dosya"]).with_suffix(".json").read_text(encoding="utf-8"))
    assert record["yontem"] == "proxy" and record["proxy"] is True
    text = (client.data / rows["publix.com"]["dosya"]).with_suffix(".json").read_text(encoding="utf-8")
    assert "abd-proxy.test" not in text and "8080" not in text and "parola-gizli-123" not in text      # never the proxy's address


def test_the_trial_list_has_realjoys_30a_listing_page():
    sites = dict((d, u) for d, u, _ in thirty_a.EXTENSION_TRIAL_SITES)
    assert sites["realjoy.com"] == "https://www.realjoy.com/beach-rentals/30a-vacation-rentals"
    assert {"cvs.com", "publix.com", "hcafloridahealthcare.com", "winndixie.com", "thefreshmarket.com", "order.online"} <= set(sites)


def test_settings_say_when_chromes_extension_is_older_than_the_folder(client):
    as_extension(client, "/api/eklenti/eslestir", {"surum": "0.16.0"})
    view = client.get("/api/tarayici-eklentisi").json()
    assert view["eski_surum"] and view["beklenen_surum"] == ext.EXPECTED_VERSION
    manifest = json.loads((ext.Path(__file__).resolve().parents[1] / "eklenti" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == ext.EXPECTED_VERSION and "proxy" not in manifest["permissions"]
    as_extension(client, "/api/eklenti/sor", {"surum": ext.EXPECTED_VERSION, "izinli": []})
    assert not client.get("/api/tarayici-eklentisi").json()["eski_surum"]
