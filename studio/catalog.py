"""Başlangıç kaynak adayları; işletme veya fiyat verisi içermez."""

CATEGORIES = ["Genel", "Konaklama", "Yeme içme", "Plaj", "Ulaşım", "Aktivite", "Hava", "Etkinlik"]
from .regions import REGIONS as CANONICAL_REGIONS

REGIONS = ["Tüm 30A", *(name for _, name in CANONICAL_REGIONS)]
METHODS = ["Belirlenecek", "HTML", "JSON", "API", "Dosya", "PDF", "Playwright"]
CADENCES = ["Günlük", "Haftalık", "Aylık", "Gerektiğinde"]

from .destinations.thirty_a import SEEDS

# The VERİ group of the sidebar: tool screens (GÖREV-14). The steps of a video (Veri … Yayın hazırlığı) come from `workflow.py`;
# "Rakip analizi" and "İçerik briefi" were removed (competitor research is in the channel research file, the brief is the data pack).
STEPS = [
    ("sources", "Veri kaynakları", "Kaynak kütüphanesi", "active"),
    ("collect", "Veri toplama", "Üç kaynak hazır", "active"),
    ("quality", "Veri kontrolü", "Katalog kontrolü hazır", "partial"),
    ("evidence", "Kanıt paketi", "Şablondan kanıt", "active"),
]
