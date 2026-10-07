"""Climate collectors: NCEI normals, NDBC sea water temperature and HURDAT2 storm passages.

Synthetic fixtures only (tests/fixtures/climate); suite-wide no_real_http prevents internet access. The storm fixture uses
a test corridor on the equator, (0, -87) -> (0, -86), where a point beside the corridor is exactly R * |latitude| away.
"""
import gzip
import hashlib
import json
import math
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Database
from studio.destinations import thirty_a
from studio.migration_v7 import upgrade_v7
from studio.migration_v8 import seed_destination_climate
from studio.sources import climate_http
from studio.sources import climate_normals as cn
from studio.sources import storm_proximity as sp
from studio.sources import water_temperature as wt
from studio.sources.base import CollectionCanceled, SourceError
from studio.sources.geo import EARTH_RADIUS_KM, KM_PER_NMI, Segment, distance_km
from studio.sources.registry import DEFAULT_REGISTRY
from tests.legacy import V8_TABLES
from tests.test_beaches import HEADERS, finished
from tests.test_destinations import add_destination
from tests.test_neighborhoods import make_v6
from tests.test_studio import payload

FIXTURES = Path(__file__).parent / "fixtures/climate"
NORMALS = json.loads((FIXTURES / "normals.json").read_text(encoding="utf-8"))
HURDAT = (FIXTURES / "hurdat2.txt").read_text(encoding="ascii")
NHC_PAGE = (FIXTURES / "nhc-data.html").read_text(encoding="utf-8")
HURDAT_FILE = "hurdat2-2010-2012-010126.txt"
KM_PER_DEGREE = EARTH_RADIUS_KM * math.pi / 180
COASTAL, INLAND = "USW00053853", "USC00082220"
TEST_CORRIDOR = {"label": "Test corridor", "west_latitude": 0.0, "west_longitude": -87.0, "west_reference": "west test point",
                 "east_latitude": 0.0, "east_longitude": -86.0, "east_reference": "east test point", "radii_nmi": [50, 100]}
BUOY = {"station_key": "water", "kind": "water_temperature", "station_id": "TEST1", "label": "Synthetic buoy",
        "role": "deniz suyu sıcaklığı", "latitude": 0.1, "longitude": -86.5, "distance_km": 11.1, "first_year": 2010}
CLIMATE_URLS = {"normals": cn.SOURCE_URL, "water": wt.SOURCE_URL, "storms": sp.SOURCE_URL}


@pytest.fixture(autouse=True)
def no_delay(monkeypatch):
    monkeypatch.setattr(climate_http, "REQUEST_GAP", 0)
    monkeypatch.setattr(climate_http, "RETRY_SECONDS", 0)


# --- Synthetic sources ------------------------------------------------------------------------------

def gz(name):
    return gzip.compress((FIXTURES / name).read_bytes())


class NormalsMock:
    def __init__(self, rows=None):
        self.rows = NORMALS if rows is None else rows
        self.seen = []

    def __call__(self, request):
        self.seen.append(request)
        assert request.url.host == "www.ncei.noaa.gov" and request.url.path == "/access/services/data/v1"
        wanted = request.url.params["stations"].split(",")
        rows = [row for row in self.rows if row.get("STATION", wanted[0]) in wanted]
        return httpx.Response(200, content=json.dumps(rows).encode(), headers={"content-type": "application/json"})


class BuoyMock:
    def __init__(self, files=None, before=None):
        self.files = {2010: gz("ndbc-2010.txt"), 2011: gz("ndbc-2011.txt")} if files is None else files
        self.before = before
        self.seen = []

    def __call__(self, request):
        assert request.url.host == "www.ndbc.noaa.gov"
        station, year = re.fullmatch(r"/data/historical/stdmet/(\w+)h(\d{4})\.txt\.gz", request.url.path).groups()
        self.seen.append((station, int(year)))
        if self.before:
            self.before(len(self.seen))
        body = self.files.get(int(year))
        if body is None:
            return httpx.Response(404, text="<html><title>404 Not Found</title></html>", headers={"content-type": "text/html"})
        return httpx.Response(200, content=body, headers={"content-type": "application/x-gzip"})


class StormMock:
    def __init__(self, page=NHC_PAGE, track=HURDAT):
        self.page, self.track, self.seen = page, track, []

    def __call__(self, request):
        self.seen.append(request.url.path)
        assert request.url.host == "www.nhc.noaa.gov"
        if request.url.path == "/data/":
            return httpx.Response(200, text=self.page, headers={"content-type": "text/html; charset=UTF-8"})
        assert request.url.path == f"/data/hurdat/{HURDAT_FILE}"
        return httpx.Response(200, text=self.track, headers={"content-type": "text/plain"})


def run_normals(tmp_path, handler=None, canceled=lambda: False, stations=thirty_a.CLIMATE_STATIONS):
    with httpx.Client(transport=httpx.MockTransport(handler or NormalsMock())) as client:
        return cn.collect(tmp_path / "manifest.json", lambda *args: None, canceled, stations=stations, client=client)


def run_water(tmp_path, handler=None, canceled=lambda: False, stations=(BUOY,), last_year=2012):
    with httpx.Client(transport=httpx.MockTransport(handler or BuoyMock())) as client:
        return wt.collect(tmp_path / "manifest.json", lambda *args: None, canceled, stations=stations, client=client, last_year=last_year)


def run_storms(tmp_path, handler=None, canceled=lambda: False, corridor=TEST_CORRIDOR):
    with httpx.Client(transport=httpx.MockTransport(handler or StormMock())) as client:
        return sp.collect(tmp_path / "manifest.json", lambda *args: None, canceled, corridor=corridor, client=client)


