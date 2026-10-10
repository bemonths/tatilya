# GÖREV-12 raporu — yazar özeti ve ayrı sayı listesi

Tarih: 10 Ekim 2026 · Dal: `gorev-12-yazar-ozeti` · Uygulama 0.14.0 · Şema 14 (değişmedi) · Paket biçimi `30a-studio-kanit-paketi/2`

## Kısaca

- main ve `v0.14.0` etiketi GÖREV-11'in son commit'ine (`9adc235`) alındı; CI üçü de başarılı.
- Kanıt paketinin sayı listesi artık ayrı bir CSV dosyası ve yalnız değer alanlarından üretiliyor. Adlardan, adreslerden ve yol numaralarından gelen gürültü kalktı: ilk video paketinde 3.003 sayı → 1.723.
- Her üretimle birlikte metni yazacak kişi için kısa bir **yazar özeti** çıkıyor: tablolar, her satırın K kimlikleri, her bloğun kullanım notu bir kez, sonda kaynak listesi. Özetteki her değer paketteki değerin aynısı; paketten hiçbir satır düşmüyor (test).
- Şablonlarda "oynak konu" alanı var; plaj erişimi hukuku satırları ve bütün çelişkili satırlar paketin ve özetin başında "Yayından önce kontrol edilecek satırlar" listesinde.
- Gerçek veride iki paket "Kanıt paketi" ekranından yeniden üretildi. Toplayıcı çalışmadı, canlı veri çekilmedi. GÖREV-11 paketleri yerinde duruyor.
- İlk video özeti 110 KB; 100 KB hedefini aştı. İçerik düşürülmedi; nedeni aşağıda.

## Adım 1 — main ve etiket

| | Konum | CI |
|---|---|---|
| GÖREV-11 dalı son commit | `9adc235661700dbe0f0bf117fa532f86149a79c1` | 38054575393 başarılı (önceden kontrol edildi) |
| main (fast-forward, push) | `9adc235661700dbe0f0bf117fa532f86149a79c1` | 38058332541 başarılı |
| `v0.14.0` (açıklamalı etiket, push) | → `9adc235` | 38058336127 başarılı |

Etiket mesajı: "v0.14.0 — kanıt paketi, büyük süpermarket ayrımı, resmî acil sağlık noktaları ve izleyici sorularından gelen referanslar". `gorev-12-yazar-ozeti` dalı bu commit'ten açıldı.

## Adım 2 — sayı listesi

- **2a.** Liste yalnız yapılandırılmış alanlardan geliyor: satırın değeri (`tur = ana`), ek değerleri ve örnek büyüklüğü. Ek değerler artık satırda ayrı alan: `"ek_degerler": [{"tur", "deger", "birim"}]`, `tur` şunlardan biri: `alt_ceyrek`, `ust_ceyrek`, `orneklem`, `pay`, `aralik_alt`, `aralik_ust`, `donusum`. İfade metni değişmedi.
  - Konaklama fiyatında çeyrekler, günlük ihtiyaçta 1 mil içindeki pay, iklimde °C/mm karşılığı, trafikte yoğun sezon haftalarının başı ve sonu bu alanlarla geliyor.
- **2b.** Ad, adres, yol ve kimlik numarası ve dönem listeye girmiyor. Referans satırları yalnız tablonun değer alanıyla giriyor; bu kural M14'e yazıldı.
- **2c.** Liste Markdown'dan çıktı. Ayrı dosya `<paket>-sayilar.csv`, sütunları `kanit, tur, deger, birim, etiket`. Markdown'ın sonunda yalnız dosya adı ve satır sayısı yazıyor. JSON aynı listeyi yeni biçimle taşıyor. CSV SHA-256'sıyla saklanıyor ve ekrandan indiriliyor.
- **2d.** Markdown'da bir bloğun bütün satırlarında aynı olan alanlar (kaynak, kapsam, etiket, not, kullanım notu) blok başında bir kez yazılıyor. Kural genel, destinasyona özel değil.
  - Bunun için bloklar ortak notu tek biçimde yazacak şekilde düzeltildi: konaklama notu, günlük ihtiyaç notu, trafik aylık oran notu.

**Listeden kalkan gürültü** (GÖREV-11 ilk video paketiyle karşılaştırma):

