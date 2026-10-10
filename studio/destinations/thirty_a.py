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
    ("South Walton · Konaklama (Book>Direct)", "https://visitsouthwalton.bookdirect.net/", "Konaklama",
     "Visit South Walton'ın resmî Stay ön yüzünün kullandığı Book>Direct aramaları: yapılandırılmış tarih pencerelerinde her mahalle filtresinde görünen ilanlar, türleri, büyüklükleri ve kaynağın verdiği fiyat alanları; ilan başına aylık fiyat takvimi özeti. Tarihli arama anlık görüntüsüdür, tam envanter değildir.", "JSON"),
    ("Restoranlar · İşletme siteleri", "https://www.visitsouthwalton.com/listings/culinary-experiences/?kaynak=isletme-siteleri", "Yeme içme",
     "Son restoran dizini çekimindeki restoranların kendi siteleri (ve yayımladıkları menü/sipariş platformu sayfaları): site durumu, menüler ve "
     "menü fiyatları, çalışma saatleri, rezervasyon, çocuk menüsü, açık hava oturma, manzara ve köpek kabulü; her değer kaynak url'si, erişim "
     "zamanı ve ham kopyanın SHA-256'sıyla. Yorum ve puan platformları kullanılmaz; sitenin söylemediği bilgi bilinmiyor kalır.", "HTML"),
    ("Kiralama şirketleri · Konaklama fiyatları", "https://visitsouthwalton.bookdirect.net/?kaynak=kiralama-sirketleri", "Konaklama",
     "Son Book>Direct çekimindeki ilanların şirket bağlantısıyla, yapılandırılmış kiralama şirketlerinin kendi sitelerinde her tarih penceresi için sorulan müsaitlik ve fiyat: kira, temizlik ve diğer ücretler, vergiler, genel toplam, en az gece ve giriş günü kuralı (site hangilerini gösteriyorsa). Eşleme yalnız bağlantıyla yapılır; tam envanter değildir.", "HTML"),
    ("OpenStreetMap · Günlük ihtiyaç noktaları", "https://www.openstreetmap.org/?kaynak=gunluk-ihtiyac", "Genel",
     "OpenStreetMap'te (Overpass API) destinasyonun alanındaki süpermarket ve marketler, küçük marketler, eczaneler, acil sağlık noktaları ve "
     "bisiklet kiralama noktaları; süpermarketler zincirlerin kendi mağaza bulucularıyla gözden geçirilir. Kiralık evlerden kuş uçuşu "
     "mesafeler okuma anında hesaplanır. © OpenStreetMap katkıcıları, ODbL.", "API"),
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
# Turkish statement of every reference row (the table's statements are English, for the video); read by the evidence pack.
REFERENCE_TRANSLATIONS = Path(__file__).with_name("thirty_a_references_tr.csv")
# Evidence-pack templates of this destination (one JSON file per template; format in docs/M14-KANIT-PAKETI.md).
EVIDENCE_TEMPLATES = Path(__file__).with_name("thirty_a_evidence")
# FDOT 2025 AADT of the CR 30A and US 98 count sites and Walton weekly seasonal factors (monthly ratios are our calculation); the same
# source columns as the reference table, one fact per row.
TRAFFIC_TABLE = Path(__file__).with_name("thirty_a_traffic.csv")
# South Walton monthly tourist development tax collections from the Walton County Clerk history workbook.
TDT_COLLECTIONS = Path(__file__).with_name("thirty_a_tdt_collections.csv")
# The channel Claude's steps work for (GÖREV-13; docs/M15-CLAUDE-ADIMLARI.md): instruction files (common first), the channel plan (the
# concept document with its content families), the channel research, the content families of the plan (the schema's fixed list), the name of
# "the whole destination" as a region, and the templates the title step builds its data summaries with.
CLAUDE_INSTRUCTIONS = Path(__file__).with_name("thirty_a_claude")
CHANNEL = {
    "plan": Path(__file__).resolve().parents[2] / "docs" / "KONSEPT.md",
    "research": CLAUDE_INSTRUCTIONS / "kanal_arastirmasi.md",
    "families": ("Bölgesel derin rehberler", "Genel planlama", "Sezon ve zamanlama", "Masraf ve bütçe", "Deneyim", "Sorun çözen videolar",
                 "Karşılaştırmalar", "Kendi tarihsel verimizden videolar"),
    "whole_region": "30A geneli",
    "general_template": "ilk-video",
    "region_template": "mahalle-rehberi",
    "region_parameter": "mahalle",
    # GÖREV-14 (Adım 4e): the starting values of Settings → title suffix; the program writes the current ones into every run's secim.md.
    "title_suffix": {"en": " | 30A Florida Vacation", "tr": " | 30A Florida Tatili"},
}

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
# Lodging search snapshots (generic Book>Direct connector; copied into SQLite by migration v10).
# Location filters are matched by their exact names in the clone's show.json; "Seagrove Beach" is a separate filter in the
# source and is also tied to Seagrove (each search row keeps the filter it came from). Other filters stay out of scope.
LODGING_CLONE_HOST = "visitsouthwalton.bookdirect.net"
LODGING_LOCATIONS = {
    "Dune Allen": "dune-allen", "Gulf Place": "gulf-place", "Santa Rosa Beach": "santa-rosa-beach",
    "Blue Mountain Beach": "blue-mountain-beach", "Grayton Beach": "grayton-beach", "Watercolor": "watercolor",
    "Seaside": "seaside", "Seagrove": "seagrove", "Seagrove Beach": "seagrove", "Watersound": "watersound",
    "Seacrest": "seacrest", "Alys Beach": "alys-beach", "Rosemary Beach": "rosemary-beach", "Inlet Beach": "inlet-beach",
}
# Saturday to Saturday, 7 nights (a common vacation-rental pattern; an assumption, not a source fact). Past windows are skipped.
LODGING_WINDOWS = (
    ("fall-2026", "Sonbahar 2026", "2026-10-17", "2026-10-24"),
    ("winter-2027", "Kış 2027", "2027-01-16", "2027-01-23"),
    ("spring-break-2027", "Bahar tatili 2027", "2027-03-13", "2027-03-20"),
    ("summer-2027", "Yaz 2027", "2027-07-10", "2027-07-17"),
)
# Rental company sites asked for prices by the generic agency rate collector (copied into SQLite by migration v11), as
# (domain, company name as the site shows it, platform adapter). Only companies whose Book>Direct links reach listing pages on a
# platform with a working public price display are listed; discovery and the companies left out: docs/gorevler/GOREV-08/AJANS-KESFI.md.
AGENCY_SITES = (
    ("benchmark30a.com", "Benchmark Management", "rescms"),
    ("30aescapes.com", "30A Escapes", "track"),
    ("rosemarybeach.com", "Rosemary Beach®", "streamline"),
    ("beautifulbeach.com", "Dune Allen Realty Vacation Rentals", "vr_router"),
    ("panhandlegetaways.com", "Panhandle Getaways", "track"),
    ("dunevacationrentals.com", "Dune Vacation Rentals", "streamline"),
    ("graytoncoastrentals.com", "Grayton Coast Rentals", "rescms"),
    ("30acottagesandconcierge.com", "30A Cottages", "rescms"),
    ("myvacationhaven.com", "My Vacation Haven", "rescms"),
)
# Added by migration v12 (agency-lodging-rates/2): new companies and per-company options. aliases: other domains the company's
# links redirect to; protected: read only through the visible browser, 6 s apart, stopping at the first refusal; guest_rule:
# two_adults or bedrooms_x2 (GÖREV-09 guest count check); inventory: the company's own listing list for address/location
# matching ("platform": the platform's list service at origin; "sitemap": listing pages named by the sitemap); own_region_id +
# own_city: the official rental program of one community, whose site names the community in its own listing data.
# Discovery and the companies left out: docs/gorevler/GOREV-09/AJANS-KESFI-2.md.
AGENCY_SITES_V12 = (
    ("homeownerscollection.com", "Homeowner's Collection", "rescms"),
    ("southernresorts.com", "Southern Vacation Rentals", "property_quote"),
    ("oceanreefresorts.com", "Ocean Reef Resorts", "track"),
    ("oversee.us", "Oversee", "vrp"),
    ("paradise30a.com", "Paradise Properties", "vr_router"),
    ("grayt30avacations.com", "Grayt 30A Vacations / Royal Destinations", "rescms"),
    ("30a-vacay.com", "30A Vacay", "vr_router"),
    ("sandersbeachrentals.com", "Sanders Beach Rentals", "rescms"),
    ("funvacay.com", "FunVacay", "rescms"),
    ("exclusive30a.com", "Exclusive 30A", "exceptional_stay"),
    ("yourfriendatthebeach.com", "Your Friend at the Beach", "qvr"),
    ("30abeachstays.com", "30A Beach Stays", "wander"),
    ("destinvacation.com", "Newman-Dailey Resort Properties", "asmx_quote"),
    ("coastalbluevacations.com", "Coastal Blue Vacations", "rescms"),
    ("alysbeach.com", "Alys Beach Vacation Rentals", "vrp"),
)
AGENCY_SITE_OPTIONS = {
    "oversee.us": {"protected": 1, "inventory": {"source": "platform", "origin": "https://oversee.us"}},
    "exclusive30a.com": {"protected": 1},
    "grayt30avacations.com": {"aliases": ["royaldestinations.com"],
                              "inventory": {"source": "sitemap", "url": "https://www.royaldestinations.com/sitemap.xml",
                                            "pattern": r"/30a-vacation-rentals/[^/]+$"}},
    "30a-vacay.com": {"inventory": {"source": "sitemap", "url": "https://www.30a-vacay.com/sitemap.xml", "pattern": r"/vacation-rentals/rental/[^/]+/?$"}},
    "rosemarybeach.com": {"inventory": {"source": "platform", "origin": "https://rosemarybeach.com"}},
    "dunevacationrentals.com": {"inventory": {"source": "platform", "origin": "https://dunevacationrentals.com"}},
    "alysbeach.com": {"inventory": {"source": "platform", "origin": "https://vacation.alysbeach.com"}, "own_region_id": "alys-beach",
                      "own_city": "Alys Beach"},
}
# Reviewed files read by the restaurant-sites collector (GÖREV-09): the official site found by a web search for restaurants whose
# directory entry has no working website (accepted only when the site shows the same address or phone), and menu items read by a
# person from image menus or text-less PDFs, each tied to the document's SHA-256.
RESTAURANT_SITE_OVERRIDES = Path(__file__).with_name("thirty_a_restaurant_sites.csv")
MENU_READINGS = Path(__file__).with_name("thirty_a_menu_readings.csv")
# GÖREV-10: classes a reviewer gave single menu items (main dishes under $8 checked one by one: add-ons, nigiri pieces, bento choices,
# page lines that are not dishes), keyed by restaurant, item name and (optionally) price text.
MENU_ITEM_CLASSES = Path(__file__).with_name("thirty_a_menu_item_classes.csv")
# Added by migration v12: the seasonal fall window (Fall 2026 became a last-minute window once queried in October 2026).
LODGING_WINDOWS_V12 = (("fall-2027", "Sonbahar 2027", "2027-10-16", "2027-10-23"),)
STORM_CORRIDOR = {
    "label": "30A kıyı koridoru",
    "west_latitude": 30.35548, "west_longitude": -86.2638, "west_reference": "Stallworth Preserve (5c81ab02f836f9166348e96c)",
    "east_latitude": 30.2713, "east_longitude": -85.99579, "east_reference": "Lupine - 1 (5c81a6a2f836f9166348e961)",
    "radii_nmi": (50, 100),
}

