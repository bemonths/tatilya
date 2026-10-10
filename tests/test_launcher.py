"""GÖREV-14: masaüstü başlatıcısı (tek kopya, port, kilit, pencere, hata kutusu, kapanma bekçisi).

Housing Atlas'taki `tests/test_launcher.py`'den uyarlandı; Windows'a özgü kısımlar taklitle sınanır.
"""
import json
import logging
import os
import random
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from studio import install_stamp, launcher, logs
from studio.watchdog import WAITING_MESSAGE

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows'a özgü")
REAL_SPAWN_INSTALLER = launcher.spawn_installer


def free_port() -> int:
    """Windows'un geçici port aralığının (49152 ve üstü) dışından boş bir port."""
    for _ in range(200):
        port = random.randint(20000, 40000)
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("Boş port bulunamadı.")


@pytest.fixture
def root_handlers():
    root = logging.getLogger()
    before = list(root.handlers)
    yield
    for handler in [h for h in root.handlers if h not in before]:
        root.removeHandler(handler)
        handler.close()


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "veri"


def health_server(payload: dict) -> ThreadingHTTPServer:
    body = json.dumps(payload).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200 if self.path == "/api/health" else 404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ---------- port ----------

def test_find_free_port_skips_busy_port() -> None:
    port = free_port()
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", port))
        busy.listen()
        chosen = launcher.find_free_port(port, port + 10)
    assert port < chosen <= port + 10


def test_find_free_port_all_busy() -> None:
    port = free_port()
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", port))
        busy.listen()
        with pytest.raises(launcher.LauncherError, match="boş port bulunamadı"):
            launcher.find_free_port(port, port)


def test_default_port_range_does_not_overlap_housing_atlas() -> None:
    assert launcher.PORT_RANGE == (8830, 8849)
    assert not set(range(8830, 8850)) & set(range(8790, 8810))
    assert launcher.app_url(8830) == "http://127.0.0.1:8830/"


# ---------- tek kopya ----------

def test_lock_write_and_remove_only_own_pid(tmp_path: Path) -> None:
    lock = tmp_path / "calisiyor.json"
    launcher.write_lock(lock, 8831, pid=4242)
    data = json.loads(lock.read_text(encoding="utf-8"))
    assert data["pid"] == 4242 and data["port"] == 8831 and "started_at" in data
    assert not launcher.remove_lock(lock, pid=1111)
    assert lock.exists()
    assert launcher.remove_lock(lock, pid=4242)
    assert not lock.exists()
    assert not launcher.remove_lock(lock, pid=4242)


def test_lock_defaults_to_current_pid(tmp_path: Path) -> None:
    lock = tmp_path / "calisiyor.json"
    launcher.write_lock(lock, 8830)
    assert launcher.read_lock(lock)["pid"] == os.getpid()
    assert launcher.remove_lock(lock)


def test_live_instance_is_detected(tmp_path: Path) -> None:
    server = health_server({"app": "thirtya-studio", "version": "0.16.0", "pid": 1})
    try:
        port = server.server_address[1]
        lock = tmp_path / "calisiyor.json"
        launcher.write_lock(lock, port, pid=1)
        assert launcher.instance_health(port) is not None
        assert launcher.running_instance_port(lock) == port
    finally:
        server.shutdown()
        server.server_close()


def test_other_app_on_port_is_stale(tmp_path: Path) -> None:
    """Housing Atlas aynı portta olsa bile 30A Studio sayılmaz."""
    server = health_server({"app": "housing-atlas", "pid": 1})
    try:
        lock = tmp_path / "calisiyor.json"
        launcher.write_lock(lock, server.server_address[1], pid=1)
        assert launcher.running_instance_port(lock) is None
    finally:
        server.shutdown()
        server.server_close()


def test_stale_lock_without_server(tmp_path: Path) -> None:
    lock = tmp_path / "calisiyor.json"
    launcher.write_lock(lock, free_port(), pid=1)
    assert launcher.running_instance_port(lock) is None


