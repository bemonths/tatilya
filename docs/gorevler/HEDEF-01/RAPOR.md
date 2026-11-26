# HEDEF-01 — Rapor: işçiler, deneme çekimi ve gece çekimine hazırlık

*26 Kasım 2026. Dal `hedef-01`; main'e fast-forward; etiket `v0.27.0`. Uygulama 0.27.0, şema 25, eklenti 0.21.0.*

## Kısa özet

- `gorev-25-realjoy-sorgu` main'e alındı, `v0.26.0` etiketi kondu.
- **İşçiler** yazıldı: doğrudan bağlantı ve proxy listesindeki her çalışan proxy bir işçi; kiralama çekimi ilan ilan işçilere dağıtılıyor;
  site başına en çok 4 işçi, işçi başına site aralığı en az 8 sn, 429/engel/doğrulamada bütün işçiler yavaşlıyor, tekrarında tek işçi;
  düşen ya da listeden çıkan proxy'nin işi başka işçiye geçiyor; havuz canlı; tarayıcı gerektiren siteler kendi sıralarında.
- **Proxy listesi** ekranı (Ayarlar → ABD proxy'si): toplu ekleme, her satır tek tek denenir, parolalar yalnız Windows Kimlik Bilgisi
  Yöneticisi'nde.
- **Deneme çekimi** (Sol menü → Veri → Okuma denemeleri → "Deneme çekimini başlat"): bütün toplayıcılar küçük ölçekte, gerçek sitelerde,
  işçilerle, veritabanının kopyasında. Üç kez gerçek sitelerde çalıştırıldı; bulunan hatalar düzeltildi; son denemede 13 toplayıcının 11'i, 28 kiralama şirketinin 21'i okundu
  (kalan 7 şirket yalnız Mucahit'in yapabileceği işe bağlı: 5'i eklenti site izni, 2'si çalışan ABD proxy'si).
- **Tahmin** işçi sayısına göre: 1 işçi ~47 sa, 2 işçi ~27 sa, 5 işçi ~11 sa, 10 ve 20 işçi ~6 sa.
- Kayıtlı tek proxy 26 Kasım'da çalışmadı; Mucahit gece 12 proxy girdi (hepsi çalışıyor). **Bugünkü tahmin: 13 işçiyle kiralama ~6 sa 10 dk,
  bu gecenin toplamı ~7 sa 15 dk.** 13 işçili 4. deneme çekiminde 28 kiralama şirketinin hepsi okundu.

---

## 1. main ve etiket

- `main` `f87582c` → `833382a` (fast-forward), açıklamalı etiket `v0.26.0` ("GÖREV-24 + GÖREV-25 (RealJoy, page queries)"), push edildi.
- İş dalı `hedef-01`. Talimat klasöründe (`studio/destinations/thirty_a_claude/`) kullanıcı değişikliği yoktu; talimat commit'i gerekmedi.
- Ara main'e alma: `43f8f82` (işçiler, deneme çekimi; CI 45859402665 başarılı). Son main ve `v0.27.0`: bölüm 9.

## 2. Kararlar (gerekçeleriyle)

1. **8 sn kuralı.** Kodda sıradan kiralama sitelerinde iki istek arası 2 sn idi (`REQUEST_GAP`), korumalı sitelerde 6 sn. Hedef "bir işçi
   aynı siteye en az 8 sn" diyor; uyguladım (korumalılar dahil 8 sn). Site başına 4 işçiyle siteye düşen yük en çok 0,5 istek/sn: eski tek
   çıkışın 2 sn aralığıyla aynı. Sonuç: az işçiyle çekim eskisinden uzun sürer (2 işçi ~27 sa; eski tahmin ~13,5 sa), işçi arttıkça kısalır.
2. **İş birimi** "şirket + ilan": ilan sayfası ve o ilanın bütün haftalarının fiyatı tek işte. Böylece bir ilanın fiyat soruları aynı
   işçinin aynı oturumunda kalır, devirde yarım iş sayılmaz. Şirketin kendi listesi tek iş; listeden eşlenen ilanlar ve kendi envanter
   evleri yine tek tek iş; yayımlanmış kira okuması şirketin son işi.
3. **Korumalı siteler programın kendi tarayıcısıyla.** Hedefe göre oversee.us ve exclusive30a.com "tarayıcı" sırasında programın
   tarayıcısıyla okunuyor (eskiden eklenti bağlıysa eklentiyle); programın tarayıcısı yoksa eklentiye düşer. RealJoy "eklenti"
   sırasında. Çekim sırasında bir işçiye doğrulama gösteren sıradan şirket, eklenti bağlıysa eklenti sırasına (yoksa tarayıcı sırasına)
   geçer ve tarayıcı doğrudan o sayfayla açılır (aynı sayfa ikinci kez doğrudan istenmez).
4. **Düşen proxy** listede "çalışmıyor" işaretlenir: sonraki çekimde işçi olmaz; "Dene" ile yeniden açılır.
5. **Deneme çekiminin yeri:** gerçek veritabanının programın aldığı kopyası (`data/deneme/<zaman>/`). Toplayıcılar orada normal iş
   akışıyla (kayıt dahil) çalışır; böylece kayıt adımı da denenmiş olur. Gerçek veritabanına yalnız deneme işinin kaydı düşer; bölge engelli
   liste ve tarayıcı alan adı işaretleri kopyada kalır. Son 3 denemenin kopyası durur; eskilerinin yalnız `sonuc.json`'u kalır.
6. **RealJoy 12 sn** göçle (v25): yalnız değer hâlâ 20 ise. 429'da işçi kuralı 24 sn'ye çıkarır; GÖREV-25'in Retry-After kuralı durur.
7. **CLAUDE.md'deki proxy cümlesi** 26 Kasım 2026 tarihli işçi kararıyla değiştirildi (CALISMA_MANTIGI ve M18 de). Proxy hâlâ bot
   korumasını, doğrulamayı ya da yasağı aşmak için kullanılmıyor; işçi doğrulama ya da engel yüzünden değiştirilmiyor.
8. **Book>Direct'in oynayan toplamı:** üç denemede de toplam yalnız 1–2 ilan (en çok %2) oynarsa son okunan ilanlar kaydedilir ve oynama
   çalışmanın notuna (`search_notes`) yazılır; daha büyük farkta çekim eskisi gibi düşer. Gerekçe: Seaside'ın toplamı her denemede 153↔154
   oynadı (bir ilan müsaitliğe göre girip çıkıyor); bütün Book>Direct çekiminin buna takılması orantısız.

## 3. İşçiler

Ayrıntı ve kurallar: `docs/M18-ABD-PROXY-BOLGE-ENGELI.md` "İşçiler". Kod: `studio/workers.py`, `studio/sources/agency_workers.py`,
`studio/proxy_list.py`.

- **Proxy listesi:** Ayarlar → ABD proxy'si → "Proxy listesi" tablosu (SIRA, PROXY `şema://sunucu`, KULLANICI, PAROLA kasada/yok, DURUM,
  ÜLKE, İŞÇİ) ve "Toplu ekleme (her satıra bir proxy)" kutusu + "Tür" (HTTP/SOCKS5) + "Listeye ekle ve dene". Kabul edilen biçimler:
  `sunucu:port:kullanıcı:parola`, `sunucu:port`, `kullanıcı:parola@sunucu:port`, `http://sunucu:port`. Kaydedince parolalar hemen
  Kimlik Bilgisi Yöneticisi'ne yazılır, kutu temizlenir; dosyada yalnız adres, port, kullanıcı adı ve tür kalır. Her satır tek tek denenir;
  çalışmayan "çalışmıyor" olur ve işçi olmaz. Eski tek proxy listenin ilk satırı oldu.
