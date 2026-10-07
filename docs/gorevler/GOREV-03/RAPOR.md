# GÖREV-03 Raporu — main'e alma, mahalle verisi ve plaj–mahalle eşlemesi

Tarih: 7 Ekim 2026 · Dal: `gorev-03-mahalleler` · Sürüm adı: **v0.7.0 — mahalle verisi ve plaj–mahalle eşlemesi** (uygulama 0.7.0, şema 7)

## Kısa özet

Altı adımın hepsi tamamlandı. main, GÖREV-02'nin son commit'ine taşındı ve push edildi. Visit South Walton mahalle dizini için yeni toplayıcı, şema 7 ve "Mahalleler" sekmesi eklendi. 53 plaj erişimini mahallelere bağlayan, yöntemi etiketli ayrı bir eşleme dosyası üretildi ve plaj ekranında gösteriliyor. Canlı deneme geçici klasörde, yükseltme denemesi gerçek veritabanının kopyasında başarılı oldu. Gerçek `data/` klasörüne dokunulmadı. Tag oluşturulmadı.

| Commit | İçerik |
|---|---|
| `e711323` | Adım 2: belge düzeltmeleri ve robots.txt kuralı |
| `830b9b3` | Adım 3: mahalle toplayıcısı, şema 7, Mahalleler sekmesi, testler |
| `a6e06f9` | Adım 5: plaj–mahalle eşleme katmanı, üretici betik, plaj ekranı, testler |
| son commit | Adım 6 belgeleri ve bu teslim klasörü |

## Adım 1 — main'e alma ve yeni dal

- `main`, `git merge --ff-only` ile `62d6b7b431669ca44a705b1c85f24f9df72bd6ca` konumuna getirildi ve GitHub'a push edildi. Fast-forward sorunsuz oldu.
- main üzerindeki CI: **başarılı** (Actions run `37598345273`).
- Güncel main'den `gorev-03-mahalleler` dalı açıldı; bütün commit'ler bu dalda.

## Adım 2 — Küçük belge düzeltmeleri

- `docs/DEVIR/07`: "Geliştirme yöntemi" akışındaki "manual acceptance" adımı "yönetici kabulü (main'e alma kararı görev metniyle)" oldu; bölüm sonundaki "kullanıcıya" ifadesi "yöneticiye, görev raporu (`docs/gorevler/GOREV-NN/RAPOR.md`) üzerinden" oldu.
- `docs/ASAMALAR.md` Aşama 4: "kullanıcı onayı" → "yönetici onayı"; kullanıcının makale aşamasında devreye girdiği yazıldı.
- `docs/DEVIR/05` içindeki "User manual v0.6 smoke" tarihsel kayıt olarak değiştirilmedi.
- `CALISMA_MANTIGI.md` 4. bölüme robots.txt / tek seferlik resmî belge / yayımlanmış API kuralı 14. madde olarak eklendi.

## Adım 3 — Mahalle veri toplayıcısı

- Yeni toplayıcı `south-walton-neighborhoods/1`: dizin sayfasındaki gömülü JSON'u ve 13 mahallenin her birinin sayfasını okur. Genel akışı kullanır (kaynak → iş → çekim → ham dosya → tek seferde yazım).
- Güvenlik restoran toplayıcısıyla aynı düzeyde: yalnız HTTPS ve izinli host, boyut/zaman sınırları, bir yeniden deneme, iptal, her yanıtın SHA-256'sıyla ham manifest. Yalnız `destination_id=30a` olan kaynağa bağlanır.
- Kapsam: 13 kanonik mahalle; ad birebir veya açık yazım tablosuyla eşlenir. Miramar Beach, Seascape, Sandestin kapsam dışı. 13'ten biri yoksa çekim başarısız olur. Adres veya koordinattan mahalle çıkarılmaz.
- Saklananlar: 24 haneli kimlik, permalink, ad, kanonik bölge, kısa tanıtım, temsilî nokta (belgede "mahalle merkezi değil, kaynağın temsilî noktası" diye yazıldı), kaynak etiketleri, kayıt bazında `modified`, sayfa tanıtım metni (yoksa NULL). Belgelere "videoda aynen kullanılmaz, kendi cümlelerimizle ve atıfla kullanılır" notu yazıldı.
- Şema 7: `neighborhood_records` tablosu ve v6 → v7 migration (açılışta yedek, tek transaction, `foreign_key_check`, hata halinde geri alma). Migration yalnız 30A'ya "South Walton · Mahalleler" kaynağını ekler; uyumlu bir kaynak zaten varsa ikincisini eklemez.
- Fark (diff) mahalle kimliği üzerinden çalışır; yalnız `modified` damgası değişmişse kayıt "aynı" sayılır.
- Arayüz: Veri toplama ekranında dördüncü sekme "Mahalleler" — toplama düğmesi, sürüm seçimi, fark özeti, batıdan doğuya liste, ayrıntı paneli. Mevcut görsel düzen korundu.
- Testler: görevde istenen bütün durumlar kapsandı (16 kayıttan 13 seçim / 3 kapsam dışı, eksik hedef mahalle, bozuk JSON, yinelenen kimlik, tanıtım metni olmayan sayfa → NULL, iptal, atomik geri alma, diff, v6 → v7 migration ve geri alma, destinasyon yalıtımı) ve ek olarak HTTP sınırları, yönlendirme, yazım tablosu, sayfa kimliği. Canlı ağ kullanılmadı.

