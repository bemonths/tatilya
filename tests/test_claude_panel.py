"""GÖREV-14 Adım 4 with the fake Claude: the usage panel (measurements of the runs, "Yenile"), the stage and time based progress of a Claude
run, the instruction editor (single source, conflict check, history, going back), the model list and the title suffix setting, and the
v15 -> v16 migration."""
import json
import shutil
import sqlite3
import time
from pathlib import Path

import pytest

from studio.ai import instructions, service as S, settings, title, usage
from studio.database import Database
from studio.destinations import thirty_a
from tests.legacy import V17_TABLES, drop_v17
from tests.test_claude_steps import FAKE, app, calls, finished, folder, start  # noqa: F401  (app: fixture with the fake Claude)


# --- 4a usage panel ------------------------------------------------------------------------------------------------------------

def test_a_runs_usage_reports_are_stored_with_their_time_and_shown(app, monkeypatch):
    assert app.get("/api/claude/usage").json() | {} == {**app.get("/api/claude/usage").json(), "measured": False, "text": "henüz ölçüm yok"}
    monkeypatch.setenv("FAKE_CLAUDE_USAGE", "0.435,0.38")
    view = start(app)
    with app.app.state.db.connect() as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM claude_usage")]
    assert len(rows) == 1 and rows[0]["source"] == "calisma" and rows[0]["run_id"] == view["id"]
    assert (rows[0]["five_hour"], rows[0]["seven_day"]) == (0.435, 0.38) and json.loads(rows[0]["info"])["unifiedWindows"]
    panel = app.get("/api/claude/usage").json()
    assert panel["measured"] and not panel["stale"] and panel["source"] == "calisma"
    assert (panel["windows"]["five_hour"]["percent"], panel["windows"]["seven_day"]["percent"]) == (44, 38)     # halves go up
    assert panel["windows"]["five_hour"]["resets_at"] and panel["windows"]["seven_day"]["label"] == "Haftalık"
    elapsed = app.get(f"/api/claude/runs/{view['id']}").json()["metrics"]["elapsed_s"]   # a fast fake run may round to 0.0 s (CI)
    assert panel["week"]["count"] == 1 and panel["week"]["total_s"] == round(elapsed, 1) and panel["week"]["basis"] == "haftalık pencere"


def test_an_old_measurement_is_marked_and_a_passed_reset_is_shown(app):
    db = app.app.state.db
    now = time.time()
    usage.record(db, {"unifiedWindows": {"five_hour": {"utilization": 0.9, "resetsAt": now - 60},
                                         "seven_day": {"utilization": 0.5, "resetsAt": now + 86400}}, "seen_at": now - 6 * 3600},
                 source="yenile")
    view = usage.view(db, now)
    assert view["stale"] and view["age_s"] >= 6 * 3600
    assert view["windows"]["five_hour"]["reset_passed"] and view["windows"]["five_hour"]["percent"] is None
    assert view["windows"]["seven_day"]["percent"] == 50
    assert usage.record(db, {"status": "allowed", "rateLimitType": "overage"}, source="calisma") is None   # no window: not stored
    older = usage.record(db, {"rateLimitType": "seven_day", "utilization": 0.2, "resetsAt": now + 1000, "seen_at": now}, source="calisma")
    assert older and usage.view(db, now)["windows"]["five_hour"]["known"] is False                      # the old one-window shape


