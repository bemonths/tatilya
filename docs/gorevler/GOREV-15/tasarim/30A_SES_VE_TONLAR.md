# 30A — Anlatıcının sesi ve tonlar (tasarım)

*11 Ekim 2026. Mucahit ses kartı taslağının üç seçimini onayladı (anlatıcı araştırmasını yapmış bir dost; izleyiciye "you", kanalın araştırmasına "we", hiç "I" yok; sakin, sıcak, açık sözlü). İki şey ekledi:*

- *Birkaç farklı anlatıcı tonu olsun. Ton seçilebilsin ve metin seçilen tonla yazılsın; böylece tonlar karşılaştırılabilsin.*
- *Çok fazla kural ve örnek cümle yapay zekâyı kalıba sokar. Örnek metinler çıktıkça durum zaten anlaşılacak.*

*Bu belge `30A_SES_KARTI_TASLAK.md`'nin yerini alır.*

## Kararlar

- **Sesin iki parçası:** Ses iki parçaya ayrılır.
  - Her tonda aynı kalan kısa bir ortak ses: `ses_ortak.md`.
  - Her biri tek paragraf olan ton dosyaları: `tonlar/<ad>.md`.
- **Örnek ve liste yok:** Claude'a giden ses metinlerinde örnek cümle ve kelime listesi bulunmaz. Yasak ve uyarı ifadeleri yazara verilmez. Program metni yazıldıktan sonra tarar ve bulduklarını denetim raporunda gösterir.
- **İlk beş ton:** İlk üçünü yönetici önerdi; son ikisi Mucahit'in eki (11 Ekim 00:40).
  - Araştırmacı dost (varsayılan),
  - Belgesel anlatıcı,
  - Pratik planlayıcı,
  - Vlogger,
  - Hikâye anlatıcısı.

  Mucahit tonları Ayarlar'dan ekler, düzenler ve kaldırır. Kaldırılan ton dosyası silinmez, arşive gider.
- **Aynı plan, farklı ses:** Plan bir kez yapılır. Seçilen her ton için aynı planla ayrı bir metin yazılır. Böylece metinler arasındaki fark yalnızca sesten gelir ve karşılaştırma adil olur.
- **Talimatlar az başlar:** Örnek metinlerde aynı sorun tekrar ederse ilgili dosyaya bir cümle eklenir; eklenen cümle ve sebebi bu notlara yazılır. Bir kez görülen sorun için kural eklenmez.

## Ortak ses — `ses_ortak.md`

*Claude'a aynen verilecek metin:*

> # Anlatıcının sesi — her tonda aynı
>
> Bu metni 30A'ya gitmeyi düşünen, İngilizce konuşan, tatilinin parasını ve zamanını doğru yere harcamak isteyen biri dinleyecek. Video yüzsüz ve metni yapay zekâ sesi okuyacak. Bu yüzden okunacak bir yazı değil, konuşan bir insanın kulağa doğal gelen sözlerini yaz.
>
> Kanalın arkasında oraya gidip gelmiş tek bir kişi yok. Bu yüzden anlatıcı kendinden "I" diye söz etmez; kanalın araştırmasından "we" diye söz eder. Yalnızca kanıt paketinde olanı bilgi olarak söyler. Yorum yaptığında bunun bir yorum olduğu duyulur. Rakamları insanın konuşurken söyleyeceği gibi yuvarlar. Bir bilginin nereden geldiğini ilk geçtiği yerde doğal bir biçimde söyler. Paketteki kullanım notları bir bilginin nasıl söylenebileceğini anlatır; anlatıcı onlara uyar.
>
> Amaç bir yeri güzel göstermek değil, anlaşılır kılmaktır. İlgi sıfatlardan değil somut bilgiden doğar. İyi yanlar da can sıkıcı yanlar da aynı dürüstlükle söylenir ve karar izleyiciye bırakılır.
>
> Aşağıda bu metin için seçilen ton var. Ton anlatıcının kişiliğini belirler; yukarıdakiler her tonda geçerlidir.

## Tonlar

*Her biri Claude'a aynen verilecek metindir.*

### Araştırmacı dost — `tonlar/arastirmaci_dost.md` (varsayılan)

