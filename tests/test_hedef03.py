"""HEDEF-03: the seven rental companies whose prices were missing, and "Seçili şirketleri yeniden oku".

- the allowed list of the page's own queries now holds the price question of 30aescapes.com, oceanreefresorts.com,
  panhandlegetaways.com (Track: each page's own dates form) and rosemarybeach.com (Streamline: the fields in the address, only the
  plugin's list/availability/price methods); the same rules on both sides (studio/extension_queries.py, eklenti/logic.js);
- the Track reader posts the page's form in the page's order (cut from the pages of the night of 26–27 November 2026);
- Vacasa's lower-case "error" answer is a stay rule, not a missing price (the night's real answers);
- a page the extension's fetch cannot get (another subdomain, an http address) is opened in the tab (Alys Beach);
- a verification page met again inside the extension is passed in the tab and the question asked once more (RealJoy, the night's
  real Cloudflare page);
- the extension lane reads several companies at once, each by one lane worker;
- a run of the chosen companies: the others are carried from the base version unchanged, the chosen ones are read again, the version
  is whole; the company rows keep their own query day.
Fixtures (tests/fixtures/hedef03/) are cut from the raw copy of the night's run (data/raw/b8055d2a…).
"""
import gzip
import json
import re
import threading
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from studio import extension as ext
from studio import extension_queries as eq
from studio.destinations import thirty_a
from studio.sources import agency_rates as ar
from studio.sources.agency_adapters import ADAPTERS
from studio.sources.extension_reader import ExtensionTransport

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures" / "hedef03"
QUERIES = thirty_a.AGENCY_SITE_QUERIES_V26
TRACK = ADAPTERS["track"]
JAN = {"window_key": "ay-2027-01", "checkin_date": date(2027, 1, 9), "checkout_date": date(2027, 1, 16), "nights": 7}
MAY = {"window_key": "ay-2027-05", "checkin_date": date(2027, 5, 15), "checkout_date": date(2027, 5, 22), "nights": 7}


def text(name):
    data = (FIX / name).read_bytes()
    return (gzip.decompress(data) if name.endswith(".gz") else data).decode("utf-8")


def allowed(domain):
    return [eq.normalize({**q, "alan_adi": domain}) for q in QUERIES[domain]]


class Answer:
    def __init__(self, status, body, url):
        self.status, self.body, self.url, self.sha256, self.location, self.hops = status, body.encode("utf-8"), url, "x" * 64, None, []

    @property
    def text(self):
        return self.body.decode("utf-8")


class Session:
    """A company session for an adapter alone: every request is kept; `answer(method, url, data, params)` gives (status, body)."""

    def __init__(self, answer):
        self.answer, self.asked = answer, []

    def request(self, method, url, *, note, params=None, data=None, json=None, headers=None):
        self.asked.append({"method": method, "url": url, "data": dict(data) if data is not None else None, "params": params, "headers": headers})
        status, body = self.answer(method, url, data, params)
        return Answer(status, body, url)


# ---- Track: the page's own form ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("domain, page, url", [
    ("30aescapes.com", "30aescapes-wave-n-sea.html.gz", "https://www.30aescapes.com/rentals/wave-n-sea"),
    ("oceanreefresorts.com", "oceanreef-seabiscuit.html.gz", "https://www.oceanreefresorts.com/vacation-rentals/seabiscuit/"),
    ("panhandlegetaways.com", "panhandle-sanibel.html.gz", "https://www.panhandlegetaways.com/vacation-rentals/30a-beach-house-sanibel")])
def test_each_track_site_posts_its_own_form_in_the_pages_order_and_the_list_allows_it(domain, page, url):
    info = TRACK.parse_page(text(page), url)
    assert list(info["fields"]) == QUERIES[domain][0]["alanlar"]          # the form as the page has it (the list was read from it)
    assert info["quote_url"] == origin(url) + "/ajax/quote"
    free = next(w for w in (JAN, MAY, {**JAN, "window_key": "x", "checkin_date": date(2027, 9, 11), "checkout_date": date(2027, 9, 18)},
                            {**JAN, "window_key": "y", "checkin_date": date(2027, 11, 13), "checkout_date": date(2027, 11, 20)})
                if not TRACK.taken_nights(info, w))
    session = Session(lambda *a: (200, "No"))
    result = TRACK.quote(session, info, free)
    sent = session.asked[0]
    assert result["status"] == "unavailable" and list(sent["data"]) == QUOTE_ORDER[domain]
    assert sent["data"]["checkin"] == free["checkin_date"].strftime("%m/%d/%Y") and sent["data"]["propertyID"] == info["site_id"]
    query = {"alan_adi": domain, "yol": "/ajax/quote", "yontem": "POST", "alanlar": sent["data"]}
    assert eq.refusal(query, allowed(domain)) is None
    assert eq.refusal(query, allowed("30aescapes.com" if domain != "30aescapes.com" else "oceanreefresorts.com")) is not None


