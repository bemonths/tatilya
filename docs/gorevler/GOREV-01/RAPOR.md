# GÖREV-01 Raporu — Devir alma, zemin kontrolü ve belge düzeni

Tarih: 7 Ekim 2026 · Dal: `devir-claude-code` · Belge commit'i: `e118f9d2b0f58bf5903b8742eef196a8480ccf47` · CI: başarılı

Saatler aksi yazılmadıkça UTC'dir. TSİ = Türkiye saati (UTC+3).

## Kısa özet

- Yerel ortam sağlam. Bütün yerel dallar ve etiketler GitHub ile aynı. Testler beklenen tabanla aynı: 289 Python + 19 arayüz testi geçti.
- Gerçek veritabanı yalnız salt okunur kopyadan okundu; gerçek dosya hiç değişmedi (SHA-256 önce ve sonra aynı). Şema 6. Sayılar belgelerle birebir aynı. Son veri çekimi 30 Eylül 2026.
- Üç kaynak bugün geçici klasörde hatasız çekildi: 53 plaj erişimi (17 kapsam dışı), 510 hava tahmini kaydı, 138 restoran.
- İstenen üç CSV, devir belgeleri, KONSEPT ve CLAUDE.md repoya yerleşti. GitHub Actions başarılı.
- Uygulama kodu, testler, şema ve `data/` klasörü değişmedi. main'e dokunulmadı, etiket oluşturulmadı.
- Birkaç küçük konu yöneticinin kararını bekliyor (en sonda).

## Adım 1 — Ortam ve repo durumu

| Konu | Durum |
|---|---|
| Windows Python (`py -0p`) | 3.12-64 → `C:\Users\1\AppData\Local\Programs\Python\Python312\python.exe` (`py` varsayılanı 3.12.3) · 3.10-64 → `C:\Users\1\AppData\Local\Programs\Python\Python310\python.exe` |
| `.venv` Python | 3.12.3 (Python312 tabanlı) |
| Node | v24.13.1 |
| Git | 2.53.0.windows.1 |
| Görev başında aktif dal ve HEAD | `v0.7-lodging-inventory` @ `23905962126ba9f00f7f8b6223c67c9633e70c2c` |
| Kaydedilmemiş değişiklik | Yok |
| İzlenmeyen dosya | Yalnız `work/` (devir paketi, görev dosyası, yönetici notları; 12 dosya) |
| Git'in yok saydığı klasörler | `.venv/`, `.pytest_cache/`, `__pycache__/`, `data/` (veritabanı, `backups/` içinde 4 yedek, `raw/` altında ham çekimler) |

`git fetch --all --prune --tags` sonrası her yerel dal origin ile aynı:

| Dal | Yerel = origin | Fark |
|---|---|---|
| `main` | `a938367` | 0 ileri / 0 geri |
| `v0.3-data-foundation` | `13ef01c` | 0 / 0 |
| `v0.4-weather-connector` | `bbeb07b` | 0 / 0 |
| `v0.5-restaurants-connector` | `3c6a6bd` | 0 / 0 |
| `v0.6-destination-layer` | `a938367` | 0 / 0 |
| `v0.7-lodging-inventory` | `2390596` | 0 / 0 |

GitHub'da bunlardan başka dal yoktu. Yerel etiketler (hepsi açıklamalı etiket, GitHub'dakilerle aynı): `v0.3.0` → `13ef01c`, `v0.4.0` → `bbeb07b`, `v0.5.0` → `3c6a6bd`, `v0.6.0` → `a938367`.

**"dubious ownership" hatası çıkmadı.** `safe.directory` ayarı global git yapılandırmasında bu repo yolu için zaten kayıtlıydı; ek bir işlem gerekmedi.

