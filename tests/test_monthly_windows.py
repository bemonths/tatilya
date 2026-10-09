"""GÖREV-10 monthly lodging windows, same-week comparison of two runs, our season groups and the suggested-refresh batch.

Synthetic responses through httpx.MockTransport only; suite-wide no_real_http prevents internet access.
"""
import json
import sqlite3
import threading
import time
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from studio import refresh
from studio.app import create_app
from studio.sources import bookdirect_lodging as bl
from studio.sources.base import SourceError
from studio.sources.price_history import compare, season_groups
from studio.sources.registry import DEFAULT_REGISTRY
from studio.sources.windows import lead_days, monthly_windows, rule_text, season_of
from tests.test_beaches import HEADERS
from tests.test_lodging import URL, BookDirectMock, fast, inventory, start  # noqa: F401  (fast: autouse fixture)

REAL_COLLECT = bl.collect
DUE = ["bookdirect-lodging", "agency-lodging-rates", "south-walton-restaurants", "restaurant-sites"]


def use(monkeypatch, mock, today):
    def collect(path, progress, canceled, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(mock)) as client:
            return REAL_COLLECT(path, progress, canceled, client=client, today=today, **kwargs)
    monkeypatch.setattr(bl, "collect", collect)


def fail(name, monkeypatch):
    def collect(self, *args, **kwargs):
        raise SourceError(f"{name} deneme hatası")
    monkeypatch.setattr(type(DEFAULT_REGISTRY.by_name(name)), "collect", collect)


# --- Window rule ------------------------------------------------------------------------------------------------------------

def test_twelve_months_after_the_run_month_each_the_saturday_week_holding_the_15th():
    windows = monthly_windows(date(2026, 10, 9))
    assert len(windows) == 12 and windows[0]["window_key"] == "ay-2026-11" and windows[-1]["window_key"] == "ay-2027-10"
    july = next(w for w in windows if w["window_key"] == "ay-2027-07")
    assert (july["label"], july["checkin"], july["checkout"], july["month"]) == ("Temmuz 2027 · 10–17 Temmuz", "2027-07-10", "2027-07-17", "2027-07")
    may = next(w for w in windows if w["window_key"] == "ay-2027-05")                      # the 15th is a Saturday: the week starts on it
    assert (may["checkin"], may["checkout"]) == ("2027-05-15", "2027-05-22")
    assert all(date.fromisoformat(w["checkin"]).weekday() == 5 and 9 <= date.fromisoformat(w["checkin"]).day <= 15 for w in windows)
    assert all((date.fromisoformat(w["checkout"]) - date.fromisoformat(w["checkin"])).days == 7 for w in windows)


def test_a_week_fewer_than_21_days_away_is_skipped_and_a_thirteenth_month_is_added():
    assert monthly_windows(date(2026, 10, 24))[0]["checkin"] == "2026-11-14"                 # exactly 21 days: kept
    later = monthly_windows(date(2026, 10, 25))                                               # 20 days: skipped
    assert len(later) == 12 and later[0]["window_key"] == "ay-2026-12" and later[-1]["window_key"] == "ay-2027-11"
    turn = monthly_windows(date(2026, 12, 1))                                                 # year change
    assert turn[0]["label"] == "Ocak 2027 · 9–16 Ocak" and turn[-1]["window_key"] == "ay-2027-12"
    assert [w["window_key"] for w in monthly_windows(date(2027, 1, 31), {"months": 2})] == ["ay-2027-03", "ay-2027-04"]   # 13 Feb: 13 days
    with pytest.raises(ValueError, match="Bilinmeyen pencere kuralı"):
        monthly_windows(date(2026, 10, 9), {"kind": "weekly"})


def test_rule_text_lead_days_and_seasons_are_labelled_ours():
    assert "bizim varsayımımız" in rule_text(None) and "21 günden yakın" in rule_text(None)
    assert lead_days("2026-11-14", "2026-10-07T10:00:00+00:00") == 38 and lead_days(None, "2026-10-07") is None
    assert [season_of(d) for d in ("2026-12-12", "2027-03-13", "2027-07-10", "2027-11-13")] == ["kış", "ilkbahar", "yaz", "sonbahar"]


# --- Same-week comparison and season groups ---------------------------------------------------------------------------------

