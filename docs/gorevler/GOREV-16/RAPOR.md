# GÖREV-16 raporu — eklentinin düzeltilmesi, ABD dışı erişim engeli için kullanıcının ABD proxy'si, GÖREV-15'in küçük düzeltmeleri

Tarih: 11 Ekim 2026 · Dal: `gorev-16-eklenti-proxy` · Uygulama 0.18.0 · Şema 18

## Kısaca

- main, GÖREV-15'in son commit'ine (`6cfab84`) alındı ve `v0.17.0` etiketi kondu. main ve etiket CI başarılı.
- Eklenti artık iş sürerken birkaç saniyede bir programa ne yaptığını söylüyor. Ekranda "Eklenti çalışıyor: <site> · <durum>" yazıyor;
  "Bağlı değil (Chrome kapalı olabilir)" yalnız eklentiden gerçekten haber alınamıyorsa çıkıyor.
- Sayfalar üç türe ayrıldı: doğrulama (kullanıcı geçer), erişim reddedildi (kimse geçemez, beklenmez), bölge engeli (ABD dışından
  gelen ziyaretçiye hizmet yok, beklenmez). Winn-Dixie'de olduğu gibi "Access Denied" sayfasında artık 15 dakika beklenmiyor.
- Başka bir siteye yönlenen sayfa (HCA gibi) "başka siteye yönlendi" ya da "bölge engeli" diye bildiriliyor. Doğrulama beklenirken
  eklenti penceresinde ve İşler panelinde "Bu sayfayı atla" düğmesi var.
- Ayarlar'a "ABD proxy'si (bölge engeli için)" bölümü eklendi. Parola Windows Kimlik Bilgisi Yöneticisi'nde duruyor; ekranda yalnız
  "kayıtlı" görünüyor. "Proxy'yi dene" çıkış adresini ve ülkesini gösteriyor.
- Proxy yalnız bölge engelli listedeki alan adları için kullanılıyor; öbür bütün istekler doğrudan gidiyor. Liste gerçek veride
  kullanıcının 11 Ekim denemesinden kuruldu: cvs.com, publix.com, hcafloridahealthcare.com.
- Video metninde sürümün kullanımı artık yalnız kendi tonunu sayıyor; planın kullanımı ayrı satırda. Seçilen çalışma "seçildi: <ton>"
  diye görünüyor. "I-10", "I-65" artık "I" uyarısı vermiyor.
- Gerçek siteye ve gerçek proxy'ye hiç gidilmedi. Bütün denemeler yerel sayfalar ve yerel sahte proxy ile yapıldı.

## Konumlar, CI ve testler

| | Konum | CI |
|---|---|---|
| GÖREV-15 dalı son commit | `6cfab845c88ebb81e4ef7ae021ba3bb795e7a9f9` | 38097203607 başarılı |
| main (fast-forward `984ca72..6cfab84`, push) | `6cfab845c88ebb81e4ef7ae021ba3bb795e7a9f9` | 38138844974 başarılı |
| Etiket `v0.17.0` (açıklamalı, push) | `6cfab84` — "v0.17.0 — video metni: yazım zinciri, seçilebilir tonlar ve ton yönetimi, karşılaştırma ve program denetimi" | 38138846294 başarılı |
| Görev dalı | `gorev-16-eklenti-proxy` | aşağıda |

| Commit | İçerik | CI |
|---|---|---|
| `7049980` | eklenti düzeltmeleri, sayfa türleri, ABD proxy'si, şema 18, 0.18.0, video metni düzeltmeleri | 38141939845 başarılı |
| `0944107` | belgeler (yeni M18), deneme tablosu ve uçtan uca test düzeltmeleri | 38143256497 başarılı |
| son commit | rapor ve ekran görüntüleri | GitHub'da |

Testler (yerelde, Windows):

| | main (v0.17.0) | Görev dalı |
|---|---|---|
| Python | 1031 | 1078 (1 atlandı: eklentinin isteğe bağlı uçtan uca denemesi) |
| Frontend (Node) | 90 | 95 |

