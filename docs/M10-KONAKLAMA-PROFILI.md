# M10 — Konaklama profili (Book>Direct tarihli arama anlık görüntüleri)

Tarih: 7 Ekim 2026 · Görev: GÖREV-07 · Dal: `gorev-07-konaklama` · Uygulama `0.10.0` · Şema `10`

> **GÖREV-08 güncellemesi (8 Ekim 2026, `bookdirect-lodging/2`, şema 11):** ilan kaydındaki şirket ilan sayfası (`url`) ve telefonlar (`phone`, `toll_free`) saklanıyor; takvimi gizli ilanlarda (`hide_rate_calendar`) takvim istenmiyor, atlanan ilan sayısı çekim kaydında (`calendars_skipped_hidden`). Çekim ~73 dakikadan ~35 dakikaya indi. Kaynakta şirket veya sahip adı alanı yok; bağlantının gösterdiği şirket sitesi fiyatları M11'de (`docs/M11-KONAKLAMA-FIYATLARI.md`).

## Durum

Toplayıcı, şema, arayüz ve testler hazır; 7 Ekim 2026'da geçici klasörde ve gerçek veritabanında çalıştırıldı (Claude Code'un izin denetimi ilk denemeyi engellemişti; kullanıcı izin modunu değiştirdikten sonra çalıştırıldı). Özet dosyaları: `docs/gorevler/GOREV-07/konaklama-ozet.csv`, `konaklama-aylik-fiyat.csv`.

## 7 Ekim 2026 çekimleri

| | Geçici klasör (`work/gorev-07/temp-data`) | Gerçek veritabanı |
|---|---:|---:|
| Süre | 72,7 dk | 72,6 dk |
| İstek | 2.659 | 2.655 |
| Benzersiz ilan | 2.389 | 2.389 |
| Arama satırı (pencere × filtre × ilan) | 9.197 | 9.189 |
| Canlı fiyat isteği | 52 | 48 |
| Liste fiyatı olan arama satırı | 20 | 12 |
| Güncel canlı fiyat (liveness 0) olan satır | 13 (her durum) | 1 |
| Fiyat takviminde en az bir fiyatlı gün olan ilan | 248 | 248 |

Gerçek çekim: `abe7764d13cb4c9198e2b873ebc4d7c7`, ön yüz sürüm yolu `/20261006094543/`, 4 pencerenin hepsi arandı, kapsam dışı 5 konum filtresi (Defuniak Springs, Freeport, Miramar Beach, Sandestin, Seascape). İstemci anahtarı ne ham dosyalarda (2.655 yanıt, gzip içerikleri dahil) ne veritabanında bulundu.

**Ne verdi:** her mahallede aramada görünen ilan sayısı, türü, yatak odası ve kapasite. Sonbahar 2026 penceresinde mahalle filtrelerine göre ilan sayısı: Seagrove (Seagrove Beach filtresiyle birlikte) 473, Seacrest 287, WaterColor 241, Santa Rosa Beach 221, Blue Mountain Beach 170, WaterSound 162, Rosemary Beach 160, Dune Allen 112, Seaside 111, Inlet Beach 92, Grayton Beach 85, Gulf Place 27, Alys Beach 2. Bütün ilanlarda kaynak kategorileri: Beach Homes & Cottages 1.547, Condominiums, Townhomes & Villas 770, Rental Agencies 65 (kiralama şirketinin kendi kaydı; birim değil), Hotels 6, Campgrounds & RV Parks 3, Bed & Breakfast Inns 2, Resorts 2; 19 ilanda kaynağın bu clone'da adını vermediği kategori kimlikleri (5, 852, 9) var.

