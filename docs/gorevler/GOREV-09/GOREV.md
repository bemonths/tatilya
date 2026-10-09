GÖREV-09 — v0.11.0 yayını, konaklama fiyat kapsamasının genişletilmesi ve restoran bilgilerinin işletme sitelerinden toplanması

BAĞLAM
GÖREV-08 kabul edildi. Kiralama şirketi fiyat toplayıcısı sağlam çalışıyor: 510 ilana vergiler ve zorunlu ücretler dahil toplam fiyat alındı. Ama fiyat örneği şirketlere göre dengesiz ve ilk videonun en çok merak edilecek mahallelerinde zayıf. Yaz 2027 penceresinde fiyatlı ilan sayısı: Seaside 5, Alys Beach 0, Gulf Place 3, Santa Rosa Beach 5, Blue Mountain Beach 7, Grayton Beach 8, Inlet Beach 11. Nedenleri GÖREV-08'in keşfinde belli: Seaside'da Homeowner's Collection (137 ilan) ve Cottage Rental Agency (59) eşlenemedi; Alys Beach'te alysbeach.com'un uyarlayıcısı yok; Grayton'da Ocean Reef (30) ve Grayt 30A (15); Blue Mountain'da Southern Resorts (29), oversee.us (24), 30a-beachgirls (20); Inlet Beach'te paradise30a (25); WaterColor'da 360blue (139) ve Sanders Beach Rentals (32). Ayrıca yapılandırılmış şirketlerde bile 184 ilanın Book>Direct bağlantısı eskimiş (404 ya da ilan sayfası değil).

Bu görevin iki asıl işi var:
A. Konaklama fiyat kapsamasını, özellikle zayıf mahallelerde genişletmek.
B. Restoranların fiyat seviyesi, çalışma saatleri, rezervasyon, çocuk menüsü gibi bilgilerini işletmelerin kendi sitelerinden toplamak. Ziyaretçi "nerede kalayım" sorusunun yanında "orada nerede, kaça yerim" diye soracak; şu an elimizde yalnız restoranın adı, mahallesi, mutfağı ve öğünleri var.

Ayrıca: v0.11.0 main'e alınacak; iki küçük eski düzeltme yapılacak; gerçek veritabanı güncellenecek.

Kullanıcı bu görev için main'e alma, etiket, gerçek veritabanını normal kullanımla güncelleme ve görevin gerektirdiği sitelere (kiralama şirketleri, restoranların siteleri ve menü platformları) tarayıcıyla girme iznini kendi mesajında açıkça veriyor. İnsan doğrulamasını kullanıcı yapacak.

KESİN SINIRLAR
- data/ yalnız Adım 7'de, CLAUDE.md kuralına göre (önce tam yedek, sonra uygulamanın normal kullanımı) değişir.
- main'e yalnız Adım 1'deki fast-forward ile dokun; yalnız Adım 1'deki etiketi koy.
- Rezervasyon yapma, ödeme ya da kişisel bilgi formu doldurma, hesap açma, giriş yapma. Fiyat yalnız sitenin herkese açık fiyat/müsaitlik gösteriminden alınır; sitenin kendi fiyat formu kullanılırsa yalnız tarih ve misafir sayısı girilir, rezervasyon adımına geçilmez.
- Proxy, VPN ya da IP değiştirme yok. Bir site bilerek engel koyduysa (doğrulama ekranı değil, engel sayfası) o siteye istek yapmayı bırak ve rapora yaz.
- Korumalı sitelerde (Cloudflare vb.) keşif de görünür tarayıcı oturumundan ve az istekle yapılır; ham HTTP isteğini art arda tekrarlama. (GÖREV-08'deki 360blue IP engeli böyle oldu.)
- Airbnb, Vrbo, Vacasa gibi platformlar kapsam dışı kalır. Restoranlarda Google, Yelp, Tripadvisor gibi yorum ve puan platformları kullanılmaz.
- Book>Direct istemci anahtarı hiçbir dosyaya, veritabanına, ham kayda ya da loga yazılmaz (mevcut kural).

TARAYICI VE İNSAN DOĞRULAMASI
Tarayıcı Adım 1b'deki yeni kuruluma göre kullanılır (gerçek Chrome, kalıcı profil, Playwright'in otomasyonla açtığı test tarayıcısı yok). Doğrulama ekranı çıkarsa kullanıcıya sohbette hangi sitede doğrulama beklendiğini yaz ve bekle; doğrulamayı kullanıcı yapar, sen çözmeye çalışmazsın; tamamlanınca aynı profil ve oturumla devam et. Uygulama içi tarayıcı site izni isterse kullanıcıdan onay iste. Korumalı sitelerde aynı siteye iki istek arasında en az 6 saniye bırak, aynı anda yalnız bir korumalı şirket okunsun; 403, 429 ya da engel sayfası gelirse o şirketi hemen durdur (yeniden deneme yok) ve kayda yaz.

