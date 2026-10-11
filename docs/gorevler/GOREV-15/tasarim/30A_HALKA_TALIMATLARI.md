# 30A — Video metni zincirinin halka talimatları (yönetici taslağı)

*11 Ekim 2026. GÖREV-15'te `studio/destinations/thirty_a_claude/` altına bu adlarla girer. Mucahit sonra Ayarlar → Talimatlar'dan düzenleyebilir. Housing Atlas'ın talimatları gibi niyet anlatan kısa metinlerdir: örnek cümle ve kural listesi yok. Bir kural yalnız örnek metinlerde aynı sorun tekrar ederse eklenir.*

## Talimatların birleşimi

Her halkada Claude'a verilen talimat, aşağıdaki parçaların bu sırayla birleşiminden oluşur:

| Halka | Dosya | ortak.md | ses_ortak.md + ton | Şema |
|---|---|---|---|---|
| Planlayıcı | `metin_plan.md` | var | yok (plan tondan bağımsız) | `plan` |
| Plan eleştirmeni | `metin_plan_elestiri.md` | var | yok | `plan_elestirisi` |
| Bölüm yazıcısı | `metin_bolum.md` | var | var | `bolum` |
| Birleştirici | `metin_birlestirme.md` | var | var | `birlestirme` |
| Giriş ve kapanış | `metin_giris_kapanis.md` | var | var | `giris_kapanis` |
| Son okuyucu | `metin_son_okuma.md` | var | var | `son_okuma` |
| Çevirmen | `metin_ceviri.md` | var | var | `ceviri` |

## Çalışma klasöründeki dosyalar

Talimatlarda bu adlar geçer; program her halkada yalnız o halkanın ihtiyaç duyduğunu koyar.

