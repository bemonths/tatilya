# M16 — Tarayıcı eklentisi: "30A Studio Yardımcısı" (GÖREV-14, v0.16.0; GÖREV-16 düzeltmeleri, v0.18.0; GÖREV-17 tek pencere, v0.19.0; GÖREV-25 sayfanın kendi sorgusu, 0.20.0)

## Neden

Bazı siteler programın kendi tarayıcısını (ayrı profil, CDP bağlantısı; `studio/sources/browser_verification.py`) içeri almıyor ama
kullanıcının günlük Chrome'unu alıyor. Raporlarda geçenler: realjoy.com (61 ilan) ve order.online (3 restoran menüsü) doğrulamayı
geçemedi; HCA Florida, CVS, Publix, Winn-Dixie ve The Fresh Market "bu bilgisayardan okunamadı".

Programın kullanıcının günlük profiline doğrudan bağlanması yapılmaz: Chrome'un yeni sürümleri varsayılan profilde uzaktan hata ayıklama
bağlantısına izin vermiyor, profil kopyalamak işe yaramıyor ve kullanıcının kişisel oturumlarını programa açar. Çözüm, kullanıcının kendi
Chrome'una kurduğu küçük bir eklentidir: sayfaları kullanıcının tarayıcısında normal sekmeler olarak açar ve yalnız sayfanın içeriğini
programa verir.

## Mimari

```
Chrome (kullanıcının profili)                         30A Studio (127.0.0.1:8830–8849)
┌──────────────────────────────┐   POST /api/eklenti/sor     ┌───────────────────────────────┐
│ eklenti/background.js         │ ──────────────────────────▶ │ studio/extension.py            │
│  (service worker, MV3)        │ ◀── oturum (alan adı, hız) ─│  ExtensionBridge (bellekte)    │
│  kendi penceresi + sekmesi    │   POST …/is/<id>/sonraki    │   Session: sayfa / istek öğeleri│
│  sayfa → outerHTML            │ ◀── öğe ──────────────────── │                               │
│  istek → sayfanın fetch'i     │   POST …/is/<id>/sonuc      │  toplayıcı iş parçacığı bekler │
└──────────────────────────────┘ ──────────────────────────▶ └───────────────────────────────┘
```

- **Eşleşme:** Ayarlar → Tarayıcı eklentisi bir kod gösterir (`ABCD-1234` biçimi, `data/eklenti.json`). Kullanıcı kodu eklentiye bir
  kez yazar; eklenti `POST /api/eklenti/eslestir` ile kendini tanıtır. Kodu bilen ilk `chrome-extension://<kimlik>` kökeni kaydedilir;
  başka bir eklenti kökeni kod yenilenene kadar reddedilir. "Kodu yenile" eşleşmeyi düşürür.
- **Programı bulma:** eklenti 127.0.0.1 üzerinde 8830–8849 aralığını `/api/health` ile tarar (`app == "thirtya-studio"`); bulduğu portu
  hatırlar. Masaüstü başlatıcısı da bu aralığı kullanır (Housing Atlas 8790–8809).
- **Sorma:** service worker 30 sn'de bir `chrome.alarms` ile uyanır, uyanıkken 3 sn'de bir iş sorar (`/api/eklenti/sor`; sürümünü ve
  izin verilen alan adlarını da bildirir). Program eklentiyi son 20 sn içinde duymadıysa "bağlı değil" sayar.
- **Oturum:** bir toplayıcı bir alan adı için oturum açar (`bridge.open(domain)`), oturuma öğe ekler ve sonucunu bekler:
  - `sayfa`: adres + bekleme kuralı (`{"saniye": n}` ya da `{"oge": "css seçici"}`); sonuç `outerHTML`, son adres, başlık, HTTP durumu
    (`performance` gezinti kaydından), durum.
  - `istek`: sayfanın kendi `fetch`'i (kiralama şirketlerinin JSON uçları için; sekme önce o sitenin kökünü açar).
  Eklenti oturumu alınca kendi açtığı ayrı ve öne gelmeyen pencerede tek bir sekme açar, öğeleri teker teker işler, bitince sekmeyi ve
  pencereyi kapatır. Kullanıcının sekmelerine dokunmaz.
- **Durumlar:** `tamam`, `dogrulama` (15 dk içinde geçilmedi), `giris` (giriş gerekiyor; içerik gönderilmez), `odeme`, `izin_yok`, `hata`.

