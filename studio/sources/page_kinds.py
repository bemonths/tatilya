"""What a page that came back is (GÖREV-16, Adım 2b): an ordinary page, a verification the user can pass, a refusal nobody can pass,
or a region block (the site serves only visitors inside the United States).

- Doğrulama ("dogrulama"): Cloudflare "Just a moment", "Checking your browser", the challenge platform's page script, PerimeterX
  (px-captcha, "Press & Hold"), and the titles "Just a moment", "Attention Required", "Verify you are human". The user passes it in the
  window; the extension waits for them (at most 15 minutes). "Access denied" is not one of them any more.
- Erişim reddedildi ("erisim_reddedildi"): Akamai's "Access Denied" / "You don't have permission to access", Cloudflare's "Sorry, you
  have been blocked", "You are unable to access", the titles "Access Denied" / "403 Forbidden", and a 403 page with (almost) nothing to
  read. Nobody passes it: it is skipped at once, never sent to the user.
- Bölge engeli ("bolge_engeli"): "outside of the United States", "outside the U.S.", "not available in your country/region",
  "unable to service customers outside", the title "International | Publix", and an address with "geo-block" in it (a redirect to a
  geo-block page). Skipped at once; the domain goes on the region-blocked list and is read through the user's US proxy when one is set
  (studio/proxy.py, studio/sources/region_reader.py). A phrase alone counts only on a short page or a 403/451 answer: an ordinary page
  may say "we do not ship outside the United States" in its footer.

The order is: region block, a strong refusal phrase, verification, a refusal title or an empty 403, ordinary page. A PerimeterX page
titled "Access to this page has been denied" that shows "Press & Hold" is therefore a verification.

The markers live here only. The extension's copy (eklenti/logic.js) is checked by a test against these patterns, and both are run on
the same fixtures (tests/fixtures/sayfa_turleri/beklenen.json).
"""
import html as html_lib
import re

# Verification the user can pass: the interstitial only (its title, its options object or its page script); a Turnstile box in a
# contact form is not one.
CHALLENGE = re.compile(r"<title>\s*Just a moment\.\.\.|cf_chl_opt|/cdn-cgi/challenge-platform/h/[a-z]/orchestrate/|Checking your browser before|"
                       r"Checking if the site connection is secure|px-captcha|Press &amp; Hold|Press & Hold", re.I)
CHALLENGE_TITLES = re.compile(r"^(just a moment|attention required|verify you are human|bir dakika)", re.I)
# A refusal nobody can pass.
DENIED = re.compile(r"Sorry, you have been blocked|You are unable to access|You don(?:'|’|&#39;|&#x27;)t have permission to access|"
                    r"You do not have permission to access", re.I)
DENIED_TITLES = re.compile(r"^(access denied|403 forbidden|forbidden|error 403)\b", re.I)
# The site serves only visitors inside the United States.
REGION = re.compile(r"outside of the United States|outside the United States|outside the U\.S\.|not available in your country|"
                    r"not available in your region|unable to service customers outside", re.I)
REGION_TITLES = re.compile(r"^International \| Publix", re.I)
REGION_ADDRESS = re.compile(r"geo-?block", re.I)

KINDS = ("tamam", "dogrulama", "erisim_reddedildi", "bolge_engeli")
LABELS = {"tamam": "tamam", "dogrulama": "doğrulama", "erisim_reddedildi": "erişim reddedildi", "bolge_engeli": "bölge engeli",
          "yonlendi": "başka siteye yönlendi"}
HEAD = 40000                 # the markers are looked for in the first part of the page
SHORT_TEXT = 4000            # a region phrase counts on a page with less visible text than this (or with a 403/451 answer)
EMPTY_TEXT = 300             # a 403 page with less visible text than this is a refusal
_INVISIBLE = re.compile(r"<(script|style|noscript|template)\b[^>]*>.*?</\1\s*>|<!--.*?-->", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def visible_text(page_html):
    """The page's readable text: scripts, styles and comments dropped, tags removed, entities decoded, spaces collapsed."""
    text = _INVISIBLE.sub(" ", str(page_html or ""))
    return _SPACE.sub(" ", html_lib.unescape(_TAG.sub(" ", text))).strip()


def classify(page_html="", title="", url="", status=None):
    """'tamam', 'dogrulama', 'erisim_reddedildi' or 'bolge_engeli' for a page that came back (see the module's order)."""
    head = str(page_html or "")[:HEAD]
    title = str(title or "").strip()
    text = visible_text(head)
    status = int(status) if isinstance(status, (int, float)) or str(status or "").isdigit() else None
    if REGION_TITLES.search(title) or REGION_ADDRESS.search(str(url or "")):
        return "bolge_engeli"
    if REGION.search(text) and (status in (403, 451) or len(text) < SHORT_TEXT):
        return "bolge_engeli"
    if DENIED.search(head):
        return "erisim_reddedildi"
    if CHALLENGE.search(head) or CHALLENGE_TITLES.search(title):
        return "dogrulama"
    if DENIED_TITLES.search(title) or (status == 403 and len(text) < EMPTY_TEXT):
        return "erisim_reddedildi"
    return "tamam"


def redirect_kind(final_url):
    """A page that went on to another site: 'bolge_engeli' when the address is a geo-block page, else 'yonlendi'."""
    return "bolge_engeli" if REGION_ADDRESS.search(str(final_url or "")) else "yonlendi"


def evidence(page_html="", title="", url=""):
    """The words that made a page a region block (for the list): the title, the address or the phrase."""
    if REGION_TITLES.search(str(title or "").strip()):
        return str(title).strip()[:200]
    if REGION_ADDRESS.search(str(url or "")):
        return str(url)[:200]
    text = visible_text(str(page_html or "")[:HEAD])
    match = REGION.search(text)
    if not match:
        return None
    start = text.rfind(". ", 0, match.start())
    end = text.find(". ", match.end())
    return text[start + 2 if start != -1 else 0:end + 1 if end != -1 else match.end() + 80].strip()[:200]
