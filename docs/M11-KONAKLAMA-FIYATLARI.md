# M11 — Konaklama fiyatları (kiralama şirketlerinin kendi siteleri)

Tarih: 8 Ekim 2026 · Görev: GÖREV-08 · Dal: `gorev-08-konaklama-fiyat` · Uygulama `0.11.0` · Şema `11`

## Durum

Toplayıcı, şema, arayüz ve testler hazır; 8 Ekim 2026'da geçici klasörde (üç deneme; ilk iki denemede bulunan hatalar düzeltildi) ve tam yedekten sonra gerçek veritabanında çalıştırıldı. Gerçek çekim `1968245cac594bb88d9bde11ed09b449`: 3.855 istek, 92,5 dakika; 529 ilan şirket sitesinde bulundu, 510 ilana en az bir pencerede fiyat alındı. Mahalle × pencere özeti: `docs/gorevler/GOREV-08/konaklama-fiyat-ozet.csv`; deneme ayrıntıları `docs/gorevler/GOREV-08/RAPOR.md`.

## Amaç

Ziyaretçinin yer seçiminde "burada kalmak ne kadar tutar" sorusuna kanıt. Book>Direct fiyatı çok az ilan için veriyor (GÖREV-07: 9.189 arama satırının 12'sinde liste fiyatı; takvimlerin çoğu gizli). Book>Direct ilanlarının çoğu bir kiralama şirketine ait ve ilan kaydındaki `url` alanı şirketin kendi ilan sayfasını gösteriyor; bu şirketlerin siteleri belirli tarihler için kalem kalem fiyat gösteriyor. Bu toplayıcı o fiyatı sitenin kendi herkese açık fiyat/müsaitlik gösteriminden okur.

## Kaynaklar

- Girdi: destinasyonun son başarılı Book>Direct konaklama çekimi (`lodging_listings`: Book>Direct kimliği, ad, `url`, yatak odası; mahalle, ilanın göründüğü konum filtrelerinden).
- Sorgulanan siteler: destinasyon yapılandırmasındaki kiralama şirketleri (`destination_agency_sites`: alan adı, sitede görünen şirket adı, uyarlayıcı). 30A için 9 şirket (`studio/destinations/thirty_a.py` → `AGENCY_SITES`); seçimin gerekçesi ve dışarıda kalan şirketler `docs/gorevler/GOREV-08/AJANS-KESFI.md` ve `ajanslar.csv`'de.
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

Yeni bir şirket aynı altyapıdaysa yalnız yapılandırmaya bir satır eklenir; yeni bir altyapı için `agency_adapters.py`'ye bir uyarlayıcı (iki yöntem: `parse_page`, `quote`) yazılır.

## Eşleme

Book>Direct ilanı ile şirket sitesindeki ilan **yalnız bağlantıyla** eşlenir: ilanın `url`'si açılır, yönlendirmeler yalnız şirketin alan adı içinde izlenir, uyarlayıcı sayfada kendi platform kimliğini bulursa ilan eşlenmiş sayılır. Ad, adres veya koordinat benzerliğiyle eşleme yapılmaz. Sayfa durumları:

| Durum | Anlamı |
|---|---|
| `matched` | Sayfa açıldı, altyapının ilan kimliği bulundu; fiyat soruldu. |
| `not_found` | Şirket sitesi bu bağlantı için 404/410 ya da 200 kodlu "not found" sayfası döndürdü (eski bağlantı). |
| `no_listing` | Sayfa açıldı ama ilan sayfası değil (ana sayfa, genel liste, betikle yönlenen sayfa). |
| `off_site` | Bağlantı başka bir alan adına yönlendi; o siteye istek yapılmadı. |
| `blocked` | İlan sayfası 401/403/429 döndü (doğrulama sayfası değil). Ardından sitenin ana sayfasına bir kez bakılır: yanıt veriyorsa yalnız o ilan erişime kapalıdır (ResCMS/Drupal sitelerinde yayından kalkmış ilan "Access denied" verir); vermiyorsa ret şirketi durdurma sayacına yazılır. |
| `error` | Siteye ulaşılamadı (bir yeniden denemeden sonra) veya beklenmeyen HTTP durumu. |
| `not_queried` | Şirket durdurulduğu ya da atlandığı için bu ilana sıra gelmedi. |
| `no_adapter` | Bağlantı yapılandırılmamış bir şirketin sitesine gidiyor. |
| `no_url` | Book>Direct kaydında bağlantı yok. |

Aynı bağlantıyı paylaşan ilanlar için sayfa bir kez açılır; aynı platform ilanı ve pencere için fiyat bir kez sorulur.

## Nezaket, ilerleme ve hatalar

- Aynı siteye istekler sıralı ve en az 2 sn arayla; en çok 3 şirket yan yana okunur. Ağ hatası bir kez (5 sn sonra) yeniden denenir.
- Bir şirket art arda 3 isteği reddederse (403/429) ya da 5 kez ulaşılamazsa yalnız o şirket durdurulur; beklenmeyen bir hata da yalnız o şirketi "hata" olarak bitirir. Diğer şirketler devam eder; çekim kaydına şirket bazında durum, ilan, eşlenen, fiyatlı sorgu ve istek sayısı yazılır (`agency_rate_companies`).
- İlerleme şirket bazında ilan sayısıyla bildirilir; iptal her istekten önce ve beklemelerde denetlenir. İptal veya yarıda kalan çekim hiçbir alan kaydı bırakmaz; kayıt tek transaction'dır.

## Tarayıcı ve insan doğrulaması

Bir şirket sitesi doğrulama ara sayfası (Cloudflare "Just a moment…", `cf-chl`, `/cdn-cgi/challenge-platform`, `cf-mitigated: challenge`, PerimeterX) döndürürse (sayfadaki sıradan bir CAPTCHA form kutusu doğrulama sayılmaz) toplayıcı `studio/sources/browser_verification.py` ile sayfayı bilgisayardaki Chrome'da (yoksa Edge) **kalıcı profille ve görünür pencerede** açar; profil `work/tarayici-profili/<alan-adı>` altındadır (repoya girmez, `STUDIO_BROWSER_PROFILE` ile değiştirilebilir). İş kaydı "kullanıcı doğrulaması bekleniyor" durumuna alınır (`job_waits` tablosu); İşler panelinde hangi sitenin beklediği görünür. Doğrulamayı kullanıcı yapar; kod hiçbir şeye tıklamaz ve tarayıcıyı gizleyen ayar kullanmaz. Sayfa normal açılınca o şirketin kalan istekleri **aynı tarayıcı oturumundan** yapılır. Doğrulama 15 dakikada tamamlanmazsa ya da Playwright bu bilgisayarda kurulu değilse o şirket atlanır ve kayda yazılır, diğerleri devam eder. Aynı anda yalnız bir doğrulama penceresi açılır. Playwright isteğe bağlı bağımlılıktır (`pip install .[browser]`).

## Saklanan alanlar (şema 11)

- `destination_agency_sites`: destinasyon, alan adı, şirket adı, uyarlayıcı, etkin, sıra.
- `agency_rate_snapshots`: çekim, girdi konaklama çekimi, sorgu günü, istek ve ilan sayısı.
- `agency_rate_windows`: pencere, giriş/çıkış, gece, `queried` / `skipped_past`.
- `agency_rate_companies`: şirket bazında sonuç (durum, ilan, eşlenen, sorgu, fiyatlı sorgu, istek, doğrulama, mesaj).
- `agency_rate_listings`: Book>Direct ilanı (kimlik, ad, yatak odası, mahalleler), Book>Direct bağlantısı, açılan son adres, HTTP durumu, sayfa durumu, platform kimliği, mesaj.
- `agency_rate_quotes` (ilan × pencere): durum (`priced`, `unavailable`, `restricted`, `no_price`, `error`); müsait (sitenin söylediği: 1/0, bilinmiyorsa NULL); gecelik fiyatlar (site veriyorsa); kira; temizlik ücreti (adında "clean" geçen ücretler); diğer ücretler; ücret kalemleri (adlarıyla); vergiler ve vergi kalemleri; genel toplam; toplamın ücret ve vergiyi içerdiği (bizim kontrolümüz: kalemlerin toplamı sitenin toplamını $1 içinde tutuyorsa 1, tutmuyorsa NULL); toplama dahil edilmeyen isteğe bağlı kalemler (ör. seçilmemiş sigorta; ResCMS'te isteğe bağlı satır yalnız sitenin ara toplamı onu içeriyorsa ücret sayılır); para birimi; en az gece ve giriş günleri (ISO hafta günü; kaynağı `sayfa` ya da `yanıt`); sitenin mesajı; sorgu zamanı; sorgulanan URL; ham yanıtların SHA-256 listesi.
- `job_waits`: çalışan bir işin kullanıcı doğrulaması beklediği site (yalnız iş sürerken gösterilir).
- Ham yanıtlar `data/raw/<çekim>/responses/*.gz`; `manifest.json` her yanıtın şirketini, aktarımı (`http`/`browser`), yöntemini, istek gövdesini, adreslerini, HTTP durumunu ve SHA-256'sını tutar.

Site bir alanı vermiyorsa o alan NULL kalır; sıfır yazılmaz. "Müsait değil" ile "kurala takıldı" ayrıdır: bir sitenin "4 gece en az" demesi müsaitlik bilgisi değildir (`available` NULL).

## Okuma anında hesaplanan özet

Hiçbiri saklanmaz (`agency_rates.summarize`). Mahalle × pencere için: mahallenin Book>Direct ilan sayısı, yapılandırılmış şirketlere bağlı ilan sayısı, sorgulanan ilan sayısı, fiyatı alınabilen ilan sayısı ve payı, müsaitliği bilinenler içinde müsait olanların payı, 7 gecelik genel toplamın ortancası ve çeyrekler aralığı, kira ÷ gece ile gecelik ortalamanın ortancası ve çeyrekleri (bizim hesabımız; ücret ve vergi hariç), oda sayısına göre (1–2 [stüdyo dahil], 3, 4, 5+) genel toplam ortancası. Bir ilan birden fazla mahallenin filtresinde göründüyse her birinde sayılır. Ayrıca kapsama (sayfa durumlarına göre ilan sayıları, fiyatlı ilan ve mahalle sayısı) ve şirket bazında sonuç. Etiket: "Kiralama şirketlerinin kendi sitelerinde <tarih> tarihinde sorgulanan fiyatlar; toplam fiyat sitenin gösterdiği zorunlu ücretleri ve vergileri içerir (isteğe bağlı sigorta gibi kalemler hariç)"; toplamı kalemleriyle doğrulanamayan fiyat varsa etiket bunu sayısıyla söyler.

## Arayüz

Konaklama sekmesinin altında "Kiralama şirketlerinin kendi siteleri · Konaklama fiyatları" bölümü: toplama düğmesi, sürüm seçimi ve ham manifest; kapsama göstergeleri; mahalle × pencere fiyat tablosu (sorgulanan, fiyatlı, müsait payı, toplam ortancası ve çeyrekleri, kira gecelik ortancası); oda sayısına göre ortancalar; şirket bazında sonuç ve eşlenemeyen ilanların nedenleri. Bir mahalleye tıklayınca ilanlar, ilana tıklayınca pencere pencere sitenin fiyat dökümü (kira, ücretler adlarıyla, vergiler, toplam, toplama dahil edilmeyen kalemler, kural, sitenin mesajı, sorgu zamanı) ve şirketin ilan sayfasına bağlantı. İşler panelinde doğrulama bekleyen iş "Kullanıcı doğrulaması bekleniyor · <site>" etiketiyle görünür.

## Kapsama

Gerçek çekim (8 Ekim 2026), ilan sayısı:

| Durum | İlan |
|---|---:|
| şirket sitesinde bulundu | 529 |
| sayfa bulunamadı (404 veya 'not found' sayfası) | 120 |
| bağlantı ilan sayfasına gitmiyor | 64 |
| başka siteye yönlendi | 0 |
| ilan sayfası erişime kapalı (403) | 43 |
| siteye ulaşılamadı | 3 |
| sorulmadı | 0 |
| şirketin sitesi için uyarlayıcı yok | 1623 |
| Book>Direct'te bağlantı yok | 7 |
| **Toplam** | **2389** |

En az bir pencerede fiyatı alınan ilan: **510**. Bütün ilanlara oranı %21,3, yapılandırılmış şirketlere bağlı 759 ilana oranı %67,2. Fiyat sorgusu (ilan × pencere): 2116. Fiyat alınan mahalle: 12/13 (Alys Beach'teki 7 ilanın 6'sı alysbeach.com'a bağlı, onun uyarlayıcısı yok; 1'inin bağlantısı eski).

Şirket bazında sonuç:

| Şirket | Uyarlayıcı | İlan | Bulunan | Fiyatlı sorgu | İstek | Durum |
|---|---|---:|---:|---:|---:|---|
| Benchmark Management (benchmark30a.com) | `rescms` | 241 | 189 | 483/756 | 1747 | tamamlandı |
| 30A Escapes (30aescapes.com) | `track` | 162 | 143 | 327/572 | 500 | tamamlandı |
| Rosemary Beach® (rosemarybeach.com) | `streamline` | 89 | 61 | 156/244 | 535 | tamamlandı |
| Dune Allen Realty Vacation Rentals (beautifulbeach.com) | `vr_router` | 88 | 37 | 92/148 | 288 | tamamlandı |
| Panhandle Getaways (panhandlegetaways.com) | `track` | 81 | 33 | 104/132 | 214 | tamamlandı |
| Dune Vacation Rentals (dunevacationrentals.com) | `streamline` | 49 | 34 | 94/136 | 314 | tamamlandı |
| 30A Cottages (30acottagesandconcierge.com) | `rescms` | 17 | 14 | 27/56 | 97 | tamamlandı |
| Grayton Coast Rentals (graytoncoastrentals.com) | `rescms` | 17 | 11 | 22/44 | 85 | tamamlandı |
| My Vacation Haven (myvacationhaven.com) | `rescms` | 15 | 7 | 20/28 | 75 | tamamlandı |

Eşlenemeyen ilanların başlıca nedenleri: Book>Direct bağlantısının eskimesi (404, 200 kodlu "not found" sayfası, arama sayfasına yönlenme) ve yayından kalkmış ilanların 403 "Access denied" sayfası. 360blue gibi kapsam dışı şirketler yüzünden fiyat örneği şirketlere ve mahallelere göre dengesizdir (WaterColor ve WaterSound'daki ilanların çoğu 360blue'nun).

## Geçici denemede düzeltilenler (8 Ekim 2026)

1. Sıradan CAPTCHA form kutusu taşıyan 403 "Access denied" sayfası doğrulama sanılıyordu (iki şirkette görünür pencere açıldı); artık yalnız ara sayfa işaretleri sayılıyor ve 403'ten sonra sitenin ana sayfasına bakılıyor.
2. Panhandle Getaways'in Track fiyat servisi, sayfa takviminde dolu görünen haftalara da fiyat veriyordu; Track uyarlayıcısı önce takvime bakıyor.
3. ResCMS'te bazı sitelerin isteğe bağlı sigorta satırı "seçilmedi" işaretsizdi ve toplama girmiyordu; ara toplama göre ayrılıyor.
4. 200 kodlu "Pages Not Found" sayfaları `not_found` sayılıyor.

## Sınırlar

- Yalnız yapılandırılmış şirketler sorulur; 360blue, oversee.us, realjoy, exclusive30a, oldseagrove (Cloudflare), Southern Resorts (fiyat servisi çözülemedi), Vrbo/Airbnb/Vacasa ve bağlantısı eskimiş şirketler kapsam dışı. Fiyat örneği bu yüzden şirketlere ve mahallelere göre dengesizdir; özet "fiyatı alınabilen ilanlar" içindir, mahallenin tamamını temsil etmez.
- Fiyat sorgu günündeki gösterimdir; site sonradan değiştirebilir. Promosyon kodu, indirim veya telefonla verilen fiyat yoktur. Misafir sayısı 2 yetişkin.
- Book>Direct bağlantısı eskiyse ilan eşlenmez; adla başka bir ilana bağlanmaz.
- Oda sayısı Book>Direct ilanından; şirket sitesindeki oda sayısıyla karşılaştırılmadı.
- Para birimi sitede "$" ya da alan olarak "USD"; dönüştürme yapılmaz.

## Video dili

Kullanılabilir: "<Mahalle>'de kiralama şirketlerinin kendi sitelerinde, <tarih> tarihinde <pencere> haftası için sorduğumuz <n> evin, sitenin gösterdiği vergiler ve ücretler dahil haftalık toplamının ortancası yaklaşık $X'ti." Ortancanın yanında kaç ilandan hesaplandığı ve aralık (çeyrekler) söylenir. Kullanılmaz: "<Mahalle>'de bir hafta $X tutar" (genelleme), "fiyatlar şu kadar arttı" (tek tarih), ilan sayısı az olan hücrelerden mahalle karşılaştırması, 360blue'nun yoğun olduğu WaterColor/WaterSound için "mahallenin fiyatı".

## Testler

`tests/test_agency_rates.py` (MockTransport, canlı ağ yok): her uyarlayıcının sayfa ve fiyat ayrıştırması (ResCMS kuralları JSON ve tek tırnaklı biçimde, Track ücret grupları, Streamline gecelik fiyatlar ve isteğe bağlı kalemler, router), eksik alanların NULL kalması, müsait değil yanıtları, en az gece kuralı (sayfadan ve yanıttan), yalnız bağlantıyla eşleme (404, ana sayfaya yönlenme, başka siteye yönlenme, bağlantısız ve yapılandırılmamış ilan; ad farklı da olsa aynı bağlantı), geçmiş pencerenin sorulmaması, ham yanıt SHA-256'ları, bir şirketin hatasında (reddetme, ulaşılamama, beklenmeyen hata) diğerlerinin devam etmesi, ağ hatasında tek yeniden deneme, doğrulama akışı (bekleme bildirimi, aynı oturumla devam, zaman aşımı ve tarayıcı yokken şirketin atlanması), iş kaydında bekleyen sitenin görünmesi ve temizlenmesi, iptal (çekirdek ve API), atomik geri alma, API özeti ve oda grupları, taze veritabanı yapılandırması ve kısıtları, v10 → v11 migration ve geri alma. `tests/frontend.test.mjs`: fiyat hücreleri, kalem dökümü, şirket tablosu, İşler panelindeki bekleme etiketi.
