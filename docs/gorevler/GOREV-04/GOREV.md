GÖREV-04 — v0.7.0 yayını, gerçek verinin güncellenmesi ve plaj–mahalle eşlemesinin ilçe verisiyle düzeltilmesi

BAĞLAM
GÖREV-03 kabul edildi: mahalle toplayıcısı, şema 7, arayüz ve testler sağlam. Eşleme katmanında ise yöntem sorunu var. Doğrulamada 9 resmî eşlemenin 8'i tuttu, ama tutanların hepsi bölgesel erişimdi ve mahalle temsilî noktalarına çok yakındı; resmî listedeki tek mahalle erişimi (Walton Dunes - 8) yanlış çıktı. Türetme 44 mahalle erişimine uygulandığı için asıl risk orada. Somut örnek: Dogwood/Thyme - 29'dan Greenwood - 21'e kadar 10 erişim "Seaside" olarak atandı. Seaside, WaterColor ve Rosemary Beach gibi planlı toplulukların temsilî noktası küçük bir kasaba merkezidir; en yakın nokta yöntemi bu yüzden komşu, daha geniş ve dağınık yerleşimlerin (ör. Seagrove) erişimlerini kolayca planlı topluluklara yazar. İlk videoda "Seaside'da şu kadar halka açık erişim var" gibi yanlış bir cümleye yol açabilir. Bu görevde eşleme, Walton County'nin resmî alt bölüm (subdivision/plat) poligonlarıyla yeniden kurulacak.

Ayrıca: v0.7.0 main'e alınıp etiketlenecek; gerçek veritabanı uygulamanın normal kullanımıyla güncellenecek (kullanıcı uygulamayı kendisi kullanmıyor; bu iş artık Claude Code'un); kararsız bir restoran testi sağlamlaştırılacak.

Kullanıcı bu görev için main'e alma, etiket ve gerçek veritabanını normal kullanımla güncelleme iznini kendi mesajında açıkça veriyor.

==================================================
ADIM 1 — v0.7.0'ı main'e al ve etiketle
==================================================
main'i origin/gorev-03-mahalleler (7f25e3ce947c69fef999f7f4454a79608008fcad) konumuna git merge --ff-only ile getir ve push et. Bu commit'e "v0.7.0" adlı açıklamalı etiket koy (mesaj: "v0.7.0 — mahalle verisi ve plaj–mahalle eşlemesi") ve etiketi push et. Etiket adı zaten varsa dur, hiçbir şeyi taşımadan rapora yaz. main üzerindeki CI sonucunu rapora ekle. Sonra güncel main'den "gorev-04-esleme-v2" dalını aç.

