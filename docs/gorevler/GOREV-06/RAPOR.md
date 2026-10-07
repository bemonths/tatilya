# GÖREV-06 Raporu — v0.8.0 yayını, kasırga evre kuralı, referans tablosu

Tarih: 7 Ekim 2026 · Dal: `gorev-06-referanslar` · Uygulama `0.9.0` · Şema `9`

## Kısaca

- main `de6685f`'e getirildi ve `v0.8.0` etiketi konuldu; ikisinin de CI'ı başarılı.
- Kasırga sayımı artık yalnız fırtınanın tropikal veya subtropikal olduğu evreleri sayıyor. 1991–2025'te 50 deniz mili içindeki fırtına sayısı 20'den 16'ya, 100 deniz mili içindeki 37'den 33'e indi; kasırgaların sayısı değişmedi.
- 85 satırlık elle doğrulanmış referans tablosu, salt okunur Referanslar sekmesi ve South Walton'ın 1998'den bu yana aylık turist vergisi dosyası eklendi.
- Gerçek veritabanı tam yedekten sonra uygulamanın normal kullanımıyla şema 9'a yükseltildi; yalnız kasırga toplayıcısı çalıştı; bütünlük kontrolleri temiz.
- Testler: 513 Python + 42 frontend, yerelde art arda 4 kez geçti.

## Adım 1 — v0.8.0'ı main'e alma ve etiketleme

| | |
|---|---|
| main | `git merge --ff-only origin/gorev-05-iklim` ile `de6685f10699d37afd4e1f13b115a6fa13369355`'e getirildi ve push edildi |
| Etiket | `v0.8.0` önceden yoktu; açıklamalı etiket konuldu (mesaj: "v0.8.0 — eşleme v3 ve iklim paketi"), `de6685f`'i gösteriyor, push edildi |
| main CI | çalıştırma 37648484410 — başarılı |
| Etiket CI | çalıştırma 37648488017 — başarılı |
| Görev dalı | güncel main'den `gorev-06-referanslar` açıldı |

main'e bunun dışında dokunulmadı; başka etiket konmadı.

## Adım 2 — Kasırga sayımı: yalnız tropikal ve subtropikal evreler

Commit `6d09ed0` (ayrı commit). Dal CI: çalıştırma 37649594431 — başarılı.

Ne değişti:
- HURDAT2 durum kodlarından yalnız TD, TS, HU, SD, SS kullanılıyor. EX, LO, WV, DB noktaları daireye giriş, en yakın uzaklık ve en yüksek rüzgâr hesabına girmiyor. İki iz noktası arasındaki ara noktalar, aralığın başındaki noktanın evresini taşıyor.
- Daireye yalnız tropikal olmayan bir evrede giren fırtına yine saklanıyor ama "yalnız tropikal olmayan evre" diye işaretleniyor (`non_tropical_only`); aylık sayımlara, sınıf tablolarına ve "en yakın geçen fırtınalar" listesine girmiyor.
- Toplayıcı sürümü `hurdat2-storm-proximity/2`. Eski `/1` çekimi veritabanında olduğu gibi duruyor.
- Bu işaret için şema 8 → 9 migration'ı (`storm_passages` tablosuna bir sütun). Migration yedek alır, tek transaction'da çalışır, `foreign_key_check` yapar ve hata olursa geri alır.
- İklim sekmesi yeni kuralı yazıyor ve sayılmayan fırtınaları ayrı bir satırda gösteriyor; eski kuralla yapılmış bir çekim açılırsa bunu söylüyor.
- Testler: evre sınırında ara değerleme, yalnız EX evresinde daireye giren fırtına, TD→EX geçişi, SD/SS'nin sayılması, v8 → v9 migration'ı ve geri alma.
- M8 belgesi güncellendi. Video dönemi kararı belgede: videoda kasırga rakamları 1991–2025 dönemiyle verilir ve dönem söylenir.

