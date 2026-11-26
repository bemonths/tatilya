HEDEF-01 — Çekime hazırlık: işçiler, bütün okuyucuların denenmesi ve kullanıcının gece çekimi için hazır sistem (kendi kendine çalışma)

BU BİR GÖREV DEĞİL, BİR HEDEFTİR
Kullanıcı (Mucahit) bu süre boyunca bilgisayarın başında olmayacak. Sen bu hedefe ulaşana kadar kendi başına, adım adım çalışırsın:
- eksikleri sen bulursun;
- teknik kararları sen verirsin;
- gerekirse kod yazar, test eder, veri çekersin;
- sonucu kontrol eder, bir sonraki eksiğe geçersin.

Teknik bir konuda soru sormak için durmazsın. Verdiğin her kararı gerekçesiyle durum dosyasına ve rapora yazarsın. Yalnız aşağıdaki "Duracağın yerler" bölümündeki durumlarda durursun.

Proje yöneticisi (ayrı bir Claude sohbeti) senin durum dosyanı okuyup kullanıcıya özet verir ve işini denetler. Bu yüzden durum dosyası her zaman güncel olmalı.

BAĞLAM
- Program: 30A Studio. Klasör: `C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`. Depo: `bemonths/tatilya`.
- Önce şunları oku:
  - `CLAUDE.md`, `CALISMA_MANTIGI.md`, `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`;
  - `docs/M21-IS-AKISI-KATMANLAR.md`, `docs/M11-KONAKLAMA-FIYATLARI.md`, `docs/M14-KANIT-PAKETI.md`, `docs/M16-TARAYICI-EKLENTISI.md`, `docs/M18-ABD-PROXY-BOLGE-ENGELI.md`;
  - son altı görevin raporları: `docs/gorevler/GOREV-20` … `GOREV-25` altındaki `RAPOR.md`;
  - yöneticinin notları: `work\yonetim\30A_PM_NOTLARI.md` (yalnız oku, değiştirme).
- Durum:
  - main `f87582c` = `v0.24.0`.
  - Dal `gorev-25-realjoy-sorgu`, son commit `833382a`: uygulama 0.26.0, şema 24, eklenti 0.20.0. GÖREV-24 ve GÖREV-25'i içerir; yönetici ikisini kabul etti ama henüz main'e alınmadı.
  - Programın günlüğüne göre program 18 Kasım sabahından beri çalışmadı. GÖREV-25'ten sonra yapılması gereken uzun kiralama çekimi (yaklaşık 13,5 saat) başlatılmamış görünüyor.
- Kanalın ilk videosu, 30A'ya ilk kez gidecek birinin üç sorusunu cevaplar: hangi kasabada kalmalı, hangi ayda gitmeli, bir hafta ne tutar. Yöneticinin önerdiği başlık:
  - İngilizce: `First Time on 30A? Which Town, Which Month and What a Week Costs | 30A Florida Vacation`
  - Türkçe: `30A'ya ilk kez mi gidiyorsunuz? Hangi kasaba, hangi ay ve bir hafta ne tutar | 30A Florida Tatili`

==================================================
"BİTTİ" NE DEMEK
==================================================
Kullanıcının kararı (26 Kasım 2026): büyük veri çekimini (bütün toplayıcılar, uzun kiralama çekimi dahil) **kullanıcı kendisi, gece başlatacak**. Senin işin sistemi buna hazır hâle getirmek ve her parçanın çalıştığını küçük denemelerle göstermek. Gerçek veride uzun çekimi sen başlatmazsın.

Hedef, aşağıdakilerin hepsi doğru olduğunda biter.

1. **Kod main'de.** `gorev-25-realjoy-sorgu` main'e fast-forward ile alındı ve `v0.26.0` etiketi kondu. Bu hedefte yazdığın kod da testleri ve CI'si geçmiş olarak main'de; son etiket `v0.27.0`.
2. **İşçiler hazır.** Aşağıdaki "İşçiler" bölümü yazıldı, test edildi ve main'de. Proxy listesi ekranı çalışıyor.
3. **Deneme çekimi var ve geçti.**
   - Programa kalıcı bir **deneme çekimi** eklenir: kiralama şirketlerinin her biri için birkaç ilan (ör. 2) ve tek bir hafta. Öbür toplayıcılar için de, varsa, küçük bir deneme. Yeri: Sol menü → Veri → Okuma denemeleri.
   - Deneme çekiminin sonucu gerçek veriye karışmaz: ayrı kaydedilir ya da geçici veri kopyasında çalışır. Hangisi doğruysa sen seç ve yaz.
   - Deneme çekimi gerçek sitelerde, işçilerle bir kez çalıştırılır. Her şirket ve toplayıcı için sonuç rapora yazılır: okundu mu, hangi işçiden (doğrudan, proxy, eklenti, programın tarayıcısı), hata varsa ne.
   - Bulunan hatalar düzeltilir, test yazılır, deneme yeniden çalıştırılır.
   - Kalıcı engeller sebebiyle kayda geçer: site yok, bot koruması, yalnız kullanıcının geçebileceği doğrulama.
