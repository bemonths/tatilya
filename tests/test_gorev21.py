"""GÖREV-21 through the app with the fake Claude: the project layer and the video layer.

- No video open: no steps; a video open: its eight steps; "Videoyu kapat" returns to the project; the open video is remembered.
- "Bu başlıkla video aç" opens the video and marks the candidate used; the other candidates stay in the pool.
- The one approval component (1 · Başlık ve vaat, 3 · Plan, 5 · Kontrol ve ton seçimi): Onayla, Düzeltme iste, Reddet; the note of
  "Düzeltme iste" is in the material Claude gets when the step runs again, and no instruction file changes.
- The writing never starts before the plan is approved.
- Staleness with its Turkish reason and "Bu değişiklik etkilemiyor".
- The cost: the estimate, the spending so far, canceling, the link table.
- Ayarlar keeps only the program's settings; the migration keeps every row.
"""
import json
import sqlite3
import time

from studio import workflow
from studio.ai import settings as claude_settings
from studio.ai import text_steps as TS
from studio.database import SCHEMA_VERSION, Database
from tests.legacy import V21_TABLES, drop_v21
from tests.test_claude_steps import finished
from tests.text_helpers import (FakeClock, add_video, app, decide, open_app, sessions, start_plan, start_text, start_writing,  # noqa: F401
                                step_status, text_env, text_job, wait_run)

TWO = ("arastirmaci_dost", "hikaye_anlaticisi")
NOTE = "Girişi kısalt; ilk cümlede fiyatı söyle."


def title_run(client, bolge="30A geneli"):
    started = client.post("/api/claude/title-runs", json={"bolge": bolge})
    assert started.status_code == 201, started.json()
    return finished(client, started.json()["id"])


def step(client, key, video_id="v1"):
    response = client.get(f"/api/videos/{video_id}/adimlar/{key}")
    assert response.status_code == 200, response.json()
    return response.json()


def statuses(client, video_id="v1"):
    return {s["id"]: s["status"] for s in client.get("/api/workflow", params={"video_id": video_id}).json()["steps"]}


def calls_of(folder):
    return [json.loads(line) for line in (folder / ".fake_claude_calls.jsonl").read_text(encoding="utf-8").splitlines()]


def settle(client, video_id, key, wanted, limit=60):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        if statuses(client, video_id)[key] in wanted:
            return
        time.sleep(0.1)
    raise AssertionError(f"{key}: {statuses(client, video_id)[key]}")


# ------------------------------------------------------------------------------------------------------------------- the two layers

def test_no_video_no_steps_and_an_open_video_shows_only_its_eight_steps(text_env):
    client = open_app(text_env / "data", FakeClock())
    try:
        assert client.get("/api/workflow").json() == {"video": None, "steps": [], "completed": 0, "total": 8}
        assert client.get("/api/bootstrap").json()["open_video_id"] is None
        assert client.get("/api/videolar").json() == {"videolar": [], "arsiv": False, "arsivdeki": 0, "acik": None}
        made = client.post("/api/videolar", json={"ad": "Kış videosu"})
        assert made.status_code == 201 and made.json()["ilerleme"] == "0/8" and made.json()["ad"] == "Kış videosu"
        video_id = made.json()["id"]
        assert client.get("/api/bootstrap").json()["open_video_id"] == video_id          # "Yeni video" opens it
        flow = client.get("/api/workflow", params={"video_id": video_id}).json()
        assert [(s["number"], s["title"]) for s in flow["steps"]] == [(1, "Başlık ve vaat"), (2, "Veri paketi"), (3, "Plan"), (4, "Yazım"),
                                                                      (5, "Kontrol ve ton seçimi"), (6, "Yayın paketi"), (7, "Seslendirme"),
                                                                      (8, "Kurgu paketi")]
        assert flow["video"]["display_name"] == "Kış videosu" and flow["steps"][0]["status"] == "ready"
        assert [s["approval"] for s in flow["steps"]] == [True, False, True, False, True, False, False, False]
        planned = step(client, "kurgu", video_id)
        assert planned["adim"]["label"] == "sonraki görevde gelecek" and "Kurgu Motoru" in planned["aciklama"] and not any(planned["eylemler"].values())
        assert client.post("/api/videolar/kapat").json() == {"acik": None}                # "Videoyu kapat": back to the project
        assert client.get("/api/bootstrap").json()["open_video_id"] is None
        assert [v["id"] for v in client.get("/api/videolar").json()["videolar"]] == [video_id]       # the video is not deleted
        assert client.post(f"/api/videos/{video_id}/ac").json()["video"]["id"] == video_id
        assert client.post("/api/videos/yok/ac").status_code == 404
        assert client.get("/api/workflow", params={"video_id": "yok"}).json()["video"] is None
        assert client.post("/api/videolar", json={"ad": "x" * 121}).status_code == 422
    finally:
        client.__exit__(None, None, None)
    again = open_app(text_env / "data", FakeClock())                                      # the open video is remembered at the next start
    try:
        assert again.get("/api/bootstrap").json()["open_video_id"] == video_id
    finally:
        again.__exit__(None, None, None)


