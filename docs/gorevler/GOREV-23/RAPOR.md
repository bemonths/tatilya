# GÖREV-23 — Rapor

Tarih: 17 Kasım 2026 · Dal: `gorev-23-okuyucular` (main `9ead6a8` = `v0.23.0` üzerinden) · Uygulama `0.24.0` · Şema `23`

## Kısa özet

| Konu | Sonuç |
|---|---|
| main ve etiket | `gorev-22-kiralama` main'e fast-forward ile alındı, `v0.23.0` etiketi konuldu, ikisi push edildi. |
| RealJoy (61 ilan) | **Bekliyor.** Eklentinin 17 Kasım tarihli deneme kaydı yok; kullanıcıya tarif verildi. Okuyucu yazılmadı. |
| 30A Beach Girls (sitede 145 ev) | **Kira okunuyor, toplam okunmuyor.** Sitenin takvimi (gecelik fiyat, müsaitlik, en az konaklama) sepetsiz geliyor: haftalık kira bundan okunur. Ücretli ve vergili toplam yalnız **sepet kaydı açan** sorguyla geliyor; o sorgu kullanılmadı ve kullanılmayacak. |
| Vacasa | **Tam liste geliyor:** `page_limit` ile 300 evin 300'ü tek istekte. Kod değişmedi. |
| Outdoor Shower (21 ilan) / LocalVR | **Okunacak site yok.** LocalVR'nin sitesindeki 548 evin hiçbiri Florida'da değil; 30A pazarı yok. Okuyucu ve yapılandırma yazılmadı. |
| Zamanlamaya bağlı test | **Düzeltildi** (yarış bulundu; test işin bitmesini bekliyor). |
| Gerçek veri | Şema 22 → 23; yalnız 30A Beach Girls'ün yapılandırma satırı değişti; hiçbir tabloda satır sayısı değişmedi. Kiralama fiyat çekimi **başlatılmadı**. |
| Çekim tahmini | Kiralama şirketleri yaklaşık **10 saat**; üç toplayıcı birlikte yaklaşık **11 sa 4 dk**. |

**Tamamlanamayan adımlar:** (1) Adım 2 — RealJoy: eklentinin ilan sayfası kaydı yok; kullanıcının düğmeye basması bekleniyor. (2) Adım 5 —
LocalVR'de 30A evi olmadığı için Outdoor Shower'ın ilanları bağlanamadı (yapılacak bir şey kalmadı; neden kayıtlı).

Programın hiçbir Claude adımı çalıştırılmadı, alt ajan kullanılmadı, zamanlanmış görev oluşturulmadı, Housing Atlas ve Rota Stüdyo
klasörlerine ve talimat dosyalarına dokunulmadı. Proxy'nin adresi, kullanıcı adı ve parolası hiçbir dosyaya, günlüğe, rapora ya da
sohbete yazılmadı; yalnız programın proxy modülü (`studio.proxy.load`) kullanıldı.

---

## Adım 1 — main ve dal

- Program kapalıydı (`data/calisiyor.json` yok).
- `gorev-22-kiralama` main'e fast-forward ile alındı (`2848c6f..9ead6a8`), `v0.23.0` açıklamalı etiketi konuldu ("v0.23.0 — GÖREV-22:
  bölge engeli ölçümü, 360 Blue ve Vacasa okuyucuları, 30A Beach Girls kendi envanteri (şema 22)"); ikisi push edildi.
- `gorev-23-okuyucular` dalı güncel main'den açıldı. `studio/destinations/thirty_a_claude/` altında kullanıcı değişikliği yoktu;
  "talimat" commit'i gerekmedi.

---

## Şirket tablosu (bütün kiralama eksiklerinin son durumu)

