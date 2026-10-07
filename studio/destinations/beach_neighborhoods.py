"""Reviewed beach access -> neighborhood mapping files supplied by destination profiles.

A mapping file is generated once by tools/plaj_mahalle_esleme.py and committed. The app only reads and
validates it; it never recomputes a mapping. Beach records and the beach collector stay unchanged.
"""
import csv
import re

COLUMNS = ("external_id", "plaj_adi", "bolge_id", "yontem", "kaynak", "not", "belirsiz")
METHOD_OFFICIAL, METHOD_COUNTY, METHOD_COUNTY_ADJACENT = "resmi_rehber", "ilce_alt_bolum", "ilce_alt_bolum_yakin"
METHOD_NEIGHBORS, METHOD_DERIVED = "komsu_tutarliligi", "turetim_en_yakin_mahalle_noktasi"
METHOD_LABELS = {METHOD_OFFICIAL: "resmî rehber", METHOD_COUNTY: "ilçe alt bölüm verisi",
                 METHOD_COUNTY_ADJACENT: "ilçe alt bölüm verisi (bitişik)", METHOD_NEIGHBORS: "komşu erişimlerle tutarlı",
                 METHOD_DERIVED: "program türetimi"}
AMBIGUOUS = {"evet": True, "hayır": False}
ID_PATTERN = re.compile(r"[0-9a-f]{24}")


class MappingError(ValueError):
    """User-facing reason why a mapping file cannot be shown."""


def load(path, regions):
    """Validated rows in file order; regions are the destination's canonical regions (id, name)."""
    names = {region["id"]: region["name"] for region in regions}
    rows, seen = [], set()
    try:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != COLUMNS:
                raise MappingError("Plaj–mahalle eşleme dosyasının sütunları beklenen biçimde değil.")
            for line, row in enumerate(reader, 2):
                if None in row or None in row.values():
                    raise MappingError(f"Eşleme dosyasının {line}. satırında sütun sayısı hatalı.")
                identifier = row["external_id"]
                if not ID_PATTERN.fullmatch(identifier):
                    raise MappingError(f"Eşleme dosyasının {line}. satırında plaj kimliği geçersiz.")
                if identifier in seen:
                    raise MappingError(f"Eşleme dosyasında aynı plaj kimliği birden fazla satırda: {identifier}.")
                if row["bolge_id"] not in names:
                    raise MappingError(f"Eşleme dosyasının {line}. satırındaki bölge kimliği bu destinasyonda yok.")
                if row["yontem"] not in METHOD_LABELS:
                    raise MappingError(f"Eşleme dosyasının {line}. satırındaki yöntem tanınmıyor.")
                if row["belirsiz"] not in AMBIGUOUS:
                    raise MappingError(f"Eşleme dosyasının {line}. satırında belirsiz alanı evet veya hayır olmalı.")
                if not row["kaynak"].strip() or not row["plaj_adi"].strip():
                    raise MappingError(f"Eşleme dosyasının {line}. satırında plaj adı veya kaynak boş.")
                seen.add(identifier)
                rows.append({"external_id": identifier, "beach_name": row["plaj_adi"], "region_id": row["bolge_id"],
                             "region_name": names[row["bolge_id"]], "method": row["yontem"],
                             "method_label": METHOD_LABELS[row["yontem"]], "source": row["kaynak"],
                             "note": row["not"] or None, "ambiguous": AMBIGUOUS[row["belirsiz"]]})
    except (OSError, UnicodeError, csv.Error) as exc:
        raise MappingError("Plaj–mahalle eşleme dosyası okunamadı.") from exc
    return rows
