"""The second Claude step (GÖREV-14, Adım 5a): the user's own title or idea, evaluated ("Başlık değerlendirme").

The user writes a title or an idea (Turkish or English) with a region and an optional note. Claude evaluates it with the measures of the
title step and turns it into 1–3 title candidates, or says honestly that the data does not fill a 15–17 minute video (then the list may be
empty, but the explanation and the missing data are written). Instructions: the destination's `ortak.md` and `baslik_degerlendirme.md`.

Inputs: the title step's files (channel plan and research, `secim.md` with the title suffixes, the summaries, the templates, the earlier
proposals) and two more: `kullanici_basligi.md` (the user's text verbatim, between markers) and `baslik_olculeri.md` (a copy of the
destination's `baslik.md`: the measures of a good title live there; its candidate count and output form do not apply here).

The candidates have the title step's structure and pass the same meaning checks (region, evidence ids, plan, template, length, suffix,
repetition); their count is 1–3. A run started from "İngilizcesini Claude yazsın" (Adım 5b) carries the edited candidate in
`kaynak` (its run and index): that candidate's own title is not an "earlier proposal" of the new one.
"""
import json
import shutil
from pathlib import Path

from . import steps, title

STEP_KEY = "baslik_degerlendirme"
OUTPUT, MARKDOWN = "baslik_degerlendirme.json", "baslik_degerlendirme.md"
USER_TITLE, MEASURES = "kullanici_basligi.md", "baslik_olculeri.md"
TITLE_INSTRUCTIONS = "baslik.md"
MAX_CANDIDATES = 3
MAX_IDEA = 500
START, END = "--- başlık başı ---", "--- başlık sonu ---"


def user_title_text(params):
    return "\n".join(["# Kullanıcının başlığı ya da fikri", "",
                      "Kullanıcının yazdığı aşağıda, iki işaret satırının arasında aynen duruyor. Türkçe ya da İngilizce olabilir; tam bir başlık "
                      "da olabilir, yalnız bir fikir de.", "", START, params["kullanici_basligi"].strip(), END, ""])


def prepare(ctx):
    inputs = title.prepare(ctx)
    (ctx.folder / USER_TITLE).write_text(user_title_text(ctx.params), encoding="utf-8")
    inputs.append({"dosya": USER_TITLE, "aciklama": "kullanıcının başlığı ya da fikri"})
    shutil.copyfile(ctx.profile.CLAUDE_INSTRUCTIONS / TITLE_INSTRUCTIONS, ctx.folder / MEASURES)
    inputs.append({"dosya": MEASURES, "aciklama": "başlığın ölçüleri (başlık önerisi talimatının kopyası)"})
    return inputs


