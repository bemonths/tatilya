"""HEDEF-04 A-7: 7 · Seslendirme — the plain English text for the voice, the uploaded audio and its match to the sentences.

- When 6 · Yayın paketi is approved the step writes the approved text as plain English (no marks, no sentence numbers) into
  `videolar/<video>/7_ses/metin/seslendirme_01.txt`, `_02`… (at most PART_LIMIT characters a part, never cut inside a sentence;
  paragraphs are kept) with `cumle_parca.json` (sentence number → part) next to them, and waits: "ses bekliyor".
- "Sesi yükle": mp3 or wav, one file or numbered parts (`_01`, `_02`… in the order of the text parts); the files are kept as they are
  under `7_ses/ses/NNN/`, their length is read with ffprobe (PATH, else E:\\KurguMotoru\\tools\\ffmpeg\\bin\\ffprobe.exe; a setting
  overrides) → "ses yüklendi".
- "Sesi cümlelerle eşleştir": a thin adapter over the Kurgu Motoru copy's recognizer (`workers/hizala.py`, JSON on stdin/stdout; the
  motor's folder and its Python are settings; a missing motor is a clear error). The recognized words are matched to the sentences
  here: sentence number → start/end (on the joined timeline of the parts) and the number of sentences not matched → "tamamlandı".
No Claude call; no ElevenLabs. Settings: `<data>/ayarlar_seslendirme.json` (paths only, nothing secret).
"""
import difflib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from . import workflow
from .database import Conflict
from .text import store as text_store

PART_LIMIT = 4500
SETTINGS_FILE = "ayarlar_seslendirme.json"
SETTING_KEYS = ("ffprobe_path", "kurgu_motoru_path", "kurgu_python_path")
FFPROBE_FALLBACK = Path(r"E:\KurguMotoru\tools\ffmpeg\bin\ffprobe.exe")
MOTOR_DEFAULT = Path(__file__).resolve().parents[1] / "work" / "kurgu-motoru"
PYTHON_FALLBACK = Path(r"E:\KurguMotoru\tools\py\.venv\Scripts\python.exe")
AUDIO_TYPES = (".mp3", ".wav")
STATE = "durum.json"
MAP_FILE = "cumle_parca.json"
MATCH_FILE = "eslesme.json"
NUMBERED = re.compile(r"_(\d{2})\.(mp3|wav)$", re.I)
NOT_READY = "Önce 6 · Yayın paketi onaylanmalı: seslendirme metni onaylı metinden hazırlanır."


# ---- settings ------------------------------------------------------------------------------------------------------------------------

def settings(data_dir):
    path = Path(data_dir) / SETTINGS_FILE
    try:
        stored = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        stored = {}
    return {k: str(stored.get(k) or "") for k in SETTING_KEYS}


def settings_view(data_dir):
    return {"settings": settings(data_dir), "varsayilan": {"ffprobe_path": f"PATH, yoksa {FFPROBE_FALLBACK}",
            "kurgu_motoru_path": str(MOTOR_DEFAULT), "kurgu_python_path": f"<motor>\\tools\\py\\.venv\\Scripts\\python.exe, yoksa {PYTHON_FALLBACK}"}}


