"""GÖREV-13 Claude steps through the app with the fake Claude: the topic and title step (inputs, task text, schema and meaning checks,
previous proposals, corrections, choosing a title into a video record), settings reaching the command, isolation, instruction hashes, one
run at a time, an interrupted run, the video's evidence pack and the v14 -> v15 migration."""
import hashlib
import json
import sqlite3
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from studio.ai import store, title
from studio.app import create_app
from studio.database import Database
from studio.destinations import thirty_a
from studio.evidence import video as V
from tests.test_beaches import HEADERS

FAKE = Path(__file__).with_name("fake_claude.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "ok")
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        assert client.put("/api/settings/claude", json={"claude_path": str(FAKE)}).status_code == 200
        client.data = tmp_path
        yield client


def finished(client, run_id, limit=90):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        view = client.get(f"/api/claude/runs/{run_id}").json()
        if view["status"] != "running":
            return view
        time.sleep(0.2)
    raise AssertionError("Claude çalışması bitmedi")


def start(client, bolge="30A geneli", aile=None, note=None):
    body = {"bolge": bolge, **({"aile": aile} if aile else {}), **({"not": note} if note else {})}
    response = client.post("/api/claude/title-runs", json=body)
    assert response.status_code == 201, response.json()
    return finished(client, response.json()["id"])


def folder(client, view):
    return client.data / view["folder"]


def calls(client, view):
    return [json.loads(line) for line in (folder(client, view) / ".fake_claude_calls.jsonl").read_text(encoding="utf-8").splitlines()]


def candidate_errors(view, index):
    return [p["metin"] for p in view["candidates"][index]["sorunlar"] if p["seviye"] == "hata"]


def test_a_valid_proposal_waits_for_approval_with_its_inputs_record_and_markdown(app):
    view = start(app)
    assert view["status"] == "awaiting_approval" and len(view["candidates"]) == 8 and view["general_problems"] == []
    assert all(c["secilebilir"] and not c["sorunlar"] for c in view["candidates"])
    files = {p.name for p in folder(app, view).iterdir()}
    assert {"kanal_plani.md", "kanal_arastirmasi.md", "secim.md", "veri_ozeti_30a.md", "sablonlar.md", "onceki_oneriler.md", "talimat.md",
            "gorev.md", "sema.json", "akis.jsonl", "baslik.json", "baslik.md", "calisma.json"} <= files
    assert "veri_ozeti_mahalle.md" not in files                                            # 30A geneli: no neighborhood summary
    assert (folder(app, view) / "kanal_plani.md").read_bytes() == thirty_a.CHANNEL["plan"].read_bytes()
    assert "## Ek — Kanal ve içerik planı" in (folder(app, view) / "kanal_plani.md").read_text(encoding="utf-8")
    assert (folder(app, view) / "onceki_oneriler.md").read_text(encoding="utf-8").endswith("Henüz önerilmiş başlık yok.\n")
    first = view["candidates"][0]
    hook = first["kanca"]["kanitlar"][0]
    assert hook["paket_id"] and hook["ifade"] and hook["deger_metni"]                     # the value comes from the summary's pack
    markdown = (folder(app, view) / "baslik.md").read_text(encoding="utf-8")
    assert markdown.index("## Başlıklar") < markdown.index("## 1. ") and first["baslik_en"] in markdown and hook["kimlik"] in markdown
    record = json.loads((folder(app, view) / "calisma.json").read_text(encoding="utf-8"))
    hashes = {f["path"]: f["sha256"] for f in record["talimat_surumu"]["files"]}
    for path in ("studio/destinations/thirty_a_claude/ortak.md", "studio/destinations/thirty_a_claude/baslik.md", "studio/ai/schemas/baslik.schema.json"):
        assert hashes[path] == hashlib.sha256((Path(__file__).resolve().parents[1] / path).read_bytes()).hexdigest()
    assert record["talimat_surumu"]["birlesik_talimat"] == hashlib.sha256((folder(app, view) / "talimat.md").read_bytes()).hexdigest()
    assert record["secim"] == {"bolge": "30A geneli", "bolge_id": None, "aile": "hepsi", "not": "",
                               "baslik_eki": {"en": " | 30A Florida Vacation", "tr": " | 30A Florida Tatili"}} and record["paketler"]["veri_ozeti_30a.md"]
    assert record["calisma_sonucu"]["session_id"] and record["calisma_sonucu"]["metrics"]["tokens"]["output"] == 800
    run = app.get("/api/claude/runs").json()[0]
    assert run["session_id"] and run["metrics"]["turns"] == 3 and run["model"] == "claude-opus-5-5" and run["effort"] == "high"
    job = next(j for j in app.get("/api/bootstrap").json()["jobs"] if j["kind"] == "claude_run")
    texts = [entry["text"] for entry in job["log"]]
    assert job["status"] == "done" and any(t.startswith("Tur 1/30 · Okuyor: secim.md") for t in texts)
    assert any(t.startswith("Claude bitti: 3 tur") for t in texts) and any("Veri özeti yeniden üretiliyor (ilk-video)" in t for t in texts)


def test_the_instructions_are_the_destination_files_verbatim_with_the_filled_schema(app):
    view = start(app)
    combined = (folder(app, view) / "talimat.md").read_text(encoding="utf-8")
    common = (thirty_a.CLAUDE_INSTRUCTIONS / "ortak.md").read_text(encoding="utf-8").strip()
    step = (thirty_a.CLAUDE_INSTRUCTIONS / "baslik.md").read_text(encoding="utf-8").strip()
    assert combined.index(common) == 0 and combined.index(step) > len(common)
    schema = json.loads((folder(app, view) / "sema.json").read_text(encoding="utf-8"))
    assert schema["$defs"]["aile"]["enum"] == list(thirty_a.CHANNEL["families"])
    assert schema["$defs"]["bolge"]["enum"][0] == "30A geneli" and "Rosemary Beach" in schema["$defs"]["bolge"]["enum"]
    assert json.dumps(schema, ensure_ascii=False, indent=1) in combined


def test_command_settings_isolation_and_environment(app, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    view = start(app)
    call = calls(app, view)[0]
    argv = call["argv"]
    assert (call["model"], call["effort"], call["tools"], call["max_turns"]) == ("claude-opus-5-5", "high", "Read,Glob,Grep,Write,Edit", "30")
    assert call["allowed"] == ["Read(./**)", "Write(./baslik.json)", "Edit(./baslik.json)"] and call["setting_sources"] == ""
    assert "--strict-mcp-config" in argv and "--disable-slash-commands" in argv and argv[argv.index("--permission-mode") + 1] == "dontAsk"
    assert call["env"] == {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "ENABLE_CLAUDEAI_MCP_SERVERS": "0", "DISABLE_AUTOUPDATER": "1",
                           "CLAUDECODE": None, "CLAUDE_CODE_ENTRYPOINT": None}
    assert call["prompt"].startswith("Adım: baslik\nTür: ilk çalışma\nBölge: 30A geneli")
    # "Genel varsayılan" takes the general default; an empty general default gives no option at all
    assert app.put("/api/settings/claude", json={"claude_model": "claude-sonnet-5", "claude_effort": "low", "claude_model_baslik": "inherit",
                                                 "claude_effort_baslik": "inherit", "claude_max_turns_baslik": 12}).status_code == 200
    second = calls(app, start(app, aile="Deneyim"))[0]
    assert (second["model"], second["effort"], second["max_turns"]) == ("claude-sonnet-5", "low", "12")
    app.put("/api/settings/claude", json={"claude_model": "", "claude_effort": ""})
    third = calls(app, start(app, aile="Genel planlama"))[0]
    assert "--model" not in third["argv"] and "--effort" not in third["argv"]
    refused = app.put("/api/settings/claude", json={"claude_max_turns_baslik": 500})
    assert refused.status_code == 422 and "Tur sınırı" in refused.json()["detail"]


def test_an_output_against_the_schema_is_an_error_with_its_problems(app, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "schema_error")
    view = start(app)
    assert view["status"] == "error" and "şemaya uymuyor" in view["error"] and view["candidates"] == []
    assert any("'kapak_fikri' alanı eksik" in p["metin"] for p in view["problems"])
    assert view["actions"] == {"select": False, "reject": False, "correct": True}
    for scenario, words in (("invalid_json", "geçerli bir JSON değil"), ("missing_file", "baslik.json dosyasını yazmadı")):
        monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", scenario)
        assert words in start(app)["error"]


def test_an_unknown_evidence_id_and_a_section_without_evidence_are_problems_of_their_candidate(app, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "bad_id")
    view = start(app)
    assert view["status"] == "awaiting_approval"
    assert candidate_errors(view, 0) == ["Kanca: var olmayan kanıt kimliği K9999 (veri_ozeti_30a.md)."] and not view["candidates"][0]["secilebilir"]
    refused = app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 0})
    assert refused.status_code == 409 and "doğrulama hatası" in refused.json()["detail"]
    assert view["candidates"][0]["kanca"]["kanitlar"][0]["durum"] == "bulunamadi" and view["candidates"][1]["secilebilir"]
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "no_evidence_section")
    assert candidate_errors(start(app), 0) == ["İçerik planının 2. bölümü (Bölüm 2) kanıtsız."]