- **"Proxy'yi dene"** (Veri → Okuma denemeleri) her proxy için ayrı sonuç verir: çalışıyor mu, çıkış ülkesi. Satırdaki "Dene" tek proxy'yi dener.
- **Site başına sınır:** Ayarlar → ABD proxy'si → "Sitenin korunması" → "Aynı siteye aynı anda çalışan en çok işçi" (1–8, başlangıç 4).
- **Yavaşlama:** bir site herhangi bir işçiye 429, engel sayfası ya da doğrulama sayfası verirse o sitedeki bütün işçilerin aralığı iki
  katına çıkar; tekrarında o site tek işçiyle okunur. Olaylar iş mesajına, İşler paneline ve çalışmanın kaydına (`metadata.isciler.olaylar`) yazılır.
- **Bölge engelli siteler** yalnız ABD çıkışlı (ya da ülkesi bilinmeyen) proxy işçilerine gider; ABD proxy'si yoksa şirket atlanır ve kaydedilir.
- **İşler paneli:** çalışan kiralama işinin kartında "İşçiler (N çalışıyor)": çıkış (doğrudan / proxy N / tarayıcı / eklenti; adres yok),
  elindeki şirket, biten iş, hata, durum ve son olaylar.
- **Testler** (`tests/test_hedef01.py`, sahte HTTP, her işçi ayrı sahte istemci): dağıtım ve tekrarsızlık; proxy düşünce işin devri ve
  "çalışmıyor" işareti; site başına sınır (2 ve 4); 429'da bütün işçilerin yavaşlaması ve ikincisinde tek işçi (öbür site etkilenmez);
  bölge engelli sitenin yalnız ABD proxy'sine gitmesi ve ABD proxy'si yoksa atlanması; korumalı ve yalnız eklentili şirketlerin bölünmeden
  kendi sıralarında okunması, doğrulama gösteren şirketin sıraya geçmesi; canlı havuz (eklenen ve çıkarılan proxy); deneme sınırları;
  tahmin; satır biçimleri, parolaların yalnız kasada durması, API.

