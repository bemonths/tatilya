GÖREV-20 — İlk videodan önce eksik verileri tamamla: kiralama şirketlerinin fiyatları, yol üzerinden mesafe ve sürüş süresi, uçak bileti ortalaması

BAĞLAM
main `7af4f1f` = `v0.20.0` (uygulama 0.20.0, şema 19). Program klasörü: `C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`.

Kanalın ilk videosu yazılmak üzere. Başlığı: "First Time on 30A? Which Town, Which Month and What a Week Costs | 30A Florida Vacation". Videonun konusu, 30A'ya ilk kez gidecek birinin üç sorusu: hangi kasabada kalmalı, hangi ayda gitmeli, bir hafta ne tutar. Kullanıcı, metin eksik veriyle değil tam veriyle yazılsın diye bu görevi istedi. Kanalın amacı ziyaretçiye karar vermesi için gereken bilginin tamamını vermektir.

Bugünkü eksikler ve sebepleri:

1. **Kiralama fiyatları.** Haftalık kira ortancaları yalnız okuyucusu (uyarlayıcı) olan şirketlerin sitelerinden geliyor (`docs/M11-KONAKLAMA-FIYATLARI.md`). Fiyatı okunamayan şirketler, Book>Direct ilan sayısıyla: 360blue.com 256, rentals.cottagerentalagency.com 82, realjoy.com 61, vrbo.com 52, 30a-beachgirls.com 48, Vacasa 21, Outdoor Shower 21. Ayrıca siteleri engelleyen 51 ilan var. 360blue o dönemde doğrudan isteğe engel sayfası verdi. realjoy.com'u eklenti okuyabiliyor ama fiyat çıkaran okuyucu yok (`docs/M16-TARAYICI-EKLENTISI.md`). Öbürleri hiç ele alınmadı.
2. **Mesafeler.** Günlük ihtiyaç mesafeleri OpenStreetMap noktalarının koordinatlarından kuş uçuşu hesaplanıyor (`docs/M13-GUNLUK-IHTIYAC.md`). Yol üzerinden mesafe ve sürüş süresi yok.
3. **Uçak.** Uçak bileti hakkında hiç veri yok.

Bu görevin kapsamı dışında kalanlar: Vrbo (pazar yeri; okumak bot korumasını aşmayı gerektirir), araç kiralama ve market fiyatları (rezervasyon ve alışveriş sitelerinden tarihe ve adrese bağlı aramalar), anlık trafik (ücretli veri), restoranların fiyat seviyesi eksikleri (kaynakta menü fiyatı yok; bu bir program eksiği değil). Bunlar kanıt paketinde "kapsam dışı" olarak açıkça yazılır ki metin bunları söylesin, uydurmasın.

Bu görevde programın hiçbir Claude adımı çalıştırılmaz ve yeni Claude adımı eklenmez. Alt ajan kullanma; işi kendin, sırayla yap.

KESİN SINIRLAR
- CLAUDE.md'deki "Bilgi toplama" ve "Veri güvenliği" kuralları aynen geçerlidir:
  - Giriş gerektiren hesaba girilmez, ücretli içerik aşılmaz, rezervasyon ve ödeme yapılmaz, kişisel form doldurulmaz.
  - Gizlenme, parmak izi sahteciliği, doğrulama çözme servisi ve IP döndürme yoktur.
  - Proxy yalnız bölge engelli alan adları içindir.
  - Aynı sitede iki istek arası en az 8 saniye.
  - Doğrulamayı yalnız kullanıcı geçer.
- Bir sitenin fiyatı ancak sitenin kendi ön yüzünün herkese açık yaptığı istekle okunabiliyorsa okunur. Site bunu engelliyorsa programın mevcut yolları kullanılır: korumalı site olarak programın kendi tarayıcısı, sayfa okuma için eklenti. Engeli aşmak için başka bir yol aranmaz; okunamayan şirket rapora yazılır.
- Eklentiyle gerçek sitelerden ilk çekimi kullanıcı başlatır (CLAUDE.md). Sen eklentiyi yalnız yerel deneme sayfalarında sınarsın.
- `data/` yalnız Adım 4'te, CLAUDE.md kuralına göre (önce tam yedek) değişir. Hiçbir kullanıcı verisi silinmez.
- Talimat dosyalarının içeriğine dokunulmaz. Housing Atlas klasöründe hiçbir dosya değiştirilmez.
- Bilgisayarda zamanlanmış görev oluşturulmaz.

==================================================
ADIM 1 — Dal
==================================================
1. Program açıksa kapanmasını bekle.
2. Güncel main'den `gorev-20-eksik-veri` dalını aç. Çalışma ağacında kullanıcının Ayarlar'dan yaptığı talimat değişikliği varsa CLAUDE.md kuralına göre ilk commit olarak ekle.

