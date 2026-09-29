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

Sonraki veri işleri: gerçek yeni connector'lar, domain bazında kalite raporları, birim/tarih/fiyat karşılaştırmaları ve kaynaklar arası veri eşleme tasarımı. Konaklama/restoran/hava connector'ları henüz yoktur. Entity yönetim ekranı ve otomatik eşleme ileride değerlendirilecektir. Scheduler henüz yoktur.

## Aşama 4 — Konu, rakip ve brief

Claude CLI bağlantısını bağımsız sağlayıcı olarak ekle. Önce sınırlı bir test görevi, ardından doğrulanmış veri paketiyle konu önerisi. Rakip kayıtları, konu seçimi, kaynaklı brief ve kullanıcı onayı. Hesapları test edilmiş fonksiyonlarla yap.

## Aşama 5 — Makale ve kaynak denetimi

Brief üzerinden taslak, sayısal iddiaların kontrolü, düzenleme ve sürüm geçmişi. Üst aşamadaki veri değiştiğinde bağlı çıktıları eskimiş olarak işaretle.

## Aşama 6 — Görsel plan ve video

Sahne listesi, görsel varlıklar, harita/grafik ihtiyaçları; sonra önizleme ve render. Çalışan veri ve metin akışı tamamlanmadan render kapsamını büyütme.

## Aşama 7 — Yayın paketi ve masaüstü paketleme

Başlık, açıklama, makale, video ve görselleri dışa aktar. Çerçevesiz uygulama penceresi, masaüstü kısayolu ve kapanma davranışı. Otomatik yayın bağlantıları ayrı kapsam olarak ele alınır.
