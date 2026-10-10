# M13 — Günlük ihtiyaç ve arabasız tatil ölçüleri

Tarih: 9 Ekim 2026 (GÖREV-10), güncelleme 10 Ekim 2026 (GÖREV-11) · Dal: `gorev-11-kanit-paketi` · Şema `14` · Toplayıcı `openstreetmap-daily-needs/1`

## Durum

GÖREV-10: toplayıcı, şema, arayüz ve testler; gerçek veritabanında ilk çekim (`docs/gorevler/GOREV-10/RAPOR.md`).

GÖREV-11: "Süpermarket ve market" kategorisi **büyük süpermarket** ve **yerel ve gurme market** diye ikiye ayrıldı; "acil sağlık" kategorisi **acil servis** ve **acil bakım (urgent care)** diye ikiye ayrıldı ve bu iki kategori yalnız resmî kaynakla doğrulanan noktaları sayar; eczane zincirleri (CVS, Walgreens) kontrol edildi. Sayılar ve mahalle ölçüleri `docs/gorevler/GOREV-11/RAPOR.md`, `gunluk-ihtiyac-mahalle.csv` ve `gunluk-ihtiyac-noktalar.csv` içinde.

## Amaç

"Arabasız bir 30A tatili mümkün mü, hangi mahallede?" sorusuna kanıt: konaklama ilanlarından en yakın büyük süpermarkete, yerel markete, eczaneye, acil servise, acil bakım merkezine, bisiklet kiralamaya ve halka açık plaj erişimine olan mesafe. Ölçüler **kuş uçuşudur** (iki nokta arasındaki büyük daire uzaklığı); yol, kaldırım, bisiklet yolu ya da yürüme süresi hesaplanmaz.

## Kaynaklar

- **OpenStreetMap, Overpass API üzerinden** (`https://overpass-api.de/api/interpreter`). Çekim başına **tek ve küçük bir sorgu** (bölge kutusu içinde yalnız yapılandırılmış etiketler, `out center tags`; iki kategorinin paylaştığı etiket seti sorguya bir kez girer). Ham yanıt `manifest.json` ile ve SHA-256'sıyla saklanır; OpenStreetMap veri tabanının yanıttaki zaman damgası (`timestamp_osm_base`) kaynak güncellenme zamanı olarak yazılır. © OpenStreetMap katkıcıları, ODbL.
- **Gözden geçirilmiş nokta dosyaları** (bir kişi kaynağın kendi sitesine bakar, sonucu dosyaya yazar):
  - `studio/destinations/thirty_a_chain_stores.csv` — **zincirlerin kendi mağaza bulucuları**, kaynak etiketi "zincirin kendi sitesi": büyük süpermarket zincirleri (Publix, Winn-Dixie, Walmart, Target, Whole Foods, The Fresh Market, Trader Joe's, Aldi) ve eczane zincirleri (CVS, Walgreens; Publix'in mağaza içi eczaneleri yalnız not).
  - `studio/destinations/thirty_a_health_points.csv` — **hastane sistemlerinin ve acil bakım zincirlerinin kendi konum sayfaları**, kaynak etiketi "kurumun kendi sitesi": Ascension Sacred Heart, HCA Florida, Emerald Coast Urgent Care ve diğerleri.
  - Sütunlar (ikisinde aynı): `kategori, zincir, magaza, adres, enlem, boylam, koordinat_kaynagi, magaza_url, kontrol_tarihi, durum, osm_id, not`. Durum: açık, kapalı, bölgede mağaza yok, okunamadı. `kategori` yapılandırmadaki bir kategori anahtarıdır (GÖREV-10 dosyası gibi sütunsuz bir dosyada markalı kategori varsayılır). Açık bir yerin adresi, koordinatı ve **koordinatın kaynağı** (sayfanın `latlon`/JSON-LD alanı ya da ABD Nüfus Bürosu adres servisi gibi) yazılır.
- **Halka açık plaj erişimleri:** ilçenin listesi (M2, son plaj erişimi çekimi, `beach_records`).
- **İlanlar:** son başarılı Book>Direct konaklama çekimindeki ilanlar ve koordinatları (`lodging_listings`); ilanın mahallesi Book>Direct konum filtresinden gelir (M10).
- **Restoran sayısı:** son restoran dizini çekiminde mahalle başına restoran sayısı (`restaurant_regions`). Restoranlar için koordinat üretilmez.

## Kategoriler (OpenStreetMap etiketleri)

