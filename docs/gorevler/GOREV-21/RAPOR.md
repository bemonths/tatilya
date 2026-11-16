# GÖREV-21 raporu — İş akışı katmanları: proje ve video; tek adım düzeni ve tek onay bileşeni

Tarih: 16 Kasım 2026 · Dal: `gorev-21-katmanlar` · Uygulama 0.22.0 · Şema 21 · main'e alınmadı, etiket konmadı (karar yöneticide).

## Kısaca

- Program iki katmana ayrıldı. Video açık değilken sol menüde yalnız dört proje ekranı (Veri, Konu bankası, Kanal, Videolar) ve en altta
  Ayarlar var. Video açılınca menüde yalnız o videonun sekiz adımı, videonun adı, "Videoyu kapat" ve daraltılmış "← Proje" satırı var.
- Adımların durumları artık saklanıyor ve Rota Stüdyo'daki kurallarla değişiyor (bekliyor, hazır, çalışıyor, onay bekliyor, onaylandı,
  tamamlandı, hata, eskidi).
- 1, 3 ve 5. adımlarda aynı onay bileşeni var: Onayla, Düzeltme iste, Reddet.
- Plan onaylanmadan yazım başlamıyor; "Plandan sonra dur" ayarı kalktı.
- Ayarlar'da yalnız program ayarları kaldı.
- Gerçek veri yeni şemaya geçti; hiçbir satır kaybolmadı, dört başlık çalışması Konu bankasında görünüyor.
- Bu görevde programın Claude adımları gerçek Claude ile çalıştırılmadı; alt ajan kullanılmadı; Rota Stüdyo deposunda hiçbir dosya değişmedi.

## Adım 1 — Dal

- Kullanıcının izniyle `gorev-20-eksik-veri` main'e fast-forward ile alındı (`7af4f1f..57088be`), açıklamalı `v0.21.0` etiketi konuldu,
  main ve etiket push edildi.
- `gorev-21-katmanlar` güncel main'den açıldı.
- `studio/destinations/thirty_a_claude/` altında kullanıcının yaptığı bir talimat değişikliği yoktu (çalışma ağacı temizdi); talimat
  commit'i gerekmedi.

## Yeni menü düzeni

**Üst çubuk:** proje adı ("30A / South Walton"; birden çok proje olursa seçici), bağlantı durumu, İşler paneli. Video seçici kalktı.
Claude kullanımı göstergesi sol menünün altında yerinde duruyor.

**Sol menü, video açık değilken (PROJE):**

| Ekran | İçinde ne var |
|---|---|
| Veri | Sekmeler: Kaynaklar · Toplama · Kalite · Kanıt paketi · Okuma denemeleri |
| Konu bankası | Öneri al · Kendi başlığını değerlendir · Öneri çalışmaları ve adayları · Bu başlıkla video aç |
| Kanal | Talimatlar · Tonlar · Uyarı ifadeleri · Başlık eki |
| Videolar | Projenin videoları · Yeni video · Arşive kaldır · Arşivdekileri göster |
| Ayarlar (en altta) | Kayıt klasörü · Claude · Claude kullanımı · Tarayıcı eklentisi · ABD proxy'si · Hakkında |

**Sol menü, video açıkken:** videonun adı ve "Videoyu kapat" · "← Proje" (daraltılmış tek satır) · ADIMLAR:
1 Başlık ve vaat · 2 Veri paketi · 3 Plan · 4 Yazım · 5 Kontrol ve ton seçimi · 6 Yayın paketi · 7 Seslendirme · 8 Kurgu paketi.
6, 7 ve 8. adımlar "sonraki görevde gelecek" notuyla duruyor. Açık video bir dahaki açılışta hatırlanıyor.

Ekran görüntüleri (geçici veri kopyasıyla; gerçek verinin göç ettirilmiş kopyası):

