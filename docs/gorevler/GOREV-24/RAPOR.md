# GÖREV-24 — Rapor

Tarih: 17 Kasım 2026 · Dal: `gorev-24-realjoy` (main `f87582c` = `v0.24.0` üzerinden) · Uygulama `0.25.0` · Şema `23` (değişmedi)

## Kısa özet

| Konu | Sonuç |
|---|---|
| main ve etiket | `gorev-23-okuyucular` main'e fast-forward ile alındı (`9ead6a8..f87582c`), `v0.24.0` etiketi konuldu, ikisi push edildi. |
| RealJoy'un fiyat isteği | **`POST /ajax/quote`** (sayfanın tarih formu). GET bir fiyat adresi yok. |
| Okuyucu | **Yazılmadı** (görev kuralı: fiyat yalnız POST ile geliyorsa okuyucu yazılmaz). RealJoy "fiyatı okunamayan şirketler"de, yeni nedeniyle. |
| Yönetici kararı (17 Kasım 2026, sohbette) | RealJoy'un fiyat sorgusu izinle **GÖREV-25**'te yapılacak; bu görevde okunmayan olarak kalır. |
| Eşleme (çevrimdışı) | Liste sayfasının verdiği 12 ev × 61 Book>Direct ilanı: **1 ilan** adres kuralıyla bağlanıyor. |
| Gerçek veri | **Değişmedi** (yapılandırma satırı eklenmedi; yedek gerekmedi). Kiralama fiyat çekimi başlatılmadı. |
| Çekim tahmini | Değişmedi: kiralama şirketleri yaklaşık **10 saat**, hepsi birlikte yaklaşık **11 sa 4 dk**. |

**Tamamlanamayan adımlar:** Adım 2.4'ün fiyat adresi doğrulaması ve Adım 3 (okuyucu, eşleme, çekim, 429 kuralı ve onların testleri) —
fiyat yalnız POST ile geldiği için kural gereği yapılmadı; yönetici bunları GÖREV-25'e bıraktı. Adım 4.1'in yapılandırması da bu yüzden
girmedi.

Programın hiçbir Claude adımı çalıştırılmadı, alt ajan kullanılmadı, zamanlanmış görev oluşturulmadı, Housing Atlas ve Rota Stüdyo
depolarına ve talimat dosyalarına dokunulmadı. **realjoy.com'a Claude Code tarafından hiç canlı istek yapılmadı;** bütün RealJoy
sayfaları kullanıcının Chrome'undaki eklentinin deneme okumasıyla (kullanıcı düğmeye bastı) alındı. Proxy kullanılmadı.

---

## Adım 1 — main ve dal

- Program açıktı (kullanıcının açtığı oturum); kapanması beklendi.
- `gorev-23-okuyucular` main'e fast-forward ile alındı (`9ead6a8..f87582c`), `v0.24.0` açıklamalı etiketi konuldu ("v0.24.0 — GÖREV-23:
  30A Beach Girls haftalık kirası (AvantStay takvimi), Vacasa tam liste, LocalVR incelemesi (şema 23)"); ikisi push edildi.
- `gorev-24-realjoy` güncel main'den açıldı. `studio/destinations/thirty_a_claude/` altında kullanıcı değişikliği yoktu; "talimat"
  commit'i gerekmedi.

---

## Adım 2 — Fiyat isteği

### Kayıtlar

| Kayıt (`data/raw/eklenti/20261117/`) | Ne | HTTP | Boyut |
|---|---|---|---|
| `125425-8fbe6b7c` | İlan sayfası "Sea La Vie Seaside Main House" | 200 | 311 KB |
| `125337-e486b52f` | 30A ilan listesi (ilk deneme) | **429** | 3,6 KB |
| `162317-6b22a8c5` | `/bookingEngine/javascripts/pdp/z_pdp.js?v=17` | 200 | 22 KB |
| `162345-2d71f10a` | `/bookingEngine/javascripts/pdp/datepicker.js?v=17` | 200 | 25 KB |
| `162412-ea2e093f` | `/bookingEngine/javascripts/be/z_global.js?v=17` | 200 | 20 KB |
| `162516-206f0cd6` | 30A ilan listesi (ikinci deneme) | 200 | 566 KB |

