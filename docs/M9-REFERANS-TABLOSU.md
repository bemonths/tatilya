# M9 — Elle doğrulanmış referans tablosu

Tarih: 7 Ekim 2026 · Görev: GÖREV-06 · Dal: `gorev-06-referanslar` · Uygulama `0.9.0`

## Amaç

Toplayıcıyla alınamayan ama ilk videoda söylenecek her bilgiyi (plaj kuralları, bayrak sistemi, plaj erişimi, ulaşım, parklar, kasırga sezonu, sezon ve maliyet) kaynağıyla ve doğrulama tarihiyle tek bir yerde tutmak. Kanıt paketi ve makale aşaması bu tabloyu okur. Tablo elle doldurulur, gözden geçirilir ve repoda sürümlenir; uygulama yalnız okur ve doğrular.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `studio/destinations/thirty_a_references.csv` | Referans tablosu; her satır tek bir olgu. Profil sabiti `thirty_a.REFERENCE_TABLE`. |
| `studio/destinations/thirty_a_tdt_collections.csv` | South Walton turist geliştirme vergisi (TDT) aylık tahsilatları, Ekim 1998–Temmuz 2026. Profil sabiti `thirty_a.TDT_COLLECTIONS`. |
| `studio/destinations/references.py` | Genel okuyucu ve doğrulayıcı (destinasyondan bağımsız; dosya yerini profil verir). |
| `work/referans-belgeler/` | Alınan belgeler ve `manifest.json` (istenen/son URL, HTTP durumu, bayt, SHA-256, UTC zamanı). Repoya girmez. |

## Sütunlar

| Sütun | Anlamı |
|---|---|
| `id` | Kalıcı kimlik, küçük harf-rakam-tire (ör. `kural-cam`). Değişmez; olgu kaldırılırsa kimlik yeniden kullanılmaz. |
| `konu` | `plaj-kurallari`, `guvenlik`, `plaj-erisimi`, `ulasim`, `parklar`, `kasirga-sezonu`, `sezon-maliyet`, `genel` |
| `ifade` | İngilizce tek cümle, kendi cümlemizle; videoda söylenebilecek biçimde. Kaynağın taşıdığından ileri gitmez. |
| `deger`, `birim` | Olgunun değeri ve birimi (boş olabilir). |
| `kapsam` | `30A`, `South Walton`, `Walton County`, `Florida`, `Atlantik havzası` |
| `kaynak_adi`, `kaynak_sahibi`, `kaynak_url` | Belgenin adı, yayımlayan kurum, alındığı adres (yönlendirmeden sonraki son adres). |
| `belge_konumu` | Bölüm, madde, sayfa veya sayfa başlığı. |
| `kisa_alinti` | Kaynaktan birebir en fazla 25 kelime; yalnız doğrulama içindir, videoda kullanılmaz. |
| `belge_tarihi` | Biliniyorsa `YYYY`, `YYYY-AA` veya `YYYY-AA-GG`. |
| `erisim_tarihi` | Belgenin alındığı gün (`YYYY-AA-GG`, UTC). |
| `belge_sha256` | Alınan dosyanın ya da sayfanın SHA-256'sı. |
| `guven` | `birincil` (kuralın veya verinin sahibi) / `ikincil` (başkasının özeti). |
| `durum` | `dogrulandi` / `celiskili` / `dogrulanamadi` |
| `celiski_notu` | Çelişkili satırda zorunlu; karşı satırın kimliği ve farkı. |
| `yeniden_kontrol_tarihi` | Satırın yeniden kontrol edileceği gün. |
| `not` | Kapsam sınırları, hesap açıklaması, uyarılar. |

## Doğrulayıcı kuralları