def test_a_neighborhood_gets_its_summary_and_a_candidate_of_another_neighborhood_is_refused(app, monkeypatch):
    view = start(app, bolge="Rosemary Beach")
    run_folder = folder(app, view)
    assert (run_folder / "veri_ozeti_mahalle.md").is_file()
    assert (run_folder / "veri_ozeti_mahalle.md").read_text(encoding="utf-8").startswith("# Mahalle rehberi — yazar özeti")
    assert "rosemary-beach" in (run_folder / "secim.md").read_text(encoding="utf-8")
    assert "`veri_ozeti_mahalle.md` — Rosemary Beach" in (run_folder / "gorev.md").read_text(encoding="utf-8")
    assert view["status"] == "awaiting_approval" and all(c["bolge"] == "Rosemary Beach" for c in view["candidates"])
    assert {k["dosya"] for c in view["candidates"] for k in c["kanca"]["kanitlar"]} == {"veri_ozeti_30a.md", "veri_ozeti_mahalle.md"}
    assert view["candidates"][0]["sablon"] == "mahalle-rehberi" and view["candidates"][0]["parametreler"] == {"mahalle": "rosemary-beach"}
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "other_region")
    other = start(app, bolge="Rosemary Beach")
    assert any("başka bir bölgeye ait" in text for text in candidate_errors(other, 1))


