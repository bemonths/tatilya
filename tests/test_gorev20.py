"""GÖREV-20: the new data in the evidence pack (road distances beside great-circle ones, airports, airport fares, which rental
companies the prices cover, the out-of-scope rows), the known gaps, and the run estimate that counts newly configured companies.

No network: collectors run through httpx.MockTransport (the fixtures of test_road_network and test_airfare).
"""
import json
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from studio import evidence, refresh
from studio.app import create_app
from studio.database import Database
from studio.destinations import thirty_a
from studio.evidence import blocks as B
from studio.evidence import pack as P
from studio.evidence import summary as S
from studio.sources import agency_rates as ar
from studio.sources import airfare as af
from studio.sources import climate_http
from studio.sources import daily_needs as dn
from studio.sources import road_network as rn
from tests.test_airfare import BtsMock
from tests.test_beaches import HEADERS
from tests.test_daily_needs import answer_mock as points_mock
from tests.test_daily_needs import element
from tests.test_evidence import NOW, PRICE_RUN
from tests.test_lodging import BookDirectMock, fast, inventory, lodging, start  # noqa: F401  (fast: autouse fixture)
from tests.test_monthly_windows import use
from tests.test_road_network import ANSWER

REAL = {"roads": rn.collect, "points": dn.collect, "fares": af.collect}
STORES = {"osm3s": {"timestamp_osm_base": "2026-10-09T11:34:06Z"}, "elements": [
    element("node", 21, 30.3100, -86.0690, shop="supermarket", name="Publix", brand="Publix"),
    element("node", 22, 30.3001, -86.0560, shop="supermarket", name="Publix", brand="Publix")]}


@pytest.fixture(autouse=True)
def no_gap(monkeypatch):
    monkeypatch.setattr(climate_http, "REQUEST_GAP", 0)


@pytest.fixture
def collected(tmp_path, monkeypatch):
    """An app with a lodging run (one Dune Allen listing on the test road network), daily-need points, road distances and airport fares."""
    data = inventory()
    data[62708] = [lodging(3001, "Dune Allen condo", 62708, latitude="30.3001", longitude="-86.0700")]
    def points(path, progress, canceled, *, config, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(points_mock(STORES))) as client:
            return REAL["points"](path, progress, canceled, config={**config, "reviewed_files": []}, client=client, today=date(2026, 10, 9))
    def roads(path, progress, canceled, *, config, **kwargs):
        handler = lambda request: httpx.Response(200, content=json.dumps(ANSWER).encode(), headers={"content-type": "application/json"})
        extra = [{"key": "VPS", "label": "Deneme Havalimanı (VPS)", "latitude": 30.3000, "longitude": -86.0400}]
        settings = {**config["settings"], "snap_limit_m": 1200, "extra_points": extra,
                    "length_checks": [{"label": "Ana yol", "refs": ["CR 1"], "expected_miles": 3.0, "source": "deneme kaynağı"}]}
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            return REAL["roads"](path, progress, canceled, config={**config, "settings": settings}, client=client, today=date(2026, 11, 16))
    def fares(path, progress, canceled, *, config, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(BtsMock(without={(2025, 3): ("ECP",)}))) as client:
            return REAL["fares"](path, progress, canceled, config=config, client=client, today=date(2026, 11, 16), gap=0)
    monkeypatch.setattr(dn, "collect", points)
    monkeypatch.setattr(rn, "collect", roads)
    monkeypatch.setattr(af, "collect", fares)
    with TestClient(create_app(tmp_path / "data"), headers=HEADERS) as client:
        use(monkeypatch, BookDirectMock(data), date(2026, 10, 7))
        for url in (None, dn.SOURCE_URL, rn.SOURCE_URL, af.SOURCE_URL):
            job = start(client, url=url) if url else start(client)
            assert job["status"] == "done", job["message"]
        yield client


def add_run(con, identifier, url_like, connector, metadata=None):
    """A finished job and source run of a built-in source, written straight into the tables."""
    source = con.execute("SELECT id FROM sources WHERE url LIKE ?", (url_like,)).fetchone()["id"]
    con.execute("INSERT INTO jobs (id,kind,title,status,progress,message,created_at,source_id,destination_id) VALUES (?,'source_collection','x','done',"
                "100,'','2026-11-01',?,'30a')", (identifier, source))
    con.execute("""INSERT INTO source_runs (id,source_id,job_id,status,started_at,finished_at,connector_name,connector_version,destination_id,metadata)
        VALUES (?,?,?,'done','2026-11-01T10:00:00+00:00','2026-11-01T11:00:00+00:00',?,'x','30a',?)""",
                (identifier, source, identifier, connector, json.dumps(metadata or {})))


