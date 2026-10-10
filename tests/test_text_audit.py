"""GÖREV-15 Adım 7: the program's check of the video text (Ek O): every red rule, the "doğrulanamadı" row, the small-sample comparison,
the source question, the warning phrases file and the "I" rule, the tolerance of numbers, length and the plan's check."""
import pytest

from studio.destinations import thirty_a
from studio.text import audit
from studio.text.numbers import Evidence, matches, mentions


def row(rid, value=None, unit=None, *, block="lodging_prices", small=False, status=None, extras=(), statement="", english=None):
    source = {"ad": "Kaynak", "durum": status} if status else {"ad": "Kaynak"}
    return {"id": rid, "blok": block, "deger": value, "birim": unit, "ek_degerler": list(extras), "kucuk_ornek": small, "kaynak": source,
            "ifade": statement, "ifade_en": english, "tablo": None, "durum": "var"}


def pack(*rows, checklist=()):
    return {"sections": [{"key": "b1", "rows": list(rows)}], "checklist": list(checklist)}


def doc(*sentences):
    """A document with one section part; `sentences` are (english, ids)."""
    items = [{"no": n, "en": en, "tr": "", "kanitlar": list(ids), "uyarilar": []} for n, (en, ids) in enumerate(sentences, 1)]
    return {"parcalar": [{"kimlik": "bolum-1", "tur": "bolum", "baslik": "1.", "numara": 1, "paragraflar": [{"kimlik": "bolum-1-p1", "cumleler": items}]}]}


def rules(found, level=None):
    return [f["kural"] for f in found if level is None or f["seviye"] == level]


PRICE = pack(row("K0001", 7223, "USD (7 gece)"), checklist=[{"kanit": "K0001", "tur": "ana", "deger": 7223, "birim": "USD (7 gece)"}])


@pytest.mark.parametrize("sentence, rule", [
    ("The beach is within walking distance [K0001].", "mesafe"),
    ("Seaside is walkable [K0001].", "mesafe"),
    ("It is a short walk to the sand [K0001].", "mesafe"),
    ("The store is ten minutes away [K0001].", "mesafe"),
    ("It is a five-minute drive [K0001].", "mesafe"),
    ("A week costs more here [K0001].", "fiyat"),
    ("A week in Rosemary Beach costs a lot [K0001].", "fiyat"),
    ("It costs about $7,200 a week [K0001].", "fiyat"),
    ("This is the full inventory of rentals [K0001].", "envanter"),
    ("We read every rental on the coast [K0001].", "envanter"),
    ("There are many homes in Seaside [K0001].", "envanter"),
    ("30A's climate is mild [K0001].", "iklim"),
    ("The climate in 30A changes slowly [K0001].", "iklim"),
    ("It is the best restaurant in town [K0001].", "restoran"),
    ("It is the most popular stop [K0001].", "restoran"),
    ("Expect a traffic jam in July [K0001].", "trafik"),
    ("It takes forty minutes to get there [K0001].", "trafik"),
    ("Traffic is bumper-to-bumper in summer [K0001].", "trafik"),
])
def test_each_red_rule_of_the_usage_notes(sentence, rule):
    found = audit.check(doc((sentence, ["K0001"])), PRICE)
    assert rule in rules(found, audit.RED)


def test_the_red_rules_know_their_blocks_and_documents():
    blocks = {code: (block, document) for code, block, document, _, _ in audit.RED_RULES}
    assert blocks == {"mesafe": ("daily_needs", "M13"), "fiyat": ("lodging_prices", "M11"), "envanter": ("lodging_inventory", "M10"),
                      "iklim": ("climate", "M8"), "restoran": ("restaurants", "M12"), "trafik": ("traffic", "M9")}


def test_a_clean_sentence_has_no_finding():
    found = audit.check(doc(("The county lists the beach access points [K0001].", ["K0001"])), PRICE)
    assert rules(found) == ["uzunluk"]                       # a one-sentence text is only too short


