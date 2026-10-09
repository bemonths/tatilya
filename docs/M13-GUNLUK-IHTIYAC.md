# M13 — Günlük ihtiyaç ve arabasız tatil ölçüleri

Tarih: 9 Ekim 2026 · Görev: GÖREV-10 · Dal: `gorev-10-aylik-gunluk` · Şema `13` · Toplayıcı `openstreetmap-daily-needs/1`

## Durum

Toplayıcı, şema, arayüz ve testler hazır. Önce work/ altında tek sorguluk canlı deneme, sonra geçici klasörde uygulama üzerinden deneme, en son tam yedekten sonra gerçek veritabanında çekim yapıldı; sayılar ve mahalle ölçüleri `docs/gorevler/GOREV-10/RAPOR.md`, `gunluk-ihtiyac-mahalle.csv` ve `gunluk-ihtiyac-noktalar.csv` içinde.

## Amaç

"Arabasız bir 30A tatili mümkün mü, hangi mahallede?" sorusuna kanıt: konaklama ilanlarından en yakın markete, eczaneye, acil sağlık noktasına, bisiklet kiralamaya ve halka açık plaj erişimine olan mesafe. Ölçüler **kuş uçuşudur** (iki nokta arasındaki büyük daire uzaklığı); yol, kaldırım, bisiklet yolu ya da yürüme süresi hesaplanmaz.

## Kaynaklar

- **OpenStreetMap, Overpass API üzerinden** (`https://overpass-api.de/api/interpreter`). Çekim başına **tek ve küçük bir sorgu** (bölge kutusu içinde yalnız yapılandırılmış etiketler, `out center tags`); Overpass'ın kullanım kurallarına uygun. Ham yanıt `manifest.json` ile ve SHA-256'sıyla saklanır; OpenStreetMap veri tabanının yanıttaki zaman damgası (`timestamp_osm_base`) kayda yazılır. Atıf arayüzde ve bu belgede: **© OpenStreetMap katkıcıları, ODbL**. Veritabanı yayımlanmaz.
- **Süpermarket zincirlerinin kendi mağaza bulucuları** (çapraz kontrol): Publix, Winn-Dixie, Walmart, Target, Whole Foods, The Fresh Market, Trader Joe's, Aldi. Bir kişi her zincirin sitesine bakar, sonucu gözden geçirilmiş dosyaya yazar (`studio/destinations/thirty_a_chain_stores.csv`: `zincir, magaza, adres, enlem, boylam, magaza_url, kontrol_tarihi, durum, osm_id, not`; durum: açık · kapalı · bölgede mağaza yok · okunamadı). Koordinat zincirin kendi sayfasındaki veriden gelir; adresten koordinat üretilmez.
- **Halka açık plaj erişimleri:** ilçenin listesi (M2, son plaj erişimi çekimi, `beach_records`).
- **İlanlar:** son başarılı Book>Direct konaklama çekimindeki ilanlar ve koordinatları (`lodging_listings`); ilanın mahallesi Book>Direct konum filtresinden gelir (M10).
- **Restoran sayısı:** son restoran dizini çekiminde mahalle başına restoran sayısı (`restaurant_regions`). Restoranlar için koordinat üretilmez.

## Kategoriler (OpenStreetMap etiketleri)

| Anahtar | Etiket | OpenStreetMap etiketleri |
|---|---|---|
| `supermarket` | Süpermarket ve market | `shop=supermarket`, `shop=grocery` |
| `convenience` | Küçük market | `shop=convenience`, `shop=general` |
| `pharmacy` | Eczane | `amenity=pharmacy`, `healthcare=pharmacy` |
| `urgent_care` | Acil sağlık | `amenity=hospital`, `healthcare=urgent_care`, `amenity=clinic` + `emergency=yes` |
| `bike_rental` | Bisiklet kiralama | `amenity=bicycle_rental`, `shop=bicycle` + `service:bicycle:rental=yes` |

Bir nokta, etiket setlerinden birini tam taşıdığı ilk kategoriye girer. Düğümün kendi koordinatı, alan ve ilişkilerin Overpass'ın verdiği merkezi kullanılır; koordinatsız öğe alınmaz. Kategoriler ve bölge kutusu destinasyon yapılandırmasındadır (`destination_poi_categories`, `destination_poi_areas`).

**30A bölgesi:** güney 30,20 · batı −86,40 · kuzey 30,45 · doğu −85,84. 30A kıyısı ve arkasındaki US-98 koridoru; iki uçtaki ilanların en yakın noktası kesilmesin diye batıda Miramar Beach'in doğu ucu, doğuda Panama City Beach'in batı ucu da alana dahil (en yakın nokta 30A dışında olabilir).

## Zincir çapraz kontrolü

