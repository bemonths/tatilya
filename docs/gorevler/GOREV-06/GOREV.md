GÖREV-06 — v0.8.0 yayını, kasırga sayımının düzeltilmesi ve elle doğrulanmış referans tablosu

BAĞLAM
GÖREV-05 kabul edildi. Eşleme v3 kilitlendi; iklim paketi çalışıyor. Bu görevde üç iş var: v0.8.0 main'e alınıp etiketlenecek (gerçek veritabanı zaten şema 8, main ise hâlâ 0.7.0); kasırga sayımı yalnız tropikal ve subtropikal evrelere göre düzeltilecek; ilk videonun toplayıcıyla alınamayan bilgileri (plaj kuralları, bayrak sistemi, ulaşım, parklar, sezon ve maliyet) için elle doğrulanmış, kaynaklı bir referans tablosu kurulacak. Bu, ilk video için veri temelinin son parçasıdır; bundan sonra kanıt paketi ve makale aşamasına geçilecek.

Kullanıcı bu görev için main'e alma, etiket ve gerçek veritabanını normal kullanımla güncelleme iznini kendi mesajında açıkça veriyor.

KESİN SINIRLAR
- data/ yalnız Adım 5'te, CLAUDE.md kuralına göre (önce tam yedek, sonra uygulamanın normal kullanımı) değişir.
- main'e yalnız Adım 1'deki fast-forward ile dokun; yalnız Adım 1'deki etiketi koy.
- Mevcut toplayıcıların davranışını değiştirme (kasırga toplayıcısındaki Adım 2 düzeltmesi hariç).

==================================================
ADIM 1 — v0.8.0'ı main'e al ve etiketle
==================================================
main'i origin/gorev-05-iklim (de6685f) konumuna git merge --ff-only ile getir ve push et. Bu commit'e "v0.8.0" açıklamalı etiketini koy (mesaj: "v0.8.0 — eşleme v3 ve iklim paketi") ve push et. Etiket zaten varsa dur ve rapora yaz. main CI sonucunu rapora ekle. Güncel main'den "gorev-06-referanslar" dalını aç.

==================================================
ADIM 2 — Kasırga sayımı: yalnız tropikal ve subtropikal evreler
==================================================
Yönetici kararı: sayım ve sınıflandırma yalnız fırtınanın tropikal veya subtropikal olduğu evrelere göre yapılır. HURDAT2 durum kodlarından TD, TS, HU, SD, SS kullanılır; EX, LO, WV, DB evreleri yarıçap içine giriş, en yakın mesafe ve en yüksek rüzgâr hesabına girmez. Ara değerlemede iki iz noktası arasındaki noktalar, aralığın başındaki noktanın evresini taşır.
- Yarıçap içinde yalnız tropikal olmayan evrede bulunmuş fırtınalar saklanmaya devam eder ama "yalnız tropikal olmayan evre" diye işaretlenir ve aylık sayımlara, sınıf tablolarına ve "en yakın geçen fırtınalar" listesine girmez.
- Toplayıcının sürümünü artır (ör. hurdat2-storm-proximity/2); eski çekimler eski sürümüyle olduğu gibi kalır.
- İklim sekmesindeki kasırga bölümü ve kaynak açıklaması yeni kuralı yazsın.
- Testler: evre sınırında ara değerleme, yalnız EX evresinde yarıçapa giren fırtına, TD→EX geçişi olan fırtına, SD/SS'nin sayılması.
- M8 belgesini güncelle. Video dönemi kararı da belgeye: videoda kasırga rakamları 1991–2025 dönemiyle verilir ve dönem açıkça söylenir.
Bu adımı ayrı bir commit olarak at.

==================================================
ADIM 3 — Elle doğrulanmış referans tablosu
==================================================
Amaç: toplayıcıyla alınamayan ama ilk videoda söylenecek her bilgiyi, kaynağıyla ve doğrulama tarihiyle tek bir yerde tutmak. Kanıt paketi ve makale aşaması bu tabloyu okuyacak.