def test_a_row_that_could_not_be_verified_is_red_and_an_unknown_id_too():
    data = pack(row("K0002", None, None, block="references", status="dogrulanamadi"))
    found = audit.check(doc(("A new law took all beaches private [K0002].", ["K0002"]), ("Something else [K0099].", ["K0099"])), data)
    assert rules(found, audit.RED) == ["dogrulanamadi", "kimlik"]


def test_comparing_two_neighborhoods_from_a_small_sample_is_yellow():
    data = pack(row("K0003", 6100, "USD (7 gece)", small=True))
    regions = ["Seaside", "Rosemary Beach", "Alys Beach"]
    found = audit.check(doc(("Seaside runs cheaper than Rosemary Beach by our count [K0003].", ["K0003"])), data, regions=regions)
    assert "kucuk_ornek" in rules(found, audit.YELLOW)
    alone = audit.check(doc(("Seaside has a small sample here [K0003].", ["K0003"])), data, regions=regions)
    assert "kucuk_ornek" not in rules(alone)


def test_no_public_beach_access_without_a_source_is_a_question():
    found = audit.check(doc(("There is no public beach access in Rosemary Beach [K0001].", ["K0001"])), PRICE)
    assert "kaynak_sorusu" in rules(found, audit.YELLOW)
    sourced = audit.check(doc(("Walton County keeps the list of beach accesses [K0001].", ["K0001"]),
                              ("It shows no public beach access in Rosemary Beach [K0001].", ["K0001"])), PRICE)
    assert "kaynak_sorusu" not in rules(sourced)


def test_the_warning_phrases_file_and_the_capital_i_rule():
    phrases = audit.read_phrases(thirty_a.TEXT["warning_phrases"])
    assert phrases[:3] == ["amazing", "stunning", "breathtaking"] and "I" in phrases and "the ocean" in phrases
    found = audit.check(doc(("It is an Amazing view, nestled by the ocean [K0001].", ["K0001"]),
                            ("I think you will like it [K0001].", ["K0001"]),
                            ("I'm sure of it [K0001].", ["K0001"]),
                            ("The river i saw was small [K0001].", ["K0001"]),
                            ("It is called Item four [K0001].", ["K0001"])), PRICE, phrases=phrases)
    texts = [(f["no"], f["metin"]) for f in found if f["kural"] == "ses"]
    assert (1, "Uyarı ifadesi: “amazing”.") in texts and (1, "Uyarı ifadesi: “nestled”.") in texts and (1, "Uyarı ifadesi: “the ocean”.") in texts
    assert (2, "Uyarı ifadesi: “I”.") in texts
    assert (3, "Uyarı ifadesi: “I'm”.") in texts and (3, "Uyarı ifadesi: “I”.") not in texts
    assert not [t for t in texts if t[0] in (4, 5)]          # "i" in lower case and "Item" are not the word "I"


# ---- numbers -------------------------------------------------------------------------------------------------------------------

def holds(sentence, *values):
    evidence = [Evidence([(v, k) for v, k in values], set(), "")]
    return all(matches(m, evidence) for m in mentions(sentence))


@pytest.mark.parametrize("sentence, value, ok", [
    ("A week runs about $7,200.", (7223, "money"), True),
    ("A week runs about $7,000.", (7223, "money"), True),
    ("Highs reach 84 degrees.", (84.2, "temperature"), True),
    ("That is about 7 percent.", (7.1, "percent"), True),
    ("We counted about 90 listings.", (87, "count"), True),
    ("A week runs $7,500.", (7223, "money"), False),
    ("We counted 90 listings.", (87, "count"), False),
    ("We counted 87 listings.", (87, "count"), True),
    ("Highs reach 86 degrees.", (84.2, "temperature"), False),
    ("That is 8 percent.", (7.1, "percent"), False),
    ("About a third of the homes are close.", (33, "percent"), True),
    ("Half of the homes are close.", (40, "percent"), False),
    ("Seven thousand people came.", (7000, "number"), True),
    ("It was $1.5 million.", (1523000, "money"), True),
])
def test_the_tolerance_of_numbers(sentence, value, ok):
    assert holds(sentence, value) is ok


