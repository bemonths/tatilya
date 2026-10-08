"""Book>Direct lodging search snapshots: client key handling, location mapping, paging, live rates, calendars, storage, API.

Synthetic responses through httpx.MockTransport only; suite-wide no_real_http prevents internet access.
"""
import gzip
import json
import sqlite3
import threading
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Database
from studio.destinations import thirty_a
from studio.migration_v10 import upgrade_v10
from studio.sources import bookdirect_lodging as bl
from studio.sources.base import CollectionCanceled, SourceError
from studio.sources.registry import DEFAULT_REGISTRY
from tests.legacy import V10_TABLES, V11_TABLES
from tests.test_beaches import HEADERS, finished
from tests.test_climate import make_v8, table_counts
from tests.test_destinations import add_destination
from tests.test_studio import payload

KEY = "pk-test-0123456789abcdef"
HOST = thirty_a.LODGING_CLONE_HOST
URL = f"https://{HOST}/"
TODAY = date(2026, 10, 7)
LOCATIONS = {58635: "Alys Beach", 2458: "Blue Mountain Beach", 62708: "Dune Allen", 2490: "Grayton Beach", 62709: "Gulf Place",
             2648: "Inlet Beach", 8527: "Miramar Beach", 2449: "Rosemary Beach", 2444: "Santa Rosa Beach", 2580: "Seacrest",
             62711: "Seagrove", 2439: "Seagrove Beach", 2565: "Seaside", 62714: "Watercolor", 62712: "Watersound"}
CATEGORIES = [{"id": 103, "title": "All Lodging", "default": True}, {"id": 849, "title": "Beach Homes & Cottages", "default": False},
              {"id": 851, "title": "Condominiums, Townhomes & Villas", "default": False}, {"id": 246, "title": "Hotels", "default": False}]
AMENITIES = [{"id": 3, "name": "Internet Access"}, {"id": 6, "name": "Swimming Pool"}, {"id": 495, "name": "Gulf Front"}]
ENTRY = '<html><head><base href="/20261006094543/"><script src="vendor.js"></script><script src="bookdirect.min.js"></script></head></html>'
BUNDLE = 'angular.module("bd").constant("cfg",{auth_token:"%s",api:"https://admin.bookdirect.net"});' % KEY


def lodging(identifier, title, location, *, bedrooms=3, sleeps=8, categories=(103, 849), rate=None, live=False, hidden=0, **extra):
    record = {"id": identifier, "title": title, "address": f"{identifier} Test Road", "bedrooms": bedrooms, "bathrooms": 2.5, "sleeps": sleeps,
              "city": "Santa Rosa Beach", "state": "FL", "zip_code": "32459", "latitude": "30.3", "longitude": "-86.1", "description": "",
              "url": "https://example.com/rental", "amenity_ids": [3, 6], "category_ids": list(categories), "location_id": location,
              "hide_rate_calendar": hidden, "res_engine": "TrackHs", "average_rate": rate, "los": 4 if rate else None, "liveness": None,
              "live_rates_enabled": live, "min_stays": None,
              "currency": {"CAD": None, "EUR": None, "MXN": None, "USD": rate}}
    return {"lodging": {**record, **extra}}


def inventory():
    seaside = [lodging(1000 + i, f"Seaside cottage {i:02d}", 2565, bedrooms=2 + i % 4, sleeps=4 + i % 6) for i in range(60)]
    seaside[0]["lodging"].update(average_rate="250.00", los=4, currency={"USD": "250.00", "CAD": "355.27"})
    seaside[1]["lodging"].update(live_rates_enabled=True)
    seaside[2]["lodging"].update(live_rates_enabled=True)
    seaside[3]["lodging"].update(live_rates_enabled=True)
    return {2565: seaside,
            62711: [lodging(2001, "Seagrove house", 62711, bedrooms=5, sleeps=12, hidden=1, url="https://agency.example/rentals/2001", toll_free="(850)555-0101"),
                    lodging(2002, "Shared listing", 62711, bedrooms=4, sleeps=10)],
            2439: [lodging(2002, "Shared listing", 62711, bedrooms=4, sleeps=10),
                   lodging(2003, "Seagrove Beach hotel", 2439, bedrooms=None, sleeps=None, categories=(103, 246))],
            62708: [lodging(3001, "Dune Allen condo", 62708, bedrooms=0, sleeps=2, categories=(103, 851), rate="")],
            8527: [lodging(9001, "Miramar resort", 8527)]}


