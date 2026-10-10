"""The program's check of the video text (GÖREV-15, Adım 7; Ek O). It is never given to Claude.

Every written version is checked; the report is kept with the version. Findings are tied to sentences (their numbers) and shown next to
them: red ("kırmızı": says the information wrongly) or yellow ("sarı": needs attention). The check stops nobody: the version is saved and
the number of red findings is shown on the comparison screen.

Red, from the usage notes of the evidence blocks (`studio/evidence/blocks.py` `USAGE`; one rule per block, each with a test):
- distance (M13, `daily_needs`): "walking distance", "walkable", "a short walk", "minute walk", "minutes' walk", "minutes away",
  "minute drive", "minutes to drive";
- price (M11, `lodging_prices`): "a week costs", "a week in … costs", "costs about $… a week", "per week it costs";
- inventory (M10, `lodging_inventory`): "full inventory", "full list", "complete list", "every rental", "all the rentals",
  "there are … homes in";
- climate (M8, `climate`): "30A's climate", "the climate in 30A", "climate of 30A";
- restaurants (M12, `restaurants`): "best restaurant", "the best place to eat", "most popular", "cheapest restaurant";
- traffic (M9, `traffic`): "traffic jam", "gridlock", "bumper-to-bumper", "takes … minutes to get";
- source status (M9, `references`): a mark points at a reference row whose status is "doğrulanamadı";
- a mark points at an id the pack does not have;
- numbers: a sentence with a number has no mark, or the number holds against none of its marks' values (`numbers.py`).
Yellow:
- small sample: a mark points at a small-sample cell and the sentence names two neighborhoods (a comparison);
- source question: "no public beach access" without a source named in that sentence or the one before (a note for the final reader and
  the Kontrol step);
- voice: the phrases of `uyari_ifadeleri.txt` (case-insensitive, at word bounds; "I" only as the capital single word);
- length: the whole text below 2,000 or above 2,800 words (target 2,200–2,500); a section more than 25 % off its budget.

The plan's check (`plan_findings`): every evidence id of plan.json is in the pack (an unknown id sends the plan back to the planner once);
every concept placed in a section; two neighbouring sections do not open the same way; section budgets add up to 1,900–2,300.
"""
import re

from ..evidence.blocks import USAGE
from . import numbers as N

RED, YELLOW = "kirmizi", "sari"
LEVEL_WORDS = {RED: "kırmızı", YELLOW: "sarı"}
TARGET_WORDS, LOW_WORDS, HIGH_WORDS = (2200, 2500), 2000, 2800
BUDGET_DRIFT = 0.25
PLAN_BUDGET = (1900, 2300)
OPENINGS = {"rakam": "rakam", "sahne": "sahne", "soru": "soru", "gecmis": "geçmiş", "karsilastirma": "karşılaştırma", "diger": "diğer"}


def phrase(*patterns):
    return re.compile("|".join(patterns), re.I)


# (code, block, M document, title, pattern) — the red phrase rules of Ek O
RED_RULES = (
    ("mesafe", "daily_needs", "M13", "Mesafe: yürüme mesafesi ya da yol ve süre iddiası kullanılmaz",
     phrase(r"\bwalking distance\b", r"\bwalkable\b", r"\ba short walk\b", r"\bminutes?[- ]walk\b", r"\bminutes['’] walk\b",
            r"\bminutes? away\b", r"\bminutes?[- ]drive\b", r"\bminutes to drive\b")),
    ("fiyat", "lodging_prices", "M11", "Fiyat: “bir hafta $X tutar” denmez",
     phrase(r"\ba week costs\b", r"\ba week in\b[^.!?]{1,60}?\bcosts\b", r"\bcosts about \$[\d,.]+[^.!?]{0,30}?\ba week\b",
            r"\bper week it costs\b")),
    ("envanter", "lodging_inventory", "M10", "Envanter: “30A'da N ev var” ya da “tam liste” denmez",
     phrase(r"\bfull inventory\b", r"\bfull list\b", r"\bcomplete list\b", r"\bevery rental\b", r"\ball the rentals\b",
            r"\bthere are\b[^.!?]{1,40}?\bhomes in\b")),
    ("iklim", "climate", "M8", "İklim: “30A'nın iklimi” denmez",
     phrase(r"\b30A['’]s climate\b", r"\bthe climate in 30A\b", r"\bclimate of 30A\b")),
    ("restoran", "restaurants", "M12", "Restoran: “en iyi”, “en popüler”, “en ucuz” sıralamaları kullanılmaz",
     phrase(r"\bbest restaurants?\b", r"\bthe best places? to eat\b", r"\bmost popular\b", r"\bcheapest restaurants?\b")),
    ("trafik", "traffic", "M9", "Trafik: sıkışıklık ya da yolculuk süresi iddiası yapılmaz",
     phrase(r"\btraffic jams?\b", r"\bgridlock(?:ed)?\b", r"\bbumper[- ]to[- ]bumper\b", r"\btakes\b[^.!?]{0,30}?\bminutes to get\b")),
)
SOURCE_CUES = re.compile(r"\baccording to\b|\bcounty\b|\bwalton\b|\bvisit south walton\b|\blists?\b|\blisted\b|\bguide\b|\brecords?\b|"
                         r"\bmap\b|\bofficial\b|\bsays\b|\bshows?\b|\bdata\b|\bsurvey\b|\bfaq\b|\bwebsite\b|\bsite\b", re.I)
