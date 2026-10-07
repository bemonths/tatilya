# Veri Kaynakları ve Doğrulama Sistemi

## Amaç

Bu belge yalnız “hangi URL'lerden veri çekiyoruz?” sorusunu değil, **bir kaynağın kullanılmaya değer olduğuna nasıl karar verdiğimizi** açıklar.

Temel ayrım:

> Kaynak teknik olarak erişilebilir olabilir ama semantik olarak bizim sorumuza cevap vermiyor olabilir.

Konaklama keşfi bunun en önemli örneğidir.

## Kaynak kabul süreci

### 1. Kaynağın sahibi / otoritesi

Sor:
- Resmî kurum mu?
- Destinasyonun resmî turizm kuruluşu mu?
- İşletmenin kendi sitesi mi?
- Aggregator mı?
- Analiz şirketi mi?

Kaynak yalnız otorite olduğu alan için kullanılır.

### 2. Veri semantiği

Sor:
- Bu liste “tüm kayıtlar” mı?
- Arama sonucu mu?
- Müsaitlik filtresi mi?
- Tarih snapshot'ı mı?
- Featured/sponsored subset mi?
- Filtre UI'si gerçekte hangi alanı temsil ediyor?

### 3. Kapsam

Sor:
- Pagination tam mı?
- Son sayfa nasıl anlaşılır?
- Başka hidden subset var mı?
- Region filtreleri güvenilir mi?
- Aynı kayıt birden fazla bölgede çıkabilir mi?

### 4. Kimlik

Öncelik:
1. explicit ID
2. stable canonical path
3. source-specific stable key

İsim, adres veya title hash'i identity olarak kullanılmamalıdır.

### 5. Teknik yol

Öncelik:
1. public/resmî API
2. JSON/embedded state
3. HTML
4. public frontend XHR/fetch endpoint
5. browser automation

### 6. Kanıt

Keşif:
- request/response,
- pagination,
- örnek ID,
- alan sözleşmesi,
- edge case,
- tarih bağımlılığı

ile belgelenir.

### 7. Test

- fixture / MockTransport
- parser tests
- malformed response
- retry
- timeout
- redirect
- 429
- cancellation
- duplicate identity
- atomic rollback

### 8. Canlı smoke

Testler geçtikten sonra gerçek kaynak üzerinde küçük veya full smoke.

Canlı snapshot sayısı sabit assertion'a çevrilmez.

---

# Çalışan kaynaklar

## Visit South Walton — Plaj erişimleri

URL:
`https://www.visitsouthwalton.com/beach-bay-access-locations/`

Rol:
Resmî bölgesel plaj erişim kaynağı.

Teknik yöntem:
HTML içindeki structured marker JSON.

Connector:
`south-walton-beaches`

Scope:
30A-specific.

Önemli sınırlar:
- Kaynaktaki city text canonical mahalle değildir.
- Miramar / bay/lake kayıtları 30A kıyı scope dışında bırakılır.
- Olanak listelenmiyorsa “yok” kabul edilmez.
- Canlı kayıt sayısı değişebilir.

## Visit South Walton — Restoranlar

URL:
`https://www.visitsouthwalton.com/listings/culinary-experiences/`

Rol:
Resmî turizm dizinindeki dining kayıtları.

Teknik yöntem:
HTML filter form + listing pagination + detail pages.

Connector:
`south-walton-restaurants`

Scope:
30A-specific.

Kapsam:
13 canonical 30A region.

Hariç:
- Miramar Beach
- Seascape
- Sandestin

Semantik:
“Restaurants” business type filtresi kullanılır.

Alanlar:
- name
- listing URL
- description nullable
- address
- contact
- website
- cuisines
- meals
- amenities
- neighborhood provenance

Own website veri alanı olarak saklanır. İşletmenin sitesi, dizindeki bağlantıyla kimliği belli olduğu için doğrudan okunabilir; okunan her sayfanın adresi, erişim tarihi ve ham kopyası saklanır. Bugünkü restoran toplayıcısı bunu henüz yapmıyor. (7 Ekim 2026, GÖREV-07: önceki "connector işletmenin sitesini crawl etmez" kuralı kaldırıldı.)

## National Weather Service

Source record URL:
`https://www.weather.gov/`

API:
`https://api.weather.gov`

Rol:
Resmî forecast ve alert kaynağı.

Connector:
`nws-weather`

Scope:
Generic.

Akış:
`/points/{lat},{lon}` → forecast / hourly → alerts.

