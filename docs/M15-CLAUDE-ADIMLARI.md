# M15 — Programın içinde Claude: çalıştırıcı, ayarlar, adım çerçevesi, onay ekranı, video kaydı, konu ve başlık adımı

Tarih: 11 Ekim 2026 · Görev: GÖREV-13; GÖREV-14 (kullanım paneli, ilerleme çubuğu, talimat düzenleyici, model takma adları, başlık eki, başlık değerlendirme, seçmeden önce düzenleme); GÖREV-15 (video metninin yedi adımı, oturum sınırı, kullanım eşikleri) · Dal: `gorev-15-video-metni` · Şema `17` · Uygulama `0.17.0`

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
- Model ve efor listeleri Housing Atlas'takiler (`MODEL_CHOICES`: Claude Code varsayılanı; aile takma adları `opus`, `sonnet`, `haiku`
  — Claude Code'un o ailedeki en yeni modeli, GÖREV-14 —; Opus 5.5, Fable 5.1, Sonnet 5.5 (GÖREV-14), Sonnet 5, Haiku 4.5;
  `EFFORT_CHOICES`: Otomatik, Düşük, Orta, Yüksek, Çok yüksek, En yüksek). Doğrulanmamış tam model kimliği eklenmez.
- Adımlar: "Konu ve başlık" ve "Başlık değerlendirme" (GÖREV-14); başlangıç ayarı ikisinde de Opus 5.5 (`claude-opus-5-5`), yüksek efor,
  30 tur. GÖREV-15: video metninin yedi adımı ve "Video metni çalışması" ayarları (aşağıda).
- Kullanım panelindeki "Yenile" çağrısı ve modeli (`haiku`, düşük efor) burada yazar.
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
klasör, model, efor, sürüm, oturum, ölçüm, sorunlar, karar notu). `evidence_packs.video_id`: paketin üretildiği video. Şema 16 (GÖREV-14): `videos.proposed_title_en`, `proposed_title_tr` (önerilen başlık) ve `user_edited` (kullanıcı başlığı seçmeden önce düzenledi); `title_en` / `title_tr` seçilen (düzenlenmişse düzenlenmiş) başlıktır.

### Videonun kanıt paketi

Video kaydında "Kanıt paketi üret": mevcut kanıt paketi üretimi, kaydın şablonu ve parametreleriyle. Paketin ve yazar özetinin başına "Video"
bölümü yazılır: başlık, Türkçe karşılığı, bölge ve aile, izleyicinin sorusu, neden önerildiği, kapak fikri, kanca ve içerik planı, eksik veri.
Kaydın şablonu yoksa (yeni şablon gerekir) düğme bunu söyler ve paket üretilmez. GÖREV-14'ten beri video kaydının paketi seçilen adayın içerik planından kurulur ve "yeni şablon gerekir" paketi engellemez (`docs/M14-KANIT-PAKETI.md`, "Video paketi: seçilen adayın içerik planından").

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

## Başlık eki (GÖREV-14)

Ayarlar → Başlık eki: destinasyon başına İngilizce ek (başlangıç " | 30A Florida Vacation") ve Türkçe ek (" | 30A Florida Tatili");
başlangıç değerleri profilden (`CHANNEL["title_suffix"]`), değişiklik `<veri>/ayarlar.json` → `baslik_ekleri`. Program ekleri her başlık
ve değerlendirme çalışmasının seçimine ve `secim.md` dosyasına yazar (çalışma o anki eki taşır); doğrulayıcı her adayın İngilizce
başlığının İngilizce ekle, Türkçe karşılığının Türkçe ekle bittiğini denetler (`title.title_problems`). `baslik.md`'deki ek cümlesi
GÖREV-14 Ek B'deki cümleyle değiştirildi.

## Başlık değerlendirme adımı (`baslik_degerlendirme`, GÖREV-14)

