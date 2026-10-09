# Sürüm Geçmişi ve Güncel Durum

## Stable durum

```text
tag v0.11.0 -> 9f2d65ae85a2adccd1e7f4605406271dbc4d952f
main -> 9f2d65ae85a2adccd1e7f4605406271dbc4d952f
app 0.11.0
schema 11
```

8 Ekim 2026'da GÖREV-09 Adım 1 ile main `9f2d65a`'ya (GÖREV-08) fast-forward edildi ve bu commit'e açıklamalı `v0.11.0` etiketi konuldu ("v0.11.0 — kiralama şirketlerinden konaklama fiyatları"). main CI (37796679492) ve etiket CI (37796684505): success.

8 Ekim 2026'da GÖREV-08 Adım 1 ile main `1f4e80b`'ye (GÖREV-07) fast-forward edildi ve bu commit'e açıklamalı `v0.10.0` etiketi konuldu ("v0.10.0 — bilgi toplama ilkesi, referans tablosu tamamlama ve konaklama profili"). main CI ve etiket CI: success.

7 Ekim 2026'da GÖREV-07 Adım 1 ile main `7110f88`'e (GÖREV-06) fast-forward edildi ve bu commit'e açıklamalı `v0.9.0` etiketi konuldu ("v0.9.0 — kasırga evre kuralı ve referans tablosu"). main CI: success.

7 Ekim 2026'da GÖREV-06 Adım 1 ile main `de6685f`'e (GÖREV-05) fast-forward edildi ve bu commit'e açıklamalı `v0.8.0` etiketi konuldu ("v0.8.0 — eşleme v3 ve iklim paketi"). main CI: success.

7 Ekim 2026'da GÖREV-04 Adım 1 ile main `7f25e3c`'ye fast-forward edildi ve bu commit'e açıklamalı `v0.7.0` etiketi konuldu ("v0.7.0 — mahalle verisi ve plaj–mahalle eşlemesi"). Aynı gün GÖREV-05 Adım 1 ile main `a7e38f2`'ye (GÖREV-04: eşleme v2, test bekleme düzeltmesi, gerçek veri güncelleme kuralı) fast-forward edildi; yeni etiket konmadı; main CI: success. Önceki stable `v0.6.0` → `a938367`.

## Aktif branch

```text
gorev-09-kapsama-restoran
app 0.12.0
schema 12
```

Bu dal:
- tarayıcıyı gerçek Chrome'a çevirir: normal uygulama gibi başlatılır, tek kalıcı profil, CDP bağlantısı, "tarayıcıyla okunur" alan adları (`browser_hosts`), doğrulamada siteyi sona bırakma ve tek 15 dk bekleme, ısınma listesi (Adım 1b; CLAUDE.md, CALISMA_MANTIGI §4),
- konaklama fiyat kapsamasını genişletir (`agency-lodging-rates/2`: 24 şirket, 6 yeni uyarlayıcı, adres/konum eşlemesi, Alys Beach kendi envanteri, yayımlanmış kira, misafir sayısı, korumalı siteler, Sonbahar 2027),
- restoranların kendi sitelerinden bilgi toplar (`restaurant-sites/1`, Restoranlar sekmesinde seviye/rezervasyon/çocuk menüsü sütunları ve mahalle özeti),
- restoran adres ayrıştırmasını düzeltir (`south-walton-restaurants/2`) ve NWS kaynak yöntemini v12'de "API" yapar,
- gerçek veride dört toplayıcı çalıştı (8 Ekim 2026); işletme siteleri 9 Ekim'de menü ayrıştırma düzeltmesinden sonra yeniden çekildi,
- main'e alınmadı; karar yöneticinin.

Test:
- 650 Python
- 54 frontend

---

## v0.1 / ilk temel

İlk bağımsız 30A Studio:
- source library
- CRUD
- archive/restore
- job panel
- dark navy/orange UI
- FastAPI/SQLite yerel uygulama

Erken referans commit:
`629e0d5f9d58569d27c84f40661334c1f1a6ad3`

## v0.2 — Plaj erişimleri

İlk gerçek connector.

Visit South Walton:
- HTML fetch
- embedded marker JSON parse
- 30A kıyı scope
- raw artifact
- versions
- CSV
- UI filter/detail

