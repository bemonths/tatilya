# GÖREV-07 Raporu — v0.9.0 yayını, bilgi toplama ilkesi, referans tablosu, konaklama profili

Tarih: 7 Ekim 2026 · Dal: `gorev-07-konaklama` · Uygulama `0.10.0` · Şema `10`

## Kısaca

- **Adım 1 tamam:** main `7110f88`'e getirildi, `v0.9.0` etiketi konuldu; ikisinin CI'ı da başarılı.
- **Adım 2 tamam:** yeni bilgi toplama ilkesi CLAUDE.md'ye ve CALISMA_MANTIGI §4'e yazıldı, kısıtlayıcı kurallar değiştirildi (ayrı commit `6e3776f`). İlk denemeyi Claude Code'un otomatik izin denetimi engellemişti; kullanıcı izin modunu değiştirdikten sonra uygulandı.
- **Adım 3 büyük ölçüde tamam:** referans tablosu 85 → 103 satır; yeni durum `yerine_gecildi`. Eyalet parkı ücretleri, Timpoochee'nin ilçe değeri ve 30A hız sınırları bulunamadı.
- **Adım 4 tamam:** Book>Direct konaklama toplayıcısı (şema 10, Konaklama sekmesi, 40 test). Canlı keşifte ön yüzün canlı fiyat mantığı okundu ve toplayıcı ona göre düzeltildi.
- **Adım 5 tamam:** belgeler (M10 yeni; M9 ve durum satırları güncel); 555 Python + 46 frontend testi art arda 3 kez geçti.
- **Adım 6 tamam:**
  - geçici klasörde canlı deneme: 72,7 dk, 2.659 istek;
  - gerçek veritabanının kopyasında v9 → v10 geçiş denemesi;
  - tam yedekten sonra gerçek veritabanında konaklama çekimi: 72,6 dk, 2.655 istek, 2.389 benzersiz ilan. Kontroller temiz, istemci anahtarı hiçbir yere yazılmadı.
- **Ana bulgu:** kaynak her mahallede ilan sayısını, türünü, oda sayısını ve kapasitesini veriyor, ama **fiyatı çok az ilan için veriyor**. Fiyat seviyesi için tek başına yetmiyor (ayrıntı aşağıda).

## Adım 1 — v0.9.0'ı main'e alma ve etiketleme

| | |
|---|---|
| main | `git merge --ff-only origin/gorev-06-referanslar` ile `7110f881e69793b907ecd791a52e761d569cdfd1`'e getirildi ve push edildi |
| Etiket | `v0.9.0` önceden yoktu; açıklamalı etiket ("v0.9.0 — kasırga evre kuralı ve referans tablosu") `7110f88`'i gösteriyor, push edildi |
| main CI | çalıştırma 37655748525 — başarılı |
| Etiket CI | çalıştırma 37655792703 — başarılı |
| Görev dalı | güncel main'den `gorev-07-konaklama` açıldı |

GitHub ilk dakikalarda bütün push'ları "Internal Server Error" ile reddetti. Push'lar aralıklarla yeniden denendi; main 6. denemede geçti.

## Adım 2 — Bilgiye erişimi kısıtlayan kurallar

Commit `6e3776f` (ayrı commit). Değişen kurallar:

