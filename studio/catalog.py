"""Başlangıç kaynak adayları; işletme veya fiyat verisi içermez."""

CATEGORIES = ["Genel", "Konaklama", "Yeme içme", "Plaj", "Ulaşım", "Aktivite", "Hava", "Etkinlik"]
from .regions import REGIONS as CANONICAL_REGIONS

REGIONS = ["Tüm 30A", *(name for _, name in CANONICAL_REGIONS)]
METHODS = ["Belirlenecek", "HTML", "JSON", "API", "PDF", "Playwright"]
CADENCES = ["Günlük", "Haftalık", "Aylık", "Gerektiğinde"]

from .destinations.thirty_a import SEEDS

STEPS = [
    ("sources", "Veri kaynakları", "Kaynak kütüphanesi", "active"),
    ("collect", "Veri toplama", "Üç kaynak hazır", "active"),
    ("quality", "Veri kontrolü", "Katalog kontrolü hazır", "partial"),
    ("research", "Konu araştırması", "Veriden konuya", "planned"),
    ("competitors", "Rakip analizi", "İçerik fırsatları", "planned"),
    ("brief", "İçerik briefi", "Kapsam ve kaynaklar", "planned"),
    ("article", "Makale", "Kaynaklı içerik", "planned"),
    ("visuals", "Görsel plan", "Sahne ve varlıklar", "planned"),
    ("video", "Video üretimi", "Kurgu ve render", "planned"),
    ("publish", "Yayın hazırlığı", "Son kontrol ve çıktı", "planned"),
]
