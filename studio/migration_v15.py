"""v14 -> v15 (GÖREV-13): Claude runs, video records and the link from an evidence pack to the video it was made for.

`claude_runs`: one row per Claude run of a step (folder `claude/<preparation or video id>/<step>/<run id>/` under the data folder; nothing is
deleted, a correction is a new run with `correction_of`). `videos`: a title the user chose, with the whole analysis of the chosen candidate
(its evidence kept with values and the pack it came from). `evidence_packs.video_id`: the video a pack was produced for.
The caller owns the backup and the single transaction; nothing existing changes.
"""
from .migrations import execute_schema

SCHEMA = """
    CREATE TABLE claude_runs (
        id TEXT PRIMARY KEY, destination_id TEXT NOT NULL REFERENCES destinations(id),
        step TEXT NOT NULL CHECK(length(step) > 0), scope_id TEXT NOT NULL CHECK(length(scope_id) > 0),
        job_id TEXT REFERENCES jobs(id), correction_of TEXT REFERENCES claude_runs(id),
        status TEXT NOT NULL CHECK(status IN ('running','awaiting_approval','approved','rejected','error')),
        params TEXT NOT NULL CHECK(json_valid(params) AND json_type(params)='object'),
        folder TEXT NOT NULL, created_at TEXT NOT NULL, finished_at TEXT,
        model TEXT, effort TEXT, claude_version TEXT, session_id TEXT,
        metrics TEXT CHECK(metrics IS NULL OR json_valid(metrics)),
        problems TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(problems) AND json_type(problems)='array'),
        error TEXT, decision_note TEXT, decided_at TEXT
    );
    CREATE INDEX claude_runs_destination ON claude_runs(destination_id, step, created_at);
    CREATE UNIQUE INDEX one_running_claude ON claude_runs(status) WHERE status='running';
    CREATE TABLE videos (
        id TEXT PRIMARY KEY, destination_id TEXT NOT NULL REFERENCES destinations(id),
        region_id TEXT REFERENCES regions(id), region_name TEXT NOT NULL,
        title_en TEXT NOT NULL CHECK(length(title_en) BETWEEN 1 AND 100), title_tr TEXT NOT NULL CHECK(length(title_tr) > 0),
        family TEXT NOT NULL, analysis TEXT NOT NULL CHECK(json_valid(analysis) AND json_type(analysis)='object'),
        template_key TEXT, params TEXT NOT NULL CHECK(json_valid(params) AND json_type(params)='object'),
        status TEXT NOT NULL CHECK(status IN ('baslik_secildi','paket_hazir')), created_at TEXT NOT NULL,
        run_id TEXT NOT NULL REFERENCES claude_runs(id), candidate INTEGER NOT NULL CHECK(candidate >= 0),
        UNIQUE(run_id, candidate)
    );
    CREATE INDEX videos_destination ON videos(destination_id, created_at);
    ALTER TABLE evidence_packs ADD COLUMN video_id TEXT REFERENCES videos(id);
"""


def upgrade_v15(con):
    execute_schema(con, SCHEMA)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v15 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=15")
