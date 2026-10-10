"""İki dilde rakam denetimi (GÖREV-15, Adım 5 ve 6): The Housing Atlas Stüdyo'nun `atlas/article/digits.py`'si (MS1) aynen. Çevirmenden
sonra her cümlenin İngilizcesi ile Türkçesindeki rakamlar karşılaştırılır; tutmayan cümleye "rakam" uyarısı düşer. Metindeki rakamların
kanıtla karşılaştırılması ayrı modülde (`studio/text/numbers.py`).

İki dildeki rakamların karşılaştırılması (MS1 Görev 3 ve 5): paralar, yüzdeler, yıllar, metrekareler.

Bir cümledeki her sayı (rakamla yazılmış; aradaki nokta ve virgül ayraçlarıyla) ayraçları atılarak karşılaştırılır:
"$170,000" ile "170.000 dolar" aynıdır ("170000"), "3.2%" ile "%3,2" aynıdır ("32"), "$1.5 million" ile "1,5 milyon"
aynıdır ("15"). Sayının sonundaki ayraç sayıya girmez ("2022." → "2022"). İngilizcedeki her sayı Türkçede de geçmeli,
Türkçedeki her sayı İngilizcede de (küme olarak; aynı sayının kaç kez geçtiği sayılmaz). Yazıyla yazılmış sayılar
("nine times") karşılaştırmaya girmez.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_NUMBER = re.compile(r"\d(?:[\d.,]*\d)?")


def numbers(text: str) -> dict[str, str]:
    """Metindeki sayılar: ayraçsız rakamlar → metinde ilk yazılışı ("170000" → "170,000")."""
    found: dict[str, str] = {}
    for match in _NUMBER.finditer(text or ""):
        written = match.group(0)
        key = re.sub(r"[.,]", "", written)
        found.setdefault(key, written)
    return found


@dataclass(frozen=True)
class DigitCheck:
    only_en: tuple[str, ...]  # İngilizcede olup Türkçede olmayan (İngilizce yazılışıyla)
    only_tr: tuple[str, ...]  # Türkçede olup İngilizcede olmayan (Türkçe yazılışıyla)

    @property
    def ok(self) -> bool:
        return not self.only_en and not self.only_tr

    def message(self) -> str:
        """Program uyarısının Türkçe metni (tutuyorsa "")."""
        if self.ok:
            return ""
        parts = []
        if self.only_en:
            parts.append(f"İngilizcede olup Türkçede olmayan: {', '.join(self.only_en)}")
        if self.only_tr:
            parts.append(f"Türkçede olup İngilizcede olmayan: {', '.join(self.only_tr)}")
        return "Rakamlar iki dilde tutmuyor. " + "; ".join(parts) + "."


def compare(en: str, tr: str) -> DigitCheck:
    """İki cümlenin rakamlarını karşılaştırır (kural modülün açıklamasında)."""
    left, right = numbers(en), numbers(tr)
    return DigitCheck(tuple(left[k] for k in left if k not in right), tuple(right[k] for k in right if k not in left))


def compare_many(en: list[str], tr: list[str]) -> DigitCheck:
    """Birden çok cümlenin rakamları birlikte (düzeltmede bir değişikliğin bütün cümleleri)."""
    return compare(" ".join(en), " ".join(tr))
