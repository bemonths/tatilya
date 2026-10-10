"""Masaüstü başlatıcısı: `python -m studio [--data-dir KLASÖR] [--port N] [--no-window|--no-browser] [--no-watchdog]`.

Housing Atlas'taki `atlas/launcher.py`'den uyarlandı (GÖREV-14). Program aynı yerel web uygulamasıdır; masaüstü hissini
bu başlatıcı verir. Sıra: çıktı akışları UTF-8 → günlük (`<veri>/gunluk/uygulama.log`; pythonw'da çıktı akışları
günlüğe) → başlatma kilidi (`<veri>/baslatiliyor.kilit`; aynı veri klasöründe iki başlatıcı "kilide bak → port seç →
sunucuyu aç → kilidi yaz" adımlarını aynı anda yapamaz) → tek kopya (`<veri>/calisiyor.json` + `/api/health`; sağlık
cevabındaki pid kilittekiyle aynı olmalı; çalışan varsa açık uygulama penceresi öne getirilir, yoksa yeni pencere
açılır) → kurulum damgası (yalnız pencereli açılışta; tutmuyorsa `baslat.bat kur` görünür bir pencerede açılır) → boş
port (8830–8849; Housing Atlas 8790–8809 kullanır, iki program aynı anda açık olabilir) → uvicorn (SelectorEventLoop)
→ sunucu hazır olunca kilit, başlatma kilidinin bırakılması ve uygulama kipi pencere (Edge, yoksa Chrome, yoksa
varsayılan tarayıcı). Başlatma başarısız olursa konsolsuz çalışmada Türkçe bir hata kutusu gösterilir. Kapanma bekçisi
yalnız pencere açıldığında çalışır ve `server.should_exit` ile sunucuyu durdurur; kilit yalnız kendi pid'imizi
taşıyorsa silinir.

Geliştirme ve deneme komutu aynen çalışır: `python -m studio --data-dir … --no-browser --port …` (pencere ve bekçi yok;
Ctrl+C ya da Ctrl+Break ile kapanır). Windows dışında (CI Linux'ta çalışır) başlatma kilidi `fcntl.flock` ile alınır;
kayıt defteri, pencere öne getirme ve ileti kutusu yoktur.
"""

import argparse
import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__, install_stamp, logs

log = logging.getLogger(__name__)

APP_ID = "thirtya-studio"
APP_NAME = "30A Studio"
HOST = "127.0.0.1"
PORT_RANGE = (8830, 8849)
WINDOW_SIZE = "1440,900"
DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data"
LOCK_FILE = "calisiyor.json"
STARTUP_LOCK_FILE = "baslatiliyor.kilit"
BROWSERS = {
    "msedge.exe": Path("Microsoft") / "Edge" / "Application",
    "chrome.exe": Path("Google") / "Chrome" / "Application",
}
APP_PATHS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{}"
STARTUP_TIMEOUT = 60.0
# Proactor döngüsü (Windows varsayılanı), kabulden önce koparılan tek bir bağlantıda dinleyen soketi kapatabiliyor;
# sunucu açık görünür ama yeni bağlantı almaz (Housing Atlas'ta görüldü). Uygulama asyncio alt süreci kullanmaz.
EVENT_LOOP = "asyncio:SelectorEventLoop"
# Edge/Chrome uygulama kipi penceresinin sınıfı; başlık sayfanın başlığıdır (`30A Studio · Videolar`).
APP_WINDOW_CLASS = "Chrome_WidgetWin_1"
# Sıradan tarayıcı penceresinin başlığına tarayıcının adı eklenir (Edge adında görünmez bir boşluk olabilir).
BROWSER_TITLE_ENDINGS = (" - Google Chrome", " - Microsoft Edge", " - Microsoft\u200b Edge", " - Chromium")
MB_ICONERROR = 0x10
MB_SETFOREGROUND = 0x10000
SW_RESTORE = 9
NO_AUTO_INSTALL = ("Kurulum güncel değil: requirements-lock.txt değişmiş ya da kurulum damgası yok. Bu işletim "
                   "sisteminde kurulum kendiliğinden yapılmaz; depo klasöründe şu iki komutu çalıştırıp programı "
                   "yeniden açın: .venv/bin/python -m pip install -r requirements-lock.txt ve "
                   ".venv/bin/python -m studio.install_stamp write")


