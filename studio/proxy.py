"""The user's own US proxy, for region-blocked sites only (GÖREV-16, Adım 3; docs/M16-TARAYICI-EKLENTISI.md).

Some sites (CVS, Publix, HCA) serve only visitors inside the United States; from the user's connection in Türkiye they cannot be read,
by the program or by the extension. The user's decision (11 October 2026): their own US proxy is used for those sites. The manager's
limit: the proxy is used only for domains on the region-blocked list (`region_blocked_hosts`), never to get past bot protection, a rate
limit or a ban; no IP rotation; the pacing rules stay the same (8 s between two pages of a site, one page at a time); a verification
page shown through the proxy is still passed by the user.

Settings → "ABD proxy'si (bölge engeli için)": the address (scheme://host:port; http, https or socks5; checked with Housing Atlas's
`proxy_url_error`) and the user name are in `<data>/ayarlar.json` → `abd_proxy`; the password is in Windows Credential Manager
(`studio.credentials`, service `30AStudio`). The API says only whether a password is saved. Texts show the proxy as `scheme://host`.

- `ProxySettings.mounts(hosts)`: httpx mounts that send only those domains (and their subdomains) through the proxy; every other
  request of the same client goes directly.
- `pac_script(proxy, hosts)`: the program's own browser gets a PAC script that sends only those domains through the proxy (DIRECT for the
  rest); the credentials never go on the command line (they are answered over CDP `Fetch`, studio/sources/region_reader.py).
- Chrome does not support a SOCKS5 proxy with a user name and password (Housing Atlas note): with such a proxy the program's own browser
  cannot be used, only direct requests.
- `test(proxy)`: "Proxy'yi dene" — through the proxy to a public IP service; shows the exit address and its country, and warns when the
  country is not the US. No site of the list is opened.
"""
import base64
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

from . import credentials, logs
from .ai import settings as stored_settings

SECTION = "abd_proxy"
PASSWORD = "abd_proxy_parolasi"
PROXY_SCHEMES = ("http", "https", "socks5")
CHROME_SCHEMES = {"http": "PROXY", "https": "HTTPS", "socks5": "SOCKS5"}
IP_SERVICE = os.environ.get("STUDIO_IP_SERVICE") or "https://ipinfo.io/json"
TIMEOUT = httpx.Timeout(60.0, connect=20.0)
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
SOCKS_AUTH = ("Chrome, kullanıcı adı ve parola isteyen SOCKS5 proxy'yi desteklemiyor: programın kendi tarayıcısı bu proxy'yle "
              "kullanılamaz, yalnız doğrudan istekler kullanılabilir. Tarayıcı da kullanılsın isterseniz http:// ile başlayan bir proxy "
              "adresi girin ya da kullanıcı adını boş bırakın.")
NO_PASSWORD = "Proxy kullanıcı adı yazılmış ama parola kayıtlı değil. Parolayı kaydedin ya da kullanıcı adını silin."
NOT_US = "Proxy'nin çıkış adresi ABD'de görünmüyor"
NO_PROXY_SKIP = "bölge engeli: ABD proxy'si tanımlı değil (Ayarlar)"
PROXY_FAILED_SKIP = "bölge engeli: proxy'yle de okunamadı"
_COUNTRY = re.compile(r"^[A-Z]{2}$")
_IP = re.compile(r"^[0-9A-Fa-f:.]{3,45}$")


class ProxyError(Exception):
    """A Turkish message for the user; it never carries the password, the user name or the port."""


