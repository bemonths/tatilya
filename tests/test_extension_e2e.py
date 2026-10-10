"""GÖREV-14 Adım 7d, end to end: Playwright's Chromium with a temporary profile loads the extension; the program runs on a free port; a local
trial server serves a normal page, a page drawn by JavaScript, a verification-like page that clears by itself, one that never clears, a
sign-in page and a JSON endpoint. No real site is opened. The user's tab stays untouched and the extension's window is closed afterwards.

Runs only with STUDIO_EKLENTI_E2E=1 (Playwright and its Chromium are needed; not in CI); STUDIO_EKLENTI_CHROMIUM may name a Chromium
that Playwright downloaded before. Screenshots for the install guide are written to STUDIO_EKLENTI_EKRAN (a folder) when it is set.
"""
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from studio import extension as ext
from studio import launcher

pytestmark = pytest.mark.skipif(not os.environ.get("STUDIO_EKLENTI_E2E"), reason="uçtan uca eklenti denemesi: STUDIO_EKLENTI_E2E=1 ile çalışır")
EXTENSION = Path(__file__).resolve().parents[1] / "eklenti"

PAGES = {
    "/normal": "<!doctype html><html><head><title>Normal sayfa</title></head><body><h1>Normal içerik</h1></body></html>",
    "/js": ("<!doctype html><html><head><title>JS sayfası</title></head><body><div id='kok'></div><script>setTimeout(() => {"
            "const p = document.createElement('p'); p.id = 'icerik'; p.textContent = 'JavaScript ile çizildi';"
            "document.getElementById('kok').appendChild(p); }, 1200);</script></body></html>"),
    "/dogrulama": ("<!doctype html><html><head><title>Just a moment...</title></head><body><p>Checking your browser before accessing</p>"
                   "<script>setTimeout(() => { document.title = 'Geçti'; document.body.innerHTML = '<h1>Doğrulama sonrası içerik</h1>'; }, 4000);"
                   "</script></body></html>"),
    "/dogrulama-kalici": "<!doctype html><html><head><title>Just a moment...</title></head><body>cf_chl_opt</body></html>",
    "/giris": ("<!doctype html><html><head><title>Sign in</title></head><body><form><input name='u'><input type='password' name='p'>"
               "</form></body></html>"),
}


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def trial_site():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/api/veri":
                body, kind = b'{"ok": true, "kaynak": "yerel"}', "application/json"
            elif self.path in PAGES:
                body, kind = PAGES[self.path].encode("utf-8"), "text/html; charset=utf-8"
            else:
                body, kind = b"<html><title>yok</title></html>", "text/html"
            self.send_response(200 if self.path in PAGES or self.path == "/api/veri" else 404)
            self.send_header("Content-Type", kind)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def program(tmp_path, monkeypatch):
    monkeypatch.setattr(ext, "VERIFY_WAIT_S", 10)            # the never-clearing page is given up after 10 s here (15 min for the user)
    from studio.app import create_app
    app = create_app(tmp_path / "veri")
    port = free_port()
    server = launcher.studio_server(launcher.server_config(app, port))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not server.started:
        assert time.monotonic() < deadline
        time.sleep(0.05)
    app.state.extension.set_gap(3)
    yield app, port
    server.should_exit = True
    thread.join(10)


def test_the_extension_reads_local_pages_in_its_own_window(program, tmp_path):
    from playwright.sync_api import sync_playwright
    app, port = program
    bridge = app.state.extension
    site = trial_site()
    base = f"http://127.0.0.1:{site.server_address[1]}"
    shots = Path(os.environ["STUDIO_EKLENTI_EKRAN"]) if os.environ.get("STUDIO_EKLENTI_EKRAN") else None
    with sync_playwright() as playwright:
        executable = os.environ.get("STUDIO_EKLENTI_CHROMIUM")                    # a Chromium Playwright downloaded before, if its own is missing
        browser = {"executable_path": executable} if executable else {"channel": "chromium"}
        context = playwright.chromium.launch_persistent_context(str(tmp_path / "gecici-profil"), headless=True, **browser,
                                                                args=[f"--disable-extensions-except={EXTENSION}", f"--load-extension={EXTENSION}"],
                                                                viewport={"width": 1100, "height": 760})
        try:
            worker = context.service_workers[0] if context.service_workers else context.wait_for_event("serviceworker", timeout=20000)
            extension_id = worker.url.split("/")[2]
            user = context.pages[0] if context.pages else context.new_page()
            user.goto(f"{base}/normal")
            worker.evaluate(f"chrome.storage.local.set({{port: {port}}})")
            popup = context.new_page()
            popup.goto(f"chrome-extension://{extension_id}/popup.html")
            popup.fill("#kod", bridge.code())
            popup.click("button[type=submit]")
            popup.wait_for_function("document.querySelector('#eslesme-sonuc').textContent.startsWith('Eşleşti')", timeout=20000)
            deadline = time.monotonic() + 20
            while not bridge.connected:
                assert time.monotonic() < deadline, "Eklenti programa bağlanmadı."
                time.sleep(0.2)
            assert bridge.config["koken"] == f"chrome-extension://{extension_id}"
            if shots:
                shots.mkdir(parents=True, exist_ok=True)
                popup.reload()
                popup.wait_for_timeout(800)
                popup.screenshot(path=str(shots / "eklenti-penceresi.png"))
                manage = context.new_page()
                manage.goto("chrome://extensions")
                manage.wait_for_timeout(1500)
                manage.screenshot(path=str(shots / "chrome-uzantilar.png"))
                manage.close()
            popup.close()
            pages_before = len(context.pages)
            session = bridge.open("127.0.0.1", purpose="uçtan uca deneme")
            normal = session.page(f"{base}/normal", {"saniye": 1})
            drawn = session.page(f"{base}/js", {"oge": "#icerik"})
            cleared = session.page(f"{base}/dogrulama", {"saniye": 1})
            stuck = session.page(f"{base}/dogrulama-kalici", {"saniye": 1})
            login = session.page(f"{base}/giris")
            status, final, headers, body = session.request("GET", f"{base}/api/veri")
            session.close()
            assert normal["durum"] == "tamam" and "Normal içerik" in normal["html"].decode("utf-8") and normal["baslik"] == "Normal sayfa"
            assert normal["http_durumu"] == 200 and normal["yontem"] == "eklenti"
            assert drawn["durum"] == "tamam" and "JavaScript ile çizildi" in drawn["html"].decode("utf-8")
            assert cleared["durum"] == "tamam" and "Doğrulama sonrası içerik" in cleared["html"].decode("utf-8")
            assert stuck["durum"] == "dogrulama" and "atlandı" in (stuck["not"] or "")
            assert login["durum"] == "giris" and login["html"] is None
            assert (status, body) == (200, b'{"ok": true, "kaynak": "yerel"}') and "application/json" in headers.get("content-type", "")
            assert user.url == f"{base}/normal"                                         # the user's tab was not touched
            deadline = time.monotonic() + 10
            while len(context.pages) > pages_before and time.monotonic() < deadline:   # the extension closed its own window
                time.sleep(0.2)
            assert len(context.pages) == pages_before
        finally:
            context.close()
            site.shutdown()