==================================================
ADIM 2 — Gerçek veriyi güncelleme kuralı ve uygulaması
==================================================
Kural (CLAUDE.md "Veri güvenliği" bölümüne ve CALISMA_MANTIGI.md'ye ekle): Kullanıcı uygulamayı kendisi kullanmaz. Gerçek veritabanı yalnız görev metni açıkça istediğinde ve yalnız uygulamanın normal kullanımıyla (uygulamayı gerçek veri klasörüyle açmak, arayüz veya API üzerinden toplayıcı çalıştırmak) değişir. Bundan önce uygulama kapalıyken data/ klasörünün tamamı work/yedek/<YYYYMMDD-HHMM>/ altına kopyalanır. data/ içindeki dosyalar elle değiştirilmez, silinmez, taşınmaz.

Uygulama:
1. Uygulamanın kapalı olduğunu doğrula ve data/ klasörünün tam yedeğini al; yedeğin dosya sayısı ve toplam boyutunu rapora yaz.
2. Uygulamayı gerçek veri klasörüyle aç (.venv Python'u, -X utf8, varsayılan data/ klasörü, --no-browser). Açılışta v6 → v7 yükseltmesi uygulamanın kendi yedeğiyle yapılacak; yükseltme yedeğinin adını rapora yaz.
3. Sırayla dört toplayıcıyı çalıştır: plaj erişimleri, National Weather Service, restoranlar, mahalleler. Her biri için durum, kayıt sayısı ve önceki sürüme göre fark özetini yaz.
4. Uygulamayı kapat. Tablo satır sayılarını (öncesi/sonrası), integrity_check ve foreign_key_check sonucunu yaz.

==================================================
ADIM 3 — Kararsız testin sağlamlaştırılması
==================================================
GÖREV-03'te bir kez başarısız olan test_api_raw_hash_rollback_and_previous_run testinin bekleme yardımcısını yük altında da güvenilir çalışacak şekilde düzelt (sabit kısa süre yerine makul üst sınırlı yoklama gibi). Test davranışını gevşetme; yalnız zamanlamayı sağlamlaştır. Tam test takımını art arda en az 5 kez çalıştırıp sonucu rapora yaz.

==================================================
ADIM 4 — Plaj–mahalle eşlemesi v2: ilçe alt bölüm poligonları
==================================================
4a. Kaynağı bul ve değerlendir. Walton County GIS'in ArcGIS servislerinde (GÖREV-02'de 186 servis görülmüştü; alt bölüm/plat poligonları vardı) alt bölüm (subdivision/plat) poligon katmanını bul. Kısaca değerlendir ve M7 belgesine yaz: URL, sahibi, alan adları (özellikle alt bölüm adı), son düzenleme tarihi, kayıt kimliği, kullanım/lisans notu. Uygun katman yoksa veya alt bölüm adı vermiyorsa dur; Adım 5'e geçmeden önce bulduklarını rapora yaz ve eşleme dosyasına dokunma.

4b. Her plaj erişimi için alt bölümü sorgula. 53 erişimin koordinatı için katmana "nokta poligonun içinde" sorgusu yap (ArcGIS REST query, geometryType=esriGeometryPoint, spatialRel=esriSpatialRelIntersects, giriş koordinatının uzamsal referansı açıkça verilerek). Her erişim için dönen alt bölüm adını, poligon kimliğini ve sorgu zamanını kaydet. Nokta hiçbir poligona düşmüyorsa (plaj erişimleri sık sık kamuya ait yol ucunda olduğu için olabilir) yalnız o erişim için en yakın alt bölüm poligonunu küçük bir arama mesafesiyle (ör. 75 m) bul ve "yakın poligon, mesafe X m" diye ayrıca işaretle. Ham yanıtları work/ altında sakla; repoya, erişim başına alt bölüm sonucunu veren küçük bir CSV koy (eşleme dosyasının yanında: external_id, alt_bolum_adi, poligon_kimligi, iliski (iceride/yakin), mesafe_m, katman_url, sorgu_zamani).

4c. Alt bölüm adı → mahalle tablosu. Dönen alt bölüm adlarının listesini çıkar. Adı bir mahalleyi açıkça belirten alt bölümler için açık bir eşleme tablosu yaz (ör. "SEASIDE ..." → seaside, "SEAGROVE ..." → seagrove, "ROSEMARY BEACH ..." → rosemary-beach; tam adlar kaynağın verdiği gibi). Adı bir mahalleyi açıkça belirtmeyen alt bölümler (kişi adı, site adı gibi) bu yöntemle mahalleye bağlanmaz. Tabloyu repoda, eşleme dosyasının yanında tut; tahmin yok.

4d. Yeni yöntem sırası:
1. resmi_rehber (9 erişim, değişmez)
2. ilce_alt_bolum: erişim bir alt bölüm poligonunun içindeyse ve alt bölüm adı tablodan bir mahalleye bağlanıyorsa
3. turetim_en_yakin_mahalle_noktasi: yalnız ilk iki yöntem sonuç vermezse; belirsizlik işareti eskisi gibi
Rosemary Beach ve Alys Beach kısıtı devam eder. İlçe verisi bir erişimi bu iki mahallenin alt bölümüne düşürürse erişimi o mahalleye atama; satırı "resmî rehberle çelişki" notuyla işaretle ve rapora ayrıca yaz.

4e. Doğrulama. ilce_alt_bolum yöntemini 9 resmî eşlemeye de uygula; kaç tanesinde aynı sonucu verdiğini, kaçında sonuç vermediğini ve farklı çıkanları yaz. Ayrıca v1 ile v2 arasındaki farkları tek tek listele (erişim, v1 mahallesi, v2 mahallesi, v2 yöntemi). Her mahalle için son erişim sayısını yönteme göre ayrılmış olarak ver.

4f. Üretim. Eşleme dosyasını gerçek veritabanının Adım 2'deki güncel plaj ve mahalle çekimleriyle yeniden üret (kaynak sütununda gerçek run kimlikleri olsun). Üretici betik yeniden çalıştırılabilir kalsın; ilçe sorgu sonuçlarını repodaki CSV'den okuyabilsin, ağa yalnız istenirse çıksın. Plaj ekranında yeni yöntem etiketi "ilçe alt bölüm verisi" olarak görünsün. Testleri güncelle ve yeni yöntem için test ekle (içeride / yakın / sonuçsuz / tabloda olmayan alt bölüm adı / Rosemary–Alys çelişkisi).

4g. Belge. docs/M7-MAHALLE-VERISI.md'yi v2 yöntemine göre güncelle. Video dili notu: "resmî rehber" ve "ilçe alt bölüm verisi" eşlemeleri kaynak gösterilerek söylenebilir (ikincisinde "Walton County subdivision verisine göre" diye); "program türetimi" yalnız yaklaşık konumdur.

==================================================
TESLİM
==================================================
docs/gorevler/GOREV-04/ altına: GOREV.md (work/gorevler/GOREV-04.md'nin kopyası), RAPOR.md, esleme-v1-v2-fark.csv, esleme-dogrulama-v2.csv ve plaj ekranının yeni eşlemeyle bir ekran görüntüsü.
RAPOR.md Türkçe ve sade: her adımın sonucu, main ve etiketin konumu, CI sonuçları, gerçek veritabanının öncesi/sonrası, test tekrarlarının sonucu, alt bölüm katmanının değerlendirmesi, v2 doğrulaması ve mahalle başına erişim sayıları, beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-04 bitti, dal gorev-04-esleme-v2, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
