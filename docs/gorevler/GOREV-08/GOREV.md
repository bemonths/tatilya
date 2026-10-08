GÖREV-08 — v0.10.0 yayını ve konaklama fiyatlarının kiralama şirketlerinden alınması

BAĞLAM
GÖREV-07 kabul edildi. Konaklama profili çalışıyor: her mahallede ilan sayısı, türü, oda sayısı ve kapasitesi var. Ama Book>Direct fiyatı çok az ilan için veriyor (9.189 arama satırının 12'sinde liste fiyatı; takvimlerin %64'ü gizli). Ziyaretçinin yer seçiminde en önemli sorulardan biri "burada kalmak ne kadar tutar" olduğu için bu görevin asıl işi, fiyatı ilanın kendi kiralama şirketinin sitesinden almak. Book>Direct'teki ilanların çoğu bir kiralama şirketine aittir ve ilan kaydındaki url alanı şirketin kendi ilan sayfasını gösterir. Bu sitelerin çoğu belirli tarihler için gecelik fiyat ya da toplam konaklama fiyatı (kira, temizlik ve diğer ücretler, vergiler) gösterir.

Ayrıca: v0.10.0 main'e alınacak; konaklama toplayıcısında iki küçük düzeltme yapılacak; referans tablosunda tarayıcı izni yüzünden kalan satırlar tamamlanacak.

Kullanıcı bu görev için main'e alma, etiket, gerçek veritabanını normal kullanımla güncelleme ve görevin gerektirdiği sitelere tarayıcıyla girme iznini kendi mesajında açıkça veriyor.

KESİN SINIRLAR
- data/ yalnız Adım 6'da, CLAUDE.md kuralına göre (önce tam yedek, sonra uygulamanın normal kullanımı) değişir.
- main'e yalnız Adım 1'deki fast-forward ile dokun; yalnız Adım 1'deki etiketi koy.
- Rezervasyon yapma, ödeme ya da kişisel bilgi formu doldurma, hesap açma. Fiyat sorgusu yalnız sitenin herkese açık fiyat/müsaitlik gösterimiyle yapılır.

TARAYICI VE İNSAN DOĞRULAMASI (bu görevde ve bundan sonra geçerli yöntem)
Bir site "insan olduğunuzu doğrulayın", Cloudflare kontrolü veya CAPTCHA gösterirse: sayfayı bilgisayardaki Chrome veya Edge ile, kalıcı bir tarayıcı profiliyle ve görünür pencerede aç (Playwright'in kalıcı profil desteğiyle ya da açık bir Chrome'a CDP ile bağlanarak). Kullanıcıya hangi sitede doğrulama beklendiğini söyle ve bekle. Doğrulamayı kullanıcı yapar; sen çözmeye çalışmazsın ve tarayıcıyı gizleyen ayar kullanmazsın. Kullanıcı tamamlayınca aynı profil ve oturumla devam et. Profil work/ altında (ör. work/tarayici-profili/) tutulur, repoya girmez. Bu yöntem Housing Atlas projesinde kullanıldı; bilgisayardaki C:\Users\1\source\repos\housing-atlas klasöründe (ör. atlas/sources/redfin_listings.py) örnek olarak salt okunur incelenebilir. Uygulama içi tarayıcı bir siteye girmek için izin isterse kullanıcıdan onay iste.

==================================================
ADIM 1 — v0.10.0'ı main'e al ve etiketle
==================================================
Önce origin/gorev-07-konaklama'nın son commit'i (1f4e80b) için GitHub Actions sonucunu kontrol et; başarısızsa önce düzelt, düzeltmeyi dala ekle ve bu adımı o commit'le yap. Sonra main'i bu dala git merge --ff-only ile getir ve push et; son commit'e "v0.10.0" açıklamalı etiketini koy (mesaj: "v0.10.0 — bilgi toplama ilkesi, referans tablosu tamamlama ve konaklama profili") ve push et. main CI sonucunu rapora ekle. Güncel main'den "gorev-08-konaklama-fiyat" dalını aç.

