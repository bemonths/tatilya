"""GÖREV-18: every Claude step is one call without tools; the estimate, the limits and the actual spending; the business-name check and
the title and cover warnings. The fake Claude (tests/fake_claude.py) refuses a step called with tools or more than one turn, reads its
input only from the task text and answers with the JSON as text."""
import json
import re

import pytest

from studio.ai import budget, settings as claude_settings, single, title_marks
from studio.text import audit, businesses, document as D
from tests.test_claude_steps import FAKE, app, calls, finished, folder, start  # noqa: F401
from tests.text_helpers import add_video, open_app, sessions, start_text, text_env, text_job, wait_run  # noqa: F401
from tests.text_helpers import app as text_app  # noqa: F401

TWO = ("arastirmaci_dost", "hikaye_anlaticisi")
NAMED = re.compile(r"\b([a-z0-9_]+\.(?:md|json|csv|txt))\b")


def listed_files(task):
    """The files the task lines list ("- `name` — …")."""
    return re.findall(r"^- `([^`]+\.(?:md|json|csv|txt))` —", task, re.M)


def check_folder(run_folder, *, retry=False):
    """One call's folder: the task text holds exactly the files the step wrote, each with the file's whole text; every section is
    named in the instructions or the task lines; the command had no tools and one turn."""
    record = json.loads((run_folder / "calisma.json").read_text(encoding="utf-8"))
    task = (run_folder / "gorev.md").read_text(encoding="utf-8")
    instructions = (run_folder / "talimat.md").read_text(encoding="utf-8")
    parts = single.parsed_sections(task)
    inputs = [item["dosya"] for item in record["girdiler"]]
    assert list(parts) == inputs, (list(parts), inputs)                       # every input, nothing more
    for name in inputs:
        assert parts[name] == (run_folder / name).read_text(encoding="utf-8-sig").rstrip("\n")   # the same content, not cut
    head = task.split("<<<DOSYA ", 1)[0]
    assert task.startswith(single.PREFACE)
    for name in inputs:
        assert name in instructions or name in head, name                     # named where Claude is told what it gets
    assert set(listed_files(head)) <= set(inputs)
    assert record["duzen"] == "tek_cagri" and record["araclar"] == [] and record["tur_siniri"] == 1 and record["izinler"] == []
    return record, task, parts


# ------------------------------------------------------------------------------------------------------------------- the title steps

def test_title_and_evaluation_calls_hold_their_files_in_the_task_text_and_no_tools(app):
    for view in (start(app), start(app, bolge="Rosemary Beach")):
        record, task, parts = check_folder(folder(app, view))
        assert "veri_ozeti_30a.md" in parts and ("veri_ozeti_mahalle.md" in parts) == (view["params"]["bolge"] == "Rosemary Beach")
        call = calls(app, view)[0]
        assert call["tools"] == "" and call["allowed"] is None and call["max_turns"] == "1" and len(calls(app, view)) == 1
        assert (folder(app, view) / "baslik.json").is_file() and (folder(app, view) / "cevap.txt").is_file()
        assert view["metrics"]["duzen"] == "tek_cagri" and view["metrics"]["tahmin"]["okunan"] > 0
    response = app.post("/api/claude/review-runs", json={"bolge": "Rosemary Beach", "baslik": "Rosemary Beach'e köpeğimizle gitsek nasıl olur?"})
    review = finished(app, response.json()["id"])
    _, _, parts = check_folder(folder(app, review))
    assert "kullanici_basligi.md" in parts and "baslik_olculeri.md" in parts and review["status"] == "awaiting_approval"
    assert parts["onceki_oneriler.md"].count("| 20") >= 8                   # the earlier proposals of the two title runs


def test_the_json_is_taken_out_of_text_around_it_and_out_of_a_fence():
    data = {"a": 1, "b": [1, 2]}
    text = json.dumps(data)
    for answer in (text, f"İşte:\n{text}\nBitti.", f"```json\n{text}\n```", f"Önce bir cümle.\n```\n{text}\n```\nSonra bir cümle."):
        assert single.parse_json(answer) == data
    for bad in ("", "Bitti.", "{", "[1, 2]"):
        with pytest.raises(single.AnswerError):
            single.parse_json(bad)


