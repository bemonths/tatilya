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
    # GÖREV-16: pages nobody passes and a region block are not waited for
    "/erisim": ("<HTML><HEAD><TITLE>Access Denied</TITLE></HEAD><BODY><H1>Access Denied</H1>You don't have permission to access "
                "this server.</BODY></HTML>"),
    "/bolge": ("<html><body><p>Example.com is not available to customers who are located outside of the United States.</p></body></html>"),
}
REDIRECTS = {"/yonlen": "http://baska-site.test/giris", "/yonlen-geo": "http://geo-blocked-site.test/"}


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def trial_site():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in REDIRECTS:
                self.send_response(302)
                self.send_header("Location", REDIRECTS[self.path])
                self.end_headers()
                return
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
            worker = next((w for w in context.service_workers if w.url.endswith("/background.js")), None)
            while worker is None:                    # Chromium's own service workers may come first (GÖREV-16)
                found = context.wait_for_event("serviceworker", timeout=20000)
                worker = found if found.url.endswith("/background.js") else None
            extension_id = worker.url.split("/")[2]
            user = context.pages[0] if context.pages else context.new_page()
            user.goto(f"{base}/normal")
            popup = context.new_page()
            popup.goto(f"chrome-extension://{extension_id}/popup.html")
            popup.evaluate(f"chrome.storage.local.set({{port: {port}}})")     # an extension page has the extension's APIs
            popup.fill("#kod", bridge.code())
            popup.click("button[type=submit]")
            deadline = time.monotonic() + 20                # the popup forbids eval: the pairing is waited for from here
            while not (popup.locator("#eslesme-sonuc").text_content() or "").startswith("Eşleşti"):
                assert time.monotonic() < deadline, popup.locator("#eslesme-sonuc").text_content()
                popup.wait_for_timeout(300)
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
            started = time.monotonic()
            denied = session.page(f"{base}/erisim", {"saniye": 1})
            region = session.page(f"{base}/bolge", {"saniye": 1})
            elsewhere = session.page(f"{base}/yonlen", {"saniye": 1})
            geo = session.page(f"{base}/yonlen-geo", {"saniye": 1})
            quick = time.monotonic() - started
            status, final, headers, body = session.request("GET", f"{base}/api/veri")
            session.close()
            assert normal["durum"] == "tamam" and "Normal içerik" in normal["html"].decode("utf-8") and normal["baslik"] == "Normal sayfa"
            assert normal["http_durumu"] == 200 and normal["yontem"] == "eklenti"
            assert drawn["durum"] == "tamam" and "JavaScript ile çizildi" in drawn["html"].decode("utf-8")
            assert cleared["durum"] == "tamam" and "Doğrulama sonrası içerik" in cleared["html"].decode("utf-8")
            assert stuck["durum"] == "dogrulama" and "atlandı" in (stuck["not"] or "")
            assert login["durum"] == "giris" and login["html"] is None
            assert denied["durum"] == "erisim_reddedildi" and region["durum"] == "bolge_engeli" and b"outside" in region["html"]
            assert elsewhere["durum"] == "yonlendi" and elsewhere["not"] == "başka siteye yönlendi: baska-site.test"
            assert geo["durum"] == "bolge_engeli" and geo["not"] == "bölge engeli: geo-blocked-site.test adresine yönlendi"
            assert quick < 60                                                          # none of them was waited for (8 s apart at most)
            assert (status, body) == (200, b'{"ok": true, "kaynak": "yerel"}') and "application/json" in headers.get("content-type", "")
            assert user.url == f"{base}/normal"                                         # the user's tab was not touched
            deadline = time.monotonic() + 10
            while len(context.pages) > pages_before and time.monotonic() < deadline:   # the extension closed its own window
                time.sleep(0.2)
            assert len(context.pages) == pages_before
        finally:
            context.close()
            site.shutdown()

def extension_context(playwright, tmp_path):
    executable = os.environ.get("STUDIO_EKLENTI_CHROMIUM")
    browser = {"executable_path": executable} if executable else {"channel": "chromium"}
    return playwright.chromium.launch_persistent_context(str(tmp_path / "gecici-profil"), headless=True, **browser,
                                                         args=[f"--disable-extensions-except={EXTENSION}", f"--load-extension={EXTENSION}"],
                                                         viewport={"width": 1100, "height": 760})