| Yer | Eski | Yeni |
|---|---|---|
| CLAUDE.md | Bilgi toplama bölümü yoktu | "Bilgi toplama" bölümü: görevdeki ilke metni aynen. Ek cümle: Claude Code CAPTCHA'yı ya da "insan olduğunuzu doğrulayın" ekranını çözmez ve tarayıcıyı bot tespitinden gizleyen ayar kullanmaz; sayfa normal bir tarayıcıda açılmazsa aynı bilgi başka resmî yayında aranır. Mimari bölümünde `bookdirect-lodging` genel connector'lar arasında. |
| CALISMA_MANTIGI §4 m.13 | "Playwright varsayılan değildir; HTTP/JSON ile çözülüyorsa kullanılmaz." | "İlk tercih API, JSON ve HTML'dir; gerekiyorsa tarayıcı otomasyonu kullanılır." (yalnız verimlilik tercihi) |
| CALISMA_MANTIGI §4 m.14 | Düzenli toplayıcılar robots.txt'ye uyar; tek seferlik belge alımı toplayıcı sayılmaz | Yeni bilgi toplama ilkesi ve aynı ek cümle |
| CALISMA_MANTIGI §9.6 | NCEI "robots.txt `/data*` yolunu kapattığı için yalnız bu yol" | "ilk tercih API olduğu için bu yol" |
| DEVIR/03 | "connector işletmenin sitesini crawl etmez"; anti-pattern "External site URL'sini otomatik crawl etme" | İşletme sitesi, dizindeki bağlantıyla kimliği belli olduğu için doğrudan okunabilir (adres, tarih, ham kopyayla); anti-pattern kaldırıldı |
| DEVIR/06 | Restoran zenginleştirmesi için önce entity matching, menü sürümleme, fiyat anlamı şartı; market için "maliyet ve değişkenlik yüksek"; POI için "eşleştirme olmadan birleştirilmemeli" | Üçü de "yapılabilir, kaynak ve tarihle"; POI kaydı mevcut kayda ancak açık bağla bağlanır |
| DEVIR/07 | "Şu an senden beklenmeyenler": 6 madde (AI, video, ikinci destinasyon ayrı ayrı) | Geçerli olanlar: tarihli aramayı tam envanter diye adlandırmamak, görevde olmayan aşamaya kendiliğinden geçmemek, production DB'yi sıfırlamamak, kaynakları sessizce değiştirmemek; "bilgiye erişim için ayrı yasak yok" notu; kaynak araştırmasında "gerekirse gerçek tarayıcıyla oku" |
| M9 | "Bot doğrulamalı sayfa otomasyonla aşılmaz"; §4 m.14'ün eski anlatımı | Eski metin duruyor; tarihli karar notu |
| M4, M6, M8, MIMARI | İşletme sitesine istek yapılmaz / "crawl edilmez" / robots.txt değerlendirmesi / "kapsam dışında kalır" | Tarihli notlar: bunlar mevcut toplayıcının davranışı, yasak değil |
| GÖREV-02 keşfi | "robots.txt kapalı / bot korumalı olduğu için kullanılamaz" değerlendirmeleri (Municode, NCEI `/data`, Clerk, `/userfiles/`, eyalet parkları, Florida Forest Service, OSM) | Başa ve ilgili 9 yere tarihli not; eski metin duruyor |
| GÖREV-06 | "Görev gereği otomasyonla aşılmadı", "başka mevzuat aranmadı" | Tarihli notlar; görev metninin sonuna not |

## Adım 3 — Referans tablosunun tamamlanması

