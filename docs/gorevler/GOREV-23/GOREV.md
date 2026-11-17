GÖREV-23 — Kiralama okuyucularını tamamla: RealJoy, 30A Beach Girls fiyatı, Vacasa tam liste, LocalVR (Outdoor Shower)

BAĞLAM
30A Studio, Mucahit'in YouTube kanalı için veri toplayıp video metni yazdıran yerel programdır. Program klasörü: `C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`.

Durum:
- main `2848c6f` = `v0.22.0`.
- GÖREV-22 (dal `gorev-22-kiralama`, son commit `9ead6a8`, uygulama 0.23.0, şema 22) yönetici tarafından kabul edildi. Raporu: `docs/gorevler/GOREV-22/RAPOR.md`. Önce onu oku.

GÖREV-22'den açık kalanlar:
1. **RealJoy** (realjoy.com, 61 ilan): Cloudflare doğrulaması var (bot koruması; proxy kullanılmaz). Okuma yolu kullanıcının Chrome'undaki eklentidir. Okuyucu yazılamadı, çünkü bir ilan sayfasının ham kaydı yoktu. Kullanıcı bu görevden hemen önce eklenti denemesini çalıştırdı: Sol menü → Veri → Okuma denemeleri → "Eklentinin deneme okuması" → "Sorunlu sitelerden birer sayfa dene". Kaydın gelip gelmediğini sen doğrula.
2. **30A Beach Girls** (30a-beachgirls.com; sitede 145 ev): evler şirketin kendi envanteri olarak kuruldu. Fiyat AvantStay'in ayrı servisinden geliyor (`arriere.prod.avantstay.com`). GÖREV-22'de bu servise deneme isteği çalışma ortamı tarafından engellendi; fiyat sorgusu yazılmadı ve kapalı (`quotes: false`). Kullanıcı bu görevde 3–5 deneme isteğine izin veriyor.
3. **Vacasa:** arama sayfasının `page_limit` ile tam ev listesini verip vermediği denenemedi (inceleme sınırı doldu).
4. **Outdoor Shower** (21 ilan): alan adı askıda; şirket LocalVR'ye devredilmiş ("LocalVR Expands in 30A Florida with Acquisition of Outdoor Shower"). `golocalvr.com` bölge engelli değil, doğrudan açılıyor. Okuyucu yok.

Ayrıca: `tests/test_gorev21.py::test_the_estimate_the_spending_and_the_link_table_of_plan_and_writing` zamanlamaya bağlı olarak ara sıra başarısız oluyor (GÖREV-22 raporu).

Bu görevden sonra kullanıcı tek bir gece çekimi başlatacak (yaklaşık 11 saat). Bu yüzden amaç, çekime girecek bütün şirketlerin okuyucularının hazır olmasıdır.

Bu görevde programın Claude adımları çalıştırılmaz. Alt ajan kullanma; işi kendin, sırayla yap.

KESİN SINIRLAR
- CLAUDE.md'deki "Bilgi toplama" ve "Veri güvenliği" kuralları aynen geçerlidir:
  - giriş, ödeme, rezervasyon, sepet ya da kişisel form yok;
  - gizlenme, parmak izi sahteciliği, doğrulama çözme servisi ve IP döndürme yok;
  - aynı sitede iki istek arası en az 8 saniye;
  - doğrulamayı yalnız kullanıcı geçer.
- Proxy yalnız bölge engelli listedeki alan adları içindir (bugün cvs.com, publix.com, hcafloridahealthcare.com, winndixie.com, 360blue.com, vacasa.com). realjoy.com, golocalvr.com, 30a-beachgirls.com ve AvantStay'in servisi proxy'den gitmez.
- Proxy bilgileri ve parola dosyaya, günlüğe, rapora ve sohbete yazılmaz.
- Eklentiyle gerçek sitelerden okumayı kullanıcı başlatır; sen eklentiyi yalnız yerel deneme sayfalarında sınarsın.
- `data/` yalnız Adım 6'da, CLAUDE.md kuralına göre değişir (önce tam yedek). Kiralama fiyat çekimini sen başlatma.
- Talimat dosyalarının içeriğine dokunulmaz. Housing Atlas ve Rota Stüdyo depolarında hiçbir dosya değiştirilmez. Zamanlanmış görev oluşturulmaz.

==================================================
ADIM 1 — main ve dal
==================================================
1. Program açıksa kapanmasını bekle.
2. Kullanıcının mesajı izin veriyorsa `gorev-22-kiralama` dalını main'e fast-forward ile al ve `v0.23.0` açıklamalı etiketini koy; ikisini push et. Fast-forward olmuyorsa dur ve sor.
3. Güncel main'den `gorev-23-okuyucular` dalını aç. Kullanıcının Kanal ekranından yaptığı talimat değişikliği varsa CLAUDE.md kuralına göre ilk commit olarak ekle.

