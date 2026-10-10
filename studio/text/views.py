"""What the Video metni screens read (GÖREV-15, Adım 8): the step's options, text runs and their plan, the comparison of tones, a
version, its files and the choice ("Bu tonla devam et")."""
import json
from pathlib import Path

from ..ai import store as ai_store, tones as T
from ..database import Conflict
from ..evidence.pack import latest_done_run, moment
from . import document as D, store

WORDS_PER_MINUTE = 150
FILES = {"en": ("metin_EN.md", "text/markdown"), "tr": ("metin_TR.md", "text/markdown"), "seslendirme": ("seslendirme_EN.txt", "text/plain"),
         "kanitli": ("metin_EN_kanitli.md", "text/markdown"), "denetim": ("denetim.md", "text/markdown")}
NOTE_LATER = ("Türkçe düzeltme ve İngilizceye uyarlama bu görevde yok; Housing Atlas'taki makale ekranı orada oturduktan sonra ayrı bir "
              "görevde taşınacak.")


def minutes_of(words):
    return round(words / WORDS_PER_MINUTE, 1)


class TextViews:
    """Mixed into TextService."""

    def pack_state(self, video):
        """{"var", "eski", "metin"}: the video pack the next run will use (made again first when missing or older than the data)."""
        packs = (next((v for v in ai_store.videos(self.db, video["destination_id"]) if v["id"] == video["id"]), None) or {}).get("packs") or []
        if not packs:
            return {"var": False, "eski": False, "metin": "Paket önce yeniden üretilecek (bu videonun paketi yok).", "paket": None}
        latest = latest_done_run(self.db, video["destination_id"])
        made = moment(packs[0]["created_at"])
        stale = bool(latest and made is not None and made < moment(latest))
        return {"var": True, "eski": stale, "paket": packs[0]["id"],
                "metin": "Paket önce yeniden üretilecek (veri paketten sonra yeniden çekildi)." if stale else None}

    def options(self, video_id):
        video = ai_store.video(self.db, video_id)
        if video is None:
            raise KeyError(video_id)
        profile = self.profile_of(video["destination_id"])
        default = T.default_file(self.data_dir, video["destination_id"], profile)
        tone_list = [{"dosya": p.stem, "ad": T.item(p)["ad"], "ilk_cumle": T.item(p)["ilk_cumle"], "varsayilan": p.stem == default}
                     for p in T.tone_files(profile)]
        config = self.settings()
        return {"video": {k: video[k] for k in ("id", "title_en", "title_tr", "region_name")}, "tonlar": tone_list, "paket": self.pack_state(video),
                "calismalar": self.runs(video_id), "surumler": self.versions(video_id), "secim": self.selection(video_id),
                "ayarlar": {"oturum_siniri": config.get("claude_max_sessions"), "plandan_sonra_dur": config.get("claude_stop_after_plan")},
                "mesgul": self.busy(), "claude_mesgul": bool(self.claude.running_runs()), "not": NOTE_LATER}

    # ---- runs --------------------------------------------------------------------------------------------------------------------

    def usage_of(self, run_id):
        sessions = store.sessions(self.db, run_id)
        cost = sum((s["metrics"] or {}).get("cost_usd") or 0 for s in sessions)
        elapsed = sum((s["metrics"] or {}).get("elapsed_s") or 0 for s in sessions)
        tokens = sum(sum(v for k, v in (((s["metrics"] or {}).get("tokens")) or {}).items() if isinstance(v, (int, float))) for s in sessions)
        by_status = {}
        for s in sessions:
            by_status[s["status"]] = by_status.get(s["status"], 0) + 1
        return {"oturum": len(sessions), "durumlar": by_status, "maliyet_usd": round(cost, 4), "sure_s": round(elapsed, 1), "token": tokens}

    def actions(self, run):
        active = run["status"] in store.ACTIVE
        return {"devam": run["status"] in store.RESUMABLE or run["status"] == "waiting_limit", "durdur": active,
                "ton_ekle": bool(run.get("plan")) and not active, "plani_yeniden_yap": not active, "plani_goster": bool(run.get("plan"))}

    def run_summary(self, run):
        versions = store.versions(self.db, text_run_id=run["id"])
        return {k: run[k] for k in ("id", "video_id", "status", "status_label", "tones", "reason", "reason_text", "wait_until", "created_at",
                                    "updated_at", "finished_at", "replan_of", "pack_id")} | {
            "kullanim": self.usage_of(run["id"]), "surumler": [self.version_summary(v) for v in versions], "eylemler": self.actions(run),
            "plan_var": bool(run.get("plan"))}

    def runs(self, video_id):
        return [self.run_summary(r) for r in store.runs(self.db, video_id)]

    def view(self, run_id):
        run = store.run(self.db, run_id)
        if run is None:
            raise KeyError(run_id)
        state = run.get("state") or {}
        return {**self.run_summary(run), "plan": run.get("plan"), "plan_uyarilari": state.get("plan_uyarilari") or [],
                "elestiri": state.get("elestiri"), "plan_turu": state.get("plan_turu"),
                "oturumlar": [{k: s[k] for k in ("id", "step", "tone", "part", "round", "attempt", "status", "model", "effort", "error",
                                                 "created_at", "finished_at")} | {"sure_s": (s["metrics"] or {}).get("elapsed_s"),
                                                                                  "maliyet_usd": (s["metrics"] or {}).get("cost_usd")}
                              for s in store.sessions(self.db, run_id)]}

    # ---- versions -----------------------------------------------------------------------------------------------------------------

    def version_summary(self, version):
        selection = self.selection(version["video_id"])
        return {k: version[k] for k in ("id", "number", "text_run_id", "tone_file", "tone_name", "words", "sentences", "red", "yellow",
                                        "cost_usd", "tokens", "elapsed_s", "created_at", "pack_id")} | {
            "dakika": minutes_of(version["words"]), "secili": bool(selection and selection["version_id"] == version["id"]),
            "ton_var": self.tone_exists(version)}

    def tone_exists(self, version):
        try:
            profile = self.profile_of(version["destination_id"])
            T.find(profile, version["tone_file"])
            return True
        except (KeyError, Conflict):
            return False

    def versions(self, video_id):
        return [self.version_summary(v) for v in store.versions(self.db, video_id=video_id)]

    def document_of(self, version):
        path = self.data_dir / version["folder"] / "metin.json"
        data = path.read_bytes()
        from .engine import sha256_bytes
        if sha256_bytes(data) != version["json_sha256"]:
            raise Conflict("Sürümün dosyası kayıttakiyle aynı değil (değiştirilmiş olabilir); gösterilmedi.")
        return json.loads(data.decode("utf-8"))

    def version_view(self, version_id):
        version = store.version(self.db, version_id)
        if version is None:
            raise KeyError(version_id)
        document = self.document_of(version)
        report = json.loads((self.data_dir / version["folder"] / "denetim.json").read_text(encoding="utf-8"))
        video = ai_store.video(self.db, version["video_id"])
        return {**self.version_summary(version), "video": {k: video[k] for k in ("id", "title_en", "title_tr")}, "metin": document,
                "denetim": report, "denetim_md": (self.data_dir / version["folder"] / "denetim.md").read_text(encoding="utf-8"),
                "not": NOTE_LATER}

    def file(self, version_id, kind):
        version = store.version(self.db, version_id)
        if version is None or kind not in FILES:
            raise KeyError(version_id)
        name, media = FILES[kind]
        path = (self.data_dir / version["folder"] / name).resolve()
        if not path.is_relative_to((self.data_dir / "metin").resolve()) or not path.is_file():
            raise KeyError(version_id)
        self.document_of(version)                       # the version's JSON must still be the recorded one
        return path, media, f"{version['number']:02d}-{version['tone_file']}-{name}"

    # ---- comparison and choice ----------------------------------------------------------------------------------------------------

    def compare(self, video_id, run_id=None):
        """Columns: the versions (of a run, or every version of the video); rows: parts by their place in the plan (introduction,
        sections, re-hooks and transitions by their heading, closing)."""
        items = store.versions(self.db, text_run_id=run_id) if run_id else store.versions(self.db, video_id=video_id)
        columns, order = [], []
        for version in items:
            document = self.document_of(version)
            parts = {}
            for part in document["parcalar"]:
                key = part["baslik"] if part["tur"] == "gecis" else part["kimlik"]
                parts[key] = {"baslik": D.heading_of(part), "tur": part["tur"],
                              "tr": [" ".join(s["tr"] for s in p["cumleler"]) for p in part["paragraflar"]],
                              "en": [" ".join(s["en"] for s in p["cumleler"]) for p in part["paragraflar"]],
                              "isaretler": sum(1 for p in part["paragraflar"] for s in p["cumleler"] for w in s["uyarilar"]
                                               if w.get("tur") == "denetim" and w.get("seviye") == "kirmizi")}
                if key not in order:
                    order.append(key)
            columns.append({**self.version_summary(version), "parcalar": parts})
        order.sort(key=lambda key: row_rank(key))
        return {"video_id": video_id, "metin_calismasi": run_id, "satirlar": order, "sutunlar": columns,
                "secim": self.selection(video_id), "not": NOTE_LATER}

    def selection(self, video_id):
        chosen = store.selection(self.db, video_id)
        if not chosen:
            return None
        version = store.version(self.db, chosen["version_id"])
        return {**chosen, "surum_no": version["number"], "ton": version["tone_name"], "ton_dosya": version["tone_file"]}

    def select(self, version_id, note=None):
        version = store.version(self.db, version_id)
        if version is None:
            raise KeyError(version_id)
        store.select(self.db, version["video_id"], version_id, (note or "").strip() or None)
        return {"secim": self.selection(version["video_id"]), "secimler": store.selections(self.db, version["video_id"])}


def row_rank(key):
    """Order of the comparison rows: introduction, then per section its text, re-hooks after it and the transition to the next; closing."""
    if key == "giris":
        return (0, 0, 0)
    if key == "kapanis":
        return (9999, 0, 0)
    if key.startswith("bolum-"):
        return (int(key.split("-")[1]), 0, 0)
    if key.startswith("Yeniden kanca"):
        number = int("".join(ch for ch in key.split("(")[1].split(".")[0] if ch.isdigit()) or 0)
        return (number, 1, 0)
    if key.startswith("Geçiş"):
        digits = [int(x) for x in key.replace("→", " ").split() if x.isdigit()]
        return (digits[0] if digits else 0, 2, 0)
    return (5000, 0, 0)
