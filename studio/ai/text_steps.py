"""The video text's seven Claude steps (GÖREV-15, Adım 4) in the step framework (`steps.py`).

| key | title | instructions | output |
|---|---|---|---|
| metin_plan | Video metni · plan | metin_plan.md | plan.json |
| metin_plan_elestiri | Video metni · plan eleştirisi | metin_plan_elestiri.md | plan_elestirisi.json |
| metin_bolum | Video metni · bölüm | metin_bolum.md | bolum.json |
| metin_birlestirme | Video metni · birleştirme | metin_birlestirme.md | birlestirme.json |
| metin_giris_kapanis | Video metni · giriş ve kapanış | metin_giris_kapanis.md | giris_kapanis.json |
| metin_son_okuma | Video metni · son okuma | metin_son_okuma.md | son_okuma.json |
| metin_ceviri | Video metni · çeviri | metin_ceviri.md | ceviri.json |

The common file comes first; the writing steps (section, merge, introduction and closing, final reading, translation) also get the narrator's
voice and the chosen tone (Ek N). Tools as in the title steps: reading in the run folder, writing the one output file. The chain
(`studio/text/engine.py`) hands each session its input files in `ctx.extra["files"]` (name → text; Ek N's table says which), the task's
facts in `ctx.extra` and, on a second try, the previous output and the reason it came back. Task texts are short and do not repeat the
instructions. The meaning checks here only refuse what the chain cannot use (an evidence id the pack does not have, a section number the
plan does not have, a translation without every number); the program's check of the text is `studio/text/audit.py`.
"""
import json

from ..text import document as D
from ..text import marks
from . import steps, title

PREVIOUS = "onceki_cikti.json"
TITLES = {"metin_plan": "Video metni · plan", "metin_plan_elestiri": "Video metni · plan eleştirisi", "metin_bolum": "Video metni · bölüm",
          "metin_birlestirme": "Video metni · birleştirme", "metin_giris_kapanis": "Video metni · giriş ve kapanış",
          "metin_son_okuma": "Video metni · son okuma", "metin_ceviri": "Video metni · çeviri"}
OUTPUTS = {"metin_plan": "plan.json", "metin_plan_elestiri": "plan_elestirisi.json", "metin_bolum": "bolum.json",
           "metin_birlestirme": "birlestirme.json", "metin_giris_kapanis": "giris_kapanis.json", "metin_son_okuma": "son_okuma.json",
           "metin_ceviri": "ceviri.json"}
VOICE_STEPS = {"metin_bolum", "metin_birlestirme", "metin_giris_kapanis", "metin_son_okuma", "metin_ceviri"}
DESCRIPTIONS = {"baslik_analizi.md": "seçilen başlık ve analizi", "paket_ozeti.md": "videonun kanıtları (video paketinin yazar özeti)",
                "sayilar.csv": "videonun sayıları (sayı listesi)", "kanal_plani.md": "kanalın planı", "plan.json": "videonun planı",
                "plan_elestirisi.json": "planın eleştirisi", "bolum.md": "senin bölümün", "bolumler.md": "bölümler sırasıyla",
                "metin.md": "birleşmiş metin", "yayinlanan_videolar.md": "kanalın yayınlanmış videoları",
                "cumleler.md": "numaralı İngilizce cümleler", PREVIOUS: "önceki çıktın (yeniden deneme)"}


def prepare(ctx):
    inputs = []
    for name, text in (ctx.extra.get("files") or {}).items():
        (ctx.folder / name).write_text(text, encoding="utf-8")
        inputs.append({"dosya": name, "aciklama": DESCRIPTIONS.get(name, name)})
    return inputs


def task_lines(key, ctx):
    extra = ctx.extra
    lines = [f"Adım: {key}", f"Video: {extra.get('video_title', '')}"]
    if ctx.tone:
        lines.append(f"Ton: {ctx.tone['ad']}")
    if extra.get("section") is not None:
        lines.append(f"Bölüm: {extra['section']}")
    if extra.get("chunk"):
        index, total = extra["chunk"]
        lines.append(f"Parça: {index}/{total}")
    lines += ["", "Çalışma klasöründeki dosyalar:"]
    lines += [f"- `{name}` — {DESCRIPTIONS.get(name, name)}" for name in (extra.get("files") or {})]
    lines += ["", f"Çıktın `{OUTPUTS[key]}`; şeması sistem talimatının sonunda. Yalnız bu klasördeki dosyaları oku, yalnız bu dosyayı yaz."]
    if extra.get("known_terms"):
        lines += ["", "Önceki parçaların terimleri (aynı biçimde kullan):"] + [f"- {t['en']} → {t['tr']}" for t in extra["known_terms"]]
    if extra.get("reason"):
        lines += ["", "DÖNÜŞ SEBEBİ", extra["reason"].strip()]
        if PREVIOUS in (extra.get("files") or {}):
            lines.append(f"Önceki çıktın `{PREVIOUS}` dosyasında; bu sebebe göre yeniden yaz.")
    return "\n".join(lines) + "\n"


