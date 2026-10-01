"""First-install and migration defaults; SQLite owns runtime configuration."""
METADATA = {"id": "30a", "name": "30A", "subtitle": "South Walton, Florida"}
REGIONS = (
    ("dune-allen", "Dune Allen"), ("gulf-place", "Gulf Place"),
    ("santa-rosa-beach", "Santa Rosa Beach"), ("blue-mountain-beach", "Blue Mountain Beach"),
    ("grayton-beach", "Grayton Beach"), ("watercolor", "WaterColor"), ("seaside", "Seaside"),
    ("seagrove", "Seagrove"), ("watersound", "WaterSound"), ("seacrest", "Seacrest"),
    ("alys-beach", "Alys Beach"), ("rosemary-beach", "Rosemary Beach"), ("inlet-beach", "Inlet Beach"),
)

SEEDS = [
    ("Visit South Walton", "https://www.visitsouthwalton.com/", "Genel",
     "Bölge rehberi ve kaynak keşfi. South Walton kapsamındaki kayıtlar 30A için ayrıca filtrelenecek.", "Belirlenecek"),
    ("South Walton · Restoranlar", "https://www.visitsouthwalton.com/listings/culinary-experiences/", "Yeme içme",
     "Visit South Walton Dining dizinindeki 30A kapsamındaki restoranlar. Ad, mahalle, açıklama, adres, iletişim, cuisine, meals served ve kaynakta listelenen amenities toplanır. Menü ve fiyat verisi bu connector’ın kapsamında değildir.", "HTML"),
    ("South Walton · Plaj erişimleri", "https://www.visitsouthwalton.com/beach-bay-access-locations/", "Plaj",
     "Plaj erişim noktalarının adresi, koordinatları, erişim türü ve kaynakta listelenen olanakları. Veri toplama ekranında belirtilen kıyı kapsamı kullanılır.", "JSON"),
    ("South Walton · Etkinlikler", "https://www.visitsouthwalton.com/events/", "Etkinlik",
     "Etkinlik takvimi. Tarih, konum ve iptal değişikliklerinin takibi planlanıyor.", "Belirlenecek"),
    ("South Walton · Ulaşım", "https://www.visitsouthwalton.com/listings/transportation/", "Ulaşım",
     "Ulaşım işletmeleri. Fiyat ve hizmet kapsamı henüz toplanmadı.", "Belirlenecek"),
    ("National Weather Service", "https://www.weather.gov/", "Hava",
     "30A koridorundaki batı, orta ve doğu örnek noktaları için NWS tahminleri ve aktif hava uyarıları. Forecast, saatlik forecast ve aktif alert verileri api.weather.gov üzerinden toplanır.", "API"),
    ("30A · Bölge rehberi", "https://30a.com/", "Genel",
     "Yerel içerik ve konu keşfi. Otomatik veri toplama henüz bağlı değil.", "Belirlenecek"),
]

ANCHOR_PROVENANCE = {
    "source_url": "https://www.visitsouthwalton.com/beach-bay-access-locations/",
    "selection": "53 kıyı erişim kaydının boylam sıralamasından batı / orta / doğu örnekleri",
    "scope": "30A koridoru için hava örnek noktaları; canonical mahalle merkezleri değildir.",
}
ANCHORS = (
    {"anchor_key": "west", "label": "Batı 30A", "source_beach_name": "Stallworth Preserve",
     "source_beach_external_id": "5c81ab02f836f9166348e96c", "latitude": 30.35548, "longitude": -86.2638},
    {"anchor_key": "central", "label": "Orta 30A", "source_beach_name": "Holly - 24",
     "source_beach_external_id": "5c81a5acf836f90dc03cccca", "latitude": 30.3167, "longitude": -86.12845},
    {"anchor_key": "east", "label": "Doğu 30A", "source_beach_name": "Lupine - 1",
     "source_beach_external_id": "5c81a6a2f836f9166348e961", "latitude": 30.2713, "longitude": -85.99579},
)
