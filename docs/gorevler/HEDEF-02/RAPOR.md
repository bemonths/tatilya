# HEDEF-02 — Rapor: gece çekiminin kurtarılması, kaydetme hatası, ilk videonun hazırlığı

*27 Kasım 2026 · dal `hedef-02` · uygulama 0.28.0 · şema 25 (değişmedi) · eklenti 0.21.0 (değişmedi)*

## Kısa özet

- **Hata kapandı.** 27 Kasım gecesi kiralama çekimi kaydetme adımında düştü. Sebep: RealJoy okuyucusu, sayfanın takviminden verdiği
  cevaplarda kural kaynağını `takvim` diye yazıyordu; şema yalnız `sayfa` ve `yanıt` kabul ediyor. Değer artık `sayfa` (takvim ilan
  sayfasının parçası). Kaydetmeden önce her cevap denetleniyor; bir hata olursa hangi şirket, ilan ve hafta olduğu söyleniyor.
- **Gece çekimi sitelere yeniden gidilmeden kurtarıldı.** Program, çekimin ham kopyasındaki 17.359 cevapla aynı toplayıcıyı yeniden
  çalıştırdı. Sonuç iş kaydındaki satırla birebir aynı: **2.384 ilan, 11.408 fiyat sorgusu, 97 ev, 28 şirket**. Yeni kiralama sürümü
  `7cba8d4cffbb4e0dbf076e66acba2c0f`.
- **Uzun bir çekim bir daha bütünüyle kaybolmaz.** Kaydetme düşerse sonuç `data/kurtarma/<iş>/` klasörüne yazılır. İşler panelinde
  "Kurtarılan sonucu kaydet" ile yeniden çekmeden kaydedilir. Ham kopyası olan düşmüş bir kiralama çekimi için "Ham kopyadan yeniden kur"
  düğmesi var.
- **Deneme artık kaydetmeyi tam ölçekte sınıyor:** son gerçek kiralama çekimini ham kopyasından kurup kopya veritabanına gerçek kaydetme
  adımıyla yazıyor.
- **Kısa toplayıcılar tazelendi** (mahalleler, plajlar, restoran dizini, günlük ihtiyaç). Mahallelerin koordinatı, yöneticinin kararıyla,
  aynı kaynağın 7 Ekim kaydından alındı; kayıtta işaretli.
- **İlk video açıldı:** başlık onaylandı, veri paketi tamam, plan "hazır"da bekliyor. Tek gerçek Claude çalışması (başlık değerlendirmesi):
  tahmin 111 bin, gerçek 123 bin token (0,80 $).

## 1. Hatanın kök nedeni ve düzeltmesi

- **Hata:** `IntegrityError: CHECK constraint failed: rule_source IS NULL OR rule_source IN ('sayfa','yanıt')`
  (`jobs.py:119 _collect → database.py:597 complete_source_run → agency_rates.py:1494 store_records`).
- **Hangi şirket, hangi kayıt, hangi değer:** RealJoy (realjoy.com). `studio/sources/agency_adapters.py`, `RealJoyAdapter.calendar_answer`.
  Sayfanın kendi tarih seçicisinin verdiği üç cevap şunlar: dolu hafta (`unavailable`), giriş/çıkış günü yasak (`restricted`), en az gece
  kuralı (`restricted`). Üçü de `rule_source = "takvim"` yazıyordu. Bu kod GÖREV-25'te (17 Kasım, `9778692`) eklendi. O görevin testleri
  bu değeri doğru diye sabitlemişti, ama hiçbir test sonucu veritabanına yazmıyordu. Gece RealJoy'dan 10 ev fiyatlandı; 18 hafta takvimden
  "dolu" çıktı. Bu cevaplardan ilki tabloya girerken bütün yazım geri alındı.
- **Karar:** değer izinli değerlerden **`sayfa`ya bağlandı**; şema genişletilmedi. Gerekçe: takvim (`#pdpStoredDates`, `min_night_…`)
  ilan sayfasının içinde gelir; "kural sayfadan okundu" anlamı aynıdır. Yeni bir anlam olmadığı için şema değişikliği gerekmedi.
- **Ek korumalar:** `agency_rates.checked_quote` kaydetmeden önce her fiyat cevabını denetler. Tanınmayan bir değer "<şirket> <ilan> ·
  <hafta>: kural kaynağı "…" tanınmıyor" diye açık bir hatayla durur (gece elimizde yalnız kısıtın metni vardı). Düzeltmeden önce yazılmış
  bir kurtarma dosyasındaki `takvim` değeri kaydetmede `sayfa`ya çevrilir. Bir test, bütün okuyuculardaki sabit `rule_source`
  değerlerinin şemaya uyduğunu sınar.
- **Gerçek kayıttan test:** `tests/test_hedef02.py`, gecenin ham kopyasındaki gerçek RealJoy sayfasını kullanır
  (`raw/b8055d2a…/responses/000595.gz` → `tests/fixtures/hedef02/realjoy-stay-salty.html.gz`; realjoy.com/beach-rentals/stay-salty,
  26 Kasım 23:38:59 UTC). Bu evin Şubat haftası takvimde dolu. Eski değerle gerçek kaydetme adımı aynı `IntegrityError`'u verir (hata
  yeniden üretilir); düzeltilmiş kodla kayıt geçer.

