"""Instruction editor (GÖREV-14, Adım 4c; Housing Atlas TASARIM 10.4): Settings → Talimatlar.

The destination's instruction files are listed (the common file, every step's file, and the channel research as an information file). The
single source is the repository file itself: the manager edits the same file outside the program, so there are never two copies. Saving
checks that the file on disk is still the one that was opened (SHA-256 of its bytes); if it changed in between, nothing is written and the
user reloads first. Before every save the previous content is kept in `<data>/claude/talimat_gecmisi/<file stem>/<time>.md`; versions are
listed and "bu sürüme dön" writes an old one back (as a new save, so the current one is kept too). Line endings of the file are kept.
"""
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from ..database import Conflict
from . import steps

HISTORY = ("claude", "talimat_gecmisi")
MAX_BYTES = 400_000
VERSION_NAME = re.compile(r"^\d{8}-\d{6}-\d{6}$")
COMMON = "ortak.md"


class InstructionError(ValueError):
    pass


def files(profile):
    """[{key, name, title, kind ("talimat"|"bilgi"), path}] in Settings order: common file, the steps' files, the channel research."""
    folder = getattr(profile, "CLAUDE_INSTRUCTIONS", None)
    if folder is None:
        return []
    found, seen = [], set()

    def add(path, title, kind):
        path = Path(path)
        if path.name in seen:
            return
        seen.add(path.name)
        found.append({"key": path.stem, "name": path.name, "title": title, "kind": kind, "path": path})

    add(Path(folder) / COMMON, "Ortak kurallar (bütün adımlar)", "talimat")
    for step in steps.STEPS.values():
        for name in step.instructions:
            if name != COMMON:
                add(Path(folder) / name, step.title, "talimat")
    research = (getattr(profile, "CHANNEL", None) or {}).get("research")
    if research:
        add(research, "Kanal araştırması (bilgi dosyası; başlık çalışmalarına girdi olarak verilir)", "bilgi")
    return found


def find(profile, key):
    item = next((f for f in files(profile) if f["key"] == key), None)
    if item is None:
        raise KeyError(key)
    return item


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def modified(path):
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def history_dir(data_dir, item):
    return Path(data_dir).joinpath(*HISTORY, item["path"].stem)


def versions(data_dir, item):
    folder = history_dir(data_dir, item)
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.glob("*.md"), reverse=True):
        if not VERSION_NAME.match(path.stem):
            continue
        saved = datetime.strptime(path.stem, "%Y%m%d-%H%M%S-%f").replace(tzinfo=timezone.utc)
        data = path.read_bytes()
        found.append({"id": path.stem, "saved_at": saved.isoformat(timespec="seconds"), "sha256": sha256(data), "size": len(data)})
    return found


def summary(item):
    data = item["path"].read_bytes()
    return {k: item[k] for k in ("key", "name", "title", "kind")} | {"sha256": sha256(data), "modified_at": modified(item["path"]),
                                                                    "size": len(data)}


def read(data_dir, profile, key):
    item = find(profile, key)
    data = item["path"].read_bytes()
    return {**summary(item), "text": data.decode("utf-8-sig").replace("\r\n", "\n"), "versions": versions(data_dir, item)}


def write(data_dir, profile, key, text, base_sha256):
    """Writes the new text when the file is still the one opened; the previous content goes to the history first."""
    item = find(profile, key)
    if not isinstance(text, str) or not text.strip():
        raise InstructionError("Talimat metni boş olamaz.")
    current = item["path"].read_bytes()
    if sha256(current) != base_sha256:
        raise Conflict("Dosya siz açtıktan sonra diskte değişti (başka biri ya da yönetici düzenlemiş olabilir). Kaydedilmedi; önce "
                       "“Yeniden yükle” ile güncel hâlini açın, değişikliğinizi onun üzerine yapıp öyle kaydedin.")
    ending = "\r\n" if b"\r\n" in current else "\n"
    bom = b"\xef\xbb\xbf" if current.startswith(b"\xef\xbb\xbf") else b""
    new = bom + text.replace("\r\n", "\n").replace("\n", ending).encode("utf-8")
    if len(new) > MAX_BYTES:
        raise InstructionError(f"Talimat metni en çok {MAX_BYTES // 1000} KB olabilir.")
    if new == current:
        return {**read(data_dir, profile, key), "unchanged": True}
    folder = history_dir(data_dir, item)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    (folder / f"{stamp}.md").write_bytes(current)
    temporary = item["path"].with_name(f".{item['path'].name}.yaziliyor")
    temporary.write_bytes(new)
    temporary.replace(item["path"])
    return {**read(data_dir, profile, key), "unchanged": False, "archived": stamp}


def version_text(data_dir, profile, key, version):
    item = find(profile, key)
    if not VERSION_NAME.match(version or ""):
        raise KeyError(version)
    path = history_dir(data_dir, item) / f"{version}.md"
    if not path.is_file():
        raise KeyError(version)
    return path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")


def restore(data_dir, profile, key, version, base_sha256):
    return write(data_dir, profile, key, version_text(data_dir, profile, key, version), base_sha256)


def used_versions(record_versions, profile):
    """The instruction files a run used, with their hash and date, and whether the file still is that version (for the run screen)."""
    current = {}
    for item in files(profile):
        try:
            current[item["name"]] = sha256(item["path"].read_bytes())
        except OSError:
            pass
    found = []
    for entry in (record_versions or {}).get("files") or []:
        name = Path(entry.get("path") or "").name
        if not name.endswith(".md"):
            continue
        found.append({"name": name, "sha256": entry.get("sha256"), "short": (entry.get("sha256") or "")[:8],
                      "modified_at": entry.get("modified_at"), "current": current.get(name) == entry.get("sha256")})
    return found
