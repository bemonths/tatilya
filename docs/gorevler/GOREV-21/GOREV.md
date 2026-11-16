GÖREV-21 — İş akışını katmanlara ayır: proje katmanı ve video katmanı; tek adım düzeni ve tek onay bileşeni

BAĞLAM
30A Studio, Mucahit'in YouTube kanalı için veri toplayıp video metni yazdıran yerel programdır. Program klasörü: `C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`. Bu görev GÖREV-20'den (dal `gorev-20-eksik-veri`, uygulama 0.21.0) sonra gelir.

Kullanıcı bütün programlarının aynı mantıkla çalışmasını istiyor; hangisini açsa neyin nerede olduğunu bilmek istiyor. Örnek aldığı program Rota Stüdyo'dur: `C:\Users\1\source\Repos\rente-studyo`. Bu depoyu **yalnız oku, hiçbir dosyasını değiştirme**. Okunacak yerler:
- `docs/TASARIM.md`: Bölüm 6 "Video ve adımlar" (6.1 Adımlar, 6.2 Durumlar ve eskime, 6.3 Onay ekranı) ve Bölüm 13 "Arayüz",
- `docs/IS_AKISI.md`,
- `rota/state.py` (adım durumları),
- `rota/web/js/claude-step.js` (Claude adımı ekranlarının ortak parçaları).

Kod kopyalanabilir, ama 30A Studio'nun yapısına uydurulur ve sadeleştirilir.

Kullanıcının kuralı:
- Program katmanlara ayrılır ve her işin yeri bellidir.
- Bir kez yapılan ve bütün videoların kullandığı işler proje katmanında durur. Tek bir videoya ait işler video katmanında durur. İki katman birbirine karışmaz.
- Video açılmamışsa ekranda yalnız proje ekranları ve Ayarlar görünür. Video açılınca sol menüde yalnız o videonun adımları sırayla görünür.
- Ekran kalabalığı olmaz.

Kullanıcı aşağıdaki düzeni onayladı (16 Kasım 2026).

Bugünkü karışıklıklar:
1. Sol menüdeki "ADIMLAR" grubunda sekiz adım var (`studio/workflow.py` → `STEPS`: Veri, Konu ve başlık, Veri paketi, Video metni, Kontrol, Görsel plan, Video üretimi, Yayın hazırlığı). "Veri" ve "Konu ve başlık" tek bir videoya ait değil:
   - veri bütün videolar için toplanır;
   - her başlık önerisi çalışması 10–11 aday üretir ve bunlar bir konu havuzudur.
2. Video seçilmemişken de adımlar "video seçilmedi" notuyla görünüyor.
3. Video hem üst çubuktaki seçiciden hem Videolar ekranından seçiliyor; Videolar ekranı aynı zamanda başlık adımının ekranı.
4. Ayarlar'da veri işleri ve kanalın içerik kuralları var: eklentinin ve proxy'nin deneme okumaları; Talimatlar, Tonlar, Uyarı ifadeleri, Başlık eki.
5. Plan onayı "Video metni" adımının içinde bir seçenek ("Plandan sonra dur"). Onay biçimleri adımdan adıma değişiyor: "Bu başlığı seç", "Devam", "Bu tonla devam et".
6. "Görsel plan" ve "Video üretimi" artık bu programın işi değil. Stok görüntü, animasyon ve kurgu, ayrı bir proje olan Kurgu Motoru'nda yapılıyor; bu program ona bir kurgu paketi verecek.

Gerçek veride bugün seçilmiş başlık ve video kaydı yok. Dört başlık çalışması onay bekliyor (30A geneli, Rosemary Beach iki kez, bir değerlendirme). GÖREV-20'den sonra durum değişmişse gerçek veriye bakarak doğrula.

Bu görevde programın Claude adımları gerçek Claude ile çalıştırılmaz. Testler sahte claude ile yapılır. Alt ajan kullanma; işi kendin, sırayla yap.

KESİN SINIRLAR
- Rota Stüdyo, Housing Atlas ve Kurgu Motoru depolarında hiçbir dosya değiştirilmez.
- `data/` yalnız Adım 6'da, CLAUDE.md kuralına göre değişir: önce tam yedek, migration önce kopyada. Hiçbir kullanıcı verisi silinmez: başlık çalışmaları, adaylar, tonlar, talimatlar ve iş kayıtları yerinde kalır ya da taşınır.
- Talimat dosyalarının içeriğine dokunulmaz; yalnız ekranda durdukları yer değişir.
- Yazım zincirinin içeriği, talimatları ve tek çağrı düzeni (GÖREV-18, 19) değişmez; değişen, adımların ekranı ve durum yönetimidir.