def test_instance_with_other_data_dir_on_stale_port_is_not_used(tmp_path: Path) -> None:
    """Bayat kilidin portunda başka bir veri klasörüyle çalışan kopya (deneme sunucusu) bizim kopyamız sayılmaz."""
    server = health_server({"app": "thirtya-studio", "version": "0.16.0", "pid": 5555})
    try:
        lock = tmp_path / "calisiyor.json"
        launcher.write_lock(lock, server.server_address[1], pid=4444)
        assert launcher.instance_health(server.server_address[1]) is not None
        assert launcher.running_instance_port(lock) is None
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize("content", [None, "{bozuk", '{"port": "8830", "pid": 1}', '{"port": true, "pid": 1}', "[8830]",
                                     '{"port": 8830}', '{"port": 8830, "pid": "1"}'])
def test_missing_or_bad_lock(tmp_path: Path, content: str | None) -> None:
    lock = tmp_path / "calisiyor.json"
    if content is not None:
        lock.write_text(content, encoding="utf-8")
    assert launcher.running_instance_port(lock, health=lambda port: {"app": "thirtya-studio", "pid": 1}) is None


def test_startup_lock(tmp_path: Path) -> None:
    path = tmp_path / "baslatiliyor.kilit"
    first, second = launcher.StartupLock(path), launcher.StartupLock(path)
    assert first.acquire(timeout=0) and first.held
    began = time.monotonic()
    assert not second.acquire(timeout=0.3, poll=0.05)
    assert time.monotonic() - began >= 0.3
    releaser = threading.Thread(target=first.release)  # sunucu hazır olunca başka iş parçacığı bırakır
    releaser.start()
    releaser.join()
    assert not first.held
    first.release()  # ikinci kez bırakmak zararsız
    assert second.acquire(timeout=1)
    second.release()


# ---------- pencere ----------

def test_find_browser_prefers_registry_edge(tmp_path: Path) -> None:
    edge = tmp_path / "msedge.exe"
    found = launcher.find_browser(app_path=lambda exe: edge if exe == "msedge.exe" else None,
                                  known_paths=lambda exe: [])
    assert found == edge


def test_find_browser_uses_known_locations_edge_before_chrome(tmp_path: Path) -> None:
    edge = tmp_path / "Edge" / "msedge.exe"
    chrome = tmp_path / "Chrome" / "chrome.exe"
    chrome.parent.mkdir()
    chrome.write_bytes(b"")
    paths = {"msedge.exe": [edge], "chrome.exe": [tmp_path / "yok.exe", chrome]}
    assert launcher.find_browser(app_path=lambda exe: None, known_paths=paths.get) == chrome
    edge.parent.mkdir()
    edge.write_bytes(b"")
    assert launcher.find_browser(app_path=lambda exe: None, known_paths=paths.get) == edge


def test_find_browser_none() -> None:
    assert launcher.find_browser(app_path=lambda exe: None, known_paths=lambda exe: []) is None


def test_registry_lookup_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setitem(sys.modules, "winreg", None)  # içe aktarma denenirse ImportError verir
    assert launcher.registry_app_path("msedge.exe") is None


def test_window_command_is_app_mode() -> None:
    assert launcher.window_command(Path("C:/Edge/msedge.exe"), "http://127.0.0.1:8830/") == [
        str(Path("C:/Edge/msedge.exe")), "--app=http://127.0.0.1:8830/", "--window-size=1440,900"]


def test_open_window_uses_browser_and_falls_back() -> None:
    calls: list[tuple[list[str], dict]] = []
    fallback: list[str] = []
    launcher.open_window("http://127.0.0.1:8830/", find=lambda: Path("C:/Edge/msedge.exe"),
                         popen=lambda command, **kw: calls.append((command, kw)), fallback=fallback.append)
    assert calls[0][0][1:] == ["--app=http://127.0.0.1:8830/", "--window-size=1440,900"]
    assert calls[0][1]["stdout"] is subprocess.DEVNULL
    assert fallback == []
    launcher.open_window("http://127.0.0.1:8830/", find=lambda: None, popen=None, fallback=fallback.append)
    assert fallback == ["http://127.0.0.1:8830/"]

    def broken_popen(command, **kwargs):
        raise OSError("başlatılamadı")

    launcher.open_window("http://127.0.0.1:8831/", find=lambda: Path("C:/x.exe"), popen=broken_popen,
                         fallback=fallback.append)
    assert fallback[-1] == "http://127.0.0.1:8831/"


