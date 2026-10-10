"""The first Claude step (GÖREV-13): topic and title proposals ("Konu ve başlık").

Generic for any destination with a channel definition (`profile.CHANNEL`: content families, channel plan and research, the "whole
destination" region name, the general and the per-region evidence template). The instruction texts (`ortak.md`, `baslik.md`) are the
destination's; this module only builds the inputs, the task text, the run's schema lists, the checks and the readable Markdown.

Inputs the program puts into the run folder: `kanal_plani.md` (the concept document, with the channel and content plan), `kanal_arastirmasi.md`,
`secim.md` (the user's region, content family and note), `veri_ozeti_30a.md` (the general template's writer's summary), `veri_ozeti_mahalle.md`
(only when a neighborhood is chosen: its template's writer's summary), `sablonlar.md` (the templates the program can build packs with, from
the template files) and `onceki_oneriler.md` (every title proposed before, chosen ones marked). A summary's pack is produced again when it is
older than the data's last run (or other code or profile files made it); otherwise the stored pack is reused.

Evidence is cited as {"dosya": <summary file>, "kimlik": "K0123"}: K identifiers belong to one pack, so the file says which.
"""
import json
import re
import shutil
import unicodedata

from .. import evidence
from ..evidence import video as V
from ..evidence.templates import TemplateError, resolve
from . import steps

OUTPUT, MARKDOWN = "baslik.json", "baslik.md"
GENERAL_SUMMARY, REGION_SUMMARY = "veri_ozeti_30a.md", "veri_ozeti_mahalle.md"
ALL_FAMILIES = "hepsi"
MIN_CANDIDATES, MAX_CANDIDATES = 8, 12
MIN_FAMILIES = 4
MIN_SECTIONS = 5
MAX_TITLE = 100
ERROR, WARNING = "hata", "uyari"


def channel(profile):
    found = getattr(profile, "CHANNEL", None)
    if not found:
        raise steps.StepError("Bu destinasyonun kanal tanımı yok; konu ve başlık önerisi alınamaz.")
    return found


def normalized(title):
    """A title compared without case, punctuation or extra spaces."""
    text = "".join(" " if unicodedata.category(ch).startswith(("P", "S")) else ch for ch in unicodedata.normalize("NFKC", title or "").casefold())
    return " ".join(text.split())


# ------------------------------------------------------------------------------------------------------------------- inputs

def selection_text(ctx):
    params = ctx.params
    region = (f"{params['bolge']} (mahalle kimliği: `{params['bolge_id']}`; bu mahallenin özeti `{REGION_SUMMARY}` dosyasında)"
              if params.get("bolge_id") else f"{params['bolge']} (bütün destinasyon; mahalle özeti verilmedi)")
    family = params.get("aile") or ALL_FAMILIES
    return "\n".join(["# Bu çalışmanın seçimi", "", f"- Bölge: {region}", f"- İçerik ailesi: {family}", f"- Not: {params.get('not') or 'yok'}", ""])


def templates_text(ctx):
    templates = evidence.destination_templates(ctx.profile)
    lines = ["# Programın paket kurabildiği şablonlar", "",
             "Her şablon bir kanıt paketi kurar: paketin ve yazar özetinin bölümleri şablonun bölümleridir. Öneride `sablon` alanına şablonun "
             "anahtarını, `parametreler` alanına parametrelerini yazın.", ""]
    for key, template in templates.items():
        lines += [f"## `{key}` — {template['title']}", "", f"- Ana soru: {template['question']}"]
        if template["parameters"]:
            for parameter in template["parameters"]:
                choices = ", ".join(f"`{r['id']}` ({r['name']})" for r in ctx.regions)
                lines.append(f"- Parametre `{parameter['key']}` ({parameter.get('label') or parameter['key']}): destinasyonun mahallelerinden "
                             f"birinin kimliği: {choices}")
        else:
            lines.append("- Parametre yok (`{}`)")
        lines.append("- Bölümler:")
        lines += [f"  {n}. {s['title']} — {s['question']}" for n, s in enumerate(template["sections"], 1)]
        lines.append("")
    return "\n".join(lines)


