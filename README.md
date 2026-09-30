# 30A Studio

30A veri ve içerik üretim uygulaması · **v0.4.0**. Genel kaynak toplama altyapısı, plaj ve NWS hava toplayıcıları hazır. Housing Atlas'tan bağımsız bir projedir.

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

Başlangıçtaki diğer beş kaynak adayının toplayıcısı, Claude, makale, görsel ve video üretimi henüz bağlı değildir. İleri aşamaların ekranları geliştirme planını gösterir. Kaynak formundaki sıklık alanı bir plandır; zamanlanmış otomatik toplama başlatmaz. Bu sürümde toplama elle başlatılır.

Kayıtlar bu projenin `data/` klasöründeki SQLite veritabanında, ham kaynaklar `data/raw/` altında kalır. Başarısız ve iptal edilmiş çekimler önceki başarılı sürümleri değiştirmez. Yedeklemek için uygulama kapalıyken `data/` klasörünün tamamını kopyalayın. Programın klasörünü başka yere taşırken `.venv` yeniden oluşturulmalıdır; kod ve `data/` korunmalıdır.

## Veri temeli ve yükseltme

Toplama işleri artık source_id ile izlenir; başarılı, başarısız ve iptal edilmiş çekimler genel source_runs yapısında saklanır. İşler panelinde kaynak adı görünür. Eski plaj ekranı, indirmeler ve veri sürümleri çalışmaya devam eder. İki gerçek connector **BeachesConnector** ve **WeatherConnector**'dır; başka kaynak için yalnızca URL eklemek yeterli değildir.

v0.1/v0.2/v0.3 veritabanı açılırken önce `data/backups/` içine SQLite yedeği alınır, ardından şema 4'e tek transaction ile yükseltilir. Kullanıcı kaynakları, geçmiş plaj sürümleri ve ham dosyalar korunur. Eski başarısız işlerde kaynak bilgisi yoksa tahmin edilmez. Yükseltmeden sonra eski uygulama sürümünü aynı veritabanına karşı çalıştırmayın; geri dönüş gerekiyorsa kapalı uygulamada yükseltme öncesi yedeğin ayrı kopyasını kullanın.

13 canonical bölge kimliği ve entities/entity_sources tabloları yalnızca temel seviyede hazırdır. Otomatik entity matching, region polygon mapping ve mahalle tahmini yoktur. Claude/OpenAI, Playwright, scheduler ve içerik üretimi henüz uygulanmadı.

## Belgeler

- [Uygulamanın çalışma mantığı](CALISMA_MANTIGI.md)
- [Housing Atlas incelemesi ve 30A mimarisi](docs/MIMARI.md)
- [Kademeli geliştirme planı](docs/ASAMALAR.md)
- [Plaj veri kaynağının kapsamı ve kontrolleri](docs/M2-VERI-TOPLAMA.md)

## Geliştirme

Python 3.12 veya sonrası gerekir. Yeni sanal ortamda `python -m pip install -e ".[test]"` ile kurulur. Testler `python -m pytest -q` ile, uygulama `python -m studio` ile çalışır. Tarayıcı açmadan çalıştırmak için `python -m studio --no-browser`; ayrı deneme verileri için `--data-dir` kullanın. Testler canlı ağ veya Claude çağrısı yapmaz.

GitHub Actions, Python 3.12 üzerinde editable test kurulumu ve pytest çalıştırır: [iş akışları](https://github.com/bemonths/tatilya/actions). Testler gerçek HTTP bağlantısını engeller.

### Korunan veri davranışı

Kaynak kütüphanesi registry'den gelen her connector için **Toplayıcı hazır** durumunu, adını ve sürümünü gösterir. Arşivdeki kaynaklar arşiv durumunu korur. Genel toplama işlerinde plaj ekranına bağlantı yalnızca plaj connector sonucunda gösterilir.

Plaj sürüm karşılaştırması aynı kaynak ve connector için devam eder; connector sürümü değişmişse ayrıştırma değişikliğinin farkları etkileyebileceği uyarısı görünür. Eski v0.2 çekimleriyle karşılaştırma korunur.

Ham SHA-256 için tek kaynak, `Database.record_raw_artifact()` tarafından diskteki gerçek dosyadan hesaplanan değerdir; `CollectionResult` hash taşımaz. Visit South Walton yönlendirmeleri yalnızca `visitsouthwalton.com` ve `www.visitsouthwalton.com` arasında, HTTPS ve varsayılan/443 port ile izlenir; en fazla üç yönlendirme kabul edilir.

Beklenmeyen hataların teknik mesajları yaygın parola/token/API anahtarı ve URL kimlik bilgileri gizlendikten sonra 500 karakterle sınırlanarak yalnızca dahili veritabanı diagnostic alanında tutulur. Normal API/SSE yanıtlarında yayımlanmaz.

## NWS hava verisi · v0.4

**Veri toplama → Hava → Hava verilerini topla** ile üç örnek noktanın güncel NWS tahminlerini ve aktif uyarılarını ayrı bir çekim olarak saklayın. Kaynak kütüphanesinde National Weather Service **API · bağlı / Toplayıcı hazır** görünür. Veri toplama içindeki Plaj/Hava sekmeleri ve İşler panelindeki sonuç bağlantıları ilgili domain'i açar.

Batı / Orta / Doğu seçimi, Visit South Walton kaynağındaki 53 kıyı erişiminin boylam sıralamasına dayanır. Noktalar canonical mahalle merkezleri değildir. Tam koordinat/provenance ve NWS akışı: [Hava verisi sözleşmesi](docs/M3-HAVA-VERISI.md).

API'nin verdiği bütün dönem ve saatlik tahminler saklanır; ekranda saatlik kayıtların ilk 24'ü gösterilir. Tahmin saatleri `/points` yanıtındaki saat dilimine göre, çekim zamanları açıkça UTC ile gösterilir. Sürüm seçiciden eski çekimler incelenebilir. NWS'nin null alanları sıfıra çevrilmez. Aynı uyarı birden çok noktayı etkiliyorsa tek uyarı ve nokta ilişkileri saklanır. “Aktif uyarı yok” seçili çekimin durumudur; canlı güvenlik bildirimi değildir.

Hava kayan/geçici bir tahmin penceresidir; eklenen/silinen kayıt farkı gösterilmez. Ham yanıt paketi indirilebilir. Tarihsel iklim, observation station/current conditions, scheduler, Claude/OpenAI ve başka yeni connector yoktur. API key gerekmez; veriler NWS'nin kendi tahminleridir.

Ön yüz yardımcı testleri: Node 22+ ile `node --test tests/frontend.test.mjs`. Node yalnızca test aracıdır; uygulamanın çalışması/kurulumu için gerekmez.

![NWS hava ekranı](docs/HAVA-ONIZLEME.png)

Varsayılan kaynak düzeltmesi: temiz kurulumda NWS yöntemi API, South Walton plaj yöntemi JSON olarak seed tanımından alınır. v3→v4 migration yalnızca tam kaynak URL'si eşleşen ve yöntemi hâlâ `Belirlenecek` olan bu iki kaydı günceller. NWS notu yalnızca eski varsayılan açıklamayla birebir aynıysa yeni tahmin/uyarı açıklamasına çevrilir. Not ve yöntem koşulları bağımsızdır; kullanıcı notu veya seçtiği yöntem korunur. Diğer kaynak alanları ve source_history değiştirilmez. Yükseltme öncesi yedek eski değerleri içerir. Zaten şema v4 olan veritabanlarında bu migration yeniden çalıştırılmaz.
