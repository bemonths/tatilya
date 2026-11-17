# M18 — ABD dışı erişim engeli için kullanıcının ABD proxy'si ve sayfa türleri (GÖREV-16, v0.18.0, şema 18; GÖREV-17 pencereler)

## Neden

Kullanıcı 11 Ekim 2026'da "30A Studio Yardımcısı" eklentisini kendi Chrome'una kurdu ve "Sorunlu sitelerden birer sayfa dene"ye bastı.
Ham kayıtlar (`data/raw/eklenti/20261011/`) şunu gösterdi: CVS ("not available to customers … outside of the United States", 403),
Publix (başlık "International | Publix Super Markets", "unable to service customers outside of the United States") ve HCA (bir
`geo-blocked-site.dpxmedcity.net` adresine yönlenme) ABD dışından gelen ziyaretçiye hizmet vermiyor. Bu siteler daha önce de bot koruması
yüzünden değil, kullanıcı Türkiye'den bağlandığı için okunamıyormuş. Eklenti kullanıcının kendi bağlantısını kullandığı için bunu çözemez.

Kullanıcının kararı: ABD dışından erişilemeyen siteler için kendi ABD proxy'si kullanılır (Housing Atlas'ta FEMA için yapılanın aynısı).
Yöneticinin sınırı: proxy yalnız ABD dışı erişim engeli olan siteler için kullanılır; bot korumasını, hız sınırını ya da yasağı aşmak için
kullanılmaz; IP döndürme yoktur. Bu kural `CLAUDE.md`'deki tarayıcı kuralına işlendi.

## Sayfa türleri (`studio/sources/page_kinds.py`)

Dönen bir sayfa dört türden biridir; işaretler tek Python kaynağındadır, `eklenti/logic.js`'teki kopyası bir testle denetlenir ve iki
taraf aynı fikstürlerde (`tests/fixtures/sayfa_turleri/beklenen.json`) aynı sonucu verir:

| Tür | Ne | Ne yapılır |
|---|---|---|
| `tamam` | sıradan sayfa | okunur |
| `dogrulama` | Cloudflare "Just a moment", "Checking your browser", sayfa betiği; PerimeterX (px-captcha, "Press & Hold"); başlıklar "Just a moment", "Attention Required", "Verify you are human" | kullanıcı geçer; eklenti en çok 15 dk bekler ("Bu sayfayı atla" ile atlanabilir) |
| `erisim_reddedildi` | Akamai "Access Denied" / "You don't have permission to access", Cloudflare "Sorry, you have been blocked", "You are unable to access", başlık "Access Denied" / "403 Forbidden", görünür metni çok kısa 403 | beklenmez, hemen atlanır |
| `bolge_engeli` | "outside of the United States", "outside the U.S.", "not available in your country/region", "unable to service customers outside", Amazon CloudFront'un "configured to block access from your country" cümlesi (GÖREV-20: vacasa.com), başlık "International \| Publix", adresinde "geo-block" geçen yönlenme | beklenmez, hemen atlanır; alan adı bölge engelli listeye girer; ABD proxy'si varsa onunla okunur |

