# GÖREV-13 raporu — programın içinde Claude, konu ve başlık önerisi

Tarih: 10 Ekim 2026 · Dal: `gorev-13-claude-baslik` · Uygulama 0.15.0 · Şema 15

## Kısaca

- main, GÖREV-12'nin son commit'ine (`a854311`) alındı; etiket konmadı. main CI başarılı.
- Program artık bilgisayardaki Claude Code'u arka planda çağırıyor. Çalıştırıcı The Housing Atlas Stüdyo'dan taşındı.
- Ayarlar'da yeni bir "Claude" bölümü var: model, efor ve tur sınırı buradan seçiliyor.
- Yeni "Videolar" ekranından konu ve başlık önerisi alınıyor. Öneriler onay ekranında önce liste olarak görünüyor; bir başlığa tıklanınca ayrıntısı açılıyor.
- Seçilen başlık bir video kaydı oluyor. Kaydın kanıt paketi, başında videonun analiziyle üretiliyor.
- Gerçek veride iki gerçek çalışma yapıldı: 30A geneli 11 aday, Rosemary Beach 10 aday. İkisinde de doğrulama sorunu yok. İkisi de onay bekliyor; başlık seçilmedi.

## Adım 1 — main ve küçük düzeltmeler

**Konumlar ve CI**

| | Konum | CI |
|---|---|---|
| GÖREV-12 dalı son commit | `a85431167e1ccacd88467dae539e1f46aa7817eb` | 38061251798 başarılı |
| main (fast-forward, push) | `a85431167e1ccacd88467dae539e1f46aa7817eb` | 38066733163 başarılı |
| Etiket | konmadı; son etiket `v0.14.0` → `9adc235` | — |

`gorev-13-claude-baslik` dalı bu commit'ten açıldı.

**1b. Yönetici kararları**
- Yazar özetinin 110 KB olması kabul.
- Yayından önce kontrol listesi aynen kaldı.

**1c. Küçük düzeltmeler** (ayrı commit `4291388`)
- **Restoran saatleri:** sitenin boş bıraktığı günler artık yazılmıyor. ", Tu 17:00-21:00, …" yerine "Tu 17:00-21:00, …" yazıyor.
  - Gerçek veride 4 restoranı etkiliyor: Edward's, Grayton Seafood, Raw & Juicy, Ticheli's.
  - Raw & Juicy ile Ticheli's'in saat metni yalnız virgüllerden ibaretti (", , , , , ,"). Bunlar artık "saat bilgisi yok" sayılıyor; saat bilgisi olan restoran sayısı okumada 91'den 89'a iniyor.
  - Kayıtlı veri değiştirilmedi; düzeltme okurken yapılıyor. Yeni çekimlerde de baştan böyle yazılıyor.
- **Havalimanı uzaklıkları:** referans tablosunda değer artık mil (ECP 13.4, VPS 17.9, PNS 55.6). km karşılığını kanıt paketi dönüşüm olarak yanına yazıyor; etiket "bizim hesabımız" olarak kaldı.
  - Hesap FAA koordinatlarından yeniden yapıldı ve eski sonuçla aynı çıktı (ör. ECP 21,511 km = 13,366 mil).
  - İfadelerden km çıkarıldı. Böylece iki farklı km yazılmıyor: eski ifade 21.5, 13.4 milin dönüşümü 21.6 km.
  - Kural genel: mil birimli her referans değeri km dönüşümünü alıyor (Timpoochee 19 mil = 30.6 km gibi).
- **Kanıt paketi listesi:** mahalle, seçili şablondan bağımsız olarak adıyla görünüyor ("Rosemary Beach").

## Adım 2 — Claude çalıştırıcısı

`studio/ai/runner.py` ve `claude_info.py` Housing Atlas'tan taşındı.

**Komut:** `claude -p --output-format stream-json --verbose --append-system-prompt-file <talimat> --tools <araçlar> --allowedTools <kurallar> --permission-mode dontAsk --max-turns <n> --setting-sources "" --strict-mcp-config --disable-slash-commands --model <m> --effort <e>`. Görev metni standart girdiden veriliyor. Çalışma klasörü o çalışmanın klasörü.

