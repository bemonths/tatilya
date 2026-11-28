"""HEDEF-04 A, bitiş ölçütü 5: the program's screens and buttons are walked through automatically and neither the browser console nor the
server shows an error. The program runs in this process on a free port with a temporary data folder (never the real `data\\`), the fake
Claude and the tests' network ban (conftest; only 127.0.0.1 is let through). Playwright's headless Chromium (no window, no focus taken).

- The walk: every screen reachable from the left menu, Ayarlar and the links inside the screens is visited and each visible, enabled
  button there is clicked except the ones on the skip list (going out to the network, closing the program, deleting, opening a folder in
  Explorer); the skipped ones are listed at the end. A click that fails on a button still on the screen is an error.
- The new steps: the trial video is taken to 6 · Yayın paketi through the API, then "Yayın paketini çıkar" and "Onayla" are pressed in
  the interface; in 7 · Seslendirme a short wav (Python's `wave`, no ffmpeg) goes in through "Sesi yükle" and "Sesi cümlelerle eşleştir"
  is pressed (the recognizer faked); in 8 · Kurgu paketi "Paketi yeniden kur" and "Kurguya gönder" are pressed (a fake Kurgu Motoru in
  tmp_path, no pnpm) and the motor's output is on the screen.
- Errors: page errors, console errors (a failed load included, except the heartbeat and event stream cut off when the page goes),
  any 5xx and any 4xx (whatever the method; ALLOWED_4XX lists the ones meant to happen), failed requests and the server's error log.
Without Playwright or its Chromium the tests are skipped. The browser closes with `browser.close()`, the server with `should_exit`."""
import logging
import re
import socket
import threading
import time
import wave
from pathlib import Path

import httpx
import pytest

from studio import launcher, voice
from studio.app import create_app
from tests.test_gorev21 import settle as settle_step, step, statuses
from tests.test_hedef04_kurgu import fake_motor
from tests.test_yayin import approve_check
from tests.text_helpers import FAKE, HEADERS, add_video, text_env  # noqa: F401

sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright kurulu değil")

# A button whose label matches is not clicked: it would go out to the network (collectors, trial reads, the browser and its warm-up,
# the extension, the proxy), close the program, delete or reset something, or open a folder or a file picker on the desktop.
SKIP = re.compile(r"(?<!\w)(sil|kaldır|kapat|topla|zamanı gelen|çek(?!ici)|oku\b|yeniden oku|okumay|dene\b|deneme okuması|ısın|bağla|sına|"
                  r"test et|tarayıcı|proxy|sürdür|programı|klasör|dosya seç|geri yükle|sıfırla)", re.IGNORECASE)
# 4xx answers the program gives on purpose (path → why); every other 4xx is an error.
ALLOWED_4XX = {"/api/veri-cekici/liste": "the temporary data folder has no site that needs a browser: 400 'Okunacak sayfa bulunamadı.' "
                                        "is the message the screen shows"}
PER_SCREEN = 25
MAX_SCREENS = 120


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Api:
    """The tests' helpers speak to the program over its own port (the same calls a TestClient would make)."""

    def __init__(self, app, base):
        self.app = app
        self.http = httpx.Client(base_url=base, headers=HEADERS, timeout=60)

    def get(self, url, **kwargs):
        return self.http.get(url, **kwargs)

    def post(self, url, **kwargs):
        return self.http.post(url, **kwargs)

    def put(self, url, **kwargs):
        return self.http.put(url, **kwargs)


class ServerLog(logging.Handler):
    def __init__(self):
        super().__init__(logging.ERROR)
        self.lines = []

    def emit(self, record):
        self.lines.append(f"{record.name}: {record.getMessage()}" + (f"\n{self.format(record)}" if record.exc_info else ""))