# GÖREV-10 (migration v13). Lodging price windows: for each of the 12 months after the run month, the Saturday-to-Saturday week that
# contains the 15th (7 nights); a week starting fewer than 21 days after the run date is skipped and the 13th month added. An
# assumption of ours (a common vacation-rental pattern), not a source fact.
LODGING_WINDOW_RULE = {"kind": "monthly", "months": 12, "anchor_day": 15, "weekday": 5, "nights": 7, "min_lead_days": 21}
# Suggested refresh interval per collector in months (the home screen shows which are due; nothing runs by itself).
REFRESH_INTERVALS = (("bookdirect-lodging", 1), ("agency-lodging-rates", 1), ("south-walton-restaurants", 3), ("restaurant-sites", 3))
# Daily-need points (generic OpenStreetMap collector): the 30A coast and the US-98 corridor behind it, widened to the east end of
# Miramar Beach and the west end of Panama City Beach so the nearest store of a listing near either end of 30A is not cut off.
DAILY_NEEDS_AREA = {"south": 30.20, "west": -86.40, "north": 30.45, "east": -85.84,
                    "note": "30A kıyısı ve arkasındaki US-98 koridoru; 30A'nın iki ucundaki ilanların en yakın noktası kesilmesin diye batıda "
                            "Miramar Beach'in doğu ucu, doğuda Panama City Beach'in batı ucu da alana dahil (en yakın nokta 30A dışında olabilir)."}
