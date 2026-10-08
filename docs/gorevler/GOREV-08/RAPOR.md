# GÖREV-08 Raporu — v0.10.0 yayını ve kiralama şirketlerinden konaklama fiyatları

Tarih: 8 Ekim 2026 · Dal: `gorev-08-konaklama-fiyat` · Uygulama `0.11.0` · Şema `11`

## Kısaca

- **Adım 1 tamam:** main `1f4e80b`'ye getirildi, `v0.10.0` etiketi konuldu; main ve etiket CI'ı başarılı.
- **Adım 2 tamam:** konaklama toplayıcısı artık her ilanın kiralama şirketindeki ilan sayfasını ve telefonlarını saklıyor, takvimi gizli ilanlarda takvim istemiyor (çekim ~73 dakikadan ~35 dakikaya indi). Doğrulama yöntemi CLAUDE.md ve CALISMA_MANTIGI'ye yazıldı (ayrı commit `8621394`).
- **Adım 3 tamam:** 2.389 ilanın şirket bağlantıları 137 alan adında; ilk 40 alan adı (ilanların %94,6'sı) incelendi. Fiyatı okunabilen dört altyapı bulundu; bağlantısı hâlâ ilan sayfasına giden 9 şirket (758 ilan) seçildi. Belgeler: `AJANS-KESFI.md`, `ajanslar.csv`.
- **Adım 4 tamam:** kiralama şirketi fiyat toplayıcısı (genel çekirdek + 4 uyarlayıcı, şema 11, Konaklama sekmesinde fiyat bölümü, İşler panelinde doğrulama beklemesi). Test sayısı: 587 Python + 52 frontend.
- **Adım 5 tamam:** referans tablosunda doğrulanamayan satır kalmadı (105 satır: 100 doğrulandı, 2 çelişkili, 3 yerine geçildi).
- **Adım 6 tamam:** geçici klasörde canlı deneme (üç hata bulundu ve düzeltildi), gerçek verinin kopyasında v10 → v11 geçişi, tam yedekten sonra gerçek veritabanında iki çekim; kontroller temiz.
- **Ana sonuç:** 510 ilana kiralama şirketinin kendi sitesinden, sitenin gösterdiği vergiler ve zorunlu ücretler dahil toplam fiyat alındı (seçilmemiş sigorta gibi isteğe bağlı kalemler hariç), 12/13 mahallede. En büyük şirket 360blue (256 ilan, çoğu WaterColor ve WaterSound'da) Cloudflare engeli yüzünden yok; bu iki mahallede fiyat örneği zayıf.

## Adım 1 — v0.10.0'ı main'e alma ve etiketleme

| | |
|---|---|
| Önce | `origin/gorev-07-konaklama` son commit `1f4e80b` CI: çalıştırma 37685683978 — başarılı |
| main | `git merge --ff-only origin/gorev-07-konaklama` ile `1f4e80bcab70e7dd5fd4cb29bd1a0d67b9822ca1`'e getirildi ve push edildi |
| Etiket | açıklamalı `v0.10.0` ("v0.10.0 — bilgi toplama ilkesi, referans tablosu tamamlama ve konaklama profili") `1f4e80b`'yi gösteriyor, push edildi |
| main CI | çalıştırma 37761297449 — başarılı |
| Etiket CI | çalıştırma 37761301031 — başarılı |
| Görev dalı | güncel main'den `gorev-08-konaklama-fiyat` açıldı |

## Adım 2 — Konaklama toplayıcısında iki düzeltme

Commit `8621394` (ayrı commit), toplayıcı `bookdirect-lodging/2`:
- İlan kaydındaki `url` (kiralama şirketinin ilan sayfası; yalnız http/https kabul edilir), `phone` ve `toll_free` veritabanına yazılıyor; ilan ayrıntısında "Şirketin ilan sayfası" bağlantısı var. Kaynakta şirket ya da sahip **adı** alanı yok; şirket bilgisi bağlantı ve telefondan ibaret.
- Takvimi gizli ilanlarda (`hide_rate_calendar`) takvim isteği yapılmıyor; ön yüz de bu ilanlarda takvim göstermiyor. Atlanan ilan sayısı çekim kaydında (`calendars_skipped_hidden`: 1.536). Bu, istekleri 2.655'ten ~1.120'ye, süreyi ~73'ten ~35 dakikaya indirdi.
- Şema 11: `lodging_listings`'e üç sütun (eski kayıtlarda NULL).
- CLAUDE.md ve CALISMA_MANTIGI §4'teki doğrulama cümlesi "Tarayıcı ve insan doğrulaması" yöntemiyle değiştirildi (doğrulamayı kullanıcı yapar; Claude Code sayfayı kalıcı profilli görünür pencerede açar, bekler, aynı oturumla devam eder).

## Adım 3 — Kiralama şirketlerinden fiyat: keşif

Ayrıntı `AJANS-KESFI.md`, tam liste `ajanslar.csv` (alan adı, şirket, ilan sayısı, mahalle dağılımı, rezervasyon ve site altyapısı, fiyat yolu, uyarlayıcı).

- İlk 13 alan adı ilanların üçte ikisini kapsıyor; ilk 40'ı (%94,6) incelendi.
- Fiyat yolu bulunan altyapılar ve şirketleri: **ResCMS** (Benchmark Management, Grayton Coast Rentals, 30A Cottages, My Vacation Haven), **Track** (30A Escapes, Panhandle Getaways), **Streamline** (Rosemary Beach®, Dune Vacation Rentals), **vacation-rentals/router** (Dune Allen Realty). Dördünde de kira, vergiler ve toplam ayrı görünüyor; ücretleri şirketlerin çoğu adlarıyla ayrı gösteriyor (30A Escapes göstermiyor); ResCMS sayfası en az gece ve giriş günü kuralını da veriyor.
- Kapsam dışı kalanlar: Cloudflare arkasındaki 360blue (256 ilan), oversee.us (185), realjoy (61), exclusive30a (29), oldseagrove (8); fiyat servisi çözülemeyen Southern Resorts (104); Book>Direct bağlantısı ana sayfaya ya da genel listeye giden Homeowner's Collection (143), Ocean Reef (96), paradise30a (59), Grayt 30A (40); bağlantıları 404 olan 30a-vacay (54), 30a-beachgirls (48); Vrbo, Airbnb, Vacasa gibi platformlar.
- **360blue:** keşifte siteye art arda denemeler yapıldı ve kullanıcının IP adresi engellendi. Kullanıcı proxy önerdi; sitenin bilerek koyduğu engeli dolanmak olacağı için kullanılmadı. Görünür tarayıcıda bir kez daha açıldığında yine engel sayfası çıktı; siteye başka istek yapılmadı.

## Adım 4 — Kiralama şirketi fiyat toplayıcısı

Ayrıntı `docs/M11-KONAKLAMA-FIYATLARI.md`.

- `agency-lodging-rates/1`: girdi son Book>Direct çekimi; ilan şirket sitesindeki ilana **yalnız bağlantıyla** eşleniyor (ad benzerliği yok). Şirket → uyarlayıcı eşlemesi destinasyon yapılandırmasında (`destination_agency_sites`).
- Her ilan × pencere: sitenin söylediği müsaitlik, kira, temizlik ve diğer ücretler, vergiler, genel toplam, isteğe bağlı (toplama girmeyen) kalemler, gecelik fiyatlar (Streamline), en az gece ve giriş günü (site gösteriyorsa), sorgu zamanı ve adresi, ham yanıtların SHA-256'sı. Vermediği alan NULL.
- Nezaket: aynı siteye istekler sıralı ve en az 2 sn arayla, en çok 3 şirket yan yana. Bir şirket reddederse ya da ulaşılamazsa yalnız o durur; sonuç şirket bazında kaydediliyor. İptal ve atomik yazım testli.
- İnsan doğrulaması: site doğrulama sayfası gösterirse kalıcı profilli görünür Chrome açılır, iş "Kullanıcı doğrulaması bekleniyor · <site>" olur, kullanıcı doğrulayınca aynı oturumla devam edilir; 15 dakikada tamamlanmazsa o şirket atlanır.
- Özet okuma anında: mahalle × pencere için sorgulanan ve fiyatlı ilan sayısı, müsait payı, 7 gecelik toplamın ortancası ve çeyrekleri, kira ÷ gece ortancası, oda gruplarına göre ortancalar; etiket "kiralama şirketlerinin kendi sitelerinde <tarih> tarihinde sorgulanan fiyatlar; toplam fiyat … içerir".
- Testler: 587 Python (görev başında 555) ve 52 frontend (46) testi; yeni dosya `tests/test_agency_rates.py` (30 test).

## Adım 5 — Referans tablosunda kalan satırlar

| Satır | Sonuç | Kaynak ve yöntem |
|---|---|---|
| Grayton Beach ücret / saat | araç $5 (2–8 kişi), tek kişi $4, yaya/bisiklet/ek yolcu $2; 08:00–gün batımı | floridastateparks.org, uygulama içi tarayıcıda normal açıldı; ham sayfa SHA-256 ile |
| Topsail Hill Preserve ücret / saat | araç $6 (2–8 kişi, fazlası kişi başı $2), tek kişi veya motosiklet $4, yaya/bisiklet $2; 08:00–gün batımı | aynı |
| Deer Lake ücret / saat | araç $3 (2–8 kişi), yaya/bisiklet/ek yolcu $2 (honor box); 08:00–gün batımı | parkın ana sayfası (eski "hours-fees" adresi artık 404) |
| 30A hız sınırları | 2017'de ilçe meclisi CR-30A için 35 mph azami hız önerisini içeren çalışmanın hız bölgesi önerilerini 5–0 kabul etti | DeFuniak Herald haberi (2 Mart 2017; ikincil) + ilçenin 14 Şubat 2017 tutanağı (birincil, hız değerlerini yazmıyor). Bugünkü levhalar ayrıca doğrulanmadı. |
| Timpoochee uzunluğu | ilçenin Timpoochee'ye özgü değeri yok; Turizm Dairesi "26 milden fazla çok amaçlı yol" bakımı yapıyor (yol adı yok) | ilçe sayfası; 19 / 18,5 mil çelişkisi sürüyor |
| Rosemary Beach otoparkı | Barrett Square boyunca ilk gelenin aldığı dükkân otoparkı; halka açık plaj erişimi yok | Visit South Walton park rehberi (2023); şirketin sitesi yalnız kiracı park kartından söz ediyor |
| WaterSound otoparkı | The Big Chill ziyaretçilerine açık otopark (ilk gelen alır) | aynı rehber; St. Joe sitelerinde ziyaretçi otoparkı bilgisi yok |

Florida State Parks sitesi otomasyonla açılan Chrome'a ve düz isteğe 403 veriyor (gizleme ayarı kullanılmadı); uygulama içi tarayıcıda doğrulama ekranı çıkmadan açıldı. Güncel tablo: `referans-tablosu.csv`.

## Adım 6 — Gerçek ortam ve teslim

### 6.1 Geçici klasörde canlı deneme (`work/gorev-08/temp-data`)

| Çekim | Süre | İstek | Sonuç |
|---|---:|---:|---|
| Konaklama (`bookdirect-lodging/2`) | 34,5 dk | 1.123 | 2.389 ilan, 9.189 arama satırı, 853 takvim okundu, 1.536 gizli takvim atlandı |
| Fiyat, deneme 1 (büyük üçü dışındaki 6 şirket) | 36,9 dk | — | **iptal edildi**: sıradan bir CAPTCHA kutusu doğrulama sayfası sanıldı (hata 1) |
| Fiyat, deneme 2 (aynı 6 şirket, hata 1 düzeltildi) | 19,0 dk | 1.101 | tamamlandı; 136 ilan eşlendi, 129 ilana fiyat; inceleme iki hata daha gösterdi (hata 2, 3) |
| Fiyat, deneme 3 (yalnız Panhandle Getaways, hata 2 düzeltildi) | 8,3 dk | 214 | tamamlandı; takvimde dolu haftalar artık "müsait değil" |

Geçici denemede yük paylaşımı için büyük üç şirket (Benchmark, 30A Escapes, Rosemary Beach) kapatıldı; gerçek çekimden önce aynı sitelere iki kat yük bindirilmedi. Ekran görüntüsü: `fiyat-bolumu-gecici-deneme.png` (deneme 3; WaterSound mahallesi ve bir ilanın kalem kalem dökümü).

Bulunan ve düzeltilen hatalar (her biri test ve ayrı commit'le):
1. **Yanlış doğrulama:** ResCMS sitelerinde yayından kalkmış bir ilan, sitenin olağan "Access denied" sayfasını (403) döndürüyor; sayfadaki form CAPTCHA kutusu doğrulama sayfası sanıldı ve görünür pencere açıldı (iki şirkette; kullanıcıya bildirildi, iş iptal edildi). Artık yalnız gerçek doğrulama sayfası işaretleri sayılıyor; 403 alan ilan sayfasından sonra sitenin ana sayfasına bir kez bakılıyor, site çalışıyorsa yalnız o ilan "erişime kapalı" oluyor (`b856b78`).
2. **Track'te müsaitlik:** Panhandle Getaways'in fiyat servisi, ilan sayfasının takviminde dolu görünen haftalara da fiyat veriyor (sonbaharda 33 ilandan 15'i). Track uyarlayıcısı artık önce sayfanın müsaitlik takvimine bakıyor; dolu gece varsa "müsait değil" yazıp fiyat sormuyor (`99fa912`).
3. **ResCMS'te isteğe bağlı sigorta:** bazı sitelerde seyahat sigortası "seçilmedi" işareti olmadan ayrı satırda; sitenin ara toplamına girmiyor. Artık ara toplama göre ayrılıyor; kaydedilmiş 64 ResCMS fiyatının hepsi sitenin toplamını tutuyor (`f20d5e1`).
4. Ayrıca: 200 koduyla dönen "Pages Not Found" sayfaları "sayfa bulunamadı" sayılıyor (`1d974ac`); destinasyon sıfırlamasında fiyat bölümünün bağlantısı kopuyordu (`7514d60`).

### 6.2 Migration denemesi (gerçek verinin kopyası, v10 → v11)

Kopya (`work/gorev-08/migration-data`) uygulamayla açıldı: sürüm 10 → 11, eski 37 tablonun satırları aynı (`sources` yalnız 13 → 14), 7 yeni tablo, `destination_agency_sites` 9 satır, `lodging_listings`'e üç boş sütun; uygulama yedeği alındı; `integrity_check` ok, `foreign_key_check` boş.

### 6.3 Gerçek veritabanı

| | |
|---|---|
| Tam yedek | uygulama kapalıyken `data/` → `work/yedek/20261008-1517/` (3.040 dosya; kopya ve kaynak SHA-256 ile doğrulandı) |
| Açılış | uygulama gerçek veriyle açıldı; v10 → v11 (uygulama yedeği `data/backups/studio-v10-38fe9237….sqlite3`) |
| Konaklama çekimi | `99735d8aa24e4d38a65f7408f5990cd8`: 34,2 dk, 1.119 istek, 2.389 ilan, 9.194 arama satırı, 853 takvim, 1.536 gizli takvim atlandı |
| Yeniden açılış | düzeltmeler (6.1) yüklensin diye uygulama kapatılıp aynı veriyle yeniden açıldı |
| Fiyat çekimi | `1968245cac594bb88d9bde11ed09b449`: 92,5 dk, 3.855 istek; doğrulama penceresi açılmadı |
| Sonra | 20 jobs, 17 source_runs; `lodging_listings` 4.778 (iki konaklama çekimi), `lodging_search_results` 18.383; `agency_rate_listings` 2.389, `agency_rate_quotes` 2.116, `agency_rate_companies` 9; `job_waits` boş |
| Kontrol | `integrity_check` ok, `foreign_key_check` boş; önceki çekimlerin satırları aynı |

Ekran görüntüsü: `fiyat-bolumu-gercek-veri.png`. Mahalle × pencere özeti: `konaklama-fiyat-ozet.csv`.

#### Kapsama (ilan sayısı)

| Durum | İlan |
|---|---:|
| şirket sitesinde bulundu | 529 |
| sayfa bulunamadı (404 veya 'not found' sayfası) | 120 |
| bağlantı ilan sayfasına gitmiyor | 64 |
| başka siteye yönlendi | 0 |
| ilan sayfası erişime kapalı (403) | 43 |
| siteye ulaşılamadı | 3 |
| sorulmadı | 0 |
| şirketin sitesi için uyarlayıcı yok | 1623 |
| Book>Direct'te bağlantı yok | 7 |
| **Toplam** | **2389** |

En az bir pencerede fiyatı alınan ilan: **510**. Bütün ilanlara oranı %21,3, yapılandırılmış şirketlere bağlı 759 ilana oranı %67,2. Fiyat sorgusu (ilan × pencere): 2116. Fiyat alınan mahalle: 12/13 (Alys Beach'teki 7 ilanın 6'sı alysbeach.com'a bağlı, onun uyarlayıcısı yok; 1'inin bağlantısı eski).

#### Şirket bazında sonuç

| Şirket | Uyarlayıcı | İlan | Bulunan | Fiyatlı sorgu | İstek | Durum |
|---|---|---:|---:|---:|---:|---|
| Benchmark Management (benchmark30a.com) | `rescms` | 241 | 189 | 483/756 | 1747 | tamamlandı |
| 30A Escapes (30aescapes.com) | `track` | 162 | 143 | 327/572 | 500 | tamamlandı |
| Rosemary Beach® (rosemarybeach.com) | `streamline` | 89 | 61 | 156/244 | 535 | tamamlandı |
| Dune Allen Realty Vacation Rentals (beautifulbeach.com) | `vr_router` | 88 | 37 | 92/148 | 288 | tamamlandı |
| Panhandle Getaways (panhandlegetaways.com) | `track` | 81 | 33 | 104/132 | 214 | tamamlandı |
| Dune Vacation Rentals (dunevacationrentals.com) | `streamline` | 49 | 34 | 94/136 | 314 | tamamlandı |
| 30A Cottages (30acottagesandconcierge.com) | `rescms` | 17 | 14 | 27/56 | 97 | tamamlandı |
| Grayton Coast Rentals (graytoncoastrentals.com) | `rescms` | 17 | 11 | 22/44 | 85 | tamamlandı |
| My Vacation Haven (myvacationhaven.com) | `rescms` | 15 | 7 | 20/28 | 75 | tamamlandı |

#### Mahalle × pencere: 7 gecelik toplam fiyat (ortanca; çeyrekler arası aralık)

Etiket: *Kiralama şirketlerinin kendi sitelerinde 2026-10-08 tarihinde sorgulanan fiyatlar; toplam fiyat vergileri içerir; zorunlu ücretler 978 fiyatta ayrı kalem olarak gösterildi ve toplama dahil, diğerlerinde site ayrı ücret göstermedi (isteğe bağlı sigorta gibi kalemler hariç).*

| Mahalle | Sonbahar 2026 (10-17→10-24) | Kış 2027 (01-16→01-23) | Bahar tatili 2027 (03-13→03-20) | Yaz 2027 (07-10→07-17) |
|---|---|---|---|---|
| Dune Allen | **$2.524** ($2.285–$3.802); 8/36 fiyatlı, müsait %22 | **$2.895** ($2.398–$4.007); 22/36 fiyatlı, müsait %61 | **$3.483** ($2.855–$4.325); 31/36 fiyatlı, müsait %86 | **$5.144** ($3.853–$5.608); 29/36 fiyatlı, müsait %81 |
| Gulf Place | **$1.946** ($1.946–$1.946); 1/3 fiyatlı, müsait %33 | **$3.321** ($2.720–$3.923); 2/3 fiyatlı, müsait %67 | **$3.678** ($3.604–$3.752); 2/3 fiyatlı, müsait %67 | **$4.803** ($4.787–$9.191); 3/3 fiyatlı, müsait %100 |
| Santa Rosa Beach | **$5.408** ($5.408–$5.408); 1/7 fiyatlı, müsait %14 | **$2.933** ($2.533–$4.452); 5/7 fiyatlı, müsait %71 | **$4.291** ($4.282–$4.324); 5/7 fiyatlı, müsait %71 | **$7.510** ($5.658–$7.927); 5/7 fiyatlı, müsait %71 |
| Blue Mountain Beach | **$2.437** ($2.283–$2.591); 2/9 fiyatlı, müsait %22 | **$1.937** ($1.584–$2.359); 7/9 fiyatlı, müsait %78 | **$3.563** ($3.164–$3.779); 7/9 fiyatlı, müsait %78 | **$5.133** ($4.521–$5.697); 7/9 fiyatlı, müsait %78 |
| Grayton Beach | **$6.308** ($4.163–$8.663); 4/12 fiyatlı, müsait %33 | **$4.770** ($3.762–$7.794); 9/12 fiyatlı, müsait %75 | **$4.580** ($3.457–$6.437); 8/12 fiyatlı, müsait %67 | **$7.497** ($5.448–$10.838); 8/12 fiyatlı, müsait %67 |
| WaterColor | **$7.104** ($6.550–$7.568); 3/24 fiyatlı, müsait %12 | **$5.894** ($4.462–$7.984); 15/24 fiyatlı, müsait %62 | **$8.055** ($5.639–$12.297); 18/24 fiyatlı, müsait %75 | **$10.389** ($6.966–$17.656); 20/24 fiyatlı, müsait %83 |
| Seaside | **$15.362** ($9.432–$21.292); 2/6 fiyatlı, müsait %33 | **$6.086** ($4.647–$14.969); 3/6 fiyatlı, müsait %50 | **$7.519** ($4.008–$23.740); 5/6 fiyatlı, müsait %83 | **$8.362** ($4.092–$24.878); 5/6 fiyatlı, müsait %83 |
| Seagrove | **$2.134** ($1.327–$3.022); 31/178 fiyatlı, müsait %17 | **$1.487** ($1.249–$2.403); 132/178 fiyatlı, müsait %74 | **$2.771** ($2.130–$4.006); 139/178 fiyatlı, müsait %78 | **$5.046** ($4.136–$6.583); 161/178 fiyatlı, müsait %91 |
| WaterSound | **$2.412** ($2.090–$2.500); 16/40 fiyatlı, müsait %40 | **$2.679** ($2.302–$4.024); 35/40 fiyatlı, müsait %88 | **$3.955** ($3.245–$5.852); 36/40 fiyatlı, müsait %90 | **$6.745** ($5.692–$7.951); 39/40 fiyatlı, müsait %98 |
| Seacrest | **$2.944** ($2.588–$3.123); 8/108 fiyatlı, müsait %7 | **$3.078** ($2.550–$3.582); 79/108 fiyatlı, müsait %73 | **$5.192** ($4.456–$6.889); 73/108 fiyatlı, müsait %68 | **$8.225** ($6.696–$9.214); 80/108 fiyatlı, müsait %74 |
| Alys Beach | sorgulanan yok | sorgulanan yok | sorgulanan yok | sorgulanan yok |
| Rosemary Beach | **$2.941** ($2.432–$4.264); 10/91 fiyatlı, müsait %11 | **$4.042** ($2.504–$6.032); 60/91 fiyatlı, müsait %66 | **$5.752** ($3.927–$8.376); 75/91 fiyatlı, müsait %82 | **$6.207** ($4.406–$11.583); 81/91 fiyatlı, müsait %89 |
| Inlet Beach | **$10.628** ($6.420–$14.836); 2/15 fiyatlı, müsait %13 | **$4.338** ($3.179–$7.172); 12/15 fiyatlı, müsait %80 | **$5.976** ($4.827–$13.323); 8/15 fiyatlı, müsait %53 | **$9.819** ($7.348–$22.851); 11/15 fiyatlı, müsait %73 |

Sayılar fiyatı alınabilen ilanlardandır; 5'ten az fiyatlı ilanı olan hücreler mahalle hakkında genelleme için kullanılmamalıdır.

#### Oda sayısına göre ortanca 7 gecelik toplam (bütün mahalleler, ilan sayısı parantezde)

| Oda | Sonbahar 2026 | Kış 2027 | Bahar tatili 2027 | Yaz 2027 |
|---|---|---|---|---|
| 1–2 | $1.983 (22) | $1.850 (125) | $2.959 (154) | $4.868 (170) |
| 3 | $2.439 (30) | $2.635 (104) | $4.626 (121) | $6.512 (128) |
| 4 | $3.420 (19) | $3.276 (71) | $5.855 (69) | $8.311 (75) |
| 5+ | $5.478 (14) | $5.715 (65) | $8.471 (47) | $14.040 (59) |

(Bir ilan birden fazla mahallede göründüyse bu tabloda bir kez sayılır.)

### 6.4 Belgeler ve testler

- Yeni: `docs/M11-KONAKLAMA-FIYATLARI.md`; güncellenen: M9 (GÖREV-08 dağılımı), M10 (bağlantı ve takvim), CALISMA_MANTIGI, README, DEVIR/05 ve 02 durum satırları.
- Tam test takımı art arda 3 kez: **587 Python** ve **52 frontend** testi geçti (her Python çalıştırmasında bilinen Starlette/httpx uyarısı).
- `git status`: `work/` ve `data/` sahnede değil.

## Beklenmeyen durumlar

- **360blue IP engeli:** keşifteki art arda denemeler sonucunda kullanıcının IP adresi 360blue'da engellendi. Proxy kullanılmadı. En büyük şirketin fiyatı bu yüzden yok.
- **Geçici denemede açılan Chrome pencereleri:** hata 1 yüzünden iki kez görünür pencere açıldı; kullanıcıya bunun bir doğrulama olmadığı söylendi, iş iptal edildi, pencereler kapandı.
- **Eskimiş bağlantılar:** yapılandırılmış şirketlerde bile birçok Book>Direct bağlantısı 404 veriyor ya da arama sayfasına gidiyor; bu ilanlar eşlenmedi.
- **Florida State Parks:** otomasyonla açılan Chrome'a 403, uygulama içi tarayıcıya normal açılıyor; ham kopya uygulama içi tarayıcıdan alındı.

## Yöneticinin karar vermesi gereken konular

1. **360blue ve diğer Cloudflare siteleri** (360blue 256, oversee.us 185, realjoy 61, exclusive30a 29, oldseagrove 8 ilan): engel kalktıktan sonra yavaş tempoda, kullanıcının görünür pencerede doğrulamasıyla yeniden denensin mi, yoksa bu açık kabul mü edilsin? 360blue WaterColor ve WaterSound'daki ilanların büyük kısmını tutuyor.
2. **Southern Resorts (104 ilan):** fiyat servisi tarayıcının ağ trafiğinden çözülmeye çalışılsın mı?
3. **Eskimiş bağlantılar:** bağlantısı 404 olan ya da ana sayfaya giden ilanlar için şirket sitesinde adres veya ad ile arama yapılsın mı? (Görev, ad benzerliğiyle eşlemeyi yasaklıyor; değişirse kural yönetici kararıyla değişmeli.)
4. **Misafir sayısı:** fiyatlar 2 yetişkin için soruluyor; büyük evlerde kişi başı ücret olan sitelerde fiyat değişebilir. Pencere başına farklı misafir sayısı istenir mi?
5. **Fiyat formu olmayan ResCMS siteleri** (Sanders Beach Rentals, funvacay.com, Coastal Blue Vacations): yalnız müsaitlik takvimi var; müsaitlik bilgisi tek başına toplansın mı?
6. **v0.11.0'ın main'e alınması.**
