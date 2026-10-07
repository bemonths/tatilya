GÖREV-02 — Karar düzeni, bakım ve ilk video için kaynak keşfi

BAĞLAM
GÖREV-01 kabul edildi. Bu görev iki bölümden oluşur. A bölümü kısa bir düzen ve bakım işidir: devir dalı main'e alınır, karar yetkisi kuralları güncellenir, küçük belge ve CI düzeltmeleri yapılır. B bölümü asıl iştir: kanalın ilk videosu için gereken veri kaynaklarını bulup değerlendirmek. B bölümünde kod yazılmaz.

Karar düzeni değişti: kullanıcı, makale (video metni) aşamasına kadar karar mekanizması değildir. Teknik kararlar ve main'e alma kararı proje yöneticisine aittir. Bu görev metni, devir-claude-code dalının main'e alınması için yöneticinin açık kararıdır.

KESİN SINIRLAR
- data/ klasörüne dokunma. Gerçek veritabanını açma.
- studio/ altındaki uygulama kodunu, testleri ve şemayı değiştirme.
- main'e yalnız A1 adımındaki fast-forward ile dokun. Tag oluşturma.

==================================================
A BÖLÜMÜ — DÜZEN VE BAKIM
==================================================

A1 — Devir dalını main'e al
main'i origin/devir-claude-code (d41a48ec400a90ab52987353218cf264fec92605) konumuna fast-forward ile getir (git merge --ff-only) ve main'i push et. Fast-forward mümkün değilse dur, hiçbir şeyi zorlamadan rapora yaz. main üzerindeki CI sonucunu rapora ekle.

A2 — Yeni dal
Güncel main'den "gorev-02-kaynak-kesfi" adında dal aç. A ve B bölümünün bütün commit'leri bu dala gider.