QUOTE_ORDER = {d: q[0]["alanlar"] for d, q in QUERIES.items() if q[0]["yol"] == "/ajax/quote"}


def origin(url):
    return re.match(r"https://[^/]+", url).group(0)


def test_the_track_form_differs_by_site_as_the_pages_show():
    assert "hash" not in QUERIES["oceanreefresorts.com"][0]["alanlar"]
    assert QUERIES["panhandlegetaways.com"][0]["alanlar"][-1] == "numDaysForAvailailityData"
    assert QUERIES["30aescapes.com"][0]["alanlar"] == thirty_a.REALJOY_QUOTE_FIELDS          # the same Track form as RealJoy's


# ---- Streamline (rosemarybeach.com): the fields in the address -------------------------------------------------------------------

STREAM = ADAPTERS["streamline"]


def test_streamline_asks_in_the_address_with_the_pages_compact_json_and_only_its_methods():
    info = STREAM.parse_page(text("rosemary-seaforth.html"), "https://rosemarybeach.com/rentals/availability/seaforth-cottage/")
    assert info["site_id"] == "411533" and info["ajax_url"] == "https://rosemarybeach.com/wp-admin/admin-ajax.php"
    answers = iter([json.dumps({"data": {"id": 1}}), json.dumps({"data": {"price": 16912, "total": 19044.04, "required_fees": [], "taxes_details": []}})])
    session = Session(lambda *a: (200, next(answers)))
    result = STREAM.quote(session, info, JAN)
    assert result["total"] == 19044.04
    for sent in session.asked:
        assert sent["data"] is None and list(sent["params"]) == ["action", "params"]          # nothing in the body: all in the address
        assert sent["params"]["params"].startswith('{"methodName":"') and ": " not in sent["params"]["params"]
        query = {"alan_adi": "rosemarybeach.com", "yol": "/wp-admin/admin-ajax.php", "yontem": "POST", "alanlar": sent["params"],
                 "alanlar_yeri": "adres"}
        assert eq.refusal(query, allowed("rosemarybeach.com")) is None
    base = {"alan_adi": "rosemarybeach.com", "yol": "/wp-admin/admin-ajax.php", "yontem": "POST", "alanlar_yeri": "adres"}
    other = '{"methodName":"CreateReservation","params":{"unit_id":1}}'
    assert "değeri" in eq.refusal({**base, "alanlar": {"action": "streamlinecore-api-request", "params": other}}, allowed("rosemarybeach.com"))
    assert "değeri" in eq.refusal({**base, "alanlar": {"action": "other-action", "params": session.asked[0]["params"]["params"]}},
                                  allowed("rosemarybeach.com"))
    assert "yerde değil" in eq.refusal({**base, "alanlar_yeri": "govde", "alanlar": session.asked[0]["params"]}, allowed("rosemarybeach.com"))


class QuerySession:
    """The extension session for a transport: `query` and `page` are kept and answered."""

    domain = "rosemarybeach.com"

    def __init__(self, answer=None, fail_requests=False, page=None):
        self.queries, self.pages, self.requests = [], [], []
        self.answer, self.fail_requests, self.page_answer = answer, fail_requests, page

    def query(self, path, method, fields, *, page=None, place=None, canceled=None):
        self.queries.append((path, method, dict(fields), place))
        return {"http_durumu": 200, "son_adres": f"https://{self.domain}{path}", "basliklar": {}, "govde": self.answer or b"{}"}

    def request(self, method, url, *, headers=None, body=None, canceled=None):
        self.requests.append(url)
        if self.fail_requests:
            raise ext.ExtensionError("Failed to fetch")
        return 200, url, {}, b"ok"

    def page(self, url, wait=None, *, canceled=None):
        self.pages.append(url)
        return self.page_answer(url) if self.page_answer else {"durum": "tamam", "http_durumu": 200, "son_adres": url, "html": b"<html>page</html>"}

    def close(self):
        pass


