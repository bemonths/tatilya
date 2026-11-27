"""HEDEF-02: the night of 27 November 2026 — the rental price run's storing step failed, the result was lost; now it is not.

- the cause: RealJoy's calendar answers wrote rule_source "takvim" (the schema takes "sayfa" and "yanıt"); the fixture is the real page
  of that night (`raw/b8055d2a…/responses/000595.gz`, realjoy.com/beach-rentals/stay-salty, 26 Nov 2026 23:38:59 UTC);
- a result whose storing fails is written to `<data>/kurtarma/<job>/` and saved later with "Kurtarılan sonucu kaydet";
- a failed run with a raw copy is rebuilt from its own answers ("Ham kopyadan yeniden kur", studio/sources/agency_replay.py);
- the trial run stores the latest real run at full size ("kaydetme sınaması").
"""
import gzip
import json
import shutil
import sqlite3
from datetime import date
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from studio import recovery
from studio.app import create_app
from studio.database import Database
from studio.sources import agency_rates as ar
from studio.sources import agency_replay as replay
from studio.sources.agency_adapters import ADAPTERS
from studio.sources.base import CollectionResult, SourceError
from tests.legacy import AGENCY_URL
from tests.test_beaches import HEADERS, finished
from tests import test_agency_rates as ta
from tests.test_agency_rates import fast  # noqa: F401  (autouse: no pacing in the synthetic runs)
from tests import test_lodging as tl

FIX = Path(__file__).parent / "fixtures" / "hedef02"
NIGHT_PAGE = "https://www.realjoy.com/beach-rentals/stay-salty"
FEB = {"window_key": "ay-2027-02", "label": "Şubat 2027 · 13–20 Şubat", "checkin": "2027-02-13", "checkout": "2027-02-20", "nights": 7,
       "checkin_date": date(2027, 2, 13), "checkout_date": date(2027, 2, 20), "status": "queried"}


def night_page():
    return gzip.decompress((FIX / "realjoy-stay-salty.html.gz").read_bytes()).decode("utf-8")


def night_quote():
    """The answer the collector gave that night for the February week of stay-salty: the page's calendar shows it taken."""
    info = ADAPTERS["realjoy"].parse_page(night_page(), NIGHT_PAGE)
    def never(*args, **kwargs):
        raise AssertionError("a week the calendar shows taken is not asked")
    session = type("S", (), {"request": staticmethod(never)})()
    return ar.ask_quote(session, ADAPTERS["realjoy"], info, FEB, lambda call: call())


def store_one(tmp_path, quote):
    """The real storing step (complete_source_run → store_records) for one listing and its one answer."""
    db = Database(tmp_path / "studio.sqlite3"); db.initialize()
    connector = ar.AgencyRatesConnector()
    source = next(s for s in db.sources() if s["url"] == AGENCY_URL)
    job = db.add_job("source_collection", "kiralama", source["id"], connector, source["version"])
    db.update_job(job, status="running")
    with db.connect() as con:      # the Book>Direct run the prices were asked for (only its snapshot row matters here)
        con.execute("INSERT INTO lodging_snapshots (run_id,clone_host,front_end_path,default_category_id,searched_on,request_count,listing_count) "
                    "VALUES (?,?,?,?,?,?,?)", (job, "visitsouthwalton.bookdirect.net", "/", 1, "2026-11-26", 0, 1))
    listing = {"lodging_id": 1, "title": "Stay Salty", "bedrooms": 3, "region_ids": ["seaside"], "listing_url": NIGHT_PAGE,
               "url_host": "realjoy.com", "domain": "realjoy.com", "page_status": "matched", "page_url": NIGHT_PAGE, "http_status": 200,
               "site_listing_id": "1097", "message": None, "link_status": None, "match_method": "address", "match_note": None}
    company = {"domain": "realjoy.com", "company": "RealJoy Vacations", "adapter": "realjoy", "status": "done", "listing_count": 1,
               "matched_count": 1, "quote_count": 1, "priced_count": 0, "request_count": 1, "verification": None, "message": None,
               "protected": 1, "guest_rule": "two_adults", "inventory_count": None, "inventory_raw_sha256": None, "own_count": 0,
               "own_outside": None, "own_on_bookdirect": None, "match_counts": {"link": 0, "address": 1, "location": 0}}
    window = {k: FEB[k] for k in ("window_key", "label", "checkin", "checkout", "nights", "status")}
    related = {"snapshot": {"lodging_run_id": job, "queried_on": "2026-11-26", "request_count": 1, "listing_count": 1},
               "windows": [window], "companies": [company], "quotes": [{**quote, "lodging_id": 1, "window_key": FEB["window_key"]}],
               "own_listings": [], "own_quotes": [], "published": [], "browser_hosts": [], "okuma_yontemleri": {}}
    db.complete_source_run(job, CollectionResult([listing], 1, 0, None, {}, related), connector)
    return db, job