# Supermarket chains whose stores count as "big supermarkets" (GÖREV-11 decision): a store whose brand or name carries one of these
# names is a big supermarket, every other supermarket or grocery store a local or gourmet market. Matching is by whole words.
BIG_SUPERMARKET_BRANDS = ["Publix", "Walmart", "Winn-Dixie", "Aldi", "Target", "The Fresh Market", "Fresh Market", "Whole Foods", "Trader Joe's"]
# OpenStreetMap tags of each category: a point belongs to the first category one of whose tag sets it carries in full (and, when the
# category lists brands, whose brand or name carries one of them). verified_only: an OpenStreetMap point of the category counts only
# when a reviewed official source confirms it (GÖREV-11: emergency and urgent care, from hospital systems' and urgent-care chains'
# own location pages).
DAILY_NEEDS_CATEGORIES = (
    ("big_supermarket", "Büyük süpermarket", [{"shop": "supermarket"}, {"shop": "grocery"}], {"brands": BIG_SUPERMARKET_BRANDS}),
    ("local_market", "Yerel ve gurme market", [{"shop": "supermarket"}, {"shop": "grocery"}], {}),
    ("convenience", "Küçük market", [{"shop": "convenience"}, {"shop": "general"}], {}),
    ("pharmacy", "Eczane", [{"amenity": "pharmacy"}, {"healthcare": "pharmacy"}], {}),
    ("emergency", "Acil servis", [{"amenity": "hospital"}, {"healthcare": "hospital"}, {"amenity": "clinic", "emergency": "yes"},
                                  {"healthcare": "emergency"}], {"verified_only": True}),
    ("urgent_care", "Acil bakım (urgent care)", [{"healthcare": "urgent_care"}, {"amenity": "urgent_care"},
                                                 {"healthcare:speciality": "urgent_care"}], {"verified_only": True}),
    ("bike_rental", "Bisiklet kiralama", [{"amenity": "bicycle_rental"}, {"shop": "bicycle", "service:bicycle:rental": "yes"}], {}),
)
# Reviewed files of points checked by a person on the owners' own sites (category column `kategori`): supermarket and pharmacy chains'
# store locators (GÖREV-10, GÖREV-11) and hospital systems' and urgent-care chains' location pages (GÖREV-11). A point OpenStreetMap does
# not have is added with the file's source label.
CHAIN_STORE_CHECKS = Path(__file__).with_name("thirty_a_chain_stores.csv")
HEALTH_POINTS = Path(__file__).with_name("thirty_a_health_points.csv")
REVIEWED_POINT_FILES = ((CHAIN_STORE_CHECKS, "zincirin kendi sitesi"), (HEALTH_POINTS, "kurumun kendi sitesi"))
