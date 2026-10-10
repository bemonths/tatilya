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

Başlatma (GÖREV-14):

```text
masaüstündeki "30A Studio" kısayolu  ->  .venv\Scripts\pythonw.exe -X utf8 -m studio
baslat.bat                           ->  ilk seferde kurar, sonra aynı komutu başlatır
python -m studio --data-dir … --no-browser --port …   (geliştirme ve deneme; pencere ve bekçi yok)
```

Server: 127.0.0.1, 8830–8849 aralığındaki ilk boş port (geliştirme komutunda varsayılan 8830). Başlatıcı `studio/launcher.py`
(başlatma kilidi `<veri>/baslatiliyor.kilit`, çalışma kilidi `<veri>/calisiyor.json`, `/api/health` ile tek kopya, uygulama kipi
pencere), kapanma bekçisi `studio/watchdog.py` (`POST /api/heartbeat`, olay akışı; çalışan iş varken bekler), günlük
`<veri>/gunluk/uygulama.log`, kurulum damgası `.venv/studio-kurulum.txt`.

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

### Restoran bilgileri (v0.12.0, şema 12; `gorev-09-kapsama-restoran` dalı)

İşletmelerin kendi sitelerinden: `restaurant_site_snapshots` (girdi restoran dizini çekimi, sayılar), `restaurant_sites` (restoran başına site durumu, kaynağı — dizin ya da gözden geçirilmiş site dosyası —, son url, HTTP durumu, not), `restaurant_facts` (saatler, rezervasyon, çocuk menüsü, açık hava, su kenarı/manzara, köpek dostu, sitenin fiyat işareti; her biri kaynak url, erişim zamanı, SHA-256 ve yöntemle), `restaurant_menus` (url, biçim, tür, durum), `restaurant_menu_items` (bölüm, ad, fiyat metni, fiyat, fiyat kuralı `single`/`lowest`/`market`, bölüm sınıfı ve dayanağı). Ana yemek ortancası ve fiyat seviyesi saklanmaz, okuma anında hesaplanır. Genel çekirdek `studio/sources/restaurant_sites.py`, bölüm sınıflama tablosu `studio/sources/menu_sections.csv`; 30A'nın gözden geçirilmiş site ve görüntü menü okuma dosyaları `studio/destinations/thirty_a_restaurant_sites.csv`, `thirty_a_menu_readings.csv`. Ayrıntı: `docs/M12-RESTORAN-BILGILERI.md`.

Şema 13 (GÖREV-10, `gorev-10-aylik-gunluk` dalı): `restaurant_facts.field` + `review_note` (gözden geçirilmiş site dosyasındaki "ana yemek sunmuyor" ya da seviye notu; erişim zamanı ve SHA yalnız bu alanda boş olabilir); menü türü + `catering`, `special`; bölüm sınıfı + `kucuk_tabak`, `sabit_menu`; sınıf dayanağı + `review` (`thirty_a_menu_item_classes.csv`); yöntem + "elle okundu", "gözden geçirme". Üç tablo yeniden kuruldu (satırlar korunur). Ayrıntı: `docs/M12-RESTORAN-BILGILERI.md`.

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

### Aylık pencere kuralı (şema 13; `gorev-10-aylik-gunluk` dalı)

`destination_lodging_sources.window_rule` (JSON; `kind=monthly, months, anchor_day, weekday, nights, min_lead_days`): çekim ayından sonraki 12 ayın her biri için ayın 15'ini içeren Cumartesi–Cumartesi haftası; 21 günden yakın pencere atlanır, 13. ay eklenir. Kural tanımlıyken `destination_lodging_windows` kapalıdır (`enabled=0`). Hesap generic `studio/sources/windows.py`; Book>Direct ve kiralama şirketi toplayıcıları aynı kuralı kullanır ve çekim kaydına (`metadata.window_rule`) yazar. Sorgudan pencereye gün, mevsim grupları ve aynı hafta karşılaştırması (`studio/sources/price_history.py`) okuma anında hesaplanır, saklanmaz. Ayrıntı: `docs/M11-KONAKLAMA-FIYATLARI.md`.

### Güncelleme zamanı ve toplu çalıştırma (şema 13)