Tam takım art arda 3 kez çalıştırıldı (11 Ekim 2026, 16:27–16:49): üçünde de 1078 Python testi geçti (1 atlandı) ve 95 frontend testi geçti; hata yok. Ara çalıştırmada görülen iki kararsız test düzeltildikten sonra (aşağıda) bir daha düşmedi.

Eklentinin uçtan uca denemesi (`STUDIO_EKLENTI_E2E=1`, Playwright'in Chromium'u, geçici profil, yalnız yerel sayfalar) ayrıca bir kez
çalıştırıldı ve geçti: sıradan sayfa, JavaScript'le çizilen sayfa, kendiliğinden geçen ve geçmeyen doğrulama, giriş sayfası, erişim
reddedildi, bölge engeli, başka siteye yönlenme, geo-block yönlenmesi ve sayfa içi istek.

Yeni testler: `test_page_kinds.py` (sayfa türleri, kullanıcının ham sayfalarından CVS ve Publix, programın kendi tarayıcısı),
`test_extension_16.py` (canlılık, 20/60 sn eşiği, "Eklenti çalışıyor", "Bu sayfayı atla", yeni sonuçlar, deneme tablosu, listedeki
sitenin eklentiye verilmemesi, proxy yokken atlama, proxy'yle okuma, yeni deneme listesi, eski sürüm notu), `test_proxy.py` (adres
doğrulaması, parolanın yalnız kasada durması, günlükte maskelenme, yerel sahte proxy ile "Proxy'yi dene" ve ülke uyarısı, yalnız listedeki
alan adlarını proxy'ye gönderme, liste, ham kayıtlardan ilk satırlar ve 17 → 18 geçişi, okuma sırası, PAC ve komut satırı, CDP kimlik
cevabı, SOCKS5 sınırı, restoran ve kiralama toplayıcıları), `test_text_usage.py` (kullanım hesabı, "seçildi"), `test_text_audit.py`'de
"I-10" testi; Node'da 5 yeni test (eklentinin sayfa türleri aynı fikstürlerle, "Son iş", Ayarlar ekranları, proxy bölümü, video metni).

## Adımların sonucu

### Adım 1 — v0.17.0'ı main'e alma

- 1.1: Görev başında (15:19) program açıktı (8830, kullanıcı açmıştı; çalışan eklenti işi yoktu, son deneme işi iptal edilmişti). Kod
  işine başlandı; program 15:35'ten önce kapanmıştı. Gerçek veri işi program kapalıyken yapıldı.
- 1.2: Çalışma ağacında kullanıcının talimat, ton ya da uyarı ifadesi değişikliği yoktu (git temiz); ayrı commit gerekmedi.
- 1.3: `6cfab84`'ün CI'ı başarılıydı; main fast-forward edildi ve itildi; `v0.17.0` açıklamalı etiketi kondu ve itildi. main ve etiket CI
  başarılı.
- 1.4: `gorev-16-eklenti-proxy` güncel main'den açıldı.

### Adım 2 — Eklentinin düzeltilmesi

