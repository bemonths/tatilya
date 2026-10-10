Adım: baslik
Tür: ilk çalışma
Bölge: Rosemary Beach
İçerik ailesi: hepsi
Not: yok

Görev: kanalın bir sonraki videosu için konu ve başlık önerileri hazırla (sistem metnindeki "Konu ve başlık önerisi").

Çalışma klasöründeki dosyalar (hepsini oku):
- `secim.md` — kullanıcının bu çalışma için seçtiği bölge, içerik ailesi ve notu.
- `kanal_plani.md` — kanal planı: içerik aileleri, konu motoru, ilkeler.
- `kanal_arastirmasi.md` — kanal araştırması: rakip videolar, izleyicinin soruları.
- `veri_ozeti_30a.md` — 30A verisinin yazar özeti (paket 3a8b1fc1).
- `veri_ozeti_mahalle.md` — Rosemary Beach mahallesinin yazar özeti (paket 0deda1fc).
- `sablonlar.md` — programın paket kurabildiği şablonlar.
- `onceki_oneriler.md` — daha önce önerilen başlıklar.

Çıktı:
- `baslik.json` — şema: sistem talimatının sonundaki "Çıktı şeması" bölümü. Okunur Markdown'ı program üretir; sen Markdown yazma.

Kurallar:
- Yalnız bu klasördeki dosyaları oku; yalnız `baslik.json`'u yaz. Başka hiçbir dosyayı oluşturma ya da değiştirme.
- 8–12 aday yaz.
- Bütün adaylar Rosemary Beach hakkında olur; her adayın `bolge` alanı "Rosemary Beach" olur.
- `aile` alanına kanal planındaki içerik ailesinin adını şemadaki listede yazıldığı gibi yaz.
- Her kanıt `{"dosya": "veri_ozeti_30a.md", "kimlik": "K0123"}` biçimindedir: kimlik o özette geçen bir K kimliğidir. İki özetin kimlikleri ayrıdır (her biri kendi paketinin); kimliği hangi özetten aldıysan o dosyayı yaz. Değerleri program özetin paketinden okur.
- Kancanın en az bir kanıtı olsun. İçerik planında en az 5 bölüm olsun ve her bölüm en az bir kanıta dayansın.
- `sablon` alanına `sablonlar.md`'deki bir şablonun anahtarını, `parametreler` alanına parametrelerini yaz (parametre değeri mahallenin kimliğidir); öneri mevcut bir şablonla kurulamıyorsa `sablon` null, `yeni_sablon_gerekir` true olur.
- İngilizce başlık en çok 100 karakterdir.
- Başlıklar birbirini ve `onceki_oneriler.md`'dekileri tekrar etmez; büyük-küçük harf ve noktalama farkı tekrar sayılır.
- Bitirince kısa bir Türkçe özet yaz: kaç aday, hangi aileler, önemli eksik veri.
