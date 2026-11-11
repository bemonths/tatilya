"""Claude runs of the app (GÖREV-13): one at a time, in the background, shown in the job panel; the approval decisions and video records.

A run's folder is `<data>/claude/<preparation or video id>/<step>/<run id>/` and holds the inputs, the combined instructions (`talimat.md`),
the run's schema (`sema.json`), the task text (`gorev.md`), the stream (`akis.jsonl`), Claude's JSON output, the program's Markdown and the run
record (`calisma.json`). Nothing is deleted; a correction opens a new run (new folder, new session) with the user's note and the previous
output in its task text. A title proposal belongs to a preparation (its first run's id); a chosen title becomes a video record.

The run record keeps the SHA-256 of every instruction file and of the core schema (and of the combined instructions and the filled schema),
the inputs with their packs, the model, effort, Claude Code version, session id, turns, tool calls, tokens and cost equivalent.
"""
import json
import statistics
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from ..database import Conflict
from ..destinations import PROFILES
from ..evidence import PackError, store as store_pack
from ..evidence import plan as plan_pack
from . import budget, claude_info, instructions, runner, settings as claude_settings, single, steps, store, usage
from . import title  # noqa: F401  (registers the title step)
from . import title_review  # noqa: F401  (registers the evaluation step, GÖREV-14)

RUN_RECORD, STREAM, INSTRUCTIONS, TASK, RUN_SCHEMA = "calisma.json", "akis.jsonl", "talimat.md", "gorev.md", "sema.json"
JOB_KIND = "claude_run"
MAX_NOTE = 4000
# GÖREV-14 (Adım 4b): a Claude run's bar moves through stages: inputs 0–10 %, Claude 10–90 % (elapsed time over the median duration of
# the step's earlier successful runs, or the step's default when there is none; never past 90 %), validation and Markdown 90–100 %.
DEFAULT_SECONDS = {"baslik": 420, "baslik_degerlendirme": 300}
FALLBACK_SECONDS = 420
MEDIAN_OF = 9
DONE_STATUSES = ("awaiting_approval", "approved", "rejected")


def claude_percent(elapsed, expected):
    return 10 + min(80, int(80 * max(0.0, elapsed) / max(1.0, expected)))


