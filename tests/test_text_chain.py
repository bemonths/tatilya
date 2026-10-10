"""GÖREV-15 Adım 4–6 with the fake Claude: the writing chain end to end (two tones on one plan, "Bu tonla da yaz", "Planı yeniden yap"),
the returns of the plan (program check, critic), an invalid answer asked once more, the section writers within the session limit, the usage
limit wait that goes on by itself, transient waits, "Durdur" and "Devam", a run cut by the app closing, "Plandan sonra dur", other Claude
runs refused while a text run works, the combined instructions with the voice and the tone, the ids of baslik_analizi.md, the pack made
again when missing or stale, the files of a version, the choice and the v16 → v17 migration."""
import json
import sqlite3
import time
import uuid

from studio.ai import settings as claude_settings
from studio.database import Database
from studio.text import engine as E
from tests.legacy import V17_TABLES, drop_v17
from tests.text_helpers import FakeClock, add_video, app, open_app, sessions, start_text, text_env, text_job, wait_run  # noqa: F401

TWO = ("arastirmaci_dost", "hikaye_anlaticisi")


def folder_of(client, session):
    return client.data / "claude" / "v1" / session["step"] / session["id"]


def test_two_tones_on_one_plan_end_to_end(app):
    add_video(app)
    view = start_text(app, TWO)
    assert view["status"] == "awaiting_comparison" and view["status_label"] == "karşılaştırma bekliyor"
    assert len(sessions(view, "metin_plan")) == 1 and len(sessions(view, "metin_plan_elestiri")) == 1
    for tone in TWO:
        assert len(sessions(view, "metin_bolum", tone)) == 6
        for step in ("metin_birlestirme", "metin_giris_kapanis", "metin_son_okuma", "metin_ceviri"):
            assert len(sessions(view, step, tone)) == 1
    versions = view["surumler"]
    assert [(v["number"], v["tone_file"], v["tone_name"]) for v in versions] == [(1, "arastirmaci_dost", "Araştırmacı dost"),
                                                                                  (2, "hikaye_anlaticisi", "Hikâye anlatıcısı")]
    assert all(v["red"] == 1 and v["yellow"] == 1 and v["words"] > 2000 for v in versions)
    plans = [json.loads((folder_of(app, s) / "plan.json").read_text(encoding="utf-8")) for s in sessions(view, "metin_bolum")]
    assert all(p == view["plan"] for p in plans)                         # every section writer of both tones had the one plan
    job = text_job(app)
    assert job["status"] == "done" and job["message"] == "Bütün tonların metni yazıldı; karşılaştırma bekliyor."
    assert job["progress"] == 100 and job["progress_info"]["tur"] == "metin"
    assert any(e["text"].startswith("Araştırmacı dost: 1. sürüm kaydedildi") for e in job["log"])


def test_the_combined_instructions_carry_the_voice_and_tone_only_where_given(app):
    add_video(app)
    view = start_text(app)
    plan_text = (folder_of(app, sessions(view, "metin_plan")[0]) / "talimat.md").read_text(encoding="utf-8")
    section = sessions(view, "metin_bolum")[0]
    section_text = (folder_of(app, section) / "talimat.md").read_text(encoding="utf-8")
    assert plan_text.startswith("# 30A Studio") or "Video metninin planı" in plan_text
    assert "Anlatıcının sesi" not in plan_text and "# Ton:" not in plan_text and "# Çıktı şeması: `plan.json`" in plan_text
    order = [section_text.index(mark) for mark in ("# Anlatıcının sesi — her tonda aynı", "# Ton: Araştırmacı dost", "# Bir bölümün metni",
                                                   "# Çıktı şeması: `bolum.json`")]
    assert order == sorted(order) and section_text.index("# Anlatıcının sesi") > 0
    record = json.loads((folder_of(app, section) / "calisma.json").read_text(encoding="utf-8"))
    tone_file = app.env / "tonlar" / "arastirmaci_dost.md"
    import hashlib
    assert record["ton"] == {"dosya": "arastirmaci_dost", "ad": "Araştırmacı dost", "sha256": hashlib.sha256(tone_file.read_bytes()).hexdigest()}
    paths = [f["path"] for f in record["talimat_surumu"]["files"]]
    assert paths[:2] == ["studio/destinations/thirty_a_claude/ortak.md", "studio/destinations/thirty_a_claude/ses_ortak.md"]
    assert paths[2].startswith("ton-arastirmaci_dost") and paths[3] == "studio/destinations/thirty_a_claude/metin_bolum.md"
    critic = (folder_of(app, sessions(view, "metin_plan_elestiri")[0]) / "talimat.md").read_text(encoding="utf-8")
    assert "# Ton:" not in critic
    for step in ("metin_birlestirme", "metin_giris_kapanis", "metin_son_okuma", "metin_ceviri"):
        assert "# Ton: Araştırmacı dost" in (folder_of(app, sessions(view, step)[0]) / "talimat.md").read_text(encoding="utf-8")


