"""HEDEF-04 A, bitiş ölçütü 5: the program's screens and buttons are walked through automatically and neither the browser console nor the
server shows an error. The program runs in this process on a free port with a temporary data folder (never the real `data\\`), the fake
Claude and the tests' network ban (conftest; only 127.0.0.1 is let through). A trial video is opened so its steps (1–8, 6 · Yayın paketi,
7 · Seslendirme and 8 · Kurgu paketi included) are in the menu. Playwright's headless Chromium (no window, no focus taken) visits every
screen it can reach from the left menu, Ayarlar and the links inside the screens, and clicks each visible, enabled button there except
the ones on the skip list (network, Claude runs, file pickers, closing, deleting); the skipped ones are listed at the end. Without
Playwright or its Chromium the test is skipped. The browser closes with Playwright's context manager, the server with `should_exit`."""
import logging
import re
import socket
import threading
import time

import httpx
import pytest

from studio import launcher
from studio.app import create_app
from tests.text_helpers import FAKE, HEADERS, add_video, text_env  # noqa: F401

sync_api = pytest.importorskip("playwright.sync_api", reason="Playwright kurulu değil")

# A button whose label starts with one of these words is not clicked: it would reach the network, start a collector or a Claude run,
# open a file picker or a folder, close the program or the video, or delete something.
SKIP = re.compile(r"(?<!\w)(sil|kaldır|kapat|topla|çek|oku|başlat|yenile|güncelle|gönder|yükle|dosya|klasör|indir|claude|çıkar|yaz|dene|"
                  r"ısın|eşle|bağla|sına|test|sürdür|devam|iptal|durdur|kur\b|kurul|doğrula|programı|zamanı gelen|aç\b|seç…|seçili|"
                  r"tamamını|hepsini|bütün|onayla|reddet|düzeltme|içe al|dışa|yedek|geri yükle|sıfırla|yeniden)", re.IGNORECASE)
PER_SCREEN = 25
MAX_SCREENS = 120


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Api:
    """`add_video` speaks to the program over its own port (the same calls a TestClient would make)."""

    def __init__(self, app, base):
        self.app = app
        self.http = httpx.Client(base_url=base, headers=HEADERS, timeout=60)

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


HASHES_JS = """() => [...document.querySelectorAll('#navigation a[href^="#"], .nav-footer a[href^="#"], #main a[href^="#"]')]
    .map(a => a.getAttribute('href')).filter(h => h && h.length > 1)"""
BUTTONS_JS = """() => [...document.querySelectorAll('#main button, #main [role=button]')]
    .filter(b => b.offsetParent !== null && !b.disabled && !b.closest('dialog:not([open])'))
    .map(b => (b.innerText || b.getAttribute('aria-label') || b.title || '').trim().replace(/\\s+/g, ' '))"""
CLOSE_DIALOGS_JS = "() => document.querySelectorAll('dialog[open]').forEach(d => d.close())"


def settle(page, ms=200):
    page.wait_for_timeout(ms)


def walk(page, base, start, visited, report):
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
            button = page.locator("#main button:visible:enabled, #main [role=button]:visible").filter(has_text=label).first
            try:
                button.click(timeout=2500)
            except Exception:
                continue                                    # the screen changed under the list: not an error of the program
            report["tiklanan"].append(f"{target} → {label}")
            settle(page)
            page.evaluate(CLOSE_DIALOGS_JS)
            if page.evaluate("location.hash") != target:
                page.evaluate(f"location.hash = {target!r}")
                settle(page)


def test_every_screen_and_button_is_walked_without_errors(program):
    app, api, port, log = program
    base = f"http://127.0.0.1:{port}"
    assert api.put("/api/settings/claude", json={"claude_path": str(FAKE)}).status_code == 200
    add_video(api)
    errors = []
    report = {"ekranlar": [], "tiklanan": [], "atlanan": set()}
    with sync_api.sync_playwright() as playwright:
        browser = launch(playwright)
        try:
            page = browser.new_context(viewport={"width": 1280, "height": 860}).new_page()
            page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text
                    and errors.append(f"konsol: {m.text}"))
            page.on("pageerror", lambda e: errors.append(f"sayfa hatası: {e}"))

            def response(r):
                if r.url.startswith(base) and (r.status >= 500 or (r.status >= 400 and r.request.method == "GET")):
                    errors.append(f"HTTP {r.status} {r.request.method} {r.url[len(base):]}")
            page.on("response", response)
            page.on("requestfailed", lambda r: r.url.startswith(base) and "/events" not in r.url and "/api/heartbeat" not in r.url
                    and errors.append(f"istek düştü: {r.method} {r.url[len(base):]} ({r.failure})"))
            visited = set()
            page.goto(base + "/#videolar")
            page.wait_for_selector("#navigation a", timeout=20000)
            walk(page, base, "#videolar", visited, report)
            walk(page, base, "#settings", visited, report)
            assert api.post("/api/videos/v1/ac", json={}).status_code == 200          # the trial video: its steps come into the menu
            page.goto(base + "/")
            page.wait_for_function("document.querySelectorAll('#navigation a').length >= 8", timeout=20000)
            steps = page.evaluate(HASHES_JS)
            for step in steps:
                walk(page, base, step, visited, report)
        finally:
            browser.close()
    errors += [f"sunucu: {line}" for line in log.lines]
    print(f"\nziyaret edilen ekran: {len(report['ekranlar'])} · tıklanan düğme: {len(report['tiklanan'])} · hata: {len(errors)}")
    print("atlanan düğmeler: " + " | ".join(sorted(report["atlanan"])))
    print("ekranlar: " + " ".join(report["ekranlar"]))
    assert any("/yayin" in s or "yayin" in s for s in report["ekranlar"]), report["ekranlar"]
    assert any("kurgu" in s for s in report["ekranlar"]) and any("ses" in s for s in report["ekranlar"]), report["ekranlar"]
    assert not errors, "\n".join(errors)