class BookDirectMock:
    """Front end, bundle and the clone API; records every request and checks the client key on API calls."""

    def __init__(self, data=None, *, bundle=BUNDLE, entry=ENTRY, before=None):
        self.data, self.bundle, self.entry, self.before = data or inventory(), bundle, entry, before
        self.seen, self.live_calls = [], []

    def __call__(self, request):
        self.seen.append(request)
        if self.before:
            self.before(len(self.seen))
        url = request.url
        if url.host == HOST:
            if url.path == "/":
                return httpx.Response(200, text=self.entry, headers={"content-type": "text/html; charset=utf-8"})
            assert url.path == "/20261006094543/bookdirect.min.js"
            return httpx.Response(200, text=self.bundle, headers={"content-type": "application/javascript"})
        assert url.host == "admin.bookdirect.net" and url.path.startswith(f"/hs4/api/v1/clones/{HOST}/")
        assert request.headers["authorization"] == f"Token token={KEY}"
        path = url.path.removeprefix(f"/hs4/api/v1/clones/{HOST}")
        if path == "/show.json":
            groups = [{"id": i, "name": n, "latitude": "30.3", "longitude": "-86.1"} for i, n in LOCATIONS.items()]
            return self.json({"data": {"clone": {"group": {"id": 62715, "sub_groups": groups}, "categories": CATEGORIES, "amenities": AMENITIES}}})
        if path == "/lodgings.json":
            assert url.params["category_ids[]"] == "103" and url.params["sort"] == "title" and url.params["per_page"] == "50"
            items = self.data.get(int(url.params["group_ids[]"]), [])
            page = int(url.params["page"])
            pages = max(1, -(-len(items) // 50))
            return self.json({"request": {"total_count": len(items), "total_pages": pages, "current_page": page},
                              "data": {"lodgings": items[(page - 1) * 50:page * 50]}})
        if path == "/lodgings/live_rates.json":
            ids = [int(i) for i in url.params.get_list("lodging_ids[]")]
            attempt = int(url.params["attempt"])
            self.live_calls.append((url.params["checkin"], attempt, ids))
            rows = []
            for i in ids:
                if i == 1001:      # pending first, then a live rate
                    rows.append({"lodging_id": i, "liveness": 1 if attempt == 1 else 0, "average_rate": None if attempt == 1 else "310.00",
                                 "los": None if attempt == 1 else 3, "currency": {"USD": None if attempt == 1 else "310.00"}})
                elif i == 1002:    # answered, no live price
                    rows.append({"lodging_id": i, "liveness": None, "average_rate": None, "los": None, "currency": {"USD": None}})
                # 1003 never appears in the answer
            return self.json({"data": {"live_rates": rows}})
        if path.endswith("/rates.json"):
            identifier = int(path.split("/")[2])
            assert url.params["per_page"] == "365"
            if identifier == 1004:
                return httpx.Response(404, json={"error": "not found"})
            return self.json({"request": {"locale": "en"}, "data": {"rates": calendar(identifier, date.fromisoformat(
                f"{url.params['checkin'][:4]}-{url.params['checkin'][4:6]}-{url.params['checkin'][6:]}"))}})
        raise AssertionError(f"Beklenmeyen istek: {url}")

    @staticmethod
    def json(payload):
        return httpx.Response(200, json=payload, headers={"content-type": "application/json; charset=utf-8"})


def calendar(identifier, start):
    days = [start + timedelta(days=offset) for offset in range(365)]
    def item(day, price, los):
        return {"date": day.isoformat(), "los": los, "data": price, "price": price, "currency": {"USD": price, "CAD": None}}
    if identifier in (1000, 1006):     # every day priced: 200 in October 2026, 180 later in the fall, 400 in July 2027
        return [item(d, "400.00" if d.month == 7 else "200.00" if d < date(2026, 11, 1) else "180.00", 7 if d.month == 7 else 4) for d in days]
    if identifier == 1005:     # one night of the fall window has no price -> no window mean
        return [item(d, "150.00", 3) for d in days if d != date(2026, 10, 20)]
    return []


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(bl, "REQUEST_GAP", 0)
    monkeypatch.setattr(bl, "LIVE_PAUSE", 0)
    monkeypatch.setattr(bl, "LIVE_BACKOFF", 0)


def config(**changes):
    return {"clone_host": HOST, "locations": dict(thirty_a.LODGING_LOCATIONS),
            "windows": [{"window_key": k, "label": l, "checkin": i, "checkout": o} for k, l, i, o in thirty_a.LODGING_WINDOWS], **changes}


REGIONS = tuple({"id": region_id, "name": name} for region_id, name in thirty_a.REGIONS)


def run(tmp_path, mock=None, *, today=TODAY, canceled=lambda: False, **changes):
    with httpx.Client(transport=httpx.MockTransport(mock or BookDirectMock())) as client:
        return bl.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, canceled, config=config(**changes), regions=REGIONS,
                          client=client, today=today)


def install(monkeypatch, mock, today=TODAY):
    original = bl.collect
    def collect(path, progress, canceled, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(mock)) as client:
            return original(path, progress, canceled, client=client, today=today, **kwargs)
    monkeypatch.setattr(bl, "collect", collect)


def start(client, destination_id="30a", url=URL):
    source = next(s for s in client.get(f"/api/sources?destination_id={destination_id}").json() if s["url"] == url)
    result = client.post("/api/jobs", json={"kind": "source_collection", "source_id": source["id"]}, headers=HEADERS)
    assert result.status_code == 202, result.text
    return finished(client, result.json()["id"])


def everything_written(root, db_path):
    """Every byte the app wrote: files (gzip bodies decompressed) and a text dump of the database."""
    blobs = []
    for path in Path(root).rglob("*"):
        if path.is_file() and not path.name.startswith("studio.sqlite3"):
            data = path.read_bytes()
            blobs.append(gzip.decompress(data) if path.suffix == ".gz" else data)
    with sqlite3.connect(db_path) as con:
        blobs.append("\n".join(con.iterdump()).encode("utf-8"))
    return blobs


# --- Client key and front end ----------------------------------------------------------------------------------

def test_key_is_read_from_the_bundle_named_in_the_entry_page_and_never_stored(tmp_path):
    mock = BookDirectMock()
    result = run(tmp_path, mock)
    paths = [str(r.url.copy_with(query=None)) for r in mock.seen[:3]]
    assert paths == [URL, f"https://{HOST}/20261006094543/bookdirect.min.js", f"https://admin.bookdirect.net/hs4/api/v1/clones/{HOST}/show.json"]
    assert all("authorization" not in r.headers for r in mock.seen[:2])          # the key goes only to the API host
    assert all(r.headers["authorization"] == f"Token token={KEY}" for r in mock.seen[2:])
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    bundle = manifest["responses"][1]
    assert bundle["note"] == "front-end-bundle" and bundle["raw_file"] is None and "anahtar" in bundle["withheld"]
    assert all(entry["raw_file"] for entry in manifest["responses"] if entry["note"] != "front-end-bundle")
    assert all(KEY.encode() not in blob for blob in everything_written(tmp_path, tmp_path / "none.sqlite3"))
    assert KEY not in json.dumps(result.metadata) + json.dumps(result.related, default=str) + json.dumps(result.records)
    assert result.metadata["front_end_path"] == "/20261006094543/"


@pytest.mark.parametrize("bundle,entry,match", [
    ('cfg={api:"x"}', ENTRY, "istemci anahtarı tanımı"),
    ('a={auth_token:"key-one-1234"};b={auth_token:"key-two-5678"}', ENTRY, "istemci anahtarı tanımı"),
    (BUNDLE, "<html><script src='app.js'></script></html>", "sürüm yolu veya ön yüz paketi"),
])
def test_missing_or_ambiguous_key_fails_before_any_api_request(tmp_path, bundle, entry, match):
    mock = BookDirectMock(bundle=bundle, entry=entry)
    with pytest.raises(SourceError, match=match):
        run(tmp_path, mock)
    assert all(r.url.host == HOST for r in mock.seen)


def test_a_response_containing_the_key_is_not_stored(tmp_path):
    data = inventory()
    data[62708][0]["lodging"]["description"] = f"leaked {KEY}"
    run(tmp_path, BookDirectMock(data))
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    withheld = [e for e in manifest["responses"] if e.get("withheld") and e["note"] != "front-end-bundle"]
    assert withheld and all(e["note"].startswith("lodgings-") and "-62708-" in e["note"] for e in withheld)
    assert all(KEY.encode() not in blob for blob in everything_written(tmp_path, tmp_path / "none.sqlite3"))


# --- Locations, paging, windows -----------------------------------------------------------------------------------

def test_locations_map_by_name_and_seagrove_beach_joins_seagrove(tmp_path):
    result = run(tmp_path)
    filters = {(f["window_key"], f["location_name"]): f for f in result.related["filters"]}
    assert len(result.related["filters"]) == 4 * 14
    assert filters[("fall-2026", "Seagrove Beach")]["region_id"] == "seagrove" and filters[("fall-2026", "Seagrove")]["region_id"] == "seagrove"
    assert filters[("fall-2026", "Watercolor")]["region_id"] == "watercolor" and filters[("fall-2026", "Watersound")]["region_id"] == "watersound"
    assert result.metadata["unmapped_locations"] == ["Miramar Beach"] and result.excluded_count == 1
    ids = {r["lodging_id"] for r in result.records}
    assert 9001 not in ids and {2001, 2002, 2003} <= ids
    rows = [r for r in result.related["results"] if r["lodging_id"] == 2002 and r["window_key"] == "fall-2026"]
    assert sorted(r["location_id"] for r in rows) == [2439, 62711]            # each row keeps the filter it came from


def test_configured_location_missing_from_the_source_fails(tmp_path):
    with pytest.raises(SourceError, match="yapılandırılmış konum bulunamadı: Test Town"):
        run(tmp_path, locations={**thirty_a.LODGING_LOCATIONS, "Test Town": "seaside"})


def test_mapping_to_an_unknown_region_fails_without_http(tmp_path):
    mock = BookDirectMock()
    with pytest.raises(SourceError, match="bölgeleriyle uyuşmuyor"):
        run(tmp_path, mock, locations={"Seaside": "nowhere"})
    assert mock.seen == []


def test_every_page_is_read(tmp_path):
    mock = BookDirectMock()
    result = run(tmp_path, mock)
    seaside = [r for r in mock.seen if r.url.path.endswith("/lodgings.json") and r.url.params["group_ids[]"] == "2565"
               and r.url.params["checkin"] == "20261017"]
    assert [r.url.params["page"] for r in seaside] == ["1", "2"]
    assert {f["page_count"] for f in result.related["filters"] if f["location_id"] == 2565} == {2}
    assert sum(1 for r in result.related["results"] if r["window_key"] == "fall-2026" and r["location_id"] == 2565) == 60


def test_a_changing_total_is_retried_once_then_fails(tmp_path):
    class Shifting(BookDirectMock):
        def __call__(self, request):
            response = super().__call__(request)
            if request.url.path.endswith("/lodgings.json") and request.url.params["group_ids[]"] == "2565" and request.url.params["page"] == "2":
                body = json.loads(response.content)
                body["request"]["total_count"] = 61
                return self.json(body)
            return response
    mock = Shifting()
    with pytest.raises(SourceError, match="tutarlı bir sonuç vermedi"):
        run(tmp_path, mock)
    pages = [r.url.params["page"] for r in mock.seen if r.url.path.endswith("/lodgings.json") and r.url.params["group_ids[]"] == "2565"]
    assert pages == ["1", "2", "1", "2"]


def test_past_windows_are_skipped_and_recorded(tmp_path):
    mock = BookDirectMock()
    result = run(tmp_path, mock, today=date(2026, 12, 1))
    statuses = {w["window_key"]: w["status"] for w in result.related["windows"]}
    assert statuses == {"fall-2026": "skipped_past", "winter-2027": "searched", "spring-break-2027": "searched", "summer-2027": "searched"}
    assert result.metadata["skipped_past_windows"] == ["fall-2026"]
    assert not any(r.url.params.get("checkin") == "20261017" for r in mock.seen)
    assert {f["window_key"] for f in result.related["filters"]} == {"winter-2027", "spring-break-2027", "summer-2027"}
    with pytest.raises(SourceError, match="geçmişte kaldı"):
        run(tmp_path, BookDirectMock(), today=date(2027, 8, 1))


# --- Prices: list fields, live rates, calendars ---------------------------------------------------------------

def test_empty_price_fields_stay_null(tmp_path):
    result = run(tmp_path)
    rows = {(r["window_key"], r["lodging_id"]): r for r in result.related["results"]}
    assert rows[("fall-2026", 1000)]["average_rate"] == 250.0 and rows[("fall-2026", 1000)]["average_rate_usd"] == 250.0
    assert rows[("fall-2026", 1000)]["los"] == 4
    empty = rows[("fall-2026", 3001)]
    assert (empty["average_rate"], empty["average_rate_usd"], empty["los"], empty["min_stays"], empty["liveness"]) == (None, None, None, None, None)
    listing = next(r for r in result.records if r["lodging_id"] == 2003)
    assert listing["bedrooms"] is None and listing["sleeps"] is None and listing["category_names"] == ["All Lodging", "Hotels"]
    assert next(r for r in result.records if r["lodging_id"] == 1000)["amenities"] == ["Internet Access", "Swimming Pool"]


def test_live_rates_are_asked_again_only_while_pending(tmp_path):
    mock = BookDirectMock()
    result = run(tmp_path, mock)
    fall = [(attempt, ids) for checkin, attempt, ids in mock.live_calls if checkin == "20261017"]
    assert fall == [(1, [1001, 1002, 1003]), (2, [1001])]
    rows = {r["lodging_id"]: r for r in result.related["results"] if r["window_key"] == "fall-2026" and r["location_id"] == 2565}
    assert (rows[1001]["live_status"], rows[1001]["live_average_rate_usd"], rows[1001]["live_los"], rows[1001]["live_liveness"],
            rows[1001]["live_attempts"]) == ("answered", 310.0, 3, 0, 2)
    assert (rows[1002]["live_status"], rows[1002]["live_average_rate_usd"], rows[1002]["live_attempts"]) == ("answered", None, 1)
    assert (rows[1003]["live_status"], rows[1003]["live_average_rate_usd"]) == ("no_answer", None)
    assert rows[1005]["live_status"] == "not_requested" and rows[1005]["live_attempts"] == 0
    assert result.metadata["live_rate_requests"] == 4 * 2


def test_live_rates_stop_after_the_attempt_limit(tmp_path, monkeypatch):
    class Stuck(BookDirectMock):
        def __call__(self, request):
            response = super().__call__(request)
            if request.url.path.endswith("/live_rates.json"):
                body = json.loads(response.content)
                for row in body["data"]["live_rates"]:
                    row["liveness"] = 1
                return self.json(body)
            return response
    mock = Stuck()
    run(tmp_path, mock)
    assert [attempt for checkin, attempt, _ in mock.live_calls if checkin == "20261017"] == [1, 2, 3, 4, 5]


def test_live_rates_follow_the_front_end_rule():
    base = {"average_rate": None, "average_rate_usd": None, "live_rates_enabled": 0, "liveness": None}
    assert not bl.needs_live(base)                                                        # no live integration at all
    assert bl.needs_live({**base, "live_rates_enabled": 1})                                # enabled, no price yet
    assert bl.needs_live({**base, "liveness": 0})                                          # the front end asks when liveness is set
    assert not bl.needs_live({**base, "live_rates_enabled": 1, "average_rate": 250.0})     # already priced and not pending
    assert bl.needs_live({**base, "liveness": 1, "average_rate": 250.0})                   # priced but pending


def test_calendar_is_read_once_per_listing_and_summarized_by_month(tmp_path):
    mock = BookDirectMock()
    result = run(tmp_path, mock)
    calendar_calls = [r for r in mock.seen if r.url.path.endswith("/rates.json")]
    hidden = {r["lodging_id"] for r in result.records if r["hide_rate_calendar"]}
    assert hidden == {2001} and result.metadata["calendars_skipped_hidden"] == 1 and result.metadata["calendars_read"] == len(result.records) - 1
    assert len(calendar_calls) == len(result.records) - 1 == len({r.url.path for r in calendar_calls})
    assert not any(r.url.path.endswith("/lodgings/2001/rates.json") for r in calendar_calls)     # hidden calendar is not asked
    assert calendar_calls[0].url.params["checkin"] == "20261007" and calendar_calls[0].url.params["checkout"] == "20271007"
    calendars = {c["lodging_id"]: c for c in result.related["calendars"]}
    assert calendars[1004]["status"] == "unavailable" and calendars[1000]["priced_days"] == 365 and calendars[2002]["priced_days"] == 0
    assert 2001 not in calendars and not any(c["lodging_id"] == 2001 for c in result.related["calendar_windows"])
    months = {(m["lodging_id"], m["month"]): m for m in result.related["months"]}
    assert months[(1000, "2026-10")] == {"lodging_id": 1000, "month": "2026-10", "priced_days": 25, "min_rate": 200.0, "median_rate": 200.0,
                                         "max_rate": 200.0, "common_los": 4}
    assert months[(1000, "2027-07")]["median_rate"] == 400.0 and months[(1000, "2027-07")]["common_los"] == 7
    assert not any(m["lodging_id"] == 2001 for m in result.related["months"])          # an empty calendar adds no month rows
    windows = {(c["lodging_id"], c["window_key"]): c for c in result.related["calendar_windows"]}
    assert windows[(1000, "fall-2026")] == {"lodging_id": 1000, "window_key": "fall-2026", "nights": 7, "priced_nights": 7, "mean_rate": 200.0, "max_los": 4}
    assert windows[(1000, "summer-2027")]["mean_rate"] == 400.0
    assert windows[(1005, "fall-2026")]["priced_nights"] == 6 and windows[(1005, "fall-2026")]["mean_rate"] is None
    assert windows[(1005, "winter-2027")]["mean_rate"] == 150.0


def test_month_summary_median_and_most_common_stay():
    rows = bl.month_summary([("2027-01-01", 100.0, 3), ("2027-01-02", 300.0, 7), ("2027-01-03", 200.0, 7), ("2027-02-01", 90.0, None)])
    assert rows == [{"month": "2027-01", "priced_days": 3, "min_rate": 100.0, "median_rate": 200.0, "max_rate": 300.0, "common_los": 7},
                    {"month": "2027-02", "priced_days": 1, "min_rate": 90.0, "median_rate": 90.0, "max_rate": 90.0, "common_los": None}]


@pytest.mark.parametrize("change,match", [
    ({"title": ""}, "kimlik veya ad"),
    ({"id": "x"}, "kimlik veya ad"),
    ({"bedrooms": "many"}, "yatak odası sayı değil"),
    ({"latitude": "95"}, "aralık dışında"),
    ({"category_ids": "103"}, "kategori listesi"),
])
def test_listing_structure_errors(tmp_path, change, match):
    data = inventory()
    data[62708][0]["lodging"].update(change)
    with pytest.raises(SourceError, match=match):
        run(tmp_path, BookDirectMock(data))


def test_cancel_between_requests(tmp_path):
    calls = []
    with pytest.raises(CollectionCanceled):
        run(tmp_path, BookDirectMock(before=calls.append), canceled=lambda: len(calls) >= 5)
    assert len(calls) == 5


# --- Database, API, migration ------------------------------------------------------------------------------------

def test_api_collects_stores_and_summarizes(tmp_path, monkeypatch):
    mock = BookDirectMock()
    install(monkeypatch, mock)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        source = next(s for s in client.get("/api/sources").json() if s["url"] == URL)
        connector = DEFAULT_REGISTRY.by_name("bookdirect-lodging")
        assert source["connector"] == {"name": "bookdirect-lodging", "version": "bookdirect-lodging/2", "method": "JSON"}
        job = start(client)
        assert job["status"] == "done", job["message"]
        assert db.run_diff(job["id"]) == {"available": False, "reason": connector.diff_reason}
        assert [r["id"] for r in client.get("/api/lodging-runs").json()] == [job["id"]]
        assert client.get("/api/bootstrap").json()["lodging_runs"][0]["id"] == job["id"]
        data = client.get(f"/api/lodging-runs/{job['id']}").json()
        assert data["run"]["record_count"] == 64 and data["snapshot"]["listing_count"] == 64 and data["snapshot"]["searched_on"] == "2026-10-07"
        assert [w["window_key"] for w in data["windows"]] == ["fall-2026", "winter-2027", "spring-break-2027", "summer-2027"]
        assert [r["region_id"] for r in data["regions"]][:3] == ["dune-allen", "gulf-place", "santa-rosa-beach"]   # west to east profile order
        assert next(r for r in data["regions"] if r["region_id"] == "seagrove")["filters"] == ["Seagrove", "Seagrove Beach"]
        cells = {(c["region_id"], c["window_key"]): c for c in data["cells"]}
        seaside = cells[("seaside", "fall-2026")]
        assert seaside["listing_count"] == 60 and seaside["categories"] == {"Beach Homes & Cottages": 60} and seaside["no_category"] == 0
        assert seaside["priced_count"] == 3 and seaside["price_sources"] == {"liste": 1, "canli": 1, "takvim": 1}
        assert (seaside["price_q1"], seaside["price_median"], seaside["price_q3"]) == (225.0, 250.0, 280.0)   # 200 calendar (1006), 250 list, 310 live
        assert seaside["priced_share"] == 0.05 and seaside["bedrooms_median"] == 3.5 and seaside["sleeps_median"] == 6.5
        assert seaside["bedrooms_4_plus_share"] == 0.5 and seaside["bedroom_buckets"]["2"] == 15
        seagrove = cells[("seagrove", "fall-2026")]
        assert seagrove["listing_count"] == 3                                                        # the shared listing counts once
        assert seagrove["categories"] == {"Beach Homes & Cottages": 2, "Hotels": 1} and seagrove["bedrooms_known"] == 2
        assert seagrove["priced_count"] == 0 and seagrove["price_median"] is None and seagrove["priced_share"] == 0.0
        assert cells[("dune-allen", "fall-2026")]["bedroom_buckets"]["stüdyo"] == 1
        assert ("watercolor", "fall-2026") in cells and cells[("watercolor", "fall-2026")]["listing_count"] == 0
        monthly = {(m["region_id"], m["month"]): m for m in data["monthly"]}
        assert monthly[("seaside", "2027-07")] == {"region_id": "seaside", "month": "2027-07", "listing_count": 3, "median_rate": 400.0}
        assert "tam envanter değildir" in data["label"] and "2026-10-07" in data["label"]
        listings = client.get(f"/api/lodging-runs/{job['id']}/listings?region_id=seagrove").json()["listings"]
        shared = next(l for l in listings if l["lodging_id"] == 2002)
        assert shared["filters"] == ["Seagrove", "Seagrove Beach"] and set(shared["windows"]) == {"fall-2026", "winter-2027", "spring-break-2027", "summer-2027"}
        first = next(l for l in client.get(f"/api/lodging-runs/{job['id']}/listings?region_id=seaside").json()["listings"] if l["lodging_id"] == 1000)
        assert first["windows"]["fall-2026"]["price"] == 250.0 and first["windows"]["fall-2026"]["price_source"] == "liste"
        assert first["calendar"]["status"] == "read" and first["months"][0]["month"] == "2026-10"
        assert client.get(f"/api/lodging-runs/{job['id']}/listings?region_id=nowhere").status_code == 404
        raw = client.get(f"/api/lodging-runs/{job['id']}/raw")
        assert raw.status_code == 200 and json.loads(raw.content)["connector"] == "bookdirect-lodging/2"
        assert client.get("/api/lodging-runs/missing").status_code == 404
        with db.connect() as con:
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
            assert con.execute("SELECT COUNT(*) FROM lodging_rate_months").fetchone()[0] > 0
        assert all(KEY.encode() not in blob for blob in everything_written(tmp_path, db.path))
        assert KEY not in json.dumps(db.job(job["id"])) and KEY not in json.dumps(db.source_run(job["id"]))


def test_failure_after_insert_rolls_back_and_keeps_previous_snapshot(tmp_path, monkeypatch):
    install(monkeypatch, BookDirectMock())
    tables = ("lodging_snapshots", "lodging_windows", "lodging_filters", "lodging_listings", "lodging_search_results", "lodging_calendars",
              "lodging_rate_months", "lodging_calendar_windows")
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        good = start(client); assert good["status"] == "done"
        original = bl.BookDirectLodgingConnector.store_records
        def fail(self, con, run_id, records, related=None):
            original(self, con, run_id, records, related); raise RuntimeError("synthetic after insert")
        monkeypatch.setattr(bl.BookDirectLodgingConnector, "store_records", fail)
        failed = start(client); assert failed["status"] == "failed"
        assert [r["id"] for r in client.get("/api/lodging-runs").json()] == [good["id"]]
        assert client.get(f"/api/lodging-runs/{failed['id']}").status_code == 404
        with client.app.state.db.connect() as con:
            for table in tables:
                assert con.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id=?", (failed["id"],)).fetchone()[0] == 0
                assert con.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id=?", (good["id"],)).fetchone()[0] > 0


def test_cancel_job_through_api_publishes_nothing(tmp_path, monkeypatch):
    release, entered = threading.Event(), threading.Event()
    def before(count):
        if count == 6:
            entered.set(); release.wait(30)
    install(monkeypatch, BookDirectMock(before=before))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        source = next(s for s in client.get("/api/sources").json() if s["url"] == URL)
        identifier = client.post("/api/jobs", json={"kind": "source_collection", "source_id": source["id"]}).json()["id"]
        try:
            assert entered.wait(30)
            assert client.post(f"/api/jobs/{identifier}/cancel").json()["status"] == "canceled"
        finally:
            release.set()
        assert finished(client, identifier)["status"] == "canceled"
        assert client.get("/api/lodging-runs").json() == []
        with client.app.state.db.connect() as con:
            assert con.execute("SELECT COUNT(*) FROM lodging_listings").fetchone()[0] == 0
        assert all(KEY.encode() not in blob for blob in everything_written(tmp_path, client.app.state.db.path))


def test_fresh_database_has_lodging_configuration_and_source(tmp_path):
    db = Database(tmp_path / "studio.sqlite3"); db.initialize()
    lodging = db.context("30a").lodging
    assert lodging["clone_host"] == HOST and lodging["locations"] == thirty_a.LODGING_LOCATIONS
    assert [(w["window_key"], w["checkin"], w["checkout"]) for w in lodging["windows"]] == [(k, i, o) for k, _, i, o in thirty_a.LODGING_WINDOWS]
    source = next(s for s in db.sources() if s["url"] == URL)
    assert (source["method"], source["category"], source["destination_id"]) == ("JSON", "Konaklama", "30a")
    with db.connect() as con:
        for statement in ("INSERT INTO destination_lodging_sources VALUES ('30a','admin.bookdirect.net',1)",
                          "UPDATE destination_lodging_windows SET checkout=checkin",
                          "UPDATE destination_lodging_windows SET checkin='2026-13-01'",
                          "INSERT INTO destination_lodging_locations VALUES ('30a','Elsewhere','no-such-region')"):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute(statement)


def test_v9_to_v10_migration_adds_tables_configuration_and_source_with_backup(tmp_path):
    path = tmp_path / "studio.sqlite3"; make_v8(path)
    with sqlite3.connect(path) as con:
        from studio.migration_v9 import upgrade_v9
        con.execute("BEGIN IMMEDIATE"); upgrade_v9(con); con.commit()
        assert con.execute("PRAGMA user_version").fetchone()[0] == 9
        before = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in table_counts(con)}
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 11
        assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        counts = table_counts(con)
        assert counts == {**{t: len(rows) for t, rows in before.items()}, **V10_TABLES, **V11_TABLES, "sources": len(before["sources"]) + 2}
        after = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in before}
        assert {t: r for t, r in after.items() if t != "sources"} == {t: r for t, r in before.items() if t != "sources"}
        assert after["sources"][:len(before["sources"])] == before["sources"]
    backup, = (tmp_path / "backups").glob("*-v9-*.sqlite3")
    with sqlite3.connect(backup) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 9
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert table_counts(con)["sources"] == len(before["sources"]) + 2 and table_counts(con)["destination_lodging_windows"] == 4


