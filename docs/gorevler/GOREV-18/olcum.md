# GÖREV-18 ölçüm tabloları

Gerçek verinin geçici kopyasında (`work/gorev-18/temp-olcum`, 11 Kasım 2026), Claude çağrılmadan; programın kendi tahmin yoluyla. Token
tahmini: karakter ÷ 1,85 (tek gerçek çağrıdan ölçüldü) + Claude Code'un kendi sistem metni için 4.500. Yazılan: adımın önceki çalışmalarının
ortancası, yoksa Ayarlar'daki çıktı varsayımı. Bu tablolarda Claude Code'un yan çağrısı (aşağıda) yoktur.

## 1. Başlık adımları: eski düzen (ölçülen) ve yeni düzen (tahmin)

| Çalışma | Eski: tur · araç | Eski: okunan | Eski: yazılan | Eski: bedel | Yeni: çağrı | Yeni: okunan | Yeni: yazılan | Yeni: toplam |
|---|---|---|---|---|---|---|---|---|
| Konu ve başlık · 30A geneli | 5 · 9 | 371 bin | 65 bin | 2,55 $ | 1 | 92 bin | 54 bin | 147 bin |
| Konu ve başlık · Rosemary Beach | 5.5 · 10 | 452 bin | 54 bin | 2,39 $ | 1 | 108 bin | 54 bin | 163 bin |
| Başlık değerlendirme · köpek fikri | 6 · 13 | 416 bin | 8 bin | 1,18 $ | 1 | 110 bin | 8 bin | 118 bin |

Eski düzendeki okunan, ilk istemle malzemenin toplamının ortalama 3,99 katıydı (aynı malzeme her turda yeniden okunuyordu). Yazılan değişmez: aynı JSON ve düşünme.

## 2. Başlık adımlarının istem parçaları

### Konu ve başlık · 30A geneli

| Parça | Karakter | Tahmini token |
|---|---|---|
| talimat.md | 8.819 | 4.768 |
| görev metni (önsöz ve adımın satırları) | 1.989 | 1.076 |
| kanal_plani.md | 13.853 | 7.489 |
| kanal_arastirmasi.md | 13.434 | 7.262 |
| secim.md | 291 | 158 |
| veri_ozeti_30a.md | 113.557 | 61.383 |
| sablonlar.md | 3.276 | 1.771 |
| onceki_oneriler.md | 6.930 | 3.746 |
| Claude Code'un kendi sistem metni (ölçülen, yaklaşık) | — | 4.500 |

### Konu ve başlık · Rosemary Beach

| Parça | Karakter | Tahmini token |
|---|---|---|
| talimat.md | 8.850 | 4.784 |
| görev metni (önsöz ve adımın satırları) | 2.121 | 1.147 |
| kanal_plani.md | 13.853 | 7.489 |
| kanal_arastirmasi.md | 13.434 | 7.262 |
| secim.md | 342 | 185 |
| veri_ozeti_30a.md | 113.557 | 61.383 |
| veri_ozeti_mahalle.md | 28.913 | 15.629 |
| sablonlar.md | 3.276 | 1.771 |
| onceki_oneriler.md | 6.930 | 3.746 |
| Claude Code'un kendi sistem metni (ölçülen, yaklaşık) | — | 4.500 |

### Başlık değerlendirme · köpek fikri

| Parça | Karakter | Tahmini token |
|---|---|---|
| talimat.md | 7.646 | 4.133 |
| görev metni (önsöz ve adımın satırları) | 2.804 | 1.516 |
| kanal_plani.md | 13.853 | 7.489 |
| kanal_arastirmasi.md | 13.434 | 7.262 |
| secim.md | 342 | 185 |
| veri_ozeti_30a.md | 113.557 | 61.383 |
| veri_ozeti_mahalle.md | 28.913 | 15.629 |
| sablonlar.md | 3.276 | 1.771 |
| onceki_oneriler.md | 6.930 | 3.746 |
| kullanici_basligi.md | 282 | 153 |
| baslik_olculeri.md | 3.569 | 1.930 |
| Claude Code'un kendi sistem metni (ölçülen, yaklaşık) | — | 4.500 |