def test_a_chosen_family_refuses_a_candidate_of_another_family(app, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "wrong_family")
    view = start(app, aile="Masraf ve bütçe")
    assert "İçerik ailesi: Masraf ve bütçe" in (folder(app, view) / "secim.md").read_text(encoding="utf-8")
    assert candidate_errors(view, 1) == [f"Aday \"{view['candidates'][1]['aile']}\" ailesinden; bu çalışmada seçilen aile \"Masraf ve bütçe\"."]
    assert not any(p["seviye"] == "hata" for c in view["candidates"][2:] for p in c["sorunlar"])
    refused = app.post("/api/claude/title-runs", json={"bolge": "30A geneli", "aile": "Uydurma aile"})
    assert refused.status_code == 409 and "İçerik ailesi" in refused.json()["detail"]
    assert app.post("/api/claude/title-runs", json={"bolge": "Atlantis"}).status_code == 409


def test_previous_proposals_are_given_and_a_repeated_title_is_refused(app, monkeypatch):
    first = start(app)
    chosen = app.post(f"/api/claude/runs/{first['id']}/select", json={"aday": 2, "not": "bunu seçtim"})
    assert chosen.status_code == 201
    second = start(app, bolge="Rosemary Beach")
    earlier = (folder(app, second) / "onceki_oneriler.md").read_text(encoding="utf-8")
    for candidate in first["candidates"]:
        assert candidate["baslik_en"].replace("|", "\\|") in earlier                   # table cells escape the suffix's bar
    cell = lambda text: text.replace("|", "\\|")
    assert f"| {cell(first['candidates'][2]['baslik_en'])} | {cell(first['candidates'][2]['baslik_tr'])} | seçildi |" in earlier
    assert second["general_problems"] == [] and all(not candidate_errors(second, c["sira"]) for c in second["candidates"])
    # an empty database's neighborhood summary has 'veri yok' rows: citing one is a warning, not an error
    assert {p["seviye"] for c in second["candidates"] for p in c["sorunlar"]} <= {"uyari"}
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "repeat_title")
    third = start(app)
    errors = candidate_errors(third, 0)
    assert len(errors) == 1 and errors[0].startswith("Başlık daha önce önerildi")         # case and punctuation do not make it new
    assert title.normalized("Why People Pay So Much — to Stay?!") == title.normalized("why people pay so much to stay")