- 2a: Eklenti iş sürerken en çok 4–5 sn arayla durumunu bildiriyor (sayfa açılıyor, sayfa okunuyor, doğrulama bekleniyor ve kalan süre,
  bekleme). Program eklentiden gelen her yetkili çağrıyı "görüldü" sayıyor. "Bağlı değil" eşiği iş sürerken 60 sn, iş yokken 20 sn.
  Ayarlar → Tarayıcı eklentisi (5 sn'de bir yenilenir) ve İşler paneli "Eklenti çalışıyor: <site> · <durum>" diyor. Eklenti penceresindeki
  "Son iş" satırı takılı işi ("takılmış görünüyor: N dk'dır ilerlemiyor") söylüyor.
- 2b: Doğrulama / erişim reddedildi / bölge engeli ayrımı tek Python kaynağında (`studio/sources/page_kinds.py`); eklentideki kopyası
  bir testle denetleniyor ve iki taraf aynı fikstürlerde aynı sonucu veriyor. "access denied" başlığı doğrulama listesinden çıktı.
  Programın kendi tarayıcısı ve onu kullanan toplayıcılar da erişim reddedildi ve bölge engelini kullanıcı doğrulamasına göndermiyor.
  CVS ve Publix sayfaları kısaltılarak fikstür oldu.
- 2c: İzin verilmemiş başka bir alan adına yönlenen sayfa "başka siteye yönlendi: <alan adı>" ya da (adreste geo-block varsa) bölge
  engeli olarak dönüyor; Chrome'un izin hata metni artık sonuç olarak yazılmıyor.
- 2d: "Bu sayfayı atla" eklenti penceresinde ve İşler panelinde; basılınca sayfa "kullanıcı atladı" diye kaydediliyor, iş sürüyor.
- 2e: realjoy.com için kalıcı sayfa: `https://www.realjoy.com/beach-rentals/30a-vacation-rentals` (11 Ekim ham kaydının
  bağlantılarından). Deneme tablosunda her sitenin türü ve okuma yöntemi yazıyor.

### Adım 3 — ABD proxy'si

- 3a: Ayarlar → "ABD proxy'si (bölge engeli için)": adres (http, https, socks5; Housing Atlas'ın `proxy_url_error`'ı), kullanıcı adı,
  parola. Parola Kimlik Bilgisi Yöneticisi'nde (hizmet `30AStudio`); alan "kayıtlı" gösteriyor, "Parolayı sil" var. `keyring` (ve socks5
  için `socksio`) bağımlılığa eklendi. Gizli değerler günlükte maskeleniyor. "Proxy'yi dene" çıkış adresini ve ülkesini gösteriyor; ABD
  değilse "Proxy'nin çıkış adresi ABD'de görünmüyor". Kullanıcı adlı SOCKS5 girilirse ekran tarayıcının bu proxy'yle kullanılamayacağını
  söylüyor.
- 3b: Bölge engelli alan adları yeni bir tabloda (`region_blocked_hosts`, şema 18). Program bölge engeli görünce alan adını tarih ve
  sayfanın başlığıyla (ya da engeli gösteren sözle) kendisi ekliyor; kullanıcı Ayarlar'dan ekleyip çıkarabiliyor. İlk satırlar geçişte
  ham kayıtlardan çıktı: cvs.com, publix.com, hcafloridahealthcare.com. Winn-Dixie ve The Fresh Market'in ham kaydı yok (deneme
  Winn-Dixie'de takılıp iptal edilmişti); eklenmediler.
