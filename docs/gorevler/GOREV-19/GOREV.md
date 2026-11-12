GÖREV-19 — Claude çağrılarında iki boşa harcamayı kapat (yan çağrı ve önbelleğe yazma), sonra v0.20.0'ı main'e al

BAĞLAM
GÖREV-18 (dal `gorev-18-token-kontrolu`, son commit `68fa4af`, uygulama 0.20.0, şema 19) kabul edildi. Program klasörü: `C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`. main bugün `a49c6d0` (`v0.19.0`); GÖREV-18 dalı henüz main'e alınmadı.

GÖREV-18'deki tek gerçek çalışma (başlık değerlendirme, Opus 5.5, tek çağrı; kayıt: `docs/gorevler/GOREV-18/gercek-calisma/calisma.json`) iki boşa harcama gösterdi:

1. **Yan çağrı.** Claude Code, cevabı veren modelin yanında kendi kendine bir Haiku 5.5 çağrısı yaptı ve görev metninin tamamını bir kez daha okuttu: 105.311 token okundu, 24 token yazıldı. Bu çağrı sonuç zarfının `usage` alanında görünmüyor, yalnız `modelUsage` alanında görünüyor. Okunan token bu yüzden ikiye katlanıyor (111 bin yerine 216 bin). 24 tokenlik çıktı, bunun oturuma ad veren arka plan isteği olduğunu düşündürüyor. Claude Code belgesi (https://code.claude.com/docs/en/env-vars) `CLAUDE_CODE_DISABLE_TERMINAL_TITLE` için şunu söylüyor: `1` yapılırsa terminal başlığı güncellemeleri kapanır ve oturum adını üreten küçük model isteği de atlanır. Bunun bizim çağrımızdaki yan çağrıyı gerçekten kapattığı henüz doğrulanmadı.
2. **Önbelleğe yazma.** Tek çağrıda istemin tamamı bir saatlik önbelleğe yazılıyor (`cache_creation_input_tokens: 110034`, `ephemeral_1h_input_tokens`). Bir saatlik önbelleğe yazma, normal girdinin 2 katı bedel tutuyor. Adımlarımız tek çağrılı olduğu için bu önbellek bir daha okunmuyor. Aynı belgede `DISABLE_PROMPT_CACHING=1` bütün modeller için önbelleği kapatıyor.

Bu iki harcama kapanmazsa iki tonlu bir video metni tahmin edilen 655 bin token yerine yaklaşık 1,1 milyon token okur. Kullanıcı ilk gerçek video metnini bu görevden sonra yazdıracak.

Bu görev küçüktür. Alt ajan kullanma; işi kendin, sırayla yap.

Kullanıcı bu görev için kendi mesajında şu izinleri veriyor:
- Adım 2'deki küçük gerçek Claude çağrıları (sınırları Adım 2'de),
- main'e alma ve `v0.20.0` etiketi.

KESİN SINIRLAR
- Gerçek Claude yalnız Adım 2'deki küçük doğrulama çağrıları için çalıştırılır. Programın gerçek adımları (başlık, değerlendirme, video metni) gerçek Claude ile çalıştırılmaz.
- `data/` klasörüne dokunulmaz. Bu görevde şema değişmez ve program gerçek veriyle açılmaz.
- Talimat dosyalarının içeriğine dokunulmaz. Çalışma ağacında kullanıcının Ayarlar'dan yaptığı bir talimat değişikliği varsa CLAUDE.md kuralına göre ilk commit olarak eklenir.
- Housing Atlas klasöründe hiçbir dosya değiştirilmez.
- Bu iki ayar yalnız programın başlattığı Claude alt süreçlerinin ortamına eklenir. Windows'un kullanıcı ya da sistem ortam değişkenlerine, kullanıcının kendi Claude Code ayar dosyalarına yazılmaz; kullanıcının kendi Claude Code oturumları etkilenmemelidir.
- Gerçek sitelere istek yapılmaz. Bilgisayarda zamanlanmış görev oluşturulmaz.

