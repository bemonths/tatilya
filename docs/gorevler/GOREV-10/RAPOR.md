# GÖREV-10 Raporu — v0.12.0 yayını, restoran fiyat seviyesi gözden geçirmesi, aylık konaklama fiyatları, güncelleme zamanı göstergesi ve günlük ihtiyaç ölçüleri

Tarih: 9–10 Ekim 2026 · Dal: `gorev-10-aylik-gunluk` · Uygulama `0.13.0` · Şema `13`

## Kısaca

- **Adım 1 tamam:** main `fdd59f6`'ya (GÖREV-09) getirildi, `v0.12.0` etiketi konuldu; main ve etiket CI'ı başarılı.
- **Adım 2 tamam — restoranlar:** fiyat seviyesi olan restoran **33 → 66** (138 restoranın; 33 yeni, 3 değişti, 30 aynı, hiçbiri kaybolmadı). Seviyesi olmayan 72 restoranın her birinin yanında tek satırlık neden yazıyor (en sık: 19 "ana yemek sunmuyor", 9 "yalnız sosyal medya sayfası"). $8 altındaki 87 "ana yemek" tek tek incelendi; 79'u ek, içecek, yan ürün ya da başlangıç çıktı.
- **Tarayıcı kuralı değişti (kullanıcı kararı, 9 Ekim 2026):** tarayıcı artık yalnız bir site doğrudan isteği engellediğinde açılıyor; açılır pencereleri kapatıyor; ısınma yalnız doğrulama bekleyen sekmeleri açık bırakıyor. Tarayıcı gerektirmeden okunabilen gömülü menüler (SinglePlatform, ohbz) için yeni okuyucular yazıldı; bu kural yüzünden hiçbir restoranın seviyesi kaybolmadı.
- **Adım 3 tamam — aylık fiyatlar ve güncelleme göstergesi:** pencere kuralı (çekim ayından sonraki 12 ayın 15'ini içeren hafta), sorgudan pencereye gün, mevsim grupları, aynı hafta karşılaştırması; ana ekranda "Güncelleme zamanı gelenler" bölümü ve "Zamanı gelenleri başlat" düğmesi. Zamanlanmış görev yok.
- **Adım 4 tamam — günlük ihtiyaç:** OpenStreetMap'ten 43 nokta + zincirin sitesinden 1 (Target Pier Park); ilanlardan kuş uçuşu uzaklıklar mahalle başına ortanca ve "1 mil içinde" payıyla.
- **Adım 5:** realjoy bu tarayıcıda doğrulamayı geçirmedi (yapılandırılmadı); 360blue hâlâ engelli; Oversee'nin düzeltilmiş liste okumasıyla **4 ilan yeni eşleşti** (174 → 178).
- **Adım 6 tamam:** geçici denemeler, gerçek DB kopyasında v12 → v13 geçişi, tam yedekten sonra gerçek veride restoran dizini, işletme siteleri, OpenStreetMap; uygulama yeniden açılıp **düğmeyle** konaklama ve kiralama şirketi fiyatları alındı (ilk aylık anlık görüntü, 12 pencere). Kontroller temiz.
- **İlk aylık anlık görüntü:** kiralama şirketlerinin sitelerinde **1.080 ilana** en az bir ayda fiyat (GÖREV-09'da 5 pencereyle 1.066); her ay her mahallede fiyatlı ilan var (Alys Beach'te şirketin kendi envanteriyle). Book>Direct'in kendi fiyatı yine yalnız ilk üç ayda ve 8 ilanda.

## Adım 1 — v0.12.0'ı main'e alma ve etiketleme

| | |
|---|---|
| Önce | `origin/gorev-09-kapsama-restoran` son commit `fdd59f6`, dal CI'ı başarılı |
| main | `git merge --ff-only origin/gorev-09-kapsama-restoran` ile `fdd59f6d417d7ba345de61e8931207b3791bce25`'e getirildi ve push edildi |
| Etiket | açıklamalı `v0.12.0` ("v0.12.0 — konaklama fiyat kapsaması, gerçek tarayıcı kurulumu ve restoran bilgileri") `fdd59f6`'yı gösteriyor, push edildi |
| main CI | çalıştırma 37919592454 — başarılı |
| Etiket CI | çalıştırma 37919601312 — başarılı |
| Görev dalı | güncel main'den `gorev-10-aylik-gunluk` açıldı |

## Adım 2 — Restoran fiyat seviyesi: elle gözden geçirme

Ayrıntılı yöntem `docs/M12-RESTORAN-BILGILERI.md` ("Fiyat seviyesi gözden geçirmesi"); tablolar `restoranlar.csv`, `restoran-seviye-once-sonra.csv` (önceki seviye ve neden, yeni seviye ve neden, yöntem), `restoran-mahalle-ozet.csv`.

**2a — Her restoran tek tek.** Seviyesi olmayan 105 restoranın siteleri tek tek açıldı (sosyal medya, kalıcı/sezon kapalı, başka işletme ve sitesiz olanlar dışında). Yapılanlar:
- Yeni okuyucular: schema.org menüleri (Popmenu siteleri: menü sayfada geç yükleniyor ama yapısal veride tam), Toast sipariş sayfası verisi, ohbz menü tasarımları (iki biçim), SinglePlatform menü sayfaları, menü platformu iframe'leri, ARIA sekmeli menüler (BentoBox), tek çerçeveli siteler, park edilmiş alan adları.
- Tablo/ayrıştırıcı düzeltmeleri: satır başı yıldızı, ondalık virgül, "Ad – açıklama" satırları, karışık büyük-küçük harfli bölüm başlıkları, bölüm notları, tek başına "MKT", "ADD EGG +2 | ADD PORK BELLY +4" gibi ek notları (başlık sayılmıyor), "ADD-ONS" gibi ek bölümleri (yan ürün), "/food" ve "/eats" sayfaları; bölüm tablosuna tapas, küçük tabak, sabit menü ve yeni başlıklar (`menu_sections.csv`, 359 satır).
- Gözden geçirilmiş site dosyasına (`thirty_a_restaurant_sites.csv`, 71 satır) toplayıcının bulamadığı menü bağlantıları, "ana yemek sunmuyor" işaretleri (19 yer) ve sitede okunan seviye notları yazıldı.
- Elle okunan menüler ("elle okundu", 107 kalem: Pescado/The Courtyard, 3 Sons BBQ, Farm & Fire, The Citizen, Bud & Alley's Restaurant) ve görüntü menüleri ("görüntüden okundu"; bu görevde Cajun Corner'ın iki görüntüsü, The Wine Bar at WaterColor'ın akşam menüsü ve Blue Mountain Bakery'nin güncel kafe menüsü) menüde yazdığı gibi, belgenin SHA-256'sına bağlı yazıldı. Blue Mountain Bakery'nin sitesindeki 22.3.2024 tarihli eski kafe menüsü ve 2026 fırın ön-sipariş listesi okunmadı.
- Ulaşılamayan siteler yeniden denendi; Bud & Alley's Taco Bar'ın sunucusu doğrudan isteği yanıtsız kapatıyordu, bu da engel sayılıp tarayıcıyla okundu ($).

**2b — Kurallar.** Ekler hiçbir zaman ana yemek değil; içecek ve "Kids …" adları kendi sınıfında; tapas menüsünde "küçük tabak ortancası" ayrı (6 restoranda: 87 Central Square $14, Amici $16, La Crema $11, Surfing Deer $18, The Bay $12,5, The Wine Bar $15); prix fixe/tadım menüsünde "sabit menü fiyatı" ayrı (bu çekimde fiyatlı sabit menü bulunmadı; Roux 30A'nın tadım menüsünde fiyat yok); kahve, tatlı, dondurma ve içecek yerleri "ana yemek sunmuyor". İnceleyen kişinin `seviye_notu` kararı seviyeden önce gelir (Black Bear Bar Room: dizindeki sitesi fırının sitesi, okunan sipariş menüsü fırınındır; Bar Room'un menüsü yok → seviye yok).

**$8 altı ana yemek kontrolü.** GÖREV-09 gerçek verisinde $8'in altında 87 "ana yemek" vardı. Tek tek incelendi: 29 yan ürün/ek, 18 içecek, 16 diğer (sayfa satırı, başlık), 12 başlangıç, 3 tatlı, 1 çocuk; 8'i gerçekten $8 altı ana yemek (taco tabakları, kruvasan sandviçleri) olarak kaldı. Kararlar `thirty_a_menu_item_classes.csv`'de. Etkisi (yalnız bu düzeltme, GÖREV-09 verisi üzerinde):

| Restoran | Önce | Ana yemek / ortanca (önce) | Sonra | Ana yemek / ortanca (sonra) |
|---|---|---|---|---|
| Angelina's Pizzeria and Pasta | $$ | 96 / $15.0 | $$ | 83 / $16.5 |
| Beachy Bean Coffee Co. | $ | 9 / $7.0 | — | 4 / $13.0 |
| Blue Mountain Bakery | — | 1 / $3.0 | — | 0 / — |
| Bruno's Pizza | $$ | 6 / $17.0 | $$ | 5 / $17.0 |
| Chiringo Grayton | $$ | 18 / $16.99 | $$ | 16 / $18.24 |
| LaCO | $$ | 19 / $19.0 | $$ | 17 / $19.0 |
| Local Catch Bar & Grill | $$ | 21 / $20.0 | $$ | 19 / $21.0 |
| Prema Organic Cafe | $ | 14 / $12.75 | $ | 13 / $13.25 |
| Redd's Pub | $ | 6 / $13.49 | $ | 5 / $13.99 |
| Scratch Biscuit Kitchen | $ | 28 / $8.0 | $ | 16 / $12.0 |
| Seagrove Village Market Cafe | $$ | 31 / $16.0 | $$ | 29 / $16.0 |
| Shades Bar & Grill | $$ | 24 / $17.5 | $$ | 23 / $18.0 |
| Ticheli's Pizza | $ | 30 / $13.0 | $$ | 21 / $19.0 |
| VKI Japanese Steakhouse & Sushi Bar | $$ | 100 / $15.0 | $$ | 86 / $16.0 |
| Wild Bill's Beach Dogs | $ | 12 / $13.0 | $ | 11 / $13.0 |

Bu tablo yalnız $8 düzeltmesinin etkisidir; gerçek çekimdeki son değerler başka okumalarla da değişti (ör. Beachy Bean yeni menü okumasıyla $, 16 ana yemek).

**Değişen seviyeler (3):** Ticheli's Pizza $ → $$ (içecekler ana yemekten çıktı; ortanca $13 → $21); The Daytrader $$ → $$$ (GÖREV-09'da üç salata yanlış bölüm başlığı yüzünden ana yemek sayılmıştı; doğru bölümlerle ortanca $25,5, sınır $25); Fish Out of Water $$ → $$$ (SinglePlatform sayfasındaki yedi menü artık ayrı okunuyor; seviye akşam menüsünden, ortanca $30).

