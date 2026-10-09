# M11 — Konaklama fiyatları (kiralama şirketlerinin kendi siteleri)

Tarih: 8 Ekim 2026 · Görevler: GÖREV-08 (`/1`), GÖREV-09 (`/2`) · Dal: `gorev-09-kapsama-restoran` · Uygulama `0.12.0` · Şema `12` · Toplayıcı `agency-lodging-rates/2`

## Durum

`agency-lodging-rates/1` GÖREV-08'de 9 şirketle gerçek veride çalıştı (510 ilana fiyat). GÖREV-09'da `/2`: 24 şirket, 6 yeni uyarlayıcı, adres/konum eşlemesi, şirketin kendi envanteri, yayımlanmış kira, misafir sayısı ve korumalı siteler. 8 Ekim 2026'da geçici klasörde (yeni şirketler ve yeni eşleme yollarıyla sınırlı) ve tam yedekten sonra gerçek veritabanında çalıştırıldı. Gerçek çekim `e54c9dfae72a4e06a0702d2394cd8083`: 10.172 istek, 209 dakika; 1.127 ilan şirket sitesinde bulundu, 1.066 ilana en az bir pencerede fiyat alındı; şirketin kendi envanterinden 73 ev (69 fiyatlı), yayımlanmış kira 21 ilan. Mahalle × pencere özeti: `docs/gorevler/GOREV-09/konaklama-fiyat-ozet.csv`; keşif `docs/gorevler/GOREV-09/AJANS-KESFI-2.md`; ayrıntılar `docs/gorevler/GOREV-09/RAPOR.md`.

## Amaç

