"""GÖREV-14 Adım 6: the video pack built from the chosen candidate's content plan, the window dates in the summary's column headers and the
note on restaurants tied to several neighborhoods."""
import json

import pytest
from fastapi.testclient import TestClient

from studio import evidence
from studio.app import create_app
from studio.destinations import thirty_a
from studio.evidence import blocks as B, plan, summary as S, video as V
from studio.evidence.pack import markdown
from tests.test_beaches import HEADERS


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        yield client


def general_pack(db):
    record, _ = evidence.fresh_pack(db, "30a", thirty_a, "ilk-video", {})
    path, _ = evidence.stored_file(db, record["id"], "json")
    return record, json.loads(path.read_text(encoding="utf-8"))


def groups(pack):
    """Consecutive rows of one block in one section, as the plan pack takes them."""
    found = []
    for section in pack["sections"]:
        for row in section["rows"]:
            if found and found[-1][0]["blok"] == row["blok"] and found[-1][0]["bolum"] == row["bolum"]:
                found[-1].append(row)
            else:
                found.append([row])
    return found


def video_of(record, cited_sections, hook):
    return {"id": "v1", "title_en": "Deneme | 30A Florida Vacation", "title_tr": "Deneme | 30A Florida Tatili", "family": "Deneyim",
            "region_name": "30A geneli", "region_id": None, "template_key": None, "user_edited": False,
            "analysis": {"paketler": {"veri_ozeti_30a.md": record["id"]}, "izleyici_sorusu": "Ne zaman gitmeli?", "neden_onerildi": "Deneme.",
                         "kanca": {"metin": "Kanca.", "kanitlar": hook}, "eksik_veri": ["Bir eksik."], "kapak_fikri": "Kapak.",
                         "icerik_plani": [{"bolum": f"Bölüm {n}", "ne_anlatir": f"Soru {n}?", "kanitlar": items}
                                          for n, items in enumerate(cited_sections, 1)]}}


def test_sections_follow_the_plan_with_the_cited_rows_and_their_whole_blocks_once(client):
    db = client.app.state.db
    record, source = general_pack(db)
    blocks = [g for g in groups(source) if len(g) > 2]
    first, second = blocks[0], blocks[1]
    cite = lambda row: V.cited(row, dosya="veri_ozeti_30a.md", pack_id=record["id"])
    changed = {**cite(second[1]), "deger": "999999"} if second[1]["durum"] == "var" else cite(second[1])
    gone = {**cite(first[0]), "blok": "references", "referans": None, "ifade": "Kaynakta olmayan bir satır"}
    video = video_of(record, [[cite(first[1])], [changed, cite(first[0]), gone], []], [cite(first[1])])
    pack = plan.build(db, "30a", thirty_a, video)
    assert [s["title"] for s in pack["sections"]] == ["Bölüm 1", "Bölüm 2", "Bölüm 3"]
    assert [s["question"] for s in pack["sections"]] == ["Soru 1?", "Soru 2?", "Soru 3?"]
    one, two, three = pack["sections"]
    assert len(one["rows"]) == len(first) and [r["kaynak_ozet"]["kimlik"] for r in one["rows"]] == [r["id"] for r in first]
    assert [r["id"] for r in one["rows"]] == [f"K{n:04d}" for n in range(1, len(first) + 1)]          # numbered again in order
    assert one["plan"][0]["yeni_kimlik"] == one["rows"][1]["id"] and one["rows"][1]["plan_satiri"] and not one["rows"][2].get("plan_satiri")
    assert one["rows"][0]["plan_satiri"]                                                             # cited by the 2nd section
    assert len(two["rows"]) == len(second)                                                           # only the new block is written
    statuses = [e["yeni_durum"] for e in two["plan"]]
    assert statuses[1] == V.SAME and two["plan"][1]["bolum_no"] == 1 and two["plan"][2]["yeni_durum"] == V.ABSENT
    if second[1]["durum"] == "var":
        assert statuses[0] == V.CHANGED and two["plan"][0]["yeni_deger_metni"] != "999999"
    assert two["onceki_bloklar"] == [{"bolum_no": 1, "bolum": "Bölüm 1", "blok": first[0]["blok"], "dosya": "veri_ozeti_30a.md",
                                      "kimlikler": [r["id"] for r in one["rows"]]}]
    assert three["rows"] == [] and three["plan"] == []
    assert pack["counts"]["evidence"] == len(first) + len(second) and pack["template"]["key"] == "video-plani"
    assert pack["video"]["kanca"]["kanitlar"][0]["yeni_kimlik"] == one["rows"][1]["id"] and pack["video"]["yeni_sablon_gerekir"] is True
    assert set(pack["header"]) >= {"bilinen_bosluklar", "yayindan_once_kontrol", "kaynaklar", "kurulus"}
    full, short = markdown(pack), S.render({**pack, "id": "p1"})
    for text in (full, short):
        assert text.index("## Video") < text.index("## 1. Bölüm 1") < text.index("## 2. Bölüm 2") < text.index("## 3. Bölüm 3")
        assert "Planın gösterdiği satırlar" in text and "bu pakette yok" in text
        assert f"Blok {first[0]['blok']} (veri_ozeti_30a.md) 1. bölümde (Bölüm 1) tam yazıldı" in text
        assert "yeni şablon gerekir” yazıyordu" in text and "Ne zaman gitmeli?" in text and "(planda bu bölüm için kanıt yok)" in text
    assert f"- **{one['rows'][1]['id']}** · **plan** ·" in full and f"Kaynak özet: veri_ozeti_30a.md {first[1]['id']}" in full


