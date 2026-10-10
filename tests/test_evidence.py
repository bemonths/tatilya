"""GÖREV-11 evidence pack: templates on the destination side, parameters, reusable data blocks, missing data as "veri yok" rows,
usage notes, the number checklist, Markdown and JSON with the same content, and dated storage with SHA-256.

No network: run-based blocks see an empty database (every one must then say "veri yok"); file-based blocks (reference table,
traffic, tourist tax) read the committed 30A profile files; the lodging price rules are checked on a synthetic summary.
"""
import csv
import hashlib
import io
import json
import re
from datetime import date, datetime, timezone
from pathlib import PurePosixPath

import pytest
from fastapi.testclient import TestClient

from studio import evidence
from studio.app import create_app
from studio.database import Database
from studio.destinations import PROFILES, thirty_a
from studio.evidence import blocks as B
from studio.evidence import pack as P
from studio.evidence import summary as S
from studio.evidence import templates as T
from tests.test_beaches import HEADERS

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "studio.sqlite3")
    database.initialize()
    return database


def template_file(tmp_path, **changes):
    data = {"key": "deneme", "version": "1", "title": "Deneme", "question": "Soru?",
            "parameters": [{"key": "mahalle", "label": "Mahalle", "kind": "region"}],
            "sections": [{"key": "bir", "title": "Bir", "question": "Ne?", "blocks": [{"block": "references", "match": "{mahalle_adi}"}]}]}
    data.update(changes)
    path = tmp_path / "deneme.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


# --- Templates and parameters ---------------------------------------------------------------------------------------------------

def test_profile_templates_are_read_and_name_only_known_blocks():
    templates = evidence.destination_templates(thirty_a)
    assert set(templates) == {"ilk-video", "mahalle-rehberi"}
    first = templates["ilk-video"]
    assert first["parameters"] == [] and len(first["sections"]) == 11 and set(first["dimensions"]) == {"bolge", "karar", "donem", "gezgin_tipi"}
    guide = templates["mahalle-rehberi"]
    assert [p["kind"] for p in guide["parameters"]] == ["region"]
    used = {spec["block"] for t in templates.values() for s in t["sections"] for spec in s["blocks"]}
    assert used == set(B.BLOCKS)                                   # every reusable block is used by one of the two templates


@pytest.mark.parametrize("changes, message", [
    ({"question": ""}, "'question' eksik"),
    ({"sections": [{"key": "a", "title": "A", "question": "?", "blocks": [{"block": "yok"}]}]}, "Bilinmeyen veri bloğu"),
    ({"sections": [{"key": "a", "title": "A", "question": "?", "blocks": [{"block": "references", "match": "{bolge}"}]}]}, "tanımlanmamış parametre"),
    ({"sections": [{"key": "a", "title": "A", "question": "?", "blocks": [{"block": "traffic"}]},
                   {"key": "a", "title": "B", "question": "?", "blocks": [{"block": "traffic"}]}]}, "iki kez"),
    ({"parameters": [{"key": "mahalle", "kind": "metin"}]}, "parametresi geçersiz"),
    ({"dimensions": {"renk": "mavi"}}, "boyutları"),
])
def test_invalid_templates_are_refused_with_a_reason(tmp_path, changes, message):
    with pytest.raises(T.TemplateError, match=message):
        T.read(template_file(tmp_path, **changes), set(B.BLOCKS))


def test_parameters_must_be_regions_and_fill_ids_and_names(tmp_path):
    template = T.read(template_file(tmp_path), set(B.BLOCKS))
    regions = [{"id": "rosemary-beach", "name": "Rosemary Beach"}, {"id": "seaside", "name": "Seaside"}]
    with pytest.raises(T.TemplateError, match="mahallelerinden biri"):
        T.resolve(template, {}, regions)
    with pytest.raises(T.TemplateError):
        T.resolve(template, {"mahalle": "miramar-beach"}, regions)
    resolved = T.resolve(template, {"mahalle": "rosemary-beach"}, regions)
    assert resolved == {"mahalle": {"id": "rosemary-beach", "name": "Rosemary Beach"}}
    assert T.fill({"block": "x", "region": "{mahalle}", "match": "{mahalle_adi}"}, resolved) == {"block": "x", "region": "rosemary-beach",
                                                                                                    "match": "Rosemary Beach"}


