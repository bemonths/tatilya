"""GÖREV-10 daily-need points from OpenStreetMap (Overpass API), the supermarket chains' cross-check and the great-circle distances
of lodging listings per neighborhood.

Synthetic responses through httpx.MockTransport only; suite-wide no_real_http prevents internet access.
"""
import csv
import json
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.destinations import thirty_a
from studio.sources import climate_http
from studio.sources import daily_needs as dn
from studio.sources.base import SourceError
from studio.sources.geo import distance_km
from tests.test_beaches import HEADERS
from tests.test_lodging import BookDirectMock, fast, inventory, lodging, start  # noqa: F401  (fast: autouse fixture)
from tests.test_monthly_windows import use

CATEGORIES = [{"category_key": key, "label": label, "filters": filters} for key, label, filters in thirty_a.DAILY_NEEDS_CATEGORIES]
AREA = {k: thirty_a.DAILY_NEEDS_AREA[k] for k in ("south", "west", "north", "east")}
REAL_COLLECT = dn.collect


def element(kind, identifier, lat, lon, **tags):
    position = {"lat": lat, "lon": lon} if kind == "node" else {"center": {"lat": lat, "lon": lon}}
    return {"type": kind, "id": identifier, **position, "tags": tags}


ANSWER = {"osm3s": {"timestamp_osm_base": "2026-10-09T11:34:06Z"}, "elements": [
    element("way", 11, 30.3010, -86.1010, shop="supermarket", name="Publix", brand="Publix", **{"addr:housenumber": "1", "addr:street": "Main St",
                                                                                                "addr:city": "Santa Rosa Beach"}),
    element("node", 12, 30.3000, -86.1200, shop="convenience", name="Corner Store"),
    element("node", 13, 30.3200, -86.1000, amenity="pharmacy", name="Pharmacy"),
    element("node", 14, 30.3500, -86.1000, amenity="clinic", emergency="yes", name="Walk-in ER"),
    element("node", 15, 30.3500, -86.2000, amenity="clinic", name="Dentist"),                       # a clinic without emergency=yes
    element("node", 16, 30.3001, -86.1001, shop="bicycle", **{"service:bicycle:rental": "yes"}, name="Bike Shop"),
    element("node", 12, 30.3000, -86.1200, shop="convenience", name="Corner Store"),                 # the same element twice
    element("way", 17, 30.3100, -86.1100, shop="supermarket", name="No center"),
    element("node", 18, 30.3100, -86.1100, amenity="cafe", name="Cafe")]}
ANSWER["elements"][7].pop("center")


def answer_mock(body=None, seen=None):
    def handler(request):
        if seen is not None:
            seen.append(request)
        assert request.url.host == dn.OVERPASS_HOST and request.url.path == "/api/interpreter"
        return httpx.Response(200, content=json.dumps(body or ANSWER).encode(), headers={"content-type": "application/json"})
    return handler


def chain_file(tmp_path, rows):
    path = tmp_path / "zincir.csv"
    fields = ["zincir", "magaza", "adres", "enlem", "boylam", "magaza_url", "kontrol_tarihi", "durum", "osm_id", "not"]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    return path


@pytest.fixture(autouse=True)
def no_gap(monkeypatch):
    monkeypatch.setattr(climate_http, "REQUEST_GAP", 0)


def test_overpass_query_asks_every_tag_set_inside_the_area_with_centers():
    query = dn.overpass_query(AREA, CATEGORIES)
    assert query.startswith("[out:json][timeout:90];(") and query.endswith(");out center tags;")
    assert 'nwr["shop"="supermarket"](30.2,-86.4,30.45,-85.84);' in query
    assert 'nwr["amenity"="clinic"]["emergency"="yes"](30.2,-86.4,30.45,-85.84);' in query
    assert query.count("nwr[") == sum(len(c["filters"]) for c in CATEGORIES)


