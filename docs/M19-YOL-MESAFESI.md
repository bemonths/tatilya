# M19 — Yol üzerinden mesafe ve tahmini sürüş süresi

Tarih: 16 Kasım 2026 · Görev: GÖREV-20 · Dal: `gorev-20-eksik-veri` · Uygulama `0.21.0` · Şema `20` · Toplayıcı `openstreetmap-road-network/1`

## Amaç

Günlük ihtiyaç mesafeleri (M13) kuş uçuşudur. Ziyaretçinin sorusu ise "markete, eczaneye, acil servise, havalimanına arabayla ne kadar" sorusudur. Bu toplayıcı, kuş uçuşu ölçülen her ilan–nokta çifti için **yol üzerinden mesafeyi** ve **trafik hesaba katılmadan tahmini sürüş süresini** ekler; "en yakın" noktayı yol mesafesine göre yeniden seçer. Kuş uçuşu değer yanında kalır.

## Kaynak ve yöntem

- **Kaynak:** OpenStreetMap yol ağı, Overpass API üzerinden (`https://overpass-api.de/api/interpreter`), çekim başına **tek sorgu**: yol alanındaki, yapılandırmada sayılan türlerdeki `highway` yolları ve düğümleri (`out body` + `out skel`). Ham yanıt `manifest.json` ile ve SHA-256'sıyla saklanır; OpenStreetMap'in zaman damgası (`timestamp_osm_base`) çekime yazılır. © OpenStreetMap katkıcıları, ODbL. API anahtarı, ücretli hesap ya da yol tarifi servisi yoktur.
- **Sunucu doluysa:** herkese açık Overpass sunucusu "kapasite dolu" (429/502/503/504) yanıtı verirse sorgu 30, 60, 120 ve 240 saniye bekleyerek yeniden sorulur; yine olmazsa çekim başarısız biter (önceki çekim durur).
- **Hesap programın içindedir** (`studio/sources/road_graph.py`, dış bağımlılık yok):
  - Yollar yönlü bir grafiğe çevrilir. Parça uzunluğu, ardışık iki OpenStreetMap düğümü arasındaki büyük daire uzaklığıdır.
  - **Hız:** yolun `maxspeed` etiketi okunabiliyorsa odur ("35 mph"; birimsiz sayı km/sa sayılır); yoksa yol türünün **yapılandırmadaki varsayılan hızı**. Süre = uzunluk ÷ hız. Trafik, ışık, dur levhası ve dönüş beklemesi **yoktur**.
  - **Tek yön:** `oneway=yes/-1`, dönel kavşaklar ve otoyollar yönüyle izlenir.
  - **Erişim:** `access`/`motor_vehicle`/`vehicle`/`motorcar` değeri "kapalı" listesindeyse (`no`, `military`, …) yol ağa girmez. "Kısıtlı" listesindeyse (`private`, `customers`, `destination`, …) yol yalnız yolculuğun **başındaki ve sonundaki** kesintisiz parçada kullanılabilir; içinden geçilip kısaltma yapılamaz (kapalı siteler, otoparklar).
  - **Noktanın yola bağlanması:** ilan ya da hedef, en yakın yol parçasının en yakın noktasına düz bir bacakla bağlanır (otoyol ve bağlantı yolları hariç). Bacak `snap_limit_m`'den (30A: 500 m) uzunsa nokta ölçülmez. Bacaktaki süre `snap_speed_mph` ile hesaplanır.
  - **Rota:** süreyi en aza indiren yol (en hızlı yol). Yol mesafesi bu rotanın uzunluğudur (bacaklar dahil).
  - **Kuş uçuşundan kısa olamaz:** bütün uzunluklar büyük daire uzaklığı olduğundan rota, iki ucu arasındaki kuş uçuşu mesafeden kısa çıkamaz (üçgen eşitsizliği). Toplayıcı her çifti ayrıca denetler; tablo da `road_km >= crow_km` kısıtını taşır.
- **Ölçülenler:** son konaklama çekimindeki her ilandan (koordinatı yol ağına bağlanabilen) → son günlük ihtiyaç çekimindeki her noktaya, son plaj çekimindeki her halka açık erişime ve yapılandırmadaki ek noktalara (30A: iki havalimanının yolcu terminali). İlan ve kategori başına **yol mesafesine göre en yakın nokta** saklanır: yol km, dakika, aynı noktaya kuş uçuşu km, kuş uçuşuna göre en yakın nokta ve onun km'si.

## Yapılandırma (koda gömülü değil; `destination_road_networks.settings`, JSON)

