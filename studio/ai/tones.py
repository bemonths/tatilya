"""Tones of the narrator (GÖREV-15, Adım 3): Settings → Tonlar, managed by the user without a task.

A tone is a Markdown file in the destination's tone folder (`TEXT["tones"]`, e.g. `studio/destinations/thirty_a_claude/tonlar/`): the first
line is `# Ton: <Ad>`, a blank line, then the tone's text. The repository file is the single source, as in the instruction editor: a tone
the user adds or edits shows as an uncommitted change in git (on purpose; Claude Code commits them at the start of the next task). Saving
checks that the file on disk is still the one that was opened (SHA-256); before every save the previous content is kept in
`<data>/claude/ton_gecmisi/<file stem>/<time>.md` and "Bu sürüme dön" writes an old one back as a new save.

- New tone: a name (not empty, at most 40 characters, not the name of another tone) and a text (not empty, at most 6,000 characters; over
  1,200 a gentle note). The file name comes from the name: Turkish letters simplified (ı→i, ş→s, ğ→g, ü→u, ö→o, ç→c, other accents
  dropped), lower case, every character that is not a letter or digit becomes `_`; a number is added when the file exists.
- Editing changes the name and the text; the file name stays, so earlier versions and records keep pointing at the same tone.
- Deleting moves the file to `<data>/claude/ton_arsivi/<file stem>-<time>.md`; nothing is deleted. "Geri al" brings it back (a number is
  added when the file name is taken). The last tone cannot be deleted.
- The default tone is a setting (`ayarlar.json` → `varsayilan_ton` → destination → file stem); it starts as the profile's default. When the
  default tone is deleted the first tone of the list becomes the default and the answer says so.
"""
import hashlib
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from ..database import Conflict
from . import settings as claude_settings

HEADER = re.compile(r"^#\s*Ton\s*:\s*(.+?)\s*$")
HISTORY = ("claude", "ton_gecmisi")
ARCHIVE = ("claude", "ton_arsivi")
DEFAULT_SECTION = "varsayilan_ton"
NAME_MAX, TEXT_MAX, TEXT_LONG = 40, 6000, 1200
LONG_NOTE = "Ton metni uzun. Kısa ve niyet anlatan metinler genellikle daha iyi sonuç verir."
VERSION_NAME = re.compile(r"^\d{8}-\d{6}-\d{6}$")
ARCHIVE_NAME = re.compile(r"^(?P<stem>.+)-(?P<stamp>\d{8}-\d{6}-\d{6})$")
TURKISH = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c",
                         "Ç": "c"})


class ToneError(ValueError):
    """User-facing reason (Turkish) a tone cannot be saved."""


def folder_of(profile):
    found = (getattr(profile, "TEXT", None) or {}).get("tones")
    if found is None:
        raise KeyError("tonlar")
    return Path(found)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def modified(path):
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def slug(name):
    """The file stem of a tone name: "Hikâye anlatıcısı" → "hikaye_anlaticisi", "Araştırmacı dost" → "arastirmaci_dost"."""
    text = unicodedata.normalize("NFKD", (name or "").translate(TURKISH))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "ton"


def parse(data):
    """(name, text) of a tone file's bytes; a file without the header line is named by nothing (None) and its whole content is the text."""
    content = data.decode("utf-8-sig").replace("\r\n", "\n")
    lines = content.split("\n")
    match = HEADER.match(lines[0]) if lines else None
    if not match:
        return None, content.strip()
    return match.group(1), "\n".join(lines[1:]).strip()


def compose(name, text, ending="\n"):
    body = f"# Ton: {name}\n\n{text.strip()}\n"
    return body.replace("\n", ending).encode("utf-8")


def first_line(text):
    return next((line.strip() for line in text.split("\n") if line.strip()), "")


def first_sentence(text):
    line = first_line(text)
    found = re.match(r"(.+?[.!?])(\s|$)", line)
    return found.group(1) if found else line


def check(name, text):
    name = (name or "").strip()
    if not name:
        raise ToneError("Tonun adı boş olamaz.")
    if len(name) > NAME_MAX:
        raise ToneError(f"Tonun adı en çok {NAME_MAX} karakter olabilir.")
    if "\n" in name or "\r" in name:
        raise ToneError("Tonun adı tek satır olmalı.")
    if not isinstance(text, str) or not text.strip():
        raise ToneError("Tonun metni boş olamaz.")
    if len(text.strip()) > TEXT_MAX:
        raise ToneError(f"Tonun metni en çok {TEXT_MAX:,} karakter olabilir ({len(text.strip()):,} karakter).".replace(",", "."))
    return name, text.strip(), (LONG_NOTE if len(text.strip()) > TEXT_LONG else None)


