# 30A Studio

30A veri ve içerik üretim uygulaması · **v0.3.0**. Genel kaynak toplama altyapısı, plaj veri toplayıcısı ve sürüm farkı hazır. Housing Atlas'tan bağımsız bir projedir.

## Açılış

Bu klasördeki **baslat.bat** dosyasına çift tıklayın. İlk açılışta gerekli paketler kurulabilir. Uygulama tarayıcıda `http://127.0.0.1:8830` adresinde açılır. Başlatma penceresi açık kalmalıdır. Durdurmak için bu pencerede **Ctrl+C** kullanın.

## İlk deneme

1. Soldaki **Veri toplama** ekranını açın ve **Plaj verilerini topla** düğmesine basın.
2. Sağdaki **İşler** panelinden ilerlemeyi izleyin. İş bitince paneli kapatarak kayıtları inceleyin.
3. Ad veya adrese göre arayın; yerleşim ve olanak filtrelerini kullanın. Kayıt adına basınca ayrıntılar açılır.
4. **CSV indir** ile seçili sürümü dışa aktarın. **Ham kaynağı indir** ile çekilen sayfanın metnini alın.
5. Daha sonraki çekimler ayrı sürümler olarak saklanır. **Sürüm** listesinden önceki çekimlere dönün; seçili sürümün önceki başarılı çekime göre eklenen/kaldırılan/değişen/aynı kayıt sayılarını görün.
6. **Veri kaynakları** ekranında yeni kaynak ekleyin, düzenleyin veya arşivleyin. **Kayıtları kontrol et** yalnızca kaynak kayıtlarının hazırlık eksiklerini denetler.

Canlı veri toplama şu an yalnızca [South Walton plaj erişim sayfasına](https://www.visitsouthwalton.com/beach-bay-access-locations/) bağlıdır. Kaynaktaki Santa Rosa Beach, Grayton Beach, Seacrest ve Inlet Beach kıyı erişimleri seçilir; Miramar ve koy/göl noktaları dışarıda kalır. Bu seçim tüm 30A plajlarının eksiksiz listesi değildir. Olanakların kaynakta listelenmemesi, bulunmadıkları anlamına gelmez. Yerleşim adları kaynaktan aynen alınır.

Başlangıçtaki diğer altı kaynak adayının toplayıcısı, Claude, makale, görsel ve video üretimi henüz bağlı değildir. İleri aşamaların ekranları geliştirme planını gösterir. Kaynak formundaki sıklık alanı bir plandır; zamanlanmış otomatik toplama başlatmaz. Bu sürümde toplama elle başlatılır.

Kayıtlar bu projenin `data/` klasöründeki SQLite veritabanında, ham kaynaklar `data/raw/` altında kalır. Başarısız ve iptal edilmiş çekimler önceki başarılı sürümleri değiştirmez. Yedeklemek için uygulama kapalıyken `data/` klasörünün tamamını kopyalayın. Programın klasörünü başka yere taşırken `.venv` yeniden oluşturulmalıdır; kod ve `data/` korunmalıdır.

## v0.3 veri temeli

Toplama işleri artık source_id ile izlenir; başarılı, başarısız ve iptal edilmiş çekimler genel source_runs yapısında saklanır. İşler panelinde kaynak adı görünür. Eski plaj ekranı, indirmeler ve veri sürümleri çalışmaya devam eder. Tek gerçek connector **BeachesConnector**'tır; başka kaynak için yalnızca URL eklemek yeterli değildir.

v0.1/v0.2 veritabanı açılırken önce `data/backups/` içine SQLite yedeği alınır, ardından şema 3'e tek transaction ile yükseltilir. Kullanıcı kaynakları, geçmiş plaj sürümleri ve ham dosyalar korunur. Eski başarısız işlerde kaynak bilgisi yoksa tahmin edilmez. Yükseltmeden sonra eski uygulama sürümünü aynı veritabanına karşı çalıştırmayın; geri dönüş gerekiyorsa kapalı uygulamada yükseltme öncesi yedeğin ayrı kopyasını kullanın.

13 canonical bölge kimliği ve entities/entity_sources tabloları yalnızca temel seviyede hazırdır. Otomatik entity matching, region polygon mapping ve mahalle tahmini yoktur. Claude/OpenAI, Playwright, scheduler ve içerik üretimi henüz uygulanmadı.

## Belgeler

- [Uygulamanın çalışma mantığı](CALISMA_MANTIGI.md)
- [Housing Atlas incelemesi ve 30A mimarisi](docs/MIMARI.md)
- [Kademeli geliştirme planı](docs/ASAMALAR.md)
- [Plaj veri kaynağının kapsamı ve kontrolleri](docs/M2-VERI-TOPLAMA.md)

## Geliştirme

Python 3.12 veya sonrası gerekir. Yeni sanal ortamda `python -m pip install -e ".[test]"` ile kurulur. Testler `python -m pytest -q` ile, uygulama `python -m studio` ile çalışır. Tarayıcı açmadan çalıştırmak için `python -m studio --no-browser`; ayrı deneme verileri için `--data-dir` kullanın. Testler canlı ağ veya Claude çağrısı yapmaz.

GitHub Actions, Python 3.12 üzerinde editable test kurulumu ve pytest çalıştırır: [iş akışları](https://github.com/bemonths/tatilya/actions). Testler gerçek HTTP bağlantısını engeller.
