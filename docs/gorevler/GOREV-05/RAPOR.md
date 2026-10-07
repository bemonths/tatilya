# GÖREV-05 Raporu — Eşleme v3 ve iklim paketi

Tarih: 7 Ekim 2026 · Dal: `gorev-05-iklim` · Uygulama `0.8.0` · Şema `8`

## Kısa özet

Altı adımın hepsi tamamlandı. main `a7e38f2`'ye taşındı (etiket konmadı). Plaj–mahalle eşlemesi v3 olarak kuruldu: kaynağa dayalı eşleme (resmî rehber ve ilçe verisi) 15'ten 31 erişime çıktı; v2'de program türetimiyle Seaside'a atanan 9 erişimin 7'si artık ilçe verisiyle (bitişik), 2'si komşu tutarlılığıyla Seagrove'da. İklim paketi kuruldu: NOAA'nın üç kaynağından (iklim normalleri, deniz suyu sıcaklığı, kasırga izleri) veri toplayan üç genel toplayıcı, şema 8 ve "İklim" sekmesi. Canlı deneme, gerçek veri kopyasında geçiş denemesi ve gerçek veritabanının güncellenmesi sorunsuz geçti; bütünlük kontrolleri temiz.

| Commit | İçerik |
|---|---|
| `645e040` | Adım 2: eşleme v3 (ayrı commit) |
| `f5362ab` | Adım 3–5: iklim paketi, şema 8, İklim sekmesi, testler |
| `fdc7607` | belgeler (M8, M7, ana belgeler), bu teslim klasörü |
| `3ac526b` | GitHub'da başarısız test adlarını görünür yapan test ayarı |
| son commit | iki kararsız testin düzeltmesi ve raporun CI bölümü |

## Adım 1 — main ve yeni dal

- main `git merge --ff-only` ile `a7e38f25b28b8b72157d1f5eb3aa74058cfeebcf` (GÖREV-04) konumuna getirildi ve push edildi. Etiket konmadı; `v0.7.0` → `7f25e3c` olduğu gibi duruyor.
- main CI: **başarılı** (Actions run `37616103259`).
- Güncel main'den `gorev-05-iklim` dalı açıldı.

## Adım 2 — Eşleme v3

Yöntem sırası görevdeki gibi: resmî rehber → ilçe alt bölüm (içeride) → ilçe alt bölüm (bitişik, ≤ 30 m) → komşu erişimlerle tutarlı → program türetimi; Rosemary Beach–Alys Beach kısıtı her yöntemde. Alt bölüm sonuç dosyasına `alt_bolum_numarasi` (SUBDIVISION_NUMBER) eklendi; bunun için ilçe sorgusu aynı 53 nokta için yeniden çalıştırıldı (106 istek, ham yanıtlar `work/` altında). Ad tablosu kuralı değişmedi (37 ad). Eşleme, gerçek veritabanındaki plaj `1a195e2b…` ve mahalle `3d1cbe8d…` çekimleriyle üretildi. Plaj ekranında iki yeni etiket var: "ilçe alt bölüm verisi (bitişik)" (yeşil, kaynaklı) ve "komşu erişimlerle tutarlı" (yaklaşık). Videoda kullanım notu M7'ye yazıldı.

**Sonuç (53 erişim):** 9 resmî rehber, 6 ilçe alt bölüm, 16 ilçe alt bölüm (bitişik), 13 komşu erişimlerle tutarlı, 9 program türetimi; belirsiz yok. Resmî rehberle çelişki 1: Winston Lane - 4 Rosemary Beach alt bölümlerine 8,5 m; Rosemary'ye atanmadı (program türetimi Inlet Beach).