@pytest.fixture
def program(text_env, local_network):
    app = create_app(text_env / "data")
    port = free_port()
    server = launcher.studio_server(launcher.server_config(app, port))
    log = ServerLog()
    logging.getLogger().addHandler(log)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not server.started:
        assert time.monotonic() < deadline, "Program 30 saniyede açılmadı."
        time.sleep(0.05)
    api = Api(app, f"http://127.0.0.1:{port}")
    assert api.put("/api/settings/claude", json={"claude_path": str(FAKE)}).status_code == 200
    try:
        yield app, api, port, log
    finally:
        api.http.close()
        server.should_exit = True
        thread.join(15)
        logging.getLogger().removeHandler(log)


def launch(playwright):
    for options in ({}, {"channel": "chromium"}):
        try:
            return playwright.chromium.launch(headless=True, **options)
        except Exception as exc:                       # Chromium not downloaded on this computer
            last = exc
    pytest.skip(f"Playwright'in Chromium'u yok: {str(last).splitlines()[0]}")


def quiet(url):
    """The heartbeat and the event stream are cut off when the page goes away or reloads: not an error of the program."""
    return "/api/heartbeat" in url or "/events" in url


def watch(page, base, errors):
    def console(m):
        if m.type == "error" and not ("Failed to load resource" in m.text and (quiet(m.location.get("url", "")) or allowed(m.location.get("url", "")))):
            errors.append(f"konsol: {m.text} ({m.location.get('url', '')})")

    def allowed(url):
        return url.startswith(base) and url[len(base):].split("?")[0] in ALLOWED_4XX

    def response(r):
        if r.url.startswith(base) and r.status >= 400 and not (r.status < 500 and allowed(r.url)):
            errors.append(f"HTTP {r.status} {r.request.method} {r.url[len(base):]}")
    page.on("console", console)
    page.on("pageerror", lambda e: errors.append(f"sayfa hatası: {e}"))
    page.on("response", response)
    page.on("requestfailed", lambda r: r.url.startswith(base) and not quiet(r.url)
            and errors.append(f"istek düştü: {r.method} {r.url[len(base):]} ({r.failure})"))


HASHES_JS = """() => [...document.querySelectorAll('#navigation a[href^="#"], .nav-footer a[href^="#"], #main a[href^="#"]')]
    .map(a => a.getAttribute('href')).filter(h => h && h.length > 1)"""
BUTTONS_JS = """() => [...document.querySelectorAll('#main button, #main [role=button], #main label.button-like')]
    .filter(b => b.offsetParent !== null && !b.disabled && !b.closest('dialog:not([open])'))
    .map(b => (b.innerText || b.getAttribute('aria-label') || b.title || '').trim().replace(/\\s+/g, ' '))"""
CLOSE_DIALOGS_JS = "() => document.querySelectorAll('dialog[open]').forEach(d => d.close())"
CLOSE_JOBS_JS = "() => document.querySelector('#jobs-toggle[aria-expanded=true]')?.click()"


def settle(page, ms=200):
    page.wait_for_timeout(ms)


