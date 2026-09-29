# 30A Studio

30A veri ve içerik üretim uygulaması · **v0.2.0**. Kaynak kütüphanesi ve ilk gerçek veri toplayıcısı hazır. Housing Atlas'tan bağımsız bir projedir.

## Açılış

Bu klasördeki **baslat.bat** dosyasına çift tıklayın. İlk açılışta gerekli paketler kurulabilir. Uygulama tarayıcıda `http://127.0.0.1:8830` adresinde açılır. Başlatma penceresi açık kalmalıdır. Durdurmak için bu pencerede **Ctrl+C** kullanın.

## İlk deneme

1. Soldaki **Veri toplama** ekranını açın ve **Plaj verilerini topla** düğmesine basın.
2. Sağdaki **İşler** panelinden ilerlemeyi izleyin. İş bitince paneli kapatarak kayıtları inceleyin.
3. Ad veya adrese göre arayın; yerleşim ve olanak filtrelerini kullanın. Kayıt adına basınca ayrıntılar açılır.
4. **CSV indir** ile seçili sürümü dışa aktarın. **Ham kaynağı indir** ile çekilen sayfanın metnini alın.
5. Daha sonraki çekimler ayrı sürümler olarak saklanır. **Sürüm** listesinden önceki çekimlere dönün.
6. **Veri kaynakları** ekranında yeni kaynak ekleyin, düzenleyin veya arşivleyin. **Kayıtları kontrol et** yalnızca kaynak kayıtlarının hazırlık eksiklerini denetler.

Canlı veri toplama şu an yalnızca [South Walton plaj erişim sayfasına](https://www.visitsouthwalton.com/beach-bay-access-locations/) bağlıdır. Kaynaktaki Santa Rosa Beach, Grayton Beach, Seacrest ve Inlet Beach kıyı erişimleri seçilir; Miramar ve koy/göl noktaları dışarıda kalır. Bu seçim tüm 30A plajlarının eksiksiz listesi değildir. Olanakların kaynakta listelenmemesi, bulunmadıkları anlamına gelmez. Yerleşim adları kaynaktan aynen alınır.

Başlangıçtaki diğer altı kaynak adayının toplayıcısı, Claude, makale, görsel ve video üretimi henüz bağlı değildir. İleri aşamaların ekranları geliştirme planını gösterir. Kaynak formundaki sıklık alanı bir plandır; zamanlanmış otomatik toplama başlatmaz. Bu sürümde toplama elle başlatılır.

Kayıtlar bu projenin `data/` klasöründeki SQLite veritabanında, ham kaynaklar `data/raw/` altında kalır. Başarısız ve iptal edilmiş çekimler önceki başarılı sürümleri değiştirmez. Yedeklemek için uygulama kapalıyken `data/` klasörünün tamamını kopyalayın. Programın klasörünü başka yere taşırken `.venv` yeniden oluşturulmalıdır; kod ve `data/` korunmalıdır.

## Belgeler

- [Uygulamanın çalışma mantığı](CALISMA_MANTIGI.md)
- [Housing Atlas incelemesi ve 30A mimarisi](docs/MIMARI.md)
- [Kademeli geliştirme planı](docs/ASAMALAR.md)
- [Plaj veri kaynağının kapsamı ve kontrolleri](docs/M2-VERI-TOPLAMA.md)

## Geliştirme

Python 3.12 veya sonrası gerekir. Yeni sanal ortamda `python -m pip install -e ".[test]"` ile kurulur. Testler `python -m pytest -q` ile, uygulama `python -m studio` ile çalışır. Tarayıcı açmadan çalıştırmak için `python -m studio --no-browser`; ayrı deneme verileri için `--data-dir` kullanın. Testler canlı ağ veya Claude çağrısı yapmaz.