def test_the_title_analysis_speaks_the_video_packs_ids(app):
    add_video(app)
    view = start_text(app)
    analysis = (folder_of(app, sessions(view, "metin_plan")[0]) / "baslik_analizi.md").read_text(encoding="utf-8")
    pack = app.get(f"/api/evidence-packs/{view['pack_id']}/json").json()
    pack_ids = {row["id"] for s in pack["sections"] for row in s["rows"]}
    plan_ids = [e["yeni_kimlik"] for p in pack["video"]["icerik_plani"] for e in p["kanitlar"]]
    for line in [l for l in analysis.splitlines() if l[:2] in ("1.", "2.", "3.", "4.", "5.")]:
        cited = line.split("kanıtlar: ")[1].split(", ")
        assert all(i in pack_ids for i in cited)
    assert set(plan_ids) <= pack_ids
    assert "Kanıtlar: (pakette yok" in analysis                         # the hook's row is not one of the plan's blocks
    assert "## İzleyicinin sorusu\n\nNe zaman gitmeli?" in analysis


def test_bu_tonla_da_yaz_and_plani_yeniden_yap(app):
    add_video(app)
    first = start_text(app, ("arastirmaci_dost",))
    more = app.post(f"/api/metin/calismalar/{first['id']}/ton", json={"ton": "pratik_planlayici"})
    assert more.status_code == 201
    view = wait_run(app, first["id"])
    assert [v["tone_file"] for v in view["surumler"]] == ["arastirmaci_dost", "pratik_planlayici"]
    assert len(sessions(view, "metin_plan")) == 1 and len(sessions(view, "metin_bolum", "arastirmaci_dost")) == 6
    again = app.post(f"/api/metin/calismalar/{first['id']}/ton", json={"ton": "pratik_planlayici"})
    assert again.status_code == 409 and again.json()["detail"] == "Bu tonla bu planın metni zaten yazıldı."
    replanned = app.post(f"/api/metin/calismalar/{first['id']}/yeniden-planla", json={"tonlar": ["vlogger"]})
    assert replanned.status_code == 201 and replanned.json()["replan_of"] == first["id"]
    second = wait_run(app, replanned.json()["id"])
    assert len(sessions(second, "metin_plan")) == 1 and [v["number"] for v in second["surumler"]] == [3]
    old = app.get(f"/api/metin/calismalar/{first['id']}").json()
    assert len(old["surumler"]) == 2 and old["status"] == "awaiting_comparison"
    assert [v["number"] for v in app.get("/api/videos/v1/metin").json()["surumler"]] == [1, 2, 3]