def test_the_nights_realjoy_calendar_answer_is_a_page_rule_and_is_stored(tmp_path):
    quote = night_quote()
    assert (quote["status"], quote["available"], quote["rule_source"]) == ("unavailable", 0, "sayfa")
    assert "takvimi bu tarihleri dolu" in quote["message"]
    db, job = store_one(tmp_path, quote)
    assert db.job(job)["status"] == "done"
    with db.connect() as con:
        assert con.execute("SELECT rule_source FROM agency_rate_quotes WHERE run_id=?", (job,)).fetchone()[0] == "sayfa"


def test_the_nights_value_still_breaks_the_schema_and_a_kept_old_result_is_mapped(tmp_path, monkeypatch):
    old = {**night_quote(), "rule_source": "takvim"}           # what the collector wrote before the fix
    monkeypatch.setattr(ar, "checked_quote", lambda quote, where: quote)
    with pytest.raises(sqlite3.IntegrityError, match=r"rule_source IS NULL OR rule_source IN \('sayfa','yanıt'\)"):
        store_one(tmp_path / "a", old)
    monkeypatch.undo()
    db, job = store_one(tmp_path / "b", old)                    # a recovery file written before the fix still stores
    with db.connect() as con:
        assert con.execute("SELECT rule_source FROM agency_rate_quotes WHERE run_id=?", (job,)).fetchone()[0] == "sayfa"


def test_an_unknown_value_is_named_before_the_database_sees_it():
    with pytest.raises(SourceError, match=r"realjoy\.com 1 · ay-2027-02: kural kaynağı \"site\" tanınmıyor"):
        ar.checked_quote({"status": "unavailable", "rule_source": "site"}, "realjoy.com 1 · ay-2027-02")
    with pytest.raises(SourceError, match="durumu \"maybe\""):
        ar.checked_quote({"status": "maybe", "rule_source": None}, "x")


def test_no_adapter_writes_a_rule_source_outside_the_schema():
    """Every literal value of rule_source in the adapters is one the schema takes (the night's value was a literal)."""
    import re
    text = (Path(ar.__file__).parent / "agency_adapters.py").read_text(encoding="utf-8")
    values = set(re.findall(r'"rule_source":\s*"([^"]+)"', text)) | set(re.findall(r'"rule_source":\s*"([^"]+)" if', text))
    assert values and values <= set(ar.RULE_SOURCES)


# --- the recovery folder and "Kurtarılan sonucu kaydet" -------------------------------------------------------------------

def collect_once(client, monkeypatch):
    tl.install(monkeypatch, tl.BookDirectMock(ta.LODGING_DATA), today=ta.TODAY)
    ta.install(monkeypatch, ta.Sites())
    ta.use_test_sites(client.app.state.db)
    tl.fixed_windows(client.app.state.db)
    assert tl.start(client)["status"] == "done"


def failing_store(monkeypatch):
    original = ar.AgencyRatesConnector.store_records
    def fail(self, con, run_id, records, related=None):
        original(self, con, run_id, records, related)
        raise sqlite3.IntegrityError("CHECK constraint failed: rule_source IS NULL OR rule_source IN ('sayfa','yanıt')")
    monkeypatch.setattr(ar.AgencyRatesConnector, "store_records", fail)
    return original


