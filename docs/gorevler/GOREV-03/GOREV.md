GÖREV-03 — main'e alma, mahalle verisi ve plaj erişimi–mahalle eşlemesi

BAĞLAM
GÖREV-02 kabul edildi. Kaynak keşfinin sonucuna göre yöneticinin bağlama kararı şudur: ilk iş mahalle verisidir, çünkü ilk videonun "30A'nın hangi parçası bana uygun" sorusu ve plaj, restoran, etkinlik verilerinin hepsi mahalle üzerinden birleşecek. Bu görevde Visit South Walton mahalle dizini için yeni bir veri toplayıcı yazılacak ve 53 plaj erişimini mahallelere bağlayan, yöntemi açıkça etiketlenmiş bir eşleme katmanı kurulacak. Ayrıca bekleyen main'e alma işlemi ve birkaç küçük belge düzeltmesi yapılacak.

Kullanıcı bu görev için sana main'e fast-forward ve push iznini kendi mesajında açıkça veriyor.

KESİN SINIRLAR
- data/ klasörüne dokunma; gerçek veritabanını uygulamayla açma. Gerçek veritabanını yalnız Adım 4'te anlatıldığı gibi kopyası üzerinden kullan.
- main'e yalnız Adım 1'deki fast-forward ile dokun. Tag oluşturma.
- Mevcut üç toplayıcının (plaj, hava, restoran) davranışını değiştirme.

==================================================
ADIM 1 — main'e alma ve yeni dal
==================================================
main'i origin/gorev-02-kaynak-kesfi (62d6b7b431669ca44a705b1c85f24f9df72bd6ca) konumuna git merge --ff-only ile getir ve main'i push et. Bu işlem GÖREV-01 ve GÖREV-02'nin incelenmiş commit'lerini main'e taşır. Fast-forward mümkün değilse dur ve rapora yaz. main üzerindeki CI sonucunu rapora ekle.
Sonra güncel main'den "gorev-03-mahalleler" dalını aç. Bu görevin bütün commit'leri bu dala gider.

==================================================
ADIM 2 — Küçük belge düzeltmeleri
==================================================
- GÖREV-02 raporunun 10. karar konusunda listelenen, kullanıcıya karar veya manuel test yükleyen ifadeleri yeni düzene göre düzelt: docs/DEVIR/07 "Geliştirme yöntemi" akışındaki "manual acceptance" adımı ve bölüm sonundaki "kullanıcıya … raporla" ifadesi (rapor yöneticiye gider), docs/ASAMALAR.md Aşama 4'teki "kullanıcı onayı" (yönetici onayı; kullanıcı makale aşamasında devreye girer). docs/DEVIR/05'teki "User manual v0.6 smoke" tarihsel kayıttır, değiştirme.
- CALISMA_MANTIGI.md 4. bölümdeki veri ilkelerine şu yönetici kararını tek madde olarak ekle: "Düzenli çalışan veri toplayıcılar robots.txt kurallarına uyar. Belirli bir resmî belgenin (rapor, yönetmelik PDF'i gibi) kaynak göstermek için tek seferlik elle alınması toplayıcı sayılmaz; URL, erişim tarihi ve SHA-256 ile kaydedilir. Programatik kullanım için yayımlanmış API'ler kendi kullanım koşullarıyla kullanılır."

==================================================
ADIM 3 — Mahalle veri toplayıcısı (south-walton-neighborhoods)
==================================================
Kaynak: https://www.visitsouthwalton.com/neighborhoods/ (Visit South Walton mahalle dizini; ayrıntısı docs/gorevler/GOREV-02/KAYNAK-KESFI.md, Alan 1A). Dizin sayfasının içindeki gömülü JSON 16 mahalleyi veriyor; her mahallenin ayrıca kendi sayfası var.

Toplayıcı mevcut genel akışı kullanmalı (kaynak → job → source_run → ham dosya → atomik yazım). Yapı ve güvenlik sınırları restoran toplayıcısıyla aynı düzeyde olsun: yalnız izinli host, HTTPS, boyut ve zaman sınırları, sınırlı yeniden deneme, iptal, ham yanıtların manifestle saklanması. 30A'ya özeldir; destination_id=30a olmadan bağlanmaz.

