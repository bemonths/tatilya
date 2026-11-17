"""GÖREV-22: the region-block measurement (three classes), the readers of the two region-blocked companies (360 Blue: Natural
Retreats' booking engine; Vacasa), the proxy only for the listed domains, 30A Beach Girls as the company's own inventory (the
neighbourhood only from the site's own place name; no home counted twice), the estimate, the evidence pack and the 21 -> 22 migration.

The fixtures (tests/fixtures/gorev22/) are cut from the raw copies of the task's own reading of 16-17 November 2026
(work/gorev-22/fikstur.py): long texts, images and unrelated parts dropped, no value changed. Nothing here reaches a site or a proxy.
"""
import json
import sqlite3
from datetime import date
from pathlib import Path

import httpx
import pytest

from studio import proxy as P
from studio.database import SCHEMA_VERSION, Database
from studio.destinations import thirty_a
from studio.evidence import blocks
from studio.sources import agency_adapters as aa
from studio.sources import agency_rates as ar
from studio.sources import region_probe as probe
from tests import legacy
from tests.test_agency_v2 import bd, site
from tests.test_proxy import FakeRegion

FIX = Path(__file__).parent / "fixtures" / "gorev22"
TODAY = date(2026, 11, 17)
WINDOWS = [{"window_key": "apr", "label": "Nisan 2027", "checkin": "2027-04-10", "checkout": "2027-04-17"},
           {"window_key": "mar", "label": "Mart 2027", "checkin": "2027-03-06", "checkout": "2027-03-13"}]
APRIL = {"window_key": "apr", "checkin_date": date(2027, 4, 10), "checkout_date": date(2027, 4, 17), "nights": 7}
MARCH = {"window_key": "mar", "checkin_date": date(2027, 3, 6), "checkout_date": date(2027, 3, 13), "nights": 7}
OPTIONS = thirty_a.AGENCY_SITE_OPTIONS_V22


def text(name):
    return (FIX / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    for name in ("REQUEST_GAP", "RETRY_PAUSE", "PROXY_GAP"):
        monkeypatch.setattr(ar, name, 0)


class Sides:
    """Two mock transports standing for the two ways out: `direct` and `through the proxy`; each records the hosts it was asked."""

    def __init__(self, handler):
        self.handler, self.direct, self.proxied = handler, [], []

    def client(self, log):
        def answer(request):
            log.append(str(request.url))
            return self.handler(request)
        return httpx.MockTransport(answer)

    def install(self, monkeypatch):
        def proxy_client(proxy, hosts=None):
            through = self.client(self.proxied)
            mounts = {pattern: through for host in hosts for pattern in (f"all://{host}", f"all://*.{host}")}
            return httpx.Client(mounts=mounts, transport=self.client(self.direct))
        monkeypatch.setattr(ar, "proxy_client", proxy_client)


def collect(tmp_path, handler, sites, listings, *, region=None, windows=WINDOWS):
    config = {"sites": sites, "windows": windows, "input": {"run_id": "lodging-run", "searched_on": "2026-11-16", "listings": listings}}
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return ar.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config, client=client, today=TODAY,
                          region=region)


def page(body, status=200, **headers):
    return httpx.Response(status, content=body.encode("utf-8"), headers={"content-type": "text/html; charset=utf-8", **headers})


def data(body, status=200):
    return httpx.Response(status, content=body.encode("utf-8"), headers={"content-type": "application/json"})


# --- Adım 2: the measurement ----------------------------------------------------------------------------------------------------

def test_region_block_is_a_refusal_directly_and_a_normal_answer_through_the_proxy():
    """vacasa.com (CloudFront's country block) and 360blue.com (Cloudflare's block page) as they answered on 17 November 2026."""
    vacasa = probe.classify(probe.answer(403, "ERROR: The request could not be satisfied", text("olcum-vacasa-dogrudan-403.html")),
                            probe.answer(200, "Dunes of Seagrove | Santa Rosa Beach | Vacasa", "<html><body>" + "Condo in Santa Rosa Beach. " * 300 + "</body></html>"))
    assert (vacasa["sinif"], vacasa["dogrudan"], vacasa["proxy"]) == ("bolge_engeli", "bolge", "icerik")
    blue = probe.classify(probe.answer(403, "Attention Required! | Cloudflare", text("olcum-360blue-dogrudan-403.html")),
                          probe.answer(301, "301 Moved Permanently", "<html><body>Moved</body></html>"))
    assert (blue["sinif"], blue["dogrudan"]) == ("bolge_engeli", "ret") and "proxy üzerinden site normal yanıt veriyor" in blue["neden"]
    silent = probe.classify(probe.answer(error="ConnectTimeout"), probe.answer(200, "Home", "<html><body>" + "Welcome. " * 200 + "</body></html>"))
    assert silent["sinif"] == "bolge_engeli" and silent["dogrudan"] == "yok"


def test_the_same_refusal_through_the_proxy_is_not_a_region_block():
    """sandestin.com's "Access denied" page came back both ways; a verification both ways and a site that answers both ways neither."""
    denied = text("olcum-sandestin-403.html")
    same = probe.classify(probe.answer(403, "Access denied | Sandestin Golf and Beach Resort", denied),
                          probe.answer(403, "Access denied | Sandestin Golf and Beach Resort", denied))
    assert same["sinif"] == "bolge_engeli_degil" and "proxy kullanılmaz" in same["neden"]
    challenge = "<html><head><title>Just a moment...</title></head><body>Checking your browser before accessing</body></html>"
    assert probe.classify(probe.answer(403, "Just a moment...", challenge), probe.answer(403, "Just a moment...", challenge))["sinif"] == "bolge_engeli_degil"
    assert probe.classify(probe.answer(403, "Attention Required! | Cloudflare", text("olcum-360blue-dogrudan-403.html")),
                          probe.answer(403, "Just a moment...", challenge))["sinif"] == "bolge_engeli_degil"      # a block here, a verification there
    moved = probe.answer(301, None, "")                                                    # wyndhamvacationrentals.com: the same redirect both ways
    assert probe.classify(moved, moved)["sinif"] == "bolge_engeli_degil"
    assert probe.classify(probe.answer(403, "Access denied", denied), probe.answer(error="ProxyError"))["sinif"] == "bolge_engeli_degil"


