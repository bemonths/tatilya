# HEDEF-03 — Rapor: eksik yedi kiralama şirketi, "Seçili şirketleri yeniden oku", veri paketinin tazelenmesi

Dal `hedef-03` (main `6a89742`'den), uygulama **0.29.0**, şema **26**, eklenti **0.22.0**.

## Kısa özet

- **Yedi şirketin yedisi okundu**, fiyatlar yeni kiralama sürümünde (`8bc68fea`). Önceki sürüm `7cba8d4c`'ydi.
  - Şirkete bağlanan ilan: 953 → 1.281.
  - En az bir haftası fiyatlı ilan: 889 → 1.213.
  - Şirketin kendi listesinden okunan ev: 97 → 171 (fiyatlı 92 → 165).
- **Rosemary Beach:** 20 → 102 fiyatlı ilan.
- **Alys Beach:** topluluğun resmî kiralama programının 73 evinde fiyat var. 7 gecenin vergi ve ücretler dahil toplamının ortancası Ocak'ta
  ~9.921 $, Temmuz'da ~17.254 $.
- **Kök nedenler:**
  - Siteler artık doğrudan bağlantıya ve proxy'ye Cloudflare engeli veriyor; yalnız eklentiyle okunabiliyorlar.
  - Track'in fiyat sorusu izinli listede yoktu.
  - Rosemary Beach Track değil, Streamline; alanlarını adreste gönderiyor.
  - Alys Beach'in bağlantılarını eklentinin `fetch`'i alamıyordu.
  - Vacasa hatayı küçük harfle yazıyor.
  - RealJoy'da Cloudflare her 30 dakikada yeniden doğrulama istiyor.
  - Hepsi düzeltildi; ayrıntı bölüm 1'de.
- **Eklenti artık birkaç şirketi aynı anda okuyor;** 12+ saatlik okuma ~3,5 saate indi.
- **"Seçili şirketleri yeniden oku"** programda; seçilmeyen şirketler son sürümden olduğu gibi taşınır, her şirket satırında kendi sorgu
  günü görünür.
- **Yol ağı** 27 Kasım'ın günlük ihtiyaç ve plaj sürümleriyle yeniden ölçüldü.
- **Videonun 2 · Veri paketi** yeni fiyatlarla yeniden kuruldu: 840 kanıt, 1.951 sayı, 13 eksik (önceden 27). 3 · Plan "hazır".
  - Tahmin: plan ~272 bin, yazım iki tonla ~789 bin; toplam ~1,1 milyon token.
- **Yol üstünde bulunup düzeltilen iki hata:**
  - Track'te "Subtotal" satırı ücret sayılıyordu.
  - Veriler yeniden çekilince video paketinden fiyat bloğu düşüyordu.

## 1. Şirketlerin kök nedenleri ve düzeltmeleri

Kaynak: 26–27 Kasım gecesinin ham kopyası (`data/raw/b8055d2a…/manifest.json`, salt okunur), programın günlüğü (`data/gunluk/uygulama.log`),
gecenin şirket ve fiyat satırları (gerçek veritabanının kopyası) ve site başına tek doğrudan istek (`work/hedef3/oku.py`; 6 istek).

**Hepsinde ortak.** 30aescapes.com, oceanreefresorts.com, panhandlegetaways.com, rosemarybeach.com, alysbeach.com ve vacation.alysbeach.com
artık doğrudan isteğe de proxy'ye de Cloudflare engeli veriyor (403; "Just a moment…" ya da Track'in kendi "Quick security check"
sayfası). Ekim'de doğrudan okunuyorlardı. Gece bu yüzden eklentiye geçtiler; bu doğru davranıştı, sorun eklentideki adımlardaydı.