> # Ton: Araştırmacı dost
>
> Anlatıcı, 30A'yı iyi tanıyan ve izleyici için araştırmasını önceden yapmış bir dost. İzleyiciyle karşısında oturuyormuş gibi, doğrudan "you" diye konuşur. Sakin, sıcak ve açık sözlüdür. Bir bilgi gerçekten şaşırtıcıysa şaşırır, değilse onu büyütmez. Yeri geldiğinde hafif bir espri yapar ama kimseyle alay etmez. Ne yapılması gerektiğini söylemek yerine, izleyicinin durumuna göre neyin önemli olduğunu gösterir. Kasırga ya da ceza gibi konuları korkutmadan, bir arkadaşın uyarısı gibi anlatır.

### Belgesel anlatıcı — `tonlar/belgesel.md`

> # Ton: Belgesel anlatıcı
>
> Anlatıcı, iyi bir gezi belgeselinin sesi. İzleyiciye doğrudan seslenmekten çok onu yerin içine götürür: kasabanın nasıl kurulduğunu, orada bir günün nasıl geçtiğini, mevsimle neyin değiştiğini anlatır. Temposu daha ağır, cümleleri daha akıcıdır ama süslü değildir. Sahneyi pakette olan bilgiyle kurar; pakette olmayan bir görüntü, ses ya da ayrıntı uydurmaz. Rakamları hikâyenin içinde ve abartmadan verir. Ciddidir ama soğuk değildir.

### Pratik planlayıcı — `tonlar/pratik_planlayici.md`

> # Ton: Pratik planlayıcı
>
> Anlatıcı, tatilini hesap tablosuyla planlayan ve lafı dolandırmayan bir arkadaş. Her konuya izleyicinin vereceği karardan girer. Rakamları, seçenekleri ve her seçeneğin bedelini öne koyar, gerisini kısa tutar. Seçenekleri izleyicinin durumuna göre ayırır. Cümleleri net ve tempolu ama kesik değildir. Manzara anlatmaya pek vakit ayırmaz ve kuru bir mizahı vardır.

### Vlogger — `tonlar/vlogger.md`

> # Ton: Vlogger
>
> Anlatıcı, kameraya konuşan bir YouTuber'ın rahat ve canlı sesiyle, izleyiciyle sohbet eder gibi gündelik bir dille konuşur. Kanalın arkasındaki küçük ekip gibi "we" der; araştırırken neye şaşırdıklarını ve neyin işlerine yaradığını içtenlikle paylaşır. Enerjisi yüksektir ama bağırmaz; temposu hızlı, geçişleri doğaldır. Oraya gidip kaldığını, bir şey yediğini ya da bir yerde yürüdüğünü söylemez, çünkü kanal bir gezi günlüğü değil, bir araştırma kanalıdır; tepkilerini elindeki bilgiye verir.

### Hikâye anlatıcısı — `tonlar/hikaye_anlaticisi.md`

> # Ton: Hikâye anlatıcısı
>
> Anlatıcı, izleyiciyi sonuna kadar ekranda tutan anlatı kanallarının sesi. Her bölümü bir soruyla ya da bir merak düğümüyle açar; cevabı hemen vermez, bilgiyi doğru anda ortaya koyar. Gerilimi abartıdan değil, bilginin sırasından kurar; şaşırtıcı bir gerçek, gerçekten şaşırtıcı olduğu için etkiler. İzleyiciye "you" diye seslenir. Merakı bir sonraki bölüme taşır ama cevabı vaat ettiği yerde verir ve boşta bir merak bırakmaz.

## Programda nasıl çalışır

1. **Ton seçimi:** Video metni adımında "Metni yaz" düğmesinin yanında tonlar onay kutularıyla listelenir. Varsayılan ton işaretli gelir. Bir ya da birkaç ton seçilebilir.
2. **Plan:** Planlayıcı ve plan eleştirmeni bir kez çalışır. Plan tondan bağımsızdır ve planlayıcıya ton verilmez.
3. **Her ton için ayrı metin:** Seçilen her ton için zincirin geri kalanı ayrı çalışır: bölüm yazıcıları, birleştirici, giriş ve kapanış, son okuyucu, program denetimi ve çevirmen. Her sürüm tonun adıyla saklanır.
   - Tonlar kullanımı korumak için sırayla çalışır.
   - Bir tonun bölüm yazıcıları kendi içinde aynı anda çalışır.
