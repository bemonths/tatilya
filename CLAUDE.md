# 30A Studio — Claude Code çalışma notları

Bu repo 30A Studio'dur: 30A / South Walton (Florida) için resmî kaynaklardan veri toplayıp her çekimi ham kanıtıyla ve geçmişiyle saklayan yerel bir FastAPI + SQLite uygulaması. Veri, ileride İngilizce YouTube rehber videolarına kanıt katmanı olacak; veritabanı kanıtı verir, yorum ve tavsiye editoryal katmanındır. 30A ilk destinasyondur, motor çok-destinasyonlu tasarlanmıştır.

Bir göreve başlamadan önce sırayla `CALISMA_MANTIGI.md` (ana devir belgesi), `docs/KONSEPT.md` (içerik yönünde bağlayıcı belge), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md` ve görevin ilgili olduğu `docs/Mx` belgesini oku. v0.6'nın ayrıntılı teknik anlatımı `docs/TEKNIK-CALISMA-MANTIGI-v0.6.md` içindedir. Kod ile belge çelişirse gerçek kodu ve veritabanı davranışını doğrula, belgeyi aynı görevde düzelt.

## Çalışma düzeni

Görevleri proje yöneticisi ayrı bir Claude sohbetinde `GÖREV-NN` numarasıyla yazar, kullanıcı buraya getirir. Her görev kendi dalında yapılır ve o dala push edilir. Teknik kararları ve main'e alma kararını proje yöneticisi verir; Claude Code main'e merge, main'e push ve tag işlemlerini yalnız görev metni bunu açıkça istediğinde yapar. Kullanıcı makale (video metni) aşamasına kadar karar vermez; ondan onay veya manuel test istenmez, gerçek ortamda gereken arayüz ve canlı kontrolleri Claude Code kendisi yapar (gerekirse ekran görüntüsüyle). Yönetici sonucu GitHub'daki daldan okur; bu yüzden her görevin sonunda görev metni (`GOREV.md`), rapor (`RAPOR.md`) ve istenen çıktılar `docs/gorevler/GOREV-NN/` klasörüne yazılıp aynı dala push edilir. Kullanıcı İngilizce bilmez ve kod okumaz; rapor ve kullanıcıya yazılan son mesaj Türkçe ve sadedir, teknik ayrıntı rapora girer.

`work/` yerel çalışma alanıdır ve `.gitignore` ile repoya gitmez. Kullanıcının getirdiği görev dosyaları, veritabanı kopyaları, geçici veri klasörleri ve yardımcı betikler orada kalır. Commit'ten önce `git status` ile bunların sahneye girmediğini kontrol et.

## Veri güvenliği

`data/` gerçek kullanıcı verisidir (veritabanı, ham çekimler, yedekler): içinde dosya değiştirilmez, silinmez, taşınmaz ve gerçek veritabanı uygulamayla deneme için açılmaz. İncelemek gerekirse uygulama kapalıyken dosyayı salt okunur açıp SQLite backup API ile `work/` altına kopyala ve kopyayı oku. Veritabanı WAL kipinde olduğundan `file:...?mode=ro&immutable=1` kullan; yalnız `mode=ro` ile açmak `data/` içinde -wal/-shm dosyası oluşturabilir. Şema değişikliğinden önce yedek alınır, migration önce kopyada denenir, satır sayıları ve `foreign_key_check` karşılaştırılır. Canlı denemeler `python -m studio --data-dir work\<görev>\temp-data --no-browser --port <boş port>` ile geçici klasörde yapılır.

Gerçek veriyi güncelleme kuralı: Kullanıcı uygulamayı kendisi kullanmaz. Gerçek veritabanı yalnız görev metni açıkça istediğinde ve yalnız uygulamanın normal kullanımıyla (uygulamayı gerçek veri klasörüyle açmak, arayüz veya API üzerinden toplayıcı çalıştırmak) değişir. Bundan önce uygulama kapalıyken `data/` klasörünün tamamı `work/yedek/<YYYYMMDD-HHMM>/` altına kopyalanır. `data/` içindeki dosyalar elle değiştirilmez, silinmez, taşınmaz.

## Test

İki komut çalıştırılır: `.venv\Scripts\python.exe -m pytest -q` ve `node --test tests/frontend.test.mjs`. Testler canlı ağa bağlanmaz; `tests/conftest.py` gerçek HTTP'yi engeller, fixture ve `httpx.MockTransport` kullanılır. Canlı çekimden gelen sayılar (53 plaj, 138 restoran gibi) test sabiti veya kabul ölçütü yapılmaz, çünkü kaynak değişebilir.

## Bilgi toplama

Amaç, ziyaretçinin karar vermesi için gereken bilgiyi eksiksiz toplamaktır. Herkese açık yayımlanmış her bilgi alınabilir: resmî siteler, işletmelerin kendi siteleri, menüler, PDF'ler, harita ve veri servisleri. Gerekirse gerçek tarayıcıyla (Playwright ve bilgisayardaki Chrome veya Edge) okunur; robots.txt ve bot doğrulaması tek başına engel sayılmaz. İstekler siteyi yormayacak hızda yapılır; her bilginin kaynağı, erişim tarihi ve ham kopyası saklanır. Giriş gerektiren hesaplara girilmez, ücretli içerik aşılmaz. Doğruluk kuralları aynen geçerlidir: kaynağın söylemediği şey yazılmaz, hesaplanan ya da türetilen değer öyle etiketlenir.

Tarayıcı ve insan doğrulaması: bir site "insan olduğunuzu doğrulayın", Cloudflare kontrolü veya CAPTCHA gösterirse Claude Code sayfayı bilgisayardaki Chrome veya Edge ile, kalıcı bir tarayıcı profiliyle (`work/tarayici-profili/`, repoya girmez) ve görünür pencerede açar, kullanıcıya hangi sitede doğrulama beklendiğini söyler ve bekler. Doğrulamayı kullanıcı yapar; Claude Code çözmeye çalışmaz ve tarayıcıyı gizleyen ayar kullanmaz. Kullanıcı tamamlayınca aynı profil ve oturumla devam edilir. Uygulama içi tarayıcı bir site için izin isterse kullanıcıdan onay istenir. (8 Ekim 2026, GÖREV-08.) Ayrıntı: `CALISMA_MANTIGI.md` §4 madde 12–14.

## Veri dili

Kaynağın söylemediği şey yazılmaz. Eksik alan NULL kalır; kaynakta listelenmemiş bir olanak "yok" anlamına gelmez; `fetched_at` kaynağın güncellenme zamanı değildir; adres veya koordinattan sessizce mahalle çıkarılmaz. Tarihli ya da aramaya bağlı bir sonuç (Book>Direct tarihli araması gibi) "tam liste" veya "tam envanter" diye adlandırılmaz. Bu katılık veri ve rapor dili içindir; video dili daha doğal olabilir ama kanıtın taşıdığından ileri gidemez.

## Mimari sınır

Generic çekirdek (kaynak → job → source_run → ham dosya → atomik yazım akışı, `jobs.py`, `database.py`, NWS connector'ı ve iklim connector'ları `ncei-climate-normals`, `ndbc-water-temperature`, `hurdat2-storm-proximity`; konaklama connector'ı `bookdirect-lodging`) destinasyondan bağımsızdır; iklim istasyonları, kıyı koridoru, yarıçaplar, Book>Direct clone adresi, konum filtresi eşlemesi ve konaklama tarih pencereleri SQLite'taki destinasyon yapılandırmasından gelir. 30A'ya özel davranış `studio/destinations/thirty_a.py` profilinde (ve yanındaki profil dosyalarında, ör. plaj–mahalle eşlemesi) veya 30A'ya bağlı connector'larda (`south-walton-beaches`, `south-walton-restaurants`, `south-walton-neighborhoods`) kalır; generic çekirdeğe gömülmez. Yeni bir davranış eklerken önce "bu generic mi, yoksa destinasyona özel mi?" diye sor.

## Ortam

Bu bilgisayarda Windows kod sayfası 936'dır. Python'u `.venv` içinden ve `-X utf8` ile çalıştır (`baslat.bat` da böyle yapar); aksi halde çıktı dosyaya yönlendirildiğinde Türkçe karakterler `UnicodeEncodeError` verir ve uygulama açılışta kapanır.
