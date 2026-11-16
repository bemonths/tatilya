"""Schema 20 → 21 (GÖREV-21): the project layer and the video layer.

`videos` is rebuilt (ids and every existing column kept): a video can now be opened without a title ("Yeni video"; the title is chosen
or written in its first step), so the title, the region, the family and the link to the chosen candidate (`run_id`, `candidate`) may be
empty; `name` is the optional working name, `archived_at` takes a video off the list ("Arşive kaldır"; nothing is deleted).
Title runs and their candidates stay tied to the destination (`claude_runs.destination_id`); a video only points at the candidate it uses.

`video_steps`: the stored status of each of a video's steps (`studio/workflow.py`): waiting, ready, running, awaiting_approval, approved,
done, error, stale; the reason it went stale and the status it had before; the user's note (a rejection, or the correction note the next
run gives to Claude); `ref` (the record the step's output is: a pack, a text run); `inputs` (what a cleared staleness was cleared for).
`video_step_log`: the status log of a video, one Turkish sentence per change or decision.
`project_state`: the video that is open in a destination (remembered for the next start).

Existing videos get their steps from their records (`workflow.seed`): a video with a title has its first step approved; a pack: the
second step done; a text run with a plan: the plan approved (the old chain wrote on without an approval); versions: the writing done; a
chosen text: the check approved. The caller owns the backup and the single transaction.
"""
from .migrations import execute_schema

SCHEMA = """
    CREATE TABLE videos_v21 (
        id TEXT PRIMARY KEY, destination_id TEXT NOT NULL REFERENCES destinations(id),
        name TEXT CHECK(name IS NULL OR length(name) BETWEEN 1 AND 120),
        region_id TEXT REFERENCES regions(id), region_name TEXT,
        title_en TEXT CHECK(title_en IS NULL OR length(title_en) BETWEEN 1 AND 100),
        title_tr TEXT CHECK(title_tr IS NULL OR length(title_tr) > 0),
        family TEXT, analysis TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(analysis) AND json_type(analysis)='object'),
        template_key TEXT, params TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(params) AND json_type(params)='object'),
        status TEXT NOT NULL CHECK(status IN ('yeni','baslik_secildi','paket_hazir')), created_at TEXT NOT NULL,
        run_id TEXT REFERENCES claude_runs(id), candidate INTEGER CHECK(candidate IS NULL OR candidate >= 0),
        proposed_title_en TEXT, proposed_title_tr TEXT,
        user_edited INTEGER NOT NULL DEFAULT 0 CHECK(user_edited IN (0,1)),
        archived_at TEXT,
        CHECK((run_id IS NULL) = (candidate IS NULL)),
        CHECK((title_en IS NULL) = (title_tr IS NULL)),
        UNIQUE(run_id, candidate)
    );
    INSERT INTO videos_v21 (id,destination_id,region_id,region_name,title_en,title_tr,family,analysis,template_key,params,status,created_at,
        run_id,candidate,proposed_title_en,proposed_title_tr,user_edited)
        SELECT id,destination_id,region_id,region_name,title_en,title_tr,family,analysis,template_key,params,status,created_at,
        run_id,candidate,proposed_title_en,proposed_title_tr,user_edited FROM videos;
    DROP INDEX videos_destination;
    DROP TABLE videos;
    ALTER TABLE videos_v21 RENAME TO videos;
    CREATE INDEX videos_destination ON videos(destination_id, created_at);
    CREATE TABLE video_steps (
        video_id TEXT NOT NULL REFERENCES videos(id), step TEXT NOT NULL CHECK(length(step) > 0),
        status TEXT NOT NULL CHECK(status IN ('waiting','ready','running','awaiting_approval','approved','done','error','stale')),
        status_before_stale TEXT CHECK(status_before_stale IS NULL OR status_before_stale IN
            ('waiting','ready','running','awaiting_approval','approved','done','error')),
        stale_reason TEXT, note TEXT, error TEXT, ref TEXT, inputs TEXT, updated_at TEXT NOT NULL,
        PRIMARY KEY(video_id, step)
    );
    CREATE TABLE video_step_log (
        id INTEGER PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(id), step TEXT, at TEXT NOT NULL,
        text TEXT NOT NULL CHECK(length(text) > 0)
    );
    CREATE INDEX video_step_log_video ON video_step_log(video_id, id);
    CREATE TABLE project_state (
        destination_id TEXT PRIMARY KEY REFERENCES destinations(id), open_video_id TEXT REFERENCES videos(id), updated_at TEXT NOT NULL
    )
"""


def upgrade_v21(con):
    from . import workflow
    execute_schema(con, SCHEMA)
    for row in con.execute("SELECT id FROM videos ORDER BY created_at, rowid").fetchall():
        workflow.seed(con, row[0], note="Taşıma (şema 21): adım durumları videonun kayıtlarından çıkarıldı.")
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v21 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=21")
