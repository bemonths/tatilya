"""GÖREV-23: the weekly rent of 30A Beach Girls' homes from the calendar AvantStay's service answers (no cart, never a total), Vacasa's
whole list in one request and the rule for a short list, Outdoor Shower's listings and the address rule, the configuration (schema
23) and the estimate.

The fixtures (tests/fixtures/gorev23/) are cut from the raw copies of the task's own reading of 17 November 2026
(work/gorev-23/fikstur.py): unrelated fields dropped, no value changed. Nothing here reaches a site or a proxy.
"""
import json
import sqlite3
from datetime import date
from pathlib import Path

import httpx
import pytest

from studio.database import SCHEMA_VERSION, Database
from studio.destinations import thirty_a
from studio.evidence import blocks
from studio.sources import agency_adapters as aa
from studio.sources import agency_matching as am
from studio.sources import agency_rates as ar
from tests.test_agency_v2 import bd, site
from tests.test_gorev22 import FIX as FIX22
from tests.test_gorev22 import PackData, Session, collect, page, stored_summary

FIX = Path(__file__).parent / "fixtures" / "gorev23"
HOME = "4e470030-7121-11ef-b5dc-c599caa5ff79"
INFO = {"site_id": "609625", "home_id": HOME, "origin": "https://30a-beachgirls.com", "page_url": "https://30a-beachgirls.com/vacation-rental/609625",
        "channel": "BEACH_GIRLS"}
V22, V23 = thirty_a.AGENCY_SITE_OPTIONS_V22, thirty_a.AGENCY_SITE_OPTIONS_V23


def text(name, folder=FIX):
    return (folder / name).read_text(encoding="utf-8")


def window(checkin, nights=7, key="w"):
    start = date.fromisoformat(checkin)
    return {"window_key": key, "checkin_date": start, "checkout_date": date.fromordinal(start.toordinal() + nights), "nights": nights}


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    for name in ("REQUEST_GAP", "RETRY_PAUSE", "PROXY_GAP"):
        monkeypatch.setattr(ar, name, 0)
    monkeypatch.setattr(aa.AvantStay, "today", staticmethod(lambda: date(2026, 11, 17)))


class Posts(Session):
    """The fake session of GÖREV-22, keeping what a POST carried."""

    def request(self, method, url, **kwargs):
        self.sent = getattr(self, "sent", []) + [(method, url, kwargs.get("json"), kwargs.get("headers"))]
        return super().request(method, url, **kwargs)


# --- Adım 3: 30A Beach Girls, the rent from the calendar -------------------------------------------------------------------------

def test_avantstay_reads_the_weekly_rent_from_the_calendar_and_never_a_total():
    adapter = aa.ADAPTERS["avantstay"]
    session, info = Posts([(200, text("avantstay-calendar.json"))]), dict(INFO)
    quote = adapter.quote(session, info, window("2027-04-10"))
    method, url, body, headers = session.sent[0]
    assert (method, url) == ("POST", "https://arriere.prod.avantstay.com/public/graphql") and headers["X-Distribution-Channel"] == "BEACH_GIRLS"
    assert body["variables"] == {"homeId": HOME, "from": "2026-11-01", "to": "2028-05-01"}       # one request: 18 months from this month's first day
    assert "calendar(from: $from, to: $to)" in body["query"] and "cartPrice" not in body["query"] and "mutation" not in body["query"]
    assert (quote["status"], quote["available"], quote["rent"], quote["currency"], quote["min_stay"]) == ("priced", 1, 1468.0, "USD", 4)
    assert quote["total"] is None and quote["taxes"] is None and quote["cleaning_fee"] is None and quote["fees"] is None
    assert quote["total_includes_fees"] is None and quote["total_includes_taxes"] is None       # no total: nothing is said about what it holds
    assert [n["date"] for n in quote["nightly_rates"]] == [f"2027-04-{day}" for day in range(10, 17)]
    assert sum(n["price"] for n in quote["nightly_rates"]) == 1468.0 and "bizim toplamımız" in quote["message"] and "sepet" in quote["message"]
    # the same calendar answers the home's other windows: no second request
    taken = adapter.quote(session, info, window("2027-06-05"))
    assert len(session.sent) == 1 and taken["status"] == "priced"                           # leaving on a day a booking starts is allowed
    assert adapter.sends_guests is False and adapter.quote_requests == 0 and adapter.api_hosts == ("arriere.prod.avantstay.com",)