| Şirket | Kök neden | Düzeltme |
|---|---|---|
| 30A Escapes, Ocean Reef Resorts, Panhandle Getaways (Track) | Fiyat sorusu `POST /ajax/quote` eklentinin izinli sorgu listesinde yoktu → "Sorgu gönderilmedi" ×5 → şirket durdu. | Göç v26 üç sitenin sorusunu listeye ekledi; alanlar her sitenin kendi tarih formundan (aşağıda). Okuyucu formu sayfadaki sırayla okur. |
| Rosemary Beach® | Track **değil**, Streamline (WordPress). Sayfanın betiği fiyatı `POST /wp-admin/admin-ajax.php` ile, alanları **adreste** göndererek soruyor (gövde boş). Eklenti adreste alan taşıyan sorguyu hiç göndermiyordu. | İzinli kayda "alanların yeri" (`adres`), içerik türü ve değer deseni eklendi (iki tarafta aynı kural); okuyucu JSON'u sayfanın betiği gibi boşluksuz yazar. |
| Alys Beach Vacation Rentals | Book>Direct'in 7 bağlantısı genel sayfaya gidiyor (`http://www.alysbeach.com`, `alysbeach.com/vacation-properties/` → `vacation.alysbeach.com`). Eklenti bunları sekmenin `fetch`'iyle istiyordu; tarayıcı http adresini (karışık içerik) ve başka alt alan adına yönlenmeyi kesti → "bağlanılamadı" ×5 → şirket kendi listesine (Ekim'de 73 ev) hiç gelmeden durdu. Kullanıcı izni ya da doğrulama sorunu değildi. | `fetch` ile alınamayan sayfa isteği (JSON değil, alan göndermeyen GET) sekmede açılarak okunur (ziyaretçinin tıklamasıyla aynı gezinme). |
| Vacasa | Site hata cevabını küçük harfle veriyor: `{"error": [{"message": "min-stay-not-met"}]}`. Okuyucu yalnız `Error` arıyordu; "en az kalış" cevabı "kira veya toplam yok" hatası sayıldı → 5 hata → durdu. | İki yazım da kural cevabı (`restricted`; `booked` → `unavailable`). Sitenin göstermediği fiyat uydurulmaz. |
| RealJoy | Eklentide 30 dakika sorunsuz okundu (23:33–00:03, 137 cevap 200); sonra Cloudflare bir fiyat sorusuna yeniden doğrulama verdi (geçişin süresi doldu). Program eklentideki ikinci doğrulamayı durdurma sebebi sayıyordu. | Yeniden doğrulama: sekme şirketin ilk sayfasını yeniden açar, doğrulamayı site ya da kullanıcı geçer (eklenti 15 dk bekler), soru bir kez daha sorulur; şirket ve çekim başına en çok 12 kez. 12 sn aralık ve 429 kuralı aynen. |

**Süre.** Eklenti tek pencere ve tek sekmeyle şirketleri sırayla okuyordu; bu yedi şirket (~5.500 istek, site başına 8–12 sn) 12 saati
geçerdi. Eklenti artık programın söylediği kadar işi (6) aynı anda, her birini kendi penceresinde okur; kiralama çekiminin eklenti sırası
6 işçidir; bir şirket baştan sona tek pencereyle okunur (site başına tek pencere, 8 sn kuralı aynen).

**Sıra.** Bu beş site gece "tarayıcı gerektiren" diye işaretlendi; bir sonraki çekimde hepsi programın **tek** tarayıcı sırasına
düşecekti. Artık eklenti eşliyse eklenti sırasına giderler (önce eklenti kuralı); yapılandırmada korumalı siteler (oversee.us,
exclusive30a.com) programın tarayıcısında kalır.

**Denemede bulunan eski bir hata.** panhandlegetaways.com'un bugünkü fiyat dökümünde "Subtotal" (kira + ücret, vergiden önce) satırı var;
Track okuyucusu bunu bir ücret sayıyordu (toplam etkilenmiyordu, ücret toplamı şişerdi). Düzeltildi (Track ve RealJoy). Ekim ve gece
verisinde "Subtotal" satırlı cevap yok.

## 2. İzinli sorgu listesinin yeni hâli

Liste şirket yapılandırmasında (`inventory.extension_queries`); Ayarlar → Tarayıcı eklentisi "İzinli sorgular"da görünür. Yasak liste
(giriş, hesap, ödeme, rezervasyon, sepet, kişisel bilgi, iletişim) aynen; iki tarafta aynı (`studio/extension_queries.py`, `eklenti/logic.js`).

| Alan adı | Yöntem ve yol | Alanlar (sayfanın gönderdiği sırayla) | Yer | Not |
|---|---|---|---|---|
| realjoy.com | POST /ajax/quote | checkin, checkout, propertyID, roomTypeID, propertyName, hash | gövde | GÖREV-25 (değişmedi) |
| realjoy.com | POST /ajax/results/scroll | page, propertyIDs, sortBy | gövde | GÖREV-25 (değişmedi) |
| 30aescapes.com | POST /ajax/quote | checkin, checkout, propertyID, roomTypeID, propertyName, hash | gövde | RealJoy ile aynı Track formu |
| oceanreefresorts.com | POST /ajax/quote | checkin, checkout, propertyID, roomTypeID, propertyName | gövde | formda `hash` yok |
| panhandlegetaways.com | POST /ajax/quote | checkin, checkout, propertyID, roomTypeID, propertyName, hash, numDaysForAvailailityData | gövde | form sona `numDaysForAvailailityData` (430) ekliyor |
| rosemarybeach.com | POST /wp-admin/admin-ajax.php | action, params | **adres** (gövde boş; `Content-Type: application/json`) | `action` yalnız `streamlinecore-api-request`; `params` yalnız `{"methodName":"GetPropertyListWordPress"\|"VerifyPropertyAvailability"\|"GetPreReservationPrice","params":{…}}` |

RealJoy'un `/ajax/quote` düzeninden farklar: Ocean Reef'te `hash` yok; Panhandle'da fazladan `numDaysForAvailailityData`; Rosemary Beach
tamamen başka bir altyapı (Streamline) ve alanlarını adreste gönderiyor. Alanlar gecenin ham kopyasındaki sayfalardan okundu
(30aescapes yanıt 3000, oceanreef 3140, panhandle 3700, rosemary 3488); fixture'lar `tests/fixtures/hedef03/`.

## 3. "Seçili şirketleri yeniden oku"

- **Yeri:** Sol menü → Veri → Toplama → Konaklama → "Konaklama fiyatları" bölümü → "Seçili şirketleri yeniden oku" (açılır bölüm). Son
  sürümün şirketleri kutularla listelenir (durumu ve fiyatlı/sorulan sayısıyla); işaretlenenler için "↻ Seçili şirketleri yeniden oku".
  İş adı "Kiralama şirketleri · Konaklama fiyatları · Seçili şirketleri yeniden oku (N şirket)".
- **Taban:** kaynağın son başarılı kiralama sürümü. Book>Direct çekimi tabandan sonra yenilenmişse iş başlamaz (bütün çekim gerekir);
  seçimdeki her şirket yapılandırmada açık olmalı; hiç sürüm yoksa başlamaz.
- **Okunan:** yalnız seçilen şirketler; haftalar tabanın haftaları (bütün şirketler aynı haftalarla). İşçiler, eklenti sıraları,
  doğrulama ve 429 kuralları normal çekimle aynı.
- **Taşınan:** seçilmeyen her şirketin şirket satırı, ilan satırları, fiyat cevapları, kendi envanteri ve yayımlanmış kiraları tabandan
  **olduğu gibi** yeni sürüme kopyalanır. Taban sürüme dokunulmaz. Sonuç tek ve bütün bir kiralama sürümüdür (bütün şirketler, bütün ilanlar).
- **Sorgu günü:** her şirket satırı kendi gününü taşır (`queried_on`); taşınan satır nereden taşındığını da (`carried_from`). Ekranda
  şirket tablosunda "SORGU GÜNÜ" sütunu: "2026-11-26 · taşındı · 7cba8d4c sürümünden, değişmeden" ya da "2026-11-27". Sürümün metadata'sında
  `secili_okuma` (seçilenler, taban ve günü, taşınan şirket ve fiyat sayısı, taşınanların istek sayısı).
- **Kurtarma:** birleştirme kaydetmeden önce yapılır; kaydetme düşerse birleştirilmiş sonuç `data/kurtarma/<iş>/`'e yazılır ve "Kurtarılan
  sonucu kaydet" ile kaydedilir. Seçim ham kopyanın yanındaki `secim.json`'da; "Ham kopyadan yeniden kur" onu okuyup aynı tabanla kurar.
- **Şema 26 (göç v26):** `agency_rate_companies.queried_on`, `carried_from`; eski satırlara kendi sürümlerinin günü yazıldı. Dört şirketin
  izinli sorusu da bu göçte.
- **Testler:** taşınan şirketin değişmemesi (şirket, ilan ve fiyat satırları birebir), yeniden okunanın değişmesi, sürümün bütün olması,
  veritabanı üzerinden sakla → oku ve taban sürümün değişmemesi, başka Book>Direct çekimi ve bilinmeyen şirket reddi
  (`tests/test_hedef03.py`); ekran (`tests/frontend.test.mjs`).

## 4. Deneme

Sol menü → Veri → Okuma denemeleri → "Deneme çekimini başlat" (iş `abb22586…`, kopya `data/deneme/20261127-151712`, gerçek veriye karışmadı).
13 toplayıcının 13'ü okundu. Kiralama adımı 489 sn; yedi şirketin yedisi "okundu":

| Şirket | eşlenen | fiyat | istek | not |
|---|---:|---:|---:|---|
| 30A Escapes | 1 | 0 | 2 | denemenin tek haftası sayfanın takviminde dolu; fiyat sorulmadı (sorulacak bir hafta yoktu) |
| Ocean Reef Resorts | 2 | 2 | 4 | `/ajax/quote` eklentiden gitti; site yalnız toplamı gösteriyor |
| Panhandle Getaways | 1 | 1 | 3 | kira 4.224,30 $, temizlik 440 $, vergi 559,72 $, toplam 5.224,02 $ |
| Rosemary Beach® | 1 | 1 | 5 | alanlar adreste; şirket listesi 225 ev; toplam 19.044,04 $ |
| RealJoy | 2 | 2 | 31 | liste 313 ev; doğrulama Mucahit'le geçti |
| Vacasa | 2 | 2 | 9 | ABD proxy işçisiyle |
| Alys Beach | 0 (bağlantılar genel sayfa) | kendi evi 2/2 | 7 | sayfa gezintisiyle; şirket listesi 74 ev |

Eklentide 3 şirket aynı anda okundu. **Kaydetme sınaması geçti** (son gerçek çekim ham kopyadan kopyaya 2.384 kayıtla yazıldı). Sınamanın
"sayılar aynı değil" satırı beklenen bir farktır: yeni kod eski ham kopyayı yeniden oynatırken bazı istekler artık farklı (Track formunun
sırası, Vacasa'nın küçük harf hatası), ham kopyada cevabı yok; kaydetme adımı yine geçti. Denemenin gerçek cevaplarından fixture'lar
kesildi (Ocean Reef ve Panhandle fiyat cevabı, Rosemary'nin müsaitlik ve fiyat cevabı). Panhandle'ın cevabı "Subtotal" hatasını ortaya
çıkardı (bölüm 1).

## 5. Gerçek okuma

Önce program kapalıyken tam yedek alındı (`work/yedek/20261127-1537`). Program 0.29.0 ile açıldı; eklenti 0.22.0 bağlıydı. Okuma programın
ekranından başlatıldı: Sol menü → Veri → Toplama → Konaklama → "Konaklama fiyatları" → "Seçili şirketleri yeniden oku". Ekranda 28 şirketin
kutusu görüldü, 7'si işaretlendi. Başlamadan önce Mucahit'e tahmini süre yazıldı (~4 saat).

**Birinci okuma** (iş ve sürüm `7cd2ea67…`, 15:38–19:00, 3 sa 22 dk, 4.481 istek; taban `7cba8d4c`):
- 30A Escapes, Ocean Reef Resorts, Rosemary Beach®, Panhandle Getaways ve RealJoy eklentide **aynı anda**, her biri kendi Chrome penceresinde okundu.
- Vacasa ABD proxy işçisiyle okundu.
- Altısı "done".
- RealJoy'da Cloudflare her ~30 dakikada doğrulamayı yeniden istedi (12:48, 13:18, 13:49, 14:19, 14:49 UTC). Beşinde de sekme sayfayı
  yeniden açtı, doğrulama geçildi, okuma sürdü. Kural gereği sitenin aralığı ilk olayda iki katına çıktı.
- **Alys Beach bu turda atlandı.** İlk sayfası okunduktan sonra şirket sessizce "doğrulama bekliyor, sona bırakıldı"ya düştü. Ham kopyada
  hiç cevabı yok. En olası sebep: 6 pencere aynı anda açılırken eklenti ilk sayfada geçici bir "hata" döndürdü; doğrulayıcı bunu doğrulama
  gibi ele aldı. Sonda eklenti için ayrıca beklenmediğinden şirket "Kullanıcı doğrulaması süresinde tamamlanmadı" diye atlandı (metin yanlış).
- Düzeltme (`8353d0f`): ilk sayfa "hata" ise bir kez daha sorulur. İki kez olursa şirket satırı gerçek sebebi yazar.
- Programın iş parçacıklarını görmek için py-spy kurmak istendi; izin sisteminden geçmedi. Sebep kod okumasıyla bulundu.

**İkinci okuma, yalnız Alys Beach** (iş ve sürüm `8bc68fea…`, 19:05–21:30, 2 sa 25 dk, 965 istek; taban `7cd2ea67`):
- Program kapatıldı, yedek alındı (`work/yedek/20261127-1904`), yeni kodla açıldı.
- Book>Direct'in 6 bağlantısı sekmede açılarak okundu. Hepsi genel sayfa; "ilan sayfası değil" (Ekim'de de böyleydi).
- Şirketin kendi listesi 74 ev; 73 evde en az bir haftanın fiyatı var. Aralık haftası Book>Direct'te de kendi evlerde de fiyatsız.
- Bu sürüm **son ve bütün sürümdür**: 28 şirket, 2.384 ilan.
  - 21 şirket 26 Kasım'dan (7cba8d4c) taşındı.
  - 6 şirket 27 Kasım'ın birinci okumasından (7cd2ea67) taşındı.
  - Alys Beach yeni okundu.
  - Her satırda kendi sorgu günü var.

Gerçek veride değişen satırlar (önce `gercek-once2.json` → sonra `gercek-sonra.json`; şema 26 → 26, `foreign_key_check` 0 → 0; 81 tablo; azalan tablo yok):
`agency_rate_snapshots` 4 → 6, `agency_rate_companies` 85 → 141, `agency_rate_listings` 9.551 → 14.319, `agency_rate_quotes` 32.731 → 63.475,
`agency_rate_own_listings` 243 → 511, `agency_rate_own_quotes` 2.405 → 5.621, `agency_rate_published` 577 → 1.017, `road_snapshots` 2 → 3,
`road_nearest` 46.130 → 69.170, `evidence_packs` 10 → 14, `source_runs` 40 → 43, `jobs` 63 → 66.

## 6. Yol ağı

Yedekten sonra (`work/yedek/20261127-2132`) programın normal kullanımıyla yeniden çalıştırıldı (sürüm `f72609d3`, 27 Kasım 21:34).
- Girdiler: konaklama 42fa6655, günlük ihtiyaç **8ad3a93c (27 Kasım)**, plaj **0d9d251c (27 Kasım)**. Önceki ölçüm Ekim sürümleriyleydi.
- Ağ: 19.672 yol, 4.422 km. 2.384 ilandan 2.305'i yola bağlandı, 2.304'ü ölçüldü, 102 hedef.

## 7. Kapsam tabloları (önce ve sonra)

Kaynak: gerçek veritabanının son kopyası (program kapalıyken, salt okunur; `work/hedef3/son.sqlite3`).

#### 13 mahalle — önce ve sonra yan yana (önce: sürüm 7cba8d4c, sorgu günü 2026-11-26; sonra: sürüm 8bc68fea)

| Mahalle | Book>Direct ilanı | şirkete bağlanan (önce → sonra) | en az bir haftası fiyatlı (önce → sonra) | kendi envanterinden fiyatlı ev (önce → sonra) | Ocak ortancası (önce → sonra) | Temmuz ortancası (önce → sonra) |
|---|---:|---:|---:|---:|---:|---:|
| Dune Allen | 114 | 50 → 58 | 47 → 55 | 0 → 0 | 3.116 $ (29) → 3.116 $ (33) | 5.608 $ (36) → 5.608 $ (41) |
| Gulf Place | 31 | 12 → 16 | 12 → 16 | 0 → 0 | 1.686 $ (10) → 1.715 $ (13) | 4.525 $ (12) → 4.457 $ (16) |
| Santa Rosa Beach | 246 | 55 → 75 | 48 → 68 | 0 → 0 | 2.025 $ (35) → 2.170 $ (49) | 4.798 $ (42) → 5.395 $ (57) |
| Blue Mountain Beach | 194 | 90 → 101 | 69 → 79 | 0 → 0 | 2.268 $ (45) → 2.303 $ (53) | 5.694 $ (66) → 5.526 $ (74) |
| Grayton Beach | 86 | 23 → 49 | 19 → 44 | 0 → 0 | 4.770 $ (12) → 3.049 $ (23) | 7.908 $ (13) → 5.996 $ (27) |
| WaterColor | 256 | 150 → 154 | 145 → 149 | 0 → 0 | 5.529 $ (100) → 5.527 $ (101) | 11.258 $ (119) → 11.202 $ (123) |
| Seaside | 221 | 134 → 134 | 127 → 127 | 0 → 0 | 4.731 $ (78) → 4.731 $ (78) | 8.504 $ (97) → 8.504 $ (97) |
| Seagrove | 497 | 256 → 304 | 250 → 298 | 0 → 0 | 1.711 $ (168) → 1.879 $ (195) | 5.096 $ (228) → 5.144 $ (264) |
| WaterSound | 165 | 32 → 66 | 28 → 62 | 2 → 2 | 5.019 $ (19) → 2.992 $ (46) | 8.480 $ (27) → 6.269 $ (60) |
| Seacrest | 300 | 87 → 168 | 84 → 162 | 7 → 7 | 2.519 $ (68) → 2.825 $ (112) | 6.781 $ (68) → 7.251 $ (132) |
| Alys Beach | 7 | 0 → 0 | 0 → 0 | 0 → 73 | — (0) → 9.921 $ (45 kendi) | — (0) → 17.254 $ (60 kendi) |
| Rosemary Beach | 166 | 22 → 104 | 20 → 102 | 1 → 1 | 3.848 $ (10) → 3.574 $ (60) | 13.017 $ (17) → 6.987 $ (87) |
| Inlet Beach | 101 | 42 → 52 | 40 → 51 | 0 → 0 | 2.712 $ (33) → 3.013 $ (42) | 6.757 $ (34) → 6.906 $ (42) |

Hücre: o haftanın vergi ve ücretler dahil 7 gecelik toplam ortancası (fiyatlı ilan sayısı). "Kendi envanteri": tek bir topluluğun resmî kiralama programı (Alys Beach) gibi, Book>Direct'e bağlanmadan şirketin kendi listesinden okunan evler.

#### 13 mahalle — kiralama, 12 ay (sonra: sürüm 8bc68fea)

| Mahalle | Oca | Şub | Mar | Nis | May | Haz | Tem | Ağu | Eyl | Eki | Kas | Ara |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dune Allen | 3.116 $ (33) | 3.091 $ (33) | 3.875 $ (45) | 3.428 $ (38) | 5.425 $ (42) | 5.506 $ (42) | 5.608 $ (41) | 3.973 $ (50) | 3.875 $ (46) | 3.483 $ (38) | 3.945 $ (19) | 3.387 $ (17) |
| Gulf Place | 1.715 $ (13) | 1.971 $ (12) | 3.364 $ (11) | 2.639 $ (13) | 3.352 $ (14) | 4.415 $ (15) | 4.457 $ (16) | 2.949 $ (16) | 2.473 $ (16) | 3.070 $ (16) | 2.491 $ (16) | 2.249 $ (12) |
| Santa Rosa Beach | 2.170 $ (49) | 2.338 $ (40) | 3.282 $ (49) | 2.841 $ (54) | 3.826 $ (53) | 4.917 $ (54) | 5.395 $ (57) | 3.274 $ (60) | 2.852 $ (63) | 3.401 $ (62) | 2.373 $ (65) | 2.980 $ (50) |
| Blue Mountain Beach | 2.303 $ (53) | 2.376 $ (45) | 3.584 $ (59) | 3.048 $ (61) | 3.922 $ (67) | 5.428 $ (71) | 5.526 $ (74) | 3.490 $ (75) | 3.118 $ (75) | 3.674 $ (71) | 2.527 $ (72) | 2.406 $ (69) |
| Grayton Beach | 3.049 $ (23) | 3.001 $ (18) | 3.941 $ (19) | 3.209 $ (29) | 5.218 $ (31) | 6.580 $ (31) | 5.996 $ (27) | 4.355 $ (38) | 3.485 $ (34) | 4.393 $ (34) | 3.224 $ (42) | 3.972 $ (41) |
| WaterColor | 5.527 $ (101) | 5.633 $ (81) | 8.162 $ (89) | 7.174 $ (102) | 8.008 $ (92) | 10.485 $ (108) | 11.202 $ (123) | 7.058 $ (137) | 6.596 $ (120) | 8.256 $ (98) | 5.771 $ (115) | 5.613 $ (120) |
| Seaside | 4.731 $ (78) | 4.934 $ (48) | 7.274 $ (68) | 6.421 $ (79) | 6.186 $ (77) | 7.758 $ (88) | 8.504 $ (97) | 6.163 $ (118) | 5.858 $ (106) | 6.336 $ (90) | 5.992 $ (109) | 5.217 $ (112) |
| Seagrove | 1.879 $ (195) | 2.257 $ (144) | 2.886 $ (209) | 2.545 $ (235) | 3.252 $ (240) | 4.384 $ (268) | 5.144 $ (264) | 3.046 $ (281) | 2.791 $ (276) | 3.691 $ (274) | 2.133 $ (284) | 2.680 $ (123) |
| WaterSound | 2.992 $ (46) | 4.204 $ (36) | 5.673 $ (47) | 3.792 $ (48) | 4.360 $ (50) | 6.352 $ (59) | 6.269 $ (60) | 4.416 $ (59) | 3.528 $ (59) | 4.575 $ (55) | 3.921 $ (60) | 3.569 $ (51) |
| Seacrest | 2.825 $ (112) | 3.169 $ (94) | 4.991 $ (100) | 4.138 $ (111) | 4.933 $ (127) | 6.712 $ (125) | 7.251 $ (132) | 4.553 $ (158) | 4.008 $ (147) | 5.093 $ (147) | 3.641 $ (150) | 3.005 $ (62) |
| Alys Beach | 9.921 $ (45 kendi) | 9.887 $ (30 kendi) | 14.001 $ (50 kendi) | 11.551 $ (57 kendi) | 12.661 $ (58 kendi) | 16.943 $ (65 kendi) | 17.254 $ (60 kendi) | 10.718 $ (69 kendi) | 10.493 $ (67 kendi) | 13.369 $ (61 kendi) | 9.386 $ (65 kendi) | — (0) |
| Rosemary Beach | 3.574 $ (60) | 4.050 $ (68) | 5.597 $ (70) | 4.734 $ (58) | 5.410 $ (60) | 6.789 $ (86) | 6.987 $ (87) | 4.865 $ (94) | 4.757 $ (92) | 5.706 $ (72) | 4.490 $ (94) | 4.578 $ (72) |
| Inlet Beach | 3.013 $ (42) | 3.097 $ (38) | 5.353 $ (34) | 4.057 $ (36) | 3.777 $ (41) | 6.787 $ (46) | 6.906 $ (42) | 4.548 $ (50) | 3.986 $ (47) | 4.864 $ (46) | 3.749 $ (51) | 3.505 $ (38) |

#### 13 mahalle — kiralama, 12 ay (önce: sürüm 7cba8d4c)

| Mahalle | Oca | Şub | Mar | Nis | May | Haz | Tem | Ağu | Eyl | Eki | Kas | Ara |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dune Allen | 3.116 $ (29) | 2.971 $ (28) | 3.483 $ (39) | 3.317 $ (33) | 5.344 $ (37) | 5.506 $ (36) | 5.608 $ (36) | 3.875 $ (43) | 3.875 $ (40) | 3.385 $ (34) | 4.163 $ (12) | 3.560 $ (12) |
| Gulf Place | 1.686 $ (10) | 1.873 $ (11) | 3.197 $ (8) | 2.555 $ (10) | 3.546 $ (11) | 4.418 $ (12) | 4.525 $ (12) | 2.917 $ (12) | 2.481 $ (12) | 3.004 $ (12) | 2.324 $ (12) | 2.249 $ (12) |
| Santa Rosa Beach | 2.025 $ (35) | 2.195 $ (28) | 3.173 $ (36) | 2.712 $ (41) | 3.416 $ (39) | 4.778 $ (42) | 4.798 $ (42) | 3.054 $ (44) | 2.744 $ (45) | 3.383 $ (46) | 2.186 $ (45) | 2.162 $ (30) |
| Blue Mountain Beach | 2.268 $ (45) | 2.376 $ (37) | 3.638 $ (52) | 3.135 $ (52) | 3.982 $ (58) | 5.558 $ (63) | 5.694 $ (66) | 3.528 $ (66) | 3.170 $ (65) | 3.714 $ (62) | 2.618 $ (63) | 2.312 $ (61) |
| Grayton Beach | 4.770 $ (12) | 5.808 $ (8) | 4.809 $ (9) | 7.453 $ (14) | 8.216 $ (14) | 9.650 $ (14) | 7.908 $ (13) | 8.602 $ (15) | 6.819 $ (16) | 8.697 $ (16) | 5.746 $ (18) | 6.450 $ (17) |
| WaterColor | 5.529 $ (100) | 5.633 $ (79) | 8.217 $ (88) | 7.174 $ (100) | 8.208 $ (88) | 10.720 $ (106) | 11.258 $ (119) | 7.105 $ (134) | 6.599 $ (117) | 8.359 $ (94) | 5.772 $ (111) | 5.613 $ (120) |
| Seaside | 4.731 $ (78) | 4.934 $ (48) | 7.274 $ (68) | 6.421 $ (79) | 6.186 $ (77) | 7.758 $ (88) | 8.504 $ (97) | 6.163 $ (118) | 5.858 $ (106) | 6.336 $ (90) | 5.992 $ (109) | 5.217 $ (112) |
| Seagrove | 1.711 $ (168) | 2.157 $ (121) | 2.737 $ (178) | 2.407 $ (205) | 3.168 $ (204) | 4.361 $ (228) | 5.096 $ (228) | 2.949 $ (236) | 2.717 $ (232) | 3.635 $ (229) | 1.920 $ (239) | 2.717 $ (102) |
| WaterSound | 5.019 $ (19) | 5.233 $ (18) | 7.029 $ (19) | 6.349 $ (22) | 6.908 $ (19) | 8.427 $ (26) | 8.480 $ (27) | 6.581 $ (27) | 6.160 $ (26) | 6.834 $ (23) | 5.633 $ (26) | 5.742 $ (24) |
| Seacrest | 2.519 $ (68) | 2.909 $ (55) | 4.738 $ (60) | 3.670 $ (67) | 4.188 $ (73) | 6.228 $ (73) | 6.781 $ (68) | 4.195 $ (83) | 3.743 $ (78) | 4.718 $ (80) | 3.004 $ (78) | 2.845 $ (50) |
| Alys Beach | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) |
| Rosemary Beach | 3.848 $ (10) | 5.673 $ (15) | 8.340 $ (7) | 8.536 $ (14) | 9.848 $ (16) | 12.602 $ (19) | 13.017 $ (17) | 8.351 $ (20) | 6.786 $ (17) | 9.101 $ (18) | 5.768 $ (19) | 4.973 $ (19) |
| Inlet Beach | 2.712 $ (33) | 2.739 $ (29) | 5.398 $ (29) | 3.766 $ (31) | 3.739 $ (34) | 6.619 $ (37) | 6.757 $ (34) | 4.254 $ (40) | 3.989 $ (38) | 4.420 $ (38) | 3.200 $ (40) | 3.438 $ (34) |

#### Kiralama şirketleri — önce ve sonra yan yana

| Şirket | Durum (önce → sonra) | Book>Direct ilanı | bağlanan (önce → sonra) | fiyatlanan ilan × hafta (önce → sonra) | kendi evi (önce → sonra) | istek (sonra) | sorgu günü (sonra) |
|---|---|---:|---:|---:|---:|---:|---|
| 360 Blue (360blue.com) | done → done | 256 | 126 → 126 | 1083 → 1083 | 0 → 0 | 1336 | 2026-11-26 (taşındı · 7cba8d4c) |
| Benchmark Management (benchmark30a.com) | done → done | 241 | 187 → 187 | 1685 → 1685 | 0 → 0 | 4368 | 2026-11-26 (taşındı · 7cba8d4c) |
| Oversee (oversee.us) | done → done | 182 | 176 → 176 | 1705 → 1705 | 0 → 0 | 2298 | 2026-11-26 (taşındı · 7cba8d4c) |
| 30A Escapes (30aescapes.com) **(yeniden okundu)** | stopped_errors → done | 162 | 1 → 141 | 0 → 1099 | 0 → 0 | 1420 | 2026-11-27 (taşındı · 7cd2ea67) |
| Homeowner's Collection (homeownerscollection.com) | done → done | 143 | 118 → 118 | 933 → 933 | 0 → 0 | 2746 | 2026-11-26 (taşındı · 7cba8d4c) |
| Southern Vacation Rentals (southernresorts.com) | done → done | 104 | 64 → 64 | 636 → 636 | 0 → 0 | 946 | 2026-11-26 (taşındı · 7cba8d4c) |
| Ocean Reef Resorts (oceanreefresorts.com) **(yeniden okundu)** | stopped_errors → done | 96 | 1 → 71 | 0 → 598 | 0 → 0 | 725 | 2026-11-27 (taşındı · 7cd2ea67) |
| Rosemary Beach® (rosemarybeach.com) **(yeniden okundu)** | stopped_errors → done | 89 | 1 → 59 | 0 → 539 | 0 → 0 | 1335 | 2026-11-27 (taşındı · 7cd2ea67) |
| Dune Allen Realty Vacation Rentals (beautifulbeach.com) | done → done | 88 | 37 → 37 | 260 → 260 | 0 → 0 | 584 | 2026-11-26 (taşındı · 7cba8d4c) |
| Panhandle Getaways (panhandlegetaways.com) **(yeniden okundu)** | stopped_errors → done | 81 | 1 → 33 | 0 → 347 | 0 → 0 | 429 | 2026-11-27 (taşındı · 7cd2ea67) |
| RealJoy Vacations (realjoy.com) **(yeniden okundu)** | stopped_blocked → done | 61 | 10 → 32 | 100 → 299 | 0 → 0 | 363 | 2026-11-27 (taşındı · 7cd2ea67) |
| Paradise Properties (paradise30a.com) | done → done | 58 | 32 → 32 | 345 → 345 | 0 → 0 | 500 | 2026-11-26 (taşındı · 7cba8d4c) |
| 30A Vacay (30a-vacay.com) | done → done | 54 | 8 → 8 | 78 → 78 | 0 → 0 | 271 | 2026-11-26 (taşındı · 7cba8d4c) |
| Dune Vacation Rentals (dunevacationrentals.com) | done → done | 49 | 35 → 35 | 281 → 281 | 0 → 0 | 787 | 2026-11-26 (taşındı · 7cba8d4c) |
| 30A Beach Girls (30a-beachgirls.com) | done → done | 48 | 0 → 0 | 0 → 0 | 97 → 97 | 242 | 2026-11-26 (taşındı · 7cba8d4c) |
| Grayt 30A Vacations / Royal Destinations (grayt30avacations.com) | done → done | 41 | 2 → 2 | 12 → 12 | 0 → 0 | 130 | 2026-11-26 (taşındı · 7cba8d4c) |
| Sanders Beach Rentals (sandersbeachrentals.com) | done → done | 38 | 26 → 26 | 189 → 189 | 0 → 0 | 586 | 2026-11-26 (taşındı · 7cba8d4c) |
| Vacasa (vacasa.com) **(yeniden okundu)** | stopped_errors → done | 35 | 3 → 9 | 23 → 83 | 0 → 0 | 209 | 2026-11-27 (taşındı · 7cd2ea67) |
| FunVacay (funvacay.com) | done → done | 31 | 23 → 23 | 221 → 221 | 0 → 0 | 518 | 2026-11-26 (taşındı · 7cba8d4c) |
| Exclusive 30A (exclusive30a.com) | done → done | 29 | 10 → 10 | 95 → 95 | 0 → 0 | 149 | 2026-11-26 (taşındı · 7cba8d4c) |
| Your Friend at the Beach (yourfriendatthebeach.com) | done → done | 22 | 20 → 20 | 0 → 0 | 0 → 0 | 285 | 2026-11-26 (taşındı · 7cba8d4c) |
| 30A Beach Stays (30abeachstays.com) | done → done | 21 | 17 → 17 | 155 → 155 | 0 → 0 | 286 | 2026-11-26 (taşındı · 7cba8d4c) |
| 30A Cottages (30acottagesandconcierge.com) | done → done | 17 | 14 → 14 | 100 → 100 | 0 → 0 | 290 | 2026-11-26 (taşındı · 7cba8d4c) |
| Grayton Coast Rentals (graytoncoastrentals.com) | done → done | 17 | 11 → 11 | 88 → 88 | 0 → 0 | 245 | 2026-11-26 (taşındı · 7cba8d4c) |
| Newman-Dailey Resort Properties (destinvacation.com) | done → done | 15 | 15 → 15 | 141 → 141 | 0 → 0 | 201 | 2026-11-26 (taşındı · 7cba8d4c) |
| My Vacation Haven (myvacationhaven.com) | done → done | 15 | 7 → 7 | 65 → 65 | 0 → 0 | 177 | 2026-11-26 (taşındı · 7cba8d4c) |
| Coastal Blue Vacations (coastalbluevacations.com) | done → done | 12 | 8 → 8 | 60 → 60 | 0 → 0 | 189 | 2026-11-26 (taşındı · 7cba8d4c) |
| Alys Beach Vacation Rentals (alysbeach.com) **(yeniden okundu)** | stopped_errors → done | 6 | 0 → 0 | 0 → 0 | 0 → 74 | 965 | 2026-11-27 |

Toplam (önce → sonra): bağlanan 953 → 1281; en az bir haftası fiyatlı 889 → 1213; kendi envanterinden ev 97 → 171 (fiyatlı 92 → 165); fiyatı olan mahalle 12/13 → 12/13.

Yeniden okunan yedi şirketin ayrıntısı (sonra):

| Şirket | durum | bağlanan | fiyat sorusu | fiyatlı | kendi evi | istek | yeniden doğrulama | mesaj |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 30A Escapes | done | 141 | 1692 | 1099 | 0 | 1420 | 0 |  |
| Ocean Reef Resorts | done | 71 | 852 | 598 | 0 | 725 | 0 |  |
| Rosemary Beach® | done | 59 | 708 | 539 | 0 | 1335 | 0 |  |
| Panhandle Getaways | done | 33 | 396 | 347 | 0 | 429 | 0 |  |
| RealJoy Vacations | done | 32 | 384 | 299 | 0 | 363 | 0 |  |
| Vacasa | done | 9 | 108 | 83 | 0 | 209 | 0 |  |
| Alys Beach Vacation Rentals | done | 0 | 0 | 0 | 74 | 965 | 0 |  |

Seçili okuma kaydı: {"sirketler": ["alysbeach.com"], "taban_surum": "7cd2ea67493a44b694938d161181f784", "taban_sorgu_gunu": "2026-11-27", "tasinan_sirket": 27, "tasinan_fiyat": 16536, "tasinan_istek": 21615}


**Notlar:**
- **Alys Beach.** Fiyatlar Book>Direct ilanlarından değil, topluluğun resmî kiralama programının kendi 73 evinden gelir. Bu satırlar "kendi"
  diye işaretli; kanıt paketinde de "(kendi envanteri)" satırıdır ve Book>Direct ilanlarıyla karşılaştırılmaz. Program "fiyatı olan
  mahalle" sayısında yalnız Book>Direct hücrelerini sayar (12/13); Alys Beach'in fiyatı ayrı bölümdedir.
- **Rosemary Beach.** 20 → 102 fiyatlı ilan. Temmuz ortancası 13.017 $ (17 ilan) → 6.987 $ (87 ilan). Önceki değer küçük örnekti (yalnız
  birkaç şirket); yeni örnekte Rosemary Beach® ve Ocean Reef gibi şirketlerin daha geniş ev yelpazesi var.
- **Grayton Beach ve WaterSound.** Fiyatlı ilan sayıları ikiye katlandı, ortancalar düştü (örnek büyüdü). Bu, örneğin değiştiği anlamına
  gelir; fiyatların düştüğü anlamına gelmez.
- **Değişmeyen şirketlerin sayıları.** 26 Kasım'daki gibidir (taşındı).
- **30A Escapes.** Aralık 2027 haftasına site "365 günden ileri rezervasyon alınmıyor" dedi (37 cevap). Sitenin kendi sınırıdır.

## 8. Veri paketi ve tahminler

**Bulunan ve düzeltilen hata (`ddd8818`).** Yeni kiralama sürümünden sonra video 2 · Veri paketi "eskidi"ye düştü. İlk yeniden kurulumda
(`93c5120e`) kiralama fiyatı bloğu (156 satır) pakete **hiç girmedi**.
- Sebep: video paketi, başlık değerlendirmesinin atıf yaptığı kanıt satırlarını ifadesinin metniyle tanıyordu.
- Fiyat ifadesinde sorgu günü ("2026-11-26 tarihinde") ve çeyrek tutarları geçtiği için, yeniden okunan veride aynı satırlar "yok" sayıldı.
- Düzeltme: satırın kimliğinde gün ve dolar tutarları yok sayılır; satır "değeri farklı" olarak eşleşir. Test:
  `test_a_cited_price_row_is_the_same_row_after_the_prices_are_asked_again`.
- Düzeltmeden sonra program kapatılıp yedek alındı (`work/yedek/20261127-2138`), paket yeniden kuruldu.

**Videonun durumu** (`7b025758…`):
- 1 · Başlık ve vaat: onaylı (değişmedi).
- 2 · Veri paketi: **tamamlandı**, paket `85f0dc79` (`data/evidence/20261127-183938-video-plani-85f0dc79.md`): 6 bölüm, **840 kanıt, 1.951
  sayı, 13 eksik**. Önceki `9f9d489c`: 840 / 1.901 / 27. "Ne tutar" bölümünde 156 fiyat satırı yeni sürümden; Alys Beach artık "(kendi
  envanteri)" satırıyla fiyatlı.
