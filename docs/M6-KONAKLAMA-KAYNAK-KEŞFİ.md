# M6 — Konaklama kaynağı keşfi

> **GÖREV-07 notu (7 Ekim 2026):** tarihli arama anlık görüntüleri toplayıcısı yazıldı (`bookdirect-lodging/1`, şema 10); yöntem ve sınırlar `docs/M10-KONAKLAMA-PROFILI.md`. Bu belge keşif kaydıdır.

Keşif: 1–3 Ekim 2026. İkinci aşama sonucu **C — PUBLIC DATE-INDEPENDENT INVENTORY PATH STILL NOT FOUND**. Public JSON arama sözleşmesi doğrulandı; tarihten bağımsız tam envanter gereksinimi karşılanmadı. Connector uygulaması başlamadı. Uygulama 0.6.0 ve SQLite şema 6 olarak kaldı.

**v0.7 için elimizde hâlâ yalnız date-filtered search var; tam unit inventory veya provider inventory doğrulanmadı.** Statik sağlayıcı sayfaları bulunması, tüm sağlayıcıları keşfeden bir envanter yolu bulunduğu anlamına gelmiyor. Tam/tarihten bağımsız envanter şartı korunuyor.

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

Public giriş HTML'i, frontend servis sözleşmesi ve clone yapılandırmasında doğrulanmış tarihsiz liste yolu bulunamadı. Bu, sağlayıcının hiçbir inventory/export servisi olmadığı iddiası değildir. Gereken sonraki kanıt, sağlayıcının desteklediği tarihsiz inventory yoludur. Kullanıcının ikinci aşama kararı gereği kapsam tarihli aramaya daraltılmaz. Tarayıcıda aynı uygulamayı çalıştırmak bu kapsam sorununu çözmez.

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

Tam envanter gereksinimi korunuyor; inventory/export sözleşmesi doğrulanmadan uygulamaya geçilmeyecek. Tarih union'ı veya başka bir rastgele gelecek tarih, kapsama sorununu gidermez. v0.8 fiyat/müsaitlik katmanı bu görevin kapsamı değildir.

Yerel araştırma dosyaları repo dışındaki `work/lodging-discovery/` klasöründe: `show.json`, `detail.json`, `comparison-20261002-{1,2,3}.json`, `comparison-20261102-{1,2,3}.json`, `date-comparison-result.json`. Public script ve ham yanıtlar Git'e eklenmedi.

## İkinci aşama — 3 Ekim 2026

### Resmi Parent / Child modeli ve güncel yönetim yolu

