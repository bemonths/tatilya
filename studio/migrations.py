"""v2 -> v3: çağıranın tek transaction'ı içinde, kimlikleri koruyan migration."""
import json

from .regions import REGIONS


def execute_schema(con, sql):
    # Sabit DDL; executescript'in örtük COMMIT davranışını kullanmıyoruz.
    for statement in sql.split(";"):
        if statement.strip():
            con.execute(statement)


def upgrade_v3(con):
    execute_schema(con, """
        ALTER TABLE jobs ADD COLUMN source_id TEXT REFERENCES sources(id);
        ALTER TABLE jobs ADD COLUMN diagnostic TEXT;
        CREATE TABLE regions (id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
        CREATE TABLE entities (
            id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, canonical_name TEXT NOT NULL,
            canonical_region_id TEXT REFERENCES regions(id),
            latitude REAL CHECK(latitude BETWEEN -90 AND 90),
            longitude REAL CHECK(longitude BETWEEN -180 AND 180),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE entity_sources (
            entity_id TEXT NOT NULL REFERENCES entities(id), source_id TEXT NOT NULL REFERENCES sources(id),
            external_id TEXT NOT NULL, source_url TEXT, record_url TEXT,
            PRIMARY KEY(source_id, external_id)
        );
        CREATE INDEX entity_sources_entity ON entity_sources(entity_id);
        CREATE TABLE source_runs (
            id TEXT PRIMARY KEY, source_id TEXT REFERENCES sources(id), job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
            status TEXT NOT NULL CHECK(status IN ('queued','running','done','failed','canceled','interrupted')),
            started_at TEXT, fetched_at TEXT, finished_at TEXT, source_url TEXT,
            connector_name TEXT NOT NULL, connector_version TEXT NOT NULL,
            raw_path TEXT, raw_sha256 TEXT, source_updated TEXT,
            record_count INTEGER NOT NULL DEFAULT 0 CHECK(record_count >= 0),
            excluded_count INTEGER NOT NULL DEFAULT 0 CHECK(excluded_count >= 0),
            error_message TEXT, metadata TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(metadata))
        );
        CREATE INDEX source_runs_source_status ON source_runs(source_id,status);
    """)
    con.executemany("INSERT INTO regions VALUES (?,?)", REGIONS)
    old_runs = {row["id"]: dict(row) for row in con.execute("SELECT * FROM collections")}
    for job in con.execute("SELECT * FROM jobs WHERE kind='beach_collection' OR id IN (SELECT id FROM collections) ORDER BY rowid").fetchall():
        old = old_runs.get(job["id"])
        metadata = {"migrated_from": 2}
        if old:
            metadata.update(total_count=old["total_count"], scope=old["scope"])
            con.execute("UPDATE jobs SET source_id=? WHERE id=?", (old["source_id"], job["id"]))
        else:
            metadata["source_identity_unknown"] = True
            metadata["legacy_data_missing"] = True
        con.execute("""INSERT INTO source_runs
            (id,source_id,job_id,status,started_at,fetched_at,finished_at,source_url,connector_name,
             connector_version,raw_path,raw_sha256,source_updated,record_count,excluded_count,error_message,metadata)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                job["id"], old["source_id"] if old else None, job["id"], "done" if old else job["status"],
                None, old["fetched_at"] if old else None, job["finished_at"] or (old["fetched_at"] if old else None),
                old["source_url"] if old else None, "south-walton-beaches",
                old["parser_version"] if old else "legacy-unknown", old["raw_path"] if old else None,
                old["raw_sha256"] if old else None, old["source_updated"] if old else None,
                old["included_count"] if old else 0, old["excluded_count"] if old else 0,
                job["message"] if not old and job["status"] in ("failed", "canceled", "interrupted") else None,
                json.dumps(metadata, ensure_ascii=False)))
    execute_schema(con, """
        CREATE TABLE beach_records_v3 (
            run_id TEXT NOT NULL REFERENCES source_runs(id), external_id TEXT NOT NULL,
            name TEXT NOT NULL, city TEXT NOT NULL, address TEXT NOT NULL,
            latitude REAL NOT NULL, longitude REAL NOT NULL, access_type TEXT NOT NULL,
            features TEXT NOT NULL, source_region_text TEXT NOT NULL,
            canonical_region_id TEXT REFERENCES regions(id), PRIMARY KEY(run_id,external_id)
        );
        INSERT INTO beach_records_v3 SELECT run_id,external_id,name,city,address,latitude,longitude,
            access_type,features,city,NULL FROM beach_records;
        DROP TABLE beach_records;
        ALTER TABLE beach_records_v3 RENAME TO beach_records;
        DROP TABLE collections;
        CREATE VIEW collections AS SELECT id,source_id,source_url,fetched_at,source_updated,
            connector_version AS parser_version, json_extract(metadata,'$.total_count') AS total_count,
            record_count AS included_count,excluded_count,raw_path,raw_sha256,
            json_extract(metadata,'$.scope') AS scope
            FROM source_runs WHERE status='done' AND connector_name='south-walton-beaches'
            AND source_id IS NOT NULL AND fetched_at IS NOT NULL;
        DROP INDEX one_active_job;
        UPDATE jobs SET kind='source_collection' WHERE kind='beach_collection';
        CREATE UNIQUE INDEX one_active_job ON jobs(kind) WHERE source_id IS NULL AND status IN ('queued','running');
        CREATE UNIQUE INDEX one_active_source_job ON jobs(source_id) WHERE source_id IS NOT NULL AND status IN ('queued','running');
        PRAGMA user_version=3;
    """)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("Migration sırasında ilişki bütünlüğü kontrolü başarısız oldu.")


def upgrade_v4(con):
    """Add weather tables and refresh untouched seed defaults; caller owns transaction/backup."""
    execute_schema(con, """
        CREATE TABLE weather_locations (
            run_id TEXT NOT NULL REFERENCES source_runs(id), anchor_key TEXT NOT NULL,
            label TEXT NOT NULL, source_beach_external_id TEXT NOT NULL, source_beach_name TEXT NOT NULL,
            latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90),
            longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
            cwa TEXT NOT NULL, grid_x INTEGER NOT NULL, grid_y INTEGER NOT NULL, time_zone TEXT NOT NULL,
            forecast_url TEXT NOT NULL, forecast_hourly_url TEXT NOT NULL, forecast_grid_data_url TEXT,
            forecast_zone_url TEXT, county_url TEXT, observation_stations_url TEXT,
            PRIMARY KEY(run_id,anchor_key)
        );
        CREATE TABLE weather_forecast_periods (
            run_id TEXT NOT NULL, anchor_key TEXT NOT NULL,
            forecast_kind TEXT NOT NULL CHECK(forecast_kind IN ('period','hourly')),
            external_id TEXT NOT NULL, number INTEGER, name TEXT,
            start_time TEXT NOT NULL, end_time TEXT NOT NULL, is_daytime INTEGER CHECK(is_daytime IN (0,1)),
            temperature REAL, temperature_unit TEXT, temperature_trend TEXT,
            precipitation_probability REAL CHECK(precipitation_probability BETWEEN 0 AND 100),
            relative_humidity REAL CHECK(relative_humidity BETWEEN 0 AND 100), dewpoint REAL, dewpoint_unit TEXT,
            wind_speed TEXT, wind_direction TEXT, icon_url TEXT, short_forecast TEXT NOT NULL, detailed_forecast TEXT,
            PRIMARY KEY(run_id,external_id), UNIQUE(run_id,anchor_key,forecast_kind,start_time),
            FOREIGN KEY(run_id,anchor_key) REFERENCES weather_locations(run_id,anchor_key)
        );
        CREATE TABLE weather_alerts (
            run_id TEXT NOT NULL REFERENCES source_runs(id), alert_id TEXT NOT NULL,
            event TEXT NOT NULL, headline TEXT, area_desc TEXT, severity TEXT, certainty TEXT, urgency TEXT,
            effective TEXT, onset TEXT, expires TEXT, ends TEXT, status TEXT, message_type TEXT,
            description TEXT, instruction TEXT, PRIMARY KEY(run_id,alert_id)
        );
        CREATE TABLE weather_alert_anchors (
            run_id TEXT NOT NULL, alert_id TEXT NOT NULL, anchor_key TEXT NOT NULL,
            PRIMARY KEY(run_id,alert_id,anchor_key),
            FOREIGN KEY(run_id,alert_id) REFERENCES weather_alerts(run_id,alert_id),
            FOREIGN KEY(run_id,anchor_key) REFERENCES weather_locations(run_id,anchor_key)
        );
        PRAGMA user_version=4;
    """)
    # Frozen v3 defaults: exact matches only, independent notes/method conditions.
    con.execute("UPDATE sources SET notes=? WHERE url=? AND notes=?", (
        "30A koridorundaki batı, orta ve doğu örnek noktaları için NWS tahminleri ve aktif hava uyarıları. Forecast, saatlik forecast ve aktif alert verileri api.weather.gov üzerinden toplanır.",
        "https://www.weather.gov/",
        "Hava verisi için başlangıç kaynağı. Bölge koordinatları ve veri uçları sonraki aşamada belirlenecek."))
    con.executemany("UPDATE sources SET method=? WHERE url=? AND method='Belirlenecek'", (
        ("API", "https://www.weather.gov/"),
        ("JSON", "https://www.visitsouthwalton.com/beach-bay-access-locations/")))
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("Hava migration ilişki bütünlüğü kontrolü başarısız oldu.")
