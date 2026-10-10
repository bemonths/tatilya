# M14 — Kanıt paketi

Tarih: 10 Ekim 2026 · Görev: GÖREV-11 · Dal: `gorev-11-kanit-paketi` · Şema `14` · Uygulama `0.14.0`

## Amaç

Bir videonun (ya da makalenin) ana sorusuna, veritabanındaki ve referans tablosundaki kanıtı tek bir okunur dosyada toplamak: her satır kaynağı, etiketi ve kullanım notuyla; sonunda metindeki her sayının karşılaştırılacağı sayı kontrol listesi. **Paket yorum, tavsiye ya da sıralama içermez**; karar editoryal katmandadır (KONSEPT).

## Yapı

- **Genel çekirdek (`studio/evidence/`)** — destinasyondan bağımsız:
  - `templates.py`: şablon dosyasını okur ve doğrular; parametreleri çözer; blok tanımlarındaki `{parametre}` yerlerini doldurur.
  - `blocks.py`: yeniden kullanılabilir veri blokları (aşağıda), satır biçimi, etiketler, kullanım notları.
  - `pack.py`: paketi üretir (bölümler, satır numaraları `K0001…`), başlığı (üretim tarihi, kaynakların son çekimi, bilinen boşluklar), sayı kontrol listesini, Markdown'ı ve saklamayı yapar.
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
  "parameters": [{"key": "mahalle", "label": "Mahalle", "kind": "region"}],
  "sections": [
    {"key": "plaj", "title": "Plaj erişimleri", "question": "Bölümün sorusu",
     "blocks": [{"block": "beach_accesses", "region": "{mahalle}"},
                {"block": "references", "topics": ["plaj-erisimi"], "match": "{mahalle_adi}"}]}
  ]
}
```

- Zorunlu alanlar: `key`, `version`, `title`, `question`, `sections`; her bölümde `key`, `title`, `question` ve en az bir blok.
- Parametre türü şimdilik yalnız `region` (destinasyonun kanonik mahallelerinden biri). `{mahalle}` mahalle kimliğiyle (`rosemary-beach`), `{mahalle_adi}` adıyla (`Rosemary Beach`) doldurulur. Tanımlanmamış parametreye başvuran, bilinmeyen blok adı kullanan ya da bölüm anahtarını iki kez kullanan şablon okunmaz (nedeniyle).

## Veri blokları

| Blok | Okuduğu | Satırlar | Etiket | Kullanım notu |
|---|---|---|---|---|
| `neighborhoods` | son mahalle çekimi | dizindeki kayıt sayısı, kapsamdaki mahalle sayısı, mahalle başına dizin kaydı ve etiketleri | kaynak gerçeği; mahalle sayısı türetilmiş | M7 metin kullanım notu |
| `beach_accesses` | son plaj çekimi + eşleme dosyası | listedeki erişim sayısı; mahalle başına kaynaklı eşlemeyle ve yaklaşık eşlemelerle erişim sayısı; `region`/`list` ile erişimlerin adları ve yöntemleri | türetilmiş / yaklaşık | M7 eşleme yöntemi kuralları |
| `beach_features` | son plaj çekimi | ADA olanağı ve plaj tekerlekli sandalyesi yazılı erişim sayısı ve listesi | kaynak gerçeği | M7 (olanaklar, GÖREV-11) |
| `references` | referans tablosu | `topics`, `ids`, `match` (ifade ya da değerde geçen ad) ile seçilen satırlar; yerine geçilmiş satırlar dışarıda; adı verilen ama tabloda olmayan satır "veri yok" | kaynak gerçeği; notunda "türetilmiş"/"bizim hesabımız" geçen satır öyle | M9 durum kuralları; çelişki notu satıra yazılır |
| `climate_months` | son NCEI normalleri | kıyı istasyonunun ay ay en yüksek/en düşük sıcaklık (°F, °C), yağış (inç, mm), yağışlı gün, 90 °F üstü gün | kaynak gerçeği | M8 |
| `sea_water` | son NDBC çekimi | ay ay deniz suyu ortalaması (°F, °C), kullanılan yıl sayısı | bizim hesabımız | M8 |
| `storms` | son HURDAT2 çekimi | `from`–`to` sezonlarında `radius_nmi` dairesinde kasırga ve tropikal fırtına sayısı, aylara göre, fırtına başına en yakın geçiş | bizim hesabımız | M8 (1991–2025, dönem söylenir) |
| `tdt_season` | `TDT_COLLECTIONS` | son `years` tam mali yılda ayın yıllık tahsilattaki payı (%2 payından) | bizim hesabımız | M9 (TDT) |
| `lodging_inventory` | son Book>Direct çekimi | mahalle × pencere görünen ilan sayısı; `detail` ile tür ve oda dağılımı | kaynak gerçeği | M10 |
| `lodging_prices` | son kiralama şirketi fiyat çekimi | mahalle × pencere 7 gecelik toplam fiyat ortancası, çeyrekler ifadede, örneklem; 20'den az fiyatlı ilan "küçük örnek"; yalnız şirketin kendi envanteri olan mahalle ayrı etiketli | bizim hesabımız | M11 |
| `lodging_bedrooms` | aynı | oda grubuna göre ortanca (`months` ile seçilen pencereler) | bizim hesabımız | M11 |
| `restaurants` | son işletme siteleri çekimi | mahalle başına restoran sayısı, seviyesi hesaplanan sayı ($…$$$$), çevrimiçi rezervasyon ve çocuk menüsü sayısı; `list` ile restoran başına seviye, rezervasyon, çocuk menüsü, saatler, ana yemek ortancası | kaynak gerçeği; seviye ve ortanca bizim hesabımız | M12 |
| `daily_needs` | son günlük ihtiyaç çekimi | mahalle × kategori kuş uçuşu mesafe ortancası (mil, km), 1 mil içindeki pay ifadede; `list_points` ile kategorideki noktalar | bizim hesabımız | M13 |
| `traffic` | `TRAFFIC_TABLE` | `kinds`: `aadt` (sayım noktası başına 2025 AADT), `season` (kategori başına aylık oran ve yoğun sezon haftaları); `categories` ile süzme | kaynak gerçeği; aylık oran bizim hesabımız | M9 (trafik, GÖREV-11) |

Bir blok kendi kaynağının **son başarılı çekimini** okur; çekim yoksa ya da bir hücre boşsa satır düşürülmez, **"veri yok"** satırı nedeniyle yazılır (ör. "Bu çekimde bu kategori yok (kategori ayrımından önceki çekim)", "Bu hücrede fiyatı okunan ilan yok").

## Kanıt satırı

Her satır (JSON'da bütün alanlarıyla):

- `id` (`K0001…`), `bolum`, `blok`
- `ifade` — Türkçe ifade; referans satırlarında ayrıca `ifade_en` (tablonun İngilizce cümlesi, videoda söylenebilecek biçim)
- `deger`, `birim` — ABD birimleri (°F, inç, mil, USD); `deger_ek` — °C, mm, km karşılığı (dönüşüm bizim hesabımız)
- `kapsam` — mahalle, ilçe, istasyon ve dönem
- `kaynak` — ad, url, belge tarihi, erişim tarihi, çekim kimliği, SHA-256 (çekimin ham dosyası ya da referans belgesi); referans ve trafik satırlarında satır kimliği
- `etiket` — **kaynak gerçeği** (kaynak bunu söylüyor), **bizim hesabımız** (kaynak verisinden hesapladığımız sayı: ortanca, pay, dönüşüm, sayım), **türetilmiş** (birden çok kaynaktan ya da bizim kuralımızla çıkardığımız sonuç: mahalle eşlemesi, kapsam kuralı, özet), **yaklaşık** (yaklaşık konum ya da eşleme)
- `orneklem` — örnek büyüklüğü (ilan, yıl, fırtına sayısı vb.)
- `kullanim_notu` — verinin M belgesindeki video dili kuralı (sonunda belge adı, ör. "(M11)"); M belgesinde olmayan not yazılmaz, eksikse önce M belgesine eklenir
- `alinti` — kaynağın İngilizce kısa alıntısı (varsa; yalnız doğrulama içindir)
- `not`, `durum` (`var` ya da `veri yok`)

## Başlık ve sonu

- Başlık: üretim tarihi, destinasyon, şablon ve sürüm, "bu paket yorum ve tavsiye içermez" notu, birim kuralı, boyut (bölüm, kanıt satırı, sayı, "veri yok" satırı); okunan her kaynağın son çekim tarihi, çekim kimliği, sonraki önerilen tarih ve zamanı gelip gelmediği (`/api/refresh` kuralı); **bilinen boşluklar** veriden hesaplanır: fiyatı okunamayan kiralama şirketleri (okuyucusu olmayan alan adları ve ilan sayıları, ör. 360blue, realjoy), engel yüzünden okunamayan ilan sayısı, küçük örnekli mahalleler (pencere başına ortanca 20'den az fiyatlı ilan), fiyatı tek şirketin kendi envanterinden gelen mahalle (Alys Beach), seviyesi hesaplanamayan restoran sayısı, OpenStreetMap sınırları, resmî kaynakta doğrulanamayan acil sağlık noktaları, sitesi okunamayan zincir ve kurumlar, doğrulanamayan referans satırları, Book>Direct'in tam envanter olmadığı.
- Son: **sayı kontrol listesi** — paketteki her sayı tek satırda: ifade, değer, birim, kanıt satırının kimliği. Bir satırın değeri ve ifadesinde, ek değerinde geçen her sayı (ISO tarihler tek sayı) listeye girer. Makale yazıldıktan sonra metindeki her sayı bu listeye karşı kontrol edilir; listede olmayan sayı kanıtsızdır.

## Çıktı ve saklama

- Tek Markdown dosyası (okunur) ve aynı içeriğin JSON'u. Markdown'da aynı bloktaki satırların ortak bilgisi (kaynak, kapsam, etiket, not, kullanım notu) bir kez yazılır; JSON her satırda bütün alanları taşır. Sayılar ABD biçimiyle (binlik virgül, ondalık nokta).
- Her üretim uygulamanın normal kullanımıyla `<veri-klasörü>/evidence/<YYYYMMDD-HHMMSS>-<şablon>[-<parametre>]-<kimlik>.md` ve `.json` olarak yazılır; ikisinin SHA-256'sı `evidence_packs` tablosuna kaydedilir (şablon ve sürümü, parametreler, bölüm, satır, sayı ve "veri yok" sayısı). İndirmede dosyanın SHA-256'sı kayıtla karşılaştırılır; uyuşmayan dosya verilmez.
- API: `GET /api/evidence-templates` (şablonlar, bölüm soruları, parametre seçenekleri), `POST /api/evidence-packs` (`template_key`, `params`; üretir ve saklar), `GET /api/evidence-packs` (saklananlar), `GET /api/evidence-packs/{id}/markdown|json`.
- Arayüz: **Kanıt paketi** ekranı (İçerik atölyesi altında): şablon seç, parametre ver, "Paketi üret", üretilmiş paketler tablosunda Markdown ve JSON indirme bağlantıları ve SHA-256.

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

`tests/test_evidence.py`: profil şablonlarının okunması ve her bloğun bir şablonda kullanılması; geçersiz şablonların nedeniyle reddi; parametre çözme ve doldurma; şablon ya da parametre eksikse üretimin reddi; çekim yokken her çekime dayalı bloğun "veri yok" yazması ve hiçbir bölümün boş kalmaması; kullanım notunun, etiketin ve kaynağın satıra geçmesi (referans durumlarına göre not, çelişki notu, yerine geçilmiş satırların dışarıda kalması); her referans satırının Türkçe ifadesi; tabloda olmayan referans kimliğinin "veri yok" olması; fiyat bloğunda küçük örnek ve kendi envanteri kuralları; sayı kontrol listesinin her satırdaki her sayıyı içermesi; Markdown ile JSON'un aynı satırları taşıması; tarihli dosyalar, SHA-256 ve kayıt; değişmiş dosyanın reddi; API.

## Sınırlar

- Paket her blok için son başarılı çekimi okur; farklı tarihli çekimler bir arada olabilir (başlıkta her kaynağın tarihi yazar).
- Referans satırlarının Türkçe ifadeleri İngilizce ifadenin çevirisidir; kaynağın söylediğinden ileri gitmez, ama video cümlesi İngilizce ifadedir.
- Sayı kontrol listesi bir satırın notundaki ve kaynağındaki sayıları (tarih, SHA-256) içermez; yalnız ifade, değer ve ek değerdeki sayıları içerir.
