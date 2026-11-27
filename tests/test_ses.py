"""HEDEF-04 A-7: 7 · Seslendirme with a fake ffprobe and a fake aligner (no audio, no network, no Claude).

- The text is plain English in parts of at most 4,500 characters, never cut inside a sentence; every sentence maps to one part.
- Approving 6 · Yayın paketi (here set directly) opens 7; opening it writes the files under videolar/<video>/7_ses/metin and waits.
- "Sesi yükle" keeps the files as they are and reads their length; numbered parts must match the text parts.
- "Sesi cümlelerle eşleştir" says clearly when the motor is missing; with the fake aligner every sentence gets its times.
"""
import json
import re
from pathlib import Path

from studio import voice, workflow
from tests.test_gorev21 import statuses, step
from tests.test_yayin import approve_check
from tests.text_helpers import app, text_env  # noqa: F401


def test_parts_keep_sentences_whole_and_map_every_sentence():
    paras = [[(i * 3 + k + 1, f"Sentence {i * 3 + k + 1} " + "word " * 40 + "end.") for k in range(3)] for i in range(30)]
    parts = voice.split_parts(paras, limit=1000)
    assert len(parts) > 1 and all(len(voice.render(p).strip()) <= 1000 for p in parts)
    assert [no for p in parts for para in p for no, _ in para] == list(range(1, 91))
    long = [[(n, "x" * 300 + ".") for n in range(1, 8)]]                          # one paragraph longer than the limit
    cut = voice.split_parts(long, limit=1000)
    assert len(cut) > 1 and all(len(voice.render(p).strip()) <= 1000 for p in cut)
    assert voice.render([[(1, "A b."), (2, "C d.")], [(3, "E f.")]]) == "A b. C d.\n\nE f.\n"


def test_sentences_get_times_and_the_unmatched_are_counted():
    sentences = [(1, "Here's a number to start with."), (2, "Seagrove came to about fifty-one hundred dollars."), (3, "Nothing like this was said.")]
    spoken = "here's a number to start with seagrove came to about fifty-one hundred dollars".split()
    words = [{"word": w, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate(spoken)]
    found = voice.match_sentences(sentences, words)
    assert (found["eslesen"], found["eslesmeyen"]) == (2, 1)
    assert found["cumleler"][0]["baslangic"] == 0.0 and found["cumleler"][1]["baslangic"] == 3.0 and found["cumleler"][1]["bitis"] == 6.4
    assert found["cumleler"][2]["baslangic"] is None
    assert voice.audio_check(["a.mp3"], 3) == [] and voice.audio_check(["s_01.wav", "s_02.wav"], 2) == []
    assert any("aynı değil" in p for p in voice.audio_check(["s_01.wav", "s_02.wav"], 3))
    assert any("numaralı değil" in p for p in voice.audio_check(["s.wav", "s_02.wav"], 2))


def test_the_step_writes_its_text_waits_for_audio_takes_it_and_matches_it(app, monkeypatch, tmp_path):
    approve_check(app)
    db = app.app.state.flow.db
    assert statuses(app)["ses"] == "waiting"
    workflow.set_step(db, "v1", "yayin", "approved")                               # 6 approved (its own tests run Claude)
    assert statuses(app)["ses"] == "ready"
    view = step(app, "ses")
    assert view["adim"]["status"] == "awaiting_audio" and view["adim"]["label"] == "ses bekliyor" and not view["adim"]["planned"]
    m = view["ses"]["metin"]
    files = [Path(f["yol"]) for f in m["dosyalar"]]
    assert files[0].name == "seslendirme_01.txt" and files[0].parent.parent.name == "7_ses" and files[0].parent.name == "metin"
    assert all(f.is_file() for f in files) and m["parca_sayisi"] == len(files)
    text = files[0].read_text(encoding="utf-8")
    assert text.strip() and not re.search(r"\[[^\]]*\]|\{|^\s*\d+[.)]\s", text, re.M) and len(text) <= voice.PART_LIMIT + 1
    mapping = json.loads(Path(m["eslesme_dosyasi"]).read_text(encoding="utf-8"))
    assert len(mapping["cumleler"]) == m["cumle_sayisi"] and set(mapping["cumleler"].values()) <= set(range(1, len(files) + 1))
    assert view["surumler"][0]["baslik"] == "Metin hazırlandı"

    monkeypatch.setattr(voice, "duration_of", lambda path, cfg: 12.5)
    assert app.post("/api/videos/v1/ses/eslestir").status_code == 409                # no audio yet
    assert app.post("/api/videos/v1/ses/yukle?ad=ses.ogg&yeni=1", content=b"x").status_code == 409
    up = app.post("/api/videos/v1/ses/yukle?ad=anlatim.mp3&yeni=1", content=b"ID3fake", headers={"Content-Type": "application/octet-stream"})
    assert up.status_code == 200, up.json()
    shown = up.json()
    assert shown["adim"]["status"] == "audio_ready" and shown["adim"]["label"] == "ses yüklendi" and shown["ses"]["ses"]["toplam_s"] == 12.5
    assert (Path(shown["ses"]["ses"]["klasor"]) / "anlatim.mp3").read_bytes() == b"ID3fake"

    assert app.put("/api/settings/seslendirme", json={"kurgu_motoru_path": str(tmp_path / "yok")}).status_code == 200
    missing = app.post("/api/videos/v1/ses/eslestir")
    assert missing.status_code == 409 and "Kurgu Motoru bulunamadı" in missing.json()["detail"]

    spoken = " ".join(f.read_text(encoding="utf-8") for f in files).split()
    monkeypatch.setattr(voice, "motor_command", lambda cfg: ["python", "hizala.py"])
    monkeypatch.setattr(voice, "transcribe_part", lambda command, audio, work, cfg: [
        {"word": w, "start": i * 0.3, "end": i * 0.3 + 0.2} for i, w in enumerate(spoken)])
    done = app.post("/api/videos/v1/ses/eslestir")
    assert done.status_code == 200, done.json()
    result = done.json()
    assert result["adim"]["status"] == "done" and result["ses"]["eslesme"]["eslesmeyen"] == 0
    saved = json.loads(Path(result["ses"]["eslesme"]["dosya"]).read_text(encoding="utf-8"))
    assert all(c["baslangic"] <= c["bitis"] for c in saved["cumleler"]) and len(saved["cumleler"]) == m["cumle_sayisi"]

    two = [app.post(f"/api/videos/v1/ses/yukle?ad=ses_0{n}.wav&yeni={int(n == 1)}", content=b"RIFF").json() for n in (1, 2)]
    expected = "audio_ready" if m["parca_sayisi"] == 2 else "awaiting_audio"
    assert two[-1]["adim"]["status"] == expected and len(two[-1]["ses"]["ses"]["dosyalar"]) == 2
    assert (Path(shown["ses"]["ses"]["klasor"]) / "anlatim.mp3").is_file()          # the earlier set stays
