GÖREV-16 — Eklentinin düzeltilmesi, ABD dışı erişim engeli için kullanıcının ABD proxy'si ve GÖREV-15'in küçük düzeltmeleri

BAĞLAM
GÖREV-15 kabul edildi. Kullanıcı 11 Ekim'de "30A Studio Yardımcısı" eklentisini kendi Chrome'una kurdu, eşleştirdi ve "Sorunlu sitelerden birer sayfa dene"ye bastı. Sonuçlar `data/raw/eklenti/20261011/` altında:

| Site | Sonuç |
|---|---|
| Yerel deneme sayfası | tamam |
| order.online | tamam (200, gerçek sayfa); eklenti işe yarıyor |
| realjoy.com | site açıldı ama denenen ilan adresi 404 (ilan kalkmış) |
| cvs.com | 403; sayfa "CVS.com is not available to customers or patients who are located outside of the United States" diyor |
| publix.com | başlık "International \| Publix Super Markets"; "unable to service customers outside of the United States" |
| hcafloridahealthcare.com | `geo-blocked-site.dpxmedcity.net`'e yönlendi; eklenti o alan adına izni olmadığı için "hata" yazdı |
| winndixie.com | eklenti 14:34'ten beri "çalışıyor" gösterdi; program "Bağlı değil (Chrome kapalı olabilir)" dedi |

Yöneticinin bulguları:
- **ABD dışı engel:** CVS, Publix ve HCA, ve büyük ihtimalle Winn-Dixie de, ABD dışından gelen ziyaretçiye hizmet vermiyor. Bu siteler daha önce de bot koruması yüzünden değil, kullanıcı Türkiye'den bağlandığı için okunamıyormuş. Eklenti kullanıcının kendi bağlantısını kullandığı için bunu çözemez.
- **Yanlış doğrulama beklemesi:** `eklenti/logic.js`'deki `CHALLENGE_TITLES` "access denied" başlığını doğrulama sayıyor. Winn-Dixie büyük ihtimalle Akamai'nin "Access Denied" sayfasını gösterdi. Eklenti bunu kullanıcının geçebileceği bir doğrulama sandı ve 15 dakika bekledi. Oysa bu sayfayı kimse geçemez.
- **Sessiz kalan eklenti:** `runJob` bir iş sürerken programa hiç haber vermiyor; `/api/eklenti/sor` yalnız işler arasında çağrılıyor. Program 20 saniye sonra eklentiyi "bağlı değil" sayıyor ve ekranda "Chrome kapalı olabilir" diyor. Kullanıcı bunu haklı olarak "saçma" buldu.