| Mahalle | Resmî | İlçe | Bitişik | Komşu | Türetim | v3 toplam | v2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dune Allen | 2 | 1 | 2 | 1 | 3 | 9 | 7 |
| Gulf Place | 1 | 0 | 0 | 0 | 0 | 1 | 3 |
| Santa Rosa Beach | 1 | 0 | 0 | 0 | 2 | 3 | 3 |
| Blue Mountain Beach | 1 | 0 | 3 | 0 | 0 | 4 | 4 |
| Grayton Beach | 1 | 2 | 1 | 0 | 0 | 4 | 4 |
| WaterColor | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Seaside | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| Seagrove | 2 | 2 | 9 | 11 | 0 | 24 | 15 |
| WaterSound | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Seacrest | 0 | 0 | 1 | 0 | 2 | 3 | 3 |
| Alys Beach | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Rosemary Beach | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Inlet Beach | 1 | 1 | 0 | 1 | 2 | 5 | 5 |

**Doğrulama** (yeni yöntemler 9 resmî eşlemeye uygulandı): ilçe (içeride) 1 aynı / 8 sonuçsuz / 0 farklı; bitişik 2 / 7 / 0; komşu 3 / 6 / 0; program türetimi 8 / 0 / 1; zincir 8 / 0 / 1. Yeni yöntemler hiçbir resmî eşlemede farklı sonuç vermedi; tek fark eskisi gibi Walton Dunes - 8 (zincirde program türetimi WaterSound, rehber Seagrove). Tablo: [esleme-dogrulama-v3.csv](esleme-dogrulama-v3.csv).

**v2 → v3:** 29 satır değişti, 11'inde mahalle: Palms of Dune Allen West/East Gulf Place → Dune Allen (bitişik); Dogwood/Thyme - 29, Hickory - 28, Live Oak - 27, Nightcap Street - 26, Holly - 24, Azalea/Camellia - 23, Gardenia - 22 Seaside → Seagrove (bitişik); Headland Ave, Greenwood - 21 Seaside → Seagrove (komşu). Kalan 18'inde yalnız yöntem değişti. Tablo: [esleme-v2-v3-fark.csv](esleme-v2-v3-fark.csv). Ad tablosu: [alt-bolum-adlari-v3.csv](alt-bolum-adlari-v3.csv). Ekran: [plaj-ekrani-esleme-v3.png](plaj-ekrani-esleme-v3.png) (gerçek veritabanının `work/` kopyası; Seagrove filtresi, listede bitişik, ayrıntıda komşu etiketi).

Not: Seaside, WaterColor ve WaterSound'a hiç erişim atanmadı. Bu yöntemin ve verinin sonucudur; "orada halka açık plaj erişimi yok" anlamına gelmez.

## Adım 3–5 — İklim paketi

Üç toplayıcı genel çekirdekte; istasyonlar, kıyı koridoru ve yarıçaplar SQLite'taki destinasyon yapılandırmasından geliyor (30A değerleri profil ve geçiş adımı yazıyor). Her yanıt ham olarak SHA-256 ile saklanıyor; iptal ve hata önceki sürümü bozmuyor; üçünde de "sürüm farkı" özeti gerekçesiyle kapalı. Şema 8, uygulama 0.8.0. Hesapladığımız değerler "NOAA verisinden bizim hesabımız" diye etiketli.

