# Mahalle rehberi

**Ana soru:** Bu mahallede kalmak nasıl bir deneyim: plaja, yemeğe ve günlük ihtiyaçlara erişim, konaklama fiyatı ve sezon? (Paket yalnız kanıtı verir.)

**Parametreler:** mahalle = Rosemary Beach (rosemary-beach)

- Üretim tarihi: 2026-10-10T12:51:37+00:00
- Destinasyon: 30A
- Şablon: mahalle-rehberi (sürüm 1)
- Bu paket yorum, tavsiye ya da sıralama içermez; yalnız kanıt, etiketi ve kullanım notu.
- Değerler ABD birimleriyle (°F, inç, mil, USD) ve ABD sayı biçimiyle (binlik virgül, ondalık nokta) yazılır; °C, mm ve km karşılıkları yanında.
- Boyut: 8 bölüm, 174 kanıt satırı, 556 sayı, 0 'veri yok' satırı

## Kaynakların son çekimi

| Kaynak | Son çekim | Çekim kimliği | Sonraki | Zamanı geldi mi |
|---|---|---|---|---|
| Kiralama şirketleri · Konaklama fiyatları | 2026-10-10 | b85a4b4e414a48508224575a378f0697 | 2026-11-10 | hayır |
| South Walton · Konaklama (Book>Direct) | 2026-10-09 | 5b5d0115f73f4edda3ef7003dfb99325 | 2026-11-09 | hayır |
| NOAA NHC · HURDAT2 kasırga izleri | 2026-10-07 | 4f23d0a272f14bb7a44bb40b26cb55a0 | — | hayır |
| NOAA NCEI · İklim normalleri 1991–2020 | 2026-10-07 | 80f41ce6a8114392874747a108182cf7 | — | hayır |
| NOAA NDBC · Deniz suyu sıcaklığı | 2026-10-07 | a8cbe865958f4975bca01e5a27671c38 | — | hayır |
| OpenStreetMap · Günlük ihtiyaç noktaları | 2026-10-10 | 080b04f1048c42388764fbe901543528 | — | hayır |
| Restoranlar · İşletme siteleri | 2026-10-09 | 1f1155b10aec44bdab98736e56892cc4 | 2027-01-09 | hayır |
| South Walton · Plaj erişimleri | 2026-10-07 | 1a195e2b27604fbb9443f7376434df6d | — | hayır |
| South Walton · Mahalleler | 2026-10-07 | 3d1cbe8d5efc4e0fbae432786d57be23 | — | hayır |

## Bilinen boşluklar

- Fiyatı okunamayan kiralama şirketleri (sitesi için okuyucu yok, Book>Direct ilan sayısıyla): 360blue.com 256, rentals.cottagerentalagency.com 82, realjoy.com 61, vrbo.com 52, 30a-beachgirls.com 48, vacasa.com 21, outdoorshower30a.com 21.
- Sitesi doğrudan isteği engellediği için fiyatı okunamayan ilan: 51.
- Gulf Place: kiralama fiyatında küçük örnek (pencere başına ortanca 14 ilan).
- Alys Beach: fiyatlar tek bir şirketin kendi envanterinden geliyor; Book>Direct ilanlarıyla karşılaştırılmaz.
- Restoranlar: 138 restoranın 72'inde fiyat seviyesi hesaplanamadı (menü yok, fiyat yok ya da 5'ten az ana yemek fiyatı).
- Günlük ihtiyaç noktaları OpenStreetMap'e dayanır; OpenStreetMap eksik ya da eski olabilir. Mesafeler kuş uçuşudur.
- Resmî kaynakta doğrulanamadığı için acil sağlık ölçülerine girmeyen OpenStreetMap noktası: 1.
- Bu bilgisayardan sitesi okunamayan zincir ve kurumlar (noktaları doğrulanamadı): CVS Pharmacy, Doc Smiley's Urgent Care, HCA Florida Healthcare, Publix, The Fresh Market, Winn-Dixie.
- Doğrulanamayan referans satırları (videoda kullanılmaz): hukuk-iddia-ozel-plaj-kalmadi, tarih-alys-kurulus.
- Book>Direct ilan sayıları tarihli aramalarda görünen ilanlardır; tam envanter değildir.

Etiketler: kaynak gerçeği, bizim hesabımız, türetilmiş, yaklaşık. 'veri yok' satırları eksik veriyi gösterir; paketten düşürülmez.

## Mahallenin resmî tanımı

**Soru:** Resmî dizin bu mahalleyi nasıl tanımlıyor?


### Veri bloğu: neighborhoods

- **K0001** · Rosemary Beach: Visit South Walton mahalle dizininde 30A mahallesi olarak listeleniyor; kaynağın etiketleri: Architecture, Arts & Culture, Family, Foodie Favorite, Music & Nightlife, Romance, Shopping & Spa, Walkable
  - Kapsam: Rosemary Beach · Etiket: kaynak gerçeği
  - Kaynak: [South Walton · Mahalleler](https://www.visitsouthwalton.com/neighborhoods/rosemary-beach/) · erişim 2026-10-07 · çekim 3d1cbe8d5efc4e0fbae432786d57be23 · SHA-256 f827ffecba3de2b204ed8f5a9867269ab6186bed50f5c43037f8a5dd84c5a241
  - Kaynaktan kısa alıntı: “Cobblestone streets and winding paths invite exploration of this popular neighborhood.”
  - Kullanım notu: Kaynak metinleri (kısa tanıtım, sayfa tanıtım metni, etiketler) yalnız iç araştırma kanıtıdır; videoda aynen kullanılmaz, kendi cümlelerimizle ve atıfla kullanılır. (M7)

## Plaj erişimleri

**Soru:** Mahalleye düşen halka açık plaj erişimleri hangileri ve olanakları ne?


### Veri bloğu: beach_accesses

- **K0002** · Rosemary Beach: ilçenin halka açık erişim listesinde bu mahalleye eşlenen erişim yok — **0 erişim**
  - Kapsam: Rosemary Beach · Etiket: türetilmiş
  - Kaynak: [South Walton · Plaj erişimleri](https://www.visitsouthwalton.com/beach-bay-access-locations/) · erişim 2026-10-07 · çekim 1a195e2b27604fbb9443f7376434df6d · SHA-256 be258eac848e50cb3e05f6b678406e9056823873e9b5d86660aa899bc7c4ec06
  - Not: Topluluğun kendi misafirlerine açık özel erişimleri bu listede değildir.
  - Kullanım notu: 'Resmî rehber' ve 'ilçe alt bölüm verisi' eşlemeleri kaynak gösterilerek söylenebilir ("Walton County subdivision verisine göre …"). (M7)

### Veri bloğu: beach_features

Bu bloktaki satırların ortak bilgisi (2 satır):
- Kapsam: Rosemary Beach
- Etiket: kaynak gerçeği
- Kaynak: [South Walton · Plaj erişimleri](https://www.visitsouthwalton.com/beach-bay-access-locations/) · erişim 2026-10-07 · çekim 1a195e2b27604fbb9443f7376434df6d · SHA-256 be258eac848e50cb3e05f6b678406e9056823873e9b5d86660aa899bc7c4ec06
- Kullanım notu: İlçe erişim listesindeki olanaklar (ADA erişimi, plaj tekerlekli sandalyesi) listenin söylediği kadarıyla ve liste anılarak söylenir; listede olmayan bir olanak 'yok' anlamına gelmez. (M7)

- **K0003** · İlçe listesinde ADA olanağı (park, tuvalet ya da yürüyüş yolu) yazılı erişim sayısı — **0 erişim**
- **K0004** · İlçe listesinde 'Beach Wheelchairs Available' yazılı erişim sayısı — **0 erişim**

### Veri bloğu: references

Bu bloktaki satırların ortak bilgisi (2 satır):
- Kapsam: 30A
- Etiket: kaynak gerçeği
- Kullanım notu: Kaynak gösterilerek söylenebilir (ör. "Walton County'nin plaj yönetmeliğine göre …"). Kısa alıntı yalnız doğrulama içindir, videoda kullanılmaz. (M9)

- **K0005** · Visit South Walton'ın 2023 otopark rehberi Rosemary Beach'te halka açık plaj erişimi listelemiyor. — **halka açık plaj erişimi yok**
  - Kaynak: [Visit South Walton — Guide to Beach Parking and Transportation](https://www.visitsouthwalton.com/blog/guide-beach-parking-transportation/) · belge 2023-05-04 · erişim 2026-10-07 · satır erisim-rosemary-yok · SHA-256 68f06d985a954ce380820cbd3332960fa23886ab007a7122b6441b8fe5a85075
  - Kaynak satırının İngilizce ifadesi: Visit South Walton's 2023 parking guide lists no public beach access in Rosemary Beach.
  - Kaynaktan kısa alıntı: “ROSEMARY BEACH No Public Beach Access”
  - Not: Rehber 2023-05-04 tarihli; mahallede yalnız dükkân otoparkı bilgisi veriyor.
- **K0006** · Visit South Walton'ın 2023 otopark rehberine göre Rosemary Beach'te halka açık plaj erişimi yoktur; Barrett Square boyunca dükkân otoparkı ilk gelen alır esasıyla kullanılabilir. — **Barrett Square boyunca dükkân otoparkı (ilk gelen alır)**
  - Kaynak: [Visit South Walton — Guide to Beach Parking and Transportation](https://www.visitsouthwalton.com/blog/guide-beach-parking-transportation/) · belge 2023-05-04 · erişim 2026-10-07 · satır otopark-rosemary · SHA-256 68f06d985a954ce380820cbd3332960fa23886ab007a7122b6441b8fe5a85075
  - Kaynak satırının İngilizce ifadesi: Visit South Walton's 2023 parking guide says Rosemary Beach has no public beach access and that shop parking is available first-come, first-served along Barrett Square.
  - Kaynaktan kısa alıntı: “Shop parking available; first-come, first-served along Barrett Square.”
  - Not: GÖREV-07'de rosemarybeach.com (Rosemary Beach Cottage Rental Company) sayfalarında ziyaretçi otoparkı bilgisi bulunamamıştı. GÖREV-08 (8 Ekim 2026): şirketin 'Know Before You Go' sayfası da (g8-rosemary-know-before-you-go.html) yalnız kiracılara verilen park kartından söz ediyor; topluluk derneğinin (RBPOA) resmî bir park sayfası bulunamadı. Bu yüzden ziyaretçi bilgisi ilçe turizm dairesinin rehberinden; rehber 2023 tarihli, ücret veya süre sınırı vermiyor.

## Konaklama

**Soru:** Kaç ilan görünüyor, türü ve oda dağılımı ne, ay ay haftalık fiyat ne?


### Veri bloğu: lodging_inventory

Bu bloktaki satırların ortak bilgisi (26 satır):
- Kapsam: Rosemary Beach
- Etiket: kaynak gerçeği
- Kaynak: [South Walton · Konaklama (Book>Direct)](https://visitsouthwalton.bookdirect.net/) · erişim 2026-10-09 · çekim 5b5d0115f73f4edda3ef7003dfb99325 · SHA-256 924d7fb4df4a001299b30975299c6215d8dbb6027775bc4a06152841258e9b8b
- Kullanım notu: "Visit South Walton'ın resmî rezervasyon sayfasında <tarih>'te yapılan aramada, <pencere> için <mahalle>'de N ilan göründü" biçiminde, arama tarihi ve pencere söylenerek. "30A'da N ev var" veya "tam liste" denmez. (M10)

- **K0007** · Rosemary Beach · Kasım 2026 · 14–21 Kasım: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **163 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0008** · Rosemary Beach · Aralık 2026 · 12–19 Aralık: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **164 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0009** · Rosemary Beach · Ocak 2027 · 9–16 Ocak: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **164 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0010** · Rosemary Beach · Şubat 2027 · 13–20 Şubat: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **166 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0011** · Rosemary Beach · Mart 2027 · 13–20 Mart: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **166 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0012** · Rosemary Beach · Nisan 2027 · 10–17 Nisan: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **166 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0013** · Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **166 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0014** · Rosemary Beach · Haziran 2027 · 12–19 Haziran: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **166 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0015** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **166 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0016** · Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **166 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0017** · Rosemary Beach · Eylül 2027 · 11–18 Eylül: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **166 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0018** · Rosemary Beach · Ekim 2027 · 9–16 Ekim: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **166 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0019** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı — **166 ilan**
  - Not: 2026-10-09 tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.
- **K0020** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Beach Homes & Cottages' türündeki ilan sayısı — **117 ilan**
- **K0021** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Bed & Breakfast Inns' türündeki ilan sayısı — **1 ilan**
- **K0022** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Condominiums, Townhomes & Villas' türündeki ilan sayısı — **44 ilan**
- **K0023** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Hotels' türündeki ilan sayısı — **2 ilan**
- **K0024** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Rental Agencies' türündeki ilan sayısı — **2 ilan**
- **K0025** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'bilinmeyen kategori 9' türündeki ilan sayısı — **1 ilan**
- **K0026** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: stüdyo ilan sayısı — **0 ilan**
  - Örneklem: 154
- **K0027** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 1 yatak odalı ilan sayısı — **27 ilan**
  - Örneklem: 154
- **K0028** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2 yatak odalı ilan sayısı — **36 ilan**
  - Örneklem: 154
- **K0029** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 3 yatak odalı ilan sayısı — **43 ilan**
  - Örneklem: 154
- **K0030** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 4 yatak odalı ilan sayısı — **25 ilan**
  - Örneklem: 154
- **K0031** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 5 yatak odalı ilan sayısı — **16 ilan**
  - Örneklem: 154
- **K0032** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 6+ yatak odalı ilan sayısı — **7 ilan**
  - Örneklem: 154

### Veri bloğu: lodging_prices

Bu bloktaki satırların ortak bilgisi (12 satır):
- Kapsam: Rosemary Beach
- Etiket: bizim hesabımız
- Kaynak: [Kiralama şirketleri · Konaklama fiyatları](https://visitsouthwalton.bookdirect.net/?kaynak=kiralama-sirketleri) · erişim 2026-10-10 · çekim b85a4b4e414a48508224575a378f0697 · SHA-256 6256b7d42923177ea19fddadcf031687d6f0a51da92767dd1c4b456844fc750d
- Not: Kiralama şirketlerinin kendi sitelerinde 2026-10-09 tarihinde sorgulanan fiyatlar; toplam fiyat 10050/10694 fiyatta vergileri ve sitenin gösterdiği ücretleri içerir, kalanında sitenin toplamı kalemlerin toplamıyla doğrulanamadı.
- Kullanım notu: "<Mahalle>'de kiralama şirketlerinin kendi sitelerinde, <tarih> tarihinde <pencere> haftası için sorduğumuz <n> evin, sitenin gösterdiği vergiler ve ücretler dahil haftalık toplamının ortancası yaklaşık $X'ti"; kaç ilandan hesaplandığı ve çeyrekler söylenir. "<Mahalle>'de bir hafta $X tutar" denmez; ilan sayısı az hücrelerden mahalle karşılaştırması yapılmaz. (M11)

- **K0033** · Rosemary Beach · Kasım 2026 · 14–21 Kasım: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,491–$6,264) — **3,727 USD (7 gece)**
  - Örneklem: 48
- **K0034** · Rosemary Beach · Aralık 2026 · 12–19 Aralık: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,482–$5,655) — **3,487 USD (7 gece)**
  - Örneklem: 70
- **K0035** · Rosemary Beach · Ocak 2027 · 9–16 Ocak: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,512–$6,108) — **4,159 USD (7 gece)**
  - Örneklem: 67
- **K0036** · Rosemary Beach · Şubat 2027 · 13–20 Şubat: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,951–$6,543) — **4,090 USD (7 gece)**
  - Örneklem: 70
- **K0037** · Rosemary Beach · Mart 2027 · 13–20 Mart: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,014–$9,367) — **5,872 USD (7 gece)**
  - Örneklem: 82
- **K0038** · Rosemary Beach · Nisan 2027 · 10–17 Nisan: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,465–$7,174) — **4,685 USD (7 gece)**
  - Örneklem: 67
- **K0039** · Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,226–$8,732) — **5,369 USD (7 gece)**
  - Örneklem: 70
