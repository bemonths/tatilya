# GÖREV-15 raporu — video metni: yazım zinciri, seçilebilir tonlar ve ton yönetimi, program denetimi, karşılaştırma

Tarih: 11 Ekim 2026 · Dal: `gorev-15-video-metni` · Uygulama 0.17.0 · Şema 17

## Kısaca

- main, GÖREV-14'ün son commit'ine (`984ca72`) alındı ve `v0.16.0` etiketi kondu. main ve etiket CI başarılı.
- İş akışının 4. adımı "Video metni" artık çalışıyor. Program, seçilen başlık ve video paketiyle Claude'u adım adım çağırıp İngilizce metni
  yazdırıyor: plan, planın eleştirisi, bölümler (yan yana), birleştirme, giriş ve kapanış, son okuma, Türkçe çeviri.
- Her seçilen ton için ayrı metin yazılıyor; plan bir kez yapılıyor ve bütün tonlar aynı planı kullanıyor. "Bu tonla da yaz" aynı planla
  bir ton daha yazdırıyor; "Planı yeniden yap" yeni bir çalışma açıyor, eskisi saklanıyor.
- Anlatıcının sesi ve beş ton görevin eklerinden aynen yazıldı. Tonlar Ayarlar → Tonlar'dan programın içinde yönetiliyor: ekleme,
  düzenleme, sürümler, silme (arşive gider), geri alma, varsayılan ton.