**Yalıtım**
- Kullanıcının ve projenin ayarları, kancaları, CLAUDE.md dosyaları, MCP sunucuları, becerileri, claude.ai bağlayıcıları ve otomatik bellek yüklenmiyor.
- Ortam değişkenleri: `ENABLE_CLAUDEAI_MCP_SERVERS=0`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, `DISABLE_AUTOUPDATER=1`.
- Uygulama bir Claude Code oturumunun içinden açılmışsa o oturumun değişkenleri alt sürece geçmiyor.
- Abonelik kullanılıyor. `ANTHROPIC_API_KEY` tanımlıysa Ayarlar'da, Videolar ekranında (çalıştırmadan önce onay sorusu) ve iş günlüğünde Türkçe uyarı çıkıyor.

**Talimat ve kayıt**
- Birleşik talimat: ortak talimat + adımın talimatı + adımın şeması.
- Her çalışma talimat dosyalarının ve şemanın SHA-256 karmalarını kaydına yazıyor.

**İzleme ve hatalar**
- Akış satır satır okunup İşler paneline Türkçe yazılıyor: "Tur 1/30 · Okuyor: secim.md", "Tur 4/30 · Yazıyor: baslik.json", reddedilen araç, düşünme süresi, kullanım sınırı uyarısı.
- Akışın tamamı `akis.jsonl`'a kaydediliyor.
- Kayıtta oturum kimliği, süre, tur, araç çağrıları, token'lar ve maliyet karşılığı var.
- Zaman aşımı, tur sınırı, kullanım sınırı, oturum açık değil, eski sürüm ve desteklenmeyen model–efor Türkçe mesajla gösteriliyor.

**Çalışma kuralları**
- Aynı anda tek Claude çalışması yürüyor.
- Uygulama çalışma sürerken kapanırsa Claude durduruluyor ve çalışma "hata: Uygulama kapanırken yarıda kaldı." oluyor. Sert kapanışta bu, bir sonraki açılışta yazılıyor.

## Adım 3 — Ayarlar → Claude

- Ekranda şunlar var:
  - bulunan programın yolu ve sürümü (bu bilgisayarda `…\npm\claude.CMD`, 2.1.284),
  - API anahtarı uyarısı,
  - genel varsayılan model ve efor,
  - adım başına model, efor ("Genel varsayılan" seçeneğiyle) ve en fazla tur.
- Listeler Housing Atlas'takiler.
- Adım listesinde şimdilik "Konu ve başlık" var. Başlangıç ayarı Opus 5.5, yüksek efor, 30 tur.
- Ayarlar `data/ayarlar.json`'da duruyor; gizli bilgi yok. Gerçek veride ayar değiştirilmedi, dosya hiç oluşmadı (varsayılanlar kullanıldı).

## Adım 4 — Adım çerçevesi, onay ekranı, video kaydı

**Adım tanımı (`studio/ai/steps.py`).** Her adımın parçaları:
- talimat dosyaları (destinasyonda),
- şema (çekirdekte),
- araçlar: yalnız klasörde okuma ve tek JSON dosyasına yazma,
- girdi kurucusu, görev metni, şema ve anlam denetimi,
- Markdown üreticisi (Claude yalnız JSON yazar).

**Çalışma klasörü:** `data/claude/<hazırlık>/<adım>/<çalışma>/`. İçinde girdiler, `talimat.md`, `sema.json`, `gorev.md`, `akis.jsonl`, `baslik.json`, `baslik.md` ve `calisma.json` var. Hiçbir çalışma silinmiyor; yeniden çalıştırma ve düzeltme yeni klasör açıyor.

**Onay ekranı (Videolar)**
- Önce başlık listesi görünüyor: İngilizce başlık, Türkçe karşılık, aile.
- Bir başlık açılınca ayrıntısı görünüyor: neden önerildi, izleyicinin sorusu, kanca ve kanıtları (değerleriyle), içerik planı, eksik veri, şablon ve parametreler, kapak fikri. "Bu başlığı seç" düğmesi bunların altında.
- Altta not alanı, "Düzeltme iste" (yeni oturum; not ve önceki çıktı görev metninde) ve "Reddet".
- Doğrulama sorunları ayrı listeleniyor. Hatalı aday seçilemiyor.