NO_PUBLIC = re.compile(r"\bno public beach access\b", re.I)


def words(text):
    return len(re.findall(r"[A-Za-z0-9$%’'.,-]+", text or "")) if text else 0


def count_words(text):
    return len((text or "").split())


def finding(level, rule, text, no=None, **extra):
    return {"no": no, "seviye": level, "kural": rule, "metin": text, **extra}


def warning_patterns(phrases):
    """(phrase, compiled) for each line of the warning phrases file: case-insensitive at word bounds; "I" only as the capital word."""
    found = []
    for raw in phrases:
        item = raw.strip()
        if not item or item.startswith("#"):
            continue
        if item == "I":
            found.append((item, re.compile(r"(?<![\w'’])I(?![\w'’])")))
        else:
            body = re.escape(item).replace("\\'", "['’]").replace("'", "['’]")
            found.append((item, re.compile(rf"(?<![\w'’]){body}(?![\w'’])", re.I)))
    return found


def read_phrases(path):
    try:
        return [line for line in path.read_text(encoding="utf-8-sig").splitlines()]
    except (OSError, AttributeError):
        return []


class Pack:
    """The video pack as the check needs it: rows by K id, the number list by K id."""

    def __init__(self, pack):
        self.rows = {row["id"]: row for section in pack.get("sections") or [] for row in section.get("rows") or []}
        self.checklist = {}
        for entry in pack.get("checklist") or []:
            self.checklist.setdefault(entry["kanit"], []).append(entry)

    def evidence(self, ids):
        return [N.evidence_of(self.rows.get(i), self.checklist.get(i, [])) for i in ids if i in self.rows]


def sentences_of(document):
    for part in document["parcalar"]:
        for paragraph in part["paragraflar"]:
            for sentence in paragraph["cumleler"]:
                yield part, sentence


def check(document, pack, *, regions=(), phrases=(), plan=None):
    """Findings of a written text (`document`: the version's metin.json) against its pack (the video pack's JSON)."""
    pack = pack if isinstance(pack, Pack) else Pack(pack)
    found = []
    region_names = [name for name in regions if name]
    voice = warning_patterns(phrases)
    previous_en = ""
    for part, sentence in sentences_of(document):
        no, en, ids = sentence["no"], sentence["en"], sentence.get("kanitlar") or []
        for code, block, doc, title, pattern in RED_RULES:
            match = pattern.search(en)
            if match:
                found.append(finding(RED, code, f"{title} (“{match.group(0)}”; {doc} kullanım notu).", no, blok=block))
        for evidence_id in ids:
            row = pack.rows.get(evidence_id)
            if row is None:
                found.append(finding(RED, "kimlik", f"Kanıt işareti pakette yok: {evidence_id}.", no))
                continue
            if (row.get("kaynak") or {}).get("durum") == "dogrulanamadi":
                found.append(finding(RED, "dogrulanamadi", f"Kanıt {evidence_id} “doğrulanamadı” durumunda bir referans satırı; "
                                                         f"{USAGE['references']['dogrulanamadi']}", no, blok="references"))
        mentions = N.mentions(en)
        if mentions and not ids:
            found.append(finding(RED, "rakam_isaretsiz", "Rakam taşıyan cümlenin kanıt işareti yok: "
                                                         + ", ".join(f"“{m.text}”" for m in mentions) + ".", no))
        elif mentions:
            evidences = pack.evidence(ids)
            wrong = [m for m in mentions if not N.matches(m, evidences)]
            if wrong:
                found.append(finding(RED, "rakam", "Rakam kanıtla tutmuyor: " + ", ".join(f"“{m.text}”" for m in wrong)
                                     + f" (işaret: {', '.join(ids)}).", no))
        small = [i for i in ids if (pack.rows.get(i) or {}).get("kucuk_ornek")]
        if small:
            named = [name for name in region_names if re.search(rf"\b{re.escape(name)}\b", en, re.I)]
            if len(named) >= 2:
                found.append(finding(YELLOW, "kucuk_ornek", f"Küçük örnekli hücreden ({', '.join(small)}) mahalle karşılaştırması: "
                                                            f"{', '.join(named)}.", no))
        if NO_PUBLIC.search(en) and not (SOURCE_CUES.search(en) or SOURCE_CUES.search(previous_en)):
            found.append(finding(YELLOW, "kaynak_sorusu", "“no public beach access” deniyor ama bu ya da önceki cümlede kaynak söylenmiyor "
                                                          "(son okuyucu ve Kontrol adımı için not).", no))
        for item, pattern in voice:
            if pattern.search(en):
                found.append(finding(YELLOW, "ses", f"Uyarı ifadesi: “{item}”.", no))
        previous_en = en
    found += length_findings(document, plan)
    return found