def test_archiving_takes_a_video_off_the_list_and_nothing_is_deleted(app):
    first = app.post("/api/videolar", json={"ad": "Bir"}).json()["id"]
    second = app.post("/api/videolar", json={}).json()
    assert second["ad"] == "Adsız video" and second["calisma_adi"] is None
    archived = app.post(f"/api/videos/{second['id']}/arsivle")
    assert archived.status_code == 200 and archived.json()["arsivlendi"]
    listing = app.get("/api/videolar").json()
    assert [v["id"] for v in listing["videolar"]] == [first] and listing["arsivdeki"] == 1 and listing["acik"] is None    # the open one was archived
    assert [v["id"] for v in app.get("/api/videolar", params={"arsiv": "true"}).json()["videolar"]] == [second["id"]]
    assert app.post(f"/api/videos/{second['id']}/arsivden-cikar").json()["arsivlendi"] is None
    assert len(app.get("/api/videolar").json()["videolar"]) == 2
    assert app.delete(f"/api/videos/{second['id']}").status_code in (404, 405)            # there is no delete
    with sqlite3.connect(app.data / "studio.sqlite3") as con:
        assert con.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 2


def test_bu_baslikla_video_ac_opens_the_video_and_marks_the_candidate_used(app):
    run = title_run(app)
    bank = app.get("/api/konu-bankasi").json()
    assert (bank["aday_sayisi"], bank["kullanilan"], bank["kullanilabilir"]) == (8, 0, 8)
    assert all(c["secilebilir"] and c["baslik_tr"] and c["baslik_en"] for c in bank["calismalar"][0]["adaylar"])
    opened = app.post(f"/api/claude/runs/{run['id']}/select", json={"aday": 2})
    assert opened.status_code == 201
    video = opened.json()
    wanted = run["candidates"][2]
    assert (video["title_en"], video["title_tr"]) == (wanted["baslik_en"], wanted["baslik_tr"])
    assert app.get("/api/bootstrap").json()["open_video_id"] == video["id"]                # the video is the open one
    assert statuses(app, video["id"]) == {"baslik": "awaiting_approval", "paket": "waiting", "plan": "waiting", "yazim": "waiting",
                                          "kontrol": "waiting", "yayin": "waiting", "ses": "waiting", "kurgu": "waiting"}
    bank = app.get("/api/konu-bankasi").json()
    used = bank["calismalar"][0]["adaylar"][2]
    assert (used["video_id"], used["video_adi"], used["secilebilir"]) == (video["id"], wanted["baslik_tr"], False)
    assert (bank["kullanilan"], bank["kullanilabilir"]) == (1, 7)                         # the others stay in the pool
    view = app.get(f"/api/claude/runs/{run['id']}").json()
    assert view["candidates"][2]["video_adi"] == wanted["baslik_tr"] and view["candidates"][3]["secilebilir"]
    again = app.post(f"/api/claude/runs/{run['id']}/select", json={"aday": 2})
    assert again.status_code == 409 and "Bu başlık kullanıldı" in again.json()["detail"]
    shown = step(app, "baslik", video["id"])
    assert shown["secim"]["baslik_tr"] == wanted["baslik_tr"] and shown["secim"]["izleyici_sorusu"] and shown["secim"]["vaat"]
    assert shown["eylemler"] == {"approve": True, "correct": True, "reject": True, "clear_stale": False, "run": False, "resume": False,
                                 "reopen": False}
    assert [v["baslik"] for v in shown["surumler"]] == ["Başlık seçildi"]                  # the output is a file
    assert list((app.data / "videolar" / video["id"] / "1_baslik").glob("surum-001.json"))
    listed = app.get("/api/videolar").json()["videolar"][0]
    assert (listed["baslik_tr"], listed["baslik_en"], listed["ilerleme"]) == (wanted["baslik_tr"], wanted["baslik_en"], "0/8")
    assert listed["siradaki"] == {"id": "baslik", "ad": "1 · Başlık ve vaat", "durum": "awaiting_approval", "durum_adi": "onay bekliyor"}


# ------------------------------------------------------------------------------------------------------------------- 1 · Başlık ve vaat