**Video kaydı (şema 15)**
- Yeni tablolar `videos` ve `claude_runs`; `evidence_packs`'e `video_id` sütunu eklendi.
- Seçilen adayın bütün analizi kayda giriyor. Kanca ve plan kanıtları değerleri ve geldikleri paketin kimliğiyle saklanıyor.
- Video kaydından "Kanıt paketi üret" mevcut paket üretimini kaydın şablonuyla çalıştırıyor. Paketin ve yazar özetinin başına başlık, soru, kanca, neden önerildiği ve içerik planı yazılıyor; paket kayda bağlanıyor.
- Her kanıtın yanında yeni paketteki kimliği yazıyor. Değer değiştiyse "değeri farklı", satır yoksa "bu pakette yok" diye açıkça yazılıyor.
- Şablonu olmayan kayıtta düğme kapalı ve "yeni şablon gerekir" yazıyor.

## Adım 5 — Konu ve başlık adımı

**Talimatlar:** `studio/destinations/thirty_a_claude/ortak.md` ve `baslik.md`. Görev metnindeki Ek A ve Ek B'den programla çıkarıldı, bayt bayt aynı.

**Kanal belgeleri**
- Ek C, `docs/KONSEPT.md`'nin sonuna aynen eklendi.
- Kanal araştırması `studio/destinations/thirty_a_claude/kanal_arastirmasi.md` olarak repoya alındı (başlığında 8 Ekim 2026 tarihi var).

**Girdiler**
- `kanal_plani.md`, `kanal_arastirmasi.md`, `secim.md`.
- `veri_ozeti_30a.md` her çalışmada; `veri_ozeti_mahalle.md` yalnız mahalle seçilince.
- `sablonlar.md`, `onceki_oneriler.md`.
- Özetin paketi verinin son çekiminden eskiyse ya da paket başka program ya da profil dosyalarıyla üretildiyse özet yeniden üretiliyor; güncelse aynı paket kullanılıyor.

**Kanıt biçimi:** `{"dosya": "veri_ozeti_30a.md", "kimlik": "K0123"}`. K kimlikleri pakete ait olduğu için hangi özetten geldiği de yazılıyor.

**Anlam denetimleri**
- 8–12 aday olmalı.
- 30A geneli iken en az 4 aile olmalı. Mahalle seçildiyse bütün adaylar o mahalleden, aile seçildiyse o aileden olmalı.
- Her kanıt kimliği verilen özette bulunmalı.
- Kancanın en az bir kanıtı olmalı. İçerik planında en az 5 bölüm olmalı ve her bölüm kanıta dayanmalı.
- Şablon ve parametre geçerli olmalı. Şablon null ise "yeni şablon gerekir" doğru olmalı.
- İngilizce başlık en çok 100 karakter olmalı.
- Başlıklar birbirini ve önceki önerileri tekrar etmemeli; büyük-küçük harf ve noktalama farkı gözetilmiyor.

**Testler:** görev metnindeki 5e listesinin hepsi sahte claude programıyla test edildi; liste "Testler" bölümünde.

## Adım 6 — Gerçek ortam

1. **Geçici deneme** (gerçek verinin kopyası, sahte claude):
   - Ayarlar → Claude bölümünden yol sahte programa çevrildi.
   - Videolar ekranından Rosemary Beach çalışması yapıldı.
   - Onay ekranı açıldı, bir başlık seçildi, video kaydı oluştu.
   - Video kaydından kanıt paketi üretildi; başında video bölümü ve kimlik eşlemesi var.
   - Bu denemede bir hata bulundu ve düzeltildi: veri klasörü göreli yolla verilince talimat dosyasının yolu da göreli kalıyordu.
2. **Geçiş denemesi** (gerçek verinin kopyası):
   - Şema 14 → 15; satır sayıları aynı (165.242).
   - `integrity_check` ok, `foreign_key_check` boş.
   - Yeni tablolar boş; `evidence_packs`'e `video_id` eklendi.