**Konaklama keşfi klasörleri** repo klasöründe ve `outputs` klasöründe yok. Bir seviye daha yukarıda, `outputs` klasörünün yanındaki `work\` klasöründe bulundu. İçerikleri taşınmadı:

- `C:\Users\1\Documents\Codex\2026-09-29\referenced-chatgpt-conversation-this-is-an\work\lodging-discovery\` — 18 dosya, yaklaşık 874 KB
- `C:\Users\1\Documents\Codex\2026-09-29\referenced-chatgpt-conversation-this-is-an\work\lodging-phase2\` — 45 dosya, yaklaşık 2,8 MB

`lodging-discovery` (ad · bayt):

```text
bookdirect.html                 7206
bookdirect.js                 229280
comparison-20261002-1.json     64977
comparison-20261002-2.json     64852
comparison-20261002-3.json     16455
comparison-20261102-1.json     64841
comparison-20261102-2.json     64879
comparison-20261102-3.json     17539
date-comparison-result.json     7486
detail.json                     1087
dune-no-dates.json                46
dune-other-date.json           64841
dune.json                      64977
home.html                      70158
listings.json                     46
newsletter.html                64251
show.json                      51508
stay.html                       7206
```

`lodging-phase2` (ad · bayt):

```text
autocomplete-no-dates.json             46
bookdirect.js                      229280
bundle-route-strings.json           15077
bundle-service-definitions.json     13721
bundle-term-inventory.json         670583
config-key-inventory.json           52425
config-value-inventory.json         86616
current-listing-policy.html        245098
current-policy-text.txt             10474
directory-0.html                    67969
directory-1.html                    67291
directory-10.html                   65432
directory-2.html                    65333
directory-3.html                    66355
directory-4.html                    67621
directory-5.html                    66884
directory-6.html                    66838
directory-7.html                    67254
directory-8.html                      162
directory-fetch-output.txt          19125
directory-filter-inventory.json     12365
entry.html                           7206
index-no-dates.json                    46
known-id-no-dates.json                 46
missing-id-comparison-dates.json     1009
missing-id-no-dates.json               46
missing-id-original-dates.json        988
pearl-detail.json                    1493
pearl-id-search.json                 2065
requests.json                       11002
robots.txt                             94
search-no-dates.json                   46
show.json                           51508
sitemap-classification.json         76712
sitemap.xml                        189433
vsw-app.js                          72608
vsw-directory.html                  65189
vsw-dune.html                       60066
vsw-hotel.html                      56464
vsw-listing-policy.html               162
vsw-page-inventory.json             53418
vsw-pearl.html                      62424
vsw-resortquest.html                63486
vsw-scan-output.txt                 38131
vsw-search.html                     60444
```

Aynı üst `work\` klasöründe (en üst seviyede 105 öğe, toplam 544 dosya, yaklaşık 35 MB) önceki yapay zekâdan kalan başka dosyalar da var: yardımcı betikler, günlükler, smoke sonuçları, `v06-user-copy\` (dosya adlarına göre gerçek veritabanının v5/v6 göç denemesi kopyaları) ve `browser-data\studio.sqlite3`. Hiçbirine dokunulmadı.

## Adım 2 — Testler

- `.venv\Scripts\python.exe -m pytest -q` → **289 geçti**, 0 hata, 25,2 sn. 1 uyarı: `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` Bu bilinen ve engelleyici olmayan uyarıdır.
- `node --test tests/frontend.test.mjs` → **19 geçti**, 0 hata. Uyarı yok.
- Sonuç beklenen tabanla (289 + 19) aynı.

## Adım 3 — Gerçek veritabanının durumu (yalnız kopya üzerinden)

Önce uygulamanın kapalı olduğu doğrulandı: 30A Studio süreci yoktu, 8830 portu dinlenmiyordu, veritabanının yanında `-wal`, `-shm` veya `-journal` dosyası yoktu.

**Kopyalama:** `data/studio.sqlite3` dosyası `file:///…/data/studio.sqlite3?mode=ro&immutable=1` ile salt okunur açıldı ve SQLite backup API ile `work/gorev-01/db-kopya.sqlite3` olarak kopyalandı. `immutable=1` eklenmesinin nedeni: veritabanı WAL kipinde (dosya başlığında 18. ve 19. bayt = 2). Yalnız `mode=ro` ile açmak `data/` içinde `-wal`/`-shm` yan dosyası oluşturabilirdi.

