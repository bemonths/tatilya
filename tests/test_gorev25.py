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
    assert manifest["version"] == ext.EXPECTED_VERSION == "0.21.0"


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
            while not self.done.is_set() and time.monotonic() < deadline:     # HEDEF-01: the CI hang — the inner loop also stops
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
    fake.join(timeout=10)      # HEDEF-01: no request of the fake extension may be in flight when the client closes
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


# ---- RealJoy's reader ---------------------------------------------------------------------------------------------------------

from datetime import date  # noqa: E402

import httpx  # noqa: E402

from studio.sources import agency_rates as ar  # noqa: E402
from studio.sources.agency_adapters import ADAPTERS, AdapterError  # noqa: E402
from studio.sources.agency_matching import address_match  # noqa: E402
from tests.test_agency_v2 import bd, site  # noqa: E402

REALJOY = ADAPTERS["realjoy"]
ORIGIN = "https://www.realjoy.com"
LIST_URL = ORIGIN + "/beach-rentals/30a-vacation-rentals"
HOME_URL = ORIGIN + "/beach-rentals/sea-la-vie-seaside-main-house"
SAMPLE_IDS = "1806,1451,504,278,191,1701,267,1521,189,1473,105,2176"     # the scroll answer's 12 (the trial's sample)
JAN = {"window_key": "jan", "checkin_date": date(2027, 1, 9), "checkout_date": date(2027, 1, 16), "nights": 7}
APR = {"window_key": "apr", "checkin_date": date(2027, 4, 10), "checkout_date": date(2027, 4, 17), "nights": 7}
JUN = {"window_key": "jun", "checkin_date": date(2027, 6, 5), "checkout_date": date(2027, 6, 12), "nights": 7}
CONFIG = thirty_a.AGENCY_SITE_OPTIONS_V24["realjoy.com"]


def fixture(name):
    return (FIX / name).read_text(encoding="utf-8")


def two_parts(count=24):
    """The listing page with its first part and one further part (the trial's scroll sample) and the given number of homes."""
    page = re.sub(r'<input[^>]*id="page(?:[3-9]|\d\d)propertyIDs"[^>]*>\n?', "", fixture("liste.html"))
    page = re.sub(r'(id="page2propertyIDs"[^>]*value=")[\d,]*"', rf'\g<1>{SAMPLE_IDS}"', page)
    return re.sub(r'data-count="\d+"', f'data-count="{count}"', page)


class Answer:
    def __init__(self, status, body, url):
        self.status, self.body, self.url, self.sha256, self.location, self.hops = status, body.encode("utf-8"), url, "x" * 64, None, []

    @property
    def text(self):
        return self.body.decode("utf-8")


class Session:
    """A company session for the adapter alone: every request is kept, `answer(method, url, data)` gives (status, body)."""

    def __init__(self, answer):
        self.answer, self.asked = answer, []

    def request(self, method, url, *, note, params=None, data=None, json=None, headers=None):
        self.asked.append((method, url, dict(data) if data is not None else None))
        status, body = self.answer(method, url, data)
        return Answer(status, body, url)


def allowed_by_configuration(path, fields):
    allowed = [eq.normalize({**q, "alan_adi": "realjoy.com"}) for q in CONFIG["inventory"]["extension_queries"]]
    return eq.refusal({"alan_adi": "realjoy.com", "yol": path, "yontem": "POST", "alanlar": fields}, allowed)


def test_the_list_is_read_in_the_pages_own_parts_of_12_with_the_allowed_fields():
    session = Session(lambda method, url, data: (200, two_parts() if method == "GET" else fixture("kaydirma.html")))
    units, replies = REALJOY.inventory(session, ORIGIN, CONFIG["inventory"])
    assert len(units) == 24 and len(replies) == 2
    assert session.asked[0] == ("GET", LIST_URL, None)
    method, url, fields = session.asked[1]
    assert (method, url) == ("POST", ORIGIN + "/ajax/results/scroll") and fields == {"page": "2", "propertyIDs": SAMPLE_IDS, "sortBy": "Random"}
    assert list(fields) == ["page", "propertyIDs", "sortBy"] and allowed_by_configuration("/ajax/results/scroll", fields) is None
    home = next(u for u in units if u["site_id"] == "1806")
    assert (home["address"], home["bedrooms"], home["latitude"], home["title"], home["url"]) == (
        "35 Tupelo St", 4, 30.31957283, "Sea La Vie Seaside Main House", HOME_URL)