# ---- the list ------------------------------------------------------------------------------------------------------------------------

def tone_files(profile):
    folder = folder_of(profile)
    return sorted(p for p in folder.glob("*.md") if p.is_file()) if folder.is_dir() else []


def item(path):
    data = path.read_bytes()
    name, text = parse(data)
    return {"dosya": path.stem, "ad": name or path.stem, "metin": text, "ilk_satir": first_line(text), "ilk_cumle": first_sentence(text),
            "sha256": sha256(data), "degisti": modified(path), "boyut": len(data)}


def default_file(data_dir, destination_id, profile):
    """The default tone's file stem: the setting when that tone exists, else the profile's default, else the first tone."""
    stems = [p.stem for p in tone_files(profile)]
    stored = (claude_settings.stored_settings(data_dir).get(DEFAULT_SECTION) or {}).get(destination_id)
    if stored in stems:
        return stored
    preferred = (getattr(profile, "TEXT", None) or {}).get("default_tone")
    if preferred in stems:
        return preferred
    return stems[0] if stems else None


def set_default(data_dir, destination_id, profile, stem):
    if stem not in [p.stem for p in tone_files(profile)]:
        raise KeyError(stem)
    stored = claude_settings.stored_settings(data_dir)
    section = stored.get(DEFAULT_SECTION) if isinstance(stored.get(DEFAULT_SECTION), dict) else {}
    section[destination_id] = stem
    stored[DEFAULT_SECTION] = section
    claude_settings.write_settings(data_dir, stored)
    return stem


def listing(data_dir, destination_id, profile, usage=None):
    """Settings → Tonlar: every tone (name, first line, last change, default or not, how many text versions used it) and the archive."""
    usage = usage or {}
    default = default_file(data_dir, destination_id, profile)
    tones = [{**item(p), "varsayilan": p.stem == default, "kullanim": usage.get(p.stem, 0)} for p in tone_files(profile)]
    return {"tonlar": tones, "varsayilan": default, "arsiv": archive(data_dir, usage), "uzun_metin": TEXT_LONG, "en_cok": TEXT_MAX,
            "ad_en_cok": NAME_MAX, "uzun_not": LONG_NOTE}


def find(profile, stem):
    path = folder_of(profile) / f"{stem}.md"
    if not re.fullmatch(r"[a-z0-9_]+", stem or "") or not path.is_file():
        raise KeyError(stem)
    return path


def read(data_dir, profile, stem):
    path = find(profile, stem)
    return {**item(path), "surumler": versions(data_dir, stem)}


def names_in_use(profile, except_stem=None):
    return {item(p)["ad"].casefold() for p in tone_files(profile) if p.stem != except_stem}


# ---- saving --------------------------------------------------------------------------------------------------------------------------

def free_path(folder, stem):
    path, number = folder / f"{stem}.md", 2
    while path.exists():
        path, number = folder / f"{stem}_{number}.md", number + 1
    return path


def atomic_write(path, data):
    temporary = path.with_name(f".{path.name}.yaziliyor")
    temporary.write_bytes(data)
    temporary.replace(path)


def create(data_dir, profile, name, text):
    name, text, note = check(name, text)
    if name.casefold() in names_in_use(profile):
        raise ToneError("Bu adla bir ton zaten var; başka bir ad yazın.")
    folder = folder_of(profile)
    folder.mkdir(parents=True, exist_ok=True)
    path = free_path(folder, slug(name))
    atomic_write(path, compose(name, text))
    return {**read(data_dir, profile, path.stem), "not": note}


def history_dir(data_dir, stem):
    return Path(data_dir).joinpath(*HISTORY, stem)


def keep_version(data_dir, stem, data):
    folder = history_dir(data_dir, stem)
    folder.mkdir(parents=True, exist_ok=True)
    name = stamp()
    (folder / f"{name}.md").write_bytes(data)
    return name


def update(data_dir, profile, stem, name, text, base_sha256):
    """New name and text of a tone when the file is still the one that was opened; the file name does not change."""
    path = find(profile, stem)
    name, text, note = check(name, text)
    current = path.read_bytes()
    if sha256(current) != base_sha256:
        raise Conflict("Ton dosyası siz açtıktan sonra diskte değişti (başka biri düzenlemiş olabilir). Kaydedilmedi; önce “Yeniden yükle” "
                       "ile güncel hâlini açın, değişikliğinizi onun üzerine yapıp öyle kaydedin.")
    if name.casefold() in names_in_use(profile, except_stem=stem):
        raise ToneError("Bu adla bir ton zaten var; başka bir ad yazın.")
    ending = "\r\n" if b"\r\n" in current else "\n"
    new = compose(name, text, ending)
    if new == current:
        return {**read(data_dir, profile, stem), "degismedi": True, "not": note}
    archived = keep_version(data_dir, stem, current)
    atomic_write(path, new)
    return {**read(data_dir, profile, stem), "degismedi": False, "saklanan_surum": archived, "not": note}