def test_same_week_comparison_matches_windows_by_dates_and_only_listings_priced_twice():
    earlier = {"windows": [{"window_key": "summer-2027", "label": "Yaz", "checkin": "2027-07-10", "checkout": "2027-07-17"},
                           {"window_key": "fall-2027", "checkin": "2027-10-02", "checkout": "2027-10-09"}],
               "prices": {(1, "summer-2027"): 200.0, (2, "summer-2027"): 400.0, (3, "summer-2027"): 300.0, (5, "summer-2027"): 100.0}}
    later = {"windows": [{"window_key": "ay-2027-07", "label": "Temmuz 2027 · 10–17 Temmuz", "checkin": "2027-07-10", "checkout": "2027-07-17"},
                         {"window_key": "ay-2027-08", "checkin": "2027-08-14", "checkout": "2027-08-21"}],
             "prices": {(1, "ay-2027-07"): 220.0, (2, "ay-2027-07"): 380.0, (4, "ay-2027-07"): 500.0, (5, "ay-2027-07"): 130.0},
             "members": {"seaside": {1, 2, 3, 4}, "grayton": {5}, "alys": set()}}
    result = compare(["seaside", "grayton", "alys"], earlier, later, "2026-10-09", "2026-11-09")
    assert result["windows"] == [{"window_key": "ay-2027-07", "label": "Temmuz 2027 · 10–17 Temmuz", "earlier_label": "Yaz",
                                  "checkin": "2027-07-10", "checkout": "2027-07-17"}]
    rows = {r["region_id"]: r for r in result["rows"]}
    assert (rows["seaside"]["matched_count"], rows["seaside"]["median_change"], rows["seaside"]["median_amount"]) == (2, 0.025, -0.0)
    assert rows["seaside"]["earlier_window_key"] == "summer-2027"
    assert (rows["grayton"]["matched_count"], rows["grayton"]["median_change"]) == (1, 0.3)
    assert (rows["alys"]["matched_count"], rows["alys"]["median_change"]) == (0, None)
    assert result["label"] == "aynı evlerin aynı hafta için 2026-10-09 ve 2026-11-09 tarihlerinde sorgulanan fiyatları; bizim hesabımız"


def test_season_groups_pool_every_priced_listing_window_of_a_season():
    windows = [{"window_key": "a", "season": "yaz", "status": "searched"}, {"window_key": "b", "season": "yaz", "status": "queried"},
               {"window_key": "c", "season": "kış", "status": "skipped_past"}]
    result = season_groups(["seaside"], windows, {("seaside", "a"): [100, 300], ("seaside", "b"): [200], ("seaside", "c"): [50]})
    assert result["rows"] == [{"region_id": "seaside", "season": "yaz", "window_count": 2, "priced_count": 3, "median": 200}]
    assert "bizim gruplamamızdır" in result["note"]


def test_two_monthly_runs_show_lead_days_seasons_and_the_same_week_comparison(tmp_path, monkeypatch):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        use(monkeypatch, BookDirectMock(), date(2026, 10, 7))
        first = start(client)
        assert first["status"] == "done", first["message"]
        data = client.get(f"/api/lodging-runs/{first['id']}").json()
        assert [w["window_key"] for w in data["windows"]][:2] == ["ay-2026-11", "ay-2026-12"] and len(data["windows"]) == 12
        november = data["windows"][0]
        assert (november["label"], november["lead_days"], november["season"], november["month"]) == ("Kasım 2026 · 14–21 Kasım", 38, "sonbahar", "2026-11")
        seasons = {(r["region_id"], r["season"]): r for r in data["seasons"]["rows"]}
        assert seasons[("seaside", "yaz")]["window_count"] == 3 and seasons[("seaside", "yaz")]["priced_count"] > 0
        assert data["comparison"] is None

        changed = inventory()
        changed[2565][0]["lodging"].update(average_rate="300.00", currency={"USD": "300.00"})    # 250 -> 300 a night
        changed[2565][1]["lodging"].update(live_rates_enabled=False)                            # no price in the later run
        use(monkeypatch, BookDirectMock(changed), date(2026, 11, 7))
        second = start(client)
        assert second["status"] == "done", second["message"]
        data = client.get(f"/api/lodging-runs/{second['id']}").json()
        assert data["windows"][0]["window_key"] == "ay-2026-12"                                 # November is 7 days away: skipped
        comparison = data["comparison"]
        assert comparison["earlier_run_id"] == first["id"] and comparison["basis"] == "gecelik fiyat (Book>Direct)"
        assert comparison["label"] == "aynı evlerin aynı hafta için 2026-10-07 ve 2026-11-07 tarihlerinde sorgulanan fiyatları; bizim hesabımız"
        assert [w["window_key"] for w in comparison["windows"]] == [f"ay-{y}-{m:02d}" for y, m in [(2026, 12)] + [(2027, m) for m in range(1, 11)]]
        rows = {(r["region_id"], r["window_key"]): r for r in comparison["rows"]}
        july = rows[("seaside", "ay-2027-07")]
        assert july["matched_count"] == 3 and july["median_change"] == 0.0                     # 250 -> 300, two calendar prices unchanged
        assert rows[("seagrove", "ay-2027-07")]["matched_count"] == 0 and rows[("seagrove", "ay-2027-07")]["median_change"] is None


