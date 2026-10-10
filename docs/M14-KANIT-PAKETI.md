# M14 — Kanıt paketi

Tarih: 10 Ekim 2026 · Görev: GÖREV-11, GÖREV-12 (yazar özeti, ayrı sayı listesi, oynak konular) · Dal: `gorev-12-yazar-ozeti` · Şema `14` (GÖREV-12'de değişmedi) · Uygulama `0.14.0` · Paket biçimi `30a-studio-kanit-paketi/2`

## Amaç

Bir videonun (ya da makalenin) ana sorusuna, veritabanındaki ve referans tablosundaki kanıtı tek bir okunur dosyada toplamak: her satır kaynağı, etiketi ve kullanım notuyla. Aynı üretimden iki dosya daha çıkar (GÖREV-12): metni yazan kişinin çalışacağı kısa **yazar özeti** ve metindeki her sayının karşılaştırılacağı **sayı listesi** (CSV). Asıl kanıt tam pakettir; özet ve liste ondan türetilir, kimlikler aynıdır. **Paket yorum, tavsiye ya da sıralama içermez**; karar editoryal katmandadır (KONSEPT).

## Yapı

- **Genel çekirdek (`studio/evidence/`)** — destinasyondan bağımsız:
  - `templates.py`: şablon dosyasını okur ve doğrular; parametreleri çözer; blok tanımlarındaki `{parametre}` yerlerini doldurur.
  - `blocks.py`: yeniden kullanılabilir veri blokları (aşağıda), satır biçimi, etiketler, kullanım notları.
  - `pack.py`: paketi üretir (bölümler, satır numaraları `K0001…`), başlığı (üretim tarihi, kaynakların son çekimi, bilinen boşluklar, yayından önce kontrol edilecek satırlar), sayı listesini (JSON alanı ve CSV), Markdown'ı ve saklamayı yapar.
  - `summary.py`: yazar özetini aynı paket nesnesinden yazar (veritabanına yeniden sorgu yapmaz).
- **Destinasyon tarafı (`studio/destinations/`)** — şablonlar ve dosyalar:
  - `thirty_a_evidence/*.json`: 30A şablonları (profil sabiti `EVIDENCE_TEMPLATES`).
  - `thirty_a_references_tr.csv`: referans tablosundaki her satırın Türkçe ifadesi (`REFERENCE_TRANSLATIONS`); tablonun kendi ifadesi İngilizce kalır ve pakette "kaynak satırının İngilizce ifadesi" olarak yer alır.
  - Okunan diğer profil dosyaları: `REFERENCE_TABLE`, `TRAFFIC_TABLE`, `TDT_COLLECTIONS`, `BEACH_NEIGHBORHOOD_MAPPING`.

Şablon yapısı ileride **bölge × karar × dönem × gezgin tipi** birleşimlerine genişleyecek şekilde kuruldu: her şablon `dimensions` alanında bu dört boyutu taşır, mahalle bir parametredir ve bloklar parametreyle süzülür. Bu görevde iki şablon yazıldı.

## Şablon biçimi

```json
{
  "key": "mahalle-rehberi",                 // küçük harf, rakam, tire
  "version": "1",
  "title": "Mahalle rehberi",
  "question": "Videonun ana sorusu",
  "dimensions": {"bolge": "mahalle", "karar": "…", "donem": "…", "gezgin_tipi": "…"},
  "oynak_konular": ["plaj-hukuku"],          // her videodan önce yeniden kontrol edilecek referans konuları (GÖREV-12)
  "parameters": [{"key": "mahalle", "label": "Mahalle", "kind": "region"}],
  "sections": [
    {"key": "plaj", "title": "Plaj erişimleri", "question": "Bölümün sorusu",
     "blocks": [{"block": "beach_accesses", "region": "{mahalle}"},
                {"block": "references", "topics": ["plaj-erisimi"], "match": "{mahalle_adi}"}]}
  ]
}
```

- Zorunlu alanlar: `key`, `version`, `title`, `question`, `sections`; her bölümde `key`, `title`, `question` ve en az bir blok.
- `oynak_konular` (isteğe bağlı): değeri sık değişebilen konuların referans konu adları (M9 `konu`). Bu konuların satırları ve bütün çelişkili satırlar paketin ve özetin başında "Yayından önce kontrol edilecek satırlar" listesine girer (aşağıda).
- Parametre türü şimdilik yalnız `region` (destinasyonun kanonik mahallelerinden biri). `{mahalle}` mahalle kimliğiyle (`rosemary-beach`), `{mahalle_adi}` adıyla (`Rosemary Beach`) doldurulur. Tanımlanmamış parametreye başvuran, bilinmeyen blok adı kullanan ya da bölüm anahtarını iki kez kullanan şablon okunmaz (nedeniyle).

## Veri blokları

| Blok | Okuduğu | Satırlar | Etiket | Kullanım notu |
|---|---|---|---|---|
| `neighborhoods` | son mahalle çekimi | dizindeki kayıt sayısı, kapsamdaki mahalle sayısı, mahalle başına dizin kaydı ve etiketleri | kaynak gerçeği; mahalle sayısı türetilmiş | M7 metin kullanım notu |
| `beach_accesses` | son plaj çekimi + eşleme dosyası | listedeki erişim sayısı; mahalle başına kaynaklı eşlemeyle ve yaklaşık eşlemelerle erişim sayısı; `region`/`list` ile erişimlerin adları ve yöntemleri | türetilmiş / yaklaşık | M7 eşleme yöntemi kuralları |
| `beach_features` | son plaj çekimi | ADA olanağı ve plaj tekerlekli sandalyesi yazılı erişim sayısı ve listesi | kaynak gerçeği | M7 (olanaklar, GÖREV-11) |
| `references` | referans tablosu | `topics`, `ids`, `match` (ifade ya da değerde geçen ad) ile seçilen satırlar; yerine geçilmiş satırlar dışarıda; adı verilen ama tabloda olmayan satır "veri yok" | kaynak gerçeği; notunda "türetilmiş"/"bizim hesabımız" geçen satır öyle | M9 durum kuralları; çelişki notu ayrı alanda (`celiski_notu`); notun "Video dili:" kısmı kullanım notuna eklenir (GÖREV-12) |
| `climate_months` | son NCEI normalleri | kıyı istasyonunun ay ay en yüksek/en düşük sıcaklık (°F, °C), yağış (inç, mm), yağışlı gün, 90 °F üstü gün | kaynak gerçeği | M8 |
| `sea_water` | son NDBC çekimi | ay ay deniz suyu ortalaması (°F, °C), kullanılan yıl sayısı | bizim hesabımız | M8 |
| `storms` | son HURDAT2 çekimi | `from`–`to` sezonlarında `radius_nmi` dairesinde kasırga ve tropikal fırtına sayısı, aylara göre, fırtına başına en yakın geçiş | bizim hesabımız | M8 (1991–2025, dönem söylenir) |
| `tdt_season` | `TDT_COLLECTIONS` | son `years` tam mali yılda ayın yıllık tahsilattaki payı (%2 payından) | bizim hesabımız | M9 (TDT) |
| `lodging_inventory` | son Book>Direct çekimi | mahalle × pencere görünen ilan sayısı; `detail` ile tür ve oda dağılımı | kaynak gerçeği | M10 |
| `lodging_prices` | son kiralama şirketi fiyat çekimi | mahalle × pencere 7 gecelik toplam fiyat ortancası, çeyrekler ek değer olarak, örneklem; 20'den az fiyatlı ilan "küçük örnek" (`kucuk_ornek`); yalnız şirketin kendi envanteri olan mahalle tablolarda "(kendi envanteri)" diye ayrı; blok notu bir kez ve vergi payı üretimde hesaplanır ("Fiyatların %94'ünde …") | bizim hesabımız | M11 |
| `lodging_bedrooms` | aynı | oda grubuna göre ortanca (`months` ile seçilen pencereler) | bizim hesabımız | M11 |
| `restaurants` | son işletme siteleri çekimi | mahalle başına restoran sayısı, seviyesi hesaplanan sayı ($…$$$$), çevrimiçi rezervasyon ve çocuk menüsü sayısı; `list: true` ile restoran başına seviye, rezervasyon, çocuk menüsü, saatler, ana yemek ortancası; `list: "seviyeli"` ile yalnız fiyat seviyesi olan restoranlar (ad, mahalle, seviye, ortanca) | kaynak gerçeği; seviye ve ortanca bizim hesabımız | M12 |
| `daily_needs` | son günlük ihtiyaç çekimi | mahalle × kategori kuş uçuşu mesafe ortancası (mil, km), 1 mil içindeki pay ek değer olarak; `list_points` ile kategorideki noktalar | bizim hesabımız | M13 |
| `traffic` | `TRAFFIC_TABLE` | `kinds`: `aadt` (sayım noktası başına 2025 AADT), `season` (kategori başına aylık oran ve yoğun sezon haftaları, haftaların başı ve sonu ek değer); `categories` ile süzme | kaynak gerçeği; aylık oran bizim hesabımız | M9 (trafik, GÖREV-11) |

Bir blok kendi kaynağının **son başarılı çekimini** okur; çekim yoksa ya da bir hücre boşsa satır düşürülmez, **"veri yok"** satırı nedeniyle yazılır (ör. "Bu çekimde bu kategori yok (kategori ayrımından önceki çekim)", "Bu hücrede fiyatı okunan ilan yok").

## Kanıt satırı

Her satır (JSON'da bütün alanlarıyla):

- `id` (`K0001…`), `bolum`, `blok`
- `ifade` — Türkçe ifade; referans satırlarında ayrıca `ifade_en` (tablonun İngilizce cümlesi, videoda söylenebilecek biçim)
- `deger`, `birim` — ABD birimleri (°F, inç, mil, USD); `deger_ek` — °C, mm, km karşılığının okunur metni (dönüşüm bizim hesabımız)
- `ek_degerler` — satırın değerden başka sayıları, ayrı alanlar olarak: `[{"tur", "deger", "birim"}]`; `tur` şunlardan biri: `alt_ceyrek`, `ust_ceyrek`, `orneklem`, `pay`, `aralik_alt`, `aralik_ust`, `donusum` (GÖREV-12). İfade metni değişmedi; sayılar ifadeden okunmaz, bu alanlardan okunur.
- `kapsam` — mahalle, ilçe, istasyon ve dönem
- `kaynak` — ad, url, belge tarihi, erişim tarihi, çekim kimliği, SHA-256 (çekimin ham dosyası ya da referans belgesi); referans ve trafik satırlarında satır kimliği
- `etiket` — **kaynak gerçeği** (kaynak bunu söylüyor), **bizim hesabımız** (kaynak verisinden hesapladığımız sayı: ortanca, pay, dönüşüm, sayım), **türetilmiş** (birden çok kaynaktan ya da bizim kuralımızla çıkardığımız sonuç: mahalle eşlemesi, kapsam kuralı, özet), **yaklaşık** (yaklaşık konum ya da eşleme)
- `orneklem` — örnek büyüklüğü (ilan, yıl, fırtına sayısı vb.)
- `kullanim_notu` — verinin M belgesindeki video dili kuralı (sonunda belge adı, ör. "(M11)"); M belgesinde olmayan not yazılmaz, eksikse önce M belgesine eklenir
- `alinti` — kaynağın İngilizce kısa alıntısı (varsa; yalnız doğrulama içindir)
- `not`, `durum` (`var` ya da `veri yok`); `celiski_notu` (çelişkili referans satırında); `kucuk_ornek` (eşiğin altında örnek)
- `tablo` — yazar özetinde satırın hangi tabloya, hangi satır ve sütuna düştüğü (`ad`, `satir`, `sutun`, `hucreler`, `baslik`); tablo dışı satırda yok

## Başlık ve sonu

- Başlık: üretim tarihi, destinasyon, şablon ve sürüm, "bu paket yorum ve tavsiye içermez" notu, birim kuralı, boyut (bölüm, kanıt satırı, sayı, "veri yok" satırı); okunan her kaynağın son çekim tarihi, çekim kimliği, sonraki önerilen tarih ve zamanı gelip gelmediği (`/api/refresh` kuralı); **bilinen boşluklar** veriden hesaplanır: fiyatı okunamayan kiralama şirketleri (okuyucusu olmayan alan adları ve ilan sayıları, ör. 360blue, realjoy), engel yüzünden okunamayan ilan sayısı, küçük örnekli mahalleler (pencere başına ortanca 20'den az fiyatlı ilan), fiyatı tek şirketin kendi envanterinden gelen mahalle (Alys Beach), seviyesi hesaplanamayan restoran sayısı, OpenStreetMap sınırları, resmî kaynakta doğrulanamayan acil sağlık noktaları, sitesi okunamayan zincir ve kurumlar, doğrulanamayan referans satırları, Book>Direct'in tam envanter olmadığı.
- Başlığın sonunda **Yayından önce kontrol edilecek satırlar** (GÖREV-12): şablonun oynak konularındaki referans satırları ve bütün çelişkili satırlar; her biri K kimliği, kısa ifadesi (en çok 100 karakter) ve yeniden kontrol tarihiyle. 30A'nın iki şablonunda oynak konu `plaj-hukuku`; yönetici kararıyla bu satırlar her videodan önce yeniden kontrol edilir.
- Son: **sayı listesi** — ayrı dosya `<paket>-sayilar.csv` (sütunlar `kanit, tur, deger, birim, etiket`); Markdown'ın sonunda yalnız dosya adı ve satır sayısı yazar, JSON listeyi `checklist` alanında aynı biçimle taşır. Makale yazıldıktan sonra metindeki her sayı bu listeye karşı kontrol edilir; listede olmayan sayı kanıtsızdır.

### Sayı listesi kuralı (GÖREV-12)

- Liste **yalnız yapılandırılmış alanlardan** üretilir: satırın değeri (`ana`, alan `deger`), ek değerleri (`ek_degerler`: çeyrekler, örneklem, pay, aralık başı ve sonu, dönüşüm) ve ek değerlerde yoksa örnek büyüklüğü. İfade metni taranmaz.
- Bu yüzden adlar, adresler, yol ve kimlik numaraları ve dönemler listeye girmez. GÖREV-11'deki gürültü örnekleri: "30A" adından 30, FDOT yol kimliği 60660100, "4200 Indian Bayou Trail" adresinden 4200, FDOT sayım noktası numaraları (600141 gibi), "2016-23" sayılı karardan 2016 ve 23.
- Referans satırları listeye **yalnız tablonun değer alanıyla** girer (değer bir rakam içeriyorsa); ifadedeki diğer sayılar satır metnine karşı kontrol edilir.
- `tur` değerleri: `ana`, `alt_ceyrek`, `ust_ceyrek`, `orneklem`, `pay`, `aralik_alt`, `aralik_ust`, `donusum`. `etiket` satırın etiketidir.

## Çıktı ve saklama

- Bir üretim dört dosyadır: tam paket Markdown (okunur) ve aynı içeriğin JSON'u, yazar özeti (`-yazar-ozeti.md`) ve sayı listesi (`-sayilar.csv`). Markdown'da aynı bloktaki satırların ortak bilgisi (kaynak, kapsam, etiket, not, kullanım notu) blok başında bir kez yazılır (genel kural); JSON her satırda bütün alanları taşır. Sayılar ABD biçimiyle (binlik virgül, ondalık nokta).
- Her üretim uygulamanın normal kullanımıyla `<veri-klasörü>/evidence/<YYYYMMDD-HHMMSS>-<şablon>[-<parametre>]-<kimlik>.md` ve `.json` olarak yazılır; ikisinin SHA-256'sı `evidence_packs` tablosuna kaydedilir (şablon ve sürümü, parametreler, bölüm, satır, sayı ve "veri yok" sayısı). Yazar özeti ve sayı listesi aynı adın sonuna `-yazar-ozeti.md` ve `-sayilar.csv` eklenerek yazılır; adları ve SHA-256'ları paketin JSON'unda `dosyalar` alanındadır (JSON'un SHA-256'sı kayıtta olduğundan şema değişmedi). İndirmede dosyanın SHA-256'sı kayıtla (ekler için kayıtla doğrulanmış JSON'la) karşılaştırılır; uyuşmayan dosya verilmez. GÖREV-12'den önceki üretimlerin eki yoktur; ekranda "eski üretim" yazar.
- API: `GET /api/evidence-templates` (şablonlar, bölüm soruları, parametre seçenekleri), `POST /api/evidence-packs` (`template_key`, `params`; üretir ve saklar), `GET /api/evidence-packs` (saklananlar), `GET /api/evidence-packs/{id}/markdown|json|yazar-ozeti|sayilar`; listede her paketin `ekler` alanı eklerin bulunup bulunmadığını söyler.
- Arayüz: **Kanıt paketi** ekranı (İçerik atölyesi altında): şablon seç, parametre ver, "Paketi üret"; üretilmiş paketler tablosunda "Yazım için" sütununda yazar özeti ve sayı listesi (CSV), "Tam paket" sütununda Markdown ve JSON indirme bağlantıları ve SHA-256.

## Yazar özeti (GÖREV-12)

Metni yazan kişinin tek başına çalışabileceği kısa Markdown dosyası. Kurallar:

- **Aynı üretimden ve aynı paket nesnesinden** yazılır; veritabanına ayrıca sorgu yapılmaz. Özetteki her değer paketteki değerin aynısıdır; biçim (binlik virgül, `$`, `%`, °F yanında °C) tam paketle aynıdır. Türkçe yazılır, ABD birimleriyle; km karşılıkları özette gösterilmez (tam pakette durur).
- Başlık: şablon adı, ana soru, parametreler, üretim tarihi ve kimliği, "Bu özet tam paketten türetilmiştir; asıl kanıt tam pakettir; kimlikler aynıdır" cümlesi; kaynakların son çekimi (kaynak başına bir satır); bilinen boşluklar; yayından önce kontrol edilecek satırlar; kısaltmalar ([KG] kaynak gerçeği, [BH] bizim hesabımız, [T] türetilmiş, [Y] yaklaşık, "—" veri yok, "*" küçük örnek, (n) örnek büyüklüğü, boş hücre: tam pakette o hücre için satır yok).
- Bölümler paketteki sırayla; değere göre sıralama yapılmaz, mahalleler paketteki sırayla (batıdan doğuya). Her bloğun kullanım notu blok başında **bir kez ve aynen** yazılır (blokta birden çok not varsa her biri kendi K kimlikleriyle).
- Sayı serileri tablodur ve **her tablo satırı kendi K kimlik aralığıyla biter**: konaklama fiyatı mahalle × ay "ortanca (n)" ve ayrı çeyrek tablosu, "*" küçük örnek, Alys Beach "(kendi envanteri)" diye ayrı; oda grubu mahalle × (dönem · grup); ilan sayısı mahalle × pencere; iklim ay × ölçü (°F yanında °C, istasyon ve dönem tablo başında); deniz suyu °F/°C ve yıl sayısı; kasırga, turist vergisi, trafik, plaj ve mahalle tabloları kendi doğal sıralarıyla; restoranlar mahalle × ölçü ve fiyat seviyesi olan restoranların listesi; günlük ihtiyaç mahalle × ölçü (mil ve 1 mil içindeki pay, n).
- Tablo dışındaki satırlar tek satırdır: `- K0001 [KG] <Türkçe ifade> — <değer birim>`; alt satır yalnız not, çelişki, ikincil kaynak ve örnek büyüklüğü için. Adres (URL), SHA-256, çekim kimliği, alıntı ve İngilizce ifade özette yoktur (tam pakettedir); notlardaki adresler "adres tam pakette", yerel dosya yolları "yerel kayıt" diye yazılır. Doğrulanamayan satır "videoda kullanılmaz" diye işaretlenir.
- Notlar bir kez yazılır: tablo satırlarının notu ve birden çok satırın paylaştığı not (ya da notların paylaştığı 40 karakterden uzun cümle) blok başında K kimlikleriyle; tablo satırından satıra değişen kısa notlar tabloda "Not" sütununda; tek satırın notu altında.
- Sonda kaynak listesi: her kaynak (aynı adres tek kaynak) bir kez, adı, sahibi ve adresiyle, taşıdığı K kimlik aralıklarıyla.
- **Paketteki hiçbir satır özetten sessizce düşmez**: her K kimliği ya kendi satırıyla ya da bir tablo satırının kimlik aralığıyla görünür (test).
- Hedef boyut: ilk video ≤100 KB, Rosemary Beach ≤30 KB. Aşılırsa içerik düşürülmez; neden rapora yazılır ve biçim sadeleştirilir. GÖREV-12'de ilk video özeti ~110 KB'ta kaldı: kalan büyüklüğün çoğu referans satırlarının notları (araştırma geçmişi: hangi görevde neyin bulunamadığı) ve kaynak listesindeki uzun resmî adresler; bu notların kısaltılması referans tablosunda editoryal bir karardır.

## Yeni şablon nasıl yazılır

1. Destinasyonun şablon klasörüne (`thirty_a_evidence/`) yeni bir JSON dosyası koyun; anahtarı benzersiz olsun.
2. `question` alanına videonun ana sorusunu, `dimensions` alanına bölge, karar, dönem ve gezgin tipini yazın.
3. Parametre gerekiyorsa `{"key": "mahalle", "label": "Mahalle", "kind": "region"}` ekleyin.
4. Her bölüm için bir soru yazın ve yukarıdaki tablodan blokları seçin; mahalleye özgü bölümlerde `region: "{mahalle}"` ya da referanslarda `match: "{mahalle_adi}"` kullanın. Mahalleye özgü olmayan bölümün sorusunda "30A geneli" yazın.
5. Bir bilginin referans tablosunda satırı yoksa önce kaynağıyla satırı ekleyin (M9) ve Türkçe ifadesini `thirty_a_references_tr.csv`'ye yazın; şablon olmayan bir satırı `ids` ile isterse paket "veri yok" yazar.
6. Yeni bir veri türü için blok gerekiyorsa `studio/evidence/blocks.py`'ye genel (destinasyondan bağımsız) bir blok ekleyin; kullanım notunu ilgili M belgesinin video dili bölümünden alın, yoksa önce M belgesine yazın.
7. Testler şablonun okunduğunu ve her bloğun eksik veride "veri yok" yazdığını kontrol eder (`tests/test_evidence.py`).

## 30A şablonları

- **`ilk-video` — "30A'ya ilk kez gidecekler için tam karar rehberi":** 30A nedir ve nerededir; 13 mahallenin karakteri; plaj erişiminin gerçeği (hukuk dahil); plaj kuralları ve güvenlik; hava, deniz suyu ve kasırga; kalabalık ve sezon (turist vergisi deseni, doluluk ve ADR, ziyaretçi kökeni ve okul tatilleri, etkinlikler, trafik mevsim oranları); konaklama maliyeti (mahalle × ay, oda grupları; Alys Beach ayrı etiketli); yemek; araba ve ulaşım (büyük süpermarket, yerel market, eczane, acil servis ve acil bakım mesafeleri ve resmî noktaları, golf arabası ve LSV, park, havalimanları, AADT); erişilebilirlik; pratik bilgiler ve merak açıları.
- **`mahalle-rehberi` (parametre: mahalle) — "Mahalle rehberi":** resmî tanım; plaj erişimleri ve olanakları; konaklama (ilan sayısı, tür ve oda dağılımı, ay ay fiyat, oda grupları); restoranlar (liste, seviye, rezervasyon, çocuk menüsü, saatler); günlük ihtiyaç mesafeleri; mahalleye özgü referanslar; etkinlikler; hava ve sezon (30A geneli, öyle etiketli). İlk üretim Rosemary Beach ile.

## Testler

`tests/test_evidence.py` (GÖREV-12 eklemeleri): sayı listesinin yalnız yapılandırılmış alanlardan gelmesi ve ad, adres, yol numarasının ("30A"daki 30 gibi) listeye girmemesi; referans satırının yalnız değer alanıyla girmesi; CSV'nin JSON listesiyle aynı olması; özet ve CSV'nin pakete bağlı ve SHA-256'lı saklanması, değişmiş ekin reddi, eski üretimin eksiz görünmesi; özette her K kimliğinin görünmesi; özetteki her sayının paketteki değer olması; eksik hücrenin "—" olması; kullanım notunun blok başına bir kez ve aynen yazılması; küçük örnek işaretinin eşiğe uyması; adres, SHA-256 ve alıntının özette olmaması; ortak not cümlelerinin bir kez yazılması; oynak konuların ve çelişkili satırların paketin ve özetin başında olması; vergi payı cümlesi. GÖREV-11'den: profil şablonlarının okunması ve her bloğun bir şablonda kullanılması; geçersiz şablonların nedeniyle reddi; parametre çözme ve doldurma; şablon ya da parametre eksikse üretimin reddi; çekim yokken her çekime dayalı bloğun "veri yok" yazması ve hiçbir bölümün boş kalmaması; kullanım notunun, etiketin ve kaynağın satıra geçmesi (referans durumlarına göre not, çelişki notu, yerine geçilmiş satırların dışarıda kalması); her referans satırının Türkçe ifadesi; tabloda olmayan referans kimliğinin "veri yok" olması; fiyat bloğunda küçük örnek ve kendi envanteri kuralları; sayı kontrol listesinin her satırdaki her sayıyı içermesi; Markdown ile JSON'un aynı satırları taşıması; tarihli dosyalar, SHA-256 ve kayıt; değişmiş dosyanın reddi; API.

## Sınırlar

- Paket her blok için son başarılı çekimi okur; farklı tarihli çekimler bir arada olabilir (başlıkta her kaynağın tarihi yazar).
- Referans satırlarının Türkçe ifadeleri İngilizce ifadenin çevirisidir; kaynağın söylediğinden ileri gitmez, ama video cümlesi İngilizce ifadedir.
- Sayı listesi bir satırın ifadesindeki, notundaki ve kaynağındaki sayıları (tarih, SHA-256) içermez; yalnız değer ve ek değerleri içerir. İfadede geçen bir tarih ya da sayı makalede kullanılacaksa satır metnine karşı kontrol edilir.
- Yazar özeti tam paketin yerine geçmez: kaynak adresi, SHA-256, çekim kimliği, alıntı ve İngilizce ifade yalnız tam pakettedir.
