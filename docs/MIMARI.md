# 30A Studio — inceleme ve bağımsız proje mimarisi

29 Eylül 2026 incelemesi · 30 Eylül 2026 v0.2.0 güncellemesi

## Housing Atlas incelemesi

İnceleme, `C:\Users\1\source\repos\housing-atlas` altındaki kaynak kodu ve kullanıcının önceki konuşmadaki beş ekran görüntüsü üzerinden yapıldı. Bu klasörde hiçbir dosya düzenlenmedi, proje çalıştırılmadı ve yeni projeye dosya kopyalanmadı. `C:\Users\1\HousingAtlas` kaynak kodu değil, mevcut uygulamanın kullanıcı verisi klasörüdür; yalnızca üst düzey dosya adları incelendi, ayar ve veri içerikleri okunmadı.

**Gerçek teknoloji Python 3.12 + FastAPI/Uvicorn + HTML/CSS/JavaScript.** Önceki konuşmadaki PySide6/Qt tahmini doğru değil. Edge veya Chrome, yerel uygulamayı adres çubuğu olmayan bir pencerede gösteriyor.

| Alan | Kodda görülen yapı | İncelenen dosyalar |
|---|---|---|
| Uygulama | FastAPI uygulama fabrikası, yerel Uvicorn sunucusu, statik ön yüz | `pyproject.toml`, `atlas/app.py` |
| Başlatma | Boş port seçimi, tek uygulama denetimi, Edge/Chrome `--app` penceresi, kapanma bekçisi | `atlas/launcher.py`, `README.md`, `docs/TASARIM.md` |
| Arayüz | Çerçevesiz ES modülleri; adres parçasıyla ekran geçişi; ortak durum deposu; her aşama için ekran modülü | `atlas/web/js/app.js`, `store.js`, `screens/` |
| Görsel dil | CSS değişkenleri; lacivert yüzeyler, turuncu vurgu; sabit sol akış, üst bağlam çubuğu, tablo ve ayrıntı alanı, sağ iş paneli | `atlas/web/css/app.css`, ekran görüntüleri |
| Grafik | Ön yüzde bağımlılıksız SVG çizgi grafikleri; video tarafında Matplotlib ve ayrı sahne/render modülleri | `atlas/web/js/charts.js`, `pyproject.toml`, `atlas/studio/` dosya düzeni |
| Veri katmanı | Eyalet/adım klasörleri; JSON/CSV çıktıları; atomik JSON yazımı; tarihli önceki sürümler | `atlas/config.py`, `state.py`, `versions.py`, `docs/TASARIM.md` |
| Akış durumu | Hazır, çalışıyor, onay bekliyor, tamamlandı, hata ve eskimiş durumları; girdi değişince sonraki çıktıların eskime takibi | `atlas/state.py` |
| Playwright | Senkron Playwright arayüzü iş parçacığında; kurulu Chrome ile kalıcı profil veya açık Chrome'a CDP bağlantısı | `atlas/sources/redfin_listings.py:264` |
| Claude | CLI alt süreci; standart girdiden görev; akış halinde JSON olayları; model/efor/tur ayarları; araç izinleri; çıktı şeması ve anlam denetimleri | `atlas/ai/runner.py`, `stages.py`, `validate.py`, `atlas/steps/claude_run.py` |
| Görev kuyruğu | Bellekte FIFO kuyruk; iş başına iş parçacığı; varsayılan en çok dört çalışan; aynı iş türü ve eyalet için tekrar engeli; iptal ve süreç ağacı sonlandırma | `atlas/jobs.py` |
| Canlı ilerleme | Server-Sent Events; ilk bağlantıda iş listesi, sonra güncellemeler; sık olayları seyrekleştirme | `atlas/events.py`, `atlas/web/js/store.js` |
| Gizli bilgiler | Windows Kimlik Bilgisi Yöneticisi üzerinden `keyring`; HousingAtlas hizmet adı | `atlas/secrets.py`, `README.md` |

Bu tespitler mimari incelemedir; Housing Atlas için çalıştırma, entegrasyon testi veya genel kod denetimi yapılmadı. Özellikle canlı Claude ve Playwright davranışları bu çalışmada denenmedi.

## 30A için karar

Yeni proje sıfırdan yazıldı. Housing Atlas'ın pencere düzeni ve aşamalı çalışma yaklaşımı tasarım referansı olarak kullanıldı. Emlak hesapları, mevcut veri, tarayıcı profili, ayarlar, Claude talimatları ve kod dosyaları taşınmadı.

