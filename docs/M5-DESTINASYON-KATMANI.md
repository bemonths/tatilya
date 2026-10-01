# M5 — Destinasyon katmanı · v0.6.0

Destinasyon, kaynakların ve veri geçmişinin ait olduğu çalışma bağlamıdır. 30A artık bu modelin ilk kaydıdır: `id=30a`, ad `30A`, alt başlık `South Walton, Florida`. Production kurulumunda yalnızca bu destinasyon vardır. `test-coast` ve `third-coast` yalnız test veritabanlarında oluşturulur.

## Veri modeli ve migration

- `destinations`: stabil ID, ad, alt başlık, enabled, sıralama ve zaman damgaları.
- `regions`: mevcut ID'ler korunur; ad `(destination_id,name)` kapsamında benzersizdir. Farklı destinasyonlarda Downtown kullanılabilir.
- `sources`: ID, kullanıcı alanları, arşiv durumu ve version korunur. URL `(destination_id,url)` kapsamında benzersizdir. Aynı NWS URL'si başka bir destinasyonda tekrar kullanılabilir.
- `scope_region_id`: NULL tüm destinasyon kapsamıdır. Eski region metni canonical ada birebir eşitse ID atanır; eşleşmeyen metin korunur ve tahmin yapılmaz. Composite FK başka destinasyonun bölgesini seçmeyi engeller. `region` metni uyumluluk için kalır.
- `jobs`: kaynak toplaması source.destination_id değerini taşır. Kaynaksız eski işler 30a'ya bağlanır. Aktif katalog kontrolü kilidi `(destination_id,kind)` kapsamındadır; kaynak toplama kilidi source_id kapsamında kalır.
- `source_runs`: destination_id oluşturulurken kaydedilen tarihsel provenance'dır. Diff hem source_id hem destination_id ile önceki başarılı çekimi arar.
- `entities`: NOT NULL destination FK; aynı canonical_name farklı destinasyonlarda bulunabilir. Bölge ilişkisi de aynı destinasyonda olmalıdır. Entity matching eklenmedi.
- `destination_weather_anchors`: `(destination_id,anchor_key)` kimliği, etiket, koordinatlar, nullable provenance referans/adı, sıralama ve enabled.

v1–v5 açılışında önce SQLite backup API ile `data/backups/` altında sürüm etiketli yedek alınır. v6 migration çağıranın tek transaction'ı içinde çalışır. SQLite tablo yeniden kurma protokolü nedeniyle FK enforcement transaction öncesinde kapatılır; tüm referanslar commit öncesi `foreign_key_check` ile doğrulanır. Sonraki bağlantılarda foreign_keys her zaman ON'dur. Hata bütün DDL/veri aktarımını geri alır; v5 ve yedeği kullanılabilir kalır.

Yeni FK/UNIQUE/NOT NULL kısıtları için tablolar kimlikleri ve eski alanları korunarak yeniden kurulur. Ham dosyalar taşınmaz. Source/run ID, hash, raw path, job log, source_history ve domain snapshot değerleri değiştirilmez. Başlangıç onarımı yalnızca 30A restoran kaynağındaki değiştirilmemiş eski default method/notes alanlarına uygulanır; yeni destinasyonlara seed veya onarım sızmaz.

## Profil, SQLite ve connector context

`studio/destinations/thirty_a.py` ilk kurulum ve migration varsayılanlarını içerir: metadata, 13 bölge, 7 kaynak ve 3 hava örnek noktası. `regions.py`, `catalog.SEEDS` ve `weather_anchors.py` eski import yolları için uyumluluk dışa aktarımlarıdır. Generic runtime, canonical bölge ve hava noktalarını SQLite'tan `Database.context(destination_id)` ile okur.

`ConnectorContext` bir işin destination, canonical_regions ve weather_anchors bilgilerini taşır. JobQueue her connector'a bu context'i verir; sunucu genelinde seçili destinasyon değişkeni yoktur.

- **NWS generic:** source'un destinasyonundaki etkin hava noktalarını kullanır. Nokta yoksa HTTP isteğinden önce açık hata verir. Kaynak konum/ad referansı olmayan noktalar da desteklenir. Eski snapshot tablolarındaki source_beach_* alan adları uyumluluk için korunur. UI geçmiş çekimin kendi konumlarını gösterir.
- **South Walton Beaches/Restaurants specific:** kaynak kimliğine ek olarak `destination_id=30a` gerekir. Başka destinasyona aynı URL eklenmesi connector'ı bağlamaz. Restoran toplamasının hedef bölgeleri context'ten alınır; profil içindeki kaynak filtre yapısı doğrulama için kullanılır.

