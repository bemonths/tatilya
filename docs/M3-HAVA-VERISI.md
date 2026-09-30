# M3 — NWS hava verisi · v0.4.0

İki çalışan connector vardır: Visit South Walton plaj sayfasının HTML içindeki JSON verisi ve National Weather Service resmî API'si. NWS tahmini yerelde üretilmez veya AI ile tamamlanmaz. [Resmî NWS API sözleşmesi](https://www.weather.gov/documentation/services-web-api) kullanılır.

## Örnek noktaların kaynağı

Bunlar **30A koridoru için hava örnek noktalarıdır**, canonical mahalle merkezi değildir. Visit South Walton'dan canlı alınan 53 kıyı erişim kaydının boylam sıralamasına göre batı/orta/doğu seçilmiştir. Kodda `weather_anchors.py` bu provenance'ı taşır; her run'ın lokasyonları koordinatları ve plaj kimliklerini ayrıca saklar. Mevcut plaj verisi değiştirilmez, gelecekteki bir çekim bu sabitleri sessizce yeniden seçmez.

| Anahtar | Etiket | Kaynak plaj | Kaynak kimliği | Enlem | Boylam |
|---|---|---|---|---|---|
| west | Batı 30A | Stallworth Preserve | 5c81ab02f836f9166348e96c | 30.35548 | -86.2638 |
| central | Orta 30A | Holly - 24 | 5c81a5acf836f90dc03cccca | 30.3167 | -86.12845 |
| east | Doğu 30A | Lupine - 1 | 5c81a6a2f836f9166348e961 | 30.2713 | -85.99579 |

Kaynak: https://www.visitsouthwalton.com/beach-bay-access-locations/

## İstek akışı

Her nokta sırayla işlenir:

1. `GET https://api.weather.gov/points/{lat},{lon}`: cwa, gridX/Y, timeZone ve forecast/forecastHourly/forecastGridData/forecastZone/county/observationStations adresleri saklanır.
2. Points yanıtından alınan `forecast`: tüm mevcut dönemler saklanır, 14 kayıt varsayılmaz.
3. Points yanıtından alınan `forecastHourly`: tüm saatlik dönemler saklanır, sabit gün/kayıt sayısı varsayılmaz.
4. `GET https://api.weather.gov/alerts/active?point={lat},{lon}`: boş features normaldir; aynı uyarı kimliği run başına tekilleştirilir ve etkilenen anchor'larla ilişkilendirilir. Tekilleştirmede ilk görülen içerik tutulur; sonraki yanıtlar ham pakette bulunur.

Header: `User-Agent: 30AStudio/0.4 (+https://github.com/bemonths/tatilya)`, `Accept: application/geo+json`. API key yoktur. Sadece HTTPS api.weather.gov, varsayılan/443 port ve credentials içermeyen URL izlenir. Redirect en fazla 3, alert pagination en fazla 5 sayfadır; limit aşımında eksik veri başarı sayılmaz. NWS points koordinatları yuvarlanmış URL'ye yönlendirebilir; verilen sabit örnek koordinatları değiştirilmez, gerçek istek URL'si audit paketine yazılır.

TLS açık; bağlantı 10 saniye ve diğer HTTP işlemleri 20 saniye timeout. Her yanıt en fazla 5 MB. JSON/content-type, gerekli alanlar, benzersiz zaman aralığı, ISO offset ve yüzdeler doğrulanır. 429/kalıcı HTTP hatası tekrar edilmez; ağ/timeout/5xx en fazla bir kez 0.5 saniye beklenerek tekrarlanır. Bekleme ve yanıt okuma sırasında iptal denetlenir.

## Saklama ve atomiklik

Generic source_collection işi, source_runs ve mevcut tek çalışanlı kuyruk kullanılır. WeatherConnector kimliği `nws-weather`, sürümü `nws-weather/1`, yöntemi API'dir. `CollectionResult.related` noktaları ve uyarıları taşır; records yalnızca forecast kayıtlarını içerir. Domain kayıtları ve başarılı iş/run bitişi aynı transaction'dadır. Bir anchor'ın gerekli yanıtı başarısızsa veya domain yazımı hata verirse kısmi kayıt yayımlanmaz. Önceki başarılı run aynen korunur.

Şema 4 tabloları: weather_locations; weather_forecast_periods (period/hourly); weather_alerts; weather_alert_anchors. Foreign key'ler run, run+anchor ve run+alert ilişkilerini korur. v3→v4, bu tabloları ekler ve aşağıdaki koşullara uyan kaynak varsayılanlarını günceller. v1/v2 zinciri ve fresh DB de v4'e ulaşır; mevcut DB yükseltilmeden SQLite backup alınır.