def test_refresh_is_the_smallest_call_and_is_refused_while_a_run_or_an_api_key_is_there(app, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_USAGE", "0.12,0.40")
    view = app.post("/api/claude/usage/refresh").json()
    assert view["measured"] and view["source"] == "yenile" and view["windows"]["seven_day"]["percent"] == 40
    assert view["last_refresh"]["model"] == "haiku" and view["last_refresh"]["effort"] == "low"
    call = [json.loads(line) for line in (app.data / "claude" / "kullanim" / ".fake_claude_calls.jsonl").read_text(encoding="utf-8").splitlines()][-1]
    assert (call["model"], call["effort"], call["tools"], call["max_turns"], call["allowed"]) == ("haiku", "low", "", "1", None)
    assert "Yalnız şu kelimeyi yaz" in call["prompt"] and call["setting_sources"] == ""
    assert app.get("/api/claude/runs").json() == []                                                    # not a step run
    monkeypatch.setenv("FAKE_CLAUDE_NO_EFFORT", "haiku")                                              # a family without effort: once more without it
    again = app.post("/api/claude/usage/refresh").json()
    assert again["last_refresh"]["effort"] is None
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-deneme-anahtari")
    refused = app.post("/api/claude/usage/refresh")
    assert refused.status_code == 409 and "ANTHROPIC_API_KEY" in refused.json()["detail"]
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "slow")
    monkeypatch.setenv("FAKE_CLAUDE_SLEEP", "4")
    running = app.post("/api/claude/title-runs", json={"bolge": "30A geneli"}).json()
    refused = app.post("/api/claude/usage/refresh")
    assert refused.status_code == 409 and "Claude çalışması sürüyor" in refused.json()["detail"]
    finished(app, running["id"])
    monkeypatch.setenv("FAKE_CLAUDE_USAGE", "none")
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "ok")
    silent = app.post("/api/claude/usage/refresh")
    assert silent.status_code == 409 and "kullanım bilgisi vermedi" in silent.json()["detail"]


# --- 4b progress -------------------------------------------------------------------------------------------------------------

def test_the_claude_bar_moves_by_stages_and_by_time(app, monkeypatch):
    assert [S.claude_percent(t, 100) for t in (0, 50, 100, 400)] == [10, 50, 90, 90]
    service = app.app.state.claude
    expected, basis = service.expected_duration("baslik")
    assert expected == 420 and basis == "önceki başarılı çalışma yok; varsayılan 7 dk"
    seen = []
    real_update = app.app.state.db.update_job

    def spy(identifier, **fields):
        if fields.get("progress_info") or fields.get("progress") is not None:
            seen.append((fields.get("progress"), (fields.get("progress_info") or {}).get("asama")))
        return real_update(identifier, **fields)

    monkeypatch.setattr(app.app.state.db, "update_job", spy)
    view = start(app)
    stages = [stage for _, stage in seen if stage]
    assert stages == ["girdiler", "claude", "dogrulama"]
    assert [p for p, stage in seen if stage] == [2, 10, 92] and seen[-1][0] == 100
    job = next(j for j in app.get("/api/jobs").json() if j["kind"] == "claude_run")
    info = job["progress_info"]
    assert info["tur"] == "claude" and info["beklenen_s"] == 420 and info["claude_baslangic"] and info["baslangic"]
    monkeypatch.setattr(app.app.state.db, "update_job", real_update)
    with app.app.state.db.connect() as con:
        con.execute("UPDATE claude_runs SET metrics=json_set(metrics,'$.elapsed_s',300) WHERE id=?", (view["id"],))
    start(app, aile="Deneyim")
    with app.app.state.db.connect() as con:
        con.execute("UPDATE claude_runs SET metrics=json_set(metrics,'$.elapsed_s',500) WHERE id<>?", (view["id"],))
    expected, basis = service.expected_duration("baslik")
    assert expected == 400 and basis == "önceki 2 başarılı çalışmanın ortancası (7 dk)"
    record = json.loads((folder(app, view) / "calisma.json").read_text(encoding="utf-8"))
    assert record["ilerleme_tahmini"]["beklenen_s"] == 420


# --- 4c instruction editor -----------------------------------------------------------------------------------------------------

@pytest.fixture
def own_instructions(tmp_path, monkeypatch):
    """The destination's instruction files copied to a temporary folder: the tests never write the repository's files."""
    copy = tmp_path / "talimatlar"
    shutil.copytree(thirty_a.CLAUDE_INSTRUCTIONS, copy)
    monkeypatch.setattr(thirty_a, "CLAUDE_INSTRUCTIONS", copy)
    monkeypatch.setitem(thirty_a.CHANNEL, "research", copy / "kanal_arastirmasi.md")
    return copy