@pytest.mark.parametrize("scenario", ["prose", "fenced"])
def test_a_json_answer_with_text_or_a_fence_is_used(app, monkeypatch, scenario):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", scenario)
    view = start(app)
    assert view["status"] == "awaiting_approval" and len(view["candidates"]) == 8 and len(calls(app, view)) == 1


def test_an_invalid_answer_is_asked_once_more_in_one_turn_and_then_used(app, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "invalid_once")
    view = start(app)
    made = calls(app, view)
    assert view["status"] == "awaiting_approval" and len(made) == 2 and all(c["max_turns"] == "1" and c["tools"] == "" for c in made)
    assert "DÖNÜŞ SEBEBİ" in made[1]["prompt"] and "okunabilir bir JSON nesnesi değil" in made[1]["prompt"]
    assert single.parsed_sections(made[1]["prompt"])["onceki_cevap.txt"] == "{"
    assert view["metrics"]["cagri"] == 2 and (folder(app, view) / "akis-2.jsonl").is_file() and (folder(app, view) / "gorev-2.md").is_file()


def test_a_cut_answer_is_its_own_case_and_is_not_used(app, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "truncated_once")
    view = start(app)
    job = next(j for j in app.get("/api/jobs").json() if j["kind"] == "claude_run")
    texts = [e["text"] for e in job["log"]]
    assert "Cevap uzunluk sınırında kesildi; kabul edilmedi." in texts and not any("geçersiz" in t.lower() and "kesildi" not in t for t in texts)
    made = calls(app, view)
    assert view["status"] == "awaiting_approval" and len(made) == 2 and "uzunluk sınırında kesildi" in made[1]["prompt"]
    assert "onceki_cevap.txt" not in single.parsed_sections(made[1]["prompt"])          # a cut answer is not given back
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "truncated")
    cut = start(app)
    assert cut["status"] == "error" and "uzunluk sınırında kesildi" in cut["error"] and cut["candidates"] == []


def test_a_task_text_over_the_call_limit_is_not_sent(app):
    assert app.put("/api/settings/claude", json={"claude_call_limit": 20_000}).status_code == 200
    estimate = app.post("/api/claude/title-runs/tahmin", json={"bolge": "30A geneli"}).json()
    assert not estimate["baslatilabilir"] and "tek çağrı sınırı" in estimate["asiyor"][0]
    view = start(app)
    assert view["status"] == "error" and "tek çağrı sınırı" in view["error"] and "kendiliğinden kısaltmaz" in view["error"]
    assert not (folder(app, view) / ".fake_claude_calls.jsonl").exists()     # Claude was not called
    assert (folder(app, view) / "veri_ozeti_30a.md").stat().st_size > 20_000          # and nothing was cut


def test_the_title_estimate_its_lines_and_the_job_limit(app):
    found = app.post("/api/claude/title-runs/tahmin", json={"bolge": "Rosemary Beach"}).json()
    row = found["satirlar"][0]
    assert row["cagri"] == 1 and row["okunan"] > single.OVERHEAD_TOKENS and row["yazilan"] == 60_000 and row["model_adi"] == "Opus 5.5"
    assert found["baslatilabilir"] and found["toplam"]["toplam"] == row["okunan"] + row["yazilan"] and "Konu ve başlık: 1 çağrı" in found["metin"]
    assert {p["parca"] for p in found["parcalar"]} >= {"talimat.md", "veri_ozeti_30a.md", "veri_ozeti_mahalle.md", "onceki_oneriler.md"}
    assert app.get("/api/claude/runs").json() == []                            # an estimate starts nothing
    assert app.put("/api/settings/claude", json={"claude_job_limit": 100_000}).status_code == 200
    over = app.post("/api/claude/title-runs/tahmin", json={"bolge": "Rosemary Beach"}).json()
    assert not over["baslatilabilir"] and "iş başına sınır" in over["asiyor"][-1]


