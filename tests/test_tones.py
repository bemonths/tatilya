"""GÖREV-15 Adım 3: Settings → Tonlar. Adding (empty name, same name, long text), editing and a change on disk, deleting to the archive
(the last tone stays), taking back from the archive, the default tone, versions and going back, file names from Turkish names. Every
test works on a copy of the tone folder (the repository's tones are never touched)."""
import shutil

import pytest
from fastapi.testclient import TestClient

from studio.ai import instructions, tones
from studio.app import create_app
from studio.destinations import thirty_a
from tests.test_beaches import HEADERS

FIVE = {"arastirmaci_dost": "Araştırmacı dost", "belgesel": "Belgesel anlatıcı", "hikaye_anlaticisi": "Hikâye anlatıcısı",
        "pratik_planlayici": "Pratik planlayıcı", "vlogger": "Vlogger"}


@pytest.fixture
def tone_copy(tmp_path, monkeypatch):
    """The tone folder and the warning phrases file copied into the test's folder; the profile points at the copies."""
    folder = tmp_path / "tonlar"
    shutil.copytree(thirty_a.TEXT["tones"], folder)
    phrases = tmp_path / "uyari_ifadeleri.txt"
    shutil.copyfile(thirty_a.TEXT["warning_phrases"], phrases)
    monkeypatch.setitem(thirty_a.TEXT, "tones", folder)
    monkeypatch.setitem(thirty_a.TEXT, "warning_phrases", phrases)
    return folder


@pytest.fixture
def client(tmp_path, tone_copy):
    with TestClient(create_app(tmp_path / "data"), headers=HEADERS) as client:
        client.data = tmp_path / "data"
        client.tones = tone_copy
        yield client


def listing(client):
    return client.get("/api/tonlar").json()


def test_the_five_tones_and_the_default(client):
    found = listing(client)
    assert {t["dosya"]: t["ad"] for t in found["tonlar"]} == FIVE
    assert found["varsayilan"] == "arastirmaci_dost" and [t["dosya"] for t in found["tonlar"] if t["varsayilan"]] == ["arastirmaci_dost"]
    first = next(t for t in found["tonlar"] if t["dosya"] == "belgesel")
    assert first["ilk_satir"].startswith("Anlatıcı, iyi bir gezi belgeselinin sesi.") and first["kullanim"] == 0 and found["arsiv"] == []


@pytest.mark.parametrize("name, stem", [("Hikâye anlatıcısı", "hikaye_anlaticisi"), ("Çok Şık Öğretmen", "cok_sik_ogretmen"),
                                        ("İyi gün!", "iyi_gun"), ("Sakin   ses — 2", "sakin_ses_2"), ("???", "ton")])
def test_file_names_from_turkish_names(name, stem):
    assert tones.slug(name) == stem


def test_adding_a_tone_writes_the_header_and_checks_the_name_and_text(client):
    made = client.post("/api/tonlar", json={"ad": "Sakin rehber", "metin": "Anlatıcı sakin bir rehber."})
    assert made.status_code == 201 and made.json()["dosya"] == "sakin_rehber" and made.json()["not"] is None
    assert (client.tones / "sakin_rehber.md").read_text(encoding="utf-8") == "# Ton: Sakin rehber\n\nAnlatıcı sakin bir rehber.\n"
    assert client.post("/api/tonlar", json={"ad": "  ", "metin": "x"}).json()["detail"] == "Tonun adı boş olamaz."
    assert client.post("/api/tonlar", json={"ad": "sakin REHBER", "metin": "x"}).json()["detail"] == "Bu adla bir ton zaten var; başka bir ad yazın."
    assert client.post("/api/tonlar", json={"ad": "x" * 41, "metin": "x"}).json()["detail"] == "Tonun adı en çok 40 karakter olabilir."
    assert client.post("/api/tonlar", json={"ad": "Boş", "metin": " "}).json()["detail"] == "Tonun metni boş olamaz."
    assert "en çok 6.000 karakter" in client.post("/api/tonlar", json={"ad": "Uzun", "metin": "a" * 6001}).json()["detail"]
    long = client.post("/api/tonlar", json={"ad": "Uzunca", "metin": "a" * 1300})
    assert long.status_code == 201 and long.json()["not"] == tones.LONG_NOTE
    same_file = client.post("/api/tonlar", json={"ad": "Sakin-Rehber!", "metin": "Başka."})
    assert same_file.json()["dosya"] == "sakin_rehber_2"                 # a different name whose file name is taken gets a number


def test_editing_keeps_the_file_name_and_refuses_a_change_on_disk(client):
    opened = client.get("/api/tonlar/vlogger").json()
    saved = client.put("/api/tonlar/vlogger", json={"ad": "Canlı anlatıcı", "metin": "Yeni metin.", "base_sha256": opened["sha256"]})
    assert saved.status_code == 200 and saved.json()["dosya"] == "vlogger" and saved.json()["ad"] == "Canlı anlatıcı"
    assert (client.tones / "vlogger.md").read_text(encoding="utf-8").startswith("# Ton: Canlı anlatıcı\n\nYeni metin.")
    assert len(saved.json()["surumler"]) == 1 and saved.json()["surumler"][0]["ad"] == "Vlogger"
    (client.tones / "vlogger.md").write_text("# Ton: Vlogger\n\nDışarıdan değişti.\n", encoding="utf-8")
    refused = client.put("/api/tonlar/vlogger", json={"ad": "Benim", "metin": "Benim metnim.", "base_sha256": saved.json()["sha256"]})
    assert refused.status_code == 409 and "diskte değişti" in refused.json()["detail"]
    assert (client.tones / "vlogger.md").read_text(encoding="utf-8").endswith("Dışarıdan değişti.\n")
    other = client.put("/api/tonlar/vlogger", json={"ad": "Belgesel anlatıcı", "metin": "x", "base_sha256": client.get("/api/tonlar/vlogger").json()["sha256"]})
    assert other.status_code == 422 and "zaten var" in other.json()["detail"]


