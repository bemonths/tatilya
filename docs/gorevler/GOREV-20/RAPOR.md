# GÖREV-20 — Rapor

Tarih: 16 Kasım 2026 · Dal: `gorev-20-eksik-veri` (main `7af4f1f` = `v0.20.0` üzerinden) · Uygulama `0.21.0` · Şema `20`

## Kısa özet

| Eksik | Sonuç |
|---|---|
| Yol üzerinden mesafe ve sürüş süresi | **Tamam.** Yeni toplayıcı gerçek veride çalıştı: 2.309 ilan, 102 nokta (günlük ihtiyaç noktaları, plaj erişimleri, iki havalimanı). Kanıt paketinde kuş uçuşu değerle yan yana. |
| Uçak bileti ortalaması | **Tamam.** BTS'nin resmî tablosundan VPS ve ECP için son beş çeyrek gerçek veride. |
| Kiralama şirketlerinin fiyatları | **Hiçbir yeni şirket okunabilir hale gelmedi.** Altı hedef şirketin beşi bu yollarla okunamıyor (nedenleri aşağıda); RealJoy **tamamlanamadı** (doğrulama geçilemedi). Okunamayanlar kanıt paketine nedenleriyle girdi. |
| Kanıt paketi | **Tamam.** Dört yeni blok, "kapsam dışı" satırları, güncellenmiş bilinen boşluklar. |

**Tamamlanamayan adım:** Adım 2'de RealJoy (61 ilan). Site Cloudflare doğrulaması istiyor; programın kendi tarayıcısında doğrulama iki kez 15 dakika bekledi ve geçmedi (sohbette haber verildi). İlan sayfası ve fiyat isteği görülemediği için okuyucu yazılamadı. Sonraki adım için hazırlık yapıldı (aşağıda "RealJoy için sıradaki iş").

Talimat dosyaları: dal açıldığında `studio/destinations/thirty_a_claude/` altında kullanıcı değişikliği yoktu; "talimat" commit'i gerekmedi. Programın hiçbir Claude adımı çalıştırılmadı, alt ajan kullanılmadı, zamanlanmış görev oluşturulmadı, Housing Atlas klasörüne dokunulmadı.

---

## 1. Kiralama şirketleri