def test_title_approve_and_reject(app):
    run = title_run(app)
    video = app.post(f"/api/claude/runs/{run['id']}/select", json={"aday": 0}).json()
    vid = video["id"]
    assert app.post(f"/api/videos/{vid}/evidence-pack").status_code == 409                # nothing before the approval
    rejected = app.post(f"/api/videos/{vid}/adimlar/baslik/reddet", json={"not": "Bu konu şimdi olmaz."})
    assert rejected.status_code == 200 and rejected.json()["adim"]["status"] == "ready" and rejected.json()["secim"] is None
    assert app.get("/api/videos").json()[0]["title_en"] is None                            # the choice of the title is gone
    bank = app.get("/api/konu-bankasi").json()
    assert bank["calismalar"][0]["adaylar"][0]["secilebilir"] and bank["kullanilan"] == 0    # the candidate is back in the pool
    assert bank["calismalar"][0]["status"] == "awaiting_approval"
    assert any(line["text"] == "1 · Başlık ve vaat reddedildi. Not: Bu konu şimdi olmaz." for line in rejected.json()["gunluk"])
    assert [c["sira"] for c in rejected.json()["adaylar"]] == list(range(8)) and rejected.json()["eylemler"]["run"]
    used = app.post(f"/api/videos/{vid}/baslik/aday", json={"calisma": run["id"], "aday": 5})      # "Bu başlığı kullan" in the step
    assert used.status_code == 201 and used.json()["id"] == vid and used.json()["title_en"] == run["candidates"][5]["baslik_en"]
    assert statuses(app, vid)["baslik"] == "awaiting_approval"
    busy = app.post(f"/api/videos/{vid}/baslik/aday", json={"calisma": run["id"], "aday": 6})
    assert busy.status_code == 409 and "değiştirilemez" in busy.json()["detail"]
    approved = app.post(f"/api/videos/{vid}/adimlar/baslik/onayla", json={"not": "Tamam."})
    assert approved.status_code == 200 and approved.json()["adim"]["status"] == "approved"
    assert statuses(app, vid)["paket"] == "ready" and approved.json()["eylemler"]["approve"] is False
    assert [v["baslik"] for v in approved.json()["surumler"]] == ["Onaylandı", "Başlık seçildi", "Reddedildi", "Başlık seçildi"]
    assert app.post(f"/api/videos/{vid}/evidence-pack").status_code == 201 and statuses(app, vid)["plan"] == "ready"
    assert app.post(f"/api/videos/{vid}/adimlar/paket/onayla", json={}).status_code == 409         # a step without approval


def test_title_duzeltme_iste_gives_the_note_to_claude_as_material(app):
    run = title_run(app)
    vid = app.post(f"/api/claude/runs/{run['id']}/select", json={"aday": 1}).json()["id"]
    empty = app.post(f"/api/videos/{vid}/adimlar/baslik/duzeltme", json={"not": "  "})
    assert empty.status_code == 409 and empty.json()["detail"].startswith("Düzeltme isterken not zorunlu")
    estimate = app.post(f"/api/videos/{vid}/adimlar/baslik/duzeltme/tahmin", json={"not": NOTE}).json()["tahmin"]
    assert estimate["toplam"]["cagri"] == 1 and estimate["toplam"]["okunan"] > 0 and estimate["baslatilabilir"]
    asked = app.post(f"/api/videos/{vid}/adimlar/baslik/duzeltme", json={"not": NOTE})
    assert asked.status_code == 201
    corrected = finished(app, asked.json()["baslayan"])
    assert corrected["status"] == "awaiting_approval" and corrected["correction_of"] == run["id"] and corrected["params"]["video_id"] == vid
    prompt = calls_of(app.data / corrected["folder"])[0]["prompt"]
    assert "Düzeltme: kullanıcının düzeltme notu aşağıda." in prompt and NOTE in prompt and "onceki_cikti.json" in prompt
    # the note is material of the task; the instructions Claude got are the ones the first run got
    assert NOTE not in (app.data / corrected["folder"] / "talimat.md").read_text(encoding="utf-8")
    assert (app.data / corrected["folder"] / "talimat.md").read_bytes() == (app.data / run["folder"] / "talimat.md").read_bytes()
    settle(app, vid, "baslik", ("ready",))
    shown = step(app, "baslik", vid)
    assert shown["secim"] is None and shown["adaylar"][0]["bu_video"] and shown["adaylar"][0]["calisma"] == corrected["id"]
    assert shown["degerlendirmeler"][0]["duzeltme_notu"] == NOTE
    assert any(NOTE in line["text"] and "düzeltme istendi" in line["text"] for line in shown["gunluk"])
    assert app.get("/api/konu-bankasi").json()["kullanilan"] == 0                          # the video gave its candidate back