- 3 · Plan: **hazır** (çalıştırılmadı).

**Tahminler** (ekrandaki tahmin düzeniyle; plan satırı 3 · Plan ekranındakiyle aynı; 4 · Yazım'ın kendi tahmini plan onaylanınca görünür,
bu yüzden zincir tahmini veritabanı kopyasında hesaplandı; tonlar Araştırmacı dost ve Vlogger):

| Kısım | Çağrı | Okunan | Yazılan | Toplam |
|---|---:|---:|---:|---:|
| Plan | 2 | 246.432 | 26.000 | 272.432 |
| Araştırmacı dost | 10 | 312.488 | 82.000 | 394.488 |
| Vlogger | 10 | 312.438 | 82.000 | 394.438 |
| **Toplam** | 22 | 871.358 | 190.000 | 1.061.358 |

Plan: 2 çağrı, yaklaşık 272 bin token · Araştırmacı dost: 10 çağrı, yaklaşık 394 bin token · Vlogger: 10 çağrı, yaklaşık 394 bin token · Toplam: yaklaşık 1,1 milyon token

Önceki tahmin 1.057.877 tokendi; fark yeni paketin biraz daha büyük olmasından.

## 9. Açık kalanlar

1. **Your Friend at the Beach**'in fiyat servisi "You are not authorized" diyor (bu hedefin yedi şirketi arasında değil; değişmedi).
2. **Hava tahmini, iklim, deniz suyu, kasırga, restoranların kendi siteleri, uçak bileti** Ekim ve Kasım ortası sürümleri (bu hedefin izinli
   listesinde değildi).