def previous_titles(ctx):
    """Every title proposed before for the destination (runs with a valid output), chosen ones marked; the run being corrected and the
    runs of its own preparation are left out (a correction rewrites them)."""
    from . import store
    chosen = store.chosen_titles(ctx.db, ctx.destination["id"])
    scope = ctx.correction["run"]["scope_id"] if ctx.correction else None
    found = []
    for run in store.runs(ctx.db, ctx.destination["id"], "baslik"):
        if run["id"] == ctx.run_id or run["scope_id"] == scope or run["status"] not in ("awaiting_approval", "approved", "rejected"):
            continue
        path = ctx.db.path.parent / run["folder"] / OUTPUT
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for index, item in enumerate(data.get("adaylar") or []):
            if isinstance(item, dict) and item.get("baslik_en"):
                found.append({"baslik_en": item["baslik_en"], "baslik_tr": item.get("baslik_tr") or "", "bolge": item.get("bolge") or "",
                              "aile": item.get("aile") or "", "tarih": run["created_at"][:10], "secildi": (run["id"], index) in chosen,
                              "calisma": run["id"]})
    return found


def previous_text(items):
    lines = ["# Daha önce önerilen başlıklar", ""]
    if not items:
        return "\n".join(lines + ["Henüz önerilmiş başlık yok.", ""])
    lines += ["Bunları ve bunlara çok benzeyenleri tekrar önerme. \"seçildi\" yazanlar kullanıcının video için seçtikleridir.", "",
              "| Tarih | Bölge | İçerik ailesi | İngilizce başlık | Türkçe karşılığı | Durum |", "|---|---|---|---|---|---|"]
    cell = lambda text: str(text).replace("|", "\\|")
    lines += [f"| {i['tarih']} | {cell(i['bolge'])} | {cell(i['aile'])} | {cell(i['baslik_en'])} | {cell(i['baslik_tr'])} | "
              f"{'seçildi' if i['secildi'] else '—'} |" for i in items]
    return "\n".join(lines + [""])


def summary_input(ctx, name, template_key, values, label):
    record, reason = evidence.fresh_pack(ctx.db, ctx.destination["id"], ctx.profile, template_key, values, log=ctx.say)
    if reason is None:
        ctx.say(f"Veri özeti güncel ({label}; paket {record['id'][:8]}).")
    path, _ = evidence.stored_file(ctx.db, record["id"], "yazar_ozeti")
    shutil.copyfile(path, ctx.folder / name)
    pack_path, _ = evidence.stored_file(ctx.db, record["id"], "json")
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    ctx.packs[name] = record
    ctx.pack_rows[name] = {row["id"]: row for section in pack["sections"] for row in section["rows"]}
    return {"dosya": name, "aciklama": label, "paket_id": record["id"], "paket_uretildi": reason}


def prepare(ctx):
    found = channel(ctx.profile)
    inputs = []
    for name, source, label in (("kanal_plani.md", found["plan"], "kanal planı"), ("kanal_arastirmasi.md", found["research"], "kanal araştırması")):
        shutil.copyfile(source, ctx.folder / name)
        inputs.append({"dosya": name, "aciklama": label})
    (ctx.folder / "secim.md").write_text(selection_text(ctx), encoding="utf-8")
    inputs.append({"dosya": "secim.md", "aciklama": "kullanıcının seçimi"})
    inputs.append(summary_input(ctx, GENERAL_SUMMARY, found["general_template"], {}, "30A verisinin yazar özeti"))
    if ctx.params.get("bolge_id"):
        inputs.append(summary_input(ctx, REGION_SUMMARY, found["region_template"], {found["region_parameter"]: ctx.params["bolge_id"]},
                                    f"{ctx.params['bolge']} yazar özeti"))
    (ctx.folder / "sablonlar.md").write_text(templates_text(ctx), encoding="utf-8")
    inputs.append({"dosya": "sablonlar.md", "aciklama": "şablonlar"})
    ctx.previous = previous_titles(ctx)
    (ctx.folder / "onceki_oneriler.md").write_text(previous_text(ctx.previous), encoding="utf-8")
    inputs.append({"dosya": "onceki_oneriler.md", "aciklama": f"önceki öneriler ({len(ctx.previous)} başlık)"})
    if ctx.correction:
        (ctx.folder / "onceki_cikti.json").write_text(json.dumps(ctx.correction.get("data") or {}, ensure_ascii=False, indent=1), encoding="utf-8")
        inputs.append({"dosya": "onceki_cikti.json", "aciklama": "düzeltilecek önceki çıktı"})
    return inputs