def test_show_app_brings_open_window_forward() -> None:
    activated: list[int] = []
    opened: list[str] = []
    launcher.show_app(8832, find=lambda: [111, 222], activate=lambda hwnd: activated.append(hwnd) or True,
                      opener=opened.append)
    assert activated == [111] and opened == []


def test_show_app_opens_window_when_none_is_open() -> None:
    opened: list[str] = []
    launcher.show_app(8832, find=lambda: [], activate=lambda hwnd: pytest.fail("pencere yok"), opener=opened.append)
    assert opened == ["http://127.0.0.1:8832/"]


@pytest.mark.parametrize(("class_name", "title", "expected"), [
    ("Chrome_WidgetWin_1", "30A Studio", True),
    ("Chrome_WidgetWin_1", "30A Studio · Videolar", True),
    ("Chrome_WidgetWin_1", "30A Studio · Videolar - Google Chrome", False),
    ("Chrome_WidgetWin_1", "30A Studio · Videolar - Kişisel - Microsoft\u200b Edge", False),
    ("Chrome_WidgetWin_1", "Housing Atlas Stüdyo", False),
    ("Chrome_WidgetWin_1", "30A Studio rehberi - YouTube", False),
    ("Notepad", "30A Studio", False),
])
def test_is_app_window(class_name: str, title: str, expected: bool) -> None:
    assert launcher.is_app_window(class_name, title) is expected


@windows_only
def test_find_app_windows_returns_handles() -> None:
    assert all(isinstance(hwnd, int) for hwnd in launcher.find_app_windows())


def forbid_win32_api(monkeypatch: pytest.MonkeyPatch) -> None:
    import ctypes

    def no_dll(*args, **kwargs):
        raise AssertionError("Windows dışında Windows DLL'i yüklenmemeli.")

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(ctypes, "WinDLL", no_dll, raising=False)


def test_window_helpers_off_windows(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    forbid_win32_api(monkeypatch)
    assert launcher.find_app_windows() == []
    assert launcher.activate_window(1234) is False
    caplog.set_level(logging.WARNING, logger="studio.launcher")
    launcher.show_error("Sunucu 8835 portunda başlatılamadı.")
    assert "Sunucu 8835 portunda başlatılamadı." in caplog.text


# ---------- kurulum damgası ----------

def test_install_stamp_follows_requirements(tmp_path: Path) -> None:
    (tmp_path / "requirements-lock.txt").write_bytes(b"fastapi==1\r\nuvicorn==2\r\n")
    assert not install_stamp.is_current(tmp_path)
    install_stamp.write(tmp_path)
    assert install_stamp.is_current(tmp_path)
    (tmp_path / "requirements-lock.txt").write_bytes(b"fastapi==1\nuvicorn==2\n")  # yalnız satır sonu değişti
    assert install_stamp.is_current(tmp_path)
    (tmp_path / "requirements-lock.txt").write_bytes(b"fastapi==1\nuvicorn==3\n")
    assert not install_stamp.is_current(tmp_path)


def test_needs_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "running_in_repo_venv", lambda: True)
    monkeypatch.setattr(install_stamp, "is_current", lambda: False)
    assert launcher.needs_install()
    monkeypatch.setattr(install_stamp, "is_current", lambda: True)
    assert not launcher.needs_install()
    monkeypatch.setattr(launcher, "running_in_repo_venv", lambda: False)
    monkeypatch.setattr(install_stamp, "is_current", lambda: False)
    assert not launcher.needs_install()


@windows_only
def test_spawn_installer() -> None:
    calls: list[tuple[list[str], dict]] = []
    launcher.spawn_installer(popen=lambda command, **kw: calls.append((command, kw)))
    assert calls == [([os.environ.get("COMSPEC") or "cmd.exe", "/c", ".\\baslat.bat", "kur"],
                      {"cwd": install_stamp.repo_root(), "creationflags": getattr(subprocess, "CREATE_NEW_CONSOLE", 0)})]


def test_spawn_installer_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    calls: list[list[str]] = []
    with pytest.raises(launcher.LauncherError) as info:
        launcher.spawn_installer(popen=lambda command, **kw: calls.append(command))
    assert calls == []
    assert str(info.value).startswith("Kurulum güncel değil") and "studio.install_stamp write" in str(info.value)


# ---------- main ----------