## 4. Deneme çekimi

### Tasarım

`studio/trial_run.py`; ekran Sol menü → Veri → Okuma denemeleri → "Deneme çekimi" bölümü → **"Deneme çekimini başlat"**.
- Gerçek veritabanının kopyası (SQLite backup API) `data/deneme/<YYYYMMDD-HHMMSS>/studio.sqlite3`; ham dosyalar yanında.
- Kiralama şirketleri: şirket başına 2 ilan (son çekimde şirket sayfasına bağlanmış olanlar önce), tek hafta, şirketin site haritası
  listesinden 3 sayfa, kendi envanterinden 2 ev; işçilerle. Book>Direct: tek hafta, 5 fiyat takvimi. Restoran siteleri: 3 restoran.
  Öbürleri (hava, iklim, deniz suyu, kasırga, plajlar, mahalleler, restoran dizini, günlük ihtiyaç, yol ağı, bilet ücreti) tam.
- Sonuç tablosu ekranda ve `sonuc.json`'da: toplayıcı başına sonuç, kayıt sayısı, süre, not; kiralama şirketi başına sonuç, ilan /
  eşlenen / fiyatlı, hangi işçiden okunduğu, not; sitenin korunma olayları.

### Gerçek sitelerdeki sonuç

Dört kez çalıştırıldı. İlk üçünde işçi yalnız **doğrudan** idi (kayıtlı tek proxy çalışmadı) ve kullanıcı yoktu (eklenti izni ve doğrulama
verilemedi). Dördüncüsünde Mucahit 12 proxy girmiş, eklentiyi yenilemiş ve beş siteye eklenti izni vermişti.

**4. deneme (13 işçi):** 28 kiralama şirketinin hepsi "tamamlandı"; her işçi iş aldı, hiçbir proxy düşmedi. Bölge engelli 360 Blue (listesi 583
ev) ve Vacasa (300 ev) ABD proxy'siyle okundu; denemedeki ikişer ilanları eşleme kuralına takıldı (360 Blue: Book>Direct ilanında oda sayısı
yok; Vacasa: aynı 15 m içinde başka ilan, çok daireli yapı) — kural gereği, hata değil. Doğrulama gösteren beş site (Alys Beach, Rosemary
Beach, 30A Escapes, Ocean Reef, Panhandle Getaways) eklenti sırasına geçip eklentiyle okundu. Avrupa çıkışlı proxy'lere özel bir ret
görülmedi (proxy'lerin aldığı 403/429'ların hepsi zaten bilinen doğrulama sayfaları). Aşağıdaki tablolar 3. denemedendir.

| Deneme | Zaman | Kod | Sonuç | Klasör |
|---|---|---|---|---|
| 1 | 19:37–20:53 | `43f8f82` | 13 toplayıcının 8'i okundu | `data/deneme/20261126-193747/` |
| 2 | 21:03–22:05 (iptal) | `519ee34` | eklenti sırası takıldı (aşağıda), iptal edildi | `data/deneme/20261126-210328/` |
| 3 | 22:07–23:41 | `1bd6f8b` | 13 toplayıcının 11'i okundu (yalnız doğrudan işçi) | `data/deneme/20261126-220734/` |
| **4** | **23:55–00:16** | `dfe4ab1` | **13 işçiyle** (doğrudan + Mucahit'in 12 proxy'si: 8 DE, 2 GB, 1 NL, 1 US), eklenti izinleri verilmiş: 13 toplayıcının 11'i; kiralamada **28 şirketin 28'i** tamamlandı, kiralama kısmı **15 dk** | `data/deneme/20261126-235534/` |

**Toplayıcılar (3. deneme)**