def test_generate_refuses_an_unknown_template_or_a_missing_parameter(db):
    with pytest.raises(evidence.PackError, match="şablon yok"):
        evidence.generate(db, "30a", thirty_a, "yok", now=NOW)
    with pytest.raises(evidence.PackError, match="mahallelerinden biri"):
        evidence.generate(db, "30a", thirty_a, "mahalle-rehberi", {}, now=NOW)


# --- Missing data, usage notes, labels ------------------------------------------------------------------------------------------

def test_without_runs_every_run_based_block_says_veri_yok_and_nothing_is_dropped(db):
    pack = evidence.generate(db, "30a", thirty_a, "ilk-video", now=NOW)
    template = evidence.destination_templates(thirty_a)["ilk-video"]
    assert [s["key"] for s in pack["sections"]] == [s["key"] for s in template["sections"]]
    for section, spec_section in zip(pack["sections"], template["sections"]):
        assert section["rows"], section["key"]
        assert {spec["block"] for spec in spec_section["blocks"]} == {row["blok"] for row in section["rows"]}   # each block left a row
    by_block = {}
    for section in pack["sections"]:
        for row in section["rows"]:
            by_block.setdefault(row["blok"], []).append(row)
    for block in ("neighborhoods", "beach_accesses", "beach_features", "climate_months", "sea_water", "storms", "lodging_inventory",
                  "lodging_prices", "lodging_bedrooms", "restaurants", "daily_needs"):
        assert all(row["durum"] == evidence.MISSING and row["not"] for row in by_block[block]), block
    assert pack["counts"]["missing"] == sum(len(by_block[b]) for b in by_block if all(r["durum"] == evidence.MISSING for r in by_block[b]))
    assert all(row["durum"] == "var" for row in by_block["traffic"] + by_block["tdt_season"])
    markdown = evidence.markdown(pack)
    assert markdown.count("**veri yok**") == pack["counts"]["missing"]


def test_rows_carry_their_usage_note_label_and_source(db):
    pack = evidence.generate(db, "30a", thirty_a, "ilk-video", now=NOW)
    rows = [r for s in pack["sections"] for r in s["rows"] if r["durum"] == "var"]
    assert rows
    for row in rows:
        assert row["kullanim_notu"] and row["etiket"] in evidence.LABELS and row["kaynak"]["url"].startswith("https://"), row["id"]
        assert re.search(r"\(M\d+\)$", row["kullanim_notu"]), row["kullanim_notu"]            # every note names its M document
    traffic = [r for r in rows if r["blok"] == "traffic"]
    assert {r["kullanim_notu"] for r in traffic} == {B.USAGE["traffic"]}
    assert {r["etiket"] for r in traffic if r["birim"] == "oran"} == {"bizim hesabımız"}
    assert {r["etiket"] for r in rows if r["blok"] == "tdt_season"} == {"bizim hesabımız"}
    refs = {r["kaynak"]["referans"]: r for r in rows if r["blok"] == "references"}
    assert refs["hukuk-iddia-ozel-plaj-kalmadi"]["kullanim_notu"] == B.USAGE["references"]["dogrulanamadi"]
    assert refs["hukuk-gecis-alani-turizm"]["kullanim_notu"] == B.USAGE["references"]["celiskili"]
    assert refs["hukuk-gecis-alani-turizm"]["celiski_notu"] and "Çelişki:" not in refs["hukuk-gecis-alani-turizm"]["not"]
    school = refs["okul-atlanta-gwinnett"]                                                # GÖREV-12: the manager's video rule
    assert "'en büyük okul bölgesi' denmez" in school["kullanim_notu"] and "Video dili" not in school["not"]
    assert refs["hukuk-video-ozet"]["etiket"] == "türetilmiş" and refs["havalimani-ecp"]["ifade"].startswith("Northwest Florida Beaches")
    assert "ziyaretci-2025-ekonomik-etki" not in refs                                      # superseded rows stay out of the pack
    assert all(r["ifade_en"] and not r["ifade"].startswith("(Türkçe ifade yok)") for r in refs.values())