def test_no_site_either_way_and_a_parked_domain_are_no_site():
    """rentals.cottagerentalagency.com has no DNS record; outdoorshower30a.com timed out directly and gave its registrar's page through
    the proxy — that page is not the site."""
    gone = probe.classify(probe.answer(error="ConnectError: getaddrinfo failed"), probe.answer(error="ProxyError"))
    assert gone["sinif"] == "site_yok"
    parked = probe.classify(probe.answer(error="ConnectTimeout"),
                            probe.answer(200, "Registrant WHOIS contact information verification | Namecheap.com", text("olcum-outdoorshower-proxy-200.html")))
    assert (parked["sinif"], parked["proxy"]) == ("site_yok", "yok")
    assert probe.classify(probe.answer(502, "Bad Gateway", ""), probe.answer(503, "Unavailable", ""))["sinif"] == "site_yok"
    assert set(probe.LABELS) == set(probe.CLASSES)


def test_the_measurement_of_17_november_classifies_as_the_report_says():
    """The recorded answers of the task's own measurement (status, title, the page kind seen then) give the report's classes."""
    records = json.loads(text("olcum-kayitlari.json"))
    def side(record):
        html = {"bolge_engeli": text("olcum-vacasa-dogrudan-403.html"), "erisim_reddedildi": text("olcum-sandestin-403.html")}.get(record.get("kind"), "")
        if record.get("status") == 200 and "Namecheap" in (record.get("title") or ""):
            html = text("olcum-outdoorshower-proxy-200.html")
        return probe.answer(record.get("status"), record.get("title"), html, record["url"], record.get("error"))
    def result(domain):
        rows = records[domain]
        return probe.classify(side(next(r for r in rows if r["yol"] == "dogrudan")), side([r for r in rows if r["yol"] == "proxy"][-1]))["sinif"]
    assert {domain: result(domain) for domain in records} == {
        "360blue.com": "bolge_engeli", "vacasa.com": "bolge_engeli", "wyndhamvacationrentals.com": "bolge_engeli_degil",
        "cottagerentalagency.com": "bolge_engeli_degil", "rentals.cottagerentalagency.com": "site_yok", "sandestin.com": "bolge_engeli_degil",
        "outdoorshower30a.com": "site_yok", "golocalvr.com": "bolge_engeli_degil"}
    assert all(len(rows) <= 3 for rows in records.values())                               # the task's limit: three requests per domain


# --- Adım 3: 360 Blue (Natural Retreats' booking engine) ---------------------------------------------------------------------

class Session:
    def __init__(self, answers):
        self.answers, self.asked = list(answers), []

    def request(self, method, url, **kwargs):
        self.asked.append((url, kwargs.get("params")))
        status, body = self.answers.pop(0)
        reply = ar.Reply(status, url, {}, body.encode("utf-8"), "0" * 64)
        return reply


def test_name_address_takes_only_a_street_address_from_a_listing_name():
    assert aa.name_address('Seaside "Sea ya real soon" 73 Odessa Street') == "73 Odessa Street"
    assert aa.name_address("WaterColor 20 Goldenrod Circle #302") == "20 Goldenrod Circle #302"
    assert aa.name_address("Blue Mtn. Adagio Unit B-304 - 2421 W. Hwy 30A") == "2421 W. Hwy 30A"
    assert aa.name_address('Seaside "The Truman House" 31 Natchez street') == "31 Natchez street"
    assert aa.name_address("Callista Collection Home") is None and aa.name_address('Seaside "Forget Me Not"') is None and aa.name_address(None) is None


def test_nrbe_reads_the_page_the_list_and_the_quote():
    adapter = aa.ADAPTERS["nrbe"]
    url = "https://www.360blue.com/destinations/emerald-coast/walton-county/properties/seaside-sea-ya-real-soon-73-odessa-street-873"
    info = adapter.parse_page(text("nrbe-page.html"), url)
    assert info == {"site_id": "873", "origin": "https://www.360blue.com", "page_url": url}
    assert adapter.parse_page("<html><body class='page'>x</body></html>", url) is None
    assert adapter.unit_fields(text("nrbe-page.html"))["address"] == "73 Odessa Street"
    session = Session([(200, text("nrbe-units.json"))])
    units, replies = adapter.inventory(session, "https://www.360blue.com", OPTIONS["360blue.com"]["inventory"])
    assert "brandId=193&brandId=195" in session.asked[0][0] and "pageSize=-1" in session.asked[0][0] and len(replies) == 1
    home = next(u for u in units if u["site_id"] == "873")
    assert len(units) == 8 and all(u["address"] for u in units)
    assert (home["address"], home["bedrooms"], home["bathrooms"], home["sleeps"], home["latitude"]) == ("73 Odessa Street", 3.0, 3.0, 10.0, 30.321804)
    assert home["page"]["page_status"] == "matched" and home["page"]["info"]["site_id"] == "873"            # no page request is needed
    session = Session([(200, text("nrbe-calendar.json")), (200, text("nrbe-quote.json"))])
    quote = adapter.quote(session, dict(info), APRIL)
    assert session.asked[0][1] == {"unitId": "873", "startDate": "2027-01-01", "endDate": "2027-06-30"}
    assert session.asked[1][1] == {"unitId": "873", "arrivalDate": "2027-04-10", "departureDate": "2027-04-17", "adults": "2", "children": "0"}
    assert (quote["status"], quote["rent"], quote["taxes"], quote["total"], quote["fees"]) == ("priced", 6975.52, 837.09, 7812.61, None)
    assert quote["total_includes_taxes"] == 1 and len(quote["replies"]) == 2             # the site's own figures: sub-total + taxes = total