- 3c: Listedeki alan adları için sıra: proxy üzerinden doğrudan istek → (engellenirse ya da sayfa JavaScript'le çiziliyorsa) programın
  kendi tarayıcısı proxy'yle → atla ve kaydet. Eklenti bu alan adları için kullanılmıyor. Programın tarayıcısında yöntem: ayrı profil ve
  süreç ve yalnız listedeki alan adlarını proxy'ye gönderen PAC betiği; proxy kimliği komut satırına yazılmıyor, CDP `Fetch` ile
  veriliyor. Restoran ve kiralama toplayıcıları ve deneme işi bu sıraya uyuyor. Ham kayıtta `yontem` `proxy` ya da `tarayici+proxy` ve
  `proxy: true`; adres yok.
- 3d: Proxy yoksa sayfa hemen atlanıyor ve "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)" yazılıyor; İşler paneli de aynısını
  yazıyor.
- 3e: `CLAUDE.md`'deki tarayıcı kuralına proxy kuralı işlendi; yeni belge `docs/M18-ABD-PROXY-BOLGE-ENGELI.md`, `docs/M16` güncellendi.

### Adım 4 — GÖREV-15'in küçük düzeltmeleri

1. Seçilmiş sürümün çalışması Video metni listesinde "seçildi: <ton adı>" diye görünüyor.
2. Sürümün kullanımı yalnız o tonun oturumlarını sayıyor; planın ve eleştirinin oturumları çalışmanın "plan" satırında bir kez;
   karşılaştırmada sütun başı tonun kullanımını, ekranın üstü planın kullanımını yazıyor; "Bu tonla da yaz" sürümü planın bedelini
   taşımıyor. (GÖREV-15'te yazılmış eski sürümlerin kayıtlı kullanımı planı da içeriyor; onlar yeniden hesaplanmadı.)
3. "I" uyarısı "I" ardından tire ve rakam gelirse ("I-10", "I‑65", "I–10") eşleşmiyor. Testi var.

### Adım 5 — Testler

Görevin listesindeki her madde sınandı (yukarıdaki test dosyaları). Gerçek siteye, gerçek proxy'ye ve Windows Kimlik Bilgisi
Yöneticisi'ne gidilmedi: testlerde bellekte bir kasa, yerel sahte proxy (yalnız 127.0.0.1'e izin veren `local_network` kalıbıyla) ve
yerel sayfalar kullanıldı.

### Adım 6 — Gerçek ortam ve teslim

Aşağıda.

## Geçici klasör denemesi (Adım 6.1)

Klasör `work/gorev-16/deneme` (gerçek verinin kopyası: GÖREV-15 deneme klasörü ve kullanıcının 11 Ekim eklenti ham kayıtları). Program
bu klasörle 8842'de açıldı; Kimlik Bilgisi Yöneticisi yerine bellekte bir kasa kullanıldı (gerçek kasaya dokunulmadı). Yerel sayfalar
(127.0.0.1:8898) ve kullanıcı adı ve parola isteyen, hiçbir isteği dışarı iletmeyen yerel sahte proxy (127.0.0.1:8899) kuruldu. Eklenti
Playwright'in Chromium'unda geçici profille yüklendi ve eşleşti. Programın proxy tarayıcısı da aynı Chromium ve geçici profille açıldı.

| Site | Tür | Durum | Yöntem |
|---|---|---|---|
| sıradan sayfa | tamam | okundu | eklenti |
| geçmeyen doğrulama | doğrulama | kullanıcı atladı (İşler panelindeki "Bu sayfayı atla") | eklenti |
| Akamai biçimli "Access Denied" | erişim reddedildi | beklenmeden atlandı | eklenti |
| CVS biçimli bölge engeli (403) | bölge engeli | proxy'yle okundu | proxy |
| geo-block adresine yönlenme | bölge engeli | proxy'yle okundu | proxy |
| başka siteye yönlenme | başka siteye yönlendi | "başka siteye yönlendi: baska-site.test" | eklenti |
| listede: bolge-ornek.test | bölge engeli | okundu | proxy (doğrudan) |
| listede: bolge-js.test (JavaScript'le çizilen) | bölge engeli | okundu | tarayıcı + proxy (PAC ve CDP kimlik) |

- "Proxy'yi dene" sahte proxy üzerinden çıkış adresini (203.0.113.7) ve ülkeyi (US) gösterdi.
- Sahte proxy yalnız bölge engelli adresleri ve IP servisini gördü; sıradan sayfalar ona hiç gitmedi.
- Doğrulama beklenirken Ayarlar "Eklenti çalışıyor: 127.0.0.1 · doğrulama bekleniyor (kalan 15 dk)" dedi; "Bağlı değil" çıkmadı.
- Parola deneme klasörünün hiçbir dosyasında, günlüklerde ve proxy tarayıcısının profilinde yok; 12 ham kayıtta `proxy: true` var, hiçbirinde
  proxy adresi yok.
- Program yeniden başlayınca bellekteki deneme kasası boşaldı; ilk deneme "Proxy kullanıcı adı yazılmış ama parola kayıtlı değil" diye
  atladı (bu yol da görülmüş oldu). Gerçek kullanımda parola Kimlik Bilgisi Yöneticisi'nde kalıcıdır.
- Video metni: sahte claude ile iki tonlu yeni bir çalışma yazıldı ve bir sürüm seçildi; listede "seçildi: Araştırmacı dost" ve "plan:
  2 oturum …" satırı, karşılaştırmanın üstünde planın kullanımı göründü.

## Geçiş denemesi (Adım 6.2)

Gerçek veritabanının `work/` kopyasında (eklenti ham kayıtlarıyla birlikte): şema 17 → 18; 165.259 satır önce, 165.262 sonra; eski
tabloların hepsi aynı; yalnız yeni `region_blocked_hosts` tablosuna 3 satır (cvs.com, hcafloridahealthcare.com, publix.com);
`integrity_check` ok, `foreign_key_check` boş; uygulamanın kendi yedeği `studio-v17-*.sqlite3` alındı.

## Gerçek veritabanı: önce ve sonra (Adım 6.3)

1. Program kapalıyken `data/` tam yedeği: `work/yedek/20261011-1621/` (45.509 dosya, 1.497.890.499 bayt; kopya ve kaynak SHA-256 ile
   doğrulandı). `keyring` ve `socksio` `.venv`'e kurulduğu için kurulum damgası yazıldı (masaüstü kısayolu yeniden kurulum açmasın diye).
2. Program masaüstü kısayoluyla açıldı (sürüm 0.18.0, port 8830); geçiş çalıştı; uygulamanın kendi yedeği
   `data/backups/studio-v17-223e00b097354032b0eeeebc851de995.sqlite3`.
3. Ayarlar'da "ABD proxy'si (bölge engeli için)" bölümü (tanımsız) ve bölge engelli liste (cvs.com, hcafloridahealthcare.com, publix.com)
   göründü (ekran `10a`). Kullanıcının Chrome'undaki eklenti eski sürümle (0.16.0) bağlandı; Ayarlar yeniden yükleme notunu gösterdi
   (ekran `10b`).
4. Proxy girilmedi; gerçek siteye gidilmedi; toplayıcı çalışmadı.
5. Program penceresinden kapatıldı; kapanma bekçisi programı kapattı; `data/` içinde -wal/-shm kalmadı.

| | Önce | Sonra |
|---|---|---|
| `user_version` | 17 | 18 |
| Eski tabloların satırları | 165.259 | 165.259 (hepsi aynı) |
| `region_blocked_hosts` | — | 3 (cvs.com, hcafloridahealthcare.com, publix.com; "program", 11 Ekim 11:34) |
| `integrity_check` | ok | ok |
| `foreign_key_check` | boş | boş |
| `ayarlar.json`, `eklenti.json` | | değişmedi |

## Housing Atlas'tan taşınanlar

Housing Atlas klasöründe hiçbir dosya değiştirilmedi; `git fetch` sonrası dosyalar `git show origin/main:…` ile okunmak için `work/`
altına kopyalandı.

| Housing Atlas | Burada | Değişen |
|---|---|---|
| `atlas/secrets.py` (keyring, Türkçe hata, değer maskeleme listesine) | `studio/credentials.py` | hizmet adı `30AStudio`, tek gizli bilgi `abd_proxy_parolasi`; modül adı standart kütüphaneyle karışmasın diye `credentials` |
| `atlas/logs.py` (`register_secret`, `mask`, `MaskFilter`, `proxy_label`) | `studio/logs.py` | başka bir tutucunun önceden biçimlediği hata dökümü de maskeleniyor |
| `atlas/config.py` `proxy_url_error` | `studio/proxy.proxy_url_error` | şemalar işçideki gibi http, https, socks5; yol ve sorgu da reddediliyor |
| `atlas/sources/fema.py` `ProxySettings` (etiket, metinden adres ve kimliği çıkarma, httpx proxy) | `studio/proxy.ProxySettings` | httpx mount'larıyla yalnız listedeki alan adları proxy'den |
| `atlas/isci/browser.py` (`_auth_answer`, `ProxyAuth`, CDP `Fetch`, SOCKS5 sınırı, parola yok uyarısı) | `studio/sources/region_reader.py` | `--proxy-server` yerine ayrı profil ve yalnız listedekileri proxy'ye gönderen PAC betiği |
| "Proxy'yi dene" (`/fema/proxy-test`, `read_public_ip`; gizli değer dönmez) | `POST /api/abd-proxy/dene` | ülke de gerektiği için ipify yerine `https://ipinfo.io/json` |
| doğrudan → proxy okuma sırası (`fema.py`, `hesap.py`) | `RegionReader` | bölge engelli listedeki alan adları için proxy → tarayıcı + proxy → atla |

## Gizli bilgi nerede durur, nerede durmaz

| Bilgi | Nerede durur | Nerede durmaz |
|---|---|---|
| Proxy parolası | Windows Kimlik Bilgisi Yöneticisi (`30AStudio` / `abd_proxy_parolasi`); program çalışırken bellekte | `ayarlar.json`, veritabanı, ham kayıtlar, uygulama günlüğü (maskelenir), iş mesajları, API cevapları, Chrome komut satırı, PAC betiği, proxy tarayıcısının profili, depo |
| Proxy adresi (şema, sunucu, port) | `ayarlar.json`; proxy tarayıcısının PAC betiği (sunucu ve port) | ham kayıtlar (yalnız `proxy: true`); ekran ve günlük metinlerinde yalnız `şema://sunucu` |
| Proxy kullanıcı adı | `ayarlar.json` | ham kayıtlar, Chrome komut satırı, PAC betiği |
| Eklentinin eşleşme kodu | `eklenti.json`, eklentinin kendi deposu (değişmedi) | — |

Testlerde gerçek kasa hiç kullanılmadı (bellekte kasa); geçici denemede de bellekte kasa kullanıldı. Kullanıcının proxy bilgileri Claude
Code'a verilmedi ve sorulmadı.

## Kullanıcının görevden sonra yapacakları

1. **Eklentiyi yeniden yükleyin:** Chrome'da `chrome://extensions` sayfasını açın, "30A Studio Yardımcısı"nın üzerindeki yenile (↻)
   düğmesine basın. (Ayarlar → Tarayıcı eklentisi eski sürüm takılıysa bunu söyler.)
2. **Proxy'yi girin:** Programda Ayarlar → "ABD proxy'si (bölge engeli için)": proxy adresi (ör. `http://sunucu:port`), kullanıcı adı ve
   parola → "Kaydet". Parola Windows Kimlik Bilgisi Yöneticisi'ne kaydedilir.
3. **Deneyin:** "Proxy'yi dene"ye basın; ülke "US" görünmeli. Görünmezse uyarı çıkar.
4. **Sorunlu siteleri deneyin:** Ayarlar → Tarayıcı eklentisi → "Sorunlu sitelerden birer sayfa dene". CVS, Publix ve HCA proxy'yle
   denenir; Winn-Dixie ve The Fresh Market eklentiyle denenir, bölge engeli görülürse listeye kendiliğinden girer ve proxy'yle denenir.
   JavaScript'le çizilen bir sayfa için programın proxy tarayıcısı ayrı bir Chrome penceresi açabilir; orada doğrulama çıkarsa siz geçersiniz.

## Beklenmedik durumlar

- **Görev başında program açıktı** (kullanıcı açmıştı). Kod işiyle başlandı; program kısa sürede kapandı, gerçek veri işi program
  kapalıyken yapıldı.
- **GÖREV-15'te bir kez görülen kararsız test bulundu ve düzeltildi.** İki zincir testi zaman zaman düşüyordu: (1) çalışma "karşılaştırma
  bekliyor" olduktan hemen sonra iş henüz "bitti" değildi — artık iş önce bitiyor; (2) yan yana çalışan sahte oturumlar ortak günlük
  dosyasına aynı anda yazarken Windows'ta bir satır kayboluyordu — yazma artık kilitli.
- **Playwright'in Chromium'u (151) eklenti çalışanında `chrome.*` vermiyor ve eklenti penceresinde `eval`'e izin vermiyor.** Uçtan uca test ve
  deneme betiği portu eklenti sayfasından yazacak ve eşleşmeyi Python'dan bekleyecek biçimde uyarlandı (yalnız test tarafı).
- **HCA'nın ham kaydı "hata"ydı** (Chrome'un izin hata metni); geçiş yönlenilen geo-block adresini bu metinden okuyup alan adını listeye
  koydu.
- **Günlük maskeleme:** pytest'in kendi günlük tutucusu hata dökümünü önceden biçimleyince maske atlanıyordu; maske artık önceden
  biçimlenmiş dökümü de kapsıyor.
- Deneme tablosunda proxy'yle okunan bölge engelli satırın türü önce "tamam" görünüyordu; artık görülen tür ("bölge engeli") ve durum
  ("okundu") ayrı sütunlarda.

## Yöneticinin karar vermesi gereken konular

1. **IP servisi:** "Proxy'yi dene" ülke de gösterebilmek için `https://ipinfo.io/json`'u kullanıyor (yalnız kullanıcı düğmeye basınca,
   proxy üzerinden). Başka bir servis istenirse tek satırlık değişiklik.
