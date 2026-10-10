GÖREV-11 — v0.13.0 yayını, küçük veri düzeltmeleri, izleyicinin sorduğu konular için referanslar ve ilk videonun kanıt paketi

BAĞLAM
GÖREV-10 kabul edildi. İlk videonun ("30A'ya ilk kez gidecekler için tam karar rehberi") veri temeli neredeyse tamam: mahalleler, plaj erişimi, kurallar, iklim, kalabalık, ay ay konaklama fiyatları, restoranlar ve günlük ihtiyaç ölçüleri var. Bu görevden sonra makale aşamasına geçilecek. Bu görevin üç işi var:

A. Günlük ihtiyaç verisinde iki düzeltme. "Süpermarket ve market" kategorisi büyük zincirlerle (Publix, Walmart, Winn-Dixie, Aldi, Target, The Fresh Market) yerel ve gurme marketleri (Modica Market, Seacrest Sundries, For The Health Of It) karıştırıyor; Seaside'ın 0,15 millik süpermarket mesafesi aslında Modica Market. Bir haftalık kiralık ev için büyük alışveriş "arabaya ihtiyaç var mı" sorusunun merkezinde olduğu için bu ayrım şart. Acil sağlıkta OpenStreetMap'te yalnız 2 nokta var; resmî kaynaklarla tamamlanacak.
B. YouTube'daki rakip videoların yorumlarında izleyicinin en çok sorduğu ve tartıştığı konular için referans tablosuna yeni satırlar: plaj erişimi hukuku (halka açık ve özel plaj; en çok tartışılan konu), erişilebilirlik, trafik, kalabalık haftaları (okul tatilleri), tekrarlayan büyük etkinlikler ve merak açıları için temel bilgiler (Seaside, Truman Show, New Urbanism).
C. Kanıt paketi: veritabanından makaleye köprü. Uygulama, seçilen video konusu için gereken bütün kanıtı kaynaklarıyla, etiketleriyle ve kullanım notlarıyla tek bir okunur dosyada toplayacak. İlk video için bir şablon ve kanalın omurgası olan mahalle rehberleri için parametreli bir şablon yazılacak; mahalle şablonu Rosemary Beach'le denenecek.

Kanal planı (bağlayıcı, yöneticinin notlarında): 30A tek bir kanal; mahalleler bu kanalın alt bölgeleri ve video konuları. Konu motoru "bölge × seyahat kararı × dönem × gezgin tipi"; her mahallenin kendi mini konu evreni var (rehber, maliyet, arabasız, aileler için, belirli bir ayda, nerede yenir, plaj erişimi, fiyatına değer mi). Şablon yapısı ileride bu kombinasyonlara genişleyebilecek şekilde kurulmalı; bu görevde yalnız iki şablon yazılır.

Kullanıcı bu görev için main'e alma, etiket, gerçek veritabanını normal kullanımla güncelleme ve görevin gerektirdiği sitelere tarayıcıyla girme iznini kendi mesajında açıkça veriyor. Bilgisayarda zamanlanmış görev oluşturulmaz.

KESİN SINIRLAR
- data/ yalnız Adım 5'te, CLAUDE.md kuralına göre (önce tam yedek, sonra uygulamanın normal kullanımı) değişir.
- main'e yalnız Adım 1'deki fast-forward ile dokun; yalnız Adım 1'deki etiketi koy.
- Tarayıcı CLAUDE.md'deki kurala göre kullanılır (yalnız engelde). Proxy, VPN, IP değiştirme, gizlenme, CAPTCHA çözme yok; hesap, giriş, form yok.
- Hukuki ve tarihî bilgiler yalnız birincil ya da resmî kaynaklardan (anayasa ve kanun metni, ilçe kararı ve sitesi, mahkeme kararı, kurumun kendi sitesi) alınır. İkincil kaynak (haber) yalnız birincil kaynak bulunamazsa ve "ikincil" diye işaretlenerek kullanılır.
- Kanıt paketi yorum, tavsiye ya da sıralama içermez; yalnız kanıt, etiketi ve kullanım notu.

