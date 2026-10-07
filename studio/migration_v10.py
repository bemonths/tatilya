"""v9 -> v10: destination lodging configuration and Book>Direct lodging search snapshots.

The caller owns the backup and the single transaction; any failure rolls everything back.
Existing sources, history, runs, domain snapshots and raw files are not modified.
"""
import uuid
from datetime import datetime, timezone

from .destinations import DEFAULT_PROFILE
from .migrations import execute_schema
from .sources.bookdirect_lodging import BookDirectLodgingConnector

SCHEMA = """
    CREATE TABLE destination_lodging_sources (
        destination_id TEXT PRIMARY KEY REFERENCES destinations(id),
        clone_host TEXT NOT NULL CHECK(clone_host LIKE '%_.bookdirect.net' AND clone_host <> 'admin.bookdirect.net'),
        enabled INTEGER NOT NULL CHECK(enabled IN (0,1))
    );
    CREATE TABLE destination_lodging_locations (
        destination_id TEXT NOT NULL REFERENCES destination_lodging_sources(destination_id), source_location_name TEXT NOT NULL,
        region_id TEXT NOT NULL,
        PRIMARY KEY(destination_id,source_location_name),
        FOREIGN KEY(destination_id,region_id) REFERENCES regions(destination_id,id)
    );
    CREATE TABLE destination_lodging_windows (
        destination_id TEXT NOT NULL REFERENCES destination_lodging_sources(destination_id), window_key TEXT NOT NULL, label TEXT NOT NULL,
        checkin TEXT NOT NULL CHECK(date(checkin) IS checkin), checkout TEXT NOT NULL CHECK(date(checkout) IS checkout AND checkout > checkin),
        sort_order INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
        PRIMARY KEY(destination_id,window_key)
    );
    CREATE TABLE lodging_snapshots (
        run_id TEXT PRIMARY KEY REFERENCES source_runs(id), clone_host TEXT NOT NULL, front_end_path TEXT NOT NULL,
        default_category_id INTEGER NOT NULL, searched_on TEXT NOT NULL CHECK(date(searched_on) IS searched_on),
        request_count INTEGER NOT NULL CHECK(request_count >= 0), listing_count INTEGER NOT NULL CHECK(listing_count >= 0)
    );
    CREATE TABLE lodging_windows (
        run_id TEXT NOT NULL REFERENCES lodging_snapshots(run_id), window_key TEXT NOT NULL, label TEXT NOT NULL,
        checkin TEXT NOT NULL, checkout TEXT NOT NULL, nights INTEGER NOT NULL CHECK(nights > 0),
        status TEXT NOT NULL CHECK(status IN ('searched','skipped_past')),
        PRIMARY KEY(run_id,window_key)
    );
    CREATE TABLE lodging_filters (
        run_id TEXT NOT NULL, window_key TEXT NOT NULL, location_id INTEGER NOT NULL, location_name TEXT NOT NULL,
        region_id TEXT NOT NULL, region_name TEXT NOT NULL, total_count INTEGER NOT NULL CHECK(total_count >= 0),
        page_count INTEGER NOT NULL CHECK(page_count >= 0),
        PRIMARY KEY(run_id,window_key,location_id),
        FOREIGN KEY(run_id,window_key) REFERENCES lodging_windows(run_id,window_key)
    );
    CREATE TABLE lodging_listings (
        run_id TEXT NOT NULL REFERENCES lodging_snapshots(run_id), lodging_id INTEGER NOT NULL CHECK(lodging_id > 0), title TEXT NOT NULL,
        category_ids TEXT NOT NULL CHECK(json_valid(category_ids) AND json_type(category_ids)='array'),
        category_names TEXT NOT NULL CHECK(json_valid(category_names) AND json_type(category_names)='array'),
        address TEXT, city TEXT, state TEXT, zip_code TEXT,
        latitude REAL CHECK(latitude IS NULL OR latitude BETWEEN -90 AND 90),
        longitude REAL CHECK(longitude IS NULL OR longitude BETWEEN -180 AND 180),
        bedrooms REAL CHECK(bedrooms IS NULL OR bedrooms >= 0), bathrooms REAL CHECK(bathrooms IS NULL OR bathrooms >= 0),
        sleeps INTEGER CHECK(sleeps IS NULL OR sleeps >= 0),
        amenities TEXT NOT NULL CHECK(json_valid(amenities) AND json_type(amenities)='array'),
        res_engine TEXT, source_location_id INTEGER, hide_rate_calendar INTEGER NOT NULL CHECK(hide_rate_calendar IN (0,1)),
        live_rates_enabled INTEGER NOT NULL CHECK(live_rates_enabled IN (0,1)),
        PRIMARY KEY(run_id,lodging_id)
    );
    CREATE TABLE lodging_search_results (
        run_id TEXT NOT NULL, window_key TEXT NOT NULL, location_id INTEGER NOT NULL, lodging_id INTEGER NOT NULL,
        position INTEGER NOT NULL CHECK(position >= 0),
        average_rate REAL CHECK(average_rate IS NULL OR average_rate >= 0), average_rate_usd REAL CHECK(average_rate_usd IS NULL OR average_rate_usd >= 0),
        los INTEGER CHECK(los IS NULL OR los >= 0), liveness INTEGER, live_rates_enabled INTEGER NOT NULL CHECK(live_rates_enabled IN (0,1)),
        min_stays TEXT CHECK(min_stays IS NULL OR json_valid(min_stays)),
        live_status TEXT NOT NULL CHECK(live_status IN ('not_requested','answered','no_answer')),
        live_average_rate_usd REAL CHECK(live_average_rate_usd IS NULL OR live_average_rate_usd >= 0), live_los INTEGER, live_liveness INTEGER,
        live_attempts INTEGER NOT NULL CHECK(live_attempts >= 0),
        PRIMARY KEY(run_id,window_key,location_id,lodging_id),
        FOREIGN KEY(run_id,window_key,location_id) REFERENCES lodging_filters(run_id,window_key,location_id),
        FOREIGN KEY(run_id,lodging_id) REFERENCES lodging_listings(run_id,lodging_id)
    );
    CREATE TABLE lodging_calendars (
        run_id TEXT NOT NULL, lodging_id INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('read','unavailable')),
        requested_from TEXT NOT NULL, requested_to TEXT NOT NULL, priced_days INTEGER NOT NULL CHECK(priced_days >= 0),
        PRIMARY KEY(run_id,lodging_id),
        FOREIGN KEY(run_id,lodging_id) REFERENCES lodging_listings(run_id,lodging_id)
    );
    CREATE TABLE lodging_rate_months (
        run_id TEXT NOT NULL, lodging_id INTEGER NOT NULL, month TEXT NOT NULL CHECK(month GLOB '[0-9][0-9][0-9][0-9]-[01][0-9]'),
        priced_days INTEGER NOT NULL CHECK(priced_days > 0), min_rate REAL NOT NULL, median_rate REAL NOT NULL, max_rate REAL NOT NULL,
        common_los INTEGER,
        PRIMARY KEY(run_id,lodging_id,month),
        FOREIGN KEY(run_id,lodging_id) REFERENCES lodging_calendars(run_id,lodging_id)
    );
    CREATE TABLE lodging_calendar_windows (
        run_id TEXT NOT NULL, lodging_id INTEGER NOT NULL, window_key TEXT NOT NULL, nights INTEGER NOT NULL CHECK(nights > 0),
        priced_nights INTEGER NOT NULL CHECK(priced_nights BETWEEN 0 AND nights), mean_rate REAL, max_los INTEGER,
        PRIMARY KEY(run_id,lodging_id,window_key),
        FOREIGN KEY(run_id,lodging_id) REFERENCES lodging_calendars(run_id,lodging_id),
        FOREIGN KEY(run_id,window_key) REFERENCES lodging_windows(run_id,window_key)
    );
    CREATE INDEX lodging_search_results_listing ON lodging_search_results(run_id,lodging_id);
"""


