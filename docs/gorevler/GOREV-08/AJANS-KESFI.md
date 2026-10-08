# GÖREV-08 · Kiralama şirketlerinden fiyat: keşif

Tarih: 8 Ekim 2026 · Girdi: gerçek veritabanındaki son konaklama çekimi `abe7764d13cb4c9198e2b873ebc4d7c7` (7 Ekim 2026, `bookdirect-lodging/1`)

## Özet

- Book>Direct'teki 2.389 ilanın 2.382'sinde bir şirket bağlantısı (`url`) var; bağlantılar 137 alan adına dağılıyor. İlk 13 alan adı ilanların üçte ikisini (%68,9) kapsıyor; ilk 40 alan adı (%94,6) incelendi.
- Fiyatı herkese açık gösterimden okunabilen dört altyapı bulundu: **ResCMS**, **Track**, **Streamline** ve **vacation-rentals/router**. Dördünde de kira, vergiler ve genel toplam ayrı geliyor, ücretleri şirketlerin çoğu adlarıyla ayrı gösteriyor (30A Escapes göstermiyor); müsait olmayan tarih sitenin kendi cümlesiyle bildiriliyor.
- Bu altyapıları kullanan ve Book>Direct bağlantıları ilan sayfasına giden **9 şirket** için uyarlayıcı yapılandırıldı: toplam **758 ilan** (%31,7). Gerçek kapsama (bağlantısı hâlâ çalışan, fiyatı alınabilen ilan) Adım 6'daki çekimde ölçüldü; rapora bakınız.
- En büyük şirket **360blue.com (256 ilan)** ile **oversee.us (185)**, **realjoy.com (61)**, **exclusive30a.com (29)** ve **oldseagrove.com (8)** Cloudflare arkasında. 360blue keşifteki art arda denemelerden sonra kullanıcının IP adresini engelledi; proxy kullanılmadı, bu siteler bu görevde kapsam dışı kaldı.
- Büyük bir engel de bağlantıların eskimesi: birçok şirkette Book>Direct'teki adres artık 404 veriyor, şirketin ana sayfasına ya da genel ilan listesine gidiyor. Bu ilanlar bağlantıyla eşlenemez (ad benzerliğiyle eşleme yapılmaz).

## Yöntem

1. Son konaklama çekiminin ham arama yanıtları salt okunur açıldı (`work/gorev-08/ilan_url.py`); her ilanın `url`, `phone`/`toll_free` ve `res_engine` alanı çıkarıldı. Mahalle, çekimdeki konum filtresinden geldi (adres veya koordinattan çıkarılmadı).
2. İlanlar `url` alan adına göre gruplandı (`www.` atılarak). Tam liste: `ajanslar.csv` (138 satır: 137 alan adı ve bağlantısız 7 ilan).
3. İlan sayısına göre ilk 40 alan adının her biri için 1–3 ilan sayfası açıldı (`work/gorev-08/altyapi_tespit.py`, istekler sıralı ve 1,5 sn arayla); sayfadaki altyapı izleri (ResCMS, Track, Streamline, router, Cloudflare vb.) ve şirket adı (sayfanın kendi telif satırı veya site adı) okundu.
4. İzi bulunan altyapılarda sitenin ön yüz betiği okunup fiyatı nereden aldığı bulundu; aynı istek tek tek denendi (`track_dene.py`, `streamline_dene.py`, `streamline_dogrula.py`, `router_dene.py`, `southern_dene.py`). Bütün ham yanıtlar `work/gorev-08/kesif/` altında (repoya girmez).
5. Toplayıcı yazıldıktan sonra her altyapıdan bir ilanla küçük bir canlı deneme yapıldı (5 ilan × 4 pencere, 36 istek, 41 sn): beşi de eşlendi, fiyat ve müsait değil yanıtları doğru ayrıştırıldı.

## Şirket tablosu (ilk 40 alan adı)

