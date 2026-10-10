"""Numbers of the video text against their evidence (GÖREV-15, Adım 7; Ek O "Rakam ve yuvarlama").

Reading the text. Every number written with digits (separators "," and "." as in Housing Atlas's `digits.py`) and the common numbers
written with words: a number word with a scale ("seven thousand", "two and a half million"), a number word before "percent", and fractions
("half", "a third", "two thirds", "a quarter", "three quarters", "a fifth"). Plain small number words ("two neighborhoods") are not read.
Not numbers: digits joined to letters ("30A", "I-10", "4th", "1990s"), road numbers ("Highway 98", "US 98", "County Road 393", "CR 30A",
"Route 20"). Each number gets a kind from its own words:
- money: "$" before it ("$7,223", "$1.5 million", "$500k");
- percent: "%" or "percent" after it, or a fraction;
- temperature: "°F", "°", "degrees" after it ("Celsius" makes it °C);
- time: "3:30 p.m.", "15:30", "9 a.m.";
- year: four digits between 1900 and 2100 that are none of the above;
- count: followed by a count word (listings, homes, days, storms, hurricanes, restaurants, beaches, walkovers, stops, …);
- number: anything else (miles, inches, cars a day, …).
A number is "about" when one of the approximation words stands right before it (about, around, roughly, approximately, nearly, almost,
close to, some, just over, just under, more than, less than, over, under, an estimated, upward(s) of).

Matching (`matches`). The evidence values come from the number list of the pack (the main value, quartiles, sample, share, range,
conversion) and the row's own value; numbers inside their texts count too (a composite value like "5 / 15" or "06:00–21:45").
- money and numbers: the text number is the evidence value, or its spoken rounding: to the nearest 1 or 0.5 (below 100), 10, 50, 100, 500
  or 1,000, or two significant figures; with "about" also within ±3 %. $7,223 → "about $7,200" and "about $7,000" hold; "$7,500" does not.
- percent: within ±0.5 points; a fraction holds within ±3 points ("a third" for 33 %).
- temperature: within ±1 °F (or °C).
- counts (days, listings, storms …): exactly, unless "about" (then as numbers): 87 listings → "about 90 listings" holds, "90 listings" not.
- years and times: the same year or time appears in the evidence (its values or texts).
"""
import re
from dataclasses import dataclass

APPROX = ("an estimated", "upwards of", "upward of", "just over", "just under", "more than", "less than", "close to", "approximately",
          "roughly", "around", "nearly", "almost", "about", "some", "over", "under")
COUNT_WORDS = {"listing", "listings", "home", "homes", "house", "houses", "rental", "rentals", "day", "days", "night", "nights", "storm",
               "storms", "hurricane", "hurricanes", "restaurant", "restaurants", "beach", "beaches", "access", "accesses", "walkover",
               "walkovers", "stop", "stops", "visitor", "visitors", "people", "neighborhood", "neighborhoods", "town", "towns", "record",
               "records", "event", "events", "school", "schools", "district", "districts", "park", "parks", "pavilion", "pavilions",
               "point", "points", "spot", "spots", "space", "spaces", "time", "times", "company", "companies", "property", "properties",
               "unit", "units", "room", "rooms", "bedroom", "bedrooms", "store", "stores", "station", "stations", "season", "seasons",
               "member", "members", "rule", "rules", "sample", "samples", "home's", "dish", "dishes", "entree", "entrees", "entrées",
               "menu", "menus", "hotel", "hotels", "agency", "agencies", "condo", "condos", "cottage", "cottages", "villa", "villas"}
ROAD_WORDS = re.compile(r"(?:highway|hwy|route|rte|us|u\.s\.|county road|cr|sr|state road|interstate|i-|scenic highway|exit|road|"
                        r"suite|ste|unit|no\.|number|#)\s*$", re.I)
UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
         "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
         "a": 1, "an": 1, "a few": 3, "a couple": 2}
SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000, "billion": 1_000_000_000}
FRACTIONS = {"half": 50.0, "a half": 50.0, "one half": 50.0, "a third": 100 / 3, "one third": 100 / 3, "two thirds": 200 / 3,
             "two-thirds": 200 / 3, "a quarter": 25.0, "one quarter": 25.0, "three quarters": 75.0, "three-quarters": 75.0,
             "a fifth": 20.0, "one fifth": 20.0, "a tenth": 10.0, "one in three": 100 / 3, "one in four": 25.0, "one in five": 20.0,
             "one in ten": 10.0, "nine in ten": 90.0}
