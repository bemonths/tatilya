"""Writer's summary of an evidence pack (GÖREV-12): a short Markdown file derived only from the pack object of the same generation, for
the person who writes the article and checks its numbers. Same sections and K identifiers as the full pack; numeric series as tables
(each table row ends with the K range it shows); each block's usage note once and verbatim; reference and other rows as single lines;
one source list at the end. Values are written exactly as the pack writes them; nothing is queried again; no interpretation, advice
or ranking — rows keep the pack's order (regions west to east).
"""
import re

from . import blocks as B

ABBREVIATIONS = {"kaynak gerçeği": "KG", "bizim hesabımız": "BH", "türetilmiş": "T", "yaklaşık": "Y"}
BLOCK_TITLES = {
    "neighborhoods": "Mahalle tanımı", "beach_accesses": "Halka açık plaj erişimleri", "beach_features": "Plaj erişimlerindeki olanaklar",
    "references": "Referans satırları", "climate_months": "İklim normalleri", "sea_water": "Deniz suyu sıcaklığı", "storms": "Kasırga geçişleri",
    "tdt_season": "Turist vergisi sezon deseni", "lodging_inventory": "Book>Direct ilan sayıları",
    "lodging_prices": "Kiralama şirketlerinin haftalık fiyatları", "lodging_bedrooms": "Oda grubuna göre haftalık fiyat",
    "restaurants": "Restoranlar", "daily_needs": "Günlük ihtiyaç mesafeleri", "traffic": "Trafik (FDOT)",
}
SENTENCE = "Bu özet tam paketten türetilmiştir; asıl kanıt tam pakettir; kimlikler aynıdır."


def value_text(value):
    from .pack import value_text as text
    return text(value)


def tag(evidence):
    return f"[{ABBREVIATIONS.get(evidence.get('etiket'), '—')}]" if evidence["durum"] == "var" else "[—]"


def ids_text(ids):
    """K0001, K0002, K0003, K0007 -> 'K0001–K0003, K0007'."""
    numbers = sorted({int(i[1:]) for i in ids})
    parts, start = [], None
    for index, value in enumerate(numbers):
        if start is None:
            start = value
        if index + 1 == len(numbers) or numbers[index + 1] != value + 1:
            parts.append(f"K{start:04d}" if start == value else f"K{start:04d}–K{value:04d}")
            start = None
    return ", ".join(parts)


def cell(text):
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


PLAIN_NUMBER = re.compile(r"^-?\d[\d,]*(\.\d+)?$")


def unit_value(value, unit, with_unit=True):
    """'$3,091', '$500 (üst sınır)', '%48.3'; a value that is not a single number keeps its unit after it ('5 / 15 USD (saat / gün)')."""
    text = value_text(value)
    single = not isinstance(value, bool) and isinstance(value, (int, float)) or bool(PLAIN_NUMBER.match(text))
    if unit and unit.startswith("USD") and single:
        rest = unit[3:].strip()
        return f"${text}" + (f" {rest}" if rest and with_unit else "")
    if unit == "%" and single:
        return f"%{text}"
    return f"{text} {unit}" if unit and with_unit else text


# addresses and local file paths stay in the full pack; the summary carries no URL
ADDRESS = re.compile(r"https?://[^\s)]+")
LOCAL_PATH = re.compile(r"work/[^\s)]+")
SENTENCE_BREAK = re.compile(r"(?<=[a-zçğıöşü0-9)'\"]\.)\s+(?=[A-ZÇĞİÖŞÜ'\"(])")


def note_text(text):
    return LOCAL_PATH.sub("yerel kayıt", ADDRESS.sub("adres tam pakette", text))


SHORT_SENTENCE = 40


def sentences_of(text):
    """Sentences of a note; a short sentence ('Çelişki sürüyor.') stays with the one before it, whose context it needs."""
    parts = []
    for part in SENTENCE_BREAK.split(text):
        if parts and len(part) < SHORT_SENTENCE:
            parts[-1] = f"{parts[-1]} {part}"
        else:
            parts.append(part)
    return parts


def extras_of(evidence, kind):
    return [item for item in evidence.get("ek_degerler") or [] if item["tur"] == kind]