**Gerçek dosyanın değişmediğinin kanıtı:** SHA-256 önce ve sonra aynı (`7900fbed4d5c9d1295e74a1b3369c895a7f5f02dcf9d8c7b217744e7d558ff4c`). Boyut 1.052.672 bayt. Dosyanın ve `data/` klasörünün değiştirilme zamanı aynı kaldı, yan dosya oluşmadı. Kopyada `integrity_check = ok`, `foreign_key_check` sıfır sorun. Kopya yalnız Python'un `sqlite3` modülüyle, salt okunur okundu. Bu bilgisayarda `sqlite3` komut satırı aracı kurulu değil.

**PRAGMA user_version = 6**

| Tablo | Satır |
|---|---:|
| beach_records | 159 |
| destination_weather_anchors | 3 |
| destinations | 1 |
| entities | 0 |
| entity_sources | 0 |
| jobs | 9 |
| metadata | 1 |
| regions | 13 |
| restaurant_records | 138 |
| restaurant_regions | 141 |
| source_history | 4 |
| source_runs | 6 |
| sources | 8 |
| weather_alert_anchors | 0 |
| weather_alerts | 0 |
| weather_forecast_periods | 1020 |
| weather_locations | 6 |

`collections` bir tablo değil, uyumluluk görünümüdür (3 satır).

**destinations:** 1 kayıt — `30a` · 30A · South Walton, Florida · etkin · sıra 0 · oluşturma 2026-09-30 23:21 UTC.

**sources (8):**

| Ad | URL | Yöntem | Etkin |
|---|---|---|---|
| 30A · Bölge rehberi | https://30a.com/ | Belirlenecek | evet |
| National Weather Service | https://www.weather.gov/ | Belirlenecek | evet |
| South Walton · Etkinlikler | https://www.visitsouthwalton.com/events/ | Belirlenecek | evet |
| South Walton · Plaj erişimleri | https://www.visitsouthwalton.com/beach-bay-access-locations/ | JSON | evet |
| South Walton · Restoranlar | https://www.visitsouthwalton.com/listings/culinary-experiences/ | HTML | evet |
| South Walton · Ulaşım | https://www.visitsouthwalton.com/listings/transportation/ | Belirlenecek | evet |
| Visit South Walton | https://www.visitsouthwalton.com/ | Belirlenecek | evet |
| MANUEL TEST KAYNAĞI - DÜZENLENDİ | https://example.com/30a-manuel-test | Belirlenecek | hayır (arşivde) |