def test_a_new_video_takes_its_title_from_the_users_own_title(app, monkeypatch):
    vid = app.post("/api/videolar", json={"ad": "Köpekle tatil"}).json()["id"]
    body = {"bolge": "Rosemary Beach", "baslik": "Rosemary Beach'e köpekle gitmek", "not": ""}
    estimate = app.post(f"/api/videos/{vid}/baslik/degerlendir/tahmin", json=body).json()
    assert estimate["toplam"]["cagri"] == 1 and estimate["satirlar"][0]["model_adi"]
    started = app.post(f"/api/videos/{vid}/baslik/degerlendir", json=body)
    assert started.status_code == 201 and started.json()["params"]["video_id"] == vid
    review = finished(app, started.json()["id"])
    settle(app, vid, "baslik", ("ready",))
    shown = step(app, "baslik", vid)
    own = [c for c in shown["adaylar"] if c["bu_video"]]
    assert len(own) == len(review["candidates"]) > 0 and shown["adaylar"][:len(own)] == own       # this video's candidates come first
    assert app.get("/api/konu-bankasi").json()["calismalar"][0]["id"] == review["id"]           # the run is in the topic bank like any other
    used = app.post(f"/api/videos/{vid}/baslik/aday", json={"calisma": review["id"], "aday": 0})
    assert used.status_code == 201 and statuses(app, vid)["baslik"] == "awaiting_approval"
    assert app.get("/api/videolar").json()["videolar"][0]["calisma_adi"] == "Köpekle tatil"


def test_a_canceled_title_run_is_recorded_as_iptal_edildi_and_the_step_is_ready_again(app, monkeypatch):
    vid = app.post("/api/videolar", json={}).json()["id"]
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "slow")
    monkeypatch.setenv("FAKE_CLAUDE_SLEEP", "20")
    started = app.post(f"/api/videos/{vid}/baslik/degerlendir", json={"bolge": "30A geneli", "baslik": "Kışın 30A"})
    assert started.status_code == 201
    settle(app, vid, "baslik", ("running",))
    shown = step(app, "baslik", vid)
    assert shown["is"] == started.json()["job_id"] and not shown["eylemler"]["run"]          # the job of the step: its "İptal" is on the screen
    assert app.post(f"/api/jobs/{shown['is']}/cancel").status_code == 200
    run = finished(app, started.json()["id"])
    assert run["canceled"] and run["status_label"] == "iptal edildi"
    job = next(j for j in app.get("/api/jobs").json() if j["id"] == shown["is"])
    assert job["status"] == "canceled"
    settle(app, vid, "baslik", ("ready",))
    assert step(app, "baslik", vid)["degerlendirmeler"][0]["status_label"] == "iptal edildi"


# ------------------------------------------------------------------------------------------------------------------- 3 · Plan, 4 · Yazım

def test_the_writing_does_not_start_before_the_plan_is_approved(app):
    add_video(app)
    assert statuses(app)["plan"] == "ready" and statuses(app)["yazim"] == "waiting"
    refused = app.post("/api/videos/v1/yazim", json={"tonlar": ["arastirmaci_dost"]})
    assert refused.status_code == 409 and refused.json()["detail"] == "Plan onaylanmadan yazım başlamaz: önce 3 · Plan adımında planı onaylayın."
    assert app.post("/api/videos/v1/yazim/tahmin", json={"tonlar": ["arastirmaci_dost"]}).status_code == 409
    plan = start_plan(app)
    assert plan["status"] == "paused" and plan["reason"] == "plan_hazir" and plan["status_label"] == "plan hazır" and plan["tones"] == []
    assert statuses(app)["plan"] == "awaiting_approval" and statuses(app)["yazim"] == "waiting"
    assert not sessions(plan, "metin_bolum")                                               # the chain stopped after the plan
    assert app.post("/api/videos/v1/yazim", json={"tonlar": ["arastirmaci_dost"]}).status_code == 409
    shown = step(app, "plan")
    assert shown["calisma"]["plan"]["bolumler"] and shown["eylemler"]["approve"] and shown["eylemler"]["reject"]
    assert decide(app, "plan", not_="x").status_code == 422                                # the note's field is "not"
    approved = decide(app, "plan", **{"not": "Plan iyi."})
    assert approved.status_code == 200 and approved.json()["adim"]["status"] == "approved"
    assert statuses(app)["yazim"] == "ready"
    done = start_writing(app)
    assert done["status"] == "awaiting_comparison" and done["id"] == plan["id"] and len(done["surumler"]) == 1
    assert statuses(app) == {"baslik": "approved", "paket": "done", "plan": "approved", "yazim": "done", "kontrol": "awaiting_approval",
                             "yayin": "waiting", "ses": "waiting", "kurgu": "waiting"}
    assert app.get("/api/videolar").json()["videolar"][0]["ilerleme"] == "4/8"


