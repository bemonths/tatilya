"""The video text's estimate before a run starts (GÖREV-18 Adım 4.1): the plan and every chosen tone on their own lines, and the total.

Calls: the plan is two calls (planner and critic); a tone is one call per section, the merger, the introduction and closing, the final
reader and one call per translation chunk. A second try of an invalid answer, a plan sent back by the program's check or by the critic,
and transient failures are not counted (the screen says a call may be asked once more).

Read tokens of a call: its combined instructions are measured exactly (the common file, the voice and the tone for the writing steps, the
step's file, the schema); of its input files, the ones that exist before the run are measured exactly (the title analysis, the pack's
writer's summary, the numbers, the channel plan, the published videos; with a known plan also the plan and every section's file). The
others are written during the run; for them the median read tokens of the step's earlier one-call sessions is used, or a size worked out
from the plan's word budget (`WORDS_*`, `TOKENS_PER_WORD`). Written tokens: `budget.output_estimate` (median of earlier calls, or the
output guess of Settings).
"""
import json
import math
from pathlib import Path

from ..ai import budget, settings as claude_settings, single, steps, tones as T
from ..ai import text_steps as TS
from ..evidence import stored_file

DEFAULT_SECTIONS = 6
WORDS_BODY = 2_200            # the plan's word budget (metin_plan.md: 2,000–2,200) plus transitions
WORDS_ENDS = 350              # introduction and closing
TOKENS_PER_WORD = 1.9         # English with evidence marks [K0123] and the markers of the text files
PLAN_JSON_CHARS = 9_000       # a 6-section plan as JSON (sections, ids, concepts, re-hooks, promise check)


def system_chars(step, ctx_like, tone):
    rctx = steps.RunContext(db=None, profile=ctx_like.profile, destination=None, run_id="tahmin", folder=Path("."), params={}, regions=[],
                            tone=tone if step.voice else None, extra={})
    schema = steps.run_schema(step, rctx)
    return len(steps.combined_instructions(step, rctx, schema))


def task_chars(step_key, files, extra):
    """The task lines and file sections as the chain would write them (the files given here by their text)."""
    rctx = steps.RunContext(db=None, profile=None, destination=None, run_id="tahmin", folder=Path("."), params={}, regions=[],
                            extra={**extra, "files": files})
    task = TS.task_lines(step_key, rctx)
    return len(single.task_text(task, list(files.items())))


class Estimator:
    def __init__(self, service, ctx_like, settings):
        self.service, self.ctx, self.settings, self.db = service, ctx_like, settings, service.db

    def call(self, step_key, read, basis="istemin boyutu"):
        return budget.call_estimate(self.db, self.settings, step_key, read, read_basis=basis)

    def measured(self, step_key, files, tone=None, extra=None):
        step = steps.get(step_key)
        chars = system_chars(step, self.ctx, tone) + task_chars(step_key, files, extra or {})
        return self.call(step_key, single.tokens_of(chars) + single.OVERHEAD_TOKENS)

    def guessed(self, step_key, known_files, unknown_tokens, tone=None, extra=None):
        """A call with files written during the run: the median read of earlier sessions, else the known part measured plus a guess."""
        median = budget.read_median(self.db, step_key)
        if median:
            return self.call(step_key, median, "önceki oturumların ortancası")
        step = steps.get(step_key)
        chars = system_chars(step, self.ctx, tone) + task_chars(step_key, known_files, extra or {})
        return self.call(step_key, single.tokens_of(chars) + unknown_tokens + single.OVERHEAD_TOKENS, "istemin bilinen kısmı ve boyut tahmini")


def words_tokens(words):
    return int(words * TOKENS_PER_WORD)