==================================================
ADIM 1 — v0.13.0'ı main'e al ve etiketle
==================================================
Önce origin/gorev-10-aylik-gunluk'un son commit'i (4187c1c) için GitHub Actions sonucunu kontrol et; başarısızsa önce düzelt, düzeltmeyi dala ekle ve bu adımı o commit'le yap. Sonra main'i bu dala git merge --ff-only ile getir ve push et; son commit'e "v0.13.0" açıklamalı etiketini koy (mesaj: "v0.13.0 — aylık konaklama fiyatları, güncelleme göstergesi, günlük ihtiyaç ölçüleri ve restoran gözden geçirmesi") ve push et. main ve etiket CI sonucunu rapora ekle. Güncel main'den "gorev-11-kanit-paketi" dalını aç.

==================================================
ADIM 2 — Günlük ihtiyaç verisinde düzeltmeler
==================================================
Yönetici kararları (GÖREV-10 raporundaki sorulara):
- order.online ve realjoy kapsam dışı; başka yöntem denenmez, normal çekimlerde açılırlarsa alınır.
- Toplu konaklama + kiralama çalıştırmasının ~9 saat sürmesi kabul; pencere sayısı azaltılmaz. README'deki düğme açıklamasına "uzun sürer, akşam başlatmak uygundur" notu eklenir.
- Publix, Winn-Dixie ve The Fresh Market'in OpenStreetMap noktaları "zincirin sitesi bu bilgisayardan doğrulanamadı" notuyla kalır.
- Blue Mountain Bakery'de yalnız güncel ("NEW") menü kullanılır.

2a. Süpermarket ayrımı: "Süpermarket ve market" kategorisi ikiye ayrılır: "büyük süpermarket" (markası destinasyon yapılandırmasındaki zincir listesinde olanlar: Publix, Walmart Supercenter ve Walmart Neighborhood Market, Winn-Dixie, Aldi, Target, The Fresh Market, Whole Foods, Trader Joe's) ve "yerel ve gurme market" (diğerleri). Zincir listesi yapılandırmada durur, kod genel kalır. Mahalle ölçüleri ikisi için ayrı verilir.

2b. Acil sağlık: bölge kutusunda acil servisi olan hastaneleri ve hastaneden bağımsız acil servisleri, ayrıca acil bakım (urgent care / walk-in) merkezlerini hastane sistemlerinin ve acil bakım zincirlerinin kendi konum sayfalarından bul (ör. Ascension Sacred Heart, HCA Florida Healthcare, Baptist Health ve bölgede yeri olan diğerleri). Kategori ikiye ayrılır: "acil servis" ve "acil bakım". Resmî kaynaktan gelen noktalar gözden geçirilmiş bir dosyayla (kaynak url, erişim tarihi, adres, koordinat ve koordinatın kaynağı) eklenir; OpenStreetMap'teki 2 nokta resmî kaynakla doğrulanırsa kalır. Farklar rapora yazılır.

2c. Eczane: CVS ve Walgreens'in kendi mağaza bulucuları okunabiliyorsa OpenStreetMap'teki eczaneleri onlarla karşılaştır; Publix mağazalarının içindeki eczaneler sitesi okunamadığı için not olarak kalır.

==================================================
ADIM 3 — Referans tablosuna yeni satırlar
==================================================
Her satır mevcut referans tablosu sütunlarıyla (ifade İngilizce, kısa alıntı, belge tarihi, erişim tarihi, SHA-256, güven, durum, yeniden kontrol tarihi). Bulunamayan bilgi "doğrulanamadı" diye kalır; tahmin yok.

3a. Plaj erişimi hukuku: Florida'da ortalama yüksek su çizgisinin deniz tarafındaki kumun halka açık olması (Florida Anayasası Madde X Bölüm 11 ve ilgili kanun); Walton County'nin 2016 "customary use" kararı; 2018'deki eyalet kanunu (HB 631, Florida Statutes 163.035) ve getirdiği süreç; ilçenin açtığı customary use davası ve sonucu (mahkeme kararlarıyla); bugünkü durum ve 2025–2026'daki değişiklikler. Rakip videonun yorumlarında "yeni bir yasa imzalandı, özel plaj kalmadı" iddiası var; bunu birincil kaynakla doğrula ya da "doğrulanamadı" yaz. Video için ayrıca kaynağın söylediği kadarıyla tek satırlık bir özet ifade ekle.

3b. Erişilebilirlik: ilçenin ya da Visit South Walton'ın plaj tekerlekli sandalyesi hizmeti (var mı, ücretsiz mi, nereden alınır) ve engelli erişimine uygun plaj erişimleri (rampa, mobi-mat vb.). İlçe böyle bir liste yayımlıyorsa listedeki erişimleri bizim 53 erişimimizle eşleştir ve rapora yaz.

3c. Trafik: FDOT'un yayımladığı yıllık ortalama günlük trafik sayıları (AADT), CR 30A ve US 98'in Walton County'deki sayım istasyonları için en son yıl; FDOT'un Walton County için yayımladığı ay ay mevsim faktörleri (trafiğin aylara göre yıllık ortalamaya oranı). Satır sayısı fazlaysa referans tablosunun yanında küçük bir CSV'ye konabilir; kaynak alanları aynı kalır.

3d. Kalabalık haftaları: 30A'ya gelen ziyaretçilerin başlıca geldiği şehirler (Walton County Tourism'in yayımladığı ziyaretçi profili raporlarından; Downs & St. Germain) ve bu raporun saydığı ilk 5 metropolün en büyük okul bölgesinin 2026–27 resmî takviminden bahar tatili ve güz tatili haftaları.