- **İklim normalleri (NCEI 1991–2020).** Destin–Fort Walton Beach Havalimanı (kıyı referansı) ve DeFuniak Springs (iç kesim karşılaştırması). Yedi değişken; kodlar API'de ve NCEI belgesinde doğrulandı. Her değerle tamlık bayrağı, ölçüm bayrağı ve yıl sayısı saklanıyor; eksik değer boş (NULL) kalıyor. NCEI'nin robots.txt kuralı `/data*` yolunu kapattığı için yalnız veri API'si kullanılıyor.
- **Deniz suyu sıcaklığı (NDBC, PCBF1 Panama City Beach).** 2005'ten bir önceki yıla kadar bütün yıllık dosyalar indiriliyor; olmayan yıl (404) kaydedilip atlanıyor. Eksik değer işaretleri (99,0 / 999,0) atlanıyor. Yıl-ay ortalaması, ölçüm ve gün sayısı saklanıyor; ham ölçümler veritabanına yazılmıyor. Çok yıllı ortalamaya yalnız en az 20 günü ölçümlü yıl-aylar giriyor.
- **Kasırga geçmişi (NHC HURDAT2).** Güncel dosya adı NHC veri sayfasından okunup kaydediliyor. Koridor: programdaki en batı (Stallworth Preserve) ve en doğu (Lupine - 1) plaj erişimi arası. İzler 1 saatlik ara değerlemeyle sıklaştırılıyor; her fırtına için koridora en yakın uzaklık, 50 ve 100 deniz mili için ilk giriş zamanı/ayı, daire içindeki en yüksek rüzgâr ve sınıf (TD, TS, HU, MH) saklanıyor. Bütün yıllar saklanıyor; dönem okuma anında seçiliyor.
- **İklim sekmesi.** Üç düğme ve son çekimler; aylık tablo (Destin normalleri °F/inç ve °C/mm, isteğe bağlı DeFuniak karşılaştırması, deniz suyu ortalaması ve kullanılan yıl sayısı); bayraklar ve NCEI açıklaması; kasırga bölümü (yarıçap ve dönem seçimi, aylara ve sınıflara göre sayılar, en yakın geçen 10 fırtına). Her tablonun altında kaynak ve "bizim hesabımız" etiketi var. Ekran: [iklim-sekmesi.png](iklim-sekmesi.png).

Ayrıntılı yöntem, veri modeli ve sınırlar: [M8-IKLIM-VERISI.md](../../M8-IKLIM-VERISI.md).

## Testler ve CI

