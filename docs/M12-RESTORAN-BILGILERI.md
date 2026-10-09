# M12 — Restoran bilgileri (işletmelerin kendi siteleri)

Tarih: 8 Ekim 2026 · Görev: GÖREV-09 · Dal: `gorev-09-kapsama-restoran` · Uygulama `0.12.0` · Şema `12` · Toplayıcı `restaurant-sites/1`

## Durum

Toplayıcı, şema, arayüz ve testler hazır. Önce work/ altında restoran listesinin kopyasıyla canlı pilotlar, sonra geçici klasörde uygulama üzerinden deneme, en son tam yedekten sonra gerçek veritabanında çekim yapıldı; sayılar ve kapsama `docs/gorevler/GOREV-09/RAPOR.md`, restoran tablosu `docs/gorevler/GOREV-09/restoranlar.csv`, mahalle özeti `restoran-mahalle-ozet.csv`.

## Amaç

Restoran dizini (Visit South Walton, M4) ad, adres, telefon, mutfak ve web sitesi veriyor; ziyaretçinin karar vermesi için gereken fiyat düzeyi, saatler, rezervasyon ve çocuk menüsü gibi bilgiler dizinde yok. Bu toplayıcı o bilgileri **işletmenin kendi sitesinden** (ve işletmenin kendi yayımladığı menü/sipariş platformu sayfalarından) okur; her değeri kaynağıyla saklar.

## Kaynaklar