def test_the_editor_lists_reads_saves_keeps_history_and_refuses_a_file_changed_on_disk(app, own_instructions):
    listed = app.get("/api/claude/instructions").json()
    assert [f["name"] for f in listed][:2] == ["ortak.md", "baslik.md"] and listed[-1]["name"] == "kanal_arastirmasi.md"
    assert listed[-1]["kind"] == "bilgi" and {f["kind"] for f in listed[:-1]} == {"talimat"}
    path = own_instructions / "baslik.md"
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))            # a CRLF file stays CRLF
    opened = app.get("/api/claude/instructions/baslik").json()
    assert "\r" not in opened["text"] and opened["versions"] == []
    saved = app.put("/api/claude/instructions/baslik", json={"text": opened["text"] + "\nYeni satır.\n", "base_sha256": opened["sha256"]}).json()
    assert saved["unchanged"] is False and saved["sha256"] != opened["sha256"] and len(saved["versions"]) == 1
    assert path.read_bytes().endswith(b"Yeni sat\xc4\xb1r.\r\n") and b"\n" not in path.read_bytes().replace(b"\r\n", b"")
    history = app.data / "claude" / "talimat_gecmisi" / "baslik"
    archived = list(history.glob("*.md"))
    assert len(archived) == 1 and archived[0].read_bytes().replace(b"\r\n", b"\n").decode("utf-8") == opened["text"]
    path.write_text(path.read_text(encoding="utf-8") + "Yönetici ekledi.\n", encoding="utf-8")       # changed outside after opening
    refused = app.put("/api/claude/instructions/baslik", json={"text": "benim metnim", "base_sha256": saved["sha256"]})
    assert refused.status_code == 409 and "Yeniden yükle" in refused.json()["detail"]
    assert "Yönetici ekledi." in path.read_text(encoding="utf-8") and len(list(history.glob("*.md"))) == 1
    current = app.get("/api/claude/instructions/baslik").json()
    old = current["versions"][0]
    assert app.get(f"/api/claude/instructions/baslik/versions/{old['id']}").json()["text"] == opened["text"]
    back = app.post(f"/api/claude/instructions/baslik/versions/{old['id']}/restore", json={"base_sha256": current["sha256"]}).json()
    assert back["text"] == opened["text"] and len(back["versions"]) == 2                               # the current one was kept too
    assert app.get("/api/claude/instructions/baslik/versions/..%2F..%2Fortak").status_code == 404
    assert app.get("/api/claude/instructions/yok").status_code == 404
    assert app.put("/api/claude/instructions/baslik", json={"text": "  ", "base_sha256": back["sha256"]}).status_code == 422


def test_the_run_screen_shows_which_instruction_version_it_used(app, own_instructions):
    view = start(app)
    used = {i["name"]: i for i in view["instruction_versions"]}
    assert set(used) == {"ortak.md", "baslik.md"} and all(i["current"] and i["modified_at"] and len(i["short"]) == 8 for i in used.values())
    opened = app.get("/api/claude/instructions/baslik").json()
    app.put("/api/claude/instructions/baslik", json={"text": opened["text"] + "\nEk kural.\n", "base_sha256": opened["sha256"]})
    later = {i["name"]: i for i in app.get(f"/api/claude/runs/{view['id']}").json()["instruction_versions"]}
    assert later["baslik.md"]["current"] is False and later["ortak.md"]["current"] is True


# --- 4d models, 4e title suffix --------------------------------------------------------------------------------------------------

def test_model_aliases_can_be_chosen(app):
    labels = {o["value"]: o["label"] for o in app.get("/api/settings/claude").json()["options"]["models"]}
    assert labels["opus"] == "Opus (en yeni sürüm)" and labels["claude-sonnet-5-5"] == "Sonnet 5.5" and "claude-haiku-5-5" not in labels
    assert app.put("/api/settings/claude", json={"claude_model_baslik": "sonnet"}).status_code == 200
    view = start(app)
    assert calls(app, view)[-1]["model"] == "sonnet"


