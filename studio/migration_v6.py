"""Preserve v5 IDs, history and raw artifacts in one caller-owned transaction.

The caller disables foreign_keys before BEGIN for SQLite's table rebuild protocol,
then runs foreign_key_check before commit and re-enables enforcement afterwards.
"""
from datetime import datetime, timezone
from .destinations import DEFAULT_PROFILE
from .migrations import execute_schema


def upgrade_v6(con):
    profile = DEFAULT_PROFILE
    destination_id = profile.METADATA['id']
    stamp = datetime.now(timezone.utc).isoformat()
    execute_schema(con, """
        CREATE TABLE destinations (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, subtitle TEXT,
            enabled INTEGER NOT NULL CHECK(enabled IN (0,1)), sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE regions_v6 (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            destination_id TEXT NOT NULL REFERENCES destinations(id), sort_order INTEGER NOT NULL DEFAULT 0,
            UNIQUE(destination_id,name), UNIQUE(destination_id,id)
        );
        CREATE TABLE sources_v6 (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL,
            category TEXT NOT NULL, region TEXT NOT NULL, method TEXT NOT NULL,
            cadence TEXT NOT NULL, notes TEXT NOT NULL, enabled INTEGER NOT NULL,
            version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            destination_id TEXT NOT NULL REFERENCES destinations(id), scope_region_id TEXT,
            UNIQUE(destination_id,url),
            FOREIGN KEY(destination_id,scope_region_id) REFERENCES regions(destination_id,id)
        );
        CREATE TABLE destination_weather_anchors (
            destination_id TEXT NOT NULL REFERENCES destinations(id), anchor_key TEXT NOT NULL,
            label TEXT NOT NULL, latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90),
            longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
            provenance_external_id TEXT, provenance_name TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
            PRIMARY KEY(destination_id,anchor_key)
        );
    """)
    con.execute('INSERT INTO destinations VALUES (?,?,?,1,0,?,?)',
                (destination_id,profile.METADATA['name'],profile.METADATA['subtitle'],stamp,stamp))
    con.execute('INSERT INTO regions_v6 SELECT id,name,?,rowid FROM regions',(destination_id,))
    con.execute('INSERT INTO sources_v6 SELECT *,?,NULL FROM sources',(destination_id,))
    # Keep referenced names unchanged; never rename the old parent tables.
    con.execute('DROP TABLE sources')
    con.execute('ALTER TABLE sources_v6 RENAME TO sources')
    con.execute('DROP TABLE regions')
    con.execute('ALTER TABLE regions_v6 RENAME TO regions')
    con.execute('''UPDATE sources SET scope_region_id=(SELECT id FROM regions
        WHERE regions.destination_id=sources.destination_id AND regions.name=sources.region)''')
    con.execute('DROP VIEW collections')
    for table in ('jobs','source_runs','entities'):
        con.execute(f'ALTER TABLE {table} ADD COLUMN destination_id TEXT REFERENCES destinations(id)')
        if table in ('jobs','source_runs'):
            con.execute(f'''UPDATE {table} SET destination_id=COALESCE(
                (SELECT destination_id FROM sources WHERE sources.id={table}.source_id),?)''',(destination_id,))
        else:
            con.execute(f'UPDATE {table} SET destination_id=?',(destination_id,))
        # SQLite cannot add NOT NULL FK columns to populated tables. Rebuild from
        # their original DDL, preserving every field, FK, index and rowid order.
        ddl=con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()[0]
        indexes=con.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",(table,)).fetchall()
        ddl=ddl.replace('destination_id TEXT REFERENCES','destination_id TEXT NOT NULL REFERENCES')
        if table == 'entities':
            end=ddl.rfind(')')
            ddl=ddl[:end]+', FOREIGN KEY(destination_id,canonical_region_id) REFERENCES regions(destination_id,id)'+ddl[end:]
        ddl=ddl.replace(f'CREATE TABLE {table}',f'CREATE TABLE {table}_v6',1)
        con.execute(ddl)
        con.execute(f'INSERT INTO {table}_v6 SELECT * FROM {table} ORDER BY rowid')
        con.execute(f'DROP TABLE {table}')
        con.execute(f'ALTER TABLE {table}_v6 RENAME TO {table}')
        for index in indexes: con.execute(index[0])
    execute_schema(con, """
        DROP INDEX one_active_job;
        CREATE UNIQUE INDEX one_active_job ON jobs(destination_id,kind)
            WHERE source_id IS NULL AND status IN ('queued','running');
        CREATE INDEX jobs_destination ON jobs(destination_id,created_at);
        CREATE INDEX source_runs_destination_status ON source_runs(destination_id,status);
        CREATE INDEX entities_destination_name ON entities(destination_id,canonical_name);
        CREATE VIEW collections AS SELECT id,source_id,source_url,fetched_at,source_updated,
            connector_version AS parser_version,json_extract(metadata,'$.total_count') AS total_count,
            record_count AS included_count,excluded_count,raw_path,raw_sha256,
            json_extract(metadata,'$.scope') AS scope,destination_id FROM source_runs
            WHERE status='done' AND connector_name='south-walton-beaches'
            AND source_id IS NOT NULL AND fetched_at IS NOT NULL;
    """)
    for order,anchor in enumerate(profile.ANCHORS):
        con.execute('INSERT INTO destination_weather_anchors VALUES (?,?,?,?,?,?,?,?,1)',(
            destination_id,anchor['anchor_key'],anchor['label'],anchor['latitude'],anchor['longitude'],
            anchor['source_beach_external_id'],anchor['source_beach_name'],order))
    if con.execute('PRAGMA foreign_key_check').fetchone():
        raise RuntimeError('Destinasyon migration ilişki bütünlüğü kontrolü başarısız oldu.')
    con.execute('PRAGMA user_version=6')