| Toplayıcı | Sonuç | Kayıt | Süre | Not |
|---|---|---|---|---|
| Kiralama şirketleri · Konaklama fiyatları | okundu | 429 | 82 dk | 28 şirketin 21'i okundu (aşağıda); sürenin çoğu eklenti izni beklemesi (5 × 15 dk) |
| Restoranlar · İşletme siteleri | okundu | 3 | 19 sn | deneme: 3 restoran |
| National Weather Service | okundu | 510 | 18 sn | |
| South Walton · Plaj erişimleri | okundu | 53 | 6 sn | 1. denemede düştü (site yeniden yapıldı); düzeltildi |
| South Walton · Restoranlar | hata | — | 2 sn | site yeniden yapıldı; açık iş (bölüm 7) |
| South Walton · Mahalleler | hata | — | 2 sn | site yeniden yapıldı; açık iş (bölüm 7) |
| NOAA NCEI · İklim normalleri | okundu | 168 | 2 sn | |
| NOAA NDBC · Deniz suyu sıcaklığı | okundu | 182 | 14 sn | |
| NOAA NHC · HURDAT2 kasırga izleri | okundu | 227 | 4 sn | |
| OpenStreetMap · Günlük ihtiyaç noktaları | okundu | 47 | 75 sn | Overpass "meşgul" dedi; 30 sn bekleyip yeniden sordu (1. denemede düşmüştü) |
| OpenStreetMap · Yol ağı ve sürüş süreleri | okundu | 23.090 | 100 sn | |
| BTS · Havalimanı ortalama bilet ücreti | okundu | 10 | 55 sn | |
| South Walton · Konaklama (Book>Direct) | okundu | 2.231 | 197 sn | deneme: tek hafta, 5 takvim; 1. denemede toplamı oynayan arama yüzünden düşmüştü |

**Kiralama şirketleri (3. deneme; şirket başına 2 ilan, tek hafta)**