==================================================
ADIM 1 — v0.11.0'ı main'e al ve etiketle
==================================================
Önce origin/gorev-08-konaklama-fiyat'ın son commit'i (9f2d65a) için GitHub Actions sonucunu kontrol et; başarısızsa önce düzelt, düzeltmeyi dala ekle ve bu adımı o commit'le yap. Sonra main'i bu dala git merge --ff-only ile getir ve push et; son commit'e "v0.11.0" açıklamalı etiketini koy (mesaj: "v0.11.0 — kiralama şirketlerinden konaklama fiyatları") ve push et. main ve etiket CI sonucunu rapora ekle. Güncel main'den "gorev-09-kapsama-restoran" dalını aç.

==================================================
ADIM 1b — Tarayıcı kurulumu (keşiften ve bütün tarayıcı işlerinden önce)
==================================================
Kullanıcının kararı (8 Ekim): Playwright'in otomasyonla açtığı test tarayıcısı kullanılmayacak. Şimdiki yöntemde tarayıcı Playwright'in launch_persistent_context komutuyla açılıyor; pencere "otomatik test yazılımı tarafından kontrol ediliyor" uyarısını ve otomasyon imzasını taşıyor, siteler de bu yüzden sık sık doğrulama istiyor. Kullanıcı başında olmadığında doğrulama kaçıyor ve iş atlanıyor. Yeni kurulum:
- Bilgisayarda kurulu gerçek Chrome (yoksa Edge) kullanılır. Playwright'in indirdiği Chromium ya da Chrome for Testing kullanılmaz.
- Tarayıcı Playwright'in launch komutuyla açılmaz; normal bir uygulama gibi işlem olarak başlatılır: bu iş için açılmış kalıcı bir kullanıcı veri klasörüyle (work/tarayici-profili/30a-studio; repoya girmez) ve yalnız 127.0.0.1'e açık uzaktan hata ayıklama portuyla. Kod tarayıcıya CDP üzerinden bağlanır (Playwright connect_over_cdp). Otomasyon bayrağı (--enable-automation) ve Playwright'in varsayılan otomasyon açılış ayarları yok. Kullanıcı aracısı, dil, saat dilimi ve pencere boyutu tarayıcının ve bilgisayarın kendi değerleridir; değiştirilmez.
- Bütün siteler için tek profil kullanılır (alan adı başına ayrı profil yok). Çerezler ve doğrulama sonucu profilde kalır; böylece aynı site her çekimde yeniden doğrulama istemez. Profil çekimler arasında korunur, silinmez. Tarayıcı zaten açıksa aynı profil ikinci kez açılmaz; uygulama açık tarayıcıya yeniden bağlanır.
- Bir kez doğrulama gösteren alan adı yapılandırmada "tarayıcıyla okunur" diye işaretlenir. Sonraki çekimlerde o siteye ayrı HTTP istemcisiyle hiç gidilmez; sayfalar ve fiyat istekleri doğrudan bu tarayıcı oturumundan (sayfanın içinden) yapılır. Doğrulama istemeyen siteler eskisi gibi kendi kimliğini söyleyen HTTP istemcisiyle okunur.
- Isınma: uzun bir çekimden önce "tarayıcıyla okunur" sitelerin her biri bu profilde ayrı bir sekmede açılır ve kullanıcıya sohbette liste halinde bildirilir; kullanıcı başındayken hepsini bir kerede doğrular, sonra çekim başlar. Çekim sırasında yine doğrulama çıkarsa o site sona bırakılır ve diğerleri devam eder; en sonda kullanıcıya bir kez daha haber verilir ve 15 dakika beklenir; yine olmazsa site atlanır ve kayda yazılır.
- Sınır (değişmedi): tarayıcının özelliklerini sahte değerlerle değiştiren gizlenme eklentileri ve parmak izi sahteciliği (stealth eklentileri, navigator özelliklerinin yamalanması, başka bir tarayıcıyı taklit etme), CAPTCHA çözme servisleri, proxy ya da IP değiştirme kullanılmaz. Tarayıcı, normal bir tarayıcı olarak olduğu gibi kullanılır. Doğrulamayı kullanıcı yapar.
- studio/sources/browser_verification.py'yi bu yönteme göre değiştir; CLAUDE.md'deki "Tarayıcı ve insan doğrulaması" paragrafını ve CALISMA_MANTIGI §4 madde 12–14'ü güncelle. Testler: tarayıcı başlatma komutunda otomasyon bayrağı olmaması, açık tarayıcıya yeniden bağlanma, "tarayıcıyla okunur" işaretinin kalıcı olması, sona bırakma ve zaman aşımı. Ayrı commit.
- Kurulumdan sonra floridastateparks.org'u (GÖREV-08'de otomasyonla açılan Chrome'a 403 veriyordu) bu tarayıcıda bir kez aç ve sonucu rapora yaz.
Görev başladıktan sonra bu bölüm eklendiyse: elindeki işi güvenli bir noktada durdur, bu adımı yap, sonra tarayıcı gerektiren işlere bu kurulumla devam et; tarayıcı gerektirmeyen ve tamamlanmış işleri yeniden yapma.