==================================================
ADIM 2 — Konaklama toplayıcısında iki düzeltme
==================================================
- İlan kaydındaki url (kiralama şirketinin ilan sayfası) ve kaynağın verdiği şirket/sahip bilgisi (varsa) veritabanına yazılsın.
- Takvimi gizli ilanlarda (hide_rate_calendar) takvim isteği yapılmasın; ön yüz de bu ilanlarda takvim göstermiyor. Atlanan ilan sayısı çekim kaydına yazılsın.
Toplayıcının sürümünü artır; testleri güncelle.
- CLAUDE.md ve CALISMA_MANTIGI.md'deki doğrulama sınırı cümlesini yukarıdaki "Tarayıcı ve insan doğrulaması" yöntemiyle değiştir (doğrulamayı kullanıcı yapar, Claude Code görünür pencerede açıp bekler ve aynı oturumla devam eder).
Ayrı commit.

==================================================
ADIM 3 — Kiralama şirketlerinden fiyat: keşif
==================================================
Gerçek veritabanındaki son konaklama çekiminin ham yanıtlarından (veya Adım 2 sonrası yeni bir geçici çekimden) bütün ilanların url alanlarını çıkar. İlanları alan adına (kiralama şirketi) ve kaynağın rez_engine değerine (TrackHs, Escapia, VRBO API vb.) göre grupla. Rapora şu tabloyu koy: alan adı, şirket adı, ilan sayısı, hangi mahallelerde kaç ilan, kullanılan rezervasyon altyapısı.

İlan sayısına göre en büyük şirketlerden başlayarak, ilanların en az üçte ikisini kapsayacak kadar şirketin sitesini incele (tek ilan sayfası örneğiyle):
- Site belirli tarihler için fiyat gösteriyor mu? Gecelik fiyat mı, toplam fiyat mı? Temizlik ücreti, hizmet ücreti, vergiler ayrı ayrı görünüyor mu?
- Fiyat sayfaya nasıl geliyor: sayfanın kendi HTML'i, bir JSON servisi (sitenin ön yüzünün çağırdığı), yoksa yalnız tarayıcıda çalışan betik mi? Aynı altyapıyı kullanan şirketlerde aynı yol mu çalışıyor?
- Minimum konaklama, giriş günü kısıtı (ör. yalnız Cumartesi) gibi kurallar görünüyor mu?
Bulguları docs/gorevler/GOREV-08/AJANS-KESFI.md'ye yaz (altyapı başına: fiyat yolu, alanlar, örnek istek ve yanıt özeti, kısıtlar).

==================================================
ADIM 4 — Kiralama şirketi fiyat toplayıcısı
==================================================
Keşifte fiyat yolu bulunan altyapılar için bir toplayıcı yaz. Yapı: genel çekirdek + altyapı başına küçük uyarlayıcılar (aynı altyapıyı kullanan şirketler aynı uyarlayıcıyı paylaşır). Hangi şirketin hangi uyarlayıcıyla okunacağı destinasyon yapılandırmasında durur.
- Girdi: son konaklama çekimindeki ilanlar (Book>Direct kimliği, url, mahalle) ve konaklama yapılandırmasındaki tarih pencereleri (Cumartesi–Cumartesi 7 gece; geçmiş pencere atlanır).
- Her ilan × pencere için saklanacaklar: müsait mi (sitenin söylediği), gecelik fiyat(lar), toplam kira, temizlik ve diğer ücretler, vergiler ve genel toplam (site hangilerini veriyorsa; vermediği alan NULL), para birimi, minimum konaklama ve giriş günü kuralları, sorgu zamanı, sorgulanan URL. Ham yanıtlar SHA-256 ile saklanır.
- Book>Direct ilanıyla şirket sitesindeki ilan, url bağlantısıyla eşlenir (kimlik bu bağlantıdır; ad benzerliğiyle eşleme yapılmaz).
- Bir şirketin sitesi doğrulama ekranı gösteriyorsa toplayıcı, "Tarayıcı ve insan doğrulaması" yöntemini kullanır: kalıcı profilli görünür tarayıcıyı açar, iş kaydını "kullanıcı doğrulaması bekleniyor" durumuna alır ve İşler panelinde hangi site için beklendiğini gösterir; doğrulama tamamlanınca aynı oturumla devam eder. Doğrulama süresi dolarsa (ör. 15 dk) o şirket atlanır ve kayda yazılır, diğerleri devam eder.
- İstekler siteyi yormayacak hızda; şirket başına sıralı. Çekim uzun sürebilir: ilerleme ve iptal doğru çalışmalı; bir şirketin hatası diğerlerini durdurmaz, çekim kaydına şirket bazında sonuç yazılır.
- Şema 11, uygulama 0.11.0; migration mevcut kurallarla.

