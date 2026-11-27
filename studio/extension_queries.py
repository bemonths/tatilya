"""The page's own queries through the extension (GÖREV-25; user decision of 17 November 2026; docs/M16-TARAYICI-EKLENTISI.md).

The extension may send, from the site's own tab, the public queries the page itself sends for its visitor: a price question and the
next part of a listing ("load more", paging). A query carries a domain, a path, a method (GET or POST) and its fields; the extension
sends exactly the given fields, from the tab's own origin, and nothing else. Only the queries of the program's allowed list (the
destination configuration: `extension_queries` of a company's options) are sent. Login, account, payment, reservation, cart, contact
and personal-data addresses are refused whatever the list says: the forbidden words and hosts below are checked on both sides (the
extension's eklenti/logic.js holds the same lists; a test keeps them equal). The extension never clicks or types.

HEDEF-03 (27 November 2026): an entry may say where the page puts its fields (`alanlar_yeri`: "govde", the form body, the default;
or "adres", the address's query part, as a Streamline page's script does with POST admin-ajax.php?action=…&params=…), the content type
the page's request carries (`icerik_turu`, one of CONTENT_TYPES), and a pattern a field's value must match in full (`desenler`: name →
regular expression), so only the page's own kinds of question go (e.g. `methodName` of the Streamline price questions).

Destination-independent: the rules know no site; which queries a site may send comes from the configuration.
"""
import re

METHODS = ("GET", "POST")
# Words of a path (split at "/", "-", "_", "." and camelCase) that refuse a query. "booking" alone is not here: booking engines
# serve their public pages under such a folder (/bookingEngine/...); a whole segment "booking"/"bookings"/"book" is refused.
FORBIDDEN_WORDS = ("login", "logon", "logout", "signin", "signup", "sign", "register", "registration", "account", "accounts", "password",
                   "auth", "oauth", "checkout", "payment", "payments", "pay", "card", "cart", "basket", "order", "orders", "reserve",
                   "reservation", "reservations", "confirm", "contact", "inquiry", "inquire", "enquiry", "subscribe", "newsletter",
                   "profile", "wallet", "guest", "owner", "save", "favorite", "favorites", "lead", "message", "email", "phone", "review")
FORBIDDEN_SEGMENTS = ("book", "booking", "bookings", "booknow", "my")
FORBIDDEN_HOSTS = ("paypal.com", "stripe.com", "squareup.com", "authorize.net", "braintreegateway.com", "accounts.google.com",
                   "login.microsoftonline.com", "appleid.apple.com", "facebook.com")
FORBIDDEN_HOST_LABELS = ("login", "auth", "account", "accounts", "checkout", "pay", "payment", "payments", "secure", "book", "booking",
                         "my", "sso", "id")
MAX_FIELDS, MAX_VALUE = 40, 2000
PLACES = ("govde", "adres")
CONTENT_TYPES = ("application/x-www-form-urlencoded; charset=UTF-8", "application/json")