def test_avantstay_a_taken_week_a_closed_arrival_day_and_a_minimum_stay_follow_the_sites_own_rule():
    adapter = aa.ADAPTERS["avantstay"]
    session, info = Posts([(200, text("avantstay-calendar.json"))]), dict(INFO)
    occupied = adapter.quote(session, info, window("2027-03-06"))
    assert (occupied["status"], occupied["available"]) == ("unavailable", 0) and "8 gününü dolu" in occupied["message"]
    arriving = adapter.quote(session, info, window("2027-04-23"))                            # another stay begins that day
    assert arriving["status"] == "unavailable" and "2027-04-23" in arriving["message"]
    leaving = adapter.quote(session, info, window("2027-03-31", nights=3))                   # a stay ends that day: arrival is possible
    assert leaving["status"] == "restricted" and leaving["min_stay"] == 4 and leaving["rule_source"] == "yanıt"
    closed = adapter.quote(session, info, window("2027-06-01", nights=3))
    assert closed["status"] == "restricted" and "girişe izin vermiyor" in closed["message"] and closed["available"] is None
    no_exit = adapter.quote(session, info, window("2027-05-25"))                             # 1 June allows no check-out
    assert no_exit["status"] == "restricted" and "çıkışa izin vermiyor" in no_exit["message"]
    with pytest.raises(aa.AdapterError):                                                    # a day the calendar did not give: nothing is guessed
        adapter.quote(session, info, window("2027-06-28"))
    assert len(session.sent) == 1


def test_avantstay_an_error_answer_and_a_missing_channel_are_errors_not_prices():
    adapter = aa.ADAPTERS["avantstay"]
    with pytest.raises(aa.AdapterError) as failure:
        adapter.quote(Posts([(422, text("avantstay-error.json"))]), dict(INFO), window("2027-04-10"))
    assert "HTTP 422" in str(failure.value) and "Internal server error" in str(failure.value)
    with pytest.raises(aa.AdapterError):
        adapter.quote(Posts([(200, "<html>Just a page</html>")]), dict(INFO), window("2027-04-10"))
    without = {key: value for key, value in INFO.items() if key != "channel"}
    session = Posts([])
    with pytest.raises(aa.AdapterError) as failure:
        adapter.quote(session, without, window("2027-04-10"))
    assert "kanal adı" in str(failure.value) and not getattr(session, "sent", [])            # nothing is sent without the site's own channel


def beach_girls(request):
    path = request.url.path
    if request.url.host == "arriere.prod.avantstay.com":
        asked = json.loads(request.content)
        assert request.method == "POST" and path == "/public/graphql" and request.headers["x-distribution-channel"] == "BEACH_GIRLS"
        assert "cartPrice" not in asked["query"] and asked["variables"]["from"] == "2026-11-01"
        return httpx.Response(200, content=text("avantstay-calendar.json").encode("utf-8"), headers={"content-type": "application/json"})
    if path == "/alphabetical-property-list":
        return page(text("avantstay-list.html", FIX22))
    if path == "/vacation-rental/609625":
        return page(text("avantstay-home-609625.html", FIX22))
    if path == "/vacation-rental/606545":
        return page(text("avantstay-home-606545.html", FIX22))
    if path == "/vacation-rental/609640":
        body = text("avantstay-home-609625.html", FIX22).replace('"hash": "609625"', '"hash": "609640"').replace("Barefoot Paradise", "30A Bella Bonita")
        return page(body.replace('"city": "Inlet Beach"', '"city": "Seagrove Beach"'))
    pytest.fail(f"an address nobody should ask: {request.url}")


