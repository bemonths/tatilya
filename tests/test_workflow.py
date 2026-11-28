"""GÖREV-21: the stored statuses of a video's steps (`studio/workflow.py`; the rules of Rota Stüdyo's TASARIM 6.2).

The first step starts ready and the others wait; a step that is approved (a step without approval: done) makes the next one ready and
takes that back when it leaves that state; an approved output that changes makes the later steps with an output stale with a Turkish
reason, and "Bu değişiklik etkilemiyor" returns a step to the status it had with the note in the status log; a step that looks running
while none of its work runs becomes an error."""
import pytest

from studio import workflow
from studio.ai import store
from studio.database import Database
from studio.text import store as text_store


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "studio.sqlite3")
    database.initialize()
    return database


def new_video(db, video_id="v1", name="Deneme"):
    with db.connect() as con:
        store.insert_video(con, {"id": video_id, "destination_id": "30a", "name": name})
        workflow.init(con, video_id)
    return video_id


def statuses(db, video_id="v1"):
    return {key: row["status"] for key, row in workflow.steps(db, video_id).items()}


def test_the_eight_steps_their_approvals_and_the_ones_not_built_yet():
    assert [title for _, title in workflow.STEPS] == ["Başlık ve vaat", "Veri paketi", "Plan", "Yazım", "Kontrol ve ton seçimi", "Yayın paketi",
                                                      "Seslendirme", "Kurgu paketi"]
    assert workflow.KEYS == ("baslik", "paket", "plan", "yazim", "kontrol", "yayin", "ses", "kurgu")
    assert workflow.APPROVAL == {"baslik", "plan", "kontrol", "yayin"} and workflow.PLANNED == {}
    assert set(workflow.STATUS_LABELS.values()) == {"bekliyor", "hazır", "çalışıyor", "onay bekliyor", "onaylandı", "tamamlandı", "hata", "eskidi"}
    assert workflow.label("plan") == "3 · Plan" and workflow.label("kurgu") == "8 · Kurgu paketi"
    # "Veri", "Konu ve başlık", "Kontrol", "Görsel plan" and "Video üretimi" are no steps of a video any more
    assert not {"veri", "gorsel", "uretim", "metin"} & set(workflow.KEYS)


def test_the_first_step_starts_ready_and_the_others_wait(db):
    new_video(db)
    assert statuses(db) == {"baslik": "ready", "paket": "waiting", "plan": "waiting", "yazim": "waiting", "kontrol": "waiting",
                            "yayin": "waiting", "ses": "waiting", "kurgu": "waiting"}
    view = workflow.compute(db, "30a", "v1")
    assert view["video"]["display_name"] == "Deneme" and (view["completed"], view["total"]) == (0, 8)
    assert [(s["number"], s["id"], s["label"]) for s in view["steps"]][:2] == [(1, "baslik", "hazır"), (2, "paket", "bekliyor")]
    assert [s["label"] for s in view["steps"]][5:] == ["bekliyor"] * 3 and not any(s["planned"] for s in view["steps"])
    assert view["steps"][7]["next"].startswith("Önce 6 · Yayın paketi onaylanmalı; kurgu paketi")
    assert workflow.compute(db, "30a", None) == {"video": None, "steps": [], "completed": 0, "total": 8}       # no video: no steps
    assert workflow.compute(db, "30a", "yok")["video"] is None


def test_an_approval_makes_the_next_step_ready_and_leaving_it_takes_that_back(db):
    new_video(db)
    workflow.set_step(db, "v1", "baslik", "awaiting_approval")
    assert statuses(db)["paket"] == "waiting"                                # nothing starts before the approval
    workflow.set_step(db, "v1", "baslik", "approved")
    assert statuses(db)["paket"] == "ready"
    workflow.set_step(db, "v1", "paket", "done")                             # a step without approval: done when it ends
    assert statuses(db)["plan"] == "ready"
    workflow.set_step(db, "v1", "plan", "running")
    assert statuses(db)["yazim"] == "waiting"
    workflow.set_step(db, "v1", "plan", "awaiting_approval")
    assert statuses(db)["yazim"] == "waiting"                                # the plan is there but not approved: the writing waits
    workflow.set_step(db, "v1", "plan", "approved")
    assert statuses(db)["yazim"] == "ready"
    workflow.set_step(db, "v1", "plan", "running")                           # run again: the next step waits for the new approval
    assert statuses(db)["yazim"] == "waiting"
    workflow.set_step(db, "v1", "plan", "approved")
    workflow.set_step(db, "v1", "plan", "ready")                             # rejected
    assert statuses(db)["yazim"] == "waiting"
    assert workflow.progress(workflow.steps(db, "v1")) == {"completed": 2, "total": 8}
    lines = [h["text"] for h in workflow.history(db, "v1")]
    assert "3 · Plan: onay bekliyor → onaylandı." in lines and "4 · Yazım: bekliyor → hazır." in lines and "4 · Yazım: hazır → bekliyor." in lines
    assert lines[-1] == "Video açıldı."