3. **Alys Beach'in "fiyatı olan mahalle" sayımı.** Program bu sayımda Book>Direct hücrelerine bakıyor; Alys Beach'in fiyatı "kendi envanteri"
   bölümünde. Rapor ve kanıt paketi bunu ayrı yazıyor; ekrandaki "12/13" yanlış değil, tanımı böyle.
4. **Videonun başlığı** hâlâ Mucahit'in onayını bekliyor (HEDEF-02'deki gibi yönetici önerisiyle onaylı). 3 · Plan ve 4 · Yazım bu hedefin
   dışında.
5. **Kalite ekranındaki 4 katalog kaydı** toplayıcısız (bilinen).

## 10. Yedekler

- `work/yedek/20261127-1514/`: hedef başında, program kapalıyken, şema 25 (65.496 dosya, 2.706.340.617 bayt; kaynakla aynı).
- `work/yedek/20261127-1537/`: deneme bitince, gerçek okumadan önce, şema 26 (65.672 dosya, 2.895.217.103 bayt).
- `work/yedek/20261127-1904/`: birinci okumadan sonra, Alys Beach'ten önce (70.155 dosya, 2.948.205.612 bayt).
- `work/yedek/20261127-2132/`: Alys Beach'ten sonra, yol ağından önce (71.122 dosya, 2.982.618.888 bayt).
- `work/yedek/20261127-2138/`: video paketinin düzeltilmiş kurulumundan önce (71.132 dosya, 3.017.017.664 bayt).
- Programın göç yedeği: `data/backups/studio-v25-….sqlite3` (şema 25 → 26).

