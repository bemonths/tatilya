# Teknik kararlar

Tarihli teknik kararlar; en yenisi en altta.

## 27 Kasım 2026 — HEDEF-04 A-5: 3 · Plan tahmini eleştirmenin geri gönderme turunu da sayar

- Gözlem: gerçek videoda (7b025758…) 3 · Plan'ın tahmini 2 çağrı / 272 bin token idi; plan eleştirmeni planı bir kez geri gönderdi (`plan_turu` 2), planlayıcı iki kez çalıştı ve gerçek harcama 3 çağrı / 466 bin token oldu. Tahmin yalnız ilk planlayıcı turunu ve eleştirmeni sayıyordu.
- Karar (ana oturum): plan tahmini eleştirmenin geri gönderebileceği turu da sayar: planlayıcı + eleştirmen + eleştirmen geri gönderirse ikinci planlayıcı turu (ilk turun istemi ve önceki plan). Plan satırı `en_cok: true` taşır; ekranda "Plan: en çok 3 çağrı, en çok yaklaşık … token" yazar; sınır denetimi ve tahmin–gerçek karşılaştırması bu en çok değerle yapılır. Halka tablosunda Planlayıcı'nın tahmini çağrısı 2'dir.
- Kapsam dışı: programın kimlik denetiminin (pakette olmayan kanıt kimliği) planı bir kez geri göndermesi tahmine eklenmedi; bu hata yoludur ve olağan akış değildir.
- Kod: `studio/text/estimate.py` (`estimate`), `studio/ai/budget.py` (`summary` metni). Testler: `tests/test_gorev18.py`, `tests/test_gorev21.py`.
