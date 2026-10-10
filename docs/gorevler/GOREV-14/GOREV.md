GÖREV-14 — Masaüstü programı, iş akışı paneli, Claude kullanımı ve talimatlar, kullanıcının kendi başlığı, içerik planından video paketi ve kullanıcının kendi tarayıcısıyla veri çekme (eklenti)

BAĞLAM
GÖREV-13 kabul edildi: program arka planda Claude'u çağırıyor ve konu ve başlık önerisi alınabiliyor. Kullanıcı programı kendisi kullanmaya başladı: başlık önerisini kendisi aldı ve Claude'un ürettiği başlıkları programda inceledi. Bu görevdeki işlerin çoğu kullanıcının programı kullanırken istediği şeylerdir:
- Program masaüstü programı gibi çalışsın (Housing Atlas gibi).
- Sol menüde iş akışı görünsün: hangi aşamadayız, ne yapmak gerekiyor.
- Sol menünün altında Claude kullanımı görünsün.
- İşler panelinde Claude çalışmasının ilerlemesi görünsün.
- Talimatlar programın içinden, Ayarlar'dan güncellensin.
- Kullanıcı kendi başlığını yazıp Claude'a değerlendirtebilsin; önerilen başlığı seçmeden önce düzeltebilsin.
- Programın açtığı tarayıcıyla girilemeyen sitelere kullanıcının kendi günlük Chrome'u üzerinden girilsin. Kullanıcı bu sitelere kendi tarayıcısıyla girebiliyor. Bu bir eklentiyle yapılacak (Adım 7).
Ayrıca yöneticinin GÖREV-13 sonrası kararları uygulanır: video paketinin içerik planından kurulması, özet tablolarında hafta tarihleri, model listesi, restoran sayısı notu, toplulukların plaj erişimi referansları ve başlık ekinin ayara alınması.

Bu büyük bir görevdir ve gece boyunca sürebilir. Adımları sırayla yap; her adımın sonunda testler geçmeli.

Housing Atlas Stüdyo (`C:\Users\1\source\repos\housing-atlas`) ayrı bir projedir. Ona dokunulmaz; yalnız örnek olarak okunur ve orada hiçbir dosya değiştirilmez. Bu görevde bakılacak yerler şunlardır:
- Masaüstü başlatıcısı: `atlas/launcher.py`, `atlas/watchdog.py`, `baslat.bat`, `kisayol-olustur.ps1`, `tools/make_icon.py`.
- Sol menü ve adım durumları: `docs/TASARIM.md` Bölüm 6 ve 7.2; `atlas/web/js/` altındaki menü ve adım dosyaları; `atlas/state.py`.
- İlerleme çubuğu: `atlas/web/js/jobs-panel.js`; TASARIM 10.1'deki M6e maddesi.
- Kullanım bilgisi: `atlas/ai/runner.py` (`rate_limit_event`, `RATE_WINDOWS`) ve Keşif ekranındaki 5 saatlik ve haftalık kullanım gösterimi.
- Talimat düzenleme: TASARIM 10.4.

Kullanıcı bu görev için şu izinleri kendi mesajında açıkça veriyor:
- main'e alma ve etiket,
- gerçek veritabanını normal kullanımla güncelleme (önce tam yedek),
- Adım 9'da kendi Claude aboneliğiyle iki küçük gerçek çalıştırma,
- masaüstüne kısayol oluşturma.
Bilgisayarda zamanlanmış görev oluşturulmaz.

KESİN SINIRLAR
- Housing Atlas klasöründe hiçbir dosya değiştirilmez.
- data/ yalnız Adım 9'da, CLAUDE.md kuralına göre (önce tam yedek, sonra uygulamanın normal kullanımı) değişir. Toplayıcı çalıştırılmaz.
- main'e yalnız Adım 1'deki fast-forward ile dokun; yalnız Adım 1'deki etiketi koy.
- Gerçek sitelerden eklentiyle veri çekilmez. Eklentiyi kullanıcı kendi Chrome'una kuracak; ilk gerçek çekimi kullanıcı başlatır.
- Eklentinin testleri yalnız yerel test sayfalarında yapılır. Bunun için Playwright'in Chromium'u geçici bir profille kullanılabilir. Bu bir veri toplama tarayıcısı değildir ve gerçek sitelere gitmez.
- Kullanıcının kendi Chrome profiline, çerezlerine, parolalarına ve geçmişine program da eklenti de erişmez.
- Hesaplara giriş, form doldurma ve ücretli içeriği aşma yok. Doğrulamayı kullanıcı yapar; doğrulama çözme servisi, gizlenme, parmak izi sahteciliği, proxy ve IP değiştirme yok.
- Talimat metinleri yalnız bu görevin eklerinde verildiği gibi değiştirilir. Talimat içeriği uydurulmaz.
- Testler gerçek Claude'u çağırmaz; sahte claude programı kullanılır.
- Claude Code başlık seçmez, video kaydı oluşturmaz (geçici klasördeki denemeler hariç).