def test_points_by_category_with_way_centers_and_nothing_outside_the_categories():
    points, stamp = dn.parse(json.dumps(ANSWER), CATEGORIES)
    assert stamp == "2026-10-09T11:34:06Z"
    assert [(p["point_id"], p["category_key"]) for p in points] == [("way/11", "supermarket"), ("node/12", "convenience"), ("node/13", "pharmacy"),
                                                                     ("node/14", "urgent_care"), ("node/16", "bike_rental")]
    publix = points[0]
    assert (publix["latitude"], publix["source"], publix["address"]) == (30.301, "openstreetmap", "1 Main St, Santa Rosa Beach")
    assert publix["source_url"] == "https://www.openstreetmap.org/way/11" and publix["tags"]["brand"] == "Publix"
    with pytest.raises(SourceError, match="beklenen JSON"):
        dn.parse("<html>busy</html>", CATEGORIES)
    with pytest.raises(SourceError, match="öğe listesi yok"):
        dn.parse(json.dumps({"elements": {}}), CATEGORIES)


def test_chain_cross_check_matches_adds_and_reports():
    points, _ = dn.parse(json.dumps(ANSWER), CATEGORIES)
    rows = [{"zincir": "Publix", "magaza": "Publix Santa Rosa", "enlem": "30.3015", "boylam": "-86.1015", "durum": "açık"},          # 60 m: same
            {"zincir": "Walmart", "magaza": "Walmart Supercenter", "enlem": "30.40", "boylam": "-86.00", "durum": "açık",
             "adres": "1 Walmart Way", "magaza_url": "https://walmart.example/1", "kontrol_tarihi": "2026-10-09"},
            {"zincir": "Aldi", "magaza": "Aldi", "enlem": "30.3010", "boylam": "-86.1010", "durum": "kapalı", "osm_id": "way/11",
             "kontrol_tarihi": "2026-10-09"},
            {"zincir": "Whole Foods", "magaza": "", "durum": "bölgede mağaza yok"},
            {"zincir": "Winn-Dixie", "magaza": "", "durum": "okunamadı", "not": "403"}]
    merged, checks = dn.merge_chain_checks(points, rows)
    assert [c["outcome"] for c in checks] == ["osm_ile_ayni", "eklendi", "osmde_var_zincirde_kapali", "bolgede_yok", "okunamadi"]
    assert checks[0]["osm_point_id"] == "way/11" and checks[2]["osm_point_id"] == "way/11"
    added = merged[-1]
    assert (added["source"], added["category_key"], added["brand"], added["address"]) == ("zincirin kendi sitesi", "supermarket", "Walmart", "1 Walmart Way")
    assert added["point_id"] == "zincir/Walmart/Walmart Supercenter" and added["checked_on"] == "2026-10-09"
    assert merged[0]["note"] == "Aldi sitesinde kapalı görünüyor (2026-10-09)."
    far = [{"zincir": "Publix", "magaza": "Publix far", "enlem": "30.32", "boylam": "-86.1010", "durum": "açık"}]   # 2 km away: another store
    assert dn.merge_chain_checks(dn.parse(json.dumps(ANSWER), CATEGORIES)[0], far)[1][0]["outcome"] == "eklendi"
    with pytest.raises(SourceError, match="koordinatsız açık mağaza"):
        dn.merge_chain_checks([], [{"zincir": "Target", "magaza": "Target", "durum": "açık"}])


def test_unknown_chain_status_fails(tmp_path):
    with pytest.raises(SourceError, match="bilinmeyen durum"):
        dn.read_chain_checks(chain_file(tmp_path, [{"zincir": "Publix", "magaza": "x", "durum": "belki"}]))
    assert dn.read_chain_checks(tmp_path / "yok.csv") == []