def pair_extension(context, bridge, port):
    worker = next((w for w in context.service_workers if w.url.endswith("/background.js")), None)
    while worker is None:
        found = context.wait_for_event("serviceworker", timeout=20000)
        worker = found if found.url.endswith("/background.js") else None
    extension_id = worker.url.split("/")[2]
    popup = context.new_page()
    popup.goto(f"chrome-extension://{extension_id}/popup.html")
    popup.evaluate(f"chrome.storage.local.set({{port: {port}}})")
    popup.fill("#kod", bridge.code())
    popup.click("button[type=submit]")
    deadline = time.monotonic() + 20
    while not (popup.locator("#eslesme-sonuc").text_content() or "").startswith("Eşleşti"):
        assert time.monotonic() < deadline, popup.locator("#eslesme-sonuc").text_content()
        popup.wait_for_timeout(300)
    deadline = time.monotonic() + 20
    while not bridge.connected:
        assert time.monotonic() < deadline, "Eklenti programa bağlanmadı."
        time.sleep(0.2)
    return popup            # an extension page: chrome.windows can be asked from it


def window_ids(popup):
    return popup.evaluate("chrome.windows.getAll({populate: false}).then(all => all.map(w => w.id))")


def test_one_window_for_the_whole_job_and_it_closes_when_the_job_ends(program, tmp_path):
    """GÖREV-17: two sites of one job are read in the same window and tab (never one window per site); the window is opened without
    the focus, stays between the two sites and closes when the job is cancelled. Local pages only."""
    from playwright.sync_api import sync_playwright
    app, port = program
    bridge, db = app.state.extension, app.state.db
    site = trial_site()
    base = f"http://127.0.0.1:{site.server_address[1]}"
    other = base                                                    # the job's second "site": another session of the same job
    with sync_playwright() as playwright:
        context = extension_context(playwright, tmp_path)
        try:
            popup = pair_extension(context, bridge, port)
            before = set(window_ids(popup))
            job = db.add_job("eklenti_deneme", "Tek pencere denemesi")
            db.update_job(job, status="running", message="başladı")
            access = ext.JobAccess(bridge, db, job)
            seen, stop = set(), threading.Event()

            def watch():                                             # every window the extension has open during the job
                while not stop.is_set():
                    try:
                        seen.update(set(window_ids(popup)) - before)
                    except Exception:
                        pass
                    time.sleep(0.15)
            first = access.open("127.0.0.1", purpose="tek pencere")
            a = first.page(f"{base}/normal", {"saniye": 1})
            seen.update(set(window_ids(popup)) - before)
            first.close()
            time.sleep(4)                                            # between two sites: the extension asks again and keeps its window
            between = set(window_ids(popup)) - before
            second = access.open("127.0.0.1", purpose="tek pencere")
            b = second.page(f"{other}/js", {"oge": "#icerik"})
            seen.update(set(window_ids(popup)) - before)
            c = second.page(f"{other}/normal", {"saniye": 1})
            seen.update(set(window_ids(popup)) - before)
            second.close()
            assert a["durum"] == b["durum"] == c["durum"] == "tamam" and "JavaScript ile çizildi" in b["html"].decode("utf-8")
            assert len(seen) == 1 and between == seen                # one window for both sites, still open in between
            window = popup.evaluate(f"chrome.windows.get({next(iter(seen))}, {{populate: true}}).then(w => ({{tabs: w.tabs.length, state: w.state}}))")
            assert window == {"tabs": 1, "state": "normal"}          # one tab; not minimized
            assert db.job(job)["progress_info"]["asama"] in ("sıradaki sayfa bekleniyor", "127.0.0.1 · sayfa okunuyor")
            db.update_job(job, status="canceled", message="İş iptal edildi.")
            deadline = time.monotonic() + 15
            while set(window_ids(popup)) - before and time.monotonic() < deadline:
                time.sleep(0.2)
            assert not set(window_ids(popup)) - before                # the job ended: the window closed
            stop.set()
            _ = watch
        finally:
            context.close()
            site.shutdown()


