"""Manually verified reference facts supplied by destination profiles: one fact per row, with its source.

The table is filled by hand, reviewed and committed; the app only reads and validates it. The documents behind the
rows are kept outside the repository and identified by SHA-256. Generic: the file location comes from the profile.
"""
import csv
import re
from datetime import date, datetime, timezone

COLUMNS = ("id", "konu", "ifade", "deger", "birim", "kapsam", "kaynak_adi", "kaynak_sahibi", "kaynak_url", "belge_konumu",
           "kisa_alinti", "belge_tarihi", "erisim_tarihi", "belge_sha256", "guven", "durum", "celiski_notu",
           "yeniden_kontrol_tarihi", "not")
REQUIRED = ("id", "konu", "ifade", "kapsam", "kaynak_adi", "kaynak_sahibi", "kaynak_url", "erisim_tarihi", "guven", "durum",
            "yeniden_kontrol_tarihi")
TOPICS = {"plaj-kurallari": "Plaj kuralları", "guvenlik": "Güvenlik", "plaj-erisimi": "Plaj erişimi", "ulasim": "Ulaşım",
          "parklar": "Parklar", "kasirga-sezonu": "Kasırga sezonu", "sezon-maliyet": "Sezon ve maliyet", "genel": "Genel"}
STATUSES = {"dogrulandi": "doğrulandı", "celiskili": "çelişkili", "dogrulanamadi": "doğrulanamadı", "yerine_gecildi": "yerine geçildi"}
# A superseded row stays in the table for the record; its note names the verified row that replaces it.
REPLACED_BY = re.compile(r"yerine geçen: ([a-z0-9]+(?:-[a-z0-9]+)*)")
CONFIDENCE = {"birincil": "birincil", "ikincil": "ikincil"}
SCOPES = ("30A", "South Walton", "Walton County", "Florida", "Atlantik havzası")
MAX_QUOTE_WORDS = 25
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SHA_PATTERN = re.compile(r"[0-9a-f]{64}")
PARTIAL_DATE = re.compile(r"\d{4}(-\d{2}(-\d{2})?)?")


class ReferenceError(ValueError):
    """User-facing reason why a reference table cannot be shown."""


def today():
    return datetime.now(timezone.utc).date()


def read(path):
    """Rows in file order as dicts of strings; only the file structure is checked here (see problems())."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != COLUMNS:
                raise ReferenceError("Referans tablosunun sütunları beklenen biçimde değil.")
            rows = []
            for line, row in enumerate(reader, 2):
                if None in row or None in row.values():
                    raise ReferenceError(f"Referans tablosunun {line}. satırında sütun sayısı hatalı.")
                rows.append({key: value.strip() for key, value in row.items()})
            return rows
    except OSError as exc:
        raise ReferenceError("Referans tablosu okunamadı.") from exc


def valid_day(text):
    try:
        return date.fromisoformat(text) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text or "") else None
    except ValueError:
        return None


def valid_partial(text):
    if not PARTIAL_DATE.fullmatch(text):
        return False
    parts = [int(part) for part in text.split("-")]
    try:
        date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
    except ValueError:
        return False
    return True


def problems(rows):
    """Every rule a row breaks, as readable sentences; an empty list means the table is valid."""
    found, seen = [], set()
    for number, row in enumerate(rows, 2):
        label = f"{number}. satır ({row.get('id') or 'kimliksiz'})"
        for column in REQUIRED:
            if not row.get(column):
                found.append(f"{label}: '{column}' boş.")
        identifier = row.get("id", "")
        if identifier and not ID_PATTERN.fullmatch(identifier):
            found.append(f"{label}: kimlik yalnız küçük harf, rakam ve tire içerebilir.")
        if identifier in seen:
            found.append(f"{label}: kimlik birden fazla satırda kullanılmış.")
        seen.add(identifier)
        if row.get("konu") and row["konu"] not in TOPICS:
            found.append(f"{label}: konu tanımlı değil ({row['konu']}).")
        if row.get("kapsam") and row["kapsam"] not in SCOPES:
            found.append(f"{label}: kapsam tanımlı değil ({row['kapsam']}).")
        if row.get("guven") and row["guven"] not in CONFIDENCE:
            found.append(f"{label}: güven değeri tanımlı değil ({row['guven']}).")
        if row.get("durum") and row["durum"] not in STATUSES:
            found.append(f"{label}: durum tanımlı değil ({row['durum']}).")
        accessed, recheck = valid_day(row.get("erisim_tarihi")), valid_day(row.get("yeniden_kontrol_tarihi"))
        if row.get("erisim_tarihi") and not accessed:
            found.append(f"{label}: erişim tarihi YYYY-AA-GG biçiminde değil.")
        if row.get("yeniden_kontrol_tarihi") and not recheck:
            found.append(f"{label}: yeniden kontrol tarihi YYYY-AA-GG biçiminde değil.")
        if accessed and recheck and recheck <= accessed:
            found.append(f"{label}: yeniden kontrol tarihi erişim tarihinden sonra olmalı.")
        if row.get("belge_tarihi") and not valid_partial(row["belge_tarihi"]):
            found.append(f"{label}: belge tarihi YYYY, YYYY-AA veya YYYY-AA-GG biçiminde değil.")
        if row.get("belge_sha256") and not SHA_PATTERN.fullmatch(row["belge_sha256"]):
            found.append(f"{label}: SHA-256 64 küçük onaltılık karakter olmalı.")
        if row.get("durum") in ("dogrulandi", "celiskili", "yerine_gecildi"):
            if not row.get("kaynak_url", "").startswith("https://"):
                found.append(f"{label}: doğrulanmış satırın kaynak adresi https ile başlamalı.")
            if not row.get("belge_sha256"):
                found.append(f"{label}: doğrulanmış satırda belgenin SHA-256'sı zorunlu.")
        if row.get("durum") == "celiskili" and not row.get("celiski_notu"):
            found.append(f"{label}: çelişkili satırda çelişki notu zorunlu.")
        if len((row.get("kisa_alinti") or "").split()) > MAX_QUOTE_WORDS:
            found.append(f"{label}: kısa alıntı {MAX_QUOTE_WORDS} kelimeyi geçiyor.")
    verified = {row.get("id") for row in rows if row.get("durum") == "dogrulandi"}
    for number, row in enumerate(rows, 2):
        if row.get("durum") != "yerine_gecildi":
            continue
        label = f"{number}. satır ({row.get('id') or 'kimliksiz'})"
        match = REPLACED_BY.search(row.get("not") or "")
        if not match:
            found.append(f"{label}: yerine geçilen satırın notunda 'yerine geçen: <kimlik>' yazmalı.")
        elif match.group(1) not in verified:
            found.append(f"{label}: yerine geçen satır ({match.group(1)}) tabloda doğrulanmış bir satır değil.")
    return found


def replaced_by(row):
    """Identifier of the verified row that supersedes this one, or None."""
    match = REPLACED_BY.search(row.get("not") or "") if row.get("durum") == "yerine_gecildi" else None
    return match.group(1) if match else None


def snapshot(path, on=None):
    """API payload: rows with an 'overdue' flag, labels and the validation result of the committed table."""
    on = on or today()
    rows = read(path)
    for row in rows:
        recheck = valid_day(row["yeniden_kontrol_tarihi"])
        row["overdue"] = bool(recheck and recheck < on)
        row["replaced_by"] = replaced_by(row)
    return {"available": True, "file": path.name, "today": on.isoformat(), "topics": TOPICS, "statuses": STATUSES,
            "problems": problems(rows), "rows": rows}