def proxy_url_error(address):
    """None when the address is usable, else the Turkish error (Housing Atlas `proxy_url_error`; schemes as its worker: http, https,
    socks5)."""
    malformed = "Adres http://sunucu:port, https://sunucu:port ya da socks5://sunucu:port biçiminde olmalı."
    try:
        parts = urlsplit((address or "").strip())
        port = parts.port
    except ValueError:
        return malformed
    if not parts.scheme or not parts.netloc:
        return malformed
    if parts.scheme.lower() not in PROXY_SCHEMES:
        return f"Desteklenmeyen şema: {parts.scheme} (http, https, socks5)."
    if "@" in parts.netloc:
        return "Kullanıcı adı ve parolayı adrese değil, ayrı kutulara yazın."
    if not parts.hostname:
        return "Adreste sunucu adı yok."
    if port is None:
        return "Adreste port yok (ör. http://sunucu:8080)."
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        return malformed
    return None


@dataclass(frozen=True)
class ProxySettings:
    """The proxy: address (`scheme://host:port`), user name and password (memory only; not in `repr`)."""

    url: str
    user: str = ""
    password: str | None = field(default=None, repr=False)

    def __post_init__(self):
        logs.register_secret(self.password)

    @property
    def parts(self):
        return urlsplit(self.url.strip())

    @property
    def scheme(self):
        return self.parts.scheme.lower()

    @property
    def host(self):
        return self.parts.hostname or ""

    @property
    def port(self):
        return self.parts.port

    @property
    def label(self):
        """`scheme://host` — what texts and logs show."""
        return logs.proxy_label(self.url)

    @property
    def is_socks(self):
        return self.scheme.startswith("socks")

    @property
    def browser_problem(self):
        """Why the program's own browser cannot use this proxy (SOCKS5 with a user name), else None."""
        return SOCKS_AUTH if self.is_socks and self.user else None

    @property
    def missing_password(self):
        return bool(self.user) and not self.password

    def sanitize(self, text):
        """The text without the proxy's port, user name and password (only `scheme://host` stays)."""
        if not text:
            return text
        address, parts = self.url.strip(), self.parts
        forms = {address, address.rstrip("/"), address + "/"}
        if parts.scheme and parts.netloc:
            forms |= {f"{parts.scheme}://{parts.netloc}", f"{self.scheme}://{parts.netloc}"}
        for form in sorted((f for f in forms if f), key=len, reverse=True):
            text = text.replace(form, self.label)
        if self.host and self.port is not None:
            text = text.replace(f"{self.host}:{self.port}", self.host)
        for secret in (self.password, self.user):
            if secret and len(secret) >= logs.MIN_SECRET_LENGTH:
                text = text.replace(secret, logs.MASK)
        return logs.mask(text)

    def httpx_proxy(self):
        auth = (self.user, self.password or "") if self.user else None
        return httpx.Proxy(self.url.strip(), auth=auth)

    def transport(self, **kwargs):
        try:
            return httpx.HTTPTransport(proxy=self.httpx_proxy(), **kwargs)
        except ImportError as exc:          # socksio missing
            raise ProxyError("socks5 proxy'si için gereken paket (socksio) kurulu değil; programı baslat.bat kur ile yeniden kurun.") from exc

    def mounts(self, hosts, **kwargs):
        """httpx mounts: only these domains and their subdomains through the proxy (every other request goes directly)."""
        transport = self.transport(**kwargs)
        out = {}
        for host in sorted({host_key(h) for h in hosts or () if host_key(h)}):
            out[f"all://{host}"] = transport
            out[f"all://*.{host}"] = transport
        return out

    def client(self, **kwargs):
        """A client that sends everything through the proxy (the proxy test and region-blocked pages only)."""
        return httpx.Client(transport=self.transport(), timeout=kwargs.pop("timeout", TIMEOUT), follow_redirects=True, **kwargs)