Ziyaretçinin yer seçiminde "burada kalmak ne kadar tutar" sorusuna kanıt. Book>Direct fiyatı çok az ilan için veriyor (GÖREV-07: 9.189 arama satırının 12'sinde liste fiyatı; takvimlerin çoğu gizli). Book>Direct ilanlarının çoğu bir kiralama şirketine ait ve ilan kaydındaki `url` alanı şirketin kendi ilan sayfasını gösteriyor; bu şirketlerin siteleri belirli tarihler için kalem kalem fiyat gösteriyor. Bu toplayıcı o fiyatı sitenin kendi herkese açık fiyat/müsaitlik gösteriminden okur.

## Kaynaklar

- Girdi: destinasyonun son başarılı Book>Direct konaklama çekimi (`lodging_listings`: Book>Direct kimliği, ad, `url`, yatak odası; mahalle, ilanın göründüğü konum filtrelerinden).
- Sorgulanan siteler: destinasyon yapılandırmasındaki kiralama şirketleri (`destination_agency_sites`: alan adı, sitede görünen şirket adı, uyarlayıcı, takma alan adları, korumalı bayrağı, misafir kuralı, şirket ilan listesi kaynağı, kendi envanteri mahallesi). 30A için 24 şirket (`studio/destinations/thirty_a.py` → `AGENCY_SITES`, `AGENCY_SITES_V12`, `AGENCY_SITE_OPTIONS`); seçimin gerekçesi ve dışarıda kalan şirketler `docs/gorevler/GOREV-08/AJANS-KESFI.md`, `docs/gorevler/GOREV-09/AJANS-KESFI-2.md` ve `docs/gorevler/GOREV-09/ajanslar.csv`'de.
- Tarih pencereleri: konaklama yapılandırmasındaki pencereler (Cumartesi–Cumartesi, 7 gece; varsayım, kaynak gerçeği değil). Geçmiş pencere sorulmaz ve "geçmiş" diye kaydedilir.
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

## Sınırlar

- Yalnız yapılandırılmış şirketler sorulur; 360blue (engel sayfası), realjoy (doğrulama tamamlanmadı), oldseagrove, Cottage Rental Agency, 30A Beach Girls, Beach Escapes, Vrbo/Airbnb/Vacasa kapsam dışı. Fiyat örneği bu yüzden şirketlere ve mahallelere göre dengesizdir (WaterColor ve WaterSound ilanlarının çoğu 360blue'nun); özet "fiyatı alınabilen ilanlar" içindir, mahallenin tamamını temsil etmez.
- Fiyat sorgu günündeki gösterimdir; site sonradan değiştirebilir. Promosyon kodu girilmez; sitenin kendiliğinden uyguladığı promosyon (Southern) ayrı kalemdir. Telefonla verilen fiyat yoktur. Misafir sayısı her fiyatta saklanır (30A'da 2 yetişkin).
- Book>Direct bağlantısı eskiyse ve şirket listesi yapılandırılmamışsa ilan eşlenmez; adla başka bir ilana bağlanmaz. Adres/konum eşlemesi şirket listesindeki alanlara dayanır; doğrulaması `docs/gorevler/GOREV-09/eslesme-dogrulama.csv`.
- Oda sayısı Book>Direct ilanından; şirket sitesindeki oda sayısıyla karşılaştırılmadı.
- Para birimi sitede "$" ya da alan olarak "USD"; dönüştürme yapılmaz.

## Video dili

Kullanılabilir: "<Mahalle>'de kiralama şirketlerinin kendi sitelerinde, <tarih> tarihinde <pencere> haftası için sorduğumuz <n> evin, sitenin gösterdiği vergiler ve ücretler dahil haftalık toplamının ortancası yaklaşık $X'ti." Ortancanın yanında kaç ilandan hesaplandığı ve aralık (çeyrekler) söylenir. Kullanılmaz: "<Mahalle>'de bir hafta $X tutar" (genelleme), "fiyatlar şu kadar arttı" (tek tarih), ilan sayısı az olan hücrelerden mahalle karşılaştırması, 360blue'nun yoğun olduğu WaterColor/WaterSound için "mahallenin fiyatı".

## Testler

`tests/test_agency_rates.py` (MockTransport, canlı ağ yok): her uyarlayıcının sayfa ve fiyat ayrıştırması (ResCMS kuralları JSON ve tek tırnaklı biçimde, Track ücret grupları, Streamline gecelik fiyatlar ve isteğe bağlı kalemler, router), eksik alanların NULL kalması, müsait değil yanıtları, en az gece kuralı (sayfadan ve yanıttan), yalnız bağlantıyla eşleme (404, ana sayfaya yönlenme, başka siteye yönlenme, bağlantısız ve yapılandırılmamış ilan; ad farklı da olsa aynı bağlantı), geçmiş pencerenin sorulmaması, ham yanıt SHA-256'ları, bir şirketin hatasında (reddetme, ulaşılamama, beklenmeyen hata) diğerlerinin devam etmesi, ağ hatasında tek yeniden deneme, doğrulama akışı (bekleme bildirimi, aynı oturumla devam, zaman aşımı ve tarayıcı yokken şirketin atlanması), iş kaydında bekleyen sitenin görünmesi ve temizlenmesi, iptal (çekirdek ve API), atomik geri alma, API özeti ve oda grupları, taze veritabanı yapılandırması ve kısıtları, v10 → v11 migration ve geri alma. `tests/frontend.test.mjs`: fiyat hücreleri, kalem dökümü, şirket tablosu, İşler panelindeki bekleme etiketi.

`tests/test_agency_v2.py` (v2): adres normalleştirme ve 30A yol adları, adres kuralı (tek aday, daire, oda, belirsiz), konum kuralı (15 m, oda/banyo, tek aday, çok daireli bina), adın tek başına eşleşmemesi, JSON-LD'de şirket ofisi adresinin alınmaması, yeni uyarlayıcıların sayfa ve fiyat ayrıştırması, site haritasından adres eşlemesi ve yöntemin saklanması, kendi envanterinde topluluk dışı ve Book>Direct'teki evlerin atlanması, yayımlanmış kiranın ayrı tutulması, misafir sayısının saklanması ve kapasite sınırı, korumalı sitelerin tarayıcıdan 6 sn arayla tek tek okunması ve ilk retle durması, engel sayfasında hiç istek yapılmaması, taze veritabanında v12 yapılandırması, v11 → v12 migration ve geri alma, özette yöntem/kendi envanteri/yayımlanmış kira ayrımı.