30A için başlangıç değerleri `studio/destinations/thirty_a.py` → `ROAD_NETWORK` (şema 20 göçü SQLite'a bir kez yazar; sonra yalnız SQLite'taki değer geçerlidir):

| Ayar | 30A değeri |
|---|---|
| Alan (`area`) | güney 30,14 · batı −86,62 · kuzey 30,56 · doğu −85,72: günlük ihtiyaç alanı, iki havalimanını ve onlara giden yolları (VPS için Mid-Bay Köprüsü ve SR 20, ECP için SR 79 ve CR 388) içine alacak kadar genişletildi |
| Varsayılan hızlar (`speeds_mph`, mil/saat) | motorway 65 · trunk 55 · primary 45 · secondary 40 · tertiary 35 · unclassified 30 · residential 25 · living_street 15 · service 10 · motorway_link 40 · trunk_link 35 · primary_link 30 · secondary_link 30 · tertiary_link 25 |
| Kapalı erişim (`closed_access`) | no, military, agricultural, forestry, emergency, delivery |
| Kısıtlı erişim (`restricted_access`) | private, customers, destination, permit, residents |
| Atlanan servis yolları (`skipped_service`) | parking_aisle, driveway, drive-through, emergency_access |
| Bağlanılmayan türler (`no_snap`) | motorway ve bütün bağlantı (`_link`) yolları |
| Bağlama sınırı ve hızı | 500 m · 10 mil/saat |
| Ek noktalar (`extra_points`) | VPS ve ECP yolcu terminalleri (OpenStreetMap'teki terminal binasının merkezi; way/162782748 ve way/122421519) |
| Uzunluk sağlaması (`length_checks`) | CR 30A: FDOT yol envanteri 18,561 mil (referans satırı `genel-30a-ilce-yolu`) |

Varsayılan hızlar **bizim varsayımımızdır** ve yalnız `maxspeed` etiketi olmayan yollarda kullanılır (16 Kasım 2026 çekiminde 4.418 km yolun 878 km'sinde etiket vardı). Değerler Florida'nın yasal sınırlarının aralığındadır (yerleşim bölgesinde 30, diğer yollarda 55, sınırlı erişimli otoyolda 70 mil/saate kadar); yol türüne göre seçimleri kaynak gerçeği değildir.

## Saklanan alanlar (şema 20)

- `destination_road_networks`: destinasyon başına ayarlar (JSON).
- `road_snapshots`: çekimin kullandığı ayarlar, sorgu tarihi, OpenStreetMap zaman damgası, yol ve düğüm sayısı, ağın km'si ve hız etiketi taşıyan km, ölçülen konaklama, günlük ihtiyaç ve plaj çekimlerinin kimlikleri, ilan sayıları (toplam, yola bağlanan, ölçülen), hedef sayısı, uzunluk sağlamaları.
- `road_targets`: ölçülen her hedef (günlük ihtiyaç noktası, plaj erişimi, ek nokta), yola bağlanma mesafesi, ulaşan ilan sayısı.
- `road_nearest`: ilan × kategori: yol mesafesine göre en yakın hedef, yol km, dakika, o hedefe kuş uçuşu km, kuş uçuşuna göre en yakın hedef ve km'si, ilanın yola bağlanma mesafesi. Kısıt: `road_km >= crow_km`.

## Okuma anında özet

`road_network.summarize`: mahalle × kategori için ölçülen ilan sayısı, **yol mesafesi ortancası** (km, mil), **tahmini sürüş ortancası** (dakika), **aynı ilanların kuş uçuşu ortancası**, 1 yol mili içindeki ilan payı, en yakını kuş uçuşuna göre olandan farklı çıkan ilan payı ve mahallede en sık en yakın çıkan nokta. Ortancalar ve paylar bizim hesabımızdır. Çekimden sonra yeni bir konaklama ya da günlük ihtiyaç çekimi yapıldıysa özet bunu söyler (`stale_inputs`) ve "Güncelleme zamanı gelenler" tablosunda toplayıcı "girdisi yenilendi" diye zamanı gelmiş görünür.

## Sağlama (16 Kasım 2026, gerçek veri)

- **CR 30A uzunluğu:** OpenStreetMap'te `ref=CR 30A` taşıyan yolların toplamı 19,06 mil; FDOT yol envanterinde 18,561 mil (fark %2,7; OpenStreetMap'te dönel kavşak kolları ve bölünmüş kısa parçalar ayrı sayılır). Her çekimde yeniden hesaplanır ve çekime yazılır; düzeltme yapılmaz.
- **Kuş uçuşundan kısa yol yok:** bütün ilan–hedef çiftlerinde denetlenir (test ve tablo kısıtı).
- Mahalle tabloları ve havalimanı süreleri: `docs/gorevler/GOREV-20/RAPOR.md` ve `yol-mesafesi-mahalle.csv`.

## Arayüz

Mahalleler sekmesinde, günlük ihtiyaç bölümünün altında **"Yol üzerinden mesafe ve tahmini sürüş süresi"**: "Yol mesafelerini hesapla" düğmesi, sürüm seçici, ham manifest; çekimin bilgileri (ağın büyüklüğü, ölçülen ve ölçülmeyen ilan, varsayılan hızlar, sağlama); mahalle × nokta türü tablosu (yol mil · dakika; altında kuş uçuşu ve 1 yol mili içindeki pay) ve havalimanı tablosu.

## Sınırlar

- Süre **tahmindir ve trafik yoktur**: ışık, dur levhası, dönüş, park ve yoğun sezon trafiği hesapta değildir; gerçek süre daha uzundur. Anlık ya da tarihsel trafik verisi kapsam dışıdır (ücretli veri).
- OpenStreetMap gönüllülerin haritasıdır: eksik bir yol, yanlış bir tek yön ya da erişim etiketi rotayı değiştirir. Hız sınırı etiketi yolların küçük bir kısmında vardır; gerisi varsayılan hızdır.
- Yola `snap_limit_m` içinde bağlanamayan ilan (koordinatı hatalı ya da alan dışında) ölçülmez; sayısı çekimde ve arayüzde yazar.
- "En yakın" nokta yol **mesafesine** göredir; en kısa sürede varılan nokta başka olabilir.
- Yürüme ve bisiklet yolu, kaldırım ve patika hesaplanmaz. **"Yürüme mesafesi" denmez.**
- Yol mesafeleri, çekimin yapıldığı gündeki konaklama ve günlük ihtiyaç çekimleriyle hesaplanır; onlar yenilenince yeniden hesaplanmalıdır.

## Video dili

Kullanılabilir: "OpenStreetMap yol ağına göre, Seaside'daki ilanların ortancası en yakın büyük süpermarkete yol üzerinden yaklaşık X mil; trafik hesaba katılmadan tahmini sürüş yaklaşık Y dakika", "kuş uçuşu X mil olan mesafe yol üzerinden Y mil", "ilanlardan VPS havalimanı terminaline yol üzerinden ortanca X mil, trafik hesaba katılmadan tahmini Y dakika". Süre her zaman **"tahmini"** ve **"trafik hesaba katılmadan"** diye söylenir.

Kullanılmaz: "yürüme mesafesi", "X dakikada varırsınız", "havalimanı X dakika" (tahmin ve trafik notu olmadan), trafikli gerçek süre ya da sıkışıklık iddiası, bisiklet ve yürüme süresi.

Program denetimi (M17): "minute drive", "minutes away", "minutes to drive" ifadeleri, cümle bir **yol mesafesi kanıtını** işaret etmiyorsa kırmızıdır (`surus_suresi`); işaret ediyorsa serbesttir. Yürüme ifadeleri her zaman kırmızıdır.

## Mimari sınır

- **Generic:** `studio/sources/road_graph.py` (grafik, bağlama, rota) ve `studio/sources/road_network.py` (sorgu, ölçüm, saklama, özet). 30A'ya özel hiçbir şey yok.
- **Destinasyona özel:** `thirty_a.py` → `ROAD_NETWORK` (alan, hızlar, erişim kuralları, ek noktalar, sağlama uzunlukları) ve kaynak tohumu.

## Testler

`tests/test_road_network.py` (küçük sentetik ağ, canlı ağ yok): yapılandırılmış yolların alınması, kapalı ve atlanan yolların dışarıda kalması; hızın `maxspeed`'den ya da ayardaki varsayılandan gelmesi (ayar değişince süre değişir); **yol mesafesinin kuş uçuşundan kısa olmaması**; en hızlı rotanın seçilmesi ve uzunluğunun o rotanın uzunluğu olması; tek yönlü yollar; özel yolun yolculuğun ucunda kullanılıp içinden geçilmemesi; yoldan uzak noktanın bağlanmaması; **en yakın noktanın yol mesafesine göre seçilmesi**; tek sorgu, dolu sunucuda bekleme, uzunluk sağlaması, ham kopya; API özeti (yol ve kuş uçuşu yan yana, eskiyen girdi uyarısı, tablonun kısa yolu reddetmesi); şema 19 → 20 göçü (eski satırlar aynı). `tests/test_gorev20.py`: kanıt paketindeki satırlar. `tests/frontend.test.mjs`: tablo hücreleri.
