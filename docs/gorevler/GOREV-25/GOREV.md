GÖREV-25 — RealJoy: eklentiyle sayfanın kendi sorguları (fiyat ve ev listesi)

BAĞLAM
30A Studio, Mucahit'in YouTube kanalı için veri toplayıp video metni yazdıran yerel programdır. Program klasörü: `C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`.

Durum:
- main `f87582c` = `v0.24.0`.
- GÖREV-24 (dal `gorev-24-realjoy`) RealJoy'un fiyatını inceledi ve okuyucu yazmadan bitti. Raporunu (`docs/gorevler/GOREV-24/RAPOR.md`) önce oku.

GÖREV-24'ün bulduğu:
- **Sayfa:** RealJoy'un ev sayfası müsaitlik takvimini ve en az konaklamayı herkese açık veriyor. Ev kimliği `propertyID`.
- **Fiyat:** yalnız sayfanın kendi tarih formunun gönderdiği istekle geliyor: `POST /ajax/quote`. Alanlar: `checkin`, `checkout`, `propertyID`, `roomTypeID`, `propertyName` ve boş `hash`. Cevap fiyat dökümü HTML'i; uygun değilse yalnız "No".
  - Bu istek sepet, rezervasyon ya da kayıt açmıyor; kişisel bilgi, giriş ve ödeme yok.
  - Ziyaretçi takvimde tarih seçince sayfa bu isteği kendiliğinden gönderiyor.
- **Liste:** liste sayfası 311 ev diyor ama ilk açılışta 12 evi veriyor; gerisi kaydırınca geliyor. O isteğin türü görülmedi.
- **Eşleme:** ilk 12 evle yapılan adres eşlemesinde 61 Book>Direct ilanından 1'i bağlandı; tam liste olmadan gerçek sayı bilinmiyor.

**Kullanıcı kararı (17 Kasım 2026).** Eklenti, bir sitenin kendi sekmesinden, o sayfanın ziyaretçi için zaten yaptığı herkese açık sorgu isteklerini gönderebilir. POST da buna dahildir.
- **Kapsam:** fiyat sorgusu ve ev listesinin devamı (sayfalama, "daha fazla yükle").
- **Alanlar:** yalnız sayfanın kendi gönderdiği alanlar (tarih, ev kimliği, oda tipi, ev adı ve sayfanın boş gönderdiği alanlar). Değerler sayfanın gönderdiği biçimde olur.
- **Yasak olan aynen kalır:** giriş, hesap, ödeme, rezervasyon, sepet, kişisel bilgi, iletişim formu, doğrulama çözme. Eklenti tıklamaz ve yazı yazmaz; isteği sayfanın betiği gibi gönderir.
- **Çerezler:** eklenti çerezleri, parolaları ve geçmişi okumaz ve programa taşımaz. İstek sitenin kendi sekmesinden gittiği için tarayıcı o sitenin oturumunu kendisi kullanır.
- Bu kural CLAUDE.md'ye ve `docs/M16-TARAYICI-EKLENTISI.md`'ye yazılır (Adım 5).

Gece çekimi bu görevden sonra, RealJoy dahil tek seferde yapılacak.

Bu görevde programın Claude adımları çalıştırılmaz. Alt ajan kullanma; işi kendin, sırayla yap.

KESİN SINIRLAR
- realjoy.com'a sen doğrudan canlı istek yapma; proxy kullanılmaz (bot koruması, bölge engeli değil). Canlı okuma yalnız kullanıcının başlattığı eklenti denemesiyle olur.
- **RealJoy hızı:**
  - iki istek arası en az 20 saniye; aynı anda tek istek;
  - 429'da `Retry-After` kadar, yoksa en az 60 saniye beklenir ve en çok iki kez yeniden denenir;
  - üst üste 429 gelirse RealJoy o çekimde durur, o ana kadarki sonuçlar saklanır, sebep kaydedilir.