## Adım 4 — Gerçek ortam kontrolleri

### Canlı deneme (`work/gorev-03/temp-data`)

robots.txt 7 Ekim'de yeniden okundu: yalnız `/userfiles/` ve `/search/` kapalı; dizin ve mahalle sayfaları açık.

| Toplayıcı | Sonuç |
|---|---|
| Plaj (`0ca63d2e…`) | Başarılı, 2 sn. Kaynakta 70 harita noktası; 53 kıyı erişimi kaydedildi, 17 kapsam dışı. Kaynağın güncelleme metni: "Sep 21, 2026 6:56:10 pm". |
| Mahalle, 1. çekim (`b9ab4b58…`) | Başarılı, 6 sn. Dizinde 16 kayıt; 13 mahalle kaydedildi, 3 kapsam dışı (Miramar Beach, Sandestin, Seascape). Tanınmayan mahalle yok. 14 ham yanıtın hepsi HTTP 200; manifest ve 14 alt dosyanın SHA-256'sı doğrulandı (manifest `81e32ffb…`). 13 mahallenin hepsinde kısa tanıtım ve sayfa tanıtım metni var; 14 farklı kaynak etiketi. En yeni kayıt değişikliği: 2026-09-14 (Santa Rosa Beach). |
| Mahalle, 2. çekim (`4473ae75…`) | Başarılı. Fark özeti: 0 eklendi · 0 kaldırıldı · 0 değişti · 13 aynı. |

13 mahallenin listesi: [mahalleler.csv](mahalleler.csv). Ekran görüntüleri: [Mahalleler sekmesi](mahalleler-sekmesi.png), [plaj ekranında eşleme](plaj-mahalle-eslemesi.png), [plaj ekranı, Seagrove filtresi](plaj-mahalle-filtre-seagrove.png).

### Migration denemesi (gerçek verinin kopyası)

`data/studio.sqlite3`, GÖREV-01 yöntemiyle (`mode=ro&immutable=1` + backup API) `work/gorev-03/db-kopya.sqlite3` olarak kopyalandı; kopya ayrı bir deneme klasöründe yeni sürümle `--data-dir` üzerinden açıldı. Uygulama önce yedek aldı (`studio-v6-….sqlite3`), sonra v6 → v7 yükseltmesini yaptı. Gerçek `data/` klasöründeki dosyaların boyut ve değişiklik zamanları kopyalamadan önce ve görev sonunda aynıydı.

| Tablo | Önce (şema 6) | Sonra (şema 7) |
|---|---:|---:|
| sources | 8 | 9 |
| source_history | 4 | 4 |
| jobs | 9 | 9 |
| source_runs | 6 | 6 |
| beach_records | 159 | 159 |
| weather_locations | 6 | 6 |
| weather_forecast_periods | 1020 | 1020 |
| weather_alerts / weather_alert_anchors | 0 / 0 | 0 / 0 |
| restaurant_records | 138 | 138 |
| restaurant_regions | 141 | 141 |
| regions / destinations / destination_weather_anchors | 13 / 1 / 3 | 13 / 1 / 3 |
| entities / entity_sources / metadata | 0 / 0 / 1 | 0 / 0 / 1 |
| neighborhood_records | — | 0 (yeni tablo) |

