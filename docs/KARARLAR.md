# Teknik kararlar

Tarihli teknik kararlar; en yenisi en altta.

## 27 Kasım 2026 — HEDEF-04 A-5: 3 · Plan tahmini eleştirmenin geri gönderme turunu da sayar

- Gözlem: gerçek videoda (7b025758…) 3 · Plan'ın tahmini 2 çağrı / 272 bin token idi; plan eleştirmeni planı bir kez geri gönderdi (`plan_turu` 2), planlayıcı iki kez çalıştı ve gerçek harcama 3 çağrı / 466 bin token oldu. Tahmin yalnız ilk planlayıcı turunu ve eleştirmeni sayıyordu.
- Karar (ana oturum): plan tahmini eleştirmenin geri gönderebileceği turu da sayar: planlayıcı + eleştirmen + eleştirmen geri gönderirse ikinci planlayıcı turu (ilk turun istemi ve önceki plan). Plan satırı `en_cok: true` taşır; ekranda "Plan: en çok 3 çağrı, en çok yaklaşık … token" yazar; sınır denetimi ve tahmin–gerçek karşılaştırması bu en çok değerle yapılır. Halka tablosunda Planlayıcı'nın tahmini çağrısı 2'dir.
- Kapsam dışı: programın kimlik denetiminin (pakette olmayan kanıt kimliği) planı bir kez geri göndermesi tahmine eklenmedi; bu hata yoludur ve olağan akış değildir.
- Kod: `studio/text/estimate.py` (`estimate`), `studio/ai/budget.py` (`summary` metni). Testler: `tests/test_gorev18.py`, `tests/test_gorev21.py`.

## 27.11.2026 — 6 · Yayın paketi (HEDEF-04 A-6)

- Adım, başlık adımlarının Claude düzenini (`ClaudeService`: tek çağrı, istemde malzeme, tahmin önce, tek çağrı/iş sınırı) kullanır; video adımı `params.video_adimi = "yayin"` ile bağlanır. Ayrı bir servis yazılmadı.
- Bölüm zamanlarını Claude hesaplamaz: program her paragrafın tahmini başlangıcını (dakikada 150 kelime, `text/views.py` ile aynı) istemde `[~mm:ss]` olarak verir, Claude bunlardan seçer, program denetler. Zamanlar "tahmini"dir; 7 · Seslendirme gelince kesinleşecek.
- Denetimden geçmeyen paket (00:00, ≥3 bölüm, ≥10 sn, artan sıra) onaylanamaz; sorun ekranda yazar, "Düzeltme iste" ile yeniden yazdırılır.
- Ton seçimi yeniden onaylanınca onaylı yayın paketi eskir ("Ton seçimi değişti.").
## 28.11.2026 — HEDEF-04 A-7: 7 · Seslendirme ElevenLabs'a bağlı değil

Ses programın dışında üretilir: program onaylı metni sese uygun düz İngilizce parçalara yazar (≤ 4.500 karakter, cümle bölünmez),
kullanıcı sesi mp3/wav olarak yükler (tek dosya ya da numaralı parçalar), eşleştirme Kurgu Motoru'nun kendi hizalama işçisiyle yapılır
(yolu ayarda; motor yoksa açık hata). Adımda onay yok; eşleşince tamamlanır. Ses ve metin dosyaları videonun klasöründe kalır, silinmez.
## 28.11.2026 — HEDEF-04 A-8: 8 · Kurgu paketi deterministik, 6'ya bağlı, kurguyu motor yapar

- Paket (`kurgu-paket/1`) Claude çağrısı olmadan onaylı metinden, onaylı metnin kanıt paketinden ve 7 · Seslendirme'nin sonucundan kurulur.
  Cümle kimliği `c<cümle no>` (yeniden kurulunca aynı kalır); kanıt satırı = veri kaydı (`id` K-kimliği, `kind` blok); kaynaklı rakam
  `value` + `ref` (`K….deger` / çeyrekler); yer adları destinasyonun bölge adları ve kaynakların kapsamı.
- 8 · Kurgu paketi 7'yi beklemez: 6 · Yayın paketi onaylanınca hazırdır. Ses yoksa paket sessiz kurulur, zamanlar boş kalır; ses eşleşip
  bütün cümleler zaman alınca `audio/zamanlar.json` girer ve motor yeniden hizalamaz; bir kısmı eşleşmediyse yalnız ses dosyası girer
  (motor kendi hizalar). Birden çok ses parçası ffmpeg ile tek wav'a birleştirilir.
- `scenes.json` yalnız kart önerisidir (ilk kaynaklı rakam → `rakam-karti`, ilk yer adı → `alt-bant`, açılış → `baslik-karti`); süreler
  yalnız zamanlar varken verilir. Hiçbir yerde ses efekti istenmez; kart/geçiş sesleri motorun kanal profilindedir (kopyada `_ornek`
  sessizleştirildi; 30A kanal profili motor deposunun işi).
- Motorun klasörü, pnpm ve motordaki kanal kimliği program ayarıdır: Ayarlar → Kurgu Motoru (motor klasörü 7'nin ayarıyla aynı değer).
- "Kurguya gönder" paketi `<motor>/cache/30a-paketler/<video>-NNN/`'ye kopyalar, `pnpm -s kurgu paket dogrula` geçerse `paket ice-al`
  (ikinci kez `--guncelle projects/<proje>`) çalıştırır; proje kimliği çıktıdaki "Proje: … →" satırından okunur. Render motorda yapılır.
- Zamanlar varken kartlar sesi 0'dan sonuna kadar kaplar (motor görüntüsüz kareyi render'da durdurur): kartı olmayan bir cümlede önceki kart
  12 sn'yi aşacaksa bölüm adıyla ara başlık kartı girer; kart en az 3 sn, en çok 12 sn (motorun kart sınırları); uzun bir cümlede kart yalnız
  o cümlenin içinde sürer. V1'e stok görüntü motorda konunca bu kartlar yalnız katman olur.
- 7 · Seslendirme'nin hizalama işçisi motorun kendi model önbelleğini (`config/tools.json` → `cacheRoots.hf/torch`) kullanır; yoksa modeli
  motor klasörüne yeniden indirmeye çalışıyor ve Windows sembolik bağ izni yüzünden düşüyordu (HEDEF-04 A-8 denemesinde bulundu).