def test_nrbe_a_taken_week_is_unavailable_from_the_calendar_and_an_unexplained_error_is_no_price():
    adapter = aa.ADAPTERS["nrbe"]
    info = {"site_id": "873", "origin": "https://www.360blue.com", "page_url": "https://www.360blue.com/x-873"}
    session = Session([(200, text("nrbe-calendar.json"))])
    taken = adapter.quote(session, info, MARCH)                                          # 11 and 12 March are booked on the calendar
    assert (taken["status"], taken["available"]) == ("unavailable", 0) and "2 gecesini dolu" in taken["message"] and len(session.asked) == 1
    session = Session([(200, text("nrbe-quote.json"))])
    again = adapter.quote(session, info, APRIL)                                          # the calendar half is asked once per listing
    assert again["status"] == "priced" and "reservation-quotes" in session.asked[0][0]
    days = json.loads(text("nrbe-calendar.json"))
    free = json.dumps([{**d, "available": True} for d in days])
    session = Session([(200, free), (500, text("nrbe-quote-error.json"))])
    silent = adapter.quote(session, {**info, "calendar": {}}, MARCH)
    assert silent["status"] == "no_price" and silent["available"] is None and "An unexpected error has occurred" in silent["message"]
    with pytest.raises(aa.AdapterError):
        adapter.quote(Session([(200, free), (502, "<html>bad gateway</html>")]), {**info, "calendar": {}}, MARCH)
    with pytest.raises(aa.AdapterError):
        adapter.inventory(Session([(200, json.dumps({"results": [], "resultTotal": 9}))]), "https://www.360blue.com", OPTIONS["360blue.com"]["inventory"])


def nrbe_site(request):
    path = request.url.path
    if path == "/api/nrbe/units.json":
        return data(text("nrbe-units.json"))
    if path == "/api/nrbe/availability-calendar.json":
        return data(text("nrbe-calendar.json"))
    if path == "/api/nrbe/reservation-quotes.json":
        return data(text("nrbe-quote.json")) if request.url.params["arrivalDate"] == "2027-04-10" else data(text("nrbe-quote-error.json"), 500)
    pytest.fail(f"an address nobody should ask: {request.url}")


def test_a_region_blocked_company_is_read_through_the_proxy_its_old_links_are_not_asked_and_it_ties_by_address(tmp_path, monkeypatch):
    sides = Sides(nrbe_site)
    sides.install(monkeypatch)
    sites = [site("360blue.com", "nrbe", inventory=OPTIONS["360blue.com"]["inventory"])]
    listings = [bd(1, "https://www.360blue.com/rentals/properties/seaside-sea-ya-real-soon-73-odessa-street/", address="73 Odessa St", bedrooms=3),
                bd(2, "https://www.360blue.com/rentals/properties/blue-mountain-beach-sea-esta-391-blue-mountain-road/", address="391 Blue Mountain Road", bedrooms=4),
                bd(3, "https://360blue.com", address="790 North County Highway 393 #3B", bedrooms=None)]
    result = collect(tmp_path, lambda r: pytest.fail("a listed company's site is never asked directly"), sites, listings,
                     region=FakeRegion({"360blue.com"}, proxy=object()))
    rows = {r["lodging_id"]: r for r in result.records}
    assert rows[1]["page_status"] == "matched" and rows[1]["match_method"] == "address" and rows[1]["site_listing_id"] == "873"
    assert rows[1]["link_status"] == "not_found" and "73 odessa st" in rows[1]["match_note"]
    assert rows[2]["page_status"] == "not_found" and "eski ilan adresleri çalışmıyor" in rows[2]["message"] and "aday yok" in rows[2]["match_note"]
    assert rows[3]["page_status"] == "not_found" and "oda sayısı yok" in rows[3]["match_note"]
    quotes = {(q["lodging_id"], q["window_key"]): q for q in result.related["quotes"]}
    assert quotes[(1, "apr")]["total"] == 7812.61 and quotes[(1, "apr")]["status"] == "priced"
    assert quotes[(1, "mar")]["status"] == "unavailable" and quotes[(1, "mar")]["total"] is None
    assert not sides.direct and not any("/rentals/properties/" in url for url in sides.proxied)
    assert [url.split("?")[0].rsplit("/", 1)[1] for url in sides.proxied] == ["units.json", "availability-calendar.json", "reservation-quotes.json"]
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert all(entry["transport"] == "proxy" and entry["proxy"] is True for entry in manifest["responses"])
    company = result.related["companies"][0]
    assert (company["status"], company["inventory_count"], company["matched_count"], company["match_counts"]["address"]) == ("done", 8, 1, 1)


# --- Adım 3: Vacasa -----------------------------------------------------------------------------------------------------------

