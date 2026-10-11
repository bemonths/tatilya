# M17 — Video metni: yazım zinciri, tonlar, ton yönetimi ve program denetimi (GÖREV-15, v0.17.0, şema 17)

## Amaç

İş akışının 4. adımı "Video metni" artık çalışıyor. Seçilen başlık ve video paketiyle program, Claude'u adım adım çağırarak
İngilizce video metnini yazdırır. Her seçilen ton için ayrı bir metin yazılır. Metnin Türkçesi cümle cümle verilir. Program metni
kendi kurallarıyla denetler. Kullanıcı tonları yan yana karşılaştırır ve birini seçer.

Yöntem The Housing Atlas Stüdyo'nun yazım zincirinden (TASARIM 21) 30A'ya uyarlandı. Yöneticinin üç tasarım belgesi
`docs/gorevler/GOREV-15/tasarim/` altındadır: `30A_YAZIM_ZINCIRI.md`, `30A_SES_VE_TONLAR.md` ve `30A_HALKA_TALIMATLARI.md`.

Türkçe düzeltme ve İngilizceye uyarlama ekranı bu görevde yok. Housing Atlas'taki MS1 ekranı orada oturduktan sonra ayrı bir görevde
taşınacak. Metnin veri biçimi bu yüzden Housing Atlas'ın `makale.json`'una yakın kuruldu.

## Yapı

