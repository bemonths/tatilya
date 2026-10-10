"""Text runs, their sessions, versions and the chosen text in SQLite (schema 17, GÖREV-15). Files live in the folders; the rows hold what
lists, statuses, the comparison and the workflow need (the workflow reads statuses and the choice from here)."""
import json
import uuid
from datetime import datetime, timezone

RUN_LABELS = {"running": "çalışıyor", "waiting_limit": "kullanım sınırı bekleniyor", "paused": "duraklatıldı", "interrupted": "yarıda kaldı",
              "awaiting_comparison": "karşılaştırma bekliyor", "error": "hata"}
ACTIVE = ("running", "waiting_limit")
RESUMABLE = ("paused", "interrupted")
RUN_JSON = ("tones", "plan", "state")
SESSION_JSON = ("metrics", "problems")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_id():
    return uuid.uuid4().hex


def decode_run(row):
    if row is None:
        return None
    item = dict(row)
    for key in RUN_JSON:
        item[key] = json.loads(item[key]) if item[key] else ({} if key == "state" else None)
    item["status_label"] = RUN_LABELS.get(item["status"], item["status"])
    return item


def insert_run(db, *, run_id, destination_id, video_id, job_id, tones, pack_id, replan_of=None):
    stamp = now()
    with db.connect() as con:
        con.execute("""INSERT INTO text_runs (id,destination_id,video_id,job_id,status,tones,pack_id,state,replan_of,created_at,updated_at)
            VALUES (?,?,?,?,'running',?,?,'{}',?,?,?)""", (run_id, destination_id, video_id, job_id, json.dumps(tones, ensure_ascii=False), pack_id,
                                                         replan_of, stamp, stamp))


def update_run(db, run_id, **fields):
    for key in RUN_JSON:
        if key in fields and fields[key] is not None:
            fields[key] = json.dumps(fields[key], ensure_ascii=False)
    fields["updated_at"] = now()
    if fields.get("status") and fields["status"] not in ACTIVE and "finished_at" not in fields:
        fields["finished_at"] = fields["updated_at"]
    with db.connect() as con:
        con.execute(f"UPDATE text_runs SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?", (*fields.values(), run_id))


def run(db, run_id):
    with db.connect() as con:
        return decode_run(con.execute("SELECT * FROM text_runs WHERE id=?", (run_id,)).fetchone())


def runs(db, video_id):
    with db.connect() as con:
        return [decode_run(r) for r in con.execute("SELECT * FROM text_runs WHERE video_id=? ORDER BY created_at DESC, rowid DESC", (video_id,))]


def active_runs(db):
    with db.connect() as con:
        return [decode_run(r) for r in con.execute(f"SELECT * FROM text_runs WHERE status IN ({','.join('?' * len(ACTIVE))})", ACTIVE)]


def recover(db):
    """A run left running or waiting by an app that closed is "yarıda kaldı" now ("Devam" goes on with what is left)."""
    with db.connect() as con:
        con.execute(f"""UPDATE text_runs SET status='interrupted', reason='program_kapandi', reason_text=?, wait_until=NULL, updated_at=?
            WHERE status IN ({','.join('?' * len(ACTIVE))})""", ("Program kapanırken yarıda kaldı; “Devam” kalan adımları çalıştırır.", now(), *ACTIVE))
        con.execute("UPDATE text_sessions SET status='canceled', finished_at=?, error=? WHERE status='running'",
                    (now(), "Program kapanırken kesildi."))


# ---- sessions ----------------------------------------------------------------------------------------------------------------------

def decode_session(row):
    if row is None:
        return None
    item = dict(row)
    for key in SESSION_JSON:
        item[key] = json.loads(item[key]) if item[key] else ([] if key == "problems" else None)
    return item


def insert_session(db, *, session_id, text_run_id, step, tone, part, round_no, attempt, folder):
    with db.connect() as con:
        con.execute("""INSERT INTO text_sessions (id,text_run_id,step,tone,part,round,attempt,status,folder,created_at)
            VALUES (?,?,?,?,?,?,?,'running',?,?)""", (session_id, text_run_id, step, tone, part, round_no, attempt, folder, now()))


