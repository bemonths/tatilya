"""The video text's writing chain (GÖREV-15, Adım 5): a text run of a video, shown as one job in the job panel.

Order (Housing Atlas TASARIM 21.4, made for 30A):
1. Freshness: when the video has no pack, or its pack is older than the data's last collection, the pack is made again first (logged).
2. Plan: the planner; the program's plan check (an evidence id the pack does not have sends the plan back to the planner once; still there:
   the run is an error; other findings are warnings); the critic (`yeniden_yap`: back to the planner once with the notes; the second plan is
   checked again but not criticised); the plan is final and kept in the run. "Plandan sonra dur" (Settings, off by default) pauses here.
3. For each chosen tone in turn: the section writers side by side (at most "Claude oturumu sınırı" sessions at once), the merger, the
   introduction and closing, the program joins the text and numbers the sentences, the final reader, the program applies the corrections,
   the program's check, the translator (chunks in turn), the digits of both languages, the version is saved.
4. Every tone written: "karşılaştırma bekliyor".
"Bu tonla da yaz" writes one more tone with a run's plan; "Planı yeniden yap" opens a new run (the old one and its versions stay).

Sessions. Every Claude session has the usual run folder (`claude/<video id>/<step>/<session id>/`: inputs, combined instructions, schema, task,
stream, output, Markdown, run record with the tone's file, name and SHA-256) and a `text_sessions` row. A finished session is never run again:
"Devam" finds it (same step, tone, part and round) and uses its output. A half-done session writes nothing.
- Invalid answer (schema or meaning check): asked once more with the errors and the previous output; invalid again: the run pauses and
  "Devam" starts that step again.
- Transient failure (timeout, network, Claude's 5xx or 529, a 429 without limit information, a session cut without its result): not a
  failure of the step; tried again after 1, 5 and 15 minutes, then the run pauses and waits for "Devam" (Housing Atlas
  `atlas/kesif/engine.py`, simpler).
- Usage limit (Housing Atlas `atlas/kesif/limits.py`): before every session the last usage measurement is read; at or over the 5-hour or the
  weekly threshold (Settings; 90 % and 95 %), or when Claude says the limit is reached, no new session opens, running ones finish and the run
  waits: until 2 minutes after the reset when that moment is known and ahead, else 5, 10, 20, 40, 60 minutes (then 60). The job panel says
  "Claude kullanım sınırı: <saat>'te kendiliğinden sürecek." and the run goes on by itself; "Devam" tries again without waiting.
- "Durdur" and the app closing cut the running sessions; the run is "duraklatıldı" (after a restart "yarıda kaldı"). The shutdown watchdog
  counts a text run as work and waits for it.
While a text run works no other Claude run (title proposal, evaluation, the usage panel's "Yenile") starts.
"""
import concurrent.futures
import hashlib
import json
import math
import re
import statistics
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..ai import claude_info, runner, settings as claude_settings, steps, store as ai_store, tones as T, usage
from ..ai import text_steps as TS
from ..ai.schema import errors as schema_errors
from ..database import Conflict
from ..destinations import PROFILES
from ..evidence import PackError, stored_file
from ..evidence.pack import latest_done_run, moment
from . import audit, document as D, store
from .views import TextViews

JOB_KIND = "claude_metin"
TRANSIENT_WAITS_S = (60.0, 300.0, 900.0)
LIMIT_WAITS_S = (300.0, 600.0, 1200.0, 2400.0, 3600.0)
LIMIT_MARGIN_S = 120.0
DEFAULT_SECONDS = {"metin_plan": 600, "metin_plan_elestiri": 240, "metin_bolum": 360, "metin_birlestirme": 300, "metin_giris_kapanis": 300,
                   "metin_son_okuma": 360, "metin_ceviri": 420}
PLAN_SHARE = 15.0
TONE_WEIGHTS = {"metin_bolum": 45.0, "metin_birlestirme": 10.0, "metin_giris_kapanis": 10.0, "metin_son_okuma": 10.0, "denetim": 5.0,
                "metin_ceviri": 20.0}
TONE_ORDER = ("metin_bolum", "metin_birlestirme", "metin_giris_kapanis", "metin_son_okuma", "denetim", "metin_ceviri")
STAGE_WORDS = {"metin_bolum": "bölümler", "metin_birlestirme": "birleştirme", "metin_giris_kapanis": "giriş ve kapanış",
               "metin_son_okuma": "son okuma", "denetim": "program denetimi", "metin_ceviri": "çeviri"}
NETWORK = re.compile(r"econnreset|econnrefused|etimedout|enotfound|socket hang up|fetch failed|network|connection (?:reset|refused|closed|"
                     r"error)|getaddrinfo|eai_again", re.I)
SERVER = re.compile(r"\b5\d\d\b.*(?:error|server)|internal server error|service unavailable|bad gateway|gateway timeout|overloaded", re.I)
PUBLISHED_EMPTY = "Henüz yayınlanmış video yok."
NOT_RESUMABLE = "Bu çalışma sürdürülemez; “Planı yeniden yap” ile yeni bir çalışma açın."


class Stopped(Exception):
    """"Durdur" or the app closing."""


class Paused(Exception):
    def __init__(self, code, text):
        super().__init__(text)
        self.code, self.text = code, text


class Failed(Exception):
    def __init__(self, code, text):
        super().__init__(text)
        self.code, self.text = code, text


class Clock:
    """Time of the chain; the tests give a clock that skips waiting."""

    def time(self):
        return time.time()

    def sleep(self, seconds):
        time.sleep(seconds)


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds")


def local_clock(epoch):
    return datetime.fromtimestamp(epoch).astimezone().strftime("%H:%M")


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def minutes(seconds):
    return f"{max(1, round(seconds / 60))} dk"


@dataclass
class Context:
    """One execution of a text run."""
    run: dict
    video: dict
    destination: dict
    profile: object
    pack_record: dict
    pack: dict
    summary_text: str
    numbers_text: str
    stop: threading.Event
    wake: threading.Event
    job_id: str
    settings: dict
    started: float
    state: dict = field(default_factory=dict)
    plan: dict | None = None
    tone_index: int = 0
    tone_count: int = 1
    stage: str = "plan"
    sections_done: int = 0
    sections_total: int = 0
    job_checked: float = 0.0

    @property
    def pack_ids(self):
        return {row["id"] for section in self.pack.get("sections") or [] for row in section.get("rows") or []}

    @property
    def title(self):
        return self.video["title_en"]


