# M21 — İş akışı katmanları: proje ve video; adımlar, durumlar, tek onay bileşeni

GÖREV-21 (16 Kasım 2026), uygulama 0.22.0, şema 21. Örnek alınan program Rota Stüdyo'dur (`rente-studyo`: `docs/TASARIM.md` Bölüm 6 ve 13,
`docs/IS_AKISI.md`, `rota/state.py`, `rota/web/js/claude-step.js`); o depoda hiçbir dosya değişmedi.

> Görev metni bu belgeye `M19-IS-AKISI-KATMANLAR.md` adını vermişti; M19 (yol mesafesi) ve M20 (uçak bileti) GÖREV-20'de kullanıldığı
> için belge M21 numarasını aldı.

## 1. Kural

- Program iki katmandır ve her işin yeri bellidir.
- **Proje katmanı** bir kez yapılan ve bütün videoların kullandığı işleri tutar: veri, konu bankası, kanalın içerik kuralları, videoların
  listesi. Proje bugün destinasyondur ("30A / South Walton").
- **Video katmanı** tek bir videoya ait işleri tutar: o videonun sekiz adımı.
- İki katman karışmaz. Video açık değilken ekranda yalnız proje ekranları ve Ayarlar görünür; video açılınca sol menüde yalnız o
  videonun adımları sırayla görünür.
- **Ayarlar yalnız program ayarıdır.** Kanalın içerik kuralları Kanal ekranında, veri işleri Veri ekranındadır.
- Kullanıcıya bir yer tarif edilirken ekranda yazan tam adlarla yol verilir: "Sol menü → Konu bankası → Bu başlıkla video aç".

## 2. Ekranlar

### Üst çubuk

Proje (tek proje varsa yalnız adı: "30A / South Walton"; birden çoksa seçici), bağlantı durumu, İşler paneli. Video seçici yoktur. Claude
kullanımı göstergesi sol menünün altında, Ayarlar'ın üstünde durur.

### Sol menü, video açık değilken — PROJE

| Ekran | Adres | İçerik |
|---|---|---|
| **Veri** | `#sources` | Sekmeler: **Kaynaklar** (`#sources`), **Toplama** (`#collect`, alt sekmeleriyle), **Kalite** (`#quality`), **Kanıt paketi** (`#evidence`), **Okuma denemeleri** (`#veri/okuma`) |
| **Konu bankası** | `#konu`, `#konu/calisma/<kimlik>` | "Öneri al", "Kendi başlığını değerlendir", öneri çalışmaları ve adayları, "Bu başlıkla video aç" |
| **Kanal** | `#kanal`, `#kanal/<bölüm>` | Talimatlar, Tonlar, Uyarı ifadeleri (işletme adlarıyla), Başlık eki |
| **Videolar** | `#videolar`, `#videolar/arsiv` | Projenin videoları, "Yeni video", "Arşive kaldır", "Arşivdekileri göster" |

En altta **Ayarlar** (`#settings`). Başka hiçbir şey görünmez.

### Sol menü, video açıkken

- En üstte videonun adı (başlığın Türkçesi, yoksa çalışma adı) ve **Videoyu kapat**. Kapatınca menü proje görünümüne döner; video silinmez.
- **← Proje**: daraltılmış tek satır. Basınca dört proje ekranı satırın altında açılır; bir proje ekranına gidilince video açık kalır.
- **ADIMLAR**: yalnız bu videonun sekiz adımı; numara, ad, durum. Adres: `#video/<video>/<adım>`.
- Açık video sunucuda saklanır (`project_state.open_video_id`); program bir dahaki açılışta o videoyla açılır.

### Veri → Okuma denemeleri

Ayarlar'dan taşınan veri işleri: eklentinin okuduğu siteler ve hızı, **Deneme** (eklentinin yerel deneme sayfası), **Sorunlu sitelerden
birer sayfa dene**, **Isınma listesi** (doğrulama gösteren alan adları ve korumalı kiralama siteleri; salt okunur, `GET /api/isinma-listesi`),
**Proxy'yi dene** ve bölge engelli alan adları listesi.

