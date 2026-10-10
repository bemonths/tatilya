GÖREV-12 — v0.14.0 yayını ve kanıt paketinin yazıma hazır hale getirilmesi (temiz sayı listesi, yazar özeti)

BAĞLAM
GÖREV-11 kabul edildi. Kanıt paketi doğru kuruldu ve verisi iyi, ama bu haliyle makale yazımına ve okumaya uygun değil. İlk video paketi 924 KB ve bunun 510 KB'ı (%55) sayı kontrol listesi. Liste ifade metnindeki her rakamı ayıklıyor: "30A"daki 30, FDOT yol numarası 60660100, sokak numarası 4200 sayı diye listelenmiş; 3.003 satırın büyük kısmı gürültü. Konaklama bölümü 156 satırlık düzyazı (103 KB), oysa aynı bilgi tek bir mahalle × ay tablosunda birkaç KB. Aynı not satır satır tekrar ediyor. Çeyrekler ve "1 mil içindeki ilan payı" gibi değerler yalnız ifade metninin içinde, ayrı alan olarak yok.

Sıradaki aşama makale. Makaleyi yazan ve sayıları kontrol eden taraf kısa ve düzenli bir metinden çalışmalı. Bu görevin işi:
A. v0.14.0'ı main'e almak.
B. Sayı kontrol listesini temizlemek ve ayrı bir CSV dosyasına almak.
C. Her paketle birlikte üretilen bir "yazar özeti" eklemek: aynı bölümler, aynı K kimlikleri, sayısal bloklar tablo halinde, kullanım notları blok başına bir kez.
Tam paket (Markdown + JSON) asıl kanıt olarak aynen kalır; yazar özeti ondan türetilir.

Bu görevde canlı veri çekimi yok; hiçbir toplayıcı çalıştırılmaz. Gerçek veritabanı yalnız Adım 5'te iki paketin yeniden üretilmesiyle değişir.

Kullanıcı bu görev için main'e alma, etiket ve gerçek veritabanını normal kullanımla güncelleme iznini kendi mesajında açıkça veriyor. Bilgisayarda zamanlanmış görev oluşturulmaz.

KESİN SINIRLAR
- data/ yalnız Adım 5'te, CLAUDE.md kuralına göre (önce tam yedek, sonra uygulamanın normal kullanımı) değişir. Toplayıcı çalıştırılmaz.
- main'e yalnız Adım 1'deki fast-forward ile dokun; yalnız Adım 1'deki etiketi koy.
- Yazar özeti de paket gibi yorum, tavsiye ya da sıralama içermez. Değere göre sıralama yapılmaz; mahalleler paketteki sırayla (batıdan doğuya) yazılır.
- Yazar özetindeki her değer paketteki değerin aynısıdır; özet veritabanından ayrıca sorgulanmaz, aynı üretimin paket nesnesinden yazılır.
- Paketteki hiçbir kanıt satırı özetten sessizce düşmez: her K kimliği özette ya kendi satırıyla ya da bir tablo satırının kimlik aralığıyla görünür.

==================================================
ADIM 1 — v0.14.0'ı main'e al ve etiketle
==================================================
Önce origin/gorev-11-kanit-paketi'nin son commit'i (9adc235) için GitHub Actions sonucunu kontrol et; başarısızsa önce düzelt, düzeltmeyi dala ekle ve bu adımı o commit'le yap. Sonra main'i bu dala git merge --ff-only ile getir ve push et; son commit'e "v0.14.0" açıklamalı etiketini koy (mesaj: "v0.14.0 — kanıt paketi, büyük süpermarket ayrımı, resmî acil sağlık noktaları ve izleyici sorularından gelen referanslar") ve push et. main ve etiket CI sonucunu rapora ekle. Güncel main'den "gorev-12-yazar-ozeti" dalını aç.