# ------------------------------------------------------------------------------------------------------------------- task

def task(ctx):
    found = channel(ctx.profile)
    params = ctx.params
    region = params.get("bolge_id")
    family = params.get("aile") or ALL_FAMILIES
    lines = ["Adım: baslik", f"Tür: {'düzeltme' if ctx.correction else 'ilk çalışma'}", f"Bölge: {params['bolge']}", f"İçerik ailesi: {family}",
             f"Not: {params.get('not') or 'yok'}", "",
             "Görev: kanalın bir sonraki videosu için konu ve başlık önerileri hazırla (sistem metnindeki \"Konu ve başlık önerisi\").", "",
             "Çalışma klasöründeki dosyalar (hepsini oku):",
             "- `secim.md` — kullanıcının bu çalışma için seçtiği bölge, içerik ailesi ve notu.",
             "- `kanal_plani.md` — kanal planı: içerik aileleri, konu motoru, ilkeler.",
             "- `kanal_arastirmasi.md` — kanal araştırması: rakip videolar, izleyicinin soruları.",
             f"- `{GENERAL_SUMMARY}` — 30A verisinin yazar özeti (paket {ctx.packs[GENERAL_SUMMARY]['id'][:8]}).",
             *([f"- `{REGION_SUMMARY}` — {params['bolge']} mahallesinin yazar özeti (paket {ctx.packs[REGION_SUMMARY]['id'][:8]})."] if region else []),
             "- `sablonlar.md` — programın paket kurabildiği şablonlar.",
             "- `onceki_oneriler.md` — daha önce önerilen başlıklar.",
             *(["- `onceki_cikti.json` — düzelteceğin önceki çıktın."] if ctx.correction else []), "",
             "Çıktı:",
             f"- `{OUTPUT}` — şema: sistem talimatının sonundaki \"Çıktı şeması\" bölümü. Okunur Markdown'ı program üretir; sen Markdown yazma.", "",
             "Kurallar:",
             f"- Yalnız bu klasördeki dosyaları oku; yalnız `{OUTPUT}`'u yaz. Başka hiçbir dosyayı oluşturma ya da değiştirme.",
             f"- {MIN_CANDIDATES}–{MAX_CANDIDATES} aday yaz."]
    if region:
        lines.append(f"- Bütün adaylar {params['bolge']} hakkında olur; her adayın `bolge` alanı \"{params['bolge']}\" olur.")
    else:
        lines.append(f"- Adayın `bolge` alanı \"{found['whole_region']}\" ya da mahallelerden birinin adıdır (şemadaki listede yazıldığı gibi).")
    if family != ALL_FAMILIES:
        lines.append(f"- Bütün adaylar \"{family}\" ailesinden olur.")
    elif not region:
        lines.append(f"- Adaylar en az {MIN_FAMILIES} farklı içerik ailesine dağılır.")
    lines += ["- `aile` alanına kanal planındaki içerik ailesinin adını şemadaki listede yazıldığı gibi yaz.",
              f"- Her kanıt `{{\"dosya\": \"{GENERAL_SUMMARY}\", \"kimlik\": \"K0123\"}}` biçimindedir: kimlik o özette geçen bir K kimliğidir. "
              + (f"İki özetin kimlikleri ayrıdır (her biri kendi paketinin); kimliği hangi özetten aldıysan o dosyayı yaz. " if region else "")
              + "Değerleri program özetin paketinden okur.",
              f"- Kancanın en az bir kanıtı olsun. İçerik planında en az {MIN_SECTIONS} bölüm olsun ve her bölüm en az bir kanıta dayansın.",
              "- `sablon` alanına `sablonlar.md`'deki bir şablonun anahtarını, `parametreler` alanına parametrelerini yaz (parametre değeri "
              "mahallenin kimliğidir); öneri mevcut bir şablonla kurulamıyorsa `sablon` null, `yeni_sablon_gerekir` true olur.",
              f"- İngilizce başlık en çok {MAX_TITLE} karakterdir.",
              "- Başlıklar birbirini ve `onceki_oneriler.md`'dekileri tekrar etmez; büyük-küçük harf ve noktalama farkı tekrar sayılır.",
              "- Bitirince kısa bir Türkçe özet yaz: kaç aday, hangi aileler, önemli eksik veri."]
    if ctx.correction:
        lines += ["", "Düzeltme: kullanıcının notu aşağıda. Önceki çıktın `onceki_cikti.json` dosyasında. Notu uygula ve "
                      f"`{OUTPUT}`'u baştan ve eksiksiz yaz (değişmeyen adayları da).", *steps.note_block(ctx.correction["note"])]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------------------------------------- schema and checks