def test_a_failed_storing_step_keeps_the_result_and_saves_it_later_without_collecting(tmp_path, monkeypatch):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        collect_once(client, monkeypatch)
        original = failing_store(monkeypatch)
        failed = tl.start(client, url=AGENCY_URL)
        assert failed["status"] == "failed" and "kurtarma dosyasına yazıldı" in failed["message"]
        folder = tmp_path / "kurtarma" / failed["id"]
        assert (folder / "sonuc.json").is_file() and (folder / "durum.json").is_file()
        state = json.loads((folder / "durum.json").read_text(encoding="utf-8"))
        assert state["nasil"] == "kaydetme_dustu" and state["hata"]["tur"] == "IntegrityError" and state["kaydedildi"] is None
        assert state["ham_kopya"] == f"raw/{failed['id']}/manifest.json"
        assert client.get("/api/agency-rate-runs").json() == []                 # nothing stored
        card = next(j for j in client.get("/api/jobs").json() if j["id"] == failed["id"])
        assert card["kurtarma"]["durum"] == "kaydet" and card["kurtarma"]["kayit"] == 8
        assert "hata" not in card["kurtarma"] and "IntegrityError" not in json.dumps(card, ensure_ascii=False)   # the diagnostic stays inside
        boot = next(j for j in client.get("/api/bootstrap").json()["jobs"] if j["id"] == failed["id"])        # the panel's first drawing
        assert boot["kurtarma"]["durum"] == "kaydet"
        monkeypatch.setattr(ar.AgencyRatesConnector, "store_records", original)        # "the fix"
        ta.install(monkeypatch, lambda request: pytest.fail(f"a site was asked: {request.url}"))
        answer = client.post(f"/api/jobs/{failed['id']}/kurtarma/kaydet")
        assert answer.status_code == 202, answer.text
        saved = finished(client, answer.json()["id"])
        assert saved["status"] == "done", saved["message"]
        runs = client.get("/api/agency-rate-runs").json()
        assert [r["id"] for r in runs] == [saved["id"]]
        with db.connect() as con:
            run = con.execute("SELECT raw_path, metadata FROM source_runs WHERE id=?", (saved["id"],)).fetchone()
            assert run["raw_path"].replace("\\", "/") == f"raw/{failed['id']}/manifest.json"       # the night's own raw copy
            assert json.loads(run["metadata"])["kurtarma"]["kaynak_is"] == failed["id"]
            assert con.execute("SELECT COUNT(*) FROM agency_rate_quotes WHERE run_id=?", (saved["id"],)).fetchone()[0] == 6 * 5
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        card = next(j for j in client.get("/api/jobs").json() if j["id"] == failed["id"])
        assert card["kurtarma"]["durum"] == "kaydedildi" and card["kurtarma"]["surum"] == saved["id"]
        again = client.post(f"/api/jobs/{failed['id']}/kurtarma/kaydet")
        assert again.status_code == 409 and "zaten kaydedildi" in again.json()["detail"]
        assert (folder / "sonuc.json").is_file()                                  # nothing is deleted


def test_recovery_keeps_dates_and_counts(tmp_path):
    batch = CollectionResult([{"a": 1, "on": date(2027, 1, 9)}], 3, 2, "2026-11-26", {"m": [1, 2]}, {"quotes": [{"q": date(2027, 2, 13)}]})
    job, source = {"id": "j1"}, {"id": "s1", "name": "Kiralama"}
    recovery.save(tmp_path, job, source, ar.AgencyRatesConnector(), batch, error={"tur": "X", "metin": "y"})
    back = recovery.load(tmp_path, "j1")
    assert back.records == batch.records and back.related == batch.related and (back.total_count, back.excluded_count) == (3, 2)


# --- rebuilt from the raw copy (agency_replay) -------------------------------------------------------------------------

