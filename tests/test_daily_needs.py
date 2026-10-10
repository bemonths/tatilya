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

CATEGORIES = [{"category_key": key, "label": label, "filters": filters, **options} for key, label, filters, options in thirty_a.DAILY_NEEDS_CATEGORIES]
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
    element("node", 18, 30.3100, -86.1100, amenity="cafe", name="Cafe"),
    element("way", 19, 30.3050, -86.1050, shop="supermarket", name="Modica Market"),                 # no big chain: local market
    element("node", 20, 30.3600, -86.1100, healthcare="urgent_care", name="Urgent Care 30A")]}
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
    assert query.count("nwr[") == len({json.dumps(f, sort_keys=True) for c in CATEGORIES for f in c["filters"]})   # shared tag sets once
    assert query.count('nwr["shop"="supermarket"]') == 1


def test_points_by_category_with_way_centers_and_nothing_outside_the_categories():
    points, stamp = dn.parse(json.dumps(ANSWER), CATEGORIES)
    assert stamp == "2026-10-09T11:34:06Z"
    assert [(p["point_id"], p["category_key"]) for p in points] == [("way/11", "big_supermarket"), ("node/12", "convenience"), ("node/13", "pharmacy"),
                                                                     ("node/14", "emergency"), ("node/16", "bike_rental"), ("way/19", "local_market"),
                                                                     ("node/20", "urgent_care")]
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
    merged, checks = dn.merge_chain_checks(points, rows, CATEGORIES)
    assert [c["outcome"] for c in checks] == ["osm_ile_ayni", "eklendi", "osmde_var_zincirde_kapali", "bolgede_yok", "okunamadi"]
    assert checks[0]["osm_point_id"] == "way/11" and checks[2]["osm_point_id"] == "way/11"
    added = merged[-1]
    assert (added["source"], added["category_key"], added["brand"], added["address"]) == ("zincirin kendi sitesi", "big_supermarket", "Walmart", "1 Walmart Way")
    assert added["point_id"] == "zincir/Walmart/Walmart Supercenter" and added["checked_on"] == "2026-10-09"
    assert merged[0]["note"] == "Aldi sitesinde kapalı görünüyor (2026-10-09)."
    far = [{"zincir": "Publix", "magaza": "Publix far", "enlem": "30.32", "boylam": "-86.1010", "durum": "açık"}]   # 2 km away: another store
    assert dn.merge_chain_checks(dn.parse(json.dumps(ANSWER), CATEGORIES)[0], far, CATEGORIES)[1][0]["outcome"] == "eklendi"
    with pytest.raises(SourceError, match="koordinatsız açık yer"):
        dn.merge_chain_checks([], [{"zincir": "Target", "magaza": "Target", "durum": "açık"}], CATEGORIES)


def test_big_chains_are_matched_by_whole_words_of_brand_name_or_operator():
    brands = thirty_a.BIG_SUPERMARKET_BRANDS
    assert dn.has_brand(brands, None, "Walmart Neighborhood Market") and dn.has_brand(brands, "Winn Dixie") and dn.has_brand(brands, None, "Fresh Market")
    assert dn.has_brand(brands, None, "Trader Joe’s") and dn.has_brand(brands, "ALDI")
    assert not dn.has_brand(brands, None, "Modica Market") and not dn.has_brand(brands, None, "Targeted Foods")


def test_official_sources_confirm_add_and_leave_unconfirmed_points_out_of_verified_categories():
    points, _ = dn.parse(json.dumps(ANSWER), CATEGORIES)
    health = [{"kategori": "emergency", "zincir": "Ascension Sacred Heart", "magaza": "Walk-in ER", "enlem": "30.3501", "boylam": "-86.1001",
               "durum": "açık", "osm_id": "node/14", "kontrol_tarihi": "2026-10-10"},
              {"kategori": "urgent_care", "zincir": "Example Urgent Care", "magaza": "Example Urgent Care Seagrove", "enlem": "30.32",
               "boylam": "-86.13", "durum": "açık", "kontrol_tarihi": "2026-10-10", "koordinat_kaynagi": "sayfanın harita bağlantısı",
               "adres": "1 Example Rd", "magaza_url": "https://care.example/seagrove"}]
    chains = [{"kategori": "big_supermarket", "zincir": "Publix", "magaza": "-", "durum": "okunamadı", "kontrol_tarihi": "2026-10-09"}]
    points, checks, confirmed = dn.merge_reviewed(points, chains, CATEGORIES, "zincirin kendi sitesi")
    points, more, ok = dn.merge_reviewed(points, health, CATEGORIES, "kurumun kendi sitesi")
    points, checks = dn.drop_unconfirmed(points, checks + more, CATEGORIES, confirmed | ok)
    by_id = {p["point_id"]: p for p in points}
    assert "node/14" in by_id and "doğrulandı" in by_id["node/14"]["note"]
    assert "node/20" not in by_id                                          # OpenStreetMap urgent care no official page confirms
    added = by_id["kurum/Example Urgent Care/Example Urgent Care Seagrove"]
    assert (added["source"], added["category_key"], added["note"]) == ("kurumun kendi sitesi", "urgent_care", "Koordinat: sayfanın harita bağlantısı.")
    assert "Publix sitesi bu bilgisayardan doğrulanamadı (2026-10-09)." in by_id["way/11"]["note"]
    outcomes = {(c["category_key"], c["outcome"]) for c in checks}
    assert ("urgent_care", "osm_dogrulanamadi") in outcomes and ("emergency", "osm_ile_ayni") in outcomes and ("urgent_care", "eklendi") in outcomes


