GÖREV-05 — Eşleme v3 ve iklim paketi (hava normalleri, deniz suyu sıcaklığı, kasırga geçmişi)

BAĞLAM
GÖREV-04 kabul edildi. Eşleme v2'de ilçe alt bölüm verisi yalnız poligonun içindeki erişimlere uygulandığı için 53 erişimin yalnız 6'sında kullanılabildi; plaj erişimleri kamuya ait yol uçlarında, alt bölüm sınırının birkaç metre dışında duruyor. Sonuçta v1'de "Seaside" yazılan 10 erişimin 9'u hâlâ Seaside. Bu görevde eşleme kuralı yönetici kararıyla genişletilip v3 olarak kilitlenecek. Ardından ilk videonun "ne zaman gitmeli" sorusu için iklim paketi kurulacak.

Kullanıcı bu görev için main'e alma ve gerçek veritabanını normal kullanımla güncelleme iznini kendi mesajında açıkça veriyor.

KESİN SINIRLAR
- data/ yalnız Adım 6'da, CLAUDE.md'deki kurala göre (önce tam yedek, sonra uygulamanın normal kullanımı) değişir.
- main'e yalnız Adım 1'deki fast-forward ile dokun. Etiket oluşturma.
- Mevcut dört toplayıcının (plaj, hava tahmini, restoran, mahalle) davranışını değiştirme.

==================================================
ADIM 1 — main'e alma ve yeni dal
==================================================
main'i origin/gorev-04-esleme-v2 (a7e38f2) konumuna git merge --ff-only ile getir ve push et. Fast-forward mümkün değilse dur ve rapora yaz. main CI sonucunu rapora ekle. Güncel main'den "gorev-05-iklim" dalını aç.

==================================================
ADIM 2 — Eşleme v3 (yönetici kararları)
==================================================
Yöntem sırası şöyle olacak:
1. resmi_rehber (9 erişim, değişmez).
2. ilce_alt_bolum: nokta, ad tablosunda bir mahalleye bağlanan bir alt bölüm poligonunun içinde.
3. ilce_alt_bolum_yakin (yeni): nokta böyle bir poligonun içinde değil ama ad tablosunda bir mahalleye bağlanan en yakın alt bölüm poligonu 30 metre veya daha yakın. Noktanın ad tablosunda olmayan bir poligonun (INFORMATION ONLY, yasal tanım, site adı vb.) içinde olması bu kuralı engellemez. 30 m içinde farklı mahallelere bağlanan birden fazla poligon varsa bu yöntem sonuç vermez ve satır notunda yazılır. 30–75 m arasındaki poligonlar kullanılmaz.
4. komsu_tutarliligi (yeni): ilk üç yöntemle atanamayan bir erişim için, boylam sırasına göre batısındaki en yakın ve doğusundaki en yakın "kaynağa dayalı" erişim (yöntemi 1, 2 veya 3 olan) aynı mahalleye atanmışsa, erişim o mahalleye atanır. Kıyı boyunca mahallelerin kesintisiz olduğu varsayımına dayanır; notta iki komşunun adı yazılır.
5. turetim_en_yakin_mahalle_noktasi: yalnız ilk dört yöntem sonuç vermezse, eskisi gibi belirsizlik işaretiyle.
Rosemary Beach ve Alys Beach kısıtı her yöntemde geçerlidir.

