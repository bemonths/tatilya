"""GÖREV-20: airport average fares from the BTS table "Average Domestic Airline Itinerary Fares".

Fixtures are the page's own HTML from the raw copies of 16 November 2026 (the first answer and one answer of the form), with the
table cut down to a few airports; httpx.MockTransport only.
"""
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.destinations import thirty_a
from studio.sources import airfare as af
from studio.sources.base import SourceError
from tests.test_beaches import HEADERS
from tests.test_lodging import start

FIXTURES = Path(__file__).parent / "fixtures" / "airfare"
LATEST = (FIXTURES / "son-ceyrek-2026-q2.html").read_text(encoding="utf-8")
EARLIER = (FIXTURES / "form-2025-q2.html").read_text(encoding="utf-8")
CONFIG = {"airports": thirty_a.AIRFARE["airports"], "quarters": 5}
REAL_COLLECT = af.collect


def page_for(year, quarter, without=()):
    """The form's answer for a quarter: the 2025 Q2 fixture with its title changed (the fares stay the fixture's)."""
    page = EARLIER.replace("By Origin City for Q2 2025", f"By Origin City for Q{quarter} {year}")
    for code in without:
        page = re.sub(rf"<tr[^>]*>(?:(?!</tr>).)*?>{code}<.*?</tr>", "", page, flags=re.S)
    return page


class BtsMock:
    def __init__(self, without=None, wrong=False, status=200):
        self.seen, self.without, self.wrong, self.status = [], without or {}, wrong, status

    def __call__(self, request):
        self.seen.append(request)
        assert request.url.host == af.HOST and request.url.path == "/AverageFare/"
        headers = {"content-type": "text/html; charset=utf-8"}
        if self.status != 200:
            return httpx.Response(self.status, text="denied", headers=headers)
        if request.method == "GET":
            return httpx.Response(200, text=LATEST, headers=headers)
        form = {k: v[0] for k, v in parse_qs(request.content.decode(), keep_blank_values=True).items()}
        year, quarter = (2024, 1) if self.wrong else (int(form["dlstYear"]), int(form["dlstQuarter"]))
        return httpx.Response(200, text=page_for(year, quarter, self.without.get((year, quarter), ())), headers=headers)


def run(tmp_path, mock, **changes):
    with httpx.Client(transport=httpx.MockTransport(mock)) as client:
        return af.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config={**CONFIG, **changes}, client=client,
                          today=date(2026, 11, 16), gap=0)


def test_page_parses_period_rows_notes_and_form():
    answer = af.parse(LATEST)
    assert (answer["year"], answer["quarter"], answer["adjusted_base"]) == (2026, 2, "Q2-2026")
    assert answer["rank_basis"] == "Total Number of Domestic Passengers in 2025"
    assert answer["rows"]["VPS"] == {"passenger_rank": 114, "city_name": "Valparaiso", "state": "FL", "average_fare": 376.10, "adjusted_fare": 376.10}
    assert answer["rows"]["ECP"]["average_fare"] == 461.65 and answer["rows"]["ECP"]["city_name"] == "Panama City"
    assert answer["notes"]["source"].startswith("Bureau of Transportation Statistics, Airline Origin & Destination Survey (10% Sample)")
    assert "round-trip or one-way for which no return is purchased" in answer["notes"]["itinerary fare"]
    assert set(answer["form"]) == {"__VIEWSTATE", "__VIEWSTATEGENERATOR", "__VIEWSTATEENCRYPTED", "__EVENTVALIDATION"}
    earlier = af.parse(EARLIER)
    assert (earlier["year"], earlier["quarter"]) == (2025, 2)
    assert earlier["rows"]["VPS"]["average_fare"] == 359.62 and earlier["rows"]["VPS"]["adjusted_fare"] == 373.51      # nominal and adjusted apart
    with pytest.raises(SourceError, match="beklenen biçimde değil"):
        af.parse("<html><body>Maintenance</body></html>")
    with pytest.raises(SourceError, match="sütunları"):
        af.parse(LATEST.replace("Average Fare ($)", "Passengers"))


def test_earlier_quarters_count_back_over_the_year_end():
    assert [af.earlier(2026, 2, step) for step in range(1, 5)] == [(2026, 1), (2025, 4), (2025, 3), (2025, 2)]


