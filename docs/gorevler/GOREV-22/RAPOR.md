# GÖREV-22 — Rapor

Tarih: 17 Kasım 2026 · Dal: `gorev-22-kiralama` (main `2848c6f` = `v0.22.0` üzerinden) · Uygulama `0.23.0` · Şema `22`

## Kısa özet

| Konu | Sonuç |
|---|---|
| Bölge engeli ölçümü | **Tamam.** 8 alan adı ölçüldü (18 istek). **360blue.com ve vacasa.com bölge engelli** çıktı ve gerçek veride listeye eklendi. Cottage Rental Agency ile Outdoor Shower'ın **sitesi yok**. sandestin.com ve wyndhamvacationrentals.com bölge engelli değil. |
| 360 Blue (256 ilan) | **Okuyucu yazıldı** (proxy üzerinden, doğrudan istekle). Çevrimdışı eşleme denemesinde 256 ilanın **127'si** şirketin güncel listesine adresle bağlanıyor. |
| Vacasa (21 + 14 Wyndham bağlantısı) | **Okuyucu yazıldı.** Kaç ilanın bağlanacağı ilk çekimde görülecek (aşağıda neden). |
| RealJoy (61 ilan) | **Bekliyor.** Eklentinin deneme kaydı yok; kullanıcıya tarif verildi. |
| 30A Beach Girls (48 ilan; sitede 145 ev) | **Yarım.** Evler şirketin kendi envanteri olarak okunacak biçimde kuruldu (mahalle kuralı, çift sayım, kanıt paketi, testler). **Fiyat sorgusu yazılmadı:** fiyat AvantStay'in ayrı servisinden geliyor ve bu servise deneme isteği bu oturumda yapılamadı. |
| Gerçek veri | Şema 21 → 22; 3 şirket satırı ve 2 bölge engelli alan adı eklendi; başka hiçbir tablo değişmedi. Kiralama fiyat çekimi **başlatılmadı**. |
| Yeni çekim tahmini | En çok **+2.575 istek**; kiralama çekimi yaklaşık **9 sa 58 dk** (son çekim 7 sa 42 dk idi). |

**Tamamlanamayan adımlar:** (1) Adım 4 — RealJoy: kayıt bekleniyor. (2) Adım 5 — 30A Beach Girls'ün fiyatı: izin gerekiyor; ev sayısı ve mahalle dağılımı da ilk çekimde ortaya çıkacak (aşağıda). Ayrıntı: "Tamamlanamayanlar ve açık kalanlar".

Programın hiçbir Claude adımı çalıştırılmadı, alt ajan kullanılmadı, zamanlanmış görev oluşturulmadı, Housing Atlas ve Rota Stüdyo klasörlerine dokunulmadı. Proxy'nin adresi, kullanıcı adı ve parolası hiçbir dosyaya, günlüğe, rapora ya da sohbete yazılmadı; yalnız programın proxy modülü (`studio.proxy.load`) kullanıldı.

---

## Adım 1 — main ve dal

- Program kapalıydı (`data/calisiyor.json` yok).
- `gorev-21-katmanlar` main'e fast-forward ile alındı (`57088be..2848c6f`), `v0.22.0` açıklamalı etiketi konuldu; ikisi push edildi.
- `gorev-22-kiralama` dalı güncel main'den açıldı. `studio/destinations/thirty_a_claude/` altında kullanıcı değişikliği yoktu; "talimat" commit'i gerekmedi.

---

## Adım 2 — Bölge engeli ölçümü