==================================================
ADIM 2 — Konaklama fiyat kapsaması: keşif
==================================================
Hedef: ilan sayısı yeten her mahallede Bahar tatili 2027 ve Yaz 2027 pencerelerinde en az 15 fiyatlı ilan. Tutmayan mahalle için neden rapora yazılır. Keşfi bu öncelik sırasıyla yap; her şirket için tek ilan örneğiyle fiyat yolunu, alanları ve kısıtları bul:

a) Seaside
- Homeowner's Collection (homeownerscollection.com, 143 ilan; ResCMS altyapısı çalışıyor, Book>Direct bağlantısı yalnız ana sayfaya gidiyor): şirketin kendi ilan listesini (site haritası ya da liste sayfaları) çıkar; her ilan için adres, daire numarası, yatak odası, banyo, kapasite ve varsa koordinat. Eşleme Adım 3a'daki adres kuralıyla yapılacak.
- Cottage Rental Agency (rentals.cottagerentalagency.com 82 ilan, cottagerentalagency.com 10): GÖREV-08'de bağlantı kurulamadı. Ana alan adını ve şirketin güncel kiralama sitesini tarayıcıda aç, fiyat yolunu bul. Site yalnız Seaside'da kiralama yaptığını kendisi söylüyor mu, kontrol et (Adım 3c için).
b) Alys Beach: alysbeach.com (Book>Direct'te 6 ilan; "Reseze API"). Fiyat yolunu bul. Sitenin kendi kiralama programında kaç ev olduğunu ve yalnız Alys Beach'te kiralama yaptığını söyleyip söylemediğini kontrol et (Adım 3c için).
c) WaterColor ve WaterSound: topluluğun kendisine ait resmî bir kiralama programı var mı, kontrol et. Sanders Beach Rentals (sandersbeachrentals.com, 32 ilan WaterColor'da) ilan sayfalarında yayımlanmış sezon kira tablosu var mı, bak.
d) Grayton Beach: Ocean Reef Resorts (oceanreefresorts.com, 96; Track izleri, bağlantılar genel listeye gidiyor) ve Grayt 30A Vacations (grayt30avacations.com, 40; ResCMS, bağlantılar ana sayfaya gidiyor): şirket ilan listesi + adresle eşleme.
e) Blue Mountain Beach, Santa Rosa Beach, Seagrove: Southern Resorts (southernresorts.com, 104). Sitenin kendi ilan sayfası tarih seçilince fiyatı POST /property/v3/quote servisinden alıyor; GÖREV-08'de istek biçimi bulunamadı. Bu kez sayfayı tarayıcıda aç, tarih seç ve sayfanın gönderdiği isteği tarayıcının ağ kaydından al (gövde, başlıklar, belirteçlerin sayfanın neresinden geldiği). İstek oturuma bağlı bir belirteç gerektiriyorsa toplayıcı ilan sayfasını açıp belirteci oradan alır. Bu da olmazsa fiyat, tarayıcı oturumu içinden sayfanın kendi fiyat gösterimiyle okunabilir (yalnız tarih ve misafir sayısı).
   Ayrıca henüz incelenmemiş, zayıf mahallelerde 5 ve daha fazla ilanı olan şirketler: yourfriendatthebeach.com (Blue Mountain 21), 30abeachstays.com (Santa Rosa Beach 14, Inlet 7), beachescapesrentals.com (Santa Rosa Beach 10), destinvacation.com (Blue Mountain 9). 30a-beachgirls.com (48; bağlantılar 404): şirketin güncel sitesini bul.
