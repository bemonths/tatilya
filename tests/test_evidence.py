"""GÖREV-11 evidence pack: templates on the destination side, parameters, reusable data blocks, missing data as "veri yok" rows,
usage notes, the number checklist, Markdown and JSON with the same content, and dated storage with SHA-256.

No network: run-based blocks see an empty database (every one must then say "veri yok"); file-based blocks (reference table,
traffic, tourist tax) read the committed 30A profile files; the lodging price rules are checked on a synthetic summary.
"""
import hashlib
import json
import re
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from studio import evidence
from studio.app import create_app
from studio.database import Database
from studio.destinations import PROFILES, thirty_a
from studio.evidence import blocks as B
from studio.evidence import pack as P
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
    assert refs["hukuk-gecis-alani-turizm"]["not"].startswith("Çelişki:")
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
               "label": "etiket", "source_note": "kaynak notu", "bedroom_note": "oda notu"}
    monkeypatch.setattr(B, "agency_summary", lambda _: (run, summary))
    rows = {r["kapsam"]: r for r in B.lodging_prices(data, {"block": "lodging_prices"})}
    assert rows["Seaside"]["deger"] == 7223 and rows["Seaside"]["orneklem"] == 42 and "$5,000–$9,100" in rows["Seaside"]["ifade"]
    assert rows["Gulf Place"]["not"].startswith("Küçük örnek (12 ilan)")
    assert "kendi envanterinden" in rows["Alys Beach"]["ifade"] and rows["Alys Beach"]["deger"] == 8319
    assert rows["Dune Allen"]["durum"] == evidence.MISSING                               # no cell at all: still a row
    assert {r["etiket"] for r in rows.values() if r["durum"] == "var"} == {"bizim hesabımız"}


# --- Number checklist, Markdown = JSON, storage ---------------------------------------------------------------------------------

def test_checklist_holds_every_number_of_every_row_and_the_markdown_lists_it(db):
    pack = evidence.generate(db, "30a", thirty_a, "ilk-video", now=NOW)
    listed = {(item["kanit"], item["deger"]) for item in pack["checklist"]}
    for section in pack["sections"]:
        for row in section["rows"]:
            if row["durum"] != "var":
                continue
            for token in re.findall(r"\d{4}-\d{2}-\d{2}|\d+(?:,\d{3})*(?:\.\d+)?", " ".join(str(v) for v in (row["ifade"], row["deger"], row["deger_ek"]) if v)):
                assert (row["id"], token) in listed or (row["id"], P.value_text(row["deger"])) in listed, (row["id"], token)
    assert pack["counts"]["numbers"] == len(pack["checklist"]) > 0
    markdown = evidence.markdown(pack)
    table = markdown.split("## Sayı kontrol listesi", 1)[1]
    assert table.count("\n| ") - 1 == len(pack["checklist"])                         # header line + one line per number


def test_markdown_and_json_carry_the_same_rows(db):
    pack = evidence.generate(db, "30a", thirty_a, "mahalle-rehberi", {"mahalle": "seaside"}, now=NOW)
    record = evidence.store(db, pack)
    folder = db.path.parent
    markdown = (folder / record["markdown_file"]).read_text(encoding="utf-8")
    stored = json.loads((folder / record["json_file"]).read_text(encoding="utf-8"))
    assert stored["id"] == record["id"] and {k: v for k, v in stored.items() if k != "id"} == json.loads(json.dumps(pack, ensure_ascii=False))
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
        assert client.get(f"/api/evidence-packs/{pack['id']}/pdf").status_code == 404
        assert client.get("/api/evidence-packs/yok/json").status_code == 404
