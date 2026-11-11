GÖREV-18 — Claude adımlarında token kontrolü: tek çağrılı adımlar, harcama tahmini ve sınırlar; işletme adı ve başlık denetimleri

BAĞLAM
GÖREV-17 (dal `gorev-17-arayuz`, son commit `a49c6d0`, uygulama 0.19.0, şema 19) kabul edildi. Program klasörü: `C:\Users\1\source\Repos\30A Studio\outputs\30a-studio`.

Kullanıcı bütün projeleri için bir kural koydu: "Token kontrolü ve çalışma düzeni". Kuralın bu göreve ilişkin özü şudur:
- Adım adım çalışan bir Claude oturumu her turda önceki konuşmanın tamamını yeniden okur. Toplam harcama tur sayısıyla katlanarak büyür.
- Uzun, çok turlu iş verilmez. İş küçük çağrılara bölünür; her çağrı tek işini yapar ve kapanır.
- Dosyalar, resimler ve sayfalar Claude'a tek tek açtırılmaz, çünkü her açış bir turdur. Malzemeyi program önceden hazırlar ve toplu verir.
- Her adımın tur ve çağrı sınırı olur.
- İş başlamadan önce kaç çağrı yapılacağı ve kabaca kaç token okunacağı kullanıcıya söylenir. İş bitince gerçek harcamaya bakılır; beklenenden büyükse kullanıcıya hemen bildirilir.
- Bir iş için 1 milyon token bile fazladır.
- Ucuz iş ucuz modele verilir: tarama ve puanlama Sonnet ile, araştırma ve yazım Opus ile yapılır.
- Talimat ve veri kısa tutulur.
- Sınırlar ve boyutlar ayardır, koda gömülmez.
- Önce 2–4 örnekle denenir ve ölçülür, sonra genişletilir.

Bugünkü durum bu kurala uymuyor. Programın bütün Claude adımları araçlı ve çok turlu çalışıyor: Claude çalışma klasöründeki dosyaları `Read` ile tek tek açıyor ve çıktıyı `Write` ile yazıyor. Tur sınırı 30. Gerçek ölçümler (10 Ekim, iş günlükleri):

| Çalışma | Tur | Araç çağrısı | Okunan token | Çıktı | Bedel karşılığı |
|---|---|---|---|---|---|
| Konu ve başlık · 30A geneli | 5 | 9 | 371 bin | 65 bin | 2,55 $ |
| Konu ve başlık · Rosemary Beach | 6 | 10 | 460 bin | 53 bin | 2,36 $ |
| Konu ve başlık · Rosemary Beach | 5 | 10 | 444 bin | 54 bin | 2,42 $ |
| Başlık değerlendirme | 6 | 13 | 416 bin | 8 bin | 1,18 $ |

Bir başlık çalışmasının malzemesi yaklaşık 90 bin token; Claude bunu 5–6 kez yeniden okuduğu için toplam 450 bine çıkıyor. Video metni zinciri de aynı düzende kurulu (GÖREV-15) ve henüz gerçek Claude ile hiç çalışmadı. Bu düzenle iki tonlu bir video metni 1,5–2 milyon token tutar. Kullanıcı ilk gerçek metni yazdırmadan önce bunun düzeltilmesini istedi.

Bu görevin ikinci kısmı iki küçük program denetimidir: videolarda ve başlıklarda işletme adı geçmemesi (kullanıcının 11 Kasım kararı), ve başlık ile kapak yazısı için birkaç uyarı.

Housing Atlas Stüdyo (`C:\Users\1\source\repos\housing-atlas`) ayrı bir projedir. Ona dokunulmaz; yalnız örnek olarak okunur. Önce `git fetch` ile son hâline bak. Orada araçsız ve tek turlu Claude adımları var: makale sistemindeki çeviri, uyarlama ve anlam kontrolü (TASARIM Bölüm 21, `atlas/article/`, `atlas/ai/`). Token sorunundan sonra orada da düzeltme yapılmış olabilir; `docs/KARARLAR.md` ve son görev dosyalarına bak ve yöntemi oradan al.