f) Inlet Beach: paradise30a.com (59; router altyapısı çalışıyor, bağlantılar sonuç listesine gidiyor): şirket ilan listesi + adresle eşleme.
g) 30a-vacay.com (54; bağlantılar 404): güncel siteyi bul.
h) Yapılandırılmış şirketlerdeki eskimiş bağlantılar (GÖREV-08: 120 ilan sayfa bulunamadı, 64 ilan bağlantısı ilan sayfasına gitmiyor, 7 ilanın bağlantısı yok): bunlar da adresle eşlenecek.
i) Cloudflare arkasındakiler:
- 360blue.com (256 ilan; WaterColor 139, WaterSound 44): GÖREV-08'de kullanıcının IP adresini engelledi. Görünür kalıcı profilli tarayıcıda ana sayfayı bir kez aç. Engel sayfası sürüyorsa 360blue bu görevde bırakılır; gerçek çekimden hemen önce bir kez daha bakılır, o kadar. Doğrulama ekranı çıkarsa kullanıcı doğrular; keşif en çok 40 istekle yapılır.
- oversee.us (185), realjoy.com (61), exclusive30a.com (29; WaterColor 15), oldseagrove.com (8): aynı yöntem; doğrulama ekranı çıkarsa kullanıcı doğrular; keşif site başına en çok 40 istek.
j) Fiyat formu olmayan ResCMS siteleri (Sanders Beach Rentals, funvacay.com, Coastal Blue Vacations): ilan sayfasında yayımlanmış sezon kira tablosu (tarih aralığı başına gecelik ya da haftalık kira) var mı, bak. Yalnız müsaitlik takvimi toplanmaz.

Bulguları docs/gorevler/GOREV-09/AJANS-KESFI-2.md'ye yaz (şirket başına: fiyat yolu, eşleme yolu, alanlar, örnek istek ve yanıt özeti, kısıtlar, sonuç). ajanslar.csv'nin güncel sürümüne iki sütun ekle: eşleme yolu (bağlantı / adres / konum / kendi envanteri / yok) ve bu görevdeki durum.

