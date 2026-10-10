"""GÖREV-14: kapanma bekçisi (Housing Atlas'taki `tests/test_watchdog.py`'den uyarlandı)."""
import logging
import threading

import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.watchdog import WAITING_MESSAGE, Watchdog


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


def make(clock: Clock, jobs: list[bool] | None = None) -> tuple[Watchdog, list[int], list[str]]:
    fired: list[int] = []
    notes: list[str] = []
    active = jobs if jobs is not None else [False]
    guard = Watchdog(timeout=45, grace=120, clock=clock, has_active_jobs=lambda: active[0],
                     on_waiting=notes.append, on_shutdown=lambda: fired.append(1))
    return guard, fired, notes


def test_grace_period_without_any_contact(clock: Clock) -> None:
    guard, fired, _ = make(clock)
    clock.now += 119
    assert not guard.check()
    clock.now += 1
    assert guard.check()
    assert fired == [1]


def test_open_stream_keeps_running(clock: Clock) -> None:
    guard, fired, _ = make(clock)
    guard.stream_opened()
    assert guard.open_streams == 1
    clock.now += 10_000
    assert not guard.check()
    assert fired == []


def test_heartbeat_then_silence(clock: Clock) -> None:
    guard, fired, _ = make(clock)
    guard.heartbeat()
    clock.now += 44
    assert not guard.check()
    guard.heartbeat()
    clock.now += 44
    assert not guard.check()
    clock.now += 1
    assert guard.check()
    assert fired == [1]


def test_closed_stream_starts_timeout(clock: Clock) -> None:
    guard, _, _ = make(clock)
    guard.stream_opened()
    clock.now += 500
    guard.stream_closed()
    guard.stream_closed()  # sayaç eksiye düşmez
    assert guard.open_streams == 0
    clock.now += 44
    assert not guard.check()
    clock.now += 1
    assert guard.check()


def test_waits_for_running_job_and_tells_log_and_job_panel_once(clock: Clock,
                                                                 caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="studio.watchdog")
    jobs = [True]
    guard, fired, notes = make(clock, jobs)
    guard.heartbeat()
    clock.now += 100
    for _ in range(5):
        clock.now += 1
        assert not guard.check()
    assert caplog.text.count(WAITING_MESSAGE) == 1
    assert notes == [WAITING_MESSAGE]
    assert fired == []
    jobs[0] = False
    assert guard.check()
    assert fired == [1]


def test_window_returning_cancels_waiting(clock: Clock) -> None:
    guard, fired, notes = make(clock, [True])
    guard.heartbeat()
    clock.now += 50
    guard.check()
    guard.heartbeat()  # pencere yeniden açıldı
    assert not guard.check()
    clock.now += 50
    guard.check()
    assert notes == [WAITING_MESSAGE, WAITING_MESSAGE]
    assert fired == []


def test_failing_note_does_not_stop_watchdog(clock: Clock) -> None:
    def broken(text):
        raise RuntimeError("veritabanı kilitli")

    fired: list[int] = []
    active = [True]
    guard = Watchdog(timeout=45, grace=120, clock=clock, has_active_jobs=lambda: active[0], on_waiting=broken,
                     on_shutdown=lambda: fired.append(1))
    clock.now += 200
    assert not guard.check()
    active[0] = False
    assert guard.check() and fired == [1]


def test_shutdown_fires_once(clock: Clock) -> None:
    guard, fired, _ = make(clock)
    clock.now += 200
    assert guard.check()
    assert guard.check()
    assert fired == [1]


def test_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STUDIO_WATCHDOG_TIMEOUT", "2")
    monkeypatch.setenv("STUDIO_WATCHDOG_GRACE", "3.5")
    guard = Watchdog.from_env()
    assert (guard.timeout, guard.grace) == (2.0, 3.5)


@pytest.mark.parametrize("raw", ["abc", "0", "-5"])
def test_from_env_ignores_invalid(raw: str) -> None:
    guard = Watchdog.from_env({"STUDIO_WATCHDOG_TIMEOUT": raw})
    assert (guard.timeout, guard.grace) == (45.0, 120.0)


def test_background_loop_calls_shutdown() -> None:
    done = threading.Event()
    guard = Watchdog(timeout=0.2, grace=0.2, interval=0.05, on_shutdown=done.set)
    guard.start()
    try:
        assert done.wait(5)
    finally:
        guard.stop()


def test_background_loop_stops() -> None:
    done = threading.Event()
    guard = Watchdog(timeout=60, grace=60, interval=0.05, on_shutdown=done.set)
    guard.start()
    guard.stop()
    assert not done.is_set()
    assert not guard.running


# ---------- uygulamaya bağlantı ----------

def test_app_heartbeat_and_health(tmp_path) -> None:
    beats: list[int] = []
    guard = Watchdog()
    guard.heartbeat = lambda: beats.append(1)
    with TestClient(create_app(tmp_path, watchdog=guard)) as client:
        health = client.get("/api/health").json()
        assert health["app"] == "thirtya-studio" and isinstance(health["pid"], int)
        assert client.post("/api/heartbeat").status_code == 403  # uygulama başlığı olmadan reddedilir
        assert client.post("/api/heartbeat", headers={"x-studio-request": "1"}).status_code == 204
    assert beats == [1]


def test_active_work_and_job_notes(tmp_path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        db = client.app.state.db
        assert not db.has_active_work()
        job = db.add_job("catalog_audit", "Kontrol")
        assert db.has_active_work()
        db.update_job(job, status="running", message="Çalışıyor")
        db.note_active_jobs(WAITING_MESSAGE)
        record = db.job(job)
        assert record["message"] == "Çalışıyor"
        assert [entry["text"] for entry in record["log"]] == ["Çalışıyor", WAITING_MESSAGE]
        db.update_job(job, status="succeeded", message="Bitti")
        assert not db.has_active_work()
        db.note_active_jobs("bitmiş işe yazılmaz")
        assert "bitmiş işe yazılmaz" not in [entry["text"] for entry in db.job(job)["log"]]