class LauncherError(RuntimeError):
    pass


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m studio", description=APP_NAME)
    parser.add_argument("--port", type=int, help="sunucu portu (verilmezse 8830-8849 arasındaki ilk boş port)")
    parser.add_argument("--data-dir", type=Path, help="veri klasörü (verilmezse depodaki data klasörü)")
    parser.add_argument("--no-window", action="store_true", help="pencere açma (deneme ve geliştirme)")
    parser.add_argument("--no-browser", action="store_true", help="--no-window ile aynı (eski ad)")
    parser.add_argument("--no-watchdog", action="store_true", help="pencere kapanınca sunucuyu kapatma")
    return parser.parse_args(argv)


def app_url(port: int) -> str:
    return f"http://{HOST}:{port}/"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


# ---------- kurulum damgası ----------

def running_in_repo_venv() -> bool:
    return Path(sys.prefix).resolve() == (install_stamp.repo_root() / ".venv").resolve()


def needs_install() -> bool:
    return running_in_repo_venv() and not install_stamp.is_current()


def spawn_installer(popen: Callable[..., Any] = subprocess.Popen) -> None:
    """`baslat.bat kur` yeni bir görünür pencerede açılır; kurulumdan sonra program kendiliğinden açılır."""
    if sys.platform != "win32":
        raise LauncherError(NO_AUTO_INSTALL)
    root = install_stamp.repo_root()
    # Göreli yol ve cwd: depo yolundaki '&', '(' ya da '%' gibi karakterler `cmd /c` satırını bozmasın.
    popen([os.environ.get("COMSPEC") or "cmd.exe", "/c", ".\\baslat.bat", "kur"], cwd=root,
          creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))


# ---------- başlatma kilidi ----------

def _lock_first_byte(fd: int) -> None:
    """Dosyanın ilk baytını beklemeden kilitler; başka bir tutamak kilitliyse OSError."""
    os.lseek(fd, 0, os.SEEK_SET)
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_first_byte(fd: int) -> None:
    os.lseek(fd, 0, os.SEEK_SET)
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)


class StartupLock:
    """Aynı veri klasöründeki başlatıcıları sıraya sokar: "kilide bak → port seç → sunucuyu aç → kilidi yaz".

    Kilit, dosyanın ilk baytındaki işletim sistemi kilididir: süreç ölürse Windows kendiliğinden bırakır; iş parçacığına
    bağlı değildir (sunucu hazır olunca başlangıç iş parçacığı bırakır). Dosya silinmez; içinde bir şey tutulmaz.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None
        self._guard = threading.Lock()

    @property
    def held(self) -> bool:
        with self._guard:
            return self._fd is not None

    def acquire(self, timeout: float, poll: float = 0.1) -> bool:
        """Kilidi alır; `timeout` saniyede alınamazsa False. Dosya açılamazsa OSError."""
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o666)
        deadline = time.monotonic() + timeout
        while True:
            try:
                _lock_first_byte(fd)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    os.close(fd)
                    return False
                time.sleep(poll)
        with self._guard:
            self._fd = fd
        return True

    def release(self) -> None:
        """Kilidi bırakır; alınmamışsa ya da zaten bırakıldıysa bir şey yapmaz."""
        with self._guard:
            fd, self._fd = self._fd, None
        if fd is None:
            return
        try:
            _unlock_first_byte(fd)
        except OSError:
            pass
        finally:
            os.close(fd)


# ---------- tek kopya ----------

def read_lock(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_lock(path: Path, port: int, pid: int | None = None) -> None:
    write_json_atomic(path, {"pid": pid or os.getpid(), "port": port, "started_at": now_iso()})


def remove_lock(path: Path, pid: int | None = None) -> bool:
    """Kilit yalnız bu sürecin pid'ini taşıyorsa silinir."""
    lock = read_lock(path)
    if lock is None or lock.get("pid") != (pid or os.getpid()):
        return False
    path.unlink(missing_ok=True)
    return True