## Okuma sırası ve toplayıcılar

Engel görülen alan adları için: 1. doğrudan istek, 2. engel varsa ve eklenti eşleşmişse eklenti, 3. iş programa devredildiyse (kullanıcı
"Programın tarayıcısına devret" dedi ya da eklenti 30 dk gelmedi) programın kendi tarayıcısı, 4. o da olmazsa atla ve kaydet.
`browser_hosts.method` (şema 16) bir alan adı için en son neyin işe yaradığını tutar (`eklenti`, `tarayici`, `dogrudan`).

- **Restoran siteleri** (`restaurant_sites`): ikinci geçiş `BrowserPages`'in açıcısı olarak `ExtensionPages`'i kullanır
  (`studio/sources/extension_reader.py`). Ham kopyalar toplayıcının kendi deposunda "(eklenti)" notuyla, SHA-256'sıyla saklanır.
- **Kiralama şirketleri** (`agency_rates`): doğrulayıcı `ExtensionVerifier`; sayfa içi istekler `ExtensionTransport` (`kind = "eklenti"`;
  ham kayıtta `transport: eklenti`).
- **Günlük ihtiyaç zincir kontrolleri:** toplayıcı zincir sitelerini canlı okumaz; gözden geçirilmiş dosyadan (`chain_checks`) okur. Bu
  sitelerin sayfaları Ayarlar'daki "Sorunlu sitelerden birer sayfa dene" ile eklentiyle okunabilir (ham kopya `raw/eklenti/`); dosyanın
  güncellenmesi ayrı bir iş (yönetici kararı).
- **Eklenti bekleniyor:** eşleşmiş ama sessiz eklenti için iş "Eklenti bekleniyor: … Chrome'u açın" der (`job_progress`:
  `{"tur": "eklenti", "bekliyor": true}`); İşler panelinde "Programın tarayıcısına devret" düğmesi çıkar.

## GÖREV-16 düzeltmeleri (v0.18.0)

Kullanıcının 11 Ekim 2026 denemesinde iki sorun çıktı: eklenti Akamai'nin "Access Denied" sayfasını geçilebilir bir doğrulama sanıp 15 dk
bekledi (Winn-Dixie) ve iş sürerken programa hiç haber vermediği için program 20 sn sonra "Bağlı değil (Chrome kapalı olabilir)" dedi.

