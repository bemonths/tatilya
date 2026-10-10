"""The video text as data (GÖREV-15, Adım 6): parts, paragraphs and numbered sentences, close to Housing Atlas's `makale.json`
(TASARIM 21.2, `atlas/ai/schemas/makale.schema.json`) so that the Turkish correction screen can be carried over later.

`metin.json` (sema 1): `parcalar` — ids `giris`, `bolum-N`, `gecis-K`, `kapanis` (kinds giris, bolum, gecis, kapanis; a re-hook is a
transition part) — each with `paragraflar` (id `<part>-p<i>`) of `cumleler`: `no` (one sequence through the whole text), `en` (clean, no
evidence marks), `tr`, `kanitlar` (the ids of the sentence's marks) and `uyarilar` (`denetim` with its level and rule, `cevirmen`, `rakam`,
`son_okuma`); `terimler` (en, tr, aciklama); `surum_bilgisi` (number, time, tone file, name and SHA-256, the plan, every step's session
with model, effort, time and cost equivalent, word and sentence counts, the check's counts, the final reader's corrections).

Order of the parts: the introduction, then each section of the plan; after a section come its re-hook(s) and then the transition to the
next section (both transition parts); the closing last.

The final reader's corrections are applied by the program: the corrected sentence must keep every evidence mark of the old one (and may
only add ids the pack has); otherwise the correction is not applied and is kept as a warning on the sentence. A correction of several
sentences is split again; numbers are given again from 1.
"""
import re

from . import digits, marks

SCHEMA_VERSION = 1


def heading_of(part):
    return part.get("baslik") or {"giris": "Giriş", "kapanis": "Kapanış"}.get(part["tur"], "Geçiş")


def paragraphs_of(texts, part_id):
    out = []
    for text in texts or []:
        sentences = [{"no": 0, "en": en, "tr": "", "kanitlar": ids, "uyarilar": []} for en, ids in marks.split_marked(text)]
        if sentences:
            out.append({"kimlik": f"{part_id}-p{len(out) + 1}", "cumleler": sentences})
    return out


def assemble(plan, sections, merge, ends):
    """The document of a tone before numbering: introduction, sections (plan order), re-hooks and transitions, closing."""
    parts, transitions = [], 0

    def add(kind, part_id, title, number, texts):
        paragraphs = paragraphs_of(texts, part_id)
        if paragraphs:
            parts.append({"kimlik": part_id, "tur": kind, "baslik": title, "numara": number, "paragraflar": paragraphs})

    add("giris", "giris", "Giriş", None, ends.get("giris"))
    ordered = sorted(plan["bolumler"], key=lambda s: s["no"])
    for index, section in enumerate(ordered):
        number = section["no"]
        add("bolum", f"bolum-{number}", f"{number}. {section.get('ic_adi') or ''}".strip(), number, (sections.get(number) or {}).get("paragraflar"))
        for hook in (merge or {}).get("yeniden_kancalar") or []:
            if hook.get("bolumden_sonra") == number and (hook.get("metin") or "").strip():
                transitions += 1
                add("gecis", f"gecis-{transitions}", f"Yeniden kanca ({number}. bölümden sonra)", None, [hook["metin"]])
        if index + 1 < len(ordered):
            following = ordered[index + 1]["no"]
            for item in (merge or {}).get("gecisler") or []:
                if item.get("onceki_bolum") == number and item.get("sonraki_bolum") == following and (item.get("metin") or "").strip():
                    transitions += 1
                    add("gecis", f"gecis-{transitions}", f"Geçiş {number} → {following}", None, [item["metin"]])
    add("kapanis", "kapanis", "Kapanış", None, ends.get("kapanis"))
    document = {"sema": SCHEMA_VERSION, "parcalar": parts, "terimler": [], "surum_bilgisi": {}}
    return renumber(document)


def sentences(document):
    return [s for part in document["parcalar"] for p in part["paragraflar"] for s in p["cumleler"]]


def renumber(document):
    for number, sentence in enumerate(sentences(document), 1):
        sentence["no"] = number
    return document


def word_count(document):
    return sum(len(s["en"].split()) for s in sentences(document))


# ---- texts for the sessions ---------------------------------------------------------------------------------------------------------

def sections_text(plan, sections):
    """bolumler.md: the sections in order with their marks."""
    lines = ["# Bölümler", ""]
    for section in sorted(plan["bolumler"], key=lambda s: s["no"]):
        lines += [f"## {section['no']}. {section.get('ic_adi') or ''}".rstrip(), ""]
        for paragraph in (sections.get(section["no"]) or {}).get("paragraflar") or []:
            lines += [paragraph, ""]
    return "\n".join(lines).rstrip() + "\n"