def instance_health(port: int, timeout: float = 1.0) -> dict[str, Any] | None:
    """Portta 30A Studio çalışıyorsa `/api/health` cevabı (`app == "thirtya-studio"`); değilse None."""
    # Sistem proxy ayarı yerel isteği başka yere yönlendirmesin.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://{HOST}:{port}/api/health", timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("app") == APP_ID else None


def running_instance_port(lock_path: Path,
                          health: Callable[[int], dict[str, Any] | None] = instance_health) -> int | None:
    """Kilitteki port, kilidi yazan sürece ait canlı bir kopyaysa o port; kilit yoksa ya da bayatsa None.

    Pid de karşılaştırılır: bayat bir kilidin portunda başka bir veri klasörüyle çalışan bir kopya (deneme sunucusu)
    varsa o kopyanın penceresi açılmaz.
    """
    lock = read_lock(lock_path)
    if not lock:
        return None
    port, pid = lock.get("port"), lock.get("pid")
    if not isinstance(port, int) or isinstance(port, bool) or not isinstance(pid, int) or isinstance(pid, bool):
        return None
    data = health(port)
    if data is None or data.get("pid") != pid:
        return None
    return port


# ---------- port ----------

def find_free_port(start: int = PORT_RANGE[0], end: int = PORT_RANGE[1]) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((HOST, port))
            except OSError:
                continue
            return port
    raise LauncherError(f"{start}-{end} arasında boş port bulunamadı. Açık kalan program pencerelerini kapatıp "
                        "yeniden deneyin.")


# ---------- pencere ----------

def registry_app_path(exe: str) -> Path | None:
    """Kayıt defterindeki App Paths kaydı (önce bilgisayar, sonra kullanıcı); Windows dışında None."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
    except ImportError:
        return None
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, APP_PATHS_KEY.format(exe)) as key:
                value, _ = winreg.QueryValueEx(key, None)
        except OSError:
            continue
        path = Path(os.path.expandvars(str(value).strip().strip('"')))
        if path.is_file():
            return path
    return None


def known_browser_paths(exe: str, env: Mapping[str, str] | None = None) -> list[Path]:
    env = os.environ if env is None else env
    roots = (env.get(name) for name in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"))
    return [Path(root) / BROWSERS[exe] / exe for root in roots if root]


def find_browser(*, app_path: Callable[[str], Path | None] = registry_app_path,
                 known_paths: Callable[[str], list[Path]] = known_browser_paths) -> Path | None:
    """Edge, yoksa Chrome: önce kayıt defteri, sonra bilinen kurulum klasörleri."""
    for exe in BROWSERS:
        found = app_path(exe) or next((path for path in known_paths(exe) if path.is_file()), None)
        if found:
            return found
    return None


def window_command(browser: Path, url: str, size: str = WINDOW_SIZE) -> list[str]:
    """Kullanıcının olağan tarayıcı profiliyle uygulama kipi pencere (adres çubuğu ve sekme yok). Program bu profilin
    çerezlerine, parolalarına ya da geçmişine erişmez; yalnız kendi yerel adresini açtırır."""
    return [str(browser), f"--app={url}", f"--window-size={size}"]


def open_window(url: str, *, find: Callable[[], Path | None] = find_browser,
                popen: Callable[..., Any] = subprocess.Popen, fallback: Callable[[str], Any] = webbrowser.open,
                size: str = WINDOW_SIZE) -> None:
    browser = find()
    if browser is None:
        log.info("Edge ya da Chrome bulunamadı; program varsayılan tarayıcıda açılıyor.")
        fallback(url)
        return
    try:
        popen(window_command(browser, url, size), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL)
    except OSError as exc:
        log.warning("Uygulama penceresi açılamadı (%s); varsayılan tarayıcı deneniyor.", exc)
        fallback(url)


def is_app_window(class_name: str, title: str) -> bool:
    """Uygulama kipindeki penceremiz mi: Edge/Chrome penceresi, başlığı `30A Studio` ya da `30A Studio · <sayfa>`.

    Sıradan tarayıcı pencerelerinin başlığı "- Microsoft Edge" ya da "- Google Chrome" gibi bir ekle biter; onlar
    sayılmaz.
    """
    if class_name != APP_WINDOW_CLASS or title.endswith(BROWSER_TITLE_ENDINGS):
        return False
    return title == APP_NAME or title.startswith(f"{APP_NAME} · ")


def find_app_windows(match: Callable[[str, str], bool] = is_app_window) -> list[int]:
    """Açık uygulama pencerelerinin tutamakları (Windows dışında ya da hata olursa boş liste)."""
    if sys.platform != "win32":
        return []
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        found: list[int] = []

        def visit(hwnd: int, _: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            class_name = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, class_name, 64)
            if match(class_name.value, title.value):
                found.append(hwnd)
            return True

        user32.EnumWindows(callback_type(visit), 0)
        return found
    except (AttributeError, OSError) as exc:
        log.warning("Açık program pencereleri aranamadı: %s", exc)
        return []


def activate_window(hwnd: int) -> bool:
    """Pencereyi simge durumundan çıkarır ve öne getirir; Windows izin vermezse görev çubuğunda yanıp söner."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        for name in ("IsIconic", "ShowWindow", "SetForegroundWindow"):
            getattr(user32, name).argtypes = [wintypes.HWND] + ([ctypes.c_int] if name == "ShowWindow" else [])
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        return bool(user32.SetForegroundWindow(hwnd))
    except (AttributeError, OSError) as exc:
        log.warning("Program penceresi öne getirilemedi: %s", exc)
        return False