def fill_schema(ctx, schema):
    found = channel(ctx.profile)
    schema["$defs"]["aile"]["enum"] = list(found["families"])
    schema["$defs"]["bolge"]["enum"] = [found["whole_region"], *[r["name"] for r in ctx.regions]]
    files = [GENERAL_SUMMARY, *([REGION_SUMMARY] if ctx.params.get("bolge_id") else [])]
    schema["$defs"]["kanit"]["properties"]["dosya"]["enum"] = files
    return schema


def problem(level, text, index=None):
    return {"aday": index, "seviye": level, "metin": text}


def evidence_problems(ctx, items, index, where):
    found = []
    for item in items:
        rows = ctx.pack_rows.get(item.get("dosya"))
        if rows is None:
            found.append(problem(ERROR, f"{where}: {item.get('dosya')} bu çalışmada verilmedi ({item.get('kimlik')}).", index))
        elif item.get("kimlik") not in rows:
            found.append(problem(ERROR, f"{where}: var olmayan kanıt kimliği {item.get('kimlik')} ({item.get('dosya')}).", index))
        elif rows[item["kimlik"]].get("durum") != "var":
            found.append(problem(WARNING, f"{where}: {item['kimlik']} bir 'veri yok' satırı ({item['dosya']}).", index))
    return found


