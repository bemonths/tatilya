# HEDEF-01 — Rapor: işçiler, deneme çekimi ve gece çekimine hazırlık

*26 Kasım 2026. Dal `hedef-01`; main'e fast-forward; etiket `v0.27.0`. Uygulama 0.27.0, şema 25, eklenti 0.21.0.*

## Kısa özet

- `gorev-25-realjoy-sorgu` main'e alındı, `v0.26.0` etiketi kondu.
- **İşçiler** yazıldı: doğrudan bağlantı ve proxy listesindeki her çalışan proxy bir işçi; kiralama çekimi ilan ilan işçilere dağıtılıyor;
  site başına en çok 4 işçi, işçi başına site aralığı en az 8 sn, 429/engel/doğrulamada bütün işçiler yavaşlıyor, tekrarında tek işçi;
  düşen ya da listeden çıkan proxy'nin işi başka işçiye geçiyor; havuz canlı; tarayıcı gerektiren siteler kendi sıralarında.
- **Proxy listesi** ekranı (Ayarlar → ABD proxy'si): toplu ekleme, her satır tek tek denenir, parolalar yalnız Windows Kimlik Bilgisi
  Yöneticisi'nde.
- **Deneme çekimi** (Sol menü → Veri → Okuma denemeleri → "Deneme çekimini başlat"): bütün toplayıcılar küçük ölçekte, gerçek sitelerde,
  işçilerle, veritabanının kopyasında. İki kez gerçek sitelerde çalıştırıldı; bulunan hatalar düzeltildi (aşağıda).
- **Tahmin** işçi sayısına göre: 1 işçi ~47 sa, 2 işçi ~27 sa, 5 işçi ~11 sa, 10 ve 20 işçi ~6 sa.
- **Önemli:** kayıtlı tek proxy 26 Kasım'da çalışmadı. Proxy listesi girilmeden kiralama çekimi tek işçiyle ~2 gün sürer ve bölge engelli
  şirketler atlanır. Gece çekiminden önce proxy listesinin girilmesi gerekir (tarif aşağıda).

---

## 1. main ve etiket

- `main` `f87582c` → `833382a` (fast-forward), açıklamalı etiket `v0.26.0` ("GÖREV-24 + GÖREV-25 (RealJoy, page queries)"), push edildi.
- İş dalı `hedef-01`. Talimat klasöründe (`studio/destinations/thirty_a_claude/`) kullanıcı değişikliği yoktu; talimat commit'i gerekmedi.
- Ara main'e alma: `43f8f82` (işçiler, deneme çekimi; CI 45859402665 başarılı). Son main ve `v0.27.0`: bölüm 9.

## 2. Kararlar (gerekçeleriyle)

1. **8 sn kuralı.** Kodda sıradan kiralama sitelerinde iki istek arası 2 sn idi (`REQUEST_GAP`), korumalı sitelerde 6 sn. Hedef "bir işçi
   aynı siteye en az 8 sn" diyor; uyguladım (korumalılar dahil 8 sn). Site başına 4 işçiyle siteye düşen yük en çok 0,5 istek/sn: eski tek
   çıkışın 2 sn aralığıyla aynı. Sonuç: az işçiyle çekim eskisinden uzun sürer (2 işçi ~27 sa; eski tahmin ~13,5 sa), işçi arttıkça kısalır.
2. **İş birimi** "şirket + ilan": ilan sayfası ve o ilanın bütün haftalarının fiyatı tek işte. Böylece bir ilanın fiyat soruları aynı
   işçinin aynı oturumunda kalır, devirde yarım iş sayılmaz. Şirketin kendi listesi tek iş; listeden eşlenen ilanlar ve kendi envanter
   evleri yine tek tek iş; yayımlanmış kira okuması şirketin son işi.
3. **Korumalı siteler programın kendi tarayıcısıyla.** Hedefe göre oversee.us ve exclusive30a.com "tarayıcı" sırasında programın
   tarayıcısıyla okunuyor (eskiden eklenti bağlıysa eklentiyle); programın tarayıcısı yoksa eklentiye düşer. RealJoy "eklenti"
   sırasında. Çekim sırasında bir işçiye doğrulama gösteren sıradan şirket, eklenti bağlıysa eklenti sırasına (yoksa tarayıcı sırasına)
   geçer ve tarayıcı doğrudan o sayfayla açılır (aynı sayfa ikinci kez doğrudan istenmez).
4. **Düşen proxy** listede "çalışmıyor" işaretlenir: sonraki çekimde işçi olmaz; "Dene" ile yeniden açılır.
5. **Deneme çekiminin yeri:** gerçek veritabanının programın aldığı kopyası (`data/deneme/<zaman>/`). Toplayıcılar orada normal iş
   akışıyla (kayıt dahil) çalışır; böylece kayıt adımı da denenmiş olur. Gerçek veritabanına yalnız deneme işinin kaydı düşer; bölge engelli
   liste ve tarayıcı alan adı işaretleri kopyada kalır. Son 3 denemenin kopyası durur; eskilerinin yalnız `sonuc.json`'u kalır.
6. **RealJoy 12 sn** göçle (v25): yalnız değer hâlâ 20 ise. 429'da işçi kuralı 24 sn'ye çıkarır; GÖREV-25'in Retry-After kuralı durur.
7. **CLAUDE.md'deki proxy cümlesi** 26 Kasım 2026 tarihli işçi kararıyla değiştirildi (CALISMA_MANTIGI ve M18 de). Proxy hâlâ bot
   korumasını, doğrulamayı ya da yasağı aşmak için kullanılmıyor; işçi doğrulama ya da engel yüzünden değiştirilmiyor.
8. **Book>Direct'in oynayan toplamı:** üç denemede de toplam yalnız 1–2 ilan (en çok %2) oynarsa son okunan ilanlar kaydedilir ve oynama
   çalışmanın notuna (`search_notes`) yazılır; daha büyük farkta çekim eskisi gibi düşer. Gerekçe: Seaside'ın toplamı her denemede 153↔154
   oynadı (bir ilan müsaitliğe göre girip çıkıyor); bütün Book>Direct çekiminin buna takılması orantısız.

## 3. İşçiler

Ayrıntı ve kurallar: `docs/M18-ABD-PROXY-BOLGE-ENGELI.md` "İşçiler". Kod: `studio/workers.py`, `studio/sources/agency_workers.py`,
`studio/proxy_list.py`.

- **Proxy listesi:** Ayarlar → ABD proxy'si → "Proxy listesi" tablosu (SIRA, PROXY `şema://sunucu`, KULLANICI, PAROLA kasada/yok, DURUM,
  ÜLKE, İŞÇİ) ve "Toplu ekleme (her satıra bir proxy)" kutusu + "Tür" (HTTP/SOCKS5) + "Listeye ekle ve dene". Kabul edilen biçimler:
  `sunucu:port:kullanıcı:parola`, `sunucu:port`, `kullanıcı:parola@sunucu:port`, `http://sunucu:port`. Kaydedince parolalar hemen
  Kimlik Bilgisi Yöneticisi'ne yazılır, kutu temizlenir; dosyada yalnız adres, port, kullanıcı adı ve tür kalır. Her satır tek tek denenir;
  çalışmayan "çalışmıyor" olur ve işçi olmaz. Eski tek proxy listenin ilk satırı oldu.
