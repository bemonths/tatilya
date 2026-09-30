# 30A Studio

30A veri ve içerik üretim uygulaması · **v0.5.0**. Genel kaynak toplama altyapısı, plaj, NWS hava ve restoran toplayıcıları hazır. Housing Atlas'tan bağımsız bir projedir.

## Açılış

Bu klasördeki **baslat.bat** dosyasına çift tıklayın. İlk açılışta gerekli paketler kurulabilir. Uygulama tarayıcıda `http://127.0.0.1:8830` adresinde açılır. Başlatma penceresi açık kalmalıdır. Durdurmak için bu pencerede **Ctrl+C** kullanın.

## İlk deneme

1. Soldaki **Veri toplama** ekranını açın ve **Plaj verilerini topla** düğmesine basın.
2. Sağdaki **İşler** panelinden ilerlemeyi izleyin. İş bitince paneli kapatarak kayıtları inceleyin.
3. Ad veya adrese göre arayın; yerleşim ve olanak filtrelerini kullanın. Kayıt adına basınca ayrıntılar açılır.
4. **CSV indir** ile seçili sürümü dışa aktarın. **Ham kaynağı indir** ile çekilen sayfanın metnini alın.
5. Daha sonraki çekimler ayrı sürümler olarak saklanır. **Sürüm** listesinden önceki çekimlere dönün; seçili sürümün önceki başarılı çekime göre eklenen/kaldırılan/değişen/aynı kayıt sayılarını görün.
6. **Veri kaynakları** ekranında yeni kaynak ekleyin, düzenleyin veya arşivleyin. **Kayıtları kontrol et** yalnızca kaynak kayıtlarının hazırlık eksiklerini denetler.