3. **Gerçek veri:**
   - Uygulama kapalıyken `data/` tam yedeği alındı: `work/yedek/20261010-1947/`, 45.415 dosya, SHA-256 ile doğrulandı.
   - Uygulama gerçek veriyle açıldı ve şema 15'e geçti; uygulamanın kendi yedeği `data/backups/studio-v14-…`.
   - Ayarlar varsayılan kaldı.
   - Videolar ekranından sırayla iki çalışma yapıldı. Başlık seçilmedi, düzeltme istenmedi; ikisi de onay bekliyor.
   - Toplayıcı çalışmadı.

### Gerçek veritabanı önce / sonra

| | Önce | Sonra |
|---|---|---|
| Şema | 14 | 15 |
| `integrity_check` | ok | ok |
| `foreign_key_check` | boş | boş |
| Tablo / toplam satır | 61 / 165.242 | 63 / 165.248 |
| `claude_runs` | yok | 2 |
| `videos` | yok | 0 |
| `evidence_packs` | 4 | 6 (iki veri özeti paketi yeniden üretildi) |
| `jobs` | 33 | 35 |
| Diğer tablolar, çekimler (30), kaynaklar | — | değişmedi |

### İki gerçek çalışma

Her iki çalışmada model Opus 5.5 (`claude-opus-5-5`), efor yüksek, Claude Code 2.1.284.

| | 30A geneli | Rosemary Beach |
|---|---|---|
| Süre | 9 dk 1 sn (düşünme 3 dk 47 sn) | 7 dk 33 sn (düşünme 2 dk 57 sn) |
| Tur | 5 | 6 |
| Araç çağrısı | 9 (8 okuma, 1 yazma) | 10 (9 okuma, 1 yazma) |
| Girdi token (yeni + önbellek) | 370.731 | 460.176 |
| Çıktı token | 65.455 | 52.998 |
| Maliyet karşılığı | 2,55 $ | 2,36 $ |
| Reddedilen araç çağrısı | 0 | 0 |
| Aday / doğrulama sorunu | 11 / yok | 10 / yok |
| Şablonu olan / yeni şablon gerekir | 3 / 8 | 7 / 3 |

**30A geneli** (aile hepsi, not boş):

| # | İngilizce başlık | Türkçe karşılık | Aile | Şablon |
|---|---|---|---|---|
| 1 | 30A Florida for First-Timers: Which Town, Which Month and What a Week Costs | İlk kez 30A Florida'ya gidenler için: hangi kasaba, hangi ay ve bir hafta ne tutar | Genel planlama | ilk-video |
| 2 | Which 30A Beaches Are Actually Public? The Law, the Map and Where to Park | 30A'da hangi plajlar gerçekten halka açık? Yasa, harita ve nereye park edilir | Genel planlama | yeni şablon |
| 3 | What a Week on 30A Really Costs: Rental Prices for All 13 Beach Towns, Month by Month | 30A'da bir hafta gerçekte ne tutar: 13 sahil kasabasında ay ay kiralık ev fiyatları | Masraf ve bütçe | yeni şablon |
| 4 | The Best Time to Visit 30A: Weather, Water, Hurricanes, Crowds and Prices by Month | 30A'ya gitmenin en iyi zamanı: ay ay hava, deniz, kasırga, kalabalık ve fiyat | Sezon ve zamanlama | yeni şablon |
| 5 | 30A in Winter: What You Get (and Give Up) When Rentals Cost Far Less | Kışın 30A: kiralar çok daha ucuzken ne kazanırsınız, nelerden vazgeçersiniz | Sezon ve zamanlama | yeni şablon |
| 6 | Do You Need a Car on 30A? Golf Cart Laws, Grocery and ER Distances, and Traffic | 30A'da arabaya ihtiyacınız var mı? Golf arabası kuralları, market ve acil servis mesafeleri, trafik | Sorun çözen videolar | yeni şablon |
| 7 | 30A Beach Rules That Can Cost You $500: Flags, Tents, Dogs, Bonfires and More | 30A'da size 500 dolara mal olabilecek plaj kuralları: bayraklar, çadırlar, köpekler, plaj ateşi ve dahası | Sorun çözen videolar | yeni şablon |
| 8 | Staying in Seaside, the Truman Show Town on 30A: What to Expect | 30A'daki Truman Show kasabası Seaside'da kalmak: neyle karşılaşırsınız | Bölgesel derin rehberler | mahalle-rehberi (seaside) |
| 9 | Why People Pay So Much to Stay in Rosemary Beach, 30A — and What They Get | İnsanlar Rosemary Beach'te kalmak için neden bu kadar ödüyor ve karşılığında ne alıyor | Bölgesel derin rehberler | mahalle-rehberi (rosemary-beach) |
| 10 | East 30A vs West 30A: Beaches, Prices, Groceries and Hospitals Compared | Doğu 30A ile Batı 30A: plajlar, fiyatlar, marketler ve hastaneler karşılaştırması | Karşılaştırmalar | yeni şablon |
| 11 | What Eating Out on 30A Really Costs: Menu Prices Town by Town | 30A'da dışarıda yemek gerçekte ne tutar: kasaba kasaba menü fiyatları | Deneyim | yeni şablon |