## 2. Denemenin neden kaçırdığı ve şimdi nasıl yakaladığı

- **Neden kaçırdı:** deneme kaydetme adımını zaten çalıştırıyordu (`studio/trial_run.py`; kopyada normal iş akışı: toplama → ham dosya →
  `store_records`). Ama küçük ölçek yüzünden hatalı değeri üreten yola girmedi. RealJoy'dan 2 ilan istendi, 1'i bağlandı, tek hafta
  soruldu ve o hafta takvimde açıktı (deneme `data/deneme/20261126-235534`: RealJoy "okundu", 1 eşlenen, 1 fiyat). Takvim cevabı hiç
  oluşmadı.
- **Şimdi:** deneme, kiralama adımındaki küçük canlı okumadan sonra **son gerçek kiralama çekimini ham kopyasından yeniden kurar**
  (sitelere gidilmez) ve kopya veritabanına **gerçek kaydetme adımıyla** yazar ("kaydetme sınaması", `TrialRun.store_check`). Sonuç
  tablosunda "Kiralama şirketleri" başlığının altında "Kaydetme adımı geçti" ya da "Kaydetme adımı düştü: <hata>" ve sınanan çekimin tarihi
  görünür. Bu gece düşen türde bir hata (gerçek veride bir cevap yolunda şemaya uymayan bir değer) burada görünür; test bunu sahte bir
  değerle sınar.

## 3. Kurtarma

### Yapıldı mı, sayılar

Evet. Program gerçek veriyle açıldı. İşler panelinde gece işinin kartında önce **"Ham kopyadan yeniden kur"** (iş `4d8f29dc…`, ~100 sn),
sonra **"Kurtarılan sonucu kaydet"** düğmesine basıldı (yeni iş ve sürüm `7cba8d4cffbb4e0dbf076e66acba2c0f`).

| | iş kaydının son satırı | kurulan ve kaydedilen |
|---|---:|---:|
| ilan | 2.384 | 2.384 |
| fiyat sorgusu | 11.408 | 11.408 |
| kendi envanterinden ev | 97 | 97 |
| şirket | 28 | 28 |

- Ham kopyadaki **17.359 cevabın 17.354'ü** kullanıldı. Kullanılmayan 5 cevabın dördü, aynı isteğin o gece yarışan ikinci cevabıdır (iki
  işçi aynı anda sorduğu için iki kez gelmiş). Beşincisi 30A Escapes'in doğrudan isteğidir: yeniden kurmada şirket doğrudan tarayıcı
  sırasına geçti; sonuç aynı.