==================================================
ADIM 2 — Kiralama şirketlerinin fiyatları
==================================================
Hedef şirketler: 360blue, Cottage Rental Agency, RealJoy, 30A Beach Girls, Vacasa, Outdoor Shower. Ayrıca "siteleri engelleyen 51 ilanın" hangi şirketlere ait olduğunu bul ve aynı yolla ele al.

1. **İnceleme.** Her şirket için:
   - Önce gerçek verideki ham kayıtlara bak (salt okunur kopya, CLAUDE.md yöntemi): Book>Direct ilan bağlantıları, daha önce okunmuş ilan sayfaları, eklentinin realjoy.com kaydı.
   - Gerekirse az sayıda canlı sayfa oku: şirket başına en çok 10 sayfa, aynı sitede iki istek arası en az 8 saniye. Okuma sırası: önce doğrudan; engel varsa programın kendi tarayıcısı. Doğrulama çıkarsa kullanıcıya sohbette tek satırla haber ver ve bekle.
   - Sitenin hangi rezervasyon altyapısını kullandığını ve fiyatı hangi istekle gösterdiğini bul.
   - Altyapı mevcut uyarlayıcılardan biriyse (rescms, track, streamline, vr_router, vrp, property_quote, exceptional_stay, asmx_quote, wander, qvr), yalnız yapılandırmaya satır ekle.
2. **Yeni uyarlayıcılar.** Yeni altyapı için `studio/sources/agency_adapters.py`'ye uyarlayıcı yaz (`parse_page`, `quote`). Mevcut kurallar aynen geçerlidir:
   - Vergiler ve ücretler sitenin gösterdiği gibi alınır; fiyat sitenin söylediğinden başka türlü hesaplanmaz.
   - Müsait olmayan pencere ayrı tutulur; eşleme kuralları ve sayfa durumları aynıdır.
   - Test, ham kayıtlardan alınmış fixture'larla yapılır.
3. **Engelli siteler.** Doğrudan isteği engelleyen bir şirket, mevcut "korumalı site" yoluyla (programın kendi tarayıcısı) okunur. Uzun çekimden önce ısınma listesine girer; kullanıcı doğrulamayı bir kez geçer. realjoy.com eklentiyle okunabiliyorsa, fiyatın eklentinin okuduğu sayfadan çıkıp çıkmadığına bak. Çıkmıyorsa programın kendi tarayıcısını kullan.
4. **Okunamayanlar.** Bir şirket bu yollarla okunamıyorsa, ya da okumak bot korumasını aşmayı gerektiriyorsa, o şirket bırakılır. Rapora sebebiyle yazılır; kanıt paketinde "fiyatı okunamayan şirketler" satırında kalır.
5. **Çekim süresi.** Aylık çekim bugün yaklaşık 21 bin istek ve 7 saat 42 dakika sürüyor. Yeni şirketlerin ekleyeceği istek sayısını ve süreyi hesapla; çekim başlamadan ekranda gösterilen tahmin bunu da içersin. Süre uzuyorsa hız kuralını gevşetme.

==================================================
ADIM 3 — Yol üzerinden mesafe ve sürüş süresi; uçak bileti
==================================================
**3a. Yol mesafesi.**
1. Günlük ihtiyaç noktalarının bugün kuş uçuşu hesaplandığı her ilan–nokta çifti için yol üzerinden mesafe ve tahmini sürüş süresi ekle: en yakın büyük süpermarket, yerel market, eczane, acil servis, acil bakım merkezi ve öbür kategoriler (`docs/M13-GUNLUK-IHTIYAC.md`). Havalimanları da eklenir: VPS Destin–Fort Walton Beach ve ECP Northwest Florida Beaches.
2. "En yakın" nokta yol mesafesine göre yeniden seçilir. Kuş uçuşu değer de kalır.
3. Yöntem:
   - API anahtarı ya da ücretli hesap gerektirmesin.
   - Önerilen yol: OpenStreetMap yol ağını (programın zaten kullandığı Overpass kaynağından) bir kez indirip ham kopyasını saklamak ve en kısa yolu programın içinde yerel olarak hesaplamak.
   - Herkese açık bir yol tarifi servisi kullanacaksan, servisin kullanım kurallarına uy (toplu kullanımı yasaklayan bir demo sunucusu kullanılmaz).
4. Sürüş süresi yolların hız sınırından (`maxspeed`) ya da yol türüne göre belgelenmiş varsayılan hızlardan hesaplanır. Trafik yoktur. Etiket: "OpenStreetMap yol ağına göre, trafik hesaba katılmadan tahmini sürüş süresi". Varsayılan hızlar ayardır, koda gömülmez. "Yürüme mesafesi" denmez.
5. Sağlama: birkaç çifti bilinen değerlerle karşılaştır, örneğin 30A boyunca iki uç nokta arasındaki yol uzunluğu. Bunun için FDOT'un yol envanterindeki CR 30A uzunluğu veritabanında var. Yol mesafesi kuş uçuşundan hiçbir zaman kısa çıkmamalı; testle göster.