def test_every_reference_row_has_a_turkish_statement():
    import csv
    from studio.destinations import references as ref
    ids = [r["id"] for r in ref.read(thirty_a.REFERENCE_TABLE)]
    with open(thirty_a.REFERENCE_TRANSLATIONS, encoding="utf-8-sig", newline="") as handle:
        translations = {r["id"]: r["ifade_tr"] for r in csv.DictReader(handle)}
    assert set(ids) == set(translations) and all(translations.values())


def test_reference_ids_a_template_names_but_the_table_lacks_become_veri_yok(db):
    data = B.BlockData(db, "30a", thirty_a, date(2026, 10, 10))
    rows = B.references(data, {"block": "references", "ids": ["bayrak-kirmizi", "olmayan-satir"]})
    assert [r["durum"] for r in rows] == [evidence.MISSING, "var"]
    assert rows[0]["ifade"] == "Referans satırı: olmayan-satir"
    assert B.references(data, {"block": "references", "match": "Atlantis"})[0]["durum"] == evidence.MISSING


def summary_cell(region, window, priced, median, q1, q3, own=None, bedrooms=None):
    return {"region_id": region, "window_key": window, "priced_count": priced, "total_median": median, "total_q1": q1, "total_q3": q3,
            "own": own or {"priced_count": 0, "total_median": None, "total_q1": None, "total_q3": None},
            "bedrooms": bedrooms or {"1-2": {"count": 0, "median": None}}}


def test_lodging_prices_note_small_samples_and_single_company_inventories(db, monkeypatch):
    data = B.BlockData(db, "30a", thirty_a, date(2026, 10, 10))
    run = {"id": "r", "metadata": {"source_name": "Kiralama"}, "source_url": "https://example.com/", "fetched_at": "2026-10-09T00:00:00",
           "finished_at": None, "raw_sha256": "a" * 64, "connector_name": "agency-lodging-rates"}
    summary = {"snapshot": {"queried_on": "2026-10-09"}, "windows": [{"window_key": "w7", "label": "Temmuz 2027 · 10–17 Temmuz", "month": "2027-07"}],
               "cells": [summary_cell("seaside", "w7", 42, 7222.69, 5000.0, 9100.5),
                         summary_cell("gulf-place", "w7", 12, 4459.35, 3000.0, 5000.0),
                         summary_cell("alys-beach", "w7", 0, None, None, None,
                                      own={"priced_count": 29, "total_median": 8319.36, "total_q1": 7324.8, "total_q3": 10460.8})],
               "label": "etiket", "source_note": "kaynak notu", "bedroom_note": "oda notu", "total_counts": {"priced": 50, "taxed": 47, "fees": 47}}
    monkeypatch.setattr(B, "agency_summary", lambda _: (run, summary))
    rows = {r["kapsam"]: r for r in B.lodging_prices(data, {"block": "lodging_prices"})}
    assert rows["Seaside"]["deger"] == 7223 and rows["Seaside"]["orneklem"] == 42 and "$5,000–$9,100" in rows["Seaside"]["ifade"]
    assert [(e["tur"], e["deger"]) for e in rows["Seaside"]["ek_degerler"]] == [("alt_ceyrek", 5000), ("ust_ceyrek", 9100)]
    assert rows["Gulf Place"]["kucuk_ornek"] and not rows["Seaside"]["kucuk_ornek"]          # threshold: fewer than 20 priced listings
    assert "kendi envanterinden" in rows["Alys Beach"]["ifade"] and rows["Alys Beach"]["deger"] == 8319
    assert rows["Alys Beach"]["tablo"]["satir"] == "Alys Beach (kendi envanteri)"            # labelled apart in the tables
    assert rows["Dune Allen"]["durum"] == evidence.MISSING                               # no cell at all: still a row
    assert {r["etiket"] for r in rows.values() if r["durum"] == "var"} == {"bizim hesabımız"}
    # one note for the whole block, written once and plainly, with the share computed from the run (47 of 50 = 94%)
    assert len({r["not"] for r in rows.values() if r["durum"] == "var"}) == 1
    assert ("Fiyatların %94'ünde sitenin gösterdiği toplam vergileri ve ücretleri içeriyor; kalanında sitenin toplamı kalemlerle "
            "doğrulanamadı.") in rows["Seaside"]["not"]