HIDDEN_CONVERSIONS = {"km"}    # distance conversions stay in the full pack; the summary keeps °C and mm beside °F and inches


def value_cell(evidence, with_unit, with_sample=True):
    """'$3,091 (30)', '63.1 / 17.3 °C (19)', '2.36 · %0 (114)', '—' for missing data; '*' marks a small sample."""
    if evidence["durum"] != "var":
        return "—"
    conversions = [item for item in extras_of(evidence, "donusum") if item["birim"] not in HIDDEN_CONVERSIONS]
    # a value shown beside its conversion always carries its own unit ('60.2 °F / 15.7 °C')
    text = unit_value(evidence["deger"], evidence.get("birim"), with_unit or bool(conversions)) if evidence["deger"] is not None else "—"
    for item in conversions:
        text += f" / {value_text(item['deger'])} {item['birim']}"
    for item in extras_of(evidence, "pay"):
        text += f" · %{value_text(item['deger'])}"
    if with_sample and evidence.get("orneklem") is not None:
        text += f" ({value_text(evidence['orneklem'])})"
    if evidence.get("kucuk_ornek"):
        text += "*"
    return text


def quartile_cell(evidence):
    if evidence["durum"] != "var":
        return "—"
    low, high = extras_of(evidence, "alt_ceyrek"), extras_of(evidence, "ust_ceyrek")
    if not low or not high:
        return "—"
    text = f"{unit_value(low[0]['deger'], low[0]['birim'], False)}–{unit_value(high[0]['deger'], high[0]['birim'], False)}"
    return text + ("*" if evidence.get("kucuk_ornek") else "")


def source_line(rows):
    names = []
    for evidence in rows:
        source = evidence.get("kaynak") or {}
        if evidence["durum"] != "var" or not source:
            continue
        text = source.get("ad") or "kaynak"
        date = source.get("belge_tarihi") or source.get("erisim_tarihi")
        if date:
            text += f" · {date}"
        if text not in names:
            names.append(text)
    if not names:
        return None
    return "Kaynak: " + ("; ".join(names) if len(names) <= 3 else f"{names[0]} ve satır başına {len(names) - 1} kaynak daha (kaynak listesinde)")


COLUMN_NOTE_LIMIT = 160


def column_notes(present):
    """Short notes that differ from table row to table row go to a "Not" column of their table instead of the block head: only when
    every value of a table row carries the same note, the table has at least two different notes, no note is held by more than half of
    the table rows (a mostly shared note stays at the head once) and no row outside the table repeats them.
    Returns {K id: note} for the rows whose note is written in a column."""
    tables = {}
    for evidence in present:
        if evidence.get("tablo"):
            tables.setdefault(evidence["tablo"]["ad"], []).append(evidence)
    found = {}
    for members in tables.values():
        by_row = {}
        for evidence in members:
            by_row.setdefault(evidence["tablo"]["satir"], set()).add(evidence.get("not"))
        texts = {note for notes in by_row.values() for note in notes if note}
        ids = {r["id"] for r in members}
        outside = {r.get("not") for r in present if r["id"] not in ids}
        held = [next(iter(notes)) for notes in by_row.values() if len(notes) == 1]
        if (all(len(notes) == 1 for notes in by_row.values()) and len(texts) > 1 and max(len(t) for t in texts) <= COLUMN_NOTE_LIMIT
                and max(held.count(t) for t in texts) * 2 <= len(by_row) and not texts & outside):
            found.update({r["id"]: r["not"] for r in members if r.get("not")})
    return found


