"""Reading a region-blocked site through the user's US proxy (GÖREV-16, Adım 3c; studio/proxy.py).

Reading order for a domain on the region-blocked list (`region_blocked_hosts`):
1. a direct request through the proxy (httpx);
2. when that is refused (verification, refusal, region block, an error status) or the page is drawn by JavaScript, the program's own
   browser through the proxy;
3. otherwise the page is skipped and written down: "bölge engeli: proxy'yle de okunamadı".
Without a proxy the page is skipped at once: "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)". The extension is never used for these
domains (the user's own connection cannot read them). Pacing as everywhere: at least 8 s between two pages of a site, one page at a time.
A verification page shown through the proxy is passed by the user in the browser window (at most 15 minutes).

The program's own browser for the proxy is a separate Chrome process with its own profile (`<profile root>-proxy`, outside the
repository) started with a PAC script that sends only the listed domains through the proxy (every other address goes DIRECT). The proxy
address is on the command line inside the PAC data address; the user name and password never are: they are answered to the proxy's
question over CDP `Fetch` in the program's own tab (Housing Atlas `ProxyAuth`; a second question for the same request is cancelled so a
wrong password cannot loop). When the list or the proxy changes, a browser started with the old PAC script is closed and started again.

Raw copies carry `yontem` "proxy" or "tarayici+proxy" and `proxy: true`; never the proxy's address.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

from .. import proxy as P
from . import browser_verification as bv
from . import page_kinds

GAP_S = 8.0
VERIFY_WAIT_S = 15 * 60
SCRIPT_DRAWN_TEXT = 300           # a 200 page with less visible text than this and with scripts is drawn by JavaScript
PAC_MARKER = "30a-proxy-pac.json"
FETCH_PATTERNS = [{"urlPattern": "*", "requestStage": "Request"}]


def proxy_profile_root():
    configured = os.environ.get("STUDIO_PROXY_BROWSER_PROFILE")
    return Path(configured) if configured else bv.profile_root().with_name(bv.PROFILE_NAME + "-proxy")


def looks_script_drawn(page_html):
    text = page_kinds.visible_text(page_html)
    return len(text) < SCRIPT_DRAWN_TEXT and "<script" in str(page_html or "").lower()


def title_of(page_html):
    import re
    match = re.search(r"<title[^>]*>(.*?)</title>", str(page_html or "")[:20000], re.I | re.S)
    return page_kinds.visible_text(match.group(1)) if match else ""


def launch_command(executable, profile, pac):
    """The proxy browser: its own profile, a debugging port on 127.0.0.1 and the PAC script. No credentials, nothing else."""
    return [str(executable), f"--user-data-dir={Path(profile)}", "--remote-debugging-port=0", f"--proxy-pac-url={P.pac_url(pac)}"]


def pac_digest(pac):
    return hashlib.sha256(pac.encode("utf-8")).hexdigest()


def auth_answer(event, username, password, asked):
    """`Fetch.authRequired` → `Fetch.continueWithAuth` parameters (Housing Atlas `_auth_answer`): the proxy's question gets the
    credentials once per request; a second question for the same request is cancelled; a site's own question is left to Chrome."""
    if not isinstance(event, dict) or not event.get("requestId"):
        return None
    request_id = event["requestId"]
    challenge = event.get("authChallenge") if isinstance(event.get("authChallenge"), dict) else {}
    if challenge.get("source") != "Proxy":
        response = {"response": "Default"}
    elif request_id in asked:
        response = {"response": "CancelAuth"}
    else:
        asked.add(request_id)
        response = {"response": "ProvideCredentials", "username": username, "password": password}
    return {"requestId": request_id, "authChallengeResponse": response}


class ProxyAuth:
    """Answers the proxy's credential question in one tab over CDP `Fetch`; every paused request is continued."""

    def __init__(self, session, username, password):
        self.session, self.credentials, self.asked = session, (username, password), set()
        session.on("Fetch.requestPaused", self.paused)
        session.on("Fetch.authRequired", self.auth)
        session.send("Fetch.enable", {"handleAuthRequests": True, "patterns": FETCH_PATTERNS})

    def __repr__(self):
        return "ProxyAuth(***)"

    def paused(self, event):
        if isinstance(event, dict) and event.get("requestId"):
            self.send("Fetch.continueRequest", {"requestId": event["requestId"]})

    def auth(self, event):
        answer = auth_answer(event, *self.credentials, self.asked)
        if answer is not None:
            self.send("Fetch.continueWithAuth", answer)

    def send(self, method, params):
        try:
            self.session.send(method, params)
        except Exception:
            pass                              # the request was cancelled or the tab closed