@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch, root_handlers) -> dict:
    """main()'in dış etkilerini kaydeder: kurulum, pencere, sunucu, hata kutusu."""
    record: dict = {"installer": 0, "windows": [], "serve": [], "errors": []}
    monkeypatch.setattr(launcher, "needs_install", lambda: False)
    monkeypatch.setattr(launcher, "spawn_installer", lambda: record.__setitem__("installer", record["installer"] + 1))
    monkeypatch.setattr(launcher, "show_app", lambda port: record["windows"].append(launcher.app_url(port)))
    monkeypatch.setattr(launcher, "show_error", record["errors"].append)

    def serve(data_dir, port, **kw):
        record["serve"].append((data_dir, port, {k: kw[k] for k in ("window", "watchdog")}))
        record["startup_lock_held"] = kw["startup_lock"].held
        return 0

    monkeypatch.setattr(launcher, "serve", serve)
    return record


def without_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """pythonw gibi: çıktı akışı yok. Test gövdesinde çağrılır (pytest akışları test başlarken yeniden kurar)."""
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)


def test_main_starts_installer_when_stamp_is_stale(fake_run: dict, monkeypatch: pytest.MonkeyPatch,
                                                   data_dir: Path) -> None:
    monkeypatch.setattr(launcher, "needs_install", lambda: True)
    assert launcher.main(["--data-dir", str(data_dir)]) == 0
    assert fake_run["installer"] == 1
    assert fake_run["serve"] == []


@pytest.mark.parametrize("flag", ["--no-window", "--no-browser"])
def test_main_command_line_without_window(fake_run: dict, monkeypatch: pytest.MonkeyPatch, data_dir: Path,
                                          flag: str) -> None:
    """Deneme komutu aynen çalışır: pencere yok, kurulum denetimi yok, kapanma bekçisi yok."""
    monkeypatch.setattr(launcher, "needs_install", lambda: True)
    assert launcher.main(["--data-dir", str(data_dir), flag, "--port", "8875"]) == 0
    assert fake_run["installer"] == 0
    assert fake_run["serve"] == [(data_dir.resolve(), 8875, {"window": False, "watchdog": False})]


def test_main_picks_free_port_and_watches_window(fake_run: dict, monkeypatch: pytest.MonkeyPatch,
                                                 data_dir: Path) -> None:
    monkeypatch.setattr(launcher, "find_free_port", lambda: 8833)
    assert launcher.main(["--data-dir", str(data_dir)]) == 0
    assert launcher.main(["--data-dir", str(data_dir), "--no-watchdog"]) == 0
    assert fake_run["serve"] == [(data_dir.resolve(), 8833, {"window": True, "watchdog": True}),
                                 (data_dir.resolve(), 8833, {"window": True, "watchdog": False})]


def test_main_existing_instance_brings_window_forward(fake_run: dict, monkeypatch: pytest.MonkeyPatch,
                                                      data_dir: Path) -> None:
    """Tek kopya: program zaten açıksa yeni sunucu açılmaz, kurulum yapılmaz, pencere öne gelir."""
    monkeypatch.setattr(launcher, "needs_install", lambda: True)
    monkeypatch.setattr(launcher, "running_instance_port", lambda lock: 8834)
    assert launcher.main(["--data-dir", str(data_dir)]) == 0
    assert fake_run["windows"] == ["http://127.0.0.1:8834/"]
    assert fake_run["serve"] == [] and fake_run["installer"] == 0
    assert launcher.main(["--data-dir", str(data_dir), "--no-window"]) == 0
    assert fake_run["windows"] == ["http://127.0.0.1:8834/"]


