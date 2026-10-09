# GÖREV-09 Raporu — v0.11.0 yayını, gerçek tarayıcı kurulumu, konaklama fiyat kapsaması ve restoran bilgileri

Tarih: 8–9 Ekim 2026 · Dal: `gorev-09-kapsama-restoran` · Uygulama `0.12.0` · Şema `12`

## Kısaca

- **Adım 1 tamam:** main `9f2d65a`'ya getirildi, `v0.11.0` etiketi konuldu; main ve etiket CI'ı başarılı.
- **Adım 1b tamam (görev sırasında eklendi):** Playwright'in test tarayıcısı bırakıldı; bilgisayardaki gerçek Chrome normal uygulama gibi, tek kalıcı profille açılıp CDP ile bağlanılıyor. Bu kurulumla eski doğrulama dertlerinin çoğu kalktı: ısınmada 24 siteden yalnız order.online doğrulama istedi; floridastateparks.org açıldı.
- **Adım 2–3 tamam:** 15 yeni kiralama şirketi (toplam 24), 6 yeni uyarlayıcı, adres/konum eşlemesi, Alys Beach'in kendi envanteri, yayımlanmış kira, misafir sayısı, korumalı siteler, Sonbahar 2027 penceresi (`agency-lodging-rates/2`, şema 12).
- **Adım 4 tamam:** misafir sayısı hiçbir şirkette toplamı değiştirmedi; bütün şirketler 2 yetişkinle soruluyor.
- **Adım 5 tamam:** restoranların kendi sitelerinden menü, fiyat seviyesi, saat, rezervasyon ve çocuk menüsü (`restaurant-sites/1`); görüntü menüler elle okundu.
- **Adım 6 tamam:** restoran adres ayrıştırması ve NWS yöntemi düzeltildi.
- **Adım 7 tamam:** geçici denemeler, gerçek DB kopyasında v11 → v12 geçişi, tam yedekten sonra gerçek veritabanında dört çekim; ilk restoran çekiminde bir menü ayrıştırma hatası görülünce düzeltilip ikinci tam yedekten sonra işletme siteleri yeniden çekildi; kontroller temiz.
- **Ana sonuç — konaklama:** fiyatı alınan Book>Direct ilanı **510 → 1.066** (şirket sitesinde bulunan 529 → 1.127). Bahar tatili 2027 ve Yaz 2027'de **her mahallede en az 15 fiyatlı ilan** var; tek istisna Gulf Place'in Bahar penceresi (11). Alys Beach'te fiyatlar şirketin kendi envanterinden (73 ev, Bahar 54, Yaz 62 fiyatlı). 360blue engelli kaldı.
- **Ana sonuç — restoranlar:** 138 restoranın 113'ünde site çalışıyor; **33'ünde fiyat seviyesi** hesaplandı (bizim sınıflamamız), 87'sinde menü, 85'inde saat, 41'inde rezervasyon bilgisi var.
- **Sonradan bulunan bir hata:** Oversee'nin şirket listesi gerçek çekimde okunamadı (site JSON yerine HTML döndürüyor); 174 ilanın fiyatı kayıtlı, bağlantısı çalışmayan 11 ilan için adres eşlemesi yapılamadı. Kod düzeltildi; sonraki çekimde bunlardan 4'ü eşlenecek.

## Adım 1 — v0.11.0'ı main'e alma ve etiketleme

| | |
|---|---|
| Önce | `origin/gorev-08-konaklama-fiyat` son commit `9f2d65a` CI: başarılı |
| main | `git merge --ff-only origin/gorev-08-konaklama-fiyat` ile `9f2d65ae85a2adccd1e7f4605406271dbc4d952f`'e getirildi ve push edildi |
| Etiket | açıklamalı `v0.11.0` ("v0.11.0 — kiralama şirketlerinden konaklama fiyatları") `9f2d65a`'yı gösteriyor, push edildi |
| main CI | çalıştırma 37796679492 — başarılı |
| Etiket CI | çalıştırma 37796684505 — başarılı |
| Görev dalı | güncel main'den `gorev-09-kapsama-restoran` açıldı |

## Adım 1b — Tarayıcı kurulumu (görev sırasında eklendi)

Commit `d4d2eb8` (ayrı commit) ve ardından küçük düzeltmeler (`c5a6652`).