- **"Proxy'yi dene"** (Veri → Okuma denemeleri) her proxy için ayrı sonuç verir: çalışıyor mu, çıkış ülkesi. Satırdaki "Dene" tek proxy'yi dener.
- **Site başına sınır:** Ayarlar → ABD proxy'si → "Sitenin korunması" → "Aynı siteye aynı anda çalışan en çok işçi" (1–8, başlangıç 4).
- **Yavaşlama:** bir site herhangi bir işçiye 429, engel sayfası ya da doğrulama sayfası verirse o sitedeki bütün işçilerin aralığı iki
  katına çıkar; tekrarında o site tek işçiyle okunur. Olaylar iş mesajına, İşler paneline ve çalışmanın kaydına (`metadata.isciler.olaylar`) yazılır.
- **Bölge engelli siteler** yalnız ABD çıkışlı (ya da ülkesi bilinmeyen) proxy işçilerine gider; ABD proxy'si yoksa şirket atlanır ve kaydedilir.
- **İşler paneli:** çalışan kiralama işinin kartında "İşçiler (N çalışıyor)": çıkış (doğrudan / proxy N / tarayıcı / eklenti; adres yok),
  elindeki şirket, biten iş, hata, durum ve son olaylar.
- **Testler** (`tests/test_hedef01.py`, sahte HTTP, her işçi ayrı sahte istemci): dağıtım ve tekrarsızlık; proxy düşünce işin devri ve
  "çalışmıyor" işareti; site başına sınır (2 ve 4); 429'da bütün işçilerin yavaşlaması ve ikincisinde tek işçi (öbür site etkilenmez);
  bölge engelli sitenin yalnız ABD proxy'sine gitmesi ve ABD proxy'si yoksa atlanması; korumalı ve yalnız eklentili şirketlerin bölünmeden
  kendi sıralarında okunması, doğrulama gösteren şirketin sıraya geçmesi; canlı havuz (eklenen ve çıkarılan proxy); deneme sınırları;
  tahmin; satır biçimleri, parolaların yalnız kasada durması, API.

## 4. Deneme çekimi