2. **Bölge engelinin tanınması:** Bir bölge ifadesi tek başına ancak kısa bir sayfada ya da 403/451 cevabında sayılıyor (sıradan
   sayfaların altbilgisi yanlış alarm vermesin diye). Uzun ve 200 dönen bir bölge sayfası kaçabilir; o zaman kullanıcı alan adını
   Ayarlar'dan listeye ekleyebilir.
3. **Winn-Dixie ve The Fresh Market** listede yok (ham kayıt yok). Kullanıcının bir sonraki denemesi bunların bölge engeli mi, erişim
   reddi mi olduğunu gösterecek; bölge engeliyse kendiliğinden listeye girecek.
4. **Günlük ihtiyaç zincir kontrolleri** (CVS, Publix, Winn-Dixie, The Fresh Market, HCA) toplayıcıda canlı okunmuyor, gözden geçirilmiş
   dosyadan geliyor. Proxy'yle okunan sayfalardan bu dosyanın güncellenmesi ayrı bir iş.
5. **SOCKS5 ve kullanıcı adı:** Kullanıcının proxy'si kullanıcı adlı SOCKS5 ise programın tarayıcısı bu proxy'yle açılamaz; yalnız doğrudan
   istekler kullanılır (JavaScript'le çizilen sayfalar okunamaz). Kullanıcının proxy'sinin türü bilinmiyor.
6. **Eski sürümlerin kullanımı:** GÖREV-15'te yazılmış sürümlerin kayıtlı kullanımı planı da içeriyor (gerçek veride metin sürümü yok;
   yalnız deneme klasörlerinde). Yeniden hesaplanmadı.

## Teslim edilenler (bu klasör)

- `GOREV.md` (görev metni), `RAPOR.md` (bu rapor)
- `ekran/`:
  - `01-abd-proxy-bos.png`, `02-abd-proxy-kayitli-parola.png`, `03-abd-proxy-dene-sonucu.png` (yerel sahte proxy)
  - `04-bolge-engelli-liste.png`
  - `05-eklenti-calisiyor.png` (Ayarlar → Tarayıcı eklentisi, iş sürerken)
  - `06-isler-dogrulama-ve-atla.png` (İşler panelinde doğrulama beklemesi ve "Bu sayfayı atla")
  - `07-deneme-tablosu-sayfa-turleri.png`
  - `08-video-metni-secildi.png`, `09-karsilastirma-plan-kullanimi.png`
  - `10a-gercek-abd-proxy.png`, `10b-gercek-eklenti-eski-surum.png` (gerçek veriyle)
  - `11-eklenti-penceresi-son-is-ve-atla.png` (eklenti penceresi, yerel deneme)
