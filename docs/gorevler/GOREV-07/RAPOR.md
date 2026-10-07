# GÖREV-07 Raporu — v0.9.0 yayını, kural değişikliği, referans tablosu, konaklama profili

Tarih: 7 Ekim 2026 · Dal: `gorev-07-konaklama` · Uygulama `0.10.0` · Şema `10`

## Kısaca

- **Adım 1 tamam:** main `7110f88`'e getirildi, `v0.9.0` etiketi konuldu; ikisinin de CI'ı başarılı.
- **Adım 2 yapılamadı:** yeni bilgi toplama ilkesini CLAUDE.md'ye ve kural belgelerine yazma işlemini Claude Code'un otomatik izin denetimi "kendi talimatlarını değiştirme" sayarak engelledi. Kural belgeleri değişmedi; ayrı commit yok.
- **Adım 3 büyük ölçüde tamam:** referans tablosu 85 → 103 satır; plajda alkol, 2026 cankurtaran sezonu, golf arabası/düşük hızlı araç, planlı toplulukların otoparkı eklendi; 2025 ziyaretçi sayısı yönetici kararıyla çözüldü; yeni durum `yerine_gecildi`. Eyalet parkı ücretleri, Timpoochee'nin ilçe değeri ve 30A hız sınırları bulunamadı.
- **Adım 4 kod olarak tamam, canlı çalıştırılmadı:** Book>Direct konaklama toplayıcısı, şema 10, Konaklama sekmesi ve 39 test hazır. Ön yüz paketinden istemci anahtarını okuyan ilk canlı deneme izin denetimince "kimlik bilgisi keşfi" sayılıp engellendi; bu yüzden gerçek konaklama verisi yok.
- **Adım 5 tamam:** belgeler (M10 yeni; M9, durum satırları), 554 Python + 46 frontend testi art arda 3 kez geçti.
- **Adım 6 kısmen:** v9 → v10 geçişi gerçek verinin kopyasında temiz. Geçici canlı deneme ve gerçek veritabanı güncellemesi yapılmadı; gerçek veritabanına ve `data/` klasörüne dokunulmadı (şema 9 kaldı, main'deki 0.9.0 açabiliyor).

## Adım 1 — v0.9.0'ı main'e alma ve etiketleme

| | |
|---|---|
| main | `git merge --ff-only origin/gorev-06-referanslar` ile `7110f881e69793b907ecd791a52e761d569cdfd1`'e getirildi ve push edildi |
| Etiket | `v0.9.0` önceden yoktu; açıklamalı etiket ("v0.9.0 — kasırga evre kuralı ve referans tablosu") `7110f88`'i gösteriyor, push edildi |
| main CI | çalıştırma 37655748525 — başarılı |
| Etiket CI | çalıştırma 37655792703 — başarılı |
| Görev dalı | güncel main'den `gorev-07-konaklama` açıldı |

Beklenmedik durum: GitHub ilk dakikalarda bütün push'ları "Internal Server Error" ile reddetti (durum sayfası sorunsuz görünüyordu). Push'lar aralıklarla yeniden denendi; main 6. denemede, etiket ilk denemede geçti. main'e bunun dışında dokunulmadı.

## Adım 2 — Bilgiye erişimi kısıtlayan kurallar (yapılamadı)

Hazırlanan düzenleme (CLAUDE.md'ye "Bilgi toplama" bölümü, CALISMA_MANTIGI §4 madde 13–14, DEVIR/03, 06, 07, M4, M6, M8, M9, MIMARI ve GÖREV-02/06 belgelerine tarihli notlar) çalıştırılmadan önce Claude Code'un otomatik izin denetimi tarafından **"Self-Modification" (kendi talimat dosyalarını değiştirme)** gerekçesiyle engellendi. Denetimin kuralı gereği aynı sonuca başka bir yoldan gidilmedi; hiçbir kural belgesi değişmedi. Kullanıcı Claude Code ayarlarında bu tür işleme izin verirse (izin kuralı) düzenleme hazır olarak uygulanabilir.

Değiştirilecek kurallar (hiçbiri uygulanmadı):

| Yer | Bugünkü kural | Görevdeki yeni hali | Durum |
|---|---|---|---|
| CLAUDE.md | Bilgi toplama bölümü yok | Görevdeki yeni ilke metni | Uygulanmadı (engellendi) |
| CALISMA_MANTIGI §4 m.13 | "Playwright varsayılan değildir; HTTP/JSON ile çözülüyorsa kullanılmaz." | "İlk tercih API, JSON ve HTML'dir; gerekiyorsa tarayıcı otomasyonu kullanılır." | Uygulanmadı |
| CALISMA_MANTIGI §4 m.14 | Düzenli toplayıcılar robots.txt'ye uyar; tek seferlik belge alımı toplayıcı sayılmaz | Yeni bilgi toplama ilkesi | Uygulanmadı |
| DEVIR/03 | "connector işletmenin sitesini crawl etmez"; anti-pattern "External site URL'sini otomatik crawl etme" | İşletme sitesi dizindeki bağlantıyla kimliği belli olduğu için doğrudan okunabilir | Uygulanmadı |
| DEVIR/06 | Restoran zenginleştirmesi için önce entity matching, menü sürümleme, fiyat anlamı tasarımı şartı; market ve POI'yi caydıran notlar | "Yapılabilir, kaynak ve tarihle" | Uygulanmadı |
| DEVIR/07 | "Şu an senden beklenmeyenler" listesi | Yalnız geçerli olanlar (production DB'yi sıfırlamamak vb.) | Uygulanmadı |
| M9, GÖREV-06 | "Bot korumalı sayfa otomasyonla aşılmaz", "başka mevzuat aranmadı" | Tarihli karar notu | Uygulanmadı |
| GÖREV-02, M8 | "robots.txt kapalı / bot korumalı olduğu için kullanılamaz" değerlendirmeleri | Tarihli karar notu | Uygulanmadı |

Ayrıca bilinmesi gereken bir sınır: yeni ilke uygulansa bile Claude Code CAPTCHA'yı ya da "insan olduğunuzu doğrulayın" ekranını çözmez ve tarayıcıyı bot tespitinden gizleyen ayarlar kullanmaz. Hazırlanan metne bunu söyleyen bir cümle eklenmişti ("sayfa normal bir tarayıcıda açılmıyorsa aynı bilgi başka bir resmî yayından aranır, bulunamazsa rapora yazılır").

## Adım 3 — Referans tablosunun tamamlanması

Yeni belgeler `work/referans-belgeler/` altına SHA-256 ile kaydedildi (31 alım; 5'i 403/404). Yeni satırların 15 kısa alıntısının hepsi kaydedilen belgede birebir bulundu (`work/gorev-07/alinti_kontrol.py`). Doğrulayıcıya `yerine_gecildi` durumu eklendi: eski satır silinmez, notunda `yerine geçen: <kimlik>` yazar ve o kimlik doğrulanmış bir satır olmalıdır; Referanslar sekmesi bu durumu sayar ve yerine geçen satırı gösterir.

| Konu | Sonuç |
|---|---|
| Parklar (Grayton Beach, Topsail Hill, Deer Lake) | **Çözülemedi.** Uygulama içi tarayıcıyla floridastateparks.org'a giriş reddedildi; düz HTTP isteği hem park sayfasında hem eyaletin ücret çizelgesi PDF'inde 403 (Cloudflare) verdi. Başka resmî yayında ücret ve saat bulunamadı. 6 satır "doğrulanamadı" kaldı. |
| Plajda alkol | **Çözüldü.** İlçe plaj yönetmeliğinde hüküm yok (eski satır). Walton County Tourism: yasal yaştaki yetişkinler yalnız kutu veya plastikle (cam bütün plajlarda yasak). Eyalet parklarında alkol tüketimi, satış yapan restoran/konaklama yerleri ve park etkinlikleri dışında yasak (Florida Administrative Code 62D-2.014(12)). 21 yaş altına bulundurmak yasak (Florida Statutes 562.111). Düşük hızlı araçta açık alkol kabı yasak (Walton County Sheriff). Walton County Code'un diğer bölümlerinde plajda alkolü düzenleyen hüküm bulunamadı. |
| Cankurtaran | **Çözüldü, ikincil kaynakla.** 2026 sezonu 1 Mart–31 Ekim, 10:00–18:00 (SoWal.com, 2 Mart 2026; SWFD Beach Safety Director alıntısıyla); Walton County Tourism'in sayfasıyla aynı. SWFD'nin kendi sitesinde 2026 duyurusu yok; SWFD SSS sayfası hâlâ 30 Eylül diyor. Yeni satır doğrulandı, iki eski satır `yerine_gecildi`. |
| Timpoochee Trail uzunluğu | **Çözülemedi.** Yolu yöneten Walton County'nin resmî uzunluk değeri bulunamadı (ilçe sitesi ve "Timpoochee Trail Extension" ihale belgesi uzunluk vermiyor). İki satır "çelişkili" kaldı. |
| 2025 ziyaretçi sayısı | **Çözüldü (yönetici kararı).** 4.586.000 doğrulandı; 4,57 milyon satırı `yerine_gecildi`, gerekçe notta. |
| Golf arabası / düşük hızlı araç | **Çözüldü.** İlçe: golf arabaları ilçe yollarında kullanılamaz; şerif: hiçbir kamu yolunda kullanılamaz. İlçenin golf arabasına açtığı bir yol bulunamadı. Düşük hızlı araç: yalnız 35 mph ve altındaki yollar; kaldırım ve bisiklet yolunda yasak; US 98'de yasak, yalnız dört yollu kavşakta geçiş. |
| 30A hız sınırları | **Çözülemedi.** Resmî karar veya trafik çalışması belgesi bulunamadı; ilçe meclisinin 35 mph azami hız önerisini onayladığını aktaran tek haber (DeFuniak Herald) Cloudflare doğrulaması nedeniyle okunamadı. 1 satır "doğrulanamadı". |
| Planlı topluluklar | **Kısmen.** Seaside: saatlik, güne ve doluluğa göre değişen ücretli otopark (tutar yok) ve 06:00–24:00 ücretsiz servis. Alys Beach: işaretli yerlerde ücretsiz ziyaretçi otoparkı; plaj ve plaj erişimleri halka kapalı. WaterColor: topluluk derneğinin yönettiği ücretli park yerleri (otelin SSS'sinden, ikincil). Rosemary Beach ve WaterSound sitelerinde ziyaretçi otoparkı bilgisi bulunamadı (2 satır "doğrulanamadı"). |

Konu başına satır ve durum sayıları (103 satır):

| Konu | Satır | Doğrulandı | Çelişkili | Doğrulanamadı | Yerine geçildi |
|---|---:|---:|---:|---:|---:|
| Plaj kuralları | 29 | 29 | 0 | 0 | 0 |
| Güvenlik | 13 | 11 | 0 | 0 | 2 |
| Plaj erişimi | 17 | 15 | 0 | 2 | 0 |
| Ulaşım | 17 | 14 | 2 | 1 | 0 |
| Parklar | 8 | 2 | 0 | 6 | 0 |
| Kasırga sezonu | 2 | 2 | 0 | 0 | 0 |
| Sezon ve maliyet | 14 | 13 | 0 | 0 | 1 |
| Genel | 3 | 3 | 0 | 0 | 0 |
| **Toplam** | **103** | **89** | **2** | **9** | **3** |

## Adım 4 — Konaklama profili toplayıcısı

Yazıldı (`studio/sources/bookdirect_lodging.py`, `bookdirect-lodging/1`; ayrıntı `docs/M10-KONAKLAMA-PROFILI.md`):

- Genel toplayıcı; clone adresi, konum filtresi eşlemesi ve tarih pencereleri SQLite'ta. 30A için ilk değerleri profil ve şema 10 migration'ı yazar: `visitsouthwalton.bookdirect.net`, 14 konum filtresi (13 mahalle; Watercolor/Watersound yazımları; Seagrove Beach da Seagrove'a bağlı, her satır hangi filtreden geldiğini saklar), görevdeki 4 pencere.
- İstemci anahtarı her çekimde giriş HTML'inin gösterdiği güncel paketten okunur, yalnız bellekte tutulur; paket gövdesi ve anahtarı içeren hiçbir yanıt saklanmaz. Testler bütün yazılan dosyaları, veritabanı dökümünü ve iş kaydını anahtar için tarıyor.
- Her pencere × filtre için bütün sayfalar (toplam değişirse bir kez yeniden, sonra hata); canlı fiyat en fazla 3 denemeyle; her benzersiz ilan için bir fiyat takvimi, veritabanına yalnız aylık özet; geçmiş pencere atlanır ve kaydedilir; istekler sıralı, 1,25 sn arayla; ham yanıtlar gzip ve SHA-256 ile; iptal ve tek transaction'da yayım.
- Okuma anında mahalle × pencere özeti (ilan sayısı, kategori ve yatak odası dağılımı, kapasite ortancası, fiyatlı ilan payı ve kaynağı, gecelik fiyat ortancası ve çeyrekleri) ve mahalle başına aylık takvim ortancası; her özetin altında görevdeki etiket.
- Veri toplama → Konaklama sekmesi: toplama düğmesi, sürüm seçimi, özet tablosu, mahalle ve ilan ayrıntısı.
- Testler: 39 Python testi (görevdeki bütün başlıklar) ve 4 frontend testi.

**Çalıştırılmadı.** Book>Direct'in güncel paket yolunu ve canlı fiyat mantığını görmek için yaptığım keşif isteği, Claude Code'un otomatik izin denetimince **"Credential Exploration" (kimlik bilgisi keşfi)** gerekçesiyle engellendi: ön yüz paketinden istemci anahtarını okuyup API'ye göndermek bu kapsama giriyor. Denetimin kuralı gereği aynı sonuç (anahtarın okunup kullanılması) başka bir yoldan denenmedi. Toplayıcı bu yüzden yalnız sahte sunucuyla, ağ olmadan sınandı; canlı fiyat deneme sayısı ve aralığı gerçek paketten okunamadığı için GÖREV-02'deki kod parçalarına göre seçildi (3 deneme, 2 sn).

## Adım 5 — Belgeler ve testler

- Yeni: `docs/M10-KONAKLAMA-PROFILI.md`. Güncellenen: `docs/M9-REFERANS-TABLOSU.md`, `CALISMA_MANTIGI.md`, `README.md`, `docs/DEVIR/02`, `05`, `07` (yalnız durum satırları), `docs/ASAMALAR.md`, `docs/M6` (M10'a işaret eden not). Kural metinleri Adım 2 nedeniyle değişmedi.
- Uygulama `0.10.0`, şema `10`.
- Testler art arda 3 kez: **554 Python testi geçti** (görev başında 513), **46 frontend testi geçti** (görev başında 42). Her Python çalıştırmasında bilinen kütüphane uyarısı (Starlette/httpx).
- Dal CI: kod commit'i `71d51ef` için çalıştırma 37661118265 — başarılı.

## Adım 6 — Gerçek ortam

1. **Geçici klasörde canlı deneme:** yapılmadı (Adım 4'teki engel). Süre, istek sayısı ve sonuç yok.
2. **Migration denemesi (v9 → v10), gerçek verinin kopyası:** `data/studio.sqlite3` salt okunur açılıp `work/gorev-07/migration-data/` altına kopyalandı, uygulama bu kopyayla açıldı ve kapatıldı. Şema 9 → 10; eski bütün tabloların satır sayıları ve çekimler aynı; yalnız 11 konaklama tablosu, 30A konaklama yapılandırması (1 clone, 14 konum filtresi, 4 pencere) ve 1 kaynak ("South Walton · Konaklama (Book>Direct)") eklendi; `integrity_check` ok, `foreign_key_check` boş.
3. **Gerçek veritabanı:** güncellenmedi. Görevde bu adımın amacı konaklama toplayıcısını gerçek veriyle çalıştırmaktı; çekim yapılamadığı için yalnız şema yükseltmesi yapmak gerçek veritabanını main'deki 0.9.0'ın açamayacağı bir hâle getirirdi. `data/` klasörüne dokunulmadı, yedek de alınmadı.

Ekran görüntüleri: `konaklama-sekmesi-bos.png` (gerçek verinin kopyasında, geçişten sonra; henüz çekim yok), `referanslar-sekmesi.png` (103 satırlık tablo), `konaklama-sekmesi-sentetik-test-verisi.png` (**gerçek veri değil**: testlerdeki sahte sunucunun verisiyle, yalnız ekranın dolu hâlini göstermek için).

## Konaklama çekiminin sonuçları

Yok. `konaklama-ozet.csv` ve `konaklama-aylik-fiyat.csv` gerçek veritabanındaki çekimden üretilecekti; çekim yapılamadığı için üretilmedi.

## Teslim klasörü

`docs/gorevler/GOREV-07/`: `GOREV.md`, `RAPOR.md`, `referans-tablosu.csv`, `konaklama-sekmesi-bos.png`, `referanslar-sekmesi.png`, `konaklama-sekmesi-sentetik-test-verisi.png`.

## Beklenmedik durumlar

- İki işlem Claude Code'un otomatik izin denetimince engellendi: kural belgelerinin değiştirilmesi (kendi talimatlarını değiştirme) ve Book>Direct istemci anahtarının okunup kullanılması (kimlik bilgisi keşfi). Kullanıcının mesajındaki izin bu denetimi aşmıyor; denetim kullanıcının ayarlarından izin verilmesini istiyor.
- Uygulama içi tarayıcıda floridastateparks.org'a giriş reddedildi.
- GitHub'ın push'ları birkaç dakika "Internal Server Error" ile reddetmesi.
- Seaside'ın 2026 otopark sayfasında tarih tutarsızlığı (başlık "Saturday, March 1, 2026", metin "Sunday, March 1, 2025"); satır notunda yazıyor.
- SWFD'nin SSS sayfası 2026'da da cankurtaran sezonunu 30 Eylül diye veriyor; 2026 sezonunun tarihli tek kaynağı yerel haber sitesi.

## Yöneticinin karar vermesi gereken konular

1. **Konaklama canlı çekimi:** devam için kullanıcının Claude Code'da Book>Direct istemci anahtarının okunup kullanılmasına izin vermesi gerekiyor. İzin gelirse sırası: geçici klasörde canlı deneme (tahmini 45–60 dakika), gerçek veritabanı (önce `data/` tam yedeği), özet CSV'leri ve ekran görüntüsü.
2. **Adım 2:** kural belgelerinin değişmesi için de kullanıcının izni gerekiyor. Hazırlanan metinde Claude Code'un etkileşimli bot doğrulamasını (CAPTCHA) çözmeyeceğini söyleyen cümle kalsın mı?
3. **Cankurtaran 2026:** tarihli kaynak yerel haber sitesi (ikincil); SWFD'den resmî bir 2026 duyurusu istenmeli mi, yoksa Walton County Tourism'in aynı tarihleri vermesi yeterli mi?
4. **Eyalet parkı ücretleri:** site otomatik erişime kapalı; kullanıcı kendi tarayıcısında bakıp değeri iletirse tabloya elle (kaynak ve tarihle) eklenebilir. Ya da videoda park ücreti söylenmez.
5. **30A hız sınırları ve Timpoochee uzunluğu:** resmî belge bulunamadı; ilçeden sorulsun mu, videoda kullanılmasın mı?
6. **main'e alma:** `gorev-07-konaklama` canlı çekimden önce mi sonra mı alınsın? (Alındığında gerçek veritabanı ilk açılışta şema 10'a yükselir.)