def estimate(service, video, tones, *, plan=None, plan_done=False):
    """The estimate of a text run: {"satirlar", "toplam", "sinirlar", "asiyor", "baslatilabilir", "metin"} (`budget.summary`).
    `tones`: [{"dosya", "ad"}]; `plan`: the run's final plan when it is known ("Bu tonla da yaz"); `plan_done`: no plan calls."""
    settings = service.settings()
    profile = service.profile_of(video["destination_id"])
    pack, summary_raw, numbers_text = pack_texts(service, video)
    from .engine import summary_for_claude

    class Like:
        pass
    ctx = Like()
    ctx.profile, ctx.video, ctx.pack, ctx.plan = profile, video, pack, plan
    summary_text = summary_for_claude(summary_raw)
    analysis = service.title_analysis(ctx)
    est = Estimator(service, ctx, settings)
    base_files = {"baslik_analizi.md": analysis, "paket_ozeti.md": summary_text, "sayilar.csv": numbers_text}
    rows = []
    title = video["title_en"]
    if not plan_done:
        planner = est.measured("metin_plan", {**base_files, "kanal_plani.md": service.channel_plan(ctx)}, extra={"video_title": title})
        if plan:
            critic = est.measured("metin_plan_elestiri", {"plan.json": json.dumps(plan, ensure_ascii=False, indent=1) + "\n", **base_files},
                                  extra={"video_title": title})
        else:
            critic = est.guessed("metin_plan_elestiri", base_files, single.tokens_of(PLAN_JSON_CHARS), extra={"video_title": title})
        rows.append(line("Plan", [planner, critic], settings, "metin_plan"))
    head = (video.get("analysis") or {}).get("icerik_plani") or []
    sections = sorted(plan["bolumler"], key=lambda s: s["no"]) if plan else None
    count = len(sections) if sections else min(7, max(5, len(head))) if head else DEFAULT_SECTIONS
    plan_text = json.dumps(plan, ensure_ascii=False, indent=1) + "\n" if plan else None
    plan_tokens = single.tokens_of(len(plan_text)) if plan_text else single.tokens_of(PLAN_JSON_CHARS)
    words = sum(s.get("kelime_butcesi") or 0 for s in sections) if sections else WORDS_BODY
    body_tokens, text_tokens = words_tokens(words), words_tokens(words + WORDS_ENDS)
    chunks = max(1, math.ceil((words + WORDS_ENDS) / 6000))
    known = T.tone_files(profile)
    paths = {p.stem: p for p in known}
    for tone in tones:
        info = {"dosya": tone["dosya"], "ad": tone["ad"], "path": str(paths[tone["dosya"]]) if tone["dosya"] in paths else None}
        if info["path"] is None:
            continue
        calls = []
        for number in range(1, count + 1):
            extra = {"video_title": title, "section": number}
            if sections:
                ctx.plan = plan
                files = {"plan.json": plan_text, "bolum.md": service.section_file(ctx, sections[number - 1])}
                calls.append(est.measured("metin_bolum", files, tone=info, extra=extra))
            else:
                calls.append(est.guessed("metin_bolum", {}, plan_tokens + single.tokens_of(len(summary_text)) // count * 2, tone=info, extra=extra))
        calls.append(est.guessed("metin_birlestirme", {"plan.json": plan_text} if plan_text else {}, body_tokens + (0 if plan_text else plan_tokens),
                                 tone=info, extra={"video_title": title}))
        calls.append(est.guessed("metin_giris_kapanis", {"baslik_analizi.md": analysis, "yayinlanan_videolar.md": service.published(ctx)},
                                 body_tokens, tone=info, extra={"video_title": title}))
        calls.append(est.guessed("metin_son_okuma", {"paket_ozeti.md": summary_text}, text_tokens, tone=info, extra={"video_title": title}))
        for index in range(1, chunks + 1):
            calls.append(est.guessed("metin_ceviri", {}, text_tokens // chunks, tone=info,
                                     extra={"video_title": title, "chunk": (index, chunks) if chunks > 1 else None}))
        rows.append(line(tone["ad"], calls, settings, "metin_bolum", tone=tone["dosya"]))
    return budget.summary(rows, settings, retries=1)


def line(title, calls, settings, model_step, tone=None):
    models = sorted({(budget.model_text(settings, c["adim"])["model_adi"]) for c in calls})
    return {"baslik": title, "ton": tone, "cagri": len(calls), "okunan": sum(c["okunan"] for c in calls), "yazilan": sum(c["yazilan"] for c in calls),
            "toplam": sum(c["toplam"] for c in calls), "en_buyuk_cagri": max(c["toplam"] for c in calls), "cagrilar": calls,
            "modeller": [{"adim": c["adim"], **budget.model_text(settings, c["adim"])} for c in dedupe(calls)], "model_adi": ", ".join(models)}


def dedupe(calls):
    seen, out = set(), []
    for call in calls:
        if call["adim"] not in seen:
            seen.add(call["adim"])
            out.append(call)
    return out


def pack_texts(service, video):
    """(pack, writer's summary, numbers) the estimate measures: the video's newest stored pack (the run makes it again when it is older
    than the last collection; its size changes little); without one, a pack built in memory exactly as the run would build it (nothing is
    stored: the estimate leaves no trace)."""
    from ..ai import store as ai_store
    from ..destinations import PROFILES
    from ..evidence import pack as P, plan as plan_pack, summary as S
    packs = (next((v for v in ai_store.videos(service.db, video["destination_id"]) if v["id"] == video["id"]), None) or {}).get("packs") or []
    if packs:
        record = packs[0]
        path, _ = stored_file(service.db, record["id"], "json")
        summary_path, _ = stored_file(service.db, record["id"], "yazar_ozeti")
        numbers_path, _ = stored_file(service.db, record["id"], "sayilar")
        return (json.loads(path.read_text(encoding="utf-8")), summary_path.read_text(encoding="utf-8"),
                numbers_path.read_text(encoding="utf-8"))
    built = plan_pack.build(service.db, video["destination_id"], PROFILES.get(video["destination_id"]), video)
    return built, S.render(built), P.checklist_csv(built)