def versions(data_dir, stem):
    folder = history_dir(data_dir, stem)
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.glob("*.md"), reverse=True):
        if not VERSION_NAME.match(path.stem):
            continue
        data = path.read_bytes()
        name, text = parse(data)
        saved = datetime.strptime(path.stem, "%Y%m%d-%H%M%S-%f").replace(tzinfo=timezone.utc)
        found.append({"id": path.stem, "saklandi": saved.isoformat(timespec="seconds"), "ad": name, "ilk_satir": first_line(text),
                      "sha256": sha256(data), "boyut": len(data)})
    return found


def version_text(data_dir, stem, version):
    if not VERSION_NAME.match(version or ""):
        raise KeyError(version)
    path = history_dir(data_dir, stem) / f"{version}.md"
    if not path.is_file():
        raise KeyError(version)
    name, text = parse(path.read_bytes())
    return {"id": version, "ad": name, "metin": text}


def restore_version(data_dir, profile, stem, version, base_sha256):
    old = version_text(data_dir, stem, version)
    current = item(find(profile, stem))
    return update(data_dir, profile, stem, old["ad"] or current["ad"], old["metin"], base_sha256)


# ---- archive ------------------------------------------------------------------------------------------------------------------------

def archive_dir(data_dir):
    return Path(data_dir).joinpath(*ARCHIVE)


def archive(data_dir, usage=None):
    folder = archive_dir(data_dir)
    if not folder.is_dir():
        return []
    usage = usage or {}
    found = []
    for path in sorted(folder.glob("*.md"), reverse=True):
        match = ARCHIVE_NAME.match(path.stem)
        if not match:
            continue
        data = path.read_bytes()
        name, text = parse(data)
        moved = datetime.strptime(match["stamp"], "%Y%m%d-%H%M%S-%f").replace(tzinfo=timezone.utc)
        found.append({"id": path.stem, "dosya": match["stem"], "ad": name or match["stem"], "ilk_satir": first_line(text),
                      "arsivlendi": moved.isoformat(timespec="seconds"), "kullanim": usage.get(match["stem"], 0)})
    return found


def delete(data_dir, destination_id, profile, stem):
    """Moves the tone to the archive (nothing is deleted). The last tone stays. A deleted default passes to the first tone of the list."""
    path = find(profile, stem)
    remaining = [p.stem for p in tone_files(profile) if p.stem != stem]
    if not remaining:
        raise ToneError("Son ton silinemez; en az bir ton kalmalı.")
    was_default = default_file(data_dir, destination_id, profile) == stem
    folder = archive_dir(data_dir)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{stem}-{stamp()}.md"
    shutil.move(str(path), str(target))
    note = None
    if was_default:
        set_default(data_dir, destination_id, profile, remaining[0])
        note = f"Silinen ton varsayılandı; artık varsayılan ton “{item(folder_of(profile) / f'{remaining[0]}.md')['ad']}”."
    return {"arsiv_kimligi": target.stem, "not": note, "varsayilan": default_file(data_dir, destination_id, profile)}


def restore_archived(data_dir, profile, archive_id):
    """"Geri al": the archived tone goes back to the tone folder (with a number when its file name is taken)."""
    match = ARCHIVE_NAME.match(archive_id or "")
    path = archive_dir(data_dir) / f"{archive_id}.md"
    if not match or not path.is_file():
        raise KeyError(archive_id)
    folder = folder_of(profile)
    folder.mkdir(parents=True, exist_ok=True)
    target = free_path(folder, match["stem"])
    shutil.move(str(path), str(target))
    return read(data_dir, profile, target.stem)


# ---- a tone for a run ---------------------------------------------------------------------------------------------------------------

def snapshot(profile, stem, target):
    """The tone as it is now, copied into a text run's folder: every session of that tone uses the same text. {dosya, ad, path, sha256}."""
    path = find(profile, stem)
    data = path.read_bytes()
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    Path(target).write_bytes(data)
    name, _ = parse(data)
    return {"dosya": stem, "ad": name or stem, "path": str(target), "sha256": sha256(data)}