def test_the_own_homes_get_their_rent_and_the_summary_keeps_rent_apart_from_totals(tmp_path, monkeypatch):
    """The run with the configuration of schema 23: each home of the 30A region asks the calendar once; the home outside is not asked.
    A rent is never a total: no total median, no priced cell of a neighbourhood; the company table and the evidence pack name it as rent."""
    sites = [site("30a-beachgirls.com", "avantstay", company="30A Beach Girls", inventory=V23["30a-beachgirls.com"]["inventory"])]
    result = collect(tmp_path, beach_girls, sites, [bd(1, "https://30a-beachgirls.com/494199/", bedrooms=4, regions=("inlet-beach",))])
    quotes = {(q["site_listing_id"], q["window_key"]): q for q in result.related["own_quotes"]}
    assert set(quotes) == {(home, key) for home in ("609625", "609640") for key in ("apr", "mar")}
    assert quotes[("609625", "apr")]["rent"] == 1468.0 and quotes[("609625", "apr")]["total"] is None and quotes[("609625", "apr")]["adults"] is None
    assert quotes[("609625", "mar")]["status"] == "unavailable" and quotes[("609625", "apr")]["queried_url"].startswith("https://arriere.prod.avantstay.com/")
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))["responses"]
    calendars = [e for e in manifest if "arriere" in e["requested_url"]]
    assert len(calendars) == 2 and all(e["method"] == "POST" and "calendar" in json.dumps(e["request_body"]) for e in calendars)
    assert all("Fiyat sorulmadı" not in (o["message"] or "") for o in result.related["own_listings"])
    summary, _ = stored_summary(tmp_path, result)
    company = summary["own_companies"][0]
    week = next(w for w in company["windows"] if w["window_key"] == "apr")
    assert (week["rent_count"], week["rent_median"], week["priced_count"], week["total_median"]) == (2, 1468.0, 0, None)
    assert company["priced"] == 2 and summary["total_counts"]["priced"] == 0
    cells = {(c["region_id"], c["window_key"]): c for c in summary["cells"]}
    assert cells[("seagrove", "apr")]["own"]["priced_count"] == 0 and cells[("seagrove", "apr")]["own"]["total_median"] is None
    assert cells[("seagrove", "mar")]["own"]["available_share"] == 0.0
    monkeypatch.setattr(blocks, "agency_summary", lambda data: (data.run("agency-lodging-rates"), data.summary))
    rows = blocks.lodging_coverage(PackData(Database(tmp_path / "studio.sqlite3"), summary), {})
    rent = next(r for r in rows if "30A Beach Girls" in r["ifade"] and "Nisan 2027" in r["ifade"])
    assert (rent["deger"], rent["birim"], rent["orneklem"], rent["etiket"]) == (1468.0, "USD", 2, "bizim hesabımız")
    assert "7 gecelik kira ortancası" in rent["ifade"] and "HARİÇ" in rent["ifade"] and "Toplam fiyat değildir" in rent["not"]
    assert not [r for r in rows if "30A Beach Girls" in r["ifade"] and "toplam ortancası" in r["ifade"]]


# --- Adım 4: Vacasa's whole list -------------------------------------------------------------------------------------------------

def test_vacasa_takes_the_whole_list_with_one_more_request_and_a_short_list_stays_an_error():
    adapter, options = aa.ADAPTERS["vacasa"], V22["vacasa.com"]["inventory"]
    first = text("vacasa-search-short.html", FIX22)                                         # the page as it opens: 300 announced, a few given
    session = Session([(200, first), (200, text("vacasa-search-all.html"))])
    units, replies = adapter.inventory(session, "https://www.vacasa.com", options)
    assert [url for url, _ in session.asked] == ["https://www.vacasa.com/search?place=/usa/Highway-30A/",
                                                 "https://www.vacasa.com/search?place=/usa/Highway-30A/&page_limit=300"]
    assert len(units) == 300 == len({u["site_id"] for u in units}) and len(replies) == 2
    assert all(u["latitude"] and u["longitude"] and u["page"]["page_status"] == "matched" for u in units)
    former = [u for u in units if u["legacy_ids"]]
    assert len(former) > 200 and all(old != u["site_id"] for u in former for old in u["legacy_ids"])
    # the former number of exactly one home ties a Book>Direct link to it; a number no home has ties to nothing
    one = former[0]
    found, note = adapter.link_unit([f"https://www.vacasa.com/unit.php?UnitID={one['legacy_ids'][0]}"], units)
    assert found["site_id"] == one["site_id"] and "eski numarası" in note
    assert adapter.link_unit(["https://www.vacasa.com/unit.php?UnitID=13293"], units) == (None, None)
    # one unit fewer than announced, also when asked for all: the company is an error of that run, no listing is tied by guess
    data = aa.Vacasa.search_results(text("vacasa-search-all.html"))
    cut = text("vacasa-search-all.html").replace(json.dumps(data["units"][-1], ensure_ascii=False) + "]", "]").replace(", ]", "]")
    assert len(aa.Vacasa.search_results(cut)["units"]) == 299
    with pytest.raises(aa.AdapterError) as failure:
        adapter.inventory(Session([(200, first), (200, cut)]), "https://www.vacasa.com", options)
    assert "300 evden yalnız 299" in str(failure.value) and "liste eksik" in str(failure.value)


# --- Adım 5: Outdoor Shower's listings and the address rule ---------------------------------------------------------------------

def test_outdoor_shower_has_no_reader_and_its_reason_is_reviewed():
    """LocalVR's own list (17 Nov 2026) has no home in Florida, so nothing is configured for Outdoor Shower's 21 listings: they stay
    without a price, with the reviewed reason in the evidence pack."""
    domains = {d for group in (thirty_a.AGENCY_SITES, thirty_a.AGENCY_SITES_V12, thirty_a.AGENCY_SITES_V22, thirty_a.AGENCY_SITES_V23) for d, _, _ in group}
    assert "outdoorshower30a.com" not in domains and "golocalvr.com" not in domains
    reason = blocks.unread_companies(thirty_a)["outdoorshower30a.com"]
    assert "site yok" in reason["altyapi"] and "548" in reason["neden"] and "Florida" in reason["neden"] and reason["kontrol_tarihi"] == "2026-11-17"