### Tasarım

`studio/trial_run.py`; ekran Sol menü → Veri → Okuma denemeleri → "Deneme çekimi" bölümü → **"Deneme çekimini başlat"**.
- Gerçek veritabanının kopyası (SQLite backup API) `data/deneme/<YYYYMMDD-HHMMSS>/studio.sqlite3`; ham dosyalar yanında.
- Kiralama şirketleri: şirket başına 2 ilan (son çekimde şirket sayfasına bağlanmış olanlar önce), tek hafta, şirketin site haritası
  listesinden 3 sayfa, kendi envanterinden 2 ev; işçilerle. Book>Direct: tek hafta, 5 fiyat takvimi. Restoran siteleri: 3 restoran.
  Öbürleri (hava, iklim, deniz suyu, kasırga, plajlar, mahalleler, restoran dizini, günlük ihtiyaç, yol ağı, bilet ücreti) tam.
- Sonuç tablosu ekranda ve `sonuc.json`'da: toplayıcı başına sonuç, kayıt sayısı, süre, not; kiralama şirketi başına sonuç, ilan /
  eşlenen / fiyatlı, hangi işçiden okunduğu, not; sitenin korunma olayları.

### Gerçek sitelerdeki sonuç

TRIAL_RESULTS

### Bulunan ve düzeltilen hatalar

| Hata | Düzeltme | Test |
|---|---|---|
| Track altyapılı 30A Escapes, Ocean Reef Resorts, Panhandle Getaways her isteğe HTTP 429 "Quick security check" (Turnstile, `challenge.icoastalnet.com`) verdi; program bunu doğrulama değil ret sayıp şirketi durdurdu | Doğrulama işaretlerine eklendi (program ve eklenti 0.21.0); şirket eklenti sırasına geçer, kullanıcı doğrular | `test_the_track_sites_own_security_check_…` (gerçek cevaptan fixture) |
| Visit South Walton sitesi Gatsby ile yeniden yapılmış: plaj sayfasında `initMarkers` verisi yok | Erişim noktaları sitenin kendi statik veri dosyasından (`allBeachAccess`, `studio/sources/gatsby.py`); eski kimliklerle aynı, 53 kıyı kaydı | `test_the_rebuilt_visit_south_walton_site_…` |
| Book>Direct Seaside araması: toplam her denemede 153↔154 oynadı, bütün çekim düştü | Küçük oynamada son okunan ilanlar kaydedilir, not düşülür (karar 8) | `test_a_total_that_only_wobbles_is_kept_with_a_note` |
| Overpass (günlük ihtiyaç noktaları) tek 502'de düştü | Meşgulken 30/60/120/240 sn bekleyip yeniden sorar (yol ağıyla aynı kural) | `test_a_busy_overpass_server_is_asked_again_after_a_wait` |
| Deneme çekiminde 30A Beach Girls'ün AvantStay listesi 144 evin hepsini açtı (deneme sınırı uygulanmıyordu) | AvantStay listesi `max_pages` sınırına uyar | `test_the_trial_run_reads_only_a_few_homes_of_the_avantstay_list` |
| winndixie.com proxy kimlik doğrulama penceresi (GÖREV-25 notu): yönlendirmede aynı istek kimliğiyle gelen ikinci proxy sorusu "yanlış parola" sayılıp iptal ediliyordu (`ERR_INVALID_AUTH_CREDENTIALS`) | İsteğin yolundaki her adrese bir kez cevap (en çok 8); aynı adres ikinci kez sorulursa yine iptal | `test_proxy.py` (auth_answer) |
| CI'daki "test_extension kapanışında takılma" (bu hedefte bir kez, 45856622744) | Takılmanın ek açıklaması artık son test satırlarını ve her iş parçacığının program satırlarını taşıyor; bir sonraki takılmada kök neden görülecek | — |

### Kalıcı engeller ve kullanıcı işi

- **Your Friend at the Beach:** sitenin fiyat servisi "You are not authorized to use this service" diyor; Ekim çekiminde de 252/252 böyleydi.
  Sitenin servisi dışarıya kapalı (kalıcı).
- **Doğrulama isteyen siteler** (yalnız kullanıcı geçer): oversee.us (programın tarayıcısı), alysbeach.com, rosemarybeach.com ve realjoy.com
  (Cloudflare "Just a moment"; eklenti), Track'li üç şirket ("Quick security check"; eklenti). Denemelerde kullanıcı yoktu; 15 dakika
  beklenip atlandılar.
- **Bölge engelli** 360 Blue ve Vacasa: proxy çalışmadığı için atlandı ("ABD proxy'si tanımlı değil"). Çalışan ABD proxy'si gerekir.

## 5. Tahminler