def test_the_extension_transport_sends_a_post_with_address_fields_as_the_pages_own_query():
    session = QuerySession()
    transport = ExtensionTransport(session)
    params = {"action": "streamlinecore-api-request", "params": '{"methodName":"GetPreReservationPrice","params":{}}'}
    transport.send("POST", "https://rosemarybeach.com/wp-admin/admin-ajax.php", params=params, headers={"Content-Type": "application/json"})
    assert session.queries == [("/wp-admin/admin-ajax.php", "POST", params, "adres")]


def test_the_extension_and_the_program_hold_the_same_new_lists():
    logic = (ROOT / "eklenti" / "logic.js").read_text(encoding="utf-8")

    def js_list(name):
        return re.findall(r'"([^"]+)"', re.search(rf"export const {name} = \[(.*?)\];", logic, re.S).group(1))
    assert js_list("PLACES") == list(eq.PLACES) and js_list("CONTENT_TYPES") == list(eq.CONTENT_TYPES)
    manifest = json.loads((ROOT / "eklenti" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == ext.EXPECTED_VERSION == "0.22.0"


def test_the_migration_gives_the_four_companies_their_questions_and_keeps_an_existing_list(tmp_path):
    from studio.database import Database
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    found = {(q["alan_adi"], q["yol"]) for q in db.extension_queries()}
    assert {("30aescapes.com", "/ajax/quote"), ("oceanreefresorts.com", "/ajax/quote"), ("panhandlegetaways.com", "/ajax/quote"),
            ("rosemarybeach.com", "/wp-admin/admin-ajax.php"), ("realjoy.com", "/ajax/quote")} <= found
    with db.connect() as con:
        columns = {r[1] for r in con.execute("PRAGMA table_info(agency_rate_companies)")}
        rose = json.loads(con.execute("SELECT inventory FROM destination_agency_sites WHERE domain='rosemarybeach.com'").fetchone()[0])
        track = json.loads(con.execute("SELECT inventory FROM destination_agency_sites WHERE domain='30aescapes.com'").fetchone()[0])
    assert {"queried_on", "carried_from"} <= columns
    assert rose["source"] == "platform" and rose["extension_queries"][0]["alanlar_yeri"] == "adres"   # the list is kept, the question added
    assert not ar.has_list(track) and ar.has_list(rose)                                               # a question alone is not a company list


# ---- Vacasa: the lower-case error ------------------------------------------------------------------------------------------------

def test_vacasas_lower_case_error_is_the_stay_rule_and_a_priced_answer_keeps_its_total():
    vacasa = ADAPTERS["vacasa"]
    info = {"site_id": "1020441", "origin": "https://www.vacasa.com", "page_url": "https://www.vacasa.com/unit/1020441"}
    rule = vacasa.quote(Session(lambda *a: (200, text("vacasa-min-stay.json"))), info, JAN)
    assert rule["status"] == "restricted" and "min-stay-not-met" in rule["message"] and rule.get("total") is None
    priced = vacasa.quote(Session(lambda *a: (200, text("vacasa-priced.json.gz"))), {**info, "site_id": "1012657"}, JAN)
    assert priced["status"] == "priced" and priced["rent"] == 1120.22 and priced["total"] == 1342.0


# ---- Alys Beach: a page the tab's fetch cannot get ---------------------------------------------------------------------------------

def test_a_page_the_tabs_fetch_cannot_get_is_opened_in_the_tab():
    session = QuerySession(fail_requests=True)
    session.domain = "alysbeach.com"
    status, final, headers, body = ExtensionTransport(session).send("GET", "http://www.alysbeach.com", headers={"Accept": "text/html"})
    assert session.requests == ["http://www.alysbeach.com"] and session.pages == ["http://www.alysbeach.com"]
    assert (status, body) == (200, b"<html>page</html>")
    session = QuerySession(fail_requests=True)            # a JSON request of the page's script is not turned into a page
    with pytest.raises(httpx.NetworkError):
        ExtensionTransport(session).send("GET", "https://vacation.alysbeach.com/?vrpjax=1", headers={"Accept": "application/json"})
    assert session.pages == []


# ---- RealJoy: the verification asked again inside the extension -------------------------------------------------------------------

def test_a_second_verification_inside_the_extension_is_passed_in_the_tab_and_the_question_asked_again(tmp_path, monkeypatch):
    from tests import test_gorev25 as g25
    monkeypatch.setattr(ar, "pause", lambda seconds, canceled: None)
    challenge = text("realjoy-challenge-403.html.gz")

    class Side(g25.ExtensionSide):
        def __init__(self):
            super().__init__()
            self.challenged, self.reverified = False, []

        def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
            if url.endswith("/ajax/quote") and not self.challenged:
                self.challenged = True
                self.sent.append((method, url, dict(data)))
                return 403, url, {"content-type": "text/html", "cf-mitigated": "challenge"}, challenge.encode("utf-8")
            return super().send(method, url, params=params, data=data, json_body=json_body, headers=headers)

        def reverify(self, url):
            self.reverified.append(url)
            return True

    side = Side()
    result = g25.run_realjoy(tmp_path, side)
    company = result.related["companies"][0]
    assert company["status"] == "done" and company["reverified"] == 1 and side.reverified == [g25.LIST_URL]
    quotes = {q["window_key"]: q for q in result.related["quotes"]}
    assert quotes["jan"]["status"] == "priced" and quotes["jan"]["total"] == 8759.05          # asked again after the check

    class Stubborn(Side):
        def reverify(self, url):
            self.reverified.append(url)
            return False
    stubborn = Stubborn()
    result = g25.run_realjoy(tmp_path / "b", stubborn)
    assert result.related["companies"][0]["status"] == "stopped_blocked" and len(stubborn.reverified) == 1


def test_the_reverification_has_a_limit(tmp_path):
    run = ar.CompanyRun.__new__(ar.CompanyRun)
    run.result, run.reverify_lock, run.browser_url = {"reverified": ar.REVERIFY_LIMIT}, threading.Lock(), "https://x.test/"
    run.browser = type("B", (), {"reverify": lambda self, url: True})()
    assert run.reverify() is False


# ---- the extension lane: several companies at once ---------------------------------------------------------------------------------

def test_the_extension_lane_reads_several_companies_at_once_each_by_one_worker(monkeypatch):
    from studio.sources import agency_workers as AW
    from studio import workers as W
    assert AW.EXTENSION_LANES == ext.PARALLEL_SESSIONS >= 6
    states = []
    for name in ("a.test", "b.test", "c.test"):
        state = AW.CompanyState.__new__(AW.CompanyState)
        state.finished, state.pending, state.inflight = False, [object()], set()
        state.lane, state.lane_started, state.lane_owner = W.LANE_EXTENSION, False, None
        states.append(state)
    scheduler = AW.Scheduler.__new__(AW.Scheduler)
    one, two = (type("Wk", (), {"lane": W.LANE_EXTENSION})() for _ in range(2))
    assert scheduler.eligible(one, states[0])
    states[0].lane_owner, states[0].lane_started = one, True
    assert scheduler.eligible(one, states[0]) and not scheduler.eligible(two, states[0])     # a company is read by one lane worker
    assert scheduler.eligible(two, states[1])                                                 # the next company by another, at once


def test_the_extension_takes_as_many_jobs_as_the_program_says():
    logic = (ROOT / "eklenti" / "logic.js").read_text(encoding="utf-8")
    background = (ROOT / "eklenti" / "background.js").read_text(encoding="utf-8")
    assert "parallel = L.parallelOf(answer.en_cok)" in background and "running.size < parallel" in background
    assert re.search(r"export const MAX_PARALLEL = (\d+);", logic).group(1) == "8"


# ---- "Seçili şirketleri yeniden oku" ----------------------------------------------------------------------------------------------

def base_of(result, run_id="base-run"):
    """A collected result in the shape version_rows() gives (as the store would have written it)."""
    snapshot = result.related["snapshot"]
    return {"run_id": run_id, "snapshot": {**snapshot, "run_id": run_id}, "windows": result.related["windows"],
            "companies": [{**c, "run_id": run_id, "queried_on": snapshot["queried_on"]} for c in result.related["companies"]],
            "listings": {r["lodging_id"]: {**r, "run_id": run_id} for r in result.records},
            "quotes": [{**q, "run_id": run_id} for q in result.related["quotes"]],
            "own_listings": result.related["own_listings"], "own_quotes": result.related["own_quotes"],
            "published": result.related["published"]}


def selected_run(tmp_path, mock, domains, base, today):
    from tests import test_agency_rates as tr
    config = {**tr.config(), "selected": {"domains": domains, "base": base}}
    with httpx.Client(transport=httpx.MockTransport(mock)) as client:
        return ar.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config, client=client, today=today)


def test_a_run_of_the_chosen_companies_carries_the_others_unchanged_and_reads_the_chosen_again(tmp_path, monkeypatch):
    from tests import test_agency_rates as tr
    monkeypatch.setattr(ar, "REQUEST_GAP", 0)
    monkeypatch.setattr(ar, "RETRY_PAUSE", 0)
    first = tr.run(tmp_path / "a")
    base = base_of(first)
    asked = []

    def changed(request):            # the chosen company now says "No" to every week; anything else asked is a mistake
        asked.append(request.url.host)
        if request.url.host == "www.track.example" and request.url.path == "/ajax/quote":
            return httpx.Response(200, text="No")
        return tr.Sites()(request)
    later = date(2026, 10, 9)
    second = selected_run(tmp_path / "b", changed, ["track.example"], base, later)
    assert set(asked) == {"www.track.example"}                                       # only the chosen company was asked
    companies = {c["domain"]: c for c in second.related["companies"]}
    assert set(companies) == {c["domain"] for c in first.related["companies"]}       # the version is whole
    for domain in ("rescms.example", "stream.example", "router.example"):
        old = next(c for c in first.related["companies"] if c["domain"] == domain)
        drop = ("queried_on", "carried_from", "run_id")
        assert {k: v for k, v in companies[domain].items() if k not in drop} == {k: v for k, v in old.items() if k not in drop}
        assert companies[domain]["carried_from"] == "base-run" and companies[domain]["queried_on"] == TODAY_ISO
    assert companies["track.example"]["carried_from"] is None and companies["track.example"]["queried_on"] == later.isoformat()
    old_quotes, new_quotes = tr.quotes_of(first), tr.quotes_of(second)
    assert set(old_quotes) == set(new_quotes)                                         # the same listings and weeks
    for key, quote in new_quotes.items():
        domain = second.related["companies"] and {r["lodging_id"]: r["domain"] for r in second.records}[key[0]]
        if domain == "track.example":
            assert quote["status"] == "unavailable"                                   # read again: changed
        else:
            assert {k: v for k, v in quote.items() if k not in ("run_id", "domain")} == \
                   {k: v for k, v in old_quotes[key].items() if k not in ("run_id", "domain")}
    assert any(old_quotes[k]["status"] == "priced" for k in old_quotes if k[0] in (20, 21, 22))   # the old track prices did change
    rows_before = {r["lodging_id"]: r for r in first.records}
    for row in second.records:
        if row["domain"] != "track.example":
            assert {k: v for k, v in row.items() if k != "run_id"} == rows_before[row["lodging_id"]]
    note = second.metadata["secili_okuma"]
    assert note["sirketler"] == ["track.example"] and note["taban_surum"] == "base-run" and note["tasinan_sirket"] == 3
    assert [w["window_key"] for w in second.related["windows"]] == [w["window_key"] for w in first.related["windows"]]


TODAY_ISO = "2026-10-08"


def test_a_selection_on_another_lodging_run_or_an_unknown_company_is_refused(tmp_path):
    from tests import test_agency_rates as tr
    base = {"run_id": "b", "snapshot": {"lodging_run_id": "older-lodging-run", "queried_on": "2026-10-01"}, "windows": []}
    with pytest.raises(ar.SourceError, match="Book>Direct çekimi"):
        selected_run(tmp_path, tr.Sites(), ["track.example"], base, date(2026, 10, 9))
    with pytest.raises(ar.SourceError, match="yapılandırmada yok"):
        selected_run(tmp_path, tr.Sites(), ["nowhere.example"], {**base, "snapshot": {**base["snapshot"], "lodging_run_id": "lodging-run"}},
                     date(2026, 10, 9))


def test_the_stored_selected_version_is_whole_and_the_base_is_untouched(tmp_path, monkeypatch):
    """Through the database: the base version is stored, a run of one company completes it; version_rows reads both back."""
    from studio.database import Database
    from tests import test_agency_rates as tr
    monkeypatch.setattr(ar, "REQUEST_GAP", 0)
    monkeypatch.setattr(ar, "RETRY_PAUSE", 0)
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    connector = ar.AgencyRatesConnector()
    first = tr.run(tmp_path / "a")
    with db.connect() as con:
        con.execute("PRAGMA foreign_keys=OFF")
        connector.store_records(con, "base-run", first.records, first.related)
        base = ar.version_rows(con, "base-run")
    assert {c["domain"]: c["queried_on"] for c in base["companies"]}["track.example"] == TODAY_ISO
    second = selected_run(tmp_path / "b", tr.Sites(), ["track.example"], base, date(2026, 10, 9))
    with db.connect() as con:
        con.execute("PRAGMA foreign_keys=OFF")
        connector.store_records(con, "new-run", second.records, second.related)
        again, new = ar.version_rows(con, "base-run"), ar.version_rows(con, "new-run")
    assert again == base                                                                  # the base version is not touched
    assert len(new["listings"]) == len(base["listings"]) and len(new["companies"]) == len(base["companies"])
    assert len(new["quotes"]) == len(base["quotes"])
    days = {c["domain"]: (c["queried_on"], c["carried_from"]) for c in new["companies"]}
    assert days["track.example"] == ("2026-10-09", None) and days["rescms.example"] == (TODAY_ISO, "base-run")


def test_a_site_that_once_showed_a_verification_goes_to_the_extension_lane_when_the_extension_is_paired():
    from studio.sources import agency_workers as AW
    from studio import workers as W

    def run(protected_config, extension_only=False):
        return type("R", (), {"extension_only": extension_only, "protected": 1, "site": {"protected_config": protected_config}})()
    assert AW.lane_of(run(0), extension_paired=True) == W.LANE_EXTENSION          # 30aescapes.com and kin: marked browser hosts
    assert AW.lane_of(run(0), extension_paired=False) == W.LANE_BROWSER
    assert AW.lane_of(run(1), extension_paired=True) == W.LANE_BROWSER             # oversee.us, exclusive30a.com: the configuration says so
    assert AW.lane_of(run(0, extension_only=True)) == W.LANE_EXTENSION


# ---- the trial's real answers (data/deneme/20261127-151712, through the user's extension) ------------------------------------------

def test_the_trials_real_track_answers_through_the_extension_give_the_price():
    page = TRACK.parse_page(text("panhandle-sanibel.html.gz"), "https://www.panhandlegetaways.com/vacation-rentals/30a-beach-house-sanibel")
    priced = TRACK.quote(Session(lambda *a: (200, text("panhandle-quote-deneme.html.gz"))), page, JAN)
    assert (priced["status"], priced["rent"], priced["total"]) == ("priced", 4224.3, 5224.02)
    assert [f["name"] for f in priced["fees"]] == ["Cleaning Fee"] and priced["taxes"] == 559.72
    page = TRACK.parse_page(text("oceanreef-seabiscuit.html.gz"), "https://www.oceanreefresorts.com/vacation-rentals/seabiscuit/")
    total_only = TRACK.quote(Session(lambda *a: (200, text("oceanreef-quote-deneme.html.gz"))), page, JAN)
    assert (total_only["status"], total_only["rent"], total_only["total"]) == ("priced", None, 1941.59)     # the site shows the total only


def test_the_trials_real_streamline_answers_through_the_extension_give_the_price():
    info = STREAM.parse_page(text("rosemary-seaforth.html"), "https://rosemarybeach.com/rentals/availability/seaforth-cottage/")
    answers = iter([text("rosemary-verify-deneme.json.gz"), text("rosemary-price-deneme.json.gz")])
    result = STREAM.quote(Session(lambda *a: (200, next(answers))), info, JAN)
    assert (result["status"], result["rent"], result["total"]) == ("priced", 16912.0, 19044.04)
    assert {f["name"] for f in result["fees"]} == {"Damage Fee", "Reservation Fee"}
    assert any(e["name"] == "Travel Insurance" for e in result["excluded_items"])                      # optional, not in the total
