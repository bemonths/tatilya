CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL, region TEXT NOT NULL, method TEXT NOT NULL,
    cadence TEXT NOT NULL, notes TEXT NOT NULL, enabled INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_history (
    id INTEGER PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id),
    saved_at TEXT NOT NULL, snapshot TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
    status TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
    finished_at TEXT, result TEXT, log TEXT NOT NULL DEFAULT '[]'
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_job ON jobs(kind)
    WHERE status IN ('queued', 'running');
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY REFERENCES jobs(id), source_id TEXT NOT NULL REFERENCES sources(id),
    source_url TEXT NOT NULL, fetched_at TEXT NOT NULL, source_updated TEXT,
    parser_version TEXT NOT NULL, total_count INTEGER NOT NULL,
    included_count INTEGER NOT NULL, excluded_count INTEGER NOT NULL,
    raw_path TEXT NOT NULL, raw_sha256 TEXT NOT NULL, scope TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS beach_records (
    run_id TEXT NOT NULL REFERENCES collections(id), external_id TEXT NOT NULL,
    name TEXT NOT NULL, city TEXT NOT NULL, address TEXT NOT NULL,
    latitude REAL NOT NULL, longitude REAL NOT NULL, access_type TEXT NOT NULL,
    features TEXT NOT NULL, PRIMARY KEY(run_id, external_id)
);
PRAGMA user_version=2;
