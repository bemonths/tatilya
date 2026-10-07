# Kademeli geliştirme planı

## Aşama 1 — Kaynak kütüphanesi ve uygulama temeli · Tamamlandı

- Housing Atlas mimarisini salt okunur olarak incele.
- 30A için bağımsız Python/FastAPI ve SQLite projesi oluştur.
- Lacivert/turuncu arayüz; sol üretim akışı, merkezde kaynak tablosu, ayrıntı ve iş panelleri.
- Kaynak ekle, düzenle, arşivle ve geri al. Arama, kategori ve bölge filtreleri.
- Katalog kontrolünü gerçek bir arka plan işi olarak çalıştır; sonuç ve günlükleri sakla.
- Veritabanı kalıcılığı, aynı adresin tekrar eklenmesi, eski sürümle güncelleme, iptal, yarım kalan iş ve başarısız istekleri test et.
- Arayüzü tarayıcıda açıp temel kullanıcı akışını kontrol et.

## Aşama 2 — İlk gerçek veri kaynağı · Tamamlandı, v0.2.0

Visit South Walton plaj erişimleri bağlandı. Sayfadaki harita noktaları tek HTTP isteğiyle okunur; JavaScript çalıştırılmadan JSON nesneleri ayrıştırılır. Kıyı kapsamı açık kuralla seçilir. Ham kaynak, tarih, ayrıştırıcı sürümü ve kayıtlar her iş için ayrı saklanır. Hata, sınırlı yeniden deneme, iptal, filtreleme, kayıt ayrıntısı, sürüm seçimi ve CSV dışa aktarma eklendi. Diğer kaynak bağlayıcıları sonraki aşamalardadır. [Ayrıntılı kapsam](M2-VERI-TOPLAMA.md).

## Aşama 3 — Genel veri temeli · v0.3.0 tamamlandı; veri kalite kapsamı kısmi

Genel source_runs, jobs.source_id, connector registry, source_collection işi, atomik v2 migration ve yükseltme öncesi yedek tamamlandı. Başarılı/başarısız/iptal run takibi ve temel plaj sürüm farkı çalışır. 13 canonical bölge kimliği ve entity/entity_sources şemaları hazırdır; henüz otomatik entity matching veya polygon mapping yapılmaz. Aynı host içi sınırlı HTTP yönlendirme, kontrollü teşhis ve Python 3.12 GitHub Actions eklendi.

Sonraki veri işleri: gerçek yeni connector'lar, domain bazında kalite raporları, birim/tarih/fiyat karşılaştırmaları ve kaynaklar arası veri eşleme tasarımı. Konaklama connector'ı henüz yoktur; NWS hava v0.4, restoran dizini v0.5 kapsamında eklendi. Entity yönetim ekranı ve otomatik eşleme ileride değerlendirilecektir. Scheduler henüz yoktur.

## Veri toplama genişlemesi — NWS hava · v0.4.0

İkinci gerçek connector NWS resmî API'sidir. Üç provenance'ı açık plaj örnek noktası için points, dönem/saatlik forecast ve aktif alerts toplanır. Canonical mahalle merkezi/polygon üretilmez. V4 şema, ham yanıt paketi, sürüm geçmişi, Plaj/Hava sekmeleri ve timezone gösterimi hazırdır. Kayan hava penceresine kayıt diff'i uygulanmaz. [Kapsam ve sınırlar](M3-HAVA-VERISI.md).

Tarihsel iklim, current conditions/observation station, scheduler ve Claude/OpenAI henüz yoktur. Sonraki aşamalar aşağıda plan olarak kalır.

## Veri toplama genişlemesi — Restoran dizini · v0.5.0

Üçüncü connector Visit South Walton HTML dizin/detay sayfalarıdır. Ana formdan keşfedilen Restaurants filtresiyle 13 canonical mahalle taranır; Miramar Beach, Seascape ve Sandestin alınmaz. Detaylar URL path'i ile tekilleştirilir, çoklu mahalle ilişkileri korunur. V5 şema, yedekli yükseltme, raw manifest, generic transaction/diff, Restoranlar sekmesi ve arama/filtre/ayrıntı eklendi. [Kapsam ve sınırlar](M4-RESTORAN-VERISI.md).