## API ve UI

`GET /api/destinations` etkin destinasyonları döndürür. Bootstrap ve sources/jobs/source-runs/collections/weather-runs/restaurant-runs liste uçları `destination_id` ile filtrelenir; parametre yoksa kurulumun varsayılanı kullanılır. Bilinmeyen veya disabled ID, 404 döndürür. SSE `/api/events?destination_id=...` yalnız o destinasyonun işlerini yayınlar.

Bootstrap yalnız seçili destinasyonun kaynak, bölge, job ve çekim listelerini taşır. Büyük snapshot kayıtları ID ile detay uçlarından tembel yüklenir. ID uçları eski kimliklerle çalışır ve run içinde destination_id bulunur. Bu yerel uygulamadaki destinasyon ayrımı bir kullanıcı yetkilendirme sistemi değildir.

Source POST için destination_id zorunludur. UI global seçimden gönderir. PUT eski istemciler için destination_id olmadan mevcut bağlamı kullanabilir; farklı destination_id ile taşıma reddedilir. Kapsam dışı scope_region_id reddedilir. Arşiv/geri alma yalnız seçilen kaydı etkiler.

Üstteki gerçek dropdown mevcut tasarımı korur. Seçim `localStorage["studio.destination_id"]` içinde tutulur; diğer istemcilerin server bağlamını değiştirmez. Geçersiz kayıtlı seçimde UI açıkça varsayılan bootstrap'a döner. Hash rotaları değişmez. Geçişte kaynak filtreleri, detaylar, veri sürümü seçimleri ve snapshot'lar sıfırlanır; eski SSE kapatılır. İstek nesli değiştiğinde geç gelen HTTP yanıtları kullanılmaz. Kaynaksız destinasyonlarda 30A verisi yerine veri türüne uygun boş durum gösterilir.

## Yeni destinasyon ekleme kontrol listesi

1. Stabil ID ile destination kaydı ve etkinlik/sıra bilgisi tanımla.
2. O destinasyona ait stabil region ID'lerini ekle; ad benzersizliği yalnız destinasyon içindedir.
3. Kaynakları açık destination_id ile ekle; aynı URL'nin başka destinasyonda olabileceğini koru.
4. NWS kullanılacaksa doğrulanmış koordinatlar ve provenance ile weather anchor kayıtlarını ekle.
5. Generic connector'ları yeniden kullan; NWS için yeni connector yazma.
6. Kaynak yapısı özel ise destination ve güvenli source identity kontrolü olan connector ekle.
7. Mock isolation, migration, stale response ve ayrı TEMP ağ/browser smoke testlerini çalıştır.

Bu sürümde destinasyon yönetim ekranı/API yazma uçları yoktur; yeni yapılandırmalar kontrollü seed/migration veya yönetim script'i üzerinden SQLite'a eklenir. İkinci production destinasyonu, yeni domain connector'ı, scheduler, AI ve ürün adı değişikliği eklenmedi.

## Doğrulama

Gerçek v5 DB'nin ayrı kopyasında bütün eski satır alanları karşılaştırıldı; hiçbir fark olmadı. Kaynak 8, history 4, job 9, run 6, plaj 159, hava konumu 6, tahmin 1020, restoran 138 ve restoran–bölge ilişkisi 141 olarak korundu. FK kontrolü temiz; initialize ikinci kez ek değişiklik yapmadı. Production DB yalnız bu testten sonra yükseltildi.

Sentetik testler aynı URL/region adını farklı destinasyonlarda, API/bootstrap/job/audit/run/diff yalıtımını, immutable source destination ve generic NWS koordinatlarını doğrular. Eski v1–v4 migration zincirleri, v5 rollback/backup ve mevcut connector davranışları test edilir.

Tarayıcıda gerçek 30A arşivi, plaj/hava geçmişi ve 138 restoran snapshot'ı açıldı. Ayrı TEMP ortamında seçim kalıcılığı, aynı rotada destinasyon geçişi, filtre sıfırlama, boş durumlar ve seçili destinasyona kaynak ekleme doğrulandı. Production'da yeni çekim yapılmadı. Ayrı TEMP canlı smoke: 53 plaj kaydı, tek NWS noktasında 170 tahmin, Dune Allen için 2 restoran; üç iş de tamamlandı. Bunlar kabul için sabit kayıt sayıları değildir.