def update_session(db, identifier, **fields):
    for key in SESSION_JSON:
        if key in fields and fields[key] is not None:
            fields[key] = json.dumps(fields[key], ensure_ascii=False)
    if fields.get("status") and fields["status"] != "running" and "finished_at" not in fields:
        fields["finished_at"] = now()
    with db.connect() as con:
        con.execute(f"UPDATE text_sessions SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?", (*fields.values(), identifier))


def close_running(db, text_run_id, status, error):
    """Sessions a stopped or failed run left 'running' end with that status (nothing is left running)."""
    with db.connect() as con:
        con.execute("UPDATE text_sessions SET status=?, error=COALESCE(error, ?), finished_at=? WHERE text_run_id=? AND status='running'",
                    (status, error, now(), text_run_id))


def done_session(db, text_run_id, step, tone, part, round_no):
    """The finished session of one place of the chain (so "Devam" does not run it again)."""
    with db.connect() as con:
        row = con.execute("""SELECT * FROM text_sessions WHERE text_run_id=? AND step=? AND tone IS ? AND part IS ? AND round=? AND status='done'
            ORDER BY created_at DESC LIMIT 1""", (text_run_id, step, tone, part, round_no)).fetchone()
    return decode_session(row)


def sessions(db, text_run_id):
    with db.connect() as con:
        return [decode_session(r) for r in con.execute("SELECT * FROM text_sessions WHERE text_run_id=? ORDER BY created_at, rowid", (text_run_id,))]


def durations(db, step, limit=9):
    with db.connect() as con:
        return [r[0] for r in con.execute("""SELECT json_extract(metrics,'$.elapsed_s') FROM text_sessions WHERE step=? AND status='done'
            AND metrics IS NOT NULL ORDER BY created_at DESC LIMIT ?""", (step, limit)) if isinstance(r[0], (int, float)) and r[0] > 0]


# ---- versions and the choice -------------------------------------------------------------------------------------------------------

def decode_version(row):
    if row is None:
        return None
    item = dict(row)
    item["tokens"] = json.loads(item["tokens"]) if item["tokens"] else None
    return item


def next_number(con, video_id):
    return (con.execute("SELECT COALESCE(MAX(number),0) FROM text_versions WHERE video_id=?", (video_id,)).fetchone()[0] or 0) + 1


def insert_version(db, version):
    with db.connect() as con:
        con.execute("""INSERT INTO text_versions (id,number,text_run_id,video_id,destination_id,tone_file,tone_name,tone_sha256,folder,words,
            sentences,red,yellow,cost_usd,tokens,elapsed_s,json_sha256,pack_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            version["id"], version["number"], version["text_run_id"], version["video_id"], version["destination_id"], version["tone_file"],
            version["tone_name"], version["tone_sha256"], version["folder"], version["words"], version["sentences"], version["red"],
            version["yellow"], version.get("cost_usd"), json.dumps(version.get("tokens")) if version.get("tokens") is not None else None,
            version.get("elapsed_s"), version["json_sha256"], version.get("pack_id"), version.get("created_at") or now()))


def version(db, version_id):
    with db.connect() as con:
        return decode_version(con.execute("SELECT * FROM text_versions WHERE id=?", (version_id,)).fetchone())


def versions(db, video_id=None, text_run_id=None):
    with db.connect() as con:
        if text_run_id:
            rows = con.execute("SELECT * FROM text_versions WHERE text_run_id=? ORDER BY number", (text_run_id,))
        else:
            rows = con.execute("SELECT * FROM text_versions WHERE video_id=? ORDER BY number", (video_id,))
        return [decode_version(r) for r in rows]


def tone_usage(db):
    """{tone file: number of text versions written with it} (Settings → Tonlar)."""
    with db.connect() as con:
        return {r[0]: r[1] for r in con.execute("SELECT tone_file, COUNT(*) FROM text_versions GROUP BY tone_file")}


def select(db, video_id, version_id, note=None):
    with db.connect() as con:
        con.execute("INSERT INTO text_selections (video_id,version_id,selected_at,note) VALUES (?,?,?,?)", (video_id, version_id, now(), note))


def selection(db, video_id):
    with db.connect() as con:
        row = con.execute("SELECT * FROM text_selections WHERE video_id=? ORDER BY id DESC LIMIT 1", (video_id,)).fetchone()
    return dict(row) if row else None


def selections(db, video_id):
    with db.connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM text_selections WHERE video_id=? ORDER BY id DESC", (video_id,))]
