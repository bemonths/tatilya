"""Manually verified reference table: validator rules, the committed 30A table, API and the TDT collections file."""
import csv
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.destinations import references as ref
from studio.destinations import thirty_a
from tests.test_beaches import HEADERS
from tests.test_destinations import add_destination

GOOD = {"id": "kural-cam", "konu": "plaj-kurallari", "ifade": "Glass containers are not allowed on the beach.", "deger": "yasak", "birim": "",
        "kapsam": "Walton County", "kaynak_adi": "Ordinance", "kaynak_sahibi": "Walton County", "kaynak_url": "https://example.gov/ordinance.pdf",
        "belge_konumu": "Sec. 22-54(d)", "kisa_alinti": "It shall be unlawful to possess glass.", "belge_tarihi": "2025-11-24",
        "erisim_tarihi": "2026-10-07", "belge_sha256": "a" * 64, "guven": "birincil", "durum": "dogrulandi", "celiski_notu": "",
        "yeniden_kontrol_tarihi": "2027-10-07", "not": ""}


def write(path, rows, columns=ref.COLUMNS):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


# --- Validator -----------------------------------------------------------------------------------------------------

def test_valid_row_has_no_problems():
    assert ref.problems([GOOD]) == []


@pytest.mark.parametrize("changes,message", [
    ({"id": ""}, "'id' boş"),
    ({"ifade": ""}, "'ifade' boş"),
    ({"kaynak_url": ""}, "'kaynak_url' boş"),
    ({"id": "Kural Cam"}, "küçük harf"),
    ({"konu": "hava"}, "konu tanımlı değil"),
    ({"kapsam": "Destin"}, "kapsam tanımlı değil"),
    ({"guven": "kesin"}, "güven değeri"),
    ({"durum": "tamam"}, "durum tanımlı değil"),
    ({"erisim_tarihi": "07.10.2026"}, "erişim tarihi YYYY-AA-GG"),
    ({"erisim_tarihi": "2026-13-01"}, "erişim tarihi YYYY-AA-GG"),
    ({"yeniden_kontrol_tarihi": "2027/10/07"}, "yeniden kontrol tarihi YYYY-AA-GG"),
    ({"yeniden_kontrol_tarihi": "2026-10-07"}, "erişim tarihinden sonra"),
    ({"belge_tarihi": "Nov 2025"}, "belge tarihi"),
    ({"belge_tarihi": "2025-02-30"}, "belge tarihi"),
    ({"kaynak_url": "http://example.gov/x"}, "https ile başlamalı"),
    ({"belge_sha256": ""}, "SHA-256'sı zorunlu"),
    ({"belge_sha256": "ABC"}, "64 küçük onaltılık"),
    ({"durum": "celiskili"}, "çelişki notu zorunlu"),
    ({"kisa_alinti": " ".join(["word"] * 26)}, "25 kelimeyi geçiyor"),
])
def test_validator_rejects(changes, message):
    found = ref.problems([{**GOOD, **changes}])
    assert any(message in problem for problem in found), found


def test_validator_accepts_partial_document_dates_quote_limit_and_unverified_rows():
    assert ref.problems([{**GOOD, "belge_tarihi": "2026"}, {**GOOD, "id": "b", "belge_tarihi": "2026-10"}]) == []
    assert ref.problems([{**GOOD, "kisa_alinti": " ".join(["word"] * 25)}]) == []
    # A row that could not be verified keeps the attempted address and date but needs no document hash.
    assert ref.problems([{**GOOD, "durum": "dogrulanamadi", "belge_sha256": "", "kisa_alinti": "", "deger": ""}]) == []
    assert ref.problems([{**GOOD, "durum": "celiskili", "celiski_notu": "Other page says otherwise."}]) == []


