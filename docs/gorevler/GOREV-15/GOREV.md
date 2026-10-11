GÖREV-15 — Video metni: yazım zinciri, seçilebilir anlatıcı tonları ve ton yönetimi, tonların karşılaştırılması ve program denetimi

BAĞLAM
GÖREV-14 kabul edildi. Program masaüstü programı gibi çalışıyor, iş akışı paneli, Claude kullanım paneli, talimat düzenleyici, kullanıcının kendi başlığı, içerik planından video paketi ve "30A Studio Yardımcısı" eklentisi hazır. Bu görevde iş akışının 4. adımı olan **Video metni** kurulur: seçilen başlık ve onun video paketiyle, program arka planda Claude'u adım adım çağırarak İngilizce video metnini yazdırır ve kullanıcıya cümle cümle eşleşen Türkçe çevirisini verir.

Kullanıcının bu görev için istekleri:
- **Metin parça parça yazılır.** Video metni tek bir Claude oturumuna yazdırılmaz; plan, bölümler, birleştirme, giriş ve kapanış, son okuma ve çeviri ayrı oturumlardır. Bu düzen Housing Atlas'ın makale sisteminden alındı ve kullanıcı onayladı.
- **Ton seçilebilir.** Birkaç farklı anlatıcı tonu olur. Kullanıcı ekrandan bir ya da birkaç ton seçer ve metin seçilen her ton için ayrı yazılır, böylece tonlar karşılaştırılabilir.
- **Ton dışarıdan yönetilir.** Kullanıcı programın içinden yeni bir ton ekler: bir ad verir, tonun metnini yazar ve kaydeder. Mevcut tonları düzenler ya da siler. Bunun için görev gerekmez.
- **Kurallar az olur.** Claude'a giden metinlerde çok fazla kural ve örnek cümle olmaz, çünkü bunlar metni kalıba sokar. Yasak ifadeleri ve rakamları program, metin yazıldıktan sonra denetler.
- **Kontrol kullanıcıya bırakılmaz.** Doğruluk denetimini program ve Claude oturumları yapar. Kullanıcı en iyi hâli seçer.

Yöneticinin tasarım belgeleri `work/yonetim/` klasöründe:
- `30A_YAZIM_ZINCIRI.md`: zincirin tasarımı,
- `30A_SES_VE_TONLAR.md`: ortak ses, tonlar ve karşılaştırma,
- `30A_HALKA_TALIMATLARI.md`: talimatlar, çalışma klasöründeki dosyalar ve program denetimi kuralları.
Bu görev metni o belgelerle çelişirse bu görev metni geçerlidir. Talimat metinleri bu görevin eklerindedir ve aynen kullanılır.

Housing Atlas Stüdyo (`C:\Users\1\source\repos\housing-atlas`) ayrı bir projedir. Ona dokunulmaz; yalnız örnek olarak okunur ve orada hiçbir dosya değiştirilmez. Önce `git fetch` ile son hâline bak; 11 Ekim'de makale sisteminin ilk paketi (MS1) eklendi. Bu görevde bakılacak yerler:
- Makale sistemi: `docs/TASARIM.md` Bölüm 21; `atlas/article/` (özellikle `split.py` cümle bölme, `digits.py` iki dilde rakam denetimi, `store.py` ve `history.py` sürümler); `atlas/ai/schemas/makale.schema.json`; `talimatlar/makale_ceviri.md`.
- Paralel oturumlar, geçici hatalar ve kullanım sınırında bekleme: `atlas/kesif/engine.py` (baştaki açıklama) ve `atlas/kesif/limits.py`.
- Zincirin planı: TASARIM 21.4.

Bu büyük bir görevdir ve gece boyunca sürebilir. Adımları sırayla yap; her adımın sonunda testler geçmeli.

Kullanıcı bu görev için şu izinleri kendi mesajında açıkça veriyor:
- main'e alma ve etiket,
- gerçek veritabanını normal kullanımla güncelleme (önce tam yedek).
Bu görevde gerçek Claude çalıştırması yapılmaz. Henüz seçilmiş bir başlık ve video kaydı yok; ilk gerçek metni kullanıcı programdan kendisi yazdıracak. Bilgisayarda zamanlanmış görev oluşturulmaz.

KESİN SINIRLAR
- Housing Atlas klasöründe hiçbir dosya değiştirilmez.
- data/ yalnız Adım 10'da, CLAUDE.md kuralına göre değişir: önce tam yedek alınır, sonra uygulama normal kullanılır. Toplayıcı çalıştırılmaz.
- main'e yalnız Adım 1'deki fast-forward ile dokunulur ve yalnız Adım 1'deki etiket konur.
- Gerçek Claude çağrılmaz; testler ve denemeler sahte claude programıyla yapılır.
- Claude Code başlık seçmez ve gerçek veride video kaydı oluşturmaz. Geçici klasördeki denemeler bunun dışındadır.
- Talimat ve ton metinleri yalnız bu görevin eklerinde verildiği gibi yazılır; talimat içeriği uydurulmaz.
- Hiçbir kullanıcı verisi silinmez. Silinen ton arşive gider, metin sürümleri ve Claude çalışmaları saklanır.
- Eklentiyle gerçek sitelerden veri çekilmez.