def check(ctx, data):
    """Meaning checks after the schema: count, families, region, evidence ids, plan, template, title length, repetitions."""
    found = channel(ctx.profile)
    params = ctx.params
    candidates = data.get("adaylar") or []
    problems = []
    if not MIN_CANDIDATES <= len(candidates) <= MAX_CANDIDATES:
        problems.append(problem(ERROR, f"{MIN_CANDIDATES}–{MAX_CANDIDATES} aday olmalı; {len(candidates)} aday var."))
    family = params.get("aile") or ALL_FAMILIES
    if not params.get("bolge_id") and family == ALL_FAMILIES:
        families = {c.get("aile") for c in candidates}
        if len(families) < MIN_FAMILIES:
            problems.append(problem(ERROR, f"Bölge \"{found['whole_region']}\" iken en az {MIN_FAMILIES} farklı içerik ailesi olmalı; "
                                           f"{len(families)} aile var."))
    templates = evidence.destination_templates(ctx.profile)
    region_ids = {r["name"]: r["id"] for r in ctx.regions}
    earlier = {normalized(p["baslik_en"]): p for p in ctx.previous}
    seen = {}
    for index, item in enumerate(candidates):
        if params.get("bolge_id") and item.get("bolge") != params["bolge"]:
            problems.append(problem(ERROR, f"Aday başka bir bölgeye ait ({item.get('bolge')}); bu çalışmanın bölgesi {params['bolge']}.", index))
        if family != ALL_FAMILIES and item.get("aile") != family:
            problems.append(problem(ERROR, f"Aday \"{item.get('aile')}\" ailesinden; bu çalışmada seçilen aile \"{family}\".", index))
        hook = item.get("kanca") or {}
        if not hook.get("kanitlar"):
            problems.append(problem(ERROR, "Kancanın kanıtı yok.", index))
        problems += evidence_problems(ctx, hook.get("kanitlar") or [], index, "Kanca")
        plan = item.get("icerik_plani") or []
        if len(plan) < MIN_SECTIONS:
            problems.append(problem(ERROR, f"İçerik planında en az {MIN_SECTIONS} bölüm olmalı; {len(plan)} bölüm var.", index))
        for number, part in enumerate(plan, 1):
            if not part.get("kanitlar"):
                problems.append(problem(ERROR, f"İçerik planının {number}. bölümü ({part.get('bolum')}) kanıtsız.", index))
            problems += evidence_problems(ctx, part.get("kanitlar") or [], index, f"İçerik planı {number}. bölüm")
        key, values = item.get("sablon"), item.get("parametreler") or {}
        if key is None:
            if not item.get("yeni_sablon_gerekir"):
                problems.append(problem(ERROR, "Şablon yok (null) ama yeni_sablon_gerekir doğru değil.", index))
        elif key not in templates:
            problems.append(problem(ERROR, f"Şablon yok: {key}.", index))
        else:
            template = templates[key]
            expected = {p["key"] for p in template["parameters"]}
            if set(values) != expected:
                problems.append(problem(ERROR, f"{key} şablonunun parametreleri {sorted(expected) or 'yok'}; adayda {sorted(values) or 'yok'}.", index))
            else:
                try:
                    resolve(template, values, ctx.regions)
                except TemplateError as exc:
                    problems.append(problem(ERROR, f"{key} şablonunun parametresi geçersiz: {exc}", index))
                region = region_ids.get(item.get("bolge"))
                if region and expected and region not in values.values():
                    problems.append(problem(ERROR, f"Şablon parametresi adayın bölgesiyle uyuşmuyor ({values}; bölge {item.get('bolge')}).", index))
            if item.get("yeni_sablon_gerekir"):
                problems.append(problem(WARNING, f"Şablon {key} verilmiş ama yeni şablon gerektiği de yazılmış.", index))
        title = item.get("baslik_en") or ""
        if len(title) > MAX_TITLE:
            problems.append(problem(ERROR, f"İngilizce başlık {MAX_TITLE} karakteri aşıyor ({len(title)} karakter).", index))
        key_title = normalized(title)
        if key_title in seen:
            problems.append(problem(ERROR, f"Başlık {seen[key_title] + 1}. adayın başlığını tekrar ediyor.", index))
        else:
            seen[key_title] = index
        if key_title in earlier:
            before = earlier[key_title]
            problems.append(problem(ERROR, f"Başlık daha önce önerildi ({before['tarih']}, {before['bolge']}): {before['baslik_en']}", index))
    return problems


# ------------------------------------------------------------------------------------------------------------------- evidence values and Markdown

def resolved(ctx, item):
    rows = ctx.pack_rows.get(item.get("dosya")) or {}
    row = rows.get(item.get("kimlik"))
    record = ctx.packs.get(item.get("dosya")) or {}
    if row is None:
        return {**item, "paket_id": record.get("id"), "ifade": None, "deger_metni": None, "durum": "bulunamadi"}
    return V.cited(row, dosya=item["dosya"], pack_id=record.get("id"))


def resolve_candidate(ctx, item):
    """The candidate with every cited row's statement and value (from its pack)."""
    hook = item.get("kanca") or {}
    return {**item, "kanca": {**hook, "kanitlar": [resolved(ctx, k) for k in hook.get("kanitlar") or []]},
            "icerik_plani": [{**p, "kanitlar": [resolved(ctx, k) for k in p.get("kanitlar") or []]} for p in item.get("icerik_plani") or []]}


