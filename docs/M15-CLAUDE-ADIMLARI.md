# M15 — Programın içinde Claude: çalıştırıcı, ayarlar, adım çerçevesi, onay ekranı, video kaydı, konu ve başlık adımı

Tarih: 10 Ekim 2026 · Görev: GÖREV-13 · Dal: `gorev-13-claude-baslik` · Şema `15` · Uygulama `0.15.0`

## Amaç

Video için yapılacak her şey programın içinden yapılır (kullanıcı kararı, 10 Ekim 2026). Program arka planda bilgisayardaki Claude Code'u çağırır;
Claude programın verdiği talimatla tek bir işi yapar ve tek bir JSON dosyası yazar. Claude burada kod yazan bir ajan değildir. Akış:

1. Program verilerden kanal konseptine uygun konu ve başlık önerileri çıkarır (bu görev).
2. Kullanıcı uygulamada birini seçer; seçilen başlık bir video kaydı olur (bu görev).
3. Program seçilen başlık için veri paketini kurar (bu görev: kaydın şablonuyla kanıt paketi, başında video analizi).
4. Claude o paketle video metnini yazar (sonraki görev).
5. Program kontrol eder (sonraki görev).

Davranış The Housing Atlas Stüdyo'dan (`C:\Users\1\source\repos\housing-atlas`) taşındı: `atlas/ai/runner.py`, `atlas/claude_info.py`,
`atlas/config.py`, `atlas/ai/stages.py`, `atlas/ai/validate.py`, `tests/fake_claude.py`; gerekçeleri o projenin `docs/KARARLAR.md` M5 ve M5b
bölümlerinde ve `docs/TASARIM.md` Bölüm 6 ve 10'da.

## Yapı

- **Genel çekirdek (`studio/ai/`)** — destinasyondan bağımsız:
  - `claude_info.py`: `claude` programını bulma, sürüm okuma, `ANTHROPIC_API_KEY` uyarısı.
  - `runner.py`: çalıştırıcı (komut, yalıtım, ortam, akış okuma, ölçüm, zaman aşımı, Türkçe hata mesajları, talimat karmaları).
  - `settings.py`: Ayarlar'ın Claude bölümü (`<veri klasörü>/ayarlar.json`).
  - `schema.py`: şemaların kullandığı JSON Schema alt kümesinin denetimi (Türkçe mesajlar).
  - `steps.py`: adım çerçevesi (adım tanımı, birleşik talimat, çalışma bağlamı).
  - `title.py`: ilk Claude adımı, konu ve başlık önerisi.
  - `service.py`: çalışmaları yürütür (tek çalışma, iş paneli, onay kararları, video kaydı, videonun kanıt paketi).
  - `store.py`: `claude_runs` ve `videos` tabloları.
  - `schemas/baslik.schema.json`: konu ve başlık adımının JSON şeması.
