"""Marks of a title candidate (GÖREV-18 Adım 6): shown on the candidate's card; information only, no candidate is refused.

Red (6a): a business name (`studio/text/businesses.py`) in the English title or in the cover idea.
Yellow (6b):
- the topic is not in the first 40 characters of the English title (the suffix does not count; it is at the end anyway). The topic is the
  candidate's region as the title would say it ("30A" for the whole destination, the neighborhood's name otherwise): a phone shows only the
  first ~40 characters;
- the cover text is longer than 3 words, or repeats words of the title (conjunctions, articles and "30A" do not count). The cover text is
  the quoted text the cover idea names as the big text ("büyük yazı '…'", "başlık '…'", "büyük harflerle '…'", "kapak yazısı '…'"); a
  cover idea without such a text gives no cover warning (the program does not guess which quoted label is the cover text);
- more than 2 words in capitals in the title (a word with a digit, like "30A", is not counted).
"""
import re

PHONE_CHARS = 40
COVER_WORDS = 3
CAPS_LIMIT = 2
RED, YELLOW = "kirmizi", "sari"
COVER_KEYS = re.compile(r"(?:büyük yazı(?:yla)?|büyük harflerle|kapak yazısı|başlık|ana yazı)\s*[:]?\s*", re.I)
QUOTES = {"'": "'", "‘": "’", "’": "’", "\"": "\"", "“": "”", "«": "»"}
SKIP_WORDS = {"and", "or", "but", "nor", "so", "yet", "the", "a", "an", "of", "in", "on", "at", "to", "for", "vs", "with", "30a", "&"}
WORD = re.compile(r"[A-Za-zÀ-ÿ0-9$%][A-Za-zÀ-ÿ0-9$%'’.,\-]*")


def without_suffix(title, suffix):
    suffix = (suffix or {}).get("en") if isinstance(suffix, dict) else suffix
    return title[: -len(suffix)] if suffix and title.endswith(suffix) else title


def topic_word(region, whole_region):
    return "30A" if not region or region == whole_region else region


def cover_text(idea):
    """The cover's big text from the cover idea, or None when the idea does not name one."""
    for found in COVER_KEYS.finditer(idea or ""):
        rest = idea[found.end():]
        if not rest or rest[0] not in QUOTES:
            continue
        opening, closing = rest[0], QUOTES[rest[0]]
        body = rest[1:]
        if opening == "'":
            end = re.search(r"'(?![A-Za-z])", body)          # "IT'S A ROAD" keeps its apostrophe
            index = end.start() if end else -1
        else:
            index = body.find(closing)
        if index > 0:
            return body[:index].strip()
    return None


def words(text):
    return [w.strip(".,'’-").casefold() for w in WORD.findall(text or "") if w.strip(".,'’-")]


def caps_words(title):
    return [w for w in re.findall(r"[A-Za-zÀ-ÿ'’]+(?:-[A-Za-zÀ-ÿ'’]+)*|\S*\d\S*", title)
            if not any(ch.isdigit() for ch in w) and sum(ch.isalpha() for ch in w) >= 2 and w.upper() == w]


def mark(level, code, text):
    return {"seviye": level, "kod": code, "metin": text}


def marks(title_en, cover_idea, *, region=None, whole_region=None, suffix=None, businesses=None):
    out = []
    title = without_suffix(title_en or "", suffix)
    if businesses is not None:
        for name in businesses.find(title_en or ""):
            out.append(mark(RED, "isletme", f"İngilizce başlıkta işletme adı: {name} (videolarda işletme adı geçmez)."))
        for name in businesses.find(cover_idea or ""):
            out.append(mark(RED, "isletme", f"Kapak fikrinde işletme adı: {name} (videolarda işletme adı geçmez)."))
    topic = topic_word(region, whole_region)
    if topic and topic.casefold() not in title[:PHONE_CHARS].casefold():
        out.append(mark(YELLOW, "ilk_40", f"Telefonda yalnız ilk yaklaşık {PHONE_CHARS} karakter görünür; konu orada olmalı (“{topic}” ilk "
                                          f"{PHONE_CHARS} karakterde yok: “{title[:PHONE_CHARS]}…”)."))
    cover = cover_text(cover_idea)
    if cover is not None:
        count = len(words(cover))
        if count > COVER_WORDS:
            out.append(mark(YELLOW, "kapak_uzun", f"Kapak yazısı {COVER_WORDS} kelimeden uzun ({count} kelime): “{cover}”."))
        repeated = sorted({w for w in words(cover) if w not in SKIP_WORDS} & {w for w in words(title) if w not in SKIP_WORDS})
        if repeated:
            out.append(mark(YELLOW, "kapak_tekrar", f"Kapak yazısı başlıktaki kelimeleri tekrar ediyor: {', '.join(repeated)} (“{cover}”)."))
    caps = caps_words(title)
    if len(caps) > CAPS_LIMIT:
        out.append(mark(YELLOW, "buyuk_harf", f"Başlıkta {CAPS_LIMIT}'den fazla tamamı büyük harfli kelime var: {', '.join(caps)}."))
    return out
