GÖREV-10 — v0.12.0 yayını, restoran fiyat seviyesinin gözden geçirilmesi, aylık fiyat pencereleri ve güncelleme zamanı göstergesi, günlük ihtiyaç ve arabasız tatil ölçüleri

BAĞLAM
GÖREV-09 kabul edildi. Gerçek Chrome kurulumu doğrulama sorununu büyük ölçüde çözdü; konaklama fiyat kapsaması 510'dan 1.066 ilana çıktı ve Bahar ile Yaz 2027'de her mahallede yeterli örnek var. Bu görevin dört işi var:

A. Restoran fiyat seviyesi zayıf: 138 restorandan yalnız 33'ünde var. Rosemary Beach'te 12 restoranın hiçbirinde yok; oysa Rosemary kanalın en çok izlenecek mahallelerinden biri. Menülerin çoğu sitede duruyor ama ayrıştırıcı ana yemekleri bulamıyor. Bu menüleri tek tek okuyup gözden geçireceksin.
B. Kanal planında "Rosemary Beach in October" gibi ay ay videolar ve kendi topladığımız fiyat geçmişinden videolar var. Bunun için fiyatın ay ay ve düzenli aralıklarla kaydedilmesi gerekiyor; geçmiş sonradan toplanamaz. Sabit 5 pencere yerine kayan 12 aylık pencereye geçilecek. Çekimler kendiliğinden yapılmayacak (kullanıcının kararı: zamanlanmış görev yok); uygulama hangi toplayıcının güncelleme zamanının geldiğini ana ekranda gösterecek, kullanıcı gerekirse tek düğmeyle başlatacak.
C. "Arabaya ihtiyaç var mı" ve "markete ne kadar uzak" soruları için hiç verimiz yok. Market, eczane, acil sağlık ve bisiklet kiralama noktaları toplanacak; kiralık evlerden bu noktalara kuş uçuşu mesafe hesaplanıp mahalle başına özetlenecek. Hesap küçük; asıl iş noktaları doğru toplamak.
D. Küçük işler: v0.12.0 main'e alınacak; realjoy yeni tarayıcıyla bir kez denenecek.

Kullanıcı bu görev için main'e alma, etiket, gerçek veritabanını normal kullanımla güncelleme ve görevin gerektirdiği sitelere tarayıcıyla girme iznini kendi mesajında açıkça veriyor. Bilgisayarda zamanlanmış görev (Windows Görev Zamanlayıcı vb.) oluşturulmaz. İnsan doğrulamasını kullanıcı yapacak.

KESİN SINIRLAR
- data/ yalnız Adım 6'da, CLAUDE.md kuralına göre (önce tam yedek, sonra uygulamanın normal kullanımı) değişir.
- Windows Görev Zamanlayıcı'da ya da başka bir yerde zamanlanmış görev oluşturma.
- main'e yalnız Adım 1'deki fast-forward ile dokun; yalnız Adım 1'deki etiketi koy.
- Rezervasyon, ödeme, kişisel bilgi formu, hesap açma ve giriş yok. Proxy, VPN, IP değiştirme, gizlenme eklentisi, parmak izi sahteciliği, CAPTCHA çözme servisi yok. Tarayıcı CLAUDE.md'deki kuruluma göre kullanılır.
- Menüden okunan her değer menüde yazdığı gibidir; menüde fiyatı olmayan kaleme fiyat yazılmaz, tahmin yok.

==================================================
ADIM 1 — v0.12.0'ı main'e al ve etiketle
==================================================
Önce origin/gorev-09-kapsama-restoran'ın son commit'i (fdd59f6) için GitHub Actions sonucunu kontrol et; başarısızsa önce düzelt, düzeltmeyi dala ekle ve bu adımı o commit'le yap. Sonra main'i bu dala git merge --ff-only ile getir ve push et; son commit'e "v0.12.0" açıklamalı etiketini koy (mesaj: "v0.12.0 — konaklama fiyat kapsaması, gerçek tarayıcı kurulumu ve restoran bilgileri") ve push et. main ve etiket CI sonucunu rapora ekle. Güncel main'den "gorev-10-aylik-gunluk" dalını aç.

==================================================
ADIM 2 — Restoran fiyat seviyesi: elle gözden geçirme
==================================================
Yönetici kararları (GÖREV-09 raporundaki sorulara):
- Ana öğün menüsü önceliği akşam > öğle > genel > brunch > kahvaltı olarak kalır.
- order.online ısınmada bir kez daha denenir; doğrulama geçmezse üç restoran açık kalır.

