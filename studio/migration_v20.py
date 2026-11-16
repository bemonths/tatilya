"""Schema 19 → 20 (GÖREV-20): road distances and driving times on the OpenStreetMap road network, and airport average fares.

Configuration (one row per destination, seeded from the destination profile, edited only in SQLite afterwards):
- `destination_road_networks.settings` (JSON): the road area, the highway types with their default speeds in mph, the access values
  that close a road or allow it only at the ends of a trip, the service roads left out, the snap limit and speed, the extra
  destinations (airport terminals) and the known lengths the network is checked against.
- `destination_airfare_sources`: the airports (JSON list of code and label) and how many quarters are read.

Data (per run):
- `road_snapshots`: the settings used, the OpenStreetMap timestamp, the size of the network, the lodging, daily-need and beach runs
  whose listings and points were measured, the counts and the length checks.
- `road_targets`: every destination measured to (daily-need point, public beach access, extra point) with its snap distance.
- `road_nearest`: per listing and category the point nearest by road: road km, minutes, the great-circle km to that same point and
  the point nearest in a straight line with its km. The table itself refuses a road distance shorter than the great-circle one.
- `airfare_snapshots`, `airfare_quarters`: the quarters read for each airport (a quarter in which the airport is not in the
  source's table is kept as a row with `listed`=0 and no fare).

The two sources and their suggested refresh intervals are added once. No existing row changes.
"""
import json

from .destinations import DEFAULT_PROFILE
from .migration_v13 import seed_source
from .migrations import execute_schema

SCHEMA = """
    CREATE TABLE destination_road_networks (
        destination_id TEXT PRIMARY KEY REFERENCES destinations(id),
        settings TEXT NOT NULL CHECK(json_valid(settings) AND json_type(settings)='object'),
        enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1))
    );
    CREATE TABLE destination_airfare_sources (
        destination_id TEXT PRIMARY KEY REFERENCES destinations(id),
        airports TEXT NOT NULL CHECK(json_valid(airports) AND json_type(airports)='array'),
        quarters INTEGER NOT NULL CHECK(quarters BETWEEN 1 AND 12),
        enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1))
    );
    CREATE TABLE road_snapshots (
        run_id TEXT PRIMARY KEY REFERENCES source_runs(id),
        settings TEXT NOT NULL CHECK(json_valid(settings) AND json_type(settings)='object'),
        queried_on TEXT NOT NULL, osm_timestamp TEXT, request_count INTEGER NOT NULL CHECK(request_count >= 0),
        way_count INTEGER NOT NULL CHECK(way_count >= 0), node_count INTEGER NOT NULL CHECK(node_count >= 0),
        network_km REAL NOT NULL CHECK(network_km >= 0), maxspeed_km REAL NOT NULL CHECK(maxspeed_km >= 0),
        lodging_run_id TEXT, poi_run_id TEXT, beach_run_id TEXT,
        listing_count INTEGER NOT NULL CHECK(listing_count >= 0), tied_count INTEGER NOT NULL CHECK(tied_count >= 0),
        measured_count INTEGER NOT NULL CHECK(measured_count >= 0), target_count INTEGER NOT NULL CHECK(target_count >= 0),
        checks TEXT NOT NULL CHECK(json_valid(checks) AND json_type(checks)='array')
    );
    CREATE TABLE road_targets (
        run_id TEXT NOT NULL REFERENCES road_snapshots(run_id), target_key TEXT NOT NULL CHECK(length(target_key) > 0),
        category_key TEXT NOT NULL CHECK(length(category_key) > 0), kind TEXT NOT NULL CHECK(kind IN ('poi','beach','extra')),
        name TEXT, latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90), longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
        snap_m REAL CHECK(snap_m IS NULL OR snap_m >= 0), reached_count INTEGER NOT NULL DEFAULT 0 CHECK(reached_count >= 0),
        PRIMARY KEY(run_id,target_key)
    );
    CREATE TABLE road_nearest (
        run_id TEXT NOT NULL, lodging_id INTEGER NOT NULL, category_key TEXT NOT NULL, target_key TEXT NOT NULL,
        road_km REAL NOT NULL CHECK(road_km >= 0), minutes REAL NOT NULL CHECK(minutes >= 0), crow_km REAL NOT NULL CHECK(crow_km >= 0),
        crow_nearest_key TEXT, crow_nearest_km REAL CHECK(crow_nearest_km IS NULL OR crow_nearest_km >= 0),
        snap_m REAL NOT NULL CHECK(snap_m >= 0),
        CHECK(road_km >= crow_km),
        PRIMARY KEY(run_id,lodging_id,category_key),
        FOREIGN KEY(run_id,target_key) REFERENCES road_targets(run_id,target_key)
    );
    CREATE INDEX road_nearest_category ON road_nearest(run_id,category_key);
    CREATE TABLE airfare_snapshots (
        run_id TEXT PRIMARY KEY REFERENCES source_runs(id), queried_on TEXT NOT NULL,
        request_count INTEGER NOT NULL CHECK(request_count >= 0), latest_year INTEGER NOT NULL,
        latest_quarter INTEGER NOT NULL CHECK(latest_quarter BETWEEN 1 AND 4), quarters INTEGER NOT NULL CHECK(quarters >= 1),
        airports TEXT NOT NULL CHECK(json_valid(airports) AND json_type(airports)='array'), source_note TEXT, fare_note TEXT
    );
    CREATE TABLE airfare_quarters (
        run_id TEXT NOT NULL REFERENCES airfare_snapshots(run_id), airport_code TEXT NOT NULL CHECK(length(airport_code) = 3),
        year INTEGER NOT NULL, quarter INTEGER NOT NULL CHECK(quarter BETWEEN 1 AND 4), listed INTEGER NOT NULL CHECK(listed IN (0,1)),
        city_name TEXT, state TEXT, passenger_rank INTEGER, rank_basis TEXT,
        average_fare REAL CHECK(average_fare IS NULL OR average_fare > 0), adjusted_fare REAL CHECK(adjusted_fare IS NULL OR adjusted_fare > 0),
        adjusted_base TEXT, title TEXT NOT NULL, raw_sha256 TEXT NOT NULL CHECK(length(raw_sha256) = 64),
        CHECK(listed = 1 OR average_fare IS NULL),
        PRIMARY KEY(run_id,airport_code,year,quarter)
    )
"""