Kapsam: programın 13 kanonik mahallesi. Miramar Beach, Seascape ve Sandestin plaj toplayıcısındaki gibi kapsam dışı sayılır ve excluded_count'a girer. Kaynaktaki ad ile kanonik bölge adı birebir eşleşerek bağlanır (WaterColor/WaterSound gibi yazım farkları açık bir eşleme tablosuyla); adres veya koordinattan mahalle çıkarılmaz. 13 mahalleden biri kaynakta bulunamazsa çekim başarısız olur.

Her mahalle için saklanacaklar: kaynak kimliği (24 haneli id), permalink, ad, kanonik bölge kimliği, kısa tanıtım cümlesi, temsilî nokta (enlem/boylam; "mahalle merkezi değil, kaynağın temsilî noktası" diye belgelenmeli), etiket listesi (Walkable, Tranquil vb. kaynak etiketleriyle), kaynağın kayıt bazındaki modified değeri, mahalle sayfasındaki tanıtım metni (yoksa NULL). Kaynak metinleri yalnız iç araştırma kanıtıdır; belgelere "videoda aynen kullanılmaz, kendi cümlelerimizle ve atıfla kullanılır" notunu yaz.

Şema 7: yeni domain tablosu (veya tabloları) ve migration. Migration mevcut kurallarla yapılır: açılışta yedek, tek transaction, foreign_key_check, hata halinde geri alma. Uygulama sürümü 0.7.0 olur. Diff etkin olsun (mahalle kimliği üzerinden).

Arayüz: Veri toplama ekranına dördüncü sekme "Mahalleler": toplama düğmesi, sürüm seçimi, fark özeti, batıdan doğuya sıralı liste ve ayrıntı paneli. Mevcut görsel düzeni koru.

Testler: fixture ve MockTransport ile; canlı ağ yok. Mutlaka kapsananlar: 16 kayıtlık dizinden 13'ün seçilmesi ve 3'ün kapsam dışı sayılması, bir hedef mahallenin eksik olması, bozuk JSON, yinelenen kimlik, mahalle sayfasında tanıtım metninin olmaması (NULL), iptal, atomik geri alma, diff, v6 → v7 migration ve geri alma, destinasyon yalıtımı.

==================================================
ADIM 4 — Gerçek ortam kontrolleri
==================================================
- Canlı deneme geçici klasörde: work/gorev-03/temp-data ile uygulamayı aç, plaj ve mahalle toplayıcılarını çalıştır, sonuçları rapora yaz. Arayüzde Mahalleler sekmesinin ekran görüntüsünü al ve docs/gorevler/GOREV-03/ altına koy.
- Migration denemesi gerçek verinin kopyasında: data/studio.sqlite3 dosyasını GÖREV-01'deki yöntemle (mode=ro&immutable=1, backup API) work/gorev-03/db-kopya.sqlite3 olarak kopyala, kopyayı yeni sürümle --data-dir üzerinden açıp v6 → v7 yükseltmesini çalıştır; öncesi ve sonrası tablo satır sayılarını, foreign_key_check sonucunu ve mevcut plaj, hava, restoran sürümlerinin görünür kaldığını rapora yaz. Gerçek data/ klasörüne dokunma; gerçek veritabanı kullanıcı uygulamayı bir sonraki açışında kendi yedeğini alarak yükselecek.

==================================================
ADIM 5 — Plaj erişimi–mahalle eşleme katmanı
==================================================
Amaç: 53 halka açık plaj erişiminin her birinin hangi mahallede olduğunu, yöntemi açıkça etiketlenmiş olarak vermek. Plaj toplayıcısı ve beach_records tablosu değişmez; eşleme ayrı, 30A'ya özel, gözden geçirilebilir bir katmandır.