def task(ctx):
    found = title.channel(ctx.profile)
    params = ctx.params
    region = params.get("bolge_id")
    summary = title.GENERAL_SUMMARY
    lines = ["Adım: baslik_degerlendirme", f"Tür: {'düzeltme' if ctx.correction else 'ilk çalışma'}", f"Bölge: {params['bolge']}",
             f"Not: {'aşağıda, secim.md dosyasında' if '\n' in (params.get('not') or '') else params.get('not') or 'yok'}", "",
             "Görev: kullanıcının yazdığı başlığı ya da fikri değerlendir (sistem metnindeki \"Kullanıcının başlığını değerlendirme\").", "",
             "Çalışma klasöründeki dosyalar (hepsini oku):",
             f"- `{USER_TITLE}` — kullanıcının yazdığı başlık ya da fikir (aynen).",
             f"- `{MEASURES}` — iyi bir başlığın ölçüleri (başlık önerisi talimatı; oradaki aday sayısı ve çıktı biçimi bu görev için geçerli değil).",
             "- `secim.md` — kullanıcının bölgesi, notu ve başlık ekleri.",
             "- `kanal_plani.md` — kanal planı: içerik aileleri, konu motoru, ilkeler.",
             "- `kanal_arastirmasi.md` — kanal araştırması: rakip videolar, izleyicinin soruları.",
             f"- `{summary}` — 30A verisinin yazar özeti (paket {ctx.packs[summary]['id'][:8]}).",
             *([f"- `{title.REGION_SUMMARY}` — {params['bolge']} mahallesinin yazar özeti (paket {ctx.packs[title.REGION_SUMMARY]['id'][:8]})."]
               if region else []),
             "- `sablonlar.md` — programın paket kurabildiği şablonlar.",
             "- `onceki_oneriler.md` — daha önce önerilen başlıklar.",
             *(["- `onceki_cikti.json` — düzelteceğin önceki çıktın."] if ctx.correction else []), "",
             "Çıktı:",
             f"- `{OUTPUT}` — şema: sistem talimatının sonundaki \"Çıktı şeması\" bölümü. Okunur Markdown'ı program üretir; sen Markdown yazma.", "",
             "Kurallar:",
             f"- Yalnız bu klasördeki dosyaları oku; yalnız `{OUTPUT}`'u yaz. Başka hiçbir dosyayı oluşturma ya da değiştirme.",
             f"- `kullanici_fikri` alanına `{USER_TITLE}`'ndaki metni (işaret satırlarının arasındakini) aynen yaz.",
             f"- `doluluk`: fikir veriyle doluyorsa `dolar_mi` true; dolmuyorsa false, `aciklama` neden dolmadığını, `eksik_veri` neyin eksik "
             f"olduğunu söyler. Fikir doluyorsa 1–{MAX_CANDIDATES} aday yaz (birincisi en çok önerdiğin); dolmuyorsa aday listesi boş kalabilir. "
             f"En çok {MAX_CANDIDATES} aday.",
             "- `sorunlar`: kullanıcının kendi ifadesindeki sorunlar (yoksa boş liste)."]
    if region:
        lines.append(f"- Adaylar {params['bolge']} hakkında olur; her adayın `bolge` alanı \"{params['bolge']}\" olur.")
    else:
        lines.append(f"- Adayın `bolge` alanı \"{found['whole_region']}\" ya da mahallelerden birinin adıdır (şemadaki listede yazıldığı gibi).")
    lines += ["- `aile` alanına kanal planındaki içerik ailesinin adını şemadaki listede yazıldığı gibi yaz.",
              f"- Her kanıt `{{\"dosya\": \"{summary}\", \"kimlik\": \"K0123\"}}` biçimindedir: kimlik o özette geçen bir K kimliğidir. "
              + ("İki özetin kimlikleri ayrıdır (her biri kendi paketinin); kimliği hangi özetten aldıysan o dosyayı yaz. " if region else "")
              + "Değerleri program özetin paketinden okur.",
              f"- Kancanın en az bir kanıtı olsun. İçerik planında en az {title.MIN_SECTIONS} bölüm olsun ve her bölüm en az bir kanıta dayansın.",
              "- `sablon` alanına `sablonlar.md`'deki bir şablonun anahtarını, `parametreler` alanına parametrelerini yaz (parametre değeri "
              "mahallenin kimliğidir); öneri mevcut bir şablonla kurulamıyorsa `sablon` null, `yeni_sablon_gerekir` true olur.",
              f"- İngilizce başlık en çok {title.MAX_TITLE} karakterdir"
              + (" (ek dahil); İngilizce başlık `secim.md`'deki İngilizce ekle, Türkçe karşılığı oradaki Türkçe ekle biter." if title.suffix_lines(params) else "."),
              "- Türkçe karşılık İngilizce başlığın birebir çevirisidir.",
              "- Başlıklar birbirini ve `onceki_oneriler.md`'dekileri tekrar etmez; büyük-küçük harf ve noktalama farkı tekrar sayılır.",
              "- Bitirince kısa bir Türkçe özet yaz: fikir doluyor mu, kaç aday, önemli eksik veri."]
    if ctx.correction:
        lines += ["", "Düzeltme: kullanıcının notu aşağıda. Önceki çıktın `onceki_cikti.json` dosyasında. Notu uygula ve "
                      f"`{OUTPUT}`'u baştan ve eksiksiz yaz.", *steps.note_block(ctx.correction["note"])]
    return "\n".join(lines) + "\n"


def check(ctx, data):
    """The evaluation's own checks, then the title step's checks of every candidate."""
    problems = []
    candidates = data.get("adaylar") or []
    fill = data.get("doluluk") or {}
    if (data.get("kullanici_fikri") or "").strip() != ctx.params["kullanici_basligi"].strip():
        problems.append(title.problem(title.ERROR, "`kullanici_fikri` kullanıcının yazdığıyla aynı değil; aynen yazılmalı."))
    if len(candidates) > MAX_CANDIDATES:
        problems.append(title.problem(title.ERROR, f"En çok {MAX_CANDIDATES} aday olmalı; {len(candidates)} aday var."))
    if fill.get("dolar_mi") and not candidates:
        problems.append(title.problem(title.ERROR, f"Fikir veriyle doluyor denmiş ama aday yok; 1–{MAX_CANDIDATES} aday olmalı."))
    if fill.get("dolar_mi") is False and not fill.get("eksik_veri"):
        problems.append(title.problem(title.ERROR, "Fikir dolmuyor denmiş ama eksik veri yazılmamış."))
    return problems + title.candidate_problems(ctx, candidates)