Ek değişiklikler:
- Alt bölüm sonuç CSV'sine SUBDIVISION_NUMBER sütununu ekle (OBJECTID haftalık yayında değişebilir). İlçe sorgularını yeniden çalıştırman gerekirse aynı 53 nokta için yap ve ham yanıtları work/ altında sakla.
- Ad tablosu kuralı (yalnız tam mahalle adı) olduğu gibi kalır.
- Plaj ekranında iki yeni yöntem etiketi: "ilçe alt bölüm verisi (bitişik)" ve "komşu erişimlerle tutarlı". Videoda kullanım notu M7'ye: "ilçe alt bölüm verisi (bitişik)" kaynak gösterilerek söylenebilir ("Walton County subdivision verisine göre, erişimin bitiştiği alt bölüm"); "komşu erişimlerle tutarlı" ve "program türetimi" yalnız yaklaşık konumdur.
- Eşleme dosyasını gerçek veritabanının mevcut plaj ve mahalle çekimleriyle (GÖREV-04'teki 1a195e2b… ve 3d1cbe8d…) yeniden üret.
- Doğrulama: yeni yöntemleri 9 resmî eşlemeye uygula (aynı / sonuçsuz / farklı). v2 → v3 farklarını tek tek listele. Mahalle başına erişim sayılarını yönteme göre ayrılmış olarak ver.
- Testler: 30 m sınırı (29,9 / 30,0 / 30,1 m), ad tablosunda olmayan poligonun içindeyken yakın kural, iki farklı mahalle yakınlığı, komşu tutarlılığı (iki komşu aynı / farklı / bir taraf yok), Rosemary–Alys kısıtı.
Adım 2'yi ayrı bir commit olarak at.

==================================================
ADIM 3 — İklim paketi: genel tasarım
==================================================
Üç yeni toplayıcı yazılacak. Üçü de genel çekirdektedir: başka destinasyonlarda da kullanılacaklar. Destinasyona özel olan şeyler (istasyonlar, kıyı koridoru, yarıçaplar) hava örnek noktalarındaki gibi SQLite'ta destinasyon kapsamlı yapılandırmadan gelir; 30A için ilk değerleri profil ve migration yazar. Kaynaklar ve ayrıntıları docs/gorevler/GOREV-02/KAYNAK-KESFI.md Alan 4 ve 5'tedir.

Hepsi mevcut genel akışı kullanır (kaynak → iş → çekim → ham dosya → atomik yazım), ham yanıtları SHA-256 ile saklar, iptali ve hatayı doğru işler. Bu veriler durağan olduğu için kayıt farkı (diff) gerekmiyorsa kapatılabilir; gerekçesini belgeye yaz.

Şema 8 ve uygulama 0.8.0. Migration mevcut kurallarla (yedek, tek transaction, foreign_key_check, geri alma).

Sözlük ve dil: veri ve rapor dilinde her değer kaynağıyla birlikte etiketlenir. "30A'nın iklimi" denmez; "30A'ya en yakın kıyı istasyonu Destin'in 1991–2020 normali" denir. Hesapladığımız değerler (deniz suyu ortalaması, kasırga sayıları) "NOAA verisinden bizim hesabımız" diye işaretlenir.

==================================================
ADIM 4 — Üç toplayıcı
==================================================
4a. ncei-climate-normals
- Kaynak: NOAA NCEI US Climate Normals 1991–2020, aylık, NCEI'nin anahtarsız erişim API'si (access/services/data/v1, dataset=normals-monthly-1991-2020). NCEI'nin robots.txt'si /data* yolunu kapatıyor; API yolunu kullan.
- 30A yapılandırması: Destin–Fort Walton Beach Havalimanı USW00053853 (rol: kıyı referansı), DeFuniak Springs USC00082220 (rol: iç kesim karşılaştırması). Her istasyonun adı, koordinatı ve 30A'ya kuş uçuşu uzaklığı yapılandırmada dursun.
- Değişkenler: aylık ortalama, en yüksek ve en düşük sıcaklık; aylık yağış; yağışlı gün sayısı (≥0,10 inç); en yüksek sıcaklığın ≥90°F olduğu gün sayısı; en düşük sıcaklığın ≤32°F olduğu gün sayısı. API'nin bu değişkenler için kullandığı tam kodları doğrula ve belgele. Bir istasyon bir değişkeni vermiyorsa NULL kalır, hata değildir.
- Her değerle birlikte kaynağın tamlık bayrağı saklanır (Destin "R" bayraklı). Birimler kaynaktaki gibi (°F, inç); arayüz ayrıca °C ve mm gösterir.

4b. ndbc-water-temperature
- Kaynak: NOAA NDBC tarihî standart meteoroloji yıllık dosyaları (data/historical/stdmet/<istasyon>h<yıl>.txt.gz). robots.txt'yi kontrol et ve rapora yaz.
- 30A yapılandırması: PCBF1 (NOS 8729210, Panama City Beach); koordinat ve 30A'ya uzaklık yapılandırmada.
- Bulunan bütün yılların dosyalarını indir (olmayan yıl 404 ise atla, rapora yaz). WTMP sütununu oku; kaynağın eksik değer işaretleri (99,0 / 999,0 gibi) NULL olur.
- Her yıl-ay için: ortalama, gözlem sayısı, verisi olan gün sayısı. Bir yıl-ay ancak en az 20 günlük verisi varsa çok yıllı ortalamaya girer. Çok yıllı aylık özet: ortalama, kullanılan yıl sayısı ve yıl aralığı. Ham 6 dakikalık değerler veritabanına yazılmaz; ham dosyalar SHA-256 ile saklanır.
- Etiket: "PCBF1 (Panama City Beach) ölçümlerinden hesaplanan aylık ortalama, kullanılan yıllar …".

4c. hurdat2-storm-proximity
- Kaynak: NOAA NHC HURDAT2 Atlantik dosyası. Dosya adı sürümle değişiyor; güncel adı NHC'nin veri sayfasından oku ve çekim kaydına yaz.
- 30A yapılandırması: kıyı koridoru = programdaki en batı ve en doğu plaj erişimi arasındaki doğru parçası (koordinatlar yapılandırmada); yarıçaplar: 50 ve 100 deniz mili.
- Yöntem (GÖREV-02'de önerildiği gibi): iz noktaları arasında 1 saatlik doğrusal ara değerleme; her fırtına için koridora en yakın mesafe; her yarıçap için fırtınanın daireye ilk girdiği zaman ve ay; daire içindeyken ulaştığı en yüksek rüzgâr ve buna göre sınıf (tropikal depresyon <34 kt, tropikal fırtına 34–63 kt, kasırga ≥64 kt, büyük kasırga ≥96 kt); her fırtına her yarıçap için bir kez sayılır.
- Saklanacak: fırtına kimliği, adı, yılı, yarıçap, ilk giriş zamanı ve ayı, en yakın mesafe (km ve deniz mili), daire içindeki en yüksek rüzgâr ve sınıf. Bütün yıllar saklanır; dönem seçimi (ör. 1991–2025 ve tüm kayıt) okuma sırasında yapılır.
- Uyarılar belgeye: merkezin geçmesi etki demek değildir; eski dönemlerde eksik sayım vardır; aylık sayılar küçük olabilir.

==================================================
ADIM 5 — Arayüz, testler, belgeler
==================================================
- Veri toplama ekranına "İklim" sekmesi: üç toplayıcının düğmeleri ve son çekimleri; aylık tablo (kıyı istasyonu normalleri, iç kesim karşılaştırması seçilebilir; deniz suyu çok yıllı ortalaması ve kullanılan yıl sayısı); kasırga bölümü (seçilen yarıçap ve dönem için aylara göre fırtına sayısı, sınıflara göre ayrılmış; en yakın geçen fırtınaların listesi). Her tablonun altında kaynak ve "bizim hesabımız" etiketi. Mevcut görsel düzeni koru.
- Testler fixture ve MockTransport ile, canlı ağ yok. Kapsananlar en az: değişken eksikliği (NULL), bayrak saklama, NDBC eksik değer işaretleri ve 20 gün kuralı, yıl dosyası 404, HURDAT2 ayrıştırma (başlık ve iz satırları), ara değerleme, mesafe hesabı, yarıçap içi ilk giriş ve sınıf, iptal, atomik geri alma, v7 → v8 migration ve geri alma, destinasyon yalıtımı (başka destinasyonun yapılandırması karışmaz).
- Yeni belge docs/M8-IKLIM-VERISI.md: kaynaklar, yapılandırma, yöntemler, sınırlar ve video dili. CALISMA_MANTIGI.md, README.md, docs/DEVIR/05 ve 02'deki güncel durum satırlarını güncelle.

==================================================
ADIM 6 — Gerçek ortam
==================================================
1. Canlı deneme geçici klasörde (work/gorev-05/temp-data): üç iklim toplayıcısını çalıştır, sonuçları rapora yaz, İklim sekmesinin ekran görüntüsünü al.
2. Migration denemesi gerçek verinin kopyasında (v7 → v8), satır sayıları ve bütünlük kontrolleriyle.
3. Gerçek veritabanı, CLAUDE.md kuralına göre: data/ tam yedeği work/yedek/<tarih>/ altına; uygulamayı gerçek veriyle aç (v7 → v8 uygulamanın kendi yedeğiyle); yalnız üç iklim toplayıcısını çalıştır; kapat; satır sayıları, integrity_check ve foreign_key_check.

==================================================
TESLİM
==================================================
docs/gorevler/GOREV-05/ altına: GOREV.md (work/gorevler/GOREV-05.md'nin kopyası), RAPOR.md, esleme-v2-v3-fark.csv, esleme-dogrulama-v3.csv, iklim-normalleri.csv (iki istasyon × 12 ay, bütün değişkenler ve bayraklar), deniz-suyu-aylik.csv (çok yıllı özet ve yıl-ay tablosu), kasirga-gecisleri.csv (iki yarıçap, bütün fırtınalar), kasirga-aylik-1991-2025.csv ve ekran görüntüleri (İklim sekmesi, plaj ekranı v3).
RAPOR.md Türkçe ve sade: her adımın sonucu, main'in konumu, CI sonuçları, test sayıları, v3 doğrulaması ve mahalle başına sayılar, üç toplayıcının canlı sonuçları, ilk videoda kullanılabilecek başlıca rakamlar (kaynak etiketleriyle, ör. Destin'de Temmuz ortalama en yüksek sıcaklığı, PCBF1'e göre Mayıs ve Ekim deniz suyu ortalaması, 1991–2025'te 50 deniz mili içinden geçen kasırga sayısının aylara dağılımı), beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-05 bitti, dal gorev-05-iklim, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