Eşleme dosyası: 30A destinasyon profilinin yanında, repoda sürümlenen bir CSV (yerini mimariye uygun seç ve belgele). Sütunlar: external_id, plaj_adi, bolge_id, yontem, kaynak, not, belirsiz (evet/hayır).

Yöntem sırası:
1. Resmî rehber: docs/gorevler/GOREV-02/plaj-mahalle-onizleme.csv dosyasındaki 9 eşleme olduğu gibi alınır. yontem = "resmi_rehber", kaynak = rehberin URL'si ve yayın tarihi (2023-05-04).
2. Program türetimi: kalan erişimler için, Adım 3'teki mahalle verisinin temsilî noktalarına boylam farkına göre en yakın mahalle seçilir (kıyı doğu–batı uzandığı için boylam kullanılır). yontem = "turetim_en_yakin_mahalle_noktasi", kaynak = kullanılan mahalle çekiminin run kimliği. Kısıt: resmî rehberin "halka açık plaj erişimi yok" dediği Rosemary Beach ve Alys Beach'e hiçbir erişim atanmaz; böyle bir durumda sıradaki en yakın mahalle seçilir ve notta belirtilir. En yakın iki mahallenin uzaklık farkı küçükse (yaklaşık 0,003 derece boylam, ~300 m) belirsiz = evet yazılır.
3. Doğrulama: aynı türetme yöntemini 9 resmî eşlemeye de uygula ve kaç tanesinde resmî rehberle aynı sonucu verdiğini, farklı çıkanları tek tek rapora yaz. Bu, yöntemin ne kadar güvenilir olduğunun ölçüsüdür. Sonuç ne çıkarsa çıksın eşleme dosyasını üret; karar yöneticinindir.

Eşlemeyi üreten betik repoda dursun (yeniden üretilebilsin); eşleme dosyası bir kez üretilip commit edilir, uygulama çalışırken kendi kendine yeniden hesaplamaz. Plaj ekranında her erişimin yanında mahalle ve yöntem etiketi görünsün ("resmî rehber" / "program türetimi"), mahalleye göre filtrelenebilsin. Eşleme dosyasında olmayan yeni bir plaj kimliği çıkarsa ekranda "eşlenmemiş" görünsün. Eşleme dosyasının okunmasına ve ekrandaki gösterime test ekle.

Belgeleme: eşleme yöntemini, kısıtı ve doğrulama sonucunu docs/ altında 30A plaj verisini anlatan belgeye (ya da yeni kısa bir M7 belgesine) yaz. Videoda kullanılacak dil notu: "resmî rehber" eşlemeleri kaynak gösterilerek söylenebilir; "program türetimi" eşlemeleri yalnız yaklaşık konum bilgisi olarak kullanılır.

==================================================
ADIM 6 — Belgeler
==================================================
CALISMA_MANTIGI.md (çalışan domain'ler, stable/aktif durum tablosu, şema), README.md ve docs/DEVIR/05'e v0.7 mahalle domain'ini ve eşleme katmanını kısa ve doğru biçimde ekle. Eski v0.7-lodging-inventory dalının adıyla karışmaması için yeni sürümün içeriğini açıkça "v0.7.0 — mahalle verisi ve plaj–mahalle eşlemesi" diye adlandır.

==================================================
TESLİM
==================================================
docs/gorevler/GOREV-03/ altına: GOREV.md (work/gorevler/GOREV-03.md'nin kopyası), RAPOR.md, mahalleler.csv (canlı çekimdeki 13 mahalle: kimlik, ad, kanonik bölge, enlem, boylam, etiketler, modified, tanıtım metni var mı), eşleme dosyasının kopyası veya yolu, doğrulama tablosu ve ekran görüntüleri.
RAPOR.md Türkçe ve sade olsun: her adımın sonucu, main'in yeni konumu, CI sonuçları, test sayıları, canlı deneme ve migration denemesi sonuçları, eşleme doğrulamasının sonucu, beklenmedik durumlar ve yöneticinin karar vermesi gereken konular.
Push etmeden önce git status ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-03 bitti, dal gorev-03-mahalleler, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
