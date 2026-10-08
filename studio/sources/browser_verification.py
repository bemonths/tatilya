"""Human verification in a visible browser for the agency rate collector.

When a company site answers with a verification page, the page is opened in the computer's Chrome (or Edge) with a persistent
profile in a visible window. The user completes the verification; this code only waits and never interacts with the check, and
no setting that hides browser automation is used. After the page opens normally, the same browser context keeps the site
session and its requests continue through it. Profiles live outside the repository (default work/tarayici-profili/<site>).
"""
import os
import re
import time
from pathlib import Path

CHALLENGE = re.compile(r"Just a moment\.\.\.|cf-chl-|/cdn-cgi/challenge-platform|Verify you are human|Checking your browser before|"
                       r"Checking if the site connection is secure|px-captcha|Press &amp; Hold|Press & Hold", re.I)
BLOCKED = re.compile(r"Sorry, you have been blocked|You are unable to access", re.I)


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
    """Requests through the verified browser context (same cookies and session as the visible window)."""

    kind = "browser"

    def __init__(self, playwright, context):
        self.playwright, self.context = playwright, context

    def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
        headers = {k: v for k, v in (headers or {}).items() if k.lower() != "user-agent"}    # the browser's own agent stays
        options = {"method": method, "params": params, "headers": headers, "max_redirects": 0, "timeout": 45_000}
        if data is not None:
            options["form"] = data
        elif json_body is not None:
            options["data"] = json_body
        try:
            response = self.context.request.fetch(url, **{k: v for k, v in options.items() if v is not None})
            return response.status, response.url, response.headers, response.body()
        except Exception as exc:          # browser-side network failures are retried like plain HTTP ones
            import httpx
            raise httpx.NetworkError(str(exc)[:200]) from exc

    def close(self):
        try:
            self.context.close()
        finally:
            self.playwright.stop()


class BrowserVerifier:
    """Called as verifier(domain, url, canceled, timeout) -> BrowserTransport, or None when the user did not complete it in time."""

    def __init__(self, root=None, channels=("chrome", "msedge")):
        self.root, self.channels = Path(root) if root else profile_root(), channels

    def __call__(self, domain, url, canceled, timeout):
        from playwright.sync_api import sync_playwright
        playwright = sync_playwright().start()
        context = None
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
                if not CHALLENGE.search(content) and not BLOCKED.search(content):
                    return BrowserTransport(playwright, context)
                if time.monotonic() > deadline:
                    break
                time.sleep(3)
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