İlan sayfasının kaydı sayfanın görünen hâlidir (DOM); sayfanın betikleri içinde değildir. Fiyatın hangi istekle geldiği betiklerdedir.
Bu yüzden ilan sayfasının yüklediği üç betik (adresleri kayıttan) deneme listesine **bir kez** eklendi ve kullanıcıdan deneme okumasını
yeniden çalıştırması istendi (izin verilen iki istekten **birincisi**). Kullanıcı çalıştırdı; RealJoy doğrulama gösterdi, kullanıcı
geçti; 10 sayfanın 10'u okundu. Betikler okunduktan sonra listeden çıkarıldı.

### Bulunanlar

- **Evin kimliği:** `propertyID` = sitenin birim kodu (`data-unitcode`; örnek ev **1806**). Track'teki ilan numarası ayrıca
  (`item_id` / `mpn`: 6198).
- **Müsaitlik takvimi:** istek gerekmeden sayfanın içinde (`#pdpStoredDates`): dolu günler (`data-unavailable-dates`), giriş ve çıkış
  günleri (`data-checkin-dates`, `data-checkout-dates`), giriş/çıkışa kapalı günler; `AA/GG/YYYY` biçiminde, yaklaşık 13 ay.
- **En az konaklama:** sayfanın içinde, 400 gün için gün gün (`min_night_AA/GG/YYYY` gizli alanları; örnek evde 3 gece, Mart 2027'den
  itibaren 7 gece).
- **Fiyat:** sayfada yok ("Total:" alanı boş). Ziyaretçi takvimde iki tarih seçince `z_pdp.js`'teki `submitQuote()` şu isteği gönderir:

  ```
  POST /ajax/quote
  gövde: #pdpDatesForm alanları — checkin, checkout, propertyID, roomTypeID (boş), propertyName, hash (boş)
  ```

  Cevap fiyat dökümü HTML'idir (`.pdp-quote-item` kalemleri; toplam `.pdp-quote-total .pdp-quote-item-price`, sayısal değeri
  `data-price`). Uygun olmayan tarihte cevap yalnız `No`, servis hatasında `API Error`. Sayfa tarihlerle açılırsa (tarih alanları dolu
  gelirse) aynı istek açılışta kendiliğinden gönderilir; yine POST'tur.
- **GET mi POST mu:** **POST.** Betiklerdeki GET istekleri yalnız favoriler ve son bakılanlar içindir (`ajax/saveFavorites`,
  `ajax/favorites`, `ajax/recentlyViewed`). Tarihli arama da POST'tur (`#srpSubmitForm` → `POST /beach-rentals`).
- **Vergi ve ücret kalemleri:** fiyat cevabı görülmediği için biçimleri bilinmiyor. Sayfada yazılı tek ücret bilgisi açıklama metnindedir
  (ör. "Optional pool heat: $75/night", aylık konaklamada ek temizlik ücreti); bunlar fiyat verisi değildir.

### Karar (Adım 2.3)

Fiyat yalnız POST ile geliyor; görev kuralı gereği **okuyucu yazılmadı**. `thirty_a_agency_unread.csv`'de RealJoy'un nedeni güncellendi
(kanıt paketinin "Fiyatı okunamayan kiralama şirketleri" tablosunda görünür):

> ilan sayfası ve betikleri eklentiyle okundu (17 Kasım 2026): müsaitlik takvimi ve en az konaklama sayfanın içinde geliyor, ama fiyat
> yalnız tarih formunun POST isteğiyle (/ajax/quote) geliyor; tarihli arama da POST; fiyatı okumak form göndermek olurdu, bu yüzden
> okuyucu yazılmadı