3e. Tekrarlayan büyük etkinlikler: 30A'nın her yıl tekrarlanan büyük etkinlikleri (ör. 30A Songwriters Festival, Seaside'daki şarap festivali, Alys Beach'teki Digital Graffiti, 4 Temmuz kutlamaları; etkinliğin kendi resmî sitesinden doğrula): ad, yer ve mahalle, olağan ay, 2027 tarihleri yayımlanmışsa tarih. 10–15 satır.

3f. Merak açıları için temel bilgiler: Seaside'ın kuruluşu ve kurucusu, The Truman Show'un Seaside'da çekilmesi (çekim ve yayın yılı), Seaside, Rosemary Beach ve Alys Beach'in planlayıcıları ve "New Urbanism", Alys Beach'in kuruluşu. Seaside'ın, Alys Beach'in, planlama firmasının ya da kurumların kendi sitelerinden.

==================================================
ADIM 4 — Kanıt paketi
==================================================
4a. Yapı: kanıt paketi üretimi genel çekirdekte; şablonlar destinasyon tarafında dosya olarak durur. Bir şablon: başlık, videonun ana sorusu, parametreler (ör. mahalle) ve bölümler. Her bölümün bir sorusu ve kullanacağı veri blokları vardır. Veri blokları genel ve yeniden kullanılabilir olur (ör. mahalle tanımı, plaj erişimleri ve eşleme yöntemi, konuya göre referans satırları, iklim ay tablosu, deniz suyu, kasırga sayıları, turist vergisi sezon deseni, mevsimlik doluluk ve ADR, konaklama ay tablosu ve oda grupları, restoran özeti, günlük ihtiyaç ölçüleri, etkinlikler). Şablon yapısı ileride "bölge × karar × dönem × gezgin tipi" kombinasyonlarına genişleyebilecek şekilde tasarlanır; bu görevde yalnız aşağıdaki iki şablon yazılır.

4b. Her kanıt satırında: Türkçe ifade; değer ve birim (videonun dili İngilizce olduğu için ABD birimleri; sıcaklıkta °F ve °C); kapsam (mahalle, ilçe, istasyon, dönem); kaynak adı, url, belge ya da erişim tarihi, çekim kimliği; etiket (kaynak gerçeği, bizim hesabımız, türetilmiş, yaklaşık); örnek büyüklüğü (varsa); kullanım notu (o verinin M belgesindeki video dili kurallarından: ne söylenebilir, ne söylenemez); varsa kaynağın İngilizce kısa alıntısı. M belgelerinde olmayan bir kullanım notu uydurulmaz; eksikse M belgesine eklenir ve rapora yazılır.

4c. Paketin başında: üretim tarihi; her kaynağın son çekim tarihi ve güncelleme zamanı gelmiş olanlar; bilinen boşluklar (ör. 360blue ve realjoy yok, Gulf Place küçük örnek, OpenStreetMap sınırları, seviyesi olmayan restoranlar, Alys Beach fiyatlarının şirketin kendi envanterinden gelmesi); "bu paket yorum ve tavsiye içermez" notu.

4d. Paketin sonunda: sayı kontrol listesi. Paketteki her sayı tek satırda: ifade, değer, birim, kanıt satırının kimliği. Makale yazıldıktan sonra metindeki her sayı bu listeye karşı kontrol edilecek.

4e. Çıktı: tek bir Markdown dosyası (okunur) ve aynı içeriğin JSON'u. Uygulamada "Kanıt paketi" ekranı: şablon seç, parametre ver, üret, indir. Her üretim tarihli ve SHA-256'lı olarak saklanır (uygulamanın normal kullanımıyla, data/ altında).