def test_a_failed_run_is_rebuilt_from_its_raw_copy_without_asking_any_site(tmp_path, monkeypatch):
    original_collect = ar.collect
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        collect_once(client, monkeypatch)
        good = tl.start(client, url=AGENCY_URL)
        assert good["status"] == "done"
        failing_store(monkeypatch)
        monkeypatch.setattr(recovery, "save", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))   # the night: no recovery file
        failed = tl.start(client, url=AGENCY_URL)
        assert failed["status"] == "failed"
        monkeypatch.undo()
        monkeypatch.setattr(ar, "collect", original_collect)
        monkeypatch.setattr(replay, "run_day", lambda job: ta.TODAY)
        monkeypatch.setattr(ar, "REQUEST_GAP", 30.0)                         # a replay never waits
        card = next(j for j in client.get("/api/jobs").json() if j["id"] == failed["id"])
        assert card["kurtarma"]["durum"] == "kur"
        def no_site(request):
            raise AssertionError(f"a site was asked: {request.url}")
        monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda self, request: no_site(request))
        answer = client.post(f"/api/jobs/{failed['id']}/kurtarma/kur")
        assert answer.status_code == 202, answer.text
        rebuilt = finished(client, answer.json()["id"])
        assert rebuilt["status"] == "done", rebuilt["message"]
        result = rebuilt["result"]
        assert result["karsilastirma"]["ayni"] is True and result["karsilastirma"]["kurulan"]["fiyat_sorgusu"] == 30
        assert result["rapor"]["kullanilan"] == result["rapor"]["cevap"] and result["rapor"]["eksik_istek"] == 0
        card = next(j for j in client.get("/api/jobs").json() if j["id"] == failed["id"])
        assert card["kurtarma"]["durum"] == "kaydet" and card["kurtarma"]["karsilastirma"]["ayni"] is True
        saved = finished(client, client.post(f"/api/jobs/{failed['id']}/kurtarma/kaydet").json()["id"])
        assert saved["status"] == "done", saved["message"]
        with db.connect() as con:
            def quotes(run):
                return sorted((r["lodging_id"], r["window_key"], r["status"], r["total"], r["rule_source"], r["raw_sha256"])
                              for r in con.execute("SELECT * FROM agency_rate_quotes WHERE run_id=?", (run,)))
            def listings(run):
                return sorted((r["lodging_id"], r["page_status"], r["page_url"], r["site_listing_id"], r["match_method"])
                              for r in con.execute("SELECT * FROM agency_rate_listings WHERE run_id=?", (run,)))
            assert quotes(saved["id"]) == quotes(good["id"]) and listings(saved["id"]) == listings(good["id"])
            meta = json.loads(con.execute("SELECT metadata FROM source_runs WHERE id=?", (saved["id"],)).fetchone()[0])
            assert meta["yeniden_kurma"]["kaynak_is"] == failed["id"] and meta["kurtarma"]["nasil"] == "yeniden_kurma"