class ProxyBrowser:
    """One tab of the proxy browser (see the module): page(url, canceled, waiting) -> (status, final url, title, html bytes)."""

    def __init__(self, proxy, hosts, *, profile=None, spawn=None, check=bv.probe, connect=None):
        self.proxy, self.hosts, self.pac = proxy, sorted({P.host_key(h) for h in hosts}), P.pac_script(proxy, hosts)
        self.profile = Path(profile) if profile else proxy_profile_root()
        self.spawn, self.check, self.connect = spawn, check, connect
        self.playwright = self.browser = self.page = self.auth = None

    def endpoint(self):
        self.profile.mkdir(parents=True, exist_ok=True)
        marker = self.profile / PAC_MARKER
        digest = pac_digest(self.pac)
        running = bv.running_endpoint(self.profile, self.check)
        try:
            known = json.loads(marker.read_text(encoding="utf-8")).get("pac_sha256")
        except (OSError, ValueError, AttributeError):
            known = None
        if running and known == digest:
            return running
        if running:
            self.close_running(running)
        executable = bv.find_browser()
        if executable is None and self.spawn is None:
            raise bv.BrowserUnavailable("Bu bilgisayarda Chrome ya da Edge bulunamadı.")
        (self.profile / "DevToolsActivePort").unlink(missing_ok=True)
        command = launch_command(executable or "chrome", self.profile, self.pac)
        if self.spawn is not None:
            self.spawn(command)
        else:
            flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if sys.platform == "win32" else 0
            subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
                             creationflags=flags, start_new_session=sys.platform != "win32")
        marker.write_text(json.dumps({"pac_sha256": digest}), encoding="utf-8")
        deadline = time.monotonic() + bv.START_SECONDS
        while time.monotonic() < deadline:
            endpoint = bv.running_endpoint(self.profile, self.check)
            if endpoint:
                return endpoint
            time.sleep(0.5)
        raise bv.BrowserUnavailable("Proxy tarayıcısı açıldı ama hata ayıklama bağlantı noktası açılmadı.")

    def close_running(self, endpoint):
        """A proxy browser started with another PAC script (the list or the proxy changed): closed before a new start."""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(endpoint)
                browser.new_browser_cdp_session().send("Browser.close")
        except Exception:
            pass
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and bv.running_endpoint(self.profile, self.check):
            time.sleep(0.5)

    def start(self):
        if self.page is not None:
            return self.page
        if self.connect is not None:
            self.page = self.connect(self)
            return self.page
        from playwright.sync_api import sync_playwright
        endpoint = self.endpoint()
        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.connect_over_cdp(endpoint)
            context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
            self.page = context.new_page()
            if self.proxy.user and self.proxy.password:
                self.auth = ProxyAuth(context.new_cdp_session(self.page), self.proxy.user, self.proxy.password)
        except Exception:
            self.close()
            raise
        return self.page

    def page_read(self, url, canceled=lambda: False, waiting=None, wait_s=VERIFY_WAIT_S):
        page = self.start()
        response = page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        try:
            page.wait_for_load_state("networkidle", timeout=5_000)
        except Exception:
            pass
        status = response.status if response is not None else None
        kind = page_kinds.classify(page.content(), page.title(), page.url, status)
        if kind == "dogrulama":
            if waiting:
                waiting(bv.host_key(url))
            deadline = time.monotonic() + wait_s
            try:
                while kind == "dogrulama" and time.monotonic() < deadline:
                    if canceled():
                        bv.raise_canceled()
                    page.wait_for_timeout(2000)          # Playwright handles the CDP events (the proxy's question) while it waits
                    kind = page_kinds.classify(page.content(), page.title(), page.url, None)
            finally:
                if waiting:
                    waiting(None)
            if kind == "tamam":
                status = 200
        return status, page.url, page.title(), page.content().encode("utf-8"), kind

    def close(self):
        try:
            if self.page is not None and self.connect is None:
                self.page.close()
        except Exception:
            pass
        self.page = self.auth = None
        try:
            if self.playwright is not None:
                self.playwright.stop()
        except Exception:
            pass
        self.playwright = self.browser = None