**3b. Uçak bileti ortalaması.**
1. ABD Ulaştırma İstatistikleri Bürosu'nun (BTS) yayımladığı havalimanı başına ortalama iç hat bilet ücretini topla: VPS ve ECP için son çeyrekler ve bir yıl önceki aynı çeyrek. BTS tablosu "Average Domestic Airline Itinerary Fares" adlı yayındır; resmî sayfasını ya da indirme dosyasını bul.
2. Değer, kaynağın tanımıyla etiketlenir: bütün kalkış noktalarından o havalimanına, dönemi söylenerek, ortalama itinerary ücreti. "Uçak bileti şu kadar" diye genelleştirilmez.
3. Kaynak erişilemezse ya da bot koruması gösterirse bırakılır ve rapora yazılır.

==================================================
ADIM 4 — Kanıt paketi, gerçek veri ve kullanıcının çekimi
==================================================
1. **Kanıt paketi ve veri özetleri.** Yeni veriler yazım zincirinin gördüğü malzemeye girmelidir (`docs/M14-KANIT-PAKETI.md`, veri özetleri):
   - mahalle başına yol mesafesi ve sürüş süresi ortancaları ile kuş uçuşu değerleri yan yana,
   - havalimanlarına yol mesafesi ve süre,
   - uçak bileti ortalaması,
   - kiralama ortancalarında hangi şirketlerin dahil olduğu ve hangilerinin olmadığı,
   - "kapsam dışı" satırı: araç kiralama, market fiyatı, anlık trafik, Vrbo.

   Kullanım notlarına yeni değerlerin nasıl söyleneceğini ekle; mevcut notların dili örnektir. Talimat dosyalarına dokunma.
2. **Gerçek veri, yalnız şu kısım.** Uygulama kapalıyken `data/` klasörünün tam yedeğini al. Sonra uygulamanın normal kullanımıyla gerçek veride şunları çalıştır:
   - yol ağı ve yol mesafeleri,
   - uçak bileti toplayıcısı.

   Bunlar resmî ve açık kaynaklardır; eklenti gerektirmez. Kiralama fiyat çekimini sen başlatma: eklenti ve doğrulama gerekebilir, süre uzun.
3. **Kullanıcının çekimi.** Kullanıcı görev bittikten sonra programda kiralama fiyatlarını ve öbür zamanı gelmiş toplayıcıları kendisi başlatacak; çekim yaklaşık bir gece sürecek. Raporun sonuna kullanıcı için Türkçe, adım adım, düğme adlarıyla kısa bir tarif yaz:
   - hangi ekranda hangi düğmeye basılacağı,
   - ısınma listesinde hangi sitelerin açılacağı ve doğrulamayı nasıl geçeceği,
   - eklentinin bağlı olması gerektiği,
   - tahmini süre,
   - bitince ekranda neye bakılacağı.

==================================================
ADIM 5 — Testler, belgeler, teslim
==================================================
1. Testler: her yeni uyarlayıcı için fixture testi; yol mesafesinin kuş uçuşundan kısa olmaması; en yakın noktanın yol mesafesine göre seçilmesi; uçak bileti toplayıcısının ayrıştırması; kanıt paketinde yeni satırlar ve "kapsam dışı" satırı. Testler canlı ağa bağlanmaz. Tam takım: `.venv\Scripts\python.exe -m pytest -q` ve `node --test tests/frontend.test.mjs`.
2. Belgeler: `docs/M11-KONAKLAMA-FIYATLARI.md`, `docs/M13-GUNLUK-IHTIYAC.md`, `docs/M14-KANIT-PAKETI.md`, `CALISMA_MANTIGI.md` (gerekiyorsa), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`. Yeni kaynak için yeni bir `docs/Mx` belgesi. Şema değişirse önce kopyada denenir (CLAUDE.md). Uygulama sürümü 0.21.0.
3. Dalı push et. main'e alma ve etiket koyma; kararı yönetici verir.

TESLİM
`docs/gorevler/GOREV-20/` altında `GOREV.md` (bu dosya) ve `RAPOR.md`. Raporda şunlar olsun:
- Her hedef şirket için: altyapısı, okuma yolu (doğrudan, korumalı site ya da okunamadı), Book>Direct ilan sayısı, okunamadıysa sebebi. Engelli 51 ilanın şirketlere dağılımı.
- Yeni çekimin tahmini istek sayısı ve süresi.
- Yol mesafesi: yöntem, varsayılan hızlar, sağlama sonuçları; mahalle başına örnek tablo (kuş uçuşu ve yol mesafesi yan yana) ve havalimanı süreleri.
- Uçak bileti: kaynak, dönem, VPS ve ECP değerleri; ya da neden alınamadığı.
- Gerçek veride ne çalıştırıldı, yedeğin yeri.
- Kullanıcı için çekim tarifi (Türkçe, düğme adlarıyla).

Kullanıcıya son mesajın yalnız şu olsun: "GÖREV-20 bitti, dal gorev-20-eksik-veri, son commit <hash>" ve varsa tamamlanamayan adımlar.
