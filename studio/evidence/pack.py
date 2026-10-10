"""Evidence pack: a destination template filled with data blocks into one Markdown file and the same content as JSON.

Generic core: the template, its parameters and the blocks it names come from the destination profile; this module runs the blocks,
numbers the rows, builds the header (generation date, each source's last run and whether it is due, known gaps), the number
checklist (every number of the pack on one line with its evidence row) and stores both files under the data folder with their
SHA-256. A pack holds no interpretation, advice or ranking.
"""
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from .. import refresh
from . import blocks as B
from .templates import TemplateError, fill, read_all, resolve

FORMAT = "30a-studio-kanit-paketi/1"
NO_ADVICE = "Bu paket yorum, tavsiye ya da sıralama içermez; yalnız kanıt, etiketi ve kullanım notu."
NUMBER = re.compile(r"\d{4}-\d{2}-\d{2}|\d+(?:,\d{3})*(?:\.\d+)?")
SMALL_SAMPLE = 20         # fewer priced listings per window than this is a small sample (our threshold, M11/M14)


class PackError(ValueError):
    """User-facing reason why a pack cannot be generated or read."""


def destination_templates(profile):
    folder = getattr(profile, "EVIDENCE_TEMPLATES", None)
    return read_all(folder, set(B.BLOCKS)) if folder else {}


def numbers_of(evidence):
    """Number tokens of a row: its value and every number written in its statement, extra value and quote (ISO dates as one token)."""
    texts = [evidence.get("ifade"), evidence.get("deger_ek")]
    value = evidence.get("deger")
    tokens = []
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        tokens.append(value_text(value))
    elif value:
        texts.append(str(value))
    for text in texts:
        for token in NUMBER.findall(text or ""):
            if token not in tokens:
                tokens.append(token)
    return tokens


def value_text(value):
    if isinstance(value, bool) or value is None:
        return "" if value is None else str(value)
    if isinstance(value, int) or float(value).is_integer() and abs(value) >= 100:
        return B.number(value, 0)
    return f"{value:,}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)