**Ne vermedi:** fiyat. Aramalarda liste fiyatı yalnız birkaç ilanda dolu; canlı fiyat neredeyse hiç dönmüyor; 2.389 ilanın 1.536'sında fiyat takvimi gizli (`hide_rate_calendar`) ve takvimi fiyatlı 248 ilanın takvimi yalnız Ekim 2026–Mart 2027'yi kapsıyor (yaz ayları yok). Pencere fiyatı çıkan mahalle × pencere hücresi 6 (en çok Seaside Kış 2027: 170 ilanın 6'sı). Takvimden aylık ortanca fiyat 12 mahallede var ama birçoğu 1–20 ilana dayanıyor; en geniş taban Seaside (87–116 ilan, Ekim–Ocak ortancası 770–894 $). Fiyat seviyesi için bu kaynak tek başına yetmiyor.

**Dikkat:** Seagrove satırı Seagrove ve Seagrove Beach filtrelerinin birleşimidir. Aramada görünmeyen ilan dolu ya da yok anlamına gelmez; pencere geceleri takvimde fiyatlı olan ilanların çoğu o pencerenin aramasında görünmedi (kaynağın dışlama kuralı bilinmiyor).

## Amaç

Her mahallede ne tür konaklama olduğunu (ev, daire, otel vb.), büyüklüklerini ve bulunabildiği kadar fiyat seviyesini vermek. Veri belirli tarihlerdeki aramaların etiketli anlık görüntüsüdür; **hiçbir yerde tam envanter denmez** (7 Ekim 2026 yönetici kararı, M6).

## Kaynak

Visit South Walton'ın resmî "Book Your Stay" bağlantısı Book>Direct ön yüzüne gider (`https://visitsouthwalton.bookdirect.net/`). Ön yüz verisini `admin.bookdirect.net` üzerindeki clone uçlarından alır; bu uçlar belgelenmiş, resmî bir API değildir, ön yüzün kullandığı uçlardır ve haber verilmeden değişebilir (keşif: M6, GÖREV-02 Alan 7).

| Uç (clone tabanına göre) | Kullanım |
|---|---|
| `/show.json` | Konum filtreleri (19), kategoriler, olanaklar |
| `/lodgings.json` | Tarihli arama: `checkin`, `checkout`, `group_ids[]` (konum), `category_ids[]` (varsayılan kategori), `per_page=50`, `sort=title`, `direction=asc`, `page` |
| `/lodgings/live_rates.json` | Canlı fiyat entegrasyonu olan ilanlar için fiyat: `lodging_ids[]`, `current_page`, `attempt` |
| `/lodgings/{id}/rates.json` | İlanın günlük fiyat takvimi: bugünden bir yıl sonrasına, `per_page=365` |

**İstemci anahtarı.** Uçlar, ön yüz paketinde herkese açık yayımlanan bir istemci anahtarını `Authorization: Token token=…` başlığıyla ister. Toplayıcı her çekimde giriş HTML'inden sürümlü paket yolunu (`<base href="/YYYYMMDDhhmmss/">` ve `bookdirect*.js`) çözer, paketi okur, anahtarı yalnız bellekte tutar. Anahtar hiçbir dosyaya, veritabanına, ham kayda veya günlüğe yazılmaz: paket yanıtının gövdesi saklanmaz (manifestte yalnız SHA-256 ve bayt), anahtarı içeren herhangi bir yanıt saklanmaz, manifest yazılmadan önce anahtar için taranır; anahtar yalnız `admin.bookdirect.net` isteklerine gider. Testler bütün yazılan dosyaları, veritabanı dökümünü ve iş günlüğünü anahtar için tarar.

## Genel çekirdek ve destinasyon yapılandırması

Toplayıcı geneldir (`studio/sources/bookdirect_lodging.py`, `bookdirect-lodging/1`): Book>Direct başka turizm kurumlarınca da kullanılıyor. Kaynak adresi `https://<clone>.bookdirect.net/` biçimindeki her kayıtla eşleşir; destinasyona özel olan her şey SQLite'tan gelir:

| Tablo | İçerik | 30A ilk değerleri (profil + v10 migration) |
|---|---|---|
| `destination_lodging_sources` | clone adresi | `visitsouthwalton.bookdirect.net` |
| `destination_lodging_locations` | kaynağın konum filtresi adı → kanonik bölge | 13 kanonik mahalle; `Watercolor` → WaterColor, `Watersound` → WaterSound; ayrıca `Seagrove Beach` → Seagrove |
| `destination_lodging_windows` | örnek tarih pencereleri | 2026-10-17→24, 2027-01-16→23, 2027-03-13→20, 2027-07-10→17 (Cumartesi–Cumartesi, 7 gece) |

Kaynağın adres ve koordinatından mahalle çıkarılmaz; mahalle yalnız konum filtresinin adından gelir. Miramar Beach, Sandestin, Seascape, Defuniak Springs ve Freeport filtreleri kapsam dışıdır (çekim metadata'sında `unmapped_locations`). Yapılandırılmış bir ad kaynakta yoksa çekim başarısız olur. Cumartesi–Cumartesi deseni bir varsayımdır, kaynak olgusu değildir. Yapılandırması olmayan destinasyonda çekim hiçbir istek yapmadan durur; kaynak adresi yapılandırmadaki clone'la uyuşmazsa da durur.

## Yöntem

1. Giriş HTML'i → sürümlü paket → istemci anahtarı (tek tanım yoksa API'ye istek yapılmadan durur).
2. `show.json`: konumlar, kategoriler (varsayılan "All Lodging" kategorisi), olanaklar.
3. Her pencere × her eşlenmiş konum filtresi için `lodgings.json`'un bütün sayfaları. Sayfalar arasında toplam değişir ya da okunan benzersiz ilan sayısı bildirilen toplamla tutmazsa filtre bir kez baştan okunur, yine tutmazsa çekim başarısız olur (kısmi sonuç yayımlanmaz). Bugünden önce başlayan pencere aranmaz, `skipped_past` diye kaydedilir; bütün pencereler geçmişteyse çekim durur.
4. Canlı fiyat: ön yüz paketindeki mantığa göre (`get_live_rate_ids`, `request_live_rates`; 7 Ekim 2026'da okundu) aramada fiyatı olmayan ya da fiyatı beklemede (`liveness` 1) olan ilanlar sorulur; ön yüz yalnız arama satırında `liveness` dolu olanlara bakar, toplayıcı ayrıca `live_rates_enabled` işaretli olanları da sorar. İlanlar 50'şerlik gruplarla gider; yanıtı bekleyen (`liveness` dolu ve 0 değil) ilanlar yeniden sorulur. Ön yüz 20 denemeye kadar, 1 sn + 0,75 sn × deneme arayla soruyor; toplayıcı aynı aralıkla en fazla 5 deneme yapar. Dönen fiyat, en az gece ve `liveness` saklanır; yanıtta hiç görünmeyen ilan `no_answer`.
5. Takvim: görülen her benzersiz ilan için `rates.json` bir kez okunur; GÖREV-08'den (`bookdirect-lodging/2`) beri takvimi gizli ilanlar (`hide_rate_calendar`; ön yüz de bu ilanlarda takvim göstermiyor) istenmez ve sayıları `calendars_skipped_hidden` olarak çekim kaydına yazılır. Ham günlük değerler veritabanına yazılmaz; ilan başına ay ay fiyatlı gün sayısı, en düşük, ortanca ve en yüksek gecelik fiyat ve en sık görülen en az gece (`los`) saklanır. Ayrıca her pencerenin gecelerinin takvim fiyatlarının ortalaması, yalnız bütün geceler fiyatlıysa saklanır. Kaynak takvim vermezse (HTTP 400/404/422) ilan `unavailable` diye kaydedilir, çekim sürer.
6. İstekler sıralı, aralarında 1,25 sn; ağ hatası ve 5xx bir kez yeniden denenir, 429 çekimi durdurur. İlerleme ve iptal her istekte denetlenir. Ham yanıtlar gzip ile sıkıştırılıp saklanır; manifestte her yanıtın adresi, durumu, zamanı, sıkıştırılmamış gövdenin SHA-256'sı ve baytı var.
7. Bütün kayıtlar tek transaction'da yazılır; hata ya da iptal önceki başarılı sürümü bozmaz.

İstek sayısı ve süre (7 Ekim 2026, ölçülen): yaklaşık 215 arama sayfası, 48–52 canlı fiyat isteği ve 2.389 takvim isteği; toplam ~2.655 istek, 1,25 sn arayla ~73 dakika. Süreyi takvim istekleri belirliyordu (ilanların çoğunda takvim gizli ve boş dönüyordu). GÖREV-08 (8 Ekim 2026, `bookdirect-lodging/2`): 1.536 gizli takvim istenmedi; geçici denemede 1.123 istek, 34,5 dakika.

## Saklanan alanlar (şema 10)

| Tablo | Alanlar |
|---|---|
| `lodging_snapshots` | clone, ön yüz sürüm yolu, varsayılan kategori, arama günü (UTC), istek ve ilan sayısı |
| `lodging_windows` | pencere, giriş/çıkış, gece, `searched` / `skipped_past` |
| `lodging_filters` | pencere × konum filtresi: kaynak konum kimliği ve adı, kanonik bölge, bildirilen toplam, sayfa sayısı |
| `lodging_listings` | kimlik, ad, kategori kimlikleri ve adları, adres, şehir, eyalet, posta kodu, koordinat, yatak odası, banyo, kapasite (`sleeps`), olanaklar, rezervasyon sistemi (`res_engine`), kaynak konum kimliği, takvim gizli mi, canlı fiyat açık mı; şema 11'den beri şirketin ilan sayfası (`url`, yalnız http/https) ve telefonlar (`phone`, `toll_free`); `bookdirect-lodging/1` kayıtlarında bu üçü NULL |
| `lodging_search_results` | pencere × filtre × ilan: sıra, `average_rate`, USD karşılığı, `los`, `liveness`, `live_rates_enabled`, `min_stays` (kaynaktaki biçimiyle JSON), canlı fiyat durumu, fiyatı, en az gecesi, `liveness`, deneme sayısı |
| `lodging_calendars` | ilan takvimi okundu mu, istenen aralık, fiyatlı gün |
| `lodging_rate_months` | ilan × ay: fiyatlı gün, en düşük, ortanca, en yüksek, en sık en az gece |
| `lodging_calendar_windows` | ilan × pencere: gece, fiyatlı gece, (hepsi fiyatlıysa) ortalama, en büyük en az gece |

Boş alan NULL kalır. Kaynakta listelenmemiş bir olanak "yok" demek değildir. `fetched_at` kaynağın güncellenme zamanı değildir; kayıtlarda kaynak güncelleme zamanı yok.

## Okuma anında hesaplanan özet

`GET /api/lodging-runs/{id}` her mahalle × pencere için hesaplar (hiçbiri saklanmaz; bizim hesabımız): ilan sayısı (aynı mahallenin iki filtresinde görünen ilan bir kez), kategori dağılımı (varsayılan "All Lodging" hariç kaynak kategorileri; bir ilan birden fazla kategoride olabilir), yatak odası dağılımı (ortanca, 4+ odalı pay, stüdyo–6+ dağılımı; yatak odası belirtilmiş ilanlar üzerinden), kapasite ortancası, fiyat bilgisi olan ilan payı ve kaynağı, fiyatı olan ilanlarda gecelik fiyatın ortancası ve çeyrekler aralığı. Fiyat önceliği: güncel canlı fiyat (`liveness` 0; ön yüz arama fiyatını bununla değiştirir), yoksa aramadaki liste fiyatı (`average_rate`), yoksa diğer canlı yanıt, yoksa pencerenin bütün geceleri fiyatlıysa takvim ortalaması. Ayrıca mahalle başına takvimden aylık ortanca gecelik fiyat (ilanların aylık ortancalarının ortancası). `GET /api/lodging-runs/{id}/listings?region_id=…` mahallenin ilanlarını pencere satırları ve aylık takvimiyle verir.

Her özetin etiketi: "<arama günü> tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor."

## Arayüz

Veri toplama → **Konaklama**: toplama düğmesi, sürüm seçimi, ham manifest indirme, mahalle × pencere özet tablosu; mahalle seçilince pencere başına tür, yatak odası, kapasite ve fiyat kaynağı, aylık takvim ortancaları ve ilan listesi; ilan seçilince adres, olanaklar, rezervasyon sistemi, canlı fiyat durumu, şirketin ilan sayfasına bağlantı (GÖREV-08) ve aylık takvim (gizli takvimde "kaynakta gizli (istenmedi)"). Aynı sekmenin altında kiralama şirketi fiyat bölümü (M11).

## Sınırlar

- Tarihli arama sonucu; görünmeyen ilan "yok" ya da "dolu" demek değildir (M6: farklı tarihlerde farklı kimlik kümeleri, dışlama nedeni bilinmiyor).
- Kaynakta misafir sayısı parametresi yok; `sleeps` mülkün kapasitesidir.
- `average_rate` arayüzde "Average Rate/Night"; kaynağa göre en düşük müsait günlük fiyata dayanır, garanti değildir; vergi ve ücretler belirtilmiyor. GÖREV-02 örneklerinde liste fiyatı çoğu ilanda boştu; fiyatın çoğu canlı fiyat ve takvimden gelebilir.
- `los` seçilen tarihlerde en az gece; `min_stays` örneklerde hep boştu, anlamı belirsiz, olduğu gibi saklanır. `liveness` değerlerinin anlamı ön yüz kodundan çıkarımdır (0 güncel, 1 bekliyor, boş canlı fiyat yok).
- Kategoriler kaynağın; bir ilan ev ve "Rental Agencies" gibi birden fazla kategoride olabilir; agresif sınıflandırma yapılmaz.
- Kaynağın konum yapılandırmasındaki koordinatlar güvenilir değil (Seacrest Florida'nın doğu kıyısında görünüyor); konum yalnız filtre adıyla kullanılır.
- Uçlar belgelenmemiş; ön yüz sürüm yolu 30 Eylül–6 Ekim 2026 arasında değişti. Sözleşme değişirse çekim açık hatayla durur.

## Video dili

"Visit South Walton'ın resmî rezervasyon sayfasında <tarih>'te yapılan aramada, <pencere> için <mahalle>'de N ilan göründü; bunların çoğu …" biçiminde, arama tarihi ve pencere söylenerek. "30A'da N ev var", "ortalama fiyat" (tarih ve kaynak söylenmeden) veya "tam liste" denmez. Fiyatlar "kaynağın gösterdiği en düşük müsait gecelik fiyat, vergi ve ücretler hariç olabilir" diye çerçevelenir.

## Testler

`tests/test_lodging.py` (40 test; sahte sunucu, `httpx.MockTransport`, ağ yok): anahtarın paketten çözülmesi ve hiçbir çıktıya yazılmaması, eksik/çift anahtar ve paket yolu, anahtarı içeren yanıtın saklanmaması, konum eşlemesi (Seagrove Beach dahil), eksik konum ve tanımsız bölge, sayfalama ve değişen toplam, geçmiş pencere, boş fiyat alanları (NULL), canlı fiyat denemeleri, deneme sınırı ve ön yüzün hangi ilanı sorduğu kuralı, takvim özetleri ve pencere ortalaması, ilan biçim hataları, iptal, API ile toplama ve özet, eklemeden sonra hata ile geri alma, API üzerinden iptal, taze kurulum yapılandırması ve kısıtlar, v9 → v10 migration ve geri alma, yapılandırmanın üzerine yazılmaması, destinasyon yalıtımı, kaynak adresi eşleşmesi. Arayüz yardımcıları `tests/frontend.test.mjs` içinde.