**Rosemary Beach** (aile hepsi, not boş):

| # | İngilizce başlık | Türkçe karşılık | Aile | Şablon |
|---|---|---|---|---|
| 1 | Rosemary Beach Has No Public Beach Access. So How Do You Get to the Sand on 30A? | Rosemary Beach'te halka açık plaj erişimi yok. 30A'da kuma nasıl ulaşırsınız? | Sorun çözen videolar | mahalle-rehberi |
| 2 | 30A's Rosemary Beach in November: Uncorked, a Thanksgiving 10K and Roughly Half July's Rent | Kasımda 30A'nın Rosemary Beach'i: Uncorked, Şükran Günü 10K koşusu ve temmuzun yaklaşık yarısı kira | Sezon ve zamanlama | mahalle-rehberi |
| 3 | Rosemary Beach in Summer: What Peak Season on 30A Costs, Feels Like and Risks | Yazın Rosemary Beach: 30A'da yoğun sezonun maliyeti, havası ve riskleri | Sezon ve zamanlama | mahalle-rehberi |
| 4 | Rosemary Beach Without a Car: What's Close, What's Far and the 30A Golf Cart Catch | Arabasız Rosemary Beach: ne yakın, ne uzak ve 30A'daki golf arabası tuzağı | Deneyim | mahalle-rehberi |
| 5 | Eating in Rosemary Beach, 30A: Who Takes Reservations, Who Doesn't and What Dinner Costs | 30A'da Rosemary Beach'te yemek: kim rezervasyon alıyor, kim almıyor ve akşam yemeği ne tutuyor | Deneyim | mahalle-rehberi |
| 6 | Taking Kids to Rosemary Beach, 30A: Bedrooms, Kid Menus, Beach Flags and the Nearest ER | Çocuklarla 30A'da Rosemary Beach: yatak odaları, çocuk menüleri, plaj bayrakları ve en yakın acil servis | Deneyim | mahalle-rehberi |
| 7 | Can You Do 30A's Rosemary Beach on a Budget? The Cheapest Weeks, by the Numbers | 30A'nın Rosemary Beach'i bütçeyle yapılır mı? En ucuz haftalar, rakamlarla | Masraf ve bütçe | mahalle-rehberi |
| 8 | Rosemary Beach vs Seaside on 30A: Prices, Beach Access, Restaurants and Who Each Town Suits | 30A'da Rosemary Beach ile Seaside: fiyatlar, plaj erişimi, restoranlar ve hangi kasaba kime uyar | Karşılaştırmalar | yeni şablon |
| 9 | Rosemary Beach or Inlet Beach on 30A? Beach Access, Rental Prices and Restaurants Compared | 30A'da Rosemary Beach mi Inlet Beach mi? Plaj erişimi, kiralık ev fiyatları ve restoranlar karşılaştırması | Karşılaştırmalar | yeni şablon |
| 10 | Rosemary Beach Was Designed in 1995. What a Planned 30A Town Means for Your Vacation | Rosemary Beach 1995'te tasarlandı. Planlı bir 30A kasabası tatiliniz için ne demek | Bölgesel derin rehberler | yeni şablon |

### İki çalışmanın çıktısını okudum