def marked_text(document, numbered=False, title=None):
    """metin.md: the joined text with its marks; plain paragraphs (for the introduction and closing) or numbered sentences (final reader)."""
    lines = [f"# {title}", ""] if title else []
    for part in document["parcalar"]:
        lines += [f"## {heading_of(part)}", ""]
        for paragraph in part["paragraflar"]:
            if numbered:
                lines += [f"[{s['no']}] {marks.marked(s['en'], s['kanitlar'])}" for s in paragraph["cumleler"]]
            else:
                lines.append(" ".join(marks.marked(s["en"], s["kanitlar"]) for s in paragraph["cumleler"]))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def numbered_english(document):
    """The translator's input (Housing Atlas's form): part headings for context and `[no] sentence` lines, without marks."""
    blocks = []
    for part in document["parcalar"]:
        blocks.append(f"## {heading_of(part)}")
        for paragraph in part["paragraflar"]:
            blocks.append("\n".join(f"[{s['no']}] {s['en']}" for s in paragraph["cumleler"]))
    return "\n\n".join(blocks) + "\n"


def chunks(document, limit=6000):
    """Whole parts into translation chunks of at most `limit` English words (a part over the limit is its own chunk; Housing Atlas)."""
    out, words = [], 0
    for part in document["parcalar"]:
        size = sum(len(s["en"].split()) for p in part["paragraflar"] for s in p["cumleler"])
        if out and words + size <= limit:
            out[-1].append(part)
            words += size
        else:
            out.append([part])
            words = size
    return out


# ---- the final reader -------------------------------------------------------------------------------------------------------------

def apply_corrections(document, corrections, pack_ids=None):
    """Applies the final reader's corrections; returns (document, applied, refused). Numbers are given again afterwards."""
    by_number = {s["no"]: s for s in sentences(document)}
    applied, refused = [], []
    replacements = {}
    for item in corrections or []:
        number, new, reason = item.get("no"), (item.get("yeni") or "").strip(), (item.get("gerekce") or "").strip()
        sentence = by_number.get(number)
        if sentence is None or not new:
            refused.append({"no": number, "yeni": new, "gerekce": reason, "neden": "Bu numarada cümle yok." if sentence is None else "Yeni cümle boş."})
            continue
        pieces = marks.split_marked(new)
        new_ids = [i for _, ids in pieces for i in ids]
        lost = [i for i in sentence["kanitlar"] if i not in new_ids]
        unknown = [i for i in new_ids if pack_ids is not None and i not in pack_ids]
        if lost or unknown or not pieces:
            why = (f"kanıt işaretleri korunmadı ({', '.join(lost)})" if lost else
                   f"pakette olmayan kanıt işareti eklendi ({', '.join(unknown)})" if unknown else "cümle okunamadı")
            sentence["uyarilar"].append({"tur": "son_okuma", "metin": f"Son okuyucunun düzeltmesi uygulanmadı: {why}. Önerilen: “{new}”"
                                                                     + (f" Gerekçe: {reason}" if reason else "")})
            refused.append({"no": number, "yeni": new, "gerekce": reason, "neden": why})
            continue
        replacements[number] = [{"no": 0, "en": en, "tr": "", "kanitlar": ids, "uyarilar": list(sentence["uyarilar"])} for en, ids in pieces]
        applied.append({"no": number, "eski": marks.marked(sentence["en"], sentence["kanitlar"]), "yeni": new, "gerekce": reason,
                        "cumle_sayisi": len(pieces)})
    for part in document["parcalar"]:
        for paragraph in part["paragraflar"]:
            out = []
            for sentence in paragraph["cumleler"]:
                out += replacements.get(sentence["no"], [sentence])
            paragraph["cumleler"] = out
    return renumber(document), applied, refused


# ---- translation --------------------------------------------------------------------------------------------------------------------

class AnswerError(ValueError):
    """The translator's answer is not usable (Turkish reason); the chain asks once more with it."""


def check_translation(data, expected):
    """Every expected number exactly once with a Turkish sentence (Housing Atlas's `parse_translation` rules)."""
    items = data.get("cumleler")
    if not isinstance(items, list):
        raise AnswerError("Cevapta \"cumleler\" listesi yok.")
    seen, twice, empty = {}, set(), set()
    for item in items:
        number = item.get("no") if isinstance(item, dict) else None
        if not isinstance(number, int) or isinstance(number, bool):
            raise AnswerError(f"\"cumleler\" listesinde numarası geçersiz bir öğe var: {number!r}.")
        if number in seen:
            twice.add(number)
        text = " ".join(str(item.get("tr") or "").split())
        if not text:
            empty.add(number)
        seen[number] = item
    wanted = set(expected)
    problems = []
    missing, extra = sorted(wanted - set(seen)), sorted(set(seen) - wanted)
    if missing:
        problems.append(f"Şu numaraların çevirisi yok: {numbers_text(missing)}.")
    if extra:
        problems.append(f"Şu numaralar metinde yok: {numbers_text(extra)}.")
    if twice:
        problems.append(f"Şu numaralar birden çok kez geçiyor: {numbers_text(sorted(twice))}.")
    if empty - set(extra):
        problems.append(f"Şu numaraların Türkçesi boş: {numbers_text(sorted(empty - set(extra)))}.")
    if problems:
        raise AnswerError(" ".join(problems))
    return seen


def numbers_text(items):
    shown = ", ".join(str(n) for n in items[:20])
    return shown + (f" … (toplam {len(items)})" if len(items) > 20 else "")


