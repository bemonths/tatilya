"""v6 -> v7: neighborhood snapshots and the 30A neighborhood source.

The caller owns the backup and the single transaction; any failure rolls everything back.
Existing sources, history, runs, domain snapshots and raw files are not modified.
"""
import uuid
from datetime import datetime, timezone

from .destinations import DEFAULT_PROFILE
from .migrations import execute_schema
from .sources.neighborhoods import SOURCE_URL, NeighborhoodsConnector


def upgrade_v7(con):
    execute_schema(con, """
        CREATE TABLE neighborhood_records (
            run_id TEXT NOT NULL REFERENCES source_runs(id), external_id TEXT NOT NULL,
            name TEXT NOT NULL, permalink TEXT NOT NULL, page_url TEXT NOT NULL,
            canonical_region_id TEXT NOT NULL REFERENCES regions(id), summary TEXT,
            latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90),
            longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
            tags TEXT NOT NULL CHECK(json_valid(tags) AND json_type(tags)='array'),
            source_modified TEXT, page_intro TEXT,
            PRIMARY KEY(run_id,external_id), UNIQUE(run_id,canonical_region_id)
        );
        CREATE INDEX neighborhood_region_lookup ON neighborhood_records(canonical_region_id,run_id);
    """)
    profile = DEFAULT_PROFILE
    destination_id = profile.METADATA["id"]
    connector = NeighborhoodsConnector()
    if con.execute("SELECT 1 FROM destinations WHERE id=?", (destination_id,)).fetchone():
        existing = [row for row in con.execute("SELECT * FROM sources WHERE destination_id=?", (destination_id,))
                    if connector.supports(dict(row))]
        if not existing:
            name, url, category, notes, method = next(seed for seed in profile.SEEDS if seed[1] == SOURCE_URL)
            stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            con.execute("""INSERT INTO sources (id,name,url,category,region,method,cadence,notes,enabled,version,
                created_at,updated_at,destination_id,scope_region_id) VALUES (?,?,?,?,?,?,?,?,1,1,?,?,?,NULL)""",
                (uuid.uuid4().hex, name, url, category, f"Tüm {profile.METADATA['name']}", method, "Haftalık", notes,
                 stamp, stamp, destination_id))
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("Mahalle migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=7")
