"""6 · Yayın paketi (HEDEF-04 A-6): the video's publishing package from the approved text, in one Claude call.

Claude gets the approved English narration (the tone chosen in 5 · Kontrol ve ton seçimi) with an estimated start time before every
paragraph, and the video's title and promise; it answers with JSON: the chapter titles (first at 00:00, at least three, each at least ten
seconds), the first two lines of the description, the three search queries the video aims at, the tags, the cover text and the cover idea.
The program checks the chapters (00:00, at least three, at least ten seconds each, ascending, inside the estimated length) and writes
`yayin.json` and the readable `yayin.md` into the run folder; the approval writes a snapshot under `videolar/<video>/6_yayin/`.

The times are estimates: the words before a paragraph at 150 words a minute (`studio/text/views.py` `WORDS_PER_MINUTE`). They become
exact when the voice exists (7 · Seslendirme); every screen and file says "tahmini".
"""
import json
import re

from . import steps, store, title

STEP_KEY = "yayin"
OUTPUT, MARKDOWN = "yayin.json", "yayin.md"
SELECTION, NARRATION, TIMING, PREVIOUS = "yayin_secim.md", "seslendirme_zamanli.md", "zaman_tahmini.json", "onceki_cikti.json"
WORDS_PER_MINUTE = 150
MIN_CHAPTERS, MIN_CHAPTER_S = 3, 10
TAGS_LIMIT = 500
ESTIMATED = "Zamanlar tahminidir: metnin kelime sayısından, dakikada 150 kelimeyle; ses gelince kesinleşecek."
TIME = re.compile(r"^(?:(\d+):)?(\d{2}):(\d{2})$")


def clock(seconds):
    total = int(round(seconds or 0))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def seconds_of(text):
    """"02:10" → 130, "1:02:10" → 3730; None when it is not a time."""
    found = TIME.match(str(text or "").strip())
    if not found or int(found.group(3)) >= 60 or (found.group(1) and int(found.group(2)) >= 60):
        return None
    return int(found.group(1) or 0) * 3600 + int(found.group(2)) * 60 + int(found.group(3))


def word_count(text):
    return len(re.findall(r"\S+", text or ""))


def timing(document):
    """([{tur, baslik, paragraflar: [{bas_s, metin}]}], words, seconds) of a text version's `metin.json` (English sentences)."""
    parts, words = [], 0
    for part in document.get("parcalar") or []:
        paragraphs = []
        for paragraph in part.get("paragraflar") or []:
            text = " ".join((s.get("en") or "").strip() for s in paragraph.get("cumleler") or []).strip()
            if text:
                paragraphs.append({"bas_s": words * 60 / WORDS_PER_MINUTE, "metin": text})
                words += word_count(text)
        parts.append({"tur": part.get("tur"), "baslik": part.get("baslik"), "paragraflar": paragraphs})
    return parts, words, words * 60 / WORDS_PER_MINUTE


def approved_version(ctx):
    from ..text import store as text_store
    version = text_store.version(ctx.db, ctx.params.get("surum_id") or "")
    if version is None or version["video_id"] != ctx.params.get("video_id"):
        raise steps.StepError("Onaylı metin bulunamadı: önce 5 · Kontrol ve ton seçimi onaylanmalı.")
    return version