def test_vacasa_reads_the_unit_page_the_search_page_and_the_quote():
    adapter = aa.ADAPTERS["vacasa"]
    info = adapter.parse_page(text("vacasa-unit.html"), "https://www.vacasa.com/unit/1012379")
    assert info == {"site_id": "1012379", "origin": "https://www.vacasa.com", "page_url": "https://www.vacasa.com/unit/1012379"}
    assert adapter.parse_page(text("vacasa-place.html"), "https://www.vacasa.com/usa/Dunes-Of-Seagrove-Santa-Rosa-Beach/") is None
    fields = adapter.unit_fields(text("vacasa-unit.html"))
    assert (fields["latitude"], fields["bedrooms"], fields["bathrooms"]) == (30.3056555, 2.0, 2.0) and "address" not in fields
    session = Session([(200, text("vacasa-search.html"))])
    units, _ = adapter.inventory(session, "https://www.vacasa.com", OPTIONS["vacasa.com"]["inventory"])
    assert session.asked[0][0] == "https://www.vacasa.com/search?place=/usa/Highway-30A/" and len(units) == 4
    unit = next(u for u in units if u["site_id"] == "1012712")
    assert (unit["legacy_ids"], unit["bedrooms"], unit["bathrooms"], unit["city"], unit["address"]) == (["32606"], 2.0, 2.0, "Seacrest", None)
    session = Session([(200, text("vacasa-quote.json"))])
    quote = adapter.quote(session, info, APRIL)
    assert session.asked[0][1] == {"unit_id": "1012379", "check_in": "2027/04/10", "check_out": "2027/04/17", "adults": "2", "children": "0", "pets": "0"}
    assert (quote["status"], quote["rent"], quote["cleaning_fee"], quote["taxes"], quote["total"]) == ("priced", 3249.23, 182.0, 411.74, 3842.97)
    assert [t["name"] for t in quote["tax_items"]] == ["Walton County Lodging Tax", "Walton County Sales Tax", "FL State Sales Tax"]
    assert quote["total_includes_fees"] == 1 and quote["total_includes_taxes"] == 1 and quote["currency"] == "USD"


def test_vacasa_refusals_a_short_list_and_the_unit_number_of_a_link():
    adapter = aa.ADAPTERS["vacasa"]
    info = {"site_id": "1012379", "origin": "https://www.vacasa.com", "page_url": "https://www.vacasa.com/unit/1012379"}
    booked = adapter.quote(Session([(400, json.dumps({"Error": [{"message": "booked"}]}))]), info, APRIL)
    assert (booked["status"], booked["available"]) == ("unavailable", 0)
    short = adapter.quote(Session([(200, json.dumps({"Error": [{"message": "min-stay-not-met"}]}))]), info, APRIL)
    assert short["status"] == "restricted" and short["available"] is None
    with pytest.raises(aa.AdapterError):                                                  # a refusal page instead of the answer: nothing is guessed
        adapter.quote(Session([(403, "<html>Forbidden</html>")]), info, APRIL)
    with pytest.raises(aa.AdapterError) as failure:                                        # 300 units announced, two given, also when asked for all
        adapter.inventory(Session([(200, text("vacasa-search-short.html")), (200, text("vacasa-search-short.html"))]),
                          "https://www.vacasa.com", OPTIONS["vacasa.com"]["inventory"])
    assert "300 evden yalnız 2" in str(failure.value)
    session = Session([(200, text("vacasa-search-short.html")), (200, text("vacasa-search.html").replace('"total_units": 4', '"total_units": 300'))])
    with pytest.raises(aa.AdapterError):
        adapter.inventory(session, "https://www.vacasa.com", OPTIONS["vacasa.com"]["inventory"])
    assert session.asked[1][0].endswith("&page_limit=300")
    units, _ = adapter.inventory(Session([(200, text("vacasa-search.html"))]), "https://www.vacasa.com", OPTIONS["vacasa.com"]["inventory"])
    found, note = adapter.link_unit(["https://www.wyndhamvacationrentals.com/florida/x-unit", "https://www.vacasa.com/unit.php?UnitID=32606"], units)
    assert found["site_id"] == "1012712" and "eski numarası" in note and "32606" in note
    assert adapter.link_unit(["https://www.vacasa.com/unit/1012379"], units)[0]["site_id"] == "1012379"
    assert adapter.link_unit(["https://www.vacasa.com/unit/13293"], units) == (None, None)       # a number the list does not know
    assert adapter.link_unit(["https://www.vacasa.com/usa/Seagrove-FL/"], units) == (None, None)  # a place page names no unit


def vacasa_site(request):
    host, path = request.url.host, request.url.path
    if host == "www.wyndhamvacationrentals.com":
        return httpx.Response(301, headers={"location": "https://www.vacasa.com/unit.php?UnitID=32606"})
    if path == "/unit.php":
        return httpx.Response(301, headers={"location": f"/unit/{request.url.params['UnitID']}"})
    if path in ("/unit/32606", "/unit/13293"):
        return httpx.Response(302, headers={"location": "https://www.vacasa.com/usa/Florida/Seacrest/"})
    if path.startswith("/usa/"):
        return page(text("vacasa-place.html"))
    if path == "/search":
        return page(text("vacasa-search.html"))
    if path == "/guest-com-api/get-unit-price-quote":
        return data(text("vacasa-quote.json")) if request.url.params["check_in"] == "2027/04/10" else data(json.dumps({"Error": [{"message": "booked"}]}), 400)
    pytest.fail(f"an address nobody should ask: {request.url}")


