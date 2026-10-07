# M10 — Konaklama profili (Book>Direct tarihli arama anlık görüntüleri)

Tarih: 7 Ekim 2026 · Görev: GÖREV-07 · Dal: `gorev-07-konaklama` · Uygulama `0.10.0` · Şema `10`

## Durum

Toplayıcı, şema, arayüz ve testler hazır. **Canlı çekim henüz yapılmadı:** 7 Ekim 2026'da Claude Code'un otomatik izin denetimi, ön yüz paketinden istemci anahtarını okuyup kullanan isteği "kimlik bilgisi keşfi" sayarak engelledi. Bu yüzden geçici klasörde canlı deneme, gerçek veritabanı güncellemesi ve gerçek veriden özet dosyaları bekliyor; ayrıntı `docs/gorevler/GOREV-07/RAPOR.md`. Aşağıdaki yöntem kodun ve ağsız testlerin anlattığıdır; sayılar canlı çekimden sonra eklenecek.

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
4. Canlı fiyat: her pencerede `live_rates_enabled` olan ilanlar 50'şerlik gruplarla sorulur; ön yüzün yaptığı gibi yanıtı bekleyen (`liveness` dolu ve 0 değil) ilanlar en fazla 3 denemeye kadar, 2 sn arayla yeniden sorulur. Dönen fiyat, en az gece ve `liveness` saklanır; yanıtta hiç görünmeyen ilan `no_answer`.
5. Takvim: görülen her benzersiz ilan için `rates.json` bir kez okunur. Ham günlük değerler veritabanına yazılmaz; ilan başına ay ay fiyatlı gün sayısı, en düşük, ortanca ve en yüksek gecelik fiyat ve en sık görülen en az gece (`los`) saklanır. Ayrıca her pencerenin gecelerinin takvim fiyatlarının ortalaması, yalnız bütün geceler fiyatlıysa saklanır. Kaynak takvim vermezse (HTTP 400/404/422) ilan `unavailable` diye kaydedilir, çekim sürer.
6. İstekler sıralı, aralarında 1,25 sn; ağ hatası ve 5xx bir kez yeniden denenir, 429 çekimi durdurur. İlerleme ve iptal her istekte denetlenir. Ham yanıtlar gzip ile sıkıştırılıp saklanır; manifestte her yanıtın adresi, durumu, zamanı, sıkıştırılmamış gövdenin SHA-256'sı ve baytı var.
7. Bütün kayıtlar tek transaction'da yazılır; hata ya da iptal önceki başarılı sürümü bozmaz.

İstek sayısı ve süre (tahmin, canlı çekimde ölçülecek): GÖREV-02 örneklerinde bir pencerede Dune Allen 112, Seaside 111, Rosemary Beach 160 ilan gösterdi; 14 filtre × 4 pencere için yaklaşık 120–200 arama sayfası, birkaç yüz canlı fiyat isteği ve ilan sayısı kadar (1.000–2.000) takvim isteği; 1,25 sn arayla yaklaşık 45–60 dakika.

## Saklanan alanlar (şema 10)

| Tablo | Alanlar |
|---|---|
| `lodging_snapshots` | clone, ön yüz sürüm yolu, varsayılan kategori, arama günü (UTC), istek ve ilan sayısı |
| `lodging_windows` | pencere, giriş/çıkış, gece, `searched` / `skipped_past` |
| `lodging_filters` | pencere × konum filtresi: kaynak konum kimliği ve adı, kanonik bölge, bildirilen toplam, sayfa sayısı |
| `lodging_listings` | kimlik, ad, kategori kimlikleri ve adları, adres, şehir, eyalet, posta kodu, koordinat, yatak odası, banyo, kapasite (`sleeps`), olanaklar, rezervasyon sistemi (`res_engine`), kaynak konum kimliği, takvim gizli mi, canlı fiyat açık mı |
| `lodging_search_results` | pencere × filtre × ilan: sıra, `average_rate`, USD karşılığı, `los`, `liveness`, `live_rates_enabled`, `min_stays` (kaynaktaki biçimiyle JSON), canlı fiyat durumu, fiyatı, en az gecesi, `liveness`, deneme sayısı |
| `lodging_calendars` | ilan takvimi okundu mu, istenen aralık, fiyatlı gün |
| `lodging_rate_months` | ilan × ay: fiyatlı gün, en düşük, ortanca, en yüksek, en sık en az gece |
| `lodging_calendar_windows` | ilan × pencere: gece, fiyatlı gece, (hepsi fiyatlıysa) ortalama, en büyük en az gece |

Boş alan NULL kalır. Kaynakta listelenmemiş bir olanak "yok" demek değildir. `fetched_at` kaynağın güncellenme zamanı değildir; kayıtlarda kaynak güncelleme zamanı yok.

## Okuma anında hesaplanan özet

`GET /api/lodging-runs/{id}` her mahalle × pencere için hesaplar (hiçbiri saklanmaz; bizim hesabımız): ilan sayısı (aynı mahallenin iki filtresinde görünen ilan bir kez), kategori dağılımı (varsayılan "All Lodging" hariç kaynak kategorileri; bir ilan birden fazla kategoride olabilir), yatak odası dağılımı (ortanca, 4+ odalı pay, stüdyo–6+ dağılımı; yatak odası belirtilmiş ilanlar üzerinden), kapasite ortancası, fiyat bilgisi olan ilan payı ve kaynağı, fiyatı olan ilanlarda gecelik fiyatın ortancası ve çeyrekler aralığı. Fiyat önceliği: aramadaki liste fiyatı (`average_rate`), yoksa canlı fiyat, yoksa pencerenin bütün geceleri fiyatlıysa takvim ortalaması. Ayrıca mahalle başına takvimden aylık ortanca gecelik fiyat (ilanların aylık ortancalarının ortancası). `GET /api/lodging-runs/{id}/listings?region_id=…` mahallenin ilanlarını pencere satırları ve aylık takvimiyle verir.

Her özetin etiketi: "<arama günü> tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor."

## Arayüz

Veri toplama → **Konaklama**: toplama düğmesi, sürüm seçimi, ham manifest indirme, mahalle × pencere özet tablosu; mahalle seçilince pencere başına tür, yatak odası, kapasite ve fiyat kaynağı, aylık takvim ortancaları ve ilan listesi; ilan seçilince adres, olanaklar, rezervasyon sistemi, canlı fiyat durumu ve aylık takvim.

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

`tests/test_lodging.py` (39 test; sahte sunucu, `httpx.MockTransport`, ağ yok): anahtarın paketten çözülmesi ve hiçbir çıktıya yazılmaması, eksik/çift anahtar ve paket yolu, anahtarı içeren yanıtın saklanmaması, konum eşlemesi (Seagrove Beach dahil), eksik konum ve tanımsız bölge, sayfalama ve değişen toplam, geçmiş pencere, boş fiyat alanları (NULL), canlı fiyat denemeleri ve deneme sınırı, takvim özetleri ve pencere ortalaması, ilan biçim hataları, iptal, API ile toplama ve özet, eklemeden sonra hata ile geri alma, API üzerinden iptal, taze kurulum yapılandırması ve kısıtlar, v9 → v10 migration ve geri alma, yapılandırmanın üzerine yazılmaması, destinasyon yalıtımı, kaynak adresi eşleşmesi. Arayüz yardımcıları `tests/frontend.test.mjs` içinde.