- Python: 408 → **479**; frontend: 30 → **37**. Adım 2 ile 415 + 31 oldu; iklim paketi 64 Python ve 6 frontend testi ekledi. Mevcut testler şema 8'e, 12 kaynağa ve 0.8.0'a göre güncellendi (davranışları değişmedi).
- İklim testleri: değişken eksikliği (NULL), boş ve özel değerler, bayrak ve yıl sayısı saklama; NDBC eksik değer işaretleri ve 20 gün kuralı (19/20 gün sınırı); yıl dosyası 404 ve hiç dosya olmaması; HURDAT2 başlık ve iz satırları, yapı hataları; ara değerleme; mesafe hesabı (ekvatordaki test koridorunda beklenen değerler hesaptan bağımsız); yarıçap içi ilk giriş, ay sınırı, yeniden giriş ve sınıf; güncel dosya adının okunması; HTTP sınırları; iptal; her toplayıcı için atomik geri alma; v7 → v8 geçişi, yedek ve geri alma; destinasyon yalıtımı; şema kısıtları; arayüz yardımcıları.
- Testler canlı ağa bağlanmıyor.
- CI: main @ `a7e38f2` başarılı (`37616103259`); dal @ `645e040` başarılı (`37617433517`); dal @ `f5362ab` başarılı (`37621670802`); dal @ `fdc7607` (belgeler) **başarısız** (`37623562964`, pytest adımı); dal @ `3ac526b` başarılı (`37624672327`). Son commit'in sonucu GitHub Actions'ta.
- `fdc7607`'deki hata kod değişikliğinden değil, ara sıra düşen iki testten kaynaklanıyordu (GitHub iş günlüğü oturum açmadan okunamadığı için yerelde tekrar çalıştırılarak bulundu):
  1. Yeni iklim testi "API üzerinden iptal", işin ikinci isteğe 3 sn içinde ulaşmasını bekliyordu; Windows'ta ölçümde iki istek arasında 3,3 sn'lik duraklama görüldü. Aynı kalıptaki 2–3 sn'lik bekleme sınırları dört test dosyasında 30 sn'ye çıkarıldı (GÖREV-04'teki `finished()` düzeltmesiyle aynı ilke; geçen testte bekleme hemen biter).
  2. Eski bir plaj testi ("desteklenmeyen kaynak hiç çekilmez"), kaynak listesindeki ilk plaj dışı kaynağın toplayıcısı olmadığını varsayıyordu. Liste kayıt anının milisaniye damgasına ve ada göre sıralandığı için damga sınırı denk geldiğinde restoran veya hava kaynağı seçiliyordu (yeni veritabanıyla 200 denemede 3); v8 ile kaynak sayısı artınca bu olasılık arttı. Test artık toplayıcısı olmayan kaynağı açıkça seçiyor.
  - Düzeltmeden sonra bu dört test dosyası yerelde art arda 30 kez, tam takım 8 kez hatasız geçti. Ayrıca GitHub'da başarısız testlerin adları artık oturum gerektirmeyen "annotation" olarak da yazılıyor (`tests/conftest.py`).

## Adım 6 — Canlı deneme, geçiş denemesi ve gerçek veritabanı

**1. Canlı deneme** (`work/gorev-05/temp-data`, gerçek `data/` kullanılmadı, 7 Ekim 2026 12:25 UTC): üç toplayıcı başarılı.

| Toplayıcı | Süre | Sonuç |
|---|---|---|
| İklim normalleri | 2 sn | 2 istasyon × 12 ay × 7 değişken = 168 değer; eksik değer 0 |
| Deniz suyu sıcaklığı | 20 sn | 21 yıl denendi; 17 yılın dosyası var, 2009–2012 yok (404); 182 yıl-ay ortalaması; 1.147.280 geçerli ölçüm, 51.201 eksik işaretli ölçüm |
| Kasırga izleri | 7 sn | `hurdat2-1851-2025-092326.txt`, 1.988 sistem (1851–2025); 50 deniz mili içinde 79, 100 içinde 148 geçiş |

**2. Geçiş denemesi** (gerçek veritabanının `work/` kopyası, v7 → v8): şema 8, `integrity_check` ok, `foreign_key_check` boş; uygulama kendi yedeğini aldı; eski tabloların satır sayıları ve içerikleri aynı; yalnız 8 yeni tablo, 3 istasyon ve 1 koridor yapılandırması ve 3 kaynak eklendi (sources 9 → 12).

**3. Gerçek veritabanı** (CLAUDE.md kuralına göre):
1. Uygulamanın kapalı olduğu doğrulandı (30A Studio süreci yok, 8830 boş, `data/` içinde -wal/-shm yok).
2. `data/` klasörünün tamamı `work/yedek/20261007-1533/` altına kopyalandı: **352 dosya, 29.341.004 bayt**; bütün dosyaların boyutu ve SHA-256'sı kaynakla aynı, kaynak kopyalama sırasında değişmedi.
3. Uygulama gerçek veriyle açıldı; v7 → v8 geçişini kendi yedeğiyle yaptı: `data/backups/studio-v7-ff556c8bc97447fca0bafa160eb7a9a7.sqlite3`.
4. Yalnız üç iklim toplayıcısı API üzerinden çalıştırıldı (12:33 UTC): normaller `80f41ce6…` 168 değer (2 sn); deniz suyu `a8cbe865…` 182 yıl-ay (16 sn); kasırga `f803f353…` 227 geçiş (9 sn). Sonuçlar canlı denemeyle aynı.
5. Uygulama Ctrl+Break ile düzgün kapandı (çıkış kodu 3, normal); `data/` içinde -wal/-shm kalmadı. Sayım, veritabanının salt okunur kopyasından:

| Tablo | Önce (şema 7) | Sonra (şema 8) |
|---|---:|---:|
| sources | 9 | 12 |
| jobs | 13 | 16 |
| source_runs | 10 | 13 |
| destination_climate_stations / destination_storm_corridors | — | 3 / 1 |
| climate_normal_stations / climate_normal_values | — | 2 / 168 |
| water_temperature_stations / water_temperature_months | — | 1 / 182 |
| storm_corridor_snapshots / storm_passages | — | 1 / 227 |
| beach_records, weather_*, restaurant_*, neighborhood_records, regions, source_history ve diğerleri | aynı | aynı |

`integrity_check` ok, `foreign_key_check` boş. Eski kaynak ve çekim satırları birebir aynı. `data/` içinde 28 yeni dosya var (uygulama yedeği ve üç çekimin ham dosyaları).

## İlk videoda kullanılabilecek başlıca rakamlar

Hepsi 7 Ekim 2026 çekimlerinden; ayrıntı teslim CSV'lerinde.

1. **Temmuz sıcaklığı.** "30A'ya en yakın kıyı istasyonu Destin'in (Destin–Fort Walton Beach Havalimanı) 1991–2020 normali": Temmuz ortalama en yüksek sıcaklık **90,9 °F (32,7 °C)**; NCEI tamlık bayrağı R (temsilî), 18 yıl. İç kesimdeki DeFuniak Springs'te aynı değer 92,3 °F (33,5 °C). "En yakın" ifadesi doğrulandı: sıcaklık normali olan istasyonlar içinde Destin 30A kıyı koridoruna en yakın olanı (20,5 km); ikinci NW Florida Beaches Havalimanı (21,7 km).
2. **Deniz suyu.** "PCBF1 (Panama City Beach) ölçümlerinden hesaplanan aylık ortalama — NOAA verisinden bizim hesabımız": Mayıs **25,1 °C (77,2 °F)**, 15 yıl; Ekim **25,9 °C (78,5 °F)**, 15 yıl (2005–2025 arasındaki yıllar; 2009–2012 dosyası yok). İstasyon 30A kıyı koridorunun doğu ucuna 12,9 km; 30A kıyısındaki suyla aynı olduğu doğrulanmadı.
3. **Kasırgalar.** "NOAA NHC HURDAT2 kayıtlarından bizim hesabımız": 1991–2025'te merkezi 30A kıyı koridoruna 50 deniz mili (93 km) içinden geçen ve bu daire içinde kasırga gücüne (≥ 64 kt) ulaşan **5 fırtına**: Temmuz 1 (Dennis 2005, büyük kasırga), Ağustos 1 (Erin 1995), Eylül 1 (Earl 1998), Ekim 2 (Opal 1995 ve Michael 2018, büyük kasırga); diğer aylarda 0. Aynı dairede bütün fırtınalar (TD dahil) 20: Mayıs 1, Temmuz 3, Ağustos 7, Eylül 4, Ekim 4, Kasım 1. Ay, fırtınanın daireye ilk girdiği aydır; sınıf daire içindeki en yüksek rüzgârdır (karaya çıkış şiddeti değildir). Tablo: [kasirga-aylik-1991-2025.csv](kasirga-aylik-1991-2025.csv).

## Belgeler

Yeni [M8-IKLIM-VERISI.md](../../M8-IKLIM-VERISI.md). M7'ye v3 bölümü ve yeni ekran görüntüsü; CALISMA_MANTIGI.md, README.md, DEVIR/02, 05 ve 07, ASAMALAR.md güncel duruma göre düzeltildi; CLAUDE.md'deki mimari sınır satırına iklim toplayıcıları (genel çekirdek) eklendi.

## Teslim dosyaları

- [GOREV.md](GOREV.md) (görev metninin kopyası), bu rapor
- [esleme-v2-v3-fark.csv](esleme-v2-v3-fark.csv), [esleme-dogrulama-v3.csv](esleme-dogrulama-v3.csv), [alt-bolum-adlari-v3.csv](alt-bolum-adlari-v3.csv)
- [iklim-normalleri.csv](iklim-normalleri.csv) — 2 istasyon × 12 ay, 7 değişken; her değişken için değer, tamlık ve ölçüm bayrağı, yıl sayısı
- [deniz-suyu-aylik.csv](deniz-suyu-aylik.csv) — `tablo` sütunu `cok_yillik_ozet` (12 ay) ve `yil_ay` (182 satır; ölçüm ve gün sayısı, ortalamaya girip girmediği)
- [kasirga-gecisleri.csv](kasirga-gecisleri.csv) — iki yarıçap, bütün sezonlar, 227 geçiş
- [kasirga-aylik-1991-2025.csv](kasirga-aylik-1991-2025.csv) — iki yarıçap için aylara ve sınıflara göre sayılar ve toplam
- Ekranlar: [iklim-sekmesi.png](iklim-sekmesi.png), [plaj-ekrani-esleme-v3.png](plaj-ekrani-esleme-v3.png)

## Beklenmedik durumlar

1. **PCBF1'in 2009–2012 yıllık dosyaları NDBC'de yok (404).** Çok yıllı ortalamalar ay başına 13–16 yıldan hesaplanıyor; kullanılan yıl sayısı her ayda gösteriliyor.
2. **Kasırga sayımında tropikal olmayan evreler.** 1991–2025'te 50 deniz mili içindeki 20 geçişin 5'inde en yüksek rüzgâr fırtınanın tropikal olmayan veya subtropikal bir evresinde (2 ekstratropikal, 2 alçak basınç, 1 subtropikal depresyon). Sınıf yalnız rüzgâra göre; evre ayrıca saklanıyor ve gösteriliyor. 5 kasırganın hepsi kasırga evresinde.
3. **Daha yakın yağış istasyonları var.** NCEI'de yalnız yağış normali olan iki gönüllü gözlem istasyonu 30A'ya Destin'den yakın: Panama City Beach 5.9 WNW (6,0 km) ve Freeport 3.4 S (14,0 km). Sıcaklık için en yakın istasyon Destin; yağış için bu iki istasyon kullanılmadı.
4. **NCEI bayrakları.** İki istasyonda da sıcaklık ve yağış normalleri R (temsilî), yağışlı gün sayıları P (geçici: eksik aylar doldurulamamış). Destin'in Kasım "≥ 90 °F gün" ve "≤ 32 °F gün" değerleri 0,0 ama X bayraklı: NCEI'ye göre "sıfır olmayan değer sıfıra yuvarlandı".
5. **Profildeki Destin uzaklığı ilk yazımda 20,6 km'ydi;** profil değerlerini hesapla karşılaştıran test bunu yakaladı (doğrusu 20,5 km). Gerçek veritabanına girmeden düzeltildi.
6. **Gerçek veritabanı artık şema 8.** main'deki 0.7.0 bu dosyayı "daha yeni bir uygulama sürümüne ait" diyerek açmıyor (veriye dokunmadan durur). Bu dal main'e alınana kadar uygulama `gorev-05-iklim` dalından çalıştırılmalı.
7. Deniz suyu ortalamasının yöntemi denetlendi: düz aylık ortalama yerine günlük ortalamaların ortalaması alınsaydı aylık değerler en fazla 0,01 °C değişirdi.
8. Belge commit'inde (`fdc7607`) GitHub testleri bir kez düştü; nedeni ara sıra düşen iki testti ve düzeltildi (ayrıntı "Testler ve CI" bölümünde).

## Yöneticinin karar vermesi gereken konular

1. **Kasırga sayımı:** Tropikal olmayan evrelerdeki rüzgârlar (ekstratropikal, alçak basınç vb.) sayıma girmeye devam etsin mi, yoksa yalnız tropikal ve subtropikal evreler mi sayılsın?
2. **Yağış referansı:** 30A'ya daha yakın iki yağış istasyonu (6,0 km ve 14,0 km) yağış normali için eklensin mi?
3. **Deniz suyu boşluğu:** 2009–2012 boşluğu aynı istasyonun NOS CO-OPS verisinden doldurulmaya çalışılsın mı?
4. **Video dönemi:** Kasırga rakamları 1991–2025 (en güncel) mi, yoksa normallerle aynı 1991–2020 mi kullanılsın? İkisi de arayüzde seçilebiliyor.
5. **main'e alma ve etiket:** `gorev-05-iklim` main'e alınıp `v0.8.0` etiketi konsun mu? (Gerçek veritabanı zaten şema 8.)
