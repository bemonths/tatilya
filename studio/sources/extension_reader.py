"""Pages and in-page requests through the user's own Chrome, by the "30A Studio Yardımcısı" extension (GÖREV-14, Adım 7), for the
collectors' shared browser layer.

Reading order for a host that blocks direct requests (CLAUDE.md, browser rule): 1. the direct request (the collector's own first pass),
2. when it is blocked and the extension is paired, the extension, 3. when the job is handed over to the program (by the user, or after
the extension stayed away for 30 minutes), the program's own browser over CDP (studio.sources.browser_verification), 4. otherwise the
site is skipped and written down. `browser_hosts.method` keeps what worked for a host.

ExtensionPages has the interface of the restaurant collector's browser pages (goto, current, request, wait_all, close; CdpPages);
ExtensionVerifier and ExtensionTransport have the interface of the rental collector's verifier and in-page transport (BrowserVerifier,
BrowserTransport). The extension itself waits up to 15 minutes for the user on a verification page; a page still verifying after that is
skipped, so the end-of-run wait of these classes does not wait again for the extension's sites.
"""
import json
from urllib.parse import urlencode

import httpx

from ..extension import ExtensionError, HandedOver, domain_of
from .base import SourceError

STOPPED = {"giris": "Sayfa giriş istiyor (giriş gerekiyor); eklenti okumadı ve atladı.",
           "odeme": "Ödeme sayfası; eklenti okumadı ve atladı.",
           "izin_yok": "Eklentiye bu site için izin verilmedi; site atlandı."}
WAIT = {"saniye": 3}


def body_text(result):
    return (result.get("html") or b"")[:40000].decode("utf-8", errors="replace")


class ExtensionPages:
    """The browser pass of the restaurant collector through the extension; after a hand-over, the program's own browser."""

    def __init__(self, access, fallback=None, canceled=lambda: False, purpose="restoran siteleri"):
        self.access, self.fallback_factory, self.canceled, self.purpose = access, fallback, canceled, purpose
        self.session = self.domain = self.last = self.fallback = None
        self.methods = {}

    @property
    def method_note(self):
        return "tarayıcı" if self.fallback is not None else "eklenti"

    def use_fallback(self):
        if self.fallback is None:
            if self.fallback_factory is None:
                raise SourceError("İş programın kendi tarayıcısına devredildi ama bu bilgisayarda o tarayıcı kullanılamıyor.")
            self.fallback = self.fallback_factory()
        return self.fallback

    def session_for(self, url):
        domain = domain_of(url)
        if self.session is None or self.domain != domain:
            if self.session is not None:
                self.session.close()
            self.session, self.domain = self.access.open(domain, purpose=self.purpose), domain
        return self.session

    def goto(self, url):
        if self.fallback is not None:
            self.methods[domain_of(url)] = "tarayici"
            return self.fallback.goto(url)
        try:
            result = self.session_for(url).page(url, WAIT, canceled=self.canceled)
        except HandedOver:
            self.methods[domain_of(url)] = "tarayici"
            return self.use_fallback().goto(url)
        except ExtensionError as exc:
            raise httpx.NetworkError(str(exc)[:200]) from exc
        state = result["durum"]
        if state in STOPPED:
            raise SourceError(STOPPED[state])
        if state == "hata":
            raise httpx.NetworkError(result.get("not") or "Eklenti sayfayı okuyamadı.")
        status = 403 if state == "dogrulama" else int(result.get("http_durumu") or 200)
        if state == "tamam":
            self.methods[domain_of(url)] = "eklenti"
        self.last = (status, result.get("son_adres") or url, "text/html; charset=utf-8", result.get("html") or b"")
        return self.last

    def current(self):
        return self.fallback.current() if self.fallback is not None else self.last

    def request(self, url):
        """A document (PDF, image) with the page's own fetch from the extension's tab on that site."""
        if self.fallback is not None:
            return self.fallback.request(url)
        try:
            status, final, headers, body = self.session_for(url).request("GET", url, canceled=self.canceled)
        except HandedOver:
            return self.use_fallback().request(url)
        except ExtensionError as exc:
            raise httpx.NetworkError(str(exc)[:200]) from exc
        return status, final, {k.lower(): v for k, v in (headers or {}).items()}.get("content-type"), body

    def wait_all(self, sites, canceled, timeout, waiting):
        """The extension already waited for the user on each verification page: those sites are skipped. After a hand-over, the
        program's own browser makes its usual end-of-run wait."""
        if self.fallback is not None:
            return self.fallback.wait_all(sites, canceled, timeout, waiting)
        return set()

    def close(self):
        if self.session is not None:
            self.session.close()
        if self.fallback is not None:
            self.fallback.close()


class ExtensionTransport:
    """Requests made with the page's own fetch inside the extension's tab on the company's site (same origin as the page)."""

    kind = "eklenti"

    def __init__(self, session, canceled=lambda: False):
        self.session, self.canceled = session, canceled

    def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
        if params:
            url = str(httpx.URL(url, params=params))
        headers = {k: v for k, v in (headers or {}).items() if k.lower() not in ("user-agent", "referer", "origin", "accept-language", "cookie", "host")}
        body = None
        if data is not None:
            body = urlencode(data)
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        elif json_body is not None:
            body = json.dumps(json_body)
            headers.setdefault("Content-Type", "application/json")
        try:
            return self.session.request(method, url, headers=headers, body=body, canceled=self.canceled)
        except ExtensionError as exc:
            raise httpx.NetworkError(str(exc)[:200]) from exc

    def close(self):
        self.session.close()


class ExtensionVerifier:
    """The rental collector's verifier through the extension: (domain, url, canceled, timeout) -> transport, or None when the page still
    verifies after the extension's wait; raises SiteBlocked on a block page or a login page. After a hand-over the program's own
    browser's verifier (fallback) takes the rest."""

    def __init__(self, access, fallback=None, blocked_pattern=None):
        self.access, self.fallback = access, fallback
        self.blocked_pattern = blocked_pattern
        self.handed = False
        self.methods = {}

    def __call__(self, domain, url, canceled, timeout):
        from .browser_verification import BLOCKED, SiteBlocked
        if self.handed:
            return self.through_fallback(domain, url, canceled, timeout)
        session = None
        try:
            session = self.access.open(domain, purpose="kiralama şirketi")
            result = session.page(url, WAIT, canceled=canceled)
        except HandedOver:
            self.handed = True
            return self.through_fallback(domain, url, canceled, timeout)
        except ExtensionError:
            if session is not None:
                session.close()
            return None
        state = result["durum"]
        if state == "tamam":
            if (self.blocked_pattern or BLOCKED).search(body_text(result)):
                session.close()
                raise SiteBlocked(f"{domain}: {result.get('baslik') or 'engel sayfası'}")
            self.methods[domain_of(domain)] = "eklenti"
            return ExtensionTransport(session, canceled)
        session.close()
        if state in ("giris", "odeme"):
            raise SiteBlocked(f"{domain}: {STOPPED[state]}")
        return None

    def through_fallback(self, domain, url, canceled, timeout):
        if self.fallback is None:
            return None
        transport = self.fallback(domain, url, canceled, timeout)
        if transport is not None:
            self.methods[domain_of(domain)] = "tarayici"
        return transport

    def wait_all(self, sites, canceled, timeout, waiting=None):
        if self.handed and self.fallback is not None and hasattr(self.fallback, "wait_all"):
            return self.fallback.wait_all(sites, canceled, timeout, waiting)
        return set()