def test_unknown_status_or_category_in_a_reviewed_file_fails(tmp_path):
    with pytest.raises(SourceError, match="bilinmeyen durum"):
        dn.read_chain_checks(chain_file(tmp_path, [{"zincir": "Publix", "magaza": "x", "durum": "belki"}]), CATEGORIES)
    assert dn.read_chain_checks(tmp_path / "yok.csv", CATEGORIES) == []
    assert dn.read_chain_checks(chain_file(tmp_path, [{"zincir": "Publix", "magaza": "x", "durum": "açık"}]), CATEGORIES)[0]["kategori"] == "big_supermarket"
    path = tmp_path / "saglik.csv"
    path.write_text("kategori,zincir,magaza,durum\nhospital,X,Y,açık\n", encoding="utf-8")
    with pytest.raises(SourceError, match="yapılandırmada olmayan kategori"):
        dn.read_reviewed(path, CATEGORIES)


def test_collect_needs_area_and_categories_and_keeps_one_raw_answer(tmp_path):
    with pytest.raises(SourceError, match="yapılandırılmamış"):
        dn.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=None)
    seen = []
    config = {"area": AREA, "categories": CATEGORIES, "reviewed_files": []}
    with httpx.Client(transport=httpx.MockTransport(answer_mock(seen=seen))) as client:
        result = dn.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config, client=client, today=date(2026, 10, 9))
    assert len(seen) == 1 and seen[0].url.params["data"] == dn.overpass_query(AREA, CATEGORIES)
    assert result.metadata["point_counts"] == {"big_supermarket": 1, "local_market": 1, "convenience": 1, "pharmacy": 1, "emergency": 0,
                                               "urgent_care": 0, "bike_rental": 1}
    assert result.metadata["osm_unconfirmed"] == 2                     # emergency and urgent care count only when an official page confirms
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
            return REAL_COLLECT(path, progress, canceled, config={**config, "reviewed_files": [(checks, "zincirin kendi sitesi")]}, client=client,
                                today=date(2026, 10, 9))
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
        target = next(c for c in summary["checks"] if c["chain"] == "Target")
        assert (target["outcome"], target["category_key"]) == ("eklendi", "big_supermarket") and summary["beach_count"] == 0
        assert {c["outcome"] for c in summary["checks"] if c["chain"] == "OpenStreetMap"} == {"osm_dogrulanamadi"}
        dune = next(r for r in summary["regions"] if r["region_id"] == "dune-allen")
        assert (dune["listing_count"], dune["measured_count"], dune["restaurant_count"]) == (2, 1, None)
        nearest = distance_km(30.3, -86.1, 30.3001, -86.1001)
        assert dune["measures"]["bike_rental"] == {"median_km": round(nearest, 3), "median_mi": round(nearest / dn.MILE_KM, 2),
                                                   "within_1mi_share": 1.0, "count": 1}
        market = distance_km(30.3, -86.1, 30.301, -86.101)                                     # Publix is nearer than the added Target
        assert dune["measures"]["big_supermarket"]["median_km"] == round(market, 3)
        local = distance_km(30.3, -86.1, 30.305, -86.105)
        assert dune["measures"]["local_market"]["median_km"] == round(local, 3)
        assert dune["measures"]["emergency"]["count"] == 0 and dune["measures"]["urgent_care"]["median_km"] is None   # not confirmed
        assert dune["measures"]["beach"] == {"median_km": None, "median_mi": None, "within_1mi_share": None, "count": 0}
        raw = client.get(f"/api/daily-needs-runs/{job['id']}/raw")
        assert raw.status_code == 200 and json.loads(raw.content)["connector"] == dn.CONNECTOR_VERSION
        assert client.get("/api/daily-needs-runs/missing").status_code == 404
        with client.app.state.db.connect() as con:
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
            assert con.execute("SELECT COUNT(*) FROM poi_points WHERE run_id=?", (job["id"],)).fetchone()[0] == 6    # 5 OpenStreetMap + Target


