"""The video pack from the chosen candidate's content plan (GÖREV-14, Adım 6a; the manager's decision after GÖREV-13, decisions 1–2).

The pack's sections are the plan's sections in the same order: a section's title is the plan's `bolum`, its question `ne_anlatir`. Each
section holds the rows the plan cites and the whole blocks those rows belong to (the whole lodging table, not only its July cell: blocks
are the context). A block met again in a later section is written in full where it first appeared; later sections refer back to it.

Source packs: the candidate's inputs — the general pack (veri_ozeti_30a.md) and, when there was one, the neighborhood pack
(veri_ozeti_mahalle.md) — taken as they are now: the stored pack when it is up to date, otherwise produced again from the same template
and parameters (`fresh_pack`). Every cited row is found again by GÖREV-13's mapping (block plus reference row or statement, and value):
the same row, the same row with another value, or a row the pack no longer has; this is written beside it. Rows are numbered again
(K0001…) in the order they appear; each keeps where it came from (summary file, its K id there, the source pack).

Head: title, the viewer's question, the hook with its values, why it was proposed and the missing data; the known gaps (computed for the
video's region and its reference rows) and the rows to check again before publishing. The writer's summary and the number checklist are
made by the same machinery as every pack. "Yeni şablon gerekir" no longer stops the pack: it stays as information. The template packs
(first video, neighborhood guide) stay the data universe and the data summaries Claude reads.
"""
import json
from datetime import datetime, timezone

from . import blocks as B
from . import video as V
from .pack import FORMAT, NO_ADVICE, PackError, fingerprint, fresh_pack, known_gaps, numbers_of, recheck_before_publishing, stored_file

TEMPLATE_KEY = "video-plani"
GENERAL_FILE = "veri_ozeti_30a.md"


def source_packs(db, destination_id, profile, video, log=None):
    """{summary file: {"record", "pack", "rows", "produced"}} of the candidate's input packs, as they are now."""
    channel = getattr(profile, "CHANNEL", None) or {}
    wanted = {}
    for name, pack_id in ((video.get("analysis") or {}).get("paketler") or {}).items():
        with db.connect() as con:
            row = con.execute("SELECT template_key, params FROM evidence_packs WHERE id=?", (pack_id,)).fetchone()
        if row is not None:
            wanted[name] = (row["template_key"], json.loads(row["params"]))
    if GENERAL_FILE not in wanted and channel.get("general_template"):
        wanted[GENERAL_FILE] = (channel["general_template"], {})
    found = {}
    for name, (template_key, values) in wanted.items():
        record, reason = fresh_pack(db, destination_id, profile, template_key, values, log=log)
        path, _ = stored_file(db, record["id"], "json")
        pack = json.loads(path.read_text(encoding="utf-8"))
        found[name] = {"record": record, "pack": pack, "produced": reason,
                       "rows": [row for section in pack["sections"] for row in section["rows"]]}
    if not found:
        raise PackError("Videonun girdi paketleri bulunamadı; paket kurulamadı.")
    return found


def block_groups(source):
    """{row id: group key} and {group key: rows}: a block is the consecutive rows one block produced in one section of a source pack."""
    of_row, rows_of = {}, {}
    for section in source["pack"]["sections"]:
        index, previous = -1, None
        for row in section["rows"]:
            if row["blok"] != previous:
                index, previous = index + 1, row["blok"]
            key = (section["key"], index)
            of_row[row["id"]] = key
            rows_of.setdefault(key, []).append(row)
    return of_row, rows_of


def cited_entry(item, status, found, new_id=None, section_no=None):
    return {**item, "yeni_durum": status, "yeni_kimlik": new_id, "yeni_deger_metni": V.value_shown(found) if found else None,
            "bolum_no": section_no, "kaynak_kimlik": found["id"] if found else None}