- Doğrulama çıkarsa kullanıcı geçer; site sona bırakılır, en sonda 15 dakika beklenir, olmazsa atlanır.
- `data/` yalnız Adım 4'te, CLAUDE.md kuralına göre değişir (önce tam yedek). Kiralama fiyat çekimini sen başlatma.
- Talimat dosyalarına, Housing Atlas ve Rota Stüdyo depolarına dokunulmaz. Zamanlanmış görev oluşturulmaz.

==================================================
ADIM 1 — Dal
==================================================
1. Program açıksa kapanmasını bekle.
2. `gorev-24-realjoy` dalının son commit'inden `gorev-25-realjoy-sorgu` dalını aç. main'e alma; GÖREV-24 ve GÖREV-25'i yönetici birlikte alacak.
3. Talimat değişikliği varsa CLAUDE.md kuralına göre ilk commit olarak ekle.

==================================================
ADIM 2 — Eklentiye "sayfanın kendi sorgusu"
==================================================
1. Eklentiye, programın verdiği bir sorguyu sitenin açık sekmesinden göndermeyi ekle. Sorgu şunları taşır: alan adı, yol, yöntem (GET ya da POST), alanlar. Kurallar:
   - Yalnız programın izinli listesindeki alan adları ve yollar. RealJoy için: `/ajax/quote` ve Adım 3'te bulunacak liste yolu. Liste yapılandırmada durur.
   - İstek o sitenin sekmesinden, sayfanın kendi kökeninden gider. Başka siteye istek yok.
   - Giriş, ödeme, rezervasyon, sepet, hesap, iletişim adreslerine giden sorgu reddedilir. Yollar ve alan adları için bir yasak listesi tutulur ve testle gösterilir.
   - Cevabın ham kopyası, isteğin yöntemi, alanları ve zamanı kaydedilir.
2. Eklenti sürümü 0.20.0. Kullanıcı Chrome'da eklentiyi yeniden yükleyecek; tarif rapora yazılır.
3. Eklenti yerel deneme sayfalarında, Playwright'in Chromium'u ve geçici profille sınanır (CLAUDE.md).

==================================================
ADIM 3 — RealJoy ev listesi ve fiyat
==================================================
1. **Liste.**
   - Liste sayfasının betiklerinden kaydırınca gelen evlerin hangi istekle geldiğini bul: yol, yöntem, sayfa ya da kaydırma parametresi.
   - Bu istekle 311 evin tamamı alınır; her ev için ev kimliği, sokak adresi, koordinat, yatak sayısı ve birim kodu.
   - Liste eksik kalırsa "liste eksik" kuralı geçerlidir: o çekimde tahmin yürütülmez.
2. **Doğrulama.** Liste isteğinden bir örnek ve fiyat isteğinden bir örnek (bir ev, bir hafta) eklentinin deneme listesine girer. Kullanıcıya sohbette şu tarifi ver ve bekle:

   "Önce Chrome'da eklentiyi yeniden yükleyin: adres çubuğuna `chrome://extensions` yazın, '30A Studio Yardımcısı'nın kartındaki yenile düğmesine basın. Sonra programı açın. Sol menü → Ayarlar → Tarayıcı eklentisi bölümünde 'Bağlı' yazdığından emin olun. Sonra Sol menü → Veri → Okuma denemeleri → 'Eklentinin deneme okuması' → 'Sorunlu sitelerden birer sayfa dene'. Chrome'da doğrulama çıkarsa kutuyu işaretleyin. Bitince programı kapatıp bana 'tamam' yazın."

   Ekrandaki adlar farklıysa tam adları yaz. Bunu en çok üç kez iste. Gelen kayıtlardan liste biçimini ve fiyat dökümünü doğrula.
3. **Okuyucu.** `studio/sources/agency_adapters.py`'ye RealJoy uyarlayıcısını yaz:
   - takvim ve en az konaklama ev sayfasından;
   - fiyat `/ajax/quote` cevabından. Kalemler, vergi ve ücretler sitenin gösterdiği gibi alınır; "No" cevabı "uygun değil" olarak ayrı tutulur. Takvimin dolu gösterdiği hafta sorulmaz.