DIGITS = re.compile(r"(?<![\w.])(\$\s?)?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\w])")
SCALE_AFTER = re.compile(r"^\s*(million|billion|thousand|k\b|m\b|mn\b|bn\b)", re.I)
TIME = re.compile(r"(?<![\w:])(\d{1,2})(?::(\d{2}))?\s*(a\.m\.|p\.m\.|am\b|pm\b)|(?<![\w:])(\d{1,2}):(\d{2})(?![\w:])", re.I)
NUMBER_WORD = "|".join(sorted((re.escape(w) for w in UNITS if w not in ("a", "an", "a few", "a couple")), key=len, reverse=True))
WORDED = re.compile(rf"\b((?:{NUMBER_WORD})(?:[\s-]+(?:and\s+)?(?:a\s+half|{NUMBER_WORD}))*|a|an|a few|a couple of)\s+"
                    rf"(hundred|thousand|million|billion)\b(?:\s+(?:and\s+)?((?:{NUMBER_WORD})(?:[\s-]+(?:{NUMBER_WORD}))*)\s+"
                    rf"(?:hundred|thousand))?", re.I)
WORDED_PERCENT = re.compile(rf"\b((?:{NUMBER_WORD})(?:[\s-]+(?:{NUMBER_WORD}))*)\s+percent\b", re.I)
FRACTION = re.compile(r"\b(" + "|".join(sorted((re.escape(f) for f in FRACTIONS), key=len, reverse=True)) + r")\b(?=\s+(?:of|the|a|an|all|"
                      r"every|those|these|its|their|our|your|percent|as))", re.I)
MONEY_UNIT = re.compile(r"usd|\$|dolar", re.I)
COUNT_UNITS = ("örnek", "restoran", "gün", "erişim", "ilan", "fırtına", "kayıt", "durak", "ziyaretçi", "mahalle", "yer", "kez", "özel mülk",
               "oda-gece", "kasırga", "ev", "etkinlik")


@dataclass
class Mention:
    text: str
    value: float
    kind: str
    about: bool
    start: int
    minutes: int | None = None        # times: minutes after midnight


def _words_value(text):
    """'two and a half' → 2.5; 'twenty five' → 25; 'a' → 1."""
    words = re.split(r"[\s-]+", text.lower().strip())
    total, current, index = 0.0, 0.0, 0
    while index < len(words):
        word = words[index]
        if word == "and":
            index += 1
            continue
        if word == "a" and index + 1 < len(words) and words[index + 1] == "half":
            current += 0.5
            index += 2
            continue
        if word in UNITS:
            current += UNITS[word]
        index += 1
    return total + current


def _approx_before(text, start):
    before = text[max(0, start - 30):start].lower().rstrip()
    before = re.sub(r"\$$", "", before).rstrip()
    return any(before.endswith(word) and (len(before) == len(word) or not before[-len(word) - 1].isalnum()) for word in APPROX)


def _kind_after(text, end):
    after = text[end:end + 40]
    lowered = after.lower()
    if re.match(r"\s*(%|percent\b|per cent\b|percentage points?\b)", lowered):
        return "percent"
    if re.match(r"\s*(°\s*c\b|degrees? celsius|-degree celsius)", lowered):
        return "temperature_c"
    if re.match(r"\s*(°|degrees?\b|-degree\b|f\b)", lowered):
        return "temperature"
    word = re.match(r"\s*(?:[-–]?\s*)?(?:more\s+|fewer\s+|other\s+|new\s+|different\s+|separate\s+|public\s+|private\s+|full\s+|"
                    r"named\s+|official\s+|beach\s+|rental\s+|vacation\s+)?([a-zA-Zéè']+)", after)
    if word and word.group(1).lower() in COUNT_WORDS:
        return "count"
    return None