def test_the_plan_goes_back_once_for_an_unknown_id_and_then_errors(app, monkeypatch):
    add_video(app)
    monkeypatch.setenv("FAKE_CLAUDE_TEXT", "plan_bad_id")
    view = start_text(app)
    rounds = sessions(view, "metin_plan")
    assert [s["round"] for s in rounds] == [1, 2] and view["status"] == "awaiting_comparison"
    assert "K9999" not in json.dumps(view["plan"])
    task = (folder_of(app, rounds[1]) / "gorev.md").read_text(encoding="utf-8")
    assert "DÖNÜŞ SEBEBİ\nProgramın plan denetimi: Planda pakette olmayan kanıt kimlikleri var: K9999." in task
    assert (folder_of(app, rounds[1]) / "onceki_cikti.json").is_file()
    add_video(app, "v2")
    monkeypatch.setenv("FAKE_CLAUDE_TEXT", "plan_bad_id_always")
    failed = start_text(app, video_id="v2")
    assert failed["status"] == "error" and failed["reason"] == "plan_kimlik" and "iki kez pakette olmayan kanıt kimliği" in failed["reason_text"]
    assert not failed["eylemler"]["devam"] and app.post(f"/api/metin/calismalar/{failed['id']}/devam").status_code == 409


def test_the_critic_sends_the_plan_back_once_and_the_new_plan_is_not_criticised_again(app, monkeypatch):
    add_video(app)
    monkeypatch.setenv("FAKE_CLAUDE_TEXT", "critic_redo")
    view = start_text(app)
    assert [s["round"] for s in sessions(view, "metin_plan")] == [1, 2] and len(sessions(view, "metin_plan_elestiri")) == 1
    task = (folder_of(app, sessions(view, "metin_plan")[1]) / "gorev.md").read_text(encoding="utf-8")
    assert "Plan eleştirmeninin notları: (1) Merak üçüncü bölümde kopuyor." in task
    assert view["elestiri"] == {"notlar": ["Merak üçüncü bölümde kopuyor."], "yeniden_yap": True} and view["plan_turu"] == 2
    assert view["plan"]["notlar"] == ["Sahte plan (yeniden)."]


def test_an_invalid_answer_is_asked_once_more_then_the_run_pauses_and_devam_starts_that_step_again(app, monkeypatch):
    add_video(app)
    monkeypatch.setenv("FAKE_CLAUDE_TEXT", "invalid:metin_birlestirme")
    view = start_text(app)
    merges = sessions(view, "metin_birlestirme")
    assert [(s["attempt"], s["status"]) for s in merges] == [(1, "invalid"), (2, "done")] and view["status"] == "awaiting_comparison"
    task = (folder_of(app, merges[1]) / "gorev.md").read_text(encoding="utf-8")
    assert "DÖNÜŞ SEBEBİ\nŞema: dosyanın kökü: 'gecisler' alanı eksik." in task
    add_video(app, "v2")
    monkeypatch.setenv("FAKE_CLAUDE_TEXT", "invalid:metin_giris_kapanis:2")
    paused = start_text(app, video_id="v2")
    assert paused["status"] == "paused" and paused["reason"] == "gecersiz_cevap" and paused["eylemler"]["devam"]
    assert "iki denemede de" in paused["reason_text"]
    done_before = {s["id"] for s in paused["oturumlar"] if s["status"] == "done"}
    monkeypatch.setenv("FAKE_CLAUDE_TEXT", "")
    assert app.post(f"/api/metin/calismalar/{paused['id']}/devam").status_code == 200
    view = wait_run(app, paused["id"])
    assert view["status"] == "awaiting_comparison" and done_before <= {s["id"] for s in view["oturumlar"]}
    assert len(sessions(view, "metin_plan")) == 1 and len(sessions(view, "metin_bolum")) == 6     # nothing finished ran again
    assert [s["status"] for s in sessions(view, "metin_giris_kapanis")] == ["invalid", "invalid", "done"]


def test_the_section_writers_run_side_by_side_within_the_session_limit(app, monkeypatch):
    add_video(app)
    assert app.put("/api/settings/claude", json={"claude_max_sessions": 2}).status_code == 200
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "slow")
    monkeypatch.setenv("FAKE_CLAUDE_SLEEP", "0.6")
    view = start_text(app)
    assert view["status"] == "awaiting_comparison"
    log = [json.loads(line) for line in (app.env / "sahte_oturumlar.jsonl").read_text(encoding="utf-8").splitlines()]
    sections = [e for e in log if e["step"] == "metin_bolum"]
    assert len(sections) == 6
    peak = max(sum(1 for o in sections if o["start"] < e["start"] + 0.05 < o["end"]) for e in sections)
    assert peak == 2                                                     # side by side, never more than the limit
    assert app.put("/api/settings/claude", json={"claude_max_sessions": 7}).status_code == 422