class ProxyChromeSession:
    """The ChromeSession interface (new_page, close) on the proxy browser, for the rental collector's verifier: every page of it
    answers the proxy's credential question over CDP Fetch."""

    def __init__(self, proxy, hosts, profile=None):
        from playwright.sync_api import sync_playwright
        self.proxy = proxy
        endpoint = ProxyBrowser(proxy, hosts, profile=profile).endpoint()
        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.connect_over_cdp(endpoint)
        except Exception:
            self.playwright.stop()
            raise
        self.context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
        self.pages, self.auths = [], []

    def new_page(self):
        page = self.context.new_page()
        self.pages.append(page)
        if self.proxy.user and self.proxy.password:
            self.auths.append(ProxyAuth(self.context.new_cdp_session(page), self.proxy.user, self.proxy.password))
        return page

    def close(self):
        for page in self.pages:
            try:
                page.close()
            except Exception:
                pass
        self.pages, self.auths = [], []
        try:
            self.playwright.stop()
        except Exception:
            pass


def proxy_verifier(proxy, hosts):
    """A BrowserVerifier on the proxy browser (its transports say "tarayici+proxy")."""
    inner = bv.BrowserVerifier(session_factory=lambda: ProxyChromeSession(proxy, hosts))

    def verify(domain, url, canceled, timeout):
        transport = inner(domain, url, canceled, timeout)
        if transport is not None:
            transport.kind = "tarayici+proxy"
        return transport
    verify.wait_all = inner.wait_all
    return verify


