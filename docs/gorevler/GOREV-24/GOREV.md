GÖREV-24 — RealJoy fiyat okuyucusu (eklentinin kaydından)

BAĞLAM
30A Studio, Mucahit'in YouTube kanalı için veri toplayıp video metni yazdıran yerel programdır. Program klasörü: `C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`.

Durum:
- main `9ead6a8` = `v0.23.0`.
- GÖREV-23 (dal `gorev-23-okuyucular`, son commit `f87582c`, uygulama 0.24.0, şema 23) yönetici tarafından kabul edildi. Raporu: `docs/gorevler/GOREV-23/RAPOR.md`. Önce onu, sonra `docs/gorevler/GOREV-20/RAPOR.md`'deki "RealJoy için sıradaki iş" bölümünü oku.

Kiralama şirketlerinden yalnız RealJoy (realjoy.com, 61 Book>Direct ilanı) eksik kaldı.
- Site Cloudflare doğrulaması istiyor. Bu bot korumasıdır; proxy kullanılmaz.
- Okuma yolu kullanıcının Chrome'undaki eklentidir; eklenti bağlı değilse programın kendi tarayıcısı.

Kullanıcı 17 Kasım 2026'da eklenti denemesini çalıştırdı. Kayıtlar `data/raw/eklenti/20261117/` altında:
- `125425-8fbe6b7c.html` ve `.json`: RealJoy'un bir ilan sayfası ("Sea La Vie Seaside Main House | RealJoy", HTTP 200, 311 KB). **Okuyucu bu kayıttan yazılacak.**
- `125337-e486b52f.html` ve `.json`: RealJoy'un 30A ilan listesi sayfası. Bu sefer **HTTP 429** (çok fazla istek) döndü, 3,6 KB.

Listenin sağlam kaydı 11 Kasım denemesindedir (`data/raw/eklenti/20261111/` altında realjoy.com etiketli kayıt). GÖREV-20'ye göre o liste her ev için sokak adresi, 8 ondalıklı koordinat, yatak sayısı ve birim kodu veriyor.

Gece çekimi bu görevden sonra başlayacak. Bu yüzden amaç, RealJoy'un çekime hazır girmesidir.

Bu görevde programın Claude adımları çalıştırılmaz. Alt ajan kullanma; işi kendin, sırayla yap.

KESİN SINIRLAR
- CLAUDE.md'deki "Bilgi toplama" ve "Veri güvenliği" kuralları aynen geçerlidir:
  - giriş, ödeme, rezervasyon, sepet ya da form yok;
  - eklenti tıklamaz, yazı yazmaz, form göndermez;
  - doğrulama çözme ve gizlenme yok;
  - doğrulamayı yalnız kullanıcı geçer.
- realjoy.com proxy'den gitmez. Doğrudan istek Cloudflare'e takılır; sen siteye canlı istek yapma. Kayıtlar yeterli değilse kullanıcıdan eklenti denemesini yeniden çalıştırmasını iste (Adım 2.4).
- **429 cevabı bir hız sınırıdır.** Program 429 alınca bekler ve aynı sayfayı daha sonra en çok iki kez yeniden ister. Bekleme süresi `Retry-After` başlığı varsa ona göre, yoksa en az 60 saniyedir. Hızı artırmaz. RealJoy'da iki sayfa arası en az 8 saniye kuralı aynen kalır; bu site için aralığı gerekirse büyüt.
- `data/` yalnız Adım 4'te, CLAUDE.md kuralına göre değişir (önce tam yedek). Kiralama fiyat çekimini sen başlatma.
- Talimat dosyalarına, Housing Atlas ve Rota Stüdyo depolarına dokunulmaz. Zamanlanmış görev oluşturulmaz.

==================================================
ADIM 1 — main ve dal
==================================================
1. Program açıksa kapanmasını bekle.
2. Kullanıcının mesajı izin veriyorsa `gorev-23-okuyucular` dalını main'e fast-forward ile al ve `v0.24.0` açıklamalı etiketini koy; ikisini push et. Fast-forward olmuyorsa dur ve sor.
3. Güncel main'den `gorev-24-realjoy` dalını aç. Talimat değişikliği varsa CLAUDE.md kuralına göre ilk commit olarak ekle.

==================================================
ADIM 2 — Fiyat isteğini bul
==================================================
1. İlan sayfasının ham kaydını (`125425-8fbe6b7c.html`) salt okunur kopyadan incele. Site ICND rezervasyon motorunu kullanıyor (`/bookingEngine/`), arkada Track. Şunları bul:
   - evin birim kodu ve kimliği;
   - müsaitlik takvimi ve fiyatın hangi istekle geldiği;
   - isteğin GET mi POST mu olduğu, hangi parametreleri aldığı;
   - vergi ve ücret kalemlerinin nasıl gösterildiği.