4. **Eşleme.** Yalnız programın adres kuralıyla yapılır: aynı sokak numarası ve sokak, aynı daire, aynı oda sayısı, tek aday. Ad karşılaştırılmaz. Book>Direct'teki eski bağlantılar sorulmaz (`dead_links`).
5. **Çekim.** RealJoy istekleri eklentiyle gider. Eklenti bağlı değilse RealJoy o çekimde atlanır ve kaydedilir: programın kendi tarayıcısı bu sorguyu göndermez. Hız ve 429 kuralı yukarıdaki gibidir.

==================================================
ADIM 4 — Gerçek veri, tahmin, test, belgeler
==================================================
1. **Yedek ve yapılandırma.** Uygulama kapalıyken `data/` klasörünün tam yedeğini al. Program gerçek veriyle normal biçimde açılır; yalnız RealJoy yapılandırması ve eklentinin izinli sorgu listesi girer. Kiralama fiyat çekimi başlatılmaz.
2. **Çekim tahmini.** "Güncelleme zamanı gelenler" tablosundaki tahmin RealJoy'u da göstersin: bağlanması beklenen ilan sayısı × haftalar, 20 saniye aralıkla. RealJoy, öbür şirketlerle yan yana okunuyorsa toplam süreyi buna göre hesapla ve rapora yaz.
3. **Testler.**
   - eklentinin sorgu gönderme kuralları: izinli yol, yasak yol, başka alan adı reddi, POST alanlarının yalnız verilenler olması;
   - liste sayfalama ve eksik liste;
   - fiyat dökümünün ayrıştırılması ve "No";
   - adres eşlemesi, ve adı benzeyen ama adresi tutmayan evin bağlanmaması;
   - 429 kuralı;
   - eklenti bağlı değilken RealJoy'un atlanması.

   Fixture'lar ham kayıtlardan kesilir. Tam takım: `.venv\Scripts\python.exe -m pytest -q` ve `node --test tests/frontend.test.mjs`.

==================================================
ADIM 5 — Kural ve belgeler
==================================================
1. CLAUDE.md "Bilgi toplama" bölümüne kullanıcı kararını ekle (17 Kasım 2026): eklenti, sitenin kendi sekmesinden, sayfanın ziyaretçi için zaten yaptığı herkese açık sorguları (fiyat, liste) gönderebilir. Yasaklar aynen: giriş, hesap, ödeme, rezervasyon, sepet, kişisel bilgi, doğrulama çözme. "Eklenti tıklamaz, yazı yazmaz" cümlesi kalır; "form göndermez" cümlesi bu kurala göre düzeltilir.
2. Şu belgeleri güncelle: `docs/M16-TARAYICI-EKLENTISI.md`, `docs/M11-KONAKLAMA-FIYATLARI.md`, `CALISMA_MANTIGI.md` (§4 eklenti maddeleri), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`.
3. Uygulama sürümünü bir artır.
4. Dalı push et; CI sonucunu rapora yaz. main'e alma ve etiket koyma.

TESLİM
`docs/gorevler/GOREV-25/` altında `GOREV.md` (bu dosya) ve `RAPOR.md`. Raporda şunlar olsun:
- eklentinin yeni yeteneği ve kuralları;
- liste isteği ve tam listenin gelip gelmediği;
- fiyat örneği (kalemler);
- çevrimdışı eşlemede kaç ilanın bağlandığı;
- deneme kayıtları;
- gerçek veride ne değişti, yedeğin yeri;
- yeni çekim tahmini;
- kullanıcı için gece çekimi tarifi: Türkçe, adım adım, ekrandaki tam adlarla; eklentinin yeniden yüklenmesi dahil. Tarif bütün şirketleri kapsasın: Chrome ve eklenti açık kalacak, proxy, doğrulama, tahmini süre, bitince bakılacak ekranlar.

Kullanıcıya son mesajın yalnız şu olsun: "GÖREV-25 bitti, dal gorev-25-realjoy-sorgu, son commit <hash>" ve varsa tamamlanamayan adımlar.
