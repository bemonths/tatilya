# 30A — Video metni yazım zinciri (tasarım)

*10 Ekim 2026. Mucahit tasarımı onayladı ("bu tasarım doğru olan, temiz bir şekilde 30A'ya ayarlayacağız"). Kaynak: The Housing Atlas'ın makale sistemi belgesi (aynı gün) ve 30A'ya uyarlamaları. Bu bir tasarımdır; gerçek bir videoyla denendikçe değişecek.*

## Kararlar

- **Dil:** Metin doğrudan İngilizce yazılır. Kanca ve cümle ritmi son dilde kurulur. Mucahit'e cümle cümle eşleşen Türkçe çevirisi verilir.
- **Başlık:** Başta kalır, çünkü başlık seçimi aynı zamanda konu seçimidir. Plan çıktıktan sonra bir "vaat kontrolü" yapılır.
- **Analistler:** İlk sürümde analist halkası yok. Bir videonun paketi tek oturuma sığıyor ve içerik planı başlık adımında kanıtlarıyla çıkıyor. Gerçek denemede eksik çıkarsa eklenir.
- **Eleştirmenler:** Üç ayrı oturum yerine tek bir plan eleştirmeni. Rakam kontrolünü program yapar.
- **Düzenleme ekranı:** Housing Atlas'ta gerçek kullanımla oturduktan sonra aynı tasarım 30A'ya taşınır; iki kez sıfırdan yapılmaz.
- **Uzunluk:** 15–17 dakika, yaklaşık 2.200–2.500 kelime (dakikada ~150 kelime), 5–7 bölüm.
- **Ses ve tonlar (11 Ekim):** Ses, her tonda aynı kalan kısa bir ortak ses ile tek paragraflık ton dosyalarından oluşur. Plan bir kez yapılır; seçilen her ton için 4–7. ve 9. halkalar ayrı çalışır ve sürümler karşılaştırma ekranında yan yana durur. Örnek cümle ve kelime listesi yazara verilmez; program yazıldıktan sonra tarar. Ayrıntı: `30A_SES_VE_TONLAR.md`.

## İlkeler

1. **Yapay zekâ düşünür, program sayar ve denetler.** Rakamlar, kanıt eşlemesi, kelime sayısı, yasak ifadeler ve biçim programın işidir. Neyin ilginç olduğuna ve nasıl anlatılacağına Claude karar verir.
2. **Her oturuma tek iş, tek seferde okunacak kadar malzeme.**
3. **Yazan kendini denetlemez.** Denetimi ayrı oturumlar ve program yapar.
4. **Hiçbir şey kaybolmaz.**
   - Her halkanın çıktısı sürümlü saklanır.
   - Zincir durup kaldığı yerden sürer.
   - Yarım kalan halka sonucunu yazmaz.
   - Kullanım eşiğinde zincir durur, sınır sıfırlanınca kendiliğinden sürer.
5. **Talimatlar niyet anlatan kısa metinlerdir,** kural listesi değildir. Az başlar; örnek metinlerde aynı sorun tekrar ederse bir cümle eklenir ve sebebi not edilir. Bir metin içinde ses sabittir, ritim değişkendir.
6. **Kanıt kimlikleri metinle birlikte yürür.** Yazıcılar bilgi taşıyan cümlenin sonuna kanıt kimliğini işaretler (ör. `[K0123]`). Program bu işaretlerle denetler; temiz metinde işaretler görünmez.

## Halkalar

| # | Halka | Kim | Girdi | Çıktı |
|---|---|---|---|---|
| 0 | Başlık ve analiz | Claude + Mucahit seçer | veri özetleri, kanal planı, araştırma | video kaydı (başlık, soru, kanca, içerik planı, eksik veri) |
| 1 | Video paketi + tazelik 1 | Program | video kaydı, veri | içerik planından paket, yazar özeti, sayı listesi; paket eskiyse yeniden üretim |
| 2 | Planlayıcı | Claude (güçlü model) | paketin tamamı (ilk elden), başlık analizi, kanal planı, ses kartı | `plan.json` |
| 3 | Plan eleştirmeni | Claude | plan, paket | notlar; zayıf plan bir kez planlayıcıya döner |
| 4 | Bölüm yazıcıları | Claude, aynı anda | ses kartı, plan, kendi bölümünün kanıtları, komşu bölümlerin tek cümlelik özeti | bölüm metinleri (İngilizce, kanıt işaretli) |
| 5 | Birleştirici | Claude | bütün bölümler, plan | geçiş cümleleri, yeniden kancalar |
| 6 | Giriş ve kapanış | Claude | bitmiş metin, başlık, yayınlanmış videolar listesi | giriş (vaadi ilk 30 saniyede doğrular) ve kapanış (kısa özet, abone çağrısı, önceki bir video önerisi) |
| 7 | Son okuyucu | Claude | bütün metin | yalnız küçük düzeltmeler (tekrar, çelişki, yapay zekâ izleri) ve farkları |
| 8 | Program denetimi | Program | metin, paket, sayı listesi, kullanım notları | denetim raporu |
| 9 | Çevirmen | Claude | bitmiş İngilizce metin | cümle cümle eşleşen Türkçe metin, anlaşılmayan cümle işaretleri, terim listesi |
| 10 | Düzenleme ekranı | Mucahit | TR ve EN | Housing Atlas'tan taşınacak |