| Şirket | Sonuç | İlan / eşlenen / fiyatlı | İşçi | Not |
|---|---|---|---|---|
| 30A Beach Girls | okundu | 2 / 0 / 0 (kendi envanteri 3 ev) | doğrudan | eski bağlantılar ölü; evler kendi listesinden, haftalık kira |
| 30A Vacay | okundu | 2 / 0 / 0 | doğrudan | iki Book>Direct bağlantısı 404 |
| 30A Beach Stays | okundu | 2 / 2 / 2 | doğrudan | |
| 30A Cottages | okundu | 2 / 2 / 2 | doğrudan | |
| 30A Escapes | atlandı | 2 / 0 / 0 | doğrudan → eklenti | "Quick security check" doğrulaması; eklentinin site izni yok |
| 360 Blue | atlandı | — | — | bölge engeli: çalışan ABD proxy'si yok |
| Alys Beach Vacation Rentals | atlandı | 2 / 0 / 0 | doğrudan → eklenti | Cloudflare doğrulaması; eklentinin site izni yok |
| Dune Allen Realty | okundu | 2 / 2 / 1 | doğrudan | 1 ilan o hafta dolu |
| Benchmark Management | okundu | 2 / 2 / 2 | doğrudan | |
| Coastal Blue Vacations | okundu | 2 / 2 / 0 | doğrudan | o hafta dolu |
| Newman-Dailey | okundu | 2 / 2 / 1 | doğrudan | |
| Dune Vacation Rentals | okundu | 2 / 2 / 1 | doğrudan | |
| Exclusive 30A | okundu | 2 / 2 / 1 | programın tarayıcısı | |
| FunVacay | okundu | 2 / 2 / 2 | doğrudan | |
| Grayt 30A Vacations | okundu | 2 / 2 / 1 | doğrudan | |
| Grayton Coast Rentals | okundu | 2 / 2 / 2 | doğrudan | |
| Homeowner's Collection | okundu | 2 / 2 / 1 | doğrudan | |
| My Vacation Haven | okundu | 2 / 2 / 1 | doğrudan | |
| Ocean Reef Resorts | atlandı | 2 / 0 / 0 | doğrudan → eklenti | "Quick security check"; eklentinin site izni yok |
| Oversee | okundu | 2 / 2 / 1 | programın tarayıcısı | 2. denemede tarayıcı sırası hatasıyla düşmüştü |
| Panhandle Getaways | atlandı | 2 / 0 / 0 | doğrudan → eklenti | "Quick security check"; eklentinin site izni yok |
| Paradise Properties | okundu | 2 / 2 / 0 | doğrudan | o hafta dolu |
| RealJoy Vacations | okundu | 2 / 1 / 1 | eklenti | tam liste (26 parça) + 1 ev bağlandı ve fiyatlandı |
| Rosemary Beach® | atlandı | 2 / 0 / 0 | doğrudan → eklenti | Cloudflare doğrulaması; eklentinin site izni yok |
| Sanders Beach Rentals | okundu | 2 / 2 / 0 | doğrudan | o hafta dolu |
| Southern Vacation Rentals | okundu | 2 / 2 / 2 | doğrudan | |
| Vacasa | atlandı | — | — | bölge engeli: çalışan ABD proxy'si yok |
| Your Friend at the Beach | okundu | 2 / 2 / 0 | doğrudan | fiyat servisi "not authorized" (kalıcı; Ekim'de de) |

"Atlandı" yazan eklenti sırasındaki şirketlerin mesajı ekranda "Kullanıcı doğrulaması süresinde tamamlanmadı" diyor; asıl sebep eklentinin
o site için izni olmaması (program bunu iş mesajında "Eklentinin … için izni yok" diye söyledi). Sitenin korunma olayları kaydı: her
doğrulama gösteren site için "bütün işçiler yavaşladı" olayı yazıldı.

**2. denemedeki takılma:** eklenti sırasında bir şirket bitince eklenti oturumu (ve tarayıcı sırasında programın tarayıcısı) kapatılmıyordu;
eklenti RealJoy'u "çalışıyor" tutup sıradaki şirketin oturumunu sonsuza kadar bekletti, tarayıcı sırasında oversee.us Playwright hatasıyla
düştü. Düzeltme `1bd6f8b` (sıra, bitmiş şirketin tarayıcısını kendi iş parçacığında kapatır); 3. denemede ikisi de doğru çalıştı.

### Bulunan ve düzeltilen hatalar

| Hata | Düzeltme | Test |
|---|---|---|
| Track altyapılı 30A Escapes, Ocean Reef Resorts, Panhandle Getaways her isteğe HTTP 429 "Quick security check" (Turnstile, `challenge.icoastalnet.com`) verdi; program bunu doğrulama değil ret sayıp şirketi durdurdu | Doğrulama işaretlerine eklendi (program ve eklenti 0.21.0); şirket eklenti sırasına geçer, kullanıcı doğrular | `test_the_track_sites_own_security_check_…` (gerçek cevaptan fixture) |
| Visit South Walton sitesi Gatsby ile yeniden yapılmış: plaj sayfasında `initMarkers` verisi yok | Erişim noktaları sitenin kendi statik veri dosyasından (`allBeachAccess`, `studio/sources/gatsby.py`); eski kimliklerle aynı, 53 kıyı kaydı | `test_the_rebuilt_visit_south_walton_site_…` |
| Book>Direct Seaside araması: toplam her denemede 153↔154 oynadı, bütün çekim düştü | Küçük oynamada son okunan ilanlar kaydedilir, not düşülür (karar 8) | `test_a_total_that_only_wobbles_is_kept_with_a_note` |
| Overpass (günlük ihtiyaç noktaları) tek 502'de düştü | Meşgulken 30/60/120/240 sn bekleyip yeniden sorar (yol ağıyla aynı kural) | `test_a_busy_overpass_server_is_asked_again_after_a_wait` |
| Deneme çekiminde 30A Beach Girls'ün AvantStay listesi 144 evin hepsini açtı (deneme sınırı uygulanmıyordu) | AvantStay listesi `max_pages` sınırına uyar | `test_the_trial_run_reads_only_a_few_homes_of_the_avantstay_list` |
| winndixie.com proxy kimlik doğrulama penceresi (GÖREV-25 notu): yönlendirmede aynı istek kimliğiyle gelen ikinci proxy sorusu "yanlış parola" sayılıp iptal ediliyordu (`ERR_INVALID_AUTH_CREDENTIALS`) | İsteğin yolundaki her adrese bir kez cevap (en çok 8); aynı adres ikinci kez sorulursa yine iptal | `test_proxy.py` (auth_answer) |
| CI'daki "test_extension kapanışında takılma" (GÖREV-18'den beri ara sıra) | Tanı adımı son test satırlarını ve iş parçacıklarının program satırlarını gösterecek biçimde düzeltildi; ikinci takılmada kök neden görüldü: test eklentilerinin iç döngüsü test bitince durmuyordu; düzeltildi | CI 45895201380 |

### Kalıcı engeller ve kullanıcı işi

- **Your Friend at the Beach:** sitenin fiyat servisi "You are not authorized to use this service" diyor; Ekim çekiminde de 252/252 böyleydi.
  Sitenin servisi dışarıya kapalı (kalıcı).
- **Eklenti izni ve doğrulama isteyen siteler** (yalnız kullanıcı verir/geçer): eklentinin site izni yalnız order.online, realjoy.com,
  thefreshmarket.com ve winndixie.com için var. Çekim sırasında eklenti sırasına geçen alysbeach.com, rosemarybeach.com (Cloudflare
  "Just a moment") ve Track'li üç şirket ("Quick security check") için Chrome'da eklenti simgesinden "İzin ver" gerekir; verilmezse 15 dk
  sonra atlanırlar. oversee.us programın tarayıcısında doğrulama isteyebilir. Denemelerde kullanıcı yoktu.
