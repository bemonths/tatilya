# GÖREV-02 — İlk video için kaynak keşfi

Tarih: 7 Ekim 2026 · Örnek istekler: 2026-10-06 23:32–23:57 UTC · Hazırlayan: Claude Code · Karar: proje yöneticisi

Bu belge, kanalın ilk videosu ("30A'ya ilk kez gidecekler için tam karar rehberi") için on soru alanında en iyi kaynağı ve kaynağın programa bağlanmaya uygun olup olmadığını değerlendirir. Kod yazılmadı. Her alanda en fazla üç aday kaynağa bakıldı; iyi bir resmî kaynak doğrulanınca o alanda durulup sonraki alana geçildi (Alan 9'daki dört alt konu için dört kaynağa bakıldı). Değerlendirme, `docs/DEVIR/03_VERI_KAYNAKLARI_VE_DOGRULAMA.md` içindeki kabul sürecine göre yapıldı ve üç düzeyde verildi: **kullanılabilir**, **sınırlı**, **kullanılamaz**.

Örnek istekler az sayıda, sıralı ve repo adresini içeren User-Agent ile yapıldı (`30AStudio/0.6 (+https://github.com/bemonths/tatilya)`). Giriş gerektiren hiçbir yere girilmedi, form gönderilmedi. Ham örnekler ve istek kayıtları yerel `work/gorev-02/` klasöründe; repoya konmadı. Book>Direct'in herkese açık istemci anahtarı hiçbir dosyaya yazılmadı. Kaynaklardaki metinler kopyalanmadı; olgular kendi cümlelerimizle özetlendi. Bu belgedeki sayılar örnek anına aittir; test sabiti veya kesin değer değildir.

Makinece okunabilir liste: `kaynaklar.csv`. Plaj erişimi → mahalle önizlemesi: `plaj-mahalle-onizleme.csv`.

## Özet

| # | Soru alanı | En iyi kaynak | Değerlendirme | Ana boşluk |
|---|---|---|---|---|
| 1 | Mahalleler | Visit South Walton mahalle dizini (16 mahalle, kararlı kimlik) | kullanılabilir | Sınır poligonu yok; "30A" alt kümesi programın kararı |
| 2 | Plaj erişimi → mahalle | Visit South Walton park ve ulaşım rehberi (2023) | sınırlı | 53 erişimin 9'u eşlenebildi; rehber Rosemary Beach ve Alys Beach için "halka açık erişim yok" diyor |
| 3 | Plaj kuralları ve güvenlik | Walton County Ordinance 2025-22 (24 Kasım 2025) + SWFD | kullanılabilir | Taranmış PDF; güncel cankurtaran saatleri ve alkol kuralı doğrulanamadı |
| 4 | İklim | NOAA NCEI 1991–2020 normalleri (Destin, ~32 km) | kullanılabilir | 30A içinde istasyon yok; hazır nem ve deniz suyu normali yok |
| 5 | Kasırga riski | NOAA NHC HURDAT2 | kullanılabilir | 30A'ya özgü aylık sayı bizim hesabımız olacak |
| 6 | Kalabalık ve sezon | Walton County Tourism aylık turist vergisi tahsilatları | sınırlı | Makinece okunabilir yol bulunamadı; para cinsinden ve South Walton geneli |
| 7 | Konaklama ve fiyat | Book>Direct tarihli arama | sınırlı | Örnek aramalarda liste fiyatı hiç dolu değildi; vergi/ücret belirtilmiyor |
| 8 | Ulaşım | FAA havalimanı verisi; Visit South Walton rehberi; mevzuat | kullanılabilir / sınırlı | 30A'ya özgü golf arabası kararı ve hız limitleri doğrulanamadı; "araba gerekli mi" için resmî cevap yok |
| 9 | Yapılacaklar | Visit South Walton Events | kullanılabilir (etkinlik) | Eyalet parkı ve orman sayfaları otomatik erişime kapalı; kumul gölü isim listesi yok |
| 10 | Günlük ihtiyaç | OpenStreetMap (Overpass) | sınırlı | Resmî envanter yok; tamlık bilinmiyor; ODbL |

## Alan 1 — Mahalleler

**1A. Visit South Walton mahalle dizini, mahalle sayfaları ve "16 Beachside Neighborhoods" medya kiti**
- URL: https://www.visitsouthwalton.com/neighborhoods/ (her mahalle için `/neighborhoods/<slug>/`), https://www.visitsouthwalton.com/media-kit/16-Beachside-Neighborhoods/
- Sahibi / otorite: Walton County Tourism Department (Visit South Walton; sayfa altında "© Walton County TDC"). Turizm mahalleleri için resmî kurum; idari sınır otoritesi değil.
- Verdiği alanlar: dizin sayfasındaki gömülü JSON'da 16 kayıt; her kayıtta 24 haneli `id`, `permalink`, ad, tek cümlelik tanıtım, temsilî nokta (`lat`/`lng`), `modified` ve etkinlik etiketleri (Walkable, Tranquil, Architecture, Family vb.). Medya kiti ve mahalle sayfaları her mahalle için tanıtım metni veriyor.
- Anlam ve sınır: 16 mahallelik liste tam (sitede 16 mahalle sayfası var). Sınır poligonu yok, koordinatlar yalnız temsilî nokta. Tanımlar ve etiketler turizm tanıtımıdır, ölçüm değildir. Medya kiti tarihsiz ve kısmen eski. Kaynak "South Walton" diyor; "30A" diye bir alt küme tanımlamıyor. Batı→doğu sırası açıkça yazılmıyor, fakat kaynağın kendi noktalarının boylam sırası ve kayıt kimliklerinin artış sırası aynı diziyi veriyor.
- Teknik yol: tek GET ile HTML içindeki JSON; kararlı kimlik `id` + `permalink`. Tanıtım metinleri HTML'den.
- Güncellenme: kayıt başına `modified` (çoğu 2025-05-09; Santa Rosa Beach 2026-09-14, Sandestin 2026-05-14, Gulf Place 2026-01-07, Seaside 2025-08-04, Seagrove 2024-12-05). Medya kitinde tarih yok.
- Kullanım: robots.txt yalnız `/userfiles/` ve `/search/` yollarını yasaklıyor. Kullanım şartları içeriği telifle koruyor ve kişisel/ticari olmayan kullanım dışında çoğaltmaya izin vermiyor. Metin aynen kullanılmamalı; olgular kendi cümlemizle ve "Visit South Walton" atfıyla verilmeli.
- Örnek istek: `GET /neighborhoods/` — 2026-10-06 23:32 UTC, HTTP 200, 156 KB; 16 kayıtlık JSON döndü.
- **Değerlendirme: kullanılabilir.** Resmî turizm kurumunun kararlı kimlikli, tam 16'lık listesi; programın 13 mahallesiyle ad ve sıra olarak birebir örtüşüyor.

Kaynağa göre 13 mahallenin karakteri (dizin etiketleri ve tanıtım metinlerinden, kendi cümlelerimizle; W = "Walkable", T = "Tranquil" etiketi):

| # | Mahalle | Etiket | Kaynağın vurgusu |
|---|---|---|---|
| 1 | Dune Allen | T | Doğa ve sükûnet, kıyı kumul gölleri, patikalar |
| 2 | Gulf Place | W | Renkli kasaba merkezi, sanatçı kolonisi; her şeye kısa yürüyüş |
| 3 | Santa Rosa Beach | T | 1910'da kurulmuş; South Walton'ın en eski ve en büyük mahallesi olarak geniş bir alanı kapsıyor |
| 4 | Blue Mountain Beach | T | Doğal ve rahat; yüksek kumullar; bölgenin en yüksek rakımı |
| 5 | Grayton Beach | T | Rahat ve yerel; dar sokaklar, eski tarz ahşap evler; devlet parkı |
| 6 | WaterColor | W | Geniş doğal alan ve koruma vurgusu; küçük kasaba havası |
| 7 | Seaside | W | New Urbanism kasabasının örneği olarak tanıtılıyor |
| 8 | Seagrove | T | Ağaç örtüsü korunmuş; eski ve yeni evlerin karışımı |
| 9 | WaterSound | T | Çevreyi gözeterek tasarlanmış topluluk; Deer Lake State Park |
| 10 | Seacrest | T | Pavyon çevresinde kasaba meydanı, lagün havuzu |
| 11 | Alys Beach | W, T | Yürünebilirlik ve mimari bütünlük odaklı tasarım; beyaz stuko mimari |
| 12 | Rosemary Beach | W | Geniş yeşil alanlar, yaya ve bisiklet yolları |
| 13 | Inlet Beach | T | Sakin sokaklar; South Walton'ın en büyük bölgesel plaj erişimi |

**1B. Walton County GIS — `WaltonCounty_Communities_WFL1`**
- URL: https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/ArcGIS/rest/services/WaltonCounty_Communities_WFL1/FeatureServer
- Sahibi / otorite: Walton County GIS; idari/planlama verisi için resmî.
- Verdiği alanlar: servis açıklaması toplulukları gösterdiğini söylüyor, fakat katmanda yalnız tek bir ilçe poligonu var; topluluk/mahalle sınırı yok. İlçenin servis listesinde (186 servis, yalnız adlara bakıldı) 30A mahallelerini kapsayan bir topluluk katmanı görülmedi; alt bölüm (plat) poligonları mahalle değil.
- Teknik yol: ArcGIS REST (JSON/GeoJSON); `OBJECTID`, `GlobalID`. Güncellenme: EditDate 2025-10-07. Kullanım: ArcGIS host'unda robots dosyası yok; öğe kaydında lisans alanı boş.
- Örnek istek: katman 1 sorgusu — 23:34 UTC, HTTP 200; tek kayıt ("Walton").
- **Değerlendirme: kullanılamaz.** Adına rağmen mahalle listesi veya sınırı içermiyor.

**1C. OpenStreetMap yer (place) verisi — Overpass API**
- URL: https://overpass-api.de/api/interpreter
- Sahibi / otorite: OpenStreetMap katkıcıları; resmî değil, çoğu noktada USGS GNIS kimliği var.
- Verdiği alanlar: yer adı, temsilî nokta, yer türü, `gnis:feature_id`, Wikidata kimliği.
- Anlam ve sınır: 13 mahallenin 12'si nokta olarak var, Gulf Place yok. Adlar GNIS biçiminde ("Dune Allen Beach", "Seacrest Beach" gibi). Hiçbir mahalle için sınır poligonu yok. "Seacrest Beach" noktası Alys Beach'in doğusunda; Visit South Walton'da Seacrest, Alys Beach'in batısında.
- Teknik yol: Overpass QL JSON ya da bölgesel extract; OSM kimliği düzenlemeyle değişebilir, GNIS kimliği daha kararlı. Güncellenme: sürekli (yanıtta `timestamp_osm_base`).
- Kullanım: ODbL; "© OpenStreetMap contributors" atfı gerekli, türetilmiş veritabanı yayımlanırsa aynı lisansla paylaşılmalı. Overpass ve openstreetmap.org robots.txt dosyaları API yollarını robotlara kapatıyor; kalıcı kullanım için bölgesel extract önerilir.
- Örnek istek: tek Overpass sorgusu — 23:36 UTC, HTTP 200, 40 öğe.
- **Değerlendirme: sınırlı.** Ad ve konum çapraz kontrolü için yararlı; resmî değil, Gulf Place eksik, sınır yok.

**Alanın sonucu.** En iyi kaynak Visit South Walton'ın mahalle dizinidir (1A). Kaynağın noktalarına göre batıdan doğuya 16 mahalle: Miramar Beach, Seascape, Sandestin, Dune Allen, Gulf Place, Santa Rosa Beach, Blue Mountain Beach, Grayton Beach, WaterColor, Seaside, Seagrove, WaterSound, Seacrest, Alys Beach, Rosemary Beach, Inlet Beach. Programın 13 mahallesi, ilk üç mahalle çıkarılınca bu listeyle ad ve sıra olarak birebir aynı. "30A" alt kümesini tanımlayan resmî bir liste bulunamadı; üç mahallenin dışarıda bırakılması programın kararıdır. Dikkat: kaynak Santa Rosa Beach'i hem mahalle hem geniş bir şemsiye alan olarak anlatıyor; Seacrest'in konumu OSM ile çelişiyor (videoda kullanmadan önce doğrulanmalı).

## Alan 2 — Plaj erişiminin mahalleye bağlanması

**2A. Visit South Walton: plaj erişim haritası, mahalle sayfaları ve "Guide to Beach Parking and Transportation" rehberi**
- URL: https://www.visitsouthwalton.com/beach-bay-access-locations/, https://www.visitsouthwalton.com/neighborhoods/<slug>/, https://www.visitsouthwalton.com/blog/guide-beach-parking-transportation/
- Sahibi / otorite: Walton County Tourism Department (Visit South Walton).
- Verdiği alanlar: haritadaki işaretçilerde kimlik, ad, adres, posta şehri, koordinat, tür ve olanaklar var; **mahalle alanı yok** (`city` yalnız posta şehri). Park rehberi ise erişimleri **mahalle başlıkları altında** ad, adres ve araç kapasitesiyle listeliyor; Rosemary Beach ve Alys Beach başlıklarında "No Public Beach Access" yazıyor; Seacrest başlığında adı verilmeden "3 neighborhood beach access" geçiyor. Mahalle sayfalarında yapılandırılmış liste yok; beş bölgesel erişim düz metinde adıyla anılıyor.
- Anlam ve sınır: rehber 2023-05-04 tarihli ve ağırlıkla bölgesel erişimleri listeliyor; mahalle erişimlerinin çoğu yok, 2026'da eklenen "Seagrove Regional Beach Access" da yok. Rehberde listelenmemek "erişim yok" demek değildir; yalnız Rosemary Beach ve Alys Beach için açık ifade var. Kaynağın kendi sayfaları arasında bir çelişki var: Santa Clara RBA rehberde Seagrove başlığı altında, Santa Rosa Beach mahalle sayfasında ise anılıyor.
- Teknik yol: harita HTML içi JSON (`initMarkers`, 24 haneli `id`); rehber düz HTML metni (eşleşme için ad ve adres kullanılabilir).
- Güncellenme: harita sayfasında "Latest map update: Sep 21, 2026 6:56:10 pm" (saat dilimi yok); rehberde yayın tarihi 2023-05-04, değişiklik tarihi alanı otomatik üretiliyor.
- Kullanım: Visit South Walton kullanım şartları metnin kopyalanmasını kısıtlıyor; olgular atıfla kullanılmalı.
- Örnek istek: harita sayfası — 2026-10-06 23:43 UTC, HTTP 200, 70 işaretçi (programdaki 53 kimliğin hepsi bugün de var); rehber — 23:47 UTC, HTTP 200.
- **Değerlendirme: sınırlı.** Erişim kimliği ve konumu için en iyi kaynak; mahalle bağı yalnız rehberde ve yalnız bir alt küme için doğrudan var.

`plaj-mahalle-onizleme.csv` bu rehberden üretildi: 53 erişimin 9'u, rehberdeki kayıtla ad ve/veya adres birebir eşleştiği için dolduruldu; diğer 44 satır boş bırakıldı (kaynak vermiyor; tahmin yapılmadı).

| Rehberdeki mahalle başlığı | Eşleşen program erişimi | Eşleşme |
|---|---|---|
| Dune Allen | Dune Allen RBA; Fort Panic RBA - 43 | ad (+ adres) |
| Gulf Place | Ed Walline RBA - 39 | ad + adres |
| Santa Rosa Beach | Gulfview Heights RBA - 37 | ad + adres |
| Blue Mountain Beach | Blue Mountain RBA - 36 | ad + adres |
| Grayton Beach | Bets "Beachmama" Haynes RBA (44 Hotz Ave) | adres (rehberde ad yok) |
| Seagrove | Santa Clara RBA - 17; Walton Dunes - 8 | ad + adres / ad + kapı no |
| Inlet Beach | Inlet Beach Regional Access - 2a, 2b, 2c | adres + ad kökü |

Rehberdeki "San Juan Beach Access" (Seagrove) programdaki "San Juan - 18" ile yalnız ad olarak benziyor; adresler farklı olduğu için eşlenmedi.

**2B. Walton County GIS plaj erişimi katmanları (`beachaccesses/0` ve `EnerGov_Additional/26`)**
- URL: https://services1.arcgis.com/TaXHPwWfIMuzJ7Ov/ArcGIS/rest/services/beachaccesses/FeatureServer/0
- Sahibi / otorite: Walton County GIS (katmandaki telif notu: Walton County TDC).
- Verdiği alanlar: katman 0'da 79 nokta (adres, tür, ad, ADA, otopark, tuvalet, cankurtaran, bayrak, erişim türü); katman 26'da 114 nokta (32'si acil araç erişimi). İkisinde de topluluk veya mahalle alanı yok.
- Anlam ve sınır: katman 0'ın açıklaması 2014'te turizm sitesiyle doğrulandığını söylüyor; bazı kayıtlar "Unconfirmed location" notu taşıyor. Erişim numaraları Visit South Walton'dan farklı (ör. Santa Clara 17 ↔ 18), numara iki yayıncı arasında ortak kimlik olamaz. İlçe katmanında Visit South Walton'da olmayan bir bölgesel erişim de var ("Oyster Lake"; incelenmedi). Meta veride düzenleme yetenekleri de listeleniyor; verinin kim tarafından güncellendiği doğrulanmadı.
- Teknik yol: ArcGIS REST; `OBJECTID`, `GlobalID`. Güncellenme: katman 0 son düzenleme 2026-05-26; katman 26 kayıtları 2026-10-04'te toplu düzenlenmiş. Kullanım: lisans alanı boş.
- Örnek istek: katman 0 tam sorgu — 23:34 UTC, HTTP 200, 79 kayıt.
- **Değerlendirme: kullanılamaz** (bu soru için). Mahalle alanı yok, numaralandırma Visit South Walton ile uyuşmuyor.

**2C. OpenStreetMap topluluk sınırları — Overpass**
- 1C ile aynı sorgu ve lisans. 13 mahallenin hiçbiri için sınır poligonu yok; bölgede yalnız Miramar Beach sayım bölgesi, ilçe ve şehir sınırları gibi poligonlar var.
- **Değerlendirme: kullanılamaz.** Sınır yok; olsaydı bile nokta-poligon ataması bir türetim olurdu ve ODbL paylaşım şartı devreye girerdi.

**Alanın sonucu.** Erişim başına mahalleyi bütün erişimler için veren resmî bir kaynak yok. Visit South Walton'ın 2023 tarihli park rehberi, bölgesel erişimlerin çoğunu mahalle başlıkları altında veriyor; buna göre 53 erişimin 9'u eşlendi (önizleme CSV). Aynı rehber Rosemary Beach ve Alys Beach için açıkça "halka açık plaj erişimi yok" diyor; bu, yönetici notundaki "bu aralıklarda listelenmemiş" gözlemini o iki mahalle için resmî bir cümleyle destekliyor (2023 tarihli olduğu belirtilerek). WaterColor, Seaside ve WaterSound başlıklarında rehber plaj erişimi değil yalnız otopark bilgisi veriyor; bu "erişim yok" anlamına gelmez. Kalan 44 erişim için seçenekler (karar yöneticinin): (1) Walton County TDC'den resmî bir erişim→mahalle listesi istemek; (2) programın kendi mahalle sınırlarını tanımlayıp nokta-poligon ile atama yapmak ve sonucu "kaynak verisi değil, program türetimi" diye etiketlemek.

## Alan 3 — Plaj kuralları ve güvenlik

**3A. Walton County Code, Bölüm 22 "Waterways and Beach Activities" — Ordinance 2025-22 (ilçe sitesi; Municode kanalı ayrıca denendi)**
- URL: https://www.mywaltonfl.gov/DocumentCenter/View/44588 (dizin: https://www.mywaltonfl.gov/654/Links-to-Codes-Ordinances-Statutes; köpek izni: https://www.mywaltonfl.gov/1329/Beach-Driving-Charter-Fishing-Dog-Beach; Municode: https://library.municode.com/fl/walton_county/codes/code_of_ordinances)
- Sahibi / otorite: Walton County Board of County Commissioners; kuralların yasal sahibi. Municode yalnız yayıncı.
- Verdiği alanlar (bölüm numaralı): köpek (§22-31), gece kamp yasağı ve ateş/ızgara/havai fişek (§22-54(a)–(b)), cam (§22-54(d)), gece eşya bırakma (§22-54(g)), plaj/su kapatma emirleri (§22-54(h)), çukur ve metal kürek, çadır/şemsiye ve 15 ft kuralı (§22-54(q)–(s)), yuvalama sezonunda gece araç yasağı (§22-57), ilçe plaj otoparkında gece park yasağı (§22-61), cezalar (§22-62). Deniz kaplumbağası yuvalama sezonu tanımı: 1 Mayıs–31 Ekim.
- Anlam ve sınır: yürürlükteki yasal metin; 24 Kasım 2025'te kabul edildi ve kabulle yürürlüğe girdi (son sayfa doğrulandı). Kuralların çoğu yalnız ilçenin sahip olduğu, kiraladığı veya bakımını yaptığı plajlar için geçerli; hangi kıyı kesiminin kamuya ait olduğunu göstermiyor. Bölüm 22'de alkol hükmü yok (bu "serbest" demek değildir; başka mevzuatta olabilir). Bayrak renklerini ve cankurtaran sezonunu tanımlamıyor.
- Teknik yol: taranmış PDF (27 sayfa, metin katmanı yok); kurallar elle veya OCR ile bölüm numaralı bir tabloya alınmalı. Kimlik: ordinance numarası + bölüm numarası. Yeni sürümler yeni ordinance numarasıyla çıkıyor; dizin sayfası izlenmeli. Municode kanalı yalnız uygulama kabuğu döndürüyor, metin belgelenmemiş bir iç API'den geliyor.
- Güncellenme: düzensiz, her değişiklik yeni ordinance ile.
- Kullanım: ilçe sitesinin robots.txt'si belge yolunu engellemiyor. Resmî belge; ordinance ve bölüm numarasıyla atıf yapılmalı.
- Örnek istek: PDF — ilk iki deneme HTTP 522 (sunucu zaman aşımı), üçüncüsü 2026-10-06 23:45 UTC'de HTTP 200, 3,7 MB, imzalı ve mühürlü 27 sayfa.
- **Değerlendirme: kullanılabilir** (ilçe PDF kanalı; Municode kanalı kullanılamaz). En yetkili ve tarihli metin; kurallar elle tabloya alınmalı.

**3B. South Walton Fire District — Beach Safety**
- URL: https://www.swfd.org/beach-safety (alt sayfalar: surf conditions, flag conditions resource, beach bonfires, FAQ)
- Sahibi / otorite: South Walton Fire District; cankurtaranları çalıştıran, bayrağa karar veren ve ateş izni veren kurum.
- Verdiği alanlar: bayrak renkleri ve anlamları (yeşil, sarı, kırmızı, çift kırmızı = suya giriş kapalı, mor = deniz canlıları), bayrağın günde iki kez değerlendirildiği, o anki bayrak, ateş izni kuralları ve saatleri.
- Anlam ve sınır: bayrak anlamları ve ateş kuralları için birincil kaynak. O anki bayrakta zaman damgası yok; bayrak ilçe genelindeki en tehlikeli koşula göre seçiliyor. SSS'deki cankurtaran bilgisi (8 kule, 10:00–18:00, 1 Mart–30 Eylül) tarihsiz ve turizm sayfasıyla çelişiyor.
- Teknik yol: HTML; anlık bayrak HTML'de sınıf adı ve açıklama metni olarak geliyor; herkese açık bir gömme widget betiği var. Kimlik sayfa yolu.
- Güncellenme: bayrak günde iki kez; statik sayfalarda tarih yok.
- Kullanım: robots.txt yalnız yönetim dizinlerini kapatıyor. Kullanım şartları ticari kullanım için yazılı izin istiyor; düzenli bayrak yoklaması planlanırsa SWFD'ye sorulmalı.
- Örnek istek: flag conditions sayfası — 23:37 UTC, HTTP 200; o anki bayrak "kırmızı + mor".
- **Değerlendirme: sınırlı.** Bayrak anlamı ve ateş kuralları için yetkili; cankurtaran bilgisi eski ve tarihsiz, ticari kullanım izne bağlı.

**3C. Walton County Tourism Department plaj sayfaları (Visit South Walton "Beach Safety", Walton County Tourism "Leave No Trace")**
- URL: https://www.visitsouthwalton.com/beach-safety/, https://www.waltoncountyfltourism.com/leave-no-trace/
- Sahibi / otorite: Walton County Tourism Department; kuralların yasal sahibi değil, ziyaretçiye yönelik özet yayımlıyor.
- Verdiği alanlar: bayrak uyarıları, kurallar listesi (cam yasağı, izin gerektiren işler, 15 ft koridor, çadır 10×10 ft vb.), cankurtaran sezonu: bölgesel erişimlerde 1 Mart–31 Ekim ve yıl boyu sınırlı devriye (doğrulandı).
- Anlam ve sınır: ikincil özet; tarih ve sürüm yok. Bazı ifadeler 2025-22 ile çelişiyor (ör. gece eşya saati ve izinsiz bırakılabilecek eşyalar, yuvalama sezonu "Mayıs–Kasım"; çift kırmızı bayrak için "criminal charges" ifadesi, yönetmelikte sivil ihlal).
- Teknik yol: HTML; kimlik sayfa yolu. Güncellenme: gösterilmiyor.
- Kullanım: Visit South Walton şartları içeriğin kopyalanmasını ve yeniden yayımlanmasını kısıtlıyor; olgular kendi cümlelerimizle ve atıfla kullanılmalı.
- Örnek istek: beach-safety sayfası — 23:37 UTC, HTTP 200.
- **Değerlendirme: sınırlı.** Cankurtaran sezonu için en güncel görünen resmî ifade; ama tarihsiz ve yönetmelikle kısmen çelişiyor, yalnız çapraz kontrol için.

Kural konusu × kaynak:

| Konu | Ordinance 2025-22 | SWFD | Turizm sayfaları |
|---|---|---|---|
| Uyarı bayrakları | Kapatma emirlerine uyma zorunluluğu; renkler tanımlı değil | Var: renkler, anlamları, günde 2 değerlendirme, anlık bayrak | Var: renkler, ceza uyarısı |
| Cankurtaran sezonu/saat | Yok | 1 Mart–30 Eylül, 10:00–18:00, 8 kule (tarihsiz, eski görünüyor) | 1 Mart–31 Ekim; saat yok |
| Köpek | Var (§22-31): yalnız izinle (ilçe mülk sahibi veya daimi sakin), saat sınırıyla | Yok | "İzin gerekir" |
| Alkol | Bölüm 22'de yok | Yok | Yok |
| Cam | Var (§22-54(d)) | — | Var |
| Çadır/şemsiye | Var: çadır en fazla 10×10 ft, plajın kara tarafındaki yarısında (Grayton Beach hariç), aralarda 4 ft; şemsiye en fazla 8×8 ft; ekipman duvar/kumul eteği/bitki çizgisine 15 ft'ten yakın konamaz | Yok | Var (ifade farklı) |
| Ateş/ızgara/havai fişek | Var (§22-54(b)): izin, mesafe ve sezon saatleri | Var: aynı saatler, izin şartları | İzin gerekir |
| Gece/aydınlatma | Kısmi: gece kamp yasağı, yuvalama sezonunda gece araç yasağı; mülk aydınlatması ayrı yönetmelikte (doğrulanamadı) | Ateşin yuvalara mesafesi | Sezon farklı yazılmış |
| Gece eşya bırakma | Var (§22-54(g)): gün batımından 1 saat sonra ile gün doğumundan 1 saat sonra arası izinsiz eşya terk edilmiş sayılır; olağanüstü hâlde 24 saatte kaldırılmalı | Yok | Var (kısmen çelişkili) |
| Kamu/özel ayrımı | Kurallar ilçe plajlarına uygulanıyor; kesim haritası yok | Yok | Yok |

**Alanın sonucu.** En iyi kaynak 24 Kasım 2025 tarihli Ordinance 2025-22'dir; köpek, cam, çadır/şemsiye, 15 ft kuralı, ateş, gece eşya, kapatma emirleri ve cezalar için ölçüleri ve saatleriyle yasal dayanak veriyor. Taranmış PDF olduğu için kurallar elle veya OCR ile bölüm numaralı bir tabloya alınmalı. Bayrak anlamları ve ateş izni için SWFD birincil kaynaktır. Boşluklar: 2026 cankurtaran saatleri ve kule sayısı resmî ve güncel bir sayfada doğrulanamadı (kaynaklar çelişiyor); alkol üç kaynakta da yok; hangi kıyı kesiminin kamuya ait olduğunu gösteren bir kaynak bulunamadı.

## Alan 4 — İklim

**4A. NOAA NCEI U.S. Climate Normals 1991–2020 (aylık ve saatlik normaller, sürüm 1.0.1)**
- URL: https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals — anahtarsız API kalıbı: `https://www.ncei.noaa.gov/access/services/data/v1?dataset=normals-monthly-1991-2020&stations={ID}&startDate=0001-01-01&endDate=9996-12-31&dataTypes=MLY-TAVG-NORMAL,MLY-TMAX-NORMAL,MLY-TMIN-NORMAL,MLY-PRCP-NORMAL&includeAttributes=true&format=csv`; istasyon başına tam CSV için NOAA'nın S3 aynası: `https://noaa-normals-pds.s3.amazonaws.com/normals-monthly/1991-2020/access/{ID}.csv`
- Sahibi / otorite: NOAA NCEI; ABD'nin resmî iklim normallerini üreten kurum.
- Verdiği alanlar: aylık ortalama, en yüksek ve en düşük sıcaklık (°F), aylık yağış (inç); ayrıca standart sapma, sıcak gün ve yağışlı gün sayıları, her değer için bayrak ve yıl sayısı. Aylık normallerde nem yok; saatlik normallerde çiy noktası ve ısı indeksi var, bağıl nem yok.
- Uygun istasyonlar (30A merkezine uzaklık): Destin–Fort Walton Beach Havalimanı USW00053853 (kıyı, ~32 km; batı ucuna ~20 km), NW Florida Beaches Havalimanı USW00073805 (~35 km; körfez kenarında; yağış normali tahmini "E" bayraklı), DeFuniak Springs USC00082220 (iç kesim, ~44 km kuzeyde). Çiy noktası için saatlik normali olan en yakın istasyon Eglin AFB USW00013858 (~39 km).
- Anlam ve sınır: 30 yıllık normaller, tek yıl değil. 30A'nın içinde istasyon yok ve yakındaki istasyonların hiçbiri "standart" (en az 24 yıl gerçek veri) bayraklı değil; Destin "R" bayraklı (en az 10 yıl gerçek veri, eksik aylar komşu istasyonlardan tahmin). Değerler "30A'ya en yakın kıyı istasyonu normali" diye etiketlenmeli ve bayraklar saklanmalı.
- Teknik yol: resmî CSV/JSON API, anahtarsız; kimlik = GHCN istasyon kodu + ay + değişken kodu.
- Güncellenme: on yılda bir üretilen ürün (v1.0.0 Mayıs 2021, v1.0.1 2023). Yanıtta güncelleme tarihi yok.
- Kullanım: ABD federal verisi, kısıt yok; atıf önerilir (DOI 10.25921/wck8-er13). NCEI robots.txt `/data*` yolunu yasaklıyor; API (`/access/services/`) ve S3 aynası serbest.
- Örnek istek: API, Destin + DeFuniak + NW Florida Beaches — 2026-10-06 23:34 UTC, HTTP 200, 36 satır (3 istasyon × 12 ay), bayraklarıyla.
- **Değerlendirme: kullanılabilir.** Resmî, anahtarsız ve kararlı kimlikli; istasyon uzaklığı ve bayrak etiketlenerek kullanılmalı.

Destin–Fort Walton Beach Havalimanı 1991–2020 normalleri (°F, inç; bayrak R):

| Ay | Ort. | Maks. | Min. | Yağış |
|---|---:|---:|---:|---:|
| Ocak | 54,2 | 63,1 | 45,3 | 4,52 |
| Şubat | 56,9 | 65,8 | 47,9 | 4,96 |
| Mart | 62,2 | 70,7 | 53,6 | 4,70 |
| Nisan | 68,1 | 76,2 | 60,1 | 4,55 |
| Mayıs | 75,8 | 83,5 | 68,0 | 3,22 |
| Haziran | 81,5 | 88,9 | 74,1 | 4,70 |
| Temmuz | 83,6 | 90,9 | 76,2 | 5,77 |
| Ağustos | 83,2 | 90,6 | 75,8 | 6,08 |
| Eylül | 80,5 | 88,5 | 72,4 | 5,18 |
| Ekim | 72,1 | 80,9 | 63,2 | 2,82 |
| Kasım | 62,6 | 72,1 | 53,0 | 4,13 |
| Aralık | 56,6 | 65,6 | 47,5 | 4,72 |

İç kesimdeki DeFuniak Springs ile kıyaslandığında kıyıda kış geceleri daha ılık, yaz öğleden sonraları biraz daha serin ve yaz yağışı daha az görünüyor.

**4B. NCEI Coastal Water Temperature Guide**
- URL: https://www.ncei.noaa.gov/products/coastal-water-temperature-guide — Sahibi: NOAA NCEI.
- Durum: sayfa ürünün 5 Mayıs 2025'te kapatıldığını söylüyor; artık tablo veya istasyon listesi yok, verinin NOS gelgit istasyonları, NDBC ve OISST üzerinden alınabileceğini belirtiyor.
- Örnek istek: ürün sayfası — 23:36 UTC, HTTP 200; kapanış notu geldi.
- **Değerlendirme: kullanılamaz.** Ürün kapatılmış, aylık değer vermiyor.

**4C. NOAA NDBC PCBF1 = NOS CO-OPS 8729210 (Panama City Beach) su sıcaklığı**
- URL: https://www.ndbc.noaa.gov/station_history.php?station=pcbf1 — yıllık dosya kalıbı `https://www.ndbc.noaa.gov/data/historical/stdmet/pcbf1h{YYYY}.txt.gz`; aynı istasyon için CO-OPS JSON API (`api.tidesandcurrents.noaa.gov`, anahtarsız, `application` parametresiyle).
- Sahibi / otorite: veriyi NOAA NDBC dağıtıyor, istasyon NOAA National Ocean Service'in; ölçüm için resmî.
- Verdiği alanlar: 6 dakikalık deniz suyu sıcaklığı (°C), hava sıcaklığı, rüzgâr, basınç. İstasyon 30A merkezine ~29 km, doğu ucuna ~12 km.
- Anlam ve sınır: ham gözlem, normal değil. Yıllık dosyalar 2005–2008 ve 2013–2025 için var (2009–2012 eksik). NDBC'nin hazır iklim özeti eski ve kısa (2005–2008). Tek kıyı noktası.
- Güncellenme: gerçek zamanlı; kalite kontrollü yıllık dosya ertesi yıl (2025 dosyası Şubat 2026). Kullanım: ABD federal verisi, kısıt yok.
- Örnek istek: `pcbf1h2025.txt.gz` — 23:38 UTC, HTTP 200, 87.014 satır. Yalnız 2025 yılının aylık ortalamaları (°C, bizim hesabımız): 14,7 / 17,6 / 18,6 / 22,6 / 26,4 / 29,1 / 28,8 / 30,0 / 28,7 / 25,9 / 21,8 / 17,6. Bunlar tek yılın değerleri, normal değil.
- **Değerlendirme: sınırlı.** Resmî ve kararlı kimlikli ölçüm; hazır aylık normal yok, seride boşluk var. Aylık ortalama bizim hesaplamamızla "PCBF1, mevcut yılların ortalaması" diye etiketlenmeli.

**Alanın sonucu.** Hava sıcaklığı ve yağış için en iyi kaynak NCEI 1991–2020 normalleridir (kıyı referansı Destin, iç kesim karşılaştırması DeFuniak Springs). Hazır bir bağıl nem normali bulunamadı; tek resmî yol Eglin'in saatlik çiy noktası normallerinden aylık değeri bizim türetmemiz (ya da değerlendirilmeyen LCD ürünü). Deniz suyu için CWTG kapalı; en iyi yol PCBF1/8729210 ham verisinden çok yıllık aylık ortalama hesaplamak. 1991–2020 türünde bir deniz yüzeyi normali istenirse NOAA OISST sonraki aday olur (aday sınırı nedeniyle değerlendirilmedi).

## Alan 5 — Kasırga riski

**5A. NOAA NHC HURDAT2 — Atlantik best track, 1851–2025**
- URL: https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2025-092326.txt (dosyanın listelendiği sayfa: https://www.nhc.noaa.gov/data/#hurdat)
- Sahibi / otorite: NOAA National Hurricane Center; Atlantik için resmî kesinleşmiş iz kaydı.
- Verdiği alanlar: her fırtına için kimlik (AL + numara + yıl) ve ad; 6 saatlik iz noktaları (UTC zaman, durum TD/TS/HU/EX…, 0,1° hassasiyetle konum, en yüksek rüzgâr, en düşük basınç, karaya çıkış işareti). Aylık sıklık doğrudan yok; dosyadan hesaplanır.
- Anlam ve sınır: sezon sonrası kesinleşmiş izler; eski dönemlerde fırtınalar eksik sayılmış ve konum belirsizliği büyük. Yeniden analiz sürüyor (23 Eylül 2026 güncellemesi 1971–1975 sezonlarını değiştirdi). 2026 sezonu dosyada yok.
- Teknik yol: API yok; virgülle ayrılmış tek metin dosyası (~7 MB), anahtarsız. Dosya adı her sürümde değişiyor; güncel ad veri sayfasından okunmalı. Fırtına kimliği dosya sürümüyle birlikte saklanmalı.
- Güncellenme: yılda bir ve yeniden analiz güncellemeleri. Kullanım: ABD federal verisi, kısıt yok; robots.txt serbest.
- Örnek istek: dosya — 2026-10-06 23:39 UTC, HTTP 200, 7,07 MB; 1.988 sistem (AL011851 … AL132025 Melissa), 2025'te 13 sistem. Fizibilite kontrolünde 30A merkezine en yakın geçişler hesaplanabildi (ör. Michael 2018 ~72 km).
- **Değerlendirme: kullanılabilir.** Resmî, anahtarsız, kolay ayrıştırılıyor; 30A'ya özgü aylık sayılar belgelenmiş bir yöntemle bizim hesabımız olarak üretilmeli.

**5B. NOAA NCEI IBTrACS v04r01**
- URL: https://www.ncei.noaa.gov/products/international-best-track-archive — Sahibi: NOAA NCEI (WMO merkezlerinin izlerini birleştiriyor; Kuzey Atlantik için kaynağı NHC).
- Anlam ve sınır: Atlantik için HURDAT2'nin yeniden biçimlendirilmiş hali, üstüne ara değerlenmiş noktalar ve süren sezonun geçici izleri. Atlantik için yeni bilgi eklemiyor.
- Teknik yol: CSV/netCDF/shapefile; dosyalar NCEI'nin robots.txt ile yasakladığı `/data` yolunun altında, bu yüzden veri dosyasından örnek alınmadı. AOML ERDDAP aynası yalnız 2022–2025 aralığını içeriyor ve güncel değil.
- Güncellenme: haftada üç kez. Kullanım: açık erişim, atıf zorunlu.
- Örnek istek: kolon belgesi PDF'i — 23:40 UTC, HTTP 200.
- **Değerlendirme: sınırlı.** Atlantik için HURDAT2'nin kopyası ve resmî indirme yolu robots.txt'ye takılıyor.

**5C. NOAA NHC Tropical Cyclone Climatology**
- URL: https://www.nhc.noaa.gov/climo/ — Sahibi: NOAA NHC.
- Verdiği alanlar: havza geneli bilgiler (sezon 1 Haziran–30 Kasım; 1991–2020 ortalama sezonu 14 adlandırılmış fırtına, 7 kasırga, 3 büyük kasırga; etkinlik zirvesi 10 Eylül civarı), aylara göre oluşum haritaları ve kıyı için dönüş periyodu haritaları (resim).
- Anlam ve sınır: 30A'ya özgü aylık sayı yok; dönüş periyodu haritaları eski bir yöntem ve 2010'a kadarki veriyle hazırlanmış, yalnız resim.
- Teknik yol: HTML + resim; kimlik yok. Güncellenme: düzensiz, sayfada tarih yok.
- Örnek istek: sayfa — 23:43 UTC, HTTP 200.
- **Değerlendirme: sınırlı.** "Sezon ve zirve" cümleleri için atıf yapılabilir bağlam; yerel aylık risk için tek başına yetmez.

**"30A'nın X km yakınından geçen fırtına" istatistiği için önerilen yöntem (hesaplanmadı).** HURDAT2 dosyası sürüm adıyla saklanır; dönem açıkça seçilir (ör. 1991–2025); 30A batı ve doğu ucu arasındaki çizgi olarak alınır; birkaç yarıçap denenir (ör. 50 deniz mili ≈ 93 km, 100 km, 200 km); iz noktaları arasında ara değerleme yapılır (yalnız 6 saatlik noktalar yakın geçişleri kaçırır); fırtına türü daire içindeyken sahip olduğu duruma göre sayılır; her fırtına bir kez ve daireye ilk giriş ayına göre sayılır; sonuç "N yılda kaç fırtına" ve "en az bir fırtına görülen yıl / N" olarak verilir. Uyarılar: merkezin geçmesi etki demek değildir (rüzgâr alanı, yağış ve dalga çok daha geniş etkiler); eski dönemlerde eksik sayım var; bazı aylarda örneklem çok küçük kalır.

**Alanın sonucu.** Birincil kaynak HURDAT2'dir; 30A'ya özgü aylık sayılar bundan, yukarıdaki yöntemle bizim hesabımız olarak üretilmeli ve öyle etiketlenmelidir. Havza ölçeğindeki sezon ve zirve cümleleri için NHC iklim sayfası yeterli atıf kaynağıdır.

## Alan 6 — Kalabalık ve sezon

**6A. Walton County Tourism — TDT Collections (aylık turist geliştirme vergisi tahsilatları)**
- URL: https://www.waltoncountyfltourism.com/tdt-collections/
- Sahibi / otorite: Walton County Tourism Department (ilçe turizm dairesi); vergiyi Walton County Clerk of Courts tahsil ediyor.
- Verdiği alanlar: South Walton ve North Walton vergi bölgeleri için aylık konaklama vergisi tahsilatı (sayfada 2024, 2025, 2026 rapor başlıkları).
- Anlam ve sınır: kişi değil para; tutar doluluğu, fiyatı ve vergi oranını birlikte yansıtır (yaz fiyatları zirveyi büyük gösterir). "South Walton" vergi bölgesi körfezin güneyindeki ilçe kısmının tamamıdır (Miramar Beach ve Sandestin dahil), 30A değildir. Vergi oranı yıllar içinde değişti. 2025 yıllık raporuna göre Kasım–Aralık 2024 tahsilatının bir kısmı yeni portal geçişi nedeniyle 2025'e kaymış olabilir. "Ay"ın konaklama ayı mı tahsil ayı mı olduğu yazmıyor.
- Teknik yol: statik site; aylık veri sayfadaki akordeonun içinde tarayıcıda JavaScript ile yükleniyor; sunucunun gönderdiği HTML'de ve sayfa verisi JSON'unda yok. Veri uç noktası bulunamadı. Kararlı kimlik yok (doğal anahtar: ay + vergi bölgesi).
- Güncellenme: aylık bültenler. Kullanım: robots.txt engel değil; "© Walton County TDC"; rakamlar atıfla kullanılabilir. Clerk sitesinin robots.txt'si genel botlara tamamen kapalı.
- Örnek istek: sayfa — 2026-10-06 23:33 UTC, HTTP 200; vergi bölgeleri ve oranlar anlatılıyor, aylık rakam HTML'de yok.
- **Değerlendirme: sınırlı.** Konu için en iyi resmî aylık gösterge, ama makinece okunabilir yolu bulunamadı ve veri 30A'nın değil vergi bölgesinin parası.

**6B. Florida Department of Revenue — ilçe ve işletme türü bazında aylık vergiye tabi satışlar**
- URL: https://floridarevenue.com/dataportal/ (erişilemedi); karşılaştırma için EDR: https://edr.state.fl.us/Content/local-government/data/county-municipal/index.cfm
- Sahibi / otorite: Florida DOR; EDR (Yasama Meclisi'nin ekonomik araştırma ofisi) bu veriyi yeniden yayımlıyor.
- Anlam ve sınır: EDR'nin açıklamasına göre veri satış vergisi beyannamelerinden gelir, işlem ayına göre tarihlenir, yaklaşık 2 ay gecikmeyle yayımlanır ve sonra revize edilir; ilçe düzeyindedir. Walton turist vergisini kendisi topladığı için DOR'un turist vergisi verisi Walton'ı kapsamıyor. Erişilebilen EDR "transient rentals" dosyası aylık değil, gelecek mali yıl için yıllık tahmin.
- Teknik yol: floridarevenue.com alan adı bu bilgisayardan keşif boyunca çözülemedi (DNS); biçim doğrulanamadı.
- Örnek istek: robots.txt — DNS hatası; EDR tahmin dosyası (XLSX) — 23:39 UTC, HTTP 200.
- **Değerlendirme: kullanılamaz** (bu keşifte). DOR'a erişilemedi; erişilebilen türev aylık değil.

**6C. Walton County Tourism — Visitor Tracking & Economic Impact raporları (hazırlayan: Downs & St. Germain Research)**
- URL: https://www.waltoncountyfltourism.com/research-reports/
- Sahibi / otorite: yayımcı Walton County Tourism; üretici üçüncü taraf araştırma şirketi (kaynakları: ilçe, konaklama işletmeleri, Key Data, STR, anketler).
- Verdiği alanlar: yıllık ve mevsimlik ziyaretçi, oda-gece, harcama, vergi, doluluk, ortalama günlük fiyat (ADR) ve ziyaretçi profili. 2025 yıllık raporu: 4.586.000 ziyaretçi, 3.497.200 oda-gece, 61.444.321 $ turist vergisi, birleşik doluluk %48,3, ADR 354,10 $.
- Anlam ve sınır: ilçe düzeyi (30A değil); ziyaretçi sayısı model tahmini; aylık değil; rapor 2025 fiyat yöntemindeki değişikliğin ADR karşılaştırmasını etkileyebileceğini söylüyor; raporda bazı iç tutarsızlıklar var.
- Teknik yol: rapor listesi sayfa verisi JSON'unda yapılandırılmış (65 kayıt, 2017–2026; CMS kimliği + PDF bağlantısı); içerik grafik ağırlıklı PDF. Bağlantıların 41'i Visit South Walton'ın robots.txt ile kapalı `/userfiles/` yolunda.
- Güncellenme: yılda dört mevsim raporu ve bir yıllık rapor.
- Örnek istek: rapor listesi JSON'u — 23:51 UTC, HTTP 200, 65 kayıt; 2025 yıllık rapor PDF'i — HTTP 200, 9,5 MB.
- **Değerlendirme: sınırlı.** Yetkili ve uzun geçmişli; ama ilçe düzeyi, model tahmini ve aylık değil.

**Alanın sonucu.** En iyi resmî aylık gösterge Walton County Tourism'in aylık turist vergisi tahsilatlarıdır (South Walton vergi bölgesi, para cinsinden); bağlamadan önce verinin yüklendiği uç nokta için kısa bir ek keşif ya da tarayıcı otomasyonu kararı gerekir. Mevsim ve yıl bağlamı için Downs & St. Germain raporları atıfla kullanılabilir. 30A düzeyinde resmî bir kalabalık göstergesi bulunamadı; veriler "South Walton" ya da "Walton County" diye etiketlenmelidir.

## Alan 7 — Konaklama ve fiyat (Book>Direct)

7 Ekim 2026 yönetici kararına göre konaklama, tarihli Book>Direct aramalarının etiketli anlık görüntüleri olarak modellenecek. Bu alanda envanter araştırması yapılmadı; yalnız fiyat ve ilgili alanların anlamı netleştirildi.

**Yöntem.** Book>Direct ön yüzünün paketi (`bookdirect.min.js`, sürüm yolu `/20261006094543/`) ve herkese açık çeviri dosyası (`locales/en.json`) okundu. Paket, ön yüzün kullandığı herkese açık istemci anahtarını içerdiği için diske yazılmadı; anahtar yalnız bellekte tutuldu, hiçbir dosyaya ve çıktıya yazılmadı (kaydedilen bütün dosyalar anahtar için tarandı). `admin.bookdirect.net` üzerinde 16 API isteği yapıldı (sıralı, 1,5 sn arayla, repo adresli User-Agent). İki hostta da robots.txt yok (404).

**Bulgular**

| Konu | Kaynağın söylediği / örnekte görülen |
|---|---|
| `average_rate` neyin fiyatı | Arayüz etiketi "Average Rate/Night": gecelik ortalama. Kaynağın genel notu: fiyatlar müsait en düşük günlük fiyata dayanır, minimum konaklamalı kayıtlarda ortalama gösterilir, fiyat garanti değildir, N/A = mevcut değil. |
| Para birimi | Kayıttaki `currency` nesnesi USD, CAD, EUR ve MXN değerlerini birlikte veriyor; `average_rate` seçili para birimindeki değerdir (varsayılan USD; arayüz notu "Prices in US Dollars"). Örnek: 250.00 USD = 355.27 CAD. Diğer para birimleri kaynak tarafından çevrilmiş görünüyor. |
| Vergi ve ücretler | Pakette ve çeviri dosyasında vergi/ücret ifadesi hiç yok. Fiyatın vergi ve ücretleri içerip içermediği kaynakta **belirtilmiyor**. |
| Kaç gece için | Alan adı ve etiket gecelik ortalama diyor. 1 gecelik aramada (2–3 Kasım 2026) "Dune Nothin" (526140) için 250.00 USD ve `los`=4 döndü: fiyat, istenen gece sayısı minimum konaklamanın altında olsa da veriliyor; arayüz bu durumda minimum konaklama uyarısı gösteriyor. |
| Boş fiyat | `average_rate` boşsa arayüz, fiyat ve müsaitlik için mülkle doğrudan iletişime geçilmesini öneren bir mesaj gösteriyor. Bu "müsait değil" anlamına gelmez; kaynak fiyat vermiyor demektir. |
| Fiyat doluluğu | 17–24 Ekim 2026 (7 gece) aramasında Dune Allen'ın 112 kaydının hiçbirinde, Seaside'ın ilk 50 kaydında (toplam 111) ve Rosemary Beach'in ilk 50 kaydında (toplam 160) `average_rate` dolu değildi. Dune Allen'da 73 kayıt `live_rates_enabled=true`; bunların 5'i için `live_rates.json` da boş döndü. |
| `rates.json` | "Rates By Date" takvimi: tek bir kayıt için günlük fiyat. Ön yüz bugünden bir yıl sonrasına kadar `per_page=365` ile çağırıyor. Her öğe: `date`, `price`, `data`, `los`, `currency`. Örnek: 526140 için 92 gün (23 Ekim 2026 – 30 Ocak 2027), hepsi 250.00 USD, `los`=4. Takvimi kapalı kayıtta (`hide_rate_calendar=1`, 540249) boş liste. |
| `live_rates.json` | Canlı fiyat entegrasyonu olan kayıtlar için ön yüzün tekrar tekrar sorduğu servis. Parametreler: `checkin`, `checkout`, `lodging_ids[]`, `current_page`, `attempt`. Yanıt: `lodging_id`, `liveness`, `average_rate`, `los`, `currency`. Koda göre ön yüz `liveness`=0'ı güncel canlı fiyat, 1'i bekleyen fiyat, boş değeri canlı fiyat yok sayıyor (koddan çıkarım; belgelenmiş değil). |
| Misafir sayısı | Konaklama aramasında yetişkin/çocuk/misafir parametresi yok: `adults=6` gönderilince sonuç değişmedi (112 kayıt, aynı bayt). Kapasite filtresi var: `min_sleeps` ve `max_sleeps` birlikte gönderilince çalışıyor (8–40 → 72 kayıt); yalnız `min_sleeps=8` gönderilince 0 kayıt döndü. `sleeps` mülkün kapasitesidir, misafir sayısına göre fiyat değildir. Ön yüz bu parametreleri ana arama sayfasında siliyor, yalnız özel sekmelerde kullanıyor. |
| Minimum konaklama | `los`: seçilen tarihlerde kaydın minimum gece sayısı (arayüz metni: "minimum stay (N nights)"). `rates.json` her gün için ayrı `los` veriyor. `min_stays` bütün örneklerde boş; anlamı belirsiz. |
| Konum filtresi | `show.json` içinde 19 konum: 13 kanonik mahallenin hepsi, ayrıca ayrı bir "Seagrove Beach", Defuniak Springs, Freeport, Miramar Beach, Sandestin, Seascape. "Seacrest" konumunun koordinatı 26.57, -80.07 (Florida'nın doğu kıyısı); kaynağın yapılandırmasındaki koordinatlar güvenilir değil. |

**Kullanım notu.** Bu uçlar belgelenmiş, resmî bir API değil; Visit South Walton'ın Book>Direct ön yüzünün kullandığı uçlar. İstek için ön yüz paketindeki herkese açık istemci anahtarı gerekiyor (her çekimde paketten okunmalı, koda veya dosyaya yazılmamalı). Book>Direct'in kullanım şartları bu turda incelenmedi. Ön yüz sürüm yolu 30 Eylül ile 6 Ekim arasında değişti; uçlar haber verilmeden değişebilir.

**Aday değerlendirmeleri**

**7A. Book>Direct `lodgings.json` ve `lodgings/{id}.json` (tarihli konaklama araması ve kayıt detayı)**
- URL: https://admin.bookdirect.net/hs4/api/v1/clones/visitsouthwalton.bookdirect.net/lodgings.json (detay `/lodgings/{id}.json`, yapılandırma `/show.json`)
- Sahibi / otorite: Book>Direct platformu; Visit South Walton'ın resmî "Stay" ön yüzü bu uçları kullanıyor. Kayıt içeriği mülklerden ve rezervasyon sistemlerinden geliyor (`res_engine`: TrackHs, VRBO API, Escapia vb.).
- Verdiği alanlar: kayıt kimliği, ad, kategori, konum filtresi (`location_id`), adres, koordinat, yatak odası, banyo, kapasite (`sleeps`), olanaklar, rezervasyon sistemi, `average_rate`, `currency`, `los`, `liveness`, `live_rates_enabled`, `min_stays`; toplam kayıt ve sayfa sayısı.
- Anlam ve sınır: tarihli arama sonucu; tam envanter değil. Fiyat alanları örneklerde boştu.
- Teknik yol: JSON, belgelenmemiş; ön yüzdeki herkese açık istemci anahtarı gerekiyor. Kararlı kimlik `lodging.id`.
- Güncellenme: canlı; kayıtlarda güncelleme tarihi yok.
- Kullanım: robots.txt yok; kullanım şartları incelenmedi.
- Örnek istek: Dune Allen, 17–24 Ekim 2026, 50'lik 3 sayfa — 2026-10-06 23:38 UTC, HTTP 200; 112 kayıt, hiçbirinde `average_rate` yok.
- **Değerlendirme: sınırlı.** Etiketli anlık görüntü modeline uygun; fiyat doluluğu örneklerde sıfır.

**7B. Book>Direct `lodgings/{id}/rates.json` ("Rates By Date" takvimi)**
- Verdiği alanlar: günlük `date`, `price`, `los`, `currency`.
- Anlam ve sınır: tek kayıt için fiyat takvimi; yalnız takvimi açık ve fiyat yükleyen kayıtlarda dolu. Kaynağa göre en düşük müsait günlük fiyat; garanti değil; vergi/ücret belirtilmemiş.
- Örnek istek: 526140 — 23:39 UTC, HTTP 200, 92 günlük takvim; 540249 — HTTP 200, boş liste.
- **Değerlendirme: sınırlı.** Fiyat yükleyen az sayıdaki kayıt için günlük fiyat verir; kapsamı bilinmiyor.

**7C. Book>Direct `lodgings/live_rates.json` (canlı fiyat)**
- Verdiği alanlar: `lodging_id`, `liveness`, `average_rate`, `los`, `currency`.
- Anlam ve sınır: yalnız canlı fiyat entegrasyonu olan kayıtlar için; ön yüz sonucu birkaç kez yeniden soruyor.
- Örnek istek: Dune Allen'dan 5 kayıt — 23:38 UTC, HTTP 200; beşi de boş.
- **Değerlendirme: sınırlı.** Örnekte fiyat dönmedi.

**Önerilen örnek tarih seti.** Kiralık evlerde yaygın olan Cumartesi–Cumartesi 7 gece (bu yaygınlık bir varsayımdır, kaynakta doğrulanmadı):

| Sezon | Giriş | Çıkış |
|---|---|---|
| Sonbahar | 2026-10-17 | 2026-10-24 (bu turda örneklendi) |
| Kış | 2027-01-16 | 2027-01-23 |
| Bahar tatili | 2027-03-13 | 2027-03-20 |
| Yaz zirvesi | 2027-07-10 | 2027-07-17 |

Her sezon için ayrıca 1 gecelik bir sorgu minimum konaklama (`los`) bilgisini yakalar. Her kayda arama tarihi (çekim günü), giriş/çıkış, kapasite filtresi (ör. `min_sleeps=4/8`, `max_sleeps=40`) ve mahalle filtresi yazılmalı; aynı set düzenli aralıklarla tekrar çekilirse "kaç gün önceden" etkisi de görülür.

**Alanın sonucu.** Book>Direct, tarihli aramada hangi kayıtların göründüğünü kararlı kimlik (`lodging.id`), mahalle filtresi, kategori, yatak odası ve kapasite ile veriyor; bu, kararlaştırılan "etiketli anlık görüntü" modeline uyuyor. Fiyat tarafı ise zayıf: alanların anlamı kaynağın kendi arayüz metinleriyle netleşti (gecelik ortalama, USD, garanti değil, vergi/ücret belirtilmemiş), fakat örnek aramalarda liste fiyatı hiç dolu değildi. "Mahalleye göre gecelik fiyat aralığı" bu kaynaktan bugünkü örneklerle çıkarılamıyor; fiyat sorusu için ek bir karar gerekir.

## Alan 8 — Ulaşım

**8A. FAA ADDS "Airports" (US_Airport) katmanı**
- URL: https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/arcgis/rest/services/US_Airport/FeatureServer/0
- Sahibi / otorite: FAA Aeronautical Information Services; havalimanı konumu için birincil resmî kaynak.
- Verdiği alanlar: havalimanı kodu, adı, koordinat, rakım, hizmet verdiği şehir, işletme durumu.
- Anlam ve sınır: koordinat havalimanının referans noktasıdır (terminal değil). FAA mesafe vermiyor; mesafe bizim hesabımız. Sürüş mesafesi için bir rota motoru gerekir (resmî değil; hesaplanmadı).
- Teknik yol: ArcGIS REST (JSON); kimlik IDENT (ECP, VPS, PNS) + GLOBAL_ID. Güncellenme: 8 haftalık döngü; veri son düzenleme 2026-09-03. Kullanım: ABD federal verisi.
- Örnek istek: ECP, VPS, PNS sorgusu — 2026-10-06 23:42 UTC, HTTP 200, 3 kayıt.
- **Değerlendirme: kullanılabilir.** Mesafeler yeniden üretilebilir; videoda "kuş uçuşu" etiketi şart.

Kuş uçuşu mesafeler (haversine; 30A noktaları programın hava örnek noktaları: batı = Stallworth Preserve, orta = Holly-24, doğu = Lupine-1; mahalle merkezi değil):

| Havalimanı | Batı | Orta | Doğu |
|---|---:|---:|---:|
| ECP — Northwest Florida Beaches Intl | 27,9 mil (44,9 km) | 20,1 mil (32,3 km) | 13,4 mil (21,6 km) |
| VPS — Destin–Fort Walton Beach (FAA kaydında Eglin AFB ile ortak) | 17,9 mil (28,8 km) | 26,3 mil (42,3 km) | 34,8 mil (56,0 km) |
| PNS — Pensacola Intl | 55,6 mil (89,5 km) | 64,0 mil (103,0 km) | 72,3 mil (116,4 km) |

**8B. Mevzuat: Florida Statutes §316.212 (golf arabası), §316.2122 (düşük hızlı araç, LSV) ve Walton County Ordinance 2009-02 (çok amaçlı yollar)**
- URL: https://www.leg.state.fl.us/statutes/ (316.212 ve 316.2122 bölümleri), https://www.mywaltonfl.gov/DocumentCenter/View/1377
- Sahibi / otorite: Florida Legislature; Walton County BCC.
- Verdiği alanlar: golf arabası kamu yollarında yasak, yerel yönetimin belirleyip tabelaladığı yollar istisna, gün doğumu–batımı arası; LSV yalnız hız limiti 35 mph ve altındaki yollarda, tescil/sigorta/ehliyetle; ilçenin 2009 yönetmeliğine göre çok amaçlı yollarda (Timpoochee gibi) golf arabası yalnız bakım ve görev istisnalarıyla.
- Anlam ve sınır: Walton County'nin 30A dahil herhangi bir yolu golf arabasına açıp açmadığı ve 30A'nın kesim bazında hız limitleri resmî bir kaynakta doğrulanamadı; yönetmeliğin 2009 sonrası değişiklikleri kontrol edilmedi.
- Teknik yol: HTML ve PDF; kimlik bölüm numarası + yıl sürümü / ordinance numarası; veri toplayıcıdan çok elle alıntıya uygun.
- Örnek istek: 316.212 ve 316.2122 sayfaları — 23:45 UTC, HTTP 200. İlçe PDF'i bu bilgisayardan iki kez HTTP 522 verdi; aynı belge başka bir okuma aracıyla alındı.
- **Değerlendirme: sınırlı.** Mevzuat güvenilir ve alıntılanabilir; 30A'ya özgü ilçe kararları doğrulanamadı.

**8C. Visit South Walton — ulaşım dizini, Timpoochee Trail sayfası ve "Guide to Beach Parking and Transportation" rehberi**
- URL: https://www.visitsouthwalton.com/listings/transportation/, https://www.visitsouthwalton.com/listing/timpoochee-trail/, https://www.visitsouthwalton.com/blog/guide-beach-parking-transportation/
- Sahibi / otorite: Walton County Tourism Department (Visit South Walton).
- Verdiği alanlar: ulaşım dizininde 6 kayıt (golf arabası/LSV kiralama ve servis şirketleri); Timpoochee Trail: 30A boyunca 12 mahalleden geçen, yaklaşık 19 millik asfalt çok amaçlı yol (rehberde ~18,5 mil); park rehberi: mahalle başlıkları altında bölgesel plaj erişimleri, adresleri ve araç kapasiteleri; ücretli "Park and Ride" otoparkları (saati 5 $, günü 15 $) ve buralardan plaja ücretsiz servis; Rosemary Beach ve Alys Beach için "No Public Beach Access".
- Anlam ve sınır: dizin tam liste değil (sayfalama yok, 6 kart). Rehber 2023-05-04 tarihli; bazı bölgesel erişimlerde ücretsiz park olduğunu söylüyor ama hangileri olduğunu tek tek yazmıyor (yazılmayan bir yer ücretsiz sayılmamalı). Servis saatleri kaynaklar arasında çelişkili. Timpoochee uzunluğu VSW'nin kendi sayfalarında 19 ile ~18,5 mil arasında değişiyor. "Araba gerekli mi" sorusuna doğrudan resmî bir cevap yok.
- Teknik yol: HTML; kimlik `/listing/<slug>/`. Güncellenme: sayfalarda tarih yok; rehberin `dateModified` alanı otomatik üretiliyor.
- Kullanım: robots.txt bu yolları engellemiyor; içerik atıfla kullanılmalı, metin kopyalanmamalı.
- Örnek istek: dizin, Timpoochee sayfası ve rehber — 23:46–23:47 UTC, HTTP 200.
- **Değerlendirme: sınırlı.** Alıntı için iyi resmî destinasyon bilgisi; tarihsiz/eski ve kısmen çelişkili.

**Alanın sonucu.** Havalimanları için FAA kullanılabilir (kuş uçuşu: 30A'nın doğu ucuna en yakın ECP ~13 mil, batı ucuna en yakın VPS ~18 mil). Golf arabası ve LSV için eyalet kanunu net; 30A'ya özgü ilçe kararları doğrulanamadı. Timpoochee ve otopark için en iyi erişilebilir resmî kaynak Visit South Walton. "Araba gerekli mi" sorusuna resmî ve doğrudan bir cevap bulunamadı.

## Alan 9 — Yapılacaklar

**9A. Florida State Parks — park "Hours & Fees" sayfaları (Grayton Beach, Topsail Hill Preserve, Deer Lake)**
- URL: https://www.floridastateparks.org/parks-and-trails/grayton-beach-state-park/hours-fees (Topsail Hill ve Deer Lake için aynı yapı)
- Sahibi / otorite: Florida DEP, Division of Recreation and Parks; park ücret ve saatleri için birincil otorite.
- Anlam ve sınır: içerik bu turda okunamadı; ücret ve saat değerleri doğrulanmadığı için verilmiyor.
- Teknik yol: HTML; robots.txt izin veriyor, ancak site Cloudflare bot doğrulamasının arkasında (otomatik istemciler 403 alıyor). Kimlik park yolu.
- Örnek istek: üç sayfa — 23:41 UTC, üçü de HTTP 403 (doğrulama sayfası).
- **Değerlendirme: kullanılamaz** (otomatik bağlantı için). Resmî ve yetkili, ama bot korumasına takılıyor; yalnız elle ve erişim tarihiyle atıf yapılabilir.

**9B. Florida Forest Service — Point Washington State Forest**
- URL: https://www.fdacs.gov/forest-wildfire/our-forests/state-forests/point-washington-state-forest
- Sahibi / otorite: Florida Department of Agriculture and Consumer Services, Florida Forest Service; ormanın yöneticisi.
- Verdiği alanlar (tek bir okumaya göre, ham kayıt yok): gün içi kullanım gün doğumundan gün batımına; günlük geçiş 2 $, yıllık 45 $; Eastern Lake Trail halka parkurları; rezervasyonlu ilkel kamp yerleri.
- Anlam ve sınır: sayfada tarih yok; ücretin kişi mi araç başına mı olduğu netleşmedi.
- Kullanım: fdacs.gov robots.txt genel botlara tamamen kapalı (`Disallow: /`); bu yüzden sayfaya örnek istek yapılmadı, yalnız robots.txt alındı.
- **Değerlendirme: kullanılamaz** (otomatik bağlantı için). Yetkili, ama robots.txt programı dışlıyor; yalnız elle ve tarihli atıf.

**9C. Visit South Walton — Events ve "Coastal Dune Lakes" yazısı**
- URL: https://www.visitsouthwalton.com/events/ (aralık araması: `/events/?startDate=AA/GG/YYYY&endDate=AA/GG/YYYY&page=N`, isteğe bağlı `neighborhood=` ve `category=`), https://www.visitsouthwalton.com/blog/rare-diverse-beautiful-coastal-dune-lakes/
- Sahibi / otorite: Walton County Tourism Department; etkinliklerin kendisi için otorite değil, düzenleyicilerin ve önerilerin seçkisini yayımlıyor.
- Verdiği alanlar: etkinlik adı, tarihleri, saat metni, tür (tekrarlayan/çok günlü), mahalle, kategori, açıklama, giriş ücreti, adres, iletişim. Göl yazısı Walton'da 15 adlandırılmış kıyı kumul gölü olduğunu söylüyor, isimlerini listelemiyor.
- Anlam ve sınır: takvim tam liste değil ("Suggest an Event" ile besleniyor); South Walton genelini kapsıyor; saatler serbest metin, saat dilimi yok. Sayfadaki Event JSON-LD hatalı (ad ve konum boş) ve kullanılmamalı. iCal, RSS veya JSON ucu yok.
- Teknik yol: sunucu tarafında üretilen HTML; kimlik kanonik `/events/<slug>/` + oturum tarihi; sayfa başına yaklaşık 9 kart.
- Güncellenme: sürekli değişiyor; güncelleme tarihi yok.
- Kullanım: robots.txt `/events/` ve `/blog/` yollarını engellemiyor; kullanım şartları kopyalamayı kısıtlıyor.
- Örnek istek: 7–31 Ekim 2026 aralık araması — 23:43 UTC, HTTP 200, 9 kart ve 5+ sayfa; bir detay sayfası (Rosemary Beach çiftçi pazarı) — HTTP 200.
- **Değerlendirme: etkinlikler kullanılabilir** ("tam liste değil", saat dilimi varsayımı ve 30A filtresi açıkça işaretlenerek); **göl yazısı sınırlı** (sayı var, liste yok).

**9D. Book>Direct `venues.json` (aktiviteler)**
- URL: https://admin.bookdirect.net/hs4/api/v1/clones/visitsouthwalton.bookdirect.net/venues.json — Sahibi: Book>Direct (Visit South Walton ön yüzü).
- Örnek istek: 17–24 Ekim 2026 tarihleriyle — 2026-10-06 23:36 UTC, HTTP 200; 0 kayıt. Ön yüz yapılandırmasında etkinlik/aktivite gösterimi kapalı (`show_events=0`).
- **Değerlendirme: kullanılamaz.** Bu ön yüz için aktivite verisi yok.

**Alanın sonucu.** Etkinlik takvimi için bağlanabilir tek kaynak Visit South Walton Events'tir (seçki niteliğinde, South Walton geneli, saat dilimi yok). Eyalet parkları ve Point Washington için yetkili kaynaklar otomatik erişime kapalı (bot doğrulaması / robots.txt); ücret ve saatler elle, erişim tarihiyle kaydedilip her yıl yeniden kontrol edilmeli. Kıyı kumul göllerinin resmî isim listesi bulunamadı.

## Alan 10 — Günlük ihtiyaç

**10A. OpenStreetMap — Overpass API**
- URL: https://overpass-api.de/api/interpreter
- Sahibi / otorite: OpenStreetMap katkıcıları; resmî değil.
- Verdiği alanlar: süpermarket, market ve eczane konumları; doluysa ad, marka, adres, açılış saati, web sitesi; öğe kimliği, sürümü ve son düzenleme zamanı.
- Anlam ve sınır: veri haritacıların girdiği kadar, tamlık bilinmiyor. Örnek kutu 30A'dan geniş: 27 öğenin 8'i 30A'nın batısında (Miramar/Sandestin tarafı), 4'ü 30A'nın doğu ucunun ötesinde, 15'i 30A boylamları içinde. Etiket kalitesi değişken; süpermarket içi eczaneler çoğu zaman ayrı işaretli değil; bazı öğeler yıllardır düzenlenmemiş. Mahalle alanı yok.
- Teknik yol: Overpass QL ile tek GET; kimlik OSM tipi + id + sürüm. Güncellenme: sürekli.
- Kullanım: ODbL; "© OpenStreetMap contributors" atfı zorunlu; kamuya açılan türetilmiş bir veritabanı (ör. mahalle–market listesi) ODbL ile paylaşılmalı. Overpass robots.txt `/api/` yolunu botlara kapatıyor; kalıcı kullanım için bölgesel extract ya da kendi sunucu düşünülmeli.
- Örnek istek: tek sorgu — 2026-10-06 23:48 UTC, HTTP 200; 27 öğe (12 süpermarket, 10 market, 5 eczane).
- **Değerlendirme: sınırlı.** Teknik olarak hazır ve kimlikli; tamlık ve kalite bilinmiyor, ODbL yükümlülüğü var.

**10B. Overture Maps — Places**
- URL: https://docs.overturemaps.org/guides/places/ (STAC kataloğu: https://stac.overturemaps.org/catalog.json)
- Sahibi / otorite: Overture Maps Foundation; resmî değil, birden çok sağlayıcının verisini birleştiriyor.
- Verdiği alanlar: işletme noktaları (GERS kimliği, ad, kategori, güven puanı, adres, web sitesi, marka, kaynak).
- Anlam ve sınır: güven puanı varlık olasılığıdır; 30A için kayıt çekilmedi, yerel kalite bilinmiyor; mahalle alanı yok.
- Teknik yol: GeoParquet dosyaları (S3/Azure); okumak için DuckDB/pyarrow gibi ek araç gerekir (projede yok). Güncellenme: aylık sürüm (son: 2026-09-23.1).
- Kullanım: kaynağa göre CDLA-Permissive-2.0 / Apache-2.0 / CC0; paylaşım şartı yok.
- Örnek istek: STAC kataloğu ve Places koleksiyonu — 23:49 UTC, HTTP 200.
- **Değerlendirme: sınırlı.** Lisans elverişli; ek araç gerekiyor ve yerel kalite görülmedi.

**Alanın sonucu.** Market ve eczane için resmî bir envanter bulunamadı. OSM hemen çalışıyor ama tamlığı bilinmiyor ve ODbL getiriyor; Overture lisans açısından daha esnek ama ek araç istiyor. Hiçbiri mahalle bilgisi vermiyor. Program, plaj erişimi koordinatlarından "en yakın market/eczane mesafesi" gibi yeniden üretilebilir bir ölçü hesaplayabilir; hiçbir yerde "tam liste" denmemeli.

## Önerilen bağlama sırası (karar yöneticinindir)

Sıralama ölçütü `docs/KONSEPT.md`'deki veri ilkesi: önce birçok videoda tekrar kullanılacak ve tatil kararını değiştiren, resmî ve teknik olarak kolay veriler; belirsiz, kapsamı zayıf veya lisans riski olanlar sonra.

1. **Mahalle profili (Alan 1).** İlk videonun "30A'nın hangi parçası bana uygun" sorusunun omurgası ve plaj, restoran, etkinlik verilerinin bağlanacağı anahtar. Tek istekle gelen gömülü JSON, kararlı kimlik ve programın 13 mahallesiyle birebir örtüşme var. 30A'ya özeldir; destinasyon profiline veya 30A connector'ına aittir.
2. **İklim normalleri (Alan 4) ve kasırga geçmişi (Alan 5).** "Ne zaman gitmeli" sorusunun resmî, anahtarsız ve durağan kaynakları; bakım yükü düşük. İstasyon ve koridor geometrisi destinasyon yapılandırmasından gelirse generic çekirdekte durabilir ve başka destinasyonlarda da kullanılır. Deniz suyu sıcaklığı PCBF1 ham verisinden çok yıllık ortalama olarak eklenebilir.
3. **Plaj erişimi → mahalle kararı (Alan 2) ve kural tablosu (Alan 3).** Rehberden gelen 9 eşleme hazır; kalan 44 erişim için yöntem seçilmeli. Kurallar bir veri toplayıcı değil, Ordinance 2025-22'den bölüm numaralı, tarihli ve elle doğrulanmış bir referans tablo olarak tutulmalı.
4. **Konaklama pilotu (Alan 7).** Bağlayıcı yazmadan önce önerilen dört sezonluk tarih setiyle 13 mahalle için tek seferlik etiketli bir anlık görüntü alınıp fiyat doluluğu ölçülmeli. Doluluk bu turdaki gibi sıfıra yakın kalırsa "yaklaşık ne harcarım" sorusu için ayrı bir kaynak kararı gerekir.
5. **Etkinlikler (Alan 9) ve sezon göstergesi (Alan 6).** Visit South Walton Events, restoran bağlayıcısına benzer bir HTML yolu. Aylık turist vergisi için önce verinin yüklendiği uç noktayı bulan kısa bir keşif gerekir; yıllık ve mevsimlik raporlar atıfla elle kullanılabilir.
6. **Ulaşım (Alan 8) ve günlük ihtiyaç (Alan 10).** Havalimanı mesafeleri tek seferlik bir referans; otopark ve golf arabası bilgileri elle doğrulanmış metin. OpenStreetMap tabanlı market/eczane ölçüsü ODbL kararından sonra.
