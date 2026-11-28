"""HEDEF-04 A-8: 8 · Kurgu paketi — the package 30A Studio gives to the Kurgu Motoru (`kurgu-paket/1`) and "Kurguya gönder".

Deterministic: no Claude call. The package is built from what the earlier steps left:
- `script.json`: the approved text (5 · Kontrol ve ton seçimi) as sections and sentences. A sentence's id is `c<number>` (the sentence
  number of the approved text, so it stays the same when the package is built again); `translation` is its Turkish, `data` the evidence
  rows it cites, `mentions.numbers` the numbers it says (with `value` and `ref` when the number is one of a cited row's values),
  `mentions.places` the destination's region names (and the cited rows' scopes) it says. A transition part ("Geçiş …") joins the section
  before it; a section's `name` (video language) is the chapter title of the approved 6 · Yayın paketi when their counts agree.
- `data.json`: every cited evidence row as a record (`id` = the row's K-id, `kind` = its block, `fields` = value, unit, scope, wording,
  quartiles …); the rows' sources are the package's `sources`.
- `scenes.json`: card suggestions, not a cut: the first sourced number of a row → `rakam-karti` with `{"$data": "K….deger"}`, the first
  mention of a place → `alt-bant`, the first sentence otherwise → `baslik-karti`. No sound is asked for anywhere; card and transition
  sounds come only from the channel profile of the motor (its own style and catalog; the channel id is a setting).
- Audio (7 · Seslendirme): the uploaded file(s) (several parts are joined with ffmpeg) and, when every sentence was matched, the
  sentence times (`audio/zamanlar.json`, the motor then does not align again); otherwise only the file (the motor aligns) — and without
  audio the package is built all the same (the project is set up silent; times empty).
"Kurguya gönder" copies the package into the motor copy's folder (`<motor>/cache/30a-paketler/<video>-NNN/`) and runs
`pnpm -s kurgu paket dogrula <folder>` and, when that passes, `pnpm -s kurgu paket ice-al <folder>` (the second time with
`--guncelle projects/<project>`) in the motor's folder; the output is shown on the screen. Settings: `<data>/ayarlar_kurgu.json`
(pnpm and the channel id) and the motor's folder, which is the same setting as 7 · Seslendirme's (`ayarlar_seslendirme.json`).
"""
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import voice, workflow
from .database import Conflict
from .text import numbers as N

FORMAT = "kurgu-paket/1"
SETTINGS_FILE = "ayarlar_kurgu.json"
SETTING_KEYS = ("pnpm_path", "kurgu_kanali")
DEFAULT_CHANNEL = "_ornek"
STATE = "durum.json"
INBOX = Path("cache") / "30a-paketler"
NOT_READY = "Önce 6 · Yayın paketi onaylanmalı: kurgu paketi onaylı metinden kurulur."
PROJECT_LINE = re.compile(r"Proje:\s*([A-Za-z0-9._-]+)\s*→")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
SECTION_NAMES = {"giris": "Introduction", "kapanis": "Closing"}
CARD_MAX = 12.0                    # seconds; the motor's cards last 3–12 s (alt-bant, rakam-karti; baslik-karti 2–12) in _ornek
CARD_MIN = 3.0                     # a shorter span is given 3 s: the card overlaps the next one (the motor puts it on an upper track)


# ---- settings ------------------------------------------------------------------------------------------------------------------------

def settings(data_dir):
    path = Path(data_dir) / SETTINGS_FILE
    try:
        stored = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        stored = {}
    out = {k: str(stored.get(k) or "") for k in SETTING_KEYS}
    out["kurgu_motoru_path"] = voice.settings(data_dir)["kurgu_motoru_path"]
    return out


def settings_view(data_dir):
    return {"settings": settings(data_dir), "varsayilan": {"pnpm_path": "PATH'teki pnpm", "kurgu_kanali": DEFAULT_CHANNEL,
                                                          "kurgu_motoru_path": str(voice.MOTOR_DEFAULT)}}


