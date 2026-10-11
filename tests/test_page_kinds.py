"""GÖREV-16 Adım 2b: what a page that came back is — an ordinary page, a verification the user can pass, a refusal nobody can pass, or a
region block. The fixtures are shared with the extension's Node test (tests/fixtures/sayfa_turleri/beklenen.json); the CVS and Publix
pages are the user's raw copies of 11 October 2026, shortened."""
import json
from pathlib import Path

import pytest

from studio.sources import browser_verification as bv
from studio.sources import page_kinds as K

FIXTURES = Path(__file__).parent / "fixtures" / "sayfa_turleri"
EXPECTED = json.loads((FIXTURES / "beklenen.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", EXPECTED, ids=lambda case: f"{case['dosya']}-{case['tur']}")
def test_each_fixture_has_its_kind(case):
    html = (FIXTURES / case["dosya"]).read_text(encoding="utf-8")
    assert K.classify(html, case["baslik"], case["adres"], case["http"]) == case["tur"]


def test_the_kinds_of_the_users_trial():
    cvs = (FIXTURES / "cvs-bolge-403.html").read_text(encoding="utf-8")
    publix = (FIXTURES / "publix-international.html").read_text(encoding="utf-8")
    assert K.classify(cvs, "", "https://www.cvs.com/store-locator", 403) == "bolge_engeli"
    assert K.evidence(cvs, "", "https://www.cvs.com/").startswith("CVS.com ® is not available to customers or patients who are located outside")
    assert K.classify(publix, "International | Publix Super Markets", "https://www.publix.com/locations", 200) == "bolge_engeli"
    assert K.evidence(publix, "International | Publix Super Markets", "") == "International | Publix Super Markets"
    assert K.redirect_kind("https://geo-blocked-site.dpxmedcity.net/") == "bolge_engeli"          # HCA's redirect
    assert K.redirect_kind("https://login.example.test/") == "yonlendi"


def test_access_denied_is_no_longer_a_verification_and_a_perimeterx_check_still_is():
    akamai = (FIXTURES / "akamai-access-denied.html").read_text(encoding="utf-8")
    assert K.classify(akamai, "Access Denied", "https://www.winndixie.com/locator", 403) == "erisim_reddedildi"
    assert K.classify("<html><title>Access Denied</title><body>Access Denied</body></html>", "Access Denied", "", 200) == "erisim_reddedildi"
    perimeterx = (FIXTURES / "perimeterx-bas-ve-tut.html").read_text(encoding="utf-8")
    assert K.classify(perimeterx, "Access to this page has been denied", "", 403) == "dogrulama"


def test_a_region_phrase_on_a_long_ordinary_page_is_not_a_block():
    page = (FIXTURES / "normal-sayfa.html").read_text(encoding="utf-8")
    assert K.classify(page, "Store Locator", "https://example.test/", 200) == "tamam"
    assert K.classify(page, "Store Locator", "https://example.test/", 403) == "bolge_engeli"          # with a 403 the phrase counts
    short = "<html><body><p>This site is not available in your country.</p></body></html>"
    assert K.classify(short, "", "", 200) == "bolge_engeli"


class Page:
    def __init__(self, content, title="", url=""):
        self._content, self._title, self.url = content, title, url

    def content(self):
        return self._content

    def title(self):
        return self._title


def test_the_programs_browser_never_sends_a_refusal_or_a_region_block_to_the_user():
    cvs = (FIXTURES / "cvs-bolge-403.html").read_text(encoding="utf-8")
    akamai = (FIXTURES / "akamai-access-denied.html").read_text(encoding="utf-8")
    challenge = (FIXTURES / "cloudflare-bir-dakika.html").read_text(encoding="utf-8")
    assert bv.page_state(Page(cvs)) == "blocked" and bv.page_state(Page(akamai, "Access Denied")) == "blocked"
    assert bv.page_state(Page(challenge, "Just a moment...")) == "challenge"
    assert bv.page_state(Page("<title>Grill</title><h1>Grill</h1>", "Grill")) == "open"
    stop = bv.region_blocked("www.cvs.com", Page(cvs, "", "https://www.cvs.com/x"))
    assert isinstance(stop, bv.RegionBlocked) and isinstance(stop, bv.SiteBlocked) and stop.domain == "cvs.com" and "outside" in stop.evidence
    assert bv.region_blocked("example.test", Page(akamai, "Access Denied")) is None
    # the end-of-run wait drops a blocked page at once instead of waiting for the user
    waits = []
    cleared = bv.wait_for_user({"cvs.com": Page(cvs), "ok.test": Page("<h1>ok</h1>")}, lambda: False, 900, waits.append, sleep=lambda s: None)
    assert cleared == {"ok.test"} and waits == ["cvs.com, ok.test", None]


class FakeSession:
    def __init__(self, page):
        self.page = page

    def new_page(self):
        return self

    def goto(self, url, **kwargs):
        pass

    def content(self):
        return self.page.content()

    def title(self):
        return self.page.title()

    @property
    def url(self):
        return self.page.url

    def close(self):
        pass


def test_the_browser_verifier_raises_region_blocked_for_a_region_page():
    cvs = (FIXTURES / "cvs-bolge-403.html").read_text(encoding="utf-8")
    verifier = bv.BrowserVerifier(session_factory=lambda: FakeSession(Page(cvs, "", "https://www.cvs.com/")))
    with pytest.raises(bv.RegionBlocked) as caught:
        verifier("cvs.com", "https://www.cvs.com/", lambda: False, 5)
    assert caught.value.domain == "cvs.com"
    denied = bv.BrowserVerifier(session_factory=lambda: FakeSession(Page("<h1>You don't have permission to access</h1>", "Access Denied")))
    with pytest.raises(bv.SiteBlocked) as refused:
        denied("winndixie.com", "https://www.winndixie.com/", lambda: False, 5)
    assert not isinstance(refused.value, bv.RegionBlocked)
