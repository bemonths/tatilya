# GÖREV-14 raporu — masaüstü programı, iş akışı, Claude kullanımı ve talimatlar, kendi başlık, içerik planından video paketi, tarayıcı eklentisi

Tarih: 10 Ekim 2026 · Dal: `gorev-14-masaustu-eklenti` · Uygulama 0.16.0 · Şema 16

## Kısaca

- main, GÖREV-13'ün son commit'ine (`a59ec65`) alındı ve `v0.15.0` etiketi kondu. main ve etiket CI başarılı.
- Program artık masaüstü programı gibi açılıyor: masaüstündeki "30A Studio" simgesi, konsol penceresi yok, kendi penceresi var. Pencere kapanınca program da kapanıyor; bir iş sürüyorsa iş bitince kapanıyor.
- Sol menüde seçili videonun sekiz adımı ve her birinin durumu görünüyor. Altında Claude kullanımı (5 saatlik ve haftalık) var.
- İşler panelinde Claude çalışmasının ilerleme çubuğu, geçen süre ve tahmini kalan süre görünüyor.
- Talimat dosyaları Ayarlar → Talimatlar'dan düzenlenebiliyor; önceki sürümler saklanıyor.
- Kullanıcı kendi başlığını ya da fikrini yazıp Claude'a değerlendirtebiliyor. Önerilen başlık seçilmeden önce düzenlenebiliyor.
- Video paketi seçilen başlığın içerik planından kuruluyor. Özet tablolarında hafta tarihleri yazıyor.
- "30A Studio Yardımcısı" Chrome eklentisi hazır. Yalnız yerel deneme sayfalarında sınandı. Eklentiyi kullanıcı kendi Chrome'una kuracak.
- Toplulukların (Seaside, WaterColor, Alys Beach, Rosemary Beach, Watersound) plaj erişimi için 13 kaynaklı satır eklendi.
- Gerçek veride iki küçük gerçek Claude çalıştırması yapıldı. "Rosemary Beach'e köpeğimizle gitsek nasıl olur?" fikri için Claude dürüstçe "veriyle dolmuyor" dedi ve eksik veriyi yazdı.

## Konumlar, CI ve testler

| | Konum | CI |
|---|---|---|
| GÖREV-13 dalı son commit | `a59ec652525bdccf753c8ce763e1757b9c767b69` | başarılı |
| main (fast-forward, push) | `a59ec652525bdccf753c8ce763e1757b9c767b69` | 38077344443 başarılı |
| Etiket `v0.15.0` (açıklamalı, push) | `a59ec65` — "v0.15.0 — programın içinde Claude: çalıştırıcı, Claude ayarları, Videolar ekranı ve konu ve başlık önerisi" | 38077345949 başarılı |
| Görev dalı | `gorev-14-masaustu-eklenti` | aşağıda |

Görev dalının CI sonuçları (GitHub Actions, Linux):

| Commit | Sonuç |
|---|---|
| `e2ef1ca` (video paketi) | 38081330720 **başarısız**: `test_a_runs_usage_reports_are_stored_with_their_time_and_shown` — sahte Claude çok hızlı bittiği için çalışma süresi 0,0 sn'ye yuvarlandı, test "süre > 0" bekliyordu. Kod hatası değil, test kararsızdı. |
| `d4a1272` (eklenti) | 38082784783 başarılı |
| `357f3b7` (gerçek çalışmadaki düzeltme) | 38084479989 başarılı |

Kararsız test düzeltildi: artık haftalık toplamı çalışmanın kendi ölçülen süresiyle karşılaştırıyor. Son commit'lerin CI sonucu dalda görülebilir.

Testler (yerel, Windows), tam takım art arda 3 kez:

| Tur | Python | Frontend |
|---|---|---|
| 1 | 889 geçti, 1 atlandı (3 dk 32 sn) | 81 geçti |
| 2 | 889 geçti, 1 atlandı (3 dk 38 sn) | 81 geçti |
| 3 | 889 geçti, 1 atlandı (3 dk 40 sn) | 81 geçti |

Atlanan test eklentinin uçtan uca denemesidir; ayrıca çalıştırılır (`STUDIO_EKLENTI_E2E=1`, aşağıda Adım 7). main'de 768 Python + 64 frontend testi vardı. Testler gerçek Claude'u çağırmaz; sahte claude kullanılır.

## Adımların sonucu

