"""HEDEF-04 A-8: 8 · Kurgu paketi with a fake Kurgu Motoru (no pnpm, no audio, no network, no Claude).

- The package (`kurgu-paket/1`) is built from the approved text: sentence ids c<number>, translations, cited rows as data records with
  their sources, sourced numbers (value + ref), place names, card suggestions; no sound anywhere.
- 8 is ready as soon as 6 · Yayın paketi is approved, whatever 7's stage; without audio the package is silent and has no times.
- With matched audio the package carries the file and the sentence times, and the cards get offsets and durations.
- "Kurguya gönder" copies the package into the motor's folder, runs `paket dogrula` then `paket ice-al` (later `--guncelle`), shows the
  output; a failed check is an error and ice-al is not run.
"""
import json
from pathlib import Path

from studio import kurgu, voice, workflow
from tests.test_gorev21 import statuses, step
from tests.test_yayin import approve_check
from tests.text_helpers import app, text_env  # noqa: F401


def test_the_package_cites_rows_numbers_and_places_and_asks_for_no_sound():
    metin = {"parcalar": [
        {"kimlik": "giris", "tur": "giris", "baslik": "Giriş", "paragraflar": [{"cumleler": [
            {"no": 1, "en": "Here's a number to start with.", "tr": "Önce bir rakam.", "kanitlar": []},
            {"no": 2, "en": "In Seagrove, the middle price came to about $5,144 for the week.", "tr": "Seagrove'da 5.144 dolar.", "kanitlar": ["K0001"]}]}]},
        {"kimlik": "gecis-1", "tur": "gecis", "baslik": "Yeniden kanca", "paragraflar": [{"cumleler": [
            {"no": 3, "en": "WaterColor is next.", "tr": "Sırada WaterColor var.", "kanitlar": []}]}]},
        {"kimlik": "bolum-1", "tur": "bolum", "baslik": "1. Fiyatlar", "paragraflar": [{"cumleler": [
            {"no": 4, "en": "That is the whole story.", "tr": "Hepsi bu.", "kanitlar": []}]}]}]}
    rows = [{"id": "K0001", "blok": "lodging_prices", "deger": 5144, "birim": "USD (7 gece)", "kapsam": "Seagrove",
             "ek_degerler": [{"tur": "alt_ceyrek", "deger": 4012, "birim": "USD (7 gece)"}],
             "kaynak": {"ad": "Kiralama şirketleri", "erisim_tarihi": "2026-11-27", "sha256": "ab" * 32, "url": "https://example.test/x"}}]
    made = kurgu.build(metin, rows, name="30A Deneme", channel="_ornek", regions=["Seagrove", "WaterColor"],
                       chapters=[{"baslik_en": "Intro"}, {"baslik_en": "Prices"}], title_en="Deneme")
    package, script, data, scenes = (made[k] for k in ("package.json", "script.json", "data.json", "scenes.json"))
    assert package["format"] == "kurgu-paket/1" and package["channel"] == "_ornek" and "audio" not in package
    assert [s["id"] for s in script["sentences"]] == ["c1", "c2", "c3", "c4"]
    assert [(s["id"], s["name"]) for s in script["sections"]] == [("giris", "Intro"), ("bolum-1", "Prices")]   # the transition joins giris
    c2 = script["sentences"][1]
    assert c2["translation"] == "Seagrove'da 5.144 dolar." and c2["data"] == ["K0001"] and c2["mentions"]["places"] == ["Seagrove"]
    assert c2["mentions"]["numbers"][0]["value"] == 5144 and c2["mentions"]["numbers"][0]["ref"] == "K0001.deger"
    assert script["sentences"][0]["markers"] == ["hook"] and script["sentences"][2]["markers"] == ["midHook"]
    record = data["records"][0]
    assert record["id"] == "K0001" and record["kind"] == "lodging_prices" and record["fields"]["deger"] == 5144 and record["fields"]["alt_ceyrek"] == 4012
    assert record["sources"] == [package["sources"][0]["id"]] and package["sources"][0]["accessedAt"] == "2026-11-27"
    cards = {s["sentence"]: s for s in scenes["scenes"]}
    assert cards["c1"]["template"] == "baslik-karti" and cards["c3"]["template"] == "alt-bant" and cards["c3"]["fields"]["title"] == "WaterColor"
    assert cards["c2"]["template"] == "rakam-karti" and cards["c2"]["fields"]["value"] == {"$data": "K0001.deger"} and cards["c2"]["fields"]["prefix"] == "$"
    assert all("offset" not in s for s in scenes["scenes"])                                 # no times: the motor's defaults
    shown = json.dumps(made).lower()
    assert not any(word in shown for word in ("sound", "whoosh", "swoosh", "pop.wav", "ses_efekti"))
    timed = kurgu.build(metin, rows, name="x", channel="_ornek", regions=["Seagrove", "WaterColor"],
                        timings={1: (0.4, 2.0), 2: (2.5, 6.0), 3: (6.4, 8.0), 4: (8.5, 10.0)}, audio_total=10.5)["scenes.json"]["scenes"]
    assert timed[0]["offset"] == -0.4 and timed[0]["duration"] == 3.0 and timed[-1]["duration"] == 4.1     # the cards cover the audio
    long = kurgu.build(metin, rows, name="x", channel="_ornek", regions=["Seagrove", "WaterColor"],
                       timings={1: (0.4, 2.0), 2: (2.5, 6.0), 3: (6.4, 8.0), 4: (8.5, 29.0)}, audio_total=30.0)["scenes.json"]["scenes"]
    tail = [(s["id"], s["template"], s["offset"], s["duration"]) for s in long[3:]]
    assert tail == [("s-c4", "baslik-karti", 0.0, 12.0), ("s-c4-2", "baslik-karti", 12.0, 9.5)]
    assert long[3]["fields"]["title"] == "Part 1" and all(s["duration"] <= kurgu.CARD_MAX for s in long)    # no frame without a picture