==================================================
ADIM 2 — RealJoy
==================================================
1. Eklentinin deneme kayıtlarına bak (`data/raw/eklenti/`; salt okunur, CLAUDE.md yöntemi). RealJoy'un bir ilan sayfasının 17 Kasım 2026 tarihli ham kaydı var mı?
2. **Kayıt yoksa ya da kayıtta yalnız doğrulama sayfası varsa** kullanıcıya sohbette bu tarifi ver ve bekle: "Chrome'u ve programı açın. Sol menü → Veri → Okuma denemeleri → 'Eklentinin deneme okuması' → 'Sorunlu sitelerden birer sayfa dene'. Chrome'da açılan sayfada doğrulama kutusu çıkarsa işaretleyin. Bitince programı kapatıp bana 'tamam' yazın." Düğmenin adı ekranda farklıysa ekrandaki tam adı yaz.
3. Kayıttan fiyatın hangi istekle geldiğini bul: ICND rezervasyon motoru (`/bookingEngine/`), arkada Track.
4. **Fiyat GET ile alınabiliyorsa** okuyucuyu yaz. Bu, eklentinin sayfa olarak açıp okuyabileceği bir yükleme olmalı: ilan sayfası ya da sitenin herkese açık bir GET adresi. Eklenti tıklamaz, yazı yazmaz, form göndermez.
   - Fiyat adresinin eklentiyle okunduğunu görmek için o adresi deneme listesine ekle ve kullanıcıdan düğmeye bir kez daha basmasını iste. Aynı tarifle, en çok iki kez.
   - Çekimde RealJoy sayfaları eklentiyle okunur; eklenti bağlı değilse programın kendi tarayıcısıyla.
5. **Fiyat yalnız tıklama ya da form gönderme ile geliyorsa** okuyucuyu yazma; sebebini rapora yaz.
6. Eşleme mevcut kurallarla yapılır. GÖREV-20'ye göre sitenin 30A ilan listesi sokak adresi, 8 ondalıklı koordinat, yatak sayısı ve birim kodu veriyor. Book>Direct'teki eski bağlantılar çalışmıyor.

==================================================
ADIM 3 — 30A Beach Girls fiyatı (AvantStay)
==================================================
1. Kullanıcı, AvantStay'in servisine en çok 5 deneme isteğine izin verdi; doğrudan, aralarında en az 8 saniye. Çalışma ortamın bir izin penceresi gösterirse kullanıcı onaylayacak; ortam yine engellerse etrafından dolaşma, rapora yaz.
2. GÖREV-22'de betikten çıkarılan iki sorguyu dene (`docs/M11-KONAKLAMA-FIYATLARI.md`): takvim ve fiyat dökümü. Tutarların birimini, durum sözlerini ve ret metinlerini gör.
3. **Sepet konusu önemli.** GÖREV-22, fiyat dökümü yanıtında bir sepet numarası döndüğünü ve sorgunun sunucuda her soruda bir sepet kaydı açıyor olabileceğini yazdı.
   - Fiyat, sitenin evin sayfasında herkese gösterdiği fiyat kutusunun yaptığı istekle ve rezervasyon ya da sepet akışı başlatmadan alınabiliyorsa okuyucuyu yaz.
   - Fiyat yalnız sepet ya da rezervasyon kaydı açan bir istekle geliyorsa kullanma. Fiyat sorgusu kapalı kalır; evler fiyatsız listelenir. Sebebi rapora yazılır. Bu bir kuraldır, bot koruması meselesi değildir: rezervasyon akışına girmiyoruz.
4. Okuyucu yazılırsa, testi incelemenin ham yanıtlarından fixture'larla yap. Yapılandırmada fiyatı aç (`quotes: true`).

==================================================
ADIM 4 — Vacasa tam liste
==================================================
1. Arama sayfasını (`/search?place=/usa/Highway-30A/`) `page_limit` ile proxy üzerinden iste; en çok 3 istek, aralarında en az 8 saniye. 30A'daki ev sayısının (GÖREV-22'de 300) tamamı geliyor mu, bak.
2. Gelmiyorsa sitenin kendi sayfalama isteğini kullan. Okuyucu tam listeyi alana kadar sayfaları ister; liste eksik kalırsa "liste eksik" kuralı aynen kalır.