def merge_terms(*lists):
    merged = {}
    for terms in lists:
        for term in terms or []:
            en = " ".join(str(term.get("en") or "").split())
            if not en:
                continue
            key = en.lower()
            if key not in merged:
                merged[key] = {"en": en, "tr": term.get("tr") or "", "aciklama": term.get("aciklama") or ""}
            else:
                merged[key]["tr"] = merged[key]["tr"] or term.get("tr") or ""
                merged[key]["aciklama"] = merged[key]["aciklama"] or term.get("aciklama") or ""
    return list(merged.values())


def apply_translation(document, answers, terms):
    """Turkish sentences, the translator's warnings and the terms; then the digits of both languages (a mismatch is a "rakam" warning)."""
    for sentence in sentences(document):
        item = answers[sentence["no"]]
        sentence["tr"] = " ".join(str(item.get("tr") or "").split())
        note = " ".join(str(item.get("uyari") or "").split())
        if note:
            sentence["uyarilar"].append({"tur": "cevirmen", "metin": note})
        result = digits.compare(sentence["en"], sentence["tr"])
        if not result.ok:
            sentence["uyarilar"].append({"tur": "rakam", "metin": result.message()})
    document["terimler"] = merge_terms(terms)
    return document


def attach_findings(document, findings):
    by_number = {s["no"]: s for s in sentences(document)}
    for item in findings:
        if item.get("no") in by_number:
            by_number[item["no"]]["uyarilar"].append({"tur": "denetim", "seviye": item["seviye"], "kural": item["kural"], "metin": item["metin"]})
    return document


# ---- files --------------------------------------------------------------------------------------------------------------------------

def render(document, title, lang="en", numbered=False):
    """metin_EN.md / metin_TR.md: the title, part headings and paragraphs (the Turkish one ends with the terms)."""
    lines = [f"# {title}", ""]
    for part in document["parcalar"]:
        lines += [f"## {heading_of(part)}", ""]
        for paragraph in part["paragraflar"]:
            if numbered:
                lines += [f"[{s['no']}] {s[lang]}" for s in paragraph["cumleler"]]
            else:
                lines.append(" ".join(s[lang] for s in paragraph["cumleler"]))
            lines.append("")
    if lang == "tr" and document.get("terimler"):
        lines += ["## Terimler", ""] + [f"- **{t['en']}** ({t['tr'] or t['en']}): {t['aciklama']}" for t in document["terimler"]] + [""]
    return "\n".join(lines).rstrip() + "\n"


def voice_text(document):
    """seslendirme_EN.txt: plain English for the voice — no numbers, no headings, no evidence marks; paragraphs apart."""
    paragraphs = [" ".join(s["en"] for s in p["cumleler"]) for part in document["parcalar"] for p in part["paragraflar"]]
    return "\n\n".join(paragraphs) + "\n"


def evidence_text(document, title):
    """metin_EN_kanitli.md: numbered English sentences with their marks (for checking)."""
    return marked_text(document, numbered=True, title=title)


def audit_text(document, findings, title, plan_notes=()):
    """denetim.md: the check's report (red and yellow findings by sentence, general findings, the plan's warnings)."""
    by_number = {s["no"]: s for s in sentences(document)}
    red = sum(f["seviye"] == "kirmizi" for f in findings)
    yellow = sum(f["seviye"] == "sari" for f in findings)
    lines = [f"# Program denetimi — {title}", "", f"- Kırmızı bulgu: {red}", f"- Sarı bulgu: {yellow}",
             f"- Kelime: {word_count(document):,}".replace(",", "."), f"- Cümle: {len(by_number)}", ""]
    for level, heading in (("kirmizi", "Kırmızı (bilgiyi yanlış söyler)"), ("sari", "Sarı (dikkat ister)")):
        items = [f for f in findings if f["seviye"] == level]
        lines += [f"## {heading}", ""]
        if not items:
            lines += ["Yok.", ""]
            continue
        for item in items:
            where = f"[{item['no']}] " if item.get("no") else ""
            sentence = by_number.get(item.get("no"))
            lines.append(f"- {where}{item['metin']}")
            if sentence:
                lines.append(f"  - Cümle: {marks.marked(sentence['en'], sentence['kanitlar'])}")
        lines.append("")
    other = [(s["no"], w) for s in by_number.values() for w in s["uyarilar"] if w["tur"] in ("cevirmen", "rakam", "son_okuma")]
    if other:
        lines += ["## Çevirmen, rakam ve son okuma uyarıları", ""]
        lines += [f"- [{no}] {({'cevirmen': 'Çevirmen', 'rakam': 'Rakam', 'son_okuma': 'Son okuma'})[w['tur']]}: {w['metin']}" for no, w in other]
        lines.append("")
    if plan_notes:
        lines += ["## Planın program denetimi", ""] + [f"- {note}" for note in plan_notes] + [""]
    return "\n".join(lines).rstrip() + "\n"


def first_sentence(text):
    match = re.match(r"(.+?[.!?])(\s|$)", (text or "").strip())
    return match.group(1) if match else (text or "").strip()