| Dosya | Ne gösteriyor |
|---|---|
| `01-menu-video-kapali.png` | Video açık değilken menü (Videolar ekranı) |
| `02-menu-video-acik.png` | Video açıkken menü (1 · Başlık ve vaat) |
| `03-adim-plan-tahmin.png` | 3 · Plan: düğmenin üstünde tahmin |
| `04-video-acikken-proje.png` | Video açıkken bir proje ekranı ("← Proje" açık) |
| `05-konu-bankasi.png` | Konu bankası: dört çalışma ve adayları |
| `06-kanal.png` | Kanal |
| `07-veri-sekmeler.png` | Veri ve sekmeleri |
| `08-veri-okuma-denemeleri.png` | Veri → Okuma denemeleri |
| `09-ayarlar.png` | Ayarlar |
| `10-plan-onay-bekliyor.png` | 3 · Plan: halka tablosu, plan ve onay bileşeni (sahte Claude ile) |
| `11-yazim-tahmin.png` | 4 · Yazım: ton seçimi ve tahmin |
| `13-yazim-bitti.png` | 4 · Yazım: halka tablosu, yazılan metinler (sahte Claude ile) |
| `14-kontrol-ve-ton-secimi.png` | 5 · Kontrol ve ton seçimi (sahte Claude ile) |

10, 13 ve 14 numaralı görüntüler testlerin sahte Claude'uyla, ikinci bir geçici kopyada alındı; içlerindeki plan ve metin sahtedir.

## Ne nereye taşındı (eski yer → yeni yer)

| Eski yer | Yeni yer |
|---|---|
| Sol menü → ADIMLAR → 1 Veri | Sol menü → Veri |
| Sol menü → VERİ grubu: Veri kaynakları, Veri toplama, Veri kontrolü, Kanıt paketi | Veri → sekmeler: Kaynaklar, Toplama, Kalite, Kanıt paketi |
| "Zamanı gelenleri başlat", "Kayıtları kontrol et", "Kaynak ekle" | Veri → Kaynaklar (yerleri aynı) |
| Sol menü → ADIMLAR → 2 Konu ve başlık (Videolar ekranı) | Sol menü → Konu bankası |
| "Konu ve başlık önerisi al" düğmesi | Konu bankası → **Öneri al** |
| "Kendi başlığını yaz" | Konu bankası → **Kendi başlığını değerlendir**; ayrıca video içinde 1 · Başlık ve vaat → Kendi başlığını yaz |
| "Bu başlığı seç" | Konu bankası → adayın **Bu başlıkla video aç** düğmesi; onay: 1 · Başlık ve vaat → **Onayla** |
| "Düzenlenmiş başlığı seç" | Konu bankası → çalışma → aday → Başlığı düzenle → **Düzenlenmiş başlıkla video aç** |
| Videolar ekranındaki "Video kayıtları" listesi ve "Kanıt paketi üret" | Sol menü → Videolar; paket: 2 · Veri paketi → **Veri paketini üret** |
| Üst çubuktaki video seçici ve "●●○○ 2/8 adım" | Kalktı. Video: Sol menü → Videolar'dan tıklanır; ilerleme listede ve menüde ("2/8") |
| 3 Veri paketi | 2 · Veri paketi |
| 4 Video metni → "Metni yaz" (plan ve yazım birlikte) | 3 · Plan → **Planı çıkar**; 4 · Yazım → **Yazımı başlat** |
| 4 Video metni → Planı göster | 3 · Plan (plan ekranın içinde) |
| 4 Video metni → "Planı yeniden yap" | 3 · Plan → **Planı yeniden çıkar** |
| 4 Video metni → "Devam", "Durdur" | Adım ekranında **Kaldığı yerden sürdür** ve **İptal** |
| 4 Video metni → Karşılaştır → "Bu tonla devam et" | 5 · Kontrol ve ton seçimi → "Devam edilecek ton" + **Onayla ve bu tonla devam et** |
| 5 Kontrol (planlanan) | 5 · Kontrol ve ton seçimi'nin içinde |
| 6 Görsel plan, 7 Video üretimi | Kalktı (Kurgu Motoru'nda yapılıyor); yerine 7 · Seslendirme ve 8 · Kurgu paketi (henüz yok) |
| 8 Yayın hazırlığı | 6 · Yayın paketi (henüz yok) |
| Ayarlar → Talimatlar | Kanal → Talimatlar |
| Ayarlar → Tonlar | Kanal → Tonlar |
| Ayarlar → Uyarı ifadeleri (işletme adları kutusuyla) | Kanal → Uyarı ifadeleri |
| Ayarlar → Başlık eki | Kanal → Başlık eki |
| Ayarlar → Tarayıcı eklentisi → izinli siteler, hız, "Deneme", "Sorunlu sitelerden birer sayfa dene" | Veri → Okuma denemeleri → Eklentinin deneme okuması |
| Isınma listesi (yalnız komut satırındaydı) | Veri → Okuma denemeleri → Isınma listesi (salt okunur) |
| Ayarlar → ABD proxy'si → "Proxy'yi dene", bölge engelli alan adları | Veri → Okuma denemeleri → Proxy'nin deneme okuması ve bölge engelli alan adları |
| Ayarlar → Claude → "Plandan sonra dur" | Kalktı (plan her zaman onay bekler) |

Ayarlar'da kalanlar: Kayıt klasörü; Claude (tablo: adımın ekrandaki adı, ait olduğu yer, model, efor, son çalışmaların ortancası, çıktı
varsayımı; tek çağrı ve iş başına sınır; oturum sayısı ve kullanım eşikleri); Claude kullanımı; Tarayıcı eklentisi (eşleşme kodu, bağlantı
durumu; kurulum adımları kapalı kutuda); ABD proxy'si (adres, kullanıcı adı, parola alanı, "kasada kayıtlı / kasada yok"); Hakkında.