def domain_of(host):
    host = (host or "").strip().lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def path_words(path):
    """'/ajax/results/scroll' -> ['ajax','results','scroll']; '/ajax/addToCart' -> ['ajax','add','to','cart']."""
    words = []
    for segment in (path or "").split("/"):
        for part in re.split(r"[-_.]+", segment):
            words += [w.lower() for w in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", part)]
    return words


def forbidden_path(path):
    segments = [s.lower() for s in (path or "").split("/") if s]
    return any(s in FORBIDDEN_SEGMENTS for s in segments) or any(w in FORBIDDEN_WORDS for w in path_words(path))


def forbidden_host(host):
    host = domain_of(host)
    if any(host == h or host.endswith("." + h) for h in FORBIDDEN_HOSTS):
        return True
    return any(label in FORBIDDEN_HOST_LABELS for label in host.split(".")[:-2])


def normalize(entry):
    """An allowed-list entry {alan_adi, yol, yontem, alanlar: [names] | None, amac, alanlar_yeri, icerik_turu, desenler}."""
    names = entry.get("alanlar")
    method = str(entry.get("yontem") or "GET").upper()
    place = str(entry.get("alanlar_yeri") or ("adres" if method == "GET" else "govde"))
    kind = entry.get("icerik_turu")
    patterns = entry.get("desenler") if isinstance(entry.get("desenler"), dict) else {}
    return {"alan_adi": domain_of(entry.get("alan_adi")), "yol": str(entry.get("yol") or ""), "yontem": method,
            "alanlar": [str(n) for n in names] if isinstance(names, (list, tuple)) else None, "amac": str(entry.get("amac") or ""),
            "alanlar_yeri": place if place in PLACES else "govde", "icerik_turu": kind if kind in CONTENT_TYPES else None,
            "desenler": {str(k): str(v) for k, v in patterns.items()}}


def allowed_from_sites(sites):
    """The allowed list from the destination's company configuration (each company's `inventory.extension_queries`)."""
    found = []
    for site in sites or ():
        inventory = site.get("inventory") or {}
        if not site.get("enabled", 1):
            continue
        for entry in inventory.get("extension_queries") or ():
            if isinstance(entry, dict):
                found.append(normalize({"alan_adi": site["domain"], **entry}))
    return found


def match_of(query, allowed):
    """The allowed-list entry of a query (domain, path, method), or None."""
    domain, path, method = domain_of(query.get("alan_adi")), str(query.get("yol") or ""), str(query.get("yontem") or "").upper()
    return next((a for a in allowed or () if a["alan_adi"] == domain and a["yol"] == path and a["yontem"] == method), None)


def refusal(query, allowed):
    """None when the query may be sent, else the reason (Turkish). query: {alan_adi, yol, yontem, alanlar: {name: value},
    alanlar_yeri: "govde" | "adres" (optional; the entry's place when not given)}."""
    domain, path = domain_of(query.get("alan_adi")), str(query.get("yol") or "")
    method = str(query.get("yontem") or "").upper()
    fields = query.get("alanlar")
    if method not in METHODS:
        return f"Sorgu yöntemi {method or '—'}; yalnız GET ya da POST gönderilir."
    if not domain or not re.fullmatch(r"[a-z0-9.-]+", domain):
        return "Sorgunun alan adı geçersiz."
    if not path.startswith("/") or "//" in path or ".." in path or re.search(r"[?#\\\s]", path):
        return "Sorgunun yolu geçersiz (yol '/' ile başlamalı; soru işareti, '#' ve '..' içermez; alanlar ayrı verilir)."
    if forbidden_host(domain):
        return f"{domain} yasak listede (giriş, ödeme ya da hesap alan adı); sorgu gönderilmedi."
    if forbidden_path(path):
        return f"{path} yasak listede (giriş, hesap, ödeme, rezervasyon, sepet, iletişim ya da kişisel bilgi adresi); sorgu gönderilmedi."
    if not isinstance(fields, dict) or len(fields) > MAX_FIELDS:
        return "Sorgunun alanları bir ad → değer listesi olmalı."
    if any(not isinstance(k, str) or not isinstance(v, str) or len(v) > MAX_VALUE for k, v in fields.items()):
        return "Sorgunun alan değerleri yazı olmalı."
    match = match_of({"alan_adi": domain, "yol": path, "yontem": method}, allowed)
    if match is None:
        return f"{method} {domain}{path} programın izinli sorgu listesinde değil; gönderilmedi."
    if match["alanlar"] is not None and list(fields) != [n for n in match["alanlar"] if n in fields]:      # a name off the list, or another order
        return f"Sorgunun alanları izinli listedekilerle aynı değil ({', '.join(match['alanlar'])}); gönderilmedi."
    place = query.get("alanlar_yeri") or match.get("alanlar_yeri") or "govde"
    if place != (match.get("alanlar_yeri") or "govde"):
        return f"Sorgunun alanları sayfanın koyduğu yerde değil ({'adreste' if match.get('alanlar_yeri') == 'adres' else 'gövdede'}); gönderilmedi."
    for name, pattern in (match.get("desenler") or {}).items():
        if name in fields and not re.fullmatch(pattern, fields[name], re.S):
            return f"Sorgunun {name} alanının değeri sayfanın kendi sorgularından değil; gönderilmedi."
    return None
