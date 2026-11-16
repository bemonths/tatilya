"""v0.2 gerçek tablo sözleşmesiyle oluşturulan sentetik migration girdisi."""
import json
import sqlite3
from pathlib import Path

from studio.sources.beaches import SOURCE_URL
from studio.sources.climate_normals import SOURCE_URL as NORMALS_URL
from studio.sources.neighborhoods import SOURCE_URL as NEIGHBORHOOD_URL
from studio.sources.storm_proximity import SOURCE_URL as STORMS_URL
from studio.sources.water_temperature import SOURCE_URL as WATER_URL
from studio.destinations.thirty_a import LODGING_CLONE_HOST
from studio.sources.daily_needs import SOURCE_URL as DAILY_NEEDS_URL
from studio.sources.road_network import SOURCE_URL as ROAD_URL
from studio.sources.airfare import SOURCE_URL as AIRFARE_URL

LODGING_URL = f"https://{LODGING_CLONE_HOST}/"
AGENCY_URL = f"https://{LODGING_CLONE_HOST}/?kaynak=kiralama-sirketleri"
RESTAURANT_SITES_URL = "https://www.visitsouthwalton.com/listings/culinary-experiences/?kaynak=isletme-siteleri"

# Built-in 30A sources added by migrations: v7 (neighborhoods), v8 (three climate sources), v10 (Book>Direct lodging),
# v11 (rental company prices), v12 (restaurant facts from the businesses' own sites), v13 (OpenStreetMap daily-need points) and
# v20 (OpenStreetMap road network, BTS airport fares).
ADDED_SOURCE_URLS = (NEIGHBORHOOD_URL, NORMALS_URL, WATER_URL, STORMS_URL, LODGING_URL, AGENCY_URL, RESTAURANT_SITES_URL, DAILY_NEEDS_URL,
                     ROAD_URL, AIRFARE_URL)
# Tables created by v8 and their rows in an upgraded 30A database (configuration only, no snapshots).
V8_TABLES = {"destination_climate_stations": 3, "destination_storm_corridors": 1, "climate_normal_stations": 0,
             "climate_normal_values": 0, "water_temperature_stations": 0, "water_temperature_months": 0,
             "storm_corridor_snapshots": 0, "storm_passages": 0}
# Tables created by v10 and their rows in an upgraded 30A database (lodging configuration only, no snapshots; v12 adds a window).
V10_TABLES = {"destination_lodging_sources": 1, "destination_lodging_locations": 14, "destination_lodging_windows": 5,
              "lodging_snapshots": 0, "lodging_windows": 0, "lodging_filters": 0, "lodging_listings": 0, "lodging_search_results": 0,
              "lodging_calendars": 0, "lodging_rate_months": 0, "lodging_calendar_windows": 0}
# Tables created by v11 and their rows in an upgraded 30A database (agency site list only, no snapshots; v12 adds 15 companies).
V11_TABLES = {"job_waits": 0, "destination_agency_sites": 24, "agency_rate_snapshots": 0, "agency_rate_windows": 0,
              "agency_rate_companies": 0, "agency_rate_listings": 0, "agency_rate_quotes": 0}
# Tables created by v12 (empty in an upgraded database).
V12_TABLES = {"agency_rate_own_listings": 0, "agency_rate_own_quotes": 0, "agency_rate_published": 0, "restaurant_site_snapshots": 0,
              "restaurant_sites": 0, "restaurant_facts": 0, "restaurant_menus": 0, "restaurant_menu_items": 0,
              "browser_hosts": 0}
# Tables created by v13 and their rows in an upgraded 30A database (configuration only: refresh intervals, daily-need area and categories).
V13_TABLES = {"destination_refresh_intervals": 6, "refresh_batches": 0, "destination_poi_areas": 1, "destination_poi_categories": 7,
              "poi_snapshots": 0, "poi_points": 0, "poi_chain_checks": 0}