@pytest.mark.parametrize("value, ending", [(94, "'ünde"), (90, "'ında"), (100, "'ünde"), (85, "'inde"), (76, "'sında"), (50, "'sinde")])
def test_percent_endings_follow_turkish_reading(value, ending):
    assert B.percent_locative(value) == ending


# --- Number checklist, Markdown = JSON, storage ---------------------------------------------------------------------------------

def test_checklist_comes_only_from_structured_fields(db):
    pack = evidence.generate(db, "30a", thirty_a, "ilk-video", now=NOW)
    assert pack["counts"]["numbers"] == len(pack["checklist"]) > 0
    assert all(set(item) == set(P.CHECKLIST_COLUMNS) for item in pack["checklist"])
    expected = []
    for section in pack["sections"]:
        for row in section["rows"]:
            if row["durum"] != "var":
                continue
            if isinstance(row["deger"], (int, float)) or isinstance(row["deger"], str) and re.search(r"\d", row["deger"]):
                expected.append((row["id"], "ana", row["deger"]))
            expected += [(row["id"], e["tur"], e["deger"]) for e in row.get("ek_degerler") or []]
            if row.get("orneklem") is not None and not any(e["tur"] == "orneklem" for e in row.get("ek_degerler") or []):
                expected.append((row["id"], "orneklem", row["orneklem"]))
    assert [(i["kanit"], i["tur"], i["deger"]) for i in pack["checklist"]] == expected
    assert {i["tur"] for i in pack["checklist"]} <= {"ana", *B.EXTRA_TYPES}
    # names, addresses, road and station numbers and periods in the statement text never become entries
    traffic = [r for s in pack["sections"] for r in s["rows"] if r["blok"] == "traffic" and r.get("birim") == "araç/gün (iki yön)"]
    assert traffic and all("30A" in r["ifade"] or "98" in r["ifade"] for r in traffic)
    for row in traffic:
        assert [(i["tur"], i["deger"]) for i in pack["checklist"] if i["kanit"] == row["id"]] == [("ana", row["deger"])]
    assert not any(i["deger"] in (30, "30") for i in pack["checklist"] if i["kanit"] in {r["id"] for r in traffic})
    # the Markdown only names the separate file; the list itself is not repeated there
    markdown = evidence.markdown(pack)
    tail = markdown.split("## Sayı kontrol listesi", 1)[1]
    assert f"({len(pack['checklist'])} satır;" in tail and "<paket>-sayilar.csv" in tail and "\n| " not in tail


def test_reference_rows_contribute_only_their_table_value(db):
    data = B.BlockData(db, "30a", thirty_a, date(2026, 10, 10))
    road = B.references(data, {"block": "references", "ids": ["genel-30a-ilce-yolu"]})[0]
    assert "60660100" in road["ifade_en"] and "30A" in road["ifade"]                    # road id and road name sit in the statement
    assert [(e["tur"], e["deger"]) for e in P.numbers_of({**road, "id": "K0001"})] == [("ana", "18.561")]
    law = B.references(data, {"block": "references", "ids": ["hukuk-walton-2016-karar"]})[0]
    assert [(e["tur"], e["deger"]) for e in P.numbers_of({**law, "id": "K0002"})] == [("ana", law["deger"])]


def test_markdown_and_json_carry_the_same_rows(db):
    pack = evidence.generate(db, "30a", thirty_a, "mahalle-rehberi", {"mahalle": "seaside"}, now=NOW)
    record = evidence.store(db, pack)
    folder = db.path.parent
    markdown = (folder / record["markdown_file"]).read_text(encoding="utf-8")
    stored = json.loads((folder / record["json_file"]).read_text(encoding="utf-8"))
    assert stored["id"] == record["id"] and set(stored["dosyalar"]) == {"sayilar", "yazar_ozeti"}
    assert {k: v for k, v in stored.items() if k not in ("id", "dosyalar")} == json.loads(json.dumps(pack, ensure_ascii=False))
    for section in stored["sections"]:
        assert f"## {section['title']}" in markdown and section["question"] in markdown
        for row in section["rows"]:
            assert f"**{row['id']}** · {row['ifade']}" in markdown
            for text in (row.get("kullanim_notu"), row.get("not"), row.get("ifade_en"), (row.get("kaynak") or {}).get("url")):
                if text:
                    assert text in markdown, (row["id"], text[:40])
            if row["durum"] == "var" and isinstance(row["deger"], (int, float)):
                assert f"**{P.value_text(row['deger'])}" in markdown
    assert stored["parameters"] == {"mahalle": {"id": "seaside", "name": "Seaside"}} and "Seaside (seaside)" in markdown
    for gap in stored["header"]["bilinen_bosluklar"]:
        assert gap in markdown
    assert P.NO_ADVICE in markdown


