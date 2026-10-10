"""v15 -> v16 (GÖREV-14): Claude usage measurements, the progress details of a job, the user's edit of a chosen title and the reading method
that worked for a host.

`claude_usage`: every `rate_limit_event` a Claude run streamed (and every "Yenile" call's), with its time: the 5-hour and weekly windows'
utilization (0–1, as Claude Code gives it) and reset times (epoch seconds), and the whole `rate_limit_info` as it came. `job_progress`:
what the job panel needs to draw a Claude run's bar (stage, start of Claude's part, the expected duration and its basis; a table of its own
so the rows of `jobs` stay as they were). `videos`: the proposed title kept next to the title the user edited (`user_edited`); existing videos were not edited, so their proposal is their title.
`browser_hosts.method`: which way of reading worked last for a host that refused direct requests (`eklenti`: the user's own Chrome through
the extension, `tarayici`: the program's own browser, `dogrudan`: a direct request again). The caller owns the backup and the single
transaction; nothing existing changes.
"""
from .migrations import execute_schema

SCHEMA = """
    CREATE TABLE claude_usage (
        id INTEGER PRIMARY KEY, measured_at TEXT NOT NULL,
        source TEXT NOT NULL CHECK(source IN ('calisma','yenile')), run_id TEXT REFERENCES claude_runs(id),
        five_hour REAL CHECK(five_hour IS NULL OR five_hour >= 0), five_hour_resets_at INTEGER,
        seven_day REAL CHECK(seven_day IS NULL OR seven_day >= 0), seven_day_resets_at INTEGER,
        status TEXT, info TEXT NOT NULL CHECK(json_valid(info) AND json_type(info)='object')
    );
    CREATE INDEX claude_usage_time ON claude_usage(measured_at);
    CREATE TABLE job_progress (
        job_id TEXT PRIMARY KEY REFERENCES jobs(id), info TEXT NOT NULL CHECK(json_valid(info) AND json_type(info)='object')
    );
    ALTER TABLE videos ADD COLUMN proposed_title_en TEXT;
    ALTER TABLE videos ADD COLUMN proposed_title_tr TEXT;
    ALTER TABLE videos ADD COLUMN user_edited INTEGER NOT NULL DEFAULT 0 CHECK(user_edited IN (0,1));
    UPDATE videos SET proposed_title_en=title_en, proposed_title_tr=title_tr;
    ALTER TABLE browser_hosts ADD COLUMN method TEXT CHECK(method IS NULL OR method IN ('dogrudan','eklenti','tarayici'));
    ALTER TABLE browser_hosts ADD COLUMN method_at TEXT;
"""


def upgrade_v16(con):
    execute_schema(con, SCHEMA)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v16 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=16")