- Playwright'in `launch_persistent_context` ile açtığı test tarayıcısı tamamen bırakıldı. `studio/sources/browser_verification.py` bilgisayarda kurulu Chrome'u (yoksa Edge) **normal bir uygulama gibi** başlatıyor: komut yalnız `chrome.exe --user-data-dir=work\tarayici-profili\30a-studio --remote-debugging-port=0` (port tarayıcının seçtiği, yalnız 127.0.0.1). Otomasyon bayrağı ve Playwright'in açılış ayarları yok; kod tarayıcıya CDP ile bağlanıyor (`connect_over_cdp`). Kullanıcı aracısı, dil (tr-TR), saat dilimi (Europe/Istanbul) ve pencere boyutu tarayıcının kendi değerleri.
- Bütün siteler için tek profil; tarayıcı açıksa yeniden bağlanılıyor (`DevToolsActivePort`), ikinci kez açılmıyor; profil çekimler arasında korunuyor.
- Bir kez doğrulama gösteren alan adı veritabanında "tarayıcıyla okunur" diye işaretleniyor (yeni `browser_hosts` tablosu, şema 12); sonraki çekimlerde o siteye ayrı HTTP istemcisiyle gidilmiyor.
- Çekim sırasında doğrulama sayfası 20 sn içinde kendiliğinden geçmezse site **sona bırakılıyor**, diğerleri devam ediyor; en sonda bekleyen siteler ayrı sekmelerde açılıyor, iş bunları tek liste halinde gösteriyor ve 15 dakika bekliyor; olmazsa site atlanıp kayda yazılıyor. Isınma komutu: `python -m studio.sources.browser_verification isinma`.
- Gizlenme eklentisi, navigator özelliklerini yamalama, başka tarayıcı taklidi, CAPTCHA çözme servisi, proxy yok. Not: bu kurulumda da sayfalar `navigator.webdriver` değerini `true` görüyor (Chrome hata ayıklama bağlantısında bunu kendisi bildiriyor); kural gereği değiştirilmedi.
- Testler: başlatma komutunda otomasyon bayrağı olmaması, açık tarayıcıya yeniden bağlanma, `browser_hosts` işaretinin kalıcı olması ve bir dahaki çekimde siteye düz HTTP ile gidilmemesi, sona bırakma, tek bekleme ve zaman aşımı (ajans ve restoran toplayıcısında ayrı ayrı).
- CLAUDE.md "Tarayıcı ve insan doğrulaması" paragrafı ve CALISMA_MANTIGI §4 madde 12–14 güncellendi.
- **floridastateparks.org** bu tarayıcıda açıldı: HTTP 200, başlık "Home | Florida State Parks" (GÖREV-08'de otomasyonla açılan Chrome'a 403 veriyordu).
- Gerçek çekimden önceki ısınmada 24 siteden yalnız **order.online** (DoorDash sipariş sayfası) doğrulama istedi; kullanıcıya tek liste halinde bildirildi. Kullanıcı birkaç kez denedi ama bu sitedeki doğrulama geçmedi; ona bağlı üç restoran (Siam Thai; Cajun Corner ve Big Bad Breakfast'ın sipariş menüleri) "doğrulama tamamlanmadı" ya da 403 notuyla kaydedildi. Eski test tarayıcısında doğrulama isteyen oversee.us, exclusive30a.com ve restoran sitelerinin hepsi bu tarayıcıda doğrulamasız açıldı.
- Kurulumdan önce bulunan iki hata da düzeltildi: Cloudflare kullanan normal sayfalardaki `/cdn-cgi/challenge-platform/scripts/jsd` betiği ve iletişim formlarındaki Turnstile kutusu doğrulama sayfası sanılıyordu (`b9424de`, `d3c018c`); tarayıcı penceresi kapanınca bütün çekimin düşmesi (`efb5dc7`).

## Adım 2 — Kiralama şirketleri: ikinci keşif

Ayrıntı `AJANS-KESFI-2.md`, güncel tablo `ajanslar.csv` (iki yeni sütun: `esleme_yolu`, `gorev09_durum`).

- Görevin saydığı bütün şirketlere bakıldı; **15 yeni şirket** yapılandırıldı (toplam 24).
- **Southern Resorts çözüldü:** sayfanın `POST /property/v3/quote` isteği belirteçsiz çalışıyor; otomatik promosyon toplamdan düşülüyor ve ayrı kalem.
- **Homeowner's Collection, Ocean Reef, Paradise:** yeniden bakıldığında Book>Direct bağlantılarının çoğu ilan sayfasına gidiyor (GÖREV-08'deki "ana sayfa/genel liste" sonucu bu kez görülmedi); bağlantıyla eşleniyor.
- **Sanders Beach, FunVacay, Coastal Blue:** ResCMS fiyat formu var (GÖREV-08 sonucu küçük örnekten); yayımlanmış kira tablosu gerekmedi.
- **Alys Beach:** vacation.alysbeach.com, VRPConnect; liste servisinde 73 ev, hepsi "Alys Beach" → kendi envanteri.
- **Grayt 30A → Royal Destinations** (site haritası, 49 ilan) ve **30A Vacay** (site haritası, 120 sayfa; ilan kimlikleri 24 haneli onaltılık, geçici denemede bulunup düzeltildi) adres/konum için şirket listesi olarak yapılandırıldı; Rosemary Beach ve Dune Vacation Rentals'ta Streamline liste servisi.
- **Cloudflare arkasındakiler:** oversee.us ve exclusive30a.com tarayıcıda doğrulamasız açıldı, korumalı olarak yapılandırıldı. **360blue** hâlâ engel sayfası ("Attention Required! | Cloudflare", 403; gerçek çekimden hemen önce yeni tarayıcıyla bir kez bakıldı) → bu görevde yok. **realjoy** keşifte doğrulama ekranı gösterdi, eski test tarayıcısında 15 ve 40 dk beklendi, tamamlanmadı → yapılandırılmadı. **oldseagrove** stay30abeachvacations.com'a yönleniyor, ilan bağlantısı yok.
- **Bulunamayanlar:** Cottage Rental Agency'nin güncel sitesi (alan adı Sandestin'in kaldırılmış sayfasına gidiyor); WaterColor ve WaterSound'un topluluğa ait resmî kiralama programı (aday alan adları bağlantı kurmuyor); 30A Beach Girls'ün kendi sitesi (evler AvantStay'de, kapsam dışı); Beach Escapes (eski bağlantılar "Page Not Found", liste servisi yok).
- **Your Friend at the Beach:** sitenin kendi fiyat formu "You are not authorized to use this service" hatası veriyor; sezon kira aralığı yayımlanmış kira olarak alındı.

## Adım 3 — agency-lodging-rates/2

Commit `3624c90` (+ `b32540c`), ayrıntı `docs/M11-KONAKLAMA-FIYATLARI.md`.

- **3a Adres/konum eşlemesi** (`studio/sources/agency_matching.py`): bağlantı ilana gitmezse ve şirketin ilan listesi yapılandırılmışsa (platform liste servisi ya da site haritası; her çekimde yeniden okunuyor, ham kopyası SHA-256'lı) adres yöntemi (sokak no + sokak adı birebir, 30A yol adları birleşik, daire ve oda aynı, tek aday) ya da adres yoksa konum yöntemi (≤15 m, oda+banyo aynı, 50 m içinde tek aday; aynı 15 m'de birden fazla Book>Direct ilanı varsa kullanılmaz). Ad hiçbir zaman ölçüt değil. Yöntem ve not her ilanda saklanıyor ve arayüzde görünüyor.
- **Doğrulama** (`eslesme-dogrulama.csv`): geçici denemede adres yönteminde 1, konum yönteminde 7 eşleşme çıktı (yöntem başına 30'dan az olduğu için hepsi); iki taraftaki başlık, adres, oda, banyo, kapasite ve fotoğraf karşılaştırıldı: **8'i de doğru** (başlıklar örtüşüyor, oda ve banyo aynı, kapasitede iki ilanda 1–2 kişi fark; iki çiftte fotoğraf birebir aynı, öbürlerinde aynı evin farklı kareleri). Hatalı eşleşme olmadığı için kurallar değişmedi ve iki yöntem gerçek çekimde kullanıldı; gerçek çekimde de aynı 8 eşleşme çıktı ve yeniden kontrol edildi. Geçici denemede 30A Vacay'in şirket listesi 0 çıkmıştı (ilan kimlikleri 24 haneli onaltılık; düzeltildi, `b32540c`), düzeltmeden sonra 7 konum eşleşmesinin hepsi oradan geldi.
- **3b Yeni uyarlayıcılar:** `vrp` (Oversee, Alys Beach), `property_quote` (Southern), `exceptional_stay` (Exclusive 30A), `asmx_quote` (Newman-Dailey), `wander` (30A Beach Stays), `qvr` (Your Friend at the Beach; yayımlanmış kira). Mevcut `rescms`, `track`, `vr_router` yeni şirketlerle paylaşılıyor.
- **3c Kendi envanteri:** Alys Beach Vacation Rentals (VRP liste servisi, 73 ev, hepsi sitenin kendi verisinde "Alys Beach"); Book>Direct'teki 6 Alys Beach ilanı tek ev değil grup kaydı olduğundan çift sayım yok. Cottage Rental Agency'nin güncel sitesi bulunamadığı için uygulanmadı.
- **3d Yayımlanmış kira:** Your Friend at the Beach — sezon gecelik kira aralığı × 7, "vergi ve ücret hariç", toplam ortancalarına karışmıyor.
- **3e Misafir sayısı:** her fiyat satırında `adults`/`children` (servis sormuyorsa boş).
- **3f Sonbahar 2027** (2027-10-16 → 10-23) eklendi; Book>Direct toplayıcısı da aradı. Pencere başına "fiyat yok" oranı (Book>Direct sorguları): Sonbahar 2026 %3,4, Kış %2,0, Bahar %2,3, Yaz %2,0, **Sonbahar 2027 %3,5**. Sonbahar 2027'deki 39 "fiyat yok": 30A Beach Stays'in 18 ilanının hepsi (sitenin cevabı `DATES_NOT_BOOKABLE`, tarihler henüz açılmamış) ve Your Friend at the Beach'in 21 ilanı (servis her pencerede reddediyor). Alys Beach'in kendi envanterinde Sonbahar 2027 için 73 evin hepsi "Arrival date is beyond the maximum notice period" (fiyat yok). Diğer şirketler Sonbahar 2027'yi fiyatladı (811 fiyatlı sorgu).
- **3g Korumalı siteler:** oversee.us ve exclusive30a.com yalnız tarayıcıdan, istekler arası ≥6 sn, aynı anda tek korumalı şirket, ilk 403/429/engel sayfasında şirket durur (yeniden deneme yok).
- **3h Özet:** mahalle × pencere için Book>Direct fiyatlı ilan sayısı yöntemlere göre (bağlantı/adres/konum), kendi envanteri ayrı sütun, yayımlanmış kira ayrı sütun; etiket kaynağı söylüyor.
- Testler: `tests/test_agency_v2.py` (32 test).

## Adım 4 — Misafir sayısı kontrolü

`misafir-sayisi-kontrol.csv`: her şirketten üçe kadar ilan, Yaz 2027 için 2 yetişkin ve oda × 2 yetişkinle (kapasiteyi aşmadan) sorgulandı.
- Karşılaştırılabilen her ilanda iki toplam **aynı** çıktı (fark 0); hiçbir şirkette toplam misafir sayısıyla değişmedi → bütün şirketler `two_adults` kaldı.
- Track (30A Escapes, Ocean Reef, Panhandle) ve ASMX (Newman-Dailey) servisleri misafir sayısı sormuyor; kontrol gerekmedi.
- Your Friend at the Beach'in fiyat servisi reddettiği için karşılaştırılamadı; 30A Vacay'de Book>Direct bağlantıları 404 olduğundan kontrol anında karşılaştırılabilir ilan yoktu; Grayton Coast'ta yalnız 1 ilan karşılaştırılabildi.
- Homeowner's Collection "For My Girls": 10 kişiyle "Occupancy for this property is 9 persons … Not Available" (sitenin kapasitesi Book>Direct'teki 11'den düşük); toplam farkı değil, kapasite sınırı.

## Adım 5 — Restoran bilgileri (restaurant-sites/1)

Commit `ca09277` ve sonrası, ayrıntı `docs/M12-RESTORAN-BILGILERI.md`.

- **5a Book>Direct restoran servisi:** 18 kayıt (2 sayfa), hepsi OpenTable kaynaklı (rezervasyon ve menü bağlantısı OpenTable), alanlar: ad, mutfak türü, adres, telefon, koordinat, OpenTable'ın `$` işareti; saat yok. İlk sayfadaki 10 kaydın 6'sı Miramar Beach (30A dışı). İşletmenin kendi beyanı olmadığı ve küçük bir kısmı kapsadığı için kullanılmadı. Anahtar yalnız bellekte.
- **5b Siteler:** dizindeki web sitesi; dizinde site olmayan/çalışmayan iki restoran için web aramasıyla resmî site bulundu ve gözden geçirilmiş dosyaya yazıldı (Thai Elephant: telefon ve adres tuttu; Siam Thai: DoorDash sipariş sayfası, adres tuttu). 98 Bar-B-Que'nun dosya adında "menu" geçmeyen iki menü görseli aynı dosyaya menü bağlantısı olarak eklendi.
- **5c Alanlar:** site durumu, menüler (biçim, tür), kalemler (bölüm, ad, fiyat metni, sayı, kural), saatler, rezervasyon, çocuk menüsü, açık hava, su kenarı, köpek; her değer kaynak url, erişim zamanı, SHA-256 ve yöntem etiketiyle. Görüntü menüler elle okundu: `studio/destinations/thirty_a_menu_readings.csv` (296 satır; 98 Bar-B-Que, Amici 3 PDF, Raw & Juicy, Daytrader 2 görsel, MeltDown, Cowgirl/CK Feed panosu; 18 fotoğraf/logo "menü değil"; 5 fiyatsız menü "fiyat yazmıyor").
- **5d Mimari sınır:** okuma, menü bulma, PDF, yapısal veri, rezervasyon/menü platformu tanıma, fiyat ayrıştırma, bölüm tablosu ve fiyat seviyesi kuralı generic çekirdekte (`studio/sources/restaurant_sites.py`, `menu_sections.csv`); restoran listesinin kaynağı (destinasyonun dizin çekimi) ve gözden geçirme dosyaları destinasyon tarafında (`thirty_a.py` profili ve yanındaki CSV'ler). Aynı siteye istekler sıralı ve ≥2 sn arayla.
- **5e Arayüz:** Restoranlar sekmesinde fiyat seviyesi, rezervasyon ve çocuk menüsü sütunları ve filtreleri; restoran ayrıntısında kaynaklarıyla bütün alanlar, menü bağlantıları, saatler, "bizim sınıflamamız" notu; mahalle özeti. Ekran görüntüleri `ekran/`.
- **5f Testler:** `tests/test_restaurant_sites.py` (30 test).
- Bölüm sınıflama tablosu: `menu-bolum-siniflari.csv` (329 satır).
- **Karar gereken nokta:** ana yemek sayıları için menü önceliğine "genel" (öğün belirtmeyen tek menü) eklendi: akşam > öğle > genel > brunch > kahvaltı. Görev "akşam, öğle, brunch, kahvaltı" diyordu; restoranların çoğu tek genel menü yayımladığı için genel menü eklenmeseydi seviyesi hesaplanan restoran sayısı belirgin düşerdi.

### Restoran kapsaması (gerçek çekim `c51e63dc`, 9 Ekim 2026, 956 istek, 45 dk)

| | Restoran |
|---|---:|
| Toplam | 138 |
| Site çalışıyor | 113 |
| Menü bulundu | 87 |
| Ana yemek fiyatı var | 48 |
| **Fiyat seviyesi hesaplandı** | **33** ($ 8 · $$ 15 · $$$ 9 · $$$$ 1) |
| Saat bilgisi | 85 |
| Rezervasyon bilgisi (çevrim içi, telefon, alınmıyor, bekleme listesi) | 41 |

330 menü bulundu, 217'si okundu (83'ünde fiyatlı kalem yok, 30'u hata), 7.815 kalem, 255 bilgi kaydı (saat, rezervasyon, çocuk menüsü vb.).

Seviyesi hesaplanmayan 105 restoranın nedenleri (`restoranlar.csv` → `seviye_yok_nedeni`): menü bulunamadı 26, menüde ana yemek fiyatı yok 22 (menü var ama bölümleri ana yemek değil: kahve, tatlı, içecek, atıştırmalık yerleri; ya da başlıksız menüler), menü okundu ama fiyatlı kalem çıkmadı 17 (JavaScript ile çizilen ya da fiyatsız menüler; 3'ünde okuma hatası), 5'ten az ana yemek fiyatı 15, site çalışmıyor 9 (bağlantı hatası, 403, doğrulama), sosyal medya sayfası 9 (giriş gerekiyor), park edilmiş alan adı 3, sayfa bulunamadı 2, sezon için kapalı 1 (Hokulia), site yok 1. Doğrulama: order.online kullanıcı denemesine rağmen geçmedi; Siam Thai (sitesi bu sayfa), Cajun Corner ve Big Bad Breakfast'ın sipariş menüleri "doğrulama tamamlanmadı" ya da 403 notuyla kaydedildi.

**Neden yeniden çekildi:** ilk gerçek çekimde (`a28b02c1`, 8 Ekim, 952 istek, 42 dk) seviyeler tek tek gözden geçirilirken Big Bad Breakfast'ın $$$ çıktığı görüldü: sitedeki besin değeri PDF'inin son sütunu (protein, gram) fiyat sanılmıştı. Düzeltildi (`f5448ff`: besin değeri tablosu menü sayılmıyor; 6 ya da daha çok sayılı tablo satırı ve yanında sayı olan "DINNER MENU" gibi başlıklar kalem sayılmıyor), ikinci tam yedekten sonra işletme siteleri yeniden çekildi. İlk çekim geçmişte duruyor; ekran ve teslim tabloları yeni çekimden. İki çekim arasındaki seviye farkları:
- Big Bad Breakfast $$$ → yok (düzeltme; kahvaltı menüsü PDF'i aslında besin değeri tablosu, sipariş menüsü order.online'da).
- Pescado ve The Courtyard at Pescado (aynı site) $$ → yok: "DINNER MENU" başlığı artık kalem sayılmadığı için 4 ana yemek kaldı (5'ten az).
- Fonville Press yok → $$: ilk çekimde site tarayıcıda da 403 vermişti; bu çekimde tarayıcıyla açıldı, PDF menüler okundu.
- Scratch Biscuit Kitchen yok → $: menü SinglePlatform'da JavaScript ile çiziliyor; bu çekimde tarayıcıyla okundu.
- Stinky's Fish Camp yok → $$$: ilk çekimde doğrulama gösterdikten sonra tarayıcıyla 4 sayfa okunmuş, yalnız genel menü sayfası bulunmuştu (1 ana yemek); bu çekimde site baştan tarayıcıyla okundu (13 sayfa) ve öğün menüleri (akşam, öğle) bulundu.
Diğer 30 restoranın seviyesi aynı. Son üç fark, aynı kodla sitelerin iki çekimde farklı davranmasından; canlı kaynakta beklenen bir oynama.

### Mahalle özeti (`restoran-mahalle-ozet.csv`)

| Mahalle | Restoran | $ | $$ | $$$ | $$$$ | Ana yemek ortancalarının ortancası | Çevrim içi rez. | Çocuk menüsü | Bilgi yok |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dune Allen | 2 | 0 | 0 | 1 | 0 | $25 | 0 | 2 | 0 |
| Gulf Place | 6 | 0 | 0 | 2 | 0 | $25,25 | 0 | 2 | 2 |
| Santa Rosa Beach | 28 | 0 | 3 | 0 | 0 | $17,95 | 1 | 6 | 12 |
| Blue Mountain Beach | 8 | 1 | 0 | 0 | 0 | $13,49 | 2 | 0 | 1 |
| Grayton Beach | 15 | 0 | 3 | 1 | 0 | $18 | 1 | 4 | 2 |
| WaterColor | 5 | 1 | 1 | 1 | 0 | $19 | 0 | 4 | 0 |
| Seaside | 19 | 3 | 2 | 0 | 0 | $13 | 3 | 2 | 4 |
| Seagrove | 17 | 2 | 2 | 1 | 1 | $15,50 | 4 | 5 | 7 |
| WaterSound | 3 | 0 | 1 | 0 | 0 | $17 | 0 | 0 | 0 |
| Seacrest | 8 | 1 | 1 | 1 | 0 | $19 | 0 | 2 | 3 |
| Alys Beach | 7 | 0 | 1 | 1 | 0 | $21 | 3 | 3 | 0 |
| Rosemary Beach | 12 | 0 | 0 | 0 | 0 | — | 1 | 4 | 2 |
| Inlet Beach | 11 | 0 | 1 | 1 | 0 | $21,25 | 1 | 3 | 2 |

Mahalle sayıları azdır (çoğu mahallede 0–6 restoranda seviye var; Rosemary Beach'te hiç yok); mahalleler arası karşılaştırma için zayıf örnek. Bir restoran birden fazla mahallede sayılabilir. Ortanca hesaplanan değerdir, "bizim hesabımız" diye etiketlenir.

## Adım 6 — İki küçük düzeltme

- Restoran adres ayrıştırması (`south-walton-restaurants/2`): posta kodu olmayan şehir satırı ayrıştırılıyor; gerçek çekimde "Canopy Road Café" şehir **Inlet Beach**, eyalet **FL**, ikinci adres satırı boş; şehri boş restoran kalmadı. Test eklendi.
- NWS kaynak kaydı: gerçek veritabanının kopyasında yöntem **"Belirlenecek"** idi; v12 geçişi "API" yapıyor (eski varsayılan not da yenisiyle değişiyor). Gerçek veride geçişten sonra "API".

## Adım 7 — Gerçek ortam

**Geçici denemeler** (`work/gorev-09/temp-data`, `temp-restoran-data`; gerçek DB'nin geçiş yapılmış kopyaları):
- Konaklama (5 pencere): 2.389 ilan, 1.191 istek, 38 dk.
- Restoran dizini (`/2`) ve işletme siteleri: üç deneme; her denemede bulunan hatalar düzeltildi (doğrulama sayfası yanlış alarmları, kapanan pencere, 404 veren dizin sayfası için ana sayfaya düşme, 403/429 sitelerin tarayıcıda denenmesi, aynı sayfayı paylaşan restoranlar, menü ayrıştırma gürültüsü, menü bölümü sınıfları). Son deneme yeni tarayıcı kurulumuyla: 111 çalışan site, 31 fiyat seviyesi.
- Kiralama şirketleri: önce yeni 15 şirket ve yeni eşleme yolları (eski 7 şirket, Oversee ve Homeowner's Collection kapalı; 81 dk), sonra yeni tarayıcıyla Exclusive 30A (79 isteğin hepsi tarayıcı içinden, doğrulama istemedi), sonra 30A Vacay + Rosemary Beach (30A Vacay düzeltmesinden sonra 7 konum eşleşmesi).
- Ekran görüntüleri `ekran/`: Restoranlar sekmesi, mahalle özeti, restoran ayrıntısı (geçici ve gerçek veri; gerçek veri görüntüleri yeniden çekimden sonra gerçek DB'nin `work/` kopyasıyla açılan uygulamadan), fiyat bölümü ve fiyat tablosu (gerçek veri). Ayrıntı görüntüsünde "İşletmenin kendi sitesi" bölümünün dar sütuna sıkıştığı görüldü ve düzeltildi (`dd9026d`); fiyat tablosunda Alys Beach hücresinin kendi envanterini göstermediği görüldü ve düzeltildi (`d0974d6`, gerçek veri görüntüsü düzeltmeden önce alındı).

**Migration denemesi:** gerçek DB'nin `work/` kopyasında iki kez (ikincisi `browser_hosts` tablosu eklendikten sonra) v11 → v12: eski 41 tablonun satırları aynı; 9 yeni tablo boş; `destination_agency_sites` 9 → 24, `destination_lodging_windows` 4 → 5, `sources` 14 → 15; NWS yöntemi "API"; `integrity_check` ok, `foreign_key_check` boş.

**Gerçek veritabanı:**
- Uygulama kapalıyken `data/` tam yedeği: `work/yedek/20261008-2310/` (8.016 dosya, 131,96 MB; kopya birebir doğrulandı). Restoran siteleri yeniden çekilmeden önce ikinci tam yedek: `work/yedek/20261009-0419/` (20.496 dosya).
- Uygulama gerçek veri klasörüyle açıldı; açılışta otomatik yedek `data/backups/studio-v11-b5d35eae98694c6c8a7bae7e9c2d2e1d.sqlite3` alındı ve şema 12'ye geçildi.
- 360blue gerçek çekimden hemen önce yeni tarayıcıyla bir kez açıldı: hâlâ engel sayfası (HTTP 403, "Attention Required! | Cloudflare").
- Çekimden önce ısınma: tarayıcıyla okunacak 24 site sekmelerde açıldı; yalnız order.online doğrulama istedi, kullanıcıya tek liste halinde bildirildi.
- Sırayla dört çekim, sonra işletme sitelerinin yeniden çekimi:

| Çekim | Kimlik | Süre | İstek | Sonuç |
|---|---|---:|---:|---|
| Restoran dizini (`south-walton-restaurants/2`) | `35c9184e` | 1,7 dk | — | 138 restoran |
| İşletme siteleri (`restaurant-sites/1`), ilk | `a28b02c1` | 42,4 dk | 952 | 112 çalışan site, 304 menü, 7.503 kalem, 33 fiyat seviyesi (biri hatalı; yerine aşağıdaki çekim geçti) |
| Konaklama (`bookdirect-lodging/2`) | `69136a08` | 38,3 dk | 1.191 | 2.389 ilan, 5 pencere |
| Kiralama şirketleri (`agency-lodging-rates/2`) | `e54c9dfa` | 209,5 dk | 10.172 | 1.127 ilan bulundu, 1.066 fiyatlı; kendi envanteri 73 ev |
| İşletme siteleri, yeniden (9 Ekim, `f5448ff` ile) | `c51e63dc` | 44,6 dk | 956 | 113 çalışan site, 330 menü, 7.815 kalem, 33 fiyat seviyesi |

- Uygulama iki oturumun (dört çekim; yeniden çekim) sonunda düzgün kapatıldı (`data/` içinde -wal/-shm kalmadı). Son kopyada: `user_version` 12, `integrity_check` ok, `foreign_key_check` boş.
- Önce/sonra (ilk yedek → son durum, değişen tablolar): `restaurant_records` 276 → 414, `restaurant_regions` 282 → 423, `restaurant_site_snapshots` 0 → 2, `restaurant_sites` 0 → 276, `restaurant_menus` 0 → 634, `restaurant_menu_items` 0 → 15.318, `restaurant_facts` 0 → 505, `lodging_snapshots` 2 → 3, `lodging_windows` 8 → 13, `lodging_listings` 4.778 → 7.167, `lodging_search_results` 18.383 → 29.965, `lodging_filters` 112 → 182, `lodging_calendars` 3.242 → 4.095, `lodging_calendar_windows` 12.968 → 17.233, `lodging_rate_months` 1.817 → 2.711, `agency_rate_snapshots` 1 → 2, `agency_rate_windows` 4 → 9, `agency_rate_listings` 2.389 → 4.778, `agency_rate_quotes` 2.116 → 7.751, `agency_rate_companies` 9 → 33, `agency_rate_own_listings` 0 → 73, `agency_rate_own_quotes` 0 → 365, `agency_rate_published` 0 → 105, `browser_hosts` 0 → 22, `destination_agency_sites` 9 → 24, `destination_lodging_windows` 4 → 5, `sources` 14 → 15, `source_runs` 17 → 22, `jobs` 20 → 25. Diğer 24 tablo aynı (plaj, hava, iklim, mahalle, eski çekimler). İkinci yedekle son durum arasında yalnız işletme sitesi tabloları, `source_runs` ve `jobs` değişti.

### Kiralama şirketleri sonucu

| Şirket | Uyarlayıcı | İlan | Eşlendi (yöntem) | Fiyatlı sorgu | Durum |
|---|---|---:|---|---:|---|
| Benchmark Management | rescms | 241 | 188 (bağlantı) | 665/940 | tamam |
| Oversee | vrp (korumalı) | 185 | 174 (bağlantı) | 622/870 | **failed**: şirket listesi okunamadı (bkz. sürprizler); fiyatlar kayıtlı |
| 30A Escapes | track | 162 | 143 | 329/715 | tamam |
| Homeowner's Collection | rescms | 143 | 118 | 325/590 | tamam |
| Southern Vacation Rentals | property_quote | 104 | 69 | 238/345 | tamam |
| Ocean Reef Resorts | track | 96 | 71 | 206/355 | tamam |
| Rosemary Beach® | streamline | 89 | 61 (liste 228) | 210/305 | tamam |
| Dune Allen Realty | vr_router | 88 | 37 | 124/185 | tamam |
| Panhandle Getaways | track | 81 | 33 | 138/165 | tamam |
| Paradise Properties | vr_router | 59 | 35 | 127/175 | tamam |
| 30A Vacay | vr_router | 54 | 7 (konum 7; liste 120) | 14/35 | tamam |
| Dune Vacation Rentals | streamline | 49 | 35 (bağlantı 34, adres 1) | 102/175 | tamam |
| Grayt 30A / Royal Destinations | rescms | 41 | 2 (liste 49) | 4/10 | tamam |
| Sanders Beach Rentals | rescms | 38 | 27 | 79/135 | tamam |
| FunVacay | rescms | 31 | 23 | 84/115 | tamam |
| Exclusive 30A | exceptional_stay (korumalı) | 29 | 10 | 31/50 | tamam |
| Your Friend at the Beach | qvr | 22 | 21 | 0/105 (yayımlanmış kira 21 ilan) | tamam |
| 30A Beach Stays | wander | 21 | 18 | 47/90 | tamam |
| Grayton Coast Rentals | rescms | 17 | 11 | 33/55 | tamam |
| 30A Cottages | rescms | 17 | 14 | 37/70 | tamam |
| Newman-Dailey | asmx_quote | 16 | 15 | 51/75 | tamam |
| My Vacation Haven | rescms | 15 | 7 | 27/35 | tamam |
| Coastal Blue Vacations | rescms | 12 | 8 | 21/40 | tamam |
| Alys Beach Vacation Rentals | vrp | 6 (grup kaydı) | 0; kendi envanteri 73 ev | 168/365 (kendi) | tamam |

Hiçbir şirkette doğrulama beklenmedi; korumalı siteler (Oversee, Exclusive 30A) tarayıcı içinden ≥6 sn arayla okundu, ret ya da engel gelmedi. Eşlenemeyen ilanların başlıca nedenleri: Book>Direct bağlantısının eskimesi (255 ilan "bulunamadı", 171 "ilan sayfası değil"), yayından kalkmış ilanların 403'ü (51); şirket listesi olan sitelerde de bu evler şirketin güncel listesinde yok (Grayt 30A'nın 39 ilanından hiçbiri Royal Destinations listesinde değil; Rosemary Beach'te 17 ilan çok daireli yapılarda olduğu için konum kuralı uygulanmadı).

### Mahalle × pencere kapsaması (fiyatlı Book>Direct ilanı; parantez içinde GÖREV-08)

| Mahalle | Book>Direct ilan | Bahar tatili 2027 | Yaz 2027 | Kış 2027 | Sonbahar 2027 | Not |
|---|---:|---:|---:|---:|---:|---|
| Dune Allen | 114 | 45 (31) | 46 (29) | 35 (22) | 46 | |
| Gulf Place | 31 | **11** (2) | 15 (3) | 12 (2) | 12 | Bahar 15'in altında: 31 ilanın yalnız 18'i yapılandırılmış şirketlere bağlı (kalanı 360blue, realjoy ve küçük şirketler) |
| Santa Rosa Beach | 246 | 44 (5) | 52 (5) | 45 (5) | 43 | |
| Blue Mountain Beach | 194 | 54 (7) | 66 (7) | 49 (7) | 62 | + yayımlanmış kira 21 ilan |
| Grayton Beach | 86 | 28 (8) | 31 (8) | 27 (9) | 39 | |
| WaterColor | 259 | 46 (18) | 52 (20) | 47 (15) | 39 | 139 ilan 360blue'da (yok) |
| Seaside | 221 | 71 (5) | 98 (5) | 86 (3) | 101 | |
| Seagrove | 498 | 222 (139) | 261 (161) | 207 (132) | 247 | |
| WaterSound | 165 | 43 (36) | 49 (39) | 41 (35) | 38 | 44 ilan 360blue'da (yok) |
| Seacrest | 301 | 115 (73) | 128 (80) | 125 (79) | 84 | |
| Alys Beach | 7 | 0 (0) · kendi envanteri 54 | 0 (0) · kendi 62 | 0 · kendi 48 | 0 · kendi 0 | Book>Direct'teki 7 kayıt grup kaydı; fiyatlar şirketin kendi envanterinden (ayrı etiketli) |
| Rosemary Beach | 166 | 82 (75) | 90 (81) | 67 (60) | 62 | |
| Inlet Beach | 101 | 38 (8) | 41 (11) | 42 (12) | 38 | |

Ortancalar, çeyrekler, oda gruplarına göre ortancalar, yöntem ve kendi envanteri sütunları `konaklama-fiyat-ozet.csv`'de. Örnek: Yaz 2027 7 gecelik toplam ortancası Seaside $8.702, WaterColor $10.781, Seagrove $5.256, Alys Beach kendi envanteri (Yaz) ayrı satırda. Fiyat örneği şirketlere göre hâlâ dengesiz (360blue yok); özet "fiyatı alınabilen ilanlar" içindir.

## Testler ve CI

- Tam takım art arda 3 kez: **650 Python** testi ve **54 frontend** testi geçti (görev başında main/v0.11.0: 587 + 52).
- Yeni test dosyaları: `tests/test_agency_v2.py` (32), `tests/test_restaurant_sites.py` (30); güncellenenler: `test_agency_rates.py`, `test_restaurants.py`, `legacy.py`, iklim/konaklama/destinasyon/temel testleri (şema 12, 10 toplayıcı, 15 kaynak), `frontend.test.mjs`.
- CI: dal push edildikten sonra eklenecek.

## Sürprizler ve notlar

- **Doğrulama dertlerinin çoğu test tarayıcısındanmış.** Playwright'in açtığı tarayıcıda oversee.us, exclusive30a.com ve pek çok restoran sitesi doğrulama istiyordu; gerçek Chrome'da (Adım 1b) bunlardan yalnız order.online kaldı. Ayrıca iki yanlış alarm vardı: Cloudflare'li normal sayfalardaki bir betik ve iletişim formlarındaki Turnstile kutusu doğrulama sayfası sanılıyordu (düzeltildi).
- **`navigator.webdriver`** yeni kurulumda da `true` görünüyor (Chrome, hata ayıklama bağlantısında bunu kendisi bildiriyor). Kural gereği değiştirilmedi; şimdiye kadar hiçbir siteyi engellemedi.
- **Oversee'nin liste servisi JSON yerine HTML döndürüyor.** Gerçek çekimde şirket listesi okunamadı, şirket "failed" kaydedildi (bağlantıyla eşlenen 174 ilanın 622 fiyatı kayıtlı). Kart biçimi eklendi (`d0974d6`); ham yanıt üzerinde: 198 ev, bağlantısı çalışmayan 11 ilandan 4'ü sonraki çekimde adresle eşlenecek. Kiralama şirketleri bu görevde yeniden çekilmedi.
- **Adres/konum eşlemesi az eşleşme verdi** (1 adres, 7 konum). Bağlantısı çalışmayan ilanların çoğu şirketlerin güncel listesinde yok (şirket artık o evi yönetmiyor) ya da çok daireli yapılarda (konum kuralı bilerek kapalı). Kapsamadaki artışın neredeyse tamamı yeni şirketlerden ve yeniden kontrol edilen bağlantılardan geldi.
- **Homeowner's Collection, Ocean Reef ve Paradise'ta bağlantılar artık ilan sayfasına gidiyor** (GÖREV-08'de ana sayfa / genel liste görünmüştü); adres eşlemesi gerekmedi.
- **Book>Direct'teki Alys Beach ilanları tek ev değil**, "3 BR Homes" gibi grup kayıtları; Alys Beach fiyatları tamamen şirketin kendi envanterinden geliyor ve ayrı etiketli.
- **30A Vacay'in ilan kimlikleri 24 haneli onaltılık**; router uyarlayıcısı yalnız sayısal kimlik bekliyordu (geçici denemede bulundu, düzeltildi).
- **Restoran menüleri çok çeşitli**; bölümsüz PDF'ler, JavaScript ile çizilen platform sayfaları (Popmenu, Toast) ve görüntü menüler fiyat seviyesini sınırlıyor. Hesaplanan seviyelerin hepsi dayandığı ana yemeklerle tek tek gözden geçirildi; yanlış ayrıştırmadan seviye çıkmasın diye birkaç kural eklendi (sepet, sayaç, alerjen notu, adres satırı, $1,5 altı kalemler, besin değeri tabloları ve menü başlıkları fiyat/kalem sayılmıyor). Bu gözden geçirmede ilk gerçek çekimdeki bir hata (Big Bad Breakfast'ın besin değeri PDF'i) bulundu ve işletme siteleri yeniden çekildi.
- **Aynı kodla iki çekim arasında üç restoranın sonucu değişti** (Fonville Press, Scratch Biscuit Kitchen, Stinky's Fish Camp): siteler bir çekimde 403 ya da doğrulama verip öbüründe tarayıcıyla açıldı. Restoran sitelerinden gelen sayılar çekimden çekime birkaç restoran oynayabilir.
- **order.online (DoorDash) doğrulaması** kullanıcı birkaç kez denemesine rağmen geçmedi; üç restoranı etkiliyor (Siam Thai, Cajun Corner, Big Bad Breakfast).

## Yöneticinin kararına kalanlar

1. **Ana menü önceliğine "genel" menünün eklenmesi** (akşam > öğle > genel > brunch > kahvaltı). Görev metni genel menüyü saymıyordu; çıkarılırsa seviyesi hesaplanan restoran sayısı belirgin düşer.
2. **Gulf Place Bahar 2027'de 11 fiyatlı ilan** (hedef 15). Kalan ilanlar 360blue, realjoy ve küçük şirketlerde; 360blue engeli kalkmadıkça artmaz.
3. **360blue** (256 ilan; WaterColor 139, WaterSound 44) hâlâ engelli. **realjoy** (61 ilan) eski test tarayıcısında doğrulanamamıştı; yeni tarayıcıyla bir keşif denemesi yapılabilir.
4. **Oversee'nin bağlantısı çalışmayan 11 ilanı** için kiralama şirketi çekiminin yeniden çalıştırılması (yaklaşık 3,5 saat; 4 ilan kazanılır) ya da bir sonraki rutin çekime bırakılması.
5. **order.online** (DoorDash) doğrulaması geçmiyor; üç restoran (Siam Thai; Cajun Corner ve Big Bad Breakfast'ın sipariş menüleri) bu sayfadan okunamıyor.
6. Dalın main'e alınması.