def add_lodging_run(con, identifier, urls=()):
    add_run(con, identifier, "https://visitsouthwalton.bookdirect.net/", "bookdirect-lodging", {"window_rule": thirty_a.LODGING_WINDOW_RULE})
    con.execute("""INSERT INTO lodging_snapshots (run_id,clone_host,front_end_path,default_category_id,searched_on,request_count,listing_count)
        VALUES (?,'h','/',1,'2026-11-01',0,?)""", (identifier, len(urls)))
    for number, url in enumerate(urls, 1):
        con.execute("""INSERT INTO lodging_listings (run_id,lodging_id,title,category_ids,category_names,amenities,hide_rate_calendar,live_rates_enabled,url)
            VALUES (?,?,?,'[]','[]','[]',0,0,?)""", (identifier, number, f"Ev {number}", url))


def rows_of(pack, block):
    return [row for section in pack["sections"] for row in section["rows"] if row["blok"] == block]


def test_templates_carry_the_new_blocks_where_the_text_needs_them():
    templates = evidence.destination_templates(thirty_a)
    first = {s["key"]: [b["block"] for b in s["blocks"]] for s in templates["ilk-video"]["sections"]}
    assert first["konaklama"][-1] == "lodging_coverage"
    assert first["ulasim"][:4] == ["daily_needs", "road_distances", "airfare", "out_of_scope"]
    road = next(b for s in templates["ilk-video"]["sections"] for b in s["blocks"] if b["block"] == "road_distances")
    assert {"extra:VPS", "extra:ECP", "big_supermarket", "emergency"} <= set(road["categories"]) and road["checks"] is True
    guide = {s["key"]: [b["block"] for b in s["blocks"]] for s in templates["mahalle-rehberi"]["sections"]}
    assert guide["gunluk"] == ["daily_needs", "road_distances"]
    assert templates["ilk-video"]["version"] == "2" and templates["mahalle-rehberi"]["version"] == "2"


def test_without_runs_the_new_blocks_say_veri_yok_and_the_gaps_say_what_is_missing(tmp_path):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    pack = evidence.generate(db, "30a", thirty_a, "ilk-video", now=NOW)
    for block in ("road_distances", "airfare", "lodging_coverage"):
        found = rows_of(pack, block)
        assert found and all(r["durum"] == evidence.MISSING and r["kullanim_notu"] == B.USAGE[block] for r in found), block
    gaps = " ".join(pack["header"]["bilinen_bosluklar"])
    assert "Yol üzerinden mesafe ve sürüş süresi yok" in gaps and "Uçak bileti hakkında veri yok" in gaps


def test_out_of_scope_topics_are_rows_and_a_known_gap(tmp_path):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    pack = evidence.generate(db, "30a", thirty_a, "ilk-video", now=NOW)
    rows = rows_of(pack, "out_of_scope")
    assert [r["ifade"] for r in rows] == ["Kapsam dışı: araç kiralama fiyatları", "Kapsam dışı: market fiyatları",
                                           "Kapsam dışı: anlık trafik ve trafikli sürüş süresi", "Kapsam dışı: Vrbo ilanlarının fiyatları"]
    assert all(r["durum"] == evidence.MISSING and r["not"].startswith("Kapsam dışı; program bu veriyi toplamıyor.") for r in rows)
    assert all(r["kullanim_notu"] == B.USAGE["out_of_scope"] and "(M14)" in r["kullanim_notu"] for r in rows)
    gap = next(g for g in pack["header"]["bilinen_bosluklar"] if g.startswith("Kapsam dışı"))
    assert all(word in gap for word in ("araç kiralama fiyatları", "market fiyatları", "anlık trafik", "Vrbo"))
    text = S.render(pack)
    assert "### Kapsam dışı (veri toplanmıyor)" in text and all(r["id"] in text for r in rows)