def test_turn_limit_and_usage_limit_are_turkish_errors(app, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "max_turns")
    view = start(app)
    assert view["status"] == "error" and "tur sınırına ulaştı (30 tur)" in view["error"]
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "usage_limit")
    assert "kullanım sınırına ulaşıldı" in start(app)["error"]
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "version_too_old")
    assert "claude update" in start(app)["error"]


def test_a_correction_opens_a_new_session_with_the_note_and_the_previous_output(app):
    first = start(app)
    assert app.post(f"/api/claude/runs/{first['id']}/correct", json={"not": ""}).status_code == 409   # a correction needs a note
    response = app.post(f"/api/claude/runs/{first['id']}/correct", json={"not": "Daha çok masraf başlığı olsun."})
    assert response.status_code == 201
    second = finished(app, response.json()["id"])
    assert second["correction_of"] == first["id"] and second["scope_id"] == first["scope_id"] and second["folder"] != first["folder"]
    assert second["session_id"] != first["session_id"]                                   # a new session, not --resume
    call = calls(app, second)[0]
    assert "--resume" not in call["argv"] and "Tür: düzeltme" in call["prompt"]
    assert "--- not başı ---\nDaha çok masraf başlığı olsun.\n--- not sonu ---" in call["prompt"]
    previous = json.loads((folder(app, second) / "onceki_cikti.json").read_text(encoding="utf-8"))
    assert previous["adaylar"][0]["baslik_en"] == first["candidates"][0]["baslik_en"]
    assert second["candidates"][0]["baslik_en"] == first["candidates"][0]["baslik_en"] + " (revised)"
    assert second["general_problems"] == []                                              # its own earlier titles are not "repeated"
    assert "Henüz önerilmiş başlık yok." in (folder(app, second) / "onceki_oneriler.md").read_text(encoding="utf-8")
    assert app.post(f"/api/claude/runs/{second['id']}/reject", json={"not": "olmadı"}).json()["status"] == "rejected"
    assert app.post(f"/api/claude/runs/{second['id']}/reject", json={}).status_code == 409


def test_choosing_a_title_makes_a_video_record_with_the_whole_analysis(app):
    view = start(app, bolge="Rosemary Beach")
    response = app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 1, "not": "Bunu çekelim."})
    assert response.status_code == 201
    video = response.json()
    candidate = view["candidates"][1]
    assert (video["title_en"], video["title_tr"], video["family"], video["region_name"], video["region_id"]) == (
        candidate["baslik_en"], candidate["baslik_tr"], candidate["aile"], "Rosemary Beach", "rosemary-beach")
    assert video["template_key"] == "mahalle-rehberi" and video["params"] == {"mahalle": "rosemary-beach"} and video["status"] == "baslik_secildi"
    analysis = video["analysis"]
    assert analysis["izleyici_sorusu"] == candidate["izleyici_sorusu"] and analysis["kapak_fikri"] == candidate["kapak_fikri"]
    assert analysis["calisma"] == view["id"] and analysis["aday"] == 1 and analysis["secim_notu"] == "Bunu çekelim."
    hook = analysis["kanca"]["kanitlar"][0]
    assert hook["paket_id"] and hook["deger_metni"] and hook["ifade"] and len(analysis["icerik_plani"]) == 5
    assert set(analysis["paketler"]) == {"veri_ozeti_30a.md", "veri_ozeti_mahalle.md"}
    assert app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 1}).status_code == 409
    after = app.get(f"/api/claude/runs/{view['id']}").json()
    assert after["status"] == "approved" and after["candidates"][1]["video_id"] == video["id"] and after["actions"]["reject"] is False
    assert app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 3}).status_code == 201   # more titles may be chosen
    assert [v["title_en"] for v in app.get("/api/videos").json()] == [view["candidates"][3]["baslik_en"], candidate["baslik_en"]]


