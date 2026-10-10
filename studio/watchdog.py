"""Kapanma bekçisi: uygulama penceresi kapanınca sunucuyu kapatır (Housing Atlas'taki `atlas/watchdog.py`'den).

Ön yüz 10 saniyede bir canlılık sinyali gönderir ve olay akışını açık tutar. Açık akış yoksa ve son sinyalden bu yana
`timeout` saniye geçtiyse (hiç bağlantı gelmediyse başlangıçtan `grace` saniye) ve çalışan iş yoksa `on_shutdown`
bir kez çağrılır. Çalışan iş varsa (toplayıcı, toplu güncelleme, Claude çalışması, eklenti işi) bu bir kez günlüğe ve
`on_waiting` ile iş paneline yazılır; iş bitince kapanılır. Pencere yeniden açılırsa bekleme kendiliğinden biter.
"""

import logging
import os
import threading
import time
from collections.abc import Callable, Mapping

log = logging.getLogger(__name__)

TIMEOUT_ENV = "STUDIO_WATCHDOG_TIMEOUT"
GRACE_ENV = "STUDIO_WATCHDOG_GRACE"
WAITING_MESSAGE = "Pencere kapandı; çalışan iş bitince uygulama kapanacak."
SHUTDOWN_MESSAGE = "Pencere kapalı ve çalışan iş yok; uygulama kapanıyor."


def _env_seconds(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = 0.0
    if value > 0:
        return value
    log.warning("%s ortam değişkeni geçersiz (%r); varsayılan %s saniye kullanılıyor.", name, raw, default)
    return default


class Watchdog:
    def __init__(
        self,
        *,
        timeout: float = 45.0,
        grace: float = 120.0,
        interval: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
        has_active_jobs: Callable[[], bool] = lambda: False,
        on_waiting: Callable[[str], None] = lambda text: None,
        on_shutdown: Callable[[], None] = lambda: None,
    ) -> None:
        self.timeout = timeout
        self.grace = grace
        self.interval = interval
        self.has_active_jobs = has_active_jobs
        self.on_waiting = on_waiting
        self.on_shutdown = on_shutdown
        self._clock = clock
        self._lock = threading.Lock()
        self._started = clock()
        self._last_seen: float | None = None
        self._streams = 0
        self._waiting_logged = False
        self._fired = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, **kwargs) -> "Watchdog":
        """Süreler `STUDIO_WATCHDOG_TIMEOUT` ve `STUDIO_WATCHDOG_GRACE` (saniye) ile değiştirilebilir."""
        env = os.environ if env is None else env
        return cls(timeout=_env_seconds(env, TIMEOUT_ENV, 45.0), grace=_env_seconds(env, GRACE_ENV, 120.0), **kwargs)

    # ---------- ön yüzden gelen sinyaller ----------

    def heartbeat(self) -> None:
        with self._lock:
            self._last_seen = self._clock()

    def stream_opened(self) -> None:
        with self._lock:
            self._streams += 1
            self._last_seen = self._clock()

    def stream_closed(self) -> None:
        with self._lock:
            self._streams = max(0, self._streams - 1)
            self._last_seen = self._clock()

    @property
    def open_streams(self) -> int:
        with self._lock:
            return self._streams

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ---------- karar ----------

    def is_idle(self, now: float) -> bool:
        """Pencereden ses yok mu: açık akış yok ve bekleme süresi dolmuş."""
        with self._lock:
            if self._streams:
                return False
            if self._last_seen is None:
                return now - self._started >= self.grace
            return now - self._last_seen >= self.timeout

    def check(self, now: float | None = None) -> bool:
        """Bir denetim turu; kapanma başlatıldıysa True."""
        if self._fired:
            return True
        now = self._clock() if now is None else now
        if not self.is_idle(now):
            self._waiting_logged = False
            return False
        if self.has_active_jobs():
            if not self._waiting_logged:
                log.info(WAITING_MESSAGE)
                self._waiting_logged = True
                try:
                    self.on_waiting(WAITING_MESSAGE)
                except Exception:
                    log.exception("Bekleme notu iş paneline yazılamadı.")
            return False
        self._fired = True
        log.info(SHUTDOWN_MESSAGE)
        self.on_shutdown()
        return True

    # ---------- arka plan döngüsü ----------

    def start(self) -> None:
        with self._lock:
            self._started = self._clock()
        self._thread = threading.Thread(target=self._run, name="kapanma-bekcisi", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                if self.check():
                    return
            except Exception:
                log.exception("Kapanma bekçisi denetimi hata verdi.")
