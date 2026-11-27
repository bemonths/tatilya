"""The video layer's service (GÖREV-21): the project's videos, what a step's screen reads, and the one approval component of the
steps with approval (1 · Başlık ve vaat, 3 · Plan, 5 · Kontrol ve ton seçimi): Onayla, Düzeltme iste, Reddet.

The statuses and their rules are `studio/workflow.py`; the Claude work is the title service's (`studio/ai/service.py`) and the text
chain's (`studio/text/engine.py`). This module only ties a decision to both:

| Adım | Onayla | Düzeltme iste (not zorunlu) | Reddet |
|---|---|---|---|
| 1 · Başlık ve vaat | adım onaylanır | adayın çalışması notla yeniden çalışır (Claude); video adayı bırakır | başlık seçimi kalkar, adım hazır |
| 3 · Plan | plan onaylanır; yazım başlayabilir | plan notla yeniden yazılır (Claude) | adım hazır; plan onaysız |
| 5 · Kontrol ve ton seçimi | seçilen ton videonun metni olur | not 4 · Yazım'a gider, o adım hazır olur; not yeniden yazımda Claude'a verilir | adım hazır |
| 6 · Yayın paketi | paket onaylanır (kopyası `videolar/<video>/6_yayin/`) | paket notla ve önceki paketle yeniden yazılır (Claude, 1 çağrı) | adım hazır |

The note of "Düzeltme iste" is given to Claude as material ("kullanıcının düzeltme notu"); no instruction file changes.
Outputs are files and are never deleted: a step's "Sürümler" lists them (packs, plans, text versions; for the first and the fifth step the
decisions' snapshots under `videolar/<video>/<step>/`).
"""
import json
from pathlib import Path

from . import workflow
from .ai import publish, store as ai_store, tones as T
from .database import Conflict
from .destinations import PROFILES
from .text import store as text_store

MAX_NAME = 120
MAX_NOTE = 4000
VERSION_DIR = "videolar"
STEP_DIRS = {key: f"{number}_{key}" for number, key in enumerate(workflow.KEYS, 1)}
NOTE_NEEDED = "Düzeltme isterken not zorunlu: neyin nasıl değişmesi gerektiğini yazın."
RULE_NAMES = {"isletme": "işletme adı", "kimlik": "kanıt kimliği", "dogrulanamadi": "doğrulanamadı", "rakam": "rakam", "rakam_isaretsiz": "işaretsiz rakam",
              "kaynak_sorusu": "kaynak sorusu", "kucuk_ornek": "küçük örnek", "ses": "ses", "uzunluk": "uzunluk", "bolum_uzunlugu": "bölüm uzunluğu"}