def render(ctx, data, problems, chosen=None):
    chosen = chosen or {}
    params = ctx.params
    fill = data.get("doluluk") or {}
    candidates = [title.resolve_candidate(ctx, c) for c in data.get("adaylar") or []]
    lines = [f"# Başlık değerlendirmesi — {params['bolge']}", "", f"- Çalışma `{ctx.run_id}` · not: {params.get('not') or 'yok'}",
             "- Veri özetleri: " + ", ".join(f"`{name}` (paket {record['id'][:8]})" for name, record in ctx.packs.items()), "",
             "## Kullanıcının fikri", "", data.get("kullanici_fikri") or "", "",
             "## Değerlendirme", "", f"- Veriyle doluyor mu: {'evet' if fill.get('dolar_mi') else 'hayır'}", f"- Açıklama: {fill.get('aciklama')}"]
    missing = fill.get("eksik_veri") or []
    lines.append("- Eksik veri: " + ("; ".join(missing) if missing else "yok"))
    lines += ["", "## Kullanıcının ifadesindeki sorunlar", ""] + ([f"- {s}" for s in data.get("sorunlar") or []] or ["Yok."])
    if candidates:
        lines += ["", "## Adaylar", "", "| # | İngilizce başlık | Türkçe karşılığı | İçerik ailesi | Şablon |", "|---|---|---|---|---|"]
        cell = lambda text: str(text or "").replace("|", "\\|")
        for number, item in enumerate(candidates, 1):
            template = f"`{item['sablon']}`" if item.get("sablon") else "yeni şablon gerekir"
            mark = " (seçildi)" if (number - 1) in chosen else ""
            lines.append(f"| {number} | {cell(item.get('baslik_en'))}{mark} | {cell(item.get('baslik_tr'))} | {cell(item.get('aile'))} | {template} |")
    else:
        lines += ["", "## Adaylar", "", "Aday yok (fikir veriyle dolmuyor)."]
    if problems:
        lines += ["", "## Doğrulama sorunları", ""]
        lines += [f"- {'Hata' if p['seviye'] == title.ERROR else 'Uyarı'}{f' · aday {p['aday'] + 1}' if p['aday'] is not None else ''}: {p['metin']}"
                  for p in problems]
    if data.get("notlar"):
        lines += ["", "## Claude'un notları", ""] + [f"- {n}" for n in data["notlar"]]
    for number, item in enumerate(candidates, 1):
        lines += title.candidate_lines(number, item)
    return "\n".join(lines).rstrip() + "\n"


def summary(data):
    """For the job panel and the run list."""
    fill = data.get("doluluk") or {}
    return {"kullanici_fikri": data.get("kullanici_fikri"), "doluluk": fill, "sorunlar": data.get("sorunlar") or []}


NO_CANDIDATES_TEXT = "Değerlendirildi: veriyle dolmuyor"


def without_candidates(data_dir, record):
    """GÖREV-15 Adım 1d: an evaluation waiting for approval that wrote no candidate ("veriyle dolmuyor") has nothing to approve. It is not
    counted as waiting in the workflow and is shown as information; "Reddet" still closes it. Read from the run's output file."""
    if record.get("step") != STEP_KEY or record.get("status") != "awaiting_approval":
        return False
    try:
        data = json.loads((Path(data_dir) / record["folder"] / OUTPUT).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return isinstance(data, dict) and not (data.get("adaylar") or [])


def source_note(view, candidate, edited_tr):
    """The note of an "İngilizcesini Claude yazsın" run (Adım 5b): the candidate was edited, with its analysis."""
    plan = "; ".join(f"{n}) {p.get('bolum')} — {p.get('ne_anlatir')}" for n, p in enumerate(candidate.get("icerik_plani") or [], 1))
    text = "\n".join([
        "Bu aday düzenlendi: kullanıcı yalnız Türkçe karşılığı değiştirdi; düzenlediği Türkçe başlık kullanici_basligi.md dosyasında. "
        "İngilizce başlığı bu Türkçe başlığın birebir karşılığı olarak yaz.",
        f"Önerilen İngilizce başlık: {candidate.get('baslik_en')}",
        f"Önerilen Türkçe karşılık: {candidate.get('baslik_tr')}",
        f"Kullanıcının Türkçe başlığı: {edited_tr}",
        "Adayın analizi:",
        f"- Bölge ve aile: {candidate.get('bolge')} · {candidate.get('aile')}",
        f"- Neden önerildi: {candidate.get('neden_onerildi')}",
        f"- İzleyicinin sorusu: {candidate.get('izleyici_sorusu')}",
        f"- Kanca: {(candidate.get('kanca') or {}).get('metin')}",
        f"- İçerik planı: {plan}",
        f"- Şablon: {candidate.get('sablon') or 'yok'} {json.dumps(candidate.get('parametreler') or {}, ensure_ascii=False)}",
        f"- Kaynak çalışma: {view['id']} · aday {candidate['sira'] + 1}"])
    return text


STEP = steps.register(steps.Step(key=STEP_KEY, title="Başlık değerlendirme",
                                 instructions=("ortak.md", "baslik_degerlendirme.md"), schema="baslik_degerlendirme.schema.json",
                                 output=OUTPUT, markdown=MARKDOWN, prepare=prepare, task=task, fill_schema=title.fill_schema, check=check,
                                 render=render))