Kullanıcı bu görev için kendi mesajında şu izinleri veriyor:
- main'e alma ve etiket,
- gerçek veritabanını normal kullanımla güncelleme (önce tam yedek),
- ölçüm için gerçek Claude ile **tek bir** "başlık değerlendirme" çalışması (Adım 7; geçici kopyada).

Bunun dışında gerçek Claude çalıştırılmaz. Gerçek sitelere istek yapılmaz. Bilgisayarda zamanlanmış görev oluşturulmaz.

KESİN SINIRLAR
- Housing Atlas klasöründe hiçbir dosya değiştirilmez.
- Talimat dosyalarının (`studio/destinations/thirty_a_claude/` altındaki `.md` dosyaları, tonlar dahil) içeriğine dokunulmaz. Bu görevdeki bütün değişiklik, programın malzemeyi nasıl verdiği ve cevabı nasıl aldığıyla ilgilidir. Çalışma ağacında yöneticinin 11 Kasım'da `ortak.md` ve `baslik.md`'de yaptığı iki değişiklik var; bunlar Adım 1'de commit edilir.
- Adımların ürettiği çıktının biçimi (şemalar) değişmez. Daha önce üretilmiş başlık çalışmaları ve kayıtlar okunmaya devam eder.
- Hiçbir kullanıcı verisi silinmez.
- data/ yalnız Adım 7'de, CLAUDE.md kuralına göre değişir.
- Adım 7'deki tek gerçek çalışma dışında Claude çağrılmaz. O çalışma 200 bin token okumayı geçerse hemen durdurulur ve rapora yazılır.

==================================================
ADIM 1 — v0.19.0'ı main'e al
==================================================
1. Program açıksa kapanmasını bekle.
2. Çalışma ağacındaki talimat değişikliklerini yeni dalda ilk commit olarak ekle. Mesaj: "talimat: işletme adları geçmez (ortak.md); mahalle konu evreninde 'yeme içme' (baslik.md)".
3. `a49c6d0`'ın CI sonucunu kontrol et. main'i bu commit'e fast-forward ile getir ve push et. "v0.19.0" açıklamalı etiketini koy; mesajı: "v0.19.0 — arayüz düzeltmeleri: İşler panelinde temizleme, Ayarlar düzeni, tek pencere". main'in GÖREV-17 raporunda "sürüyor" görünen CI çalışmasına da bak.
4. Güncel main'den "gorev-18-token-kontrolu" dalını aç.

==================================================
ADIM 2 — Bütün Claude adımları tek çağrılı ve araçsız olur
==================================================
Kapsam: `baslik`, `baslik_degerlendirme`, `metin_plan`, `metin_plan_elestiri`, `metin_bolum`, `metin_birlestirme`, `metin_giris_kapanis`, `metin_son_okuma`, `metin_ceviri`. Kullanım ölçümü (Haiku, tek tur) zaten böyle; ona dokunma.

Yeni düzen:
1. **Malzeme istemin içinde verilir.** Bugün çalışma klasörüne yazılan girdi dosyaları aynı adlarla ve aynı içerikle hazırlanmaya devam eder; kayıt ve denetim için klasörde de dururlar. Ama Claude onları açmaz: program hepsini tek bir istem metninde, her biri kendi adıyla ayrılmış bölümler olarak verir.
2. **Araç yok, tek tur.** Claude'a `Read`, `Write` ya da başka bir araç verilmez. Tur sınırı 1'dir. Claude cevabını doğrudan şemaya uyan JSON olarak verir; program bunu alır, doğrular ve çıktı dosyasını (`baslik.json`, `plan.json` ve öbürleri) kendisi yazar.
   - Claude Code komut satırının araçsız çalıştırma ve yapılandırılmış çıktı seçeneklerine `claude --help` ile bak; Housing Atlas'taki yönteme uy.
   - Cevabın başında ya da sonunda JSON dışı metin gelirse program JSON'u ayıklar. Ayıklayamazsa bu "geçersiz cevap"tır.