def test_the_usage_threshold_holds_new_sessions_and_the_run_goes_on_by_itself(app, monkeypatch):
    add_video(app)
    monkeypatch.setenv("FAKE_CLAUDE_USAGE", "0.95,0.20")      # the first session reports 95 % of the 5-hour window (threshold 90 %)
    view = start_text(app)
    assert view["status"] == "awaiting_comparison"
    job = text_job(app)
    waits = [e["text"] for e in job["log"] if e["text"].startswith("Claude kullanım sınırı:")]
    assert waits and waits[0].endswith("'te kendiliğinden sürecek.")
    assert any("Kullanım eşiğe geldi (5 saatlik pencere)" in e["text"] for e in job["log"])
    assert any(e["text"] == "Kullanım sınırı beklemesi bitti; çalışma sürüyor." for e in job["log"])
    assert any(s >= 3600 * 0.5 for s in [sum(app.clock.slept)])           # the clock went past the reset (+2 minutes)


def test_claudes_limit_message_waits_for_the_reset_and_tries_again(app, monkeypatch):
    add_video(app)
    monkeypatch.setenv("FAKE_CLAUDE_TEXT", "limit:metin_son_okuma")
    monkeypatch.setenv("FAKE_CLAUDE_LIMIT_RESET", "600")
    view = start_text(app)
    assert [s["status"] for s in sessions(view, "metin_son_okuma")] == ["limit", "done"] and view["status"] == "awaiting_comparison"
    assert 600 <= sum(app.clock.slept) <= 600 + E.LIMIT_MARGIN_S + 5
    assert any("Claude kullanım sınırına ulaşıldı" in e["text"] for e in text_job(app)["log"])


def test_transient_failures_wait_1_5_15_minutes_then_pause(app, monkeypatch):
    add_video(app)
    monkeypatch.setenv("FAKE_CLAUDE_TEXT", "transient:metin_giris_kapanis:2")
    view = start_text(app)
    assert [s["status"] for s in sessions(view, "metin_giris_kapanis")] == ["transient", "transient", "done"]
    assert sum(app.clock.slept) >= 330                                   # 1 and 5 minutes (the clock sleeps in steps)
    log = [e["text"] for e in text_job(app)["log"]]
    assert any("geçici hata" in t and "1 dk sonra yeniden denenecek" in t for t in log) and any("5 dk sonra" in t for t in log)
    add_video(app, "v2")
    monkeypatch.setenv("FAKE_CLAUDE_STATE", str(app.env / "durum2.json"))
    monkeypatch.setenv("FAKE_CLAUDE_TEXT", "transient:metin_plan:4")
    paused = start_text(app, video_id="v2")
    assert paused["status"] == "paused" and paused["reason"] == "gecici_hata" and len(sessions(paused, "metin_plan")) == 4


def test_durdur_and_devam(app, monkeypatch):
    add_video(app)
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "slow")
    monkeypatch.setenv("FAKE_CLAUDE_SLEEP", "1.5")
    run = start_text(app, wait=False)
    end = time.monotonic() + 60
    while time.monotonic() < end and not sessions(app.get(f"/api/metin/calismalar/{run['id']}").json(), "metin_plan_elestiri"):
        time.sleep(0.1)
    assert app.post(f"/api/metin/calismalar/{run['id']}/durdur").status_code == 200
    paused = wait_run(app, run["id"])
    assert paused["status"] == "paused" and paused["reason"] == "durduruldu" and paused["status_label"] == "duraklatıldı"
    assert sessions(paused, "metin_plan")[0]["status"] == "done" and sessions(paused, "metin_plan_elestiri")[-1]["status"] == "canceled"
    assert text_job(app)["status"] == "canceled"
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "ok")
    assert app.post(f"/api/metin/calismalar/{run['id']}/devam").status_code == 200
    view = wait_run(app, run["id"])
    assert view["status"] == "awaiting_comparison" and len(sessions(view, "metin_plan")) == 1