def test_a_videos_evidence_pack_starts_with_its_analysis_and_maps_the_cited_rows(app):
    view = start(app, bolge="Rosemary Beach")
    video = app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 0}).json()
    response = app.post(f"/api/videos/{video['id']}/evidence-pack")
    assert response.status_code == 201
    pack_id = response.json()["id"]
    assert response.json()["video_id"] == video["id"]
    summary = app.get(f"/api/evidence-packs/{pack_id}/yazar-ozeti").text
    full = app.get(f"/api/evidence-packs/{pack_id}/markdown").text
    for text in (summary, full):
        head = text[:text.index("## Kaynakların son çekimi")]
        assert "## Video" in head and video["title_en"] in head and video["analysis"]["izleyici_sorusu"] in head and "### İçerik planı" in head
    pack = app.get(f"/api/evidence-packs/{pack_id}/json").json()
    statuses = {k["dosya"]: k["yeni_durum"] for p in pack["video"]["icerik_plani"] for k in p["kanitlar"]}
    assert statuses["veri_ozeti_mahalle.md"] == V.SAME                                  # the neighborhood pack's own rows are found again
    assert app.get("/api/videos").json()[0]["status"] == "paket_hazir" and app.get("/api/videos").json()[0]["packs"][0]["id"] == pack_id
    general = start(app)
    no_template = next(c for c in general["candidates"] if c["sablon"] is None)
    other = app.post(f"/api/claude/runs/{general['id']}/select", json={"aday": no_template["sira"]}).json()
    refused = app.post(f"/api/videos/{other['id']}/evidence-pack")
    assert refused.status_code == 409 and "yeni bir şablon gerekir" in refused.json()["detail"]


def test_cited_rows_are_matched_by_source_row_and_value():
    old = {"id": "K0004", "blok": "references", "kaynak": {"referans": "a"}, "ifade": "x", "deger": "5", "birim": "mil", "durum": "var"}
    cited = V.cited(old, dosya="veri_ozeti_30a.md", pack_id="p1")
    same = [{"id": "K0010", "blok": "references", "kaynak": {"referans": "a"}, "ifade": "x", "deger": "5", "birim": "mil", "durum": "var"}]
    changed = [{**same[0], "deger": "6"}]
    assert V.match(cited, same) == (V.SAME, same[0]) and V.match(cited, changed)[0] == V.CHANGED and V.match(cited, [])[0] == V.ABSENT
    assert V.evidence_line(V.mapped(cited, changed)).endswith("bu pakette K0010, değeri farklı: 6 mil")
    assert V.evidence_line(V.mapped(cited, [])).endswith("bu pakette yok")