3. **Talimatlar değişmez.** Talimat metinleri "plan.json dosyasında" gibi dosya adlarıyla konuşuyor. Bu adlar istemdeki bölüm adlarıyla aynı kalır. İstemin başına program şu açıklamayı koyar (görev metni; talimat dosyası değildir):

   "Talimatta adı geçen dosyalar aşağıda, her biri kendi adıyla verilmiştir; başka dosya yoktur ve dosya açman gerekmez. Çıktını bir dosyaya yazma: cevabın yalnızca şemaya uyan JSON olsun, başına ya da sonuna başka bir şey ekleme."
4. **Geçersiz cevap.** Şemaya uymayan ya da denetimden geçmeyen cevap bir kez yeniden istenir. Bu ikinci çağrı da tek turdur; önceki cevabı ve hataları içerir. İkincisi de olmazsa adım hata verir. Bugünkü kural aynen böyledir.
5. **Büyük malzeme.** Bir adımın istemi tek çağrıya sığmayacak kadar büyükse (Ayarlar'daki tek çağrı sınırını aşıyorsa), program çalışmayı başlatmaz ve neden başlatmadığını söyler. Çeviri bugün olduğu gibi dilimlere bölünür; her dilim tek çağrıdır.
6. **Canlı izleme.** İş günlüğü artık "Tur 3/30 · Okuyor: …" yazmaz. Yerine çağrının aşamasını yazar: istem hazırlandı (kaç bin token tahmini), Claude düşünüyor, cevap geldi (kaç bin token okundu ve yazıldı), doğrulandı.
7. **Cevap kesilirse.** Tek turda cevabın tamamı bir kerede yazılır; başlık adımında bu büyük bir çıktıdır (ölçülen çalışmalarda düşünmeyle birlikte 53–65 bin token). Komut satırının çıktı sınırına bak ve gerekiyorsa yükselt. Cevap uzunluk sınırında kesilirse program bunu "geçersiz JSON" olarak değil, ayrı bir durum olarak tanır ("cevap uzunluk sınırında kesildi") ve günlüğe yazar. Kesilen cevap kabul edilmez.
8. **Malzeme sessizce kırpılmaz.** Program hiçbir adımda malzemeyi kendiliğinden kesmez ya da özetlemez. Sığmıyorsa başlatmaz ve söyler (madde 5).
9. **Eski düzen kalkar.** Araçlı çok turlu yol bu adımlar için kaldırılır; ayar olarak da sunulmaz. Çalıştırıcının araçlı yolu başka bir iş için gerekiyorsa kodda kalabilir, ama hiçbir adım onu kullanmaz.

Paralel çalışma: bölüm yazıcıları için "Aynı anda en çok Claude oturumu" ayarının başlangıç değeri 6 olur (1–8 arası). Kullanıcı ayarı daha önce değiştirdiyse onun değeri kalır.

==================================================
ADIM 3 — Malzeme: önce kalite, kısaltma yalnız tekrar için
==================================================
Kullanıcının şartı: kısaltırken ve parçalara bölerken işin kalitesi bozulmasın. Tasarrufun asıl kaynağı Adım 2'dir (aynı malzemenin 5–6 kez yeniden okunmaması). Bu yüzden bu görevde Claude'un gördüğü bilgi azaltılmaz.

1. **Aynı bilgi, aynı içerik.** Her adım, eski düzende çalışma klasöründe gördüğü dosyaların tamamını yeni düzende de görür. Bunu bir testle güvenceye al: her adım için istemdeki bölümlerin içeriği, eski düzenin girdi dosyalarıyla bire bir aynıdır. Yalnız aşağıdaki iki bilinçli fark olabilir.
2. **İzin verilen iki kısaltma:**
   - Aynı içerik bir istemde iki kez geçiyorsa bir kez verilir. Örnek: şemanın hem talimatta hem ayrı bölümde durması.
   - Başlık adımındaki önceki öneriler listesi, tekrarı önlemek için gereken kadarını taşır: her önerinin başlığı, bölgesi, ailesi ve tek satırlık konusu. Önceki önerilerin tam analizleri verilmez.
3. **Ölçüm tablosu.** Gerçek verinin kopyasında, her adım için istemin parçalarını ve boyutlarını çıkar: `ortak.md`, ses ve ton, adımın talimatı, şema, her girdi dosyası. Boyutu karakter ve tahmini token olarak ver ve rapora koy.
4. **Öneriler rapora, karar yöneticiye.** Bir malzemenin kısaltılabileceğini düşünüyorsan bunu uygulama; rapora yaz: hangi adım, hangi malzeme, kaç token kazandırır ve kalite için ne riski vardır. Örnek adaylar: mahalle başlığında 30A özetinin yalnız karşılaştırma blokları; son okuyucuda yazar özeti yerine yalnız kullanılan kanıt satırları. Bunlara ilk gerçek metinler görüldükten sonra karar verilecek.

==================================================
ADIM 4 — Tahmin, sınır ve gerçek harcama
==================================================
1. **Başlamadan önce tahmin.** Bir Claude işi başlatılırken program önce şunu gösterir ve onay ister:
   - kaç Claude çağrısı yapılacak,
   - kabaca kaç token okunacak ve yazılacak (istem boyutlarından hesap; çıktı için adımın önceki çalışmalarının ortancası, yoksa adım başına ayarlı bir varsayım),
   - hangi adım hangi modelle çalışacak.

   Video metninde bu, plan ve seçilen her ton için ayrı satırlarla ve toplamla gösterilir. Örnek biçim: "Plan: 2 çağrı, yaklaşık 90 bin token · Araştırmacı dost: 11 çağrı, yaklaşık 180 bin token · Toplam: yaklaşık 270 bin token".
2. **Sınırlar (Ayarlar → Claude):**
   - tek çağrı sınırı (başlangıç: 250 bin token; okunan ve yazılan toplam). Kullanıcının kuralındaki "1 milyon bile fazla" sınırı işin tek bir parçası içindir; bizde bir parça tek çağrıdır ve bu sınırın çok altında kalmalıdır.
   - iş başına toplam sınır (başlangıç: 1,5 milyon token). Bu, kaçak harcamaya karşı emniyettir; çok tonlu bir video metninin toplamı bunun altında kalır.

   Tahmin bir sınırı aşıyorsa iş başlatılmaz; ekran neyin büyük olduğunu söyler.
3. **Çalışırken.** Zincir her çağrıdan sonra gerçek toplamı günceller. Gerçek toplam iş başına sınıra ulaşırsa zincir durur ("Token sınırına ulaşıldı") ve kullanıcının "Devam" demesini bekler. Biten adımlar kaybolmaz.
4. **Bitince.** İşin kartında ve çalışma kaydında tahmin ile gerçek yan yana yazar. Gerçek, tahminin 1,5 katını geçtiyse kart kırmızı bir uyarı gösterir: "Beklenenden fazla harcandı: tahmin X, gerçek Y". Sol menüdeki Claude kullanımı kutusu da son işin gerçek harcamasını gösterir.
5. **Kayıt.** Her çağrının okunan, önbellekten okunan ve yazılan token sayıları, modeli ve süresi çalışma kaydında durur; bugün de büyük ölçüde duruyor. Geçmiş çalışmalar için Ayarlar → Claude kullanımı bölümünde adım başına ortanca ve en yüksek harcama tablosu olur.

==================================================
ADIM 5 — Model ve efor: bu görevde değişmez
==================================================
Model ve efor başlangıç değerleri bugünkü gibi kalır (planlama, yazım, eleştiri, birleştirme ve son okuma Opus; çeviri Sonnet). Daha ucuz modele geçiş kaliteyi etkileyebilir; bu yüzden ilk gerçek metinler görülüp ölçüldükten sonra, yönetici ve kullanıcı birlikte karar verecek. Bu görevde yalnız şunu yap: Ayarlar → Claude'daki model tablosunda her adımın yanında son çalışmalarının ortanca harcamasını göster ki karar veriyle verilebilsin.

==================================================
ADIM 6 — İki program denetimi
==================================================
6a. **İşletme adı denetimi (kırmızı).** Kullanıcının kararı: videolarda marka, restoran, otel ve benzeri işletme adları geçmez; onlardan genel olarak söz edilir.
- Program, veritabanındaki işletme adlarından bir liste kurar: restoranlar, kiralama şirketleri, konaklama işletmeleri (otel, inn), günlük ihtiyaç zincirleri ve işletmeleri (market, eczane, özel sağlık kuruluşu). Liste her denetimde veriden yeniden kurulur.
- Listeye girmeyenler: topluluk ve yer adları (Rosemary Beach, Seaside, WaterColor, Alys Beach ve öbür mahalleler), kamu kurumları ve resmî kaynaklar (Walton County, Visit South Walton, NOAA, FDOT gibi), devlet parkları ve plaj erişimleri, etkinlikler.
  - Bir işletmenin adı bir yer adıyla aynıysa ya da onu içeriyorsa (örneğin "Rosemary Beach®" adlı kiralama şirketi), yer adının kendisi işaretlenmez.
  - İstisna listesi ve elle eklenen adlar Ayarlar'dan düzenlenir: uyarı ifadeleri kutusunun yanında "İşletme adları: ekle / hariç tut".
- Denetim iki yerde çalışır: video metninin program denetiminde (cümleye bağlı kırmızı bulgu: "işletme adı: <ad>") ve başlık adaylarında (İngilizce başlıkta ya da kapak fikrinde işletme adı varsa aday kartında kırmızı uyarı).
- Denetim kimseyi durdurmaz; bulguyu gösterir.

6b. **Başlık ve kapak uyarıları (sarı).** Başlık adayları ve kullanıcının kendi başlığı için, aday kartında gösterilir:
- İngilizce başlığın konusu ilk 40 karakterde değilse: "Telefonda yalnız ilk yaklaşık 40 karakter görünür; konu orada olmalı". Başlık eki bu hesaba girmez, çünkü zaten sondadır.
- Kapak fikrindeki kapak yazısı 3 kelimeden uzunsa ya da başlıktaki kelimeleri tekrar ediyorsa (bağlaçlar ve "30A" hariç).
- Başlıkta 2'den fazla tamamı büyük harfli kelime varsa.

Bu uyarılar yalnız bilgidir; aday reddedilmez. Kapak yazısı kapak fikri metninden ayrılamıyorsa bu uyarıyı kurma ve rapora yaz.

6c. **Küçük düzeltme.** Ayarlar → Hakkında kartındaki eskimiş cümle ("Sonraki aşama: Claude ile video metni…") programın bugünkü durumuna göre düzeltilir.

==================================================
ADIM 7 — Testler, ölçüm, gerçek ortam ve teslim
==================================================
1. **Testler.** Sahte claude programı yeni düzene uyarlanır: istemi standart girdiden alır, tek cevap verir, araç çağırmaz. En az şunlar sınanır:
   - her adımın isteminde talimatta adı geçen bütün bölümlerin bulunması ve fazladan bölüm olmaması;
   - komutta araç olmaması ve tur sınırının 1 olması;
   - JSON'un ayıklanması (başında ve sonunda metin, kod çiti);
   - geçersiz cevapta tek yeniden deneme;
   - çevirinin dilimleri;
   - tek çağrı sınırını aşan istemde başlatmama; malzemenin hiçbir yerde sessizce kırpılmaması;
   - her adımda istemdeki bölümlerin eski girdi dosyalarıyla aynı içerikte olması (Adım 3'teki iki fark dışında);
   - cevabın uzunluk sınırında kesilmesinin ayrı tanınması;
   - tahminin hesaplanması ve ekranda gösterilmesi;
   - iş başına sınırda başlatmama ve çalışırken durma, "Devam";
   - tahmin ile gerçek karşılaştırması ve kırmızı uyarı;
   - model ve efor değerlerinin bu görevle değişmemesi;
   - işletme adı denetimi (yer adıyla çakışan işletme adı dahil) ve Ayarlar'daki istisnalar;
   - başlık ve kapak uyarıları;
   - video metni zincirinin iki tonla uçtan uca çalışması ve toplam çağrı sayısı.

   Tam takım yerelde art arda en az 3 kez geçmeli.
2. **Ölçüm tablosu (gerçek verinin kopyası, Claude çağrılmadan).** Her adım için eski düzenin ölçülen ya da hesaplanan harcaması ile yeni düzenin tahmini yan yana verilir. Video metni için: plan, bir ton ve iki ton toplamları.
3. **Tek gerçek ölçüm (kullanıcının izniyle).** Geçici kopyada, gerçek Claude ile bir "başlık değerlendirme" çalışması yap. Kullanıcının 10 Ekim'deki fikrini kullan ("Rosemary Beach'e köpeğimizle gitsek nasıl olur?"); eski düzende 416 bin token okumuştu. Rapora yaz: çağrı sayısı, okunan ve yazılan token, süre, bedel karşılığı, programın tahmini ve sonucun eskisiyle aynı yönde olup olmadığı (o gün "veriyle dolmuyor" demişti). 200 bin tokeni geçerse durdur.
4. **Gerçek veritabanı** (CLAUDE.md kuralına göre): tam yedek; program kısayolla açılır; Ayarlar → Claude'da yeni sınırlar görünür; Claude çalıştırılmaz; program kapatılır; önce ve sonra karşılaştırması.
5. **Belgeler.** M15 (Claude adımları: yeni çağırma düzeni, tahmin ve sınırlar), M17 (video metni zinciri), CALISMA_MANTIGI.md, README.md, docs/DEVIR/05 ve 02. CLAUDE.md'ye kısa bir kural eklenir: programın Claude adımları araçsız ve tek turludur; yeni bir adım eklenirken malzeme istemin içinde verilir, tahmin ve sınır tanımlanır.

TESLİM
docs/gorevler/GOREV-18/ altına şunlar konur:
- GOREV.md (work/gorevler/GOREV-18.md'nin kopyası) ve RAPOR.md,
- ölçüm tabloları,
- tek gerçek çalışmanın çıktısı ve harcaması,
- ekran görüntüleri:
  - başlamadan önceki tahmin ve onay (başlık ve video metni),
  - iş kartında tahmin ile gerçek,
  - kırmızı "beklenenden fazla" uyarısı (sahte claude ile),
  - Ayarlar → Claude: sınırlar, model tablosu, adım başına harcama tablosu,
  - işletme adı bulgusu (metinde ve başlık adayında),
  - başlık ve kapak uyarıları.

RAPOR.md Türkçe ve sade olur. İçinde şunlar bulunur:
- her adımın sonucu;
- main ve etiketin konumu, CI ve test sayıları;
- eski ve yeni düzenin harcama tablosu;
- malzemenin eski düzenle aynı kaldığının kanıtı ve kısaltma önerileri (uygulanmadan);
- Housing Atlas'tan alınanlar;
- gerçek veritabanının önce ve sonrası;
- kullanıcının görevden sonra yapacakları;
- yöneticinin karar vermesi gereken konular.

Push etmeden önce `git status` ile work/ ve data/ içeriğinin sahnede olmadığını kontrol et.

Son mesajında kullanıcıya yalnız şunu söyle: "Görev bitti. Yöneticiye şunu yaz: GÖREV-18 bitti, dal gorev-18-token-kontrolu, son commit <hash>." Bir adım tamamlanamadıysa bunu aynı mesaja tek cümleyle ekle.