4–7. ve 9. halkalar seçilen her ton için ayrı çalışır; 0–3. halkalar bir kez çalışır. Ton seçilince 9'dan sonra karşılaştırma ekranı gelir, Mucahit bir tonla devam eder.

### 2 · Planlayıcının planı

Plan şunları içerir:
- **Bölümler:** sıra, her bölümün tek fikri, en çarpıcı anı, dayandığı kanıtlar, kelime bütçesi, giriş biçimi ve ritim türü. Giriş biçimi örnekleri: bir sayıyla, bir sahneyle, izleyicinin sorusuyla ya da yerin geçmişiyle açılmak.
- **Kavramların yeri:** her açıklama yalnız bir bölümde ve bir kez yapılır. Örnek kavramlar:
  - ilçe listesinde halka açık erişim olmaması,
  - ıslak kum ve kuru kum,
  - "sorduğumuz evlerin ortancası",
  - kuş uçuşu mesafe,
  - kiralama fiyatlarının tam envanter olmaması.
- **Yeniden kancalar:** videonun üçte birinde ve üçte ikisinde.
- **Vaat kontrolü:** başlığın vaadi hangi bölümlerde karşılanıyor? Karşılanmayan bir vaat varsa uyarı yazılır.

Program planı şu açılardan denetler:
- bütün kanıt kimlikleri pakette var mı,
- kelime bütçelerinin toplamı aralıkta mı,
- her kavram bir kez mi yerleştirilmiş,
- yan yana iki bölüm aynı ritimde mi.

### 8 · Program denetimi

- **Rakam:** sayı taşıyan her cümlenin kanıt işareti var mı ve sayı paketteki değerle tutuyor mu? Yuvarlama kuralı ayrıca yazılacak; ör. "about $7,200" ile 7,223 tutar sayılır.
- **Yasak ifadeler:** kullanım notlarından çıkarılan liste. Örnekler: "walking distance", "a week costs", "full inventory", "no public beach access" (kaynağı söylenmeden).
- **Uzunluk:** kelime sayısı ve bölüm bütçeleri.
- **Temiz metin:** kanıt işaretleri çıkarılmış sürüm.

## Tazelik

- **Yazımdan önce:** video paketi verinin son çekiminden eskiyse yeniden üretilir.
- **Yayından önce:** oynak satırlar (plaj hukuku) ve aylık fiyatlar kontrol edilir. Değişen bilgi hangi bölümdeyse yalnız o bölüm yeniden yazılır.

## Açık konular (kodlamadan önce)

- ~~**Ses kartı**~~ → 11 Ekim'de karara bağlandı: ortak ses + üç ton (`30A_SES_VE_TONLAR.md`).
- ~~**Ritim türleri listesi**~~ → planda `acilis_bicimi` alanı; yazara liste verilmez (`30A_HALKA_TALIMATLARI.md`).
- ~~**Her halkanın talimat metni**~~ → 11 Ekim'de yazıldı (`30A_HALKA_TALIMATLARI.md`).
- ~~**Halka başına model ve efor**~~ → başlangıç tablosu `30A_HALKA_TALIMATLARI.md`'de; ilk denemede ölçülür.
- ~~**Yasak ifade listesi**~~ → kullanım notlarından çıkarıldı (`30A_HALKA_TALIMATLARI.md`, program denetimi).
- ~~**Sayı yuvarlama ve tolerans kuralı**~~ → `30A_HALKA_TALIMATLARI.md`, program denetimi.

## Sıra

1. GÖREV-14 biter (masaüstü, iş akışı, eklenti, içerik planından video paketi).
2. Yönetici ses kartı taslağını ve halka talimatlarını yazar; ses kartını Mucahit onaylar. (Ses ve tonlar ve halka talimatları 11 Ekim'de yazıldı.)
3. GÖREV-15: zincir kodlanır (halkalar, plan denetimleri, program denetimi, çevirmen, sürümler, sürdürme, kullanım eşiği, ton seçimi ve karşılaştırma ekranı).
4. Seçilen ilk başlıkla gerçek deneme; yönetici çıktıyı denetler, talimatlar düzeltilir.
5. Düzenleme ekranı, Housing Atlas'taki sürüm oturunca taşınır.