Eski adresler yeni yerlerine yönleniyor: `#settings/talimatlar`, `/tonlar`, `/uyari-ifadeleri`, `/baslik-eki` → `#kanal/…`; `#videos` →
`#konu`; `#videos/run/<kimlik>` → `#konu/calisma/<kimlik>`; `#adim/…` → açık videonun ilgili adımı (video açık değilse `#videolar`).

## Durum geçişleri

Durumlar `video_steps` tablosunda saklanır; her değişiklik ve karar `video_step_log` tablosuna Türkçe bir cümleyle yazılır
(`studio/workflow.py`).

| Olay | Sonuç |
|---|---|
| Video açılır ("Yeni video") | 1. adım hazır, öbürleri bekliyor |
| Video konu bankasından açılır | 1. adım onay bekliyor |
| Onaylı adım onaylanır / onaysız adım biter | Sonraki adım bekliyorsa hazır olur |
| Adım yeniden çalışır ya da reddedilir | Hazır bekleyen sonraki adım yeniden bekler |
| Plan çalışması planı yazar | 3. adım onay bekliyor; zincir durur |
| Yazım biter | 4. adım tamamlandı; 5. adım onay bekliyor (5. adım onaylıysa "Yazım değişti." sebebiyle eskir) |
| Başlık onayı değişir / veri paketi yeniden üretilir / plan onayı değişir | Sonraki adımlardan çıktısı olanlar eskir: "Başlık onayı değişti.", "Veri paketi değişti.", "Plan onayı değişti." |
| Veri, paketten sonra yeniden çekilir | Yalnız 2. adım eskir: "Veri paketten sonra yeniden çekildi." |
| "Bu değişiklik etkilemiyor" | Adım önceki durumuna döner; not durum günlüğüne yazılır |
| Program yarıda kapanır | "Çalışıyor" görünen ama işi olmayan adım "hata" olur; "Kaldığı yerden sürdür" biten halkaları yeniden çalıştırmaz |
| İş iptal edilir | 3 ve 4. adım "hata" (sürdürülebilir); 1. adım yeniden hazır |

## Onay bileşeni

1 · Başlık ve vaat, 3 · Plan ve 5 · Kontrol ve ton seçimi adımlarında aynı bileşen: üstünde çıktının okunur Türkçe hâli, "Karar" kartında
not alanı ve üç düğme.

