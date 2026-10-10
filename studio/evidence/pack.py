"""Evidence pack: a destination template filled with data blocks into one Markdown file and the same content as JSON.

Generic core: the template, its parameters and the blocks it names come from the destination profile; this module runs the blocks,
numbers the rows, builds the header (generation date, each source's last run and whether it is due, known gaps, rows to re-check
before publishing) and the number checklist, and stores the files of one generation under the data folder with their SHA-256: the
full pack (Markdown + JSON, the evidence), the number checklist (CSV) and the writer's summary (Markdown, derived from the pack).
A pack holds no interpretation, advice or ranking.

Number checklist (GÖREV-12): built only from structured fields — a row's value, its extra values (quartiles, shares, range ends,
conversions) and its sample size. Digits inside statements (names, addresses, road and record numbers, periods) never enter it;
a reference row contributes its table value only, and the rest of its statement is checked against the statement itself.
"""
import csv
import hashlib
import io
import json
import re
import uuid
from datetime import datetime, timezone

from .. import refresh
from . import blocks as B
from . import summary as S
from .templates import TemplateError, fill, read_all, resolve

FORMAT = "30a-studio-kanit-paketi/2"
NO_ADVICE = "Bu paket yorum, tavsiye ya da sıralama içermez; yalnız kanıt, etiketi ve kullanım notu."
CHECKLIST_COLUMNS = ("kanit", "tur", "deger", "birim", "etiket")
EXTRA_FILES = {"sayilar": "-sayilar.csv", "yazar_ozeti": "-yazar-ozeti.md"}


class PackError(ValueError):
    """User-facing reason why a pack cannot be generated or read."""


def destination_templates(profile):
    folder = getattr(profile, "EVIDENCE_TEMPLATES", None)
    return read_all(folder, set(B.BLOCKS)) if folder else {}


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def value_text(value):
    """A value as the pack writes it: US formatting, thousands with commas."""
    if value is None:
        return ""
    if not is_number(value):
        return str(value)
    if isinstance(value, int) or float(value).is_integer() and abs(value) >= 100:
        return B.number(value, 0)
    return f"{value:,}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)


def numbers_of(evidence):
    """Checklist entries of one row, from structured fields only: the value (a reference row's table value when it holds a digit), the
    extra values and the sample size."""
    if evidence["durum"] != "var":
        return []
    entries = []
    value = evidence.get("deger")
    if is_number(value) or isinstance(value, str) and re.search(r"\d", value):
        entries.append(("ana", value, evidence.get("birim")))
    for item in evidence.get("ek_degerler") or []:
        entries.append((item["tur"], item["deger"], item["birim"]))
    if evidence.get("orneklem") is not None and not any(kind == "orneklem" for kind, _, _ in entries):
        entries.append(("orneklem", evidence["orneklem"], "örnek"))
    return [{"kanit": evidence["id"], "tur": kind, "deger": number, "birim": unit, "etiket": evidence["etiket"]} for kind, number, unit in entries]


