# M6 — Konaklama kaynağı keşfi

Keşif: 1–2 Ekim 2026. Durum: JSON sözleşmesi doğrulandı; tarihten bağımsız tam envanter gereksinimi henüz karşılanmadı. Connector uygulaması başlamadı. Uygulama 0.6.0 ve SQLite şema 6 olarak kaldı.

## Gerçek Stay adresi ve yöntem

[Visit South Walton ana sayfasının](https://www.visitsouthwalton.com/) “Book Your Stay” bağlantısı şu hedefi yayımlıyor:

`https://visitsouthwalton.bookdirect.net/#/lodgings?campaign=staynav`

Resmi turizm bülteninin STAY bağlantısı da `https://visitsouthwalton.bookdirect.net/` adresine yönlendi. Ayrı bir VisitSouthWalton.com Stay envanter HTML'i doğrulanmadı. Kaynak kimliği için aday canonical giriş `https://visitsouthwalton.bookdirect.net/`; fragment ve campaign takip parametresi kimliğe dahil edilmez. Henüz seed eklenmedi.

Giriş HTML'i kayıtları içermeyen AngularJS kabuğudur. Keşif sırasında `<base href="/20260930092117/">` ve `bookdirect.min.js` script referansı vardı. Gerçek script:

`https://visitsouthwalton.bookdirect.net/20260930092117/bookdirect.min.js`

Bu sürümlü yol kalıcı endpoint olarak sabitlenmemelidir; giriş HTML'inden çözülmelidir. JS çalıştırmadan HTML ve script HTTP üzerinden okundu. Public frontend'in Clone, Lodgings ve Lodging servis tanımlarındaki adresler kullanıldı; endpoint tahmini yapılmadı. **Çalışan veri yöntemi JSON'dur; Playwright gerekmiyor.**

## Doğrulanan endpoint ve sözleşme

API host: `admin.bookdirect.net`. Clone kapsamı: `visitsouthwalton.bookdirect.net`.

| Amaç | Method | Exact endpoint |
|---|---|---|
| Filtreler, konumlar, kategoriler, amenities | GET | `https://admin.bookdirect.net/hs4/api/v1/clones/visitsouthwalton.bookdirect.net/show.json` |
| Sayfalı sonuçlar | GET | `https://admin.bookdirect.net/hs4/api/v1/clones/visitsouthwalton.bookdirect.net/lodgings.json` |
| Gözlenen kaydın detayı | GET | `https://admin.bookdirect.net/hs4/api/v1/clones/visitsouthwalton.bookdirect.net/lodgings/540249.json` |

İstek gövdesi yoktur. Public uygulama scriptinde yayımlanan istemci değeri, uygulamanın kullandığı `Authorization: Token token=<public client value>` başlığıyla gönderildi. Kişisel hesap, oturum veya özel yönetim erişimi kullanılmadı. Değer belgeye/koda sabitlenmedi; izin verilen host dışına gönderilmemelidir. İstemci scriptinin yayınlanan sözleşmesi değişirse açık hata gerekir.

Çalışan liste sorgusu örneği:

```text
?page=1&checkin=20261002&checkout=20261003&per_page=50&category_ids%5B%5D=103&sort=title&direction=asc&group_ids%5B%5D=62708
```

- `checkin`, `checkout`: YYYYMMDD. `checkin` kaldırıldığında ve boş gönderildiğinde HTTP 400, `'checkin' parameter is required` yanıtı alındı.
- `page`: 1 tabanlı. `per_page=50` doğrulandı.
- `group_ids[]`: yapılandırmadaki konum kimliği; 62708 Dune Allen.
- `category_ids[]`: yapılandırmadaki kategori kimliği; 103 All Lodging.
- `sort=title&direction=asc`: uygulama scriptinde bulunan sıralama sözleşmesi.
- Yanıt: `request.total_count`, `request.total_pages`, `request.current_page`; kayıtlar `data.lodgings[].lodging`.
- Detay yanıtı: `data.lodging`. Örnek detay, aynı kaydın listedeki envanter alanlarını tekrar döndürdü; ayrı detay isteğinin her kayıt için gerekli olduğu henüz gösterilmedi.

Script ayrıca `lodgings/live_rates.json` servisini içeriyor. Bu servise istek yapılmadı. Fiyat/availability toplama geliştirilmedi.

## Tam envanter sorunu — doğrulanan kanıt

2 Ekim 2026'da aynı Dune Allen filtresi ve aynı alfabetik sıralamayla iki aralığın bütün sayfaları okundu:

| Aralık | API total_count | Sayfa | Benzersiz ID |
|---|---:|---:|---:|
| 2–3 Ekim 2026 | 112 | 3 | 112 |
| 2–3 Kasım 2026 | 113 | 3 | 113 |

İlk kümede olup ikinci kümede olmayan ID yok. Yalnız ikinci kümede `526140` (Dune Nothin) var. Altı yanıt dosyası ve SHA-256 değerleri yerel keşif kanıtında saklandı. Bu, sadece üstteki sonuç sayısına bakılarak verilmiş bir karar değildir; bütün sayfaların explicit ID kümeleri karşılaştırıldı.

1 Ekim'deki ön kontrolde de 1–2 Ekim için 112, 1–2 Kasım için 114 sonucu alınmıştı. Bu sayılar uygulama sabiti veya kalıcı kabul ölçütü değildir.

**Sonuç:** keşfedilen endpoint'in bu kullanım biçimi tarih aralığına bağlı bir sonuç kümesidir. Listeyi tek bir tarihle çekip “tam konaklama envanteri” diye yayımlamak doğrulanmış olmaz. Farkın backend'deki kesin kuralı bilinmiyor; kayıt farkından müsaitlik, minimum konaklama veya silinme nedeni tahmin edilmiyor. Tarihleri birleştirmek de tüm envanterin kapsandığını kanıtlamaz. Böyle bir farkı normal envanter diff'inde “kaldırıldı” diye göstermek yanıltıcı olabilir.

Public giriş HTML'i, frontend servis sözleşmesi ve clone yapılandırmasında doğrulanmış tarihsiz liste yolu bulunamadı. Bu, sağlayıcının hiçbir inventory/export servisi olmadığı iddiası değildir. Gereken sonraki kanıt, sağlayıcının desteklediği tarihsiz inventory yolu veya kullanıcı tarafından açıkça onaylanmış daha dar kapsamdır. Tarayıcıda aynı uygulamayı çalıştırmak bu kapsam sorununu çözmez.

## Kayıt semantiği ve alanlar

Kaynak tek tip işletme dizini değildir. Örnek `540249` kaydı “30A Florida Flashback” adında, 5 yatak odalı, 3 banyolu, 12 kişilik kiralık birimdir. Yapılandırma ayrıca Hotels, Resorts, Rental Agencies, Bed & Breakfast Inns, Campgrounds & RV Parks kategorilerini yayımlar. Her kaydı hotel veya her kaydı rental_unit olarak sınıflandırmak doğru değildir.

Explicit `lodging.id` stabil kimlik adayıdır; ad veya sorgu metninden ID üretilmez. Kaynak kategori adları korunmalı; birden fazla veya belirsiz kategori varsa agresif sınıflandırma yapılmamalıdır. Aynı ID'nin farklı ad/kanonik referansla tekrarı doğrulama hatası olmalıdır.

| Kaynak alanı | Aday envanter alanı / davranış |
|---|---|
| id, title | external_id, name |
| category_ids + clone.categories | source_type; muhafazakâr entity_kind eşlemesi |
| address, city, state, zip_code | Adres alanları; boş değer NULL |
| latitude, longitude | Sayısal/range doğrulaması; boş değer NULL |
| bedrooms, bathrooms, sleeps | bedrooms, bathrooms, max_guests; boş değer NULL |
| description | Temizlenmiş kaynak açıklaması; boş değer NULL |
| phone, toll_free | Telefon ve alternatif telefon provenance'ı; boş değer NULL |
| url | Yayınlanan harici bağlantı; veri olarak saklanabilir, crawl edilmez |
| amenity_ids + clone.amenities | Kaynağın etiketlerinden list[str] |
| location_id / group_ids[] | Açık kaynak konumu ve filtre provenance'ı |

Örneklerde unit_count, email, address_line_2 veya gerçek güncelleme timestamp'i doğrulanmadı. Bulunmayan alanlara değer türetilmemelidir. `source_updated` için `fetched_at` kullanılmamalıdır. Yanıtlardaki rate/currency/min_stays/liveness alanları v0.7 envanter modeline alınmamalıdır. Ham kaynak yanıtı bunları içerebilir; bu, ayrı fiyat/availability snapshot modeli kurulduğu anlamına gelmez.

Amenities sözlüğünde görülen değerler: Internet Access, Swimming Pool, Pets Allowed, Gulf Front, Fitness Center. Bunlar başka bir taxonomy'ye çevrilmeden kaynak etiketi olarak korunabilir.

## 30A kapsamı ve güvenlik

Clone yapılandırması 19 konum yayımlıyor. 13 canonical 30A bölgesi için runtime `context.canonical_regions` kullanılmalı. Kaynakta Seagrove ve Seagrove Beach ayrı filtrelerdir; Watercolor ve Watersound yazımları canonical WaterColor/WaterSound ile açık profil eşlemesi gerektirir. Adres veya koordinattan mahalle tahmini yapılmamalıdır.

Miramar Beach, Seascape, Sandestin yanında kaynakta Defuniak Springs ve Freeport da var; bunlar 30A profilinin 13 bölgesine dahil değildir. Bir kayıt birden fazla onaylı filtrede bulunursa tüm provenance ilişkileri korunmalı; kimlik yalnız bir kez saklanmalıdır.

Gerekli aday fetch host'ları `visitsouthwalton.bookdirect.net` (public kabuk/script) ve `admin.bookdirect.net` (yalnız doğrulanan clone API yolları). Resmi kaynak keşfi için `www.visitsouthwalton.com` kullanıldı. Her yönlendirme allowlist ve path kontrollerinden geçmelidir. Kaynakların yayımladığı işletme URL'leri ve VRBO dahil üçüncü taraf bağlantılar takip edilmedi; Airbnb/VRBO/Booking/Expedia scrape yapılmadı.

## Uygulama kararı ve sonraki adım

`south-walton-lodging/1`, method JSON ve destination_id=30a eşlemesi teknik olarak mümkün görünüyor; ancak tarihsiz tam envanter sözleşmesi henüz doğrulanmadığı için connector, seed, schema 7 ve UI eklenmedi. Kullanıcı DB'si değiştirilmedi. Başarılı v0.6 release korunuyor.

Tam envanter gereksinimi korunacaksa inventory/export sözleşmesi doğrulanmadan uygulamaya geçilmemeli. Tarihle sınırlı liste onaylanırsa kapsam, arama tarihleri, diff karşılaştırılabilirliği ve eksik kapsama ilişkin UI metinleri önce açıkça yeniden tanımlanmalı. Bunun v0.8 fiyat/müsaitlik katmanıyla karıştırılmaması gerekir.

Yerel araştırma dosyaları repo dışındaki `work/lodging-discovery/` klasöründe: `show.json`, `detail.json`, `comparison-20261002-{1,2,3}.json`, `comparison-20261102-{1,2,3}.json`, `date-comparison-result.json`. Public script ve ham yanıtlar Git'e eklenmedi.