| Gürültü | Eski listede | Örnek satır |
|---|---|---|
| "30A" adından 30 | 41 | K0001 "… W CO HWY 30A …" |
| Sayım noktası numaraları (600141 gibi) | 16 | K0690 "US 98, sayım noktası 600141 …" |
| FDOT yol kimliği 60660100 | 2 | K0001 "… 60660100 numaralı yolu …" |
| Adres numarası 4200 | 2 | K0002 "Destin Belediye Binası'nı (4200 Indian Bayou Trail) …" |
| Karar numarası 2016-23'ten 2016 ve 23 | 2 | K0073 "… 2016-23 sayılı …" |

Yeni ilk video listesinin türleri: `ana` 759, `orneklem` 465, `alt_ceyrek` 156, `ust_ceyrek` 156, `donusum` 118, `pay` 65, `aralik_alt` 2, `aralik_ust` 2.

## Adım 3 — yazar özeti

`<paket>-yazar-ozeti.md`, aynı üretim kimliğiyle, aynı paket nesnesinden yazılıyor (`studio/evidence/summary.py`; veritabanına ayrıca sorgu yok). `data/evidence/` altında SHA-256'sıyla saklanıyor ve ekranda "Yazım için" sütunundan indiriliyor. Türkçe, ABD birimleriyle.

- **Başlık:** ad, soru, tarih, kimlik ve "Bu özet tam paketten türetilmiştir; asıl kanıt tam pakettir; kimlikler aynıdır". Sonra kaynak başına bir satır son çekim, bilinen boşluklar, yayından önce kontrol edilecek satırlar ve kısaltmalar. Kısaltmalar: [KG], [BH], [T], [Y], "—" veri yok, "*" küçük örnek, (n), boş hücre.
- **Bölümler** paketteki sırayla. Her bloğun kullanım notu blok başında bir kez ve aynen. Değere göre sıralama yok; mahalleler batıdan doğuya.
- **Tablolar** görev metnindeki her blok için. Her tablo satırı kendi K kimlik aralığıyla bitiyor.
  - Konaklama fiyatı: ortanca (n), ayrı çeyrek tablosu, "*" küçük örnek, Alys Beach "(kendi envanteri)" diye ayrı.
  - Oda grubu: dönem · grup. İlan sayısı: pencere.
  - İklim: °F yanında °C; istasyon ve dönem tablo başında.
  - Deniz suyu: yıl sayısı ve yılların notu.
  - Kasırga, turist vergisi, trafik, plaj ve mahalle tabloları kendi doğal sıralarıyla.
  - Restoranlar: mahalle özeti ve fiyat seviyesi olan restoranların listesi (ad, mahalle, seviye, ortanca).
  - Günlük ihtiyaç: mil · 1 mil içindeki pay, (n).
- **Diğer satırlar** tek satır: `- K0001 [KG] <Türkçe ifade> — <değer birim>`. Alt satır yalnız not, çelişki, ikincil kaynak ve örnek büyüklüğü için. Adres, SHA-256, çekim kimliği, alıntı ve İngilizce ifade özette yok. Doğrulanamayan satır "videoda kullanılmaz" diye işaretli.
- **Kaynak listesi** sonda: her kaynak bir kez, adı, sahibi, adresi ve K aralıklarıyla. Aynı adres farklı adla yazılmışsa tek kaynak sayıldı.
- **3h testleri** (yalnız fixture). Hepsi geçiyor; ayrıntılı liste "Testler" bölümünde.
  - Her K kimliğinin özette görünmesi; özetteki her sayının paketteki değer olması.
  - Eksik hücrenin "—" olması; kullanım notunun blok başına bir kez ve aynen yazılması.
  - Küçük örnek işaretinin 20 eşiğine uyması; "30A"daki 30 gibi ad ve adres sayılarının listeye girmemesi.
  - CSV'nin JSON listesiyle aynı olması; özet ve CSV'nin pakete bağlı, SHA-256'lı saklanması.

### Boyutlar (gerçek veri, 10 Ekim 2026)

KB = 1024 bayt.

| | GÖREV-11 | GÖREV-12 |
|---|---|---|
| İlk video · Markdown | 924.476 bayt (903 KB) | 477.442 bayt (466 KB) |
| İlk video · JSON | 1.705.468 bayt | 1.691.126 bayt |
| İlk video · yazar özeti | — | 112.704 bayt (110 KB; hedef ≤100 KB) |
| İlk video · sayı listesi (CSV) | Markdown'ın içindeydi | 78.543 bayt (77 KB) |
| İlk video · satır / sayı | 732 / 3.003 | 843 / 1.723 |
| Rosemary Beach · Markdown | 132.764 bayt (130 KB) | 56.358 bayt (55 KB) |
| Rosemary Beach · JSON | 323.905 bayt | 332.664 bayt |
| Rosemary Beach · yazar özeti | — | 28.741 bayt (28 KB; hedef ≤30 KB) |
| Rosemary Beach · sayı listesi (CSV) | Markdown'ın içindeydi | 15.890 bayt (16 KB) |
| Rosemary Beach · satır / sayı | 174 / 556 | 179 / 385 |