def evidence_text(item):
    if item.get("durum") == "bulunamadi":
        return f"{item.get('kimlik')} ({item.get('dosya')}): bulunamadı"
    label = {"kaynak gerçeği": "KG", "bizim hesabımız": "BH", "türetilmiş": "T", "yaklaşık": "Y"}.get(item.get("etiket"), "—")
    return f"{item['kimlik']} ({item['dosya']}) [{label}] {item.get('ifade') or ''} — {item.get('deger_metni')}"


def render(ctx, data, problems, chosen=None):
    chosen = chosen or {}
    params = ctx.params
    candidates = [resolve_candidate(ctx, c) for c in data.get("adaylar") or []]
    lines = [f"# Konu ve başlık önerileri — {params['bolge']} · {params.get('aile') or ALL_FAMILIES}", "",
             f"- Çalışma `{ctx.run_id}` · not: {params.get('not') or 'yok'}",
             "- Veri özetleri: " + ", ".join(f"`{name}` (paket {record['id'][:8]})" for name, record in ctx.packs.items()), ""]
    lines += ["## Başlıklar", "", "| # | İngilizce başlık | Türkçe karşılığı | İçerik ailesi | Şablon |", "|---|---|---|---|---|"]
    cell = lambda text: str(text or "").replace("|", "\\|")
    for number, item in enumerate(candidates, 1):
        template = f"`{item['sablon']}`" if item.get("sablon") else "yeni şablon gerekir"
        mark = " (seçildi)" if (number - 1) in chosen else ""
        lines.append(f"| {number} | {cell(item.get('baslik_en'))}{mark} | {cell(item.get('baslik_tr'))} | {cell(item.get('aile'))} | {template} |")
    if problems:
        lines += ["", "## Doğrulama sorunları", ""]
        lines += [f"- {'Hata' if p['seviye'] == ERROR else 'Uyarı'}{f' · aday {p['aday'] + 1}' if p['aday'] is not None else ''}: {p['metin']}"
                  for p in problems]
    if data.get("notlar"):
        lines += ["", "## Claude'un notları", ""] + [f"- {n}" for n in data["notlar"]]
    for number, item in enumerate(candidates, 1):
        hook = item.get("kanca") or {}
        lines += ["", f"## {number}. {item.get('baslik_en')}", "", f"Türkçe: {item.get('baslik_tr')}", "",
                  f"- Bölge: {item.get('bolge')} · İçerik ailesi: {item.get('aile')}", "",
                  f"**Neden önerildi:** {item.get('neden_onerildi')}", "", f"**İzleyicinin sorusu:** {item.get('izleyici_sorusu')}", "",
                  f"**Kanca:** {hook.get('metin')}", ""]
        lines += [f"- {evidence_text(k)}" for k in hook.get("kanitlar") or []] or ["- —"]
        lines += ["", "**İçerik planı**", ""]
        for part_number, part in enumerate(item.get("icerik_plani") or [], 1):
            lines.append(f"{part_number}. **{part.get('bolum')}** — {part.get('ne_anlatir')}")
            lines += [f"   - {evidence_text(k)}" for k in part.get("kanitlar") or []] or ["   - (kanıt yok)"]
        missing = item.get("eksik_veri") or []
        lines += ["", "**Eksik veri:** " + ("; ".join(missing) if missing else "yok"), ""]
        if item.get("sablon"):
            values = ", ".join(f"{k} = {v}" for k, v in (item.get("parametreler") or {}).items()) or "yok"
            lines.append(f"**Şablon:** `{item['sablon']}` · parametreler: {values}" + (" (yeni şablon da gerektiği yazılmış)" if item.get("yeni_sablon_gerekir") else ""))
        else:
            lines.append("**Şablon:** yok; yeni şablon gerekir")
        lines += ["", f"**Kapak fikri:** {item.get('kapak_fikri')}"]
    return "\n".join(lines).rstrip() + "\n"


STEP = steps.register(steps.Step(key="baslik", title="Konu ve başlık", instructions=("ortak.md", "baslik.md"), schema="baslik.schema.json",
                                 output=OUTPUT, markdown=MARKDOWN, prepare=prepare, task=task, fill_schema=fill_schema, check=check,
                                 render=render))
