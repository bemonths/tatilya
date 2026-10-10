"""GÖREV-15 Adım 6: the video text as data — evidence marks tied to their sentences and the clean text, the joining order of the parts,
numbering, the final reader's corrections (applied, or refused when a mark is lost), the translator's number check, the digits of both
languages and the files of a version."""
import pytest

from studio.text import document as D, marks


def test_marks_stay_with_their_sentence_whichever_side_of_the_full_stop():
    found = marks.split_marked("Prices rose to about $7,200 [K0123]. The beach is wide. [K0004] Rosemary has 9 walkovers [K0007, K0008]. "
                               "He moved to the U.S. [K0001] The next year it rained [K0002][K0003].")
    assert found == [("Prices rose to about $7,200.", ["K0123"]), ("The beach is wide.", ["K0004"]), ("Rosemary has 9 walkovers.", ["K0007", "K0008"]),
                     ("He moved to the U.S.", ["K0001"]), ("The next year it rained.", ["K0002", "K0003"])]
    assert marks.split_marked("[K0001] Odd start. No mark here.") == [("Odd start.", ["K0001"]), ("No mark here.", [])]
    assert marks.strip_marks("Clean [K0001]. Text [K0002, K0003].") == "Clean. Text."
    assert marks.marked("It costs about $7,200.", ["K0123", "K0001"]) == "It costs about $7,200 [K0123, K0001]."
    assert marks.ids_in("[K0001] a [K0002, K0001]") == ["K0001", "K0002"]


PLAN = {"bolumler": [{"no": 1, "ic_adi": "Bir"}, {"no": 2, "ic_adi": "İki"}, {"no": 3, "ic_adi": "Üç"}]}
SECTIONS = {1: {"paragraflar": ["One a [K0001]. One b [K0002]."]}, 2: {"paragraflar": ["Two a [K0003].", "Two b."]},
            3: {"paragraflar": ["Three [K0004]."]}}
MERGE = {"gecisler": [{"onceki_bolum": 1, "sonraki_bolum": 2, "metin": "Now to two."}, {"onceki_bolum": 2, "sonraki_bolum": 3, "metin": "Then three."}],
         "yeniden_kancalar": [{"bolumden_sonra": 2, "metin": "Stay for the answer [K0003]."}], "notlar": []}
ENDS = {"giris": ["Hello [K0001]."], "kapanis": ["Bye. Subscribe."]}


def assembled():
    return D.assemble(PLAN, SECTIONS, MERGE, ENDS)


def test_parts_come_in_order_and_sentences_are_numbered_through_the_text():
    document = assembled()
    assert [(p["kimlik"], p["tur"], p["baslik"]) for p in document["parcalar"]] == [
        ("giris", "giris", "Giriş"), ("bolum-1", "bolum", "1. Bir"), ("gecis-1", "gecis", "Geçiş 1 → 2"), ("bolum-2", "bolum", "2. İki"),
        ("gecis-2", "gecis", "Yeniden kanca (2. bölümden sonra)"), ("gecis-3", "gecis", "Geçiş 2 → 3"), ("bolum-3", "bolum", "3. Üç"),
        ("kapanis", "kapanis", "Kapanış")]
    sentences = D.sentences(document)
    assert [s["no"] for s in sentences] == list(range(1, len(sentences) + 1))
    assert [(s["en"], s["kanitlar"]) for s in sentences[:3]] == [("Hello.", ["K0001"]), ("One a.", ["K0001"]), ("One b.", ["K0002"])]
    assert document["parcalar"][3]["paragraflar"][1]["kimlik"] == "bolum-2-p2"
    numbered = D.marked_text(document, numbered=True, title="T")
    assert "[2] One a [K0001]." in numbered and "## Yeniden kanca (2. bölümden sonra)" in numbered