==================================================
ADIM 1 — v0.16.0'ı main'e al; kullanıcının talimat değişiklikleri; küçük düzeltme
==================================================
1a. **Talimat değişiklikleri:** Çalışma ağacında `studio/destinations/thirty_a_claude/` altında commit edilmemiş değişiklik varsa (kullanıcı Ayarlar → Talimatlar'dan düzenlemiş olabilir), bunları kaybetme. Bir kenara al ve 1c'deki yeni dalda ilk commit olarak ekle. Mesaj: "talimat: kullanıcının Ayarlar'dan yaptığı talimat değişiklikleri". Değişiklik yoksa bunu rapora yaz.

1b. **main ve etiket:**
- origin/gorev-14-masaustu-eklenti'nin son commit'i (984ca72) için GitHub Actions sonucunu kontrol et; başarısızsa önce düzelt.
- main'i bu commit'e fast-forward ile getir ve push et.
- "v0.16.0" açıklamalı etiketini koy ve push et. Etiket mesajı: "v0.16.0 — masaüstü programı, iş akışı paneli, Claude kullanımı ve talimat düzenleyici, kullanıcının kendi başlığı, içerik planından video paketi, tarayıcı eklentisi".
- main ve etiketin CI sonucunu rapora ekle.

1c. **Yeni dal:** Güncel main'den "gorev-15-video-metni" dalını aç.

1d. **Küçük düzeltme (GÖREV-14 raporu, karar konusu 1):** Aday üretmeyen bir başlık değerlendirmesi ("veriyle dolmuyor"), iş akışında "onay bekliyor" sayılmasın.
- "Konu ve başlık" adımının sayımı bu çalışmayı dışarıda bırakır.
- Videolar ekranında bu çalışma "Değerlendirildi: veriyle dolmuyor" diye bilgi olarak görünür.
- Kullanıcı yine istediği zaman "Reddet" ile kapatabilir.
- Testi yazılır.

==================================================
ADIM 2 — Talimat dosyaları ve ses
==================================================
Şu dosyaları `studio/destinations/thirty_a_claude/` altına eklerdeki metinlerle **aynen** yaz:
- `ses_ortak.md` (Ek A),
- `tonlar/arastirmaci_dost.md`, `tonlar/belgesel.md`, `tonlar/pratik_planlayici.md`, `tonlar/vlogger.md`, `tonlar/hikaye_anlaticisi.md` (Ek B–F),
- `metin_plan.md`, `metin_plan_elestiri.md`, `metin_bolum.md`, `metin_birlestirme.md`, `metin_giris_kapanis.md`, `metin_son_okuma.md`, `metin_ceviri.md` (Ek G–M).

**Ton dosyasının biçimi:** İlk satır `# Ton: <Ad>`, bir boş satır, sonra tonun metni gelir. Programda tonun adı bu başlıktan okunur.

**Birleşik talimat:** Her adımda Claude'a giden birleşik talimat şu parçaların bu sırayla birleşimidir. Hangi adıma ses ve ton verildiği Ek N'deki tabloda yazar.
1. `ortak.md`,
2. sesin verildiği adımlarda `ses_ortak.md` ve seçilen tonun dosyası,
3. adımın kendi dosyası,
4. şema.

**Çalışma kaydı:** Çalışma kaydı, kullanılan ton dosyasının adını, tonun adını ve SHA-256'sını da tutar. Birleşik talimatın kendisi zaten `talimat.md` olarak çalışma klasöründe saklanıyor; bu, ton metninin o anki kopyası yerine geçer.

**Talimat düzenleyici:** Ayarlar → Talimatlar listesine şunlar eklenir:
- `ses_ortak.md`, başlığı "Anlatıcının sesi (bütün tonlarda aynı)",
- yedi `metin_*.md` dosyası, adımların Türkçe adlarıyla.
Tonlar bu listede değil, Adım 3'teki kendi ekranlarında yönetilir.

==================================================
ADIM 3 — Ton yönetimi (Ayarlar → Tonlar)
==================================================
Kullanıcı tonları görev gerekmeden, programın içinden yönetir. Talimat düzenleyicinin ilkeleri aynen geçerlidir:
- **Tek kaynak:** Tek kaynak repodaki dosyadır (`studio/destinations/thirty_a_claude/tonlar/`).
- **Değişiklik denetimi:** Dosya kullanıcı açtıktan sonra diskte değiştiyse kayıt reddedilir.
- **Sürüm geçmişi:** Her kayıttan önce önceki hâl veri klasöründe saklanır ve sürümlere geri dönülebilir.

Ayarlar'a "Tonlar" bölümü eklenir. Bölümde şunlar bulunur:
- **Liste:** Tonun adı, metninin ilk satırı, son değişiklik zamanı, varsayılan olup olmadığı ve kaç metin sürümünde kullanıldığı.
- **Yeni ton:** İki alan vardır: "Tonun adı" ve "Tonun metni". Kullanıcı Markdown başlığı yazmaz; program dosyayı `# Ton: <Ad>` başlığıyla kendisi yazar.
  - Ad boş olamaz, en çok 40 karakterdir ve başka bir tonun adıyla aynı olamaz.
  - Dosya adı, addan Türkçe harfler sadeleştirilerek kurulur: ı→i, ş→s, ğ→g, ü→u, ö→o, ç→c; küçük harf; harf ve rakam dışındaki karakterler `_` olur. Ad zaten varsa sonuna sayı eklenir.
  - Metin boş olamaz ve en çok 6.000 karakterdir.
  - Metin 1.200 karakterden uzunsa kayıt yapılır ama ekranda nazik bir not çıkar: "Ton metni uzun. Kısa ve niyet anlatan metinler genellikle daha iyi sonuç verir."
- **Düzenle:** Ad ve metin değiştirilebilir. Ad değişince dosya adı değişmez; yalnız başlık satırı değişir. Böylece eski sürümler ve kayıtlar aynı tonu göstermeye devam eder.
- **Sil:** Onay sorulur ("Bu ton arşive taşınacak; istediğiniz zaman geri alabilirsiniz."). Dosya `<data>/claude/ton_arsivi/<dosya adı>-<zaman>.md` içine taşınır. Hiçbir şey silinmez. Silinen tonla yazılmış metin sürümleri yerinde kalır ve ton adlarıyla görünmeye devam eder.
- **Arşiv:** Arşivdeki tonlar ayrı bir listede durur ve "Geri al" ile tonlar klasörüne döner. Aynı dosya adı varsa sonuna sayı eklenir.
- **Varsayılan ton:** Bir ton varsayılan yapılır; ayar `ayarlar.json`'da tutulur. Başlangıçta varsayılan "Araştırmacı dost"tur. Varsayılan ton silinirse listedeki ilk ton varsayılan olur ve ekranda söylenir. En az bir ton kalmalıdır; son ton silinemez.
- **Sürümler:** Talimat düzenleyicideki gibi sürüm listesi ve "Bu sürüme dön".

Kullanıcının eklediği ya da değiştirdiği ton dosyaları repodaki klasöre yazılır ve git'te commit edilmemiş değişiklik olarak görünür. Bu bilerek böyledir; belgelerde de yazılsın. Her görevin başında Claude Code bunları Adım 1a'daki gibi commit eder.

Video metni ekranında (Adım 8) "Tonları yönet" bağlantısı bu bölümü açar.

==================================================
ADIM 4 — Yazım zincirinin adımları ve şemaları
==================================================
`studio/ai/steps.py` çatısıyla yedi yeni Claude adımı kaydedilir. Her adımın bir talimat dosyası, `studio/ai/schemas/` altında bir JSON şeması, girdi hazırlayıcısı, görev metni, çıktı denetimi ve Markdown yazıcısı olur. Araçlar başlık adımlarındaki gibidir: yalnız çalışma klasöründe okuma ve tek çıktı dosyasını yazma.

| Anahtar | Türkçe adı | Talimat | Çıktı |
|---|---|---|---|
| `metin_plan` | Video metni · plan | `metin_plan.md` | `plan.json` |
| `metin_plan_elestiri` | Video metni · plan eleştirisi | `metin_plan_elestiri.md` | `plan_elestirisi.json` |
| `metin_bolum` | Video metni · bölüm | `metin_bolum.md` | `bolum.json` |
| `metin_birlestirme` | Video metni · birleştirme | `metin_birlestirme.md` | `birlestirme.json` |
| `metin_giris_kapanis` | Video metni · giriş ve kapanış | `metin_giris_kapanis.md` | `giris_kapanis.json` |
| `metin_son_okuma` | Video metni · son okuma | `metin_son_okuma.md` | `son_okuma.json` |
| `metin_ceviri` | Video metni · çeviri | `metin_ceviri.md` | `ceviri.json` |

**Şemalarda bulunması gerekenler.** Ayrıntıyı sen kurarsın; şu alanlar olmalı:
- **plan:**
  - Bölümler. Her bölümde: numara, iç adı, tek fikri, en çarpıcı anı, kanıt kimlikleri, kelime bütçesi, `acilis_bicimi` ve açılış notu. `acilis_bicimi` şu değerlerden biridir: `rakam`, `sahne`, `soru`, `gecmis`, `karsilastirma`, `diger`.
  - Kavramlar: hangi kavram, hangi bölümde açıklanacak.
  - Yeniden kancalar: hangi bölümden sonra geleceği ve ne üzerine kurulacağı.
  - Vaat kontrolü: karşılanan vaatler ve bölümleri, karşılanamayan vaatler.
  - Notlar.
- **plan_elestirisi:** Notlar ve `yeniden_yap` (doğru/yanlış).
- **bolum:**
  - Bölüm numarası.
  - Paragraflar: düz metin; bilgi taşıyan cümlenin sonunda `[K0123]` biçiminde kanıt işareti bulunur.
  - Yazıcının notu (isteğe bağlı).
- **birlestirme:**
  - Geçişler: hangi iki bölüm arasında olduğu ve metni.
  - Yeniden kancalar: hangi bölümden sonra geldiği ve metni.
  - Birleşme yerlerindeki tekrar ve çelişki notları.
- **giris_kapanis:** Giriş paragrafları, kapanış paragrafları ve önerilen video (yoksa boş).
- **son_okuma:** Düzeltmeler: cümle numarası, yeni cümle ve gerekçe.
- **ceviri:**
  - Her cümle numarası için tek Türkçe cümle.
  - Terimler: İngilizcesi, Türkçesi ve açıklaması.
  - Çevirmen uyarıları: cümle numarası ve metni.
  Housing Atlas'taki `makale_ceviri` ile aynı biçim kullanılır.

**Girdi dosyaları.** Hangi adıma hangi dosyanın konduğu Ek N'deki tabloda yazar.
- **`baslik_analizi.md`:** Video kaydındaki seçilmiş adaydan yazılır. İçinde başlık, izleyicinin sorusu, kanca, neden önerildiği, içerik planı ve eksik veri bulunur.

  **Önemli:** Adayın kanıt kimlikleri kaynak paketlerin kimlikleridir (`veri_ozeti_30a.md` ve `veri_ozeti_mahalle.md`). Video paketi ise satırları yeniden numaralandırır ve her satırın eski kimliğini saklar. `baslik_analizi.md` yazılırken bütün kimlikler video paketinin kimliklerine çevrilir; böylece Claude tek bir kimlik dizisi görür. Video paketinde karşılığı olmayan bir kimlik "(pakette yok)" diye yazılır.
- **`paket_ozeti.md` ve `sayilar.csv`:** Video paketinin yazar özeti ve sayı listesi. Bunlar GÖREV-14'teki içerik planından paketin dosyalarıdır.
- **`kanal_plani.md`:** Başlık adımındaki aynı dosya.
- **`bolum.md`:** Bölüm yazıcısının kendi dosyası. İçinde şunlar bulunur:
  - planın o bölüme ait kısmı,
  - o bölüme verilen kavram açıklamaları,
  - bölümün kanıt satırları ve ait oldukları blokların tamamı, kullanım notlarıyla,
  - önceki ve sonraki bölümün tek fikri, birer cümle olarak.
- **`bolumler.md`:** Bölümler sırasıyla, kanıt işaretleriyle.
- **`metin.md`:** Birleşmiş metin. Giriş ve kapanış adımına düz metin olarak verilir; son okuyucuya numaralı cümlelerle verilir.
- **`yayinlanan_videolar.md`:** Henüz yayın kaydı olmadığı için "Henüz yayınlanmış video yok." yazar. Yayın adımı kurulunca dolacak; alanı şimdiden ayır.
- **Çevirmen:** Housing Atlas'taki gibi numaralı İngilizce cümleleri alır. Metin uzunsa parçalara bölünür; parçaları ve terim birleştirmeyi Housing Atlas'tan al.

**Görev metinleri.** Görev metinleri kısa olur ve talimatı tekrar etmez. Düzeltme ya da yeniden yapma turunda görev metnine iki şey eklenir: önceki çıktı ve dönüş sebebi. Dönüş sebebi programın denetim bulguları ya da eleştirmenin notlarıdır.

==================================================
ADIM 5 — Zincirin işleyişi
==================================================
"Metni yaz" düğmesi bir **metin çalışması** açar. Metin çalışması bir videoya aittir ve İşler panelinde tek bir iş olarak görünür.

**Sıra:**
1. **Tazelik:** Videonun paketi yoksa ya da verinin son çekiminden eskiyse, paket önce kendiliğinden yeniden üretilir ve bu, iş günlüğüne yazılır.
2. **Plan:**
   1. Planlayıcı çalışır.
   2. Program planı denetler (Ek O, "Uzunluk ve plan").
      - Planda pakette olmayan bir kanıt kimliği varsa plan bir kez planlayıcıya döner; yine varsa çalışma hata verir.
      - Öbür bulgular uyarı olarak kaydedilir.
   3. Plan eleştirmeni çalışır. Eleştirmen `yeniden_yap` derse plan, notlarla birlikte bir kez daha planlayıcıya döner. İkinci plan yeniden denetlenir ama yeniden eleştirilmez.
   4. Plan kesinleşir ve çalışmada saklanır.
   5. Ayarlar'da "Plandan sonra dur" açıksa (varsayılan kapalı) çalışma burada durur. Kullanıcı planı görür ve "Devam" ile sürdürür.
3. **Her ton için ayrı metin:** Seçilen her ton için sırayla şu adımlar çalışır:
   1. Bölüm yazıcıları aynı anda çalışır; aynı anda en çok "Claude oturumu sınırı" kadar oturum açılır.
   2. Birleştirici.
   3. Giriş ve kapanış.
   4. Program metni birleştirir ve cümleleri numaralar (Adım 6).
   5. Son okuyucu.
   6. Program düzeltmeleri uygular.
   7. Program denetimi (Adım 7).
   8. Çevirmen.
   9. Program iki dilde rakamları denetler.
   10. Sürüm kaydedilir.
   Bir tonun metni bitince sıradaki tona geçilir.
4. Bütün tonlar bitince çalışma "karşılaştırma bekliyor" olur.

**Aynı plan, farklı ses:** Plan bir kez yapılır ve bütün tonlar aynı planı kullanır. "Bu tonla da yaz" düğmesi, var olan bir çalışmanın planıyla yalnız bir ton daha yazdırır. "Planı yeniden yap" ise yeni bir metin çalışması açar; eski çalışma ve sürümleri saklanır.

**Oturum sınırı:** Ayarlar → Claude'a "Aynı anda en çok Claude oturumu" ayarı eklenir (1–6, varsayılan 3). Metin çalışması sürerken başka bir Claude çalışması (başlık önerisi gibi) başlatılmaz. Kullanıcıya "Bir video metni çalışması sürüyor; bitmesini bekleyin." denir. Mevcut tek işçili yapı, bu çalışmanın kendi içinde paralel oturum açabileceği biçimde genişletilir.

**Geçersiz cevap:** Şemaya uymayan ya da denetimden geçmeyen çıktı, hatalarıyla birlikte bir kez yeniden istenir. İkinci denemede de olmazsa o adım hata verir. Çalışma "duraklatıldı" olur ve "Devam" ile o adımdan yeniden başlar.

**Geçici hatalar:** Zaman aşımı, ağ hatası, Claude'un 5xx ya da 529 hatası ve sınır bilgisi taşımayan 429 geçici hatadır. Adım hata sayılmaz; 1, 5 ve 15 dakika beklenerek yeniden denenir. Yine olmazsa çalışma duraklar ve "Devam" bekler. Yöntem Housing Atlas'ın `atlas/kesif/engine.py`'sindeki gibidir, ama daha sadedir.

**Kullanım sınırı:** Ayarlar → Claude'a iki eşik eklenir: 5 saatlik pencere (varsayılan %90) ve haftalık pencere (varsayılan %95).
- **Bekleme ne zaman başlar:** Her oturumdan önce son kullanım ölçümüne bakılır. Eşik geçilmişse ya da Claude "kullanım sınırına ulaşıldı" derse yeni oturum açılmaz. Çalışan oturumlar biter ve çalışma bekler.
- **Ne kadar beklenir:** Sıfırlanma anı biliniyorsa ve gelecekteyse o andan 2 dakika sonrasına kadar beklenir. Değilse 5, 10, 20, 40 ve 60 dakika beklenir.
- **Ekranda ne görünür:** İşler panelinde şu yazar: "Claude kullanım sınırı: <saat>'te kendiliğinden sürecek." Süre gelince çalışma kendiliğinden sürer.
- **Kullanıcı ne yapabilir:** "Devam" beklemeden yeniden dener.
- Yöntem `atlas/kesif/limits.py`'deki gibidir.

**Sürdürme:**
- **Hiçbir şey kaybolmaz:** Biten her adımın çıktısı hemen saklanır. Yarım kalan adım sonuç yazmaz.
- **Program kapanırsa:** Program kapanırsa ya da kullanıcı "Durdur"a basarsa, çalışan oturumlar kesilir ve çalışma "duraklatıldı" olur. Program yeniden açılınca çalışma "yarıda kaldı" diye görünür. "Devam", biten adımları yeniden çalıştırmadan yalnız kalanları çalıştırır.
- **Kapanma bekçisi:** Kapanma bekçisi metin çalışmasını da bir iş sayar ve bitmesini bekler.

**İlerleme:** İlerleme çubuğu aşamalardan ilerler. Plan yaklaşık %15'tir; kalan pay tonlara bölünür, tonun içinde de adımlara. Yanında iki şey yazar:
- aşamanın metni; örneğin "Araştırmacı dost (1/2 ton) · bölümler 4/6 bitti",
- geçen süre ve tahmini kalan süre (aynı adımın önceki çalışmalarının ortanca süresinden).

**Çalışma klasörü:** Her Claude oturumunun klasörü mevcut düzendedir (`<data>/claude/<video kimliği>/<adım>/<çalışma kimliği>/`). Metin çalışmasının kendi kaydı ve sürümleri Adım 6'dadır.

==================================================
ADIM 6 — Metin verisi, cümle numaraları, çeviri ve sürümler
==================================================
**Veri biçimi.** Veri biçimini Housing Atlas'ın `makale.json` biçimine (TASARIM 21.2, `atlas/ai/schemas/makale.schema.json`) olabildiğince yakın kur, çünkü Türkçe düzeltme ekranı sonra oradan taşınacak.
- Parçalar: `giris`, `bolum-N`, `gecis-K`, `kapanis`. Yeniden kancalar geçiş parçasıdır.
- Paragraflar.
- Cümleler. Her cümlede şunlar bulunur:
  - numara: bütün metinde tek sıradadır;
  - İngilizcesi: kanıt işaretleri çıkarılmış temiz metindir;
  - Türkçesi;
  - kanıt kimlikleri: işaretlerden çıkarılır ve cümlede ayrı tutulur;
  - uyarılar: denetimden, çevirmenden ve rakamdan gelir.
- Terimler.
- Sürüm bilgisi: ton dosyası, ton adı ve ton SHA-256'sı; plan; her adımın çalışma kimliği, modeli, eforu, süresi ve bedel karşılığı; kelime sayısı.

**Cümle bölme.** Housing Atlas'ın `atlas/article/split.py`'sindeki İngilizce ve Türkçe bölücüyü taşı. Testleri de taşınır; davranışı bilerek değiştirirsen sebebini rapora yaz. Kanıt işaretleri bölmeden önce cümleye bağlanır; bir işaret, ait olduğu cümlenin sonunda kalır.

**Son okuma.** Son okuyucunun düzeltmeleri program tarafından uygulanır.
- Düzeltilen cümlenin kanıt işaretleri korunmalı; korunmazsa düzeltme uygulanmaz ve uyarı olarak kaydedilir.
- Düzeltme birden fazla cümle içeriyorsa yeniden bölünür ve numaralar yeniden verilir.

**Dosyalar.** Her sürüm için şu dosyalar yazılır:
- İngilizce temiz metin, başlıklı Markdown,
- Türkçe metin, başlıklı Markdown; terimler sonda,
- seslendirme dosyası: numarasız, başlıksız, kanıt işaretsiz düz İngilizce,
- kanıt işaretli İngilizce metin (denetim için),
- denetim raporu.
Ekrandan üçü indirilebilir: İngilizce, Türkçe ve seslendirme.

**Saklama.** Metin çalışmaları ve sürümleri saklanır, hiçbiri silinmez. Şema 17 olur ve geçiş yazılır. Uygulama sürümü 0.17.0 olur. Kayıtların bir kısmını dosyada, bir kısmını veritabanında tutmak serbesttir; ama sürüm listesi, durumlar ve seçim veritabanından okunur ki iş akışı hesaplanabilsin.

**Seçim.** Karşılaştırma ekranında "Bu tonla devam et" seçilen sürümü videonun seçilmiş metni yapar. Seçim değiştirilebilir; eski seçim kayıtta kalır.

==================================================
ADIM 7 — Program denetimi
==================================================
Ek O'daki kuralları uygula. Denetim yazılan her sürüm için çalışır ve raporu sürümle saklanır. Bulgular cümlelere bağlanır; ekranda cümlenin yanında kırmızı ya da sarı işaret olarak görünür.

- **Kırmızı kurallar:** Bloklarla ilgili olanlar kanıt bloklarının kullanım notlarından gelir (`studio/evidence/blocks.py` `USAGE`). Kod içinde tanımlanır ve her birinin testi olur.
- **Sarı uyarı ifadeleri:** `studio/destinations/thirty_a_claude/uyari_ifadeleri.txt` dosyasında, her satırda bir ifade olarak durur. Dosya Ek O'daki listeyle başlar ve Ayarlar → Tonlar sayfasının altındaki "Denetim: uyarı ifadeleri" kutusundan düzenlenir. Bu kutu talimat düzenleyicinin aynı kayıt ve sürüm kurallarına uyar. Eşleşme büyük-küçük harfe duyarsızdır ve kelime sınırına bakar. Tek istisna "I": yalnız büyük harfle ve tek kelime olarak eşleşir.
- **Rakam denetimi:** Ek O'daki toleranslarla yapılır. Housing Atlas'ın `atlas/article/digits.py`'sindeki rakam okuma yöntemini temel al. "seven thousand", "a third", "half" gibi kelimeyle yazılan yaygın sayıları da oku.
- **Denetim kimseyi durdurmaz:** Bulgular raporlanır, sürüm kaydedilir. Kırmızı bulgu sayısı karşılaştırma ekranında görünür.

==================================================
ADIM 8 — Ekranlar
==================================================
**Video metni adımı** (`#adim/metin`). En üstte "Sıradaki iş" satırı durur. Altında şunlar bulunur:
- **Ton seçimi:** Tonlar onay kutularıyla listelenir. Varsayılan ton işaretli gelir. Her tonun yanında metninin ilk cümlesi görünür. Yanında "Tonları yönet" bağlantısı vardır.
- **"Metni yaz" düğmesi.** Paket yoksa ya da eskiyse düğmenin altında "Paket önce yeniden üretilecek" yazar.
- **Metin çalışmaları:** Tarih, tonlar, durum, kullanım ve sürümler listelenir. Duraklatılmış ya da yarıda kalmış çalışmada "Devam" düğmesi bulunur.
- **"Planı göster":** Bölümler, tek fikirleri, bütçeleri, açılış biçimleri, kavramların yeri, yeniden kancalar, vaat kontrolü, program uyarıları ve eleştirmenin notları salt okunur gösterilir.

**Karşılaştırma ekranı.**
- **Düzen:** Tonlar yan yana sütunlarda durur. Satırlar parçalardır: giriş, bölümler, geçişler ve kapanış. Sütun çok olursa yatay kaydırma olur.
- **Dil:** Türkçe önde gelir; "İngilizce" düğmesi sütunları İngilizceye çevirir. Ayrıca İngilizce ile Türkçe alt alta da gösterilebilir.
- **Sütun başı:** Her sütunun başında tonun adı, kelime sayısı, tahmini süre (kelime/150 dakika), kırmızı ve sarı bulgu sayısı, harcanan kullanım (token, bedel karşılığı) ve süre yazar.
- **Düğmeler:**
  - "Bu tonla devam et" sürümü seçer.
  - "Tek göster" sürüm görünümünü açar.
  - Ekranın üstündeki "Bu tonla da yaz" düğmesi listeden başka bir ton seçtirir ve aynı planla yazdırır.

**Sürüm görünümü.**
- **Metin:** Cümleler numaralıdır; İngilizce ve Türkçe yan yana durur.
- **Uyarılar:** Kanıt kimlikleri cümlenin üzerine gelince görünür. Denetim bulguları ve çevirmen uyarıları cümlenin yanında durur.
- **Ekler:** Terim listesi ve denetim raporunun tamamı.
- **İndirme:** İngilizce, Türkçe ve seslendirme dosyaları.

Türkçe düzeltme ve İngilizceye uyarlama bu görevde yok. Housing Atlas'taki MS1 ekranı orada oturduktan sonra ayrı bir görevde taşınacak. Ekranda bunu söyleyen kısa bir not durur.

**İş akışı.** "Video metni" adımı artık planlanan değildir. Durumu kayıtlardan hesaplanır:

| Durum | Ne zaman | "Sıradaki iş" satırı |
|---|---|---|
| bekliyor | paket yok | Önce paket üretilmeli. |
| hazır | çalışma yok | Ton seç ve "Metni yaz"a bas. |
| çalışıyor | çalışma sürüyor | — |
| hata ya da duraklatıldı | çalışma durdu | Sebep ve "Devam". |
| onay bekliyor | sürümler var, seçim yok | Karşılaştırma ekranında tonları karşılaştır ve "Bu tonla devam et" de. |
| tamamlandı | seçim var | Seçilen metin ve ton yazılır; sonraki adım Kontrol (henüz kurulmadı). |
| eskidi | seçilen sürümden sonra veri yeniden çekildi ve paket değişti | Bilgi olarak gösterilir. |

**Ayarlar.** Ayarlar'a şunlar eklenir:
- Tonlar bölümü (Adım 3) ve uyarı ifadeleri kutusu,
- Claude bölümüne yedi yeni adımın model ve eforu (başlangıç değerleri Ek N'de), oturum sınırı, kullanım eşikleri ve "Plandan sonra dur".

Bütün renk, boşluk ve yazı tipleri mevcut CSS değişkenlerinden gelir. Ekran metinleri Türkçedir.

==================================================
ADIM 9 — Testler
==================================================
Testlerde gerçek Claude çağrılmaz. `tests/fake_claude.py` yeni adımları tanıyacak biçimde genişletilir: her adım için şemaya uyan, kanıt işaretli örnek çıktı yazar. Ayrıca istenince şu durumları canlandırır:
- geçersiz cevap,
- geçici hata,
- kullanım sınırı (akışta sınır bildirimi ve hata metni),
- yavaş cevap (paralellik ve kesme için).

En az şunlar sınanır:
- **Ton yönetimi:**
  - ekleme; boş ad, aynı ad ve uzun metin;
  - düzenleme ve diskte değişiklik çakışması;
  - silme: arşive taşınır, son ton silinemez;
  - arşivden geri alma;
  - varsayılan tonun değişmesi;
  - sürümler ve geri dönüş;
  - Türkçe adlardan dosya adı;
  - silinmiş tonla yazılmış sürümün görünmesi.
- **Birleşik talimat:** Sesin verildiği ve verilmediği adımlar; çalışma kaydında ton bilgisi.
- **Kimlik çevirisi:** `baslik_analizi.md`'de kimliklerin video paketine çevrilmesi; pakette olmayan kimlik.
- **Zincir:**
  - iki tonla uçtan uca çalışma;
  - aynı planın iki tonda kullanılması;
  - "Bu tonla da yaz";
  - "Planı yeniden yap";
  - plan denetiminden dönüş;
  - eleştirmenden dönüş;
  - geçersiz cevapta bir yeniden deneme;
  - paralel bölüm yazıcılarının oturum sınırına uyması;
  - kullanım eşiğinde bekleme ve kendiliğinden sürme (saat taklit edilerek);
  - geçici hata beklemeleri;
  - "Durdur" ve "Devam";
  - program kapanıp açılınca yarıda kalan çalışmanın sürmesi (biten adımlar yeniden çalışmaz);
  - "Plandan sonra dur";
  - metin çalışması sürerken başka Claude çalışmasının reddedilmesi.
- **Metin:**
  - cümle bölme (Housing Atlas'ın testleriyle);
  - kanıt işaretlerinin cümleye bağlanması ve temiz metin;
  - son okuma düzeltmelerinin uygulanması ve işaret kaybında reddedilmesi;
  - çevirinin numara denetimi;
  - iki dilde rakam denetimi;
  - seslendirme dosyası.
- **Program denetimi:**
  - Ek O'daki her kırmızı kural;
  - `dogrulanamadi` satırı;
  - küçük örnekte mahalle karşılaştırması;
  - uyarı ifadeleri dosyası;
  - "I" kuralı;
  - rakam toleransı.
    - Şu örnekler tutar: $7,223 → "about $7,200" ve "about $7,000"; 84.2 °F → "84 degrees"; %7.1 → "about 7 percent"; 87 ilan → "about 90 listings".
    - Şu örnekler tutmaz: $7,223 → "$7,500"; 87 ilan → "90 listings" (burada "about" yok).
  - uzunluk ve plan denetimleri.
- **İş akışı:** Video metni adımının bütün durumları; Adım 1d'deki adaysız değerlendirme.
- **Arayüz** (Node):
  - ton listesi ve formu;
  - ton seçimi;
  - karşılaştırma sütunları ve dil düğmesi;
  - sürüm görünümü;
  - ilerleme metni;
  - bekleme metni.
- **Geçiş:** Şema 16 → 17.

==================================================
ADIM 10 — Gerçek ortam ve teslim
==================================================
1. **Geçici klasörde deneme:** Gerçek verinin kopyası ve sahte claude kullanılır.
   1. Geçici bir video kaydı açılır: Rosemary Beach çalışmasının (0d773a0c) ilk adayından seçim yapılır.
   2. Video paketi üretilir.
   3. "Araştırmacı dost" ve "Hikâye anlatıcısı" tonlarıyla metin yazdırılır. Sonra "Bu tonla da yaz" ile "Pratik planlayıcı" eklenir.
   4. Kullanım sınırı beklemesi ve "Durdur" / "Devam" bir kez canlandırılır.
   5. Ayarlar → Tonlar'da bir ton eklenir, düzenlenir, silinir ve geri alınır.
   6. Ekran görüntüleri alınır (Teslim'deki liste).
2. **Geçiş denemesi:** Gerçek verinin kopyasında şema 16 → 17 denenir. Satır sayıları önce ve sonra karşılaştırılır; `integrity_check` ve `foreign_key_check` çalıştırılır.
3. **Gerçek veritabanı** (CLAUDE.md kuralına göre):
   1. data/ tam yedeği alınır.
   2. Uygulama masaüstü kısayoluyla gerçek veriyle açılır; geçiş çalışır.
   3. Ayarlar → Tonlar'da beş ton ve varsayılan "Araştırmacı dost" görünür. Ayarlar → Claude'da yeni adımlar görünür.
   4. Gerçek Claude çalıştırması yapılmaz. Başlık seçilmez, video kaydı açılmaz.
   5. Program kapatılır. Önce ve sonra karşılaştırması yapılır: satır sayıları, `integrity_check`, `foreign_key_check`.
4. **Belgeler:**
   - yeni `docs/M17-VIDEO-METNI.md`: zincir, tonlar, ton yönetimi, denetim, ekranlar, sınırlar;
   - CALISMA_MANTIGI.md, README.md (Video metni ve tonlar; kullanıcının tonlarının git'te değişiklik olarak görünmesi);
   - docs/DEVIR/05 ve 02'nin güncel durum satırları;
   - M15: yeni adımlar, ayarlar;
   - CLAUDE.md: ton ve uyarı ifadeleri dosyalarının da Adım 1a'daki gibi korunacağı.
   - Yöneticinin üç tasarım belgesinin kopyası `docs/gorevler/GOREV-15/tasarim/` altına konur.
   - Tam test takımı yerelde art arda en az 3 kez geçmeli.

TESLİM
docs/gorevler/GOREV-15/ altına şunlar konur:
- GOREV.md (work/gorevler/GOREV-15.md'nin kopyası) ve RAPOR.md,
- `tasarim/` (yöneticinin üç belgesi),
- geçici denemedeki bir sürümün dosyaları: İngilizce, Türkçe, seslendirme ve denetim raporu (sahte claude çıktısı olduğu belirtilerek),
- ekran görüntüleri:
  - Ayarlar → Tonlar: liste, yeni ton formu, arşiv;
  - Video metni adımı ve ton seçimi;
  - plan görünümü;
  - İşler panelinde zincirin ilerlemesi ve kullanım sınırı beklemesi;
  - karşılaştırma ekranı: Türkçe ve İngilizce;
  - sürüm görünümü, denetim işaretleriyle;
  - Ayarlar → Claude: yeni adımlar, oturum sınırı, eşikler;
  - iş akışında Video metni adımının durumları.

RAPOR.md Türkçe ve sade olur. İçinde şunlar bulunur:
- her adımın sonucu;
- main ve etiketin konumu, CI sonuçları, test sayıları;
- Housing Atlas'tan taşınanlar ve bilerek değiştirilenler;
- şemaların özeti;
- program denetimi kuralları ve testleri;
- geçici denemenin özeti;
- gerçek veritabanının önce ve sonrası;
- beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.

Push etmeden önce `git status` ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.

Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-15 bitti, dal gorev-15-video-metni, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.

==================================================
EK A — studio/destinations/thirty_a_claude/ses_ortak.md (aynen)
==================================================
# Anlatıcının sesi — her tonda aynı

Bu metni 30A'ya gitmeyi düşünen, İngilizce konuşan, tatilinin parasını ve zamanını doğru yere harcamak isteyen biri dinleyecek. Video yüzsüz ve metni yapay zekâ sesi okuyacak. Bu yüzden okunacak bir yazı değil, konuşan bir insanın kulağa doğal gelen sözlerini yaz.

Kanalın arkasında oraya gidip gelmiş tek bir kişi yok. Bu yüzden anlatıcı kendinden "I" diye söz etmez; kanalın araştırmasından "we" diye söz eder. Yalnızca kanıt paketinde olanı bilgi olarak söyler. Yorum yaptığında bunun bir yorum olduğu duyulur. Rakamları insanın konuşurken söyleyeceği gibi yuvarlar. Bir bilginin nereden geldiğini ilk geçtiği yerde doğal bir biçimde söyler. Paketteki kullanım notları bir bilginin nasıl söylenebileceğini anlatır; anlatıcı onlara uyar.

Amaç bir yeri güzel göstermek değil, anlaşılır kılmaktır. İlgi sıfatlardan değil somut bilgiden doğar. İyi yanlar da can sıkıcı yanlar da aynı dürüstlükle söylenir ve karar izleyiciye bırakılır.

Aşağıda bu metin için seçilen ton var. Ton anlatıcının kişiliğini belirler; yukarıdakiler her tonda geçerlidir.

==================================================
EK B — studio/destinations/thirty_a_claude/tonlar/arastirmaci_dost.md (aynen)
==================================================
# Ton: Araştırmacı dost

Anlatıcı, 30A'yı iyi tanıyan ve izleyici için araştırmasını önceden yapmış bir dost. İzleyiciyle karşısında oturuyormuş gibi, doğrudan "you" diye konuşur. Sakin, sıcak ve açık sözlüdür. Bir bilgi gerçekten şaşırtıcıysa şaşırır, değilse onu büyütmez. Yeri geldiğinde hafif bir espri yapar ama kimseyle alay etmez. Ne yapılması gerektiğini söylemek yerine, izleyicinin durumuna göre neyin önemli olduğunu gösterir. Kasırga ya da ceza gibi konuları korkutmadan, bir arkadaşın uyarısı gibi anlatır.

==================================================
EK C — studio/destinations/thirty_a_claude/tonlar/belgesel.md (aynen)
==================================================
# Ton: Belgesel anlatıcı

Anlatıcı, iyi bir gezi belgeselinin sesi. İzleyiciye doğrudan seslenmekten çok onu yerin içine götürür: kasabanın nasıl kurulduğunu, orada bir günün nasıl geçtiğini, mevsimle neyin değiştiğini anlatır. Temposu daha ağır, cümleleri daha akıcıdır ama süslü değildir. Sahneyi pakette olan bilgiyle kurar; pakette olmayan bir görüntü, ses ya da ayrıntı uydurmaz. Rakamları hikâyenin içinde ve abartmadan verir. Ciddidir ama soğuk değildir.

==================================================
EK D — studio/destinations/thirty_a_claude/tonlar/pratik_planlayici.md (aynen)
==================================================
# Ton: Pratik planlayıcı

Anlatıcı, tatilini hesap tablosuyla planlayan ve lafı dolandırmayan bir arkadaş. Her konuya izleyicinin vereceği karardan girer. Rakamları, seçenekleri ve her seçeneğin bedelini öne koyar, gerisini kısa tutar. Seçenekleri izleyicinin durumuna göre ayırır. Cümleleri net ve tempolu ama kesik değildir. Manzara anlatmaya pek vakit ayırmaz ve kuru bir mizahı vardır.

==================================================
EK E — studio/destinations/thirty_a_claude/tonlar/vlogger.md (aynen)
==================================================
# Ton: Vlogger

Anlatıcı, kameraya konuşan bir YouTuber'ın rahat ve canlı sesiyle, izleyiciyle sohbet eder gibi gündelik bir dille konuşur. Kanalın arkasındaki küçük ekip gibi "we" der; araştırırken neye şaşırdıklarını ve neyin işlerine yaradığını içtenlikle paylaşır. Enerjisi yüksektir ama bağırmaz; temposu hızlı, geçişleri doğaldır. Oraya gidip kaldığını, bir şey yediğini ya da bir yerde yürüdüğünü söylemez, çünkü kanal bir gezi günlüğü değil, bir araştırma kanalıdır; tepkilerini elindeki bilgiye verir.

==================================================
EK F — studio/destinations/thirty_a_claude/tonlar/hikaye_anlaticisi.md (aynen)
==================================================
# Ton: Hikâye anlatıcısı

Anlatıcı, izleyiciyi sonuna kadar ekranda tutan anlatı kanallarının sesi. Her bölümü bir soruyla ya da bir merak düğümüyle açar; cevabı hemen vermez, bilgiyi doğru anda ortaya koyar. Gerilimi abartıdan değil, bilginin sırasından kurar; şaşırtıcı bir gerçek, gerçekten şaşırtıcı olduğu için etkiler. İzleyiciye "you" diye seslenir. Merakı bir sonraki bölüme taşır ama cevabı vaat ettiği yerde verir ve boşta bir merak bırakmaz.

==================================================
EK G — studio/destinations/thirty_a_claude/metin_plan.md (aynen)
==================================================
# Video metninin planı

Görevin, seçilen başlık için 15–17 dakikalık videonun planını yapmak. Metni sen yazmayacaksın; bölümleri ayrı yazıcılar aynı anda yazacak ve her biri yalnız kendi bölümünü ve senin planını görecek. Bu yüzden plan, her yazıcının videonun bütününü bilmeden doğru bölümü yazabileceği kadar açık olsun.

Seçilen başlık ve onun için yapılmış analiz baslik_analizi.md dosyasında: izleyicinin sorusu, kanca, neden önerildiği, ilk içerik planı ve eksik veri. Videonun kanıtları paket_ozeti.md dosyasında, sayıları sayilar.csv dosyasında. Paketi kendin baştan sona oku; kimse senin için özetlemedi. Kanalın planı kanal_plani.md dosyasında.

Başlık analizindeki içerik planı bir başlangıçtır. Kanıtı okuyunca daha iyi bir sıra ya da bölümleme görürsen değiştir. İzleyici videoyu bir soruyla açtı; plan bu soruya adım adım cevap veren bir yol olsun ve her bölüm bir öncekinin bıraktığı merakı taşısın. En güçlü bilgiyi başta harcama: ikinci en güçlüsü başa, en güçlüsü sona doğru gelsin.

Her bölüm için tek fikrini, en çarpıcı anını, dayandığı kanıt kimliklerini, kelime bütçesini ve nasıl açılacağını yaz. Bölümlerin açılışları birbirine benzemesin; yan yana iki bölüm aynı biçimde açılmasın. Açıklanması gereken bir kavram varsa onu hangi bölümün bir kez açıklayacağını yaz; diğer bölümler o açıklamayı tekrarlamaz. Videonun üçte birinde ve üçte ikisinde izleyiciyi yeniden yakalayacak bir an göster. Son olarak başlığın vaadinin hangi bölümlerde karşılandığını yaz; karşılanamayan bir vaat varsa bunu açıkça söyle.

Çıktın plan.json dosyasıdır ve şemaya uyar: 5–7 bölüm. Bölümlerin kelime bütçeleri toplamı yaklaşık 2.000–2.200 olsun; giriş ve kapanış ayrıca yazılacak.

==================================================
EK H — studio/destinations/thirty_a_claude/metin_plan_elestiri.md (aynen)
==================================================
# Planın eleştirisi

Görevin, bir video metninin planını metin yazılmadan önce okumak ve zayıf yerlerini bulmak. Planı sen yazmadın; onu ilk kez gören biri gibi oku. Plan plan.json dosyasında, başlık analizi baslik_analizi.md dosyasında, kanıtlar paket_ozeti.md ve sayilar.csv dosyalarında.

Kendine şunu sor: bu başlığa tıklayan biri videoyu sonuna kadar izler mi ve sorusunun cevabını alır mı? Başlığın vaadinin karşılanıp karşılanmadığına, bir bölümün kanıtın söylediğinden fazlasını vaat edip etmediğine, iki bölümün aynı şeyi anlatıp anlatmadığına, bir bölümün doldurulamayacak kadar ince olup olmadığına ve merakın bir yerde kopup kopmadığına bak. Pakette olup plana girmemiş daha güçlü bir bilgi varsa onu da söyle. Yalnız gerçekten önemli olanları yaz; küçük beğeni farklarını not etme.

Çıktın plan_elestirisi.json dosyasıdır ve şemaya uyar: notların ve planın yeniden yapılması gerekip gerekmediği. Plan iyiyse bunu söylemekten çekinme.

==================================================
EK I — studio/destinations/thirty_a_claude/metin_bolum.md (aynen)
==================================================
# Bir bölümün metni

Görevin, videonun tek bir bölümünü yazmak; diğer bölümleri başka yazıcılar aynı anda yazıyor. Planın tamamı plan.json dosyasında. Senin bölümün bolum.md dosyasında: bölümün tek fikri, en çarpıcı anı, nasıl açılacağı, kelime bütçesi, açıklaman gereken kavramlar ve kanıtların. Önceki ve sonraki bölümün ne anlattığı da orada birer cümleyle var; yalnız bölümünün yerini bilmen için.

Bölümün kendi başına anlaşılsın. İzleyici geri saramaz: başka bir bölüme gönderme yapma; bir şeyi hatırlatman gerekiyorsa kısaca yeniden söyle. Bölümün sonunda anlattığını özetleme; bölüm son bilgisiyle bitsin. Başka bir bölümün açıklayacağı bir kavramı açıklama. Kelime bütçesine yakın kal.

Bilgi taşıyan her cümlenin sonuna dayandığı kanıtın kimliğini köşeli parantez içinde yaz, örneğin [K0123]. Bu işaretler seslendirmede görünmeyecek; program rakamları ve iddiaları onlarla kontrol edecek. Kanıtta olmayan bir bilgiyi yazma.

Çıktın bolum.json dosyasıdır ve şemaya uyar.

==================================================
EK J — studio/destinations/thirty_a_claude/metin_birlestirme.md (aynen)
==================================================
# Bölümlerin birleştirilmesi

Bölümler ayrı yazıcılar tarafından aynı anda yazıldı; şimdi tek bir video gibi akmaları gerekiyor. Görevin, bölümlerin arasına geçişleri ve planın gösterdiği yerlere yeniden kancaları yazmak. Bölümler bolumler.md dosyasında sırasıyla, plan plan.json dosyasında.

Bir geçiş, bir sonraki bölümün en çarpıcı anına doğru merak uyandırır; her yere uyan bir kalıp cümle değildir. Yeniden kanca, videonun ortasında dikkati dağılmaya başlayan izleyiciye neden izlemeye devam etmesi gerektiğini somut bir bilgiyle hatırlatır. Geçişleri kısa tut; bölümlerin işini onlar yapmaz.

Bölümlerin metnine dokunma. İki bölümün birleştiği yerde bir cümle kendini tekrarlıyor ya da çelişiyorsa bunu not et. Geçişlerde bir bilgi kullanırsan kanıt kimliğini yaz.

Çıktın birlestirme.json dosyasıdır ve şemaya uyar.

==================================================
EK K — studio/destinations/thirty_a_claude/metin_giris_kapanis.md (aynen)
==================================================
# Giriş ve kapanış

Videonun gövdesi bitti. Girişi ve kapanışı en son sen yazıyorsun, çünkü neyin vaat edileceğini ancak bitmiş metni okuyan biri bilir. Bitmiş metin metin.md dosyasında, başlık ve analizi baslik_analizi.md dosyasında, kanalın yayınlanmış videoları yayinlanan_videolar.md dosyasında.

Giriş, başlığa tıklayan kişiye ilk 30 saniyede doğru yere geldiğini gösterir: başlığın vaadini somut bir bilgiyle doğrular ve videonun cevaplayacağı soruyu kurar. İçindekileri saymaz, videoyu tanıtmaz, doğrudan konuya girer. Yaklaşık 80–120 kelime.

Kapanış, videonun izleyiciye bıraktığını kısaca toplar ve kararı ona bırakır. Kanala abone olmayı doğal bir cümleyle önerir ve yayınlanmış videolardan bu izleyicinin işine yarayacak birini önerir; yayınlanmış video yoksa öneri yapmaz. Yaklaşık 80–120 kelime.

Bilgi taşıyan cümlelere kanıt kimliğini yaz. Çıktın giris_kapanis.json dosyasıdır ve şemaya uyar.

==================================================
EK L — studio/destinations/thirty_a_claude/metin_son_okuma.md (aynen)
==================================================
# Son okuma

Metin bitti ve ilk kez baştan sona tek parça olarak okunuyor. Görevin, onu bir dinleyicinin kulağıyla okumak ve yalnız küçük düzeltmeler yapmak. Metin metin.md dosyasında numaralı cümleler hâlinde, kanıtlar paket_ozeti.md dosyasında.

Ayrı yazıcılardan gelen metinlerde olan şeyleri ara: aynı bilginin ya da ifadenin tekrar etmesi, bölümler arasında çelişki, aynı biçimde açılan ya da biten cümleler, yapay zekâ yazısını ele veren yerler, kulağa doğal gelmeyen cümleler, kanıtın söylediğinden fazlasını söyleyen ya da pakette olmayan bir ayrıntı ekleyen cümleler. Anlatıcının seçilen tonunu bir kusur sayıp düzeltme. Bölümleri yeniden yazma, sırayı değiştirme; yalnız gereken cümleyi düzelt ve neden düzelttiğini kısaca yaz. Kanıt kimliklerini koru.

Çıktın son_okuma.json dosyasıdır ve şemaya uyar: düzeltilen her cümlenin numarası, yeni hali ve kısa bir gerekçe. Düzeltecek bir şey yoksa liste boş kalır.

==================================================
EK M — studio/destinations/thirty_a_claude/metin_ceviri.md (aynen)
==================================================
# Türkçe çeviri

Sana bir YouTube videosunun İngilizce metni numaralı cümleler hâlinde veriliyor. Metni İngilizce bilmeyen kanal sahibi okuyacak ve farklı anlatıcı tonlarını bu çeviriden karşılaştıracak. Her cümleyi kendi numarasıyla Türkçeye çevir. Çeviri anlamı tam taşısın, anlatıcının tonunu da taşısın ve Türkçede doğal dursun; çeviri kokan kalıplardan ve Türkçede kullanılmayan tabirlerden kaçın. Cümle sayısını değiştirme: her numaraya tek bir Türkçe cümle karşılık gelsin. Rakamları, paraları ve özel adları olduğu gibi koru.

Bölgeye ya da Amerika'ya özgü ve Türkçede tam karşılığı olmayan terimleri (örneğin customary use, LSV, beach walkover) Türkçe metinde İngilizce bırak ve terim listesine ekle; her terime bir iki cümlelik sade bir Türkçe açıklama yaz. Bir İngilizce cümle belirsiz, iki anlama gelebilen ya da kendi içinde yanlış görünüyorsa, onu çevirirken numarasıyla birlikte kısa bir Türkçe uyarı yaz. Çeviri sırasında anlaşılmayan bir cümle, izleyicinin de anlamayacağı bir cümledir.

Çıktın ceviri.json dosyasıdır ve şemaya uyar.

==================================================
EK N — Talimatların birleşimi, girdi dosyaları ve başlangıç modeli
==================================================
### Talimatların birleşimi

Her halkada Claude'a verilen talimat, aşağıdaki parçaların bu sırayla birleşiminden oluşur:

| Halka | Dosya | ortak.md | ses_ortak.md + ton | Şema |
|---|---|---|---|---|
| Planlayıcı | `metin_plan.md` | var | yok (plan tondan bağımsız) | `plan` |
| Plan eleştirmeni | `metin_plan_elestiri.md` | var | yok | `plan_elestirisi` |
| Bölüm yazıcısı | `metin_bolum.md` | var | var | `bolum` |
| Birleştirici | `metin_birlestirme.md` | var | var | `birlestirme` |
| Giriş ve kapanış | `metin_giris_kapanis.md` | var | var | `giris_kapanis` |
| Son okuyucu | `metin_son_okuma.md` | var | var | `son_okuma` |
| Çevirmen | `metin_ceviri.md` | var | var | `ceviri` |

### Çalışma klasöründeki dosyalar

Talimatlarda bu adlar geçer; program her halkada yalnız o halkanın ihtiyaç duyduğunu koyar.

- `baslik_analizi.md`: seçilen aday; başlık, izleyicinin sorusu, kanca, neden önerildiği, içerik planı, eksik veri.
- `paket_ozeti.md` ve `sayilar.csv`: video paketinin yazar özeti ve sayı listesi (GÖREV-14'teki içerik planından paket).
- `kanal_plani.md`: kanalın planı.
- `plan.json` ve `plan_elestirisi.json`: önceki halkaların çıktıları.
- `bolum.md`: bölüm yazıcısının kendi bölümü. İçinde planın o bölüme ait kısmı, o bölümün kanıt satırları ve önceki ile sonraki bölümün birer cümlelik özeti bulunur.
- `bolumler.md`: bölümler sırasıyla, kanıt işaretleriyle.
- `metin.md`: o ana kadar birleşmiş metin. Son okuyucuya cümleleri numaralı olarak verilir.
- `yayinlanan_videolar.md`: kanalın yayınlanmış videoları (başlık, konu, adres). İlk videoda boştur.

### Hangi adıma hangi dosya

| Adım | Çalışma klasörüne konan dosyalar |
|---|---|
| Planlayıcı | `baslik_analizi.md`, `paket_ozeti.md`, `sayilar.csv`, `kanal_plani.md` |
| Plan eleştirmeni | `plan.json`, `baslik_analizi.md`, `paket_ozeti.md`, `sayilar.csv` |
| Bölüm yazıcısı | `plan.json`, `bolum.md` |
| Birleştirici | `bolumler.md`, `plan.json` |
| Giriş ve kapanış | `metin.md` (düz), `baslik_analizi.md`, `yayinlanan_videolar.md` |
| Son okuyucu | `metin.md` (numaralı cümleler), `paket_ozeti.md` |
| Çevirmen | numaralı İngilizce cümleler (Housing Atlas'taki gibi görev metninde ya da bir dosyada) |

### Başlangıç modeli ve eforu

Bunlar Ayarlar → Claude'daki başlangıç değerleridir (model listesindeki aile adları ve efor değerleri). Kullanıcı Ayarlar'dan değiştirebilir; ilk gerçek denemede ölçülüp gözden geçirilecek.

| Halka | Model | Efor |
|---|---|---|
| Planlayıcı | opus | high |
| Plan eleştirmeni | opus | medium |
| Bölüm yazıcısı | opus | high |
| Birleştirici | opus | medium |
| Giriş ve kapanış | opus | high |
| Son okuyucu | opus | medium |
| Çevirmen | sonnet | medium |

==================================================
EK O — Program denetimi kuralları (Claude'a verilmez)
==================================================
#### Kırmızı: bilgiyi yanlış söyler

Bu kurallar kanıt bloklarının kullanım notlarından çıkarıldı (`studio/evidence/blocks.py` `USAGE`). Program metinde bunları arar ve denetim raporunda kırmızıyla gösterir.

| Blok | Kullanım notu | Aranan |
|---|---|---|
| Mesafe (M13) | "Yürüme mesafesi" ya da yol ve süre iddiası kullanılmaz | walking distance, walkable, a short walk, minute walk, minutes' walk, minutes away, minute drive, minutes to drive |
| Fiyat (M11) | "Bir hafta $X tutar" denmez | a week costs, a week in … costs, costs about $… a week, per week it costs |
| Envanter (M10) | "30A'da N ev var" ya da "tam liste" denmez | full inventory, full list, complete list, every rental, all the rentals, there are … homes in |
| İklim (M8) | "30A'nın iklimi" denmez | 30A's climate, the climate in 30A, climate of 30A |
| Restoran (M12) | "En iyi", "en popüler", "en ucuz" sıralamaları kullanılmaz | best restaurant, the best place to eat, most popular, cheapest restaurant |
| Trafik (M9) | Sıkışıklık ya da yolculuk süresi iddiası yapılmaz | traffic jam, gridlock, bumper-to-bumper, takes … minutes to get |
| Kaynak durumu (M9) | Durumu "doğrulanamadı" olan satır kullanılmaz | Kanıt işareti durumu `dogrulanamadi` olan bir satırı gösteriyorsa |

#### Sarı: dikkat ister

- **Küçük örnek:** Kanıt işareti küçük örnek (`*`) hücresini gösteriyor ve cümlede iki mahalle karşılaştırılıyor.
- **Kaynak sorusu:** "no public beach access" geçiyor ve aynı ya da önceki cümlede kaynak söylenmiyor. Bu, son okuyucuya ve Kontrol adımına not olarak düşer.
- **Ses uyarıları:** `uyari_ifadeleri.txt`'deki ifadeler (aşağıda). Liste Ayarlar'dan düzenlenir.

#### Rakam ve yuvarlama

- **Kanıt işareti zorunlu:** Rakam taşıyan her cümlenin bir kanıt işareti olmalı. Rakam, işaretin gösterdiği satırların değerlerinden biriyle tutmalı: ana değer, çeyrekler, örneklem, pay, aralık ya da dönüşüm.
- **Tutma toleransı:**
  - Para ve sayılar: metindeki sayı, kanıt değerinin konuşma yuvarlamasıyla tutmalı. Yuvarlama; en yakın 10, 50, 100, 500 ya da 1.000'e, ya da "about" varken ±%3 içine olabilir. Örnek: $7,223 → "about $7,200" ya da "about $7,000" tutar; "$7,500" tutmaz.
  - Yüzdeler: ±0,5 puan. Yarım ve üçte bir gibi kesir ifadeleri kabul edilir.
  - Sıcaklıklar: ±1 °F.
  - Sayımlar (gün, ilan, kasırga): "about" yoksa tam tutmalı.
- **Kelimeyle yazılan sayılar:** "seven thousand", "a third" gibi ifadeler de denetlenir.
- **Kanıtsız rakam:** Tutmayan ya da işaretsiz rakam kırmızıdır.

#### Uzunluk ve plan

- **Uzunluk:**
  - Toplam kelime: hedef 2.200–2.500; 2.000'in altı ve 2.800'ün üstü sarı.
  - Bölümler: bütçesinden %25'ten fazla sapan bölüm sarı.
- **Plan denetimi:**
  - plan.json'daki bütün kanıt kimlikleri pakette olmalı.
  - Her kavram bir bölüme yerleştirilmiş olmalı.
  - Yan yana iki bölümün açılış biçimi aynı olmamalı. Bunun için şemada `acilis_bicimi` alanı bulunur: rakam, sahne, soru, geçmiş, karşılaştırma ya da diğer.
  - Bölüm bütçelerinin toplamı 1.900–2.300 arasında olmalı (planlayıcıya 2.000–2.200 denir).

  Pakette olmayan bir kanıt kimliği varsa plan bir kez planlayıcıya döner; yine varsa çalışma hata verir. Öbür bulgular uyarı olarak kaydedilir ve zincir sürer.

#### `uyari_ifadeleri.txt` başlangıç içeriği (her satırda bir ifade)

```
amazing
stunning
breathtaking
paradise
hidden gem
nestled
you won't believe
let's dive in
in this video we'll
without further ado
buckle up
as we mentioned
as I said
remember when
I
I'm
my
the ocean
```