def test_plan_duzeltme_iste_writes_the_plan_again_with_the_note_and_the_old_plan_as_material(app):
    add_video(app)
    first = start_plan(app)
    estimate = app.post("/api/videos/v1/adimlar/plan/duzeltme/tahmin", json={"not": NOTE}).json()["tahmin"]
    assert estimate["satirlar"][0]["baslik"] == "Plan" and estimate["toplam"]["cagri"] == 2
    asked = decide(app, "plan", "duzeltme", **{"not": NOTE})
    assert asked.status_code == 201 and asked.json()["baslayan"] != first["id"]
    second = wait_run(app, asked.json()["baslayan"])
    assert second["reason"] == "plan_hazir" and second["replan_of"] == first["id"] and second["plan_notu"] == NOTE
    assert statuses(app)["plan"] == "awaiting_approval" and step(app, "plan")["calisma"]["id"] == second["id"]
    planner = sessions(second, "metin_plan")[0]
    folder = app.data / "claude" / "v1" / "metin_plan" / planner["id"]
    task = (folder / "gorev.md").read_text(encoding="utf-8")
    assert f"- `{TS.NOTE_FILE}` — kullanıcının düzeltme notu" in task and NOTE in task
    assert f"- `{TS.PREVIOUS_PLAN}` — kullanıcının düzeltme istediği önceki plan" in task
    assert (folder / TS.NOTE_FILE).read_text(encoding="utf-8") == f"# Kullanıcının düzeltme notu\n\n{NOTE}\n"
    assert json.loads((folder / TS.PREVIOUS_PLAN).read_text(encoding="utf-8")) == first["plan"]
    assert NOTE in calls_of(folder)[0]["prompt"]                                           # it is in what Claude was sent
    old = app.data / "claude" / "v1" / "metin_plan" / sessions(first, "metin_plan")[0]["id"]
    assert (folder / "talimat.md").read_bytes() == (old / "talimat.md").read_bytes()       # no instruction file changed
    critic = app.data / "claude" / "v1" / "metin_plan_elestiri" / sessions(second, "metin_plan_elestiri")[0]["id"]
    assert not (critic / TS.NOTE_FILE).exists()
    versions = step(app, "plan")["surumler"]
    assert [v["id"] for v in versions] == [second["id"], first["id"]] and versions[0]["ayrinti"] == f"Düzeltme notu: {NOTE}"
    rejected = decide(app, "plan", "reddet", **{"not": "Baştan."})
    assert rejected.json()["adim"]["status"] == "ready" and statuses(app)["yazim"] == "waiting"
    assert decide(app, "plan").status_code == 409                                          # nothing to approve after the rejection


def test_check_approval_picks_the_tone_and_duzeltme_iste_sends_the_note_to_the_writing(app):
    add_video(app)
    first = start_text(app, TWO)
    shown = step(app, "kontrol")
    assert shown["adim"]["status"] == "awaiting_approval" and [t["tone_name"] for t in shown["tonlar"]] == ["Araştırmacı dost", "Hikâye anlatıcısı"]
    assert shown["tonlar"][0]["bulgular"] and {"isletme_adi", "red", "yellow"} <= set(shown["tonlar"][0])
    assert decide(app, "kontrol").status_code == 409                                       # "Onayla" needs the tone to go on with
    # Düzeltme iste: the note makes 4 · Yazım ready and waits there for the rewrite
    asked = decide(app, "kontrol", "duzeltme", **{"not": NOTE})
    assert asked.status_code == 201 and asked.json()["adim"]["status"] == "waiting"
    writing = step(app, "yazim")
    assert writing["adim"]["status"] == "ready" and writing["duzeltme_notu"] == NOTE
    assert app.post("/api/videos/v1/adimlar/kontrol/duzeltme/tahmin", json={"not": NOTE}).status_code == 409      # the check is closed now
    estimate = app.post("/api/videos/v1/yazim/tahmin", json={"tonlar": ["arastirmaci_dost"]}).json()
    assert [r["baslik"] for r in estimate["satirlar"]] == ["Araştırmacı dost"] and estimate["satirlar"][0]["cagri"] == 10
    second = start_writing(app)
    assert second["id"] != first["id"] and second["plan_kaynagi"] == first["id"] and second["yazim_notu"] == NOTE
    assert not sessions(second, "metin_plan") and second["plan"] == first["plan"]          # the approved plan, not a new one
    for name in ("metin_bolum", "metin_birlestirme", "metin_giris_kapanis", "metin_son_okuma"):
        for session in sessions(second, name):
            folder = app.data / "claude" / "v1" / name / session["id"]
            assert (folder / TS.NOTE_FILE).read_text(encoding="utf-8") == f"# Kullanıcının düzeltme notu\n\n{NOTE}\n", name
            assert NOTE in calls_of(folder)[0]["prompt"], name
    translation = app.data / "claude" / "v1" / "metin_ceviri" / sessions(second, "metin_ceviri")[0]["id"]
    assert not (translation / TS.NOTE_FILE).exists()
    assert step(app, "yazim")["duzeltme_notu"] is None and statuses(app)["kontrol"] == "awaiting_approval"
    assert len(step(app, "yazim")["surumler"]) == 3                                        # the earlier texts are still there
    shown = step(app, "kontrol")
    assert [t["number"] for t in shown["tonlar"]] == [3] and shown["calisma"] == second["id"]
    approved = decide(app, "kontrol", surum=shown["tonlar"][0]["id"], **{"not": "Bu ton."})
    assert approved.status_code == 200 and approved.json()["adim"]["status"] == "approved"
    assert approved.json()["secim"]["ton"] == "Araştırmacı dost" and approved.json()["tonlar"][0]["secili"]
    assert app.get("/api/videolar").json()["videolar"][0]["ilerleme"] == "5/8"
    assert [v["baslik"] for v in approved.json()["surumler"]] == ["Onaylandı: Araştırmacı dost", "Düzeltme istendi"]
    rejected = decide(app, "kontrol", "reddet", **{"not": "Vazgeçtim."})
    assert rejected.json()["adim"]["status"] == "ready" and rejected.json()["secim"] is None and rejected.json()["eylemler"]["reopen"]
    assert app.post("/api/videos/v1/kontrol/ac").json()["adim"]["status"] == "awaiting_approval"