4f. İki şablon:
1. "30A'ya ilk kez gidecekler için tam karar rehberi" (ilk video). Bölümler: 30A nedir ve nerededir (30A'nın bir yol olduğu, Walton County, Destin ve Fort Walton Beach ile karıştırılması); 13 mahallenin karakteri; plaj erişiminin gerçeği (ilçenin halka açık erişimleri ve hangi topluluklarda listede erişim olmadığı, plaj erişimi hukuku); plaj kuralları ve güvenlik (bayraklar, cankurtaran, cam, köpek, çadır); hava, deniz suyu ve kasırga; kalabalık ve sezon (turist vergisi deseni, mevsimlik doluluk ve ADR, okul tatilleri, büyük etkinlikler); konaklama maliyeti (mahalle × ay, oda grupları; Alys Beach ayrı etiketli); yemek (mahalle başına restoran sayısı, fiyat seviyeleri, rezervasyon); araba ve ulaşım (büyük süpermarket, eczane ve acil sağlık mesafeleri, golf arabası ve LSV kuralları, park, havalimanları, trafik); erişilebilirlik; pratik bilgiler.
2. "Mahalle rehberi" (parametre: mahalle). KONSEPT'teki bölge videosu sorularının veriyle cevaplanabilenleri: mahallenin resmî tanımı, plaj erişimleri, konaklama (ilan sayısı, tür ve oda dağılımı, ay ay fiyat), restoranlar (liste, seviye, rezervasyon, çocuk menüsü, saatler), günlük ihtiyaç mesafeleri, mahalleye özgü referanslar (otopark, servis, kurallar), etkinlikler, hava ve sezon (30A genelinden, öyle etiketli). Rosemary Beach ile üret.

4g. Testler: şablon okuma, parametre, her veri bloğunun eksik veride davranışı (eksik veri paketten sessizce düşmez, "veri yok" diye yazılır), kullanım notunun satıra geçmesi, sayı kontrol listesinin paketteki her sayıyı içermesi, Markdown ve JSON'un aynı içeriği taşıması, üretimin saklanması.

4h. Belge: docs/M14-KANIT-PAKETI.md (yapı, veri blokları, şablon biçimi, etiketler, sayı kontrol listesi, yeni şablon nasıl yazılır).

==================================================
ADIM 5 — Gerçek ortam ve teslim
==================================================
1. Geçici klasörde deneme: günlük ihtiyaç (ayrım ve resmî acil sağlık noktalarıyla), referans tablosu, iki kanıt paketi.
2. Şema değişirse migration denemesi gerçek verinin kopyasında.
3. Gerçek veritabanı, CLAUDE.md kuralına göre: data/ tam yedeği; uygulamayı gerçek veriyle aç; günlük ihtiyaç toplayıcısı; referans tablosunun yüklenmesi; iki kanıt paketinin üretilmesi (ilk video ve Rosemary Beach); kapat; satır sayıları, integrity_check ve foreign_key_check.
4. Belgeler: CALISMA_MANTIGI.md, README.md, docs/DEVIR/05 ve 02'nin güncel durum satırları, M9 (referanslar), M13, M14. Tam test takımı yerelde art arda en az 3 kez geçmeli.

TESLİM
docs/gorevler/GOREV-11/ altına: GOREV.md (work/gorevler/GOREV-11.md'nin kopyası), RAPOR.md, referans-tablosu.csv (güncel; yeni satırlar ayrıca listelenmiş), varsa trafik CSV'si, gunluk-ihtiyac-mahalle.csv (güncel), gunluk-ihtiyac-noktalar.csv (güncel), kanit-paketi-ilk-video.md ve .json, kanit-paketi-rosemary-beach.md ve .json, ekran görüntüleri.
RAPOR.md Türkçe ve sade: her adımın sonucu, main ve etiketin konumu, CI sonuçları, test sayıları, süpermarket ayrımından sonra mahalle başına büyük süpermarket mesafeleri, resmî acil sağlık noktaları ve OpenStreetMap ile farkları, yeni referans satırlarının özeti (özellikle plaj erişimi hukukunun bugünkü durumu ve "yeni yasa" iddiasının sonucu), kanıt paketlerinin yapısı ve boyutu (bölüm, kanıt satırı, sayı adedi), paketlerde "veri yok" kalan yerler, gerçek veritabanının öncesi/sonrası, beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-11 bitti, dal gorev-11-kanit-paketi, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