def test_a_redirects_target_is_kept_in_the_raw_copy_and_used_by_the_replay(tmp_path):
    store = ar.RawStore(tmp_path / "manifest.json")
    def site(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        return httpx.Response(200, text="page")
    with httpx.Client(transport=httpx.MockTransport(site)) as client:
        session = ar.SiteSession(store, "ornek.test", ar.HttpTransport(client), lambda: False, gap=0)
        assert session.request("GET", "https://www.ornek.test/old", note="listing-page").url == "https://www.ornek.test/new"
    store.flush()
    first = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["responses"][0]
    assert first["status"] == 301 and first["location"] == "https://www.ornek.test/new"
    book = replay.ReplayBook(tmp_path / "manifest.json")
    assert book.locations == {1: "https://www.ornek.test/new"}


def record(sequence, url, at, status=200, note="listing-page"):
    return {"sequence": sequence, "company": "ornek.test", "transport": "proxy", "note": note, "method": "GET", "requested_url": url,
            "request_body": None, "final_url": url, "status": status, "content_type": "text/html", "fetched_at": f"2026-11-26T23:{at}+00:00",
            "raw_file": f"responses/{sequence:06d}.gz"}


def test_an_older_copys_redirect_target_is_the_same_workers_next_request(tmp_path):
    """Before HEDEF-02 a redirect's target was not kept: it is the answer the same worker asked one gap (8 s) later, not another
    worker's listing link and not another redirect's hop; among several, the one nearest the usual delay and most alike."""
    records = [record(1, "https://ornek.test/a-cottage", "40:00.0", 301), record(2, "https://ornek.test/b-cottage", "40:01.0", 301),
               record(3, "https://ornek.test/c", "40:03.0"),                 # another worker's own listing link
               record(4, "https://www.ornek.test/a-cottage", "40:08.7"), record(5, "https://www.ornek.test/b-cottage", "40:09.8")]
    (tmp_path / "manifest.json").write_text(json.dumps({"responses": records}), encoding="utf-8")
    book = replay.ReplayBook(tmp_path / "manifest.json", ["https://ornek.test/a-cottage", "https://ornek.test/b-cottage", "https://ornek.test/c"])
    assert book.locations == {1: "https://www.ornek.test/a-cottage", 2: "https://www.ornek.test/b-cottage"}


def test_the_replay_gives_each_answer_once_and_fails_an_unknown_request_like_a_dropped_connection(tmp_path):
    folder = tmp_path / "responses"; folder.mkdir()
    records = [record(1, "https://ornek.test/x", "40:00.0"), record(2, "https://ornek.test/x", "40:09.0", status=429)]
    for r, body in zip(records, (b"first", b"second")):
        (tmp_path / r["raw_file"]).write_bytes(gzip.compress(body))
    (tmp_path / "manifest.json").write_text(json.dumps({"responses": records}), encoding="utf-8")
    book = replay.ReplayBook(tmp_path / "manifest.json")
    assert book.answer("http", "GET", "https://ornek.test/x", "")[3] == b"first"
    assert book.answer("http", "GET", "https://ornek.test/x", "")[0] == 429
    with pytest.raises(httpx.ConnectError):
        book.answer("http", "GET", "https://ornek.test/x", "")
    with pytest.raises(httpx.ConnectError):                                     # the extension's answers are apart from plain HTTP
        book.answer("eklenti", "GET", "https://ornek.test/y", "")
    report = book.report()
    assert (report["kullanilan"], report["eksik_istek"], report["kullanilmayan"]) == (2, 2, 0)


def test_the_log_line_gives_the_counts_to_compare():
    log = [{"text": "x"}, {"text": "2384 ilan, 11408 fiyat sorgusu, kendi envanterinden 97 ev ve 28 şirket sonucu kaydediliyor."}, {"text": "y"}]
    assert replay.summary_counts(log) == {"ilan": 2384, "fiyat_sorgusu": 11408, "kendi_evi": 97, "sirket": 28}
    assert replay.summary_counts([{"text": "başka"}]) is None


# --- the trial run stores the latest real run at full size --------------------------------------------------------------

def test_the_trial_stores_the_latest_real_run_and_shows_a_storing_error(tmp_path, monkeypatch):
    from studio import trial_run
    original_collect = ar.collect
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        collect_once(client, monkeypatch)
        assert tl.start(client, url=AGENCY_URL)["status"] == "done"
        monkeypatch.setattr(ar, "collect", original_collect)
        monkeypatch.setattr(replay, "run_day", lambda job: ta.TODAY)
        source = next(s for s in db.sources() if s["url"] == AGENCY_URL)
        connector = db.registry.for_source(source)
        job = db.add_job("deneme_cekimi", "Deneme")
        trial = trial_run.TrialRun(db, job)
        trial.folder.mkdir(parents=True)
        copy = trial_run.TrialDatabase(trial_run.copy_database(db.path, trial.folder), db.registry)
        check = trial.store_check(copy, source, connector)
        assert check["durum"] == "gecti" and check["karsilastirma"]["ayni"] is True, check
        # the night's kind of error: a value the schema does not take, met only at full size
        monkeypatch.setattr(ar, "checked_quote", lambda quote, where: {**quote, "rule_source": "takvim"})
        check = trial.store_check(copy, source, connector)
        assert check["durum"] == "dustu" and "IntegrityError" in check["metin"] and "rule_source" in check["metin"]