National Weather Service kaydının yöntem alanı gerçek veritabanında hâlâ "Belirlenecek". Yeni kurulumda bu alan "API" olarak yazılıyor (Adım 4'teki geçici veritabanında öyle). Bu, yönetici notundaki gözlemle aynıdır; arayüz bağlı toplayıcının yöntemini gösterdiği için ekranda sorun yaratmaz.

**source_runs (6):** hepsi başarılı (`done`). Başarısız, iptal edilmiş veya yarıda kalmış çekim yok.

| Connector (sürüm) | Durum | Başlangıç (UTC) | Kayıt | Kapsam dışı |
|---|---|---|---:|---:|
| south-walton-beaches/1 | done | boş (v0.2'den taşınan eski çekim; çekim zamanı 2026-09-29 21:08) | 53 | 17 |
| south-walton-beaches/2 | done | 2026-09-29 22:02:05 | 53 | 17 |
| south-walton-beaches/2 | done | 2026-09-29 23:07:58 | 53 | 17 |
| nws-weather/1 | done | 2026-09-30 03:52:28 | 510 | 0 |
| nws-weather/1 | done | 2026-09-30 04:10:48 | 510 | 0 |
| south-walton-restaurants/1 | done | 2026-09-30 17:48:05 | 138 | 0 |

**Her connector'ın son başarılı çekimi** (`fetched_at`):

| Connector | Başarılı çekim | Son çekim |
|---|---:|---|
| south-walton-beaches | 3 | 2026-09-29 23:07:59 UTC (30 Eylül 02:07 TSİ) |
| nws-weather | 2 | 2026-09-30 04:10:49 UTC (30 Eylül 07:10 TSİ) |
| south-walton-restaurants | 1 | 2026-09-30 17:49:44 UTC (30 Eylül 20:49 TSİ) |

`jobs` tablosundaki 9 işin hepsi bitmiş durumda (6 veri toplama + 3 katalog kontrolü); hiçbirinde hata teşhis kaydı yok. Bu sayılar v0.6 belgelerindeki ve yönetici notlarındaki sayılarla birebir aynı.

## Adım 4 — Canlı kontrol (geçici veri klasöründe)

**Komut:** `.venv\Scripts\python.exe -X utf8 -m studio --data-dir work\gorev-01\temp-data --no-browser --port 8831`

`-X utf8` eklendi. Bu bilgisayarın Windows kod sayfası 936'dır (Çince GBK). Çıktı bir dosyaya yönlendirildiğinde uygulama, açılış mesajındaki "ç" harfi yüzünden `UnicodeEncodeError` vererek açılmadan kapanıyor. Bu, ayrı bir deneme klasöründe doğrulandı. `baslat.bat` zaten `-X utf8` kullandığı için kullanıcının normal açılışında sorun yok.

Geçici klasörde yeni bir veritabanı oluştu (şema 6, 7 başlangıç kaynağı). Üç kaynak API üzerinden (`POST /api/jobs`, gövde `{"kind":"source_collection","source_id":…}`, başlık `X-Studio-Request: 1`) sırayla toplandı; her iş bitmeden sonraki başlatılmadı.

| Kaynak | Durum | Kayıt | Kapsam dışı | Süre | Hata |
|---|---|---:|---:|---:|---|
| South Walton · Plaj erişimleri | done | 53 | 17 (kaynakta toplam 70 nokta) | 1,2 sn | yok |
| National Weather Service | done | 510 (42 dönem + 468 saatlik, 3 nokta) | 0 | 6,0 sn | yok |
| South Walton · Restoranlar | done | 138 | 0 | 94,2 sn | yok |

Süre, çekimin başlangıç ve bitiş zamanı arasındaki farktır. Çekimler 6 Ekim 2026 22:59–23:01 UTC (7 Ekim 01:59–02:01 TSİ) arasında yapıldı. Hata olmadığı için teşhis kaydı (`jobs.diagnostic`) boş.

Bu çekime ait ek gözlemler:

- Plaj kaynağının kendi güncelleme metni: "Sep 21, 2026 6:56:10 pm". Kaynak saat dilimi vermiyor.
- NWS: çekim anında 1 aktif uyarı vardı: "Rip Current Statement" (Moderate), NWS Tallahassee, 6 Ekim 03:16 EDT – 7 Ekim 04:00 EDT, alan "South Walton; Coastal Bay; Coastal Gulf; Coastal Franklin". Uyarı üç noktaya da bağlandı. Bu canlı bir güvenlik bildirimi değil, o çekim anının kaydıdır.
- Restoranlar: 22 liste sayfası ve 138 detay sayfası okundu, 3 tekrar tekilleştirildi. 13 mahallenin hepsi temsil ediliyor; 22 farklı mutfak türü var; 2 restoranda açıklama yok (Beignets & Brew, Cajun Corner Sports Bar and Grill). Mahalle başına sayılar M4 belgesindeki 30 Eylül tablosuyla aynı.
- Gerçek veritabanındaki son sürümle karşılaştırma (uygulamanın kendi karşılaştırma alanlarıyla): plajlarda 0 eklenen, 0 çıkan, 0 değişen, 53 aynı. Restoranlarda kimlik kümesi aynı (138); 6 kayıt değişmiş (4'ünde web sitesi adresi, 2'sinde açıklama metni), 132 kayıt aynı.
- İş bitince uygulama Ctrl+Break sinyaliyle kapatıldı. 8831 portu boşaldı, geride süreç kalmadı. Geçici veriler `work/gorev-01/temp-data/` altında duruyor ve repoya gitmiyor.

## Adım 5 — Veri dökümü

Dosyalar `docs/gorevler/GOREV-01/` altında. Biçim: UTF-8 (BOM yok), virgülle ayrılmış; liste hücrelerinde ayraç "|". Değerler kaynağın özgün (İngilizce) etiketleriyle yazıldı, çeviri yapılmadı. Kaynak: Adım 4'teki geçici çekim (plaj çekimi `fecf901e66524ccba558ba00dbec5e87`, restoran çekimi `110a56a6c6aa45c18634d37148362102`). Uygulama kodu değişmedi; döküm `work/gorev-01/csv_dokum.py` betiğiyle yapıldı.

| Dosya | Satır | Sütunlar |
|---|---:|---|
| `plajlar.csv` | 53 | external_id, ad, city, adres, enlem, boylam, erisim_turu, olanaklar |
| `plajlar-kapsam-disi.csv` | 17 | external_id, ad, city, tur, enlem, boylam |
| `restoranlar.csv` | 138 | external_id, ad, kaynak_mahalleler, adres_satiri, adres_satiri_2, sehir, posta_kodu, mutfak_turleri, ogunler, olanaklar, web_sitesi_var_mi, aciklama_var_mi |

- **Plajlar** batıdan doğuya (boylama göre) sıralı. Kaynaktaki yerleşim adı dağılımı: Santa Rosa Beach 44, Inlet Beach 6, Seacrest 2, Grayton Beach 1. Erişim türü: neighborhood 44, regional 9. 24 erişimde olanak hücresi boş; bu "kaynakta listelenmemiş" demektir, "yok" demek değildir.
- **Kapsam dışı noktalar** aynı çekimin ham HTML'indeki `initMarkers` verisinden, mevcut ayrıştırıcının deseni ve kapsam kuralı kullanılarak okundu. Ham dosyanın SHA-256'sı çekim kaydındakiyle aynı. 70 nokta = 53 kapsam içi + 17 kapsam dışı; ham dosyadan çıkan kapsam içi kimlikler veritabanındakilerle birebir aynı. Dağılım: Santa Rosa Beach/bays-lakes 7; Miramar Beach 8 (neighborhood 4, regional 2, bays-lakes 2); Grayton Beach/bays-lakes 1; Inlet Beach/bays-lakes 1.
- **Restoranlar:** istenen sütunlara ek olarak `adres_satiri_2` sütunu konuldu, çünkü 43 restoranda kaynak ikinci bir adres satırı veriyor (ör. "Ste 101", "Unit H"); bu sütun olmasa bilgi kaybolurdu. 3 restoran birden fazla mahallede listeleniyor. Web sitesi olmayan 2, açıklaması olmayan 2 kayıt var. Boş mutfak, öğün ve olanak hücreleri (sırasıyla 43, 42, 57 kayıt) yine "kaynakta listelenmemiş" anlamındadır.
- Bir kayıtta adres ayrıştırması beklenmedik: "Canopy Road Café" için ikinci adres satırında "Inlet Beach, FL" yazıyor, şehir ve posta kodu boş. Kod değiştirilmedi; karar konusu olarak aşağıda.

## Adım 6 — Belgeler

`devir-claude-code` dalı, `origin/v0.7-lodging-inventory` HEAD'inden (`23905962126ba9f00f7f8b6223c67c9633e70c2c`) açıldı.

**Belge commit'i:** `e118f9d2b0f58bf5903b8742eef196a8480ccf47`

- Kökteki eski `CALISMA_MANTIGI.md`, `git mv` ile `docs/TEKNIK-CALISMA-MANTIGI-v0.6.md` oldu. İçerik aynı: iki dosyanın git blob kimliği aynı (`cceaa69212c458318506f884ec3f62b2b4ca762a`).
- Köke devir paketindeki `CALISMA_MANTIGI.md` kondu. Yalnız 13. bölüm ("Geliştirme çalışma biçimi") yeni düzene göre yeniden yazıldı: proje yöneticisi görevi yazar → kullanıcı Claude Code'a taşır → Claude Code uygular, test eder, kendi dalına push eder ve rapor yazar → yönetici commit'i ve raporu inceler, gerekirse düzeltme görevi verir → dal kullanıcının onayıyla main'e alınır. Belgedeki tek ChatGPT / "kodlama ajanı" atfı bu bölümdeydi. "Codex" sözcüğü yalnız gerçek yerel klasör yolunda geçiyor; yol olduğu için değiştirilmedi. Belgenin geri kalanı paketle aynı.
- `docs/DEVIR/` altına 01–07 kondu. 01, 02, 03, 05, 06 ve 07 paketle birebir aynı. 04'te çalışma modeli akışı ve açıklaması aynı yeni düzene göre yazıldı; "Code tarafı" ifadesi "Claude Code" yapıldı. 04'teki `CodexSandboxOffline` notu geçmişteki dosya sahipliğini anlattığı için korundu.
- `docs/KONSEPT.md` paketle birebir aynı (blob `c59b8e99f1b6e0a396887818561111d065e73abb`).
- `README.md` "Belgeler" listesine KONSEPT, `docs/DEVIR/` ve taşınan teknik belge bağlantıları eklendi; `CALISMA_MANTIGI.md` bağlantısı yerinde kaldı.
- `.gitignore` dosyasına `work/` satırı eklendi.
- Köke `CLAUDE.md` yazıldı (31 satır): proje ve okuma sırası, çalışma düzeni, veri güvenliği, test, veri dili, mimari sınır ve bu bilgisayara özel `-X utf8` notu.
- Uygulama kodu, testler, şema ve `data/` değişmedi. Paketteki `DEVIR_PAKETI_OKU.md` görevde istenmediği için repoya konmadı.

**CI sonucu:** GitHub Actions "Tests" iş akışı, çalıştırma `37544640691` — **başarılı** (6 Ekim 2026 23:06 UTC, yaklaşık 33 sn). Kurulum, pytest ve arayüz testi adımlarının hepsi başarılı. Bağlantı: https://github.com/bemonths/tatilya/actions/runs/37544640691

CI'daki iki not: (1) bilinen uyarı — Node.js 20 hedefleyen action'lar (`actions/checkout@v4`, `actions/setup-node@v4`, `actions/setup-python@v5`) Node.js 24 üzerinde çalıştırılıyor; (2) yeni bilgi notu — `ubuntu-latest` etiketi 19 Ekim 2026'dan itibaren Ubuntu 26'ya geçecek. CI günlüğü oturum açmadan okunamadığı için test sayıları buraya yerel çalıştırmadan yazıldı; CI'da iki test adımı da başarılı bitti.

## Adım 7 — Teslim

İkinci commit `docs/gorevler/GOREV-01/` klasörünü ekler: `GOREV.md` (`work/gorevler/GOREV-01.md` dosyasının birebir kopyası), bu `RAPOR.md` ve üç CSV. Push etmeden önce `git status` ile `work/` (veritabanı kopyası, geçici veri klasörü, betikler) ve `data/` klasörünün sahnede olmadığı kontrol edildi. İkinci commit'in kimliği kullanıcının yöneticiye ileteceği satırda yer alır.

## Beklenmeyen durumlar

1. Konaklama keşfi klasörleri repoda veya `outputs` içinde değil, `outputs` klasörünün yanındaki `work\` klasöründe çıktı.
2. Bilgisayarın kod sayfası 936 (Çince GBK). Python çıktısı dosyaya yönlendirildiğinde Türkçe karakterler hata veriyor; bu görevde `-X utf8` ile çalışıldı ve CLAUDE.md'ye not edildi.
3. Gerçek veritabanı WAL kipinde; `data/` içinde yan dosya oluşmasın diye salt okunur açılışa `immutable=1` eklendi.
4. Taşınan teknik belgenin (`docs/TEKNIK-CALISMA-MANTIGI-v0.6.md`) içindeki 6 göreli bağlantı artık kırık: `docs/MIMARI.md`, `docs/ASAMALAR.md`, `docs/M2-VERI-TOPLAMA.md`, `docs/M3-HAVA-VERISI.md`, `docs/M4-RESTORAN-VERISI.md`, `docs/M5-DESTINASYON-KATMANI.md`. Belge `docs/` içine taşındığı için bu yollar `docs/docs/...` olarak çözülüyor. Görev "içeriği değişmesin" dediği için düzeltilmedi.
5. `docs/M2-VERI-TOPLAMA.md` ve `docs/MIMARI.md`, teknik ayrıntı için `../CALISMA_MANTIGI.md` dosyasına bağlanıyor. Bu bağlantılar artık yeni ana devir belgesine gidiyor; o ayrıntılar ise taşınan teknik belgede.
6. "Canopy Road Café" restoran kaydında adres alanları beklenen yere yazılmamış (Adım 5).
7. Gerçek veritabanında National Weather Service kaynağının yöntem alanı hâlâ "Belirlenecek" (Adım 3).

## Yöneticinin karar vermesi gereken konular

1. **Kırık bağlantılar:** `docs/TEKNIK-CALISMA-MANTIGI-v0.6.md` içindeki 6 bağlantı düzeltilsin mi? `docs/M2-VERI-TOPLAMA.md` ve `docs/MIMARI.md` içindeki `../CALISMA_MANTIGI.md` bağlantıları taşınan teknik belgeye çevrilsin mi?
2. **Belge indeksi:** Kökteki `CALISMA_MANTIGI.md` belgesinin 16. bölümü `docs/KONSEPT.md` ve taşınan teknik belgeyi listelemiyor. Görev 13. bölüm dışını değiştirmeyi yasakladığı için eklenmedi. Eklensin mi?
3. **Gerçek veritabanının güncelliği:** Gerçek veri 30 Eylül'den beri yenilenmedi. Bugünkü kontrolde plajlar aynı, restoranlarda 6 küçük değişiklik var, hava tahmini doğası gereği eskidi. Kullanıcı uygulamadan yeni çekim yapsın mı? (Bu normal kullanımdır ve gerçek veritabanına yeni sürüm ekler.)
4. **NWS yöntem alanı:** Gerçek kayıttaki "Belirlenecek" değeri küçük bir onarım göreviyle "API" yapılsın mı?
5. **Eski `work\` klasörü:** `outputs` klasörünün yanındaki yaklaşık 35 MB'lık klasör M6 keşfinin yerel kanıtlarını ve gerçek veritabanının eski kopyalarını (`v06-user-copy\`) içeriyor. Olduğu yerde mi kalsın, repo içindeki `work/` altına mı alınsın, yoksa arşivlensin mi?
6. **CSV sütunu:** `restoranlar.csv` dosyasına eklenen `adres_satiri_2` sütunu uygun mu?
7. **Restoran adres ayrıştırması:** "Canopy Road Café" örneği için ileride bir düzeltme görevi açılsın mı?
8. **Bağımlılık ve CI bakımı:** Test uyarısı (`httpx` yerine `httpx2` önerisi), Node 20 action uyarısı ve 19 Ekim'deki Ubuntu 26 geçişi için bir bakım görevi planlansın mı?

## Repoya gitmeyen yerel dosyalar

`work/gorev-01/` altında: `db-kopya.sqlite3` (gerçek veritabanının kopyası), `temp-data/` (geçici çekim), betikler (`db_kopya.py`, `db_rapor.py`, `canli_kontrol.py`, `csv_dokum.py`) ve kanıt çıktıları (`pytest-cikti.txt`, `node-test-cikti.txt`, `db-kopya-sonuc.json`, `db-rapor.json`, `canli-sonuc.json`, `csv-dokum-sonuc.json`, `gercek-vs-gecici-fark.txt`, `ci-runs.json`, `ci-jobs.json`).