| Şirket | Book>Direct ilanı / ev | Altyapı | Okuma yolu | Sonuç ya da okunamama sebebi |
|---|---|---|---|---|
| **360 Blue** (360blue.com) | 256 ilan | Natural Retreats'in rezervasyon motoru | ABD proxy'si üzerinden doğrudan istek | Okuyucu hazır (GÖREV-22, `nrbe`). Çevrimdışı denemede 127 ilan adres kuralıyla bağlanıyor. İlk çekimi bekliyor. |
| **Vacasa** (vacasa.com; Wyndham bağlantıları buraya yönleniyor) | 21 + 14 ilan | Vacasa | ABD proxy'si üzerinden doğrudan istek (Wyndham bağlantısının ilk adımı doğrudan) | Okuyucu hazır (`vacasa`). **Tam liste doğrulandı (300/300).** Kaç ilanın bağlanacağı çekimde görülecek (aşağıda). |
| **30A Beach Girls** (30a-beachgirls.com) | 48 ilan; sitede 145 ev | AvantStay | doğrudan (engel yok) | Evler şirketin kendi envanteri olarak okunur. **Haftalık kira okunur** (sitenin takviminden); temizlik ücreti, öbür ücretler, vergi ve toplam **okunmaz** (sepet sorgusu kullanılmıyor). 48 Book>Direct ilanı kural gereği bağlanmıyor. |
| **RealJoy** (realjoy.com) | 61 ilan | ICND rezervasyon motoru (arkada Track) | eklenti (bot koruması; proxy kullanılmaz) | **Bekliyor:** ilan sayfasının ham kaydı yok; okuyucu yazılmadı. |
| **Outdoor Shower** (outdoorshower30a.com) | 21 ilan | — (alan adı askıda; devralan LocalVR: Guesty üzerinde kendi ön yüzü) | — | **Okunacak site yok:** LocalVR'nin sitesinde 30A'da ev yok. |
| **Cottage Rental Agency** | 92 ilan | — | — | **Site yok** (GÖREV-22; değişmedi). |

### Kaç ilan fiyatlanabilir, kaçı hâlâ eksik

Bu altı şirket 513 Book>Direct ilanıdır.

| | İlan / ev | Açıklama |
|---|---|---|
| Okuyucusu var, bağlanması bekleniyor | **127 ilan** | 360 Blue (çevrimdışı deneme; gerçek sayı çekimde kesinleşir). |
| Okuyucusu var, kaçının bağlanacağı çekimde görülecek | **25 ilan** | Vacasa: bağlantısında ilan numarası olan 11 ilan + 14 Wyndham bağlantısı. Tam listeyle çevrimdışı karşılaştırmada 11 ilandan yalnız **1'inin** numarası listedeki bir evin eski numarası; öbürleri büyük olasılıkla artık Vacasa'da değil. Wyndham bağlantılarının yönlendiği numara ancak çekimde görülür. |
| Okuyucusu var ama bağlanamıyor | **129 + 10 ilan** | 360 Blue'da 129 (adresi şirketin güncel listesinde yok, oda sayısı yok ya da belirsiz); Vacasa'da 10 bağlantı bir evin değil bir yerleşkenin sayfası. |
| İlanlara bağlanmıyor (kural gereği); yerine şirketin kendi evleri okunuyor | **48 ilan → sitede 145 ev** | 30A Beach Girls. Evlerin **kirası** okunur; toplam fiyat okunmaz. Kaç evin 30A bölgesinde olduğu ve mahalle dağılımı ilk çekimde görülecek. |
| Bekliyor | **61 ilan** | RealJoy. |
| Site yok | **113 ilan** | Cottage Rental Agency 92, Outdoor Shower 21. |

Karşılaştırma için: son çekimde (10 Ekim 2026) 2.389 ilanın 1.131'i şirket sitesinde bulunmuş, 1.080'ine fiyat alınmıştı.

---

## Adım 2 — RealJoy

- **Kayıt.** Eklentinin deneme kayıtlarına bakıldı (`data/raw/eklenti/`, salt okunur): klasörler `20261011` ve `20261111`. **17 Kasım 2026
  tarihli kayıt yok.** Programın günlüğüne göre program 17 Kasım'da yalnız GÖREV-22'nin açılışında (12:20–12:22) çalışmış; deneme düğmesine
  basılmamış. 11 Kasım kaydında RealJoy'un yalnız **30A ilan listesi** sayfası var (iki kez, HTTP 200, 564 KB); ilan sayfası
  (`/beach-rentals/sea-la-vie-seaside-main-house`) deneme listesine 16 Kasım'da eklendiği için kaydı yok.