==================================================
ADIM 1 — Dal ve ayarlar
==================================================
1. `gorev-18-token-kontrolu` dalının son commit'inden (`68fa4af`) `gorev-19-yan-cagri-onbellek` dalını aç.
2. `studio/ai/runner.py` içindeki alt süreç ortamına (`ISOLATION_ENV`) iki değişkeni ekle:
   - `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`
   - `DISABLE_PROMPT_CACHING=1`

   `build_env`, bir Claude Code oturumunun içinden çalışırken `CLAUDE_CODE_` ile başlayan değişkenleri siliyor ve ardından `ISOLATION_ENV`'i ekliyor; yeni değişkenlerin bu durumda da alt sürece ulaştığını testle göster.
3. Bu ayarlar programın bütün Claude çağrılarında geçerlidir (başlık adımları, video metni zinciri, kullanım ölçümü). Ayarlar ekranına yeni bir seçenek ekleme; değişkenler kodda, gerekçesiyle birlikte durur.

==================================================
ADIM 2 — Küçük gerçek çağrılarla doğrulama
==================================================
Amaç: iki ayarın gerçekten işe yaradığını en az harcamayla görmek. Doğrulama küçük istemlerle yapılır; 110 bin tokenlik gerçek malzeme kullanılmaz.

**Nasıl.** `work/gorev-19/` altında küçük bir betik yaz. Betik programın kendi çalıştırıcısını (`studio.ai.runner`) kullanır; komut gerçek adımlardaki gibi olur: araçsız (`--tools ""`), tek tur (`--max-turns 1`), talimat `--append-system-prompt-file` ile, görev standart girdiden. Model `claude-sonnet-5-5`, efor düşük. Sonnet seçildi, çünkü ucuzdur ve yan çağrı (Haiku) `modelUsage` içinde ayrı bir model olarak görünür. Talimat iki satır, görev tek satır olsun; cevap küçük bir JSON olsun. Her çağrının sonuç zarfını (`usage`, `modelUsage`, `total_cost_usd`) `docs/gorevler/GOREV-19/dogrulama/` altına kaydet.

**Çağrılar.**
1. **Karşılaştırma çağrısı (eski ortam):** iki yeni değişken olmadan. Beklenen: `modelUsage` içinde Haiku var; `usage` içinde `cache_creation_input_tokens` sıfırdan büyük.
2. **Yeni ortam:** iki değişkenle. Beklenen: `modelUsage` içinde yalnız cevap veren model var; `cache_creation_input_tokens` ve `cache_read_input_tokens` sıfır, girdinin tamamı `input_tokens` içinde.