### Adım 1 — v0.15.0 ve yöneticinin talimat dosyaları
- `a59ec65`'in CI'ı başarılıydı. main bu commit'e fast-forward edildi, `v0.15.0` etiketi kondu, ikisi de push edildi; CI başarılı.
- Yöneticinin çalışma ağacında güncellediği iki dosya (`baslik.md`, `kanal_arastirmasi.md`) kaybolmadan yeni dalın ilk commit'i oldu (`b2d46e9`, görev metnindeki mesajla).
- 1b: yöneticinin GÖREV-13 sonrası kararları Adım 4d (model listesi), 4e (başlık eki), 6a–6c (plan paketi, hafta tarihleri, restoran notu) ve 8'de (plaj erişimi) uygulandı.

### Adım 2 — Masaüstü programı
- Konsolsuz açılış (`pythonw -X utf8 -m studio`), uygulama kipi pencere (önce Edge, yoksa Chrome, yoksa varsayılan tarayıcı; pencere adı "30A Studio").
- Tek kopya: program açıksa ikinci açılış yeni sunucu açmıyor, açık pencereyi öne getiriyor. Denendi: günlükte "Program zaten çalışıyor (port 8830); yeni sunucu açılmadı." ve "Program penceresi zaten açık; öne getirildi."
- Port 8830–8849 (Housing Atlas 8790–8809; ikisi aynı anda açık olabilir).
- Kapanma bekçisi: denendi.
  - Pencere kapanınca 8 sn içinde "Pencere kapalı ve çalışan iş yok; uygulama kapanıyor." ve "Program kapandı."; kilit dosyası silindi.
  - 60 sn süren (sahte) bir Claude çalışması sırasında pencere kapatıldı: "Pencere kapandı; çalışan iş bitince uygulama kapanacak." hem uygulama günlüğüne hem işin günlüğüne yazıldı; iş bittikten 1 sn sonra program kapandı.
  - Gerçek veride pencere kapatılınca program 45 sn sonra kendiliğinden kapandı.
