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

LODGING_URL = f"https://{LODGING_CLONE_HOST}/"
AGENCY_URL = f"https://{LODGING_CLONE_HOST}/?kaynak=kiralama-sirketleri"

# Built-in 30A sources added by migrations: v7 (neighborhoods), v8 (three climate sources), v10 (Book>Direct lodging) and
# v11 (rental company prices).
ADDED_SOURCE_URLS = (NEIGHBORHOOD_URL, NORMALS_URL, WATER_URL, STORMS_URL, LODGING_URL, AGENCY_URL)
# Tables created by v8 and their rows in an upgraded 30A database (configuration only, no snapshots).
V8_TABLES = {"destination_climate_stations": 3, "destination_storm_corridors": 1, "climate_normal_stations": 0,
             "climate_normal_values": 0, "water_temperature_stations": 0, "water_temperature_months": 0,
             "storm_corridor_snapshots": 0, "storm_passages": 0}
# Tables created by v10 and their rows in an upgraded 30A database (lodging configuration only, no snapshots).
V10_TABLES = {"destination_lodging_sources": 1, "destination_lodging_locations": 14, "destination_lodging_windows": 4,
              "lodging_snapshots": 0, "lodging_windows": 0, "lodging_filters": 0, "lodging_listings": 0, "lodging_search_results": 0,
              "lodging_calendars": 0, "lodging_rate_months": 0, "lodging_calendar_windows": 0}
# Tables created by v11 and their rows in an upgraded 30A database (agency site list only, no snapshots).
V11_TABLES = {"job_waits": 0, "destination_agency_sites": 9, "agency_rate_snapshots": 0, "agency_rate_windows": 0,
              "agency_rate_companies": 0, "agency_rate_listings": 0, "agency_rate_quotes": 0}


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