class VideoFlow:
    def __init__(self, db, data_dir, claude, text):
        self.db, self.data_dir, self.claude, self.text = db, Path(data_dir), claude, text

    # ------------------------------------------------------------------------------------------------------------- the project's videos

    def video(self, video_id):
        video = ai_store.video(self.db, video_id)
        if video is None:
            raise KeyError(video_id)
        return video

    def summary(self, video):
        rows = workflow.steps(self.db, video["id"])
        progress = workflow.progress(rows)
        current = next((key for key in workflow.KEYS if rows[key]["status"] not in workflow.COMPLETE), workflow.KEYS[-1])
        return {"id": video["id"], "ad": workflow.display_name(video), "calisma_adi": video.get("name"), "baslik_tr": video.get("title_tr"),
                "baslik_en": video.get("title_en"), "bolge": video.get("region_name"), "olusturuldu": video["created_at"],
                "arsivlendi": video.get("archived_at"), "ilerleme": f"{progress['completed']}/{progress['total']}", **progress,
                "siradaki": {"id": current, "ad": workflow.label(current), "durum": rows[current]["status"],
                             "durum_adi": workflow.STATUS_LABELS[rows[current]["status"]]}}

    def list(self, destination_id, archived=False):
        workflow.recover(self.db)
        items = [v for v in ai_store.videos(self.db, destination_id) if bool(v.get("archived_at")) == bool(archived)]
        return {"videolar": [self.summary(v) for v in items], "arsiv": bool(archived),
                "arsivdeki": sum(1 for v in ai_store.videos(self.db, destination_id) if v.get("archived_at")),
                "acik": self.opened(destination_id)}

    def create(self, destination_id, name=None):
        """"Yeni video": an empty video with an optional working name; its title is chosen or written in its first step."""
        name = (name or "").strip() or None
        if name and len(name) > MAX_NAME:
            raise Conflict(f"Çalışma adı en çok {MAX_NAME} karakter olabilir.")
        video_id = ai_store.new_id()
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            ai_store.insert_video(con, {"id": video_id, "destination_id": destination_id, "name": name})
            workflow.init(con, video_id, note=f"Video açıldı{f' (çalışma adı: {name})' if name else ''}; başlığı 1. adımda seçilecek.")
        self.open(destination_id, video_id)
        return self.summary(self.video(video_id))

    def set_archived(self, video_id, archived):
        """"Arşive kaldır" takes the video off the list; nothing is deleted and "Arşivdekileri göster" brings it back."""
        video = self.video(video_id)
        if archived and any(v == video_id for v, _ in workflow.active_steps(self.db)):
            raise Conflict("Bu videonun çalışan bir işi var; önce bitmesini bekleyin ya da iptal edin.")
        ai_store.set_archived(self.db, video_id, archived)
        if archived and self.opened(video["destination_id"]) == video_id:
            self.close(video["destination_id"])
        workflow.log(self.db, video_id, None, "Video arşive kaldırıldı." if archived else "Video arşivden çıkarıldı.")
        return self.summary(self.video(video_id))

    def opened(self, destination_id):
        video_id = ai_store.open_video(self.db, destination_id)
        video = ai_store.video(self.db, video_id) if video_id else None
        return video_id if video and video["destination_id"] == destination_id and not video.get("archived_at") else None

    def open(self, destination_id, video_id):
        video = self.video(video_id)
        if video["destination_id"] != destination_id:
            raise KeyError(video_id)
        ai_store.set_open_video(self.db, destination_id, video_id)
        return workflow.compute(self.db, destination_id, video_id)

    def close(self, destination_id):
        """"Videoyu kapat": the menu returns to the project; the video stays as it is."""
        ai_store.set_open_video(self.db, destination_id, None)
        return {"acik": None}

    # ------------------------------------------------------------------------------------------------------------- versions (files)

    def version_folder(self, video_id, step):
        return self.data_dir / VERSION_DIR / video_id / STEP_DIRS[step]

    def write_version(self, video_id, step, reason, content):
        """One more file of a step's output or decision; earlier files stay."""
        folder = self.version_folder(video_id, step)
        folder.mkdir(parents=True, exist_ok=True)
        number = len(list(folder.glob("surum-*.json"))) + 1
        data = {"no": number, "zaman": workflow.now(), "adim": workflow.label(step), "sebep": reason, "icerik": content}
        (folder / f"surum-{number:03d}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return data

    def file_versions(self, video_id, step):
        folder = self.version_folder(video_id, step)
        out = []
        for path in sorted(folder.glob("surum-*.json"), reverse=True) if folder.is_dir() else []:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            content = data.get("icerik") or {}
            out.append({"id": path.stem, "zaman": data.get("zaman"), "baslik": data.get("sebep"),
                        "ayrinti": content.get("ozet") or content.get("baslik_tr") or content.get("not"), "dosya": path.name})
        return out

    def versions(self, video_id, step):
        """The "Sürümler" of a step: every output it has written, newest first; nothing is ever deleted."""
        video = self.video(video_id)
        if step == "yayin":
            return self.publish_versions(video_id)
        if step in ("baslik", "kontrol"):
            return self.file_versions(video_id, step)
        if step == "paket":
            packs = (next((v for v in ai_store.videos(self.db, video["destination_id"]) if v["id"] == video_id), None) or {}).get("packs") or []
            return [{"id": p["id"], "zaman": p["created_at"], "baslik": f"Paket {p['id'][:8]}", "ayrinti": None, "paket": p["id"]} for p in packs]
        if step == "plan":
            current = workflow.step(self.db, video_id, "plan")
            out = []
            for run in text_store.runs(self.db, video_id):
                if not run.get("plan") or (run.get("state") or {}).get("plan_kaynagi"):
                    continue
                state = run.get("state") or {}
                chosen = current["ref"] == run["id"] and current["status"] == "approved"
                out.append({"id": run["id"], "zaman": run["created_at"], "calisma": run["id"],
                            "baslik": f"{len(run['plan'].get('bolumler') or [])} bölümlü plan" + (" · onaylı" if chosen else ""),
                            "ayrinti": f"Düzeltme notu: {state['plan_notu']}" if state.get("plan_notu") else None})
            return out
        if step == "yazim":
            return [{"id": v["id"], "zaman": v["created_at"], "surum": v["id"], "baslik": f"{v['number']}. sürüm · {v['tone_name']}",
                     "ayrinti": f"{v['words']} kelime · {v['red']} kırmızı · {v['yellow']} sarı"}
                    for v in reversed(text_store.versions(self.db, video_id=video_id))]
        return []

    # ------------------------------------------------------------------------------------------------------------- a step's screen

    def actions(self, step, row, video):
        status = row["status"]
        approval = step in workflow.APPROVAL
        decided = status in ("awaiting_approval", "approved", "stale")
        resumable = False
        if step in ("plan", "yazim") and status == "error" and row["ref"]:
            run = text_store.run(self.db, row["ref"])
            resumable = bool(run and run["status"] in text_store.RESUMABLE)
        return {"approve": approval and status in ("awaiting_approval", "stale"), "correct": approval and decided,
                "reject": approval and decided, "clear_stale": status == "stale",
                "run": {"baslik": status in ("ready", "error"), "paket": status in ("ready", "done", "stale", "error"),
                        "plan": status in ("ready", "error", "awaiting_approval", "approved", "stale"),
                        "yazim": status in ("ready", "done", "stale", "error"), "kontrol": False,
                        "yayin": status in ("ready", "error", "awaiting_approval", "approved", "stale")}.get(step, False),
                "resume": resumable, "reopen": step == "kontrol" and status == "ready" and bool(text_store.versions(self.db, video_id=video["id"]))}

    def job_of(self, video_id, step, row):
        """The job that works for the step now (its live spending and "İptal" are on the step's screen)."""
        if step in ("baslik", "yayin"):
            with self.db.connect() as con:
                found = con.execute("SELECT job_id FROM claude_runs WHERE status='running' AND json_extract(params,'$.video_id')=? "
                                    "AND coalesce(json_extract(params,'$.video_adimi'),'baslik')=?", (video_id, step)).fetchone()
            return found[0] if found else None
        if step in ("plan", "yazim") and row["ref"]:
            run = text_store.run(self.db, row["ref"])
            return run["job_id"] if run and run["status"] in text_store.ACTIVE else None
        return None

    def title_view(self, video):
        if not video.get("title_en"):
            return None
        analysis = video.get("analysis") or {}
        marks = self.claude.check_title(video["destination_id"], video["title_en"], analysis.get("kapak_fikri"), video.get("region_name"))
        return {"baslik_tr": video["title_tr"], "baslik_en": video["title_en"], "bolge": video.get("region_name"), "aile": video.get("family"),
                "izleyici_sorusu": analysis.get("izleyici_sorusu"), "vaat": (analysis.get("kanca") or {}).get("metin"),
                "neden_onerildi": analysis.get("neden_onerildi"),
                "icerik_plani": [{"bolum": p.get("bolum"), "ne_anlatir": p.get("ne_anlatir")} for p in analysis.get("icerik_plani") or []],
                "eksik_veri": analysis.get("eksik_veri") or [], "kapak_fikri": analysis.get("kapak_fikri"),
                "kullanici_duzenledi": video.get("user_edited"), "onerilen_tr": video.get("proposed_title_tr"),
                "onerilen_en": video.get("proposed_title_en"), "calisma": video.get("run_id"), "aday": video.get("candidate"),
                "isaretler": marks["isaretler"]}

    def step_view(self, video_id, step):
        workflow.check_step(step)
        video = self.video(video_id)
        flow = workflow.compute(self.db, video["destination_id"], video_id)
        view = next(s for s in flow["steps"] if s["id"] == step)
        row = workflow.step(self.db, video_id, step)
        out = {"video": flow["video"], "adim": view, "eylemler": self.actions(step, row, video), "is": self.job_of(video_id, step, row),
               "surumler": self.versions(video_id, step),
               "gunluk": [h for h in workflow.history(self.db, video_id, 400) if h["step"] in (step, None)][:15]}
        if step in workflow.PLANNED:
            out["aciklama"] = workflow.PLANNED[step]
        elif step == "baslik":
            bank = self.claude.bank(video["destination_id"])
            own = [r for r in bank["calismalar"] if (r.get("params") or {}).get("video_id") == video_id]
            free = [{"calisma": r["id"], "calisma_bolge": (r.get("params") or {}).get("bolge"), "bu_video": r in own, **c}
                    for r in bank["calismalar"] for c in r["adaylar"] if c["secilebilir"]]
            free.sort(key=lambda c: not c["bu_video"])
            out.update({"secim": self.title_view(video), "adaylar": free, "degerlendirmeler": [
                {k: r.get(k) for k in ("id", "status", "status_label", "created_at", "error", "adaysiz", "bilgi", "canceled")}
                | {"baslik": (r.get("params") or {}).get("kullanici_basligi"), "aday_sayisi": len(r["adaylar"]),
                   "duzeltme_notu": (r.get("params") or {}).get("duzeltme_notu")} for r in own],
                        "secenekler": self.claude.options(video["destination_id"])})
        elif step == "paket":
            out["paket"] = self.text.pack_state(video) if video.get("title_en") else None
        elif step == "plan":
            out["calisma"] = self.text.view(row["ref"]) if row["ref"] and text_store.run(self.db, row["ref"]) else None
            out["mesgul"] = self.busy_text()
        elif step == "yazim":
            profile = PROFILES.get(video["destination_id"])
            default = T.default_file(self.data_dir, video["destination_id"], profile)
            run = text_store.run(self.db, row["ref"]) if row["ref"] else None
            out.update({"tonlar": [{"dosya": p.stem, "ad": T.item(p)["ad"], "ilk_cumle": T.item(p)["ilk_cumle"], "varsayilan": p.stem == default}
                                   for p in T.tone_files(profile)],
                        "calisma": self.text.view(run["id"]) if run and (run.get("state") or {}).get("plan_onaylandi") else None,
                        "duzeltme_notu": row["note"], "mesgul": self.busy_text()})
        elif step == "kontrol":
            writing = workflow.step(self.db, video_id, "yazim")
            run_id = writing["ref"] if writing["ref"] and text_store.run(self.db, writing["ref"]) else None
            versions = text_store.versions(self.db, text_run_id=run_id) if run_id else []
            if not versions:
                versions, run_id = text_store.versions(self.db, video_id=video_id), None
            out.update({"calisma": run_id, "secim": self.text.selection(video_id),
                        "tonlar": [self.check_summary(v) for v in versions], "not": row["note"]})
        elif step == "yayin":
            out.update({"yayin": self.publish_view(row), "secim": self.text.selection(video_id)})
        return out

    def check_summary(self, version):
        """A written tone for the check: its counts and the findings of the program's check grouped by rule (business names apart)."""
        summary = self.text.version_summary(version)
        try:
            report = json.loads((self.data_dir / version["folder"] / "denetim.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            report = {"bulgular": []}
        groups = {}
        for item in report.get("bulgular") or []:
            group = groups.setdefault(item.get("kural") or "diger", {"kural": item.get("kural") or "diger", "kirmizi": 0, "sari": 0, "ornekler": []})
            group["kirmizi" if item.get("seviye") == "kirmizi" else "sari"] += 1
            if len(group["ornekler"]) < 5:
                group["ornekler"].append({"no": item.get("no"), "metin": item.get("metin"), "seviye": item.get("seviye")})
        for group in groups.values():
            group["ad"] = RULE_NAMES.get(group["kural"], group["kural"])
        ordered = sorted(groups.values(), key=lambda g: (g["kural"] != "isletme", -g["kirmizi"], -g["sari"]))
        return {**summary, "bulgular": ordered, "isletme_adi": next((g["kirmizi"] + g["sari"] for g in ordered if g["kural"] == "isletme"), 0)}

    def busy_text(self):
        if self.text.busy():
            return "Bir plan ya da yazım çalışması sürüyor; bitmesini bekleyin."
        if self.claude.running_runs():
            return "Bir Claude çalışması sürüyor; bitmesini bekleyin."
        return None

    # ------------------------------------------------------------------------------------------------------------- running the steps

    def require(self, video_id, step, statuses, message):
        row = workflow.step(self.db, video_id, step)
        if row["status"] not in statuses:
            raise Conflict(message)
        return row

    def use_candidate(self, run_id, index, note="", title_en=None, title_tr=None, video_id=None):
        """"Bu başlıkla video aç" (topic bank) or "Bu başlığı kullan" (a video's first step): the candidate is marked used, the first
        step waits for approval and the video is the open one."""
        video = self.claude.select(run_id, index, note, title_en, title_tr, video_id)
        self.write_version(video["id"], "baslik", "Başlık seçildi", {"baslik_tr": video["title_tr"], "baslik_en": video["title_en"],
                                                                     "calisma": run_id, "aday": index, "analiz": video.get("analysis")})
        ai_store.set_open_video(self.db, video["destination_id"], video["id"])
        return video

    def start_review(self, video_id, region, user_title, note):
        """1 · Başlık ve vaat: the user writes the title; Claude evaluates it and its candidates appear in this step."""
        video = self.video(video_id)
        self.require(video_id, "baslik", ("ready", "error"), "Bu videonun başlığı seçili; yeni bir değerlendirme için önce “Reddet” deyin.")
        return self.claude.start_review(video["destination_id"], region, user_title, note, video_id=video_id)

    def build_pack(self, video_id):
        video = self.video(video_id)
        self.require(video_id, "baslik", ("approved",), "Veri paketi başlık onaylanınca üretilir: önce 1 · Başlık ve vaat adımını onaylayın.")
        if not video.get("title_en"):
            raise Conflict("Bu videonun başlığı yok.")
        try:
            return self.claude.video_pack(video_id)
        except Conflict as exc:
            workflow.set_step(self.db, video_id, "paket", "error", error=str(exc))
            raise

    def check_pack_ready(self, video_id):
        self.require(video_id, "baslik", ("approved",), "Önce 1 · Başlık ve vaat adımını onaylayın.")
        self.require(video_id, "paket", ("done", "stale"), "Plan veri paketinden çıkarılır: önce 2 · Veri paketi adımında paketi üretin.")

    def estimate_plan(self, video_id, note=None):
        self.check_pack_ready(video_id)
        return self.text.estimate_plan(video_id, note)

    def start_plan(self, video_id, note=None):
        self.check_pack_ready(video_id)
        return self.text.start_plan(video_id, note)

    def estimate_writing(self, video_id, tones):
        note = workflow.step(self.db, video_id, "yazim")["note"]
        return self.text.estimate_writing(video_id, tones, note)

    def start_writing(self, video_id, tones):
        """4 · Yazım: never before the plan is approved. A correction note waiting from the check is given to Claude with this run."""
        note = workflow.step(self.db, video_id, "yazim")["note"]
        return self.text.start_writing(video_id, tones, note)

    # ------------------------------------------------------------------------------------------------------------- 6 · Yayın paketi

    def publish_runs(self, video_id):
        """The Claude runs of 6 · Yayın paketi for this video, newest first (they are not in the topic bank)."""
        with self.db.connect() as con:
            ids = [r[0] for r in con.execute("SELECT id FROM claude_runs WHERE step=? AND json_extract(params,'$.video_id')=? "
                                             "ORDER BY created_at DESC, rowid DESC", (publish.STEP_KEY, video_id))]
        return [ai_store.run(self.db, i) for i in ids]

    def publish_view(self, row):
        """The step's output: the package (`yayin.json`), its readable file, the program's check, the timing and the spending."""
        from .ai.service import RUN_RECORD
        record = ai_store.run(self.db, row["ref"]) if row["ref"] else None
        if record is None:
            return None
        folder = self.data_dir / record["folder"]

        def read(name, as_json=False):
            try:
                text = (folder / name).read_text(encoding="utf-8-sig")
                return json.loads(text) if as_json else text
            except (OSError, ValueError):
                return None
        saved = read(RUN_RECORD, True) or {}
        return {"calisma": record["id"], "durum": record["status"], "durum_adi": record["status_label"], "hata": record.get("error"),
                "paket": read(publish.OUTPUT, True), "markdown": read(publish.MARKDOWN), "zaman": read(publish.TIMING, True),
                "sorunlar": record.get("problems") or [], "harcama": saved.get("harcama"), "tahmini": publish.ESTIMATED,
                "duzeltme_notu": (record.get("params") or {}).get("duzeltme_notu"), "dosya": f"{record['folder']}/{publish.MARKDOWN}"}

    def publish_versions(self, video_id):
        runs = [{"id": r["id"], "zaman": r["created_at"], "baslik": f"Yayın paketi · {r['status_label']}",
                 "ayrinti": f"Düzeltme notu: {(r.get('params') or {})['duzeltme_notu']}" if (r.get("params") or {}).get("duzeltme_notu") else None}
                for r in self.publish_runs(video_id)]
        return runs + self.file_versions(video_id, "yayin")

    def publish_params(self, video_id):
        video = self.video(video_id)
        self.require(video_id, "yayin", ("ready", "error", "awaiting_approval", "approved", "stale"),
                     "Önce 5 · Kontrol ve ton seçimi onaylanmalı: yayın paketi onaylı metinden yazılır.")
        chosen = self.text.selection(video_id)
        if not chosen:
            raise Conflict("Önce 5 · Kontrol ve ton seçimi onaylanmalı: yayın paketi onaylı metinden yazılır.")
        return video, {"video_id": video_id, "video_adimi": publish.STEP_KEY, "bolge": video.get("region_name") or "30A",
                       "surum_id": chosen["version_id"]}

    def estimate_publish(self, video_id):
        """The estimate above "Yayın paketini çıkar" (one call; nothing is sent)."""
        video, params = self.publish_params(video_id)
        return self.claude.estimate(video["destination_id"], publish.STEP_KEY, params)

    def start_publish(self, video_id):
        video, params = self.publish_params(video_id)
        started = self.claude.start(video["destination_id"], publish.STEP_KEY, params)          # sets the step running
        workflow.log(self.db, video_id, "yayin", f"6 · Yayın paketi: Claude çalışması başladı ({started['id'][:8]}).")
        return started

    def resume(self, video_id, step):
        row = workflow.step(self.db, video_id, step)
        if step not in ("plan", "yazim") or not row["ref"]:
            raise Conflict("Bu adımda sürdürülecek bir çalışma yok.")
        return self.text.resume(row["ref"])

    def reopen_check(self, video_id):
        if not text_store.versions(self.db, video_id=video_id):
            raise Conflict("Henüz yazılmış metin yok.")
        self.require(video_id, "kontrol", ("ready",), "Kontrol zaten açık.")
        workflow.set_step(self.db, video_id, "kontrol", "awaiting_approval", log="5 · Kontrol ve ton seçimi yeniden açıldı.")
        return self.step_view(video_id, "kontrol")

    # ------------------------------------------------------------------------------------------------------------- the approval component

    @staticmethod
    def clean(note, required=False):
        note = (note or "").strip()
        if required and not note:
            raise Conflict(NOTE_NEEDED)
        if len(note) > MAX_NOTE:
            raise Conflict(f"Not en çok {MAX_NOTE} karakter olabilir.")
        return note

    def decision_row(self, video_id, step, action):
        if step not in workflow.APPROVAL:
            raise Conflict(f"{workflow.label(step)} adımında onay yok.")
        video = self.video(video_id)
        row = workflow.step(self.db, video_id, step)
        if not self.actions(step, row, video)[action]:
            raise Conflict(f"{workflow.label(step)} şu anda bu karara açık değil (durum: {workflow.STATUS_LABELS[row['status']]}).")
        return video, row

    def approve(self, video_id, step, note="", version_id=None):
        video, row = self.decision_row(video_id, step, "approve")
        note = self.clean(note)
        said = f"{workflow.label(step)} onaylandı. Not: {note or 'yok'}"
        if step == "baslik":
            if not video.get("title_en"):
                raise Conflict("Onaylanacak başlık seçilmedi.")
            workflow.set_step(self.db, video_id, "baslik", "approved", note=note or None, ref=video.get("run_id"), stale_from="paket",
                              reason=workflow.REASONS["baslik"], log=said)
            self.write_version(video_id, "baslik", "Onaylandı", {"baslik_tr": video["title_tr"], "baslik_en": video["title_en"], "not": note or None})
        elif step == "plan":
            run = text_store.run(self.db, row["ref"]) if row["ref"] else None
            if not run or not run.get("plan"):
                raise Conflict("Onaylanacak plan yok.")
            self.text.set_plan_approval(run["id"], True)
            workflow.set_step(self.db, video_id, "plan", "approved", note=note or None, ref=run["id"], stale_from="yazim",
                              reason=workflow.REASONS["plan"], log=said)
        elif step == "yayin":
            record = ai_store.run(self.db, row["ref"]) if row["ref"] else None
            if not record or record["status"] not in ("awaiting_approval", "approved"):
                raise Conflict("Onaylanacak yayın paketi yok.")
            errors = [p["metin"] for p in record.get("problems") or [] if p.get("seviye") == "hata"]
            if errors:
                raise Conflict("Yayın paketi programın denetiminden geçmedi: " + " ".join(errors[:3]) + " “Düzeltme iste” ile yeniden yazdırın.")
            data = json.loads((self.data_dir / record["folder"] / publish.OUTPUT).read_text(encoding="utf-8-sig"))
            ai_store.update_run(self.db, record["id"], status="approved", decision_note=note or None, decided_at=ai_store.now())
            workflow.set_step(self.db, video_id, "yayin", "approved", note=note or None, ref=record["id"], log=said)
            self.write_version(video_id, "yayin", "Onaylandı", {
                "calisma": record["id"], "dosya": f"{record['folder']}/{publish.MARKDOWN}", "zamanlar": publish.ESTIMATED, "paket": data,
                "not": note or None, "ozet": f"{len(data.get('bolumler') or [])} bölüm (tahmini zamanlar) · {len(data.get('etiketler') or [])} etiket"})
        else:
            if not version_id:
                raise Conflict("Onaylarken hangi tonla devam edileceğini seçin.")
            version = text_store.version(self.db, version_id)
            if version is None or version["video_id"] != video_id:
                raise KeyError(version_id)
            self.text.select(version_id, note)
            workflow.mark_stale(self.db, video_id, "yayin", workflow.REASONS["kontrol"])      # a package of the earlier tone is old
            self.write_version(video_id, "kontrol", f"Onaylandı: {version['tone_name']}", {
                "ton": version["tone_name"], "surum": version["number"], "surum_kimligi": version_id, "kirmizi": version["red"],
                "sari": version["yellow"], "not": note or None, "ozet": f"{version['number']}. sürüm · {version['red']} kırmızı · {version['yellow']} sarı"})
        return self.step_view(video_id, step)

    def correction_estimate(self, video_id, step, note):
        """What "Düzeltme iste" will cost, before it starts (the same estimate box as every Claude step)."""
        video, row = self.decision_row(video_id, step, "correct")
        note = self.clean(note, required=True)
        if step == "baslik":
            if not video.get("run_id"):
                raise Conflict("Düzeltilecek başlık seçilmedi.")
            return self.claude.estimate_correction(video["run_id"], note)
        if step == "plan":
            return self.text.estimate_plan(video_id, note)
        if step == "yayin":
            return self.claude.estimate_correction(row["ref"], note)
        return None      # 5 · Kontrol: no Claude now; the cost is shown above "Yazımı başlat" in 4 · Yazım

    def correct(self, video_id, step, note):
        video, row = self.decision_row(video_id, step, "correct")
        note = self.clean(note, required=True)
        said = f"{workflow.label(step)}: düzeltme istendi. Kullanıcının düzeltme notu: {note}"
        if step == "baslik":
            if not video.get("run_id"):
                raise Conflict("Düzeltilecek başlık seçilmedi.")
            run_id = video["run_id"]
            self.write_version(video_id, "baslik", "Düzeltme istendi", {"baslik_tr": video["title_tr"], "baslik_en": video["title_en"], "not": note})
            started = self.claude.correct(run_id, note, video_id=video_id)          # sets the step running
            self.claude.release(video_id)
            workflow.log(self.db, video_id, "baslik", said)
            workflow.mark_stale(self.db, video_id, "paket", workflow.REASONS["baslik"])
            return {**self.step_view(video_id, step), "baslayan": started["id"]}
        if step == "plan":
            started = self.text.start_plan(video_id, note)                           # sets the step running
            if row["ref"] and row["ref"] != started["id"]:
                self.text.set_plan_approval(row["ref"], False)
            workflow.log(self.db, video_id, "plan", said)
            workflow.mark_stale(self.db, video_id, "yazim", workflow.REASONS["plan"])
            return {**self.step_view(video_id, step), "baslayan": started["id"]}
        if step == "yayin":
            started = self.claude.correct(row["ref"], note, video_id=video_id)                     # sets the step running
            workflow.log(self.db, video_id, "yayin", said)
            return {**self.step_view(video_id, step), "baslayan": started["id"]}
        self.write_version(video_id, "kontrol", "Düzeltme istendi", {"not": note})
        workflow.set_step(self.db, video_id, "kontrol", "waiting", note=note, log=said)
        workflow.set_step(self.db, video_id, "yazim", "ready", note=note,
                          log="4 · Yazım yeniden yazım için hazır: kontrolün düzeltme notu yazımda Claude'a verilecek.")
        return self.step_view(video_id, step)

    def reject(self, video_id, step, note=""):
        video, row = self.decision_row(video_id, step, "reject")
        note = self.clean(note)
        said = f"{workflow.label(step)} reddedildi. Not: {note or 'yok'}"
        if step == "baslik":
            if video.get("title_en"):
                self.write_version(video_id, "baslik", "Reddedildi", {"baslik_tr": video["title_tr"], "baslik_en": video["title_en"], "not": note or None})
            self.claude.release(video_id)
            workflow.set_step(self.db, video_id, "baslik", "ready", note=note or None, ref=None, stale_from="paket",
                              reason=workflow.REASONS["baslik"], log=said)
        elif step == "plan":
            if row["ref"] and text_store.run(self.db, row["ref"]):
                self.text.set_plan_approval(row["ref"], False)
            workflow.set_step(self.db, video_id, "plan", "ready", note=note or None, stale_from="yazim", reason=workflow.REASONS["plan"], log=said)
        elif step == "yayin":
            record = ai_store.run(self.db, row["ref"]) if row["ref"] else None
            if record and record["status"] == "awaiting_approval":
                ai_store.update_run(self.db, record["id"], status="rejected", decision_note=note or None, decided_at=ai_store.now())
            self.write_version(video_id, "yayin", "Reddedildi", {"calisma": row["ref"], "not": note or None})
            workflow.set_step(self.db, video_id, "yayin", "ready", note=note or None, log=said)
        else:
            self.write_version(video_id, "kontrol", "Reddedildi", {"not": note or None})
            workflow.set_step(self.db, video_id, "kontrol", "ready", note=note or None, log=said)
        return self.step_view(video_id, step)

    def clear_stale(self, video_id, step, note=""):
        """"Bu değişiklik etkilemiyor": the step returns to the status it had; the note goes to the status log."""
        video = self.video(video_id)
        inputs = None
        if step == "paket":
            from .evidence.pack import latest_done_run
            inputs = latest_done_run(self.db, video["destination_id"])
        try:
            workflow.clear_stale(self.db, video_id, step, self.clean(note), inputs)
        except workflow.StateError as exc:
            raise Conflict(str(exc)) from exc
        return self.step_view(video_id, step)
