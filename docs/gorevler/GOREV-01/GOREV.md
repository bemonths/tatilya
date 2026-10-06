GÖREV-01 — Devir alma, zemin kontrolü ve belge düzeni

BAĞLAM
Bu repo (bemonths/tatilya) 30A Studio'dur. 30A / South Walton (Florida) için resmî kaynaklardan veri toplayan ve ileride İngilizce YouTube rehber videolarına kanıt sağlayacak yerel bir FastAPI + SQLite uygulamasıdır. Proje daha önce başka bir yapay zekâ ile geliştirildi, şimdi sana devrediliyor.

Yeni çalışma düzeni şöyle: proje yöneticisi ayrı bir Claude sohbetinde görevleri yazar, kullanıcı görevi sana getirir, sen uygularsın, kullanıcı senin raporunu yöneticiye taşır. Yönetici commit'lerini GitHub'dan kendisi çekip inceler. Kullanıcı İngilizce bilmez ve kodu okumaz; raporlarını Türkçe ve sade yaz.

Bu görevde uygulama kodu ve veritabanı şeması değişmeyecek. Amaç üç şey: yerel ortamın ve gerçek verinin bugünkü durumunu tespit etmek, veri kaynaklarının bugün hâlâ çalıştığını geçici bir veri klasöründe denemek, devir belgelerini ve senin kalıcı çalışma kurallarını (CLAUDE.md) repoya yerleştirmek.

ÖNCE OKU
Kullanıcı devir paketini work/devir-paketi/ klasörüne koydu. Sırayla oku:
1. work/devir-paketi/CALISMA_MANTIGI.md (ana devir belgesi)
2. work/devir-paketi/KONSEPT.md (kanalın içerik konsepti; içerik yönü konusunda en güncel ve bağlayıcı belge budur)
3. work/devir-paketi/DEVIR/ altındaki 01–07 belgeleri
4. Repodaki mevcut CALISMA_MANTIGI.md, README.md, docs/ altındaki belgeler ve studio/ kodu

KESİN SINIRLAR
- data/ klasöründeki hiçbir dosyayı değiştirme, silme veya taşıma. Gerçek veritabanını (data/studio.sqlite3) uygulamayla açma; yalnız Adım 3'te anlatıldığı gibi salt okunur kopyala.
- main dalına commit, merge veya push yapma. Tag oluşturma veya taşıma.
- studio/ altındaki uygulama kodunu, testleri ve şemayı değiştirme.

ADIM 1 — Ortam ve repo durumu
Şunları tespit et: Windows'taki Python sürümleri (py -0p), .venv içindeki Python sürümü, Node sürümü, git status (kaydedilmemiş değişiklikler ve izlenmeyen dosyalar dahil), aktif dal ve HEAD, git fetch sonrası her yerel dalın origin ile farkı, yerel tag'ler. "dubious ownership" hatası çıkarsa CALISMA_MANTIGI.md'deki safe.directory çözümünü uygula ve bunu rapora yaz. Önceki konaklama keşfinden kalan work/lodging-discovery/ ve work/lodging-phase2/ klasörlerini repo klasöründe ve bir üst klasörde (outputs) ara; bulursan yerini ve dosya listesini yaz, içeriklerini taşıma.

ADIM 2 — Testler
.venv Python'u ile "python -m pytest -q" ve "node --test tests/frontend.test.mjs" çalıştır. Beklenen taban 289 Python + 19 arayüz testidir. Sonucu ve uyarıları yaz.

ADIM 3 — Gerçek veritabanının durumu (yalnız kopya üzerinden)
Uygulamanın kapalı olduğundan emin ol. data/studio.sqlite3 dosyasını salt okunur (file:...?mode=ro) açıp SQLite backup API ile work/gorev-01/db-kopya.sqlite3 olarak kopyala. Kopyayı uygulamayla açma; yalnız sqlite3 ile oku. Kopyadan şunları rapora yaz: PRAGMA user_version, her tablonun satır sayısı, destinations kayıtları, sources listesi (ad, URL, yöntem, enabled), source_runs listesi (connector, durum, başlangıç tarihi, kayıt sayısı) ve her connector'ın son başarılı çekim tarihi.

ADIM 4 — Canlı kontrol, geçici veri klasöründe
Gerçek veritabanına dokunmadan, work/gorev-01/temp-data/ klasörünü veri alanı yaparak uygulamayı başlat:
python -m studio --data-dir work\gorev-01\temp-data --no-browser --port 8831
API üzerinden (POST /api/jobs, gövde {"kind":"source_collection","source_id":...}, başlık X-Studio-Request: 1) şu üç kaynağı sırayla topla: "South Walton · Plaj erişimleri", "National Weather Service", "South Walton · Restoranlar". Her biri için durumu, kayıt sayısını, kapsam dışı sayısını, süreyi ve hata varsa mesajını yaz. Bir toplayıcı hata verirse kodu düzeltmeye çalışma; ham dosyadan ve jobs.diagnostic alanından anlayabildiğin nedeni rapora yaz. İş bitince uygulamayı kapat.