- `destination_refresh_intervals`: destinasyon × toplayıcı adı → önerilen aralık (ay) ve sıra (30A: Book>Direct ve kiralama şirketi fiyatları 1, restoran dizini ve işletme siteleri 3).
- `refresh_batches`: "Zamanı gelenleri başlat" ile başlayan toplu çalıştırmalar (durum `running` / `done` / `failed` / `canceled` / `interrupted`, uygulamanın yedek dosyası, plan JSON'u: adım başına toplayıcı, iş kimliği, durum, mesaj; tahmini süre).
- `studio/refresh.py`: zamanı gelme hesabı (hiç çekilmedi; son başarılı çekim + aralık; pencere toplayıcısında son çekimin kuralı güncel kuraldan farklı), tahmin (son başarılı çekimin süresi; pencere sayısı değiştiyse oranla), yedek (`data/backups/toplu-*.sqlite3`, son 6), `BatchRunner` (tek seferde bir toplu çalıştırma; sıra yapılandırmadaki sıra; toplayıcı `inputs`/`produces` bağımlılığıyla girdisi tamamlanmayan adımı atlar; iptal; uygulama açılırken yarıda kalan toplu çalıştırma `interrupted`). Zamanlanmış görev yoktur.

### Günlük ihtiyaç (şema 13)

Yapılandırma: `destination_poi_areas` (bölge kutusu), `destination_poi_categories` (OpenStreetMap etiket setleri). Çekim: `poi_snapshots` (sorgu tarihi, OpenStreetMap zaman damgası, istek ve öğe sayısı), `poi_points` (kategori, ad, marka, koordinat, kaynak `openstreetmap` / `zincirin kendi sitesi`, OpenStreetMap kimliği, etiketler, adres, bağlantı, not), `poi_chain_checks` (zincir mağaza kontrolü ve sonucu). İlanlardan kuş uçuşu uzaklıklar ve mahalle ortancaları okuma anında. Ayrıntı: `docs/M13-GUNLUK-IHTIYAC.md`.

### Claude adımları ve video kaydı (şema 15; `gorev-13-claude-baslik` dalı)

`claude_runs` (kimlik, destinasyon, adım, hazırlık ya da video kimliği, iş, düzeltilen çalışma, durum: running / awaiting_approval / approved / rejected / error, seçim JSON, klasör, model, efor, Claude Code sürümü, oturum, ölçüm JSON, sorunlar JSON, hata, karar notu; aynı anda tek `running` satırı). `videos` (kimlik, destinasyon, bölge, İngilizce ve Türkçe başlık, aile, seçilen adayın analizi JSON, şablon ve parametreler, durum: baslik_secildi / paket_hazir, çalışma ve aday sırası). `evidence_packs.video_id`. Çekirdek `studio/ai/` (çalıştırıcı, ayarlar, adım çerçevesi, konu ve başlık adımı, servis); talimatlar destinasyonda (`studio/destinations/thirty_a_claude/`); çalışma klasörleri `<veri>/claude/`; ayarlar `<veri>/ayarlar.json`. Ayrıntı: `docs/M15-CLAUDE-ADIMLARI.md`.

### Claude kullanımı, iş ilerlemesi ve eklenti yöntemi (şema 16; `gorev-14-masaustu-eklenti` dalı)

`claude_usage` (ölçüm zamanı, kaynak: `calisma` / `yenile`, çalışma kimliği, 5 saatlik ve haftalık oran ve sıfırlanma zamanı, durum,
ham bilgi JSON). `job_progress` (iş başına `progress_info` JSON: Claude çalışmasının aşaması ve başlangıçları, beklenen süre ve dayanağı;
eklenti bekleyen işte `{"tur": "eklenti", "bekliyor": true}`); `jobs` satırları değişmez, `/api/jobs` ikisini birleştirir.
`browser_hosts.method` (alan adı için en son işe yarayan yöntem: `eklenti`, `tarayici`, `dogrudan`). Talimat sürümleri veritabanında değil,
`<veri>/claude/talimat_gecmisi/<dosya>/<zaman>.md`; başlık ekleri `<veri>/ayarlar.json` → `baslik_ekleri`; eklenti eşleşmesi
`<veri>/eklenti.json`. Video kaydında (`videos`) önerilen başlık ve "kullanıcı düzenledi" işareti. Ayrıntı: `docs/M15-CLAUDE-ADIMLARI.md`,
`docs/M16-TARAYICI-EKLENTISI.md`.

### Günlük ihtiyaç ve kanıt paketi (şema 14; `gorev-11-kanit-paketi` dalı)

`destination_poi_categories` + `brands` (JSON marka listesi; büyük süpermarket), `verified_only` (acil servis, acil bakım: yalnız resmî kaynakla doğrulanan nokta sayılır). `poi_points.source` + `kurumun kendi sitesi`. `poi_chain_checks` + `category_key` (birincil anahtar `run_id, category_key, chain, store`), sonuç + `osm_dogrulanamadi`. `evidence_packs` (kimlik, destinasyon, şablon anahtarı ve sürümü, başlık, parametreler JSON, üretim zamanı, Markdown ve JSON dosya yolu ve SHA-256'sı, bölüm/satır/sayı/"veri yok" sayısı). Kanıt paketi çekirdeği `studio/evidence/` (generic); şablonlar `studio/destinations/thirty_a_evidence/*.json`. GÖREV-12 (`gorev-12-yazar-ozeti`, şema değişmedi): `summary.py` yazar özetini aynı paket nesnesinden yazar; her üretim dört dosya (Markdown, JSON, `-yazar-ozeti.md`, `-sayilar.csv`); eklerin adı ve SHA-256'sı JSON'un `dosyalar` alanında (JSON'un SHA-256'sı `evidence_packs`'te); satırlarda `ek_degerler` (`tur`: alt_ceyrek, ust_ceyrek, orneklem, pay, aralik_alt, aralik_ust, donusum), `tablo`, `kucuk_ornek`, `celiski_notu`; sayı listesi yalnız bu alanlardan; şablonda `oynak_konular`. Ayrıntı: `docs/M13-GUNLUK-IHTIYAC.md`, `docs/M14-KANIT-PAKETI.md`.

### Konaklama fiyatları (v0.11.0, şema 11; `gorev-08-konaklama-fiyat` dalı)

Yapılandırma: `destination_agency_sites` (alan adı, şirket adı, uyarlayıcı, etkin). Çekim: `agency_rate_snapshots` (girdi konaklama çekimi, sorgu günü), `agency_rate_windows`, `agency_rate_companies` (şirket bazında sonuç), `agency_rate_listings` (Book>Direct ilanı, bağlantı, sayfa durumu, platform kimliği), `agency_rate_quotes` (ilan × pencere: müsaitlik, kira, ücretler, vergiler, toplam, isteğe bağlı kalemler, kurallar, ham yanıt SHA-256'ları). `job_waits`: çalışan bir işin kullanıcı doğrulaması beklediği site. Genel çekirdek `studio/sources/agency_rates.py`, uyarlayıcılar `agency_adapters.py`, görünür tarayıcı `browser_verification.py` (isteğe bağlı Playwright). Ayrıntı: `docs/M11-KONAKLAMA-FIYATLARI.md`.

Şema 12 (`agency-lodging-rates/2`, `gorev-09-kapsama-restoran` dalı): `destination_agency_sites`'a takma alan adları (`aliases`), korumalı bayrağı (`protected`), misafir kuralı (`guest_rule`: `two_adults` / `bedrooms_x2`), şirket ilan listesi kaynağı (`inventory`: platform liste servisi ya da site haritası) ve kendi envanteri mahallesi (`own_region_id`, `own_city`); `agency_rate_listings`'e eşleme yöntemi (`match_method`: `link` / `address` / `location`), bağlantı durumu ve eşleme notu; `agency_rate_quotes`'a misafir sayısı (`adults`, `children`); `agency_rate_companies`'e korumalı, misafir kuralı, şirket listesi sayısı ve ham SHA-256'ları, kendi envanteri sayıları ve yöntem dağılımı. Yeni tablolar: `agency_rate_own_listings` ve `agency_rate_own_quotes` (şirketin kendi envanteri), `agency_rate_published` (yayımlanmış sezon kirası; toplam fiyatlardan ayrı). Adres/konum kuralları `studio/sources/agency_matching.py`'de.

## Migration stratejisi

Şema yükseltmeden önce:
- SQLite backup API ile yedek,
- transaction,
- gerekiyorsa table rebuild,
- `PRAGMA foreign_key_check`,
- hata halinde rollback.

Stable şema: `10` (v0.10.0 ve main): v7 → v8 iklim tablolarını, 30A iklim yapılandırmasını ve üç iklim kaynağını ekler; v8 → v9 `storm_passages.non_tropical_only` sütununu ekler (kasırga evre kuralı); v9 → v10 konaklama yapılandırma tablolarını (`destination_lodging_sources`, `_locations`, `_windows`), sekiz konaklama anlık görüntü tablosunu ve 30A Book>Direct kaynağını ekler. `gorev-08-konaklama-fiyat` dalında şema `11` (gerçek DB 8 Ekim 2026'da şema 11'e yükseltildi): v10 → v11 `lodging_listings`'e `url`, `phone`, `toll_free` sütunlarını, `job_waits`, `destination_agency_sites` ve beş kiralama şirketi fiyat tablosunu, 30A için 9 şirketi ve kiralama şirketi fiyat kaynağını ekler. `gorev-09-kapsama-restoran` dalında şema `12` (`studio/migration_v12.py`): v11 → v12 kiralama şirketi tablolarına yukarıdaki sütunları ve üç tabloyu, beş restoran bilgisi tablosunu ekler; eski çekimlerde eşleme yöntemi `link`, misafir sayısı 2 yetişkin (Track hariç; servis sormuyor) olarak doldurulur; 30A için 15 yeni şirket, şirket seçenekleri, Sonbahar 2027 penceresi ve "Restoranlar · İşletme siteleri" kaynağı eklenir; NWS kaynağının yöntemi hâlâ "Belirlenecek" ise "API" yapılır.

GÖREV-10 (`gorev-10-aylik-gunluk`, şema `13`, `studio/migration_v13.py`): v12 → v13 `destination_lodging_sources.window_rule` sütununu, yenileme aralığı ve toplu çalıştırma tablolarını, günlük ihtiyaç tablolarını ekler; `restaurant_facts`, `restaurant_menus` ve `restaurant_menu_items`'ı yeni değerlerle yeniden kurar; 30A için pencere kuralını, aralıkları, bölge kutusunu, kategorileri ve OpenStreetMap kaynağını tohumlar. Gerçek DB kopyasında satır sayıları korunarak denendi.

GÖREV-11 (`gorev-11-kanit-paketi`, şema `14`, `studio/migration_v14.py`): v13 → v14 kategori yapılandırmasına `brands` ve `verified_only` sütunlarını ekler, `poi_points` ve `poi_chain_checks`'i genişleyen CHECK listeleri ve kategori anahtarıyla yeniden kurar (eski satırlar korunur, eski kontrol satırlarına `supermarket` yazılır), `evidence_packs` tablosunu ekler ve destinasyonun günlük ihtiyaç kategorilerini profildeki yeni listeyle değiştirir. Gerçek DB kopyasında denendi: yalnız `destination_poi_categories` 5 → 7 ve yeni boş `evidence_packs`; `integrity_check` ok, `foreign_key_check` boş.

GÖREV-13 (`gorev-13-claude-baslik`, şema `15`): v14 → v15 `claude_runs`, `videos` ve `evidence_packs.video_id`'yi ekler. GÖREV-14 (`gorev-14-masaustu-eklenti`, şema `16`, `studio/migration_v16.py`): v15 → v16 `claude_usage` ve `job_progress` tablolarını, `browser_hosts.method` sütununu ve video kaydına önerilen başlık ve "kullanıcı düzenledi" alanlarını ekler; eski satırlar değişmez. Gerçek DB kopyasında denendi: 165.250 satır önce ve sonra aynı; `integrity_check` ok, `foreign_key_check` boş.

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
- `/api/agency-rate-runs`, `/api/agency-rate-runs/{id}` (mahalle × pencere fiyat özeti, oda gruplarına göre ortancalar, kapsama ve şirket sonuçları; okuma anında), `/api/agency-rate-runs/{id}/listings?region_id=`, `/api/agency-rate-runs/{id}/raw` (v0.11.0; v0.12.0'da mahalle ilan listesi `{listings, own}` biçiminde, kendi envanteri ayrı); `/api/jobs` ve olay akışındaki işlerde `waiting_for` (doğrulama bekleyen site)
- `/api/restaurant-site-runs`, `/api/restaurant-site-runs/{id}` (restoran listesi, mahalle özeti, kapsama; okuma anında), `/api/restaurant-site-runs/{id}/restaurant?external_id=` (bir restoranın bütün alanları, menüleri ve kalemleri), `/api/restaurant-site-runs/{id}/raw` (v0.12.0)
- `/api/refresh` (toplayıcıların son başarılı çekimi, önerilen aralık, zamanı gelip gelmediği ve nedeni, tahmin, son toplu çalıştırma), `POST /api/refresh-batches` (zamanı gelenleri başlatır; zamanı gelen yoksa, başka bir toplu çalıştırma ya da iş sürüyorsa 409), `POST /api/refresh-batches/{id}/cancel` (v0.13.0)
- `/api/daily-needs-runs`, `/api/daily-needs-runs/{id}` (noktalar, zincir kontrolü, mahalle başına kuş uçuşu uzaklık ortancaları; okuma anında), `/api/daily-needs-runs/{id}/raw` (v0.13.0)
- `/api/evidence-templates` (şablonlar, bölüm soruları, parametre seçenekleri), `POST /api/evidence-packs` (`template_key`, `params`; üretir, `data/evidence/` altına Markdown + JSON yazar ve SHA-256'larıyla kaydeder), `/api/evidence-packs` (her pakette `ekler`), `/api/evidence-packs/{id}/markdown|json|yazar-ozeti|sayilar` (dosyanın SHA-256'sı kayıtla, eklerinki kayıtla doğrulanmış JSON'la karşılaştırılarak) (v0.14.0; yazar özeti ve sayı listesi GÖREV-12)
- `/api/settings/claude` (GET, PUT: Claude Code'un yolu ve sürümü, API anahtarı uyarısı, model, efor, tur sınırı), `/api/claude/options`, `/api/claude/runs`, `POST /api/claude/title-runs` (bölge, aile, not), `/api/claude/runs/{id}` (onay görünümü), `POST /api/claude/runs/{id}/select|reject|correct`, `/api/claude/runs/{id}/files/{ad}`, `/api/videos`, `POST /api/videos/{id}/evidence-pack` (v0.15.0, GÖREV-13)
- `/api/workflow?video_id=` (iş akışının 8 adımı ve durumları), `POST /api/heartbeat` (kapanma bekçisi), `/api/claude/usage`, `POST /api/claude/usage/refresh`, `/api/claude/instructions`, `/api/claude/instructions/{key}` (GET, PUT `base_sha256` ile; değiştiyse 409), `/api/claude/instructions/{key}/versions/{sürüm}` ve `…/restore`, `/api/settings/title-suffix` (GET, PUT), `POST /api/claude/review-runs` (bölge, başlık, not), `POST /api/claude/runs/{id}/translate` (aday, düzenlenmiş Türkçe başlık), `select` gövdesinde düzenlenmiş `baslik_en` / `baslik_tr`; `POST /api/videos/{id}/evidence-pack` artık içerik planından paket kurar (v0.16.0, GÖREV-14)
- Eklenti (yalnız eşleşmiş eklentinin kökeni ve `X-Studio-Eklenti` kodu): `POST /api/eklenti/eslestir`, `/api/eklenti/sor`, `/api/eklenti/is/{oturum}/sonraki|sonuc|durum|bitti`; programın ekranı için `/api/tarayici-eklentisi` (GET), `…/kod-yenile`, `…/ayarlar` (PUT), `…/deneme`, `…/sorunlu-siteler`, `…/devret/{iş}`, `/eklenti-deneme` (yerel deneme sayfası), `/eklenti-kurulum/{resim}` (v0.16.0, GÖREV-14)

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
- Origin kontrolü; GÖREV-14'ten beri durum değiştiren istekte `Sec-Fetch-Site` `cross-site` / `same-site` ise ya da `Origin` farklıysa ret (kullanıcının tarayıcısı programla konuştuğu için)
- eklenti API'si yalnız eşleşmiş eklentinin kökenine ve eşleşme koduna açık; CORS yalnız o köken için
- dış URL fetch allowlist'leri
- path traversal kontrolleri
- raw endpoint root sınırları

Bu bir kullanıcı yetkilendirme sistemi değildir.

## Teknik borç / dikkat noktaları

- `app.py` bootstrap içinde bazı connector metadata hâlâ domain-specific key'ler kullanır.
- UI domain target mapping explicit'tir.
- Product/package adı hâlâ `thirtya-studio`; multi-destination branding henüz yapılmadı.
- Entity eşleme tamamlanmadı.
- Scheduler yok (kullanıcı kararı; bilgisayarda zamanlanmış görev de oluşturulmaz).
- Eski uyumluluk export'ları kalsa bile runtime source of truth DB olmalıdır.
