"""Cümle bölme (GÖREV-15, Adım 6): The Housing Atlas Stüdyo'nun `atlas/article/split.py`'si (MS1, 11 Ekim 2026) aynen taşındı; davranışı
değiştirilmedi, testleri `tests/test_text_split.py`. Video metninde parçaları program kurar; `parse_article` taşınan testlerle
birlikte durur. Kanıt işaretlerinin cümleye bağlanması ayrı modülde (`studio/text/marks.py`).

İçe aktarılan metnin parçalara, paragraflara ve cümlelere bölünmesi (MS1 Görev 2).

PARÇA BAŞLIKLARI
Markdown başlık satırı (`#` … `######`, ardından boşluk ve metin) bir parça başlatır. Başlığın metni parçanın başlığı
(`baslik`) olarak aynen saklanır ("10 · Lee County"); parçanın türü başlığın metninden çıkar:
- giriş (`giris`): ilk kelimesi "Intro", "Introduction", "Opening", "Giriş" olan başlık ("## Intro").
- kapanış (`kapanis`): ilk kelimesi "Closing", "Outro", "Conclusion", "Ending", "Kapanış" olan başlık ("## Closing").
- madde (`madde`, `numara` ile): 1–3 basamaklı bir sayıyla başlayan başlık; sayıdan sonra hiçbir şey, bir ayraç
  (`.`, `)`, `:`, `·`, `•`, `|`, `-`, `–`, `—`) ya da boşluk gelir: "## 1", "## 10.", "## 10. Lee County",
  "## 10 · Lee County", "## 10 Lee County", "## No. 3", "## Number 3", "## #3".
- geçiş (`gecis`): öbür bütün başlıklar ("## Mid-video hook").
Kimlikler: `giris`, `madde-<numara>`, `gecis-<sıra>` (1, 2, …), `kapanis`; aynı kimlik ikinci kez gelirse `-2`, `-3`
eklenir ("madde-3-2"). İlk başlıktan önceki metin, metinde giriş başlığı yoksa başlıksız bir giriş parçası (`baslik`
""), varsa başlıksız bir geçiş parçası olur. Altında hiç cümle olmayan başlık atılır (ör. en üstteki "# Başlık";
`ParsedArticle.dropped`). Metinde hiç başlık yoksa bütün metin tek parçadır: kimlik ve tür `metin`, başlık "".
Paragraflar boş satırlarla ayrılır; paragrafın içindeki satır sonları boşluk olur; yatay çizgiler (`---`, `***`)
paragraf ayırır. Paragraf kimliği `<parça>-p<sıra>` ("madde-10-p2").

CÜMLE BÖLME (kurallı; `split_sentences(metin, "en" | "tr")`)
Aday sınır: `.`, `!`, `?` (ya da "?!" gibi bir dizi), ardından isteğe bağlı kapanış tırnağı ya da parantez
(`" ' ” ’ ) ] »`), ardından boşluk ve küçük harfle başlamayan bir kelime (açılış tırnağı ve parantezi atlanır). Şunlarda
bölünmez:
- üç nokta ("..." ya da "…"): hiçbir zaman sınır değildir;
- boşluksuz nokta: ondalık ve para ("$1.5 million", "3.2%", "170.000"), alan adı ("Realtor.com"), "U.S.-based";
- çift tırnak içi (`"…"`, `“…”`, `«…»`): tırnak kapanmadan sınır olmaz; tırnağı kapatan noktadan sonra sınır olabilir.
  Eşi olmayan tırnak hesaba katılmaz (cümle bölme bütün paragrafta durmasın);
- liste işareti: cümlenin başındaki "1." gibi tek sayı;
- tek büyük harfle kısaltılmış ad ("Joel B. Berner"; İngilizcede "I" hariç);
- kısaltmalar. Ünvanlar her zaman (`TITLES_EN`: Mr., Mrs., Dr., St., Mt., Prof., Gov. …; Türkçede `TITLES_TR`: Dr.,
  Prof., Doç., Av., Sn. …); öbür kısaltmalar (`ABBREVIATIONS_EN`: approx., est., etc., vs., Inc., Jr., Ave., sq.,
  ft., No., Jan. … Dec.; noktalı kısaltmalar "U.S.", "a.m.", "e.g."; Türkçede ayrıca vb., vs., vd., örn., bkz., yak.)
  yalnız ardından bir cümle başlangıcı kelimesi gelirse (`STARTERS_EN` / `STARTERS_TR`: The, This, It, But … / Bu, Ve,
  Ama, Şimdi …) sınırdır: "in the U.S. The next year" bölünür, "U.S. Census Bureau" bölünmez;
- Türkçede 1–3 basamaklı sayıdan sonraki nokta sıra sayısıdır ("10. Lee County", "1. Dünya Savaşı").
Metin önce boşlukları tek boşluğa indirilerek düzenlenir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

Language = Literal["en", "tr"]

TERMINALS = ".!?"
ELLIPSIS = "…"
CLOSERS = "\"'”’)]»"
OPENERS = "\"'“‘([«"

TITLES_EN = frozenset({"mr", "mrs", "ms", "dr", "st", "mt", "prof", "gen", "gov", "sen", "rep", "capt", "lt", "col",
                       "sgt", "rev", "hon", "pres", "supt", "messrs", "mme", "mlle"})
ABBREVIATIONS_EN = frozenset({
    "jr", "sr", "inc", "co", "corp", "ltd", "bros", "etc", "approx", "est", "vs", "dept", "univ", "assn", "ave",
    "blvd", "rd", "hwy", "apt", "sq", "ft", "no", "nos", "fig", "vol", "jan", "feb", "mar", "apr", "jun", "jul", "aug",
    "sep", "sept", "oct", "nov", "dec", "mon", "tue", "tues", "wed", "thu", "thur", "thurs", "fri", "sat", "sun",
    "min", "max", "avg", "pct", "yr", "yrs", "mo", "mos", "ste", "bldg", "cir", "ct", "ln", "pkwy", "pl", "dist",
})
TITLES_TR = frozenset({"dr", "prof", "doç", "doc", "av", "sn", "alb", "yrd", "öğr", "ogr", "mr", "mrs", "ms", "st",
                       "mt", "ft", "gen", "gov"})
ABBREVIATIONS_TR = frozenset({"vb", "vs", "vd", "örn", "orn", "bkz", "yak", "krş", "s", "sf", "tel", "cad", "sok",
                              "mah", "apt", "no", "yy", "bl", "böl", "inc", "co", "corp", "ltd", "jr", "sr", "approx",
                              "etc", "sq", "ave", "blvd"}) | ABBREVIATIONS_EN

STARTERS_EN = frozenset("""
The This That These Those It Its It's He She We They I You Our Their His Her My Your A An And But So Yet Or Nor Now
Then There Here In On At For From With By As If When While What Why How Who Which Where Today Still Even Also After
Before Since One Another Some Most Many All Of To Not No Prices Homes Home Houses House Every Each Over Under Just
Only Last Next First Second Third Back Across Meanwhile However Instead Overall Otherwise Let Let's That's There's
Here's We're They're You're It'll We'll
""".split())
STARTERS_TR = frozenset("""
Bu Şu O Bir Ve Ama Fakat Ancak Yine Şimdi Sonra Bunun Bunu Buna Burada Orada Evet Hayır Peki Yani Kısacası Ayrıca
Üstelik Böylece Çünkü Eğer Hem Ne Neden Nasıl Kim Hangi Her Hiç En Daha İlk Son Bugün Dün Yarın Geçen Bazı Birçok Tüm
Bütün Biz Ben Siz Onlar Sen Bunlar Şunlar Oysa Gerçi Hatta Dahası Sonuçta Özetle Kaldı Diğer Öte Gelelim Geçelim
Fiyatlar Fiyat Evler Ev
""".split()) | STARTERS_EN

_MULTI_DOT = re.compile(r"(?:[A-Za-z]\.)+[A-Za-z]")
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_RULE = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")
_NUMBERED = re.compile(
    r"^(?:no\.?\s*|number\s+|#\s*|madde\s+)?(\d{1,3})(?:\s*$|\s*[.):·•|\-–—]\s*(.*)$|\s+(.*)$)", re.IGNORECASE)
INTRO_WORDS = frozenset({"intro", "introduction", "opening", "giriş", "giris"})
CLOSING_WORDS = frozenset({"closing", "outro", "conclusion", "ending", "kapanış", "kapanis"})
_FIRST_WORD = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*", re.UNICODE)


# ---------------------------------------------------------------- cümle bölme

def _quote_spans(text: str) -> list[tuple[int, int]]:
    """Çift tırnakların (açılış, kapanış) konumları. Düz tırnak (") sırayla eşlenir, eşi olmayan sonuncusu sayılmaz;
    “…” ve «…» kendi eşleriyle."""
    spans: list[tuple[int, int]] = []
    straight = [i for i, ch in enumerate(text) if ch == '"']
    spans += [(straight[k], straight[k + 1]) for k in range(0, len(straight) - 1, 2)]
    for opener, closer in (("“", "”"), ("«", "»")):
        start: int | None = None
        for i, ch in enumerate(text):
            if ch == opener and start is None:
                start = i
            elif ch == closer and start is not None:
                spans.append((start, i))
                start = None
    return spans


def _token_before(text: str, end: int) -> str:
    """`end`'deki noktadan önceki kelime (harf, rakam, nokta, virgül): "U.S", "approx", "170,000"."""
    start = end
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] in ".,"):
        start -= 1
    return text[start:end].strip(".,")


