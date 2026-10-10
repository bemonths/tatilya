"""The computer's own browser for collectors: sites that show a human-verification page, protected sites and menus drawn by
JavaScript.

The installed Chrome (or Edge) is started as an ordinary application with one persistent profile for every site (default
work/tarayici-profili/30a-studio, outside the repository) and a remote-debugging port open on 127.0.0.1 only; the code connects to it
over CDP (Playwright connect_over_cdp). It is never launched by Playwright: no --enable-automation flag, no Playwright launch
defaults, no downloaded Chromium; user agent, language, time zone and window size are the browser's and the computer's own. A browser
already running with the profile is reused, never opened twice. Cookies and completed verifications stay in the profile between runs.

When a verification page is on screen the code waits a short grace period (most clear by themselves) and otherwise leaves that site
for the end of the run; at the end the waiting sites are opened in tabs, the job lists them once and the user completes them in the
window (the code never interacts with the check and never disguises the browser). A block page (the site refusing the visitor) stops
that site at once. Requests to a verified or protected site run inside its page with the browser's own fetch.

Hosts that once showed a verification page are kept in browser_hosts ("read with the browser"): later runs go to them through the
browser only, and a warm-up opens them all in tabs before a long run (python -m studio.sources.browser_verification isinma).
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

# The interstitial only (its title, its options object or its page script); a Turnstile box in a form is not one.
CHALLENGE = re.compile(r"<title>\s*Just a moment\.\.\.|cf_chl_opt|/cdn-cgi/challenge-platform/h/[a-z]/orchestrate/|Checking your browser before|"
                       r"Checking if the site connection is secure|px-captcha|Press &amp; Hold|Press & Hold", re.I)
BLOCKED = re.compile(r"Sorry, you have been blocked|You are unable to access", re.I)
FETCH = """async ({url, method, headers, body}) => {
    const response = await fetch(url, {method, headers, body: body === null ? undefined : body, credentials: 'include', redirect: 'follow'});
    const bytes = new Uint8Array(await response.arrayBuffer());
    let binary = '';
    for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return {status: response.status, url: response.url, headers: Object.fromEntries(response.headers.entries()), body: btoa(binary)};
}"""
SKIPPED_HEADERS = ("user-agent", "referer", "origin", "accept-language", "cookie", "host")    # the browser sets its own
PROFILE_NAME = "30a-studio"
GRACE_SECONDS = 20              # a verification page that clears by itself within this time is not left for the end
FINAL_WAIT_SECONDS = 15 * 60    # the one wait at the end of a run for the sites left for the user
START_SECONDS = 30
BROWSERS = (
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    Path("/usr/bin/google-chrome"), Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
)


class SiteBlocked(Exception):
    """The site shows a block page (not a verification page): requests to it stop."""


class BrowserUnavailable(Exception):
    """No installed Chrome/Edge, no Playwright, or the browser did not open its debugging port."""


def available():
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return find_browser() is not None


def profile_root():
    configured = os.environ.get("STUDIO_BROWSER_PROFILE")
    return Path(configured) if configured else Path(__file__).resolve().parents[2] / "work" / "tarayici-profili" / PROFILE_NAME


def find_browser():
    configured = os.environ.get("STUDIO_BROWSER_PATH")
    for candidate in ([Path(configured)] if configured else []) + list(BROWSERS):
        if str(candidate) not in ("", ".") and candidate.is_file():
            return candidate
    return None


def launch_command(executable, profile):
    """The browser started like an ordinary application: its own profile folder and a debugging port the browser picks on 127.0.0.1.
    Nothing else: no automation flag and none of Playwright's launch defaults."""
    return [str(executable), f"--user-data-dir={Path(profile)}", "--remote-debugging-port=0"]


def probe(endpoint):
    import httpx
    try:
        return httpx.get(f"{endpoint}/json/version", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def running_endpoint(profile, check=probe):
    """The debugging endpoint of a browser already running with this profile (Chrome writes its port to DevToolsActivePort)."""
    marker = Path(profile) / "DevToolsActivePort"
    try:
        port = int(marker.read_text(encoding="utf-8").splitlines()[0].strip())
    except (OSError, ValueError, IndexError):
        return None
    endpoint = f"http://127.0.0.1:{port}"
    return endpoint if check(endpoint) else None


def ensure_browser(profile=None, *, spawn=None, check=probe, wait=START_SECONDS):
    """(endpoint, launched): reuse the browser running with the profile, or start the installed one detached from this process."""
    profile = Path(profile) if profile else profile_root()
    profile.mkdir(parents=True, exist_ok=True)
    endpoint = running_endpoint(profile, check)
    if endpoint:
        return endpoint, False
    executable = find_browser()
    if executable is None and spawn is None:
        raise BrowserUnavailable("Bu bilgisayarda Chrome ya da Edge bulunamadı.")
    marker = profile / "DevToolsActivePort"
    try:
        marker.unlink()                       # a stale port file from a browser that is no longer running
    except OSError:
        pass
    command = launch_command(executable or "chrome", profile)
    if spawn is not None:
        spawn(command)
    else:
        flags = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if sys.platform == "win32" else 0
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
                         creationflags=flags, start_new_session=sys.platform != "win32")
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        endpoint = running_endpoint(profile, check)
        if endpoint:
            return endpoint, True
        time.sleep(0.5)
    raise BrowserUnavailable("Tarayıcı açıldı ama hata ayıklama bağlantı noktası açılmadı (aynı profil hata ayıklamasız açık olabilir).")