# ------------------------------------------------------------------------------------------------------------------- staleness

def test_a_changed_approval_makes_later_steps_stale_and_bu_degisiklik_etkilemiyor(app):
    add_video(app)
    view = start_text(app)
    assert decide(app, "kontrol", surum=view["surumler"][0]["id"]).status_code == 200
    assert app.post("/api/videos/v1/evidence-pack").status_code == 201                     # the pack is made again
    assert statuses(app) == {"baslik": "approved", "paket": "done", "plan": "stale", "yazim": "stale", "kontrol": "stale",
                             "yayin": "waiting", "ses": "waiting", "kurgu": "waiting"}
    shown = step(app, "plan")
    assert shown["adim"]["stale_reason"] == "Veri paketi değişti." and shown["adim"]["status_before_stale"] == "approved"
    assert shown["eylemler"]["clear_stale"] and shown["calisma"]["plan"]                   # the output is not deleted
    assert app.post("/api/videos/v1/yazim", json={"tonlar": ["belgesel"]}).status_code == 409           # a stale plan is not an approved one
    cleared = decide(app, "plan", "etkilemiyor", **{"not": "Paket aynı satırlarla kuruldu."})
    assert cleared.status_code == 200 and cleared.json()["adim"]["status"] == "approved"
    assert any("eskime kaldırıldı" in line["text"] and "Paket aynı satırlarla kuruldu." in line["text"] for line in cleared.json()["gunluk"])
    assert decide(app, "plan", "etkilemiyor").status_code == 409                           # not stale any more
    assert decide(app, "yazim", "etkilemiyor").json()["adim"]["status"] == "done"
    assert decide(app, "kontrol", "etkilemiyor").json()["adim"]["status"] == "approved"
    # the plan's approval changes: the steps after it are stale with that reason
    assert decide(app, "plan", "reddet").json()["adim"]["status"] == "ready"
    after = {s["id"]: s for s in app.get("/api/workflow", params={"video_id": "v1"}).json()["steps"]}
    assert (after["yazim"]["status"], after["yazim"]["stale_reason"]) == ("stale", "Plan onayı değişti.")
    assert (after["kontrol"]["status"], after["kontrol"]["detail"]) == ("stale", "Plan onayı değişti.")
    assert step(app, "kontrol")["secim"]["ton"] == "Araştırmacı dost"                      # the choice holds until the user decides again


# ------------------------------------------------------------------------------------------------------------------- the cost

