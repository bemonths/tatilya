# Aşama 2 — İlk gerçek veri kaynağı · v0.2 tarihsel çalışma kaydı

Bu belge v0.2 aşamasını kaydeder. Güncel v0.3 run/connector, migration ve yönlendirme davranışı [çalışma mantığında](../CALISMA_MANTIGI.md) açıklanmıştır.

## Kaynak ve yöntem

Kaynak: https://www.visitsouthwalton.com/beach-bay-access-locations/

29 Eylül 2026 incelemesinde sayfadaki `initMarkers` işlevinin `data` dizisinde 70 harita noktası bulundu. Dizi JSON nesnelerinden oluşuyor; JavaScript çalıştırılmadan ayrıştırılıyor. Haritanın diğer coğrafi katmanları ve güncel tehlike bayrağı bu aşamanın kapsamı dışında.

## Kapsam kuralı

30A kıyı odağı için kaynakta `regional` veya `neighborhood` türünde olan ve yerleşimi `Santa Rosa Beach`, `Grayton Beach`, `Seacrest` veya `Inlet Beach` yazan kayıtlar gösterilir. Miramar ve koy/göl noktaları dışarıda kalır. Bu, uygulamanın açıkça belirtilen seçme kuralıdır; tüm plajları veya özel erişimleri kapsadığı iddia edilmez. Kaynaktaki yerleşim adı mahalle düzeyinde yeniden tahmin edilmez. Kaynakta listelenmeyen bir olanak “yok” diye yorumlanmaz.

## Uygulama

- Tek izinli kaynak adresi için HTTP bağlayıcısı; TLS doğrulaması, süre ve boyut sınırları.
- En çok iki deneme, geçici ağ hatasında sınırlı yeniden deneme ve iptal kontrolü.
- Ham HTML, SHA-256 özeti, çekim zamanı, kaynak güncelleme metni ve ayrıştırıcı sürümü.
- Önce bellekte bütün kayıtları doğrula; hatalı/boş kaynakta eski başarılı sürümü koru.
- İş başına ayrı veri sürümü; kayıtlar ve başarılı iş sonucu tek veritabanı işleminde kaydedilir.
- Veri toplama ekranı: kayıt tablosu, arama, kaynak yerleşimi ve olanak filtreleri, ayrıntılar ve önceki sürümler.
- CSV dışa aktarma ve ham kaynak indirme.
- Başlangıçtaki yedi kaynak adayından yalnızca plaj erişimi bağlayıcısı bu aşamada etkin.

## Kontroller

- Sentetik HTML örnekleri: sondaki virgül, metindeki özel karakterler, eksik/bozuk dizi, yinelenen kimlik, geçersiz koordinat, bilinmeyen tür ve boş sonuç.
- Bir olanak kaynakta belirtilmemişse eksik olarak koru.
- İptal ile bitiş çakışması; iptal edilen iş veri sürümünü yayımlamamalı.
- Aynı kaynaktan iki başarılı çekim: ikisi de korunmalı; yenisi ayrı sürüm olmalı.
- Başarısız çekim: son başarılı sürüm ve kullanıcı kaynak kaydı değişmemeli.
- Bir gerçek çekim; kaynak sayısıyla ayrıştırılan, seçilen ve dışarıda kalan sayılar tutmalı.
- Arayüzde toplama, filtreleme, ayrıntılar ve dışa aktarma bağlantısı.

## Doğrulama sonucu · 30 Eylül 2026

40 otomatik test geçti. Kaynak kütüphanesi regresyonları, kaynak ayrıştırma ve kapsam, HTTP hata/boyut sınırı, tek yeniden deneme, iptal, eşzamanlı iş engeli, sürüm kalıcılığı, şema yükseltme ve CSV çıktısı denetlendi. Testler canlı ağa bağlanmaz. Test istemcisinin httpx geçiş uyarısı var; test başarısızlığı yok.

Uygulamadan ilk gerçek çekim yapıldı: **70 kaynak noktası = 53 seçilen kıyı kaydı + 17 kapsam dışı kayıt**. İlk başarılı sürüm kimliği: `86ed6fa86e6043bcb6f5694646b4db15`. Arayüzde yerleşim/olanak/arama filtreleri ve boş sonuç görünümü kontrol edildi; gerçek CSV dosyası indirildi. Olanak adları Türkçe gösterilir, kaynağın özgün etiketleri veritabanında korunur. Playwright ve Claude çağrısı yapılmadı.
