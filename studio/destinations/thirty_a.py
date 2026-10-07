"""First-install and migration defaults; SQLite owns runtime configuration."""
from pathlib import Path

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
    ("South Walton · Mahalleler", "https://www.visitsouthwalton.com/neighborhoods/", "Genel",
     "Visit South Walton mahalle dizini. 13 kanonik 30A mahallesinin kaynak kimliği, temsilî noktası, etiketleri ve tanıtım metinleri toplanır; Miramar Beach, Seascape ve Sandestin kapsam dışıdır. Metinler iç araştırma kanıtıdır, videoda aynen kullanılmaz.", "HTML"),
    ("NOAA NCEI · İklim normalleri 1991–2020", "https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals", "Hava",
     "Destinasyonun iklim istasyonları için 1991–2020 aylık normalleri: ortalama, en yüksek ve en düşük sıcaklık, yağış, yağışlı gün, sıcak ve donlu gün sayıları; bayraklarıyla. 30A için kıyı referansı Destin, iç kesim karşılaştırması DeFuniak Springs.", "API"),
    ("NOAA NDBC · Deniz suyu sıcaklığı", "https://www.ndbc.noaa.gov/", "Hava",
     "Yapılandırılmış istasyonun tarihî yıllık ölçüm dosyalarından aylık deniz suyu sıcaklığı ortalamaları (bizim hesabımız). 30A için PCBF1 (Panama City Beach).", "Dosya"),
    ("NOAA NHC · HURDAT2 kasırga izleri", "https://www.nhc.noaa.gov/data/", "Hava",
     "Atlantik best track dosyasından destinasyonun kıyı koridoruna yakın geçen tropikal siklonlar (bizim hesabımız): ilk giriş ayı, en yakın mesafe, daire içindeki en yüksek rüzgâr ve sınıf.", "Dosya"),
]

# Visit South Walton spells a few neighborhoods differently from the canonical regions.
# Only these exact spellings are accepted; names are never inferred from addresses or coordinates.
NEIGHBORHOOD_ALIASES = {"Blue Mountain": "Blue Mountain Beach", "Watercolor": "WaterColor", "Watersound": "WaterSound"}
# South Walton neighborhoods outside the 30A scope, as in the restaurant directory rule.
NEIGHBORHOOD_EXCLUDED = ("Miramar Beach", "Seascape", "Sandestin")

# Reviewed beach access -> neighborhood layer, generated once by tools/plaj_mahalle_esleme.py and
# committed; the app only reads it. Method and validation: docs/M7-MAHALLE-VERISI.md.
BEACH_NEIGHBORHOOD_MAPPING = Path(__file__).with_name("thirty_a_beach_neighborhoods.csv")
# Generator inputs (not read by the app): Walton County subdivision polygons queried per beach access,
# and the explicit subdivision name -> neighborhood table. Names that do not clearly name a neighborhood stay out.
COUNTY_SUBDIVISION_LAYER = "https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/ArcGIS/rest/services/EnerGov_Additional/FeatureServer/13"
BEACH_SUBDIVISIONS = Path(__file__).with_name("thirty_a_beach_subdivisions.csv")
SUBDIVISION_NEIGHBORHOODS = Path(__file__).with_name("thirty_a_subdivision_neighborhoods.csv")
# Manually verified reference facts (one per row, with source, quote and document SHA-256); read-only in the app.
REFERENCE_TABLE = Path(__file__).with_name("thirty_a_references.csv")
# South Walton monthly tourist development tax collections from the Walton County Clerk history workbook.
TDT_COLLECTIONS = Path(__file__).with_name("thirty_a_tdt_collections.csv")

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

# Climate configuration for the destination-independent climate connectors (copied into SQLite by migration v8).
# Distances: shortest great-circle distance to the 30A coastal corridor, i.e. the segment between the westernmost
# and easternmost beach accesses in the program (computed with studio.sources.geo.Segment, rounded to 0.1 km).
CLIMATE_DISTANCE_BASIS = "30A kıyı koridoruna (programdaki en batı ve en doğu plaj erişimi arasındaki doğru parçası) en kısa kuş uçuşu uzaklık"
CLIMATE_STATIONS = (
    {"station_key": "coastal", "kind": "normals", "station_id": "USW00053853", "label": "Destin–Fort Walton Beach Havalimanı",
     "role": "kıyı referansı", "latitude": 30.4, "longitude": -86.4717, "distance_km": 20.5, "first_year": None},
    {"station_key": "inland", "kind": "normals", "station_id": "USC00082220", "label": "DeFuniak Springs",
     "role": "iç kesim karşılaştırması", "latitude": 30.7244, "longitude": -86.0939, "distance_km": 44.1, "first_year": None},
    {"station_key": "water", "kind": "water_temperature", "station_id": "PCBF1", "label": "Panama City Beach (NOS 8729210)",
     "role": "deniz suyu sıcaklığı", "latitude": 30.213, "longitude": -85.88, "distance_km": 12.9, "first_year": 2005},
)
STORM_CORRIDOR = {
    "label": "30A kıyı koridoru",
    "west_latitude": 30.35548, "west_longitude": -86.2638, "west_reference": "Stallworth Preserve (5c81ab02f836f9166348e96c)",
    "east_latitude": 30.2713, "east_longitude": -85.99579, "east_reference": "Lupine - 1 (5c81a6a2f836f9166348e961)",
    "radii_nmi": (50, 100),
}