==================================================
ADIM 1 — v0.15.0'ı main'e al; yöneticinin talimat değişikliklerini commit et
==================================================
1a. Çalışma ağacında yöneticinin 10 Ekim'de doğrudan güncellediği iki dosya var, henüz commit edilmedi:
- `studio/destinations/thirty_a_claude/baslik.md` (başlık dili, kanıtın ötesine geçmeme, başlık eki),
- `studio/destinations/thirty_a_claude/kanal_arastirmasi.md` (7. bölüm: başlık eki için arama ve başlık verisi).
Bunları kaybetme. Önce origin/gorev-13-claude-baslik'in son commit'i (a59ec65) için GitHub Actions sonucunu kontrol et; başarısızsa önce düzelt. Sonra main'i bu commit'e fast-forward ile getir ve push et; "v0.15.0" açıklamalı etiketini koy (mesaj: "v0.15.0 — programın içinde Claude: çalıştırıcı, Claude ayarları, Videolar ekranı ve konu ve başlık önerisi") ve push et. main ve etiket CI sonucunu rapora ekle. Güncel main'den "gorev-14-masaustu-eklenti" dalını aç. Yöneticinin iki dosyasını bu dalda ilk commit olarak ekle (mesaj: "talimat: yöneticinin başlık talimatı ve kanal araştırması güncellemesi (10 Ekim)").