Kullanıcının kararı: ABD dışından erişilemeyen siteler için kendi ABD proxy'si kullanılacak. Housing Atlas'ta da FEMA için aynı şey yapılıyor: FEMA proxy'si, parolası Kimlik Bilgisi Yöneticisi'nde, "Proxy'yi dene" düğmesi, okuma sırası doğrudan → proxy → arşiv. Yöneticinin sınırı şudur: proxy yalnız ABD dışı erişim engeli olan siteler için kullanılır. Bot korumasını, hız sınırını ya da yasağı aşmak için kullanılmaz (bu kural CLAUDE.md'deki tarayıcı kuralına işlenir).

Housing Atlas Stüdyo (`C:\Users\1\source\repos\housing-atlas`) ayrı bir projedir. Ona dokunulmaz; yalnız örnek olarak okunur. Önce `git fetch` ile son hâline bak. Bakılacak yerler:
- `atlas/secrets.py`: Kimlik Bilgisi Yöneticisi (`keyring`), değerin günlükte maskelenmesi.
- `atlas/config.py`: `PROXY_SCHEMES`, `proxy_url_error`.
- `atlas/app.py`: "Proxy'yi dene" (`/fema/proxy-test`; gizli değer dönmez).
- `atlas/isci/browser.py`: Chrome'u `--proxy-server` ile açma, proxy kimliğini CDP `Fetch` ile verme (`ProxyAuth`), SOCKS5 sınırı, "Proxy'yi dene" (`read_public_ip`).
- `atlas/analysis/hesap.py` ve `atlas/sources/documents`: doğrudan → proxy okuma sırası.

Kullanıcı bu görev için şu izinleri kendi mesajında açıkça veriyor:
- main'e alma ve etiket,
- gerçek veritabanını normal kullanımla güncelleme (önce tam yedek).

Bu görevde gerçek Claude çalıştırması yok. Gerçek sitelere istek yapılmaz. Kullanıcının proxy bilgileri Claude Code'a verilmez ve sorulmaz: kullanıcı görev bittikten sonra bunları Ayarlar'a kendisi girecek ve denemeyi kendisi yapacak.

KESİN SINIRLAR
- Housing Atlas klasöründe hiçbir dosya değiştirilmez.
- **Proxy'nin kapsamı:**
  - Proxy yalnız "bölge engelli" listesindeki alan adları için kullanılır. Öbür bütün istekler doğrudan gider.
  - Proxy bot korumasını, hız sınırını ya da yasağı aşmak için kullanılmaz. IP döndürme yoktur.
  - Hız kuralı aynı kalır: aynı sitede iki sayfa arası en az 8 saniye, bir anda tek sayfa.
  - Proxy üzerinden doğrulama sayfası çıkarsa onu yine kullanıcı geçer.
- **Gizli bilgiler:** Proxy parolası hiçbir dosyaya, günlüğe, komut satırına ya da API cevabına yazılmaz. Parola Windows Kimlik Bilgisi Yöneticisi'nde (`keyring`) durur; API yalnız "kayıtlı mı" bilgisini verir. Proxy adresi ve kullanıcı adı `ayarlar.json`'da durabilir. Ham kayıtlarda yalnız `proxy: true` yazar; adres yazmaz.
- **Kullanıcının Chrome'u:** Eklenti proxy kullanmaz ve kullanıcının Chrome'unun proxy ayarına dokunmaz; `proxy` izni eklenmez.
- **Testler:** Gerçek sitelere ve gerçek proxy'ye gidilmez. Testler yerel sahte proxy sunucusu ve yerel sayfalarla yapılır.
- **data/:** data/ yalnız Adım 6'da, CLAUDE.md kuralına göre değişir. Toplayıcı çalıştırılmaz.
- **main:** main'e yalnız Adım 1'deki fast-forward ile dokunulur ve yalnız Adım 1'deki etiket konur.

==================================================
ADIM 1 — v0.17.0'ı main'e al
==================================================
1. **Program açık mı:** Program 8830–8849'da açıksa kapanmasını bekle. 30 dakikada kapanmazsa yalnız kodu değiştir; Adım 6'daki gerçek veri işini program kapalıyken yap ve bunu rapora yaz. Çalışan bir eklenti işi varsa bitmesini bekle.
2. **Kullanıcının değişiklikleri:** Çalışma ağacında kullanıcının Ayarlar'dan yaptığı talimat, ton ya da uyarı ifadesi değişikliği varsa kaybetme. Bunları yeni dalda ilk commit olarak ekle (CLAUDE.md kuralı).
3. **main ve etiket:**
   - origin/gorev-15-video-metni'nin son commit'i (`6cfab84`) için CI sonucunu kontrol et.
   - main'i bu commit'e fast-forward ile getir ve push et.
   - "v0.17.0" açıklamalı etiketini koy ve push et. Etiket mesajı: "v0.17.0 — video metni: yazım zinciri, seçilebilir tonlar ve ton yönetimi, karşılaştırma ve program denetimi".
   - main ve etiketin CI sonucunu rapora ekle.
4. **Yeni dal:** Güncel main'den "gorev-16-eklenti-proxy" dalını aç.

==================================================
ADIM 2 — Eklentinin düzeltilmesi
==================================================
2a. **İş sürerken canlılık.** Eklenti bir iş sürerken de programa birkaç saniyede bir (en çok 5 sn arayla) canlılık ve durum bildirir. Durum şunlardan biridir: sayfa açılıyor, sayfa okunuyor, doğrulama bekleniyor (kalan süreyle), bekleme (hız kuralı).
- Program eklentiden gelen her çağrıyı "görüldü" sayar.
- Ayarlar → Tarayıcı eklentisi ve İşler paneli, iş sürerken şunu yazar: "Eklenti çalışıyor: <site> · <durum>".
- "Bağlı değil (Chrome kapalı olabilir)" yalnız eklentiden gerçekten haber alınamıyorsa yazılır. Bunun için iş sürerken eşik 60 sn, iş yokken 20 sn'dir.
- Eklenti penceresindeki "Son iş" satırı, iş takılı kalmışsa (en son ne zaman ilerlediğiyle) bunu söyler.

2b. **Sayfa türleri.** Kullanıcının geçebileceği doğrulama ile kimsenin geçemeyeceği engel ayrılır:
- **Doğrulama** (kullanıcı geçer; 15 dk bekleme kalır): Cloudflare "Just a moment", "Verify you are human", "Press & Hold", px-captcha ve benzerleri. Bunlar mevcut `CHALLENGE` işaretleridir. "access denied" başlığı bu listeden çıkar.
- **Erişim reddedildi** (beklenmez, hemen atlanır): Akamai'nin "Access Denied" / "You don't have permission to access" sayfası, "Sorry, you have been blocked", "You are unable to access", 403 ile gelen boş ya da engel sayfaları.
- **Bölge engeli** (beklenmez, hemen atlanır; Adım 3'e göre proxy'yle denenir): "outside of the United States", "outside the United States", "outside the U.S.", "not available in your country", "not available in your region", "unable to service customers outside", sayfa başlığı "International | Publix" ve adresi "geo-block" içeren yönlendirmeler.
- İşaretler tek bir Python kaynağında durur ve `eklenti/logic.js`'teki kopyası bir testle denetlenir; bugünkü `CHALLENGE`/`BLOCKED` düzeni böyle çalışıyor.
- Bu ayrım programın kendi tarayıcısında da (`studio/sources/browser_verification.py` ve onu kullanan toplayıcılar) uygulanır: "erişim reddedildi" ve "bölge engeli" kullanıcı doğrulamasına gönderilmez.
- Bugünkü gerçek ham kayıtlar test fikstürü olarak kullanılabilir. CVS ve Publix sayfalarının ilgili kısımları kısaltılarak alınır.

2c. **Başka siteye yönlenme.** Sayfa izin verilmemiş başka bir alan adına yönlenirse (HCA'da olduğu gibi), eklenti sekmenin adresini okur ve sonucu şöyle verir: "başka siteye yönlendi: <alan adı>". Adres "geo-block" içeriyorsa sonuç "bölge engeli" olur. Bugünkü gibi Chrome'un izin hata metni sonuç olarak yazılmaz.

2d. **"Bu sayfayı atla".** Doğrulama beklenirken eklenti penceresinde ve İşler panelinde "Bu sayfayı atla" düğmesi olur. Basılınca o sayfa "kullanıcı atladı" diye kaydedilir ve iş sürer.

2e. **Deneme listesi.** `EXTENSION_TRIAL_SITES`'ta realjoy.com için artık bulunmayan ilan adresi yerine kalıcı bir sayfa konur: 30A bölgesinin ilan listesi sayfası. Adresi bugünkü ham kaydın (`113307-b7957c1e.html`) bağlantılarından bul. Deneme sonuç tablosunda her sitenin yanında türü yazar: tamam, doğrulama, erişim reddedildi, bölge engeli, başka siteye yönlendi. Bölge engelli siteler, proxy tanımlıysa proxy'yle denenir (Adım 3).

==================================================
ADIM 3 — ABD dışı erişim engeli için kullanıcının ABD proxy'si
==================================================
3a. **Ayarlar → "ABD proxy'si (bölge engeli için)".** Bu bölümde şunlar bulunur:
- Proxy adresi (şema://sunucu:port; şemalar Housing Atlas'taki gibi; doğrulama `proxy_url_error`'dan taşınır), kullanıcı adı ve parola.
- Parola Kimlik Bilgisi Yöneticisi'nde durur; hizmet adı `30AStudio`. Kayıtlıysa alan "kayıtlı" gösterir ve değeri göstermez. "Parolayı sil" düğmesi vardır.
- `keyring` bağımlılığa eklenir. Housing Atlas'taki gibi, okunan ya da kaydedilen gizli değerler günlük maskeleme listesine girer.
- **"Proxy'yi dene":** Proxy üzerinden herkese açık bir IP servisine gidilir. Ekranda çıkış adresi ve ülkesi yazar. Ülke ABD değilse uyarı çıkar: "Proxy'nin çıkış adresi ABD'de görünmüyor".
- Chrome, kullanıcı adı ve parola isteyen SOCKS5 proxy'yi desteklemez (Housing Atlas notu). Böyle bir proxy girilirse ekran bunu söyler: programın kendi tarayıcısı bu proxy'yle kullanılamaz, yalnız doğrudan istekler kullanılabilir.

3b. **Bölge engelli alan adları.**
- Program bir alan adında bölge engeli görünce o alan adını listeye kendisi ekler: tarih ve engel sayfasının başlığıyla, `browser_hosts`'ta ya da yeni bir alanda.
- Kullanıcı Ayarlar'dan listeye alan adı ekleyebilir ve listeden çıkarabilir.
- Başlangıçta bugünkü ham kayıtlardan cvs.com, publix.com ve hcafloridahealthcare.com eklenir. winndixie.com ve thefreshmarket.com, kullanıcının denemesinin ham kaydı varsa ona göre eklenir; ham kayıt yoksa eklenmez.

3c. **Okuma sırası.** Listedeki bir alan adı için sıra şudur:
1. Proxy üzerinden doğrudan istek.
2. Sayfa JavaScript'le çiziliyorsa ya da istek engellenirse programın kendi tarayıcısı, proxy'yle.
3. O da olmazsa atla ve kaydet: "bölge engeli: proxy'yle de okunamadı".

Bu alan adları için eklenti kullanılmaz, çünkü kullanıcının bağlantısıyla zaten okunamazlar.

Programın kendi tarayıcısında proxy yalnız listedeki alan adlarına uygulanır, öbür siteler doğrudan gider. Yöntemi sen seç: PAC betiği (`--proxy-pac-url` ile `data:` adresi) ya da yalnız bu iş için ayrı bir profil ve süreç. Proxy kimliği komut satırına yazılmaz; Housing Atlas'taki gibi CDP `Fetch` ile verilir.

Ham kayıtta `yontem` alanı `proxy` ya da `tarayici+proxy` olur ve `proxy: true` yazar.

3d. **Proxy yoksa.** Proxy tanımlı değilse bölge engelli sayfa hemen atlanır ve şu kaydedilir: "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)". İş paneli de aynı bilgiyi verir.

3e. **Belgeler.** CLAUDE.md'deki tarayıcı kuralına şu eklenir: proxy yalnız ABD dışı erişim engeli için ve kullanıcının kendi proxy'siyle kullanılır; bot korumasını, hız sınırını ya da yasağı aşmak için kullanılmaz; IP döndürme yoktur. `docs/M16-TARAYICI-EKLENTISI.md` güncellenir ya da yeni bir M belgesi yazılır.

==================================================
ADIM 4 — GÖREV-15'in küçük düzeltmeleri
==================================================
1. **Seçilmiş çalışma:** Bir sürüm "Bu tonla devam et" ile seçilince, o sürümün çalışması Video metni ekranındaki listede "seçildi: <ton adı>" diye görünür.
2. **Kullanım hesabı:**
   - Sürümün kullanımı yalnız o tonun oturumlarını sayar.
   - Planın ve eleştirinin oturumları (tonsuz) çalışmanın "plan" satırında bir kez gösterilir.
   - Karşılaştırma ekranında sütun başı tonun kullanımını, ekranın üstü planın kullanımını yazar.
   - "Bu tonla da yaz" sürümü yeniden yapılmamış planın bedelini göstermez.
3. **"I" uyarısı:** "I" uyarısı "I-10", "I-65" gibi yol adlarında eşleşmez. Bunun için "I" ardından tire ve rakam gelirse hariç tutulur. Testi yazılır.

==================================================
ADIM 5 — Testler
==================================================
En az şunlar sınanır:
- **Eklenti:**
  - iş sürerken canlılık;
  - ekran metinleri: "Eklenti çalışıyor", "Bağlı değil" eşikleri;
  - üç sayfa türünün ayrımı: Python ve JS işaretlerinin aynı olması, bugünkü ham kayıtlardan fikstürler;
  - erişim reddedildi ve bölge engelinde beklenmemesi;
  - başka siteye yönlenme;
  - "Bu sayfayı atla";
  - yeni deneme listesi.
- **Proxy:**
  - adres doğrulaması;
  - parolanın Kimlik Bilgisi Yöneticisi'nde durması (testte sahte `keyring` arka ucu) ve hiçbir dosyada, günlükte ya da API cevabında görünmemesi;
  - "Proxy'yi dene": yerel sahte proxy ve sahte IP servisi; ülke uyarısı;
  - bölge engelli listeye kendiliğinden ekleme ve Ayarlar'dan ekleme ya da çıkarma;
  - okuma sırası;
  - proxy yokken atlama ve kayıt;
  - programın kendi tarayıcısında proxy'nin yalnız listedeki alan adlarına uygulanması (PAC içeriği ya da süreç ayrımı);
  - SOCKS5 kimlik sınırının ekranda söylenmesi;
  - ham kayıtta adres olmaması.
- **Adım 4'ün üç düzeltmesi.**
- **Geçiş:** Şema değişirse 17 → 18.

==================================================
ADIM 6 — Gerçek ortam ve teslim
==================================================
1. **Geçici klasörde deneme:** Gerçek verinin kopyası kullanılır. Eklenti Playwright'in Chromium'unda geçici profille, yalnız yerel sayfalarla denenir. Şu yerel sayfalar kurulur: doğrulama, erişim reddedildi, bölge engeli ve başka siteye yönlenme. Ayrıca yerel sahte proxy'yle "Proxy'yi dene" ve bölge engelli bir yerel sayfanın proxy üzerinden okunması denenir. Ekran görüntüleri alınır.
2. **Geçiş denemesi:** Şema değiştiyse kopyada geçiş denenir. Satır sayıları önce ve sonra karşılaştırılır; `integrity_check` ve `foreign_key_check` çalıştırılır.
3. **Gerçek veritabanı** (CLAUDE.md kuralına göre):
   1. data/ tam yedeği alınır.
   2. Program masaüstü kısayoluyla açılır.
   3. Ayarlar'da proxy bölümü ve bölge engelli liste görünür (cvs.com, publix.com, hcafloridahealthcare.com).
   4. Proxy girilmez ve gerçek siteye gidilmez.
   5. Program kapatılır. Önce ve sonra karşılaştırması yapılır.
4. **Belgeler:** CALISMA_MANTIGI.md, README.md (proxy'nin nereye girildiği ve ne için kullanıldığı), docs/DEVIR/05 ve 02, M16 (ya da yeni M belgesi), M17 (Adım 4), CLAUDE.md. Tam test takımı yerelde art arda en az 3 kez geçmeli.

TESLİM
docs/gorevler/GOREV-16/ altına şunlar konur:
- GOREV.md (work/gorevler/GOREV-16.md'nin kopyası) ve RAPOR.md,
- ekran görüntüleri:
  - Ayarlar → ABD proxy'si: boş hâli, kayıtlı parola, "Proxy'yi dene" sonucu (yerel sahte proxy);
  - bölge engelli liste;
  - Ayarlar → Tarayıcı eklentisi: iş sürerken "Eklenti çalışıyor";
  - İşler panelinde doğrulama beklemesi ve "Bu sayfayı atla";
  - deneme sonuç tablosunda sayfa türleri;
  - Video metni listesinde "seçildi" ve karşılaştırmada plan kullanımı.

RAPOR.md Türkçe ve sade olur. İçinde şunlar bulunur:
- her adımın sonucu;
- main ve etiketin konumu, CI sonuçları, test sayıları;
- Housing Atlas'tan taşınanlar;
- gizli bilginin nerede durduğu ve nerede durmadığı (tablo);
- gerçek veritabanının önce ve sonrası;
- kullanıcının görevden sonra yapacakları (proxy'yi girme, deneme, eklentiyi yeniden yükleme);
- beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.

Push etmeden önce `git status` ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.

Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-16 bitti, dal gorev-16-eklenti-proxy, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