A3 — Karar yetkisi kurallarını güncelle
Aşağıdaki yerlerde "kullanıcı onayı / kullanıcı kabulü / kullanıcının manuel testi" geçen kuralları yeni düzene göre yeniden yaz. Yeni düzenin özü şudur: teknik kararları ve main'e alma kararını proje yöneticisi verir; Claude Code main'e yalnız görev metni açıkça istediğinde alır; kullanıcı makale aşamasına kadar karar vermez ve ondan onay ya da manuel test istenmez; gerçek ortamda yapılması gereken arayüz ve canlı kontrolleri Claude Code kendisi yapar (gerekirse ekran görüntüsüyle).
Değişecek yerler:
- CLAUDE.md, "Çalışma düzeni" bölümündeki main'e alma cümlesi.
- CALISMA_MANTIGI.md, 13. bölümdeki 7. ve 8. maddeler ve bölümün son cümlesi; 15. bölümdeki 11. kural.
- docs/DEVIR/04_GELISTIRME_TEST_RELEASE_AKISI.md: çalışma modeli akışındaki manuel kabul ve merge satırları, "Branch disiplini" altındaki "kullanıcı kabulü" maddesi, "Kullanıcı manuel testleri" bölümü (Claude Code'un kendi gerçek ortam kontrolü olarak yeniden yaz) ve kontrol listesindeki "user critical smoke" maddesi.
- docs/DEVIR/06_ROADMAP_VE_ACIK_KONULAR.md, en üstteki "Kullanıcı onayı olmadan yeni domain seçilmiş sayılmaz" cümlesi (yönetici kararı olarak).
- docs/DEVIR/07_YENI_AI_BASLANGIC_TALIMATI.md, "Main'e merge" bölümündeki cümle.
Bu yerlerin dışında belge metnini değiştirme.

A4 — Konaklama kararını kaydet
CALISMA_MANTIGI.md 10. bölümün sonuna ve docs/DEVIR/06_ROADMAP_VE_ACIK_KONULAR.md içindeki "Şu anki açık konu: lodging" bölümünün başına şu kararı tarihli bir not olarak ekle (anlamını koruyarak kendi cümlelerinle yazabilirsin):
"7 Ekim 2026 yönetici kararı: Tarihten bağımsız tam konaklama envanteri şartı kaldırıldı; içerik için gerekli değildir. Konaklama, belirli tarihler için yapılan Book>Direct aramalarının etiketli anlık görüntüleri olarak modellenecek (arama tarihi, giriş/çıkış tarihi, misafir sayısı, mahalle filtresi, dönen kayıtlar ve kaynağın verdiği fiyat alanları). Bu veri hiçbir yerde tam envanter diye adlandırılmayacak."
15. bölümdeki 12. kural (tarihli sonucu tam envanter diye modelleme) geçerli kalır.

A5 — Belge bağlantıları
- docs/TEKNIK-CALISMA-MANTIGI-v0.6.md içindeki 6 kırık göreli bağlantıyı düzelt (belge artık docs/ içinde). Metnin geri kalanına dokunma.
- docs/M2-VERI-TOPLAMA.md ve docs/MIMARI.md içinde teknik ayrıntı için CALISMA_MANTIGI.md'ye verilen bağlantıları docs/TEKNIK-CALISMA-MANTIGI-v0.6.md'ye çevir.
- CALISMA_MANTIGI.md 16. bölümdeki belge indeksine docs/KONSEPT.md, docs/TEKNIK-CALISMA-MANTIGI-v0.6.md ve docs/gorevler/ klasörünü ekle.

A6 — CI bakımı
.github/workflows/tests.yml içinde runs-on değerini ubuntu-24.04 olarak sabitle (ubuntu-latest 19 Ekim'de Ubuntu 26'ya geçiyor). actions/checkout, actions/setup-python ve actions/setup-node'u Node.js 24 ile çalışan güncel ana sürümlere yükselt; sürümleri GitHub'daki resmî sürüm sayfalarından doğrula ve rapora yaz. Python 3.12 ve Node 22 ayarları aynı kalsın.

A7 — Commit
A3–A6'yı tek commit olarak gorev-02-kaynak-kesfi dalına ekle, push et ve CI sonucunu bekle. İki yerel test komutu da geçmeli.

==================================================
B BÖLÜMÜ — İLK VİDEO İÇİN KAYNAK KEŞFİ
==================================================

AMAÇ
Kanalın ilk videosu "30A'ya ilk kez gidecekler için tam karar rehberi" olacak (İngilizce video). İzleyici videonun sonunda 30A'nın hangi parçasının kendisine uygun olduğunu, ne zaman gitmesi gerektiğini, yaklaşık ne harcayacağını ve oraya gidince neyle karşılaşacağını bilmeli. Bu videonun her iddiası güvenilir bir kaynağa dayanmalı. Senin işin, aşağıdaki soru alanları için en iyi kaynağı bulmak ve programa bağlanmaya uygun olup olmadığını değerlendirmek. Veri toplayıcı yazmıyorsun; hangi veriyi hangi sırayla bağlayacağımıza yönetici bu keşfin sonucuna göre karar verecek.

Bu bir planlama girdisidir; orantılı tut. Her alan için en fazla üç aday kaynağa bak. İyi bir resmî kaynak doğruladığında o alanda dur. Kaynak bulamazsan "bulunamadı" yaz ve devam et. M6 konaklama keşfindeki gibi derin araştırmaya girme.

SORU ALANLARI
1. Mahalleler: 30A hangi mahallelerden oluşuyor, batıdan doğuya sırası ne, her birinin resmî tanımı ve karakteri ne (planlı topluluk mu, eski yerleşim mi, sakin mi, yürünebilir mi)? Programdaki 13 kanonik mahalle ile kaynaktaki mahalle listesi nerede ayrışıyor?
2. Plaj erişiminin mahalleye bağlanması: Programdaki 53 halka açık plaj erişimi hangi mahallede? Hangi mahallelerde resmî listede halka açık erişim yok? Erişim başına mahalleyi doğrudan veren resmî bir kaynak var mı (örneğin Walton County coğrafi veri katmanları, ilçenin plaj erişim haritası, Visit South Walton mahalle sayfaları)? OpenStreetMap'teki topluluk sınırları kullanılabilir mi?
3. Plaj kuralları ve güvenlik: bayrak sistemi, cankurtaran sezonu ve saatleri, köpek, alkol, cam, çadır/şemsiye, ateş ve gece kuralları, eşyaların gece bırakılmaması, özel plaj ve halka açık plaj ayrımı. Resmî kaynak (Walton County mevzuatı, South Walton Fire District, Visit South Walton).
4. İklim: aylara göre ortalama hava sıcaklığı, yağış, nem ve deniz suyu sıcaklığı. Adaylar: NOAA NCEI 1991–2020 iklim normalleri (30A'ya en yakın uygun istasyon), NCEI kıyı suyu sıcaklığı rehberi, NOAA NDBC şamandıra ve istasyonları.
5. Kasırga riski: aylara göre tarihsel tropikal fırtına ve kasırga sıklığı. Adaylar: NOAA HURDAT2, IBTrACS, NHC iklim istatistikleri.
6. Kalabalık ve sezon: aylara göre ziyaretçi yoğunluğunu gösteren resmî bir gösterge. Adaylar: Florida Department of Revenue'nun ilçe bazında aylık turizm vergisi verileri, Walton County turizm vergisi tahsilatları, Visit South Walton yıllık raporları (doluluk, ziyaretçi sayısı).
7. Konaklama ve fiyat: mahalleye göre seçenek sayısı ve gecelik fiyat aralığı, sezona göre fark. Bilinen kaynak Book>Direct tarihli aramasıdır (docs/M6-KONAKLAMA-KAYNAK-KEŞFİ.md). Envanter araştırması yapma; şunları netleştir: average_rate ve diğer fiyat alanlarının anlamı (para birimi, vergi/ücret dahil mi, gecelik mi, kaç gece için), rates.json ve live_rates.json servislerinin ne döndürdüğü, misafir sayısı parametresi, minimum konaklama alanları. Sezonları temsil edecek örnek tarih seti öner (yaz zirvesi, bahar tatili, sonbahar, kış). Kaynak scriptindeki istemci anahtarını hiçbir dosyaya yazma.
8. Ulaşım: en yakın havalimanları ve 30A'ya uzaklıkları, araba gerekli mi, Timpoochee bisiklet yolu, golf arabası/LSV kuralları, otopark (bölgesel erişimlerde ve planlı topluluklarda ücretli mi). Adaylar: havalimanlarının resmî siteleri, Walton County, Visit South Walton ulaşım dizini (programda kaynak kaydı var), OpenStreetMap.
9. Yapılacaklar: devlet parkları (Grayton Beach, Topsail Hill Preserve, Deer Lake, Point Washington State Forest) ücret ve saatleri, kıyı kumul gölleri, etkinlik takvimi. Adaylar: Florida State Parks, Florida Forest Service, Visit South Walton etkinlikler sayfası (programda kaynak kaydı var), Book>Direct venues servisi.
10. Günlük ihtiyaç: market ve eczaneye mahallelere göre erişim. Adaylar: OpenStreetMap (Overpass), Overture Maps.

HER ADAY KAYNAK İÇİN DEĞERLENDİRME
Projenin kaynak kabul süreci docs/DEVIR/03_VERI_KAYNAKLARI_VE_DOGRULAMA.md içindedir; ona göre, kısa tut:
- kaynak adı, URL, sahibi ve otoritesi
- hangi soruya cevap veriyor, hangi alanları veriyor
- verinin anlamı ve sınırı (tam liste mi, örnek mi, tarihli mi, tahmin mi)
- teknik yol (API, CSV/JSON indirme, HTML, PDF) ve kararlı kimlik var mı
- güncellenme sıklığı ve kaynakta güncelleme tarihi var mı
- kullanım/lisans notu (atıf gerekiyor mu, robots.txt veya kullanım şartı engel mi)
- küçük bir örnek istek ve sonucunun özeti
- değerlendirme: kullanılabilir / sınırlı / kullanılamaz, tek cümle gerekçe
Örnek istekleri az ve nazik tut (repo adresini içeren User-Agent), giriş gerektiren hiçbir yere girme. Ham örnekleri work/gorev-02/ altına kaydet; repoya koyma.
Bir kaynak plaj erişimi başına mahalleyi doğrudan veriyorsa, programdaki 53 erişim için docs/gorevler/GOREV-02/plaj-mahalle-onizleme.csv dosyası çıkar (external_id, ad, kaynağın verdiği mahalle, kaynak). 53 erişimin güncel listesi docs/gorevler/GOREV-01/plajlar.csv dosyasındadır. Kaynağın vermediği eşlemeyi tahmin etme; boş bırak.

B ÇIKTILARI
- docs/gorevler/GOREV-02/KAYNAK-KESFI.md: her soru alanı için ayrı başlık, aday kaynakların değerlendirmesi ve alanın sonucu. En sonda senin önerdiğin bağlama sırası ve gerekçesi (karar yöneticinindir).
- docs/gorevler/GOREV-02/kaynaklar.csv: soru_alani, kaynak_adi, url, sahibi, yontem, kararli_kimlik, guncelleme, degerlendirme, not.
- Varsa docs/gorevler/GOREV-02/plaj-mahalle-onizleme.csv.

==================================================
TESLİM
==================================================
docs/gorevler/GOREV-02/RAPOR.md dosyasını Türkçe yaz: A bölümünün her adımının sonucu (main'in yeni konumu, CI sonuçları, güncellenen action sürümleri), B bölümünün kısa özeti, beklenmedik durumlar ve yöneticinin karar vermesi gereken konular. Görev metnini work/gorevler/GOREV-02.md'den docs/gorevler/GOREV-02/GOREV.md olarak kopyala.
docs/gorevler/GOREV-02/ klasörünü ikinci commit olarak gorev-02-kaynak-kesfi dalına ekle ve push et. Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-02 bitti, dal gorev-02-kaynak-kesfi, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