def _next_word(text: str, start: int) -> str:
    match = _FIRST_WORD.match(text, start)
    if not match:
        return ""
    word = match.group(0)
    end = match.end()
    if end < len(text) and text[end] in "'’" and end + 1 < len(text) and text[end + 1].isalpha():
        tail = _FIRST_WORD.match(text, end + 1)
        if tail:
            word = f"{word}'{tail.group(0)}"
    return word


def _period_allows_split(token: str, sentence_so_far: str, next_word: str, lang: Language) -> bool:
    """Noktadan sonra bölünür mü (kısaltma, baş harf, sıra sayısı ve liste işareti kuralları)."""
    if not token:
        return True
    lower = token.lower()
    starters = STARTERS_TR if lang == "tr" else STARTERS_EN
    if token.isdigit():
        if sentence_so_far.strip().strip("([") == token:
            return False  # liste işareti: "1. …"
        if lang == "tr" and len(token) <= 3:
            return False  # Türkçe sıra sayısı: "10. Lee County"
        return True
    if _MULTI_DOT.fullmatch(token):
        return next_word in starters  # "U.S." "a.m." "e.g."
    if len(token) == 1 and token.isalpha() and token.isupper():
        return lang == "en" and token == "I"  # baş harf: "Joel B. Berner"
    titles = TITLES_TR if lang == "tr" else TITLES_EN
    abbreviations = ABBREVIATIONS_TR if lang == "tr" else ABBREVIATIONS_EN
    if lower in titles:
        return False
    if lower in abbreviations:
        return next_word in starters
    return True