class RegionReader:
    """read(url) for a region-blocked domain (see the module). `client` is a client that goes through the proxy (tests give one with a
    mock transport); `browser_factory()` gives a ProxyBrowser-like object."""

    def __init__(self, proxy, hosts, *, client=None, browser_factory=None, canceled=lambda: False, waiting=None, sleep=time.sleep,
                 clock=time.monotonic, gap=GAP_S):
        self.proxy, self.hosts = proxy, list(hosts)
        self.client, self.browser_factory = client, browser_factory
        self.canceled, self.waiting, self.sleep, self.clock, self.gap = canceled, waiting, sleep, clock, gap
        self.browser = None
        self.last = {}

    def pace(self, url):
        host = P.host_key(url)
        if host in self.last:
            remaining = self.gap - (self.clock() - self.last[host])
            if remaining > 0:
                self.sleep(remaining)
        self.last[host] = self.clock()

    def skipped(self, url, note):
        return {"durum": "bolge_engeli", "adres": url, "son_adres": url, "baslik": "", "http_durumu": None, "html": None, "not": note,
                "yontem": None, "proxy": False, "tur": "bolge_engeli"}

    def read(self, url, *, needs_browser=False):
        if self.proxy is None:
            return self.skipped(url, P.NO_PROXY_SKIP)
        if self.proxy.missing_password:
            return self.skipped(url, f"{P.PROXY_FAILED_SKIP} ({P.NO_PASSWORD})")
        notes = []
        try:
            if self.client is None:
                self.client = self.proxy.client()
            self.pace(url)
            response = self.client.get(url)
            body = response.content
            content_type = response.headers.get("content-type") or ""
            if response.status_code < 400 and "html" not in content_type.lower() and content_type:
                return {"durum": "tamam", "adres": url, "son_adres": str(response.url), "baslik": "", "http_durumu": response.status_code,
                        "html": body, "content_type": content_type, "not": None, "yontem": "proxy", "proxy": True, "tur": "tamam"}
            text = body.decode(response.encoding or "utf-8", errors="replace")
            kind = page_kinds.classify(text, title_of(text), str(response.url), response.status_code)
            if kind == "tamam" and response.status_code < 400 and not needs_browser and not looks_script_drawn(text):
                return {"durum": "tamam", "adres": url, "son_adres": str(response.url), "baslik": title_of(text),
                        "http_durumu": response.status_code, "html": body, "content_type": content_type or "text/html; charset=utf-8",
                        "not": None, "yontem": "proxy", "proxy": True, "tur": "tamam"}
            notes.append(f"proxy'yle doğrudan istek: {page_kinds.LABELS.get(kind, kind)}, HTTP {response.status_code}"
                         + (", sayfa JavaScript'le çiziliyor" if kind == "tamam" and response.status_code < 400 else ""))
        except P.ProxyError as exc:
            notes.append(str(exc))
        except (httpx.HTTPError, OSError, ValueError) as exc:
            notes.append(self.proxy.sanitize(f"proxy'yle doğrudan istek: {P.describe(exc)}"))
        if self.proxy.browser_problem:
            return self.skipped(url, f"{P.PROXY_FAILED_SKIP} ({'; '.join(notes)}; programın tarayıcısı bu proxy'yle kullanılamıyor: "
                                     "kullanıcı adlı SOCKS5)")
        if self.browser_factory is None:
            return self.skipped(url, f"{P.PROXY_FAILED_SKIP} ({'; '.join(notes)}; bu bilgisayarda tarayıcı kullanılamıyor)")
        try:
            known = getattr(self.browser, "hosts", None)
            if self.browser is not None and known is not None and not P.is_listed(known, url):
                self.browser.close()              # a domain added during the run: the PAC script must name it too
                self.browser = None
            if self.browser is None:
                self.browser = self.browser_factory()
            self.pace(url)
            status, final, title, body, kind = self.browser.page_read(url, self.canceled, self.waiting)
        except Exception as exc:
            if type(exc).__name__ == "CollectionCanceled":
                raise
            notes.append(self.proxy.sanitize(f"programın tarayıcısı: {type(exc).__name__}: {str(exc)[:160]}"))
            return self.skipped(url, f"{P.PROXY_FAILED_SKIP} ({'; '.join(notes)})")
        if kind == "tamam":
            return {"durum": "tamam", "adres": url, "son_adres": final, "baslik": title, "http_durumu": status, "html": body, "not": None,
                    "yontem": "tarayici+proxy", "proxy": True, "tur": "tamam"}
        notes.append(f"programın tarayıcısı: {page_kinds.LABELS.get(kind, kind)}")
        return self.skipped(url, f"{P.PROXY_FAILED_SKIP} ({'; '.join(notes)})")

    def close(self):
        if self.browser is not None:
            self.browser.close()
            self.browser = None
        if self.client is not None:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None


class RegionAccess:
    """What a job gets: the region-blocked list (read when the job starts; a domain the job finds is added at once), the proxy (or
    None), httpx mounts for its own client (only the listed domains through the proxy) and a RegionReader."""

    def __init__(self, db, data_dir, *, proxy_loader=None, browser_factory=None):
        self.db, self.data_dir = db, Path(data_dir)
        with db.connect() as con:
            self.hosts = set(P.listed_hosts(con))
        try:
            self.proxy = (proxy_loader or P.load)(self.data_dir)
        except Exception:                      # Credential Manager unreadable: the proxy is not used
            self.proxy = None
        self.browser_factory = browser_factory if browser_factory is not None else self.default_browser_factory

    def default_browser_factory(self):
        if not bv.available():
            raise bv.BrowserUnavailable("Bu bilgisayarda Chrome/Edge ya da Playwright yok.")
        return ProxyBrowser(self.proxy, sorted(self.hosts))

    def listed(self, url_or_host):
        return P.is_listed(self.hosts, url_or_host)

    def mark(self, host, *, title=None, url=None, evidence=None):
        with self.db.connect() as con:
            if P.mark(con, host, title=title, url=url, evidence=evidence, added_by="program"):
                self.hosts.add(P.host_key(host))
                return True
        return False

    def mounts(self, **kwargs):
        if self.proxy is None or not self.hosts:
            return {}
        try:
            return self.proxy.mounts(self.hosts, **kwargs)
        except P.ProxyError:
            return {}

    def reader(self, canceled=lambda: False, waiting=None, **kwargs):
        factory = (lambda: self.browser_factory()) if self.proxy is not None else None
        return RegionReader(self.proxy, sorted(self.hosts), browser_factory=factory, canceled=canceled, waiting=waiting, **kwargs)