**Satır sayısı neden arttı:**
- Restoran bloğu mahalle başına seviye ($–$$$$), çevrimiçi rezervasyon ve çocuk menüsü satırlarını ayrı veriyor. Fiyat seviyesi olan restoranların listesi eklendi. İlk video için 52 → 170.
- Referans satırları 156 → 149 oldu: ilk video şablonunda iki kez çağrılan 7 satır (30A tanımı ve havalimanları) bir kez kaldı. Hiçbir referans satırı kaybolmadı (149 benzersiz satır aynı).
- Rosemary paketine plaj hukukunun video özeti eklendi; oynak konu listesi boş kalmasın diye.

**İlk video özeti neden 100 KB'ı aştı:** içerik düşürülmeden ulaşılan en küçük biçim 110 KB.
- Kalan büyüklüğün dağılımı:
  - Satır maddeleri ~31 KB; bunların çoğu 149 referans satırının Türkçe ifadesi.
  - Tablolar ~27 KB.
  - Satır notları ~17 KB.
  - Kaynak listesi ~16 KB (resmî belgelerin uzun adları ve sorgu adresleri).
  - Kullanım ve ortak notlar ~12 KB.
- Notların büyük kısmı araştırma geçmişi; "GÖREV-07'de bulunamadı, GÖREV-08'de tarayıcıda açıldı" gibi.
- Hedefin altına inmenin yolu referans tablosundaki bu notları kısaltmak. Bu editoryal bir karar olduğu için yapılmadı.

**Denenen sadeleştirmeler:**
- Aynı not blok başında bir kez yazıldı. Birden çok notta tekrarlanan uzun cümle de bir kez yazıldı; örneğin park sayfalarının erişim geçmişi 6 kez, okul seçimi cümlesi 5 kez tekrar ediyordu.
- Satırdan satıra değişen kısa notlar tabloda "Not" sütununa alındı.
- Satır başına aynı olan örnek büyüklüğü ayrı (n) sütununa alındı.
- km karşılıkları özette gizlendi; tam pakette duruyor.
- Aynı adresli kaynaklar birleştirildi.
- Yayından önce listesindeki ifade 100 karakterle sınırlandı.

## Adım 4 — kararlar ve oynak konular

- **4a.**
  - Beş okul satırının notuna yöneticinin cümlesi "Video dili:" diye eklendi (`thirty_a_references.csv`; tablo doğrulayıcısı temiz, yalnız bu beş satır değişti). Paket bu kısmı nottan ayırıp kullanım notuna ekliyor: "… Video dilinde 'örneğin Atlanta bölgesindeki Gwinnett County okulları' denir; resmî öğrenci sayısıyla doğrulanmadıkça 'en büyük okul bölgesi' denmez. (M9)".
  - M9'a okul kararı ve "Video dili:" not kuralı yazıldı. M13'e kural yazıldı: "en yakın resmî acil servis bölge kutusunun dışındaysa notuyla eklenir". HCA ve CVS kararı da M13'te.
- **4b.** Konaklama notu blok başında bir kez ve sade: "Fiyatların %94'ünde sitenin gösterdiği toplam vergileri ve ücretleri içeriyor; kalanında sitenin toplamı kalemlerle doğrulanamadı."
  - Pay üretim anında çekimden hesaplanıyor (`agency_rates.total_counts`).
  - Türkçe ek, yüzdenin okunuşuna göre seçiliyor (%94'ünde, %90'ında; test).
- **4c.** Şablonlara `oynak_konular` alanı eklendi; iki şablonda da `plaj-hukuku`. Paketin ve özetin başında K kimliği, kısa ifade ve yeniden kontrol tarihiyle "Yayından önce kontrol edilecek satırlar" var.

**Yayından önce kontrol listesi** (gerçek veri paketlerinden):

İlk video, 18 satır:

