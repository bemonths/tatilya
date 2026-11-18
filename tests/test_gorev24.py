"""GÖREV-24: RealJoy (realjoy.com). The listing page and its scripts were read with the user's extension (17 November 2026): the price
comes only from the page's dates form (POST /ajax/quote). GÖREV-25 (user decision of 17 November 2026): the extension sends the
page's own queries on the allowed list, RealJoy got its reader and configuration; its row in the reviewed table says so. The extension
trial keeps two pages of one site at least the site's own gap apart (RealJoy answered 429)."""
import time

from studio.destinations import thirty_a
from studio.evidence import blocks as B
from studio.sources.agency_adapters import ADAPTERS
from tests.test_extension import paired
from tests.test_extension_16 import client, run_trial  # noqa: F401  (the fixture)


def test_realjoys_row_names_the_post_reason_and_the_reader_of_gorev25():
    rows = B.unread_companies(thirty_a)
    reason = rows["realjoy.com"]["neden"]
    assert "POST" in reason and "/ajax/quote" in reason and "GÖREV-25" in reason and rows["realjoy.com"]["kontrol_tarihi"] == "2026-11-17"
    assert "realjoy" in ADAPTERS                                              # GÖREV-25: the reader
    configured = [site[0] for name in ("AGENCY_SITES", "AGENCY_SITES_V12", "AGENCY_SITES_V22", "AGENCY_SITES_V23", "AGENCY_SITES_V24")
                  for site in getattr(thirty_a, name)]
    assert configured.count("realjoy.com") == 1                               # configured once, by migration v24


def test_two_trial_pages_of_one_site_wait_for_the_sites_own_gap(client, monkeypatch):  # noqa: F811
    bridge = paired(client)
    bridge.set_gap(3)
    monkeypatch.setattr(thirty_a, "EXTENSION_TRIAL_GAP_S", {"ornek.test": 4})
    seen = []

    def pages(url):
        seen.append((url, time.monotonic()))
        return {"durum": "tamam", "son_adres": url, "baslik": "Örnek", "http_durumu": 200, "html": "<html><title>Örnek</title>içerik</html>"}
    sites = (("ornek.test", "https://ornek.test/a", "örnek"), ("cvs.com", "https://www.cvs.com/x", "eczane"),
             ("ornek.test", "https://ornek.test/b", "örnek"))
    job, _ = run_trial(client, monkeypatch, sites, pages)
    assert job["status"] == "done" and [r["durum"] for r in job["result"]["siteler"]] == ["tamam"] * 3
    at = dict(seen)
    assert at["https://ornek.test/b"] - at["https://ornek.test/a"] >= 4 - 0.05          # the site's gap (above the extension's 3 s)
    assert at["https://www.cvs.com/x"] - at["https://ornek.test/a"] < 3                  # another site does not wait