Plaj veri toplama [South Walton plaj erişim sayfasına](https://www.visitsouthwalton.com/beach-bay-access-locations/) bağlıdır. Kaynaktaki Santa Rosa Beach, Grayton Beach, Seacrest ve Inlet Beach kıyı erişimleri seçilir; Miramar ve koy/göl noktaları dışarıda kalır. Bu seçim tüm 30A plajlarının eksiksiz listesi değildir. Olanakların kaynakta listelenmemesi, bulunmadıkları anlamına gelmez. Yerleşim adları kaynaktan aynen alınır.

Başlangıçtaki diğer dört kaynak adayının toplayıcısı, Claude, makale, görsel ve video üretimi henüz bağlı değildir. İleri aşamaların ekranları geliştirme planını gösterir. Kaynak formundaki sıklık alanı bir plandır; zamanlanmış otomatik toplama başlatmaz. Bu sürümde toplama elle başlatılır.

Kayıtlar bu projenin `data/` klasöründeki SQLite veritabanında, ham kaynaklar `data/raw/` altında kalır. Başarısız ve iptal edilmiş çekimler önceki başarılı sürümleri değiştirmez. Yedeklemek için uygulama kapalıyken `data/` klasörünün tamamını kopyalayın. Programın klasörünü başka yere taşırken `.venv` yeniden oluşturulmalıdır; kod ve `data/` korunmalıdır.

## Veri temeli ve yükseltme

Toplama işleri artık source_id ile izlenir; başarılı, başarısız ve iptal edilmiş çekimler genel source_runs yapısında saklanır. İşler panelinde kaynak adı görünür. Eski plaj ekranı, indirmeler ve veri sürümleri çalışmaya devam eder. Üç gerçek connector **BeachesConnector**, **WeatherConnector** ve **RestaurantsConnector** olarak kayıtlıdır; başka kaynak için yalnızca URL eklemek yeterli değildir.

v0.1/v0.2/v0.3/v0.4 veritabanı açılırken önce `data/backups/` içine SQLite yedeği alınır, ardından şema 5'e tek transaction ile yükseltilir. Kullanıcı kaynakları, geçmiş plaj sürümleri ve ham dosyalar korunur. Eski başarısız işlerde kaynak bilgisi yoksa tahmin edilmez. Yükseltmeden sonra eski uygulama sürümünü aynı veritabanına karşı çalıştırmayın; geri dönüş gerekiyorsa kapalı uygulamada yükseltme öncesi yedeğin ayrı kopyasını kullanın.

13 canonical bölge kimliği ve entities/entity_sources tabloları yalnızca temel seviyede hazırdır. Otomatik entity matching, region polygon mapping ve mahalle tahmini yoktur. Claude/OpenAI, Playwright, scheduler ve içerik üretimi henüz uygulanmadı.

## Belgeler

- [Uygulamanın çalışma mantığı](CALISMA_MANTIGI.md)
- [Housing Atlas incelemesi ve 30A mimarisi](docs/MIMARI.md)
- [Kademeli geliştirme planı](docs/ASAMALAR.md)
- [Plaj veri kaynağının kapsamı ve kontrolleri](docs/M2-VERI-TOPLAMA.md)
- [Hava verisi](docs/M3-HAVA-VERISI.md)
- [Restoran dizini ve kapsamı](docs/M4-RESTORAN-VERISI.md)

## Geliştirme

Python 3.12 veya sonrası gerekir. Yeni sanal ortamda `python -m pip install -e ".[test]"` ile kurulur. Testler `python -m pytest -q` ile, uygulama `python -m studio` ile çalışır. Tarayıcı açmadan çalıştırmak için `python -m studio --no-browser`; ayrı deneme verileri için `--data-dir` kullanın. Testler canlı ağ veya Claude çağrısı yapmaz.

GitHub Actions, Python 3.12 üzerinde editable test kurulumu ve pytest çalıştırır: [iş akışları](https://github.com/bemonths/tatilya/actions). Testler gerçek HTTP bağlantısını engeller.

### Korunan veri davranışı

Kaynak kütüphanesi registry'den gelen her connector için **Toplayıcı hazır** durumunu, adını ve sürümünü gösterir. Arşivdeki kaynaklar arşiv durumunu korur. Genel toplama işlerinde plaj ekranına bağlantı yalnızca plaj connector sonucunda gösterilir.

Plaj sürüm karşılaştırması aynı kaynak ve connector için devam eder; connector sürümü değişmişse ayrıştırma değişikliğinin farkları etkileyebileceği uyarısı görünür. Eski v0.2 çekimleriyle karşılaştırma korunur.

Ham SHA-256 için tek kaynak, `Database.record_raw_artifact()` tarafından diskteki gerçek dosyadan hesaplanan değerdir; `CollectionResult` hash taşımaz. Visit South Walton yönlendirmeleri yalnızca `visitsouthwalton.com` ve `www.visitsouthwalton.com` arasında, HTTPS ve varsayılan/443 port ile izlenir; en fazla üç yönlendirme kabul edilir.

Beklenmeyen hataların teknik mesajları yaygın parola/token/API anahtarı ve URL kimlik bilgileri gizlendikten sonra 500 karakterle sınırlanarak yalnızca dahili veritabanı diagnostic alanında tutulur. Normal API/SSE yanıtlarında yayımlanmaz.

## NWS hava verisi · v0.4

**Veri toplama → Hava → Hava verilerini topla** ile üç örnek noktanın güncel NWS tahminlerini ve aktif uyarılarını ayrı bir çekim olarak saklayın. Kaynak kütüphanesinde National Weather Service **API · bağlı / Toplayıcı hazır** görünür. Veri toplama içindeki Plaj/Hava/Restoranlar sekmeleri ve İşler panelindeki sonuç bağlantıları ilgili domain'i açar.

Batı / Orta / Doğu seçimi, Visit South Walton kaynağındaki 53 kıyı erişiminin boylam sıralamasına dayanır. Noktalar canonical mahalle merkezleri değildir. Tam koordinat/provenance ve NWS akışı: [Hava verisi sözleşmesi](docs/M3-HAVA-VERISI.md).

API'nin verdiği bütün dönem ve saatlik tahminler saklanır; ekranda saatlik kayıtların ilk 24'ü gösterilir. Tahmin saatleri `/points` yanıtındaki saat dilimine göre, çekim zamanları açıkça UTC ile gösterilir. Sürüm seçiciden eski çekimler incelenebilir. NWS'nin null alanları sıfıra çevrilmez. Aynı uyarı birden çok noktayı etkiliyorsa tek uyarı ve nokta ilişkileri saklanır. “Aktif uyarı yok” seçili çekimin durumudur; canlı güvenlik bildirimi değildir.

Hava kayan/geçici bir tahmin penceresidir; eklenen/silinen kayıt farkı gösterilmez. Ham yanıt paketi indirilebilir. Tarihsel iklim, observation station/current conditions, scheduler, Claude/OpenAI yoktur. API key gerekmez; veriler NWS'nin kendi tahminleridir.

Ön yüz yardımcı testleri: Node 22+ ile `node --test tests/frontend.test.mjs`. Node yalnızca test aracıdır; uygulamanın çalışması/kurulumu için gerekmez.

![NWS hava ekranı](docs/HAVA-ONIZLEME.png)

Varsayılan kaynak düzeltmesi: temiz kurulumda NWS yöntemi API, South Walton plaj yöntemi JSON olarak seed tanımından alınır. v3→v4 migration yalnızca tam kaynak URL'si eşleşen ve yöntemi hâlâ `Belirlenecek` olan bu iki kaydı günceller. NWS notu yalnızca eski varsayılan açıklamayla birebir aynıysa yeni tahmin/uyarı açıklamasına çevrilir. Not ve yöntem koşulları bağımsızdır; kullanıcı notu veya seçtiği yöntem korunur. Diğer kaynak alanları ve source_history değiştirilmez. Yükseltme öncesi yedek eski değerleri içerir. Zaten şema v4 olan veritabanlarında bu migration yeniden çalıştırılmaz.

## Restoran dizini · v0.5

**Veri toplama → Restoranlar → Restoran verilerini topla** ile Visit South Walton HTML dizini ve detay sayfaları okunur. 13 canonical mahalle, yalnızca **Restaurants** işletme türüyle taranır; Miramar Beach, Seascape ve Sandestin kapsam dışıdır. Filtre seçenekleri ana sayfadan keşfedilir. Her mahallenin bütün sayfaları taranır, detay URL'leri tekilleştirilir ve birden fazla mahallede bulunan kayıtların bütün ilişkileri korunur.

Ad, açıklama, adres, iletişim, işletme sitesi bağlantısı, cuisine, meals served ve diğer amenities saklanır. Metin, mahalle, mutfak türü ve öğün filtreleri; ayrıntı paneli, eski sürüm seçimi ve önceki başarılı sürüme göre fark sayıları kullanılabilir. Ham indirme, response dosyalarının yollarını ve hash'lerini içeren manifesttir. Kaynak güncelleme zamanı bulunmadığından `source_updated` null kalır.

Menü/fiyat, ratings/reviews, restoranın kendi sitesini tarama, scheduler ve AI yoktur. Üç bağlantının yöntemleri: Beaches = HTML içi JSON, Weather = NWS API, Restaurants = HTML dizin/detay. v4→v5 yalnızca yeni restoran tablolarını ekler; eski kaynak URL'si tam eşleştiğinde, yöntem hâlâ Belirlenecek ise HTML yapılır ve yalnızca eski varsayılan not güncellenir. Kullanıcı düzenlemeleri korunur. Ayrıntılar: [M4 restoran veri sözleşmesi](docs/M4-RESTORAN-VERISI.md).
Canlı kaynak sınırı (30 Eylül 2026): 138 benzersiz restoranın ikisinde zorunlu açıklama yok. Mevcut sözleşme nedeniyle tam çekim güvenli biçimde başarısız olur ve kısmi veri yayımlanmaz. Ayrıntı ve mahalle sayıları [M4 canlı inceleme notunda](docs/M4-RESTORAN-VERISI.md). Açıklamayı nullable kabul etme tercihi henüz uygulanmadı.