- **Doğrulama sorunu:** iki çalışmada da yok.
  - Bütün kanıt kimlikleri verilen özetlerde var. Her plan bölümünün kanıtı var. Şablonlar ve parametreler geçerli.
  - Araç izinleri çalıştı: Claude yalnız okudu ve `baslik.json`'u yazdı, reddedilen çağrı yok.
- **Kanıt değerleri:** kancaların metnini dayandıkları değerlerle tek tek karşılaştırdım; söylenen sayılar paketteki değerlerle aynı.
  - Örnekler: Rosemary Kasım haftası 3,727 $ (48 ilan), Temmuz 7,223 $ (91 ilan); Seagrove Ocak 1,885 $; turist vergisinde Temmuz %20, Ocak %2.1; Ekim'de deniz suyu 78.5 °F; acil servise ortanca 13.57 mil.
  - Rosemary 8. adaydaki "12 haftanın hepsinde Rosemary'nin ortancası Seaside'ınkinden düşük" iddiası kanıt olarak yalnız Temmuz'u gösteriyor. Paketten 12 haftayı tek tek kontrol ettim; doğru.
- **Aile dağılımı:**
  - 30A geneli 7 aileye dağıldı: Genel planlama 2, Sezon ve zamanlama 2, Sorun çözen 2, Bölgesel derin rehber 2, Masraf ve bütçe 1, Karşılaştırma 1, Deneyim 1.
  - Rosemary 6 aileye dağıldı.
  - "Kendi tarihsel verimizden" ailesinden aday yok. Claude'un notu: elde tek bir fiyat anlık görüntüsü var.
- **Rosemary'nin 30A bağı:** 10 başlığın hepsinde "30A" geçiyor ("on 30A", "30A's Rosemary Beach", "a Planned 30A Town").
  - Konular mahallenin farklı parçalarına dağıldı: plaj erişimi, Kasım, yaz, arabasız, yemek, çocuklar, bütçe, iki karşılaştırma, kuruluş.
  - Tam rehber önerilmedi. Claude bunu birinci çalışmadaki "Why People Pay So Much…" başlığı zaten kapsadığı için yaptığını notunda yazıyor.
- **Tekrar:** ikinci çalışmanın `onceki_oneriler.md` dosyasında birinci çalışmanın 11 başlığı vardı. Hiçbiri tekrar edilmedi.
- **Şablonsuz öneri:** 30A genelinde 11 adayın 8'i, Rosemary'de 10 adayın 3'ü (iki karşılaştırma ve kuruluş) yeni şablon gerektiriyor.
  - Claude'un önerdiği öncelik: plaj erişimi, haftalık maliyet, en iyi ay. Gerekçesi: rakiplerin boş bıraktığı ve izleyicinin en çok sorduğu konular.
- **Claude'un notlarından dikkat çekenler**
  - Restoran özetinde mahalle sayılarının toplamı 141, bilinen boşluklar notu ise 138 restoran diyor. Bunun kontrol edilmesini öneriyor; bazı restoranlar iki mahalleye düşüyor olabilir.
  - Rosemary Beach'in kendi misafirlerine açık özel plaj erişimleri hakkında elimizde kaynaklı satır yok. Bu boşluk plaj erişimi, aileler ve yaz adaylarını en çok etkileyen eksik veri.
  - K0081 ("özel plaj kalmadı" iddiası, doğrulanamadı) hiçbir adayda kullanılmadı.

## Housing Atlas'tan taşınanlar ve bilerek değiştirilenler