def test_the_address_rule_ties_a_listing_by_its_address_and_never_by_a_name_alone():
    """The rule Outdoor Shower's listings would be tied by (the one 360 Blue's are): the same street number and street, the same unit,
    the same bedrooms, one candidate, within 2 km. A home whose name is the same but whose address differs is not tied."""
    listing = {"lodging_id": 1, "title": "Sandy Feet Retreat", "address": "114 Seacrest Beach Blvd E", "bedrooms": 4, "latitude": 30.2871, "longitude": -86.0305}
    same_name = {"site_id": "a", "url": "https://x.test/a", "title": "Sandy Feet Retreat", "address": "27 Dune Rosemary Ct", "bedrooms": 4,
                 "latitude": 30.2872, "longitude": -86.0306}
    same_address = {"site_id": "b", "url": "https://x.test/b", "title": "Another Name Entirely", "address": "114 Seacrest Beach Boulevard E",
                    "bedrooms": 4, "latitude": 30.2872, "longitude": -86.0306}
    kind, unit, note = am.address_match(listing, [same_name])
    assert kind != "matched" and unit is None                                               # the name alone ties nothing
    kind, unit, note = am.address_match(listing, [same_name, same_address])
    assert kind == "matched" and unit["site_id"] == "b"
    assert am.address_match({**listing, "bedrooms": 3}, [same_address])[0] != "matched"     # another bedroom count
    far = {**same_address, "latitude": 30.3601, "longitude": -86.2301}
    assert am.address_match(listing, [far])[0] != "matched"                                 # the same address text more than 2 km away
    twin = {**same_address, "site_id": "c", "url": "https://x.test/c"}
    assert am.address_match(listing, [same_address, twin])[0] != "matched"                  # two candidates: not tied


# --- Adım 6: the configuration, the migration and the estimate -----------------------------------------------------------------

def test_a_fresh_database_has_schema_23_and_asks_beach_girls_for_the_rent(tmp_path):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    assert SCHEMA_VERSION == 24
    agency = {s["domain"]: ar.site_options(s) for s in db.context("30a").agency["sites"]}
    inventory = agency["30a-beachgirls.com"]["inventory"]
    assert inventory == V23["30a-beachgirls.com"]["inventory"] and inventory["channel"] == "BEACH_GIRLS"
    assert inventory["own"]["quotes"] is True and "quotes_note" not in inventory["own"] and inventory["own"]["regions"]["Seagrove Beach"] == "seagrove"
    assert agency["vacasa.com"]["inventory"] == V22["vacasa.com"]["inventory"] and agency["360blue.com"]["inventory"] == V22["360blue.com"]["inventory"]


def test_the_22_to_23_migration_changes_only_the_options_it_gave_and_keeps_every_row(tmp_path):
    path = tmp_path / "studio.sqlite3"
    Database(path).initialize()
    old = json.dumps(V22["30a-beachgirls.com"]["inventory"], ensure_ascii=False)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE destination_agency_sites SET inventory=? WHERE domain='30a-beachgirls.com'", (old,))
        con.execute("UPDATE destination_agency_sites SET inventory=? WHERE domain='360blue.com'", (json.dumps({"source": "platform", "origin": "https://elle.test"}),))
        con.execute("PRAGMA user_version=22")
        counts = {name: con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                  for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()}
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 24 and con.execute("PRAGMA foreign_key_check").fetchall() == []
        after = {name: con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in counts}
        assert after == counts                                                               # no row added or lost
        girls = json.loads(con.execute("SELECT inventory FROM destination_agency_sites WHERE domain='30a-beachgirls.com'").fetchone()[0])
        assert girls == V23["30a-beachgirls.com"]["inventory"]
        blue = json.loads(con.execute("SELECT inventory FROM destination_agency_sites WHERE domain='360blue.com'").fetchone()[0])
        assert blue == {"source": "platform", "origin": "https://elle.test"}                 # a row somebody changed is left alone
    assert list((tmp_path / "backups").glob("studio-v22-*.sqlite3"))                         # the program's own backup before the change


def test_the_estimate_counts_one_page_and_one_calendar_per_own_home(monkeypatch):
    monkeypatch.setattr(ar, "REQUEST_GAP", 2.0)
    sites = [{"domain": "30a-beachgirls.com", "company": "30A Beach Girls", "adapter": "avantstay", "enabled": 1, "aliases": "[]",
              "inventory": json.dumps(V23["30a-beachgirls.com"]["inventory"])}]
    added = ar.new_site_estimate(sites, [{"url": "https://30a-beachgirls.com/1/"}], set(), 12)[0]
    assert (added["listings"], added["own_homes"], added["requests"], added["seconds"]) == (1, 145, 145 * 2, 145 * 2 * 3)