Yeni belgeler `work/referans-belgeler/` altına SHA-256 ile kaydedildi (31 alım; 5'i 403/404). Yeni satırların 15 kısa alıntısının hepsi kaydedilen belgede birebir bulundu. Doğrulayıcıya `yerine_gecildi` durumu eklendi: eski satır silinmez, notunda `yerine geçen: <kimlik>` yazar ve o kimlik doğrulanmış bir satır olmalıdır. Referanslar sekmesi bu durumu sayar ve yerine geçen satırı gösterir.

| Konu | Sonuç |
|---|---|
| Parklar (Grayton Beach, Topsail Hill, Deer Lake) | **Çözülemedi.** Uygulama içi tarayıcı floridastateparks.org'a girişi iki kez reddetti (tarayıcının kendi site izni). Düz HTTP isteği park sayfasında ve eyaletin ücret çizelgesi PDF'inde 403 (Cloudflare) verdi. Başka resmî yayında ücret ve saat bulunamadı. 6 satır "doğrulanamadı". |
| Plajda alkol | **Çözüldü.** İlçe plaj yönetmeliğinde hüküm yok. Walton County Tourism'e göre yasal yaştaki yetişkinler içebilir, yalnız kutu veya plastikle; cam bütün plajlarda yasak. Eyalet parklarında alkol tüketimi, satış yapan restoran ve konaklama yerleri ile park etkinlikleri dışında yasak (Florida Administrative Code 62D-2.014(12)). 21 yaş altına bulundurmak yasak (Florida Statutes 562.111). Düşük hızlı araçta açık alkol kabı yasak (Walton County Sheriff). |
| Cankurtaran | **Çözüldü, ikincil kaynakla.** 2026 sezonu 1 Mart–31 Ekim, 10:00–18:00 (SoWal.com, 2 Mart 2026). Walton County Tourism'in sayfası aynı tarihleri veriyor. SWFD'nin kendi sitesinde 2026 duyurusu yok; SWFD SSS'si hâlâ 30 Eylül diyor. Yeni satır doğrulandı, iki eski satır `yerine_gecildi`. |
| Timpoochee Trail uzunluğu | **Çözülemedi.** Walton County'nin resmî uzunluk değeri bulunamadı. İki satır "çelişkili" kaldı. |
| 2025 ziyaretçi sayısı | **Çözüldü (yönetici kararı).** 4.586.000 doğrulandı; 4,57 milyon satırı `yerine_gecildi`. |
| Golf arabası / düşük hızlı araç | **Çözüldü.** İlçe: golf arabaları ilçe yollarında kullanılamaz. Şerif: hiçbir kamu yolunda kullanılamaz. İlçenin golf arabasına açtığı bir yol bulunamadı. Düşük hızlı araç: yalnız 35 mph ve altındaki yollar; kaldırımda ve bisiklet yolunda yasak; US 98'de yasak, yalnız dört yollu kavşakta karşıya geçilebilir. |
| 30A hız sınırları | **Çözülemedi.** Resmî karar veya trafik çalışması belgesi bulunamadı. İlçe meclisinin 35 mph azami hız önerisini onayladığını aktaran tek haber (DeFuniak Herald) Cloudflare doğrulaması nedeniyle okunamadı. |
| Planlı topluluklar | **Kısmen.** Seaside: saatlik, güne ve doluluğa göre değişen ücretli otopark ve 06:00–24:00 ücretsiz servis. Alys Beach: işaretli yerlerde ücretsiz ziyaretçi otoparkı; plaj ve plaj erişimleri halka kapalı. WaterColor: topluluk derneğinin yönettiği ücretli park yerleri (otelin SSS'sinden, ikincil). Rosemary Beach ve WaterSound sitelerinde ziyaretçi otoparkı bilgisi bulunamadı. |

| Konu | Satır | Doğrulandı | Çelişkili | Doğrulanamadı | Yerine geçildi |
|---|---:|---:|---:|---:|---:|
| Plaj kuralları | 29 | 29 | 0 | 0 | 0 |
| Güvenlik | 13 | 11 | 0 | 0 | 2 |
| Plaj erişimi | 17 | 15 | 0 | 2 | 0 |
| Ulaşım | 17 | 14 | 2 | 1 | 0 |
| Parklar | 8 | 2 | 0 | 6 | 0 |
| Kasırga sezonu | 2 | 2 | 0 | 0 | 0 |
| Sezon ve maliyet | 14 | 13 | 0 | 0 | 1 |
| Genel | 3 | 3 | 0 | 0 | 0 |
| **Toplam** | **103** | **89** | **2** | **9** | **3** |

## Adım 4 — Konaklama profili toplayıcısı

`studio/sources/bookdirect_lodging.py` (`bookdirect-lodging/1`), şema 10, Veri toplama → Konaklama sekmesi; ayrıntı `docs/M10-KONAKLAMA-PROFILI.md`.

- **Genel toplayıcı:** clone adresi, konum filtresi eşlemesi ve tarih pencereleri SQLite'ta. 30A için:
  - `visitsouthwalton.bookdirect.net`;
  - 14 konum filtresi: 13 mahalle, Watercolor ve Watersound yazımlarıyla; Seagrove Beach da Seagrove'a bağlı ve her satır hangi filtreden geldiğini saklıyor;
  - görevdeki 4 tarih penceresi.
- **İstemci anahtarı:** her çekimde giriş sayfasının gösterdiği güncel paketten okunur, yalnız bellekte tutulur. Paket gövdesi ve anahtarı içeren hiçbir yanıt saklanmaz.
- **Toplama:**
  - her pencere × filtre için bütün arama sayfaları;
  - sınırlı denemeli canlı fiyat;
  - her ilan için bir fiyat takvimi; veritabanına yalnız aylık özeti yazılır;
  - geçmiş pencere atlanır ve kaydedilir;
  - istekler sıralı, 1,25 sn arayla; ham yanıtlar gzip ve SHA-256 ile saklanır;
  - iptal edilebilir; sonuç tek transaction'da yazılır.
- **Okuma anında özet:** mahalle × pencere ve mahalle × ay; görevdeki etiketle.
- **Canlı keşifte okunanlar (ön yüz paketi, 7 Ekim 2026):**
  - ön yüz sayfa başına 10 ilan gösteriyor;
  - canlı fiyatı yalnız arama fiyatı olmayan ya da fiyatı beklemede olan ilanlar için soruyor;
  - beklemedeki yanıtları 20 denemeye kadar, 1 sn + 0,75 sn × deneme arayla yeniden soruyor;
  - güncel canlı fiyat arama fiyatının yerine geçiyor.

  Toplayıcı buna göre düzeltildi (commit `cbc502b`): aynı seçim kuralı (ek olarak `live_rates_enabled` işaretli ilanlar da soruluyor), aynı bekleme aralığı, en fazla 5 deneme, fiyat önceliğinde önce güncel canlı fiyat.
- **Testler:** 40 Python testi (görevdeki bütün başlıklar) ve 4 frontend testi.

## Adım 5 — Belgeler ve testler

- Yeni: `docs/M10-KONAKLAMA-PROFILI.md`.
- Güncellenen: `docs/M9-REFERANS-TABLOSU.md`, `CALISMA_MANTIGI.md`, `README.md`, `docs/DEVIR/02`, `05`, `07`, `docs/ASAMALAR.md`, `docs/M6`. Kural metinleri Adım 2'de değişti.
- Uygulama `0.10.0`, şema `10`.
- Testler art arda 3 kez: **555 Python testi geçti** (görev başında 513), **46 frontend testi geçti** (görev başında 42). Her Python çalıştırmasında bilinen kütüphane uyarısı (Starlette/httpx).
- CI: dal commit'leri `71d51ef` ve `4ff7e00` başarılı. Son commit'in sonucu push'tan sonra kontrol edildi.

## Adım 6 — Gerçek ortam

1. **Geçici klasörde canlı deneme** (`work/gorev-07/temp-data`):
   - süre 72,7 dk, 2.659 istek;
   - 2.389 benzersiz ilan, 9.197 arama satırı, 52 canlı fiyat isteği;
   - şema 10, `integrity_check` ok, `foreign_key_check` boş;
   - istemci anahtarı 2.659 ham dosyada (gzip içerikleri dahil) ve veritabanı dökümünde yok;
   - ekran görüntüsü `konaklama-sekmesi-gecici-deneme.png`.
2. **Migration denemesi** (gerçek verinin `work/` kopyası):
   - v9 → v10;
   - eski bütün tabloların satır sayıları ve çekimler aynı;
   - eklenenler: 11 konaklama tablosu, 30A konaklama yapılandırması (1 clone, 14 filtre, 4 pencere) ve 1 kaynak;
   - `integrity_check` ok, `foreign_key_check` boş.
3. **Gerçek veritabanı** (CLAUDE.md kuralıyla):
   - **Yedek:** uygulama kapalıyken `data/` klasörünün tamamı `work/yedek/20261007-2235/` altına kopyalandı (384 dosya, 59.979.791 bayt; kopya ve kaynak karşılaştırıldı, aynı).
   - **Açılış:** uygulama gerçek veriyle açıldı. Önce kendi yedeğini aldı (`data/backups/studio-v9-f6412e0032864a4d8088398d54fe0223.sqlite3`), sonra şemayı 10'a yükseltti.
   - **Çekim:** yalnız konaklama toplayıcısı çalıştırıldı (çekim `abe7764d13cb4c9198e2b873ebc4d7c7`): 72,6 dk, 2.655 istek, 2.389 ilan, 9.189 arama satırı, 48 canlı fiyat isteği. Uygulama düzgün kapatıldı.
   - **Sonra:**
     - şema 10, `integrity_check` ok, `foreign_key_check` boş;
     - değişen satır sayıları: jobs 17 → 18, source_runs 14 → 15, sources 12 → 13; yeni tablolar: lodging_listings 2.389, lodging_search_results 9.189, lodging_calendars 2.389, lodging_rate_months 923, lodging_calendar_windows 9.556, lodging_filters 56;
     - eski 14 çekim aynı;
     - istemci anahtarı `data/` altındaki 3.039 dosyada ve veritabanında yok;
     - `data/` 384 → 3.040 dosya (2.655 ham yanıt ve manifest, 1 uygulama yedeği).
   - **Ekran görüntüsü:** `konaklama-sekmesi-gercek-veri.png`, gerçek verinin kopyasından.
   - **Kesinti:** çekim sırasında izleme betiğim yerel bir bağlantı hatasıyla kapandı. Çekim etkilenmedi; izleme yeniden başlatıldı.

## Konaklama çekiminin sonuçları (gerçek veri, arama günü 7 Ekim 2026)

Bu sayılar o gün yapılan aramalarda görünen ilanlardır; tam envanter değildir. Seagrove satırı Seagrove ve Seagrove Beach filtrelerinin birleşimidir.

| Mahalle | Sonbahar 2026 | Kış 2027 | Bahar tatili 2027 | Yaz 2027 | Tür (Sonbahar 2026, kaynak kategorileri) | Yatak odası ortancası / 4+ oda payı | Kapasite ortancası |
|---|---:|---:|---:|---:|---|---|---:|
| Dune Allen | 112 | 112 | 114 | 114 | ev 70, daire/villa 42 | 3 / %46 | 8 |
| Gulf Place | 27 | 28 | 31 | 31 | daire/villa 19, ev 8 | 3 / %17 | 8 |
| Santa Rosa Beach | 221 | 240 | 246 | 246 | ev 111, daire/villa 63, kiralama şirketi 47, kamp 3, otel 1, adsız kategori 7 | 3 / %45 | 10 |
| Blue Mountain Beach | 170 | 182 | 194 | 194 | daire/villa 88, ev 80, kiralama şirketi 1 | 3 / %48 | 10 |
| Grayton Beach | 85 | 86 | 86 | 86 | ev 80, daire/villa 4, pansiyon 1 | 4 / %62 | 10 |
| WaterColor | 241 | 247 | 258 | 259 | ev 200, daire/villa 40, otel 1 | 4 / %69 | 10 |
| Seaside | 111 | 170 | 214 | 221 | ev 103, daire/villa 7, kiralama şirketi 1 | 3 / %24 | 6 |
| Seagrove | 473 | 489 | 498 | 498 | ev 248, daire/villa 224, kiralama şirketi 4, otel 1, adsız kategori 7 | 3 / %39 | 8 |
| WaterSound | 162 | 163 | 165 | 165 | ev 91, daire/villa 67, resort 1, otel 1 | 3 / %32 | 9 |
| Seacrest | 287 | 294 | 301 | 301 | ev 187, daire/villa 97, kiralama şirketi 4 | 3 / %48 | 10 |
| Alys Beach | 2 | 7 | 7 | 7 | ev 2 | 3,5 / %50 | 8,5 |
| Rosemary Beach | 160 | 164 | 166 | 166 | ev 116, daire/villa 40, kiralama şirketi 2, otel 1, pansiyon 1, adsız kategori 1 | 3 / %31 | 8 |
| Inlet Beach | 92 | 94 | 101 | 101 | ev 71, daire/villa 18, kiralama şirketi 3 | 4 / %59 | 10 |

("ev" = Beach Homes & Cottages, "daire/villa" = Condominiums, Townhomes & Villas, "kiralama şirketi" = Rental Agencies (şirketin kendi kaydı, birim değil), "adsız kategori" = kaynağın bu sitede adını vermediği kategori kimliği.)

**Fiyat:**
- **Liste fiyatı:** 9.189 arama satırının yalnız 12'sinde dolu (11 ilan).
- **Canlı fiyat:** 48 istekte güncel canlı fiyat yalnız 1 satırda döndü.
- **Takvim:** 2.389 ilanın 1.536'sında takvim gizli. Takvimi fiyatlı 248 ilanın verisi yalnız Ekim 2026–Mart 2027'yi kapsıyor; yaz ayları yok.
- **Pencere fiyatı çıkan hücreler (13 mahalle × 4 pencerenin 6'sı):**
  - Seaside, Kış 2027: 170 ilanın 6'sında, ortanca 458 $ (çeyrekler 372–680 $);
  - WaterSound, Sonbahar: 2 ilan, 457 $;
  - WaterColor, Sonbahar: 1 ilan, 850 $; Kış: 1 ilan, 405 $;
  - Seacrest, Sonbahar: 1 ilan, 542 $;
  - Seagrove, Sonbahar: 1 ilan, 229 $.

Takvimden aylık ortanca gecelik fiyat (ilanların aylık ortancalarının ortancası, bizim hesabımız; parantezde takvimi o ayda fiyatlı ilan sayısı):

| Mahalle | Eki 2026 | Kas 2026 | Ara 2026 | Oca 2027 | Şub 2027 | Mar 2027 |
|---|---|---|---|---|---|---|
| Seaside | 770 $ (87) | 851 $ (113) | 894 $ (115) | 887 $ (116) | 932 $ (20) | 1.051 $ (20) |
| Blue Mountain Beach | 148 $ (29) | 136 $ (28) | 129 $ (26) | 112 $ (25) | — | — |
| Santa Rosa Beach | 317 $ (15) | 272 $ (18) | 185 $ (19) | 168 $ (18) | — | 315 $ (1) |
| WaterColor | 133 $ (14) | 121 $ (12) | 119 $ (11) | 112 $ (14) | — | 155 $ (1) |
| Seacrest | 197 $ (11) | 136 $ (10) | 119 $ (8) | 112 $ (8) | — | — |
| Inlet Beach | 186 $ (11) | 139 $ (9) | 128 $ (10) | 124 $ (10) | 326 $ (1) | 545 $ (1) |
| Seagrove | 322 $ (10) | 300 $ (13) | 266 $ (11) | 220 $ (11) | 151 $ (3) | 276 $ (4) |
| Rosemary Beach | 519 $ (8) | 338 $ (8) | 373 $ (8) | 434 $ (5) | 325 $ (1) | — |
| Gulf Place | 179 $ (6) | 169 $ (5) | 186 $ (4) | 120 $ (3) | 200 $ (1) | 281 $ (2) |
| WaterSound | 462 $ (4) | 344 $ (4) | 334 $ (4) | 299 $ (3) | 299 $ (1) | 412 $ (2) |
| Dune Allen | 250 $ (3) | 250 $ (3) | 250 $ (3) | 244 $ (3) | — | — |
| Grayton Beach | 422 $ (2) | 412 $ (2) | 411 $ (2) | 200 $ (1) | 202 $ (1) | 205 $ (1) |

Alys Beach'te takvimi fiyatlı ilan yok. Bu ortancaların çoğu birkaç ilana dayanıyor ve takvimini açan ilanların fiyatıdır; mahallenin fiyat seviyesi diye sunulamaz. Seaside'ın tabanı en geniş olanı (87–116 ilan).

Dosyalar: `konaklama-ozet.csv` (13 mahalle × 4 pencere), `konaklama-aylik-fiyat.csv` (mahalle × ay); ikisi de gerçek veritabanındaki çekimden.

## Teslim klasörü

`docs/gorevler/GOREV-07/`:
- `GOREV.md`, `RAPOR.md`;
- `referans-tablosu.csv`;
- `konaklama-ozet.csv`, `konaklama-aylik-fiyat.csv`;
- ekran görüntüleri: `konaklama-sekmesi-gecici-deneme.png`, `konaklama-sekmesi-gercek-veri.png`, `referanslar-sekmesi.png`.

## Beklenmedik durumlar

- **İzin denetimi:** Claude Code'un otomatik izin denetimi iki işlemi ilk denemede engelledi: kural belgelerinin değiştirilmesi (kendi talimatlarını değiştirme) ve Book>Direct istemci anahtarının okunup kullanılması (kimlik bilgisi keşfi). Kullanıcı izin modunu değiştirdikten sonra ikisi de yapıldı.
- **Eyalet parkları:** uygulama içi tarayıcı floridastateparks.org'a girişi hâlâ reddediyor.
- **GitHub:** push'lar birkaç dakika "Internal Server Error" ile reddedildi.
- **İzleme betiği:** gerçek çekim sırasında yerel bir bağlantı hatasıyla kapandı; çekim etkilenmedi.
- **Fiyat:** kaynak fiyatı beklenenden de seyrek veriyor. Takvimlerin %64'ü gizli; açık takvimler yalnız Mart 2027'ye kadar gidiyor.
- **Takvim istekleri:** görev her ilan için takvim istediği için çekimin ~55 dakikası takvim isteklerine gidiyor. Takvimi gizli ilanlarda bu istekler boş dönüyor.
- **İki çekim arası fark:** geçici deneme ile gerçek çekim arasında birkaç saat içinde küçük farklar var: arama satırı 9.197 / 9.189, liste fiyatlı satır 20 / 12. Kaynak canlı değişiyor.
- **Kategoriler:** 19 ilanda bu sitede adı verilmeyen kategori kimlikleri (5, 852, 9) var; 65 ilan "Rental Agencies", yani kiralama şirketinin kendi kaydı.
- **Seaside otopark sayfası:** tarih tutarsızlığı var. Başlık "Saturday, March 1, 2026", metin "Sunday, March 1, 2025" diyor.
- **Cankurtaran:** SWFD'nin SSS sayfası 2026'da da sezonu 30 Eylül diye veriyor.

## Yöneticinin karar vermesi gereken konular

1. **Fiyat kaynağı:** Book>Direct mahalle fiyat seviyesi için yetmiyor. Seçenekler:
   - kiralama şirketlerinin kendi sitelerinden fiyat okumak (yeni ilkeye uygun; kaynaktaki ilan kaydının `url` alanı şirketin ilan sayfasını gösteriyor; bu alan ham yanıtlarda var, veritabanına henüz yazılmıyor);
   - başka bir platform;
   - videoda fiyatı yalnız Walton County Tourism'in ADR değerleriyle (referans tablosu) vermek.
2. **Takvim istekleri:** takvimi gizli ilanlarda (1.536) takvim isteği atlanırsa çekim ~73 dakikadan ~35 dakikaya iner. Ön yüz de bu ilanlarda takvim göstermiyor. Görevdeki "her benzersiz ilan" kuralı değiştirilsin mi?
3. **Düzenli tekrar:** konaklama çekimi belirli aralıklarla tekrarlansın mı? Her çekim ayrı sürüm olarak saklanıyor.
4. **Cankurtaran 2026:** tarihli kaynak yerel haber sitesi (ikincil). SWFD'den resmî duyuru istensin mi?
5. **Eyalet parkı ücretleri:** kullanıcı kendi tarayıcısında bakıp iletirse tabloya elle (kaynak ve tarihle) eklenebilir; ya da videoda söylenmez.
6. **30A hız sınırları ve Timpoochee uzunluğu:** resmî belge bulunamadı. İlçeye sorulsun mu, videoda kullanılmasın mı?
7. **main'e alma:** gerçek veritabanı artık şema 10. main'deki 0.9.0 onu açmıyor; dal main'e alınana kadar uygulama `gorev-07-konaklama` dalından çalıştırılmalı.