3a. Yapı
- 30A destinasyon profilinin yanında repoda sürümlenen bir CSV (yerini mimariye uygun seç). Her satır tek bir olgu. Sütunlar:
  id (kalıcı, ör. kural-cam-yasagi), konu, ifade (İngilizce, tek cümle, kendi cümlemizle; videoda söylenebilecek biçimde), deger, birim, kapsam (30A / South Walton / Walton County / Florida / Atlantik havzası), kaynak_adi, kaynak_sahibi, kaynak_url, belge_konumu (bölüm, madde, sayfa), kisa_alinti (kaynaktan birebir en fazla 25 kelime; yalnız doğrulama için, videoda kullanılmaz), belge_tarihi (biliniyorsa), erisim_tarihi, belge_sha256 (alınan dosyanın ya da sayfanın), guven (birincil / ikincil), durum (dogrulandi / celiskili / dogrulanamadi), celiski_notu, yeniden_kontrol_tarihi, not.
- Alınan belgeler work/referans-belgeler/ altında saklanır (repoya girmez); SHA-256 tabloya yazılır.
- Uygulama tabloyu okur; Veri toplama ekranına salt okunur bir "Referanslar" sekmesi eklenir: konulara göre gruplu liste, kaynak bağlantısı, erişim tarihi, durum etiketi ve yeniden kontrol tarihi geçmiş satırların işaretlenmesi.
- Doğrulayıcı test: zorunlu sütunlar, kimlik tekilliği, tarih biçimleri, "dogrulandi" satırlarında URL, erişim tarihi ve SHA-256 zorunluluğu, alıntının 25 kelimeyi geçmemesi.

3b. Kaynak politikası (CALISMA_MANTIGI 4. bölüm, 14. madde): belirli bir resmî belgenin kaynak göstermek için tek seferlik elle alınması toplayıcı sayılmaz. Bot doğrulaması (Cloudflare) olan bir sayfayı aşmak için otomasyon kullanma; böyle bir sayfa okunamazsa satır "dogrulanamadi" olur. İki kaynak çelişirse ikisi de ayrı satır olarak yazılır, durum "celiskili" olur ve celiski_notu doldurulur; hangisinin doğru olduğuna sen karar verme.

