"""Is a site region-blocked? One page asked twice — directly and through the user's US proxy — and the two answers compared
(GÖREV-22, Adım 2; docs/M18-ABD-PROXY-BOLGE-ENGELI.md "Bölge engeli ölçümü").

The proxy is only for sites that serve visitors inside the United States and nobody else; it is never a way past bot protection, a
rate limit or a ban. So a domain goes on the region-blocked list only when this comparison says so:

- "bolge_engeli": the direct request is refused (a country block, a refusal page, a verification, a 401/403/429/451) or gets no
  answer (no connection, a timeout), and through the proxy the site answers normally.
- "bolge_engeli_degil": through the proxy the same refusal, block page or verification comes back, or the site answers normally both
  ways (no block at all). The site is left alone; the proxy is not used for it.
- "site_yok": neither way reaches a site (no DNS record, no connection, a server error both ways): the site is gone for a visitor in
  the United States too.

"Answers normally" means the site itself answered without a block: a page the page kinds call ordinary (`page_kinds.classify`), a
redirect, or the site's own "not found" page. An answer is described by `answer(...)`; nothing here asks a site anything.
"""
import re

from . import page_kinds

# A domain that is suspended, expired or parked answers with its registrar's or a parking company's page, not with the site
# (GÖREV-22: outdoorshower30a.com answered through the proxy with Namecheap's "Registrant WHOIS contact information verification").
PARKED = re.compile(r"Registrant WHOIS contact information verification|domain (?:name )?has (?:been suspended|expired)|"
                    r"This domain (?:is parked|has expired|is for sale)|Buy this domain|domain is parked free", re.I)

CLASSES = ("bolge_engeli", "bolge_engeli_degil", "site_yok")
LABELS = {"bolge_engeli": "bölge engeli", "bolge_engeli_degil": "bölge engeli değil", "site_yok": "site yok"}
REFUSED_STATUSES = (401, 403, 429, 451)
KINDS = {"icerik": "normal yanıt", "ret": "ret ya da engel sayfası", "dogrulama": "doğrulama sayfası", "bolge": "ülke engeli sayfası",
         "yok": "yanıt yok"}


def answer(status=None, title=None, html="", url="", error=None):
    """One side of the comparison: what came back for the page (`status` None with `error` when nothing came back)."""
    return {"status": status, "title": title, "html": html or "", "url": url or "", "error": error}


def side_kind(side):
    """'icerik' (the site answered normally), 'bolge' (a country block page), 'ret' (a refusal nobody passes), 'dogrulama' (a
    verification page) or 'yok' (no answer: no connection, a timeout, a server error)."""
    status = side.get("status")
    if status is None or status >= 500:
        return "yok"
    if PARKED.search(f"{side.get('title') or ''} {str(side.get('html') or '')[:page_kinds.HEAD]}"):
        return "yok"                 # the registrar's or a parking company's page: the site itself is not there
    kind = page_kinds.classify(side.get("html"), side.get("title") or "", side.get("url"), status)
    if kind == "bolge_engeli":
        return "bolge"
    if kind == "dogrulama":
        return "dogrulama"
    if kind == "erisim_reddedildi" or status in REFUSED_STATUSES:
        return "ret"
    return "icerik"


def classify(direct, proxied):
    """{"sinif": one of CLASSES, "dogrudan": the direct side's kind, "proxy": the proxy side's kind, "neden": a Turkish sentence}."""
    one, two = side_kind(direct), side_kind(proxied)
    if two == "icerik" and one != "icerik":
        result, reason = "bolge_engeli", f"Doğrudan istek: {KINDS[one]}; proxy üzerinden site normal yanıt veriyor."
    elif one == "yok" and two == "yok":
        result, reason = "site_yok", "İki yoldan da siteye ulaşılamıyor; ABD'deki bir ziyaretçi için de site yok."
    elif one == "icerik" and two == "icerik":
        result, reason = "bolge_engeli_degil", "Site iki yoldan da normal yanıt veriyor; engel yok."
    elif two == "yok":
        result, reason = "bolge_engeli_degil", f"Proxy üzerinden yanıt yok; doğrudan istek: {KINDS[one]}. Bölge engeli gösterilemedi."
    else:
        result, reason = "bolge_engeli_degil", (f"Proxy üzerinden de {KINDS[two]} geliyor (doğrudan: {KINDS[one]}); bu bir bölge engeli "
                                                "değil, proxy kullanılmaz.")
    return {"sinif": result, "dogrudan": one, "proxy": two, "neden": reason}
