GÖREV-13 — Programın içinde Claude: çalıştırıcı, Ayarlar'da model ve efor, ilk Claude adımı (konu ve başlık önerisi)

BAĞLAM
Veri toplama ve kanıt paketi aşaması bitti; sıradaki iş video metni. Kullanıcının kararı (10 Ekim 2026): video için yapılacak her şey programın içinden yapılır. Program arka planda Claude'u çağırır ve Claude, programın verdiği talimata göre işi yapar. Claude burada kod yazan bir ajan değildir: ek talimatla doğrudan çağrılan Claude'dur. Hangi adımda hangi modelin ve hangi eforun kullanılacağı Ayarlar'dan seçilir. Akış şöyle olacak:
1. Program verilerden kanal konseptine uygun konu ve başlık önerileri çıkarır.
2. Kullanıcı uygulamada birini seçer.
3. Program seçilen başlık için veri paketini kurar.
4. Claude o paketle video metnini yazar; gerekirse bölüm bölüm.
5. Program kontrol eder.
Bu görev bu akışın ilk parçasını kurar: Claude çalıştırıcısı, Ayarlar'da model ve efor, adım çerçevesi ve onay ekranı, video kaydı ve ilk Claude adımı olan "konu ve başlık önerisi". Video metni adımı sonraki görevde gelecek.

Kullanıcının konu ve başlık adımı için istekleri (10 Ekim 2026):
- Kanalın genel konusu 30A'dır; videolar çoğunlukla mahalle düzeyinde, yani dar bir nişte olacak. Başlıklar bu bağı koparmamalı ve sürdürülebilir olmalı: aynı başlıklar tekrar tekrar çıkmamalı, bir mahallenin konuları bir defada tüketilmemeli.
- Başlıklar İngilizce ve Türkçe karşılığıyla gelir.
- Bir başlık ancak içi elimizdeki veriyle doldurulabiliyorsa önerilir.
- Claude her başlığı neden önerdiğini kısaca yazar. Ekranda önce başlık listesi görünür; bir başlık seçilince açıklaması ve neden önerildiği görünür.
- Bu analiz kaydedilir ve sonraki adımlarda (veri paketi ve video metni) kullanılır.