### Kasırga sayımındaki değişiklik (1991–2025, aynı HURDAT2 dosyası)

| Yarıçap | Eski kural (`/1`) | Yeni kural (`/2`) | TD | TS | HU | MH |
|---|---:|---:|---|---|---|---|
| 50 deniz mili | 20 | 16 | 6 → 3 | 9 → 8 | 2 → 2 | 3 → 3 |
| 100 deniz mili | 37 | 33 | 7 → 4 | 21 → 20 | 5 → 5 | 4 → 4 |

Sayımdan çıkan fırtınalar (daireye yalnız tropikal olmayan evrede girmişler):
- 50 deniz mili: Ida 2009 (EX), Five 2010 (LO), Nestor 2019 (EX), Fay 2020 (LO; fırtınanın öncü alçak basıncı)
- 100 deniz mili: Paloma 2008 (LO), Ida 2009 (EX), Five 2010 (LO), Fay 2020 (LO)

Yalnız en yakın uzaklığı değişenler: Nestor 2019 (100 deniz mili; 48,0 km → 130,9 km, çünkü yakın geçtiği nokta ekstratropikal evredeydi) ve Tammy 2005 (iki yarıçapta da 38,1 km → 40,1 km).

Bütün sezonlarda (1851–2025) işaretli satır sayısı: 50 deniz milinde 5, 100 deniz milinde 5.

Dosyalar: `kasirga-aylik-1991-2025-v2.csv` (yeni kuralla aylara ve sınıflara göre sayılar), `kasirga-v1-v2-fark.csv` (aylara ve sınıflara göre eski ve yeni sayılar ile değişen her fırtına).

## Adım 3 — Elle doğrulanmış referans tablosu

Commit `5800714`. Dal CI: çalıştırma 37653007192 — başarılı.

### Yapı