def test_v9_to_v10_failure_rolls_back_everything(tmp_path, monkeypatch):
    from studio import database
    from studio.migration_v9 import upgrade_v9
    path = tmp_path / "studio.sqlite3"; make_v8(path)
    with sqlite3.connect(path) as con:
        con.execute("BEGIN IMMEDIATE"); upgrade_v9(con); con.commit()
        before = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in table_counts(con)}
    original = database.upgrade_v10
    def fail(con): original(con); raise RuntimeError("after all DDL, configuration and source inserts")
    with monkeypatch.context() as m:
        m.setattr(database, "upgrade_v10", fail)
        with pytest.raises(RuntimeError):
            Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 9
        assert table_counts(con).keys() == before.keys()
        assert {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in before} == before
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 11


def test_v10_never_duplicates_an_existing_lodging_source_or_overwrites_configuration(tmp_path):
    db = Database(tmp_path / "studio.sqlite3"); db.initialize()
    with db.connect() as con:
        con.execute("UPDATE destination_lodging_windows SET label='edited' WHERE window_key='fall-2026'")
        con.execute("UPDATE sources SET name='edited lodging', enabled=0 WHERE url=?", (URL,))
        from studio.migration_v10 import seed_destination_lodging
        seed_destination_lodging(con, thirty_a)
        assert con.execute("SELECT COUNT(*) FROM sources WHERE url=?", (URL,)).fetchone()[0] == 1
        assert con.execute("SELECT label FROM destination_lodging_windows WHERE window_key='fall-2026'").fetchone()[0] == "edited"