## v0.3 — Generic data foundation

Final main:
`13ef01c40cd3722e838d25a902a26738f8c3e77a`

Önemli:
- source_runs
- jobs.source_id
- connector protocol/registry
- generic source_collection
- diagnostics
- migration backup/rollback
- entities/regions foundation
- connector-version-aware diff

## v0.4 — NWS weather

Final:
`bbeb07b6206f420e45026b7b3618341f8312e5d3`

Önemli:
- NWS API
- weather anchors
- periods/hourly/alerts
- timezone handling
- weather UI
- schema v4

## v0.5 — Restaurants

Final:
`3c6a6bd0811692011d745547ec15aafea68d8a58`

Tag:
`v0.5.0`

Önemli:
- Visit South Walton dining filter discovery
- 13 neighborhoods
- listing/detail parse
- optional descriptions
- raw response manifest
- restaurant UI
- source identity normalization/reconciliation

Gerçek snapshot'ta:
- 138 restaurants
- 13 represented neighborhoods
- 22 cuisine values observed

Bunlar sabit beklenti değildir.

## v0.6 — Destination layer

Final:
`a938367a280ef799597d5d90dc39ef34a26a6fcb`

Tag:
`v0.6.0`

Önemli:
- destinations
- destination-scoped regions/sources/jobs/runs/entities
- same URL across destinations
- same region name across destinations
- destination weather anchors in DB
- ConnectorContext
- generic NWS
- 30A-specific beach/restaurants
- global destination selector
- localStorage selection
- stale request protection
- schema v6

Automated:
- 289 Python
- 19 frontend

User manual v0.6 smoke:
- destination selector normal
- source library normal
- archived test source preserved
- beach history visible
- weather history visible
- 138 restaurant snapshot preserved
- restaurant detail/filter normal

## v0.7 — Lodging inventory discovery

Dal adı `v0.7-lodging-inventory`; yalnız belge/kanıt. Aşağıdaki v0.7.0 uygulama sürümüyle ilgisi yoktur.

### İlk discovery commit

`318d73644f761b6a89e7d49d5de9a77f71d00381`

Book>Direct public JSON route'ları doğrulandı.

Sorun:
aynı location farklı tarihlerde farklı ID setleri.

### İkinci discovery commit

`23905962126ba9f00f7f8b6223c67c9633e70c2c`

Sonuç:

**C — PUBLIC DATE-INDEPENDENT INVENTORY PATH STILL NOT FOUND**

Doğrulanan:
- date-free list/search/detail → 400
- date params required
- tarihli detail → 200
- bir listede olmayan ID detail'da erişilebilir
- filter nedeni unknown
- sitemap + 11 directory incelendi
- static provider pages var
- full provider inventory yok
- full unit inventory yok

### Book>Direct örnek kanıt

Dune Allen:

| Aralık | Unique ID |
|---|---:|
| 2–3 Ekim 2026 | 112 |
| 2–3 Kasım 2026 | 113 |

Bu sayılar:
- sabit değil,
- tam envanter değil,
- availability count diye de kesin etiketlenmiyor.

### Current decision

Tam inventory requirement korunur.

Yapılmadı:
- schema 7
- lodging_records
- lodging source seed
- lodging UI
- connector

Book>Direct'i price/availability snapshot için ileride değerlendirmek mümkün.

> **7 Ekim 2026 yönetici kararı:** Tarihten bağımsız tam konaklama envanteri şartı kaldırıldı. Konaklama, belirli tarihler için yapılan Book>Direct aramalarının etiketli anlık görüntüleri olarak modellenecek ve hiçbir yerde tam envanter diye adlandırılmayacak (ayrıntı: `CALISMA_MANTIGI.md` §10). Henüz kodlanmadı.

## v0.7.0 — mahalle verisi ve plaj–mahalle eşlemesi

Dal: `gorev-03-mahalleler` (GÖREV-03, 7 Ekim 2026). Uygulama 0.7.0, şema 7. 7 Ekim 2026'da main'e alındı; tag `v0.7.0` → `7f25e3c`.