def test_road_rows_put_road_miles_minutes_and_the_great_circle_value_side_by_side(collected):
    db = collected.app.state.db
    pack = evidence.generate(db, "30a", thirty_a, "mahalle-rehberi", {"mahalle": "dune-allen"}, now=NOW)
    road = {r["tablo"]["sutun"]: r for r in rows_of(pack, "road_distances") if r["durum"] == "var"}
    market = road["Büyük süpermarket"]
    kinds = {e["tur"]: e for e in market["ek_degerler"]}
    assert set(kinds) == {"sure_dk", "kus_ucusu", "pay", "donusum"}
    assert market["birim"] == "mil" and market["deger"] >= kinds["kus_ucusu"]["deger"] > 0 and kinds["sure_dk"]["deger"] >= 1
    assert market["etiket"] == "bizim hesabımız" and market["orneklem"] == 1 and market["kullanim_notu"] == B.USAGE["road_distances"]
    assert "trafik hesaba katılmadan" in market["ifade"] and "kuş uçuşu ortancası" in market["ifade"] and "Yürüme mesafesi değildir" in market["not"]
    assert market["tablo"]["ad"].startswith("Yol üzerinden mesafe ortancası")
    crow = next(r for r in rows_of(pack, "daily_needs") if r["tablo"]["sutun"] == "Büyük süpermarket" and r["durum"] == "var")
    assert crow["deger"] == kinds["kus_ucusu"]["deger"]                               # the same listing: the two blocks agree on the straight line
    airport = road["Deneme Havalimanı (VPS)"]
    assert airport["tablo"]["ad"].startswith("Havalimanlarına yol mesafesi") and {e["tur"] for e in airport["ek_degerler"]} == {"sure_dk", "donusum"}
    numbers = {(n["kanit"], n["tur"]) for n in pack["checklist"]}
    assert {(market["id"], "ana"), (market["id"], "sure_dk"), (market["id"], "kus_ucusu")} <= numbers       # every number can be checked
    text = S.render(pack)
    line = next(l for l in text.splitlines() if l.startswith("| Dune Allen |") and " dk · kuş " in l)
    assert f"{P.value_text(market['deger'])} · {kinds['sure_dk']['deger']} dk · kuş {P.value_text(kinds['kus_ucusu']['deger'])}" in line
    assert "### Yol üzerinden mesafe ve tahmini sürüş süresi" in text
    gaps = " ".join(pack["header"]["bilinen_bosluklar"])
    assert "süre trafik, ışık ve dönüş beklemesi olmadan tahmindir" in gaps and "Yol üzerinden mesafe ve sürüş süresi yok" not in gaps


def test_first_video_pack_has_airports_the_length_check_and_the_airport_fares(collected):
    db = collected.app.state.db
    pack = evidence.generate(db, "30a", thirty_a, "ilk-video", now=NOW)
    road = rows_of(pack, "road_distances")
    check = next(r for r in road if r["ifade"].startswith("Sağlama:"))
    assert "deneme kaynağı" in check["ifade"] and check["birim"] == "mil" and "videoda söylenecek bir değer değildir" in check["not"]
    assert any(r["durum"] == evidence.MISSING and "extra:ECP" in r["ifade"] for r in road)          # an airport this run did not measure
    fares = rows_of(pack, "airfare")
    table = [r for r in fares if r.get("tablo")]
    assert len(table) == 10 and sum(r["durum"] == evidence.MISSING for r in table) == 1               # ECP is not in the table of 2025 Q3
    latest = next(r for r in table if r["tablo"]["satir"].endswith("(VPS)") and r["tablo"]["sutun"] == "2026 Q2")
    assert (latest["deger"], latest["birim"], latest["etiket"]) == (376.10, "USD", "kaynak gerçeği")
    assert "başlayan iç hat yolculuklarının ortalama bilet ücreti" in latest["ifade"] and "By Origin City for Q2 2026" in latest["alinti"]
    assert "belirli bir şehirden o havalimanına bilet fiyatı değildir" in latest["not"] and "(M20)" in latest["kullanim_notu"]
    change = next(r for r in fares if not r.get("tablo") and "(VPS)" in r["ifade"])
    assert (change["deger"], change["etiket"]) == (16.48, "bizim hesabımız") and change["ek_degerler"] == [{"tur": "degisim", "deger": 4.6,
                                                                                                           "birim": "% (bir yıl önceki aynı çeyreğe göre)"}]
    assert {i["tur"] for i in pack["checklist"]} <= {"ana", *B.EXTRA_TYPES}
    text = S.render(pack)
    assert "| Havalimanı | 2026 Q2 | 2026 Q1 | 2025 Q4 | 2025 Q3 | 2025 Q2 | Kimlik |" in text and "$376.1" in text
    gaps = " ".join(pack["header"]["bilinen_bosluklar"])
    assert "BTS'nin havalimanı ortalamasıdır" in gaps and "Uçak bileti hakkında veri yok" not in gaps
    stored = collected.post("/api/evidence-packs", json={"template_key": "ilk-video", "params": {}})
    assert stored.status_code == 201                                                                  # the app stores the same pack


