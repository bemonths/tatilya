"""HEDEF-04 A-6: 6 · Yayın paketi with the fake Claude.

- The program's check of the chapters: 00:00 first, at least three, at least ten seconds each, ascending, inside the estimated length.
- The step opens when 5 · Kontrol ve ton seçimi is approved; the estimate is one call; the run writes `yayin.json` and `yayin.md` (the
  times marked "tahmini"); the one approval component approves it, and 7 · Seslendirme (not built) stays waiting.
- The model and effort of the step are in Ayarlar → Claude with the other Claude steps; its runs are not in the topic bank.
"""
from studio.ai import publish
from studio.ai import settings as claude_settings
from tests.test_gorev21 import calls_of, settle, statuses, step
from tests.text_helpers import add_video, app, decide, start_text, text_env  # noqa: F401


def texts(chapters, total=600):
    return " ".join(p["metin"] for p in publish.chapter_problems([{"zaman": t} for t in chapters], total))


def test_the_program_checks_the_chapters():
    assert texts(["00:00", "01:00", "02:30"]) == ""
    assert "00:00" in texts(["00:05", "01:00", "02:30"])
    assert "En az 3" in texts(["00:00", "01:00"])
    assert "en az 10 sn" in texts(["00:00", "00:05", "02:30"])
    assert "artan sırada değil" in texts(["00:00", "02:00", "01:00"])
    assert "Son bölüm" in texts(["00:00", "01:00", "09:55"])
    assert "okunamadı" in texts(["00:00", "1:2", "02:00"])
    assert publish.seconds_of("1:02:10") == 3730 and publish.clock(3730) == "1:02:10" and publish.clock(130) == "02:10"


def approve_check(client):
    add_video(client)
    start_text(client)
    shown = step(client, "kontrol")
    assert decide(client, "kontrol", surum=shown["tonlar"][0]["id"]).status_code == 200


def test_publish_runs_one_call_writes_its_files_and_is_approved(app):
    approve_check(app)
    assert statuses(app)["yayin"] == "ready"
    estimate = app.post("/api/videos/v1/yayin/tahmin")
    assert estimate.status_code == 200, estimate.json()
    assert [(r["baslik"], r["cagri"]) for r in estimate.json()["satirlar"]] == [("Yayın paketi", 1)]
    started = app.post("/api/videos/v1/yayin")
    assert started.status_code == 201, started.json()
    settle(app, "v1", "yayin", {"awaiting_approval", "error"})
    view = step(app, "yayin")
    assert view["adim"]["status"] == "awaiting_approval", view["adim"]
    found = view["yayin"]
    chapters = found["paket"]["bolumler"]
    assert chapters[0]["zaman"] == "00:00" and len(chapters) >= 3 and not found["sorunlar"], found
    assert found["zaman"]["tahmini"] and "tahmini" in found["markdown"] and "Chapters:" in found["markdown"]
    folder = (app.data / found["dosya"]).parent
    assert (folder / publish.OUTPUT).is_file() and len(calls_of(folder)) == 1
    prompt = calls_of(folder)[0]["prompt"]
    assert "Adım: yayin" in prompt and "[~00:00]" in prompt
    approved = decide(app, "yayin", **{"not": "Uygun."})
    assert approved.status_code == 200, approved.json()
    assert approved.json()["adim"]["status"] == "approved" and statuses(app)["ses"] == "waiting"
    assert any(v["baslik"] == "Onaylandı" for v in approved.json()["surumler"])


def test_a_package_that_fails_the_check_cannot_be_approved(app, monkeypatch):
    approve_check(app)
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "yayin_kotu")
    assert app.post("/api/videos/v1/yayin").status_code == 201
    settle(app, "v1", "yayin", {"awaiting_approval", "error"})
    found = step(app, "yayin")["yayin"]
    assert any("00:00" in p["metin"] for p in found["sorunlar"])
    refused = decide(app, "yayin")
    assert refused.status_code == 409 and "denetiminden geçmedi" in refused.json()["detail"]


def test_the_step_has_its_model_and_effort_in_settings():
    assert ("yayin", "Yayın paketi") in claude_settings.CLAUDE_STEPS
    assert claude_settings.STEP_PLACES["yayin"] == ("Yayın paketi", "6 · Yayın paketi") and "yayin" in claude_settings.STEP_DEFAULTS
