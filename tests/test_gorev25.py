"""GÖREV-25: the page's own queries through the extension (user decision of 17 November 2026) and RealJoy's reader.

- the rules of a query (studio/extension_queries.py and the same lists in eklenti/logic.js): the allowed list, the forbidden paths and
  hosts, another domain, only the given fields;
- the Settings trial sends one sample of each allowed query and keeps the answer with the query's method, fields and time;
- RealJoy (realjoy.com): the listing in parts of 12 (POST /ajax/results/scroll) and the "liste eksik" rule, the price breakdown of
  POST /ajax/quote and its "No", the address rule (a home with a similar name but another address is not tied), the 429 rule, and
  the company skipped when the extension is not connected.
Fixtures (tests/fixtures/gorev25/) are cut from the raw copies of the user's extension trials of 17 November 2026.
"""
import base64
import json
import re
import threading
import time
from pathlib import Path

import pytest

from studio import extension as ext
from studio import extension_queries as eq
from studio.destinations import thirty_a
from tests.test_extension import as_extension, paired
from tests.test_extension_16 import client  # noqa: F401  (the fixture)

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures" / "gorev25"
QUOTE_FIELDS = ["checkin", "checkout", "propertyID", "roomTypeID", "propertyName", "hash"]
ALLOWED = [eq.normalize({"alan_adi": "realjoy.com", "yol": "/ajax/quote", "yontem": "POST", "alanlar": QUOTE_FIELDS}),
           eq.normalize({"alan_adi": "realjoy.com", "yol": "/ajax/results/scroll", "yontem": "POST", "alanlar": ["page", "propertyIDs", "sortBy"]})]
GIVEN = {"checkin": "01/09/2027", "checkout": "01/16/2027", "propertyID": "1806", "roomTypeID": "", "propertyName": "Sea La Vie", "hash": ""}


def ask(path="/ajax/quote", method="POST", fields=None, domain="realjoy.com"):
    return eq.refusal({"alan_adi": domain, "yol": path, "yontem": method, "alanlar": GIVEN if fields is None else fields}, ALLOWED)


# ---- the rules ----------------------------------------------------------------------------------------------------------------

def test_an_allowed_query_passes_and_the_www_form_of_the_domain_is_the_same_site():
    assert ask() is None and ask(domain="www.realjoy.com") is None
    assert ask("/ajax/results/scroll", fields={"page": "2", "propertyIDs": "1,2", "sortBy": "Random"}) is None


@pytest.mark.parametrize("path", ["/ajax/addToCart", "/checkout", "/account/login", "/ajax/saveFavorites", "/book/now", "/booking",
                                  "/contact-us", "/ajax/sendInquiry", "/reservations/new", "/my/trips", "/ajax/payment", "/guest/profile"])
def test_a_forbidden_path_is_refused_even_on_the_list(path):
    allowed = ALLOWED + [eq.normalize({"alan_adi": "realjoy.com", "yol": path, "yontem": "POST", "alanlar": None})]
    reason = eq.refusal({"alan_adi": "realjoy.com", "yol": path, "yontem": "POST", "alanlar": {"x": "1"}}, allowed)
    assert reason and "yasak listede" in reason


def test_the_booking_engine_folder_alone_is_not_a_forbidden_word():
    assert not eq.forbidden_path("/bookingEngine/javascripts/srp/z_srp.js") and eq.forbidden_path("/bookingEngine/ajax/addToCart")


@pytest.mark.parametrize("domain", ["paypal.com", "checkout.stripe.com", "login.realjoy.com", "secure.realjoy.com", "accounts.google.com"])
def test_a_forbidden_host_is_refused(domain):
    assert "yasak listede" in ask(domain=domain)


def test_another_domain_another_path_another_method_and_other_fields_are_refused():
    assert "izinli sorgu listesinde değil" in ask(domain="otherrentals.com")
    assert "izinli sorgu listesinde değil" in ask("/ajax/map")
    assert "izinli sorgu listesinde değil" in ask(method="GET")
    assert "yalnız GET ya da POST" in ask(method="PUT")
    assert "alanları" in ask(fields={**GIVEN, "email": "a@b.c"})                        # a field the page does not send
    assert "alanları" in ask(fields=dict(reversed(list(GIVEN.items()))))                # not in the page's own order
    assert ask(fields={k: v for k, v in GIVEN.items() if k != "hash"}) is None          # fewer is fine (the page may leave one out)
    assert "geçersiz" in ask("/ajax/quote?x=1") and "geçersiz" in ask("https://evil.test/ajax/quote") and "geçersiz" in ask("/a/../b")