Bu yapının çalışan bir örneği kullanıcının başka projesinde var: The Housing Atlas Stüdyo, bilgisayarda `C:\Users\1\source\repos\housing-atlas`. Davranışı oradan taşı, yeniden icat etme. Önce şu dosyaları salt okunur incele:
- `atlas/ai/runner.py`: çalıştırıcı (komut, yalıtım, ortam değişkenleri, akış okuma, ölçüm, zaman aşımı, hata mesajları).
- `atlas/claude_info.py`: `claude` programını bulma, sürüm okuma, API anahtarı uyarısı.
- `atlas/config.py`: model ve efor listeleri, genel varsayılan ve adım başına ayar, `resolve_model_effort`.
- `atlas/ai/stages.py` ve `atlas/ai/validate.py`: adım tanımı, şema doğrulaması.
- `atlas/ai/schemas/`, `talimatlar/` (ortak ve adım dosyalarının birleştirilmesi).
- `tests/fake_claude.py` ile `tests/test_claude_runner.py`, `tests/test_claude_run.py`, `tests/test_claude_approval.py`, `tests/test_settings_claude.py`.
- `docs/TASARIM.md` Bölüm 6 (adımlar, onay ekranı, eskime) ve Bölüm 10 (Claude adımları); `docs/KARARLAR.md`'de M5 ve M5b kararları.
Gerekçesi orada yazılı olan ayrıntıları (ör. `claude.cmd` kabuğunun çözülmesi, `Write` izninin `Edit(...)` kuralıyla verilmesi, `--effort`'u tanımayan sürüm mesajı) aynen koru. 30A Studio'nun mimari sınırına uyarla: çalıştırıcı, adım çerçevesi ve onay ekranı genel çekirdekte; kanal tanımı ve talimat metinleri destinasyon tarafında durur.

Kullanıcı bu görev için main'e alma, gerçek veritabanını normal kullanımla güncelleme ve Adım 6'da kendi Claude aboneliğiyle iki gerçek çalıştırma yapılması iznini kendi mesajında açıkça veriyor. Bilgisayarda zamanlanmış görev oluşturulmaz.

KESİN SINIRLAR
- Housing Atlas klasöründe hiçbir dosya değiştirilmez; yalnız okunur.
- Testler gerçek Claude'u çağırmaz; sahte claude programı kullanılır. Gerçek çağrı yalnız Adım 6'dadır.
- Claude'a verilen araçlar adım başına sınırlıdır. Konu ve başlık adımında yalnız çalışma klasöründe okuma ve tek çıktı dosyasına yazma izni vardır; web araması, Bash ve başka araç yoktur.
- Talimat metinleri bu görevin eklerinde (Ek A ve Ek B) verilmiştir ve aynen kopyalanır. Talimat içeriği uydurulmaz ve kendiliğinden değiştirilmez; önerin varsa rapora yaz.
- data/ yalnız Adım 6'da, CLAUDE.md kuralına göre (önce tam yedek, sonra uygulamanın normal kullanımı) değişir. Toplayıcı çalıştırılmaz.
- main'e yalnız Adım 1'deki fast-forward ile dokun; bu görevde etiket konmaz.
- Claude Code, Adım 6'daki öneriler arasından başlık seçmez. Seçim kullanıcınındır.

==================================================
ADIM 1 — GÖREV-12'yi main'e al; küçük düzeltmeler
==================================================
1a. Önce origin/gorev-12-yazar-ozeti'nin son commit'i (a854311) için GitHub Actions sonucunu kontrol et; başarısızsa önce düzelt, düzeltmeyi dala ekle ve bu adımı o commit'le yap. Sonra main'i bu dala git merge --ff-only ile getir ve push et. Bu sefer etiket konmaz: GÖREV-12 uygulama sürümünü değiştirmedi (0.14.0, şema 14). Bu görev uygulamayı 0.15.0'a ve şemayı 15'e çıkarır; v0.15.0 etiketi bir sonraki görevin ilk adımında konur. main CI sonucunu rapora ekle. Güncel main'den "gorev-13-claude-baslik" dalını aç.

1b. Yönetici kararları (GÖREV-12 raporundaki konulara):
- İlk video yazar özetinin 110 KB olması kabul. Referans notlarındaki araştırma geçmişinin ("GÖREV-07'de bulunamadı" gibi) nottan ayrılması ileride ele alınacak; bu görevde yapılmaz.
- Yayından önce kontrol listesi (18 satır) doğru kuruldu; böyle kalır.

1c. Küçük düzeltmeler (bu dalda, ayrı commit):
- Restoran saatlerinin yazımı: kaynakta boş olan gün yazılmaz. Edward's Fine Food & Wine'daki gibi ", Tu 17:00-21:00 …" diye virgülle başlayan metin çıkmaz. Bu kaynağın değil, bizim yazımımızın sorunudur.
- Havalimanı uzaklığı referans satırlarında değer alanı mil olur, km karşılığı dönüşüm olarak yanında yazar. Mesafe kaynağın değil bizim hesabımızsa, etiketi de öyle kalır.
- Kanıt paketi ekranındaki paket listesinde mahalle, seçili şablondan bağımsız olarak adıyla görünür ("rosemary-beach" değil, "Rosemary Beach").

==================================================
ADIM 2 — Claude çalıştırıcısı (genel çekirdek)
==================================================
2a. `studio/ai/` altında: `claude` programını bulma ve sürüm okuma, çalıştırıcı, sahte claude programıyla testler. Komut Housing Atlas'takiyle aynıdır: `claude -p --output-format stream-json --verbose --append-system-prompt-file <birleşik talimat> --tools <adımın araçları> [--allowedTools …] --permission-mode dontAsk --max-turns <n> --setting-sources "" --strict-mcp-config --disable-slash-commands [--model …] [--effort …]`. Görev metni standart girdiden verilir; çalışma klasörü o çalışmanın klasörüdür.
2b. Yalıtım Housing Atlas'taki gibi: kullanıcının ve projenin CLAUDE.md dosyaları, ayarları, kancaları, MCP sunucuları, becerileri, claude.ai bağlayıcıları ve otomatik bellek yüklenmez (`ENABLE_CLAUDEAI_MCP_SERVERS=0`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, `DISABLE_AUTOUPDATER=1`). Uygulama bir Claude Code oturumunun içinden başlatıldıysa o oturumun değişkenleri alt sürece geçmez. Kullanıcının aboneliği kullanılır. `ANTHROPIC_API_KEY` tanımlıysa bu, API ücretlendirmesi demektir: Ayarlar'da ve çalıştırmadan önce Türkçe uyarı gösterilir.
2c. Birleşik talimat şu sırayla kurulur: destinasyonun ortak talimatı, adımın talimatı ve adımın JSON şeması. Her çalışma, kullandığı talimat dosyalarının ve şemanın SHA-256 karmalarını kaydına yazar; böylece hangi sonucun hangi talimatla üretildiği her zaman bellidir.
2d. Akış satır satır okunur ve mevcut iş paneline Türkçe ilerleme satırları olarak yazılır (tur, okunan dosya, yazılan dosya, reddedilen araç). Akışın tamamı çalışma klasörüne kaydedilir. Kayda şunlar girer: oturum kimliği, süre, tur sayısı, araç çağrıları, token'lar ve varsa maliyet karşılığı. Zaman aşımı, tur sınırı, kullanım sınırı, eski sürüm ve desteklenmeyen model–efor durumları anlaşılır Türkçe mesajla gösterilir.
2e. Aynı anda tek Claude çalışması yürür. Uygulama çalışma sürerken kapanırsa o çalışma bir sonraki açılışta "hata: uygulama kapanırken yarıda kaldı" olur.

==================================================
ADIM 3 — Ayarlar: Claude bölümü
==================================================
3a. Ayarlar ekranına "Claude" bölümü eklenir. Bu bölümde şunlar bulunur:
- bulunan `claude` programının yolu ve sürümü,
- API anahtarı uyarısı (varsa),
- genel varsayılan model ve efor,
- adım başına model ve efor ("Genel varsayılan" seçeneğiyle),
- adım başına en fazla tur sayısı.
Model ve efor listeleri Housing Atlas'taki listelerdir (`MODEL_CHOICES`, `EFFORT_CHOICES`). Adım listesi şimdilik tek adımdır: "Konu ve başlık"; sonraki adımlar eklendikçe listeye girer. Konu ve başlık adımının başlangıç ayarı claude-opus-5-5 ve yüksek efordur.
3b. Ayarlar kullanıcı verisidir, repoya girmez: veri klasöründe saklanır. Gizli bilgi saklanmaz.

==================================================
ADIM 4 — Adım çerçevesi, onay ekranı ve video kaydı
==================================================
4a. Adım tanımı (genel çekirdek). Her Claude adımının şu parçaları vardır:
- anahtar ve Türkçe adı,
- talimat dosyaları (destinasyon tarafında),
- JSON şeması (çekirdekte),
- izinli araçlar,
- girdi kurucusu: program, girdi dosyalarını çalışmanın klasörüne kopyalar ya da üretir,
- görev metni,
- çıktı doğrulayıcısı: şema ve anlam denetimleri,
- okunur Markdown üreticisi: Claude yalnız JSON yazar, okunur Markdown'ı program üretir.
4b. Çalışma klasörü: `data/claude/<video ya da hazırlık kimliği>/<adım>/<çalışma kimliği>/`. İçinde girdiler, birleşik talimat, görev metni, akış kaydı, çıktı JSON'u, Markdown ve çalışma kaydı bulunur. Hiçbir çalışma silinmez; yeniden çalıştırma yeni klasör açar.
4c. Onay ekranı (genel). Claude'un çıktısı okunur biçimde gösterilir. Ekranda bir not alanı ve üç işlem vardır:
- **Seç / Onayla:** konu ve başlık adımında aday seçilir (4d).
- **Düzeltme iste:** yeni bir oturum açar. Kullanıcının notu ve önceki çıktı görev metninde verilir.
- **Reddet.**
Doğrulama sorunları (ör. var olmayan kanıt kimliği) ekranda ayrı listelenir.

4d. Videolar ekranı ve başlık önerisi.
- Yeni "Videolar" ekranında videolar listelenir ve "Konu ve başlık önerisi al" düğmesi bulunur. Düğmenin yanında üç seçim vardır:
  - **Bölge** (zorunlu): "30A geneli" ya da destinasyonun mahallelerinden biri.
  - **İçerik ailesi** (isteğe bağlı): kanal planındaki ailelerden biri ya da "hepsi".
  - **Not** (isteğe bağlı): kullanıcının kısa yönlendirmesi.
  Bu üç seçim görev metnine ve çalışma kaydına yazılır.
- Öneriler onay ekranında önce liste olarak görünür. Her satırda İngilizce başlık, altında Türkçe karşılığı ve içerik ailesi yazar.
- Bir başlığa tıklanınca ayrıntısı açılır:
  - neden önerildiği (kısa özet),
  - izleyicinin sorusu,
  - kanca ve dayandığı bilgiler (değerleriyle),
  - içerik planı: videonun bölümleri ve her bölümün hangi veriyle dolacağı,
  - eksik veri (varsa),
  - şablon ve parametreler,
  - kapak fikri.
  "Bu başlığı seç" düğmesi bu ayrıntının altındadır.

4e. Video kaydı. Seçilen her başlık bir video kaydı olur. Seçilen adayın bütün analizi kayda girer, çünkü sonraki adımlar (veri paketi ve video metni) bu analizi kullanacak. Kayıtta şunlar tutulur:
- kimlik ve destinasyon, bölge,
- İngilizce başlık ve Türkçe karşılığı,
- içerik ailesi,
- neden önerildiği, izleyicinin sorusu, kanca (kanıtlarıyla), içerik planı, eksik veri, kapak fikri,
- şablon ve parametreler,
- durum ve oluşturulma zamanı,
- başlığın geldiği çalışma.
Şema değişikliği gerekir: şema 15, uygulama sürümü 0.15.0. Migration önce gerçek verinin kopyasında denenir.

4f. Bir video kaydı için kanıt paketi üretildiğinde (mevcut "Kanıt paketi" üretimi, kaydın şablonu ve parametreleriyle), paketin ve yazar özetinin başına videonun başlığı, sorusu, kancası, neden önerildiği ve içerik planı yazılır ve paket video kaydına bağlanır. Kaydın şablonu yoksa (yeni şablon gerekir), paket düğmesi bunu söyler ve üretmez.

4g. K kimlikleri paket başınadır; başlık önerisindeki kimlikler öneriye girdi olan özetlerin paketlerine aittir. Bu yüzden video kaydı kancanın ve içerik planının kanıtlarını değerleriyle ve geldikleri paketin kimliğiyle saklar. Videonun paketi üretildiğinde başa yazılan analiz bu değerleri ve kaynak paketi gösterir. Aynı satır yeni pakette de varsa (aynı kaynak satırı ve aynı değer), yeni paketteki kimliği yanına yazılır; yoksa bu durum açıkça belirtilir.

==================================================
ADIM 5 — İlk Claude adımı: konu ve başlık önerisi
==================================================
5a. Talimatlar: `studio/destinations/thirty_a_claude/ortak.md` (Ek A) ve `baslik.md` (Ek B), aynen. Şema: `studio/ai/schemas/baslik.schema.json`.
5b. Girdiler. Program şu dosyaları çalışma klasörüne koyar:
- `kanal_plani.md`: docs/KONSEPT.md'nin tamamı. Önce Ek C'deki kanal ve içerik planını KONSEPT.md'nin sonuna ek olarak yaz.
- `kanal_arastirmasi.md`: `work/yonetim/30A_YOUTUBE_ARASTIRMA.md`'nin kopyası. Bu dosya repoya `studio/destinations/thirty_a_claude/kanal_arastirmasi.md` olarak alınır; tarihi başlığında yazar.
- `secim.md`: kullanıcının seçtiği bölge, içerik ailesi ve notu.
- `veri_ozeti_30a.md`: güncel verinin "ilk video" şablonundan üretilmiş yazar özeti. Her çalışmada verilir.
- `veri_ozeti_mahalle.md`: bölge olarak bir mahalle seçildiyse, o mahallenin "Mahalle rehberi" şablonundan üretilmiş yazar özeti. 30A geneli seçildiyse bu dosya yoktur.
- Program, bir özetin paketi verinin son çekiminden eskiyse özeti yeniden üretir.
- `sablonlar.md`: programın paket kurabildiği şablonlar. Her şablon için adı, ana sorusu, parametreleri (ör. mahalle ve geçerli değerleri) ve bölüm başlıkları. Program bu listeyi şablon dosyalarından üretir.
- `onceki_oneriler.md`: daha önce önerilen bütün başlıklar (İngilizce ve Türkçe, bölge, aile, tarih), seçilenler "seçildi" diye işaretli. İlk çalışmada boştur.

5c. Şema (`baslik.schema.json`). Alan adları Türkçedir:
- `surum`, `adim`, `notlar[]`,
- `adaylar[]`: her biri şu alanları taşır:
  - `baslik_en`, `baslik_tr`, `bolge`, `aile`,
  - `neden_onerildi`: kısa özet,
  - `izleyici_sorusu`,
  - `kanca{metin, kanitlar[]}`,
  - `icerik_plani[]`: her biri `{bolum, ne_anlatir, kanitlar[]}`,
  - `eksik_veri[]`,
  - `sablon` (şablon anahtarı ya da null), `parametreler{}`, `yeni_sablon_gerekir`,
  - `kapak_fikri`.
- `aile`, kanal planındaki içerik ailelerinden biridir (sabit liste).
Şema bilinmeyen alanı reddeder. Anlam denetimleri şunlardır:
- 8–12 aday olmalı.
- Bölge "30A geneli" ise en az 4 farklı aile bulunmalı. Bir mahalle seçildiyse adayların hepsi o mahalleyle ilgili olmalı. Bir aile seçildiyse adayların hepsi o aileden olmalı.
- Her kanıt kimliği (kanca ve içerik planı) verilen özetlerde bulunmalı.
- Her adayın içerik planında en az 5 bölüm olmalı ve her bölüm en az bir kanıta dayanmalı.
- Şablon ve parametreler var olmalı. Şablon null ise `yeni_sablon_gerekir` doğru olmalı.
- İngilizce başlık en çok 100 karakter olmalı.
- Başlıklar birbirini ve önceki önerileri tekrar etmemeli. Karşılaştırma büyük-küçük harf ve noktalama farkı gözetmeden yapılır.

5d. Markdown üreticisi. Önce başlık listesi gelir (İngilizce başlık, Türkçe karşılık, aile), sonra her aday için ayrıntı kartı (4d'deki alanlar; kanıtlar değerleriyle).

5e. Testler sahte claude programıyla yazılır ve şunları kapsar:
- geçerli çıktı, şemaya uymayan çıktı, var olmayan kanıt kimliği,
- içerik planında kanıtsız bölüm,
- mahalle seçildiğinde mahalle özetinin girdiye konması ve başka mahalleye ait adayın reddi,
- aile seçimine uymayan aday,
- önceki önerilerin girdiye konması ve tekrar eden başlığın reddi,
- tur sınırı, zaman aşımı, düzeltme isteğinin yeni oturum açması,
- seçimin video kaydını analiziyle birlikte oluşturması,
- ayarlardan gelen model ve eforun komuta geçmesi ("Genel varsayılan" dahil),
- yalıtım bayraklarının ve ortam değişkenlerinin komutta olması,
- talimat karmalarının kayda yazılması.

==================================================
ADIM 6 — Gerçek ortam ve teslim
==================================================
1. Geçici klasörde deneme: gerçek verinin kopyasıyla uygulama; Ayarlar'daki Claude bölümü, sahte claude ile bir başlık çalışması, onay ekranı, seçim ve video kaydı, video kaydından kanıt paketi.
2. Migration denemesi gerçek verinin kopyasında (şema 14 → 15): satır sayıları, integrity_check, foreign_key_check.
3. Gerçek veritabanı (CLAUDE.md kuralına göre): data/ tam yedeği; uygulamayı gerçek veriyle aç. Ayarlar varsayılan kalsın: konu ve başlık için claude-opus-5-5, yüksek efor. Kullanıcının aboneliğiyle iki gerçek "Konu ve başlık önerisi" çalışması yap, sırayla:
   - birincisi bölge "30A geneli", aile "hepsi", not boş;
   - ikincisi bölge "Rosemary Beach", aile "hepsi", not boş. İkinci çalışmada birincinin önerileri `onceki_oneriler.md` içinde olmalı.
   Başlık seçme ve düzeltme isteme; iki çalışma da onay bekler durumda kalsın. Sonra kapat ve önce/sonra karşılaştırmasını yap (satır sayıları, integrity_check, foreign_key_check).
4. İki çalışmanın çıktısını kendin oku ve rapora yaz: doğrulama sorunu var mı, kanıt kimlikleri ve değerleri doğru mu, aileler dağılmış mı, Rosemary önerileri 30A ile bağını koruyor mu, ikinci çalışma birincinin başlıklarını tekrar ediyor mu, şablonsuz öneri var mı. Her çalışmanın süresini, tur sayısını ve token'larını da rapora ekle.
5. Belgeler: CALISMA_MANTIGI.md, README.md, docs/DEVIR/05 ve 02'nin güncel durum satırları, yeni docs/M15-CLAUDE-ADIMLARI.md (çalıştırıcı, yalıtım, ayarlar, adım çerçevesi, onay ekranı, video kaydı, konu ve başlık adımı, yeni adım nasıl eklenir). Tam test takımı yerelde art arda en az 3 kez geçmeli.

TESLİM
docs/gorevler/GOREV-13/ altına şunlar konur:
- GOREV.md (work/gorevler/GOREV-13.md'nin kopyası) ve RAPOR.md,
- iki gerçek çalışmanın `baslik.json`, `baslik.md`, görev metni ve çalışma kaydı (akış kaydı hariç), ayrı klasörlerde,
- Ayarlar'daki Claude bölümünün, Videolar ekranının (seçimlerle), başlık listesinin ve bir başlığın açık ayrıntısının ekran görüntüleri.
RAPOR.md Türkçe ve sade olur. İçinde şunlar bulunur:
- her adımın sonucu,
- main'in konumu, CI sonuçları, test sayıları,
- Housing Atlas'tan taşınan ve bilerek değiştirilen davranışlar (gerekçeleriyle),
- iki gerçek çalışmanın özeti (her biri için adaylar tablo halinde: İngilizce başlık, Türkçe karşılık, aile, şablon),
- gerçek veritabanının öncesi/sonrası,
- beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-13 bitti, dal gorev-13-claude-baslik, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.

==================================================
EK A — studio/destinations/thirty_a_claude/ortak.md (aynen)
==================================================
# 30A kanalı — Claude adımları için ortak bilgi

Sen 30A Studio programının içinde çalışıyorsun. Program seni tek bir iş için çağırır; soru soramazsın, kullanıcıya dönemezsin. İşin görev metnindedir. Okuyabileceğin dosyalar çalışma klasöründedir; çıktını görev metninin söylediği dosyaya yazarsın. Kullanıcı sonucu programda görür ve karar verir.

Kanal, 30A / South Walton (Florida) için İngilizce, yüzü görünmeyen bir YouTube seyahat kanalıdır. İzleyici buraya tatile gelmeyi düşünen Amerikalılardır ve aklındaki soru şudur: "Burada tatil yapmak benim için doğru seçim mi, gidersem ne beklemeliyim?" Kanal bu karar için gereken bilgiyi eksiksiz ve kaynağıyla verir, kararı izleyiciye bırakır. Turistik tanıtım dili yoktur; kanal bir yeri güzel göstermeye değil, anlaşılır kılmaya çalışır.

Elindeki bilgi, programın resmî ve herkese açık kaynaklardan topladığı kanıttır. Her satırın bir kimliği (K0001 gibi), bir etiketi ve bir kullanım notu vardır. Kullanım notu o bilginin videoda nasıl söylenebileceğini anlatır; ona uy. Kanıtta olmayan bir şeyi bilgi gibi sunma. Bir bilgiye dayandığında kimliğini yaz ki program kontrol edebilsin.

Kullanıcıya yazdığın açıklamalar Türkçe, düz ve tam cümlelerle yazılır. Başlıklar ve video metni İngilizcedir.

==================================================
EK B — studio/destinations/thirty_a_claude/baslik.md (aynen)
==================================================
# Konu ve başlık önerisi

Görevin, kanalın bir sonraki videosu için konu ve başlık önermek. Kullanıcı önerilerinden birini seçecek. Seçilen başlıkla birlikte senin bu başlık için yaptığın analiz de kaydedilir; veri paketi ve video metni o analizle hazırlanır. Bu yüzden analizin, metni yazacak olana yol gösterecek kadar açık olsun.

Kullanıcının bu çalışma için seçtiği bölge, içerik ailesi ve notu secim.md dosyasında. Kanalın planı kanal_plani.md dosyasında: içerik aileleri, konu motoru (bölge × seyahat kararı × dönem × gezgin tipi) ve ilkeler. Kanal araştırması kanal_arastirmasi.md dosyasında: rakip videolar ve izleyicinin en çok sorduğu, tartıştığı konular. 30A'nın verisi veri_ozeti_30a.md dosyasında; bir mahalle seçildiyse o mahallenin verisi veri_ozeti_mahalle.md dosyasında. Programın paket kurabildiği video türleri sablonlar.md dosyasında. Daha önce önerilen bütün başlıklar onceki_oneriler.md dosyasında; onları ve onlara çok benzeyenleri tekrar önerme.

Kanal 30A'nın kanalıdır. Mahalleler bu kanalın alt bölgeleridir; bir mahalle videosu da 30A'nın bir parçasını anlatır. Mahalle başlıkları izleyiciye bunun 30A'da bir yer olduğunu hissettirsin ve kanalın tek konusu dağılmasın. Her mahallenin kendi konu evreni vardır (tam rehber, masraflar, arabasız tatil, aileler için, belirli bir ay, nerede yenir, plaj erişimi, fiyatına değer mi); önerilerin bu evreni bir defada tüketmesin, sonraki videolara yer bıraksın.

İyi bir konu, YouTube'un ana sayfasında ya da önerilen videolarda karşısına çıkan birinin tıklamak isteyeceği gerçek bir tatil sorusu ya da merak taşır. Başlık merak uyandırabilir ama videonun özünü değiştirmez; içerik ciddi, kaynaklı ve pratiktir. Kanca, verimizden çıkan ve başlığı taşıyan somut bir bilgidir.

Bir başlık ancak içi doldurulabiliyorsa önerilir. 15–17 dakikalık bir videonun bölümlerini elimizdeki veriyle kurabiliyor olmalısın; içerik planında her bölümün hangi bilgiyle dolacağını kimlikleriyle göster. Eksik kalan bir şey varsa gizleme, eksik veri olarak yaz. Küçük bir soru sırf video sayısı artsın diye ayrı video yapılmaz.

Her öneri için programın onu mevcut bir şablonla kurup kuramayacağını belirt. Kuramıyorsa yeni şablon gerektiğini yaz; öneriyi yine de sunabilirsin, çünkü hangi şablonların yazılacağına bu önerilerle karar verilecek.

Çıktın baslik.json dosyasıdır ve şemaya uyar: 8–12 aday. Her aday için İngilizce başlık ve Türkçe karşılığı, bölge, içerik ailesi, neden önerdiğinin kısa özeti, izleyicinin sorusu, kanca ve dayandığı kimlikler, içerik planı, eksik veri, şablon ve parametreler (ya da yeni şablon gerektiği) ve kısa bir kapak fikri.

==================================================
EK C — docs/KONSEPT.md'nin sonuna eklenecek bölüm (aynen)
==================================================
## Ek — Kanal ve içerik planı (kullanıcının tanımı, 8 Ekim 2026; bağlayıcı)

**Kanal yapısı**
- 30A / South Walton tek bir YouTube kanalıdır. Mahalleler (Dune Allen, Gulf Place / Santa Rosa Beach, Blue Mountain, Grayton, WaterColor, Seaside, Seagrove, WaterSound, Seacrest, Alys, Rosemary, Inlet Beach) ayrı kanal değildir; aynı kanalın alt bölgeleri ve video konularıdır.
- İlk etapta kanalın odağı yalnız 30A'dır. Destin, Panama City Beach gibi yakın yerler gerektiğinde karşılaştırma ya da bağlam için kullanılabilir, ana konu olmaz.
- Uzun vadede her mikro-destinasyon kendi uzman kanalıdır (ör. 30A, Napa Valley, Lake Tahoe). Program, veri motoru ve mimari tektir; dışarıdaki yapı: bir mikro-destinasyon = bir uzman kanal.

**30A kanalının içerik aileleri**
1. Bölgesel derin rehberler (omurga): her mahalle için neden seçilir, kim için uygun, ne yapılır, plaj, yemek, ulaşım, masraf, artı ve eksi.
2. Genel planlama: ilk kez gidenler, tatil ne kadara mal olur, arabaya ihtiyaç var mı, plaj erişim sistemi nasıl çalışır, nerede kalınır, kaç gün yeter.
3. Sezon ve zamanlama: en iyi aylar, yaz ve ara sezon, hava, deniz sıcaklığı, kalabalık, kasırga ve yağmur riski, etkinlik dönemleri, fiyatların dönemsel değişimi.
4. Masraf ve bütçe: konaklama, yemek, park, ulaşım, market, günlük bütçe, farklı bütçe seviyelerinde tatil.
5. Deneyim: plaj, bisiklet ve golf arabası, yürünebilirlik, restoranlar, kahvaltı, aileyle yapılacaklar, çiftler, sakin tatil, gece hayatı, açık hava aktiviteleri.
6. Sorun çözen videolar: en sık yapılan hatalar, plaja yakın kalmak gerçekten gerekli mi, kiralık araba şart mı, hangi bölgelerde park sorun olur.
7. Karşılaştırmalar (sonraki tur): Seaside ile Rosemary, Doğu 30A ile Batı 30A, "en iyisi" listeleri, veri destekli sıralamalar.
8. Kendi tarihsel verimizden videolar (ileride): ör. "30A fiyatları sonbaharda gerçekten ne kadar düşüyor?"

**Konu motoru:** Bölge × seyahat kararı × dönem × gezgin tipi. Tek bir mahalle bile tek video değildir; örnek Rosemary Beach: tam rehber, masraflar, arabasız, aileler için, yazın, ekimde, ne yapılır, nerede yenir, plaj erişimi, fiyatına değer mi. Aynı yapı her mahallede tekrar eder; her bölgenin kendi küçük konu evreni vardır.

**İlkeler**
- Konu seçimi yalnız arama hacmine göre yapılmaz; ana sayfa ve önerilen videolardan izlenebilecek, güçlü bir tatil sorusu ya da merak noktası olan başlıklar esastır. Paketleme merak ile gerçek tatil kararını birleştirebilir (ör. "Why People Pay So Much to Stay in Rosemary Beach"), ama içerik ciddi, kaynaklı ve pratik kalır; başlık uğruna videonun özü değişmez.
- Bir konu sırf sayı artsın diye bölünmez; 15–17 dakikalık videoyu doğal biçimde taşıyabilmelidir. Taşımıyorsa ilgili bölge rehberinin içinde kalır.
