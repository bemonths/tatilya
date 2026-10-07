# Sürüm Geçmişi ve Güncel Durum

## Stable durum

```text
tag v0.6.0 -> a938367a280ef799597d5d90dc39ef34a26a6fcb
app 0.6.0
schema 6
main -> 62d6b7b431669ca44a705b1c85f24f9df72bd6ca
```

`v0.6.0` tag'i doğrudan a938367'ye işaret eder. main, 7 Ekim 2026'da GÖREV-03 Adım 1 ile `62d6b7b`'ye fast-forward edildi: v0.6.0 koduna ek olarak konaklama keşif belgeleri (`v0.7-lodging-inventory`) ve GÖREV-01/02 belgeleri. Kod ve şema main'de hâlâ 0.6.0 / 6. main CI: success.

## Aktif branch

```text
gorev-03-mahalleler
v0.7.0 — mahalle verisi ve plaj–mahalle eşlemesi
app 0.7.0
schema 7
```

Bu dal:
- mahalle toplayıcısını (`south-walton-neighborhoods`) ve şema 7'yi ekler,
- plaj erişimi–mahalle eşleme katmanını ekler,
- main'e alınmadı, tag yok; karar yöneticinin.

Test:
- 390 Python
- 29 frontend

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

Dal: `gorev-03-mahalleler` (GÖREV-03, 7 Ekim 2026). Uygulama 0.7.0, şema 7. main'e alınmadı; tag yok.

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

---

## Konaklama: açık konu

3 Ekim'deki blocker, tam/tarihten bağımsız lodging inventory idi. 7 Ekim 2026 yönetici kararıyla bu şart kaldırıldı: konaklama tarihli arama anlık görüntüleri olarak modellenecek. Tam envanter iddiası taşıyan bir “lodging inventory connector” yine yapılmamalıdır.

---

## Yeni geliştiricinin bu dosyadan çıkarması gereken sonuç

Stable ürün:
**v0.6.0**

Çalışan veri domain'leri:
**beach + weather + restaurants**; görev dalında ayrıca **neighborhoods + plaj–mahalle eşlemesi** (v0.7.0)

Kodlanmamış:
**lodging** (tarihli arama anlık görüntüleri olarak planlandı)

Yanlış sonraki adım:
**Book>Direct date search'i full inventory diye kodlamak**; program türetimi mahalle eşlemelerini resmî bilgi gibi sunmak

Doğru yaklaşım:
v0.7.0 yönetici incelemesinden ve main'e alma kararından sonra stable olur; sıradaki domain'i yönetici seçer.