def test_destination_without_lodging_configuration_fails_and_runs_never_mix(tmp_path, monkeypatch):
    mock = BookDirectMock()
    install(monkeypatch, mock)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        add_destination(db)
        assert db.context("test-coast").lodging is None
        created = client.post("/api/sources", json=payload(destination_id="test-coast", url="https://othercoast.bookdirect.net/", category="Konaklama"))
        assert created.status_code == 201, created.text
        job = start(client, "test-coast", "https://othercoast.bookdirect.net/")
        assert job["status"] == "failed" and "konaklama (Book>Direct) yapılandırması yok" in job["message"]
        assert mock.seen == []
        good = start(client)
        assert good["status"] == "done"
        assert client.get("/api/lodging-runs?destination_id=test-coast").json() == []
        assert [r["id"] for r in client.get("/api/lodging-runs").json()] == [good["id"]]
        assert client.get("/api/lodging-runs?destination_id=missing").status_code == 404


def test_source_host_must_match_the_destination_configuration(tmp_path, monkeypatch):
    mock = BookDirectMock()
    install(monkeypatch, mock)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        client.post("/api/sources", json=payload(url="https://othercoast.bookdirect.net/", category="Konaklama"))
        job = start(client, url="https://othercoast.bookdirect.net/")
        assert job["status"] == "failed" and "uyuşmuyor" in job["message"] and mock.seen == []