Önerilen temel: **Python + FastAPI + bağımsız HTML/CSS/JavaScript arayüzü + SQLite.** Bu yerel ve tek kullanıcılı ilk sürümde ayrıca Node derlemesi veya veritabanı sunucusu gerekmiyor. SQLite seçimi; kaynak, bölge, zaman, iş ve içerik ilişkilerini sorgulamak, işlem bütünlüğü sağlamak ve iş geçmişini yeniden açılışta korumak için yapıldı. Python'un [SQLite desteği](https://docs.python.org/3.12/library/sqlite3.html) ve [FastAPI veritabanı belgeleri](https://fastapi.tiangolo.com/tutorial/sql-databases/) incelendi. İleride çok kullanıcılı uzak kurulum gerekirse veritabanı ve iş yürütücüsü ayrı servislere taşınabilir.

### Şimdi uygulanan düzen

```text
30a-studio/
  baslat.bat               Kullanıcı için başlatma
  pyproject.toml           Bağımlılıklar
  studio/
    __main__.py            Yerel sunucu ve tarayıcı açılışı
    app.py                 API, uygulama yaşam döngüsü, canlı iş akışı
    models.py              Kaynak alanlarının doğrulanması
    catalog.py             Kategoriler, bölgeler ve kaynak adayları
    database.py            SQLite, değişiklik geçmişi ve iş kayıtları
    jobs.py                Katalog kontrolü, veri toplama ve iş yaşam döngüsü
    sources/beaches.py     South Walton plaj haritası bağlayıcısı
    web/                   Yeni arayüz, stiller, ekranlar, API istemcisi
  tests/                   Veri kaybı, çakışma, iptal ve API kontrolleri
  docs/                    Mimari ve aşama planı
  data/                    SQLite ve raw/<iş-kimliği>/source.html
```

Kaynak güncellemeleri sürüm numarasıyla denetlenir; eski bir penceredeki düzenleme yeni kaydı ezemez. Arşivleme kaydı silmez. Geçmiş kayıtlar veritabanında korunur; bu ilk sürümde geçmişi görüntüleyen ayrı ekran henüz yoktur. İşler tek çalışanlı kuyruktadır. Kuyruk durumu ve sonuçlar SQLite'ta tutulur; yeniden açılışta yarım kalan işler “yarıda kaldı” olarak işaretlenir, otomatik yeniden çalıştırılmaz. Arayüze SSE üzerinden değişen iş listesi aktarılır; ilk sürümde sunucu bunu saniyede bir sorgular.

### Modüllerin gelişimi

| Modül | Sorumluluk |
|---|---|
| `sources/` | Plaj erişimi bağlayıcısı mevcut; diğer siteler için alan eşleme ve sayfalama eklenecek |
| `collection/` | HTTP/JSON/HTML/PDF okuma; gerektiğinde Playwright oturumları |
| `quality/` | Zorunlu alan, birim, zaman, mükerrer kayıt ve kaynak kontrolü |
| `workflow/` | Önkoşullar, onaylar, girdi sürümleri ve sonraki çıktıların eskime takibi |
| `ai/` | Claude CLI sağlayıcısı; ileride başka sağlayıcı eklenebilen arayüz |
| `content/` | Konu, rakip analizi, brief, makale ve sürümleri |
| `media/` | Görsel plan, varlık kayıtları, sahneler ve render |

Plaj kaynağı dışındaki bağlayıcılar ve içerik üretim modülleri henüz bağlı değildir. İlgili içerik ekranları kapsamı gösteren plan ekranlarıdır.

### Veri sözleşmesi

Toplanan her olgu; kaynak kimliği ve adresi, bölge, çekim zamanı, geçerlilik tarihi/aralığı, özgün değer ve birim, ayrıştırıcı sürümü ve ham veri dosyasıyla ilişkilendirilecek. Konaklama fiyatlarında tarih, kişi sayısı, gece sayısı, para birimi ve dahil ücretler birlikte tutulacak; koşulları farklı fiyatlar doğrudan karşılaştırılmayacak. İşletmeler ve aynı işletmenin farklı kaynaklardaki kayıtları ayrı kimliklerle eşlenecek. Sayısal hesaplar Python fonksiyonlarında yapılacak; yapay zekâya hesap sonucu ve dayanak kayıtlar verilecek.

Ham veri, iş başına tarihli dosyalarda; sorgulanacak kayıtlar SQLite'ta tutulacak. Brief ve makaleler, kullandıkları veri sürümüne bağlanacak. Veri güncellendiğinde eski içerik kaybolmayacak; yenilenmesi gereken aşamalar işaretlenecek.

### Playwright ve Claude bağlantısı