30A koordinatları DB'deki destination weather anchors'tan gelir.

Sınırlar:
- Forecast “current conditions” değildir.
- Anchor'lar canonical mahalle merkezi değildir.
- Rolling window olduğu için record diff anlamlı değildir.

---

# Konaklama keşfi — Book>Direct

## Public giriş

`https://visitsouthwalton.bookdirect.net/`

Frontend üzerinden public clone API:
`admin.bookdirect.net`

Doğrulanmış route sınıfları:
- clone config
- lodgings list/search
- lodging detail
- rates/live-rates ile ilişkili yollar

Public token/script değeri repoya hard-code edilmemelidir.

## Ana sorun

Book>Direct lodging list/search/detail çağrıları tarih istiyor.

Tarihsiz:
- list → 400
- search → 400
- bilinen-ID detail → 400

Tarihli:
- 200

Aynı Dune Allen filtresi:
- 2–3 Ekim 2026 → 112 ID
- 2–3 Kasım 2026 → 113 ID

Listede görünmeyen bir ID tarihli detail çağrısında erişilebilir kalabiliyor.

Kesin filtre nedeni:
**unknown**

Muhtemel açıklamalar kanıtlanmadan kullanılmamalı:
- availability
- minimum stay
- aktif/pasif
- başka backend scope

## Visit South Walton provider tarafı

Resmî eski yönergelerde Parent Listing / Child Listing kavramları görülür.

Güncel Walton County Tourism açıklaması accommodation listing yönetiminin Book>Direct'e geçtiğini belirtir.

Ancak:
- tam parent/provider index,
- tam child/unit index,
- public tarihsiz enumeration

doğrulanmamıştır.

## Sitemap araştırması

Visit South Walton sitemap:
- 948 URL
- 575 `/listing/`
- 11 `/listings/` dizini

Konaklama provider/otel örnekleri bulunmuştur.

Ama sitemap:
- typed lodging inventory değildir,
- tüm provider'ları kapsadığı kanıtlanmamıştır,
- bazı bilinen provider sayfaları sitemap'te yoktur.

## Sonuç

v0.7 sonucu:

**C — PUBLIC DATE-INDEPENDENT INVENTORY PATH STILL NOT FOUND**

Bu yüzden:
- schema 7 yok,
- lodging connector yok,
- seed yok,
- UI yok.

Book>Direct ileride **price / availability snapshot** için değerli olabilir.

---

# Planlanan / henüz bağlı olmayan kaynak aileleri

Bunlar stratejik adaylardır; connector oldukları anlamına gelmez.

## Florida State Parks

Kullanım:
- state park metadata
- kurallar
- erişim / hizmetler

## NOAA / NCEI

Kullanım:
- historical climate
- mevsimsel analiz

## NDBC / NOAA Tides & Currents

Kullanım:
- deniz koşulları
- su sıcaklığı
- istasyon bazlı geçmiş

## EIA

Kullanım:
- fuel / energy price bağlamı

## Overture Maps

Kullanım:
- POI / transportation discovery
- spatial enrichment

## İşletmelerin kendi siteleri

Kullanım:
- restoran menü/fiyat
- doğrudan oda/tesis ayrıntısı
- hizmet bilgisi

Bu katman ancak doğru entity matching sonrasında daha güvenli hale gelir.

---

# Veri doğrulama anti-pattern'leri

Yapma:

- Bir tarih seçip availability listesini “tam inventory” sanma.
- Birkaç tarihi union edip completeness iddia etme.
- Search result count'u hard-coded expected count yapma.
- Adres üzerinden sessiz mahalle tahmini yapma.
- Kaynakta olmayan update time üretme.
- “empty” alanı “false/no” olarak yorumlama.
- Provider ile unit'i aynı entity türü sayma.
- Aynı isimli farklı kaydı sessiz merge etme.
- Kaynak değişince parser'ın sessizce eksik kayıt üretmesine izin verme.

---

# Production connector kabul kriteri

- Otorite/kaynak rolü tanımlı.
- Semantik açık.
- Scope açık.
- Stable identity var.
- Pagination/bitiş açık.
- Raw kanıt tutuluyor.
- Hata/cancel atomik.
- Domain schema semantiğe uygun.
- Destination isolation doğru.
- Fixture testleri var.
- Live smoke başarılı.
- Kullanıcı DB migration kopyada test edilmiş.
- UI yanlış anlam üretmiyor.