# --- Suggested refresh ------------------------------------------------------------------------------------------------------

def test_add_months_keeps_the_day_or_takes_the_month_end():
    assert refresh.add_months(date(2026, 10, 9), 3) == date(2027, 1, 9)
    assert refresh.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28) and refresh.add_months(date(2027, 12, 31), 2) == date(2028, 2, 29)


def test_status_lists_due_collectors_in_order_and_the_interval_starts_at_the_last_successful_run(tmp_path, monkeypatch):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        current = client.get("/api/refresh").json()
        assert [i["connector"] for i in current["items"] if i["due"]] == DUE and current["due_count"] == 4
        assert {i["due_reason"] for i in current["items"] if i["due"]} == {"hiç çekilmedi"} and current["estimate_seconds"] is None
        assert [i["interval_months"] for i in current["items"][:4]] == [1, 1, 3, 3] and current["estimate_complete"] is False
        assert all(i["interval_months"] is None and not i["due"] for i in current["items"][4:])
        assert "kendiliğinden çalışmaz" in current["note"]
        assert client.get("/api/bootstrap").json()["refresh"]["due_count"] == 4

        use(monkeypatch, BookDirectMock(), date(2026, 10, 7))
        job = start(client)
        assert job["status"] == "done", job["message"]
        item = next(i for i in client.get("/api/refresh").json()["items"] if i["connector"] == "bookdirect-lodging")
        done_on = date.fromisoformat(item["last_done_on"])
        assert item["last_run_id"] == job["id"] and item["next_due_on"] == refresh.add_months(done_on, 1).isoformat()
        assert item["due"] is False and item["estimate_note"] == "son başarılı çekimin süresi; bizim tahminimiz"
        later = refresh.status(db, "30a", refresh.add_months(done_on, 1))["items"][0]
        assert (later["due"], later["due_reason"]) == (True, "önerilen aralık doldu")
        with db.connect() as con:                                       # a run made before the monthly rule (fixed windows)
            con.execute("UPDATE source_runs SET metadata=json_remove(metadata, '$.window_rule') WHERE id=?", (job["id"],))
        item = refresh.status(db, "30a", done_on)["items"][0]
        assert (item["due"], item["due_reason"]) == (True, "pencere kuralı son çekimden sonra değişti")
        with db.connect() as con:
            con.execute("UPDATE source_runs SET metadata=json_set(metadata, '$.window_rule', json(?)) WHERE id=?",
                        (json.dumps({"kind": "monthly"}), job["id"]))               # the same rule written shorter: not a change
        assert refresh.status(db, "30a", done_on)["items"][0]["due"] is False
        with db.connect() as con:
            con.execute("UPDATE destination_lodging_sources SET window_rule=?", (json.dumps({"kind": "monthly", "months": 6}),))
        item = refresh.status(db, "30a", done_on)["items"][0]
        assert item["due_reason"] == "pencere kuralı son çekimden sonra değişti"
        assert item["estimate_note"].startswith("son çekimin süresi × pencere oranı (12 → 6)")