def no_fill(ctx, schema):
    return schema


def pack_ids(ctx):
    return ctx.extra.get("pack_ids") or set()


def unknown_ids(ctx, texts):
    known = pack_ids(ctx)
    return sorted({i for text in texts for i in marks.ids_in(text) if i not in known})


def check_plan(ctx, data):
    numbers = [s["no"] for s in data.get("bolumler") or []]
    found = []
    if numbers != list(range(1, len(numbers) + 1)):
        found.append(title.problem(title.ERROR, f"Bölüm numaraları 1'den başlayıp sırayla gitmeli (yazılan: {', '.join(map(str, numbers))})."))
    return found     # unknown evidence ids are the program's plan check (it sends the plan back once; studio/text/audit.py)


def check_critique(ctx, data):
    return []


def check_section(ctx, data):
    found = []
    if data.get("bolum_no") != ctx.extra.get("section"):
        found.append(title.problem(title.ERROR, f"bolum_no {ctx.extra.get('section')} olmalı (yazılan: {data.get('bolum_no')})."))
    unknown = unknown_ids(ctx, data.get("paragraflar") or [])
    if unknown:
        found.append(title.problem(title.ERROR, f"Pakette olmayan kanıt kimlikleri: {', '.join(unknown)}."))
    return found


def check_merge(ctx, data):
    plan = ctx.extra.get("plan") or {}
    order = [s["no"] for s in sorted(plan.get("bolumler") or [], key=lambda s: s["no"])]
    pairs = set(zip(order, order[1:]))
    found = []
    for item in data.get("gecisler") or []:
        if (item.get("onceki_bolum"), item.get("sonraki_bolum")) not in pairs:
            found.append(title.problem(title.ERROR, f"Geçiş ardışık iki bölüm arasında olmalı ({item.get('onceki_bolum')} → "
                                                    f"{item.get('sonraki_bolum')} planda ardışık değil)."))
    for item in data.get("yeniden_kancalar") or []:
        if item.get("bolumden_sonra") not in order:
            found.append(title.problem(title.ERROR, f"Yeniden kanca planda olmayan bir bölümden sonra ({item.get('bolumden_sonra')})."))
    unknown = unknown_ids(ctx, [i.get("metin") or "" for i in (data.get("gecisler") or []) + (data.get("yeniden_kancalar") or [])])
    if unknown:
        found.append(title.problem(title.ERROR, f"Pakette olmayan kanıt kimlikleri: {', '.join(unknown)}."))
    return found


def check_ends(ctx, data):
    unknown = unknown_ids(ctx, (data.get("giris") or []) + (data.get("kapanis") or []))
    return [title.problem(title.ERROR, f"Pakette olmayan kanıt kimlikleri: {', '.join(unknown)}.")] if unknown else []


def check_final_read(ctx, data):
    highest = ctx.extra.get("sentence_count") or 0
    wrong = sorted({item.get("no") for item in data.get("duzeltmeler") or [] if not 1 <= (item.get("no") or 0) <= highest})
    return [title.problem(title.ERROR, f"Metinde olmayan cümle numaraları: {', '.join(map(str, wrong))} (1–{highest}).")] if wrong else []


def check_translation(ctx, data):
    try:
        D.check_translation(data, ctx.extra.get("expected_numbers") or [])
    except D.AnswerError as exc:
        return [title.problem(title.ERROR, str(exc))]
    return []


def render_json(ctx, data, problems):
    lines = [f"# {TITLES.get(ctx.extra.get('step_key'), 'Video metni')}", "", "```json", json.dumps(data, ensure_ascii=False, indent=1), "```"]
    if problems:
        lines += ["", "## Sorunlar", ""] + [f"- {p['metin']}" for p in problems]
    return "\n".join(lines) + "\n"


CHECKS = {"metin_plan": check_plan, "metin_plan_elestiri": check_critique, "metin_bolum": check_section, "metin_birlestirme": check_merge,
          "metin_giris_kapanis": check_ends, "metin_son_okuma": check_final_read, "metin_ceviri": check_translation}

STEPS = {}
for _key, _title in TITLES.items():
    STEPS[_key] = steps.register(steps.Step(
        key=_key, title=_title, instructions=("ortak.md", f"{_key}.md"), schema=f"{_key}.schema.json", output=OUTPUTS[_key],
        markdown=OUTPUTS[_key].replace(".json", ".md"), prepare=prepare, task=(lambda key: lambda ctx: task_lines(key, ctx))(_key),
        fill_schema=no_fill, check=CHECKS[_key], render=render_json, voice=_key in VOICE_STEPS))
