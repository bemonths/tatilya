GÖREV-07 — v0.9.0 yayını, kısıtlayıcı kuralların kaldırılması, referans tablosunun tamamlanması ve konaklama profili

BAĞLAM
GÖREV-06 kabul edildi. Ancak görevin ilk sürümü uygulandı; kullanıcının sonradan verdiği karar o sürümde yoktu. Kullanıcının kararı şudur: Bu programın amacı, tatile gelecek kişinin yer seçimi için ihtiyaç duyduğu bilgiyi eksiksiz vermektir. Bilgiyi biz toplayıp sunarız, karar izleyicinindir. Eksik bilgi verilmez. Bilgiye ulaşmayı temkin gerekçesiyle engelleyen kurallar geçerli değildir.

Bu görevde dört iş var: v0.9.0 main'e alınıp etiketlenecek; repodaki bilgiye erişimi kısıtlayan kurallar kaldırılacak; referans tablosunda bu kurallar yüzünden eksik kalan satırlar tamamlanacak; yer seçiminin en büyük eksiği olan konaklama profili için yeni bir toplayıcı yazılacak.

Kullanıcı bu görev için main'e alma, etiket, gerçek veritabanını normal kullanımla güncelleme ve görevin gerektirdiği sitelere tarayıcıyla girme iznini kendi mesajında açıkça veriyor.

KESİN SINIRLAR
- data/ yalnız Adım 6'da, CLAUDE.md kuralına göre (önce tam yedek, sonra uygulamanın normal kullanımı) değişir.
- main'e yalnız Adım 1'deki fast-forward ile dokun; yalnız Adım 1'deki etiketi koy.

==================================================
ADIM 1 — v0.9.0'ı main'e al ve etiketle
==================================================
main'i origin/gorev-06-referanslar (7110f88) konumuna git merge --ff-only ile getir ve push et. Bu commit'e "v0.9.0" açıklamalı etiketini koy (mesaj: "v0.9.0 — kasırga evre kuralı ve referans tablosu") ve push et. Etiket zaten varsa dur ve rapora yaz. main CI sonucunu rapora ekle. Güncel main'den "gorev-07-konaklama" dalını aç.

