"""Claude runs and video records in SQLite (schema 15, GÖREV-13). The run's files live in its folder; the row holds what lists and decisions
need. Statuses: running, awaiting_approval, approved (at least one title chosen), rejected, error."""
import json
import uuid
from datetime import datetime, timezone

from ..database import Conflict
from .settings import effort_label, model_label

STATUS_LABELS = {"running": "çalışıyor", "awaiting_approval": "onay bekliyor", "approved": "seçildi", "rejected": "reddedildi", "error": "hata"}
VIDEO_STATUS_LABELS = {"yeni": "başlık seçilmedi", "baslik_secildi": "başlık seçildi", "paket_hazir": "kanıt paketi hazır"}
CANCELED = "İş iptal edildi; Claude durduruldu."      # runner.CANCELED_MESSAGE: a canceled run is recorded as "iptal edildi"
INTERRUPTED = "Uygulama kapanırken yarıda kaldı."
JSON_FIELDS = ("params", "metrics", "problems")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_id():
    return uuid.uuid4().hex


def decode_run(row):
    if row is None:
        return None
    item = dict(row)
    for key in JSON_FIELDS:
        item[key] = json.loads(item[key]) if item[key] else ([] if key == "problems" else None)
    item["canceled"] = item["status"] == "error" and item.get("error") == CANCELED
    item["status_label"] = "iptal edildi" if item["canceled"] else STATUS_LABELS.get(item["status"], item["status"])
    item["model_label"], item["effort_label"] = model_label(item["model"] or ""), effort_label(item["effort"] or "")
    return item


def insert_run(con, *, run_id, destination_id, step, scope_id, job_id, params, folder, correction_of=None):
    try:
        con.execute("""INSERT INTO claude_runs (id,destination_id,step,scope_id,job_id,correction_of,status,params,folder,created_at)
            VALUES (?,?,?,?,?,?,'running',?,?,?)""", (run_id, destination_id, step, scope_id, job_id, correction_of,
                                                     json.dumps(params, ensure_ascii=False), folder, now()))
    except Exception as exc:
        if "one_running_claude" in str(exc) or "UNIQUE" in str(exc):
            raise Conflict("Bir Claude çalışması zaten sürüyor; bitmesini bekleyin.") from exc
        raise


def update_run(db, run_id, **fields):
    for key in JSON_FIELDS:
        if key in fields and fields[key] is not None:
            fields[key] = json.dumps(fields[key], ensure_ascii=False)
    if fields.get("status") and fields["status"] != "running" and "finished_at" not in fields:
        fields["finished_at"] = now()
    with db.connect() as con:
        con.execute(f"UPDATE claude_runs SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?", (*fields.values(), run_id))


def run(db, run_id):
    with db.connect() as con:
        return decode_run(con.execute("SELECT * FROM claude_runs WHERE id=?", (run_id,)).fetchone())


def runs(db, destination_id, step=None):
    with db.connect() as con:
        return [decode_run(r) for r in con.execute("""SELECT * FROM claude_runs WHERE destination_id=? AND (? IS NULL OR step=?)
            ORDER BY created_at DESC, rowid DESC""", (destination_id, step, step))]


def recover(db):
    """A run left 'running' by an app that closed is an error now (its job is already 'interrupted')."""
    with db.connect() as con:
        con.execute("UPDATE claude_runs SET status='error', error=?, finished_at=? WHERE status='running'", (INTERRUPTED, now()))


def decode_video(row):
    if row is None:
        return None
    item = dict(row)
    item["analysis"] = json.loads(item["analysis"])
    item["params"] = json.loads(item["params"])
    item["user_edited"] = bool(item.get("user_edited"))
    item["status_label"] = VIDEO_STATUS_LABELS.get(item["status"], item["status"])
    return item


USED = "Bu başlık başka bir videoda kullanılıyor."