## 3. Talimat parçaları (her adım; ses ve ton ilk tonla)

| Adım | Parça | Karakter | Tahmini token |
|---|---|---|---|
| Konu ve başlık | ortak.md | 1.476 | 798 |
| Konu ve başlık | baslik.md | 3.569 | 1.930 |
| Konu ve başlık | şema baslik.schema.json | 2.672 | 1.445 |
| Başlık değerlendirme | ortak.md | 1.476 | 798 |
| Başlık değerlendirme | baslik_degerlendirme.md | 1.680 | 909 |
| Başlık değerlendirme | şema baslik_degerlendirme.schema.json | 4.598 | 2.486 |
| Video metni · plan | ortak.md | 1.476 | 798 |
| Video metni · plan | metin_plan.md | 1.687 | 912 |
| Video metni · plan | şema metin_plan.schema.json | 3.197 | 1.729 |
| Video metni · plan eleştirisi | ortak.md | 1.476 | 798 |
| Video metni · plan eleştirisi | metin_plan_elestiri.md | 947 | 512 |
| Video metni · plan eleştirisi | şema metin_plan_elestiri.schema.json | 533 | 289 |
| Video metni · bölüm | ortak.md | 1.476 | 798 |
| Video metni · bölüm | ses_ortak.md | 1.087 | 588 |
| Video metni · bölüm | ton: arastirmaci_dost.md | 520 | 282 |
| Video metni · bölüm | metin_bolum.md | 980 | 530 |
| Video metni · bölüm | şema metin_bolum.schema.json | 718 | 389 |
| Video metni · birleştirme | ortak.md | 1.476 | 798 |
| Video metni · birleştirme | ses_ortak.md | 1.087 | 588 |
| Video metni · birleştirme | ton: arastirmaci_dost.md | 520 | 282 |
| Video metni · birleştirme | metin_birlestirme.md | 823 | 445 |
| Video metni · birleştirme | şema metin_birlestirme.schema.json | 1.424 | 770 |
| Video metni · giriş ve kapanış | ortak.md | 1.476 | 798 |
| Video metni · giriş ve kapanış | ses_ortak.md | 1.087 | 588 |
| Video metni · giriş ve kapanış | ton: arastirmaci_dost.md | 520 | 282 |
| Video metni · giriş ve kapanış | metin_giris_kapanis.md | 909 | 492 |
| Video metni · giriş ve kapanış | şema metin_giris_kapanis.schema.json | 720 | 390 |
| Video metni · son okuma | ortak.md | 1.476 | 798 |
| Video metni · son okuma | ses_ortak.md | 1.087 | 588 |
| Video metni · son okuma | ton: arastirmaci_dost.md | 520 | 282 |
| Video metni · son okuma | metin_son_okuma.md | 920 | 498 |
| Video metni · son okuma | şema metin_son_okuma.schema.json | 857 | 464 |
| Video metni · çeviri | ortak.md | 1.476 | 798 |
| Video metni · çeviri | ses_ortak.md | 1.087 | 588 |
| Video metni · çeviri | ton: arastirmaci_dost.md | 520 | 282 |
| Video metni · çeviri | metin_ceviri.md | 1.051 | 569 |
| Video metni · çeviri | şema metin_ceviri.schema.json | 1.288 | 697 |

## 4. Video metni (kopyada seçilen başlık: “Rosemary Beach for Couples: Is It the Right Town for Two? | 30A Florida Vacation”)

Gerçek veride video kaydı yok; ölçüm için kopyada bir Rosemary Beach başlık adayı seçildi ve paketi kuruldu (yalnız kopyada).

### Planlayıcının girdileri (tam ölçüm)

| Dosya | Karakter | Tahmini token |
|---|---|---|
| baslik_analizi.md | 3.354 | 1.813 |
| paket_ozeti.md | 38.502 | 20.812 |
| sayilar.csv | 7.164 | 3.873 |
| kanal_plani.md | 13.853 | 7.489 |

