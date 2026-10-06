# Geliştirme, Test ve Release İş Akışı

## Çalışma modeli

Projede şu pratik döngü kullanılır:

```text
Gereksinim / sorun
→ Proje yöneticisi (ayrı Claude sohbeti) GÖREV-NN metnini yazar
→ Kullanıcı görevi Claude Code'a taşır
→ Claude Code yerel repo üzerinde, görevin kendi dalında çalışır
→ test (gerekirse geçici veri klasöründe canlı smoke)
→ commit + görev dalına push
→ Claude Code raporu; görev metni, rapor ve çıktılar docs/gorevler/GOREV-NN/ altında aynı dala push edilir
→ yönetici commit, CI ve raporu GitHub'dan inceler; gerekirse düzeltme görevi verir
→ gerekirse kullanıcı gerçek ortamda manuel kabul yapar
→ kullanıcı onayıyla main merge
→ release tag
```

Bu modelin amacı, yöneticinin erişemediği gerçek yerel program/DB ve canlı kaynak davranışını Claude Code tarafında test ettirmek ve commit'i ayrıca bağımsız incelemektir. Kullanıcı İngilizce bilmez ve kod okumaz; görevi ve raporu taşır, main'e alma kararını verir. Raporlar bu yüzden Türkçe ve sadedir.

## Repo ve local

Repo:

```text
https://github.com/bemonths/tatilya
```

Yerel:

```text
C:\Users\1\Documents\Codex\2026-09-29\referenced-chatgpt-conversation-this-is-an\outputs\30a-studio
```

Başlatma:

```text
baslat.bat
```

## Git ownership notu

Repo geçmişte `CodexSandboxOffline` sahibi olarak göründüğü için normal Windows kullanıcı Git komutlarında “dubious ownership” uyarısı verdi.

Gerekirse kullanılmış çözüm:

```bat
git config --global --add safe.directory "C:/Users/1/Documents/Codex/2026-09-29/referenced-chatgpt-conversation-this-is-an/outputs/30a-studio"
```

Bu yalnız Git güvenlik exception'ıdır; repo içeriğini değiştirmez.

## Branch disiplini

Stable:
`main`

Yeni geliştirme:
feature branch.

Örnek:
- `v0.5-restaurants-connector`
- `v0.6-destination-layer`
- `v0.7-lodging-inventory`

Feature branch main'e ancak:
- kod incelemesi,
- CI,
- gereken real smoke,
- kullanıcı kabulü

sonrası alınmalıdır.

## Test komutları

Python:

```text
python -m pytest -q
```

Frontend:

```text
node --test tests/frontend.test.mjs
```

Stable v0.6 / güncel docs branch test tabanı:
- 289 Python
- 19 frontend

## Network test politikası

Unit/integration testleri canlı web'e bağımlı olmamalıdır.

Tercih:
- fixture
- `httpx.MockTransport`
- synthetic second destination

Canlı HTTP:
yalnız explicit smoke/discovery.

Bu ayrım kaynak sitesi geçici değiştiğinde test suite'in rastgele kırılmasını engeller.

## Yeni connector iş akışı

### A. Kaynak keşfi

Önce:
- gerçek URL,
- gerçek method,
- pagination,
- filter sözleşmesi,
- external ID,
- response semantics,
- completeness

kanıtlanır.

Kodlamaya erken başlanmaz.

### B. Schema tasarımı

Source semantiği netleşince:
- required vs nullable alanlar,
- relation tabloları,
- provenance,
- destination isolation

tasarlanır.

### C. Migration

- gerçek DB kopyası,
- before/after counts,
- foreign_key_check,
- rollback test.

Production DB doğrudan deneme alanı değildir.

### D. Parser / HTTP test

- happy path
- malformed
- duplicate ID
- pagination loop
- redirect
- wrong content type
- max bytes
- timeout
- retry
- 429
- cancel

### E. Atomic publish

Tam crawl parse edilmeden snapshot görünür olmamalı.

### F. Raw artifact

Manifest ve alt dosyalar gerekiyorsa hash/provenance ile saklanır.

### G. UI

- source readiness
- run selector
- filters
- detail
- diff
- raw download
- empty state

### H. Live smoke

TEMP data dir tercih edilir.

Üretim DB'si ancak migration güvenli ise açılır.

## Migration güvenliği

Kullanıcı verisi kritik.

Yapma:

```text
rm data/
DB reset
fresh DB ile gerçek kullanıcı verisini değiştirme
```

Her schema bump:
- backup,
- copy test,
- migration,
- FK check,
- existing snapshot check.

## GitHub inceleme

Commit geldikten sonra şu kontrol edilir:

- branch doğru mu?
- parent main doğru mu?
- diff istenen kapsamda mı?
- app/schema version doğru mu?
- CI yeşil mi?
- test sayıları?
- main yanlışlıkla değişmiş mi?
- tag doğru commit'e mi işaret ediyor?

## Kullanıcı manuel testleri

Kullanıcıya otomatik testlerin zaten kanıtladığı her şeyi tekrar yaptırmak gerekmez.

Manuel test yalnız gerçek ortamın anlamlı olduğu yerlerde:
- eski user DB migration
- UI gerçek rendering
- local path/process
- browser behavior
- production snapshot görünürlüğü

için kullanılmalıdır.

## Release

Örnek v0.6:

Feature:
`v0.6-destination-layer`

Verified commit:
`a938367...`

Sonra:
- main fast-forward
- main CI
- `v0.6.0` annotated tag

Tag farklı commit'e zaten bağlıysa sessizce taşınmamalıdır.

## Doküman güncelleme kuralı

Her önemli mimari değişiklikte en az şu belgeler gözden geçirilir:

- `CALISMA_MANTIGI.md`
- `README.md`
- `docs/MIMARI.md`
- `docs/ASAMALAR.md`
- ilgili domain Mx belgesi

Bu devir paketi repo'ya yerleştirilirse `docs/DEVIR/` belgeleri de aynı commit içinde güncellenmelidir.

## Debug yaklaşımı

Sorun kullanıcı makinesinde ise:
- tahmin ederek kullanıcıya çok komut yaptırmak yerine,
- Claude Code gerçek local path/DB/process'i incelemelidir.

Önceden yaşanan örnek:
Restaurant source “Bağlantı bekliyor” görünüyordu. Git branch/head aslında günceldi. Gerçek local DB/source identity üzerinde teşhis yapılıp connector readiness doğrulandı.

## Main'e merge öncesi checklist

- [ ] scope tamam
- [ ] code review
- [ ] Python tests
- [ ] frontend tests
- [ ] CI success
- [ ] migration copy test
- [ ] destination isolation
- [ ] raw artifact
- [ ] live smoke
- [ ] user critical smoke
- [ ] docs
- [ ] branch push
- [ ] main merge
- [ ] main CI
- [ ] tag