def test_only_the_listed_domain_goes_through_the_proxy_and_the_old_unit_number_ties_the_listing(tmp_path, monkeypatch):
    """wyndhamvacationrentals.com is not region-blocked (it only redirects to vacasa.com): its request goes directly; every vacasa.com
    request goes through the proxy. The link's old unit number is the one the site's list gives for one home."""
    sides = Sides(vacasa_site)
    sides.install(monkeypatch)
    sites = [site("vacasa.com", "vacasa", aliases=["wyndhamvacationrentals.com"], inventory=OPTIONS["vacasa.com"]["inventory"])]
    listings = [bd(1, "https://www.wyndhamvacationrentals.com/florida/seacrest/white-caps-unit?utm_medium=referral", bedrooms=2, lat=30.2805, lon=-86.0201),
                bd(2, "https://www.vacasa.com/unit.php?UnitID=13293", bedrooms=4, lat=30.3128, lon=-86.0991),
                bd(3, "https://www.vacasa.com/usa/Seagrove-FL/", bedrooms=None)]
    result = collect(tmp_path, lambda r: pytest.fail("the shared client is not used for a listed company"), sites, listings,
                     region=FakeRegion({"vacasa.com"}, proxy=object()))
    rows = {r["lodging_id"]: r for r in result.records}
    assert rows[1]["page_status"] == "matched" and rows[1]["match_method"] == "link" and rows[1]["site_listing_id"] == "1012712"
    assert rows[1]["link_status"] == "no_listing" and "32606" in rows[1]["match_note"]
    assert rows[2]["page_status"] == "no_listing" and rows[2]["match_method"] is None      # 13293 is no home of the list; its location ties to none
    assert rows[3]["page_status"] == "no_listing" and rows[3]["match_method"] is None
    quotes = {(q["lodging_id"], q["window_key"]): q for q in result.related["quotes"]}
    assert quotes[(1, "apr")]["total"] == 3842.97 and quotes[(1, "mar")]["status"] == "unavailable" and set(quotes) == {(1, "apr"), (1, "mar")}
    assert [httpx.URL(url).host for url in sides.direct] == ["www.wyndhamvacationrentals.com"]
    assert sides.proxied and all(httpx.URL(url).host == "www.vacasa.com" for url in sides.proxied)
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))["responses"]
    assert [(e["transport"], e.get("proxy")) for e in manifest if "wyndham" in e["requested_url"]] == [("http", None)]
    assert all(e["transport"] == "proxy" and e["proxy"] is True for e in manifest if "wyndham" not in e["requested_url"])


def test_the_proxy_client_mounts_only_the_listed_domains():
    proxy = P.ProxySettings("http://proxy.test:8080", "user", "a-long-secret-password")
    client = ar.proxy_client(proxy, ["vacasa.com", "360blue.com"])
    try:
        patterns = sorted(pattern.pattern for pattern in client._mounts)
        assert patterns == ["all://*.360blue.com", "all://*.vacasa.com", "all://360blue.com", "all://vacasa.com"]
        assert client._transport_for_url(httpx.URL("https://www.vacasa.com/unit/1")) is not client._transport       # through the proxy
        assert client._transport_for_url(httpx.URL("https://www.wyndhamvacationrentals.com/x")) is client._transport   # directly
    finally:
        client.close()


# --- Adım 5: 30A Beach Girls, the company's own inventory -----------------------------------------------------------------------

def beach_girls(request, third_city="Seagrove Beach"):
    path = request.url.path
    if path == "/alphabetical-property-list":
        return page(text("avantstay-list.html"))
    if path == "/vacation-rental/609625":
        return page(text("avantstay-home-609625.html"))
    if path == "/vacation-rental/606545":
        return page(text("avantstay-home-606545.html"))
    if path == "/vacation-rental/609640":
        # The third home of the list has no raw copy: the first home's page with this home's id, hash and name and (to exercise the
        # mapping) a neighbourhood name as its place; nothing else changed.
        body = text("avantstay-home-609625.html").replace('"hash": "609625"', '"hash": "609640"').replace("Barefoot Paradise", "30A Bella Bonita")
        return page(body.replace('"city": "Inlet Beach"', f'"city": "{third_city}"'))
    pytest.fail(f"an address nobody should ask: {request.url}")


def test_avantstay_reads_the_home_page_and_the_list():
    adapter = aa.ADAPTERS["avantstay"]
    info = adapter.parse_page(text("avantstay-home-609625.html"), "https://30a-beachgirls.com/vacation-rental/609625")
    assert (info["site_id"], info["home_id"]) == ("609625", "4e470030-7121-11ef-b5dc-c599caa5ff79")
    fields = adapter.unit_fields(text("avantstay-home-609625.html"))
    assert (fields["city"], fields["site_region"], fields["bedrooms"], fields["bathrooms"], fields["sleeps"]) == ("Inlet Beach", "Emerald Coast - 30A", 4.0, 3.0, 10.0)
    assert (fields["latitude"], fields["longitude"]) == (30.3, -86.066)                    # rounded by the site: no use for the location rule
    assert adapter.parse_page(text("avantstay-list.html"), "https://30a-beachgirls.com/alphabetical-property-list") is None
    with pytest.raises(aa.AdapterError):                                                  # the price is not read until an answer has been seen
        adapter.quote(None, info, APRIL)
    found, _ = adapter.link_unit(["https://30a-beachgirls.com/609625/"], [{"site_id": "609625", "url": "u", "legacy_ids": []}])
    assert found["site_id"] == "609625" and adapter.link_unit(["https://30a-beachgirls.com/494199/"], [{"site_id": "609625", "url": "u"}]) == (None, None)


def beach_girls_run(tmp_path, listings, handler=beach_girls):
    sites = [site("30a-beachgirls.com", "avantstay", company="30A Beach Girls", inventory=OPTIONS["30a-beachgirls.com"]["inventory"])]
    return collect(tmp_path, handler, sites, listings)


def test_own_inventory_takes_the_neighbourhood_only_from_the_sites_place_name(tmp_path):
    """Three homes on the list: one the site places in Panama City Beach (outside), one whose place is a neighbourhood name, one whose
    place is the postal city "Inlet Beach" — that one stays without a neighbourhood although its coordinates are known."""
    result = beach_girls_run(tmp_path, [bd(1, "https://30a-beachgirls.com/494199/", bedrooms=4, regions=("inlet-beach",))])
    own = {o["site_listing_id"]: o for o in result.related["own_listings"]}
    assert set(own) == {"609625", "609640"}
    assert (own["609625"]["city"], own["609625"]["region_id"], own["609625"]["latitude"]) == ("Inlet Beach", None, 30.3)
    assert (own["609640"]["city"], own["609640"]["region_id"]) == ("Seagrove Beach", "seagrove")
    assert all("Fiyat sorulmadı" in o["message"] and o["page_status"] == "matched" for o in own.values())
    assert result.related["own_quotes"] == [] and result.related["quotes"] == []
    company = result.related["companies"][0]
    assert (company["status"], company["inventory_count"], company["own_count"], company["own_outside"], company["own_on_bookdirect"]) == ("done", 3, 2, 1, 0)
    row = result.records[0]
    assert row["page_status"] == "not_found" and "eski ilan adresleri çalışmıyor" in row["message"]       # the dead link is not asked
    regions = OPTIONS["30a-beachgirls.com"]["inventory"]["own"]["regions"]
    assert "Santa Rosa Beach" not in regions and "Inlet Beach" not in regions            # postal cities on this site, not neighbourhoods