**Aynen taşınanlar**
- Komut ve bayraklar.
- Yalıtım değişkenleri; oturum değişkenlerinin düşürülmesi (`CLAUDE_CODE_GIT_BASH_PATH` ve `CLAUDE_CODE_OAUTH_TOKEN` korunur).
- `claude.cmd` kabuğunun çözülmesi; `.py` sahte program; sürümün her çalışmadan önce okunması.
- Yazma izninin `Edit(...)` kuralıyla verilmesi; çıktı klasörlerinin önceden açılması.
- Akış olaylarının Türkçe satırlara çevrilmesi. Tur, cevap sayısıdır; Claude Code'un `num_turns`'ü yalnız kayda yazılır.
- Ölçüm: süre, düşünme, araç türleri, token'lar, maliyet.
- Hata türleri ve mesajları: sıfırlanma saatiyle kullanım sınırı, tur sınırı, giriş, eski sürüm, `--effort`'u tanımayan sürüm, desteklenmeyen model ve efor.
- Zaman aşımı kuralı: 45 dk ya da tur × 90 sn.
- Model ve efor listeleri ve "Genel varsayılan" mantığı (`resolve_model_effort`).
- Birleşik talimat: ortak + adım + şema.
- Şemanın bilinmeyen alanı reddetmesi; Claude'un yalnız JSON, programın Markdown yazması.
- Onay ekranındaki Seç / Düzeltme iste / Reddet.
- Yarıda kalan çalışmanın açılışta hata olması.

**Bilerek değiştirilenler**

| Değişiklik | Gerekçe |
|---|---|
| Paralel çalışma sınırı (`claude_parallel`) yerine aynı anda tek Claude çalışması | Görev metni 2e. |
| "Düzeltme iste" her zaman yeni oturum açıyor (`--resume` yok); not ve önceki çıktı görev metninde. Housing Atlas'ta analizin düzeltmesi aynı oturumu sürdürüyordu. | Görev metni 4c. Housing Atlas da araştırmada M6c ile buna geçmişti. |
| Bash aracı ve hesap aracı yok; uygulamanın Python'u alt sürecin PATH'ine ve PYTHONPATH'ine eklenmiyor | Bu adımda Claude yalnız okuyup tek dosya yazıyor. |
| Talimat sürümü git içerik karması değil, dosyaların SHA-256'sı (ayrıca depo commit'i) | Görev metni 2c. |
| `jsonschema` paketi eklenmedi; şemaların kullandığı alt kümeyi denetleyen küçük bir denetleyici yazıldı (Türkçe mesajlar; desteklenmeyen anahtar şemada varsa yükleme reddedilir) | Yeni bağımlılık eklememek için. |
| İçerik aileleri ve bölgeler şemaya çalışma sırasında destinasyondan dolduruluyor; çekirdek şemada 30A listesi yok | Mimari sınır: kanal tanımı destinasyonda. |
| İş paneli olarak 30A Studio'nun mevcut iş tablosu ve günlüğü kullanıldı | Uygulamanın kendi iş sistemi. |
| Kalıcı dersler, talimat düzenleyicisi, denetim paketi (zip), otomatik sürdürme taşınmadı | Bu görevde istenmedi. |
| Gizli bilgi maskesi yalnız `sk-ant-…` biçimini kapsıyor | Uygulama başka gizli bilgi tutmuyor. |

## Testler

- Python 768 test (main: 733), frontend 64 test (main: 60). Tam takım art arda 3 kez geçti: üç turda da 768 passed (1 bilinen uyarı: Starlette TestClient / httpx) ve 64/64 frontend.
- Testler gerçek Claude'u çağırmıyor; sahte program `tests/fake_claude.py`.
- `tests/test_claude_runner.py`:
  - komut ve yalıtım bayrakları,
  - ortam değişkenleri ve üst oturum değişkenlerinin düşmesi,
  - npm kabuğunun çözülmesi, sürüm, API anahtarı,
  - Türkçe hata mesajları, akış satırları, zaman aşımı, talimat karmaları,
  - ayarların varsayılanı, "Genel varsayılan", doğrulaması ve saklanması.
- `tests/test_claude_steps.py`:
  - geçerli çıktı; şemaya uymayan, okunamayan ve yazılmayan çıktı,
  - var olmayan kanıt kimliği, kanıtsız bölüm,
  - mahalle özetinin girdiye konması ve başka mahalleye ait adayın reddi,
  - aile seçimine uymayan aday,
  - önceki önerilerin girdiye konması ("seçildi" işaretiyle) ve tekrar eden başlığın reddi,
  - tur sınırı, kullanım sınırı, eski sürüm,
  - düzeltmenin yeni oturum açması,
  - seçimin video kaydını analiziyle oluşturması,
  - ayarlardaki model ve eforun komuta geçmesi ("Genel varsayılan" ve boş değer dahil),
  - yalıtım bayrakları ve ortam değişkenleri, talimat karmaları,
  - tek çalışma kuralı ve iptal; yarıda kalan çalışma,
  - videonun kanıt paketi ve kimlik eşlemesi; şablonsuz kayıt,
  - özet paketinin yeniden kullanılması ve eskiyince yeniden üretilmesi,
  - API anahtarı uyarısı, v14 → v15 geçişi.