Önemli:
- `south-walton-neighborhoods/1`: Visit South Walton mahalle dizini (gömülü JSON) + mahalle sayfaları; 30A'ya özel
- 13 canonical mahalle, birebir ad veya açık yazım tablosu; Miramar Beach, Seascape, Sandestin kapsam dışı; eksik hedef mahalle çekimi durdurur
- kaynak kimliği, permalink, kısa tanıtım, temsilî nokta (mahalle merkezi değil), etiketler, kayıt `modified`, sayfa tanıtım metni (nullable)
- `neighborhood_records`, v6 → v7 migration (yedek, tek transaction, foreign_key_check, rollback)
- Veri toplama → Mahalleler sekmesi; kimliğe göre diff
- plaj erişimi–mahalle eşleme dosyası `studio/destinations/thirty_a_beach_neighborhoods.csv`: 9 resmî rehber + 44 program türetimi (boylam farkıyla en yakın temsilî nokta; Alys Beach ve Rosemary Beach'e erişim atanmaz; 2 belirsiz)
- doğrulama: türetme 9 resmî eşlemenin 8'inde aynı (fark: Walton Dunes - 8)
- plaj ekranında mahalle + yöntem etiketi, mahalle filtresi, “eşlenmemiş”

Canlı deneme (geçici klasör): 16 dizin kaydı → 13 mahalle, 3 kapsam dışı; 14 ham yanıt; ikinci çekim farkı 13 aynı. Gerçek DB kopyasında v6 → v7 denemesi başarılı. Ayrıntı: `docs/M7-MAHALLE-VERISI.md`, `docs/gorevler/GOREV-03/RAPOR.md`.

---

## Kullanıcı DB snapshot korunma örneği

v0.6 migration verification sırasında raporlanan:

| Tablo / veri | Count |
|---|---:|
| sources | 8 |
| source_history | 4 |
| jobs | 9 |
| source_runs | 6 |
| beach_records | 159 |
| weather_locations | 6 |
| weather forecast rows | 1020 |
| restaurant_records | 138 |
| restaurant_regions | 141 |

Bu tablo tarihsel doğrulama snapshot'ıdır; production invariant değildir.

v0.7 (şema 7) migration denemesi, 7 Ekim 2026, gerçek DB'nin salt okunur kopyası: yukarıdaki sayılar aynen korundu; `sources` 8 → 9 (yalnız mahalle kaynağı eklendi); yeni `neighborhood_records` boş; `foreign_key_check` boş; 3 plaj, 2 hava ve 1 restoran sürümü API'de görünür kaldı.

Gerçek DB güncellemesi, 7 Ekim 2026 (GÖREV-04): `data/` tam yedeği alındıktan sonra uygulama gerçek klasörle açıldı (v6 → v7, uygulama yedeği alındı) ve plaj, NWS, restoran, mahalle toplayıcıları çalıştı. Sonra: 10 source_runs, 212 beach_records, 9 weather_locations, 1530 forecast rows, 276 restaurant_records, 282 restaurant_regions, 13 neighborhood_records; `integrity_check` ok, `foreign_key_check` boş.

v0.8 (şema 8) migration denemesi, 7 Ekim 2026, gerçek DB'nin `work/` kopyası: eski satırların hepsi aynı; yalnız 8 yeni tablo, 3 iklim istasyonu ve 1 koridor yapılandırması, `sources` 9 → 12; `integrity_check` ok, `foreign_key_check` boş.

Gerçek DB güncellemesi, 7 Ekim 2026 (GÖREV-05): `data/` tam yedeği (`work/yedek/20261007-1533/`) alındıktan sonra uygulama gerçek klasörle açıldı (v7 → v8, uygulama yedeği alındı) ve yalnız üç iklim toplayıcısı çalıştı. Sonra: 12 sources, 16 jobs, 13 source_runs, 2 climate_normal_stations, 168 climate_normal_values, 1 water_temperature_stations, 182 water_temperature_months, 1 storm_corridor_snapshots, 227 storm_passages; eski tablolar aynı; `integrity_check` ok, `foreign_key_check` boş. Şema 8 dosyasını main'deki 0.7.0 açmaz ("daha yeni sürüme ait").

---

## GÖREV-04 — plaj–mahalle eşlemesi v2 (dal)

Dal: `gorev-04-esleme-v2`. Walton County `EnerGov_Additional/FeatureServer/13` "Subdivision Boundaries" katmanıyla nokta-poligon sorgusu; yöntem sırası resmi_rehber → ilce_alt_bolum (yalnız içindeki poligonlar, açık ad tablosu) → turetim_en_yakin_mahalle_noktasi. Sonuç: 9 resmî rehber, 6 ilçe alt bölüm verisi, 38 program türetimi; doğrulama: ilçe yöntemi 9 resmî eşlemenin 1'inde aynı, 8'inde sonuçsuz, farklı yok. Ayrıntı: `docs/M7-MAHALLE-VERISI.md`, `docs/gorevler/GOREV-04/RAPOR.md`.

---

## GÖREV-05 — eşleme v3 ve iklim paketi (dal)

Dal: `gorev-05-iklim`, uygulama 0.8.0, şema 8.

Eşleme v3 (ayrı commit): yöntem sırası resmi_rehber → ilce_alt_bolum → ilce_alt_bolum_yakin (≤ 30 m) → komsu_tutarliligi → turetim_en_yakin_mahalle_noktasi. Sonuç: 9 resmî rehber, 6 ilçe, 16 ilçe (bitişik), 13 komşu, 9 türetim; belirsiz yok; resmî rehberle çelişki 1 (Winston Lane - 4). Yeni yöntemler 9 resmî eşlemenin hiçbirinde farklı sonuç vermedi. v2 → v3: 29 satır, 11'inde mahalle değişti. Ayrıntı: `docs/M7-MAHALLE-VERISI.md`.

İklim paketi:
- `ncei-climate-normals/1`: NCEI veri API'si, `normals-monthly-1991-2020`, yedi değişken, bayraklar ve yıl sayıları; 30A: Destin (kıyı referansı) ve DeFuniak Springs (iç kesim)
- `ndbc-water-temperature/1`: PCBF1 yıllık stdmet dosyaları, WTMP, yıl-ay ortalamaları; çok yıllı ortalamaya ≥ 20 günlü yıl-aylar
- `hurdat2-storm-proximity/1`: güncel HURDAT2 dosyası, 1 saatlik ara değerleme, 30A kıyı koridoruna 50/100 deniz mili, ilk giriş ayı ve sınıf
- tablolar: `destination_climate_stations`, `destination_storm_corridors`, `climate_normal_stations`, `climate_normal_values`, `water_temperature_stations`, `water_temperature_months`, `storm_corridor_snapshots`, `storm_passages`
- üç toplayıcıda kayıt farkı kapalı, gerekçesi API'de

Canlı deneme (geçici klasör) ve gerçek DB (7 Ekim 2026): 168 normal değeri (0 eksik), 182 yıl-ay deniz suyu ortalaması (dosyası bulunan 17 yıl; 2009–2012 404), HURDAT2 `hurdat2-1851-2025-092326.txt` 1.988 sistem, 50 deniz mili içinde 79, 100 içinde 148 geçiş. Ayrıntı: `docs/M8-IKLIM-VERISI.md`, `docs/gorevler/GOREV-05/RAPOR.md`.

---

## v0.8.0 — eşleme v3 ve iklim paketi

7 Ekim 2026'da main'e alındı ve etiketlendi (`v0.8.0` → `de6685f`). İçerik yukarıdaki GÖREV-05 bölümünde.

## GÖREV-06 — kasırga evre kuralı ve referans tablosu (dal)

Dal: `gorev-06-referanslar`, uygulama 0.9.0, şema 9.

- Kasırga sayımı: yalnız HURDAT2 TD, TS, HU, SD, SS evreleri; EX, LO, WV, DB noktaları giriş, en yakın mesafe ve rüzgâr hesabına girmez; yalnız tropikal olmayan evrede daireye giren fırtına işaretlenip saklanır. 1991–2025: 50 deniz milinde 20 → 16, 100 deniz milinde 37 → 33; kasırgalar (HU+MH) değişmedi (5 ve 9). Ayrıntı: `docs/M8-IKLIM-VERISI.md`.
- Referans tablosu: 85 satır (73 doğrulandı, 6 çelişkili, 6 doğrulanamadı); `GET /api/references`, Referanslar sekmesi; aylık TDT dosyası (334 ay). Ayrıntı: `docs/M9-REFERANS-TABLOSU.md`.
- Gerçek DB: `data/` tam yedeği (`work/yedek/20261007-1935/`), v8 → v9 (uygulama yedeği `studio-v8-14fb0efc…`), yalnız kasırga toplayıcısı; sonra 17 jobs, 14 source_runs, 2 storm_corridor_snapshots, 454 storm_passages; `integrity_check` ok, `foreign_key_check` boş.

## v0.9.0 — kasırga evre kuralı ve referans tablosu

7 Ekim 2026'da main'e alındı ve etiketlendi (`v0.9.0` → `7110f88`). İçerik yukarıdaki GÖREV-06 bölümünde.

## GÖREV-07 — konaklama profili ve referans tablosunun tamamlanması (dal)

Dal: `gorev-07-konaklama`, uygulama 0.10.0, şema 10.

- Konaklama: generic Book>Direct toplayıcısı; clone, konum filtresi eşlemesi (30A: 14 filtre, Seagrove Beach → Seagrove) ve 4 tarih penceresi SQLite'ta; ön yüz istemci anahtarı yalnız bellekte; bütün arama sayfaları, sınırlı denemeli canlı fiyat, ilan başına fiyat takvimi (aylık özet); okuma anında mahalle × pencere özeti. 40 test. Geçici deneme ve gerçek çekim (her biri ~73 dk, ~2.655 istek): 4 pencerede 2.389 benzersiz ilan; tür, oda ve kapasite her mahallede var; fiyat çok seyrek (liste fiyatı birkaç ilanda, takvimlerin çoğu gizli, takvimler yalnız Ekim–Mart). İlk deneme Claude Code'un izin denetimince engellenmişti; kullanıcı izin modunu değiştirdikten sonra çalıştı. Ayrıntı: `docs/M10-KONAKLAMA-PROFILI.md`.
- Referans tablosu: 103 satır (89 doğrulandı, 2 çelişkili, 9 doğrulanamadı, 3 yerine geçildi). Ayrıntı: `docs/M9-REFERANS-TABLOSU.md`.
- v9 → v10 migration denemesi gerçek DB kopyasında temiz. Gerçek DB: `data/` tam yedeği (`work/yedek/20261007-2235/`), v9 → v10, yalnız konaklama toplayıcısı; sonra 18 jobs, 15 source_runs, 2.389 lodging_listings, 9.189 lodging_search_results; `integrity_check` ok, `foreign_key_check` boş.
- Bilgi toplama ilkesi (Adım 2) ayrı commit'le yazıldı (ilk deneme izin denetimince engellenmişti).

---

## v0.10.0 — bilgi toplama ilkesi, referans tablosu tamamlama ve konaklama profili

8 Ekim 2026'da main'e alındı ve etiketlendi (`v0.10.0` → `1f4e80b`). İçerik yukarıdaki GÖREV-07 bölümünde.

## GÖREV-08 — kiralama şirketlerinden konaklama fiyatları (dal)

Dal: `gorev-08-konaklama-fiyat`, uygulama 0.11.0, şema 11.

- Keşif: 2.389 Book>Direct ilanının şirket bağlantıları 137 alan adında; ilk 40 alan adı (%94,6) incelendi. Fiyat yolu bulunan dört altyapı (ResCMS, Track, Streamline, vacation-rentals/router) ve bağlantısı ilan sayfasına giden 9 şirket (758 ilan) yapılandırıldı. 360blue ve dört site daha Cloudflare arkasında (360blue keşif denemelerinden sonra kullanıcının IP'sini engelledi; proxy kullanılmadı), Southern Resorts'un fiyat servisi çözülemedi. Ayrıntı: `docs/gorevler/GOREV-08/AJANS-KESFI.md`.
- Toplayıcı: genel çekirdek + 4 uyarlayıcı; yalnız bağlantıyla eşleme; şirket bazında sonuç; görünür tarayıcıyla insan doğrulaması (`job_waits`). Geçici denemede üç hata bulundu ve düzeltildi (sıradan CAPTCHA kutusunun doğrulama sanılması, Track'te müsaitliğin fiyat servisinden değil sayfa takviminden okunması gereği, ResCMS'te isteğe bağlı sigortanın ara toplama göre ayrılması) ve 200 kodlu "not found" sayfaları ayrıldı. Gerçek çekim: 3.855 istek, 92,5 dk; 510 ilana fiyat (12/13 mahalle). Ayrıntı: `docs/M11-KONAKLAMA-FIYATLARI.md`.
- Referans tablosu: 105 satır (100 doğrulandı, 2 çelişkili, 0 doğrulanamadı, 3 yerine geçildi).
- v10 → v11 migration denemesi gerçek DB kopyasında temiz. Gerçek DB: `data/` tam yedeği (`work/yedek/20261008-1517/`), v10 → v11, konaklama sonra kiralama şirketi fiyat toplayıcısı; `integrity_check` ok, `foreign_key_check` boş.

## v0.11.0 — kiralama şirketlerinden konaklama fiyatları

8 Ekim 2026'da main'e alındı ve etiketlendi (`v0.11.0` → `9f2d65a`). İçerik yukarıdaki GÖREV-08 bölümünde.

## GÖREV-09 — tarayıcı kurulumu, konaklama fiyat kapsaması ve restoran bilgileri (dal)

Dal: `gorev-09-kapsama-restoran`, uygulama 0.12.0, şema 12.

- Tarayıcı (Adım 1b, kullanıcı kararı): Playwright'in test tarayıcısı bırakıldı; gerçek Chrome normal uygulama gibi açılıp CDP ile bağlanılıyor. Isınmada 24 siteden yalnız order.online doğrulama istedi; 360blue hâlâ engel sayfası gösteriyor; floridastateparks.org bu tarayıcıda açıldı (GÖREV-08'de 403).
- Keşif ve toplayıcı: 15 yeni şirket (`AJANS-KESFI-2.md`, `ajanslar.csv`); adres/konum eşlemesi doğrulandı (`eslesme-dogrulama.csv`); misafir sayısı kontrolünde hiçbir şirkette toplam değişmedi (bütün şirketler 2 yetişkin).
- Restoranlar: işletme sitelerinden menü, fiyat seviyesi, saat, rezervasyon, çocuk menüsü; görüntü menüleri elle okundu.
- v11 → v12 migration denemesi gerçek DB kopyasında temiz. Gerçek DB: `data/` tam yedeği (`work/yedek/20261008-2310/`), v11 → v12, sırayla dört toplayıcı; 9 Ekim 2026'da besin değeri tablosu düzeltmesinden sonra ikinci tam yedek (`work/yedek/20261009-0419/`) alınıp işletme siteleri toplayıcısı yeniden çalıştırıldı; `integrity_check` ok, `foreign_key_check` boş. Sayılar `docs/gorevler/GOREV-09/RAPOR.md`.

---

## Konaklama: açık konu

3 Ekim'deki blocker, tam/tarihten bağımsız lodging inventory idi. 7 Ekim 2026 yönetici kararıyla bu şart kaldırıldı: konaklama tarihli arama anlık görüntüleri olarak modellenecek. Tam envanter iddiası taşıyan bir “lodging inventory connector” yine yapılmamalıdır.

---

## Yeni geliştiricinin bu dosyadan çıkarması gereken sonuç

Stable ürün:
**v0.11.0 — kiralama şirketlerinden konaklama fiyatları**

Çalışan veri domain'leri:
**beach + weather + restaurants + neighborhoods + iklim + elle doğrulanmış referans tablosu + konaklama profili + kiralama şirketlerinden konaklama fiyatları** ve plaj–mahalle eşlemesi v3; `gorev-09-kapsama-restoran` dalında ayrıca **genişletilmiş fiyat kapsaması** ve **restoranların kendi sitelerinden bilgiler**

Görev dalında, gerçek veride çalışmış:
**konaklama fiyatları** (24 şirket; örnek şirketlere göre hâlâ dengesiz, 360blue yok) ve **restoran bilgileri** (`gorev-09-kapsama-restoran`)

Yanlış sonraki adım:
**Book>Direct date search'i full inventory diye kodlamak**; program türetimi mahalle eşlemelerini resmî bilgi gibi sunmak

Doğru yaklaşım:
`gorev-09-kapsama-restoran` yönetici incelemesinden sonra main'e alınır; sıradaki aşama kanıt paketi ve makaledir (yönetici kararı).