- **Bölge engelli** 360 Blue ve Vacasa: proxy çalışmadığı için atlandı ("ABD proxy'si tanımlı değil"). Çalışan ABD proxy'si gerekir.

## 5. Tahminler

"Güncelleme zamanı gelenler" tablosunun "Kiralama şirketleri · Konaklama fiyatları" satırı artık işçi sayısıyla hesaplanıyor ve altında
10 ve 20 işçiyle tahmini de yazıyor. Kaynak: son kiralama çekiminin (9–10 Ekim) şirket başına istek sayıları ve sonra eklenen 4 şirketin
(360 Blue, Vacasa, 30A Beach Girls, RealJoy) tahmini istekleri; toplam ~24.700 istek; site başına 4 işçi; işçi başına 8 sn + 1 sn cevap.

| İşçi | Tahmini süre (kiralama) |
|---|---|
| 1 (yalnız doğrudan; bugünkü durum, proxy çalışmıyor; bölge engelli şirketler atlanır) | ~47 sa |
| 2 (doğrudan + 1 ABD proxy'si) | ~27 sa |
| 3 | ~18 sa |
| 5 | ~11 sa |
| 10 | ~6 sa 10 dk |
| 20 | ~6 sa 10 dk |

10 işçiden sonra süreyi oversee.us belirliyor: korumalı site, tarayıcı sırasında tek başına (~2.300 istek × 9 sn ≈ 6 sa). Bu gece zamanı
gelen öbür toplayıcılar: Book>Direct (~1 sa) ve Yol ağı (~1 dk); restoran dizini, mahalleler ve plajların zamanı gelmedi.

## 6. Kullanıcının gece çekimi tarifi

**Önce bilin:** kiralama çekimi artık işçilerle yapılıyor. İşçi sayısı = doğrudan bağlantı + çalışan proxy sayısı. Kayıtlı tek proxy'niz
26 Kasım'da çalışmadı; proxy girmeden başlatırsanız kiralama çekimi tek işçiyle **yaklaşık 47 saat** sürer ve 360 Blue ile Vacasa atlanır.
10 ya da daha çok çalışan proxy'yle **yaklaşık 6 saat**. Bilgisayarın uyumaması ve internetin açık kalması gerekir. **Chrome'u ve programı
çekim bitene kadar kapatmayın.**

**Başlamadan önce**

1. **Chrome'u açın.** Adres çubuğuna `chrome://extensions` yazın. "30A Studio Yardımcısı" kartında sürüm **0.21.0** olmalı. Değilse
   karttaki yenile (dairesel ok) düğmesine bir kez basın.
2. **Programı açın** (masaüstündeki "30A Studio").
3. **Eklenti bağlı mı:** Sol menü → **Ayarlar** → **Tarayıcı eklentisi**. Yeşil **"Bağlı"** yazmalı. "Bağlı değil" yazıyorsa Chrome'un açık
   olduğundan emin olup birkaç saniye bekleyin.
4. **Proxy listesini girin:** Sol menü → **Ayarlar** → **ABD proxy'si** bölümü.
   - **"Toplu ekleme (her satıra bir proxy)"** kutusuna proxy'lerinizi Housing Atlas'taki gibi her satıra bir tane yapıştırın:
     `sunucu:port:kullanıcı:parola`.
   - **"Tür"** kutusundan **HTTP** ya da **SOCKS5** seçin.
   - **"Listeye ekle ve dene"** düğmesine basın. Program her satırı tek tek dener. Tabloda her proxy için **DURUM** (çalışıyor /
     çalışmıyor) ve **ÜLKE** görünür. Parolalar Windows Kimlik Bilgisi Yöneticisi'ne yazılır, kutu kendiliğinden temizlenir.
   - Çalışmayan satırları **"Listeden çıkar"** ile kaldırabilirsiniz (kalsalar da işçi olmazlar).
   - Bölümün üstünde **"Şu an N işçi"** yazar. Bölge engelli şirketler (360 Blue, Vacasa) için ÜLKE sütununda en az bir **US** olmalı.
   - **"Sitenin korunması"** kutusundaki **4** sayısını değiştirmeyin.
5. **Tahmini süreye bakın:** Sol menü → **Veri** → **Kaynaklar** → **"Güncelleme zamanı gelenler"** tablosu. "Kiralama şirketleri ·
   Konaklama fiyatları" satırının **TAHMİNİ SÜRE** sütunu işçi sayısına göre süreyi gösterir; altında "N işçiyle … ; 10 işçiyle …, 20
   işçiyle …" yazar. Süre çok uzunsa (ör. 20 saatten fazla) daha çok proxy ekleyin.
6. İsterseniz önce küçük bir deneme: Sol menü → **Veri** → **Okuma denemeleri** → **"Deneme çekimini başlat"** (yaklaşık 1–2 saat,
   gerçek veriye karışmaz). Gerekmez; ben iki kez çalıştırdım.

**Başlatma**

7. Sol menü → **Veri** → **Kaynaklar** → **"Güncelleme zamanı gelenler"** → **"Zamanı gelenleri başlat"**. Program önce kendi yedeğini
   alır, sonra sırayla çalıştırır: **Konaklama (Book>Direct)** (~1 saat), **Kiralama şirketleri** (işçi sayısına göre), **Yol ağı** (~1 dk).

**Çekim sırasında**

8. İlerlemeyi sağ üstteki **"İşler"** düğmesinden izleyin. Kiralama işinin kartında **"İşçiler (N çalışıyor)"** tablosu her işçinin
   çıkışını (doğrudan / proxy N), elindeki şirketi ve hata sayısını gösterir. Bir proxy düşerse "düştü" yazar; işi başka işçiye geçer,
   sizin bir şey yapmanız gerekmez. Çekim sürerken listeye proxy eklerseniz birkaç dakika içinde çekime katılır.
9. **Doğrulama çıkarsa:**
   - **RealJoy, Alys Beach, Rosemary Beach, 30A Escapes, Ocean Reef Resorts, Panhandle Getaways**: eklenti Chrome'unuzda kendi penceresini
     öne getirir. Sayfadaki "insan olduğunuzu doğrulayın" kutusunu **işaretleyin**. Her site en çok 15 dakika bekler; geçilmezse atlanır.
   - **oversee.us** ve **exclusive30a.com**: programın kendi tarayıcı penceresi öne gelir; kutuyu orada işaretleyin. Bekleyen siteler
     çekimin sonuna bırakılır, en sonda 15 dakika beklenir.
   - **Eklentiye site izni verin.** Çekim bu sitelere gelince (ilk birkaç dakikada) Chrome'da sağ üstteki **"30A Studio Yardımcısı"**
     simgesine tıklayın. Açılan küçük pencerede **"İzin bekleyen siteler"** altında görünen her site için **"İzin ver"**e basın
     (30aescapes.com, oceanreefresorts.com, panhandlegetaways.com, alysbeach.com, rosemarybeach.com). Eklenti izin verilmeyen siteye
     gitmez; izin 15 dakika içinde verilmezse o şirket atlanır. İzin bir kez verilir, sonraki çekimlerde sorulmaz.
   - İşler panelindeki kartta "Kullanıcı doğrulaması bekleniyor: <site>" yazar. Beklemek istemezseniz **"Bu sayfayı atla"** düğmesi var.
10. Winn-Dixie'nin proxy kullanıcı adı/şifre penceresi bu çekimde çıkmaz (o site bu gece yok). Çıkarsa kapatın.

**Atlanan bir şirketi sonra yeniden okumak**

11. Bir şirket doğrulama yüzünden atlandıysa, ertesi gün Chrome açıkken: Sol menü → **Veri** → **Toplama** → **Konaklama** sekmesi →
    **"Konaklama fiyatları"** bölümü → **"↓ Kiralama şirketi fiyatlarını topla"**. Bu, kiralama çekimini baştan çalıştırır (işçi sayısına
    göre süre). Doğrulama penceresi çıkınca kutuyu işaretleyin.

**Bitince**

12. Sol menü → **Veri** → **Toplama** → **Konaklama** sekmesi → **"Konaklama fiyatları"** bölümü → **"Şirket bazında sonuç"** tablosu.
    DURUM sütununda çoğu şirkette "tamamlandı" yazmalı. "doğrulama gerekti; atlandı" ya da "kullanıcı doğrulaması süresinde
    tamamlanmadı" yazan şirketleri not edin.
13. Bana (ya da yöneticiye) **"çekim bitti"** yazın; sonuçların denetimi ayrı hedefte yapılacak.

## 7. Açık kalanlar

- **winndixie.com düzeltmesi** gerçek proxy'yle programın tarayıcısında denenmedi (bu gece o site yok; günlük ihtiyaç toplayıcısı zincir
  sitelerini canlı okumuyor).