def test_store_writes_dated_files_with_sha256_and_a_record(db):
    pack = evidence.generate(db, "30a", thirty_a, "ilk-video", now=NOW)
    record = evidence.store(db, pack)
    folder = db.path.parent
    for kind in ("markdown", "json"):
        path = folder / record[f"{kind}_file"]
        assert path.parent.name == "evidence" and path.name.startswith("20261010-120000-ilk-video-")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record[f"{kind}_sha256"]
    assert record["evidence_count"] == pack["counts"]["evidence"] and record["number_count"] == pack["counts"]["numbers"]
    assert record["missing_count"] == pack["counts"]["missing"] and record["params"] == {}
    assert [r["id"] for r in evidence.stored(db, "30a")] == [record["id"]]
    (folder / record["json_file"]).write_text("{}", encoding="utf-8")                  # a changed file is refused
    with pytest.raises(evidence.PackError, match="SHA-256"):
        evidence.stored_file(db, record["id"], "json")


def test_api_lists_templates_generates_stores_and_serves_packs(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        templates = client.get("/api/evidence-templates").json()["templates"]
        guide = next(t for t in templates if t["key"] == "mahalle-rehberi")
        assert len(guide["parameters"][0]["choices"]) == 13 and guide["sections"][0]["question"]
        refused = client.post("/api/evidence-packs", json={"template_key": "mahalle-rehberi", "params": {}})
        assert refused.status_code == 422 and "mahallelerinden" in refused.json()["detail"]
        assert client.post("/api/evidence-packs", json={"template_key": "x", "params": {}}, headers={"X-Studio-Request": "0"}).status_code == 403
        made = client.post("/api/evidence-packs", json={"template_key": "mahalle-rehberi", "params": {"mahalle": "rosemary-beach"}})
        assert made.status_code == 201
        pack = made.json()
        assert pack["params"] == {"mahalle": "rosemary-beach"} and pack["section_count"] == 8
        assert [p["id"] for p in client.get("/api/evidence-packs").json()] == [pack["id"]]
        markdown = client.get(f"/api/evidence-packs/{pack['id']}/markdown")
        assert markdown.status_code == 200 and markdown.text.startswith("# Mahalle rehberi")
        assert hashlib.sha256(markdown.content).hexdigest() == pack["markdown_sha256"]
        assert client.get(f"/api/evidence-packs/{pack['id']}/json").json()["template"]["key"] == "mahalle-rehberi"
        assert pack["ekler"] == {"sayilar": True, "yazar_ozeti": True}
        summary = client.get(f"/api/evidence-packs/{pack['id']}/yazar-ozeti")
        assert summary.status_code == 200 and summary.text.startswith("# Mahalle rehberi") and pack["id"] in summary.text
        numbers = client.get(f"/api/evidence-packs/{pack['id']}/sayilar")
        assert numbers.status_code == 200 and numbers.text.splitlines()[0] == ",".join(P.CHECKLIST_COLUMNS)
        assert len(numbers.text.splitlines()) - 1 == pack["number_count"]
        assert client.get(f"/api/evidence-packs/{pack['id']}/pdf").status_code == 404
        assert client.get("/api/evidence-packs/yok/json").status_code == 404


# --- Writer's summary and number list (GÖREV-12) --------------------------------------------------------------------------------

PRICE_RUN = {"id": "fiyat-cekimi", "metadata": {"source_name": "Kiralama şirketleri · Konaklama fiyatları"}, "source_url": "https://example.com/",
             "fetched_at": "2026-10-09T00:00:00", "finished_at": None, "raw_sha256": "a" * 64, "connector_name": "agency-lodging-rates"}


@pytest.fixture
def priced(db, monkeypatch):
    """The ilk-video pack on an empty database plus synthetic lodging prices (a large, a small and a single-company cell)."""
    windows = [{"window_key": "w1", "label": "Ocak 2027 · 9–16 Ocak", "month": "2027-01"},
               {"window_key": "w7", "label": "Temmuz 2027 · 10–17 Temmuz", "month": "2027-07"}]
    cells = [summary_cell("seaside", "w1", 42, 4100.4, 3000.0, 5200.0, bedrooms={"1-2": {"count": 25, "median": 3020.0}, "3": {"count": 0, "median": None}}),
             summary_cell("seaside", "w7", 41, 7222.69, 5000.0, 9100.5),
             summary_cell("gulf-place", "w1", 12, 2100.0, 1650.0, 2400.0),
             summary_cell("gulf-place", "w7", 14, 4459.35, 3000.0, 5000.0),
             summary_cell("alys-beach", "w1", 0, None, None, None, own={"priced_count": 29, "total_median": 8319.36, "total_q1": 7324.8, "total_q3": 10460.8})]
    summary = {"snapshot": {"queried_on": "2026-10-09"}, "windows": windows, "cells": cells, "label": "etiket", "source_note": "kaynak notu",
               "bedroom_note": "Oda sayısı ilandan.", "total_counts": {"priced": 50, "taxed": 47, "fees": 47}}
    monkeypatch.setattr(B, "agency_summary", lambda _: (PRICE_RUN, summary))
    return evidence.generate(db, "30a", thirty_a, "ilk-video", now=NOW)


def ids_in(text):
    """Every K identifier the text shows, ranges ('K0003–K0006') expanded."""
    found = set()
    for start, end in re.findall(r"K(\d{4})(?:–K(\d{4}))?", text):
        found.update(f"K{n:04d}" for n in range(int(start), int(end or start) + 1))
    return found


def rows_of(pack):
    return [r for s in pack["sections"] for r in s["rows"]]


def last_cell(line):
    return line.rstrip(" |").rsplit("|", 1)[-1]


def lines_of(text, identifier):
    """Summary lines that carry a row: its own line item, or table rows whose K range (last cell) holds it."""
    return [line for line in text.splitlines()
            if line.startswith(f"- {identifier} ") or line.startswith("| ") and identifier in ids_in(last_cell(line))]


def test_summary_shows_every_k_id_and_drops_no_row(priced):
    text = S.render({**priced, "id": "f" * 32})
    body, sources = text.split("## Kaynak listesi", 1)
    for row in rows_of(priced):
        assert lines_of(body, row["id"]), row["id"]                                     # each row has its own line or a table row
    assert {r["id"] for r in rows_of(priced) if r["durum"] == "var"} <= ids_in(sources)  # and every present row names its source
    assert S.SENTENCE in text and "f" * 32 in text


def test_summary_numbers_are_the_pack_values(priced):
    text = S.render(priced)
    by_id = {r["id"]: r for r in rows_of(priced)}
    token = re.compile(r"\d[\d,]*(?:\.\d+)?")
    checked = 0
    for row in rows_of(priced):
        if row["durum"] != "var":
            continue
        lines = lines_of(text, row["id"])
        if row["deger"] is not None:
            shown = P.value_text(row["deger"])
            assert any(shown in line for line in lines), (row["id"], shown)
        for line in lines:
            members = [by_id[i] for i in (ids_in(last_cell(line)) if line.startswith("|") else {row["id"]}) if i in by_id]
            allowed = set()
            for member in members:
                values = [member["deger"], member.get("orneklem"), *[e["deger"] for e in member.get("ek_degerler") or []]]
                allowed |= {P.value_text(v) for v in values if v is not None}
                allowed |= {t for v in values if isinstance(v, str) for t in token.findall(v)}
                hint = member.get("tablo") or {}
                words = [member.get("birim") or "", member["ifade"], *(hint.get("hucreler") or {}).values(), hint.get("satir") or ""]
                allowed |= set(token.findall(" ".join(str(w) for w in words)))
            shown_part = line.rstrip(" |").rsplit("|", 1)[0] if line.startswith("|") else line.split(" — ", 1)[1] if " — " in line else ""
            for number in token.findall(shown_part):
                assert number in allowed, (row["id"], number, line)
                checked += 1
    assert checked > 100


def test_summary_marks_missing_cells_small_samples_and_the_single_company_label(priced):
    text = S.render(priced)
    part = text.split("**7 gecelik toplam fiyat ortancası**", 1)[1].split("**7 gecelik toplam fiyat ortancası — çeyrekler", 1)[0]
    rows = {line.split(" | ")[0][2:]: line for line in part.splitlines() if line.startswith("| ") and not line.startswith("| Mahalle")}
    assert rows["Seaside"].startswith("| Seaside | $4,100 (42) | $7,223 (41) |")             # no star at 20 or more
    assert rows["Gulf Place"].startswith("| Gulf Place | $2,100 (12)* | $4,459 (14)* |")     # fewer than 20 priced listings: '*'
    assert rows["Alys Beach (kendi envanteri)"].startswith("| Alys Beach (kendi envanteri) | $8,319 (29) | — |")  # a missing cell is '—'
    assert rows["Dune Allen"].startswith("| Dune Allen | — | — |")
    assert "$1,650–$2,400*" in text and "$3,000–$5,200" in text                             # quartiles in their own table
    assert '"—" veri yok' in text and '"*" küçük örnek' in text
    assert "Fiyatların %94'ünde sitenin gösterdiği toplam vergileri ve ücretleri içeriyor" in text
    assert text.count("Fiyatların %94'ünde") == 1                                         # the lodging note once, not per row


def test_usage_note_appears_once_per_block_and_verbatim(priced):
    text = S.render(priced)
    expected = {}
    for section in priced["sections"]:
        for group in S.groups_of(section["rows"]):
            for note in {r["kullanim_notu"] for r in group if r.get("kullanim_notu")}:
                expected[note] = expected.get(note, 0) + 1
    assert expected
    for note, count in expected.items():
        assert text.count(note) == count, note[:60]


def test_summary_carries_no_address_sha_or_quote_outside_the_source_list(priced):
    text = S.render(priced)
    body = text.split("## Kaynak listesi", 1)[0]
    assert "http" not in body and not re.search(r"[0-9a-f]{64}", text)
    for row in rows_of(priced):
        if row.get("alinti") and row["alinti"] not in row["ifade"]:                      # a quoted name may sit in the statement
            assert row["alinti"] not in text
        if row.get("ifade_en"):
            assert row["ifade_en"] not in text


def test_shared_note_sentences_go_to_the_block_head_once():
    note_a = "Sayfa tarihsiz. GÖREV-08: sayfa uygulama içi tarayıcıda normal açıldı ve ham kopyası alındı. Çelişki sürüyor."
    note_b = "GÖREV-08: sayfa uygulama içi tarayıcıda normal açıldı ve ham kopyası alındı. Çelişki sürüyor. Kamp ücreti ayrıca yazılmış ve alınmadı."
    base = {"blok": "references", "durum": "var", "etiket": "kaynak gerçeği", "deger": None, "birim": None, "kullanim_notu": "Not (M9)",
            "kaynak": {"ad": "Kaynak", "url": "https://example.com/"}}
    lines = S.block_lines([{**base, "id": "K0001", "ifade": "Bir.", "not": note_a}, {**base, "id": "K0002", "ifade": "İki.", "not": note_b},
                           {**base, "id": "K0003", "ifade": "Üç.", "not": None}])
    text = "\n".join(lines)
    assert text.count("ham kopyası alındı. Çelişki sürüyor.") == 1                      # a short sentence stays with the one before it
    assert "Not (K0001–K0002): GÖREV-08: sayfa uygulama içi tarayıcıda normal açıldı ve ham kopyası alındı. Çelişki sürüyor." in text
    assert "  - Not: Sayfa tarihsiz." in text and "  - Not: Kamp ücreti ayrıca yazılmış ve alınmadı." in text


def test_text_values_keep_their_unit_and_numbers_get_the_dollar_sign():
    assert S.unit_value(3091, "USD (7 gece)", False) == "$3,091"
    assert S.unit_value("500", "USD (üst sınır)") == "$500 (üst sınır)"
    assert S.unit_value("5 / 15", "USD (saat / gün)") == "5 / 15 USD (saat / gün)"
    assert S.unit_value("48.3", "%") == "%48.3"
    assert S.note_text("Bkz. (https://example.com/a?b=1) ve work/gorev-11/kaynaklar/x.html") == "Bkz. (adres tam pakette) ve yerel kayıt"


def stem_of(record):
    return PurePosixPath(record["markdown_file"]).stem


def test_number_list_csv_matches_the_json_and_both_files_are_linked_to_the_pack(priced, db):
    record = evidence.store(db, priced)
    folder = db.path.parent
    stored = json.loads((folder / record["json_file"]).read_text(encoding="utf-8"))
    for key, suffix in P.EXTRA_FILES.items():
        attached = stored["dosyalar"][key]
        path = folder / attached["dosya"]
        assert path.name == stem_of(record) + suffix and hashlib.sha256(path.read_bytes()).hexdigest() == attached["sha256"]
        assert evidence.stored_file(db, record["id"], key)[0] == path.resolve()
    rows = list(csv.DictReader(io.StringIO((folder / stored["dosyalar"]["sayilar"]["dosya"]).read_text(encoding="utf-8"))))
    assert rows == [{k: "" if item[k] is None else str(item[k]) for k in P.CHECKLIST_COLUMNS} for item in stored["checklist"]]
    summary = (folder / stored["dosyalar"]["yazar_ozeti"]["dosya"]).read_text(encoding="utf-8")
    assert summary == S.render({k: v for k, v in stored.items() if k != "dosyalar"})   # written from the same pack object
    assert record["id"] in summary and [p["ekler"] for p in evidence.stored(db, "30a")] == [{"sayilar": True, "yazar_ozeti": True}]
    assert f"`{stem_of(record)}-sayilar.csv` ({len(stored['checklist'])} satır;" in (folder / record["markdown_file"]).read_text(encoding="utf-8")
    (folder / stored["dosyalar"]["sayilar"]["dosya"]).write_text("degisti", encoding="utf-8")   # a changed attached file is refused
    with pytest.raises(evidence.PackError, match="SHA-256"):
        evidence.stored_file(db, record["id"], "sayilar")


def test_packs_from_before_the_writer_summary_have_no_attached_files(db):
    pack = evidence.generate(db, "30a", thirty_a, "mahalle-rehberi", {"mahalle": "seaside"}, now=NOW)
    record = evidence.store(db, pack)
    folder = db.path.parent
    old = json.loads((folder / record["json_file"]).read_text(encoding="utf-8"))
    old.pop("dosyalar")
    data = (json.dumps(old, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    (folder / record["json_file"]).write_bytes(data)
    with db.connect() as con:
        con.execute("UPDATE evidence_packs SET json_sha256=? WHERE id=?", (hashlib.sha256(data).hexdigest(), record["id"]))
    for suffix in P.EXTRA_FILES.values():
        (folder / "evidence" / f"{stem_of(record)}{suffix}").unlink()
    assert evidence.stored(db, "30a")[0]["ekler"] == {"sayilar": False, "yazar_ozeti": False}
    with pytest.raises(evidence.PackError, match="GÖREV-12"):
        evidence.stored_file(db, record["id"], "yazar_ozeti")


def test_volatile_topics_and_contradictions_open_the_pack_and_the_summary(priced):
    recheck = priced["header"]["yayindan_once_kontrol"]
    assert priced["template"]["volatile_topics"] == ["plaj-hukuku"]
    by_id = {r["id"]: r for r in rows_of(priced)}
    expected = [r["id"] for r in rows_of(priced) if r["durum"] == "var" and (r["kaynak"].get("konu") == "plaj-hukuku"
                                                                              or r["kaynak"].get("durum") == "celiskili")]
    assert [i["kanit"] for i in recheck] == expected and expected
    assert all(i["yeniden_kontrol_tarihi"] == by_id[i["kanit"]]["kaynak"]["yeniden_kontrol_tarihi"] for i in recheck)
    for text in (evidence.markdown(priced), S.render(priced)):
        part = text.split("## Yayından önce kontrol edilecek satırlar", 1)[1].split("\n## ", 1)[0]
        assert [line.split(" · ")[0][2:] for line in part.splitlines() if line.startswith("- K")] == expected
