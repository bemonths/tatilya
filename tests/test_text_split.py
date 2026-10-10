"""Cümle bölme (GÖREV-15): The Housing Atlas Stüdyo'nun `tests/test_article_split.py`'si aynen (atlas.article.split → studio.text.split;
örnek makale `tests/fixtures/metin/florida_kisa_EN.md`)."""

from pathlib import Path

import pytest

from studio.text.split import classify_heading, parse_article, split_en, split_tr

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "metin" / "florida_kisa_EN.md"


@pytest.mark.parametrize("text, expected", [
    ("Prices fell. Sales rose.", ["Prices fell.", "Sales rose."]),
    ("Is it cheap? Yes! It is.", ["Is it cheap?", "Yes!", "It is."]),
    # kısaltmalar
    ("Mr. Smith lives on Main St. in St. Petersburg. He moved.", ["Mr. Smith lives on Main St. in St. Petersburg.",
                                                                  "He moved."]),
    ("Dr. Jones agreed. Prof. Lee did not.", ["Dr. Jones agreed.", "Prof. Lee did not."]),
    ("It was approx. 5 miles away. We drove.", ["It was approx. 5 miles away.", "We drove."]),
    ("The U.S. Census Bureau counted them. Then it rained.", ["The U.S. Census Bureau counted them.",
                                                              "Then it rained."]),
    ("He moved to the U.S. The next year he bought a house.", ["He moved to the U.S.",
                                                               "The next year he bought a house."]),
    ("It closed on Jan. 15, 2024. Prices rose.", ["It closed on Jan. 15, 2024.", "Prices rose."]),
    ("They met at 9 a.m. Monday. It went well.", ["They met at 9 a.m. Monday.", "It went well."]),
    ("Joel B. Berner said so. Others agreed.", ["Joel B. Berner said so.", "Others agreed."]),
    ("Acme Inc. The company grew.", ["Acme Inc.", "The company grew."]),
    ("The house is 2,000 sq. ft. and it has a pool.", ["The house is 2,000 sq. ft. and it has a pool."]),
    ("Fort Myers, e.g. the downtown, flooded. Then it dried.", ["Fort Myers, e.g. the downtown, flooded.",
                                                                "Then it dried."]),
    # ondalıklar ve paralar
    ("It sold for $1.5 million. That was 3.2% more.", ["It sold for $1.5 million.", "That was 3.2% more."]),
    ("The rate is 6.75 percent. It was 7.1 before.", ["The rate is 6.75 percent.", "It was 7.1 before."]),
    ("Prices peaked in 2022. Three months later, Ian hit.", ["Prices peaked in 2022.", "Three months later, Ian hit."]),
    ("He works at Realtor.com in Tampa. He is an economist.", ["He works at Realtor.com in Tampa.",
                                                               "He is an economist."]),
    # tırnaklar
    ('She said "they are tired. They are tired of costs." Then she left.',
     ['She said "they are tired. They are tired of costs."', "Then she left."]),
    ("He wrote “Prices fell. Sales rose.” in May. It was true.", ["He wrote “Prices fell. Sales rose.” in May.",
                                                                  "It was true."]),
    ('"Is it over?" she asked. Nobody knew.', ['"Is it over?" she asked.', "Nobody knew."]),
    ('One quote never closes: "Prices fell. Sales rose.', ['One quote never closes: "Prices fell.', "Sales rose."]),
    # üç nokta
    ("And then... The market turned.", ["And then... The market turned."]),
    ("Wait… Prices rose again.", ["Wait… Prices rose again."]),
    # küçük harfle devam, liste işareti, boşluklar
    ("It was approx. five miles.", ["It was approx. five miles."]),
    ("1. First item here. Second sentence.", ["1. First item here.", "Second sentence."]),
    ("  Lots   of\nspace.  Here.  ", ["Lots of space.", "Here."]),
    ("", []),
])
def test_split_en(text: str, expected: list[str]) -> None:
    assert split_en(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("Fiyatlar düştü. Satışlar arttı.", ["Fiyatlar düştü.", "Satışlar arttı."]),
    ("Dr. Ahmet geldi. Prof. Ayşe gelmedi.", ["Dr. Ahmet geldi.", "Prof. Ayşe gelmedi."]),
    ("Havuz, garaj vb. özellikler var. Bu ev güzel.", ["Havuz, garaj vb. özellikler var.", "Bu ev güzel."]),
    ("Havuz, garaj vb. Bu ev güzel.", ["Havuz, garaj vb.", "Bu ev güzel."]),
    ("Örn. Lee County böyle. Diğerleri değil.", ["Örn. Lee County böyle.", "Diğerleri değil."]),
    ("Ev St. Petersburg'da. Fiyatı yüksek.", ["Ev St. Petersburg'da.", "Fiyatı yüksek."]),
    ("Ev 1,5 milyon dolara satıldı. Bu %3,2 fazla.", ["Ev 1,5 milyon dolara satıldı.", "Bu %3,2 fazla."]),
    ("Fiyat 170.000 dolar düştü. Satış arttı.", ["Fiyat 170.000 dolar düştü.", "Satış arttı."]),
    ("Geri sayıma 10. Lee County ile başlıyoruz. Sonra 9. sıraya geçiyoruz.",
     ["Geri sayıma 10. Lee County ile başlıyoruz.", "Sonra 9. sıraya geçiyoruz."]),
    ('Jones "insanlar yoruldu. Masraflardan yoruldular." dedi. Sonra gitti.',
     ['Jones "insanlar yoruldu. Masraflardan yoruldular." dedi.', "Sonra gitti."]),
    ("Peki ya şimdi... Fiyatlar yine düştü.", ["Peki ya şimdi... Fiyatlar yine düştü."]),
    ("Neden satılmıyor? Çünkü pahalı!", ["Neden satılmıyor?", "Çünkü pahalı!"]),
])
def test_split_tr(text: str, expected: list[str]) -> None:
    assert split_tr(text) == expected


