GÖREV-17 — Arayüz düzeltmeleri: İşler panelinde temizleme, Ayarlar düzeni, açılan pencerelerin düzenlenmesi ve küçük düzeltmeler

BAĞLAM
Program 11 Kasım'da yeni klasöre taşındı: `C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`. Kısayol `kisayol-olustur.ps1 -Hedef <program klasörü>` ile yeniden oluşturuldu.

GÖREV-16 (dal `gorev-16-eklenti-proxy`, son commit `988ca8d`, uygulama 0.18.0, şema 18) kabul edildi. Kullanıcı aynı gün eklentiyi yeni klasörden yeniden yükledi, eşleştirdi, ABD proxy'sini girdi ve "Sorunlu sitelerden birer sayfa dene"yi çalıştırdı: 7 siteden 7'si okundu (winndixie.com'u kullanıcı bölge engelli listeye elle ekledi). Bu görev, kullanıcının o sırada gördüğü arayüz sorunlarını düzeltir. Yeni özellik yoktur.

Housing Atlas Stüdyo (`C:\Users\1\source\repos\housing-atlas`) ayrı bir projedir. Ona dokunulmaz; yalnız örnek olarak okunur. Önce `git fetch` ile son hâline bak.

Kullanıcı bu görev için kendi mesajında şu izinleri veriyor:
- main'e alma ve etiket,
- gerçek veritabanını normal kullanımla güncelleme (önce tam yedek).

Bu görevde gerçek Claude çalıştırması yok. Gerçek sitelere istek yapılmaz. Bilgisayarda zamanlanmış görev oluşturulmaz.

KESİN SINIRLAR
- Housing Atlas klasöründe hiçbir dosya değiştirilmez.
- Hiçbir kullanıcı verisi silinmez. İşler panelinden kaldırılan işler yalnız gizlenir; kayıtları ve günlükleri yerinde kalır.
- Mevcut ayarların hiçbiri bozulmaz ve hiçbir ayar değeri değişmez. Ayarlar ekranının yalnız düzeni değişir.
- Eklenti ve proxy kuralları aynen geçerlidir (CLAUDE.md, M16, M18). Pencere düzenlemesi hız kuralını, doğrulamanın kullanıcı tarafından geçilmesini ve proxy'nin yalnız bölge engelli alan adlarında kullanılmasını değiştirmez.
- data/ yalnız Adım 6'da, CLAUDE.md kuralına göre değişir.

==================================================
ADIM 1 — v0.18.0'ı main'e al
==================================================
1. **Program açık mı:** Program açıksa kapanmasını bekle. 30 dakika içinde kapanmazsa yalnız kod işini yap; gerçek veri işini program kapalıyken yap ve bunu rapora yaz.
2. **Kullanıcının değişiklikleri:** Çalışma ağacında kullanıcının Ayarlar'dan yaptığı talimat, ton ya da uyarı ifadesi değişikliği varsa, bunları yeni dalda ilk commit olarak ekle (CLAUDE.md kuralı). `30A Studio.lnk` gibi kullanıcıya ait dosyaları commit etme; gerekiyorsa `.gitignore`'a ekle.
3. **main ve etiket:**
   - `988ca8d`'nin CI sonucunu kontrol et.
   - main'i bu commit'e fast-forward ile getir ve push et.
   - "v0.18.0" açıklamalı etiketini koy. Etiket mesajı: "v0.18.0 — eklentinin düzeltilmesi ve bölge engeli için ABD proxy'si".
4. **Yeni dal:** Güncel main'den "gorev-17-arayuz" dalını aç.

==================================================
ADIM 2 — İşler panelinde biten işleri kaldırma
==================================================
Kullanıcının sözü: "İşler panelinde bitenleri kaldır gibi bir seçenek yok, bir sürü geçmiş iş var."

Bugün panelde Eylül'den bu yana bütün işler duruyor. Bunlar arasında 1.480 satırlık günlüğü olan toplama işleri de var.

- **Toplu kaldırma:** Panelin başına "Bitenleri kaldır" düğmesi gelir. Bu düğme tamamlanan, hata veren ve iptal edilen işlerin hepsini panelden kaldırır. Çalışan, bekleyen ve onay bekleyen işlere dokunmaz.
- **Tek tek kaldırma:** Her bitmiş işin kartında küçük bir "Kaldır" düğmesi olur.
- **Kaldırmanın anlamı:** Kaldırma yalnız gizlemedir. İşin kaydı, günlüğü ve sonucu silinmez. İş gizli olarak işaretlenir; işaret veritabanında bir alan ya da küçük bir tabloda tutulur. Şema değişirse şema 19 olur ve geçiş yazılır.
- **Gizlenenleri geri getirme:** Panelin altında "Gizlenen işleri göster (N)" bağlantısı olur. Gizlenen işler orada listelenir ve "Geri getir" ile panele döner.
- **Örnek:** Housing Atlas'ın İşler panelinde benzer bir düzen varsa ona bak ve aynı davranışı kur.
- **Ayrıca:** Uzun günlükler (yüzlerce satır) kartta kapalı gelmeli. Bugün de öyleyse dokunma.

==================================================
ADIM 3 — Ayarlar düzeni Housing Atlas gibi
==================================================
Kullanıcının sözü: "İlgili ayarı seçip direkt gitme ve sol tarafta Ayarlar. Bizdeki durum şu anda belirgin değil. Referans olarak Housing Atlas uygulamasını alsın. Bozuk olmasın."

Kullanıcının gönderdiği Housing Atlas ekranlarına göre örnek davranış şöyle:
- **Sol menü:** Sol menünün en altında, ince bir çizgiyle ayrılmış iki öğe var: simgeli "Ayarlar" ve "Yardım". Ayarlar ekranı açıkken öğe vurgulu görünüyor ve solunda turuncu bir işaret var.
- **Ayarlar ekranı:** Ekranın üstünde bir açıklama, altında bölüm düğmeleri var (Görünüm, Klasörler, Video render, API anahtarları, FEMA proxy, Telegram, Tarayıcı, Claude Code, Talimat dosyaları, Hakkında…). Bir düğmeye basınca sayfa doğrudan o bölüme gidiyor. Her bölüm kendi başlığı ve simgesi olan bir kart.

Bizde bugün Ayarlar, sol menüde Claude kullanımı kutusunun altında küçük bir bağlantı olarak duruyor ve belirgin değil.

Yapılacaklar:
1. **Sol menü:** Sol menünün en altına Housing Atlas'taki gibi belirgin bir "Ayarlar" öğesi konur. Öğe simgeli ve vurgulanabilir olur.
   - "Yardım" öğesi yalnız programda bir yardım ekranı varsa konur. Yardım içeriği uydurulmaz. Yardım ekranı yoksa yalnız Ayarlar konur ve bu rapora yazılır.
   - Claude kullanımı kutusu yerinde kalır.
   - Eski küçük Ayarlar bağlantısı kaldırılır; aynı yere iki bağlantı olmaz.
2. **Bölüm düğmeleri:** Ayarlar ekranının üstüne, programdaki mevcut bölümlerin hepsi için birer düğme gelir. Örnekler: Claude, Tonlar, Talimatlar, Tarayıcı eklentisi, ABD proxy'si, … Hangi bölümler varsa onlar listelenir.
   - Düğmeye basınca sayfa o bölüme kayar.
   - Adres de bölümü gösterir, örneğin `#ayarlar/tonlar`. Böylece başka ekranlardaki bağlantılar doğrudan bölüme gider: "Tonları yönet", eklenti uyarıları, proxy notları ve benzerleri.
   - Bu bağlantıları bul ve hepsini bölüm adresine bağla.
3. **Görünüm:** Her bölüm kendi başlığı (ve varsa simgesi) olan bir kart olur. Bütün renk, boşluk ve yazı tipleri mevcut CSS değişkenlerinden gelir.
4. **Hiçbir şey bozulmasın:**
   - Her bölümün kaydetme, deneme ve sürüm düğmeleri aynen çalışmalı.
   - Arayüz testleri geçmeli.
   - Her bölüm için en az bir test olmalı: düğmeyle gidilebiliyor ve bölümün ana düğmesi görünüyor.

==================================================
ADIM 4 — Açılan pencerelerin düzenlenmesi
==================================================
Kullanıcının sözü: "Sürekli web sayfası açıyor. Eklentiyle bağlantılı değil mi anlamadım? Bunu da kontrol ettir."

Önce incele, sonra düzelt:

1. **İnceleme:** Deneme işi ("Sorunlu sitelerden birer sayfa dene") ve toplayıcılar sırasında hangi pencerenin, kim tarafından, ne zaman açıldığını bul. Olası kaynaklar:
   - eklentinin kendi penceresi (kullanıcının Chrome'u),
   - programın kendi tarayıcısı (doğrulama ve CDP),
   - programın proxy tarayıcısı (bölge engelli, JavaScript'le çizilen sayfalar),
   - programın bir sekme ya da Edge penceresi açması.

   Sonucu raporda bir tabloyla ver: kaynak, ne zaman açılıyor, kaç kez, kapanıyor mu, öne geliyor mu.
2. **Düzeltme ilkeleri:**
   - Her kaynak, bir iş boyunca tek bir pencere kullanır. Pencere sayfa sayfa yeniden açılıp kapanmaz; aynı pencerede yeni sayfaya gidilir.
   - Pencere arka planda açılır: küçültülmüş ya da odak almadan. Kullanıcının çalıştığı pencerenin önüne geçmez.
   - Pencere yalnız kullanıcının geçmesi gereken bir doğrulama çıkınca öne gelir. Bugünkü doğrulama kuralları aynen kalır.
   - İş bitince ya da iptal edilince pencere kapanır.
   - İşler panelinde, pencere açıkken hangi iş için açık olduğu yazar. Örnek: "Eklentinin penceresi: realjoy.com okunuyor".
3. **Eklenti için:** Pencere `chrome.windows.create` ile `focused: false` (ya da `state: "minimized"`) açılır. Doğrulamada `chrome.windows.update` ile öne alınır. Pencere iş boyunca tekrar kullanılır.
   - Küçültülmüş pencerede sayfanın JavaScript'i ya da doğrulaması yavaşlıyor veya çalışmıyorsa, odaksız normal pencereyi seç ve bunu rapora yaz.
   - Eklentinin sürümü artar. Ayarlar'daki "eski sürüm" notu kullanıcıyı yeniden yüklemeye çağırır.
4. **Programın tarayıcıları için:** Aynı ilkeler geçerlidir: tek pencere, arka planda, iş bitince kapanır, doğrulamada öne gelir. Görünmez (headless) kip, doğrulama gerekebilecek yerlerde kullanılmaz.

==================================================
ADIM 5 — Küçük düzeltmeler
==================================================
1. **İş günlüğünde proxy:** İş günlüğü, proxy'yle okunan bölge engelli siteler için bugün yalnız "bölge engeli" yazıyor. Bu yanıltıcı. Sonuç şöyle yazılsın: "bölge engeli · proxy'yle okundu" (ya da okunamadıysa "proxy'yle de okunamadı"). Deneme tablosu ve İşler paneli de aynı dili kullanır.
2. **Eşleşme kodu:** "Kodu yenile"ye basınca Ayarlar → Tarayıcı eklentisi ekranı yeni kodu hemen göstersin. 11 Kasım'da kod yenilendi ama ekran F5'e basılana kadar eski kodu gösterdi; kullanıcı eski kodu yazdı ve eşleşme olmadı. Ekran başka yerden değişen kodu da birkaç saniyede kendisi tazelesin.
3. **Taşınan klasör:** Masaüstündeki eski kısayol eski klasörü gösteriyor ve tıklayınca hiçbir şey olmuyor. Programın klasörü taşındıysa ve `.venv`'deki betikler eski yolu gösteriyorsa, `baslat.bat` bunu anlayıp kurulumu yenilesin ve kısayolu yeni yerle yeniden oluştursun. Bunun mümkün olup olmadığını incele; mümkünse kur, değilse rapora yaz.

==================================================
ADIM 6 — Testler, gerçek ortam ve teslim
==================================================
1. **Testler:**
   - İşler panelinde gizleme ve geri getirme; çalışan işin gizlenememesi.
   - Ayarlar'da bölüm düğmeleri ve bölüm adresleri; diğer ekranlardaki bağlantılar.
   - Eklentinin tek ve arka plan penceresi (uçtan uca deneme, Playwright'in Chromium'unda yalnız yerel sayfalarla; Chromium'da `chrome.windows` sınırları varsa test tarafında uyarla).
   - Programın tarayıcılarının iş sonunda kapanması.
   - Proxy günlük metni.
   - Eşleşme kodunun ekranda tazelenmesi.
   - Şema değiştiyse geçiş.

   Tam takım yerelde art arda en az 3 kez geçmeli.
2. **Geçici klasörde deneme:** Gerçek verinin kopyası kullanılır. Ekran görüntüleri alınır:
   - sol menüde Ayarlar,
   - Ayarlar'da bölüm düğmeleri ve bir bölüme gidiş,
   - İşler panelinde "Bitenleri kaldır" öncesi ve sonrası, "Gizlenen işleri göster",
   - deneme işi sürerken İşler panelinde pencere satırı,
   - proxy'yle okunan satırın yeni metni.
3. **Gerçek veritabanı** (CLAUDE.md kuralına göre):
   1. data/ tam yedeği alınır.
   2. Program kısayolla açılır.
   3. Şema değiştiyse geçiş çalışır.
   4. İşler panelinde hiçbir iş gizlenmez; gizlemeyi kullanıcı kendisi yapacak.
   5. Program kapatılır. Önce ve sonra karşılaştırması yapılır: satır sayıları, `integrity_check`, `foreign_key_check`.
4. **Belgeler:** CALISMA_MANTIGI.md, README.md, M16 ve M18 (pencereler), docs/DEVIR/05 ve 02'nin güncel durum satırları.

TESLİM
docs/gorevler/GOREV-17/ altına şunlar konur:
- GOREV.md (work/gorevler/GOREV-17.md'nin kopyası),
- RAPOR.md,
- ekran görüntüleri.

RAPOR.md Türkçe ve sade olur. İçinde şunlar bulunur:
- her adımın sonucu;
- main ve etiketin konumu, CI ve test sayıları;
- pencere inceleme tablosu (önce ve sonra);
- Housing Atlas'tan örnek alınanlar;
- gerçek veritabanının önce ve sonrası;
- kullanıcının görevden sonra yapacakları (eklentiyi Chrome'da yeniden yükleme gibi);
- yöneticinin karar vermesi gereken konular.

Push etmeden önce `git status` ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.

Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-17 bitti, dal gorev-17-arayuz, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