| | Onayla | Düzeltme iste (not zorunlu) | Reddet |
|---|---|---|---|
| 1 · Başlık ve vaat | Adım onaylanır | Adayın çalışması notla yeniden çalışır (tahmin önce gösterilir); yeni adaylar bu ekranda görünür | Başlık seçimi kalkar, aday havuza döner, adım hazır |
| 3 · Plan | Plan onaylanır; yazım başlayabilir | Plan, not ve önceki plan malzeme verilerek yeniden yazılır (tahmin önce gösterilir) | Adım hazır |
| 5 · Kontrol ve ton seçimi | Seçilen ton videonun metni olur | Not 4 · Yazım adımını hazır yapar ve yeniden yazımda Claude'a verilir | Adım hazır ("Kontrolü yeniden aç" karşılaştırmayı geri getirir) |

Düzeltme notu Claude'a malzeme olarak gidiyor ("kullanıcının düzeltme notu"); talimat dosyalarının içeriğine dokunulmadı. Testlerde
sahte Claude'a giden istemde notun bulunduğu ve talimat metninin değişmediği doğrulandı. "Bu başlığı seç", "Devam" ve "Bu tonla devam
et" düğmeleri kalktı. Her adımın çıktısı dosyada duruyor ve adım ekranının altındaki "Sürümler" bölümünde görülüyor; yanında "Durum
günlüğü" var.

## Veri modeli ve migration

- Başlık çalışmaları ve adayları projeye (destinasyona) bağlı; video yalnız kullandığı adayı gösteriyor. Aday bir videoda kullanılınca
  "kullanıldı" görünüyor; video adayı bırakınca (ret, düzeltme) aday havuza dönüyor.
- Şema 21: `videos` tablosu yeniden kuruldu (başlıksız video açılabiliyor; yeni sütunlar `name`, `archived_at`); yeni tablolar
  `video_steps`, `video_step_log`, `project_state`.
- **Kopyada deneme** (`work/gorev-21/gocdene.py`; gerçek veritabanı salt okunur açılıp `work/gorev-21/temp-data/` altına kopyalandı):
  şema 20 → 21; 78 tablo → 81 tablo; toplam satır 188.518 → 188.518; `foreign_key_check` önce ve sonra boş; değişen tablolar yalnız üç
  yeni boş tablo. `claude_runs` 4 → 4, `videos` 0 → 0, `jobs` 42 → 42, `evidence_packs` 8 → 8, `sources` 18 → 18, `source_runs` 32 → 32.
- **Gerçek veri** (16 Kasım 2026): uygulama kapalıyken `data/` klasörünün tamamı `work/yedek/20261116-2126/` altına kopyalandı
  (45.548 dosya, 1.702.332.642 bayt; kaynakla aynı boyut). Sonra program gerçek veri klasörüyle normal biçimde açıldı (0.22.0); migration
  açılışta çalıştı ve program kendi yedeğini de aldı (`data/backups/studio-v20-709da9d3….sqlite3`). Program kapatıldıktan sonra salt okunur
  sayım:

  | | Önce | Sonra |
  |---|---|---|
  | Şema | 20 | 21 |
  | Tablo | 78 | 81 (üç yeni boş tablo: `video_steps`, `video_step_log`, `project_state`) |
  | Toplam satır | 188.518 | 188.518 |
  | `foreign_key_check` | boş | boş |
  | Eksilen tablo, satırı değişen eski tablo | — | yok |

  Program açıkken Konu bankası dört çalışmayı gösterdi: 30A geneli önerisi (11 aday), Rosemary Beach önerisi (10 aday), Rosemary Beach
  önerisi (9 aday) ve bir değerlendirme ("veriyle dolmuyor", aday yok); toplam 30 aday, hepsi havuzda, hiçbiri kullanılmamış. Videolar
  listesi boş, açık video yok. Claude adımı çalıştırılmadı; hiçbir video açılmadı.

Görev metnindeki durum doğrulandı: gerçek veride seçilmiş başlık ve video kaydı yoktu; dört başlık çalışması vardı (30A geneli, Rosemary
Beach iki kez, bir değerlendirme).

## Maliyet görünürlüğü