ADIM 5 — Veri dökümü (Adım 4'teki geçici çekimden)
docs/gorevler/GOREV-01/ altına UTF-8 CSV dosyaları yaz. Bu klasör repoya gidecek; yönetici dosyaları oradan okuyacak. Kod değiştirmeden, gerekirse work/gorev-01/ altında küçük bir betik kullan (betik repoya gitmez).
- plajlar.csv: kaydedilen her plaj erişimi için external_id, ad, kaynaktaki yerleşim adı (city), adres, enlem, boylam, erişim türü, olanaklar ("|" ile ayrılmış).
- plajlar-kapsam-disi.csv: aynı çekimin ham HTML'inde bulunup kapsam dışı kalan noktalar için external_id, ad, city, tür, enlem, boylam. Ham dosyayı mevcut ayrıştırıcının okuduğu initMarkers verisinden oku.
- restoranlar.csv: external_id, ad, kaynak mahalleler ("|" ile), adres satırı, şehir, posta kodu, mutfak türleri, öğünler, olanaklar, web sitesi var mı (evet/hayır), açıklama var mı (evet/hayır).

ADIM 6 — Belgeleri repoya yerleştir
origin/v0.7-lodging-inventory dalının HEAD'inden (23905962126ba9f00f7f8b6223c67c9633e70c2c) "devir-claude-code" adında yeni bir dal aç. Bu dalda:
- Kökteki mevcut CALISMA_MANTIGI.md'yi git mv ile docs/TEKNIK-CALISMA-MANTIGI-v0.6.md adına taşı; içeriği değişmesin.
- work/devir-paketi/CALISMA_MANTIGI.md'yi köke koy. Bu belgenin 13. bölümünü ("Geliştirme çalışma biçimi") yeni düzene göre yeniden yaz: proje yöneticisi (ayrı Claude sohbeti) görevi yazar, kullanıcı görevi Claude Code'a taşır, Claude Code uygular, test eder, kendi dalına push eder ve rapor yazar, yönetici commit'i ve raporu inceler, gerekirse düzeltme görevi verir, dal kullanıcının onayıyla main'e alınır. Belgedeki ChatGPT veya Codex atıflarını aynı anlamda düzelt. Belgenin geri kalanını değiştirme.
- work/devir-paketi/DEVIR/ içindeki 01–07 belgelerini docs/DEVIR/ altına koy. 04_GELISTIRME_TEST_RELEASE_AKISI.md içindeki ChatGPT/kodlama ajanı akışını da aynı yeni düzene göre güncelle.
- work/devir-paketi/KONSEPT.md'yi docs/KONSEPT.md olarak koy; içeriğini değiştirme.
- README.md'deki "Belgeler" listesine KONSEPT, docs/DEVIR/ ve taşınan teknik belge için bağlantı ekle; CALISMA_MANTIGI.md bağlantısı yerinde kalsın.
- .gitignore dosyasına work/ satırını ekle.
- Köke CLAUDE.md yaz (aşağıdaki bölüme göre).
Tümünü tek commit'te topla, dalı push et, GitHub Actions sonucunu bekle ve rapora yaz.

CLAUDE.md İÇERİĞİ
Kısa tut (en fazla yaklaşık 60 satır). Uzun kural listesi yerine projenin mantığını anlatan düz cümleler kullan. Şu konuları kapsasın:
- Projenin ne olduğu ve okuma sırası: CALISMA_MANTIGI.md, docs/KONSEPT.md, docs/DEVIR/05, sonra görevin ilgili docs/Mx belgesi.
- Çalışma düzeni: görevler GÖREV-NN numarasıyla gelir; her görev kendi dalında yapılır; main'e yalnız kullanıcı onayıyla alınır; her görevin sonunda görev metni, rapor ve istenen çıktılar docs/gorevler/GOREV-NN/ klasörüne yazılıp dala push edilir, çünkü yönetici sonucu repodan okur; rapor Türkçe ve sadedir çünkü kullanıcı kod okumaz. work/ yerel çalışma alanıdır ve repoya gitmez; veritabanı kopyaları, geçici veri klasörleri ve yardımcı betikler orada kalır.
- Veri güvenliği: data/ gerçek kullanıcı verisidir ve dokunulmaz; şema değişikliğinden önce yedek alınır ve kopya üzerinde denenir; canlı denemeler --data-dir ile geçici klasörde yapılır.
- Test: iki test komutu; testler canlı ağa bağlanmaz; canlı çekimden gelen sayılar test sabiti yapılmaz.
- Veri dili: kaynağın söylemediği şey yazılmaz, eksik alan NULL kalır, tarihli veya aramaya bağlı bir sonuç "tam liste" diye adlandırılmaz.
- 30A'ya özel davranış destinasyon profilinde veya ona özel connector'da kalır; generic çekirdeğe gömülmez.

ADIM 7 — Rapor ve teslim
docs/gorevler/GOREV-01/RAPOR.md dosyasını Türkçe yaz. Her adımın sonucunu ayrı başlık altında ver. Belge commit'inin hash'ini, CI sonucunu, karşılaştığın beklenmedik durumları ve yöneticinin karar vermesi gereken konuları yaz. Görev metnini de work/gorevler/GOREV-01.md'den docs/gorevler/GOREV-01/GOREV.md olarak kopyala.
docs/gorevler/GOREV-01/ klasörünü (GOREV.md, RAPOR.md ve üç CSV) aynı dala ikinci bir commit olarak ekle ve push et. work/ içindeki veritabanı kopyası, geçici veri klasörü ve betikler kesinlikle repoya gitmesin; push etmeden önce git status ile kontrol et.
Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-01 bitti, dal devir-claude-code, son commit <hash>." Eğer bir adım tamamlanamadıysa bunu da aynı mesaja tek cümleyle ekle.