def test_estimate_and_actual_side_by_side_and_the_red_warning(app, monkeypatch):
    view = start(app)
    spend = view["harcama"]
    assert spend["tahmin"]["toplam"] > 0 and spend["gercek"]["cagri"] == 1 and spend["karsilastirma"]["fazla"] is False
    monkeypatch.setenv("FAKE_CLAUDE_TOKENS", "600000,2000")
    over = start(app, aile="Deneyim")
    comparison = over["harcama"]["karsilastirma"]
    assert comparison["fazla"] and comparison["uyari"].startswith("Beklenenden fazla harcandı: tahmin ")
    job = next(j for j in app.get("/api/jobs").json() if j["kind"] == "claude_run")
    assert job["result"]["harcama"]["karsilastirma"]["fazla"] and any("Beklenenden fazla harcandı" in e["text"] for e in job["log"])
    usage = app.get("/api/claude/usage").json()
    assert usage["son_is"]["karsilastirma"]["fazla"] and usage["son_is"]["gercek"]["toplam"] == 602_000
    rows = {r["adim"]: r for r in usage["adimlar"]}
    assert rows["baslik"]["yeni"]["sayi"] == 2 and rows["baslik"]["yeni"]["en_yuksek"] == 602_000
    settings_view = app.get("/api/settings/claude").json()
    assert {r["adim"] for r in settings_view["harcama"]} == {k for k, _ in claude_settings.CLAUDE_STEPS}


def test_model_and_effort_are_unchanged_and_the_sessions_default_is_six(tmp_path):
    values = claude_settings.load(tmp_path)
    assert {k: (values[f"claude_model_{k}"], values[f"claude_effort_{k}"]) for k, _ in claude_settings.CLAUDE_STEPS} == {
        "baslik": ("claude-opus-5-5", "high"), "baslik_degerlendirme": ("claude-opus-5-5", "high"), "metin_plan": ("opus", "high"),
        "metin_plan_elestiri": ("opus", "medium"), "metin_bolum": ("opus", "high"), "metin_birlestirme": ("opus", "medium"),
        "metin_giris_kapanis": ("opus", "high"), "metin_son_okuma": ("opus", "medium"), "metin_ceviri": ("sonnet", "medium")}
    assert values["claude_max_sessions"] == 6 and claude_settings.TEXT_FIELDS["claude_max_sessions"][:2] == (1, 8)
    # a file saved before GÖREV-18 holds the old default 3 because save() wrote every field: the new default holds; any other value stays
    (tmp_path / "ayarlar.json").write_text(json.dumps({"claude": {"claude_max_sessions": 3, "claude_max_turns_baslik": 30}}), encoding="utf-8")
    assert claude_settings.load(tmp_path)["claude_max_sessions"] == 6
    (tmp_path / "ayarlar.json").write_text(json.dumps({"claude": {"claude_max_sessions": 2}}), encoding="utf-8")
    assert claude_settings.load(tmp_path)["claude_max_sessions"] == 2
    saved = claude_settings.save(tmp_path, {"claude_max_sessions": 3})                     # chosen now: kept
    assert saved["claude_max_sessions"] == 3 and claude_settings.load(tmp_path)["claude_max_sessions"] == 3
    assert json.loads((tmp_path / "ayarlar.json").read_text(encoding="utf-8"))["claude"]["ayar_surumu"] == 18


# ------------------------------------------------------------------------------------------------------------------- the video text