def test_the_estimate_the_spending_and_the_link_table_of_plan_and_writing(app):
    add_video(app)
    estimate = app.post("/api/videos/v1/plan/tahmin", json={}).json()
    line = estimate["satirlar"][0]
    assert (line["baslik"], line["cagri"]) == ("Plan", 2) and line["okunan"] > 0 and line["yazilan"] > 0
    assert [m["adim"] for m in line["modeller"]] == ["metin_plan", "metin_plan_elestiri"] and all(m["model_adi"] for m in line["modeller"])
    plan = start_plan(app)
    chain = plan["halkalar"]
    assert [(r["baslik"], r["durum"], r["cagri"], r["tahmini_cagri"]) for r in chain["halkalar"]] == [("Planlayıcı", "done", 1, 1),
                                                                                                    ("Plan eleştirmeni", "done", 1, 1)]
    assert all(r["gercek"] > 0 and r["tahmin"] > 0 and r["durum_adi"] == "Tamamlandı" for r in chain["halkalar"])
    assert chain["toplam"]["cagri"] == 2 and chain["toplam"]["gercek"] == sum(r["gercek"] for r in chain["halkalar"])
    assert chain["toplam"]["tahmin"] == estimate["toplam"]["toplam"] and chain["fazla"] is False
    job = text_job(app, settled=True)
    assert job["result"]["harcama"]["gercek"]["cagri"] == 2 and job["result"]["harcama"]["tahmin"] == estimate["toplam"]["toplam"]
    assert plan["harcama"]["gercek"]["toplam"] == chain["toplam"]["gercek"]                # actual beside the estimate, after the job
    decide(app, "plan")
    done = start_writing(app)
    rows = done["halkalar"]["halkalar"]
    tone = [r for r in rows if r["grup"] == "arastirmaci_dost"]
    assert [r["baslik"] for r in tone] == ["Bölümler", "Birleştirme", "Giriş ve kapanış", "Son okuma", "Program denetimi", "Çeviri"]
    assert (tone[0]["cagri"], tone[0]["tahmini_cagri"], tone[0]["ayrinti"]) == (6, 6, "6/6 bölüm")
    assert (tone[4]["cagri"], tone[4]["ayrinti"], tone[4]["tahmin"]) == (0, "Claude çağrısı yok", None)
    assert all(r["durum"] == "done" and r["grup_adi"] == "Araştırmacı dost" for r in tone)
    assert done["halkalar"]["toplam"]["cagri"] == 2 + 10 and len(rows) == 2 + 6


def test_canceling_the_writing_records_it_as_iptal_edildi_counts_what_it_spent_and_can_go_on(app, monkeypatch):
    add_video(app)
    assert app.put("/api/settings/claude", json={"claude_max_sessions": 1}).status_code == 200
    start_plan(app)
    decide(app, "plan")
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "slow")
    monkeypatch.setenv("FAKE_CLAUDE_SLEEP", "1.2")
    run = start_writing(app, wait=False)
    end = time.monotonic() + 60
    spending = {}
    while time.monotonic() < end:                                                         # until the job shows its first finished call
        live = step(app, "yazim")
        if live["is"] and any(s["status"] == "done" for s in sessions(live["calisma"], "metin_bolum")):
            spending = (next(j for j in app.get("/api/jobs").json() if j["id"] == live["is"])["progress_info"] or {}).get("harcama") or {}
            if (spending.get("gercek") or {}).get("cagri"):
                break
        time.sleep(0.1)
    assert live["adim"]["status"] == "running" and live["is"]
    assert spending["gercek"]["cagri"] >= 1 and spending["gercek"]["toplam"] > 0 and spending["tahmin"] > 0      # the spending so far
    partial = next(r for r in live["calisma"]["halkalar"]["halkalar"] if r["adim"] == "metin_bolum")
    assert partial["durum"] == "running" and partial["ayrinti"].endswith("/6 bölüm")
    assert app.post(f"/api/jobs/{live['is']}/cancel").status_code == 200                   # "İptal"
    stopped = wait_run(app, run["id"])
    assert stopped["status"] == "paused" and stopped["status_label"] == "iptal edildi" and stopped["reason_text"].startswith("İptal edildi")
    job = next(j for j in app.get("/api/jobs").json() if j["id"] == live["is"])
    assert job["status"] == "canceled"
    after = step(app, "yazim")
    assert after["adim"]["status"] == "error" and after["eylemler"]["resume"] and after["is"] is None
    rows = {r["adim"]: r for r in after["calisma"]["halkalar"]["halkalar"] if r["grup"] != "plan"}
    assert rows["metin_bolum"]["durum_adi"] == "Yarıda kaldı" and rows["metin_bolum"]["cagri"] >= 1 and rows["metin_ceviri"]["durum_adi"] == "Bekliyor"
    assert after["calisma"]["harcama"]["gercek"]["cagri"] >= 1                             # what it spent is counted
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "ok")
    assert app.post("/api/videos/v1/adimlar/yazim/surdur").status_code == 200
    final = wait_run(app, run["id"])
    assert final["status"] == "awaiting_comparison" and len([s for s in sessions(final, "metin_bolum") if s["status"] == "done"]) == 6
    assert statuses(app)["yazim"] == "done"


# ------------------------------------------------------------------------------------------------------------------- Ayarlar, Veri