- Küçük düzeltmelerin testleri ve önceki geçiş testlerine yeni tablolar eklendi.

## Beklenmedik durumlar

- Geçici denemede bir hata bulundu: veri klasörü göreli yolla verilince Claude'a verilen talimat dosyası yolu da göreli kalıyordu ve sahte program dosyayı bulamadı. Çalışma klasörü artık mutlak yol; gerçek veride sorun çıkmadı.
- Referans çeviri dosyasının satır sonları karışık (başlık CRLF, satırlar LF). Havalimanı satırları bu yüzden metin olarak değiştirildi; yalnız üç satır değişti.
- Belge güncelleme betiği DEVIR 02'deki kanıt paketi API satırını yanlışlıkla sildi. Git'teki aslından geri konuldu.
- Claude Code akışında, haftalık kullanım %35'teyken bile "allowed_warning" bildirimi geliyor. İş günlüğünde "Uyarı: Claude kullanım sınırına yaklaşılıyor · haftalık sınır: %35 kullanıldı" satırı çıkıyor. Housing Atlas'ın davranışı aynı; bildirim Claude Code'dan geliyor.
- Veri özetlerinin paketi, programın kodu ya da profil dosyaları değişince yeniden üretiliyor ("profil karması"). Gerçek veride iki özet de bu yüzden yeniden üretildi; eski GÖREV-12 paketleri yerinde.

## Yöneticinin karar vermesi gereken konular

1. **Hangi yeni şablonlar yazılacak?** 30A genelinde 8, Rosemary'de 3 öneri yeni şablon istiyor. Claude'un önerdiği öncelik: plaj erişimi, haftalık maliyet, en iyi ay. Karşılaştırmalar ve kuruluş hikâyesi de şablon bekliyor.
2. **Bir videonun paketi birden çok şablonun verisini kullanabilsin mi?**
   - Rosemary'nin mahalle-rehberi şablonlu adayları plaj hukuku, golf arabası, okul tatilleri gibi yalnız ilk video paketinde olan satırlara da dayanıyor. Claude bunu notunda yazdı.
   - Bu adaylardan biri seçilip paketi üretilirse o satırlar video bölümünde "bu pakette yok" diye görünecek.
3. **Model listesi.** Housing Atlas'ın listesi aynen alındı (Opus 5.5, Fable 5.1, Sonnet 5, Haiku 4.5). Daha yeni Sonnet 5.5 (`claude-sonnet-5-5`) ve Haiku 5.5 (`claude-haiku-5-5`) listede yok; eklenip eklenmeyeceği yöneticinin kararı.
4. **Restoran sayısı farkı.** Claude'un notu: mahalle toplamı 141, bilinen boşluk notu 138. Bir restoranın birden çok mahalleye düşmesinden olabilir; kontrol edilmesi bir sonraki işe bırakıldı.
5. **Rosemary Beach'in özel plaj erişimleri** için kaynaklı satır yok. Plaj erişimi videosu için önemli bir eksik veri.

Talimat metinlerine dokunulmadı. Önerim yok; iki gerçek çalışmada talimat beklendiği gibi işledi.

## Teslim dosyaları

`docs/gorevler/GOREV-13/`:
- `GOREV.md`, `RAPOR.md`
- `calisma-30a-geneli/` ve `calisma-rosemary-beach/`: her birinde `baslik.json`, `baslik.md`, `gorev.md`, `calisma.json` (akış kaydı hariç)
- Ekran görüntüleri:
  - `ayarlar-claude.png` (Ayarlar → Claude)
  - `videolar-ekrani.png` (Videolar, seçimlerle)
  - `baslik-listesi.png` (Rosemary başlık listesi)
  - `baslik-ayrintisi.png` (bir başlığın açık ayrıntısı)

## Dal CI

DAL_CI
