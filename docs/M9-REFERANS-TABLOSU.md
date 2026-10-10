# M9 — Elle doğrulanmış referans tablosu

Tarih: 7 Ekim 2026 · Görevler: GÖREV-06 (tablo), GÖREV-07 (tamamlama, `yerine_gecildi` durumu), GÖREV-08 (kalan satırlar, 8 Ekim 2026) · Uygulama `0.11.0`

## Amaç

Toplayıcıyla alınamayan ama ilk videoda söylenecek her bilgiyi (plaj kuralları, bayrak sistemi, plaj erişimi, ulaşım, parklar, kasırga sezonu, sezon ve maliyet) kaynağıyla ve doğrulama tarihiyle tek bir yerde tutmak. Kanıt paketi ve makale aşaması bu tabloyu okur. Tablo elle doldurulur, gözden geçirilir ve repoda sürümlenir; uygulama yalnız okur ve doğrular.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `studio/destinations/thirty_a_references.csv` | Referans tablosu; her satır tek bir olgu. Profil sabiti `thirty_a.REFERENCE_TABLE`. |
| `studio/destinations/thirty_a_references_tr.csv` | Her referans satırının Türkçe ifadesi (GÖREV-11). Profil sabiti `thirty_a.REFERENCE_TRANSLATIONS`. |
| `studio/destinations/thirty_a_traffic.csv` | FDOT 2025 AADT (CR 30A ve US 98 sayım noktaları) ve Walton mevsim faktörleri; referans tablosunun kaynak sütunlarıyla (GÖREV-11). Profil sabiti `thirty_a.TRAFFIC_TABLE`. |
| `studio/destinations/thirty_a_tdt_collections.csv` | South Walton turist geliştirme vergisi (TDT) aylık tahsilatları, Ekim 1998–Temmuz 2026. Profil sabiti `thirty_a.TDT_COLLECTIONS`. |
| `studio/destinations/references.py` | Genel okuyucu ve doğrulayıcı (destinasyondan bağımsız; dosya yerini profil verir). |
| `work/referans-belgeler/` | Alınan belgeler ve `manifest.json` (istenen/son URL, HTTP durumu, bayt, SHA-256, UTC zamanı). Repoya girmez. |

## Sütunlar

| Sütun | Anlamı |
|---|---|
| `id` | Kalıcı kimlik, küçük harf-rakam-tire (ör. `kural-cam`). Değişmez; olgu kaldırılırsa kimlik yeniden kullanılmaz. |
| `konu` | `plaj-kurallari`, `guvenlik`, `plaj-erisimi`, `ulasim`, `parklar`, `kasirga-sezonu`, `sezon-maliyet`, `genel`; GÖREV-11 ile `plaj-hukuku`, `erisilebilirlik`, `kalabalik`, `etkinlikler`, `tarihce` |
| `ifade` | İngilizce tek cümle, kendi cümlemizle; videoda söylenebilecek biçimde. Kaynağın taşıdığından ileri gitmez. |
| `deger`, `birim` | Olgunun değeri ve birimi (boş olabilir). |
| `kapsam` | `30A`, `South Walton`, `Walton County`, `Florida`, `Atlantik havzası`; GÖREV-11 ile `ABD`, `Okul bölgesi` |
| `kaynak_adi`, `kaynak_sahibi`, `kaynak_url` | Belgenin adı, yayımlayan kurum, alındığı adres (yönlendirmeden sonraki son adres). |
| `belge_konumu` | Bölüm, madde, sayfa veya sayfa başlığı. |
| `kisa_alinti` | Kaynaktan birebir en fazla 25 kelime; yalnız doğrulama içindir, videoda kullanılmaz. |
| `belge_tarihi` | Biliniyorsa `YYYY`, `YYYY-AA` veya `YYYY-AA-GG`. |
| `erisim_tarihi` | Belgenin alındığı gün (`YYYY-AA-GG`, UTC). |
| `belge_sha256` | Alınan dosyanın ya da sayfanın SHA-256'sı. |
| `guven` | `birincil` (kuralın veya verinin sahibi) / `ikincil` (başkasının özeti). |
| `durum` | `dogrulandi` / `celiskili` / `dogrulanamadi` / `yerine_gecildi` |
| `celiski_notu` | Çelişkili satırda zorunlu; karşı satırın kimliği ve farkı. |
| `yeniden_kontrol_tarihi` | Satırın yeniden kontrol edileceği gün. |
| `not` | Kapsam sınırları, hesap açıklaması, uyarılar. |