İnceleme kuralı: şirket başına en çok 10 istek, aynı sitede iki istek arası en az 8 saniye; önce doğrudan istek, engel varsa programın kendi tarayıcısı; engeli aşmak için başka yol aranmadı. Yapılan bütün istekler `canli-istekler.csv` içinde (toplam 20 istek; en çok 6 istek 30A Beach Girls'te). Ham yanıtlar `work/gorev-20/ham/` altında.

| Şirket | Book>Direct ilanı | Altyapı | Okuma yolu | Sonuç ve sebep |
|---|---|---|---|---|
| **360 Blue** (360blue.com) | 256 | okunamadı (Book>Direct kaydında "Natural Retreats") | doğrudan → programın tarayıcısı | **Okunamadı.** İkisi de aynı Cloudflare engel sayfasını aldı ("Sorry, you have been blocked"). Bu bir doğrulama değil; kimsenin geçemeyeceği bir ret. Görev kuralına göre bırakıldı. |
| **Cottage Rental Agency** (rentals.cottagerentalagency.com 82, cottagerentalagency.com 10) | 92 | okunamadı | doğrudan | **Okunamadı.** Kiralama alan adının DNS kaydı yok. Ana alan adı sandestin.com'da kaldırılmış bir sayfaya yönleniyor (403 "Access denied"). Şirketin güncel kiralama sitesi bulunamadı. |
| **RealJoy** (realjoy.com) | 61 | ICND rezervasyon motoru (`/bookingEngine/`), arkada Track | doğrudan → programın tarayıcısı | **Tamamlanamadı.** Cloudflare doğrulaması; programın tarayıcısında geçmedi. Ayrıntı aşağıda. |
| **30A Beach Girls** (30a-beachgirls.com) | 48 | AvantStay (şirketin kendi alan adında) | doğrudan (engel yok) | **Okunuyor ama ilanlarla eşlenemiyor.** Book>Direct bağlantılarının hepsi 404. Site 145 evini listeliyor ama sokak adresi vermiyor, koordinatı 3 ondalığa (yaklaşık 100 m) yuvarlıyor. Programın eşleme kuralları sokak adresi ya da 15 m içinde konum ister; ad tek başına ölçüt değildir. Kural değiştirilmediği için bırakıldı. |
| **Vacasa** (vacasa.com 21; wyndhamvacationrentals.com 14 ilanın bağlantısı da buraya gidiyor) | 21 (+14) | Vacasa | doğrudan | **Okunamadı (bölge engeli).** Site ABD dışından gelen isteği reddediyor (CloudFront: "configured to block access from your country"). Sayfa görülemediği için okuyucu yazılamadı. Program bu yanıtı artık "bölge engeli" olarak tanıyor. |
| **Outdoor Shower** (outdoorshower30a.com) | 21 | okunamadı (Book>Direct kaydında "LiveRez") | doğrudan | **Okunamadı.** Site yanıt vermiyor (https ve http bağlantısı zaman aşımı). |

Bu altı şirket (Cottage Rental Agency'nin iki alan adı ve Wyndham bağlantılarıyla) Book>Direct'teki 2.389 ilanın 513'ünü tutuyor. Vrbo (52 ilan) ve Airbnb (19) görev gereği kapsam dışı.

Mevcut uyarlayıcılardan birine uyan şirket çıkmadı; **yeni uyarlayıcı yazılmadı, yapılandırmaya şirket eklenmedi.** (30A Beach Girls için uyarlayıcı yazılabilirdi ama eşleme olmadan hiçbir ilana fiyat bağlanamayacağı için yazılmadı.)

### "Siteleri engelleyen 51 ilan"ın dağılımı

Hepsi zaten okunan ResCMS (Drupal 7) şirketlerinde:

| Şirket | İlan |
|---|---|
| Benchmark Management (benchmark30a.com) | 33 |
| Sanders Beach Rentals | 7 |
| Grayton Coast Rentals | 6 |
| My Vacation Haven | 3 |
| 30A Cottages | 2 |

Bunlar **site engeli değil.** Sitenin ana sayfası ve öbür ilanları açılıyor; yalnız bu ilan sayfaları 403 "Access denied — You are not authorized to access this page" veriyor. Bu, Drupal'ın yayından kaldırılmış sayfaya verdiği yanıttır. 16 Kasım'da bakılan üç örnekten biri artık 404 (silinmiş), biri başka adrese yönleniyor, biri hâlâ 403. Yani bu evler şirketin sitesinde yayından kalkmış ama Book>Direct'te duruyor; okunacak fiyat yok. Kanıt paketindeki satır buna göre düzeltildi ("Sitesi engellediği için" yerine "ilan yayından kaldırılmış").

### RealJoy için sıradaki iş

- Kullanıcının Chrome'undaki eklenti bu siteyi okuyabiliyor (11 Kasım 2026'daki denemenin ham kaydı duruyor). O kayıttan öğrenilenler: site ICND'nin rezervasyon motorunu kullanıyor; 30A ilan listesi sayfası her ev için **sokak adresi, 8 ondalıklı koordinat, yatak sayısı ve birim kodu** veriyor (adres eşlemesine uygun); ilan sayfaları `/beach-rentals/<ad>` biçiminde. Book>Direct'teki eski bağlantılar çalışmıyor.
- Eksik olan tek şey bir **ilan sayfasının** ham kopyası: fiyatın hangi istekle geldiği oradan görülecek.
- Bunun için **Ayarlar → Tarayıcı eklentisi → "Sorunlu sitelerden birer sayfa dene"** listesine RealJoy'un bir ilan sayfası eklendi. Kullanıcı bu düğmeye bir kez basarsa sayfa kaydedilir; okuyucu sonraki görevde o kayıttan yazılır.
- Eklendiği zaman çekime etkisi: 61 ilan × (1 sayfa + 12 hafta × 2 istek) = yaklaşık 1.525 istek, korumalı site hızında yaklaşık 3 saat.

### Yeni çekimin tahmini istek sayısı ve süresi

Yeni şirket eklenmediği için aylık kiralama çekimi **değişmedi**: son çekim 21.129 istek, 7 saat 42 dakika. Hız kuralı gevşetilmedi.

"Güncelleme zamanı gelenler" tablosundaki tahmin artık ileride eklenecek şirketleri de kendiliğinden sayar: son çekimin okumadığı her etkin şirket için ilan sayısı × (1 sayfa + hafta sayısı × 2 istek) × (şirketin istek aralığı + 1 sn); tahminin altında "yeni şirketler dahil: … ilan, +… istek" yazar.

---

## 2. Yol üzerinden mesafe ve sürüş süresi

**Yöntem.** OpenStreetMap yol ağı, programın zaten kullandığı Overpass kaynağından **tek sorguyla** indirilir; ham kopyası saklanır. En hızlı yol programın içinde hesaplanır. API anahtarı, ücretli hesap ya da yol tarifi servisi yok. Ayrıntı: `docs/M19-YOL-MESAFESI.md`.

- Ölçülen çiftler: son konaklama çekimindeki her ilan → günlük ihtiyaç noktaları (7 tür, 47 nokta), ilçenin 53 halka açık plaj erişimi, VPS ve ECP yolcu terminalleri.
- "En yakın" nokta **yol mesafesine göre** seçilir. Kuş uçuşu değer de saklanır ve yanında gösterilir.
- Tek yönlü yollar izlenir. Kapalı siteler ve otoparklar gibi özel yollar yalnız yolculuğun başında ve sonunda kullanılır; içinden kestirme yapılmaz.
- Süre = uzunluk ÷ hız. Hız, yolun kendi hız sınırı etiketi (`maxspeed`); yoksa yol türünün varsayılan hızı. **Trafik, ışık ve dönüş beklemesi yok.** Etiket: "OpenStreetMap yol ağına göre, trafik hesaba katılmadan tahmini sürüş süresi". "Yürüme mesafesi" hiçbir yerde denmez.

**Varsayılan hızlar** (mil/saat; ayardır, koda gömülü değildir; yalnız hız sınırı etiketi olmayan yollarda): motorway 65 · trunk 55 · primary 45 · secondary 40 · tertiary 35 · unclassified 30 · residential 25 · living_street 15 · service 10 · motorway_link 40 · trunk_link 35 · primary_link 30 · secondary_link 30 · tertiary_link 25. Bunlar bizim varsayımımızdır.

**Gerçek çekim** (`84bf543eb71a4842a151cfd7e2a02465`, 16 Kasım 2026, 57 saniye, 1 istek): 19.619 yol, 4.418 km (878 km'sinde hız sınırı etiketi var); 2.389 ilanın 2.309'u ölçüldü. Ölçülmeyen 80 ilanın 79'unun Book>Direct'teki koordinatı hatalı ya da alan dışında (başka eyaletlerde görünenler, 0,0 olanlar); 1 ilan yola bağlandı ama hiçbir noktaya yol bulunamadı. 23.090 satır (ilan × nokta türü) kaydedildi.

**Sağlama.**

- **CR 30A uzunluğu:** OpenStreetMap yol ağında 19,06 mil; FDOT yol envanterinde 18,561 mil (fark %2,7). Fark, OpenStreetMap'te dönel kavşak kollarının ve bölünmüş kısa parçaların ayrı sayılmasından.
- **Yol mesafesi kuş uçuşundan kısa çıkmıyor:** 23.090 satırın hepsinde denetlendi; ayrıca tablonun kendisi daha kısa bir yol mesafesini reddeder ve test bunu gösterir.
- **En yakın nokta değişiyor mu:** 23.090 satırın 2.194'ünde yol mesafesine göre en yakın nokta, kuş uçuşuna göre en yakın noktadan farklı çıktı (ör. Seaside ilanlarının %99'unda en yakın eczane).
- **Akla yatkınlık:** Seaside'dan VPS terminaline ortanca 38,7 mil ve 52 dakika, ECP'ye 33,1 mil ve 41 dakika. Süreler trafik ve ışıklar olmadığı için gerçekte beklenenden biraz kısadır; etiket bunu söyler.

**Mahalle başına örnek tablo** (kuş uçuşu → yol üzerinden mil · tahmini dakika; ortancalar; tam tablo `yol-mesafesi-mahalle.csv`):

| Mahalle | İlan | Büyük süpermarket | Eczane | Acil servis | Halka açık plaj erişimi |
|---|---|---|---|---|---|
| Dune Allen | 113 | 2,35 → 3,13 mil · 6 dk | 1,2 → 1,5 mil · 3 dk | 3,89 → 4,41 mil · 7 dk | 0,11 → 0,17 mil · 1 dk |
| Gulf Place | 30 | 2,17 → 3,11 mil · 6 dk | 0,16 → 0,25 mil · 1 dk | 5,04 → 5,5 mil · 10 dk | 0,18 → 0,27 mil · 1 dk |
| Santa Rosa Beach | 237 | 2,06 → 3,25 mil · 6 dk | 1,65 → 2,0 mil · 5 dk | 5,68 → 6,55 mil · 11 dk | 0,26 → 0,39 mil · 1 dk |
| Blue Mountain Beach | 171 | 2,45 → 3,54 mil · 7 dk | 1,71 → 2,18 mil · 6 dk | 6,68 → 9,0 mil · 13 dk | 0,25 → 0,39 mil · 1 dk |
| Grayton Beach | 84 | 2,5 → 3,76 mil · 8 dk | 3,91 → 4,79 mil · 10 dk | 8,91 → 11,36 mil · 16 dk | 0,25 → 0,34 mil · 1 dk |
| WaterColor | 258 | 0,64 → 0,94 mil · 2 dk | 4,06 → 6,55 mil · 10 dk | 10,78 → 13,47 mil · 18 dk | 0,65 → 1,01 mil · 2 dk |
| Seaside | 210 | 0,85 → 1,4 mil · 3 dk | 4,23 → 6,66 mil · 14 dk | 10,9 → 14,07 mil · 19 dk | 0,32 → 0,4 mil · 1 dk |
| Seagrove | 486 | 1,32 → 2,0 mil · 5 dk | 3,28 → 7,98 mil · 12 dk | 12,37 → 14,89 mil · 20 dk | 0,12 → 0,2 mil · 1 dk |
| WaterSound | 162 | 2,54 → 3,65 mil · 7 dk | 2,97 → 7,43 mil · 11 dk | 15,31 → 18,09 mil · 26 dk | 0,95 → 1,18 mil · 2 dk |
| Seacrest | 296 | 1,25 → 2,45 mil · 5 dk | 3,25 → 3,7 mil · 6 dk | 14,14 → 14,75 mil · 20 dk | 0,56 → 1,06 mil · 2 dk |
| Alys Beach | 7 | 1,1 → 1,9 mil · 4 dk | 3,61 → 3,99 mil · 7 dk | 14,47 → 15,04 mil · 20 dk | 1,05 → 1,15 mil · 2 dk |
| Rosemary Beach | 158 | 1,34 → 2,12 mil · 4 dk | 2,7 → 3,12 mil · 5 dk | 13,56 → 14,17 mil · 18 dk | 0,36 → 0,88 mil · 2 dk |
| Inlet Beach | 97 | 1,65 → 2,11 mil · 4 dk | 2,22 → 2,59 mil · 4 dk | 13,07 → 13,65 mil · 18 dk | 0,16 → 0,26 mil · 1 dk |

Okuma notları: Alys Beach satırı yalnız 7 ilana dayanır (Book>Direct'te görünenler). Plaj erişimi yalnız ilçenin halka açık listesidir; toplulukların kendi özel erişimleri dahil değildir. Seagrove ve WaterSound'da eczane kuş uçuşuna göre yakın görünüp yol üzerinden iki katından uzak çıkıyor: kuş uçuşu en yakın eczaneye doğrudan yol yok.

**Havalimanlarına yol mesafesi ve tahmini sürüş** (ilanlardan yolcu terminaline; ortanca; trafik hesaba katılmadan):

| Mahalle | Destin–Fort Walton Beach (VPS) | Northwest Florida Beaches (ECP) |
|---|---|---|
| Dune Allen | 29,05 mil · 41 dk | 38,4 mil · 47 dk |
| Gulf Place | 30,15 mil · 43 dk | 37,64 mil · 45 dk |
| Santa Rosa Beach | 31,19 mil · 44 dk | 37,29 mil · 45 dk |
| Blue Mountain Beach | 33,63 mil · 46 dk | 36,05 mil · 44 dk |
| Grayton Beach | 35,99 mil · 49 dk | 33,6 mil · 41 dk |
| WaterColor | 38,1 mil · 51 dk | 32,65 mil · 40 dk |
| Seaside | 38,7 mil · 52 dk | 33,09 mil · 41 dk |
| Seagrove | 39,52 mil · 54 dk | 28,03 mil · 39 dk |
| WaterSound | 42,75 mil · 59 dk | 24,99 mil · 33 dk |
| Seacrest | 45,75 mil · 58 dk | 21,26 mil · 28 dk |
| Alys Beach | 45,21 mil · 57 dk | 21,55 mil · 29 dk |
| Rosemary Beach | 45,42 mil · 57 dk | 20,68 mil · 27 dk |
| Inlet Beach | 45,43 mil · 57 dk | 20,16 mil · 26 dk |

---

## 3. Uçak bileti ortalaması

**Kaynak.** ABD Ulaştırma İstatistikleri Bürosu (BTS), "Average Domestic Airline Itinerary Fares": `https://www.transtats.bts.gov/AverageFare/`. Sayfa doğrudan okunuyor; giriş ya da bot koruması yok. İlk yanıt son yayımlanan çeyreği verir; önceki çeyrekler sayfanın kendi formuyla istenir (5 istek, aralarında 8 saniye). Ayrıntı: `docs/M20-UCAK-BILETI.md`.

**Önemli düzeltme.** Görev metni değeri "bütün kalkış noktalarından o havalimanına" diye tarif ediyordu. Kaynağın tablosu ise **"By Origin City"**: değer, **o havalimanından başlayan** iç hat yolculuklarının ortalamasıdır. Etiket kaynağın tanımına göre yazıldı: gidiş-dönüş ya da dönüşü alınmamış tek yön bilet; satın almadaki vergi ve ücretler dahil; bagaj gibi sonradan ödenenler hariç; biletlerin %10'luk örneğinden. Bu yüzden "30A'ya uçak bileti şu kadar" denemez; kanıt paketinin kullanım notu bunu açıkça yasaklar.

**Gerçek çekim** (`b4a40f70b2f1455bad36f2eb8c9b3a21`, 16 Kasım 2026): son yayımlanan çeyrek 2026 Q2. Ortalama bilet ücreti (nominal dolar):

| Havalimanı | 2026 Q2 | 2026 Q1 | 2025 Q4 | 2025 Q3 | 2025 Q2 | Bir yıl önceye göre |
|---|---|---|---|---|---|---|
| VPS — Destin–Fort Walton Beach (BTS'de "Valparaiso, FL"; yolcu sırası 114) | $376,10 | $431,66 | $394,61 | $339,52 | $359,62 | +$16,48 (%4,6) |
| ECP — Northwest Florida Beaches (BTS'de "Panama City, FL"; yolcu sırası 126) | $461,65 | $480,55 | $458,96 | $411,41 | $413,03 | +$48,62 (%11,8) |

Fark sütunu bizim hesabımızdır (enflasyon düzeltmesi yok). BTS'nin enflasyona göre düzeltilmiş değerleri de saklandı (`ucak-bileti.csv`).

---

## 4. Kanıt paketi

Yazım zincirinin gördüğü malzemeye girenler (`docs/M14-KANIT-PAKETI.md`; şablonlar sürüm 2):

- **Yol mesafesi ve sürüş süresi** (`road_distances`): mahalle × nokta türü; yazar özetinde hücre "yol mil · dakika · kuş <kuş uçuşu mil> · %<1 yol mili içindeki pay>". İlk video şablonunda "Araba ve ulaşım" bölümünde, günlük ihtiyaç tablosunun hemen ardında; mahalle rehberinde "Günlük ihtiyaç mesafeleri" bölümünde.
- **Havalimanlarına yol mesafesi ve süre:** aynı blokta ayrı tablo.
- **Uçak bileti ortalaması** (`airfare`): havalimanı × çeyrek tablosu ve bir yıl önceye göre fark.
- **Kiralama fiyatlarının kapsadığı şirketler** (`lodging_coverage`): fiyat ortancalarına giren 22 şirket (fiyatlı ilan sayılarıyla) ve fiyatı okunamayan şirketler (ilan sayısı, neden, bakıldığı tarih).
- **Kapsam dışı** (`out_of_scope`): araç kiralama fiyatları, market fiyatları, anlık trafik ve trafikli sürüş süresi, Vrbo ilanlarının fiyatları; her biri "veri yok" satırı ve ayrıca "bilinen boşluklar"da tek satır.
- **Kullanım notları** (blok başında bir kez): süre her zaman "tahmini" ve "trafik hesaba katılmadan" söylenir; uçak bileti değeri dönem ve "bu havalimanından başlayan yolculuklar" tanımıyla söylenir, genelleştirilmez; okunamayan şirketler adlarıyla anılmaz; kapsam dışı konu hakkında sayı söylenmez. Talimat dosyalarına dokunulmadı.
- **Program denetimi:** "minute drive", "minutes away" gibi ifadeler eskiden her zaman kırmızıydı. Artık cümle bir yol mesafesi kanıtını işaret ediyorsa serbest, etmiyorsa kırmızı. Yürüme ifadeleri hâlâ her zaman kırmızı.

Gerçek verinin kopyasında denendi (gerçek veride paket üretilmedi): ilk video paketi 995 satır (önce 843), yazar özeti 135 KB (önce 110 KB).

---

## 5. Gerçek veride ne çalıştırıldı

1. Program kapalıyken `data/` klasörünün tam yedeği alındı: **`work/yedek/20261116-1805/`** (45.539 dosya, 1,5 GB).
2. Program gerçek veri klasörüyle normal biçimde açıldı. Açılışta şema 19 → 20 yükseltildi; uygulama kendi yedeğini aldı (`data/backups/studio-v19-9b6fefc4….sqlite3`).
3. Programın kendi iş kuyruğuyla yalnız iki toplayıcı çalıştırıldı: **yol ağı ve yol mesafeleri**, **uçak bileti**. İkisi de tamamlandı.
4. Program kapatıldı.

Kiralama fiyat çekimi **başlatılmadı**. Gerçek veride kanıt paketi üretilmedi, Claude çalıştırılmadı.

Önce/sonra karşılaştırması (yedek ile bugünkü veritabanı): 71 eski tablonun 67'si satırı satırına aynı. Değişen dört tablo beklenenlerdir: kaynaklar 16 → 18 (iki yeni kaynak), önerilen yenileme aralıkları 4 → 6, işler 40 → 42, çekimler 30 → 32. Yedi yeni tablo eklendi. `foreign_key_check` boş, bütünlük denetimi "ok". Şema değişikliği önce kopyada denendi (aynı sonuç).

---

## 6. Testler ve belgeler

- Yeni testler: `tests/test_road_network.py` (yol mesafesi kuş uçuşundan kısa olamaz; en yakın nokta yol mesafesine göre seçilir; tek yön, özel yol, varsayılan hızların ayar olması, dolu sunucuda bekleme, şema 19 → 20), `tests/test_airfare.py` (BTS sayfasının ham kopyasından fixture; ayrıştırma, form, eksik havalimanı), `tests/test_gorev20.py` (kanıt paketinde yeni satırlar ve "kapsam dışı", kapsanan ve okunamayan şirketler, çekim tahmini). Testler canlı ağa bağlanmaz.
- Yeni uyarlayıcı yazılmadığı için uyarlayıcı fixture testi yok.
- Tam takım: `pytest` ve `node --test tests/frontend.test.mjs` sonuçları bu dosyanın sonundaki "Son test turu" satırında.
- Belgeler: yeni `docs/M19-YOL-MESAFESI.md` ve `docs/M20-UCAK-BILETI.md`; güncellenen `M11`, `M13`, `M14`, `M17`, `CALISMA_MANTIGI.md`, `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`.
- Küçük ek: eklentinin sayfa türü işaretlerine CloudFront'un ülke engeli cümlesi eklendi (programdaki ile aynı kalsın diye). Eklenti sürümü değiştirilmedi; Chrome'daki eklentiyi yenilemek gerekmez.

Dal push edildi; main'e alınmadı, etiket konmadı.

**CI.** İlk iki commit'in (`de80499` kod ve testler, `1b950a6` belgeler) çalışması (43894810272) test adımında 16 dakikalık zaman sınırına takıldı. Bu, GÖREV-17 ve GÖREV-18 raporlarında anlatılan rastgele takılmadır (aynı kod bir çalışmada geçiyor, öbüründe bir test bekliyor; kök neden bulunmadı): günlüğün herkese açık özeti takılmanın bu görevin yeni testlerine sıra gelmeden, eklenti, temel ve GÖREV-17/18 testlerinin olduğu bölümde olduğunu gösteriyor; yerelde tam takım art arda iki kez takılmadan geçti. Özet 4.000 karakterde kesildiği için günlüğün sonu (bekleyen testin adı ve yığın) yine görünmedi; iş akışındaki özet adımı artık günlüğün **sonunu** tutuyor (`.github/workflows/tests.yml`). Bu düzeltmeyi taşıyan commit'in çalışması yeniden bekledi; sonucu aşağıdaki "CI sonucu" satırında.

---

## 7. Yöneticinin karar vermesi gerekenler

1. **30A Beach Girls (48 ilan):** site okunuyor ama eşleme kuralları tutmuyor. "Aynı ad + aynı yatak sayısı + yuvarlanmış koordinat aynı ~100 m karesinde" gibi yeni bir eşleme kuralı kabul edilir mi? Edilirse uyarlayıcı yazılabilir.
2. **RealJoy (61 ilan):** kullanıcı eklenti denemesini bir kez çalıştırırsa okuyucu sonraki görevde yazılabilir.
3. **Vacasa (21 + 14 ilan):** yalnız kullanıcının ABD proxy'siyle görülebilir. Proxy üzerinden inceleme ve okuyucu istenir mi?
4. **360 Blue (256 ilan):** en büyük eksik hâlâ bu; WaterColor ve WaterSound fiyatları bu yüzden zayıf. Bu yollarla okunamıyor.

---

## 8. Kullanıcı için: kiralama fiyatı çekimini başlatma tarifi

Çekim yaklaşık bir gece sürer. Akşam başlatıp sabah bakmak en rahatı.

**Başlamadan önce**

1. Bilgisayar prize takılı olsun ve uyku moduna geçmesin.
2. Masaüstündeki **30A Studio** simgesiyle programı açın.
3. Sol menünün en altından **Ayarlar**'a girin, **Tarayıcı eklentisi** bölümüne bakın. "Bağlantı" satırında yeşil etiketle **"Bağlı"** yazmalı. "Bağlı değil (Chrome kapalı olabilir)" yazıyorsa günlük Chrome'unuzu açın ve sayfayı yenileyin. Chrome bütün gece açık kalsın.
4. Aynı bölümde **"İzin bekleyen siteler"** satırında bir site adı varsa: Chrome'da eklenti simgesine ("30A Studio Yardımcısı") tıklayıp **İzin ver**'e basın.

**Başlatma**

5. Sol menüden **Veri kaynakları**'na girin (programın açılış ekranı).
6. **Güncelleme zamanı gelenler** tablosuna bakın. "Zamanı geldi" yazan satırlar çalışacak olanlardır: "South Walton · Konaklama (Book>Direct)", "Kiralama şirketleri · Konaklama fiyatları" ve "OpenStreetMap · Yol ağı ve sürüş süreleri".
7. Tablonun altındaki **Zamanı gelenleri başlat** düğmesine basın. Program önce kendi yedeğini alır, sonra toplayıcıları sırayla çalıştırır. Düğmenin yanında tahmini süre yazar: yaklaşık 8 saat 45 dakika (konaklama aramaları 1 saat, kiralama şirketleri 7 saat 42 dakika, yol mesafeleri 1 dakika). Bu, geçen ayki çekimin süresidir; korumalı siteler eklentiyle okunursa biraz daha uzun sürebilir.
8. Sağ üstteki **İşler** düğmesine basarsanız ilerlemeyi görürsünüz.

**Doğrulama isteyen siteler (ısınma listesi)**

9. İki korumalı site var: **oversee.us** ve **exclusive30a.com**. Eklenti bağlıysa bu siteler sizin Chrome'unuzda, eklentinin kendi açtığı ayrı pencerede ("30A Studio Yardımcısı") açılır; eklenti bağlı değilse program kendi Chrome penceresini açar.
10. Site doğrulama isterse İşler panelinde turuncu **"Kullanıcı doğrulaması bekleniyor"** etiketi ve sitenin adı görünür; pencere öne gelir. O pencerede "Verify you are human / İnsan olduğunuzu doğrulayın" kutusunu işaretleyin. Başka bir şey yapmanız gerekmez; program hiçbir şeye tıklamaz.
11. Doğrulama için en çok 15 dakika beklenir. O sırada bilgisayar başında değilseniz o site atlanır ve kayda yazılır; öbür şirketlerin fiyatları yine alınır. Bu yüzden başlattıktan sonra ilk yarım saat ekrana bir göz atmanız yeterli; sabah İşler paneline bakın.

**Durdurmak isterseniz**

12. Aynı tablonun altında **Toplu çalıştırmayı durdur** düğmesi çıkar. Programın penceresini kapatırsanız süren iş bitene kadar program arkada çalışmaya devam eder.

**Bitince neye bakılır**

13. **Veri kaynakları → Güncelleme zamanı gelenler**: "Son toplu çalıştırma: Tamamlandı" ve her satırda "tamamlandı" yazmalı. Bir satırda "hata" ya da "atlandı" varsa bana haber verin.
14. Sol menüden **Veri toplama → Konaklama** sekmesi, aşağıda **"Kiralama şirketlerinin kendi siteleri · Konaklama fiyatları"** bölümü: en üstteki sürüm bugünün tarihi olmalı; şirket tablosunda her şirketin yanında durumu yazar.
15. **Veri toplama → Mahalleler** sekmesinin altında **"Yol üzerinden mesafe ve tahmini sürüş süresi"**: sürüm bugünün tarihi olmalı ve "yeniden hesaplayın" uyarısı görünmemeli.

**İsteğe bağlı (RealJoy için, 2 dakika):** Ayarlar → Tarayıcı eklentisi → **"Sorunlu sitelerden birer sayfa dene"** düğmesine bir kez basın. Chrome'da siteler birer birer açılır; RealJoy doğrulama isterse kutuyu işaretleyin. Bu, RealJoy'un fiyat okuyucusunun yazılabilmesi için gereken sayfayı kaydeder; gece çekiminden bağımsızdır ve ondan önce ya da sonra yapılabilir.

---

## Ekler

- `GOREV.md` — görev metni
- `yol-mesafesi-mahalle.csv` — mahalle × nokta türü: ölçülen ilan, kuş uçuşu ve yol ortancaları, sürüş dakikası, 1 yol mili içindeki pay, en yakını değişen pay, en sık en yakın nokta
- `ucak-bileti.csv` — havalimanı × çeyrek: ortalama ve enflasyona göre düzeltilmiş ücret, BTS başlığı, ham yanıtın SHA-256'sı
- `okunamayan-sirketler.csv` — şirket başına altyapı, okuma yolu, neden, tarih (programın okuduğu dosyanın kopyası)
- `canli-istekler.csv` — inceleme sırasında yapılan 20 canlı isteğin kaydı

Son test turu: 16 Kasım 2026 — `.venv\Scripts\python.exe -m pytest -q`: 1147 geçti, 2 atlandı (eklentinin uçtan uca denemesi; ayrı ortam ister), 0 hata · `node --test tests/frontend.test.mjs`: 124 geçti, 0 hata.

CI sonucu: CI_SONUCU