Yönetici kararları (GÖREV-11 raporundaki sorulara); belgelere işle:
1. Bölge kutusu dışındaki acil servis (Ascension, Panama City Beach) kabul. Kural M13'e yazılır: en yakın resmî acil servis bölge kutusunun dışındaysa notuyla eklenir.
2. HCA Florida ve CVS "bu bilgisayardan okunamadı" olarak kalır; başka yol denenmez.
3. Küçük örnek eşiği (pencere başına 20 fiyatlı ilan) uygun.
4. Okul bölgesi seçimi "bizim seçimimiz" etiketiyle kabul. Okul tatili satırlarının kullanım notuna şu eklenir: "Video dilinde 'örneğin Atlanta bölgesindeki Gwinnett County okulları' denir; resmî öğrenci sayısıyla doğrulanmadıkça 'en büyük okul bölgesi' denmez."
5. Plaj hukuku satırları her video yayımlanmadan önce yeniden kontrol edilir (Adım 4c'deki liste bunun için).
6. Paket boyutu bu görevde çözülüyor.
7. main ve etiket bu adımda.

==================================================
ADIM 2 — Sayı kontrol listesini temizle
==================================================
2a. Sayı listesi yalnız yapılandırılmış alanlardan üretilir; ifade metninden rakam ayıklanmaz. Bir satırın listeye giren sayıları:
- ana değer (deger),
- satırın yapılandırılmış ek değerleri: çeyrekler, örnek büyüklüğü, "1 mil içindeki ilan payı" gibi paylar, aralık uçları,
- birim dönüşümü (°C, km, mm karşılığı) ayrı türle.
Şu an yalnız ifade metninde duran ek değerler (ör. konaklamada çeyrekler, günlük ihtiyaçta 1 mil içindeki pay) veri bloğunda ayrı alan olarak üretilir ve JSON satırına eklenir (ör. "ek_degerler": [{"tur": "alt_ceyrek", "deger": 2240, "birim": "USD (7 gece)"}, …]). İfade metni değişmez.

2b. Adlardaki, adreslerdeki, yol ve kimlik numaralarındaki ve dönem adlarındaki rakamlar (30A, US 98, CR 395, 4200 Indian Bayou Trail, 60660100, 1991–2020, Ordinance 2016-23 gibi) listeye girmez. Referans satırlarında listeye yalnız referans tablosunun deger alanı girer; ifade metnindeki diğer sayıların kontrolü satır metninin kendisine karşı yapılır (M14'e yaz).

2c. Liste Markdown paketin sonundan çıkar ve ayrı dosya olur: "<paket>-sayilar.csv" (sütunlar: kanit, tur [ana / alt_ceyrek / ust_ceyrek / orneklem / pay / aralik_alt / aralik_ust / donusum], deger, birim, etiket). Markdown paketin sonunda yalnız bu dosyanın adı ve satır sayısı yazar. JSON paket listeyi yeni biçimde taşır. CSV de aynı üretimle, aynı yerde, SHA-256'sıyla saklanır ve "Kanıt paketi" ekranından indirilebilir.

2d. Markdown pakette bir bloktaki bütün satırlarda aynı olan her alan (kaynak, kullanım notu, etiket, not, kapsam) blok başında bir kez yazılır; satırda yalnız farklı olan alanlar kalır. Bu genel bir kuraldır, bloğa özel kod yazılmaz. JSON satırları tam kalır.

==================================================
ADIM 3 — Yazar özeti
==================================================
3a. Ne: her paket üretiminde paketle birlikte üretilen, makaleyi yazan ve sayıları kontrol eden tarafın çalışacağı kısa Markdown dosyası: "<paket>-yazar-ozeti.md". Aynı üretim kimliğiyle, aynı yerde (data/evidence/), SHA-256'sıyla saklanır ve "Kanıt paketi" ekranından indirilir. Dil Türkçe (paketle aynı); değerler paketteki gibi ABD birimleriyle.

3b. Başlık bölümü (kısa):
- paketin adı, ana sorusu, üretim tarihi ve üretim kimliği; "Bu özet tam paketten türetilmiştir; asıl kanıt tam pakettir; kimlikler aynıdır" cümlesi,
- kaynakların son çekimi, kaynak başına tek satır (ad, tarih, zamanı geldi mi),
- bilinen boşluklar (paketteki gibi),
- "Yayından önce kontrol edilecek satırlar" (Adım 4c),
- etiket kısaltmaları: [KG] kaynak gerçeği, [BH] bizim hesabımız, [T] türetilmiş, [Y] yaklaşık; "—" veri yok; "*" küçük örnek.

3c. Bölümler paketteki sırayla ve aynı başlıklarla. Her bloğun kullanım notu blok başında bir kez ve aynen yazılır (M belgesinden gelen not kısaltılmaz; video dilinin sınırını o taşıyor).

3d. Sayısal seri blokları tablo olur. Her tablo satırının sonunda o satırın K kimlik aralığı yazar; tablo başlığında etiket, kaynak adı, sorgu tarihi ve örnek büyüklüğü kuralı bir kez yazar. Blok başına tablo biçimi:
- lodging_prices: mahalle × ay; hücre "ortanca (n)". İkinci tablo aynı düzende çeyrekler ("alt–üst"). Küçük örnek hücreleri "*" ile. Alys Beach satırı ayrı etiketli (şirketin kendi envanteri).
- lodging_bedrooms: mahalle × (dönem × oda grubu); hücre "ortanca (n)".
- lodging_inventory: mahalle × pencere; ilan sayısı.
- climate_months: ay × ölçü (istasyon ve dönem başlıkta); °F ve yanında °C.
- sea_water: ay satırı; °F ve °C; yıl sayısı.
- storms, tdt_season, traffic, beach_accesses, beach_features, neighborhoods: bloğun doğal düzeninde küçük tablolar (ör. tdt_season ay satırı; traffic sayım noktası × değer ve kategori × ay oranı; neighborhoods mahalle × kaynağın etiketleri).
- restaurants: mahalle × (restoran sayısı, fiyat seviyesi dağılımı, rezervasyon ve çocuk menüsü sayıları gibi bloğun taşıdığı ölçüler); ardından fiyat seviyesi olan restoranların listesi (ad, mahalle, seviye), paketteki sırayla.
- daily_needs: mahalle × ölçü (büyük süpermarket, yerel market, eczane, acil servis, acil bakım için ortanca kuş uçuşu mil ve 1 mil içindeki pay; n).
Örnek biçim (gerçek veriden, ilk iki satır):

| Mahalle | Kas 2026 | Ara 2026 | Oca 2027 | … | Tem 2027 | … | Kimlik |
|---|---|---|---|---|---|---|---|
| Dune Allen | $3,091 (30) | $3,091 (46) | $3,080 (35) | … | $5,608 (46) | … | K0281–K0292 |
| Gulf Place | $1,939 (8)* | $2,013 (14)* | $1,944 (12)* | … | $4,803 (15)* | … | K0293–K0304 |

3e. Referans satırları ve tablo dışında kalan satırlar tek satır olur: "- K0001 [KG] <Türkçe ifade> — <değer birim>". Altında yalnız varsa: not, çelişki notu, "ikincil kaynak" işareti, örnek büyüklüğü. URL, SHA-256, çekim kimliği, kısa alıntı ve İngilizce ifade özete girmez (tam pakette duruyor). Doğrulanamadı durumundaki satırlar "videoda kullanılmaz" işaretiyle kalır.

3f. Sonunda tek bir kaynak listesi: her kaynak bir kez (ad, sahibi, url) ve hangi K kimliklerini taşıdığı (aralık olarak). Video açıklamasındaki kaynak listesi buradan çıkacak.

3g. Hedef boyut: ilk video yazar özeti 100 KB'ı, Rosemary Beach yazar özeti 30 KB'ı geçmez. Geçerse neyin büyüttüğünü rapora yaz; içerik düşürerek küçültme, biçimi sadeleştir.

3h. Testler (fixture ile; canlı sayı test sabiti yapılmaz): pakette olan her K kimliğinin özette görünmesi (satır ya da tablo aralığı), özetteki her sayının paketteki değerle aynı olması, "veri yok" satırlarının "—" olarak görünmesi, kullanım notunun blok başına bir kez ve aynen geçmesi, küçük örnek işaretinin eşiğe göre konması, sayı listesinde ad ve adres rakamlarının olmaması (ör. "30A" içeren ifadeden 30 çıkmaması), sayı CSV'sinin JSON listesiyle aynı olması, özetin ve CSV'nin pakete bağlı saklanması.

==================================================
ADIM 4 — Küçük düzeltmeler
==================================================
4a. Okul tatili satırlarının kullanım notu (Adım 1, karar 4) ve acil servis kuralı (karar 1) ilgili M belgelerine ve referans tablosuna işlenir.
4b. Konaklama satırlarındaki not şu an teknik bir oran yazıyor ("toplam fiyat 10050/10694 fiyatta vergileri ve sitenin gösterdiği ücretleri içerir"). Bu, blok başında bir kez ve sade yazılır: "Fiyatların %94'ünde sitenin gösterdiği toplam vergileri ve ücretleri içeriyor; kalanında sitenin toplamı kalemlerle doğrulanamadı." Oran üretim anındaki veriden hesaplanır, sabit yazılmaz.
4c. "Yayından önce kontrol edilecek satırlar": şablona bir alan eklenir (oynak konular; ilk video ve mahalle şablonunda şimdilik "plaj-hukuku"). Paketin ve yazar özetinin başında şu satırlar listelenir: şablonun oynak konularındaki referans satırları ve durumu "çelişkili" olan bütün satırlar (çelişki notuyla). Her biri için K kimliği, kısa ifade ve referans tablosundaki yeniden kontrol tarihi. Kod genel kalır; konu listesi şablonda durur.

==================================================
ADIM 5 — Gerçek ortam ve teslim
==================================================
1. Geçici klasörde deneme: gerçek verinin kopyasıyla iki paket (ilk video, Rosemary Beach); paket, yazar özeti ve sayı CSV'si birlikte üretiliyor mu, boyutlar hedefte mi.
2. Şema değişirse migration denemesi gerçek verinin kopyasında. (Beklenen: şema değişikliği gerekmez; gerekirse gerekçesini rapora yaz.)
3. Gerçek veritabanı, CLAUDE.md kuralına göre: data/ tam yedeği; uygulamayı gerçek veriyle aç; iki paketi "Kanıt paketi" ekranından yeniden üret (toplayıcı çalıştırma); kapat; satır sayıları, integrity_check ve foreign_key_check. GÖREV-11'de üretilen eski paketler silinmez.
4. Yazar özetini kendin baştan sona oku: bir yazarın tek başına çalışabileceği kadar açık mı, tablolar doğru hizalı mı, eksik blok var mı. Bulduğun sorunları düzelt ve rapora yaz.
5. Belgeler: M14 (sayı listesi kuralı, ayrı CSV, yazar özeti, oynak konular), M13, ilgili referans/M belgesi, CALISMA_MANTIGI.md, README.md, docs/DEVIR/05 ve 02'nin güncel durum satırları. Tam test takımı yerelde art arda en az 3 kez geçmeli.

TESLİM
docs/gorevler/GOREV-12/ altına: GOREV.md (work/gorevler/GOREV-12.md'nin kopyası), RAPOR.md, gerçek veriden üretilen kanit-paketi-ilk-video.md, .json, -yazar-ozeti.md ve -sayilar.csv; aynı dört dosya Rosemary Beach için; "Kanıt paketi" ekranının ekran görüntüsü.
RAPOR.md Türkçe ve sade: her adımın sonucu, main ve etiketin konumu, CI sonuçları, test sayıları, iki paketin önceki ve yeni boyutları (Markdown paket, yazar özeti, sayı CSV'si; satır ve sayı adedi), sayı listesinden çıkan gürültünün örnekleri, yayından önce kontrol edilecek satırlar listesi, yazar özetini okurken bulduğun sorunlar, gerçek veritabanının öncesi/sonrası, beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-12 bitti, dal gorev-12-yazar-ozeti, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
