# M11 — Konaklama fiyatları (kiralama şirketlerinin kendi siteleri)

Tarih: 8 Ekim 2026 · Görevler: GÖREV-08 (`/1`), GÖREV-09 (`/2`) · Dal: `gorev-09-kapsama-restoran` · Uygulama `0.12.0` · Şema `12` · Toplayıcı `agency-lodging-rates/2`

## Durum

`agency-lodging-rates/1` GÖREV-08'de 9 şirketle gerçek veride çalıştı (510 ilana fiyat). GÖREV-09'da `/2`: 24 şirket, 6 yeni uyarlayıcı, adres/konum eşlemesi, şirketin kendi envanteri, yayımlanmış kira, misafir sayısı ve korumalı siteler. 8 Ekim 2026'da geçici klasörde (yeni şirketler ve yeni eşleme yollarıyla sınırlı) ve tam yedekten sonra gerçek veritabanında çalıştırıldı. Gerçek çekim `e54c9dfae72a4e06a0702d2394cd8083`: 10.172 istek, 209 dakika; 1.127 ilan şirket sitesinde bulundu, 1.066 ilana en az bir pencerede fiyat alındı; şirketin kendi envanterinden 73 ev (69 fiyatlı), yayımlanmış kira 21 ilan. Mahalle × pencere özeti: `docs/gorevler/GOREV-09/konaklama-fiyat-ozet.csv`; keşif `docs/gorevler/GOREV-09/AJANS-KESFI-2.md`; ayrıntılar `docs/gorevler/GOREV-09/RAPOR.md`.

GÖREV-10 (şema 13): aylık pencere kuralı (12 ay). İlk aylık çekim `b85a4b4e414a48508224575a378f0697` (10 Ekim 2026, düğmeyle toplu çalıştırma): 21.129 istek, 7 sa 42 dk; 1.131 ilan şirket sitesinde bulundu (bağlantı 1.119, adres 5, konum 7), 1.080 ilana en az bir ayda fiyat; kendi envanteri 73 ev (73 fiyatlı); Oversee bu kez tamamlandı (178 ilan, düzeltilmiş liste okumasıyla 4 yeni adres eşlemesi). Mahalle × ay özeti `docs/gorevler/GOREV-10/konaklama-fiyat-ozet.csv`, mevsimler `konaklama-mevsim-ozet.csv`, aynı hafta karşılaştırması `konaklama-ayni-hafta.csv`.

GÖREV-20 (16 Kasım 2026, şema 20, uygulama 0.21.0): fiyatı okunamayan altı şirket yeniden incelendi (aşağıda "Fiyatı okunamayan şirketler"); hiçbiri bu görevde okunabilir hale gelmedi, yeni uyarlayıcı ve yeni şirket satırı yok. Her birinin nedeni gözden geçirilmiş dosyaya yazıldı (`studio/destinations/thirty_a_agency_unread.csv`) ve kanıt paketine "Kiralama fiyatlarının kapsadığı şirketler" bloğuyla girdi. "Engelli 51 ilan"ın site engeli olmadığı, şirketlerin sitelerinde yayından kaldırılmış ilanlar olduğu görüldü. Çekim tahmini, son çekimden sonra eklenen şirketlerin isteklerini de sayar. Ayrıntı: `docs/gorevler/GOREV-20/RAPOR.md`.

GÖREV-22 (17 Kasım 2026, şema 22, uygulama 0.23.0): okunamayan şirketlerden ikisinin engeli bölge engeli çıktı (360 Blue, Vacasa);
ABD proxy'si üzerinden incelendi ve okuyucuları yazıldı (`nrbe`, `vacasa`). 30A Beach Girls'ün evleri, ilanlara bağlanmadan şirketin
kendi envanteri olarak okunur (`avantstay`; fiyat sorgusu henüz doğrulanmadığı için kapalı). Yapılandırma 27 şirket. Yeni şirketlerle
gerçek fiyat çekimi henüz yapılmadı (kullanıcı başlatacak). Ayrıntı aşağıda: "Bölge engelli iki şirket, bağlantıdaki numara kuralı ve
şirketin kendi sitesindeki evler".

GÖREV-23 (17 Kasım 2026, şema 23, uygulama 0.24.0): açık kalan dört şirket yeniden ele alındı. **30A Beach Girls:** AvantStay'in
servisine deneme istekleri yapıldı; evlerin haftalık **kirası** artık sitenin takviminden okunur (`inventory.own.quotes: true`), ücretli
ve vergili toplam ise yalnız sepet kaydı açan bir sorguyla geldiği için **sorulmaz**. **Vacasa:** arama sayfası `page_limit` ile 300 evin
tamamını tek istekte veriyor; okuyucu değişmedi, tam listeyle sınandı. **Outdoor Shower:** devralan LocalVR'nin sitesinde 30A'da ya da
Florida'da ev yok; okunacak site yok. **RealJoy:** eklentinin ilan sayfası kaydı bekleniyor. Yapılandırma 27 şirket (değişmedi).
Ayrıntı aşağıda: "GÖREV-23: AvantStay'in takvimi, Vacasa'nın tam listesi, LocalVR".

## Amaç