def save_settings(data_dir, body):
    values = settings(data_dir)
    for key in SETTING_KEYS:
        if key in (body or {}):
            value = str(body[key] or "").strip().strip('"')
            if len(value) > 500:
                raise Conflict("Yol çok uzun.")
            values[key] = value
    path = Path(data_dir) / SETTINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(values, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return settings_view(data_dir)


# ---- the text ------------------------------------------------------------------------------------------------------------------------

def paragraphs_of(metin):
    """The approved text's paragraphs, each a list of (sentence number, English sentence)."""
    out = []
    for part in metin.get("parcalar") or []:
        for para in part.get("paragraflar") or []:
            found = [(int(c["no"]), " ".join(str(c["en"]).split())) for c in para.get("cumleler") or [] if c.get("en") and c.get("no") is not None]
            if found:
                out.append(found)
    return out


def render(part):
    return "\n\n".join(" ".join(en for _, en in para) for para in part) + "\n"


def split_parts(paragraphs, limit=PART_LIMIT):
    """Parts of at most `limit` characters; a paragraph longer than that is cut between sentences, a sentence is never cut."""
    pieces = []
    for para in paragraphs:
        chunk = []
        for sentence in para:
            if chunk and len(" ".join(en for _, en in chunk + [sentence])) > limit:
                pieces.append(chunk)
                chunk = []
            chunk.append(sentence)
        if chunk:
            pieces.append(chunk)
    parts, current = [], []
    for piece in pieces:
        if current and len(render(current + [piece])) - 1 > limit:
            parts.append(current)
            current = []
        current.append(piece)
    if current:
        parts.append(current)
    return parts


# ---- audio and its length ------------------------------------------------------------------------------------------------------------

def ffprobe_of(cfg):
    given = cfg.get("ffprobe_path")
    if given:
        if not Path(given).is_file():
            raise Conflict(f"ffprobe bulunamadı: {given}. 7 · Seslendirme → Ses ayarları'nda yolu düzeltin.")
        return given
    found = shutil.which("ffprobe") or (str(FFPROBE_FALLBACK) if FFPROBE_FALLBACK.is_file() else None)
    if not found:
        raise Conflict(f"ffprobe bulunamadı (PATH'te ve {FFPROBE_FALLBACK} yolunda yok). 7 · Seslendirme → Ses ayarları'nda yolunu yazın.")
    return found


def duration_of(path, cfg):
    """The audio's length in seconds (ffprobe)."""
    done = subprocess.run([ffprobe_of(cfg), "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        return round(float(done.stdout.strip().splitlines()[0]), 3)
    except (ValueError, IndexError):
        raise Conflict(f"Sesin süresi okunamadı ({Path(path).name}): {(done.stderr or '').strip()[:300] or 'ffprobe cevap vermedi'}") from None


def audio_check(files, part_count):
    """Problems of an uploaded set: one file, or numbered parts _01.._NN in sequence and as many as the text parts."""
    problems = []
    if len(files) > 1:
        numbers = []
        for name in files:
            found = NUMBERED.search(name)
            if not found:
                problems.append(f"“{name}” numaralı değil: birden çok parça _01, _02… diye numaralanmalı.")
            else:
                numbers.append(int(found.group(1)))
        if numbers and sorted(numbers) != list(range(1, len(numbers) + 1)):
            problems.append("Parça numaraları 01'den başlayıp sırayla gitmeli.")
        if len(files) != part_count:
            problems.append(f"Ses parça sayısı ({len(files)}) metin parça sayısıyla ({part_count}) aynı değil.")
    return problems


# ---- the adapter over the Kurgu Motoru recognizer ------------------------------------------------------------------------------------

def motor_command(cfg):
    """[python, worker] of the Kurgu Motoru copy; a clear error when it is not there."""
    motor = Path(cfg.get("kurgu_motoru_path") or MOTOR_DEFAULT)
    worker = motor / "workers" / "hizala.py"
    if not worker.is_file():
        raise Conflict(f"Kurgu Motoru bulunamadı: {worker} yok. 7 · Seslendirme → Ses ayarları'nda motorun klasörünü yazın.")
    candidates = [Path(cfg["kurgu_python_path"])] if cfg.get("kurgu_python_path") else [motor / "tools" / "py" / ".venv" / "Scripts" / "python.exe", PYTHON_FALLBACK]
    python = next((p for p in candidates if p.is_file()), None)
    if python is None:
        raise Conflict(f"Kurgu Motoru'nun Python'u bulunamadı ({', '.join(map(str, candidates))}). Ses ayarları'nda yolunu yazın.")
    return [str(python), str(worker)]


def motor_cache_env(motor):
    """The model caches the motor itself uses (`config/tools.json` → `cacheRoots.hf` / `.torch`, as its own `toolEnv`): the downloaded
    models are found there and nothing is downloaded (or symlinked, which Windows refuses without the privilege) again (HEDEF-04 A-8)."""
    try:
        roots = (json.loads((Path(motor) / "config" / "tools.json").read_text(encoding="utf-8")) or {}).get("cacheRoots") or {}
    except (OSError, ValueError, AttributeError):
        return {}
    names = {"hf": "HF_HOME", "torch": "TORCH_HOME"}
    return {names[k]: str(Path(v)) for k, v in roots.items() if k in names and isinstance(v, str) and v}


def transcribe_part(command, audio, work_dir, cfg):
    """The recognized words of one audio file: converted to 16 kHz mono wav (the worker's input), then `transcribe`."""
    probe = Path(ffprobe_of(cfg))
    ffmpeg = probe.with_name(probe.name.replace("ffprobe", "ffmpeg"))
    ffmpeg = str(ffmpeg) if ffmpeg.is_file() else shutil.which("ffmpeg")
    if not ffmpeg:
        raise Conflict("ffmpeg bulunamadı (ffprobe'un yanında ve PATH'te yok).")
    work_dir.mkdir(parents=True, exist_ok=True)
    wav = work_dir / f"{Path(audio).stem}.16k.wav"
    hidden = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    converted = subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", str(wav)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800, creationflags=hidden)
    if converted.returncode != 0:
        raise Conflict(f"Ses wav'a çevrilemedi: {converted.stderr.strip()[:300]}")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    env.update(motor_cache_env(Path(command[1]).parents[1]))
    env.setdefault("HF_HOME", str(Path(command[1]).parents[1] / "cache" / "models"))
    env.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    done = subprocess.run(command, input=json.dumps({"command": "transcribe", "audio": str(wav), "language": "en", "model": "large-v3"}),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=7200, cwd=str(Path(command[1]).parents[1]),
                          env=env, creationflags=hidden)
    try:
        answer = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise Conflict(f"Kurgu Motoru'nun hizalaması cevap vermedi: {done.stderr.strip()[-300:]}") from None
    if not answer.get("ok"):
        raise Conflict(f"Kurgu Motoru'nun hizalaması hata verdi: {answer.get('error')}")
    return answer.get("words") or []


def tokens(text):
    return re.findall(r"[a-z0-9]+", str(text).lower().replace("'", "").replace("’", ""))


def match_sentences(sentences, words, minimum=0.5):
    """Sentence number → start/end from recognized words ({word, start, end}); a sentence with less than half its words found is
    not matched."""
    said, owner = [], []
    for no, en in sentences:
        for token in tokens(en):
            said.append(token)
            owner.append(no)
    heard, word_of = [], []
    for index, word in enumerate(words):
        for token in tokens(word.get("word", "")):
            heard.append(token)
            word_of.append(index)
    hits = {}
    for a, b, size in difflib.SequenceMatcher(None, said, heard, autojunk=False).get_matching_blocks():
        for k in range(size):
            hits.setdefault(owner[a + k], []).append(word_of[b + k])
    out, missing = [], 0
    for no, en in sentences:
        total, got = len(tokens(en)), sorted(hits.get(no, []))
        timed = [words[i] for i in got if words[i].get("start") is not None and words[i].get("end") is not None]
        ratio = len(got) / total if total else 0.0
        if timed and ratio >= minimum:
            out.append({"no": no, "baslangic": round(float(timed[0]["start"]), 3), "bitis": round(float(timed[-1]["end"]), 3), "oran": round(ratio, 2)})
        else:
            missing += 1
            out.append({"no": no, "baslangic": None, "bitis": None, "oran": round(ratio, 2)})
    return {"cumleler": out, "cumle_sayisi": len(sentences), "eslesmeyen": missing, "eslesen": len(sentences) - missing}


# ---- the step ------------------------------------------------------------------------------------------------------------------------

class VoiceStep:
    def __init__(self, flow):
        self.flow = flow

    @property
    def db(self):
        return self.flow.db

    def folder(self, video_id):
        return self.flow.version_folder(video_id, "ses")

    def state(self, video_id):
        try:
            return json.loads((self.folder(video_id) / STATE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def save(self, video_id, state):
        folder = self.folder(video_id)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / STATE).write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def approved_text(self, video_id):
        chosen = text_store.selection(self.db, video_id)
        version = text_store.version(self.db, chosen["version_id"]) if chosen else None
        if version is None:
            raise Conflict(NOT_READY)
        try:
            metin = json.loads((self.flow.data_dir / version["folder"] / "metin.json").read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            raise Conflict(f"Onaylı metin okunamadı: {version['folder']}/metin.json") from None
        return version, metin

    def auto(self, video_id):
        """A ready step writes its text as soon as it is shown (also for videos whose 6 was approved before this version)."""
        if workflow.voice_status(workflow.step(self.db, video_id, "ses")) == "ready":
            try:
                self.prepare(video_id)
            except Conflict:
                pass

    def prepare(self, video_id, by_user=False):
        row, yayin = workflow.step(self.db, video_id, "ses"), workflow.step(self.db, video_id, "yayin")
        if yayin["status"] not in workflow.COMPLETE or workflow.voice_status(row) == "waiting":
            raise Conflict(NOT_READY)
        version, metin = self.approved_text(video_id)
        parts = split_parts(paragraphs_of(metin))
        if not parts:
            raise Conflict("Onaylı metinde İngilizce cümle yok.")
        folder = self.folder(video_id) / "metin"
        if folder.is_dir() and any(folder.iterdir()):                       # the earlier text stays, moved aside
            old = self.folder(video_id) / "metin-eski"
            old.mkdir(parents=True, exist_ok=True)
            folder.rename(old / f"{len(list(old.iterdir())) + 1:03d}")
        folder.mkdir(parents=True, exist_ok=True)
        files, mapping = [], {}
        for number, part in enumerate(parts, 1):
            name = f"seslendirme_{number:02d}.txt"
            text = render(part)
            (folder / name).write_text(text, encoding="utf-8")
            nos = [no for para in part for no, _ in para]
            mapping.update({str(no): number for no in nos})
            files.append({"parca": number, "dosya": name, "karakter": len(text.strip()), "ilk": nos[0], "son": nos[-1], "cumle_sayisi": len(nos)})
        (folder / MAP_FILE).write_text(json.dumps({"surum_id": version["id"], "parca_siniri": PART_LIMIT, "parcalar": files, "cumleler": mapping},
                                                  ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        info = {"surum_id": version["id"], "parcalar": files, "cumle_sayisi": len(mapping), "karakter": sum(f["karakter"] for f in files)}
        self.save(video_id, {"metin": info, "ses": None, "eslesme": None})
        self.flow.write_version(video_id, "ses", "Metin hazırlandı", {**info, "ozet": f"{len(files)} parça · {info['cumle_sayisi']} cümle"})
        workflow.set_step(self.db, video_id, "ses", "awaiting_audio",
                          log=f"7 · Seslendirme: metin {'yeniden ' if by_user else ''}hazırlandı ({len(files)} parça); ses bekliyor.")
        return self.flow.step_view(video_id, "ses")

    def upload(self, video_id, name, data, new):
        state = self.state(video_id)
        if not state.get("metin") or workflow.voice_status(workflow.step(self.db, video_id, "ses")) not in ("awaiting_audio", "audio_ready", "done", "error"):
            raise Conflict("Önce seslendirme metni hazırlanmalı; ses metin hazırken yüklenir.")
        name = Path(str(name or "").replace("\\", "/")).name
        if Path(name).suffix.lower() not in AUDIO_TYPES:
            raise Conflict("Ses mp3 ya da wav olmalı.")
        if not data:
            raise Conflict("Dosya boş.")
        root = self.folder(video_id) / "ses"
        current = (state.get("ses") or {}).get("klasor")
        if new or not current:
            root.mkdir(parents=True, exist_ok=True)
            current = f"{len([p for p in root.iterdir() if p.is_dir()]) + 1:03d}"
        target = root / current
        target.mkdir(parents=True, exist_ok=True)
        (target / name).write_bytes(data)
        cfg = settings(self.flow.data_dir)
        names = sorted(p.name for p in target.iterdir() if p.suffix.lower() in AUDIO_TYPES)
        lengths = {n: duration_of(target / n, cfg) for n in names}
        problems = audio_check(names, len(state["metin"]["parcalar"]))
        state["ses"] = {"klasor": current, "dosyalar": [{"ad": n, "sure_s": lengths[n]} for n in names],
                        "toplam_s": round(sum(lengths.values()), 3), "sorunlar": problems}
        state["eslesme"] = None
        self.save(video_id, state)
        self.flow.write_version(video_id, "ses", "Ses yüklendi", {**state["ses"], "ozet": f"{len(names)} dosya · {state['ses']['toplam_s']} sn"})
        workflow.set_step(self.db, video_id, "ses", "awaiting_audio" if problems else "audio_ready",
                          log=f"7 · Seslendirme: ses yüklendi ({name}).")
        return self.flow.step_view(video_id, "ses")

    def match(self, video_id):
        state = self.state(video_id)
        audio = state.get("ses") or {}
        if workflow.voice_status(workflow.step(self.db, video_id, "ses")) not in ("audio_ready", "done") or not audio.get("dosyalar"):
            raise Conflict("Önce ses yüklenmeli (parçalar metin parçalarıyla aynı sayıda ve sırada).")
        cfg = settings(self.flow.data_dir)
        command = motor_command(cfg)
        _, metin = self.approved_text(video_id)
        sentences = [s for para in paragraphs_of(metin) for s in para]
        folder = self.folder(video_id) / "ses" / audio["klasor"]
        words, offset = [], 0.0
        for item in audio["dosyalar"]:
            for word in transcribe_part(command, folder / item["ad"], self.folder(video_id) / "hizalama", cfg):
                moved = dict(word)
                for key in ("start", "end"):
                    if moved.get(key) is not None:
                        moved[key] = float(moved[key]) + offset
                words.append(moved)
            offset += float(item["sure_s"] or 0)
        result = match_sentences(sentences, words)
        out = self.folder(video_id) / "eslesme"
        out.mkdir(parents=True, exist_ok=True)
        (out / MATCH_FILE).write_text(json.dumps({"ses_klasoru": audio["klasor"], "kelime_sayisi": len(words), **result}, ensure_ascii=False, indent=1) + "\n",
                                      encoding="utf-8")
        state["eslesme"] = {k: result[k] for k in ("cumle_sayisi", "eslesen", "eslesmeyen")} | {"kelime_sayisi": len(words)}
        self.save(video_id, state)
        self.flow.write_version(video_id, "ses", "Eşleştirildi", {**state["eslesme"], "ozet": f"{result['eslesen']}/{result['cumle_sayisi']} cümle eşleşti"})
        workflow.set_step(self.db, video_id, "ses", "done", log=f"7 · Seslendirme: ses cümlelerle eşleştirildi; eşleşmeyen {result['eslesmeyen']} cümle.")
        return self.flow.step_view(video_id, "ses")

    def open_folder(self, video_id, which="metin"):
        folder = self.folder(video_id) / ("metin" if which == "metin" else "ses")
        if not folder.is_dir():
            raise Conflict("Klasör henüz yok.")
        if hasattr(os, "startfile"):
            os.startfile(str(folder))
        return {"klasor": str(folder)}

    def view(self, video_id):
        state, base = self.state(video_id), self.folder(video_id)
        metin = state.get("metin")
        if metin:
            metin = {**metin, "klasor": str(base / "metin"), "eslesme_dosyasi": str(base / "metin" / MAP_FILE), "parca_sayisi": len(metin["parcalar"]),
                     "dosyalar": [{**f, "yol": str(base / "metin" / f["dosya"])} for f in metin["parcalar"]]}
        audio = state.get("ses")
        if audio:
            audio = {**audio, "klasor": str(base / "ses" / audio["klasor"])}
        found = state.get("eslesme")
        if found:
            try:
                rows = json.loads((base / "eslesme" / MATCH_FILE).read_text(encoding="utf-8"))["cumleler"]
            except (OSError, ValueError, KeyError):
                rows = []
            found = {**found, "dosya": str(base / "eslesme" / MATCH_FILE), "ilk_cumleler": rows[:12]}
        return {"metin": metin, "ses": audio, "eslesme": found, "ayarlar": settings_view(self.flow.data_dir)}
