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