def mentions(text):
    """Every number of an English sentence (see the module's rules), in order."""
    text = text or ""
    found, taken = [], []

    def free(start, end):
        return not any(s < end and start < e for s, e in taken)

    for match in TIME.finditer(text):
        if match.group(4):
            hour, minute = int(match.group(4)), int(match.group(5))
            if hour > 23 or minute > 59:
                continue
        else:
            hour, minute, half = int(match.group(1)), int(match.group(2) or 0), match.group(3).lower().replace(".", "")
            if hour > 12:
                continue
            hour = (hour % 12) + (12 if half == "pm" else 0)
        taken.append(match.span())
        found.append(Mention(match.group(0), hour * 60 + minute, "time", False, match.start(), hour * 60 + minute))
    for match in WORDED.finditer(text):
        if not free(*match.span()):
            continue
        head = match.group(1).lower()
        base = {"a few": 3, "a couple of": 2}.get(head, None)
        base = base if base is not None else (_words_value(head) or 1)
        value = base * SCALES[match.group(2).lower()]
        if match.group(3):
            value += _words_value(match.group(3)) * 1000 if match.group(2).lower() == "million" else 0
        money = text[max(0, match.start() - 2):match.start()].strip().endswith("$") or re.match(r"\s*dollars?\b", text[match.end():], re.I)
        kind = "money" if money else (_kind_after(text, match.end()) or "number")
        taken.append(match.span())
        found.append(Mention(match.group(0), float(value), kind, _approx_before(text, match.start()), match.start()))
    for match in WORDED_PERCENT.finditer(text):
        if not free(*match.span()):
            continue
        taken.append(match.span())
        found.append(Mention(match.group(0), float(_words_value(match.group(1))), "percent", _approx_before(text, match.start()), match.start()))
    for match in FRACTION.finditer(text):
        if not free(*match.span()):
            continue
        taken.append(match.span())
        found.append(Mention(match.group(1), FRACTIONS[match.group(1).lower()], "fraction", _approx_before(text, match.start()), match.start()))
    for match in DIGITS.finditer(text):
        start, end = match.span()
        if not free(start, end):
            continue
        dollar = bool(match.group(1))
        number_start = match.start(2)
        if not dollar and ROAD_WORDS.search(text[max(0, number_start - 20):number_start]):
            continue
        if text[end:end + 1] in ("-",) and re.match(r"-[A-Za-z]", text[end:end + 2] or "") and not re.match(r"-(?:degree|day|night|year|"
                                                                                                           r"week|month|mile|foot|hour|minute)",
                                                                                                           text[end:end + 12], re.I):
            continue
        written = match.group(2) + (match.group(3) or "")
        value = float(written.replace(",", ""))
        scale = SCALE_AFTER.match(text[end:])
        if scale:
            word = scale.group(1).lower()
            value *= {"million": 1e6, "m": 1e6, "mn": 1e6, "billion": 1e9, "bn": 1e9, "thousand": 1e3, "k": 1e3}[word]
            end += scale.end()
        kind = "money" if dollar or re.match(r"\s*dollars?\b", text[end:], re.I) else _kind_after(text, end)
        if kind is None:
            if not match.group(3) and 1900 <= value <= 2100 and len(match.group(2)) == 4:
                kind = "year"
            else:
                kind = "number"
        taken.append((start, end))
        found.append(Mention(text[start:end], value, kind, _approx_before(text, start), start))
    return sorted(found, key=lambda m: m.start)


# ---- evidence values ----------------------------------------------------------------------------------------------------------------

def unit_kind(unit):
    unit = (unit or "").lower()
    if MONEY_UNIT.search(unit):
        return "money"
    if unit.startswith("%") or "yüzde" in unit:
        return "percent"
    if "°f" in unit:
        return "temperature"
    if "°c" in unit:
        return "temperature_c"
    if any(unit == word or unit.startswith(word) for word in COUNT_UNITS):
        return "count"
    return "number"