1b. Yöneticinin GÖREV-13 kararlarını uygula (Adım 4 ve 6'daki ilgili maddeler) ve rapora işle.

==================================================
ADIM 2 — Masaüstü programı
==================================================
Housing Atlas'taki başlatıcının davranışını taşı. Programın kendisi aynı kalır (yerel web uygulaması); masaüstü hissini başlatıcı verir:
- Konsol penceresi olmadan başlatma (`pythonw`, `-X utf8`).
- Uygulama kipi pencere: önce Edge, yoksa Chrome, yoksa varsayılan tarayıcı. Adres çubuğu ve sekme olmaz; pencere adı "30A Studio".
- Tek kopya: program zaten açıksa ikinci açılışta yeni sunucu açılmaz, açık pencere öne gelir; yoksa yeni pencere açılır. Başlatma kilidi ve sağlık kontrolü Housing Atlas'taki gibidir.
- Boş port: 8830'dan başlayarak 8830–8849 aralığında. Bu aralık Housing Atlas'ınkiyle (8790–8809) çakışmaz; iki program aynı anda açık olabilir.
- Kapanma bekçisi: pencere kapanınca sunucu kapanır. Bir iş (toplayıcı, Claude çalışması, eklenti işi) sürüyorsa iş bitince kapanır ve bu, günlüğe ve iş paneline yazılır.
- Başlatma başarısız olursa Türkçe hata kutusu gösterilir.
- Kurulum: `baslat.bat` ilk seferde kurar, sonra konsolsuz başlatır.
- Masaüstü kısayolu: `kisayol-olustur.ps1` masaüstünde simgeli bir "30A Studio" kısayolu oluşturur (Unicode yollar için Housing Atlas'taki yöntem). Simge için sade bir 30A simgesi üret (`tools/make_icon.py` benzeri).
- Geliştirme ve deneme için mevcut komut satırı aynen çalışmaya devam eder: `python -m studio --data-dir … --no-browser --port …`. Pencere açmamak için ayrıca `--no-window` eklenebilir.
Testler: tek kopya, port seçimi, kilit, bekçinin iş sürerken beklemesi (Housing Atlas'taki testlere benzer, Windows'a özgü kısımlar taklitle).

==================================================
ADIM 3 — İş akışı paneli (sol menü)
==================================================
30A'da iş akışının birimi videodur (Housing Atlas'ta eyalet). Sol menü şu andaki sabit listenin (`studio/catalog.py` STEPS, "Planlanan aşama") yerine şöyle olur:
- **Üst çubuk:** video seçici (Housing Atlas'taki eyalet seçicinin yerine; "Video seçilmedi" ve video kayıtları başlıklarıyla) ve seçili videonun "●●○○○○○○ 2/8 adım" göstergesi.
- **ADIMLAR grubu (seçili videonun):** 1 Veri · 2 Konu ve başlık · 3 Veri paketi · 4 Video metni · 5 Kontrol · 6 Görsel plan · 7 Video üretimi · 8 Yayın hazırlığı. Her adımın altında canlı durumu yazar. Durumlar Housing Atlas'taki gibidir: bekliyor, hazır, çalışıyor, onay bekliyor, onaylandı, tamamlandı, hata, eskidi. Henüz kurulmamış adımlar "planlanan" diye görünür (video metni, kontrol, görsel plan, video üretimi, yayın hazırlığı).
  - Veri: zamanı gelen kaynak varsa "güncelleme zamanı geldi", yoksa "güncel".
  - Konu ve başlık: onay bekleyen çalışma varsa "onay bekliyor"; video kaydı seçildiyse "onaylandı".
  - Veri paketi: video kaydının paketi varsa "tamamlandı". Paket verinin son çekiminden eskiyse "eskidi".
- **Durumlar ayrı bir dosyada tutulmaz:** kayıtlardan hesaplanır (video kaydı, Claude çalışmaları, paketler, çekimler). Böylece gösterilen durum ile gerçek kayıt birbirinden kopmaz.
- **Sıradaki iş:** her adımın ekranının başında "Sıradaki iş" satırı bulunur. Bu satır ne yapılması gerektiğini ve hangi düğmeye basılacağını söyler; örneğin "Başlık seçilmedi: onay bekleyen öneriden bir başlık seç ya da yeni öneri al".
- **VERİ grubu:** araç ekranları bu grupta durur: veri kaynakları, veri toplama, veri kontrolü, kanıt paketi.
- **Kalkan yer tutucular:** "Rakip analizi" ve "İçerik briefi". Rakip araştırması kanal araştırması dosyasındadır; brif, veri paketidir.
- **Ayarlar:** en altta kalır.
Testler: durum hesaplarının kayıtlardan doğru çıkması (her durum için), eskime kuralı, sıradaki iş metni.

==================================================
ADIM 4 — Claude: kullanım paneli, ilerleme çubuğu, talimat düzenleyici, model listesi, başlık eki
==================================================
4a. **Claude kullanım paneli** (sol menünün altında, son adımla Ayarlar arasındaki boş alan).
- Claude her cevabından sonra akışta kullanım bilgisini veriyor (`rate_limit_event`: 5 saatlik ve haftalık pencere, kullanım oranı, sıfırlanma zamanı). Çalıştırıcı bunu zaten okuyor; her ölçüm zamanıyla birlikte saklanır.
- Panelde şunlar görünür:
  - 5 saatlik kullanım yüzdesi ve sıfırlanma saati,
  - haftalık kullanım yüzdesi ve sıfırlanma günü ve saati,
  - ölçümün zamanı ("son ölçüm 21:17"),
  - bu haftaki Claude çalışmalarının sayısı ve toplam süresi.
- "Yenile" düğmesi kullanımı en küçük bir çağrıyla tazeler: araçsız, tek tur, en ucuz model ailesi ve düşük efor. Bu çağrı ve modeli Ayarlar'da gösterilir.
- Hiç ölçüm yoksa "henüz ölçüm yok" yazar. Ölçüm 5 saatten eskiyse soluk görünür ve yanında "eski ölçüm" yazar.

4b. **İlerleme çubuğu** (İşler paneli).
- Housing Atlas'taki gibi dolan bir çubuk ve yüzde gösterilir.
- Tur oranı burada yanıltır: bir başlık çalışması 30 turun yalnız 5–6'sını kullanıyor. Bu yüzden Claude çalışmasında çubuk aşamalardan ilerler:
  - girdiler hazırlanıyor (%0–10),
  - Claude çalışıyor (%10–90): geçen süre, aynı adımın önceki başarılı çalışmalarının ortanca süresine bölünür; önceki çalışma yoksa varsayılan süre kullanılır; %90'ı geçmez,
  - doğrulama ve Markdown (%90–100).
- Yanında yüzde, geçen süre ve tahmini kalan süre yazar. Mevcut "Tur 3/30 · Okuyor: …" satırı altında kalır.
- Toplayıcı işlerinin mevcut ilerlemesi bozulmaz.

4c. **Talimat düzenleyici** (Ayarlar → Talimatlar).
- Destinasyonun talimat dosyaları listelenir: ortak, başlık, başlık değerlendirme (Adım 5) ve bilgi dosyası olarak kanal araştırması.
- Bir dosya açılır, düzenlenir ve kaydedilir.
- Tek kaynak repodaki dosyadır. Yönetici de aynı dosyayı dışarıdan düzenliyor; iki ayrı kopya olmaz.
- Kaydederken dosya diskte, açıldığından beri değişmişse (karma farklıysa) uyarı verilir ve üzerine yazılmaz; kullanıcı yeniden yükleyip öyle kaydeder.
- Her kayıtta önceki sürüm veri klasöründe saklanır (`data/claude/talimat_gecmisi/<dosya>/<zaman>.md`). Sürümler listelenir; "bu sürüme dön" ile eski hali geri getirilebilir.
- Claude çalışmalarının ekranında, o çalışmanın talimatın hangi sürümünü (karma ve tarih) kullandığı görünür.

4d. **Model listesi.** `claude-sonnet-5-5` eklenir. Housing Atlas'taki aile takma adları ("opus", "sonnet", "haiku": Claude Code'un o ailedeki en yeni modeli) seçilebilir olur. Doğrulanmamış tam model kimliği eklenmez.

4e. **Başlık eki ayarı.**
- Ayarlar'da destinasyon için iki alan bulunur: İngilizce başlık eki (başlangıç değeri " | 30A Florida Vacation") ve Türkçe başlık eki (" | 30A Florida Tatili").
- Program ekleri her başlık ve değerlendirme çalışmasında `secim.md` dosyasına yazar.
- Doğrulayıcı her adayın İngilizce başlığının İngilizce ekle, Türkçe karşılığının Türkçe ekle bittiğini denetler.
- `baslik.md` içindeki ek cümlesi Ek B'deki cümleyle değiştirilir; dosyanın geri kalanına dokunulmaz.

==================================================
ADIM 5 — Kullanıcının kendi başlığı ve seçmeden önce düzeltme
==================================================
5a. **Kendi başlığını değerlendirme** (yeni Claude adımı: "Başlık değerlendirme").
- Videolar ekranında "Kendi başlığını yaz" alanı bulunur. Kullanıcı aklındaki başlığı ya da fikri yazar; Türkçe ya da İngilizce olabilir. Yanında bölge seçimi ve isteğe bağlı bir not vardır.
- Program yeni bir Claude çalışması başlatır:
  - talimatlar: `ortak.md` ve `baslik_degerlendirme.md` (Ek A),
  - şema: `studio/ai/schemas/baslik_degerlendirme.schema.json`,
  - girdiler: başlık adımıyla aynı dosyalar, ayrıca `kullanici_basligi.md` ve `baslik_olculeri.md` (`baslik.md`'nin kopyası; başlığın ölçüleri orada).
- Şema:
  - `surum`, `adim`, `notlar[]`,
  - `kullanici_fikri` (kullanıcının yazdığı, aynen),
  - `doluluk{dolar_mi, aciklama}`,
  - `sorunlar[]` (kullanıcının ifadesindeki sorunlar; yoksa boş),
  - `adaylar[]`: 1–3 aday, başlık adımındaki aday yapısıyla aynı.
- Anlam denetimleri başlık adımındakilerle aynıdır; aday sayısı 1–3'tür. `dolar_mi` yanlışsa aday listesi boş olabilir, ama `aciklama` ve eksik veri doldurulmalıdır.
- Onay ekranı başlık adımınınkiyle aynı biçimdedir: önce değerlendirme özeti, sonra adaylar ve "Bu başlığı seç".

5b. **Seçmeden önce düzeltme.**
- Aday ayrıntısında "Başlığı düzenle" ile İngilizce başlık ve Türkçe karşılığı değiştirilebilir. Program ek ve uzunluk kurallarını denetler.
- Kullanıcı İngilizce bilmiyor. Bu yüzden yalnız Türkçe karşılığı değiştirdiyse "İngilizcesini Claude yazsın" düğmesi görünür. Bu düğme değiştirilen Türkçe başlıkla bir başlık değerlendirme çalışması başlatır (`kullanici_basligi.md` Türkçe başlık olur, not alanına "bu aday düzenlendi" ve adayın analizi yazılır).
- Video kaydı hem önerilen başlığı hem düzenlenmiş halini tutar ve "kullanıcı düzenledi" işareti taşır.

5c. Testler (sahte claude): değerlendirme çalışmasının girdileri ve şeması; dolmayan fikir; 1–3 aday sınırı; ek denetimi; düzenlemenin kayda geçmesi; Türkçe düzenlemeden değerlendirme çalışması.

==================================================
ADIM 6 — Video paketi içerik planından; özet tablolarında hafta tarihleri; restoran notu
==================================================
6a. **Video paketi seçilen adayın içerik planından kurulur** (yönetici kararı, GÖREV-13 karar 1–2).
- Paketin bölümleri planın bölümleridir ve aynı sırayla gelir. Bölüm başlığı `bolum`, bölümün sorusu `ne_anlatir` olur.
- Her bölümde iki şey bulunur:
  - planın gösterdiği kanıt satırları,
  - bu satırların ait olduğu blokların tamamı. Blokların tamamı bağlam içindir; örneğin yalnız Temmuz hücresi değil bütün konaklama tablosu gelir.
- Bir blok birden çok bölümde geçiyorsa ilk geçtiği bölümde tam yazılır; sonraki bölümler oraya gönderme yapar.
- Kaynak paketler, adayın girdisi olan 30A paketi ve (varsa) mahalle paketidir; GÖREV-13'teki kimlik eşlemesi kullanılır.
- Paketin başında şunlar bulunur:
  - başlık, soru, kanca (değerleriyle), neden önerildiği ve eksik veri,
  - bilinen boşluklar,
  - yayından önce kontrol edilecek satırlar.
- Yazar özeti ve sayı CSV'si aynı makineyle üretilir.
- "Yeni şablon gerekir" artık paketi engellemez; bilgi olarak kalır. Şablon paketleri (ilk video, mahalle rehberi) veri evreni ve veri özeti olarak kalır.
- Videolar ekranındaki "Kanıt paketi üret" düğmesi bu paketi üretir.

6b. **Hafta tarihleri.** Yazar özetinde pencere sütunu olan bütün tablolarda (konaklama fiyatı, çeyrekler, oda grubu, ilan sayısı) sütun başlığı pencerenin tarihlerini de taşır: "Mar 2027 (13–20)". Aynı ay iki pencere içeriyorsa ikisi ayrı sütundur. Sebep: Claude "hangi hafta olduğu özette yazmıyor" diye not düştü. Mart penceresi (13–20 Mart) Dallas ISD bahar tatiliyle (15–19 Mart) çakışıyor; bu bilinmeden "mart nisandan pahalı" gibi bir sonuç yanlış yorumlanır.

6c. **Restoran sayısı notu.** Özette ve pakette mahalle toplamının (141) restoran sayısından (138) büyük olmasının sebebi açıkça yazılır: bazı restoranlar iki mahalleye bağlı. Sayılar sabit yazılmaz, üretim anında hesaplanır.

==================================================
ADIM 7 — Kullanıcının kendi Chrome'u üzerinden veri çekme: "30A Studio Yardımcısı" eklentisi
==================================================
Sorun: bazı sitelere programın açtığı tarayıcıyla (ayrı profil, CDP bağlantısı) girilemiyor, ama kullanıcı kendi günlük Chrome'uyla girebiliyor. Raporlarda geçen siteler şunlardır:
- realjoy.com (61 ilan) ve order.online (3 restoran menüsü): doğrulama geçmedi.
- HCA Florida, CVS, Publix, Winn-Dixie, The Fresh Market: "bu bilgisayardan okunamadı".

Kullanıcının günlük profiline programın doğrudan bağlanması yapılmaz. Chrome yeni sürümlerinde varsayılan profilde uzaktan hata ayıklama bağlantısına izin vermiyor; profil kopyalamak işe yaramıyor ve kullanıcının kişisel oturumlarını programa açar. Çözüm, kullanıcının kendi Chrome'una kurduğu küçük bir eklentidir. Eklenti sayfaları kullanıcının tarayıcısında normal sekmeler olarak açar ve yalnız sayfanın içeriğini programa verir.

7a. **Eklenti (Chrome, Manifest V3)** repoda `eklenti/` klasöründe durur. Adı "30A Studio Yardımcısı"dır, arayüz metinleri Türkçedir.
- **İzinler en dar tutulur:**
  - `tabs`, `scripting`, `storage`, `alarms`, `notifications`,
  - `http://127.0.0.1/*` (yalnız yerel program),
  - siteler için `optional_host_permissions`.
  - Çerez, geçmiş, yer imi, indirme ve `debugger` izni yoktur. Eklenti CDP kullanmaz.
- **Site izni:** program bir alan adı için iş verdiğinde, o alan adına izin yoksa eklenti penceresinde (popup) "İzin ver" düğmesi görünür. İzni kullanıcı verir (`chrome.permissions.request`); eklenti izinsiz siteye gitmez.
- **Programla eşleşme:** Ayarlar → Tarayıcı eklentisi ekranında bir eşleşme kodu görünür. Kullanıcı bu kodu eklenti penceresine bir kez yazar. Eklenti, programı 127.0.0.1 üzerinde 8830–8849 aralığında `/api/health` ile kendisi bulur. Kod, programın veri klasöründe ve eklentinin `storage`'ında saklanır; Ayarlar'dan yenilenebilir.
- **İş akışı:**
  1. Eklenti, program açıkken birkaç saniyede bir yeni iş sorar.
  2. Bir iş, sayfa adreslerinin listesi ve her sayfa için bekleme kuralıdır: sayfa yüklendikten sonra en az şu kadar saniye bekle ya da şu öğe görünene kadar bekle.
  3. Eklenti kendi açtığı ayrı ve öne gelmeyen bir pencerede sayfaları teker teker açar. Kullanıcının mevcut sekmelerine dokunmaz.
  4. Sayfa hazır olunca, yalnız kendi açtığı sekmeye içerik betiği koyarak sayfanın işlenmiş halini (`document.documentElement.outerHTML`, son adres, başlık, HTTP durumu biliniyorsa) alır, programa gönderir ve sekmeyi kapatır. İş bitince pencereyi kapatır.
- **Hız:** aynı alan adında iki sayfa arasında en az 8 saniye beklenir (Ayarlar'dan değiştirilebilir) ve bir anda tek sayfa açılır.
- **Doğrulama sayfası:** programın mevcut doğrulama işaretleriyle tanınır (`studio.sources.browser_verification`). Görülürse eklenti işi duraklatır, pencereyi öne getirir ve "30A Studio: doğrulama bekleniyor" bildirimi gösterir. Doğrulamayı kullanıcı yapar, eklenti devam eder. 15 dakika içinde geçilmezse o sayfa atlanır ve kayda yazılır.
- **Yasaklar:** giriş sayfası, ödeme sayfası ve form yoktur. Eklenti tıklamaz, yazı yazmaz, yalnız adres açar. Sayfa giriş istiyorsa "giriş gerekiyor" diye işaretler ve atlar.
- **Kod okunur kalır:** sıkıştırma ve gizleme yoktur; kullanıcı ne yaptığını görebilir.

7b. **Programın tarafı.**
- **Yeni API:** `/api/eklenti/...`. Yalnız eşleşmiş eklentinin kökenini (`chrome-extension://<kimlik>`) ve eşleşme kodunu kabul eder; CORS yalnız o köken için açıktır.
- **Güvenlik sıkılaştırması:** programın kendi API'sinde durum değiştiren istekler başka kökenlerden (ör. kullanıcının açtığı herhangi bir web sitesinden) gelirse reddedilir. Kullanıcının tarayıcısı artık programla konuşacağı için bu şarttır.
- **Kayıt:** eklentiden gelen sayfalar, diğer çekimler gibi ham kopya ve SHA-256 ile saklanır. Kayıtta yöntem "eklenti" diye yazılır.
- **Okuma sırası:** engel görülen alan adları için yeni okuma sırası şudur:
  1. doğrudan istek,
  2. engel varsa ve eklenti bağlıysa eklenti,
  3. eklenti bağlı değilse programın kendi tarayıcısı (mevcut CDP yöntemi),
  4. o da olmazsa atla ve kaydet.
  `browser_hosts` alan adı başına hangi yöntemin işe yaradığını tutar.
- **Bağlantı:** toplayıcılar sayfa alma işini mevcut ortak katman üzerinden yaptığı için eklenti yöntemi o katmana eklenir; restoran siteleri, kiralama şirketleri ve günlük ihtiyaç zincir kontrolleri bundan yararlanır.
- **Eklenti bekleniyorsa:** iş "eklenti bekleniyor" durumunda bekler. İş panelinde "Eklenti bağlı değil: Chrome'u açın" yazar ve kullanıcı isterse işi programın kendi tarayıcısına devredebilir.
- **Ayarlar → Tarayıcı eklentisi ekranı:**
  - bağlantı durumu (bağlı / bağlı değil, son görülme, eklenti sürümü),
  - eşleşme kodu ve "kodu yenile",
  - eklentinin izin verilmiş ve izin bekleyen alan adları,
  - hız ayarı,
  - kurulum adımları (aşağıda),
  - "Deneme" düğmesi: eklentiyle tek bir sayfa açıp sonucu gösterir. Varsayılan deneme sayfası programın kendi yerel deneme sayfasıdır, gerçek bir site değildir.
  - "Sorunlu sitelerden birer sayfa dene" düğmesi: yukarıdaki listeden her alan adı için tek bir sayfa okur ve sonucu tablo halinde gösterir. Bu düğmeye kullanıcı basar; Claude Code bu görevde basmaz.

7c. **Kurulum (kullanıcı yapar, bir kez):** Türkçe ve resimli kısa bir rehber yazılır (`eklenti/KURULUM.md` ve Ayarlar ekranında). Adımlar:
1. Chrome'da `chrome://extensions` adresini açın.
2. Sağ üstten "Geliştirici modu"nu açın.
3. "Paketlenmemiş öğe yükle" ile repodaki `eklenti` klasörünü seçin.
4. Eklentiyi araç çubuğuna sabitleyin.
5. Programda Ayarlar → Tarayıcı eklentisi ekranındaki kodu eklentiye yazın.
6. "Deneme" düğmesine basın.

7d. **Testler:**
- Eklentinin saf mantığı Node testleriyle sınanır: iş kuyruğu, hız sınırı, doğrulama tanıma, giriş sayfası tanıma.
- Programın eklenti API'si TestClient ile sınanır: eşleşme kodu, köken denetimi, başka kökenden durum değiştiren isteğin reddi, iş yaşam döngüsü, ham kayıt.
- Uçtan uca deneme: Playwright'in Chromium'u geçici profille eklentiyi yükler ve yerel bir deneme sunucusunda şunları sınar: normal sayfa, JavaScript ile çizilen sayfa, doğrulama sayfası benzeri, giriş isteyen sayfa. Gerçek siteye gidilmez.

7e. **Belge:**
- yeni `docs/M16-TARAYICI-EKLENTISI.md` (neden, mimari, izinler, güvenlik, iş akışı, sınırlar),
- CLAUDE.md'deki tarayıcı kuralına eklenti yöntemi: engel görülen sitelerde ilk tercih, eklenti bağlıysa kullanıcının kendi Chrome'udur; programın kendi tarayıcısı yedektir. Diğer bütün kurallar aynen kalır.

==================================================
ADIM 8 — Toplulukların plaj erişimi (referans satırları)
==================================================
İzleyicinin en çok tartıştığı konu plaj erişimi. Elimizde ilçenin halka açık erişim listesi var. Seaside, WaterColor, WaterSound, Alys Beach ve Rosemary Beach topluluklarının kendi sakinlerine ve misafirlerine açık özel plaj erişimleri hakkında ise kaynaklı satır yok. Rosemary ile ilgili 9 başlık önerisinin hepsinde bu eksik olarak çıktı.
- Her topluluk için topluluğun kendi resmî sitesinden, topluluk derneğinin sitesinden ya da topluluğun resmî kiralama şirketinin sitesinden şunları bul:
  - kiracıların ve misafirlerin plaja nereden ve nasıl girdiği (topluluğa özel plaj geçitleri, sayısı ya da adı varsa),
  - kimlerin kullanabildiği (sakin, kiracı, ziyaretçi),
  - varsa erişilebilirlik (rampa, merdiven),
  - misafir park kuralı.
- Referans tablosuna satır olarak ekle; kuralı aynıdır: birincil kaynak, kısa alıntı, tarih, SHA-256. Giriş gerektiren sayfaya girilmez. Bulunamayan bilgi "bulunamadı" diye rapora yazılır, tahmin edilmez.
- Bu satırlar `plaj-erisimi` konusunda ve mahalle paketine de girer.

==================================================
ADIM 9 — Gerçek ortam ve teslim
==================================================
1. **Geçici klasörde deneme** (gerçek verinin kopyası, sahte claude):
   - masaüstü başlatıcısı (pencere, tek kopya, kapanma),
   - iş akışı paneli: video yokken ve geçici bir video kaydıyla,
   - kullanım paneli ve ilerleme çubuğu,
   - talimat düzenleyici (kaydet, sürüm, geri dön, diskteki değişiklik uyarısı),
   - kendi başlığını değerlendirme, seçmeden önce düzenleme,
   - geçici video kaydından içerik planlı video paketi,
   - eklenti: geçici profil ve yerel deneme sayfalarıyla.
2. **Migration** gerçek verinin kopyasında denenir (şema 15 → 16; uygulama 0.16.0): satır sayıları, integrity_check, foreign_key_check.
3. **Gerçek veritabanı** (CLAUDE.md kuralına göre):
   1. data/ tam yedeği.
   2. Uygulamayı yeni başlatıcıyla gerçek veriyle aç.
   3. Referans tablosunu (Adım 8) yükle.
   4. Kullanıcının aboneliğiyle iki küçük gerçek çalıştırma yap:
      - "Yenile" ile kullanım ölçümü (tek küçük çağrı),
      - bir "Başlık değerlendirme" çalışması. Bölge Rosemary Beach; kullanıcı başlığı "Rosemary Beach'e köpeğimizle gitsek nasıl olur?"; not boş.
   5. Başlık seçme, video kaydı oluşturma.
   6. Kapat; önce/sonra karşılaştırması (satır sayıları, integrity_check, foreign_key_check).
4. **Masaüstü kısayolu:** `kisayol-olustur.ps1` ile kullanıcının masaüstüne kısayol oluştur; kısayolla açılışı dene.
5. **Değerlendirme çalışmasını oku** ve rapora yaz:
   - Fikrin içinin dolup dolmadığını dürüstçe söylemiş mi? Elimizde köpeklerin halka açık plajlardaki durumu var; Rosemary'ye özgü kural yok.
   - Kanıt değerleri doğru mu, ek kurala uyuyor mu?
   - Süresi, turu ve token'ları.
6. **Belgeler:**
   - CALISMA_MANTIGI.md, README.md (masaüstü kısayolu, eklenti kurulumu),
   - docs/DEVIR/05 ve 02'nin güncel durum satırları,
   - M14 (içerik planlı video paketi, hafta tarihleri),
   - M15 (kullanım paneli, ilerleme, talimat düzenleyici, başlık değerlendirme, düzenleme, başlık eki),
   - yeni M16, CLAUDE.md (tarayıcı kuralı).
   - Tam test takımı yerelde art arda en az 3 kez geçmeli.

TESLİM
docs/gorevler/GOREV-14/ altına şunlar konur:
- GOREV.md (work/gorevler/GOREV-14.md'nin kopyası) ve RAPOR.md,
- gerçek değerlendirme çalışmasının JSON, Markdown, görev metni ve çalışma kaydı (akış kaydı hariç),
- eklenti kurulum rehberinin kopyası,
- ekran görüntüleri:
  - masaüstü penceresi,
  - sol menüdeki iş akışı (video yokken ve geçici bir videoyla),
  - kullanım paneli,
  - İşler panelinde ilerleme çubuğu,
  - Ayarlar → Talimatlar,
  - Ayarlar → Tarayıcı eklentisi,
  - kendi başlığını yazma ve değerlendirme ekranı,
  - başlık düzenleme,
  - içerik planlı video paketinin başı.
RAPOR.md Türkçe ve sade olur. İçinde şunlar bulunur:
- her adımın sonucu,
- main ve etiketin konumu, CI sonuçları, test sayıları,
- Housing Atlas'tan taşınanlar ve bilerek değiştirilenler,
- eklentinin izinleri ve güvenlik önlemleri (tablo),
- toplulukların plaj erişimi için bulunanlar ve bulunamayanlar,
- gerçek değerlendirme çalışmasının özeti,
- gerçek veritabanının öncesi/sonrası,
- beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-14 bitti, dal gorev-14-masaustu-eklenti, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.

==================================================
EK A — studio/destinations/thirty_a_claude/baslik_degerlendirme.md (aynen)
==================================================
# Kullanıcının başlığını değerlendirme

Kullanıcı aklındaki bir başlığı ya da video fikrini yazdı; kullanici_basligi.md dosyasında. Türkçe ya da İngilizce olabilir; tam bir başlık da olabilir, yalnız bir fikir de. Görevin bu fikri kanalın başlık önerileriyle aynı ölçülerle değerlendirmek ve kanala uygun bir başlığa dönüştürmek. İyi bir başlığın ölçüleri baslik_olculeri.md dosyasında; o dosyadaki aday sayısı ve çıktı biçimi bu görev için geçerli değil, ölçüler geçerli. Kullanıcının seçtiği bölge, notu ve başlık ekleri secim.md dosyasında; kanal planı, kanal araştırması, veri özetleri ve daha önce önerilen başlıklar başlık önerisindeki dosyalarla aynı.

Önce fikrin içinin elimizdeki veriyle dolup dolmadığına bak: 15–17 dakikalık bir videonun bölümlerini kurabiliyor musun? Dolmuyorsa bunu açıkça söyle ve neyin eksik olduğunu yaz. Kullanıcıyı memnun etmek için verinin taşımadığı bir plan kurma; dürüst bir "dolmuyor" kullanıcıya daha çok yarar.

Doluyorsa fikri bir başlığa çevir. Kullanıcının niyetine sadık kal; onun sorusunu tatilcinin kelimeleriyle sor. Kullanıcının kendi ifadesinde bir sorun varsa (kanıtın ötesine geçen bir iddia, aranmayan bir ifade, eksik başlık eki gibi) bunu kısaca yaz. En fazla üç ifade seçeneği ver; birincisi en çok önerdiğin olsun ve neden onu önerdiğini kısa tut. Bu fikir daha önce önerilen bir başlığa çok benziyorsa bunu söyle.

Kullanıcı İngilizce bilmiyor. Türkçe karşılık, İngilizce başlığın birebir çevirisi olsun ki kullanıcı neyi seçtiğini bilsin.

Çıktın baslik_degerlendirme.json dosyasıdır ve şemaya uyar: kullanıcının fikri aynen, doluluk değerlendirmesi, sorunlar ve 1–3 aday (fikir dolmuyorsa aday listesi boş kalabilir).

==================================================
EK B — baslik.md'de değişecek tek cümle
==================================================
Şu cümle:
Her İngilizce başlık " | 30A Florida Vacation" ekiyle biter; Türkçe karşılığı " | 30A Florida Tatili" ile.
şununla değiştirilir:
Her İngilizce başlık secim.md dosyasında yazan İngilizce başlık ekiyle, Türkçe karşılığı da oradaki Türkçe ekle biter.