def seed_destination_lodging(con, profile):
    """Copy the profile's first lodging configuration and source into SQLite once; existing rows are never overwritten."""
    destination_id = profile.METADATA["id"]
    host = getattr(profile, "LODGING_CLONE_HOST", None)
    if not host or not con.execute("SELECT 1 FROM destinations WHERE id=?", (destination_id,)).fetchone():
        return
    if not con.execute("SELECT 1 FROM destination_lodging_sources WHERE destination_id=?", (destination_id,)).fetchone():
        con.execute("INSERT INTO destination_lodging_sources (destination_id,clone_host,enabled) VALUES (?,?,1)", (destination_id, host))
        con.executemany("INSERT INTO destination_lodging_locations (destination_id,source_location_name,region_id) VALUES (?,?,?)",
                        [(destination_id, name, region_id) for name, region_id in profile.LODGING_LOCATIONS.items()])
        con.executemany("""INSERT INTO destination_lodging_windows (destination_id,window_key,label,checkin,checkout,sort_order,enabled)
            VALUES (?,?,?,?,?,?,1)""", [(destination_id, key, label, checkin, checkout, order)
                                        for order, (key, label, checkin, checkout) in enumerate(profile.LODGING_WINDOWS)])
    connector = BookDirectLodgingConnector()
    sources = [dict(row) for row in con.execute("SELECT * FROM sources WHERE destination_id=?", (destination_id,))]
    if any(connector.supports(source) for source in sources):
        return
    url = f"https://{host}/"
    seed = next((seed for seed in profile.SEEDS if seed[1] == url), None)
    if seed is None:
        return
    name, url, category, notes, method = seed
    stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    con.execute("""INSERT INTO sources (id,name,url,category,region,method,cadence,notes,enabled,version,
        created_at,updated_at,destination_id,scope_region_id) VALUES (?,?,?,?,?,?,?,?,1,1,?,?,?,NULL)""",
        (uuid.uuid4().hex, name, url, category, f"Tüm {profile.METADATA['name']}", method, "Gerektiğinde", notes, stamp, stamp, destination_id))


def upgrade_v10(con):
    execute_schema(con, SCHEMA)
    seed_destination_lodging(con, DEFAULT_PROFILE)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("Konaklama migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=10")