def test_a_home_that_is_a_bookdirect_listing_is_not_counted_twice(tmp_path):
    """A Book>Direct link that names a home's number ties the listing to that home; the home then is not in the own inventory."""
    result = beach_girls_run(tmp_path, [bd(1, "https://30a-beachgirls.com/609625/", bedrooms=4, regions=("inlet-beach",)),
                                        bd(2, "https://30a-beachgirls.com/494199/", bedrooms=3, regions=("seagrove",))])
    rows = {r["lodging_id"]: r for r in result.records}
    assert rows[1]["page_status"] == "matched" and rows[1]["match_method"] == "link" and rows[1]["site_listing_id"] == "609625"
    assert rows[2]["page_status"] == "not_found" and rows[2]["match_method"] is None
    assert [o["site_listing_id"] for o in result.related["own_listings"]] == ["609640"]
    assert result.related["companies"][0]["own_on_bookdirect"] == 1 and result.related["quotes"] == []


def stored_summary(tmp_path, result, order=("seagrove", "inlet-beach")):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    with db.connect() as con:
        con.execute("PRAGMA foreign_keys=OFF")          # the synthetic run has no Book>Direct lodging run behind it
        con.execute("INSERT INTO jobs(id,kind,title,status,created_at,destination_id) VALUES ('r','source_collection','t','done','now','30a')")
        con.execute("""INSERT INTO source_runs(id,job_id,status,connector_name,connector_version,destination_id,metadata)
            VALUES ('r','r','done','agency-lodging-rates','agency-lodging-rates/2','30a','{}')""")
        ar.AgencyRatesConnector().store_records(con, "r", result.records, result.related)
        names = {"seagrove": "Seagrove", "inlet-beach": "Inlet Beach"}
        return ar.summarize(con, "r", list(order), names), ar.region_listings(con, "r", "seagrove")


def priced(result, prices):
    """The run with the own homes priced as given ({hash: total}); stands for a run after the price query has been written."""
    quotes = []
    for home in result.related["own_listings"]:
        for window in WINDOWS:
            total = prices.get(home["site_listing_id"])
            quotes.append({"status": "priced" if total else "no_price", "available": 1 if total else None, "nightly_rates": None, "rent": total and total - 500,
                           "cleaning_fee": None, "other_fees": None, "fees": None, "taxes": 500 if total else None, "tax_items": None, "total": total,
                           "total_includes_fees": 0 if total else None, "total_includes_taxes": 1 if total else None, "excluded_items": None, "currency": "USD",
                           "min_stay": None, "checkin_days": None, "rule_source": None, "message": None, "adults": 2, "children": 0,
                           "queried_at": "2026-11-17T10:00:00+00:00", "queried_url": home["page_url"], "raw_sha256": ["0" * 64],
                           "domain": home["domain"], "site_listing_id": home["site_listing_id"], "window_key": window["window_key"]})
    result.related["own_quotes"] = quotes
    return result


def test_a_home_without_a_neighbourhood_enters_no_neighbourhoods_median_and_is_counted_apart(tmp_path):
    result = priced(beach_girls_run(tmp_path, [bd(1, "https://30a-beachgirls.com/494199/", bedrooms=4, regions=("inlet-beach",))]),
                    {"609625": 9000.0, "609640": 5000.0})
    summary, listing_view = stored_summary(tmp_path, result)
    cells = {(c["region_id"], c["window_key"]): c for c in summary["cells"]}
    assert cells[("seagrove", "apr")]["own_listing_count"] == 1 and cells[("seagrove", "apr")]["own"]["total_median"] == 5000.0
    assert cells[("inlet-beach", "apr")]["own_listing_count"] == 0                         # its place says "Inlet Beach" as a postal city: not here
    assert cells[("inlet-beach", "apr")]["own"]["priced_count"] == 0 and None not in {r["region_id"] for r in summary["regions"]}
    assert summary["coverage"]["own_listings"] == 2 and summary["coverage"]["own_unassigned"] == 1
    company = summary["own_companies"][0]
    assert (company["homes"], company["with_region"], company["unassigned"], company["outside"], company["priced"]) == (2, 1, 1, 1, 2)
    assert company["regions"] == [{"region_id": "seagrove", "region_name": "Seagrove", "homes": 1}]
    assert company["unassigned_label"] == "mahallesi belirtilmemiş" and "Book>Direct ilanlarına bağlanmadı" in company["source"]
    week = next(w for w in company["windows"] if w["window_key"] == "apr")
    assert (week["priced_count"], week["total_median"], week["unassigned_priced"], week["unassigned_median"]) == (2, 7000.0, 1, 9000.0)
    assert [o["site_listing_id"] for o in listing_view["own"]] == ["609640"]


class PackData:
    """The little of the evidence pack's data the coverage block reads."""

    def __init__(self, db, summary):
        self.db, self.profile, self.summary = db, thirty_a, summary
        self.order, self.names = ["seagrove", "inlet-beach"], {"seagrove": "Seagrove", "inlet-beach": "Inlet Beach"}

    def run(self, connector):
        return {"id": "r", "metadata": {"source_name": "Kiralama şirketleri"}, "connector_name": connector, "source_url": "https://x.bookdirect.net/",
                "fetched_at": "2026-11-17T10:00:00+00:00", "finished_at": None, "raw_sha256": "0" * 64}