- `foreign_key_check`: önce de sonra da boş. `integrity_check`: ok.
- Eski 8 kaynak satırı birebir aynı kaldı; eklenen tek satır "South Walton · Mahalleler" (HTML, toplayıcı bağlı). Arşivdeki manuel test kaynağı korundu.
- API'den görünürlük: 3 plaj sürümü (her biri 53 kayıt; son iki sürüm arasında fark 53 aynı), 2 hava sürümü (her biri 3 nokta, 42 dönem, 468 saatlik kayıt) ve 1 restoran sürümü (138 kayıt) görünür kaldı. Kenar çubuğunda "4 kaynak hazır" görünüyor.
- Gerçek veritabanı, kullanıcı uygulamanın yeni sürümünü ilk açtığında kendi yedeğini alarak aynı şekilde yükselecek.

## Adım 5 — Plaj erişimi–mahalle eşleme katmanı

- Eşleme dosyası: `studio/destinations/thirty_a_beach_neighborhoods.csv` (30A profilinin yanında; profil dosyayı gösterir; paket verisine eklendi). Sütunlar: `external_id, plaj_adi, bolge_id, yontem, kaynak, not, belirsiz`.
- Üretici betik: `tools/plaj_mahalle_esleme.py` (veritabanını salt okunur açar). Dosya bir kez üretildi ve commit edildi; uygulama yalnız okur, yeniden hesaplamaz. Plaj toplayıcısı ve `beach_records` değişmedi.
- Girdi: canlı denemedeki plaj çekimi (53 kimlik, ad ve koordinat gerçek veritabanı kopyasıyla ve GÖREV-02 önizlemesiyle birebir aynı) ve mahalle çekimi `4473ae75f66b40d49c75f5fa2444c6db`.

**Sonuç:** 53 erişimin 9'u "resmî rehber", 44'ü "program türetimi"; 2 satır belirsiz (Greenwood - 21 → Seaside, Andalusia - 20 → Seagrove).

| Mahalle | Erişim | | Mahalle | Erişim |
|---|---:|---|---|---:|
| Dune Allen | 6 | | Seaside | 10 |
| Gulf Place | 4 | | Seagrove | 14 |
| Santa Rosa Beach | 3 | | WaterSound | 0 |
| Blue Mountain Beach | 4 | | Seacrest | 3 |
| Grayton Beach | 4 | | Alys Beach | 0 (kısıt) |
| WaterColor | 0 | | Rosemary Beach | 0 (kısıt) |
| | | | Inlet Beach | 5 |

- Kısıt bir kez devreye girdi: Winston Lane - 4 için en yakın nokta Rosemary Beach'ti; atlandı, Inlet Beach seçildi ve notta yazıldı.
- Belirsizlik, atanabilir en yakın iki aday arasında ölçüldü (Alys/Rosemary atlandıysa ölçüme girmez, notta yazılır).

**Doğrulama:** Aynı türetme 9 resmî eşlemeye uygulandı: **8'i aynı**, 1'i farklı.

| Erişim | Resmî rehber | Türetme | Not |
|---|---|---|---|
| Walton Dunes - 8 | Seagrove | WaterSound | WaterSound noktasına 0,0157°, Seagrove'a 0,0215° |

Tam tablo: [esleme-dogrulama.csv](esleme-dogrulama.csv). Bu oran temkinli okunmalı: aynı çıkan 8 erişim bölgesel erişimdir ve mahalle noktalarına çok yakındır; türetilen 44 erişimin 43'ü ise mahalle erişimidir ve farklı çıkan tek örnek de resmî listedeki tek mahalle erişimidir.

- Plaj ekranı: her erişimin yanında mahalle ve yöntem etiketi ("resmî rehber" / "program türetimi", gerekiyorsa "belirsiz"), mahalle filtresi; dosyada olmayan yeni kimlik "eşlenmemiş" görünür. Eşleme dosyasının okunması ve ekrandaki gösterim test edildi.
- Belge: yöntem, kısıt, doğrulama ve video dili notu `docs/M7-MAHALLE-VERISI.md` içinde. Video dili: "resmî rehber" eşlemeleri kaynak gösterilerek söylenebilir; "program türetimi" yalnız yaklaşık konum bilgisidir.