# Tables created by v14 (GÖREV-11; v14 also replaces the 5 daily-need categories with the profile's 7, counted above).
V14_TABLES = {"evidence_packs": 0}
V15_TABLES = {"claude_runs": 0, "videos": 0}
V16_TABLES = {"claude_usage": 0, "job_progress": 0}
V17_TABLES = {"text_runs": 0, "text_sessions": 0, "text_versions": 0, "text_selections": 0}
V18_TABLES = {"region_blocked_hosts": 0}
V19_TABLES = {"job_hidden": 0}
# Tables created by v20 and their rows in an upgraded 30A database (configuration only; v20 also adds two refresh intervals and two sources).
V20_TABLES = {"destination_road_networks": 1, "destination_airfare_sources": 1, "road_snapshots": 0, "road_targets": 0, "road_nearest": 0,
              "airfare_snapshots": 0, "airfare_quarters": 0}
V20_INTERVALS = ("openstreetmap-road-network", "bts-airport-fares")
# Tables created by v21 (GÖREV-21: the steps of a video, their status log, the open video); empty in a database without videos.
V21_TABLES = {"video_steps": 0, "video_step_log": 0, "project_state": 0}
V20_VIDEOS = """CREATE TABLE videos (
        id TEXT PRIMARY KEY, destination_id TEXT NOT NULL REFERENCES destinations(id),
        region_id TEXT REFERENCES regions(id), region_name TEXT NOT NULL,
        title_en TEXT NOT NULL CHECK(length(title_en) BETWEEN 1 AND 100), title_tr TEXT NOT NULL CHECK(length(title_tr) > 0),
        family TEXT NOT NULL, analysis TEXT NOT NULL CHECK(json_valid(analysis) AND json_type(analysis)='object'),
        template_key TEXT, params TEXT NOT NULL CHECK(json_valid(params) AND json_type(params)='object'),
        status TEXT NOT NULL CHECK(status IN ('baslik_secildi','paket_hazir')), created_at TEXT NOT NULL,
        run_id TEXT NOT NULL REFERENCES claude_runs(id), candidate INTEGER NOT NULL CHECK(candidate >= 0),
        proposed_title_en TEXT, proposed_title_tr TEXT, user_edited INTEGER NOT NULL DEFAULT 0 CHECK(user_edited IN (0,1)),
        UNIQUE(run_id, candidate)
    )"""


def drop_v21(con):
    """A schema 20 file made from a fresh one: the videos table as schema 15–20 had it (a title and a chosen candidate required, no
    working name, no archive) and without the v21 tables. Rows of videos are kept (a video without a title cannot exist there)."""
    con.execute("PRAGMA foreign_keys=OFF")
    con.execute("DROP INDEX video_step_log_video")
    for table in ("video_step_log", "video_steps", "project_state"):
        con.execute(f"DROP TABLE {table}")
    con.execute("ALTER TABLE videos RENAME TO videos_v21")
    con.execute("DROP INDEX videos_destination")
    con.execute(V20_VIDEOS)
    con.execute("""INSERT INTO videos SELECT id,destination_id,region_id,region_name,title_en,title_tr,family,analysis,template_key,params,
        CASE status WHEN 'yeni' THEN 'baslik_secildi' ELSE status END,created_at,run_id,candidate,proposed_title_en,proposed_title_tr,user_edited
        FROM videos_v21""")
    con.execute("DROP TABLE videos_v21")
    con.execute("CREATE INDEX videos_destination ON videos(destination_id, created_at)")


def drop_v17(con):
    """A file of an older schema made from a fresh one: without the v17 tables (GÖREV-15: the video text) and the v18 table
    (GÖREV-16: the region-blocked domains)."""
    drop_v18(con)
    for index in ("text_selections_video", "text_versions_run", "text_sessions_run", "text_runs_video"):
        con.execute(f"DROP INDEX {index}")
    for table in ("text_selections", "text_versions", "text_sessions", "text_runs"):
        con.execute(f"DROP TABLE {table}")


