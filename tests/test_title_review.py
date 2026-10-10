"""GÖREV-14 Adım 5 with the fake Claude: the user's own title evaluated by Claude (inputs, schema, the idea that does not fill a video, 1–3
candidates, suffix checks), editing a title before choosing it, and "İngilizcesini Claude yazsın" from an edited Turkish title."""
import json

from studio.ai import title, title_review
from studio.destinations import thirty_a
from tests.test_claude_steps import app, calls, finished, folder, start  # noqa: F401  (app: fixture with the fake Claude)

IDEA = "Rosemary Beach'e köpeğimizle gitsek nasıl olur?"


def review(client, idea=IDEA, bolge="Rosemary Beach", note=None):
    body = {"bolge": bolge, "baslik": idea, **({"not": note} if note else {})}
    response = client.post("/api/claude/review-runs", json=body)
    assert response.status_code == 201, response.json()
    return finished(client, response.json()["id"])


def errors(view, index=None):
    problems = view["general_problems"] if index is None else view["candidates"][index]["sorunlar"]
    return [p["metin"] for p in problems if p["seviye"] == "hata"]


def test_an_evaluation_gets_the_title_inputs_its_own_two_files_and_its_schema(app):
    view = review(app)
    assert view["step"] == "baslik_degerlendirme" and view["status"] == "awaiting_approval" and view["step_title"] == "Başlık değerlendirme"
    files = {p.name for p in folder(app, view).iterdir()}
    assert {"kanal_plani.md", "kanal_arastirmasi.md", "secim.md", "veri_ozeti_30a.md", "veri_ozeti_mahalle.md", "sablonlar.md",
            "onceki_oneriler.md", "kullanici_basligi.md", "baslik_olculeri.md", "talimat.md", "gorev.md", "sema.json",
            "baslik_degerlendirme.json", "baslik_degerlendirme.md", "calisma.json"} <= files
    assert (folder(app, view) / "baslik_olculeri.md").read_bytes() == (thirty_a.CLAUDE_INSTRUCTIONS / "baslik.md").read_bytes()
    user_file = (folder(app, view) / "kullanici_basligi.md").read_text(encoding="utf-8")
    assert f"--- başlık başı ---\n{IDEA}\n--- başlık sonu ---" in user_file
    instructions = (folder(app, view) / "talimat.md").read_text(encoding="utf-8")
    expected = (thirty_a.CLAUDE_INSTRUCTIONS / "baslik_degerlendirme.md").read_text(encoding="utf-8").strip()
    assert instructions.startswith((thirty_a.CLAUDE_INSTRUCTIONS / "ortak.md").read_text(encoding="utf-8").strip()) and expected in instructions
    assert '"adim": {\n  "const": "baslik_degerlendirme"' in instructions.replace(" \n", "\n") or '"const": "baslik_degerlendirme"' in instructions
    task = (folder(app, view) / "gorev.md").read_text(encoding="utf-8")
    assert task.startswith("Adım: baslik_degerlendirme") and "kullanici_basligi.md" in task and "baslik_olculeri.md" in task
    assert "1–3 aday" in task and "birebir çevirisidir" in task
    record = json.loads((folder(app, view) / "calisma.json").read_text(encoding="utf-8"))
    used = {f["path"] for f in record["talimat_surumu"]["files"]}
    assert {"studio/destinations/thirty_a_claude/baslik_degerlendirme.md", "studio/ai/schemas/baslik_degerlendirme.schema.json"} <= used
    assert view["review"]["kullanici_fikri"] == IDEA and view["review"]["doluluk"]["dolar_mi"] is True
    assert len(view["candidates"]) == 2 and not errors(view) and all(not errors(view, i) for i in range(2))
    assert view["output_file"] == "baslik_degerlendirme.json" and view["markdown_file"] == "baslik_degerlendirme.md"
    markdown = (folder(app, view) / "baslik_degerlendirme.md").read_text(encoding="utf-8")
    assert markdown.index("## Kullanıcının fikri") < markdown.index("## Değerlendirme") < markdown.index("## Adaylar") < markdown.index("## 1. ")
    assert calls(app, view)[-1]["model"] == "claude-opus-5-5"
    job = next(j for j in app.get("/api/jobs").json() if j["kind"] == "claude_run")
    assert job["message"] == "Değerlendirme hazır: fikir veriyle doluyor; 2 aday onay bekliyor." and job["title"].startswith("Claude · Başlık değerlendirme")