def walk(page, base, start, visited, report, errors):
    """Visit every screen reachable from `start` (breadth first over the in-page addresses) and click its buttons."""
    queue = [start]
    while queue and len(visited) < MAX_SCREENS:
        target = queue.pop(0)
        if target in visited:
            continue
        visited.add(target)
        page.evaluate(f"location.hash = {target!r}")
        settle(page, 350)
        if page.evaluate("location.hash") != target:        # an old address that moves elsewhere: the new one is visited itself
            queue.append(page.evaluate("location.hash"))
            continue
        report["ekranlar"].append(target)
        queue += [h for h in page.evaluate(HASHES_JS) if h not in visited and h not in queue]
        labels = list(dict.fromkeys(page.evaluate(BUTTONS_JS)))[:PER_SCREEN]
        for label in labels:
            if not label or SKIP.search(label):
                report["atlanan"].add(label or "(adsız)")
                continue
            button = page.locator("#main button:visible:enabled, #main [role=button]:visible, #main label.button-like:visible") \
                .filter(has_text=label).first
            if not button.count():                          # an earlier click opened a form in its place: the screen afresh, once
                page.reload()
                page.wait_for_selector("#navigation a", timeout=20000)
                settle(page, 350)
            if not button.count():                          # still not there: counted, not clicked
                report["kaybolan"].append(f"{target} → {label}")
                continue
            if button.evaluate("b => b.matches('label')"):  # a file picker ("Sesi yükle"): the picker itself is not opened
                report["atlanan"].add(label)
                continue
            page.evaluate(CLOSE_JOBS_JS)                    # the İşler panel lies over the screen's right side while it is open
            button.evaluate("b => b.scrollIntoView({block: 'center'})")    # not under the sticky top bar
            try:
                button.click(timeout=2500)
            except Exception as exc:
                if button.count() and button.is_visible() and button.is_enabled():
                    errors.append(f"tıklanamadı: {target} → {label}: {' / '.join(str(exc).splitlines()[-4:])}")
                else:                                       # hidden or disabled while being clicked (a job started, the screen redrew)
                    report["kaybolan"].append(f"{target} → {label}")
                continue
            report["tiklanan"].append(f"{target} → {label}")
            settle(page)
            page.evaluate(CLOSE_DIALOGS_JS)
            if page.evaluate("location.hash") != target:
                page.evaluate(f"location.hash = {target!r}")
                settle(page)


def summary(report, errors):
    print(f"\nziyaret edilen ekran: {len(report['ekranlar'])} · tıklanan düğme: {len(report['tiklanan'])} · "
          f"kaybolan: {len(report['kaybolan'])} · hata: {len(errors)}")
    print("atlanan düğmeler: " + " | ".join(sorted(report["atlanan"])))
    if report["kaybolan"]:
        print("tıklanmadan kaybolan: " + " | ".join(report["kaybolan"]))


def test_every_screen_and_button_is_walked_without_errors(program):
    app, api, port, log = program
    base = f"http://127.0.0.1:{port}"
    add_video(api)
    errors = []
    report = {"ekranlar": [], "tiklanan": [], "atlanan": set(), "kaybolan": []}
    with sync_api.sync_playwright() as playwright:
        browser = launch(playwright)
        try:
            page = browser.new_context(viewport={"width": 1280, "height": 860}).new_page()
            page.on("dialog", lambda d: d.dismiss())        # confirm() of a reset or a rerun: answered "no"
            watch(page, base, errors)
            visited = set()
            page.goto(base + "/#videolar")
            page.wait_for_selector("#navigation a", timeout=20000)
            walk(page, base, "#videolar", visited, report, errors)
            walk(page, base, "#settings", visited, report, errors)
            assert api.post("/api/videos/v1/ac", json={}).status_code == 200          # the trial video: its steps come into the menu
            page.goto(base + "/")
            page.wait_for_function("document.querySelectorAll('#navigation a').length >= 8", timeout=20000)
            for target in page.evaluate(HASHES_JS):
                walk(page, base, target, visited, report, errors)
        finally:
            browser.close()
    errors += [f"sunucu: {line}" for line in log.lines]
    summary(report, errors)
    print("ekranlar: " + " ".join(report["ekranlar"]))
    assert any("yayin" in s for s in report["ekranlar"]), report["ekranlar"]
    assert any("kurgu" in s for s in report["ekranlar"]) and any("ses" in s for s in report["ekranlar"]), report["ekranlar"]
    assert not errors, "\n".join(errors)


def short_wav(path, seconds=1.0, rate=16000):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"\0\0" * int(seconds * rate))
    return path


