"""v16 -> v17 (GÖREV-15): the video text — text runs, their Claude sessions, the versions they write and the user's choice.

`text_runs`: a text run of a video (one plan, one or more tones; the job panel shows it as one job). Statuses: running, waiting_limit
(waiting for Claude's usage limit; it goes on by itself), paused (stopped by the user, an error of a step, or "Plandan sonra dur"),
interrupted (the app closed while it ran), awaiting_comparison (every tone written), error. `tones` lists the tones asked for ({dosya, ad});
`plan` is the final plan; `state` holds where the chain is (plan rounds, finished steps per tone) so "Devam" does not run finished steps again.
`text_sessions`: one row per Claude session of the chain (its folder `claude/<video id>/<step>/<session id>/` is the usual run folder).
`text_versions`: a written text of one tone (its files under `metin/<video id>/surumler/<number>/`); nothing is deleted.
`text_selections`: "Bu tonla devam et"; the newest row of a video is its chosen text, older rows stay as the record of earlier choices.
The caller owns the backup and the single transaction; nothing existing changes.
"""
from .migrations import execute_schema

SCHEMA = """
    CREATE TABLE text_runs (
        id TEXT PRIMARY KEY, destination_id TEXT NOT NULL REFERENCES destinations(id), video_id TEXT NOT NULL REFERENCES videos(id),
        job_id TEXT REFERENCES jobs(id),
        status TEXT NOT NULL CHECK(status IN ('running','waiting_limit','paused','interrupted','awaiting_comparison','error')),
        tones TEXT NOT NULL CHECK(json_valid(tones) AND json_type(tones)='array'),
        pack_id TEXT REFERENCES evidence_packs(id),
        plan TEXT CHECK(plan IS NULL OR json_valid(plan)),
        state TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(state) AND json_type(state)='object'),
        reason TEXT, reason_text TEXT, wait_until TEXT, replan_of TEXT REFERENCES text_runs(id),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, finished_at TEXT
    );
    CREATE INDEX text_runs_video ON text_runs(video_id, created_at);
    CREATE TABLE text_sessions (
        id TEXT PRIMARY KEY, text_run_id TEXT NOT NULL REFERENCES text_runs(id), step TEXT NOT NULL CHECK(length(step) > 0),
        tone TEXT, part TEXT, round INTEGER NOT NULL DEFAULT 1, attempt INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL CHECK(status IN ('running','done','invalid','failed','transient','limit','canceled')),
        folder TEXT NOT NULL, model TEXT, effort TEXT, claude_version TEXT, session_id TEXT,
        metrics TEXT CHECK(metrics IS NULL OR json_valid(metrics)),
        problems TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(problems) AND json_type(problems)='array'),
        error TEXT, created_at TEXT NOT NULL, finished_at TEXT
    );
    CREATE INDEX text_sessions_run ON text_sessions(text_run_id, step, tone, part);
    CREATE TABLE text_versions (
        id TEXT PRIMARY KEY, number INTEGER NOT NULL CHECK(number >= 1), text_run_id TEXT NOT NULL REFERENCES text_runs(id),
        video_id TEXT NOT NULL REFERENCES videos(id), destination_id TEXT NOT NULL REFERENCES destinations(id),
        tone_file TEXT NOT NULL, tone_name TEXT NOT NULL, tone_sha256 TEXT NOT NULL, folder TEXT NOT NULL,
        words INTEGER NOT NULL, sentences INTEGER NOT NULL, red INTEGER NOT NULL, yellow INTEGER NOT NULL,
        cost_usd REAL, tokens TEXT CHECK(tokens IS NULL OR json_valid(tokens)), elapsed_s REAL, json_sha256 TEXT NOT NULL,
        pack_id TEXT REFERENCES evidence_packs(id), created_at TEXT NOT NULL,
        UNIQUE(video_id, number)
    );
    CREATE INDEX text_versions_run ON text_versions(text_run_id, created_at);
    CREATE TABLE text_selections (
        id INTEGER PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(id), version_id TEXT NOT NULL REFERENCES text_versions(id),
        selected_at TEXT NOT NULL, note TEXT
    );
    CREATE INDEX text_selections_video ON text_selections(video_id, id);
"""


def upgrade_v17(con):
    execute_schema(con, SCHEMA)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v17 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=17")
