# Yeni Yapay Zekâ / Geliştirici Başlangıç Talimatı

Bu belge başka bir AI'a doğrudan verilebilecek kısa onboarding talimatıdır.

---

## Rolün

Sen `bemonths/tatilya` reposundaki 30A Studio projesini devralıyorsun.

Bu proje, 30A / South Walton için güvenilir veri toplayan ve ileride kaynaklı YouTube araştırma/içerik üretimini besleyecek yerel bir FastAPI + SQLite stüdyosudur.

30A yalnız ilk destinasyondur; mimari multi-destination'dır.

## Önce oku

Sırayla:

1. `CALISMA_MANTIGI.md`
2. `docs/DEVIR/05_SURUM_GECMISI_VE_GUNCEL_DURUM.md`
3. `docs/DEVIR/02_TEKNIK_MIMARI_VE_VERI_MODELI.md`
4. `docs/DEVIR/03_VERI_KAYNAKLARI_VE_DOGRULAMA.md`
5. görev domain'ine ait Mx belge

Kodla belge çelişirse kodu doğrula ve dokümanı güncelle.

## Repo

```text
bemonths/tatilya
```

Yerel:

```text
C:\Users\1\Documents\Codex\2026-09-29\referenced-chatgpt-conversation-this-is-an\outputs\30a-studio
```

## Stable

```text
tag v0.8.0 -> de6685f10699d37afd4e1f13b115a6fa13369355
main -> de6685f10699d37afd4e1f13b115a6fa13369355
app 0.8.0 / schema 8
```

## Aktif branch

```text
gorev-06-referanslar
kasırga evre kuralı (HURDAT2 /2) ve elle doğrulanmış referans tablosu (Referanslar sekmesi)
app 0.9.0 / schema 9
```

main'e alınmadı; karar yöneticinin. Eski `v0.7-lodging-inventory` dalı yalnız konaklama keşif belgeleriydi ve main'e alındı; adı v0.7.0 ile ilgili değildir. Gerçek veritabanı yalnız görev metni açıkça isterse ve normal kullanımla, önce `data/` tam yedeği alınarak güncellenir (CLAUDE.md). Gerçek veritabanı 7 Ekim 2026'dan beri şema 9'dur; main'deki 0.8.0 onu açmaz, uygulama bu dal main'e alınana kadar `gorev-06-referanslar` dalından çalıştırılır.

## Çalışan connector'lar

- south-walton-beaches
- nws-weather
- south-walton-restaurants
- south-walton-neighborhoods (v0.7.0)
- ncei-climate-normals, ndbc-water-temperature, hurdat2-storm-proximity (v0.8.0; generic, yapılandırma SQLite'ta; `docs/M8-IKLIM-VERISI.md`; kasırga `/2` görev dalında)

Elle doğrulanmış referans tablosu connector değildir: `studio/destinations/thirty_a_references.csv` (`docs/M9-REFERANS-TABLOSU.md`).

Plaj erişimi–mahalle eşlemesi connector değildir; `studio/destinations/thirty_a_beach_neighborhoods.csv` dosyasında duran, yöntemi etiketli ayrı bir katmandır (`docs/M7-MAHALLE-VERISI.md`).

## Mevcut lodging sonucu

Book>Direct public JSON search bulunmuştur fakat tarih zorunludur.

Tam date-independent:
- unit inventory yok,
- provider inventory yok.

Karar:
date-filtered search'i full inventory diye kodlama. 7 Ekim 2026 yönetici kararıyla tam envanter şartı kaldırıldı; konaklama tarihli arama anlık görüntüleri olarak modellenecek.

## Veri ilkeleri

- Uydurma alan yok.
- Missing → NULL.
- fetched_at ≠ source_updated.
- Stable source ID tercih et.
- Adres/coordinate ile mahalle tahmini yapma.
- Partial crawl publish etme.
- Raw artifact + hash sakla.
- Destination isolation koru.
- 30A-specific connector başka destination'a bağlanmasın.
- Live count'ları test sabiti yapma.

## Geliştirme yöntemi

Her görev:

```text
keşif
→ semantik doğrulama
→ schema
→ tests
→ implementation
→ TEMP live smoke
→ user DB copy migration
→ commit/push
→ CI
→ review
→ yönetici kabulü (main'e alma kararı görev metniyle)
→ main
→ tag
```

## Kullanıcı verisi

`data/` silinmez/sıfırlanmaz.

Migration önce kopya/yedek üzerinde denenir.

## Test

```text
python -m pytest -q
node --test tests/frontend.test.mjs
```

Mevcut taban:
- 289 Python
- 19 frontend

## Main'e merge

Main'e alma kararı proje yöneticisine aittir. Görev dalını main'e yalnız görev metni bunu açıkça istediğinde al; kullanıcıdan onay isteme.

## Şu an senden beklenmeyenler

- lodging tarih aramalarını full inventory yapmak
- AI/Claude entegrasyonuna kendiliğinden geçmek
- video render eklemek
- ikinci gerçek destination eklemek
- production DB resetlemek
- kullanıcı kaynaklarını sessizce değiştirmek

## Yeni görev gelince

Önce görev mevcut roadmap ile uyumlu mu kontrol et.

Kaynak araştırması istiyorsa:
- gerçek sayfayı/endpoint'i keşfet,
- semantic scope'u kanıtla,
- endpoint tahmin etme,
- gerekli durumlarda public frontend/network sözleşmesini incele,
- bulamadığın şeyi bulmuş gibi davranma.

Sonra yöneticiye, görev raporu (`docs/gorevler/GOREV-NN/RAPOR.md`) üzerinden:
- ne bulundu,
- ne kanıtlanmadı,
- hangi kararın gerektiği

açık şekilde raporla.