3c. Doldurulacak konular (kaynak adayları docs/gorevler/GOREV-02/KAYNAK-KESFI.md Alan 2, 3, 6, 8, 9'da):
- Plaj kuralları — Walton County Ordinance 2025-22 (taranmış PDF; sayfaları okuyarak, bölüm numarasıyla): köpek, cam, çadır ve şemsiye ölçüleri, 15 ft kuralı, gece eşya bırakma saatleri, ateş/ızgara/havai fişek, gece kamp yasağı, çukur ve metal kürek, kapatma emirlerine uyma, deniz kaplumbağası yuvalama sezonu ve buna bağlı gece kuralları, cezalar. Alkol için Bölüm 22'de hüküm olmadığını ayrı bir satırda "bu bölümde hüküm yok" diye yaz; başka mevzuatı arama.
- Güvenlik — South Walton Fire District: bayrak renkleri ve anlamları, çift kırmızı bayrağın anlamı, mor bayrak, bayrağın ne sıklıkla değerlendirildiği, ateş izni kuralları. Cankurtaran sezonu: SWFD ve Visit South Walton'daki iki farklı ifade ayrı satır, durum "celiskili".
- Plaj erişimi — Visit South Walton park ve ulaşım rehberi (2023-05-04): Rosemary Beach ve Alys Beach için "halka açık plaj erişimi yok" ifadesi; bölgesel ve mahalle erişimi türlerinin tanımı (haritadaki açıklamadan); ücretli park-and-ride otoparkları ve ücretleri; ücretsiz servis.
- Ulaşım — havalimanları (ECP, VPS, PNS) ve 30A kıyı koridoruna kuş uçuşu uzaklıkları (FAA koordinatlarından bizim hesabımız; guven=birincil, not="bizim hesabımız"); Timpoochee Trail uzunluğu (Visit South Walton'daki iki farklı değer, "celiskili"); golf arabası ve düşük hızlı araç kuralları (Florida Statutes 316.212 ve 316.2122); Walton County Ordinance 2009-02'nin çok amaçlı yollar hükmü.
- Parklar — Grayton Beach State Park, Topsail Hill Preserve State Park, Deer Lake State Park giriş ücreti ve saatleri (Florida State Parks; okunamazsa "dogrulanamadi"); Point Washington State Forest gün kullanımı ücreti ve saatleri (Florida Forest Service).
- Kasırga sezonu — NHC: Atlantik kasırga sezonunun resmî tarihleri ve etkinlik zirvesi.
- Sezon ve maliyet — Walton County Tourism'in Downs & St. Germain raporları: en son yıllık rapordan yıllık ziyaretçi sayısı, oda-gece, ortalama günlük oda fiyatı (ADR) ve doluluk; en son dört mevsim raporundan her mevsimin ADR ve doluluk değeri. Kapsamı (Walton County veya South Walton) her satırda doğru yaz; raporda yöntem değişikliği uyarısı varsa nota ekle.
- Genel — Visit South Walton'ın mahalle sayısı (16) ve South Walton tanımı; Ordinance 2025-22'nin "Gulf of America" adlandırması (yalnız olgu olarak).

3d. Aylık turist vergisi (kısa keşif, en fazla yaklaşık 30 dakika): Walton County Tourism "TDT Collections" sayfasında aylık değerlerin tarayıcıda hangi istekle yüklendiğini bul (sayfanın kendi betiği ve ağ istekleri; tarayıcı otomasyonu yok). Herkese açık bir veri ucu (JSON, CSV, XLSX, PDF) bulursan: South Walton vergi bölgesinin bulunabilen bütün aylık tahsilatlarını referans CSV'nin yanına ayrı bir CSV olarak kaydet (ay, vergi bölgesi, tutar, kaynak URL, erişim tarihi, SHA-256) ve "ayın tahsil ayı mı konaklama ayı mı olduğu" sorusuna kaynakta cevap ara. Bulamazsan neyi denediğini rapora yaz ve geç.

==================================================
ADIM 4 — Belgeler ve testler
==================================================
- Yeni kısa belge docs/M9-REFERANS-TABLOSU.md: tablonun amacı, sütunlar, kaynak politikası, durumlar, yeniden kontrol kuralı (kurallar ve ücretler yılda bir; mevsim raporları her yeni rapor çıktığında) ve video dili ("dogrulandi" satırlar kaynak gösterilerek söylenebilir; "celiskili" satırlar ancak çelişki açıkça söylenerek ya da daha güncel resmî kaynakla çözülerek; "dogrulanamadi" satırlar videoda kullanılmaz).
- CALISMA_MANTIGI.md, README.md, docs/DEVIR/05 ve 02'nin güncel durum satırları. Uygulama sürümü 0.9.0.
- Tam test takımı yerelde art arda en az 3 kez geçmeli.

==================================================
ADIM 5 — Gerçek ortam
==================================================
1. Geçici klasörde canlı deneme (work/gorev-06/temp-data): kasırga toplayıcısının yeni sürümünü çalıştır; 1991–2025 için 50 ve 100 deniz mili aylık sayımlarını eski sonuçla karşılaştır.
2. Gerçek veritabanı, CLAUDE.md kuralına göre: data/ tam yedeği; uygulamayı gerçek veriyle aç; yalnız kasırga toplayıcısını çalıştır; kapat; satır sayıları, integrity_check ve foreign_key_check.
3. Referanslar sekmesinin ve İklim sekmesindeki kasırga bölümünün ekran görüntülerini al.

==================================================
TESLİM
==================================================
docs/gorevler/GOREV-06/ altına: GOREV.md (work/gorevler/GOREV-06.md'nin kopyası), RAPOR.md, referans tablosunun kopyası, kasirga-aylik-1991-2025-v2.csv, kasirga-v1-v2-fark.csv (aylara ve sınıflara göre eski ve yeni sayılar, sayımdan çıkan fırtınaların listesi), varsa turist vergisi CSV'si ve ekran görüntüleri.
RAPOR.md Türkçe ve sade: her adımın sonucu, main ve etiketin konumu, CI sonuçları, test sayıları, kasırga sayımındaki değişiklik, referans tablosunun konu başına satır ve durum sayıları ("dogrulandi / celiskili / dogrulanamadi"), okunamayan kaynaklar, çelişkiler, turist vergisi keşfinin sonucu, beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-06 bitti, dal gorev-06-referanslar, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