class TextService(TextViews):
    def __init__(self, db, data_dir, claude, clock=None):
        self.db, self.data_dir, self.claude = db, Path(data_dir), claude
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="30a-metin")
        self.lock = threading.Lock()
        self.gate_lock = threading.Lock()
        self.closing = False
        self.stops, self.wakes = {}, {}
        self.limit_until, self.limit_level, self.trial_after = {}, {}, {}
        self.clock = clock or Clock()

    # ------------------------------------------------------------------------------------------------------------------- state of the app

    def busy(self):
        """Is a text run working (running or waiting for the usage limit)? Other Claude runs do not start then."""
        return bool(store.active_runs(self.db))

    def settings(self):
        return claude_settings.load(self.data_dir)

    def profile_of(self, destination_id):
        profile = PROFILES.get(destination_id)
        if not (getattr(profile, "TEXT", None) or {}).get("tones"):
            raise Conflict("Bu destinasyonun video metni ayarları (ses ve tonlar) yok.")
        return profile

    # ------------------------------------------------------------------------------------------------------------------- starting

    def check_free(self):
        if self.closing:
            raise Conflict("Uygulama kapanıyor.")
        if self.busy():
            raise Conflict("Bir video metni çalışması sürüyor; bitmesini bekleyin.")
        if self.claude.running_runs():
            raise Conflict("Bir Claude çalışması sürüyor; bitmesini bekleyin.")
        if getattr(self.claude, "refreshing", False):
            raise Conflict("Claude kullanımı yenileniyor; biraz sonra yeniden deneyin.")

    def tone_entries(self, profile, files):
        known = {p.stem: T.item(p) for p in T.tone_files(profile)}
        chosen = []
        for stem in files or []:
            if stem not in known:
                raise Conflict(f"Böyle bir ton yok: {stem}.")
            if stem not in [c["dosya"] for c in chosen]:
                chosen.append({"dosya": stem, "ad": known[stem]["ad"]})
        if not chosen:
            raise Conflict("En az bir ton seçin.")
        return chosen

    def start(self, video_id, tone_files, *, replan_of=None):
        video = ai_store.video(self.db, video_id)
        if video is None:
            raise KeyError(video_id)
        profile = self.profile_of(video["destination_id"])
        chosen = self.tone_entries(profile, tone_files)
        with self.lock:
            self.check_free()
            run_id = store.new_id()
            job_id = self.new_job(video, chosen, replan=bool(replan_of))
            store.insert_run(self.db, run_id=run_id, destination_id=video["destination_id"], video_id=video_id, job_id=job_id, tones=chosen,
                             pack_id=None, replan_of=replan_of)
            self.submit(run_id)
        return self.view(run_id)

    def replan(self, run_id, tone_files=None):
        old = store.run(self.db, run_id)
        if old is None:
            raise KeyError(run_id)
        return self.start(old["video_id"], tone_files or [t["dosya"] for t in old["tones"]], replan_of=run_id)

    def add_tone(self, run_id, tone_file):
        """"Bu tonla da yaz": one more tone with the run's plan (the plan and the pack stay)."""
        run = store.run(self.db, run_id)
        if run is None:
            raise KeyError(run_id)
        if not run.get("plan"):
            raise Conflict("Bu çalışmanın planı henüz kesinleşmedi; önce çalışmanın bitmesini bekleyin.")
        video = ai_store.video(self.db, run["video_id"])
        profile = self.profile_of(run["destination_id"])
        added = self.tone_entries(profile, [tone_file])[0]
        with self.lock:
            self.check_free()
            tones = list(run["tones"])
            if added["dosya"] in [t["dosya"] for t in tones]:
                if any(v["tone_file"] == added["dosya"] for v in store.versions(self.db, text_run_id=run_id)):
                    raise Conflict("Bu tonla bu planın metni zaten yazıldı.")
            else:
                tones.append(added)
            job_id = self.new_job(video, [added], extra=True)
            store.update_run(self.db, run_id, status="running", tones=tones, job_id=job_id, reason=None, reason_text=None, wait_until=None,
                             finished_at=None)
            self.submit(run_id)
        return self.view(run_id)

    def resume(self, run_id):
        """"Devam": a paused or interrupted run goes on with what is left; a run waiting for the usage limit tries again at once."""
        run = store.run(self.db, run_id)
        if run is None:
            raise KeyError(run_id)
        if run["status"] == "waiting_limit":
            self.limit_until.pop(run_id, None)
            self.wakes.setdefault(run_id, threading.Event()).set()
            return self.view(run_id)
        if run["status"] == "error":
            raise Conflict(NOT_RESUMABLE)
        if run["status"] not in store.RESUMABLE:
            raise Conflict(f"Bu çalışma sürdürülemez (durum: {run['status_label']}).")
        video = ai_store.video(self.db, run["video_id"])
        with self.lock:
            self.check_free()
            job_id = self.new_job(video, run["tones"], resumed=True)
            store.update_run(self.db, run_id, status="running", job_id=job_id, reason=None, reason_text=None, wait_until=None, finished_at=None)
            self.submit(run_id)
        return self.view(run_id)

    def stop(self, run_id):
        run = store.run(self.db, run_id)
        if run is None:
            raise KeyError(run_id)
        if run["status"] not in store.ACTIVE:
            raise Conflict(f"Bu çalışma şu anda çalışmıyor (durum: {run['status_label']}).")
        self.stops.setdefault(run_id, threading.Event()).set()
        self.wakes.setdefault(run_id, threading.Event()).set()
        return self.view(run_id)

    def new_job(self, video, tones, *, replan=False, extra=False, resumed=False):
        names = ", ".join(t["ad"] for t in tones)
        what = "devam" if resumed else "bir ton daha" if extra else "planı yeniden" if replan else "yeni"
        try:
            return self.db.add_job(kind=JOB_KIND, title=f"Video metni · {video['title_en']} · {names} ({what})", destination_id=video["destination_id"])
        except Conflict as exc:
            raise Conflict("Bir video metni çalışması sürüyor; bitmesini bekleyin.") from exc

    def submit(self, run_id):
        self.stops[run_id] = threading.Event()
        self.wakes[run_id] = threading.Event()
        self.limit_level.pop(run_id, None)
        self.executor.submit(self.execute, run_id)

    # ------------------------------------------------------------------------------------------------------------------- the run

    def log(self, ctx, text, **fields):
        self.db.update_job(ctx.job_id, message=text, **fields)

    def canceled(self, ctx):
        """"Durdur", the app closing, or the job panel's "İptal et" (the job is no longer running; looked up at most once a second)."""
        if ctx.stop.is_set() or self.closing:
            return True
        now = time.monotonic()
        if now - ctx.job_checked >= 1.0:
            ctx.job_checked = now
            job = self.db.job(ctx.job_id)
            if not job or job["status"] not in ("queued", "running"):
                ctx.stop.set()
        return ctx.stop.is_set()

    def check_stop(self, ctx):
        if self.canceled(ctx):
            raise Stopped()

    def execute(self, run_id):
        run = store.run(self.db, run_id)
        job_id = run["job_id"]
        ctx = None
        try:
            self.db.update_job(job_id, status="running", progress=1, message="Metin çalışması başlıyor.",
                               progress_info={"tur": "metin", "yuzde": 1, "asama": "Hazırlanıyor", "baslangic": iso(self.clock.time())})
            ctx = self.prepare(run)
            plan = self.plan_phase(ctx)
            if plan is None:
                return
            ctx.tone_count = len(ctx.run["tones"])
            written = {v["tone_file"] for v in store.versions(self.db, text_run_id=run_id)}
            for index, tone in enumerate(ctx.run["tones"]):
                ctx.tone_index = index
                if tone["dosya"] in written:
                    continue
                self.tone_phase(ctx, tone)
            store.update_run(self.db, run_id, status="awaiting_comparison", reason=None, reason_text=None, wait_until=None)
            self.db.update_job(job_id, status="done", progress=100, message="Bütün tonların metni yazıldı; karşılaştırma bekliyor.",
                               result={"metin_calismasi": run_id, "video": run["video_id"]},
                               progress_info={**self.progress_info(ctx, "Bitti"), "yuzde": 100})
        except Stopped:
            closing = self.closing
            store.update_run(self.db, run_id, status="interrupted" if closing else "paused", reason="program_kapandi" if closing else "durduruldu",
                             reason_text="Program kapanırken yarıda kaldı; “Devam” kalan adımları çalıştırır." if closing else
                             "Durduruldu; “Devam” kalan adımları çalıştırır.", wait_until=None)
            self.db.update_job(job_id, status="canceled", message="Durduruldu; biten adımlar saklandı, “Devam” kalan adımları çalıştırır.")
        except Paused as exc:
            store.update_run(self.db, run_id, status="paused", reason=exc.code, reason_text=exc.text, wait_until=None)
            self.db.update_job(job_id, status="failed" if exc.code != "plan_hazir" else "done", message=exc.text)
        except Failed as exc:
            store.update_run(self.db, run_id, status="error", reason=exc.code, reason_text=exc.text, wait_until=None)
            self.db.update_job(job_id, status="failed", message=exc.text)
        except Exception as exc:  # anything unexpected: the run pauses ("Devam" tries again), nothing is left running
            text = f"Beklenmedik hata: {exc}. Biten adımlar saklandı; “Devam” kalan adımları yeniden dener."
            store.update_run(self.db, run_id, status="paused", reason="beklenmedik", reason_text=text, wait_until=None,
                             state={**((ctx.state if ctx else run.get("state")) or {}), "son_hata": traceback.format_exc()[-4000:]})
            self.db.update_job(job_id, status="failed", message=text)
        finally:
            store.close_running(self.db, run_id, "canceled" if (ctx and ctx.stop.is_set()) or self.closing else "failed",
                                "Çalışma bu oturum bitmeden durdu.")
            for table in (self.limit_until, self.limit_level, self.trial_after):
                table.pop(run_id, None)

    def prepare(self, run):
        video = ai_store.video(self.db, run["video_id"])
        destination = self.db.destination(run["destination_id"])
        profile = self.profile_of(run["destination_id"])
        job_id = run["job_id"]
        pack_id = run.get("pack_id")
        if not pack_id:
            try:
                pack_id = self.fresh_pack(video, job_id)
            except (Conflict, PackError) as exc:
                raise Failed("paket", f"Videonun paketi üretilemedi: {exc}") from None
            store.update_run(self.db, run["id"], pack_id=pack_id)
        path, record = stored_file(self.db, pack_id, "json")
        pack = json.loads(path.read_text(encoding="utf-8"))
        summary_path, _ = stored_file(self.db, pack_id, "yazar_ozeti")
        numbers_path, _ = stored_file(self.db, pack_id, "sayilar")
        run = store.run(self.db, run["id"])
        ctx = Context(run=run, video=video, destination=destination, profile=profile, pack_record=record, pack=pack,
                      summary_text=summary_for_claude(summary_path.read_text(encoding="utf-8")), numbers_text=numbers_path.read_text(encoding="utf-8"),
                      stop=self.stops.setdefault(run["id"], threading.Event()), wake=self.wakes.setdefault(run["id"], threading.Event()),
                      job_id=job_id, settings=self.settings(), started=self.clock.time(), state=dict(run.get("state") or {}),
                      plan=run.get("plan"), tone_count=len(run["tones"]))
        return ctx

    def fresh_pack(self, video, job_id):
        """The video pack the run uses: the newest one when it is not older than the data's last collection; else made again (logged)."""
        packs = (next((v for v in ai_store.videos(self.db, video["destination_id"]) if v["id"] == video["id"]), None) or {}).get("packs") or []
        latest = latest_done_run(self.db, video["destination_id"])
        if packs:
            made = moment(packs[0]["created_at"])
            if not latest or (made is not None and made >= moment(latest)):
                return packs[0]["id"]
            self.db.update_job(job_id, message="Videonun paketi verinin son çekiminden eski; paket yeniden üretiliyor.")
        else:
            self.db.update_job(job_id, message="Videonun paketi yok; paket üretiliyor.")
        record = self.claude.video_pack(video["id"])
        self.db.update_job(job_id, message=f"Paket hazır ({record['id'][:8]}).")
        return record["id"]

    def run_folder(self, ctx):
        return Path("metin") / ctx.video["id"] / "calismalar" / ctx.run["id"]

    def save_state(self, ctx):
        store.update_run(self.db, ctx.run["id"], state=ctx.state)

    # ------------------------------------------------------------------------------------------------------------------- inputs

    def title_analysis(self, ctx):
        """baslik_analizi.md: the chosen candidate with every evidence id turned into the video pack's id ("(pakette yok)" otherwise)."""
        head = ctx.pack.get("video") or {}
        analysis = ctx.video.get("analysis") or {}

        def ids(items):
            out = []
            for item in items or []:
                if item.get("yeni_kimlik"):
                    out.append(item["yeni_kimlik"])
                else:
                    text = (item.get("ifade") or item.get("kimlik") or "").strip()
                    out.append(f"(pakette yok: {text[:90]})" if text else "(pakette yok)")
            return ", ".join(out) or "kanıt yok"

        hook = head.get("kanca") or analysis.get("kanca") or {}
        lines = ["# Seçilen başlık ve analizi", "", f"- Başlık: {ctx.video['title_en']}", f"- Türkçe karşılığı: {ctx.video['title_tr']}",
                 f"- Bölge: {ctx.video['region_name']}", f"- İçerik ailesi: {ctx.video['family']}", "",
                 "Kanıt kimlikleri video paketinin (paket_ozeti.md) kimlikleridir.", "",
                 "## İzleyicinin sorusu", "", head.get("izleyici_sorusu") or analysis.get("izleyici_sorusu") or "—", "",
                 "## Kanca", "", f"{hook.get('metin') or '—'}", f"Kanıtlar: {ids(hook.get('kanitlar'))}", "",
                 "## Neden önerildi", "", head.get("neden_onerildi") or analysis.get("neden_onerildi") or "—", "",
                 "## İçerik planı (başlık önerisindeki ilk plan)", ""]
        for number, part in enumerate(head.get("icerik_plani") or analysis.get("icerik_plani") or [], 1):
            lines.append(f"{number}. {part.get('bolum')} — {part.get('ne_anlatir')} · kanıtlar: {ids(part.get('kanitlar'))}")
        lines += ["", "## Eksik veri", ""]
        lines += [f"- {m}" for m in head.get("eksik_veri") or analysis.get("eksik_veri") or []] or ["Yok."]
        return "\n".join(lines) + "\n"

    def channel_plan(self, ctx):
        plan = (getattr(ctx.profile, "CHANNEL", None) or {}).get("plan")
        return Path(plan).read_text(encoding="utf-8") if plan and Path(plan).is_file() else "Kanal planı yok.\n"

    def published(self, ctx):
        items = (getattr(ctx.profile, "TEXT", None) or {}).get("published_videos") or ()
        if not items:
            return f"# Kanalın yayınlanmış videoları\n\n{PUBLISHED_EMPTY}\n"
        return "# Kanalın yayınlanmış videoları\n\n" + "\n".join(f"- {v['baslik']} — {v.get('konu', '')} — {v.get('adres', '')}" for v in items) + "\n"

    def section_file(self, ctx, section):
        """bolum.md: the plan's part of the section, its concepts, its evidence rows with their whole blocks and usage notes, the sections
        before and after in one sentence each."""
        plan = ctx.plan
        ordered = sorted(plan["bolumler"], key=lambda s: s["no"])
        index = next(i for i, s in enumerate(ordered) if s["no"] == section["no"])
        before = ordered[index - 1] if index > 0 else None
        after = ordered[index + 1] if index + 1 < len(ordered) else None
        lines = [f"# {section['no']}. bölüm: {section.get('ic_adi')}", "", f"- Tek fikri: {section.get('tek_fikir')}",
                 f"- En çarpıcı anı: {section.get('en_carpici_an')}", f"- Nasıl açılacak: {section.get('acilis_bicimi')} — {section.get('acilis_notu')}",
                 f"- Kelime bütçesi: yaklaşık {section.get('kelime_butcesi')}", ""]
        concepts = [c["kavram"] for c in plan.get("kavramlar") or [] if c.get("bolum") == section["no"]]
        lines += ["## Bu bölümün açıklayacağı kavramlar", ""] + ([f"- {c}" for c in concepts] or ["Yok."]) + [""]
        lines += ["## Önceki ve sonraki bölüm", "", f"- Önceki: {before['tek_fikir'] if before else 'yok (bu ilk bölüm)'}",
                  f"- Sonraki: {after['tek_fikir'] if after else 'yok (bu son bölüm)'}", "", "## Kanıtlar", ""]
        lines += self.evidence_lines(ctx, section.get("kanitlar") or [])
        return "\n".join(lines).rstrip() + "\n"

    def evidence_lines(self, ctx, ids):
        """The cited rows and every row of the blocks they belong to (consecutive rows of one block in one section), with usage notes once."""
        rows_by_section = [(s, s.get("rows") or []) for s in ctx.pack.get("sections") or []]
        groups, seen = [], set()
        for wanted in ids:
            for section, rows in rows_by_section:
                for index, row in enumerate(rows):
                    if row["id"] != wanted:
                        continue
                    start = index
                    while start > 0 and rows[start - 1]["blok"] == row["blok"]:
                        start -= 1
                    end = index
                    while end + 1 < len(rows) and rows[end + 1]["blok"] == row["blok"]:
                        end += 1
                    key = (section["key"], start)
                    if key not in seen:
                        seen.add(key)
                        groups.append((rows[start:end + 1], set(ids)))
        lines = []
        for rows, cited in groups:
            note = rows[0].get("kullanim_notu")
            lines.append(f"### {rows[0]['blok']}" + (f" — kullanım notu: {note}" if note else ""))
            for row in rows:
                value = row.get("deger")
                unit = row.get("birim") or ""
                mark = " (planın gösterdiği)" if row["id"] in cited else ""
                lines.append(f"- {row['id']}{mark} [{row.get('etiket') or 'veri yok'}] {row.get('ifade')}"
                             + (f" — {value} {unit}".rstrip() if value not in (None, "") else "")
                             + (f" · İngilizce: {row['ifade_en']}" if row.get("ifade_en") else "")
                             + (" · küçük örnek" if row.get("kucuk_ornek") else "")
                             + (f" · not: {row['not']}" if row.get("not") else ""))
            lines.append("")
        return lines or ["Bu bölüm için kanıt satırı bulunamadı.", ""]

    # ------------------------------------------------------------------------------------------------------------------- sessions

    def session(self, ctx, step_key, *, files, tone=None, part=None, round_no=1, extra=None, reason=None, previous=None):
        """One place of the chain: its finished session's output, or a new session (invalid answers once more, transient failures and the
        usage limit waited for). Returns the output data."""
        done = store.done_session(self.db, ctx.run["id"], step_key, tone and tone["dosya"], part, round_no)
        if done:
            return json.loads((self.data_dir / done["folder"] / TS.OUTPUTS[step_key]).read_text(encoding="utf-8-sig"))
        step = steps.get(step_key)
        attempt, transient = 1, 0
        while True:
            self.check_stop(ctx)
            self.wait_gate(ctx)
            session_id = store.new_id()
            folder = Path("claude") / ctx.video["id"] / step_key / session_id
            absolute = (self.data_dir / folder).resolve()
            absolute.mkdir(parents=True, exist_ok=True)
            store.insert_session(self.db, session_id=session_id, text_run_id=ctx.run["id"], step=step_key, tone=tone and tone["dosya"],
                                 part=part, round_no=round_no, attempt=attempt, folder=folder.as_posix())
            given = dict(files)
            if previous is not None:
                given[TS.PREVIOUS] = json.dumps(previous, ensure_ascii=False, indent=1) + "\n"
            rctx = steps.RunContext(db=self.db, profile=ctx.profile, destination=ctx.destination, run_id=session_id, folder=absolute,
                                    params={"video": ctx.video["id"], "metin_calismasi": ctx.run["id"]}, regions=[],
                                    tone=tone if step.voice else None,
                                    extra={**(extra or {}), "files": given, "reason": reason, "step_key": step_key, "video_title": ctx.title,
                                           "pack_ids": ctx.pack_ids})
            outcome = self.run_session(ctx, step, rctx, session_id, absolute)
            kind, data, message, result = outcome
            if kind == "done":
                self.limit_level.pop(ctx.run["id"], None)
                return data
            if kind == "invalid":
                if attempt == 1:
                    attempt, reason, previous = 2, message, data
                    self.log(ctx, f"{step.title}: çıktı geçersizdi; hatalarıyla bir kez daha isteniyor.")
                    continue
                raise Paused("gecersiz_cevap", f"{step.title}: Claude iki denemede de kullanılabilir bir çıktı yazmadı ({message}). Çalışma "
                                               "duraklatıldı; “Devam” bu adımı yeniden başlatır.")
            if kind == "limit":
                self.hold_for_limit(ctx, result, message)
                continue
            if kind == "transient":
                transient += 1
                if transient > len(TRANSIENT_WAITS_S):
                    raise Paused("gecici_hata", f"{step.title}: geçici hata {len(TRANSIENT_WAITS_S)} beklemeden sonra da sürdü ({message}). "
                                                "Çalışma duraklatıldı; “Devam” ile yeniden deneyin.")
                wait = TRANSIENT_WAITS_S[transient - 1]
                self.log(ctx, f"{step.title}: geçici hata ({message}); {minutes(wait)} sonra yeniden denenecek.")
                self.sleep(ctx, self.clock.time() + wait)
                continue
            raise Paused("claude_hatasi", f"{step.title}: {message} Çalışma duraklatıldı; sorun giderilince “Devam” ile sürdürün.")

    def run_session(self, ctx, step, rctx, session_id, folder):
        """Runs one Claude session: (kind "done"|"invalid"|"limit"|"transient"|"failed"|…, data, message, result)."""
        profile = ctx.profile
        inputs = step.prepare(rctx)
        for item in inputs:
            item["sha256"] = hashlib.sha256((folder / item["dosya"]).read_bytes()).hexdigest()
        schema = steps.run_schema(step, rctx)
        write_json(folder / "sema.json", schema)
        (folder / "talimat.md").write_text(steps.combined_instructions(step, rctx, schema), encoding="utf-8")
        prompt = step.task(rctx)
        (folder / "gorev.md").write_text(prompt, encoding="utf-8")
        paths = [*step.instruction_paths(profile), step.schema_path()]
        if rctx.tone:
            paths.insert(2, Path(rctx.tone["path"]))
        versions = runner.instruction_hashes(paths)
        versions["birlesik_talimat"] = hashlib.sha256((folder / "talimat.md").read_bytes()).hexdigest()
        config = ctx.settings
        model, effort = claude_settings.resolve_model_effort(config, step.key)
        turns = claude_settings.max_turns(config, step.key)
        base = {"oturum": session_id, "metin_calismasi": ctx.run["id"], "video": ctx.video["id"], "adim": step.key, "parca": rctx.extra.get("section"),
                "ton": {k: rctx.tone[k] for k in ("dosya", "ad", "sha256")} if rctx.tone else None, "talimat_surumu": versions,
                "girdiler": inputs, "model": model, "efor": effort, "tur_siniri": turns, "araclar": list(step.tools), "izinler": list(step.allowed),
                "paket": ctx.pack_record["id"]}
        store.update_session(self.db, session_id, model=model, effort=effort)
        try:
            _, command = runner.find_command(config["claude_path"])
        except runner.ClaudeRunnerError as exc:
            store.update_session(self.db, session_id, status="failed", error=exc.failure.message)
            write_json(folder / "calisma.json", {**base, "durum": "failed", "hata": exc.failure.message})
            return "failed", None, exc.failure.message, None
        invocation = runner.Invocation(cwd=folder, prompt=prompt, system_prompt_file=folder / "talimat.md", tools=step.tools, allowed=step.allowed,
                                       max_turns=turns, model=model, effort=effort)
        result = runner.run(invocation, command, stream_path=folder / "akis.jsonl", is_canceled=lambda: self.canceled(ctx),
                            on_rate_limit=lambda info: usage.record(self.db, info, source="calisma"))
        base["calisma_sonucu"] = runner.result_dict(result)
        store.update_session(self.db, session_id, claude_version=result.claude_version, session_id=result.session_id, metrics=result.metrics())
        if result.failure:
            kind = failure_kind(result)
            status = {"iptal": "canceled", "sinir": "limit", "gecici": "transient"}.get(kind, "failed")
            store.update_session(self.db, session_id, status=status, error=result.failure.message)
            write_json(folder / "calisma.json", {**base, "durum": status, "hata": result.failure.message})
            if kind == "iptal":
                raise Stopped()
            return {"sinir": "limit", "gecici": "transient"}.get(kind, "failed"), None, result.failure.message, result
        output = folder / step.output
        data, problems = None, []
        if not output.is_file():
            problems = [f"Claude {step.output} dosyasını yazmadı."]
        else:
            try:
                data = json.loads(output.read_text(encoding="utf-8-sig"))
            except ValueError as exc:
                problems = [f"{step.output} geçerli bir JSON değil: {exc}"]
        if data is not None:
            problems = [f"Şema: {e}" for e in schema_errors(schema, data)]
            if not problems:
                found = step.check(rctx, data)
                problems = [p["metin"] for p in found if p["seviye"] == "hata"]
        if problems:
            store.update_session(self.db, session_id, status="invalid", problems=[{"seviye": "hata", "metin": p} for p in problems])
            write_json(folder / "calisma.json", {**base, "durum": "invalid", "sorunlar": problems})
            return "invalid", data, " ".join(problems)[:1500], result
        (folder / step.markdown).write_text(step.render(rctx, data, []), encoding="utf-8")
        store.update_session(self.db, session_id, status="done")
        write_json(folder / "calisma.json", {**base, "durum": "done"})
        return "done", data, None, result

    # ------------------------------------------------------------------------------------------------------------------- waiting

    def sleep(self, ctx, until):
        """Sleeps until `until` (epoch); "Durdur" ends it with Stopped, "Devam" wakes it at once."""
        while True:
            self.check_stop(ctx)
            left = until - self.clock.time()
            if left <= 0:
                return
            if ctx.wake.is_set():
                ctx.wake.clear()
                self.check_stop(ctx)
                return
            self.clock.sleep(min(1.0, left))

    def threshold_hold(self, ctx):
        """(window, reset epoch) when the last measurement is at or over its threshold and its window has not reset; else None."""
        row = usage.latest(self.db)
        if not row:
            return None
        now = self.clock.time()
        measured = datetime.fromisoformat(row["measured_at"]).timestamp()
        if measured < self.trial_after.get(ctx.run["id"], 0):
            return None                                    # after a wait one session tries (its answer brings a new measurement)
        limits = {"five_hour": ctx.settings.get("claude_limit_five_hour", 90), "seven_day": ctx.settings.get("claude_limit_week", 95)}
        for window in ("five_hour", "seven_day"):
            value, reset = row.get(window), row.get(f"{window}_resets_at")
            if value is None:
                continue
            if reset and reset <= now:
                continue                                   # the window has reset since: its use counts as nothing
            if value * 100 >= limits[window]:
                return window, reset
        return None

    def wait_until_for(self, ctx, reset):
        now = self.clock.time()
        if reset and reset > now:
            return reset + LIMIT_MARGIN_S
        level = self.limit_level.get(ctx.run["id"], 0)
        self.limit_level[ctx.run["id"]] = level + 1
        return now + LIMIT_WAITS_S[min(level, len(LIMIT_WAITS_S) - 1)]

    def hold_for_limit(self, ctx, result, message):
        reset = None
        for info in (result.rate_limits if result else []) or []:
            if isinstance(info, dict) and info.get("status") == "rejected":
                found = info.get("resetsAt")
                if isinstance(found, (int, float)):
                    reset = found / 1000 if found > 1e11 else found
        until = self.wait_until_for(ctx, reset)
        self.limit_until[ctx.run["id"]] = max(until, self.limit_until.get(ctx.run["id"], 0))
        self.log(ctx, f"Claude kullanım sınırına ulaşıldı ({message}).")

    def wait_gate(self, ctx):
        """Before a session: wait while the usage limit holds (threshold or Claude's refusal). One thread waits, the others queue behind."""
        with self.gate_lock:
            while True:
                self.check_stop(ctx)
                until = self.limit_until.get(ctx.run["id"])
                if until is None:
                    hold = self.threshold_hold(ctx)
                    if hold is None:
                        return
                    until = self.wait_until_for(ctx, hold[1])
                    self.log(ctx, f"Kullanım eşiğe geldi ({'5 saatlik' if hold[0] == 'five_hour' else 'haftalık'} pencere); yeni oturum açılmıyor.")
                if until <= self.clock.time():
                    self.limit_until.pop(ctx.run["id"], None)
                    continue
                self.limit_until[ctx.run["id"]] = until
                text = f"Claude kullanım sınırı: {local_clock(until)}'te kendiliğinden sürecek."
                store.update_run(self.db, ctx.run["id"], status="waiting_limit", wait_until=iso(until), reason="kullanim_siniri", reason_text=text)
                self.log(ctx, text, progress_info={**self.progress_info(ctx, ctx.stage), "bekleme": {"bitis": iso(until), "metin": text}})
                try:
                    self.sleep(ctx, until)
                finally:
                    self.limit_until.pop(ctx.run["id"], None)
                    self.trial_after[ctx.run["id"]] = self.clock.time()
                store.update_run(self.db, ctx.run["id"], status="running", wait_until=None, reason=None, reason_text=None, finished_at=None)
                self.log(ctx, "Kullanım sınırı beklemesi bitti; çalışma sürüyor.", progress_info=self.progress_info(ctx, ctx.stage))

    # ------------------------------------------------------------------------------------------------------------------- progress

    def expected(self, step_key):
        values = store.durations(self.db, step_key)
        return float(statistics.median(values)) if values else float(DEFAULT_SECONDS[step_key])

    def progress_info(self, ctx, stage_text):
        tones = max(1, ctx.tone_count)
        if ctx.stage == "plan":
            done = 0.0 if not ctx.state.get("plan_bitti") else 1.0
            percent = PLAN_SHARE * done
        else:
            weights_before = sum(TONE_WEIGHTS[k] for k in TONE_ORDER[:TONE_ORDER.index(ctx.stage)]) if ctx.stage in TONE_ORDER else 100.0
            within = weights_before
            if ctx.stage == "metin_bolum" and ctx.sections_total:
                within += TONE_WEIGHTS["metin_bolum"] * ctx.sections_done / ctx.sections_total
            percent = PLAN_SHARE + (100 - PLAN_SHARE) * (ctx.tone_index + within / 100.0) / tones
        sessions = max(1, int(ctx.settings.get("claude_max_sessions", 3)))
        remaining = 0.0
        if ctx.stage == "plan" and not ctx.state.get("plan_bitti"):
            remaining += self.expected("metin_plan") + self.expected("metin_plan_elestiri")
        sections = len((ctx.plan or {}).get("bolumler") or []) or 6
        per_tone = (math.ceil(sections / sessions) * self.expected("metin_bolum") + self.expected("metin_birlestirme")
                    + self.expected("metin_giris_kapanis") + self.expected("metin_son_okuma") + self.expected("metin_ceviri"))
        if ctx.stage in TONE_ORDER:
            left = 0.0
            if ctx.stage == "metin_bolum":
                left += math.ceil(max(0, ctx.sections_total - ctx.sections_done) / sessions) * self.expected("metin_bolum")
            for key in TONE_ORDER[TONE_ORDER.index(ctx.stage) + 1:]:
                left += self.expected(key) if key in DEFAULT_SECONDS else 0.0
            if ctx.stage != "metin_bolum" and ctx.stage in DEFAULT_SECONDS:
                left += self.expected(ctx.stage) / 2
            remaining += left + per_tone * max(0, tones - ctx.tone_index - 1)
        else:
            remaining += per_tone * max(0, tones - ctx.tone_index)
        return {"tur": "metin", "yuzde": max(1, min(99, int(percent))), "asama": stage_text, "baslangic": iso(ctx.started),
                "kalan_s": round(remaining), "bekleme": None, "metin_calismasi": ctx.run["id"]}

    def stage(self, ctx, stage, text=None):
        ctx.stage = stage
        tone = ctx.run["tones"][ctx.tone_index] if stage != "plan" and ctx.run["tones"] else None
        head = f"{tone['ad']} ({ctx.tone_index + 1}/{ctx.tone_count} ton) · " if tone else ""
        if stage == "metin_bolum":
            body = f"bölümler {ctx.sections_done}/{ctx.sections_total} bitti"
        else:
            body = text or STAGE_WORDS.get(stage, stage)
        info = self.progress_info(ctx, head + body)
        self.db.update_job(ctx.job_id, progress=info["yuzde"], progress_info=info)

    # ------------------------------------------------------------------------------------------------------------------- the plan

    def plan_phase(self, ctx):
        if ctx.plan:
            ctx.state["plan_bitti"] = True
            return ctx.plan
        ctx.stage = "plan"
        self.stage(ctx, "plan", "Plan yazılıyor")
        base_files = {"baslik_analizi.md": self.title_analysis(ctx), "paket_ozeti.md": ctx.summary_text, "sayilar.csv": ctx.numbers_text}
        planner_files = {**base_files, "kanal_plani.md": self.channel_plan(ctx)}
        warnings, round_no = [], 1

        def plan_round(number, reason=None, previous=None):
            return self.session(ctx, "metin_plan", files=planner_files, round_no=number, reason=reason, previous=previous)

        def checked(plan, number):
            """The plan after the program's check: an unknown id sends it back once; still there: the run is an error."""
            found = audit.plan_findings(plan, ctx.pack_ids)
            errors = [t for level, t in found if level == "hata"]
            if not errors:
                return plan, number, [t for level, t in found if level == "uyari"]
            self.log(ctx, "Planda pakette olmayan kanıt kimliği var; plan bir kez planlayıcıya dönüyor.")
            number += 1
            plan = plan_round(number, "Programın plan denetimi: " + " ".join(errors), plan)
            found = audit.plan_findings(plan, ctx.pack_ids)
            errors = [t for level, t in found if level == "hata"]
            if errors:
                raise Failed("plan_kimlik", "Plan iki kez pakette olmayan kanıt kimliği gösterdi: " + " ".join(errors)
                             + " Çalışma hata verdi; “Planı yeniden yap” ile yeni bir çalışma açabilirsiniz.")
            return plan, number, [t for level, t in found if level == "uyari"]

        plan = plan_round(round_no)
        plan, round_no, warnings = checked(plan, round_no)
        self.stage(ctx, "plan", "Plan eleştiriliyor")
        critique = self.session(ctx, "metin_plan_elestiri", files={"plan.json": json.dumps(plan, ensure_ascii=False, indent=1) + "\n", **base_files})
        notes = critique.get("notlar") or []
        if critique.get("yeniden_yap"):
            self.log(ctx, "Eleştirmen planın yeniden yapılmasını istedi; plan notlarla bir kez daha planlayıcıya dönüyor.")
            round_no += 1
            plan = plan_round(round_no, "Plan eleştirmeninin notları: " + " ".join(f"({n}) {t}" for n, t in enumerate(notes, 1)), plan)
            plan, round_no, warnings = checked(plan, round_no)
        ctx.plan = plan
        ctx.state.update({"plan_bitti": True, "plan_uyarilari": warnings, "elestiri": {"notlar": notes, "yeniden_yap": bool(critique.get("yeniden_yap"))},
                          "plan_turu": round_no})
        store.update_run(self.db, ctx.run["id"], plan=plan, state=ctx.state)
        folder = self.data_dir / self.run_folder(ctx)
        folder.mkdir(parents=True, exist_ok=True)
        write_json(folder / "plan.json", plan)
        write_json(folder / "plan_denetimi.json", {"uyarilar": warnings, "elestiri": ctx.state["elestiri"]})
        self.log(ctx, f"Plan kesinleşti: {len(plan['bolumler'])} bölüm" + (f"; {len(warnings)} program uyarısı." if warnings else "."))
        if ctx.settings.get(claude_settings.STOP_AFTER_PLAN):
            raise Paused("plan_hazir", "Plan hazır; “Plandan sonra dur” açık olduğu için çalışma durdu. Planı görüp “Devam” ile sürdürün.")
        return plan

    # ------------------------------------------------------------------------------------------------------------------- one tone

    def tone_snapshot(self, ctx, tone):
        known = (ctx.state.get("tonlar") or {}).get(tone["dosya"])
        if known and (self.data_dir / known["kopya"]).is_file():
            return {"dosya": tone["dosya"], "ad": known["ad"], "sha256": known["sha256"], "path": str(self.data_dir / known["kopya"])}
        relative = self.run_folder(ctx) / f"ton-{tone['dosya']}.md"
        try:
            info = T.snapshot(ctx.profile, tone["dosya"], self.data_dir / relative)
        except KeyError:
            raise Paused("ton_yok", f"“{tone['ad']}” tonu bulunamadı (silinmiş olabilir). Tonu arşivden geri alıp “Devam” deyin ya da başka bir tonla "
                                   "yazdırın.") from None
        ctx.state.setdefault("tonlar", {})[tone["dosya"]] = {"ad": info["ad"], "sha256": info["sha256"], "kopya": relative.as_posix()}
        self.save_state(ctx)
        return info

    def tone_phase(self, ctx, tone):
        info = self.tone_snapshot(ctx, tone)
        plan = ctx.plan
        plan_text = json.dumps(plan, ensure_ascii=False, indent=1) + "\n"
        ordered = sorted(plan["bolumler"], key=lambda s: s["no"])
        ctx.sections_total, ctx.sections_done = len(ordered), 0
        self.stage(ctx, "metin_bolum")
        sections = self.sections(ctx, info, ordered, plan_text)
        self.stage(ctx, "metin_birlestirme")
        merge = self.session(ctx, "metin_birlestirme", tone=info, files={"bolumler.md": D.sections_text(plan, sections), "plan.json": plan_text},
                             extra={"plan": plan})
        draft = D.assemble(plan, sections, merge, {"giris": [], "kapanis": []})
        self.stage(ctx, "metin_giris_kapanis")
        ends = self.session(ctx, "metin_giris_kapanis", tone=info, files={
            "metin.md": D.marked_text(draft, numbered=False, title=ctx.title), "baslik_analizi.md": self.title_analysis(ctx),
            "yayinlanan_videolar.md": self.published(ctx)})
        document = D.assemble(plan, sections, merge, ends)
        self.stage(ctx, "metin_son_okuma")
        final = self.session(ctx, "metin_son_okuma", tone=info, files={
            "metin.md": D.marked_text(document, numbered=True, title=ctx.title), "paket_ozeti.md": ctx.summary_text},
            extra={"sentence_count": len(D.sentences(document))})
        document, applied, refused = D.apply_corrections(document, final.get("duzeltmeler"), ctx.pack_ids)
        self.stage(ctx, "denetim")
        regions = [r["name"] for r in self.db.context(ctx.video["destination_id"]).canonical_regions]
        phrases = audit.read_phrases((getattr(ctx.profile, "TEXT", None) or {}).get("warning_phrases"))
        findings = audit.check(document, ctx.pack, regions=regions, phrases=phrases, plan=plan)
        self.stage(ctx, "metin_ceviri")
        answers, terms = {}, []
        chunks = D.chunks(document)
        for index, parts in enumerate(chunks, 1):
            part_doc = {"parcalar": parts}
            expected = [s["no"] for s in D.sentences(part_doc)]
            data = self.session(ctx, "metin_ceviri", tone=info, part=f"parca-{index}" if len(chunks) > 1 else None,
                                files={"cumleler.md": D.numbered_english(part_doc)},
                                extra={"expected_numbers": expected, "chunk": (index, len(chunks)) if len(chunks) > 1 else None,
                                       "known_terms": D.merge_terms(terms)})
            answers.update({item["no"]: item for item in data["cumleler"]})
            terms.append(data.get("terimler") or [])
        document = D.apply_translation(document, answers, D.merge_terms(*terms))
        document = D.attach_findings(document, findings)
        self.save_version(ctx, info, document, findings, applied, refused)

    def sections(self, ctx, info, ordered, plan_text):
        """The section writers side by side, at most the session limit at once; finished ones are kept even when another one stops."""
        results, problems = {}, []
        limit = max(1, int(ctx.settings.get("claude_max_sessions", 3)))
        counter = threading.Lock()

        def one(section):
            data = self.session(ctx, "metin_bolum", tone=info, part=f"bolum-{section['no']}", files={
                "plan.json": plan_text, "bolum.md": self.section_file(ctx, section)}, extra={"section": section["no"]})
            with counter:
                ctx.sections_done += 1
            self.stage(ctx, "metin_bolum")
            return section["no"], data

        with ThreadPoolExecutor(max_workers=limit, thread_name_prefix="30a-metin-bolum") as pool:
            futures = [pool.submit(one, section) for section in ordered]
            for future in concurrent.futures.as_completed(futures):
                try:
                    number, data = future.result()
                    results[number] = data
                except (Stopped, Paused, Failed) as exc:
                    problems.append(exc)
                    if isinstance(exc, Stopped):
                        ctx.stop.set()
        stops = [p for p in problems if isinstance(p, Stopped)]
        if stops:
            raise stops[0]
        if problems:
            raise problems[0]
        return results

    # ------------------------------------------------------------------------------------------------------------------- versions

    def save_version(self, ctx, info, document, findings, applied, refused):
        sessions = [s for s in store.sessions(self.db, ctx.run["id"]) if s["status"] == "done" and (s["tone"] in (None, info["dosya"]))]
        cost = sum((s["metrics"] or {}).get("cost_usd") or 0 for s in sessions)
        elapsed = sum((s["metrics"] or {}).get("elapsed_s") or 0 for s in sessions)
        tokens = {}
        for s in sessions:
            for key, value in (((s["metrics"] or {}).get("tokens")) or {}).items():
                if isinstance(value, (int, float)):
                    tokens[key] = tokens.get(key, 0) + value
        counts = audit.counts(findings)
        with self.db.connect() as con:
            number = store.next_number(con, ctx.video["id"])
        folder = Path("metin") / ctx.video["id"] / "surumler" / str(number)
        absolute = self.data_dir / folder
        absolute.mkdir(parents=True, exist_ok=True)
        version_id = store.new_id()
        document["video"] = ctx.video["id"]
        document["metin_calismasi"] = ctx.run["id"]
        document["surum_bilgisi"] = {
            "no": number, "kimlik": version_id, "zaman": store.now(), "ton": {k: info[k] for k in ("dosya", "ad", "sha256")},
            "paket": ctx.pack_record["id"], "plan": {"bolum_sayisi": len(ctx.plan["bolumler"]), "tur": ctx.state.get("plan_turu"),
                                                      "uyarilar": ctx.state.get("plan_uyarilari") or []},
            "oturumlar": [{"adim": s["step"], "parca": s["part"], "calisma": s["id"], "model": s["model"], "efor": s["effort"],
                           "sure_sn": (s["metrics"] or {}).get("elapsed_s"), "maliyet_usd": (s["metrics"] or {}).get("cost_usd")} for s in sessions],
            "kelime_sayisi": D.word_count(document), "cumle_sayisi": len(D.sentences(document)), "denetim": counts,
            "son_okuma": {"uygulanan": applied, "uygulanmayan": refused}}
        title = ctx.title
        files = {"metin.json": json.dumps(document, ensure_ascii=False, indent=1) + "\n", "metin_EN.md": D.render(document, title, "en"),
                 "metin_TR.md": D.render(document, ctx.video["title_tr"], "tr"), "seslendirme_EN.txt": D.voice_text(document),
                 "metin_EN_kanitli.md": D.evidence_text(document, title),
                 "denetim.md": D.audit_text(document, findings, title, ctx.state.get("plan_uyarilari") or []),
                 "denetim.json": json.dumps({"bulgular": findings, "sayilar": counts}, ensure_ascii=False, indent=1) + "\n"}
        for name, text in files.items():
            (absolute / name).write_bytes(text.encode("utf-8"))       # bytes: the recorded SHA-256 is of exactly these bytes
        store.insert_version(self.db, {"id": version_id, "number": number, "text_run_id": ctx.run["id"], "video_id": ctx.video["id"],
                                       "destination_id": ctx.video["destination_id"], "tone_file": info["dosya"], "tone_name": info["ad"],
                                       "tone_sha256": info["sha256"], "folder": folder.as_posix(), "words": D.word_count(document),
                                       "sentences": len(D.sentences(document)), "red": counts["kirmizi"], "yellow": counts["sari"],
                                       "cost_usd": round(cost, 4), "tokens": tokens, "elapsed_s": round(elapsed, 1),
                                       "json_sha256": sha256_bytes(files["metin.json"].encode("utf-8")), "pack_id": ctx.pack_record["id"]})
        self.log(ctx, f"{info['ad']}: {number}. sürüm kaydedildi ({D.word_count(document):,} kelime, {counts['kirmizi']} kırmızı, "
                      f"{counts['sari']} sarı bulgu).".replace(",", "."))
        return version_id

    # ------------------------------------------------------------------------------------------------------------------- life

    def recover(self):
        store.recover(self.db)

    def shutdown(self):
        with self.lock:
            self.closing = True
        for event in list(self.stops.values()) + list(self.wakes.values()):
            event.set()
        self.executor.shutdown(wait=True, cancel_futures=True)
        store.recover(self.db)