def part_words(document):
    return {part["kimlik"]: sum(count_words(s["en"]) for p in part["paragraflar"] for s in p["cumleler"]) for part in document["parcalar"]}


def length_findings(document, plan=None):
    counts = part_words(document)
    total = sum(counts.values())
    out = []
    if total < LOW_WORDS or total > HIGH_WORDS:
        out.append(finding(YELLOW, "uzunluk", f"Toplam {total:,} kelime; hedef {TARGET_WORDS[0]:,}–{TARGET_WORDS[1]:,} "
                                              f"({LOW_WORDS:,}'in altı ve {HIGH_WORDS:,}'in üstü uyarı).".replace(",", ".")))
    for section in (plan or {}).get("bolumler") or []:
        budget = section.get("kelime_butcesi") or 0
        got = counts.get(f"bolum-{section.get('no')}")
        if budget and got is not None and abs(got - budget) > BUDGET_DRIFT * budget:
            out.append(finding(YELLOW, "bolum_uzunlugu", f"{section.get('no')}. bölüm {got} kelime; bütçesi {budget} "
                                                          f"(%{round(100 * (got - budget) / budget):+d}).", None, bolum=section.get("no")))
    return out


def counts(findings):
    return {"kirmizi": sum(f["seviye"] == RED for f in findings), "sari": sum(f["seviye"] == YELLOW for f in findings)}


# ---- the plan ----------------------------------------------------------------------------------------------------------------------

def plan_findings(plan, pack_ids):
    """[(level "hata"|"uyari", text)] of plan.json: unknown ids are errors (the plan goes back), the rest warnings (recorded, the chain goes on)."""
    out = []
    sections = plan.get("bolumler") or []
    numbers = {s.get("no") for s in sections}
    unknown = sorted({i for s in sections for i in s.get("kanitlar") or [] if i not in pack_ids})
    if unknown:
        out.append(("hata", f"Planda pakette olmayan kanıt kimlikleri var: {', '.join(unknown)}."))
    for concept in plan.get("kavramlar") or []:
        if concept.get("bolum") not in numbers:
            out.append(("uyari", f"“{concept.get('kavram')}” kavramı bir bölüme yerleştirilmemiş (bölüm {concept.get('bolum')} planda yok)."))
    for first, second in zip(sections, sections[1:]):
        if first.get("acilis_bicimi") and first.get("acilis_bicimi") == second.get("acilis_bicimi"):
            kind = OPENINGS.get(first["acilis_bicimi"], first["acilis_bicimi"])
            out.append(("uyari", f"{first.get('no')}. ve {second.get('no')}. bölüm aynı biçimde açılıyor ({kind})."))
    total = sum(s.get("kelime_butcesi") or 0 for s in sections)
    if not PLAN_BUDGET[0] <= total <= PLAN_BUDGET[1]:
        out.append(("uyari", f"Bölüm bütçelerinin toplamı {total:,} kelime; {PLAN_BUDGET[0]:,}–{PLAN_BUDGET[1]:,} olmalı.".replace(",", ".")))
    for hook in plan.get("yeniden_kancalar") or []:
        if hook.get("bolumden_sonra") not in numbers:
            out.append(("uyari", f"Yeniden kanca planda olmayan bir bölümden sonra gösterilmiş ({hook.get('bolumden_sonra')})."))
    return out