==================================================
ADIM 3 — Fiyat toplayıcısının genişletilmesi (agency-lodging-rates/2)
==================================================
3a. Adres ve konum ile eşleme. Book>Direct bağlantısı çalışmayan (404, ana sayfa, genel liste, bağlantı yok) ya da bağlantıyla eşleme yolu olmayan şirketlerde ilan, şirketin kendi ilan listesiyle şöyle eşlenir:
- Adres yöntemi: normalleştirilmiş sokak numarası + sokak adı birebir aynı (Street/St, Drive/Dr, East/E gibi kısaltmalar; "County Highway 30A", "CR 30A", "Scenic Highway 30A" ve "30A" aynı yol sayılır), daire numarası aynı (iki taraftan birinde daire numarası varsa ikisinde de aynı olmalı), yatak odası sayısı aynı ve bu koşulları sağlayan tek aday var. Birden fazla aday varsa eşleme yapılmaz ("belirsiz").
- Konum yöntemi (şirket sitesi adres vermiyorsa): koordinatlar arası mesafe en çok 15 m, yatak odası ve banyo sayısı aynı ve 50 m içinde bu değerlere sahip tek aday var. Aynı 15 m içinde birden fazla Book>Direct ilanı olan yerlerde (çok daireli binalar) konum yöntemi kullanılmaz.
- İlan adı tek başına ya da ana ölçüt olarak kullanılmaz; yalnız kayda yazılabilir.
- Her eşleşmenin yöntemi (bağlantı, adres, konum, kendi envanteri) saklanır ve arayüzde görünür. Şirketin ilan listesi her çekimde yeniden alınır ve ham kopyası SHA-256 ile saklanır.
- Doğrulama: adres ve konum yöntemlerinin her birinden rastgele 30 eşleşmeyi (yöntemde 30'dan az varsa hepsini) iki taraftaki ilan sayfasını açarak karşılaştır: başlık, adres, oda, banyo, kapasite, görünüyorsa fotoğraf. Sonucu eslesme-dogrulama.csv'ye yaz. Hatalı eşleşme bulunursa nedenini bul, kuralı sıkılaştır ve örneği yeniden kontrol et; hatasız olmayan yöntem gerçek çekimde kullanılmaz.

3b. Yeni uyarlayıcılar: keşifte fiyat yolu bulunan altyapılar için. Aynı altyapıyı kullanan şirketler aynı uyarlayıcıyı paylaşır; şirket → uyarlayıcı eşlemesi destinasyon yapılandırmasında kalır.

3c. Şirketin kendi envanteri. Tek bir topluluğa hizmet eden ve bunu sitesinde kendisi söyleyen resmî kiralama programlarında (ör. alysbeach.com; Cottage Rental Agency site böyle söylüyorsa) Book>Direct'te olmayan evler de şirketin sitesinden alınır. Kurallar:
- Mahalle, sitenin kendi beyanından gelir; site o topluluk dışındaki bir evi listeliyorsa o ev alınmaz. Adresler topluluğun sokaklarıyla uyumsuz görünürse rapora yaz.
- Her ev için şirket ilan kimliği, url, başlık, adres, oda, banyo, kapasite ve aynı pencerelerde fiyat.
- Book>Direct'le eşlenen bir evle aynı ev (aynı url ya da Adım 3a'daki adres kuralı) iki kez sayılmaz.
- Özetlerde bu evler "şirketin kendi envanteri" diye ayrı sayılır; mahalle özetinin etiketi kaç ilanın Book>Direct'ten, kaçının şirketin kendi envanterinden geldiğini söyler.

3d. Yayımlanmış kira tabloları. Fiyat formu olmayan ama ilan sayfasında sezon kira tablosu yayımlayan sitelerde, pencerenin düştüğü sezonun kirası "yayımlanmış kira (vergi ve ücret hariç)" diye ayrı alana ve ayrı durumla yazılır. Bu değerler 7 gecelik toplam fiyat ortancalarına karıştırılmaz; özette ayrı sütun olur ("yayımlanmış haftalık kira ortancası, vergi ve ücret hariç").

3e. Misafir sayısı her fiyat satırında saklanır. Varsayılan 2 yetişkin; şirket bazında farklı değer destinasyon yapılandırmasından gelir (Adım 4).