2. Fiyat **GET ile** alınabiliyorsa okuyucu yazılabilir. Eklenti bir adresi sayfa olarak açıp okur; sitenin herkese açık bir GET adresi, sayfa olarak açıldığında JSON ya da HTML döndürüyorsa eklenti bunu okuyabilir.
3. Fiyat yalnız tıklama, form gönderme ya da POST ile geliyorsa okuyucuyu yazma. Sebebini rapora yaz ve RealJoy'u "fiyatı okunamayan şirketler" satırında bırak.
4. **Doğrulama.** Bulduğun fiyat adresinin eklentiyle gerçekten okunduğunu görmek için o adresten bir örneği (bir ev, bir hafta) eklentinin deneme listesine ekle. Sonra kullanıcıya sohbette şu tarifi ver ve bekle: "Chrome'u ve programı açın. Sol menü → Ayarlar → Tarayıcı eklentisi bölümünde 'Bağlı' yazdığından emin olun. Sonra Sol menü → Veri → Okuma denemeleri → 'Eklentinin deneme okuması' → 'Sorunlu sitelerden birer sayfa dene'. Chrome'da doğrulama çıkarsa kutuyu işaretleyin. Bitince programı kapatıp bana 'tamam' yazın." Bunu en çok iki kez iste. Gelen kayıttan fiyatın birimini ve biçimini doğrula.

==================================================
ADIM 3 — Okuyucu ve eşleme
==================================================
1. `studio/sources/agency_adapters.py`'ye RealJoy uyarlayıcısını yaz. Mevcut Track tabanlı uyarlayıcılardan biri uyuyorsa onu kullan. Kurallar aynen geçerlidir (`docs/M11-KONAKLAMA-FIYATLARI.md`):
   - vergi ve ücretler sitenin gösterdiği gibi alınır;
   - toplamı site göstermiyorsa program hesaplamaz, olanı yazar;
   - müsait olmayan hafta ve en az konaklama ayrı tutulur.
2. **Eşleme.** RealJoy'un 30A ilan listesinden, yalnız programın adres kuralıyla yapılır: aynı sokak numarası ve sokak, aynı daire, aynı oda sayısı, tek aday. Ad karşılaştırılmaz. Book>Direct'teki eski bağlantılar çalışmıyor; çekimde sorulmaz (`dead_links`).
3. **Çekim.**
   - Sıra: RealJoy sayfaları ve fiyat adresleri eklentiyle, eklenti bağlı değilse programın kendi tarayıcısıyla okunur.
   - Doğrulama çıkarsa site sona bırakılır, en sonda 15 dakika beklenir; olmazsa atlanır ve kaydedilir.
   - 429 kuralı yukarıdaki gibidir. Üst üste 429 gelirse RealJoy o çekimde durdurulur, o ana kadarki fiyatlar saklanır, sebep kaydedilir.
4. **Testler.** Fixture'lar ham kayıtlardan kesilir; değer değiştirilmez. Şunlar sınanır:
   - fiyatın ayrıştırılması;
   - dolu hafta;
   - adres eşlemesi, ve adı benzeyen ama adresi tutmayan evin bağlanmaması;
   - 429'da bekleme ve en çok iki yeniden deneme;
   - üst üste 429'da şirketin durması.

==================================================
ADIM 4 — Gerçek veri, tahmin, test, belgeler
==================================================
1. **Yedek ve yapılandırma.** Uygulama kapalıyken `data/` klasörünün tam yedeğini al. Program gerçek veriyle normal biçimde açılır; yalnız RealJoy'un yapılandırması girer. Kiralama fiyat çekimi başlatılmaz.
2. **Çekim tahmini.** "Güncelleme zamanı gelenler" tablosundaki tahmin RealJoy'u da göstersin. Toplam süreyi rapora yaz.
3. **Testler.** Tam takımı çalıştır: `.venv\Scripts\python.exe -m pytest -q` ve `node --test tests/frontend.test.mjs`.
4. **Belgeler ve sürüm.** `docs/M11-KONAKLAMA-FIYATLARI.md`, `docs/M16-TARAYICI-EKLENTISI.md` (deneme listesindeki fiyat adresi), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`. Uygulama sürümü 0.25.0.
5. Dalı push et; CI sonucunu rapora yaz. main'e alma ve etiket koyma.

TESLİM
`docs/gorevler/GOREV-24/` altında `GOREV.md` (bu dosya) ve `RAPOR.md`. Raporda şunlar olsun:
- fiyat isteğinin ne olduğu ve eklentiyle okunup okunmadığı;
- okuyucu ve eşleme sonucu (çevrimdışı denemede kaç ilan bağlanıyor);
- 429 kuralı;
- gerçek veride ne değişti, yedeğin yeri;
- yeni çekim tahmini;
- kullanıcı için gece çekimi tarifi: Türkçe, adım adım, ekrandaki tam adlarla. Tarif GÖREV-23 raporundakinin güncel hâli olsun ve RealJoy'u da kapsasın: Chrome açık kalacak, RealJoy doğrulama isteyebilir.

Kullanıcıya son mesajın yalnız şu olsun: "GÖREV-24 bitti, dal gorev-24-realjoy, son commit <hash>" ve varsa tamamlanamayan adımlar.
