# M16 — Tarayıcı eklentisi: "30A Studio Yardımcısı" (GÖREV-14, v0.16.0)

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
- Eklenti tıklamaz, yazı yazmaz, form doldurmaz; giriş ve ödeme sayfalarını okumadan atlar; doğrulamayı kullanıcı yapar (çözme servisi,
  gizlenme, parmak izi sahteciliği, proxy, IP değiştirme yoktur).

## Hız ve doğrulama

- Aynı alan adında iki sayfa arası en az 8 sn (Ayarlar'dan 3–120 sn); bir anda tek sayfa.
- Doğrulama sayfası programın işaretleriyle tanınır (`CHALLENGE`, `BLOCKED`; `eklenti/logic.js` aynı metni taşır, bir Python testi
  denetler). Görülürse eklenti pencereyi öne getirir, bildirim gösterir, programa bildirir (iş panelinde "Kullanıcı doğrulaması
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
- realjoy.com için kiralama okuyucusu (adaptör) yok: eklenti sayfayı okuyabilir ama fiyat çıkarılamaz (yönetici kararı).
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