- O gece cevabı hiç gelmemiş **10 istek** (eklentinin açamadığı `http://` adresleri, Alys Beach'in iki sayfası, bir Book>Direct alan adı)
  yeniden kurmada da bağlantı hatası sayıldı. Gece de öyleydi.
- 882 yönlendirmenin hedefi o gece saklanmıyordu. 876'sının hedefi, aynı işçinin 8 sn sonraki isteğinden çıkarıldı (aşağıda). Sayıların
  birebir tutması ve cevapların neredeyse tamamının bir kez kullanılması, bu eşlemenin doğru olduğunu gösteriyor. Artık hedef saklanıyor.
- Gerçek veride `foreign_key_check` boş. Kiralama tablolarına 2.384 ilan, 11.408 + 1.164 fiyat satırı, 97 kendi evi ve 220 yayımlanmış kira
  satırı eklendi. Sürümün `metadata.kurtarma` ve `metadata.yeniden_kurma` alanları nereden geldiğini söyler. Ham kopyası gecenin
  klasörüdür (`raw/b8055d2a…`).

### Nasıl kuruldu

`studio/sources/agency_replay.py`. Aynı toplayıcı kodu (`agency_rates.collect`), aynı şirket yapılandırması, çekimin başladığı andaki son
Book>Direct girdisi (`lodging_input(before=…)`) ve çekimin günü (26 Kasım UTC, aynı 12 hafta) kullanılır. Her istek ham kopyadaki cevapla
karşılanır:
- yöntem, adres, gönderilen alanlar ve yol (doğrudan/proxy, tarayıcı, eklenti) eşleşir; her cevap bir kez verilir;
- o gece cevabı olmayan istek bağlantı hatasıdır;
- eklentinin izinli sorgu kuralı aynen uygulanır (o gece gönderilmemiş sorgu yine gönderilmez);
- bekleme yapılmaz; doğrulama ve tarayıcı açılmaz.

Eski kopyalarda yönlendirmenin hedefi şöyle bulunur: aynı şirketin aynı türden isteği; bir işçi aralığı (8 sn; iki katı, dört katı) sonra
gelmiş; kendi başına bir ilan bağlantısı değil; başka bir yönlendirmenin hedefi değil. Birden çok aday varsa beklenen gecikmeye en yakın ve
adresin son parçası en çok benzeyen seçilir. Sonuç önce kurtarma dosyasına yazılır ve sayılar çekimin son günlük satırıyla karşılaştırılır.
Kaydetmek ayrı bir düğmedir; sayılar tutmazsa panel uyarır.

## 4. Kurtarma dosyası düzeni

`data/kurtarma/<iş kimliği>/` (programın kendi klasörü; `studio/recovery.py`):

- `sonuc.json` — toplayıcının verdiği sonuç: kayıtlar, toplam ve dışlanan sayısı, kaynak güncellemesi, metadata, ilişkili satırlar
  (şirketler, fiyatlar, kendi evleri, yayımlanmış kiralar…). Tarihler tarih olarak saklanır.
- `durum.json` — iş, kaynak, toplayıcı ve sürümü, ham kopyanın yolu, yazılma zamanı, nasıl oluştuğu (`kaydetme_dustu` ya da
  `yeniden_kurma`), hatanın türü ve metni (yalnız burada; İşler panelinde teknik metin gösterilmez), kayıt sayısı ve kaydedildiyse sürümü
  (`kaydedildi`).
- `yeniden-kurma.json` — yalnız ham kopyadan kurulduysa: cevap, kullanılan ve eksik sayıları ve çekim kaydıyla karşılaştırma.

Akış: kaydetme düşerse (her toplayıcıda; `jobs.py`) sonuç bu klasöre yazılır ve iş "Toplanan sonuç kaydedilemedi… kurtarma dosyasına
yazıldı" der. İşler panelindeki kartta **"Kurtarma dosyası"** ve **"Kurtarılan sonucu kaydet"** görünür. Basınca yeni bir iş ve sürüm
oluşur, ham kopya aynıdır, siteye gidilmez; kart artık **"Kurtarıldı"** der. Sonuç ikinci kez kaydedilmez, dosya silinmez. Ham kopyası
olan düşmüş bir kiralama çekiminin kartı **"Ham kopyadan yeniden kur"** gösterir. Testler: `tests/test_hedef02.py` (kaydetme düşer →
dosya → kaydet; ham kopyadan kur → kaydet → fiyat ve ilan satırları ilk çekimle birebir aynı; hiçbir siteye gidilmez),
`tests/frontend.test.mjs` (kart).

## 5. Kısa toplayıcılar ve mahalle koordinatları kararı

Program kapalıyken yedek alındı (`work/yedek/20261127-1257`); toplayıcılar programın normal kullanımıyla çalıştırıldı:

| Toplayıcı | İş | Sonuç |
|---|---|---|
| Mahalleler (`south-walton-neighborhoods/2`) | `2682b17e…` | 13 kayıt (kaynakta 16; 3'ü kapsam dışı) |
| Plajlar (`south-walton-beaches`) | `0d9d251c…` | 53 erişim (kaynakta 70; 17'si kapsam dışı) |
| Restoran dizini (`south-walton-restaurants/3`, sitenin API'si) | `084bb20e…` | 131 restoran |
| Günlük ihtiyaç (`openstreetmap-daily-needs`) | `8ad3a93c…` | 47 nokta |

**Mahalle koordinatları (yöneticinin kararı):** yeni API koordinat vermiyor. 13 mahallenin enlem/boylamı, aynı kaynağın en son
koordinatlı başarılı kaydından (7 Ekim 2026; eski dizinin kendi harita noktaları; sürüm `3d1cbe8d…`) mahalle adıyla eşleşerek alındı. Öbür
alanlar (tanıtım, sayfa, değişiklik zamanı, etiketler) yeni API'dendir. Kayıtta iki yerde işaretli: çalışmanın `metadata.koordinat_kaynagi`
alanında (kaynak sürüm, tarih, mahalle başına not) ve kayıt okunurken `koordinat_notu` = "koordinat: aynı kaynağın 2026-10-07 kaydından".
Not, Mahalleler ekranında temsilî noktanın altında görünür. Önceki kaydı olmayan bir mahalle için koordinat uydurulmaz; çekim eskisi gibi
durur. Şema değişmedi (`Database.neighborhood_coordinates`, bağlam girdisi `neighborhood_coordinates`; `docs/M7-MAHALLE-VERISI.md`).

## 6. oversee.us kontrolü

27 Kasım 09:44 UTC'de programın kullanıcı aracısıyla **tek doğrudan istek** yapıldı (`https://www.oversee.us/`). Cevap: **HTTP 403**,
`server: cloudflare`, `cf-mitigated: challenge`, başlık "Just a moment..." (Cloudflare doğrulama sayfası). Site doğrudan isteğe hâlâ
kapalı; korumalı site işareti değiştirilmedi. Gece çekiminde oversee.us programın tarayıcısıyla okundu: 182 ilanın 176'sı bağlandı,
1.705 fiyat.

## 7. Kapsam tabloları

Kaynak: gerçek veritabanının hedef sonundaki kopyası (program kapalıyken, salt okunur).

#### 13 mahalle — kiralama (sürüm 7cba8d4c, sorgu günü 2026-11-26)

| Mahalle | Book>Direct ilanı | şirkete bağlanan | en az bir haftası fiyatlı | Oca | Şub | Mar | Nis | May | Haz | Tem | Ağu | Eyl | Eki | Kas | Ara |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Dune Allen | 114 | 50 | 47 | 3.116 $ (29) | 2.971 $ (28) | 3.483 $ (39) | 3.317 $ (33) | 5.344 $ (37) | 5.506 $ (36) | 5.608 $ (36) | 3.875 $ (43) | 3.875 $ (40) | 3.385 $ (34) | 4.163 $ (12) | 3.560 $ (12) |
| Gulf Place | 31 | 12 | 12 | 1.686 $ (10) | 1.873 $ (11) | 3.197 $ (8) | 2.555 $ (10) | 3.546 $ (11) | 4.418 $ (12) | 4.525 $ (12) | 2.917 $ (12) | 2.481 $ (12) | 3.004 $ (12) | 2.324 $ (12) | 2.249 $ (12) |
| Santa Rosa Beach | 246 | 55 | 48 | 2.025 $ (35) | 2.195 $ (28) | 3.173 $ (36) | 2.712 $ (41) | 3.416 $ (39) | 4.778 $ (42) | 4.798 $ (42) | 3.054 $ (44) | 2.744 $ (45) | 3.383 $ (46) | 2.186 $ (45) | 2.162 $ (30) |
| Blue Mountain Beach | 194 | 90 | 69 | 2.268 $ (45) | 2.376 $ (37) | 3.638 $ (52) | 3.135 $ (52) | 3.982 $ (58) | 5.558 $ (63) | 5.694 $ (66) | 3.528 $ (66) | 3.170 $ (65) | 3.714 $ (62) | 2.618 $ (63) | 2.312 $ (61) |
| Grayton Beach | 86 | 23 | 19 | 4.770 $ (12) | 5.808 $ (8) | 4.809 $ (9) | 7.453 $ (14) | 8.216 $ (14) | 9.650 $ (14) | 7.908 $ (13) | 8.602 $ (15) | 6.819 $ (16) | 8.697 $ (16) | 5.746 $ (18) | 6.450 $ (17) |
| WaterColor | 256 | 150 | 145 | 5.529 $ (100) | 5.633 $ (79) | 8.217 $ (88) | 7.174 $ (100) | 8.208 $ (88) | 10.720 $ (106) | 11.258 $ (119) | 7.105 $ (134) | 6.599 $ (117) | 8.359 $ (94) | 5.772 $ (111) | 5.613 $ (120) |
| Seaside | 221 | 134 | 127 | 4.731 $ (78) | 4.934 $ (48) | 7.274 $ (68) | 6.421 $ (79) | 6.186 $ (77) | 7.758 $ (88) | 8.504 $ (97) | 6.163 $ (118) | 5.858 $ (106) | 6.336 $ (90) | 5.992 $ (109) | 5.217 $ (112) |
| Seagrove | 497 | 256 | 250 | 1.711 $ (168) | 2.157 $ (121) | 2.737 $ (178) | 2.407 $ (205) | 3.168 $ (204) | 4.361 $ (228) | 5.096 $ (228) | 2.949 $ (236) | 2.717 $ (232) | 3.635 $ (229) | 1.920 $ (239) | 2.717 $ (102) |
| WaterSound | 165 | 32 | 28 | 5.019 $ (19) | 5.233 $ (18) | 7.029 $ (19) | 6.349 $ (22) | 6.908 $ (19) | 8.427 $ (26) | 8.480 $ (27) | 6.581 $ (27) | 6.160 $ (26) | 6.834 $ (23) | 5.633 $ (26) | 5.742 $ (24) |
| Seacrest | 300 | 87 | 84 | 2.519 $ (68) | 2.909 $ (55) | 4.738 $ (60) | 3.670 $ (67) | 4.188 $ (73) | 6.228 $ (73) | 6.781 $ (68) | 4.195 $ (83) | 3.743 $ (78) | 4.718 $ (80) | 3.004 $ (78) | 2.845 $ (50) |
| Alys Beach | 7 | 0 | 0 | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) | — (0) |
| Rosemary Beach | 166 | 22 | 20 | 3.848 $ (10) | 5.673 $ (15) | 8.340 $ (7) | 8.536 $ (14) | 9.848 $ (16) | 12.602 $ (19) | 13.017 $ (17) | 8.351 $ (20) | 6.786 $ (17) | 9.101 $ (18) | 5.768 $ (19) | 4.973 $ (19) |
| Inlet Beach | 101 | 42 | 40 | 2.712 $ (33) | 2.739 $ (29) | 5.398 $ (29) | 3.766 $ (31) | 3.739 $ (34) | 6.619 $ (37) | 6.757 $ (34) | 4.254 $ (40) | 3.989 $ (38) | 4.420 $ (38) | 3.200 $ (40) | 3.438 $ (34) |

Hücre: o haftanın vergi ve ücretler dahil 7 gecelik toplam ortancası (fiyatlı ilan sayısı). Kaynak: şirketlerin kendi siteleri, 26 Kasım 2026'da sorulan haftalar.

**30A Beach Girls** (ayrı; kendi envanteri, Book>Direct'e bağlanmadı; yalnız kira — toplam yok): 97 ev, 11'i mahalleli (Seacrest 8, WaterSound 2, Rosemary Beach 1), 86 mahallesi belirtilmemiş.

| Ay | Oca | Şub | Mar | Nis | May | Haz | Tem | Ağu | Eyl | Eki | Kas | Ara |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| kira ortancası (ev) | 1.105 $ (74) | 1.470 $ (57) | 2.398 $ (54) | 1.838 $ (74) | 2.354 $ (71) | 3.853 $ (81) | 4.064 $ (88) | 2.205 $ (85) | 2.008 $ (86) | 2.793 $ (84) | 1.538 $ (87) | 1.520 $ (90) |

#### Kiralama şirketleri

| Şirket | Durum | Book>Direct ilanı | bağlanan | fiyatlanan (ilan × hafta) | istek |
|---|---|---:|---:|---:|---:|
| 360 Blue (360blue.com) | done | 256 | 126 | 1083 | 1336 |
| Benchmark Management (benchmark30a.com) | done | 241 | 187 | 1685 | 4368 |
| Oversee (oversee.us) | done | 182 | 176 | 1705 | 2298 |
| 30A Escapes (30aescapes.com) | stopped_errors | 162 | 1 | 0 | 3 |
| Homeowner's Collection (homeownerscollection.com) | done | 143 | 118 | 933 | 2746 |
| Southern Vacation Rentals (southernresorts.com) | done | 104 | 64 | 636 | 946 |
| Ocean Reef Resorts (oceanreefresorts.com) | stopped_errors | 96 | 1 | 0 | 2 |
| Rosemary Beach® (rosemarybeach.com) | stopped_errors | 89 | 1 | 0 | 4 |
| Dune Allen Realty Vacation Rentals (beautifulbeach.com) | done | 88 | 37 | 260 | 584 |
| Panhandle Getaways (panhandlegetaways.com) | stopped_errors | 81 | 1 | 0 | 4 |
| RealJoy Vacations (realjoy.com) | stopped_blocked | 61 | 10 | 100 | 138 |
| Paradise Properties (paradise30a.com) | done | 58 | 32 | 345 | 500 |
| 30A Vacay (30a-vacay.com) | done | 54 | 8 | 78 | 271 |
| Dune Vacation Rentals (dunevacationrentals.com) | done | 49 | 35 | 281 | 787 |
| 30A Beach Girls (30a-beachgirls.com) | done | 48 | 0 | 0 | 242 |
| Grayt 30A Vacations / Royal Destinations (grayt30avacations.com) | done | 41 | 2 | 12 | 130 |
| Sanders Beach Rentals (sandersbeachrentals.com) | done | 38 | 26 | 189 | 586 |
| Vacasa (vacasa.com) | stopped_errors | 35 | 3 | 23 | 67 |
| FunVacay (funvacay.com) | done | 31 | 23 | 221 | 518 |
| Exclusive 30A (exclusive30a.com) | done | 29 | 10 | 95 | 149 |
| Your Friend at the Beach (yourfriendatthebeach.com) | done | 22 | 20 | 0 | 285 |
| 30A Beach Stays (30abeachstays.com) | done | 21 | 17 | 155 | 286 |
| 30A Cottages (30acottagesandconcierge.com) | done | 17 | 14 | 100 | 290 |
| Grayton Coast Rentals (graytoncoastrentals.com) | done | 17 | 11 | 88 | 245 |
| Newman-Dailey Resort Properties (destinvacation.com) | done | 15 | 15 | 141 | 201 |
| My Vacation Haven (myvacationhaven.com) | done | 15 | 7 | 65 | 177 |
| Coastal Blue Vacations (coastalbluevacations.com) | done | 12 | 8 | 60 | 189 |
| Alys Beach Vacation Rentals (alysbeach.com) | stopped_errors | 6 | 0 | 0 | 2 |

Toplam: 2384 ilan; bağlanan 953 (bağlantı 805, adres 140, konum 8); en az bir haftası fiyatlı 889; okuyucusu olmayan alan adı 366, adressiz 7; sorulmayan 440, bulunamayan 450, ilan sayfası olmayan 136, engel 18, hata 14. Fiyatı olan mahalle 12/13.

#### Plaj erişimleri

- Son çekim 0d9d251c: 53 erişim (kaynakta 70 kayıt; 17'si kapsam dışı).
- access_type: neighborhood 44, regional 9
- city: Santa Rosa Beach 44, Inlet Beach 6, Seacrest 2, Grayton Beach 1
- Mahalle eşlemesi: {"available": true, "file": "thirty_a_beach_neighborhoods.csv"}

#### Hava, deniz suyu, kasırga

- NWS hava tahmini: son çekim 2026-10-07, 510 kayıt (tahmin verisi; Ekim'den beri tazelenmedi — bu hedefin izinli listesinde değil).
- normals: sürüm 80f41ce6 (2026-10-07), kayıt 168
- water: sürüm a8cbe865 (2026-10-07), kayıt 182
- storms: sürüm 4f23d0a2 (2026-10-07), kayıt 227

#### Günlük ihtiyaç, yol mesafeleri, havalimanı süreleri

- Günlük ihtiyaç (8ad3a93c, 27 Kasım): convenience 16, big_supermarket 13, pharmacy 5, local_market 4, bike_rental 4, urgent_care 3, emergency 2 — toplam 47.
- Yol ağı (86695396, 27 Kasım 05:44): 19672 yol, 4422.0 km; ilan 2384, bağlanan 2305, ölçülen 2304, hedef 102; girdiler: konaklama 42fa6655, günlük ihtiyaç 080b04f1 (Ekim), plaj 1a195e2b (Ekim). Yol ağı bu hedefte yeniden çalıştırılmadı (izinli listede değil).
- Havalimanı hedefleri: Northwest Florida Beaches Uluslararası Havalimanı (ECP), Destin–Fort Walton Beach Havalimanı (VPS)

#### Uçak bileti

- BTS ortalama bilet (b4a40f70, son çeyrek 2026 Q2): 10 satır (havalimanı × çeyrek). Değer havalimanından BAŞLAYAN yolculukların ortalaması; şehirden şehre fiyat değil.

#### Restoranlar

- Restoran dizini (084bb20e, 27 Kasım, sitenin API'si): 131 restoran; mahalle başına: Santa Rosa Beach 26, Seaside 17, Seagrove 15, Grayton Beach 15, Rosemary Beach 12, Inlet Beach 11, Blue Mountain Beach 8, Gulf Place 6, Alys Beach 6, WaterColor 5, Seacrest 5, WaterSound 3, Dune Allen 2
- Fiyat seviyesi dizinde yok (dizin kaydının alanları: name, listing_url, description, address_line_1, address_line_2, city, state, postal_code, phone, email, website_url, cuisines, meals_served, amenities); restoranların kendi sitelerinden okunur (aşağıda).
- Restoranların kendi siteleri (1f1155b1, 2026-10-09; bu hedefte çalıştırılmadı): hours 91 restoran, kids_menu 51 restoran, review_note 46 restoran, reservation 46 restoran, outdoor_seating 32 restoran, water_view 29 restoran, site_price_range 25 restoran, dog_friendly 3 restoran (dizinin 138 restoranından)

#### Plaj kuralları

- Referans tablosunda plaj kuralı satırları: 40: kural-kapsam; kural-hayvan-yasagi; kural-kopek-izin-saat; kural-cam; kural-cadir-olcu; kural-cadir-yer; kural-semsiye-olcu; kural-15-ft; kural-gece-esya; kural-gece-esya-terk; kural-ates-izin; kural-ates-mesafe; kural-ates-saat-mart-ekim; kural-ates-saat-kasim-subat; kural-izgara; kural-havai-fisek; kural-gece-kamp; kural-cukur; kural-metal-kurek; kural-kapatma-emri

**Kalite ekranı** (Sol menü → Veri → Kalite → "Kayıtları kontrol et", 27 Kasım 13:07): 17 kaynak. Bunların 4'ünde "Veri toplama yöntemi
belirlenmemiş" yazıyor: 30A · Bölge rehberi, South Walton · Etkinlikler, South Walton · Ulaşım, Visit South Walton. Bunlar toplayıcısı
henüz olmayan, katalogda ileride bağlanmak üzere duran kaynak kayıtlarıdır (Ekim'den beri aynı); veri hatası değildir. Başka bulgu yok.

**Kapsamda dikkat edilecekler:**
- **Alys Beach:** 7 ilan; hiçbiri fiyatlanmadı. alysbeach.com gece eklenti tarafında okunamadı ("Siteye art arda 5 kez ulaşılamadı").
- **Eklentiyle okunan dört Track sitesi** (30A Escapes, Ocean Reef Resorts, Rosemary Beach®, Panhandle Getaways): sayfa açıldı, ama fiyat
  sorusu (`POST /ajax/quote`) programın izinli sorgu listesinde yalnız RealJoy için var. Eklenti soruyu göndermedi ("Sorgu
  gönderilmedi…"); 5 hatadan sonra şirket durdu. Listeyi genişletmek "sayfanın kendi sorgusu" kuralının kapsamını değiştirir; karar
  yöneticinin (açık kalan).
- **RealJoy:** 10 ev fiyatlandı (100 fiyat, 18 hafta takvimden dolu); sonra sitenin doğrulama sayfası ikinci kez çıktı ve şirket durdu.
- **Your Friend at the Beach:** 20 ilan bağlandı; fiyat servisi "You are not authorized to use this service" dedi (240 cevap fiyatsız).
- **Vacasa:** 3 ilan bağlandı; fiyat cevaplarından 5'inde kira ya da toplam yok; art arda hatalarla durdu.
- **Grayton Beach, Rosemary Beach, Gulf Place:** fiyatlı ilan sayısı 20'nin altında (küçük örnek).
- **Bu hedefte tazelenmeyenler:** hava tahmini, iklim, deniz suyu, kasırga, restoranların kendi siteleri ve uçak bileti (izinli listede
  yalnız dört kısa toplayıcı vardı). Sürümleri ve tarihleri yukarıda. Yol ağı 27 Kasım 05:44'te (gece) çalıştı, ama günlük ihtiyaç ve plaj
  girdileri Ekim sürümleridir; bugünkü yeni sürümlerle yeniden ölçülmedi.

## 8. Başlık değerlendirmesi (tek gerçek Claude çalışması)

Sol menü → Konu bankası → Kendi başlığını değerlendir; bölge "30A geneli"; başlık
`First Time on 30A? Which Town, Which Month and What a Week Costs | 30A Florida Vacation`. Çalışma `31bab2a3…` (iş `422ee82c…`), Opus 5.5,
efor Yüksek, 1 çağrı, 160 sn. Veri özeti o anda yeni üretilen paketten geldi (`95889c92…`; kurtarılan kiralama sürümü dahil).

| | okunan | yazılan | toplam |
|---|---:|---:|---:|
| Tahmin (ekranda, başlamadan önce) | 102.998 | 7.618 | 110.616 |
| Gerçek | 103.328 | 19.287 | 122.615 (0,80 $) |

Gerçek harcama, hedefteki ~118 bin tahminine yakın; ekrandaki tahminden 12 bin fazla (yazılan kısım tahminden uzun çıktı; tek çağrı sınırı
250 bin).

**Türkçe özet:**
- **Fikir veriyle doluyor.** "Hangi kasaba" sorusunu 13 mahallenin ilan sayıları, restoran sayıları ve plaj erişimi eşlemesi karşılıyor.
  "Hangi ay" sorusunu iklim normalleri, deniz suyu, kasırga sayımları, turist vergisinin aylık payı, doluluk ve okul tatilleri karşılıyor.
  "Bir hafta ne tutar" sorusunu 13 mahallede 12 ayın kiralama toplam ortancaları karşılıyor.
- **Sorunlar:** başlık, 10 Ekim'de önerilen "30A Florida for First-Timers: Which Town, Which Month and What a Week Costs" başlığıyla
  neredeyse aynı; iki benzer başlık izleyiciyi karıştırır. Üç soru bir içerik listesi gibi duruyor. "What a Week Costs" tek bir rakam vaadi
  veriyor; kanıt ise ortanca, ilan sayısı ve çeyreklerle söylenebilir, Alys Beach'te de hiç fiyat yok. "30A" başlıkta iki kez geçiyor.
- **Üç aday** (Claude'un sırasıyla):
  1. "30A bir kasaba değil: ilk kez gidenlerin rezervasyondan önce bilmesi gerekenler" — en çok önerilen. Kanca: 30A 18,6 millik bir ilçe
     yolu; 13 mahallenin beşinde ilçenin halka açık plaj erişimi yok.
  2. "30A'da ilk kez mi? Bir kasaba seçmeden önce bilmeniz gerekenler" — kullanıcının açılışını koruyor. Kanca: temmuz haftası Seagrove'da
     ~5.096 $, WaterColor'da ~11.258 $.
  3. "İlk 30A gezinizi mi planlıyorsunuz? Nerede kalınır, ne zaman gidilir ve ne tutar" — üç soruyu koruyor. Kanca: turist vergisinin
     %20'si temmuzda, %2,1'i ocakta toplanıyor.
- **Eksik veri:** Alys Beach'te fiyat yok; üç mahallede küçük örnek; Vrbo ve fiyatı okunamayan şirketler ortancada yok; araç kiralama ve
  market fiyatı kapsam dışı; trafikli sürüş ve yürüme süresi yok; şehirden şehre bilet fiyatı yok.

## 9. Videonun durumu ve tahminler

- **Video** `7b025758cdd3435f9f0b6a56f9a54fac` bu değerlendirmeden açıldı ("Bu başlıkla video aç"). Başlık **yöneticinin metni** olarak
  girildi: EN "First Time on 30A? Which Town, Which Month and What a Week Costs | 30A Florida Vacation", TR "30A'ya ilk kez mi
  gidiyorsunuz? Hangi kasaba, hangi ay ve bir hafta ne tutar | 30A Florida Tatili". Analiz (izleyici sorusu, kanca, içerik planı) aynı üç
  soruyu soran 3. adaydan alındı. Claude'un önerdiği yeni başlıklardan birini ben seçmedim; başlığı Mucahit seçer. Mucahit isterse 1 ·
  Başlık ve vaat adımında "Reddet" deyip Konu bankası'ndan başka bir adayı kullanabilir.
- **1 · Başlık ve vaat:** onaylandı; not "Yönetici önerisi; Mucahit değiştirebilir".
- **2 · Veri paketi:** tamamlandı. Paket `9f9d489c…` (`data/evidence/20261127-100417-video-plani-9f9d489c.md`): 6 bölüm, 840 kanıt,
  1.901 sayı, 27 eksik satır; yazar özeti ve sayılar ekli.
- **3 · Plan:** "hazır"da; çalıştırılmadı.

**Tahminler.** Ekrandaki tahmin düzeniyle hesaplandı. 4 · Yazım'ın kendi tahminini program ancak plan onaylanınca gösteriyor (şimdi 409
"Plan onaylanmadan yazım başlamaz" diyor). Bu yüzden 4'ün satırları, planı henüz yapılmamış zincirin tahmininden (veritabanı kopyasında,
Araştırmacı dost ve Vlogger tonlarıyla) alındı. Plan satırı, programın 3 · Plan ekranındaki tahminle aynı.

| Kısım | Çağrı | Okunan | Yazılan | Toplam |
|---|---:|---:|---:|---:|
| Plan | 2 | 243.671 | 26.000 | 269.671 |
| Araştırmacı dost | 10 | 312.128 | 82.000 | 394.128 |
| Vlogger | 10 | 312.078 | 82.000 | 394.078 |
| **Toplam** | 22 | 867.877 | 190.000 | 1.057.877 |

Plan: 2 çağrı, yaklaşık 270 bin token · Araştırmacı dost: 10 çağrı, yaklaşık 394 bin token · Vlogger: 10 çağrı, yaklaşık 394 bin token · Toplam: yaklaşık 1,1 milyon token

## 10. Açık kalanlar

1. **Eklentiyle okunan dört Track sitesinin fiyat sorusu** (30A Escapes, Ocean Reef Resorts, Rosemary Beach®, Panhandle Getaways):
   `POST /ajax/quote` izinli sorgu listesinde yok; bu şirketlerden fiyat gelmiyor. Listeyi genişletmek kural kapsamı kararıdır (yönetici).
2. **Alys Beach** eklentide açılamadı (7 ilan, fiyat yok). **Your Friend at the Beach**'in fiyat servisi yetki hatası veriyor. **Vacasa**
   cevaplarında kira/toplam eksik. **RealJoy** ikinci doğrulama sayfasında durdu.
3. **Yol ağı** Ekim'in günlük ihtiyaç ve plaj sürümleriyle ölçülü; bugünkü sürümlerle yeniden çalıştırılmadı (izinli listede değildi).
   Hava tahmini, iklim, deniz suyu, kasırga, restoran siteleri ve uçak bileti Ekim/Kasım ortası sürümleridir.
4. **Kalite ekranındaki 4 katalog kaydı** toplayıcısız (bilinen; ileride bağlanacak).
5. **Videonun başlığı** Mucahit'in onayını bekliyor (yönetici önerisiyle onaylandı). 3 · Plan ve 4 · Yazım bu hedefin dışında.
6. `test_text_chain::test_a_run_cut_by_the_app_closing_is_yarida_kaldi_and_devam_goes_on` tam turda bir kez zamanlama yüzünden düştü, tek
   başına geçti (önceden bilinen bir yarış).

## 11. Yedekler

- `work/yedek/20261127-1205/` — hedef başında, program kapalıyken (65.453 dosya, 2.666.340.235 bayt; kaynakla aynı). Program gece
  çekiminden beri açıktı; yedekten önce kapatıldı.
- `work/yedek/20261127-1257/` — kurtarmadan sonra, kısa toplayıcılardan önce (65.456 dosya, 2.694.730.175 bayt).
- Şema değişmedi; programın göç yedeği yok. Satır sayıları (kısa toplayıcılardan önce → sonra): beach_records 212 → 265,
  neighborhood_records 13 → 26, poi_points 91 → 138, restaurant_records 552 → 683, videos 0 → 1, video_steps 0 → 8, evidence_packs 8 → 10,
  claude_runs 4 → 5. Eksilen tablo yok; `foreign_key_check` 0.
- Kurtarma dosyası: `data/kurtarma/b8055d2a0419492cacf45717ef487ff1/` (durum "kaydedildi").

## 12. Testler ve CI

- Yeni testler: `tests/test_hedef02.py` (12): gerçek RealJoy sayfasıyla hata ve düzeltme, eski değerin eşlenmesi, değer denetimi, okuyucu
  sabitleri, kurtarma dosyası → kaydet (panelin ilk açılışı dahil; teknik metin panelde yok), tarihlerin korunması, ham kopyadan kur →
  kaydet → ilk çekimle aynı satırlar, yönlendirme hedefinin saklanması ve eski kopyada çıkarılması, cevabın bir kez verilmesi, günlük
  satırının sayıları, denemenin kaydetme sınaması (geçer/düşer). Ayrıca `tests/test_neighborhoods.py` (koordinat kararı),
  `tests/frontend.test.mjs` (kurtarma kartı, kaydetme sınaması satırı). GÖREV-25'in `takvim` beklentisi `sayfa` oldu; sürüm testi 0.28.0.
- Bulunan ve düzeltilen: kurtarma kartı İşler panelinin ilk çizimine ve canlı akışına (`/api/events`) girmiyordu; teknik hata metni
  kartta görünüyordu (iç kayıtta kalmalı; mevcut bir test yakaladı); dar panelde karşılaştırma tablosu taşıyordu (ekran görüntüsüyle
  doğrulandı).

- Yerel tam takım (son kod): `.venv\Scripts\python.exe -m pytest -q` → **1286 geçti, 3 atlandı, 1 düştü**; düşen
  `test_claude_steps::test_previous_proposals_are_given_and_a_repeated_title_is_refused` ("Bir Claude çalışması zaten sürüyor", önceki
  sahte çalışmanın bitişiyle yarış) tek başına geçti; bir önceki tam turda geçmişti. `node --test tests/frontend.test.mjs` → **143/143**.
- GitHub CI: 45980849507 (`c45be1e`, kod ve rapor) **başarılı**. Son commit yalnız bu satırı ekler; onun CI sonucu da main'e almadan önce beklendi (başarılı olmasa main'e alınmazdı).

## 13. Uyulan kurallar

- Uzun kiralama çekimi başlatılmadı; kurtarma sitelere gitmeden yapıldı. Canlı istek: oversee.us'a tek istek. Kısa toplayıcılar programın
  normal kullanımıyla çalıştı.
- Gerçek Claude yalnız bir kez çalıştı (başlık değerlendirmesi). Plan ve yazım çalıştırılmadı.
- `data/` içinde elle dosya değiştirilmedi; her değişiklikten önce program kapalıyken tam yedek alındı. Kullanıcı verisi silinmedi.
- Proxy bilgisi hiçbir yere yazılmadı. Talimat dosyalarına ve öbür depolara dokunulmadı; dal açılışında talimat klasöründe kullanıcı
  değişikliği yoktu. Zamanlanmış görev oluşturulmadı, Windows ayarı değişmedi. Alt ajan kullanılmadı.