### Konu bankası

Başlık çalışmaları ve adayları projeye (destinasyona) bağlıdır, videoya bağlı değildir. Her öneri çalışması bir konu havuzudur. Aday
listesinde Türkçe başlık büyük, İngilizcesi küçük ve soluk yazar. **Bu başlıkla video aç** adayla yeni bir video açar: aday "kullanıldı"
işaretlenir ve hangi videoda kullanıldığı adayın yanında görünür; kullanılmayan adaylar havuzda kalır. Dörtten fazla çalışma varsa eskileri
"Önceki öneriler" altında durur. Bir çalışmanın bütünü için "Düzeltme iste" (notla yeni çalışma) ve "Reddet" çalışmanın kendi ekranındadır.

### Videolar

Her satırda seçilen başlığın Türkçesi büyük, İngilizcesi küçük; oluşturma tarihi; adım ilerlemesi ("3/8") ve sıradaki adımın durumu.
**Yeni video** isteğe bağlı çalışma adıyla boş bir video açar; başlığı 1. adımda bankadan seçilir ya da yazılır. Silme yoktur:
**Arşive kaldır** videoyu listeden alır, **Arşivdekileri göster** geri getirmeyi sağlar.

### Ayarlar

Yalnız program ayarları: **Kayıt klasörü**; **Claude** (bütün Claude adımlarının modeli, eforu ve çıktı varsayımı tek tabloda; her satırda
adımın ekrandaki adı ve ait olduğu yer; tek çağrı sınırı, iş başına sınır, oturum ve kullanım eşikleri); **Claude kullanımı**;
**Tarayıcı eklentisi** (yalnız eşleşme kodu ve bağlantı durumu, kurulum adımları kapalı bir kutuda); **ABD proxy'si** (yalnız bağlantı
bilgileri ve parolanın kasada olup olmadığı); **Hakkında**.

| Claude adımı (anahtar) | Ekrandaki adı | Ait olduğu yer |
|---|---|---|
| `baslik` | Öneri al (başlık önerisi) | Proje · Konu bankası |
| `baslik_degerlendirme` | Kendi başlığını değerlendirme | Proje · Konu bankası; 1 · Başlık ve vaat |
| `metin_plan` | Planlayıcı | 3 · Plan |
| `metin_plan_elestiri` | Plan eleştirmeni | 3 · Plan |
| `metin_bolum`, `metin_birlestirme`, `metin_giris_kapanis`, `metin_son_okuma`, `metin_ceviri` | Bölümler, Birleştirme, Giriş ve kapanış, Son okuma, Çeviri | 4 · Yazım |

### Eski adresler

| Eski | Yeni |
|---|---|
| `#settings/talimatlar`, `/tonlar`, `/uyari-ifadeleri`, `/baslik-eki` (ve `#ayarlar/…`) | `#kanal/<aynı bölüm>` |
| `#videos`, `#videos/run/<kimlik>` | `#konu`, `#konu/calisma/<kimlik>` |
| `#adim/veri` | `#sources` |
| `#adim/baslik` | `#konu` |
| `#adim/paket`, `#adim/metin`, `#adim/metin/karsilastirma/…`, `#adim/metin/surum/<kimlik>` | açık videonun `paket`, `plan`, `kontrol`, `yazim/surum/<kimlik>` adresi; video açık değilse `#videolar` |

Yönlendirme `studio/web/layers.js` → `redirectOf`; metinlerdeki "Ayarlar → Tonlar" gibi eski yollar `linkSettingsMentions` ile yeni yere bağlanır.

## 3. Videonun adımları

`studio/workflow.py` → `STEPS`:

