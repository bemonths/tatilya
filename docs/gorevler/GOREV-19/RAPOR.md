# GÖREV-19 Raporu — yan çağrı ve önbelleğe yazma kapatıldı

Dal: `gorev-19-yan-cagri-onbellek` (`gorev-18-token-kontrolu`'nun son commit'i `68fa4af`'tan açıldı). Uygulama 0.20.0, şema 19 (değişmedi).

## Kısaca

- Programın başlattığı her Claude çağrısına iki ayar eklendi: **oturum adı isteği kapalı** (`CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`) ve
  **önbelleğe yazma kapalı** (`DISABLE_PROMPT_CACHING=1`). Yalnız programın kendi Claude alt süreçlerinde; Windows'un ortam değişkenlerine ve
  kullanıcının Claude Code ayarlarına yazılmadı. Ayarlar ekranına seçenek eklenmedi.
- **Önbellek ayarı doğrulandı:** aynı istemde önbelleğe yazma sıfıra indi, bedel **%45** düştü (0,087 $ → 0,048 $).
- **Yan çağrı:** GÖREV-18'deki 105 bin tokenlik Haiku çağrısı, Claude Code'un **oturuma ad veren isteği**. Bugünkü küçük çağrılarda bu istek
  ayarsız ortamda da hiç oluşmadı (4 farklı deneme), bu yüzden kapandığını çağrıyla gösteremedim; ama Claude Code'un kendi kodunda bu ayarın
  isteği koşulsuz kapattığı görülüyor (aşağıda). Yeniden görünürse program onu eskisi gibi harcamaya sayar.
- Doğrulama: **6 gerçek çağrı, 61.765 token, 0,22 $** (tahminim 20–50 bin token idi; sınır 8 çağrı / 150 bin).
- Talimat dosyalarında kullanıcının yaptığı değişiklik yoktu (çalışma ağacı temizdi); bu yüzden "talimat:" commit'i yok.

## Adım 1 — Ayarlar

`studio/ai/runner.py`: `ISOLATION_ENV`'e iki değişken eklendi, gerekçesi modülün başındaki açıklamada ve satırın yanında. `build_env` bir Claude
Code oturumunun içinde önce o oturumun `CLAUDE_CODE_*` değişkenlerini siler, sonra `ISOLATION_ENV`'i yazar; böylece üst oturumda
`CLAUDE_CODE_DISABLE_TERMINAL_TITLE=0` olsa bile alt süreç `1` alır. Testler:

- `tests/test_claude_runner.py::test_environment_turns_off_the_side_call_and_prompt_caching_inside_and_outside_a_claude_session`
- `tests/test_gorev19.py::test_every_claude_call_gets_the_title_and_caching_switches_even_inside_a_claude_code_session` (uçtan uca: program
  `CLAUDECODE=1` ortamında çalışırken sahte claude'un gördüğü ortam).

Ayar bütün Claude çağrılarında geçerli: başlık adımları, video metni zinciri ve kullanım ölçümü aynı çalıştırıcıyı (`runner.run` → `build_env`)
kullanır.

## Adım 2 — Küçük gerçek çağrılar

Betik: `work/gorev-19/dogrula.py` (depoya girmez). Programın kendi çalıştırıcısıyla, gerçek adımlardaki komut: `--tools ""`, `--max-turns 1`,
talimat `--append-system-prompt-file` ile (iki satır), görev standart girdiden, model `claude-sonnet-5-5`, efor düşük. "Eski" ortam: programın
ortamından iki yeni değişken çıkarılmış hâli. Sonuç zarfları: `dogrulama/c1…c6.json`.

| # | Ortam | İstem | Model | input | önbelleğe yazılan | önbellekten okunan | yazılan | `modelUsage` | Bedel |
|---|---|---|---|---:|---:|---:|---:|---|---:|
| c1 | eski (iki değişken yok) | tek satır | Sonnet 5.5 | 2 | 2.050 | 658 | 10 | yalnız claude-sonnet-5-5 | 0,0084 $ |
| c2 | yeni (iki değişken) | tek satır | Sonnet 5.5 | 2.734 | 0 | 0 | 10 | yalnız claude-sonnet-5-5 | 0,0056 $ |
| c3 | eski | ~20 bin token malzeme (`CALISMA_MANTIGI.md`'nin ilk 36.000 karakteri) | Sonnet 5.5 | 2 | 20.434 | 1.587 | 549 | yalnız claude-sonnet-5-5 | 0,0874 $ |
| c4 | yeni | c3 ile aynı | Sonnet 5.5 | 22.024 | 0 | 0 | 366 | yalnız claude-sonnet-5-5 | 0,0477 $ |
| c5 | eski | tek satır, uzun cevap (62 sn sürdü) | Sonnet 5.5 | 2 | 1.211 | 1.587 | 5.798 | yalnız claude-sonnet-5-5 | 0,0630 $ |
| c6 | eski, `--debug-file` ile | tek satır | Sonnet 5.5 | 2 | 1.142 | 1.587 | 10 | yalnız claude-sonnet-5-5 | 0,0048 $ |

Toplam: 61.765 token (okunan + yazılan), 0,2169 $. Hiçbir çağrı 30 bini geçmedi.

### Yan çağrının ne olduğu

- Küçük istemde (c1) yan çağrı çıkmadı; görev metnindeki gibi ~20 bin tokenlik malzemeyle yineledim (c3): yine çıkmadı. GÖREV-18'deki çağrı 41 sn
  sürmüştü; yan çağrı ana çağrı uzun sürünce mi yetişiyor diye uzun cevaplı bir çağrı (c5, 62 sn) yaptım: yine yok. `--debug-file` ile (c6)
  Claude Code'un günlüğünde de oturum adına dair bir satır yok.
- Bunun üzerine Claude Code 2.1.318'in kendi dosyasındaki koda baktım (yalnız okuma, `work/gorev-19/ara.py`). Bulgular:
  - Claude Code'un iç çağrılarından biri `generate_session_title`: "oturuma ad ver" sistem metniyle küçük modele mesajı gönderir ve
    `{"title": …}` JSON'u ister. 24 tokenlik çıktı tam bu boydadır.
  - Gönderilen metin, bir sunucu bayrağı (`tengu_lucky_brooks`, varsayılan kapalı) açık değilse **ilk mesajın tamamıdır** (kodda: "sending the
    whole message"). GÖREV-18'de Haiku'nun 105 bin token okuması bununla açıklanıyor (istemin talimat dışındaki kısmı).
  - Oturum başında `CLAUDE_CODE_DISABLE_TERMINAL_TITLE` doluysa ad "denenmiş" sayılır ve istek **hiç yapılmaz**; bu kontrol öbür koşullardan önce
    gelir ve sunucu bayraklarına bağlı değildir. Değişken yoksa isteğin yapılıp yapılmayacağı başka bir sunucu bayrağına ve giriş noktasına bağlı;
    bugünkü çağrılarda istek bu yüzden yapılmadı, 11 Kasım'daki çağrıda yapılmıştı. Sunucu tarafı bayraklar her gün değişebildiği için ayar yine gerekli.
- Sonuç: yan çağrı oturum adı isteğidir ve bu ayar onu kapatır; bunu bugün gerçek bir çağrıyla karşılaştıramadım (eski ortamda da oluşmadı).
  Başka bir ayar denemedim; `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` gibi geniş bayraklara gerek görülmedi.
- Program yan çağrıyı zarfın `modelUsage`'ından okumaya, harcamaya saymaya ve iş günlüğüne "…Claude Code'un kendi yan çağrısı … okudu" diye
  yazmaya devam ediyor; ilk gerçek video metninde görünürse yöneticiye haber verir.

### Önbellek ayarının etkisi

- Eski ortamda istemin tamamı **bir saatlik** önbelleğe yazılıyor (`ephemeral_1h_input_tokens`); yeni ortamda önbelleğe yazma ve önbellekten okuma
  sıfır, girdinin tamamı `input_tokens`'ta (c2, c4). Beklenen sonuç bu; `DISABLE_PROMPT_CACHING_OPUS` ve `FORCE_PROMPT_CACHING_5M`'i denemeye
  gerek kalmadı.
- Aynı istem için bedel: c3 0,0874 $ → c4 0,0477 $ (%45 ucuz); tek satırda c1 0,0084 $ → c2 0,0056 $.
- Zarflardan çıkan liste fiyatları (milyon token başına): Sonnet 5.5 girdi 2 $, çıktı 10 $, 1 saatlik önbelleğe yazma 4 $, önbellekten okuma
  0,2 $. GÖREV-18'in Opus çağrısından: Opus 5.5 girdi 4 $, çıktı 20 $, önbelleğe yazma 8 $; Haiku 5.5 girdi 0,5 $. (Hesaptır; Anthropic'in fiyat
  sayfasından okunmadı.)
- Token sayısı değişmez, yalnız bedel. Claude Code'un kendi sistem metninin önbellekten okunan küçük payı (658–1.587 token) da artık normal fiyattan;
  etkisi binde birin altında.
- Program bedeli Claude Code'un `total_cost_usd`'sinden gösteriyor; değişiklik gerekmedi. Ekranda "önbelleğe yazma" diye bir açıklama yok; Ayarlar
  → Claude kullanımı'ndaki "okunan (önbellekten okunan dahil)" notu eski kayıtlar için doğru olduğundan kaldı.

## Adım 3 — Programdaki izler

- Tahmindeki yan çağrı payı, son tek çağrıların oranlarının ortancası. Yan çağrısız kayıtlar biriktikçe pay kendiliğinden sıfıra iner:
  `tests/test_gorev19.py::test_side_call_share_falls_to_zero_when_the_one_call_records_have_none` (bir yan çağrılı, iki yan çağrısız çalışma →
  ortanca 0, tahminde pay ve "yan çağrısı için … eklendi" notu yok). Gerçek veride hiç yan çağrılı kayıt yok (GÖREV-18'in gerçek çağrısı geçici
  kopyadaydı), yani gerçek programda pay zaten 0.
- 1,85 karakter/token ve 4.500 Claude Code sistem metni payı değişmedi.

## Programın yeni tahminleri

Token tahminleri GÖREV-18'in ölçüm tablosundakilerdir (gerçek verinin kopyası, Claude çağrılmadan); yan çağrı kapandığı için onlara pay eklenmez.
"Yan çağrı ve önbellekle" sütunu, iki boşa harcama sürseydi ne olacağıdır (okunan ikiye katlanır). Bedel Opus 5.5 liste fiyatıyla kabaca
hesaplandı (video metninde çeviri Sonnet'le çalıştığı için gerçek bedel biraz daha düşük olur).

| Çalışma | Okunan | Yazılan | Toplam | Yan çağrı ve önbellekle (eski) | Bedel eski → yeni |
|---|---:|---:|---:|---:|---|
| Konu ve başlık · 30A geneli | 92 bin | 54 bin | 147 bin | 238 bin | ~1,86 $ → ~1,45 $ |
| Konu ve başlık · Rosemary Beach | 108 bin | 54 bin | 163 bin | 270 bin | ~2,00 $ → ~1,51 $ |
| Başlık değerlendirme | 110 bin | 8 bin | 118 bin | 228 bin (GÖREV-18 gerçek: 219 bin) | ~1,10 $ → ~0,60 $ (GÖREV-18 gerçek: 1,00 $) |
| Video metni · bir ton (plan dahil) | 273 bin | 108 bin | 381 bin | 654 bin | ~4,48 $ → ~3,25 $ |
| Video metni · iki ton (plan dahil) | 465 bin | 190 bin | 655 bin | 1,12 milyon | ~7,75 $ → ~5,66 $ |

Video metninde yazılan değerler Ayarlar'daki çıktı varsayımlarıdır (gerçek metin henüz hiç yazılmadı); ilk gerçek metinden sonra ortancadan gelir.

## Adım 4 — Testler, belgeler, CI, main ve etiket

- Testler: `.venv\Scripts\python.exe -m pytest -q` → 1118 geçti, 2 atlandı (7 dk 34 sn; ilk turda eski bir testin ortam karşılaştırması iki yeni değişken yüzünden düştü, test güncellendi); `node --test tests/frontend.test.mjs` → 120 geçti.
- Belgeler: `docs/M15-CLAUDE-ADIMLARI.md` ("Tek çağrı düzeni, tahmin ve sınırlar" bölümüne "İki boşa harcama kapalı" maddesi; Yalıtım bölümüne iki
  değişken), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`.
- CI: CI_SONUCU
- main ve etiket: MAIN_SONUCU