def show_app(port: int, *, find: Callable[[], list[int]] = find_app_windows,
             activate: Callable[[int], bool] = activate_window, opener: Callable[[str], None] = open_window) -> None:
    """Çalışan kopyanın açık penceresini öne getirir; açık pencere yoksa yeni pencere açar.

    Her tıklamada yeni pencere açılsaydı her pencerenin olay akışı tarayıcının sunucu başına 6 bağlantılık sınırını
    doldururdu.
    """
    windows = find()
    if windows:
        activate(windows[0])
        log.info("Program penceresi zaten açık; öne getirildi.")
        return
    opener(app_url(port))


def show_error(text: str, title: str = APP_NAME) -> None:
    """Konsolsuz çalışmada (pythonw) başlatma hatasını bir Windows ileti kutusuyla gösterir; başka sistemlerde yalnız
    günlüğe yazar."""
    if sys.platform != "win32":
        log.warning("Başlatma hatası ileti kutusuyla gösterilemedi (yalnız Windows'ta var): %s", text)
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
        user32.MessageBoxW(None, text, title, MB_ICONERROR | MB_SETFOREGROUND)
    except (AttributeError, OSError) as exc:
        log.warning("Hata kutusu gösterilemedi: %s", exc)


# ---------- sunucu ----------

def _when_started(server: Any, action: Callable[[], None], timeout: float = STARTUP_TIMEOUT) -> None:
    """Sunucu dinlemeye başlayınca `action`'ı çalıştırır (ayrı iş parçacığında çağrılır)."""
    deadline = time.monotonic() + timeout
    while not server.started:
        if server.should_exit or time.monotonic() > deadline:
            return
        time.sleep(0.05)
    action()


def server_config(app: Any, port: int) -> Any:
    import uvicorn

    return uvicorn.Config(app, host=HOST, port=port, log_config=None, log_level="warning", access_log=False,
                          timeout_graceful_shutdown=5, loop=EVENT_LOOP)