**Sonuca göre.**
- Karşılaştırma çağrısında Haiku hiç görünmezse yan çağrı küçük istemde oluşmuyor demektir. O zaman iki çağrıyı yaklaşık 20 bin tokenlik bir malzemeyle yinele (malzeme olarak depodaki bir belgeyi, örneğin `CALISMA_MANTIGI.md`'yi görev metnine koy).
- Yeni ortamda Haiku hâlâ görünüyorsa yan çağrının ne olduğunu araştır: Claude Code belgesindeki ortam değişkenleri sayfası ve maliyet sayfasındaki "background token usage" bölümü, gerekirse `--debug` çıktısı. Bulduğun ayarı tek tek dene. Kullanıcının kendi oturumlarını ya da hesabını etkileyen, ağ ya da özellik bayraklarını topluca kapatan bir ayarı (örneğin `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`) ancak başka yol yoksa dene ve yan etkisini rapora yaz.
- Yan çağrı hiçbir ayarla kapanmıyorsa uğraşmayı bırak ve rapora yaz. Program onu zaten harcamaya sayıyor ve tahmine ekliyor; bu davranış kalır.
- Önbellek ayarı beklenen sonucu vermezse (örneğin önbelleğe yazma sürüyorsa) belgedeki öbür değişkenlere bak (`DISABLE_PROMPT_CACHING_OPUS`, `FORCE_PROMPT_CACHING_5M`) ve hangisinin ne yaptığını aynı küçük çağrılarla ölç.

**Harcama sınırı.** En çok 8 gerçek çağrı. Tek bir çağrı 30 bin tokeni geçmez. Bütün doğrulamanın toplamı 150 bin tokeni geçmez; geçecekse dur ve o ana kadarki sonucu raporla. Beklenen toplam 10–60 bin token arasındadır. Başlamadan önce kendi tahminini, bitince gerçek toplamı rapora yaz.

==================================================
ADIM 3 — Programdaki izler
==================================================
1. Yan çağrı kapandıysa tahmine eklenen yan çağrı payı kendiliğinden sıfıra iner (pay, önceki tek çağrıların ortancasından geliyor). Bunu testle göster. Yan çağrı bir gün yeniden görünürse iş günlüğündeki "Claude Code'un kendi yan çağrısı … okudu" satırı ve harcamaya sayılması aynen kalır.
2. Tahminin karakter/token oranını (1,85) ve Claude Code'un kendi sistem metni payını (4.500) değiştirme; ilk gerçek çalışmalardan sonra ölçüme göre bakılacak.
3. Önbellek kapanınca bedel hesabı değişir (girdi normal fiyattan). Programın gösterdiği bedel Claude Code'un zarfındaki `total_cost_usd` değeridir; ayrıca bir şey yapmak gerekmez. Yalnız, ekranda ya da belgelerde "önbelleğe yazma" diye geçen bir açıklama varsa güncel duruma göre düzelt.

==================================================
ADIM 4 — Testler, belgeler, main ve etiket
==================================================
1. Testler: ortamda iki değişkenin bulunduğu (bir Claude Code oturumunun içinden çalışırken de); yan çağrısız kayıtlarda tahmine pay eklenmediği. Tam takım: `.venv\Scripts\python.exe -m pytest -q` ve `node --test tests/frontend.test.mjs`.
2. Belgeler: `docs/M15-CLAUDE-ADIMLARI.md` ("Tek çağrı düzeni, tahmin ve sınırlar" bölümüne iki ayar, gerekçesi ve doğrulama sonucu), `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`, `README.md`. Uygulama sürümü 0.20.0 kalır (0.20.0 henüz yayımlanmadı).
3. Dalı push et ve GitHub'daki test çalışmasının sonucunu bekle. Çalışma takılır ve 20 dakikada kesilirse hangi testin beklediğini GÖREV-18'de eklenen yoldan oku (`https://api.github.com/repos/bemonths/tatilya/check-runs/<iş kimliği>/annotations`) ve çalışmayı bir kez yeniden başlat. Takılan test belliyse ve düzeltmesi küçükse düzelt; değilse testin adını ve yığını rapora yaz, yöneticiye bırak.
4. Son commit'in test çalışması en az bir kez başarıyla bittiyse main'i bu commit'e fast-forward ile getir ve push et. "v0.20.0" açıklamalı etiketini koy; mesajı: "v0.20.0 — Claude adımları tek çağrılı: tahmin, sınırlar, işletme adı ve başlık denetimleri". Test çalışması başarıyla bitmediyse main'e alma; rapora yaz.

==================================================
TESLİM
==================================================
`docs/gorevler/GOREV-19/` altında:
- `GOREV.md` (bu dosya) ve `RAPOR.md`,
- `dogrulama/`: her gerçek çağrının sonuç zarfı.

Raporda şunlar olsun:
- Her gerçek çağrı için bir satırlık tablo: ortam (eski ya da yeni, hangi değişkenler), model, okunan token (`input_tokens`, önbelleğe yazılan, önbellekten okunan ayrı ayrı), yazılan token, `modelUsage` içindeki modeller, bedel.
- Yan çağrının ne olduğu ve hangi ayarla kapandığı; kapanmadıysa neler denendi.
- Önbellek ayarının etkisi: aynı istem için eski ve yeni bedel.
- Doğrulamanın tahmini ve gerçek toplam harcaması.
- Bu sonuçlara göre programın yeni tahminleri: başlık önerisi, başlık değerlendirme, bir tonlu ve iki tonlu video metni (okunan, yazılan, toplam).
- main ve etiket durumu, test çalışmalarının sonucu.

Kullanıcıya son mesajın yalnız şu olsun: "GÖREV-19 bitti, dal gorev-19-yan-cagri-onbellek, son commit <hash>" ve varsa tamamlanamayan adımlar.