Videolar ekranında "Kendi başlığını yaz": kullanıcı aklındaki başlığı ya da fikri (Türkçe ya da İngilizce, en çok 500 karakter), bölgeyi ve
isteğe bağlı bir notu yazar (`POST /api/claude/review-runs`).

- Talimatlar `ortak.md` ve `baslik_degerlendirme.md` (GÖREV-14 Ek A, aynen); şema `studio/ai/schemas/baslik_degerlendirme.schema.json`;
  modül `studio/ai/title_review.py`.
- Girdiler başlık adımınınkiler (kanal planı ve araştırması, `secim.md`, veri özetleri, şablonlar, önceki öneriler) ve iki dosya daha:
  `kullanici_basligi.md` (kullanıcının yazdığı, iki işaret satırı arasında aynen) ve `baslik_olculeri.md` (`baslik.md`'nin kopyası; iyi
  başlığın ölçüleri orada, aday sayısı ve çıktı biçimi bu adım için geçerli değil).
- Çıktı `baslik_degerlendirme.json`: `kullanici_fikri` (aynen), `doluluk` {`dolar_mi`, `aciklama`, `eksik_veri`[]}, `sorunlar`[]
  (kullanıcının ifadesindeki sorunlar), `adaylar`[] (başlık adımının aday yapısı). `eksik_veri` görev metninin "aciklama ve eksik veri
  doldurulmalı" kuralı için şemaya eklendi.
- Denetimler: `kullanici_fikri` aynen olmalı; en çok 3 aday; "doluyor" ise en az 1 aday; "dolmuyor" ise eksik veri yazılmalı (aday listesi
  boş kalabilir); adaylar başlık adımının bütün anlam denetimlerinden geçer (bölge, kanıt kimlikleri, plan, şablon, uzunluk, ek, tekrar).
- Onay ekranı başlık adımınınkiyle aynı biçimde: önce değerlendirme özeti (veriyle doluyor mu, açıklama, eksik veri, sorunlar), sonra
  adaylar ve "Bu başlığı seç". Aday yoksa "Bu çalışmada gösterilecek öneri yok." yazar; iş mesajı "fikir veriyle dolmuyor; başlık adayı yok".