def test_collect_reads_the_latest_quarter_then_asks_the_form_for_the_earlier_ones(tmp_path):
    mock = BtsMock()
    result = run(tmp_path, mock)
    assert [r.method for r in mock.seen] == ["GET", "POST", "POST", "POST", "POST"]
    forms = [{k: v[0] for k, v in parse_qs(r.content.decode(), keep_blank_values=True).items()} for r in mock.seen[1:]]
    assert [(f["dlstYear"], f["dlstQuarter"], f["btnSubmit"]) for f in forms] == [("2026", "1", "Submit"), ("2025", "4", "Submit"),
                                                                                  ("2025", "3", "Submit"), ("2025", "2", "Submit")]
    assert all(f["__VIEWSTATE"] == "FIXTUREVIEWSTATE" for f in forms)                      # the page's own hidden fields go back with the form
    assert len(result.records) == 10 and {(r["year"], r["quarter"]) for r in result.records} == {(2026, 2), (2026, 1), (2025, 4), (2025, 3), (2025, 2)}
    latest = next(r for r in result.records if (r["airport_code"], r["year"], r["quarter"]) == ("VPS", 2026, 2))
    assert (latest["average_fare"], latest["listed"], latest["title"]) == (376.10, 1, "Average Domestic Airline Itinerary Fares By Origin City for Q2 2026 "
                                                                                       "Ranked by Total Number of Domestic Passengers in 2025")
    assert len(latest["raw_sha256"]) == 64 and result.source_updated == "2026 Q2"
    snapshot = result.related["snapshot"]
    assert (snapshot["latest_year"], snapshot["latest_quarter"], snapshot["request_count"], snapshot["queried_on"]) == (2026, 2, 5, "2026-11-16")
    assert "do not include other fees, such as baggage fees" in snapshot["fare_note"]
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert [r["method"] for r in manifest["responses"]] == ["GET", "POST", "POST", "POST", "POST"]
    assert manifest["responses"][1]["request_form"] == {"dlstQuarter": "1", "dlstYear": "2026", "btnSubmit": "Submit"}   # no hidden fields kept


def test_an_airport_missing_from_a_quarter_stays_a_row_without_a_fare(tmp_path):
    result = run(tmp_path, BtsMock(without={(2025, 4): ("ECP",)}))
    row = next(r for r in result.records if (r["airport_code"], r["year"], r["quarter"]) == ("ECP", 2025, 4))
    assert (row["listed"], row["average_fare"], row["adjusted_fare"], row["city_name"]) == (0, None, None, None)


def test_refusal_wrong_period_and_missing_configuration_stop_the_run(tmp_path):
    with pytest.raises(SourceError, match="yapılandırılmamış"):
        af.collect(tmp_path / "x" / "manifest.json", lambda *a: None, lambda: False, config=None)
    with pytest.raises(SourceError, match="reddetti"):
        run(tmp_path / "a", BtsMock(status=403))
    with pytest.raises(SourceError, match="istenen dönemi"):
        run(tmp_path / "b", BtsMock(wrong=True))


def test_api_stores_the_quarters_and_gives_the_change_from_a_year_earlier(tmp_path, monkeypatch):
    def collect(path, progress, canceled, *, config, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(BtsMock(without={(2025, 3): ("ECP",)}))) as client:
            return REAL_COLLECT(path, progress, canceled, config=config, client=client, today=date(2026, 11, 16), gap=0)
    monkeypatch.setattr(af, "collect", collect)
    with TestClient(create_app(tmp_path / "data"), headers=HEADERS) as client:
        job = start(client, url=af.SOURCE_URL)
        assert job["status"] == "done", job["message"]
        assert client.get("/api/bootstrap").json()["airfare_runs"][0]["id"] == job["id"]
        summary = client.get(f"/api/airfare-runs/{job['id']}").json()
        assert "BAŞLAYAN" in summary["note"] and "havalimanından başlayan" in summary["label"]
        vps = next(a for a in summary["airports"] if a["code"] == "VPS")
        assert [(q["year"], q["quarter"]) for q in vps["quarters"]] == [(2026, 2), (2026, 1), (2025, 4), (2025, 3), (2025, 2)]
        assert vps["latest"]["average_fare"] == 376.10 and vps["year_before"]["average_fare"] == 359.62
        assert vps["change"] == {"amount": 16.48, "percent": 4.6}
        ecp = next(a for a in summary["airports"] if a["code"] == "ECP")
        assert next(q for q in ecp["quarters"] if (q["year"], q["quarter"]) == (2025, 3))["listed"] == 0
        raw = client.get(f"/api/airfare-runs/{job['id']}/raw")
        assert raw.status_code == 200 and json.loads(raw.content)["connector"] == af.CONNECTOR_VERSION
        assert client.get("/api/airfare-runs/missing").status_code == 404
        with client.app.state.db.connect() as con:
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
            assert con.execute("SELECT COUNT(*) FROM airfare_quarters WHERE run_id=?", (job["id"],)).fetchone()[0] == 10