def fake_motor(tmp_path, monkeypatch, fail_check=False):
    motor = tmp_path / "motor"
    (motor / "projects").mkdir(parents=True)
    (motor / "package.json").write_text("{}", encoding="utf-8")
    calls = []

    def run(cfg, args, timeout=3600):
        calls.append(args)
        assert Path(args[2]).is_dir() and Path(args[2]).is_relative_to(motor / "cache" / "30a-paketler")
        if args[1] == "dogrula":
            return (1, "Hata: script.json → c9: yok") if fail_check else (0, "Paket geçerli. 0 hata, 1 uyarı.")
        (motor / "projects" / "30a-deneme").mkdir(exist_ok=True)
        return 0, "Proje: 30a-deneme → projects/30a-deneme\nSahneler: 3"
    monkeypatch.setattr(kurgu, "run_motor", run)
    monkeypatch.setattr(kurgu, "pnpm_of", lambda cfg: "pnpm")
    return motor, calls


def test_the_step_builds_without_audio_then_with_times_and_sends_to_the_motor(app, monkeypatch, tmp_path):
    approve_check(app)
    db = app.app.state.flow.db
    assert statuses(app)["kurgu"] == "waiting"
    assert app.post("/api/videos/v1/kurgu/kur").status_code == 409
    workflow.set_step(db, "v1", "yayin", "approved")
    assert statuses(app)["kurgu"] == "ready"                                         # 7 has not even written its text
    view = step(app, "kurgu")                                                         # opening it builds the package
    assert view["adim"]["status"] == "ready" and not view["adim"]["planned"] and view["eylemler"]["run"]
    pack = view["kurgu"]["paket"]
    folder = Path(pack["yol"])
    assert folder.parent.parent.name == "8_kurgu" and set(pack["dosyalar"]) == {"package.json", "script.json", "data.json", "scenes.json"}
    assert not pack["ozet"]["ses"] and not pack["ozet"]["zamanlar"] and pack["ozet"]["cumle"] > 0 and pack["ozet"]["kayit"] > 0
    script = json.loads((folder / "script.json").read_text(encoding="utf-8"))
    assert all(s["id"] == f"c{n}" for s, n in zip(script["sentences"], [int(s["id"][1:]) for s in script["sentences"]]))
    assert view["surumler"][0]["baslik"] == "Paket kuruldu"
    statuses_before = statuses(app)
    assert statuses_before["ses"] == "awaiting_audio" or statuses_before["ses"] == "ready"

    step(app, "ses")                                                                  # 7: text, fake audio, fake match
    monkeypatch.setattr(voice, "duration_of", lambda path, cfg: 30.0)
    assert app.post("/api/videos/v1/ses/yukle?ad=anlatim.wav&yeni=1", content=b"RIFFfake").status_code == 200
    files = [Path(f["yol"]) for f in step(app, "ses")["ses"]["metin"]["dosyalar"]]
    spoken = " ".join(f.read_text(encoding="utf-8") for f in files).split()
    monkeypatch.setattr(voice, "motor_command", lambda cfg: ["python", "hizala.py"])
    monkeypatch.setattr(voice, "transcribe_part", lambda command, audio, work, cfg: [
        {"word": w, "start": i * 0.1, "end": i * 0.1 + 0.08} for i, w in enumerate(spoken)])
    assert app.post("/api/videos/v1/ses/eslestir").json()["adim"]["status"] == "done"
    assert statuses(app)["kurgu"] == "ready" and step(app, "kurgu")["kurgu"]["ses_degisti"]

    rebuilt = app.post("/api/videos/v1/kurgu/kur")
    assert rebuilt.status_code == 200, rebuilt.json()
    pack = rebuilt.json()["kurgu"]["paket"]
    assert pack["klasor"] == "002" and pack["ozet"]["ses"] and pack["ozet"]["zamanlar"] and not rebuilt.json()["kurgu"]["ses_degisti"]
    folder = Path(pack["yol"])
    package = json.loads((folder / "package.json").read_text(encoding="utf-8"))
    assert package["audio"]["file"] == "audio/anlatim.wav" and package["audio"]["timings"] == "audio/zamanlar.json"
    assert (folder / "audio" / "anlatim.wav").read_bytes() == b"RIFFfake"
    times = json.loads((folder / "audio" / "zamanlar.json").read_text(encoding="utf-8"))["sentences"]
    assert len(times) == pack["ozet"]["cumle"] and all(t["start"] <= t["end"] for t in times)
    scenes = json.loads((folder / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert scenes and all("duration" in s for s in scenes)
    assert (tmp_path / "eski").exists() is False and (folder.parent / "001").is_dir()        # the earlier package stays

    motor, calls = fake_motor(tmp_path, monkeypatch, fail_check=True)
    assert app.put("/api/settings/kurgu", json={"kurgu_motoru_path": str(motor), "kurgu_kanali": "30a"}).status_code == 200
    assert kurgu.settings(app.app.state.flow.data_dir)["kurgu_motoru_path"] == str(motor)
    assert voice.settings(app.app.state.flow.data_dir)["kurgu_motoru_path"] == str(motor)     # one setting for both steps
    assert app.put("/api/settings/kurgu", json={"kurgu_kanali": "bad id!"}).status_code == 409
    failed = app.post("/api/videos/v1/kurgu/gonder").json()
    assert failed["adim"]["status"] == "error" and [c[1] for c in calls] == ["dogrula"]
    assert not failed["kurgu"]["gonderim"]["basarili"] and "c9: yok" in failed["kurgu"]["gonderim"]["adimlar"][0]["cikti"]

    motor, calls = fake_motor(tmp_path / "ikinci", monkeypatch)
    app.put("/api/settings/kurgu", json={"kurgu_motoru_path": str(motor)})
    sent = app.post("/api/videos/v1/kurgu/gonder")
    assert sent.status_code == 200, sent.json()
    shown = sent.json()
    assert shown["adim"]["status"] == "done" and shown["kurgu"]["gonderim"]["proje"] == "30a-deneme"
    assert [c[:2] for c in calls] == [["paket", "dogrula"], ["paket", "ice-al"]] and "--guncelle" not in calls[1]
    inbox = Path(calls[0][2])
    assert json.loads((inbox / "package.json").read_text(encoding="utf-8"))["format"] == "kurgu-paket/1"
    again = app.post("/api/videos/v1/kurgu/gonder").json()
    assert again["adim"]["status"] == "done" and calls[-1][-2:] == ["--guncelle", "projects/30a-deneme"]
    assert any(v["baslik"] == "Kurguya gönderildi" for v in again["surumler"])


def test_the_motor_settings_say_clearly_what_is_missing(tmp_path):
    try:
        kurgu.motor_dir({"kurgu_motoru_path": str(tmp_path / "yok")})
    except Exception as exc:                                  # Conflict
        assert "Kurgu Motoru bulunamadı" in str(exc) and "Ayarlar → Kurgu Motoru" in str(exc)
    else:
        raise AssertionError("no error")
    assert kurgu.settings_view(tmp_path)["varsayilan"]["kurgu_kanali"] == "_ornek"


def test_the_aligner_uses_the_motors_own_model_caches(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "tools.json").write_text(json.dumps({"cacheRoots": {"hf": "E:/m/hf", "torch": "E:/m/torch", "uv": "x"}}), encoding="utf-8")
    assert voice.motor_cache_env(tmp_path) == {"HF_HOME": str(Path("E:/m/hf")), "TORCH_HOME": str(Path("E:/m/torch"))}
    assert voice.motor_cache_env(tmp_path / "yok") == {}