- **K0040** · Rosemary Beach · Haziran 2027 · 12–19 Haziran: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,804–$12,522) — **6,994 USD (7 gece)**
  - Örneklem: 89
- **K0041** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$12,028) — **7,223 USD (7 gece)**
  - Örneklem: 91
- **K0042** · Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,535–$8,704) — **4,929 USD (7 gece)**
  - Örneklem: 92
- **K0043** · Rosemary Beach · Eylül 2027 · 11–18 Eylül: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,355–$8,467) — **4,771 USD (7 gece)**
  - Örneklem: 87
- **K0044** · Rosemary Beach · Ekim 2027 · 9–16 Ekim: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$9,524) — **6,219 USD (7 gece)**
  - Örneklem: 58

### Veri bloğu: lodging_bedrooms

Bu bloktaki satırların ortak bilgisi (8 satır):
- Kapsam: Rosemary Beach
- Etiket: bizim hesabımız
- Kaynak: [Kiralama şirketleri · Konaklama fiyatları](https://visitsouthwalton.bookdirect.net/?kaynak=kiralama-sirketleri) · erişim 2026-10-10 · çekim b85a4b4e414a48508224575a378f0697 · SHA-256 6256b7d42923177ea19fddadcf031687d6f0a51da92767dd1c4b456844fc750d
- Not: Oda sayısı Book>Direct ilanından; 1–2 grubuna stüdyolar dahildir. Ortancalar 7 gecelik toplam fiyattandır.
- Kullanım notu: "<Mahalle>'de kiralama şirketlerinin kendi sitelerinde, <tarih> tarihinde <pencere> haftası için sorduğumuz <n> evin, sitenin gösterdiği vergiler ve ücretler dahil haftalık toplamının ortancası yaklaşık $X'ti"; kaç ilandan hesaplandığı ve çeyrekler söylenir. "<Mahalle>'de bir hafta $X tutar" denmez; ilan sayısı az hücrelerden mahalle karşılaştırması yapılmaz. (M11)

- **K0045** · Rosemary Beach · Ocak 2027 · 9–16 Ocak · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası — **2,793 USD (7 gece)**
  - Örneklem: 31
- **K0046** · Rosemary Beach · Ocak 2027 · 9–16 Ocak · 3 yatak odası: 7 gecelik toplam fiyatın ortancası — **4,752 USD (7 gece)**
  - Örneklem: 16
- **K0047** · Rosemary Beach · Ocak 2027 · 9–16 Ocak · 4 yatak odası: 7 gecelik toplam fiyatın ortancası — **5,956 USD (7 gece)**
  - Örneklem: 9
- **K0048** · Rosemary Beach · Ocak 2027 · 9–16 Ocak · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası — **8,640 USD (7 gece)**
  - Örneklem: 10
- **K0049** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası — **4,440 USD (7 gece)**
  - Örneklem: 40
- **K0050** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 3 yatak odası: 7 gecelik toplam fiyatın ortancası — **8,376 USD (7 gece)**
  - Örneklem: 24
- **K0051** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 4 yatak odası: 7 gecelik toplam fiyatın ortancası — **12,817 USD (7 gece)**
  - Örneklem: 16
- **K0052** · Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası — **15,287 USD (7 gece)**
  - Örneklem: 10

## Restoranlar

**Soru:** Mahallede hangi restoranlar var; seviye, rezervasyon, çocuk menüsü ve saatler ne?


### Veri bloğu: restaurants

Bu bloktaki satırların ortak bilgisi (16 satır):
- Kapsam: Rosemary Beach
- Kullanım notu: "İşletmenin kendi sitesindeki menüye göre (erişim tarihi) ana yemeklerin ortancası yaklaşık $X" gibi; fiyat seviyesi kullanılırsa "bizim sınıflamamıza göre" denir. "En iyi", "en popüler", "en ucuz" gibi sıralamalar ve sitede olmayan bilgi kullanılmaz; bulunamayan bir olanak için "yok" denmez. (M12)

- **K0053** · Rosemary Beach: Visit South Walton restoran dizininde bu mahalleye bağlı restoran sayısı — **12 restoran**
  - Etiket: kaynak gerçeği
  - Kaynak: [Restoranlar · İşletme siteleri](https://www.visitsouthwalton.com/listings/culinary-experiences/?kaynak=isletme-siteleri) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
- **K0054** · Rosemary Beach: fiyat seviyesi hesaplanabilen restoran sayısı ($ 0, $$ 0, $$$ 2, $$$$ 1) — **3 restoran**
  - Etiket: bizim hesabımız
  - Kaynak: [Restoranlar · İşletme siteleri](https://www.visitsouthwalton.com/listings/culinary-experiences/?kaynak=isletme-siteleri) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
  - Not: Fiyat seviyesi bizim sınıflamamızdır: işletmenin kendi sitesindeki en kapsamlı ana öğün menüsünde (akşam, yoksa öğle, yoksa genel, yoksa brunch, yoksa kahvaltı) ana yemek fiyatlarının ortancası $15 altı '$', $15–25 '$$', $25–40 '$$$', $40 ve üstü '$$$$'; 5'ten az ana yemek fiyatı varsa hesaplanmaz. Ek malzeme, ekstra ve yan ürünler ana yemek sayılmaz; tapas / küçük tabaklar ve kişi başı sabit fiyatlı menüler ayrı verilir.
- **K0055** · Rosemary Beach: sitesinde çevrimiçi rezervasyon bağlantısı bulunan restoran sayısı — **1 restoran**
  - Etiket: kaynak gerçeği
  - Kaynak: [Restoranlar · İşletme siteleri](https://www.visitsouthwalton.com/listings/culinary-experiences/?kaynak=isletme-siteleri) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
- **K0056** · Rosemary Beach: sitesinde çocuk menüsü yayımlayan restoran sayısı — **5 restoran**
  - Etiket: kaynak gerçeği
  - Kaynak: [Restoranlar · İşletme siteleri](https://www.visitsouthwalton.com/listings/culinary-experiences/?kaynak=isletme-siteleri) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
- **K0057** · Amavida Coffee in Rosemary Beach: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: 6:30am – 7:00pm · Open Daily
  - Etiket: kaynak gerçeği
  - Kaynak: [Restoranlar · İşletme siteleri](http://amavida.com) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
  - Not: ana yemek sunmuyor (kahve dükkânı)
- **K0058** · CK Feed & Supply Provisions & Gifts: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: Open Daily: 7:30am-9pm
  - Etiket: kaynak gerçeği
  - Kaynak: [Restoranlar · İşletme siteleri](http://cowgirlkitchen.com) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
  - Not: ana yemek sunmuyor (şarap ve provizyon dükkânı)
- **K0059** · Cowgirl Kitchen Restaurant & Bar: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: Open Daily: 7:30am-9pm
  - Etiket: kaynak gerçeği
  - Kaynak: [Restoranlar · İşletme siteleri](http://cowgirlkitchen.com) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
  - Not: işletmenin sitesinde Rosemary Beach'te bu adla restoran ya da menü yok
- **K0060** · Creative Crepes: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler sitede bulunamadı
  - Etiket: kaynak gerçeği
  - Kaynak: [Restoranlar · İşletme siteleri](https://www.facebook.com/CreativeCrepes/) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
  - Not: yalnız sosyal medya sayfası var (giriş gerekiyor)
- **K0061** · Edward's Fine Food & Wine: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: , Tu 17:00-21:00, We 17:00-21:00, Th 17:00-21:00, Fr 17:00-21:30, Sa 17:00-21:30, Su 17:00-21:00 — **35 USD (ana yemek ortancası)**
  - Etiket: bizim hesabımız · Örneklem: 8
  - Kaynak: [Restoranlar · İşletme siteleri](http://edwards30a.com) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
- **K0062** · Gallion's: seviye hesaplanmadı; çevrimiçi rezervasyon bağlantısı var; çocuk menüsü sitede bulunamadı; saatler: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday 09:00–22:00
  - Etiket: kaynak gerçeği
  - Kaynak: [Restoranlar · İşletme siteleri](http://gallions30a.com) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
  - Not: sitedeki menüde yemek fiyatları yazmıyor (yalnız ek malzeme fiyatları var)
- **K0063** · Havana Beach Bar & Grill: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: 8 AM–2 PM
  - Etiket: kaynak gerçeği
  - Kaynak: [Restoranlar · İşletme siteleri](http://www.havanabeachbar.com) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
  - Not: menü fiyatları sayfanın düz HTML'inde yok (JavaScript ile çiziliyor olabilir); tarayıcı yalnız engelde kullanıldığı için okunmadı
- **K0064** · La Crema-Tapas and Chocolate: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: Mo 11:00-21:00, Tu 11:00-21:00, We 11:00-21:00, Th 11:00-21:00, Fr 11:00-22:00, Sa 11:00-22:00, Su 11:00-21:00 — **25 USD (ana yemek ortancası)**
  - Etiket: bizim hesabımız · Örneklem: 5
  - Kaynak: [Restoranlar · İşletme siteleri](http://www.lacrematapas.com) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
- **K0065** · Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday | 3PM–10PM · Wednesday–Sunday | 10AM–10PM · Brunch | Wednesday–Sunday, 10AM–1:45PM · Happy Hour | Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. — **49 USD (ana yemek ortancası)**
  - Etiket: bizim hesabımız · Örneklem: 3
  - Kaynak: [Restoranlar · İşletme siteleri](http://www.rooftop30a.com) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
  - Not: 5'ten az fiyatlı ana yemek (3)
- **K0066** · Restaurant Paradis: seviye $$$$ (bizim sınıflamamız); telefonla rezervasyon; çocuk menüsü sitede var; saatler: Sunday, Monday, Tuesday, Wednesday, Thursday 17:00–21:00 · Friday, Saturday 17:00–22:00 — **47 USD (ana yemek ortancası)**
  - Etiket: bizim hesabımız · Örneklem: 9
  - Kaynak: [Restoranlar · İşletme siteleri](http://restaurantparadis.com) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
- **K0067** · Summer Kitchen Café: seviye hesaplanmadı; rezervasyon almıyor; çocuk menüsü sitede bulunamadı; saatler: OPEN DAILY FROM 730AM - 3PM
  - Etiket: kaynak gerçeği
  - Kaynak: [Restoranlar · İşletme siteleri](http://www.theskcafe.com) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
  - Not: menü fiyatları sayfanın düz HTML'inde yok (JavaScript ile çiziliyor olabilir); tarayıcı yalnız engelde kullanıldığı için okunmadı
- **K0068** · The Courtyard at Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday | 3PM–10PM · Wednesday–Sunday | 10AM–10PM · Brunch | Wednesday–Sunday, 10AM–1:45PM · Happy Hour | Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. — **49 USD (ana yemek ortancası)**
  - Etiket: bizim hesabımız · Örneklem: 3
  - Kaynak: [Restoranlar · İşletme siteleri](https://rooftop30a.com/the-courtyard) · erişim 2026-10-09 · çekim 1f1155b10aec44bdab98736e56892cc4 · SHA-256 5033dfeaa5becf2fa2876ec80f736e0cf325beb25f912094ed62ddd8b6f8440d
  - Not: 5'ten az fiyatlı ana yemek (3)

## Günlük ihtiyaç mesafeleri

**Soru:** Market, eczane, acil sağlık, bisiklet kiralama ve plaj erişimi kuş uçuşu ne kadar uzak?


### Veri bloğu: daily_needs

Bu bloktaki satırların ortak bilgisi (8 satır):
- Kapsam: Rosemary Beach
- Etiket: bizim hesabımız
- Kaynak: [OpenStreetMap · Günlük ihtiyaç noktaları](https://www.openstreetmap.org/?kaynak=gunluk-ihtiyac) · erişim 2026-10-10 · çekim 080b04f1048c42388764fbe901543528 · SHA-256 5e2b75419121237c47a589d6a4c6a3906fb4813a6575ffc371d91f5f9f07a01e
- Kullanım notu: "OpenStreetMap'e göre, <mahalle>'deki ilanların ortancası en yakın <yer>'e kuş uçuşu yaklaşık X mil" gibi. "Yürüme mesafesi" ya da yol ve süre iddiası kullanılmaz. (M13)

- **K0069** · Rosemary Beach: ilanların en yakın büyük süpermarket noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) — **1.36 mil** (2.18 km)
  - Örneklem: 166
  - Not: OpenStreetMap'e göre, kuş uçuşu mesafe (yol üzerinden hesaplanmadı; 'yürüme mesafesi' denmez). Mahalle, ilanın Book>Direct konum filtresinden gelir. Ortanca ve 1 mil içindeki ilan payı bizim hesabımızdır.
- **K0070** · Rosemary Beach: ilanların en yakın yerel ve gurme market noktasına kuş uçuşu mesafe ortancası (ilanların %91'i 1 mil içinde) — **0.25 mil** (0.40 km)
  - Örneklem: 166
  - Not: OpenStreetMap'e göre, kuş uçuşu mesafe (yol üzerinden hesaplanmadı; 'yürüme mesafesi' denmez). Mahalle, ilanın Book>Direct konum filtresinden gelir. Ortanca ve 1 mil içindeki ilan payı bizim hesabımızdır.
- **K0071** · Rosemary Beach: ilanların en yakın küçük market noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) — **2.77 mil** (4.45 km)
  - Örneklem: 166
  - Not: OpenStreetMap'e göre, kuş uçuşu mesafe (yol üzerinden hesaplanmadı; 'yürüme mesafesi' denmez). Mahalle, ilanın Book>Direct konum filtresinden gelir. Ortanca ve 1 mil içindeki ilan payı bizim hesabımızdır.
- **K0072** · Rosemary Beach: ilanların en yakın eczane noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) — **2.71 mil** (4.36 km)
  - Örneklem: 166
  - Not: OpenStreetMap'e göre, kuş uçuşu mesafe (yol üzerinden hesaplanmadı; 'yürüme mesafesi' denmez). Mahalle, ilanın Book>Direct konum filtresinden gelir. Ortanca ve 1 mil içindeki ilan payı bizim hesabımızdır.
- **K0073** · Rosemary Beach: ilanların en yakın acil servis noktasına kuş uçuşu mesafe ortancası (ilanların %0'i 1 mil içinde) — **13.57 mil** (21.83 km)
  - Örneklem: 166
  - Not: OpenStreetMap'e göre, kuş uçuşu mesafe (yol üzerinden hesaplanmadı; 'yürüme mesafesi' denmez). Mahalle, ilanın Book>Direct konum filtresinden gelir. Ortanca ve 1 mil içindeki ilan payı bizim hesabımızdır.
- **K0074** · Rosemary Beach: ilanların en yakın acil bakım (urgent care) noktasına kuş uçuşu mesafe ortancası (ilanların %36'i 1 mil içinde) — **1.05 mil** (1.69 km)
  - Örneklem: 166
  - Not: OpenStreetMap'e göre, kuş uçuşu mesafe (yol üzerinden hesaplanmadı; 'yürüme mesafesi' denmez). Mahalle, ilanın Book>Direct konum filtresinden gelir. Ortanca ve 1 mil içindeki ilan payı bizim hesabımızdır.
- **K0075** · Rosemary Beach: ilanların en yakın bisiklet kiralama noktasına kuş uçuşu mesafe ortancası (ilanların %91'i 1 mil içinde) — **0.3 mil** (0.48 km)
  - Örneklem: 166
  - Not: OpenStreetMap'e göre, kuş uçuşu mesafe (yol üzerinden hesaplanmadı; 'yürüme mesafesi' denmez). Mahalle, ilanın Book>Direct konum filtresinden gelir. Ortanca ve 1 mil içindeki ilan payı bizim hesabımızdır.
- **K0076** · Rosemary Beach: ilanların en yakın halka açık plaj erişimi (ilçe listesi) noktasına kuş uçuşu mesafe ortancası (ilanların %93'i 1 mil içinde) — **0.37 mil** (0.59 km)
  - Örneklem: 166
  - Not: OpenStreetMap'e göre, kuş uçuşu mesafe (yol üzerinden hesaplanmadı; 'yürüme mesafesi' denmez). Mahalle, ilanın Book>Direct konum filtresinden gelir. Ortanca ve 1 mil içindeki ilan payı bizim hesabımızdır. Plaj erişimi ölçüsü yalnız ilçenin halka açık erişim listesine göredir; Seaside, WaterColor, Alys Beach, Rosemary Beach gibi toplulukların kendi misafirlerine açık özel erişimleri dahil değildir.

## Mahalleye özgü referanslar

**Soru:** Otopark, servis, kurallar ve tarih hakkında bu mahalleyi anan kaynaklı satırlar neler?


### Veri bloğu: references

- **K0077** · DPZ, Rosemary Beach'i 1995'te Paul Borden, Leucadia National Corp. ve Patrick Bienvenue için tasarlanmış olarak listeliyor. — **1995**
  - Kapsam: 30A · Etiket: kaynak gerçeği
  - Kaynak: [DPZ CoDesign — Rosemary Beach (project page)](https://www.dpz.com/projects/rosemary-beach/) · erişim 2026-10-10 · satır tarih-rosemary-dpz · SHA-256 1d93f691a357b9371bde889b3b2810b85ed8595743fb715918d8f264efa1975d
  - Kaynak satırının İngilizce ifadesi: DPZ lists Rosemary Beach as designed in 1995 for Paul Borden, Leucadia National Corp. and Patrick Bienvenue.
  - Kaynaktan kısa alıntı: “calendar_month 1995 Designed”
  - Kullanım notu: Kaynak gösterilerek söylenebilir (ör. "Walton County'nin plaj yönetmeliğine göre …"). Kısa alıntı yalnız doğrulama içindir, videoda kullanılmaz. (M9)

## Etkinlikler

**Soru:** Mahallede her yıl tekrarlanan etkinlikler neler?


### Veri bloğu: references

Bu bloktaki satırların ortak bilgisi (2 satır):
- Kapsam: 30A
- Etiket: kaynak gerçeği
- Kullanım notu: Kaynak gösterilerek söylenebilir (ör. "Walton County'nin plaj yönetmeliğine göre …"). Kısa alıntı yalnız doğrulama içindir, videoda kullanılmaz. (M9)

- **K0078** · Rosemary Beach'teki yemek ve şarap etkinliği Rosemary Beach Uncorked 15. yılını 14 Kasım 2026'da kutluyor. — **Kasım (2026: 14 Kasım)**
  - Kaynak: [Rosemary Beach — Rosemary Beach Uncorked](https://rosemarybeach.com/events/rosemary-beach-uncorked-2/) · erişim 2026-10-10 · satır etkinlik-rosemary-uncorked · SHA-256 675278cff6dfbbb7f7c15a8ca8d279d307d04ebf87c2b07e30d868f037d4227b
  - Kaynak satırının İngilizce ifadesi: Rosemary Beach Uncorked, a food and wine event in Rosemary Beach, celebrates its 15th year on 14 November 2026.
  - Kaynaktan kısa alıntı: “Rosemary Beach Uncorked™ will celebrate its 15th year with the 2026 event set to take place Saturday, November 14, 2026”
- **K0079** · 30A 10K Thanksgiving Day Races Şükran Günü'nde Rosemary Beach'te yapılır; 15. yarışlar 26 Kasım 2026'da. — **Şükran Günü (2026: 26 Kasım)**
  - Kaynak: [30A 10K Thanksgiving Day Races — official site](https://www.30a10k.com/) · erişim 2026-10-10 · satır etkinlik-30a-10k · SHA-256 9efeef26dbd73cc805e188ac166d5af773a1a30148a1db5b00c7eae738bb6ce8
  - Kaynak satırının İngilizce ifadesi: The 30A 10K Thanksgiving Day Races are held in Rosemary Beach on Thanksgiving Day; the 15th annual races are on 26 November 2026.
  - Kaynaktan kısa alıntı: “Welcome to our 15th Annual 30A 10K Races!”
  - Not: Sayfa adresi Rosemary Beach, FL 32461 veriyor; parkur ayrıntısı bu işte okunmadı.

## Hava ve sezon (30A geneli)

**Soru:** Hava, deniz suyu ve sezon deseni ne? (Bu bölüm mahalleye özgü değildir; 30A genelinden ve öyle etiketli.)


### Veri bloğu: climate_months

Bu bloktaki satırların ortak bilgisi (60 satır):
- Kapsam: Destin–Fort Walton Beach Havalimanı (USW00053853), 30A kıyı koridoruna 12.7 mil; 1991–2020
- Etiket: kaynak gerçeği
- Kaynak: [NOAA NCEI · İklim normalleri 1991–2020](https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals) · erişim 2026-10-07 · çekim 80f41ce6a8114392874747a108182cf7 · SHA-256 c6b93437e3b259fc76c624aef6313311e70b93afb6fc66e0d5d0376184ebced6
- Kullanım notu: Bu değer destinasyonun içinden ölçüm değildir; "30A'nın iklimi" denmez, "30A'ya en yakın kıyı istasyonu Destin'in 1991–2020 normali" denir. °C/mm dönüşümleri bizim hesabımızdır. (M8)

- **K0080** · Ocak: ortalama en yüksek sıcaklık — **63.1 °F** (17.3 °C)
  - Örneklem: 19
  - Not: NCEI tamlık işareti: R.
- **K0081** · Şubat: ortalama en yüksek sıcaklık — **65.8 °F** (18.8 °C)
  - Örneklem: 20
  - Not: NCEI tamlık işareti: R.
- **K0082** · Mart: ortalama en yüksek sıcaklık — **70.7 °F** (21.5 °C)
  - Örneklem: 20
  - Not: NCEI tamlık işareti: R.
- **K0083** · Nisan: ortalama en yüksek sıcaklık — **76.2 °F** (24.6 °C)
  - Örneklem: 20
  - Not: NCEI tamlık işareti: R.
- **K0084** · Mayıs: ortalama en yüksek sıcaklık — **83.5 °F** (28.6 °C)
  - Örneklem: 19
  - Not: NCEI tamlık işareti: R.
- **K0085** · Haziran: ortalama en yüksek sıcaklık — **88.9 °F** (31.6 °C)
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0086** · Temmuz: ortalama en yüksek sıcaklık — **90.9 °F** (32.7 °C)
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0087** · Ağustos: ortalama en yüksek sıcaklık — **90.6 °F** (32.6 °C)
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0088** · Eylül: ortalama en yüksek sıcaklık — **88.5 °F** (31.4 °C)
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0089** · Ekim: ortalama en yüksek sıcaklık — **80.9 °F** (27.2 °C)
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0090** · Kasım: ortalama en yüksek sıcaklık — **72.1 °F** (22.3 °C)
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0091** · Aralık: ortalama en yüksek sıcaklık — **65.6 °F** (18.7 °C)
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0092** · Ocak: ortalama en düşük sıcaklık — **45.3 °F** (7.4 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0093** · Şubat: ortalama en düşük sıcaklık — **47.9 °F** (8.8 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0094** · Mart: ortalama en düşük sıcaklık — **53.6 °F** (12.0 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0095** · Nisan: ortalama en düşük sıcaklık — **60.1 °F** (15.6 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0096** · Mayıs: ortalama en düşük sıcaklık — **68 °F** (20.0 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0097** · Haziran: ortalama en düşük sıcaklık — **74.1 °F** (23.4 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0098** · Temmuz: ortalama en düşük sıcaklık — **76.2 °F** (24.6 °C)
  - Örneklem: 21
  - Not: NCEI tamlık işareti: R.
- **K0099** · Ağustos: ortalama en düşük sıcaklık — **75.8 °F** (24.3 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0100** · Eylül: ortalama en düşük sıcaklık — **72.4 °F** (22.4 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0101** · Ekim: ortalama en düşük sıcaklık — **63.2 °F** (17.3 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0102** · Kasım: ortalama en düşük sıcaklık — **53 °F** (11.7 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0103** · Aralık: ortalama en düşük sıcaklık — **47.5 °F** (8.6 °C)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0104** · Ocak: ortalama yağış — **4.52 inç** (115 mm)
  - Örneklem: 21
  - Not: NCEI tamlık işareti: R.
- **K0105** · Şubat: ortalama yağış — **4.96 inç** (126 mm)
  - Örneklem: 21
  - Not: NCEI tamlık işareti: R.
- **K0106** · Mart: ortalama yağış — **4.7 inç** (119 mm)
  - Örneklem: 21
  - Not: NCEI tamlık işareti: R.
- **K0107** · Nisan: ortalama yağış — **4.55 inç** (116 mm)
  - Örneklem: 23
  - Not: NCEI tamlık işareti: R.
- **K0108** · Mayıs: ortalama yağış — **3.22 inç** (82 mm)
  - Örneklem: 21
  - Not: NCEI tamlık işareti: R.
- **K0109** · Haziran: ortalama yağış — **4.7 inç** (119 mm)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0110** · Temmuz: ortalama yağış — **5.77 inç** (147 mm)
  - Örneklem: 20
  - Not: NCEI tamlık işareti: R.
- **K0111** · Ağustos: ortalama yağış — **6.08 inç** (154 mm)
  - Örneklem: 19
  - Not: NCEI tamlık işareti: R.
- **K0112** · Eylül: ortalama yağış — **5.18 inç** (132 mm)
  - Örneklem: 16
  - Not: NCEI tamlık işareti: R.
- **K0113** · Ekim: ortalama yağış — **2.82 inç** (72 mm)
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0114** · Kasım: ortalama yağış — **4.13 inç** (105 mm)
  - Örneklem: 22
  - Not: NCEI tamlık işareti: R.
- **K0115** · Aralık: ortalama yağış — **4.72 inç** (120 mm)
  - Örneklem: 21
  - Not: NCEI tamlık işareti: R.
- **K0116** · Ocak: 0,10 inç ve üstü yağışlı gün ortalaması — **5.6 gün**
  - Örneklem: 22
  - Not: NCEI tamlık işareti: P.
- **K0117** · Şubat: 0,10 inç ve üstü yağışlı gün ortalaması — **5.3 gün**
  - Örneklem: 22
  - Not: NCEI tamlık işareti: P.
- **K0118** · Mart: 0,10 inç ve üstü yağışlı gün ortalaması — **5.2 gün**
  - Örneklem: 22
  - Not: NCEI tamlık işareti: P.
- **K0119** · Nisan: 0,10 inç ve üstü yağışlı gün ortalaması — **4 gün**
  - Örneklem: 23
  - Not: NCEI tamlık işareti: P.
- **K0120** · Mayıs: 0,10 inç ve üstü yağışlı gün ortalaması — **3.7 gün**
  - Örneklem: 23
  - Not: NCEI tamlık işareti: P.
- **K0121** · Haziran: 0,10 inç ve üstü yağışlı gün ortalaması — **6.1 gün**
  - Örneklem: 23
  - Not: NCEI tamlık işareti: P.
- **K0122** · Temmuz: 0,10 inç ve üstü yağışlı gün ortalaması — **7.2 gün**
  - Örneklem: 23
  - Not: NCEI tamlık işareti: P.
- **K0123** · Ağustos: 0,10 inç ve üstü yağışlı gün ortalaması — **8.1 gün**
  - Örneklem: 23
  - Not: NCEI tamlık işareti: P.
- **K0124** · Eylül: 0,10 inç ve üstü yağışlı gün ortalaması — **5.3 gün**
  - Örneklem: 23
  - Not: NCEI tamlık işareti: P.
- **K0125** · Ekim: 0,10 inç ve üstü yağışlı gün ortalaması — **3.5 gün**
  - Örneklem: 23
  - Not: NCEI tamlık işareti: P.
- **K0126** · Kasım: 0,10 inç ve üstü yağışlı gün ortalaması — **4.3 gün**
  - Örneklem: 23
  - Not: NCEI tamlık işareti: P.
- **K0127** · Aralık: 0,10 inç ve üstü yağışlı gün ortalaması — **6.5 gün**
  - Örneklem: 23
  - Not: NCEI tamlık işareti: P.
- **K0128** · Ocak: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **0 gün**
  - Örneklem: 19
  - Not: NCEI tamlık işareti: R.
- **K0129** · Şubat: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **0 gün**
  - Örneklem: 20
  - Not: NCEI tamlık işareti: R.
- **K0130** · Mart: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **0 gün**
  - Örneklem: 20
  - Not: NCEI tamlık işareti: R.
- **K0131** · Nisan: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **0 gün**
  - Örneklem: 20
  - Not: NCEI tamlık işareti: R.
- **K0132** · Mayıs: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **1.1 gün**
  - Örneklem: 19
  - Not: NCEI tamlık işareti: R.
- **K0133** · Haziran: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **7.8 gün**
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0134** · Temmuz: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **14.9 gün**
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0135** · Ağustos: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **16.9 gün**
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0136** · Eylül: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **8.7 gün**
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0137** · Ekim: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **0.9 gün**
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0138** · Kasım: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **0 gün**
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.
- **K0139** · Aralık: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması — **0 gün**
  - Örneklem: 18
  - Not: NCEI tamlık işareti: R.

### Veri bloğu: sea_water

Bu bloktaki satırların ortak bilgisi (12 satır):
- Etiket: bizim hesabımız
- Kaynak: [NOAA NDBC · Deniz suyu sıcaklığı](https://www.ndbc.noaa.gov/) · erişim 2026-10-07 · çekim a8cbe865958f4975bca01e5a27671c38 · SHA-256 f9d252d6673e98c4f6a3eea333e827e59f1fed750d3a17bdbb37d68412f954c5
- Kullanım notu: PCBF1 (Panama City Beach) ölçümlerinden hesaplanan aylık ortalama, kullanılan yıllar söylenerek; NOAA verisinden bizim hesabımız. İstasyonun sensöründe ölçülen su sıcaklığıdır; 30A kıyısındaki deniz suyu sıcaklığıyla aynı olduğu doğrulanmadı. (M8)

- **K0140** · Ocak: aylık ortalama deniz suyu sıcaklığı — **60.2 °F** (15.7 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2006–2025 · Örneklem: 15
  - Not: 15 yılın ortalaması; 0 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0141** · Şubat: aylık ortalama deniz suyu sıcaklığı — **60.6 °F** (15.9 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2005–2025 · Örneklem: 14
  - Not: 14 yılın ortalaması; 1 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0142** · Mart: aylık ortalama deniz suyu sıcaklığı — **65.7 °F** (18.7 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2005–2025 · Örneklem: 14
  - Not: 14 yılın ortalaması; 1 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0143** · Nisan: aylık ortalama deniz suyu sıcaklığı — **70.7 °F** (21.5 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2005–2025 · Örneklem: 15
  - Not: 15 yılın ortalaması; 0 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0144** · Mayıs: aylık ortalama deniz suyu sıcaklığı — **77.2 °F** (25.1 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2005–2025 · Örneklem: 15
  - Not: 15 yılın ortalaması; 0 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0145** · Haziran: aylık ortalama deniz suyu sıcaklığı — **82.3 °F** (28.0 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2005–2025 · Örneklem: 15
  - Not: 15 yılın ortalaması; 0 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0146** · Temmuz: aylık ortalama deniz suyu sıcaklığı — **84.3 °F** (29.0 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2005–2025 · Örneklem: 13
  - Not: 13 yılın ortalaması; 2 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0147** · Ağustos: aylık ortalama deniz suyu sıcaklığı — **85.8 °F** (29.9 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2005–2025 · Örneklem: 14
  - Not: 14 yılın ortalaması; 0 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0148** · Eylül: aylık ortalama deniz suyu sıcaklığı — **84.2 °F** (29.0 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2006–2025 · Örneklem: 13
  - Not: 13 yılın ortalaması; 2 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0149** · Ekim: aylık ortalama deniz suyu sıcaklığı — **78.5 °F** (25.9 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2005–2025 · Örneklem: 15
  - Not: 15 yılın ortalaması; 1 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0150** · Kasım: aylık ortalama deniz suyu sıcaklığı — **70.3 °F** (21.3 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2005–2025 · Örneklem: 16
  - Not: 16 yılın ortalaması; 0 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.
- **K0151** · Aralık: aylık ortalama deniz suyu sıcaklığı — **63.8 °F** (17.7 °C)
  - Kapsam: Panama City Beach (NOS 8729210) (PCBF1), 30A kıyı koridoruna 8.0 mil; 2005–2025 · Örneklem: 16
  - Not: 16 yılın ortalaması; 0 yıl-ay yetersiz gün sayısı nedeniyle dışarıda.

### Veri bloğu: tdt_season

Bu bloktaki satırların ortak bilgisi (12 satır):
- Kapsam: South Walton turist vergisi bölgesi; FY2021–FY2025 mali yılları
- Etiket: bizim hesabımız
- Kaynak: [Walton County Clerk — SW TDT Collections History with Monthly FYTD Comparisons (çalışma kitabı)](https://www.waltoncountyfltourism.com/userfiles/SW_TDT_Collections_History_with_Monthly_FYTD_Comparisons.xlsx) · erişim 2026-10-07 · SHA-256 0b191d85e519e1371b055e93937490120a2898e6d8358f60962fb16932b1cb03
- Not: Ay, Clerk tablosundaki dönem ayıdır (tahsilat bir sonraki ay alınır); %2 payından hesaplandı.
- Kullanım notu: Tutar o dönemin vergi oranıyla toplam tahsilattır; yıllar arası karşılaştırma için %2 payı kullanılır. Videoda tek ay rakamı söylenecekse kaynak belge birlikte anılmalı. (M9)

- **K0152** · Ekim: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **6.5 %**
  - Örneklem: 5
- **K0153** · Kasım: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **3 %**
  - Örneklem: 5
- **K0154** · Aralık: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **2.6 %**
  - Örneklem: 5
- **K0155** · Ocak: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **2.1 %**
  - Örneklem: 5
- **K0156** · Şubat: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **2.4 %**
  - Örneklem: 5
- **K0157** · Mart: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **8.5 %**
  - Örneklem: 5
- **K0158** · Nisan: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **8.6 %**
  - Örneklem: 5
- **K0159** · Mayıs: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **10.6 %**
  - Örneklem: 5
- **K0160** · Haziran: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **18.3 %**
  - Örneklem: 5
- **K0161** · Temmuz: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **20 %**
  - Örneklem: 5
- **K0162** · Ağustos: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **10.2 %**
  - Örneklem: 5
- **K0163** · Eylül: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) — **7.1 %**
  - Örneklem: 5

### Veri bloğu: storms

Bu bloktaki satırların ortak bilgisi (11 satır):
- Kapsam: 30A kıyı koridoru, 50 deniz mili (93 km); 1991–2025
- Etiket: bizim hesabımız
- Kaynak: [NOAA NHC · HURDAT2 kasırga izleri](https://www.nhc.noaa.gov/data/) · erişim 2026-10-07 · çekim 4f23d0a272f14bb7a44bb40b26cb55a0 · SHA-256 c8e6dc3499d1b8ab6aea6f70826686831a36d89d48102bb8c4fdec19f9e78d3d
- Kullanım notu: Videoda kasırga rakamları 1991–2025 dönemiyle verilir ve dönem açıkça söylenir; sayım NOAA HURDAT2 verisinden bizim hesabımızdır. (M8)

- **K0164** · Bu daire içinde kasırga gücünde rüzgâra ulaşan fırtına sayısı — **5 fırtına**
- **K0165** · Bu daire içinde en az tropikal fırtına gücüne ulaşan fırtına sayısı — **13 fırtına**
- **K0166** · Temmuz: daireye ilk girişi bu ayda olan kasırga gücündeki fırtına sayısı — **1 fırtına**
- **K0167** · Ağustos: daireye ilk girişi bu ayda olan kasırga gücündeki fırtına sayısı — **1 fırtına**
- **K0168** · Eylül: daireye ilk girişi bu ayda olan kasırga gücündeki fırtına sayısı — **1 fırtına**
- **K0169** · Ekim: daireye ilk girişi bu ayda olan kasırga gücündeki fırtına sayısı — **2 fırtına**
- **K0170** · Erin (1995): koridora en yakın geçiş — **35.1 deniz mili** (65.0 km)
  - Not: Daire içindeki en yüksek rüzgâr 85 knot; sınıf kasırga.
- **K0171** · Opal (1995): koridora en yakın geçiş — **39.7 deniz mili** (73.4 km)
  - Not: Daire içindeki en yüksek rüzgâr 100 knot; sınıf büyük kasırga.
- **K0172** · Earl (1998): koridora en yakın geçiş — **18.2 deniz mili** (33.8 km)
  - Not: Daire içindeki en yüksek rüzgâr 76 knot; sınıf kasırga.
- **K0173** · Dennis (2005): koridora en yakın geçiş — **40.6 deniz mili** (75.1 km)
  - Not: Daire içindeki en yüksek rüzgâr 111 knot; sınıf büyük kasırga.
- **K0174** · Michael (2018): koridora en yakın geçiş — **30.5 deniz mili** (56.4 km)
  - Not: Daire içindeki en yüksek rüzgâr 140 knot; sınıf büyük kasırga.

## Sayı kontrol listesi

| İfade | Değer | Birim | Kanıt |
|---|---|---|---|
| Rosemary Beach: Visit South Walton mahalle dizininde 30A mahallesi olarak listeleniyor; kaynağın etiketleri: Architecture, Arts & Culture, Family, Foodie Favorite, Music & Nightlife, Romance, Shopping & Spa, Walkable | 30 |  | K0001 |
| Rosemary Beach: ilçenin halka açık erişim listesinde bu mahalleye eşlenen erişim yok | 0 | erişim | K0002 |
| İlçe listesinde ADA olanağı (park, tuvalet ya da yürüyüş yolu) yazılı erişim sayısı | 0 | erişim | K0003 |
| İlçe listesinde 'Beach Wheelchairs Available' yazılı erişim sayısı | 0 | erişim | K0004 |
| Visit South Walton'ın 2023 otopark rehberi Rosemary Beach'te halka açık plaj erişimi listelemiyor. | 2023 |  | K0005 |
| Visit South Walton'ın 2023 otopark rehberine göre Rosemary Beach'te halka açık plaj erişimi yoktur; Barrett Square boyunca dükkân otoparkı ilk gelen alır esasıyla kullanılabilir. | 2023 |  | K0006 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 163 | ilan | K0007 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026 | ilan | K0007 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 14 | ilan | K0007 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 21 | ilan | K0007 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0007 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 164 | ilan | K0008 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026 | ilan | K0008 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 12 | ilan | K0008 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 19 | ilan | K0008 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0008 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 164 | ilan | K0009 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0009 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 9 | ilan | K0009 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 16 | ilan | K0009 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0009 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 166 | ilan | K0010 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0010 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 13 | ilan | K0010 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 20 | ilan | K0010 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0010 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 166 | ilan | K0011 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0011 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 13 | ilan | K0011 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 20 | ilan | K0011 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0011 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 166 | ilan | K0012 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0012 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 10 | ilan | K0012 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 17 | ilan | K0012 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0012 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 166 | ilan | K0013 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0013 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 15 | ilan | K0013 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 22 | ilan | K0013 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0013 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 166 | ilan | K0014 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0014 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 12 | ilan | K0014 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 19 | ilan | K0014 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0014 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 166 | ilan | K0015 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0015 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 10 | ilan | K0015 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 17 | ilan | K0015 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0015 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 166 | ilan | K0016 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0016 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 14 | ilan | K0016 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 21 | ilan | K0016 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0016 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 166 | ilan | K0017 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0017 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 11 | ilan | K0017 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 18 | ilan | K0017 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0017 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 166 | ilan | K0018 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0018 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 9 | ilan | K0018 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 16 | ilan | K0018 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0018 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 166 | ilan | K0019 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2027 | ilan | K0019 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 10 | ilan | K0019 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 17 | ilan | K0019 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2026-10-09 tarihli Book>Direct aramasında görünen ilan sayısı | 2026-10-09 | ilan | K0019 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Beach Homes & Cottages' türündeki ilan sayısı | 117 | ilan | K0020 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Beach Homes & Cottages' türündeki ilan sayısı | 2027 | ilan | K0020 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Beach Homes & Cottages' türündeki ilan sayısı | 10 | ilan | K0020 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Beach Homes & Cottages' türündeki ilan sayısı | 17 | ilan | K0020 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Bed & Breakfast Inns' türündeki ilan sayısı | 1 | ilan | K0021 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Bed & Breakfast Inns' türündeki ilan sayısı | 2027 | ilan | K0021 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Bed & Breakfast Inns' türündeki ilan sayısı | 10 | ilan | K0021 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Bed & Breakfast Inns' türündeki ilan sayısı | 17 | ilan | K0021 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Condominiums, Townhomes & Villas' türündeki ilan sayısı | 44 | ilan | K0022 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Condominiums, Townhomes & Villas' türündeki ilan sayısı | 2027 | ilan | K0022 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Condominiums, Townhomes & Villas' türündeki ilan sayısı | 10 | ilan | K0022 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Condominiums, Townhomes & Villas' türündeki ilan sayısı | 17 | ilan | K0022 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Hotels' türündeki ilan sayısı | 2 | ilan | K0023 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Hotels' türündeki ilan sayısı | 2027 | ilan | K0023 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Hotels' türündeki ilan sayısı | 10 | ilan | K0023 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Hotels' türündeki ilan sayısı | 17 | ilan | K0023 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Rental Agencies' türündeki ilan sayısı | 2 | ilan | K0024 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Rental Agencies' türündeki ilan sayısı | 2027 | ilan | K0024 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Rental Agencies' türündeki ilan sayısı | 10 | ilan | K0024 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'Rental Agencies' türündeki ilan sayısı | 17 | ilan | K0024 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'bilinmeyen kategori 9' türündeki ilan sayısı | 1 | ilan | K0025 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'bilinmeyen kategori 9' türündeki ilan sayısı | 2027 | ilan | K0025 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'bilinmeyen kategori 9' türündeki ilan sayısı | 10 | ilan | K0025 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'bilinmeyen kategori 9' türündeki ilan sayısı | 17 | ilan | K0025 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 'bilinmeyen kategori 9' türündeki ilan sayısı | 9 | ilan | K0025 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: stüdyo ilan sayısı | 0 | ilan | K0026 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: stüdyo ilan sayısı | 2027 | ilan | K0026 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: stüdyo ilan sayısı | 10 | ilan | K0026 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: stüdyo ilan sayısı | 17 | ilan | K0026 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 1 yatak odalı ilan sayısı | 27 | ilan | K0027 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 1 yatak odalı ilan sayısı | 2027 | ilan | K0027 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 1 yatak odalı ilan sayısı | 10 | ilan | K0027 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 1 yatak odalı ilan sayısı | 17 | ilan | K0027 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 1 yatak odalı ilan sayısı | 1 | ilan | K0027 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2 yatak odalı ilan sayısı | 36 | ilan | K0028 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2 yatak odalı ilan sayısı | 2027 | ilan | K0028 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2 yatak odalı ilan sayısı | 10 | ilan | K0028 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2 yatak odalı ilan sayısı | 17 | ilan | K0028 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 2 yatak odalı ilan sayısı | 2 | ilan | K0028 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 3 yatak odalı ilan sayısı | 43 | ilan | K0029 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 3 yatak odalı ilan sayısı | 2027 | ilan | K0029 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 3 yatak odalı ilan sayısı | 10 | ilan | K0029 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 3 yatak odalı ilan sayısı | 17 | ilan | K0029 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 3 yatak odalı ilan sayısı | 3 | ilan | K0029 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 4 yatak odalı ilan sayısı | 25 | ilan | K0030 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 4 yatak odalı ilan sayısı | 2027 | ilan | K0030 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 4 yatak odalı ilan sayısı | 10 | ilan | K0030 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 4 yatak odalı ilan sayısı | 17 | ilan | K0030 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 4 yatak odalı ilan sayısı | 4 | ilan | K0030 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 5 yatak odalı ilan sayısı | 16 | ilan | K0031 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 5 yatak odalı ilan sayısı | 2027 | ilan | K0031 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 5 yatak odalı ilan sayısı | 10 | ilan | K0031 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 5 yatak odalı ilan sayısı | 17 | ilan | K0031 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 5 yatak odalı ilan sayısı | 5 | ilan | K0031 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 6+ yatak odalı ilan sayısı | 7 | ilan | K0032 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 6+ yatak odalı ilan sayısı | 2027 | ilan | K0032 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 6+ yatak odalı ilan sayısı | 10 | ilan | K0032 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 6+ yatak odalı ilan sayısı | 17 | ilan | K0032 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: 6+ yatak odalı ilan sayısı | 6 | ilan | K0032 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,491–$6,264) | 3,727 | USD (7 gece) | K0033 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,491–$6,264) | 2026 | USD (7 gece) | K0033 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,491–$6,264) | 14 | USD (7 gece) | K0033 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,491–$6,264) | 21 | USD (7 gece) | K0033 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,491–$6,264) | 2026-10-09 | USD (7 gece) | K0033 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,491–$6,264) | 7 | USD (7 gece) | K0033 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,491–$6,264) | 2,491 | USD (7 gece) | K0033 |
| Rosemary Beach · Kasım 2026 · 14–21 Kasım: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,491–$6,264) | 6,264 | USD (7 gece) | K0033 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,482–$5,655) | 3,487 | USD (7 gece) | K0034 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,482–$5,655) | 2026 | USD (7 gece) | K0034 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,482–$5,655) | 12 | USD (7 gece) | K0034 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,482–$5,655) | 19 | USD (7 gece) | K0034 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,482–$5,655) | 2026-10-09 | USD (7 gece) | K0034 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,482–$5,655) | 7 | USD (7 gece) | K0034 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,482–$5,655) | 2,482 | USD (7 gece) | K0034 |
| Rosemary Beach · Aralık 2026 · 12–19 Aralık: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,482–$5,655) | 5,655 | USD (7 gece) | K0034 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,512–$6,108) | 4,159 | USD (7 gece) | K0035 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,512–$6,108) | 2027 | USD (7 gece) | K0035 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,512–$6,108) | 9 | USD (7 gece) | K0035 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,512–$6,108) | 16 | USD (7 gece) | K0035 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,512–$6,108) | 2026-10-09 | USD (7 gece) | K0035 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,512–$6,108) | 7 | USD (7 gece) | K0035 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,512–$6,108) | 2,512 | USD (7 gece) | K0035 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,512–$6,108) | 6,108 | USD (7 gece) | K0035 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,951–$6,543) | 4,090 | USD (7 gece) | K0036 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,951–$6,543) | 2027 | USD (7 gece) | K0036 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,951–$6,543) | 13 | USD (7 gece) | K0036 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,951–$6,543) | 20 | USD (7 gece) | K0036 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,951–$6,543) | 2026-10-09 | USD (7 gece) | K0036 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,951–$6,543) | 7 | USD (7 gece) | K0036 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,951–$6,543) | 2,951 | USD (7 gece) | K0036 |
| Rosemary Beach · Şubat 2027 · 13–20 Şubat: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $2,951–$6,543) | 6,543 | USD (7 gece) | K0036 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,014–$9,367) | 5,872 | USD (7 gece) | K0037 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,014–$9,367) | 2027 | USD (7 gece) | K0037 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,014–$9,367) | 13 | USD (7 gece) | K0037 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,014–$9,367) | 20 | USD (7 gece) | K0037 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,014–$9,367) | 2026-10-09 | USD (7 gece) | K0037 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,014–$9,367) | 7 | USD (7 gece) | K0037 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,014–$9,367) | 4,014 | USD (7 gece) | K0037 |
| Rosemary Beach · Mart 2027 · 13–20 Mart: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,014–$9,367) | 9,367 | USD (7 gece) | K0037 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,465–$7,174) | 4,685 | USD (7 gece) | K0038 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,465–$7,174) | 2027 | USD (7 gece) | K0038 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,465–$7,174) | 10 | USD (7 gece) | K0038 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,465–$7,174) | 17 | USD (7 gece) | K0038 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,465–$7,174) | 2026-10-09 | USD (7 gece) | K0038 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,465–$7,174) | 7 | USD (7 gece) | K0038 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,465–$7,174) | 3,465 | USD (7 gece) | K0038 |
| Rosemary Beach · Nisan 2027 · 10–17 Nisan: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,465–$7,174) | 7,174 | USD (7 gece) | K0038 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,226–$8,732) | 5,369 | USD (7 gece) | K0039 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,226–$8,732) | 2027 | USD (7 gece) | K0039 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,226–$8,732) | 15 | USD (7 gece) | K0039 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,226–$8,732) | 22 | USD (7 gece) | K0039 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,226–$8,732) | 2026-10-09 | USD (7 gece) | K0039 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,226–$8,732) | 7 | USD (7 gece) | K0039 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,226–$8,732) | 4,226 | USD (7 gece) | K0039 |
| Rosemary Beach · Mayıs 2027 · 15–22 Mayıs: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,226–$8,732) | 8,732 | USD (7 gece) | K0039 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,804–$12,522) | 6,994 | USD (7 gece) | K0040 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,804–$12,522) | 2027 | USD (7 gece) | K0040 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,804–$12,522) | 12 | USD (7 gece) | K0040 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,804–$12,522) | 19 | USD (7 gece) | K0040 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,804–$12,522) | 2026-10-09 | USD (7 gece) | K0040 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,804–$12,522) | 7 | USD (7 gece) | K0040 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,804–$12,522) | 4,804 | USD (7 gece) | K0040 |
| Rosemary Beach · Haziran 2027 · 12–19 Haziran: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,804–$12,522) | 12,522 | USD (7 gece) | K0040 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$12,028) | 7,223 | USD (7 gece) | K0041 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$12,028) | 2027 | USD (7 gece) | K0041 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$12,028) | 10 | USD (7 gece) | K0041 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$12,028) | 17 | USD (7 gece) | K0041 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$12,028) | 2026-10-09 | USD (7 gece) | K0041 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$12,028) | 7 | USD (7 gece) | K0041 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$12,028) | 4,665 | USD (7 gece) | K0041 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$12,028) | 12,028 | USD (7 gece) | K0041 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,535–$8,704) | 4,929 | USD (7 gece) | K0042 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,535–$8,704) | 2027 | USD (7 gece) | K0042 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,535–$8,704) | 14 | USD (7 gece) | K0042 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,535–$8,704) | 21 | USD (7 gece) | K0042 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,535–$8,704) | 2026-10-09 | USD (7 gece) | K0042 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,535–$8,704) | 7 | USD (7 gece) | K0042 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,535–$8,704) | 3,535 | USD (7 gece) | K0042 |
| Rosemary Beach · Ağustos 2027 · 14–21 Ağustos: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,535–$8,704) | 8,704 | USD (7 gece) | K0042 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,355–$8,467) | 4,771 | USD (7 gece) | K0043 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,355–$8,467) | 2027 | USD (7 gece) | K0043 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,355–$8,467) | 11 | USD (7 gece) | K0043 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,355–$8,467) | 18 | USD (7 gece) | K0043 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,355–$8,467) | 2026-10-09 | USD (7 gece) | K0043 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,355–$8,467) | 7 | USD (7 gece) | K0043 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,355–$8,467) | 3,355 | USD (7 gece) | K0043 |
| Rosemary Beach · Eylül 2027 · 11–18 Eylül: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $3,355–$8,467) | 8,467 | USD (7 gece) | K0043 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$9,524) | 6,219 | USD (7 gece) | K0044 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$9,524) | 2027 | USD (7 gece) | K0044 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$9,524) | 9 | USD (7 gece) | K0044 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$9,524) | 16 | USD (7 gece) | K0044 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$9,524) | 2026-10-09 | USD (7 gece) | K0044 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$9,524) | 7 | USD (7 gece) | K0044 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$9,524) | 4,665 | USD (7 gece) | K0044 |
| Rosemary Beach · Ekim 2027 · 9–16 Ekim: kiralama şirketlerinin sitelerinde 2026-10-09 tarihinde sorulan 7 gecelik toplam fiyatın ortancası (çeyrekler $4,665–$9,524) | 9,524 | USD (7 gece) | K0044 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 2,793 | USD (7 gece) | K0045 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 2027 | USD (7 gece) | K0045 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 9 | USD (7 gece) | K0045 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 16 | USD (7 gece) | K0045 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 1 | USD (7 gece) | K0045 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 2 | USD (7 gece) | K0045 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 7 | USD (7 gece) | K0045 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 4,752 | USD (7 gece) | K0046 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 2027 | USD (7 gece) | K0046 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 9 | USD (7 gece) | K0046 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 16 | USD (7 gece) | K0046 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 3 | USD (7 gece) | K0046 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 7 | USD (7 gece) | K0046 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 5,956 | USD (7 gece) | K0047 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 2027 | USD (7 gece) | K0047 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 9 | USD (7 gece) | K0047 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 16 | USD (7 gece) | K0047 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 4 | USD (7 gece) | K0047 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 7 | USD (7 gece) | K0047 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 8,640 | USD (7 gece) | K0048 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 2027 | USD (7 gece) | K0048 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 9 | USD (7 gece) | K0048 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 16 | USD (7 gece) | K0048 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 5 | USD (7 gece) | K0048 |
| Rosemary Beach · Ocak 2027 · 9–16 Ocak · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 7 | USD (7 gece) | K0048 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 4,440 | USD (7 gece) | K0049 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 2027 | USD (7 gece) | K0049 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 10 | USD (7 gece) | K0049 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 17 | USD (7 gece) | K0049 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 1 | USD (7 gece) | K0049 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 2 | USD (7 gece) | K0049 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 1-2 yatak odası: 7 gecelik toplam fiyatın ortancası | 7 | USD (7 gece) | K0049 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 8,376 | USD (7 gece) | K0050 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 2027 | USD (7 gece) | K0050 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 10 | USD (7 gece) | K0050 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 17 | USD (7 gece) | K0050 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 3 | USD (7 gece) | K0050 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 3 yatak odası: 7 gecelik toplam fiyatın ortancası | 7 | USD (7 gece) | K0050 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 12,817 | USD (7 gece) | K0051 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 2027 | USD (7 gece) | K0051 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 10 | USD (7 gece) | K0051 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 17 | USD (7 gece) | K0051 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 4 | USD (7 gece) | K0051 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 4 yatak odası: 7 gecelik toplam fiyatın ortancası | 7 | USD (7 gece) | K0051 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 15,287 | USD (7 gece) | K0052 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 2027 | USD (7 gece) | K0052 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 10 | USD (7 gece) | K0052 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 17 | USD (7 gece) | K0052 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 5 | USD (7 gece) | K0052 |
| Rosemary Beach · Temmuz 2027 · 10–17 Temmuz · 5+ yatak odası: 7 gecelik toplam fiyatın ortancası | 7 | USD (7 gece) | K0052 |
| Rosemary Beach: Visit South Walton restoran dizininde bu mahalleye bağlı restoran sayısı | 12 | restoran | K0053 |
| Rosemary Beach: fiyat seviyesi hesaplanabilen restoran sayısı ($ 0, $$ 0, $$$ 2, $$$$ 1) | 3 | restoran | K0054 |
| Rosemary Beach: fiyat seviyesi hesaplanabilen restoran sayısı ($ 0, $$ 0, $$$ 2, $$$$ 1) | 0 | restoran | K0054 |
| Rosemary Beach: fiyat seviyesi hesaplanabilen restoran sayısı ($ 0, $$ 0, $$$ 2, $$$$ 1) | 2 | restoran | K0054 |
| Rosemary Beach: fiyat seviyesi hesaplanabilen restoran sayısı ($ 0, $$ 0, $$$ 2, $$$$ 1) | 1 | restoran | K0054 |
| Rosemary Beach: sitesinde çevrimiçi rezervasyon bağlantısı bulunan restoran sayısı | 1 | restoran | K0055 |
| Rosemary Beach: sitesinde çocuk menüsü yayımlayan restoran sayısı | 5 | restoran | K0056 |
| Amavida Coffee in Rosemary Beach: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: 6:30am – 7:00pm · Open Daily | 6 |  | K0057 |
| Amavida Coffee in Rosemary Beach: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: 6:30am – 7:00pm · Open Daily | 30 |  | K0057 |
| Amavida Coffee in Rosemary Beach: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: 6:30am – 7:00pm · Open Daily | 7 |  | K0057 |
| Amavida Coffee in Rosemary Beach: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: 6:30am – 7:00pm · Open Daily | 00 |  | K0057 |
| CK Feed & Supply Provisions & Gifts: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: Open Daily: 7:30am-9pm | 7 |  | K0058 |
| CK Feed & Supply Provisions & Gifts: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: Open Daily: 7:30am-9pm | 30 |  | K0058 |
| CK Feed & Supply Provisions & Gifts: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: Open Daily: 7:30am-9pm | 9 |  | K0058 |
| Cowgirl Kitchen Restaurant & Bar: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: Open Daily: 7:30am-9pm | 7 |  | K0059 |
| Cowgirl Kitchen Restaurant & Bar: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: Open Daily: 7:30am-9pm | 30 |  | K0059 |
| Cowgirl Kitchen Restaurant & Bar: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: Open Daily: 7:30am-9pm | 9 |  | K0059 |
| Edward's Fine Food & Wine: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: , Tu 17:00-21:00, We 17:00-21:00, Th 17:00-21:00, Fr 17:00-21:30, Sa 17:00-21:30, Su 17:00-21:00 | 35 | USD (ana yemek ortancası) | K0061 |
| Edward's Fine Food & Wine: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: , Tu 17:00-21:00, We 17:00-21:00, Th 17:00-21:00, Fr 17:00-21:30, Sa 17:00-21:30, Su 17:00-21:00 | 17 | USD (ana yemek ortancası) | K0061 |
| Edward's Fine Food & Wine: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: , Tu 17:00-21:00, We 17:00-21:00, Th 17:00-21:00, Fr 17:00-21:30, Sa 17:00-21:30, Su 17:00-21:00 | 00 | USD (ana yemek ortancası) | K0061 |
| Edward's Fine Food & Wine: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: , Tu 17:00-21:00, We 17:00-21:00, Th 17:00-21:00, Fr 17:00-21:30, Sa 17:00-21:30, Su 17:00-21:00 | 21 | USD (ana yemek ortancası) | K0061 |
| Edward's Fine Food & Wine: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: , Tu 17:00-21:00, We 17:00-21:00, Th 17:00-21:00, Fr 17:00-21:30, Sa 17:00-21:30, Su 17:00-21:00 | 30 | USD (ana yemek ortancası) | K0061 |
| Gallion's: seviye hesaplanmadı; çevrimiçi rezervasyon bağlantısı var; çocuk menüsü sitede bulunamadı; saatler: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday 09:00–22:00 | 09 |  | K0062 |
| Gallion's: seviye hesaplanmadı; çevrimiçi rezervasyon bağlantısı var; çocuk menüsü sitede bulunamadı; saatler: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday 09:00–22:00 | 00 |  | K0062 |
| Gallion's: seviye hesaplanmadı; çevrimiçi rezervasyon bağlantısı var; çocuk menüsü sitede bulunamadı; saatler: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday 09:00–22:00 | 22 |  | K0062 |
| Havana Beach Bar & Grill: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: 8 AM–2 PM | 8 |  | K0063 |
| Havana Beach Bar & Grill: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede bulunamadı; saatler: 8 AM–2 PM | 2 |  | K0063 |
| La Crema-Tapas and Chocolate: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: Mo 11:00-21:00, Tu 11:00-21:00, We 11:00-21:00, Th 11:00-21:00, Fr 11:00-22:00, Sa 11:00-22:00, Su 11:00-21:00 | 25 | USD (ana yemek ortancası) | K0064 |
| La Crema-Tapas and Chocolate: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: Mo 11:00-21:00, Tu 11:00-21:00, We 11:00-21:00, Th 11:00-21:00, Fr 11:00-22:00, Sa 11:00-22:00, Su 11:00-21:00 | 11 | USD (ana yemek ortancası) | K0064 |
| La Crema-Tapas and Chocolate: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: Mo 11:00-21:00, Tu 11:00-21:00, We 11:00-21:00, Th 11:00-21:00, Fr 11:00-22:00, Sa 11:00-22:00, Su 11:00-21:00 | 00 | USD (ana yemek ortancası) | K0064 |
| La Crema-Tapas and Chocolate: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: Mo 11:00-21:00, Tu 11:00-21:00, We 11:00-21:00, Th 11:00-21:00, Fr 11:00-22:00, Sa 11:00-22:00, Su 11:00-21:00 | 21 | USD (ana yemek ortancası) | K0064 |
| La Crema-Tapas and Chocolate: seviye $$$ (bizim sınıflamamız); rezervasyon almıyor; çocuk menüsü sitede var; saatler: Mo 11:00-21:00, Tu 11:00-21:00, We 11:00-21:00, Th 11:00-21:00, Fr 11:00-22:00, Sa 11:00-22:00, Su 11:00-21:00 | 22 | USD (ana yemek ortancası) | K0064 |
| Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 49 | USD (ana yemek ortancası) | K0065 |
| Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 3 | USD (ana yemek ortancası) | K0065 |
| Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 10 | USD (ana yemek ortancası) | K0065 |
| Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 1 | USD (ana yemek ortancası) | K0065 |
| Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 45 | USD (ana yemek ortancası) | K0065 |
| Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 4 | USD (ana yemek ortancası) | K0065 |
| Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 18 | USD (ana yemek ortancası) | K0065 |
| Restaurant Paradis: seviye $$$$ (bizim sınıflamamız); telefonla rezervasyon; çocuk menüsü sitede var; saatler: Sunday, Monday, Tuesday, Wednesday, Thursday 17:00–21:00 · Friday, Saturday 17:00–22:00 | 47 | USD (ana yemek ortancası) | K0066 |
| Restaurant Paradis: seviye $$$$ (bizim sınıflamamız); telefonla rezervasyon; çocuk menüsü sitede var; saatler: Sunday, Monday, Tuesday, Wednesday, Thursday 17:00–21:00 · Friday, Saturday 17:00–22:00 | 17 | USD (ana yemek ortancası) | K0066 |
| Restaurant Paradis: seviye $$$$ (bizim sınıflamamız); telefonla rezervasyon; çocuk menüsü sitede var; saatler: Sunday, Monday, Tuesday, Wednesday, Thursday 17:00–21:00 · Friday, Saturday 17:00–22:00 | 00 | USD (ana yemek ortancası) | K0066 |
| Restaurant Paradis: seviye $$$$ (bizim sınıflamamız); telefonla rezervasyon; çocuk menüsü sitede var; saatler: Sunday, Monday, Tuesday, Wednesday, Thursday 17:00–21:00 · Friday, Saturday 17:00–22:00 | 21 | USD (ana yemek ortancası) | K0066 |
| Restaurant Paradis: seviye $$$$ (bizim sınıflamamız); telefonla rezervasyon; çocuk menüsü sitede var; saatler: Sunday, Monday, Tuesday, Wednesday, Thursday 17:00–21:00 · Friday, Saturday 17:00–22:00 | 22 | USD (ana yemek ortancası) | K0066 |
| Summer Kitchen Café: seviye hesaplanmadı; rezervasyon almıyor; çocuk menüsü sitede bulunamadı; saatler: OPEN DAILY FROM 730AM - 3PM | 730 |  | K0067 |
| Summer Kitchen Café: seviye hesaplanmadı; rezervasyon almıyor; çocuk menüsü sitede bulunamadı; saatler: OPEN DAILY FROM 730AM - 3PM | 3 |  | K0067 |
| The Courtyard at Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 49 | USD (ana yemek ortancası) | K0068 |
| The Courtyard at Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 3 | USD (ana yemek ortancası) | K0068 |
| The Courtyard at Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 10 | USD (ana yemek ortancası) | K0068 |
| The Courtyard at Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 1 | USD (ana yemek ortancası) | K0068 |
| The Courtyard at Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 45 | USD (ana yemek ortancası) | K0068 |
| The Courtyard at Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 4 | USD (ana yemek ortancası) | K0068 |
| The Courtyard at Pescado: seviye hesaplanmadı; rezervasyon bilgisi yok; çocuk menüsü sitede var; saatler: Monday–Tuesday \| 3PM–10PM · Wednesday–Sunday \| 10AM–10PM · Brunch \| Wednesday–Sunday, 10AM–1:45PM · Happy Hour \| Daily, 3PM–4PM · All ages welcome Wednesday–Sunday until 3PM. · Guests must be 18+ after 3PM. | 18 | USD (ana yemek ortancası) | K0068 |
| Rosemary Beach: ilanların en yakın büyük süpermarket noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) | 1.36 | mil | K0069 |
| Rosemary Beach: ilanların en yakın büyük süpermarket noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) | 1 | mil | K0069 |
| Rosemary Beach: ilanların en yakın büyük süpermarket noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) | 2.18 | mil | K0069 |
| Rosemary Beach: ilanların en yakın yerel ve gurme market noktasına kuş uçuşu mesafe ortancası (ilanların %91'i 1 mil içinde) | 0.25 | mil | K0070 |
| Rosemary Beach: ilanların en yakın yerel ve gurme market noktasına kuş uçuşu mesafe ortancası (ilanların %91'i 1 mil içinde) | 91 | mil | K0070 |
| Rosemary Beach: ilanların en yakın yerel ve gurme market noktasına kuş uçuşu mesafe ortancası (ilanların %91'i 1 mil içinde) | 1 | mil | K0070 |
| Rosemary Beach: ilanların en yakın yerel ve gurme market noktasına kuş uçuşu mesafe ortancası (ilanların %91'i 1 mil içinde) | 0.40 | mil | K0070 |
| Rosemary Beach: ilanların en yakın küçük market noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) | 2.77 | mil | K0071 |
| Rosemary Beach: ilanların en yakın küçük market noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) | 1 | mil | K0071 |
| Rosemary Beach: ilanların en yakın küçük market noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) | 4.45 | mil | K0071 |
| Rosemary Beach: ilanların en yakın eczane noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) | 2.71 | mil | K0072 |
| Rosemary Beach: ilanların en yakın eczane noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) | 1 | mil | K0072 |
| Rosemary Beach: ilanların en yakın eczane noktasına kuş uçuşu mesafe ortancası (ilanların %1'i 1 mil içinde) | 4.36 | mil | K0072 |
| Rosemary Beach: ilanların en yakın acil servis noktasına kuş uçuşu mesafe ortancası (ilanların %0'i 1 mil içinde) | 13.57 | mil | K0073 |
| Rosemary Beach: ilanların en yakın acil servis noktasına kuş uçuşu mesafe ortancası (ilanların %0'i 1 mil içinde) | 0 | mil | K0073 |
| Rosemary Beach: ilanların en yakın acil servis noktasına kuş uçuşu mesafe ortancası (ilanların %0'i 1 mil içinde) | 1 | mil | K0073 |
| Rosemary Beach: ilanların en yakın acil servis noktasına kuş uçuşu mesafe ortancası (ilanların %0'i 1 mil içinde) | 21.83 | mil | K0073 |
| Rosemary Beach: ilanların en yakın acil bakım (urgent care) noktasına kuş uçuşu mesafe ortancası (ilanların %36'i 1 mil içinde) | 1.05 | mil | K0074 |
| Rosemary Beach: ilanların en yakın acil bakım (urgent care) noktasına kuş uçuşu mesafe ortancası (ilanların %36'i 1 mil içinde) | 36 | mil | K0074 |
| Rosemary Beach: ilanların en yakın acil bakım (urgent care) noktasına kuş uçuşu mesafe ortancası (ilanların %36'i 1 mil içinde) | 1 | mil | K0074 |
| Rosemary Beach: ilanların en yakın acil bakım (urgent care) noktasına kuş uçuşu mesafe ortancası (ilanların %36'i 1 mil içinde) | 1.69 | mil | K0074 |
| Rosemary Beach: ilanların en yakın bisiklet kiralama noktasına kuş uçuşu mesafe ortancası (ilanların %91'i 1 mil içinde) | 0.3 | mil | K0075 |
| Rosemary Beach: ilanların en yakın bisiklet kiralama noktasına kuş uçuşu mesafe ortancası (ilanların %91'i 1 mil içinde) | 91 | mil | K0075 |
| Rosemary Beach: ilanların en yakın bisiklet kiralama noktasına kuş uçuşu mesafe ortancası (ilanların %91'i 1 mil içinde) | 1 | mil | K0075 |
| Rosemary Beach: ilanların en yakın bisiklet kiralama noktasına kuş uçuşu mesafe ortancası (ilanların %91'i 1 mil içinde) | 0.48 | mil | K0075 |
| Rosemary Beach: ilanların en yakın halka açık plaj erişimi (ilçe listesi) noktasına kuş uçuşu mesafe ortancası (ilanların %93'i 1 mil içinde) | 0.37 | mil | K0076 |
| Rosemary Beach: ilanların en yakın halka açık plaj erişimi (ilçe listesi) noktasına kuş uçuşu mesafe ortancası (ilanların %93'i 1 mil içinde) | 93 | mil | K0076 |
| Rosemary Beach: ilanların en yakın halka açık plaj erişimi (ilçe listesi) noktasına kuş uçuşu mesafe ortancası (ilanların %93'i 1 mil içinde) | 1 | mil | K0076 |
| Rosemary Beach: ilanların en yakın halka açık plaj erişimi (ilçe listesi) noktasına kuş uçuşu mesafe ortancası (ilanların %93'i 1 mil içinde) | 0.59 | mil | K0076 |
| DPZ, Rosemary Beach'i 1995'te Paul Borden, Leucadia National Corp. ve Patrick Bienvenue için tasarlanmış olarak listeliyor. | 1995 |  | K0077 |
| Rosemary Beach'teki yemek ve şarap etkinliği Rosemary Beach Uncorked 15. yılını 14 Kasım 2026'da kutluyor. | 15 |  | K0078 |
| Rosemary Beach'teki yemek ve şarap etkinliği Rosemary Beach Uncorked 15. yılını 14 Kasım 2026'da kutluyor. | 14 |  | K0078 |
| Rosemary Beach'teki yemek ve şarap etkinliği Rosemary Beach Uncorked 15. yılını 14 Kasım 2026'da kutluyor. | 2026 |  | K0078 |
| 30A 10K Thanksgiving Day Races Şükran Günü'nde Rosemary Beach'te yapılır; 15. yarışlar 26 Kasım 2026'da. | 30 |  | K0079 |
| 30A 10K Thanksgiving Day Races Şükran Günü'nde Rosemary Beach'te yapılır; 15. yarışlar 26 Kasım 2026'da. | 10 |  | K0079 |
| 30A 10K Thanksgiving Day Races Şükran Günü'nde Rosemary Beach'te yapılır; 15. yarışlar 26 Kasım 2026'da. | 15 |  | K0079 |
| 30A 10K Thanksgiving Day Races Şükran Günü'nde Rosemary Beach'te yapılır; 15. yarışlar 26 Kasım 2026'da. | 26 |  | K0079 |
| 30A 10K Thanksgiving Day Races Şükran Günü'nde Rosemary Beach'te yapılır; 15. yarışlar 26 Kasım 2026'da. | 2026 |  | K0079 |
| Ocak: ortalama en yüksek sıcaklık | 63.1 | °F | K0080 |
| Ocak: ortalama en yüksek sıcaklık | 17.3 | °F | K0080 |
| Şubat: ortalama en yüksek sıcaklık | 65.8 | °F | K0081 |
| Şubat: ortalama en yüksek sıcaklık | 18.8 | °F | K0081 |
| Mart: ortalama en yüksek sıcaklık | 70.7 | °F | K0082 |
| Mart: ortalama en yüksek sıcaklık | 21.5 | °F | K0082 |
| Nisan: ortalama en yüksek sıcaklık | 76.2 | °F | K0083 |
| Nisan: ortalama en yüksek sıcaklık | 24.6 | °F | K0083 |
| Mayıs: ortalama en yüksek sıcaklık | 83.5 | °F | K0084 |
| Mayıs: ortalama en yüksek sıcaklık | 28.6 | °F | K0084 |
| Haziran: ortalama en yüksek sıcaklık | 88.9 | °F | K0085 |
| Haziran: ortalama en yüksek sıcaklık | 31.6 | °F | K0085 |
| Temmuz: ortalama en yüksek sıcaklık | 90.9 | °F | K0086 |
| Temmuz: ortalama en yüksek sıcaklık | 32.7 | °F | K0086 |
| Ağustos: ortalama en yüksek sıcaklık | 90.6 | °F | K0087 |
| Ağustos: ortalama en yüksek sıcaklık | 32.6 | °F | K0087 |
| Eylül: ortalama en yüksek sıcaklık | 88.5 | °F | K0088 |
| Eylül: ortalama en yüksek sıcaklık | 31.4 | °F | K0088 |
| Ekim: ortalama en yüksek sıcaklık | 80.9 | °F | K0089 |
| Ekim: ortalama en yüksek sıcaklık | 27.2 | °F | K0089 |
| Kasım: ortalama en yüksek sıcaklık | 72.1 | °F | K0090 |
| Kasım: ortalama en yüksek sıcaklık | 22.3 | °F | K0090 |
| Aralık: ortalama en yüksek sıcaklık | 65.6 | °F | K0091 |
| Aralık: ortalama en yüksek sıcaklık | 18.7 | °F | K0091 |
| Ocak: ortalama en düşük sıcaklık | 45.3 | °F | K0092 |
| Ocak: ortalama en düşük sıcaklık | 7.4 | °F | K0092 |
| Şubat: ortalama en düşük sıcaklık | 47.9 | °F | K0093 |
| Şubat: ortalama en düşük sıcaklık | 8.8 | °F | K0093 |
| Mart: ortalama en düşük sıcaklık | 53.6 | °F | K0094 |
| Mart: ortalama en düşük sıcaklık | 12.0 | °F | K0094 |
| Nisan: ortalama en düşük sıcaklık | 60.1 | °F | K0095 |
| Nisan: ortalama en düşük sıcaklık | 15.6 | °F | K0095 |
| Mayıs: ortalama en düşük sıcaklık | 68 | °F | K0096 |
| Mayıs: ortalama en düşük sıcaklık | 20.0 | °F | K0096 |
| Haziran: ortalama en düşük sıcaklık | 74.1 | °F | K0097 |
| Haziran: ortalama en düşük sıcaklık | 23.4 | °F | K0097 |
| Temmuz: ortalama en düşük sıcaklık | 76.2 | °F | K0098 |
| Temmuz: ortalama en düşük sıcaklık | 24.6 | °F | K0098 |
| Ağustos: ortalama en düşük sıcaklık | 75.8 | °F | K0099 |
| Ağustos: ortalama en düşük sıcaklık | 24.3 | °F | K0099 |
| Eylül: ortalama en düşük sıcaklık | 72.4 | °F | K0100 |
| Eylül: ortalama en düşük sıcaklık | 22.4 | °F | K0100 |
| Ekim: ortalama en düşük sıcaklık | 63.2 | °F | K0101 |
| Ekim: ortalama en düşük sıcaklık | 17.3 | °F | K0101 |
| Kasım: ortalama en düşük sıcaklık | 53 | °F | K0102 |
| Kasım: ortalama en düşük sıcaklık | 11.7 | °F | K0102 |
| Aralık: ortalama en düşük sıcaklık | 47.5 | °F | K0103 |
| Aralık: ortalama en düşük sıcaklık | 8.6 | °F | K0103 |
| Ocak: ortalama yağış | 4.52 | inç | K0104 |
| Ocak: ortalama yağış | 115 | inç | K0104 |
| Şubat: ortalama yağış | 4.96 | inç | K0105 |
| Şubat: ortalama yağış | 126 | inç | K0105 |
| Mart: ortalama yağış | 4.7 | inç | K0106 |
| Mart: ortalama yağış | 119 | inç | K0106 |
| Nisan: ortalama yağış | 4.55 | inç | K0107 |
| Nisan: ortalama yağış | 116 | inç | K0107 |
| Mayıs: ortalama yağış | 3.22 | inç | K0108 |
| Mayıs: ortalama yağış | 82 | inç | K0108 |
| Haziran: ortalama yağış | 4.7 | inç | K0109 |
| Haziran: ortalama yağış | 119 | inç | K0109 |
| Temmuz: ortalama yağış | 5.77 | inç | K0110 |
| Temmuz: ortalama yağış | 147 | inç | K0110 |
| Ağustos: ortalama yağış | 6.08 | inç | K0111 |
| Ağustos: ortalama yağış | 154 | inç | K0111 |
| Eylül: ortalama yağış | 5.18 | inç | K0112 |
| Eylül: ortalama yağış | 132 | inç | K0112 |
| Ekim: ortalama yağış | 2.82 | inç | K0113 |
| Ekim: ortalama yağış | 72 | inç | K0113 |
| Kasım: ortalama yağış | 4.13 | inç | K0114 |
| Kasım: ortalama yağış | 105 | inç | K0114 |
| Aralık: ortalama yağış | 4.72 | inç | K0115 |
| Aralık: ortalama yağış | 120 | inç | K0115 |
| Ocak: 0,10 inç ve üstü yağışlı gün ortalaması | 5.6 | gün | K0116 |
| Ocak: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0116 |
| Ocak: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0116 |
| Şubat: 0,10 inç ve üstü yağışlı gün ortalaması | 5.3 | gün | K0117 |
| Şubat: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0117 |
| Şubat: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0117 |
| Mart: 0,10 inç ve üstü yağışlı gün ortalaması | 5.2 | gün | K0118 |
| Mart: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0118 |
| Mart: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0118 |
| Nisan: 0,10 inç ve üstü yağışlı gün ortalaması | 4 | gün | K0119 |
| Nisan: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0119 |
| Nisan: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0119 |
| Mayıs: 0,10 inç ve üstü yağışlı gün ortalaması | 3.7 | gün | K0120 |
| Mayıs: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0120 |
| Mayıs: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0120 |
| Haziran: 0,10 inç ve üstü yağışlı gün ortalaması | 6.1 | gün | K0121 |
| Haziran: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0121 |
| Haziran: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0121 |
| Temmuz: 0,10 inç ve üstü yağışlı gün ortalaması | 7.2 | gün | K0122 |
| Temmuz: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0122 |
| Temmuz: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0122 |
| Ağustos: 0,10 inç ve üstü yağışlı gün ortalaması | 8.1 | gün | K0123 |
| Ağustos: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0123 |
| Ağustos: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0123 |
| Eylül: 0,10 inç ve üstü yağışlı gün ortalaması | 5.3 | gün | K0124 |
| Eylül: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0124 |
| Eylül: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0124 |
| Ekim: 0,10 inç ve üstü yağışlı gün ortalaması | 3.5 | gün | K0125 |
| Ekim: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0125 |
| Ekim: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0125 |
| Kasım: 0,10 inç ve üstü yağışlı gün ortalaması | 4.3 | gün | K0126 |
| Kasım: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0126 |
| Kasım: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0126 |
| Aralık: 0,10 inç ve üstü yağışlı gün ortalaması | 6.5 | gün | K0127 |
| Aralık: 0,10 inç ve üstü yağışlı gün ortalaması | 0 | gün | K0127 |
| Aralık: 0,10 inç ve üstü yağışlı gün ortalaması | 10 | gün | K0127 |
| Ocak: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 0 | gün | K0128 |
| Ocak: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0128 |
| Şubat: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 0 | gün | K0129 |
| Şubat: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0129 |
| Mart: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 0 | gün | K0130 |
| Mart: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0130 |
| Nisan: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 0 | gün | K0131 |
| Nisan: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0131 |
| Mayıs: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 1.1 | gün | K0132 |
| Mayıs: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0132 |
| Haziran: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 7.8 | gün | K0133 |
| Haziran: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0133 |
| Temmuz: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 14.9 | gün | K0134 |
| Temmuz: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0134 |
| Ağustos: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 16.9 | gün | K0135 |
| Ağustos: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0135 |
| Eylül: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 8.7 | gün | K0136 |
| Eylül: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0136 |
| Ekim: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 0.9 | gün | K0137 |
| Ekim: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0137 |
| Kasım: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 0 | gün | K0138 |
| Kasım: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0138 |
| Aralık: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 0 | gün | K0139 |
| Aralık: en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması | 90 | gün | K0139 |
| Ocak: aylık ortalama deniz suyu sıcaklığı | 60.2 | °F | K0140 |
| Ocak: aylık ortalama deniz suyu sıcaklığı | 15.7 | °F | K0140 |
| Şubat: aylık ortalama deniz suyu sıcaklığı | 60.6 | °F | K0141 |
| Şubat: aylık ortalama deniz suyu sıcaklığı | 15.9 | °F | K0141 |
| Mart: aylık ortalama deniz suyu sıcaklığı | 65.7 | °F | K0142 |
| Mart: aylık ortalama deniz suyu sıcaklığı | 18.7 | °F | K0142 |
| Nisan: aylık ortalama deniz suyu sıcaklığı | 70.7 | °F | K0143 |
| Nisan: aylık ortalama deniz suyu sıcaklığı | 21.5 | °F | K0143 |
| Mayıs: aylık ortalama deniz suyu sıcaklığı | 77.2 | °F | K0144 |
| Mayıs: aylık ortalama deniz suyu sıcaklığı | 25.1 | °F | K0144 |
| Haziran: aylık ortalama deniz suyu sıcaklığı | 82.3 | °F | K0145 |
| Haziran: aylık ortalama deniz suyu sıcaklığı | 28.0 | °F | K0145 |
| Temmuz: aylık ortalama deniz suyu sıcaklığı | 84.3 | °F | K0146 |
| Temmuz: aylık ortalama deniz suyu sıcaklığı | 29.0 | °F | K0146 |
| Ağustos: aylık ortalama deniz suyu sıcaklığı | 85.8 | °F | K0147 |
| Ağustos: aylık ortalama deniz suyu sıcaklığı | 29.9 | °F | K0147 |
| Eylül: aylık ortalama deniz suyu sıcaklığı | 84.2 | °F | K0148 |
| Eylül: aylık ortalama deniz suyu sıcaklığı | 29.0 | °F | K0148 |
| Ekim: aylık ortalama deniz suyu sıcaklığı | 78.5 | °F | K0149 |
| Ekim: aylık ortalama deniz suyu sıcaklığı | 25.9 | °F | K0149 |
| Kasım: aylık ortalama deniz suyu sıcaklığı | 70.3 | °F | K0150 |
| Kasım: aylık ortalama deniz suyu sıcaklığı | 21.3 | °F | K0150 |
| Aralık: aylık ortalama deniz suyu sıcaklığı | 63.8 | °F | K0151 |
| Aralık: aylık ortalama deniz suyu sıcaklığı | 17.7 | °F | K0151 |
| Ekim: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 6.5 | % | K0152 |
| Kasım: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 3 | % | K0153 |
| Aralık: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 2.6 | % | K0154 |
| Ocak: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 2.1 | % | K0155 |
| Şubat: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 2.4 | % | K0156 |
| Mart: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 8.5 | % | K0157 |
| Nisan: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 8.6 | % | K0158 |
| Mayıs: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 10.6 | % | K0159 |
| Haziran: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 18.3 | % | K0160 |
| Temmuz: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 20 | % | K0161 |
| Ağustos: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 10.2 | % | K0162 |
| Eylül: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması) | 7.1 | % | K0163 |
| Bu daire içinde kasırga gücünde rüzgâra ulaşan fırtına sayısı | 5 | fırtına | K0164 |
| Bu daire içinde en az tropikal fırtına gücüne ulaşan fırtına sayısı | 13 | fırtına | K0165 |
| Temmuz: daireye ilk girişi bu ayda olan kasırga gücündeki fırtına sayısı | 1 | fırtına | K0166 |
| Ağustos: daireye ilk girişi bu ayda olan kasırga gücündeki fırtına sayısı | 1 | fırtına | K0167 |
| Eylül: daireye ilk girişi bu ayda olan kasırga gücündeki fırtına sayısı | 1 | fırtına | K0168 |
| Ekim: daireye ilk girişi bu ayda olan kasırga gücündeki fırtına sayısı | 2 | fırtına | K0169 |
| Erin (1995): koridora en yakın geçiş | 35.1 | deniz mili | K0170 |
| Erin (1995): koridora en yakın geçiş | 1995 | deniz mili | K0170 |
| Erin (1995): koridora en yakın geçiş | 65.0 | deniz mili | K0170 |
| Opal (1995): koridora en yakın geçiş | 39.7 | deniz mili | K0171 |
| Opal (1995): koridora en yakın geçiş | 1995 | deniz mili | K0171 |
| Opal (1995): koridora en yakın geçiş | 73.4 | deniz mili | K0171 |
| Earl (1998): koridora en yakın geçiş | 18.2 | deniz mili | K0172 |
| Earl (1998): koridora en yakın geçiş | 1998 | deniz mili | K0172 |
| Earl (1998): koridora en yakın geçiş | 33.8 | deniz mili | K0172 |
| Dennis (2005): koridora en yakın geçiş | 40.6 | deniz mili | K0173 |
| Dennis (2005): koridora en yakın geçiş | 2005 | deniz mili | K0173 |
| Dennis (2005): koridora en yakın geçiş | 75.1 | deniz mili | K0173 |
| Michael (2018): koridora en yakın geçiş | 30.5 | deniz mili | K0174 |
| Michael (2018): koridora en yakın geçiş | 2018 | deniz mili | K0174 |
| Michael (2018): koridora en yakın geçiş | 56.4 | deniz mili | K0174 |
