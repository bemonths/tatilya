HEDEF-03 — Kiralama fiyatlarındaki eksik şirketleri tamamla (Rosemary Beach, Alys Beach ve öbürleri), yalnız onları yeniden oku, veri paketini tazele

BU BİR HEDEFTİR
HEDEF-01 ve HEDEF-02'deki gibi çalışırsın:
- teknik kararları sen verirsin;
- ilerlemeyi `work\hedef\DURUM.md`'ye yazarsın;
- yalnız "Duracağın yerler"de durursun.

Önce şunları oku: `CLAUDE.md`, `docs/gorevler/HEDEF-02/HEDEF.md` ve `RAPOR.md` (özellikle bölüm 7 ve 10), `docs/M11-KONAKLAMA-FIYATLARI.md`, `docs/M16-TARAYICI-EKLENTISI.md`.

**Fark:** Bu hedefte kullanıcı (Mucahit) bilgisayarın başında. Yalnız onun yapabileceği bir şey gerektiğinde (Chrome'da doğrulama kutusu, eklenti izni), Claude Code sohbetinde ona kısa ve ekran adlarıyla söyle, sonra bekle. Teknik konularda yine soru sorma.

DURUM
main `6a89742` = `v0.28.0`. Kurtarılan kiralama sürümü `7cba8d4cffbb4e0dbf076e66acba2c0f` (26–27 Kasım gecesi).

Fiyatı eksik kalan şirketler (HEDEF-02 raporu, bölüm 7 ve 10):

| Şirket | Book>Direct ilanı | Gece sonucu | Sebep (raporda) |
|---|---:|---|---|
| 30A Escapes (30aescapes.com) | 162 | 0 fiyat | Track; fiyat sorusu (`POST /ajax/quote`) eklentinin izinli sorgu listesinde yok |
| Ocean Reef Resorts (oceanreefresorts.com) | 96 | 0 | aynı |
| Rosemary Beach® (rosemarybeach.com) | 89 | 0 | aynı |
| Panhandle Getaways (panhandlegetaways.com) | 81 | 0 | aynı |
| RealJoy (realjoy.com) | 61 | 10 bağlı, 100 fiyat | ikinci doğrulama sayfasında durdu (kullanıcı yoktu) |
| Vacasa (vacasa.com) | 35 | 3 bağlı, 23 fiyat | cevaplarda kira ya da toplam eksik |
| Alys Beach Vacation Rentals (alysbeach.com) | 6–7 | 0 | eklentide açılamadı |

Bu yüzden ilk videonun "bir hafta ne tutar" sorusunda iki önemli mahalle zayıf:
- **Alys Beach:** hiç fiyat yok.
- **Rosemary Beach:** 166 ilanın yalnız 20'si fiyatlı.

**Kullanıcı kararı (17 Kasım 2026, CLAUDE.md'de):** eklenti, sitenin kendi sekmesinden, sayfanın ziyaretçi için zaten yaptığı herkese açık sorguları (fiyat, liste) gönderebilir. Bu dört Track sitesinin `POST /ajax/quote` sorusu bu kararın içindedir. İzinli listeye eklenmesi için yeni bir kullanıcı kararı gerekmez. Yasaklar aynen geçerlidir: giriş, ödeme, rezervasyon, sepet, kişisel bilgi, doğrulama çözme.

==================================================
"BİTTİ" NE DEMEK
==================================================
1. **Track siteleri.** 30A Escapes, Ocean Reef Resorts, Rosemary Beach® ve Panhandle Getaways için fiyat sorusu eklentinin izinli sorgu listesinde.
   - Alanlar sayfanın kendi gönderdiği alanlar. RealJoy'un `/ajax/quote` düzeninden farkları varsa yaz.
   - Okuyucu, eklenti yolundan fiyatı alıyor. Bu, gerçek kayıtlardan kesilmiş fixture ile test edilir.
2. **Alys Beach.** Eklentinin siteyi neden açamadığı bulundu ve düzeltildi. Gerçekten yalnız kullanıcının verebileceği bir izin ya da doğrulama ise, bu sohbette istenir.
3. **Vacasa.** Cevaplarda kira ya da toplamın neden eksik geldiği bulundu ve okuyucu düzeltildi; ya da sitenin göstermediği bir şeyse kayda geçti. Fiyat uydurulmaz.
4. **RealJoy.** İkinci doğrulamada durmasının sebebi anlaşıldı. Kullanıcı başındayken yeniden okunuyor. Gerekiyorsa aralık ya da sıra ayarlanır; 429 kuralı aynen kalır.
5. **"Seçili şirketleri yeniden oku".**
   - Programda bir kiralama çekimi yalnız seçilen şirketleri yeniden okuyabilir. Yeri: Sol menü → Veri → Toplama → Konaklama → "Konaklama fiyatları" bölümü.
   - Sonuç yeni bir kiralama sürümüdür. Seçilmeyen şirketlerin sonuçları son başarılı sürümden olduğu gibi taşınır. Her şirketin satırında kendi sorgu tarihi görünür.
   - Kurtarma dosyası düzeni bu çekimde de çalışır.
   - Test edilir: taşınan şirketin değişmemesi, yeni okunanın değişmesi, sürümün bütün olması.
6. **Deneme.** Bu yedi şirket deneme çekiminde (gerçek veriye karışmadan) okundu ve geçti. Deneme, kaydetme adımını da sınıyor (HEDEF-02).
7. **Gerçek okuma.** Program kapalıyken yedek alınır, sonra "Seçili şirketleri yeniden oku" bu yedi şirketle gerçek veride çalıştırılır.
   - Başlatan sensin, kullanıcı başında.
   - Doğrulama ya da izin gerekirse Claude Code sohbetinde kullanıcıya söyle: hangi pencerede neyi işaretleyeceği, eklenti simgesinden hangi siteye "İzin ver" diyeceği.
   - Başlamadan önce tahmini süreyi ona yaz.
8. **Yol ağı yeniden çalıştırıldı.** Güncel günlük ihtiyaç ve plaj sürümleriyle ölçülsün diye; kısa bir iş.
9. **Kapsam tablosu ve video.**
   - HEDEF-02 bölüm 7'deki "13 mahalle — kiralama" ve "Kiralama şirketleri" tabloları yeni sürümle yeniden yazılır; önce ve sonra yan yana.
   - Açık videonun (`7b025758…`) 2 · Veri paketi adımı yeni kiralama sürümüyle yeniden kurulur. Adım "eskidi"ye düşerse yeniden çalıştırılır; 3 · Plan "hazır"da kalır.
   - Plan ve yazımın tahmini yeniden yazılır.
10. **Teslim.** Testler (tam takım), CI, main'e fast-forward, `v0.29.0`. Rapor `docs/gorevler/HEDEF-03/RAPOR.md`.

==================================================
İZİNLER (kullanıcı verdi)
==================================================
- **main ve etiket.** `hedef-03` dalında çalışırsın; testler ve CI geçince main'e fast-forward ile alır, etiketi koyarsın.
- **İzinli sorgular.** Dört Track sitesinin fiyat sorusu izinli sorgu listesine eklenir; liste değişikliği yapılandırmada ve gerçek veride yedekten sonra.
- **Gerçek veride çalıştırabileceklerin:** deneme çekimi; "Seçili şirketleri yeniden oku" (yalnız bu yedi şirket); yol ağı. Her gerçek veri değişikliğinden önce, program kapalıyken tam yedek.
- **Canlı incelemeler.** Okuyucu hataları için site başına en çok 10 sayfa; aynı sitede 8 sn (RealJoy 12 sn) aralık; proxy ve eklenti kuralları aynen.
- **Gerçek Claude yok.**
- **Alt ajan.** Kullanabilirsin; DURUM'a yaz.

==================================================
DEĞİŞMEYEN KURALLAR
==================================================
HEDEF-01 ve HEDEF-02'deki değişmeyen kurallar aynen geçerlidir. Bütün kiralama çekimi (28 şirket) bu hedefte başlatılmaz.

==================================================
DURACAĞIN YERLER
==================================================
- "Bitti"nin hepsi doğru.
- Kalan iş yalnız kullanıcının yapabileceği bir şeye bağlı ve kullanıcı cevap vermiyor. 15 dakika bekle, sonra DURUM'a yaz ve öbür işlere geç. Hepsi bittiyse dur.
- Veri kaybı şüphesi; bir kuralın değişmesi gerekiyor; makale adımları gerekiyor.

TESLİM
`docs/gorevler/HEDEF-03/` altında `HEDEF.md` (bu dosya) ve `RAPOR.md`. Raporda şunlar olsun:
- her şirketin kök nedeni ve düzeltmesi;
- izinli sorgu listesinin yeni hâli;
- "Seçili şirketleri yeniden oku"nun tasarımı;
- deneme ve gerçek okuma sonuçları;
- önce ve sonra kapsam tabloları;
- veri paketinin ve tahminlerin yeni hâli;
- açık kalanlar;
- yedekler;
- testler ve CI.

Bitince kullanıcıya son mesajın yalnız şu olsun: "HEDEF-03 bitti, son commit <hash>" ve varsa açık kalanlar (kısa).