- **Destinasyon tarafı**:
  - `studio/destinations/thirty_a_claude/ortak.md` ve `baslik.md`: talimat metinleri (GÖREV-13 Ek A ve Ek B, aynen).
  - `studio/destinations/thirty_a_claude/kanal_arastirmasi.md`: kanal araştırması (vidIQ, 8 Ekim 2026; `work/yonetim/30A_YOUTUBE_ARASTIRMA.md`'nin kopyası).
  - `thirty_a.py` → `CLAUDE_INSTRUCTIONS` (talimat klasörü) ve `CHANNEL`: kanal planı (`docs/KONSEPT.md`, Ek C'deki kanal ve içerik planıyla),
    kanal araştırması, içerik aileleri (şemanın sabit listesi), "30A geneli" adı, veri özetleri için genel ve mahalle şablonu.

## Çalıştırıcı

Komut (Housing Atlas'takiyle aynı):

```
claude -p --output-format stream-json --verbose --append-system-prompt-file <birleşik talimat> --tools <adımın araçları>
  [--allowedTools <kurallar…>] --permission-mode dontAsk --max-turns <n> --setting-sources "" --strict-mcp-config
  --disable-slash-commands [--model <model>] [--effort <efor>]
```

- Görev metni standart girdiden verilir; çalışma klasörü o çalışmanın klasörüdür (mutlak yol).
- `claude` programı: Ayarlar'daki yol, PATH, `%APPDATA%\npm\claude.cmd`, `%USERPROFILE%\.local\bin\claude.exe`. npm'in `claude.cmd` kabuğu
  çözülür ve içindeki `claude.exe` doğrudan çalıştırılır (cmd.exe'nin 8.191 karakter sınırı ve tırnak sorunları olmasın). `.py` ile biten yol
  uygulamanın Python'uyla çalışır (testlerin sahte programı).
- Sürüm her çalışmadan önce yeniden okunur (önbellek yok; Claude Code güncellenince eski sürüm görünmesin).
- `--model` ve `--effort` yalnız doluysa verilir ("" Claude Code'un kendi seçimi).
- Zaman aşımı: 45 dakika ya da tur sınırı × 90 saniye, hangisi büyükse.
- Aynı anda tek Claude çalışması yürür (iş tablosunun "aynı türde tek etkin iş" kuralı ve `claude_runs` üzerindeki tekil dizin).

### Yalıtım

- `--setting-sources ""`: kullanıcının, projenin ve yerel ayar dosyaları (kancalar, izinler, eklentiler, kullanıcı becerileri, CLAUDE.md
  dosyaları) yüklenmez; kuruluş (managed) ayarları her zaman geçerlidir.
- `--strict-mcp-config` (ve `--mcp-config` verilmez): hiçbir MCP sunucusu yüklenmez. `--disable-slash-commands`: beceriler kapalı.
- Ortam değişkenleri: `ENABLE_CLAUDEAI_MCP_SERVERS=0` (claude.ai bağlayıcıları kapalı), `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` (otomatik bellek
  kapalı), `DISABLE_AUTOUPDATER=1` (çalışma sırasında kendini güncellemez).
- Uygulama bir Claude Code oturumunun içinden başlatıldıysa (`CLAUDECODE`) o oturumun değişkenleri (`CLAUDE_CODE_*`, `CLAUDECODE`,
  `ANTHROPIC_BASE_URL` …) alt sürece geçmez; `CLAUDE_CODE_GIT_BASH_PATH` ve `CLAUDE_CODE_OAUTH_TOKEN` korunur.
- Kullanıcının aboneliği kullanılır. `ANTHROPIC_API_KEY` tanımlıysa Claude Code API'den ücretlendirir: Ayarlar'da, Videolar ekranında
  (çalıştırmadan önce onay sorusuyla) ve iş günlüğünde Türkçe uyarı gösterilir.
- `--bare` kullanılmaz (yalnız API anahtarı kabul eder; abonelik girişi çalışmaz).

### Akış ve ölçüm

Akış satır satır okunur ve iş paneline Türkçe satırlar olarak yazılır: "Tur 3/30 · Okuyor: veri_ozeti_30a.md", "Tur 4/30 · Yazıyor:
baslik.json", "Tur 4/30 · Reddedildi: …", "Tur 5/30 · Düşünüyor (12 sn)", kullanım sınırı uyarısı, bitişte "Claude bitti: 9 tur · 10 araç
çağrısı (9 okuma, 1 yazma) · 6 dk 12 sn · 410 bin girdi / 62 bin çıktı token · maliyet karşılığı 1,23 $". Akışın tamamı çalışma klasöründe
`akis.jsonl`'dadır. Tur, Claude'un ana oturumdaki cevap sayısıdır (`--max-turns` bunu sınırlar); Claude Code'un sonuç zarfındaki `num_turns`
yalnız kayda `cc_num_turns` olarak yazılır.

### Hatalar

Kullanım sınırı (sıfırlanma zamanıyla), tur sınırı, oturum açık değil, program bulunamadı, zaman aşımı, iptal, eski Claude Code sürümü
(`claude_code_version_too_old`, `cli_version_too_old`, `--effort`'u tanımayan sürüm) ve desteklenmeyen model ya da efor
(`model_not_found`, `effort_requires_thinking`; `claude update` önerilir) anlaşılır Türkçe mesajla gösterilir. Uygulama çalışma sürerken
kapanırsa Claude durdurulur ve çalışma "hata: Uygulama kapanırken yarıda kaldı." olur; sert kapanışta bu, bir sonraki açılışta yazılır.

## Ayarlar → Claude

- Bulunan `claude` programının yolu ve sürümü; API anahtarı uyarısı.
- Genel varsayılan model ve efor; adım başına model ve efor ("Genel varsayılan" seçeneğiyle) ve adım başına en fazla tur sayısı.
- Model ve efor listeleri Housing Atlas'takiler (`MODEL_CHOICES`: Claude Code varsayılanı, Opus 5.5, Fable 5.1, Sonnet 5, Haiku 4.5;
  `EFFORT_CHOICES`: Otomatik, Düşük, Orta, Yüksek, Çok yüksek, En yüksek).
- Adım listesi şimdilik tek: "Konu ve başlık"; başlangıç ayarı Opus 5.5 (`claude-opus-5-5`), yüksek efor, 30 tur.
- Ayarlar kullanıcı verisidir: `<veri klasörü>/ayarlar.json`; gizli bilgi yoktur (Claude Code kendi girişini tutar).

## Adım çerçevesi

Her Claude adımı (`steps.Step`): anahtar ve Türkçe adı; talimat dosyaları (destinasyon tarafında, ortak dosya önce); JSON şeması (çekirdekte);
izinli araçlar; girdi kurucusu; görev metni; çıktı denetimi (şema, sonra anlam); okunur Markdown üreticisi. Claude yalnız JSON yazar; Markdown'ı
program üretir.

- Araçlar: `Read`, `Glob`, `Grep` (çalışma klasöründe okuma; Claude Code `Read(./**)` kuralını Glob ve Grep'e de uygular) ve `Write`, `Edit`
  yalnız adımın JSON çıktısında (`Write(./baslik.json)`, `Edit(./baslik.json)`; tek başına `Write(...)` kuralı yok sayıldığı için `Edit(...)`
  şart — Housing Atlas'ta canlıda doğrulandı). Web araması, Bash ve başka araç yoktur; `dontAsk` kipinde kurala uymayan her çağrı reddedilir
  ve kayda yazılır.
- Birleşik talimat: destinasyonun ortak talimatı + adımın talimatı + adımın bu çalışma için doldurulmuş JSON şeması (destinasyonun listeleri:
  içerik aileleri, bölgeler, özet dosyaları). `talimat.md` olarak çalışma klasörüne yazılır.
- Talimat karmaları: her çalışma, kullandığı talimat dosyalarının ve çekirdek şemanın SHA-256 karmalarını (ve birleşik talimatın ve
  doldurulmuş şemanın karmalarını, depo işlemesini) çalışma kaydına yazar.

### Çalışma klasörü

`<veri klasörü>/claude/<hazırlık ya da video kimliği>/<adım>/<çalışma kimliği>/`. İçinde: girdiler, `talimat.md`, `sema.json`, `gorev.md`
(görev metni), `akis.jsonl`, Claude'un JSON çıktısı, programın Markdown'ı ve `calisma.json` (çalışma kaydı: seçim, girdiler ve SHA-256'ları,
kullanılan paketler, talimat karmaları, model, efor, Claude Code sürümü, oturum kimliği, tur, araç çağrıları, token'lar, maliyet karşılığı,
reddedilen çağrılar, sorunlar). Hiçbir çalışma silinmez; yeniden çalıştırma ve düzeltme yeni klasör açar. Konu ve başlık önerisinde hazırlık
kimliği ilk çalışmanın kimliğidir; düzeltmeleri aynı hazırlıkta durur.

## Onay ekranı

Videolar ekranında bir çalışma açılınca Claude'un çıktısı okunur biçimde görünür: önce başlık listesi, bir başlığa tıklanınca ayrıntısı.
Doğrulama sorunları ayrı listelenir (genel sorunlar başta, adayın sorunları kendi ayrıntısında; hatalı aday seçilemez). Bir not alanı ve üç işlem:

- **Seç (Bu başlığı seç):** seçilen aday bir video kaydı olur; aynı çalışmadan başka başlık da seçilebilir.
- **Düzeltme iste:** yeni bir oturum açar (`--resume` yok); kullanıcının notu ve önceki çıktı (`onceki_cikti.json`) görev metninde verilir.
- **Reddet:** yalnız onay bekleyen çalışmada.

Şemaya uymayan, okunamayan ya da hiç yazılmamış çıktı "hata" olur; sorunları listelenir, "Düzeltme iste" açılabilir.

## Video kaydı (şema 15)

`videos`: kimlik, destinasyon, bölge (30A geneli için boş) ve adı, İngilizce başlık ve Türkçe karşılığı, içerik ailesi, seçilen adayın
bütün analizi (neden önerildiği, izleyicinin sorusu, kanca, içerik planı, eksik veri, kapak fikri, şablon ve parametreler; kancanın ve
planın her kanıtı değeriyle ve geldiği paketin kimliğiyle), şablon ve parametreler, durum (`baslik_secildi`, `paket_hazir`), oluşturulma
zamanı, başlığın geldiği çalışma ve aday sırası. `claude_runs`: çalışmanın satırı (adım, hazırlık, iş, düzeltilen çalışma, durum, seçim,
klasör, model, efor, sürüm, oturum, ölçüm, sorunlar, karar notu). `evidence_packs.video_id`: paketin üretildiği video.

### Videonun kanıt paketi

Video kaydında "Kanıt paketi üret": mevcut kanıt paketi üretimi, kaydın şablonu ve parametreleriyle. Paketin ve yazar özetinin başına "Video"
bölümü yazılır: başlık, Türkçe karşılığı, bölge ve aile, izleyicinin sorusu, neden önerildiği, kapak fikri, kanca ve içerik planı, eksik veri.
Kaydın şablonu yoksa (yeni şablon gerekir) düğme bunu söyler ve paket üretilmez.

K kimlikleri paket başınadır. Başlık önerisindeki kimlikler öneriye girdi olan özetlerin paketlerine aittir; video bölümü her kanıtı değeri ve
kaynak paketiyle gösterir. Aynı satır yeni pakette de varsa (aynı kaynak satırı — blok ve referans satırı ya da ifade — ve aynı değer) yeni
paketteki kimliği yanına yazılır; değeri farklıysa "değeri farklı", yoksa "bu pakette yok" diye açıkça yazılır.

## Konu ve başlık adımı (`baslik`)

- Talimatlar: `ortak.md` (Ek A) ve `baslik.md` (Ek B), aynen. Şema: `studio/ai/schemas/baslik.schema.json`.
- Seçimler (Videolar ekranı): **bölge** (zorunlu; "30A geneli" ya da bir mahalle), **içerik ailesi** (isteğe bağlı; kanal planındaki
  ailelerden biri ya da "hepsi"), **not** (isteğe bağlı). Üçü görev metnine ve çalışma kaydına yazılır.
- Girdiler (çalışma klasörüne):
  - `kanal_plani.md`: `docs/KONSEPT.md`'nin tamamı (sonunda Ek C, kanal ve içerik planı).
  - `kanal_arastirmasi.md`: kanal araştırması.
  - `secim.md`: bölge, içerik ailesi, not.
  - `veri_ozeti_30a.md`: "ilk video" şablonunun yazar özeti (her çalışmada).
  - `veri_ozeti_mahalle.md`: bölge bir mahalleyse o mahallenin "Mahalle rehberi" yazar özeti.
  - `sablonlar.md`: programın paket kurabildiği şablonlar (adı, ana sorusu, parametreleri ve geçerli değerleri, bölümleri; şablon
    dosyalarından üretilir).
  - `onceki_oneriler.md`: daha önce önerilen bütün başlıklar (İngilizce, Türkçe, bölge, aile, tarih; seçilenler "seçildi"). İlk çalışmada
    boştur. Düzeltilen çalışmanın kendi hazırlığındaki başlıklar buraya girmez (düzeltme onları yeniden yazar).
  - Bir özetin paketi verinin son çekiminden eskiyse ya da paket başka program veya profil dosyalarıyla üretildiyse (paketin "profil karması")
    program özeti yeniden üretir; güncel paket varsa onu kullanır.
- Kanıt biçimi: `{"dosya": "veri_ozeti_30a.md" | "veri_ozeti_mahalle.md", "kimlik": "K0123"}` (K kimlikleri pakete aittir; dosya hangi özet
  olduğunu söyler). Değerleri program paketten okur.
- Şema (alan adları Türkçe): `surum`, `adim`, `notlar[]`, `adaylar[]` — her aday: `baslik_en`, `baslik_tr`, `bolge`, `aile`, `neden_onerildi`,
  `izleyici_sorusu`, `kanca{metin, kanitlar[]}`, `icerik_plani[{bolum, ne_anlatir, kanitlar[]}]`, `eksik_veri[]`, `sablon` (anahtar ya da null),
  `parametreler{}`, `yeni_sablon_gerekir`, `kapak_fikri`. `aile` ve `bolge` destinasyonun listeleridir. Şema bilinmeyen alanı reddeder.
- Anlam denetimleri: 8–12 aday; "30A geneli" ve "hepsi" iken en az 4 farklı aile; bir mahalle seçildiyse bütün adaylar o mahalleden; bir aile
  seçildiyse bütün adaylar o aileden; her kanıt kimliği verilen özetin paketinde (yoksa hata; "veri yok" satırı uyarı); kancanın en az bir
  kanıtı; içerik planında en az 5 bölüm ve her bölüm en az bir kanıtla; şablon ve parametreler var ve geçerli (mahalle parametresi adayın
  bölgesiyle uyuşur), şablon null ise `yeni_sablon_gerekir` doğru; İngilizce başlık en çok 100 karakter; başlıklar birbirini ve önceki
  önerileri tekrar etmez (büyük-küçük harf ve noktalama farkı gözetilmeden).
- Markdown (`baslik.md`): önce başlık listesi (İngilizce, Türkçe, aile, şablon), doğrulama sorunları, sonra her aday için ayrıntı kartı
  (kanıtlar değerleriyle).

## Yeni adım nasıl eklenir

1. Talimat dosyasını destinasyonun Claude klasörüne koyun (ör. `thirty_a_claude/metin.md`); ortak dosya aynı kalır. Talimat metni kullanıcının
   ya da yöneticinin metnidir; program uydurmaz.
2. JSON şemasını `studio/ai/schemas/` altına yazın (yalnız `schema.py`'nin denetlediği anahtarlar; destinasyon listeleri çalışmada doldurulur).
3. `studio/ai/` altında adımın modülünü yazın: `prepare` (girdileri çalışma klasörüne koyar), `task` (görev metni), `fill_schema`, `check`
   (anlam denetimleri; `{"aday", "seviye", "metin"}`), `render` (Markdown); `steps.register(steps.Step(...))` ile kaydedin.
4. `studio/ai/settings.py` → `CLAUDE_STEPS` ve `STEP_DEFAULTS`'a adımı ekleyin (Ayarlar'daki satırı buradan gelir).
5. Onay kararının ne yapacağını `service.py`'de tanımlayın (konu ve başlık adımında seçim video kaydı açar).
6. Sahte claude'a (`tests/fake_claude.py`) adımın çıktısını ekleyin ve testleri yazın; testler gerçek Claude'u çağırmaz.

## Testler

`tests/test_claude_runner.py` (komut ve yalıtım bayrakları, ortam değişkenleri ve oturum değişkenlerinin düşmesi, npm kabuğunun çözülmesi,
sürüm ve API anahtarı, Türkçe hata mesajları, akış satırları, zaman aşımı, talimat karmaları, ayarların varsayılanı, "Genel varsayılan",
doğrulama ve saklanması), `tests/test_claude_steps.py` (geçerli çıktı; şemaya uymayan, okunamayan ve yazılmayan çıktı; var olmayan kanıt
kimliği; kanıtsız bölüm; mahalle özetinin girdiye konması ve başka mahalleye ait aday; aile seçimine uymayan aday; önceki önerilerin girdiye
konması ve tekrar eden başlık; tur sınırı, kullanım sınırı, eski sürüm; düzeltmenin yeni oturum açması; seçimin video kaydını analiziyle
oluşturması; ayarlardaki model ve eforun komuta geçmesi; talimat karmaları; tek çalışma ve yarıda kalan çalışma; videonun kanıt paketi ve
kimlik eşlemesi; özet paketinin yeniden kullanılması; API anahtarı uyarısı; v14 → v15 geçişi), `tests/frontend.test.mjs` (Videolar formu,
başlık listesi ve ayrıntı, video kaydı, Ayarlar → Claude).

## Sınırlar

- Testler gerçek Claude'u çağırmaz; sahte claude (`tests/fake_claude.py`) kullanılır.
- Claude soru soramaz; çıktısı şemaya ve anlam denetimlerine uymazsa kullanıcı "Düzeltme iste" ile yeni bir çalışma açar.
- Video metni, metnin kontrolü ve yeni şablonlar sonraki görevlerdedir.