- Başlatma başarısız olursa Türkçe hata kutusu. Günlük `data/gunluk/uygulama.log`.
- `baslat.bat` ilk seferde kurar, kısayolu oluşturur ve konsolsuz başlatır; kurulum damgası tutmazsa (paketler değiştiyse) program kurulumu kendisi başlatır. Bu bilgisayarda kurulum damgası yazıldı (paket kurulumu gerekmedi).
- `kisayol-olustur.ps1` masaüstüne simgeli "30A Studio" kısayolu oluşturdu (Unicode yollar için Housing Atlas'taki yöntem). Gerçek veriyle açılış bu kısayolla yapıldı (Adım 9.4).
- Simge: `tools/make_icon.py` ile sade bir "30A" simgesi (`studio/web/img/30a.ico`, `.svg`, `-192.png`).
- Geliştirme komutu aynen çalışıyor: `python -m studio --data-dir … --no-browser --port …`; ayrıca `--no-window` ve `--no-watchdog`. Ctrl+C ya da Ctrl+Break ile düzgün kapanıyor (çıkış kodu 0, kilit siliniyor).
- Testler: `test_launcher.py` (45), `test_watchdog.py` (14), `test_launch_files.py` (7).

### Adım 3 — İş akışı paneli
- Üst çubukta video seçici ("Video seçilmedi" ve video kayıtları) ve "●●○○○○○○ 2/8 adım" göstergesi.
- ADIMLAR: 1 Veri · 2 Konu ve başlık · 3 Veri paketi · 4 Video metni · 5 Kontrol · 6 Görsel plan · 7 Video üretimi · 8 Yayın hazırlığı. Kurulmamış beş adım "planlanan".
- Durumlar ayrı bir dosyada tutulmuyor; her seferinde kayıtlardan hesaplanıyor (video kaydı, Claude çalışmaları, paketler, çekimler). Veri: "güncelleme zamanı geldi" / "güncel"; Konu ve başlık: "onay bekliyor" / "onaylandı"; Veri paketi: "tamamlandı" / "eskidi".
- Her adımın ekranı "Sıradaki iş" satırıyla başlıyor. VERİ grubunda dört araç ekranı; "Rakip analizi" ve "İçerik briefi" yer tutucuları kalktı; Ayarlar en altta.
- Geçici denemede: video yokken ve geçici bir video kaydıyla görüntü alındı; paket üretilince 2/8 → 3/8 oldu.
- Testler: `test_workflow.py` (6) ve frontend testleri.

### Adım 4 — Kullanım paneli, ilerleme çubuğu, talimat düzenleyici, model listesi, başlık eki
- **Kullanım paneli** (sol menünün altında): 5 saatlik ve haftalık yüzde, sıfırlanma zamanı, "son ölçüm", bu haftaki çalışma sayısı ve süresi. Ölçümler Claude'un her cevaptan sonra verdiği kullanım bilgisinden ve "Yenile" düğmesinden geliyor; her ölçüm zamanıyla saklanıyor (`claude_usage`). "Yenile": araçsız, tek tur, `haiku`, düşük efor; Ayarlar → Claude'da yazıyor. Ölçüm yoksa "henüz ölçüm yok", 5 saatten eskiyse soluk ve "eski ölçüm".
- **İlerleme çubuğu**: girdiler %0–10, Claude %10–90 (geçen süre / aynı adımın önceki başarılı çalışmalarının ortanca süresi; yoksa başlıkta 7 dk, değerlendirmede 5 dk), doğrulama %90–100. Yanında yüzde, geçen süre, tahmini kalan süre; "Tur 3/30 · …" satırı altında. Toplayıcı işlerinin ilerlemesi değişmedi.
- **Talimat düzenleyici** (Ayarlar → Talimatlar): ortak, başlık, başlık değerlendirme ve bilgi dosyası olarak kanal araştırması. Tek kaynak depodaki dosya. Dosya açıldığından beri diskte değiştiyse kayıt yapılmıyor ve uyarı veriliyor. Her kayıttan önce önceki hâl `data/claude/talimat_gecmisi/` altında; "Bu sürüme dön" var. Çalışma ekranında kullanılan talimat sürümleri görünüyor.
  - Geçici denemede: kaydet → dışarıdan değişiklikte ret (409) → eski sürüme dön; dosya denemenin sonunda bayt bayt ilk hâline döndü.
- **Model listesi**: `claude-sonnet-5-5` ve aile takma adları `opus`, `sonnet`, `haiku` eklendi.
- **Başlık eki**: Ayarlar'da İngilizce (" | 30A Florida Vacation") ve Türkçe (" | 30A Florida Tatili") ek; `secim.md`'ye yazılıyor; doğrulayıcı denetliyor. `baslik.md`'deki cümle Ek B'deki cümleyle değiştirildi, dosyanın geri kalanına dokunulmadı.
- Testler: `test_claude_panel.py` (10) ve frontend testleri.

### Adım 5 — Kendi başlığını değerlendirme ve seçmeden önce düzenleme
- Videolar ekranında "Kendi başlığını yaz" (başlık ya da fikir, bölge, not). Yeni Claude adımı "Başlık değerlendirme": talimatlar `ortak.md` + `baslik_degerlendirme.md` (Ek A, aynen), girdiler başlık adımınınkiler + `kullanici_basligi.md` + `baslik_olculeri.md`.
- Onay ekranı: önce değerlendirme özeti (veriyle doluyor mu, açıklama, eksik veri, kullanıcının ifadesindeki sorunlar), sonra en çok 3 aday ve "Bu başlığı seç".
- "Başlığı düzenle": İngilizce başlık ve Türkçe karşılık değiştirilebiliyor; uzunluk ve ek denetleniyor. Yalnız Türkçe değiştiyse "İngilizcesini Claude yazsın" yeni bir değerlendirme çalışması açıyor. Video kaydı önerilen başlığı da tutuyor ve "kullanıcı düzenledi" işareti taşıyor.
- Geçici denemede: değerlendirme, Türkçe düzenlemeden değerlendirme ve düzenlenmiş başlıkla seçim (geçici video kaydı) yapıldı.
- Testler: `test_title_review.py` (7) ve frontend testleri.

### Adım 6 — İçerik planından video paketi, hafta tarihleri, restoran notu
- Video kaydının paketi artık seçilen adayın içerik planından kuruluyor: bölümler planın bölümleri; her bölümde planın kanıt satırları ve ait oldukları blokların tamamı; bir blok ilk geçtiği bölümde tam, sonra gönderme. Başta başlık, soru, kanca, neden önerildiği, eksik veri, bilinen boşluklar ve yayından önce kontrol edilecek satırlar. Yazar özeti ve sayı listesi aynı makineyle. "Yeni şablon gerekir" artık paketi engellemiyor.
- Gerçek verinin kopyasında deneme: Rosemary Beach çalışmasının ilk adayından 6 bölüm, 118 satır; planın bütün kanıtları aynı değerle bulundu.
- Yazar özetinde pencere sütunları tarihli: "Mar 2027 (13–20)". Aynı aydaki iki pencere ayrı sütun.
- Restoran tablolarında mahalle toplamının restoran sayısından neden büyük olduğu yazıyor (birden çok mahalleye bağlı restoranlar); sayılar üretim anında hesaplanıyor.
- Testler: `test_video_plan_pack.py` (4).

### Adım 7 — "30A Studio Yardımcısı" eklentisi
- Eklenti `eklenti/` klasöründe (Manifest V3, Türkçe arayüz, kod sıkıştırılmamış). Program tarafı `studio/extension.py`, okuyucular `studio/sources/extension_reader.py`.
- Eşleşme kodu Ayarlar → Tarayıcı eklentisi'nde; eklenti programı 8830–8849'da kendisi buluyor.
- Okuma sırası: doğrudan istek → engel varsa ve eklenti bağlıysa eklenti → değilse programın kendi tarayıcısı → atla ve kaydet. `browser_hosts.method` hangi yöntemin işe yaradığını tutuyor.
- Restoran siteleri ve kiralama şirketleri bu katmanı kullanıyor. Günlük ihtiyaç zincir kontrolleri canlı okunmuyor (gözden geçirilmiş dosyadan geliyor); bu sitelerin sayfaları "Sorunlu sitelerden birer sayfa dene" ile okunabiliyor.
- Eklenti beklenirken iş panelinde "Eklenti bekleniyor: … Chrome'u açın" ve "Programın tarayıcısına devret" düğmesi.
- Kurulum rehberi resimli: `eklenti/KURULUM.md` (kopyası bu klasörde `eklenti-kurulum/`). Rehber resimleri Playwright'in Chromium'unda geçici profille alındı.
- "Sorunlu sitelerden birer sayfa dene" düğmesine basılmadı (kullanıcı basacak). Eklentiyle gerçek sitelerden veri çekilmedi.
- Uçtan uca deneme (Playwright'in Chromium'u, geçici profil, yalnız yerel deneme sunucusu): normal sayfa, JavaScript ile çizilen sayfa, kendiliğinden geçen ve geçmeyen doğrulama sayfası, giriş sayfası, JSON ucu; kullanıcının sekmesine dokunulmadığı ve eklenti penceresinin kapandığı denetlendi. 4 çalıştırmada 3'ü geçti; ilk çalıştırma 2 sn'de Chromium açılırken hata verdi, sonraki 3 çalıştırma art arda geçti (her biri ~31 sn).
- Testler: Node (iş kuyruğu, hız sınırı, doğrulama tanıma, giriş ve ödeme sayfası tanıma, izinler, bekleme kuralı, Ayarlar ekranı), `test_extension.py` (13), `test_extension_e2e.py` (1, isteğe bağlı).
- Belge: `docs/M16-TARAYICI-EKLENTISI.md`; CLAUDE.md'deki tarayıcı kuralına eklenti yöntemi eklendi.

### Adım 8 — Toplulukların plaj erişimi
13 satır `plaj-erisimi` konusuna eklendi; her biri topluluğun, topluluk derneğinin ya da resmî kiralama şirketinin sitesinden, kısa alıntı, tarih ve belgenin SHA-256'sıyla. Satırlar mahalle paketine de giriyor (gerçek değerlendirme çalışmasında Rosemary Beach özetinde göründü).

| Topluluk | Bulunanlar | Bulunamayanlar |
|---|---|---|
| Seaside | Kiracı, evin sokağındaki pavyonu kullanır (Seaside SSS, 2024). Halk Coleman Pavyonu'ndan Cabana Man rezervasyonuyla girer. Van Ness Butler erişimi artık halka açık değil (ilçe listesinde de yok). | Pavyonların sayısı ve adları, rampa (resmî kaynakta yok). |
| WaterColor | Beach Club'da kumul geçidi; batı iskelesinde ADA rampası. Yalnız WaterColor sakinleri ve WaterColor Inn misafirleri. 5 yaş üstüne bileklik (iade edilmezse 50 $). | Geçit sayısı. |
| Alys Beach | Ev sahipleri ve kiracılar Gulf Green, Turtle Bale ve Béla Gray'den girer; Beach Club yalnız ev sahiplerine (2026). | Erişilebilirlik (rampa, merdiven). |
| Rosemary Beach | Kiralık ev 9 özel plaj geçidinden erişimi içerir (kiralama şirketinin ilanı). Sandalye, konutun plaj erişim koduyla ayırtılır. Kiracıya park kartı verilir. | Geçitlerin adları ve yerleri, rampa; topluluk derneğinin (RBPOA) erişimi anlatan resmî bir sayfası bulunamadı. |
| Watersound | Beach Club'da üyelere özel iskele. Watersound Inn misafirleri Beach Club'ı kullanır. Watersound kendi topluluklarında tatil evi kiralamıyor. | Kiracı erişimi (kiralama olmadığı için), erişilebilirlik, misafir otoparkı. |

Giriş gerektiren sayfaya girilmedi. Bulunamayanlar tahmin edilmedi.

### Adım 9 — Gerçek ortam
- **9.1 Geçici deneme** (gerçek verinin kopyası, sahte Claude): masaüstü penceresi, tek kopya ve kapanma; iş akışı (video yok / geçici video); kullanım paneli ve ilerleme çubuğu; talimat düzenleyici; kendi başlığını değerlendirme ve seçmeden önce düzenleme; geçici video kaydından plan paketi; eklenti (geçici profil, yerel sayfalar). Hepsi çalıştı; ekran görüntüleri `ekran/` klasöründe.
- **9.2 Geçiş denemesi** (gerçek verinin kopyası, 15 → 16): 165.250 satır önce ve sonra aynı; yeni boş tablolar `claude_usage`, `job_progress`; `integrity_check` ok, `foreign_key_check` boş; uygulama kendi yedeğini aldı.
- **9.3 Gerçek veritabanı**: aşağıda.
- **9.4 Masaüstü kısayolu**: `C:\Users\1\Desktop\30A Studio.lnk` oluşturuldu (hedef `.venv\Scripts\pythonw.exe -X utf8 -m studio`, simge `30a.ico`). Program gerçek veriyle bu kısayoldan açıldı.
- **9.5 Değerlendirme çalışması**: aşağıda.
- **9.6 Belgeler**: CALISMA_MANTIGI.md, README.md (masaüstü kısayolu, eklenti kurulumu), DEVIR/05 ve 02, M14 (plan paketi, hafta tarihleri, restoran notu), M15 (kullanım paneli, ilerleme, talimat düzenleyici, başlık değerlendirme, düzenleme, başlık eki), yeni M16, CLAUDE.md (tarayıcı kuralı) güncellendi. Tam test takımı art arda 3 kez geçti.

## Gerçek değerlendirme çalışması

Bölge Rosemary Beach; başlık "Rosemary Beach'e köpeğimizle gitsek nasıl olur?"; not boş. Dosyalar: `gercek-degerlendirme/` (JSON, Markdown, görev metni, çalışma kaydı; akış kaydı yok).

- **Sonuç:** fikir veriyle **dolmuyor**; aday yok. Claude bunu açıkça söyledi: elimizdeki tek güçlü bilgi ilçenin halka açık plajlarındaki köpek yasağı ve bu Rosemary'ye özgü değil, bütün 30A için geçerli; Rosemary'nin kendi özel plajında köpek kuralı olup olmadığını hiçbir kaynağımız söylemiyor. "Elimizdeki bilgiyle yaklaşık bir dakikalık bir bölüm kurulabiliyor" dedi. Kullanıcıyı memnun etmek için plan kurmadı. Bu, görev metnindeki beklentiyle aynı.
- **Eksik veri (7):** topluluğun köpek kuralı; kiralık evlerin evcil hayvan kuralı; iki otelin evcil hayvan politikası; restoranların köpek kabulü; veteriner uzaklığı; köpekle gidilebilecek yerler; ziyaretçi köpeklerinin girebildiği en yakın plaj.
- **Kullanıcının ifadesindeki sorunlar (3):** Türkçe bir soru, İngilizce başlığa çevrilip " | 30A Florida Vacation" ekiyle bitmeli; "nasıl olur" çok geniş, aranan ifade daha somut ("Rosemary Beach dog friendly") ama bu sorulara bugün verimiz cevap veremiyor; "Rosemary Beach'te köpeğiniz plaja çıkamaz" gibi bir başlık kanıtın ötesine geçer.
- **Kanıt değerleri:** hepsi veri özetindeki satırlarla aynı. 30A özeti: K0097 (halka açık plajlarda hayvan yasak; hizmet hayvanı ve ilçe izni istisna), K0098 (izin yalnız mülk sahibi ve daimi sakine; tasmalı, 15:30–08:30), K0119 (ihlal başına 500 $'a kadar). Mahalle özeti: K0002 (Rosemary'de eşlenen halka açık erişim 0), K0005 (Visit South Walton 2023 rehberi Rosemary'de halka açık erişim listelemiyor), K0007 (9 özel geçit), K0008 (konuta özel erişim kodu) — son ikisi bu görevde eklenen satırlar.
  - Küçük bir genelleme: "iki otel" ifadesi o tarihli Book>Direct aramasında "Hotels" kategorisinde görünen 2 ilandan geliyor; eksik veri maddesinde, değerlendirmeyi değiştirmiyor.
- **Ek kuralı:** aday olmadığı için başlıkta ek denetimi yok; Claude, kullanıcının ifadesinde ekin eksik olduğunu doğru eki yazarak söyledi. Çalışmanın seçiminde ek ayardaki değerle kaydedildi.
- **Ölçüm:** Opus 5.5 (`claude-opus-5-5`), yüksek efor, Claude Code 2.1.284; 78 sn (Claude'un tarafı 76 sn, düşünme 37 sn); 6 tur, 13 araç çağrısı (12 okuma, 1 yazma), reddedilen çağrı yok; token: önbelleğe yazma 120.852, önbellekten okuma 295.192, yeni girdi 12, çıktı 7.618; maliyet karşılığı 1,18 $ (abonelikle çalıştı).
- Veri özetleri yeniden üretildi (program dosyaları önceki paketten sonra değiştiği için): `ilk-video` ve `mahalle-rehberi` birer paket.
- Programda bulunan bir kusur düzeltildi: aday çıkmayınca iş mesajı "0 aday onay bekliyor" diyordu; artık "fikir veriyle dolmuyor; başlık adayı yok" diyor (test eklendi).

**Kullanım ölçümü ("Yenile"):** 4,4 sn; `haiku` takma adı Claude Haiku 4.5'e (`claude-haiku-4-5-20251001`) gitti; düşük efor; maliyet karşılığı 0,005 $. Ölçüm: 5 saatlik %11, haftalık %43. Değerlendirme çalışması da bir ölçüm bıraktı (aynı değerler).

## Gerçek veritabanı: önce ve sonra

- Önce: uygulama kapalıyken `data/` tam yedeği `work/yedek/20261010-2330/` (45.465 dosya, 1,39 GB; kopya ve kaynak SHA-256 ile doğrulandı).
- Program masaüstü kısayoluyla gerçek veriyle açıldı; uygulama 15 → 16 geçişinden önce kendi yedeğini aldı (`data/backups/studio-v15-214465b2fb1a477cb2a9c3c599af43de.sqlite3`).
- `/api/references`: 165 satır, sorun yok; yeni 13 satırın hepsi yüklendi.
- İki gerçek çalıştırma yapıldı. Başlık seçilmedi, video kaydı açılmadı, toplayıcı çalışmadı.
- Pencere kapatıldı; program kendiliğinden kapandı; `data/` içinde -wal/-shm kalmadı.

| | Önce | Sonra |
|---|---|---|
| Şema (`user_version`) | 15 | 16 |
| `integrity_check` | ok | ok |
| `foreign_key_check` | boş | boş |
| `claude_runs` | 3 | 4 |
| `claude_usage` | — | 2 |
| `evidence_packs` | 6 | 8 |
| `jobs` | 36 | 37 |
| `job_progress` | — | 1 |
| `videos` | 0 | 0 |
| Diğer bütün tablolar | aynı | aynı |
| Toplam satır | 165.250 | 165.257 |

`source_runs` ve `sources` satırları birebir aynı. `data/` içinde yeni dosyalar: `gunluk/uygulama.log`, `eklenti.json` (eşleşme kodu), `baslatiliyor.kilit` (boş başlatma kilidi; Housing Atlas'taki gibi yerinde kalır), `claude/` altında iki çalışma klasörü, `evidence/` altında iki paket.

## Housing Atlas'tan taşınanlar ve bilerek değiştirilenler

Housing Atlas klasöründe hiçbir dosya değiştirilmedi; yalnız okundu.

| Konu | Taşınan | Bilerek değiştirilen |
|---|---|---|
| Başlatıcı (`atlas/launcher.py`) | Konsolsuz açılış, başlatma kilidi, çalışma kilidi + `/api/health` pid denetimi, uygulama kipi pencere (Edge → Chrome → varsayılan), pencereyi başlığından bulup öne getirme, SelectorEventLoop, Türkçe hata kutusu, kurulum damgası ve kurulumu kendiliğinden başlatma | Port 8830–8849; veri klasörü `--data-dir` ya da depodaki `data/`; pencere başlığı "30A Studio" ya da "30A Studio · …"; Ctrl+C / Ctrl+Break'te sunucu sinyali yeniden tetiklemiyor (çıkış kodu 0, kilit siliniyor) ve açık olay akışları kapanışı bekletmiyor; bekçi yalnız pencere açılınca çalışıyor |
| Kapanma bekçisi (`atlas/watchdog.py`) | Canlılık sinyali ve olay akışı sayımı, 45 sn / 120 sn, ortam değişkeniyle süre değiştirme (`STUDIO_WATCHDOG_*`), çalışan iş varken bekleme | Bekleme notu yalnız günlüğe değil, çalışan işin günlüğüne (İşler paneli) de yazılıyor |
| `baslat.bat`, `kisayol-olustur.ps1`, `tools/make_icon.py` | Kurulum akışı, yalnız ASCII ve CRLF bat dosyası, IShellLinkW ile Unicode kısayol, standart kütüphaneyle simge | 30A simgesi; CRLF kuralı `.gitattributes` ile depoda da sabitlendi |
| Sol menü ve durumlar (TASARIM 6, 7.2; `atlas/state.py`) | Durum kodları (bekliyor, hazır, çalışıyor, onay bekliyor, onaylandı, tamamlandı, hata, eskidi), adım listesi ve sıradaki iş fikri | Birim eyalet değil video; durumlar dosyada tutulmuyor, her seferinde kayıtlardan hesaplanıyor; iki ek durum: "güncelleme zamanı geldi" ve "planlanan" |
| Kullanım (`atlas/claude_usage.py`, `rate_limit_event`) | Akıştaki kullanım bilgisini okuma, 5 saatlik ve haftalık pencere | Daha sade panel; her ölçüm veritabanında saklanıyor; "Yenile" en küçük çağrıyla (görev metni) |
| İlerleme çubuğu (`jobs-panel.js`) | Dolan çubuk ve yüzde | Claude çalışmasında tur oranı yerine aşama ve süre (ortanca süre) |
| Talimat düzenleme (TASARIM 10.4) | Program içinden düzenleme, sürümler | Tek kaynak depodaki dosya (yönetici de dışarıdan düzenliyor); diskteki değişiklikte kayıt yapılmıyor; geçmiş veri klasöründe |

## Eklentinin izinleri ve güvenlik önlemleri

| İzin ya da önlem | Ne için / nasıl |
|---|---|
| `tabs` | Eklentinin kendi penceresini ve sekmesini açmak, adresini değiştirmek, yüklenmesini beklemek, kapatmak |
| `scripting` | Yalnız kendi açtığı sekmede sayfanın içeriğini okumak, bir öğeyi beklemek, sayfa içi istek |
| `storage` | Eşleşme kodu, bulunan port, son durum |
| `alarms` | 30 sn'de bir uyanıp iş sormak |
| `notifications` | "30A Studio: doğrulama bekleniyor" bildirimi |
| `http://127.0.0.1/*` | Yalnız yerel program |
| Site izinleri (isteğe bağlı) | Her site için kullanıcı eklenti penceresinde "İzin ver" der; izinsiz siteye gidilmez |
| Olmayan izinler | Çerez, geçmiş, yer imi, indirme, `debugger` (CDP), `webRequest`, `<all_urls>` |
| Eşleşme | Kod programın veri klasöründe; kodu bilen ilk eklenti kökeni kaydedilir, başkası reddedilir; "Kodu yenile" eşleşmeyi düşürür |
| Eklenti API'si | Yalnız eşleşmiş eklentinin kökeni ve eşleşme kodu; CORS yalnız o köken için |
| Programın kendi API'si | Durum değiştiren istek başka bir siteden gelirse (`Origin` farklı ya da `Sec-Fetch-Site` başka site) reddedilir |
| Davranış sınırları | Tıklama, yazı yazma, form yok; giriş ve ödeme sayfaları okunmadan atlanır; kullanıcının sekmelerine dokunulmaz; aynı sitede iki sayfa arası en az 8 sn, bir anda tek sayfa |
| Doğrulama | Kullanıcı yapar; eklenti pencereyi öne getirir, bildirim gösterir, 15 dk bekler, geçilmezse sayfayı atlar ve kaydeder; çözme servisi, gizlenme, parmak izi sahteciliği, proxy, IP değiştirme yok |
| Kullanıcının verisi | Program da eklenti de kullanıcının Chrome profiline, çerezlerine, parolalarına ve geçmişine erişmez |

## Beklenmedik durumlar

- **Eski bir tarayıcı sekmesi programı açık tuttu.** Geçici denemede pencere kapatıldığı hâlde program kapanmadı. Sebep: kullanıcının kendi Chrome'unda 127.0.0.1:8830'a açık eski bir "30A Studio" sekmesi vardı; bu sekme programa canlılık sinyali gönderiyordu. Sekme kapanınca program 8 sn içinde kapandı. Bu tasarım gereğidir (programı gösteren her sayfa onu açık tutar). Kullanıcı programı artık masaüstü simgesiyle açacağı için tarayıcıdaki eski sekmeleri kapatması yeterli. Sekmeye dokunulmadı; deneme başka bir portta tamamlandı.
- **CI'da kararsız bir test** (yukarıda): düzeltildi.
- **Eklentinin uçtan uca denemesi bir kez** Chromium açılırken hata verdi; sonraki 3 çalıştırma geçti. Tekrar etmedi.
- **Gerçek çalışmada iş mesajı** "0 aday onay bekliyor" diyordu: düzeltildi.
- Talimat düzenleyici denemesinden sonra `baslik_degerlendirme.md` dosyasının içeriği bayt bayt aynı kaldı (SHA-256 `acdaade6…`); yalnız dosyanın değiştirilme zamanı denemenin saatine döndü.
- Gerçek çalışmanın ilerleme çubuğu varsayılan 5 dk'ya göre hesaplandı (önceki gerçek değerlendirme yoktu); çalışma 78 sn'de bittiği için çubuk %90'a varmadan doğrulamaya geçti. Bundan sonraki çalışmalar bu süreyi ortancaya katacak.

## Yöneticinin karar vermesi gereken konular

1. **Adaysız değerlendirme iş akışında "onay bekliyor" sayılıyor.** Gerçek çalışma aday üretmedi ama "Konu ve başlık" adımı "onay bekliyor" gösteriyor (kullanıcı "Reddet" ile kapatabilir). Adaysız değerlendirmenin bu sayımdan çıkarılması istenirse küçük bir değişiklik.
2. **Şemaya `doluluk.eksik_veri` eklendi.** Görev metnindeki şema listesinde `doluluk{dolar_mi, aciklama}` vardı; ama aynı metin "dolmuyorsa açıklama ve eksik veri doldurulmalı" diyor. Eksik verinin ayrı ve denetlenebilir olması için alan eklendi. Gerçek çalışmada 7 madde yazıldı.
3. **realjoy.com için okuyucu yok.** Eklenti sayfayı okuyabilir ama fiyat çıkaran bir kiralama okuyucusu (adaptör) yazılmadı.
4. **Günlük ihtiyaç zincir kontrolleri** (Publix, Winn-Dixie, The Fresh Market, CVS, HCA) canlı okunmuyor, gözden geçirilmiş dosyadan geliyor. Eklentiyle okunan sayfalardan bu dosyanın güncellenmesi ayrı bir iş.
5. **Köpekle tatil konusu** için Claude'un eksik veri listesi yeni bir veri işi önerisi gibi okunabilir (evcil hayvan kuralları, veteriner, köpek dostu yerler). Kanalın bu konuya girip girmeyeceği editoryal bir karar.
6. Eklentiyle ilk gerçek çekimi kullanıcı başlatacak ("Sorunlu sitelerden birer sayfa dene" düğmesi). Sonuçlar bir sonraki görevde değerlendirilebilir.

## Teslim edilenler (bu klasör)

- `GOREV.md` (görev metni), `RAPOR.md` (bu rapor)
- `gercek-degerlendirme/`: `baslik_degerlendirme.json`, `baslik_degerlendirme.md`, `gorev.md`, `calisma.json`
- `eklenti-kurulum/`: `KURULUM.md` ve resimleri
- `ekran/`:
  - `01-masaustu-penceresi.png` (gerçek veriyle, kısayoldan açılan pencere)
  - `02-is-akisi-video-yok.png`, `03-is-akisi-gecici-video.png`
  - `04-kullanim-paneli.png` (geçici), `04b-kullanim-paneli-gercek.png`
  - `05-kendi-basligini-yaz.png`, `06-degerlendirme-ekrani.png`, `07-baslik-duzenleme.png`
  - `08-isler-ilerleme.png` (geçici, yavaş sahte Claude), `08b-isler-ilerleme-gercek.png` (gerçek çalışma: %22, geçen 50 sn, tahmini kalan ~4 dk)
  - `09-video-paketi-basi.png`
  - `10-ayarlar-talimatlar.png`, `11-ayarlar-tarayici-eklentisi.png`, `12-ayarlar-baslik-eki-kullanim.png`
  - `13-eklenti-penceresi-yerel-deneme.png` (eklentinin penceresi, yerel deneme)