`references.problems()` her ihlali okunur bir cümleyle döndürür; testler (`tests/test_references.py`) repodaki tablonun hiç ihlal içermediğini denetler. Kurallar: sütunlar ve sırası birebir; zorunlu alanlar dolu; kimlik biçimi ve tekilliği; konu, kapsam, güven ve durum tanımlı değerlerden; erişim ve yeniden kontrol tarihi `YYYY-AA-GG` ve yeniden kontrol erişimden sonra; belge tarihi kısmi tarih biçimlerinden biri; `dogrulandi` ve `celiskili` satırlarda https adresi ve SHA-256 zorunlu; `celiskili` satırda çelişki notu zorunlu; kısa alıntı en fazla 25 kelime. API (`GET /api/references`) satırları, doğrulama sonucunu ve yeniden kontrol tarihi geçmiş satırları (`overdue`) verir; bozuk dosyada uygulama hata vermez, nedenini gösterir.

## Kaynak politikası

- `CALISMA_MANTIGI.md` §4 madde 14: belirli bir resmî belgenin kaynak göstermek için tek seferlik elle alınması toplayıcı sayılmaz; URL, erişim tarihi ve SHA-256 ile kaydedilir. Bu tablonun belgeleri böyle alındı (`work/referans-belgeler/al.py`, repo adresli User-Agent, istekler arası 1,5 sn).
- Bot doğrulaması (Cloudflare vb.) olan sayfa otomasyonla aşılmaz; okunamazsa satır `dogrulanamadi` olur (7 Ekim 2026'da Florida State Parks sayfaları HTTP 403 döndürdü).
- İki kaynak çelişirse ikisi de ayrı satır olarak yazılır, ikisi de `celiskili` olur ve `celiski_notu` doldurulur; hangisinin doğru olduğuna tabloyu dolduran karar vermez. Aynı belgenin iki sayfası çelişirse de böyle yapılır.
- Taranmış belgeler (Ordinance 2025-22, metin katmanı yok) sayfa görüntüleri çıkarılıp okunarak işlendi; OCR yalnız arama içindir, alıntılar sayfa görüntüsünden doğrulandı. Metin tabanlı PDF'lerdeki infografik değerler Windows'un PDF çizicisiyle sayfa görüntüsü üretilip gözle doğrulandı.

## Durumlar ve video dili

- **`dogrulandi`** — kaynak gösterilerek söylenebilir (ör. "Walton County'nin plaj yönetmeliğine göre …").
- **`celiskili`** — ancak çelişki açıkça söylenerek ya da daha güncel bir resmî kaynakla çözülerek kullanılır.
- **`dogrulanamadi`** — videoda kullanılmaz.
- Değeri bizim hesapladığımız satırlar (havalimanı uzaklıkları) `not` sütununda "bizim hesabımız" diye işaretlidir.

## Yeniden kontrol kuralı

Kurallar, ücretler, saatler ve tanımlar yılda bir yeniden kontrol edilir (7 Ekim 2026'da alınanlar için 2027-10-07). Ziyaretçi ve konaklama raporlarından gelen satırlar her yeni rapor çıktığında kontrol edilir (ilk kontrol 2026-12-01). Çelişkili cankurtaran satırları bir sonraki sezondan önce, 2027-02-01'de. Sekme, tarihi geçmiş satırları işaretler ve sayar.

## 7 Ekim 2026 içeriği

85 satır: 73 `dogrulandi`, 6 `celiskili`, 6 `dogrulanamadi`.

| Konu | Satır | Doğrulandı | Çelişkili | Doğrulanamadı | Başlıca kaynak |
|---|---:|---:|---:|---:|---|
| Plaj kuralları | 25 | 25 | 0 | 0 | Walton County Ordinance 2025-22 (24 Kasım 2025) |
| Güvenlik | 12 | 10 | 2 | 0 | South Walton Fire District; Visit South Walton |
| Plaj erişimi | 10 | 10 | 0 | 0 | Visit South Walton park ve ulaşım rehberi (2023-05-04), plaj erişim haritası |
| Ulaşım | 11 | 9 | 2 | 0 | FAA, Florida Statutes 316.212 ve 316.2122, Ordinance 2009-02, Visit South Walton |
| Parklar | 8 | 2 | 0 | 6 | Florida Forest Service; Florida State Parks (okunamadı) |
| Kasırga sezonu | 2 | 2 | 0 | 0 | NOAA NHC |
| Sezon ve maliyet | 14 | 12 | 2 | 0 | Walton County Tourism / Downs & St. Germain raporları; TDT Collections |
| Genel | 3 | 3 | 0 | 0 | Ordinance 2025-22; Visit South Walton |

Çelişkiler: cankurtaran sezonu (SWFD SSS: 1 Mart–30 Eylül, 10:00–18:00, 8 kule; Visit South Walton: 1 Mart–31 Ekim), Timpoochee Trail uzunluğu (19 mil / 18,5 mil) ve 2025 ziyaretçi sayısı (aynı raporun 5. sayfasında 4.586.000, 8. sayfasında 4,57 milyon; doğrudan harcama da iki sayfada farklı). Ziyaretçi ve konaklama satırlarındaki ADR değerleri, Airbnb ve Vrbo'nun 2025'te fiyat gösterimini değiştirmesiyle (temizlik ve platform ücretleri dahil) yıllar arası karşılaştırmada şişkin görünebilir; bu uyarı ilgili satırların notunda.

## Aylık turist vergisi (TDT)

Walton County Tourism'in "TDT Collections" sayfası (Gatsby sitesi) aylık raporları sayfanın statik sorgu dosyasındaki bir akordeon bileşeninden listeliyor (`/page-data/sq/d/2777485464.json`). Bağlantılar herkese açık PDF ve XLSX dosyalarına gidiyor. South Walton için Walton County Clerk of Courts & County Comptroller'ın "SW TDT Collections History with Monthly FYTD Comparisons" çalışma kitabı FY1999'dan bu yana bütün ayları içeriyor; `thirty_a_tdt_collections.csv` bu kitaptan üretildi (334 ay, her mali yılın aylık toplamı kitaptaki yıllık toplamla birebir aynı). Sütunlar: ay, mali yıl (Ekim–Eylül), vergi bölgesi, o dönemin oranıyla toplam tahsilat, oran değişimlerinden bağımsız %2 payı, kaynak sayfa, URL, erişim tarihi, SHA-256.

**Ay neyi gösteriyor?** Aylık rapor dönemi ayın adıyla ve bir sonraki ayda alınmış olarak veriyor: "Monthly Collections: June 2026 (Received during July 2026)"; dosya adları da "MAY25 collected in JUN25" biçiminde. Yani etiket ayı tahsil ayı değil; tahsilat bir sonraki ay alınıyor. Etiket ayının konaklama (vergiye tabi kiralama) ayı olduğunu açıkça söyleyen bir ifade kaynakta bulunamadı. Vergi oranı yıllar içinde değişti (%3 → %4 → %4,5 → %4 → %5, 1 Ocak 2020'den beri %5); yıllar arası karşılaştırmada `yuzde2_payi_usd` kullanılmalı.

Çalışma kitabı ile aylık PDF raporu küçük farklar gösterebiliyor: Haziran 2026 için South Walton toplamı kitapta 11.945.425,14 $, "FY26 TDT Collections Report – JUN26 collected in JUL26" PDF'inde 11.945.791,53 $ (fark 366,39 $). CSV çalışma kitabını izler; videoda tek ay rakamı söylenecekse kaynak belge birlikte anılmalı.

## Yeniden üretim

`work/gorev-06/referans_tablosu.py` olguları, alıntıları ve konumları içerir; adres, erişim tarihi ve SHA-256'yı `work/referans-belgeler/manifest.json`'dan doldurur ve doğrulayıcıdan geçmeyen tabloyu yazmaz. `work/gorev-06/tdt_csv.py` TDT dosyasını üretir. İkisi de `work/` altındadır (repoya girmez); yeni bir sürüm gözden geçirildikten sonra ayrı commit olarak alınır.