def table_lines(block, name, rows, in_column=None):
    in_column = in_column or {}
    present = [r for r in rows if r["durum"] == "var"]
    head = rows[0]["tablo"].get("baslik") or "Satır"
    order, columns, value_columns = [], [], []
    by_row = {}
    for evidence in rows:
        hint = evidence["tablo"]
        if hint["satir"] not in by_row:
            order.append(hint["satir"])
            by_row[hint["satir"]] = []
        by_row[hint["satir"]].append(evidence)
        for column in hint.get("hucreler") or {}:
            if column not in columns:
                columns.append(column)
        if hint.get("sutun") and hint["sutun"] not in value_columns:
            value_columns.append(hint["sutun"])
    units = {r.get("birim") for r in present if r["deger"] is not None}
    unit = units.pop() if len(units) == 1 else None
    labels = {r.get("etiket") for r in present}
    lines = ["", f"**{name}**", ""]
    meta = []
    if len(labels) == 1:
        meta.append(f"Etiket: [{ABBREVIATIONS.get(next(iter(labels)), '—')}]")
    if unit and not unit.startswith("USD") and unit != "%":
        meta.append(f"Birim: {unit}")
    elif unit and unit.startswith("USD"):
        meta.append(f"Birim: {unit}")
    if any(r.get("orneklem") is not None or r.get("kucuk_ornek") for r in present) and B.SAMPLE_RULES.get(block):
        meta.append(B.SAMPLE_RULES[block])
    scopes = {r.get("kapsam") for r in present}
    if len(scopes) == 1 and head != "Mahalle":
        meta.append(f"Kapsam: {next(iter(scopes))}")
    line = source_line(rows)
    if line:
        meta.append(line)
    lines += [" · ".join(meta), ""] if meta else []
    column_labels = {}
    if len(labels) > 1:
        for column in value_columns:
            found = {r.get("etiket") for r in present if r["tablo"].get("sutun") == column}
            column_labels[column] = f" [{ABBREVIATIONS.get(found.pop(), '—')}]" if len(found) == 1 else ""
    # one sample size per table row (the same for every value of the row) goes to its own "(n)" column instead of every cell
    samples = {key: {r.get("orneklem") for r in by_row[key] if r["durum"] == "var" and r["tablo"].get("sutun")} for key in order}
    row_sample = len(value_columns) > 1 and all(len(found) <= 1 for found in samples.values()) and any(None not in f and f for f in samples.values())
    noted = any(r["id"] in in_column for r in present)
    header = [head, *columns, *[f"{c}{column_labels.get(c, '')}" for c in value_columns], *(["(n)"] if row_sample else []),
              *(["Not"] if noted else []), "Kimlik"]
    lines += ["| " + " | ".join(cell(h) for h in header) + " |", "|" + "---|" * len(header)]
    quartiles = any(extras_of(r, "alt_ceyrek") for r in present)
    for key in order:
        members = by_row[key]
        texts = {}
        for evidence in members:
            for column, text in (evidence["tablo"].get("hucreler") or {}).items():
                texts.setdefault(column, text)
        values = {}
        for evidence in members:
            column = evidence["tablo"].get("sutun")
            if column:
                values[column] = value_cell(evidence, with_unit=unit is None, with_sample=not row_sample)
        sample = [value_text(next(iter(samples[key])))] if row_sample and samples[key] and None not in samples[key] else [""] if row_sample else []
        note = [next((in_column[r["id"]] for r in members if r["id"] in in_column), "")] if noted else []
        line_cells = [key, *[texts.get(c, "") for c in columns], *[values.get(c, "") for c in value_columns], *sample,
                      *[note_text(n) for n in note], ids_text(r["id"] for r in members)]
        lines.append("| " + " | ".join(cell(c) for c in line_cells) + " |")
    if quartiles:
        lines += ["", f"**{name} — çeyrekler (alt–üst)**", "", "| " + " | ".join(cell(h) for h in [head, *value_columns, "Kimlik"]) + " |",
                  "|" + "---|" * (len(value_columns) + 2)]
        for key in order:
            members = by_row[key]
            values = {evidence["tablo"].get("sutun"): quartile_cell(evidence) for evidence in members if evidence["tablo"].get("sutun")}
            lines.append("| " + " | ".join(cell(c) for c in [key, *[values.get(c, "") for c in value_columns], ids_text(r["id"] for r in members)]) + " |")
    return lines