def prepare(ctx):
    version = approved_version(ctx)
    document = json.loads((ctx.db.path.parent / version["folder"] / "metin.json").read_text(encoding="utf-8-sig"))
    parts, words, length = timing(document)
    video = store.video(ctx.db, ctx.params["video_id"]) or {}
    analysis = video.get("analysis") or {}
    record = {"kelime": words, "sure_s": round(length), "dakikada_kelime": WORDS_PER_MINUTE, "ton": version["tone_name"],
              "surum": version["number"], "surum_kimligi": version["id"], "tahmini": True}
    ctx.extra["zaman"] = record
    (ctx.folder / TIMING).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    selection = ["# Yayın paketi için seçim", "",
                 f"- Video başlığı (İngilizce): {video.get('title_en') or '—'}",
                 f"- Türkçe karşılığı: {video.get('title_tr') or '—'}",
                 f"- Bölge: {video.get('region_name') or ctx.params.get('bolge') or '—'}",
                 f"- İzleyicinin sorusu: {analysis.get('izleyici_sorusu') or '—'}",
                 f"- Vaat (kanca): {(analysis.get('kanca') or {}).get('metin') or '—'}",
                 f"- Başlık adımındaki kapak fikri: {analysis.get('kapak_fikri') or '—'}",
                 f"- Onaylı metin: {version['tone_name']} tonu, {version['number']}. sürüm",
                 f"- Kelime sayısı: {words}; tahmini süre: {clock(length)} ({round(length)} sn). Dakikada {WORDS_PER_MINUTE} kelimeyle "
                 "hesaplandı; ses gelince kesinleşecek.", ""]
    (ctx.folder / SELECTION).write_text("\n".join(selection), encoding="utf-8")
    lines = ["# İngilizce seslendirme metni, tahmini zamanlarla", "",
             f"Her paragrafın başındaki `[~mm:ss]` o paragrafın tahmini başlangıcıdır (önceki kelimeler, dakikada {WORDS_PER_MINUTE} "
             "kelime). `##` satırları metnin kendi bölümleridir; adları Türkçedir.", ""]
    for part in parts:
        if not part["paragraflar"]:
            continue
        lines += [f"## [~{clock(part['paragraflar'][0]['bas_s'])}] {part['baslik']} ({part['tur']})", ""]
        for paragraph in part["paragraflar"]:
            lines += [f"[~{clock(paragraph['bas_s'])}] {paragraph['metin']}", ""]
    lines.append(f"[~{clock(length)}] (metnin sonu)")
    (ctx.folder / NARRATION).write_text("\n".join(lines) + "\n", encoding="utf-8")
    inputs = [{"dosya": SELECTION, "aciklama": "videonun başlığı, vaadi ve onaylı metnin bilgisi"},
              {"dosya": NARRATION, "aciklama": "onaylı İngilizce seslendirme metni, paragraf başlarında tahmini zamanlar"}]
    if ctx.correction and ctx.correction.get("data") is not None:
        (ctx.folder / PREVIOUS).write_text(json.dumps(ctx.correction["data"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        inputs.append({"dosya": PREVIOUS, "aciklama": "düzeltilecek önceki yayın paketi"})
    return inputs


def task(ctx):
    length = clock((ctx.extra.get("zaman") or {}).get("sure_s"))
    lines = ["Adım: yayin", f"Tür: {'düzeltme' if ctx.correction else 'ilk çalışma'}", "",
             "Görev: onaylı İngilizce seslendirme metninden videonun yayın paketini yaz (sistem metnindeki \"Yayın paketi\").", "",
             "Verilen dosyalar (hepsi aşağıda; hepsini oku):",
             f"- `{SELECTION}` — videonun başlığı, vaadi, kapak fikri ve metnin tahmini süresi.",
             f"- `{NARRATION}` — onaylı İngilizce seslendirme metni; her paragrafın başında tahmini zamanı.",
             *([f"- `{PREVIOUS}` — düzelteceğin önceki çıktın."] if ctx.correction else []), "",
             "Çıktı:",
             f"- `{OUTPUT}`'un içeriği: cevabın yalnız bu JSON'dur; şeması sistem talimatının sonundaki \"Çıktı şeması\" bölümünde. Okunur "
             "Markdown'ı program üretir; sen Markdown yazma.", "",
             "Kurallar:",
             f"- `bolumler`: ilk bölümün zamanı `00:00`; en az {MIN_CHAPTERS} bölüm; zamanlar artan sırada ve `mm:ss` biçiminde; iki bölüm "
             f"başı arası en az {MIN_CHAPTER_S} saniye. Her bölümün zamanını `{NARRATION}`'daki `[~mm:ss]` işaretlerinden birinden al (bölüm "
             f"o paragrafla başlar). Metnin tahmini süresi {length}; son bölüm bundan en az {MIN_CHAPTER_S} saniye önce başlar.",
             "- Zamanlar tahminidir; ses gelince program kesinleştirir. İşaretlerdeki zamanları kullan, kendin hesaplama.",
             "- `aciklama_ilk_iki_satir` tam iki satır, `arama_sorgulari` tam üç sorgu; her birinin `en`'i YouTube'a gidecek İngilizce metin, "
             "`tr`'si Türkçe karşılığıdır.",
             f"- `etiketler`: İngilizce; virgüllerle birleşince en çok {TAGS_LIMIT} karakter.",
             "- Kısa Türkçe notlarını (neye dikkat ettin, kullanıcı neyi seçmeli) `notlar` alanına yaz."]
    if ctx.correction:
        lines += ["", f"Düzeltme: kullanıcının düzeltme notu aşağıda. Önceki çıktın `{PREVIOUS}` bölümünde. Notu uygula ve `{OUTPUT}`'u "
                      "baştan ve eksiksiz yaz.", *steps.note_block(ctx.correction["note"])]
    return "\n".join(lines) + "\n"


def chapter_problems(chapters, total=None):
    """The program's check of the chapters: 00:00 first, at least three, at least ten seconds each, ascending, inside the length."""
    out = []
    error = lambda text: out.append(title.problem(title.ERROR, text))
    if len(chapters) < MIN_CHAPTERS:
        error(f"En az {MIN_CHAPTERS} bölüm olmalı; {len(chapters)} bölüm var.")
    times = [seconds_of(c.get("zaman")) for c in chapters]
    unread = [str(c.get("zaman")) for c, t in zip(chapters, times) if t is None]
    if unread:
        error("Bölüm zamanı okunamadı (mm:ss olmalı): " + ", ".join(unread) + ".")
        return out
    if times and times[0] != 0:
        error(f"İlk bölüm 00:00'da başlamalı; {chapters[0].get('zaman')} yazılmış.")
    for number in range(1, len(times)):
        gap = times[number] - times[number - 1]
        if gap <= 0:
            error(f"Bölümler artan sırada değil: {number + 1}. bölüm ({chapters[number].get('zaman')}) öncekinden sonra başlamıyor.")
        elif gap < MIN_CHAPTER_S:
            error(f"{number}. bölüm {gap} sn; her bölüm en az {MIN_CHAPTER_S} sn olmalı.")
    if total and times:
        if times[-1] >= total:
            error(f"Son bölüm ({chapters[-1].get('zaman')}) metnin tahmini süresinden ({clock(total)}) sonra başlıyor.")
        elif total - times[-1] < MIN_CHAPTER_S:
            error(f"Son bölüm {total - times[-1]} sn; her bölüm en az {MIN_CHAPTER_S} sn olmalı.")
    return out


def timing_of(ctx):
    if ctx.extra.get("zaman"):
        return ctx.extra["zaman"]
    try:
        return json.loads((ctx.folder / TIMING).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def check(ctx, data):
    problems = chapter_problems(data.get("bolumler") or [], timing_of(ctx).get("sure_s"))
    tags = ", ".join(data.get("etiketler") or [])
    if len(tags) > TAGS_LIMIT:
        problems.append(title.problem(title.WARNING, f"Etiketler virgüllerle {len(tags)} karakter; YouTube en çok {TAGS_LIMIT} karakter alır."))
    return problems


def youtube_text(data):
    """The head of the description as it goes to YouTube: the two lines, then the chapters (estimated times)."""
    lines = [(item or {}).get("en") or "" for item in data.get("aciklama_ilk_iki_satir") or []]
    lines += ["", "Chapters:"] + [f"{c.get('zaman')} {c.get('baslik_en')}" for c in data.get("bolumler") or []]
    return "\n".join(lines)


def render(ctx, data, problems, chosen=None):
    found = timing_of(ctx)
    video = store.video(ctx.db, ctx.params.get("video_id")) or {}
    cell = lambda text: str(text or "").replace("|", "\\|")
    pair = lambda number, item: f"{number}. {(item or {}).get('en')} — _{(item or {}).get('tr')}_"
    lines = [f"# Yayın paketi — {video.get('title_en') or ctx.params.get('bolge')}", "",
             f"- Çalışma `{ctx.run_id}` · metin: {found.get('ton')} tonu, {found.get('surum')}. sürüm · {found.get('kelime')} kelime · "
             f"tahmini süre {clock(found.get('sure_s'))}", f"- {ESTIMATED}", "",
             "## Bölüm başlıkları (tahmini zamanlar)", "", "| Zaman (tahmini) | İngilizce | Türkçe |", "|---|---|---|"]
    lines += [f"| ~{cell(c.get('zaman'))} | {cell(c.get('baslik_en'))} | {cell(c.get('baslik_tr'))} |" for c in data.get("bolumler") or []]
    lines += ["", "## Açıklamanın ilk iki satırı", ""] + [pair(n, i) for n, i in enumerate(data.get("aciklama_ilk_iki_satir") or [], 1)]
    lines += ["", "## Hedeflenen arama sorguları", ""] + [pair(n, i) for n, i in enumerate(data.get("arama_sorgulari") or [], 1)]
    lines += ["", "## Etiketler", "", ", ".join(data.get("etiketler") or [])]
    cover = data.get("kapak_yazisi") or {}
    lines += ["", "## Kapak", "", f"- Kapak yazısı: {cover.get('en')} — _{cover.get('tr')}_", f"- Kapak fikri: {data.get('kapak_fikri')}"]
    lines += ["", "## YouTube'a yapıştırılacak açıklama başı (bölüm zamanları tahmini)", "", "```text", youtube_text(data), "```"]
    if problems:
        lines += ["", "## Doğrulama sorunları", ""] + [f"- {'Hata' if p['seviye'] == title.ERROR else 'Uyarı'}: {p['metin']}" for p in problems]
    else:
        lines += ["", "## Doğrulama", "", "Bölümler uygun: ilki 00:00, en az 3 bölüm, her biri en az 10 sn, artan sıra."]
    if data.get("notlar"):
        lines += ["", "## Claude'un notları", ""] + [f"- {n}" for n in data["notlar"]]
    return "\n".join(lines).rstrip() + "\n"


STEP = steps.register(steps.Step(key=STEP_KEY, title="Yayın paketi", instructions=("ortak.md", "yayin.md"), schema="yayin.schema.json",
                                 output=OUTPUT, markdown=MARKDOWN, prepare=prepare, task=task, fill_schema=lambda ctx, schema: schema,
                                 check=check, render=render))
