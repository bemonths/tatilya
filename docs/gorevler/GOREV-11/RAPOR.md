# GÖREV-11 Raporu — kanıt paketi, günlük ihtiyaç düzeltmeleri ve referans tablosu

Tarih: 10 Ekim 2026 · Dal: `gorev-11-kanit-paketi` · Uygulama `0.14.0` · Şema `14`

## Kısa özet

- v0.13.0 main'e alındı ve etiketlendi; main ve etiket CI başarılı.
- Günlük ihtiyaçta süpermarketler "büyük süpermarket" ve "yerel ve gurme market" diye ayrıldı; acil servis ve acil bakım artık yalnız hastane sistemlerinin ve acil bakım zincirlerinin kendi sitelerinde doğrulanan noktaları sayıyor.
- Referans tablosuna 47 satır eklendi (152 satır): plaj erişimi hukuku, erişilebilirlik, ziyaretçi kökeni ve okul tatilleri, etkinlikler, tarihçe ve iki genel satır. Ayrıca FDOT trafik tablosu.
- Kanıt paketi yapıldı: şablondan Markdown + JSON, her satırda kaynak, etiket ve kullanım notu, "veri yok" satırları, sonunda sayı kontrol listesi; uygulamada "Kanıt paketi" ekranı. İki paket gerçek veriyle üretildi.
- Gerçek veritabanı tam yedekten sonra uygulamanın normal kullanımıyla şema 14'e geçti; bütünlük ve ilişki kontrolleri temiz.

## Adım 1 — v0.13.0

- GÖREV-10 dalının son commit'i `4187c1c` için CI başarılıydı (çalıştırma 38018479836).
- `main` → `4187c1cb1b4b07650bb0c34b2122ec6ec9f20f6c` (fast-forward), push edildi.
- Açıklamalı etiket `v0.13.0` → aynı commit: "v0.13.0 — aylık konaklama fiyatları, güncelleme göstergesi, günlük ihtiyaç ölçüleri ve restoran gözden geçirmesi"; push edildi.
- main CI: 38048064609 başarılı. Etiket CI: 38048065961 başarılı.
- `gorev-11-kanit-paketi` dalı açıldı.

## Adım 2 — Günlük ihtiyaç düzeltmeleri

**Yöneticinin bu adımdaki kararları uygulandı:** order.online ve realjoy kapsam dışı; ~9 saatlik toplu çalıştırma kabul (README'deki düğme açıklamasına "uzun sürer (GÖREV-10'daki ölçüme göre yaklaşık 9 saat); akşam başlatmak uygundur" eklendi); Publix, Winn-Dixie ve The Fresh Market OpenStreetMap noktaları "<zincir> sitesi bu bilgisayardan doğrulanamadı" notuyla kalıyor; Blue Mountain Bakery için yalnız yeni menü (bu görevde restoran çekimi yapılmadı).

### 2a. Süpermarket ayrımı

