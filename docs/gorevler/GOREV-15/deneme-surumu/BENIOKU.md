# Deneme sürümü — sahte claude çıktısı

Bu klasördeki dosyalar gerçek bir video metni değildir. GÖREV-15'in geçici klasör denemesinde (gerçek verinin kopyası) testlerin
sahte claude programıyla (`tests/fake_claude.py`, `tests/fake_claude_text.py`) yazıldı. Gerçek Claude çağrılmadı.

- Video: Rosemary Beach çalışmasının (0d773a0c) ilk adayı, "Rosemary Beach for Couples: Is It the Right Town for Two? | 30A Florida
  Vacation" (yalnız geçici klasörde; gerçek veride video kaydı yok).
- Sürüm: 3. sürüm, ton "Araştırmacı dost" (ikinci çalışma, "Planı yeniden yap" ile açılan).
- Cümleler sahte claude'un tekrar eden dolgu metnidir; kanıt kimlikleri video paketinin gerçek kimlikleridir.
- Denetimdeki kırmızı ("walking distance") ve sarı ("amazing") bulgular, denetimin çalıştığı görülsün diye sahte claude'un metne koyduğu
  ifadelerdendir. Türkçe metin sahte çevirmenin "TR:" önekli kopyasıdır.

Dosyalar:
- `metin_EN.md` — İngilizce metin
- `metin_TR.md` — Türkçe metin
- `seslendirme_EN.txt` — seslendirme için düz İngilizce
- `metin_EN_kanitli.md` — numaralı cümleler ve kanıt kimlikleri
- `denetim.md` — program denetiminin raporu
