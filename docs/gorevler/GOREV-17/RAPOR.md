# GÖREV-17 — Rapor

Arayüz düzeltmeleri: İşler panelinde temizleme, Ayarlar düzeni, açılan pencerelerin düzenlenmesi ve küçük düzeltmeler.
Tarih: 11 Kasım 2026. Dal: `gorev-17-arayuz`. Uygulama 0.19.0, şema 19, eklenti 0.19.0. Yeni özellik yok.

## Kısa özet

- `v0.18.0` main'e alındı ve etiketlendi.
- İşler panelinde biten işler artık panelden kaldırılabiliyor (toplu ve tek tek). Kaldırmak silmek değil; hepsi geri getirilebiliyor.
- Ayarlar sol menünün altında belirgin bir öğe oldu; ekranın üstündeki düğmeler doğrudan ilgili bölüme götürüyor.
- "Sürekli web sayfası açıyor" sorununun nedeni bulundu: eklenti her site için yeni pencere açıp kapatıyordu. Artık bir iş boyunca tek
  pencere kullanıyor, pencere arka planda açılıyor ve iş bitince kapanıyor.
- Üç küçük düzeltme yapıldı (proxy günlük metni, eşleşme kodunun tazelenmesi, taşınan klasör).
- Gerçek veritabanında yalnız şema geçişi yapıldı; hiçbir iş gizlenmedi, hiçbir satır değişmedi.
- Gerçek Claude çalıştırılmadı, gerçek sitelere istek yapılmadı, zamanlanmış görev oluşturulmadı.

## Konumlar, CI ve testler

| | Konum | CI |
|---|---|---|
| main | `988ca8d` (fast-forward `6cfab84..988ca8d`, itildi) | Aynı commit'in görev dalı çalışması 38144739045 başarılı. main'e itişin kendi çalışması (43011750701) rapor yazılırken GitHub'da hâlâ "sürüyor" görünüyordu; sonucu görülemedi. |
| Etiket `v0.18.0` (açıklamalı, itildi) | `988ca8d` — "v0.18.0 — eklentinin düzeltilmesi ve bölge engeli için ABD proxy'si" | 43011754490 başarılı |
| Dal `gorev-17-arayuz` | son commit kullanıcıya yazılan son mesajda | push'tan sonra GitHub'da görülür |

Testler (yerelde, tam takım art arda 3 kez):

| Tur | Python | Ön yüz |
|---|---|---|
| 1 | 1095 geçti, 2 atlandı | 115 geçti |
| 2 | 1095 geçti, 2 atlandı | 115 geçti |
| 3 | 1095 geçti, 2 atlandı | 115 geçti |