| K | Referans satırı | Durum | Yeniden kontrol |
|---|---|---|---|
| K0069 | hukuk-anayasa-islak-kum | doğrulandı | 2027-04-10 |
| K0070 | hukuk-walton-2016-karar | doğrulandı | 2027-04-10 |
| K0071 | hukuk-2018-kanun-surec | doğrulandı | 2027-04-10 |
| K0072 | hukuk-dava-1194 | doğrulandı | 2027-04-10 |
| K0073 | hukuk-dava-sonuc-2024 | doğrulandı | 2027-04-10 |
| K0074 | hukuk-2025-kaldirma | doğrulandı | 2027-04-10 |
| K0075 | hukuk-2025-ecl | doğrulandı | 2027-04-10 |
| K0076 | hukuk-2025-etki | doğrulandı | 2027-04-10 |
| K0077 | hukuk-2026-temyiz | doğrulandı | 2027-04-10 |
| K0078 | hukuk-2026-ilce-tutum | doğrulandı | 2027-04-10 |
| K0079 | hukuk-2026-yeni-karar-yok | doğrulandı | 2027-04-10 |
| K0080 | hukuk-gecis-alani-turizm | çelişkili | 2027-04-10 |
| K0081 | hukuk-iddia-ozel-plaj-kalmadi | doğrulanamadı | 2027-04-10 |
| K0082 | hukuk-video-ozet | doğrulandı | 2027-04-10 |
| K0781 | timpoochee-uzunluk-liste | çelişkili | 2027-10-07 |
| K0782 | timpoochee-uzunluk-rehber | çelişkili | 2027-10-07 |
| K0823 | erisim-ada-bolgesel | çelişkili | 2027-04-10 |
| K0838 | tarih-seaside-dpz | çelişkili | 2027-10-10 |

Rosemary Beach, 1 satır: K0007 · hukuk-video-ozet · doğrulandı · 2027-04-10.

## Adım 5 — deneme, gerçek veri, okuma, belgeler

1. **Geçici deneme.** Gerçek veritabanı salt okunur kopyalandı (`work/gorev-12/deneme/`). İki paket, yazar özetleri ve CSV'ler birlikte üretildi; boyutlar yukarıdaki gibi. Dört dosya türü de SHA-256 doğrulamasıyla okundu.
2. **Geçiş denemesi.** Şema değişmedi (14), bu yüzden geçiş denemesi gerekmedi. Eklerin adı ve SHA-256'sı paketin JSON'unda; JSON'un SHA-256'sı zaten kayıtta.
3. **Gerçek veri.**
   - Uygulama kapalıyken `data/` tam yedeği alındı: `work/yedek/20261010-1739/`, 45.407 dosya, 1,32 GB; kopya ve kaynak SHA-256 ile doğrulandı.
   - Uygulama gerçek veriyle açıldı (port 8773). "Kanıt paketi" ekranında önce "30A'ya ilk kez gidecekler için tam karar rehberi", sonra "Mahalle rehberi · Rosemary Beach" seçilip "Paketi üret"e basıldı.
   - Dört indirme bağlantısı iki paket için de 200 döndü; eski paketin yazar özeti 404 ("eski üretim"). Uygulama düzgün kapandı (kod 3).
   - Toplayıcı çalışmadı. GÖREV-11 paketleri silinmedi.

| Gerçek veritabanı | Önce | Sonra |
|---|---|---|
| Şema | 14 | 14 |
| `integrity_check` | ok | ok |
| `foreign_key_check` | boş | boş |
| Toplam satır (61 tablo) | 165.240 | 165.242 |
| `evidence_packs` | 2 | 4 |
| Diğer tablolar | — | değişmedi |
| Çekim / kaynak | 30 / 16 | 30 / 16 |
| `data/evidence/` dosya | 4 | 12 |

Yeni paketler: ilk video `bb8ea220be894701b82d16e7d948af24`, Rosemary Beach `0e0f01a360914eee905bb4a9bd51ba21`. Teslim klasöründeki kopyaların SHA-256'sı kayıtla (Markdown, JSON) ve JSON'daki değerle (özet, CSV) uyuşuyor.

4. **Özeti baştan sona okudum.** İki özeti de okudum. Bulunan sorunlar ve yapılanlar aşağıda.

**Düzeltilenler:**