def known_gaps(data):
    """Gaps computed from the data the pack read: unpriced agency companies, small samples, restaurants without a level, OpenStreetMap
    limits and unconfirmed points, single-company inventories, superseded or unverified reference rows."""
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
        for region in data.order:
            cells = [c for c in summary["cells"] if c["region_id"] == region]
            counts = [c["priced_count"] for c in cells]
            own = [c["own"]["priced_count"] for c in cells]
            if counts and not any(counts) and any(own):
                gaps.append(f"{data.names[region]}: fiyatlar tek bir şirketin kendi envanterinden geliyor; Book>Direct ilanlarıyla karşılaştırılmaz.")
            elif counts and any(counts) and sorted(counts)[len(counts) // 2] < SMALL_SAMPLE:
                gaps.append(f"{data.names[region]}: kiralama fiyatında küçük örnek (pencere başına ortanca {sorted(counts)[len(counts) // 2]} ilan).")
    run, sites = B.restaurant_summary(data)
    if sites:
        coverage = sites["coverage"]
        gaps.append(f"Restoranlar: {coverage['restaurants']} restoranın {coverage['restaurants'] - coverage['with_level']}'inde fiyat seviyesi "
                    f"hesaplanamadı (menü yok, fiyat yok ya da 5'ten az ana yemek fiyatı).")
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
            gaps.append("Bu bilgisayardan sitesi okunamayan zincir ve kurumlar (noktaları doğrulanamadı): " + ", ".join(unread) + ".")
    table, _ = B.reference_rows(data)
    unverified = [r["id"] for r in table if r["durum"] == "dogrulanamadi"]
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
    checklist = [{"ifade": e["ifade"], "deger": token, "birim": e.get("birim"), "kanit": e["id"]}
                 for s in sections for e in s["rows"] if e["durum"] == "var" for token in numbers_of(e)]
    evidence_count = sum(len(s["rows"]) for s in sections)
    destination = db.destination(destination_id)
    return {
        "format": FORMAT,
        "template": {k: template[k] for k in ("key", "version", "title", "question", "dimensions", "file")},
        "parameters": resolved,
        "destination": {"id": destination_id, "name": destination["name"] if destination else destination_id},
        "created_at": now.isoformat(timespec="seconds"),
        "header": {"uretim_tarihi": now.isoformat(timespec="seconds"), "kaynaklar": sources_header(data, today),
                   "bilinen_bosluklar": known_gaps(data), "not": NO_ADVICE,
                   "birimler": "Değerler ABD birimleriyle (°F, inç, mil, USD) ve ABD sayı biçimiyle (binlik virgül, ondalık nokta) yazılır; "
                               "°C, mm ve km karşılıkları yanında."},
        "sections": sections,
        "checklist": checklist,
        "counts": {"sections": len(sections), "evidence": evidence_count, "numbers": len(checklist),
                   "missing": sum(1 for s in sections for e in s["rows"] if e["durum"] == B.MISSING)},
    }


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
    labels = ", ".join(B.LABELS)
    lines += ["", f"Etiketler: {labels}. 'veri yok' satırları eksik veriyi gösterir; paketten düşürülmez.", ""]
    for section in pack["sections"]:
        lines += [f"## {section['title']}", "", f"**Soru:** {section['question']}", ""]
        current = None
        for evidence in section["rows"]:
            if evidence["blok"] != current:
                current = evidence["blok"]
                lines += ["", f"### Veri bloğu: {current}", ""]
            lines.append(evidence_markdown(evidence))
        lines.append("")
    lines += ["## Sayı kontrol listesi", "", "| İfade | Değer | Birim | Kanıt |", "|---|---|---|---|"]
    lines += [f"| {cell(item['ifade'])} | {cell(item['deger'])} | {cell(item['birim'])} | {item['kanit']} |" for item in pack["checklist"]]
    return "\n".join(lines) + "\n"


def evidence_markdown(evidence):
    if evidence["durum"] == B.MISSING:
        text = f"- **{evidence['id']}** · {evidence['ifade']} — **veri yok**: {evidence['not']} · kapsam: {evidence['kapsam']}"
        return text + (f"\n  - Kullanım notu: {evidence['kullanim_notu']}" if evidence.get("kullanim_notu") else "")
    value = value_text(evidence["deger"]) if isinstance(evidence["deger"], (int, float)) else evidence["deger"]
    head = f"- **{evidence['id']}** · {evidence['ifade']}"
    if value not in (None, ""):
        head += f" — **{value}{' ' + evidence['birim'] if evidence.get('birim') else ''}**"
        if evidence.get("deger_ek"):
            head += f" ({evidence['deger_ek']})"
    parts = [head, f"  - Kapsam: {evidence['kapsam']} · Etiket: {evidence['etiket']}"
             + (f" · Örneklem: {evidence['orneklem']}" if evidence.get("orneklem") is not None else ""),
             f"  - Kaynak: {source_text(evidence['kaynak'])}"]
    if evidence.get("ifade_en"):
        parts.append(f"  - Kaynak satırının İngilizce ifadesi: {evidence['ifade_en']}")
    if evidence.get("alinti"):
        parts.append(f"  - Kaynaktan kısa alıntı: “{evidence['alinti']}”")
    if evidence.get("not"):
        parts.append(f"  - Not: {evidence['not']}")
    parts.append(f"  - Kullanım notu: {evidence['kullanim_notu']}")
    return "\n".join(parts)


# --- Storage --------------------------------------------------------------------------------------------------------------------

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def store(db, pack):
    """Write the Markdown and JSON under <data>/evidence/ and record both with their SHA-256 in evidence_packs."""
    folder = db.path.parent / "evidence"
    folder.mkdir(exist_ok=True)
    identifier = uuid.uuid4().hex
    stamp = pack["created_at"][:19].replace("-", "").replace(":", "").replace("T", "-")
    name = "-".join([stamp, pack["template"]["key"], *[slug(v["id"]) for v in pack["parameters"].values()], identifier[:8]])
    md_bytes = markdown(pack).encode("utf-8")
    json_bytes = (json.dumps({**pack, "id": identifier}, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
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
    return decode(record)


def decode(row):
    item = dict(row)
    item["params"] = json.loads(item["params"])
    return item


def stored(db, destination_id):
    with db.connect() as con:
        return [decode(r) for r in con.execute("SELECT * FROM evidence_packs WHERE destination_id=? ORDER BY created_at DESC, rowid DESC",
                                               (destination_id,))]


def stored_file(db, identifier, kind):
    """Path of a stored pack's Markdown or JSON after its SHA-256 is checked against the record."""
    with db.connect() as con:
        row = con.execute("SELECT * FROM evidence_packs WHERE id=?", (identifier,)).fetchone()
    if row is None:
        raise PackError("Bu kanıt paketi bulunamadı.")
    relative, digest = (row["markdown_file"], row["markdown_sha256"]) if kind == "md" else (row["json_file"], row["json_sha256"])
    path = (db.path.parent / relative).resolve()
    if not path.is_relative_to((db.path.parent / "evidence").resolve()) or not path.is_file():
        raise PackError("Kanıt paketinin dosyası bulunamadı.")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise PackError("Kanıt paketinin dosyası kayıttaki SHA-256 ile uyuşmuyor.")
    return path, decode(row)
