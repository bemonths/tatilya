# Roadmap ve Açık Konular

> Bu belge kesin sprint planı değil, mevcut ürün kararlarıyla uyumlu öncelik havuzudur. Proje yöneticisinin kararı olmadan yeni domain seçilmiş sayılmaz.

## Şu anki açık konu: lodging

> **7 Ekim 2026 yönetici kararı:** Tarihten bağımsız tam konaklama envanteri şartı kaldırıldı; içerik için gerekli değildir. Konaklama, belirli tarihler için yapılan Book>Direct aramalarının etiketli anlık görüntüleri olarak modellenecek: arama tarihi, giriş/çıkış tarihi, misafir sayısı, mahalle filtresi, dönen kayıtlar ve kaynağın verdiği fiyat alanları. Bu veri hiçbir yerde tam envanter diye adlandırılmayacak. Bu bölümün aşağıdaki kısmı kararın öncesindeki durumu anlatır.

### Hedef

30A için tarihten bağımsız konaklama varlık envanteri.

### Bloker

Public deterministik:
- unit inventory
veya
- provider inventory

bulunmadı.

### Devam edebilmek için kabul edilebilir yollar

1. Book>Direct'in supported date-independent read/export route'u.
2. Walton County Tourism'un tam accommodation listing export'u.
3. Başka resmî, deterministik provider/unit dizini.
4. Kapsamı açıkça farklı tanımlanmış başka bir dataset.

### Kabul edilmeyen workaround

- arbitrary future date
- multi-date union
- “en çok kayıt döndüren tarih”
- search count'u inventory count saymak

## Lodging price / availability — ayrı domain

Book>Direct burada daha uygun adaydır.

Gelecekte olası model:

```text
lodging entity
+ search date
+ checkin/checkout
+ guests
+ observed availability
+ observed rate
+ taxes/fees if explicitly exposed
+ min stay
+ fetched_at
```

Bu veri envanter değildir; time-indexed market/search snapshot'tır.

Inventory identity çözülmeden price history ile yanlış entity bağlama riski vardır.

## Tarihsel hava / iklim

Mevcut NWS forecast kısa dönemdir.

Evergreen YouTube için daha değerli katman:
- NOAA/NCEI historical climate
- aylık sıcaklık
- yağış
- ekstrem olay sıklığı
- sezon kıyasları

Bu domain, “hangi ay daha mantıklı?” videolarına yüksek katkı sağlar.

## Deniz sıcaklığı / sahil koşulları

Aday:
- NOAA/NDBC
- NOAA Tides & Currents

Potansiyel:
- seasonal sea temperature
- wave/wind proxy
- beach-condition context

Resmî istasyonun 30A temsiliyeti ayrıca doğrulanmalıdır.

## Etkinlikler

Visit South Walton events:
`https://www.visitsouthwalton.com/events/`

Gerekli kararlar:
- event stable ID
- recurring events
- cancellations
- start/end timezone
- venue identity
- source updated

Event history saklanmalıdır.

## Ulaşım

Visit South Walton transportation directory adaydır.

Ayrıca:
- airports
- drive time
- parking
- shuttle
- bike/golf-cart policy
- transit

gibi decision-support alanları değerlendirilebilir.

Travel time dinamik trafik verisiyle karıştırılmamalıdır.

## Fuel

EIA gibi resmî kaynaklar:
- bölgesel yakıt fiyat trendi

için kullanılabilir.

30A mikro-lokasyon seviyesinde “bugünkü en ucuz benzin” gibi iddia için farklı kaynak gerekir.

## POI / transportation geometry

Overture Maps:
- business/POI discovery
- transportation features

için adaydır.

Canonical entity matching olmadan dış POI dataset'i doğrudan source record'larla merge edilmemelidir.

## Restaurants enrichment

Bugün:
Visit South Walton directory.

Gelecekte:
- restaurant own websites
- menus
- prices
- opening hours

Fakat:
- entity matching,
- menu versioning,
- price field semantics

önce tasarlanmalıdır.

## Grocery / günlük harcama

İçerik değerli olabilir:
- Publix / Walmart / local markets
- basket snapshots

Ancak veri toplama maliyeti ve değişkenliği yüksektir.

## Entity matching

Gelecekte kritik.

Amaç:
aynı gerçek varlığı:
- Visit South Walton
- own website
- Overture
- lodging platform
- menu source

arasında bağlamak.

Otomatik fuzzy matching tek başına güvenilir değildir.

Yaklaşım:
- stable URL/domain
- phone
- coordinates
- explicit source relations
- manual review

kombinasyonu.

## Region polygons

Bugün canonical region ID'leri var fakat polygon yok.

Gelecekte:
- adres/coordinate → region

eşlemesi için güvenilir boundary kaynağı gerekir.

Connector'lar bugün bu inference'ı yapmamalıdır.

## Scheduler

Bugün `cadence` yalnız metadata.

Gelecekte:
- dynamic source weekly/daily
- static source slower
- backoff
- source health
- changed-source alerts

gibi scheduler düşünülebilir.

## AI / evidence pack

Veri temeli yeterince olgunlaştığında:

1. topic decision
2. relevant source_run selection
3. evidence pack
4. claims + citations
5. brief
6. user approval
7. script

Bu aşamada AI doğrudan canlı web yerine önce trusted DB kullanmalıdır; gerektiğinde web supplement eklenir.

## Content stages

### Konu / competitor / brief
Plan.

### Makale / source audit
Plan.

### Görsel plan
Plan.

### Video render
Plan.

### Publish package
Plan.

Bunlar veri katmanının yerine geçmemeli.

## Multi-destination expansion

İkinci production destination eklenmeden önce mevcut v0.6 mimarisi yeterli bir temel sağlıyor.

Yeni destination checklist:
1. destination metadata
2. canonical regions
3. source seeds
4. weather anchors
5. generic connector reuse
6. specific connector gerekiyorsa scope guard
7. isolation tests
8. UI smoke

## Önerilen karar sırası

Lodging research sonuç C iken makul seçenekler:

### Seçenek A — lodging kaynağı aramaya devam
Yalnız yeni güçlü lead varsa.

### Seçenek B — lodging blocker'ını dokümante edip başka veri domain'ine geç
Örneğin historical climate / events / sea temperature.

### Seçenek C — Book>Direct price/availability'ye erken geç
Ancak inventory/entity identity sorunu çözülmeden veri anlamı daha zor olabilir; dikkatli tasarım gerekir.

## Şu anda yapılmaması gerekenler

- v0.7 branch'i “tamamlandı” diye main'e almak.
- Schema 7'yi boş yere yükseltmek.
- Book>Direct sonucu inventory diye adlandırmak.
- Yeni ikinci destination ekleyip core tasarımı aynı anda test alanına çevirmek.
- Veri katmanı henüz genişlerken AI/video render'a erken atlamak.