- Program her metni kendi kurallarıyla denetliyor (denetim Claude'a verilmez): verinin söylemediği iddialar ve kanıtla tutmayan
  sayılar kırmızı, abartılı ifadeler ve uzunluk sarı. Bulgular cümlenin yanında görünüyor.
- Karşılaştırma ekranında tonlar yan yana (Türkçe önde); "Bu tonla devam et" ile bir sürüm seçiliyor.
- Claude kullanım sınırına gelince çalışma bekliyor ve sıfırlanınca kendiliğinden sürüyor; "Durdur" ve "Devam" var; program kapanırsa
  çalışma "yarıda kaldı" olarak bekliyor ve biten adımlar yeniden yapılmıyor.
- Gerçek Claude çağrılmadı. Bütün denemeler sahte claude programıyla, gerçek verinin geçici bir kopyasında yapıldı.
- Gerçek veritabanı normal kullanımla şema 17'ye geçti: eski satırların hepsi aynı, dört yeni tablo boş.

## Konumlar, CI ve testler

| | Konum | CI |
|---|---|---|
| GÖREV-14 dalı son commit | `984ca72a6d3a784146125a1a2146c6c7eabd2139` | 38085832280 başarılı |
| main (fast-forward `a59ec65..984ca72`, push) | `984ca72a6d3a784146125a1a2146c6c7eabd2139` | 38089912314 başarılı |
| Etiket `v0.16.0` (açıklamalı, push) | `984ca72` — "v0.16.0 — masaüstü programı, iş akışı paneli, Claude kullanımı ve talimat düzenleyici, kullanıcının kendi başlığı, içerik planından video paketi, tarayıcı eklentisi" | 38089918781 başarılı |
| Görev dalı | `gorev-15-video-metni` | aşağıda |

Görev dalının commit'leri ve CI sonuçları (GitHub Actions, Linux):

| Commit | İçerik | CI |
|---|---|---|
| `f956dda` | 1d: adaysız değerlendirme iş akışında "onay bekliyor" sayılmaz | `36c784f` ile birlikte itildi |
| `b442d96` | talimatlar, ses, beş ton, uyarı ifadeleri (eklerden aynen) | `36c784f` ile birlikte itildi |
| `36c784f` | video metni (şema 17, 0.17.0) | 38093013971 başarılı |
| `2299760` | denemede görülen düzeltmeler | son push'la birlikte |
| `89a73da` | "eskidi" kuralı ve iş akışı durumları testi | son push'la birlikte |
| son commit | belgeler, ekran görüntüleri, rapor | GitHub'da |

Testler (yerelde, Windows):

| | main (v0.16.0) | Görev dalı |
|---|---|---|
| Python | 889 | 1031 (1 atlandı: eklentinin isteğe bağlı uçtan uca denemesi) |
| Frontend (Node) | 81 | 90 |

Tam takım art arda 3 kez çalıştırıldı (11 Ekim 2026, 02:44–03:04): üçünde de 1031 Python testi geçti (1 atlandı) ve 90 frontend testi geçti; hata yok. Bundan önceki bir tam çalıştırma da aynı sonucu verdi.

Yeni Python testleri: `test_text_split.py` 57 (Housing Atlas'ın testleri), `test_text_audit.py` 43, `test_text_document.py` 6,
`test_tones.py` 13, `test_text_chain.py` 20, `test_text_workflow.py` 2; ayrıca `test_workflow.py`'de 1d testi ve sürüm sabitleri
(16 → 17) güncellendi. Frontend'de 9 yeni test (1d ve GÖREV-15).

## Adımların sonucu

### Adım 1 — v0.16.0, talimat değişiklikleri, küçük düzeltme

- 1a: `studio/destinations/thirty_a_claude/` altında commit edilmemiş değişiklik yoktu (git temiz). Ayrı commit gerekmedi.
- 1b: `984ca72`'nin dal CI'ı başarılıydı; main fast-forward edildi ve itildi; `v0.16.0` açıklamalı etiketi kondu ve itildi. main ve
  etiket CI'ı başarılı.
- 1c: `gorev-15-video-metni` güncel main'den açıldı.
- 1d: Aday üretmeyen başlık değerlendirmesi ("veriyle dolmuyor") artık "Konu ve başlık" adımının "onay bekliyor" sayımına girmiyor;
  Videolar ekranında "Değerlendirildi: veriyle dolmuyor" diye bilgi olarak görünüyor, iş mesajı "başlık adayı yok" diyor; "Reddet" yine
  kullanılabiliyor. Python ve frontend testi var. Gerçek verideki değerlendirme (Rosemary Beach köpek fikri) artık bekleyen iş sayılmıyor.

### Adım 2 — Talimat dosyaları ve ses

- `ses_ortak.md` (Ek A), beş ton (Ek B–F), yedi `metin_*.md` (Ek G–M) ve `uyari_ifadeleri.txt` (Ek O'daki liste) görev metninden
  bir betikle aynen yazıldı ve ayrı commit'e kondu (`b442d96`). Ek A–M'nin 13 dosyasının SHA-256'sı yazıldıktan sonra kaydedildi ve
  görevin sonunda yeniden karşılaştırıldı; değişmedi. Uyarı ifadeleri dosyası da commit'teki hâlinde (git temiz).
- Birleşik talimat: `ortak.md` → (yazım adımlarında) `ses_ortak.md` ve seçilen ton → adımın dosyası → şema. Planlayıcı ve eleştirmen
  ses ve ton almaz. Testi var.
- Çalışma kaydı (`calisma.json`) tonun dosyasını, adını ve SHA-256'sını tutuyor; birleşik talimat `talimat.md` olarak klasörde.
- Ayarlar → Talimatlar'a "Anlatıcının sesi (bütün tonlarda aynı)" ve yedi `metin_*.md` dosyası adımların Türkçe adlarıyla eklendi.
  Tonlar listede yok.

### Adım 3 — Ton yönetimi (Ayarlar → Tonlar)

Liste (ad, dosya, ilk satır, son değişiklik, varsayılan, kullanım), yeni ton formu, düzenleme (dosya adı değişmez), sürümler ve "Bu
sürüme dön", silme (onaylı; `<veri>/claude/ton_arsivi/` içine taşınır), arşivden geri alma, varsayılan ton (`ayarlar.json`), son tonun
silinememesi, Türkçe addan dosya adı, uzun metin notu, diskte değişiklik çakışması. Video metni ekranındaki "Tonları yönet" bu bölümü
açıyor. Kullanıcının ton değişikliklerinin git'te görünmesi belgelere ve `CLAUDE.md`'ye yazıldı.

### Adım 4 — Zincirin adımları ve şemaları

Yedi adım adım çerçevesine kaydedildi (`studio/ai/text_steps.py`), şemalar `studio/ai/schemas/metin_*.schema.json`. Girdi dosyaları Ek
N'deki tabloya göre konuyor. Görev metinleri kısa; yeniden deneme turunda önceki çıktı ve dönüş sebebi ekleniyor. Anlam denetimleri
yalnız zincirin kullanamayacağı şeyi reddediyor (pakette olmayan kimlik, planda olmayan bölüm numarası, eksik ya da fazla çeviri
numarası). Ayarlar → Claude'da yedi adımın başlangıç modeli ve eforu Ek N'deki gibi.

### Adım 5 — Zincirin işleyişi

Tazelik (paket yoksa ya da eskiyse önce yeniden üretiliyor), plan → program plan denetimi → eleştirmen, her ton için bölümler (oturum
sınırıyla yan yana), birleştirme, giriş ve kapanış, numaralama, son okuma, düzeltmeler, denetim, çeviri (dilimler), iki dilde rakamlar,
sürüm. Geçersiz cevapta bir yeniden deneme; geçici hatada 1, 5, 15 dakika; kullanım eşiğinde ya da Claude'un sınır bildiriminde
sıfırlanma + 2 dakika (bilinmiyorsa 5, 10, 20, 40, 60 dakika) bekleme ve kendiliğinden sürme; "Durdur", "İptal et" ve programın
kapanması; "Devam" biten oturumları yeniden çalıştırmıyor; "Plandan sonra dur"; metin çalışması sürerken başka Claude çalışması ve
"Yenile" reddediliyor. Kapanma bekçisi metin çalışmasını iş sayıyor. İlerleme çubuğu aşamalardan ilerliyor; aşamanın metni, geçen ve
tahmini kalan süre yazıyor.

### Adım 6 — Metin verisi, numaralar, çeviri, sürümler

`metin.json` Housing Atlas'ın `makale.json`'una yakın kuruldu (parça, paragraf, numaralı cümle, iki dil, kanıtlar, uyarılar, terimler,
sürüm bilgisi). Cümle bölücü Housing Atlas'tan aynen taşındı (testleriyle). Kanıt işaretleri bölmeden önce cümleye bağlanıyor ve
cümlenin sonunda kalıyor. Son okuyucunun düzeltmelerini program uyguluyor; kanıt işaretini kaybeden düzeltme uygulanmıyor ve uyarı
olarak kalıyor. Her sürüm için `metin.json`, `metin_EN.md`, `metin_TR.md`, `seslendirme_EN.txt`, `metin_EN_kanitli.md`, `denetim.md`,
`denetim.json` yazılıyor. Hiçbir şey silinmiyor; seçim değiştirilebiliyor, eski seçim kayıtta kalıyor.

### Adım 7 — Program denetimi

Aşağıda ayrı bölümde.

### Adım 8 — Ekranlar

Video metni adımı (ton seçimi, "Metni yaz", paket notu, çalışmalar, "Devam", "Durdur", "Planı göster", "Karşılaştır", "Bu tonla da
yaz", "Planı yeniden yap"), plan görünümü, karşılaştırma ekranı (sütunlar, dil düğmesi, sütun başı sayıları, "Bu tonla devam et",
"Tek göster"), sürüm görünümü (numaralı cümleler, iki dil, kanıt kimlikleri üzerine gelince, denetim ve çevirmen uyarıları, terimler,
rapor, indirmeler), İşler panelindeki çubuk ve bekleme satırı, iş akışındaki durumlar, Ayarlar → Tonlar ve uyarı ifadeleri kutusu,
Ayarlar → Claude'daki yeni ayarlar. Türkçe düzeltme ekranının bu görevde olmadığını söyleyen not ekranda.

### Adım 9 — Testler

Görevin istediği listenin hepsi test edildi (dosyalar yukarıda). Sahte claude (`tests/fake_claude_text.py`) yedi adımı tanıyor, şemaya
uyan ve kanıt işaretli çıktı yazıyor; geçersiz cevap, geçici hata, kullanım sınırı (akışta sınır bildirimi ve hata metni), yavaş cevap,
planda bilinmeyen kimlik, eleştirmenden dönüş, son okumada işaret kaybı ve çeviride eksik numara canlandırılabiliyor. Saat taklit
ediliyor; testlerde gerçekten beklenmiyor. Görev sonunda iş akışı durumlarının testinin eksik olduğu görüldü ve eklendi
(`test_text_workflow.py`).

### Adım 10 — Gerçek ortam ve teslim

Geçici deneme, geçiş denemesi ve gerçek veritabanı aşağıda. Belgeler: yeni `docs/M17-VIDEO-METNI.md`; `CALISMA_MANTIGI.md`, `README.md`,
`docs/DEVIR/05` ve `02`, `docs/M15-CLAUDE-ADIMLARI.md`, `CLAUDE.md` güncellendi; yöneticinin üç tasarım belgesi `tasarim/` altında.

## Housing Atlas'tan taşınanlar ve bilerek değiştirilenler

Housing Atlas klasöründe hiçbir dosya değiştirilmedi; gereken dosyalar okunmak için `work/` altına kopyalandı.

Taşınanlar:
- `atlas/article/split.py` (İngilizce ve Türkçe cümle bölücü) ve testleri aynen; davranış değiştirilmedi (57 test geçiyor).
- `atlas/article/digits.py` (iki dilde rakam karşılaştırması) aynen.
- `makale.json` biçimine yakın veri: parça, paragraf, bütün metin boyunca tek sıra numaralı cümle, uyarılar, terimler, sürüm bilgisi.
- Çevirinin bütün parçalarla dilimlere bölünmesi (en çok 6.000 kelime).
- Geçici hata beklemeleri (`atlas/kesif/engine.py`) ve kullanım sınırı beklemesi (`atlas/kesif/limits.py`), daha sade biçimde.

Bilerek değiştirilenler:
- Housing Atlas metni içe aktarıp bölüyor; burada parçaları program kuruyor (plan, bölümler, geçişler, giriş, kapanış).
  `parse_article` taşınan testleriyle birlikte duruyor ama zincir onu kullanmıyor.
- Kanıt işaretlerinin cümleye bağlanması (`marks.py`) ve metnin sayılarının kanıtla toleranslı karşılaştırılması (`numbers.py`) bu
  projeye özgü. `numbers.py`, `digits.py`'nin rakam okuma yöntemini temel alıyor; kelimeyle yazılan yaygın sayıları ve sayının türünü
  (para, yüzde, sıcaklık, saat, yıl, sayım) da okuyor.
- Tek işçili Claude yapısı, metin çalışmasının kendi içinde paralel oturum açabileceği biçimde genişletildi; bir metin çalışması sürerken
  başka Claude çalışması başlamıyor.

## Şemaların özeti

**Veritabanı (şema 17, yalnız ekleme):**

| Tablo | İçerik |
|---|---|
| `text_runs` | metin çalışması: durum (çalışıyor, kullanım sınırı bekleniyor, duraklatıldı, yarıda kaldı, karşılaştırma bekliyor, hata), tonlar, paket, kesin plan, zincirin durumu, sebep, bekleme sonu, önceki çalışma |
| `text_sessions` | her Claude oturumu: adım, ton, parça, tur, deneme, durum, klasör, model, efor, ölçümler, sorunlar |
| `text_versions` | bir tonun metni: video başına numara, tonun dosyası, adı ve SHA-256'sı, kelime, cümle, kırmızı, sarı, bedel karşılığı, token, süre, paket |
| `text_selections` | "Bu tonla devam et" kayıtları (en yeni satır güncel seçim) |

**Claude çıktıları (`studio/ai/schemas/`):**

| Adım | Çıktı | Başlıca alanlar |
|---|---|---|
| Planlayıcı | `plan.json` | `bolumler` (5–7; no, iç adı, tek fikir, en çarpıcı an, kanıtlar, kelime bütçesi, açılış biçimi: rakam / sahne / soru / geçmiş / karşılaştırma / diğer), `kavramlar` (kavram → bölüm), `yeniden_kancalar`, `vaat_kontrolu` (karşılanan, karşılanamayan), `notlar` |
| Plan eleştirmeni | `plan_elestirisi.json` | `notlar`, `yeniden_yap` (evet/hayır) |
| Bölüm yazıcısı | `bolum.json` | `bolum_no`, `paragraflar` (kanıt işaretli), `yazici_notu` |
| Birleştirici | `birlestirme.json` | `gecisler` (önceki, sonraki bölüm, metin), `yeniden_kancalar` (hangi bölümden sonra, metin), `notlar` |
| Giriş ve kapanış | `giris_kapanis.json` | `giris`, `kapanis` (paragraflar), `onerilen_video` |
| Son okuyucu | `son_okuma.json` | `duzeltmeler` (cümle no, yeni cümle, gerekçe) |
| Çevirmen | `ceviri.json` | `cumleler` (no, Türkçe, uyarı), `terimler` (İngilizce, Türkçe, açıklama) |

## Program denetimi kuralları ve testleri

Denetim `studio/text/audit.py` ve `studio/text/numbers.py` içinde; Claude'a verilmez; her sürümde çalışır; kimseyi durdurmaz.

| Seviye | Kural | Test |
|---|---|---|
| Kırmızı | Mesafe (M13): "walking distance", "walkable", "a short walk", "minute walk", "minutes away", "minute drive" … | her kural için olumlu ve olumsuz örnek (`test_each_red_rule_of_the_usage_notes`); kuralların blok ve M belgesiyle eşleşmesi |
| Kırmızı | Fiyat (M11): "a week costs", "a week in … costs", "costs about $… a week", "per week it costs" | aynı |
| Kırmızı | Envanter (M10): "full inventory", "full list", "complete list", "every rental", "all the rentals", "there are … homes in" | aynı |
| Kırmızı | İklim (M8): "30A's climate", "the climate in 30A", "climate of 30A" | aynı |
| Kırmızı | Restoran (M12): "best restaurant", "the best place to eat", "most popular", "cheapest restaurant" | aynı |
| Kırmızı | Trafik (M9): "traffic jam", "gridlock", "bumper-to-bumper", "takes … minutes to get" | aynı |
| Kırmızı | Kaynak durumu (M9): işaret `dogrulanamadi` bir referans satırını gösteriyor | `test_a_row_that_could_not_be_verified_is_red_and_an_unknown_id_too` |
| Kırmızı | Pakette olmayan kimlik | aynı |
| Kırmızı | Sayı: işaretsiz sayılı cümle ya da işaretlerin değerleriyle tutmayan sayı | `test_the_tolerance_of_numbers`, `test_numbers_against_the_marks_of_a_sentence`, `test_roads_and_names_with_digits_are_not_numbers_and_years_come_from_the_row`, `test_words_and_times_are_read` |
| Sarı | Küçük örnekte iki mahallenin karşılaştırılması | `test_comparing_two_neighborhoods_from_a_small_sample_is_yellow` |
| Sarı | Kaynaksız "no public beach access" | `test_no_public_beach_access_without_a_source_is_a_question` |
| Sarı | `uyari_ifadeleri.txt` ifadeleri; "I" yalnız büyük harfle ve tek kelime | `test_the_warning_phrases_file_and_the_capital_i_rule`; dosyanın düzenlenmesi `test_the_warning_phrases_are_edited_with_the_instruction_rules` |
| Sarı | Uzunluk: metin 2.000'den az ya da 2.800'den çok kelime; bölüm bütçesinden %25'ten fazla sapma | `test_length_findings` |
| Plan | Pakette olmayan kimlik (plan bir kez geri döner), yeri olmayan kavram, aynı açılan komşu bölümler, bütçe toplamı 1.900–2.300 | `test_the_plan_check`; zincirde `test_the_plan_goes_back_once_for_an_unknown_id_and_then_errors` |

Rakam toleransının görevdeki örnekleri birebir test edildi: $7,223 → "about $7,200" ve "about $7,000" tutar; 84.2 °F → "84 degrees"
tutar; %7.1 → "about 7 percent" tutar; 87 ilan → "about 90 listings" tutar; $7,223 → "$7,500" tutmaz; 87 ilan → "90 listings" tutmaz.

## Geçici deneme (gerçek verinin kopyası, sahte claude)

Klasör `work/gorev-15/deneme` (gerçek veritabanının salt okunur kopyası, `claude/` ve `evidence/` kopyası; ayarlar sahte claude'u
gösterir), program 8841 portunda. Sahte claude yavaş kipte (her oturum 3 sn) çalıştı.

1. Geçici video kaydı: Rosemary Beach çalışmasının (`0d773a0c`) ilk adayı seçildi: "Rosemary Beach for Couples: Is It the Right Town for
   Two? | 30A Florida Vacation". Video paketi üretildi (6 bölüm).
2. "Araştırmacı dost" ve "Hikâye anlatıcısı" ile metin yazıldı (1. ve 2. sürüm). "Planı yeniden yap" ile ikinci çalışma açıldı (3. ve 4.
   sürüm); bu çalışmaya "Bu tonla da yaz" ile "Pratik planlayıcı" (5. sürüm) ve "Belgesel anlatıcı" (6. sürüm) eklendi. Toplam 2 çalışma,
   64 oturum (hepsi bitti), 6 sürüm; 3. sürüm seçildi ve iş akışı "tamamlandı" gösterdi.
3. Kullanım sınırı: 5 saatlik eşik geçici olarak %40'a indirildi (sahte ölçüm %43). Çalışma "Claude kullanım sınırı: 03:00'te
   kendiliğinden sürecek." diyerek bekledi; "Durdur" ile "duraklatıldı" oldu; eşik %90'a geri alındı ve "Devam" ile kalan ton yazıldı.
   Bir kez de beklerken program kapatıldı: açılışta çalışma ve işi "yarıda kaldı" gösterdi, "Devam" biten oturumları yeniden yapmadan
   sürdü.
4. Ayarlar → Tonlar: "Sakin rehber" eklendi, "Sakin rehber (deneme)" olarak düzenlendi, silindi (arşive gitti), geri alındı, yeniden
   silindi. Ton geçici klasörün arşivinde duruyor; depodaki ton klasörü ilk hâlinde (git temiz).
5. Ekran görüntüleri alındı (aşağıdaki liste).

Denemede görülüp düzeltilenler:
- İşler panelinde bekleme sırasında aşamanın yerinde iç adım adı ("metin_bolum") görünüyordu; artık "Belgesel anlatıcı (4/4 ton) ·
  bölümler 0/6 bitti" gibi aşamanın metni duruyor. Testi var.
- Bekleme cümlesi İşler panelinde iki kez yazılıyordu; bir kez yazılıyor.
- Program beklenmedik biçimde kapanınca (süreç kesilince) metin işinin mesajı kaynak kontrollerinin genel cümlesiydi ("Kontrolü yeniden
  başlatabilirsiniz"); artık "Program kapanırken yarıda kaldı; “Devam” kalan adımları çalıştırır." Testi var.
- Ton listesindeki "ilk satır" bütün paragraftı; 160 karakterde kısaltılıyor. Plan tablosunun sütun genişlikleri düzeltildi.

Deneme sürümünün dosyaları `deneme-surumu/` altında (3. sürüm, "Araştırmacı dost"; sahte claude çıktısı olduğu `BENIOKU.md`'de yazıyor).

## Geçiş denemesi (şema 16 → 17, kopyada)

Gerçek veritabanının `work/` kopyasında: 165.257 satır önce ve sonra aynı; yalnız dört yeni boş tablo; `integrity_check` ok,
`foreign_key_check` boş; uygulamanın kendi yedeği `studio-v16-*.sqlite3` alındı.

## Gerçek veritabanı: önce ve sonra

1. Program kapalıyken `data/` tam yedeği: `work/yedek/20261011-0211/` (45.495 dosya, 1.443.621.916 bayt; kopya ve kaynak SHA-256 ile
   doğrulandı).
2. Program masaüstü kısayoluyla açıldı (sürüm 0.17.0, port 8830); geçiş çalıştı; uygulamanın kendi yedeği
   `data/backups/studio-v16-50669303f5104ef0955e9165096af161.sqlite3`.
3. Ayarlar → Tonlar: beş ton, varsayılan "Araştırmacı dost", arşiv boş. Ayarlar → Claude: yedi yeni adım, oturum sınırı 3, eşikler %90 ve
   %95, "Plandan sonra dur" kapalı (ekran görüntüleri `10a`, `10b`).
4. Claude çalıştırılmadı; başlık seçilmedi; video kaydı açılmadı; toplayıcı çalışmadı.
5. Program penceresinden kapatıldı; kapanma bekçisi programı kapattı; `data/` içinde -wal/-shm dosyası kalmadı.

| | Önce | Sonra |
|---|---|---|
| `user_version` | 16 | 17 |
| Eski tabloların satırları | 165.257 | 165.257 (hepsi aynı) |
| `text_runs`, `text_sessions`, `text_versions`, `text_selections` | — | 0, 0, 0, 0 |
| `integrity_check` | ok | ok |
| `foreign_key_check` | boş | boş |

GÖREV-14'ün sonundaki sayımla bu görevin "önce" sayımı da aynıydı. Programın günlüğünde, bu görevden önce (11 Ekim 00:09) programın
bir dakikalığına açılıp kapandığı görülüyor; veritabanında bir değişiklik bırakmamış.

## Beklenmedik durumlar

- **Bir test modüllerin yüklenme sırasına bağlıydı.** Talimat listesinin sırası adımların kaydolma sırasından geliyordu; testler başka
  sırayla çalışınca liste farklı sıralanıyordu. Sıra artık Ayarlar'daki adım listesinden geliyor (program açılışında zaten doğruydu).
- **Bir ara çalıştırmada bir test bir kez düştü** (zincir ve ton testleri birlikteyken 33'ten 1'i); hemen ardından aynı dosyalar 4 kez,
  tam takım da 4 kez çalıştı ve tekrar etmedi. Hangi test olduğu o çıktıda kaydedilmedi. CI'da görülürse kararsız test olarak ele
  alınmalı.
- **İş akışında "eskidi" kuralı** ilk yazımda "veri yeniden çekildi *ya da* paket değişti" idi; görevdeki tablo "*ve*" diyor. Tabloya
  uyduruldu ve testlendi.
- **İş akışı durumlarının testi eksikti** (Adım 9'un listesinde var); görev sonunda eklendi.
- Denemede görülen dört küçük ekran ve mesaj sorunu (yukarıda) düzeltildi.

## Yöneticinin karar vermesi gereken konular

1. **İlk gerçek metin.** Gerçek veride henüz seçilmiş başlık ve video kaydı yok. İlk gerçek metin için kullanıcının bir başlık seçip
   paketini üretmesi gerekiyor. Bir tonluk bir metin yaklaşık 10–12 Opus oturumu ve 1 Sonnet oturumu demek (plan ve eleştiri 2, planın 5–7
   bölümü, birleştirme, giriş ve kapanış, son okuma; çeviri Sonnet). Her ek ton planı yeniden kullanır (8–10 Opus, 1 Sonnet). Kullanım ve süre ölçülmedi. Öneri: ilk denemede tek ton ve "Plandan sonra dur" açık; plan
   görüldükten sonra "Devam".
2. **`paket_ozeti.md`'nin "Video" bölümü Claude'a verilmiyor.** O bölüm başlık önerisinin kaynak paketlerindeki kimlikleri listeliyor;
   video paketinin kimlikleriyle karışıp planın "pakette olmayan kimlik" diye geri dönmesine yol açıyordu. Bölümün yerine tek satır
   konuyor: analiz `baslik_analizi.md`'de ve oradaki kimlikler bu özetin kimlikleri. Paket dosyası değişmiyor; yalnız Claude'a giden
   kopya. Onayınız gerekir.
3. **Seçimden sonra çalışmanın durumu.** Bir sürüm seçilince iş akışı "tamamlandı" gösteriyor ama çalışmalar listesinde çalışma
   "karşılaştırma bekliyor" olarak kalıyor (çalışmanın kendi durumu değişmiyor). İstenirse listede "seçildi" gösterilebilir.
4. **`metin_EN.md`'deki başlıklar** planın iç adlarından ve "Giriş", "Kapanış" sözcüklerinden geliyor (okuma dosyası; seslendirme
   dosyasında başlık yok). İngilizce başlık istenirse plana İngilizce bölüm adı alanı eklenebilir.
5. **Model ve efor değerleri** Ek N'deki başlangıç değerleri (aile adları: opus, sonnet). İlk gerçek denemeden sonra gözden geçirilmeli.

## Teslim edilenler (bu klasör)

- `GOREV.md` (görev metni), `RAPOR.md` (bu rapor)
- `tasarim/`: `30A_YAZIM_ZINCIRI.md`, `30A_SES_VE_TONLAR.md`, `30A_HALKA_TALIMATLARI.md` (yöneticinin belgeleri)
- `deneme-surumu/`: `metin_EN.md`, `metin_TR.md`, `seslendirme_EN.txt`, `metin_EN_kanitli.md`, `denetim.md`, `BENIOKU.md` (sahte claude
  çıktısı)
- `ekran/` (geçici klasör ve sahte claude; `10a`, `10b` gerçek veriyle):
  - `01-ayarlar-tonlar-liste-ve-arsiv.png`, `02-ayarlar-yeni-ton-formu.png`
  - `03-video-metni-ton-secimi.png`, `03b-video-metni-calismalar-bekleme.png`, `03c-video-metni-secilen-surum.png`,
    `03d-video-metni-yarida-kaldi.png`
  - `04-plan-gorunumu.png`
  - `05a-karsilastirma-turkce.png`, `05b-karsilastirma-ingilizce.png`
  - `06a-surum-gorunumu-ust.png`, `06b-surum-gorunumu-kirmizi-isaret.png`
  - `07a-isler-zincir-ilerleme.png`, `07b-isler-kullanim-siniri-beklemesi.png`
  - `09-ayarlar-claude.png`
  - `10a-gercek-ayarlar-tonlar.png`, `10b-gercek-ayarlar-claude.png`
  - `12a-is-akisi-metin-bekliyor.png`, `12b-is-akisi-metin-hazir.png`, `12c-is-akisi-metin-calisiyor.png`,
    `12d-is-akisi-metin-onay-bekliyor.png`, `12e-is-akisi-metin-duraklatildi.png`, `12f-is-akisi-metin-tamamlandi.png`