def test_numbers_against_the_marks_of_a_sentence():
    found = audit.check(doc(("A week here ran about $7,200 in July [K0001].", ["K0001"]),
                            ("It ran $7,500 in July [K0001].", ["K0001"]),
                            ("It ran $7,223 without a mark.", [])), PRICE)
    assert [(f["no"], f["kural"]) for f in found if f["seviye"] == audit.RED] == [(2, "rakam"), (3, "rakam_isaretsiz")]


def test_roads_and_names_with_digits_are_not_numbers_and_years_come_from_the_row():
    data = pack(row("K0004", 2016, None, block="references", statement="2016 kararı", english="In 2016 the county adopted it."))
    found = audit.check(doc(("Drive Highway 98 and County Road 30A [K0004].", ["K0004"]),
                            ("In 2016 the county voted [K0004].", ["K0004"]),
                            ("In 2019 the county voted [K0004].", ["K0004"])), data)
    assert [(f["no"], f["kural"]) for f in found if f["seviye"] == audit.RED] == [(3, "rakam")]


def test_words_and_times_are_read():
    assert [m.kind for m in mentions("Two thirds of it, seven thousand visitors, ten percent and 3:30 p.m.")] == ["fraction", "count", "percent", "time"]


# ---- length and the plan ------------------------------------------------------------------------------------------------------

def long_doc(words_per_part):
    parts = []
    for number, words in enumerate(words_per_part, 1):
        sentence = {"no": number, "en": " ".join(["word"] * words), "tr": "", "kanitlar": [], "uyarilar": []}
        parts.append({"kimlik": f"bolum-{number}", "tur": "bolum", "baslik": "", "numara": number,
                      "paragraflar": [{"kimlik": f"bolum-{number}-p1", "cumleler": [sentence]}]})
    return {"parcalar": parts}


def test_length_findings():
    plan = {"bolumler": [{"no": 1, "kelime_butcesi": 400}, {"no": 2, "kelime_butcesi": 400}]}
    found = audit.length_findings(long_doc([400, 600]), plan)
    assert [f["kural"] for f in found] == ["uzunluk", "bolum_uzunlugu"]
    assert "2. bölüm 600 kelime; bütçesi 400 (%+50)" in found[1]["metin"]
    assert audit.length_findings(long_doc([1200, 1100]), {"bolumler": [{"no": 1, "kelime_butcesi": 1100}, {"no": 2, "kelime_butcesi": 1100}]}) == []


def test_the_plan_check():
    plan = {"bolumler": [{"no": 1, "kanitlar": ["K0001"], "kelime_butcesi": 300, "acilis_bicimi": "soru"},
                         {"no": 2, "kanitlar": ["K9999"], "kelime_butcesi": 300, "acilis_bicimi": "soru"}],
            "kavramlar": [{"kavram": "customary use", "bolum": 5}], "yeniden_kancalar": [{"bolumden_sonra": 1}]}
    found = audit.plan_findings(plan, {"K0001"})
    levels = [level for level, _ in found]
    assert levels[0] == "hata" and "K9999" in found[0][1]
    assert any("customary use" in t for _, t in found) and any("aynı biçimde açılıyor (soru)" in t for _, t in found)
    assert any("Bölüm bütçelerinin toplamı 600" in t for _, t in found) and levels.count("hata") == 1
    good = {"bolumler": [{"no": n, "kanitlar": ["K0001"], "kelime_butcesi": 350, "acilis_bicimi": b} for n, b in
                         zip(range(1, 7), ("rakam", "sahne", "soru", "gecmis", "karsilastirma", "diger"))],
            "kavramlar": [{"kavram": "x", "bolum": 2}], "yeniden_kancalar": [{"bolumden_sonra": 2}]}
    assert audit.plan_findings(good, {"K0001"}) == []