def test_an_idea_that_does_not_fill_a_video_may_have_no_candidates_but_must_say_what_is_missing(app, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "dolmuyor")
    view = review(app)
    assert view["status"] == "awaiting_approval" and view["candidates"] == [] and not errors(view)
    assert view["review"]["doluluk"] == {"dolar_mi": False, "aciklama": "Bu fikre özgü kural verisi yok.",
                                         "eksik_veri": ["Mahalleye özgü köpek kuralı kaydı yok."]}
    assert "Aday yok (fikir veriyle dolmuyor)." in (folder(app, view) / "baslik_degerlendirme.md").read_text(encoding="utf-8")
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "no_missing")
    assert errors(review(app)) == ["Fikir dolmuyor denmiş ama eksik veri yazılmamış."]


def test_one_to_three_candidates_the_idea_verbatim_and_the_suffix(app, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "too_many")
    assert "En çok 3 aday olmalı; 4 aday var." in errors(review(app))
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "changed_idea")
    assert errors(review(app)) == ["`kullanici_fikri` kullanıcının yazdığıyla aynı değil; aynen yazılmalı."]
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "ok")
    monkeypatch.setenv("FAKE_CLAUDE_REVIEW_COUNT", "0")
    assert errors(review(app)) == ["Fikir veriyle doluyor denmiş ama aday yok; 1–3 aday olmalı."]
    monkeypatch.setenv("FAKE_CLAUDE_REVIEW_COUNT", "1")
    monkeypatch.setenv("FAKE_CLAUDE_NO_SUFFIX", "1")
    view = review(app, idea="A dog friendly week at Rosemary Beach")
    assert 'İngilizce başlık " | 30A Florida Vacation" ekiyle bitmiyor.' in errors(view, 0)
    assert not view["candidates"][0]["secilebilir"]
    assert app.post("/api/claude/review-runs", json={"bolge": "Rosemary Beach", "baslik": "   "}).status_code == 409
    assert app.post("/api/claude/review-runs", json={"bolge": "Mars", "baslik": "x"}).status_code == 409


def test_an_evaluated_candidate_is_chosen_like_a_proposal_and_later_proposals_know_it(app):
    view = review(app)
    video = app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 0}).json()
    assert video["title_en"] == view["candidates"][0]["baslik_en"] and video["user_edited"] is False
    assert video["proposed_title_en"] == video["title_en"] and video["analysis"]["calisma"] == view["id"]
    later = start(app, bolge="Rosemary Beach")
    earlier = (folder(app, later) / "onceki_oneriler.md").read_text(encoding="utf-8")
    assert view["candidates"][0]["baslik_en"].replace("|", "\\|") in earlier and "seçildi" in earlier