def test_title_suffixes_are_a_setting_written_into_secim_and_checked(app, monkeypatch):
    shown = app.get("/api/settings/title-suffix").json()
    assert (shown["en"], shown["tr"]) == (" | 30A Florida Vacation", " | 30A Florida Tatili") and shown["defaults"]["en"] == shown["en"]
    view = start(app)
    text = (folder(app, view) / "secim.md").read_text(encoding="utf-8")
    assert '- İngilizce başlık eki: " | 30A Florida Vacation"' in text and '- Türkçe başlık eki: " | 30A Florida Tatili"' in text
    assert all(c["baslik_en"].endswith(" | 30A Florida Vacation") and not c["sorunlar"] for c in view["candidates"])
    assert "`secim.md`'deki İngilizce ekle" in (folder(app, view) / "gorev.md").read_text(encoding="utf-8")
    assert app.put("/api/settings/title-suffix", json={"en": " | 30A Beach Trip"}).json()["en"] == " | 30A Beach Trip"
    assert app.put("/api/settings/title-suffix", json={"tr": "x" * 41}).status_code == 422
    assert app.put("/api/settings/title-suffix", json={"tr": "a\nb"}).status_code == 422
    second = start(app, bolge="Seaside")
    assert '" | 30A Beach Trip"' in (folder(app, second) / "secim.md").read_text(encoding="utf-8")
    assert all(c["baslik_en"].endswith(" | 30A Beach Trip") for c in second["candidates"])
    monkeypatch.setenv("FAKE_CLAUDE_NO_SUFFIX", "1")
    third = start(app, bolge="Rosemary Beach")
    errors = [p["metin"] for c in third["candidates"] for p in c["sorunlar"] if p["seviye"] == "hata"]
    assert errors.count('İngilizce başlık " | 30A Beach Trip" ekiyle bitmiyor.') == len(third["candidates"])
    assert errors.count('Türkçe karşılık " | 30A Florida Tatili" ekiyle bitmiyor.') == len(third["candidates"])
    assert title.title_problems("A" * 101, "B", {}) == ["İngilizce başlık 100 karakteri aşıyor (101 karakter)."]


def test_the_new_suffix_sentence_of_the_title_instructions():
    text = (thirty_a.CLAUDE_INSTRUCTIONS / "baslik.md").read_text(encoding="utf-8")
    assert "Her İngilizce başlık secim.md dosyasında yazan İngilizce başlık ekiyle, Türkçe karşılığı da oradaki Türkçe ekle biter." in text
    assert '" | 30A Florida Vacation" ekiyle biter' not in text


# --- v15 -> v16 ------------------------------------------------------------------------------------------------------------------

def test_v15_to_v16_adds_usage_progress_and_title_edit_and_keeps_rows(tmp_path):
    path = tmp_path / "studio.sqlite3"
    Database(path).initialize()
    with sqlite3.connect(path) as con:       # a v15 file with one video
        drop_v17(con)
        con.execute("DROP TABLE claude_usage")
        con.execute("DROP TABLE job_progress")
        for column in ("method", "method_at"):
            con.execute(f"ALTER TABLE browser_hosts DROP COLUMN {column}")
        for column in ("proposed_title_en", "proposed_title_tr", "user_edited"):
            con.execute(f"ALTER TABLE videos DROP COLUMN {column}")
        con.execute("""INSERT INTO claude_runs (id,destination_id,step,scope_id,status,params,folder,created_at)
            VALUES ('r1','30a','baslik','r1','approved','{}','claude/r1/baslik/r1','2026-10-10T10:00:00+00:00')""")
        con.execute("""INSERT INTO videos (id,destination_id,region_name,title_en,title_tr,family,analysis,params,status,created_at,run_id,candidate)
            VALUES ('v1','30a','Seaside','Seaside first | 30A Florida Vacation','Seaside | 30A Florida Tatili','Deneyim','{}','{}',
            'baslik_secildi','2026-10-10T10:01:00+00:00','r1',0)""")
        con.execute("INSERT INTO browser_hosts (host,url,reason,marked_by,first_seen_at,last_seen_at) VALUES ('example.com',NULL,'doğrulama','deneme','x','x')")
        con.execute("PRAGMA user_version=15")
        before = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in
                  con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        jobs_before = con.execute("SELECT * FROM jobs ORDER BY id").fetchall()
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        assert con.execute("PRAGMA user_version").fetchone()[0] == 17
        assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        after = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in
                 con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        assert after == {**before, "claude_usage": 0, "job_progress": 0, **V17_TABLES}
        video = dict(con.execute("SELECT * FROM videos").fetchone())
        assert (video["proposed_title_en"], video["proposed_title_tr"], video["user_edited"]) == (video["title_en"], video["title_tr"], 0)
        assert dict(con.execute("SELECT method, method_at FROM browser_hosts").fetchone()) == {"method": None, "method_at": None}
        assert [tuple(r) for r in con.execute("SELECT * FROM jobs ORDER BY id")] == [tuple(r) for r in jobs_before]
    assert list((tmp_path / "backups").glob("*-v15-*.sqlite3"))