def item_lines(evidence, note=None):
    """One line item; `note` is what is left of its note after the block head took the shared parts."""
    if evidence["durum"] != "var":
        lines = [f"- {evidence['id']} [—] {evidence['ifade']}: — (veri yok: {note_text(evidence['not'])})"]
        return lines
    line = f"- {evidence['id']} {tag(evidence)} {evidence['ifade']}"
    if evidence["deger"] not in (None, ""):
        line += f" — {unit_value(evidence['deger'], evidence.get('birim'))}"
    if (evidence.get("kaynak") or {}).get("durum") == "dogrulanamadi":
        line += " · **videoda kullanılmaz**"
    lines = [line]
    if evidence.get("celiski_notu"):
        lines.append(f"  - Çelişki: {note_text(evidence['celiski_notu'])}")
    if note:
        lines.append(f"  - Not: {note_text(note)}")
    if (evidence.get("kaynak") or {}).get("guven") == "ikincil":
        lines.append("  - İkincil kaynak")
    if evidence.get("orneklem") is not None:
        lines.append(f"  - Örnek büyüklüğü: {value_text(evidence['orneklem'])}")
    return lines


def block_lines(rows):
    block = rows[0]["blok"]
    lines = ["", f"### {BLOCK_TITLES.get(block, block)}", ""]
    usages = []
    for evidence in rows:
        note = evidence.get("kullanim_notu")
        if note and note not in [u for u, _ in usages]:
            usages.append((note, []))
        if note:
            next(ids for u, ids in usages if u == note).append(evidence["id"])
    if len(usages) == 1:
        lines.append(f"Kullanım notu: {usages[0][0]}")
    else:
        lines += [f"Kullanım notu ({ids_text(ids)}): {note}" for note, ids in usages]
    # notes are written once: every note of a table row, and every note several line items share, at the block head with its K ids;
    # a note of a single line item stays under it
    present = [r for r in rows if r["durum"] == "var"]
    in_column = column_notes(present)
    notes = []
    for evidence in present:
        if evidence.get("not") and evidence["id"] not in in_column and evidence["not"] not in [n for n, _ in notes]:
            notes.append((evidence["not"], []))
        if evidence.get("not") and evidence["id"] not in in_column:
            next(ids for n, ids in notes if n == evidence["not"]).append(evidence)
    head_notes = [(note, members) for note, members in notes if len(members) > 1 or members[0].get("tablo")]
    hoisted = {note for note, _ in head_notes}
    # a long sentence several line items repeat in otherwise different notes also goes to the head once; the rest stays under the item
    left = {r["id"]: sentences_of(r["not"]) for r in present if r.get("not") and r["not"] not in hoisted and not r.get("tablo")}
    holders = {}
    for key, parts in left.items():
        for part in dict.fromkeys(parts):
            holders.setdefault(part, []).append(key)
    shared = {part: keys for part, keys in holders.items() if len(keys) > 1 and len(part) >= SHORT_SENTENCE}
    by_members = {}
    for part, keys in shared.items():
        by_members.setdefault(tuple(keys), []).append(part)
    for keys, parts in by_members.items():
        text, members = " ".join(parts), [r for r in present if r["id"] in keys]
        same = next((item for item in head_notes if item[0] == text), None)
        if same:
            same[1].extend(members)
        else:
            head_notes.append((text, members))
    position = {r["id"]: index for index, r in enumerate(present)}
    for _, members in head_notes:
        members.sort(key=lambda r: position[r["id"]])
    head_notes.sort(key=lambda item: position[item[1][0]["id"]])
    remaining = {key: " ".join(p for p in parts if p not in shared) for key, parts in left.items()}
    if len(head_notes) == 1 and len(head_notes[0][1]) == len(present):
        lines.append(f"Not: {note_text(head_notes[0][0])}")
    else:
        lines += [f"Not ({ids_text(r['id'] for r in members)}): {note_text(note)}" for note, members in head_notes]
    done = set()
    for evidence in rows:
        hint = evidence.get("tablo")
        if hint:
            if hint["ad"] in done:
                continue
            done.add(hint["ad"])
            lines += table_lines(block, hint["ad"], [r for r in rows if (r.get("tablo") or {}).get("ad") == hint["ad"]], in_column)
            lines.append("")
        else:
            lines += item_lines(evidence, remaining.get(evidence["id"]))
    return lines