"Güncelleme zamanı gelenler" tablosunun "Kiralama şirketleri · Konaklama fiyatları" satırı artık işçi sayısıyla hesaplanıyor ve altında
10 ve 20 işçiyle tahmini de yazıyor. Kaynak: son kiralama çekiminin (9–10 Ekim) şirket başına istek sayıları ve sonra eklenen 4 şirketin
(360 Blue, Vacasa, 30A Beach Girls, RealJoy) tahmini istekleri; toplam ~24.700 istek; site başına 4 işçi; işçi başına 8 sn + 1 sn cevap.

| İşçi | Tahmini süre (kiralama) |
|---|---|
| 1 (yalnız doğrudan; bugünkü durum, proxy çalışmıyor; bölge engelli şirketler atlanır) | ~47 sa |
| 2 (doğrudan + 1 ABD proxy'si) | ~27 sa |
| 3 | ~18 sa |
| 5 | ~11 sa |
| 10 | ~6 sa 10 dk |
| 20 | ~6 sa 10 dk |

10 işçiden sonra süreyi oversee.us belirliyor: korumalı site, tarayıcı sırasında tek başına (~2.300 istek × 9 sn ≈ 6 sa). Bu gece zamanı
gelen öbür toplayıcılar: Book>Direct (~1 sa) ve Yol ağı (~1 dk); restoran dizini, mahalleler ve plajların zamanı gelmedi.

## 6. Kullanıcının gece çekimi tarifi

TARIF

## 7. Açık kalanlar

- **Proxy listesi** kullanıcıdan gelecek; kayıtlı tek proxy 26 Kasım'da çalışmadı. Deneme çekimi bu yüzden yalnız doğrudan işçiyle yapıldı;
  proxy işçileri gerçek sitelerde denenmedi (testlerde sahte HTTP'yle denendi). Bölge engelli 360 Blue, Vacasa ve proxy'yle okunan
  CVS/Publix/Winn-Dixie sayfaları bu yüzden gerçek denemede okunmadı; winndixie düzeltmesi de gerçek proxy'yle denenemedi.
- **Visit South Walton'ın restoran dizini ve mahalleleri** (site yeniden yapıldı): restoran listesinde alt kategori ("Restaurants") bilgisi
  boş geliyor (aynı listede catering, bar vb.; 235 işletme), mahalle kayıtlarında koordinat, etiket ve değişiklik zamanı yok (tablo
  koordinatı zorunlu tutuyor). İkisi kaynağın ne söylediğine dair karar istiyor; okuyucu yazılmadı. Bu iki toplayıcı çalıştırılırsa
  "kaynak yapısı değişti" hatası verir; eski kayıtlar korunur. Bu gece zamanları gelmediği için gece çekimini etkilemez.
- **Doğrulama gerektiren siteler** kullanıcı doğrularsa okunur (tarif).
- **CI'daki ara sıra takılma** (test_extension kapanışı): tanı adımı düzeltildi, kök neden bir sonraki takılmada.

## 8. Yedekler

- Gerçek verinin tam yedeği, program kapalıyken: `work/yedek/20261126-1905/` (45.688 dosya, 1.976.684.410 bayt; kaynakla aynı).
- Programın göç yedeği (şema 24 → 25): `data/backups/studio-v24-737ad661f5534f1980f964bb121a58e6.sqlite3`.
- Göç önce kopyada denendi: satır sayıları aynı, `foreign_key_check` boş, RealJoy `gap_s` 12.
- Deneme çekimlerinin kopyaları: `data/deneme/20261126-193747/`, `data/deneme/SECOND_TRIAL/`.

## 9. Testler ve CI

TESTS

## 10. Uyulan kurallar

- Uzun çekim ("Zamanı gelenleri başlat" ya da bir toplayıcının tam çalışması) başlatılmadı; yalnız deneme çekimi (küçük, kopyada).
- Gerçek Claude çalıştırılmadı; alt ajan kullanılmadı; zamanlanmış görev oluşturulmadı; Windows ayarı değiştirilmedi.
- `data/` içinde elle dosya değiştirilmedi, silinmedi, taşınmadı; veri yalnız programın normal kullanımıyla (göç, deneme çekimi) değişti.
- Proxy adresi, kullanıcı adı ve parola hiçbir dosyaya, günlüğe ve rapora yazılmadı; proxy'ler "proxy N" diye anılır.
- Housing Atlas yalnız okundu (işçi düzeni ve proxy biçimi); parola ya da proxy bilgisi okunmadı. Talimat dosyalarına dokunulmadı.
- Canlı incelemeler: visitsouthwalton.com'a 8 istek (aralar ≥8 sn): sayfa verisi, plaj bileşeni, iki statik sorgu, mahalle ve restoran
  sayfa verileri.