**Yöntem.** Her alan adı için aynı sayfa bir kez doğrudan, bir kez programın proxy modülüyle istendi. Alan adı başına en çok 3 istek; aynı sitede iki istek arası en az 8 saniye (ölçülen en kısa aralık 8 sn); yönlendirme izlenmedi (her adım ayrı istek); programın kendi tarayıcısı kullanılmadı. Ham yanıtlar `work/gorev-22/ham/olcum-<alan adı>/` altında (repoya girmez); her isteğin dökümü `olcum-istekleri.csv` içinde (ham kopyanın adı ve SHA-256'sıyla).

**Sınıflandırma kuralı** artık programın içinde ve testli (`studio/sources/region_probe.py`): doğrudan istek ret/engel/yanıtsız, proxy üzerinden site normal yanıt veriyorsa **bölge engeli**; proxy üzerinden de aynı ret/engel/doğrulama geliyorsa ya da site iki yoldan da açılıyorsa **bölge engeli değil**; iki yoldan da siteye ulaşılamıyorsa (ya da gelen sayfa alan adı kayıt firmasının sayfasıysa) **site yok**.

| Alan adı | Doğrudan yanıt | Proxy yanıtı | Sınıf | Listeye eklendi mi | Ham kopyalar (`ham/` altında) |
|---|---|---|---|---|---|
| `360blue.com` | 403 · "Attention Required! \| Cloudflare" (engel sayfası) | 301 (aynı sitede adres düzeltmesi) → 404 · "Error Page" (sitenin kendi sayfası, 97 KB; menüsü ve bağlantılarıyla) | **bölge engeli** | **Evet** | `olcum-360blue.com/01-dogrudan.bin`, `02-proxy.bin`, `03-proxy.bin` |
| `vacasa.com` | 403 · "ERROR: The request could not be satisfied" (CloudFront: ülkenizden erişim engelli) | 200 · "Dunes of Seagrove \| Santa Rosa Beach \| Professionally Cleaned \| Vacasa" | **bölge engeli** | **Evet** | `olcum-vacasa.com/01-dogrudan.bin`, `02-proxy.bin` |
| `wyndhamvacationrentals.com` | 301 → `vacasa.com/unit.php?UnitID=32791` | 301 → aynı adres | bölge engeli değil | Hayır | `olcum-wyndhamvacationrentals.com/01-…`, `02-…` |
| `cottagerentalagency.com` | 301 → `sandestin.com/accommodations/cottage-rental-agency` | 301 → aynı adres | bölge engeli değil | Hayır | `olcum-cottagerentalagency.com/01-…`, `02-…` |
| `rentals.cottagerentalagency.com` | yanıt yok (DNS kaydı yok) | yanıt yok (proxy bağlantıyı kuramadı) | **site yok** | Hayır | — |
| `sandestin.com` | 403 · "Access denied \| Sandestin Golf and Beach Resort" | 403 · aynı sayfa (aynı boyut: 349.014 bayt) | bölge engeli değil | Hayır | `olcum-sandestin.com/01-…`, `02-…` |
| `outdoorshower30a.com` | yanıt yok (zaman aşımı) | https: yanıt yok; http: 200 · "Registrant WHOIS contact information verification \| Namecheap.com" (alan adı kayıt firmasının sayfası) | **site yok** | Hayır | `olcum-outdoorshower30a.com/03-proxy.bin` |
| `golocalvr.com` (aşağıya bakın) | 301 (kendi sitesinde) | 301 (aynı) | bölge engeli değil | Hayır | `olcum-golocalvr.com/01-…`, `02-…` |

Notlar:

- **360 Blue.** Ölçümün üç isteğinde proxy üzerinden 200 görülmedi (Book>Direct'teki ilan adresi artık yok: 301, sonra sitenin kendi "Error Page"i). Sitenin kendisi engelsiz yanıt verdiği için bölge engeli sayıldı; incelemenin ilk sayfası bunu doğruladı: `https://www.360blue.com/destinations/seaside` proxy üzerinden **200 · "Seaside, FL Vacation Rentals \| 30A \| 360 Blue"** (`ham/360blue/01-proxy.bin`).
- **sandestin.com.** "Access denied" sayfası sitenin kendi teması içinde, iki yoldan da aynı: kaldırılmış bir sayfa (Drupal), ülke engeli değil.
- **Cottage Rental Agency (92 ilan): site yok.** Kiralama alan adının DNS kaydı yok; ana alan adı iki yoldan da sandestin.com'daki kaldırılmış sayfaya yönleniyor. Güncel site arandı (iki web araması: şirket adı, "kapandı / devredildi"): yeni bir site ya da devir haberi bulunamadı; arama sonuçları hâlâ `cottagerentalagency.com`'u gösteriyor.
- **Outdoor Shower (21 ilan): site yok; şirket LocalVR'ye devredilmiş.** Alan adı askıda. Web aramasında LocalVR'nin duyurusu bulundu: "LocalVR Expands in 30A Florida with Acquisition of Outdoor Shower" (30 ev). Bu yüzden `golocalvr.com` da ölçüldü: bölge engeli yok, doğrudan açılıyor. LocalVR için okuyucu yazmak bu görevin kapsamında değildi (yalnız bölge engelli çıkan şirketler); sonraki bir görev için aday.

**Listeye ekleme (gerçek veri, yedekten sonra).** Program gerçek veriyle açıldı ve iki alan adı arayüzün kullandığı istekle eklendi (Sol menü → Veri → Okuma denemeleri → "Proxy'nin deneme okuması ve bölge engelli alan adları" → "Listeye ekle" düğmesinin gönderdiği `POST /api/abd-proxy/bolge-engelli`; ölçümün kanıtı da satıra yazılsın diye istek artık isteğe bağlı `baslik`, `adres`, `kanit` alanlarını kabul ediyor).

| Alan adı | Listedeki kanıt satırı |
|---|---|
| 360blue.com | başlık "Attention Required! \| Cloudflare"; adres `https://www.360blue.com/rentals/properties/watersound-west-10-blue-moon-lane/`; "17.11.2026 ölçümü (GÖREV-22): doğrudan istek 403 Cloudflare engel sayfası; ABD proxy'si üzerinden sitenin kendi sayfaları (301, 404 'Error Page', inceleme 200)" |
| vacasa.com | başlık "ERROR: The request could not be satisfied"; adres `https://www.vacasa.com/usa/Dunes-Of-Seagrove-Santa-Rosa-Beach/`; "17.11.2026 ölçümü (GÖREV-22): doğrudan istek 403 CloudFront ülke engeli; ABD proxy'si üzerinden 200, sitenin sayfası" |

---

## Adım 3 — Bölge engelli çıkan şirketlerin okuyucuları

İnceleme proxy üzerinden, şirket başına en çok 10 sayfa, iki istek arası en az 8 sn: 360 Blue 9 sayfa, Vacasa 10 sayfa. Bütün istekler `canli-istekler.csv` içinde.

### Şirket tablosu (altı şirketin son durumu)

| Şirket | Book>Direct ilanı | Altyapı | Okuma yolu | Sonuç ya da okunamama sebebi |
|---|---|---|---|---|
| **360 Blue** (360blue.com) | 256 | Natural Retreats'in rezervasyon motoru (site Adobe Experience Manager üzerinde; arkada Track) | ABD proxy'si üzerinden doğrudan istek | **Okuyucu yazıldı** (`nrbe`). Ev listesi, müsaitlik takvimi ve fiyat herkese açık GET adreslerinden geliyor. Book>Direct bağlantıları sitenin eski adresleri (hepsi 301 → 404), bu yüzden ilanlar şirketin listesine **adres kuralıyla** bağlanıyor. Çevrimdışı denemede 256 ilanın 127'si bağlandı. |
| **Vacasa** (vacasa.com; wyndhamvacationrentals.com bağlantıları buraya yönleniyor) | 21 (+14) | Vacasa (Casago'ya geçmiş; yeni ilan numaraları) | ABD proxy'si üzerinden doğrudan istek (Wyndham bağlantısının ilk adımı doğrudan) | **Okuyucu yazıldı** (`vacasa`). Fiyat tek GET isteğiyle geliyor (kira, temizlik ücreti, vergi kalemleri, toplam). Bağlantılardaki ilan numaraları eski; site kendi listesinde her evin eski numarasını veriyor, eşleme bununla. Kaç ilanın bağlanacağı ilk çekimde görülecek. |
| **30A Beach Girls** (30a-beachgirls.com) | 48 | AvantStay | doğrudan (engel yok) | **İlanlara bağlanmıyor; şirketin kendi envanteri olarak okunacak** (Adım 5). Fiyat sorgusu yazılmadı. |
| **RealJoy** (realjoy.com) | 61 | ICND rezervasyon motoru (arkada Track) | eklenti (bot koruması; proxy kullanılmaz) | **Bekliyor** (Adım 4). |
| **Cottage Rental Agency** (rentals.… 82, ana alan adı 10) | 92 | — | — | **Site yok.** Okunacak bir site bulunamadı. |
| **Outdoor Shower** (outdoorshower30a.com) | 21 | — (Book>Direct kaydında LiveRez) | — | **Site yok;** şirket LocalVR'ye devredilmiş. LocalVR için okuyucu yok. |

Toplam: bu altı şirket 513 ilan.

### Bütün eksikler sonunda nerede duruyor

| | İlan | Açıklama |
|---|---|---|
| Fiyatlanabilir oldu (okuyucusu var, eşleşmesi bekleniyor) | **127** | 360 Blue: adres kuralıyla şirketin 17 Kasım'daki listesine bağlanan ilanlar (çevrimdışı deneme; gerçek çekimde liste değişmiş olabilir). |
| Okuyucusu var, kaçının bağlanacağı çekimde görülecek | **25** | Vacasa: bağlantısında ilan numarası olan 11 ilan + 14 Wyndham bağlantısı. Denenen iki eski numara (13293, 32663) artık bir eve gitmiyor; bir kısmı sitede kalmamış olabilir. |
| Okuyucusu var ama bağlanamıyor | **129 + 10** | 360 Blue'da 129 ilan: 120'sinin adresi şirketin güncel listesinde yok (büyük olasılıkla artık 360 Blue yönetmiyor), 7'sinde Book>Direct oda sayısı vermiyor (ikisi şirketin ofis kaydı), 2'si belirsiz (aynı adreste birden çok aday). Vacasa'da 10 "ilan" aslında bir evin değil bir yerleşkenin ya da bölgenin sayfası (ör. "Vacasa - Seagrove"); fiyatlanacak tek bir ev yok. |
| İlanlara bağlanmıyor (kural gereği) | **48** | 30A Beach Girls. Yerine şirketin kendi sitesindeki evler ayrı okunacak. |
| Bekliyor | **61** | RealJoy. |
| Site yok | **113** | Cottage Rental Agency 92, Outdoor Shower 21. |

Karşılaştırma için: son çekimde (10 Ekim 2026) 2.389 ilanın 1.131'i şirket sitesinde bulunmuş, 1.080'ine fiyat alınmıştı.

### 360 Blue — ne bulundu

- `GET /api/nrbe/units.json?brandId=193&brandId=195&resourcePath=…&pageSize=-1`: sitenin "30A" koleksiyonundaki **585 ev** tek istekte (ad, sayfa adresi, 6 ondalıklı koordinat, oda, banyo, kapasite). 125 evin sayfası kardeş marka Callista Vacations'ın alan adında; fiyatları yine 360blue.com'un servisinden soruluyor.
- Listede ayrı bir adres alanı yok; evin sokak adresi adının sonunda: `Seaside "Sea ya real soon" 73 Odessa Street`. Okuyucu **yalnız bu adresi** alır (585 evin 579'unda sokak numarasıyla başlayan bir adres var) ve programın adres kuralını uygular: aynı sokak numarası ve sokak, aynı daire numarası, aynı oda sayısı, tek aday; koordinatlar 2 km'den uzaksa eşlenmez. Ad karşılaştırılmaz.
- `GET /api/nrbe/availability-calendar.json?unitId&startDate&endDate`: gün gün müsaitlik (site altı ayı bir istekte soruyor; okuyucu da öyle).
- `GET /api/nrbe/reservation-quotes.json?unitId&arrivalDate&departureDate&adults&children`: örnek (ev 873, 10–17 Nisan 2027, 2 yetişkin) → ara toplam 6.975,52 $, vergi 837,09 $, toplam 7.812,61 $. Site ücret kalemi göstermiyor; ara toplam sitenin kendi sayısı olarak saklanır.
- Site satamadığı tarih için sebep söylemeyen bir hata döndürüyor (HTTP 500, "An unexpected error has occurred"). Bu yüzden takvimin dolu gösterdiği hafta **takvimden** "müsait değil" yazılır ve fiyat sorulmaz; takvim boş gösterdiği halde hata gelirse satır "fiyat yok"tur (müsaitlik bilinmiyor) ve sitenin sözü yazılır.
- Book>Direct bağlantıları sorulmaz (`dead_links`): 256 ilan için 512 boş istek ve proxy hızında yaklaşık 77 dakika harcanmaz.

### Vacasa — ne bulundu

- Ev sayfası (`/unit/<numara>`): evin numarası ve koordinatı var, sokak adresi yok.
- Fiyat: `GET /guest-com-api/get-unit-price-quote?unit_id&check_in&check_out&adults&children&pets`. Örnek (ev 1012379, 10–17 Nisan 2027): kira 3.249,23 $, temizlik ücreti 182,00 $, vergi 411,74 $ (üç kalem), toplam 3.842,97 $. Sayfanın kendi kutusu bu isteği doğrulama belirteci olmadan gönderiyor (sitenin ayarı: `recaptcha: false`); okuyucu da aynısını yapar. Site bir gün bu istek için doğrulama isterse okuyucu durur, aşmaya çalışmaz.
- "Dolu" ve "en az konaklama" yanıtları sitenin kendi kodlarıyla gelir (`booked`, `min-stay-not-met`) ve ayrı tutulur.
- Arama sayfası (`/search?place=/usa/Highway-30A/`): 30A'da 300 ev; her evin koordinatı, odası, banyosu ve **eski ilan numarası** (`migrated_from_unit_id`). Book>Direct bağlantısındaki numara bu eski numarayla tam bir eve denk geliyorsa ilan o eve bağlanır ("bağlantı" yöntemi). Bu bir ad eşlemesi değildir.
- **Doğrulanamayan nokta:** arama sayfası ilk açılışta 24 evi veriyor. Sitenin kendi betiğine göre adres `page_limit` parametresini kabul ediyor; okuyucu ikinci istekte bütün evleri ister. 10 sayfalık inceleme sınırı dolduğu için bu denenemedi. Liste eksik gelirse okuyucu **tahmin yürütmez**: şirket o çekimde "liste eksik" hatasıyla kaydedilir, hiçbir ilan yanlış eve bağlanmaz. Bu durumda sonraki görevde sayfalama isteği yazılmalı.
- wyndhamvacationrentals.com bölge engelli değil; yalnız vacasa.com'a yönlendiriyor. Bu yüzden Wyndham bağlantısı **doğrudan**, yönlendiği vacasa.com adresi **proxy'den** istenir (aşağıda).

### Programda değişenler

- **Yalnız listedeki alan adları proxy'den gider.** Eskiden bölge engelli bir şirketin bütün istekleri proxy'den gidiyordu. Artık yalnız listedeki alan adları (ve alt alan adları) proxy'den, şirketin öbür alan adları doğrudan gider; ham kayıtta her isteğin yolu ayrı yazılır.
- Okuma sırası değişmedi: proxy üzerinden doğrudan istek → programın kendi tarayıcısı proxy'yle → atla ve kaydet. Eklenti bu alan adları için kullanılmaz. Proxy üzerinden doğrulama çıkarsa onu kullanıcı geçer. Bu iki şirket incelemede doğrulama göstermedi; ısınma listesine girmeleri gerekmedi.
- İki yeni uyarlayıcı (`nrbe`, `vacasa`), "bağlantıdaki ilan numarası" kuralı, ölü bağlantıların sorulmaması. Ayrıntı: `docs/M11-KONAKLAMA-FIYATLARI.md`.

---

## Adım 4 — RealJoy

- Eklentinin deneme kayıtlarına bakıldı (`data/raw/eklenti/`): son kayıt klasörü **11 Kasım 2026**. 16 Kasım akşamından sonra deneme çalıştırılmamış; RealJoy'un ilan sayfasının ham kaydı **yok**.
- Kullanıcıya sohbette tarif verildi (ekrandaki adlarla): *Programı açın. Sol menü → Veri → Okuma denemeleri → "Eklentinin deneme okuması" bölümü → "Sorunlu sitelerden birer sayfa dene". Chrome'da açılan sayfada doğrulama çıkarsa kutuyu işaretleyin. Bitince "tamam" yazın.*
- Rapor yazıldığı sırada yanıt gelmemişti. **Okuyucu yazılmadı.** Kayıt gelince yapılacak iş: kayıttan fiyatın hangi istekle geldiğine bakmak; eklentinin okuyabildiği bir sayfa yüklemesiyle (sayfanın kendisi ya da herkese açık bir GET adresi) geliyorsa okuyucuyu yazmak, tıklama ya da form gerekiyorsa yazmayıp sebebini kaydetmek.

---

## Adım 5 — 30A Beach Girls: şirketin kendi envanteri

**Kurulan yol.** Programda benzer bir örnek vardı: tek bir topluluğun resmî kiralama programındaki "kendi envanter" (Alys Beach). Aynı tablolar ve aynı akış kullanıldı, mahalleler arası çalışacak biçimde genişletildi (`inventory.own`):

- Şirketin alfabetik ev listesi (`/alphabetical-property-list`) ve her evin kendi sayfası okunur.
- Ev, site onu "Emerald Coast - 30A" bölgesine koyuyorsa alınır; başka bölgedeki evler (ör. Panama City Beach) alınmaz ve sayıları şirket satırında yazar.
- **Mahalle yalnız sitenin ev için söylediği yer adından alınır**; koordinattan ya da adresten mahalle çıkarılmaz. Yer adı bir mahalle adı değilse ev **mahallesiz** kalır: hiçbir mahallenin ortancasına girmez, "mahallesi belirtilmemiş" diye ayrı sayılır. Bunun için şema 22'de kendi envanter satırının mahalle alanı boş olabilir hale getirildi.
- Sitenin yer adlarından **"Santa Rosa Beach" ve "Inlet Beach" bilerek mahalleye çevrilmedi.** Bu sitede bunlar posta adresindeki şehir: elimizdeki ham kopyada site, kendi açıklamasında "Prominence South'ta" dediği bir evin şehrine "Inlet Beach" yazıyor. Böyle bir evi Inlet Beach mahallesine yazmak sitenin söylemediği bir şeyi yazmak olurdu. Seagrove Beach, Seacrest, WaterSound, Rosemary Beach, Blue Mountain Beach gibi adlar ise mahalle adıdır ve eşlenir.
- **Çift sayım yok.** Bir ev bir Book>Direct ilanına bağlanmışsa (bağlantıdaki numara evin numarasıysa, aynı adres ya da adres kuralı) kendi envantere girmez. GÖREV-20'ye göre şirketin 48 Book>Direct bağlantısının hepsi 404 ve numaraları sitedeki numaralarla tutmuyor; yine de kural yazıldı ve testle gösterildi.
- Kanıt paketinde ve ekranda kaynağıyla ayrı görünür: **"şirketin kendi sitesindeki evler; Book>Direct ilanlarına bağlanmadı"**. Kapsanan şirketler bloğuna (`lodging_coverage`) yeni bir tablo eklendi: şirket, ev sayısı, mahallesi belirtilen, mahallesi belirtilmemiş, fiyatlı ev.

**Sayılar.**

| | |
|---|---|
| Sitenin alfabetik listesindeki ev | **145** (16 Kasım 2026 ham kopyası) |
| Kaçında bölge (mahalle) adı var, mahallelere dağılımı | **Henüz bilinmiyor.** Listede yer adı yok; yer adı her evin kendi sayfasında. Elimizde iki ev sayfasının ham kopyası var: biri "Emerald Coast - 30A" / şehir "Inlet Beach" (mahallesiz kalır), biri "Panama City Beach" bölgesinde (alınmaz). Ana sayfadaki altı evlik örnek: 3 Panama City Beach, 2 Santa Rosa Beach, 1 Watersound. 145 sayfanın okunması bir çekim işidir ve bu görevde çekim başlatılmadı; dağılım kullanıcının ilk çekiminden sonra programda görünecek (Veri → Toplama → Konaklama → "Şirketin kendi sitesindeki evler" tablosu). |

**Fiyat neden yok.** Sitenin fiyatı kendi alan adından değil, AvantStay'in ayrı bir servisinden geliyor (`arriere.prod.avantstay.com`). Sitenin betiğinden iki sorgunun biçimi çıkarıldı (takvim ve fiyat dökümü; `docs/M11-KONAKLAMA-FIYATLARI.md`'de yazılı). Sorguyu doğrulamak için bu servise bir deneme isteği göndermek istedim; **bu oturumda bu istek engellendi** ve etrafından dolaşılmadı. Hiçbir yanıt görülmediği için tutarların birimi, takvimdeki durum sözleri ve ret metinleri bilinmiyor; görülmemiş bir yanıt için okuyucu yazmak yanlış fiyat kaydetme riski taşırdı. Bu yüzden:

- Fiyat sorgusu **yazılmadı**; yapılandırmada kapalı (`quotes: false`). Evler listelenir, satırlarında "Fiyat sorulmadı: … henüz doğrulanmadı" yazar.
- Dikkat edilecek bir nokta daha: fiyat dökümü sorgusunun yanıtında bir sepet numarası dönüyor; sorgu sunucuda her soruda bir sepet kaydı açıyor olabilir. Etkinleştirmeden önce buna bakılmalı.
- Kullanıcı sohbette izin verirse 3–5 deneme isteğiyle doğrulanıp okuyucu yazılabilir.

---

## Adım 6 — Gerçek veri, çekim tahmini, testler, belgeler

### Gerçek veri: ne değişti

1. **Yedek.** Program kapalıyken `data/` klasörünün tamamı kopyalandı: `work/yedek/20261117-1220/` (45.549 dosya, 1.762.073.225 bayt; kaynakla aynı boyut).
2. **Göç önce kopyada denendi** (`work/gorev-22/temp-data`): şema 21 → 22, satır 188.518 → 188.521 (yalnız 3 şirket satırı), ilişki bütünlüğü hatası 0, eksilen tablo yok; kendi envanterin 146 satırı ve 1.241 fiyat satırı yerinde.
3. **Program gerçek veriyle normal biçimde açıldı** (sürüm 0.23.0). Açılışta program kendi yedeğini aldı (`data/backups/studio-v21-….sqlite3`) ve şema 22'ye geçti. Sonra iki alan adı listeye eklendi. Program kapatıldı.

| | Önce | Sonra |
|---|---|---|
| Şema | 21 | 22 |
| Tablo sayısı | 81 | 81 |
| Toplam satır | 188.518 | 188.523 |
| `destination_agency_sites` (yapılandırılmış şirket) | 24 | 27 (360 Blue, Vacasa, 30A Beach Girls) |
| `region_blocked_hosts` (bölge engelli alan adı) | 4 | 6 (360blue.com, vacasa.com) |
| İlişki bütünlüğü hatası | 0 | 0 |

Başka hiçbir tablo değişmedi. **Kiralama fiyat çekimi başlatılmadı.**

### Çekim: yeni tahmini istek sayısı ve süre

"Güncelleme zamanı gelenler" tablosu gerçek veride şunu gösteriyor (`ekran/01-guncelleme-zamani-gelenler.png`): **Kiralama şirketleri · Konaklama fiyatları — ~9 sa 58 dk**; altında "yeni şirketler dahil: 360 Blue 256 ilan, en çok +1905 istek (ABD proxy'siyle); Vacasa 35 ilan, en çok +525 istek (ABD proxy'siyle); 30A Beach Girls 48 ilan, kendi sitesinde 145 ev, en çok +145 istek".

| Şirket | Hesap (üst sınır) | İstek | Tek başına süre |
|---|---|---|---|
| 360 Blue | bağlanması beklenen 127 ilan × (3 takvim isteği + 12 hafta × 1 fiyat isteği); bağlantılar sorulmuyor | 1.905 | 4 sa 46 dk (istek başına 8 sn + 1 sn) |
| Vacasa | 35 ilan × (bağlantının 3 adımı + 12 hafta × 1) | 525 | 1 sa 19 dk |
| 30A Beach Girls | 145 ev × 1 sayfa (fiyat sorulmuyor) | 145 | 7 dk |
| **Toplam** | | **en çok +2.575** | |

- Son çekim 21.129 istek ve 7 sa 42 dk idi. Şirketler üçer üçer yan yana okunduğu için yeni şirketlerin süresi düz toplanmaz: tahmin, son çekimin şirketlerini (her biri kendi isteği ve hızıyla) yeni şirketlerle ve yeni şirketler olmadan aynı düzende yerleştirir ve son çekimin gerçek süresini bu orana göre büyütür: **+2 sa 15 dk → yaklaşık 9 sa 58 dk**.
- Bu bir üst sınırdır ve bizim tahminimizdir: takvimin dolu gösterdiği haftalar sorulmaz, bağlanmayan Vacasa ilanları fiyat sormaz. Hız kuralı gevşetilmedi (proxy üzerinden iki istek arası 8 sn).
- Aynı düğme iki toplayıcıyı daha çalıştırır (zamanı gelmiş): Konaklama (Book>Direct) ~1 sa 3 dk ve Yol ağı ~1 dk. **Hepsi birlikte yaklaşık 11 saat.**

### Testler

- Yeni: `tests/test_gorev22.py` (22 test) ve `tests/frontend.test.mjs` içinde 2 test. Fixture'lar incelemenin ham kopyalarından kesildi (`tests/fixtures/gorev22/`; değer değiştirilmedi, uzun metinler ve resimler atıldı). Testler canlı ağa ve gerçek proxy'ye bağlanmaz.
  - Bölge engeli sınıflandırması: üç sınıf, park edilmiş alan adı, 17 Kasım ölçümünün kayıtları.
  - `nrbe`, `vacasa`, `avantstay` uyarlayıcıları (sayfa, liste, fiyat, dolu hafta, retler, eksik liste, bağlantıdaki numara).
  - Bölge engelli alan adının proxy'den, öbürlerinin doğrudan gitmesi (Wyndham bağlantısı doğrudan, vacasa.com proxy'den); ham kayıtta yolun doğru yazılması.
  - 30A Beach Girls: yer adı mahalle adı olmayan evin mahallesiz kalması ve hiçbir mahalle ortancasına girmemesi; Book>Direct ilanına bağlanan evin iki kez sayılmaması.
  - Kanıt paketinde yeni şirket satırları; tahmin; şema 21 → 22 geçişi.
- Tam takım sonucu: aşağıda "Test sonuçları".

### Belgeler

`docs/M11-KONAKLAMA-FIYATLARI.md` (yeni bölüm ve durum), `docs/M18-ABD-PROXY-BOLGE-ENGELI.md` (ölçüm kuralı ve 17 Kasım tablosu), `docs/M14-KANIT-PAKETI.md` (yeni tablo), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`, `CALISMA_MANTIGI.md` (dal satırı). Uygulama sürümü 0.23.0.

---

## Kullanıcı için çekim tarifi

Çekim yaklaşık **11 saat** sürer; bilgisayarın uyumaması ve internetin açık kalması gerekir. Başlamadan önce:

1. **Chrome'u açın** (eklenti Chrome'un içinde çalışır).
2. **Programı açın** (masaüstündeki "30A Studio").
3. **Eklenti bağlı mı bakın:** Sol menü → **Ayarlar** → **Tarayıcı eklentisi**. Üstte yeşil **"Bağlı · eklenti sürümü …"** yazmalı. "Bağlı değil (Chrome kapalı olabilir)" yazıyorsa Chrome'u açıp birkaç saniye bekleyin.
4. **Proxy çalışıyor mu bakın:** Sol menü → **Veri** → **Okuma denemeleri** → "Proxy'nin deneme okuması ve bölge engelli alan adları" bölümü → **"Proxy'yi dene"**. Çıkış ülkesi "US" görünmeli. Aynı bölümdeki listede **360blue.com** ve **vacasa.com** duruyor olmalı.
5. **Isınma listesi:** aynı ekranda en altta **"Isınma listesi"** bölümü hangi sitelerin doğrulama isteyebileceğini gösterir. Kiralama çekimi için ikisi önemli: **oversee.us** ve **exclusive30a.com** (korumalı siteler). Elle bir şey açmanız gerekmez.

Başlatma:

6. Sol menü → **Veri** → **Kaynaklar** → **"Güncelleme zamanı gelenler"** tablosu → **"Zamanı gelenleri başlat"**. Program önce kendi yedeğini alır, sonra sırayla çalışır: Konaklama (Book>Direct), Kiralama şirketleri, Yol ağı.

Çekim sırasında:

7. **Doğrulama çıkarsa:** eklenti, sizin Chrome'unuzda kendi açtığı ayrı pencerede siteyi açar. Sayfada "insan olduğunuzu doğrulayın" kutusu görürseniz **kutuyu işaretleyin**; başka bir şey yapmanız gerekmez. Bir site doğrulama beklerse program onu sona bırakır ve en sonda 15 dakika bekler; o sürede geçilmezse siteyi atlar ve kaydeder. 360 Blue ya da Vacasa doğrulama gösterirse (incelemede göstermediler) programın kendi tarayıcı penceresi öne gelir; kutuyu orada işaretleyin.
8. İlerlemeyi sağ üstteki **"İşler"** düğmesinden izleyebilirsiniz.

Bitince:

9. Sol menü → **Veri** → **Toplama** → **Konaklama** sekmesi → **"Konaklama fiyatları"** bölümü:
   - **"Şirket bazında sonuç"** tablosunda **360 Blue**, **Vacasa** ve **30A Beach Girls** satırlarına bakın. DURUM sütununda "tamamlandı" yazmalı; "BULUNAN" ve "FİYATLI SORGU" sütunları kaç ilanın bağlandığını ve fiyatlandığını gösterir. Vacasa'da "hata" ve "liste eksik" yazarsa bu beklenen olasılıklardan biridir (yukarıda anlatıldı); bana haber verin.
   - **"Şirketin kendi sitesindeki evler"** tablosunda 30A Beach Girls'ün ev sayısı, mahallesi belirtilen ve belirtilmemiş ev sayıları görünür.
10. Bana **"çekim bitti"** yazın; sonuçları rapora işlerim.

---

## Canlı istekler ve kurallara uyum

- Toplam **47 canlı istek** (`canli-istekler.csv`): ölçüm 18 (8 doğrudan, 10 proxy), 360 Blue incelemesi 9 (proxy), Vacasa incelemesi 10 (proxy), 30A Beach Girls sitesinden 10 betik dosyası (doğrudan; site engelli değil). Aynı sitede iki istek arası en kısa süre 8 sn.
- Ayrıca 3 web araması (Cottage Rental Agency'nin ve Outdoor Shower'ın güncel sitesi).
- AvantStay'in servisine istek **yapılmadı** (engellendi).
- Giriş, ödeme, rezervasyon, form yok; doğrulama çözme, gizlenme, IP döndürme yok. Proxy yalnız ölçümde ve bölge engelli çıkan iki alan adında kullanıldı; realjoy.com ölçülmedi ve proxy'yle açılmadı.

---

## Tamamlanamayanlar ve açık kalanlar

1. **RealJoy (Adım 4).** Eklenti deneme kaydı yok; kullanıcının "Sorunlu sitelerden birer sayfa dene"yi çalıştırması bekleniyor. Okuyucu yazılmadı.
2. **30A Beach Girls fiyatı (Adım 5).** AvantStay'in servisine deneme isteği yapılamadı; fiyat sorgusu yazılmadı ve kapalı. Ev sayısı (145) biliniyor; kaçında mahalle adı olduğu ve mahallelere dağılımı ilk çekimde ortaya çıkacak.
3. **Vacasa'nın tam ev listesi.** `page_limit` ile tam liste gelip gelmediği denenemedi (inceleme sınırı). Gelmezse şirket ilk çekimde "liste eksik" diye kaydedilir; sayfalama isteği sonraki görevde yazılır.
4. **Yeni okuyucular gerçek çekimde henüz çalışmadı** (çekimi kullanıcı başlatacak). Okuyucular incelemenin ham yanıtlarıyla sınandı.
5. **LocalVR** (Outdoor Shower'ın evleri) ve Cottage Rental Agency için okunacak site yok / okuyucu yok.
6. Rapordaki "127 ilan" bir çevrimdışı denemenin sonucudur; gerçek sayı çekimden sonra kesinleşir.

## Test sonuçları

(aşağıya çalıştırıldıktan sonra eklendi)