2a. Seviyesi hesaplanmamış her restoranı tek tek ele al (sosyal medya sayfası, sezon için kapalı, başka işletme ve sitesi olmayanlar hariç):
- "Ana yemek fiyatı yok", "menü okunamadı" ve "5'ten az ana yemek" olanlarda menüyü kendin oku. Önce ayrıştırıcının neden kaçırdığına bak: bölüm başlığı sınıflama tablosunda yoksa (ör. "From the Sea", "Plates", "Mains", "Dinner Entrées" türevleri) tabloyu düzelt; JavaScript ile çizilen menü platformlarında (Popmenu, Toast, BentoBox, SinglePlatform vb.) tarayıcının çizdiği sayfayı oku. Bu da olmazsa menüdeki ana yemekleri gözden geçirme dosyasına (thirty_a_menu_readings.csv) yaz: bölüm başlığı menüde yazdığı gibi, kalem adı, fiyat metni, menü url'si, ham kopyanın SHA-256'sı, yöntem "elle okundu" (görüntüyse "görüntüden okundu").
- "Menü bulunamadı" olanlarda menüyü sitenin alt sayfalarında, PDF'lerde ve siteden bağlantı verilen menü/sipariş platformlarında ara; bulursan menü bağlantısını gözden geçirilmiş site dosyasına (thirty_a_restaurant_sites.csv) ekle ve toplayıcı okusun.
- "Ulaşılamadı" olanları tarayıcıyla yeniden dene.

2b. Kurallar:
- Ek malzeme, ekstra, topping, sos, yan ürün ve "add …", "+ …", "sub …", "side of …" kalemleri hiçbir zaman ana yemek sayılmaz. Şu an ana yemek sayılan ve $8'ın altında kalan bütün kalemleri tek tek kontrol et; yanlış sınıflananları düzelt. Bu düzeltmenin hangi restoranın ortancasını ve seviyesini değiştirdiğini rapora yaz.
- Tapas ya da küçük tabak menüsü olup ana yemek bölümü olmayan restoranlarda fiyat seviyesi hesaplanmaz; küçük tabakların ortancası ayrı alanda, "küçük tabak ortancası" etiketiyle verilir.
- Kişi başı sabit fiyatlı menüler (prix fixe, tasting menu) ana yemek ortancasına karışmaz; ayrı alanda "sabit menü fiyatı" diye saklanır.
- Kahve, tatlı, dondurma ve içecek yerlerinde ana yemek yoksa seviye hesaplanmaz; neden "ana yemek sunmuyor" diye yazılır.

2c. Hedef: sitesinde fiyatlı ana yemek menüsü yayımlayan her restoranın seviyesi olsun. Seviyesi olmayan her restoran için tek satırlık neden kalsın. Rapora Rosemary Beach, Seaside, WaterColor, Alys Beach ve Grayton Beach restoranlarını tek tek yaz (seviye ya da neden).

==================================================
ADIM 3 — Aylık fiyat pencereleri ve güncelleme zamanı göstergesi
==================================================
3a. Pencere kuralı (destinasyon yapılandırması; varsayım, kaynak gerçeği değil): çekim tarihinden sonraki 12 ayın her biri için o ayın 15'ini içeren Cumartesi–Cumartesi haftası (7 gece). Başlangıcı çekim tarihine 21 günden yakın olan pencere atlanır ve yerine 13. ay eklenir; böylece her çekimde 12 pencere olur. Etiket ay adıyla ("Temmuz 2027 · 10–17 Temmuz"). Book>Direct konaklama toplayıcısı ve kiralama şirketi toplayıcısı aynı kuralı kullanır. Eski çekimlerin pencereleri olduğu gibi kalır.

3b. Özet ve arayüz: fiyat tablosu ay sütunlarıyla; her pencerede çekim tarihi ile pencere başlangıcı arasındaki gün sayısı görünür. Mevsim grupları okuma anında hesaplanır (Aralık–Şubat kış, Mart–Mayıs ilkbahar, Haziran–Ağustos yaz, Eylül–Kasım sonbahar) ve "bizim gruplamamız" diye etiketlenir.

3c. Aynı hafta için çekimler arası karşılaştırma: aynı ilan ve aynı pencere iki farklı çekimde fiyatlıysa, mahalle bazında eşleşen ilanların fiyat değişiminin ortancası okuma anında hesaplanır. Etiket: "aynı evlerin aynı hafta için <tarih1> ve <tarih2> tarihlerinde sorgulanan fiyatları; bizim hesabımız". Eşleşen ilan sayısı her zaman yazılır. Bu, kanalın tarihsel veri videolarının temelidir.