## Doğrulayıcı kuralları

`references.problems()` her ihlali okunur bir cümleyle döndürür; testler (`tests/test_references.py`) repodaki tablonun hiç ihlal içermediğini denetler. Kurallar: sütunlar ve sırası birebir; zorunlu alanlar dolu; kimlik biçimi ve tekilliği; konu, kapsam, güven ve durum tanımlı değerlerden; erişim ve yeniden kontrol tarihi `YYYY-AA-GG` ve yeniden kontrol erişimden sonra; belge tarihi kısmi tarih biçimlerinden biri; `dogrulandi`, `celiskili` ve `yerine_gecildi` satırlarda https adresi ve SHA-256 zorunlu; `celiskili` satırda çelişki notu zorunlu; `yerine_gecildi` satırın notunda `yerine geçen: <kimlik>` yazmalı ve o kimlik tabloda `dogrulandi` bir satır olmalı; kısa alıntı en fazla 25 kelime. API (`GET /api/references`) satırları, doğrulama sonucunu, yeniden kontrol tarihi geçmiş satırları (`overdue`) ve yerine geçen satırın kimliğini (`replaced_by`) verir; bozuk dosyada uygulama hata vermez, nedenini gösterir.

## Kaynak politikası

- `CALISMA_MANTIGI.md` §4 madde 14: belirli bir resmî belgenin kaynak göstermek için tek seferlik elle alınması toplayıcı sayılmaz; URL, erişim tarihi ve SHA-256 ile kaydedilir. Bu tablonun belgeleri böyle alındı (`work/referans-belgeler/al.py`, repo adresli User-Agent, istekler arası 1,5 sn). **GÖREV-07 notu (7 Ekim 2026):** madde 14 artık bilgi toplama ilkesidir: herkese açık her bilgi alınır, gerekirse gerçek tarayıcıyla; kaynak, erişim tarihi ve ham kopya saklanır.
- Bot doğrulaması (Cloudflare vb.) olan sayfa otomasyonla aşılmaz; okunamazsa satır `dogrulanamadi` olur (7 Ekim 2026'da Florida State Parks sayfaları HTTP 403 döndürdü). **GÖREV-07 notu (7 Ekim 2026):** bu kural kaldırıldı. Bot doğrulamalı sayfa gerçek tarayıcıyla okunur; etkileşimli doğrulama (CAPTCHA) çözülmez, o durumda aynı bilgi başka bir resmî yayından aranır. `dogrulanamadi` yalnız bilgi hiçbir yoldan okunamadığında kullanılır.
- İki kaynak çelişirse ikisi de ayrı satır olarak yazılır, ikisi de `celiskili` olur ve `celiski_notu` doldurulur; hangisinin doğru olduğuna tabloyu dolduran karar vermez. Aynı belgenin iki sayfası çelişirse de böyle yapılır.
- Çelişki daha güncel bir resmî kaynakla ya da yönetici kararıyla çözülürse (GÖREV-07) eski satırlar silinmez: durumları `yerine_gecildi` olur, `celiski_notu` korunur, `not` sütununa gerekçe ve `yerine geçen: <kimlik>` yazılır; geçerli değer yeni ya da seçilen satırda `dogrulandi` olarak durur.
- Taranmış belgeler (Ordinance 2025-22, metin katmanı yok) sayfa görüntüleri çıkarılıp okunarak işlendi; OCR yalnız arama içindir, alıntılar sayfa görüntüsünden doğrulandı. Metin tabanlı PDF'lerdeki infografik değerler Windows'un PDF çizicisiyle sayfa görüntüsü üretilip gözle doğrulandı.

## Durumlar ve video dili

- **`dogrulandi`** — kaynak gösterilerek söylenebilir (ör. "Walton County'nin plaj yönetmeliğine göre …").
- **`celiskili`** — ancak çelişki açıkça söylenerek ya da daha güncel bir resmî kaynakla çözülerek kullanılır.
- **`dogrulanamadi`** — videoda kullanılmaz.
- **`yerine_gecildi`** — kayıt için durur, videoda kullanılmaz; yerine geçen satır kullanılır.
- Değeri bizim hesapladığımız satırlar (havalimanı uzaklıkları) `not` sütununda "bizim hesabımız" diye işaretlidir.

## Yeniden kontrol kuralı

Kurallar, ücretler, saatler ve tanımlar yılda bir yeniden kontrol edilir (7 Ekim 2026'da alınanlar için 2027-10-07). Ziyaretçi ve konaklama raporlarından gelen satırlar her yeni rapor çıktığında kontrol edilir (ilk kontrol 2026-12-01). Çelişkili cankurtaran satırları bir sonraki sezondan önce, 2027-02-01'de. Sekme, tarihi geçmiş satırları işaretler ve sayar.

## 7 Ekim 2026 içeriği

GÖREV-06'da 85 satır (73 `dogrulandi`, 6 `celiskili`, 6 `dogrulanamadi`); GÖREV-07 sonrası 103 satır: 89 `dogrulandi`, 2 `celiskili`, 9 `dogrulanamadi`, 3 `yerine_gecildi`; GÖREV-08 sonrası 105 satır: 100 `dogrulandi`, 2 `celiskili`, 0 `dogrulanamadi`, 3 `yerine_gecildi` (dağılım aşağıda).

GÖREV-06 dağılımı (kayıt için):

| Konu | Satır | Doğrulandı | Çelişkili | Doğrulanamadı | Başlıca kaynak |
|---|---:|---:|---:|---:|---|
| Plaj kuralları | 25 | 25 | 0 | 0 | Walton County Ordinance 2025-22 (24 Kasım 2025) |
| Güvenlik | 12 | 10 | 2 | 0 | South Walton Fire District; Visit South Walton |
| Plaj erişimi | 10 | 10 | 0 | 0 | Visit South Walton park ve ulaşım rehberi (2023-05-04), plaj erişim haritası |
| Ulaşım | 11 | 9 | 2 | 0 | FAA, Florida Statutes 316.212 ve 316.2122, Ordinance 2009-02, Visit South Walton |
| Parklar | 8 | 2 | 0 | 6 | Florida Forest Service; Florida State Parks (okunamadı) |
| Kasırga sezonu | 2 | 2 | 0 | 0 | NOAA NHC |
| Sezon ve maliyet | 14 | 12 | 2 | 0 | Walton County Tourism / Downs & St. Germain raporları; TDT Collections |
| Genel | 3 | 3 | 0 | 0 | Ordinance 2025-22; Visit South Walton |

Çelişkiler: cankurtaran sezonu (SWFD SSS: 1 Mart–30 Eylül, 10:00–18:00, 8 kule; Visit South Walton: 1 Mart–31 Ekim), Timpoochee Trail uzunluğu (19 mil / 18,5 mil) ve 2025 ziyaretçi sayısı (aynı raporun 5. sayfasında 4.586.000, 8. sayfasında 4,57 milyon; doğrudan harcama da iki sayfada farklı). Ziyaretçi ve konaklama satırlarındaki ADR değerleri, Airbnb ve Vrbo'nun 2025'te fiyat gösterimini değiştirmesiyle (temizlik ve platform ücretleri dahil) yıllar arası karşılaştırmada şişkin görünebilir; bu uyarı ilgili satırların notunda.

GÖREV-07 sonrası dağılım:

| Konu | Satır | Doğrulandı | Çelişkili | Doğrulanamadı | Yerine geçildi |
|---|---:|---:|---:|---:|---:|
| Plaj kuralları | 29 | 29 | 0 | 0 | 0 |
| Güvenlik | 13 | 11 | 0 | 0 | 2 |
| Plaj erişimi | 17 | 15 | 0 | 2 | 0 |
| Ulaşım | 17 | 14 | 2 | 1 | 0 |
| Parklar | 8 | 2 | 0 | 6 | 0 |
| Kasırga sezonu | 2 | 2 | 0 | 0 | 0 |
| Sezon ve maliyet | 14 | 13 | 0 | 0 | 1 |
| Genel | 3 | 3 | 0 | 0 | 0 |
| **Toplam** | **103** | **89** | **2** | **9** | **3** |

GÖREV-07'de eklenen ve değişenler:
- **Plajda alkol:** ilçe plaj yönetmeliğinde hüküm yok (`kural-alkol`); Walton County Tourism yasal yaştaki yetişkinlere yalnız kutu veya plastikle izin verildiğini yazıyor (`alkol-plaj-vsw`, ikincil özet); eyalet parklarında alkol tüketimi, satış yapan restoran ve konaklama yerleri ile park etkinlikleri dışında yasak (Florida Administrative Code 62D-2.014(12)); 21 yaş altına alkol bulundurmak yasak (F.S. 562.111); düşük hızlı araçta açık alkol kabı yasak (Walton County Sheriff's Office).
- **Cankurtaran:** 2026 sezonu 1 Mart–31 Ekim, 10:00–18:00 (`cankurtaran-2026`; SoWal.com'un 2 Mart 2026 haberi, ikincil; Walton County Tourism'in sayfasıyla aynı). SWFD'nin kendi sitesinde 2026 duyurusu bulunamadı; iki eski satır `yerine_gecildi`.
- **2025 ziyaretçi:** yönetici kararıyla raporun tabloları esas (4.586.000, `ziyaretci-2025-ozet` doğrulandı); 4,57 milyon satırı `yerine_gecildi`.
- **Golf arabası ve düşük hızlı araç:** ilçe golf arabalarının ilçe yollarında kullanılmadığını, şerif hiçbir kamu yolunda kullanılamadığını söylüyor; ilçenin golf arabasına açtığı bir yol bulunamadı. Düşük hızlı araç: 35 mph ve altındaki yollar, kaldırım ve bisiklet yolunda yasak, US 98'de yasak (yalnız dört yollu kavşakta geçiş).
- **Planlı topluluklar:** Seaside saatlik değişken ücretli otopark ve 06:00–24:00 ücretsiz servis; Alys Beach işaretli yerlerde ücretsiz ziyaretçi otoparkı, plaj ve plaj erişimleri halka kapalı; WaterColor'da topluluk derneğinin yönettiği ücretli park yerleri (otelin SSS'sinden, ikincil). Rosemary Beach ve WaterSound'un sitelerinde ziyaretçi otoparkı bilgisi bulunamadı (`dogrulanamadi`).
- **Çözülemeyenler:** eyalet parklarının ücret ve saatleri (site Cloudflare doğrulaması; uygulama içi tarayıcıyla giriş reddedildi; ücret çizelgesi PDF'i de 403), Timpoochee uzunluğu (Walton County'nin resmî değeri bulunamadı; çelişki sürüyor), 30A hız sınırları (resmî karar belgesi bulunamadı; tek haber kaynağı Cloudflare arkasında).

GÖREV-08 sonrası dağılım (8 Ekim 2026):

| Konu | Satır | Doğrulandı | Çelişkili | Doğrulanamadı | Yerine geçildi |
|---|---:|---:|---:|---:|---:|
| Plaj kuralları | 29 | 29 | 0 | 0 | 0 |
| Güvenlik | 13 | 11 | 0 | 0 | 2 |
| Plaj erişimi | 17 | 17 | 0 | 0 | 0 |
| Ulaşım | 19 | 17 | 2 | 0 | 0 |
| Parklar | 8 | 8 | 0 | 0 | 0 |
| Kasırga sezonu | 2 | 2 | 0 | 0 | 0 |
| Sezon ve maliyet | 14 | 13 | 0 | 0 | 1 |
| Genel | 3 | 3 | 0 | 0 | 0 |
| **Toplam** | **105** | **100** | **2** | **0** | **3** |

GÖREV-08'de tamamlananlar ("Tarayıcı ve insan doğrulaması" yöntemiyle):
- **Eyalet parkları:** floridastateparks.org sayfaları uygulama içi tarayıcıda normal açıldı (doğrulama ekranı çıkmadı; otomasyonla açılan Chrome'a ve düz isteğe ise 403 veriyor). Ham sayfa aynı tarayıcı oturumunda `fetch` ile alındı, SHA-256'sı tarayıcıda ve diskte aynı. Grayton Beach: araç başına $5 (2–8 kişi), tek kişilik araç $4, yaya/bisikletli/ek yolcu $2; 08:00–gün batımı, her gün. Topsail Hill Preserve: $6 (2–8 kişi; fazlası kişi başı $2), tek kişilik araç veya motosiklet $4, yaya/bisikletli $2; 08:00–gün batımı. Deer Lake: $3 (2–8 kişi), yaya/bisikletli/ek yolcu $2, "honor box" ile; 08:00–gün batımı. Deer Lake'in eski "hours-fees" adresi artık 404; değerler parkın ana sayfasından.
- **30A hız sınırları:** DeFuniak Herald haberi okundu (yayın 2 Mart 2017): ilçe meclisi CR-30A trafik çalışmasının hız önerilerini onayladı; öneri 35 mph azami hız (`hiz-30a`, ikincil). İlçenin 14 Şubat 2017 tutanağı kararı doğruluyor (5–0; `hiz-30a-karar`, birincil) ama hız değerlerini yazmıyor; Atkins çalışmasının kendisi bulunamadı. Bugünkü levha hızları ayrıca doğrulanmadı.
- **Timpoochee:** ilçenin Turizm Dairesi sayfası "26 milden fazla çok amaçlı yol"un bakımını yaptığını söylüyor (`timpoochee-ilce-bakim`) ama yolun adını vermiyor; Timpoochee'ye özgü ilçe veya FDOT değeri yine bulunamadı. 19 / 18,5 mil çelişkisi sürüyor.
- **Rosemary Beach ve WaterSound otoparkı:** toplulukların ve kiralama şirketlerinin sitelerinde ziyaretçi otoparkı bilgisi yok (Rosemary Beach'te yalnız kiracılara park kartı). Visit South Walton'ın 2023 park rehberi: Rosemary Beach'te Barrett Square boyunca ilk gelenin aldığı dükkân otoparkı; WaterSound'da The Big Chill ziyaretçilerine açık otopark (ikincil).

## Aylık turist vergisi (TDT)

Walton County Tourism'in "TDT Collections" sayfası (Gatsby sitesi) aylık raporları sayfanın statik sorgu dosyasındaki bir akordeon bileşeninden listeliyor (`/page-data/sq/d/2777485464.json`). Bağlantılar herkese açık PDF ve XLSX dosyalarına gidiyor. South Walton için Walton County Clerk of Courts & County Comptroller'ın "SW TDT Collections History with Monthly FYTD Comparisons" çalışma kitabı FY1999'dan bu yana bütün ayları içeriyor; `thirty_a_tdt_collections.csv` bu kitaptan üretildi (334 ay, her mali yılın aylık toplamı kitaptaki yıllık toplamla birebir aynı). Sütunlar: ay, mali yıl (Ekim–Eylül), vergi bölgesi, o dönemin oranıyla toplam tahsilat, oran değişimlerinden bağımsız %2 payı, kaynak sayfa, URL, erişim tarihi, SHA-256.

**Ay neyi gösteriyor?** Aylık rapor dönemi ayın adıyla ve bir sonraki ayda alınmış olarak veriyor: "Monthly Collections: June 2026 (Received during July 2026)"; dosya adları da "MAY25 collected in JUN25" biçiminde. Yani etiket ayı tahsil ayı değil; tahsilat bir sonraki ay alınıyor. Etiket ayının konaklama (vergiye tabi kiralama) ayı olduğunu açıkça söyleyen bir ifade kaynakta bulunamadı. Vergi oranı yıllar içinde değişti (%3 → %4 → %4,5 → %4 → %5, 1 Ocak 2020'den beri %5); yıllar arası karşılaştırmada `yuzde2_payi_usd` kullanılmalı.

Çalışma kitabı ile aylık PDF raporu küçük farklar gösterebiliyor: Haziran 2026 için South Walton toplamı kitapta 11.945.425,14 $, "FY26 TDT Collections Report – JUN26 collected in JUL26" PDF'inde 11.945.791,53 $ (fark 366,39 $). CSV çalışma kitabını izler; videoda tek ay rakamı söylenecekse kaynak belge birlikte anılmalı.

## Yeniden üretim

`work/gorev-06/referans_tablosu.py` (GÖREV-07 sürümü `work/gorev-07/referans_tablosu.py`) olguları, alıntıları ve konumları içerir; adres, erişim tarihi ve SHA-256'yı `work/referans-belgeler/manifest.json`'dan doldurur ve doğrulayıcıdan geçmeyen tabloyu yazmaz. `work/gorev-06/tdt_csv.py` TDT dosyasını üretir. İkisi de `work/` altındadır (repoya girmez); yeni bir sürüm gözden geçirildikten sonra ayrı commit olarak alınır.

## 10 Ekim 2026 içeriği (GÖREV-11)

GÖREV-11 tabloya 47 satır ekledi (152 satır); yeni konular `plaj-hukuku`, `erisilebilirlik`, `kalabalik`, `etkinlikler`, `tarihce`, yeni kapsamlar `ABD` ve `Okul bölgesi`. Hukuki ve tarihî satırlar yalnız birincil ya da resmî kaynaktan alındı (anayasa ve kanun metni, Senato kanun analizi, ilçe kararı, mahkeme kararı, kurumun kendi sitesi); The Truman Show satırı kurum yayını olduğu için `ikincil` işaretli. Belgeler `work/gorev-11/kaynaklar/` altında, `manifest.json` ile (repoya girmez).

| Konu | Satır | Doğrulandı | Çelişkili | Doğrulanamadı | Yerine geçildi |
|---|---|---|---|---|---|
| Plaj kuralları | 29 | 29 | 0 | 0 | 0 |
| Güvenlik | 13 | 11 | 0 | 0 | 2 |
| Plaj erişimi | 17 | 17 | 0 | 0 | 0 |
| Ulaşım | 19 | 17 | 2 | 0 | 0 |
| Parklar | 8 | 8 | 0 | 0 | 0 |
| Kasırga sezonu | 2 | 2 | 0 | 0 | 0 |
| Sezon ve maliyet | 14 | 13 | 0 | 0 | 1 |
| Genel | 5 | 5 | 0 | 0 | 0 |
| Plaj erişimi hukuku | 14 | 12 | 1 | 1 | 0 |
| Erişilebilirlik | 4 | 3 | 1 | 0 | 0 |
| Ziyaretçiler ve okul tatilleri | 6 | 6 | 0 | 0 | 0 |
| Etkinlikler | 13 | 13 | 0 | 0 | 0 |
| Tarihçe | 8 | 6 | 1 | 1 | 0 |
| **Toplam** | **152** | **142** | **5** | **2** | **3** |

- **Plaj erişimi hukuku:** Florida Anayasası Madde X Bölüm 11; Walton County 2016-23 sayılı kararı; 2018 kanunu (HB 631, s. 163.035) ve süreci; ilçenin 1.194 mülk için açtığı dava ve sonucu (Senato analizi); 2025'te 163.035'in kaldırılması (Ch. 2025-178) ve aynı kanunun erozyon kontrol çizgisi hükmü; 1. Bölge Temyiz Mahkemesi'nin 18 Şubat 2026 kararı (2024 nihai kararı hükümsüz) ve ilçenin aynı davadaki tutumu (2017 kararı yürürlükte değil); 2026-01…2026-10 sayılı ilçe kararları arasında customary use kararı yok; ilçe turizm dairesinin 20 feet geçiş alanı ifadesi (`celiskili`); "yeni yasa imzalandı, özel plaj kalmadı" iddiası (`dogrulanamadi`); video için tek satırlık özet (`türetilmiş`).
- **Erişilebilirlik:** ücretsiz plaj tekerlekli sandalyesi ve yerleri, ADA uygun bölgesel erişimler (`celiskili`: aynı kurum başka sayfada 11 bölgesel erişim diyor), Ed Walline erişim matları.
- **Ziyaretçiler ve okul tatilleri:** 2025 ziyaretçi çalışmasının ilk beş pazarı; Atlanta (Gwinnett), Nashville (MNPS), Dallas–Fort Worth (Dallas ISD), Birmingham (Jefferson County Schools), Houston (Houston ISD) 2026–27 güz ve bahar tatilleri. Metronun en büyük okul bölgesinin seçimi bizim seçimimizdir (notta yazılı).
- **Etkinlikler:** 30A Songwriters Festival, 30A Wine Festival, Seaside School Half Marathon, South Walton Beaches Wine & Food Festival, Digital Graffiti (iki yılda bir; 2027'de yok), Seaside 4 Temmuz, Halloweener Derby, Seeing Red Wine Festival, Rosemary Beach Uncorked, 30A 10K, Seaside Holiday Parade, Seaside yılbaşı, Escape to Create (2027'de ara).
- **Tarihçe:** Seaside'ın arazisi ve kuruluşu, DPZ'nin Seaside, Rosemary Beach ve Alys Beach kayıtları, The Truman Show, New Urbanism tüzüğü; Alys Beach'in kuruluş yılı `dogrulanamadi`.
- **Genel:** 30A'nın FDOT envanterindeki adı (W/E CO HWY 30A) ve Destin ile Fort Walton Beach'in Okaloosa County'de olduğu (ABD Nüfus Bürosu adres servisi).

### Türkçe ifadeler

`studio/destinations/thirty_a_references_tr.csv` (`id, ifade_tr`; profil sabiti `REFERENCE_TRANSLATIONS`) her satırın Türkçe ifadesini tutar; kanıt paketi bunu satırın ifadesi olarak, tablonun İngilizce cümlesini "kaynak satırının İngilizce ifadesi" olarak yazar. Yeni satır eklenirken Türkçe ifadesi de eklenir (test bütün satırları arar).

### Trafik tablosu (FDOT)

`studio/destinations/thirty_a_traffic.csv` (profil sabiti `TRAFFIC_| Konu | Satır | Doğrulandı | Çelişkili | Doğrulanamadı | Yerine geçildi |
|---|---|---|---|---|---|
| Plaj kuralları | 29 | 29 | 0 | 0 | 0 |
| Güvenlik | 13 | 11 | 0 | 0 | 2 |
| Plaj erişimi | 17 | 17 | 0 | 0 | 0 |
| Ulaşım | 19 | 17 | 2 | 0 | 0 |
| Parklar | 8 | 8 | 0 | 0 | 0 |
| Kasırga sezonu | 2 | 2 | 0 | 0 | 0 |
| Sezon ve maliyet | 14 | 13 | 0 | 0 | 1 |
| Genel | 5 | 5 | 0 | 0 | 0 |
| Plaj erişimi hukuku | 14 | 12 | 1 | 1 | 0 |
| Erişilebilirlik | 4 | 3 | 1 | 0 | 0 |
| Ziyaretçiler ve okul tatilleri | 6 | 6 | 0 | 0 | 0 |
| Etkinlikler | 13 | 13 | 0 | 0 | 0 |
| Tarihçe | 8 | 6 | 1 | 1 | 0 |
| **Toplam** | **152** | **142** | **5** | **2** | **3** |`) referans tablosunun yanında, aynı kaynak sütunlarıyla (`kaynak_adi, kaynak_sahibi, kaynak_url, belge_konumu, belge_tarihi, erisim_tarihi, belge_sha256, guven, durum, yeniden_kontrol_tarihi, not`) tutulur; ek sütunlar `tur, yol, sayim_noktasi, aciklama, yil, ay, kategori, deger, birim, isaret, etiket`. İçerik: FDOT'un 2025 Walton County AADT raporundaki CR 30A (7) ve US 98 (9) sayım noktaları (iki yön, araç/gün; işaret C hesaplanmış, F ilk yıl tahmini — raporun kendi açıklaması) ve 2025 Peak Season Factor Category raporundaki dört Walton kategorisi (6000 countywide, 6001 recreational, 6010 I-10, 6098 US98) için aylık oran ve yoğun sezon haftaları. FDOT haftalık mevsim faktörü (SF) yayımlar; **aylık oran bizim hesabımızdır**: ayın her günü kendi haftasının SF değerini alır, ay ortalaması alınır, trafiğin yıllık ortalamaya oranı 1/SF kabul edilir (FDOT: AADT = sayım × SF). Raporda sayım noktalarının hangi kategoriye bağlı olduğu yazmaz. Üretim betiği `work/gorev-11/trafik.py`.

**Trafik video dili:** FDOT AADT bir sayım noktasındaki yıllık ortalama günlük araç sayısıdır (iki yön); "<yer> sayım noktasında 2025 yıllık ortalaması" denir, yolun tamamı için tek sayı söylenmez. Aylık oranlar FDOT'un haftalık mevsim faktörlerinden bizim hesabımızdır ve kategori söylenir; sıkışıklık ya da yolculuk süresi iddiası yapılmaz.
