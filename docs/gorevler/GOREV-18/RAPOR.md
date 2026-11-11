# GÖREV-18 Raporu — Claude adımlarında token kontrolü, işletme adı ve başlık denetimleri

Tarih: 11 Kasım 2026 · Dal: `gorev-18-token-kontrolu` · Uygulama `0.20.0` · Şema `19` (değişmedi)

## Kısaca

- Programın bütün Claude adımları artık **tek çağrı**: program adımın bütün malzemesini istemin içinde verir, Claude hiçbir araç kullanmadan tek
  turda JSON ile cevap verir, program cevabı denetleyip çıktı dosyasını kendisi yazar. Malzeme hiçbir yerde kısaltılmadı.
- Her Claude işi başlamadan önce **tahmin** gösterilir ve "Başlat" istenir; Ayarlar'da **tek çağrı** (250 bin) ve **iş başına** (1,5 milyon) sınırı
  var; bitince **tahmin ile gerçek** yan yana, gerçek 1,5 katı geçerse kırmızı uyarı.
- **Tek gerçek ölçüm** (izinle, geçici kopyada): köpek fikrinin değerlendirmesi eskiden 416 bin token okumuştu, şimdi Opus **111 bin** okudu (1 çağrı,
  41 sn, sonuç aynı: "veriyle dolmuyor"). Ama Claude Code aynı çağrıda kendi kendine bir **Haiku çağrısı** daha yaptı ve istemi bir kez daha okudu
  (105 bin token, bedelin %5'i). İkisi birlikte **216 bin** eder; kullanıcının 200 bin sınırını bu yan çağrı yüzünden geçti (aşağıda, "Tek gerçek
  ölçüm"). Program bu yan çağrıyı artık harcamaya sayıyor ve tahmine ekliyor.
- **İşletme adı denetimi** (kırmızı) ve **başlık ve kapak uyarıları** (sarı) eklendi.
- Testler iki eski hatayı buldu ve düzeldi: video metninin ikinci çeviri dilimi hata veriyordu; bölüm yazıcısının okunur dosyası girdisinin üstüne
  yazılıyordu.

## Adım 1 — v0.19.0 main'e alındı

| | Konum | CI |
|---|---|---|
| Talimat commit'i (dalın ilk commit'i) | `a7d414c` — "talimat: işletme adları geçmez (ortak.md); mahalle konu evreninde 'yeme içme' (baslik.md)" | — |
| main | `a49c6d0` (fast-forward `988ca8d..a49c6d0`, itildi) | main çalışması 43053256607: **başarılı** (4 dk 24 sn) |
| Etiket `v0.19.0` (açıklamalı, itildi) | `a49c6d0` — "v0.19.0 — arayüz düzeltmeleri: İşler panelinde temizleme, Ayarlar düzeni, tek pencere" | 43053261163: rapor yazılırken "sürüyor" (takıldı, aşağıda) |
| Dal `gorev-18-token-kontrolu` | güncel main'den | `49fa9db`: 43068491888 takıldı, yeni 20 dakikalık sınırla "zaman aşımı" bitti · `82f29d7`: 43071944301 **başarılı** (test adımı 4 dk 50 sn) · son commit: aşağıda |