@pytest.mark.parametrize("url,supported", [
    (URL, True), ("https://visitsouthwalton.bookdirect.net", True), ("https://admin.bookdirect.net/", False),
    ("http://visitsouthwalton.bookdirect.net/", False), ("https://visitsouthwalton.bookdirect.net/#/lodgings", False),
    ("https://bookdirect.net.example.com/", False), ("https://www.visitsouthwalton.com/", False),
])
def test_connector_supports_only_clone_front_ends(url, supported):
    assert bl.BookDirectLodgingConnector().supports({"url": url}) is supported


def test_quartiles_and_price_priority():
    assert bl.quartiles([]) == (None, None, None) and bl.quartiles([5.0]) == (5.0, 5.0, 5.0)
    assert bl.quartiles([100.0, 200.0, 300.0, 400.0]) == (175.0, 250.0, 325.0)
    row = {"average_rate": None, "average_rate_usd": None, "live_average_rate_usd": None}
    assert bl.price_of(row, {"mean_rate": 120.0}) == (120.0, "takvim")
    assert bl.price_of({**row, "live_average_rate_usd": 130.0}, {"mean_rate": 120.0}) == (130.0, "canli")
    assert bl.price_of({**row, "average_rate": 140.0}, None) == (140.0, "liste")
    assert bl.price_of(row, {"mean_rate": None}) == (None, None)
    # A current live answer replaces a pending search price, as on the front end; a pending live answer does not.
    pending = {**row, "average_rate": 250.0, "average_rate_usd": 250.0, "live_average_rate_usd": 310.0}
    assert bl.price_of({**pending, "live_liveness": 0}, None) == (310.0, "canli")
    assert bl.price_of({**pending, "live_liveness": 1}, None) == (250.0, "liste")