def build(db, destination_id, profile, video, *, now=None, log=None):
    """The video pack object (same shape as a template pack, so it is stored, rendered and summarised by the same code)."""
    now = now or datetime.now(timezone.utc)
    today = now.date()
    analysis = video.get("analysis") or {}
    plan = analysis.get("icerik_plani") or []
    if not plan:
        raise PackError("Videonun içerik planı yok; paket kurulamadı.")
    sources = source_packs(db, destination_id, profile, video, log=log)
    groups = {name: block_groups(source) for name, source in sources.items()}
    included, new_ids, counter, sections = {}, {}, 0, []
    for number, part in enumerate(plan, 1):
        rows, cited, earlier = [], [], []
        for item in part.get("kanitlar") or []:
            source = sources.get(item.get("dosya"))
            status, found = V.match(item, source["rows"]) if source else (V.ABSENT, None)
            if found is None:
                cited.append(cited_entry(item, V.ABSENT, None))
                continue
            name = item["dosya"]
            key = (name, *groups[name][0][found["id"]])
            if key not in included:
                ids = []
                for row in groups[name][1][key[1:]]:
                    counter += 1
                    new_id = f"K{counter:04d}"
                    new_ids[(name, row["id"])] = new_id
                    ids.append(new_id)
                    rows.append({**row, "id": new_id, "bolum": f"b{number}",
                                 "kaynak_ozet": {"dosya": name, "kimlik": row["id"], "paket_id": sources[name]["record"]["id"]}})
                included[key] = {"bolum_no": number, "bolum": part.get("bolum"), "blok": found["blok"], "dosya": name, "kimlikler": ids}
            elif included[key]["bolum_no"] != number and all(e["kimlikler"] != included[key]["kimlikler"] for e in earlier):
                earlier.append(dict(included[key]))
            cited.append(cited_entry(item, status, found, new_ids[(name, found["id"])], included[key]["bolum_no"]))
        sections.append({"key": f"b{number}", "title": part.get("bolum") or f"{number}. bölüm", "question": part.get("ne_anlatir") or "",
                         "plan": cited, "onceki_bloklar": earlier, "rows": rows})
    marked = {e["yeni_kimlik"] for s in sections for e in s["plan"] if e["yeni_kimlik"]}
    for section in sections:
        for row in section["rows"]:
            if row["id"] in marked:
                row["plan_satiri"] = True
    rows_by_file = {name: source["rows"] for name, source in sources.items()}

    def mapped(item):
        source_rows = rows_by_file.get(item.get("dosya")) or []
        status, found = V.match(item, source_rows)
        new_id = new_ids.get((item.get("dosya"), found["id"])) if found else None
        return cited_entry(item, status, found, new_id)

    hook = analysis.get("kanca") or {}
    head = {"id": video["id"], "baslik_en": video["title_en"], "baslik_tr": video["title_tr"], "aile": video["family"], "bolge": video["region_name"],
            "izleyici_sorusu": analysis.get("izleyici_sorusu"), "neden_onerildi": analysis.get("neden_onerildi"),
            "kanca": {"metin": hook.get("metin"), "kanitlar": [mapped(i) for i in hook.get("kanitlar") or []]},
            "icerik_plani": [{"bolum": s["title"], "ne_anlatir": s["question"], "kanitlar": s["plan"]} for s in sections],
            "eksik_veri": list(analysis.get("eksik_veri") or []), "kapak_fikri": analysis.get("kapak_fikri"),
            "yeni_sablon_gerekir": bool(analysis.get("yeni_sablon_gerekir")) or not video.get("template_key"),
            "kullanici_duzenledi": bool(video.get("user_edited")), "plan_bolumlerde": True,
            "kaynak_paketler": [{"dosya": name, "paket_id": s["record"]["id"], "sablon": s["record"]["template_key"],
                                 "uretildi": s["produced"]} for name, s in sources.items()]}
    volatile = sorted({topic for s in sources.values() for topic in s["pack"]["template"].get("volatile_topics") or []})
    data = B.BlockData(db, destination_id, profile, today)
    focus = {video["region_id"]} if video.get("region_id") else None
    references = {(r.get("kaynak") or {}).get("referans") for s in sections for r in s["rows"]}
    runs = {(r.get("kaynak") or {}).get("cekim_kimligi") for s in sections for r in s["rows"]}
    seen, kaynaklar = set(), []
    for source in sources.values():
        for item in source["pack"]["header"].get("kaynaklar") or []:
            if item["cekim_kimligi"] in runs and item["cekim_kimligi"] not in seen:
                seen.add(item["cekim_kimligi"])
                kaynaklar.append(item)
    checklist = [entry for s in sections for e in s["rows"] for entry in numbers_of(e)]
    destination = db.destination(destination_id)
    return {"video": head,
            "format": FORMAT,
            "template": {"key": TEMPLATE_KEY, "version": 1, "title": video["title_en"],
                         "question": analysis.get("izleyici_sorusu") or video["title_tr"], "dimensions": [], "volatile_topics": volatile,
                         "file": None},
            "parameters": {},
            "destination": {"id": destination_id, "name": destination["name"] if destination else destination_id},
            "created_at": now.isoformat(timespec="seconds"),
            "header": {"uretim_tarihi": now.isoformat(timespec="seconds"), "kaynaklar": kaynaklar,
                       "bilinen_bosluklar": known_gaps(data, focus, references), "not": NO_ADVICE,
                       "yayindan_once_kontrol": recheck_before_publishing(sections, set(volatile)), "profil_karmasi": fingerprint(),
                       "birimler": "Değerler ABD birimleriyle (°F, inç, mil, USD) ve ABD sayı biçimiyle (binlik virgül, ondalık nokta) yazılır; "
                                   "°C, mm ve km karşılıkları yanında.",
                       "kurulus": "İçerik planından: bölümler planın bölümleridir; her bölümde planın gösterdiği satırlar ve bu satırların "
                                  "ait olduğu blokların tamamı. Bir blok ilk geçtiği bölümde tam yazılır, sonraki bölümler oraya gönderme yapar."},
            "sections": sections,
            "checklist": checklist,
            "counts": {"sections": len(sections), "evidence": sum(len(s["rows"]) for s in sections), "numbers": len(checklist),
                       "missing": sum(1 for s in sections for e in s["rows"] if e["durum"] == B.MISSING)}}


