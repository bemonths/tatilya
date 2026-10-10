"""Kurulum damgası: requirements-lock.txt'nin karması `.venv/studio-kurulum.txt` dosyasında saklanır.

Damga tutmuyorsa bağımlılıklar değişmiş demektir; `baslat.bat` ve başlatıcı kurulumu yeniden yapar.
Bu modül bağımlılıklar kurulmadan önce de çalışır (`baslat.bat` çağırır); bu yüzden yalnız standart kütüphaneyi kullanır.
Housing Atlas'taki `atlas/install_stamp.py`'den uyarlandı (orada pyproject.toml'un karması).

Komut satırı:
    python -m studio.install_stamp check   # damga güncelse 0, değilse 1 ile çıkar
    python -m studio.install_stamp write   # damgayı yazar
"""

import hashlib
import sys
from pathlib import Path

STAMP_NAME = "studio-kurulum.txt"
REQUIREMENTS = "requirements-lock.txt"


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


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["check"]:
        return 0 if is_current() else 1
    if args == ["write"]:
        write()
        return 0
    print("Kullanım: python -m studio.install_stamp check|write", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