def test_versions_and_going_back(client):
    first = client.get("/api/tonlar/belgesel").json()
    original = (client.tones / "belgesel.md").read_bytes()
    saved = client.put("/api/tonlar/belgesel", json={"ad": "Belgesel anlatıcı", "metin": "Kısa belgesel.", "base_sha256": first["sha256"]}).json()
    version = saved["surumler"][0]
    assert client.get(f"/api/tonlar/belgesel/surumler/{version['id']}").json()["metin"].startswith("Anlatıcı, iyi bir gezi belgeselinin sesi.")
    back = client.post(f"/api/tonlar/belgesel/surumler/{version['id']}/geri-don", json={"base_sha256": saved["sha256"]})
    assert back.status_code == 200 and (client.tones / "belgesel.md").read_bytes() == original and len(back.json()["surumler"]) == 2
    assert client.get("/api/tonlar/belgesel/surumler/19990101-000000-000000").status_code == 404


def test_deleting_moves_to_the_archive_and_taking_back_returns_it(client):
    gone = client.delete("/api/tonlar/vlogger")
    assert gone.status_code == 200 and gone.json()["not"] is None and not (client.tones / "vlogger.md").exists()
    archived = listing(client)["arsiv"]
    assert [(a["dosya"], a["ad"]) for a in archived] == [("vlogger", "Vlogger")]
    assert (client.data / "claude" / "ton_arsivi" / f"{archived[0]['id']}.md").is_file()
    (client.tones / "vlogger.md").write_text("# Ton: Yeni vlogger\n\nAynı dosya adı.\n", encoding="utf-8")
    back = client.post(f"/api/ton-arsivi/{archived[0]['id']}/geri-al")
    assert back.status_code == 200 and back.json()["dosya"] == "vlogger_2" and back.json()["ad"] == "Vlogger"
    assert listing(client)["arsiv"] == []


def test_the_default_tone_and_the_last_tone(client):
    assert client.post("/api/tonlar/belgesel/varsayilan").json() == {"varsayilan": "belgesel"}
    assert listing(client)["varsayilan"] == "belgesel"
    note = client.delete("/api/tonlar/belgesel").json()
    assert note["varsayilan"] == "arastirmaci_dost" and "artık varsayılan ton “Araştırmacı dost”" in note["not"]
    for stem in ("arastirmaci_dost", "hikaye_anlaticisi", "pratik_planlayici"):
        assert client.delete(f"/api/tonlar/{stem}").status_code == 200
    last = client.delete("/api/tonlar/vlogger")
    assert last.status_code == 422 and last.json()["detail"] == "Son ton silinemez; en az bir ton kalmalı."
    assert listing(client)["varsayilan"] == "vlogger"


def test_tones_are_not_in_the_instruction_list_but_the_voice_and_the_text_steps_are(client):
    names = [i["name"] for i in client.get("/api/claude/instructions").json()]
    assert names[:3] == ["ortak.md", "baslik.md", "baslik_degerlendirme.md"]
    assert names[3:11] == ["ses_ortak.md", "metin_plan.md", "metin_plan_elestiri.md", "metin_bolum.md", "metin_birlestirme.md",
                           "metin_giris_kapanis.md", "metin_son_okuma.md", "metin_ceviri.md"]
    assert names[-1] == "kanal_arastirmasi.md" and not any(n in names for n in ("arastirmaci_dost.md", "uyari_ifadeleri.txt"))
    titles = {i["name"]: i["title"] for i in client.get("/api/claude/instructions").json()}
    assert titles["ses_ortak.md"] == "Anlatıcının sesi (bütün tonlarda aynı)" and titles["metin_bolum.md"] == "Video metni · bölüm"


def test_the_warning_phrases_are_edited_with_the_instruction_rules(client):
    opened = client.get("/api/claude/instructions/uyari_ifadeleri").json()
    assert opened["kind"] == "denetim" and opened["text"].startswith("amazing\nstunning\n")
    saved = client.put("/api/claude/instructions/uyari_ifadeleri", json={"text": opened["text"] + "gorgeous\n", "base_sha256": opened["sha256"]})
    assert saved.status_code == 200 and saved.json()["text"].endswith("gorgeous\n") and len(saved.json()["versions"]) == 1
    stale = client.put("/api/claude/instructions/uyari_ifadeleri", json={"text": "x\n", "base_sha256": opened["sha256"]})
    assert stale.status_code == 409
    back = client.post(f"/api/claude/instructions/uyari_ifadeleri/versions/{saved.json()['versions'][0]['id']}/restore",
                       json={"base_sha256": saved.json()["sha256"]})
    assert back.status_code == 200 and back.json()["text"] == opened["text"]
    assert instructions.find(thirty_a, "uyari_ifadeleri")["path"] == thirty_a.TEXT["warning_phrases"]
