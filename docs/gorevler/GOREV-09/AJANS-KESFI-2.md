# GÖREV-09 · Kiralama şirketleri: ikinci keşif

Tarih: 8 Ekim 2026 · Girdi: GÖREV-08 gerçek çekimi (konaklama `bookdirect-lodging/1`, 2.389 ilan; şirket fiyatları `agency-lodging-rates/1`, 9 şirket) ve GÖREV-08 keşfi (`docs/gorevler/GOREV-08/AJANS-KESFI.md`).

## Özet

- Görevin saydığı şirketlerin hepsine bakıldı. **15 yeni şirket** yapılandırıldı (toplam 24): 6 yeni uyarlayıcı (`vrp`, `property_quote`, `exceptional_stay`, `asmx_quote`, `wander`, `qvr`) ve mevcut `rescms`, `track`, `vr_router` uyarlayıcıları.
- **Southern Resorts** (104 ilan) çözüldü: fiyat, sayfanın kendi `POST /property/v3/quote` isteğiyle alınıyor; belirteç gerekmiyor. Ön yüz toplamdan otomatik promosyonu düşüyor; toplayıcı da öyle yapıyor ve promosyonu ayrı kalem olarak saklıyor.
- Cloudflare arkasındaki **oversee.us** (185) ve **exclusive30a.com** (29) görünür, kalıcı profilli Chrome'da doğrulama ekranı çıkmadan açıldı; ikisi de "korumalı" olarak yapılandırıldı (yalnız görünür tarayıcıdan, istekler arası ≥ 6 sn, aynı anda tek korumalı şirket, ilk 403/429/engel sayfasında şirket durur).
- **360blue.com** engel sayfası ("Sorry, you have been blocked") sürüyor; bu görevde bırakıldı, gerçek çekimden hemen önce bir kez daha bakıldı (sonuç RAPOR.md'de). **realjoy.com** doğrulama ekranı (Cloudflare "Just a moment") gösterdi; görünür pencere iki kez açıldı (15 dk ve 40 dk), doğrulama tamamlanmadığı için yapılandırılmadı.
- Bağlantısı çalışmayan şirketler için **adres/konum eşlemesi** (Adım 3a) eklendi. Şirket listesi okunabilen siteler: Grayt 30A / Royal Destinations (site haritası, 49 ilan), 30A Vacay (site haritası, ~121 sayfa), Rosemary Beach ve Dune Vacation Rentals (Streamline liste servisi, 228 ve 91 ev), Oversee (VRP liste servisi), Alys Beach (VRP liste servisi, 73 ev).
- **Alys Beach Vacation Rentals** (vacation.alysbeach.com) tek topluluğun resmî programı: liste servisindeki 73 evin hepsinde şehir "Alys Beach", her kartta "Located in Alys Beach" yazıyor. Book>Direct'te olmayan evleri "şirketin kendi envanteri" olarak alınıyor (Adım 3c).
- **Your Friend at the Beach**: sitenin kendi fiyat formu "You are not authorized to use this service" hatası veriyor; tarih seçicinin okuduğu servis sezon başına **yayımlanmış gecelik kira aralığı** veriyor → Adım 3d "yayımlanmış kira" olarak ayrı saklanıyor.
- Sanders Beach Rentals, FunVacay ve Coastal Blue Vacations'ta (GÖREV-08: "fiyat formu yok") ResCMS fiyat formu **var**; GÖREV-08 sonucu küçük örnekten kaynaklanmış. Üçü de `rescms` ile fiyatlanıyor; yayımlanmış kira tablosuna gerek kalmadı.
- Bulunamayanlar: Cottage Rental Agency'nin güncel kiralama sitesi (alan adı Sandestin'in kaldırılmış sayfasına gidiyor), WaterColor ve WaterSound'un topluluğa ait resmî kiralama programı (iki aday alan adı bağlantı kurmuyor), 30A Beach Girls'ün kendi sitesi (evler AvantStay'de, kapsam dışı platform).

## Yöntem

1. Her şirket için Book>Direct'teki bir ilanın bağlantısı açıldı; sitenin ön yüz betiği okunup fiyatı hangi istekle aldığı bulundu ve aynı istek tek ilanla denendi (`work/gorev-09/` altındaki `southern_dene.py`, `form_alanlari.py`, `ham_bak.py`, `envanter_bak.py`). Ham yanıtlar `work/gorev-09/kesif/siteler/` altında (repoya girmez).
2. Korumalı siteler (oversee.us, exclusive30a.com, realjoy.com, oldseagrove.com, 360blue.com) yalnız görünür, kalıcı profilli Chrome penceresinden ve az istekle açıldı (`korumali_dene.py`); ham HTTP isteği art arda tekrarlanmadı. Site başına en çok 40 istek sınırının altında kalındı.
3. Toplayıcı yazıldıktan sonra her yeni uyarlayıcı tek ilanla canlı denendi (`mini_canli2.py`: deneme 1 = 8 şirket, 91 istek, 200 sn; deneme 2 = 2 korumalı şirket, 8 istek, 54 sn). Fiyat, müsait değil ve "fiyat yok" yanıtları doğru ayrıldı.
4. Misafir sayısı kontrolü (Adım 4) ayrı yapıldı: `misafir-sayisi-kontrol.csv`.

## Şirket başına bulgular

Sıra görevdeki öncelik sırasıdır. "Eşleme yolu": Book>Direct ilanının şirket sayfasıyla nasıl eşlendiği (bağlantı / adres / konum / kendi envanteri / yok).

### a) Seaside

**Homeowner's Collection** (homeownerscollection.com, 143 ilan) — ResCMS (Drupal).
- Fiyat yolu: `rescms` (pricing/simple + pricing/quote; GÖREV-08 uyarlayıcısı).
- Eşleme yolu: bağlantı. Yeniden bakıldığında Book>Direct bağlantılarının çoğu ilan sayfasına (`/seaside-vacation-rentals/<ad>`) gidiyor. 7 ilan "toplu" yer tutucu (ofis adresi 124 Quincy Circle, bağlantı ana sayfa); bunlar bir eve eşlenemez.
- Alanlar: kira, temizlik, "Seaside A&E Fee (Optional)" (sitenin ara toplamına dahil), vergi, toplam; "Travel Insurance (optional)" toplama dahil değil.
- Sonuç: yapılandırıldı (`rescms`).

**Cottage Rental Agency** (rentals.cottagerentalagency.com 82, cottagerentalagency.com 10).
- rentals.cottagerentalagency.com için DNS kaydı yok. cottagerentalagency.com, sandestin.com/accommodations/cottage-rental-agency sayfasına yönleniyor; o sayfa "Access denied" (tarayıcıda da aynı; kaldırılmış bir Drupal sayfası).
- Şirketin güncel bir kiralama sitesi bulunamadı; "yalnız Seaside'da kiralama yapıyoruz" beyanı okunamadı.
- Sonuç: yapılandırılmadı (eşleme yolu yok).

### b) Alys Beach

**Alys Beach Vacation Rentals** (alysbeach.com → vacation.alysbeach.com; Book>Direct'te 6 ilan) — VRPConnect (Gueststream WordPress eklentisi; satıcı Track).
- Fiyat yolu: `vrp`. Sayfadaki `#bookingform` alanları (`obj[Arrival]` AA/GG/YYYY, `obj[Departure]`, `obj[Adults]`, `obj[Children]`, `obj[PropID]`) `/?vrpjax=1&act=checkavailability` ile gönderiliyor; yanıt `TotalCost`, `TotalTax`, `Charges[{Description, Amount, Required}]`, `BookDetails`.
- Örnek (Bahar tatili 2027): kira 10.876,00 · ücretler 1.540,00 + 770,00 · vergi 1.582,32 · toplam 14.768,32. Yaz 2027: "Provided unit or unit type is not available for the dates provided." Sonbahar 2027: "Arrival date is beyond the maximum notice period. Please call to book." (fiyat yok; müsaitlik bilinmiyor).
- Envanter: `act=search` (json) tek istekte 73 ev veriyor: kimlik, Address1, City, enlem/boylam, oda, banyo, sayfa adı. 73 evin hepsinde City "Alys Beach" (Area: Homes North/South, Condos North/South, Studios North); liste sayfasındaki her kartta "Located in Alys Beach".
- Eşleme yolu: bağlantı + **kendi envanteri** (Adım 3c; mahalle `alys-beach`, yalnız City "Alys Beach" olan evler alınır). Geçici denemede okunan 73 evin sokakları (Governors Court, North Charles Street, North Somerset Street, North Castle Harbour Drive, Seven Wells Court, Nonesuch Way, Mark Twain Lane, Admiralty Row vb.) ve koordinatları (30,2831–30,2877 K; −86,0317–−86,0256 B) tek bir küçük alanda; topluluk dışı görünen adres yok. Book>Direct'teki 6 Alys Beach ilanı tek ev değil, "Alys Beach - 3 BR Homes" gibi grup kayıtları (bağlantıları genel sayfaya gidiyor); bir eve eşlenmedikleri için kendi envanteriyle çift sayım oluşmuyor.
- Sonuç: yapılandırıldı (`vrp`, kendi envanteri).

### c) WaterColor ve WaterSound

- Topluluğun kendisine ait resmî kiralama programı bulunamadı: watercolorvacationhomes.com ve watersoundvacationrentals.com SSL bağlantısı kurmuyor; topluluk sitelerinde kiralama yönetimi yapılmıyor (WaterColor ilanlarının çoğu 360blue ve Sanders Beach Rentals'ta, WaterSound ilanlarının çoğu Panhandle Getaways ve 360blue'da).
- **Sanders Beach Rentals** (sandersbeachrentals.com, 38 ilan; 32'si WaterColor) — ResCMS. İlan sayfasında ResCMS fiyat formu var (GÖREV-08'deki "yalnız takvim" sonucu küçük örnekten). Yayımlanmış sezon kira tablosu yok. Bir bağlantı 404, bir bağlantı 403 verdi. Eşleme yolu: bağlantı. Sonuç: yapılandırıldı (`rescms`).

### d) Grayton Beach

**Ocean Reef Resorts** (oceanreefresorts.com, 96) — Track.
- Fiyat yolu: `track` (POST ajax/quote; yanıt yalnız toplamı veriyor). Yeniden bakıldığında bağlantılar ilan sayfasına gidiyor.
- Eşleme yolu: bağlantı. Sonuç: yapılandırıldı (`track`).

**Grayt 30A Vacations / Royal Destinations** (grayt30avacations.com, 40) — ResCMS.
- Bağlantıların bir kısmı royaldestinations.com'a (aynı şirket grubu, ResCMS) yönleniyor; eski Escapia `detailpage` bağlantıları 404.
- Envanter: royaldestinations.com site haritası (`/30a-vacation-rentals/<ad>` sayfaları, 49 ilan); her sayfadan Drupal alanları (sokak, şehir, enlem/boylam, oda, banyo, kapasite).
- Eşleme yolu: bağlantı + adres (site haritasından). Takma alan adı: royaldestinations.com. Sonuç: yapılandırıldı (`rescms`).

### e) Blue Mountain Beach, Santa Rosa Beach, Seagrove

**Southern Vacation Rentals** (southernresorts.com, 104) — kendi Vue ön yüzü.
- İlan sayfasında `booking-data="{propertyInfo:{propertyId:5055,…}}"`. Tarih seçilince sayfa `POST /property/v3/quote` gönderiyor; gövde `{unitId:"5055", arrivalDate:"2027-07-10", departureDate:"2027-07-17", occupants:{adults:2, children:0, pets:0}, promoCode:"", applyAutoPromoCode:true}`. Belirteç yok; düz HTTP ile çalışıyor.
- Yanıt: `quote.sections.rent/fees/taxes` (kalemler + toplam), `quote.total`, `promoCode{name, value}`, `promoType "AutoApplied"`. Toplam = kira + ücretler + vergiler − otomatik promosyon; toplayıcı promosyonu eksi tutarlı ayrı kalem ("Promotion <kod> (AutoApplied)") olarak saklıyor.
- Örnek (Yaz 2027, ilan 529594): kira 3.434,25 · ücretler 345,00 (+ promosyon −2,80) · vergi 453,22 · toplam 4.229,67.
- Kaldırılmış ilanlar `/rentals/...?unavailableProperty=...` sayfasına yönleniyor (eşleşme yok).
- Eşleme yolu: bağlantı. Sonuç: yapılandırıldı (`property_quote`).

**Your Friend at the Beach** (yourfriendatthebeach.com, 22) — WordPress + Q4VR eklentisi (Escapia).
- Sitenin fiyat formu `admin-ajax action=q4vr_stay` isteğine "You are not authorized to use this service" yanıtı alıyor (sitenin kendi formunda da aynı hata).
- Tarih seçicinin okuduğu `q4vr_availability`, sezon başına `base_rate` ("$564-$636" gibi gecelik kira aralığı, vergi ve ücret hariç) veriyor.
- Fiyat yolu: yayımlanmış kira (Adım 3d). Pencerenin düştüğü sezon aralığı × 7 gece "yayımlanmış kira" olarak ayrı alana yazılır; 7 gecelik toplam fiyat ortancalarına karışmaz. Örnek (Yaz 2027): $564–$636 gecelik → 3.948–4.452 haftalık.
- Eşleme yolu: bağlantı. Sonuç: yapılandırıldı (`qvr`).

**30A Beach Stays** (30abeachstays.com, 21) — Wander SaaS.
- Fiyat yolu: `wander`. `POST https://api.wander.com/saas/website/listings/<kimlik>/estimate`, başlıklar `X-Website-Id` (sayfadaki `<html data-website-id>`) ve `X-Wander-Client: wander-customer-website`; gövde `{checkIn, checkOut, paymentType:"FULL", pricingSurface:"CALENDAR", numberOfGuests:2, numberOfPets:0}`. Yanıt kuruş cinsinden: `totalNightsPrice`, `totalWithFees`, `taxes.total` + döküm, `total`.
- Örnek (Yaz 2027): kira 2.760,78 · ücretler 180,14 · vergi 318,56 · toplam 3.259,48. Sonbahar 2027: `DATES_NOT_BOOKABLE` → fiyat yok (site nedenini söylemiyor; "müsait değil" denmez).
- Eşleme yolu: bağlantı. Sonuç: yapılandırıldı (`wander`).

**Beach Escapes Realty** (beachescapesrentals.com, 13) — eski `.asp` bağlantıları "Page Not Found" (HTTP 200) sayfasına gidiyor; şirketin ilan listesi için okunabilir bir servis bulunamadı. Sonuç: yapılandırılmadı (eşleme yolu yok).

**Newman-Dailey Resort Properties** (destinvacation.com, 15) — ASP.NET.
- Fiyat yolu: `asmx_quote`. `POST /service.asmx/GetQuote` gövde `{RentalId: 4418044, Arrival: '7/10/2027', Departure: '7/17/2027', PromoCode: ''}` → `d.Charge[{Charge, Amount}]` (Rent Charges, Departure Clean, Resort Fee per Night, Wristbands, Tax, Total, Deposit Due), `d.IsAvailable`, `d.Message`. Misafir sayısı istenmiyor.
- Örnek (Yaz 2027): kira 5.659,65 · ücretler 143,00 + 330,00 · vergi 735,93 · toplam 6.868,58.
- Eşleme yolu: bağlantı. Sonuç: yapılandırıldı (`asmx_quote`).

**30A Beach Girls** (30a-beachgirls.com, 48) — Next.js sitesi; bağlantılar 404. Web aramasında şirketin evleri AvantStay koleksiyonlarında ("provided by 30A Beach Girls") yayımlanıyor; AvantStay ulusal bir yönetim platformu (Vacasa benzeri), kapsam dışı. Sonuç: yapılandırılmadı.

### f) Inlet Beach

**Paradise Properties** (paradise30a.com, 59) — vacation-rentals/router (WordPress).
- Kısa bağlantılar (`paradise30a.com/LagoonLounge/`) yeniden bakıldığında `www.paradise30a.com/vacation-rentals/rental/<ad>/` ilan sayfasına yönleniyor; bazı sayfalarda başlık boş (betikle doluyor) ama `unitId` var.
- Fiyat yolu: `vr_router`. Eşleme yolu: bağlantı. Sonuç: yapılandırıldı.

### g) 30A Vacay

**30A Vacay** (30a-vacay.com, 54) — vacation-rentals/router (WordPress). Alan adı çalışıyor; Book>Direct'teki eski `.asp` bağlantıları 404. Site haritasında ~121 `/vacation-rentals/rental/<ad>` sayfası var; her sayfadan konum (enlem/boylam), oda ve banyo okunuyor.
- Eşleme yolu: adres/konum (site haritasından). Sonuç: yapılandırıldı (`vr_router`).

### h) Yapılandırılmış şirketlerdeki eskimiş bağlantılar

- **Rosemary Beach®** ve **Dune Vacation Rentals** (Streamline): `admin-ajax streamlinecore-api-request methodName=GetPropertyListWordPress` tek istekte bütün evleri veriyor (228 ve 91; kimlik, ad, enlem/boylam, oda, tam ve yarım banyo, sayfa adı). Adres alanı yok; `location_name` alanında "|" sonrası adres olarak okunabildiğinde adres, yoksa **konum** yöntemi kullanılıyor.
- **Panhandle Getaways** (Track): liste sayfasında koordinat yok, ~957 ilan bağlantısı var; sayfa sayfa okumak ağır olduğu için envanter yapılandırılmadı (eskimiş bağlantılar eşlenemiyor).
- **Benchmark, 30A Escapes, Dune Allen Realty, Grayton Coast, 30A Cottages, My Vacation Haven**: şirket listesi için tek istekli bir servis bulunamadı; bağlantıyla eşleme sürüyor.
- Bağlantısı olmayan 7 ilan şirkete bağlanamıyor (Book>Direct'te alan adı yok).

### i) Cloudflare arkasındakiler

- **360blue.com** (256): görünür kalıcı profilli Chrome'da ana sayfa bir kez açıldı → "Sorry, you have been blocked" (engel sayfası, doğrulama ekranı değil). Bu görevde bırakıldı; gerçek çekimden hemen önce bir kez daha açıldı (RAPOR.md).
- **oversee.us** (185) — VRPConnect. Görünür Chrome'da doğrulamasız açıldı (HTTP 200). Bağlantılar `/vrp/unit/<ad>-<kod>-15`. Form alanları `search[Adults]` biçiminde (Alys Beach'ten farklı; uyarlayıcı sayfadaki alan adını kullanıyor). Bahar 2027 örneği: "Unit has no availability for the dates specified."; Yaz 2027: toplam 7.290,49. Envanter: VRP liste servisi. Eşleme yolu: bağlantı + adres/konum. Sonuç: yapılandırıldı (`vrp`, korumalı).
- **exclusive30a.com** (29) — Exceptional Stay altyapısı. Görünür Chrome'da doğrulamasız açıldı. Bağlantı `/property-details/<ad>/` → `/vacation-rentals/<ad>`; sayfada `unitData={unitID:30}`. `GET /quote?arrival=…&departure=…&pid=30&numberOfAdult=2&numberOfChild=0&numberOfPets=0&nights=7…` → `guestDiscountedRent`, `otherChargesItemized` (zorunlu), `additionalAddonFee` (isteğe bağlı, toplama katılmıyor), `taxes`, `grandTotal`. Örnek (Yaz 2027): kira 8.300,41 · ücretler 169,00 + 420,00 · vergi 1.054,73 · toplam 9.944,14. Eşleme yolu: bağlantı. Sonuç: yapılandırıldı (`exceptional_stay`, korumalı).
- **realjoy.com** (61): ilk yanıt HTTP 403 "Just a moment..." (Cloudflare doğrulama ekranı). Görünür pencere açıldı, kullanıcıya bildirildi; 15 dk ve 40 dk içinde doğrulama tamamlanmadı. Sonuç: yapılandırılmadı (doğrulama bekliyor).
- **oldseagrove.com** (8): doğrulama çıkmadı; site stay30abeachvacations.com ana sayfasına yönleniyor, ilan bağlantıları ilan sayfasına gitmiyor. Sonuç: yapılandırılmadı (eşleme yolu yok).

### j) Fiyat formu olmayan ResCMS siteleri

- **Sanders Beach Rentals**, **FunVacay** (funvacay.com, 31), **Coastal Blue Vacations** (coastalbluevacations.com, 12): üçünde de ilan sayfasında ResCMS fiyat formu var; `rescms` ile fiyatlanıyor. Coastal Blue'da 4 bağlantıdan 2'si `TooManyRedirects` verdi. Yayımlanmış sezon kira tablosu yok.

## Diğer küçük şirketler

- **Legacy Beach Homes** (legacybeachhomes.com, 18): WordPress `/listing/` sayfaları; görev önceliği dışında kaldı, incelenmedi.
- **Outdoor Shower 30A** (outdoorshower30a.com, 21): bağlantı zaman aşımına uğradı.
- **Vrbo, Airbnb, Vacasa, Wyndham** platformları kapsam dışı (görev kuralı).

## Yeni uyarlayıcılar ve paylaşım

| Uyarlayıcı | Altyapı | Şirketler | Misafir sayısı gönderiyor mu |
|---|---|---|---|
| `vrp` | VRPConnect (Gueststream) | Oversee, Alys Beach | evet (formdaki alan adıyla) |
| `property_quote` | /property/v3/quote | Southern Vacation Rentals | evet |
| `exceptional_stay` | Exceptional Stay /quote | Exclusive 30A | evet |
| `asmx_quote` | ASP.NET service.asmx/GetQuote | Newman-Dailey | hayır (servis istemiyor) |
| `wander` | Wander SaaS estimate | 30A Beach Stays | evet |
| `qvr` | Q4VR (Escapia) | Your Friend at the Beach | yayımlanmış kira; fiyat sorgusu reddediliyor |
| `rescms` | ResCMS (Drupal) | + Homeowner's Collection, Grayt 30A, Sanders, FunVacay, Coastal Blue | evet |
| `track` | Track bookingEngine | + Ocean Reef Resorts | hayır (servis istemiyor) |
| `vr_router` | vacation-rentals/router | + Paradise Properties, 30A Vacay | evet |

Şirket → uyarlayıcı eşlemesi, takma alan adları, korumalı bayrağı, misafir kuralı, envanter kaynağı ve kendi envanteri mahallesi destinasyon yapılandırmasında (`destination_agency_sites`, migration v12 ile `studio/destinations/thirty_a.py` profilinden) durur; generic çekirdekte şirket adı yoktur.

## Gerçek çekim sonucu

Her şirketin gerçek çekimdeki durumu (eşleşen, fiyatlı ilan, eşleme yöntemi dağılımı) `ajanslar.csv` dosyasının `gorev09_durum` sütununda ve RAPOR.md'de.