- Tablo: `studio/destinations/thirty_a_references.csv` (30A profilinin yanında; profil sabiti `REFERENCE_TABLE`). Her satır tek bir olgu; görevdeki 19 sütun aynen.
- Okuyucu ve doğrulayıcı destinasyondan bağımsız (`studio/destinations/references.py`); API `GET /api/references`.
- Veri toplama → **Referanslar** sekmesi: konulara göre gruplu, kaynak bağlantısı, belge konumu, kısa alıntı, erişim tarihi, durum etiketi, yeniden kontrol tarihi; tarihi geçmiş satırlar işaretleniyor; arama ve durum süzgeci var. Salt okunur.
- Doğrulayıcı test (`tests/test_references.py`): sütunlar ve sırası, zorunlu alanlar, kimlik biçimi ve tekilliği, tarih biçimleri, "dogrulandi" ve "celiskili" satırlarda https adresi, erişim tarihi ve SHA-256, çelişkili satırda not, alıntının 25 kelimeyi geçmemesi. Repodaki tablo hiç ihlal içermiyor.
- Belgeler `work/referans-belgeler/` altında (52 alım kaydı, her biri adres, HTTP durumu, bayt, SHA-256 ve zamanla `manifest.json`'da); repoya girmedi.

### Konu başına satır ve durum sayıları

| Konu | Satır | dogrulandi | celiskili | dogrulanamadi |
|---|---:|---:|---:|---:|
| Plaj kuralları (Ordinance 2025-22) | 25 | 25 | 0 | 0 |
| Güvenlik (bayraklar, ateş, cankurtaran) | 12 | 10 | 2 | 0 |
| Plaj erişimi ve park-and-ride | 10 | 10 | 0 | 0 |
| Ulaşım (havalimanları, Timpoochee, golf arabası, düşük hızlı araç, çok amaçlı yol) | 11 | 9 | 2 | 0 |
| Parklar | 8 | 2 | 0 | 6 |
| Kasırga sezonu | 2 | 2 | 0 | 0 |
| Sezon ve maliyet (ziyaretçi, oda-gece, ADR, doluluk, turist vergisi) | 14 | 12 | 2 | 0 |
| Genel (16 mahalle, South Walton tanımı, "Gulf of America") | 3 | 3 | 0 | 0 |
| **Toplam** | **85** | **73** | **6** | **6** |

Notlar:
- Ordinance 2025-22 taranmış bir PDF; metin katmanı yok. Sayfalar görüntüye çevrilip okundu, her alıntı sayfa görüntüsünden doğrulandı, bölüm numaraları yazıldı. Alkol için ayrı bir satır var: "bu bölümde hüküm yok"; başka mevzuat aranmadı.
- Havalimanı uzaklıkları FAA koordinatlarından bizim hesabımız (kuş uçuşu, 30A kıyı koridorunun en yakın ucuna): ECP 21,5 km (13,4 mil, doğu ucu), VPS 28,9 km (17,9 mil, batı ucu), PNS 89,5 km (yaklaşık 56 mil, batı ucu). Satır notlarında "bizim hesabımız" yazıyor.
- En son yıllık rapor (2025): 4.586.000 ziyaretçi (aynı raporda başka sayfada 4,57 milyon, bkz. çelişkiler), 3.497.200 oda-gece, doluluk %48,3, ADR 354,10 $. Kapsam raporun dediği gibi Walton County. Son dört mevsim raporu: Yaz 2025 %69,1 / 500,54 $, Sonbahar 2025 %35,7 / 335,96 $, Kış 2026 %32,1 / 213,82 $, İlkbahar 2026 %56,6 / 389,17 $. Raporlardaki yöntem uyarısı nota eklendi: Airbnb (30 Nisan 2025) ve Vrbo (30 Mayıs 2025) fiyat gösterimini temizlik ve platform ücretleri dahil olacak biçimde değiştirdi; bu yüzden ADR yıllar arası karşılaştırmada şişkin görünebilir.
- Yeniden kontrol tarihleri: kurallar, ücretler ve tanımlar 2027-10-07 (70 satır); mevsim ve yıllık rapor satırları 2026-12-01 (13 satır); çelişkili cankurtaran satırları sezondan önce 2027-02-01 (2 satır).

### Okunamayan kaynaklar

- Florida State Parks sayfaları (Grayton Beach, Topsail Hill Preserve, Deer Lake; "hours-fees") HTTP 403 döndürdü (Cloudflare bot doğrulaması). Görev gereği otomasyonla aşılmadı. Bu üç parkın giriş ücreti ve saatleri (6 satır) "dogrulanamadi"; videoda kullanılmaz. Elle bir tarayıcıdan bakılıp tablo güncellenebilir.
- Geçici sorunlar (sonra okundu): Ordinance 2009-02 ilk denemelerde HTTP 522 verdi, üçüncü denemede alındı. Visit South Walton'ın Timpoochee rehber yazısının tahmin edilen adresi 404 verdi; doğru adres aynı sitede bulundu.

### Çelişkiler (ikisi de ayrı satır, ikisi de "celiskili"; hangisinin doğru olduğuna karar verilmedi)

1. **Cankurtaran sezonu:** South Walton Fire District SSS sayfası 1 Mart–30 Eylül, 10:00–18:00, 8 kule diyor; Visit South Walton plaj güvenliği sayfası 1 Mart–31 Ekim diyor.
2. **Timpoochee Trail uzunluğu:** Visit South Walton'ın listeleme sayfası 19 mil; aynı kurumun 2021 tarihli rehber yazısı tam güzergâhı 18,5 millik bir bisiklet turu olarak anlatıyor.
3. **2025 ziyaretçi sayısı:** aynı yıllık raporun 5. sayfası (ve tabloları) 4.586.000, 8. sayfası 4,57 milyon diyor; doğrudan harcama da iki sayfada farklı (3.928.943.400 $ / 3,23 milyar $).

### 3d — Aylık turist vergisi (TDT) keşfi

- Bulundu. "TDT Collections" sayfası bir Gatsby sitesi; aylık raporların listesi sayfanın statik sorgu dosyasından (`/page-data/sq/d/2777485464.json`) geliyor ve herkese açık PDF/XLSX dosyalarına bağlanıyor. Tarayıcı otomasyonu kullanılmadı.
- South Walton için Walton County Clerk'in "SW TDT Collections History with Monthly FYTD Comparisons" çalışma kitabı Ekim 1998'den bu yana bütün ayları içeriyor. Bundan `studio/destinations/thirty_a_tdt_collections.csv` üretildi: 334 ay (Ekim 1998 – Temmuz 2026); ay, mali yıl, vergi bölgesi, tutar, oran değişimlerinden bağımsız %2 payı, kaynak sayfa, URL, erişim tarihi, SHA-256. Her mali yılın aylık toplamı kitaptaki yıllık toplamla birebir aynı. Teslim kopyası: `turist-vergisi-aylik.csv`.
- **Ay neyi gösteriyor?** Aylık rapor dönemi "Monthly Collections: June 2026 (Received during July 2026)" diye veriyor; dosya adları da "MAY25 collected in JUN25" biçiminde. Yani etiketteki ay tahsil ayı değil; para bir sonraki ay alınıyor. Etiketteki ayın konaklama ayı olduğunu açıkça söyleyen bir ifade kaynakta bulunamadı; bu yüzden "konaklama ayı" diye yazılmadı.
- Vergi oranı yıllar içinde değişti (%3 → %4 → %4,5 → %4 → %5; 1 Ocak 2020'den beri %5). Yıllar arası karşılaştırmada %2 payı sütunu kullanılmalı.
- Küçük fark: Haziran 2026 South Walton toplamı çalışma kitabında 11.945.425,14 $, aylık PDF raporunda 11.945.791,53 $ (fark 366,39 $). CSV çalışma kitabını izliyor; fark M9'a yazıldı.

## Adım 4 — Belgeler ve testler

- Yeni belge `docs/M9-REFERANS-TABLOSU.md`: amaç, dosyalar, sütunlar, doğrulayıcı, kaynak politikası, durumlar ve video dili, yeniden kontrol kuralı (kurallar ve ücretler yılda bir; mevsim raporları her yeni rapor çıktığında), 7 Ekim 2026 içeriği ve TDT bölümü.
- Güncellenen durum satırları: `CALISMA_MANTIGI.md`, `README.md`, `docs/DEVIR/05`, `docs/DEVIR/02`; ayrıca `docs/DEVIR/07`, `docs/ASAMALAR.md` ve `docs/M8-IKLIM-VERISI.md`.
- Uygulama sürümü `0.9.0`.
- Testler (yerelde art arda 4 kez): **513 Python testi geçti** (görev başında 479), **42 frontend testi geçti** (görev başında 37). Her Python çalıştırmasında bir kütüphane uyarısı var (Starlette'in `httpx` ile test istemcisi kullanımının ileride kaldırılacağı); testleri etkilemiyor.

## Adım 5 — Gerçek ortam

1. **Geçici klasörde canlı deneme** (`work/gorev-06/temp-data`): yeni kasırga toplayıcısı NOAA'dan canlı çalıştı. 1991–2025 aylık sayımları eski çekimle karşılaştırıldı; sonuç yukarıdaki tabloyla aynı (gerçek veritabanındaki sonuçla da birebir aynı).
2. **Migration denemesi:** gerçek veritabanının `work/` kopyasında şema 8 → 9 denendi; bütün tabloların satır sayıları, kaynaklar ve çekimler aynı kaldı; `integrity_check` ok, `foreign_key_check` boş.
3. **Gerçek veritabanı** (CLAUDE.md kuralıyla):
   - Uygulama kapalıyken `data/` klasörünün tamamı `work/yedek/20261007-1935/` altına kopyalandı (380 dosya, 50.989.177 bayt; kopya ve kaynak karşılaştırıldı, aynı).
   - Uygulama gerçek veriyle açıldı; açılışta kendi yedeğini aldı (`data/backups/studio-v8-14fb0efcabd8429ebdb63c0fdb353ac9.sqlite3`) ve şemayı 9'a yükseltti.
   - Yalnız kasırga toplayıcısı çalıştırıldı: çekim `4f23d0a272f14bb7a44bb40b26cb55a0`, 227 kayıt, 4,2 sn. Uygulama düzgün kapatıldı.
   - Sonra: şema 9, `integrity_check` ok, `foreign_key_check` boş. Değişen satır sayıları: jobs 16 → 17, source_runs 13 → 14, storm_corridor_snapshots 1 → 2, storm_passages 227 → 454 (eski 227 satır olduğu gibi duruyor). Diğer bütün tablolar aynı. `data/` 380 → 384 dosya (uygulama yedeği ve yeni çekimin ham dosyaları).
4. **Ekran görüntüleri** (gerçek veritabanının güncelleme sonrası kopyasıyla açılan uygulamadan): `referanslar-sekmesi.png` (Referanslar sekmesi), `referanslar-celiskili.png` (yalnız çelişkili satırlar süzülmüş), `iklim-kasirga-bolumu.png` (İklim sekmesinin kasırga bölümü, yeni kural metni ve sayılmayan fırtınalar satırıyla).

## Teslim klasörü

`docs/gorevler/GOREV-06/`: `GOREV.md`, `RAPOR.md`, `referans-tablosu.csv`, `turist-vergisi-aylik.csv`, `kasirga-aylik-1991-2025-v2.csv`, `kasirga-v1-v2-fark.csv`, `referanslar-sekmesi.png`, `referanslar-celiskili.png`, `iklim-kasirga-bolumu.png`.

## Beklenmedik durumlar

- Florida State Parks'ın Cloudflare engeli (yukarıda); 6 park satırı doğrulanamadı.
- Yıllık ziyaretçi raporu kendi içinde çelişiyor (5. ve 8. sayfa).
- Uygulama içi tarayıcıda Walton County Tourism sitesine gitme izni verilmedi; PDF'lerdeki infografik değerler bu yüzden Windows'un kendi PDF çizicisiyle sayfa görüntüsüne çevrilip gözle doğrulandı. Sonuca etkisi yok.
- Turist vergisi çalışma kitabı ile aylık PDF raporu arasında Haziran 2026 için 366,39 $'lık fark.
- Gerçek veritabanı artık şema 9: main'deki 0.8.0 bu dosyayı "daha yeni sürüme ait" diye açmaz. Uygulama bu dal main'e alınana kadar `gorev-06-referanslar` dalından çalıştırılmalı.

## Yöneticinin karar vermesi gereken konular

1. `gorev-06-referanslar` dalının main'e alınması ve `v0.9.0` etiketi.
2. Üç çelişki videoda nasıl kullanılacak: cankurtaran sezonu (SWFD 30 Eylül / Visit South Walton 31 Ekim), Timpoochee uzunluğu (19 / 18,5 mil), 2025 ziyaretçi sayısı (4.586.000 / 4,57 milyon). Her biri ya çelişki söylenerek ya da daha güncel resmî kaynakla çözülerek kullanılabilir.
3. Park ücretleri ve saatleri: Florida State Parks sayfası elle bir tarayıcıdan okunup tabloya mı eklensin, yoksa videoda park ücreti hiç söylenmesin mi?
4. Turist vergisi: etiket ayının konaklama ayı olduğu kaynakta yazmıyor. Videoda bu veri "ay ay toplanan vergi" diye mi kullanılsın, yoksa Walton County Clerk'e sorulsun mu?
5. ADR değerleri: 2025'teki platform fiyat gösterimi değişikliği yüzünden yıllar arası ADR karşılaştırması videoda yapılsın mı?