- `baslik_analizi.md`: seçilen aday; başlık, izleyicinin sorusu, kanca, neden önerildiği, içerik planı, eksik veri.
- `paket_ozeti.md` ve `sayilar.csv`: video paketinin yazar özeti ve sayı listesi (GÖREV-14'teki içerik planından paket).
- `kanal_plani.md`: kanalın planı.
- `plan.json` ve `plan_elestirisi.json`: önceki halkaların çıktıları.
- `bolum.md`: bölüm yazıcısının kendi bölümü. İçinde planın o bölüme ait kısmı, o bölümün kanıt satırları ve önceki ile sonraki bölümün birer cümlelik özeti bulunur.
- `bolumler.md`: bölümler sırasıyla, kanıt işaretleriyle.
- `metin.md`: o ana kadar birleşmiş metin. Son okuyucuya cümleleri numaralı olarak verilir.
- `yayinlanan_videolar.md`: kanalın yayınlanmış videoları (başlık, konu, adres). İlk videoda boştur.

## Başlangıç modeli ve eforu

Bunlar Ayarlar'daki varsayılanlardır; ilk gerçek denemede ölçülüp değiştirilecek.

| Halka | Model | Efor |
|---|---|---|
| Planlayıcı | Opus | yüksek |
| Plan eleştirmeni | Opus | orta |
| Bölüm yazıcısı | Opus | yüksek |
| Birleştirici | Opus | orta |
| Giriş ve kapanış | Opus | yüksek |
| Son okuyucu | Opus | orta |
| Çevirmen | Sonnet | orta |

---

## `metin_plan.md`

```markdown
# Video metninin planı

Görevin, seçilen başlık için 15–17 dakikalık videonun planını yapmak. Metni sen yazmayacaksın; bölümleri ayrı yazıcılar aynı anda yazacak ve her biri yalnız kendi bölümünü ve senin planını görecek. Bu yüzden plan, her yazıcının videonun bütününü bilmeden doğru bölümü yazabileceği kadar açık olsun.

Seçilen başlık ve onun için yapılmış analiz baslik_analizi.md dosyasında: izleyicinin sorusu, kanca, neden önerildiği, ilk içerik planı ve eksik veri. Videonun kanıtları paket_ozeti.md dosyasında, sayıları sayilar.csv dosyasında. Paketi kendin baştan sona oku; kimse senin için özetlemedi. Kanalın planı kanal_plani.md dosyasında.

Başlık analizindeki içerik planı bir başlangıçtır. Kanıtı okuyunca daha iyi bir sıra ya da bölümleme görürsen değiştir. İzleyici videoyu bir soruyla açtı; plan bu soruya adım adım cevap veren bir yol olsun ve her bölüm bir öncekinin bıraktığı merakı taşısın. En güçlü bilgiyi başta harcama: ikinci en güçlüsü başa, en güçlüsü sona doğru gelsin.

Her bölüm için tek fikrini, en çarpıcı anını, dayandığı kanıt kimliklerini, kelime bütçesini ve nasıl açılacağını yaz. Bölümlerin açılışları birbirine benzemesin; yan yana iki bölüm aynı biçimde açılmasın. Açıklanması gereken bir kavram varsa onu hangi bölümün bir kez açıklayacağını yaz; diğer bölümler o açıklamayı tekrarlamaz. Videonun üçte birinde ve üçte ikisinde izleyiciyi yeniden yakalayacak bir an göster. Son olarak başlığın vaadinin hangi bölümlerde karşılandığını yaz; karşılanamayan bir vaat varsa bunu açıkça söyle.

Çıktın plan.json dosyasıdır ve şemaya uyar: 5–7 bölüm. Bölümlerin kelime bütçeleri toplamı yaklaşık 2.000–2.200 olsun; giriş ve kapanış ayrıca yazılacak.
```

## `metin_plan_elestiri.md`

```markdown
# Planın eleştirisi

Görevin, bir video metninin planını metin yazılmadan önce okumak ve zayıf yerlerini bulmak. Planı sen yazmadın; onu ilk kez gören biri gibi oku. Plan plan.json dosyasında, başlık analizi baslik_analizi.md dosyasında, kanıtlar paket_ozeti.md ve sayilar.csv dosyalarında.

Kendine şunu sor: bu başlığa tıklayan biri videoyu sonuna kadar izler mi ve sorusunun cevabını alır mı? Başlığın vaadinin karşılanıp karşılanmadığına, bir bölümün kanıtın söylediğinden fazlasını vaat edip etmediğine, iki bölümün aynı şeyi anlatıp anlatmadığına, bir bölümün doldurulamayacak kadar ince olup olmadığına ve merakın bir yerde kopup kopmadığına bak. Pakette olup plana girmemiş daha güçlü bir bilgi varsa onu da söyle. Yalnız gerçekten önemli olanları yaz; küçük beğeni farklarını not etme.

Çıktın plan_elestirisi.json dosyasıdır ve şemaya uyar: notların ve planın yeniden yapılması gerekip gerekmediği. Plan iyiyse bunu söylemekten çekinme.
```

## `metin_bolum.md`

```markdown
# Bir bölümün metni

Görevin, videonun tek bir bölümünü yazmak; diğer bölümleri başka yazıcılar aynı anda yazıyor. Planın tamamı plan.json dosyasında. Senin bölümün bolum.md dosyasında: bölümün tek fikri, en çarpıcı anı, nasıl açılacağı, kelime bütçesi, açıklaman gereken kavramlar ve kanıtların. Önceki ve sonraki bölümün ne anlattığı da orada birer cümleyle var; yalnız bölümünün yerini bilmen için.

Bölümün kendi başına anlaşılsın. İzleyici geri saramaz: başka bir bölüme gönderme yapma; bir şeyi hatırlatman gerekiyorsa kısaca yeniden söyle. Bölümün sonunda anlattığını özetleme; bölüm son bilgisiyle bitsin. Başka bir bölümün açıklayacağı bir kavramı açıklama. Kelime bütçesine yakın kal.

Bilgi taşıyan her cümlenin sonuna dayandığı kanıtın kimliğini köşeli parantez içinde yaz, örneğin [K0123]. Bu işaretler seslendirmede görünmeyecek; program rakamları ve iddiaları onlarla kontrol edecek. Kanıtta olmayan bir bilgiyi yazma.

Çıktın bolum.json dosyasıdır ve şemaya uyar.
```

## `metin_birlestirme.md`

```markdown
# Bölümlerin birleştirilmesi

Bölümler ayrı yazıcılar tarafından aynı anda yazıldı; şimdi tek bir video gibi akmaları gerekiyor. Görevin, bölümlerin arasına geçişleri ve planın gösterdiği yerlere yeniden kancaları yazmak. Bölümler bolumler.md dosyasında sırasıyla, plan plan.json dosyasında.

Bir geçiş, bir sonraki bölümün en çarpıcı anına doğru merak uyandırır; her yere uyan bir kalıp cümle değildir. Yeniden kanca, videonun ortasında dikkati dağılmaya başlayan izleyiciye neden izlemeye devam etmesi gerektiğini somut bir bilgiyle hatırlatır. Geçişleri kısa tut; bölümlerin işini onlar yapmaz.

Bölümlerin metnine dokunma. İki bölümün birleştiği yerde bir cümle kendini tekrarlıyor ya da çelişiyorsa bunu not et. Geçişlerde bir bilgi kullanırsan kanıt kimliğini yaz.

Çıktın birlestirme.json dosyasıdır ve şemaya uyar.
```

## `metin_giris_kapanis.md`

```markdown
# Giriş ve kapanış

Videonun gövdesi bitti. Girişi ve kapanışı en son sen yazıyorsun, çünkü neyin vaat edileceğini ancak bitmiş metni okuyan biri bilir. Bitmiş metin metin.md dosyasında, başlık ve analizi baslik_analizi.md dosyasında, kanalın yayınlanmış videoları yayinlanan_videolar.md dosyasında.

Giriş, başlığa tıklayan kişiye ilk 30 saniyede doğru yere geldiğini gösterir: başlığın vaadini somut bir bilgiyle doğrular ve videonun cevaplayacağı soruyu kurar. İçindekileri saymaz, videoyu tanıtmaz, doğrudan konuya girer. Yaklaşık 80–120 kelime.

Kapanış, videonun izleyiciye bıraktığını kısaca toplar ve kararı ona bırakır. Kanala abone olmayı doğal bir cümleyle önerir ve yayınlanmış videolardan bu izleyicinin işine yarayacak birini önerir; yayınlanmış video yoksa öneri yapmaz. Yaklaşık 80–120 kelime.

Bilgi taşıyan cümlelere kanıt kimliğini yaz. Çıktın giris_kapanis.json dosyasıdır ve şemaya uyar.
```

## `metin_son_okuma.md`

```markdown
# Son okuma

Metin bitti ve ilk kez baştan sona tek parça olarak okunuyor. Görevin, onu bir dinleyicinin kulağıyla okumak ve yalnız küçük düzeltmeler yapmak. Metin metin.md dosyasında numaralı cümleler hâlinde, kanıtlar paket_ozeti.md dosyasında.

Ayrı yazıcılardan gelen metinlerde olan şeyleri ara: aynı bilginin ya da ifadenin tekrar etmesi, bölümler arasında çelişki, aynı biçimde açılan ya da biten cümleler, yapay zekâ yazısını ele veren yerler, kulağa doğal gelmeyen cümleler, kanıtın söylediğinden fazlasını söyleyen ya da pakette olmayan bir ayrıntı ekleyen cümleler. Anlatıcının seçilen tonunu bir kusur sayıp düzeltme. Bölümleri yeniden yazma, sırayı değiştirme; yalnız gereken cümleyi düzelt ve neden düzelttiğini kısaca yaz. Kanıt kimliklerini koru.

Çıktın son_okuma.json dosyasıdır ve şemaya uyar: düzeltilen her cümlenin numarası, yeni hali ve kısa bir gerekçe. Düzeltecek bir şey yoksa liste boş kalır.
```

## `metin_ceviri.md`

```markdown
# Türkçe çeviri

Sana bir YouTube videosunun İngilizce metni numaralı cümleler hâlinde veriliyor. Metni İngilizce bilmeyen kanal sahibi okuyacak ve farklı anlatıcı tonlarını bu çeviriden karşılaştıracak. Her cümleyi kendi numarasıyla Türkçeye çevir. Çeviri anlamı tam taşısın, anlatıcının tonunu da taşısın ve Türkçede doğal dursun; çeviri kokan kalıplardan ve Türkçede kullanılmayan tabirlerden kaçın. Cümle sayısını değiştirme: her numaraya tek bir Türkçe cümle karşılık gelsin. Rakamları, paraları ve özel adları olduğu gibi koru.

Bölgeye ya da Amerika'ya özgü ve Türkçede tam karşılığı olmayan terimleri (örneğin customary use, LSV, beach walkover) Türkçe metinde İngilizce bırak ve terim listesine ekle; her terime bir iki cümlelik sade bir Türkçe açıklama yaz. Bir İngilizce cümle belirsiz, iki anlama gelebilen ya da kendi içinde yanlış görünüyorsa, onu çevirirken numarasıyla birlikte kısa bir Türkçe uyarı yaz. Çeviri sırasında anlaşılmayan bir cümle, izleyicinin de anlamayacağı bir cümledir.

Çıktın ceviri.json dosyasıdır ve şemaya uyar.
```

---

## Program denetimi için kurallar (Claude'a verilmez; GÖREV-15'te kodlanır)

### Kırmızı: bilgiyi yanlış söyler

Bu kurallar kanıt bloklarının kullanım notlarından çıkarıldı (`studio/evidence/blocks.py` `USAGE`). Program metinde bunları arar ve denetim raporunda kırmızıyla gösterir.

| Blok | Kullanım notu | Aranan |
|---|---|---|
| Mesafe (M13) | "Yürüme mesafesi" ya da yol ve süre iddiası kullanılmaz | walking distance, walkable, a short walk, minute walk, minutes' walk, minutes away, minute drive, minutes to drive |
| Fiyat (M11) | "Bir hafta $X tutar" denmez | a week costs, a week in … costs, costs about $… a week, per week it costs |
| Envanter (M10) | "30A'da N ev var" ya da "tam liste" denmez | full inventory, full list, complete list, every rental, all the rentals, there are … homes in |
| İklim (M8) | "30A'nın iklimi" denmez | 30A's climate, the climate in 30A, climate of 30A |
| Restoran (M12) | "En iyi", "en popüler", "en ucuz" sıralamaları kullanılmaz | best restaurant, the best place to eat, most popular, cheapest restaurant |
| Trafik (M9) | Sıkışıklık ya da yolculuk süresi iddiası yapılmaz | traffic jam, gridlock, bumper-to-bumper, takes … minutes to get |
| Kaynak durumu (M9) | Durumu "doğrulanamadı" olan satır kullanılmaz | Kanıt işareti durumu `dogrulanamadi` olan bir satırı gösteriyorsa |

### Sarı: dikkat ister

- **Küçük örnek:** Kanıt işareti küçük örnek (`*`) hücresini gösteriyor ve cümlede iki mahalle karşılaştırılıyor.
- **Kaynak sorusu:** "no public beach access" geçiyor ve aynı ya da önceki cümlede kaynak söylenmiyor. Bu, son okuyucuya ve Kontrol adımına not olarak düşer.
- **Ses uyarıları:** `30A_SES_VE_TONLAR.md`'deki uyarı ifadeleri (broşür ve YouTube kalıpları, geri göndermeler, "I", "the ocean"). Liste Ayarlar'dan düzenlenir.

### Rakam ve yuvarlama

- **Kanıt işareti zorunlu:** Rakam taşıyan her cümlenin bir kanıt işareti olmalı. Rakam, işaretin gösterdiği satırların değerlerinden biriyle tutmalı: ana değer, çeyrekler, örneklem, pay, aralık ya da dönüşüm.
- **Tutma toleransı:**
  - Para ve sayılar: metindeki sayı, kanıt değerinin konuşma yuvarlamasıyla tutmalı. Yuvarlama; en yakın 10, 50, 100, 500 ya da 1.000'e, ya da "about" varken ±%3 içine olabilir. Örnek: $7,223 → "about $7,200" ya da "about $7,000" tutar; "$7,500" tutmaz.
  - Yüzdeler: ±0,5 puan. Yarım ve üçte bir gibi kesir ifadeleri kabul edilir.
  - Sıcaklıklar: ±1 °F.
  - Sayımlar (gün, ilan, kasırga): "about" yoksa tam tutmalı.
- **Kelimeyle yazılan sayılar:** "seven thousand", "a third" gibi ifadeler de denetlenir.
- **Kanıtsız rakam:** Tutmayan ya da işaretsiz rakam kırmızıdır.

### Uzunluk ve plan

- **Uzunluk:**
  - Toplam kelime: hedef 2.200–2.500; 2.000'in altı ve 2.800'ün üstü sarı.
  - Bölümler: bütçesinden %25'ten fazla sapan bölüm sarı.
- **Plan denetimi:**
  - plan.json'daki bütün kanıt kimlikleri pakette olmalı.
  - Her kavram bir bölüme yerleştirilmiş olmalı.
  - Yan yana iki bölümün açılış biçimi aynı olmamalı. Bunun için şemada `acilis_bicimi` alanı bulunur: rakam, sahne, soru, geçmiş, karşılaştırma ya da diğer.
  - Bölüm bütçelerinin toplamı 1.900–2.300 arasında olmalı (planlayıcıya 2.000–2.200 denir).

  Pakette olmayan bir kanıt kimliği varsa plan bir kez planlayıcıya döner; yine varsa çalışma hata verir. Öbür bulgular uyarı olarak kaydedilir ve zincir sürer.