==================================================
ADIM 1 — Dal
==================================================
1. Kullanıcının mesajı izin veriyorsa önce `gorev-20-eksik-veri` dalını main'e fast-forward ile al ve `v0.21.0` açıklamalı etiketini koy. İzin yoksa ya da fast-forward olmuyorsa dur ve sor.
2. Güncel main'den `gorev-21-katmanlar` dalını aç. Talimat değişikliği varsa CLAUDE.md kuralına göre ilk commit olarak ekle.

==================================================
ADIM 2 — Proje katmanı
==================================================
1. **Üst çubuk.**
   - Proje seçici: destinasyon; bugün "30A / South Walton". Tek proje varsa yalnız adı görünür.
   - İşler paneli ve Claude kullanımı göstergesi yerinde kalır.
   - Üst çubuktaki video seçici kalkar.
2. **Sol menü, video açık değilken.** "PROJE" grubunda dört ekran, en altta Ayarlar. Başka hiçbir şey görünmez:
   - **Veri:** bugünkü "VERİ" araçlarının hepsi (Kaynaklar, Toplama, Kalite, Kanıt ve öbürleri; kaynak kayıtları, toplayıcılar, "Zamanı gelenleri başlat", kalite kontrolü). Buna Ayarlar'dan taşınan eklenti deneme okuması ("Tarayıcı eklentisi" bölümündeki deneme), ısınma listesi ve proxy deneme okuması eklenir. Ekran kalabalıksa sekmelere böl; sekme adları ekranda açıkça yazar.
   - **Konu bankası:**
     - başlık önerisi ("Öneri al") ve kullanıcının kendi başlığını değerlendirme;
     - öneri çalışmaları ve adayları (Türkçe büyük, İngilizce küçük ve soluk), önceki öneriler;
     - her adayda "Bu başlıkla video aç" düğmesi. Video açılınca aday "kullanıldı" işaretlenir ve hangi videoda kullanıldığı görünür. Kullanılmayan adaylar havuzda kalır.
     - Bugünkü dört çalışma ve adayları buraya taşınır.
   - **Kanal:** Ayarlar'dan taşınan Talimatlar, Tonlar, Uyarı ifadeleri, Başlık eki. Bunlar kanalın içerik kurallarıdır.
   - **Videolar:**
     - projenin videoları: seçilen başlığın Türkçesi büyük, İngilizcesi küçük; oluşturma tarihi; adım ilerlemesi (ör. "3/8");
     - "Yeni video" düğmesi (isteğe bağlı çalışma adıyla; başlık 1. adımda bankadan seçilir ya da yazılır);
     - videoyu açmak için tıklanır;
     - bir videoyu listeden kaldırmak için "Arşive kaldır" ve "Arşivdekileri göster". Silme yoktur.
3. **Ayarlar.** Yalnız program ayarları kalır:
   - Kayıt klasörü;
   - Claude: bütün Claude adımlarının modeli, eforu ve sınırları tek tabloda. Her satırda adımın ekrandaki adı ve hangi video adımına ait olduğu yazar. Tek çağrı sınırı ve iş başına sınır da buradadır. Adımların içerikle ilgili ayarları buraya girmez;
   - Claude kullanımı;
   - Tarayıcı eklentisi: yalnız eşleştirme kodu ve bağlantı durumu;
   - ABD proxy'si: yalnız bağlantı bilgileri ve parolanın kasada olup olmadığı;
   - Hakkında.

   Taşınan bölümlerin eski adresleri (ör. `#settings/tonlar`) yeni yerlerine yönlenir.

==================================================
ADIM 3 — Video katmanı ve adımlar
==================================================
1. **Video açılınca sol menü.**
   - En üstte videonun adı ve "Videoyu kapat" düğmesi. Kapatınca menü proje görünümüne döner; video silinmez.
   - Altında yalnız bu videonun sekiz adımı: numara, ad, durum.
   - Proje grubu daraltılmış tek satır olarak ("← Proje") erişilebilir kalır. Açık video, bir dahaki açılışta hatırlanır.
2. **Adımlar.** `studio/workflow.py` → `STEPS` yeniden yazılır:

| No | Adım | İçerik (bugünkü kod) | Onay |
|---|---|---|---|
| 1 | Başlık ve vaat | Seçilen başlık (bankadan ya da değerlendirilmiş kendi başlığı), Türkçesi, izleyici sorusu ve vaat (başlık analizinden). Bankadan açılan videoda adım "onay bekliyor" başlar. | Evet |
| 2 | Veri paketi | Bugünkü "Veri paketi" (kanıt paketi ve yazar özeti); Claude yok | Hayır (bitince tamamlandı) |
| 3 | Plan | `metin_plan` ve `metin_plan_elestiri` | Evet |
| 4 | Yazım | `metin_bolum` … `metin_ceviri`; tonlar bu adımın ekranında seçilir | Hayır |
| 5 | Kontrol ve ton seçimi | Program denetimi, işletme adı denetimi, tonların karşılaştırması; onayla birlikte ton seçilir | Evet |
| 6 | Yayın paketi | Henüz yok: "Sonraki görevde gelecek" notu ve kısa açıklaması | — |
| 7 | Seslendirme | Henüz yok | — |
| 8 | Kurgu paketi | Henüz yok; Kurgu Motoru'na gidecek paket | — |

   "Veri" ve "Konu ve başlık" adımları proje katmanına taşınır. "Kontrol" adımı 5. adımın içine girer. "Görsel plan" ve "Video üretimi" kalkar.
3. **"Plandan sonra dur" seçeneği kalkar.** Yazım zinciri plan onaylanmadan 4. adıma geçmez. Zincirin sürdürme, kullanım sınırında bekleme ve kaldığı yerden devam özellikleri aynen korunur.
4. **Durumlar.** Bütün adımlar şu durumları kullanır: bekliyor, hazır, çalışıyor, onay bekliyor, onaylandı, tamamlandı, hata, eskidi. Kurallar Rota Stüdyo `docs/TASARIM.md` 6.2'deki gibidir:
   - İlk adım hazır başlar, öbürleri bekler.
   - Bir adım onaylanınca (onaysız adım bitince) sonraki adım hazır olur.
   - Bir adımın onaylanan çıktısı değişince sonraki adımlar "eskidi" olur ve sebebi Türkçe yazılır (ör. "Plan onayı değişti."). Kullanıcı ya yeniden çalıştırır ya da "Bu değişiklik etkilemiyor" der; adım önceki durumuna döner ve not durum günlüğüne yazılır.
   - Program yarıda kapanırsa "çalışıyor" görünen ama çalışan işi olmayan adım "hata" olur ve kaldığı yerden sürdürülebilir.
5. **Tek onay bileşeni.** 1, 3 ve 5. adımlarda aynı bileşen kullanılır:
   - çıktının okunur Türkçe hâli, not alanı;
   - **Onayla:** adım onaylanır.
   - **Düzeltme iste:** not, adım yeniden çalıştırılırken Claude'a malzeme olarak "kullanıcının düzeltme notu" diye verilir. Talimat dosyası değişmez. 5. adımda Düzeltme iste notu 4. adımı "hazır" yapar ve not yeniden yazımda verilir.
   - **Reddet:** adım hazır durumuna döner; 1. adımda başlık seçimi kalkar.

   "Bu başlığı seç", "Devam" ve "Bu tonla devam et" düğmeleri bu bileşene dönüşür. 5. adımda Onayla'nın yanında hangi tonla devam edileceği seçilir.
6. **Sürümler.** Her adımın çıktısı dosyaya yazılır; eski sürüm silinmez. Adım ekranında "Sürümler" bölümünden görülür.

==================================================
ADIM 4 — Claude adımlarında maliyet görünürlüğü
==================================================
GÖREV-18'de gelenler korunur: başlamadan tahmin ve "Başlat" onayı, gerçek harcama ile tahminin yan yana gösterilmesi, gerçek harcama tahminin 1,5 katını geçerse uyarı. Bunları her Claude adımında aynı yerde ve aynı biçimde göster:
- konu bankasındaki öneri ve değerlendirme,
- 3, 4 ve 5. adımlar.

Şunlar eksikse ekle:
1. Düğmenin üstünde tahmin: kaç çağrı, kaç token (okunan ve yazılan), model.
2. İş sürerken o ana kadarki harcama (çağrı ve token) ve "İptal" düğmesi. İptal edilen iş kayda "iptal edildi" diye düşer, harcaması sayılır.
3. Çok parçalı adımlarda (3 ve 4) halka tablosu: her halkanın durumu, çağrı sayısı, gerçek ve tahmini tokeni; altında toplam ve tahmin. Örnek: Rota Stüdyo'daki "4 · Yazım" ekranının halka tablosu.