@pytest.mark.parametrize("title, expected", [
    ("Intro", ("giris", None)), ("Introduction", ("giris", None)), ("Giriş", ("giris", None)),
    ("Closing", ("kapanis", None)), ("Outro", ("kapanis", None)), ("Kapanış", ("kapanis", None)),
    ("1", ("madde", 1)), ("10.", ("madde", 10)), ("10. Lee County", ("madde", 10)),
    ("10 · Lee County", ("madde", 10)), ("10 Lee County", ("madde", 10)), ("No. 3", ("madde", 3)),
    ("#3 Pasco", ("madde", 3)), ("Mid-video hook", ("gecis", None)), ("2013 was the year", ("gecis", None)),
])
def test_classify_heading(title: str, expected: tuple) -> None:
    assert classify_heading(title) == expected


def test_parse_parts_paragraphs_and_ids() -> None:
    text = ("# Florida video\n\nSome text before. More text.\n\n## Intro\n\nHello there. Welcome.\n\nSecond para.\n\n"
            "## 10 · Lee County\nLine one\ncontinues here. Next.\n\n---\n\nAfter the rule.\n\n## Mid-video hook\n\n"
            "Stay with us.\n\n## Empty heading\n\n## 3\n\nThree.\n\n## 3\n\nThree again.\n\n## Closing\n\nBye.\n")
    article = parse_article(text)
    assert [(p.kimlik, p.tur, p.baslik, p.numara) for p in article.parts] == [
        ("gecis-1", "gecis", "Florida video", None), ("giris", "giris", "Intro", None),
        ("madde-10", "madde", "10 · Lee County", 10), ("gecis-2", "gecis", "Mid-video hook", None),
        ("madde-3", "madde", "3", 3), ("madde-3-2", "madde", "3", 3), ("kapanis", "kapanis", "Closing", None)]
    assert article.dropped == ["Empty heading"]
    assert article.parts[1].paragraphs == [["Hello there.", "Welcome."], ["Second para."]]
    assert article.parts[2].paragraphs == [["Line one continues here.", "Next."], ["After the rule."]]
    assert article.sentence_count == 12


def test_parse_without_headings_and_text_before_first_heading() -> None:
    plain = parse_article("One. Two.\r\n\r\nThree.")
    assert [(p.kimlik, p.tur, p.baslik) for p in plain.parts] == [("metin", "metin", "")]
    assert plain.parts[0].paragraphs == [["One.", "Two."], ["Three."]]
    before = parse_article("Opening line here.\n\n## 1\n\nFirst.")
    assert [(p.kimlik, p.tur, p.baslik) for p in before.parts] == [("giris", "giris", ""), ("madde-1", "madde", "1")]
    assert parse_article("   \n\n").parts == []


def test_real_article_sample() -> None:
    """Kullanıcının eski Florida makalesinden kısaltılmış örnek (giriş, 10, 9, ara kanca, 1, kapanış)."""
    article = parse_article(FIXTURE.read_text(encoding="utf-8"))
    assert [p.kimlik for p in article.parts] == ["giris", "madde-10", "madde-9", "gecis-1", "madde-1", "kapanis"]
    assert [p.sentence_count for p in article.parts] == [11, 16, 15, 5, 16, 16]
    sentences = [s for p in article.parts for para in p.paragraphs for s in para]
    assert len(sentences) == 79
    # tırnak içindeki noktalar bölünmez
    quote = next(s for s in sentences if s.startswith("Arthur Jones"))
    assert quote.endswith('"because they\'re tired of having to rebuild. They\'re tired of the high costs. They\'re '
                          'tired of the anxiety that comes from hurricane season."')
    assert any(s.startswith("Gloria Rybinski") and s.endswith('see your living room flooded."') for s in sentences)
    # paralar ve alan adları bölünmez; her cümle büyük harfle başlar, noktalamayla biter
    assert any("$170,000" in s for s in sentences)
    assert all(s[0].isupper() and s[-1] in '.!?"' for s in sentences)