| Dosya | Ne yapar |
|---|---|
| `studio/ai/text_steps.py` | Yedi Claude adımı (adım çerçevesinde), anlam denetimleri |
| `studio/ai/schemas/metin_*.schema.json` | Yedi adımın şeması |
| `studio/ai/tones.py` | Tonlar: liste, ekleme, düzenleme, sürümler, arşiv, varsayılan ton |
| `studio/text/engine.py` | Zincir (`TextService`): sıra, paralel oturumlar, beklemeler, sürdürme, ilerleme |
| `studio/text/store.py` | `text_runs`, `text_sessions`, `text_versions`, `text_selections` okuma ve yazma |
| `studio/text/views.py` | Ekranların verisi: çalışmalar, plan, karşılaştırma, sürüm, dosyalar, seçim |
| `studio/text/document.py` | Metnin verisi (`metin.json`), parçalar, numaralar, son okuma düzeltmeleri, dosyalar |
| `studio/text/marks.py` | Kanıt işaretlerinin cümleye bağlanması |
| `studio/text/split.py` | Cümle bölme (Housing Atlas'tan aynen) |
| `studio/text/digits.py` | İki dilde rakam karşılaştırması (Housing Atlas'tan aynen) |
| `studio/text/numbers.py` | Metindeki sayıların kanıtla karşılaştırılması (toleranslar) |
| `studio/text/audit.py` | Program denetimi (kırmızı ve sarı kurallar, plan denetimi) |
| `studio/migration_v17.py` | Şema 16 → 17 (dört yeni tablo) |
| `studio/web/text.js` | Video metni ekranı, plan, karşılaştırma, sürüm görünümü, İşler panelindeki çubuk |
| `studio/web/tones.js` | Ayarlar → Tonlar ve "Denetim: uyarı ifadeleri" kutusu |
| `studio/destinations/thirty_a_claude/` | `ses_ortak.md`, `tonlar/*.md`, yedi `metin_*.md`, `uyari_ifadeleri.txt` |

Talimat ve ton metinleri GÖREV-15'in eklerinden (Ek A–M ve Ek O) aynen yazıldı. Hepsi destinasyonun klasöründedir. Generic çekirdek
(`studio/text/`, `studio/ai/`) 30A'ya özel metin taşımaz. Profil `studio/destinations/thirty_a.py` içindeki `TEXT` sözlüğüyle sesin,
ton klasörünün, varsayılan tonun, uyarı ifadeleri dosyasının ve yayınlanmış videolar listesinin yerini söyler.

## Zincir

Bir metin çalışması İşler panelinde tek bir iş olarak görünür (iş türü `claude_metin`). Sıra:

1. **Tazelik.** Videonun paketi yoksa ya da verinin son çekiminden eskiyse paket önce kendiliğinden yeniden üretilir ve iş
   günlüğüne yazılır.
2. **Plan.**
   - Planlayıcı (`metin_plan`) planı yazar.
   - Program planı denetler. Pakette olmayan bir kanıt kimliği plan planlayıcıya bir kez geri gider. İkinci planda da varsa
     çalışma hata verir. Öbür bulgular uyarıdır.
   - Plan eleştirmeni (`metin_plan_elestiri`) planı okur. `yeniden_yap` derse plan notlarla birlikte planlayıcıya bir kez geri gider.
     İkinci plan program denetiminden yine geçer ama yeniden eleştirilmez.
   - Plan kesinleşir ve çalışmada saklanır. Ayarlar → Claude'daki "Plandan sonra dur" açıksa çalışma burada durur. Kullanıcı planı
     görür ve "Devam" ile sürdürür.
3. **Her ton için ayrı metin.** Seçilen her ton için sırayla:
   1. bölüm yazıcıları (`metin_bolum`) yan yana çalışır; aynı anda en çok "Aynı anda en çok Claude oturumu" kadar oturum açılır;
   2. birleştirici (`metin_birlestirme`) geçişleri ve yeniden kancaları yazar;
   3. giriş ve kapanış (`metin_giris_kapanis`);
   4. program metni birleştirir ve cümleleri numaralar;
   5. son okuyucu (`metin_son_okuma`) düzeltmeleri önerir, program uygular;
   6. program denetimi;
   7. çevirmen (`metin_ceviri`) Türkçeyi yazar; uzun metin bütün parçalarla 6.000 kelimelik dilimlere bölünür;
   8. program iki dilde rakamları karşılaştırır;
   9. sürüm kaydedilir.
4. Bütün tonlar bitince çalışma "karşılaştırma bekliyor" olur.

**Aynı plan, farklı ses.** Plan bir kez yapılır ve bütün tonlar aynı planı kullanır. "Bu tonla da yaz" var olan bir çalışmanın planıyla
yalnız bir ton daha yazdırır. "Planı yeniden yap" yeni bir metin çalışması açar; eski çalışma ve sürümleri saklanır.

### Talimatın birleşimi

Her oturumda Claude'a giden talimat (`talimat.md`) şu parçaların bu sırayla birleşimidir:

| Adım | ortak.md | ses_ortak.md + ton | Adımın dosyası | Şema |
|---|---|---|---|---|
| Planlayıcı | var | yok (plan tondan bağımsız) | `metin_plan.md` | `metin_plan` |
| Plan eleştirmeni | var | yok | `metin_plan_elestiri.md` | `metin_plan_elestiri` |
| Bölüm yazıcısı | var | var | `metin_bolum.md` | `metin_bolum` |
| Birleştirici | var | var | `metin_birlestirme.md` | `metin_birlestirme` |
| Giriş ve kapanış | var | var | `metin_giris_kapanis.md` | `metin_giris_kapanis` |
| Son okuyucu | var | var | `metin_son_okuma.md` | `metin_son_okuma` |
| Çevirmen | var | var | `metin_ceviri.md` | `metin_ceviri` |

Ton dosyasının ilk satırı `# Ton: <Ad>` başlığıdır; birleşimde tonun metni bu başlıkla birlikte girer. Çalışma kaydı (`calisma.json`)
tonun dosya adını, adını ve SHA-256'sını tutar. Birleşik talimatın kendisi çalışma klasöründe saklandığı için tonun o anki metni de
orada durur.

### Çalışma klasöründeki dosyalar

| Adım | Klasöre konan dosyalar |
|---|---|
| Planlayıcı | `baslik_analizi.md`, `paket_ozeti.md`, `sayilar.csv`, `kanal_plani.md` |
| Plan eleştirmeni | `plan.json`, `baslik_analizi.md`, `paket_ozeti.md`, `sayilar.csv` |
| Bölüm yazıcısı | `plan.json`, `bolum.md` (planın o bölümü, bölümün kanıt satırları, önceki ve sonraki bölümün birer cümlelik özeti) |
| Birleştirici | `bolumler.md`, `plan.json` |
| Giriş ve kapanış | `metin.md` (düz), `baslik_analizi.md`, `yayinlanan_videolar.md` |
| Son okuyucu | `metin.md` (numaralı cümleler), `paket_ozeti.md` |
| Çevirmen | `cumleler.md` (numaralı İngilizce cümleler) |

- `baslik_analizi.md` seçilen adayın analizidir. İçindeki kanıt kimlikleri video paketinin kimlikleridir. Pakette karşılığı olmayan bir
  kimlik "(pakette yok: …)" diye yazılır.
- `paket_ozeti.md`, video paketinin yazar özetidir; Claude'a başındaki "Video" bölümü olmadan verilir. O bölüm başlık önerisinin kaynak
  paketlerindeki kimlikleri listeler. Bu kimlikler video paketinin kimlikleriyle karışmasın diye bölümün yerine tek satır konur:
  analiz `baslik_analizi.md`'dedir ve oradaki kimlikler bu özetin kimlikleridir. Böylece Claude tek bir kimlik dizisi görür.
- `yayinlanan_videolar.md` kanalın yayınlanmış videolarıdır; ilk videoda "Henüz yayınlanmış video yok." yazar.
- Düzeltme ya da yeniden deneme turunda görev metnine önceki çıktı (`onceki_cikti.json`) ve dönüş sebebi eklenir.

Her oturumun klasörü mevcut düzendedir: `<veri>/claude/<video kimliği>/<adım>/<oturum kimliği>/` (girdiler, `talimat.md`, şema,
`gorev.md`, akış, çıktı, çalışma kaydı). Metin çalışmasının kendi ara dosyaları `<veri>/metin/<video>/calismalar/<çalışma>/` altındadır.

### Başlangıç modeli ve eforu (Ayarlar → Claude)

| Adım | Model | Efor |
|---|---|---|
| Planlayıcı | opus | high |
| Plan eleştirmeni | opus | medium |
| Bölüm yazıcısı | opus | high |
| Birleştirici | opus | medium |
| Giriş ve kapanış | opus | high |
| Son okuyucu | opus | medium |
| Çevirmen | sonnet | medium |

Model adları aile takma adlarıdır (o ailenin en yeni sürümü). İlk gerçek denemede ölçülüp gözden geçirilecek.

## Hatalar, beklemeler ve sürdürme

- **Oturum sınırı.** Ayarlar → Claude → "Aynı anda en çok Claude oturumu" (1–6, varsayılan 3). Bölüm yazıcıları bu sınırla yan yana
  çalışır.
- **Başka Claude çalışması yok.** Metin çalışması sürerken başlık önerisi, başlık değerlendirmesi ve kullanım panelinin "Yenile"
  düğmesi çalışmaz: "Bir video metni çalışması sürüyor; bitmesini bekleyin." Başlık çalışması sürerken de metin çalışması başlamaz.
- **Geçersiz cevap.** Şemaya ya da anlam denetimine uymayan çıktı, hatalarıyla ve önceki çıktıyla bir kez yeniden istenir. Yine olmazsa
  çalışma "duraklatıldı" olur; "Devam" o adımı yeniden başlatır.
- **Geçici hata.** Zaman aşımı, ağ hatası, Claude'un 5xx ya da 529 hatası, sınır bilgisi taşımayan 429 ve sonucu gelmeden kesilen oturum
  adımın hatası sayılmaz. 1, 5 ve 15 dakika beklenip yeniden denenir; yine olmazsa çalışma durur ve "Devam" bekler.
- **Kullanım sınırı.** Ayarlar → Claude'da iki eşik var: 5 saatlik pencere (varsayılan %90) ve haftalık pencere (varsayılan %95).
  - Her oturumdan önce son kullanım ölçümüne bakılır. Eşik geçilmişse ya da Claude "kullanım sınırına ulaşıldı" derse yeni oturum
    açılmaz; çalışan oturumlar biter ve çalışma bekler (durum "kullanım sınırı bekleniyor").
  - Sıfırlanma anı biliniyorsa ve gelecekteyse o andan 2 dakika sonrasına kadar beklenir; bilinmiyorsa 5, 10, 20, 40 ve 60 dakika
    (sonra hep 60).
  - İşler panelinde "Claude kullanım sınırı: <saat>'te kendiliğinden sürecek." yazar. Süre gelince çalışma kendiliğinden sürer.
    Beklemeden sonraki ilk oturum, ölçüm yenilenmemiş olsa da açılır (deneme oturumu).
  - "Devam" beklemeden yeniden dener.
- **Durdur, İptal et ve programın kapanması.** Çalışan oturumlar kesilir, yarım kalan oturum sonuç yazmaz. "Durdur" ya da İşler
  panelindeki "İptal et" ile çalışma "duraklatıldı" olur. Program kapanırsa açılışta çalışma "yarıda kaldı" görünür; işin mesajı da
  "Program kapanırken yarıda kaldı; “Devam” kalan adımları çalıştırır." olur. Kapanma bekçisi metin çalışmasını iş sayar ve bitmesini
  bekler.
- **Sürdürme.** Biten her oturumun çıktısı hemen saklanır. "Devam" biten oturumları (aynı adım, ton, parça ve tur) yeniden
  çalıştırmaz; yalnız kalanları çalıştırır.

**İlerleme.** Plan yaklaşık %15'tir; kalan pay tonlara, tonun içinde adımlara bölünür. Çubuğun altında aşamanın metni ("Araştırmacı dost
(1/2 ton) · bölümler 4/6 bitti"), geçen süre ve tahmini kalan süre yazar. Tahmin, aynı adımın önceki başarılı oturumlarının ortanca
süresinden hesaplanır; ölçüm yoksa başlangıç değerleri kullanılır. Kullanım sınırı beklemesinde aşamanın metni durur, altına bekleme
satırı gelir.

## Metnin verisi ve sürümler

**`metin.json`** (sema 1, Housing Atlas `makale.json`'a yakın):
- `parcalar`: `giris`, `bolum-N`, `gecis-K`, `kapanis` (türleri giris, bolum, gecis, kapanis; yeniden kanca bir geçiş parçasıdır).
  Sıra: giriş, planın sırasıyla bölümler, her bölümden sonra yeniden kancaları ve sonraki bölüme geçiş, en sonda kapanış.
- Her parçada `paragraflar` (`<parça>-p<i>`), her paragrafta `cumleler`: `no` (bütün metin boyunca tek sıra), `en` (temiz, işaretsiz),
  `tr`, `kanitlar` (cümlenin kanıt kimlikleri), `uyarilar` (`denetim` seviyesi ve kuralıyla, `cevirmen`, `rakam`, `son_okuma`).
- `terimler` (en, tr, açıklama) ve `surum_bilgisi`: numara, zaman, tonun dosyası, adı ve SHA-256'sı, plan, her adımın oturumu (model,
  efor, süre, bedel karşılığı), kelime ve cümle sayısı, denetimin sayıları, son okuyucunun düzeltmeleri.

**Kanıt işaretleri.** Yazıcılar bilgi taşıyan her cümlenin sonuna kanıt kimliğini köşeli parantezle koyar ("… about $7,200 [K0123].").
İşaretler cümle bölmeden önce çıkarılır; işaret noktanın hangi yanında olursa olsun ait olduğu cümlede kalır. Temiz İngilizce cümlede
işaret yoktur.

**Son okuma.** Düzeltmeleri program uygular. Düzeltilmiş cümle eski cümlenin bütün kanıt işaretlerini korumalıdır (pakette olan yeni
kimlik ekleyebilir); korumazsa düzeltme uygulanmaz ve cümlede uyarı olarak kalır. Birden çok cümleye bölünen düzeltme yeniden bölünür,
numaralar baştan verilir.

**Çeviri.** Her İngilizce cümlenin numarasıyla bir Türkçesi olmalıdır; eksik ya da fazla numara geçersiz cevaptır. Sonra iki dilde
rakamlar karşılaştırılır (Housing Atlas `digits.py`); tutmayan cümleye "rakam" uyarısı düşer.

**Sürümün dosyaları** (`<veri>/metin/<video>/surumler/<numara>/`):
`metin.json`, `metin_EN.md`, `metin_TR.md`, `seslendirme_EN.txt` (yalnız okunacak metin: başlık, işaret ve numara yok),
`metin_EN_kanitli.md` (cümle numaraları ve kanıt kimlikleriyle), `denetim.md` ve `denetim.json`.

**Saklama ve seçim.** Metin çalışmaları, oturumlar ve sürümler saklanır; hiçbiri silinmez. Sürüm numaraları video başınadır.
Karşılaştırma ekranındaki "Bu tonla devam et" sürümü videonun seçilmiş metni yapar. Seçim değiştirilebilir; eski seçimler kayıtta kalır
(`text_selections`, en yeni satır güncel seçimdir).

## Şema 17

| Tablo | İçerik |
|---|---|
| `text_runs` | Videonun metin çalışması: durum (running, waiting_limit, paused, interrupted, awaiting_comparison, error), tonlar, paket, kesin plan, zincirin durumu (`state`), sebep ve metni, bekleme sonu, "Planı yeniden yap"ta önceki çalışma |
| `text_sessions` | Zincirin her Claude oturumu: adım, ton, parça, tur, deneme, durum (running, done, invalid, failed, transient, limit, canceled), klasör, model, efor, ölçümler, sorunlar |
| `text_versions` | Bir tonun yazılmış metni: video başına numara, ton dosyası, adı ve SHA-256'sı, klasör, kelime ve cümle sayısı, kırmızı ve sarı bulgu, bedel karşılığı, token, süre, `metin.json`'un SHA-256'sı, paket |
| `text_selections` | "Bu tonla devam et" kayıtları |

Geçiş yalnız ekler; var olan hiçbir şey değişmez. Uygulama geçişten önce kendi yedeğini alır (`data/backups/studio-v16-*.sqlite3`).

## Tonlar

**Ses ve ton.** Anlatıcının sesi (`ses_ortak.md`) bütün tonlarda aynıdır: dürüstlük, kanıt, dil kuralları. Ton, anlatıcının kişiliğini
birkaç cümleyle anlatan kısa bir metindir. Başlangıçta beş ton var: Araştırmacı dost (varsayılan), Belgesel anlatıcı, Hikâye
anlatıcısı, Pratik planlayıcı ve Vlogger.

**Ton dosyası.** `studio/destinations/thirty_a_claude/tonlar/<dosya>.md`; ilk satır `# Ton: <Ad>`, bir boş satır, sonra tonun metni.
Programda tonun adı bu başlıktan okunur.

### Ayarlar → Tonlar

Kullanıcı tonları görev gerekmeden programın içinden yönetir. Talimat düzenleyicinin ilkeleri aynen geçerlidir:
- **Tek kaynak** depodaki dosyadır. Kullanıcının eklediği ya da değiştirdiği ton dosyaları depodaki klasöre yazılır ve git'te
  commit edilmemiş değişiklik olarak görünür. Bu bilerek böyledir: her görevin başında Claude Code bunları kaybetmeden commit eder
  (talimat dosyalarındaki gibi; `CLAUDE.md`).
- **Değişiklik denetimi:** Dosya açıldıktan sonra diskte değiştiyse kayıt reddedilir (SHA-256).
- **Sürüm geçmişi:** Her kayıttan önce önceki hâl `<veri>/claude/ton_gecmisi/<dosya>/<zaman>.md` içinde saklanır; "Bu sürüme dön"
  eski hâli yeni bir kayıt olarak yazar.

Bölümde şunlar var:
- **Liste:** tonun adı ve dosyası, metninin ilk satırı (en çok 160 karakter), son değişiklik, varsayılan olup olmadığı, kaç metin
  sürümünde kullanıldığı; "Düzenle", "Sil", "Varsayılan yap".
- **Yeni ton:** "Tonun adı" ve "Tonun metni". Kullanıcı Markdown başlığı yazmaz; program başlığı kendisi yazar.
  - Ad boş olamaz, en çok 40 karakterdir, başka bir tonun adıyla aynı olamaz.
  - Dosya adı addan kurulur: ı→i, ş→s, ğ→g, ü→u, ö→o, ç→c (öbür aksanlar atılır), küçük harf, harf ve rakam dışındaki karakterler `_`.
    Dosya varsa sonuna sayı eklenir.
  - Metin boş olamaz, en çok 6.000 karakterdir. 1.200 karakteri geçerse kayıt yapılır ve bir not çıkar: "Ton metni uzun. Kısa ve niyet
    anlatan metinler genellikle daha iyi sonuç verir."
- **Düzenle:** ad ve metin değişir; dosya adı değişmez, yalnız başlık satırı değişir. Böylece eski sürümler ve kayıtlar aynı tonu gösterir.
- **Sil:** onay sorulur ("Bu ton arşive taşınacak; istediğiniz zaman geri alabilirsiniz."). Dosya
  `<veri>/claude/ton_arsivi/<dosya>-<zaman>.md` içine taşınır; hiçbir şey silinmez. Silinmiş tonla yazılmış sürümler yerinde kalır ve
  ton adlarıyla görünür. Son ton silinemez.
- **Arşiv:** ayrı liste; "Geri al" tonu klasörüne döndürür (dosya adı doluysa sonuna sayı eklenir).
- **Varsayılan ton:** `ayarlar.json` → `varsayilan_ton` → destinasyon → dosya adı. Başlangıçta "Araştırmacı dost". Varsayılan ton
  silinirse listedeki ilk ton varsayılan olur ve ekranda söylenir.
- **Denetim: uyarı ifadeleri** kutusu bölümün altındadır (aşağıda).

Ayarlar → Talimatlar listesinde tonlar görünmez; anlatıcının sesi ("Anlatıcının sesi (bütün tonlarda aynı)") ve yedi `metin_*.md`
dosyası görünür. Uyarı ifadeleri dosyası da talimat listesinde değil, Tonlar bölümünün altındadır.

## Program denetimi

Denetim Claude'a verilmez. Yazılan her sürüm denetlenir; rapor sürümle saklanır (`denetim.md`, `denetim.json`). Bulgular cümlelere
bağlanır ve ekranda cümlenin yanında kırmızı ya da sarı işaret olarak görünür. Denetim kimseyi durdurmaz: sürüm kaydedilir, kırmızı
bulgu sayısı karşılaştırma ekranında görünür.

**Kırmızı (bilgiyi yanlış söyler).** Bloklarla ilgili kurallar kanıt bloklarının kullanım notlarından gelir (`studio/evidence/blocks.py`
`USAGE`); her biri kodda tanımlı ve testli:
- mesafe (M13): "walking distance", "walkable", "a short walk", "minute walk", "minutes away", "minute drive" …;
- fiyat (M11): "a week costs", "a week in … costs", "costs about $… a week", "per week it costs";
- envanter (M10): "full inventory", "full list", "complete list", "every rental", "all the rentals", "there are … homes in";
- iklim (M8): "30A's climate", "the climate in 30A", "climate of 30A";
- restoranlar (M12): "best restaurant", "the best place to eat", "most popular", "cheapest restaurant";
- trafik (M9): "traffic jam", "gridlock", "bumper-to-bumper", "takes … minutes to get";
- kaynak durumu (M9): işaret, durumu `dogrulanamadi` olan bir referans satırını gösteriyor;
- pakette olmayan kimlik;
- sayılar: sayı içeren cümlede işaret yok ya da sayı, işaretlerinin değerlerinden hiçbiriyle tutmuyor.

**Sarı (dikkat ister).**
- küçük örnek: işaret küçük örneklemli bir hücreyi gösteriyor ve cümle iki mahalleyi karşılaştırıyor;
- kaynak sorusu: "no public beach access" o cümlede ya da bir önceki cümlede kaynak adı olmadan (son okuyucuya ve Kontrol adımına not);
- ses: `uyari_ifadeleri.txt`'deki ifadeler (büyük-küçük harfe duyarsız, kelime sınırında; "I" yalnız büyük harfle ve tek kelime olarak);
- uzunluk: bütün metin 2.000 kelimeden az ya da 2.800'den çok (hedef 2.200–2.500); bir bölüm bütçesinden %25'ten fazla sapıyor.

**Rakam ve yuvarlama** (`studio/text/numbers.py`). Rakamla yazılmış sayılar ve kelimeyle yazılan yaygın sayılar ("seven thousand",
"two and a half million", "a third", "half", "ten percent") okunur. "30A", "I-10", "Highway 98", "County Road 393" gibi adlar sayı
sayılmaz. Her sayının türü kendi kelimelerinden çıkar (para, yüzde, sıcaklık, saat, yıl, sayım, sayı); "about", "around", "nearly"
gibi bir kelime önündeyse sayı yaklaşıktır.
- Para ve sayılar: kanıt değeri ya da konuşma dilindeki yuvarlaması (1 ya da 0,5; 10, 50, 100, 500, 1.000; iki anlamlı basamak);
  "about" varsa ±%3 de tutar. $7,223 → "about $7,200" ve "about $7,000" tutar; "$7,500" tutmaz.
- Yüzde: ±0,5 puan; kesir ±3 puan ("a third" %33 için). %7.1 → "about 7 percent" tutar.
- Sıcaklık: ±1 °F (ya da °C). 84.2 °F → "84 degrees" tutar.
- Sayım (gün, ilan, fırtına …): tam olarak; "about" varsa sayı gibi. 87 ilan → "about 90 listings" tutar, "90 listings" tutmaz.
- Yıl ve saat: aynı yıl ya da saat kanıtta geçmeli.

**Plan denetimi.** plan.json'daki her kanıt kimliği pakette olmalı (yoksa plan bir kez geri döner); her kavramın bir bölümü olmalı; yan
yana iki bölüm aynı biçimde açılmamalı; bölüm bütçelerinin toplamı 1.900–2.300 kelime olmalı.

**Uyarı ifadeleri dosyası.** `studio/destinations/thirty_a_claude/uyari_ifadeleri.txt`, her satırda bir ifade; Ek O'daki listeyle başlar.
Ayarlar → Tonlar'ın altındaki "Denetim: uyarı ifadeleri" kutusundan düzenlenir; talimat düzenleyicinin kayıt ve sürüm kurallarına uyar
(geçmiş `<veri>/claude/talimat_gecmisi/`).

## Ekranlar

**Video metni adımı** (`#adim/metin`). En üstte "Sıradaki iş" satırı. Altında:
- ton seçimi: onay kutuları, varsayılan ton işaretli, her tonun yanında metninin ilk cümlesi, "Tonları yönet" bağlantısı;
- "Metni yaz" düğmesi; paket yoksa ya da eskiyse altında "Paket önce yeniden üretilecek" yazar;
- metin çalışmaları: tarih, tonlar, durum (ve sebebi), kullanım (oturum, süre, token, bedel karşılığı), sürümler; duraklatılmış ya da
  yarıda kalmış çalışmada "Devam", çalışan ya da bekleyen çalışmada "Durdur"; "Planı göster", "Karşılaştır", "Bu tonla da yaz" (ton
  listesiyle) ve "Planı yeniden yap";
- Türkçe düzeltme ekranının bu görevde olmadığını söyleyen kısa not.

**Plan** (`#adim/metin/plan/<çalışma>`): bölümler, tek fikirleri, bütçeleri, açılış biçimleri, kavramların yeri, yeniden kancalar, vaat
kontrolü, program uyarıları ve eleştirmenin notları; salt okunur.

**Karşılaştırma** (`#adim/metin/karsilastirma[/<çalışma>]`; çalışma verilmezse videonun bütün sürümleri): tonlar yan yana sütunlarda, satırlar parçalar (giriş, bölümler, geçişler, kapanış);
sütun çoksa yatay kaydırma. Türkçe önde; "İngilizce" düğmesi sütunları İngilizceye çevirir, "Alt alta" ikisini birlikte gösterir.
Sütun başında tonun adı, kelime sayısı, tahmini süre (kelime/150 dakika), kırmızı ve sarı bulgu sayısı, harcanan kullanım (token,
bedel karşılığı) ve süre. Düğmeler: "Bu tonla devam et", "Tek göster"; üstte "Bu tonla da yaz".

**Sürüm** (`#adim/metin/surum/<sürüm>`): numaralı cümleler, İngilizce ve Türkçe yan yana; kanıt kimlikleri cümlenin üzerine gelince
görünür; denetim bulguları ve çevirmen uyarıları cümlenin yanında; terim listesi ve denetim raporunun tamamı; İngilizce, Türkçe,
seslendirme, kanıtlı İngilizce ve denetim raporu indirmeleri.

**İş akışı.** "Video metni" adımının durumu kayıtlardan hesaplanır (`studio/workflow.py` `text_step`):

| Durum | Ne zaman | "Sıradaki iş" |
|---|---|---|
| bekliyor | video yok ya da paket yok | Önce paket üretilmeli. |
| hazır | çalışma yok | Ton seç ve "Metni yaz"a bas. |
| çalışıyor | çalışma sürüyor ya da kullanım sınırını bekliyor | ilerleme İşler panelinde; beklemede bekleme satırı |
| duraklatıldı / hata | son çalışma durdu, yarıda kaldı ya da hata verdi | sebep ve "Devam" |
| onay bekliyor | sürümler var, seçim yok | Karşılaştırma ekranında tonları karşılaştır ve "Bu tonla devam et" de. |
| tamamlandı | seçim var | seçilen metin ve ton; sonraki adım Kontrol (henüz kurulmadı) |
| eskidi | seçilen sürümden sonra veri yeniden çekildi ve paket değişti | bilgi olarak |

**İşler paneli.** Metin çalışmasının çubuğu, aşamanın metni, geçen ve tahmini kalan süre; beklemede "Bekliyor" etiketiyle bekleme satırı.

**Ayarlar → Claude.** Yedi yeni adımın modeli, eforu ve tur sınırı; "Video metni çalışması" bölümünde oturum sınırı, iki eşik ve
"Plandan sonra dur".

## API

| Uç | İş |
|---|---|
| `GET/POST /api/videos/{id}/metin` | ekranın verisi (tonlar, çalışmalar, sürümler, seçim) / metin çalışması başlat (`{"tonlar": [...]}`) |
| `GET /api/videos/{id}/metin/karsilastirma?calisma=` | karşılaştırma (bir çalışmanın ya da videonun bütün sürümleri) |
| `GET /api/metin/calismalar/{id}` | çalışma, plan, oturumlar, sürümler |
| `POST /api/metin/calismalar/{id}/devam`, `/durdur` | sürdür, durdur |
| `POST /api/metin/calismalar/{id}/ton`, `/yeniden-planla` | "Bu tonla da yaz" (`{"ton": ...}`), "Planı yeniden yap" |
| `GET /api/metin/surumler/{id}`, `/dosya/{en,tr,seslendirme,kanitli,denetim}` | sürüm görünümü, indirmeler |
| `POST /api/metin/surumler/{id}/sec` | "Bu tonla devam et" |
| `GET/POST /api/tonlar`, `GET/PUT/DELETE /api/tonlar/{dosya}` | tonlar |
| `POST /api/tonlar/{dosya}/varsayilan`, `GET /api/tonlar/{dosya}/surumler/{s}`, `POST …/geri-don` | varsayılan, sürümler |
| `POST /api/ton-arsivi/{id}/geri-al` | arşivden geri al |

## Housing Atlas'tan taşınanlar

- `atlas/article/split.py` (cümle bölme) ve testleri aynen; davranış değiştirilmedi (`tests/test_text_split.py`).
- `atlas/article/digits.py` (iki dilde rakam karşılaştırması) aynen.
- `makale.json` biçimine yakın veri (`metin.json`): parça, paragraf, numaralı cümle, uyarılar, terimler, sürüm bilgisi.
- Çeviri dilimleri: bütün parçalarla, en çok 6.000 kelime.
- Geçici hata beklemeleri (`atlas/kesif/engine.py`) ve kullanım sınırı beklemesi (`atlas/kesif/limits.py`), daha sade.

Bilerek değiştirilenler:
- Housing Atlas metni içe aktarıp böler; burada parçaları program kurar (plan, bölümler, geçişler). `parse_article` taşınan testlerle
  birlikte duruyor ama zincir onu kullanmıyor.
- Kanıt işaretlerinin bölmeden önce cümleye bağlanması (`marks.py`) bu projeye özgüdür; bölücünün kendisine dokunulmadı.
- Metnin sayılarının kanıtla karşılaştırılması (`numbers.py`) yenidir; `digits.py`'nin rakam okuma yöntemini temel alır, kelimeyle
  yazılan sayıları ve türleri de okur.
- Tek işçili Claude yapısı, metin çalışmasının kendi içinde paralel oturum açabileceği biçimde genişletildi; başka Claude çalışmasıyla
  aynı anda çalışmaz.

## Testler

`tests/test_text_split.py` (Housing Atlas'ın testleri), `tests/test_text_audit.py` (her kırmızı kural, `dogrulanamadi`, küçük örnek,
uyarı ifadeleri, "I", rakam toleransları, uzunluk ve plan), `tests/test_text_document.py` (işaretler, sıra ve numaralar, son okuma,
çeviri ve rakamlar, dosyalar, uzun metnin dilimleri), `tests/test_tones.py` (ton yönetimi), `tests/test_text_chain.py` (zincir, sürdürme,
beklemeler, kapanma, seçim, geçiş), `tests/test_text_workflow.py` (iş akışındaki bütün durumlar), `tests/frontend.test.mjs` (GÖREV-15
testleri). Testlerde gerçek Claude çağrılmaz: `tests/fake_claude.py` yeni adımları `tests/fake_claude_text.py` ile tanır ve şemaya uyan,
kanıt işaretli çıktı yazar; `FAKE_CLAUDE_TEXT` ile geçersiz cevap, geçici hata, kullanım sınırı, planda bilinmeyen kimlik, eleştirmenden
dönüş, son okumada işaret kaybı ve çeviride eksik numara canlandırılır; `FAKE_CLAUDE_SCENARIO=slow` paralellik ve kesme içindir. Saat
taklit edilir (`FakeClock`), beklemeler gerçekte beklenmez.

## Sınırlar

- Gerçek Claude ile hiç metin yazılmadı (GÖREV-15'te yalnız sahte claude). Modeller, eforlar, süreler ve bedel ilk gerçek denemede
  ölçülecek; tahmini kalan süre o zamana kadar başlangıç değerlerinden gelir.
- Türkçe düzeltme ve İngilizceye uyarlama ekranı yok (Housing Atlas MS1'den ayrı bir görevde taşınacak).
- Denetim kurallar listesidir; listede olmayan bir yanlışı bulmaz. Kontrol adımı (5. adım) henüz kurulmadı.
- Kelimeyle yazılan küçük sayılar ("two neighborhoods") okunmaz; sayıların türü cümlenin kelimelerinden tahmin edilir.
- `yayinlanan_videolar.md` profildeki listeden gelir; bugün boştur.
