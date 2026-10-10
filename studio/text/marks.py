"""Evidence marks of the video text (GÖREV-15, Adım 6).

The writers put the evidence id of every sentence that carries information at its end in square brackets: "… about $7,200 [K0123]." or
"… about $7,200. [K0123]"; one bracket may hold several ids ("[K0123, K0124]") and marks may follow each other ("[K0123][K0124]").
Before the paragraph is split into sentences the marks are taken out and their place is remembered; after splitting, every mark belongs
to the sentence it stands in, and a mark standing between two sentences (after the end mark, before the next sentence) belongs to the
sentence before it. So a mark always stays at the end of its sentence, whichever side of the full stop the writer put it. The clean
English sentence has no marks; the ids are kept apart, in order of appearance, without repeats.
"""
import re

from .split import split_sentences

MARK = re.compile(r"\s*\[(\s*K\d{4}(?:\s*[,;]\s*K\d{4})*\s*)\]")
ID = re.compile(r"K\d{4}")


def ids_in(text):
    """Every evidence id in the text, in order, without repeats."""
    return list(dict.fromkeys(ID.findall(text or "")))


def strip_marks(text):
    return " ".join(MARK.sub("", text or "").split())


def split_marked(paragraph, lang="en"):
    """[(clean sentence, [ids])] of a paragraph whose sentences end with evidence marks."""
    text = " ".join((paragraph or "").split())
    clean, marks, cursor = "", [], 0
    for match in MARK.finditer(text):                 # a mark is cut with the spaces before it; its place is where it stood
        clean += text[cursor:match.start()]
        marks.append((len(clean), ID.findall(match.group(1))))
        cursor = match.end()
    clean += text[cursor:]
    lead = len(clean) - len(clean.lstrip())
    clean = " ".join(clean.split())
    if not clean:
        return []
    sentences = split_sentences(clean, lang)
    starts, cursor = [], 0
    for sentence in sentences:
        found = clean.find(sentence, cursor)
        starts.append(found if found >= 0 else cursor)
        cursor = starts[-1] + len(sentence)
    out = [(sentence, []) for sentence in sentences]
    for place, ids in marks:
        place = max(0, place - lead)
        index = max((n for n, begin in enumerate(starts) if begin < place), default=0)   # in a sentence or right after it: that one
        out[index][1].extend(ids)
    return [(sentence, list(dict.fromkeys(ids))) for sentence, ids in out]


def marked(sentence, ids):
    """The sentence with its marks at the end, before the end mark: "… $7,200 [K0123]." (the form the final reader and the checks see)."""
    if not ids:
        return sentence
    tag = f"[{', '.join(ids)}]"
    match = re.match(r"^(.*?)([.!?]+[\"'”’)\]»]*)$", sentence)
    if match:
        return f"{match.group(1)} {tag}{match.group(2)}"
    return f"{sentence} {tag}"
