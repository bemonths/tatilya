"""Kurulum damgası: requirements-lock.txt'nin karması `.venv/studio-kurulum.txt` dosyasında saklanır.

Damga tutmuyorsa bağımlılıklar değişmiş demektir; `baslat.bat` ve başlatıcı kurulumu yeniden yapar.
Bu modül bağımlılıklar kurulmadan önce de çalışır (`baslat.bat` çağırır); bu yüzden yalnız standart kütüphaneyi kullanır.
Housing Atlas'taki `atlas/install_stamp.py`'den uyarlandı (orada pyproject.toml'un karması).

Komut satırı:
    python -m studio.install_stamp check   # damga güncelse 0, değilse 1 ile çıkar
    python -m studio.install_stamp write   # damgayı ve programın klasörünü yazar
    python -m studio.install_stamp moved   # program klasörü taşınmışsa 0, taşınmamışsa 1 ile çıkar

GÖREV-17: programın klasörü `.venv/studio-konum.txt` dosyasına da yazılır. Klasör taşınırsa sanal ortamın içindeki kayıtlar eski yolu
gösterir; `baslat.bat` bunu `moved` ile anlar, kurulumu yeni klasöre göre yeniler ve masaüstü kısayolunu yeniden oluşturur. Konum
dosyası yoksa (eski kurulum) sanal ortamın kendi kaydına (`pyvenv.cfg` içindeki `command` satırı) bakılır.
"""

import hashlib
import os
import re
import sys
from pathlib import Path

STAMP_NAME = "studio-kurulum.txt"
REQUIREMENTS = "requirements-lock.txt"
LOCATION_NAME = "studio-konum.txt"
VENV_COMMAND = re.compile(r"^command\s*=.*?-m venv\s+(?:--\S+\s+)*(.+?)\s*$", re.M)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def stamp_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / ".venv" / STAMP_NAME


def compute(root: Path | None = None) -> str:
    """requirements-lock.txt'nin SHA-256 karması; satır sonları LF'ye çevrilerek hesaplanır (yalnız satır sonu
    değişince bağımlılıklar yeniden kurulmasın)."""
    data = ((root or repo_root()) / REQUIREMENTS).read_bytes()
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def read(root: Path | None = None) -> str | None:
    try:
        return stamp_path(root).read_text(encoding="utf-8").strip() or None
    except (OSError, UnicodeDecodeError):
        return None


def write(root: Path | None = None) -> None:
    path = stamp_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(compute(root) + "\n", encoding="utf-8")


def is_current(root: Path | None = None) -> bool:
    return read(root) == compute(root)


def location_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / ".venv" / LOCATION_NAME


def recorded_location(root: Path | None = None) -> str | None:
    """Sanal ortamın kurulduğu sırada bulunduğu klasör: konum dosyası, yoksa pyvenv.cfg içindeki `command` satırı."""
    venv = (root or repo_root()) / ".venv"
    try:
        text = location_path(root).read_text(encoding="utf-8").strip()
        if text:
            return text
    except (OSError, UnicodeDecodeError):
        pass
    try:
        match = VENV_COMMAND.search((venv / "pyvenv.cfg").read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    return match.group(1) if match else None


def same_folder(first: str, second: Path) -> bool:
    return os.path.normcase(os.path.normpath(first)) == os.path.normcase(os.path.normpath(str(second)))


def moved(root: Path | None = None) -> bool:
    """Program klasörü, sanal ortam kurulduktan sonra başka bir yere taşınmış mı? Kayıt yoksa taşınmamış sayılır."""
    venv = ((root or repo_root()) / ".venv").resolve()
    recorded = recorded_location(root)
    return recorded is not None and not same_folder(recorded, venv)


def write_location(root: Path | None = None) -> None:
    path = location_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(path.parent.resolve()) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["check"]:
        return 0 if is_current() else 1
    if args == ["write"]:
        write()
        write_location()
        return 0
    if args == ["moved"]:
        return 0 if moved() else 1
    print("Kullanım: python -m studio.install_stamp check|write|moved", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