**Zaten olanlar (GÖREV-18), korundu:** başlamadan tahmin kutusu ve "Başlat" onayı; tahmin bir sınırı aşarsa "Başlat" yok; iş kartında ve
çalışmada gerçek harcama ile tahmin yan yana; gerçek tahminin 1,5 katını geçince kırmızı "Beklenenden fazla" uyarısı; tek çağrı ve iş
başına sınır; İşler panelinde "İptal et".

**Eklenenler:**

1. **Düğmenin üstünde tahmin satırı**, her Claude adımında aynı yerde: "Tahmin 2 çağrı · okunacak ≈ 82 bin · yazılacak ≈ 26 bin token
   (toplam ≈ 108 bin) · model: …". 3 · Plan ve 4 · Yazım'da ekran açılınca kendiliğinden hesaplanıyor (yazımda ton seçimi değişince
   yeniden); bölge ya da başlık girilmesi gereken yerlerde (Konu bankası, 1. adımdaki kendi başlık) düğmeye basınca tahmin kutusu çıkıyor.
2. **Adım ekranında çalışma paneli:** iş sürerken o ana kadarki harcama (çağrı ve token; token çağrı bitince sayılıyor), tahmin ve
   **İptal** düğmesi. İptal edilen iş kayda "iptal edildi" diye düşüyor (iş "İptal edildi", metin çalışması ve başlık çalışması
   listelerde "iptal edildi"), harcaması sayılıyor, biten parçalar saklanıyor.
3. **Halka tablosu** (3 · Plan ve 4 · Yazım): her halkanın durumu (Tamamlandı, Çalışıyor, Yarıda kaldı, Bekliyor), çağrı sayısı
   (yapılan / tahmin), gerçek ve tahmini tokeni; altında toplam ve tahmin; 1,5 katı geçince uyarı. Yazımda halkalar ton başına:
   Bölümler, Birleştirme, Giriş ve kapanış, Son okuma, Program denetimi (Claude çağrısı yok), Çeviri.
4. Plan ve yazım ayrı işler olduğu için her birinin tahmini ve gerçek harcaması ayrı görünüyor.

Sınır: çalışma panelindeki "çalışırken" görüntüsü rapora konamadı, çünkü sahte Claude ekran görüntüsü alınana kadar işi bitiriyor; panel
ve iptal testlerle doğrulandı.

## Rota Stüdyo'dan kopyalanan ya da örnek alınan parçalar

| Rota Stüdyo | 30A Studio | Nasıl |
|---|---|---|
| `rota/state.py` | `studio/workflow.py` | Durumlar, "sonraki adım hazır / yeniden bekler" kuralı, eskime ve `status_before_stale`, "Bu değişiklik etkilemiyor", yarıda kalan adımın hata olması, durum günlüğü. Uyarlandı: `durum.json` yerine SQLite (`video_steps`, `video_step_log`); olay yayını yok; henüz kurulmayan adımlar bekler |
| `docs/TASARIM.md` 6.2, 6.3 | Durum kuralları ve onay bileşeni | Kurallar aynen; "Bu notu kalıcı ders yap" alınmadı (sadeleştirme) |
| `docs/TASARIM.md` 13 "Arayüz" | Sol menü, Videolar ekranı, Ayarlar | Ayrı video seçici yok; video Videolar'dan açılır; başlığın Türkçesi büyük, videonun dilindeki hâli küçük ve soluk; Ayarlar yalnız program ayarı ve her ayar ait olduğu adımın adıyla |
| `rota/web/js/claude-step.js` | `studio/web/claude-step.js` | Tahmin satırı, çalışma paneli (o ana kadarki harcama, İptal), gerçekleşen ile tahmin, eskime kutusu, karar kartı, sürümler kartı. Kod kopyalanmadı; bu programın metin şablonlarıyla yeniden yazıldı |
| "4 · Yazım" ekranının halka tablosu | `chainTable` ve `TextViews.chain` | Sütunlar ve durum adları örnek alındı |
| `docs/IS_AKISI.md` | Adım sırası | Plan onayının yazımdan önce gelmesi, Kurgu paketinin sonda olması |