def test_two_tones_end_to_end_every_call_one_turn_without_tools_and_the_call_count(text_app):
    add_video(text_app)
    estimate = text_app.post("/api/videos/v1/metin/tahmin", json={"tonlar": list(TWO)}).json()
    lines = {r["baslik"]: r for r in estimate["satirlar"]}
    assert list(lines) == ["Plan", "Araştırmacı dost", "Hikâye anlatıcısı"] and lines["Plan"]["cagri"] == 2
    assert lines["Araştırmacı dost"]["cagri"] == 5 + 3 + 1                    # 5 sections from the title's plan, merge, ends, final, 1 chunk
    assert estimate["metin"].startswith("Plan: 2 çağrı, yaklaşık ") and "Toplam: yaklaşık " in estimate["metin"]
    view = start_text(text_app, TWO)
    assert view["status"] == "awaiting_comparison"
    done = [s for s in view["oturumlar"] if s["status"] == "done"]
    assert len(done) == 2 + 2 * (6 + 3 + 1) == len(view["oturumlar"])        # the fake plan has 6 sections; one chunk per tone
    for session in done:
        run_folder = text_app.data / "claude" / "v1" / session["step"] / session["id"]
        record, task, parts = check_folder(run_folder)
        call = json.loads((run_folder / ".fake_claude_calls.jsonl").read_text(encoding="utf-8").splitlines()[0])
        assert call["tools"] == "" and call["max_turns"] == "1" and call["allowed"] is None
        assert record["tahmin"]["okunan"] > 0
    job = text_job(text_app, settled=True)
    texts = [e["text"] for e in job["log"]]
    assert job["result"]["harcama"]["gercek"]["cagri"] == 22 and job["result"]["harcama"]["tahmin"] == estimate["toplam"]["toplam"]
    assert any(t.startswith("Tahmin: Plan: 2 çağrı") for t in texts) and any(t.startswith("Harcama: tahmin ") for t in texts)
    assert any("istem hazırlandı (yaklaşık " in t for t in texts) and any(": cevap geldi (" in t for t in texts)
    assert not any(t.startswith("Tur ") for t in texts)


def test_the_plan_sections_and_translation_get_their_files_unchanged(text_app, monkeypatch):
    add_video(text_app)
    original = D.chunks
    monkeypatch.setattr(D, "chunks", lambda document, limit=6000: original(document, 300))   # small chunks: several translation calls
    view = start_text(text_app)
    translations = sessions(view, "metin_ceviri")
    assert len(translations) > 1 and all(s["status"] == "done" for s in translations)
    tasks = [(text_app.data / "claude" / "v1" / "metin_ceviri" / s["id"] / "gorev.md").read_text(encoding="utf-8") for s in translations]
    assert all(f"Parça: {i}/{len(tasks)}" in t for i, t in enumerate(tasks, 1))
    plan = sessions(view, "metin_plan")[0]
    _, _, parts = check_folder(text_app.data / "claude" / "v1" / "metin_plan" / plan["id"])
    assert list(parts) == ["baslik_analizi.md", "paket_ozeti.md", "sayilar.csv", "kanal_plani.md"]


def test_the_job_limit_stops_the_chain_and_devam_goes_on(text_app, monkeypatch):
    add_video(text_app)
    assert text_app.put("/api/settings/claude", json={"claude_job_limit": 100_000}).status_code == 200
    refused = text_app.post("/api/videos/v1/metin", json={"tonlar": list(TWO)})
    assert refused.status_code == 409 and "Tahmin token sınırını aşıyor" in refused.json()["detail"]
    assert text_app.put("/api/settings/claude", json={"claude_job_limit": 400_000}).status_code == 200
    one = text_app.post("/api/videos/v1/metin/tahmin", json={"tonlar": ["arastirmaci_dost"]}).json()
    assert one["baslatilabilir"] and one["toplam"]["toplam"] < 400_000
    monkeypatch.setenv("FAKE_CLAUDE_TOKENS", "200000,1000")                     # every call reads 200 thousand: far more than estimated
    view = start_text(text_app)
    assert view["status"] == "paused" and view["reason"] == "token_siniri" and view["reason_text"].startswith("Token sınırına ulaşıldı")
    first = [s for s in view["oturumlar"] if s["status"] == "done"]
    assert [s["step"] for s in first] == ["metin_plan", "metin_plan_elestiri"]   # 402 thousand after two calls: no third call
    job = text_job(text_app, settled=True)
    assert job["status"] == "failed" and job["result"]["harcama"]["gercek"]["toplam"] == 402_000
    monkeypatch.setenv("FAKE_CLAUDE_TOKENS", "1000,500")
    assert text_app.put("/api/settings/claude", json={"claude_job_limit": 1_500_000}).status_code == 200
    resumed = text_app.post(f"/api/metin/calismalar/{view['id']}/devam").json()
    final = wait_run(text_app, resumed["id"])
    assert final["status"] == "awaiting_comparison"
    assert all(s["status"] == "done" for s in final["oturumlar"]) and len([s for s in final["oturumlar"] if s["step"] == "metin_plan"]) == 1


