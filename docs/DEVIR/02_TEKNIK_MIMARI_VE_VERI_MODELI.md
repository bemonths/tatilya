# Teknik Mimari ve Veri Modeli

## Teknoloji

- Python 3.12+
- FastAPI
- Uvicorn
- SQLite
- HTTPX
- HTML/CSS/Vanilla JS
- SSE
- ThreadPoolExecutor
- pytest
- Node built-in frontend tests

Frontend için bundler yoktur.

## Yerel başlatma

Proje yolu:

```text
C:\Users\1\Documents\Codex\2026-09-29\referenced-chatgpt-conversation-this-is-an\outputs\30a-studio
```

Başlatma:

```text
baslat.bat
```

Varsayılan server:

```text
127.0.0.1:8830
```

Varsayılan DB:

```text
data/studio.sqlite3
```

## Üst seviye modüller

```text
studio/
├─ app.py
├─ database.py
├─ jobs.py
├─ models.py
├─ migrations.py
├─ migration_v6.py
├─ destinations/
├─ sources/
└─ web/
```

Ana sorumluluklar:

- `app.py`: HTTP API, bootstrap, domain endpoint'leri, SSE.
- `database.py`: SQLite erişimi, CRUD, jobs/runs, diff, raw artifact izi.
- `jobs.py`: generic toplama kuyruğu.
- `sources/base.py`: Connector Protocol + CollectionResult.
- `sources/registry.py`: source → connector eşleştirme.
- `destinations/`: profile ve runtime context.
- `web/`: vanilla JS UI.

## Multi-destination veri modeli

### destinations

Stabil destination kimliği.

Production: `30a`.

### regions

Destination'a bağlı canonical alt bölgeler.

Önemli:

```text
UNIQUE(destination_id, name)
```

Global region-name uniqueness yoktur.

30A canonical bölgeleri:
- Dune Allen
- Gulf Place
- Santa Rosa Beach
- Blue Mountain Beach
- Grayton Beach
- WaterColor
- Seaside
- Seagrove
- WaterSound
- Seacrest
- Alys Beach
- Rosemary Beach
- Inlet Beach

### sources

Başlıca alanlar:
- id
- name
- url
- category
- region legacy display text
- method
- cadence
- notes
- enabled
- version
- timestamps
- destination_id
- scope_region_id

URL uniqueness:

```text
UNIQUE(destination_id, url)
```

Aynı NWS URL'si iki destinasyonda kullanılabilir.

### source_history

Source edit snapshot'ları.

### jobs

Asenkron iş kaydı:
- catalog audit
- source collection

Destination provenance taşır.

### source_runs

Her kabul edilmiş veri çekiminin tarihsel kaydı.

Başlıca alanlar:
- id
- source_id
- job_id
- destination_id
- status
- started_at
- fetched_at
- finished_at
- source_url
- connector_name
- connector_version
- raw_path
- raw_sha256
- source_updated
- record_count
- excluded_count
- metadata
- error

### entities / entity_sources

Gelecekte farklı kaynaklardaki aynı gerçek dünyadaki varlığı bağlamak için temel.

Henüz otomatik entity matching yoktur.

### destination_weather_anchors

NWS gibi generic connector'ların destination'a göre kullanacağı koordinatlar.

### destination_climate_stations / destination_storm_corridors (şema 8)

İklim connector'larının destination'a göre kullanacağı istasyonlar (`kind`: normals / water_temperature; kimlik, ad, rol, koordinat, koridora uzaklık ve uzaklık tanımı, ilk yıl) ve kasırga kıyı koridoru (batı/doğu uç noktaları ve referansları, yarıçaplar). 30A değerleri profilden v8 migration'ıyla bir kez yazılır.

## ConnectorContext

Runtime source of truth SQLite'tır.

`ConnectorContext`:
- destination
- canonical_regions
- weather_anchors
- climate_stations (şema 8)
- storm_corridor (şema 8)

taşır.

Connector'ın global `REGIONS` veya hard-coded weather point import etmesi yerine context kullanması beklenir.

## Connector sözleşmesi

Connector:

```text
supports(source)
collect(source, raw_path, progress, canceled, context=...)
store_records(...)
read_records(...)
comparison_value(...)
```