4. **Tahmin doğru.** "Güncelleme zamanı gelenler" tablosu, işçi sayısına göre bütün çekimin tahmini süresini gösteriyor. Rapora mevcut işçi sayısıyla ve örnek olarak 10 ve 20 işçiyle tahmin yazılır.
5. **Kullanıcının gece çekimi için tarif.** Rapora ve DURUM'a, Türkçe ve ekrandaki tam adlarla:
   - proxy listesinin nereye, nasıl girileceği;
   - eklentinin ve Chrome'un açık kalması;
   - çekimin nasıl başlatılacağı;
   - doğrulama çıkarsa ne yapılacağı;
   - tahmini süre;
   - bitince nereye bakılacağı.
6. **Testler geçti.**
   - Tam takım: `.venv\Scripts\python.exe -m pytest -q` ve `node --test tests/frontend.test.mjs`.
   - GitHub'daki test çalışması son commit'te başarılı.
7. **Rapor yazıldı.** `docs/gorevler/HEDEF-01/RAPOR.md` yazıldı ve main'e girdi.

Gece çekiminden sonraki işler bu hedefin dışındadır: sonuçların denetimi, kapsam tabloları, başlık değerlendirmesi, videonun açılması. Bunlar ayrı bir hedefle yapılacak.

==================================================
İZİNLER (kullanıcı verdi)
==================================================
- **main ve etiket.** `gorev-25-realjoy-sorgu`'yu main'e fast-forward ile alabilir ve `v0.26.0` etiketini koyabilirsin. Kendi işini `hedef-01` dalında yaparsın. Dalı sık sık push edersin. Testler ve CI geçince main'e fast-forward ile alır, `v0.27.0` etiketini koyarsın. Gerekirse arada da main'e alabilirsin; her seferinde testler ve CI geçmiş olmalı.
- **Gerçek veri.** Programı gerçek veri klasörüyle açabilirsin. Bunu yalnız şunlar için yaparsın: göçler, ayarların girilmesi, deneme çekimi.
  - Uzun çekimi ("Zamanı gelenleri başlat" ya da bir toplayıcının tam çalışması) başlatmazsın; onu kullanıcı başlatacak.
  - Gerçek veride bir değişiklikten önce, program kapalıyken `data/` klasörünün tam yedeğini `work/yedek/<YYYYMMDD-HHMM>/` altına al.
  - `data/` içindeki dosyaları elle değiştirme, silme, taşıma.