def numbers_in(value):
    """Numbers inside an evidence value or text (a composite "5 / 15", "06:00–21:45", "2016-10-25 (kabul)")."""
    text = str(value)
    times = [int(h) * 60 + int(m) for h, m in re.findall(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", text)]
    plain = re.sub(r"(?<!\d)\d{1,2}:\d{2}(?!\d)", " ", text)
    values = []
    for match in re.finditer(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.,])\d+(?:[.,]\d+)?", plain):
        written = match.group(0)
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", written):
            values.append(float(written.replace(",", "")))
        else:
            values.append(float(written.replace(",", ".")))
    return values, times


@dataclass
class Evidence:
    """What one evidence id allows: numeric values with their kinds, times (minutes), years, and the row's whole text."""
    values: list
    times: set
    text: str


def evidence_of(row, checklist_entries):
    values, times, texts = [], set(), []
    for entry in checklist_entries:
        kind = unit_kind(entry.get("birim"))
        if entry.get("tur") == "pay":
            kind = "percent"
        found, found_times = numbers_in(entry.get("deger"))
        values += [(v, kind) for v in found]
        times.update(found_times)
        if isinstance(entry.get("deger"), (int, float)) and not isinstance(entry.get("deger"), bool):
            values.append((float(entry["deger"]), kind))
    if row:
        if isinstance(row.get("deger"), (int, float)) and not isinstance(row.get("deger"), bool):
            values.append((float(row["deger"]), unit_kind(row.get("birim"))))
        for extra in row.get("ek_degerler") or []:
            if isinstance(extra.get("deger"), (int, float)) and not isinstance(extra.get("deger"), bool):
                values.append((float(extra["deger"]), "percent" if extra.get("tur") == "pay" else unit_kind(extra.get("birim"))))
        if isinstance(row.get("orneklem"), (int, float)):
            values.append((float(row["orneklem"]), "count"))
        source = row.get("kaynak") or {}
        table = row.get("tablo") or {}
        texts = [str(row.get(k) or "") for k in ("ifade", "ifade_en", "deger", "deger_ek", "alinti", "not", "kapsam")]
        texts += [str(source.get(k) or "") for k in ("ad", "belge_tarihi", "erisim_tarihi")]
        texts += [str(v) for v in (table.get("hucreler") or {}).values()] + [str(table.get("satir") or ""), str(table.get("sutun") or "")]
        for text in texts:
            found, found_times = numbers_in(text)
            values += [(v, "text") for v in found]
            times.update(found_times)
    return Evidence(values, times, " ".join(texts))


# ---- matching -------------------------------------------------------------------------------------------------------------------------

def spoken_roundings(value):
    """Roundings a speaker uses: nearest 1 and 0.5 (below 100), 0.1 (below 10), 10, 50, 100, 500, 1,000, and two significant figures."""
    out = {value}
    magnitude = abs(value)
    steps = [10, 50, 100, 500, 1000]
    if magnitude < 100:
        steps += [1, 0.5]
    if magnitude < 10:
        steps.append(0.1)
    for step in steps:
        out.add(round(value / step) * step)
    if magnitude >= 10:
        digits = len(str(int(magnitude))) - 2
        out.add(round(value, -digits))
    return out


def close(a, b, tolerance=1e-6):
    return abs(a - b) <= tolerance * max(1.0, abs(b))


def holds(mention, value, value_kind):
    """Does the text number stand for this evidence value (rules in the module's text)?"""
    if mention.kind == "fraction":
        return value_kind in ("percent", "text", "number") and abs(mention.value - value) <= 3.0
    if mention.kind == "percent":
        return value_kind in ("percent", "text", "number") and abs(mention.value - value) <= 0.5
    if mention.kind in ("temperature", "temperature_c"):
        wanted = ("temperature", "text", "number") if mention.kind == "temperature" else ("temperature_c", "text", "number")
        return value_kind in wanted and abs(mention.value - value) <= 1.0
    if mention.kind == "count" and not mention.about:
        return close(mention.value, value)
    if mention.kind == "money" and value_kind in ("percent", "temperature", "temperature_c"):
        return False
    if any(close(mention.value, rounded) for rounded in spoken_roundings(value)):
        return True
    return mention.about and value and abs(mention.value - value) <= 0.03 * abs(value)


def matches(mention, evidences):
    """Does the mention hold against any of the cited evidence (values, times, years in the texts)?"""
    for evidence in evidences:
        if mention.kind == "time":
            if mention.minutes in evidence.times:
                return True
            continue
        if mention.kind == "year":
            if str(int(mention.value)) in evidence.text or any(close(mention.value, v) for v, _ in evidence.values):
                return True
            continue
        if any(holds(mention, value, kind) for value, kind in evidence.values):
            return True
    return False