VIDEO_HEAD = re.compile(r"^## Video\n.*?(?=^## )", re.S | re.M)
VIDEO_POINTER = ("## Video\n\nVideonun başlığı ve analizi `baslik_analizi.md` dosyasında; oradaki kimlikler bu özetin (video paketinin) "
                 "kimlikleridir.\n\n")


def summary_for_claude(text):
    """paket_ozeti.md as the sessions read it: the video pack's writer summary without its "Video" head, which lists the title proposal's
    ids of the source packs next to this pack's ids; the analysis is in baslik_analizi.md with this pack's ids, so Claude sees one id series."""
    return VIDEO_HEAD.sub(VIDEO_POINTER, text, count=1)


def failure_kind(result):
    """"iptal", "sinir" (usage limit with its information), "gecici" (transient) or "hata"."""
    failure = result.failure
    if failure.kind == runner.CANCELED:
        return "iptal"
    if failure.kind == runner.USAGE_LIMIT:
        informed = failure.reset or any(isinstance(i, dict) and i.get("status") == "rejected" for i in result.rate_limits or [])
        return "sinir" if informed else "gecici"
    if failure.kind == runner.TIMEOUT:
        return "gecici"
    statuses = {(result.envelope or {}).get("api_error_status")} | {e.get("status") for e in result.api_errors or [] if isinstance(e, dict)}
    if any(isinstance(s, int) and (s == 529 or 500 <= s <= 599) for s in statuses):
        return "gecici"
    if failure.kind == runner.OTHER and failure.retryable:
        return "gecici"
    texts = "\n".join([failure.message or "", failure.detail or "", str((result.envelope or {}).get("result") or ""), (result.stderr or "")[-2000:]])
    if failure.kind == runner.OTHER and (SERVER.search(texts) or NETWORK.search(texts)):
        return "gecici"
    if failure.kind == runner.OTHER and result.envelope is None:
        return "gecici"
    return "hata"