Playwright, yalnızca ilgili kaynak gerektirdiğinde kullanılacak. Yeni uygulamanın kendine ait profili olacak; Housing Atlas profiline bağlanılmayacak. Kullanıcının açık Chrome'una bağlanma seçeneği ayrı ayar olarak değerlendirilecek. Bağlayıcılar hata, süre aşımı ve iptal sonucunu ortak iş sözleşmesine döndürecek.

Claude için görev başına ayrı çalışma alanı, izinli araç listesi, süre/tur sınırı, model ayarı ve yapılandırılmış çıktı denetimi planlanıyor. Kaynak metinleri görev talimatı değil, veri olarak işlenecek. Brief ve makale üretimi, kontrol edilmiş veri paketi üzerinden ilerleyecek; eksik bilgiler açıkça belirtilecek. Bu ilk sürüm Claude'u çağırmaz, mevcut hesabı veya ayarları okumaz.

## İlk aşamanın kapsamı

Çalışan özellikler: kaynak ekleme/düzenleme, kategori ve bölge seçimi, arama, filtre, ayrıntı paneli, arşivleme/geri alma, kayıt bilgilerinin yerel kontrolü, kalıcı iş sonucu ve günlük, on aşamalı gezinme, yerel başlatma.

Katalog kontrolü yalnızca yöntem ve açıklama alanlarındaki eksikleri listeler. Sitenin çalıştığını veya sayfadaki bilginin doğru olduğunu kanıtlamaz. Bağlı plaj toplayıcısının yöntemini tanır. Yöntem ve sıklık alanları bir zamanlayıcı çalıştırmaz.

Başlangıçtaki yedi kaynak, 29 Eylül 2026'da açılan sayfalara dayanarak eklenen adaylardır: [Visit South Walton](https://www.visitsouthwalton.com/), [restoranlar](https://www.visitsouthwalton.com/listings/culinary-experiences/), [plaj erişimleri](https://www.visitsouthwalton.com/beach-bay-access-locations/), [etkinlikler](https://www.visitsouthwalton.com/events/), [ulaşım](https://www.visitsouthwalton.com/listings/transportation/), [National Weather Service](https://www.weather.gov/) ve [30A](https://30a.com/). Bu katalog eksiksiz kaynak araştırması değildir. v0.2.0'da plaj erişimleri bağlandı; diğer altı adayın veri çekme yöntemi henüz sınanmadı.

## İkinci aşama: gerçek plaj verisi

South Walton sayfasının içindeki harita JSON nesneleri HTTP ile alınır; kaynak JavaScript'i çalıştırılmaz. Kayıt kimliği, zorunlu alanlar, koordinatlar ve türler topluca denetlenir. Bozuk veya boş yanıt başarılı sürümün yerini almaz. Her iş için kaynak sayfası, SHA-256 özeti, çekim zamanı, kaynak güncelleme metni, kapsam kuralı ve ayrıştırıcı sürümü saklanır. Kaynak zamanı metin olarak korunur; belirtilmeyen zaman dilimi tahmin edilmez.

SQLite şeması 1'den 2'ye yükseltilir; mevcut kaynak ve işler korunur. `collections` tablosu çekimleri, `beach_records` bunların kayıtlarını tutar. Kayıtlar ve işin başarılı bitişi tek işlemde kaydedilir; iptal önce gerçekleşirse sonuç yayımlanmaz. Ham dosyalar `data/raw/<iş-kimliği>/source.html` altında tutulur. Başarısız ayrıştırmanın ham yanıtı da teşhis için kalabilir.

Veri ekranı; arama, yerleşim/olanak filtreleri, ayrıntı, sürüm seçimi ve CSV indirme içerir. CSV UTF-8 BOM ve noktalı virgül kullanır; kaynak metnindeki formül başlangıçları etkisizleştirilir. Ham HTML, indirirken metin eki olarak sunulur. 30 Eylül 2026 ilk canlı işinde 70 noktadan 53 kıyı kaydı seçildi, 17 nokta kapsam dışında kaldı. Bu sayı kaynak güncellendiğinde değişebilir. [Kaynak kapsamı ve kontroller](M2-VERI-TOPLAMA.md).

İlk başlatıcı standart tarayıcı sekmesini kullanır. Housing Atlas'taki çerçevesiz pencere, görünmez başlatma, masaüstü kısayolu ve pencere kapanınca otomatik sunucu kapatma, sonraki paketleme aşamasında eklenebilir. Şimdilik sunucu başlatma penceresindeki Ctrl+C ile durdurulur. Adres yalnızca `127.0.0.1` üzerinde dinlenir; internete yayın yapılmaz.