def insert_video(con, video):
    """A new video: with the candidate it was opened with (topic bank), or empty ("Yeni video": only an optional working name)."""
    titled = bool(video.get("title_en"))
    try:
        con.execute("""INSERT INTO videos (id,destination_id,name,region_id,region_name,title_en,title_tr,family,analysis,template_key,params,status,
            created_at,run_id,candidate,proposed_title_en,proposed_title_tr,user_edited) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            video["id"], video["destination_id"], video.get("name"), video.get("region_id"), video.get("region_name"), video.get("title_en"),
            video.get("title_tr"), video.get("family"), json.dumps(video.get("analysis") or {}, ensure_ascii=False), video.get("template_key"),
            json.dumps(video.get("params") or {}, ensure_ascii=False), "baslik_secildi" if titled else "yeni", now(),
            video.get("run_id"), video.get("candidate"), video.get("proposed_title_en", video.get("title_en")),
            video.get("proposed_title_tr", video.get("title_tr")), 1 if video.get("user_edited") else 0))
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise Conflict(USED) from exc
        raise


TITLE_FIELDS = ("region_id", "region_name", "title_en", "title_tr", "family", "template_key", "run_id", "candidate", "proposed_title_en",
                "proposed_title_tr")


def set_video_title(con, video_id, video):
    """The candidate an existing video uses from now on (its first step: chosen from the bank or from its own evaluation)."""
    try:
        con.execute(f"""UPDATE videos SET {', '.join(f'{k}=?' for k in TITLE_FIELDS)}, analysis=?, params=?, user_edited=?, status='baslik_secildi'
            WHERE id=?""", (*(video.get(k) for k in TITLE_FIELDS), json.dumps(video.get("analysis") or {}, ensure_ascii=False),
                            json.dumps(video.get("params") or {}, ensure_ascii=False), 1 if video.get("user_edited") else 0, video_id))
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise Conflict(USED) from exc
        raise


def clear_video_title(con, video_id):
    """The video no longer uses a candidate (rejected, or a correction was asked for): the candidate is free in the bank again."""
    con.execute(f"""UPDATE videos SET {', '.join(f'{k}=NULL' for k in TITLE_FIELDS)}, analysis='{{}}', params='{{}}', user_edited=0, status='yeni'
        WHERE id=?""", (video_id,))


def set_archived(db, video_id, archived):
    with db.connect() as con:
        con.execute("UPDATE videos SET archived_at=? WHERE id=?", (now() if archived else None, video_id))


def open_video(db, destination_id):
    with db.connect() as con:
        row = con.execute("SELECT open_video_id FROM project_state WHERE destination_id=?", (destination_id,)).fetchone()
    return row[0] if row else None


def set_open_video(db, destination_id, video_id):
    with db.connect() as con:
        con.execute("""INSERT INTO project_state (destination_id,open_video_id,updated_at) VALUES (?,?,?)
            ON CONFLICT(destination_id) DO UPDATE SET open_video_id=excluded.open_video_id, updated_at=excluded.updated_at""",
                    (destination_id, video_id, now()))


def used_candidates(db, destination_id):
    """{(run id, candidate): video} of the candidates a video uses ("kullanıldı")."""
    with db.connect() as con:
        return {(r["run_id"], r["candidate"]): {"id": r["id"], "ad": r["title_tr"] or r["name"] or "Adsız video", "arsivde": bool(r["archived_at"])}
                for r in con.execute("SELECT id,run_id,candidate,title_tr,name,archived_at FROM videos WHERE destination_id=? AND run_id IS NOT NULL",
                                     (destination_id,))}


def videos(db, destination_id):
    with db.connect() as con:
        items = [decode_video(r) for r in con.execute("SELECT * FROM videos WHERE destination_id=? ORDER BY created_at DESC, rowid DESC",
                                                      (destination_id,))]
        packs = {}
        for row in con.execute("""SELECT id,video_id,created_at,markdown_sha256,json_sha256 FROM evidence_packs WHERE video_id IS NOT NULL
                ORDER BY created_at DESC, rowid DESC"""):
            packs.setdefault(row["video_id"], []).append(dict(row))
    return [{**v, "packs": packs.get(v["id"], [])} for v in items]


def video(db, video_id):
    with db.connect() as con:
        return decode_video(con.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone())


def set_video_status(db, video_id, status):
    with db.connect() as con:
        con.execute("UPDATE videos SET status=? WHERE id=?", (status, video_id))


def chosen(db, run_id):
    with db.connect() as con:
        return {r["candidate"]: r["id"] for r in con.execute("SELECT id,candidate FROM videos WHERE run_id=?", (run_id,))}


def chosen_titles(db, destination_id):
    """(run id, candidate) pairs that became videos."""
    with db.connect() as con:
        return {(r["run_id"], r["candidate"]) for r in con.execute("SELECT run_id,candidate FROM videos WHERE destination_id=?", (destination_id,))}