- Gerçek çalışma (10 Ekim 2026, Rosemary Beach, "Rosemary Beach'e köpeğimizle gitsek nasıl olur?"): fikir dolmuyor; elimizdeki tek güçlü
  bilgi ilçenin halka açık plajlarındaki köpek yasağı (Rosemary'ye özgü değil), Rosemary'nin özel plajı için köpek kuralı yok; 7 eksik veri
  (topluluğun köpek kuralı, kiralık evlerin evcil hayvan kuralı, restoranların köpek kabulü, veteriner, köpekle gidilebilecek yerler…);
  78 sn, 6 tur (`docs/gorevler/GOREV-14/gercek-degerlendirme/`).

## Seçmeden önce düzenleme (GÖREV-14)

Aday ayrıntısında "Başlığı düzenle": İngilizce başlık ve Türkçe karşılığı değiştirilir; program uzunluk ve ek kurallarını denetler
(önerideki kuralların aynısı). Seçilince video kaydı önerilen başlığı da tutar ve "kullanıcı düzenledi" işareti taşır. Kullanıcı İngilizce
bilmediği için yalnız Türkçe karşılığı değiştirdiyse "İngilizcesini Claude yazsın" görünür (`POST /api/claude/runs/{id}/translate`): değişen
Türkçe başlıkla bir başlık değerlendirme çalışması açılır; `kullanici_basligi.md` Türkçe başlıktır, notta "bu aday düzenlendi" ve adayın
analizi yazar; adayın kendi başlığı yeni çalışmanın "önceki önerisi" sayılmaz.

## Kullanım paneli (GÖREV-14)

Sol menünün altında (`studio/ai/usage.py`, `studio/web/usage.js`). Kaynak: Claude Code'un her cevaptan sonra akışa yazdığı
`rate_limit_event` (`rate_limit_info.unifiedWindows.five_hour|seven_day.{utilization, resetsAt}`; eski biçimde tek pencere). Her ölçüm
zamanıyla `claude_usage` tablosuna yazılır: çalışma sırasında çalıştırıcının `on_rate_limit`'iyle, ve "Yenile" çağrısıyla. Panel: en son
ölçümün 5 saatlik ve haftalık yüzdesi ve sıfırlanma zamanı (haftalıkta gün ve saat), "son ölçüm SS:DD", bu haftaki Claude çalışmalarının
sayısı ve toplam süresi (hafta: ölçümün haftalık penceresi, yoksa son 7 gün). Ölçüm yoksa "henüz ölçüm yok"; 5 saatten eskiyse soluk ve
"eski ölçüm". "Yenile": araçsız, tek tur, `haiku` (Claude Code'un en yeni Haiku'su), düşük efor, tek kelimelik cevap; `<veri>/claude/kullanim/`
klasöründe çalışır; bir adımın çalışması sürerken ve `ANTHROPIC_API_KEY` tanımlıyken yapılmaz. Gerçek ölçüm (10 Ekim 2026): 4,4 sn, Claude
Haiku 4.5, maliyet karşılığı 0,005 $.

## İlerleme çubuğu (GÖREV-14)

Tur oranı yanıltır (bir başlık çalışması 30 turun 5–6'sını kullanıyor); Claude çalışmasının çubuğu aşamalardan ilerler (`job_progress`,
`studio/web/usage.js` → `claudeProgress`): girdiler hazırlanıyor %0–10; Claude çalışıyor %10–90: geçen süre / beklenen süre (aynı adımın
son 9 başarılı çalışmasının ortanca süresi; yoksa varsayılan: başlık 7 dk, değerlendirme 5 dk), %90'ı geçmez; doğrulama ve Markdown
%90–100. Yanında yüzde, geçen süre ve tahmini kalan süre (aşılırsa "tahminden uzun sürüyor"); "Tur 3/30 · Okuyor: …" satırı altında kalır.
Toplayıcı işlerinin ilerlemesi değişmedi.

## Ayarlar → Talimatlar (GÖREV-14)

Destinasyonun talimat dosyaları (`studio/ai/instructions.py`, `studio/web/instructions.js`): ortak, başlık, başlık değerlendirme ve bilgi
dosyası olarak kanal araştırması. Bir dosya açılır, düzenlenir, kaydedilir. Tek kaynak depodaki dosyadır (yönetici de aynı dosyayı dışarıdan
düzenliyor). Kaydederken dosya açıldığından beri diskte değiştiyse (SHA-256 farklı) hiçbir şey yazılmaz ve uyarı verilir; kullanıcı yeniden
yükleyip öyle kaydeder. Her kayıttan önce önceki hâl `<veri>/claude/talimat_gecmisi/<dosya>/<YYYYMMDD-HHMMSS-ffffff>.md`'ye yazılır; sürümler
listelenir, "Bu sürüme dön" eski hâli yeni bir kayıt olarak geri yazar (şimdiki hâl de sürümlere eklenir). Dosyanın satır sonları korunur.
Claude çalışmasının ekranında çalışmanın kullandığı talimat sürümleri (dosya, karma, tarih) görünür.

## Video metninin adımları ve ayarları (GÖREV-15)

Yedi yeni Claude adımı aynı çerçevede çalışır (`studio/ai/text_steps.py`; zincir `studio/text/engine.py`, ayrıntı
`docs/M17-VIDEO-METNI.md`): `metin_plan` (plan), `metin_plan_elestiri` (plan eleştirisi), `metin_bolum` (bölüm), `metin_birlestirme`
(birleştirme), `metin_giris_kapanis` (giriş ve kapanış), `metin_son_okuma` (son okuma), `metin_ceviri` (çeviri). Çerçeveye iki şey
eklendi: adımın `voice` bayrağı (yazım adımlarında birleşik talimata ortak dosyadan sonra anlatıcının sesi `ses_ortak.md` ve seçilen
ton girer) ve oturumun tonu ile ek bilgileri (`RunContext.tone`, `RunContext.extra`). Çalışma kaydı tonun dosyasını, adını ve
SHA-256'sını tutar. Şema denetimine `minimum` ve `maximum` eklendi.

Ayarlar → Claude:
- yedi adımın modeli, eforu ve tur sınırı; başlangıç değerleri: plan opus/high, plan eleştirisi opus/medium, bölüm opus/high,
  birleştirme opus/medium, giriş ve kapanış opus/high, son okuma opus/medium, çeviri sonnet/medium (aile takma adları), 30 tur;
- "Video metni çalışması" bölümü: "Aynı anda en çok Claude oturumu" (`claude_max_sessions`, 1–6, varsayılan 3), "5 saatlik pencere
  eşiği" (`claude_limit_five_hour`, varsayılan %90), "Haftalık pencere eşiği" (`claude_limit_week`, varsayılan %95), "Plandan sonra dur"
  (`claude_stop_after_plan`, kapalı).

Ayarlar → Talimatlar listesine "Anlatıcının sesi (bütün tonlarda aynı)" ve yedi `metin_*.md` dosyası eklendi; adımların sırası
`settings.CLAUDE_STEPS`'ten gelir (modüllerin yüklenme sırasından bağımsız). Tonlar bu listede değil, Ayarlar → Tonlar'dadır; uyarı
ifadeleri dosyası da (`uyari_ifadeleri.txt`) Tonlar bölümünün altındaki "Denetim: uyarı ifadeleri" kutusundan, talimatların kayıt ve
sürüm kurallarıyla düzenlenir.

Tek işçi: metin çalışması kendi içinde paralel oturum açar; o sürerken başlık önerisi, başlık değerlendirmesi ve "Yenile" çalışmaz
("Bir video metni çalışması sürüyor; bitmesini bekleyin."), başlık çalışması sürerken de metin çalışması başlamaz. Kullanım panelindeki
haftalık çalışma sayısına metnin oturumları da girer.

Adaysız başlık değerlendirmesi ("veriyle dolmuyor") artık iş akışında "onay bekliyor" sayılmaz; çalışma listesinde "başlık adayı yok"
diye bilgi olarak görünür (GÖREV-14 karar 1).

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
başlık listesi ve ayrıntı, video kaydı, Ayarlar → Claude). GÖREV-14: `tests/test_claude_panel.py` (kullanım ölçümünün okunması ve saklanması, panel görünümü, "Yenile", aşamalı ilerleme ve beklenen süre, talimat düzenleyici: kaydetme, diskteki değişiklikte ret, sürümler, geri dönme, satır sonları; model takma adları, başlık eki ayarı), `tests/test_title_review.py` (değerlendirme çalışmasının girdileri ve şeması, dolmayan fikir, 1–3 aday sınırı, ek denetimi, düzenlemenin kayda geçmesi, Türkçe düzenlemeden değerlendirme çalışması), `tests/test_workflow.py` (iş akışı durumları), `tests/frontend.test.mjs` (kullanım paneli, ilerleme çubuğu, talimat düzenleyici, değerlendirme formu ve sonucu, başlık düzenleme).

## Sınırlar

- Testler gerçek Claude'u çağırmaz; sahte claude (`tests/fake_claude.py`) kullanılır.
- Claude soru soramaz; çıktısı şemaya ve anlam denetimlerine uymazsa kullanıcı "Düzeltme iste" ile yeni bir çalışma açar.
- Video metni GÖREV-15'te geldi (M17); metnin Kontrol adımı, Türkçe düzeltme ekranı ve yeni şablonlar sonraki görevlerdedir.
- Kullanım yüzdesi Claude Code'un bildirdiğidir; ölçüm yalnız bir Claude çağrısından sonra güncellenir.
