HEDEF-02 — Gece çekiminin kaybolan sonucunu kurtar, hatayı kapat, ilk videoyu makale adımının önüne getir (kendi kendine çalışma)

BU BİR HEDEFTİR
HEDEF-01'deki gibi çalışırsın:
- kullanıcı (Mucahit) başında değil;
- teknik kararları sen verirsin, soru sormak için durmazsın;
- ilerlemeyi `work\hedef\DURUM.md` dosyasına yazarsın (HEDEF-01'deki bölümlerle);
- yalnız "Duracağın yerler"de durursun.

Önce şunları oku: `CLAUDE.md`, `docs/gorevler/HEDEF-01/HEDEF.md` ve `RAPOR.md`, `docs/M11-KONAKLAMA-FIYATLARI.md`, `docs/M14-KANIT-PAKETI.md`, `docs/M21-IS-AKISI-KATMANLAR.md`, yöneticinin notları `work\yonetim\30A_PM_NOTLARI.md` (yalnız oku).

NE OLDU (27 Kasım 2026 gecesi)
Kullanıcı "Zamanı gelenleri başlat" ile gece çekimini başlattı. Durum: main `a56e5bb` = `v0.27.0`, 13 işçi.
- **Book>Direct** (iş `42fa6655…`): başarılı, 2.384 ilan.
- **Yol ağı** (iş `86695396…`): başarılı, 23.040 kayıt.
- **Kiralama şirketleri** (iş `b8055d2a0419492cacf45717ef487ff1`): 02:32'den 08:43'e kadar (yerel saat) 6 saat 11 dakika çalıştı ve bütün şirketleri okudu. Son kayıt satırı: "2384 ilan, 11408 fiyat sorgusu, kendi envanterinden 97 ev ve 28 şirket sonucu kaydediliyor." Hemen ardından iş düştü:
  - `IntegrityError: CHECK constraint failed: rule_source IS NULL OR rule_source IN ('sayfa','yanıt')`
  - yer: `jobs.py:119 _collect → database.py:597 complete_source_run → agency_rates.py:1494 store_records`.
  - Atomik yazım geri alındı; gerçek veride Ekim'in kiralama sürümü duruyor. Çekimin ham kopyaları diskte.
- Deneme çekimi (HEDEF-01) bu hatayı yakalamadı: 28 şirketin 28'i "tamamlandı" dedi. Deneme ya son kaydetme adımını çalıştırmıyor ya da hatalı değeri üreten yola girmiyor. Bunu bul.

==================================================
"BİTTİ" NE DEMEK
==================================================
1. **Hata kapandı.**
   - `rule_source` hatasının kök nedeni bulundu: hangi şirketin hangi kaydı hangi değeri yazdı.
   - Düzeltildi. Değer ya izinli değerlerden birine bağlanır ya da gerçekten yeni bir anlamsa şema ona göre genişletilir; şema değişikliği CLAUDE.md'deki kopyada deneme kuralıyla yapılır. Kararını yaz.
   - Gerçek kayıtlardan alınmış bir test, bu hatayı yeniden üretiyor ve artık geçiyor.
2. **Deneme çekimi son kaydetme adımını da sınıyor.** Deneme, gerçek çekimin kaydetme adımını veritabanının kopyasında aynen çalıştırır. Bu gece düşen türde bir hata denemede görünür.
3. **Uzun çekim bir daha bütünüyle kaybolmuyor.**
   - Kaydetme adımı düşerse, toplanan sonuçlar bir kurtarma dosyasına yazılır (`work/` dışında, `data/` altında programın kendi klasöründe).
   - İşler panelinde "Kurtarılan sonucu kaydet" gibi bir yol olur; düzeltmeden sonra sonuç yeniden çekmeden kaydedilir.
   - Test edilir.
4. **Bu gecenin sonucu kurtarıldı, ya da neden kurtarılamadığı belli.**
   - Gece çekiminin ham kopyalarından ve iş kaydından, sitelere yeniden gitmeden, bu çekimin sonucunu kurmayı dene. Programın verisi buna yetiyorsa sonuç yeni bir kiralama sürümü olarak kaydedilir.
   - Sayılar iş kaydındaki satırla karşılaştırılır: 2.384 ilan, 11.408 fiyat sorgusu, 97 ev, 28 şirket.
   - Ham kopyalar yetmiyorsa (bazı cevaplar saklanmıyorsa) kurtarma yapılmaz. Sebebini yaz. DURUM'a, kullanıcının bu gece çekimi yeniden başlatması için kısa bir tarif yaz ("Mucahit'in yapması gerekenler"). Sonra 5–8. maddeleri kiralama dışında yapabildiğin kadarıyla yap ve dur.
5. **Kısa toplayıcılar gerçek veride tazelendi.** Restoran dizini (yeni API okuyucusu), plajlar ve günlük ihtiyaç noktaları programın normal kullanımıyla çalıştırıldı.
   - **Mahalleler:** Visit South Walton'ın yeni API'si koordinat vermiyor (HEDEF-01 raporu, bölüm 7). Yöneticinin kararı: 13 mahallenin koordinatı aynı kaynağın önceki (Ekim) kayıtlarından, mahalle adıyla eşleşerek alınır; kayıtta "koordinat: aynı kaynağın <tarih> kaydından" diye işaretlenir. Öbür alanlar yeni API'den gelir.
   - **oversee.us:** bugün doğrudan isteğe açık mı, tek bir istekle bak. Açıksa korumalı site işaretini kaldırma; yalnız rapora yaz.
6. **Kapsam ölçülmüş.** HEDEF-01'in eski "Bitti" maddesi 3'teki kapsam tabloları rapora yazılır:
   - 13 mahalle: ilan, fiyatlı ilan, ay ay haftalık ortanca. 30A Beach Girls'ün kira ortancası ayrı durur.
   - Kiralama şirketleri: ilan, bağlanan, fiyatlanan.
   - Plaj erişimleri; hava, deniz suyu, kasırga; günlük ihtiyaç ve yol mesafeleri; havalimanı süreleri; uçak bileti; restoran sayıları ve fiyat seviyesi kapsamı; plaj kuralları.
   - Programın kalite ekranında (Sol menü → Veri → Kalite) açıklanmamış kırmızı bulgu kalmaz.
7. **İlk video yazım adımının önünde.** Bu madde yalnız kiralama sonucu kurtarıldıysa ya da kullanıcının yeni çekimi başarıyla bittiyse yapılır.
   - **Başlık değerlendirmesi:** Sol menü → Konu bankası → kullanıcının kendi başlığını değerlendirme, şu başlıkla: `First Time on 30A? Which Town, Which Month and What a Week Costs | 30A Florida Vacation`. Bu, bu hedefte izin verilen **tek gerçek Claude çalışmasıdır** (tahmin ~118 bin token; harcamayı tahminle yan yana yaz).
   - **Video:** bu değerlendirmeden açılır. 1 · Başlık ve vaat, onay notu "Yönetici önerisi; Mucahit değiştirebilir" ile onaylanır.
   - **Veri paketi:** 2 · Veri paketi tamamlanır.
   - **Plan:** 3 · Plan "hazır"da kalır. 3. ve 4. adımın tahminleri rapora yazılır.
8. **Teslim.** Testler (tam takım), CI, main'e fast-forward, `v0.28.0` etiketi. Rapor `docs/gorevler/HEDEF-02/RAPOR.md`.

==================================================
İZİNLER (kullanıcı verdi)
==================================================
- **main ve etiket.** `hedef-02` dalında çalışırsın; testler ve CI geçince main'e fast-forward ile alır, etiketi koyarsın.
- **Gerçek veri.** Programın normal kullanımıyla kısa toplayıcıları çalıştırabilirsin: restoran dizini, plajlar, mahalleler, günlük ihtiyaç, uçak bileti. Göç, kurtarma ve ayar da yapabilirsin. Her değişiklikten önce, program kapalıyken `data/` klasörünün tam yedeği alınır. `data/` içindeki dosyalar elle değiştirilmez.
- **Uzun kiralama çekimi.** Bunu yeniden başlatmazsın. Gerekirse kullanıcı başlatır (madde 4).
- **Canlı istekler.** Yalnız madde 5'teki kontrol için, ve bir okuyucu hatası için gerekirse site başına en çok 10 sayfa. Aynı sitede iki istek arası en az 8 saniye.
- **Gerçek Claude:** yalnız madde 7'deki tek başlık değerlendirmesi.
- **Alt ajan.** Kullanabilirsin. Ama her ajan işi için DURUM'a ne yaptırdığını yaz.

==================================================
DEĞİŞMEYEN KURALLAR
==================================================
- HEDEF-01'deki "Değişmeyen kurallar" aynen geçerlidir: CLAUDE.md'nin bilgi toplama, veri dili, veri güvenliği ve katmanlar bölümleri; proxy bilgileri hiçbir yere yazılmaz; talimat dosyalarına ve öbür depolara dokunulmaz; zamanlanmış görev yok; Windows ayarları değişmez.
- Kullanıcı verisi silinmez.

==================================================
DURACAĞIN YERLER
==================================================
- "Bitti"nin hepsi doğru (rapor main'de).
- Kurtarma mümkün değil ve kalan iş kullanıcının yeniden çekimine bağlı (madde 4). DURUM'a tarifi yaz ve dur.
- Veri kaybı şüphesi, ya da bir göçün başarısız olması: programı kapat, son yedeği yerinde bırak, yaz.
- Bir kuralın değişmesi gerekiyor.
- Makale (plan ya da yazım) çalıştırmak gerekiyor; bu hedefin dışındadır.

TESLİM
`docs/gorevler/HEDEF-02/` altında `HEDEF.md` (bu dosya) ve `RAPOR.md`. Raporda şunlar olsun:
- hatanın kök nedeni ve düzeltmesi;
- denemenin neden kaçırdığı ve şimdi nasıl yakaladığı;
- kurtarma: yapıldı mı, sayılar;
- kurtarma dosyası düzeni;
- kısa toplayıcıların sonuçları ve mahalle koordinatları kararı;
- oversee.us kontrolü;
- kapsam tabloları;
- başlık değerlendirmesinin Türkçe özeti ve harcaması;
- videonun durumu ve tahminler;
- açık kalanlar;
- yedekler;
- testler ve CI.

Bitince kullanıcıya son mesajın yalnız şu olsun: "HEDEF-02 bitti, son commit <hash>" ve varsa açık kalanlar (kısa).
