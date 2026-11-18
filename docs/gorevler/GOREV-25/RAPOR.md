# GÖREV-25 Raporu — Eklentide "sayfanın kendi sorgusu" ve RealJoy okuyucusu

Dal: `gorev-25-realjoy-sorgu` (`gorev-24-realjoy`'un son commit'i `e2d1454`'ten açıldı). main'e alınmadı, etiket konmadı.
Uygulama 0.26.0, şema 24, eklenti 0.20.0.

## Kısa sonuç

| Konu | Sonuç |
|---|---|
| Eklenti | Sitenin kendi sekmesinden, yalnız izinli listedeki sorguyu sayfanın kendi alanlarıyla gönderiyor; yasak liste iki tarafta aynı. |
| RealJoy listesi | Liste isteği bulundu (`POST /ajax/results/scroll`). Üçüncü denemede **311 evin 311'i** geldi. |
| RealJoy fiyatı | `POST /ajax/quote` cevabı kalem kalem okunuyor (kira, ücretler, promosyon, vergi, toplam); "No" = uygun değil. |
| Eşleme | Yalnız adres kuralı: son Book>Direct çekimindeki 61 RealJoy ilanından **32'si** bağlanıyor (çevrimdışı). |
| Gerçek veri | Program normal açılışla şema 24'e geçti; yalnız RealJoy ayar satırı eklendi. Yedek: `work/yedek/20261117-2025`. |
| Tahmin | Kiralama ~12 sa 28 dk; zamanı gelenlerin hepsi ~13 sa 31 dk (RealJoy en çok +819 istek). |
| Fiyat çekimi | Başlatılmadı (kullanıcı başlatacak). |

Adım 1: `studio/destinations/thirty_a_claude/` altında talimat değişikliği yoktu; talimat commit'i yapılmadı.

---

## 1. Eklentinin yeni yeteneği ve kuralları (Adım 2)

Kullanıcı kararı (17 Kasım 2026): eklenti, bir sitenin kendi sekmesinden, o sayfanın ziyaretçi için zaten yaptığı herkese açık
sorguları gönderebilir (POST dahil). Kapsam: fiyat sorgusu ve ev listesinin devamı.

- **Yeni öğe türü `sorgu`** (`eklenti/background.js` `doQuery`): alan adı, yol, yöntem (GET/POST), alanlar.
  - Sekme o sitede değilse önce sitenin sayfasına gider.
  - Sekmenin kökeni sorgunun alan adıyla aynı olmalı; cevabın son adresi de.
  - İstek sayfanın kendi dünyasında `fetch` ile gider (`credentials: "same-origin"`, `X-Requested-With`, form gövdesi).
  - Aralık kuralı (bir anda tek istek, sitenin aralığı) aynen geçerli.
- **İzinli liste yapılandırmada:** şirketin `inventory.extension_queries` alanı. RealJoy için iki sorgu var: `/ajax/quote` (6 alan) ve
  `/ajax/results/scroll` (3 alan). Kapalı şirketin sorgusu listeye girmez. Ayarlar → Tarayıcı eklentisi'nde "İzinli sorgular" diye
  görünür.
- **Kurallar iki tarafta aynı** (`studio/extension_queries.py` `refusal`, `eklenti/logic.js` `queryRefusal`; bir test iki listeyi
  karşılaştırır):
  - yöntem yalnız GET ya da POST;
  - yol `/` ile başlar; `?`, `#`, `..` ve tam adres yoktur;
  - alan adı + yol + yöntem izinli listede olmalı;
  - alanlar listedeki adların alt kümesi olmalı ve aynı sırada gelmeli;
  - en çok 40 alan, değer başına 2000 karakter.
- **Yasak liste** (izinli listede olsa bile reddedilir):
  - yol sözcükleri: login, account, password, auth, checkout, payment, pay, card, cart, basket, order, reserve, reservation, confirm,
    contact, inquiry, subscribe, newsletter, profile, wallet, guest, owner, save, favorite, lead, message, email, phone, review ve
    benzerleri (camelCase de bölünür: `addToCart` → cart);
  - yol parçaları: `book`, `booking`, `bookings`, `booknow`, `my`. RealJoy'un `bookingEngine` klasörü yasak sayılmaz, ama
    `bookingEngine/ajax/addToCart` yasaktır;
  - alan adları: paypal.com, stripe.com, squareup.com, authorize.net, braintreegateway.com, accounts.google.com,
    login.microsoftonline.com, appleid.apple.com, facebook.com;
  - alt alan adları: login., auth., account(s)., checkout., pay(ment(s))., secure., book(ing)., my., sso., id.
- **Program tarafı:** reddedilen sorgu eklentiye hiç gitmez. **Eklenti tarafı:** gelirse gönderilmez, sonuç "reddedildi" olur. Düz
  `istek` öğesi artık yalnız GET'tir.
- **Kayıt:** ham cevap sorgunun yöntemi, yolu, alanları, adresi ve zamanıyla saklanır (deneme: `raw/eklenti/<tarih>/*.json` içindeki
  `sorgu`; toplayıcı: kendi ham deposu `request_body` ile).
- **Yalnız eklentiyle okunan şirket** (`inventory.extension_only`): eklenti eşleşmemiş, bağlı değil ya da iş programın kendi tarayıcısına
  devredilmişse şirket hiç istek yapılmadan atlanır ve kaydedilir. Programın kendi tarayıcısı ve doğrudan istek bu sorguları göndermez.
- **Sınama:**
  - Playwright'in Chromium'u, geçici profil, yerel sayfa (`tests/test_extension_e2e.py`): izinli sorgu tam verilen alanlarla gider;
    yasak yol, listede olmayan yol, fazladan alan ve düz isteğin POST'u eklentinin kendisinde reddedilir.
  - `tests/test_gorev25.py`: kurallar, yasak yollar ve alan adları.

**Eklentiyi yeniden yükleme:** Chrome'da adres çubuğuna `chrome://extensions` yazılır, "30A Studio Yardımcısı" kartındaki yenile
düğmesine basılır; kartta **0.20.0** yazmalı. Programda Sol menü → Ayarlar → Tarayıcı eklentisi "Bağlı" ve sürüm 0.20.0 göstermeli.
Kullanıcı 17 Kasım'da yeniledi; 0.20.0 bağlı.

## 2. Liste isteği ve tam liste (Adım 3)

- **İstek:** liste sayfasının betiği (`z_srp.js`) sayfa kaydırılınca `#scrollForm`'u gönderir: `POST /ajax/results/scroll`. Alanlar
  `page`, `propertyIDs` (12 ev kimliği) ve `sortBy` ("Random"). Cevap, istenen 12 evin kartlarıdır.
- **Liste sayfası şunları taşır:**
  - ev sayısı: `#bottomOfResults data-count="311"`;
  - 26 parçanın kimlikleri: gizli `page1propertyIDs` … `page26propertyIDs` alanları (her açılışta rastgele sıra).
- **Okuyucu:** liste sayfasını ve sonraki 25 parçayı sorar.
  - Gelen ev sayısı sayfanın söylediğinden azsa ya da bir parça 200 dışı dönerse hata verir ("liste eksik").
  - O çekimde listeden ilan bağlanmaz.
- **Üçüncü deneme (18 Kasım 2026, 05:22–05:31):** 26 parça istendi (kimlikler 17 Kasım liste kaydından).
  - 311 kimlik istendi, **311 ev geldi**; her parça tam istenen 12 evi istenen sırayla verdi.
  - 311 evin hepsinde sokak adresi, koordinat ve oda sayısı var.
- **Kart alanları:** birim kodu (`data-unitcode`), ad, sokak adresi, koordinat, oda ve kişi sayısı, sayfa adresi
  (`/beach-rentals/<seo>`).

## 3. Fiyat örneği (Adım 3)

Örnek: ev 1806, "Sea La Vie Seaside Main House", 9–16 Ocak 2027. İstek: `POST /ajax/quote`. Alanlar:
`checkin=01/09/2027`, `checkout=01/16/2027`, `propertyID=1806`, `roomTypeID=` (boş), `propertyName=Sea La Vie Seaside Main House`,
`hash=` (boş).

| Kalem (sitenin yazdığı gibi) | Tutar ($) |
|---|---|
| Rent | 6.692,02 |
| Fees (grup; kalemleri aşağıda, grup toplamı 1.755,00 yeniden eklenmez) | |
| · Accidental Damage Waiver | 130,00 |
| · Guest Departure Clean | 600,00 |
| · Check In Amenity Fee-Sea La Vie Seaside | 805,00 |
| · Check In & Amenity Fee | 220,00 |
| Promo discount (site kendiliğinden uyguladı, kod HOTDEALS) | −626,50 |
| Taxes | 938,53 |
| **Total** | **8.759,05** |

Kalemlerin toplamı sitenin toplamına eşit. Bu bizim kontrolümüzdür; bu yüzden toplam ücretleri ve vergiyi içeriyor diye işaretlenir.

Fiyat dışındaki durumlar:
- Cevap "No": "uygun değil" olarak ayrı tutulur (`unavailable`, `available=0`).
- Cevap "API Error" ya da başka bir biçim: hata.
- Fiyat sorusunda konuk sayısı alanı yoktur.

**Takvim ve en az gece** (ev sayfasında, GET):
- Takvim sitenin tarih seçicisinin kuralıyla okunur: dolu günler, başka konaklamanın başladığı gün (o gece dolu), kapalı günler, giriş ve
  çıkış yasak günleri.
- Gecelerinden biri dolu olan hafta **sorulmaz**: "unavailable", kaynak "takvim"; kanıt olarak sayfanın kaydı kullanılır.
- Giriş gününün en az gecesi haftadan uzunsa hafta sorulmaz, "restricted" olur.
- Örnek ev: Ocak'ta en az 3 gece, Haziran'da 7 gece. 5–12 Haziran 2027 takvimde dolu.

## 4. Çevrimdışı eşleme

Veri: üçüncü denemenin 311 evi × son Book>Direct çekimindeki 61 RealJoy ilanı (GÖREV-20 kopyası, salt okunur;
`work/gorev-25/esle.py`). Kural: aynı sokak numarası ve sokak, aynı daire, aynı oda sayısı ve tek aday. Adlar hiç karşılaştırılmaz.

| Sonuç | İlan |
|---|---|
| Bağlandı | **32** |
| Belirsiz (aynı bina adresinde 2–23 ev; daire numarası adreste yok) | 10 |
| Aday yok | 17 |
| Kullanılamaz (Book>Direct'te oda sayısı yok) | 2 |

**Bina koruması (yeni).** RealJoy bir binanın dairelerini binanın adresiyle yazar; daire numarası yalnız adda geçer. Örnek: "Beachside
Villas 214" kartında adres yalnız "11 Beachside Drive".
- Düz kural, Book>Direct'teki "Beachside Villas #814" ilanını yanlışlıkla 214'e bağlardı (ilk 46 kartlık örnekte de, tam listede de).
- Bu yüzden RealJoy için ek kural var: adresinde daire numarası olmayan bir ilan, şirket listesinde o adreste tek ev varsa bağlanır;
  birden çok ev varsa "belirsiz" kalır (`agency_matching.address_match(..., address_without_unit=True)`; okuyucunun özelliği).
- Etkisi: düz kuralla 33, bina korumasıyla 32 bağ.

GÖREV-24'te ilk 12 evle 1 bağ bulunmuştu; tam listeyle 32 bağ çıkıyor.

## 5. Deneme kayıtları (kullanıcının başlattığı üç deneme; `data/raw/eklenti/`)

1. **17 Kasım, 16:23–17:08 (birinci).** Okunanlar:
   - `z_srp.js` (`170734-8c00a7c8`) ve `map.js` (`170801-1cf04f34`): liste isteği bu iki betikten bulundu;
   - liste sayfası (`162516-206f0cd6`, `170706-ae171b6e`).

   Doğrulama çıktı; kullanıcı geçti. Betikler okunduktan sonra deneme listesinden çıkarıldı.
2. **17 Kasım, 21:09–21:11 (ikinci, eklenti 0.20.0).** Kayıtlar:
   - liste sayfası (`211057-d8f8ca2f`, 200);
   - liste örneği, 2. parça (`211120-e8a691fc`, 200): istenen 12 ev geldi;
   - fiyat örneği (`211141-b120af7c`, 200): yukarıdaki döküm.
3. **18 Kasım, 05:20–05:31 (üçüncü).** Kayıtlar:
   - liste sayfası (`052106-6d4a7c56`, **HTTP 429**, sayfa yine geldi);
   - iki örnek (`052128-650a6b05`, `052152-c164656d`);
   - tam listenin 26 parçası (`052214-d979590c` … `053135-c50c0c72`), hepsi 200, aralar ~22 sn.

   Bu denemede tam liste geçici olarak deneme listesine eklendi, sonra çıkarıldı. Kalıcı deneme listesinde iki örnek var.

Test fixture'ları bu kayıtlardan kesildi (`tests/fixtures/gorev25/`: liste sayfası, 2. parça, ev 1806 sayfası, fiyat cevabı; kesme
betiği `work/gorev-25/kes.py`). Değer değiştirilmedi.

Ayrı bir not: denemelerde winndixie.com proxy üzerinden okunamadı. Programın kendi tarayıcısında `ERR_INVALID_AUTH_CREDENTIALS`
görüldü, Chrome'da proxy kullanıcı adı/şifre penceresi çıktı. Bu görevle ilgili değil ve kod değişmedi. Proxy'nin tarayıcıda kimlik
doğrulaması ayrı bir görevde bakılmalı.

## 6. Toplayıcı (Adım 3–4)

- **Okuyucu:** `realjoy` (`studio/sources/agency_adapters.py` `RealJoy`): `parse_page`, `unit_fields`, `inventory`, `calendar_answer`,
  `quote`, `parse_quote`.
- **Akış:**
  - Book>Direct'in eski RealJoy bağlantıları sorulmaz (`dead_links`).
  - Eklentinin penceresi liste sayfasıyla açılır.
  - Tam liste okunur ve ilanlar adres kuralıyla bağlanır.
  - Bağlanan her evin sayfası bir kez açılır; takvimde boş görünen her hafta için fiyat sorulur.
- **Hız:** iki istek arası en az 20 sn (`gap_s`); korumalı şirket olarak aynı anda tek şirket ve tek istek.
- **429 kuralı** (`SiteSession`, `retry_429`):
  - `Retry-After` kadar beklenir; başlık yoksa 60 sn (en çok 1 saat);
  - en çok iki kez yeniden sorulur;
  - üçüncü 429'da şirket o çekimde durur: durum "site reddetti; durduruldu", neden mesajda, o ana kadarki fiyatlar saklanır.
- **Eklenti yoksa:** şirket atlanır. Durum "doğrulama gerekti; atlandı" (`verification_unavailable`; tablodaki durum kısıtı değişmesin diye
  mevcut durum kullanıldı). Mesaj: "Eklenti bağlı değil: bu şirket yalnız tarayıcı eklentisiyle … okunur; programın kendi tarayıcısı bu
  sorguları göndermez. Şirket bu çekimde atlandı."
- **"Okunamayan şirketler" tablosu** (`thirty_a_agency_unread.csv`): RealJoy satırı GÖREV-22'deki 360 Blue gibi güncellendi ("okuyucusu
  yazıldı (GÖREV-25), bu çekimden sonraki fiyat çekiminde eklenti bağlıysa okunur").

## 7. Gerçek veride ne değişti

- **Yedek:** program kapalıyken `data/` klasörünün tamamı `work/yedek/20261117-2025/` altına kopyalandı (45.601 dosya, 1.900.698.754
  bayt, kaynakla aynı).
- **Önce kopyada denendi:** migration 23 → 24 kopyada çalıştırıldı; ilişki hatası 0 → 0, 81 tablo; yalnız `destination_agency_sites`
  27 → 28.
- **Gerçek açılış:** program ikinci denemede kullanıcının açmasıyla, normal açılışla şema 24'e geçti.
- **Önce/sonra karşılaştırması** (18 Kasım, program kapalıyken salt okunur):

  | | Önce | Sonra |
  |---|---|---|
  | Şema | 23 | 24 |
  | İlişki hatası | 0 | 0 |
  | Tablo | 81 | 81 |
  | Satır | 188.529 | 188.534 |
  | `destination_agency_sites` (RealJoy ayar satırı) | 27 | 28 |
  | `jobs` (kullanıcının iki deneme işi) | 45 | 47 |
  | `job_progress` | 7 | 9 |

  Eksilen satır yok.
- Gerçek veriye RealJoy yapılandırmasından ve izinli sorgu listesinden başka bir şey eklenmedi. Fiyat çekimi çalıştırılmadı.

## 8. Yeni çekim tahmini

Kaynak: Sol menü → Veri → Kaynaklar → "Güncelleme zamanı gelenler". Hesap gerçek veritabanının kopyasında yapıldı, bizim tahminimizdir.

| Toplayıcı | Tahmin |
|---|---|
| Konaklama (Book>Direct) | ~1 sa 3 dk |
| Kiralama şirketleri · Konaklama fiyatları | **~12 sa 28 dk** (son çekimden sonra eklenen 4 şirket: +3.539 istek, +285 dk; şirketler yan yana okunur) |
| Yol ağı | ~1 dk |
| **Zamanı gelenlerin toplamı** | **~13 sa 31 dk** (GÖREV-24'te ~11 sa 4 dk) |

RealJoy'un kendi payı:
- **Üst sınır:** 61 ilan × (ev sayfası 1 + 12 hafta × 1) + liste 26 = **819 istek**. 20 sn aralık + 1 sn cevapla ~4 sa 47 dk.
- **Çevrimdışı eşlemedeki 32 bağla:** ~442 istek, ~2 sa 35 dk.
- Takvimde dolu haftalar sorulmayacağı için gerçek süre daha kısa olur.

## 9. Testler

- Yeni testler (`tests/test_gorev25.py`, 36 test):
  - sorgu kuralları, yasak yollar ve alan adları;
  - liste sayfalaması ve eksik liste;
  - fiyat dökümü ve "No";
  - dolu haftanın sorulmaması ve en az gece;
  - adres eşlemesi, benzer ad ama yanlış adres, bina koruması;
  - 429 kuralı;
  - eklenti yokken atlama;
  - RealJoy'un yalnız eklentiyle okunması (programın kendi istemcisi hiç kullanılmaz);
  - tahmin.
- Güncellenen eski testler:
  - şema 24 ve sürüm beklentileri;
  - şirket sayısı 28;
  - GÖREV-24'ün RealJoy testi yeni duruma göre;
  - eklenti aktarım testi (POST artık yalnız izinli sorgu).
- Tam takım: `.venv\Scripts\python.exe -m pytest -q` → **1232 geçti, 3 atlandı** (18 Kasım 2026). `node --test tests/frontend.test.mjs` → **138/138 geçti**.
  Uçtan uca eklenti testleri (`STUDIO_EKLENTI_E2E=1`, Playwright Chromium, geçici profil): 3/3 geçti.
- CI: `9778692` için "Tests" iş akışı **başarılı** (https://github.com/bemonths/tatilya/actions/runs/44246626531, 18 Kasım 2026 05:52 UTC).

## 10. Canlı istekler ve kurallara uyum

- **Canlı istek:** Claude Code'un yaptığı canlı istek yok (realjoy.com dahil). RealJoy'a giden her istek kullanıcının başlattığı üç eklenti
  denemesinden geldi.
- **İstek kapsamı:** proxy kullanılmadı. Giriş, ödeme, rezervasyon, sepet ve kişisel bilgi yok; eklenti tıklamadı ve yazı yazmadı.
  Doğrulamayı kullanıcı geçti.
- **Yasak işler:** programın Claude adımları çalıştırılmadı, alt ajan kullanılmadı, zamanlanmış görev oluşturulmadı.
- **Dokunulmayanlar:** talimat dosyaları, Housing Atlas ve Rota Stüdyo depoları.

---

## Kullanıcı için gece çekimi tarifi

Çekim yaklaşık **13,5 saat** sürer. Bilgisayarın uyumaması ve internetin açık kalması gerekir. **Chrome ve programı çekim bitene
kadar kapatmayın.** RealJoy yalnız Chrome'daki eklentiyle okunur; Chrome kapanırsa RealJoy atlanır.

**Başlamadan önce**

1. **Chrome'u açın.** Adres çubuğuna `chrome://extensions` yazın. "30A Studio Yardımcısı" kartında sürüm **0.20.0** olmalı. Değilse
   karttaki yenile düğmesine basın.
2. **Programı açın** (masaüstündeki "30A Studio").
3. **Eklenti bağlı mı:** Sol menü → **Ayarlar** → **Tarayıcı eklentisi**. Üstte yeşil **"Bağlı · eklenti sürümü 0.20.0"** yazmalı.
   Aynı bölümde "İzinli sorgular" altında RealJoy'un iki sorgusu görünür. "Bağlı değil" yazıyorsa Chrome'un açık olduğundan emin olup
   birkaç saniye bekleyin.
4. **Proxy çalışıyor mu:** Sol menü → **Veri** → **Okuma denemeleri** → "Proxy'nin deneme okuması ve bölge engelli alan adları" bölümü →
   **"Proxy'yi dene"**. Çıkış ülkesi "US" görünmeli. Aynı bölümdeki listede **360blue.com** ve **vacasa.com** duruyor olmalı.
5. **Doğrulama isteyebilecek siteler:** aynı ekranın en altındaki **"Isınma listesi"** bölümü bunları gösterir. Kiralama çekiminde
   **oversee.us** ve **exclusive30a.com** önemli; **realjoy.com** da doğrulama isteyebilir (denemelerde bir kez istedi). Elle bir şey
   açmanız gerekmez.

**Başlatma**

6. Sol menü → **Veri** → **Kaynaklar** → **"Güncelleme zamanı gelenler"** tablosu → **"Zamanı gelenleri başlat"**. Program önce kendi
   yedeğini alır, sonra sırayla şunları çalıştırır: Konaklama (Book>Direct), Kiralama şirketleri, Yol ağı. "Kiralama şirketleri ·
   Konaklama fiyatları" satırında yaklaşık 12,5 saat yazar.

**Çekim sırasında**

7. **Doğrulama çıkarsa:**
   - RealJoy, oversee.us ya da exclusive30a.com doğrulama isterse eklenti sizin Chrome'unuzda kendi penceresini öne getirir. Sayfadaki
     "insan olduğunuzu doğrulayın" kutusunu **işaretleyin**.
   - Bir site doğrulama beklerse program onu sona bırakır ve en sonda 15 dakika bekler. O sürede geçilmezse siteyi atlar ve kaydeder.
   - 360 Blue ya da Vacasa doğrulama gösterirse programın kendi tarayıcı penceresi öne gelir; kutuyu orada işaretleyin.
8. RealJoy yavaş okunur: iki istek arasında 20 saniye beklenir. Site "çok fazla istek" derse program önce bekler, sonra yeniden sorar; yine
   olmazsa RealJoy'u o gece durdurur ve o ana kadar okunanları saklar. Sizin bir şey yapmanız gerekmez.
9. Winn-Dixie'nin proxy kullanıcı adı/şifre penceresi bu çekimde çıkmaz (o site kiralama çekiminde yok). Çıkarsa kapatın.
10. İlerlemeyi sağ üstteki **"İşler"** düğmesinden izleyebilirsiniz.

**Bitince**

11. Sol menü → **Veri** → **Toplama** → **Konaklama** sekmesi → **"Konaklama fiyatları"** bölümü:
    - **"Şirket bazında sonuç"** tablosunda şu satırlara bakın: **RealJoy Vacations**, **360 Blue**, **Vacasa**, **30A Beach Girls**.
      - DURUM sütununda "tamamlandı" yazmalı.
      - "BULUNAN" ve "FİYATLI SORGU" sütunları kaç ilanın bağlandığını ve fiyatlandığını gösterir. RealJoy için 30 civarı bağlı ilan
        beklenir.
      - RealJoy'da "doğrulama gerekti; atlandı" yazıyorsa Chrome ya da eklenti bağlı değildi.
    - **"Şirketin kendi sitesindeki evler"** tablosunda 30A Beach Girls'ün ev sayısı ve **"HAFTALIK KİRA ORTANCASI"** görünür. Bu sütun
      yalnız kiradır.
12. Bana **"çekim bitti"** yazın; sonuçları rapora işlerim.

---

## Tamamlanamayanlar ve açık kalanlar

- Yok. Bütün adımlar tamamlandı.
- **Açık gözlem 1:** gerçek çekimde RealJoy'un kaç ilanı bağlayacağı, çekimdeki listeye ve o günkü Book>Direct ilanlarına bağlı. Çevrimdışı
  sayı (32) bir tahmindir.
- **Açık gözlem 2:** winndixie.com'un proxy kimlik doğrulaması (Bölüm 5) ayrı bir iş.