def test_the_real_listing_page_names_311_homes_in_26_parts():
    page = fixture("liste.html")
    parts = re.findall(r'id="page(\d+)propertyIDs"[^>]*value="([\d,]*)"', page)
    assert re.search(r'data-count="(\d+)"', page).group(1) == "311" and len(parts) == 26
    assert len({i for _, ids in parts for i in ids.split(",")}) == 311 and len(REALJOY.cards(page, ORIGIN)) == 12


def test_a_short_list_is_an_error_and_no_home_is_tied_from_it():
    session = Session(lambda method, url, data: (200, two_parts(36) if method == "GET" else fixture("kaydirma.html")))
    with pytest.raises(AdapterError, match="36 evden yalnız 24.*liste eksik"):
        REALJOY.inventory(session, ORIGIN, CONFIG["inventory"])
    failing = Session(lambda method, url, data: (200, two_parts()) if method == "GET" else (500, "error"))
    with pytest.raises(AdapterError, match="2. parçası HTTP 500.*liste eksik"):
        REALJOY.inventory(failing, ORIGIN, CONFIG["inventory"])


def test_the_home_page_gives_the_form_the_calendar_and_the_minimum_stay():
    info = REALJOY.parse_page(fixture("ev-1806.html"), HOME_URL)
    assert info["site_id"] == "1806" and list(info["fields"]) == thirty_a.REALJOY_QUOTE_FIELDS
    assert "12/18/2026" in info["calendar"]["checkout"] and "05/29/2027" in info["calendar"]["unavailable"]
    assert info["min_nights"]["01/09/2027"] == 3 and info["min_nights"]["06/05/2027"] == 7
    assert REALJOY.unit_fields(fixture("ev-1806.html"))["address"] == "35 Tupelo St"


def test_the_price_keeps_the_sites_lines_and_its_promotion():
    quote = REALJOY.parse_quote(fixture("fiyat.html"))
    assert (quote["rent"], quote["taxes"], quote["total"], quote["cleaning_fee"]) == (6692.02, 938.53, 8759.05, 600.0)
    assert {f["name"]: f["amount"] for f in quote["fees"]} == {"Accidental Damage Waiver": 130.0, "Guest Departure Clean": 600.0,
                                                               "Check In Amenity Fee-Sea La Vie Seaside": 805.0, "Check In & Amenity Fee": 220.0,
                                                               "Promo discount (HOTDEALS)": -626.5}
    assert quote["total_includes_fees"] == quote["total_includes_taxes"] == 1         # rent + fee items + promotion + taxes = the site's total


def test_the_quote_posts_the_pages_form_and_no_is_not_available_and_a_taken_week_is_not_asked():
    info = REALJOY.parse_page(fixture("ev-1806.html"), HOME_URL)
    session = Session(lambda method, url, data: (200, fixture("fiyat.html") if data["checkin"] == "01/09/2027" else "No"))
    priced = REALJOY.quote(session, info, JAN)
    assert priced["status"] == "priced" and priced["total"] == 8759.05 and priced["min_stay"] == 3
    method, url, fields = session.asked[0]
    assert (method, url) == ("POST", ORIGIN + "/ajax/quote") and allowed_by_configuration("/ajax/quote", fields) is None
    assert fields == {"checkin": "01/09/2027", "checkout": "01/16/2027", "propertyID": "1806", "roomTypeID": "",
                      "propertyName": "Sea La Vie Seaside Main House", "hash": ""}
    no = REALJOY.quote(session, info, APR)
    assert (no["status"], no["available"]) == ("unavailable", 0) and '"No"' in no["message"]
    taken = REALJOY.quote(session, info, JUN)                                          # 06/05-06/12/2027: the calendar shows it taken
    assert (taken["status"], taken["available"], taken["rule_source"]) == ("unavailable", 0, "takvim") and len(session.asked) == 2
    short = REALJOY.quote(session, info, {**JAN, "checkout_date": date(2027, 1, 11), "nights": 2})
    assert short["status"] == "restricted" and short["min_stay"] == 3 and len(session.asked) == 2
    with pytest.raises(AdapterError, match="beklenen biçimde değil"):
        REALJOY.quote(Session(lambda *a: (200, "API Error")), info, JAN)