Atlanan 2 test eklentinin uçtan uca denemesidir (`STUDIO_EKLENTI_E2E=1` ister; CI'da çalışmaz). Ayrıca çalıştırıldı: 2/2 geçti
(Playwright'in Chromium'u, geçici profil, yalnız yerel sayfalar).

Önceki iki 3'lü turda, her seferinde üçüncü turda birer test bir kez düştü; ikisi de bu görevin koduyla ilgisiz, zamanlamaya bağlı test yarışlarıydı:

- `test_lodging.py::test_cancel_job_through_api_publishes_nothing`: test, programın o anda yeniden adlandırdığı geçici dosyayı
  (`manifest.tmp`) okumaya çalışıyordu (o sırada 1,5 GB'lık tam yedek alınıyordu, disk yavaştı). Testin yardımcı işlevi böyle bir
  dosyayı atlayacak şekilde düzeltildi.
- `test_title_review.py::test_an_idea_that_does_not_fill_a_video…`: Claude çalışması "onay bekliyor" olur olmaz test işi okuyordu;
  işin son mesajı bir an sonra yazılıyor. Test, işin bitmesini bekleyecek şekilde düzeltildi (sahte Claude; gerçek Claude çalışmadı).

İki düzeltmeden sonra 3 tur yeniden çalıştırıldı; yukarıdaki tablo o turlardır.

Bu görevde eklenen testler: `tests/test_gorev17.py` (17 test), `tests/frontend.test.mjs` içinde 20 test (her Ayarlar bölümü için bir
test dahil), `tests/test_extension_e2e.py` içinde 1 uçtan uca test.

## Adım 1 — v0.18.0'ı main'e alma

- Program kapalıydı (kilit yok, süreç yok).
- Çalışma ağacında kullanıcının Ayarlar'dan yaptığı talimat, ton ya da uyarı ifadesi değişikliği **yoktu**; bu yüzden "talimat" commit'i
  atılmadı. Tek izlenmeyen dosya `30A Studio.lnk` idi; commit edilmedi, `.gitignore`'a `*.lnk` eklendi.
- `988ca8d`'nin CI'ı başarılıydı; main fast-forward edildi ve itildi; `v0.18.0` açıklamalı etiketi istenen mesajla kondu ve itildi.
- Güncel main'den `gorev-17-arayuz` dalı açıldı.

## Adım 2 — İşler panelinde biten işleri kaldırma

- Panelin başında **"Bitenleri kaldır (N)"**: tamamlanan, hata veren, iptal edilen ve yarıda kalan işleri kaldırır. Çalışan ve sırada
  bekleyen işlere dokunmaz. Claude çalışması sizin kararınızı bekleyen işler ("Onay bekliyor" etiketiyle görünür) toplu kaldırmaya
  girmez; istenirse kendi "Kaldır" düğmesiyle tek tek kaldırılabilir.
- Her bitmiş işin kartında küçük **"Kaldır"** düğmesi.
- Kaldırma yalnız gizlemedir. İşaret veritabanında küçük bir tabloda tutulur (`job_hidden`, şema 19). İşin kaydı, günlüğü ve sonucu
  değişmez; program içindeki öbür ekranlar o işi görmeye devam eder (ör. son deneme tablosu).
- Panelin altında **"Gizlenen işleri göster (N)"**; liste açılınca her satırda **"Geri getir"**.
- Housing Atlas'ın İşler panelinde kalıcı kaldırma yok; yalnız geçici bir "Bitenleri gizle / göster" süzgeci var. Oradan düğmenin
  panelin başında durması ve "kaldırılan iş silinmez" anlayışı alındı; kalıcılık ve geri getirme görev metnine göre kuruldu.
- Uzun günlükler kartta zaten kapalı geliyordu; dokunulmadı. Ek olarak, açık bırakılan bir günlük ve panelin kaydırma yeri artık iş
  olayı geldiğinde kapanmıyor (önceden her yenilemede kapanıyordu).

## Adım 3 — Ayarlar düzeni

- **Sol menü:** en altta, ince çizgiyle ayrılmış, simgeli "Ayarlar" öğesi. Ekran açıkken vurgulu ve solunda turuncu işaret var. Claude
  kullanımı kutusu yerinde. Eski küçük bağlantı kaldırıldı.
- **"Yardım" konmadı:** programda bir yardım ekranı yok; içerik uydurulmadı.
- **Bölüm düğmeleri:** Kayıt klasörü, Claude, Başlık eki, Claude kullanımı, Talimatlar, Tonlar, Uyarı ifadeleri, Tarayıcı eklentisi,
  ABD proxy'si, Hakkında. Düğme sayfayı o bölüme götürür; adres bölümü gösterir (`#settings/tonlar`; `#ayarlar/tonlar` da açar).
  Düğme satırı sayfa kayarken üstte kalır.
- **Kartlar:** her bölüm kendi başlığı ve simgesi olan bir kart. Renkler ve yazı tipi mevcut CSS değişkenlerinden.
- **Bağlantılar:** "Tonları yönet", "Ayarlar → Claude", "Ayarlar → Tarayıcı eklentisi" geçen uyarılar (iş panelindeki mesajlar dahil),
  eklenti bölümündeki ABD proxy'si sözü, proxy bölümündeki eklenti sözü ve deneme tablosundaki "ABD proxy'si tanımlı değil" notu
  doğrudan ilgili bölüme gider.
- **Bozulmadı:** her bölümün içeriğini ve düğmelerini eskisi gibi kendi kodu çiziyor; hiçbir ayarın değeri değişmedi. Önceki bir kusur
  da giderildi: adres Ayarlar içinde değişince ekran yeniden çizilmiyor, yani yazılıp kaydedilmemiş değer kaybolmuyor.

Geçici klasörde gerçek tarayıcıyla denetim (10 bölümün 10'u):

| Bölüm | Düğmeyle gidildi | Ana düğme / ana satır göründü |
|---|---|---|
| Kayıt klasörü | evet | evet (klasör yolu) |
| Claude | evet | evet ("Claude ayarlarını kaydet") |
| Başlık eki | evet | evet ("Başlık ekini kaydet") |
| Claude kullanımı | evet | evet (kullanım açıklaması; bu bölümde düğme yok) |
| Talimatlar | evet | evet ("Kaydet") |
| Tonlar | evet | evet ("Tonu ekle") |
| Uyarı ifadeleri | evet | evet ("Kaydet") |
| Tarayıcı eklentisi | evet | evet ("Deneme") |
| ABD proxy'si | evet | evet ("Kaydet") |
| Hakkında | evet | evet (sürüm satırı) |

Ayrıca: proxy adresi kutusuna yazılan değer başka bölüme gidip dönünce duruyordu; başka ekrandan `#settings/eklenti` adresine gidince
sayfa o bölümde açıldı.

## Adım 4 — Açılan pencereler

### İnceleme

Kod okunarak ve yerel denemeyle çıkarıldı (gerçek siteye gidilmedi).

**Önce:**

| Kaynak | Ne zaman açılıyordu | Kaç kez | Kapanıyor muydu | Öne geliyor muydu |
|---|---|---|---|---|
| Eklentinin penceresi (sizin Chrome'unuz) | Bir işin her sitesi için yeniden | Site sayısı kadar (7 sitelik denemede eklentiye giden her site için bir pencere; restoran ve kiralama toplayıcılarında eklentiyle okunan her alan adı için bir pencere) | Evet, her siteden sonra | Odak almadan açılıyordu ama ekranda beliriyordu; doğrulamada öne geliyordu |
| Programın kendi tarayıcısı (doğrulama, CDP) | Eklenti yokken ya da iş devredilince, engel gösteren site okunurken | Tarayıcı bir kez; restoranlarda tek sekme, kiralama şirketlerinde şirket başına bir sekme | Sekmeler kapanıyordu, tarayıcı penceresi iş bittikten sonra **açık kalıyordu** | Açılırken ekrana geliyordu |
| Programın proxy tarayıcısı | Bölge engelli ve JavaScript'le çizilen sayfa proxy'yle okunurken | Tarayıcı bir kez, tek sekme | Sekme kapanıyordu, pencere iş bittikten sonra **açık kalıyordu** | Açılırken ekrana geliyordu |
| Programın uygulama penceresi (Edge) | Program açılırken | Bir kez | Program kapanınca | Evet (programın kendi penceresi) |
| Başka sekme ya da Edge penceresi | — | Toplayıcılar ve deneme işi başka pencere açmıyor | — | — |

Yani "sürekli web sayfası açıyor" gözleminin kaynağı eklentiydi: eklentiyle bağlantılıydı, ama pencere iş başına değil site başına
açılıp kapanıyordu.

**Sonra:**

| Kaynak | Ne zaman açılıyor | Kaç kez | Kapanıyor mu | Öne geliyor mu |
|---|---|---|---|---|
| Eklentinin penceresi | İşin eklentiye giden ilk sayfasında | **İş başına 1 pencere, 1 sekme**; sonraki siteler aynı sekmede açılır | İş bitince, iptal edilince, programın tarayıcısına devredilince ya da program kapanınca | Yalnız sizin geçmeniz gereken doğrulamada |
| Programın kendi tarayıcısı | Aynı durumlarda | Tarayıcı bir kez; restoranlarda tek sekme; kiralama şirketlerinde şirket başına bir sekme (aşağıdaki nota bakın) | İşin kendisi başlattıysa iş bitince ya da iptal edilince kapanır | Odak almadan açılır; yalnız doğrulamada öne gelir |
| Programın proxy tarayıcısı | Aynı durumlarda | Tarayıcı bir kez, tek sekme | İşin kendisi başlattıysa iş bitince ya da iptal edilince kapanır | Odak almadan açılır; yalnız doğrulamada öne gelir |
| Programın uygulama penceresi | Değişmedi | | | |

İşler panelinde, pencere açıkken süren işin kartında yazar: "Açık pencere — Eklentinin penceresi: realjoy.com · sayfa okunuyor",
"Programın tarayıcısı: … okunuyor", "Programın proxy tarayıcısı: … okunuyor". İki site arasında "sıradaki sayfa bekleniyor" yazar.

Hız kuralı, doğrulamanın kullanıcı tarafından geçilmesi ve proxy'nin yalnız bölge engelli alan adlarında kullanılması değişmedi.
Görünmez (headless) kip hiçbir yerde kullanılmıyor.

### Küçültülmüş pencere yerine odak almayan normal pencere seçildi

Görev metni iki seçenek veriyordu. Odak almayan normal pencere seçildi:

- Gerçek Chrome'la (geçici profil, yalnız boş sayfa) denendi: "etkinleştirmeden" başlatılan tarayıcı sizin o an çalıştığınız
  pencerenin odağını değiştirmedi ve sayfa normal çizildi.
- Küçültülmüş pencerede sayfanın çizmeye devam edip etmediği güvenilir biçimde ölçülemedi (ölçüm tarayıcıya bağlı hata ayıklama
  bağlantısından yapıldı ve "görünür" dedi; bu bağlantının kendisi sonucu etkiliyor olabilir). Chrome gizli sayfada çizimi ve görünüme
  girince yüklenen bölümleri durdurduğu, restoran toplayıcısı da menüleri sayfayı kaydırarak yüklediği için, sayfanın yarım okunması
  riski alınmadı.
- Eklentinin komut satırında ve programın tarayıcısının başlatma komutunda hiçbir bayrak eklenmedi; yalnız Windows'a "pencereyi
  etkinleştirmeden göster" denir.

### Eklenti

- `chrome.windows.create` yalnız bir yerde ve `focused: false` ile çağrılıyor; iş içinde pencere kapatılmıyor.
- Program, eklentinin her sorusuna hangi işlerin penceresinin açık kalması gerektiğini söylüyor; iş listeden çıkınca eklenti pencereyi
  kapatıyor.
- Eklenti sürümü 0.19.0. Gerçek program açıldığında Chrome'daki eklenti 0.18.0 olarak bağlandı ve Ayarlar "eski sürüm" notunu gösterdi.
- Uçtan uca deneme (Playwright'in Chromium'u, yerel sayfalar): bir işin iki oturumu aynı pencerede okundu, pencere iki site arasında
  açık kaldı, tek sekmeydi, küçültülmemişti ve iş iptal edilince kapandı. Playwright'in Chromium'unda `chrome.windows` sınırı
  çıkmadı; test tarafında uyarlama gerekmedi.

## Adım 5 — Küçük düzeltmeler

1. **İş günlüğünde proxy:** deneme işinin günlüğü, deneme tablosu ve İşler paneli aynı sözleri kullanıyor: "bölge engeli · proxy'yle
   okundu", "bölge engeli · proxy'yle de okunamadı (neden)", "bölge engeli · ABD proxy'si tanımlı değil (Ayarlar)". İşin son satırı
   kaç sitenin proxy'yle okunduğunu da söylüyor. Gerçek verinin kopyasında, sizin 11 Kasım denemenizin tablosu yeni metinle göründü
   (HCA, CVS, Publix: "bölge engeli · proxy'yle okundu").
2. **Eşleşme kodu:** "Kodu yenile" yeni kodu hemen gösteriyor. Başka yerden yenilenen kod denemede 1,8 saniyede ekranda göründü
   (ekran 5 saniyede bir tazeleniyor). 11 Kasım'daki durumun olası nedeni de kapatıldı: yenilemeden önce yola çıkmış eski bir cevap
   artık eski kodu geri getiremiyor.
3. **Taşınan klasör:** mümkün ve kuruldu. `baslat.bat`, sanal ortamın kayıtlarının eski yolu gösterdiğini anlıyor, kurulumu yeni
   klasöre göre yeniliyor (paketler silinmiyor) ve masaüstü kısayolunu yeniden oluşturuyor. Geçici bir kopyada denendi: klasör
   taşındıktan sonra "Program klasoru tasinmis…" dedi, kısayol betiğini çağırdı; ikinci çalıştırmada yeniden yapmadı. Bu bilgisayardaki
   gerçek kurulumda `baslat.bat` çalıştırılmadı (aşağıda "Kullanıcının yapacakları").
   Sınır: masaüstündeki eski kısayol kendi kendini düzeltemez; yeni klasördeki `baslat.bat`'a bir kez çift tıklamak gerekir.

## Adım 6 — Geçici klasörde deneme

Gerçek veritabanının kopyasıyla (SQLite yedekleme arayüzüyle, kaynak salt okunur), 8843 numaralı kapıda, yerel sayfalarla ve sahte bir
proxy istemcisiyle yapıldı. Gerçek kasaya dokunulmadı (bellekte kasa).

- Kopyada geçiş: şema 18 → 19; yalnız `job_hidden` eklendi (0 satır); toplam 165.268 → 165.268; `integrity_check` ok;
  `foreign_key_check` 0; uygulama `backups/studio-v18-…` yedeğini aldı.
- İşler paneli: 40 kart, açık günlük 0, en uzun günlük 1.480 satır. "Bitenleri kaldır (36)" → 4 kart kaldı (dördü de "Onay bekliyor").
  Veritabanında 40 iş duruyordu, 36'sı gizli. "Gizlenen işleri göster (36)" listesi açıldı; bir iş geri getirildi (günlüğü 15 satırla
  yerindeydi), sonra kendi "Kaldır" düğmesiyle yeniden kaldırıldı.
- Deneme işi (4 yerel site): eklenti **1** pencere açtı, iş bitince açık pencere **0**. Günlük: "3/4 · bolge-ornek.test: bölge engeli
  · proxy'yle okundu"; son satır "4/4 site okundu (1 bölge engelli site proxy'yle)."
- Programın kendi tarayıcısı: işin başlattığı tarayıcı iş sürerken açıktı, sayfa görünürdü, iş bitince kapandı.

Ekran görüntüleri (`docs/gorevler/GOREV-17/ekran/`):

| Dosya | Ne gösteriyor |
|---|---|
| `01-sol-menu-ayarlar-ve-bolum-dugmeleri.png` | Sol menüde Ayarlar öğesi ve Ayarlar'ın bölüm düğmeleri |
| `02-ayarlar-tonlar-bolumune-gidis.png` | "Tonlar" düğmesiyle bölüme gidiş |
| `03-isler-bitenleri-kaldir-oncesi.png` | İşler paneli, "Bitenleri kaldır" öncesi |
| `04-isler-bitenleri-kaldir-sonrasi.png` | Sonrası |
| `05-isler-gizlenen-isleri-goster.png` | "Gizlenen işleri göster" listesi ve "Geri getir" |
| `06-is-surerken-pencere-satiri.png` | Deneme işi sürerken panelde pencere satırı |
| `07-is-gunlugunde-proxy-metni.png` | İş günlüğünde proxy'yle okunan satırın yeni metni |
| `08-deneme-tablosunda-proxy-metni.png` | Deneme tablosunda aynı metin |

## Gerçek veritabanı (önce ve sonra)

CLAUDE.md kuralına göre yapıldı: program kapalıyken tam yedek, sonra program kısayolla açıldı, hiçbir düğmeye basılmadı, kapatıldı.

- Tam yedek: `work/yedek/20261111-1529/` — 45.538 dosya, 1.564.131.923 bayt; kopya kaynağıyla aynı, kaynak değişmedi.
- Program klasördeki `30A Studio.lnk` ile açıldı (0.19.0, kapı 8830) ve pencere kapatılarak kapandı.

| | Önce | Sonra |
|---|---|---|
| Şema | 18 | 19 |
| Toplam satır | 165.268 | 165.268 |
| Değişen tablo | — | yalnız `job_hidden` (yeni, 0 satır) |
| İşler | 40 (37 tamamlandı, 2 hata, 1 iptal) | aynı |
| Gizlenen iş | — | 0 (gizlemeyi kullanıcı yapacak) |
| İş kayıtlarının ve günlüklerinin karması | `1b01eaa6…` | aynı |
| `integrity_check` | ok | ok |
| `foreign_key_check` | 0 | 0 |
| `ayarlar.json`, `eklenti.json` | — | değişmedi |
| Uygulamanın kendi yedeği | — | `data/backups/studio-v18-2c5d9ace….sqlite3` |

## Housing Atlas'tan örnek alınanlar

Housing Atlas klasöründe hiçbir dosya değiştirilmedi; yalnız `git fetch` yapıldı ve dosyalar okundu.

| Housing Atlas | 30A Studio | Fark |
|---|---|---|
| Sol menünün altındaki çizgiyle ayrılmış "Ayarlar" ve "Yardım" öğeleri; açık ekranda vurgu ve soldaki turuncu işaret (`app.js`, `app.css` `.nav-footer`, `.nav-item[aria-current]::before`) | `index.html` `nav.nav-footer`, `style.css` | "Yardım" yok (ekranı yok) |
| Ayarlar'ın bölüm listesi ve bölüm düğmeleri; düğme bölüme kaydırır ve odağı başlığa taşır (`settings.js` `SECTIONS`, `sectionNav`) | `studio/web/settings.js` `SECTIONS`, `settingsNav`; `app.js` `goToSettingsSection` | Bizde adres de bölümü gösterir ve düğme satırı üstte kalır |
| Her bölümün başlıklı ve simgeli kart olması (`card({title, icon, id})`) | `sectionCard` ve kart başlığındaki simge | Kartların içi bizde eski modüllerce çizilir |
| İşler panelinin başındaki "Bitenleri gizle" düğmesi (`jobs-panel.js`) | "Bitenleri kaldır" | Orada geçici süzgeç; bizde kalıcı, veritabanında ve geri getirilebilir |

## Kullanıcının görevden sonra yapacakları

1. **Eklentiyi Chrome'da yeniden yükleyin:** `chrome://extensions` sayfasında "30A Studio Yardımcısı"nın yenile (dairesel ok) düğmesine
   bir kez basın. Ayarlar → Tarayıcı eklentisi'ndeki "eski sürüm" notu kaybolur. Eşleşme kodunu yeniden yazmanız gerekmez.
2. **Masaüstündeki eski kısayol için:** yeni klasördeki (`C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`) `baslat.bat`
   dosyasına bir kez çift tıklayın. Kurulumu yeni klasöre göre yeniler ve masaüstü kısayolunu yeniden oluşturur. İnternet bağlantısı
   gerekebilir. Program klasördeki kısayolla zaten açılıyor; bu adım yalnız masaüstü kısayolu içindir.
3. **İşler panelini temizlemek isterseniz:** panelin başındaki "Bitenleri kaldır"a basın. Hiçbir şey silinmez.

## Yöneticinin karar vermesi gereken konular

1. **main'in CI çalışması.** `988ca8d` görev dalında ve etikette başarılı; main'e itişin kendi çalışması (43011750701) saatlerdir
   "sürüyor" görünüyor. Kod aynı olduğu için bir sorun beklenmez, ama GitHub'da bakılıp gerekirse yeniden çalıştırılabilir.
2. **Küçültülmüş pencere.** Odak almayan normal pencere seçildi (yukarıda nedeni). Pencere ekranda görünür ama öne geçmez. Tamamen
   görünmez olması istenirse küçültülmüş kip gerçek sitelerle ayrıca denenmeli; bu görevde gerçek siteye gidilemediği için denenmedi.
3. **Kiralama toplayıcısında şirket başına sekme.** Programın kendi tarayıcısı kiralama şirketlerinde hâlâ şirket başına bir sekme
   açıyor (aynı pencerede; şirketler aynı anda okunduğu ve her şirketin istekleri kendi sayfasından yapıldığı için). Tek sekmeye
   indirmek toplayıcının eşzamanlılığını değiştirmeyi gerektirir; bu görevin kapsamına alınmadı. Bu yol yalnız eklenti bağlı değilken
   ya da iş devredilince kullanılıyor.
4. **Onay bekleyen işler.** Görev metnine uyularak "Bitenleri kaldır" bunlara dokunmuyor. Gerçek veride bugün 4 iş bu durumda (eski
   başlık önerileri). Bunların da toplu kaldırılması istenirse tek satırlık bir değişiklik.
5. **Playwright'in Chromium'u.** Bu bilgisayarda kurulu değildi; kullanıcının onayıyla indirildi. `%LOCALAPPDATA%\ms-playwright`
   altındaki kopya bu oturumdan başlatılamadı (Windows "yan yana yapılandırma" hatası verdi); `work/gorev-17/cft` altına kopyalanan
   aynı sürüm çalıştı ve denemeler onunla yapıldı. Neden klasöre bağlı olduğu araştırılmadı.
6. **Hakkında kartının metni.** "Sonraki aşama: Claude ile video metni…" yazısı eskimiş (video metni v0.17.0'da geldi). Yalnız düzen
   değişsin dendiği için metne dokunulmadı.
7. **Taşınan klasörün başlatıcıya bağlanması.** Taşınma şu an yalnız `baslat.bat` çalıştırılınca düzeltiliyor. Program kısayolla
   açıldığında da kendiliğinden düzeltmesi istenirse başlatıcıya eklenebilir; kullanıcının masaüstüne sormadan dokunmamak için
   eklenmedi.