Rota Stüdyo, Housing Atlas ve Kurgu Motoru depolarında hiçbir dosya değiştirilmedi.

## Testler

Tam takım (16 Kasım 2026, yerelde):

- `.venv\Scripts\python.exe -m pytest -q` → **1162 geçti, 2 atlandı** (8 dk 56 sn). GÖREV-20'de 1147 idi.
- `node --test tests/frontend.test.mjs` → **135 geçti** (GÖREV-20'de 124).

Yeni ve değişen testler:

| İstenen | Nerede |
|---|---|
| Video açık değilken yalnız proje ekranları ve Ayarlar | `frontend.test.mjs` "GÖREV-21 menü, video açık değilken"; `test_gorev21.py::test_no_video_no_steps…` |
| Video açıkken yalnız sekiz adım; "Videoyu kapat" | `frontend.test.mjs` "GÖREV-21 menü, video açıkken"; `test_gorev21.py::test_no_video_no_steps…` |
| "Bu başlıkla video aç" videoyu açar, adayı "kullanıldı" işaretler | `test_gorev21.py::test_bu_baslikla_video_ac…`; `frontend.test.mjs` "GÖREV-21 konu bankası" |
| Durum geçişleri, eskime, "Bu değişiklik etkilemiyor", yarıda kapanınca hata | `tests/test_workflow.py` (9 test); `test_gorev21.py::test_a_changed_approval…`; `test_text_chain.py` (uygulama kapanınca) |
| Onay bileşeni: üç düğme; düzeltme notunun Claude'a giden malzemede bulunması | `frontend.test.mjs` "GÖREV-21 onay bileşeni"; `test_gorev21.py::test_title_duzeltme_iste…`, `::test_plan_duzeltme_iste…`, `::test_check_approval…` |
| Plan onaylanmadan yazım başlamıyor | `test_gorev21.py::test_the_writing_does_not_start…`; `test_text_chain.py::test_the_chain_always_stops_after_the_plan…` |
| Taşınan bölümlerin eski adresleri; Ayarlar'da veri işi ve içerik kuralı yok | `frontend.test.mjs` "GÖREV-21 taşıma", "GÖREV-17 Ayarlar…", eklenti ve proxy testleri; `test_gorev21.py::test_settings_name_every_claude_step…` |
| Maliyet: tahmin, o ana kadarki harcama, iptal, halka tablosu | `frontend.test.mjs` üç "GÖREV-21 maliyet" testi; `test_gorev21.py::test_the_estimate_the_spending_and_the_link_table…`, `::test_canceling_the_writing…`, `::test_a_canceled_title_run…` |
| Migration: kopyada satır sayıları | `test_gorev21.py::test_v20_to_v21_keeps_every_row…`; eski göç testleri şema 21'e güncellendi |

Eski testlerden yeni düzene uyarlananlar: `test_text_chain.py` (zincir artık plan → onay → yazım), `test_gorev18.py` (plan ve yazımın
ayrı tahmini ve işi), `test_claude_steps.py` (paket başlık onayından sonra), şema sürümü bekleyen bütün göç testleri. Kaldırılanlar:
`tests/test_text_workflow.py` ve eski `tests/test_workflow.py` (kayıtlardan hesaplanan eski sekiz adımı sınıyorlardı; yerlerine yeni
`tests/test_workflow.py` ve `tests/test_gorev21.py` geldi).

## Belgeler

- Yeni: `docs/M21-IS-AKISI-KATMANLAR.md`. Görev metni bu belgeye M19 adını vermişti; M19 ve M20 GÖREV-20'de kullanıldığı için M21 oldu.
- Güncellenen: `CALISMA_MANTIGI.md` (§1, §9.13c notu, yeni §9.16, §14, belge indeksi), `docs/M15-CLAUDE-ADIMLARI.md` ve
  `docs/M17-VIDEO-METNI.md` (başlarına "GÖREV-21 ile değişenler"), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`
  ("Proje ve video katmanları · v0.22.0"), `CLAUDE.md` (yeni "Katmanlar" kuralı; "Ayarlar → Talimatlar/Tonlar" → "Kanal → …").

## Kullanıcı için kısa tarif: ilk videoyu açmaktan plan onayına kadar

1. Programı açın. Sol menüde dört ekran görürsünüz: Veri, Konu bankası, Kanal, Videolar.
2. **Sol menü → Konu bankası.** "Öneri çalışmaları ve adayları" bölümünde dört çalışma durur. Örneğin "Öneri · Rosemary Beach"
   çalışmasında beğendiğiniz adayın sağındaki **Bu başlıkla video aç** düğmesine basın. (Adayın ayrıntısını görmek için başlığına tıklayın.)
3. Video açılır; sol menüde artık yalnız bu videonun adımları vardır. **1 · Başlık ve vaat** ekranında başlığı, izleyicinin sorusunu ve
   vaadi okuyun. Uygunsa en alttaki "Karar" kartında **Onayla** düğmesine basın. Değişmesini istiyorsanız notunuzu yazıp
   **Düzeltme iste** deyin; vazgeçtiyseniz **Reddet**.
4. **Sol menü → 2 · Veri paketi → Veri paketini üret.** Claude çalışmaz; birkaç saniyede biter.
5. **Sol menü → 3 · Plan.** Düğmenin üstünde tahmini görürsünüz (kaç çağrı, kaç token, hangi model). **Planı çıkar** düğmesine basın;
   açılan tahmin kutusunda **Planı çıkar: başlat** deyin. Claude çalışırken harcama ve **İptal** aynı ekrandadır.
6. Plan gelince aynı ekranda Türkçe okunur. En alttaki "Karar" kartında **Onayla** deyin. Plan onaylanmadan yazım başlamaz.
7. Sonrası: **Sol menü → 4 · Yazım** → tonları seçin → **Yazımı başlat**; bitince **5 · Kontrol ve ton seçimi** → "Devam edilecek ton"u
   seçin → **Onayla ve bu tonla devam et**.

Başka bir işe bakmak için **Videoyu kapat**'a basın (video silinmez) ya da **← Proje** satırını açın. Videoya dönmek için
**Sol menü → Videolar** → videonun satırına tıklayın.

## Tamamlanamayanlar ve açık kalanlar

Tamamlanamayan adım yok. Bilinmesi gerekenler:

- Yeni düzen gerçek Claude ile hiç çalışmadı (görev gereği). Plan, yazım ve düzeltme notu yalnız testlerin sahte Claude'uyla denendi;
  ilk gerçek plan çalışmasında tahmin ile gerçek harcamaya bakılmalı.
- Düzeltme notu Claude'a ek bir malzeme dosyası olarak veriliyor; talimat dosyaları bu dosyadan söz etmiyor (talimatlara dokunulmadı).
  Görev metni dosyayı "kullanıcının düzeltme notu (… bu nota göre yaz)" diye tanıtıyor. Gerçek çalışmada Claude notu yeterince
  dikkate almazsa talimatlara bir cümle eklemek gerekebilir; bu yöneticinin kararıdır.
- 5 · Kontrol ve ton seçimi adımında programın ayrıca çalıştırdığı bir iş yok: denetim yazım zincirinin içinde yapılıyor, adım yazım
  bitince kendiliğinden "onay bekliyor" oluyor. "Reddet"ten sonra adım "hazır" olur ve "Kontrolü yeniden aç" düğmesiyle geri açılır.
- Veri ekranında sekmeler eski ekranların üstüne eklendi; "Toplama" sekmesinin kendi alt sekmeleri (Plajlar, Hava, Restoranlar …)
  aynen duruyor. Ekran kalabalığı azaltılmadı, yalnız yeri belli edildi.
- Çalışma panelinin "çalışırken" ekran görüntüsü alınamadı (yukarıda açıklandı).
- Belge adı M19 yerine M21 oldu (yukarıda açıklandı).
- 6 · Yayın paketi, 7 · Seslendirme ve 8 · Kurgu paketi adımları yalnız yer tutuyor ("Sonraki görevde gelecek").
- CI sonucu bu raporun sonuna eklenecek (dal push edildikten sonra).