- **Tarif** kullanıcıya sohbette verildi (ekrandaki adlarla; düğmenin adı görev metnindekiyle aynı): *Chrome'u ve programı açın. Sol
  menü → Veri → Okuma denemeleri → "Eklentinin deneme okuması" → "Sorunlu sitelerden birer sayfa dene". Chrome'da açılan sayfada doğrulama
  kutusu çıkarsa işaretleyin. Bitince programı kapatıp bana "tamam" yazın.*
- **Fiyat isteği.** Liste sayfasının kaydından görülen: site ICND'nin rezervasyon motorunu kullanıyor (`/bookingEngine/…` betikleri ve
  stilleri). Fiyatın hangi istekle geldiği ilan sayfasının kaydı olmadan görülemiyor; liste sayfasında fiyat isteği yok.
- **Okuyucu.** Yazılmadı. Kayıt gelince yapılacak iş değişmedi: fiyat, eklentinin sayfa olarak açabileceği bir GET adresiyle geliyorsa
  okuyucu yazılır; yalnız tıklama ya da form gönderme ile geliyorsa yazılmaz ve sebebi kaydedilir.

---

## Adım 3 — 30A Beach Girls fiyatı (AvantStay)

### Yapılan istekler

AvantStay'in servisine **2 istek** yapıldı (izin 5 idi; doğrudan, aralarında 13 saniye). Çalışma ortamı bu kez engellemedi.

