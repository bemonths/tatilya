"""GÖREV-14: the workflow sidebar. Every status is computed from the records (video record, Claude runs, packs, collector runs); the
staleness rule of the data pack and the "Sıradaki iş" line of each step."""
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from studio import workflow
from studio.ai import store
from tests.test_claude_steps import app, finished, start  # noqa: F401  (app: fixture with the fake Claude)


def steps(view):
    return {s["id"]: s for s in view["steps"]}


def stamp(delta=timedelta(0)):
    return (datetime.now(timezone.utc) + delta).isoformat(timespec="milliseconds")


def done_run(db, finished_at=None):
    """A finished collector run of the destination (only its finish time matters to the workflow)."""
    identifier = uuid.uuid4().hex
    with db.connect() as con:
        con.execute("""INSERT INTO jobs (id,kind,title,status,progress,message,created_at,finished_at,result,log,destination_id)
            VALUES (?,'source_collection','deneme','done',100,'',?,?,'{}','[]','30a')""", (identifier, stamp(), finished_at or stamp()))
        con.execute("""INSERT INTO source_runs (id,job_id,status,started_at,finished_at,connector_name,connector_version,metadata,destination_id)
            VALUES (?,?,'done',?,?,'deneme','deneme/1','{}','30a')""", (identifier, identifier, stamp(), finished_at or stamp()))
    return identifier


@pytest.fixture
def nothing_due(monkeypatch):
    real = workflow.refresh.status

    def status(db, destination_id, today=None):
        return {**real(db, destination_id, today), "due_count": 0, "items": [], "batch": None}

    monkeypatch.setattr(workflow.refresh, "status", status)


def test_without_data_or_video_only_the_data_step_has_work(app):
    view = app.get("/api/workflow").json()
    s = steps(view)
    assert [x["number"] for x in view["steps"]] == list(range(1, 9))
    assert [x["title"] for x in view["steps"]] == ["Veri", "Konu ve başlık", "Veri paketi", "Video metni", "Kontrol", "Görsel plan",
                                                   "Video üretimi", "Yayın hazırlığı"]
    assert (s["veri"]["status"], s["veri"]["label"]) == ("due", "güncelleme zamanı geldi")
    assert "Zamanı gelenleri başlat" in s["veri"]["next"] and s["veri"]["detail"]          # the due collectors are named
    assert (s["baslik"]["status"], s["baslik"]["href"]) == ("waiting", "#videos") and "Önce veri gerekiyor" in s["baslik"]["next"]
    assert s["paket"]["status"] == "waiting" and "Önce bir başlık seç" in s["paket"]["next"]
    for key in ("metin", "kontrol", "gorsel", "uretim", "yayin"):
        assert (s[key]["status"], s[key]["label"], s[key]["planned"]) == ("planned", "planlanan", True)
        assert s[key]["href"] == f"#adim/{key}" and "henüz kurulmadı" in s[key]["next"]
    assert (view["completed"], view["total"], view["dots"], view["video"]) == (0, 8, "○○○○○○○○", None)


def test_data_step_is_current_running_or_never_fetched(app, nothing_due):
    db = app.app.state.db
    s = steps(app.get("/api/workflow").json())
    assert s["veri"]["status"] == "waiting" and "Veri toplama" in s["veri"]["next"]          # nothing due, but nothing fetched yet
    done_run(db)
    s = steps(app.get("/api/workflow").json())
    assert (s["veri"]["status"], s["veri"]["label"]) == ("done", "güncel") and "yapılacak iş yok" in s["veri"]["next"]
    assert s["baslik"]["status"] == "ready" and "Öneri al" in s["baslik"]["next"]
    job = db.add_job("source_collection", "Toplama")
    s = steps(app.get("/api/workflow").json())
    assert s["veri"]["status"] == "running" and "İşler panelinde" in s["veri"]["next"]
    db.update_job(job, status="done", message="Bitti")
    assert app.get("/api/workflow").json()["completed"] == 1


def test_title_step_follows_the_claude_runs_and_the_chosen_video(app, nothing_due):
    db = app.app.state.db
    done_run(db)
    view = start(app, bolge="Rosemary Beach")
    s = steps(app.get("/api/workflow").json())
    assert s["baslik"]["status"] == "awaiting_approval" and s["baslik"]["label"] == "onay bekliyor"
    assert s["baslik"]["next"].startswith("Başlık seçilmedi: onay bekleyen öneriden bir başlık seç")
    video = app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 0}).json()
    current = app.get("/api/workflow", params={"video_id": video["id"]}).json()
    s = steps(current)
    assert current["video"]["id"] == video["id"] and [v["id"] for v in current["videos"]] == [video["id"]]
    assert (s["baslik"]["status"], s["baslik"]["label"]) == ("approved", "onaylandı") and video["title_en"] in s["baslik"]["next"]
    assert s["paket"]["status"] == "ready" and "Kanıt paketi üret" in s["paket"]["next"]
    assert (current["completed"], current["dots"]) == (2, "●●○○○○○○")
    unselected = steps(app.get("/api/workflow").json())                                        # no video selected: the runs speak
    assert unselected["baslik"]["status"] == "ready" and unselected["paket"]["status"] == "waiting"
    assert app.get("/api/workflow", params={"video_id": "yok"}).json()["video"] is None        # an unknown id is no selection