def test_only_the_address_ties_a_home_never_a_similar_name():
    units = REALJOY.cards(fixture("kaydirma.html"), ORIGIN)
    same = {"address": "35 Tupelo Street", "bedrooms": 4, "title": "Seaside cottage"}
    assert address_match(same, units, address_without_unit=True)[1]["site_id"] == "1806"
    similar = {"address": "37 Tupelo St", "bedrooms": 4, "title": "Sea La Vie Seaside Main House"}       # the name, another address
    assert address_match(similar, units, address_without_unit=True)[0] == "none"
    fewer = {"address": "35 Tupelo St", "bedrooms": 3, "title": "Sea La Vie Seaside Main House"}       # the name, other bedrooms
    assert address_match(fewer, units, address_without_unit=True)[0] == "none"
    building = [{"site_id": "1", "address": "11 Beachside Drive", "bedrooms": 2}, {"site_id": "2", "address": "11 Beachside Drive", "bedrooms": 3}]
    flat = {"address": "11 Beachside Dr", "bedrooms": 2, "title": "Beachside Villas #814"}
    assert address_match(flat, building)[0] == "matched"                                                   # the plain rule would tie it
    kind, _, note = address_match(flat, building, address_without_unit=True)
    assert kind == "ambiguous" and "daire numarası" in note                                              # RealJoy: a building, not tied


# ---- the 429 rule and the company read only through the extension -------------------------------------------------------------

class Statuses:
    """A transport answering the given statuses in turn (headers per answer)."""

    kind = "eklenti"

    def __init__(self, *answers):
        self.answers, self.sent = list(answers), 0

    def send(self, method, url, **kwargs):
        self.sent += 1
        status, headers = self.answers.pop(0)
        return status, url, headers, b"<html>ok</html>"


def session_with(transport, tmp_path):
    return ar.SiteSession(ar.RawStore(tmp_path / "manifest.json"), "realjoy.com", transport, lambda: False, gap=0, protected=True,
                          retry_429=CONFIG["inventory"]["retry_429"])


def test_a_429_waits_retry_after_or_a_minute_and_is_asked_again_at_most_twice(tmp_path, monkeypatch):
    waits = []
    monkeypatch.setattr(ar, "pause", lambda seconds, canceled: waits.append(seconds))
    transport = Statuses((429, {"Retry-After": "90"}), (429, {}), (200, {}))
    reply = session_with(transport, tmp_path).request("GET", LIST_URL, note="t")
    assert reply.status == 200 and transport.sent == 3 and [w for w in waits if w] == [90.0, 60.0]
    stopped = Statuses((429, {}), (429, {}), (429, {}), (200, {}))
    with pytest.raises(ar.CompanyStopped, match="art arda 3 kez HTTP 429") as stop:
        session_with(stopped, tmp_path).request("GET", LIST_URL, note="t")
    assert stopped.sent == 3 and stop.value.status == "stopped_blocked"                   # the fourth is never asked


def test_the_429_wait_reads_an_http_date_and_is_capped():
    assert ar.retry_after("120", 60) == 120 and ar.retry_after(None, 60) == 60 and ar.retry_after("999999", 60) == ar.RETRY_AFTER_MAX
    assert 0 <= ar.retry_after("Wed, 21 Oct 2015 07:28:00 GMT", 60) <= 1                  # a date in the past: no wait


def realjoy_site():
    return site("realjoy.com", "realjoy", protected=CONFIG["protected"], inventory=json.dumps(CONFIG["inventory"], ensure_ascii=False))


LISTINGS = [bd(1, "https://www.realjoy.com/rentals/old-link-1", address="35 Tupelo St", bedrooms=4, sleeps=10, title="Seaside cottage"),
            bd(2, "https://www.realjoy.com/rentals/old-link-2", address="37 Tupelo St", bedrooms=4, title="Sea La Vie Seaside Main House")]
WINDOWS = [{"window_key": "jan", "label": "Ocak 2027", "checkin": "2027-01-09", "checkout": "2027-01-16"},
           {"window_key": "apr", "label": "Nisan 2027", "checkin": "2027-04-10", "checkout": "2027-04-17"},
           {"window_key": "jun", "label": "Haziran 2027", "checkin": "2027-06-05", "checkout": "2027-06-12"}]