def split_sentences(text: str, lang: Language = "en") -> list[str]:
    """Paragrafı cümlelere böler (kurallar modülün açıklamasında). Boş metin → []."""
    text = " ".join((text or "").split())
    if not text:
        return []
    spans = _quote_spans(text)
    sentences: list[str] = []
    start = 0
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if ch == ELLIPSIS:
            i += 1
            continue
        if ch not in TERMINALS:
            i += 1
            continue
        j = i
        while j + 1 < n and text[j + 1] in TERMINALS:
            j += 1
        run = text[i:j + 1]
        if ".." in run or (i > 0 and text[i - 1] == ELLIPSIS):
            i = j + 1
            continue  # üç nokta
        k = j + 1
        while k < n and text[k] in CLOSERS:
            k += 1
        inside = next(((o, c) for o, c in spans if o < i < c), None)
        if inside is not None and not (j < inside[1] < k):
            i = k
            continue  # tırnak içi
        if k >= n:
            break
        if text[k] != " ":
            i = k
            continue  # boşluksuz: ondalık, alan adı …
        m = k + 1
        while m < n and text[m] in OPENERS:
            m += 1
        if m >= n or text[m].islower():
            i = k
            continue
        if run == ".":
            token = _token_before(text, i)
            if not _period_allows_split(token, text[start:i], _next_word(text, m), lang):
                i = k
                continue
        sentences.append(text[start:k].strip())
        start = k + 1
        i = k + 1
    rest = text[start:].strip()
    if rest:
        sentences.append(rest)
    return sentences