def test_listing_keeps_the_company_page_and_phones(tmp_path):
    result = run(tmp_path)
    listings = {r["lodging_id"]: r for r in result.records}
    assert listings[2001]["url"] == "https://agency.example/rentals/2001" and listings[2001]["toll_free"] == "(850)555-0101"
    assert listings[1000]["url"] == "https://example.com/rental" and listings[1000]["phone"] is None
    assert bl.web_url("javascript:alert(1)") is None and bl.web_url("") is None and bl.web_url("https://a.example/x y") is None


def test_v10_to_v11_migration_adds_listing_link_columns(tmp_path):
    from studio.migration_v11 import upgrade_v11
    path = tmp_path / "studio.sqlite3"
    db = Database(path); db.initialize()
    with sqlite3.connect(path) as con:
        columns = [row[1] for row in con.execute("PRAGMA table_info(lodging_listings)")]
        assert columns[-3:] == ["url", "phone", "toll_free"] and con.execute("PRAGMA user_version").fetchone()[0] == 11
        with pytest.raises(sqlite3.OperationalError):
            con.execute("BEGIN IMMEDIATE"); upgrade_v11(con)                     # columns already exist; the transaction rolls back
        con.rollback()
        assert con.execute("PRAGMA user_version").fetchone()[0] == 11