- **Eklenti.** Bu hedef boyunca eklentiyle gerçek sitelerden okumayı sen başlatabilirsin: deneme düğmesi ve deneme çekimi. Kullanıcının Chrome'u açık bırakılacak. Eklentinin kuralları aynen geçerlidir.
- **Kod.** Okuyucu yazmak, hata düzeltmek, yeni kapsam ölçümü ya da ekran eklemek serbesttir. Her değişiklik test ile gelir ve ilgili `docs/Mx` belgesine işlenir.
- **Gerçek Claude yok.** Programın hiçbir Claude adımını gerçek Claude ile çalıştırma.
- **Canlı incelemeler.** Yeni bir okuyucu ya da hata için canlı sayfa okumak gerekirse: site başına en çok 20 sayfa, aynı sitede iki istek arası en az 8 saniye (RealJoy'da 20 saniye).

==================================================
İŞÇİLER: ÇEKİMİ HIZLANDIRMA (kullanıcı kararı, 26 Kasım 2026)
==================================================
Kiralama çekimi bugün yaklaşık 12,5 saat sürüyor. Program aynı anda yalnız 3 şirket okuyor, aynı siteye 8 saniyede bir istek yapıyor ve hepsi tek çıkıştan (doğrudan ya da tek proxy) gidiyor.

Kullanıcının kararı: çekim, Housing Atlas'taki gibi **işçilerle** yapılır. Her işçi ayrı bir çıkıştan çalışır: doğrudan ya da kullanıcının proxy'lerinden biri. İşçiler aynı anda çalışır; işçi eklendikçe çekim hızlanır. Proxy'ler artık yalnız bölge engeli için değil, hız için de kullanılabilir.

CLAUDE.md'deki "proxy yalnız bölge engeli için; hız sınırını aşmak için kullanılmaz; IP döndürme yoktur" cümlesini bu karara göre düzelt; kararın tarihini yaz.

Housing Atlas'ın işçi düzenine bak ve oradan örnek al. Klasör: `C:\Users\1\source\repos\housing-atlas`; yalnız oku, hiçbir dosyasını değiştirme. Orada proxy bilgileri ya da parolalar varsa onları okuma ve kopyalama.

**Ölçüler:**
1. **Proxy listesi.** Ayarlar → ABD proxy'si bölümü birden çok proxy alabilir.
   - Her proxy bir işçidir; doğrudan çıkış da bir işçidir.
   - Parolalar yalnız Windows Kimlik Bilgisi Yöneticisi'nde durur; dosyaya, günlüğe ve rapora yazılmaz.
   - Bugünkü tek proxy listenin ilk satırı olur.
   - "Proxy'yi dene" her proxy için ayrı sonuç gösterir: çalışıyor mu, çıkış ülkesi.
   - **Toplu ekleme.** Kullanıcı listeyi bir kutuya satır satır yapıştırabilir. Her satır bir proxy olur; Housing Atlas'ta kullandığı biçim kabul edilir (ör. `adres:port:kullanıcı:parola`). Tür (HTTP ya da SOCKS5) seçilebilir.
     - Program kaydederken parolaları hemen Windows Kimlik Bilgisi Yöneticisi'ne yazar, kutuyu temizler. Dosyada yalnız adres, port, kullanıcı adı ve tür kalır.
     - Her satır tek tek denenir; çalışmayan satır "çalışmıyor" diye işaretlenir ve işçi olmaz.
   - **Havuz canlıdır.** Çekim sürerken havuza eklenen proxy, en geç birkaç dakika içinde yeni işçi olarak çekime katılır. Havuzdan çıkarılan ya da çekim sırasında düşen proxy'nin işçisi durur; yarım kalan işi başka işçiye geçer.
2. **Dağıtım.** İşler şirket ve ilan bazında işçilere dağıtılır. Bir işçi takılırsa ya da proxy'si düşerse, işi başka işçiye geçer.
3. **Sitenin korunması.** Hızlanma sitenin çökmesine ya da kapanmasına yol açmamalı.
   - Bir işçi aynı siteye en az 8 saniye arayla istek yapar.
   - **Aynı siteye aynı anda çalışabilecek işçi sayısına üst sınır.** Ayarda durur, başlangıç değeri 4.
   - Bir site herhangi bir işçiye 429, engel ya da doğrulama sayfası verirse, o sitedeki bütün işçiler yavaşlar (aralık iki katına çıkar). Tekrar ederse o site için işçi sayısı bire iner. Bu olaylar çekim kaydına yazılır.
4. **Tarayıcı gerektiren siteler işçiye bölünmez.**
   - RealJoy kullanıcının Chrome'undaki eklentiyle okunur.
   - oversee.us ve exclusive30a.com programın kendi tarayıcısıyla okunur.
   - Bunlar kendi sıralarında, öbür işçilerle aynı anda çalışır.
   - RealJoy'un aralığı 20 saniyeden 12 saniyeye iner; 429 gelirse kendiliğinden 20 saniyeye ve üstüne çıkar.
5. **Bölge engelli siteler** (360 Blue, Vacasa ve öbürleri) yalnız proxy'li işçilere gider.
6. **Tahmin ve ekran.**
   - "Güncelleme zamanı gelenler" tablosundaki tahmin işçi sayısına göre hesaplanır.
   - İşler panelinde işçilerin durumu görünür: her işçinin çıkışı (doğrudan ya da proxy sırası; adresi değil), elindeki şirket ve hata sayısı.
7. **Model ve efor yok.** Bu bir Claude adımı değildir.
8. **Testler.** Dağıtım; işçi düşünce işin devri; site başına işçi sınırı; 429'da bütün işçilerin yavaşlaması; bölge engelli sitenin yalnız proxy'li işçiye gitmesi; tarayıcı gerektiren sitelerin bölünmemesi. Testler sahte HTTP ile, canlı ağsız yapılır.

**Sıra:** Bu değişiklik deneme çekiminden önce yapılır, test edilir ve main'e alınır. Deneme çekimi işçilerle yapılır.

**Proxy listesi kullanıcıdan gelir.**
- Listeyi kullanıcı girecek. O girene kadar mevcut tek proxy ve doğrudan çıkışla çalış.
- Liste ekranı hazır olunca DURUM'un "Mucahit'in yapması gerekenler" bölümüne tam ekran adlarıyla yaz: proxy listesini nereye, nasıl gireceği.
- Kullanıcı listeyi girmeden deneme çekiminin zamanı gelirse, denemeyi eldeki işçilerle (mevcut tek proxy ve doğrudan çıkış) yap. Bekleme.

==================================================
DEĞİŞMEYEN KURALLAR
==================================================
- CLAUDE.md'deki "Bilgi toplama", "Veri dili", "Veri güvenliği" ve "Katmanlar" bölümleri aynen geçerlidir:
  - giriş, hesap, ödeme, rezervasyon, sepet ve kişisel form yok;
  - gizlenme, parmak izi sahteciliği, doğrulama çözme servisi ve IP döndürme yok;
  - proxy, bölge engeli ve işçilerle hızlanma için kullanılır (yukarıdaki "İşçiler" bölümü); doğrulama sayfasını ya da bot korumasını geçmek için kullanılmaz;
  - doğrulamayı yalnız kullanıcı geçer;
  - kaynağın söylemediği yazılmaz; koordinattan sessizce mahalle çıkarılmaz.
- Proxy bilgileri ve parola hiçbir dosyaya, günlüğe ve rapora yazılmaz.
- Talimat dosyalarına (`studio/destinations/thirty_a_claude/`), Housing Atlas, Rota Stüdyo ve Kurgu Motoru depolarına dokunulmaz. Zamanlanmış görev oluşturulmaz. Windows ayarları değiştirilmez.
- Alt ajan kullanma; işi kendin yap.
- Kullanıcı verisi silinmez.

==================================================
ÇALIŞMA DÜZENİ
==================================================
1. **Durum dosyası.** `work\hedef\DURUM.md`. Her adımın başında ve sonunda güncelle; saat ve tarihle. Bölümleri:
   - **Şu an ne yapıyorum;**
   - **Bitenler:** kısa, her biri bir satır;
   - **Sıradakiler;**
   - **Mucahit'in yapması gerekenler:** yalnız onun yapabileceği şeyler; her biri ekrandaki tam adlarla tarif edilir, ör. "Sol menü → Veri → …";
   - **Sorunlar ve kararlarım.**

   Dosya kısa ve güncel kalır: eskiyen satırları "Bitenler"e indir ya da sil.
2. **Sıra önerisi** (daha iyisini bulursan değiştir ve yaz):
   1. main ve etiket;
   2. küçük açık işler: winndixie.com'un proxy kimlik doğrulama penceresi; GÖREV raporlarında açık kalan hatalar;
   3. işçiler ve proxy listesi ekranı: yaz, test et;
   4. deneme çekimi: yaz, test et;
   5. yedek; deneme çekimini gerçek sitelerde işçilerle çalıştır; hataları düzelt; yeniden dene;
   6. tahmin, tarif, testler, CI, main, rapor.
3. **Beklemeler.** Deneme çekimi sürerken işin durumunu 10–15 dakikada bir kısa bir sorguyla kontrol et: işin yüzdesi, hatalar. Büyük günlükleri baştan sona okuma; yalnız son satırlara ve hata satırlarına bak.
4. **Doğrulama çıkarsa.** Programın akışı aynen kalır: site sona bırakılır, en sonda 15 dakika beklenir, olmazsa atlanır. Atlanan siteyi DURUM'da "Mucahit'in yapması gerekenler"e yaz: hangi site, ne yapacak, sonra hangi düğmeyle o şirketin yeniden okunacağı. Öbür işlere devam et.
5. **Bir şey bozulursa.** Programın veritabanı bozulursa, bir göç başarısız olursa ya da veri kaybı şüphesi olursa: dur. Programı kapat, son yedeği yerinde bırak, DURUM'a yaz. Yedekten geri dönme kararını yönetici verir.

==================================================
DURACAĞIN YERLER
==================================================
Yalnız şu durumlarda durursun ve DURUM'a "DURDUM: <sebep>" yazarsın:
- "Bitti" bölümündeki her şey doğru. Bu durumda rapor yazılmış ve main'e girmiş olur, ve DURUM'da kullanıcının gece çekimi tarifi durur.
- Kalan her iş yalnız kullanıcının yapabileceği bir şeye bağlı: doğrulama, ya da Chrome veya programın kapalı olması.
- Bir kuralın değişmesi gerekiyor. Bu, kullanıcının kararıdır; sen değiştirmezsin.
- Veri kaybı şüphesi (yukarıda).
- Uzun çekimi başlatmak ya da gerçek Claude çalıştırmak gerekiyor. Bunlar bu hedefin dışındadır.

TESLİM
`docs/gorevler/HEDEF-01/` altında `HEDEF.md` (bu dosya) ve `RAPOR.md`. Raporda şunlar olsun:
- yapılan işler ve kararlar;
- işçiler: nasıl çalıştığı, site başına sınır, yavaşlama kuralı, proxy listesi;
- deneme çekimi: tasarım, gerçek sitelerdeki sonuç tablosu, bulunan ve düzeltilen hatalar;
- tahminler: mevcut işçi sayısıyla, ve 10 ile 20 işçiyle;
- kullanıcının gece çekimi tarifi;
- açık kalanlar ve sebepleri;
- yedeklerin yerleri;
- test ve CI sonuçları.

Bitince kullanıcıya son mesajın yalnız şu olsun: "HEDEF-01 bitti, son commit <hash>" ve varsa açık kalanlar (kısa).