def test_main_uses_lock_in_data_dir(fake_run: dict, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> None:
    seen: list[Path] = []
    monkeypatch.setattr(launcher, "running_instance_port", lambda lock: seen.append(lock))
    launcher.main(["--data-dir", str(data_dir), "--no-window"])
    assert seen == [data_dir.resolve() / "calisiyor.json"]


def test_main_holds_startup_lock_until_server_is_ready(fake_run: dict, data_dir: Path) -> None:
    assert launcher.main(["--data-dir", str(data_dir), "--no-window", "--port", "8875"]) == 0
    assert fake_run["startup_lock_held"] is True
    after = launcher.StartupLock(data_dir / launcher.STARTUP_LOCK_FILE)
    assert after.acquire(timeout=0)  # main bitince kilit bırakılmış
    after.release()


def test_second_launcher_waits_for_first_to_be_ready(fake_run: dict, monkeypatch: pytest.MonkeyPatch,
                                                     data_dir: Path) -> None:
    """İki hızlı tıklama: ikinci başlatıcı, birincisi kilidi yazana kadar bekler ve yeni sunucu açmaz."""
    data_dir.mkdir(parents=True)
    first = launcher.StartupLock(data_dir / launcher.STARTUP_LOCK_FILE)
    assert first.acquire(timeout=0)
    ready = threading.Event()
    monkeypatch.setattr(launcher, "running_instance_port", lambda lock: 8834 if ready.is_set() else None)
    result: list[int] = []
    second = threading.Thread(target=lambda: result.append(launcher.main(["--data-dir", str(data_dir)])), daemon=True)
    second.start()
    time.sleep(0.4)
    assert second.is_alive() and fake_run["serve"] == []
    ready.set()  # birinci sunucu hazır: kilit yazıldı, başlatma kilidi bırakılıyor
    threading.Thread(target=first.release).start()
    second.join(10)
    assert result == [0]
    assert fake_run["serve"] == []
    assert fake_run["windows"] == ["http://127.0.0.1:8834/"]


def test_main_shows_turkish_error_box_without_console(fake_run: dict, monkeypatch: pytest.MonkeyPatch,
                                                      data_dir: Path) -> None:
    without_console(monkeypatch)

    def busy(data_dir, port, **kw):
        raise launcher.LauncherError("Sunucu 8835 portunda başlatılamadı.")

    monkeypatch.setattr(launcher, "serve", busy)
    assert launcher.main(["--data-dir", str(data_dir), "--port", "8835"]) == 1
    assert fake_run["errors"] == ["Sunucu 8835 portunda başlatılamadı."]


def test_main_unexpected_error_points_to_log(fake_run: dict, monkeypatch: pytest.MonkeyPatch,
                                             data_dir: Path) -> None:
    without_console(monkeypatch)

    def broken(data_dir, port, **kw):
        raise RuntimeError("create_app bozuldu")

    monkeypatch.setattr(launcher, "serve", broken)
    assert launcher.main(["--data-dir", str(data_dir), "--port", "8835"]) == 1
    log_file = data_dir.resolve() / "gunluk" / "uygulama.log"
    assert fake_run["errors"] == [f"30A Studio açılamadı. Ayrıntı program günlüğünde: {log_file}"]
    for handler in logging.getLogger().handlers:
        handler.flush()
    text = log_file.read_text(encoding="utf-8")
    assert "Program başlatılamadı." in text and "create_app bozuldu" in text


def test_main_error_with_console_is_printed_not_boxed(fake_run: dict, monkeypatch: pytest.MonkeyPatch,
                                                      data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    def no_port():
        raise launcher.LauncherError("8830-8849 arasında boş port bulunamadı.")

    monkeypatch.setattr(launcher, "find_free_port", no_port)
    assert launcher.main(["--data-dir", str(data_dir)]) == 1
    assert fake_run["errors"] == []
    assert "boş port bulunamadı" in capsys.readouterr().err


def test_main_shows_error_when_data_dir_cannot_be_prepared(fake_run: dict, monkeypatch: pytest.MonkeyPatch,
                                                           tmp_path: Path) -> None:
    without_console(monkeypatch)
    blocker = tmp_path / "dosya"
    blocker.write_text("x", encoding="utf-8")
    assert launcher.main(["--data-dir", str(blocker)]) == 1
    assert len(fake_run["errors"]) == 1
    assert fake_run["errors"][0].startswith(f"30A Studio açılamadı: {blocker} klasörü hazırlanamadı (")


def test_main_redirects_missing_streams_to_log(fake_run: dict, monkeypatch: pytest.MonkeyPatch,
                                               data_dir: Path) -> None:
    without_console(monkeypatch)
    launcher.main(["--data-dir", str(data_dir), "--no-window"])
    assert sys.stdout is not None and sys.stderr is not None
    print("pythonw altında yazıldı")
    for handler in logging.getLogger().handlers:
        handler.flush()
    text = (data_dir / "gunluk" / "uygulama.log").read_text(encoding="utf-8")
    assert "Program başlıyor (sürüm" in text and "pythonw altında yazıldı" in text


@windows_only
def test_help_is_utf8_when_output_is_redirected() -> None:
    """Sistem kod sayfası 936: yönlendirilmiş çıktıda `ı` gibi harfler kodlanamayınca --help çökerdi."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    result = subprocess.run([sys.executable, "-m", "studio", "--help"], cwd=install_stamp.repo_root(), env=env,
                            capture_output=True, timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    text = result.stdout.decode("utf-8")
    assert "--no-window" in text and "--no-browser" in text and "--data-dir" in text


# ---------- serve ----------

def test_server_uses_selector_event_loop() -> None:
    import asyncio

    config = launcher.server_config(object(), 8830)
    assert config.loop == "asyncio:SelectorEventLoop"
    loop = config.get_loop_factory()()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()


def run_serve(data_dir: Path, opener, **kw) -> tuple[threading.Thread, list[int]]:
    result: list[int] = []
    thread = threading.Thread(target=lambda: result.append(
        launcher.serve(data_dir, free_port(), window=True, watchdog=True, opener=opener, **kw)), daemon=True)
    thread.start()
    return thread, result


def test_serve_opens_window_and_closes_when_window_is_gone(data_dir: Path, monkeypatch: pytest.MonkeyPatch,
                                                           root_handlers) -> None:
    monkeypatch.setenv("STUDIO_WATCHDOG_GRACE", "1")
    lock = data_dir / "calisiyor.json"
    seen: list[tuple[str, dict, dict]] = []

    def opener(url: str) -> None:
        port = int(url.rsplit(":", 1)[1].strip("/"))
        seen.append((url, launcher.read_lock(lock), launcher.instance_health(port)))

    thread, result = run_serve(data_dir, opener)
    thread.join(60)
    assert not thread.is_alive() and result == [0]
    url, written, health = seen[0]
    assert written["pid"] == os.getpid() and url == launcher.app_url(written["port"])
    assert health["app"] == "thirtya-studio" and health["pid"] == os.getpid()
    assert not lock.exists()


def test_serve_waits_for_running_job_before_closing(data_dir: Path, monkeypatch: pytest.MonkeyPatch,
                                                    root_handlers) -> None:
    """Pencere kapalıyken bir iş sürüyorsa sunucu açık kalır, bu iş panelinde görünür; iş bitince kapanır."""
    monkeypatch.setenv("STUDIO_WATCHDOG_GRACE", "1")
    import studio.app

    apps = []
    real_create = studio.app.create_app
    monkeypatch.setattr(studio.app, "create_app", lambda *a, **kw: apps.append(real_create(*a, **kw)) or apps[-1])
    job: list[str] = []

    def opener(url: str) -> None:
        db = apps[0].state.db
        job.append(db.add_job("catalog_audit", "Uzun iş"))
        db.update_job(job[0], status="running", message="Çalışıyor")

    thread, result = run_serve(data_dir, opener)
    db = None
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if job:
            db = apps[0].state.db
            if any(entry["text"] == WAITING_MESSAGE for entry in db.job(job[0])["log"]):
                break
        time.sleep(0.1)
    else:
        pytest.fail("Bekleme notu iş günlüğüne yazılmadı.")
    time.sleep(1.5)
    assert thread.is_alive(), "İş sürerken sunucu kapandı."
    assert db.job(job[0])["message"] == "Çalışıyor"  # not, işin kendi durum satırını değiştirmez
    db.update_job(job[0], status="succeeded", message="Bitti")
    thread.join(30)
    assert not thread.is_alive() and result == [0]


def test_serve_reports_port_in_use(data_dir: Path, root_handlers) -> None:
    """uvicorn başlayamayınca `sys.exit` çağırır; bu Türkçe bir başlatma hatasına çevrilir, kilit yazılmaz."""
    data_dir.mkdir(parents=True)
    logs.setup_logging(data_dir)
    port = free_port()
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", port))
        busy.listen()
        with pytest.raises(launcher.LauncherError, match=f"^Sunucu {port} portunda başlatılamadı"):
            launcher.serve(data_dir, port, window=True, watchdog=False,
                           opener=lambda url: pytest.fail("pencere açıldı"))
    assert not (data_dir / "calisiyor.json").exists()