| # | İstek | Yanıt |
|---|---|---|
| 1 | Takvim sorgusu (evin sayfasının yaptığı istek): `home(homeId){calendar(from,to){date minStay rate season status restrictions{…}}}`, ev 609625 "Barefoot Paradise", 1 Mart – 30 Haziran 2027 | **200**, 122 gün. Gecelik fiyat **dolar** olarak (ör. 175.0; Nisan'da 179–322). Durum sözleri: `VACANT` 68, `OCCUPIED` 46, `CHECK_IN` 4, `CHECK_OUT` 4 (sitenin betiğinde beşincisi de var: `CHECK_OUT_AND_CHECK_IN`). En az konaklama 3, 4 ya da 6 gece. Bazı günler girişe ve/veya çıkışa kapalı (`checkInAllowed`, `checkOutAllowed`). `season` hep boş. |
| 2 | Tür tanımı sorgusu (yalnız şema; fiyat ya da sepet sorgusu değil) | **422** "Internal server error" (`GRAPHQL_VALIDATION_FAILED`): servis tür tanımı vermiyor. Ret metni olarak fixture'a alındı. |

`cartPrice` (fiyat dökümü) sorgusu **gönderilmedi.**

### Sepet konusu

Görev metni şunu sordu: fiyat, sitenin evin sayfasında herkese gösterdiği fiyat kutusunun yaptığı istekle ve sepet akışı başlatmadan
alınabiliyor mu? Cevap sitenin kendi betiğinden (GÖREV-22'de alınan ham kopyalar) okundu, istek göndermeye gerek kalmadan:

- Fiyat kutusunun yaptığı istek `cartPrice`'tır. Sayfa onu ilk kez **sepet numarası olmadan** sorar; yanıtta dönen `cartId`'yi saklar
  (`cartIdWithoutInsurance`) ve sonraki her soruda **geri gönderir**. Aynı numara ödeme adımlarının (`initializeCartPayment`,
  `setCartPayment`, `confirmCartPayment`, `recreateCart`) girdisidir.
- Yani bu soru serviste her seferinde bir **sepet kaydı açar.** Kural: rezervasyon ya da sepet akışına girmiyoruz. Bu yüzden `cartPrice`
  denenmedi bile; denemek de bir sepet açmak olurdu.
- Sayfanın sepetsiz bir fiyat dökümü sorgusu yok. Sepetsiz gelen tek fiyat bilgisi **takvimdir**: evin sayfasındaki takvimin gün gün
  gösterdiği gecelik fiyat.

### Sonuç ve okuyucu

- **Toplam fiyat (ücretler ve vergi dahil) okunmuyor ve okunmayacak;** sebebi yukarıdaki kural.
- **Haftalık kira okunuyor.** Okuyucu (`AvantStay.quote`) ev başına tek takvim isteği yapar (bu ayın ilk gününden 18 ay; evin bütün
  haftalarına yeter) ve:
  - haftanın tutulabilir olup olmadığını **sitenin kendi kuralıyla** (sayfanın betiğindeki kural) belirler: giriş günü boş ve girişe
    açık, aradaki geceler boş, çıkış günü çıkışa açık, en az konaklama haftaya sığıyor;
  - hafta doluysa "müsait değil", kural yüzünden tutulamıyorsa "kısıtlı" (en az gece sayısıyla) yazar;
  - hafta boşsa **kira = takvimin o yedi geceye yazdığı gecelik fiyatların toplamı.** Örnek: 10–17 Nisan 2027, 252 + 213 + 183 + 179 +
    182 + 192 + 267 = **1.468 $**. Bu toplam **bizim toplamımızdır** ve her yerde öyle etiketlenir; gecelik fiyatlar sitenin kendi
    sayılarıdır ve satırda saklanır.
- Temizlik ücreti, öbür ücretler, vergi ve toplam **boş** kalır. Bu satırlar hiçbir **toplam fiyat ortancasına girmez**; ekranda
  ("Şirketin kendi sitesindeki evler" tablosunda yeni sütun: **HAFTALIK KİRA ORTANCASI** — "yalnız kira; ücret ve vergi hariç") ve kanıt
  paketinde ("7 gecelik kira ortancası; temizlik ücreti, öbür ücretler ve vergi HARİÇ") ayrı görünür. Video metninde "haftalık toplam"
  diye anılamaz.
- Yapılandırmada fiyat açıldı (`quotes: true`), kanal adı eklendi (`channel`). Testler incelemenin ham yanıtlarından fixture'larla.

**Yöneticinin bilmesi gereken:** görev metni "fiyat yalnız sepet açan istekle geliyorsa fiyat sorgusu kapalı kalır, evler fiyatsız
listelenir" diyordu. Toplam fiyat için tam olarak bu yapıldı. Kirayı (sepetsiz, sayfanın kendi takvim isteğinden) ayrıca okumak benim
kararımdır; kapatmak tek satırdır (yapılandırmada `quotes: false`). İstenmezse söylenmesi yeter.

---

## Adım 4 — Vacasa tam liste

- **1 istek** (izin 3 idi), ABD proxy'si üzerinden: `GET /search?place=/usa/Highway-30A/&page_limit=300` → **200**, 4,4 MB.
- Yanıt: `total_units: 300`, `units`: **300**, `page_count: 1`. **30A'daki 300 evin tamamı tek istekte geliyor.**
- Okuyucu zaten ilk sayfadan (24 ev) sonra ikinci istekte `page_limit=<toplam>` soruyordu: **kod değişmedi**, sayfalama isteği
  gerekmedi. Liste eksik gelirse "liste eksik" kuralı aynen geçerli (şirket o çekimde hatayla kaydedilir, hiçbir ilan tahminle
  bağlanmaz); bu, 300 evlik gerçek listeyle ve bir evi eksiltilmiş haliyle testte gösterildi.
- 300 evin 296'sında eski ilan numarası var. Son Book>Direct çekimindeki 35 Vacasa/Wyndham bağlantısıyla çevrimdışı
  karşılaştırma: numaralı 11 bağlantıdan 1'i listedeki bir evin eski numarası.

---

## Adım 5 — LocalVR (Outdoor Shower'ın evleri)

**8 sayfa** (izin 10 idi), doğrudan, aralarında en az 9 saniye; doğrulama ya da engel çıkmadı.

| # | Sayfa | Ne görüldü |
|---|---|---|
| 1–2 | `golocalvr.com` ana sayfa | Başlık: "LocalVR — Luxury Vacation Rental Management \| Colorado, Utah, Montana, Tahoe". Konumlar: Big Sky, Breckenridge, Lake Tahoe, Park City, Telluride, Vail. 30A ya da Florida yok. Rezervasyon sitesi: `stay.golocalvr.com`. |
| 3 | `stay.golocalvr.com` ana sayfa | 13 pazar (California 4, Colorado 7, Montana 1, Utah 1). Florida yok. |
| 4 | Devir duyurusunun adresi ("LocalVR Expands in 30A Florida with Acquisition of Outdoor Shower") | **Artık yok:** blog ana sayfasına yönleniyor (308). |
| 5 | `stay.golocalvr.com/locations` | Sitenin arama bağlantılarındaki bütün şehirler (55 bağlantı); hiçbiri Florida'da değil. |
| 6 | Sitenin kendi araması, `listings?city=Santa Rosa Beach` | Sayfa açılıyor; ev listesi sayfanın betiğiyle ayrı bir istekten geliyor. |
| 7 | İlan listesi sayfasının betiği | Altyapı: Guesty üzerinde kendi ön yüzü. Ev listesi `GET /api/properties?fetchAll=1`, fiyat `POST /api/listing-quotes`, takvim `GET /api/property-dates/`. |
| 8 | `GET /api/properties?fetchAll=1` (ilan listesi sayfasının yaptığı istek) | **548 ev, tam liste** (`total: 548`). Eyaletler: Colorado 254, California 137, Utah 96, Montana 51, Nevada 10. **Florida 0.** |

**Sonuç.** LocalVR bugün 30A'da ev kiralamıyor (ya da sitesinde göstermiyor). Outdoor Shower'ın 21 Book>Direct ilanının bağlanacağı bir
liste olmadığı için:

- uyarlayıcı yazılmadı, yapılandırmaya satır eklenmedi (mevcut uyarlayıcılara uyup uymadığı sorusu da böylece düşüyor; not: Guesty
  mevcut uyarlayıcılardan hiçbirine uymuyor);
- **bağlanan ilan sayısı: 0;** 21 ilan fiyatsız kalır. Nedeni gözden geçirilmiş dosyada güncellendi (`thirty_a_agency_unread.csv`) ve
  kanıt paketinin "Fiyatı okunamayan kiralama şirketleri" tablosunda görünür;
- ölü bağlantılar (outdoorshower30a.com) çekimde sorulmaz: yapılandırılmış bir şirketin alan adı olmadıkları için program onlara zaten
  istek yapmıyor;
- adres kuralının kendisi (aynı sokak numarası ve sokak, aynı daire, aynı oda sayısı, tek aday, 2 km) testle gösterildi; adı aynı ama
  adresi tutmayan ev bağlanmıyor.

Engeli aşmak ya da şirketin evlerini başka yerde aramak için başka yol denenmedi.

---

## Adım 6 — Gerçek veri, çekim tahmini, testler, belgeler

### Gerçek veri: ne değişti

1. **Yedek.** Program kapalıyken `data/` klasörünün tamamı kopyalandı: `work/yedek/20261117-1332/` (45.550 dosya, 1.821.867.056 bayt;
   kaynakla aynı boyut).
2. **Göç önce kopyada denendi** (`work/gorev-23/temp-data`): şema 22 → 23, 81 tablo, 188.523 satır önce ve sonra aynı, ilişki bütünlüğü
   hatası 0.
3. **Program gerçek veriyle normal biçimde açıldı** (sürüm 0.24.0), şema 23'e geçti ve kapatıldı. Açılışta program kendi yedeğini de aldı
   (`data/backups/studio-v22-….sqlite3`).

| | Önce | Sonra |
|---|---|---|
| Şema | 22 | 23 |
| Tablo sayısı | 81 | 81 |
| Toplam satır | 188.523 | 188.523 |
| Değişen satır | — | 1: `destination_agency_sites` içinde 30A Beach Girls'ün seçenekleri (`channel: BEACH_GIRLS`, `quotes: true`, `expected_matches: 0`; "fiyat sorulmadı" notu kalktı) |
| Yapılandırılmış şirket | 27 | 27 |
| İlişki bütünlüğü hatası | 0 | 0 |

Yeni şirket satırı eklenmedi (RealJoy bekliyor, LocalVR'de okunacak ev yok). **Kiralama fiyat çekimi başlatılmadı.**

### Çekim tahmini

"Güncelleme zamanı gelenler" tablosu gerçek veride şunu gösteriyor: **Kiralama şirketleri · Konaklama fiyatları — yaklaşık 10 saat**
(35.999 sn); notu: "son çekimden sonra eklenen 3 şirket için en çok +2720 istek, +137 dk (şirketler yan yana okunur; 360 Blue, Vacasa,
30A Beach Girls)".

| Şirket | Hesap (üst sınır) | İstek |
|---|---|---|
| 360 Blue | 127 ilan × (3 takvim + 12 hafta × 1 fiyat) | 1.905 |
| Vacasa | 35 ilan × (bağlantının 3 adımı + 12 hafta × 1) | 525 |
| 30A Beach Girls | 145 ev × (1 sayfa + 1 takvim); haftalar için ayrı istek yok | 290 (GÖREV-22'de 145 idi) |
| **Toplam** | | **en çok +2.720** |

Aynı düğme iki toplayıcıyı daha çalıştırır: Konaklama (Book>Direct) yaklaşık 1 sa 3 dk, Yol ağı yaklaşık 1 dk.
**Hepsi birlikte yaklaşık 11 sa 4 dk** (39.833 sn). Bu bizim tahminimizdir ve bir üst sınırdır.

### Zamanlamaya bağlı test

`tests/test_gorev21.py::test_the_estimate_the_spending_and_the_link_table_of_plan_and_writing`

- **Yarış.** Test planı başlatıp çalışmanın "onay bekliyor" durumuna geçmesini bekliyor ve çalışmanın görünümünü o anda okuyordu. Çalışma
  durumunu, işinin son mesajını yazmasından **bir an önce** değiştirir; çalışmanın harcaması (`harcama`) ise iş kapanırken yazılır. Test
  işin bitmesini sonradan bekliyordu ama o anda okuduğu eski görünümü kullanıyordu: iş yavaş kapandığında `harcama` henüz boştu
  (`TypeError: 'NoneType' object is not subscriptable`).
- **Düzeltme.** Test, iş bittikten sonra çalışmayı **yeniden okuyor.** Ayrıca yardımcı `text_job(settled=True)` 15 saniye dolunca işi
  bitmemiş haliyle sessizce döndürüyordu; artık işin bitmesini bekliyor ve bitmezse hata veriyor (sabit bekleme yok).

### Yeni testler

- `tests/test_gorev23.py` (10 test) ve `tests/frontend.test.mjs` içinde 1 test. Fixture'lar 17 Kasım incelemesinin ham yanıtlarından
  (`tests/fixtures/gorev23/`; değer değiştirilmedi): AvantStay'in takvim yanıtı ve hata yanıtı, Vacasa'nın 300 evlik arama sayfası
  (okuyucunun kullanmadığı alanlar atıldı).
  - `avantstay`: takvimden haftalık kira; toplam, ücret ve vergi boş; sorgu metninde `cartPrice` yok; dolu hafta; başka bir konaklamanın
    başladığı gün; girişe ya da çıkışa kapalı gün; en az konaklama; takvimin vermediği gün; hata yanıtı; kanal adı yoksa istek yapılmaması.
  - Çekim: ev başına tek takvim isteği; özetin, ekranın ve kanıt paketinin kirayı toplamdan ayrı tutması.
  - Vacasa: tam listenin alınması (300/300) ve bir ev eksik gelince "liste eksik".
  - Adres kuralı: adresle bağlanma; adı aynı ama adresi tutmayan evin bağlanmaması; başka oda sayısı; 2 km'den uzak; iki aday.
  - Outdoor Shower için yapılandırma olmaması ve gözden geçirilmiş neden; şema 22 → 23 geçişi; tahmin.
- GÖREV-22 testlerinden biri güncellendi (yeni kurulumda 30A Beach Girls'ün fiyatı artık açık).

### Test sonuçları

- `.venv\Scripts\python.exe -m pytest -q`, **iki tam tur arka arkaya** (son kodla):
  - 1. tur: **1.194 geçti, 0 başarısız, 2 atlandı** (8 dk 28 sn).
  - 2. tur: **1.194 geçti, 0 başarısız, 2 atlandı** (8 dk 15 sn).
- `node --test tests/frontend.test.mjs`: **138 geçti, 0 başarısız**.
- Bunlardan önceki bir tam turda (1.193 geçti, 1 başarısız) aynı yarışın **ikinci bir örneği** görüldü:
  `tests/test_text_chain.py::test_the_plan_needs_the_pack_step_and_the_pack_is_made_again_when_older_than_the_data` — plan "onay bekliyor"
  olur olmaz onaylanmak istenmiş, adım ise işi henüz kapanmadığı için hâlâ "çalışıyor" görünmüştü (HTTP 409). Düzeltme ortak yardımcıya
  kondu (`tests/text_helpers.py`, `start_plan`): plan başlatıldıktan sonra adımın "çalışıyor" durumundan çıkması beklenir (sabit bekleme
  değil). Planı başlatıp onaylayan bütün testler bundan yararlanır. Yukarıdaki iki tur bu düzeltmeden sonradır.
- Göç gerçek verinin kopyasında denendi (yukarıda): satır kaybı yok, ilişki bütünlüğü hatası 0.
- GitHub'daki test çalışması: CI_SONUCU

### Belgeler

`docs/M11-KONAKLAMA-FIYATLARI.md` (yeni bölüm: AvantStay'in takvimi, Vacasa'nın tam listesi, LocalVR), `docs/M14-KANIT-PAKETI.md` (yalnız
kira veren şirket), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`, `CALISMA_MANTIGI.md` (dal satırı). Uygulama sürümü 0.24.0.

---

## Canlı istekler ve kurallara uyum

Toplam **11 canlı istek** (`canli-istekler.csv`; ham kopyalar `work/gorev-23/ham/` altında, repoya girmez):

| Nereye | İstek | İzin | Yol |
|---|---|---|---|
| AvantStay'in servisi (arriere.prod.avantstay.com) | 2 | 5 | doğrudan |
| vacasa.com | 1 | 3 | ABD proxy'si |
| golocalvr.com (ve `stay.` alt alan adı) | 8 | 10 | doğrudan |

- Aynı sitede iki istek arası en kısa süre 9 saniye.
- Sepet ya da rezervasyon kaydı açan istek **yapılmadı.** Giriş, ödeme, form yok; doğrulama çözme, gizlenme, IP döndürme yok.
- Proxy yalnız vacasa.com için kullanıldı. realjoy.com'a, 30a-beachgirls.com'a ve AvantStay'in servisine proxy'den istek yapılmadı;
  realjoy.com'a hiç istek yapılmadı.
- Eklenti gerçek sitelerde çalıştırılmadı.

---

## Kullanıcı için gece çekimi tarifi

Çekim yaklaşık **11 saat** sürer. Bilgisayarın uyumaması ve internetin açık kalması gerekir.

**Başlamadan önce**

1. **Chrome'u açın** (eklenti Chrome'un içinde çalışır) ve açık bırakın.
2. **Programı açın** (masaüstündeki "30A Studio").
3. **Eklenti bağlı mı:** Sol menü → **Ayarlar** → **Tarayıcı eklentisi**. Üstte yeşil **"Bağlı · eklenti sürümü …"** yazmalı. "Bağlı
   değil (Chrome kapalı olabilir)" yazıyorsa Chrome'u açıp birkaç saniye bekleyin.
4. **Proxy çalışıyor mu:** Sol menü → **Veri** → **Okuma denemeleri** → "Proxy'nin deneme okuması ve bölge engelli alan adları" bölümü →
   **"Proxy'yi dene"**. Çıkış ülkesi "US" görünmeli. Aynı bölümdeki listede **360blue.com** ve **vacasa.com** duruyor olmalı.
5. **Doğrulama isteyebilecek siteler:** aynı ekranın en altındaki **"Isınma listesi"** bölümü bunları gösterir. Kiralama çekiminde ikisi
   önemli: **oversee.us** ve **exclusive30a.com**. Elle bir şey açmanız gerekmez.
   **RealJoy bu çekimde okunmayacak:** okuyucusu henüz yazılmadı (aşağıdaki "RealJoy için" notuna bakın). 360 Blue ve Vacasa incelemede
   doğrulama göstermedi; 30A Beach Girls engelsiz açılıyor.

**Başlatma**

6. Sol menü → **Veri** → **Kaynaklar** → **"Güncelleme zamanı gelenler"** tablosu → **"Zamanı gelenleri başlat"**. Program önce kendi
   yedeğini alır, sonra sırayla çalışır: Konaklama (Book>Direct), Kiralama şirketleri, Yol ağı. Tabloda "Kiralama şirketleri · Konaklama
   fiyatları" satırında yaklaşık 10 saat yazar.

**Çekim sırasında**

7. **Doğrulama çıkarsa:** eklenti, sizin Chrome'unuzda kendi açtığı ayrı pencerede siteyi açar. Sayfada "insan olduğunuzu doğrulayın"
   kutusu görürseniz **kutuyu işaretleyin**; başka bir şey yapmanız gerekmez. Bir site doğrulama beklerse program onu sona bırakır ve en
   sonda 15 dakika bekler; o sürede geçilmezse siteyi atlar ve kaydeder. 360 Blue ya da Vacasa doğrulama gösterirse programın kendi
   tarayıcı penceresi öne gelir; kutuyu orada işaretleyin.
8. İlerlemeyi sağ üstteki **"İşler"** düğmesinden izleyebilirsiniz.

**Bitince**

9. Sol menü → **Veri** → **Toplama** → **Konaklama** sekmesi → **"Konaklama fiyatları"** bölümü:
   - **"Şirket bazında sonuç"** tablosunda **360 Blue**, **Vacasa** ve **30A Beach Girls** satırlarına bakın. DURUM sütununda
     "tamamlandı" yazmalı; "BULUNAN" ve "FİYATLI SORGU" sütunları kaç ilanın bağlandığını ve fiyatlandığını gösterir. Vacasa'da az ilan
     bağlanması beklenen bir sonuçtur (bağlantıların çoğu artık Vacasa'da olmayan evlere gidiyor).
   - **"Şirketin kendi sitesindeki evler"** tablosunda 30A Beach Girls'ün ev sayısı, mahallesi belirtilen ve belirtilmemiş ev sayıları ve
     yeni **"HAFTALIK KİRA ORTANCASI"** sütunu görünür. Bu sütun yalnız kiradır; ücret ve vergi içinde değildir.
10. Bana **"çekim bitti"** yazın; sonuçları rapora işlerim.

**RealJoy için (çekimden ayrı, iki dakikalık iş).** Okuyucunun yazılabilmesi için bir ilan sayfasının kaydı gerekiyor: Chrome ve program
açıkken Sol menü → **Veri** → **Okuma denemeleri** → **"Eklentinin deneme okuması"** → **"Sorunlu sitelerden birer sayfa dene"**. Chrome'da
açılan sayfada doğrulama kutusu çıkarsa işaretleyin. Bitince programı kapatıp bana "tamam" yazın. Bunu gece çekiminden **önce** yaparsanız
ve fiyat uygun bir istekle geliyorsa RealJoy da aynı çekime girebilir.

---

## Tamamlanamayanlar ve açık kalanlar

1. **RealJoy (Adım 2).** Eklentinin 17 Kasım kaydı yok; okuyucu yazılmadı. Kullanıcının deneme düğmesine basması bekleniyor.
2. **30A Beach Girls'ün toplam fiyatı.** Okunmuyor (sepet kuralı). Yalnız kira okunuyor; bu bir karar noktasıdır (yukarıda).
3. **Outdoor Shower.** LocalVR'de 30A evi yok; 21 ilan fiyatsız kalıyor. Yapılacak iş kalmadı.
4. **Yeni okuyucular gerçek çekimde henüz çalışmadı** (çekimi kullanıcı başlatacak). 360 Blue'nun 127 ilanı çevrimdışı bir denemenin
   sonucudur; Vacasa'da ve 30A Beach Girls'te gerçek sayılar çekimden sonra görülecek.
5. **Gözlem (düzeltilmedi, kapsam dışı):** adres kuralı, sonda tek başına duran yön harfini ("… Blvd E") daire numarası gibi okuyor;
   karşı tarafta aynı adres "East" diye yazılmışsa ikisi bağlanmıyor. Bu yalnız eşleşme kaçırır, yanlış eşleme üretmez.