def test_a_run_cut_by_the_app_closing_is_yarida_kaldi_and_devam_goes_on(text_env, monkeypatch):
    clock = FakeClock()
    client = open_app(text_env / "data", clock)
    add_video(client)
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "slow")
    monkeypatch.setenv("FAKE_CLAUDE_SLEEP", "1.5")
    run = start_text(client, wait=False)
    end = time.monotonic() + 60
    while time.monotonic() < end and not sessions(client.get(f"/api/metin/calismalar/{run['id']}").json(), "metin_plan_elestiri"):
        time.sleep(0.1)
    client.__exit__(None, None, None)                                    # the app closes while the critic runs
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "ok")
    again = open_app(text_env / "data", FakeClock())
    try:
        view = again.get(f"/api/metin/calismalar/{run['id']}").json()
        assert view["status"] == "interrupted" and view["status_label"] == "yarıda kaldı" and view["eylemler"]["devam"]
        assert again.post(f"/api/metin/calismalar/{run['id']}/devam").status_code == 200
        view = wait_run(again, run["id"])
        assert view["status"] == "awaiting_comparison" and len(sessions(view, "metin_plan")) == 1
        assert [s["status"] for s in sessions(view, "metin_plan_elestiri")] == ["canceled", "done"]
    finally:
        again.__exit__(None, None, None)


def test_plandan_sonra_dur(app):
    add_video(app)
    assert app.put("/api/settings/claude", json={claude_settings.STOP_AFTER_PLAN: True}).status_code == 200
    view = start_text(app)
    assert view["status"] == "paused" and view["reason"] == "plan_hazir" and view["plan"] and not view["surumler"]
    assert text_job(app)["status"] == "done" and "Plan hazır" in text_job(app)["message"]
    assert view["eylemler"]["plani_goster"] and view["eylemler"]["devam"]
    assert app.post(f"/api/metin/calismalar/{view['id']}/devam").status_code == 200
    done = wait_run(app, view["id"])
    assert done["status"] == "awaiting_comparison" and len(sessions(done, "metin_plan")) == 1 and len(done["surumler"]) == 1


def test_other_claude_runs_are_refused_while_a_text_run_works(app, monkeypatch):
    add_video(app)
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "slow")
    monkeypatch.setenv("FAKE_CLAUDE_SLEEP", "1.0")
    run = start_text(app, wait=False)
    refused = app.post("/api/claude/title-runs", json={"bolge": "30A geneli"})
    assert refused.status_code == 409 and refused.json()["detail"] == "Bir video metni çalışması sürüyor; bitmesini bekleyin."
    assert app.post("/api/claude/usage/refresh").json()["detail"] == "Bir video metni çalışması sürüyor; bitmesini bekleyin."
    second = app.post("/api/videos/v1/metin", json={"tonlar": ["belgesel"]})
    assert second.status_code == 409 and second.json()["detail"] == "Bir video metni çalışması sürüyor; bitmesini bekleyin."
    assert app.post(f"/api/metin/calismalar/{run['id']}/durdur").status_code == 200
    wait_run(app, run["id"])


def test_the_pack_is_made_when_missing_and_again_when_older_than_the_data(app):
    add_video(app, with_pack=False)
    options = app.get("/api/videos/v1/metin").json()
    assert options["paket"] == {"var": False, "eski": False, "paket": None, "metin": "Paket önce yeniden üretilecek (bu videonun paketi yok)."}
    view = start_text(app)
    assert view["pack_id"] and any(e["text"] == "Videonun paketi yok; paket üretiliyor." for e in text_job(app)["log"])
    db = app.app.state.db
    later = "2099-01-01T00:00:00+00:00"
    identifier = uuid.uuid4().hex
    with db.connect() as con:
        con.execute("""INSERT INTO jobs (id,kind,title,status,progress,message,created_at,finished_at,result,log,destination_id)
            VALUES (?,'source_collection','deneme','done',100,'',?,?,'{}','[]','30a')""", (identifier, later, later))
        con.execute("""INSERT INTO source_runs (id,job_id,status,started_at,finished_at,connector_name,connector_version,metadata,destination_id)
            VALUES (?,?,'done',?,?,'deneme','deneme/1','{}','30a')""", (identifier, identifier, later, later))
    assert app.get("/api/videos/v1/metin").json()["paket"]["eski"] is True
    again = start_text(app, ("belgesel",))
    assert again["pack_id"] != view["pack_id"]
    assert any(e["text"] == "Videonun paketi verinin son çekiminden eski; paket yeniden üretiliyor." for e in text_job(app)["log"])


