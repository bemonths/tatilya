# GÖREV-04 Raporu — v0.7.0 yayını, gerçek verinin güncellenmesi ve plaj–mahalle eşlemesi v2

Tarih: 7 Ekim 2026 · Dal: `gorev-04-esleme-v2`

## Kısa özet

Dört adımın hepsi tamamlandı. main `7f25e3c`'ye taşındı ve `v0.7.0` etiketi konuldu. Gerçek veritabanı, `data/` klasörünün tam yedeği alındıktan sonra uygulamanın normal kullanımıyla şema 7'ye yükseltildi; dört toplayıcı başarıyla çalıştı ve bütünlük kontrolleri temiz. Kararsız test sağlamlaştırıldı. Plaj–mahalle eşlemesi Walton County alt bölüm poligonlarıyla yeniden kuruldu (v2).

**En önemli bulgu:** Plaj erişim noktalarının çoğu kamuya ait yol uçlarında, alt bölüm poligonlarının birkaç metre dışında kalıyor (53 erişimin 21'i bir poligonun içinde, 32'si yalnız yakınında). Görev metni ilçe yöntemini yalnız poligonun "içindeki" erişimler için tanımladığından v2 bunu harfiyen uyguladı; bu yüzden ilçe verisi yalnız 6 erişimin mahallesini belirledi ve v1'de "Seaside" yazılan 10 erişimin 9'u hâlâ "Seaside (program türetimi)". Bu 9 erişimin 7'si Seagrove alt bölümlerine 4,5–21,3 m uzaklıkta. Yakın poligonların da kullanılması yöneticinin kararına bırakıldı (aşağıda etkisiyle birlikte).

| Commit | İçerik |
|---|---|
| `0f39d8a` | Adım 2: gerçek veriyi güncelleme kuralı (CLAUDE.md, CALISMA_MANTIGI.md) |
| `dcce559` | Adım 3: test bekleme yardımcıları |
| `d419e10` | Adım 4: eşleme v2, ilçe sorgu sonuçları, ad tablosu, ekran etiketi, testler |
| son commit | M7 ve ana belgeler, bu teslim klasörü |

## Adım 1 — v0.7.0'ı main'e alma ve etiket