## Adım 6 — Belgeler

`CALISMA_MANTIGI.md` (durum tablosu, 30A'ya özel connector listesi, 9.4 Mahalleler, 9.5 eşleme, stable/test durumu, migration denemesi, belge indeksi), `README.md`, `docs/DEVIR/05` (stable ve aktif dal, "v0.7.0 — mahalle verisi ve plaj–mahalle eşlemesi" bölümü) güncellendi; yeni `docs/M7-MAHALLE-VERISI.md` yazıldı. Eski `v0.7-lodging-inventory` dalıyla karışmaması için sürüm her yerde bu adla anıldı. Eski durumu "güncel" diye yazan küçük yerler de düzeltildi: `docs/DEVIR/07` (aktif dal, connector listesi), `docs/DEVIR/02` (şema 7, yeni tablo ve API uçları), `docs/ASAMALAR.md` (yeni aşama). 7 Ekim konaklama kararı bu belgelerin güncel durum kısımlarına da not edildi.

## Testler ve CI

| | Python | Frontend |
|---|---:|---:|
| main (v0.6.0 kodu) | 289 | 19 |
| `gorev-03-mahalleler` | **390 geçti** | **29 geçti** |

- Yeni: 68 mahalle toplayıcısı testi, 28 eşleme testi, 5 destinasyon yalıtımı testi; 10 frontend testi. Eski testler şema 7 ve yeni kaynak için güncellendi (eski kaynak satırlarının birebir korunduğu ayrıca doğrulanıyor).
- CI: main @ `62d6b7b` başarılı (`37598345273`); dal @ `830b9b3` başarılı (`37601010398`); dal @ `a6e06f9` başarılı (`37604040730`). Son commit yalnız belge ve teslim dosyalarını içerir; CI sonucu GitHub Actions'ta görülebilir.

## Beklenmedik durumlar

1. Bir tam test çalıştırmasında mevcut restoran testlerinden biri (`test_api_raw_hash_rollback_and_previous_run`) bir kez başarısız oldu; tek başına ve sonraki dört tam çalıştırmada geçti. Muhtemelen test yardımcısının 3 saniyelik bekleme sınırı yük altında yetmedi. Bu testte değişiklik yapılmadı.
2. Ekran görüntüsü için başsız Edge çöktü ve `work/` altında geçici bir tarayıcı profili bıraktı; profil silindi. Görüntüler başsız Chrome ile alındı. Repoya etkisi yok.
3. Canlı dizindeki adlar şu an kanonik adlarla birebir aynı; yazım tablosu (Blue Mountain, Watercolor, Watersound) yalnız önlem olarak duruyor.
4. Türetme WaterColor ve WaterSound'a hiç erişim atamadı. Bu yöntemin sonucudur; "orada plaj erişimi yok" anlamına gelmez (rehber bu iki başlıkta yalnız otopark bilgisi veriyor).
5. Rehberin Seacrest başlığı ad vermeden "3 neighborhood beach access" diyor; türetme de Seacrest'e 3 erişim atadı. Adlar rehberde olmadığı için bunu doğrulama saymadım.

## Yöneticinin karar vermesi gereken konular

1. `gorev-03-mahalleler` dalının main'e alınması ve `v0.7.0` etiketi.
2. Eşleme yönteminin kabulü: doğrulama 8/9, farklı çıkan örnek bir mahalle erişimi. Program türetimi satırları için ek önlem isteniyor mu (ör. sınıra yakın erişimleri elle gözden geçirme veya Walton County TDC'den resmî liste istemek)?
3. Belirsizliğin yalnız atanabilir adaylar arasında ölçülmesi (Alys/Rosemary dışarıda) uygun mu? Belirsiz 2 satır yaklaşık konum olarak mı kalsın?
4. Eşleme dosyasındaki "kaynak" run kimliği (`4473ae75…`) geçici deneme klasöründeki çekime ait; gerçek veritabanında bu kimlik yok. Kullanılan 13 nokta `mahalleler.csv` içinde kayıtlı. Kullanıcının uygulaması ilk gerçek mahalle çekimini yaptıktan sonra dosya o çekimle yeniden üretilsin mi?