- **ABD çıkışlı proxy tek:** bölge engelli 360 Blue ve Vacasa yalnız ona gidiyor (tahminde ~4,8 sa; toplamı aşmıyor). Düşerse bu iki şirket
  o gece atlanır.
- **Visit South Walton'ın restoran dizini ve mahalleleri** (site yeniden yapıldı; Mucahit 27 Kasım gecesi sitenin kendi API'sinin
  kullanılmasını onayladı, okuyucular ayrı bir dalda yazılıyor): restoran listesinde alt kategori ("Restaurants") bilgisi
  boş geliyor (aynı listede catering, bar vb.; 235 işletme), mahalle kayıtlarında koordinat, etiket ve değişiklik zamanı yok (tablo
  koordinatı zorunlu tutuyor). İkisi kaynağın ne söylediğine dair karar istiyor; okuyucu yazılmadı. Bu iki toplayıcı çalıştırılırsa
  "kaynak yapısı değişti" hatası verir; eski kayıtlar korunur. Bu gece zamanları gelmediği için gece çekimini etkilemez.
- **Doğrulama gerektiren siteler** kullanıcı doğrularsa okunur (tarif).

## 8. Yedekler

- Gerçek verinin tam yedeği, program kapalıyken: `work/yedek/20261126-1905/` (45.688 dosya, 1.976.684.410 bayt; kaynakla aynı).
- Programın göç yedeği (şema 24 → 25): `data/backups/studio-v24-737ad661f5534f1980f964bb121a58e6.sqlite3`.
- Göç önce kopyada denendi: satır sayıları aynı, `foreign_key_check` boş, RealJoy `gap_s` 12.
- Deneme çekimlerinin kopyaları: `data/deneme/20261126-193747/`, `20261126-210328/`, `20261126-220734/` (her birinde `sonuc.json`).

