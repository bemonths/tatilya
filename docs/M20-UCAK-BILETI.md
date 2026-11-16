# M20 — Uçak bileti: havalimanı ortalama iç hat bilet ücreti (BTS)

Tarih: 16 Kasım 2026 · Görev: GÖREV-20 · Dal: `gorev-20-eksik-veri` · Uygulama `0.21.0` · Şema `20` · Toplayıcı `bts-airport-fares/1`

## Amaç

"30A'ya uçmak ne tutar" sorusuna, resmî bir kaynağın söylediği kadarıyla kanıt. Program uçak bileti aramaz ve tarihli fiyat toplamaz; yalnız ABD Ulaştırma İstatistikleri Bürosu'nun (BTS) havalimanı başına yayımladığı çeyreklik ortalamayı okur.

## Kaynak

- **BTS — "Average Domestic Airline Itinerary Fares"** (TranStats): `https://www.transtats.bts.gov/AverageFare/`. Sayfa ilk açılışta **son yayımlanan çeyreği** gösterir; önceki çeyrekler sayfanın kendi formuyla (çeyrek, yıl, "Submit") istenir. Giriş, anahtar ya da bot koruması yoktur; doğrudan okunur.
- İstekler sıralıdır, iki istek arası 8 saniye. Her yanıt `manifest.json` ile ve SHA-256'sıyla saklanır. Sayfa isteği reddederse (403/429) ya da istenen dönemi döndürmezse çekim bırakılır ve nedeni kayda yazılır.
- Yapılandırma `destination_airfare_sources` (şema 20): havalimanları ve kaç çeyrek okunacağı. 30A: VPS (Destin–Fort Walton Beach) ve ECP (Northwest Florida Beaches); 5 çeyrek = son yayımlanan çeyrek, ondan önceki üç çeyrek ve bir yıl önceki aynı çeyrek (`thirty_a.py` → `AIRFARE`).

## Değerin anlamı (kaynağın tanımı)

Tablonun başlığı **"By Origin City"**dir: değer, **o havalimanından başlayan** iç hat yolculuklarının (itinerary) ortalama ücretidir. Kaynağın notu (çekimle birlikte İngilizce aslıyla saklanır):

- Gidiş-dönüş bilet ya da dönüşü alınmamış tek yön bilet; toplam bilet değeri (havayolunun fiyatı + satın almada alınan vergi ve ücretler).
- Bagaj gibi havalimanında ya da uçakta ödenen ücretler **dahil değildir**.
- Sıfır ücretli (mil ile alınan) biletler ve birkaç olağan dışı yüksek ücret ortalamaya girmez.
- Veri: Airline Origin & Destination Survey, biletlerin **%10'luk örneği** (DB1B).
- Sayfa ayrıca enflasyona göre düzeltilmiş ücreti (son çeyreğin dolarıyla) ve havalimanının yolcu sırasını verir; ikisi de saklanır.

**Önemli:** bu, "bütün şehirlerden o havalimanına gelen ziyaretçinin ödediği ortalama" değildir; o havalimanından yola çıkanların (büyük ölçüde bölgede yaşayanların) biletlerinin ortalamasıdır. Belirli bir şehirden 30A'ya bilet fiyatı da değildir. Görev metni değeri "bütün kalkış noktalarından o havalimanına" diye tarif etmişti; kaynağın tanımı bunun tersidir ve etiket kaynağın tanımına göre yazıldı.

## Saklanan alanlar (şema 20)

- `airfare_snapshots`: sorgu tarihi, istek sayısı, son yayımlanan yıl ve çeyrek, okunan çeyrek sayısı, havalimanları, kaynağın "Source" ve "Itinerary Fare" notları.
- `airfare_quarters` (havalimanı × yıl × çeyrek): tabloda olup olmadığı (`listed`), şehir adı, eyalet, yolcu sırası ve sıranın dayanağı, **ortalama ücret** (nominal dolar), enflasyona göre düzeltilmiş ücret ve baz çeyreği, sayfanın başlığı, ham yanıtın SHA-256'sı. Havalimanı bir çeyreğin tablosunda yoksa satır `listed=0` ve ücret NULL olarak kalır; sıfır yazılmaz.

## Okuma anında hesap

`airfare.summarize`: havalimanı başına çeyrekler (yeniden eskiye), son çeyrek, bir yıl önceki aynı çeyrek ve aralarındaki **fark** (tutar ve yüzde; nominal dolar; bizim hesabımız).

## İlk çekim (16 Kasım 2026, gerçek veri)

Değerler `docs/gorevler/GOREV-20/RAPOR.md` ve `ucak-bileti.csv` içinde. Son yayımlanan çeyrek 2026 Q2: VPS $376,10 · ECP $461,65; bir yıl önce (2025 Q2): VPS $359,62 · ECP $413,03.

## Arayüz

Mahalleler sekmesinin altında **"Havalimanından başlayan iç hat yolculuklarının ortalama bilet ücreti"**: "Uçak bileti ortalamalarını topla" düğmesi, sürüm seçici, ham manifest; etiket ve not; havalimanı × çeyrek tablosu ve bir yıl önceye göre fark.

## Sınırlar

- Yalnız iki havalimanı ve yalnız o havalimanından **başlayan** yolculuklar. Varış noktasına, havayoluna, mevsime ya da satın alma zamanına göre kırılım yoktur.
- Çeyreklik ortalamadır; bir tatil haftasının bilet fiyatı değildir. BTS veriyi birkaç ay gecikmeyle yayımlar.
- İki havalimanının farkı yolcu ve hat karışımını yansıtır (ör. düşük ücretli havayolu payı); "hangisi daha ucuz" sonucu çıkarılmaz.
- Önerilen yenileme aralığı 3 aydır ("Güncelleme zamanı gelenler").

## Video dili

Kullanılabilir: "ABD Ulaştırma İstatistikleri Bürosu'na göre, 2026'nın ikinci çeyreğinde Destin–Fort Walton Beach havalimanından başlayan iç hat yolculuklarının ortalama bilet ücreti yaklaşık $376'ydı; bir yıl önce aynı çeyrekte $360" — dönem ve "bu havalimanından başlayan yolculuklar" tanımı söylenerek.

Kullanılmaz: "30A'ya uçak bileti $X", "<şehir>'den bilet $X", "bilet fiyatları şu kadar" (genelleme), "VPS daha ucuz havalimanı" (yorum), bagaj dahil toplam yolculuk maliyeti.

## Mimari sınır

- **Generic:** `studio/sources/airfare.py` (sayfanın okunması, form, ayrıştırma, saklama, özet).
- **Destinasyona özel:** `thirty_a.py` → `AIRFARE` (havalimanları, çeyrek sayısı) ve kaynak tohumu.

## Testler

`tests/test_airfare.py` (fixture: 16 Kasım 2026 ham sayfalarının kendi HTML'i, tablo birkaç havalimanına indirilmiş; canlı ağ yok): başlık, dönem, satırlar, notlar ve formun ayrıştırılması; nominal ve düzeltilmiş ücretin ayrı tutulması; beklenmeyen sayfa ve sütun sırasının reddi; önceki çeyreklerin yıl sonunu aşarak sayılması; ilk yanıt + formla dört istek, gizli form alanlarının geri gönderilmesi, ham kopyada gizli alanların saklanmaması; tabloda olmayan havalimanının ücretsiz satır olması; ret, yanlış dönem ve eksik yapılandırmada çekimin durması; API özeti ve bir yıl önceye göre fark. `tests/test_gorev20.py`: kanıt paketindeki satırlar ve kullanım notu.