| Sorun | Yapılan |
|---|---|
| Birden çok sayı taşıyan dolar değerleri birimini kaybediyordu ("$5 / 4 / 2"; "(araç / tek kişilik araç / yaya …)" düşüyordu) | Tek sayıda "$500 (üst sınır)", çok sayıda "5 / 4 / 2 USD (araç / …)" |
| Çeyrek hücrelerinde birim iki kez yazılıyordu (çalışma sırasında çıkan hata) | Tablo başlığındaki birim yeterli: "$2,240–$3,823" |
| Deniz suyu hücresinde °F yazmıyordu ("60.2 / 15.7 °C") | Karşılık gösterilen hücrede asıl birim de yazıyor: "60.2 °F / 15.7 °C" |
| Tablodaki boş hücrelerin anlamı yazmıyordu | Kısaltmalara "boş hücre: tam pakette o hücre için satır yok" eklendi |
| Trafik notu bir CSV sütun adı söylüyordu | Not sadeleşti: "Oran = 1 / SF; SF, FDOT haftalık mevsim faktörlerinin gün ağırlıklı ay ortalamasıdır." Ay ortalaması tabloda ayrı sütunda (değerler değişmedi) |
| Notlarda adres ve yerel dosya yolu vardı (`work/gorev-11/...`) | Özette "adres tam pakette" ve "yerel kayıt" yazıyor; tam paket aynen |
| Aynı uzun cümle birçok notta tekrarlanıyordu | Blok başında bir kez. İlk denemede "Çelişki sürüyor." gibi kısa cümleler bağlamından kopuyordu; kısa cümle artık önceki cümleyle birlikte taşınıyor |
| Satırdan satıra değişen kısa notlar blok başında uzun bir liste oluyordu | Tabloda "Not" sütunu (deniz suyu yılları, kasırgaların en yüksek rüzgârı, Rosemary restoranlarının seviye nedeni) |
| Aynı belge iki adla iki kez listeleniyordu (Senato analizi, temyiz kararı, 2025 ziyaretçi çalışması) | Aynı adres tek kaynak |
| Acil sağlık noktalarının kaynağı yalnız "kurumun kendi sitesi" diye görünüyordu | "Acil sağlık noktaları · kurumun kendi sitesi" |
| Rosemary paketinin bilinen boşlukları başka mahalleleri sayıyordu (Gulf Place küçük örnek, Alys Beach) ve pakette olmayan doğrulanamayan satırları listeliyordu | Mahalle paketinde yalnız o mahallenin boşlukları ve paketteki satırlar |
| Yayından önce listesinde çelişki notu tam yazılıyor, aşağıda tekrar ediyordu | Listede "çelişkili (çelişki notu satırın altında)" |
| İklim tablosunda istasyon, yağışlı gün sütununda eşik yazmıyordu | "Kapsam: Destin–Fort Walton Beach Havalimanı …; 1991–2020", "Yağışlı gün (≥0.10 inç)" |

**Düzeltilmeyenler** (veri ya da karar konusu):
- Edward's Fine Food & Wine'ın saatleri ", Tu 17:00-21:00 …" diye virgülle başlıyor. Sitenin verisinde pazartesi boş; restoran çekiminden geliyor (GÖREV-10). Paket kaynağın söylediğini yazıyor.
- Havalimanı uzaklıklarının referans değeri km ("21.5 km (kuş uçuşu)"); mil Türkçe ifadede var. Özet yeni sayı hesaplamadığı için paketteki km değerini gösteriyor. Referans tablosunda değerin mile çevrilmesi ayrı bir iş.
- Rosemary'nin tür tablosunda "bilinmeyen kategori 9" sütunu var. Book>Direct'in adı olmayan kategorisi; konaklama verisinden geliyor.
- Acil sağlık tablosunun başında "Kapsam: bölge kutusu" yazıyor. Kutu dışındaki Panama City Beach noktası (K0773) bunu kendi notunda söylüyor.
- Ekrandaki paket listesinde mahalle, seçili şablon "ilk video"yken kimliğiyle ("rosemary-beach") görünüyor. Ad yalnız seçili şablonun seçeneklerinden okunuyor; GÖREV-11'den kalma küçük bir görünüm konusu.

5. **Belgeler.**
   - M14: sayı listesi kuralı, ayrı CSV, yazar özeti, oynak konular, satır alanları, API ve ekran.
   - M13: bölge kutusu dışındaki acil servis kuralı; HCA ve CVS kararı.
   - M9: okul kararı, "Video dili:" not kuralı, plaj hukuku her videodan önce kontrol, trafik notu ve sütunu.
   - M9'da GÖREV-11'den kalma bir bozukluk düzeltildi: trafik paragrafının ortasına konu tablosunun bir kopyası yapışmıştı.
   - `CALISMA_MANTIGI.md`, `README.md`, DEVIR 05 ve 02 güncel satırları (stable v0.14.0, aktif dal gorev-12).