def seed_v20_configuration(con, profile):
    """The road network settings, the airfare airports, the two sources and their refresh intervals of the destination; each once."""
    destination_id = profile.METADATA["id"]
    if not con.execute("SELECT 1 FROM destinations WHERE id=?", (destination_id,)).fetchone():
        return
    road = getattr(profile, "ROAD_NETWORK", None)
    if road:
        con.execute("INSERT OR IGNORE INTO destination_road_networks (destination_id,settings,enabled) VALUES (?,?,1)",
                    (destination_id, json.dumps(road, ensure_ascii=False)))
        seed_source(con, profile, "https://www.openstreetmap.org/?kaynak=yol-agi")
    airfare = getattr(profile, "AIRFARE", None)
    if airfare:
        con.execute("INSERT OR IGNORE INTO destination_airfare_sources (destination_id,airports,quarters,enabled) VALUES (?,?,?,1)",
                    (destination_id, json.dumps(airfare["airports"], ensure_ascii=False), airfare["quarters"]))
        seed_source(con, profile, "https://www.transtats.bts.gov/AverageFare/")
    start = con.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM destination_refresh_intervals WHERE destination_id=?", (destination_id,)).fetchone()[0]
    for order, (connector, months) in enumerate(getattr(profile, "REFRESH_INTERVALS_V20", ())):
        con.execute("INSERT OR IGNORE INTO destination_refresh_intervals (destination_id,connector_name,months,sort_order) VALUES (?,?,?,?)",
                    (destination_id, connector, months, start + order))


def upgrade_v20(con):
    execute_schema(con, SCHEMA)
    seed_v20_configuration(con, DEFAULT_PROFILE)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v20 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=20")