record_count = normal + saatlik dönem sayısı. Metadata: anchors, forecast_period_count, hourly_period_count, alert_count, source_timestamps, anchor_provenance. generatedAt/updateTime her anchor ve tahmin türü için korunur. source_updated, normal forecast'lerin updateTime (yoksa generatedAt) değerleri arasındaki en yenisidir. NWS zamanı yoksa null kalır; bizim çekim zamanımızla doldurulmaz.

ISO zamanlar kaynak offset'iyle, null ölçümler null olarak saklanır; 0 yağış olasılığı kaybolmaz. Dewpoint değeriyle birlikte kaynak birimi de saklanır. UI dereceleri kaynağın temperatureUnit değeriyle gösterir; örtük dönüşüm yapılmaz.

Ham paket `data/raw/<run-id>/source.json`: sıra, anchor, request_kind, gerçek URL, HTTP durum/content-type, fetched_at ve ham response body metni. Tamamlanan her yanıt atomik dosya değişimiyle korunur; hash yalnızca Database.record_raw_artifact() tarafından son dosyanın gerçek baytlarından hesaplanır. Hatalı JSON da pakette incelenebilir; tamamlanmayan/oversize yanıtın tüm baytları saklanmaz.

## Ekran/API

Veri toplama → Plaj erişimleri / Hava. Hava sekmesinde başarılı sürümler, üç nokta seçimi, kaynak plaj/grid/timezone, tüm dönemler ve ilk 24 saatlik kayıt görünür. DB'de tüm saatlik kayıtlar vardır. Tahmin/uyarı zamanları points.timeZone ile biçimlenir; çekim listesinde UTC açıkça belirtilir. Eksik/geçersiz zone halinde ham kaynak ISO zamanı gösterilir, tarayıcının yerel zone'u kullanılmaz.

Uyarılar seçili run/anchor'a aittir; geçmiş bir çekim canlı uyarı durumu değildir. WeatherConnector.diff_enabled=False: kayan tahmin penceresine plaj tipi added/removed özeti uygulanmaz. Generic diff endpoint açıklamalı available=false döndürür. İşler paneli hava sonucunu #collect/weather, plaj sonucunu #collect açacak şekilde yönlendirir.

GET /api/weather-runs başarılı hava run'larını; /{id} run/locations/forecast_periods/hourly_periods/alerts/diff'i; /{id}/raw ana JSON paketini sunar. Başka domain veya başarısız run bu uçlarda 404 döner. Ham indirme raw dizininin dışına çıkamaz. Generic /api/source-runs uçları korunur.

## Doğrulama ve sınırlar

Pytest sentetik JSON/MockTransport kullanır, no_real_http fixture korunur. Migration, rollback, null/0, URL güvenliği, retry/iptal, bundle/hash, metadata, API ve generic kuyruk testleri vardır. Node yardımcı testleri domain yönlendirmesi, timezone ve escaping'i doğrular.

30 Eylül 2026 bağımsız canlı smoke testi başarılı oldu: 3 noktada 42 dönem + 468 saatlik kayıt (510 toplam), 0 aktif uyarı. Bu sayılar yalnızca test anına aittir, hedef veya sabit sayı değildir. Smoke testi pytest'e dahil değildir; ilk bağımsız deneme kullanıcı DB'sine yazmadı.

Henüz yok: NOAA tarihsel iklimi, observation station/current conditions, scheduler, Claude/OpenAI, Playwright, restoran/konaklama connector'ları, canonical mahalle merkezi/polygon üretimi. Forecast/grid güncellenebilir; veriler bir çekim anının değişken tahminleridir.

Ek uygulama doğrulaması: yedekli kullanıcı DB v3→v4 yükseltmesinde mevcut tüm tablo satırları ve ham dosyalar birebir korundu. Uygulamanın Hava düğmesinden generic source_collection ile gerçek NWS çekimi başarılı oldu: 510 kayıt, 0 uyarı; diskteki raw SHA-256 doğrulandı. Üç anchor ve doğru job hedefi tarayıcıda kontrol edildi. Ayrı sentetik UI verisinde iki sürüm arasında geçiş ve aktif uyarı görünümü doğrulandı. Son yerel kontroller: 117 pytest + 4 Node yardımcı testi geçti. Sentetik veriler kullanıcı DB'sine eklenmedi.

Varsayılan kaynak düzeltmesi: temiz kurulumda NWS yöntemi API, South Walton plaj yöntemi JSON olarak seed tanımından alınır. v3→v4 migration yalnızca tam kaynak URL'si eşleşen ve yöntemi hâlâ `Belirlenecek` olan bu iki kaydı günceller. NWS notu yalnızca eski varsayılan açıklamayla birebir aynıysa yeni tahmin/uyarı açıklamasına çevrilir. Not ve yöntem koşulları bağımsızdır; kullanıcı notu veya seçtiği yöntem korunur. Diğer kaynak alanları ve source_history değiştirilmez. Yükseltme öncesi yedek eski değerleri içerir. Zaten şema v4 olan veritabanlarında bu migration yeniden çalıştırılmaz.