def test_the_final_readers_correction_keeps_marks_or_is_refused():
    document = assembled()
    document, applied, refused = D.apply_corrections(document, [
        {"no": 2, "yeni": "Indeed, one a [K0001].", "gerekce": "Doğal."},
        {"no": 3, "yeni": "One b without its mark.", "gerekce": "Kısa."},
        {"no": 5, "yeni": "Two a, first [K0003]. Two a, second.", "gerekce": "Böl."},
        {"no": 99, "yeni": "None.", "gerekce": "Yok."}], pack_ids={"K0001", "K0002", "K0003", "K0004"})
    sentences = D.sentences(document)
    assert sentences[1]["en"] == "Indeed, one a." and sentences[1]["kanitlar"] == ["K0001"]
    assert sentences[2]["en"] == "One b." and sentences[2]["uyarilar"][0]["tur"] == "son_okuma"
    assert "kanıt işaretleri korunmadı (K0002)" in sentences[2]["uyarilar"][0]["metin"]
    assert [s["en"] for s in sentences[4:6]] == ["Two a, first.", "Two a, second."]
    assert [s["no"] for s in sentences] == list(range(1, len(sentences) + 1))
    assert [a["no"] for a in applied] == [2, 5] and [r["no"] for r in refused] == [3, 99]
    _, _, added = D.apply_corrections(assembled(), [{"no": 2, "yeni": "One a [K0001, K0777].", "gerekce": "x"}], pack_ids={"K0001"})
    assert "pakette olmayan" in added[0]["neden"]


def test_the_translation_has_every_number_once_and_the_digits_of_both_languages_are_checked():
    with pytest.raises(D.AnswerError, match="Şu numaraların çevirisi yok: 3"):
        D.check_translation({"cumleler": [{"no": 1, "tr": "a"}, {"no": 2, "tr": "b"}]}, [1, 2, 3])
    with pytest.raises(D.AnswerError, match="birden çok kez"):
        D.check_translation({"cumleler": [{"no": 1, "tr": "a"}, {"no": 1, "tr": "b"}]}, [1])
    with pytest.raises(D.AnswerError, match="metinde yok: 7"):
        D.check_translation({"cumleler": [{"no": 1, "tr": "a"}, {"no": 7, "tr": "b"}]}, [1])
    with pytest.raises(D.AnswerError, match="Türkçesi boş: 1"):
        D.check_translation({"cumleler": [{"no": 1, "tr": "  "}]}, [1])
    document = D.assemble({"bolumler": [{"no": 1, "ic_adi": "x"}]}, {1: {"paragraflar": ["It costs $7,200 [K0001]. Wide beaches."]}},
                          {}, {"giris": [], "kapanis": []})
    answers = {1: {"no": 1, "tr": "7.200 dolar tutar.", "uyari": None}, 2: {"no": 2, "tr": "Geniş plajlar 9.", "uyari": "Belirsiz."}}
    document = D.apply_translation(document, answers, [{"en": "walkover", "tr": "walkover", "aciklama": "Geçit."}])
    first, second = D.sentences(document)
    assert first["tr"] == "7.200 dolar tutar." and first["uyarilar"] == []
    assert [w["tur"] for w in second["uyarilar"]] == ["cevirmen", "rakam"] and "Türkçede olup İngilizcede olmayan: 9" in second["uyarilar"][1]["metin"]
    assert document["terimler"] == [{"en": "walkover", "tr": "walkover", "aciklama": "Geçit."}]


def test_the_files_of_a_version():
    document = assembled()
    answers = {s["no"]: {"no": s["no"], "tr": "TR " + s["en"], "uyari": None} for s in D.sentences(document)}
    document = D.apply_translation(document, answers, [{"en": "walkover", "tr": "walkover", "aciklama": "Geçit."}])
    voice = D.voice_text(document)
    assert "[" not in voice and "#" not in voice and voice.startswith("Hello.\n\nOne a. One b.")
    english = D.render(document, "Title")
    assert english.startswith("# Title\n\n## Giriş\n\nHello.") and "[K0001]" not in english
    turkish = D.render(document, "Başlık", "tr")
    assert "## Terimler" in turkish and "- **walkover** (walkover): Geçit." in turkish
    marked = D.evidence_text(document, "Title")
    assert "[1] Hello [K0001]." in marked
    report = D.audit_text(document, [{"no": 2, "seviye": "kirmizi", "kural": "mesafe", "metin": "Mesafe."}], "Title")
    assert "- Kırmızı bulgu: 1" in report and "- [2] Mesafe." in report and "  - Cümle: One a [K0001]." in report


def test_long_texts_are_translated_in_whole_parts():
    document = assembled()
    chunks = D.chunks(document, limit=3)
    assert all(len(chunk) >= 1 for chunk in chunks) and sum(len(c) for c in chunks) == len(document["parcalar"])
    assert len(D.chunks(document)) == 1