def test_version_files_downloads_and_the_choice(app):
    add_video(app)
    view = start_text(app, TWO)
    first, second = view["surumler"]
    voice = app.get(f"/api/metin/surumler/{first['id']}/dosya/seslendirme")
    assert voice.status_code == 200 and "[" not in voice.text and "#" not in voice.text and voice.text.startswith("You came here")
    english = app.get(f"/api/metin/surumler/{first['id']}/dosya/en").text
    assert english.startswith("# Deneme | 30A Florida Vacation\n\n## Giriş") and "[K" not in english
    turkish = app.get(f"/api/metin/surumler/{first['id']}/dosya/tr").text
    assert turkish.startswith("# Deneme | 30A Florida Tatili") and "## Terimler" in turkish
    assert app.get(f"/api/metin/surumler/{first['id']}/dosya/baska").status_code == 404
    detail = app.get(f"/api/metin/surumler/{first['id']}").json()
    sentence = detail["metin"]["parcalar"][0]["paragraflar"][0]["cumleler"][0]
    assert sentence["no"] == 1 and sentence["kanitlar"] and sentence["tr"].startswith("TR: ")
    assert any(w["tur"] == "cevirmen" for w in sentence["uyarilar"])
    assert detail["denetim"]["sayilar"] == {"kirmizi": 1, "sari": 1}
    assert detail["metin"]["surum_bilgisi"]["ton"]["ad"] == "Araştırmacı dost" and detail["metin"]["surum_bilgisi"]["son_okuma"]["uygulanan"]
    compare = app.get("/api/videos/v1/metin/karsilastirma").json()
    assert [c["tone_name"] for c in compare["sutunlar"]] == ["Araştırmacı dost", "Hikâye anlatıcısı"]
    assert compare["satirlar"][:3] == ["giris", "bolum-1", "Geçiş 1 → 2"] and compare["satirlar"][-1] == "kapanis"
    chosen = app.post(f"/api/metin/surumler/{second['id']}/sec", json={})
    assert chosen.status_code == 200 and chosen.json()["secim"]["ton"] == "Hikâye anlatıcısı"
    app.post(f"/api/metin/surumler/{first['id']}/sec", json={"not": "Daha sade."})
    history = app.post(f"/api/metin/surumler/{first['id']}/sec", json={}).json()["secimler"]
    assert [h["version_id"] for h in history] == [first["id"], first["id"], second["id"]]
    assert app.get("/api/videos/v1/metin").json()["secim"]["surum_no"] == 1


def test_a_version_of_a_deleted_tone_keeps_its_tone_name(app):
    add_video(app)
    view = start_text(app, ("vlogger",))
    assert app.delete("/api/tonlar/vlogger").status_code == 200
    version = app.get("/api/videos/v1/metin").json()["surumler"][0]
    assert version["tone_name"] == "Vlogger" and version["ton_var"] is False
    assert app.get("/api/tonlar").json()["arsiv"][0]["kullanim"] == 1
    assert app.get(f"/api/metin/surumler/{view['surumler'][0]['id']}").status_code == 200


def test_v16_to_v17_adds_the_text_tables_and_keeps_rows(tmp_path):
    path = tmp_path / "studio.sqlite3"
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        drop_v17(con)
        con.execute("PRAGMA user_version=16")
        before = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in
                  con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 17
        assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        after = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for (t,) in
                 con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    assert after == {**before, **V17_TABLES}
    assert list((tmp_path / "backups").glob("studio-v16-*.sqlite3"))