Ziyaretçinin yer seçiminde "burada kalmak ne kadar tutar" sorusuna kanıt. Book>Direct fiyatı çok az ilan için veriyor (GÖREV-07: 9.189 arama satırının 12'sinde liste fiyatı; takvimlerin çoğu gizli). Book>Direct ilanlarının çoğu bir kiralama şirketine ait ve ilan kaydındaki `url` alanı şirketin kendi ilan sayfasını gösteriyor; bu şirketlerin siteleri belirli tarihler için kalem kalem fiyat gösteriyor. Bu toplayıcı o fiyatı sitenin kendi herkese açık fiyat/müsaitlik gösteriminden okur.

## Kaynaklar

- Girdi: destinasyonun son başarılı Book>Direct konaklama çekimi (`lodging_listings`: Book>Direct kimliği, ad, `url`, yatak odası; mahalle, ilanın göründüğü konum filtrelerinden).
- Sorgulanan siteler: destinasyon yapılandırmasındaki kiralama şirketleri (`destination_agency_sites`: alan adı, sitede görünen şirket adı, uyarlayıcı, takma alan adları, korumalı bayrağı, misafir kuralı, şirket ilan listesi kaynağı, kendi envanteri mahallesi). 30A için 24 şirket (`studio/destinations/thirty_a.py` → `AGENCY_SITES`, `AGENCY_SITES_V12`, `AGENCY_SITE_OPTIONS`); seçimin gerekçesi ve dışarıda kalan şirketler `docs/gorevler/GOREV-08/AJANS-KESFI.md`, `docs/gorevler/GOREV-09/AJANS-KESFI-2.md` ve `docs/gorevler/GOREV-09/ajanslar.csv`'de.
- Tarih pencereleri: GÖREV-10'dan (şema 13) beri destinasyonun **aylık pencere kuralından** (aşağıda); kural tanımlı değilse konaklama yapılandırmasındaki sabit pencereler. Cumartesi–Cumartesi, 7 gece; varsayım, kaynak gerçeği değil. Geçmiş pencere sorulmaz ve "geçmiş" diye kaydedilir.
- Kaynak kaydı: "Kiralama şirketleri · Konaklama fiyatları", adres `https://visitsouthwalton.bookdirect.net/?kaynak=kiralama-sirketleri` (ilanların ve şirket bağlantılarının geldiği ön yüz; sorgu dizesi bu kaynağı konaklama arama kaynağından ayırır).

## Genel çekirdek ve uyarlayıcılar

`studio/sources/agency_rates.py` destinasyondan ve şirketten bağımsız çekirdektir: girdi ilanlarını şirket alan adına göre gruplar, her ilanın Book>Direct bağlantısını açar, uyarlayıcıya sayfadaki platform kimliğini buldurur, her pencere için fiyat sorar, ham yanıtları saklar, şirket bazında sonucu yazar. `studio/sources/agency_adapters.py` altyapı başına küçük uyarlayıcılardır; aynı altyapıyı kullanan şirketler aynı uyarlayıcıyı paylaşır:

| Uyarlayıcı | Sayfadaki kimlik | Fiyat isteği (sitenin ön yüzünün yaptığı) | Müsait değil / kural |
|---|---|---|---|
| `rescms` | `rcItemAvailForm.eid`; kurallar `restr` (`mn` en az gece, `t` giriş günü) | `GET /rescms/ajax/item/pricing/simple`, sonra "Show Detailed Quote" bağlantısı (`pricing/quote`) | `rc-na` "Not Available"; en az gece ve giriş günü sayfanın takviminden |
| `track` | gizli `propertyID` vb. alanlar; sayfanın müsaitlik takvimi (`td.booked` / `check-in` / `available`, `data-date`) | `POST /ajax/quote` (form) — yalnız takvimde pencerenin bütün geceleri boşsa ya da takvim pencereyi kapsamıyorsa | takvimde dolu gece (fiyat sorulmaz; kaynak sayfanın yanıtı); `No`; uyarı metni (ör. "4 night minimum"); `API Error` |
| `streamline` | `getRatesDetails(<birim>)`, `streamlinecoreConfig.ajaxUrl` | `VerifyPropertyAvailability`, sonra `GetPreReservationPrice` (`separate_taxes`) | `status.description` (ör. E0031 "no inventory available") |
| `vr_router` | `unitId` | `POST /vacation-rentals/router/` `getPrice` | `isAvailable:false` + `errorMsg` |
| `vrp` (v2) | `#bookingform` birim kimliği ve alan adları | `/?vrpjax=1&act=checkavailability` (formdaki `obj[...]` ya da `search[...]` alanlarıyla) | sitenin cümlesi ("Unit has no availability…"); "beyond the maximum notice period" → fiyat yok |
| `property_quote` (v2) | `booking-data` → `propertyId` | `POST /property/v3/quote` (`occupants`, `applyAutoPromoCode`) | sitenin cümlesi; otomatik promosyon ayrı eksi kalem |
| `exceptional_stay` (v2) | `unitData.unitID` | `GET /quote?arrival=&departure=&pid=&numberOfAdult=…` | `result` başarısızsa sitenin mesajı; isteğe bağlı ek ücret toplama katılmaz |
| `asmx_quote` (v2) | sayfadaki `rentalId` | `POST /service.asmx/GetQuote` | `IsAvailable` + `Message`; misafir sorulmaz |
| `wander` (v2) | `<html data-website-id>` + url'deki kimlik | `POST api.wander.com/.../estimate` | `DATES_NOT_BOOKABLE` → fiyat yok (müsaitlik bilinmiyor) |
| `qvr` (v2) | Q4VR birim kimliği | `admin-ajax q4vr_stay` (sitede reddediliyor) | yayımlanmış sezon kirası `q4vr_availability`'den ayrı tutulur |

Yeni bir şirket aynı altyapıdaysa yalnız yapılandırmaya bir satır eklenir; yeni bir altyapı için `agency_adapters.py`'ye bir uyarlayıcı (iki yöntem: `parse_page`, `quote`) yazılır.

## Eşleme

Önce **bağlantı**: ilanın Book>Direct `url`'si açılır, yönlendirmeler yalnız şirketin alan adı (ve yapılandırılmış takma alan adları) içinde izlenir, uyarlayıcı sayfada kendi platform kimliğini bulursa ilan eşlenmiş sayılır.

Bağlantı ilana gitmiyorsa (`not_found`, `no_listing`, `off_site`) ve şirketin ilan listesi yapılandırılmışsa (`inventory`: platformun liste servisi ya da site haritasındaki ilan sayfaları; her çekimde yeniden okunur, ham kopyası SHA-256 ile saklanır), ilan şirket listesiyle eşlenir (`studio/sources/agency_matching.py`):

- **Adres yöntemi** (listenin en az yarısında sokak adresi varsa): normalleştirilmiş sokak numarası + sokak adı birebir aynı (Street/St, Drive/Dr, East/E gibi USPS kısaltmaları; "County Highway 30A", "CR 30A", "Scenic Highway 30A" ve "30A" aynı yol), daire numarası aynı (bir tarafta varsa diğerinde de aynı olmalı), yatak odası aynı ve bu koşulları sağlayan **tek aday**. Birden fazla aday varsa eşleme yapılmaz ("belirsiz"). Koordinatlar iki tarafta da varsa adaylar 2 km içinde olmalı (yanlış şehirdeki aynı sokak adını eler).
- **Konum yöntemi** (şirket listesi adres vermiyorsa): koordinatlar arası en çok 15 m, yatak odası ve banyo aynı ve 50 m içinde bu değerlere sahip tek aday. Aynı 15 m içinde birden fazla Book>Direct ilanı olan yerlerde (çok daireli binalar) konum yöntemi kullanılmaz.
- İlan adı tek başına ya da ana ölçüt olarak kullanılmaz; yalnız kayda yazılır.
- Her eşleşmenin yöntemi (`link` / `address` / `location`) ve notu (`match_note`: hangi adres anahtarı ya da mesafe, neden eşlenmedi) saklanır ve arayüzde görünür.

**Şirketin kendi envanteri:** tek bir topluluğa hizmet eden resmî kiralama programında (30A: Alys Beach Vacation Rentals; `own_region_id` + `own_city`), şirket listesinde şehri sitenin kendi verisinde o topluluk olan ve Book>Direct'te olmayan evler (aynı sayfa, aynı url ya da adres kuralıyla aynı ev iki kez sayılmaz) ayrı tabloya alınır ve aynı pencerelerde fiyatlanır; topluluk dışındaki evler alınmaz (sayısı şirket kaydında). Özetlerde ayrı sütundur.

Sayfa durumları:

| Durum | Anlamı |
|---|---|
| `matched` | Sayfa açıldı, altyapının ilan kimliği bulundu; fiyat soruldu. |
| `not_found` | Şirket sitesi bu bağlantı için 404/410 ya da 200 kodlu "not found" sayfası döndürdü (eski bağlantı). |
| `no_listing` | Sayfa açıldı ama ilan sayfası değil (ana sayfa, genel liste, betikle yönlenen sayfa). |
| `off_site` | Bağlantı başka bir alan adına yönlendi; o siteye istek yapılmadı. |
| `blocked` | İlan sayfası 401/403/429 döndü (doğrulama sayfası değil). Ardından sitenin ana sayfasına bir kez bakılır: yanıt veriyorsa yalnız o ilan erişime kapalıdır; vermiyorsa ret şirketi durdurma sayacına yazılır. |
| `error` | Siteye ulaşılamadı (bir yeniden denemeden sonra) veya beklenmeyen HTTP durumu. |
| `not_queried` | Şirket durdurulduğu ya da atlandığı için bu ilana sıra gelmedi. |
| `no_adapter` | Bağlantı yapılandırılmamış bir şirketin sitesine gidiyor. |
| `no_url` | Book>Direct kaydında bağlantı yok. |

Adres/konum yöntemiyle eşlenen ilanda `link_status` bağlantının kendi sonucunu, `page_status` eşlenen sayfayı gösterir. Aynı bağlantıyı paylaşan ilanlar için sayfa bir kez açılır; aynı platform ilanı, pencere ve misafir sayısı için fiyat bir kez sorulur.

**Misafir sayısı:** her fiyatın kaç yetişkin ve çocukla sorulduğu saklanır (`adults`, `children`; servis misafir sormuyorsa boş). Kural şirket başına (`guest_rule`): `two_adults` ya da `bedrooms_x2` (yatak odası × 2 yetişkin, ilanın kapasitesini aşmadan). GÖREV-09 kontrolünde (`docs/gorevler/GOREV-09/misafir-sayisi-kontrol.csv`) hiçbir şirkette toplam misafir sayısıyla değişmedi; bütün şirketler `two_adults`.

**Yayımlanmış kira:** fiyat formu çalışmayan ama sezon kirası yayımlayan sitelerde (30A: Your Friend at the Beach, Q4VR) pencerenin düştüğü sezonun gecelik kira aralığı × gece sayısı `agency_rate_published`'a ayrı durumla yazılır; vergi ve ücret hariçtir ve 7 gecelik toplam fiyat ortancalarına karışmaz.

## Nezaket, ilerleme ve hatalar

- Aynı siteye istekler sıralı ve en az 2 sn arayla; en çok 3 şirket yan yana okunur. Ağ hatası bir kez (5 sn sonra) yeniden denenir.
- **Korumalı siteler** (`protected`: Cloudflare arkasındaki oversee.us ve exclusive30a.com): bütün istekler görünür, kalıcı profilli tarayıcı oturumunun içinden (sayfanın kendi `fetch`'iyle) yapılır; iki istek arasında en az 6 sn; aynı anda yalnız bir korumalı şirket okunur; ilk 403, 429 ya da engel sayfasında o şirket hemen durur (yeniden deneme yok) ve kayda `stopped_blocked` yazılır.
- Bir şirket art arda 3 isteği reddederse (403/429) ya da 5 kez ulaşılamazsa yalnız o şirket durdurulur; beklenmeyen bir hata da yalnız o şirketi "hata" olarak bitirir. Diğer şirketler devam eder; çekim kaydına şirket bazında durum, ilan, eşlenen, fiyatlı sorgu ve istek sayısı yazılır (`agency_rate_companies`).
- İlerleme şirket bazında ilan sayısıyla bildirilir; iptal her istekten önce ve beklemelerde denetlenir. İptal veya yarıda kalan çekim hiçbir alan kaydı bırakmaz; kayıt tek transaction'dır.

## Tarayıcı ve insan doğrulaması

GÖREV-09 Adım 1b'den beri (kullanıcı kararı) Playwright'in otomasyonla açtığı test tarayıcısı kullanılmaz. `studio/sources/browser_verification.py` bilgisayarda kurulu gerçek Chrome'u (yoksa Edge) normal bir uygulama gibi başlatır: bütün siteler için tek kalıcı profil (`work/tarayici-profili/30a-studio`, repoya girmez; `STUDIO_BROWSER_PROFILE` ile değiştirilebilir) ve yalnız 127.0.0.1'e açık uzaktan hata ayıklama portu. Kod tarayıcıya CDP üzerinden bağlanır (Playwright `connect_over_cdp`); otomasyon bayrağı ve Playwright'in açılış ayarları yoktur, kullanıcı aracısı, dil, saat dilimi ve pencere boyutu tarayıcının kendi değerleridir. Tarayıcı açıksa yeniden bağlanılır; profil ikinci kez açılmaz ve çekimler arasında korunur.

Korumalı bir şirketin (yapılandırmada `protected`) ve bir kez doğrulama sayfası göstermiş bir alan adının (`browser_hosts` tablosu: "tarayıcıyla okunur") bütün istekleri bu tarayıcıda, şirketin ilan sayfasını açan sekmenin içinden (sayfanın kendi `fetch`'iyle) yapılır; ayrı HTTP istemcisiyle gidilmez. Doğrulama sayfası 20 sn içinde kendiliğinden geçmezse şirket **sona bırakılır**, diğerleri devam eder; en sonda bekleyen siteler ayrı sekmelerde açılır, iş "Kullanıcı doğrulaması bekleniyor · <siteler>" olarak bunları tek seferde listeler ve **15 dakika** bekler; doğrulanan şirketler okunur, doğrulanmayanlar `verification_timeout` olarak kaydedilir. Uzun bir çekimden önce bu siteler `python -m studio.sources.browser_verification isinma` ile sekmelerde açılır ve kullanıcıya tek liste halinde bildirilir. Doğrulamayı kullanıcı yapar; kod hiçbir şeye tıklamaz, tarayıcıyı gizleyen ya da taklit eden ayar, CAPTCHA çözme servisi, proxy kullanılmaz. Engel sayfası gelirse şirket hemen durur. Playwright isteğe bağlı bağımlılıktır (`pip install .[browser]`).

## Saklanan alanlar (şema 11, v12 eklemeleriyle)

- `destination_agency_sites`: destinasyon, alan adı, şirket adı, uyarlayıcı, etkin, sıra.
- `agency_rate_snapshots`: çekim, girdi konaklama çekimi, sorgu günü, istek ve ilan sayısı.
- `agency_rate_windows`: pencere, giriş/çıkış, gece, `queried` / `skipped_past`.
- `agency_rate_companies`: şirket bazında sonuç (durum, ilan, eşlenen, sorgu, fiyatlı sorgu, istek, doğrulama, mesaj).
- `agency_rate_listings`: Book>Direct ilanı (kimlik, ad, yatak odası, mahalleler), Book>Direct bağlantısı, açılan son adres, HTTP durumu, sayfa durumu, platform kimliği, mesaj.
- `agency_rate_quotes` (ilan × pencere): durum (`priced`, `unavailable`, `restricted`, `no_price`, `error`); müsait (sitenin söylediği: 1/0, bilinmiyorsa NULL); gecelik fiyatlar (site veriyorsa); kira; temizlik ücreti (adında "clean" geçen ücretler); diğer ücretler; ücret kalemleri (adlarıyla); vergiler ve vergi kalemleri; genel toplam; toplamın ücret ve vergiyi içerdiği (bizim kontrolümüz: kalemlerin toplamı sitenin toplamını $1 içinde tutuyorsa 1, tutmuyorsa NULL); toplama dahil edilmeyen isteğe bağlı kalemler (ör. seçilmemiş sigorta; ResCMS'te isteğe bağlı satır yalnız sitenin ara toplamı onu içeriyorsa ücret sayılır); para birimi; en az gece ve giriş günleri (ISO hafta günü; kaynağı `sayfa` ya da `yanıt`); sitenin mesajı; sorgu zamanı; sorgulanan URL; ham yanıtların SHA-256 listesi.
- `job_waits`: çalışan bir işin kullanıcı doğrulaması beklediği site (yalnız iş sürerken gösterilir).
- v12: `destination_agency_sites`'a takma alan adları, korumalı bayrağı, misafir kuralı, şirket ilan listesi kaynağı, kendi envanteri mahallesi ve şehir adı; `agency_rate_listings`'e `link_status`, `match_method`, `match_note`; `agency_rate_quotes`'a `adults`, `children`; `agency_rate_companies`'e korumalı, misafir kuralı, şirket listesi sayısı ve ham SHA-256'ları, kendi envanteri sayıları, yöntem dağılımı. Yeni tablolar: `agency_rate_own_listings`, `agency_rate_own_quotes` (şirketin kendi envanteri ve fiyatları), `agency_rate_published` (yayımlanmış sezon kirası; toplamlardan ayrı), `browser_hosts` (tarayıcıyla okunan alan adları; ilk ve son görülme, neden).
- Ham yanıtlar `data/raw/<çekim>/responses/*.gz`; `manifest.json` her yanıtın şirketini, aktarımı (`http`/`browser`), yöntemini, istek gövdesini, adreslerini, HTTP durumunu ve SHA-256'sını tutar.

Site bir alanı vermiyorsa o alan NULL kalır; sıfır yazılmaz. "Müsait değil" ile "kurala takıldı" ayrıdır: bir sitenin "4 gece en az" demesi müsaitlik bilgisi değildir (`available` NULL).

## Okuma anında hesaplanan özet

Hiçbiri saklanmaz (`agency_rates.summarize`). Mahalle × pencere için: mahallenin Book>Direct ilan sayısı, yapılandırılmış şirketlere bağlı ilan sayısı, sorgulanan ilan sayısı, fiyatı alınabilen ilan sayısı ve payı, müsaitliği bilinenler içinde müsait olanların payı, 7 gecelik genel toplamın ortancası ve çeyrekler aralığı, kira ÷ gece ile gecelik ortalamanın ortancası ve çeyrekleri (bizim hesabımız; ücret ve vergi hariç), oda sayısına göre (1–2 [stüdyo dahil], 3, 4, 5+) genel toplam ortancası. Bir ilan birden fazla mahallenin filtresinde göründüyse her birinde sayılır. Ayrıca kapsama (sayfa durumlarına göre ilan sayıları, fiyatlı ilan ve mahalle sayısı) ve şirket bazında sonuç. Etiket: "Kiralama şirketlerinin kendi sitelerinde <tarih> tarihinde sorgulanan fiyatlar; toplam fiyat sitenin gösterdiği zorunlu ücretleri ve vergileri içerir (isteğe bağlı sigorta gibi kalemler hariç)"; toplamı kalemleriyle doğrulanamayan fiyat varsa etiket bunu sayısıyla söyler.

## Arayüz

Konaklama sekmesinin altında "Kiralama şirketlerinin kendi siteleri · Konaklama fiyatları" bölümü: toplama düğmesi, sürüm seçimi ve ham manifest; kapsama göstergeleri; mahalle × pencere fiyat tablosu (sorgulanan, fiyatlı, müsait payı, toplam ortancası ve çeyrekleri, kira gecelik ortancası); oda sayısına göre ortancalar; şirket bazında sonuç ve eşlenemeyen ilanların nedenleri. Bir mahalleye tıklayınca ilanlar, ilana tıklayınca pencere pencere sitenin fiyat dökümü (kira, ücretler adlarıyla, vergiler, toplam, toplama dahil edilmeyen kalemler, kural, sitenin mesajı, sorgu zamanı) ve şirketin ilan sayfasına bağlantı. İşler panelinde doğrulama bekleyen iş "Kullanıcı doğrulaması bekleniyor · <site>" etiketiyle görünür. v0.12.0: hücrede eşleme yöntemi (adres/konum varsa), şirketin kendi envanteri ve yayımlanmış kira ayrı satırlarda; mahallenin ilan listesinin altında kendi envanteri tablosu; şirket tablosunda yöntem dağılımı, misafir kuralı ve korumalı işareti.

## Kapsama

Gerçek çekimin ayrıntılı kapsaması (sayfa durumu ve eşleme yöntemine göre ilan sayıları, şirket bazında sonuç, mahalle × pencere fiyatlı ilan sayıları ve GÖREV-08 ile karşılaştırma) `docs/gorevler/GOREV-09/RAPOR.md` ve `konaklama-fiyat-ozet.csv` içindedir. Özet: 2.389 ilanın 1.127'i şirket sitesinde bulundu (bağlantı 1119, adres 1, konum 7); 1.066 ilana fiyat; fiyatlı mahalle 12/13; kendi envanteri 73 ev (69 fiyatlı); yayımlanmış kira 21 ilan.

Gerçek çekimde Oversee'nin (oversee.us) VRP liste servisi JSON yerine HTML sonuç kartları döndürdüğü için şirket listesi okunamadı ve şirket "failed" diye kaydedildi; bağlantıyla eşlenen 174 ilanın fiyatları kayıtlı, bağlantısı çalışmayan 11 ilan için adres eşlemesi bu çekimde yapılamadı. Kartlar artık okunuyor (`data-vrp-*` nitelikleri; sokak satırından şehir ve eyalet ayıklanıyor); ham yanıt üzerinde yapılan kontrolde bu 11 ilandan 4'ü sonraki çekimde adresle eşlenecek.

## Geçici denemede düzeltilenler (8 Ekim 2026)

1. Sıradan CAPTCHA form kutusu taşıyan 403 "Access denied" sayfası doğrulama sanılıyordu (iki şirkette görünür pencere açıldı); artık yalnız ara sayfa işaretleri sayılıyor ve 403'ten sonra sitenin ana sayfasına bakılıyor.
2. Panhandle Getaways'in Track fiyat servisi, sayfa takviminde dolu görünen haftalara da fiyat veriyordu; Track uyarlayıcısı önce takvime bakıyor.
3. ResCMS'te bazı sitelerin isteğe bağlı sigorta satırı "seçilmedi" işaretsizdi ve toplama girmiyordu; ara toplama göre ayrılıyor.
4. 200 kodlu "Pages Not Found" sayfaları `not_found` sayılıyor.

## Fiyatı okunamayan şirketler (GÖREV-20, 16 Kasım 2026)

İnceleme kuralı: şirket başına en çok 10 istek, aynı sitede iki istek arası en az 8 sn; önce doğrudan istek, engel varsa programın kendi tarayıcısı; engeli aşmak için başka yol aranmadı. Ham yanıtlar `work/gorev-20/ham/` altında (repoya girmez).

| Şirket (alan adı) | Book>Direct ilanı | Altyapı | Sonuç |
|---|---|---|---|
| 360 Blue (360blue.com) | 256 | okunamadı (Book>Direct kaydında Natural Retreats) | **Okunamadı.** Doğrudan istek ve programın kendi tarayıcısı aynı Cloudflare engel sayfasını aldı ("Sorry, you have been blocked"); bu bir doğrulama değil, kimsenin geçemeyeceği bir rettir. 2 istek yapıldı. |
| Cottage Rental Agency (rentals.cottagerentalagency.com, cottagerentalagency.com) | 82 + 10 | okunamadı | **Okunamadı.** Kiralama alan adının DNS kaydı yok; ana alan adı sandestin.com'daki kaldırılmış bir sayfaya (403 "Access denied") yönleniyor. Şirketin güncel kiralama sitesi bulunamadı. 3 istek. |
| RealJoy (realjoy.com) | 61 | ICND rezervasyon motoru (`/bookingEngine/`), arkada Track | **Tamamlanamadı.** Site Cloudflare doğrulaması istiyor; programın kendi tarayıcısında doğrulama iki kez 15 dakika beklendi, geçmedi. Kullanıcının Chrome'undaki eklenti siteyi okuyabiliyor (11 Kasım 2026 ham kaydı): ilan listesi sayfası her ev için sokak adresi, 8 ondalıklı koordinat, yatak ve birim kodu veriyor (adres eşlemesine uygun), ilan sayfaları `/beach-rentals/<ad>` biçiminde. Fiyat isteği ilan sayfası görülmeden incelenemedi; eklenti deneme listesine bir ilan sayfası eklendi. Okuyucu sonraki görevde, o sayfanın ham kopyasından yazılabilir. |
| 30A Beach Girls (30a-beachgirls.com) | 48 | AvantStay (şirketin kendi alan adında, Next.js) | **Doğrudan okunuyor ama eşlenemiyor.** Book>Direct bağlantıları 404. Sitenin ilan verisinde sokak adresi yok, koordinat 3 ondalığa (yaklaşık 100 m) yuvarlanmış: adres ve konum (15 m) kuralları uygulanamıyor; ad tek başına ölçüt değil. Eşleme kuralı değiştirilmediği için bırakıldı. 6 istek. |
| Vacasa (vacasa.com; wyndhamvacationrentals.com bağlantıları da buraya gidiyor) | 21 (+14) | Vacasa | **Okunamadı (bölge engeli).** CloudFront: "configured to block access from your country". Sayfa görülemediği için okuyucu yazılamadı. Program bu cümleyi artık bölge engeli olarak tanıyor (`page_kinds`). 1 istek. |
| Outdoor Shower (outdoorshower30a.com) | 21 | okunamadı (Book>Direct kaydında LiveRez) | **Okunamadı.** Site yanıt vermiyor (https ve http bağlantısı zaman aşımı). 2 deneme. |

**"Sitesi engellediği için okunamayan 51 ilan":** hepsi yapılandırılmış ResCMS (Drupal 7) şirketlerinde: Benchmark Management 33, Sanders Beach Rentals 7, Grayton Coast Rentals 6, My Vacation Haven 3, 30A Cottages 2. Bunlar site engeli değil: sitenin ana sayfası açılıyor, yalnız o ilan sayfası 403 "Access denied / You are not authorized to access this page" veriyor (Drupal'ın yayından kaldırılmış sayfaya verdiği yanıt). 16 Kasım 2026'da bakılan üç örnekten biri artık 404 (silinmiş), biri başka adrese yönleniyor, biri hâlâ 403. Yani bu ilanlar şirketin sitesinde yayından kalkmış ama Book>Direct'te duruyor; okunacak fiyat yok. Kanıt paketindeki boşluk satırı buna göre düzeltildi.

**Çekim süresi:** yeni şirket eklenmediği için aylık çekim aynı kaldı (son çekim 21.129 istek, 7 sa 42 dk). "Güncelleme zamanı gelenler" tablosundaki tahmin artık son çekimin okumadığı etkin şirketleri de sayar: şirketin Book>Direct ilan sayısı × (1 sayfa + pencere sayısı × 2 istek) × (şirketin istek aralığı + 1 sn); korumalı sitede aralık 6 sn (`agency_rates.new_site_estimate`; bizim tahminimiz). RealJoy eklenirse: 61 ilan × 25 = 1.525 istek, yaklaşık 3 saat.

## Bölge engelli iki şirket, bağlantıdaki numara kuralı ve şirketin kendi sitesindeki evler (GÖREV-22, 17 Kasım 2026, şema 22, v0.23.0)

GÖREV-20'de okunamayan altı şirketten ikisinin engeli **bölge engeli** çıktı (ölçüm: `docs/M18-ABD-PROXY-BOLGE-ENGELI.md`); bunlar
kullanıcının ABD proxy'si üzerinden incelendi (şirket başına 10 sayfa, iki istek arası en az 8 sn) ve okuyucuları yazıldı. Üç yeni
şirket satırı migration v22 ile yapılandırmaya girer (`AGENCY_SITES_V22`, `AGENCY_SITE_OPTIONS_V22`); toplam 27 şirket.

| Şirket | Uyarlayıcı | Site ne veriyor | Eşleme |
|---|---|---|---|
| 360 Blue (360blue.com; bölge engelli) | `nrbe` — Natural Retreats'in rezervasyon motoru (Adobe Experience Manager) | `GET /api/nrbe/units.json` (30A koleksiyonunun bütün evleri tek istekte: ad, koordinat, oda, banyo, kapasite), `availability-calendar.json` (altı aylık müsaitlik), `reservation-quotes.json?unitId&arrivalDate&departureDate&adults&children` (`subTotal`, `taxes`, `total`) | Adres kuralı. Listede adres alanı yok; evin sokak adresi adının sonundan alınır (`name_address`: `Seaside "Sea ya real soon" 73 Odessa Street` → `73 Odessa Street`). Yalnız adres alınır, ad karşılaştırılmaz |
| Vacasa (vacasa.com; bölge engelli; wyndhamvacationrentals.com bağlantıları buraya yönleniyor) | `vacasa` | Arama sayfası (`/search?place=/usa/Highway-30A/`): her ev için koordinat, oda, banyo ve evin **eski ilan numarası** (`migrated_from_unit_id`); `GET /guest-com-api/get-unit-price-quote` (kira, ücret kalemleri, vergi kalemleri, toplam; `Error` yanıtı sebebi söyler) | Bağlantıdaki numara kuralı (aşağıda); olmazsa konum kuralı |
| 30A Beach Girls (30a-beachgirls.com) | `avantstay` | Alfabetik ev listesi ve her evin sayfası (`__NEXT_DATA__`): şehir, sitenin bölge adı, 3 ondalığa yuvarlanmış koordinat; sokak adresi yok. GÖREV-23: AvantStay'in servisindeki takvim (gün gün gecelik fiyat, en az konaklama, durum) | Eşleme yok: şirketin kendi envanteri (aşağıda) |

**Fiyat kalemleri sitenin gösterdiği gibidir.** 360 Blue ücret kalemi göstermez: `rent` sitenin ara toplamıdır (`subTotal`), vergi ve
toplam sitenin kendi sayılarıdır. Vacasa'da temizlik ücreti ve vergi kalemleri ayrı gelir; tesiste ödenecek ücretler (varsa) toplama
katılmadan "hariç" kalemlerde durur. **Müsait olmayan pencere ayrı tutulur:** 360 Blue satamadığı tarih için sebep söylemeyen bir hata
döndürdüğünden, takvimin dolu gösterdiği pencere takvimden "müsait değil" yazılır ve fiyat sorulmaz; takvim boş gösterdiği halde hata
gelirse satır "fiyat yok"tur (müsaitlik bilinmiyor), sitenin sözüyle. Vacasa'da `booked` → müsait değil, `min-stay-not-met` → kural.

**Ölü bağlantılar (`inventory.dead_links`).** 360 Blue'nun Book>Direct'teki bağlantıları sitenin eski adresleridir (301, sonra sitenin
kendi 404 sayfası); 30A Beach Girls'ünkiler 404. Bunlar yapılandırmada işaretlidir: bağlantı sorulmaz (ilan başına iki boş istek ve
proxy hızında 8'er saniye harcanmaz), ilan doğrudan şirketin listesinden eşlenir; ilanın kaydında "Book>Direct bağlantısı sorulmadı"
yazar.

**Bağlantıdaki numara kuralı (`link_unit`; eşleme yöntemi "bağlantı").** Book>Direct bağlantısı (ya da yönlendiği adreslerden biri)
bir ilan numarası taşıyorsa ve şirketin kendi listesi bu numarayı **tam bir ev** için — şimdiki ya da eski numarası olarak — veriyorsa
ilan o eve bağlanır. Bu ad benzerliği değildir: numarayı bağlantı, karşılığını şirketin kendi kaydı söyler. Numara listede yoksa ya da
birden çok evde varsa kural uygulanmaz ve adres/konum kuralına geçilir. `SiteSession` artık bir yanıta giderken sorulan bütün adresleri
tutar (`Reply.hops`): Wyndham bağlantısı numarayı ancak yönlendiği `unit.php?UnitID=…` adresinde gösterir.

**Şirketin kendi sitesindeki evler — mahalleler arası kendi envanter (`inventory.own`).** Sitesi sokak adresi vermeyen ve koordinatı
yuvarlayan bir şirketin evleri Book>Direct ilanlarına bağlanamaz (yöneticinin kararı: ad benzerliğiyle eşleme yapılmaz). Bu evler,
tek topluluğun resmî programındaki "kendi envanter" yoluyla (GÖREV-09, Alys Beach) aynı tablolara, ama mahalleler arası yazılır:

- Ev, site onu yapılandırmadaki bölgesine koyuyorsa alınır (`site_region`; 30A Beach Girls'te "Emerald Coast - 30A"); başka bölgedeki
  ev (Panama City Beach) alınmaz ve sayısı şirket satırında yazar.
- **Mahalle yalnız sitenin ev için söylediği yer adından gelir** (`regions`: sitenin yer adı → mahalle). Koordinattan ya da adresten
  mahalle çıkarılmaz. Yer adı bir mahalle adı değilse ev **mahallesiz** kalır (`region_id` boş; şema 22 buna izin verir): hiçbir
  mahallenin ortancasına girmez, özetlerde "mahallesi belirtilmemiş" diye ayrı sayılır.
- 30A Beach Girls sitesinde "Santa Rosa Beach" ve "Inlet Beach" bilerek eşlenmedi: bu sitede posta adresindeki şehirdir, mahalle
  değil (site Prominence'ta diye anlattığı bir evin şehrine "Inlet Beach" yazıyor). Böyle evler mahallesiz kalır.
- Bir ev Book>Direct ilanına bağlanmışsa (aynı şirket sayfası, aynı adres, adres kuralı ya da bağlantıdaki numara) kendi envantere
  girmez; iki kez sayılmaz.
- Kanıt paketinde ve ekranda kaynağıyla ayrı durur: "şirketin kendi sitesindeki evler; Book>Direct ilanlarına bağlanmadı".

**30A Beach Girls'te GÖREV-22'de fiyat sorulmuyordu (`inventory.own.quotes: false`);** sitenin fiyatı kendi alan adından değil,
AvantStay'in ayrı servisinden geliyor ve o görevde bu servise deneme isteği yapılamamıştı. GÖREV-23'te yapıldı; sonuç bir sonraki
bölümde.

## GÖREV-23: AvantStay'in takvimi, Vacasa'nın tam listesi, LocalVR

### 30A Beach Girls — yalnız kira, sitenin takviminden (sepet sorgusu kullanılmaz)

Servis: `POST https://arriere.prod.avantstay.com/public/graphql`, başlık `X-Distribution-Channel: BEACH_GIRLS` (sitenin kendi betiğinin
gönderdiği kanal adı; yapılandırmada `inventory.channel`). Evin sayfası bu servise iki şey sorar:

| Sorgu | Ne verir | Kullanılıyor mu |
|---|---|---|
| `home(homeId){calendar(from,to){date minStay rate season status restrictions{checkInAllowed checkOutAllowed}}}` (sayfanın takvimi) | Gün gün gecelik fiyat (**dolar**, ör. `175.0`), en az konaklama ve durum: `VACANT`, `OCCUPIED`, `CHECK_IN`, `CHECK_OUT`, `CHECK_OUT_AND_CHECK_IN` | **Evet** |
| `cartPrice(bookingRequest:{…}, cartId){creditCard{subtotal taxesAndFees{…} totalOfStay …} cartId}` (sayfanın fiyat kutusu) | Ücretler, vergiler ve toplam; yanında bir **sepet numarası** | **Hayır** |

**Sepet konusu (17 Kasım 2026, sitenin kendi betiğinden).** Fiyat kutusu `cartPrice`'ı ilk kez sepet numarası olmadan sorar, yanıtta
dönen `cartId`'yi saklar (`cartIdWithoutInsurance`) ve sonraki her soruda geri gönderir; aynı numara ödeme adımlarının (`initializeCartPayment`,
`setCartPayment`, `confirmCartPayment`) girdisidir. Yani bu soru serviste bir sepet kaydı açar. Kural gereği rezervasyon ya da sepet
akışına girilmez: `cartPrice` **hiç gönderilmedi**, okuyucuda da yoktur (test bunu sorgu metninde denetler). Sayfanın sepetsiz bir fiyat
dökümü sorgusu yoktur; servis tür tanımı sorgusuna (introspection) yanıt vermiyor (HTTP 422).

**Okuyucu (`AvantStay.quote`).** Ev başına **bir** takvim isteği (bu ayın ilk gününden 18 ay; sitenin betiğinin bir kerede sorduğu
aralık) evin bütün pencerelerine yeter. Bir haftanın tutulabilir olup olmadığı sitenin kendi kuralıyla (sayfanın betiği) belirlenir:

- giriş günü `CHECK_IN`, `CHECK_OUT_AND_CHECK_IN` ya da `OCCUPIED` değilse (`CHECK_OUT` günü giriş yapılabilir), aradaki geceler `VACANT`
  ise ve çıkış günü `CHECK_OUT`, `CHECK_OUT_AND_CHECK_IN` ya da `OCCUPIED` değilse (`CHECK_IN` günü çıkış yapılabilir) hafta boştur;
  değilse **müsait değil** (takvimden);
- giriş günü girişe ya da çıkış günü çıkışa kapalıysa (`restrictions`), ya da giriş gününün en az konaklaması pencereden uzunsa
  **kısıtlı** (en az gece sayısı saklanır);
- hafta boşsa **kira = takvimin o gecelere yazdığı gecelik fiyatların toplamı**. Bu toplam **bizim toplamımızdır** ve öyle etiketlenir;
  gecelik fiyatlar sitenin kendi sayılarıdır ve satırda saklanır.

Temizlik ücreti, öbür ücretler, vergi ve **toplam boş kalır** (site bunları sepetsiz söylemiyor). Bu yüzden bu satırlar hiçbir toplam
fiyat ortancasına girmez: mahalle hücrelerinde "fiyatlı" sayılmaz, yalnız müsaitlik payına girer. Şirket tablosunda ve kanıt paketinde
ayrı bir ölçü olarak görünür: **"7 gecelik kira ortancası; temizlik ücreti, öbür ücretler ve vergi HARİÇ"** (`own_companies[].windows[]`
içinde `rent_count`, `rent_median`). Misafir sayısı takvim sorusunda yoktur; satırlarda boş kalır. Para birimi: servis sayı verir, site
"$" ile gösterir; "USD" yazılır.

### Vacasa — tam liste

`GET /search?place=/usa/Highway-30A/&page_limit=300` (ABD proxy'si üzerinden, 17 Kasım 2026): **300 evin 300'ü tek yanıtta** (4,4 MB;
`total_units: 300`, `page_count: 1`). Okuyucu zaten ilk sayfadan sonra ikinci istekte `page_limit=<toplam>` soruyordu; kod değişmedi,
sayfalama isteği gerekmedi. "Liste eksik" kuralı aynen duruyor: yanıt duyurulan sayıdan az ev verirse şirket o çekimde hatayla kaydedilir,
hiçbir ilan tahminle bağlanmaz. Çevrimdışı karşılaştırma (son Book>Direct çekimi ile bu liste): bağlantısında ilan numarası olan 11
Vacasa ilanından **1'i** listedeki bir evin eski numarasına denk geliyor; 14 Wyndham bağlantısının yönlendiği numara ancak çekimde
görülür; 10 bağlantı bir evin değil bir yerleşkenin sayfası.

### Outdoor Shower / LocalVR — okunacak site yok

`golocalvr.com` ve rezervasyon sitesi `stay.golocalvr.com` doğrudan incelendi (8 sayfa, 17 Kasım 2026). Rezervasyon sitesi Guesty
üzerinde kendi ön yüzü (Next.js); ev listesi `GET /api/properties?fetchAll=1`, fiyat `POST /api/listing-quotes`. Listede **548 ev** var:
Colorado 254, California 137, Utah 96, Montana 51, Nevada 10. **Florida'da ve 30A'da tek bir ev yok;** sitenin 13 pazarı arasında 30A
yok, "LocalVR Expands in 30A Florida with Acquisition of Outdoor Shower" duyurusunun adresi de artık blog ana sayfasına yönleniyor.
Bu yüzden Outdoor Shower'ın 21 Book>Direct ilanının bağlanacağı bir liste yok: uyarlayıcı yazılmadı, yapılandırmaya satır eklenmedi,
ilanlar fiyatsız kalır (`thirty_a_agency_unread.csv`'de gözden geçirilmiş nedeniyle). Bağlantıları (outdoorshower30a.com) yapılandırılmış
bir şirketin alan adı olmadığı için çekimde zaten sorulmaz.

**Okunamayan şirketlerin son durumu** (`thirty_a_agency_unread.csv`, 17 Kasım 2026): Cottage Rental Agency — site yok (DNS kaydı yok;
ana alan adı sandestin.com'daki kaldırılmış sayfaya yönleniyor, proxy'den de aynı); Outdoor Shower — alan adı askıda; devralan LocalVR'nin
sitesinde 30A'da ev yok (GÖREV-23), okunacak site yok; RealJoy — Cloudflare doğrulaması (bot koruması; proxy kullanılmaz), okuma yolu
eklenti.

**Çekim tahmini (`new_site_estimate`).** Yeni şirket için: ilan × (bağlantıyı açma istekleri — ölü bağlantıda 0 — + ilan başına ek
istek + pencere × fiyat isteği), bölge engelli şirkette istek aralığı 8 sn (+1 sn yanıt). Uyarlayıcı ipuçları: `nrbe` ilan başına 3
takvim isteği ve pencere başına 1; `vacasa` bağlantı başına 3 (iki yönlendirme ve yer sayfası) ve pencere başına 1. Kendi envanterde
beklenen ev sayısı × 1 sayfa (`expected_homes`). Bu bir üst sınırdır: eşleşmeyen ilan fiyat sormaz, dolu pencere sorulmaz. GÖREV-23:
`avantstay` ev başına 1 takvim isteği ve pencere başına 0 (145 ev × 2 = 290 istek); şirketin 48 Book>Direct bağlantısından hiçbirinin
bağlanması beklenmediği için (`expected_matches: 0`) onlar için takvim sayılmaz.

## Aylık pencere kuralı, mevsim grupları ve aynı hafta karşılaştırması (GÖREV-10, şema 13)

**Kural (bizim varsayımımız, kaynak gerçeği değil):** çekim ayından sonraki **12 ayın** her biri için ayın **15'ini içeren Cumartesi–Cumartesi haftası** (7 gece): hafta, 15'inden önceki ya da 15'i olan Cumartesi başlar, dolayısıyla her zaman ayın 9'u ile 22'si arasındadır. Başlangıcı çekim tarihine **21 günden yakın** olan pencere atlanır ve yerine 13. ay eklenir; her çekim aynı sayıda pencere sorar. Pencere anahtarı ayı adlandırır (`ay-2027-07`), etiket "Temmuz 2027 · 10–17 Temmuz". Kural destinasyon yapılandırmasındadır (`destination_lodging_sources.window_rule`, JSON: `kind, months, anchor_day, weekday, nights, min_lead_days`; 30A: `thirty_a.py` → `LODGING_WINDOW_RULE`); hesap `studio/sources/windows.py` içinde generic'tir. Book>Direct konaklama aramaları ve kiralama şirketi fiyatları aynı kuralı kullanır; her çekim kullandığı kuralı kaydına yazar (`metadata.window_rule`). Kural tanımlıyken eski sabit pencereler (`destination_lodging_windows`) kapalı kalır.

**Sorgudan pencereye gün:** her pencerenin başlığında sorgu tarihinden pencerenin ilk gecesine kaç gün olduğu yazar ("sorgudan 274 gün sonra"); fiyatların ne kadar önceden sorulduğu böylece görünür.

**Mevsim grupları (bizim gruplamamız):** Aralık–Şubat kış, Mart–Mayıs ilkbahar, Haziran–Ağustos yaz, Eylül–Kasım sonbahar. Mahalle başına mevsimdeki her fiyatlı ilan-pencere çifti bir kez sayılır ve ortancası verilir (Book>Direct'te gecelik fiyat, kiralama şirketlerinde 7 gecelik toplam); pencere ve fiyat sayısı yanında yazar. Okuma anında hesaplanır (`studio/sources/price_history.py`).

**Aynı hafta, iki sorgu:** bir çekim, aynı giriş ve çıkış tarihli en az bir pencere sormuş en son önceki başarılı çekimle karşılaştırılır (pencere anahtarları farklı olabilir; tarihler belirler). Bir ilan yalnız **iki çekimde de fiyatlıysa** sayılır; değişim (sonraki − önceki) ÷ önceki; mahalle × pencere için ortanca değişim, ortanca tutar farkı ve **eşleşen ilan sayısı** gösterilir. Etiket: "aynı evlerin aynı hafta için <tarih1> ve <tarih2> tarihlerinde sorgulanan fiyatları; bizim hesabımız". Temel: Book>Direct'te gecelik fiyat (liste, canlı ya da takvim; öncelik M10'daki gibi), kiralama şirketlerinde sitenin 7 gecelik toplamı. İlk aylık çekimde yalnız eski sabit pencerelerden tarihi aylık haftayla aynı olanlar karşılaştırılır (30A: Bahar tatili 2027 = 13–20 Mart, Yaz 2027 = 10–17 Temmuz; iki sorgu arasında birkaç gün olduğundan bu karşılaştırma fiyatların değişimi için değil, yöntemin sınaması için anlamlıdır); bütün aylar ikinci aylık çekimle karşılaştırılır.

**Güncelleme zamanı:** Book>Direct ve kiralama şirketi fiyatları için önerilen aralık 1 aydır; ana ekrandaki "Güncelleme zamanı gelenler" bölümü ve "Zamanı gelenleri başlat" düğmesi (CALISMA_MANTIGI.md §9.11). Pencere kuralı son çekimden sonra değiştiyse (sabit pencerelerden aylık kurala geçiş dahil) toplayıcı aralık dolmasa da "zamanı geldi" görünür, çünkü eski çekim aylık seriye ait değildir.

## Sınırlar

- Yalnız yapılandırılmış şirketler sorulur; 360blue (engel sayfası), realjoy (doğrulama tamamlanmadı), oldseagrove, Cottage Rental Agency, 30A Beach Girls, Beach Escapes, Vrbo/Airbnb/Vacasa kapsam dışı. Fiyat örneği bu yüzden şirketlere ve mahallelere göre dengesizdir (WaterColor ve WaterSound ilanlarının çoğu 360blue'nun); özet "fiyatı alınabilen ilanlar" içindir, mahallenin tamamını temsil etmez.
- Fiyat sorgu günündeki gösterimdir; site sonradan değiştirebilir. Promosyon kodu girilmez; sitenin kendiliğinden uyguladığı promosyon (Southern) ayrı kalemdir. Telefonla verilen fiyat yoktur. Misafir sayısı her fiyatta saklanır (30A'da 2 yetişkin).
- Book>Direct bağlantısı eskiyse ve şirket listesi yapılandırılmamışsa ilan eşlenmez; adla başka bir ilana bağlanmaz. Adres/konum eşlemesi şirket listesindeki alanlara dayanır; doğrulaması `docs/gorevler/GOREV-09/eslesme-dogrulama.csv`.
- Oda sayısı Book>Direct ilanından; şirket sitesindeki oda sayısıyla karşılaştırılmadı.
- Para birimi sitede "$" ya da alan olarak "USD"; dönüştürme yapılmaz.

## Video dili

Kullanılabilir: "<Mahalle>'de kiralama şirketlerinin kendi sitelerinde, <tarih> tarihinde <pencere> haftası için sorduğumuz <n> evin, sitenin gösterdiği vergiler ve ücretler dahil haftalık toplamının ortancası yaklaşık $X'ti." Ortancanın yanında kaç ilandan hesaplandığı ve aralık (çeyrekler) söylenir. İki aylık çekimden sonra: "aynı <n> ev için <hafta> haftasının fiyatı <tarih1> ile <tarih2> arasında ortanca olarak %Y değişti (bizim hesabımız)"; eşleşen ev sayısı söylenir. **Kapsanan şirketler (GÖREV-20):** fiyat ortancaları yalnız fiyatı okunan şirketlerin ilanlarından gelir; fiyatı okunamayan şirketler videoda adlarıyla anılmaz, "fiyatını okuyamadığımız şirketler" denir ve onların yoğun olduğu mahallede "mahallenin fiyatı" denmez.

Kullanılmaz: "<Mahalle>'de bir hafta $X tutar" (genelleme), "fiyatlar şu kadar arttı" (eşleşmemiş evlerden ya da tek tarihten), ilan sayısı az olan hücrelerden mahalle karşılaştırması, 360blue'nun yoğun olduğu WaterColor/WaterSound için "mahallenin fiyatı". **Küçük örnek (GÖREV-11, bizim eşiğimiz):** bir pencerede 20'den az fiyatlı ilanı olan hücre küçük örnektir; kanıt paketi bu hücrelerde "küçük örnek; mahalle karşılaştırmasında kullanılmaz" yazar ve pencere başına ortanca fiyatlı ilan sayısı 20'nin altında kalan mahalleyi bilinen boşluklara ekler (ör. Gulf Place).

## Testler (GÖREV-23)

`tests/test_gorev23.py`, 17 Kasım 2026 incelemesinin ham yanıtlarından fixture'larla (`tests/fixtures/gorev23/`): `avantstay` — takvimden
haftalık kira (toplam, ücret ve vergi boş), sorgu metninde `cartPrice` olmaması, dolu hafta, giriş günü başka bir konaklamanın başladığı
gün, girişe ya da çıkışa kapalı gün, en az konaklama, takvimin vermediği gün ve hata yanıtı; çekimde ev başına tek takvim isteği, özetin
ve kanıt paketinin kirayı toplamdan ayrı tutması; `vacasa` — 300 evlik tam listenin ikinci istekte alınması ve bir ev eksik gelince
"liste eksik" hatası; adres kuralı — aynı adla ama başka adresle bağlanmama, başka oda sayısı, 2 km'den uzak koordinat, iki aday;
Outdoor Shower için yapılandırma olmaması ve gözden geçirilmiş neden; şema 22 → 23 geçişi (satır sayıları aynı, elle değiştirilmiş satıra
dokunulmaz); tahmin. `tests/frontend.test.mjs`: şirket tablosunda "HAFTALIK KİRA ORTANCASI" sütunu.

## Testler (GÖREV-22)

`tests/test_gorev22.py`, incelemenin ham kopyalarından kesilmiş fixture'larla (`tests/fixtures/gorev22/`): bölge engeli sınıflandırması
(üç sınıf ve 17 Kasım ölçümünün kayıtları); `nrbe` (sayfa, liste, fiyat, takvimden "müsait değil", sebepsiz hata), `vacasa` (sayfa,
arama listesi, fiyat, retler, eksik liste, bağlantıdaki numara) ve `avantstay` (ev sayfası, liste) uyarlayıcıları; bölge engelli
şirketin proxy'den, listede olmayan alan adının doğrudan gitmesi ve ham kayıttaki `transport`; ölü bağlantının sorulmaması; kendi
envanterde mahallenin yalnız sitenin yer adından gelmesi, mahallesiz evin hiçbir mahalle ortancasına girmemesi, Book>Direct ilanına
bağlanan evin iki kez sayılmaması; kanıt paketindeki satırlar; tahmin; şema 21 → 22 geçişi.

## Testler

`tests/test_agency_rates.py` (MockTransport, canlı ağ yok): her uyarlayıcının sayfa ve fiyat ayrıştırması (ResCMS kuralları JSON ve tek tırnaklı biçimde, Track ücret grupları, Streamline gecelik fiyatlar ve isteğe bağlı kalemler, router), eksik alanların NULL kalması, müsait değil yanıtları, en az gece kuralı (sayfadan ve yanıttan), yalnız bağlantıyla eşleme (404, ana sayfaya yönlenme, başka siteye yönlenme, bağlantısız ve yapılandırılmamış ilan; ad farklı da olsa aynı bağlantı), geçmiş pencerenin sorulmaması, ham yanıt SHA-256'ları, bir şirketin hatasında (reddetme, ulaşılamama, beklenmeyen hata) diğerlerinin devam etmesi, ağ hatasında tek yeniden deneme, doğrulama akışı (bekleme bildirimi, aynı oturumla devam, zaman aşımı ve tarayıcı yokken şirketin atlanması), iş kaydında bekleyen sitenin görünmesi ve temizlenmesi, iptal (çekirdek ve API), atomik geri alma, API özeti ve oda grupları, taze veritabanı yapılandırması ve kısıtları, v10 → v11 migration ve geri alma. `tests/frontend.test.mjs`: fiyat hücreleri, kalem dökümü, şirket tablosu, İşler panelindeki bekleme etiketi.

`tests/test_agency_v2.py` (v2): adres normalleştirme ve 30A yol adları, adres kuralı (tek aday, daire, oda, belirsiz), konum kuralı (15 m, oda/banyo, tek aday, çok daireli bina), adın tek başına eşleşmemesi, JSON-LD'de şirket ofisi adresinin alınmaması, yeni uyarlayıcıların sayfa ve fiyat ayrıştırması, site haritasından adres eşlemesi ve yöntemin saklanması, kendi envanterinde topluluk dışı ve Book>Direct'teki evlerin atlanması, yayımlanmış kiranın ayrı tutulması, misafir sayısının saklanması ve kapasite sınırı, korumalı sitelerin tarayıcıdan 6 sn arayla tek tek okunması ve ilk retle durması, engel sayfasında hiç istek yapılmaması, taze veritabanında v12 yapılandırması, v11 → v12 migration ve geri alma, özette yöntem/kendi envanteri/yayımlanmış kira ayrımı.