İlan sayısı, son konaklama çekimindeki benzersiz ilan; "Kümülatif %" 2.389 ilana göre. Şirket adı yalnız sitenin kendi sayfasında görüldüyse yazıldı. "Book>Direct rez. altyapısı" kaynağın `res_engine` alanı (ilk iki değer); "Site altyapısı" ilan sayfasında görülen izdir.

| # | Alan adı | Şirket (sitede görünen) | İlan | Kümülatif % | Başlıca mahalleler | Book>Direct rez. altyapısı | Site altyapısı | Fiyat yolu | Uyarlayıcı |
|---|---|---|---:|---:|---|---|---|---|---|
| 1 | 360blue.com | — (site açılamadı) | 256 | 10.7 | WaterColor 139; WaterSound 44; Seagrove 20 … | Natural Retreats 253; Escapia 3 | Cloudflare arkasında; altyapı okunamadı | site açılmadı | yok |
| 2 | benchmark30a.com | Benchmark Management | 241 | 20.8 | Seagrove 181; Seacrest 39; Blue Mountain Beach 8 … | Escapia 240; Res CMS 1 | ResCMS (Drupal) | çalışıyor: pricing/simple + pricing/quote | rescms |
| 3 | oversee.us | — (site açılamadı) | 185 | 28.5 | Seagrove 60; Seacrest 31; Blue Mountain Beach 24 … | VR Pros 172; - No Reservation Engine - 7 | Cloudflare arkasında; sayfada /vrp/ izi | site açılmadı | yok |
| 4 | 30aescapes.com | 30A Escapes | 162 | 35.3 | Seacrest 78; Rosemary Beach 28; Seagrove 27 … | TrackHs 83; TrackHS API 53 | Track bookingEngine | çalışıyor: POST ajax/quote | track |
| 5 | homeownerscollection.com | Homeowner's Collection | 143 | 41.3 | Seaside 137; Santa Rosa Beach 6 | Homeowners Collection 138; Res CMS 5 | ResCMS (Drupal) | altyapı çalışır; eşleme yok | yok |
| 6 | southernresorts.com | — (sayfada şirket adı satırı yok) | 104 | 45.7 | Blue Mountain Beach 29; Seagrove 25; Santa Rosa Beach 20 … | SouthernResorts 104 | kendi ön yüzü (/property/v3/quote) | bulunamadı | yok |
| 7 | oceanreefresorts.com | Ocean Reef Resorts | 96 | 49.7 | Grayton Beach 30; Santa Rosa Beach 23; Seagrove 18 … | Res CMS 96 | Track izleri | eşleme yok | yok |
| 8 | rosemarybeach.com | Rosemary Beach® | 89 | 53.4 | Rosemary Beach 83; Inlet Beach 4; Seacrest 2 | Irmnet Json 89 | Streamline (WordPress eklentisi) | çalışıyor: VerifyPropertyAvailability + GetPreReservationPrice | streamline |
| 9 | beautifulbeach.com | Dune Allen Realty Vacation Rentals | 87 | 57.1 | Dune Allen 70; Santa Rosa Beach 8; Blue Mountain Beach 4 … | VR Pros 87 | vacation-rentals/router (WordPress) | çalışıyor: POST router getPrice | vr_router |
| 10 | rentals.cottagerentalagency.com | — (site yanıt vermedi) | 82 | 60.5 | Seaside 59; Seagrove 9; Inlet Beach 4 … | Synxis XML 75; - Unique - 6 | okunamadı | site açılmadı | yok |
| 11 | panhandlegetaways.com | Panhandle Getaways | 81 | 63.9 | WaterSound 56; Seacrest 13; Seagrove 5 … | VRM Reservations 53; Res CMS 28 | Track bookingEngine | çalışıyor: POST ajax/quote | track |
| 12 | realjoy.com | — (site açılamadı) | 61 | 66.4 | Seagrove 18; Santa Rosa Beach 12; Seacrest 9 … | Kigo 36; - Unique - 25 | Cloudflare arkasında | site açılmadı | yok |
| 13 | paradise30a.com | — (sayfada şirket adı satırı yok) | 59 | 68.9 | Inlet Beach 25; Seagrove 13; Seacrest 8 … | streamline api 59 | vacation-rentals/router (WordPress) | altyapı çalışır; eşleme yok | yok |
| 14 | 30a-vacay.com | 30A Vacay | 54 | 71.2 | Seacrest 20; Seagrove 11; Blue Mountain Beach 7 … | Live Rez 54 | WordPress | eşleme yok | yok |
| 15 | vrbo.com | — (platform) | 52 | 73.3 | Seagrove 13; Santa Rosa Beach 9; Blue Mountain Beach 8 … | VRBO API 52 | Vrbo | site açılmadı | yok |
| 16 | dunevacationrentals.com | Dune Vacation Rentals | 49 | 75.4 | WaterColor 27; WaterSound 8; Seaside 5 … | streamline api 48; - No Reservation Engine - 1 | Streamline (WordPress eklentisi) | çalışıyor: VerifyPropertyAvailability + GetPreReservationPrice | streamline |
| 17 | 30a-beachgirls.com | — (sayfa yok) | 48 | 77.4 | Blue Mountain Beach 20; Seacrest 11; WaterSound 9 … | streamline api 48 | okunamadı | eşleme yok | yok |
| 18 | grayt30avacations.com | Grayt 30A Vacations | 40 | 79.1 | Seagrove 17; Grayton Beach 15; Blue Mountain Beach 2 … | VRM Reservations 39; - No Reservation Engine - 1 | ResCMS (Drupal) | altyapı çalışır; eşleme yok | yok |
| 19 | sandersbeachrentals.com | Sanders Beach Rentals | 38 | 80.7 | WaterColor 32; Seagrove 2; WaterSound 2 … | Live Rez 38 | ResCMS (Drupal) | sayfada fiyat sorgusu yok | yok |
| 20 | funvacay.com | — (sayfada şirket adı satırı yok) | 31 | 82.0 | Seagrove 9; Santa Rosa Beach 6; Dune Allen 3 … | Res CMS 31 | ResCMS (Drupal) | sayfada fiyat sorgusu yok | yok |
| 21 | exclusive30a.com | — (site açılamadı) | 29 | 83.2 | WaterColor 15; Seacrest 4; Seaside 4 … | Escapia 29 | Cloudflare arkasında | site açılmadı | yok |
| 22 | yourfriendatthebeach.com | Your Friend at the Beach | 22 | 84.1 | Blue Mountain Beach 21; Santa Rosa Beach 1 | Escapia 22 | WordPress (Barefoot/Escapia izleri) | incelenmedi | yok |
| 23 | vacasa.com | — (site açılamadı) | 21 | 85.0 | Santa Rosa Beach 8; Seacrest 4; Seagrove 4 … | Vacasa 21 | Vacasa | site açılmadı | yok |
| 24 | outdoorshower30a.com | — (site yanıt vermedi) | 21 | 85.9 | Seacrest 13; WaterSound 5; Seagrove 2 … | Live Rez 21 | okunamadı | site açılmadı | yok |
| 25 | 30abeachstays.com | — (başlıkta '30a Beach Stays') | 21 | 86.7 | Santa Rosa Beach 14; Inlet Beach 7 | - No Reservation Engine - 21 | farklı altyapı | incelenmedi | yok |
| 26 | airbnb.com | — (platform) | 19 | 87.5 | Santa Rosa Beach 9; Inlet Beach 2; Rosemary Beach 2 … | AirBnb API 17; - No Reservation Engine - 1 | Airbnb | incelenmedi | yok |
| 27 | legacybeachhomes.com | Legacy Beach Homes | 18 | 88.3 | Seagrove 8; Dune Allen 7; Blue Mountain Beach 1 … | - Unique - 17; - No Reservation Engine - 1 | WordPress | incelenmedi | yok |
| 28 | graytoncoastrentals.com | Grayton Coast Rentals | 17 | 89.0 | Grayton Beach 10; WaterColor 3; Seagrove 2 … | Res CMS 17 | ResCMS (Drupal) | çalışıyor: pricing/simple + pricing/quote | rescms |
| 29 | 30acottagesandconcierge.com | 30A Cottages | 17 | 89.7 | Rosemary Beach 6; WaterColor 4; Seacrest 3 … | streamline api 17 | ResCMS (Drupal) | çalışıyor: pricing/simple + pricing/quote | rescms |
| 30 | destinvacation.com | Newman-Dailey Resort Properties, Inc. | 16 | 90.4 | Blue Mountain Beach 9; Santa Rosa Beach 7 | Instant Software Online XML 16 | farklı altyapı | incelenmedi | yok |
| 31 | myvacationhaven.com | My Vacation Haven | 15 | 91.0 | Santa Rosa Beach 4; Inlet Beach 3; Gulf Place 2 … | Escapia 15 | ResCMS (Drupal) | çalışıyor: pricing/simple + pricing/quote | rescms |
| 32 | wyndhamvacationrentals.com | — (site açılamadı) | 14 | 91.6 | Santa Rosa Beach 6; Seagrove 6; Seacrest 2 | Vacasa 14 | bağlantılar vacasa.com'a gidiyor | site açılmadı | yok |
| 33 | beachescapesrentals.com | Beach Escapes Realty | 13 | 92.1 | Santa Rosa Beach 10; Seagrove 2; Seacrest 1 | Live Rez 13 | Escapia izleri | eşleme yok | yok |
| 34 | coastalbluevacations.com | Coastal Blue Vacations | 12 | 92.6 | Blue Mountain Beach 5; Santa Rosa Beach 5; Gulf Place 1 … | Res CMS 12 | ResCMS (Drupal) | sayfada fiyat sorgusu yok | yok |
| 35 | cottagerentalagency.com | — (sandestin.com'a yönleniyor) | 10 | 93.1 | Santa Rosa Beach 10 | Synxis XML 10 | okunamadı | site açılmadı | yok |
| 36 | liv-vacations.com | Liv Vacations | 8 | 93.4 | Blue Mountain Beach 5; Seacrest 2; Seagrove 1 | Lodgix 8 | Lodgix (WordPress) | incelenmedi | yok |
| 37 | beachesofsouthwaltonvacations.com | Beaches of South Walton Vacations, LLC | 8 | 93.7 | Seagrove 4; Seacrest 3; Santa Rosa Beach 1 | - No Reservation Engine - 8 | okunamadı | eşleme yok | yok |
| 38 | oldseagrove.com | — (site açılamadı) | 8 | 94.1 | Seagrove 7; Santa Rosa Beach 1 | VRM Reservations 7; - Unique - 1 | Cloudflare arkasında | site açılmadı | yok |
| 39 | (url yok) | — | 7 | 94.3 | Santa Rosa Beach 5; Seacrest 1; Seagrove 1 | - No Reservation Engine and No Website - 7 | — | bağlantı yok | yok |
| 40 | alysbeach.com | Alys Beach | 6 | 94.6 | Alys Beach 6 | Reseze API 6 | WordPress | eşleme yok | yok |

Kalan 98 alan adı toplam 129 ilan (her biri 1–5 ilan); `ajanslar.csv`'de listeli, incelenmedi.

## Altyapı başına bulgular

### ResCMS (Drupal `rescms` modülü) — uyarlayıcı `rescms`

- **Şirketler:** Benchmark Management (benchmark30a.com, 241), Grayton Coast Rentals (17), 30A Cottages (17), My Vacation Haven (15). Aynı altyapıdaki Homeowner's Collection (143) ve Grayt 30A Vacations (40) için Book>Direct bağlantısı yalnız şirketin ana sayfasını gösterdiği için eşleme yapılamıyor; Sanders Beach Rentals, funvacay.com ve Coastal Blue Vacations'ın ilan sayfalarında fiyat sorgusu yok (yalnız müsaitlik takvimi).
- **Kimlik ve kurallar sayfanın HTML'inde:** `Drupal.settings.rcItemAvailForm` nesnesinde ilanın varlık kimliği (`eid`), varsayılan en az gece (`mns`), tarih aralıklı kurallar (`restr`: `b`–`e` aralığı, `mn` en az gece, `t` giriş günü; `t` 1=Pazartesi … 7=Pazar, 0=her gün) ve müsaitlik aralıkları (`avail`). Bazı sitelerde aynı nesne tek tırnaklı JavaScript olarak yazılıyor; uyarlayıcı ikisini de okuyor. Sayfanın tarih seçicisi (`jquery.rcItemAvailForm.js`) giriş gününü ve en az geceyi bu alanlardan hesaplıyor; uyarlayıcı aynı kuralı uygular ve kaynağı "sayfa" olarak etiketler.
- **Fiyat yolu (JSON servisi, ön yüzün çağırdığı):**
  1. `GET /rescms/ajax/item/pricing/simple?rcav[begin]=01/16/2027&rcav[end]=01/23/2027&rcav[flex_type]=d&rcav[adult]=2&rcav[child]=0&rcav[eid]=261` → `{"status":1,"content":"<HTML>"}`. Müsait değilse içerik `<span class="rc-na">Not Available</span>`; müsaitse vergiler hariç ara toplam (`$1,247`) ve "Show Detailed Quote" bağlantısı.
  2. Bağlantıdaki `GET /rescms/ajax/item/pricing/quote?…&rcav[IDs][8][0]=2261-210212` → kalem kalem tablo.
- **Örnek (benchmark30a.com, 19 Moonlit Shores Ln, 16–23 Ocak 2027):** Lodging $705,99 · Cleaning Fee $325,00 · Damage Waiver $125,00 · Booking Fee $90,63 · Sub-Total $1.246,62 · Tax $149,59 · **Total $1.396,21**. İsteğe bağlı seyahat sigortası ($100,34) "Declined" olarak ayrı satırda, toplama dahil değil. Aynı ilanın sayfasında bu tarih için en az gece 3; 17–24 Ekim 2026 için yanıt "Not Available".
- **Alanlar:** kira (Lodging satırı), temizlik ve diğer ücretler (satır adlarıyla), vergi, genel toplam, para birimi ($). Gecelik fiyat dökümü yok.

### Track (şirketin kendi alan adında `bookingEngine`) — uyarlayıcı `track`

- **Şirketler:** 30A Escapes (162), Panhandle Getaways (81). Ocean Reef Resorts'ta (96) da Track izleri var ama Book>Direct bağlantıları genel ilan listesine yönleniyor (eşleme yok). Southern Resorts'un sitesi Track izi taşısa da fiyatı başka bir servisten alıyor (aşağıda).
- **Kimlik sayfanın HTML'inde:** gizli form alanları `propertyID`, `roomTypeID`, `propertyName`, `hash`; istek adresi betikteki `siteFolder` + `ajax/quote` + `siteURLEnding`.
- **Fiyat yolu:** `POST /ajax/quote` (form: `checkin=01/16/2027&checkout=01/23/2027&propertyID=…`) → HTML döküm (`ul.pdp-quote-list`: Rent, Fees [alt kalemleriyle], Taxes, Total; her tutar `data-price` özniteliğinde). Müsait değilse yanıt yalnız `No` ya da "Unit has no availability for the dates specified."; kural ihlalinde uyarı metni ("This property has a **4 night** minimum for the selected dates."); servis hatasında `API Error`. Ön yüz betiği (`z_pdp.js`) bu üç durumu aynı şekilde ayırıyor.
- **Örnekler (16–23 Ocak 2027):** 30A Escapes, Mirasol Blue: Rent $1.729,15 · Taxes $207,50 · **Total $1.936,65** (bu şirket ücretleri ayrı göstermiyor). Panhandle Getaways (propertyID 23): Rent $2.303 · Fees $689 (Cleaning $380, Curbside Collection $31, Reservation Fee $179, Damage Waiver $99) · Taxes $347,16 · **Total $3.339,16**.
- **Kurallar:** sayfada müsaitlik takvimi var (gün sınıfları available/booked/check-in/check-out) ama en az gece yazmıyor; en az gece yalnız uyarı metninde geliyor ("yanıt" kaynaklı).

### Streamline (WordPress `streamline-core` eklentisi) — uyarlayıcı `streamline`

- **Şirketler:** Rosemary Beach® (rosemarybeach.com, 89), Dune Vacation Rentals (49). paradise30a.com Book>Direct'te "streamline api" görünse de sitesi router altyapısında.
- **Kimlik sayfanın HTML'inde:** `getRatesDetails(411533)` / `getCalendarDataNew(…)` çağrısındaki birim kimliği ve `streamlinecoreConfig.ajaxUrl` (sitenin `admin-ajax.php` adresi).
- **Fiyat yolu (ön yüzle aynı sırada):**
  1. `POST admin-ajax.php?action=streamlinecore-api-request&params={"methodName":"VerifyPropertyAvailability","params":{"unit_id":…,"startdate":"01/16/2027","enddate":"01/23/2027","occupants":2,…}}` → müsaitse `{"data":{"id":…}}`, değilse `{"status":{"code":"E0031","description":"We have no inventory available for the selected dates."}}`.
  2. `methodName: GetPreReservationPrice` (`separate_taxes: 1`) → JSON: `price` (kira), `required_fees[]`, `optional_fees[]` (isteğe bağlı; toplama dahil değil), `taxes_details[]`, `reservation_days[]` (gece gece fiyat), `total`, `currency`.
- **Örnekler:** Dune Vacation Rentals, More Grayter (16–23 Ocak 2027): kira $3.990 (7 × $570) · Admin Fee $299,25 · Amenity Rate $805 · Departure Clean $550 · Property Damage Protection $159 · vergiler $696,39 · **toplam $6.499,64**. Rosemary Beach®, Seaforth Cottage: kira $16.912 · ücretler $99 · vergiler $2.033,04 · **toplam $19.044,04**; bu ilanda `reservation_days` gece başına $2.000 gösteriyor (7 gece = $14.000), kira alanı ise $16.912 — fark sitenin kendi verisinde; ikisi de olduğu gibi saklanır.
- **Not:** fiyat servisi tek gecelik bir sorguyu da fiyatlıyor; müsaitlik ve kural kararı birinci çağrıdan alınıyor.

### "vacation-rentals/router" (WordPress, Vue ön yüz) — uyarlayıcı `vr_router`

- **Şirketler:** Dune Allen Realty Vacation Rentals (beautifulbeach.com, 87). Aynı altyapıdaki paradise30a.com'un (59) Book>Direct bağlantıları sayfa içi betikle sonuç listesine yönleniyor (eşleme yok).
- **Kimlik:** sayfadaki `unitId` ("3151-268932") ya da adresteki `/vacation-rentals/rental/<kimlik>/`.
- **Fiyat yolu:** `POST /vacation-rentals/router/` JSON `{"call":"getPrice","unitId":"3151-268932","people":2,"arrive":"1/16/2027","depart":"1/23/2027","nights":7,…}` → `isAvailable`, `rent`, `fees[]`, `taxes[]`, `bookingTotal`, `dueNow`, `extraneousPricing[]` (isteğe bağlı sigorta), müsait değilse `errorMsg` ("The unit … is unavailable for these dates …").
- **Örnek (Blue, 13–20 Mart 2027):** kira $2.800 · "Housekeeping, Damage Ins, Admin" $660 · Florida State Tax $242,20 · Walton County Tax $173 · **toplam $3.875,20**; isteğe bağlı sigorta $269,33 ayrı.

### Fiyat yolu bulunamayanlar

- **Southern Resorts (104 ilan):** kendi ön yüzü fiyatı `POST /property/v3/quote` servisinden alıyor; sayfadaki istek belirteci ve farklı tarih biçimleriyle yapılan denemeler 400/500 döndü. Doğru istek biçimi bulunamadı; uyarlayıcı yazılmadı.
- **Cloudflare arkasındakiler:** 360blue (256), oversee.us (185; sayfada VRP izi), realjoy (61), exclusive30a (29), oldseagrove (8). İlk istekler 403 ve doğrulama sayfası döndü. Görev yöntemine göre 360blue görünür Chrome'da (kalıcı profil) açıldı; ancak keşifteki art arda denemeler kullanıcının IP adresinin engellenmesine yol açtı. Kullanıcının önerdiği proxy kullanılmadı (sitenin engelini dolanmak olur); bu siteler bu görevde sorgulanmadı.
- **Platformlar:** Vrbo (52) 429 ve "Bot or Not?" doğrulaması; Airbnb (19) incelenmedi; Vacasa (21) ve Wyndham bağlantıları (14) 403.
- **Yanıt vermeyen veya eski bağlantılar:** rentals.cottagerentalagency.com (82) bağlantı kurulamadı; 30a-vacay.com (54) ve 30a-beachgirls.com (48) bağlantıları 404.

## Bağlantıların durumu

Book>Direct'teki `url` alanı şirketin bir zamanki ilan adresi. Keşifte birçok şirkette bu adresin artık çalışmadığı görüldü: 404 (30a-vacay, 30a-beachgirls, beautifulbeach ve panhandlegetaways'in bir kısmı), şirketin ana sayfası (homeownerscollection, grayt30avacations, beachesofsouthwaltonvacations) ya da genel liste (oceanreefresorts, paradise30a, alysbeach). Toplayıcı bu durumları ilan bazında ayrı ayrı kaydeder (`not_found`, `no_listing`, `off_site`); ilan adı ya da adres benzerliğiyle başka bir sayfaya eşleme yapılmaz.