Çalışan bağlantılar: Beaches = HTML içi JSON, Weather = NWS API, Restaurants = HTML dizin/detay. Menü/fiyat enrichment, ratings/reviews, own-site crawling, scheduler ve AI henüz yoktur. Güvenilir kaynak tarihi olmayan restoranlarda source_updated null kalır.

## Aşama 4 — Konu, rakip ve brief · Plan

Claude CLI bağlantısını bağımsız sağlayıcı olarak ekle. Önce sınırlı bir test görevi, ardından doğrulanmış veri paketiyle konu önerisi. Rakip kayıtları, konu seçimi, kaynaklı brief ve yönetici onayı (kullanıcı makale aşamasında devreye girer). Hesapları test edilmiş fonksiyonlarla yap.

## Aşama 5 — Makale ve kaynak denetimi

Brief üzerinden taslak, sayısal iddiaların kontrolü, düzenleme ve sürüm geçmişi. Üst aşamadaki veri değiştiğinde bağlı çıktıları eskimiş olarak işaretle.

## Aşama 6 — Görsel plan ve video

Sahne listesi, görsel varlıklar, harita/grafik ihtiyaçları; sonra önizleme ve render. Çalışan veri ve metin akışı tamamlanmadan render kapsamını büyütme.

## Aşama 7 — Yayın paketi ve masaüstü paketleme

Başlık, açıklama, makale, video ve görselleri dışa aktar. Çerçevesiz uygulama penceresi, masaüstü kısayolu ve kapanma davranışı. Otomatik yayın bağlantıları ayrı kapsam olarak ele alınır.

## Destinasyon temeli — v0.6.0

Şema 6, ilk production destinasyonu 30A, destinasyon kapsamlı sources/regions/jobs/runs/entities, DB hava noktaları, ConnectorContext ve global seçici tamamlandı. Gerçek kullanıcı DB’si önce kopyada doğrulandı; eski veriler korundu. Sentetik ikinci/üçüncü destinasyonlar sadece testlerde kullanıldı. NWS generic kaldı; South Walton connector’ları 30A kapsamına bağlandı. Onaylı v0.6, 1 Ekim 2026'da fast-forward ile main'e alındı ve v0.6.0 etiketiyle sabitlendi. [M5 kapsam ve testler](M5-DESTINASYON-KATMANI.md).

## Konaklama envanteri — v0.7 keşif aşaması

Book>Direct public JSON araması doğrulandı; aynı konumun bütün sayfaları farklı tarihlerde farklı kayıt kimlikleri döndürüyor. 3 Ekim'deki ikinci keşfin kararı C: public tarihsiz tam unit/provider inventory yolu hâlâ bulunamadı. Bundle, clone config, sitemap/dizinler ve resmi parent/child modeli incelendi; güncel resmi yönerge accommodation yönetiminin Extranet'ten Book>Direct'e geçtiğini belirtiyor. Tam/tarihten bağımsız envanter şartı korunuyor. Schema 7, lodging connector veya yeni ekran eklenmedi; uygulama v0.6.0 olarak kalır. [M6 keşif ve kanıt](M6-KONAKLAMA-KAYNAK-KEŞFİ.md). 7 Ekim 2026 yönetici kararıyla tam envanter şartı kaldırıldı; konaklama tarihli arama anlık görüntüleri olarak modellenecek.

## Mahalle verisi ve plaj–mahalle eşlemesi — v0.7.0

GÖREV-03 (7 Ekim 2026, `gorev-03-mahalleler` dalı): Visit South Walton mahalle dizini için 30A'ya özel toplayıcı, şema 7 ve Veri toplama → Mahalleler sekmesi; 53 plaj erişimini mahallelere bağlayan, yöntemi etiketli (resmî rehber / program türetimi) ayrı eşleme katmanı ve plaj ekranında mahalle etiketi ile filtre. Gerçek DB'nin kopyasında v6 → v7 denemesi yapıldı. 7 Ekim 2026'da main'e alındı ve `v0.7.0` olarak etiketlendi. GÖREV-04'te gerçek veritabanı normal kullanımla v7'ye yükseltildi ve eşleme, Walton County alt bölüm poligonlarıyla yeniden kuruldu (v2: resmî rehber → ilçe alt bölüm verisi → program türetimi). [M7 kapsam, yöntem ve doğrulama](M7-MAHALLE-VERISI.md).