def install(monkeypatch, module, handler, **fixed):
    original = module.collect
    def collect(path, progress, canceled, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            return original(path, progress, canceled, client=client, **kwargs, **fixed)
    monkeypatch.setattr(module, "collect", collect)


def install_all(monkeypatch, normals=None, water=None, storms=None):
    install(monkeypatch, cn, normals or NormalsMock())
    install(monkeypatch, wt, water or BuoyMock(), last_year=2012)
    install(monkeypatch, sp, storms or StormMock())


def use_test_corridor(db, destination_id="30a"):
    with db.connect() as con:
        con.execute("""UPDATE destination_storm_corridors SET label=?,west_latitude=?,west_longitude=?,west_reference=?,
            east_latitude=?,east_longitude=?,east_reference=? WHERE destination_id=?""",
            (TEST_CORRIDOR["label"], 0.0, -87.0, "west test point", 0.0, -86.0, "east test point", destination_id))


def start(client, url, destination_id="30a"):
    source = next(s for s in client.get(f"/api/sources?destination_id={destination_id}").json() if s["url"] == url)
    result = client.post("/api/jobs", json={"kind": "source_collection", "source_id": source["id"]}, headers=HEADERS)
    assert result.status_code == 202, result.text
    return finished(client, result.json()["id"])


def by_key(records, *keys):
    return {tuple(record[key] for key in keys): record for record in records}


# --- Geometry --------------------------------------------------------------------------------------

def test_great_circle_distances_are_exact_on_the_equator():
    assert distance_km(0, 0, 1, 0) == pytest.approx(KM_PER_DEGREE, rel=1e-12)
    assert distance_km(30, -86, 30, -86) == 0
    corridor = Segment((0, -87), (0, -86))
    assert corridor.distance_km(1, -86.5) == pytest.approx(KM_PER_DEGREE, rel=1e-12)
    assert corridor.distance_km(-0.5, -86.9) == pytest.approx(KM_PER_DEGREE / 2, rel=1e-12)
    assert corridor.distance_km(0, -86.3) == pytest.approx(0, abs=1e-9)
    # Beyond an end the distance is to the nearest endpoint, never to the extended great circle.
    assert corridor.distance_km(0, -85) == pytest.approx(KM_PER_DEGREE, rel=1e-12)
    assert corridor.distance_km(1, -85) == pytest.approx(distance_km(1, -85, 0, -86), rel=1e-12)
    assert corridor.distance_km(0.5, -88) == pytest.approx(distance_km(0.5, -88, 0, -87), rel=1e-12)
    assert Segment((0, -86), (0, -87)).distance_km(1, -85) == pytest.approx(corridor.distance_km(1, -85), rel=1e-12)
    assert KM_PER_NMI == 1.852
    with pytest.raises(ValueError):
        Segment((30, -86), (30, -86))


def test_profile_station_distances_match_the_corridor_geometry():
    corridor = thirty_a.STORM_CORRIDOR
    segment = Segment((corridor["west_latitude"], corridor["west_longitude"]), (corridor["east_latitude"], corridor["east_longitude"]))
    for station in thirty_a.CLIMATE_STATIONS:
        assert round(segment.distance_km(station["latitude"], station["longitude"]), 1) == station["distance_km"], station


# --- HURDAT2 parsing, interpolation and passages -------------------------------------------------

def test_hurdat2_parses_headers_and_track_lines():
    storms = sp.parse_hurdat2(HURDAT)
    assert [(s["storm_id"], s["name"], s["season"], len(s["fixes"])) for s in storms] == [
        ("AL012010", "ALPHA", 2010, 3), ("AL022011", "BRAVO", 2011, 3), ("AL032011", "CHARLIE", 2011, 3),
        ("AL042011", "DELTA", 2011, 2), ("AL012012", "ECHO", 2012, 4), ("AL022012", "FOXTROT", 2012, 2), ("AL032012", "GOLF", 2012, 3)]
    alpha = storms[0]["fixes"]
    assert alpha[0] == (datetime(2010, 8, 1, 0, 0, tzinfo=timezone.utc), "TS", -3.0, -86.5, 40)
    assert alpha[1] == (datetime(2010, 8, 1, 6, 0, tzinfo=timezone.utc), "HU", 0.0, -86.5, 100)
    assert [fix[4] for fix in storms[5]["fixes"]] == [None, None]          # -999 wind is unknown, never zero
    assert storms[6]["fixes"][1][0] == datetime(2012, 9, 10, 15, 30, tzinfo=timezone.utc)  # non-synoptic landfall fix


def track(header, *lines):
    return "\n".join([header, *lines]) + "\n"


LINE = "20100801, {time},  , TS, {lat}, 86.5W,   40, -999, -999, -999, -999, -999, -999, -999, -999, -999, -999, -999, -999, -999, -999"


@pytest.mark.parametrize("text,match", [
    ("", "fırtına bulunamadı"),
    (track("12345678, BROKEN, 1,", LINE.format(time="0000", lat="28.0N")), "başlığı bekleniyordu"),
    (track("AL012010, SHORT, 3,", LINE.format(time="0000", lat="28.0N"), LINE.format(time="0600", lat="28.5N")), "sayısı tutmuyor"),
    (track("AL012010, SHORT, 2,", LINE.format(time="0000", lat="28.0N"), "AL022010, NEXT, 1,", LINE.format(time="0000", lat="28.0N")),
     "iz satırları eksik"),
    (track("AL012010, ZERO, 0,"), "sayısı tutmuyor"),
    (track("AL012010, BADLAT, 1,", LINE.format(time="0000", lat="95.0N")), "aralık dışında"),
    (track("AL012010, BADLAT, 1,", LINE.format(time="0000", lat="28.0X")), "okunamadı"),
    (track("AL012010, BADTIME, 1,", LINE.format(time="2400", lat="28.0N")), "okunamadı"),
    (track("AL012010, ORDER, 2,", LINE.format(time="0600", lat="28.0N"), LINE.format(time="0000", lat="28.5N")), "sıralı değil"),
])
def test_hurdat2_structure_errors(text, match):
    with pytest.raises(SourceError, match=match):
        sp.parse_hurdat2(text)


def test_hourly_linear_interpolation():
    alpha, foxtrot, golf = (storm["fixes"] for storm in sp.parse_hurdat2(HURDAT) if storm["name"] in ("ALPHA", "FOXTROT", "GOLF"))
    points = sp.hourly(alpha)
    assert len(points) == 13 and [p[0].hour for p in points] == list(range(13))
    assert points[3][1:] == (-1.5, -86.5, 70.0, "TS")          # 3 h into the first 6-hour segment
    assert points[6][1:] == (0.0, -86.5, 100, "HU")            # the fix itself, with its own status
    assert points[9][1:] == (1.5, -86.5, 70.0, "HU")
    assert points[-1][1:] == (3.0, -86.5, 40, "TS")
    assert [p[3] for p in sp.hourly(foxtrot)] == [None] * 7    # unknown wind is never interpolated
    assert [p[0].strftime("%H:%M") for p in sp.hourly(golf)] == ["12:00", "13:00", "14:00", "15:00", "15:30", "16:30", "17:30", "18:00"]
    mixed = [(datetime(2020, 1, 1, tzinfo=timezone.utc), "TS", 0.0, 0.0, 50), (datetime(2020, 1, 1, 2, tzinfo=timezone.utc), "TS", 0.2, 0.0, None)]
    assert [p[3] for p in sp.hourly(mixed)] == [50, None, None]


def test_passages_first_entry_closest_distance_and_class():
    records = sp.passages(sp.parse_hurdat2(HURDAT), TEST_CORRIDOR, [50, 100])
    found = by_key(records, "name", "radius_nmi")
    # CHARLIE stays 2 degrees (222 km, 120 nmi) away; DELTA is far out in the Atlantic.
    assert sorted(found) == [("ALPHA", 50), ("ALPHA", 100), ("BRAVO", 50), ("BRAVO", 100), ("ECHO", 50), ("ECHO", 100),
                             ("FOXTROT", 50), ("FOXTROT", 100), ("GOLF", 100)]
    expected = {
        # 50 nmi = 0.833 degrees here, 100 nmi = 1.666 degrees; hourly latitudes step 0.5 (ALPHA) or 0.25 (BRAVO).
        ("ALPHA", 50): ("2010-08-01T05:00Z", 8, 100, "MH", "HU", 0.0),
        ("ALPHA", 100): ("2010-08-01T03:00Z", 8, 100, "MH", "HU", 0.0),
        # BRAVO peaks at 80 kt outside 50 nmi: the class depends on the radius.
        ("BRAVO", 50): ("2011-09-10T03:00Z", 9, 56, "TS", "HU", 0.0),
        ("BRAVO", 100): ("2011-09-10T00:00Z", 9, 80, "HU", "HU", 0.0),
        # ECHO enters 100 nmi on 30 June and 50 nmi on 1 July; it leaves and re-enters but is counted once per radius.
        ("ECHO", 50): ("2012-07-01T00:00Z", 7, 45, "TS", "TS", round(0.5 * KM_PER_DEGREE, 1)),
        ("ECHO", 100): ("2012-06-30T22:00Z", 6, 45, "TS", "TS", round(0.5 * KM_PER_DEGREE, 1)),
        ("FOXTROT", 50): ("2012-08-01T00:00Z", 8, None, None, None, round(0.5 * KM_PER_DEGREE, 1)),
        ("FOXTROT", 100): ("2012-08-01T00:00Z", 8, None, None, None, round(0.5 * KM_PER_DEGREE, 1)),
        # GOLF passes 1 degree east of the corridor's east end: the closest distance is to that endpoint.
        ("GOLF", 100): ("2012-09-10T12:00Z", 9, 70, "HU", "HU", round(KM_PER_DEGREE, 1)),
    }
    actual = {key: (r["first_entry_time"], r["first_entry_month"], r["max_wind_kt"], r["storm_class"], r["status_at_max"], r["closest_km"])
              for key, r in found.items()}
    assert actual == expected
    for record in records:
        assert record["closest_nmi"] == round(record["closest_km"] / KM_PER_NMI, 1) <= record["radius_nmi"]
        assert record["season"] == int(record["storm_id"][4:])
    assert found[("GOLF", 100)]["closest_nmi"] == 60.0


def test_storm_class_thresholds_and_floor():
    assert [sp.storm_class(w) for w in (None, 0, 33, 34, 63, 64, 95, 96, 150)] == [None, "TD", "TD", "TS", "TS", "HU", "HU", "MH", "MH"]
    # 63.9 kt interpolated inside the circle stays TS: the stored wind is floored so value and class agree.
    corridor = {**TEST_CORRIDOR, "radii_nmi": [50]}
    storm = {"storm_id": "AL012020", "name": "EDGE", "season": 2020, "fixes": [
        (datetime(2020, 8, 1, tzinfo=timezone.utc), "TS", 0.0, -86.5, 63), (datetime(2020, 8, 1, 10, tzinfo=timezone.utc), "HU", 3.0, -86.5, 64)]}
    record, = sp.passages([storm], corridor, [50])
    assert record["max_wind_kt"] == 63 and record["storm_class"] == "TS"


def test_monthly_counts_by_radius_and_season_range():
    records = sp.passages(sp.parse_hurdat2(HURDAT), TEST_CORRIDOR, [50, 100])
    def nonzero(table):
        return {month: {k: v for k, v in counts.items() if v} for month, counts in table.items() if any(counts.values())}
    assert nonzero(sp.monthly_counts(records, 50)) == {7: {"TS": 1}, 8: {"MH": 1, "bilinmiyor": 1}, 9: {"TS": 1}}
    assert nonzero(sp.monthly_counts(records, 100)) == {6: {"TS": 1}, 8: {"MH": 1, "bilinmiyor": 1}, 9: {"HU": 2}}
    assert nonzero(sp.monthly_counts(records, 100, 2011, 2011)) == {9: {"HU": 1}}
    assert nonzero(sp.monthly_counts(records, 100, 2012)) == {6: {"TS": 1}, 8: {"bilinmiyor": 1}, 9: {"HU": 1}}
    assert sum(sum(c.values()) for c in sp.monthly_counts(records, 100).values()) == len({r["storm_id"] for r in records})


# --- NHC collection --------------------------------------------------------------------------------

def test_storm_collection_reads_current_file_name_and_keeps_raw_files(tmp_path):
    mock = StormMock()
    result = run_storms(tmp_path, mock)
    assert mock.seen == ["/data/", f"/data/hurdat/{HURDAT_FILE}"]      # the Pacific file and the PDFs are never read
    assert result.total_count == 7 and len(result.records) == 9
    assert {k: result.metadata[k] for k in ("hurdat_file", "hurdat_url", "storm_count", "first_season", "last_season", "passages")} == {
        "hurdat_file": HURDAT_FILE, "hurdat_url": f"https://www.nhc.noaa.gov/data/hurdat/{HURDAT_FILE}", "storm_count": 7,
        "first_season": 2010, "last_season": 2012, "passages": {"50": 4, "100": 5}}
    assert "bizim hesabımız" in result.metadata["scope"]
    corridor = result.related["corridor"]
    assert {k: corridor[k] for k in TEST_CORRIDOR} == TEST_CORRIDOR and corridor["hurdat_file"] == HURDAT_FILE
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert [r["note"] for r in manifest["responses"]] == ["nhc-data-page", HURDAT_FILE]
    for response in manifest["responses"]:
        body = (tmp_path / response["raw_file"]).read_bytes()
        assert response["raw_sha256"] == hashlib.sha256(body).hexdigest() and response["bytes"] == len(body)
    assert (tmp_path / manifest["responses"][1]["raw_file"]).read_text(encoding="ascii") == HURDAT


@pytest.mark.parametrize("page", [
    NHC_PAGE.replace(HURDAT_FILE, "hurdat2-renamed.txt"),
    NHC_PAGE.replace("</ul>", '<li><a href="/data/hurdat/hurdat2-1851-2012-010126.txt">other</a></li></ul>'),
])
def test_storm_page_without_exactly_one_atlantic_file_fails(tmp_path, page):
    mock = StormMock(page=page)
    with pytest.raises(SourceError, match="tek bir Atlantik"):
        run_storms(tmp_path, mock)
    assert mock.seen == ["/data/"]


def test_same_atlantic_link_twice_is_one_file(tmp_path):
    page = NHC_PAGE.replace("</ul>", f'<li><a href="/data/hurdat/{HURDAT_FILE}">again</a></li></ul>')
    assert run_storms(tmp_path, StormMock(page=page)).metadata["hurdat_file"] == HURDAT_FILE


@pytest.mark.parametrize("corridor,match", [(None, "koridoru yapılandırılmamış"), ({**TEST_CORRIDOR, "radii_nmi": []}, "yarıçapları"),
                                            ({**TEST_CORRIDOR, "radii_nmi": [0]}, "yarıçapları")])
def test_storm_configuration_errors_fail_without_http(tmp_path, corridor, match):
    mock = StormMock()
    with pytest.raises(SourceError, match=match):
        run_storms(tmp_path, mock, corridor=corridor)
    assert mock.seen == []


# --- HTTP reader (shared by the three collectors) --------------------------------------------------

def test_redirect_to_other_host_is_rejected_before_follow(tmp_path):
    seen = []
    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://example.com/data/"})
    with pytest.raises(SourceError, match="izin verilmeyen"):
        run_storms(tmp_path, handler)
    assert seen == ["https://www.nhc.noaa.gov/data/"]


def test_same_host_redirect_followed(tmp_path):
    base = StormMock()
    def handler(request):
        if request.url.path == "/data":
            return httpx.Response(301, headers={"location": "/data/"})
        return base(request)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        reader = climate_http.Reader(client, tmp_path / "manifest.json", lambda: False, connector="test", hosts={"www.nhc.noaa.gov"},
                                     max_bytes=10_000, label="Test")
        body, final = reader.get("https://www.nhc.noaa.gov/data", suffix=".html", note="page", content_types={"text/html"})
    assert body.decode() == NHC_PAGE and final == "https://www.nhc.noaa.gov/data/"


@pytest.mark.parametrize("responses,match", [
    ([httpx.Response(500), httpx.Response(500)], "sunucu hatası"),
    ([httpx.Response(429)], "istek sınırı"),
    ([httpx.Response(403)], "HTTP 403"),
    ([httpx.Response(200, text="{}", headers={"content-type": "text/html"})], "içerik türü"),
])
def test_http_failures(tmp_path, responses, match):
    queue = list(responses)
    with pytest.raises(SourceError, match=match):
        run_normals(tmp_path, lambda request: queue.pop(0))


def test_server_error_retried_once(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(503) if len(calls) == 1 else NormalsMock()(request)
    assert len(run_normals(tmp_path, handler).records) == 168 and len(calls) == 2


def test_response_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(cn, "MAX_BYTES", 1000)
    with pytest.raises(SourceError, match="boyut sınırını"):
        run_normals(tmp_path)


# --- NCEI normals ------------------------------------------------------------------------------------

def test_normals_missing_variables_are_null_and_flags_are_kept(tmp_path):
    mock = NormalsMock()
    result = run_normals(tmp_path, mock)
    request, = mock.seen
    assert request.url.path == "/access/services/data/v1" and not request.url.path.startswith("/data")   # robots.txt: /data* disallowed
    params = request.url.params
    assert params["dataset"] == "normals-monthly-1991-2020" and params["stations"] == f"{COASTAL},{INLAND}"
    assert params["dataTypes"].split(",") == list(cn.ELEMENTS) and params["includeAttributes"] == "true"
    records = by_key(result.records, "station_id", "month", "element")
    assert len(records) == 2 * 12 * 7
    # A variable the source does not publish for a station is NULL, not zero.
    inland_hot = [records[(INLAND, m, "MLY-TMAX-AVGNDS-GRTH090")] for m in range(1, 13)]
    assert {(r["value"], r["completeness_flag"], r["measurement_flag"], r["years"]) for r in inland_hot} == {(None, None, None, None)}
    assert records[(COASTAL, 2, "MLY-PRCP-AVGNDS-GE010HI")] | {} == {
        "station_id": COASTAL, "month": 2, "element": "MLY-PRCP-AVGNDS-GE010HI", "value": None, "unit": "gün",
        "completeness_flag": None, "measurement_flag": None, "years": None}
    sentinel = records[(COASTAL, 3, "MLY-TMIN-AVGNDS-LSTH032")]
    assert sentinel["value"] is None and sentinel["completeness_flag"] == "R" and sentinel["years"] == 19
    # Flags and year counts are stored exactly as published.
    assert records[(COASTAL, 7, "MLY-TMAX-NORMAL")] | {} == {
        "station_id": COASTAL, "month": 7, "element": "MLY-TMAX-NORMAL", "value": 90.0, "unit": "°F",
        "completeness_flag": "R", "measurement_flag": None, "years": 19}
    assert records[(COASTAL, 11, "MLY-TMAX-NORMAL")]["completeness_flag"] == "S"
    assert records[(COASTAL, 11, "MLY-TMAX-AVGNDS-GRTH090")]["measurement_flag"] == "X"
    assert records[(COASTAL, 1, "MLY-PRCP-AVGNDS-GE010HI")]["completeness_flag"] == "P"
    assert records[(COASTAL, 1, "MLY-PRCP-NORMAL")]["unit"] == "inç" and records[(COASTAL, 1, "MLY-PRCP-NORMAL")]["years"] == 22
    assert records[(INLAND, 7, "MLY-TMAX-NORMAL")]["value"] == 92.0
    assert result.metadata["missing_values"] == 14 and result.metadata["sentinel_values"] == 1
    stations = by_key(result.related["stations"], "station_id")
    assert stations[(COASTAL,)] == {"station_id": COASTAL, "station_key": "coastal", "role": "kıyı referansı",
                                   "label": "Destin–Fort Walton Beach Havalimanı", "source_name": "SYNTHETIC COASTAL TEST, FL US",
                                   "latitude": 30.4, "longitude": -86.4717, "elevation_m": 6.7, "distance_km": 20.5}
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    response, = manifest["responses"]
    assert response["raw_sha256"] == hashlib.sha256((tmp_path / response["raw_file"]).read_bytes()).hexdigest()


def without(rows, predicate):
    return [row for row in rows if not predicate(row)]


@pytest.mark.parametrize("rows,match", [
    (without(NORMALS, lambda r: r["STATION"] == INLAND), "normal verisi dönmedi"),
    (without(NORMALS, lambda r: r["STATION"] == COASTAL and r["DATE"] == "12"), "12 ayın"),
    (NORMALS + [r for r in NORMALS if r["STATION"] == COASTAL and r["DATE"] == "01"], "yinelenmiş"),
    ([{**r, "MLY-TMAX-NORMAL": "warm"} if r["DATE"] == "05" else r for r in NORMALS], "okunamadı"),
    ([{**r, "DATE": "13"} if r["DATE"] == "12" else r for r in NORMALS], "geçersiz"),
    ([{k: v for k, v in r.items() if k != "STATION"} for r in NORMALS], "istasyon kimliği"),
])
def test_normals_structure_errors(tmp_path, rows, match):
    with pytest.raises(SourceError, match=match):
        run_normals(tmp_path, NormalsMock(rows))


def test_normals_response_must_be_a_json_list(tmp_path):
    for content, match in ((b"{}", "liste"), (b"not json", "JSON")):
        with pytest.raises(SourceError, match=match):
            run_normals(tmp_path, lambda request: httpx.Response(200, content=content, headers={"content-type": "application/json"}))


def test_normals_without_configured_station_fails_without_http(tmp_path):
    mock = NormalsMock()
    with pytest.raises(SourceError, match="istasyonu yapılandırılmamış"):
        run_normals(tmp_path, mock, stations=(BUOY,))
    assert mock.seen == []


# --- NDBC sea water temperature ------------------------------------------------------------------------

def test_water_missing_markers_monthly_means_and_20_day_rule(tmp_path):
    mock = BuoyMock()
    result = run_water(tmp_path, mock)
    assert mock.seen == [("test1", 2010), ("test1", 2011), ("test1", 2012)]
    assert [(r["year"], r["month"], r["mean_c"], r["observation_count"], r["day_count"]) for r in result.records] == [
        (2010, 1, 16.0, 20, 20), (2010, 2, 18.0, 19, 19), (2011, 1, 18.0, 40, 20), (2011, 2, 19.0, 20, 20)]
    # 999.0 and 99.0 are missing markers: two on 5 January 2010 and the only reading of 20 February 2010.
    assert result.metadata["valid_observations"] == 99 and result.metadata["missing_observations"] == 3
    station, = result.related["stations"]
    assert station["years_found"] == [2010, 2011] and station["years_missing"] == [2012]
    assert (station["first_year"], station["last_year"]) == (2010, 2012)
    summary = {row["month"]: row for row in wt.monthly_summary(result.records)}
    # January: both years have 20 days with data; February 2010 has 19 and stays out of the multi-year mean.
    assert summary[1] == {"month": 1, "mean_c": 17.0, "years_used": 2, "first_year": 2010, "last_year": 2011, "excluded_year_months": 0}
    assert summary[2] == {"month": 2, "mean_c": 19.0, "years_used": 1, "first_year": 2011, "last_year": 2011, "excluded_year_months": 1}
    assert summary[3] == {"month": 3, "mean_c": None, "years_used": 0, "first_year": None, "last_year": None, "excluded_year_months": 0}
    assert wt.monthly_summary(result.records, min_days=19)[1]["mean_c"] == pytest.approx((18.0 + 19.0) / 2)


def test_water_raw_year_files_kept_with_sha256_and_404_recorded(tmp_path):
    run_water(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert [(r["note"], r["status"]) for r in manifest["responses"]] == [("TEST1 2010", 200), ("TEST1 2011", 200), ("TEST1 2012", 404)]
    for response in manifest["responses"]:
        body = (tmp_path / response["raw_file"]).read_bytes()
        assert response["raw_sha256"] == hashlib.sha256(body).hexdigest()
    assert gzip.decompress((tmp_path / manifest["responses"][0]["raw_file"]).read_bytes()) == (FIXTURES / "ndbc-2010.txt").read_bytes()


def test_water_every_year_missing_fails(tmp_path):
    with pytest.raises(SourceError, match="hiç yıllık dosya"):
        run_water(tmp_path, BuoyMock(files={}))


@pytest.mark.parametrize("text,match", [
    ("YYYY MM DD hh mm ATMP\n2010 01 01 00 00 20.0\n", "WTMP sütunu"),
    ("YYYY MM DD hh mm ATMP WTMP\n2010 01 01 00 00 20.0\n", "sütun sayısında"),
    ("YYYY MM DD hh mm ATMP WTMP\n2010 13 01 00 00 20.0 18.0\n", "geçersiz tarih"),
    ("YYYY MM DD hh mm ATMP WTMP\n2010 01 01 00 00 20.0 warm\n", "okunamadı"),
])
def test_water_file_format_errors(tmp_path, text, match):
    with pytest.raises(SourceError, match=match):
        run_water(tmp_path, BuoyMock(files={2010: gzip.compress(text.encode())}), last_year=2010)


def test_water_file_must_be_gzip(tmp_path):
    with pytest.raises(SourceError, match="gzip"):
        run_water(tmp_path, BuoyMock(files={2010: b"plain text"}), last_year=2010)


@pytest.mark.parametrize("stations,match", [((), "istasyonu yapılandırılmamış"), (({**BUOY, "first_year": None},), "ilk yıl")])
def test_water_configuration_errors_fail_without_http(tmp_path, stations, match):
    mock = BuoyMock()
    with pytest.raises(SourceError, match=match):
        run_water(tmp_path, mock, stations=stations)
    assert mock.seen == []


# --- Cancel ----------------------------------------------------------------------------------------------

def test_cancel_before_start_and_between_requests(tmp_path):
    with pytest.raises(CollectionCanceled):
        run_normals(tmp_path, canceled=lambda: True)
    with pytest.raises(CollectionCanceled):
        run_storms(tmp_path, canceled=lambda: True)
    mock = BuoyMock()
    with pytest.raises(CollectionCanceled):
        run_water(tmp_path, mock, canceled=lambda: len(mock.seen) >= 2)
    assert len(mock.seen) == 2
    storms = StormMock()
    with pytest.raises(CollectionCanceled):
        run_storms(tmp_path, storms, canceled=lambda: len(storms.seen) >= 1)
    assert storms.seen == ["/data/"]


# --- Database, API and atomic publication ------------------------------------------------------------------

def test_fresh_database_has_climate_configuration_and_sources(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        context = db.context("30a")
        assert [(s["station_key"], s["kind"], s["station_id"], s["distance_km"], s["first_year"]) for s in context.climate_stations] == [
            ("coastal", "normals", COASTAL, 20.5, None), ("inland", "normals", INLAND, 44.1, None), ("water", "water_temperature", "PCBF1", 12.9, 2005)]
        assert {s["distance_basis"] for s in context.climate_stations} == {thirty_a.CLIMATE_DISTANCE_BASIS}
        corridor = context.storm_corridor
        assert {k: corridor[k] for k in thirty_a.STORM_CORRIDOR if k != "radii_nmi"} == {
            k: v for k, v in thirty_a.STORM_CORRIDOR.items() if k != "radii_nmi"}
        assert corridor["radii_nmi"] == [50, 100]
        sources = {s["url"]: s for s in client.get("/api/sources").json()}
        expected = {cn.SOURCE_URL: ("API", cn.ClimateNormalsConnector), wt.SOURCE_URL: ("Dosya", wt.WaterTemperatureConnector),
                    sp.SOURCE_URL: ("Dosya", sp.StormProximityConnector)}
        for url, (method, connector) in expected.items():
            source = sources[url]
            assert (source["method"], source["category"], source["cadence"], source["region"], source["enabled"]) == (method, "Hava", "Haftalık", "Tüm 30A", True)
            assert source["connector"] == {"name": connector.name, "version": connector.version, "method": method}
            assert not connector.diff_enabled and connector.diff_reason
        bootstrap = client.get("/api/bootstrap").json()
        assert bootstrap["climate_runs"] == []
        assert bootstrap["climate_connectors"] == {"normals": "ncei-climate-normals", "water": "ndbc-water-temperature", "storms": "hurdat2-storm-proximity"}
        assert client.get("/api/climate").json() == {"config": {"stations": [dict(s) for s in context.climate_stations],
                                                              "corridor": dict(corridor)}, "normals": None, "water": None, "storms": None}


def test_api_runs_the_three_collectors_and_serves_latest_snapshots(tmp_path, monkeypatch):
    water = BuoyMock()
    install_all(monkeypatch, water=water)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        use_test_corridor(db)
        jobs = {key: start(client, url) for key, url in CLIMATE_URLS.items()}
        assert {key: job["status"] for key, job in jobs.items()} == {"normals": "done", "water": "done", "storms": "done"}, jobs
        assert {water_station for water_station, _ in water.seen} == {"pcbf1"}
        assert [year for _, year in water.seen] == list(range(2005, 2013))
        climate = client.get("/api/climate").json()
        normals, buoy, storms = climate["normals"], climate["water"], climate["storms"]
        assert normals["run"]["id"] == jobs["normals"]["id"] and len(normals["values"]) == 168
        assert [s["station_id"] for s in normals["stations"]] == [COASTAL, INLAND]            # ordered by distance
        assert [e["code"] for e in normals["elements"]] == list(cn.ELEMENTS)
        assert normals["run"]["metadata"]["missing_values"] == 14
        assert buoy["stations"][0]["years_found"] == [2010, 2011] and buoy["stations"][0]["years_missing"] == [2005, 2006, 2007, 2008, 2009, 2012]
        assert len(buoy["months"]) == 4 and buoy["min_days"] == 20
        assert buoy["summary"]["PCBF1"][0] == {"month": 1, "mean_c": 17.0, "years_used": 2, "first_year": 2010, "last_year": 2011, "excluded_year_months": 0}
        assert storms["corridor"]["label"] == "Test corridor" and storms["corridor"]["hurdat_file"] == HURDAT_FILE
        assert storms["corridor"]["radii_nmi"] == [50, 100] and storms["corridor"]["storm_count"] == 7
        assert len(storms["passages"]) == 9 and storms["class_labels"]["MH"] == "büyük kasırga"
        assert storms["run"]["record_count"] == 9 and storms["run"]["metadata"]["total_count"] == 7
        assert [run["id"] for run in client.get("/api/climate-runs").json()] == [jobs[k]["id"] for k in ("storms", "water", "normals")]
        assert [run["id"] for run in client.get("/api/bootstrap").json()["climate_runs"]] == [jobs[k]["id"] for k in ("storms", "water", "normals")]
        for key, job in jobs.items():
            run = db.source_run(job["id"])
            raw = client.get(f"/api/climate-runs/{job['id']}/raw")
            assert raw.status_code == 200 and hashlib.sha256(raw.content).hexdigest() == run["raw_sha256"]
            connector = DEFAULT_REGISTRY.by_name(run["connector_name"])
            assert db.run_diff(job["id"]) == {"available": False, "reason": connector.diff_reason}
        assert client.get("/api/climate-runs/missing/raw").status_code == 404
        # A second storm run becomes the latest snapshot; the first stays readable as history.
        second = start(client, sp.SOURCE_URL)
        assert client.get("/api/climate").json()["storms"]["run"]["id"] == second["id"]
        with db.connect() as con:
            assert con.execute("SELECT COUNT(*) FROM storm_passages").fetchone()[0] == 18
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("key,module,connector,tables", [
    ("normals", cn, cn.ClimateNormalsConnector, ("climate_normal_stations", "climate_normal_values")),
    ("water", wt, wt.WaterTemperatureConnector, ("water_temperature_stations", "water_temperature_months")),
    ("storms", sp, sp.StormProximityConnector, ("storm_corridor_snapshots", "storm_passages")),
])
def test_failure_after_insert_rolls_back_and_keeps_previous_snapshot(tmp_path, monkeypatch, key, module, connector, tables):
    install_all(monkeypatch)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        use_test_corridor(db)
        good = start(client, CLIMATE_URLS[key]); assert good["status"] == "done"
        before = client.get("/api/climate").json()[key]
        original = connector.store_records
        def fail(self, con, run_id, records, related=None):
            original(self, con, run_id, records, related); raise RuntimeError("synthetic after insert")
        monkeypatch.setattr(connector, "store_records", fail)
        failed = start(client, CLIMATE_URLS[key]); assert failed["status"] == "failed"
        assert client.get("/api/climate").json()[key] == before
        assert [run["id"] for run in client.get("/api/climate-runs").json()] == [good["id"]]
        assert client.get(f"/api/climate-runs/{failed['id']}/raw").status_code == 404
        with db.connect() as con:
            for table in tables:
                assert con.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id=?", (failed["id"],)).fetchone()[0] == 0
                assert con.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id=?", (good["id"],)).fetchone()[0] > 0


def test_cancel_job_through_api_publishes_nothing(tmp_path, monkeypatch):
    release, entered = threading.Event(), threading.Event()
    def before(count):
        if count == 2:
            entered.set(); release.wait(3)
    install_all(monkeypatch, water=BuoyMock(before=before))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        source = next(s for s in client.get("/api/sources").json() if s["url"] == wt.SOURCE_URL)
        identifier = client.post("/api/jobs", json={"kind": "source_collection", "source_id": source["id"]}).json()["id"]
        try:
            assert entered.wait(3)
            assert client.post(f"/api/jobs/{identifier}/cancel").json()["status"] == "canceled"
        finally:
            release.set()
        assert finished(client, identifier)["status"] == "canceled"
        assert client.get("/api/climate").json()["water"] is None and client.get("/api/climate-runs").json() == []
        with client.app.state.db.connect() as con:
            assert con.execute("SELECT COUNT(*) FROM water_temperature_months").fetchone()[0] == 0


def test_schema_constraints(tmp_path):
    db = Database(tmp_path / "studio.sqlite3"); db.initialize()
    with db.connect() as con:
        for statement in (
            "UPDATE destination_climate_stations SET kind='other'",
            "UPDATE destination_climate_stations SET latitude=95",
            "UPDATE destination_storm_corridors SET radii_nmi='{}'",
            "UPDATE destination_storm_corridors SET radii_nmi='broken'",
            "INSERT INTO destination_climate_stations VALUES ('missing','x','normals','X','X','X',0,0,0,'b',NULL,0,1)",
            "INSERT INTO storm_passages VALUES ('missing','AL012010','A',2010,50,'2010-08-01T00:00Z',8,0,0,40,'TS',NULL)",
            "INSERT INTO water_temperature_months VALUES ('missing','X',2010,1,15,1,1)",
        ):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute(statement)
                if con.execute("PRAGMA foreign_key_check").fetchone():
                    raise sqlite3.IntegrityError("foreign key")


# --- Migration ---------------------------------------------------------------------------------------------

def make_v7(path):
    make_v6(path)
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        con.execute("BEGIN IMMEDIATE"); upgrade_v7(con)


def table_counts(con):
    return {row[0]: con.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_v7_to_v8_migration_adds_tables_configuration_and_sources_with_backup(tmp_path):
    path = tmp_path / "studio.sqlite3"; make_v7(path)
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 7
        tables_before = table_counts(con)
        rows_before = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in tables_before}
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 8
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert table_counts(con) == {**tables_before, **V8_TABLES, "sources": tables_before["sources"] + 3}
        for table, rows in rows_before.items():
            after = con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
            assert after[:len(rows)] == rows, table
        added = con.execute("SELECT name,url,category,region,method,cadence,notes,enabled,version,destination_id,scope_region_id "
                            "FROM sources ORDER BY rowid").fetchall()[len(rows_before["sources"]):]
        assert added == [(name, url, category, "Tüm 30A", method, "Haftalık", notes, 1, 1, "30a", None)
                         for name, url, category, notes, method in thirty_a.SEEDS[-3:]]
        stations = con.execute("SELECT station_key,station_id,distance_km,first_year,sort_order,enabled FROM destination_climate_stations "
                               "WHERE destination_id='30a' ORDER BY sort_order").fetchall()
        assert stations == [("coastal", COASTAL, 20.5, None, 0, 1), ("inland", INLAND, 44.1, None, 1, 1), ("water", "PCBF1", 12.9, 2005, 2, 1)]
        assert con.execute("SELECT radii_nmi,west_reference FROM destination_storm_corridors").fetchall() == [
            ("[50, 100]", "Stallworth Preserve (5c81ab02f836f9166348e96c)")]
    backup, = (tmp_path / "backups").glob("*-v7-*.sqlite3")
    with sqlite3.connect(backup) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 7
        assert {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in rows_before} == rows_before
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert table_counts(con)["sources"] == tables_before["sources"] + 3
        assert table_counts(con)["destination_climate_stations"] == 3
    assert len(list((tmp_path / "backups").glob("*.sqlite3"))) == 1


def test_v7_to_v8_failure_rolls_back_everything(tmp_path, monkeypatch):
    from studio import database
    path = tmp_path / "studio.sqlite3"; make_v7(path)
    with sqlite3.connect(path) as con:
        before = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in table_counts(con)}
    original = database.upgrade_v8
    def fail(con): original(con); raise RuntimeError("after all DDL, configuration and source inserts")
    with monkeypatch.context() as m:
        m.setattr(database, "upgrade_v8", fail)
        with pytest.raises(RuntimeError):
            Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 7
        assert table_counts(con).keys() == before.keys()
        assert {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in before} == before
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 8
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("url,enabled", [(cn.SOURCE_URL, 0), ("https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals/", 1)])
def test_v8_never_duplicates_an_existing_climate_source(tmp_path, url, enabled):
    path = tmp_path / "studio.sqlite3"; make_v7(path)
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "mine", "My normals", url, "Hava", "Tüm 30A", "Belirlenecek", "Aylık", "My notes", enabled, 3, "old", "old", "30a", None))
        before = con.execute("SELECT * FROM sources WHERE id='mine'").fetchone()
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT * FROM sources WHERE url LIKE 'https://www.ncei.noaa.gov/%'").fetchall() == [before]
        assert con.execute("SELECT COUNT(*) FROM sources WHERE url IN (?,?)", (wt.SOURCE_URL, sp.SOURCE_URL)).fetchone()[0] == 2


def test_seed_never_overwrites_edited_configuration(tmp_path):
    db = Database(tmp_path / "studio.sqlite3"); db.initialize()
    with db.connect() as con:
        con.execute("UPDATE destination_climate_stations SET enabled=0 WHERE station_key='inland'")
        con.execute("UPDATE destination_storm_corridors SET radii_nmi='[75]'")
        before = (con.execute("SELECT * FROM destination_climate_stations ORDER BY rowid").fetchall(),
                  con.execute("SELECT * FROM destination_storm_corridors").fetchall(), con.execute("SELECT * FROM sources ORDER BY rowid").fetchall())
        seed_destination_climate(con, thirty_a)
        after = (con.execute("SELECT * FROM destination_climate_stations ORDER BY rowid").fetchall(),
                 con.execute("SELECT * FROM destination_storm_corridors").fetchall(), con.execute("SELECT * FROM sources ORDER BY rowid").fetchall())
        assert [list(map(tuple, part)) for part in after] == [list(map(tuple, part)) for part in before]
    context = db.context("30a")
    assert [s["station_key"] for s in context.climate_stations] == ["coastal", "water"] and context.storm_corridor["radii_nmi"] == [75]


# --- Destination isolation ---------------------------------------------------------------------------------

def add_climate_config(db, identifier="test-coast"):
    with db.connect() as con:
        con.execute("""INSERT INTO destination_climate_stations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                    (identifier, "coastal", "normals", "USW00099999", "Test airport", "kıyı referansı", 1.0, -86.5, 111.2, "test basis", None, 0))
        con.execute("""INSERT INTO destination_climate_stations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                    (identifier, "water", "water_temperature", "TEST1", "Synthetic buoy", "deniz suyu sıcaklığı", 0.1, -86.5, 11.1, "test basis", 2010, 1))
        con.execute("INSERT INTO destination_storm_corridors VALUES (?,?,?,?,?,?,?,?,?,1)",
                    (identifier, "Test corridor", 0.0, -87.0, "west test point", 0.0, -86.0, "east test point", "[100]"))


def test_destination_configuration_never_mixes(tmp_path, monkeypatch):
    rows = NORMALS + [{**row, "STATION": "USW00099999", "NAME": "SYNTHETIC TEST AIRPORT"} for row in NORMALS if row["STATION"] == COASTAL]
    normals, water, storms = NormalsMock(rows), BuoyMock(), StormMock()
    install_all(monkeypatch, normals, water, storms)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        add_destination(db); add_destination(db, "third-coast"); add_climate_config(db)
        assert [s["station_id"] for s in db.context("30a").climate_stations] == [COASTAL, INLAND, "PCBF1"]
        assert [s["station_id"] for s in db.context("test-coast").climate_stations] == ["USW00099999", "TEST1"]
        assert db.context("test-coast").storm_corridor["radii_nmi"] == [100]
        assert db.context("third-coast").climate_stations == () and db.context("third-coast").storm_corridor is None
        for key, url in CLIMATE_URLS.items():
            created = client.post("/api/sources", json=payload(destination_id="test-coast", url=url, category="Hava"))
            assert created.status_code in (200, 201), created.text
            assert start(client, url, "test-coast")["status"] == "done"
        assert [r.url.params["stations"] for r in normals.seen] == ["USW00099999"]
        assert {station for station, _ in water.seen} == {"test1"}
        climate = client.get("/api/climate?destination_id=test-coast").json()
        assert [s["station_id"] for s in climate["normals"]["stations"]] == ["USW00099999"]
        assert climate["storms"]["corridor"]["radii_nmi"] == [100] and {p["radius_nmi"] for p in climate["storms"]["passages"]} == {100}
        assert client.get("/api/climate").json() | {"config": None} == {"config": None, "normals": None, "water": None, "storms": None}
        assert client.get("/api/climate-runs").json() == []
        assert len(client.get("/api/climate-runs?destination_id=test-coast").json()) == 3
        # A destination without climate configuration fails before any request.
        seen = (len(normals.seen), len(water.seen), len(storms.seen))
        for url, match in ((cn.SOURCE_URL, "istasyonu yapılandırılmamış"), (wt.SOURCE_URL, "istasyonu yapılandırılmamış"),
                           (sp.SOURCE_URL, "koridoru yapılandırılmamış")):
            client.post("/api/sources", json=payload(destination_id="third-coast", url=url, category="Hava"))
            job = start(client, url, "third-coast")
            assert job["status"] == "failed" and match in job["message"]
        assert (len(normals.seen), len(water.seen), len(storms.seen)) == seen
        assert client.get("/api/climate?destination_id=missing").status_code == 404
        assert client.get("/api/climate-runs?destination_id=missing").status_code == 404
