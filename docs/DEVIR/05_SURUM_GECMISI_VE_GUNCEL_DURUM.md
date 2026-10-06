# Sürüm Geçmişi ve Güncel Durum

## Stable durum

```text
main
a938367a280ef799597d5d90dc39ef34a26a6fcb
v0.6.0
schema 6
```

`v0.6.0` tag'i doğrudan bu commit'e işaret eder.

## Aktif branch

```text
v0.7-lodging-inventory
23905962126ba9f00f7f8b6223c67c9633e70c2c
```

Bu branch:
- main'in üzerine yalnız lodging discovery doküman/kanıt çalışması ekler,
- app version hâlâ 0.6.0,
- schema hâlâ 6,
- production DB'ye lodging veri eklemedi,
- main'e merge edilmedi.

Son Actions: success.

Test:
- 289 Python
- 19 frontend

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

---

## Şu anda açık kritik research blocker

**Tam/tarihten bağımsız lodging inventory.**

İhtiyaç:
- supported public inventory/export/read path,
- stable IDs,
- deterministic enumeration,
- complete pagination,
- clear provider/unit semantics,
- 30A scope mapping.

Bunlar bulunmadan “lodging inventory connector” yapılmamalıdır.

---

## Yeni geliştiricinin bu dosyadan çıkarması gereken sonuç

Stable ürün:
**v0.6.0**

Çalışan veri domain'leri:
**beach + weather + restaurants**

Aktif fakat kodlanmamış research:
**lodging inventory**

Yanlış sonraki adım:
**Book>Direct date search'i full inventory diye kodlamak**

Doğru yaklaşım:
ya tam inventory kaynağı bulmak, ya lodging'i bekletip başka veri domain'ine geçmek.