def test_a_text_call_over_the_call_limit_pauses_the_run(text_app, monkeypatch):
    add_video(text_app)
    assert text_app.put("/api/settings/claude", json={"claude_call_limit": 20_000}).status_code == 200
    refused = text_app.post("/api/videos/v1/metin", json={"tonlar": ["arastirmaci_dost"]})
    assert refused.status_code == 409 and "tek çağrı sınırı" in refused.json()["detail"]
    # a call that is bigger than its estimate said is still not sent: the run pauses before it
    from studio.text import engine
    passing = {"satirlar": [], "toplam": {"cagri": 1, "okunan": 1, "yazilan": 1, "toplam": 2}, "sinirlar": {}, "asiyor": [],
               "baslatilabilir": True, "metin": "deneme", "yeniden_deneme": 1}
    monkeypatch.setattr(engine.text_estimate, "estimate", lambda *a, **k: passing)
    view = start_text(text_app)
    assert view["status"] == "paused" and view["reason"] == "cagri_siniri" and "tek çağrı sınırı" in view["reason_text"]
    assert [s["status"] for s in view["oturumlar"]] == ["failed"]


# ------------------------------------------------------------------------------------------------------------------- business names

PLACES = {"rosemary beach", "seaside", "gulf place", "grayton beach", "30a"}


@pytest.fixture
def names(monkeypatch, tmp_path):
    data = [("Rosemary Beach®", "kiralama şirketi"), ("Modica Market", "günlük ihtiyaç"), ("Target", "günlük ihtiyaç"),
            ("Walton County Sheriff Office", "x"), ("The Perfect Pig - Gulf Place", "restoran"), ("Rosemary Beach Realty", "kiralama şirketi"),
            ("WaterColor Inn", "konaklama işletmesi"), ("CVS Pharmacy", "günlük ihtiyaç")]
    monkeypatch.setattr(businesses, "data_names", lambda db, destination_id: list(data))
    monkeypatch.setattr(businesses, "place_names", lambda db, destination_id: set(PLACES))
    path = tmp_path / "isletme_adlari.txt"
    path.write_text("# açıklama\n+ Örnek Kafe\n- CVS Pharmacy\n", encoding="utf-8")
    return path


def test_the_business_list_leaves_out_places_and_public_bodies_and_takes_the_overrides(names):
    table = businesses.names(None, "30a", names)
    shown = set(table.values())
    assert {"Modica Market", "Target", "The Perfect Pig - Gulf Place", "Rosemary Beach Realty", "WaterColor Inn", "Örnek Kafe"} <= shown
    assert "Rosemary Beach" not in shown and not any("Sheriff" in n for n in shown) and "CVS Pharmacy" not in shown
    found = businesses.Matcher(table)
    assert found.find("Rosemary Beach is quiet; Rosemary Beach Realty rents homes there.") == ["Rosemary Beach Realty"]
    assert found.find("A Rosemary Beach® week.") == []                          # the place name itself is never marked
    assert found.find("Coffee at modica market, then the Perfect Pig.") == ["Modica Market", "The Perfect Pig - Gulf Place"]
    assert found.find("Aim for the target.") == [] and found.find("Target sells sunscreen.") == ["Target"]   # one word: as written
    assert found.find("CVS Pharmacy is open.") == []