def test_coverage_block_names_the_companies_in_the_prices_and_the_unreadable_ones_with_reasons(tmp_path, monkeypatch):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    with db.connect() as con:
        add_lodging_run(con, "l")
        add_run(con, "fiyat-cekimi", "%kaynak=kiralama-sirketleri", "agency-lodging-rates")
        con.execute("INSERT INTO agency_rate_snapshots (run_id,lodging_run_id,queried_on,request_count,listing_count) VALUES ('fiyat-cekimi','l','2026-10-09',1,0)")
        con.execute("INSERT INTO agency_rate_windows (run_id,window_key,label,checkin,checkout,nights,status) VALUES ('fiyat-cekimi','w','Hafta','2027-07-10','2027-07-17',7,'queried')")
        con.execute("""INSERT INTO agency_rate_companies (run_id,domain,company,adapter,status,listing_count,matched_count,quote_count,priced_count,
            request_count) VALUES ('fiyat-cekimi','benchmark30a.com','Benchmark Management','rescms','done',2,2,1,1,3)""")
        def listing(identifier, host, status, domain=None):
            con.execute("""INSERT INTO agency_rate_listings (run_id,lodging_id,title,region_ids,listing_url,url_host,domain,page_status,site_listing_id)
                VALUES ('fiyat-cekimi',?,?,'[]',?,?,?,?,?)""", (identifier, f"Ev {identifier}", f"https://{host}/x", host, domain, status,
                                                              str(identifier) if status == "matched" else None))
        for index in range(25):
            listing(100 + index, "360blue.com", "no_adapter")
        for index in range(3):
            listing(200 + index, "www.vacasa.com", "no_adapter")
        listing(300, "kucuksirket.example", "no_adapter")
        listing(400, "benchmark30a.com", "matched", "benchmark30a.com")
        listing(401, "benchmark30a.com", "matched", "benchmark30a.com")
        con.execute("""INSERT INTO agency_rate_quotes (run_id,lodging_id,window_key,status,available,total,queried_at,queried_url,raw_sha256)
            VALUES ('fiyat-cekimi',400,'w','priced',1,5000,'2026-10-09','https://benchmark30a.com/x','[]')""")
    data = B.BlockData(db, "30a", thirty_a, date(2026, 11, 16))
    summary = {"snapshot": {"queried_on": "2026-10-09"}, "coverage": {"listings": 31, "priced_listings": 1}, "cells": [],
               "companies": [{"domain": "benchmark30a.com", "company": "Benchmark Management", "listing_count": 2},
                             {"domain": "funvacay.com", "company": "FunVacay", "listing_count": 4}]}
    monkeypatch.setattr(B, "agency_summary", lambda _: (PRICE_RUN, summary))
    rows = B.lodging_coverage(data, {"block": "lodging_coverage"})
    assert (rows[0]["deger"], rows[0]["orneklem"]) == (1, 31)
    included = [r for r in rows if (r.get("tablo") or {}).get("ad") == "Fiyat ortancalarına giren kiralama şirketleri"]
    assert [(r["tablo"]["satir"], r["deger"], r["orneklem"]) for r in included] == [("Benchmark Management", 1, 2)]   # a company with no price is not "in"
    left = {r["tablo"]["satir"]: r for r in rows if (r.get("tablo") or {}).get("ad") == "Fiyatı okunamayan kiralama şirketleri"}
    assert set(left) == {"360blue.com", "vacasa.com"}                                  # the small unreviewed site stays out; a reviewed one is named
    assert left["360blue.com"]["deger"] == 25 and "engel sayfası" in left["360blue.com"]["tablo"]["hucreler"]["Neden"]
    assert left["vacasa.com"]["deger"] == 3 and left["vacasa.com"]["tablo"]["hucreler"]["Bakıldığı tarih"] == "2026-11-17"      # looked at again in GÖREV-22
    assert all(r["kullanim_notu"] == B.USAGE["lodging_coverage"] and r["etiket"] == "bizim hesabımız" for r in rows)
    gaps = P.known_gaps(data)
    assert any(g.startswith("Fiyatı okunamayan kiralama şirketleri") and "360blue.com 25" in g and "vacasa.com 3" in g and "kucuksirket" not in g for g in gaps)


