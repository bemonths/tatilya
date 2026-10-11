"""Uygulama günlüğü: `<veri klasörü>/gunluk/uygulama.log` (1 MB × 3 dönen dosya).

Konsolsuz çalışmada (pythonw) `sys.stdout` ve `sys.stderr` yoktur; `print` ve hata dökümleri günlüğe yönlendirilir.
Housing Atlas'taki `atlas/logs.py`'nin sadeleştirilmiş kopyası (iş günlüğü biçimi yok). GÖREV-16: gizli değer maskeleme
Housing Atlas'taki gibi: bu süreçte kaydedilen ya da okunan gizli değerler (ABD proxy parolası; `studio.credentials`)
listeye girer ve günlüğe yazılan her mesajda ve hata dökümünde `***` olur; proxy adresi günlükte yalnız `şema://sunucu`
olarak görünür (`proxy_label`).
"""

import io
import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlsplit

LOGS_DIR = "gunluk"
APP_LOG_NAME = "uygulama.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3

LEVEL_NAMES = {logging.DEBUG: "AYRINTI", logging.INFO: "BILGI", logging.WARNING: "UYARI",
               logging.ERROR: "HATA", logging.CRITICAL: "HATA"}


MASK = "***"
# Çok kısa değerler maskelenmez: her geçtiği yerde metni bozar, gizlilik kazancı yoktur.
MIN_SECRET_LENGTH = 4
_secrets: set[str] = set()
_secrets_lock = threading.Lock()


def register_secret(value: str | None) -> None:
    if value and len(value) >= MIN_SECRET_LENGTH:
        with _secrets_lock:
            _secrets.add(value)


def mask(text: str) -> str:
    with _secrets_lock:
        values = sorted(_secrets, key=len, reverse=True)
    for value in values:
        if value in text:
            text = text.replace(value, MASK)
    return text


def proxy_label(url: str) -> str:
    """Proxy adresinin günlükte ve metinlerde görünen biçimi: `şema://sunucu` (port, kullanıcı ve parola olmadan)."""
    try:
        parts = urlsplit((url or "").strip())
        host = parts.hostname
    except ValueError:
        return ""
    if not parts.scheme or not host:
        return ""
    return f"{parts.scheme.lower()}://{host}"


class MaskFilter(logging.Filter):
    """Tutucu süzgeci: biçimlenmiş mesajdaki ve hata dökümündeki gizli değerleri maskeler."""

    _formatter = logging.Formatter()

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            if isinstance(record.args, tuple):
                record.args = tuple(mask(str(arg)) for arg in record.args)
            return True
        masked = mask(message)
        if masked != message:
            record.msg, record.args = masked, None
        if record.exc_text:              # another handler may have formatted (and cached) the traceback already
            record.exc_text = mask(record.exc_text)
        elif record.exc_info:
            record.exc_text = mask(self._formatter.formatException(record.exc_info))
        return True


class _Formatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.levelname_tr = LEVEL_NAMES.get(record.levelno, record.levelname)
        return super().format(record)


_FORMAT = "%(asctime)s [%(levelname_tr)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def log_path(data_dir: Path) -> Path:
    return data_dir / LOGS_DIR / APP_LOG_NAME


def setup_logging(data_dir: Path, *, console: bool = False) -> RotatingFileHandler:
    """Kök günlükçüye dönen dosya tutucusu (ve istenirse konsol) ekler; önceki kurulumun tutucularını kaldırır."""
    path = log_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, "studio_handler", False)]:
        root.removeHandler(handler)
        handler.close()
    file_handler = RotatingFileHandler(path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
    handlers: list[logging.Handler] = [file_handler]
    if console:
        handlers.append(logging.StreamHandler())
    for handler in handlers:
        handler.studio_handler = True
        handler.addFilter(MaskFilter())
        handler.setFormatter(_Formatter(_FORMAT, _DATE_FORMAT))
        root.addHandler(handler)
    root.setLevel(logging.WARNING)
    logging.getLogger("studio").setLevel(logging.INFO)
    return file_handler


class _LogStream(io.TextIOBase):
    """`print` ve yakalanmamış hata dökümlerini satır satır günlüğe yazan akış (pythonw'da konsol yoktur)."""

    def __init__(self, logger: logging.Logger, level: int) -> None:
        super().__init__()
        self._logger, self._level = logger, level
        self._buffer = ""
        self._local = threading.local()

    @property
    def encoding(self) -> str:
        return "utf-8"

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        # Günlük tutucusu hata verirse hata metni yine buraya yazılır; sonsuz döngüye girmemek için bırakılır.
        if getattr(self._local, "busy", False):
            return len(text)
        self._local.busy = True
        try:
            self._buffer += text
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                self._emit(line)
        finally:
            self._local.busy = False
        return len(text)

    def flush(self) -> None:
        if self._buffer and not getattr(self._local, "busy", False):
            line, self._buffer = self._buffer, ""
            self._emit(line)

    def _emit(self, line: str) -> None:
        if line.strip():
            self._logger.log(self._level, line.rstrip())


def utf8_stdio() -> None:
    """Yönlendirilmiş çıktıda da Türkçe harfler yazılabilsin: sistem kod sayfası (936) `ı` gibi harfleri kodlayamaz.
    pythonw'da akışlar yoktur (None); onlara dokunulmaz."""
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None:
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


def redirect_missing_streams() -> bool:
    """`sys.stdout`/`sys.stderr` yoksa (pythonw) onları uygulama günlüğüne yönlendirir. Yönlendirme yapıldıysa True."""
    redirected = False
    if sys.stdout is None:
        sys.stdout = _LogStream(logging.getLogger("studio.stdout"), logging.INFO)
        redirected = True
    if sys.stderr is None:
        sys.stderr = _LogStream(logging.getLogger("studio.stderr"), logging.ERROR)
        redirected = True
    return redirected