| Anahtar | Etiket | OpenStreetMap etiketleri | Ek kural |
|---|---|---|---|
| `big_supermarket` | Büyük süpermarket | `shop=supermarket`, `shop=grocery` | marka listesi: adı, markası ya da işletmecisi listedeki bir zinciri bütün kelime olarak taşır |
| `local_market` | Yerel ve gurme market | `shop=supermarket`, `shop=grocery` | marka listesine girmeyen süpermarket ve marketler |
| `convenience` | Küçük market | `shop=convenience`, `shop=general` | — |
| `pharmacy` | Eczane | `amenity=pharmacy`, `healthcare=pharmacy` | — |
| `emergency` | Acil servis | `amenity=hospital`, `healthcare=hospital`, `amenity=clinic` + `emergency=yes`, `healthcare=emergency` | yalnız resmî kaynakla doğrulanan noktalar sayılır |
| `urgent_care` | Acil bakım (urgent care) | `healthcare=urgent_care`, `amenity=urgent_care`, `healthcare:speciality=urgent_care` | yalnız resmî kaynakla doğrulanan noktalar sayılır |
| `bike_rental` | Bisiklet kiralama | `amenity=bicycle_rental`, `shop=bicycle` + `service:bicycle:rental=yes` | — |

Bir nokta, etiket setlerinden birini tam taşıdığı (ve marka listesi varsa markası uyan) ilk kategoriye girer. **Büyük süpermarket marka listesi** destinasyon yapılandırmasındadır (30A: Publix, Walmart Supercenter ve Neighborhood Market, Winn-Dixie, Aldi, Target, The Fresh Market, Whole Foods, Trader Joe's); eşleme bütün kelimeyle yapılır ("Winn Dixie" ve "Winn-Dixie" aynı, "Targeted Foods" Target değil). Kategoriler, marka listesi ve "yalnız doğrulanmış" anahtarı `destination_poi_categories` içindedir (`brands`, `verified_only`); bölge kutusu `destination_poi_areas` içinde.

**30A bölgesi:** güney 30,20 · batı −86,40 · kuzey 30,45 · doğu −85,84. 30A kıyısı ve arkasındaki US-98 koridoru; iki uçtaki ilanların en yakın noktası kesilmesin diye batıda Miramar Beach'in doğu ucu, doğuda Panama City Beach'in batı ucu da alana dahil (en yakın nokta 30A dışında olabilir). Gözden geçirilmiş dosyadaki bir resmî nokta kutunun dışında olabilir; bu durumda notunda yazılır (30A: doğu mahallelerine en yakın resmî acil servis olabileceği için kutunun hemen güneydoğusundaki Ascension Sacred Heart Emergency Care – Panama City Beach eklendi).

## Gözden geçirilmiş dosyaların birleştirilmesi

- Açık görünen bir yer OpenStreetMap'te aynı kategoride, aynı marka ya da kurumla 400 m içinde (ya da dosyadaki `osm_id` ile) varsa sonuç "OpenStreetMap'te de var" ve noktaya "<kaynak> sitesinde doğrulandı (tarih)" notu düşülür. Kurum adı eşlemesi, noktanın markasında, adında ya da işletmecisinde (`operator`) kurum adının geçmesine ya da noktanın ilk kelimesinin kurum adında geçmesine bakar ("Sacred Heart Hospital …" ile "Ascension Sacred Heart").
- OpenStreetMap'te yoksa yer, dosyanın kaynak etiketiyle eklenir ("zincirin kendi sitesi" ya da "kurumun kendi sitesi"; adres, koordinat ve koordinatın kaynağı, sayfa, kontrol tarihi).
- OpenStreetMap'te olup kaynakta **kapalı** görünen yer raporlanır; noktaya not düşülür, silinmez.
- "Bölgede mağaza yok" ve "okunamadı" ayrı yazılır; okunamayan zincir ya da kurumun OpenStreetMap noktalarına "<kaynak> sitesi bu bilgisayardan doğrulanamadı (tarih)" notu düşülür.
- **Yalnız doğrulanmış kategoriler (acil servis, acil bakım):** resmî bir satırın doğrulamadığı OpenStreetMap noktası ölçülere girmez; kontrol tablosunda "OpenStreetMap'te var; resmî kaynakta doğrulanamadı" (`osm_dogrulanamadi`) diye yazılır.

## Ölçüler (okuma anında hesaplanır, ayrı tablo yok)

- Her ilan için her kategoride en yakın nokta ve uzaklığı (km, mil, metre), en yakın halka açık plaj erişimi.
- Mahalle başına: bu uzaklıkların **ortancası** ve **1 mil (1.609 m) içinde kalan ilanların payı**; ilan sayısı, ölçülebilen ilan sayısı (koordinatı olmayan ilan ölçülmez, sayısı ayrıca yazılır) ve restoran dizinindeki restoran sayısı.
- Etiket: "OpenStreetMap'e göre, kuş uçuşu (yol üzerinden değil)"; ortanca ve pay bizim hesabımızdır.
- **Plaj erişimi notu (etiketin parçası):** ölçü yalnız ilçenin halka açık erişim listesine göredir; Seaside, WaterColor, Alys Beach, Rosemary Beach gibi toplulukların kendi misafirlerine açık özel erişimleri dahil değildir.
- Eski bir çekim kendi kategori listesiyle (çekim anındaki) okunur; kategori ayrımından önceki çekimde "büyük süpermarket" gibi yeni bir kategori yoktur ve kanıt paketinde "veri yok" diye görünür.

## Şema (v13, v14)

`destination_poi_areas` (destinasyon başına bölge kutusu ve notu) · `destination_poi_categories` (anahtar, etiket, OpenStreetMap etiket setleri, sıra; v14: `brands` JSON listesi, `verified_only`) · `poi_snapshots` (çekim başına bölge, kategoriler, sorgu tarihi, OpenStreetMap zaman damgası, istek ve öğe sayısı) · `poi_points` (nokta, kategori, ad, marka, koordinat, kaynak: `openstreetmap`, `zincirin kendi sitesi` ya da v14 ile `kurumun kendi sitesi`, OpenStreetMap kimliği, etiketler, adres, sayfa, kontrol tarihi, not) · `poi_chain_checks` (gözden geçirilmiş satır başına sonuç; v14: `category_key` ve birincil anahtar `run_id, category_key, chain, store` — aynı zincir iki kategoride kontrol edilebilir; sonuçlara `osm_dogrulanamadi` eklendi). v13 → v14 geçişi eski çekimlerin satırlarını korur, eski kontrol satırlarına `supermarket` kategorisini yazar ve destinasyonun kategori yapılandırmasını profildeki yeni listeyle değiştirir (`studio/migration_v14.py`).

## Arayüz

Mahalleler sekmesinin altında: "Günlük ihtiyaç noktalarını topla" düğmesi, sürüm seçici ve ham Overpass yanıtının indirme bağlantısı; mahalle başına tablo (ilan, restoran sayısı ve her kategori için ortanca mil/metre ve 1 mil içindeki pay); kategori sekmeleriyle nokta listesi (ad, marka, adres, koordinat, kaynak bağlantısı: OpenStreetMap, zincirin ya da kurumun kendi sitesi); "Zincir ve kurum kontrolü" tablosu (zincir ya da kurum, yer, kategori, durum, sonuç). Her yerde "kuş uçuşu" etiketi.

## Mimari sınır

- **Generic (`studio/sources/daily_needs.py`):** Overpass sorgusu, kategori ve marka eşleme, ayrıştırma, gözden geçirilmiş dosyaların birleştirilmesi, yalnız doğrulanmış kategorilerin süzülmesi, mesafe ve mahalle ortancaları. 30A'ya özel hiçbir şey yok.
- **Destinasyona özel (`studio/destinations/thirty_a.py`):** bölge kutusu (`DAILY_NEEDS_AREA`), kategoriler ve büyük süpermarket marka listesi (`DAILY_NEEDS_CATEGORIES`, `BIG_SUPERMARKET_BRANDS`), gözden geçirilmiş dosyalar (`REVIEWED_POINT_FILES`: `CHAIN_STORE_CHECKS`, `HEALTH_POINTS`) ve kaynak tohumu. Yeni bir destinasyon kendi kutusunu, kategorilerini, markalarını ve dosyalarını getirir.

## Sınırlar

- OpenStreetMap gönüllülerin haritasıdır; bir noktanın olmaması işletmenin olmadığı anlamına gelmez, olan bir nokta da kapanmış olabilir. Süpermarketler ve eczaneler zincirlerin siteleriyle kısmen doğrulandı; bu bilgisayardan okunamayan siteler (Publix, Winn-Dixie, The Fresh Market, CVS: ABD dışı bağlantıya kapalı ya da engelli; HCA Florida: konum engeli) raporda.
- Acil servis ve acil bakım ölçüleri yalnız resmî sayfası okunan noktalara dayanır; resmî sayfası okunamayan bir acil servis (ör. HCA Florida Breakfast Point Emergency) ölçüde yoktur ve en yakın acil servis mesafesi bu yüzden olduğundan uzun görünebilir.
- Adres servisinden alınan koordinat (ABD Nüfus Bürosu adres aralığı eşlemesi) yaklaşıktır; notunda yazılır.
- Mesafe kuş uçuşudur; yol üzerinden mesafe, yürüme ya da bisiklet süresi değildir. "Yürüme mesafesi" denmez.
- Mahalle ölçüsü yalnız Book>Direct'te görünen ilanlara göredir (tarihli arama; tam envanter değil).

## Video dili

Kullanılabilir: "OpenStreetMap'e göre, Seaside'daki ilanların ortancası en yakın büyük süpermarkete kuş uçuşu yaklaşık X mil", "ilanların yüzde Y'si bir eczaneye kuş uçuşu bir milden yakın", "hastane sistemlerinin kendi sitelerinde listelenen en yakın acil servise kuş uçuşu ortanca X mil". Kullanılmaz: "markete yürüme mesafesi", "her yere bisikletle gidilir" gibi yol ve süre iddiaları; "en yakın hastane X dakika"; özel topluluk plaj erişimleri hakkında listede olmayan bilgi.