4. **Tonun gittiği yerler:** Ton metni, o tonun bütün halkalarına ortak sesle birlikte verilir. Çevirmene de verilir, çünkü çeviri tonu da Türkçeye taşımalıdır: Mucahit karşılaştırmayı Türkçeden yapacak.
5. **Karşılaştırma ekranı:**
   - Tonlar yan yana sütunlarda, bölüm bölüm gösterilir. Türkçe önde durur, İngilizce bir tıkla açılır.
   - Her sürüm için kelime sayısı, tahmini süre, denetim uyarılarının sayısı ve harcanan kullanım yazar.
   - "Bu tonla devam et" düğmesi seçilen sürümü Kontrol adımına götürür. Seçilmeyen sürümler silinmez.
6. **Sonradan ton ekleme:** "Bu tonla da yaz" düğmesi aynı planı kullanarak tek bir ton daha yazdırır.
7. **Talimat kopyası:** Her çalışma kullandığı ortak ses ve ton metninin kopyasını saklar. Böylece talimat değiştikçe hangi metnin hangi talimat sürümünden çıktığı bilinir.

## Program denetimine taşınanlar (yazara verilmez)

- **Yasak ifadeler (kırmızı):** Bilgiyi yanlış söyleyen ifadelerdir ve kullanım notlarından çıkarılır. Örnekler:
  - "walking distance",
  - "a week costs",
  - "full inventory",
  - kaynağı söylenmeden "no public beach access".
- **Uyarı ifadeleri (sarı):** Sesi bozan ifadelerdir. Liste Ayarlar'dan düzenlenir.
  - Broşür ve YouTube kalıpları: amazing, stunning, breathtaking, paradise, hidden gem, nestled, you won't believe, let's dive in, in this video we'll, without further ado, buckle up.
  - Geri göndermeler: as we mentioned, as I said, remember when.
  - Anlatıcının kendinden söz etmesi: I, I'm, my.
  - Deniz için "the ocean".
- **Diğer denetimler:** Rakam, kanıt işareti ve uzunluk denetimleri yazım zinciri tasarımındaki gibidir.

## Ses kartından halka talimatlarına taşınan yapı bilgileri

- **Bölüm yazıcısı:**
  - Dinleyici geri saramaz. Bu yüzden başka bir bölüme gönderme yapılmaz; bir şeyin hatırlatılması gerekiyorsa kısaca yeniden söylenir.
  - Bölüm sonunda özet tekrarlanmaz.
- **Kavram açıklamaları:** Planın gösterdiği yerde bir kez yapılır. Bu bilgi planlayıcı ve yazıcı talimatlarında yer alır.

## Bilinen sınırlar

- **Çeviriden karşılaştırma:** Mucahit İngilizce bilmediği için tonları çeviriden karşılaştıracak. Tonun bir kısmı çeviride kaybolabilir. Seslendirme adımı gelince İngilizce metni dinleyerek de karşılaştırma yapılabilir.
- **Belgeselde uydurma riski:** Belgesel tonunda sahne kurma isteği, pakette olmayan ayrıntı uydurma riskini artırır (ışık, ses, koku gibi). Son okuyucu ve Kontrol adımı bunu özellikle arar; ilk örneklerde yönetici de bakar.
- **Vlogger ve "I":** Gerçek bir vlogger "I stayed here, I ate there" der. Bizim kanalımızda oraya gidip gelmiş biri olmadığı için bu, izleyiciye yalan söylemek olur. Bu yüzden vlogger tonu kameraya konuşan bir YouTuber'ın enerjisini ve rahatlığını alır ama "we" der ve yalnız araştırmanın kendisine tepki verir ("when we pulled the prices…" doğrudur, çünkü fiyatları gerçekten biz çektik). Program "I" geçen cümleleri bu tonda da sarı uyarıyla gösterir.
- **Belgesel ile hikâye anlatıcısının farkı:** Belgesel sakin ve sahne odaklıdır, izleyiciyi yerin içine götürür. Hikâye anlatıcısı merak ve sıra odaklıdır, izleyiciyi bir sonraki bilgiye çeker.
- **Kullanım:** Her ek ton, yazım zincirinin büyük kısmını yeniden çalıştırır. Kullanım ilk denemede ölçülecek.