def make_v13(path):
    """A v13 database with one GÖREV-10 daily-need run: an OpenStreetMap supermarket, a chain-added store and one chain check."""
    import sqlite3
    from studio.migration_v12 import upgrade_v12
    from studio.migration_v13 import upgrade_v13
    from tests.test_agency_v2 import make_v11
    make_v11(path)
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        con.execute("BEGIN IMMEDIATE"); upgrade_v12(con); upgrade_v13(con); con.commit()
        con.execute("INSERT INTO jobs(id,kind,title,status,created_at,destination_id) VALUES ('dn','source_collection','old','done','now','30a')")
        con.execute("""INSERT INTO source_runs(id,job_id,status,connector_name,connector_version,destination_id,metadata)
            VALUES ('dn','dn','done','openstreetmap-daily-needs','openstreetmap-daily-needs/1','30a','{}')""")
        con.execute("""INSERT INTO poi_snapshots VALUES ('dn','{}','[{"category_key": "supermarket"}]','2026-10-09',NULL,1,1,1)""")
        con.execute("""INSERT INTO poi_points VALUES ('dn','way/1','supermarket','Publix','Publix',30.3,-86.1,'openstreetmap','way',1,'{}',NULL,NULL,NULL,NULL)""")
        con.execute("""INSERT INTO poi_points VALUES ('dn','zincir/Target/T','supermarket','T','Target',30.2,-85.9,'zincirin kendi sitesi',NULL,NULL,NULL,
            NULL,'https://t.example',NULL,NULL)""")
        con.execute("""INSERT INTO poi_chain_checks VALUES ('dn','Target','T',NULL,30.2,-85.9,NULL,'2026-10-09','açık',NULL,'eklendi',NULL)""")
        con.commit()


def test_v13_to_v14_splits_categories_keeps_old_runs_and_adds_evidence_packs(tmp_path):
    import sqlite3
    from studio.database import Database
    path = tmp_path / "studio.sqlite3"; make_v13(path)
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 13
        old_points = con.execute("SELECT * FROM poi_points ORDER BY rowid").fetchall()
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        assert con.execute("PRAGMA user_version").fetchone()[0] == 16
        assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert [tuple(r) for r in con.execute("SELECT * FROM poi_points ORDER BY rowid")] == [tuple(r) for r in old_points]
        check = dict(con.execute("SELECT * FROM poi_chain_checks").fetchone())
        assert (check["chain"], check["outcome"], check["category_key"]) == ("Target", "eklendi", "supermarket")   # the old category kept
        categories = {r["category_key"]: dict(r) for r in con.execute("SELECT * FROM destination_poi_categories WHERE destination_id='30a' ORDER BY sort_order")}
        assert list(categories) == [key for key, *_ in thirty_a.DAILY_NEEDS_CATEGORIES]
        assert json.loads(categories["big_supermarket"]["brands"]) == thirty_a.BIG_SUPERMARKET_BRANDS
        assert categories["local_market"]["brands"] is None
        assert (categories["emergency"]["verified_only"], categories["urgent_care"]["verified_only"], categories["pharmacy"]["verified_only"]) == (1, 1, 0)
        assert con.execute("SELECT COUNT(*) FROM evidence_packs").fetchone()[0] == 0
        con.execute("""INSERT INTO poi_points VALUES ('dn','kurum/A/B','emergency','B','A',30.3,-86.3,'kurumun kendi sitesi',NULL,NULL,NULL,NULL,NULL,NULL,NULL)""")
        con.execute("""INSERT INTO poi_chain_checks VALUES ('dn','Target','T',NULL,NULL,NULL,NULL,NULL,'okunamadı',NULL,'okunamadi',NULL,'pharmacy')""")
        with pytest.raises(sqlite3.IntegrityError):              # the same chain and store twice in one category
            con.execute("""INSERT INTO poi_chain_checks VALUES ('dn','Target','T',NULL,NULL,NULL,NULL,NULL,'okunamadı',NULL,'okunamadi',NULL,'pharmacy')""")
    backup, = (tmp_path / "backups").glob("*-v13-*.sqlite3")
    with sqlite3.connect(backup) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 13


def test_v13_to_v14_failure_rolls_back_everything(tmp_path, monkeypatch):
    import sqlite3
    from studio import database
    from tests.test_climate import table_counts
    path = tmp_path / "studio.sqlite3"; make_v13(path)
    with sqlite3.connect(path) as con:
        before = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in table_counts(con)}
    original = database.upgrade_v14
    def fail(con): original(con); raise RuntimeError("after all DDL and the category seed")
    with monkeypatch.context() as m:
        m.setattr(database, "upgrade_v14", fail)
        with pytest.raises(RuntimeError):
            database.Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 13
        assert {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in table_counts(con)} == before


def test_profile_reviewed_files_name_their_source_url_date_and_coordinate_source():
    """The 30A reviewed files: known categories and statuses; each open place added from a file carries its page, check date and
    where its coordinate comes from (the GÖREV-10 supermarket rows say it in their note)."""
    for path, label in thirty_a.REVIEWED_POINT_FILES:
        rows = dn.read_reviewed(path, CATEGORIES, "big_supermarket")
        assert rows and label in ("zincirin kendi sitesi", "kurumun kendi sitesi")
        for row in rows:
            assert row["kontrol_tarihi"] and (row["magaza_url"] or row["durum"] == "okunamadı")
            if row["durum"] == "açık":
                assert row["enlem"] and row["boylam"] and row["adres"]
                assert row["koordinat_kaynagi"] or "oordinat" in row["not"]
    health = dn.read_reviewed(thirty_a.HEALTH_POINTS, CATEGORIES)
    assert {r["kategori"] for r in health} == {"emergency", "urgent_care"}