Okuma anında hesaplanacak özet (mahalle × pencere): sorgulanan ilan sayısı, fiyatı alınabilen ilan sayısı ve payı, müsait olanların payı, 7 gecelik toplamın (ve varsa gecelik ortalamanın) ortancası ve çeyrekler aralığı, ayrıca oda sayısına göre (1–2, 3, 4, 5+ oda) ortanca. Etiket: "kiralama şirketlerinin kendi sitelerinde, şu tarihte sorgulanan fiyatlar; toplam fiyat sitenin gösterdiği ücret ve vergileri içerir/içermez" (hangisiyse).

Arayüz: Konaklama sekmesine fiyat bölümü: mahalle × pencere fiyat özeti, oda sayısına göre ortancalar, ilan ayrıntısında şirket sitesinden gelen fiyat dökümü ve kaynak bağlantısı.

Testler (fixture ve MockTransport; canlı ağ yok): her uyarlayıcı için ayrıştırma, eksik alanların NULL kalması, müsait değil yanıtı, minimum konaklama kuralı, bir şirketin hatasında diğerlerinin devam etmesi, url eşlemesi, iptal, atomik geri alma, migration ve geri alma.

Belge: docs/M11-KONAKLAMA-FIYATLARI.md (kaynaklar, uyarlayıcılar, alanların anlamı, kapsama oranı, sınırlar, video dili).

==================================================
ADIM 5 — Referans tablosunda kalan satırlar
==================================================
Bu sayfalar için "Tarayıcı ve insan doğrulaması" yöntemini kullan: uygulama içi tarayıcı site izni isterse kullanıcıdan onay iste; Cloudflare doğrulaması çıkarsa sayfayı kalıcı profilli görünür Chrome/Edge penceresinde aç ve kullanıcının doğrulamasını bekle. Şunları tamamla:
- Grayton Beach, Topsail Hill Preserve ve Deer Lake State Park giriş ücreti ve saatleri (6 "dogrulanamadi" satırı).
- 30A hız sınırları: DeFuniak Herald haberi ve varsa ilçenin karar belgesi.
- Timpoochee Trail uzunluğu: ilçenin resmî değeri (ilçe sayfaları, plan belgeleri, FDOT).
- Rosemary Beach ve WaterSound ziyaretçi otoparkı (kendi siteleri ve resmî yayınları).
Sayfa yine açılmazsa nedenini ve neyi denediğini rapora yaz.

==================================================
ADIM 6 — Gerçek ortam ve teslim
==================================================
1. Geçici klasörde canlı deneme (work/gorev-08/temp-data): konaklama toplayıcısının yeni sürümü ve kiralama şirketi fiyat toplayıcısı; süre, istek sayısı, şirket bazında sonuç; Konaklama sekmesinin fiyat bölümünün ekran görüntüsü.
2. Migration denemesi gerçek verinin kopyasında (v10 → v11).
3. Gerçek veritabanı, CLAUDE.md kuralına göre: data/ tam yedeği; uygulamayı gerçek veriyle aç; önce konaklama toplayıcısı, sonra kiralama şirketi fiyat toplayıcısı; kapat; satır sayıları, integrity_check ve foreign_key_check.
4. Belgeler: CALISMA_MANTIGI.md, README.md, docs/DEVIR/05 ve 02'nin güncel durum satırları; M10'a url ve takvim değişikliği. Tam test takımı yerelde art arda en az 3 kez geçmeli.

TESLİM
docs/gorevler/GOREV-08/ altına: GOREV.md (work/gorevler/GOREV-08.md'nin kopyası), RAPOR.md, AJANS-KESFI.md, ajanslar.csv (alan adı, şirket, ilan sayısı, mahalle dağılımı, altyapı, uyarlayıcı var mı), konaklama-fiyat-ozet.csv (gerçek veritabanından mahalle × pencere fiyat özeti ve oda sayısına göre ortancalar), güncel referans tablosunun kopyası ve ekran görüntüleri.
RAPOR.md Türkçe ve sade: her adımın sonucu, main ve etiketin konumu, CI sonuçları, test sayıları, ajans keşfinin sonucu, fiyat toplayıcısının kapsama oranı (ilanların ve mahallelerin ne kadarında fiyat alınabildi), mahalle başına fiyat özetleri, referans tablosunda tamamlanan satırlar, beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-08 bitti, dal gorev-08-konaklama-fiyat, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