def test_superseded_rows_name_a_verified_replacement():
    old = {**GOOD, "id": "eski", "durum": "yerine_gecildi", "celiski_notu": "Two pages disagreed.", "not": "Karar: yerine geçen: kural-cam."}
    assert ref.problems([GOOD, old]) == []
    assert ref.replaced_by(old) == "kural-cam" and ref.replaced_by(GOOD) is None
    missing_note = ref.problems([GOOD, {**old, "not": "kural-cam daha yeni"}])
    assert any("'yerine geçen: <kimlik>'" in problem for problem in missing_note), missing_note
    unknown = ref.problems([GOOD, {**old, "not": "yerine geçen: yok-boyle"}])
    assert any("(yok-boyle) tabloda doğrulanmış bir satır değil" in problem for problem in unknown), unknown
    # The replacement must itself be verified, and a superseded row still needs its document hash and https address.
    unverified = ref.problems([{**GOOD, "durum": "dogrulanamadi", "belge_sha256": ""}, old])
    assert any("doğrulanmış bir satır değil" in problem for problem in unverified)
    assert any("SHA-256'sı zorunlu" in problem for problem in ref.problems([GOOD, {**old, "belge_sha256": ""}]))
    assert any("https ile başlamalı" in problem for problem in ref.problems([GOOD, {**old, "kaynak_url": "http://x"}]))


def test_snapshot_names_the_replacing_row(tmp_path):
    path = write(tmp_path / "r.csv", [GOOD, {**GOOD, "id": "eski", "durum": "yerine_gecildi", "not": "yerine geçen: kural-cam"}])
    data = ref.snapshot(path, on=date(2026, 10, 8))
    assert [row["replaced_by"] for row in data["rows"]] == [None, "kural-cam"]
    assert data["statuses"]["yerine_gecildi"] == "yerine geçildi" and data["problems"] == []


def test_duplicate_identifier():
    assert any("birden fazla" in p for p in ref.problems([GOOD, dict(GOOD)]))


def test_read_rejects_wrong_columns_and_ragged_rows(tmp_path):
    with pytest.raises(ref.ReferenceError, match="sütunları"):
        ref.read(write(tmp_path / "a.csv", [], columns=ref.COLUMNS[:-1]))
    path = write(tmp_path / "b.csv", [GOOD])
    path.write_text(path.read_text(encoding="utf-8") + "extra,cell\n", encoding="utf-8")
    with pytest.raises(ref.ReferenceError, match="sütun sayısı"):
        ref.read(path)
    with pytest.raises(ref.ReferenceError, match="okunamadı"):
        ref.read(tmp_path / "missing.csv")


def test_snapshot_marks_overdue_rows(tmp_path):
    path = write(tmp_path / "r.csv", [GOOD, {**GOOD, "id": "eski", "yeniden_kontrol_tarihi": "2026-11-01"}])
    data = ref.snapshot(path, on=date(2026, 11, 2))
    assert [row["overdue"] for row in data["rows"]] == [False, True]
    assert data["today"] == "2026-11-02" and data["problems"] == [] and data["file"] == "r.csv"
    assert ref.snapshot(path, on=date(2026, 11, 1))["rows"][1]["overdue"] is False


# --- The committed 30A table ---------------------------------------------------------------------------------------

def test_committed_30a_table_is_valid():
    rows = ref.read(thirty_a.REFERENCE_TABLE)
    assert ref.problems(rows) == []
    assert len({row["id"] for row in rows}) == len(rows)
    assert {row["konu"] for row in rows} == set(ref.TOPICS)
    for row in rows:
        if row["durum"] != "dogrulanamadi":
            assert row["kaynak_url"].startswith("https://") and re.fullmatch(r"[0-9a-f]{64}", row["belge_sha256"]), row["id"]
        assert len(row["kisa_alinti"].split()) <= ref.MAX_QUOTE_WORDS
        if row["durum"] == "celiskili":
            assert row["celiski_notu"]
    # Conflicting facts come in pairs that name each other.
    conflicts = {row["id"]: row["celiski_notu"] for row in rows if row["durum"] == "celiskili"}
    for pair in (("timpoochee-uzunluk-liste", "timpoochee-uzunluk-rehber"),):
        assert pair[1] in conflicts[pair[0]] and pair[0] in conflicts[pair[1]]
    # Resolved conflicts (GOREV-07) stay in the table and name the verified row that replaced them.
    by_id = {row["id"]: row for row in rows}
    for old, new in (("cankurtaran-swfd", "cankurtaran-2026"), ("cankurtaran-vsw", "cankurtaran-2026"),
                     ("ziyaretci-2025-ekonomik-etki", "ziyaretci-2025-ozet")):
        assert by_id[old]["durum"] == "yerine_gecildi" and ref.replaced_by(by_id[old]) == new and by_id[new]["durum"] == "dogrulandi"