### Bir ton: tahmin

> Plan: 2 çağrı, yaklaşık 107 bin token · Araştırmacı dost: 10 çağrı, yaklaşık 274 bin token · Toplam: yaklaşık 381 bin token

| Kısım | Çağrı | Okunan | Yazılan | Toplam | En büyük çağrı |
|---|---|---|---|---|---|
| Plan | 2 | 81 bin | 26 bin | 107 bin | 63 bin |
| Araştırmacı dost | 10 | 192 bin | 82 bin | 274 bin | 43 bin |
| **Toplam** | 12 | 273 bin | 108 bin | **381 bin** | |

Eski düzende (hesap: okunan × 3,99): yaklaşık 1.089 bin okunan + 108 bin yazılan = 1.197 bin.

Adım adım (bir tonun çağrıları):

| Adım | Okunan | Yazılan | Dayanak |
|---|---|---|---|
| Video metni · plan | 43 bin | 20 bin | okunan: istemin boyutu; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · plan eleştirisi | 38 bin | 6 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · bölüm | 19 bin | 8 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · birleştirme | 17 bin | 6 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · giriş ve kapanış | 14 bin | 6 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · son okuma | 33 bin | 10 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · çeviri | 13 bin | 12 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |

### İki ton: tahmin

> Plan: 2 çağrı, yaklaşık 107 bin token · Araştırmacı dost: 10 çağrı, yaklaşık 274 bin token · Belgesel anlatıcı: 10 çağrı, yaklaşık 274 bin token · Toplam: yaklaşık 655 bin token

| Kısım | Çağrı | Okunan | Yazılan | Toplam | En büyük çağrı |
|---|---|---|---|---|---|
| Plan | 2 | 81 bin | 26 bin | 107 bin | 63 bin |
| Araştırmacı dost | 10 | 192 bin | 82 bin | 274 bin | 43 bin |
| Belgesel anlatıcı | 10 | 192 bin | 82 bin | 274 bin | 43 bin |
| **Toplam** | 22 | 465 bin | 190 bin | **655 bin** | |

Eski düzende (hesap: okunan × 3,99): yaklaşık 1.855 bin okunan + 190 bin yazılan = 2.045 bin.

Adım adım (bir tonun çağrıları):

| Adım | Okunan | Yazılan | Dayanak |
|---|---|---|---|
| Video metni · plan | 43 bin | 20 bin | okunan: istemin boyutu; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · plan eleştirisi | 38 bin | 6 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · bölüm | 19 bin | 8 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · birleştirme | 17 bin | 6 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · giriş ve kapanış | 14 bin | 6 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · son okuma | 33 bin | 10 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |
| Video metni · çeviri | 13 bin | 12 bin | okunan: istemin bilinen kısmı ve boyut tahmini; yazılan: önceki çalışma yok; Ayarlar'daki çıktı varsayımı |

## 5. Claude Code'un yan çağrısı

Tek gerçek çağrıda (değerlendirme) Claude Code, Opus 5.5'in yanında kendi kendine bir Haiku 5.5 çağrısı yaptı ve görev metninin tamamını
bir kez daha okudu: 105.311 token okudu, 24 yazdı, 0,053 $ (çağrının bedelinin %5'i). Program GÖREV-18'in son hâlinde bunu gerçek harcamaya
sayar ve sonraki tahminlere önceki tek çağrıların oranını (bu ölçümde okunanın %95'i) ekler. Yukarıdaki tahminlerde bu pay yoktur: gerçek veride
henüz tek çağrılı çalışma olmadığı için oran 0'dır; ilk gerçek çalışmadan sonra tahminler buna göre büyür (başlık önerisi yaklaşık 90 bin daha,
iki tonlu metin yaklaşık 430 bin daha okunan). Bunun kapatılıp kapatılamayacağı yöneticinin karar konusudur (RAPOR).