**2c — Neden dağılımı (seviyesi olmayan 72 restoran):** 19 ana yemek sunmuyor · 9 yalnız sosyal medya sayfası (giriş gerekiyor) · 5 sitedeki menüde ana yemek fiyatı yazmıyor · 4 beşten az fiyatlı ana yemek · 4 alan adı başka işletmede/satılık · 3 sitede menü bulunamadı · 2 menü yalnız JavaScript ile çiziliyor (Havana Beach Bar, Summer Kitchen Café; ikisinin de GÖREV-09'da menüsü yoktu) · 2 alan adı bir siteye bağlı değil · 2 alan adı çözülmüyor · kalan 22'si tekil nedenler (sezon için kapalı, yangın sonrası geçici kapalı, tadım menüsü, yemek kamyonu, order.online doğrulaması geçmedi, Cloudflare engel sayfası vb.; tam liste `restoranlar.csv` `seviye_yok_nedeni`).

**Mahalle özeti:**

| Mahalle | Restoran | $ | $$ | $$$ | $$$$ | Seviyeli | Ana yemek ortancalarının ortancası | Çevrim içi rezervasyon | Çocuk menüsü | Bilgi bulunamadı |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dune Allen | 2 | 0 | 1 | 1 | 0 | 2 | $21.25 | 0 | 2 | 0 |
| Gulf Place | 6 | 0 | 1 | 3 | 0 | 4 | $25.25 | 0 | 3 | 1 |
| Santa Rosa Beach | 28 | 1 | 8 | 1 | 0 | 10 | $19.0 | 1 | 7 | 9 |
| Blue Mountain Beach | 8 | 2 | 1 | 0 | 0 | 3 | $13.99 | 2 | 2 | 1 |
| Grayton Beach | 15 | 0 | 6 | 3 | 0 | 9 | $20.0 | 1 | 8 | 2 |
| WaterColor | 5 | 1 | 1 | 3 | 0 | 5 | $25.0 | 0 | 4 | 0 |
| Seaside | 19 | 3 | 3 | 3 | 1 | 10 | $19.5 | 3 | 6 | 4 |
| Seagrove | 17 | 2 | 2 | 2 | 2 | 8 | $24.5 | 4 | 5 | 6 |
| WaterSound | 3 | 0 | 1 | 0 | 0 | 1 | $17.0 | 0 | 0 | 0 |
| Seacrest | 8 | 0 | 2 | 1 | 0 | 3 | $21.0 | 0 | 2 | 3 |
| Alys Beach | 7 | 0 | 1 | 1 | 2 | 4 | $32.5 | 3 | 4 | 0 |
| Rosemary Beach | 12 | 0 | 0 | 2 | 1 | 3 | $35.0 | 1 | 5 | 1 |
| Inlet Beach | 11 | 0 | 2 | 2 | 0 | 4 | $22.0 | 1 | 3 | 2 |

**İstenen beş mahallenin restoranları tek tek:**

**Rosemary Beach** (12 restoran)

| Restoran | Önce (GÖREV-09) | Şimdi | Ana yemek (adet · ortanca) | Seviye yoksa nedeni |
|---|---|---|---|---|
| Amavida Coffee in Rosemary Beach | — | — | — | ana yemek sunmuyor (kahve dükkânı) |
| CK Feed & Supply Provisions & Gifts | — | — | — | ana yemek sunmuyor (şarap ve provizyon dükkânı) |
| Cowgirl Kitchen Restaurant & Bar | — | — | — | işletmenin sitesinde Rosemary Beach'te bu adla restoran ya da menü yok |
| Creative Crepes | — | — | — | yalnız sosyal medya sayfası var (giriş gerekiyor) |
| Edward's Fine Food & Wine | — | $$$ | 8 · $35 |  |
| Gallion's | — | — | — | sitedeki menüde yemek fiyatları yazmıyor (yalnız ek malzeme fiyatları var) |
| Havana Beach Bar & Grill | — | — | — | menü fiyatları sayfanın düz HTML'inde yok (JavaScript ile çiziliyor olabilir); tarayıcı yalnız engelde kullanıldığı için okunmadı |
| La Crema-Tapas and Chocolate | — | $$$ | 5 · $25 |  |
| Pescado | — | — | 3 · $49 | 5'ten az fiyatlı ana yemek (3) |
| Restaurant Paradis | — | $$$$ | 9 · $47 |  |
| Summer Kitchen Café | — | — | — | menü fiyatları sayfanın düz HTML'inde yok (JavaScript ile çiziliyor olabilir); tarayıcı yalnız engelde kullanıldığı için okunmadı |
| The Courtyard at Pescado | — | — | 3 · $49 | 5'ten az fiyatlı ana yemek (3) |

**Seaside** (19 restoran)

| Restoran | Önce (GÖREV-09) | Şimdi | Ana yemek (adet · ortanca) | Seviye yoksa nedeni |
|---|---|---|---|---|
| 87 Central Square Wine Bar | — | $$ | 5 · $20 |  |
| Amavida Coffee in Seaside | — | — | — | ana yemek sunmuyor (kahve dükkânı) |
| Barefoot BBQ | — | — | — | alan adı artık bir siteye bağlı değil |
| Bud & Alley's Pizza Bar + Trattoria | $$ | $$ | 22 · $19 |  |
| Bud & Alley's Restaurant | — | $$$$ | 8 · $43.5 |  |
| Bud & Alley's Taco Bar | $ | $ | 9 · $9 |  |
| Crepes Du Soleil | — | — | — | sitedeki menüde ana yemek fiyatları yazmıyor (yemek kamyonu) |
| Dawson's Yogurt & Fudge Works | — | — | — | ana yemek sunmuyor (frozen yogurt ve fudge) |
| Frost Bites | — | — | — | sitede menü bulunamadı |
| Great Southern Cafe | — | $$$ | 18 · $28 |  |
| It's Heavenly | — | — | — | ana yemek sunmuyor (dondurma ve tatlı) |
| Modica Market | — | — | — | ana yemek sunmuyor (gurme market) |
| Mr. Gyro Hero | — | — | — | yalnız sosyal medya sayfası var (giriş gerekiyor) |
| Pickles Beachside Grill | — | $$ | 20 · $17 |  |
| The Daytrader Tiki Bar and Restaurant | $$ | $$$ | 16 · $25.5 |  |
| The MeltDown on 30A | $ | $ | 9 · $12 |  |
| The Shrimp Shack | — | $$$ | 17 · $25 |  |
| Wild Bill's Beach Dogs | $ | $ | 10 · $13.5 |  |
| Wild Nectar 30A | — | — | — | yalnız sosyal medya sayfası var (giriş gerekiyor) |

**WaterColor** (5 restoran)

| Restoran | Önce (GÖREV-09) | Şimdi | Ana yemek (adet · ortanca) | Seviye yoksa nedeni |
|---|---|---|---|---|
| Fish Out of Water | $$ | $$$ | 12 · $30 |  |
| Pizza by the Sea in WaterColor | $$$ | $$$ | 49 · $25 |  |
| Scratch Biscuit Kitchen | $ | $ | 7 · $12 |  |
| The Perfect Pig - WaterColor | — | $$$ | 12 · $36 |  |
| The Wine Bar at WaterColor | — | $$ | 11 · $21 |  |

**Alys Beach** (7 restoran)

| Restoran | Önce (GÖREV-09) | Şimdi | Ana yemek (adet · ortanca) | Seviye yoksa nedeni |
|---|---|---|---|---|
| Caliza | — | — | — | menü yayımlanmıyor (Alys Beach sahip ve misafir havuz restoranı) |
| Charlie's Delights | — | — | — | ana yemek sunmuyor (donut ve tatlı) |
| Fonville Press | $$ | $$ | 8 · $17 |  |
| George's at Alys Beach | — | $$$$ | 9 · $40 |  |
| NEAT Bottle Shop and Tasting Room | — | — | — | ana yemek sunmuyor (şişe dükkânı ve şarap barı) |
| Raw & Juicy | $$$ | $$$ | 5 · $25 |  |
| The Citizen | — | $$$$ | 9 · $45 |  |

**Grayton Beach** (15 restoran)

| Restoran | Önce (GÖREV-09) | Şimdi | Ana yemek (adet · ortanca) | Seviye yoksa nedeni |
|---|---|---|---|---|
| AJ's Grayton Beach | $$ | $$ | 57 · $18 |  |
| Bad Ass Coffee | — | — | — | ana yemek sunmuyor (kahve dükkânı) |
| Black Bear Bar Room | — | — | 19 · $16 | sitede Bar Room menüsü yok |
| Black Bear Bread Co. | — | $$ | 19 · $16 |  |
| Borago | $$$ | $$$ | 7 · $29 |  |
| Chanticleer Eatery | — | $$ | 19 · $22 |  |
| Chiringo Grayton | $$ | $$ | 16 · $16.99 |  |
| Crackings | — | $$ | 21 · $18 |  |
| Grayton Corner Cafe | — | — | — | alan adı başka bir işletmede ya da satılık |
| Grayton Seafood Company | — | $$$ | 8 · $29.95 |  |
| Hibiscus Coffee & Guesthouse | — | — | — | pansiyon sitesi; kafeyi Raw & Juicy işletiyor, sitede menü yok |
| Hurricane Oyster Bar & Grill | $$ | $$ | 20 · $20 |  |
| Pickle Factory | — | — | — | web sitesi yok |
| Roux 30A | — | — | — | yalnız tadım menüsü; sitede yemek listesi ve fiyat yok |
| The Red Bar | — | $$$ | 6 · $29.5 |  |

**Tarayıcı kararı (kullanıcı, 9 Ekim 2026).** Kullanıcı deneme sırasında tarayıcının çok sayıda siteyi tek tek açtığını ve order.online'da açılır pencerelerin kapanmadığını gördü; "tarayıcı yalnız engellenme durumunda kullanılsın" dedi. Yapılanlar: her sayfa önce doğrudan istenir (daha önce doğrulama göstermiş siteler dahil); yalnız doğrulama sayfası ya da ret (403/429, yanıtsız kapanan bağlantı) gösteren alan adının sayfaları tarayıcıyla okunur, restoranın diğer sayfaları doğrudan kalır; "menü JavaScript ile çiziliyor" artık tarayıcı nedeni değil. Bu yüzden seviyesi kaybolacak üç restoranın (Local Catch, Scratch Biscuit Kitchen, Fish Out of Water) menüsü SinglePlatform'un doğrudan okunabilen sayfasından alındı; seviyeleri korundu. Tarayıcıyla ikinci okumaya giden restoran 43'ten 36'ya indi; kalanların hepsinde site doğrudan isteğe gerçekten doğrulama sayfası ya da ret döndürüyor (Cloudflare, Toast sipariş sayfaları, order.online). Açılır pencereler okumadan önce Escape ve pencerenin kendi "Kapat" düğmesiyle kapatılıyor (sipariş, konum ya da çerez seçimi yapılmıyor); ölçüldüğünde pencere okumayı engellemiyordu (Pizza by the Sea sayfasından pencere açıkken de 87 kalem okunmuştu). CLAUDE.md, CALISMA_MANTIGI §4 ve M12 güncellendi.

## Adım 3 — Aylık fiyat pencereleri ve güncelleme zamanı göstergesi

- **3a Pencere kuralı** (destinasyon yapılandırması, bizim varsayımımız): çekim ayından sonraki 12 ayın her biri için ayın 15'ini içeren Cumartesi–Cumartesi haftası; 21 günden yakın pencere atlanır, 13. ay eklenir; etiket "Temmuz 2027 · 10–17 Temmuz". Book>Direct ve kiralama şirketi toplayıcıları aynı kuralı kullanıyor ve kuralı çekim kaydına yazıyor; eski çekimlerin pencereleri olduğu gibi duruyor.
- **3b** Fiyat tabloları ay sütunlu; her pencerede sorgudan ilk geceye gün sayısı ("sorgudan 36 gün sonra"); mevsim grupları okuma anında, "bizim gruplamamız" etiketiyle.
- **3c Aynı hafta karşılaştırması:** iki çekimde de fiyatlı aynı ilanlar, giriş-çıkış tarihleri aynı pencereler; mahalle × pencere ortanca değişim ve eşleşen ilan sayısı; etiket "aynı evlerin aynı hafta için <tarih1> ve <tarih2> tarihlerinde sorgulanan fiyatları; bizim hesabımız".
- **3d Güncelleme göstergesi:** aralıklar Book>Direct ve kiralama şirketleri 1 ay, restoran dizini ve işletme siteleri 3 ay; diğerleri tanımsız. Ana ekranda "Güncelleme zamanı gelenler" (son başarılı çekim, aralık, durum ve nedeni, tahmini süre) ve "Zamanı gelenleri başlat" düğmesi: önce uygulamanın kendi yedeği (`data/backups/toplu-*`, son 6 saklanır), sonra sırayla (konaklama → kiralama; dizin → işletme siteleri), girdisi tamamlanmayan adım atlanır, "Toplu çalıştırmayı durdur" ile durdurulur. Görevde öngörülmeyen bir ayrıntı: gerçek veride konaklama ve kiralama 8–9 Ekim'de çekildiği için 1 aylık aralık dolmamıştı ve düğme hiçbir şey başlatmayacaktı. Bu yüzden "pencere kuralı son çekimden sonra değişti" nedeni eklendi: sabit pencerelerle yapılmış son çekim aylık seriye ait değil, toplayıcı "zamanı geldi" görünür. Bir toplu çalıştırma için tahmin, son çekimin süresinden (pencere sayısı değiştiyse oranla) hesaplanıyor: düğmenin yanında **~9 sa 54 dk** yazdı, gerçekte **8 sa 45 dk** sürdü (Book>Direct 63 dk, kiralama 7 sa 42 dk). CLAUDE.md "Gerçek veriyi güncelleme kuralı"na görevdeki cümle eklendi; README'ye Türkçe bölüm yazıldı.
- **3e Testler:** pencere kuralı (21 gün sınırı, 13. ay, ay sonu, yıl geçişi, 15'i Cumartesi), iki çekim arası eşleşmiş karşılaştırma (API üzerinden iki aylık çekimle), mevsim grupları, zamanı gelme hesabı ve nedenleri, toplu başlatmanın sırası, bağımlılıkla atlama, iptal, uygulama açılırken yarıda kalanın işaretlenmesi, yedek alma ve son 6'nın saklanması, 409 durumları; arayüz testleri.

## Adım 4 — Günlük ihtiyaç ve arabasız tatil ölçüleri

Belge `docs/M13-GUNLUK-IHTIYAC.md`; tablolar `gunluk-ihtiyac-mahalle.csv`, `gunluk-ihtiyac-noktalar.csv`, `gunluk-ihtiyac-zincir-kontrolu.csv`.

- **Kaynak:** OpenStreetMap, Overpass API; çekim başına tek sorgu (10 sn, 1 istek), ham yanıt SHA-256'sıyla; OpenStreetMap verisi 2026-10-09T17:36:21Z. Atıf arayüzde ve belgede: "© OpenStreetMap katkıcıları, ODbL".
- **Noktalar:** süpermarket ve market 16 + 1 (zincirin sitesinden), küçük market 16, eczane 5, acil sağlık 2, bisiklet kiralama 4. Bölge kutusu 30A'nın iki ucundaki ilanlar için Miramar Beach'in doğu ucunu ve Panama City Beach'in batı ucunu da içeriyor.
- **Zincir çapraz kontrolü:** Walmart'ın 3 mağazası ve Aldi'nin 1 mağazası OpenStreetMap'te de var; **Target Pier Park** OpenStreetMap'in süpermarket listesinde yok → "zincirin kendi sitesi" kaynağıyla eklendi; Whole Foods ve Trader Joe's'un bölgede mağazası yok (en yakın Whole Foods Destin'de, kutunun ~2 km batısında); **Publix** (bu bilgisayara yalnız "International" sayfası gösteriyor), **Winn-Dixie** (403 Akamai) ve **The Fresh Market** (mağaza listesi yüklenmiyor) okunamadı, bu zincirlerin OpenStreetMap noktaları doğrulanamadı. OpenStreetMap'te olup zincirin sitesinde kapalı görünen mağaza bulunmadı.
- **Ölçüler (kuş uçuşu; mahalle ortancası · 1 mil içindeki ilan payı):**

| Mahalle | İlan | Restoran (dizin) | Süpermarket | Küçük market | Eczane | Acil sağlık | Bisiklet kiralama | Halka açık plaj erişimi |
|---|---:|---:|---|---|---|---|---|---|
| Dune Allen | 114 | 2 | 2.32 mi · %2 | 0.75 mi · %78 | 1.20 mi · %43 | 3.90 mi · %0 | 2.85 mi · %2 | 0.11 mi · %97 |
| Gulf Place | 31 | 6 | 1.72 mi · %0 | 0.61 mi · %84 | 0.16 mi · %81 | 5.05 mi · %0 | 1.71 mi · %0 | 0.18 mi · %97 |
| Santa Rosa Beach | 246 | 28 | 1.31 mi · %32 | 0.93 mi · %60 | 1.73 mi · %40 | 5.72 mi · %0 | 1.53 mi · %25 | 0.27 mi · %82 |
| Blue Mountain Beach | 194 | 8 | 0.29 mi · %75 | 0.30 mi · %83 | 1.75 mi · %15 | 6.78 mi · %0 | 0.30 mi · %75 | 0.28 mi · %88 |
| Grayton Beach | 86 | 15 | 1.79 mi · %7 | 0.54 mi · %93 | 3.91 mi · %0 | 8.91 mi · %0 | 1.56 mi · %7 | 0.26 mi · %95 |
| WaterColor | 259 | 5 | 0.42 mi · %100 | 1.58 mi · %3 | 4.06 mi · %0 | 10.78 mi · %0 | 0.38 mi · %86 | 0.65 mi · %100 |
| Seaside | 221 | 19 | 0.15 mi · %93 | 1.58 mi · %1 | 4.23 mi · %0 | 10.92 mi · %0 | 0.46 mi · %93 | 0.34 mi · %95 |
| Seagrove | 498 | 17 | 1.32 mi · %26 | 0.66 mi · %67 | 3.28 mi · %0 | 12.37 mi · %0 | 1.90 mi · %12 | 0.12 mi · %97 |
| WaterSound | 165 | 3 | 2.54 mi · %3 | 2.90 mi · %1 | 2.97 mi · %0 | 15.33 mi · %0 | 3.13 mi · %2 | 0.96 mi · %56 |
| Seacrest | 301 | 8 | 0.44 mi · %54 | 3.34 mi · %0 | 3.28 mi · %1 | 18.08 mi · %0 | 0.39 mi · %54 | 0.56 mi · %97 |
| Alys Beach | 7 | 7 | 0.75 mi · %100 | 3.68 mi · %0 | 3.61 mi · %0 | 17.74 mi · %0 | 0.69 mi · %100 | 1.05 mi · %29 |
| Rosemary Beach | 166 | 12 | 0.25 mi · %92 | 2.77 mi · %1 | 2.71 mi · %1 | 18.68 mi · %0 | 0.30 mi · %91 | 0.37 mi · %93 |
| Inlet Beach | 101 | 11 | 0.75 mi · %70 | 2.28 mi · %1 | 2.22 mi · %1 | 19.15 mi · %0 | 0.81 mi · %63 | 0.16 mi · %93 |

  Plaj notu (etiketin parçası): ölçü yalnız ilçenin 53 halka açık erişimine göre; Seaside, WaterColor, Alys Beach, Rosemary Beach gibi toplulukların misafirlerine açık özel erişimleri dahil değil (Alys Beach ve WaterSound'un yüksek değerleri bundan). Koordinatı olmayan ilan yok. Restoranlar için koordinat üretilmedi; sayı dizinden.
- **Sınır:** OpenStreetMap'te bölgede acil hizmet etiketli yalnız 2 nokta var (Sacred Heart Hospital on the Emerald Coast ve adsız bir hastane, ikisi de Miramar Beach tarafında); bu yüzden acil sağlık uzaklıkları doğu uçta 18–19 mile çıkıyor. Bu OpenStreetMap'in eksikliği olabilir; videoda "OpenStreetMap'e göre" denmeli ya da başka kaynakla doğrulanmalı.

## Adım 5 — Kiralama şirketlerinde küçük işler

- **realjoy.com (61 ilan):** yeni tarayıcıyla bir kez açıldı: Cloudflare doğrulama sayfası. Isınmada kullanıcı doğruladı ama site her seferinde yeniden doğrulama istedi (döngü); kullanıcının kendi Chrome'unda site sorunsuz açılıyor. Altyapısına bakılamadı, **yapılandırılmadı**.
- **360blue:** toplu çalıştırmadan hemen önce bir kez bakıldı: "Sorry, you have been blocked" (403). Bu çekimde yok.
- **Oversee:** GÖREV-09'da şirket listesi okunamadığı için çekim yarıda kalmıştı. Bu kez tamamlandı: 185 ilanın 178'i eşlendi (bağlantı 174 + **adres 4 yeni**), fiyatlı ilan 167 → 171. Korumalı site olduğu için tarayıcıdan, istekler arasında 6 sn ile okunuyor; 185 ilan × 13 istek yaklaşık 4,5 saat sürdü (kiralama adımının çoğu).

## Adım 6 — Gerçek ortam

**6.1 Geçici klasörde deneme** (`work/gorev-10/temp-data`, gerçek DB'nin salt okunur kopyası):

| Deneme | Süre | İstek | Sonuç |
|---|---|---|---|
| İşletme siteleri (eski tarayıcı kuralıyla) | iptal edildi (yeni kural geldi) | — | — |
| İşletme siteleri (yeni kural) | 50,8 dk | 879 | 60 seviye (SinglePlatform okuyucusundan önce) |
| İşletme siteleri, son kodla, uygulama dışında | 46,4 dk | 887 | 66 seviye |
| OpenStreetMap | 10 sn | 1 | 44 nokta |
| Toplu çalıştırma: Book>Direct 12 pencere | 66 dk | 1.662 | 2.389 ilan |
| Toplu çalıştırma: kiralama (Oversee + 2 şirket) | durduruldu | — | Oversee 26 dk'da 17/185 ilan; deneme klasöründe 4–5 saat süreceği için toplu çalıştırma düğmeyle durduruldu (iptal sınaması da oldu) |
| Kiralama, 2 küçük şirket, 12 pencere | 8,7 dk | 394 | 23 ilan eşlendi, 22 fiyatlı; mevsim ve aynı hafta tabloları çalıştı |

**6.2 Migration denemesi** (gerçek DB'nin `work/` kopyası): v12 → v13; eski bütün tabloların satırları aynı; 7 yeni tablo; kaynak 15 → 16 (OpenStreetMap); `integrity_check` ok, `foreign_key_check` boş.

**6.3–6.4 Gerçek veritabanı:**
1. Uygulama kapalıyken `data/` tam yedeği: `work/yedek/20261009-1851/` (21.453 dosya, 695 MB; kopya ve kaynak SHA-256 ile doğrulandı).
2. Uygulama gerçek veriyle açıldı; v12 → v13 (uygulamanın yedeği `data/backups/studio-v12-ab66a150d6054b4b9b783df2a2c3c146.sqlite3`).
3. Isınma: 25 sitenin 22'si doğrudan açıldı; **order.online**, **outcastseafood.com** ve **realjoy.com** doğrulama istedi, kullanıcıya tek liste halinde bildirildi. outcastseafood.com kullanıcı Google'dan gidince açıldı; order.online ve realjoy her doğrulamadan sonra yeniden doğrulama istedi.
4. Restoran dizini (100 sn, 138 restoran), işletme siteleri (47 dk, 889 istek; order.online için en sonda 15 dk beklendi, geçmedi), OpenStreetMap (10 sn). Uygulama kapatıldı.
5. Uygulama yeniden açıldı; ana ekrandaki "Güncelleme zamanı gelenler" bölümü doğru göründü (`ekran/guncelleme-zamani-gelenler.png`: konaklama ve kiralama "zamanı geldi — pencere kuralı son çekimden sonra değişti", restoranlar "güncel, sonraki 9 Ocak 2027"). 360blue'ya bakıldı (engelli); oversee.us ve exclusive30a.com doğrulamasız açıldı.
6. "Zamanı gelenleri başlat" arayüzden tıklandı. **İlk basış:** uygulama yedeğini aldı (`toplu-20261009-173951-…`), Book>Direct 6 dakika sonra durdu: Seaside'ın Aralık araması sayfalar arasında 173 ilan okunurken 174 bildirdi (arama sırasında bir ilan eklendi); toplayıcı bir kez yeniden deneyip kısmi sonucu kaydetmeden durdu, kiralama adımı "girdisi tamamlanmadı" diye atlandı. 12 pencereyle arama sayısı 2,4 kat arttığı için bu daha olası hale gelmişti; yeniden okuma 20 sn arayla 3 denemeye çıkarıldı, uygulama yeniden başlatıldı. **İkinci basış:** yedek `toplu-20261009-174826-…`; Book>Direct 63 dk (1.655 istek, 2.389 ilan), kiralama şirketleri 7 sa 42 dk (21.129 istek); toplu çalıştırma "2/2 toplayıcı tamamlandı" (`ekran/toplu-calistirma-bitti.png`). Uygulama kapatıldı.

**Gerçek DB öncesi / sonrası:**

| | Önce | Sonra |
|---|---|---|
| Şema | 12 | 13 |
| `integrity_check` | ok | ok |
| `foreign_key_check` | boş | boş |
| Çekim (`source_runs`) | 22 | 28 (6 yeni: restoran dizini, işletme siteleri, OpenStreetMap, Book>Direct başarısız + başarılı, kiralama) |
| Kaynak | 15 | 16 |
| restoran menü kalemi / menü / site | 15.318 / 634 / 276 | 24.482 / 1.003 / 414 |
| konaklama arama satırı / ilan | 29.965 / 7.167 | 58.228 / 9.556 |
| kiralama fiyat sorgusu / ilan satırı | 7.751 / 4.778 | 21.323 / 7.167 |
| günlük ihtiyaç noktası / zincir kontrolü | — | 44 / 10 |
| toplu çalıştırma | — | 2 (biri başarısız, biri tamam) |
| `browser_hosts` | 22 | 28 |

Hiçbir tabloda satır azalmadı; `data/` içinde -wal/-shm kalmadı. Tam karşılaştırma `work/gorev-10/gercek-oncesi.json` / `gercek-sonrasi.json` (repoda değil).

## İlk aylık anlık görüntü (12 pencere, sorgu 9–10 Ekim 2026)

Tablolar `konaklama-fiyat-ozet.csv` (mahalle × ay, Book>Direct ve kiralama), `konaklama-mevsim-ozet.csv`, `konaklama-ayni-hafta.csv`. Kiralama şirketlerinde: 2.389 Book>Direct ilanının 1.131'i şirket sitesinde bulundu (bağlantı 1.119, adres 5, konum 7), **1.080'ine en az bir ayda fiyat** alındı; Alys Beach'in kendi envanterindeki 73 evin hepsine fiyat; yayımlanmış kira 21 ilan. Fiyatlı mahalle 12/13 (Alys Beach yalnız kendi envanteriyle).

**Fiyatlı ilan sayısı (Book>Direct ilanı + şirketin kendi envanteri):**

| Mahalle | Kas 26 | Ara 26 | Oca 27 | Şub 27 | Mar 27 | Nis 27 | May 27 | Haz 27 | Tem 27 | Ağu 27 | Eyl 27 | Eki 27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dune Allen | 30 | 46 | 35 | 36 | 45 | 43 | 45 | 43 | 46 | 53 | 50 | 43 |
| Gulf Place | 8 | 14 | 12 | 12 | 11 | 13 | 14 | 14 | 15 | 15 | 15 | 12 |
| Santa Rosa Beach | 31 | 51 | 46 | 34 | 44 | 46 | 48 | 48 | 51 | 53 | 53 | 42 |
| Blue Mountain Beach | 50 | 59 | 52 | 36 | 55 | 61 | 65 | 68 | 67 | 68 | 66 | 63 |
| Grayton Beach | 18 | 35 | 26 | 22 | 28 | 33 | 34 | 34 | 31 | 40 | 37 | 39 |
| WaterColor | 37 | 50 | 48 | 41 | 45 | 47 | 49 | 45 | 52 | 62 | 53 | 38 |
| Seaside | 62 | 94 | 86 | 57 | 71 | 90 | 84 | 87 | 97 | 119 | 103 | 99 |
| Seagrove | 152 | 226 | 207 | 145 | 221 | 235 | 245 | 265 | 262 | 269 | 265 | 247 |
| WaterSound | 34 | 47 | 41 | 29 | 43 | 44 | 45 | 48 | 48 | 48 | 49 | 38 |
| Seacrest | 92 | 127 | 122 | 91 | 115 | 116 | 128 | 130 | 128 | 154 | 145 | 82 |
| Alys Beach | 0+29 | 0+58 | 0+49 | 0+47 | 0+54 | 0+62 | 0+62 | 0+67 | 0+62 | 0+72 | 0+70 | 0+65 |
| Rosemary Beach | 48 | 70 | 67 | 70 | 82 | 67 | 70 | 89 | 91 | 92 | 87 | 58 |
| Inlet Beach | 38 | 43 | 43 | 38 | 38 | 41 | 43 | 44 | 41 | 48 | 48 | 38 |

**7 gecelik toplam fiyatın ortancası (sitenin gösterdiği vergi ve zorunlu ücretler dahil; bin $):**

| Mahalle | Kas 26 | Ara 26 | Oca 27 | Şub 27 | Mar 27 | Nis 27 | May 27 | Haz 27 | Tem 27 | Ağu 27 | Eyl 27 | Eki 27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dune Allen | 3.1 | 3.1 | 3.1 | 3.1 | 3.9 | 3.5 | 5.5 | 5.5 | 5.6 | 4.1 | 3.9 | 3.6 |
| Gulf Place | 1.9 | 2.0 | 1.9 | 2.3 | 3.5 | 2.8 | 3.6 | 4.5 | 4.8 | 3.0 | 2.5 | 3.0 |
| Santa Rosa Beach | 2.4 | 2.5 | 2.5 | 3.0 | 4.0 | 3.1 | 4.4 | 6.1 | 6.5 | 3.8 | 3.1 | 4.7 |
| Blue Mountain Beach | 2.0 | 2.1 | 2.3 | 2.5 | 3.7 | 3.1 | 4.1 | 5.7 | 5.7 | 3.5 | 3.1 | 3.7 |
| Grayton Beach | 3.7 | 2.8 | 2.9 | 2.8 | 4.1 | 3.4 | 4.8 | 5.7 | 5.5 | 4.3 | 3.2 | 4.1 |
| WaterColor | 5.6 | 5.9 | 6.5 | 6.4 | 8.7 | 8.1 | 8.9 | 10.3 | 10.8 | 8.2 | 7.2 | 8.9 |
| Seaside | 4.9 | 4.6 | 4.3 | 4.9 | 7.3 | 6.6 | 6.4 | 7.9 | 8.7 | 6.2 | 6.3 | 6.5 |
| Seagrove | 1.9 | 1.9 | 1.9 | 2.2 | 3.1 | 2.6 | 3.5 | 4.9 | 5.2 | 3.1 | 2.7 | 3.6 |
| WaterSound | 2.5 | 2.6 | 2.7 | 3.7 | 4.2 | 3.5 | 4.0 | 5.8 | 6.8 | 3.6 | 3.2 | 4.0 |
| Seacrest | 2.7 | 2.8 | 3.0 | 3.4 | 5.3 | 4.6 | 5.6 | 7.4 | 7.8 | 4.6 | 4.1 | 4.6 |
| Alys Beach | 8.3* | 9.8* | 9.1* | 8.4* | 14.1* | 12.2* | 13.6* | 14.7* | 15.1* | 10.6* | 10.6* | 13.5* |
| Rosemary Beach | 3.7 | 3.5 | 4.2 | 4.1 | 5.9 | 4.7 | 5.4 | 7.0 | 7.2 | 4.9 | 4.8 | 6.2 |
| Inlet Beach | 2.9 | 2.9 | 3.0 | 3.4 | 5.3 | 4.5 | 5.7 | 6.8 | 7.1 | 4.4 | 4.1 | 4.8 |

`*` Alys Beach: şirketin kendi envanteri (Book>Direct'te olmayan evler). Ortanca, sitenin gösterdiği vergiler ve zorunlu ücretler dahil 7 gecelik toplamdır; 2 yetişkin için sorulmuştur.

**Mevsim grupları (bizim gruplamamız; kiralama şirketleri, 7 gecelik toplam ortancası ve fiyat sayısı):**

| Mahalle | Kış | İlkbahar | Yaz | Sonbahar |
|---|---:|---:|---:|---:|
| Dune Allen | $3.1k (117) | $4.0k (133) | $5.1k (142) | $3.8k (123) |
| Gulf Place | $2.0k (38) | $3.4k (38) | $4.5k (44) | $2.5k (35) |
| Santa Rosa Beach | $2.6k (131) | $3.8k (138) | $5.6k (152) | $3.4k (126) |
| Blue Mountain Beach | $2.3k (147) | $3.6k (181) | $5.1k (203) | $3.1k (179) |
| Grayton Beach | $2.9k (83) | $4.1k (95) | $5.2k (105) | $3.7k (94) |
| WaterColor | $6.1k (139) | $8.6k (141) | $9.8k (159) | $7.3k (128) |
| Seaside | $4.6k (237) | $6.6k (245) | $6.7k (303) | $5.8k (264) |
| Seagrove | $2.0k (578) | $3.2k (701) | $4.5k (796) | $2.9k (664) |
| WaterSound | $2.8k (117) | $3.9k (132) | $5.6k (144) | $3.5k (121) |
| Seacrest | $3.0k (340) | $5.1k (359) | $6.4k (412) | $3.8k (319) |
| Alys Beach | — | — | — | — |
| Rosemary Beach | $4.0k (207) | $5.2k (219) | $6.2k (272) | $5.0k (193) |
| Inlet Beach | $3.1k (124) | $5.1k (122) | $5.9k (133) | $4.0k (124) |

Alys Beach'in fiyatları yalnız şirketin kendi envanterinde olduğu için mevsim tablosunda görünmüyor (mevsim grupları Book>Direct ilanlarıyla eşlenen fiyatlardan); kendi envanteri ay tablosunda.

**Aynı hafta, iki sorgu.** Eski sabit pencerelerden ikisi aylık haftalarla aynı tarihte: Bahar tatili 2027 = 13–20 Mart, Yaz 2027 = 10–17 Temmuz. Bu iki hafta, GÖREV-09'un 8 Ekim kiralama çekimiyle karşılaştırıldı (iki sorgu arasında bir gün var; bu yöntemin sınamasıdır, fiyat değişimi beklenmez):

| Mahalle | 13–20 Mart 2027: eşleşen · ortanca değişim | 10–17 Temmuz 2027: eşleşen · ortanca değişim |
|---|---|---|
| Dune Allen | 45 · %0.0 | 46 · %0.0 |
| Gulf Place | 11 · %0.0 | 15 · %0.0 |
| Santa Rosa Beach | 44 · %0.0 | 51 · %-0.1 |
| Blue Mountain Beach | 54 · %0.0 | 66 · %0.0 |
| Grayton Beach | 28 · %0.0 | 31 · %0.0 |
| WaterColor | 45 · %0.0 | 52 · %0.0 |
| Seaside | 71 · %0.4 | 97 · %0.0 |
| Seagrove | 220 · %0.0 | 260 · %-0.2 |
| WaterSound | 43 · %0.0 | 48 · %0.1 |
| Seacrest | 115 · %0.0 | 128 · %0.0 |
| Alys Beach | 0 · — | 0 · — |
| Rosemary Beach | 82 · %0.0 | 90 · %0.0 |
| Inlet Beach | 38 · %0.0 | 41 · %0.0 |

Book>Direct'in kendi fiyatı Mart ve Temmuz'da hiç olmadığından Book>Direct karşılaştırmasında eşleşen ilan yok. Bütün aylar ikinci aylık çekimle karşılaştırılacak.

**Book>Direct'in kendi fiyatı:** fiyatlı ilan sayısı (bütün mahalleler) Kas 26 8, Ara 26 8, Oca 27 8, Şub 27 0, Mar 27 0, Nis 27 0, May 27 0, Haz 27 0, Tem 27 0, Ağu 27 0, Eyl 27 0, Eki 27 0. GÖREV-09'daki gibi Book>Direct ilanların çok azında fiyat gösteriyor; asıl fiyat kaynağı kiralama şirketlerinin siteleri.

## Testler ve CI

- Yerelde tam takım art arda 3 kez: **692 Python + 57 frontend** testi, hepsi geçti (`.venv\Scripts\python.exe -m pytest -q`, `node --test tests/frontend.test.mjs`). Önce (main/v0.12.0): 650 + 54.
- Dal CI'ı: push sonrası eklenecek.

## Beklenmedik durumlar

1. **Görev metni güncellendi:** ilk okunan sürümde zamanlanmış görev vardı; kullanıcı yeni sürümü (göstergesi ve düğmesiyle) getirdi; zamanlanmış görev oluşturulmadı.
2. **Tarayıcı kuralı görev sırasında değişti** (kullanıcı kararı; yukarıda). Uygulama dışında çalışan eski deneme iptal edildi.
3. **order.online ve realjoy doğrulama döngüsü:** bu ayrı tarayıcı profilinde doğrulama geçmiyor; kullanıcının kendi Chrome'unda açılıyor. Kullanıcı kendi Chrome'unun kullanılmasını önerdi; görev metni tarayıcıyı CLAUDE.md kurulumuna bağladığı (ve Chrome günlük profilde uzaktan hata ayıklamaya izin vermediği) için yapılmadı.
4. **Düğmenin zamanı gelmemiş görünmesi:** gerçek veride aralık dolmamıştı; "pencere kuralı değişti" nedeni eklendi (Adım 3d).
5. **İlk toplu çalıştırmanın durması:** Book>Direct araması tutarsız toplam verdi; yeniden okuma 3 denemeye çıkarıldı, düğmeye yeniden basıldı (Adım 6).
6. **Oversee çok yavaş:** korumalı site, ilan başına ~1,5 dk; 12 pencereyle kiralama adımı 7 sa 42 dk sürdü.
7. **Black Bear Bar Room:** dizindeki site fırının sitesi olduğu için fırının menüsü Bar Room'a $$ verecekti; inceleme notu belirleyici yapıldı.

## Yöneticinin karar vermesi gereken konular

1. **order.online ve realjoy:** bu tarayıcıda doğrulama geçmiyor. Seçenekler: kapsam dışı kabul; kullanıcının kendi tarayıcısında, kullanıcının onayıyla yalnız bu birkaç sayfaya elle bakılması (otomatik toplama değil); ya da başka bir yol. order.online'a bağlı restoranlar: Big Bad Breakfast, Cajun Corner (sipariş menüsü; site menüsü görüntüden okundu), Smallcakes; realjoy 61 ilan.
2. **Kiralama adımının süresi:** 12 aylık pencereyle ~8 saat (Oversee tek başına ~4,5 saat). Aylık yenilemede bu süre kabul mü, yoksa korumalı sitelerde pencere sayısı azaltılsın mı?
3. **Acil sağlık kategorisi:** OpenStreetMap'te bölgede yalnız 2 nokta var; videoda kullanılacaksa ek kaynak gerekebilir (ör. ilçe ya da hastanelerin kendi siteleri).
4. **Publix, Winn-Dixie, The Fresh Market** sitelerinin mağaza listeleri bu bilgisayardan okunamadı (Publix ABD dışı bağlantıya "International" sayfası gösteriyor).
5. **Blue Mountain Bakery:** sitede iki kafe menüsü var (22.3.2024 tarihli ve "NEW"); yalnız "NEW" okundu. İkisi de kalsın mı?
6. **Branch'in main'e alınması** (v0.13.0).

## Teslim

`docs/gorevler/GOREV-10/`: `GOREV.md`, `RAPOR.md`, `restoranlar.csv`, `restoran-seviye-once-sonra.csv`, `restoran-mahalle-ozet.csv`, `konaklama-fiyat-ozet.csv` (12 ay; Book>Direct ve kiralama), `konaklama-mevsim-ozet.csv`, `konaklama-ayni-hafta.csv`, `gunluk-ihtiyac-mahalle.csv`, `gunluk-ihtiyac-noktalar.csv`, `gunluk-ihtiyac-zincir-kontrolu.csv`, `ozet.json`, `ekran/` (gerçek veri: güncelleme bölümü, toplu çalıştırmanın başlaması ve bitmesi, kiralama ay tablosu, aynı hafta tablosu, restoranlar, günlük ihtiyaç; geçici deneme: konaklama ay tablosu, mevsim tablosu, restoran tablosunun stil düzeltmesinden sonraki hâli).

Commit'ler (main'den sonra): 

- `e8e80a5` feat: monthly lodging windows, suggested refresh, OpenStreetMap daily needs and restaurant level review (schema 13)
- `eafc271` feat: a lodging window collector is due when its last run asked another window rule
- `4d25341` docs: GÖREV-10 methods (M11 window rule, M12 level review, new M13 daily needs), README, CLAUDE.md rule; app 0.13.0
- `d8b4737` feat: the browser only where a site blocks plain requests (user decision, 9 October 2026)
- `075c0ea` fix: the browser closes a page's pop-up before reading; single item pages are not menus
- `d1fefef` feat: menus embedded with SinglePlatform or a platform frame are read directly, without the browser
- `f4b55de` data: image menus of Cajun Corner, The Wine Bar at WaterColor and Blue Mountain Bakery read as written
- `885dddf` fix: the batch's backup file is stored with forward slashes
- `0500a08` fix: a site that drops the plain request without an answer is a block and is read in the browser
- `a1611ed` fix: an add-on price note is not a section heading; an add-on heading is a section
- `98089b4` fix: the warm-up leaves open only the tabs that wait for the user's verification
- `543bd48` fix: a reviewer's level note decides; the menu of another business on a shared site gives no level
- `820fbf5` fix: a Book>Direct search whose total changes between pages is read again up to three times
- `de9efcd` fix: the restaurant table shows the level reason on its own line