def test_collect_needs_area_and_categories_and_keeps_one_raw_answer(tmp_path):
    with pytest.raises(SourceError, match="yapılandırılmamış"):
        dn.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=None)
    seen = []
    config = {"area": AREA, "categories": CATEGORIES, "chain_checks": None}
    with httpx.Client(transport=httpx.MockTransport(answer_mock(seen=seen))) as client:
        result = dn.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config, client=client, today=date(2026, 10, 9))
    assert len(seen) == 1 and seen[0].url.params["data"] == dn.overpass_query(AREA, CATEGORIES)
    assert result.metadata["point_counts"] == {"supermarket": 1, "convenience": 1, "pharmacy": 1, "urgent_care": 1, "bike_rental": 1}
    assert result.metadata["attribution"] == "© OpenStreetMap katkıcıları, ODbL" and result.metadata["request_count"] == 1
    assert result.related["snapshot"]["queried_on"] == "2026-10-09" and result.related["snapshot"]["element_count"] == 5
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["responses"]) == 1 and len(manifest["responses"][0]["raw_sha256"]) == 64


def test_api_summary_gives_great_circle_distances_per_neighborhood(tmp_path, monkeypatch):
    data = inventory()
    data[62708] = [lodging(3001, "Dune Allen condo", 62708, latitude="30.3000", longitude="-86.1000"),
                   lodging(3002, "No coordinates", 62708, latitude=None, longitude=None)]
    checks = chain_file(tmp_path, [{"zincir": "Target", "magaza": "Target Test", "enlem": "30.3000", "boylam": "-86.1300", "durum": "açık",
                                    "kontrol_tarihi": "2026-10-09"}])
    def collect(path, progress, canceled, *, config, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(answer_mock())) as client:
            return REAL_COLLECT(path, progress, canceled, config={**config, "chain_checks": checks}, client=client, today=date(2026, 10, 9))
    monkeypatch.setattr(dn, "collect", collect)
    with TestClient(create_app(tmp_path / "data"), headers=HEADERS) as client:
        use(monkeypatch, BookDirectMock(data), date(2026, 10, 7))
        assert start(client)["status"] == "done"
        job = start(client, url=dn.SOURCE_URL)
        assert job["status"] == "done", job["message"]
        assert [r["id"] for r in client.get("/api/daily-needs-runs").json()] == [job["id"]]
        assert client.get("/api/bootstrap").json()["daily_needs_runs"][0]["id"] == job["id"]
        summary = client.get(f"/api/daily-needs-runs/{job['id']}").json()
        assert summary["attribution"] == "© OpenStreetMap katkıcıları, ODbL" and "kuş uçuşu" in summary["note"]
        assert summary["snapshot"]["osm_timestamp"] == "2026-10-09T11:34:06Z" and summary["missing_coordinates"] == 1
        assert {p["source"] for p in summary["points"]} == {"openstreetmap", "zincirin kendi sitesi"}
        assert summary["checks"][0]["outcome"] == "eklendi" and summary["beach_count"] == 0
        dune = next(r for r in summary["regions"] if r["region_id"] == "dune-allen")
        assert (dune["listing_count"], dune["measured_count"], dune["restaurant_count"]) == (2, 1, None)
        nearest = distance_km(30.3, -86.1, 30.3001, -86.1001)
        assert dune["measures"]["bike_rental"] == {"median_km": round(nearest, 3), "median_mi": round(nearest / dn.MILE_KM, 2),
                                                   "within_1mi_share": 1.0, "count": 1}
        market = distance_km(30.3, -86.1, 30.301, -86.101)                                     # Publix is nearer than the added Target
        assert dune["measures"]["supermarket"]["median_km"] == round(market, 3)
        assert dune["measures"]["urgent_care"]["within_1mi_share"] == 0.0                    # 5.5 km away
        assert dune["measures"]["beach"] == {"median_km": None, "median_mi": None, "within_1mi_share": None, "count": 0}
        raw = client.get(f"/api/daily-needs-runs/{job['id']}/raw")
        assert raw.status_code == 200 and json.loads(raw.content)["connector"] == dn.CONNECTOR_VERSION
        assert client.get("/api/daily-needs-runs/missing").status_code == 404
        with client.app.state.db.connect() as con:
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
            assert con.execute("SELECT COUNT(*) FROM poi_points WHERE run_id=?", (job["id"],)).fetchone()[0] == 6