class ExtensionSide:
    """The extension for the collector: `without_fallback` gives a transport answering from the fixtures; every request is kept."""

    kind = "eklenti"

    def __init__(self, ready=True):
        self.ready, self.sent, self.opened, self.methods = ready, [], [], {}

    def extension_ready(self):
        return self.ready

    def without_fallback(self, domain, url, canceled, timeout):
        self.opened.append(url)
        return self

    def __call__(self, *args):
        raise AssertionError("a company read only through the extension never reaches the program's own browser")

    def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
        self.sent.append((method, url, dict(data) if data else None))
        if url == LIST_URL:
            body = two_parts()
        elif url.endswith("/ajax/results/scroll"):
            body = fixture("kaydirma.html")
        elif url == HOME_URL:
            body = fixture("ev-1806.html")
        elif url.endswith("/ajax/quote"):
            body = fixture("fiyat.html") if data["checkin"] == "01/09/2027" else "No"
        else:
            raise AssertionError(f"unexpected request {method} {url}")
        return 200, url, {"content-type": "text/html"}, body.encode("utf-8")

    def close(self):
        pass


def run_realjoy(tmp_path, verifier):
    def program(request):
        raise AssertionError(f"the program's own client asked {request.url}")
    config = {"sites": [realjoy_site()], "windows": WINDOWS, "input": {"run_id": "lodging-run", "searched_on": "2026-11-16", "listings": LISTINGS}}
    with httpx.Client(transport=httpx.MockTransport(program)) as http:
        return ar.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config, client=http, verifier=verifier,
                          today=date(2026, 11, 18))


def test_realjoy_is_read_only_through_the_extension_from_its_list_page(tmp_path, monkeypatch):
    monkeypatch.setattr(ar, "pause", lambda seconds, canceled: None)
    side = ExtensionSide()
    result = run_realjoy(tmp_path, side)
    company = result.related["companies"][0]
    assert company["status"] == "done" and company["inventory_count"] == 24 and side.opened == [LIST_URL]   # the list page, not a dead link
    rows = {r["lodging_id"]: r for r in result.records}
    assert (rows[1]["page_status"], rows[1]["match_method"], rows[1]["site_listing_id"]) == ("matched", "address", "1806")
    assert rows[2]["page_status"] == "not_found" and "aday yok" in rows[2]["match_note"]          # the similar name is not tied
    quotes = {q["window_key"]: q for q in result.related["quotes"]}
    assert quotes["jan"]["status"] == "priced" and quotes["jan"]["total"] == 8759.05 and quotes["jan"]["adults"] is None
    assert quotes["apr"]["status"] == "unavailable" and quotes["jun"]["rule_source"] == "takvim"
    posts = [(url, fields) for method, url, fields in side.sent if method == "POST"]
    assert [u.rsplit("/", 1)[1] for u, _ in posts] == ["scroll", "quote", "quote"]                # June was not asked
    assert all(allowed_by_configuration(httpx.URL(u).path, f) is None for u, f in posts)
    assert not any("old-link" in url for _, url, _ in side.sent)                                    # the dead Book>Direct links are not asked


@pytest.mark.parametrize("ready", [None, False])
def test_realjoy_is_skipped_and_recorded_when_the_extension_is_not_connected(tmp_path, ready):
    verifier = None if ready is None else ExtensionSide(ready=ready)
    result = run_realjoy(tmp_path, verifier)
    company = result.related["companies"][0]
    assert company["status"] == "verification_unavailable" and company["message"] == ar.EXTENSION_ONLY_SKIP and company["request_count"] == 0
    assert all(r["message"] for r in result.records) and result.related["quotes"] == []
    assert verifier is None or (verifier.sent == [] and verifier.opened == [])


def test_the_estimate_counts_realjoys_list_and_its_20_seconds():
    listings = [{"url": f"https://www.realjoy.com/x/{i}"} for i in range(61)]
    added = ar.new_site_estimate([{**realjoy_site(), "aliases": "[]"}], listings, set(), 12)[0]
    assert added["requests"] == 61 * (1 + 12 * 1) + 26                                  # dead links: no link page; home page and 12 weeks; the list
    assert added["seconds"] == int(added["requests"] * (20 + ar.ANSWER_SECONDS)) and added["protected"]