- **Girdi:** destinasyonun son başarılı restoran dizini çekimi (`restaurant_records`: ad, web sitesi, telefon, adres; mahalleler `restaurant_regions`'tan). Liste destinasyon tarafından gelir.
- **İşletmenin sitesi:** dizindeki web sitesi. Dizinde site yoksa ya da çalışmıyorsa resmî site web aramasıyla bulunur ve **gözden geçirilmiş site dosyasına** yazılır (`studio/destinations/thirty_a_restaurant_sites.csv`: `external_id, name, site_url, kanit, kaynak, kontrol_tarihi, menu_urls`). Yalnız sitede dizindeki adres ya da telefon görünüyorsa kabul edilir; kanıt sütununda hangisinin tuttuğu yazar. Aynı dosyada `site_url` boş bırakılıp yalnız `menu_urls` (noktalı virgülle) yazılabilir: bir kişinin işletmenin kendi sitesinde bulduğu ama toplayıcının menü sanmadığı belge bağlantıları (ör. dosya adında "menu" geçmeyen menü görselleri); site dizindeki site olarak kalır.
- **Platform sayfaları:** işletmenin kendi yayımladığı menü ve sipariş sayfaları (Toast, Square, Popmenu, BentoBox, SpotHopper, ChowNow, Olo, Clover, Menufy, DoorDash Storefront, SinglePlatform, BeyondMenu, TouchBistro, Owner.com vb.) işletmenin kendi kaynağı sayılır; yöntem etiketi "platform verisi".
- **Sosyal medya:** yalnız giriş yapmadan okunabiliyorsa. Facebook ve Instagram sayfaları giriş istediği için okunmaz; site durumu `social_login`.
- **Kullanılmayanlar:** Google, Yelp, Tripadvisor gibi yorum ve puan platformları (görev kuralı). Book>Direct ön yüzünün `restaurants` servisi (Adım 5a) incelendi: 30A çevresi için 18 kayıt; alanlar ad, mutfak türü, adres, telefon, OpenTable rezervasyon ve menü bağlantısı, OpenTable'ın `$`/`$$` fiyat işareti, koordinat; saat yok. Kayıtların çoğu 30A dışında (Miramar Beach/Sandestin) ve hepsi OpenTable'dan; işletmenin kendi beyanı olmadığı ve 30A restoranlarının küçük bir kısmını kapsadığı için kullanılmadı. İstemci anahtarı yalnız bellekte okundu, hiçbir yere yazılmadı.
- **Görüntü menüler:** görüntü olarak yayımlanmış ya da metni okunamayan menüleri bir kişi okur; değerler **gözden geçirme dosyasına** yazılır (`studio/destinations/thirty_a_menu_readings.csv`: `external_id, menu_url, raw_sha256, menu_type, menu_title, section, name, price_text, price, price_rule, okundu`). Her satır görüntünün SHA-256'sına bağlıdır; toplayıcı yalnız aynı SHA'lı belge gelirse okumayı kullanır (görüntü değişirse okuma kullanılmaz, menü "okunmadı" kalır). Kurallar: `menu_type` "menü değil" → fotoğraf ya da logo, menü sayılmaz; adı boş tek satır → menü okundu ama fiyat yazmıyor. Şarap ve bira listeleri kalem kalem yazılmadı; yemekler, kokteyller ve tek fiyatlı içecekler yazıldı. Yöntem etiketi "görüntüden okundu".

## Toplanan bilgiler

Her değer için kaynak url, erişim zamanı (`fetched_at`), ham kopyanın SHA-256'sı ve yöntem etiketi (yapısal veri, sayfa metni, PDF metni, platform verisi, görüntüden okundu, bağlantı) saklanır. Sitenin söylemediği alan yazılmaz (bilinmiyor); "hayır" yalnız site söylüyorsa yazılır.

| Alan | Değerler | Nereden |
|---|---|---|
| Site durumu | çalışıyor · bulunamadı · kalıcı olarak kapandı · sezon için kapalı · başka işletmeye ait (park edilmiş alan adı) · ulaşılamadı · sosyal medya (giriş gerekiyor) · site yok | ana sayfanın yanıtı ve metni ("permanently closed", "closed for the season", "domain for sale" gibi beyanlar) |
| Menüler | url, biçim (html, pdf, görüntü, platform), tür (kahvaltı, brunch, öğle, akşam, çocuk, içecek, tatlı, happy hour, genel), durum (okundu, kalem yok, görüntü okunmadı, hata) | ana sayfadaki menü bağlantıları, menü merkez sayfalarındaki alt bağlantılar ve görüntüler, yapısal verideki `hasMenu` |
| Menü kalemleri | bölüm başlığı, kalem adı, fiyat metni, sayı, fiyat kuralı, bölüm sınıfı ve sınıfın dayanağı | sayfa metni, PDF metni, platform sayfası, görüntü okuması |
| Çalışma saatleri | sitenin yazdığı metin aynen; ayrıştırılabiliyorsa gün gün | yapısal veri (`openingHoursSpecification`) ya da saat/iletişim sayfasının metni |
| Rezervasyon | çevrim içi (platform adı ve bağlantı) · telefonla · alınmıyor · bekleme listesi | sitedeki platform bağlantısı (OpenTable, Resy, Tock, SevenRooms, Toast Tables, resOS, Tablein, Yelp) ya da sitenin cümlesi |
| Çocuk menüsü | evet (çocuk menüsü ya da çocuk bölümü var) · hayır (yalnız site söylüyorsa) | menü türü/bölümü ya da sayfa metni |
| Açık hava oturma, su kenarı/manzara, köpek dostu | evet · hayır (yalnız site söylüyorsa) | sayfa metni |
| Sitenin kendi fiyat işareti | sitenin yazdığı `$$` gibi değer | yapısal veri `priceRange` (bizim seviyemizden ayrı tutulur) |

Saatlerin etiketi: "işletmenin sitesinde <tarih> tarihinde yazan". Sezon notları metinde korunur.

## Menü fiyatları ve kurallar

- **Fiyat ayrıştırma:** satır sonundaki fiyat (`Grouper 34`, `Calamari ........ $14`), ayrı satırdaki fiyat (ad üstte, açıklama, sonra fiyat), başlık olarak yazılmış yemek adı ve hemen altındaki fiyat. Eklemeler ("add shrimp 6", "sub…", "extra…") kalem sayılmaz. Saat, telefon, ons/adet gibi birimler fiyat sayılmaz. Besin değeri tablosu olan belgeler ("Nutrition Facts", "Total Fat (g)" gibi sütun başlıkları) fiyat menüsü sayılmaz; 6 ya da daha çok sayı içeren tablo satırları ve yanında sayı olan menü başlıkları ("DINNER MENU 23") kalem sayılmaz.
- **En düşük boy kuralı:** birden fazla boy ya da porsiyon fiyatı olan kalemde (ör. "cup 9 | bowl 14", "4 Bone 17.45 / 6 Bone 21.95 / Full Rack 36.25") **en düşük fiyat** kullanılır; fiyat metni aynen saklanır, kural `lowest`.
- **Piyasa fiyatı:** "Market price", "MKT", "MP" sayıya çevrilmez; kural `market`, sayı boş.
- **Bölüm sınıflaması:** bölüm başlıkları gözden geçirilmiş tabloyla sınıflanır (`studio/sources/menu_sections.csv`; teslimde kopyası `docs/gorevler/GOREV-09/menu-bolum-siniflari.csv`). Sınıflar: ana yemek, başlangıç, salata/çorba, tatlı, içecek, çocuk, yan ürün, diğer. Tablo sırayla okunur, ilk eşleşen satır kazanır (çocuk satırları önce: "Kids Burgers" çocuk; "dessert cocktails" içecek; "pizza pies" ana yemek, "pies" tatlı). `tam=1` satırları yalnız başlığın tamamı olduğunda geçerlidir ("Red", "White" gibi). Başlık sınıf vermezse (başlık yok ya da tabloda yok) kalemin kendi adı aynı tabloyla denenir (dayanak `name`). Çocuk menüsündeki sınıfsız/ana yemek kalemleri çocuk, içecek menüsündeki sınıfsız kalemler içecek sayılır (dayanak `menu`). Her kalemin sınıfı ve dayanağı (`section` / `name` / `menu`) saklanır.
- **Ana yemek sayıları:** işletmenin en kapsamlı ana öğün menüsünden hesaplanır. Sıra: akşam, yoksa öğle, yoksa **genel** (öğün belirtmeyen tek menü), yoksa brunch, yoksa kahvaltı; aynı türde birden fazla menü varsa en çok ana yemek fiyatı olan. Görev "akşam, öğle, brunch, kahvaltı" sırasını veriyordu; restoranların çoğu öğün belirtmeyen tek bir menü yayımladığı için "genel" menü öğleden sonra eklendi (karar yöneticiye bırakıldı, RAPOR.md). Ortanca, en düşük, en yüksek ve kalem sayısı okunurken hesaplanır ve hangi menüden (tür ve url) hesaplandığı gösterilir.
- **Fiyat seviyesi (bizim sınıflamamız, öyle etiketlenir):** ana yemek ortancası $15'in altı `$`, $15–25 `$$`, $25–40 `$$$`, $40 ve üstü `$$$$` (alt sınır dahil: tam $15 `$$`). **En az 5 ana yemek fiyatı** yoksa seviye hesaplanmaz. Sitenin kendi `priceRange` değeri ayrı alandır, seviyeye karışmaz.

## Toplama akışı

1. Dizindeki her restoranın sitesi (ya da gözden geçirilmiş site) okunur; aynı siteye istekler sıralı ve **en az 2 sn arayla**, farklı restoranlar 6 iş parçacığıyla yan yana. Bir sitenin hatası diğerlerini durdurmaz; hata o restoranın kaydına yazılır.
2. Ana sayfadan yapısal veri (JSON-LD: saatler, `priceRange`, `acceptsReservations`, `hasMenu`), menü bağlantıları (en çok 10 belge) ve saat/iletişim sayfaları (en çok 3) okunur. PDF menülerin metni `pypdf` ile çıkarılır.
3. **Tarayıcıyla ikinci okuma:** düz HTTP isteğine doğrulama sayfası (Cloudflare "Just a moment" vb.) gösteren ya da isteği reddeden (403/429) siteler, daha önceki bir çekimde doğrulama gösterdiği için "tarayıcıyla okunur" diye işaretlenmiş siteler (`browser_hosts`; bunlara düz HTTP isteği hiç yapılmaz) ve menüsünü JavaScript ile çizen siteler, bilgisayarda kurulu gerçek Chrome (yoksa Edge) ile okunur. Tarayıcı Playwright'in test tarayıcısı değildir: normal bir uygulama gibi, tek kalıcı profille (`work/tarayici-profili/30a-studio`, repoya girmez) başlatılır ve kod ona CDP üzerinden bağlanır (`studio/sources/browser_verification.py`). Sayfa başına en çok 5 sn ağ sakinliği beklenir; aynı siteye iki sayfa arasında en az 3 sn (doğrulama gösteren sitelerde 6 sn). Doğrulama sayfası 20 sn içinde kendiliğinden geçmezse o restoran sona bırakılır, diğerleri okunur; en sonda bekleyen siteler ayrı sekmelerde açılır, iş bunları tek liste halinde gösterir ve kullanıcı için **15 dakika** beklenir; doğrulanan siteler okunur, doğrulanmayanlar "doğrulama tamamlanmadı" notuyla atlanır. Doğrulamayı kullanıcı yapar; toplayıcı çözmeye çalışmaz, tarayıcıyı gizleyen ya da taklit eden ayar kullanmaz. Engel sayfası gelirse o siteye istek bırakılır. Tarayıcı penceresi kapatılırsa kalan restoranlar ilk okumalarıyla kalır, çekim sürer. Dizindeki sayfa 404 verirse sitenin ana sayfası bir kez okunur (notta yazar); birden fazla restoranın paylaştığı sayfa bir çekimde bir kez istenir.
4. Görüntü menüler ve metinsiz PDF'ler gözden geçirme dosyasında aynı SHA'lı okuma varsa okunur, yoksa "görüntü okunmadı" diye kaydedilir. Metni olan ama fiyat içermeyen PDF "kalem yok" kaydedilir.
5. Bütün ham yanıtlar gzip ile, SHA-256'larıyla ve `manifest.json` ile saklanır; kayıtlar tek işlemde (atomik) yazılır, hata olursa hiçbiri yazılmaz.

## Şema (v12)

`restaurant_site_snapshots` (çekim başına; girdi restoran çekimi, sayılar) · `restaurant_sites` (restoran başına site durumu, kaynağı, son url, HTTP durumu, not) · `restaurant_facts` (alan, değer, ayrıntı, bağlantı, veri, kaynak url, erişim zamanı, SHA, yöntem) · `restaurant_menus` (url, biçim, tür, başlık, platform, bağlantı veren sayfa, erişim zamanı, SHA, yöntem, durum, mesaj, kalem sayısı) · `restaurant_menu_items` (bölüm, ad, fiyat metni, fiyat, fiyat kuralı, bölüm sınıfı, sınıf dayanağı, yöntem). Fiyat kuralı `market` ise fiyat boş olmak zorundadır (CHECK).

## Arayüz

Restoranlar sekmesi: fiyat seviyesi, ana yemek ortancası, rezervasyon ve çocuk menüsü sütunları ve filtreleri; restoran ayrıntısında bütün alanlar kaynaklarıyla (url, erişim tarihi, yöntem), menü bağlantıları, ana yemek sayılarının hangi menüden hesaplandığı ve saatler; mahalle özeti (fiyat seviyesine göre restoran sayısı, ana yemek ortancalarının ortancası, çevrim içi rezervasyon ve çocuk menüsü olan restoran sayısı, bilgisi bulunamayan restoran sayısı). Fiyat seviyesinin yanında "bizim sınıflamamız" notu durur.

## Mimari sınır

CLAUDE.md sorusu: "bu generic mi, yoksa destinasyona özel mi?"

- **Generic (çekirdek, `studio/sources/restaurant_sites.py`):** işletme sitesini okuma, menü bulma, PDF metni, yapısal veri, rezervasyon ve menü platformu tanıma, fiyat ayrıştırma, bölüm sınıflama tablosu (`menu_sections.csv`, İngilizce menü başlıkları; destinasyona bağlı değil), fiyat seviyesi kuralı, tarayıcıyla ikinci okuma, ham kayıt ve atomik yazım. Bu dosyada 30A'ya, Visit South Walton'a ya da tek bir restorana özel kural yok.
- **Destinasyona özel:** restoran listesinin hangi kaynaktan geldiği (destinasyonun son restoran dizini çekimi; 30A için `south-walton-restaurants`), gözden geçirilmiş site dosyası ve görüntü okuma dosyası (`studio/destinations/thirty_a_restaurant_sites.csv`, `thirty_a_menu_readings.csv`; yolları `thirty_a.py` profilinde) ve kaynak kaydının tohumu (`thirty_a.py` → `SEEDS`). Yeni bir destinasyon kendi restoran dizinini ve kendi gözden geçirme dosyalarını getirir; çekirdek değişmez.

## Sınırlar

- Site bir bilgiyi yazmıyorsa alan boş kalır; "bulunamadı" "yok" demek değildir. Fiyat seviyesi hesaplanamayan restoranın nedeni site durumundan, site notundan ve menü kayıtlarının mesajlarından görülür (site yok, menü yok, görüntü menü okunmadı, 5'ten az ana yemek fiyatı, doğrulama tamamlanmadı vb.); teslimdeki restoranlar.csv bu nedeni ayrı sütunda verir.
- Menü fiyatları sitenin yayımladığı menüdendir; restoranın o gün uyguladığı fiyat olmayabilir. `fetched_at` sitenin güncellenme zamanı değildir; menünün tarihi ancak menü kendisi yazıyorsa bilinir.
- Bölüm sınıflaması bir tabloya dayanır; tabloda olmayan başlıklar "diğer" kalır ve ana yemek sayısına girmez. Başlıksız menülerde kalem adı denenir; bu bir türetmedir ve dayanağı (`name`) saklanır.
- Görüntü okuması bir kişinin okumasıdır; değerler görüntünün SHA'sına bağlıdır ve görüntü değişince kullanılmaz.
- Doğrulama isteyen sitelerde kullanıcı 15 dakikalık bekleme içinde doğrulamazsa o restoran tarayıcıyla okunamaz.

## Video dili

Kullanılabilir: "işletmenin kendi sitesindeki menüye göre (erişim tarihi) ana yemeklerin ortancası yaklaşık $X", "sitesinde OpenTable üzerinden rezervasyon bağlantısı var", "sitesinde çocuk menüsü yayımlıyor", "sitesinde yazan saatlere göre (tarih) Pazartesi kapalı". Fiyat seviyesi kullanılırsa "bizim sınıflamamıza göre" denir. Kullanılmaz: "en iyi", "en popüler", "en ucuz" gibi sıralamalar ve sitede olmayan bilgi; bulunamayan bir olanak için "yok".