## Testler

- Python: 733 test (GÖREV-11: 716). Frontend: 60 test (59). Tam takım art arda 3 kez geçti: 733 passed (1 bilinen uyarı: Starlette TestClient / httpx) ve 60/60 frontend, üç turda da (113 s, 111 s, 109 s).
- Testler canlı ağa bağlanmıyor; yeni testler sentetik fiyat özeti ve boş veritabanıyla çalışıyor.
- Yeni ya da değişen Python testleri (`tests/test_evidence.py`):
  - Sayı listesinin yalnız yapılandırılmış alanlardan gelmesi ve trafik satırlarında yol adı ve sayım noktası sayısının girmemesi.
  - Referans satırının yalnız değer alanıyla girmesi ("60660100" ve "30A" ifadede, listede yalnız 18.561).
  - Konaklama notunun blokta tek olması ve %94 cümlesi; yüzde ekleri.
  - Her K kimliğinin özette görünmesi; özetteki her sayının paketteki değer olması.
  - Eksik hücre "—", küçük örnek "*", kendi envanteri etiketi.
  - Kullanım notunun blok başına bir kez ve aynen yazılması; özette adres, SHA-256 ve alıntı olmaması.
  - Ortak not cümleleri; birim yazımı.
  - CSV = JSON; özet ve CSV'nin pakete bağlı, SHA-256'lı saklanması; değişmiş ekin reddi; eski üretimin eksiz görünmesi.
  - Oynak konular ve çelişkili satırların paketin ve özetin başında olması; API indirmeleri.
- Frontend: "Yazım için" bağlantılarının yalnız eki olan pakette görünmesi.

## Beklenmeyen durumlar

- M9'da GÖREV-11'den kalma metin bozukluğu (yukarıda; düzeltildi).
- Okul notunu eklerken tabloyu doğrulayıcının okuyucusuyla yeniden yazmak `park-topsail-saat` satırındaki bir boşluğu da değiştiriyordu. Fark kontrolü bunu yakaladı. Dosya ham CSV olarak düzenlendi; yalnız beş okul satırı değişti.
- Trafik tablosu GÖREV-11 betiğinin kopyasıyla yeniden yazıldı. Değerlerin hiçbiri değişmedi (68 satır karşılaştırıldı; yalnız `not` sütunu farklı).
- Bilgisayarda başka projelerin Python süreçleri çalışıyordu (Housing Atlas işçisi, Blender bağlantısı). Gerçek veriye dokunmadan önce bu uygulamanın kapalı olduğu süreç listesinden doğrulandı.

## Yönetici kararlarının işlenişi

1. Kutu dışındaki acil servis (Ascension, Panama City Beach) kabul edildi; kural M13'te.
2. HCA ve CVS "bu bilgisayardan okunamadı" olarak kaldı; başka yol denenmedi (M13).
3. Küçük örnek eşiği 20 (kod ve M14; test eşiğe göre).
4. Okul bölgesi seçimi "bizim seçimimiz"; video dili cümlesi beş okul satırında ve M9'da.
5. Plaj hukuku satırları her videodan önce yeniden kontrol edilecek: `oynak_konular` ve "Yayından önce kontrol edilecek satırlar" (M9, M14).
6. Paket boyutu bu görevde çözüldü: Markdown 903 KB → 466 KB; sayı listesi ayrı dosyada; yazar özeti 110 KB.
7. main ve etiket Adım 1'de alındı.

## Teslim dosyaları

`docs/gorevler/GOREV-12/`:
- `GOREV.md`, `RAPOR.md`
- `kanit-paketi-ilk-video.md`, `.json`, `-yazar-ozeti.md`, `-sayilar.csv`
- `kanit-paketi-rosemary-beach.md`, `.json`, `-yazar-ozeti.md`, `-sayilar.csv`
- `kanit-paketi-ekrani.png`

Paket dosyalarının hepsi gerçek veriden üretildi.

## Dal CI

Kod ve teslim commit'i `f6041d1` için dal CI çalışması 38061119283: başarılı (https://github.com/bemonths/tatilya/actions/runs/38061119283). Bu rapor satırını ekleyen son commit yalnız raporu değiştirir.