def test_settings_name_every_claude_step_with_its_place_and_keep_no_content_setting(app):
    view = app.get("/api/settings/claude").json()
    rows = view["options"]["steps"]
    assert [r["key"] for r in rows] == [key for key, _ in claude_settings.CLAUDE_STEPS] and len(rows) == 9
    assert {r["key"]: r["place"] for r in rows} == {"baslik": "Proje · Konu bankası", "baslik_degerlendirme": "Proje · Konu bankası; 1 · Başlık ve vaat",
                                                    "metin_plan": "3 · Plan", "metin_plan_elestiri": "3 · Plan", "metin_bolum": "4 · Yazım",
                                                    "metin_birlestirme": "4 · Yazım", "metin_giris_kapanis": "4 · Yazım",
                                                    "metin_son_okuma": "4 · Yazım", "metin_ceviri": "4 · Yazım"}
    assert [r["screen"] for r in rows][:4] == ["Öneri al (başlık önerisi)", "Kendi başlığını değerlendirme", "Planlayıcı", "Plan eleştirmeni"]
    assert all(r["model_field"] in view["settings"] and r["effort_field"] in view["settings"] for r in rows)
    assert {"claude_call_limit", "claude_job_limit"} <= set(view["settings"]) and [f["field"] for f in view["options"]["limits"]] == [
        "claude_call_limit", "claude_job_limit"]
    assert not any("plan" in key and "stop" in key for key in view["settings"]) and "stop_after_plan" not in view["options"]["text"]
    sites = app.get("/api/isinma-listesi").json()                                          # Veri → Okuma denemeleri: the warm-up list
    assert {"oversee.us", "exclusive30a.com"} <= {s["alan_adi"] for s in sites["siteler"]} and "isinma" in sites["komut"]


# ------------------------------------------------------------------------------------------------------------------- the migration

def test_v20_to_v21_keeps_every_row_and_gives_existing_videos_their_steps(text_env):
    client = open_app(text_env / "data", FakeClock())
    try:
        run = title_run(client)                                                            # title runs with candidates (the topic bank)
        title_run(client, "Rosemary Beach")
        add_video(client)                                                                  # a video with a pack and a written text
        written = start_text(client)
        add_video(client, "v2", with_pack=False)                                           # a video that only has its title
    finally:
        client.__exit__(None, None, None)
    path = text_env / "data" / "studio.sqlite3"
    counts = lambda con: {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in
                          con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    with sqlite3.connect(path) as con:
        con.execute("UPDATE text_runs SET state=json_remove(state,'$.plan_onaylandi')")     # as the old chain left it
        drop_v21(con)
        con.execute("PRAGMA user_version=20")
        before = counts(con)
        videos = con.execute("SELECT id,title_en,title_tr,run_id,candidate,analysis FROM videos ORDER BY id").fetchall()
        runs = con.execute("SELECT * FROM claude_runs ORDER BY id").fetchall()
        jobs = con.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    assert before["claude_runs"] == 3 and before["videos"] == 2 and "video_steps" not in before
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        assert con.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION == 21
        assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        after = counts(con)
        assert after == {**before, **V21_TABLES, "video_steps": 16, "video_step_log": 2}    # nothing lost; two videos × eight steps
        assert [tuple(r) for r in con.execute("SELECT id,title_en,title_tr,run_id,candidate,analysis FROM videos ORDER BY id")] == videos
        assert [tuple(r) for r in con.execute("SELECT * FROM claude_runs ORDER BY id")] == runs
        assert [tuple(r) for r in con.execute("SELECT * FROM jobs ORDER BY id")] == jobs
        steps = {(r["video_id"], r["step"]): r["status"] for r in con.execute("SELECT * FROM video_steps")}
        assert [steps[("v1", key)] for key in workflow.KEYS] == ["approved", "done", "approved", "done", "awaiting_approval", "waiting", "waiting",
                                                                 "waiting"]
        assert [steps[("v2", key)] for key in workflow.KEYS][:3] == ["approved", "ready", "waiting"]
        assert json.loads(con.execute("SELECT state FROM text_runs WHERE id=?", (written["id"],)).fetchone()[0])["plan_onaylandi"] is True
        columns = {r[1]: r for r in con.execute("PRAGMA table_info(videos)")}
        assert {"name", "archived_at"} <= set(columns) and columns["title_en"][3] == 0 and columns["run_id"][3] == 0       # a video may wait for its title
    assert list((text_env / "data" / "backups").glob("studio-v20-*.sqlite3"))              # the backup made before the migration
    again = open_app(text_env / "data", FakeClock())
    try:
        bank = again.get("/api/konu-bankasi").json()                                       # the runs and their candidates are the topic bank
        assert len(bank["calismalar"]) == 3 and bank["aday_sayisi"] == 16
        assert next(r for r in bank["calismalar"] if r["id"] == run["id"])["adaylar"][0]["secilebilir"]
        assert again.get("/api/videolar").json()["videolar"][0]["ilerleme"] in ("1/8", "4/8")
        assert again.post("/api/videolar", json={"ad": "Yeni"}).status_code == 201         # the new table takes a video without a title
    finally:
        again.__exit__(None, None, None)
