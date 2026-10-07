# 30A Studio — Master Devir / Çalışma Mantığı

> **Bu dosya projenin ana devir-teslim belgesidir.**
>
> Yeni bir geliştirici veya yapay zekâ projeye devam etmeden önce önce bu dosyayı, sonra `docs/DEVIR/` altındaki belgeleri okumalıdır. Domain belgeleri (`M2`–`M9`) ayrıntılı teknik kayıt niteliğindedir. Kod ile belge çelişirse gerçek kod ve güncel veritabanı davranışı incelenmeli, ardından bu belge aynı geliştirme turunda güncellenmelidir.
>
> Bu paket 3 Ekim 2026 itibarıyla `bemonths/tatilya` reposunun durumu esas alınarak hazırlanmış, en son 7 Ekim 2026'da GÖREV-06 (v0.8.0 yayını, kasırga evre kuralı, referans tablosu) ile güncellenmiştir.

## 1. Bir bakışta mevcut durum

| Alan | Güncel durum |
|---|---|
| Repo | `bemonths/tatilya` |
| Yerel çalışma klasörü | `C:\Users\1\Documents\Codex\2026-09-29\referenced-chatgpt-conversation-this-is-an\outputs\30a-studio` |
| Başlatma | `baslat.bat` |
| Stable branch | `main` @ `de6685f10699d37afd4e1f13b115a6fa13369355` (GÖREV-05: eşleme v3 ve iklim paketi; 7 Ekim 2026'da GÖREV-06 Adım 1 ile fast-forward) |
| Stable tag | `v0.8.0` → `de6685f` — **v0.8.0 — eşleme v3 ve iklim paketi** (önceki: `v0.7.0` → `7f25e3c`, `v0.6.0` → `a938367`) |
| Stable uygulama sürümü / şema | `0.8.0` / `8` (main ve `v0.8.0`) |
| Aktif geliştirme dalı | `gorev-06-referanslar` — kasırga sayımında yalnız tropikal/subtropikal evreler (HURDAT2 `/2`) ve elle doğrulanmış referans tablosu (Referanslar sekmesi, aylık turist vergisi dosyası) |
| Aktif dal durumu | Uygulama `0.9.0`, şema `9`; main'e alınmadı; karar yöneticinin |
| Eski araştırma dalı | `v0.7-lodging-inventory` — yalnız konaklama keşif belgeleri; main'e alındı. Adı v0.7.0 sürümüyle ilgili değildir. |
| Son CI | main @ de6685f başarılı; görev dalının sonucu `docs/gorevler/GOREV-06/RAPOR.md` içinde |
| Test tabanı | Görev dalında 513 Python testi + 42 frontend testi (main/v0.8.0: 479 + 37) |
| Gerçek connector'lar | Plaj erişimleri, NWS hava, restoran dizini, mahalle dizini, NCEI iklim normalleri, NDBC deniz suyu sıcaklığı, HURDAT2 kasırga geçişleri (görev dalında `/2`: yalnız tropikal/subtropikal evreler) |
| Plaj–mahalle eşlemesi | Ayrı, gözden geçirilebilir katman `studio/destinations/thirty_a_beach_neighborhoods.csv`. v0.7.0'da v1, v0.8.0/main'de v3 (9 resmî rehber + 6 ilçe alt bölüm + 16 ilçe alt bölüm (bitişik) + 13 komşu erişimlerle tutarlı + 9 program türetimi; kilitli) |
| Gerçek veritabanı | 7 Ekim 2026'da (GÖREV-06) tam yedekten sonra normal kullanımla şema 9'a yükseltildi ve yalnız kasırga toplayıcısı (`/2`) çalıştı (GÖREV-05'te şema 8 ve üç iklim toplayıcısı). Şema 9 dosyasını main'deki 0.8.0 "daha yeni sürüme ait" diye açmaz; uygulama bu dal main'e alınana kadar `gorev-06-referanslar` dalından çalıştırılır. |
| Mevcut production destinasyonu | 30A / South Walton, Florida |
| Konaklama durumu | Book>Direct tarihli arama doğrulandı; tam envanter şartı 7 Ekim 2026'da kaldırıldı, konaklama tarihli arama anlık görüntüleri olarak modellenecek (henüz kodlanmadı) |

## 2. Projenin amacı

30A Studio yalnız bir scraper veya veri tabanı değildir. Uzun vadeli amaç, **30A / South Walton gibi mikro-destinasyonlar için güvenilir veri toplayan ve bu veriyi YouTube içerik üretim zincirine kanıt katmanı olarak veren yerel bir içerik stüdyosu** oluşturmaktır.

İlk gerçek kullanım alanı İngilizce, yüz göstermeyen, yaklaşık 15–17 dakikalık YouTube videolarıdır. İçerik yaklaşımı “mekânı tanıt” değil, **gerçek bir tatil kararını çöz** yaklaşımıdır.

Örnek karar soruları:

- Hangi 30A mahallesi hangi tatil tipi için daha uygun?
- Hangi bölgede plaj erişimi daha rahat?
- Hangi tarihler hava açısından daha mantıklı?
- Hangi bölgede restoran/konaklama seçeneği daha güçlü?
- Maliyet, ulaşım, sezon, kalabalık, deniz koşulları ve hizmet çeşitliliği nasıl değişiyor?

Programdaki veri, videoda istatistik yağdırmak için değil; AI'ın ve editörün **kanıta dayalı araştırma, karşılaştırma ve senaryo üretmesi** için kullanılır.

## 3. Uzun vadeli ürün modeli

30A yalnızca ilk destinasyondur. Sistem baştan şu modelle tasarlanmıştır:

```text
Destinasyon
├─ Kaynaklar
├─ Canonical alt bölgeler
├─ Plajlar
├─ Hava
├─ Restoranlar
├─ Konaklama
├─ Etkinlikler
├─ Ulaşım
├─ Fiyat / müsaitlik snapshot'ları
├─ Araştırma / evidence pack
└─ İçerik üretimi
```

Bugün production'da yalnız `30a` vardır. Gelecekte Napa Valley, Lake Tahoe, Cape Cod vb. destinasyonlar aynı motoru kullanabilmelidir.

Bu yüzden yeni geliştirmelerde şu ayrım korunur:

> Bu davranış generic core'da mı olmalı, yoksa yalnız bu destinasyona özel connector/profile içinde mi kalmalı?

## 4. Temel veri ilkeleri

1. **Kaynağın kimliği ve otoritesi doğrulanmadan veri ana kaynak kabul edilmez.**
2. **Verinin ne anlama geldiği doğrulanmadan tabloya yanlış semantik ile yazılmaz.**
3. Eksik alan tahmin edilmez; mümkünse `NULL` bırakılır.
4. `fetched_at`, kaynağın kendi `source_updated` zamanı değildir.
5. Adres/koordinattan mahalle tahmini yalnız açıkça tasarlanmış ayrı bir eşleme katmanında yapılabilir; connector bunu sessizce yapmaz.
6. Kaynağın yayınladığı bir alan “listelenmedi” ise “yok” anlamına gelmez.
7. Stable external ID tercih edilir; isimden kimlik üretmekten kaçınılır.
8. Kısmi crawl sonucu başarılı snapshot olarak yayımlanmaz.
9. Ham cevaplar ve SHA-256 izi korunur.
10. Başarısız/iptal run önceki başarılı snapshot'ı bozmaz.
11. Dynamic search sonucu “tam inventory” diye adlandırılmaz.
12. Kaynak keşfinde öncelik: API → structured JSON → HTML → public network endpoint → gerekiyorsa browser automation.
13. Playwright varsayılan değildir; HTTP/JSON ile çözülüyorsa kullanılmaz.
14. Düzenli çalışan veri toplayıcılar robots.txt kurallarına uyar. Belirli bir resmî belgenin (rapor, yönetmelik PDF'i gibi) kaynak göstermek için tek seferlik elle alınması toplayıcı sayılmaz; URL, erişim tarihi ve SHA-256 ile kaydedilir. Programatik kullanım için yayımlanmış API'ler kendi kullanım koşullarıyla kullanılır. (7 Ekim 2026 yönetici kararı)

Ayrıntı: `docs/DEVIR/03_VERI_KAYNAKLARI_VE_DOGRULAMA.md`.

## 5. Çalışan teknik yığın

- Python 3.12+
- FastAPI
- Uvicorn
- SQLite
- HTTPX
- HTML/CSS/Vanilla JavaScript
- Server-Sent Events
- `ThreadPoolExecutor`
- pytest
- frontend testleri için Node built-in test runner

PySide6/Qt kullanılmaz. Node tabanlı frontend build sistemi yoktur.

Yerel uygulama varsayılan olarak `http://127.0.0.1:8830` adresinde çalışır.

`baslat.bat`:
- proje klasörüne geçer,
- gerekirse `.venv` oluşturur,
- bağımlılıkları kurar,
- `python -m studio` başlatır.

Varsayılan DB: `data/studio.sqlite3`  
Ham cevaplar: `data/raw/`  
Yedekler: `data/backups/`

## 6. Multi-destination omurgası

v0.6 ile 30A sistemin kendisi olmaktan çıkarıldı ve ilk `destination` haline getirildi.

Production kaydı:

```text
id       = 30a
name     = 30A
subtitle = South Walton, Florida
```

Destination-scoped temel yapılar:
- `destinations`
- `regions`
- `sources`
- `jobs`
- `source_runs`
- `entities`
- `destination_weather_anchors`

Önemli kurallar:
- Aynı URL farklı destinasyonlarda kullanılabilir.
- Aynı bölge adı farklı destinasyonlarda kullanılabilir.
- Source başka destination'a normal edit ile taşınamaz.
- Job/run hangi destinasyon için üretildiyse provenance bunu korur.
- Diff başka destinasyondaki run ile karşılaştırmaz.
- NWS connector generic'tir.
- İklim connector'ları (`ncei-climate-normals`, `ndbc-water-temperature`, `hurdat2-storm-proximity`) generic'tir; istasyonlar, kıyı koridoru ve yarıçaplar `destination_climate_stations` ve `destination_storm_corridors` tablolarından gelir.
- South Walton Beaches, Restaurants ve Neighborhoods connector'ları 30A'ya özeldir.
- Profil varlıkları (ör. plaj–mahalle eşleme dosyası) `studio/destinations/` altında destinasyon profiliyle durur; generic çekirdeğe gömülmez.

Frontend seçimi server-global değildir. Seçim `localStorage["studio.destination_id"]` ile tutulur. Destination değişince eski async cevapların yeni ekrana yazılması engellenir.

## 7. Connector modeli

Genel connector sözleşmesi `studio/sources/base.py` içindedir.

Connector şu sorumlulukları taşır:
- `name`
- `version`
- `raw_filename`
- `method`
- `diff_enabled`
- `supports(source)`
- `collect(..., context=ConnectorContext)`
- `store_records(...)`
- `read_records(...)`
- `comparison_value(...)`

`ConnectorContext` runtime'da destination'a ait:
- destination kaydı,
- canonical regions,
- weather anchors,
- iklim istasyonları ve kasırga kıyı koridoru (şema 8)

gibi yapılandırmayı taşır. Kayıt farkı kapalı connector'lar gerekçeyi isteğe bağlı `diff_reason` alanıyla verir.

Yeni domain connector'ı mümkün olduğunca generic `source_collection → job → run → raw → atomic publish` akışını kullanmalıdır.

## 8. Job / source_run / raw artifact akışı

```mermaid
flowchart TD
    A[Kaynak kaydı] --> B[Registry connector seçer]
    B --> C[Job + queued source_run]
    C --> D[Tek çalışanlı queue]
    D --> E[Kaynağı çek]
    E --> F[Ham cevabı sakla]
    F --> G[Parse + validation]
    G --> H[Domain kayıtlarını transaction içinde yaz]
    H --> I[Run ve job = done]
    I --> J[Önceki başarılı run ile diff]
    G --> K[Hata/iptal]
    K --> L[Kısmi domain publish yok]
```

Önemli:
- `run.id` bugün job kimliğiyle aynıdır.
- Ham artifact SHA'sı DB katmanında gerçek dosya baytlarından hesaplanır.
- İptal edilmiş iş geç gelen sonucu publish edemez.
- Domain yazımı hata verirse transaction geri alınır.
- Başarısız/iptal run tarihsel olarak kalır.

## 9. Bugün çalışan domain'ler

### 9.1 Plaj erişimleri

Kaynak: `https://www.visitsouthwalton.com/beach-bay-access-locations/`  
Connector: `south-walton-beaches`  
Yöntem: HTML içindeki JSON  
Scope: 30A-specific

Toplanan başlıca alanlar:
- external ID
- ad
- kaynak yerleşim adı
- adres
- koordinatlar
- erişim tipi
- kaynakta listelenen olanaklar

Örnek live snapshot'larda 53 kıyı erişim kaydı görülmüştür; bu sayı sabit kabul kriteri değildir.

### 9.2 NWS hava

Source record URL: `https://www.weather.gov/`  
API: `https://api.weather.gov`  
Connector: `nws-weather`  
Scope: generic

Destination'ın `destination_weather_anchors` kayıtlarını kullanır.

30A için üç örnek nokta:
- Batı 30A
- Orta 30A
- Doğu 30A

Bunlar canonical mahalle merkezi değildir; hava örnek noktalarıdır.

Toplanır:
- NWS point/grid bilgisi
- 12 saatlik forecast dönemleri
- saatlik forecast
- aktif alerts

Rolling forecast olduğu için generic record diff kapalıdır.

### 9.3 Restoranlar

Kaynak: `https://www.visitsouthwalton.com/listings/culinary-experiences/`  
Connector: `south-walton-restaurants`  
Yöntem: HTML dizin + detay  
Scope: 30A-specific

Kapsam: 13 canonical mahalle; Miramar Beach, Seascape ve Sandestin hariç.

Alanlar:
- stable listing path identity
- ad
- açıklama nullable
- adres
- telefon
- e-posta
- website
- cuisines
- meals served
- amenities
- source neighborhood provenance

Gerçek kullanıcı snapshot'ında 138 restoran ve 141 restoran-bölge ilişkisi korunmuştur. Bunlar kaynak değişebileceği için sabit test sayısı değildir.

### 9.4 Mahalleler (v0.7.0)

Kaynak: `https://www.visitsouthwalton.com/neighborhoods/`  
Connector: `south-walton-neighborhoods`  
Yöntem: HTML içindeki JSON dizin + mahalle sayfaları  
Scope: 30A-specific · Şema 7 tablo: `neighborhood_records` · diff etkin (kaynak kimliği)

Kapsam: 13 canonical mahalle; kaynak adı birebir veya açık yazım tablosuyla bağlanır; Miramar Beach, Seascape ve Sandestin kapsam dışı. Hedef mahallelerden biri yoksa çekim başarısız olur.

Alanlar: 24 haneli kaynak kimliği, permalink, ad, canonical bölge, kısa tanıtım cümlesi, temsilî nokta (enlem/boylam — **mahalle merkezi değil, kaynağın temsilî noktası**), kaynak etiketleri, kayıt bazında `modified`, sayfa tanıtım metni (yoksa NULL). Kaynak metinleri iç araştırma kanıtıdır; videoda aynen kullanılmaz, kendi cümlelerimizle ve atıfla kullanılır.

7 Ekim 2026 canlı denemesinde 16 dizin kaydından 13 mahalle kaydedildi, 3'ü kapsam dışı sayıldı; bu sayılar sabit kabul kriteri değildir. Ayrıntı: `docs/M7-MAHALLE-VERISI.md`.

### 9.5 Plaj erişimi–mahalle eşlemesi (v1: v0.7.0; v2: GÖREV-04; v3: v0.8.0)

Plaj kaynağında mahalle alanı yoktur. Eşleme, plaj toplayıcısından ve `beach_records`'tan ayrı, 30A'ya özel, gözden geçirilebilir bir katmandır: `studio/destinations/thirty_a_beach_neighborhoods.csv` (sütunlar: `external_id, plaj_adi, bolge_id, yontem, kaynak, not, belirsiz`). Dosyayı `tools/plaj_mahalle_esleme.py` üretir; dosya commit edilir, uygulama yalnız okur ve yeniden hesaplamaz.

v3 yöntem sırası (yönetici kararıyla kilitlendi): (1) resmî park ve ulaşım rehberindeki (2023-05-04) 9 eşleme olduğu gibi — `resmi_rehber`; (2) erişim noktası Walton County "Subdivision Boundaries" poligonlarından birinin içindeyse ve alt bölüm adı açık ad tablosuyla tek bir mahalleye bağlanıyorsa — `ilce_alt_bolum`; (3) nokta böyle bir poligonun içinde değil ama ad tablosunda bir mahalleye bağlanan ve 30 m veya daha yakın poligonlar tek bir mahalle gösteriyorsa — `ilce_alt_bolum_yakin` (tabloda olmayan bir poligonun içinde olmak engel değil; 30 m içinde farklı mahalleler varsa sonuç yok; 30–75 m kullanılmaz); (4) batıdaki ve doğudaki en yakın kaynaklı erişim (1–3) aynı mahalledeyse o mahalle — `komsu_tutarliligi` (zincirleme yok); (5) kalanlar için mahalle temsilî noktalarına boylam farkıyla en yakın mahalle — `turetim_en_yakin_mahalle_noktasi`, kaynak = mahalle çekiminin run kimliği; en yakın iki aday arasındaki fark 0,003°'den küçükse `belirsiz=evet`. Alys Beach ve Rosemary Beach'e (rehber: halka açık plaj erişimi yok) hiçbir yöntem erişim atamaz; ilçe verisi oraya düşürürse satır "resmî rehberle çelişki" diye işaretlenir (v3'te 1: Winston Lane - 4). Sonuç: 9 resmî, 6 ilçe, 16 ilçe (bitişik), 13 komşu, 9 türetim; belirsiz yok. Ayrıntı ve doğrulama: `docs/M7-MAHALLE-VERISI.md`.

Video dili: "resmî rehber", "ilçe alt bölüm verisi" ve "ilçe alt bölüm verisi (bitişik)" eşlemeleri kaynak gösterilerek söylenebilir ("Walton County subdivision verisine göre"); "komşu erişimlerle tutarlı" ve "program türetimi" eşlemeleri yalnız yaklaşık konum bilgisidir. Plaj ekranı her erişimde mahalle ve yöntem etiketini gösterir, mahalleye göre filtreler; dosyada olmayan kimlik "eşlenmemiş" görünür.

### 9.6 İklim paketi (v0.8.0; kasırga evre kuralı `gorev-06-referanslar` dalında)

Üç generic toplayıcı; destinasyona özel istasyon, koridor ve yarıçaplar SQLite'tan (30A için profil + v8 migration):

- `ncei-climate-normals` — NCEI 1991–2020 aylık normalleri, anahtarsız veri API'si (`/access/services/data/v1`; robots.txt `/data*` yolunu kapattığı için yalnız bu yol). 30A: Destin–Fort Walton Beach Havalimanı (kıyı referansı, sıcaklık normali olan istasyonlar içinde 30A kıyı koridoruna en yakın, 20,5 km) ve DeFuniak Springs (iç kesim karşılaştırması, 44,1 km). Yedi değişken; tamlık/ölçüm bayrakları ve yıl sayıları saklanır; eksik değer NULL.
- `ndbc-water-temperature` — NDBC tarihî yıllık dosyalarından PCBF1 (Panama City Beach, NOS 8729210) su sıcaklığı; yıl-ay ortalaması, ölçüm ve gün sayısı; çok yıllı aylık ortalamaya yalnız en az 20 günü ölçümlü yıl-aylar girer; 404 yıllar kaydedilir; ham ölçümler veritabanına yazılmaz.
- `hurdat2-storm-proximity` — NHC HURDAT2 (güncel dosya adı veri sayfasından okunur), 1 saatlik ara değerleme, programdaki en batı ve en doğu plaj erişimi arasındaki koridora en yakın uzaklık, 50 ve 100 deniz mili içinde ilk giriş ayı ve daire içindeki en yüksek rüzgâra göre sınıf (TD/TS/HU/MH); bütün sezonlar saklanır, dönem okuma anında seçilir.

Hesapladığımız değerler "NOAA verisinden bizim hesabımız" diye etiketlenir; "30A'nın iklimi" denmez. Veri toplama → İklim sekmesi. Ayrıntı, yöntem, sınırlar ve açık konular: `docs/M8-IKLIM-VERISI.md`.

GÖREV-06 (yönetici kararı): kasırga sayımı ve sınıflandırması yalnız fırtınanın tropikal veya subtropikal olduğu evrelere göre yapılır (HURDAT2 TD, TS, HU, SD, SS; EX, LO, WV, DB sayılmaz; ara noktalar aralığın başındaki evreyi taşır). Daireye yalnız tropikal olmayan evrede giren fırtına saklanır ama `non_tropical_only` diye işaretlenip bütün sayımların dışında kalır (`hurdat2-storm-proximity/2`, şema 9). Videoda kasırga rakamları 1991–2025 dönemiyle ve dönem söylenerek verilir.

### 9.7 Elle doğrulanmış referans tablosu (`gorev-06-referanslar`)

Toplayıcıyla alınamayan ama videoda söylenecek olgular (plaj kuralları, bayraklar, plaj erişimi, ulaşım, parklar, kasırga sezonu, sezon ve maliyet) `studio/destinations/thirty_a_references.csv` dosyasında, her satır tek olgu olarak tutulur: kaynak, belge konumu, en fazla 25 kelimelik alıntı, erişim tarihi, belgenin SHA-256'sı, güven, durum (`dogrulandi` / `celiskili` / `dogrulanamadi`) ve yeniden kontrol tarihi. Belgeler `work/referans-belgeler/` altında (repoya girmez). Genel okuyucu/doğrulayıcı `studio/destinations/references.py`; API `GET /api/references`; Veri toplama → Referanslar sekmesi salt okunur. South Walton aylık turist vergisi tahsilatları `thirty_a_tdt_collections.csv` dosyasında (Walton County Clerk çalışma kitabı, 1998-10 → 2026-07). Ayrıntı ve video dili: `docs/M9-REFERANS-TABLOSU.md`.

## 10. Konaklama — şu an nerede kaldık?

Branch: `v0.7-lodging-inventory`  
HEAD: `23905962126ba9f00f7f8b6223c67c9633e70c2c`

Bu branch'te **kod, şema veya production DB değişmedi**. Yalnız kaynak keşfi ve kanıt belgelendi.

Doğrulanan Book>Direct giriş: `https://visitsouthwalton.bookdirect.net/`

Doğrulanan public clone API host: `admin.bookdirect.net`

Önemli public yol sınıfları:
- clone config: `/show.json`
- list/search: `/lodgings.json`, `/lodgings/search.json`
- detail: `/lodgings/:id.json`

Ancak:
- tarihsiz liste 400,
- tarihsiz search 400,
- tarihsiz bilinen-ID detail 400,
- `checkin` zorunlu,
- farklı tarihlerde farklı ID kümeleri dönüyor.

Dune Allen örneği:
- 2–3 Ekim 2026: 112 benzersiz ID
- 2–3 Kasım 2026: 113 benzersiz ID

Bir tarihin listesinde görünmeyen ID, tarihli detail isteğinde yine 200 dönebildi. Dışlama sebebinin availability, minimum stay veya başka backend scope olup olmadığı **unknown** bırakıldı.

Visit South Walton sitemap'i ve 11 public listing directory incelendi. Statik provider/otel sayfaları bulundu ancak bütün provider veya bütün unit kayıtlarını deterministik veren tarihsiz public inventory yolu bulunamadı.

**Karar:** Book>Direct date-filtered search, statik “tam konaklama envanteri” olarak kullanılmayacak.

Bu kaynak ileride tarih/misafir/rate/availability/minimum stay gibi snapshot tabanlı fiyat-müsaitlik katmanında değerlendirilebilir.

Tam envanter için yeni, deterministik bir public/read/export sözleşmesi bulunmadan "tam envanter" iddiasıyla bir lodging connector geliştirilmemelidir. (Şema 7 artık v0.7.0 mahalle verisine aittir; konaklamayla ilgisi yoktur.)

Ayrıntı: `docs/M6-KONAKLAMA-KAYNAK-KEŞFİ.md`

> **7 Ekim 2026 yönetici kararı:** Tarihten bağımsız tam konaklama envanteri şartı kaldırıldı; içerik için gerekli değildir. Konaklama, belirli tarihler için yapılan Book>Direct aramalarının etiketli anlık görüntüleri olarak modellenecek: arama tarihi, giriş/çıkış tarihi, misafir sayısı, mahalle filtresi, dönen kayıtlar ve kaynağın verdiği fiyat alanları. Bu veri hiçbir yerde tam envanter diye adlandırılmayacak.

## 11. Stable release ve test durumu

Stable: main ve tag `v0.8.0` → `de6685f10699d37afd4e1f13b115a6fa13369355` (uygulama 0.8.0, şema 8; 7 Ekim 2026'da GÖREV-06 Adım 1 ile fast-forward ve açıklamalı etiket "v0.8.0 — eşleme v3 ve iklim paketi"; main CI başarılı). Önceki: `v0.7.0` → `7f25e3c`, `v0.6.0` → `a938367`.

Aktif dal `gorev-06-referanslar`:
- 513 Python testi ve 42 frontend testi geçti (tam takım art arda en az 3 kez)
- kasırga sayımında evre kuralı (`/2`, şema 9); referans tablosu, Referanslar sekmesi ve aylık TDT dosyası; uygulama 0.9.0
- main'e alınmadı

Bilinen non-blocking uyarılar:
- Starlette TestClient / httpx deprecation warning
- GitHub Actions Node 20 action'larının Node 24 üzerinde zorlanması uyarısı

## 12. Kullanıcı verisini koruma politikası

`data/` gerçek kullanıcı verisidir.

Yapılmaması gerekenler:
- DB'yi sıfırlamak,
- `data/` klasörünü silmek,
- test için production DB'yi rastgele değiştirmek,
- migration testini doğrudan tek kopya DB üzerinde denemek.

Şema migration'larında:
1. gerçek DB'nin yedeği alınır,
2. mümkünse ayrı copy üzerinde migration denenir,
3. count/FK kontrolleri yapılır,
4. sonra gerçek DB açılır.

**Gerçek veriyi güncelleme kuralı (7 Ekim 2026, GÖREV-04):** Kullanıcı uygulamayı kendisi kullanmaz. Gerçek veritabanı yalnız görev metni açıkça istediğinde ve yalnız uygulamanın normal kullanımıyla (uygulamayı gerçek veri klasörüyle açmak, arayüz veya API üzerinden toplayıcı çalıştırmak) değişir. Bundan önce uygulama kapalıyken `data/` klasörünün tamamı `work/yedek/<YYYYMMDD-HHMM>/` altına kopyalanır. `data/` içindeki dosyalar elle değiştirilmez, silinmez, taşınmaz.

v0.6 migration doğrulamasında raporlanan örnek sayılar:
- 8 sources
- 4 source_history
- 9 jobs
- 6 source_runs
- 159 beach_records
- 6 weather_locations
- 1020 forecast rows
- 138 restaurant_records
- 141 restaurant_regions

Bunlar yalnız o doğrulama anının snapshot'ıdır.

v0.7 (şema 6 → 7) migration denemesi 7 Ekim 2026'da gerçek DB'nin salt okunur kopyasında yapıldı: yukarıdaki satır sayılarının hepsi korundu, `sources` 8 → 9 oldu (yalnız "South Walton · Mahalleler" kaynağı eklendi), boş `neighborhood_records` tablosu oluştu, `foreign_key_check` boş döndü ve yedek alındı. Gerçek `data/` klasörüne dokunulmadı.

Gerçek DB, 7 Ekim 2026'da (GÖREV-04) `data/` klasörünün tam yedeği (`work/yedek/20261007-1318/`) alındıktan sonra uygulamanın normal kullanımıyla şema 7'ye yükseltildi (uygulama yedeği `data/backups/studio-v6-0940e8b1e88246ad87f5c25771e8addf.sqlite3`) ve dört toplayıcı çalıştırıldı. Sonrasında `integrity_check` ok, `foreign_key_check` boş; ayrıntılı sayılar `docs/gorevler/GOREV-04/RAPOR.md` içinde.

v0.8 (şema 7 → 8) migration denemesi 7 Ekim 2026'da gerçek DB'nin `work/` kopyasında yapıldı: eski satırların hepsi korundu, yalnız 8 yeni tablo, 30A iklim yapılandırması (3 istasyon, 1 koridor) ve 3 kaynak eklendi; `integrity_check` ok, `foreign_key_check` boş. Ardından (GÖREV-05) `data/` tam yedeği (`work/yedek/20261007-1533/`, 352 dosya) alındı, uygulama gerçek veriyle açıldı (uygulama yedeği `data/backups/studio-v7-ff556c8bc97447fca0bafa160eb7a9a7.sqlite3`) ve yalnız üç iklim toplayıcısı çalıştırıldı: 168 normal değeri, 182 yıl-ay deniz suyu ortalaması, 227 fırtına geçişi; `integrity_check` ok, `foreign_key_check` boş; ayrıntı `docs/gorevler/GOREV-05/RAPOR.md`.

v0.9 (şema 8 → 9) migration denemesi 7 Ekim 2026'da gerçek DB'nin `work/` kopyasında yapıldı (satır sayıları, kaynaklar ve çekimler aynı; `integrity_check` ok, `foreign_key_check` boş). Ardından (GÖREV-06) `data/` tam yedeği (`work/yedek/20261007-1935/`, 380 dosya) alındı, uygulama gerçek veriyle açıldı (uygulama yedeği `data/backups/studio-v8-14fb0efcabd8429ebdb63c0fdb353ac9.sqlite3`) ve yalnız kasırga toplayıcısı çalıştırıldı (`/2`, 227 geçiş, 10'u işaretli); `integrity_check` ok, `foreign_key_check` boş; ayrıntı `docs/gorevler/GOREV-06/RAPOR.md`.

## 13. Geliştirme çalışma biçimi

1. Proje yöneticisi (ayrı bir Claude sohbeti) görevi `GÖREV-NN` numarasıyla yazar.
2. Kullanıcı görevi Claude Code'a taşır.
3. Claude Code görevi kullanıcının gerçek yerel repo ortamında, görevin kendi dalında uygular.
4. Claude Code testleri çalıştırır, gerekiyorsa geçici veri klasöründe canlı smoke yapar, commit eder ve kendi dalına push eder.
5. Claude Code Türkçe raporunu yazar; görev metni, rapor ve istenen çıktılar `docs/gorevler/GOREV-NN/` altında aynı dala push edilir.
6. Yönetici commit'i, CI sonucunu ve raporu GitHub üzerinden inceler; gerekirse düzeltme görevi verir.
7. Gerçek ortamda yapılması gereken arayüz ve canlı kontrolleri Claude Code kendisi yapar (gerekirse ekran görüntüsüyle); kullanıcıdan onay veya manuel test istenmez.
8. Dal, proje yöneticisinin kararıyla main'e alınır; Claude Code main'e yalnız görev metni bunu açıkça istediğinde alır.
9. Stable release tag'lenir.
10. Sonraki görev dalı açılır.

Görev dalı; yönetici incelemesi ve gereken gerçek ortam kontrolleri tamamlanmadan ve yönetici main'e alma kararını görev metninde vermeden main'e alınmamalıdır. Teknik kararlar yöneticiye aittir; kullanıcı makale (video metni) aşamasına kadar karar mekanizması değildir.

Ayrıntı: `docs/DEVIR/04_GELISTIRME_TEST_RELEASE_AKISI.md`

## 14. Şu anda uygulanmamış başlıca alanlar

- Tam lodging inventory connector
- Lodging rates / availability history
- Deniz koşulları (dalga, akıntı, bayrak geçmişi); iklim normalleri, deniz suyu sıcaklığı ve kasırga geçmişi v0.8.0'da var
- Nem normali (hazır bir kaynak bulunamadı)
- Yakıt fiyatı
- Overture/POI enrichment
- Etkinlik connector
- Ulaşım connector
- Grocery / günlük ihtiyaç fiyatları
- Restoran menü/fiyat enrichment
- Scheduler
- Otomatik entity matching
- Mahalle sınırı poligonları (plaj–mahalle eşlemesi ilçe alt bölüm poligonları, komşuluk ve boylam yöntemleriyle ayrı katmandadır; mahalle sınırı yoktur)
- AI evidence-pack / konu seçimi
- Makale/senaryo
- Görsel plan
- Video render
- Yayın paketi

## 15. Sonraki geliştirici / AI için ilk kurallar

1. Önce bu belgeyi oku.
2. Sonra `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md` oku.
3. Aktif görev veri kaynağıyla ilgiliyse `03_VERI_KAYNAKLARI_VE_DOGRULAMA.md` oku.
4. Kod değişmeden önce gerçek branch/head'i doğrula.
5. `data/` klasörüne zarar verme.
6. Kaynak semantiğini doğrulamadan schema/domain yazma.
7. 30A-specific davranışı generic core'a gömme.
8. Yeni destination uyumluluğunu test et.
9. Test fixture'ları canlı web'e bağımlı yapma.
10. Canlı smoke sonuçlarını sabit production/test sayısı haline getirme.
11. Görev metni (yönetici kararı) açıkça istemedikçe görev dalını main'e merge etme.
12. Konaklama konusunda date-filtered sonucu “tam inventory” diye modelleme.

## 16. Devir dokümanı indeksi

- `CALISMA_MANTIGI.md` — ana devir ve çalışma mantığı
- `docs/KONSEPT.md` — kanal konsepti ve içerik stratejisi; içerik yönünde bağlayıcı belge
- `docs/TEKNIK-CALISMA-MANTIGI-v0.6.md` — v0.6 uygulamasının ayrıntılı teknik çalışma mantığı (eski kök belge)
- `docs/gorevler/` — görev metinleri, raporlar ve görev çıktıları (`GOREV-NN/`)
- `docs/DEVIR/01_URUN_VIZYONU_VE_KARARLAR.md`
- `docs/DEVIR/02_TEKNIK_MIMARI_VE_VERI_MODELI.md`
- `docs/DEVIR/03_VERI_KAYNAKLARI_VE_DOGRULAMA.md`
- `docs/DEVIR/04_GELISTIRME_TEST_RELEASE_AKISI.md`
- `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`
- `docs/DEVIR/06_ROADMAP_VE_ACIK_KONULAR.md`
- `docs/DEVIR/07_YENI_AI_BASLANGIC_TALIMATI.md`

Mevcut ayrıntılı domain belgeleri de korunmalıdır:
- `docs/M2-VERI-TOPLAMA.md`
- `docs/M3-HAVA-VERISI.md`
- `docs/M4-RESTORAN-VERISI.md`
- `docs/M5-DESTINASYON-KATMANI.md`
- `docs/M6-KONAKLAMA-KAYNAK-KEŞFİ.md`
- `docs/M7-MAHALLE-VERISI.md`
- `docs/M8-IKLIM-VERISI.md`
- `docs/M9-REFERANS-TABLOSU.md`

---

**Son güncelleme:** 7 Ekim 2026  
**Stable:** v0.8.0 — eşleme v3 ve iklim paketi (`de6685f`)  
**Aktif geliştirme:** `gorev-06-referanslar` — kasırga evre kuralı ve referans tablosu, uygulama 0.9.0, şema 9 (yönetici incelemesinde)