def query_site(seen):
    """A local site that answers the page's own queries (POST) with what it got: method, content type and body."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"<!doctype html><html><head><title>Ev sayfasi</title></head><body><form id='pdpDatesForm'></form></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length)
            seen.append((self.command, self.path, self.headers.get("Content-Type"), self.headers.get("X-Requested-With"), body))
            answer = b"No" if b"checkin=01%2F01%2F2027" in body else b"<div class='pdp-quote-total'>ok</div>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(answer)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_the_extension_sends_only_allowed_queries_with_exactly_the_given_fields(program, tmp_path):
    """GÖREV-25: the page's own query from the extension's tab on the site: an allowed POST goes with exactly the given fields (the
    page's form encoding); a forbidden path, a query off the list and a plain request that is not a GET are refused by the extension
    itself (sent past the program's own check here), and nothing reaches the site for them. Local pages only."""
    from playwright.sync_api import sync_playwright
    app, port = program
    bridge = app.state.extension
    seen = []
    site = query_site(seen)
    base = f"http://127.0.0.1:{site.server_address[1]}"
    fields = ["checkin", "checkout", "propertyID", "roomTypeID", "propertyName", "hash"]
    bridge.queries = lambda: [{"alan_adi": "127.0.0.1", "yol": "/ajax/quote", "yontem": "POST", "alanlar": fields, "amac": "fiyat"}]
    with sync_playwright() as playwright:
        context = extension_context(playwright, tmp_path)
        try:
            pair_extension(context, bridge, port).close()
            session = bridge.open("127.0.0.1", purpose="sorgu denemesi")
            page = session.page(f"{base}/ev", {"saniye": 1})
            given = {"checkin": "01/09/2027", "checkout": "01/16/2027", "propertyID": "1806", "roomTypeID": "", "propertyName": "Sea & Vie", "hash": ""}
            priced = session.query("/ajax/quote", "POST", given)
            taken = session.query("/ajax/quote", "POST", {**given, "checkin": "01/01/2027"})
            with pytest.raises(ext.QueryRefused):
                session.query("/ajax/addToCart", "POST", {"x": "1"})                   # the program's own check
            raw = lambda **item: session.submit({"tur": "sorgu", "adres": base, "alan_adi": "127.0.0.1", **item}, lambda: False, 60)
            cart = raw(yol="/ajax/addToCart", yontem="POST", alanlar={"x": "1"})
            unlisted = raw(yol="/ajax/other", yontem="POST", alanlar={"x": "1"})
            extra = raw(yol="/ajax/quote", yontem="POST", alanlar={**given, "email": "a@b.c"})
            plain = session.submit({"tur": "istek", "yontem": "POST", "adres": f"{base}/ajax/quote", "basliklar": {}, "govde": "a=1"}, lambda: False, 60)
            session.close()
            assert page["durum"] == "tamam"
            assert priced["durum"] == "tamam" and priced["govde"] == b"<div class='pdp-quote-total'>ok</div>" and taken["govde"] == b"No"
            assert priced["sorgu"]["yontem"] == "POST" and priced["sorgu"]["alanlar"] == given and priced["sorgu"]["zaman"]
            assert len(seen) == 2                                                     # nothing else reached the site
            method, path, kind, xhr, body = seen[0]
            assert (method, path, xhr) == ("POST", "/ajax/quote", "XMLHttpRequest") and kind.startswith("application/x-www-form-urlencoded")
            assert body == b"checkin=01%2F09%2F2027&checkout=01%2F16%2F2027&propertyID=1806&roomTypeID=&propertyName=Sea+%26+Vie&hash="
            assert cart["durum"] == "reddedildi" and "yasak listede" in cart["not"]
            assert unlisted["durum"] == "reddedildi" and "izinli sorgu listesinde değil" in unlisted["not"]
            assert extra["durum"] == "reddedildi" and "alanları" in extra["not"]
            assert plain["durum"] == "reddedildi" and "yalnız GET" in plain["not"]
        finally:
            context.close()
            site.shutdown()