def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def minutes_text(seconds):
    minutes = max(1, round(seconds / 60))
    return f"{minutes} dk"


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def sha256_of(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def schema_errors_of(schema, data):
    from .schema import errors
    return errors(schema, data)


def combined_metrics(calls, estimate):
    """The run's metrics (GÖREV-18): its one or two calls summed (tokens, cost, time), `cagri` their number, the estimate beside them."""
    items = [r.metrics() for r in calls]
    tokens = {}
    for m in items:
        for key, value in (m.get("tokens") or {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                tokens[key] = tokens.get(key, 0) + value
    last = dict(items[-1]) if items else {}
    last.update({"elapsed_s": round(sum(m.get("elapsed_s") or 0 for m in items), 1), "turns": len(items), "cagri": len(items),
                 "tool_calls": sum(m.get("tool_calls") or 0 for m in items), "duzen": budget.ONE_CALL, "tahmin": estimate,
                 "tokens": {**tokens, "source": (last.get("tokens") or {}).get("source", "result")} if tokens else None,
                 "cost_usd": round(sum(m.get("cost_usd") or 0 for m in items), 6) if any(m.get("cost_usd") for m in items) else None})
    return last


def spending_record(spend):
    """{"tahmin", "gercek", "karsilastirma"} for the job, the run record and the screens."""
    if not spend.get("tahmin"):
        return None
    return {"tahmin": spend["tahmin"], "gercek": spend.get("gercek"),
            "karsilastirma": single.comparison(spend["tahmin"], spend.get("gercek"))}


class ClaudeService:
    def __init__(self, db, data_dir):
        self.db, self.data_dir = db, Path(data_dir)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="30a-claude")
        self.closing = False
        self.refreshing = False
        self.lock = threading.Lock()
        self.text = None            # GÖREV-15: the video text's service (set by the app); while it works no other Claude run starts

    # ------------------------------------------------------------------------------------------------------------- options

    def regions(self, destination_id):
        return [{"id": r["id"], "name": r["name"]} for r in self.db.context(destination_id).canonical_regions]

    def options(self, destination_id):
        profile = PROFILES.get(destination_id)
        channel = getattr(profile, "CHANNEL", None) or {}
        return {"available": bool(channel), "whole_region": channel.get("whole_region"), "regions": self.regions(destination_id),
                "families": list(channel.get("families") or ()), "all_families": title.ALL_FAMILIES, "steps": [
                    {"key": s.key, "title": s.title} for s in steps.ordered()], "claude": claude_info.info(self.settings()["claude_path"])}

    def settings(self):
        return claude_settings.load(self.data_dir)

    def selection(self, destination_id, region, family, note):
        """The user's choices checked: region "<whole>" or one of the neighborhoods (id or name), a content family or all, a short note."""
        profile = PROFILES.get(destination_id)
        channel = title.channel(profile)
        regions = self.regions(destination_id)
        if region in (channel["whole_region"], "", None):
            if not region:
                raise Conflict("Önce bölge seçin.")
            chosen = {"bolge": channel["whole_region"], "bolge_id": None}
        else:
            match = next((r for r in regions if region in (r["id"], r["name"])), None)
            if match is None:
                raise Conflict("Bölge bu destinasyonun mahallelerinden biri ya da 30A geneli olmalı.")
            chosen = {"bolge": match["name"], "bolge_id": match["id"]}
        family = family or title.ALL_FAMILIES
        if family != title.ALL_FAMILIES and family not in channel["families"]:
            raise Conflict("İçerik ailesi kanal planındaki ailelerden biri ya da \"hepsi\" olmalı.")
        note = (note or "").strip()
        if len(note) > MAX_NOTE:
            raise Conflict(f"Not en çok {MAX_NOTE} karakter olabilir.")
        return {**chosen, "aile": family, "not": note}

    # ------------------------------------------------------------------------------------------------------------- starting a run

    def suffixes(self, destination_id):
        values = claude_settings.title_suffixes(self.data_dir, destination_id, PROFILES.get(destination_id))
        return {k: values[k] for k in ("en", "tr")}

    def start(self, destination_id, step_key, params, *, correction_of=None, note=None):
        step = steps.get(step_key)
        destination = self.db.destination(destination_id)
        params = {**params, "baslik_eki": self.suffixes(destination_id)}   # the suffixes as Settings has them now (GÖREV-14)
        previous = store.run(self.db, correction_of) if correction_of else None
        run_id = store.new_id()
        scope_id = previous["scope_id"] if previous else run_id[:12]
        folder = Path("claude") / scope_id / step.key / run_id
        label = params["bolge"] + (f" · {params['aile']}" if params.get("aile") not in (None, title.ALL_FAMILIES) else "")
        with self.lock:
            if self.closing:
                raise Conflict("Uygulama kapanıyor.")
            self.check_text_free()
            try:
                job_id = self.db.add_job(kind=JOB_KIND, title=f"Claude · {step.title}{' · düzeltme' if previous else ''} · {label}",
                                         destination_id=destination_id)
            except Conflict as exc:
                raise Conflict("Bir Claude çalışması zaten sürüyor; bitmesini bekleyin.") from exc
            try:
                with self.db.connect() as con:
                    store.insert_run(con, run_id=run_id, destination_id=destination_id, step=step.key, scope_id=scope_id, job_id=job_id,
                                     params={**params, **({"duzeltme_notu": note} if previous else {})}, folder=folder.as_posix(),
                                     correction_of=correction_of)
            except Conflict as exc:
                self.db.update_job(job_id, status="failed", message=str(exc))
                raise
            (self.db.path.parent / folder).mkdir(parents=True, exist_ok=True)
            self.executor.submit(self.work, run_id, destination, step, params, previous, note)
        return store.run(self.db, run_id)

    def start_title(self, destination_id, region, family, note):
        return self.start(destination_id, "baslik", self.selection(destination_id, region, family, note))

    def start_review(self, destination_id, region, user_title, note, *, source=None):
        """GÖREV-14 Adım 5a: the user's own title or idea, evaluated by Claude into 0–3 candidates."""
        text = (user_title or "").strip()
        if not text:
            raise Conflict("Değerlendirilecek başlığı ya da fikri yazın.")
        if len(text) > title_review.MAX_IDEA:
            raise Conflict(f"Başlık ya da fikir en çok {title_review.MAX_IDEA} karakter olabilir.")
        params = {**self.selection(destination_id, region, title.ALL_FAMILIES, note), "kullanici_basligi": text}
        if source:
            params["kaynak"] = source
        return self.start(destination_id, "baslik_degerlendirme", params)

    def translate(self, run_id, index, edited_tr):
        """GÖREV-14 Adım 5b: the user changed only the Turkish title of a candidate; Claude writes the English one in an evaluation run."""
        record = store.run(self.db, run_id)
        if record is None:
            raise KeyError(run_id)
        view = self.view(run_id)
        candidate = next((c for c in view["candidates"] if c["sira"] == index), None)
        if candidate is None:
            raise Conflict("Böyle bir aday yok.")
        edited = (edited_tr or "").strip()
        if not edited or edited == candidate["baslik_tr"].strip():
            raise Conflict("Türkçe başlık değişmedi; İngilizcesini yazdırmak için önce Türkçe karşılığı düzenleyin.")
        note = title_review.source_note(view, candidate, edited)[:MAX_NOTE]
        return self.start_review(record["destination_id"], candidate["bolge"], edited, note,
                                 source={"calisma": run_id, "aday": index, "baslik_en": candidate["baslik_en"],
                                         "baslik_tr": candidate["baslik_tr"]})

    # ------------------------------------------------------------------------------------------------------------- estimates (GÖREV-18)

    def estimate(self, destination_id, step_key, params, *, correction_of=None, note=None):
        """What a run would read and write, before it starts: the step's inputs are prepared in a temporary folder (the same files the run
        would give Claude; a stale summary pack is made again, as the run would), the task text built, its size measured. Nothing is sent."""
        step = steps.get(step_key)
        destination = self.db.destination(destination_id)
        params = {**params, "baslik_eki": self.suffixes(destination_id)}
        previous = store.run(self.db, correction_of) if correction_of else None
        correction = None
        if previous:
            data = None
            try:
                data = json.loads((self.db.path.parent / previous["folder"] / step.output).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
            correction = {"run": previous, "data": data, "note": note or ""}
        config = self.settings()
        with tempfile.TemporaryDirectory(prefix="30a-tahmin-") as folder:
            ctx = steps.RunContext(db=self.db, profile=PROFILES.get(destination_id), destination=destination, run_id="tahmin",
                                   folder=Path(folder), params=params, regions=self.regions(destination_id), correction=correction)
            try:
                ctx.inputs = step.prepare(ctx)
            except (steps.StepError, PackError) as exc:
                raise Conflict(str(exc)) from exc
            schema = steps.run_schema(step, ctx)
            system_text = steps.combined_instructions(step, ctx, schema)
            task = step.task(ctx)
            parts = single.sections(Path(folder), ctx.inputs)
            prompt = single.task_text(task, parts)
            table = single.parts_table([(INSTRUCTIONS, system_text)], task, parts)
        call = budget.call_estimate(self.db, config, step.key, single.prompt_tokens(system_text, prompt))
        row = {"baslik": step.title, "cagri": 1, **call, "en_buyuk_cagri": call["toplam"], **budget.model_text(config, step.key),
               "not": "Cevap kullanılamazsa (JSON değilse, şemaya uymuyorsa ya da kesildiyse) bir kez daha çağrılır."}
        return {**budget.summary([row], config, retries=1), "parcalar": table}

    def estimate_title(self, destination_id, region, family, note):
        return self.estimate(destination_id, "baslik", self.selection(destination_id, region, family, note))

    def estimate_review(self, destination_id, region, user_title, note):
        text = (user_title or "").strip()
        if not text:
            raise Conflict("Değerlendirilecek başlığı ya da fikri yazın.")
        params = {**self.selection(destination_id, region, title.ALL_FAMILIES, note), "kullanici_basligi": text}
        return self.estimate(destination_id, "baslik_degerlendirme", params)

    def estimate_correction(self, run_id, note):
        record = store.run(self.db, run_id)
        if record is None:
            raise KeyError(run_id)
        params = {k: v for k, v in record["params"].items() if k not in ("duzeltme_notu", "baslik_eki")}
        return self.estimate(record["destination_id"], record["step"], params, correction_of=run_id, note=(note or "").strip())

    def estimate_translate(self, run_id, index, edited_tr):
        record = store.run(self.db, run_id)
        if record is None:
            raise KeyError(run_id)
        view = self.view(run_id)
        candidate = next((c for c in view["candidates"] if c["sira"] == index), None)
        if candidate is None:
            raise Conflict("Böyle bir aday yok.")
        edited = (edited_tr or "").strip()
        note = title_review.source_note(view, candidate, edited)[:MAX_NOTE]
        params = {**self.selection(record["destination_id"], candidate["bolge"], title.ALL_FAMILIES, note), "kullanici_basligi": edited,
                  "kaynak": {"calisma": run_id, "aday": index, "baslik_en": candidate["baslik_en"], "baslik_tr": candidate["baslik_tr"]}}
        return self.estimate(record["destination_id"], "baslik_degerlendirme", params)

    # ------------------------------------------------------------------------------------------------------------- the run

    def work(self, run_id, destination, step, params, previous, note):
        """GÖREV-18: one Claude call without tools (a second one only when the answer cannot be used: no JSON, not the schema, cut at the
        output limit). The input files stay in the run folder and are given inside the task text; the program writes the output file."""
        record = store.run(self.db, run_id)
        job_id = record["job_id"]
        folder = (self.db.path.parent / record["folder"]).resolve()   # the run's folder; Claude opens nothing in it
        spend = {"tahmin": None, "gercek": None}

        def log(text, level="info"):
            self.db.update_job(job_id, message=text)

        def canceled():
            job = self.db.job(job_id)
            return self.closing or not job or job["status"] not in ("queued", "running")

        def fail(message, problems=None, extra=None):
            store.update_run(self.db, run_id, status="error", error=message, problems=problems or [])
            write_json(folder / RUN_RECORD, {**(extra or {}), "durum": "error", "hata": message, "sorunlar": problems or [],
                                             "harcama": spending_record(spend)})
            self.db.update_job(job_id, status="failed" if not canceled() or self.closing else "canceled", message=message,
                               result={"claude_run": run_id, "harcama": spending_record(spend)})

        try:
            self.db.update_job(job_id, status="running", progress=2, message="Girdiler hazırlanıyor.",
                               progress_info={"tur": "claude", "asama": "girdiler", "baslangic": iso_now()})
            profile = PROFILES.get(destination["id"])
            correction = None
            if previous:
                data = None
                try:
                    data = json.loads((self.db.path.parent / previous["folder"] / step.output).read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    pass
                correction = {"run": previous, "data": data, "note": note or ""}
            ctx = steps.RunContext(db=self.db, profile=profile, destination=destination, run_id=run_id, folder=folder, params=params,
                                   regions=self.regions(destination["id"]), log=log, correction=correction)
            ctx.inputs = step.prepare(ctx)
            for item in ctx.inputs:
                item["sha256"] = sha256_of(folder / item["dosya"])
            if canceled():
                return fail(store.INTERRUPTED if self.closing else runner.CANCELED_MESSAGE)
            schema = steps.run_schema(step, ctx)
            write_json(folder / RUN_SCHEMA, schema)
            system_text = steps.combined_instructions(step, ctx, schema)
            (folder / INSTRUCTIONS).write_text(system_text, encoding="utf-8")
            task = step.task(ctx)
            parts = single.sections(folder, ctx.inputs)
            prompt = single.task_text(task, parts)
            (folder / TASK).write_text(prompt, encoding="utf-8")
            versions = runner.instruction_hashes([*step.instruction_paths(profile), step.schema_path()])
            versions["birlesik_talimat"] = sha256_of(folder / INSTRUCTIONS)
            versions["calisma_semasi"] = sha256_of(folder / RUN_SCHEMA)
            config = self.settings()
            model, effort = claude_settings.resolve_model_effort(config, step.key)
            call_limit, job_limit = claude_settings.limits(config)
            estimate = budget.call_estimate(self.db, config, step.key, single.prompt_tokens(system_text, prompt))
            spend["tahmin"] = estimate
            base = {"calisma": run_id, "adim": step.key, "hazirlik": record["scope_id"], "destinasyon": destination["id"], "secim": params,
                    "duzeltme": {"onceki_calisma": previous["id"], "not": note} if previous else None, "talimat_surumu": versions,
                    "girdiler": ctx.inputs, "model": model, "efor": effort, "duzen": budget.ONE_CALL, "tur_siniri": 1, "araclar": [],
                    "izinler": [], "tahmin": estimate, "sinirlar": {"cagri": call_limit, "is": job_limit},
                    "istem_parcalari": single.parts_table([(INSTRUCTIONS, system_text)], task, parts)}
            store.update_run(self.db, run_id, model=model, effort=effort)
            log(f"İstem hazırlandı: {len(parts)} dosya istemin içinde; tahmin: yaklaşık {single.thousands(estimate['okunan'])} token okunacak, "
                f"{single.thousands(estimate['yazilan'])} yazılacak.")
            try:
                single.check_size(estimate, call_limit, step.title)
            except single.TooLarge as exc:
                return fail(exc.message, extra=base)
            if estimate["toplam"] > job_limit:
                return fail(f"{step.title}: tahmin yaklaşık {single.thousands(estimate['toplam'])} token; iş başına sınır "
                            f"{single.thousands(job_limit)} (Ayarlar → Claude). Çalışma başlatılmadı.", extra=base)
            try:
                _, command = runner.find_command(config["claude_path"])
            except runner.ClaudeRunnerError as exc:
                return fail(exc.failure.message, extra=base)
            if claude_info.api_key_in_env():
                log(claude_info.API_KEY_WARNING, "warning")
            expected, basis = self.expected_duration(step.key)
            progress = {"tur": "claude", "asama": "claude", "baslangic": ((self.db.job(job_id) or {}).get("progress_info") or {}).get("baslangic"),
                        "claude_baslangic": iso_now(), "beklenen_s": expected, "dayanak": basis, "harcama": spending_record(spend)}
            base["ilerleme_tahmini"] = {"beklenen_s": expected, "dayanak": basis}
            self.db.update_job(job_id, progress=10, progress_info=progress)
            calls, retry, data = [], None, None
            for attempt in (1, 2):
                text = prompt if attempt == 1 else single.task_text(task, parts, retry=retry)
                if attempt == 2:
                    (folder / f"gorev-{attempt}.md").write_text(text, encoding="utf-8")
                    again = budget.call_estimate(self.db, config, step.key, single.prompt_tokens(system_text, text))
                    if again["toplam"] > call_limit or spend["gercek"]["toplam"] + again["toplam"] > job_limit:
                        return fail(f"{step.title}: cevap kullanılamadı ({retry['reason']}); ikinci çağrı token sınırını aşacağı için yapılmadı "
                                    "(Token sınırına ulaşıldı). \"Düzeltme iste\" ile yeni bir çalışma açabilirsiniz.", extra=base)
                    log(f"İkinci çağrı (tek tur, önceki cevap ve sorunu istemde): yaklaşık {single.thousands(again['okunan'])} token okunacak.")
                invocation = runner.Invocation(cwd=folder, prompt=text, system_prompt_file=folder / INSTRUCTIONS, tools=(), allowed=(),
                                               max_turns=1, model=model, effort=effort)
                log("Claude düşünüyor; cevap tek seferde gelecek.")
                result = runner.run(invocation, command, stream_path=folder / (STREAM if attempt == 1 else f"akis-{attempt}.jsonl"), on_log=log,
                                    is_canceled=canceled, on_tick=lambda elapsed: self.db.update_job(job_id, progress=claude_percent(elapsed, expected)),
                                    on_rate_limit=lambda info: usage.record(self.db, info, source="calisma", run_id=run_id))
                calls.append(result)
                answer = single.answer_text(result)
                (folder / single.ANSWER_FILE.format(n="" if attempt == 1 else f"-{attempt}")).write_text(answer, encoding="utf-8")
                spend["gercek"] = single.spent([r.metrics() for r in calls])
                base.update({"calisma_sonucu": runner.result_dict(result), "cagrilar": [runner.result_dict(r) for r in calls],
                             "cikti_siniri": single.max_output(result)})
                store.update_run(self.db, run_id, claude_version=result.claude_version, session_id=result.session_id,
                                 metrics=combined_metrics(calls, estimate))
                cut = single.truncated(result)
                if result.failure and not cut:
                    closed = result.failure.kind == runner.CANCELED and self.closing
                    return fail(store.INTERRUPTED if closed else result.failure.message, extra=base)
                read, written = single.token_total(result.metrics())
                log(f"Cevap geldi: {single.thousands(read)} token okundu, {single.thousands(written)} token yazıldı · "
                    f"{runner.duration_text(result.elapsed_s)}.")
                problem, previous_answer = None, answer
                if cut:
                    problem, previous_answer = (f"Cevap uzunluk sınırında kesildi ({single.thousands(written)} token yazılmıştı); kesik cevap kabul "
                                                "edilmez. Daha kısa yaz: aynı bilgiyi daha az sözle ver."), None
                    log(f"Cevap uzunluk sınırında kesildi; kabul edilmedi.", "warning")
                else:
                    try:
                        data = single.parse_json(answer)
                    except single.AnswerError as exc:
                        problem = exc.message
                    else:
                        found = schema_errors_of(schema, data)
                        if found:
                            problem = f"Cevap şemaya uymuyor ({len(found)} sorun): " + "; ".join(found[:25])
                if problem is None:
                    break
                data = None
                if not cut:
                    log(f"Cevap geçersiz: {problem}", "warning")
                if attempt == 2:
                    return fail(f"{step.title}: Claude'un cevabı iki çağrıda da kullanılamadı: {problem} \"Düzeltme iste\" ile yeni bir "
                                "çalışma açabilirsiniz.", extra=base)
                if spend["gercek"]["toplam"] >= job_limit:
                    return fail(f"Token sınırına ulaşıldı: bu iş {single.thousands(spend['gercek']['toplam'])} token harcadı (iş başına sınır "
                                f"{single.thousands(job_limit)}); cevap kullanılamadığı hâlde ikinci çağrı yapılmadı.", extra=base)
                retry = {"reason": problem, "previous": previous_answer}
            write_json(folder / step.output, data)
            log("Cevap doğrulandı (JSON ve şema); program çıktıyı yazdı.")
            self.db.update_job(job_id, progress=92, message="Çıktı denetleniyor ve okunur Markdown yazılıyor.",
                               progress_info={**progress, "asama": "dogrulama", "harcama": spending_record(spend)})
            self.finish(run_id, step, ctx, base, folder, job_id, spend)
        except Exception as exc:  # anything unexpected: the run is an error, the job ends, nothing is left 'running'
            import traceback
            fail(f"Claude çalışması tamamlanamadı: {exc}", extra={"istisna": traceback.format_exc()})

    def expected_duration(self, step_key):
        """(seconds, basis): the median duration of the step's last successful runs, or the step's default."""
        with self.db.connect() as con:
            values = [r[0] for r in con.execute(f"""SELECT json_extract(metrics,'$.elapsed_s') FROM claude_runs WHERE step=? AND metrics IS NOT NULL
                AND status IN ({",".join("?" * len(DONE_STATUSES))}) ORDER BY created_at DESC LIMIT ?""", (step_key, *DONE_STATUSES, MEDIAN_OF))
                      if isinstance(r[0], (int, float)) and r[0] > 0]
        if values:
            middle = float(statistics.median(values))
            return middle, f"önceki {len(values)} başarılı çalışmanın ortancası ({minutes_text(middle)})"
        default = DEFAULT_SECONDS.get(step_key, FALLBACK_SECONDS)
        return float(default), f"önceki başarılı çalışma yok; varsayılan {minutes_text(default)}"

    # ------------------------------------------------------------------------------------------------------------- usage panel

    def usage(self):
        return usage.view(self.db)

    def refresh_usage(self):
        """The panel's "Yenile": the smallest Claude call (no tools, one turn, haiku, low effort). Its usage reports are stored."""
        if claude_info.api_key_in_env():
            raise Conflict("ANTHROPIC_API_KEY tanımlı: bu çağrı aboneliğinizden değil API'den ücretlendirilir. Kullanım yenilenmedi.")
        with self.lock:
            if self.closing:
                raise Conflict("Uygulama kapanıyor.")
            if any(r["status"] == "running" for r in self.running_runs()):
                raise Conflict("Bir Claude çalışması sürüyor; kullanım bilgisi o çalışmanın her cevabıyla zaten güncelleniyor.")
            self.check_text_free()
            if self.refreshing:
                raise Conflict("Kullanım zaten yenileniyor.")
            self.refreshing = True
        try:
            try:
                _, command = runner.find_command(self.settings()["claude_path"])
            except runner.ClaudeRunnerError as exc:
                raise Conflict(exc.failure.message) from exc
            folder = self.data_dir.joinpath(*usage.REFRESH_DIR)
            folder.mkdir(parents=True, exist_ok=True)
            instruction = folder / INSTRUCTIONS
            instruction.write_text(usage.REFRESH_INSTRUCTION, encoding="utf-8")
            stored = []
            effort = usage.REFRESH_EFFORT
            for _ in range(2):
                inv = runner.Invocation(cwd=folder, prompt=usage.REFRESH_PROMPT, system_prompt_file=instruction, tools=(), allowed=(),
                                        max_turns=1, model=usage.REFRESH_MODEL, effort=effort)
                result = runner.run(inv, command, timeout=usage.REFRESH_TIMEOUT_S, stream_path=folder / STREAM,
                                    on_rate_limit=lambda info: stored.append(usage.record(self.db, info, source="yenile")))
                if result.failure and result.failure.kind == runner.UNSUPPORTED and effort:
                    effort = ""                      # the family does not take an effort: once more with Claude Code's own choice
                    continue
                break
            if result.failure and not any(stored):
                raise Conflict(f"Kullanım yenilenemedi: {result.failure.message}")
            if not any(stored):
                raise Conflict("Claude bu çağrıda kullanım bilgisi vermedi; kullanım yenilenemedi.")
            cost = (result.envelope or {}).get("total_cost_usd")
            return {**usage.view(self.db), "last_refresh": {"model": usage.REFRESH_MODEL, "effort": effort or None,
                                                            "model_used": result.model_used, "elapsed_s": result.elapsed_s,
                                                            "cost_usd": cost if isinstance(cost, (int, float)) else None}}
        finally:
            with self.lock:
                self.refreshing = False

    def check_text_free(self):
        if self.text is not None and self.text.busy():
            raise Conflict("Bir video metni çalışması sürüyor; bitmesini bekleyin.")

    def running_runs(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("SELECT id, status FROM claude_runs WHERE status='running'")]

    def finish(self, run_id, step, ctx, base, folder, job_id, spend=None):
        spending = spending_record(spend or {})
        result_extra = {"harcama": spending} if spending else {}
        base = {**base, "harcama": spending} if spending else base
        output = folder / step.output
        if not output.is_file():
            message = f"Claude {step.output} dosyasını yazmadı."
            store.update_run(self.db, run_id, status="error", error=message, problems=[])
            write_json(folder / RUN_RECORD, {**base, "durum": "error", "hata": message})
            self.db.update_job(job_id, status="failed", message=message, result={"claude_run": run_id, **result_extra})
            return
        try:
            data = json.loads(output.read_text(encoding="utf-8-sig"))
        except ValueError as exc:
            message = f"{step.output} geçerli bir JSON değil: {exc}"
            store.update_run(self.db, run_id, status="error", error=message, problems=[])
            write_json(folder / RUN_RECORD, {**base, "durum": "error", "hata": message})
            self.db.update_job(job_id, status="failed", message=message, result={"claude_run": run_id, **result_extra})
            return
        from .schema import errors
        schema_errors = errors(json.loads((folder / RUN_SCHEMA).read_text(encoding="utf-8")), data)
        if schema_errors:
            problems = [title.problem(title.ERROR, f"Şema: {e}") for e in schema_errors]
            message = f"{step.output} şemaya uymuyor ({len(schema_errors)} sorun); \"Düzeltme iste\" ile yeni bir çalışma açabilirsiniz."
            store.update_run(self.db, run_id, status="error", error=message, problems=problems)
            write_json(folder / RUN_RECORD, {**base, "durum": "error", "hata": message, "sorunlar": problems})
            self.db.update_job(job_id, status="failed", message=message, result={"claude_run": run_id, **result_extra})
            return
        problems = step.check(ctx, data)
        (folder / step.markdown).write_text(step.render(ctx, data, problems), encoding="utf-8")
        store.update_run(self.db, run_id, status="awaiting_approval", problems=problems)
        write_json(folder / RUN_RECORD, {**base, "durum": "awaiting_approval", "sorunlar": problems,
                                         "paketler": {name: record["id"] for name, record in ctx.packs.items()}})
        errors_count = sum(p["seviye"] == title.ERROR for p in problems)
        count = len(data.get("adaylar") or [])
        if step.key == title_review.STEP.key:
            filled = (data.get("doluluk") or {}).get("dolar_mi")
            message = (f"Değerlendirme hazır: fikir veriyle {'doluyor' if filled else 'dolmuyor'}; "
                       + (f"{count} aday onay bekliyor" if count else "başlık adayı yok"))
        else:
            message = f"{count} başlık önerisi onay bekliyor"
        comparison = (spending or {}).get("karsilastirma")
        if comparison:
            self.db.update_job(job_id, message=f"Harcama: {comparison['metin']}." + (f" {comparison['uyari']}" if comparison["fazla"] else ""))
        info = (self.db.job(job_id) or {}).get("progress_info") or {}
        self.db.update_job(job_id, status="done", progress=100, result={"claude_run": run_id, **result_extra},
                           message=message + (f"; {errors_count} doğrulama sorunu var." if errors_count else "."),
                           progress_info={**info, "harcama": spending} if spending else None)

    # ------------------------------------------------------------------------------------------------------------- reading a run

    def context_of(self, record):
        """A step context rebuilt from a finished run (its packs' rows, previous titles as they were for the checks)."""
        step = steps.get(record["step"])
        folder = (self.db.path.parent / record["folder"]).resolve()
        saved = json.loads((folder / RUN_RECORD).read_text(encoding="utf-8")) if (folder / RUN_RECORD).is_file() else {}
        destination = self.db.destination(record["destination_id"])
        ctx = steps.RunContext(db=self.db, profile=PROFILES.get(record["destination_id"]), destination=destination, run_id=record["id"],
                               folder=folder, params=record["params"], regions=self.regions(record["destination_id"]))
        from ..evidence import stored_file
        for name, pack_id in (saved.get("paketler") or {}).items():
            try:
                path, pack_record = stored_file(self.db, pack_id, "json")
            except PackError:
                continue
            pack = json.loads(path.read_text(encoding="utf-8"))
            ctx.packs[name] = pack_record
            ctx.pack_rows[name] = {row["id"]: row for section in pack["sections"] for row in section["rows"]}
        return step, ctx, saved

    def view(self, run_id):
        record = store.run(self.db, run_id)
        if record is None:
            raise KeyError(run_id)
        step, ctx, saved = self.context_of(record)
        folder = (self.db.path.parent / record["folder"]).resolve()
        data = None
        if (folder / step.output).is_file():
            try:
                data = json.loads((folder / step.output).read_text(encoding="utf-8-sig"))
            except ValueError:
                data = None
        chosen = store.chosen(self.db, run_id)
        problems = record["problems"]
        candidates = []
        if data and record["status"] != "error":
            for index, item in enumerate(data.get("adaylar") or []):
                own = [p for p in problems if p["aday"] == index]
                candidates.append({**title.resolve_candidate(ctx, item), "sira": index, "sorunlar": own, "video_id": chosen.get(index),
                                   "secilebilir": not any(p["seviye"] == title.ERROR for p in own) and index not in chosen})
        markdown = (folder / step.markdown).read_text(encoding="utf-8") if (folder / step.markdown).is_file() else None
        result = saved.get("calisma_sonucu") or {}
        review = title_review.summary(data) if data and step.key == title_review.STEP.key else None
        return {**self.with_outcome(record), "step_title": step.title, "candidates": candidates,
                "general_problems": [p for p in problems if p["aday"] is None],
                "review": review, "output_file": step.output, "markdown_file": step.markdown,
                "notes": (data or {}).get("notlar") or [], "markdown": markdown, "inputs": saved.get("girdiler") or [],
                "instructions": saved.get("talimat_surumu"),
                "instruction_versions": instructions.used_versions(saved.get("talimat_surumu"), PROFILES.get(record["destination_id"])),
                "summary": {k: result.get(k) for k in ("num_turns", "tool_calls", "total_cost_usd",
                                                                                                    "elapsed_s", "denied", "result")},
                "actions": self.actions(record)}

    @staticmethod
    def actions(record):
        status = record["status"]
        return {"select": status in ("awaiting_approval", "approved"), "reject": status == "awaiting_approval",
                "correct": status in ("awaiting_approval", "approved", "error", "rejected")}

    def with_outcome(self, record):
        """GÖREV-15 Adım 1d: an evaluation that wrote no candidate is shown as information ("Değerlendirildi: veriyle dolmuyor")."""
        empty = title_review.without_candidates(self.db.path.parent, record)
        return {**record, "adaysiz": empty, "bilgi": title_review.NO_CANDIDATES_TEXT if empty else None}

    def runs(self, destination_id):
        return [self.with_outcome(r) for r in store.runs(self.db, destination_id)]

    # ------------------------------------------------------------------------------------------------------------- decisions

    def select(self, run_id, index, note="", title_en=None, title_tr=None):
        record = store.run(self.db, run_id)
        if record is None:
            raise KeyError(run_id)
        if not self.actions(record)["select"]:
            raise Conflict(f"Bu çalışmadan başlık seçilemez (durum: {record['status_label']}).")
        view = self.view(run_id)
        candidate = next((c for c in view["candidates"] if c["sira"] == index), None)
        if candidate is None:
            raise Conflict("Böyle bir aday yok.")
        if candidate["video_id"]:
            raise Conflict("Bu başlık zaten seçildi; video kaydı var.")
        if not candidate["secilebilir"]:
            raise Conflict("Bu adayda doğrulama hatası var; seçilemez. \"Düzeltme iste\" ile yeni bir çalışma açabilirsiniz.")
        note = (note or "").strip()
        if len(note) > MAX_NOTE:
            raise Conflict(f"Not en çok {MAX_NOTE} karakter olabilir.")
        # GÖREV-14 Adım 5b: the user may edit the title before choosing it; the edit passes the same length and suffix rules
        chosen_en = (title_en if title_en is not None else candidate["baslik_en"]).strip()
        chosen_tr = (title_tr if title_tr is not None else candidate["baslik_tr"]).strip()
        edited = (chosen_en, chosen_tr) != (candidate["baslik_en"].strip(), candidate["baslik_tr"].strip())
        if edited:
            suffix = record["params"].get("baslik_eki") or self.suffixes(record["destination_id"])
            found = title.title_problems(chosen_en, chosen_tr, suffix)
            if found:
                raise Conflict("Düzenlenen başlık kurallara uymuyor: " + " ".join(found))
        regions = {r["name"]: r["id"] for r in self.regions(record["destination_id"])}
        analysis = {k: candidate[k] for k in ("baslik_en", "baslik_tr", "bolge", "aile", "neden_onerildi", "izleyici_sorusu", "kanca",
                                             "icerik_plani", "eksik_veri", "sablon", "parametreler", "yeni_sablon_gerekir", "kapak_fikri")}
        analysis.update({"calisma": run_id, "aday": index, "secim_notu": note or None,
                         "paketler": {name: pack["id"] for name, pack in self.context_of(record)[1].packs.items()}})
        if edited:
            analysis["duzenleme"] = {"onerilen_en": candidate["baslik_en"], "onerilen_tr": candidate["baslik_tr"], "zaman": store.now()}
        video = {"id": store.new_id(), "destination_id": record["destination_id"], "region_id": regions.get(candidate["bolge"]),
                 "region_name": candidate["bolge"], "title_en": chosen_en, "title_tr": chosen_tr,
                 "proposed_title_en": candidate["baslik_en"], "proposed_title_tr": candidate["baslik_tr"], "user_edited": edited,
                 "family": candidate["aile"], "analysis": analysis, "template_key": candidate.get("sablon"),
                 "params": candidate.get("parametreler") or {}, "run_id": run_id, "candidate": index}
        with self.db.connect() as con:
            store.insert_video(con, video)
            con.execute("UPDATE claude_runs SET status='approved', decision_note=?, decided_at=? WHERE id=?", (note or None, store.now(), run_id))
        return store.video(self.db, video["id"])

    def reject(self, run_id, note=""):
        record = store.run(self.db, run_id)
        if record is None:
            raise KeyError(run_id)
        if not self.actions(record)["reject"]:
            raise Conflict(f"Bu çalışma reddedilemez (durum: {record['status_label']}).")
        store.update_run(self.db, run_id, status="rejected", decision_note=(note or "").strip() or None, decided_at=store.now())
        return store.run(self.db, run_id)

    def correct(self, run_id, note):
        record = store.run(self.db, run_id)
        if record is None:
            raise KeyError(run_id)
        if not self.actions(record)["correct"]:
            raise Conflict(f"Bu çalışma için düzeltme istenemez (durum: {record['status_label']}).")
        note = (note or "").strip()
        if not note:
            raise Conflict("Düzeltme için ne değişmesi gerektiğini nota yazın.")
        if len(note) > MAX_NOTE:
            raise Conflict(f"Not en çok {MAX_NOTE} karakter olabilir.")
        params = {k: v for k, v in record["params"].items() if k != "duzeltme_notu"}
        return self.start(record["destination_id"], record["step"], params, correction_of=run_id, note=note)

    # ------------------------------------------------------------------------------------------------------------- videos

    def videos(self, destination_id):
        return store.videos(self.db, destination_id)

    def video_pack(self, video_id):
        """The evidence pack of a video record (GÖREV-14): built from the chosen candidate's content plan, its sections in the plan's order,
        each with the rows the plan cites and their whole blocks; the analysis at its head; linked to the video. "Yeni şablon gerekir"
        does not stop it."""
        video = store.video(self.db, video_id)
        if video is None:
            raise KeyError(video_id)
        try:
            pack = plan_pack.build(self.db, video["destination_id"], PROFILES.get(video["destination_id"]), video)
        except PackError as exc:
            raise Conflict(str(exc)) from exc
        record = store_pack(self.db, pack, video_id=video["id"])
        store.set_video_status(self.db, video["id"], "paket_hazir")
        return record

    # ------------------------------------------------------------------------------------------------------------- life

    def recover(self):
        store.recover(self.db)

    def shutdown(self):
        with self.lock:
            self.closing = True
        self.executor.shutdown(wait=True, cancel_futures=True)
        store.recover(self.db)