3d. Güncelleme zamanı göstergesi (zamanlanmış görev yok):
- Destinasyon yapılandırmasında toplayıcı başına önerilen yenileme aralığı: Book>Direct konaklama ve kiralama şirketi fiyatları 1 ay; restoran dizini ve işletme siteleri 3 ay; diğerleri için aralık tanımlanmaz.
- Uygulamanın ana ekranında "Güncelleme zamanı gelenler" bölümü: her toplayıcının son başarılı çekim tarihi, önerilen aralık ve zamanı gelip gelmediği; zamanı gelenler belirgin görünür. Altında tek bir "Zamanı gelenleri başlat" düğmesi: zamanı gelen toplayıcıları uygun sırayla (konaklama → kiralama şirketleri; restoran dizini → işletme siteleri) normal iş akışıyla başlatır, tahmini süreyi gösterir ve iptal edilebilir.
- Düğmeyle başlatılan toplu çalıştırmadan önce uygulama kendi veritabanı yedeğini alır (SQLite backup API, data/backups altında, "toplu" önekiyle; bu türden son 6 yedek saklanır, daha eskileri uygulama siler).
- Doğrulama gerekirse mevcut kural geçerli (ısınma, sona bırakma, 15 dakika bekleme).
- CLAUDE.md "Gerçek veriyi güncelleme kuralı"na ekle: "Kullanıcı, uygulamadaki 'Zamanı gelenleri başlat' düğmesiyle zamanı gelen toplayıcıları kendisi başlatabilir; bu uygulamanın normal kullanımıdır ve öncesinde uygulama kendi yedeğini alır. Claude Code gerçek veriyi yine yalnız görev metni açıkça istediğinde değiştirir. Bilgisayarda zamanlanmış görev oluşturulmaz (kullanıcı kararı, 9 Ekim 2026)." README'ye Türkçe olarak bu bölümün ne gösterdiğini ve düğmenin ne yaptığını yaz.

3e. Testler: pencere kuralı (21 gün sınırı, 13. ay, ay sonu ve yıl geçişi), iki çekim arası eşleşmiş karşılaştırma, zamanı gelme hesabı, toplu başlatmanın sırası ve iptali, yedek alma ve son 6'nın saklanması. Belge: docs/M11-KONAKLAMA-FIYATLARI.md'ye pencere kuralı ve karşılaştırma; güncelleme göstergesi CALISMA_MANTIGI.md'ye.

==================================================
ADIM 4 — Günlük ihtiyaç ve arabasız tatil ölçüleri
==================================================
4a. Kaynak: OpenStreetMap, Overpass API üzerinden (genel bir toplayıcı; bölge sınırı ve kategoriler destinasyon yapılandırmasından). Kategoriler: süpermarket ve market (shop=supermarket, shop=grocery), küçük market (shop=convenience, shop=general), eczane (amenity=pharmacy, healthcare=pharmacy), acil sağlık (amenity=hospital, healthcare=urgent_care, acil hizmet veren amenity=clinic), bisiklet kiralama (amenity=bicycle_rental, kiralama yapan shop=bicycle). Ham yanıtlar SHA-256 ile saklanır; Overpass'ın kullanım kurallarına uyulur (az ve küçük sorgu). Atıf arayüzde ve belgede: "© OpenStreetMap katkıcıları, ODbL". Veritabanı yayımlanmaz.

