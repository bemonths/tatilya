"""GÖREV-14: başlatma dosyaları (baslat.bat, kisayol-olustur.ps1) ve program simgesi."""
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from tools import make_icon

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "studio" / "web" / "img"
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows'a özgü")


def png_pixels(data: bytes) -> tuple[int, bytes]:
    """PNG'nin boyutu ve sıkıştırması açılmış piksel satırları (sıkıştırma ayarı farkı sayılmaz)."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    position, idat, size = 8, b"", 0
    while position < len(data):
        length, tag = struct.unpack(">I4s", data[position:position + 8])
        chunk = data[position + 8:position + 8 + length]
        if tag == b"IHDR":
            size = struct.unpack(">I", chunk[:4])[0]
        elif tag == b"IDAT":
            idat += chunk
        position += 12 + length
    return size, zlib.decompress(idat)


def ico_entries(data: bytes) -> dict[int, bytes]:
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1)
    entries = {}
    for index in range(count):
        width, _, _, _, _, _, length, offset = struct.unpack("<BBBBHHII", data[6 + 16 * index:22 + 16 * index])
        entries[width or 256] = data[offset:offset + length]
    return entries


def test_committed_icons_match_generator(tmp_path: Path) -> None:
    built = {path.name: path.read_bytes() for path in make_icon.build(tmp_path)}
    assert set(built) == {"30a.svg", "30a.ico", "30a-192.png"}
    assert (IMG / "30a.svg").read_bytes().replace(b"\r\n", b"\n") == built["30a.svg"]
    assert png_pixels((IMG / "30a-192.png").read_bytes()) == png_pixels(built["30a-192.png"])
    committed, fresh = ico_entries((IMG / "30a.ico").read_bytes()), ico_entries(built["30a.ico"])
    assert sorted(committed) == sorted(fresh) == list(make_icon.ICO_SIZES)
    for size in committed:
        assert png_pixels(committed[size]) == png_pixels(fresh[size])


def test_icon_uses_program_colours_and_name() -> None:
    svg = (IMG / "30a.svg").read_text(encoding="utf-8")
    assert "<title>30A Studio</title>" in svg
    for colour in (make_icon.NAVY, make_icon.ORANGE, make_icon.CREAM):
        assert colour in svg
    assert 'href="/static/img/30a.svg"' in (ROOT / "studio" / "web" / "index.html").read_text(encoding="utf-8")


def test_baslat_bat_is_ascii_crlf_and_launches_without_console() -> None:
    data = (ROOT / "baslat.bat").read_bytes()
    data.decode("ascii")
    assert b"\n" not in data.replace(b"\r\n", b"")
    text = data.decode("ascii")
    assert 'start "" "%VENV_PYW%" -X utf8 -m studio' in text
    assert "-m studio.install_stamp check" in text and "-m studio.install_stamp write" in text
    assert "-r requirements-lock.txt" in text
    assert 'if /i "%~1"=="kur" goto install' in text
    assert "kisayol-olustur.ps1" in text


def test_shortcut_script_is_utf8_bom_crlf_and_uses_unicode_api() -> None:
    data = (ROOT / "kisayol-olustur.ps1").read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")
    assert b"\n" not in data.replace(b"\r\n", b"")
    text = data.decode("utf-8-sig")
    assert "IShellLinkW" in text and "WScript.Shell" in text  # WScript.Shell yalnız açıklamada, neden kullanılmadığı
    assert '"-X utf8 -m studio"' in text and r"studio\web\img\30a.ico" in text and '"30A Studio.lnk"' in text


def test_gitattributes_keeps_windows_scripts_crlf() -> None:
    text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.bat text eol=crlf" in text and "*.ps1 text eol=crlf" in text


@windows_only
@pytest.mark.skipif(not (ROOT / ".venv" / "Scripts" / "pythonw.exe").exists(), reason="sanal ortam kurulu değil")
def test_shortcut_is_created_in_unicode_folder(tmp_path: Path) -> None:
    target = tmp_path / "Masaüstü şğı"
    target.mkdir()
    result = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(ROOT / "kisayol-olustur.ps1"), "-Hedef", str(target)],
                            capture_output=True, timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert result.returncode == 0, result.stdout.decode("utf-8", "replace") + result.stderr.decode("utf-8", "replace")
    link = target / "30A Studio.lnk"
    assert link.exists() and link.stat().st_size > 0
    data = link.read_bytes()
    assert "pythonw.exe".encode("utf-16-le") in data and "-X utf8 -m studio".encode("utf-16-le") in data
