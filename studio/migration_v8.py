"""v7 -> v8: destination climate configuration and climate snapshots (normals, sea water temperature, storm passages).

The caller owns the backup and the single transaction; any failure rolls everything back.
Existing sources, history, runs, domain snapshots and raw files are not modified.
"""
import json
import uuid
from datetime import datetime, timezone

from .destinations import DEFAULT_PROFILE
from .migrations import execute_schema
from .sources.climate_normals import ClimateNormalsConnector, SOURCE_URL as NORMALS_URL
from .sources.storm_proximity import StormProximityConnector, SOURCE_URL as STORMS_URL
from .sources.water_temperature import WaterTemperatureConnector, SOURCE_URL as WATER_URL

SCHEMA = """
    CREATE TABLE destination_climate_stations (
        destination_id TEXT NOT NULL REFERENCES destinations(id), station_key TEXT NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('normals','water_temperature')), station_id TEXT NOT NULL,
        label TEXT NOT NULL, role TEXT NOT NULL,
        latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90),
        longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
        distance_km REAL NOT NULL CHECK(distance_km >= 0), distance_basis TEXT NOT NULL,
        first_year INTEGER CHECK(first_year IS NULL OR first_year BETWEEN 1800 AND 2200),
        sort_order INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
        PRIMARY KEY(destination_id,station_key)
    );
    CREATE TABLE destination_storm_corridors (
        destination_id TEXT PRIMARY KEY REFERENCES destinations(id), label TEXT NOT NULL,
        west_latitude REAL NOT NULL CHECK(west_latitude BETWEEN -90 AND 90),
        west_longitude REAL NOT NULL CHECK(west_longitude BETWEEN -180 AND 180), west_reference TEXT NOT NULL,
        east_latitude REAL NOT NULL CHECK(east_latitude BETWEEN -90 AND 90),
        east_longitude REAL NOT NULL CHECK(east_longitude BETWEEN -180 AND 180), east_reference TEXT NOT NULL,
        radii_nmi TEXT NOT NULL CHECK(json_valid(radii_nmi) AND json_type(radii_nmi)='array'),
        enabled INTEGER NOT NULL CHECK(enabled IN (0,1))
    );
    CREATE TABLE climate_normal_stations (
        run_id TEXT NOT NULL REFERENCES source_runs(id), station_id TEXT NOT NULL, station_key TEXT NOT NULL,
        role TEXT NOT NULL, label TEXT NOT NULL, source_name TEXT, latitude REAL, longitude REAL, elevation_m REAL,
        distance_km REAL NOT NULL CHECK(distance_km >= 0),
        PRIMARY KEY(run_id,station_id)
    );
    CREATE TABLE climate_normal_values (
        run_id TEXT NOT NULL, station_id TEXT NOT NULL, month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
        element TEXT NOT NULL, value REAL, unit TEXT NOT NULL, completeness_flag TEXT, measurement_flag TEXT,
        years INTEGER CHECK(years IS NULL OR years >= 0),
        PRIMARY KEY(run_id,station_id,month,element),
        FOREIGN KEY(run_id,station_id) REFERENCES climate_normal_stations(run_id,station_id)
    );
    CREATE TABLE water_temperature_stations (
        run_id TEXT NOT NULL REFERENCES source_runs(id), station_id TEXT NOT NULL, station_key TEXT NOT NULL,
        role TEXT NOT NULL, label TEXT NOT NULL,
        latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90), longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
        distance_km REAL NOT NULL CHECK(distance_km >= 0), first_year INTEGER NOT NULL, last_year INTEGER NOT NULL,
        years_found TEXT NOT NULL CHECK(json_valid(years_found) AND json_type(years_found)='array'),
        years_missing TEXT NOT NULL CHECK(json_valid(years_missing) AND json_type(years_missing)='array'),
        PRIMARY KEY(run_id,station_id)
    );
    CREATE TABLE water_temperature_months (
        run_id TEXT NOT NULL, station_id TEXT NOT NULL, year INTEGER NOT NULL,
        month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12), mean_c REAL NOT NULL,
        observation_count INTEGER NOT NULL CHECK(observation_count > 0),
        day_count INTEGER NOT NULL CHECK(day_count BETWEEN 1 AND 31),
        PRIMARY KEY(run_id,station_id,year,month),
        FOREIGN KEY(run_id,station_id) REFERENCES water_temperature_stations(run_id,station_id)
    );
    CREATE TABLE storm_corridor_snapshots (
        run_id TEXT PRIMARY KEY REFERENCES source_runs(id), label TEXT NOT NULL,
        west_latitude REAL NOT NULL, west_longitude REAL NOT NULL, west_reference TEXT NOT NULL,
        east_latitude REAL NOT NULL, east_longitude REAL NOT NULL, east_reference TEXT NOT NULL,
        radii_nmi TEXT NOT NULL CHECK(json_valid(radii_nmi) AND json_type(radii_nmi)='array'),
        hurdat_file TEXT NOT NULL, storm_count INTEGER NOT NULL CHECK(storm_count >= 0),
        first_season INTEGER NOT NULL, last_season INTEGER NOT NULL
    );
    CREATE TABLE storm_passages (
        run_id TEXT NOT NULL REFERENCES storm_corridor_snapshots(run_id), storm_id TEXT NOT NULL, name TEXT NOT NULL,
        season INTEGER NOT NULL, radius_nmi REAL NOT NULL CHECK(radius_nmi > 0), first_entry_time TEXT NOT NULL,
        first_entry_month INTEGER NOT NULL CHECK(first_entry_month BETWEEN 1 AND 12),
        closest_km REAL NOT NULL CHECK(closest_km >= 0), closest_nmi REAL NOT NULL CHECK(closest_nmi >= 0),
        max_wind_kt INTEGER CHECK(max_wind_kt IS NULL OR max_wind_kt >= 0),
        storm_class TEXT CHECK(storm_class IS NULL OR storm_class IN ('TD','TS','HU','MH')), status_at_max TEXT,
        PRIMARY KEY(run_id,storm_id,radius_nmi)
    );
    CREATE INDEX storm_passages_month ON storm_passages(run_id,radius_nmi,first_entry_month);
"""
CONNECTORS = ((NORMALS_URL, ClimateNormalsConnector()), (WATER_URL, WaterTemperatureConnector()), (STORMS_URL, StormProximityConnector()))


