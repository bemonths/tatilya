"""Başlangıç kaynak adayları; işletme veya fiyat verisi içermez."""

CATEGORIES = ["Genel", "Konaklama", "Yeme içme", "Plaj", "Ulaşım", "Aktivite", "Hava", "Etkinlik"]
from .regions import REGIONS as CANONICAL_REGIONS

REGIONS = ["Tüm 30A", *(name for _, name in CANONICAL_REGIONS)]
METHODS = ["Belirlenecek", "HTML", "JSON", "API", "PDF", "Playwright"]
CADENCES = ["Günlük", "Haftalık", "Aylık", "Gerektiğinde"]

SEEDS = [
    ("Visit South Walton", "https://www.visitsouthwalton.com/", "Genel",
     "Bölge rehberi ve kaynak keşfi. South Walton kapsamındaki kayıtlar 30A için ayrıca filtrelenecek."),
    ("South Walton · Restoranlar", "https://www.visitsouthwalton.com/listings/culinary-experiences/", "Yeme içme",
     "Restoran dizini. Menü ve fiyatlar için işletmelerin kendi sayfaları ayrıca incelenecek."),
    ("South Walton · Plaj erişimleri", "https://www.visitsouthwalton.com/beach-bay-access-locations/", "Plaj",
     "Plaj erişim noktalarının adresi, koordinatları, erişim türü ve kaynakta listelenen olanakları. Veri toplama ekranında belirtilen kıyı kapsamı kullanılır."),
    ("South Walton · Etkinlikler", "https://www.visitsouthwalton.com/events/", "Etkinlik",
     "Etkinlik takvimi. Tarih, konum ve iptal değişikliklerinin takibi planlanıyor."),
    ("South Walton · Ulaşım", "https://www.visitsouthwalton.com/listings/transportation/", "Ulaşım",
     "Ulaşım işletmeleri. Fiyat ve hizmet kapsamı henüz toplanmadı."),
    ("National Weather Service", "https://www.weather.gov/", "Hava",
     "Hava verisi için başlangıç kaynağı. Bölge koordinatları ve veri uçları sonraki aşamada belirlenecek."),
    ("30A · Bölge rehberi", "https://30a.com/", "Genel",
     "Yerel içerik ve konu keşfi. Otomatik veri toplama henüz bağlı değil."),
]

STEPS = [
    ("sources", "Veri kaynakları", "Kaynak kütüphanesi", "active"),
    ("collect", "Veri toplama", "Plaj erişimleri hazır", "active"),
    ("quality", "Veri kontrolü", "Katalog kontrolü hazır", "partial"),
    ("research", "Konu araştırması", "Veriden konuya", "planned"),
    ("competitors", "Rakip analizi", "İçerik fırsatları", "planned"),
    ("brief", "İçerik briefi", "Kapsam ve kaynaklar", "planned"),
    ("article", "Makale", "Kaynaklı içerik", "planned"),
    ("visuals", "Görsel plan", "Sahne ve varlıklar", "planned"),
    ("video", "Video üretimi", "Kurgu ve render", "planned"),
    ("publish", "Yayın hazırlığı", "Son kontrol ve çıktı", "planned"),
]