def serve(data_dir: Path, port: int, *, window: bool, watchdog: bool,
          opener: Callable[[str], None] = open_window, startup_lock: StartupLock | None = None,
          announce: Callable[[str], None] | None = None) -> int:
    """Sunucuyu çalıştırır ve kapanınca 0 döndürür. Sunucu hiç başlayamazsa (ör. port dolu) `LauncherError`."""
    import uvicorn

    from .app import create_app

    app = create_app(data_dir)
    server = uvicorn.Server(server_config(app, port))
    lock_path = data_dir / LOCK_FILE

    def on_started() -> None:
        try:
            write_lock(lock_path, port)
        except OSError as exc:
            log.error("Kilit dosyası yazılamadı (%s): %s", lock_path, exc)
        finally:
            if startup_lock is not None:
                startup_lock.release()
        log.info("Sunucu hazır: %s", app_url(port))
        if announce is not None:
            announce(app_url(port))
        if window:
            opener(app_url(port))

    def request_exit() -> None:
        server.should_exit = True

    guard = app.state.watchdog
    guard.on_shutdown = request_exit
    threading.Thread(target=_when_started, args=(server, on_started), name="baslangic", daemon=True).start()
    if watchdog:
        guard.start()
    try:
        server.run()
    except SystemExit:
        # uvicorn başlayamayınca (port dolu vb.) sebebi günlüğe yazıp `sys.exit` çağırır.
        if server.started:
            raise
    finally:
        server.should_exit = True
        guard.stop()
        remove_lock(lock_path)
    if not server.started:
        raise LauncherError(f"Sunucu {port} portunda başlatılamadı. Açık kalan program pencerelerini kapatıp yeniden "
                            f"deneyin. Ayrıntı: {logs.log_path(data_dir)}")
    log.info("Program kapandı.")
    return 0


def _take_startup_lock(lock: StartupLock) -> None:
    try:
        if not lock.acquire(STARTUP_TIMEOUT):
            log.warning("Başka bir başlatma %d saniyedir bitmedi; beklemeden devam ediliyor.", STARTUP_TIMEOUT)
    except OSError as exc:
        log.warning("Başlatma kilidi alınamadı (%s); kilitsiz devam ediliyor.", exc)


def _start(args: argparse.Namespace, data_dir: Path, startup: StartupLock, console: bool) -> int:
    window = not (args.no_window or args.no_browser)
    _take_startup_lock(startup)

    port = running_instance_port(data_dir / LOCK_FILE)
    if port is not None:
        log.info("Program zaten çalışıyor (port %d); yeni sunucu açılmadı.", port)
        if console:
            print(f"30A Studio zaten açık: {app_url(port)}")
        if window:
            show_app(port)
        return 0

    if window and needs_install():
        log.info("Kurulum damgası tutmuyor; kurulum penceresi açılıyor (baslat.bat kur).")
        spawn_installer()
        return 0

    if args.port:
        port = args.port
    else:
        port = find_free_port()

    def announce(url: str) -> None:
        if console:
            print(f"30A Studio: {url}\nKapatmak için bu pencerede Ctrl+C kullanın.", flush=True)

    return serve(data_dir, port, window=window, watchdog=window and not args.no_watchdog, startup_lock=startup,
                 announce=announce)


def _failure_text(exc: Exception, data_dir: Path, logging_ready: bool) -> str:
    if isinstance(exc, LauncherError):
        return str(exc)
    if not logging_ready:
        reason = exc.strerror if isinstance(exc, OSError) and exc.strerror else str(exc)
        return f"30A Studio açılamadı: {data_dir} klasörü hazırlanamadı ({reason})."
    return f"30A Studio açılamadı. Ayrıntı program günlüğünde: {logs.log_path(data_dir)}"


def main(argv: list[str] | None = None) -> int:
    logs.utf8_stdio()
    console = sys.stderr is not None
    args = parse_args(argv)
    data_dir = (args.data_dir or DEFAULT_DATA).resolve()
    startup = StartupLock(data_dir / STARTUP_LOCK_FILE)
    logging_ready = False
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        logs.setup_logging(data_dir, console=console)
        logging_ready = True
        logs.redirect_missing_streams()
        log.info("Program başlıyor (sürüm %s, pid %d, veri klasörü %s).", __version__, os.getpid(), data_dir)
        return _start(args, data_dir, startup, console)
    except Exception as exc:
        if isinstance(exc, LauncherError):
            log.error("%s", exc)
        else:
            log.exception("Program başlatılamadı.")
        if console:
            print(_failure_text(exc, data_dir, logging_ready), file=sys.stderr)
        else:
            show_error(_failure_text(exc, data_dir, logging_ready))
        return 1
    finally:
        startup.release()