def groups_of(rows):
    groups = []
    for evidence in rows:
        if groups and groups[-1][0]["blok"] == evidence["blok"]:
            groups[-1].append(evidence)
        else:
            groups.append([evidence])
    return groups


def sources(pack):
    """Every source once (name, owner, address) with the K ranges it carries; several addresses of one source are not repeated."""
    found = {}
    for section in pack["sections"]:
        for evidence in section["rows"]:
            source = evidence.get("kaynak") or {}
            if evidence["durum"] != "var" or not source:
                continue
            key = (source.get("ad") or "kaynak", source.get("sahibi") or "")
            entry = found.setdefault(key, {"urls": [], "ids": []})
            if source.get("url") and source["url"] not in entry["urls"]:
                entry["urls"].append(source["url"])
            entry["ids"].append(evidence["id"])
    # one address is one source: rows that name the same page differently are listed under the first name
    merged, by_url = [], {}
    for (name, owner), entry in found.items():
        single = entry["urls"][0] if len(entry["urls"]) == 1 else None
        if single and single in by_url:
            by_url[single]["ids"] += entry["ids"]
            continue
        item = {"name": name, "owner": owner, "urls": entry["urls"], "ids": list(entry["ids"])}
        merged.append(item)
        if single:
            by_url[single] = item
    lines = []
    for item in merged:
        urls = item["urls"]
        url = urls[0] if len(urls) == 1 else f"satır başına {len(urls)} adres (tam pakette)" if urls else "—"
        lines.append(f"- {item['name']}{' — ' + item['owner'] if item['owner'] else ''} · {url} · {ids_text(item['ids'])}")
    return lines


def render(pack):
    t, header = pack["template"], pack["header"]
    lines = [f"# {t['title']} — yazar özeti", "", f"**Ana soru:** {t['question']}", ""]
    if pack["parameters"]:
        lines += ["**Parametreler:** " + ", ".join(f"{k} = {v['name']}" for k, v in pack["parameters"].items()), ""]
    lines += [f"- Üretim: {header['uretim_tarihi']} · üretim kimliği `{pack.get('id') or '—'}` · şablon {t['key']} (sürüm {t['version']})",
              f"- {SENTENCE}", f"- {header['not']}", f"- {header['birimler']}", ""]
    if pack.get("video"):
        from .video import markdown_lines
        lines += markdown_lines(pack["video"])
    lines += ["## Kaynakların son çekimi", ""]
    lines += [f"- {item['kaynak']}: {item['son_cekim']} · zamanı geldi: {'evet' if item['zamani_geldi'] else 'hayır'}" for item in header["kaynaklar"]] or ["- —"]
    lines += ["", "## Bilinen boşluklar", ""] + [f"- {gap}" for gap in header["bilinen_bosluklar"] or ["—"]]
    lines += ["", "## Yayından önce kontrol edilecek satırlar", ""]
    recheck = header.get("yayindan_once_kontrol") or []
    for item in recheck:
        line = f"- {item['kanit']} · {item['ifade']} · yeniden kontrol {item['yeniden_kontrol_tarihi'] or '—'}"
        if item.get("durum") == "celiskili":
            line += " · çelişkili (çelişki notu satırın altında)"
        lines.append(line)
    if not recheck:
        lines.append("- —")
    lines += ["", "## Kısaltmalar", "", "[KG] kaynak gerçeği · [BH] bizim hesabımız · [T] türetilmiş · [Y] yaklaşık · \"—\" veri yok · "
              "\"*\" küçük örnek · (n) örnek büyüklüğü (tablonun başında ne saydığı yazar) · boş hücre: tam pakette o hücre için satır yok. "
              "Tablolarda her satırın sonunda o satırın tam paketteki K kimlikleri yazar."]
    for section in pack["sections"]:
        lines += ["", f"## {section['title']}", "", f"**Soru:** {section['question']}"]
        for group in groups_of(section["rows"]):
            lines += block_lines(group)
    lines += ["", "## Kaynak listesi", "", "Her kaynak bir kez; satırın sonunda taşıdığı K kimlikleri.", ""] + sources(pack)
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip() + "\n"