- **İş sürerken canlılık.** Eklenti bir iş sürerken en çok 4–5 sn arayla programa ne yaptığını bildirir (`/api/eklenti/is/<oturum>/durum`,
  `{asama: {asama, adres, kalan_s}}`): sayfa açılıyor, sayfa okunuyor, doğrulama bekleniyor (kalan süreyle), bekleme (hız kuralı). Program
  eklentiden gelen her yetkili çağrıyı "görüldü" sayar. "Bağlı değil" yalnız eklentiden gerçekten haber alınamıyorsa yazar: iş sürerken
  60 sn, iş yokken 20 sn. Ayarlar → Tarayıcı eklentisi (5 sn'de bir yenilenir) ve İşler paneli iş sürerken "Eklenti çalışıyor: <site> ·
  <durum>" der. Eklenti penceresindeki "Son iş" satırı takılı bir işi en son ne zaman ilerlediğiyle söyler.
- **Sayfa türleri.** Doğrulama (kullanıcı geçer), erişim reddedildi (beklenmez) ve bölge engeli (beklenmez; alan adı bölge engelli listeye
  girer) ayrıldı; işaretler `studio/sources/page_kinds.py`'de, eklentideki kopyası testle denetlenir; ayrıntı ve tablo
  `docs/M18-ABD-PROXY-BOLGE-ENGELI.md`. "access denied" başlığı artık doğrulama sayılmaz.
- **Başka siteye yönlenme.** Sayfa izin verilmemiş başka bir alan adına yönlenirse eklenti sekmenin adresini okur ve sonucu "başka siteye
  yönlendi: <alan adı>" diye verir; adres "geo-block" içeriyorsa sonuç bölge engelidir. Chrome'un izin hata metni sonuç olarak yazılmaz.
- **"Bu sayfayı atla".** Doğrulama beklenirken eklenti penceresinde ve İşler panelinde düğme vardır; basılınca sayfa "kullanıcı atladı"
  (`atlandi`) diye kaydedilir ve iş sürer. İşler panelindeki düğme programa söyler, eklenti bunu bir sonraki bildiriminin cevabında öğrenir.
- **Yeni sonuçlar.** `erisim_reddedildi`, `bolge_engeli` (sayfa kanıt olarak saklanır), `yonlendi`, `atlandi`.
- **Deneme listesi ve tablosu.** realjoy.com için kalkmış ilan adresi yerine kalıcı 30A ilan listesi sayfası
  (`https://www.realjoy.com/beach-rentals/30a-vacation-rentals`, 11 Ekim ham kaydının bağlantılarından). Tabloda her sitenin türü ve
  okuma yöntemi (eklenti, proxy, tarayıcı + proxy) yazar. Bölge engelli listedeki siteler eklentiye verilmez; ABD proxy'si varsa onunla
  denenir.
- **Sürüm.** Eklenti 0.18.0 oldu; Chrome'da eski sürüm takılıysa Ayarlar bunu söyler: `chrome://extensions` sayfasında eklentinin yenile
  düğmesine basılır. Eklenti proxy kullanmaz, Chrome'un proxy ayarına dokunmaz; `proxy` izni yoktur.

## İzinler (manifest)

| İzin | Neden |
|---|---|
| `tabs` | Kendi penceresini ve sekmesini açmak, adresini değiştirmek, yüklenmesini beklemek, kapatmak |
| `scripting` | Yalnız kendi açtığı sekmede sayfanın `outerHTML`'ini okumak, bir öğeyi beklemek, sayfa içi `fetch` |
| `storage` | Eşleşme kodu, bulunan port, son durum |
| `alarms` | 30 sn'de bir uyanıp iş sormak |
| `notifications` | "30A Studio: doğrulama bekleniyor" bildirimi |
| `http://127.0.0.1/*` | Yalnız yerel program (ve programın yerel deneme sayfası) |
| `optional_host_permissions` (`https://*/*`, `http://*/*`) | Site izni: her site için kullanıcı eklenti penceresinde "İzin ver" der (`chrome.permissions.request`) |

Yok: `cookies`, `history`, `bookmarks`, `downloads`, `debugger` (CDP), `webRequest`, `<all_urls>`. Kod sıkıştırılmamış ve gizlenmemiştir.

## Güvenlik

- `/api/eklenti/*` yalnız eşleşmiş eklentinin kökenini ve eşleşme kodunu (`X-Studio-Eklenti` başlığı) kabul eder; CORS yalnız o köken
  için açılır (ön kontrol dahil). Eşleşmeden önce yalnız `/api/eklenti/eslestir` bir `chrome-extension://` kökenine açıktır.
- Programın kendi API'sinde durum değiştiren istekler (GET dışı) başka bir kökenden (`Origin` farklı) ya da tarayıcının
  `Sec-Fetch-Site: cross-site/same-site` dediği bir sayfadan gelirse reddedilir; programın kendi penceresi `X-Studio-Request` başlığını
  gönderir. Programın API'si başka kökenlere CORS açmaz; `TrustedHostMiddleware` yalnız 127.0.0.1/localhost'u kabul eder.
- Program kullanıcının Chrome profiline, çerezlerine, parolalarına ve geçmişine erişmez; eklenti de bu izinleri istemez.
- Eklenti tıklamaz, yazı yazmaz, form doldurmaz; sayfanın kendi sorgusunu (GÖREV-25) yalnız izinli listeyle ve sayfanın alanlarıyla
  gönderir (aşağıda); giriş ve ödeme sayfalarını okumadan atlar; doğrulamayı kullanıcı yapar (çözme servisi,
  gizlenme, parmak izi sahteciliği ve IP değiştirme yoktur; eklenti proxy kullanmaz, Chrome'un proxy ayarına dokunmaz). Programın ABD
  proxy'si yalnız bölge engelli alan adları içindir ve eklentiyle ilgisi yoktur (`docs/M18-ABD-PROXY-BOLGE-ENGELI.md`).

## Hız ve doğrulama

- Aynı alan adında iki sayfa arası en az 8 sn (Ayarlar'dan 3–120 sn); bir anda tek sayfa.
- Doğrulama sayfası programın işaretleriyle tanınır (`studio/sources/page_kinds.py`; `eklenti/logic.js` aynı metni taşır, bir Python
  testi denetler ve iki taraf aynı fikstürleri sınar). Erişim reddedildi ve bölge engeli beklenmez (GÖREV-16). Görülürse eklenti pencereyi öne getirir, bildirim gösterir, programa bildirir (iş panelinde "Kullanıcı doğrulaması
  bekleniyor"), 3 sn'de bir bakar; 15 dk içinde geçilmezse sayfa atlanır ve kayda yazılır. Toplayıcılar bu siteler için sonda ikinci kez
  beklemez.

## Ayarlar → Tarayıcı eklentisi

Bağlantı (bağlı / bağlı değil, son görülme, eklenti sürümü), eşleşme kodu ve "Kodu yenile", izin verilmiş ve izin bekleyen alan adları,
hız ayarı, kurulum adımları ve resimli rehber (`eklenti/KURULUM.md`, `eklenti/kurulum/*.png`), "Deneme" (programın kendi yerel sayfası
`/eklenti-deneme`; ham kopya `raw/eklenti/<tarih>/`), "Sorunlu sitelerden birer sayfa dene" (profildeki `EXTENSION_TRIAL_SITES`; arka plan
işi `eklenti_deneme`; bu düğmeye kullanıcı basar).

## Sınırlar

- Oturumlar bellekte tutulur; program kapanırsa bekleyen öğeler düşer (iş zaten yarıda kalır).
- Service worker Chrome tarafından durdurulursa eklenti oturumu yeniden alır (45 sn sessiz kalan oturum yeniden verilir; yarım öğe yeniden
  sorulur).
- realjoy.com için kiralama okuyucusu (adaptör) yok: eklenti sayfayı okuyabilir ama fiyat çıkarılamaz (yönetici kararı). GÖREV-20 (16 Kasım 2026): site ICND rezervasyon motorunu kullanıyor (arkada Track); doğrulaması programın kendi tarayıcısında geçmedi. Okuyucunun yazılabilmesi için deneme listesinin sonuna bir **ilan sayfası** eklendi (`https://www.realjoy.com/beach-rentals/sea-la-vie-seaside-main-house`, 11 Kasım ham kaydının bağlantılarından); kullanıcı "Sorunlu sitelerden birer sayfa dene"ye basınca ham kopyası alınır. Ayrıntı: `docs/M11-KONAKLAMA-FIYATLARI.md`.
  GÖREV-24 (17 Kasım 2026): ilan sayfasının kaydı geldi; fiyat sayfanın betiklerinde olduğu için listeye bir kez sayfanın üç betiği
  (`z_pdp.js`, `datepicker.js`, `z_global.js`; sayfa olarak açılıp okundu) kondu ve okunduktan sonra çıkarıldı. Fiyat yalnız
  `POST /ajax/quote` ile geliyor; **deneme listesinde fiyat adresi yok** (GET bir fiyat adresi bulunmadı), okuyucu yazılmadı. Listede
  realjoy.com'dan yalnız 30A ilan listesi kaldı (sonda). Deneme okuması bir sitenin iki sayfası arasında en az eklentinin aralığı
  kadar, realjoy.com'da 20 sn bekler (`EXTENSION_TRIAL_GAP_S`; site 429 vermişti).
- Bildirim ve pencereyi öne getirme Chrome'un ve Windows'un izin verdiği kadardır.

## Testler

- Node (`tests/frontend.test.mjs`): iş kuyruğu, hız sınırı, doğrulama/engel tanıma, giriş ve ödeme sayfası tanıma, izin desenleri,
  bekleme kuralı, Ayarlar ekranı.
- Python (`tests/test_extension.py`): eşleşme, köken denetimi ve CORS, başka kökenden durum değiştiren isteğin reddi, oturum yaşam döngüsü
  (taklit eklentiyle), izin bekleme, deneme ve ham kayıt, eklenti beklenirken devretme, toplayıcı okuyucuları, `browser_hosts.method`,
  işaretlerin programınkiyle aynı olması, manifestin dar izinleri.
- Uçtan uca (`tests/test_extension_e2e.py`, `STUDIO_EKLENTI_E2E=1`): Playwright'in Chromium'u geçici profille eklentiyi yükler; yerel
  deneme sunucusunda normal sayfa, JavaScript ile çizilen sayfa, kendiliğinden geçen ve geçmeyen doğrulama sayfası, giriş sayfası ve JSON
  ucu sınanır; kullanıcı sekmesine dokunulmadığı ve eklenti penceresinin kapandığı denetlenir. Gerçek siteye gidilmez.

## GÖREV-17: bir iş boyunca tek pencere (eklenti 0.19.0)

Kullanıcının 11 Kasım 2026 gözlemi: "Sürekli web sayfası açıyor." İnceleme: eklenti her oturum (bir işin bir sitesi) için
`chrome.windows.create` ile yeni bir pencere açıyor, o sitenin sayfaları bitince pencereyi kapatıyordu; 7 sitelik deneme işinde ya da
restoran sitelerinin ikinci okumasında bu, art arda açılıp kapanan pencereler demekti.

- **Tek pencere.** Eklenti programın bir işi boyunca tek pencere ve tek sekme kullanır; aynı sekmede sıradaki adrese gider. Oturum
  görünümü `pencere` anahtarını taşır (programın iş kimliği; Ayarlar'daki "Deneme" gibi işsiz oturumda oturumun kendisi). Pencerenin
  kimliği `chrome.storage.session`'da durur; durdurulup yeniden başlayan service worker penceresini bulur. Kullanıcı pencereyi
  kapatırsa sıradaki sayfada yeniden açılır.
- **Ne zaman kapanır.** `/api/eklenti/sor` cevabı `acik_pencereler` listesini verir: eklentiyi kullanmış ve hâlâ sırada ya da
  çalışan işler ile bitmemiş deneme oturumları. Eklentinin penceresinin anahtarı listede değilse (iş bitti, iptal edildi, programın
  tarayıcısına devredildi) pencere kapanır. Program bulunamazsa ya da eşleşme düşerse de kapanır. Listeyi göndermeyen eski bir
  programla eklenti eskisi gibi her oturumdan sonra kapatır.
- **Arka planda.** Pencere `focused: false` ile, normal boyutta açılır; kullanıcının çalıştığı pencerenin önüne geçmez.
  `state: "minimized"` seçilmedi: küçültülmüş (gizli) sayfada çizim (`requestAnimationFrame`) ve görünüme girince yüklenen bölümler
  durur, sayfa yarım okunabilir. Gerçek Chrome'la yapılan denemede etkinleştirilmeden açılan pencere kullanıcının odağını değiştirmedi
  ve sayfa normal çizildi.
- **Öne gelme.** Yalnız kullanıcının geçmesi gereken doğrulamada (`chrome.windows.update(…, {focused: true, state: "normal"})` ve
  bildirim). Doğrulama kuralları aynı: en çok 15 dk, "Bu sayfayı atla".
- **İşler paneli.** Süren işin kartında "Açık pencere — Eklentinin penceresi: <site> · <durum>"; iki site arasında "sıradaki sayfa
  bekleniyor".
- **Sürüm.** Eklenti 0.19.0. Chrome'daki eklenti eski sürümse Ayarlar → Tarayıcı eklentisi bunu söyler; `chrome://extensions`
  sayfasında eklentinin yenile düğmesine basılır.
- **Test.** `tests/test_gorev17.py` (köprü: pencere anahtarı, açık pencereler listesi, devir; eklenti dosyalarında tek
  `chrome.windows.create` ve iş içinde pencere kapatmama), `tests/frontend.test.mjs` (`windowKey`, `keepWindow`, `WINDOW_OPTIONS`),
  uçtan uca `tests/test_extension_e2e.py` (Playwright'in Chromium'u, yerel sayfalar: bir işin iki oturumu aynı pencerede, pencere iki
  site arasında açık, tek sekme, küçültülmemiş, iş iptal edilince kapanıyor).


## GÖREV-25: sayfanın kendi sorgusu (eklenti 0.20.0, 17 Kasım 2026)

**Kullanıcı kararı (17 Kasım 2026).** Eklenti, bir sitenin kendi sekmesinden, o sayfanın ziyaretçi için zaten yaptığı herkese açık
sorguları gönderebilir; POST da buna dahildir. Kapsam: fiyat sorgusu ve ev listesinin devamı (sayfalama, "daha fazla yükle"). Alanlar
yalnız sayfanın kendi gönderdiği alanlardır, değerler sayfanın biçimindedir. Yasak olan aynen kalır: giriş, hesap, ödeme, rezervasyon,
sepet, kişisel bilgi, iletişim formu, doğrulama çözme. Eklenti tıklamaz, yazı yazmaz; isteği sayfanın betiği gibi gönderir. Çerezleri,
parolaları ve geçmişi okumaz, programa taşımaz; istek sitenin kendi sekmesinden gittiği için tarayıcı o sitenin oturumunu kendisi
kullanır.

- **Öğe türü `sorgu`.** Program öğeyi `{tur: "sorgu", alan_adi, yol, yontem, alanlar, sayfa?}` olarak verir. Eklenti
  (`background.js` `doQuery`): sekme o sitede değilse önce sitenin sayfasına gider (`sayfa`, yoksa `https://<alan adı>/`); sekmenin
  kökeninin alan adı sorgunun alan adıyla aynı olmalıdır; aralık kuralını bekler; isteği sayfanın kendi dünyasında (`MAIN`) `fetch` ile,
  `credentials: "same-origin"`, `X-Requested-With: XMLHttpRequest` ve POST'ta `application/x-www-form-urlencoded; charset=UTF-8`
  gövdesiyle gönderir; cevabın son adresi yine o alan adında olmalıdır. Sonuç: durum, HTTP durumu, son adres, başlıklar, gövde
  (base64) ve `gonderilen` (yöntem, adres, alanlar, zaman).
- **İzinli liste.** Programın yapılandırmasında, şirketin `inventory.extension_queries` alanında durur (alan adı, yol, yöntem, alan
  adları sırasıyla, amaç; `studio/extension_queries.py` `allowed_from_sites`); kapalı şirketin sorgusu listeye girmez. Program listeyi
  oturum görünümünde (`izinli_sorgular`, yalnız oturumun alan adı) ve Ayarlar → Tarayıcı eklentisi'nde ("İzinli sorgular") gösterir.
- **İki tarafta aynı kural** (`studio/extension_queries.py` `refusal`, `eklenti/logic.js` `queryRefusal`; bir Python testi iki listeyi
  karşılaştırır): yöntem yalnız GET ya da POST; yol `/` ile başlar, `?`, `#`, `..` ve tam adres taşımaz; alan adı ve yol yasak listede
  değil; alan adı, yol ve yöntem izinli listede; alanlar listedeki adların alt kümesi ve aynı sırada; en çok 40 alan, değer başına 2000
  karakter. Yasak liste: yolda `login`, `account`, `password`, `checkout`, `payment`, `cart`, `order`, `reserve`, `reservation`,
  `contact`, `inquiry`, `subscribe`, `profile`, `guest`, `owner`, `save`, `favorite`, `email`, `phone`, `review` gibi sözcükler (camelCase
  da bölünür; `addToCart` → cart) ve `book`, `booking`, `my` yol parçaları; alan adlarında ödeme ve giriş servisleri (paypal.com,
  stripe.com, accounts.google.com, …) ve `login.`, `secure.`, `checkout.`, `pay.`, `book.`, `my.` gibi alt alan adları. Reddedilen sorgu
  eklentiye hiç gitmez (program tarafı) ya da gönderilmez (eklenti tarafı, `reddedildi`). Düz `istek` öğesi artık yalnız GET'tir.
- **Kayıt.** Programın ham kaydı (`raw/eklenti/<tarih>/`, toplayıcıda kendi ham deposu) cevabı sorgunun yöntemi, yolu, alanları, adresi
  ve zamanıyla tutar (`sorgu`).
- **Yalnız eklentiyle okunan şirket** (`inventory.extension_only`, RealJoy): eklenti eşleşmemiş, bağlı değil ya da iş programın kendi
  tarayıcısına devredilmişse şirket atlanır ve kaydedilir; programın kendi tarayıcısı ve doğrudan istek bu sorguları göndermez.
- **Deneme.** "Sorunlu sitelerden birer sayfa dene" sayfalardan sonra izinli her sorgudan birer örnek gönderir (`EXTENSION_TRIAL_QUERIES`;
  sitenin kendi aralığıyla, RealJoy 20 sn).
- **Sürüm.** Eklenti 0.20.0. Yeniden yükleme: Chrome'da `chrome://extensions` → "30A Studio Yardımcısı" kartındaki yenile düğmesi;
  kartta 0.20.0 yazmalı; programda Ayarlar → Tarayıcı eklentisi "Bağlı" ve sürüm 0.20.0 göstermeli.
- **Test.** `tests/test_gorev25.py` (kurallar, yasak yollar ve alan adları, iki tarafın listeleri, yapılandırmadan liste, deneme),
  uçtan uca `tests/test_extension_e2e.py` (Playwright'in Chromium'u, geçici profil, yerel sayfa: izinli sorgu tam verilen alanlarla
  gider; yasak yol, listede olmayan yol, fazladan alan ve düz isteğin POST'u eklentinin kendisinde reddedilir; başka alan adı Python
  tarafında sınanır).