def test_the_extension_holds_the_same_lists_and_rules():
    logic = (ROOT / "eklenti" / "logic.js").read_text(encoding="utf-8")

    def js_list(name):
        return re.findall(r'"([^"]+)"', re.search(rf"export const {name} = \[(.*?)\];", logic, re.S).group(1))
    assert js_list("FORBIDDEN_WORDS") == list(eq.FORBIDDEN_WORDS) and js_list("FORBIDDEN_SEGMENTS") == list(eq.FORBIDDEN_SEGMENTS)
    assert js_list("FORBIDDEN_HOSTS") == list(eq.FORBIDDEN_HOSTS) and js_list("FORBIDDEN_HOST_LABELS") == list(eq.FORBIDDEN_HOST_LABELS)
    assert js_list("QUERY_METHODS") == list(eq.METHODS)
    assert int(re.search(r"export const MAX_FIELDS = (\d+);", logic).group(1)) == eq.MAX_FIELDS
    manifest = json.loads((ROOT / "eklenti" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == ext.EXPECTED_VERSION == "0.20.0"


def test_the_allowed_list_comes_from_the_configuration(tmp_path):
    from studio.database import Database
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    found = db.extension_queries()
    assert [(q["alan_adi"], q["yontem"], q["yol"]) for q in found] == [("realjoy.com", "POST", "/ajax/quote"), ("realjoy.com", "POST", "/ajax/results/scroll")]
    assert found[0]["alanlar"] == QUOTE_FIELDS
    with db.connect() as con:
        con.execute("UPDATE destination_agency_sites SET enabled=0 WHERE domain='realjoy.com'")
    assert db.extension_queries() == []                                                  # a company switched off sends nothing


# ---- the program's side of a query --------------------------------------------------------------------------------------------

class QueryExtension(threading.Thread):
    """The extension for the bridge: pages and queries answered by `answer(item)`; every item it was given is kept."""

    def __init__(self, client, answer, permitted=("realjoy.com", "ornek.test")):
        super().__init__(daemon=True)
        self.client, self.answer, self.permitted, self.items, self.views, self.done = client, answer, list(permitted), [], [], threading.Event()

    def run(self):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not self.done.is_set():
            job = as_extension(self.client, "/api/eklenti/sor", {"surum": ext.EXPECTED_VERSION, "izinli": self.permitted}).json()["is"]
            if not job:
                time.sleep(0.05)
                continue
            self.views.append(job)
            while True:
                step = as_extension(self.client, f"/api/eklenti/is/{job['id']}/sonraki").json()
                if step.get("bitti"):
                    as_extension(self.client, f"/api/eklenti/is/{job['id']}/bitti")
                    break
                if step.get("bekle"):
                    time.sleep(0.05)
                    continue
                self.items.append(step["oge"])
                as_extension(self.client, f"/api/eklenti/is/{job['id']}/sonuc", {"oge_id": step["oge"]["id"], **self.answer(step["oge"])})


def answered(body, status=200):
    return {"durum": "tamam", "http_durumu": status, "son_adres": "https://www.realjoy.com/x", "basliklar": {"content-type": "text/html"},
            "govde_base64": base64.b64encode(body).decode(), "gonderilen": {"zaman": "2026-11-17T20:00:00Z", "adres": "https://www.realjoy.com/x"}}


def test_the_trial_sends_each_allowed_query_once_and_keeps_its_fields_and_answer(client, monkeypatch):  # noqa: F811
    bridge = paired(client)
    bridge.set_gap(3)
    monkeypatch.setattr(thirty_a, "EXTENSION_TRIAL_SITES", (("realjoy.com", "https://www.realjoy.com/beach-rentals/30a-vacation-rentals", "liste"),))
    monkeypatch.setattr(thirty_a, "EXTENSION_TRIAL_GAP_S", {"realjoy.com": 3})
    monkeypatch.setattr(thirty_a, "EXTENSION_TRIAL_QUERIES", thirty_a.EXTENSION_TRIAL_QUERIES + (
        {"alan_adi": "realjoy.com", "yol": "/ajax/addToCart", "yontem": "POST", "alanlar": {"x": "1"}, "aciklama": "yasak"},))
    at = []

    def answer(item):
        at.append(time.monotonic())
        if item["tur"] == "sayfa":
            return {"durum": "tamam", "son_adres": item["adres"], "baslik": "Liste", "http_durumu": 200, "html": "<html>liste</html>"}
        return answered(b"No" if item["yol"] == "/ajax/quote" else b"<div class='be-property-widget'></div>")
    fake = QueryExtension(client, answer)
    fake.start()
    job = client.post("/api/tarayici-eklentisi/sorunlu-siteler").json()
    deadline = time.monotonic() + 30
    while client.app.state.db.job(job["id"])["status"] in ("queued", "running"):
        assert time.monotonic() < deadline
        time.sleep(0.05)
    fake.done.set()
    fake.join(5)
    rows = client.app.state.db.job(job["id"])["result"]["siteler"]
    assert [r["durum"] for r in rows] == ["tamam", "tamam", "tamam", "reddedildi"]
    queries = [i for i in fake.items if i["tur"] == "sorgu"]
    assert [q["yol"] for q in queries] == ["/ajax/results/scroll", "/ajax/quote"]           # the forbidden one never reached the extension
    assert queries[1]["alanlar"] == thirty_a.EXTENSION_TRIAL_QUERIES[1]["alanlar"] and list(queries[1]["alanlar"]) == QUOTE_FIELDS
    assert all(view["izinli_sorgular"] and all(q["alan_adi"] == "realjoy.com" for q in view["izinli_sorgular"]) for view in fake.views)
    assert min(b - a for a, b in zip(at, at[1:])) >= 3 - 0.05                                  # the site's own gap between every two
    record = json.loads((client.app.state.db.path.parent / rows[2]["dosya"]).with_suffix(".json").read_text(encoding="utf-8"))
    assert record["sorgu"]["yontem"] == "POST" and record["sorgu"]["yol"] == "/ajax/quote" and record["sorgu"]["zaman"]
    assert record["sorgu"]["alanlar"]["propertyID"] == "1806" and (client.app.state.db.path.parent / rows[2]["dosya"]).read_bytes() == b"No"
    assert "yasak listede" in rows[3]["not"]