def plan_lines(section, summary=False):
    """The lines a plan section starts with: the rows the plan cites (with GÖREV-13's mapping) and the blocks written in earlier sections."""
    lines = []
    if section.get("plan") is None:
        return lines
    lines += ["", "**Planın gösterdiği satırlar:**", ""]
    for item in section["plan"]:
        origin = f"{item.get('dosya')} {item.get('kimlik')}"
        text = f"{item.get('ifade') or ''} — {item.get('deger_metni')}"
        if item["yeni_durum"] == V.ABSENT:
            lines.append(f"- ({origin}) {text} · **bu pakette yok** (kaynak paketin güncel hâlinde bu satır bulunamadı)")
            continue
        where = f"{item['yeni_kimlik']}" + (f" ({item['bolum_no']}. bölümde)" if item.get("bolum_no") and f"b{item['bolum_no']}" != section["key"] else "")
        if item["yeni_durum"] == V.CHANGED:
            lines.append(f"- {where} ← {origin}: {text} · **değeri değişti**: şimdi {item['yeni_deger_metni']}")
        else:
            lines.append(f"- {where} ← {origin}: {text}")
    if not section["plan"]:
        lines.append("- (planda bu bölüm için kanıt yok)")
    for block in section.get("onceki_bloklar") or []:
        ids = block["kimlikler"]
        span = ids[0] if len(ids) == 1 else f"{ids[0]}–{ids[-1]}"
        lines.append(f"- Blok {block['blok']} ({block['dosya']}) {block['bolum_no']}. bölümde ({block['bolum']}) tam yazıldı: {span}.")
    if section["rows"]:
        lines += ["", "Bu bölümde ilk kez geçen blokların tamamı aşağıda (planın gösterdiği satırlar “plan” işaretli)." if not summary
                  else "Bu bölümde ilk kez geçen bloklar aşağıda."]
    return lines
