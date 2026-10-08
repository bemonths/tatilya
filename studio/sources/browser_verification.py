"""Visible browser for the agency rate collector: human verification and protected sites.

A company site that answers with a verification page, or one configured as protected, is opened in the computer's Chrome (or
Edge) with a persistent profile in a visible window. When a verification page is on screen the job shows which site waits and
the user completes it; this code only waits and never interacts with the check, and no setting that hides browser automation is
used. A block page (the site refusing the visitor) stops that company at once. After the page opens normally, the company's
requests run inside that page with the browser's own fetch (same cookies, session and network stack as the visible window).
Profiles live outside the repository (default work/tarayici-profili/<site>).
"""
import base64
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlencode

CHALLENGE = re.compile(r"<title>\s*Just a moment\.\.\.|cf-chl-|cf_chl_opt|/cdn-cgi/challenge-platform/h/[a-z]/orchestrate|Verify you are human|Checking your browser before|"
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


class SiteBlocked(Exception):
    """The site shows a block page (not a verification page): requests to it stop."""


def available():
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


def profile_root():
    configured = os.environ.get("STUDIO_BROWSER_PROFILE")
    return Path(configured) if configured else Path(__file__).resolve().parents[2] / "work" / "tarayici-profili"


class BrowserTransport:
    """Requests from inside the opened page with the browser's fetch (same origin as the page; redirects followed by the browser)."""

    kind = "browser"

    def __init__(self, playwright, context, page):
        self.playwright, self.context, self.page = playwright, context, page

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
        try:
            self.context.close()
        finally:
            self.playwright.stop()


class BrowserVerifier:
    """verifier(domain, url, canceled, timeout) or .open(..., waiting) -> BrowserTransport, None when the user did not complete
    a verification in time; raises SiteBlocked on a block page."""

    def __init__(self, root=None, channels=("chrome", "msedge")):
        self.root, self.channels = Path(root) if root else profile_root(), channels

    def __call__(self, domain, url, canceled, timeout):
        return self.open(domain, url, canceled, timeout, None)

    def open(self, domain, url, canceled, timeout, waiting):
        from playwright.sync_api import sync_playwright
        playwright = sync_playwright().start()
        context, announced = None, False
        try:
            profile = self.root / domain
            profile.mkdir(parents=True, exist_ok=True)
            for channel in self.channels:
                try:
                    context = playwright.chromium.launch_persistent_context(str(profile), channel=channel, headless=False, no_viewport=True,
                                                                            locale="en-US")
                    break
                except Exception:
                    context = None
            if context is None:
                playwright.stop()
                return None
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            deadline = time.monotonic() + timeout
            while True:
                if canceled():
                    raise_canceled()
                content = page.title() + page.content()[:30000]
                if BLOCKED.search(content):
                    if announced and waiting:
                        waiting(None)
                    raise SiteBlocked(f"{domain}: {page.title()[:80]}")
                if not CHALLENGE.search(content):
                    if announced and waiting:
                        waiting(None)
                    return BrowserTransport(playwright, context, page)
                if not announced and waiting:
                    waiting(domain)
                    announced = True
                if time.monotonic() > deadline:
                    break
                time.sleep(3)
            if announced and waiting:
                waiting(None)
            context.close()
            playwright.stop()
            return None
        except BaseException:
            try:
                if context is not None:
                    context.close()
            finally:
                playwright.stop()
            raise


def raise_canceled():
    from .base import CollectionCanceled
    raise CollectionCanceled()