def save_settings(data_dir, body):
    body = body or {}
    values = {k: v for k, v in settings(data_dir).items() if k in SETTING_KEYS}
    for key in SETTING_KEYS:
        if key in body:
            value = str(body[key] or "").strip().strip('"')
            if len(value) > 500:
                raise Conflict("Değer çok uzun.")
            if key == "kurgu_kanali" and value and not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
                raise Conflict("Kanal kimliği yalnız harf, rakam, tire ve alt çizgi olabilir.")
            values[key] = value
    if "kurgu_motoru_path" in body:
        voice.save_settings(data_dir, {"kurgu_motoru_path": body["kurgu_motoru_path"]})
    path = Path(data_dir) / SETTINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(values, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return settings_view(data_dir)


def motor_dir(cfg):
    folder = Path(cfg.get("kurgu_motoru_path") or voice.MOTOR_DEFAULT)
    if not (folder / "package.json").is_file():
        raise Conflict(f"Kurgu Motoru bulunamadı: {folder} klasöründe package.json yok. Ayarlar → Kurgu Motoru'nda motorun klasörünü yazın.")
    return folder


def pnpm_of(cfg):
    given = cfg.get("pnpm_path")
    if given:
        if not Path(given).is_file():
            raise Conflict(f"pnpm bulunamadı: {given}. Ayarlar → Kurgu Motoru'nda yolu düzeltin.")
        return given
    found = shutil.which("pnpm")
    if not found:
        raise Conflict("pnpm bulunamadı (PATH'te yok). Ayarlar → Kurgu Motoru'nda yolunu yazın.")
    return found


def run_motor(cfg, args, timeout=3600):
    """`pnpm -s kurgu <args>` in the motor's folder → (exit code, output without colour codes)."""
    command = [pnpm_of(cfg), "-s", "kurgu", *args]
    env = {**os.environ, "NO_COLOR": "1", "FORCE_COLOR": "0"}
    try:
        done = subprocess.run(command, cwd=str(motor_dir(cfg)), capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return 124, f"Kurgu Motoru {timeout} sn içinde bitmedi: {' '.join(args)}"
    return done.returncode, ANSI.sub("", (done.stdout or "") + (("\n" + done.stderr) if done.stderr else "")).strip()


# ---- the package ---------------------------------------------------------------------------------------------------------------------

def number_or_none(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and re.fullmatch(r"-?\d+(\.\d+)?", value.strip()):
        number = float(value)
        return int(number) if number.is_integer() else number
    return None


def source_id(source):
    if source.get("referans"):
        base = str(source["referans"])
    elif source.get("sha256"):
        base = f"kaynak-{str(source['sha256'])[:12]}"
    else:
        base = "kaynak-" + re.sub(r"[^a-z0-9]+", "-", str(source.get("ad") or "bilinmiyor").lower()).strip("-")[:40]
    return re.sub(r"[^A-Za-z0-9_-]+", "-", base)[:64] or "kaynak"


def record_of(row, sources):
    """An evidence row as a data record; its source joins `sources` (id → package source)."""
    fields = {"deger": number_or_none(row.get("deger")) if number_or_none(row.get("deger")) is not None else row.get("deger"),
              "birim": row.get("birim"), "kapsam": row.get("kapsam"), "ifade": row.get("ifade"), "ifade_en": row.get("ifade_en"),
              "deger_ek": row.get("deger_ek"), "orneklem": row.get("orneklem"), "etiket": row.get("etiket")}
    for extra in row.get("ek_degerler") or []:
        if extra.get("tur") and number_or_none(extra.get("deger")) is not None:
            fields.setdefault(re.sub(r"[^A-Za-z0-9_]", "_", str(extra["tur"])), number_or_none(extra["deger"]))
    fields = {k: v for k, v in fields.items() if v not in (None, "")}
    table = row.get("tablo") or {}
    record = {"id": row["id"], "kind": row.get("blok") or "kanit", "title": str(row.get("kapsam") or table.get("satir") or row["id"])[:120],
              "fields": fields}
    source = row.get("kaynak") or {}
    if source.get("ad"):
        sid = source_id(source)
        entry = {"id": sid, "name": str(source["ad"]), "attribution": str(source.get("sahibi") or source["ad"])}
        if source.get("url"):
            entry["url"] = source["url"]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(source.get("erisim_tarihi") or "")):
            entry["accessedAt"] = source["erisim_tarihi"]
        sources.setdefault(sid, entry)
        record["sources"] = [sid]
    return record


def value_ref(mention, rows):
    """(record id, field, value) of the cited row value the number says, or None."""
    for row in rows:
        record = None
        candidates = [("deger", number_or_none(row.get("deger")), N.unit_kind(row.get("birim")))]
        for extra in row.get("ek_degerler") or []:
            kind = "percent" if extra.get("tur") == "pay" else N.unit_kind(extra.get("birim"))
            candidates.append((re.sub(r"[^A-Za-z0-9_]", "_", str(extra.get("tur") or "")), number_or_none(extra.get("deger")), kind))
        for field, value, kind in candidates:
            if value is None or not field:
                continue
            try:
                if N.holds(mention, float(value), kind):
                    record = (row["id"], field, value)
            except (TypeError, ValueError):
                continue
            if record:
                return record
    return None


def places_in(text, names):
    found = []
    for name in names:
        if name and re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", text, re.I) and name not in found:
            found.append(name)
    return sorted(found, key=lambda n: text.lower().find(n.lower()))


def sections_of(metin, chapters):
    """[(section, [(part, sentence)…])…]: a transition part joins the section before it."""
    out = []
    for part in metin.get("parcalar") or []:
        sentences = [s for para in part.get("paragraflar") or [] for s in para.get("cumleler") or [] if s.get("en") and s.get("no") is not None]
        if part.get("tur") == "gecis" and out:
            out[-1][1].extend((part, s) for s in sentences)
            continue
        out.append(({"id": re.sub(r"[^A-Za-z0-9_-]+", "-", str(part.get("kimlik") or f"bolum-{len(out) + 1}"))[:64],
                     "tur": part.get("tur"), "translation": str(part.get("baslik") or "")}, [(part, s) for s in sentences]))
    titles = [c.get("baslik_en") for c in chapters or [] if c.get("baslik_en")]
    numbered = 0
    for index, (section, _) in enumerate(out):
        if section["tur"] == "bolum":
            numbered += 1
        section["name"] = (titles[index] if len(titles) == len(out) else
                           SECTION_NAMES.get(section["tur"]) or (f"Part {numbered}" if section["tur"] == "bolum" else section["translation"] or section["id"]))
    return [(s, items) for s, items in out if items]


def build(metin, rows, *, name, channel, regions=(), chapters=None, title_en=None, timings=None, audio_total=None):
    """The four files of the package (dicts) from the approved text, the evidence rows and (optionally) the sentence times
    {number: (start, end)} — complete times only."""
    by_id = {row["id"]: row for row in rows}
    sources, records, sentences, scenes = {}, {}, [], []
    region_names = list(regions)
    shown_places, shown_refs = set(), set()
    sections = sections_of(metin, chapters)
    for section, items in sections:
        for index, (part, s) in enumerate(items):
            no, en = int(s["no"]), " ".join(str(s["en"]).split())
            cited = [by_id[i] for i in s.get("kanitlar") or [] if i in by_id]
            for row in cited:
                records.setdefault(row["id"], record_of(row, sources))
            sentence = {"id": f"c{no}", "section": section["id"], "text": en}
            if s.get("tr"):
                sentence["translation"] = " ".join(str(s["tr"]).split())
            if cited:
                sentence["data"] = [row["id"] for row in cited]
            numbers, refs = [], []
            for mention in N.mentions(en):
                found = value_ref(mention, cited)
                if found:
                    numbers.append({"text": mention.text, "value": found[2], "ref": f"{found[0]}.{found[1]}"})
                    refs.append((found, mention))
                else:
                    numbers.append({"text": mention.text})
            names = region_names + [str(r.get("kapsam")) for r in cited if r.get("kapsam") and len(str(r.get("kapsam"))) <= 50]
            places = places_in(en, list(dict.fromkeys(names)))
            mentions = {k: v for k, v in (("numbers", numbers), ("places", places)) if v}
            if mentions:
                sentence["mentions"] = mentions
            if section["tur"] == "giris" and index == 0 and not sentences:
                sentence["markers"] = ["hook"]
            elif part.get("tur") == "gecis" and "kanca" in str(part.get("baslik") or "").lower() and s is first_of(part):
                sentence["markers"] = ["midHook"]
            sentences.append(sentence)
            scene = None
            new_ref = next(((f, m) for f, m in refs if f"{f[0]}.{f[1]}" not in shown_refs), None)
            new_place = next((p for p in places if p not in shown_places), None)
            if new_ref:
                (rid, field, _), mention = new_ref
                shown_refs.add(f"{rid}.{field}")
                fields = {"title": str(records[rid]["title"])[:70], "value": {"$data": f"{rid}.{field}"}}
                if mention.kind == "money":
                    fields["prefix"] = "$"
                elif mention.kind == "percent":
                    fields["suffix"] = "%"
                scene = {"template": "rakam-karti", "fields": fields, "rationale": f"Kaynaklı rakam ilk kez söyleniyor ({rid})"}
            elif new_place:
                shown_places.add(new_place)
                scene = {"template": "alt-bant", "fields": {"title": new_place[:50]}, "rationale": f"Yer adı ilk kez söyleniyor ({new_place})"}
            elif not scenes:
                scene = {"template": "baslik-karti", "fields": {"title": str(title_en or section["name"])[:80], "backdrop": "dim"},
                         "rationale": "Videonun açılışı"}
            if scene:
                scenes.append({"id": f"s-c{no}", "sentence": f"c{no}", **scene})
    if timings and scenes:
        scenes = cover(scenes, sentences, {s["id"]: s["name"] for s, _ in sections}, timings,
                       max([audio_total or 0] + [e for _, e in timings.values()]))
    package = {"format": FORMAT, "name": name, "channel": channel, "languages": {"video": "en", "user": "tr"}, "aspect": "16:9",
               "resolution": "1080p", "fps": 30, "sources": list(sources.values())}
    script = {"sections": [{"id": s["id"], "name": s["name"], "translation": s["translation"] or s["name"]} for s, _ in sections],
              "sentences": sentences}
    return {"package.json": package, "script.json": script, "data.json": {"records": list(records.values())}, "scenes.json": {"scenes": scenes}}


def cover(scenes, sentences, section_names, timings, end, longest=CARD_MAX):
    """With sentence times the cards cover the audio from 0 to its end (the motor stops the render at a frame without any picture):
    a sentence without a card where the card before it would run longer than `longest` gets a section title card, each card runs
    until the next one, and a card still longer than `longest` goes on as a title card on the same sentence (offset)."""
    by_sentence = {sc["sentence"]: sc for sc in scenes}
    start = lambda sid: timings[int(sid[1:])][0]
    order = [s for s in sentences if int(s["id"][1:]) in timings]
    cards = [by_sentence[s["id"]] for s in order if s["id"] in by_sentence]
    for s in order:
        if s["id"] in by_sentence:
            continue
        before = [c for c in cards if start(c["sentence"]) <= start(s["id"])]
        after = [c for c in cards if start(c["sentence"]) > start(s["id"])]
        if before and (start(after[0]["sentence"]) if after else end) - start(before[-1]["sentence"]) > longest:
            card = {"id": f"s-{s['id']}", "sentence": s["id"], "template": "baslik-karti",
                    "fields": {"title": str(section_names.get(s["section"]) or "30A")[:80], "backdrop": "dim"},
                    "rationale": "Ara başlık: görüntüsüz aralık kalmasın"}
            by_sentence[s["id"]] = card
            cards = sorted(cards + [card], key=lambda c: start(c["sentence"]))
    out = []
    for i, card in enumerate(cards):
        at = start(card["sentence"])
        offset = -at if i == 0 else 0.0
        until = start(cards[i + 1]["sentence"]) if i + 1 < len(cards) else end
        span = max(0.5, until - (at + offset))
        card["offset"], card["duration"] = round(offset, 3), round(max(CARD_MIN, min(span, longest)), 3)
        out.append(card)
        n = 2
        length = timings[int(card["sentence"][1:])][1] - at          # a card goes on only inside its own sentence (the motor's link)
        while span > longest and offset + longest < length - 0.5:
            offset, span = offset + longest, span - longest
            out.append({"id": f"{card['id']}-{n}", "sentence": card["sentence"], "template": "baslik-karti",
                        "fields": {"title": str(section_names.get(next((s["section"] for s in order if s["id"] == card["sentence"]), "")) or "30A")[:80],
                                   "backdrop": "dim"}, "rationale": "Ara başlık: görüntüsüz aralık kalmasın",
                        "offset": round(offset, 3), "duration": round(max(CARD_MIN, min(span, longest)), 3)})
            n += 1
    return out


def first_of(part):
    for para in part.get("paragraflar") or []:
        for s in para.get("cumleler") or []:
            if s.get("en") and s.get("no") is not None:
                return s
    return None


def join_audio(files, target, cfg):
    """One file as it is; several parts joined into one wav (ffmpeg next to ffprobe, or on PATH)."""
    if len(files) == 1:
        out = target.with_suffix(Path(files[0]).suffix.lower())
        shutil.copyfile(files[0], out)
        return out
    probe = Path(voice.ffprobe_of(cfg))
    ffmpeg = probe.with_name(probe.name.replace("ffprobe", "ffmpeg"))
    ffmpeg = str(ffmpeg) if ffmpeg.is_file() else shutil.which("ffmpeg")
    if not ffmpeg:
        raise Conflict("ffmpeg bulunamadı (ffprobe'un yanında ve PATH'te yok); ses parçaları birleştirilemedi.")
    out = target.with_suffix(".wav")
    inputs = [a for f in files for a in ("-i", str(f))]
    graph = "".join(f"[{i}:a]" for i in range(len(files))) + f"concat=n={len(files)}:v=0:a=1[a]"
    done = subprocess.run([ffmpeg, "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[a]", "-ar", "48000", str(out)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if done.returncode != 0:
        raise Conflict(f"Ses parçaları birleştirilemedi: {done.stderr.strip()[:300]}")
    return out


# ---- the step ------------------------------------------------------------------------------------------------------------------------

class KurguStep:
    def __init__(self, flow):
        self.flow = flow

    @property
    def db(self):
        return self.flow.db

    def folder(self, video_id):
        return self.flow.version_folder(video_id, "kurgu")

    def state(self, video_id):
        try:
            return json.loads((self.folder(video_id) / STATE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def save(self, video_id, state):
        folder = self.folder(video_id)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / STATE).write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def chapters(self, video_id):
        folder = self.flow.version_folder(video_id, "yayin")
        for path in sorted(folder.glob("surum-*.json"), reverse=True) if folder.is_dir() else []:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if data.get("sebep") == "Onaylandı":
                return ((data.get("icerik") or {}).get("paket") or {}).get("bolumler") or []
        return []

    def rows(self, version):
        from .evidence import PackError, stored_file
        if not version.get("pack_id"):
            return []
        try:
            path, _ = stored_file(self.db, version["pack_id"], "json")
            pack = json.loads(path.read_text(encoding="utf-8"))
        except (PackError, OSError, ValueError):
            return []
        return [row for section in pack.get("sections") or [] for row in section.get("rows") or []]

    def audio(self, video_id):
        """The voice step's uploaded files, its sentence times ({no: (start, end)}, only when every sentence matched) and a signature."""
        vstate, base = self.flow.voice.state(video_id), self.flow.voice.folder(video_id)
        audio, matched = vstate.get("ses") or {}, vstate.get("eslesme") or {}
        files = [base / "ses" / audio["klasor"] / f["ad"] for f in audio.get("dosyalar") or []] if audio.get("klasor") and not audio.get("sorunlar") else []
        times = None
        if files and matched and not matched.get("eslesmeyen"):
            try:
                rows = json.loads((base / "eslesme" / voice.MATCH_FILE).read_text(encoding="utf-8"))["cumleler"]
                times = {int(r["no"]): (float(r["baslangic"]), float(r["bitis"])) for r in rows}
            except (OSError, ValueError, KeyError, TypeError):
                times = None
        signature = {"klasor": audio.get("klasor"), "toplam_s": audio.get("toplam_s"), "eslesme": matched or None}
        return files, times, audio.get("toplam_s"), signature

    def auto(self, video_id):
        """A ready step builds its package as soon as it is shown (it is deterministic and costs nothing)."""
        if workflow.step(self.db, video_id, "kurgu")["status"] == "ready" and not self.state(video_id).get("paket"):
            try:
                self.build(video_id)
            except Conflict:
                pass

    def build(self, video_id, by_user=False):
        row, yayin = workflow.step(self.db, video_id, "kurgu"), workflow.step(self.db, video_id, "yayin")
        if yayin["status"] not in workflow.COMPLETE or row["status"] == "waiting":
            raise Conflict(NOT_READY)
        version, metin = self.flow.voice.approved_text(video_id)
        video = self.flow.video(video_id)
        cfg = settings(self.flow.data_dir)
        try:
            regions = [r["name"] for r in self.db.context(video["destination_id"]).canonical_regions]
        except Exception:                      # a destination without regions: no place names from the profile
            regions = []
        files, times, total, signature = self.audio(video_id)
        if times is not None:
            nos = {int(s["no"]) for p in metin.get("parcalar") or [] for para in p.get("paragraflar") or [] for s in para.get("cumleler") or []
                   if s.get("en") and s.get("no") is not None}
            if not nos <= set(times):
                times = None
        title = str(video.get("title_en") or video.get("display_name") or video_id)
        made = build(metin, self.rows(version), name=f"30A {title.split('|')[0].strip()}"[:80], channel=cfg["kurgu_kanali"] or DEFAULT_CHANNEL,
                     regions=regions, chapters=self.chapters(video_id), title_en=title.split("|")[0].strip(), timings=times, audio_total=total)
        if not made["script.json"]["sentences"]:
            raise Conflict("Onaylı metinde İngilizce cümle yok.")
        root = self.folder(video_id) / "paket"
        root.mkdir(parents=True, exist_ok=True)
        number = f"{len([p for p in root.iterdir() if p.is_dir()]) + 1:03d}"
        target = root / number
        target.mkdir(parents=True)
        if files:
            (target / "audio").mkdir()
            joined = join_audio(files, target / "audio" / "anlatim", cfg)
            made["package.json"]["audio"] = {"file": f"audio/{joined.name}",
                                             "source": {"site": "30a-studio", "license": "kanalın kendi seslendirmesi (7 · Seslendirme'de yüklendi)"}}
            if times is not None:
                timing = {"sentences": [{"id": f"c{no}", "start": start, "end": end} for no, (start, end) in sorted(times.items())]}
                (target / "audio" / "zamanlar.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                made["package.json"]["audio"]["timings"] = "audio/zamanlar.json"
        for name, content in made.items():
            (target / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        script = made["script.json"]["sentences"]
        summary = {"cumle": len(script), "bolum": len(made["script.json"]["sections"]), "kayit": len(made["data.json"]["records"]),
                   "kaynak": len(made["package.json"]["sources"]), "sahne": len(made["scenes.json"]["scenes"]),
                   "yer": len({p for s in script for p in (s.get("mentions") or {}).get("places") or []}),
                   "rakam": sum(len((s.get("mentions") or {}).get("numbers") or []) for s in script),
                   "kaynakli_rakam": sum(1 for s in script for n in (s.get("mentions") or {}).get("numbers") or [] if n.get("ref")),
                   "ses": bool(files), "zamanlar": times is not None, "kanal": made["package.json"]["channel"]}
        state = self.state(video_id)
        state["paket"] = {"klasor": number, "zaman": workflow.now(), "surum_id": version["id"], "ozet": summary, "ses_imzasi": signature}
        self.save(video_id, state)
        voice_text = "ses ve cümle zamanlarıyla" if summary["zamanlar"] else "sesle (zamanları motor hizalar)" if files else "sessiz (ses henüz yok)"
        self.flow.write_version(video_id, "kurgu", "Paket kuruldu", {**summary, "klasor": number,
                                "ozet": f"{summary['cumle']} cümle · {summary['kayit']} veri kaydı · {summary['sahne']} kart önerisi · {voice_text}"})
        status = workflow.step(self.db, video_id, "kurgu")["status"]
        if status != "ready":
            workflow.set_step(self.db, video_id, "kurgu", "ready", log=f"8 · Kurgu paketi: paket {'yeniden ' if by_user else ''}kuruldu ({number}).")
        else:
            workflow.log(self.db, video_id, "kurgu", f"8 · Kurgu paketi: paket {'yeniden ' if by_user else ''}kuruldu ({number}; {voice_text}).")
        return self.flow.step_view(video_id, "kurgu")

    def send(self, video_id):
        state = self.state(video_id)
        package = state.get("paket")
        if not package or workflow.step(self.db, video_id, "kurgu")["status"] == "waiting":
            raise Conflict("Önce kurgu paketi kurulmalı.")
        cfg = settings(self.flow.data_dir)
        motor = motor_dir(cfg)
        pnpm_of(cfg)
        source = self.folder(video_id) / "paket" / package["klasor"]
        inbox = motor / INBOX / f"{video_id}-{package['klasor']}"
        if inbox.exists():
            shutil.rmtree(inbox)
        shutil.copytree(source, inbox)
        steps, ok, project = [], False, state.get("proje")
        code, output = run_motor(cfg, ["paket", "dogrula", str(inbox)], timeout=600)
        steps.append({"komut": "paket dogrula", "kod": code, "cikti": output[-6000:]})
        if code == 0:
            args = ["paket", "ice-al", str(inbox)]
            if project and (motor / "projects" / project).is_dir():
                args += ["--guncelle", f"projects/{project}"]
            code, output = run_motor(cfg, args)
            steps.append({"komut": " ".join(args[:2] + args[3:]), "kod": code, "cikti": output[-6000:]})
            found = PROJECT_LINE.search(output)
            if code == 0:
                ok, project = True, found.group(1) if found else project
        sent = {"zaman": workflow.now(), "paket": package["klasor"], "motor_klasoru": str(inbox), "basarili": ok, "proje": project if ok else None,
                "proje_klasoru": str(motor / "projects" / project) if ok and project else None, "adimlar": steps}
        state["gonderim"] = sent
        if ok:
            state["proje"] = project
        self.save(video_id, state)
        self.flow.write_version(video_id, "kurgu", "Kurguya gönderildi" if ok else "Gönderim hata verdi",
                                {"paket": package["klasor"], "proje": sent["proje"], "ozet": f"proje {project}" if ok else steps[-1]["komut"] + " hata verdi"})
        if ok:
            workflow.set_step(self.db, video_id, "kurgu", "done", log=f"8 · Kurgu paketi: Kurgu Motoru'na gönderildi (proje {project}).")
        else:
            reason = "Paket denetimden geçmedi" if len(steps) == 1 else "Kurgu Motoru paketi içe aktaramadı"
            workflow.set_step(self.db, video_id, "kurgu", "error", error=f"{reason}; motorun çıktısı aşağıda.",
                              log=f"8 · Kurgu paketi: gönderim hata verdi ({steps[-1]['komut']}, kod {steps[-1]['kod']}).")
        return self.flow.step_view(video_id, "kurgu")

    def open_folder(self, video_id):
        package = self.state(video_id).get("paket")
        folder = self.folder(video_id) / "paket" / package["klasor"] if package else None
        if not folder or not folder.is_dir():
            raise Conflict("Paket henüz kurulmadı.")
        if hasattr(os, "startfile"):
            os.startfile(str(folder))
        return {"klasor": str(folder)}

    def view(self, video_id):
        state = self.state(video_id)
        package = state.get("paket")
        out = {"paket": None, "gonderim": state.get("gonderim"), "ses_degisti": False}
        if package:
            folder = self.folder(video_id) / "paket" / package["klasor"]
            out["paket"] = {**package, "yol": str(folder), "dosyalar": sorted(str(p.relative_to(folder)).replace("\\", "/")
                                                                              for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else []}
            try:
                scenes = json.loads((folder / "scenes.json").read_text(encoding="utf-8"))["scenes"]
                script = {s["id"]: s for s in json.loads((folder / "script.json").read_text(encoding="utf-8"))["sentences"]}
            except (OSError, ValueError, KeyError):
                scenes, script = [], {}
            out["paket"]["kartlar"] = [{"cumle": sc["sentence"], "kart": sc["template"], "gerekce": sc.get("rationale"),
                                        "metin": (script.get(sc["sentence"]) or {}).get("text", "")[:140]} for sc in scenes[:30]]
            out["ses_degisti"] = package.get("ses_imzasi") != self.audio(video_id)[3]
        return out