ve metadata:
- name
- version
- raw_filename
- method
- diff_enabled
- isteğe bağlı `diff_reason` (kayıt farkı kapalıysa API'de gösterilen gerekçe)

### Generic / destination-specific ayrımı

Generic:
- `nws-weather`
- `ncei-climate-normals`, `ndbc-water-temperature`, `hurdat2-storm-proximity` (şema 8)

Destination-specific:
- `south-walton-beaches`
- `south-walton-restaurants`
- `south-walton-neighborhoods`

Specific connector `destination_id=30a` olmadan bağlanmaz.

## Job sistemi

ThreadPoolExecutor bugün tek worker ile çalışır.

Akış:
1. source etkin mi?
2. registry connector buluyor mu?
3. job + queued source_run oluştur.
4. queue collect başlatır.
5. raw dosya yazılır.
6. parse/validate.
7. domain kayıtları ve run success tek transaction.
8. job result oluşturulur.

### İptal

İptal:
- DB status'ünü değiştirir,
- connector checkpoint'lerde bunu görür,
- geç sonuç publish edilmez.

## Raw artifact modeli

Plaj:

```text
raw/<run>/source.html
```

Hava:

```text
raw/<run>/source.json
```

Restoran:

```text
raw/<run>/manifest.json
raw/<run>/listing/...
raw/<run>/detail/...
```

Ana `raw_sha256`, DB katmanında gerçek dosyadan hesaplanır.

Amaç:
- provenance,
- tekrar inceleme,
- parser değişikliği analizi,
- kaynak yapısı değişikliği teşhisi.

## Diff

Diff:
- aynı source_id,
- aynı connector,
- aynı destination,
- önceki başarılı run

üzerinden hesaplanır.

Başarısız/iptal run atlanır.

External ID kümeleri:
- added
- removed

ortak ID alan farkları:
- changed
- unchanged

Weather rolling forecast için diff disabled.

## Domain tabloları

### Beach

`beach_records`

Alanlar:
- external_id
- name
- city/source region text
- address
- lat/lon
- access_type
- features
- nullable canonical_region_id

### Weather

- weather_locations
- weather_forecast_periods
- weather_alerts
- weather_alert_anchors

### Restaurants

- restaurant_records
- restaurant_regions

Description nullable'dır.

### Neighborhoods (v0.7.0, şema 7)

- neighborhood_records: kaynak kimliği, permalink, ad, canonical_region_id, nullable summary, temsilî nokta (mahalle merkezi değil), tags (JSON dizi), nullable source_modified, nullable page_intro

Plaj–mahalle eşlemesi tablo değildir; `beach_records.canonical_region_id` NULL kalır.

### Climate (v0.8.0, şema 8; kasırga evre kuralı v0.9.0, şema 9)

- climate_normal_stations, climate_normal_values: istasyon × ay × değişken; nullable value, unit, completeness_flag, measurement_flag, years
- water_temperature_stations (denenen yıllar, dosyası bulunan/olmayan yıllar), water_temperature_months (yıl-ay ortalaması °C, ölçüm sayısı, gün sayısı); ham ölçümler tabloda değil, ham dosyalarda
- storm_corridor_snapshots (koridor, yarıçaplar, HURDAT2 dosya adı), storm_passages (fırtına × yarıçap: ilk giriş zamanı/ayı, en yakın uzaklık, daire içi en yüksek rüzgâr, sınıf, evre)

Ayrıntı: `docs/M8-IKLIM-VERISI.md`. Şema 9'da `storm_passages.non_tropical_only` (0/1): daireye yalnız tropikal olmayan evrede giren fırtına.

### Referans tablosu (v0.9.0)

Tablo değildir: `studio/destinations/thirty_a_references.csv` (elle doldurulan, repoda sürümlenen olgular) ve `thirty_a_tdt_collections.csv` (aylık turist vergisi). Genel okuyucu ve doğrulayıcı `studio/destinations/references.py`. Ayrıntı: `docs/M9-REFERANS-TABLOSU.md`.

### Konaklama (v0.10.0, şema 10; şema 11'de üç sütun)

Yapılandırma: `destination_lodging_sources` (clone adresi), `destination_lodging_locations` (kaynağın konum filtresi adı → kanonik bölge), `destination_lodging_windows` (örnek tarih pencereleri). Anlık görüntü: `lodging_snapshots`, `lodging_windows` (`searched` / `skipped_past`), `lodging_filters` (pencere × filtre), `lodging_listings`, `lodging_search_results` (pencere × filtre × ilan; liste ve canlı fiyat alanları), `lodging_calendars`, `lodging_rate_months` (ilan × ay takvim özeti; günlük değerler saklanmaz), `lodging_calendar_windows`. Özetler saklanmaz, okuma anında hesaplanır. Şema 11'de `lodging_listings`'e şirket ilan sayfası (`url`) ve telefonlar (`phone`, `toll_free`) eklendi. Ayrıntı: `docs/M10-KONAKLAMA-PROFILI.md`.

### Konaklama fiyatları (v0.11.0, şema 11; `gorev-08-konaklama-fiyat` dalı)

Yapılandırma: `destination_agency_sites` (alan adı, şirket adı, uyarlayıcı, etkin). Çekim: `agency_rate_snapshots` (girdi konaklama çekimi, sorgu günü), `agency_rate_windows`, `agency_rate_companies` (şirket bazında sonuç), `agency_rate_listings` (Book>Direct ilanı, bağlantı, sayfa durumu, platform kimliği), `agency_rate_quotes` (ilan × pencere: müsaitlik, kira, ücretler, vergiler, toplam, isteğe bağlı kalemler, kurallar, ham yanıt SHA-256'ları). `job_waits`: çalışan bir işin kullanıcı doğrulaması beklediği site. Genel çekirdek `studio/sources/agency_rates.py`, uyarlayıcılar `agency_adapters.py`, görünür tarayıcı `browser_verification.py` (isteğe bağlı Playwright). Ayrıntı: `docs/M11-KONAKLAMA-FIYATLARI.md`.

## Migration stratejisi

Şema yükseltmeden önce:
- SQLite backup API ile yedek,
- transaction,
- gerekiyorsa table rebuild,
- `PRAGMA foreign_key_check`,
- hata halinde rollback.

Stable şema: `10` (v0.10.0 ve main): v7 → v8 iklim tablolarını, 30A iklim yapılandırmasını ve üç iklim kaynağını ekler; v8 → v9 `storm_passages.non_tropical_only` sütununu ekler (kasırga evre kuralı); v9 → v10 konaklama yapılandırma tablolarını (`destination_lodging_sources`, `_locations`, `_windows`), sekiz konaklama anlık görüntü tablosunu ve 30A Book>Direct kaynağını ekler. `gorev-08-konaklama-fiyat` dalında şema `11` (gerçek DB 8 Ekim 2026'da şema 11'e yükseltildi): v10 → v11 `lodging_listings`'e `url`, `phone`, `toll_free` sütunlarını, `job_waits`, `destination_agency_sites` ve beş kiralama şirketi fiyat tablosunu, 30A için 9 şirketi ve kiralama şirketi fiyat kaynağını ekler.

v0.7 lodging discovery sırasında schema 7 oluşturulmadı. Şema 7, GÖREV-03'te (`gorev-03-mahalleler`, v0.7.0) mahalle verisi için eklendi: `neighborhood_records` tablosu ve v6 → v7 migration'ı; konaklamayla ilgisi yoktur. Plaj–mahalle eşlemesi veritabanında değil, `studio/destinations/thirty_a_beach_neighborhoods.csv` dosyasındadır. Ayrıntı: `docs/M7-MAHALLE-VERISI.md`.

## API'nin ana grupları

Genel:
- `/api/health`
- `/api/destinations`
- `/api/bootstrap`
- `/api/sources`
- `/api/jobs`
- `/api/events`
- `/api/source-runs`

Domain:
- `/api/collections` (beach uyumluluk)
- `/api/weather-runs`
- `/api/restaurant-runs`
- `/api/neighborhood-runs` (v0.7.0)
- `/api/beach-neighborhoods` (v0.7.0; profil dosyasındaki plaj–mahalle eşlemesi, salt okunur)
- `/api/climate-runs`, `/api/climate`, `/api/climate-runs/{id}/raw` (v0.8.0; iklim çekimleri, yapılandırma ve son anlık görüntüler, ham manifest)
- `/api/references` (v0.9.0; profil dosyasındaki elle doğrulanmış referans tablosu, doğrulama sonucu ve yeniden kontrol işaretiyle, salt okunur; v0.10.0'da `replaced_by`)
- `/api/lodging-runs`, `/api/lodging-runs/{id}` (mahalle × pencere özeti ve aylık takvim ortancaları, okuma anında), `/api/lodging-runs/{id}/listings?region_id=`, `/api/lodging-runs/{id}/raw` (v0.10.0)
- `/api/agency-rate-runs`, `/api/agency-rate-runs/{id}` (mahalle × pencere fiyat özeti, oda gruplarına göre ortancalar, kapsama ve şirket sonuçları; okuma anında), `/api/agency-rate-runs/{id}/listings?region_id=`, `/api/agency-rate-runs/{id}/raw` (v0.11.0); `/api/jobs` ve olay akışındaki işlerde `waiting_for` (doğrulama bekleyen site)

Liste endpoint'leri destination-filtered'dır.

## Frontend destination davranışı

Seçim:

```text
localStorage["studio.destination_id"]
```

İstekler query ile destination taşır.

Destinasyon değişince:
- eski SSE kapanır,
- filtre/detail state resetlenir,
- request revision artar,
- eski response yeni UI'a yazılmaz.

## Güvenlik kapsamı

Uygulama localhost için tasarlanmıştır.

- TrustedHost sınırı
- write isteklerinde `X-Studio-Request`
- Origin kontrolü
- dış URL fetch allowlist'leri
- path traversal kontrolleri
- raw endpoint root sınırları

Bu bir kullanıcı yetkilendirme sistemi değildir.

## Teknik borç / dikkat noktaları

- `app.py` bootstrap içinde bazı connector metadata hâlâ domain-specific key'ler kullanır.
- UI domain target mapping explicit'tir.
- Product/package adı hâlâ `thirtya-studio`; multi-destination branding henüz yapılmadı.
- Entity eşleme tamamlanmadı.
- Scheduler yok.
- Eski uyumluluk export'ları kalsa bile runtime source of truth DB olmalıdır.