Sıra: bölge engeli → güçlü ret ifadesi → doğrulama → ret başlığı ya da boş 403 → tamam. "Access denied" başlığı artık doğrulama sayılmaz
(Winn-Dixie'de 15 dk boşuna beklenmişti). Bir bölge ifadesi tek başına ancak kısa bir sayfada (görünür metin 4.000 karakterden az) ya
da 403/451 cevabında sayılır; sıradan bir sayfanın altbilgisindeki "we do not ship outside the United States" sayılmaz. PerimeterX'in
"Access to this page has been denied" başlıklı "Press & Hold" sayfası doğrulamadır.

Programın kendi tarayıcısı da aynı ayrımı kullanır (`browser_verification.page_state`): erişim reddedildi ve bölge engeli kullanıcı
doğrulamasına gönderilmez; bölge engeli `RegionBlocked` olarak toplayıcıya döner ve alan adı listeye girer.

## Ayarlar → "ABD proxy'si (bölge engeli için)"

- **Proxy adresi** (`şema://sunucu:port`; http, https ya da socks5). Doğrulama Housing Atlas'ın `proxy_url_error`'ından taşındı:
  şema, sunucu ve port olmalı; kullanıcı adı ve parola adrese yazılmaz; yol, sorgu olmaz.
- **Kullanıcı adı** ve **parola**. Adres ve kullanıcı adı `<veri>/ayarlar.json` → `abd_proxy`'de durur. Parola Windows Kimlik Bilgisi
  Yöneticisi'nde durur (`keyring`, hizmet adı `30AStudio`, ad `abd_proxy_parolasi`; `studio/credentials.py`). Ekran yalnız "kayıtlı"
  gösterir; "Parolayı sil" düğmesi vardır. Okunan ya da kaydedilen gizli değer günlük maskeleme listesine girer (`studio/logs.py`,
  Housing Atlas'taki gibi): günlüğe yazılan her mesajda ve hata dökümünde `***` olur.
- **"Proxy'yi dene":** proxy üzerinden herkese açık bir IP servisine gidilir (`https://ipinfo.io/json`); ekranda çıkış adresi ve ülkesi
  yazar. Ülke ABD değilse uyarı çıkar: "Proxy'nin çıkış adresi ABD'de görünmüyor". Listedeki hiçbir siteye gidilmez. Satırlarda proxy
  yalnız `şema://sunucu` olarak görünür (port, kullanıcı adı ve parola yok).
- **SOCKS5 sınırı:** Chrome kullanıcı adı ve parola isteyen SOCKS5 proxy'yi desteklemez (Housing Atlas notu). Böyle bir proxy girilirse
  ekran şunu söyler: programın kendi tarayıcısı bu proxy'yle kullanılamaz, yalnız doğrudan istekler kullanılabilir.

## Bölge engelli alan adları (şema 18: `region_blocked_hosts`)

- Program bir alan adında bölge engeli görünce o alan adını listeye kendisi ekler: tarih, sayfanın adresi, başlığı ve engeli gösteren
  söz ya da yönlendiği adres (`added_by = program`). Programın kendi yerel adresi hiçbir zaman listeye girmez.
- Kullanıcı Ayarlar'dan alan adı ekleyebilir (`added_by = kullanici`) ve herhangi bir satırı çıkarabilir.
- İlk satırlar geçişte, eklentinin ham kayıtlarından çıkar (`<veri>/raw/eklenti/*/*.json` ve yanındaki sayfa): 11 Ekim denemesinden
  cvs.com, publix.com ve hcafloridahealthcare.com. winndixie.com ve thefreshmarket.com için ham kayıt yok (deneme Winn-Dixie'de takılıp
  iptal edilmişti); bunlar eklenmedi.

## Okuma sırası (`studio/sources/region_reader.py`)

Listedeki bir alan adı için:

1. Proxy üzerinden doğrudan istek (httpx).
2. Bu reddedilirse (doğrulama, erişim reddedildi, bölge engeli, hata durumu) ya da sayfa JavaScript'le çiziliyorsa (görünür metni kısa ve
   betikli sayfa) programın kendi tarayıcısı, proxy'yle.
3. O da olmazsa atla ve kaydet: "bölge engeli: proxy'yle de okunamadı (…)".

Proxy tanımlı değilse bölge engelli sayfa hemen atlanır ve kaydedilir: "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)"; iş paneli de
aynısını yazar. Bu alan adları için **eklenti kullanılmaz** (kullanıcının bağlantısıyla zaten okunamazlar). Hız kuralı aynıdır: aynı
sitede iki sayfa arası en az 8 sn, bir anda tek sayfa. Proxy üzerinden doğrulama sayfası çıkarsa onu kullanıcı programın tarayıcı
penceresinde geçer (en çok 15 dk).

**Programın kendi tarayıcısında proxy yalnız listedeki alan adlarına uygulanır.** Yöntem: ayrı bir Chrome süreci ve ayrı profil
(`work/tarayici-profili/30a-studio-proxy`, repoya girmez) ve bir PAC betiği (`--proxy-pac-url=data:…`): listedeki alan adları ve alt alan
adları proxy'ye, öbür bütün adresler `DIRECT`. Proxy kimliği komut satırına yazılmaz; Housing Atlas'taki gibi CDP `Fetch` ile, yalnız
programın sekmesinde verilir (aynı istekte ikinci soru gelirse vazgeçilir; sitenin kendi parola sorusu Chrome'a bırakılır). Liste ya da
proxy değişince eski PAC'la açılmış proxy tarayıcısı kapatılıp yeniden açılır (profildeki `30a-proxy-pac.json` PAC'ın SHA-256'sını tutar).

Toplayıcılarda:

- **Restoran siteleri:** listedeki alan adının her sayfası okuma sırasıyla (proxy → tarayıcı + proxy → atla) okunur; doğrudan istekte bölge
  engeli görülürse (sayfa ya da geo-block yönlenmesi) alan adı listeye girer ve aynı sayfa hemen proxy'yle denenir (proxy yoksa atlanır).
  Eklentiyle okunurken bölge engeli çıkarsa alan adı listeye girer.
- **Kiralama şirketleri:** listedeki şirket sitesinin istekleri proxy'den gider (en az 8 sn arayla); tarayıcı gerekirse programın proxy
  tarayıcısı kullanılır; proxy yoksa şirket "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)" diye atlanır. Eklenti ya da programın
  tarayıcısı bölge engeli görürse alan adı listeye girer ve şirket bu çekimde durur (sonraki çekimde proxy'yle okunur).
- **"Sorunlu sitelerden birer sayfa dene":** listedeki siteler eklentiye verilmez, proxy'yle denenir; eklenti bir sitede bölge engeli
  görürse alan adı listeye girer ve proxy varsa sayfa hemen proxy'yle denenir.

Ham kayıtlarda `yontem` alanı `proxy` ya da `tarayici+proxy` olur ve `proxy: true` yazar; proxy'nin adresi yazılmaz.

## GÖREV-17: pencereler ve günlük metni (v0.19.0)

- **Programın proxy tarayıcısının penceresi.** Odak almadan başlatılır (`browser_verification.start_browser`: pencere gösterilir ama
  etkinleştirilmez; komut satırı aynıdır, bayrak eklenmedi), bir iş boyunca tek sekme kullanır, yalnız proxy üzerinden çıkan ve
  kullanıcının geçmesi gereken doğrulamada öne gelir (`bring_forward`) ve onu başlatan iş bitince ya da iptal edilince kapatılır
  (`JobWindows`; CDP `Browser.close`, profil diskte kalır). Görünmez (headless) kip ve küçültülmüş pencere kullanılmaz. İşler panelinde
  "Programın proxy tarayıcısı: <site> okunuyor" yazar. Programın proxy'siz kendi tarayıcısı da aynı kurallara uyar; iş başlamadan önce
  zaten açık olan tarayıcı (kullanıcının ısınma sekmeleri) kapatılmaz, yalnız işin kendi sekmeleri kapanır.
- **Günlük metni.** Bölge engelli sitenin sonucu deneme işinin günlüğünde, deneme tablosunda ve İşler panelinde aynı sözlerle yazar
  (`proxy.region_outcome`): "bölge engeli · proxy'yle okundu", "bölge engeli · proxy'yle de okunamadı (neden)", "bölge engeli · ABD
  proxy'si tanımlı değil (Ayarlar)". İşin son satırı kaç sitenin proxy'yle okunduğunu söyler. Ham kayıtlardaki `yontem` ve `proxy`
  alanları ve toplayıcıların atlama notları (`NO_PROXY_SKIP`, `PROXY_FAILED_SKIP`) değişmedi.
- Proxy'nin yalnız bölge engelli alan adlarında kullanılması, hız kuralı ve doğrulamayı kullanıcının geçmesi değişmedi.

## Bölge engeli ölçümü (GÖREV-22, 17 Kasım 2026, v0.23.0)

Bir alan adı listeye "bence bölge engelli" diye girmez; ölçülür. Kural `studio/sources/region_probe.py` içindedir (hiçbir siteye
istek yapmaz, yalnız iki yanıtı karşılaştırır): aynı sayfa bir kez doğrudan, bir kez proxy üzerinden istenir.

| Sınıf | Ne zaman | Ne yapılır |
|---|---|---|
| `bolge_engeli` | Doğrudan istek ret, engel sayfası, doğrulama ya da ülke engeli alıyor ya da hiç yanıt almıyor; proxy üzerinden site normal yanıt veriyor | Alan adı listeye eklenir (Veri → Okuma denemeleri → Bölge engelli alan adları) |
| `bolge_engeli_degil` | Proxy üzerinden de aynı ret, engel sayfası ya da doğrulama geliyor; ya da site iki yoldan da normal yanıt veriyor | Site bırakılır; proxy kullanılmaz |
| `site_yok` | İki yoldan da siteye ulaşılamıyor (DNS kaydı yok, bağlantı yok, sunucu hatası) ya da gelen sayfa alan adı kayıt firmasının / park şirketinin sayfası | Şirketin güncel sitesi aranır; bulunursa o adres ölçülür |

"Normal yanıt": sitenin kendisi engelsiz yanıt verdi — sıradan bir sayfa, bir yönlendirme ya da sitenin kendi "bulunamadı" sayfası.
Ölçüm kuralı: alan adı başına en çok 3 istek, aynı sitede iki istek arası en az 8 sn, yönlendirme izlenmez (her adım ayrı istektir),
programın kendi tarayıcısı kullanılmaz. Ölçümü kullanıcı izin verdiğinde Claude Code yapar; programda bunun için bir düğme yoktur.

17 Kasım 2026 ölçümünün sonucu (ayrıntı ve ham kopyaların adları: `docs/gorevler/GOREV-22/RAPOR.md`, `olcum-istekleri.csv`):

| Alan adı | Doğrudan | Proxy | Sınıf |
|---|---|---|---|
| 360blue.com | 403, Cloudflare engel sayfası | sitenin kendi sayfaları (301, sitenin "Error Page"i; incelemede 200) | bölge engeli → listede |
| vacasa.com | 403, CloudFront ülke engeli | 200, sitenin sayfası | bölge engeli → listede |
| wyndhamvacationrentals.com | 301 → vacasa.com | 301 → vacasa.com | bölge engeli değil (yalnız yönlendiriyor) |
| cottagerentalagency.com | 301 → sandestin.com | 301 → sandestin.com | bölge engeli değil |
| rentals.cottagerentalagency.com | DNS kaydı yok | bağlantı kurulamadı | site yok |
| sandestin.com | 403 "Access denied" | 403 "Access denied" | bölge engeli değil (kaldırılmış sayfa) |
| outdoorshower30a.com | zaman aşımı | bağlantı kurulamadı; http'de alan adı kayıt firmasının sayfası | site yok (alan adı askıda) |
| golocalvr.com (Outdoor Shower'ı devralan şirket) | 301 (kendi sitesine) | 301 (aynı) | bölge engeli değil |

Listeye ekleme isteği (`POST /api/abd-proxy/bolge-engelli`) artık isteğe bağlı olarak ölçümde görüleni de alır (`baslik`, `adres`,
`kanit`); ekrandaki kutu yalnız alan adını gönderir.

**Kiralama toplayıcısında yalnız listedeki alan adları proxy'den gider (GÖREV-22).** Bölge engelli bir şirketin bütün istekleri
artık proxy'den gitmez: şirketin listede olmayan alan adları (bağlantıların başladığı başka bir alan adı, altyapının API adresi)
doğrudan gider (`agency_rates.proxy_client(proxy, hosts)`; `HttpTransport.proxied`). Örnek: wyndhamvacationrentals.com bağlantısı
doğrudan istenir, yönlendiği vacasa.com adresi proxy'den. Ham kayıtta `transport` her istek için ayrı yazılır (`http` ya da `proxy`).

## Gizli bilgi nerede durur

| Bilgi | Nerede | Nerede durmaz |
|---|---|---|
| Proxy parolası | Windows Kimlik Bilgisi Yöneticisi (`30AStudio` / `abd_proxy_parolasi`); çalışırken bellekte | `ayarlar.json`, veritabanı, ham kayıtlar, uygulama günlüğü (maskelenir), iş mesajları, API cevapları, Chrome komut satırı, PAC betiği, proxy tarayıcısının profili |
| Proxy adresi (şema, sunucu, port) | `ayarlar.json`; proxy tarayıcısının PAC betiği (yalnız sunucu ve port) | ham kayıtlar (yalnız `proxy: true`); metinlerde yalnız `şema://sunucu` |
| Kullanıcı adı | `ayarlar.json` | ham kayıtlar, Chrome komut satırı, PAC betiği |

## Testler

`tests/test_page_kinds.py` (fikstürler, kullanıcının ham sayfalarından CVS ve Publix, "access denied" ve PerimeterX, uzun sıradan sayfa,
programın tarayıcısı), `tests/test_proxy.py` (adres doğrulaması; parolanın yalnız sahte kasada durması, hiçbir dosyada, günlükte ve API
cevabında görünmemesi; yerel sahte proxy ve sahte IP servisiyle "Proxy'yi dene" ve ülke uyarısı; httpx mount'larının yalnız listedeki alan
adlarını proxy'ye göndermesi; liste; ham kayıtlardan ilk satırlar ve 17 → 18 geçişi; okuma sırası; PAC içeriği ve komut satırı; CDP
kimlik cevabı; SOCKS5 sınırı; restoran ve kiralama toplayıcıları), `tests/test_extension_16.py` (deneme tablosu, listedeki sitenin
eklentiye verilmemesi, proxy yokken atlama, proxy'le okuma ve ham kayıtta adres olmaması). Testler gerçek siteye ve gerçek proxy'ye
gitmez; Windows Kimlik Bilgisi Yöneticisi yerine bellekte bir kasa kullanılır (`tests/conftest.py`); yerel sahte proxy yalnız `local_network`
kalıbıyla 127.0.0.1'e bağlanabilir.

## Sınırlar

- GÖREV-16'da gerçek proxy ve gerçek sitelerle denenmemişti. GÖREV-22'de (17 Kasım 2026) kullanıcının izniyle proxy modülü gerçek
  proxy'yle kullanıldı: yukarıdaki ölçüm (18 istek) ve iki bölge engelli şirketin incelemesi (şirket başına 10 sayfa). Programın proxy
  tarayıcısı gerçek sitede henüz denenmedi (bu iki şirket doğrudan istekle okunuyor); kiralama toplayıcısının proxy'li ilk çekimini
  kullanıcı başlatacak.
- Proxy tarayıcısı (Chrome) yalnız PAC'teki alan adlarını proxy'ye gönderir; Chrome'un kendi arka plan istekleri doğrudan gider.
- Günlük ihtiyaç zincir kontrolleri (CVS, Publix, Winn-Dixie, The Fresh Market, HCA) toplayıcıda canlı okunmuyor, gözden geçirilmiş
  dosyadan geliyor; proxy'yle okunan sayfalardan bu dosyanın güncellenmesi ayrı bir iş.