def test_a_title_edited_before_choosing_keeps_both_and_passes_the_rules(app):
    view = start(app, bolge="Rosemary Beach")
    candidate = view["candidates"][1]
    bad = app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 1, "baslik_en": "Rosemary Beach with a dog"})
    assert bad.status_code == 409 and '" | 30A Florida Vacation" ekiyle bitmiyor' in bad.json()["detail"]
    long = app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 1, "baslik_en": "x" * 90 + " | 30A Florida Vacation"})
    assert long.status_code == 409 and "100 karakteri aşıyor" in long.json()["detail"]
    edited_en, edited_tr = "Rosemary Beach With a Dog | 30A Florida Vacation", "Rosemary Beach'te Köpekle | 30A Florida Tatili"
    video = app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 1, "baslik_en": edited_en, "baslik_tr": edited_tr}).json()
    assert (video["title_en"], video["title_tr"], video["user_edited"]) == (edited_en, edited_tr, True)
    assert (video["proposed_title_en"], video["proposed_title_tr"]) == (candidate["baslik_en"], candidate["baslik_tr"])
    assert video["analysis"]["duzenleme"]["onerilen_en"] == candidate["baslik_en"]
    listed = app.get("/api/videos").json()[0]
    assert listed["user_edited"] is True and listed["proposed_title_tr"] == candidate["baslik_tr"]
    same = app.post(f"/api/claude/runs/{view['id']}/select", json={"aday": 2, "baslik_en": view["candidates"][2]["baslik_en"]}).json()
    assert same["user_edited"] is False                                                       # unchanged text is not an edit


def test_a_changed_turkish_title_starts_an_evaluation_that_writes_the_english_one(app):
    view = start(app, bolge="Rosemary Beach")
    candidate = view["candidates"][0]
    unchanged = app.post(f"/api/claude/runs/{view['id']}/translate", json={"aday": 0, "baslik_tr": candidate["baslik_tr"]})
    assert unchanged.status_code == 409 and "Türkçe başlık değişmedi" in unchanged.json()["detail"]
    edited_tr = "Rosemary Beach'te köpekle bir hafta | 30A Florida Tatili"
    response = app.post(f"/api/claude/runs/{view['id']}/translate", json={"aday": 0, "baslik_tr": edited_tr})
    assert response.status_code == 201
    run = finished(app, response.json()["id"])
    assert run["step"] == "baslik_degerlendirme" and run["params"]["kullanici_basligi"] == edited_tr
    assert run["params"]["kaynak"] == {"calisma": view["id"], "aday": 0, "baslik_en": candidate["baslik_en"], "baslik_tr": candidate["baslik_tr"]}
    note = run["params"]["not"]
    assert note.startswith("Bu aday düzenlendi") and candidate["neden_onerildi"] in note and candidate["izleyici_sorusu"] in note
    selection = (folder(app, run) / "secim.md").read_text(encoding="utf-8")
    assert "- Not (aşağıda):" in selection and "--- not başı ---\nBu aday düzenlendi" in selection
    assert run["candidates"][0]["baslik_tr"] == edited_tr and not errors(run, 0)
    assert run["params"]["bolge"] == "Rosemary Beach"
    review_text = (folder(app, run) / "kullanici_basligi.md").read_text(encoding="utf-8")
    assert edited_tr in review_text


def test_the_source_candidate_is_not_an_earlier_proposal_of_its_own_rewrite():
    from studio.ai.steps import RunContext
    item = {"baslik_en": "Same | 30A Florida Vacation", "baslik_tr": "Aynı | 30A Florida Tatili", "bolge": "Seaside", "aile": "Deneyim",
            "kanca": {}, "icerik_plani": [], "sablon": None, "yeni_sablon_gerekir": True}
    earlier = [{"baslik_en": "SAME! | 30A Florida Vacation", "calisma": "r1", "aday": 0, "tarih": "2026-10-10", "bolge": "Seaside"}]

    def repeats(params):
        ctx = RunContext(db=None, profile=thirty_a, destination={"id": "30a"}, run_id="x", folder=None, params=params, regions=[],
                         previous=earlier)
        return [p["metin"] for p in title.candidate_problems(ctx, [item]) if "daha önce önerildi" in p["metin"]]

    assert repeats({}) and not repeats({"kaynak": {"calisma": "r1", "aday": 0}}) and repeats({"kaynak": {"calisma": "r1", "aday": 1}})
    assert title_review.MAX_CANDIDATES == 3 and title.TITLE_STEPS["baslik_degerlendirme"] == "baslik_degerlendirme.json"