def host_key(url_or_host):
    text = str(url_or_host or "").strip()
    host = (urlsplit(text).hostname if "//" in text else text.split("/")[0].split(":")[0]) or ""
    host = host.lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def pac_script(proxy, hosts):
    """A PAC script: the region-blocked domains (and their subdomains) through the proxy, every other address DIRECT."""
    kind = CHROME_SCHEMES[proxy.scheme]
    names = sorted({host_key(h) for h in hosts or () if host_key(h)})
    target = f"{kind} {proxy.host}:{proxy.port}"
    checks = " ||\n      ".join(f'host === "{h}" || dnsDomainIs(host, ".{h}")' for h in names) or "false"
    return (f"function FindProxyForURL(url, host) {{\n  host = host.toLowerCase();\n  if ({checks}) {{\n    return \"{target}\";\n  }}\n"
            f"  return \"DIRECT\";\n}}\n")


def pac_url(script):
    return "data:application/x-ns-proxy-autoconfig;base64," + base64.b64encode(script.encode("utf-8")).decode("ascii")


# ---- settings -----------------------------------------------------------------------------------------------------------------------

def stored(data_dir):
    section = stored_settings.stored_settings(data_dir).get(SECTION)
    section = section if isinstance(section, dict) else {}
    url = section.get("adres") if isinstance(section.get("adres"), str) else ""
    user = section.get("kullanici") if isinstance(section.get("kullanici"), str) else ""
    return {"adres": url if not proxy_url_error(url) else "", "kullanici": user[:200]}


def load(data_dir, *, with_password=True):
    """The proxy, or None when no address is set."""
    values = stored(data_dir)
    if not values["adres"]:
        return None
    password = credentials.get_secret(PASSWORD) if with_password and values["kullanici"] else None
    return ProxySettings(values["adres"], values["kullanici"], password)


def view(data_dir):
    """Settings → ABD proxy'si: address and user name (not secret), "parola kayıtlı" and the notes; never the password."""
    values = stored(data_dir)
    try:
        saved = credentials.has_secret(PASSWORD)
        error = None
    except credentials.SecretError as exc:
        saved, error = False, str(exc)
    notes = []
    if values["adres"]:
        proxy = ProxySettings(values["adres"], values["kullanici"])
        if proxy.browser_problem:
            notes.append(proxy.browser_problem)
        if values["kullanici"] and not saved:
            notes.append(NO_PASSWORD)
    if error:
        notes.append(error)
    return {"adres": values["adres"], "kullanici": values["kullanici"], "parola_kayitli": saved, "tanimli": bool(values["adres"]),
            "etiket": logs.proxy_label(values["adres"]) if values["adres"] else "", "semalar": list(PROXY_SCHEMES), "notlar": notes,
            "tarayici_kullanilabilir": bool(values["adres"]) and not ProxySettings(values["adres"], values["kullanici"]).browser_problem}


def save(data_dir, url, user, password=None):
    """Address and user name to ayarlar.json (empty address: no proxy); a password, when given, to Credential Manager."""
    url = (url or "").strip()
    user = (user or "").strip()
    if url:
        error = proxy_url_error(url)
        if error:
            raise ProxyError(error)
    if len(user) > 200:
        raise ProxyError("Kullanıcı adı en çok 200 karakter olabilir.")
    if password:
        try:
            credentials.set_secret(PASSWORD, password)
        except credentials.SecretError as exc:
            raise ProxyError(str(exc)) from exc
    data = stored_settings.stored_settings(data_dir)
    data[SECTION] = {"adres": url, "kullanici": user}
    stored_settings.write_settings(data_dir, data)
    return view(data_dir)


def delete_password(data_dir):
    try:
        credentials.delete_secret(PASSWORD)
    except credentials.SecretError as exc:
        raise ProxyError(str(exc)) from exc
    return view(data_dir)


# ---- "Proxy'yi dene" ----------------------------------------------------------------------------------------------------------------

def describe(exc):
    if isinstance(exc, httpx.ProxyError):
        return "proxy bağlantıyı kurmadı (adres, port, kullanıcı adı ya da parola yanlış olabilir)"
    if isinstance(exc, httpx.TimeoutException):
        return "zaman aşımı"
    if isinstance(exc, httpx.ConnectError):
        return "bağlantı kurulamadı"
    if isinstance(exc, httpx.HTTPError):
        return "bağlantı hatası"
    return type(exc).__name__


