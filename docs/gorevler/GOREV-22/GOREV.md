GÖREV-22 — Kiralama fiyatlarının eksiklerini kapat: bölge engeli denemesi (ABD proxy'si), RealJoy okuyucusu, 30A Beach Girls

BAĞLAM
30A Studio, Mucahit'in YouTube kanalı için veri toplayıp video metni yazdıran yerel programdır. Program klasörü: `C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`.

Durum:
- main `57088be` = `v0.21.0`.
- GÖREV-21 (dal `gorev-21-katmanlar`, son commit `2848c6f`, uygulama 0.22.0, şema 21) yönetici tarafından kabul edildi.
- Program artık iki katmanlı: Sol menü → Veri, Konu bankası, Kanal, Videolar; video açılınca o videonun adımları (`docs/M21-IS-AKISI-KATMANLAR.md`, CLAUDE.md "Katmanlar").

Kanalın ilk videosu, 30A'ya ilk kez gidecek birinin üç sorusunu cevaplıyor: hangi kasaba, hangi ay, bir hafta ne tutar. "Bir hafta ne tutar" sorusu kiralama fiyatlarına dayanıyor.

GÖREV-20'de (rapor: `docs/gorevler/GOREV-20/RAPOR.md`, bölüm 1) altı kiralama şirketinin hiçbiri okunabilir hale gelmedi. Book>Direct'teki 2.389 ilanın 513'ü bu şirketlerde. Yöneticinin değerlendirmesi: bu şirketlerin bir kısmında görülen engel büyük olasılıkla **bölge engeli**. İnceleme Türkiye'deki bilgisayardan yapıldı, ve:
- **Vacasa** (vacasa.com 21 ilan; wyndhamvacationrentals.com 14 ilanın bağlantısı da buraya gidiyor) açıkça "ülkenizden erişim engelli" diyor (CloudFront).
- **360 Blue** (360blue.com, 256 ilan, en büyük eksik) Cloudflare'in "Sorry, you have been blocked" sayfasını verdi. Bu, ülkeye göre konmuş bir kural da olabilir.
- **Cottage Rental Agency** (92 ilan): ana alan adı sandestin.com'da "403 Access denied" sayfasına yönleniyor. Kiralama alan adının DNS kaydı yok.
- **Outdoor Shower** (outdoorshower30a.com, 21 ilan) hiç yanıt vermedi. Bazı siteler ABD dışından gelen bağlantıyı cevapsız bırakır.

Kullanıcının kendi ABD proxy'si bu iş için var (GÖREV-16, `docs/M18-ABD-PROXY-BOLGE-ENGELI.md`). Kural değişmiyor:
- Proxy yalnız bölge engeli içindir; bot korumasını, hız sınırını ya da yasağı aşmak için kullanılmaz.
- Yalnız bölge engelli listesindeki alan adları (`region_blocked_hosts`) proxy'den gider.

Bu görevde bir sitenin bölge engelli olup olmadığı ölçülür. Yalnız bölge engelli çıkanlar listeye girer.

İki şirket daha:
- **RealJoy** (realjoy.com, 61 ilan): Cloudflare doğrulaması istiyor. Bu bot korumasıdır, bölge engeli değildir; proxy kullanılmaz. Kullanıcının Chrome'undaki eklenti siteyi okuyabiliyor. GÖREV-20, eklentinin deneme listesine RealJoy'un bir ilan sayfasını ekledi. Kullanıcıdan bu denemeyi çalıştırması istendi; çalıştırıp çalıştırmadığı bilinmiyor.
- **30A Beach Girls** (30a-beachgirls.com, 48 ilan): site okunuyor (AvantStay), ama sokak adresi vermediği ve koordinatı yaklaşık 100 m'ye yuvarladığı için ilanlarla eşlenemiyor. Yöneticinin kararı: ad benzerliğiyle eşleme yapılmaz; yanlış eşleşme riski var. Bunun yerine şirketin kendi evleri, Book>Direct ilanlarına bağlanmadan, şirketin kendi envanteri olarak fiyatlanır (Adım 5).

Bu görevde programın Claude adımları çalıştırılmaz. Alt ajan kullanma; işi kendin, sırayla yap.

KESİN SINIRLAR
- CLAUDE.md'deki "Bilgi toplama" ve "Veri güvenliği" kuralları aynen geçerlidir:
  - Giriş, ödeme, rezervasyon ve kişisel form yok.
  - Gizlenme, parmak izi sahteciliği, doğrulama çözme servisi ve IP döndürme yok.
  - Aynı sitede iki istek arası en az 8 saniye.
  - Doğrulamayı yalnız kullanıcı geçer.
- Proxy yalnız Adım 2'deki ölçüm ve bölge engelli çıkan alan adları için kullanılır. Doğrulama sayfası ya da bot engeli gösteren bir site, proxy'den de aynı engeli veriyorsa bölge engelli sayılmaz ve proxy ile okunmaz.
- Proxy parolası Windows Kimlik Bilgisi Yöneticisi'ndedir. Programın kendi proxy modülü kullanılır. Parola ve proxy bilgileri dosyaya, günlüğe, rapora ve sohbete yazılmaz; kullanıcıya sorulmaz.
- Eklentiyle gerçek sitelerden okumayı kullanıcı başlatır; sen eklentiyi yalnız yerel deneme sayfalarında sınarsın.
- `data/` yalnız Adım 6'da, CLAUDE.md kuralına göre değişir (önce tam yedek). Kiralama fiyat çekimini sen başlatma; onu kullanıcı başlatacak.
- Talimat dosyalarının içeriğine dokunulmaz. Housing Atlas ve Rota Stüdyo depolarında hiçbir dosya değiştirilmez. Zamanlanmış görev oluşturulmaz.

==================================================
ADIM 1 — main ve dal
==================================================
1. Program açıksa kapanmasını bekle.
2. Kullanıcının mesajı izin veriyorsa `gorev-21-katmanlar` dalını main'e fast-forward ile al ve `v0.22.0` açıklamalı etiketini koy; ikisini push et. Fast-forward olmuyorsa dur ve sor.
3. Güncel main'den `gorev-22-kiralama` dalını aç. Kullanıcının Kanal ekranından yaptığı talimat değişikliği varsa CLAUDE.md kuralına göre ilk commit olarak ekle.

==================================================
ADIM 2 — Bölge engeli ölçümü
==================================================
Ölçülecek alan adları: `360blue.com`, `vacasa.com`, `wyndhamvacationrentals.com`, `cottagerentalagency.com`, `rentals.cottagerentalagency.com`, `sandestin.com`, `outdoorshower30a.com`. realjoy.com ölçülmez (bot koruması).

1. Her alan adı için aynı sayfaya (ana sayfa ya da Book>Direct'teki bir ilan bağlantısı) iki istek yap:
   - biri doğrudan,
   - biri programın proxy modülüyle, proxy üzerinden doğrudan istek olarak.

   Aradaki süre en az 8 saniye. Bu ölçüm için alan adı başına en çok 3 istek. Programın kendi tarayıcısı bu adımda kullanılmaz.
2. İki yanıtın ham kopyası saklanır (`work/gorev-22/ham/`).
3. Sınıflandırma:
   - **Bölge engeli:** doğrudan istek ülke engeli, ret ya da zaman aşımı alıyor; proxy üzerinden normal içerik geliyor (200, sitenin gerçek sayfası).
   - **Bölge engeli değil:** proxy üzerinden de aynı engel, doğrulama sayfası ya da ret geliyor. Site bırakılır.
   - **Site yok:** DNS kaydı yok ya da iki yoldan da kalıcı hata geliyor. Bir ABD'li için de durum aynıysa şirketin güncel sitesi olup olmadığına bak: Book>Direct'teki şirket adı, sandestin.com'un yönlendirdiği adres. Bulursan aynı ölçümü o adresle yap.
4. Bölge engelli çıkan alan adları, programın normal arayüzüyle bölge engelli listeye eklenir: **Sol menü → Veri → Okuma denemeleri** → bölge engelli alan adları. Bu ekleme gerçek veritabanını değiştirir; Adım 6'daki yedekten sonra yapılır. Her ekleme için kanıt rapora yazılır: iki yanıtın durum kodu, sayfa başlığı, ham kopyanın adı.

==================================================
ADIM 3 — Bölge engelli çıkan şirketlerin okuyucuları
==================================================
1. Bölge engelli çıkan her şirket için GÖREV-20 Adım 2'deki incelemeyi proxy üzerinden yap:
   - şirket başına en çok 10 sayfa, iki istek arası en az 8 saniye;
   - rezervasyon altyapısı ve fiyatı veren istek bulunur;
   - mevcut uyarlayıcılardan birine uyuyorsa (rescms, track, streamline, vr_router, vrp, property_quote, exceptional_stay, asmx_quote, wander, qvr) yalnız yapılandırmaya satır eklenir; uymuyorsa `studio/sources/agency_adapters.py`'ye yeni uyarlayıcı yazılır.
2. Kurallar aynen geçerlidir (`docs/M11-KONAKLAMA-FIYATLARI.md`):
   - vergi ve ücretler sitenin gösterdiği gibi alınır;
   - eşleme sokak adresi ya da 15 m içinde konumla yapılır, ad tek başına ölçüt değildir;
   - müsait olmayan pencere ayrı tutulur.
3. Okuma sırası, bölge engelli alan adları için programda zaten tanımlı olandır: proxy üzerinden doğrudan istek → programın kendi tarayıcısı proxy'yle → atla ve kaydet. Eklenti bu alan adları için kullanılmaz.
4. Proxy üzerinden doğrulama çıkarsa o şirket korumalı site gibi ısınma listesine girer ve doğrulamayı kullanıcı geçer.
5. Testler, ham kopyalardan alınmış fixture'larla yapılır.

==================================================
ADIM 4 — RealJoy
==================================================
1. Eklentinin deneme kayıtlarına bak: kullanıcı 16 Kasım 2026 akşamından sonra eklenti denemesini çalıştırdıysa, RealJoy'un bir ilan sayfasının ham kaydı vardır.
2. **Kayıt yoksa** kullanıcıya sohbette şu tarifi ver ve bekle: "Programı açın. Sol menü → Veri → Okuma denemeleri → Eklentinin deneme okuması → Sorunlu sitelerden birer sayfa dene. Chrome'da açılan sayfada doğrulama çıkarsa kutuyu işaretleyin. Bitince bana 'tamam' yazın." Düğmenin adı ekranda farklıysa ekrandaki tam adı yaz. Kullanıcı 'tamam' deyince kaydı oku.
3. Kayıttan fiyatın nasıl geldiğini bul.
   - Fiyat, eklentinin okuyabildiği bir sayfa yüklemesiyle alınabiliyorsa okuyucuyu yaz. Bu, sayfanın kendisi ya da sitenin herkese açık bir GET adresi olabilir; eklenti tıklamaz ve form doldurmaz. Çekimde RealJoy sayfaları eklentiyle okunur, eklenti bağlı değilse programın kendi tarayıcısıyla.
   - Fiyat yalnız eklentinin yapamadığı bir istekle geliyorsa (sayfada tıklama ya da form göndermek gerekiyorsa) okuyucuyu yazma; sebebini rapora yaz.
   - Site 30A ilan listesinde sokak adresi ve koordinat veriyor (GÖREV-20 raporu); eşleme mevcut kurallarla yapılır.

==================================================
ADIM 5 — 30A Beach Girls: şirketin kendi envanteri
==================================================
1. Şirketin sitesindeki evler, Book>Direct ilanlarına eşlenmeden, ayrı bir "şirketin kendi envanteri" olarak fiyatlanır. Programda bunun bir örneği varsa (ör. tek mahalleye ait bir şirketin kendi sitesinden okunan evler) aynı yolu kullan; yoksa en sade biçimde kur ve `docs/M11-KONAKLAMA-FIYATLARI.md`'ye yaz.
2. **Mahalle**, yalnız sitenin her ev için kendi söylediği bölge ya da mahalle adından alınır. Koordinattan mahalle çıkarılmaz (CLAUDE.md "Veri dili"). Bölge adı vermeyen ev, mahalle ortancalarına girmez; 30A geneli sayımında "mahallesi belirtilmemiş" diye ayrı durur.
3. Aynı ev hem Book>Direct'te fiyatlı hem bu envanterde varsa iki kez sayılmaz. GÖREV-20'ye göre şirketin Book>Direct ilanlarının hiçbiri fiyatlı değil; yine de testle göster.
4. Kanıt paketinde bu fiyatlar kaynağıyla ayrı görünür: "şirketin kendi sitesindeki evler; Book>Direct ilanlarına bağlanmadı". Kapsanan şirketler satırına (`lodging_coverage`) eklenir.

==================================================
ADIM 6 — Gerçek veri, kullanıcının çekimi, testler, belgeler
==================================================
1. **Yedek.** Uygulama kapalıyken `data/` klasörünün tam yedeğini al.
2. **Gerçek veride yapılacaklar.** Program gerçek veriyle normal biçimde açılır; yalnız şunlar yapılır:
   - Adım 2'de bölge engelli çıkan alan adlarının listeye eklenmesi;
   - yeni şirketlerin yapılandırmaya girmesi (program bunu kendi yapılandırma yoluyla yapıyorsa).

   Kiralama fiyat çekimi başlatılmaz.
3. **Çekim süresi.** Yeni şirketlerin ekleyeceği istek sayısını ve süreyi hesapla. "Güncelleme zamanı gelenler" tablosundaki tahmin bunu göstersin.
4. **Kullanıcı için çekim tarifi.** Raporun sonuna Türkçe, adım adım, ekrandaki tam adlarla yaz. GÖREV-21'den sonraki menüye göre: Sol menü → Veri → Kaynaklar → Güncelleme zamanı gelenler → Zamanı gelenleri başlat. Tarif şunları söylesin:
   - eklentinin bağlı olması gerektiği ve bunun nereden görüleceği;
   - ısınma listesinde hangi sitelerin açılacağı;
   - doğrulamanın nasıl geçileceği;
   - tahmini süre;
   - bitince hangi ekranda neye bakılacağı.
5. **Testler.** Her yeni uyarlayıcı için fixture testi; bölge engeli sınıflandırması (üç durum); bölge engelli alan adının proxy'den, öbürlerinin doğrudan gitmesi; 30A Beach Girls'te bölge adı olmayan evin mahalle ortancasına girmemesi ve evlerin iki kez sayılmaması; kanıt paketinde yeni şirketler. Testler canlı ağa bağlanmaz. Tam takım: `.venv\Scripts\python.exe -m pytest -q` ve `node --test tests/frontend.test.mjs`.
6. **Belgeler.** `docs/M11-KONAKLAMA-FIYATLARI.md`, `docs/M18-ABD-PROXY-BOLGE-ENGELI.md`, `docs/M14-KANIT-PAKETI.md`, `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`. Uygulama sürümü 0.23.0.
7. Dalı push et. main'e alma ve etiket koyma; kararı yönetici verir.

TESLİM
`docs/gorevler/GOREV-22/` altında `GOREV.md` (bu dosya) ve `RAPOR.md`. Raporda şunlar olsun:
- **Bölge engeli ölçümü tablosu:** alan adı; doğrudan ve proxy yanıtı (durum kodu, sayfa başlığı); sınıf; listeye eklendi mi.
- **Şirket tablosu:** şirket, ilan sayısı, altyapı, okuma yolu, sonuç ya da okunamama sebebi. Bütün eksikler sonunda nerede duruyor: kaç ilan fiyatlanabilir oldu, kaçı hâlâ eksik.
- **RealJoy:** kayıt bulundu mu, okuyucu yazıldı mı.
- **30A Beach Girls:** kaç ev, kaçında bölge adı var, mahallelere dağılımı.
- **Çekim:** yeni tahmini istek sayısı ve süre.
- **Gerçek veri:** ne değişti, yedeğin yeri.
- **Kullanıcı için çekim tarifi.**

Kullanıcıya son mesajın yalnız şu olsun: "GÖREV-22 bitti, dal gorev-22-kiralama, son commit <hash>" ve varsa tamamlanamayan adımlar.