def test_the_text_check_marks_a_business_name_red_on_its_sentence(names):
    matcher = businesses.Matcher(businesses.names(None, "30a", names))
    document = {"parcalar": [{"kimlik": "bolum-1", "paragraflar": [{"cumleler": [
        {"no": 1, "en": "Seaside has a small market.", "kanitlar": ["K0001"]},
        {"no": 2, "en": "Modica Market sells sandwiches.", "kanitlar": []}]}]}]}
    found = audit.check(document, {"sections": [{"rows": [{"id": "K0001", "blok": "x", "deger": None}]}]}, businesses=matcher)
    red = [f for f in found if f.get("kural") == "isletme"]
    assert len(red) == 1 and red[0]["seviye"] == audit.RED and red[0]["no"] == 2 and red[0]["metin"].startswith("işletme adı: Modica Market")


def test_title_candidates_get_business_and_title_marks(app, monkeypatch, names):
    view = start(app)
    assert all(c["isaretler"] == [] for c in view["candidates"])               # the fake's titles name no business and keep 30A up front
    found = app.post("/api/claude/title-check", json={"baslik_en": "Is Modica Market Worth It? A Long Road Trip Along 30A | 30A Florida Vacation",
                                                      "kapak_fikri": "Bir market; büyük yazı 'IS IT WORTH THE DRIVE?'", "bolge": "30A geneli"}).json()
    codes = [m["kod"] for m in found["isaretler"]]
    assert codes[0] == "isletme" and found["isaretler"][0]["seviye"] == "kirmizi" and "Modica Market" in found["isaretler"][0]["metin"]
    assert {"ilk_40", "kapak_uzun", "kapak_tekrar"} <= set(codes)
    listing = app.get("/api/claude/business-names").json()
    assert listing["sayi"] >= 6 and "Modica Market" in listing["adlar"]


def test_title_and_cover_warnings():
    suffix = {"en": " | 30A Florida Vacation"}
    ok = title_marks.marks("30A in Winter: What You Get | 30A Florida Vacation", "Kumsal; büyük yazı '$214 vs $501'", region="30A geneli",
                           whole_region="30A geneli", suffix=suffix)
    assert ok == []
    late = title_marks.marks("Why People Pay So Much to Stay in Rosemary Beach | 30A Florida Vacation", "", region="Rosemary Beach",
                             whole_region="30A geneli", suffix=suffix)
    assert [m["kod"] for m in late] == ["ilk_40"] and late[0]["metin"].startswith("Telefonda yalnız ilk yaklaşık 40 karakter görünür; konu orada olmalı")
    cover = title_marks.marks("Rosemary Beach: 7 Mistakes to Avoid | 30A Florida Vacation", "Kırmızı çarpı; büyük yazı '7 MISTAKES TO AVOID NOW'",
                              region="Rosemary Beach", whole_region="30A geneli", suffix=suffix)
    assert [m["kod"] for m in cover] == ["kapak_uzun", "kapak_tekrar"] and "mistakes" in cover[1]["metin"]
    caps = title_marks.marks("30A BEACH RULES: FLAGS AND DOGS | 30A Florida Vacation", "", region="30A geneli", whole_region="30A geneli",
                             suffix=suffix)
    assert [m["kod"] for m in caps] == ["buyuk_harf"]
    assert title_marks.cover_text("Harita; büyük yazı ‘IT'S A ROAD, NOT A TOWN’ ve köşede takvim") == "IT'S A ROAD, NOT A TOWN"
    assert title_marks.cover_text("İki etiket: 'JAN ~$8.6K' ve 'JUL ~$15.3K'") is None   # labels are not the cover text: no warning


def test_budget_comparison_and_thousands():
    assert single.thousands(85_400) == "85 bin" and single.thousands(1_200_000) == "1,2 milyon" and single.thousands(1_000_000) == "1 milyon"
    estimate = {"toplam": 100_000}
    assert single.comparison(estimate, {"toplam": 150_000})["fazla"] is False
    assert single.comparison(estimate, {"toplam": 150_001})["fazla"] is True
    assert budget.summary([{"baslik": "A", "cagri": 1, "okunan": 10, "yazilan": 5, "toplam": 15, "en_buyuk_cagri": 15}],
                          {"claude_call_limit": 20_000, "claude_job_limit": 100_000})["baslatilabilir"]