def test(proxy, *, client_factory=None, service=None):
    """Through the proxy to a public IP service: {"ok", "ip", "ulke", "uyari", "satirlar"}. The lines name the proxy as `scheme://host`
    only."""
    if proxy is None:
        raise ProxyError("ABD proxy'si tanımlı değil: önce adresini kaydedin.")
    if proxy.missing_password:
        raise ProxyError(NO_PASSWORD)
    service = service or IP_SERVICE
    lines = [f"Proxy: {proxy.label}" + (" (kullanıcı adıyla)" if proxy.user else "")]
    try:
        client = client_factory(proxy) if client_factory else proxy.client()
    except ProxyError as exc:
        return {"ok": False, "ip": None, "ulke": None, "uyari": None, "satirlar": lines + [str(exc)]}
    started = datetime.now(timezone.utc)
    try:
        with client:
            response = client.get(service, headers={"Accept": "application/json"})
            body = response.json() if response.status_code == 200 else {}
    except (httpx.HTTPError, OSError, ValueError) as exc:
        lines.append(proxy.sanitize(f"BAŞARISIZ: {describe(exc)}."))
        return {"ok": False, "ip": None, "ulke": None, "uyari": None, "satirlar": lines}
    elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    ip = body.get("ip") if isinstance(body, dict) and isinstance(body.get("ip"), str) and _IP.match(body["ip"]) else None
    country = body.get("country") if isinstance(body, dict) and isinstance(body.get("country"), str) else None
    country = country.upper() if country and _COUNTRY.match(country.upper()) else None
    if response.status_code != 200 or ip is None:
        lines.append(proxy.sanitize(f"BAŞARISIZ: IP servisi HTTP {response.status_code} döndü; çıkış adresi okunamadı."))
        return {"ok": False, "ip": None, "ulke": None, "uyari": None, "satirlar": lines}
    warning = None if country == "US" else NOT_US
    lines.append(f"Çıkış adresi {ip}, ülke {country or 'bilinmiyor'} ({urlsplit(service).hostname}, {elapsed} ms).")
    if warning:
        lines.append(warning + ".")
    return {"ok": True, "ip": ip, "ulke": country, "uyari": warning, "satirlar": lines}


test.__test__ = False


# ---- the region-blocked list (schema 18) --------------------------------------------------------------------------------------------

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def listed_hosts(con):
    return [row[0] for row in con.execute("SELECT host FROM region_blocked_hosts ORDER BY host")]


def is_listed(hosts, url_or_host):
    host = host_key(url_or_host)
    return any(host == h or host.endswith("." + h) for h in hosts)


def mark(con, host, *, title=None, url=None, evidence=None, added_by="program", when=None):
    """Put a domain on the list (or refresh its last-seen time and page title). Local addresses are never listed."""
    host = host_key(host)
    if not host or host in LOCAL_HOSTS:
        return False
    stamp = when or now_iso()
    con.execute("""INSERT INTO region_blocked_hosts (host,title,url,evidence,added_by,first_seen_at,last_seen_at) VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(host) DO UPDATE SET title=COALESCE(excluded.title, title), url=COALESCE(excluded.url, url),
        evidence=COALESCE(excluded.evidence, evidence), last_seen_at=excluded.last_seen_at""",
                (host, (title or None) and str(title)[:300], (url or None) and str(url)[:500], (evidence or None) and str(evidence)[:300],
                 added_by, stamp, stamp))
    return True


def unmark(con, host):
    return con.execute("DELETE FROM region_blocked_hosts WHERE host=?", (host_key(host),)).rowcount > 0


def listing(con):
    return [dict(row) for row in con.execute("SELECT * FROM region_blocked_hosts ORDER BY host")]


def dumps(value):
    return json.dumps(value, ensure_ascii=False)