**CI'daki takılma.** `a49c6d0`'ın görev dalı çalışması (43032939565, 13:51'de başladı) ve GÖREV-17 raporunda "sürüyor" görünen main çalışması
(43011750701, 988ca8d, 11:24'te başladı) saatlerdir "Test" adımında "sürüyor". Aynı commit'lerin öbür çalışmaları (988ca8d'nin etiket çalışması,
a49c6d0'ın main çalışması) 4–5 dakikada başarıyla bitti; yani aynı kod bir çalışmada geçiyor, öbüründe bir test takılıyor. Günlükler GitHub'a girişsiz
okunamadığı için hangi testin takıldığı görülemedi; yerelde hiçbir turda takılma olmadı. Bu dalda: iş akışına zaman sınırı (iş 30 dk, test adımı
20 dk; takılan çalışma 6 saat yerine yarım saatte biter) ve pytest'e `faulthandler_timeout = 600` (10 dakikadan uzun süren bir test bütün
iş parçacıklarının yığınını günlüğe basar) eklendi. Bu dalın ilk itişinde de (49fa9db) aynı takılma oldu ve sınır işe yaradı (20. dakikada "The action
'Test' has timed out after 20 minutes."). Günlük girişsiz okunamadığı için iş akışı bir adım daha kazandı: test adımı başarısız olur ya da durdurulursa
günlüğün son 120 satırı (çalışan testin adı; 10 dakikadan sonra yığınlar) GitHub'da bir "annotation" olarak yazılır ve girişsiz API ile okunur
(`https://api.github.com/repos/bemonths/tatilya/check-runs/<iş kimliği>/annotations`); testler `-v` ile çalışır ve 16 dakikada kesilir. Bu hâliyle ilk
çalışma (82f29d7) takılmadan geçti; bir sonraki takılmada hangi testin beklediği bu yoldan okunabilir. Kök neden bulunmadı.

## Adım 2 — Bütün Claude adımları tek çağrılı ve araçsız

Kapsam: `baslik`, `baslik_degerlendirme`, `metin_plan`, `metin_plan_elestiri`, `metin_bolum`, `metin_birlestirme`, `metin_giris_kapanis`,
`metin_son_okuma`, `metin_ceviri`. Kullanım ölçümü (Haiku, tek tur) değişmedi.

1. **Malzeme istemin içinde.** Girdi dosyaları eskisi gibi aynı adla ve içerikle çalışma klasörüne yazılıyor; program hepsini görev metninde
   `<<<DOSYA ad>>>` … `<<<DOSYA SONU ad>>>` bölümleri olarak veriyor. Görev metni (`gorev.md`) önsözle başlıyor (görev metnindeki birebir cümle).
   Görev satırları "Çalışma klasöründeki dosyalar (hepsini oku)" yerine "Verilen dosyalar (hepsi aşağıda)" diyor; "yalnız bu dosyayı yaz" ve
   "bitirince kısa bir özet yaz" satırları kalktı (özet `notlar` alanına). Talimat dosyalarına dokunulmadı.
2. **Araç yok, tek tur.** Komut: `--tools "" --max-turns 1`, `--allowedTools` yok. Komut satırının `--json-schema` seçeneği kullanılmadı: Housing
   Atlas'ın yöntemi şemayı sistem talimatında verip cevabı programın kendisi denetlemek; şema talimatın sonunda zaten var.
   JSON ayıklama Housing Atlas'ın `parse_json` kuralı: çıplak, kod çiti içinde ya da önünde/arkasında metinle. Ayıklanamazsa "geçersiz cevap".
3. **Talimatlar değişmedi**; bölüm adları talimattaki dosya adlarıyla aynı.
4. **Geçersiz cevap** bir kez yeniden isteniyor (tek tur, önceki cevap ve hatalarla). Başlık adımlarında bu GÖREV-18'den önce yoktu (çıktı şemaya
   uymazsa çalışma hata veriyordu); şimdi ikinci çağrı yapılıyor. Aday başına anlam sorunları (yanlış kanıt kimliği gibi) eskisi gibi adayın
   kartında gösteriliyor ve o aday seçilemiyor; bunlar için ikinci çağrı yapılmıyor (öbür adaylar kullanılabilir; "Düzeltme iste" duruyor).
5. **Büyük malzeme**: tahmini tek çağrı sınırını aşan istem gönderilmiyor; ekran ve iş günlüğü nedenini söylüyor. Çeviri eskisi gibi dilimlere
   bölünüyor (6.000 kelime), her dilim tek çağrı.
6. **Canlı izleme**: "Tur 3/30 · Okuyor" satırları yok. İş günlüğü: "İstem hazırlandı: 9 dosya istemin içinde; tahmin: yaklaşık 89 bin token
   okunacak, 8 bin yazılacak." → "Claude düşünüyor; cevap tek seferde gelecek." → "Claude düşünüyor (16 sn)" → "Cevap geldi: 111 bin token okundu,
   4 bin token yazıldı · 41 sn." → "Cevap doğrulandı (JSON ve şema); program çıktıyı yazdı." → "Harcama: tahmin 97 bin, gerçek 114 bin token."
   (Bu satırlar gerçek çalışmanın günlüğünden.)
7. **Cevap kesilirse**: Claude Code'un çıktı sınırı Opus 5.5 ve Sonnet 5.5 için zaten 128.000 (sonuç zarfının `modelUsage.maxOutputTokens`'ı; 10 Ekim
   çalışmalarında da böyle); en büyük ölçülen başlık çıktısı düşünmeyle 65 bin. Yükseltmeye gerek görülmedi. Kesik cevap (`stop_reason: max_tokens`
   ya da Claude Code'un çıktı sınırı iletisi) "geçersiz JSON" değil, ayrı durum: günlüğe "Cevap uzunluk sınırında kesildi; kabul edilmedi." yazılıyor,
   kesik cevap kullanılmıyor ve geri verilmiyor, "daha kısa yaz" notuyla bir kez yeniden isteniyor.
8. **Sessiz kırpma yok**: hiçbir adımda malzeme kesilmiyor ya da özetlenmiyor (test: bölümler dosyalarla bire bir aynı; tek çağrı sınırının
   altına inilsin diye hiçbir şey kısaltılmıyor, çalışma başlamıyor).
9. **Eski düzen kalktı**, ayar olarak sunulmuyor; tur sınırı ayarı kalktı (eski ayar dosyalarındaki `claude_max_turns_*` okunmuyor). Çalıştırıcı
   araç ve kural verebiliyor (Housing Atlas'tan gelen yetenek), hiçbir adım kullanmıyor; sahte claude araç ya da birden çok tur verilirse hata
   veriyor, yani hiçbir test eski düzenle geçemez.

**Paralel çalışma**: "Aynı anda en çok Claude oturumu" 1–8, başlangıç 6. Program ayarları kaydederken bütün alanları yazdığı için GÖREV-18'den önce
kaydedilmiş dosyadaki 3 (eski başlangıç değeri) kullanıcının seçimi sayılmıyor ve 6'ya dönüyor; başka bir değer kalıyor. Bundan sonra kaydedilen dosya
`ayar_surumu: 18` taşıyor ve ne yazıyorsa o geçerli. Gerçek ayar dosyasında 3 vardı (kullanıcı programı kendisi kullanmıyor); program onu 6 olarak
okuyor (gerçek veriyle açılışta Ayarlar'da 6 göründü). Dosyanın kendisi değişmedi; ayarlar bir kez kaydedilince 6 ve `ayar_surumu` yazılır.

## Adım 3 — Malzeme: aynı bilgi, aynı içerik

- **Kanıt**: `tests/test_gorev18.py` her adım için (başlık, değerlendirme ve video metninin bütün oturumları) görev metnindeki bölümlerin
  çalışma klasöründeki girdi dosyalarıyla aynı ad, aynı sıra ve bire bir aynı içerikte olduğunu, fazladan bölüm olmadığını ve her bölümün talimatta ya
  da görev satırlarında adının geçtiğini denetliyor. Girdi dosyaları GÖREV-18'den önceki düzenin girdi dosyalarıdır (aynı hazırlık işlevleri).
- **İzin verilen iki kısaltma uygulanmadı, çünkü gerek yoktu**: (1) şema bugün yalnız sistem talimatının sonunda veriliyor, ayrıca bir bölüm olarak
  verilmiyor; aynı içerik iki kez geçmiyor. (2) `onceki_oneriler.md` zaten yalnız tarih, bölge, aile, İngilizce ve Türkçe başlık ve "seçildi"
  durumunu taşıyor; önceki önerilerin analizleri hiç verilmiyordu. Görev metninin istediği "tek satırlık konu" bugün dosyada yok; eklenmedi
  (eklemek malzemeyi büyütür; tekrarı önlemeye katkısı yöneticinin kararı).
- **Ölçüm tablosu**: `olcum.md` (ve `olcum.json`). Her adım için `ortak.md`, ses, ton, adımın talimatı, şema ve her girdi dosyası karakter ve tahmini
  token olarak. Başlık çalışmasında malzemenin üçte ikisi 30A veri özeti (113.557 karakter, ~61 bin token).

**Kısaltma önerileri (uygulanmadı; karar yöneticinin):**

| Adım | Malzeme | Kazanç (tahmini, çağrı başına) | Kalite riski |
|---|---|---|---|
| Konu ve başlık · mahalle | `veri_ozeti_30a.md` yerine yalnız 30A karşılaştırma blokları (fiyat, plaj, iklim özetleri) | ~40–45 bin token (61 binlik özetin büyük kısmı) | Mahalle başlığı 30A'yı karşılaştırma için kullanıyor; başka bir 30A bilgisi (kural, etkinlik) kancaya giremez |
| Başlık değerlendirme · mahalle | aynı | ~40–45 bin | aynı |
| Konu ve başlık (hepsi) | `kanal_arastirmasi.md` (13.434 karakter) yerine izleyici soruları ve rakip başlıklar bölümü | ~4–5 bin | Arama hacmi ve rekabet bilgisi kaybolur |
| Başlık değerlendirme | `baslik_olculeri.md` (`baslik.md`'nin kopyası, 3.572 karakter) | ~2 bin | Değerlendirme iyi başlığın ölçülerini kaybeder |
| Video metni · son okuma | `paket_ozeti.md` (38.502 karakter) yerine yalnız metinde kullanılan kanıt satırları | ~15 bin (ton başına) | Son okuyucu, metnin söylemediği ama paketin söylediği bir düzeltmeyi göremez |
| Video metni · plan eleştirisi | `paket_ozeti.md` ve `sayilar.csv` yerine planın gösterdiği satırlar | ~20 bin | Eleştirmen planın kaçırdığı güçlü bir kanıtı göremez |

## Adım 4 — Tahmin, sınır ve gerçek harcama

1. **Başlamadan önce tahmin ve onay.** Konu ve başlık önerisi, değerlendirme, "İngilizcesini Claude yazsın", "Düzeltme iste", "Metni yaz", "Bu tonla da
   yaz", "Planı yeniden yap" önce tahmini gösterip "Başlat" istiyor (ekran 01, 05). Satırlar: kısım, çağrı, okunacak, yazılacak, toplam, model ve efor;
   video metninde plan ve her ton ayrı satırda ve toplamla ("Plan: 2 çağrı, yaklaşık 107 bin token · Araştırmacı dost: 10 çağrı, yaklaşık 274 bin token
   · Belgesel anlatıcı: 10 çağrı, yaklaşık 274 bin token · Toplam: yaklaşık 655 bin token"). Okunan istemin boyutundan (karakter ÷ 1,85 + Claude
   Code'un kendi sistem metni 4.500; video metninde çalışmadan önce var olmayan girdiler için önceki oturumların ortancası ya da planın kelime
   bütçesinden), yazılan adımın önceki çalışmalarının ortancasından, yoksa Ayarlar'daki adım başına "çıktı varsayımı"ndan. "Devam" tahmin göstermiyor.
2. **Sınırlar** Ayarlar → Claude → Token sınırları: tek çağrı (250 bin) ve iş başına (1,5 milyon). Tahmin aşıyorsa "Başlat" düğmesi yok, sunucu da
   başlatmıyor; ekran neyin büyük olduğunu yazıyor.
3. **Çalışırken.** Video metni zinciri her çağrıdan sonra gerçek toplamı güncelliyor; iş başına sınıra ulaşınca yeni çağrı açılmıyor, çalışma "Token
   sınırına ulaşıldı" ile duruyor ve "Devam"ı bekliyor; biten adımlar kalıyor; "Devam" sınırı o andan yeniden sayıyor. Başlık çalışmasında sınıra
   ulaşılmışsa ikinci çağrı yapılmıyor.
4. **Bitince.** İş kartında ve çalışma ekranında "Harcama: tahmin X · gerçek Y token (N çağrı)" (ekran 02, 06); gerçek 1,5 katı geçerse kırmızı
   "Beklenenden fazla harcandı: tahmin X, gerçek Y" (ekran 10, sahte claude). Sol menüdeki Claude kullanımı kutusu son işin gerçek harcamasını gösteriyor
   (ekran 11).
5. **Kayıt.** Her çağrının okunan, önbellekten okunan, yazılan token'ı, modeli ve süresi çalışma kaydında (`calisma.json` → `calisma_sonucu`,
   `cagrilar`, `tahmin`, `harcama`; metriklerde `duzen`, `cagri`, `side_tokens`); video metninde ayrıca `harcama.json`. Ayarlar → Claude
   kullanımı'nda adım başına ortanca ve en yüksek harcama tablosu (tek çağrılı çalışmalar ve eski çok turlu çalışmalar ayrı sütunda; ekran 04).

## Adım 5 — Model ve efor değişmedi

Başlangıç değerleri aynı (test: `test_model_and_effort_are_unchanged_and_the_sessions_default_is_six`). Ayarlar → Claude'daki model tablosunda her adımın
yanında son çalışmalarının ortanca harcaması var (tek çağrılı yoksa eski düzenin ortancası "eski düzen" diye; ekran 03). Tur sütunu kalktı; yerine
"çıktı varsayımı".

## Adım 6 — İki program denetimi

**6a İşletme adı (kırmızı).** Liste her denetimde veriden kuruluyor (`studio/text/businesses.py`): restoranlar, kiralama şirketleri, otel / B&B inn /
kiralama acentesi kategorisindeki konaklama ilanları, günlük ihtiyaç noktalarının adları ve markaları. Girmeyenler: bölgeler ve mahalle kayıtları,
destinasyonun adı, 30A, South Walton; adında County, State Park, Department, Sheriff, Library, Visit South Walton, NOAA, FDOT, Beach Access,
Regional, Public … geçenler. "Rosemary Beach®" adlı şirket yer adıyla aynı olduğu için alınmıyor; yer adı hiçbir zaman işaretlenmiyor; "Rosemary
Beach Realty" gibi yer adını içeren bir ad yalnız tam adıyla işaretleniyor. Gerçek veride 256 ad. Dört harften kısa adlar alınmıyor; tek kelimelik
adlar ("Target", "Lookout", "Citizen" gibi aynı zamanda sıradan İngilizce kelimeler) yalnız verideki büyük harfle eşleşiyor. Ayarlar → Uyarı
ifadeleri → "İşletme adları: ekle / hariç tut" (`isletme_adlari.txt`, "+ Ad" / "- Ad"; ekran 09). Denetim video metninde cümleye bağlı kırmızı
bulgu "işletme adı: <ad>" (ekran 07) ve başlık adaylarında İngilizce başlıkta ya da kapak fikrinde kırmızı işaret (ekran 08); kimseyi durdurmuyor.

**6b Başlık ve kapak uyarıları (sarı).** Aday kartında ve kullanıcının düzenlediği başlıkta (yazarken sunucuya sorulur):
- konu ilk 40 karakterde değil: konu adayın bölgesi (30A geneli için "30A", mahallede mahallenin adı); ek sayılmıyor;
- kapak yazısı 3 kelimeden uzun ya da başlıktaki kelimeleri tekrar ediyor (and, or, the, a, of, in, to, for, vs … ve "30A" sayılmıyor);
- başlıkta 2'den fazla tamamı büyük harfli kelime (rakam içeren "30A" sayılmıyor).
**Kapak yazısı** kapak fikrinden yalnız fikir onu açıkça adlandırıyorsa ayrılıyor: "büyük yazı '…'", "başlık '…'", "büyük harflerle '…'", "kapak yazısı
'…'". Gerçek verideki 30 kapak fikrinin 12'sinde ayrılabildi; öbür 18'inde yalnız etiketler var ("üzerinde iki etiket: 'JAN ~$8.6K' ve …") ve program
hangisinin kapak yazısı olduğunu tahmin etmiyor; o adaylarda kapak uyarısı kurulmuyor. Uyarı yalnız bilgi; aday reddedilmiyor.

**6c** Ayarlar → Hakkında kartı: "Veriden video metnine" — bugün kullanılabilenler (konu ve başlık, kendi başlığın değerlendirilmesi, tonlarla video
metni, Türkçesi ve denetim, tek çağrı ve tahmin); sonraki aşama: ilk gerçek video metinleri ve ölçümü, sonra görsel plan, video üretimi, yayın.

## Adım 7 — Testler, ölçüm, gerçek ortam

### Testler

Tam takım yerelde art arda 3 kez (son kodla, ekran görüntüleri ve gerçek ölçümden sonra):

| Tur | Python | Ön yüz |
|---|---|---|
| 1 | 1115 geçti, 2 atlandı (7 dk 30 sn) | 120 geçti |
| 2 | 1115 geçti, 2 atlandı (7 dk 16 sn) | 120 geçti |
| 3 | 1115 geçti, 2 atlandı (7 dk 38 sn) | 120 geçti |

Atlanan 2 test eklentinin uçtan uca denemesidir (`STUDIO_EKLENTI_E2E=1` ister; bu görevde eklenti değişmedi). main'de 1095 + 115 idi.

Yeni testler `tests/test_gorev18.py` (20) ve ön yüzde 5 test. Görev metnindeki listenin hepsi sınanıyor: her adımın isteminde talimatta adı geçen bütün
bölümler ve fazlası yok; komutta araç yok ve tur 1; JSON ayıklama (önde ve arkada metin, kod çiti); geçersiz cevapta tek yeniden deneme; çevirinin
dilimleri; tek çağrı sınırını aşan istemde başlatmama (başlıkta ve metinde; metinde tahmini geçip gerçeği aşan çağrıda duraklama); malzemenin
kırpılmaması; bölümlerin dosyalarla aynı içeriği; kesik cevabın ayrı tanınması; tahminin hesaplanması (başlık ve video metni) ve ekranda gösterimi; iş
başına sınırda başlatmama, çalışırken durma ve "Devam"; tahmin ile gerçek ve kırmızı uyarı; Claude Code'un yan çağrısının sayılması ve tahmine
eklenmesi; model ve eforun değişmemesi, oturum ayarının 6 olması ve eski ayar dosyası; işletme adı (yer adıyla çakışan ad dahil) ve Ayarlar'daki
ekleme ve hariç tutma; başlık ve kapak uyarıları; iki tonlu video metni uçtan uca ve toplam çağrı sayısı (22). Eski testlerden eski düzene göre yazılmış
olanlar (tur sayısı, araç listesi, "Okuyor" satırı, tur sınırı ayarı, dosya yazmayan sahte claude) yeni düzene göre güncellendi.

**Testlerin bulduğu iki eski hata (GÖREV-15'ten; gerçek Claude ile hiç çalışmadığı için görülmemişti):**
- Video metninde ikinci ve sonraki çeviri dilimi "Beklenmedik hata: 'list' object has no attribute 'get'" ile duruyordu: önceki dilimlerin terimleri
  yanlış birleştiriliyordu (`merge_terms(terms)` → `merge_terms(*terms)`). Yaklaşık 3.000 kelimeyi aşan bir metin bundan etkilenirdi.
- Bölüm yazıcısının okunur Markdown'ı (`bolum.md`) girdi dosyasıyla aynı adı taşıyordu ve kayıt için saklanan girdinin üstüne yazılıyordu; artık
  `bolum_cikti.md`.

### Ölçüm: eski ve yeni düzen (Claude çağrılmadan, gerçek verinin kopyasında)

| Çalışma | Eski düzen (ölçülen, 10 Ekim) | Yeni düzen (tahmin) |
|---|---|---|
| Konu ve başlık · 30A geneli | 5 tur, 9 araç · 371 bin okunan + 65 bin yazılan · 2,55 $ | 1 çağrı · 92 bin + 54 bin = 147 bin |
| Konu ve başlık · Rosemary Beach | 5–6 tur, 10 araç · 444–460 bin + 53–54 bin · 2,36–2,42 $ | 1 çağrı · 108 bin + 54 bin = 163 bin |
| Başlık değerlendirme | 6 tur, 13 araç · 416 bin + 8 bin · 1,18 $ | 1 çağrı · 110 bin + 8 bin = 118 bin (gerçek: 111 bin + 4 bin, aşağıda) |
| Video metni · plan (2 çağrı) | hesap: ~325 bin | 81 bin + 26 bin = 107 bin |
| Video metni · bir ton (10 çağrı) | hesap: ~765 bin + 82 bin | 192 bin + 82 bin = 274 bin |
| Video metni · bir ton toplam | hesap: ~1,2 milyon | 381 bin |
| Video metni · iki ton toplam | hesap: ~2,0 milyon | 655 bin |

Eski video metni değerleri hesaptır (video metni eski düzende hiç çalışmadı): başlık çalışmalarında okunan toplam, ilk istemle malzemenin ortalama 4 katı
çıktı; bu kat video adımlarına uygulandı. Video metninin yeni tahmininde yazılan değerler Ayarlar'daki çıktı varsayımları (gerçek metin hiç
yazılmadığı için ortanca yok). Ayrıntı ve adım adım parçalar: `olcum.md`.

**Önemli ek:** Yukarıdaki yeni düzen tahminlerinde Claude Code'un yan çağrısı yok. Tek gerçek çağrıda bu yan çağrı ana modelin okuduğunun %95'i
kadar okudu. Bu her çağrıda olursa okunan token ikiye katlanır (bedel etkisi küçük: Haiku ucuz, çağrının bedelinin %5'i). Program ilk gerçek
çalışmadan sonra bu payı tahmine kendiliğinden ekler.

### Tek gerçek ölçüm (kullanıcının izniyle; `gercek-calisma/`)

Gerçek verinin geçici kopyasında (`work/gorev-18/temp-gercek`), program bu dalın koduyla açıldı; Videolar → "Kendi başlığını yaz": "Rosemary Beach'e
köpeğimizle gitsek nasıl olur?", bölge Rosemary Beach, not yok (10 Ekim'deki çalışmanın aynısı). Ekranın tahmini: 1 çağrı, 89 bin okunacak, 8 bin
yazılacak, toplam 97 bin; Opus 5.5 · Yüksek (ekran 01). "Başlat"a basıldı.

| | Eski (10 Ekim, çok turlu) | Yeni (11 Kasım, tek çağrı) |
|---|---|---|
| Çağrı / tur | 1 çalışma, 6 tur, 13 araç çağrısı | 1 çağrı, 1 tur, araç yok |
| Opus 5.5 okunan | 416.056 (121 bin önbelleğe yazma + 295 bin önbellekten okuma) | **110.694** (110 bin önbelleğe yazma) |
| Opus 5.5 yazılan (düşünme dahil) | 7.618 | **3.556** (1.182 düşünme) |
| Claude Code'un yan çağrısı (Haiku 5.5) | yok | **105.311 okunan, 24 yazılan** |
| Süre | 78 sn | **41 sn** |
| Bedel karşılığı | 1,18 $ | **1,00 $** (0,95 $ Opus + 0,05 $ Haiku) |
| Programın tahmini | — | 97 bin (gerçek, yan çağrı hariç 114 bin; dahil 219 bin) |
| Sonuç | "veriyle dolmuyor", aday yok | **aynı yön**: "veriyle dolmuyor", aday yok; eksik veri ve köpek kuralı kanıtları (K0097, K0098) |

- **200 bin sınırı.** Görev metni "200 bin token okumayı geçerse durdur" diyordu. Ana model 111 bin okudu; Claude Code'un yan çağrısı ayrıca 105 bin
  okudu; toplam okunan **216 bin**, sınırı aştı. Çağrı tek parça olduğu ve 41 saniyede bittiği için arada durdurulamazdı; tahmin (97 bin) yan çağrıyı
  bilmiyordu. Başka gerçek çağrı yapılmadı.
- **Yan çağrı nedir?** Sonuç zarfının `usage` alanında görünmüyor, yalnız `modelUsage`'da: `claude-haiku-5-5`, 105.311 girdi, 24 çıktı, önbelleksiz.
  Eski çok turlu çalışmaların `modelUsage`'ında yoktu; yani istem büyük ve tek parça gelince Claude Code'un kendi bir işi (ör. oturum başlığı ya da
  bir sınıflandırma) istemin tamamını küçük modele okutuyor. Program artık bunu harcamaya sayıyor (iş günlüğü: "…bunun 105 bin token'ını Claude
  Code'un kendi yan çağrısı (claude-haiku-5-5) okudu"), tahmine önceki tek çağrıların payını ekliyor. Kapatılıp kapatılamayacağı denenmedi (yalnız
  bir gerçek çalışma izni vardı); yöneticinin konusu.
- **Neden bedel yalnız %15 düştü?** Token %73 düştü ama eski düzende okunanın çoğu önbellekten okumaydı (fiyatın onda biri); tek çağrıda istemin
  tamamı bir saatlik önbelleğe yazılıyor (Claude Code'un ayarı; girdi fiyatının 2 katı). Tek çağrılı bir adımda bu önbellek bir daha kullanılmıyor.
  Claude Code'da `DISABLE_PROMPT_CACHING` (ve modele göre `DISABLE_PROMPT_CACHING_OPUS`) değişkenleri var; kapatılırsa aynı istem normal girdi
  fiyatıyla okunur (bu çağrı için kabaca yarı bedel). Denenmedi; yöneticinin konusu. Aboneliğin kullanım ölçüsü üzerindeki etkisi de ölçülmeli.
- **Tahmin ayarı.** Bu çağrıdan karakter/token oranı ölçüldü: 195.412 karakter → 110.694 token (1,83). Tahmin oranı 2,3'ten 1,85'e indirildi (Türkçe
  metin, tablolar ve sayılar İngilizce metinden daha çok token tutuyor; Housing Atlas'ın makalelerinde 2,8 ölçülmüştü). Yeni oranla bu çağrının tahmini
  110 bin olurdu.
- Dosyalar: `gercek-calisma/baslik_degerlendirme.json` (Claude'un cevabından programın yazdığı çıktı), `baslik_degerlendirme.md`, `cevap.txt` (ham
  cevap), `calisma.json` (çalışma kaydı: komut, tahmin, harcama, ölçüm, `modelUsage`).

### Sahte claude ile uçtan uca (ekran görüntüleri için, geçici kopyada)

İki tonlu video metni (Araştırmacı dost, Belgesel anlatıcı): tahmin 655 bin, 22 çağrı; sahte claude'un okuduğu (istemlerin gerçek boyutu) 432 bin, yazdığı
(sahte) 18 bin. Tahminin okuma kısmı istemlerin gerçek boyutundan %8 fazla çıktı; yazılan kısmı sahte claude ölçemez. Metinde işletme adı bulgusu,
başlık adayında işletme adı ve sarı uyarılar, kırmızı "beklenenden fazla" (sahte claude'a 420 bin okuttu) bu kopyada görüntülendi.

### Gerçek veritabanı

CLAUDE.md kuralına göre: program kapalıyken `data/` klasörünün tamamı `work/yedek/20261111-2024/` altına kopyalandı (45.539 dosya, 1.617.475.257
bayt; kaynakla dosya sayısı ve toplam boyut aynı). Program masaüstü kısayoluyla (`30A Studio.lnk` → `pythonw -X utf8 -m studio`) açıldı: sürüm 0.20.0,
gerçek veri klasörü. Ayarlar → Claude'da token sınırları (250.000 ve 1.500.000), "Aynı anda en çok Claude oturumu" 6, tur sütunu yok (ekran 12); başlık
adımları Opus 5.5 · Yüksek. Claude çalıştırılmadı, hiçbir düğmeye basılmadı. Program penceresi kapatıldı; program kendiliğinden kapandı ("Pencere kapalı
ve çalışan iş yok; uygulama kapanıyor").

| | Önce | Sonra |
|---|---|---|
| Şema (`user_version`) | 19 | 19 |
| Tablo sayısı | 71 | 71 |
| Satır sayıları | — | 71 tablonun hepsinde aynı (ör. jobs 40, claude_runs 4, videos 0, text_runs 0, evidence_packs 8, claude_usage 3) |
| `foreign_key_check` | boş | boş |
| `quick_check` | ok | ok |
| `metadata` | — | aynı |
| `ayarlar.json` (Claude bölümü) | `claude_max_sessions: 3`, tur sınırları, `ayar_surumu` yok | aynı (dosya değişmedi; program 3'ü 6 okur) |
| `data/` içindeki dosya ve klasörler | — | aynı |

Şema değişmediği için geçiş olmadı ve uygulama kendi yedeğini almadı. Bu dal main'e alınana kadar gerçek veri main'deki 0.19.0 ile de açılır (şema aynı);
0.19.0 Ayarlar'ı kaydederse yeni sınır alanları yazılmaz, 0.20.0 onları başlangıç değeriyle okur.

### Belgeler

M15 (yeni bölüm "Tek çağrı düzeni, tahmin ve sınırlar"; yeni adım kuralı), M17 ("Tek çağrılı zincir, tahmin ve token sınırı"; denetimde işletme adı),
CALISMA_MANTIGI.md (9.13h, durum tablosu, bölüm 11), README.md (v0.20.0 bölümü), DEVIR 02 (yeni bölüm) ve 05 (durum ve geçmiş), CLAUDE.md
("Programın Claude adımları" kuralı).

## Housing Atlas'tan alınanlar

`git fetch` ile son hâline bakıldı (main `75ac646`); hiçbir dosyası değiştirilmedi.
- Araçsız ve tek turlu oturum: `--tools ""`, `--max-turns 1`, talimat `--append-system-prompt-file`, görev standart girdiden (KARARLAR "Çalıştırma
  motoru"; `atlas/article/service.py` `_session`).
- Cevaptan JSON ayıklama kuralı (`atlas/article/prompts.py` `parse_json`: çıplak, kod çiti, çevresinde metin).
- Geçersiz cevapta bir kez, sorunu ekleyerek yeni oturumla yeniden deneme (`_ask`); kesik cevabın `stop_reason: max_tokens`'tan ya da Claude Code'un
  çıktı sınırı iletisinden tanınması ve "daha kısa yaz" notu (KARARLAR "Uzun metin ve kesik cevap"; `TRUNCATED` deseni).
- Token tahmininde karakter bölü sabit ve Claude Code'un sistem metni için pay (KARARLAR: karakter ÷ 2,5, 5 bin pay); bu projede gerçek ölçümle 1,85
  ve 4.500.
- Çıktı sınırının `modelUsage.maxOutputTokens`'tan okunması ve Claude Code'un Opus/Sonnet için 128 bin göndermesi (KARARLAR, toplu istek ölçümü).
- Alınmayan: Housing Atlas'ın çevirisinde kesik cevapta bölümü ikiye bölme (burada çeviri dilimleri 6.000 kelime ve Sonnet'in çıktı sınırı 128 bin;
  kesik cevap bir kez "daha kısa yaz" ile yeniden isteniyor).

## Kullanıcının görevden sonra yapacakları

- Programı her zamanki gibi masaüstündeki simgeyle açın. Bir Claude işi başlatınca önce tahmin çıkar; "Başlat"a basınca iş başlar.
- Başka bir şey gerekmiyor. Eklenti değişmedi (0.19.0).

## Yöneticinin karar vermesi gereken konular

1. **Claude Code'un yan çağrısı** (her tek çağrıda istemi Haiku'ya bir kez daha okutuyor; okunan token ikiye katlanıyor, bedel %5 artıyor): bir sonraki
   izinli gerçek çalışmada `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` gibi bir ayarla kapanıp kapanmadığı denensin mi? Kullanıcının "200 bin"
   sınırı bu yan çağrıyı sayıyor mu?
2. **Önbellek**: tek çağrılı adımlarda istem bir saatlik önbelleğe yazılıyor (girdi fiyatının 2 katı) ama yeniden kullanılmıyor. `DISABLE_PROMPT_CACHING`
   denensin mi? Video metninde bölüm yazıcılarının ortak kısmı (talimat, plan) önbellekten yararlanabilir; bunun için istemde ortak dosyaların görev
   satırlarından önce gelmesi gerekir (bugün görev satırları önce).
3. **Kısaltma önerileri** (Adım 3 tablosu): ilk gerçek metinler görüldükten sonra.
4. **Daha ucuz model** (tarama ve puanlama Sonnet): ilk gerçek metinlerden sonra; model tablosundaki ortancalar artık kararı destekliyor.
5. **Tahminin video metni kısmı** bugün çıktı varsayımlarına dayanıyor; ilk gerçek metinden sonra ortancalar kendiliğinden devreye girer.
   Varsayımların (Ayarlar → Claude → çıktı varsayımı) gözden geçirilmesi.
6. **CI'daki takılma**: bir sonraki takılmada günlükte yığın görünecek; okunup kök nedeni ayrı bir görevde düzeltilmeli.
7. **"Tek satırlık konu"** önceki öneriler listesine eklensin mi (Adım 3)?

## Ekran görüntüleri (`ekran/`)

| Dosya | Ne gösteriyor |
|---|---|
| 01-tahmin-baslik-degerlendirme.jpg | Başlamadan önce tahmin ve onay (başlık değerlendirme; gerçek çalışmadan hemen önce) |
| 02-gercek-calisma-tahmin-ve-gercek.jpg | Gerçek çalışmanın ekranı: "Harcama: tahmin 97 bin · gerçek 114 bin token (1 çağrı)" |
| 03-ayarlar-claude-model-tablosu-ve-sinirlar.jpg | Ayarlar → Claude: model tablosunda son çalışmaların ortancası ve çıktı varsayımı, token sınırları |
| 04-ayarlar-adim-basina-harcama.jpg | Ayarlar → Claude kullanımı: adım başına harcama tablosu (tek çağrı ve eski düzen) |
| 05-tahmin-video-metni-iki-ton.jpg | "Metni yaz" öncesi tahmin: plan ve iki ton ayrı satırda, toplam |
| 06-is-karti-tahmin-ve-gercek.jpg | İş kartında tahmin ve gerçek (sahte claude, iki ton) |
| 07-metinde-isletme-adi-bulgusu.jpg | Video metninde cümleye bağlı kırmızı "işletme adı: Modica Market" |
| 08-baslik-adayinda-isletme-adi-ve-baslik-kapak-uyarilari.jpg | Başlık adayında kırmızı işletme adı ve sarı başlık ve kapak uyarıları |
| 09-ayarlar-isletme-adlari-ekle-haric-tut.jpg | Ayarlar → Uyarı ifadeleri → İşletme adları: ekle / hariç tut (veriden kurulan 256 ad) |
| 10-beklenenden-fazla-kirmizi-uyari-sahte-claude.jpg | Kırmızı "Beklenenden fazla harcandı" (sahte claude; iş kartı ve çalışma ekranı) |
| 11-kullanim-kutusu-son-is.png | Sol menüdeki Claude kullanımı kutusunda son işin harcaması (sahte claude) |
| 12-gercek-veri-ayarlar-claude-token-sinirlari.jpg | Gerçek veriyle açılışta Ayarlar → Claude: token sınırları ve oturum ayarı 6 |

01–04 gerçek verinin geçici kopyasında, gerçek Claude'la yapılan tek çalışmadan; 05–11 aynı kopyanın bir başka kopyasında sahte claude ile; 12 gerçek
veriyle.

Gerçek Claude yalnız bir kez çalıştı (yukarıdaki değerlendirme). Gerçek sitelere istek yapılmadı; zamanlanmış görev oluşturulmadı; Housing Atlas'ta ve
talimat dosyalarında hiçbir şey değişmedi (yalnız Adım 1'deki yöneticinin talimat değişiklikleri commit edildi).