def known_gaps(data, focus=None, references=None):
    """Gaps computed from the data the pack read: unpriced agency companies, small samples, restaurants without a level, OpenStreetMap
    limits and unconfirmed points, single-company inventories, superseded or unverified reference rows. A pack about some regions
    (`focus`) lists only their region gaps; unverified reference rows are listed when the pack carries them (`references`)."""
    gaps = []
    run, summary = B.agency_summary(data)
    if summary:
        with data.db.connect() as con:
            missing = con.execute("""SELECT REPLACE(COALESCE(domain, url_host), 'www.', ''), COUNT(*) FROM agency_rate_listings
                WHERE run_id=? AND page_status='no_adapter' AND COALESCE(domain, url_host) IS NOT NULL
                GROUP BY 1 HAVING COUNT(*) >= 20 ORDER BY COUNT(*) DESC""", (run["id"],)).fetchall()
            blocked = con.execute("SELECT COUNT(*) FROM agency_rate_listings WHERE run_id=? AND page_status='blocked'", (run["id"],)).fetchone()[0]
        if missing:
            gaps.append("Fiyatı okunamayan kiralama şirketleri (sitesi için okuyucu yok, Book>Direct ilan sayısıyla): "
                        + ", ".join(f"{domain} {count}" for domain, count in missing) + ".")
        if blocked:
            gaps.append(f"Sitesi doğrudan isteği engellediği için fiyatı okunamayan ilan: {blocked}.")
        for region in [r for r in data.order if not focus or r in focus]:
            cells = [c for c in summary["cells"] if c["region_id"] == region]
            counts = [c["priced_count"] for c in cells]
            own = [c["own"]["priced_count"] for c in cells]
            if counts and not any(counts) and any(own):
                gaps.append(f"{data.names[region]}: fiyatlar tek bir şirketin kendi envanterinden geliyor; Book>Direct ilanlarıyla karşılaştırılmaz.")
            elif counts and any(counts) and sorted(counts)[len(counts) // 2] < B.SMALL_SAMPLE:
                gaps.append(f"{data.names[region]}: kiralama fiyatında küçük örnek (pencere başına ortanca {sorted(counts)[len(counts) // 2]} ilan).")
    run, sites = B.restaurant_summary(data)
    if sites:
        coverage = sites["coverage"]
        gaps.append(f"Restoranlar: fiyat seviyesi hesaplanamayan restoran {coverage['restaurants'] - coverage['with_level']} / "
                    f"{coverage['restaurants']} (menü yok, fiyat yok ya da 5'ten az ana yemek fiyatı).")
    run = data.run("openstreetmap-daily-needs")
    if run:
        meta = run["metadata"] or {}
        gaps.append("Günlük ihtiyaç noktaları OpenStreetMap'e dayanır; OpenStreetMap eksik ya da eski olabilir. Mesafeler kuş uçuşudur.")
        if meta.get("osm_unconfirmed"):
            gaps.append(f"Resmî kaynakta doğrulanamadığı için acil sağlık ölçülerine girmeyen OpenStreetMap noktası: {meta['osm_unconfirmed']}.")
        with data.db.connect() as con:
            unread = [r[0] for r in con.execute("SELECT DISTINCT chain FROM poi_chain_checks WHERE run_id=? AND outcome='okunamadi' ORDER BY chain",
                                                (run["id"],))]
        if unread:
            gaps.append("Sitesi bu bilgisayardan okunamayan ya da kendi sitesi bulunamayan zincir ve kurumlar (noktaları doğrulanamadı): "
                        + ", ".join(unread) + ".")
    table, _ = B.reference_rows(data)
    unverified = [r["id"] for r in table if r["durum"] == "dogrulanamadi" and (references is None or r["id"] in references)]
    if unverified:
        gaps.append("Doğrulanamayan referans satırları (videoda kullanılmaz): " + ", ".join(unverified) + ".")
    lodging_run, lodging = B.lodging_summary(data)
    if lodging:
        gaps.append("Book>Direct ilan sayıları tarihli aramalarda görünen ilanlardır; tam envanter değildir.")
    return gaps


def sources_header(data, today):
    """Last successful run of each source the pack read, with its refresh interval and whether it is due."""
    status = {item["connector"]: item for item in refresh.status(data.db, data.destination_id, today=today)["items"]}
    rows = []
    for connector, run in sorted(data.used.items(), key=lambda item: item[0]):
        item = status.get(connector) or {}
        rows.append({"kaynak": (run["metadata"] or {}).get("source_name") or connector, "toplayici": connector, "cekim_kimligi": run["id"],
                     "son_cekim": (run["finished_at"] or run["fetched_at"] or "")[:10], "sonraki": item.get("next_due_on"),
                     "zamani_geldi": bool(item.get("due"))})
    return rows


def short(text, limit=160):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def recheck_before_publishing(sections, volatile):
    """Reference rows of the template's volatile topics and every row marked contradictory, with their re-check date."""
    found = []
    for section in sections:
        for evidence in section["rows"]:
            source = evidence.get("kaynak") or {}
            if evidence["durum"] != "var" or not source.get("referans"):
                continue
            if source.get("konu") in volatile or source.get("durum") == "celiskili":
                found.append({"kanit": evidence["id"], "referans": source["referans"], "ifade": short(evidence["ifade"], 100),
                              "durum": source.get("durum"), "konu": source.get("konu"),
                              "yeniden_kontrol_tarihi": source.get("yeniden_kontrol_tarihi"), "celiski_notu": evidence.get("celiski_notu")})
    return found


def generate(db, destination_id, profile, template_key, values=None, *, today=None, now=None):
    available = destination_templates(profile)
    template = available.get(template_key)
    if template is None:
        raise PackError("Bu destinasyonda böyle bir şablon yok.")
    now = now or datetime.now(timezone.utc)
    today = today or now.date()
    data = B.BlockData(db, destination_id, profile, today)
    try:
        resolved = resolve(template, values, data.regions)
    except TemplateError as exc:
        raise PackError(str(exc)) from exc
    sections, counter = [], 0
    for section in template["sections"]:
        rows = []
        for spec in section["blocks"]:
            spec = fill(spec, resolved)
            for evidence in B.BLOCKS[spec["block"]](data, spec):
                counter += 1
                rows.append({"id": f"K{counter:04d}", "bolum": section["key"], "blok": spec["block"], **evidence})
        sections.append({"key": section["key"], "title": section["title"], "question": section["question"], "rows": rows})
    checklist = [entry for s in sections for e in s["rows"] for entry in numbers_of(e)]
    evidence_count = sum(len(s["rows"]) for s in sections)
    destination = db.destination(destination_id)
    return {
        "format": FORMAT,
        "template": {k: template[k] for k in ("key", "version", "title", "question", "dimensions", "volatile_topics", "file")},
        "parameters": resolved,
        "destination": {"id": destination_id, "name": destination["name"] if destination else destination_id},
        "created_at": now.isoformat(timespec="seconds"),
        "header": {"uretim_tarihi": now.isoformat(timespec="seconds"), "kaynaklar": sources_header(data, today),
                   "bilinen_bosluklar": known_gaps(data, {v["id"] for v in resolved.values()} or None,
                                                   {(e.get("kaynak") or {}).get("referans") for s in sections for e in s["rows"]}),
                   "not": NO_ADVICE,
                   "yayindan_once_kontrol": recheck_before_publishing(sections, set(template["volatile_topics"])),
                   "birimler": "Değerler ABD birimleriyle (°F, inç, mil, USD) ve ABD sayı biçimiyle (binlik virgül, ondalık nokta) yazılır; "
                               "°C, mm ve km karşılıkları yanında."},
        "sections": sections,
        "checklist": checklist,
        "counts": {"sections": len(sections), "evidence": evidence_count, "numbers": len(checklist),
                   "missing": sum(1 for s in sections for e in s["rows"] if e["durum"] == B.MISSING)},
    }


# --- Number checklist (CSV) -----------------------------------------------------------------------------------------------------

def checklist_csv(pack):
    """The checklist as CSV text: kanit, tur, deger, birim, etiket (values as in the JSON)."""
    handle = io.StringIO()
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(CHECKLIST_COLUMNS)
    for item in pack["checklist"]:
        writer.writerow(["" if item[k] is None else item[k] for k in CHECKLIST_COLUMNS])
    return handle.getvalue()


# --- Markdown -------------------------------------------------------------------------------------------------------------------

def cell(text):
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def source_text(source):
    if not source:
        return "—"
    name = source.get("ad") or "kaynak"
    parts = [f"[{name}]({source['url']})" if source.get("url") else name]
    if source.get("belge_tarihi"):
        parts.append(f"belge {source['belge_tarihi']}")
    if source.get("erisim_tarihi"):
        parts.append(f"erişim {source['erisim_tarihi']}")
    if source.get("cekim_kimligi"):
        parts.append(f"çekim {source['cekim_kimligi']}")
    if source.get("referans"):
        parts.append(f"satır {source['referans']}")
    if source.get("sha256"):
        parts.append(f"SHA-256 {source['sha256']}")
    return " · ".join(parts)


def file_name(pack, key):
    """Name of an attached file of the pack: the stored name once saved, a placeholder before."""
    stored = (pack.get("dosyalar") or {}).get(key)
    return stored["dosya"].split("/")[-1] if stored else f"<paket>{EXTRA_FILES[key]}"


def recheck_lines(pack):
    items = pack["header"].get("yayindan_once_kontrol") or []
    if not items:
        return ["- —"]
    lines = []
    for item in items:
        line = f"- {item['kanit']} · {item['ifade']} · satır {item['referans']} · yeniden kontrol {item['yeniden_kontrol_tarihi'] or '—'}"
        if item.get("durum") == "celiskili":
            line += f" · çelişkili: {item.get('celiski_notu') or '—'}"
        lines.append(line)
    return lines


def markdown(pack):
    t = pack["template"]
    lines = [f"# {t['title']}", "", f"**Ana soru:** {t['question']}", ""]
    if pack["parameters"]:
        lines += ["**Parametreler:** " + ", ".join(f"{k} = {v['name']} ({v['id']})" for k, v in pack["parameters"].items()), ""]
    header = pack["header"]
    lines += [f"- Üretim tarihi: {header['uretim_tarihi']}", f"- Destinasyon: {pack['destination']['name']}",
              f"- Şablon: {t['key']} (sürüm {t['version']})", f"- {header['not']}", f"- {header['birimler']}",
              f"- Boyut: {pack['counts']['sections']} bölüm, {pack['counts']['evidence']} kanıt satırı, {pack['counts']['numbers']} sayı, "
              f"{pack['counts']['missing']} 'veri yok' satırı", "", "## Kaynakların son çekimi", "",
              "| Kaynak | Son çekim | Çekim kimliği | Sonraki | Zamanı geldi mi |", "|---|---|---|---|---|"]
    for item in header["kaynaklar"]:
        lines.append(f"| {cell(item['kaynak'])} | {item['son_cekim']} | {item['cekim_kimligi']} | {item['sonraki'] or '—'} | "
                     f"{'evet' if item['zamani_geldi'] else 'hayır'} |")
    lines += ["", "## Bilinen boşluklar", ""] + [f"- {gap}" for gap in header["bilinen_bosluklar"] or ["—"]]
    lines += ["", "## Yayından önce kontrol edilecek satırlar", "",
              f"Şablonun oynak konuları ({', '.join(t.get('volatile_topics') or []) or '—'}) ve çelişkili bütün satırlar:", ""] + recheck_lines(pack)
    labels = ", ".join(B.LABELS)
    lines += ["", f"Etiketler: {labels}. 'veri yok' satırları eksik veriyi gösterir; paketten düşürülmez.", ""]
    for section in pack["sections"]:
        lines += [f"## {section['title']}", "", f"**Soru:** {section['question']}", ""]
        for group in block_groups(section["rows"]):
            lines += block_markdown(group)
        lines.append("")
    lines += ["## Sayı kontrol listesi", "",
              f"Ayrı dosya: `{file_name(pack, 'sayilar')}` ({len(pack['checklist'])} satır; sütunlar {', '.join(CHECKLIST_COLUMNS)}). Liste yalnız "
              "yapılandırılmış alanlardan üretilir (değer, ek değerler, örnek büyüklüğü); ifade metnindeki adlar, adresler, yol ve kimlik numaraları "
              "listeye girmez. Referans satırlarında yalnız tablonun değer alanı listededir; ifadedeki diğer sayılar satır metnine karşı kontrol edilir."]
    return "\n".join(lines) + "\n"


SHARED = ("kapsam", "etiket", "kaynak", "not", "kullanim_notu")
SHARED_LABELS = {"kapsam": "Kapsam", "etiket": "Etiket", "kaynak": "Kaynak", "not": "Not", "kullanim_notu": "Kullanım notu"}


def block_groups(rows):
    """Consecutive rows of the same block; the Markdown writes what they share once (the JSON keeps every field on every row)."""
    groups = []
    for evidence in rows:
        if groups and groups[-1][0]["blok"] == evidence["blok"]:
            groups[-1].append(evidence)
        else:
            groups.append([evidence])
    return groups


def field_text(key, value):
    return source_text(value) if key == "kaynak" else str(value)


def block_markdown(rows):
    present = [r for r in rows if r["durum"] == "var"]
    shared = {}
    if len(present) > 1:
        for key in SHARED:
            values = [json.dumps(r.get(key), ensure_ascii=False, sort_keys=True) for r in present]
            if len(set(values)) == 1 and present[0].get(key):
                shared[key] = present[0][key]
    lines = ["", f"### Veri bloğu: {rows[0]['blok']}", ""]
    if shared:
        lines += [f"Bu bloktaki satırların ortak bilgisi ({len(present)} satır):"] + [f"- {SHARED_LABELS[k]}: {field_text(k, v)}" for k, v in shared.items()] + [""]
    lines += [evidence_markdown(r, shared if r["durum"] == "var" else {}) for r in rows]
    return lines


def evidence_markdown(evidence, shared=None):
    shared = shared or {}
    if evidence["durum"] == B.MISSING:
        text = f"- **{evidence['id']}** · {evidence['ifade']} — **veri yok**: {evidence['not']} · kapsam: {evidence['kapsam']}"
        return text + (f"\n  - Kullanım notu: {evidence['kullanim_notu']}" if evidence.get("kullanim_notu") else "")
    value = value_text(evidence["deger"])
    head = f"- **{evidence['id']}** · {evidence['ifade']}"
    if value not in (None, ""):
        head += f" — **{value}{' ' + evidence['birim'] if evidence.get('birim') else ''}**"
        if evidence.get("deger_ek"):
            head += f" ({evidence['deger_ek']})"
    facts = [f"{SHARED_LABELS[k]}: {evidence[k]}" for k in ("kapsam", "etiket") if k not in shared]
    if evidence.get("orneklem") is not None:
        facts.append(f"Örneklem: {evidence['orneklem']}")
    if evidence.get("kucuk_ornek"):
        facts.append("küçük örnek")
    parts = [head] + ([f"  - {' · '.join(facts)}"] if facts else [])
    if "kaynak" not in shared:
        parts.append(f"  - Kaynak: {source_text(evidence['kaynak'])}")
    if evidence.get("ifade_en"):
        parts.append(f"  - Kaynak satırının İngilizce ifadesi: {evidence['ifade_en']}")
    if evidence.get("alinti"):
        parts.append(f"  - Kaynaktan kısa alıntı: “{evidence['alinti']}”")
    if evidence.get("celiski_notu"):
        parts.append(f"  - Çelişki: {evidence['celiski_notu']}")
    if evidence.get("not") and "not" not in shared:
        parts.append(f"  - Not: {evidence['not']}")
    if "kullanim_notu" not in shared:
        parts.append(f"  - Kullanım notu: {evidence['kullanim_notu']}")
    return "\n".join(parts)


# --- Storage --------------------------------------------------------------------------------------------------------------------

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def store(db, pack):
    """Write one generation under <data>/evidence/: the full pack (Markdown + JSON, recorded with their SHA-256 in evidence_packs) and,
    attached to it, the number checklist (CSV) and the writer's summary; their names and SHA-256 are in the pack's JSON."""
    folder = db.path.parent / "evidence"
    folder.mkdir(exist_ok=True)
    identifier = uuid.uuid4().hex
    stamp = pack["created_at"][:19].replace("-", "").replace(":", "").replace("T", "-")
    name = "-".join([stamp, pack["template"]["key"], *[slug(v["id"]) for v in pack["parameters"].values()], identifier[:8]])
    pack = {**pack, "id": identifier}
    attached = {"sayilar": checklist_csv(pack).encode("utf-8"), "yazar_ozeti": S.render(pack).encode("utf-8")}
    pack["dosyalar"] = {key: {"dosya": f"evidence/{name}{EXTRA_FILES[key]}", "sha256": hashlib.sha256(data).hexdigest()}
                        for key, data in attached.items()}
    md_bytes = markdown(pack).encode("utf-8")
    json_bytes = (json.dumps(pack, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    for key, data in attached.items():
        (folder / f"{name}{EXTRA_FILES[key]}").write_bytes(data)
    (folder / f"{name}.md").write_bytes(md_bytes)
    (folder / f"{name}.json").write_bytes(json_bytes)
    record = {"id": identifier, "destination_id": pack["destination"]["id"], "template_key": pack["template"]["key"],
              "template_version": pack["template"]["version"], "title": pack["template"]["title"],
              "params": json.dumps({k: v["id"] for k, v in pack["parameters"].items()}, ensure_ascii=False), "created_at": pack["created_at"],
              "markdown_file": f"evidence/{name}.md", "markdown_sha256": hashlib.sha256(md_bytes).hexdigest(),
              "json_file": f"evidence/{name}.json", "json_sha256": hashlib.sha256(json_bytes).hexdigest(),
              "section_count": pack["counts"]["sections"], "evidence_count": pack["counts"]["evidence"],
              "number_count": pack["counts"]["numbers"], "missing_count": pack["counts"]["missing"]}
    with db.connect() as con:
        con.execute(f"INSERT INTO evidence_packs ({','.join(record)}) VALUES ({','.join('?' * len(record))})", tuple(record.values()))
    return {**decode(record), "ekler": {key: True for key in EXTRA_FILES}}


def decode(row):
    item = dict(row)
    item["params"] = json.loads(item["params"])
    return item


def attached_paths(db, row):
    stem = (db.path.parent / row["markdown_file"]).with_suffix("")
    return {key: stem.parent / f"{stem.name}{suffix}" for key, suffix in EXTRA_FILES.items()}


def stored(db, destination_id):
    """Stored packs, newest first; `ekler` says which attached files exist (packs before GÖREV-12 have none)."""
    with db.connect() as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM evidence_packs WHERE destination_id=? ORDER BY created_at DESC, rowid DESC",
                                             (destination_id,))]
    return [{**decode(row), "ekler": {key: path.is_file() for key, path in attached_paths(db, row).items()}} for row in rows]


def verified(path, digest, message):
    if not path.is_file():
        raise PackError(message)
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise PackError("Kanıt paketinin dosyası kayıttaki SHA-256 ile uyuşmuyor.")
    return data


def stored_file(db, identifier, kind):
    """Path of a stored pack's file ("md", "json", "sayilar", "yazar_ozeti") after its SHA-256 is checked: the Markdown and JSON against
    the record, an attached file against the SHA-256 written in the (checked) JSON."""
    with db.connect() as con:
        row = con.execute("SELECT * FROM evidence_packs WHERE id=?", (identifier,)).fetchone()
    if row is None:
        raise PackError("Bu kanıt paketi bulunamadı.")
    base = (db.path.parent / "evidence").resolve()
    json_path = (db.path.parent / row["json_file"]).resolve()
    if kind in ("md", "json"):
        relative, digest = (row["markdown_file"], row["markdown_sha256"]) if kind == "md" else (row["json_file"], row["json_sha256"])
        path = (db.path.parent / relative).resolve()
        if not path.is_relative_to(base):
            raise PackError("Kanıt paketinin dosyası bulunamadı.")
        verified(path, digest, "Kanıt paketinin dosyası bulunamadı.")
        return path, decode(row)
    if kind not in EXTRA_FILES:
        raise PackError("Bilinmeyen dosya türü.")
    if not json_path.is_relative_to(base):
        raise PackError("Kanıt paketinin dosyası bulunamadı.")
    pack = json.loads(verified(json_path, row["json_sha256"], "Kanıt paketinin dosyası bulunamadı."))
    attached = (pack.get("dosyalar") or {}).get(kind)
    if not attached:
        raise PackError("Bu paketle bu dosya üretilmemiş (GÖREV-12'den önceki üretim).")
    path = (db.path.parent / attached["dosya"]).resolve()
    if not path.is_relative_to(base):
        raise PackError("Kanıt paketinin dosyası bulunamadı.")
    verified(path, attached["sha256"], "Kanıt paketinin dosyası bulunamadı.")
    return path, decode(row)