def test_tdt_collections_file_is_complete_and_consistent():
    with open(thirty_a.TDT_COLLECTIONS, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == ["ay", "mali_yil", "vergi_bolgesi", "tutar_usd", "yuzde2_payi_usd", "kaynak_sayfa", "kaynak_url", "erisim_tarihi",
                             "belge_sha256", "not"]
    months = [row["ay"] for row in rows]
    assert months == sorted(months) and len(set(months)) == len(months)
    for earlier, later in zip(months, months[1:]):
        year, month = map(int, earlier.split("-"))
        assert later == (f"{year + 1}-01" if month == 12 else f"{year}-{month + 1:02d}")
    for row in rows:
        assert row["vergi_bolgesi"] == "South Walton" and row["kaynak_url"].startswith("https://")
        assert re.fullmatch(r"[0-9a-f]{64}", row["belge_sha256"]) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["erisim_tarihi"])
        assert 0 < float(row["yuzde2_payi_usd"]) <= float(row["tutar_usd"])
        year, month = map(int, row["ay"].split("-"))
        assert row["mali_yil"] == f"FY{year + 1 if month >= 10 else year}"


# --- API -----------------------------------------------------------------------------------------------------------

def test_api_serves_the_table_for_30a_only(tmp_path, monkeypatch):
    monkeypatch.setattr(ref, "today", lambda: date(2026, 10, 8))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        add_destination(client.app.state.db)
        data = client.get("/api/references").json()
        assert data["available"] and data["problems"] == [] and data["today"] == "2026-10-08"
        assert len(data["rows"]) == len(ref.read(thirty_a.REFERENCE_TABLE)) and data["topics"] == ref.TOPICS
        assert not any(row["overdue"] for row in data["rows"])
        other = client.get("/api/references?destination_id=test-coast").json()
        assert other == {"available": False, "reason": "Bu destinasyon için referans tablosu yok.", "rows": []}
        assert client.get("/api/references?destination_id=missing").status_code == 404
        latest = max(date.fromisoformat(row["yeniden_kontrol_tarihi"]) for row in data["rows"])
        monkeypatch.setattr(ref, "today", lambda: latest + timedelta(days=1))     # a day after the latest re-check date
        assert all(row["overdue"] for row in client.get("/api/references").json()["rows"])


def test_api_reports_a_broken_table_instead_of_failing(tmp_path, monkeypatch):
    broken = tmp_path / "broken.csv"
    broken.write_text("id,konu\nx,y\n", encoding="utf-8")
    monkeypatch.setattr(thirty_a, "REFERENCE_TABLE", broken)
    with TestClient(create_app(tmp_path / "data"), headers=HEADERS) as client:
        data = client.get("/api/references").json()
        assert data == {"available": False, "reason": "Referans tablosunun sütunları beklenen biçimde değil.", "rows": []}


def test_traffic_table_has_one_sourced_fact_per_row():
    """GÖREV-11: FDOT 2025 AADT and seasonal-factor rows beside the reference table, with the same source columns; monthly ratios
    are labelled as our calculation."""
    import csv
    with open(thirty_a.TRAFFIC_TABLE, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows and len({r["id"] for r in rows}) == len(rows)
    assert {r["etiket"] for r in rows} <= {"kaynak gerçeği", "bizim hesabımız"}
    for row in rows:
        assert row["kaynak_url"].startswith("https://") and len(row["belge_sha256"]) == 64 and row["erisim_tarihi"]
        assert (row["etiket"] == "bizim hesabımız") == row["tur"].startswith("mevsim faktörü")
    roads = {r["yol"] for r in rows if r["tur"] == "AADT"}
    assert roads == {"CR 30A", "US 98"}