def test_the_evidence_pack_shows_the_own_inventory_company_apart(tmp_path, monkeypatch):
    result = priced(beach_girls_run(tmp_path, [bd(1, "https://30a-beachgirls.com/494199/", bedrooms=4, regions=("inlet-beach",))]),
                    {"609625": 9000.0, "609640": 5000.0})
    summary, _ = stored_summary(tmp_path, result)
    pack = PackData(Database(tmp_path / "studio.sqlite3"), summary)
    monkeypatch.setattr(blocks, "agency_summary", lambda data: (data.run("agency-lodging-rates"), data.summary))
    rows = blocks.lodging_coverage(pack, {})
    homes = next(r for r in rows if "30A Beach Girls" in r["ifade"] and r["birim"] == "ev")
    assert homes["deger"] == 2 and "şirketin kendi sitesindeki evler; Book>Direct ilanlarına bağlanmadı" in homes["ifade"]
    assert "Mahallesi belirtilmemiş 1 ev hiçbir mahallenin ortancasına girmez" in homes["not"] and "Seagrove 1" in homes["not"]
    assert homes["tablo"]["hucreler"] == {"Site": "30a-beachgirls.com", "Mahallesi belirtilen": "1", "Mahallesi belirtilmemiş": "1", "Fiyatlı ev": "2"}
    week = next(r for r in rows if "30A Beach Girls" in r["ifade"] and "Nisan 2027" in r["ifade"])
    assert (week["deger"], week["birim"], week["orneklem"], week["etiket"]) == (7000.0, "USD", 2, "bizim hesabımız") and "9,000.00 USD" in week["not"]
    reasons = blocks.unread_companies(thirty_a)
    assert "bölge engeli" in reasons["360blue.com"]["neden"] and "bölge engeli" in reasons["vacasa.com"]["neden"]
    assert "site yok" in reasons["outdoorshower30a.com"]["altyapi"] and reasons["30a-beachgirls.com"]["kontrol_tarihi"] == "2026-11-17"


# --- Adım 6: the estimate, the configuration and the migration -------------------------------------------------------------------

def test_the_estimate_counts_the_new_companies_at_the_proxys_pace_and_the_own_homes(monkeypatch):
    monkeypatch.setattr(ar, "REQUEST_GAP", 2.0)
    monkeypatch.setattr(ar, "PROXY_GAP", 8.0)
    sites = [{"domain": d, "company": c, "adapter": a, "enabled": 1, "aliases": json.dumps(OPTIONS[d].get("aliases", [])),
              "inventory": json.dumps(OPTIONS[d]["inventory"])} for d, c, a in thirty_a.AGENCY_SITES_V22]
    listings = ([{"url": f"https://www.360blue.com/rentals/properties/x-{n}/"} for n in range(10)]
                + [{"url": "https://www.vacasa.com/unit/1"}, {"url": "https://www.wyndhamvacationrentals.com/florida/x-unit"}]
                + [{"url": "https://30a-beachgirls.com/1/"}])
    added = {a["domain"]: a for a in ar.new_site_estimate(sites, listings, set(), 12, ["vacasa.com", "360blue.com"])}
    assert (added["360blue.com"]["listings"], added["360blue.com"]["requests"], added["360blue.com"]["proxy"]) == (10, 10 * (3 + 12), True)
    assert added["360blue.com"]["seconds"] == 150 * 9                                      # 8 s between two requests through the proxy + 1 s
    assert (added["vacasa.com"]["listings"], added["vacasa.com"]["requests"]) == (2, 2 * (3 + 12))          # the Wyndham link counts with Vacasa
    girls = added["30a-beachgirls.com"]
    assert (girls["listings"], girls["own_homes"], girls["requests"], girls["proxy"]) == (1, 145, 145, False)   # one page per home; dead link, no price request
    assert girls["seconds"] == 145 * 3
    assert ar.new_site_estimate(sites, listings, {"360blue.com", "vacasa.com", "30a-beachgirls.com"}, 12) == []
    unlisted = {a["domain"]: a for a in ar.new_site_estimate(sites, listings, set(), 12)}
    assert unlisted["360blue.com"]["proxy"] is False and unlisted["360blue.com"]["seconds"] == 150 * 3


def test_a_fresh_database_has_the_three_new_companies_of_schema_22(tmp_path):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    assert SCHEMA_VERSION == 23
    agency = {s["domain"]: s for s in db.context("30a").agency["sites"]}
    assert [(d, agency[d]["company"], agency[d]["adapter"]) for d in ("360blue.com", "vacasa.com", "30a-beachgirls.com")] == list(thirty_a.AGENCY_SITES_V22)
    options = {domain: ar.site_options(agency[domain]) for domain in agency}
    assert options["vacasa.com"]["aliases"] == ["wyndhamvacationrentals.com"]
    own = options["30a-beachgirls.com"]["inventory"]["own"]
    assert own["site_region"] == "Emerald Coast - 30A" and options["30a-beachgirls.com"]["own_region_id"] is None
    assert own["quotes"] is True and OPTIONS["30a-beachgirls.com"]["inventory"]["own"]["quotes"] is False      # GÖREV-23 (schema 23) turned the rent on
    with db.connect() as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 23
        assert {r[0] for r in con.execute("SELECT id FROM regions")} >= set(own["regions"].values())
        assert [r["notnull"] for r in con.execute("PRAGMA table_info(agency_rate_own_listings)") if r["name"] == "region_id"] == [0]
        assert not con.execute("SELECT 1 FROM region_blocked_hosts WHERE host IN ('360blue.com','vacasa.com')").fetchone()     # the list is the user's data
    assert all(adapter in ar.ADAPTERS for _, _, adapter in thirty_a.AGENCY_SITES_V22)