- `v0.7.0` etiketi önceden yoktu (yerelde ve GitHub'da kontrol edildi).
- main, `git merge --ff-only` ile `7f25e3ce947c69fef999f7f4454a79608008fcad` konumuna getirildi ve push edildi.
- Açıklamalı etiket `v0.7.0` (mesaj: "v0.7.0 — mahalle verisi ve plaj–mahalle eşlemesi") bu commit'e konuldu ve push edildi (etiket nesnesi `f2397f65…`).
- main CI: **başarılı** (Actions run `37606378932`).
- Güncel main'den `gorev-04-esleme-v2` dalı açıldı.

## Adım 2 — Gerçek veriyi güncelleme kuralı ve uygulaması

Kural CLAUDE.md "Veri güvenliği" bölümüne ve CALISMA_MANTIGI.md 12. bölüme eklendi.

1. **Yedek.** Uygulamanın kapalı olduğu doğrulandı (30A Studio süreci yok, 8830 portu boş, `data/` içinde -wal/-shm yok). `data/` klasörünün tamamı `work/yedek/20261007-1318/` altına kopyalandı: **172 dosya, 15.108.412 bayt**; bütün dosyaların SHA-256 listesi kaynakla birebir aynı.
2. **Açılış.** Uygulama `.venv\Scripts\python.exe -X utf8 -m studio --no-browser` ile varsayılan `data/` klasörüyle açıldı. v6 → v7 yükseltmesini uygulama kendi yedeğiyle yaptı: **`data/backups/studio-v6-0940e8b1e88246ad87f5c25771e8addf.sqlite3`**.
3. **Toplayıcılar** (API üzerinden, sırayla):

| Toplayıcı | Durum | Kayıt | Önceki sürüme göre fark |
|---|---|---|---|
| Plaj erişimleri (`1a195e2b…`) | Başarılı, 2 sn | 53 (70 harita noktası, 17 kapsam dışı) | 0 eklendi · 0 kaldırıldı · 0 değişti · 53 aynı |
| National Weather Service (`8e68987f…`) | Başarılı, 8 sn | 510 (3 nokta, 42 dönem, 468 saatlik) | Hava için fark gösterilmiyor (kayan tahmin penceresi). Çekimde 1 aktif uyarı var: Rip Current Statement (NWS Tallahassee). |
| Restoranlar (`5a62f787…`) | Başarılı, 96 sn | 138 | 0 eklendi · 0 kaldırıldı · **6 değişti** · 132 aynı |
| Mahalleler (`3d1cbe8d…`) | Başarılı, 8 sn | 13 (16 dizin kaydı, 3 kapsam dışı) | İlk sürüm (önceki yok) |

Restoranlardaki 6 değişiklik kaynağın kendisinden: 4 işletmenin web adresi `dawsongroupseasidefl.com` altından kendi alan adlarına geçmiş (Dawson's Yogurt & Fudge Works, It's Heavenly, The Shrimp Shack, Wild Bill's Beach Dogs); 2 işletmenin açıklaması değişmiş (Farm & Fire, North Beach Social).

4. **Kapanış ve kontrol.** Uygulama Ctrl+Break ile normal kapanışını yaparak kapandı (çıkış kodu 3: Windows'ta Ctrl+Break sonrası düzgün kapanışın standart kodu); `data/` içinde -wal/-shm kalmadı. Veritabanı salt okunur kopyalanıp sayıldı:

| Tablo | Önce (şema 6) | Sonra (şema 7) |
|---|---:|---:|
| sources | 8 | 9 |
| source_history | 4 | 4 |
| jobs | 9 | 13 |
| source_runs | 6 | 10 |
| beach_records | 159 | 212 |
| weather_locations | 6 | 9 |
| weather_forecast_periods | 1020 | 1530 |
| weather_alerts / weather_alert_anchors | 0 / 0 | 1 / 3 |
| restaurant_records | 138 | 276 |
| restaurant_regions | 141 | 282 |
| neighborhood_records | — | 13 |
| regions / destinations / destination_weather_anchors | 13 / 1 / 3 | 13 / 1 / 3 |
| entities / entity_sources / metadata | 0 / 0 / 1 | 0 / 0 / 1 |

`integrity_check`: önce ok, sonra ok. `foreign_key_check`: önce boş, sonra boş. `data/` artık 352 dosya (yeni ham yanıtlar ve yükseltme yedeği).

## Adım 3 — Kararsız test

`test_api_raw_hash_rollback_and_previous_run` testinin kullandığı `finished()` yardımcısı (ve aynı kalıptaki `wait_job()`) işi en fazla 3 saniye bekliyordu; yük altında bu süre aşılabiliyordu. Artık 20 ms aralıkla, en fazla 30 saniye yokluyor, süre dolunca durumu bir kez daha okuyor ve hata mesajında son durumu yazıyor. Testlerin doğruladığı davranış değişmedi; biten iş ilk kontrolde döner.

- Düzeltmeden sonra tam takım art arda 5 kez: her seferinde 390 Python + 29 frontend testi geçti.
- Yük denemesi: 3 tam takım aynı anda çalıştırıldı; üçü de 390/390 geçti (her biri ~50 sn).
- Son kodla (Adım 4 testleri dahil) art arda 5 kez daha: her seferinde **408 Python + 30 frontend testi geçti** (28–31 sn).

## Adım 4 — Plaj–mahalle eşlemesi v2

### 4a. Alt bölüm katmanının değerlendirmesi

| | |
|---|---|
| Katman | Walton County GIS, `EnerGov_Additional/FeatureServer/13` "Subdivision Boundaries" — https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/ArcGIS/rest/services/EnerGov_Additional/FeatureServer/13 |
| Sahibi | Walton County GIS (servis açıklaması: "Additional GIS Data made for EnerGov application also general use - Updated Weekly") |
| Kayıt | 2.254 poligon; kimlik `OBJECTID` (GlobalID yok); `SUBDIVISION_NUMBER` ilçenin alt bölüm numarası |
| Alt bölüm adı | **Ayrı bir ad alanı yok.** Ad, alt bölüm başlık kayıtlarında `OWNER_NAME` alanında (katmanın görüntüleme alanı) duruyor, ör. `SEAGROVE 1ST ADD`. Bazı kayıtlarda bu alan şirket/sahip adı, bilgi kaydı veya yasal tanım taşıyor; bu yüzden yalnız adı açıkça mahalle belirten kayıtlar kullanıldı. |
| Son düzenleme | `dataLastEditDate` 2026-10-04 (servis haftalık yeniden yayımlanıyor; verinin gerçek değişiklik tarihi olmayabilir) |
| Kullanım / lisans | Katmanda açıklama ve telif metni yok; servisin telif alanı doldurulmamış. Ayrı bir kullanım koşulu bulunamadı. Yayımlanmış ArcGIS REST API'si üzerinden 53 nokta için tek seferlik sorgu yapıldı; robots.txt yok. |
| Alternatif | Aynı servisteki "Covenants Restrictions" (katman 31) açık `Sub_Name` alanı veriyor ama yalnız sözleşme/kısıtlama belgesi kayıtlı alt bölümleri kapsıyor ve 2013 tarihli; kullanılmadı. |

Katman alt bölüm adını ayrı bir alanda vermese de başlık kayıtlarında veriyor; bu yüzden durulmadı, ad seçimi ad tablosuyla sıkı tutuldu.

### 4b. Sorgu sonucu

53 erişimin her biri için nokta-poligon sorgusu yapıldı (`esriGeometryPoint`, `esriSpatialRelIntersects`, giriş koordinatı WGS84 / `wkid 4326` olarak açıkça verildi). İçinde değilse 75 m içindeki en yakın poligon(lar) mesafesiyle kaydedildi. Sonuç: **21 erişim içeride, 32 erişim yakın** (en uzak 70,2 m), sonuçsuz yok. Repodaki dosya: `studio/destinations/thirty_a_beach_subdivisions.csv` (99 satır; bir nokta birden fazla poligonun içindeyse her poligon ayrı satır). Ham yanıtlar `work/gorev-04/ilce-ham/sorgu/` altında (85 dosya, repoda değil).

### 4c. Ad tablosu

Sorgu 49 farklı ad döndürdü. Adında kanonik mahalle adı tam olarak geçen 13 alt bölüm başlığı tabloya alındı (`studio/destinations/thirty_a_subdivision_neighborhoods.csv`): Dune Allen 2, Blue Mountain Beach 1, Grayton Beach 3, Seagrove 5, Seacrest 1, Inlet Beach 1. Alınmayanlar: şirket/sahip adları (`SEAGROVE ENDEAVORS`, `WALKOVER PROPERTIES`), bilgi kayıtları (`INFORMATION ONLY …`), yasal tanımlar (`S/D OF …`), tam mahalle adı taşımayan `BUTLER'S ADD TOWN OF GRAYTON` ve başka yer/site adları (ör. `SEA HIGHLANDS S/D`, `SUGARWOOD S/D`). Kararlı tam liste: [alt-bolum-adlari.csv](alt-bolum-adlari.csv).

### 4d–4f. Yeni yöntem ve sonuç

Yöntem sırası: resmî rehber (9, değişmedi) → ilçe alt bölüm verisi (nokta poligonun içinde ve ad tablodan tek bir mahalleye bağlanıyorsa) → program türetimi (eskisi gibi, belirsizlik işaretiyle). Alys Beach / Rosemary Beach kısıtı sürüyor. **Resmî rehberle çelişki: yok** (hiçbir erişim bu iki mahallenin alt bölümünün içine düşmedi; Winston Lane - 4 Rosemary Beach alt bölümlerine 8,5 m yakın ama içinde değil).

Eşleme dosyası gerçek veritabanının Adım 2'deki çekimleriyle üretildi: plaj `1a195e2b27604fbb9443f7376434df6d`, mahalle `3d1cbe8d5efc4e0fbae432786d57be23` (program türetimi satırlarının kaynak sütunu). Sonuç: **9 resmî rehber, 6 ilçe alt bölüm verisi, 38 program türetimi; 2 belirsiz.**

| Mahalle | Resmî rehber | İlçe alt bölüm | Program türetimi | Toplam | v1 |
|---|---:|---:|---:|---:|---:|
| Dune Allen | 2 | 1 | 4 | 7 | 6 |
| Gulf Place | 1 | 0 | 2 | 3 | 4 |
| Santa Rosa Beach | 1 | 0 | 2 | 3 | 3 |
| Blue Mountain Beach | 1 | 0 | 3 | 4 | 4 |
| Grayton Beach | 1 | 2 | 1 | 4 | 4 |
| WaterColor | 0 | 0 | 0 | 0 | 0 |
| Seaside | 0 | 0 | 9 | 9 | 10 |
| Seagrove | 2 | 2 | 11 | 15 | 14 |
| WaterSound | 0 | 0 | 0 | 0 | 0 |
| Seacrest | 0 | 0 | 3 | 3 | 3 |
| Alys Beach | 0 | 0 | 0 | 0 | 0 |
| Rosemary Beach | 0 | 0 | 0 | 0 | 0 |
| Inlet Beach | 1 | 1 | 3 | 5 | 5 |

### 4e. Doğrulama ve v1–v2 farkı

İlçe yöntemi 9 resmî eşlemeye uygulandı: **1'inde aynı** (Bets "Beachmama" Haynes → Grayton Beach), **8'inde sonuç yok** (5'i yalnız yakın poligonda; 3'ünde içinde olunan poligonun adı mahalle belirtmiyor), **farklı çıkan yok**. Program türetimi aynı 9 eşlemenin 8'inde aynı (fark Walton Dunes - 8, v1'deki gibi). Tablo: [esleme-dogrulama-v2.csv](esleme-dogrulama-v2.csv).

v1 → v2 farkı (6 satır; tablo: [esleme-v1-v2-fark.csv](esleme-v1-v2-fark.csv)):

| Erişim | v1 | v2 | v2 yöntemi |
|---|---|---|---|
| Lake Causeway - 41 | Gulf Place | **Dune Allen** | ilçe alt bölüm (`VIZCAYA AT DUNE ALLEN S/D`) |
| Highway 395 - 25 | Seaside | **Seagrove** | ilçe alt bölüm (`SEAGROVE HORIZONS`) |
| Grayton Dunes - 17 | Grayton Beach | Grayton Beach | ilçe alt bölüm |
| Grayton Dunes (West) | Grayton Beach | Grayton Beach | ilçe alt bölüm |
| Campbell Street - 15 | Seagrove | Seagrove | ilçe alt bölüm |
| Lupine - 1 | Inlet Beach | Inlet Beach | ilçe alt bölüm |

### Yakın poligonlar da kullanılsaydı (uygulanmadı)

| Erişim | v2 | Yakın poligonla | En yakın alt bölüm | Mesafe |
|---|---|---|---|---:|
| Palms of Dune Allen West - 44 | Gulf Place | Dune Allen | PALMS AT DUNE ALLEN UNRECD | 7,2 m |
| Palms of Dune Allen East - 43 | Gulf Place | Dune Allen | PALMS AT DUNE ALLEN UNRECD | 7,6 m |
| Dogwood/Thyme - 29 | Seaside | Seagrove | SEAGROVE 1ST ADD | 18,6 m |
| Hickory - 28 | Seaside | Seagrove | SEAGROVE 1ST ADD | 13,7 m |
| Live Oak - 27 | Seaside | Seagrove | SEAGROVE 1ST ADD | 21,3 m |
| Nightcap Street - 26 | Seaside | Seagrove | SEAGROVE REVISED | 9,7 m |
| Holly - 24 | Seaside | Seagrove | SEAGROVE 3RD ADD | 6,3 m |
| Azalea/Camellia - 23 | Seaside | Seagrove | SEAGROVE 3RD ADD | 4,6 m |
| Gardenia - 22 | Seaside | Seagrove | SEAGROVE 3RD ADD | 4,5 m |

Ayrıca Gulf Point Road - 35, Seagrade Road - 34, Blue Lake Road - 33 (Blue Mountain Beach) ve Seacrest Dr - 5 (Seacrest) aynı mahallede kalıp yöntem olarak ilçe verisine geçerdi. Bu seçenekle toplamlar: Seaside 9 → 2, Seagrove 15 → 22, Dune Allen 7 → 9, Gulf Place 3 → 1.

### 4g. Belge ve ekran

`docs/M7-MAHALLE-VERISI.md` v2'ye göre güncellendi (kaynak değerlendirmesi, sorgu, ad tablosu kuralı, yöntem, sonuç, doğrulama, sınır ve video dili). Video dili: "resmî rehber" ve "ilçe alt bölüm verisi" eşlemeleri kaynak gösterilerek söylenebilir ("Walton County subdivision verisine göre"); "program türetimi" yalnız yaklaşık konumdur. Plaj ekranında yeni etiket "ilçe alt bölüm verisi" (yeşil, kaynaklı) olarak görünüyor; ekran görüntüsü gerçek veritabanının `work/` altındaki kopyasıyla alındı: [plaj-ekrani-esleme-v2.png](plaj-ekrani-esleme-v2.png). CALISMA_MANTIGI.md, README.md, DEVIR/02/05/07 ve ASAMALAR.md'deki güncel durum satırları v0.7.0 yayınına ve v2'ye göre düzeltildi.

## Testler ve CI

- Python: 390 → **408**; frontend: 29 → **30**. Yeni testler: ilçe yöntemi (içeride, yakın, sonuçsuz, tabloda olmayan ad, adsız poligon, farklı mahalle gösteren adlar, Rosemary/Alys çelişkisi), yöntem sırası, sonuç ve ad tablosu okuyucuları, ilçe sorgusunun parametreleri (nokta, ilişki, uzamsal referans), yakın/eşit mesafe/75 m sınırı, mesafe hesabı, ağ hatası, v1–v2 farkı, ağa yalnız istenince çıkma, ekrandaki etiket ve bağlantı.
- CI: main @ `7f25e3c` başarılı (`37606378932`). Dalın sonucu GitHub Actions'ta.

## Beklenmedik durumlar

1. Alt bölüm katmanında ayrı bir ad alanı yok; ad `OWNER_NAME` alanından alındı ve şirket/sahip adları dışarıda tutuldu.
2. Erişim noktalarının çoğu poligonların hemen dışında (yol uçları). Görev metnine göre yalnız "içeride" olanlar atandığı için ilçe verisi yalnız 6 erişimde kullanıldı ve Seaside sorunu büyük ölçüde sürüyor (yukarıdaki tablo).
3. Restoran dizininde 6 değişiklik çıktı (4 web adresi, 2 açıklama); kaynaktaki gerçek değişiklikler.
4. Hava çekiminde 1 aktif NWS uyarısı vardı (Rip Current Statement); bu yalnız o çekimin durumudur.
5. Uygulama Ctrl+Break ile kapanınca çıkış kodu 3 oluyor; bu Windows'ta normal kapanışın ardından gelen standart koddur, hata değildir.

## Yöneticinin karar vermesi gereken konular

1. **Yakın poligonlar:** 75 m içindeki en yakın alt bölüm adı da atamada kullanılsın mı? Kullanılırsa 7 erişim Seaside'dan Seagrove'a, 2 erişim Gulf Place'ten Dune Allen'a geçer (veri repoda hazır; yalnız kural değişir).
2. **Ad tablosu kuralı:** Yalnız tam mahalle adı geçen alt bölüm başlıkları kabul edildi. `BUTLER'S ADD TOWN OF GRAYTON` gibi kısmi adlar ve şirket adları dışarıda; bu sıkılık uygun mu?
3. **Katman seçimi:** Ana katman olarak "Subdivision Boundaries" (ad alanı yok, haftalık güncel) kullanıldı; açık ad alanı olan ama 2013 tarihli ve kısmi "Covenants Restrictions" katmanı kullanılmadı.
4. **Kimlik kalıcılığı:** Poligon kimliği olarak `OBJECTID` yazıldı; haftalık yayında değişebilir. İleride CSV'ye `SUBDIVISION_NUMBER` da eklensin mi?
5. `gorev-04-esleme-v2` dalının main'e alınması (ve gerekirse yeni bir etiket).
