# GÖREV-02 Raporu — Karar düzeni, bakım ve ilk video için kaynak keşfi

Tarih: 7 Ekim 2026 · Dal: `gorev-02-kaynak-kesfi` · A bölümü commit'i: `3d8be98bbb312ff20742fd80b95295a5719063b0` (CI başarılı) · B bölümü ve bu rapor ikinci commit'tedir.

Saatler aksi yazılmadıkça UTC'dir.

## Kısa özet

- **A1 yapılamadı.** main'i devir dalına fast-forward ile alıp push etmek istendiğinde bu bilgisayardaki Claude Code izin sistemi işlemi engelledi. Hiçbir şey zorlanmadı; main değiştirilmedi.
- A2–A7 tamamlandı. Görev dalı, main'in A1'de taşınacağı commit'in (`d41a48e`) üzerinden açıldı. Karar yetkisi kuralları, konaklama kararı, belge bağlantıları ve CI bakımı tek commit'te; CI başarılı (ubuntu-24.04, v7 action'lar, hiç uyarı yok). Yerel testler: 289 Python + 19 arayüz testi geçti.
- B: on soru alanı için 30 aday kaynak değerlendirildi. Güçlü ve resmî kaynaklar: Visit South Walton mahalle dizini, Walton County Ordinance 2025-22, NOAA iklim normalleri, NHC HURDAT2 ve FAA havalimanı verisi. Zayıf alanlar: konaklama fiyatı, aylık kalabalık göstergesi ve plaj erişimi → mahalle eşlemesi (53 erişimin 9'u).
- Ayrıntı: `KAYNAK-KESFI.md`, `kaynaklar.csv`, `plaj-mahalle-onizleme.csv`. Görev metni `GOREV.md` olarak bu klasöre kopyalandı.

## A bölümü — Düzen ve bakım

### A1 — Devir dalını main'e alma: yapılamadı

Ön kontrol yapıldı: `git fetch` sonrası `origin/main` = `a938367`, `origin/devir-claude-code` = `d41a48ec400a90ab52987353218cf264fec92605`; `a938367` devir dalının atası olduğu için fast-forward teknik olarak mümkündü (main'e 4 commit gelecekti: v0.7 konaklama keşfinin iki belge commit'i ve GÖREV-01'in iki commit'i).

`git merge --ff-only` ve `git push origin main` çalıştırılmak istendiğinde Claude Code'un izin sistemi işlemi engelledi (gerekçe: istenmemiş/incelenmemiş main değişikliği). Komut çalışmadı. Talimat gereği hiçbir şey zorlanmadı ve aynı sonuca başka bir yoldan gidilmedi; main ile ilgili sonraki salt okunur kontrol de aynı engel nedeniyle çalıştırılamadı. Bu yüzden main'in deneme öncesindeki konumunda (`a938367`) kaldığı varsayılıyor ve **main üzerinde yeni bir CI çalışması yok**.

Bu adımın tamamlanması için ya kullanıcının bu bilgisayarda Claude Code'a main'e push izni vermesi (izin istendiğinde onaylaması ya da Claude Code ayarlarına bir izin kuralı eklemesi), ya da fast-forward'ın GitHub'da yapılması gerekiyor.

### A2 — Yeni dal

`gorev-02-kaynak-kesfi`, main güncellenemediği için main'in A1'de taşınacağı commit'ten, yani `d41a48ec400a90ab52987353218cf264fec92605` üzerinden açıldı. main bu commit'e fast-forward edildiğinde dal doğrudan main'in üstünde durur; ek birleştirme gerekmez.

### A3 — Karar yetkisi kuralları

Yeni düzenin özü her yere aynı anlamla yazıldı: teknik kararlar ve main'e alma kararı proje yöneticisinindir; Claude Code main'e yalnız görev metni açıkça istediğinde alır; kullanıcı makale aşamasına kadar karar vermez ve ondan onay ya da manuel test istenmez; gerçek ortamda gereken arayüz ve canlı kontrolleri Claude Code kendisi yapar (gerekirse ekran görüntüsüyle).

| Belge | Değişen yer |
|---|---|
| `CLAUDE.md` | "Çalışma düzeni"ndeki main'e alma cümlesi |
| `CALISMA_MANTIGI.md` | 13. bölüm 7. ve 8. maddeler ve bölümün son cümlesi; 15. bölüm 11. kural |
| `docs/DEVIR/04_GELISTIRME_TEST_RELEASE_AKISI.md` | Çalışma modeli akışındaki manuel kabul ve merge satırları; "Branch disiplini"ndeki "kullanıcı kabulü"; "Kullanıcı manuel testleri" bölümü "Claude Code'un gerçek ortam kontrolleri" olarak yeniden yazıldı; kontrol listesindeki "user critical smoke" |
| `docs/DEVIR/06_ROADMAP_VE_ACIK_KONULAR.md` | En üstteki domain seçimi cümlesi (yönetici kararı) |
| `docs/DEVIR/07_YENI_AI_BASLANGIC_TALIMATI.md` | "Main'e merge" bölümündeki cümle |

Liste dışında tek bir cümle daha değişti: `04` belgesinin aynı "Çalışma modeli" bölümünde GÖREV-01'de benim eklediğim "kullanıcı … main'e alma kararını verir" ifadesi yeni kuralla doğrudan çeliştiği için "makale aşamasına kadar karar vermez" olarak düzeltildi. Liste dışında kalan ve değiştirilmeyen ifadeler karar konuları bölümünde.

### A4 — Konaklama kararı

`CALISMA_MANTIGI.md` 10. bölümün sonuna ve `docs/DEVIR/06` içindeki "Şu anki açık konu: lodging" bölümünün başına tarihli not eklendi: tarihten bağımsız tam envanter şartı kaldırıldı; konaklama, belirli tarihler için yapılan Book>Direct aramalarının etiketli anlık görüntüleri olarak modellenecek (arama tarihi, giriş/çıkış, misafir sayısı, mahalle filtresi, dönen kayıtlar, kaynağın fiyat alanları); bu veri hiçbir yerde tam envanter diye adlandırılmayacak. `06`'daki notun sonuna, bölümün geri kalanının kararın öncesini anlattığı belirtildi. 15. bölümün 12. kuralı değişmedi.

### A5 — Belge bağlantıları

- `docs/TEKNIK-CALISMA-MANTIGI-v0.6.md` içindeki 6 kırık bağlantı (`docs/MIMARI.md`, `docs/ASAMALAR.md`, `docs/M2…`, `M3…`, `M4…`, `M5…`) belgenin yeni konumuna göre düzeltildi; metnin geri kalanı değişmedi. Hedef dosyaların hepsinin var olduğu kontrol edildi.
- `docs/M2-VERI-TOPLAMA.md` ve `docs/MIMARI.md` içindeki teknik ayrıntı atıfları (`MIMARI.md`'deki düz metin atıf dahil) `docs/TEKNIK-CALISMA-MANTIGI-v0.6.md`'ye çevrildi.
- `CALISMA_MANTIGI.md` 16. bölümdeki indekse `docs/KONSEPT.md`, `docs/TEKNIK-CALISMA-MANTIGI-v0.6.md` ve `docs/gorevler/` eklendi.

### A6 — CI bakımı

`.github/workflows/tests.yml`: `runs-on` `ubuntu-24.04` olarak sabitlendi; Python 3.12 ve Node 22 ayarları aynı kaldı. Action sürümleri GitHub'daki resmî sürüm sayfalarından ve her sürümün `action.yml` dosyasından doğrulandı:

| Action | Eski | Yeni | Doğrulanan en güncel sürüm | Çalışma ortamı |
|---|---|---|---|---|
| actions/checkout | v4 | v7 | v7.0.1 (2026-07-20) — https://github.com/actions/checkout/releases | `node24` |
| actions/setup-python | v5 | v7 | v7.0.0 (2026-07-20) — https://github.com/actions/setup-python/releases | `node24` |
| actions/setup-node | v4 | v7 | v7.0.0 (2026-07-14) — https://github.com/actions/setup-node/releases | `node24` |

Sürüm notlarında bu iş akışını etkileyen bir kırıcı değişiklik görülmedi (checkout v7 yalnız `pull_request_target`/`workflow_run` olaylarında fork checkout'unu engelliyor; setup-python v7 kullanılmayan `pip-install` girdisini kaldırdı).

### A7 — Commit ve CI

- Commit: `3d8be98bbb312ff20742fd80b95295a5719063b0` (A3–A6, tek commit), `gorev-02-kaynak-kesfi` dalına push edildi.
- Yerel testler: `.venv\Scripts\python.exe -m pytest -q` → 289 geçti (bilinen 1 Starlette uyarısı); `node --test tests/frontend.test.mjs` → 19 geçti.
- CI: "Tests" çalıştırması `37547214694` — **başarılı** (23:33:32–23:34:02). Çalıştırıcı etiketi `ubuntu-24.04`; checkout/setup-python/setup-node v7 adımları, kurulum, pytest ve arayüz testleri başarılı. GÖREV-01'deki Node 20 uyarısı ve Ubuntu 26 notu artık yok (0 not). https://github.com/bemonths/tatilya/actions/runs/37547214694

## B bölümü — Kaynak keşfinin kısa özeti

| # | Soru alanı | En iyi kaynak | Değerlendirme |
|---|---|---|---|
| 1 | Mahalleler | Visit South Walton mahalle dizini (16 mahalle; programın 13'ü ad ve sırayla birebir) | kullanılabilir |
| 2 | Plaj erişimi → mahalle | Visit South Walton park ve ulaşım rehberi (2023): 9/53 erişim eşlendi; Rosemary Beach ve Alys Beach "halka açık erişim yok" | sınırlı |
| 3 | Plaj kuralları | Walton County Ordinance 2025-22 (24 Kasım 2025) + SWFD bayrak/ateş kuralları | kullanılabilir |
| 4 | İklim | NOAA NCEI 1991–2020 normalleri (Destin istasyonu, 30A'ya ~32 km) | kullanılabilir |
| 5 | Kasırga riski | NOAA NHC HURDAT2 (1851–2025) | kullanılabilir |
| 6 | Kalabalık ve sezon | Walton County Tourism aylık turist vergisi tahsilatları | sınırlı |
| 7 | Konaklama ve fiyat | Book>Direct tarihli arama | sınırlı |
| 8 | Ulaşım | FAA havalimanı verisi (kuş uçuşu mesafe) + Visit South Walton rehberi + mevzuat | kullanılabilir / sınırlı |
| 9 | Yapılacaklar | Visit South Walton Events | kullanılabilir (etkinlik) |
| 10 | Günlük ihtiyaç | OpenStreetMap (Overpass) | sınırlı |

Öne çıkan bulgular:
- **Konaklama fiyatı (Alan 7):** Kaynağın kendi arayüz metinleri alanların anlamını netleştirdi: `average_rate` gecelik ortalama, USD (CAD/EUR/MXN karşılıklarıyla), en düşük müsait günlük fiyata dayanıyor, garanti değil; vergi ve ücretlerin dahil olup olmadığı hiçbir yerde yazmıyor. Misafir sayısı parametresi yok (yalnız `min_sleeps`+`max_sleeps` kapasite filtresi). `los` minimum konaklama gecesi. Fakat 17–24 Ekim 2026 örneğinde Dune Allen'ın 112 kaydının hiçbirinde, Seaside ve Rosemary Beach'in ilk 50'şer kaydında da liste fiyatı yoktu. Fiyatı olan tek örnekte (`rates.json`) günlük takvim döndü. Dört sezonluk örnek tarih seti önerildi (Cumartesi–Cumartesi 7 gece).
- **Plaj erişimi → mahalle (Alan 2):** Erişim başına mahalleyi bütün erişimler için veren resmî kaynak yok; turizm kurumunun park rehberi bölgesel erişimlerin çoğunu mahalle başlıkları altında veriyor. Buna göre `plaj-mahalle-onizleme.csv`'de 53 satırın 9'u dolduruldu; diğerleri boş bırakıldı (tahmin yok).
- **İklim (Alan 4):** 30A içinde iklim istasyonu yok; hazır bir nem normali ve deniz suyu normali yok (NCEI'nin kıyı suyu rehberi Mayıs 2025'te kapatılmış). Deniz suyu için en yakın resmî ölçüm Panama City Beach istasyonu (PCBF1).
- **Kurallar (Alan 3):** Yönetmelik taranmış PDF; kurallar elle bölüm numaralı tabloya alınmalı. Cankurtaran sezonu kaynaklar arasında çelişkili (1 Mart–30 Eylül / 1 Mart–31 Ekim).

## Beklenmeyen durumlar

1. **A1 izin engeli** (yukarıda).
2. **Book>Direct:** fiyat alanları örneklerde boştu; aktivite servisi (`venues.json`) bu ön yüz için 0 kayıt döndürüyor; konum filtresi listesindeki "Seacrest" koordinatı Florida'nın doğu kıyısını gösteriyor (kaynak yapılandırmasında hata). Ön yüz sürüm yolu 30 Eylül ile 6 Ekim arasında değişti.
3. **Anahtarlar:** Book>Direct paketi, istemci anahtarına ek olarak bir uçuş widget'ına ait başka bir herkese açık anahtar da içeriyor. Bu ikinci değer ilk kod-parçası dosyasına maskelenmeden girdi; birkaç dakika içinde maskelenip dosya yeniden yazıldı. Dosya yalnız yerel `work/` klasöründeydi, repoya gitmedi. Book>Direct istemci anahtarı hiçbir dosyaya yazılmadı (kaydedilen bütün dosyalar tarandı).
4. **Resmî bir sitenin herkese açık ön yüz kodunda** kimlik bilgisi benzeri bir değer görüldü. Kullanılmadı, kaydedilmedi; ilgili dosya silindi. Herkese açık repoya ayrıntı yazılmadı; yerel not `work/gorev-02/GUVENLIK-NOTU.md` (repoya gitmez).
5. **Ağ ve erişim:** `floridarevenue.com` alan adı bu bilgisayardan keşif boyunca çözülemedi (DNS). `mywaltonfl.gov` aralıklı HTTP 522 verdi (üçüncü denemede açıldı). Repo `.venv` Python'u iki sitede "certificate has expired" TLS hatası verdi, Windows curl aynı siteleri doğruladı; ileride Python ile yazılacak bağlayıcılar aynı hataya takılabilir.
6. **robots.txt ve bot koruması:** NCEI `/data*` (IBTrACS ve toplu normal dosyaları), fdacs.gov (Point Washington), Walton County Clerk sitesi ve Overpass `/api/` robotlara kapalı; Florida State Parks Cloudflare doğrulamasıyla engelliyor. Visit South Walton'ın robots.txt dosyası biçimsiz (User-agent satırı yok); `/userfiles/` temkinle kapalı sayıldı.
7. **Kaynak çelişkileri:** cankurtaran sezonu (SWFD SSS ↔ turizm sayfası); Seacrest'in konumu (Visit South Walton ↔ OpenStreetMap); Santa Clara RBA (park rehberi Seagrove der, Santa Rosa Beach mahalle sayfası bu erişimi anar); Timpoochee uzunluğu (19 ↔ ~18,5 mil); turizm sayfasındaki bazı kurallar ↔ Ordinance 2025-22.
8. **Terim:** Ordinance 2025-22 "Gulf of Mexico" adını metnin tamamında "Gulf of America" olarak değiştiriyor; İngilizce videoda adlandırma kararı gerekebilir.
9. **Aday sınırı:** Alan 9'da dört alt konu (eyalet parkları, Point Washington, etkinlikler, Book>Direct aktiviteleri) için dört kaynağa bakıldı; Alan 3'te Municode ayrı aday sayılmadı, yönetmeliğin bir kanalı olarak değerlendirildi.

## Yöneticinin karar vermesi gereken konular

1. **A1:** main'e fast-forward nasıl yapılacak — kullanıcı bu bilgisayarda Claude Code'a izin mi verecek, yoksa işlem GitHub'da mı yapılacak?
2. **Bağlama sırası:** `KAYNAK-KESFI.md` sonundaki öneri (mahalle profili → iklim ve kasırga → plaj-mahalle ve kural tablosu → konaklama pilotu → etkinlik ve sezon → ulaşım ve günlük ihtiyaç).
3. **Plaj erişimi → mahalle:** kalan 44 erişim için Walton County TDC'den resmî liste mi istenecek, yoksa program kendi mahalle sınırlarını tanımlayıp sonucu "program türetimi" diye mi etiketleyecek?
4. **Konaklama:** fiyat doluluğu bu kadar düşükse önerilen tarih setiyle tek seferlik bir pilot mu yapılacak, "yaklaşık maliyet" için başka bir kaynak mı aranacak? Book>Direct kullanım şartları ayrıca kontrol edilmeli.
5. **Aylık kalabalık göstergesi:** turist vergisi tahsilatlarının yüklendiği veri ucu için kısa bir ek keşif mi, tarayıcı otomasyonu mu (Playwright varsayılan değil)?
6. **robots.txt politikası:** NCEI `/data*`, Overpass `/api/` ve Visit South Walton `/userfiles/` için nasıl davranılacağı; Overpass yerine bölgesel OSM extract kullanılması.
7. **Elle tutulacak referanslar:** eyalet parkı ücret/saatleri, Point Washington ücretleri ve plaj kuralları otomatik toplanamıyor; elle, erişim tarihiyle ve yıllık yeniden kontrolle tutulması öneriliyor.
8. **Lisans:** OpenStreetMap verisinden türetilecek ve yayımlanacak her liste ODbL paylaşım şartı getirir; Visit South Walton ve SWFD metinleri kopyalanamaz (SWFD ticari kullanım için yazılı izin istiyor).
9. **Güvenlik notu:** resmî sitedeki açık kimlik bilgisi için site sahibine bildirim yapılıp yapılmayacağı.
10. **Değiştirilmeyen kullanıcı-kararı ifadeleri:** görev listesinde olmadığı için dokunulmadı: `docs/DEVIR/07` "Geliştirme yöntemi" akışındaki "manual acceptance" adımı ve bölüm sonundaki "kullanıcıya … raporla" ifadesi; `docs/ASAMALAR.md` Aşama 4'teki "kaynaklı brief ve kullanıcı onayı"; `docs/DEVIR/05`'teki "User manual v0.6 smoke" (tarihsel kayıt). Bunlar da yeni düzene göre güncellensin mi?

## Repoya gitmeyen yerel dosyalar

`work/gorev-02/` altında: alan klasörleri (`01-02-mahalle-plaj`, `03-09-kurallar-yapilacaklar`, `04-05-iklim-kasirga`, `06-08-10-sezon-ulasim-ihtiyac`, `07-konaklama`) içinde ham örnekler ve `requests.json` istek kayıtları; `a6-ci` (action sürüm kanıtları); CI ve test çıktıları; birleştirme betikleri ve taslaklar; `GUVENLIK-NOTU.md`.