==================================================
ADIM 5 — LocalVR (Outdoor Shower'ın evleri)
==================================================
1. `golocalvr.com`'u doğrudan incele: en çok 10 sayfa, aralarında en az 8 saniye.
   - rezervasyon altyapısı, 30A ev listesi ve fiyatı veren istek bulunur;
   - mevcut uyarlayıcılardan birine uyuyorsa (rescms, track, streamline, vr_router, vrp, property_quote, exceptional_stay, asmx_quote, wander, qvr, nrbe, vacasa, avantstay) yalnız yapılandırmaya satır eklenir; uymuyorsa yeni uyarlayıcı yazılır.
2. Outdoor Shower'ın 21 Book>Direct ilanı, LocalVR'nin listesine yalnız programın adres kuralıyla bağlanır. Bu kural 360 Blue'da da kullanıldı: aynı sokak numarası ve sokak, aynı daire, aynı oda sayısı, tek aday, koordinatlar 2 km'den yakın. Ad karşılaştırılmaz. Bağlanmayan ilan fiyatsız kalır.
3. Ölü bağlantılar (outdoorshower30a.com) çekimde sorulmaz (GÖREV-22'deki `dead_links` gibi).
4. LocalVR'nin, Book>Direct'te olmayan öbür 30A evleri bu görevde eklenmez.
5. Doğrulama ya da engel çıkarsa GÖREV-20 kuralları geçerlidir. Engeli aşmak için başka yol aranmaz; şirket rapora yazılır.

==================================================
ADIM 6 — Gerçek veri, çekim tahmini, test, belgeler
==================================================
1. **Yedek ve yapılandırma.** Uygulama kapalıyken `data/` klasörünün tam yedeğini al. Program gerçek veriyle normal biçimde açılır; yalnız yeni şirket yapılandırmaları ve açılan fiyat sorguları girer. Kiralama fiyat çekimi başlatılmaz.
2. **Çekim tahmini.** "Güncelleme zamanı gelenler" tablosundaki tahmin yeni şirketleri de göstersin. Toplam süreyi rapora yaz.
3. **Zamanlamaya bağlı test.** `test_gorev21.py::test_the_estimate_the_spending_and_the_link_table_of_plan_and_writing` testindeki yarışı bul ve düzelt; test sabit bir bekleme yerine işin bittiğini beklesin. Tam takımı en az iki kez çalıştır: `.venv\Scripts\python.exe -m pytest -q` ve `node --test tests/frontend.test.mjs`.
4. **Yeni testler.** Her yeni ya da değişen uyarlayıcı için fixture testi. Vacasa için tam listenin alınması ve eksik liste kuralı. Outdoor Shower ilanlarının adres kuralıyla bağlanması, adı benzeyen ama adresi tutmayan evin bağlanmaması.
5. **Belgeler ve sürüm.** `docs/M11-KONAKLAMA-FIYATLARI.md`, `docs/M14-KANIT-PAKETI.md` (gerekirse), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`. Uygulama sürümü 0.24.0.
6. Dalı push et; GitHub'daki test çalışmasının sonucunu rapora yaz. main'e alma ve etiket koyma; kararı yönetici verir.

TESLİM
`docs/gorevler/GOREV-23/` altında `GOREV.md` (bu dosya) ve `RAPOR.md`. Raporda şunlar olsun:
- **Şirket tablosu:** şirket, ilan ya da ev sayısı, altyapı, okuma yolu, sonuç ya da okunamama sebebi. Bütün kiralama eksiklerinin son durumu: kaç ilan fiyatlanabilir, kaçı hâlâ eksik ve neden.
- **RealJoy:** kayıt, fiyat isteği, okuyucu.
- **AvantStay:** yapılan istekler, sepet konusu, sonuç.
- **Vacasa:** tam liste sonucu.
- **LocalVR:** altyapı, bağlanan ilan sayısı.
- **Canlı istekler:** listesi (`canli-istekler.csv`).
- **Gerçek veri:** ne değişti, yedeğin yeri.
- **Testler:** iki tam turun sonuçları ve CI sonucu.
- **Kullanıcı için gece çekimi tarifi:** Türkçe, adım adım, ekrandaki tam adlarla (Sol menü → Veri → Kaynaklar → Güncelleme zamanı gelenler → Zamanı gelenleri başlat). Tarif şunları söylesin:
  - eklentinin ve proxy'nin bağlı olduğunun nereden görüleceği;
  - doğrulama isteyebilecek siteler (RealJoy dahil) ve doğrulamanın nasıl geçileceği;
  - tahmini süre;
  - bitince hangi ekranda neye bakılacağı.

Kullanıcıya son mesajın yalnız şu olsun: "GÖREV-23 bitti, dal gorev-23-okuyucular, son commit <hash>" ve varsa tamamlanamayan adımlar.