def split_en(text: str) -> list[str]:
    return split_sentences(text, "en")


def split_tr(text: str) -> list[str]:
    return split_sentences(text, "tr")


# ---------------------------------------------------------------- parçalar ve paragraflar

@dataclass
class ParsedPart:
    kimlik: str
    tur: str
    baslik: str
    numara: int | None
    paragraphs: list[list[str]] = field(default_factory=list)  # paragraf → İngilizce cümleler

    @property
    def sentence_count(self) -> int:
        return sum(len(p) for p in self.paragraphs)

    def summary(self) -> dict:
        return {"kimlik": self.kimlik, "tur": self.tur, "baslik": self.baslik, "numara": self.numara,
                "paragraf_sayisi": len(self.paragraphs), "cumle_sayisi": self.sentence_count}


@dataclass
class ParsedArticle:
    parts: list[ParsedPart]
    dropped: list[str] = field(default_factory=list)  # altında cümle olmadığı için atılan başlıklar

    @property
    def sentence_count(self) -> int:
        return sum(p.sentence_count for p in self.parts)

    @property
    def word_count(self) -> int:
        return sum(len(s.split()) for p in self.parts for para in p.paragraphs for s in para)


def classify_heading(title: str) -> tuple[str, int | None]:
    """Başlığın türü ve madde numarası: ("giris", None), ("madde", 10), ("kapanis", None), ("gecis", None)."""
    clean = title.strip().strip("*_").strip()
    numbered = _NUMBERED.match(clean)
    if numbered:
        return "madde", int(numbered.group(1))
    first = _FIRST_WORD.search(clean)
    word = first.group(0).lower() if first else ""
    if word in INTRO_WORDS or clean.lower() == "cold open":
        return "giris", None
    if word in CLOSING_WORDS or clean.lower().startswith("wrap-up") or clean.lower().startswith("wrap up"):
        return "kapanis", None
    return "gecis", None


def _paragraphs(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if not line.strip() or _RULE.match(line):
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line.strip())
    if current:
        blocks.append(current)
    out = []
    for block in blocks:
        sentences = split_en(" ".join(block))
        if sentences:
            out.append(sentences)
    return out


def parse_article(text: str) -> ParsedArticle:
    """Metni parçalara, paragraflara ve İngilizce cümlelere böler (kurallar modülün açıklamasında)."""
    text = (text or "").replace("﻿", "").replace("\r\n", "\n").replace("\r", "\n")
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in text.split("\n"):
        heading = _HEADING.match(line)
        if heading and heading.group(2).strip():
            sections.append((heading.group(2).strip(), []))
        else:
            sections[-1][1].append(line)
    has_headings = len(sections) > 1
    if not has_headings:
        part = ParsedPart("metin", "metin", "", None, _paragraphs(sections[0][1]))
        return ParsedArticle([part] if part.paragraphs else [])
    kinds = [classify_heading(title) for title, _ in sections[1:] if title is not None]
    has_intro = any(kind == "giris" for kind, _ in kinds)
    parts: list[ParsedPart] = []
    dropped: list[str] = []
    used: dict[str, int] = {}
    transitions = 0

    def unique(base: str) -> str:
        used[base] = used.get(base, 0) + 1
        return base if used[base] == 1 else f"{base}-{used[base]}"

    for title, lines in sections:
        paragraphs = _paragraphs(lines)
        if title is None:
            if not paragraphs:
                continue
            kind, number = ("gecis", None) if has_intro else ("giris", None)
            title = ""
        else:
            kind, number = classify_heading(title)
            if not paragraphs:
                dropped.append(title)
                continue
        if kind == "madde":
            base = f"madde-{number}"
        elif kind == "gecis":
            transitions += 1
            base = f"gecis-{transitions}"
        else:
            base = kind
        parts.append(ParsedPart(unique(base), kind, title, number, paragraphs))
    return ParsedArticle(parts, dropped)