def test_one_claude_run_at_a_time_and_an_interrupted_run_becomes_an_error(app, monkeypatch, tmp_path):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "slow")
    monkeypatch.setenv("FAKE_CLAUDE_SLEEP", "8")
    running = app.post("/api/claude/title-runs", json={"bolge": "30A geneli"})
    assert running.status_code == 201
    second = app.post("/api/claude/title-runs", json={"bolge": "Seaside"})
    assert second.status_code == 409 and "zaten sürüyor" in second.json()["detail"]
    job = next(j for j in app.get("/api/bootstrap").json()["jobs"] if j["kind"] == "claude_run")
    app.post(f"/api/jobs/{job['id']}/cancel")
    view = finished(app, running.json()["id"])
    assert view["status"] == "error" and view["error"] == "İş iptal edildi; Claude durduruldu."
    db = Database(tmp_path / "other" / "studio.sqlite3")
    db.initialize()
    with db.connect() as con:
        store.insert_run(con, run_id="r1", destination_id="30a", step="baslik", scope_id="r1", job_id=None, params={"bolge": "30A geneli"},
                         folder="claude/r1/baslik/r1")
    store.recover(db)
    assert store.run(db, "r1")["status"] == "error" and store.run(db, "r1")["error"] == "Uygulama kapanırken yarıda kaldı."


def test_v14_to_v15_adds_runs_videos_and_the_pack_link_and_keeps_rows(tmp_path):
    path = tmp_path / "studio.sqlite3"
    Database(path).initialize()
    with sqlite3.connect(path) as con:       # a v14 file: without the v15 tables and column (and the v16 additions)
        con.execute("DROP TABLE claude_usage")
        con.execute("DROP TABLE job_progress")
        con.execute("ALTER TABLE browser_hosts DROP COLUMN method")
        con.execute("ALTER TABLE browser_hosts DROP COLUMN method_at")
        con.execute("DROP INDEX videos_destination")
        con.execute("DROP TABLE videos")
        con.execute("DROP INDEX one_running_claude")
        con.execute("DROP INDEX claude_runs_destination")
        con.execute("DROP TABLE claude_runs")
        con.execute("ALTER TABLE evidence_packs DROP COLUMN video_id")
        con.execute("PRAGMA user_version=14")
        before = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in
                  con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 16
        assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        after = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in
                 con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        assert after == {**before, "claude_runs": 0, "videos": 0, "claude_usage": 0, "job_progress": 0}
        assert "video_id" in [r[1] for r in con.execute("PRAGMA table_info(evidence_packs)")]
    assert list((tmp_path / "backups").glob("*-v14-*.sqlite3"))


def test_summary_packs_are_reused_while_fresh_and_made_again_when_stale(app, monkeypatch):
    from studio.evidence import pack as P
    first, second = start(app), start(app, aile="Deneyim")
    packs = [json.loads((folder(app, v) / "calisma.json").read_text(encoding="utf-8"))["paketler"]["veri_ozeti_30a.md"] for v in (first, second)]
    assert packs[0] == packs[1]
    texts = [e["text"] for e in next(j for j in app.get("/api/bootstrap").json()["jobs"] if j["kind"] == "claude_run")["log"]]
    assert any(t.startswith("Veri özeti güncel (30A verisinin yazar özeti") for t in texts)
    monkeypatch.setattr(P, "latest_done_run", lambda db, destination_id: "2999-01-01T00:00:00+00:00")   # data collected after the pack
    third = start(app, aile="Genel planlama")
    record = json.loads((folder(app, third) / "calisma.json").read_text(encoding="utf-8"))
    assert record["paketler"]["veri_ozeti_30a.md"] != packs[0]
    assert record["girdiler"][3]["paket_uretildi"] == "veri paketten sonra yeniden çekildi"


def test_the_api_key_is_warned_about_in_settings_options_and_the_run(app, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-deneme-anahtari")
    warning = app.get("/api/claude/options").json()["claude"]["api_key_warning"]
    assert warning.startswith("ANTHROPIC_API_KEY ortam değişkeni tanımlı") and app.get("/api/settings/claude").json()["info"]["api_key_warning"] == warning
    view = start(app)
    texts = [e["text"] for e in next(j for j in app.get("/api/bootstrap").json()["jobs"] if j["kind"] == "claude_run")["log"]]
    assert warning in texts and calls(app, view)[0]["api_key_set"] is True
    assert "sk-ant-deneme" not in (folder(app, view) / "calisma.json").read_text(encoding="utf-8")