3f. Tarih pencereleri: destinasyon yapılandırmasına "Sonbahar 2027" (2027-10-16 → 2027-10-23, Cumartesi–Cumartesi) ekle. Sonbahar 2026 kalır; geçmişe düşünce zaten atlanıyor. (GÖREV-08'de Sonbahar 2026 son dakika penceresi oldu, müsait payı %7–40; mevsim fiyatı için Sonbahar 2027 kullanılacak.) Book>Direct konaklama toplayıcısı da aynı pencereleri kullandığı için o da yeni pencereyi arar. Bir şirket o tarih için henüz fiyat açmamışsa bu "fiyat yok" diye kaydedilir; rapora pencere başına oranı yaz.

3g. Korumalı siteler için tempo kuralı (yukarıdaki doğrulama bölümü) toplayıcıda uygulanır.

3h. Özet: mevcut özete eşleme yöntemine göre kapsama, kendi envanteri ve yayımlanmış kira sütunları eklenir. Eşlenemeyen ilanların nedenleri şirket bazında kalır.

Şema 12, uygulama 0.12.0 (Adım 5 ile ortak); migration mevcut kurallarla. Testler (fixture ve MockTransport; canlı ağ yok): adres normalleştirme ve eşleme (birebir, daire farkı, oda farkı, belirsiz aday, kısaltmalar, 30A yol adları), konum eşlemesi (15 m, çok daireli bina, tek aday), adın tek başına eşleme yapmaması, her yeni uyarlayıcının ayrıştırması, kendi envanteri (topluluk dışı evin alınmaması, çift sayılmama), yayımlanmış kira (toplama karışmaması), misafir sayısının saklanması, korumalı site temposu ve 403/429'da durma, yeni pencere, migration ve geri alma. Belge: docs/M11-KONAKLAMA-FIYATLARI.md güncellenir (eşleme yöntemleri, kendi envanteri, yayımlanmış kira, video dili).

==================================================
ADIM 4 — Misafir sayısı kontrolü
==================================================
Fiyatlar 2 yetişkin için soruluyor; büyük evlerde bazı siteler kişi başı ücret ekleyebilir. Her şirketten en az 3 ilan (4 ve daha fazla odalı; yoksa şirketin en büyük ilanları) seç ve Yaz 2027 penceresinde iki kez sor: 2 yetişkin ve "yatak odası × 2 yetişkin" (ilanın kapasitesini aşmadan). Sonucu misafir-sayisi-kontrol.csv'ye yaz (şirket, ilan, oda, kapasite, iki toplam, fark ve hangi kalemde). Kural: bir şirketin örneklerinden herhangi birinde toplam değişirse o şirketin bütün sorguları "yatak odası × 2 yetişkin, kapasiteyi aşmadan" ile yapılır ve bu, destinasyon yapılandırmasına yazılır; değişmezse 2 yetişkin kalır. Özet etiketinde misafir sayısı kuralı söylenir.

==================================================
ADIM 5 — Restoran bilgilerinin işletme sitelerinden toplanması
==================================================
Girdi: güncel restoran listesi (Visit South Walton; ad, mahalle, adres, telefon, web sitesi, mutfak, öğünler).

5a. Book>Direct restoran servisi: Book>Direct betiğindeki restaurants servisini kısa bir kontrolle değerlendir (30A'da kaç kayıt, hangi alanlar: saat, fiyat, menü bağlantısı, rezervasyon). İşe yarıyorsa ikincil kaynak olarak, etiketiyle kullanılır. Anahtar saklanmaz.

5b. İşletmenin sitesi: Visit South Walton'daki web sitesi. Yoksa ya da çalışmıyorsa resmî siteyi web aramasıyla bul; site yalnız adresi ya da telefonu Visit South Walton kaydıyla tutuyorsa kabul edilir. İşletmenin kendi yayımladığı platform sayfaları (Toast, Square, Popmenu, BentoBox, SpotHopper, ChowNow, Olo ve benzeri menü ve sipariş sayfaları) işletmenin kendi kaynağı sayılır. Sosyal medya sayfaları yalnız giriş yapmadan okunabiliyorsa kullanılır.

5c. Toplanacak bilgiler. Her değer için kaynak url, erişim zamanı, ham kopyanın SHA-256'sı ve yöntem etiketi saklanır (yapısal veri, sayfa metni, PDF metni, platform verisi, görüntüden okundu). Sitenin söylemediği alan NULL ya da "bilinmiyor" kalır; söylenmeyen şey "yok" yazılmaz.
- Site durumu: çalışıyor / bulunamadı / site işletmenin "kalıcı olarak kapandı" ya da "sezon için kapalı" dediğini söylüyor / başka işletmeye ait.
- Menüler: url, biçim (html, pdf, görüntü, platform) ve türü (kahvaltı, brunch, öğle, akşam, çocuk, içecek, tatlı, happy hour, genel).
- Menü kalemleri: bölüm başlığı, kalem adı, fiyat metni ve sayı. "Market price" gibi fiyatlar sayıya çevrilmez. Birden fazla boy ya da porsiyon fiyatı olan kalemde en düşük fiyat kullanılır (kural belgeye yazılır).
- Ana yemek fiyatı: menü bölüm başlıkları bir sınıflama tablosuyla (repoda CSV; başlık → ana yemek, başlangıç, salata/çorba, tatlı, içecek, çocuk, yan ürün, diğer) ayrılır; tabloyu sen hazırlar ve gözden geçirirsin. Ana yemek fiyatlarının ortancası, en düşüğü, en yükseği ve kalem sayısı, işletmenin en kapsamlı ana öğün menüsünden hesaplanır (akşam, yoksa öğle, yoksa brunch, yoksa kahvaltı) ve hangi menüden hesaplandığı yazılır.
- Fiyat seviyesi (bizim sınıflamamız, öyle etiketlenir): ana yemek ortancası $15'in altı "$", $15–25 "$$", $25–40 "$$$", $40 ve üstü "$$$$". En az 5 ana yemek fiyatı yoksa seviye hesaplanmaz.
- Çalışma saatleri: sitenin yazdığı metin aynen, ayrıştırılabiliyorsa gün gün; sezon notları korunur. Etiket: "işletmenin sitesinde <tarih> tarihinde yazan".
- Rezervasyon: çevrim içi (platform adı ve bağlantı: OpenTable, Resy, Tock, SevenRooms vb.) / telefonla / alınmıyor / bekleme listesi / bilinmiyor. Yalnız sitenin beyanından ya da sitedeki platform bağlantısından.
- Çocuk menüsü: evet / bilinmiyor ("hayır" yalnız site söylüyorsa).
- Açık hava oturma, su kenarı ya da manzara, köpek dostu: evet / bilinmiyor ("hayır" yalnız site söylüyorsa).
Görüntü olarak yayımlanmış ya da metni okunamayan menüleri sen okursun; okuduğun değerler repoda bir gözden geçirme dosyasına (CSV) "görüntüden okundu" etiketiyle ve ham dosyanın SHA-256'sıyla yazılır, toplayıcı bu dosyayı okur (çekim yeniden çalıştırılabilir kalır).

5d. Mimari: işletme sitesini okuma, menü bulma, yapısal veri ve rezervasyon platformu tanıma genel çekirdekte; restoran listesinin hangi destinasyon kaynağından geldiği destinasyon tarafında. Aynı siteye istekler sıralı ve en az 2 saniye arayla; doğrulama ekranında Adım 2'deki yöntem. Toplayıcı adı ve sürümü senin kararın; CLAUDE.md'deki "Mimari sınır" sorusunu cevapla ve belgeye yaz.

5e. Arayüz: Restoranlar sekmesinde fiyat seviyesi, ana yemek ortancası, rezervasyon ve çocuk menüsü sütunları ve filtreleri; restoran ayrıntısında bütün alanlar kaynaklarıyla, menü bağlantıları ve saatler; mahalle özeti (fiyat seviyesine göre restoran sayısı, ana yemek ortancalarının ortancası, çevrim içi rezervasyon ve çocuk menüsü olan restoran sayısı, bilgisi bulunamayan restoran sayısı).

5f. Testler (fixture; canlı ağ yok): yapısal veriden saat ve menü bağlantısı, rezervasyon platformu tanıma, HTML ve PDF menüden fiyat ayrıştırma, bölüm sınıflaması, en düşük boy kuralı, fiyat seviyesi sınırları ve 5'ten az kalemde hesaplanmaması, "market price", kapandı beyanı, gözden geçirme dosyasının okunması, eksik alanların NULL kalması, bir sitenin hatasında diğerlerinin devam etmesi, iptal, atomik geri alma, migration.

5g. Belge: docs/M12-RESTORAN-BILGILERI.md (kaynaklar, alanlar, sınıflama tablosu, fiyat seviyesi kuralı, sınırlar, video dili). Video dili: "işletmenin kendi sitesindeki menüye göre (erişim tarihi) ana yemeklerin ortancası yaklaşık $X" kullanılabilir; "en iyi", "en popüler", "en ucuz" gibi sıralamalar ve sitede olmayan bilgi kullanılmaz.

==================================================
ADIM 6 — İki küçük düzeltme
==================================================
- Restoran toplayıcısının adres ayrıştırması: "Canopy Road Café" kaydında ikinci adres satırına "Inlet Beach, FL" yazılıyor, şehir ve eyalet boş kalıyor (GÖREV-01 raporu). Posta kodu olmayan şehir satırını doğru ayrıştır; toplayıcının sürümünü artır; test ekle.
- Gerçek veritabanının kopyasında National Weather Service kaynak kaydının yöntem alanına bak; hâlâ "Belirlenecek" yazıyorsa v12 geçişinde düzelt.

==================================================
ADIM 7 — Gerçek ortam ve teslim
==================================================
1. Geçici klasörde canlı deneme (work/gorev-09/temp-data): restoran toplayıcısı ve restoran zenginleştirmesi; konaklama toplayıcısı; fiyat toplayıcısının yeni sürümü (gerçek çekimden önce aynı sitelere iki kat yük binmesin diye bu denemede yalnız yeni eklenen şirketler ve eşleme yolları çalıştırılabilir). Süre, istek sayısı, şirket ve restoran bazında sonuç; Restoranlar sekmesi ve fiyat bölümünün ekran görüntüleri.
2. Migration denemesi gerçek verinin kopyasında (v11 → v12).
3. Gerçek veritabanı, CLAUDE.md kuralına göre: data/ tam yedeği; uygulamayı gerçek veriyle aç; sırayla restoran toplayıcısı, restoran zenginleştirmesi, konaklama toplayıcısı, fiyat toplayıcısı (bütün şirketler); kapat; satır sayıları, integrity_check ve foreign_key_check.
4. Belgeler: CALISMA_MANTIGI.md, README.md, docs/DEVIR/05 ve 02'nin güncel durum satırları, M11, M12. Tam test takımı yerelde art arda en az 3 kez geçmeli.

TESLİM
docs/gorevler/GOREV-09/ altına: GOREV.md (work/gorevler/GOREV-09.md'nin kopyası), RAPOR.md, AJANS-KESFI-2.md, ajanslar.csv (güncel), eslesme-dogrulama.csv, misafir-sayisi-kontrol.csv, konaklama-fiyat-ozet.csv (gerçek veritabanından mahalle × pencere; eşleme yöntemi ve kendi envanteri ayrımıyla; oda sayısına göre ortancalar), restoranlar.csv (restoran başına toplanan alanlar, fiyat seviyesi ve kaynak url'leri), restoran-mahalle-ozet.csv, menu-bolum-siniflari.csv ve ekran görüntüleri.
RAPOR.md Türkçe ve sade: her adımın sonucu, main ve etiketin konumu, CI sonuçları, test sayıları, tarayıcı kurulumunun sonucu (kaç sitede doğrulama istendi, ısınmadan sonra çekim sırasında yeniden doğrulama çıktı mı), keşfin sonucu (şirket başına), eşleme doğrulaması, misafir sayısı kontrolü, kapsamanın önce/sonra karşılaştırması (mahalle × pencere fiyatlı ilan sayısı; 15 hedefini tutmayan mahalleler ve nedeni), mahalle başına fiyat özetleri, restoran kapsaması (kaç restoranda site, menü, fiyat seviyesi, saat, rezervasyon bulundu; bulunamayanların nedenleri), mahalle başına restoran özeti, gerçek veritabanının öncesi/sonrası, beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-09 bitti, dal gorev-09-kapsama-restoran, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