**Yöneticinin bilmesi gereken (GÖREV-25 için):** bu POST bir fiyat sorusudur; sepet ya da rezervasyon kaydı açmaz, kişisel bilgi, giriş ya
da ödeme istemez; ziyaretçi tarih seçince sayfanın kendisi gönderir. Eklentinin bunu sitenin kendi sekmesinden göndermesi için altyapı
var (`Session.request`, sayfanın kendi `fetch`'i). Tam ev listesi de bir sorun: liste sayfası "311 sonuç" diyor ama ilk açılışta yalnız
12 evi veriyor, gerisi kaydırınca geliyor (o isteğin betiği `z_srp.js` okunmadı; büyük olasılıkla o da form ya da POST).

**Adım 2.4 (fiyat adresinin doğrulaması):** GET bir fiyat adresi olmadığı için deneme listesine fiyat adresi eklenmedi; ikinci deneme
istenmedi.

---

## Adım 3 — Okuyucu ve eşleme

Okuyucu, çekim ve 429 kuralı yazılmadı (Adım 2'nin kararı). Yapılan:

### Çevrimdışı adres eşlemesi (bilgi için)

Programın adres kuralıyla (`address_match`: aynı sokak numarası ve sokak, aynı daire, aynı oda sayısı, tek aday, 2 km sağlaması; ad
karşılaştırılmaz), ağa çıkmadan: RealJoy'un 30A ilan listesi (17 Kasım kaydı; sayfanın verdiği **12 ev**, hepsinde sokak adresi,
8 ondalıklı koordinat ve oda sayısı var) × son Book>Direct çekimindeki **61 RealJoy ilanı** (gerçek verinin GÖREV-20 kopyası,
`work/gorev-20/kopya.sqlite3`).

| Sonuç | İlan |
|---|---|
| Bağlanan | **1** |
| Şirket listesinde aday yok | 58 |
| Kullanılamaz (adres sokak numarasıyla başlamıyor ya da oda sayısı yok) | 2 |

58 ilanın çoğu, listenin yalnız ilk 12 evini görebildiğimiz içindir; tam listeyle sayı artar. Gerçek sayı GÖREV-25'te tam listeyle
görülür. Betik: `work/gorev-24/esle.py`, çıktı `work/gorev-24/esle-sonuc.txt` (repoya girmez).

### 429 kuralı

- **Görülen:** RealJoy, 17 Kasım'ın ilk deneme okumasında ilk sayfaya (30A ilan listesi) **HTTP 429** (çok fazla istek) döndü. İkinci
  denemede (sayfaları arası en az 20 sn) RealJoy'un dört sayfasının dördü 200 döndü.
- **Koda giren:** deneme okuması ("Sorunlu sitelerden birer sayfa dene") artık bir sitenin iki sayfası arasında eklentinin aralığı
  (varsayılan 8 sn) ile sitenin kendi aralığından (`EXTENSION_TRIAL_GAP_S`; realjoy.com **20 sn**) uzun olanı kadar bekler. Önceden bu
  bekleme yalnız aynı oturumun sayfaları arasındaydı; deneme her siteyi ayrı oturumla açtığı için aynı sitenin iki sayfası arka arkaya
  gelebiliyordu.
- **Koda girmeyen:** çekimdeki 429 kuralı (bekle — `Retry-After` varsa ona göre, yoksa en az 60 sn —, aynı sayfayı en çok iki kez yeniden
  iste, üst üste 429'da şirketi o çekimde durdur ve o ana kadarki fiyatları sakla). RealJoy'u okuyan bir toplayıcı olmadığı için bu
  görevde yazılmadı; GÖREV-25'in işidir.

---

## Adım 4 — Gerçek veri, tahmin, test, belgeler

### Gerçek veri

**Değişmedi.** RealJoy'un okuyucusu yazılmadığı için yapılandırmaya satır girmedi; bu yüzden `data/` yedeği de alınmadı (izin "yedek
alarak ekleyebilirsin" idi; eklenecek bir şey olmadı). Programı gerçek veriyle yalnız kullanıcı açtı (iki deneme okuması için);
eklentinin kayıtları `data/raw/eklenti/20261117/` altına programın kendisi tarafından yazıldı. RealJoy'un nedeni depodaki
`thirty_a_agency_unread.csv` dosyasındadır; veritabanında değil. Kiralama fiyat çekimi **başlatılmadı.**

### Çekim tahmini

"Güncelleme zamanı gelenler" tablosu (programın kendi `/api/refresh` cevabı, 17 Kasım 2026, kullanıcının açık programından salt okunur):

| Toplayıcı | Tahmin |
|---|---|
| South Walton · Konaklama (Book>Direct) | 3.778 sn ≈ 1 sa 3 dk |
| Kiralama şirketleri · Konaklama fiyatları | 35.999 sn ≈ **10 sa**; "son çekimden sonra eklenen 3 şirket için en çok +2720 istek, +137 dk (360 Blue, Vacasa, 30A Beach Girls)" |
| Yol ağı | ≈ 1 dk |
| **Toplam** | ≈ **11 sa 4 dk** (GÖREV-23 ile aynı) |

RealJoy tahminde **yok**, çünkü yapılandırılmış bir şirket değil ve bu çekimde okunmayacak. GÖREV-25'te eklenirse kaba üst sınır: 61 ilan
× (1 sayfa + 12 hafta × 1 fiyat isteği) ≈ 800 istek; 20 sn aralıkla yaklaşık 4,5 saat (RealJoy öbür şirketlerle yan yana okunacağı için
toplam süreye etkisi daha az olur).

### Testler

- Yeni: `tests/test_gorev24.py` (2 test): RealJoy'un okunamayan şirketlerde POST nedeniyle durduğu, uyarlayıcısı ve yapılandırma satırı
  olmadığı; deneme okumasında aynı sitenin iki sayfası arasında sitenin kendi aralığı kadar beklendiği, başka sitenin beklemediği.
- Güncellenen: `tests/test_extension.py`, `tests/test_extension_16.py` (deneme listesinin yeni sırası; realjoy.com'dan yalnız 30A ilan
  listesi, sonda), `tests/test_weather.py` (sürüm 0.25.0).
- Fixture eklenmedi: okuyucu yazılmadığı için ayrıştırılacak bir fiyat cevabı yok.

### Test sonuçları

- `.venv\Scripts\python.exe -m pytest -q` (son kodla): **1.196 geçti, 0 başarısız, 2 atlandı** (8 dk 24 sn).
- `node --test tests/frontend.test.mjs`: **138 geçti, 0 başarısız**.

### Belgeler

`docs/M11-KONAKLAMA-FIYATLARI.md` (yeni bölüm "GÖREV-24: RealJoy'un fiyat isteği"), `docs/M16-TARAYICI-EKLENTISI.md` (deneme listesi:
fiyat adresi yok, betikler bir kez okundu, site başına bekleme), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`,
`CALISMA_MANTIGI.md` (dal satırı). Uygulama sürümü 0.25.0.

---

## Kullanıcı için gece çekimi tarifi

Çekim yaklaşık **11 saat** sürer. Bilgisayarın uyumaması ve internetin açık kalması gerekir.

**Başlamadan önce**

1. **Chrome'u açın** (eklenti Chrome'un içinde çalışır) ve çekim boyunca **açık bırakın**.
2. **Programı açın** (masaüstündeki "30A Studio").
3. **Eklenti bağlı mı:** Sol menü → **Ayarlar** → **Tarayıcı eklentisi**. Üstte yeşil **"Bağlı · eklenti sürümü …"** yazmalı. "Bağlı
   değil (Chrome kapalı olabilir)" yazıyorsa Chrome'u açıp birkaç saniye bekleyin.
4. **Proxy çalışıyor mu:** Sol menü → **Veri** → **Okuma denemeleri** → "Proxy'nin deneme okuması ve bölge engelli alan adları" bölümü →
   **"Proxy'yi dene"**. Çıkış ülkesi "US" görünmeli. Aynı bölümdeki listede **360blue.com** ve **vacasa.com** duruyor olmalı.
5. **Doğrulama isteyebilecek siteler:** aynı ekranın en altındaki **"Isınma listesi"** bölümü bunları gösterir. Kiralama çekiminde ikisi
   önemli: **oversee.us** ve **exclusive30a.com**. Elle bir şey açmanız gerekmez.
   **RealJoy bu çekimde okunmaz:** sitesi fiyatı yalnız bir form gönderilince veriyor; buna izin yöneticinin kararıyla sonraki görevde
   (GÖREV-25) verilecek. Bu yüzden bu gece RealJoy için doğrulama da çıkmaz. Sonraki görevden sonra RealJoy da çekime girecek; o zaman
   Chrome'un açık kalması ve RealJoy'un doğrulama isteyebileceği (kutuyu sizin işaretlemeniz) tarife eklenecek.

**Başlatma**

6. Sol menü → **Veri** → **Kaynaklar** → **"Güncelleme zamanı gelenler"** tablosu → **"Zamanı gelenleri başlat"**. Program önce kendi
   yedeğini alır, sonra sırayla çalışır: Konaklama (Book>Direct), Kiralama şirketleri, Yol ağı. Tabloda "Kiralama şirketleri · Konaklama
   fiyatları" satırında yaklaşık 10 saat yazar.

**Çekim sırasında**

7. **Doğrulama çıkarsa:** eklenti, sizin Chrome'unuzda kendi açtığı ayrı pencerede siteyi açar. Sayfada "insan olduğunuzu doğrulayın"
   kutusu görürseniz **kutuyu işaretleyin**; başka bir şey yapmanız gerekmez. Bir site doğrulama beklerse program onu sona bırakır ve en
   sonda 15 dakika bekler; o sürede geçilmezse siteyi atlar ve kaydeder. 360 Blue ya da Vacasa doğrulama gösterirse programın kendi
   tarayıcı penceresi öne gelir; kutuyu orada işaretleyin.
8. İlerlemeyi sağ üstteki **"İşler"** düğmesinden izleyebilirsiniz.

**Bitince**

9. Sol menü → **Veri** → **Toplama** → **Konaklama** sekmesi → **"Konaklama fiyatları"** bölümü:
   - **"Şirket bazında sonuç"** tablosunda **360 Blue**, **Vacasa** ve **30A Beach Girls** satırlarına bakın. DURUM sütununda
     "tamamlandı" yazmalı; "BULUNAN" ve "FİYATLI SORGU" sütunları kaç ilanın bağlandığını ve fiyatlandığını gösterir. Vacasa'da az ilan
     bağlanması beklenen bir sonuçtur.
   - **"Şirketin kendi sitesindeki evler"** tablosunda 30A Beach Girls'ün ev sayısı ve **"HAFTALIK KİRA ORTANCASI"** sütunu görünür. Bu
     sütun yalnız kiradır; ücret ve vergi içinde değildir.
10. Bana **"çekim bitti"** yazın; sonuçları rapora işlerim.

---

## Canlı istekler ve kurallara uyum

- Claude Code'un yaptığı canlı istek: **yok** (realjoy.com dahil hiçbir siteye). RealJoy sayfalarını kullanıcının Chrome'undaki eklenti,
  kullanıcının bastığı deneme okumasıyla aldı (iki deneme; RealJoy'dan toplam 6 sayfa, bunlardan biri 429).
- Proxy kullanılmadı. Form, giriş, ödeme, sepet yok; eklenti tıklamadı, yazı yazmadı. Doğrulamayı kullanıcı geçti.
- Gerçek veritabanı açılmadı ve değişmedi; eşleme denemesi GÖREV-20'nin kopyası üzerinde, salt okunur yapıldı.

---

## Tamamlanamayanlar ve açık kalanlar

1. **RealJoy'un fiyatı (Adım 2.4, Adım 3, Adım 4.1'in yapılandırması).** Fiyat yalnız `POST /ajax/quote` ile geliyor; okuyucu kural gereği
   yazılmadı. Yönetici kararı: GÖREV-25'te izinle. O görevde gerekenler: fiyat isteğinin eklentiden gönderilmesi, cevabın (kalemler,
   vergi, ücret, toplam) ayrıştırılması, tam ev listesinin alınması (311 ev; ilk açılış yalnız 12 veriyor), adres eşlemesi, çekimdeki 429
   kuralı ve testleri.
2. **Gözlem (değişmedi):** GÖREV-23'teki adres kuralının sondaki tek yön harfini daire gibi okuması aynen duruyor.

## CI sonucu

CI_SONUCU
