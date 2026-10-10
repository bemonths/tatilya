"""The video a pack is produced for (GÖREV-13): the chosen title's analysis written at the head of the pack and of the writer's summary.

K identifiers belong to one pack. The title proposal cited rows of the packs whose summaries it read; the video record keeps each of those
rows with its value and the id of its pack. When the video's own pack is produced, every cited row is looked up in it by its source row (the
block and the reference row, or the statement itself) and its value: the same row with the same value gets its new K id beside it; a row whose
value changed, or that the new pack does not hold, is said so plainly.
"""
SAME, CHANGED, ABSENT = "ayni", "deger_farkli", "yok"


def value_shown(row):
    from .pack import value_text
    if row.get("durum") != "var":
        return "veri yok"
    value = row.get("deger")
    if value in (None, ""):
        return "—"
    return f"{value_text(value)}{' ' + row['birim'] if row.get('birim') else ''}"


def row_key(row):
    """What makes two rows of different packs the same source row: the block plus the reference row id, or the block plus the statement."""
    reference = (row.get("kaynak") or {}).get("referans") if isinstance(row.get("kaynak"), dict) else row.get("referans")
    return row.get("blok"), reference or row.get("ifade")


def cited(row, *, dosya, pack_id):
    """A cited row as the video record keeps it (with its value and the pack it came from)."""
    return {"dosya": dosya, "kimlik": row["id"], "paket_id": pack_id, "blok": row.get("blok"), "referans": (row.get("kaynak") or {}).get("referans"),
            "ifade": row.get("ifade"), "deger": row.get("deger"), "birim": row.get("birim"), "deger_metni": value_shown(row),
            "etiket": row.get("etiket"), "durum": row.get("durum")}


def match(item, rows):
    """The cited row in the new pack: (status, new row or None)."""
    key = row_key(item)
    found = next((r for r in rows if row_key(r) == key), None)
    if found is None:
        return ABSENT, None
    same = found.get("durum") == item.get("durum") and found.get("deger") == item.get("deger") and found.get("birim") == item.get("birim")
    return (SAME if same else CHANGED), found


def mapped(item, rows):
    status, found = match(item, rows)
    return {**item, "yeni_durum": status, "yeni_kimlik": found["id"] if found else None, "yeni_deger_metni": value_shown(found) if found else None}


def block(video, sections):
    """The video block of a pack: title, question, hook, why proposed and content plan, every cited row mapped onto this pack's rows."""
    analysis = video["analysis"]
    rows = [r for s in sections for r in s["rows"]]
    hook = analysis.get("kanca") or {}
    return {"id": video["id"], "baslik_en": video["title_en"], "baslik_tr": video["title_tr"], "aile": video["family"],
            "bolge": video["region_name"], "izleyici_sorusu": analysis.get("izleyici_sorusu"), "neden_onerildi": analysis.get("neden_onerildi"),
            "kanca": {"metin": hook.get("metin"), "kanitlar": [mapped(i, rows) for i in hook.get("kanitlar") or []]},
            "icerik_plani": [{"bolum": p.get("bolum"), "ne_anlatir": p.get("ne_anlatir"), "kanitlar": [mapped(i, rows) for i in p.get("kanitlar") or []]}
                             for p in analysis.get("icerik_plani") or []],
            "eksik_veri": list(analysis.get("eksik_veri") or []), "kapak_fikri": analysis.get("kapak_fikri"),
            "kaynak_paketler": sorted({i["paket_id"] for i in [*(hook.get("kanitlar") or []),
                                                                *[k for p in analysis.get("icerik_plani") or [] for k in p.get("kanitlar") or []]]
                                       if i.get("paket_id")})}


def evidence_line(item):
    where = f"{item['kimlik']} (paket {str(item.get('paket_id') or '—')[:8]}, {item['dosya']})"
    text = f"{where}: {item.get('ifade') or ''} — {item.get('deger_metni')}"
    if item.get("yeni_durum") == SAME:
        return f"{text} · bu pakette {item['yeni_kimlik']}"
    if item.get("yeni_durum") == CHANGED:
        return f"{text} · bu pakette {item['yeni_kimlik']}, değeri farklı: {item.get('yeni_deger_metni')}"
    return f"{text} · bu pakette yok"


def markdown_lines(video):
    """The video block in Markdown (the pack and the writer's summary start with it)."""
    lines = ["## Video", "", f"**{video['baslik_en']}**", "", f"- Türkçe karşılığı: {video['baslik_tr']}", f"- Bölge: {video['bolge']} · İçerik ailesi: "
             f"{video['aile']}", f"- İzleyicinin sorusu: {video.get('izleyici_sorusu') or '—'}", f"- Neden önerildi: {video.get('neden_onerildi') or '—'}",
             f"- Kapak fikri: {video.get('kapak_fikri') or '—'}", "",
             "Başlık önerisindeki kimlikler önerinin okuduğu paketlere aittir; her birinin yanında bu paketteki karşılığı yazar.", "",
             "### Kanca", "", video["kanca"].get("metin") or "—", ""]
    lines += [f"- {evidence_line(i)}" for i in video["kanca"]["kanitlar"]] or ["- —"]
    lines += ["", "### İçerik planı", ""]
    for number, part in enumerate(video["icerik_plani"], 1):
        lines += [f"{number}. **{part['bolum']}** — {part['ne_anlatir']}"]
        lines += [f"   - {evidence_line(i)}" for i in part["kanitlar"]] or ["   - —"]
    lines += ["", "### Eksik veri", ""] + ([f"- {m}" for m in video["eksik_veri"]] or ["- —"])
    return lines + [""]