def test_the_videos_pack_button_makes_the_plan_pack_with_its_summary_and_checklist(client, tmp_path):
    db = client.app.state.db
    record, source = general_pack(db)
    rows = [r for g in groups(source) for r in g]
    cite = lambda row: V.cited(row, dosya="veri_ozeti_30a.md", pack_id=record["id"])
    video = video_of(record, [[cite(rows[0])], [cite(rows[-1])], [cite(rows[len(rows) // 2])], [cite(rows[1])], [cite(rows[2])]], [cite(rows[0])])
    with db.connect() as con:
        con.execute("""INSERT INTO claude_runs (id,destination_id,step,scope_id,status,params,folder,created_at)
            VALUES ('r1','30a','baslik','r1','approved','{}','claude/r1/baslik/r1','2026-10-10T10:00:00+00:00')""")
        con.execute("""INSERT INTO videos (id,destination_id,region_name,title_en,title_tr,family,analysis,params,status,created_at,run_id,candidate,
            proposed_title_en,proposed_title_tr,user_edited) VALUES ('v1','30a','30A geneli',?,?,'Deneyim',?,'{}','baslik_secildi',
            '2026-10-10T10:01:00+00:00','r1',0,?,?,0)""", (video["title_en"], video["title_tr"], json.dumps(video["analysis"], ensure_ascii=False),
                                                         video["title_en"], video["title_tr"]))
    made = client.post("/api/videos/v1/evidence-pack")
    assert made.status_code == 201 and made.json()["template_key"] == "video-plani" and made.json()["video_id"] == "v1"
    pack_id = made.json()["id"]
    assert made.json()["section_count"] == 5
    summary = client.get(f"/api/evidence-packs/{pack_id}/yazar-ozeti").text
    assert summary.startswith("# Deneme | 30A Florida Vacation — yazar özeti") and "## 5. Bölüm 5" in summary
    csv = client.get(f"/api/evidence-packs/{pack_id}/sayilar").text
    assert csv.startswith("kanit,tur,deger,birim,etiket")
    assert client.get("/api/videos").json()[0]["status"] == "paket_hazir"


def test_window_columns_carry_their_dates_and_two_windows_of_a_month_stay_apart():
    assert B.window_column({"month": "2027-03", "checkin": "2027-03-13", "checkout": "2027-03-20"}) == "Mar 2027 (13–20)"
    assert B.window_column({"month": "2027-05", "checkin": "2027-05-29", "checkout": "2027-06-05"}) == "May 2027 (29 May–5 Haz)"
    assert B.window_column({"month": "2027-07"}) == "Tem 2027"
    one = B.window_column({"month": "2027-03", "checkin": "2027-03-06", "checkout": "2027-03-13"})
    two = B.window_column({"month": "2027-03", "checkin": "2027-03-13", "checkout": "2027-03-20"})
    assert one != two


def test_the_restaurant_note_says_why_neighborhoods_add_up_to_more():
    summary = {"regions": [{"region_id": "a", "restaurant_count": 3}, {"region_id": "b", "restaurant_count": 2}, {"region_id": "c", "restaurant_count": 0}],
               "restaurants": [{"regions": ["a"]}, {"regions": ["a", "b"]}, {"regions": ["a"]}, {"regions": ["b"]}]}
    note = B.overlap_note(summary, ["a", "b", "c"])
    assert note == ("Mahalle satırlarının toplamı (5) tekil restoran sayısından (4) büyüktür: 1 restoran dizinde birden çok mahalleye bağlı "
                    "olduğu için bağlı olduğu her mahallede sayılır.")
    assert "3 restoranından 1 tanesi dizinde başka bir mahalleye de bağlı" in B.overlap_note(summary, ["a"])
    assert B.overlap_note({"regions": [{"region_id": "a", "restaurant_count": 1}, {"region_id": "b", "restaurant_count": 1}],
                           "restaurants": [{"regions": ["a"]}, {"regions": ["b"]}]}, ["a", "b"]) is None