def test_reviewed_unreadable_companies_file_names_every_target_company_with_a_reason_and_a_date():
    rows = B.unread_companies(thirty_a)
    assert {"360blue.com", "rentals.cottagerentalagency.com", "realjoy.com", "30a-beachgirls.com", "vacasa.com", "outdoorshower30a.com"} <= set(rows)
    assert all(item["neden"] and item["okuma_yolu"] and item["kontrol_tarihi"] in ("2026-11-16", "2026-11-17") for item in rows.values())


def test_estimate_counts_the_companies_configured_since_the_last_run():
    sites = [{"domain": "eski.example", "company": "Eski", "adapter": "rescms", "enabled": 1, "aliases": [], "protected": 0},
             {"domain": "yeni.example", "company": "Yeni", "adapter": "track", "enabled": 1, "aliases": ["yeni-rentals.example"], "protected": 0},
             {"domain": "korumali.example", "company": "Korumalı", "adapter": "vrp", "enabled": 1, "aliases": [], "protected": 1},
             {"domain": "kapali.example", "company": "Kapalı", "adapter": "vrp", "enabled": 0, "aliases": [], "protected": 0}]
    listings = [{"url": "https://www.yeni.example/a"}, {"url": "https://book.yeni-rentals.example/b"}, {"url": "https://korumali.example/c"},
                {"url": "https://eski.example/d"}, {"url": "https://kapali.example/e"}, {"url": None}]
    added = {a["domain"]: a for a in ar.new_site_estimate(sites, listings, {"eski.example"}, 12)}
    assert set(added) == {"yeni.example", "korumali.example"}
    assert added["yeni.example"]["listings"] == 2 and added["yeni.example"]["requests"] == 2 * (1 + 12 * ar.QUOTE_REQUESTS)
    assert added["yeni.example"]["seconds"] == int(added["yeni.example"]["requests"] * (ar.REQUEST_GAP + ar.ANSWER_SECONDS))
    assert added["korumali.example"]["seconds"] == int(25 * (ar.PROTECTED_GAP + ar.ANSWER_SECONDS)) and added["korumali.example"]["protected"]


def test_refresh_status_lists_the_new_collectors_and_adds_new_companies_to_the_rate_estimate(tmp_path, monkeypatch):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    status = refresh.status(db, "30a", today=date(2026, 11, 16))
    by_name = {i["connector"]: i for i in status["items"]}
    assert (by_name["openstreetmap-road-network"]["interval_months"], by_name["bts-airport-fares"]["interval_months"]) == (1, 3)
    assert by_name["openstreetmap-road-network"]["follows"] == ["bookdirect-lodging", "openstreetmap-daily-needs"]
    assert by_name["agency-lodging-rates"]["added_companies"] == []                    # no run yet: nothing to compare with
    with db.connect() as con:
        add_lodging_run(con, "konaklama", ["https://www.benchmark30a.com/rentals/a", "https://www.benchmark30a.com/rentals/b"])
        add_run(con, "fiyat", "%kaynak=kiralama-sirketleri", "agency-lodging-rates", {"window_rule": thirty_a.LODGING_WINDOW_RULE})
        con.execute("INSERT INTO agency_rate_snapshots (run_id,lodging_run_id,queried_on,request_count,listing_count) VALUES ('fiyat','konaklama','2026-11-01',1,2)")
        # the last run read every configured company except Benchmark (as if it had been configured after that run)
        for row in con.execute("SELECT domain, company, adapter FROM destination_agency_sites WHERE domain<>'benchmark30a.com'").fetchall():
            con.execute("""INSERT INTO agency_rate_companies (run_id,domain,company,adapter,status,listing_count,matched_count,quote_count,priced_count,
                request_count) VALUES ('fiyat',?,?,?,'done',0,0,0,0,0)""", tuple(row))
    item = next(i for i in refresh.status(db, "30a", today=date(2026, 11, 16))["items"] if i["connector"] == "agency-lodging-rates")
    added = item["added_companies"]
    assert [(a["domain"], a["listings"], a["requests"]) for a in added] == [("benchmark30a.com", 2, 2 * (1 + 12 * ar.QUOTE_REQUESTS))]
    assert item["estimate_seconds"] == 3600 + added[0]["seconds"] and "+50 istek" in item["estimate_note"] and "Benchmark Management" in item["estimate_note"]