def drop_v20(con, rows=False):
    """A schema 19 file made from a fresh one: without the v20 tables (GÖREV-20: road distances, airfare) and the v21 changes. The two
    v20 sources and refresh intervals stay (the upgrade adds each only once); `rows=True` takes them out too, as in a file v20 never touched."""
    drop_v21(con)
    con.execute("DROP INDEX road_nearest_category")
    for table in ("road_nearest", "road_targets", "road_snapshots", "airfare_quarters", "airfare_snapshots", "destination_road_networks",
                  "destination_airfare_sources"):
        con.execute(f"DROP TABLE {table}")
    if rows:
        con.execute("DELETE FROM sources WHERE url IN (?,?)", (ROAD_URL, AIRFARE_URL))
        con.execute("DELETE FROM destination_refresh_intervals WHERE connector_name IN (?,?)", V20_INTERVALS)


def drop_v19(con):
    """A schema 18 file made from a fresh one: without the v19 table (GÖREV-17: jobs taken off the job panel) and the v20 additions."""
    drop_v20(con)
    con.execute("DROP TABLE job_hidden")


def drop_v18(con):
    """A schema 17 file made from a fresh one: without the v18 table (GÖREV-16: the region-blocked domains) and the v19 table."""
    drop_v19(con)
    con.execute("DROP TABLE region_blocked_hosts")


def without_added_sources(sources):
    """Migrations add exactly one source per built-in URL; every older source row must stay unchanged."""
    url = lambda source: source["url"] if isinstance(source, dict) else source[2]
    for added in ADDED_SOURCE_URLS:
        assert sum(url(source) == added for source in sources) == 1, added
    return [source for source in sources if url(source) not in ADDED_SOURCE_URLS]


def without_added_snapshot(snapshot):
    return {**snapshot, "sources": without_added_sources(snapshot["sources"])}


def make_legacy_db(path, version=2):
    with sqlite3.connect(path) as con:
        con.executescript((Path(__file__).parent / "fixtures/v02-schema.sql").read_text(encoding="utf-8"))
        con.execute("INSERT INTO metadata VALUES ('seeded','2026-09-01')")
        con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            "source-a", "Kullanıcının değiştirdiği ad", SOURCE_URL, "Plaj", "Tüm 30A", "JSON", "Gerektiğinde",
            "Kullanıcı notu korunmalı", 0, 4, "2026-09-01", "2026-09-02"))
        con.execute("INSERT INTO source_history(source_id,saved_at,snapshot) VALUES (?,?,?)", (
            "source-a", "2026-09-02", json.dumps({"name": "Kullanıcının değiştirdiği ad", "version": 4})))
        for identifier, status in (("old-success", "done"), ("old-failed", "failed"), ("old-canceled", "canceled")):
            con.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)", (
                identifier, "beach_collection", "Eski toplama", status, 100 if status == "done" else 10,
                "Eski iş mesajı", "2026-09-01", "2026-09-02", '{"included":1}' if status == "done" else None,
                '[{"at":"2026-09-01","text":"Eski günlük"}]'))
        con.execute("INSERT INTO collections VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            "old-success", "source-a", SOURCE_URL, "2026-09-02", "Kaynak zamanı", "south-walton-beaches/1",
            2, 1, 1, "raw/old-success/source.html", "abc123", "Eski kapsam kuralı"))
        con.execute("INSERT INTO beach_records VALUES (?,?,?,?,?,?,?,?,?)", (
            "old-success", "external-1", "Eski plaj", "Santa Rosa Beach", "Kaynak adresi", 30.35, -86.14,
            "regional", '["Parking"]'))
        if version == 1:
            con.execute("DROP TABLE beach_records")
            con.execute("DROP TABLE collections")
        con.execute(f"PRAGMA user_version={version}")
    raw = path.parent / "raw/old-success/source.html"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("Sentetik eski ham kaynak", encoding="utf-8")