- Kategoriler: büyük süpermarket (marka listesi destinasyon yapılandırmasında: Publix, Walmart Supercenter ve Neighborhood Market, Winn-Dixie, Aldi, Target, The Fresh Market, Whole Foods, Trader Joe's; adı, markası ya da işletmecisi bütün kelime olarak eşlenir), yerel ve gurme market (geri kalan süpermarket ve marketler). Kod genel; marka listesi 30A profilinde.
- Gerçek veride (10 Ekim 2026 çekimi): 12 büyük süpermarket OpenStreetMap'ten + Target Pier Park zincirin sitesinden; 4 yerel market (Modica Market, For The Health Of It, Seacrest Sundries, Carousel Supermarket & Liquor Store).

**Büyük süpermarkete kuş uçuşu mesafe (ilanların ortancası, mil) ve 1 mil içindeki ilan payı:**

| Mahalle | Büyük süpermarket | 1 mil içinde | Yerel market |
|---|---|---|---|
| Dune Allen | 2,36 | %0 | 2,85 |
| Gulf Place | 2,16 | %0 | 1,72 |
| Santa Rosa Beach | 2,07 | %16 | 1,49 |
| Blue Mountain Beach | 2,45 | %0 | 0,29 |
| Grayton Beach | 2,51 | %1 | 1,79 |
| WaterColor | 0,64 | %70 | 0,53 |
| Seaside | 0,86 | %86 | 0,15 |
| Seagrove | 1,32 | %26 | 1,46 |
| WaterSound | 2,54 | %1 | 3,18 |
| Seacrest | 1,25 | %19 | 0,44 |
| Alys Beach | 1,10 | %14 | 0,75 |
| Rosemary Beach | 1,36 | %1 | 0,25 |
| Inlet Beach | 1,65 | %0 | 0,75 |

(Kaynak: OpenStreetMap, kuş uçuşu; ortanca ve pay bizim hesabımız. Tam tablo `gunluk-ihtiyac-mahalle.csv`.)

### 2b. Acil sağlık — resmî noktalar ve OpenStreetMap ile farkları

Kategoriler "acil servis" ve "acil bakım (urgent care)" oldu; ikisi de yalnız resmî kaynakla doğrulanan noktayı sayar. Resmî noktalar gözden geçirilmiş dosyada (`studio/destinations/thirty_a_health_points.csv`: kaynak url, kontrol tarihi, adres, koordinat ve koordinatın kaynağı). Ham sayfalar `work/gorev-11/kaynaklar/` altında SHA-256 ile.

| Kategori | Yer | Kaynak | Koordinatın kaynağı | OpenStreetMap ile |
|---|---|---|---|---|
| Acil servis | Ascension Sacred Heart Emergency Care – Emerald Coast, 7800 US 98, Miramar Beach | Ascension'ın konum sayfası | sayfadaki `latlon` | OSM'deki "Sacred Heart Hospital on the Emerald Coast" ile aynı (doğrulandı) |
| Acil servis | Ascension Sacred Heart Emergency Care – Panama City Beach, 11111 Panama City Beach Pkwy | Ascension'ın konum sayfası | sayfadaki `latlon` | OSM'de yok; eklendi (bölge kutusunun hemen dışında, aşağıya bakın) |
| Acil bakım | Ascension Sacred Heart Primary Care & Urgent Care – South Walton, 5551 US 98, Santa Rosa Beach | Ascension'ın konum sayfası (+ Mart 2026 duyurusu) | sayfadaki `latlon` | OSM'de yok; eklendi |
| Acil bakım | Emerald Coast Urgent Care Inlet Beach, 13625 US-98 Suite 8-9 | şirketin kendi sayfası | ABD Nüfus Bürosu adres servisi (yaklaşık) | OSM'de yok; eklendi |
| Acil bakım | Emerald Coast Urgent Care "Destin", 12598 Emerald Coast Pkwy (posta kodu Miramar Beach) | şirketin kendi sayfası | ABD Nüfus Bürosu adres servisi (yaklaşık) | OSM'de yok; eklendi |

- OpenStreetMap'in GÖREV-10'daki 2 noktasından biri (Sacred Heart Emerald Coast) doğrulandı; diğeri (adsız `amenity=hospital`, way/1140748455, Miramar Beach'in batı ucu) hiçbir resmî kaynakta doğrulanamadı ve ölçüye girmedi (tabloda "OpenStreetMap'te var; resmî kaynakta doğrulanamadı").
- Okunamayanlar: **HCA Florida** sitesi bu bilgisayarın konumuna kapalı ("Page is not available to your current location"; doğrudan istek ve tarayıcı aynı); haberlere göre (ikincil) Breakfast Point Emergency (9318 Panama City Beach Pkwy) ve Destin Emergency var ama resmî sayfa okunamadığı için eklenmedi. **Doc Smiley's Urgent Care** (Seagrove) kendi sitesi bulunamadı; eklenmedi.
- Sonuç: en yakın acil servis mesafesi batıda 3,9–6,8 mil, doğuda 13–15 mil (ilanların ortancası, kuş uçuşu). HCA Breakfast Point okunamadığı için doğu mahallelerinde gerçek en yakın acil servis daha yakın olabilir.

### 2c. Eczaneler

- **Walgreens:** kendi mağaza arama servisi bölge kutusunda mağaza vermedi (en yakınlar Destin ve Panama City Beach'te, kutunun dışında) → "bölgede mağaza yok".
- **CVS:** site ABD dışından erişime kapalı (bilgisayardaki Chrome'da da "not available outside the United States") → "okunamadı"; OpenStreetMap'teki 3 CVS noktası doğrulanmadan kaldı.
- **Publix mağaza içi eczaneleri:** not olarak kaldı (sitesi okunamıyor; OpenStreetMap'te ayrı eczane noktası değil).

### Kod ve şema

- Şema 14 (`studio/migration_v14.py`): kategori yapılandırmasına marka listesi ve "yalnız doğrulanmış" anahtarı; nokta kaynağına "kurumun kendi sitesi"; kontrol satırlarına kategori (birincil anahtara girdi; aynı zincir iki kategoride kontrol edilebilir) ve "osm_dogrulanamadi" sonucu; kanıt paketleri tablosu `evidence_packs`.
- Arayüz: "Zincir ve kurum kontrolü" tablosu, kategori adları. Belge: `docs/M13-GUNLUK-IHTIYAC.md`.

## Adım 3 — Referans tablosu

Tablo 105 → 152 satır (`referans-tablosu.csv`; yeni satırlar Türkçe ifadeleriyle `referans-tablosu-yeni-satirlar.csv`). Her satır mevcut sütunlarla: İngilizce ifade, kısa alıntı, belge ve erişim tarihi, SHA-256, güven, durum, yeniden kontrol tarihi. Yeni konular: plaj-hukuku, erisilebilirlik, kalabalik, etkinlikler, tarihce; yeni kapsamlar: ABD, Okul bölgesi. Doğrulayıcı temiz (sorun yok).

### 3a. Plaj erişimi hukuku (birincil ve resmî kaynaklar)

- Florida Anayasası Madde X Bölüm 11: ortalama yüksek su çizgisinin altındaki kumsal devletin, halk adına.
- Walton County 2016-23 sayılı kararı (25 Ekim 2016 kabul, 1 Nisan 2017 yürürlük): kuru kumda halkın eski kullanımı (customary use) korundu, 15 ft tampon. (Belge taranmış görüntüydü; sayfaları görüntü olarak okundu.)
- 2018 kanunu (HB 631, Ch. 2018-94, s. 163.035): yerel yönetim customary use kuralını ancak mahkeme parsel parsel onaylarsa sürdürebilir.
- Dava: Aralık 2018'de ilçe 1.194 mülk için dava açtı; dava duruşmaya gitmedi, itiraz eden sahipler ya davadan çıktı ya da 20 ft geçiş alanı veren uzlaşma yaptı; mahkeme yalnız itiraz etmeyen 95 parselde customary use kabul etti (14 Şubat 2024 kararı; Florida Senatosu'nun resmî kanun analizinden).
- **2025:** Ch. 2025-178 (SB 1622), 24 Haziran 2025'te vali onayıyla 163.035'i kaldırdı; aynı kanun bazı Gulf ilçelerinde erozyon kontrol çizgisini ortalama yüksek su çizgisi yaptı.
- **2026:** 1. Bölge Temyiz Mahkemesi 18 Şubat 2026'da sahiplerin başvurusunu reddetti; taraflar kabul etti, mahkeme de katıldı: kanun kaldırıldığı için 2024 kararı hükümsüz ve hukuki etkisi yok. İlçe aynı davada 2017 kararının artık yürürlükte olmadığını, isterse yeni bir karar çıkarabileceğini söyledi. İlçe katipliğinin 2026-01…2026-10 kararları arasında customary use kararı yok (10 Ekim 2026'da kontrol).
- **Bugünkü durum (bu kaynaklara göre):** ıslak kum halka açık; kuru kumun bir kısmı özel; Şubat 2026 itibarıyla ne 2017 ilçe kararı ne de 2024 mahkeme kararı yürürlükte. İlçe turizm dairesinin "uzlaşan parsellerde 20 ft geçiş alanı" ifadesi tarihsiz ve 2026 kararıyla çelişebilir → "çelişkili" işaretlendi.
- **"Yeni bir yasa imzalandı, özel plaj kalmadı" iddiası:** ilk yarısı doğru (24 Haziran 2025'te kanun imzalandı); ikinci yarısını destekleyen birincil kaynak yok — kanun kuru kumu halka açmıyor. Satır **"doğrulanamadı"**; videoda "özel plaj kalmadı" denemez.
- Video için tek satırlık özet satırı eklendi (`hukuk-video-ozet`, "türetilmiş"): "Walton County'de ıslak kum halka açıktır, kuru kumun bir kısmı özel mülktür; Şubat 2026 itibarıyla ne ilçenin 2017 kararı ne de 2024 mahkeme kararı yürürlüktedir; plaja gidenler halka açık erişimleri kullanmalıdır."

### 3b. Erişilebilirlik

- Ücretsiz plaj tekerlekli sandalyesi (South Walton İtfaiye Bölgesi aracılığıyla, 1 Mart–31 Ekim, 10:30–17:30); yerleri Miramar Beach, Ed Walline, Santa Clara, Inlet Beach kuleleri.
- ADA'ya uygun 6 bölgesel erişim (Visit South Walton) — aynı kurumun başka sayfası 11 bölgesel erişim diyor, "çelişkili".
- Ed Walline'da erişim matları (5 × 120 ft, 2017 bülteni).
- **53 erişimimizle eşleme:** ilçenin listesi zaten olanakları taşıyor. Tekerlekli sandalye yazılı erişimler bizde 3 (Ed Walline, Santa Clara, Inlet Beach) — sayfadaki 4 yerden 3'ü eşleşti, Miramar Beach 30A dışında. ADA listesindeki 6 erişimden 5'i bizde var (Fort Panic, Dune Allen, Ed Walline, Santa Clara, Inlet Beach); ilçe listesinde ayrıca Blue Mountain, Gulfview Heights ve Seagrove'da ADA olanağı yazıyor.

### 3c. Trafik (FDOT)

- `trafik-fdot-2025.csv` (repoda `studio/destinations/thirty_a_traffic.csv`): FDOT 2025 AADT raporundan CR 30A'nın 7 ve US 98'in 9 sayım noktası (ör. CR 30A batı ucu 8.300, Seaside doğusu 14.000; US 98 30A batı ucu yakını 50.000 araç/gün) ve 2025 mevsim faktörü raporundaki 4 Walton kategorisi.
- FDOT yalnız haftalık mevsim faktörü yayımlıyor; **aylık oranlar bizim hesabımız** (ör. "Walton, US98" kategorisinde Temmuz ≈ yıllık ortalamanın 1,10 katı, Ocak ≈ 0,85). Raporda sayım noktasının hangi kategoriye bağlı olduğu yazmıyor.
- FDOT yol envanterinde 30A "W/E CO HWY 30A" (ilçe yolu, kilometre taşı uzunluğu 18,561 mil) — `genel-30a-ilce-yolu`.

### 3d. Kalabalık haftaları

- Walton County Tourism 2025 ziyaretçi çalışması (Downs & St. Germain, 2.655 anket): ilk 5 pazar Atlanta %11,1, Nashville %7,5, Dallas–Fort Worth %4,8, Birmingham %4,0, Houston %3,6.
- 2026–27 resmî takvimler (okul bölgelerinin kendi siteleri): Gwinnett (Atlanta) güz 12–16 Ekim, bahar 5–9 Nisan 2027; Metro Nashville güz 12–16 Ekim, bahar 22–26 Mart 2027; Dallas ISD güz 8–9 Ekim, bahar 15–19 Mart 2027; Jefferson County (Birmingham) bahar 22–26 Mart 2027, güz tatili yok; Houston ISD bahar 8–12 Mart 2027 (+26 Mart), güz tatili yok.
- Her metronun "en büyük okul bölgesi" seçimi bizim seçimimiz; resmî bir öğrenci sayısı karşılaştırmasıyla doğrulanmadı (satırların notunda yazılı).

### 3e. Etkinlikler (13 satır, etkinliklerin kendi siteleri)

30A Songwriters Festival (2027: 15–18 Ocak), 30A Wine Festival (Alys Beach, 2027: 17–21 Şubat), Seaside School Half Marathon (Şubat), South Walton Beaches Wine & Food Festival (Nisan, Grand Boulevard), Digital Graffiti (Alys Beach; iki yılda bir, sonraki Mayıs 2028), Seaside 4 Temmuz, Halloweener Derby (Ekim), Seeing Red Wine Festival (Kasım başı), Rosemary Beach Uncorked (Kasım), 30A 10K (Şükran Günü, Rosemary Beach), Seaside Holiday Parade (Kasım sonu), Seaside yılbaşı, Escape to Create (2027'de ara). 2027 tarihi yalnız ilk ikisinde yayımlanmış.

### 3f. Merak açıları

Seaside: arazi 1946 (J.S. Smolian), Robert Davis 1978'de miras aldı, inşaat 1981, kurucular Robert ve Daryl Rose Davis, planlayıcılar Andrés Duany ve Elizabeth Plater-Zyberk (Seaside'ın sitesi). DPZ: Seaside tasarım 1980 / temel 1982 (Seaside'ın "1981"iyle çelişkili), Rosemary Beach 1995, Alys Beach 2003 (EBSCO). The Truman Show: 1997'de Seaside'da çekildi, Mayıs 1998 sonunda gösterime girdi (CNU yayını, "ikincil"). New Urbanism tüzüğü 1996. **Alys Beach'in kuruluş yılı doğrulanamadı.**

Ayrıca: Destin ve Fort Walton Beach'in Okaloosa County'de olduğu (ABD Nüfus Bürosu adres servisi, şehirlerin resmî sitelerindeki belediye binası adresleriyle).

### Türkçe ifadeler

Kanıt paketi Türkçe ifade istediği için tablonun her satırının Türkçe karşılığı ayrı bir dosyada (`studio/destinations/thirty_a_references_tr.csv`); tablonun kendi sütunlarına dokunulmadı.

## Adım 4 — Kanıt paketi

- **Yapı:** genel çekirdek `studio/evidence/` (şablon okuma, 14 veri bloğu, paket, saklama); şablonlar destinasyon tarafında dosya (`studio/destinations/thirty_a_evidence/`). Şablon: başlık, ana soru, boyutlar (bölge × karar × dönem × gezgin tipi), parametre (mahalle), bölümler (her birinin sorusu ve blokları).
- **Satır:** Türkçe ifade; ABD birimleriyle değer (°F yanında °C, mil yanında km); kapsam; kaynak (ad, url, belge/erişim tarihi, çekim kimliği ya da belge SHA-256'sı); etiket (kaynak gerçeği, bizim hesabımız, türetilmiş, yaklaşık); örneklem; M belgesinden kullanım notu; varsa İngilizce kısa alıntı.
- **Başlık:** üretim tarihi, kaynakların son çekimi ve zamanı gelip gelmediği, veriden hesaplanan bilinen boşluklar, "yorum ve tavsiye içermez" notu. **Son:** sayı kontrol listesi (her sayı: ifade, değer, birim, kanıt satırı).
- **Çıktı:** Markdown + aynı içeriğin JSON'u, `data/evidence/` altında tarihli ve SHA-256'lı; "Kanıt paketi" ekranı (şablon seç, mahalle ver, üret, indir).
- **M belgelerine eklenen kullanım notları** (paket kendi notunu uydurmasın diye): trafik video dili (M9), plaj erişimi olanakları (M7), küçük örnek eşiği 20 ilan (M11), acil servis cümlesi (M13). Belge: `docs/M14-KANIT-PAKETI.md`.

**Üretilen paketler (gerçek veri):**

| Paket | Bölüm | Kanıt satırı | Sayı | "Veri yok" | Markdown | JSON |
|---|---|---|---|---|---|---|
| İlk video (`kanit-paketi-ilk-video`) | 11 | 732 | 3.003 | 10 | 924 KB | 1,7 MB |
| Rosemary Beach (`kanit-paketi-rosemary-beach`) | 8 | 174 | 556 | 0 | 133 KB | 324 KB |

İlk video bölümleri: 30A nedir (22 satır), 13 mahalle (32), plaj erişimi ve hukuk (31), kurallar ve güvenlik (40), hava–deniz–kasırga (85), kalabalık ve sezon (70), konaklama (260), yemek (52), ulaşım (113), erişilebilirlik (14), pratik ve tarihçe (13). Etiketler: 401 bizim hesabımız, 301 kaynak gerçeği, 15 türetilmiş, 5 yaklaşık.

**"Veri yok" kalan yerler:** yalnız ilk video paketinde, oda grubu fiyatlarında: Gulf Place'te 4 yatak odası (Ocak ve Temmuz) fiyatı okunan ilan yok; Alys Beach'in fiyatları şirketin kendi envanterinden geldiği için oda grubu kırılımı yok (8 satır). Rosemary Beach paketinde "veri yok" yok.

**Paketin kendi saydığı bilinen boşluklar:** okuyucusu olmayan kiralama şirketleri (360blue 256, cottagerentalagency 82, realjoy 61, vrbo 52, 30a-beachgirls 48, vacasa 21, outdoorshower30a 21 ilan); engel yüzünden fiyatı okunamayan 51 ilan; Gulf Place küçük örnek (pencere başına ortanca 14 fiyatlı ilan); Alys Beach tek şirketin envanteri; 138 restorandan 72'sinde seviye yok; OpenStreetMap sınırları; doğrulanamayan 1 acil sağlık noktası; okunamayan zincir/kurumlar (CVS, Doc Smiley's, HCA, Publix, The Fresh Market, Winn-Dixie); doğrulanamayan 2 referans satırı; Book>Direct'in tam envanter olmadığı.

## Adım 5 — Gerçek ortam

1. **Geçici klasörde deneme** (gerçek verinin kopyasıyla, port 8771): günlük ihtiyaç toplayıcısı yeni kategori ve resmî noktalarla çalıştı (47 nokta), iki paket uygulama üzerinden üretildi.
2. **Migration denemesi** (gerçek veritabanının kopyası): v13 → v14; yalnız `destination_poi_categories` 5 → 7 ve yeni boş `evidence_packs`; `integrity_check` ok, `foreign_key_check` boş.
3. **Gerçek veritabanı:**
   - `data/` tam yedeği: `work/yedek/20261010-1548/` (45.396 dosya, 1,27 GB; kopya ve kaynak SHA-256 ile doğrulandı). Uygulama da yükseltmeden önce kendi yedeğini aldı (`data/backups/studio-v13-*`).
   - Uygulama gerçek veriyle açıldı (normal kullanım), şema 13 → 14.
   - Günlük ihtiyaç toplayıcısı: ilk denemede Overpass sunucu hatası (çekim "başarısız" kaydı), 45 sn sonra ikinci deneme başarılı (47 nokta, 21 kontrol satırı).
   - Referans tablosu uygulamada yüklendi: 152 satır, doğrulama sorunu yok.
   - İki kanıt paketi üretildi (`data/evidence/`).
   - Uygulama düzgün kapatıldı.
   - **Önce/sonra:** sürüm 13 → 14; `integrity_check` ok → ok; `foreign_key_check` boş → boş. Değişen tablolar: `destination_poi_categories` 5 → 7, `evidence_packs` 0 → 2, `jobs` 31 → 33, `source_runs` 28 → 30, `poi_snapshots` 1 → 2, `poi_points` 44 → 91, `poi_chain_checks` 10 → 31. Diğer bütün tablolar aynı. (`gercek-veritabani-once-sonra.json`)
4. **Belgeler:** CALISMA_MANTIGI.md, README.md, DEVIR/05 ve 02 güncel durum satırları, M7, M9, M11, M13 güncellendi; M14 yeni.
5. **Testler:** 716 Python testi ve 59 arayüz testi; tam takım art arda 3 kez geçti (önce 692 + 57).
6. **Görev dalı CI:** `d57c43f` için çalıştırma 38054445589 başarılı.

Not: Görev klasöründeki iki paket dosyası `data/evidence/` altındakilerin bayt bayt kopyasıdır (SHA-256'ları `gercek-veritabani-once-sonra.json` içinde); Windows'ta git satır sonlarını değiştirerek çekerse kopyanın SHA-256'sı farklı görünebilir, `data/evidence/` altındaki asıl dosyalar kayıtla eşleşir.

## Beklenmedik durumlar

- Bu bilgisayarın konumu yüzünden bazı ABD siteleri kapalı: HCA Florida (hastane), CVS (eczane), Publix; proxy kullanılmadı.
- Florida mahkeme sisteminin belge sunucusu (acis-api) doğrudan isteğe ve tarayıcıya 403 verdi; aynı kararın resmî PDF'i mahkemenin medya sunucusunda (flcourts-media) bulundu.
- Ordinance 2016-23 ve 2026-01 taranmış görüntüydü; sayfalar görüntü olarak okundu. 2024 mahkeme kararının kopyası da taranmış (faks biçimi); metni okunamadığı için sonuç Senato'nun resmî analizinden alındı.
- Metro Nashville'in İngilizce takvim PDF'i sayfada bağlantılı değildi; bölgenin kendi İspanyolca PDF'i kullanıldı. Dallas ISD'nin PDF takvimi bulunamadı; sitenin etkinlik takvimi kullanıldı. Jefferson County Schools sitesi doğrudan isteğe 403 verdi; bağlantı tarayıcıdan alındı, PDF doğrudan indi.
- Emerald Coast Urgent Care sayfaları koordinat vermiyor; koordinat ABD Nüfus Bürosu adres servisinden (yaklaşık).
- İlk Overpass isteği sunucu hatası verdi; ikinci deneme başarılı.
- İlk video Markdown'ı ilk denemede 1,27 MB idi; aynı bloktaki ortak bilgiler (kaynak, kullanım notu) bir kez yazılarak 924 KB'a indi. Büyük kısmı 3.003 satırlık sayı kontrol listesi.
- Uygulama sürümü 0.14.0'a yükseltildi (şema 14).

## Yöneticinin karar vermesi gereken konular

1. **Bölge kutusu dışındaki acil servis:** doğu mahallelerine en yakın resmî acil servis kutunun hemen dışında (Ascension, Panama City Beach) olduğu için eklendi ve notunda yazıldı. Görev metni "bölge kutusunda" diyordu; bu istisna kabul mü?
2. **HCA Florida ve CVS:** bu bilgisayardan okunamıyor. Kullanıcının kendi tarayıcısında elle bakılıp dosyaya yazılması (ya da başka bir yol) istenir mi, yoksa "okunamadı" olarak mı kalsın?
3. **Küçük örnek eşiği:** pencere başına 20'den az fiyatlı ilan "küçük örnek" sayıldı (bizim eşiğimiz; Gulf Place). Eşik uygun mu?
4. **Okul bölgesi seçimi:** her metronun en büyük okul bölgesi bizim seçimimiz (Gwinnett, MNPS, Dallas ISD, Jefferson County, Houston ISD); resmî öğrenci sayısıyla doğrulansın mı?
5. **Plaj hukuku:** ilçenin Mayıs 2026'da gündeme aldığı belirtilen önergenin (resolution) kabul edilip edilmediği resmî kaynakta doğrulanamadı; uzlaşma parsellerindeki 20 ft geçiş alanının bugünkü durumu belirsiz. Bu satırlar 10 Nisan 2027'de yeniden kontrol edilecek; daha erken mi bakılsın?
6. **Kanıt paketi boyutu:** sayı kontrol listesi her sayıyı (tarihler dahil) satır satır yazıyor; ilk video paketinde 3.003 satır. Bu biçim makale kontrolü için uygun mu?
7. **Sürüm:** dal uygulama 0.14.0 / şema 14; main'e alma ve etiket kararı.

## Teslim edilen dosyalar (`docs/gorevler/GOREV-11/`)

`GOREV.md`, `RAPOR.md`, `referans-tablosu.csv`, `referans-tablosu-yeni-satirlar.csv`, `trafik-fdot-2025.csv`, `gunluk-ihtiyac-mahalle.csv`, `gunluk-ihtiyac-noktalar.csv`, `gunluk-ihtiyac-kontrol.csv`, `kanit-paketi-ilk-video.md` ve `.json`, `kanit-paketi-rosemary-beach.md` ve `.json`, `gercek-veritabani-once-sonra.json`, `ekran/kanit-paketi-ekrani.png`, `ekran/gunluk-ihtiyac-mahalle.png`.