def test_the_statuses_a_step_cannot_take(db):
    new_video(db)
    for step, status in (("paket", "approved"), ("yazim", "awaiting_approval"), ("baslik", "done"), ("plan", "done"), ("plan", "stale"),
                         ("kurgu", "approved"), ("yayin", "awaiting_audio"), ("kurgu", "awaiting_audio"), ("plan", "bilinmeyen")):
        with pytest.raises(workflow.StateError):
            workflow.set_step(db, "v1", step, status)
    with pytest.raises(workflow.StateError):
        workflow.set_step(db, "v1", "yok", "ready")
    with pytest.raises(workflow.StateError):
        workflow.set_step(db, "v1", "plan", "approved", stale_from="paket", reason="x")          # staleness only goes forward
    with pytest.raises(workflow.StateError):
        workflow.set_step(db, "v1", "plan", "approved", stale_from="yazim")                      # and needs its reason
    for step in ("baslik", "paket", "plan", "yazim"):
        workflow.set_step(db, "v1", step, "approved" if step in workflow.APPROVAL else "done")
    workflow.set_step(db, "v1", "kontrol", "approved")
    assert statuses(db)["yayin"] == "ready" and statuses(db)["ses"] == "waiting"   # 6 opens; the steps not built stay waiting


def all_done(db):
    new_video(db)
    workflow.set_step(db, "v1", "baslik", "approved")
    workflow.set_step(db, "v1", "paket", "done")
    workflow.set_step(db, "v1", "plan", "approved")
    workflow.set_step(db, "v1", "yazim", "done")
    workflow.set_step(db, "v1", "kontrol", "awaiting_approval")


def test_a_changed_approval_makes_the_later_outputs_stale_and_bu_degisiklik_etkilemiyor_brings_the_status_back(db):
    all_done(db)
    workflow.set_step(db, "v1", "plan", "approved", stale_from="yazim", reason="Plan onayı değişti.")
    rows = workflow.steps(db, "v1")
    assert (rows["yazim"]["status"], rows["yazim"]["status_before_stale"], rows["yazim"]["stale_reason"]) == ("stale", "done", "Plan onayı değişti.")
    assert (rows["kontrol"]["status"], rows["kontrol"]["status_before_stale"]) == ("stale", "awaiting_approval")
    assert rows["paket"]["status"] == "done" and rows["plan"]["status"] == "approved"          # earlier steps are not touched
    view = next(s for s in workflow.compute(db, "30a", "v1")["steps"] if s["id"] == "yazim")
    assert view["label"] == "eskidi" and view["detail"] == "Plan onayı değişti." and "Bu değişiklik etkilemiyor" in view["next"]
    workflow.mark_stale(db, "v1", "yazim", "Veri paketi değişti.")             # a second reason joins the first; the old status is kept
    row = workflow.step(db, "v1", "yazim")
    assert row["stale_reason"] == "Plan onayı değişti. Veri paketi değişti." and row["status_before_stale"] == "done"
    workflow.clear_stale(db, "v1", "yazim", "Plan aynı kaldı, yalnız onay yenilendi.")
    row = workflow.step(db, "v1", "yazim")
    assert (row["status"], row["stale_reason"], row["status_before_stale"]) == ("done", None, None)
    newest = workflow.history(db, "v1")[0]["text"]
    assert newest.startswith("4 · Yazım: eskime kaldırıldı (“Bu değişiklik etkilemiyor”).") and newest.endswith("Not: Plan aynı kaldı, yalnız onay yenilendi.")
    workflow.clear_stale(db, "v1", "kontrol")
    assert workflow.step(db, "v1", "kontrol")["status"] == "awaiting_approval" and workflow.history(db, "v1")[0]["text"].endswith("Not: yok")
    with pytest.raises(workflow.StateError):
        workflow.clear_stale(db, "v1", "kontrol")                                # not stale: nothing to clear
    workflow.mark_stale(db, "v1", "plan", "Veri paketi değişti.")
    assert statuses(db)["plan"] == "stale"
    workflow.set_step(db, "v1", "plan", "running")                              # the other way out of staleness: run the step again
    row = workflow.step(db, "v1", "plan")
    assert (row["status"], row["stale_reason"], row["status_before_stale"]) == ("running", None, None)


