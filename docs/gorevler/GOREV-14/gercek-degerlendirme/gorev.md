Adım: baslik_degerlendirme
Tür: ilk çalışma
Bölge: Rosemary Beach
Not: yok

Görev: kullanıcının yazdığı başlığı ya da fikri değerlendir (sistem metnindeki "Kullanıcının başlığını değerlendirme").

Çalışma klasöründeki dosyalar (hepsini oku):
- `kullanici_basligi.md` — kullanıcının yazdığı başlık ya da fikir (aynen).
- `baslik_olculeri.md` — iyi bir başlığın ölçüleri (başlık önerisi talimatı; oradaki aday sayısı ve çıktı biçimi bu görev için geçerli değil).
- `secim.md` — kullanıcının bölgesi, notu ve başlık ekleri.
- `kanal_plani.md` — kanal planı: içerik aileleri, konu motoru, ilkeler.
- `kanal_arastirmasi.md` — kanal araştırması: rakip videolar, izleyicinin soruları.
- `veri_ozeti_30a.md` — 30A verisinin yazar özeti (paket 103e05e7).
- `veri_ozeti_mahalle.md` — Rosemary Beach mahallesinin yazar özeti (paket f3c2de5a).
- `sablonlar.md` — programın paket kurabildiği şablonlar.
- `onceki_oneriler.md` — daha önce önerilen başlıklar.

Çıktı:
- `baslik_degerlendirme.json` — şema: sistem talimatının sonundaki "Çıktı şeması" bölümü. Okunur Markdown'ı program üretir; sen Markdown yazma.

Kurallar:
- Yalnız bu klasördeki dosyaları oku; yalnız `baslik_degerlendirme.json`'u yaz. Başka hiçbir dosyayı oluşturma ya da değiştirme.
- `kullanici_fikri` alanına `kullanici_basligi.md`'ndaki metni (işaret satırlarının arasındakini) aynen yaz.
- `doluluk`: fikir veriyle doluyorsa `dolar_mi` true; dolmuyorsa false, `aciklama` neden dolmadığını, `eksik_veri` neyin eksik olduğunu söyler. Fikir doluyorsa 1–3 aday yaz (birincisi en çok önerdiğin); dolmuyorsa aday listesi boş kalabilir. En çok 3 aday.
- `sorunlar`: kullanıcının kendi ifadesindeki sorunlar (yoksa boş liste).
- Adaylar Rosemary Beach hakkında olur; her adayın `bolge` alanı "Rosemary Beach" olur.
- `aile` alanına kanal planındaki içerik ailesinin adını şemadaki listede yazıldığı gibi yaz.
- Her kanıt `{"dosya": "veri_ozeti_30a.md", "kimlik": "K0123"}` biçimindedir: kimlik o özette geçen bir K kimliğidir. İki özetin kimlikleri ayrıdır (her biri kendi paketinin); kimliği hangi özetten aldıysan o dosyayı yaz. Değerleri program özetin paketinden okur.
- Kancanın en az bir kanıtı olsun. İçerik planında en az 5 bölüm olsun ve her bölüm en az bir kanıta dayansın.
- `sablon` alanına `sablonlar.md`'deki bir şablonun anahtarını, `parametreler` alanına parametrelerini yaz (parametre değeri mahallenin kimliğidir); öneri mevcut bir şablonla kurulamıyorsa `sablon` null, `yeni_sablon_gerekir` true olur.
- İngilizce başlık en çok 100 karakterdir (ek dahil); İngilizce başlık `secim.md`'deki İngilizce ekle, Türkçe karşılığı oradaki Türkçe ekle biter.
- Türkçe karşılık İngilizce başlığın birebir çevirisidir.
- Başlıklar birbirini ve `onceki_oneriler.md`'dekileri tekrar etmez; büyük-küçük harf ve noktalama farkı tekrar sayılır.
- Bitirince kısa bir Türkçe özet yaz: fikir doluyor mu, kaç aday, önemli eksik veri.