4b. Süpermarketler için çapraz kontrol: bölgede mağazası olabilecek zincirlerin (Publix, Winn-Dixie, Walmart, Target, Whole Foods, The Fresh Market, Trader Joe's, Aldi) kendi mağaza bulucularına bak. OpenStreetMap'te olmayan bir mağaza varsa "zincirin kendi sitesi" kaynağıyla ekle; OpenStreetMap'te olup zincirin sitesinde kapalı görünenleri rapora yaz.

4c. Ölçüler (hepsi kuş uçuşu, mil ve metre; "kuş uçuşu" etiketiyle; okuma anında hesaplanabilir, ayrı tablo gerekmez):
- Son konaklama çekimindeki her ilan için: en yakın süpermarket, en yakın küçük market, en yakın eczane, en yakın acil sağlık noktası, en yakın bisiklet kiralama, en yakın halka açık plaj erişimi (ilçenin listesindeki 53 erişim) mesafesi.
- Mahalle başına (ilanın mahallesi Book>Direct filtresinden): bu mesafelerin ortancası ve 1 mil içinde kalan ilanların payı. Restoranlar için koordinat üretilmez; mahalle başına restoran sayısı mevcut dizinden gelir.
- Plaj erişimi notu: ölçü yalnız ilçenin halka açık erişim listesine göredir; Seaside, WaterColor, Alys, Rosemary gibi toplulukların kendi misafirlerine açık özel erişimleri dahil değildir. Bu not etiketin parçasıdır.

4d. Arayüz: Mahalleler sekmesinde mahalle başına günlük ihtiyaç tablosu (noktaların listesiyle). Belge: docs/M13-GUNLUK-IHTIYAC.md (kaynaklar, kategoriler, çapraz kontrol, ölçülerin anlamı, sınırlar). Video dili: "OpenStreetMap'e göre, kuş uçuşu"; "markete yürüme mesafesi" denmez, çünkü yol üzerinden mesafe hesaplanmadı. Testler: Overpass yanıtı ayrıştırma, kategori eşlemesi, mesafe hesabı, mahalle ortancaları, eksik koordinat.

==================================================
ADIM 5 — Kiralama şirketlerinde küçük işler
==================================================
- realjoy.com (61 ilan): yeni tarayıcıyla bir kez keşif. Açılırsa ya da kullanıcı ısınmada doğrularsa altyapısına bak; mevcut bir uyarlayıcıya uyuyorsa yapılandır, uymuyorsa rapora yaz.
- 360blue: gerçek çekimden hemen önce bir kez bak; engel sürüyorsa bırak.
- Oversee'nin düzeltilmiş liste okuması Adım 6'daki aylık çekimde kullanılır; kaç ilanın yeni eşleştiğini yaz.

==================================================
ADIM 6 — Gerçek ortam ve teslim
==================================================
1. Geçici klasörde canlı deneme: restoran siteleri (gözden geçirme dosyalarıyla), OpenStreetMap, konaklama ve kiralama şirketleri 12 pencereyle (yük binmesin diye bu denemede birkaç şirketle sınırlı tutulabilir). Süre ve istek sayıları; ekran görüntüleri.
2. Şema değişirse migration denemesi gerçek verinin kopyasında.
3. Gerçek veritabanı, CLAUDE.md kuralına göre: data/ tam yedeği; uygulamayı gerçek veriyle aç; ısınma (order.online ve realjoy dahil, kullanıcıya tek liste); sırayla restoran dizini, işletme siteleri, OpenStreetMap ve günlük ihtiyaç ölçüleri; uygulamayı kapat.
4. Uygulamayı gerçek veriyle yeniden aç; ana ekrandaki "Güncelleme zamanı gelenler" bölümünün doğru göründüğünü kontrol et (ekran görüntüsü). "Zamanı gelenleri başlat" düğmesiyle konaklama ve kiralama şirketi fiyatlarını başlat; bu, 12 pencereli ilk aylık anlık görüntüdür (360blue'ya hemen önce bir kez bak). Bittiğinde uygulamanın kendi yedeğinin alındığını ve iki toplayıcının tamamlandığını kontrol et; uygulamayı kapat. Satır sayıları, integrity_check ve foreign_key_check.
5. Belgeler: CALISMA_MANTIGI.md, README.md, docs/DEVIR/05 ve 02'nin güncel durum satırları, M11, M12, M13. Tam test takımı yerelde art arda en az 3 kez geçmeli.

TESLİM
docs/gorevler/GOREV-10/ altına: GOREV.md (work/gorevler/GOREV-10.md'nin kopyası), RAPOR.md, restoranlar.csv (güncel), restoran-seviye-once-sonra.csv (restoran, önceki seviye ve neden, yeni seviye ve neden, yöntem), restoran-mahalle-ozet.csv, konaklama-fiyat-ozet.csv (12 ay), gunluk-ihtiyac-mahalle.csv, gunluk-ihtiyac-noktalar.csv (nokta, kategori, kaynak, koordinat) ve ekran görüntüleri.
RAPOR.md Türkçe ve sade: her adımın sonucu, main ve etiketin konumu, CI sonuçları, test sayıları, restoran seviyesinin önce/sonra sayıları ve mahalle bazında durumu, ek malzeme düzeltmesinin etkisi, pencere kuralı ve ilk aylık anlık görüntünün sonucu (mahalle × ay fiyatlı ilan sayıları ve ortancalar), güncelleme göstergesinin ayarı ve süresi, günlük ihtiyaç noktalarının sayıları ve çapraz kontrol sonucu, mahalle başına mesafe ölçüleri, realjoy ve 360blue sonucu, gerçek veritabanının öncesi/sonrası, beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-10 bitti, dal gorev-10-aylik-gunluk, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