## Uyarlayıcı kararı

| Uyarlayıcı | Şirketler (alan adı, ilan) | İlan |
|---|---|---:|
| `rescms` | benchmark30a.com 241, graytoncoastrentals.com 17, 30acottagesandconcierge.com 17, myvacationhaven.com 15 | 290 |
| `track` | 30aescapes.com 162, panhandlegetaways.com 81 | 243 |
| `streamline` | rosemarybeach.com 89, dunevacationrentals.com 49 | 138 |
| `vr_router` | beautifulbeach.com 87 | 87 |
| **Toplam** | 9 şirket | **758 (%31,7)** |

Eşleme destinasyon yapılandırmasında (`destination_agency_sites`, 30A için `studio/destinations/thirty_a.py` → `AGENCY_SITES`); yeni bir şirket aynı altyapıdaysa yalnız bir satır eklenir.

## Kısıtlar

- Fiyatlar sorgu günündeki sitenin gösterdiğidir; promosyon kodu, sadakat indirimi veya telefonla verilen fiyat dahil değildir. Misafir sayısı 2 yetişkin olarak sorulur (sitelerin fiyat formu bunu ister).
- "Müsait değil" ile "kural nedeniyle sorulamadı" ayrı tutulur; kural yalnız site gösterdiğinde yazılır.
- 360blue ve diğer Cloudflare siteleri, Southern Resorts ve eski bağlantılı ilanlar yüzünden fiyat örneği şirketlere göre dengesizdir (ör. WaterColor'daki ilanların çoğu 360blue'nun). Mahalle özetleri bu yüzden "fiyatı alınabilen ilanlar" diye etiketlenir; mahallenin tamamını temsil ettiği söylenmez.