==================================================
ADIM 5 — Veri modeli ve taşıma
==================================================
1. Başlık çalışmaları ve adaylar projeye (destinasyona) bağlı olur, videoya bağlı olmaz. Video, seçtiği adayı ya da kendi başlığının değerlendirmesini gösterir.
2. Adım durumları, eskime sebepleri, onay notları ve durum günlüğü videoya bağlı saklanır.
3. Şema değişiyorsa migration önce `work\` altındaki kopyada denenir; satır sayıları ve `foreign_key_check` karşılaştırılır (CLAUDE.md).
4. Bugünkü dört başlık çalışması, adayları ve iş kayıtları kaybolmadan konu bankasına geçer.

==================================================
ADIM 6 — Testler, gerçek veri, belgeler, teslim
==================================================
1. Testler:
   - **Video açık değilken:** menüde yalnız proje ekranları ve Ayarlar var.
   - **Video açıkken:** yalnız o videonun sekiz adımı var; "Videoyu kapat" menüyü proje görünümüne döndürüyor.
   - **Video açma:** "Bu başlıkla video aç" videoyu açıyor ve adayı "kullanıldı" işaretliyor.
   - **Durum geçişleri:** Rota Stüdyo 6.2'deki kurallar; eskime ve "Bu değişiklik etkilemiyor"; yarıda kapanınca "hata".
   - **Onay bileşeni:** üç düğme; Düzeltme iste notunun yeniden çalıştırmada Claude'a giden malzemede bulunması (sahte claude ile).
   - **Plan:** onaylanmadan yazım başlamıyor.
   - **Taşıma:** Ayarlar'dan taşınan bölümlerin eski adreslerinin yönlenmesi; Ayarlar'da veri işi ve içerik kuralı kalmaması.
   - **Maliyet:** tahmin, o ana kadarki harcama, iptal, halka tablosu.
   - **Migration:** kopyada satır sayıları.

   Tam takım: `.venv\Scripts\python.exe -m pytest -q` ve `node --test tests/frontend.test.mjs`.
2. **Gerçek veri.** Uygulama kapalıyken `data/` klasörünün tam yedeğini al, sonra migration'ı gerçek veride uygulamanın normal açılışıyla çalıştır. Satır sayılarını ve konu bankasında dört çalışmanın göründüğünü doğrula. Claude adımı çalıştırma.
3. **Ekran kontrolü.** Programı geçici bir veri kopyasıyla aç; video açık ve kapalıyken menünün ekran görüntülerini al ve rapora koy.
4. **Belgeler.** `CALISMA_MANTIGI.md`, `docs/M15-CLAUDE-ADIMLARI.md`, `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md` ve yeni `docs/M19-IS-AKISI-KATMANLAR.md` (katmanlar, adımlar, durumlar, onay bileşeni). CLAUDE.md'ye kısa bir kural ekle:
   - proje ve video katmanları karışmaz;
   - Ayarlar yalnız program ayarıdır;
   - kullanıcıya bir yer tarif edilirken ekranda yazan tam adlarla yol verilir (ör. "Sol menü → Konu bankası → Bu başlıkla video aç").

   Uygulama sürümü 0.22.0.
5. Dalı push et. main'e alma ve etiket koyma; kararı yönetici verir.

TESLİM
`docs/gorevler/GOREV-21/` altında `GOREV.md` (bu dosya), `RAPOR.md` ve ekran görüntüleri. Raporda şunlar olsun:
- Yeni menü düzeni, ekran adlarıyla.
- Hangi ekranın, bölümün ve düğmenin nereye taşındığı (eski yer → yeni yer).
- Durum geçişleri ve onay bileşeni.
- Migration sonucu: satır sayıları, yedeğin yeri.
- Maliyet görünürlüğünde neyin zaten olduğu, neyin eklendiği.
- Rota Stüdyo'dan kopyalanan ya da örnek alınan parçalar.
- Kullanıcı için kısa Türkçe tarif: ilk videoyu açmaktan plan onayına kadar, her adımda ekrandaki tam adlarla. Örnek: "Sol menü → Konu bankası → 30A geneli çalışması → adayın 'Bu başlıkla video aç' düğmesi → 1 · Başlık ve vaat → Onayla".

Kullanıcıya son mesajın yalnız şu olsun: "GÖREV-21 bitti, dal gorev-21-katmanlar, son commit <hash>" ve varsa tamamlanamayan adımlar.