class ChromeSession:
    """One CDP connection (per thread) to the running browser; pages opened here are closed on close(), the browser stays open."""

    def __init__(self, profile=None):
        from playwright.sync_api import sync_playwright
        if find_browser() is None and not os.environ.get("STUDIO_BROWSER_PATH"):
            raise BrowserUnavailable("Bu bilgisayarda Chrome ya da Edge bulunamadı.")
        endpoint, _ = ensure_browser(profile)
        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.connect_over_cdp(endpoint)
        except Exception:
            self.playwright.stop()
            raise
        self.context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
        self.pages = []

    def new_page(self):
        page = self.context.new_page()
        self.pages.append(page)
        return page

    def close(self):
        for page in self.pages:
            try:
                page.close()
            except Exception:
                pass                          # the window or tab may already be closed by the user
        self.pages = []
        try:
            self.playwright.stop()            # disconnects; the browser and its profile stay as they are
        except Exception:
            pass


def page_state(page):
    """'blocked', 'challenge' or 'open' for what the page shows now."""
    try:
        content = page.title() + page.content()[:30000]
    except Exception:
        return "challenge"                    # navigating (the check reloads the page): look again
    if BLOCKED.search(content):
        return "blocked"
    return "challenge" if CHALLENGE.search(content) else "open"


def watch(page, seconds, canceled):
    """Look at the page every 2 s for at most `seconds`; returns its last state."""
    deadline = time.monotonic() + seconds
    while True:
        if canceled():
            raise_canceled()
        state = page_state(page)
        if state != "challenge" or time.monotonic() >= deadline:
            return state
        time.sleep(2)


def wait_for_user(pages, canceled, timeout, waiting=None, sleep=time.sleep):
    """The end-of-run wait: pages {host: page} already open in tabs; the job lists the hosts once; returns the hosts whose page
    opened normally within `timeout` (blocked or still verifying hosts are left out)."""
    pending, cleared = dict(pages), set()
    if waiting and pending:
        waiting(", ".join(sorted(pending)))
    deadline = time.monotonic() + timeout
    try:
        while pending:
            if canceled():
                raise_canceled()
            for host, page in list(pending.items()):
                state = page_state(page)
                if state != "challenge":
                    pending.pop(host)
                    if state == "open":
                        cleared.add(host)
            if not pending or time.monotonic() >= deadline:
                break
            sleep(3)
    finally:
        if waiting and pages:
            waiting(None)
    return cleared


class BrowserTransport:
    """Requests from inside the opened page with the browser's fetch (same origin as the page; redirects followed by the browser)."""

    kind = "browser"

    def __init__(self, session, page):
        self.session, self.page = session, page

    def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
        import httpx
        if params:
            url = str(httpx.URL(url, params=params))
        headers = {k: v for k, v in (headers or {}).items() if k.lower() not in SKIPPED_HEADERS}
        body = None
        if data is not None:
            body = urlencode(data)
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        elif json_body is not None:
            body = json.dumps(json_body)
            headers.setdefault("Content-Type", "application/json")
        try:
            answer = self.page.evaluate(FETCH, {"url": url, "method": method, "headers": headers, "body": body})
        except Exception as exc:          # a browser-side network failure is recorded like a plain HTTP one
            raise httpx.NetworkError(str(exc)[:200]) from exc
        return answer["status"], answer["url"] or url, answer["headers"], base64.b64decode(answer["body"])

    def close(self):
        self.session.close()


