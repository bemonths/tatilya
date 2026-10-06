# Ürün Vizyonu ve Ana Kararlar

## Amaç

30A Studio'nun ilk amacı, 30A / South Walton için güvenilir bir yerel veri ve araştırma katmanı kurmak; daha sonra bu katmanı YouTube içerik üretim zincirine bağlamaktır.

Programın başarısı “çok veri toplaması” ile değil, şu üç şeyle ölçülmelidir:

1. doğru kaynağı kullanması,
2. verinin semantiğini yanlış yorumlamaması,
3. kullanıcıya/AI'a gerçek tatil kararlarını çözebilecek kanıt sağlaması.

## YouTube kullanım modeli

Hedef içerik:
- İngilizce,
- yüz göstermeyen,
- yaklaşık 15–17 dakika,
- ana sayfa/önerilen akışta merak uyandıran ama pratik karar değeri olan,
- 30A tatili planlayan kişinin bir kararını çözmeye çalışan video.

İçerik yalnız “Seaside güzel bir yer” gibi genel tanıtım olmamalıdır.

Daha iyi örnekler:
- First-time visitors: Seaside vs Rosemary Beach
- Which 30A neighborhood works best without a car?
- Where do you get the easiest beach access?
- Best month for warm water with lower storm risk?
- Where are restaurants concentrated?
- What changes in shoulder season?
- Which area is better for families / couples / quiet stays?

## Veri neden toplanıyor?

Veriler videonun içinde tablo okumak için değil, şu katmanları beslemek için toplanır:

```text
Kaynak
→ normalize veri
→ geçmiş/snapshot
→ evidence pack
→ konu/karar sorusu
→ kaynaklı brief
→ senaryo
→ görsel/harita/grafik planı
→ video
```

AI'ın serbest web bilgisinden ziyade önce güvenilir, izlenebilir ve tarihçesi tutulan veriyle çalışması hedeflenir.

## Çok-destinasyon kararı

30A ürünün ilk destinasyonudur; ürünün motoru mantıksal olarak yalnız 30A'ya bağımlı olmamalıdır.

Uzun vadeli model:
- 30A
- başka mikro-destinasyonlar
- aynı generic core
- destination-specific profile ve connector'lar

Bu nedenle:
- source URL unique kuralı destination-scoped'dur,
- region isimleri destination-scoped'dur,
- weather anchor'ları destination-scoped'dur,
- source_runs/jobs provenance destination taşır.

## Kullanıcı kitlesi

Doğal izleyici kitlesi 45–65+ olabilir, fakat kanal “senior travel” olarak markalanmamalıdır. İçerik herkes için erişilebilir ve karar odaklı olmalıdır.

## Kaynak önceliği

Genel yaklaşım:

1. Resmî / birincil kamu veya destinasyon kaynağı
2. İşletmenin kendi sitesi
3. Büyük aggregator / platform
4. Üçüncü taraf analiz verisi

Bu mutlak kalite sıralaması değildir; her kaynak yalnız **otorite olduğu alan** için kullanılır.

Örnek:
- NWS → forecast ve alerts
- Visit South Walton → resmî bölgesel dizinler / plaj erişimleri
- İşletmenin sitesi → menü / doğrudan hizmet ayrıntısı
- Booking/Expedia vb. → kapsam / fiyat karşılaştırması
- AirDNA → validasyon/analiz, gerekirse

## Semantik doğruluk

“HTTP 200 geldi” veri doğrulaması değildir.

Örnek konaklama vakası:
Book>Direct sonuçları tarih parametresine göre değişiyor. Bu sonuçlar teknik olarak okunabiliyor; fakat “30A'nın tam lodging inventory'si” anlamına geldiği kanıtlanmadı. Bu yüzden connector kodlanmadı.

Bu proje için doğru karar:

> **Eksik ama doğru tanımlanmış veri, tam görünüp yanlış anlam taşıyan veriden daha değerlidir.**

## Veri geçmişi kararı

Dinamik veriler yalnız son değer olarak tutulmamalıdır.

Örnek gelecekte:
- fiyatlar,
- availability,
- yakıt,
- deniz sıcaklığı,
- hava,
- etkinlikler

snapshot/time-series yaklaşımıyla saklanmalıdır.

Statik veya yavaş değişen kaynaklar daha seyrek yenilenebilir.

## AI rolü

AI gelecekte:
- evidence pack oluşturabilir,
- konu önerebilir,
- kaynaklı brief yazabilir,
- senaryo taslağı oluşturabilir,
- görsel planı çıkarabilir.

Ancak:
- kaynakta olmayan alanı uydurmamalı,
- tarih/ölçüm kapsamını karıştırmamalı,
- belirsizliği saklamamalı,
- otomatik olarak “resmî” olmayan bir veriyi doğrulanmış gerçek gibi yükseltmemelidir.

## Ürün sınırları

Şu anda sistem:
- yayın otomasyonu değildir,
- video render sistemi değildir,
- AI yazı sistemi değildir,
- uzaktan çok kullanıcılı SaaS değildir.

Bugün esas olarak:

**yerel, güvenilir, sürümlü veri toplama ve araştırma temelidir.**

## Yeni modül karar soruları

Yeni modül önerildiğinde şu sorular sorulmalıdır:

- Kullanıcıya hangi tatil kararını çözmede yardım ediyor?
- Kaynağın semantiği doğrulandı mı?
- Veri zaman bağımlı mı?
- Snapshot/history gerekiyor mu?
- Stabil ID var mı?
- Destination scope nedir?
- Generic connector olabilir mi?
- Ham kanıt saklanıyor mu?
- Başarısız crawl önceki başarıyı koruyor mu?
- Bu verinin ileride AI/evidence pack içinde nasıl kullanılacağı açık mı?
