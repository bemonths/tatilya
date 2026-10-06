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
main
a938367a280ef799597d5d90dc39ef34a26a6fcb
v0.6.0
schema 6
```

## Aktif branch

```text
v0.7-lodging-inventory
23905962126ba9f00f7f8b6223c67c9633e70c2c
```

Aktif branch yalnız lodging keşif belgeleri içeriyor; app ve DB değiştirilmedi.

## Çalışan connector'lar

- south-walton-beaches
- nws-weather
- south-walton-restaurants

## Mevcut lodging sonucu

Book>Direct public JSON search bulunmuştur fakat tarih zorunludur.

Tam date-independent:
- unit inventory yok,
- provider inventory yok.

Karar:
date-filtered search'i full inventory diye kodlama.

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
→ manual acceptance
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

Kullanıcı açıkça onaylamadan feature branch'i main'e alma.

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

Sonra kullanıcıya:
- ne bulundu,
- ne kanıtlanmadı,
- hangi kararın gerektiği

açık şekilde raporla.