def seed_destination_climate(con, profile):
    """Copy the profile's first climate configuration into SQLite once; existing rows are never overwritten."""
    destination_id = profile.METADATA["id"]
    if not con.execute("SELECT 1 FROM destinations WHERE id=?", (destination_id,)).fetchone():
        return
    if not con.execute("SELECT 1 FROM destination_climate_stations WHERE destination_id=?", (destination_id,)).fetchone():
        for order, station in enumerate(profile.CLIMATE_STATIONS):
            con.execute("""INSERT INTO destination_climate_stations (destination_id,station_key,kind,station_id,label,role,latitude,
                longitude,distance_km,distance_basis,first_year,sort_order,enabled) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                (destination_id, station["station_key"], station["kind"], station["station_id"], station["label"], station["role"],
                 station["latitude"], station["longitude"], station["distance_km"], profile.CLIMATE_DISTANCE_BASIS,
                 station["first_year"], order))
    if not con.execute("SELECT 1 FROM destination_storm_corridors WHERE destination_id=?", (destination_id,)).fetchone():
        corridor = profile.STORM_CORRIDOR
        con.execute("""INSERT INTO destination_storm_corridors (destination_id,label,west_latitude,west_longitude,west_reference,
            east_latitude,east_longitude,east_reference,radii_nmi,enabled) VALUES (?,?,?,?,?,?,?,?,?,1)""",
            (destination_id, corridor["label"], corridor["west_latitude"], corridor["west_longitude"], corridor["west_reference"],
             corridor["east_latitude"], corridor["east_longitude"], corridor["east_reference"], json.dumps(list(corridor["radii_nmi"]))))
    sources = [dict(row) for row in con.execute("SELECT * FROM sources WHERE destination_id=?", (destination_id,))]
    for url, connector in CONNECTORS:
        if any(connector.supports(source) for source in sources):
            continue
        name, url, category, notes, method = next(seed for seed in profile.SEEDS if seed[1] == url)
        stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        con.execute("""INSERT INTO sources (id,name,url,category,region,method,cadence,notes,enabled,version,
            created_at,updated_at,destination_id,scope_region_id) VALUES (?,?,?,?,?,?,?,?,1,1,?,?,?,NULL)""",
            (uuid.uuid4().hex, name, url, category, f"Tüm {profile.METADATA['name']}", method, "Haftalık", notes,
             stamp, stamp, destination_id))


def upgrade_v8(con):
    execute_schema(con, SCHEMA)
    seed_destination_climate(con, DEFAULT_PROFILE)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("İklim migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=8")