Her yedek program kapalıyken alındı; bayt sayıları kaynakla aynı.

## 11. Testler ve CI

- Yeni: `tests/test_hedef03.py` (22 test; biri üç Track sitesiyle parametreli) ve `tests/fixtures/hedef03/`. Fixture'lar gecenin ham kopyasından (Track formları, Vacasa
  cevapları, RealJoy'un Cloudflare sayfası, Rosemary'nin sayfası) ve denemenin gerçek cevaplarından (Ocean Reef ve Panhandle fiyatı,
  Rosemary'nin müsaitlik ve fiyat cevabı) kesildi. Kapsadıkları:
  - her Track sitesinin kendi formu ve izinli listesi;
  - Streamline'ın adresteki alanları ve yöntem deseni;
  - iki tarafın listelerinin eşitliği ve göç v26;
  - Vacasa'nın küçük harfli hatası;
  - fetch'in alamadığı sayfanın sekmede açılması;
  - yeniden doğrulama ve sınırı;
  - eklenti sırasının 6 işçisi ve "tek şirket, tek işçi" kuralı;
  - doğrulama gösteren sitenin eklenti sırasına gitmesi;
  - ilk sayfa hatasının bir kez daha sorulması;
  - seçili okuma: taşınan değişmez, okunan değişir, sürüm bütün, veritabanı üzerinden sakla → oku, taban değişmez, ret durumları;
  - "Subtotal" satırının ücret sayılmaması;
  - video paketinde yeniden çekilmiş fiyat satırının eşleşmesi.
- `tests/frontend.test.mjs`: şirketin sorgu günü, "Seçili şirketleri yeniden oku" bölümü, `queryRequest` (adres/gövde, içerik türü),
  desen reddi, `parallelOf`.
- Uçtan uca eklenti testi (`STUDIO_EKLENTI_E2E=1`; yerel sayfalar, Playwright Chromium, geçici profil; CI'da yok): 4/4. Yeni test: iki oturum
  aynı anda iki pencerede, alanları adreste giden POST'un gövdesi boş, iş bitince iki pencere de kapanıyor.
- Güncellenen eski testler: şema 25 → 26, uygulama 0.29.0, eklenti 0.22.0; GÖREV-17'nin pencere metni kontrolü (pencere artık işin
  oturumu başına); GÖREV-25'in izinli liste testi (artık beş şirket).
- Yerel tam takım (son kod): `.venv\Scripts\python.exe -m pytest -q` → **1309 geçti, 4 atlandı**; `node --test tests/frontend.test.mjs` →
  **146/146**.
- GitHub CI: 45999725727 (`2d31815`, kod) ve 46052815261 (`8468cbc`, kod ve rapor) **başarılı**. Rapor satırını ekleyen commit'in CI'ı (46053670270, `8a151f4`) bu hedefin değiştirmediği bir testte düştü: `test_gorev18.py::test_a_cut_answer_is_its_own_case_and_is_not_used` (JSONDecodeError). Test, sahte Claude'un kayıt dosyasını dosyaya hâlâ yazılırken okuyabiliyordu (zamanlamaya bağlı yarış; yerelde 5/5 geçti). Yardımcı (`tests/test_claude_steps.py` `calls`) yarım yazılmış dosyayı birkaç saniye içinde yeniden okuyacak biçimde düzeltildi. Son commit'in CI'ı main'e almadan önce beklendi.

## 12. Uyulan kurallar

- **Okunanlar.** Bütün kiralama çekimi başlatılmadı; yalnız yedi şirket okundu (Alys Beach ikinci kez, tek başına). Sitelere aralık ve
  sıra kuralları aynen uygulandı (site başına 8 sn, RealJoy 12 sn, 429 kuralı, doğrulamada aralığın iki katına çıkması). Eklentide site
  başına tek pencere vardı; işçi ve çıkış değiştirilmedi.
- **Canlı inceleme.** Toplam 6 doğrudan istek (site başına 1).
- **Doğrulama.** Doğrulamayı program çözmedi. Denemedeki RealJoy doğrulaması için Mucahit'e haber verildi; gerçek okumadaki
  doğrulamalar sekmede geçti.
- **Gerçek Claude** çalıştırılmadı.
- **Veri güvenliği.** Gerçek veri yalnız programın normal kullanımıyla değişti; her değişiklikten önce program kapalıyken tam yedek alındı.
  `data/` içinde elle dosya değiştirilmedi, kullanıcı verisi silinmedi.
- **Dokunulmayanlar.** Proxy bilgisi hiçbir yere yazılmadı. Talimat dosyalarına dokunulmadı (dal açılışında kullanıcı değişikliği yoktu).
  Zamanlanmış görev oluşturulmadı.
- **Alt ajan** kullanılmadı.