- Zincirin sitesinde **açık** görünen mağaza OpenStreetMap'te aynı markayla 400 m içinde (ya da dosyadaki `osm_id` ile) varsa sonuç "OpenStreetMap'te de var".
- OpenStreetMap'te yoksa nokta **"zincirin kendi sitesi"** kaynağıyla süpermarket kategorisine eklenir (adres, koordinat, sayfa ve kontrol tarihiyle).
- OpenStreetMap'te olup zincirin sitesinde **kapalı** görünen mağaza raporlanır; noktaya not düşülür, silinmez.
- "Bölgede mağaza yok" ve "okunamadı" (site bu bilgisayardan liste vermedi, engel gösterdi) ayrı yazılır; okunamayan zincirin OpenStreetMap noktaları doğrulanmamış kalır.

## Ölçüler (okuma anında hesaplanır, ayrı tablo yok)

- Her ilan için her kategoride en yakın nokta ve uzaklığı (km, mil, metre), en yakın halka açık plaj erişimi.
- Mahalle başına: bu uzaklıkların **ortancası** ve **1 mil (1.609 m) içinde kalan ilanların payı**; ilan sayısı, ölçülebilen ilan sayısı (koordinatı olmayan ilan ölçülmez, sayısı ayrıca yazılır) ve restoran dizinindeki restoran sayısı.
- Etiket: "OpenStreetMap'e göre, kuş uçuşu (yol üzerinden değil)"; ortanca ve pay bizim hesabımızdır.
- **Plaj erişimi notu (etiketin parçası):** ölçü yalnız ilçenin halka açık erişim listesine göredir; Seaside, WaterColor, Alys Beach, Rosemary Beach gibi toplulukların kendi misafirlerine açık özel erişimleri dahil değildir.

## Şema (v13)

`destination_poi_areas` (destinasyon başına bölge kutusu ve notu) · `destination_poi_categories` (anahtar, etiket, OpenStreetMap etiket setleri, sıra) · `poi_snapshots` (çekim başına bölge, kategoriler, sorgu tarihi, OpenStreetMap zaman damgası, istek ve öğe sayısı) · `poi_points` (nokta, kategori, ad, marka, koordinat, kaynak: `openstreetmap` ya da `zincirin kendi sitesi`, OpenStreetMap türü/kimliği, saklanan etiketler, adres, kaynak bağlantısı, kontrol tarihi, not) · `poi_chain_checks` (zincir, mağaza, adres, koordinat, sayfa, kontrol tarihi, durum, eşleşen nokta, sonuç, not).

## Arayüz

Mahalleler sekmesinin altında: "Günlük ihtiyaç noktalarını topla" düğmesi, sürüm seçici ve ham Overpass yanıtının indirme bağlantısı; mahalle başına tablo (ilan, restoran sayısı ve her kategori için ortanca mil/metre ve 1 mil içindeki pay); kategori sekmeleriyle nokta listesi (ad, marka, adres, koordinat, kaynak bağlantısı); zincir mağaza kontrolü tablosu. Her yerde "kuş uçuşu" etiketi ve OpenStreetMap atfı.

## Mimari sınır

- **Generic (`studio/sources/daily_needs.py`):** Overpass sorgusu, kategori eşleme, ayrıştırma, zincir dosyası birleştirme, mesafe ve mahalle ortancaları. 30A'ya özel hiçbir şey yok.
- **Destinasyona özel (`studio/destinations/thirty_a.py`):** bölge kutusu (`DAILY_NEEDS_AREA`), kategoriler (`DAILY_NEEDS_CATEGORIES`), zincir kontrol dosyası (`CHAIN_STORE_CHECKS`) ve kaynak tohumu. Yeni bir destinasyon kendi kutusunu, kategorilerini ve zincir dosyasını getirir.

## Sınırlar

- OpenStreetMap gönüllülerin haritasıdır; bir noktanın olmaması işletmenin olmadığı anlamına gelmez, olan bir nokta da kapanmış olabilir. Süpermarketler zincirlerin siteleriyle kısmen doğrulandı (okunamayan zincirler raporda).
- Mesafe kuş uçuşudur; yol üzerinden mesafe, yürüme ya da bisiklet süresi değildir. "Yürüme mesafesi" denmez.
- Mahalle ölçüsü yalnız Book>Direct'te görünen ilanlara göredir (tarihli arama; tam envanter değil).
- Acil sağlık kategorisi `emergency=yes` etiketi olmayan klinikleri almaz; bir kliniğin acil hizmet verip vermediği OpenStreetMap'te yazmıyorsa bilinmez.

## Video dili

Kullanılabilir: "OpenStreetMap'e göre, Seaside'daki ilanların ortancası en yakın markete kuş uçuşu yaklaşık X mil", "ilanların yüzde Y'si bir eczaneye kuş uçuşu bir milden yakın". Kullanılmaz: "markete yürüme mesafesi", "her yere bisikletle gidilir" gibi yol ve süre iddiaları; özel topluluk plaj erişimleri hakkında listede olmayan bilgi.