def test_the_21_to_22_migration_keeps_every_row_and_adds_each_company_once(tmp_path):
    from studio import migration_v22
    from studio.migrations import execute_schema
    path = tmp_path / "studio.sqlite3"
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        con.execute("PRAGMA foreign_keys=OFF")
        legacy.drop_v22(con, rows=True)
        # the table change alone on a copy that holds a home (a run behind it would need a whole lodging run; the relation check of
        # the real upgrade is exercised below on the file without it)
        con.execute("""INSERT INTO agency_rate_own_listings (run_id,domain,site_listing_id,title,page_url,address,city,region_id,page_status)
            VALUES ('run','alysbeach.com','7','Ev','https://vacation.alysbeach.com/vrp/unit/7','1 Sea Garden St','Alys Beach','alys-beach','matched')""")
        execute_schema(con, migration_v22.SCHEMA)
        assert con.execute("SELECT site_listing_id,region_id,city FROM agency_rate_own_listings").fetchall() == [("7", "alys-beach", "Alys Beach")]
        con.execute("INSERT INTO agency_rate_own_listings (run_id,domain,site_listing_id,title,page_url,page_status) VALUES ('run','x.test','8','Ev','https://x.test/8','matched')")
        con.execute("DELETE FROM agency_rate_own_listings")
        legacy.drop_v22(con, rows=True)
        con.execute("INSERT INTO destination_agency_sites (destination_id,domain,company,adapter,enabled,sort_order) VALUES ('30a','vacasa.com','Elle eklendi','vacasa',0,99)")
        con.execute("PRAGMA user_version=21")
        before = con.execute("SELECT COUNT(*) FROM destination_agency_sites").fetchone()[0]
        assert [r[3] for r in con.execute("PRAGMA table_info(agency_rate_own_listings)") if r[1] == "region_id"] == [1]
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 23
        assert [r[3] for r in con.execute("PRAGMA table_info(agency_rate_own_listings)") if r[1] == "region_id"] == [0]
        assert con.execute("SELECT COUNT(*) FROM destination_agency_sites").fetchone()[0] == before + 2
        assert con.execute("SELECT company,enabled FROM destination_agency_sites WHERE domain='vacasa.com'").fetchall() == [("Elle eklendi", 0)]
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        assert len(list((tmp_path / "backups").glob("studio-v21-*.sqlite3"))) == 1          # the program's own backup before the change


def test_a_measured_domain_goes_on_the_list_with_its_evidence(tmp_path):
    from fastapi.testclient import TestClient
    from studio.app import create_app
    from tests.test_proxy import HEADERS
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        added = client.post("/api/abd-proxy/bolge-engelli", json={
            "alan_adi": "vacasa.com", "baslik": "ERROR: The request could not be satisfied", "adres": "https://www.vacasa.com/usa/Dunes-Of-Seagrove-Santa-Rosa-Beach/",
            "kanit": "17.11.2026 ölçümü: doğrudan 403 (CloudFront ülke engeli), proxy 200"})
        row = added.json()["bolge_engelli"][0]
        assert added.status_code == 201 and (row["host"], row["added_by"], row["title"]) == ("vacasa.com", "kullanici", "ERROR: The request could not be satisfied")
        assert row["evidence"].startswith("17.11.2026 ölçümü") and row["url"].endswith("/Dunes-Of-Seagrove-Santa-Rosa-Beach/")
        plain = client.post("/api/abd-proxy/bolge-engelli", json={"alan_adi": "360blue.com", "kanit": 5}).json()["bolge_engelli"]
        assert [(r["host"], r["evidence"]) for r in plain if r["host"] == "360blue.com"] == [("360blue.com", None)]


def test_added_companies_lengthen_the_run_as_companies_read_side_by_side(monkeypatch):
    monkeypatch.setattr(ar, "REQUEST_GAP", 2.0)
    monkeypatch.setattr(ar, "PROTECTED_GAP", 6.0)
    last = [{"domain": "a.test", "listing_count": 100, "request_count": 1000, "protected": 0},      # 3,000 s
            {"domain": "b.test", "listing_count": 50, "request_count": 400, "protected": 0},        # 1,200 s
            {"domain": "c.test", "listing_count": 20, "request_count": 100, "protected": 1}]        # 700 s
    small = [{"domain": "n.test", "listings": 10, "seconds": 1000, "protected": False}]
    assert ar.added_run_seconds(3000, last, small, workers=3) == 0                    # it fits beside the longest company
    big = [{"domain": "n.test", "listings": 200, "seconds": 4500, "protected": False}]
    assert ar.added_run_seconds(3300, last, big, workers=3) == 1650                   # the run is as long as its longest company: 3,000 -> 4,500 s, scaled by the real duration
    assert ar.added_run_seconds(3000, last, big, workers=1) == int(3000 * 9400 / 4900) - 3000   # one at a time: everything adds up
    assert ar.added_run_seconds(None, last, big) == 4500 and ar.added_run_seconds(3000, [], big) == 4500      # nothing to scale: the plain sum
    sites = [{"domain": "360blue.com", "company": "360 Blue", "adapter": "nrbe", "enabled": 1, "inventory": json.dumps(OPTIONS["360blue.com"]["inventory"])}]
    listings = [{"url": f"https://www.360blue.com/rentals/properties/x-{n}/"} for n in range(256)]
    blue = ar.new_site_estimate(sites, listings, set(), 12, ["360blue.com"])[0]
    assert (blue["listings"], blue["requests"]) == (256, 127 * (3 + 12))             # only the listings expected to tie ask the calendar and the prices