## 9. Testler ve CI

- **Yerel tam takım** (`60ceb89`): `.venv\Scripts\python.exe -m pytest -q` → **1267 geçti, 3 atlandı**; `node --test tests/frontend.test.mjs`
  → **141/141**. Bu hedefte eklenen testler: `tests/test_hedef01.py` (32), `test_proxy.py` (winndixie), `test_lodging.py` (oynayan toplam),
  `test_daily_needs.py` (Overpass meşgul), `test_gorev22.py` (AvantStay deneme sınırı), arayüz testleri (proxy listesi, İşler panelindeki
  işçiler, tahmin satırı, deneme çekimi).
- **Bağımsız inceleme:** işçi zamanlayıcısı ayrı bir inceleme ajanıyla okundu; 6 bulgu (ikisi sahte HTTP'yle yeniden üretildi: takılan bir
  işin fiyatları iki kez yazılıyordu; iş çevresindeki bir hata çekimi bitmez hâle getiriyordu) `60ceb89`'da düzeltildi, ikisine gerileme testi
  yazıldı. Bulgular: takılan işin iki kez kuyruğa girmesi (takılma sınırı en uzun Retry-After beklemesinden uzun yapıldı), iş dışındaki
  hatada işin kuyrukta kalması, durdurulan şirketin öbür işçilerinin okumayı sürdürmesi, art arda ret sayacının işçiler arasında paylaşılması,
  bölge engelli şirketin havuz yenilenmeden atlanması, geç eklenen işçinin beklenmemesi.
- **GitHub CI:** 45856622744 (`190944c`) bilinen test_extension kapanış takılmasına düştü (tanı adımı düzeltildi); 45859402665 (`43f8f82`)
  başarılı; 45882082512 (`60ceb89`) başarılı; 45892968427 (`29484d4`) yine test_extension kapanışında takıldı — bu kez yeni tanı satırları takılan yeri gösterdi:
  sahte eklentinin iç döngüsü test bitince durmuyordu (`/sonraki`'yi sorup duruyordu); üç test dosyasında düzeltildi (`dfe4ab1`), CI
  45895201380 başarılı. Son commit: bölüm 1'deki etiket commit'i.

## 10. Uyulan kurallar

- Uzun çekim ("Zamanı gelenleri başlat" ya da bir toplayıcının tam çalışması) başlatılmadı; yalnız deneme çekimi (küçük, kopyada).
- Gerçek Claude çalıştırılmadı; alt ajan kullanılmadı; zamanlanmış görev oluşturulmadı; Windows ayarı değiştirilmedi.
- `data/` içinde elle dosya değiştirilmedi, silinmedi, taşınmadı; veri yalnız programın normal kullanımıyla (göç, deneme çekimi) değişti.
- Proxy adresi, kullanıcı adı ve parola hiçbir dosyaya, günlüğe ve rapora yazılmadı; proxy'ler "proxy N" diye anılır.
- Housing Atlas yalnız okundu (işçi düzeni ve proxy biçimi); parola ya da proxy bilgisi okunmadı. Talimat dosyalarına dokunulmadı.
- Canlı incelemeler: visitsouthwalton.com'a 8 istek (aralar ≥8 sn): sayfa verisi, plaj bileşeni, iki statik sorgu, mahalle ve restoran
  sayfa verileri.