def test_the_new_steps_main_buttons_are_pressed_in_the_interface(program, monkeypatch, tmp_path):
    app, api, port, log = program
    base = f"http://127.0.0.1:{port}"
    approve_check(api)                                                                   # 1–5 through the API (their own tests cover them)
    api.post("/api/videos/v1/ac", json={})
    audio = short_wav(tmp_path / "anlatim.wav")
    monkeypatch.setattr(voice, "duration_of", lambda path, cfg: wave.open(str(path)).getnframes() / 16000)   # no ffprobe
    motor, calls = fake_motor(tmp_path, monkeypatch)
    assert api.put("/api/settings/kurgu", json={"kurgu_motoru_path": str(motor)}).status_code == 200
    errors, pressed = [], []
    main_text = "() => document.querySelector('#main').textContent"

    def press(selector, label, until, limit=60000):
        page.locator(selector).first.click(timeout=10000)
        page.wait_for_function(f"() => document.querySelector('#main').textContent.includes({until!r})", timeout=limit)
        pressed.append(label)

    with sync_api.sync_playwright() as playwright:
        browser = launch(playwright)
        try:
            page = browser.new_context(viewport={"width": 1280, "height": 860}).new_page()
            page.on("dialog", lambda d: d.accept())
            watch(page, base, errors)
            page.goto(base + "/#video/v1/yayin")
            page.wait_for_selector("#publish-start:enabled", timeout=20000)
            press("#publish-start", "6 · Yayın paketini çıkar", "başlat")
            page.locator("#step-estimate button:has-text('başlat')").first.click(timeout=10000)
            pressed.append("6 · tahmin → başlat")
            settle_step(api, "v1", "yayin", {"awaiting_approval", "error"}, limit=90)
            assert statuses(api)["yayin"] == "awaiting_approval", step(api, "yayin")["adim"]
            try:
                page.wait_for_selector("[data-decision=onayla]:enabled", timeout=20000)
            except Exception:
                raise AssertionError("6 · Onayla açılmadı:\n" + page.evaluate(main_text)[-1500:]) from None
            page.fill("#decision-note", "Uygun.")
            press("[data-decision=onayla]", "6 · Onayla", "Onaylandı")
            settle_step(api, "v1", "yayin", {"approved"})

            page.evaluate("location.hash = '#video/v1/ses'")
            page.wait_for_selector("#voice-files:enabled", timeout=20000)
            page.set_input_files("#voice-files", str(audio))
            page.wait_for_function(f"() => ({main_text})().includes('ses yüklendi')", timeout=20000)
            pressed.append("7 · Sesi yükle (anlatim.wav)")
            files = [Path(f["yol"]) for f in step(api, "ses")["ses"]["metin"]["dosyalar"]]
            spoken = " ".join(f.read_text(encoding="utf-8") for f in files).split()
            monkeypatch.setattr(voice, "motor_command", lambda cfg: ["python", "hizala.py"])
            monkeypatch.setattr(voice, "transcribe_part", lambda command, audio, work, cfg: [
                {"word": w, "start": i * 0.1, "end": i * 0.1 + 0.08} for i, w in enumerate(spoken)])
            page.wait_for_selector("#voice-match:enabled", timeout=10000)
            press("#voice-match", "7 · Sesi cümlelerle eşleştir", "cümle eşleşti")
            assert "eşleşmeyen 0 cümle" in page.evaluate(main_text)
            assert statuses(api)["ses"] == "done"

            page.evaluate("location.hash = '#video/v1/kurgu'")
            page.wait_for_selector("#kurgu-build:enabled", timeout=20000)
            press("#kurgu-build", "8 · Paketi yeniden kur", "Ses ve cümle zamanları pakette.")
            page.wait_for_selector("#kurgu-send:enabled", timeout=10000)
            press("#kurgu-send", "8 · Kurguya gönder", "Gönderildi")
            shown = page.evaluate(main_text)
            assert "30a-deneme" in shown and "Paket geçerli" in shown and "Sahneler: 3" in shown, shown[-1500:]
            assert [c[:2] for c in calls] == [["paket", "dogrula"], ["paket", "ice-al"]]
        finally:
            browser.close()
    errors += [f"sunucu: {line}" for line in log.lines]
    print("\nbasılan yeni adım düğmeleri: " + " | ".join(pressed) + f" · hata: {len(errors)}")
    assert not errors, "\n".join(errors)