def test_batch_backs_up_runs_due_collectors_in_order_and_skips_one_whose_input_did_not_finish(tmp_path, monkeypatch):
    use(monkeypatch, BookDirectMock(), date(2026, 10, 7))
    fail("agency-lodging-rates", monkeypatch)
    fail("south-walton-restaurants", monkeypatch)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db, runner = client.app.state.db, client.app.state.batches
        runner.poll = 0.02
        started = client.post("/api/refresh-batches", json={"destination_id": "30a"}, headers=HEADERS)
        assert started.status_code == 202, started.text
        batch = started.json()
        assert batch["status"] == "running" and batch["message"].startswith("Uygulamanın yedeği alındı: toplu-")
        assert [s["connector"] for s in batch["plan"]] == DUE
        runner.thread.join(60)
        batch = runner.batch(batch["id"])
        assert [s["status"] for s in batch["plan"]] == ["done", "failed", "failed", "skipped"]
        assert batch["plan"][3]["message"] == "girdisini üreten toplayıcı bu çalıştırmada tamamlanmadı" and batch["plan"][3]["job_id"] is None
        assert batch["status"] == "failed" and batch["message"] == "1/4 toplayıcı tamamlandı." and batch["finished_at"]
        copy = tmp_path / batch["backup_file"]
        assert copy.parent == tmp_path / "backups" and copy.is_file()
        with sqlite3.connect(copy) as con:
            assert con.execute("SELECT COUNT(*) FROM source_runs WHERE status='done'").fetchone()[0] == 0   # taken before the batch
        jobs = [db.job(s["job_id"]) for s in batch["plan"][:3]]
        assert [j["created_at"] for j in jobs] == sorted(j["created_at"] for j in jobs)
        status = client.get("/api/refresh").json()
        assert status["batch"]["id"] == batch["id"] and [i["connector"] for i in status["items"] if i["due"]] == DUE[1:]


def test_nothing_due_another_job_running_and_unknown_batch_are_refused(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        with client.app.state.db.connect() as con:
            con.execute("DELETE FROM destination_refresh_intervals")
        result = client.post("/api/refresh-batches", json={"destination_id": "30a"}, headers=HEADERS)
        assert result.status_code == 409 and "zamanı gelen toplayıcı yok" in result.json()["detail"]
        assert not (tmp_path / "backups").exists() or not list((tmp_path / "backups").glob("toplu-*"))
        assert client.post("/api/refresh-batches/missing/cancel", headers=HEADERS).status_code == 404


def test_cancel_stops_the_running_collector_and_skips_the_rest(tmp_path, monkeypatch):
    reached, release = threading.Event(), threading.Event()
    def before(count):
        if count == 3:
            reached.set()
            release.wait(10)
    use(monkeypatch, BookDirectMock(before=before), date(2026, 10, 7))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        runner = client.app.state.batches
        runner.poll = 0.02
        batch = client.post("/api/refresh-batches", json={"destination_id": "30a"}, headers=HEADERS).json()
        assert reached.wait(10)
        canceled = client.post(f"/api/refresh-batches/{batch['id']}/cancel", headers=HEADERS)
        assert canceled.status_code == 200 and canceled.json()["status"] == "canceled"
        release.set()
        runner.thread.join(30)
        batch = runner.batch(batch["id"])
        assert batch["status"] == "canceled" and batch["finished_at"] and batch["message"] == "Kullanıcı durdurdu."
        assert batch["plan"][0]["status"] == "canceled" and client.app.state.db.job(batch["plan"][0]["job_id"])["status"] == "canceled"
        assert all(s["status"] == "skipped" and s["message"] == "toplu çalıştırma durduruldu" for s in batch["plan"][1:])


def test_a_batch_left_running_is_marked_interrupted_when_the_app_starts(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        path = client.app.state.db.path
    with sqlite3.connect(path) as con:                                   # as if the app had been killed during a batch
        con.execute("INSERT INTO refresh_batches (id,destination_id,created_at,status,plan) VALUES ('old','30a','2026-10-09T00:00:00+00:00','running','[]')")
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        batch = client.get("/api/refresh").json()["batch"]
        assert batch["id"] == "old" and batch["status"] == "interrupted" and "yarıda kaldı" in batch["message"]


def test_app_backups_keep_only_the_newest_six_of_the_batch_prefix(tmp_path):
    database = tmp_path / "studio.sqlite3"
    with sqlite3.connect(database) as con:
        con.execute("CREATE TABLE t (x)")
    (tmp_path / "backups").mkdir()
    other = tmp_path / "backups" / "studio-v12-yedek.sqlite3"
    other.write_bytes(b"x")
    made = [refresh.backup(database).name for _ in range(8)]
    kept = sorted(p.name for p in (tmp_path / "backups").glob("toplu-*.sqlite3"))
    assert kept == made[2:] and other.is_file()
    with sqlite3.connect(tmp_path / "backups" / kept[-1]) as con:
        assert con.execute("SELECT name FROM sqlite_master").fetchall() == [("t",)]