def test_running_and_failed_title_runs(app, nothing_due, monkeypatch):
    db = app.app.state.db
    done_run(db)
    with db.connect() as con:
        store.insert_run(con, run_id="r1", destination_id="30a", step="baslik", scope_id="r1", job_id=None, params={"bolge": "Seaside"},
                         folder="claude/r1/baslik/r1")
    assert steps(workflow.compute(db, "30a"))["baslik"]["status"] == "running"
    store.update_run(db, "r1", status="error", error="Claude kullanım sınırına ulaşıldı.")
    s = steps(workflow.compute(db, "30a"))
    assert s["baslik"]["status"] == "error" and s["baslik"]["detail"] == "Claude kullanım sınırına ulaşıldı."
    assert "yeniden çalıştır" in s["baslik"]["next"]


def test_the_data_pack_is_done_and_becomes_stale_when_data_is_fetched_again(app, nothing_due):
    db = app.app.state.db
    done_run(db, stamp(-timedelta(hours=1)))
    view = start(app, bolge="Rosemary Beach")
    video = app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 0}).json()
    assert app.post(f"/api/videos/{video['id']}/evidence-pack").status_code == 201
    current = app.get("/api/workflow", params={"video_id": video["id"]}).json()
    s = steps(current)
    assert (s["paket"]["status"], s["paket"]["label"]) == ("done", "tamamlandı") and current["completed"] == 3
    assert "Video metni" in s["paket"]["next"]
    time.sleep(0.01)
    done_run(db)                                                                                # data fetched after the pack
    time.sleep(1.1)                                                                             # pack times are whole seconds
    s = steps(app.get("/api/workflow", params={"video_id": video["id"]}).json())
    assert (s["paket"]["status"], s["paket"]["label"]) == ("stale", "eskidi")
    assert s["paket"]["next"].startswith("Paket verinin son çekiminden eski") and s["paket"]["detail"] == "veri paketten sonra yeniden çekildi"
    assert app.post(f"/api/videos/{video['id']}/evidence-pack").status_code == 201             # made again: done
    assert steps(app.get("/api/workflow", params={"video_id": video["id"]}).json())["paket"]["status"] == "done"


def test_statuses_are_not_stored_anywhere(app):
    with app.app.state.db.connect() as con:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not {t for t in tables if "workflow" in t or "durum" in t}


def test_an_evaluation_without_candidates_is_information_not_waiting(app, nothing_due, monkeypatch):
    """GÖREV-15 Adım 1d: "veriyle dolmuyor" with no candidate is not counted as waiting; it is shown as information and can be rejected."""
    db = app.app.state.db
    done_run(db)
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "dolmuyor")
    response = app.post("/api/claude/review-runs", json={"bolge": "Rosemary Beach", "baslik": "Rosemary Beach'e köpeğimizle gitsek nasıl olur?"})
    run = finished(app, response.json()["id"])
    assert run["status"] == "awaiting_approval" and run["candidates"] == []
    assert run["adaysiz"] is True and run["bilgi"] == "Değerlendirildi: veriyle dolmuyor"
    listed = next(r for r in app.get("/api/claude/runs").json() if r["id"] == run["id"])
    assert listed["adaysiz"] is True and listed["bilgi"] == "Değerlendirildi: veriyle dolmuyor"
    s = steps(app.get("/api/workflow").json())
    assert s["baslik"]["status"] == "ready" and s["baslik"]["detail"] == "Değerlendirildi: veriyle dolmuyor"
    assert "veriyle dolmuyor" in s["baslik"]["next"]
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "ok")
    start(app, bolge="Rosemary Beach")                                    # a proposal with candidates waits as before
    assert steps(app.get("/api/workflow").json())["baslik"]["detail"] == "1 çalışma onay bekliyor"
    rejected = app.post(f"/api/claude/runs/{run['id']}/reject", json={}).json()
    assert rejected["status"] == "rejected"
    assert not next(r for r in app.get("/api/claude/runs").json() if r["id"] == run["id"])["adaysiz"]