==================================================
ADIM 2 — Bilgiye erişimi kısıtlayan kuralların kaldırılması
==================================================
Yeni ilke (CALISMA_MANTIGI.md 4. bölümdeki ilgili maddelerin yerine ve CLAUDE.md'ye yaz):
"Amaç, ziyaretçinin karar vermesi için gereken bilgiyi eksiksiz toplamaktır. Herkese açık yayımlanmış her bilgi alınabilir: resmî siteler, işletmelerin kendi siteleri, menüler, PDF'ler, harita ve veri servisleri. Gerekirse gerçek tarayıcıyla (Playwright ve bilgisayardaki Chrome veya Edge) okunur; robots.txt ve bot doğrulaması tek başına engel sayılmaz. İstekler siteyi yormayacak hızda yapılır; her bilginin kaynağı, erişim tarihi ve ham kopyası saklanır. Giriş gerektiren hesaplara girilmez, ücretli içerik aşılmaz. Doğruluk kuralları aynen geçerlidir: kaynağın söylemediği şey yazılmaz, hesaplanan ya da türetilen değer öyle etiketlenir."

Bilinen kısıtlayıcı kurallar (değiştir veya kaldır):
- CALISMA_MANTIGI.md 4. bölüm 13. madde (Playwright varsayılan değildir) → "İlk tercih API, JSON ve HTML'dir; gerekiyorsa tarayıcı otomasyonu kullanılır." (yalnız verimlilik tercihi)
- CALISMA_MANTIGI.md 4. bölüm 14. madde (robots.txt kuralı) → yukarıdaki yeni ilke.
- docs/DEVIR/03: "connector işletmenin sitesini crawl etmez" ve anti-pattern listesindeki "External site URL'sini otomatik crawl etme" → kaldır. Yerine: işletmenin sitesi, dizindeki bağlantıyla kimliği belli olduğu için doğrudan okunabilir.
- docs/DEVIR/06: restoran zenginleştirmesinin önüne entity matching, menü sürümleme ve fiyat anlamı tasarımını şart koşan ifade; market/günlük harcama ve POI verisini caydıran ifadeler → kaldır; yerine kısa bir "yapılabilir, kaynak ve tarihle" notu.
- docs/DEVIR/07 "Şu an senden beklenmeyenler" bölümü: güncelliğini yitirmiş yasakları kaldır; yalnız gerçekten geçerli olanları bırak (ör. production veritabanını sıfırlamamak).
- docs/M9-REFERANS-TABLOSU.md ve GÖREV-06'daki "bot korumalı sayfa otomasyonla aşılmaz", "başka mevzuat aranmadı" türü politika ifadeleri; GÖREV-02 ve M8'deki "robots.txt kapalı olduğu için kullanılmadı / bot korumalı olduğu için kullanılamaz" türü değerlendirmeler → yeni ilkeye göre güncelle (eski metni silme, tarihli karar notu düş).
Bunların dışında CLAUDE.md, CALISMA_MANTIGI.md, README.md, docs/DEVIR/*, docs/M*.md ve docs/ASAMALAR.md içinde aynı türden başka kural varsa onları da bul ve düzelt. Veri doğruluğu, veri güvenliği (data/ klasörü, yedek), test ve git kuralları bu kapsamda değildir.
Raporda değiştirdiğin her kuralın eski ve yeni halini kısa bir tabloyla ver. Bu adımı ayrı bir commit olarak at.

==================================================
ADIM 3 — Referans tablosunun tamamlanması
==================================================
Yeni ilkeyle şunları yap. Bot doğrulamalı sayfalar için Playwright'i bilgisayardaki Chrome veya Edge ile (channel="chrome" veya "msedge"; gerekiyorsa görünür pencereyle) kullan. Her yeni belgeyi work/referans-belgeler/ altına SHA-256 ile kaydet.
- Parklar: Grayton Beach, Topsail Hill Preserve ve Deer Lake State Park giriş ücreti ve saatleri (Florida State Parks "hours-fees" sayfaları). "dogrulanamadi" satırlarını doğrulanmış değerle değiştir.
- Plajda alkol: Walton County Code'un diğer bölümlerinde, ilçenin resmî sayfalarında ve Florida mevzuatında 30A plajlarında alkolle ilgili geçerli kuralı bul.
- Cankurtaran: 2026 sezonunun güncel resmî bilgisini bul (South Walton Fire District duyuruları, 2026 sezon açıklamaları, ilçe bütçe veya sözleşme belgeleri). Güncel resmî değeri "dogrulandi" yaz; eski çelişkili satırları silme, durumlarını "yerine_gecildi" yap ve notta hangi satırın yerine geçtiğini yaz. (Doğrulayıcıya bu yeni durumu ekle.)
- Timpoochee Trail uzunluğu: Walton County'nin (yolu yöneten kurum) resmî değerini bul; çelişkiyi aynı yöntemle çöz.
- 2025 ziyaretçi sayısı: yönetici kararı — raporun tabloları esas alınır. "ziyaretci-2025-ozet" (4.586.000) "dogrulandi", "ziyaretci-2025-ekonomik-etki" "yerine_gecildi" olur; notta gerekçe.
- Golf arabası ve düşük hızlı araç: Walton County'nin 30A ve çevresindeki yollar için golf arabası belirlemesi (varsa hangi yollar) ve 30A'nın hız limitleri.
- Planlı toplulukların ziyaretçi otoparkı: Seaside, Rosemary Beach, Alys Beach, WaterColor ve WaterSound'un kendi resmî sitelerinde ziyaretçi otoparkı, ücretleri ve plaja erişimle ilgili ziyaretçi bilgisi.
Raporda bu adımın sonunda konu başına satır ve durum sayılarını yeniden ver.

==================================================
ADIM 4 — Konaklama profili toplayıcısı (Book>Direct)
==================================================
Amaç: her mahallede ne tür konaklama olduğunu (ev, daire, otel vb.), büyüklüklerini ve bulunabildiği kadar fiyat seviyesini vermek. Kaynak, Visit South Walton'ın resmî "Stay" ön yüzünün kullandığı Book>Direct servisleridir (ayrıntı: docs/M6-KONAKLAMA-KAYNAK-KEŞFİ.md ve docs/gorevler/GOREV-02/KAYNAK-KESFI.md Alan 7). 7 Ekim kararı geçerlidir: bu veri belirli tarihlerdeki aramaların etiketli anlık görüntüsüdür, hiçbir yerde tam envanter denmez.

Tasarım:
- Genel bir toplayıcı yaz (Book>Direct başka turizm kurumlarınca da kullanılıyor); destinasyona özel olanlar (clone adresi, konum filtrelerinin kanonik mahallelere eşlemesi, örnek tarih pencereleri) SQLite'taki destinasyon yapılandırmasından gelir. 30A için ilk değerleri profil ve migration yazar.
- Herkese açık istemci anahtarı her çekimde ön yüzün güncel paketinden okunur; hiçbir dosyaya, veritabanına, ham kayda veya günlüğe yazılmaz. Paketin sürüm yolu giriş HTML'inden çözülür.
- Konum filtreleri show.json'dan okunur; 13 kanonik mahalle adla eşlenir (Watercolor/Watersound yazımları dahil). "Seagrove Beach" filtresi de seagrove'a bağlanır ve hangi filtreden geldiği kayıtta saklanır.
- 30A örnek tarih pencereleri (Cumartesi–Cumartesi, 7 gece): 2026-10-17→2026-10-24, 2027-01-16→2027-01-23, 2027-03-13→2027-03-20, 2027-07-10→2027-07-17. Pencereler yapılandırmada durur; geçmiş tarihli pencere atlanır ve kayda yazılır.
- Her pencere × her mahalle filtresi için lodgings.json'un bütün sayfaları okunur. İlan başına saklanacaklar: kimlik, ad, kategori adları, konum filtresi, adres, koordinat, yatak odası, banyo, kapasite (sleeps), olanaklar, rezervasyon sistemi, average_rate, para birimi, los, live_rates_enabled, min_stays.
- Canlı fiyatı olan ilanlar için live_rates.json, ön yüzün yaptığı gibi sınırlı sayıda denemeyle sorulur; dönen fiyat ve durum saklanır.
- Görülen her benzersiz ilan için rates.json fiyat takvimi bir kez okunur. Ham günlük değerler veritabanına yazılmaz; ilan başına ay ay özet saklanır: fiyatı olan gün sayısı, en düşük, ortanca ve en yüksek gecelik fiyat, en sık görülen los.
- İstekler sıralı ve siteyi yormayacak hızda (yaklaşık 1–1,5 sn arayla). Çekim uzun sürebilir; ilerleme ve iptal doğru çalışmalı. Ham yanıtlar SHA-256 ile saklanır (gerekirse sıkıştırılarak).
- Şema 10, uygulama 0.10.0; migration mevcut kurallarla.

Okuma anında hesaplanacak özet (mahalle × pencere): ilan sayısı, kategori dağılımı, yatak odası dağılımı (ortanca ve 4+ odalı payı), kapasite ortancası, fiyat bilgisi olan ilanların payı ve kaynağı (liste / canlı / takvim), fiyatı olan ilanlarda gecelik fiyatın ortancası ve çeyrekler aralığı. Ayrıca mahalle başına takvimden aylık ortanca gecelik fiyat. Her özetin altında "şu tarihte yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor" etiketi.

Arayüz: Veri toplama ekranına "Konaklama" sekmesi: toplama düğmesi, sürüm seçimi, mahalle × pencere özet tablosu, mahalle seçilince ilan listesi ve ayrıntısı.

Testler (fixture ve MockTransport; canlı ağ yok): anahtarın paketten çözülmesi ve hiçbir çıktıya yazılmaması, konum eşlemesi (Seagrove Beach dahil), sayfalama, geçmiş pencerenin atlanması, live_rates denemeleri, rates.json özetleri, boş fiyat alanları (NULL), iptal, atomik geri alma, migration ve geri alma, destinasyon yalıtımı.

Belge: docs/M10-KONAKLAMA-PROFILI.md (kaynak, yöntem, alanların anlamı, sınırlar, video dili).

==================================================
ADIM 5 — Belgeler ve testler
==================================================
CALISMA_MANTIGI.md, README.md, docs/DEVIR/05 ve 02'nin güncel durum satırları. Tam test takımı yerelde art arda en az 3 kez geçmeli.

==================================================
ADIM 6 — Gerçek ortam
==================================================
1. Geçici klasörde canlı deneme (work/gorev-07/temp-data): konaklama toplayıcısını çalıştır; süreyi, istek sayısını ve sonuçları rapora yaz; Konaklama sekmesinin ekran görüntüsünü al.
2. Migration denemesi gerçek verinin kopyasında (v9 → v10).
3. Gerçek veritabanı, CLAUDE.md kuralına göre: data/ tam yedeği; uygulamayı gerçek veriyle aç; konaklama toplayıcısını çalıştır; kapat; satır sayıları, integrity_check ve foreign_key_check.

==================================================
TESLİM
==================================================
docs/gorevler/GOREV-07/ altına: GOREV.md (work/gorevler/GOREV-07.md'nin kopyası), RAPOR.md, güncel referans tablosunun kopyası, konaklama-ozet.csv (gerçek veritabanındaki çekimden mahalle × pencere özeti), konaklama-aylik-fiyat.csv (mahalle × ay takvim özeti) ve ekran görüntüleri (Konaklama sekmesi, Referanslar sekmesi).
RAPOR.md Türkçe ve sade: her adımın sonucu, main ve etiketin konumu, CI sonuçları, test sayıları, kaldırılan/değiştirilen kuralların tablosu, referans tablosunda çözülen ve kalan konular, konaklama çekiminin sonuçları (mahalle başına ilan sayısı, kategori dağılımı, fiyat bilgisi olan ilan payı ve fiyat özetleri), beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-07 bitti, dal gorev-07-konaklama, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