class BrowserVerifier:
    """verifier(domain, url, canceled, timeout) -> BrowserTransport, or None while a verification page is still on screen after
    `timeout` seconds; raises SiteBlocked on a block page. wait_all() is the one end-of-run wait for the sites left for the user."""

    def __init__(self, profile=None, session_factory=None):
        self.profile = profile
        self.session_factory = session_factory or (lambda: ChromeSession(self.profile))

    def __call__(self, domain, url, canceled, timeout):
        return self.open(domain, url, canceled, timeout, None)

    def open(self, domain, url, canceled, timeout, waiting=None):
        session = self.session_factory()
        try:
            page = session.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            state = watch(page, timeout, canceled)
            if state == "blocked":
                raise SiteBlocked(f"{domain}: {page.title()[:80]}")
            if state == "open":
                return BrowserTransport(session, page)
            session.close()
            return None
        except BaseException:
            session.close()
            raise

    def wait_all(self, sites, canceled, timeout, waiting=None):
        """sites: {domain: url}. Opens each in its own tab, lists them once and waits; returns the domains that opened normally."""
        session = self.session_factory()
        try:
            pages = {}
            for domain, url in sites.items():
                page = session.new_page()
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                except Exception:
                    pass
                pages[domain] = page
            return wait_for_user(pages, canceled, timeout, waiting)
        finally:
            session.close()


def raise_canceled():
    from .base import CollectionCanceled
    raise CollectionCanceled()


# --- "read with the browser" hosts --------------------------------------------------------------------------------------------

def host_key(url_or_host):
    host = (urlsplit(url_or_host).hostname if "//" in (url_or_host or "") else url_or_host) or ""
    host = host.lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def mark_hosts(con, hosts, connector):
    """Remember hosts that showed a verification page: [{'host', 'url', 'reason'}]. Kept across runs (first and last seen)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for item in hosts:
        host = host_key(item["host"])
        if not host:
            continue
        con.execute("""INSERT INTO browser_hosts (host,url,reason,marked_by,first_seen_at,last_seen_at) VALUES (?,?,?,?,?,?)
            ON CONFLICT(host) DO UPDATE SET url=excluded.url, reason=excluded.reason, last_seen_at=excluded.last_seen_at""",
                    (host, item.get("url"), item.get("reason") or "doğrulama sayfası", connector, now, now))


def record_methods(con, methods):
    """GÖREV-14: which way of reading worked for a host that refused direct requests ({host: 'eklenti' | 'tarayici' | 'dogrudan'});
    only hosts already in browser_hosts are updated."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for host, method in (methods or {}).items():
        if method in ("eklenti", "tarayici", "dogrudan"):
            con.execute("UPDATE browser_hosts SET method=?, method_at=? WHERE host=?", (method, now, host_key(host)))


def warm_up(entries, profile=None, canceled=lambda: False, session_factory=None):
    """Open every 'read with the browser' site in its own tab of the profile's browser (left open for the user); returns
    [(host, url, state)] with state 'açık', 'doğrulama bekliyor' or 'engel sayfası'."""
    session = (session_factory or (lambda: ChromeSession(profile)))()
    results, waiting = [], []
    for host, url in entries:
        page = session.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            state = watch(page, 8, canceled)
        except Exception as exc:
            state = f"açılamadı ({type(exc).__name__})"
        if state == "challenge":
            waiting.append(page)
        results.append((host, url, {"open": "açık", "challenge": "doğrulama bekliyor", "blocked": "engel sayfası"}.get(state, state)))
    session.pages = [p for p in session.pages if p not in waiting]     # only the tabs waiting for the user stay open
    session.close()
    return results


def warm_up_entries(database):
    """Hosts to open before a long run: browser_hosts and the configured protected rental sites of the database (read-only)."""
    import sqlite3
    con = sqlite3.connect(f"{Path(database).resolve().as_uri()}?mode=ro&immutable=1", uri=True)
    try:
        rows = con.execute("SELECT host, COALESCE(url, 'https://' || host || '/') FROM browser_hosts ORDER BY host").fetchall()
        protected = con.execute("SELECT domain FROM destination_agency_sites WHERE enabled=1 AND protected=1 ORDER BY domain").fetchall()
    finally:
        con.close()
    entries = dict(rows)
    for (domain,) in protected:
        entries.setdefault(domain, f"https://www.{domain}/")
    return sorted(entries.items())


def main(argv=None):
    """python -m studio.sources.browser_verification isinma [<veritabanı>] | ac <url> ..."""
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv.pop(0) if argv else "isinma"
    if command == "isinma":
        database = Path(argv[0]) if argv else Path(__file__).resolve().parents[2] / "data" / "studio.sqlite3"
        entries = warm_up_entries(database)
    elif command == "ac":
        entries = [(host_key(url), url) for url in argv]
    else:
        print(main.__doc__)
        return 2
    for host, url, state in warm_up(entries):
        print(f"{host}\t{state}\t{url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