[Website Listings SOP, s. 1–3](https://www.visitsouthwalton.com/userfiles/downloads/websitelistings/Website_Listing_-_SOP_FINAL.pdf), kiralama şirketini Parent Listing, tekil birimleri Child Listings olarak tarif eder; bunlar aynı partner/extranet hesabından yönetilebilir. Parent şirket/storefront bilgisini taşır. Ancak child kayıtları tüm birimlerin birebir dökümü olmak zorunda değildir: mahalle başına temsili örnekler ve en fazla beş örnek önerilir; bu kesin bir limit değildir. Tek birim de kendi başına parent olabilir. Dolayısıyla parent her zaman agency, child listesi de eksiksiz unit inventory sayılamaz.

SOP, yönetilen kayıtların arama tarihinden bağımsız var olabileceğini destekler; public enumeration endpoint'ini veya Book>Direct ile ortak ID sözleşmesini kanıtlamaz.

**Güncel resmi sayfa bu tarihsel modeli sınırlar:** eski VSW Website Listings adresi HTTP 301 ile [Walton County Tourism Website Listings](https://www.waltoncountyfltourism.com/website-listings/) sayfasına yönleniyor. Bu sayfa, accommodation kayıtlarının artık Extranet ile eşitlenmediğini ve Book>Direct üzerinden yönetildiğini açıkça söylüyor. Partnerin Extranet erişimi iletişim bilgileri için sürüyor; accommodation listings bölümü kullanılmıyor. Bu nedenle eski SOP üzerinden güncel Simpleview accommodation index'i varsayılmadı. Login, partner hesabı ve özel yönetim uçlarına erişilmedi.

### Book>Direct bundle taraması

Girişten yeniden çözülen sürüm yine `20260930092117`. Script 229.280 byte; SHA-256:

`5a1ee933a2662d182b93b32124f8bb4d2dcc8f5afdead8d2acad168623ebf8f6`

Terimler büyük/küçük harf duyarsız alt dize olarak bütün dosyada tarandı. Sayılar endpoint sayısı değildir; örneğin lodging, lodgings eşleşmelerini de içerir.

| Terim | Adet | Terim | Adet |
|---|---:|---|---:|
| lodging | 371 | lodgings | 227 |
| listing | 46 | listings | 18 |
| inventory | 0 | properties | 3 |
| units | 5 | accommodations | 0 |
| partners | 0 | parent | 46 |
| children | 16 | child | 23 |
| agencies | 0 | clone | 525 |
| search | 482 | availability | 10 |
| rates | 64 | groups | 1 |
| categories | 40 | | |

`properties` eşleşmeleri IntentMedia analitik nesnesine, `units` mesafe birimine, `groups` clone alt gruplarına aittir. Parent/child sözcükleri tek başına ilişki kanıtı değildir: Angular/DOM ve uçuş yolcu alanları da bu kelimeleri kullanır. Konaklama parent/child ilişki servisi veya ayrı inventory kaynağı doğrulanmadı. Servis tanımları ve string konumları ayrıca çıkarıldı.

Aşağıdaki yollar bundle'da gerçekten vardır. Clone tabanı önceki bölümdeki `/hs4/api/v1/clones/visitsouthwalton.bookdirect.net` adresidir. Tablo statik inceleme ile HTTP denemesini ayrı gösterir; listelenen her yol çağrılmış değildir.

| Clone tabanına eklenen yol | İnceleme / sonuç |
|---|---|
| `/show.json` | Tarihsiz GET 200; yapılandırma, tam kayıt index'i değil |
| `/lodgings.json` | Tarihsiz GET 400; önceki tam sayfa karşılaştırması tarih bağımlılığını gösteriyor |
| `/lodgings/search.json` | Tarihsiz GET ve `q=Dune&per_page=12` ile GET 400; tarihli isim araması çalışıyor |
| `/lodgings/:lodging_id.json` | Bilinen iki ID için tarihsiz GET 400; tarihli detay 200 |
| `/lodgings/:lodging_id/packages.json` | Bilinen ID'nin paketleri; ayrı ID index'i değil, çağrılmadı |
| `/lodgings/:lodging_id/rates.json` | Bilinen ID'nin fiyatları; çağrılmadı |
| `/lodgings/live_rates.json` | Canlı fiyat servisi; çağrılmadı |
| `/packages.json`, `/packages/search.json` | Paket arama servisleri; lodging index'i olarak doğrulanmadı, çağrılmadı |
| `/restaurants.json`, `/restaurants/search.json`, `/restaurants/:restaurant_id.json` | Restoran kaynakları; kapsam dışı, çağrılmadı |
| `/venues.json`, `/venues/search.json`, `/venues/:id.json` | Activities servisleri; kapsam dışı, çağrılmadı |
| `/flights.json` | Uçuş servisi; kapsam dışı, çağrılmadı |

Bu GET kaynaklarının bundle'daki `.jsonp?` varyantları eski tarayıcı fallback'leridir; ayrı bir inventory kaynağı olarak sayılmadı veya çağrılmadı. Tam literal listesi ve karakter konumları [kanıt dosyasında](evidence/M6-phase2-2026-10-03.json).

Diğer bulunan yollar da ayrıştırıldı:

- Clone altındaki `/booking_submissions.json`, `/clicks.json`, `/lodgings/:lodging_id/track_click.json`, `/restaurants/track_click.json`, `/ticketed_events/track_click.json`: submission/tracking; çağrılmadı.
- Bilinen lodging altında birleştirilen `/redirect.json?group_id=`: booking yönlendirmesi; çağrılmadı.
- `/hs4/api/v1/airbnb_api/lodgings/:location`, `/hs4/api/v1/tripadvisor_api/lodging_reviews/:location_id`: üçüncü taraf lodging/review kaynakları; çağrılmadı.
- TrustYou `//api.trustyou.com/hotels/` tabanı ile birleştirilen `/meta_review.json?key=&callback=JSON_CALLBACK`, `/seal.json?key=&callback=JSON_CALLBACK`, `/meta_review.html?`, `/badges.html`: review/widget kaynakları; çağrılmadı.
- `/hs4/admin/lodgings/` + ID + `/dev_links`: credential kullanan admin yolu; public inventory adayı kabul edilmedi, **istek yapılmadı**.

UI route'ları (`/lodgings`, `/lodgings/ctab/:tab_id`, paket/restoran/aktivite/flight ekranları), asset ve analitik URL'leri API index'i değildir. Geliştirme/staging host'ları kullanılmadı. Endpoint adı veya auth parametresi tahmin edilmedi.

### Clone JSON'unun recursive incelemesi

`show.json` yanıtında kök dahil 592 node ve 528 scalar leaf gezildi; her JSON path için tip ve değer envanteri üretildi. Tam değerler yerel araştırma dosyalarında, path/tip ve değer parmak izleri [Git'teki kanıtta](evidence/M6-phase2-2026-10-03.json). Vendor HTML, analitik değerler ve public client token repoya kopyalanmadı.

İncelenen clone alanları: `id`, `name`, `city`, `state`, `show_no_availability`, `specials`, `show_events`, `show_restaurants`, `show_driving_distances`, `show_all_poi`, `template_style`, `host_site_fullname`, `locales`, `country`, `hostsite`, `field_values`, `filter_sets`, `interstitials`, `group`, `points_of_interest`, `amenities`, `categories`, `clones_categories`, `clone_tab_pages`, `custom_ratings`, `info_rules`.

- `group`: South Walton Area 62715; 19 alt konum. Kategori sayısı 8, amenity sayısı 5. Bunlar lodging ID listesi değildir.
- `clone_tab_pages`: 108–114 kimlikli 7 kategori sekmesi; property/partner ID listesi değil.
- `field_values`: header/footer HTML, navigasyon, stiller, analitik ve kart şablonları. `Directory URL`, `Only Display Member Properties`, `Hide Rates For Lodging Ids` ve `Live Rates Only` alanları boş.
- `show_no_availability=0` bir config değeridir. Backend'in kaydı hangi kesin kuralla dışladığını tek başına açıklamaz.
- Featured lodging index'i, agency/partner dökümü, `parent_id`, `child_ids`, doğrulanmış ilişki tablosu veya tarihsiz ID discovery link'i bulunmadı.

### Liste dışında kalan ID'nin detay denemesi

Yalnız önceki karşılaştırmanın iki tarih çifti tekrar kullanıldı; yeni rastgele tarih veya tarih union'ı oluşturulmadı. Aşağıdaki yollar clone tabanına göredir:

| GET | HTTP | Sonuç |
|---|---:|---|
| `/lodgings.json` | 400 | `'checkin' parameter is required` |
| `/lodgings/search.json` | 400 | Aynı tarih zorunluluğu |
| `/lodgings/search.json?q=Dune&per_page=12` | 400 | Arama metni zorunlu tarihi kaldırmıyor |
| `/lodgings/540249.json` | 400 | Bilinen ID tarihsiz detayı açmıyor |
| `/lodgings/526140.json` | 400 | Listeden eksik ID de tarihsiz açılamıyor |
| `/lodgings/526140.json?checkin=20261002&checkout=20261003` | 200 | Önceki Ekim sonuçlarında olmayan Dune Nothin kaydı erişilebilir |
| `/lodgings/526140.json?checkin=20261102&checkout=20261103` | 200 | Aynı ID ve temel kimlik alanları |

İlk detayda `average_rate=null`, `los=1`; ikinci detayda `average_rate="250.00"`, `los=4`. Her ikisinde `min_stays=null`, `liveness=null`, `client_status=0`, `aggregate_id=0`, `field_values=null`. `los=4` minimum dört gece şartı olarak yorumlanmadı; alanın bu anlamı doğrulanmış değil.

**Kanıtın sınırı:** 2 Ekim'deki tüm sayfalar farklı ID kümeleri verdi; 3 Ekim'de o farktaki ID aynı eski tarihlerle detaydan okunabiliyor. Bu, kaydın tamamen silindiği varsayımını desteklemez. Ancak iki gözlem farklı zamanlarda alınmıştır ve detail payload dışlama nedenini açıklamaz. Availability / minimum stay / active-inactive / başka backend scope ayrımı **unknown** kalır. Detay erişimi bir tarihli arama sonucunu tam inventory yapmaz.

### Visit South Walton sitemap, dizinler ve arama

`robots.txt` içindeki [sitemap.xml](https://www.visitsouthwalton.com/sitemap.xml) indirildi: sitemap index değil, 948 URL içeren `urlset`. Bunların 575'i `/listing/`, 11'i `/listings/`. XML alanları `loc`, `lastmod`, `changefreq`, `priority`; accommodation tipi, partner ID veya parent/child ilişkisi yok. URL adlarından envanter sınıflandırılmadı.

Sitemap'teki **11 dizinin tamamının** public HTML/form seçenekleri incelendi: `outdoors-nature`, `culinary-experiences`, `entertainment`, `golf`, `water-activities`, `arts-culture`, `spa-fitness`, `shopping`, `unique-spaces`, `meetings`, `weddings`.

Konaklamaya özel tam dizin bulunmadı. Meetings alan/büyüklük filtreleri sunuyor ve hotel dışı mekânları da içeriyor. Weddings içindeki `Venue with Accommodations` seçeneği düğün mekânı sınıfıdır; bütün lodging/provider kayıtlarının kapsamını garanti etmez. Seçenek adları kanıt dosyasında korundu.

Doğrudan okunan statik örnekler:

| Public sayfa | HTTP | Envanter açısından sınır |
|---|---:|---|
| [Dune Allen Realty Vacation Rentals](https://www.visitsouthwalton.com/dune-allen-realty-vacation-rentals/) | 200 | Sağlayıcı sayfası var; indirilen sitemap'te URL'si yok |
| [ResortQuest](https://www.visitsouthwalton.com/resortquest/) | 200 | Root-level legacy sağlayıcı sayfası; sitemap'te var |
| [Residence Inn](https://www.visitsouthwalton.com/residence-inn-by-marriott-sandestin-at-grand-boulevard/) | 200 | Root-level otel sayfası; sitemap'te var |
| [The Pearl Hotel](https://www.visitsouthwalton.com/listing/the-pearl-hotel/) | 200 | Meetings dizininden keşfedilen listing; JSON-LD `Store`, iletişim/konum alanları |

Genel Organization JSON-LD, VSW kuruluşunu tarif ediyor; rental agency ilişkisi olarak kullanılmadı. Örnekler tarihsiz sayfa varlığını doğrular, **tam provider inventory'yi doğrulamaz**. Dune Allen sayfasının sitemap'te bulunmaması da sitemap kapsamına dayanarak eksiksizlik iddiasını engeller.

Sayfadaki gerçek GET formu `/search/` ve `keywords` alanını kullanıyor. `/search/?keywords=accommodation` 200 dönüyor; 116 karma sonuç, ilk sayfada 10 kayıt ve 12 sayfaya bağlantı var. Blog, restoran, politika ve mekân sonuçları karışık. Typed accommodation/parent/unit index'i değildir; buradan elle isim listesi yapılmadı.

Sayfaların referans verdiği `https://cdn.visitsouthwalton.com/js/app.js?v=20260616` scripti incelendi. Dizin/arama için mevcut sayfaya seri hale getirilmiş form parametreleri ile GET kullanılıyor. İncelenen script/HTML'de ayrı WordPress REST, Algolia/Elastic inventory kaynağı veya accommodation embedded state bulunmadı. Varsayımsal `/wp-json/` veya tahmini arama API'leri çağrılmadı. Bu bulgu sitenin tüm altyapısının ispatı olarak sunulmaz.

### Book>Direct ile VSW kimlik ilişkisi

Kontrollü karşılaştırma için VSW'de görülen The Pearl Hotel, mevcut tarih çiftiyle frontend'in `lodgings/search.json?q=The%20Pearl&per_page=12&checkin=20261002&checkout=20261003` yolunda arandı. Sekiz metin eşleşmesi arasındaki The Pearl Hotel kaydının explicit Book>Direct ID'si `353512`; tarihli detail GET 200.

Detail `location_id=2449`, hotel kategori ilişkisi, `aggregate_id=null`, `field_values=null` döndürüyor. VSW tarafında kalıcı public referans `/listing/the-pearl-hotel/`; görsel yollarında `/userfiles/listings/12759/` görülüyor. **12759 belgelenmiş partner/listing ID'si kabul edilmedi**; yalnız asset dizin parçasıdır. İsim/site/telefon benzerliği, iki sistem arasında doğrulanmış foreign-key ilişkisi değildir. `353512 = 12759` denmedi; parent/child/agency eşlemesi türetilmedi.

### Son karar ve saklanan kanıt

Seçilen sonuç yalnız **C — PUBLIC DATE-INDEPENDENT INVENTORY PATH STILL NOT FOUND**.

A seçilmedi: tarihsiz kayıt index'i, bütün unit ID'leri ve eksiksiz sayfalama doğrulanmadı. B seçilmedi: statik sağlayıcı örnekleri var, ancak bütün provider/parent kayıtlarını deterministik olarak veren yol doğrulanmadı. Mevcut veri, tarihli Book>Direct araması ve bağımsız statik sayfa örnekleridir.

Uygulamaya geçmek için sağlayıcının desteklediği tarihsiz public read/export sözleşmesi; stabil kimlikler, sayfalama/bitiş koşulu, kayıt türleri, varsa parent/child ilişkileri ve 30A konum eşlemesi gerekir. Bu çalışma sağlayıcıya mesaj göndermedi veya özel erişim denemedi.

[Makinece okunabilir kanıt](evidence/M6-phase2-2026-10-03.json): 33 HTTP yanıtının URL/status/byte/SHA-256 manifesti; 64 API yol literal'inin bundle konumu; terim sayıları; 592 JSON node ve 528 leaf parmak izi; sitemap ve 11 dizinin filtre envanteri. Bu 64 literal benzersiz endpoint sayısı değildir. Manifestteki 33 yanıtın boyut/hash değerleri yerel dosyalarla doğrulandı. Eski tarih karşılaştırmasının altı sayfası önceki aşamanın ayrı kanıtıdır.

Repo dışı `work/lodging-phase2/` altında ham yanıtlar, bütün terim eşleşmeleri ve bağlamları, servis/string çıkarımları, recursive key/value envanteri ve sitemap sınıflandırması saklandı. Git'e yalnız keşif belgesi, aşama durumu ve token içermeyen kanıt eklendi. Uygulama kodu, source seed, UI, sürüm, şema ve production DB değiştirilmedi; main'e merge yapılmadı.