| No | Adım (anahtar) | İçerik | Onay |
|---|---|---|---|
| 1 | Başlık ve vaat (`baslik`) | Seçilen başlık (bankadan ya da değerlendirilmiş kendi başlığı), Türkçesi, izleyicinin sorusu ve vaat (başlık analizinden) | Evet |
| 2 | Veri paketi (`paket`) | Kanıt paketi ve yazar özeti; Claude yok | Hayır (bitince tamamlandı) |
| 3 | Plan (`plan`) | `metin_plan` ve `metin_plan_elestiri` | Evet |
| 4 | Yazım (`yazim`) | `metin_bolum` … `metin_ceviri`; tonlar bu adımın ekranında seçilir | Hayır |
| 5 | Kontrol ve ton seçimi (`kontrol`) | Programın denetimi, işletme adı denetimi, tonların karşılaştırması; onayla birlikte ton seçilir | Evet |
| 6 | Yayın paketi (`yayin`) | Henüz yok: "Sonraki görevde gelecek" | — |
| 7 | Seslendirme (`ses`) | Henüz yok | — |
| 8 | Kurgu paketi (`kurgu`) | Kuruldu (HEDEF-04 A-8): Kurgu Motoru'na gidecek paket, "Kurguya gönder" | — |

Eski "Veri" ve "Konu ve başlık" adımları proje katmanına taşındı; "Kontrol" 5. adımın içine girdi; "Görsel plan" ve "Video üretimi"
kalktı (stok görüntü, animasyon ve kurgu ayrı bir proje olan Kurgu Motoru'nda yapılır).

**Yazım zinciri plan onaylanmadan başlamaz.** "Plandan sonra dur" ayarı kalktı: zincir planı yazınca her zaman durur (`plan_hazir`),
3. adım "onay bekliyor" olur; "Yazımı başlat" yalnız plan onaylıyken çalışır (`POST /api/videos/<video>/yazim` aksi hâlde 409). Zincirin
sürdürme, kullanım sınırında bekleme ve kaldığı yerden devam özellikleri aynen durur. Planın metin çalışması yazıma aynı çalışmayla devam
eder; yeniden yazımda (ya da düzeltme notuyla yazımda) onaylı planı taşıyan yeni bir çalışma açılır, eski metinler kalır.

## 4. Durumlar

Bütün adımlar şu durumları kullanır (`video_steps.status`): `waiting` bekliyor, `ready` hazır, `running` çalışıyor, `awaiting_approval`
onay bekliyor, `approved` onaylandı, `done` tamamlandı, `error` hata, `stale` eskidi. Durumlar saklanır (GÖREV-14'te kayıtlardan
hesaplanıyordu); her değişiklik ve her karar `video_step_log` tablosuna tarihli bir Türkçe cümleyle yazılır.

- İlk adım hazır başlar, öbürleri bekler. Konu bankasından açılan videoda 1. adım "onay bekliyor" başlar.
- Bir adım onaylanınca (onaysız adım bitince) sonraki adım hazır olur; adım bu durumdan çıkınca (yeniden çalışınca, reddedilince) hazır
  bekleyen sonraki adım yeniden bekler.
- Bir adımın onaylanan çıktısı değişince sonraki adımlardan çıktısı olanlar (onay bekliyor, onaylandı, tamamlandı) "eskidi" olur ve sebebi
  Türkçe yazılır: "Başlık onayı değişti.", "Veri paketi değişti.", "Plan onayı değişti.", "Yazım değişti."; veri paketten sonra yeniden
  çekilince yalnız 2. adım "Veri paketten sonra yeniden çekildi." sebebiyle eskir. Çıktılar silinmez. Kullanıcı adımı yeniden çalıştırır
  ya da **Bu değişiklik etkilemiyor** der: adım önceki durumuna döner, not durum günlüğüne yazılır.
- Program yarıda kapanırsa "çalışıyor" görünen ama çalışan işi olmayan adım "hata" olur (`workflow.recover`; açılışta ve adımlar
  okunurken); 3 ve 4. adımda **Kaldığı yerden sürdür** biten halkaları yeniden çalıştırmadan devam eder.
- 4. adım bitince 5. adım kendiliğinden "onay bekliyor" olur (denetim yazım zincirinin içinde yapılmıştır); 5. adım onaylıyken yazım
  yeniden yapılırsa "Yazım değişti." sebebiyle eskir.
- 6–8. adımlar kurulana kadar "bekliyor" kalır; menüde "sonraki görevde gelecek" yazar.

## 5. Tek onay bileşeni

1, 3 ve 5. adımlarda aynı bileşen (`studio/web/claude-step.js` → `decisionCard`; sunucuda `studio/video_flow.py`): çıktının okunur
Türkçe hâli, not alanı ve üç düğme.

| Adım | Onayla | Düzeltme iste (not zorunlu) | Reddet |
|---|---|---|---|
| 1 · Başlık ve vaat | Adım onaylanır; 2. adım hazır | Adayın çalışması notla yeniden çalışır (Claude; tahmin önce gösterilir); video adayı bırakır, yeni adaylar bu ekranda görünür | Başlık seçimi kalkar, aday havuza döner, adım hazır |
| 3 · Plan | Plan onaylanır; 4. adım hazır | Plan, not ve önceki plan malzeme olarak verilerek yeniden yazılır (2 çağrı; tahmin önce gösterilir) | Adım hazır; plan onaysız |
| 5 · Kontrol ve ton seçimi | Onayla'nın yanında seçilen ton videonun metni olur | Not 4. adımı "hazır" yapar ve yeniden yazımda Claude'a verilir; 5. adım bekler | Adım hazır ("Kontrolü yeniden aç" karşılaştırmayı geri getirir) |

**Düzeltme notu Claude'a malzeme olarak verilir; talimat dosyası değişmez.** Başlıkta görev metninin sonundaki "Düzeltme: kullanıcının
düzeltme notu aşağıda." bloğunda; planda ve yazımda `kullanicinin_duzeltme_notu.md` dosyasında (planda ayrıca `onceki_plan.json`). Yazımda
notu bölüm yazarı, birleştirme, giriş ve kapanış ve son okuma alır; çevirmen almaz. Eski "Bu başlığı seç", "Devam" ve "Bu tonla devam et"
düğmeleri bu bileşene dönüştü.

**Sürümler.** Her adımın çıktısı dosyaya yazılır, eski sürüm silinmez; adım ekranının altındaki **Sürümler** bölümünde görülür: 1 ve 5.
adımda kararların kayıtları (`videolar/<video>/1_baslik/surum-NNN.json`, `…/5_kontrol/…`), 2. adımda paketler, 3. adımda planlar (metin
çalışmaları), 4. adımda metin sürümleri. Yanında **Durum günlüğü** son satırları gösterir.

## 6. Claude adımlarında maliyet

GÖREV-18'in getirdikleri (başlamadan tahmin ve "Başlat", gerçek ile tahmin yan yana, 1,5 katını geçince kırmızı uyarı) her Claude adımında
aynı yerde ve aynı biçimdedir: konu bankasındaki "Öneri al" ve "Kendi başlığını değerlendir", 1. adımdaki "Claude değerlendirsin", 3, 4 ve
5. adımlar.

1. **Düğmenin üstünde tahmin** (`costLine`): kaç çağrı, okunacak ve yazılacak token, model ve efor. 3 ve 4. adımda ekran açılınca
   kendiliğinden hesaplanır; girdi gerektiren yerlerde düğmeye basınca. Claude "Başlat" denmeden çalışmaz (`estimateBox`).
2. **İş sürerken** (`runningPanel`): o ana kadarki harcama (çağrı ve token; token çağrı bitince sayılır) ve **İptal**. İptal edilen iş
   kayda "iptal edildi" diye düşer, harcaması sayılır, biten parçalar saklanır.
3. **Halka tablosu** (3 ve 4. adım; `chainTable`, sunucuda `TextViews.chain`): her halkanın durumu (Tamamlandı, Çalışıyor, Yarıda kaldı,
   Bekliyor), çağrı sayısı (yapılan / tahmin), gerçek ve tahmini tokeni; altında toplam ve tahmin. Program denetimi satırında "Claude
   çağrısı yok" yazar.

## 7. Veri modeli (şema 21)

- `videos` yeniden kuruldu (kimlikler ve bütün sütunlar korunarak): başlık, bölge, aile ve aday bağı (`run_id`, `candidate`) boş olabilir;
  yeni sütunlar `name` (çalışma adı) ve `archived_at`. `UNIQUE(run_id, candidate)` durur: bir aday tek videoda kullanılır.
- `video_steps` (video başına sekiz satır): `status`, `status_before_stale`, `stale_reason`, `note` (ret notu ya da bekleyen düzeltme
  notu), `error`, `ref` (adımın çıktısı olan kayıt: paket, metin çalışması), `inputs`, `updated_at`.
- `video_step_log`: durum günlüğü. `project_state`: projede açık olan video.
- Başlık çalışmaları ve adayları `claude_runs`'ta destinasyona bağlıdır (değişmedi); video yalnız kullandığı adayı gösterir.
- Taşıma (`studio/migration_v21.py`): var olan videoların adımları kayıtlarından çıkarılır (`workflow.seed`): başlığı olan videoda 1. adım
  onaylı; paketi varsa 2. adım tamam; planı olan metin çalışması varsa plan onaylı sayılır (eski zincir onaysız yazıyordu); sürümler varsa
  yazım tamam; seçilmiş metin varsa kontrol onaylı.

## 8. Kod

| Dosya | İş |
|---|---|
| `studio/workflow.py` | Adımlar, durumlar ve kuralları (Rota Stüdyo `rota/state.py`'den uyarlandı; dosya yerine SQLite) |
| `studio/video_flow.py` | Videolar, adım ekranının verisi, onay bileşeninin kararları, sürümler |
| `studio/migration_v21.py` | Şema 21 |
| `studio/ai/service.py` | Konu bankası (`bank`), adayla video açma (`select`), adayı bırakma (`release`), videodan başlatılan başlık çalışması |
| `studio/text/engine.py`, `views.py` | `start_plan`, `start_writing`, plan onayı kapısı, düzeltme notu, halka tablosu |
| `studio/web/layers.js` | Katmanlar, adresler, yönlendirme, sol menü, sekmeler |
| `studio/web/claude-step.js` | Claude adımlarının ortak parçaları (Rota Stüdyo `claude-step.js`'ten uyarlandı) |
| `studio/web/steps.js` | Sekiz adımın ekranları |
| `studio/web/videos.js`, `videolist.js` | Konu bankası; Videolar |

## 9. API (yeni ve değişen)

| Yol | İş |
|---|---|
| `GET /api/workflow?video_id=` | Açık videonun sekiz adımı; video yoksa adım yok |
| `GET /api/konu-bankasi` | Çalışmalar, adayları ve kullanan videolar |
| `POST /api/claude/runs/<çalışma>/select` | "Bu başlıkla video aç" (`video_id` verilirse o video adayı kullanır) |
| `GET/POST /api/videolar`, `POST /api/videolar/kapat` | Liste (`?arsiv=true`), "Yeni video", "Videoyu kapat" |
| `POST /api/videos/<video>/ac`, `/arsivle`, `/arsivden-cikar` | Aç, arşive kaldır, arşivden çıkar |
| `GET /api/videos/<video>/adimlar/<adım>` | Adım ekranının verisi (durum, eylemler, çalışan iş, sürümler, günlük) |
| `POST …/adimlar/<adım>/onayla` · `/duzeltme` (+`/tahmin`) · `/reddet` · `/etkilemiyor` · `/surdur` | Onay bileşeni, eskimeyi kaldırma, kaldığı yerden sürdürme |
| `POST /api/videos/<video>/baslik/aday` · `/baslik/degerlendir` (+`/tahmin`) | 1. adım: bankadan aday, kendi başlığın değerlendirmesi |
| `POST /api/videos/<video>/evidence-pack` | 2. adım (başlık onaylı değilse 409) |
| `POST /api/videos/<video>/plan` (+`/tahmin`) · `/yazim` (+`/tahmin`) · `/kontrol/ac` | 3, 4 ve 5. adım |
| `GET /api/isinma-listesi` | Veri → Okuma denemeleri: ısınma listesi |

Kalkanlar: `POST /api/videos/<video>/metin` (+`/tahmin`), `POST /api/metin/calismalar/<çalışma>/yeniden-planla` (+`/tahmin`). Duranlar:
`GET /api/videos/<video>/metin`, `…/metin/karsilastirma`, `/api/metin/calismalar/<çalışma>` (+`/devam`, `/durdur`, `/ton`),
`/api/metin/surumler/<sürüm>` (+`/dosya/<tür>`, `/sec`).

## 10. Testler

`tests/test_workflow.py` (durum kuralları), `tests/test_gorev21.py` (sahte claude ile akışlar: menünün sunucu tarafı, video açma, üç
düğme, düzeltme notunun Claude'a giden malzemede bulunması, plan onaylanmadan yazımın başlamaması, eskime, maliyet, iptal, Ayarlar,
taşıma) ve `tests/frontend.test.mjs` içindeki "GÖREV-21" testleri (menü, adresler, yönlendirme, ortak parçalar, adım ekranları, konu
bankası, Videolar).

## HEDEF-04 A-6: 6 · Yayın paketi (27.11.2026)

Adım kuruldu (`studio/ai/publish.py`, kimlik `yayin`); "sonraki görevde gelecek" listesinde yalnız 7 · Seslendirme ve 8 · Kurgu paketi kaldı.

- 5 · Kontrol ve ton seçimi onaylanınca 6 hazır olur (bu sürümden önce onaylanmış videolarda da: adım satırları okunurken).
- Claude tek çağrıda JSON döndürür: bölüm başlıkları, açıklamanın ilk iki satırı, hedeflenen üç arama sorgusu, etiketler, kapak yazısı ve kapak fikri. Malzeme istemdedir: `yayin_secim.md` (başlık, vaat, kapak fikri, metnin bilgisi) ve `seslendirme_zamanli.md` (onaylı İngilizce metin, her paragrafın başında tahmini zamanı).
- Zamanlar kelime sayısından tahminidir (dakikada 150 kelime); ekranda ve dosyada "tahmini" yazar, ses gelince kesinleşecek.
- Program bölümleri denetler: ilki 00:00, en az 3, her biri en az 10 sn, artan sıra, son bölüm tahmini sürenin en az 10 sn öncesinde. Hata varsa paket onaylanamaz; "Düzeltme iste" ile yeniden yazdırılır.
- Çıktı çalışma klasöründe `yayin.json` ve `yayin.md`; onay `videolar/<video>/6_yayin/surum-NNN.json`'a paketin kopyasını yazar. Ton seçimi değişirse onaylı paket eskir ("Ton seçimi değişti.").
- Onay tek bileşen: Onayla / Düzeltme iste (not ve önceki paket Claude'a malzeme; 1 çağrı, tahmin önce) / Reddet. 6 onaylanınca 7 · Seslendirme kurulmadığı için bekler.
- Modeli ve eforu Ayarlar → Claude'da öbür Claude adımlarıyla birlikte ("Yayın paketi", yer "6 · Yayın paketi"; varsayılan Opus · Orta). Uçlar: `POST /api/videos/{id}/yayin/tahmin`, `POST /api/videos/{id}/yayin`. Bu adımın çalışmaları konu bankasında görünmez.
## HEDEF-04 A-7: 7 · Seslendirme (28.11.2026)

Adım kuruldu (`studio/voice.py`); "sonraki görevde gelecek" listesinde yalnız 8 · Kurgu paketi kaldı. Claude çağrısı yok.

- 6 · Yayın paketi onaylanınca 7 metni yazar ve "ses bekliyor"da durur (önceden onaylanmış videolarda adım ekranı açılınca).
  Durumlar: hazır → ses bekliyor (`awaiting_audio`) → ses yüklendi (`audio_ready`) → tamamlandı (eşleşti). Ton seçimi değişirse eskir.
- Metin: onaylı metnin İngilizcesi, işaretsiz ve cümle numarasız, paragraflar boş satırla; parça başına en çok 4.500 karakter, cümle
  ortasında bölünmez: `videolar/<video>/7_ses/metin/seslendirme_01.txt`, `_02`… ve `cumle_parca.json` (cümle no → parça). "Metni yeniden
  hazırla" eski dosyaları `metin-eski/NNN/`'ye taşır.
- "Sesi yükle": mp3/wav, tek dosya ya da `_01`, `_02`… (metin parçalarıyla aynı sayı ve sıra); dosyalar olduğu gibi `7_ses/ses/NNN/`'de;
  süre ffprobe ile (PATH, yoksa `E:\KurguMotoru\tools\ffmpeg\bin\ffprobe.exe`; 7 · Seslendirme → Ses ayarları).
- "Sesi cümlelerle eşleştir": Kurgu Motoru kopyasının `workers/hizala.py` işçisine (`transcribe`, stdin/stdout JSON) 16 kHz wav verilir;
  kelimeler programda cümlelere eşlenir (yarısından azı bulunan cümle eşleşmemiş sayılır). Sonuç `7_ses/eslesme/eslesme.json`: cümle no →
  başlangıç/bitiş (parçalar arka arkaya), eşleşmeyen cümle sayısı. Motor ya da Python'u yoksa açık hata (409).
- Uçlar: `POST /api/videos/{id}/ses/metin`, `/ses/yukle?ad=&yeni=` (ham gövde), `/ses/eslestir`, `/ses/klasor`; `GET/PUT /api/settings/seslendirme`.
  Testler: `tests/test_ses.py` (sahte ffprobe ve hizalama), `tests/frontend.test.mjs` "HEDEF-04 A-7".
## HEDEF-04 A-8: 8 · Kurgu paketi (28.11.2026)

Adım kuruldu (`studio/kurgu.py`); "sonraki görevde gelecek" listesi boşaldı (`workflow.PLANNED == {}`). Claude çağrısı yok.

- 6 · Yayın paketi onaylanınca hazır (7'nin aşamasından bağımsız); ekran açılınca paket kurulur. Durumlar: hazır → (Kurguya gönder)
  tamamlandı; gönderim hata verirse hata. Ton seçimi değişirse eskir.
- Paket `videolar/<video>/8_kurgu/paket/NNN/`: `package.json`, `script.json`, `data.json`, `scenes.json`, sesle `audio/anlatim.*` ve
  (bütün cümleler eşleştiyse) `audio/zamanlar.json`. "Paketi yeniden kur" yeni bir NNN açar, eskiler kalır. Ses paketten sonra değişirse
  ekran söyler.
- "Kurguya gönder": motorun kopyasına kopyalar, `paket dogrula` + `paket ice-al`; komutların çıkış kodu ve çıktısı ekranda.
- Uçlar: `POST /api/videos/{id}/kurgu/kur`, `/kurgu/gonder`, `/kurgu/klasor`; `GET/PUT /api/settings/kurgu` (Ayarlar → Kurgu Motoru).
  Testler: `tests/test_hedef04_kurgu.py` (sahte motor), `tests/frontend.test.mjs` "HEDEF-04 A-8".