def test_steps_without_an_output_do_not_go_stale(db):
    new_video(db)
    workflow.set_step(db, "v1", "baslik", "approved", stale_from="paket", reason="Başlık onayı değişti.")
    assert statuses(db) == {"baslik": "approved", "paket": "ready", "plan": "waiting", "yazim": "waiting", "kontrol": "waiting",
                            "yayin": "waiting", "ses": "waiting", "kurgu": "waiting"}


def test_a_step_that_looks_running_without_its_work_becomes_an_error(db):
    all_done(db)
    workflow.set_step(db, "v1", "plan", "running")                              # as if the program had closed half way
    assert workflow.active_steps(db) == set()
    workflow.recover(db)
    row = workflow.step(db, "v1", "plan")
    assert row["status"] == "error" and row["error"] == workflow.INTERRUPTED and "kaldığı yerden sürdürebilirsiniz" in row["error"]
    assert "çalışıyor görünüyordu ama çalışan işi yoktu" in workflow.history(db, "v1")[0]["text"]
    # a step whose work does run is left alone: a text run that is still in its plan, and one that writes with the approved plan
    text_store.insert_run(db, run_id="t1", destination_id="30a", video_id="v1", job_id=None, tones=[], pack_id=None)
    workflow.set_step(db, "v1", "plan", "running")
    assert workflow.active_steps(db) == {("v1", "plan")}
    workflow.recover(db)
    assert statuses(db)["plan"] == "running"
    text_store.update_run(db, "t1", state={"plan_onaylandi": True})
    assert workflow.active_steps(db) == {("v1", "yazim")}
    assert workflow.compute(db, "30a", "v1")["steps"][2]["status"] == "error"   # reading the video's steps recovers them too


def test_the_writing_done_opens_the_check_and_makes_an_approved_check_stale(db):
    new_video(db)
    for step, status in (("baslik", "approved"), ("paket", "done"), ("plan", "approved"), ("yazim", "running")):
        workflow.set_step(db, "v1", step, status)
    workflow.writing_done(db, "v1", "t1")
    rows = workflow.steps(db, "v1")
    assert (rows["yazim"]["status"], rows["yazim"]["ref"]) == ("done", "t1") and rows["kontrol"]["status"] == "awaiting_approval"
    assert not workflow.choice_valid(db, "v1")
    workflow.set_step(db, "v1", "kontrol", "approved")
    assert workflow.choice_valid(db, "v1")
    workflow.set_step(db, "v1", "yazim", "running")
    workflow.writing_done(db, "v1", "t2")                                       # written again after the tone was chosen
    row = workflow.step(db, "v1", "kontrol")
    assert (row["status"], row["stale_reason"], row["status_before_stale"]) == ("stale", "Yazım değişti.", "approved")
    assert workflow.choice_valid(db, "v1")                                      # the choice holds until the user decides again


def test_a_video_made_before_the_steps_were_stored_gets_them_from_its_records(db):
    with db.connect() as con:
        con.execute("""INSERT INTO claude_runs (id,destination_id,step,scope_id,status,params,folder,created_at)
            VALUES ('r1','30a','baslik','r1','approved','{}','claude/r1/baslik/r1','2026-10-10T10:00:00+00:00')""")
        store.insert_video(con, {"id": "v1", "destination_id": "30a", "region_name": "30A geneli", "title_en": "T | 30A Florida Vacation",
                                 "title_tr": "B | 30A Florida Tatili", "family": "Deneyim", "run_id": "r1", "candidate": 0})
    assert statuses(db) == {"baslik": "approved", "paket": "ready", "plan": "waiting", "yazim": "waiting", "kontrol": "waiting",
                            "yayin": "waiting", "ses": "waiting", "kurgu": "waiting"}
    assert workflow.display_name(store.video(db, "v1")) == "B | 30A Florida Tatili"
