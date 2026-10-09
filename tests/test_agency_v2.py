"""agency-lodging-rates/2: address and location matching, new platform adapters, own inventory, published rents, guest counts,
protected-site pacing and the v11 -> v12 migration.

Synthetic pages in the platforms' real shapes through httpx.MockTransport only; suite-wide no_real_http prevents internet access.
"""
import json
import sqlite3
import tempfile
import threading
from pathlib import Path
from datetime import date
from urllib.parse import parse_qs

import httpx
import pytest

from studio.database import Database
from studio.destinations import thirty_a
from studio.sources import agency_adapters as aa
from studio.sources import agency_matching as am
from studio.sources import agency_rates as ar
from tests.test_agency_rates import RESCMS_PAGE, RESCMS_PRICE, RESCMS_QUOTE, TRACK_PAGE, TRACK_QUOTE, html, json_reply
from tests.test_climate import table_counts

TODAY = date(2026, 10, 8)
WINDOWS = [{"window_key": "winter", "label": "Kış", "checkin": "2027-01-16", "checkout": "2027-01-23"},
           {"window_key": "fall-2027", "label": "Sonbahar 2027", "checkin": "2027-10-16", "checkout": "2027-10-23"}]
WINTER = {"window_key": "winter", "checkin_date": date(2027, 1, 16), "checkout_date": date(2027, 1, 23), "nights": 7}


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(ar, "REQUEST_GAP", 0)
    monkeypatch.setattr(ar, "RETRY_PAUSE", 0)


def bd(lodging_id, url, *, address=None, bedrooms=3, bathrooms=2, sleeps=8, lat=None, lon=None, regions=("seaside",), title=None):
    return {"lodging_id": lodging_id, "title": title or f"Listing {lodging_id}", "url": url, "bedrooms": bedrooms, "bathrooms": bathrooms,
            "sleeps": sleeps, "address": address, "latitude": lat, "longitude": lon, "region_ids": list(regions)}


def site(domain, adapter, **options):
    return {"domain": domain, "company": domain.split(".")[0].title(), "adapter": adapter, "enabled": 1, **options}


def run(tmp_path, handler, sites, listings, *, verifier=None, waiting=None, windows=WINDOWS):
    config = {"sites": sites, "windows": windows, "input": {"run_id": "lodging-run", "searched_on": "2026-10-07", "listings": listings}}
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return ar.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config, client=client,
                          verifier=verifier, waiting=waiting, today=TODAY)


def quotes_of(result):
    return {(q["lodging_id"], q["window_key"]): q for q in result.related["quotes"]}


# --- Address and location rules ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text,key", [
    ("2381 W County Highway 30a #5", ("2381", "w 30a", "5")),
    ("2421 W County Hwy 30A F302", ("2421", "w 30a", "f302")),
    ("2421 West Scenic Highway 30-A, Unit F302", ("2421", "w 30a", "f302")),
    ("2449 CR-30A", ("2449", "30a", None)),
    ("8090 E Cty Hwy 30A, Unit 5", ("8090", "e 30a", "5")),
    ("216 Blue Mtn Rd, Unit 4A", ("216", "blue mtn rd", "4a")),
    ("216 Blue Mountain Road #4A", ("216", "blue mtn rd", "4a")),
    ("57 Western Lake Drive", ("57", "western lk dr", None)),
    ("Ocean Breeze", None), ("", None), (None, None),
])
def test_address_normalization_abbreviations_and_30a_names(text, key):
    assert am.normalize_address(text) == key


def unit(site_id, address, bedrooms=3, bathrooms=2, lat=None, lon=None, city="Seaside"):
    return {"site_id": site_id, "url": f"https://co.example/u/{site_id}", "title": f"Unit {site_id}", "address": address, "city": city,
            "bedrooms": bedrooms, "bathrooms": bathrooms, "latitude": lat, "longitude": lon}


def test_address_rule_needs_one_exact_candidate_same_unit_and_bedrooms():
    listing = {"lodging_id": 1, "address": "216 Blue Mtn Rd, Unit 4A", "bedrooms": 2, "latitude": 30.3381, "longitude": -86.2020}
    exact = unit("a", "216 Blue Mountain Road #4A", 2, lat=30.33812, lon=-86.20201)
    kind, found, note = am.address_match(listing, [exact, unit("b", "216 Blue Mountain Road #4B", 2), unit("c", "216 Blue Mountain Road", 2)])
    assert (kind, found["site_id"]) == ("matched", "a") and "216 blue mtn rd #4a" in note
    assert am.address_match(listing, [unit("b", "216 Blue Mountain Road #4B", 2)])[0] == "none"          # another unit
    assert am.address_match(listing, [unit("c", "216 Blue Mountain Road", 2)])[0] == "none"              # one side has no unit
    assert am.address_match(listing, [unit("a", "216 Blue Mountain Road #4A", 3)])[0] == "none"           # bedrooms differ
    kind, _, note = am.address_match(listing, [unit("a", "216 Blue Mountain Road #4A", 2), unit("d", "216 Blue Mtn Rd Unit 4A", 2)])
    assert kind == "ambiguous" and "2 aday" in note
    far = unit("e", "216 Blue Mountain Road #4A", 2, lat=30.40, lon=-86.30)                                # same text, 10 km away
    assert am.address_match(listing, [far])[0] == "none"
    assert am.address_match({**listing, "address": "Gulf front cottage"}, [exact])[0] == "unusable"
    assert am.address_match({**listing, "bedrooms": None}, [exact])[0] == "unusable"


def test_location_rule_15_m_same_rooms_single_candidate_and_crowded_buildings():
    here = {"lodging_id": 1, "latitude": 30.2794374, "longitude": -86.0133082, "bedrooms": 4, "bathrooms": 3.5}
    near = unit("n", None, 4, 3.5, lat=30.27950, lon=-86.01331)         # ~7 m north
    other = unit("o", None, 4, 3.5, lat=30.27990, lon=-86.01331)        # ~50 m north (inside the 50 m uniqueness ring? ~51 m)
    kind, found, note = am.location_match(here, [near, unit("x", None, 3, 2, lat=30.27944, lon=-86.01331)], [here])
    assert (kind, found["site_id"]) == ("matched", "n") and "m," in note
    assert am.location_match(here, [unit("f", None, 4, 3.5, lat=30.27980, lon=-86.01331)], [here])[0] == "none"     # ~38 m: too far
    assert am.location_match(here, [near, unit("p", None, 4, 3.5, lat=30.27970, lon=-86.01331)], [here])[0] == "ambiguous"  # two within 50 m
    assert am.location_match(here, [unit("b", None, 4, 2.5, lat=30.27950, lon=-86.01331)], [here])[0] == "none"     # bathrooms differ
    neighbour = {"lodging_id": 2, "latitude": 30.27945, "longitude": -86.01330}
    assert am.location_match(here, [near], [here, neighbour])[0] == "crowded"                                          # several units here
    assert am.location_match({**here, "latitude": None}, [near], [here])[0] == "unusable"
    assert am.distance_m(30.0, -86.0, 30.0, -86.0) == 0 and 110 < am.distance_m(30.0, -86.0, 30.001, -86.0) < 112
    del other


def test_a_title_alone_never_matches():
    listing = {"lodging_id": 1, "address": None, "bedrooms": 3, "bathrooms": 2, "latitude": None, "longitude": None}
    same_name = {**unit("a", None, 3, 2), "title": "Listing 1"}
    assert am.address_match(listing, [same_name])[0] == "unusable" and am.location_match(listing, [same_name], [listing])[0] == "unusable"


def test_json_ld_unit_reads_the_lodging_never_the_company_office():
    page = """<script type="application/ld+json">{"@context":"https://schema.org","@type":"LocalBusiness","address":{"@type":"PostalAddress",
    "streetAddress":"5365 East County Highway 30A, Suite 101"}}</script><script type="application/ld+json">{"@type":"VacationRental",
    "address":{"@type":"PostalAddress","streetAddress":"97 West Okeechobee","addressLocality":"30A"},"geo":{"@type":"GeoCoordinates",
    "latitude":30.349091,"longitude":-86.216763},"containsPlace":{"@type":"Accommodation","numberOfBedrooms":4,"numberOfBathroomsTotal":4,
    "occupancy":{"@type":"QuantitativeValue","maxValue":8}}}</script>"""
    assert am.json_ld_unit(page) == {"address": "97 West Okeechobee", "city": "30A", "latitude": 30.349091, "longitude": -86.216763,
                                     "bedrooms": 4.0, "bathrooms": 4.0, "sleeps": 8.0}
    assert am.json_ld_unit(page.split("</script>")[0] + "</script>") == {}


# --- New adapters ------------------------------------------------------------------------------------------------------

VRP_PAGE = """<form action="https://vrp.example/vrp/book/step3/" method="get" id="bookingform">
<input type="text" id="check-availability-arrival-date" name="check-availability-arrival-date" value="">
<input type="hidden" id="hiddenArrive" name="obj[Arrival]" value=""><input type="hidden" id="hiddenDepart" name="obj[Departure]" value="">
<select id="searchadults" name="obj[Adults]" onchange="checkAvailability();"><option value="1">1</option></select>
<select id="searchchildren" name="obj[Children]"><option value="0">0</option></select>
<input type="hidden" name="obj[Vendor]" value="Track"><input type="hidden" name="obj[PropID]" value="%s"></form>"""
VRP_QUOTE = {"arrival": "01/16/2027", "departure": "01/23/2027", "nights": 7, "TotalGoods": 13186, "TotalTax": 1582.32, "TotalCost": 14768.32,
             "InsuranceAmount": "1144.54",
             "Charges": [{"Description": "Rent", "Amount": "10876.00"}, {"Description": "Departure Cleaning Fee", "Amount": "770.00", "Required": True},
                         {"Description": "Resort Fee", "Amount": "1540.00", "Required": True}, {"Description": "FL State Tax", "Amount": "791.16"},
                         {"Description": "Walton County Tax", "Amount": "131.86"}, {"Description": "Bed Tax", "Amount": "659.30"}],
             "BookDetails": {"tax": [{"Description": "FL State Tax", "Amount": "791.16"}, {"Description": "Walton County Tax", "Amount": "131.86"},
                                     {"Description": "Bed Tax", "Amount": "659.30"}]}}
SOUTHERN_PAGE = '<div booking-data="{&quot;propertyInfo&quot;:{&quot;propertyId&quot;:5055,&quot;propertyName&quot;:&quot;Tofino&quot;}}"></div>'
SOUTHERN_QUOTE = {"quote": {"total": "$4,229.67", "travelInsurance": "$329.91", "sections": {
    "rent": {"total": "$3,434.25", "items": [{"label": "07/10/2027", "value": "$522.07"}]},
    "fees": {"total": "$485.00", "items": [{"label": "Service Fees", "value": "$100.00"}, {"label": "Cleaning Fee", "value": "$345.00"},
                                           {"label": "Damage Waiver Fee", "value": "$40.00"}]},
    "taxes": {"total": "$453.22", "items": [{"label": "Florida Sales Tax (6.0%)", "value": "$226.61"}, {"label": "Walton County Sales Tax (1%)", "value": "$37.79"},
                                            {"label": "Walton Lodging Tax (5.0%)", "value": "$188.82"}]}},
    "promoCode": {"valid": True, "name": "SVREARLY2027", "value": "$142.80"}, "promoType": "AutoApplied", "promoDiscount": 142.80}}
ES_PAGE = "<script>var unitData = {'unitID':30 };</script><script src=\"/website/assets/js/main.js?v=7.60\"></script>"
ES_QUOTE = {"body": {"result": "success", "guestDiscountedRent": "8,300.41", "nightlyRates": "8,300.41", "serviceFeeTotal": "0", "discount": "0.00",
                     "otherChargesItemized": [{"name": "Damage Waiver", "type": "required", "displayName": "Damage Waiver", "value": "169.00", "isRequired": True},
                                              {"name": "Guest Cleaning Fee", "type": "required", "displayName": "Cleaning Fee", "value": "420.00", "isRequired": True}],
                     "additionalAddonFee": [{"name": "Mid-Stay Clean", "type": "manual", "value": "420.00", "isRequired": False}],
                     "taxes": "1,054.73", "grandTotal": "9,944.14"}}
ASMX_PAGE = "<script src=\"/scripts/property-calendar.min.js\"></script><script>var cal = {rentalId: 4418044, reservationsUrl: '/r'};</script>"
ASMX_QUOTE = {"d": {"IsAvailable": True, "Message": None, "Charge": [
    {"Charge": "Rent Charges", "Amount": 5659.65}, {"Charge": "Departure Clean", "Amount": 330}, {"Charge": "Resort Fee per Night", "Amount": 98},
    {"Charge": "Wristbands", "Amount": 45}, {"Charge": "Tax", "Amount": 735.93}, {"Charge": "Total", "Amount": 6868.58}, {"Charge": "Deposit Due", "Amount": 2747.43}]}}
WANDER_PAGE = '<html lang="en" data-website-id="660568836512155950" data-org-id="x"><body>Heavenly Hideaway</body></html>'
WANDER_QUOTE = {"currency": "USD", "estimate": {"total": 325948, "totalNightsPrice": 276078, "totalWithFees": 294092, "couponOff": 0,
                                                "taxes": {"total": 31856, "breakdown": [{"name": "Special lodging tax", "amount": 13273},
                                                                                       {"name": "State sales tax", "amount": 15928},
                                                                                       {"name": "County sales tax", "amount": 2655}]}}}
QVR_PAGE = """<input id="unitCode" type="hidden" name="unit_code" value="1907-138598" aria-label="Unit Code">
<script>var VRAjax = {"ajaxurl":"https:\\/\\/qvr.example\\/wp-admin\\/admin-ajax.php","search_nonce":"x"};</script>"""
QVR_ERROR = {"data": '<div id="summary"><ul class="list-group"><li class="stay-error-list-item list-group-item">You are not authorized to use this service</li></ul></div>'}
QVR_AVAILABILITY = {"data": {"minimumNights": [
    {"base_rate": "$275-$648", "start_date": "2026-12-01", "end_date": "2027-02-28", "nights": 2, "type": "Nightly"},
    {"base_rate": "$359-$648", "start_date": "2027-09-01", "end_date": "2027-10-18", "nights": 2, "type": "Nightly"},
    {"base_rate": "$0", "start_date": "2027-10-19", "end_date": "2028-01-31", "nights": 2, "type": "Nightly"}]}}


def test_vrp_search_answered_with_html_cards_is_read():
    cards = ('<div class="abe-item map-filter-loader" data-vrp-index="0" data-vrp-address="3604 E. Co Hwy 30A A-8 Santa Rosa Beach, FL" '
             'data-vrp-city="Santa Rosa Beach" data-vrp-property-code="245" data-vrp-name="Palms Getaway" '
             'data-vrp-url="https://vrp.example/vrp/unit/Palms_Getaway-245-15" data-vrp-latitude="30.31292200" data-vrp-longitude="-86.11681580" '
             'data-vrp-beds="1" data-vrp-baths="2" data-vrp-sleeps="4" data-vrp-unitid="371">'
             '<div class="abe-item" data-vrp-address="" data-vrp-unitid="x"></div>')
    def handler(request):
        assert request.url.params["act"] == "search"
        return httpx.Response(200, text=cards, headers={"content-type": "text/html; charset=UTF-8"})
    store = ar.RawStore(Path(tempfile.mkdtemp()) / "manifest.json")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        session = ar.SiteSession(store, "vrp.example", ar.HttpTransport(client), lambda: False)
        units, replies = aa.VRP().inventory(session, "https://vrp.example", {})
    assert units == [{"site_id": "371", "url": "https://vrp.example/vrp/unit/Palms_Getaway-245-15", "title": "Palms Getaway",
                      "address": "3604 E. Co Hwy 30A A-8", "city": "Santa Rosa Beach", "latitude": 30.312922, "longitude": -86.1168158,
                      "bedrooms": 1.0, "bathrooms": 2.0, "sleeps": 4.0, "info": None}] and len(replies) == 1
    assert am.normalize_address(units[0]["address"]) == ("3604", "e 30a", "a 8")


def test_vrp_page_quote_and_refusals():
    info = aa.VRP().parse_page(VRP_PAGE % "1", "https://vacation.vrp.example/vrp/unit/103_North_Charles_Street-1-15")
    assert info["site_id"] == "1" and info["origin"] == "https://vacation.vrp.example" and info["fields"]["obj[Vendor]"] == "Track"
    assert "check-availability-arrival-date" not in info["fields"]
    assert aa.VRP().parse_page("<form id='x'></form>", "https://x.example/") is None
    quote = aa.VRP.parse_quote(VRP_QUOTE)
    assert (quote["rent"], quote["cleaning_fee"], quote["other_fees"], quote["taxes"], quote["total"]) == (10876.0, 770.0, 1540.0, 1582.32, 14768.32)
    assert (quote["total_includes_fees"], quote["total_includes_taxes"]) == (1, 1) and quote["excluded_items"][0]["amount"] == 1144.54
    assert aa.site_answer("Arrival date is beyond the maximum notice period. Please call to book.") == ("no_price", None)
    assert aa.site_answer("Unit has no availability for the dates specified.") == ("unavailable", None)
    assert aa.site_answer("This unit requires a minimum stay of 5 nights") == ("restricted", 5)


def test_company_front_end_quotes():
    southern = aa.PropertyQuoteV3.parse_quote(SOUTHERN_QUOTE["quote"])
    assert (southern["rent"], southern["cleaning_fee"], southern["taxes"], southern["total"]) == (3434.25, 345.0, 453.22, 4229.67)
    assert southern["fees"][-1] == {"name": "Promotion SVREARLY2027 (AutoApplied)", "amount": -142.8} and southern["total_includes_taxes"] == 1
    assert southern["excluded_items"][0]["amount"] == 329.91
    assert aa.PropertyQuoteV3().parse_page(SOUTHERN_PAGE, "https://sr.example/property/abc")["site_id"] == "5055"
    es = aa.ExceptionalStay.parse_quote(ES_QUOTE["body"])
    assert (es["rent"], es["cleaning_fee"], es["other_fees"], es["taxes"], es["total"], es["total_includes_fees"]) == (8300.41, 420.0, 169.0, 1054.73, 9944.14, 1)
    assert aa.ExceptionalStay().parse_page(ES_PAGE, "https://es.example/vacation-rentals/x")["site_id"] == "30"
    assert aa.AsmxGetQuote().parse_page(ASMX_PAGE, "https://nd.example/rentals/unit/x")["site_id"] == "4418044"
    assert aa.Wander().parse_page(WANDER_PAGE, "https://www.wa.example/property/660559395444228375/heavenly")["website_id"] == "660568836512155950"
    assert aa.Wander().parse_page(WANDER_PAGE, "https://www.wa.example/listing/heavenly/") is None
    assert aa.Q4VR().parse_page(QVR_PAGE, "https://qvr.example/vacation_rentals/a/") == {
        "site_id": "1907-138598", "ajax_url": "https://qvr.example/wp-admin/admin-ajax.php", "page_url": "https://qvr.example/vacation_rentals/a/",
        "origin": "https://qvr.example"}


class NewSites:
    """Synthetic sites for the new adapters, an address-matched company list and an own-inventory community."""

    def __init__(self, refuse_after=None):
        self.seen = []
        self.lock = threading.Lock()
        self.refuse_after = refuse_after

    def __call__(self, request):
        with self.lock:
            self.seen.append(request)
        url, host, path = request.url, request.url.host, request.url.path
        if host == "www.vrp.example":
            if path.startswith("/vrp/unit/"):
                return html(VRP_PAGE % path.split("-")[-2])
            if path == "/" and url.params.get("act") == "search":
                return json_reply({"count": 4, "results": [
                    {"id": "1", "Name": "103 North Charles", "Address1": "103 North Charles Street", "City": "Alys Beach", "lat": "30.2866", "long": "-86.0298",
                     "Bedrooms": "4", "Bathrooms": "4.5", "Sleeps": "8", "page_slug": "103_North_Charles_Street-1-15"},
                    {"id": "2", "Name": "On Book>Direct by url", "Address1": "5 Main Street", "City": "Alys Beach", "lat": "30.2867", "long": "-86.0297",
                     "Bedrooms": "3", "Bathrooms": "3", "Sleeps": "6", "page_slug": "Five_Main-2-15"},
                    {"id": "3", "Name": "On Book>Direct by address", "Address1": "9 Somerset Street", "City": "Alys Beach", "lat": "30.2868", "long": "-86.0296",
                     "Bedrooms": "2", "Bathrooms": "2", "Sleeps": "4", "page_slug": "Nine_Somerset-3-15"},
                    {"id": "4", "Name": "Elsewhere", "Address1": "1 Barrett Square", "City": "Rosemary Beach", "lat": "30.28", "long": "-86.01",
                     "Bedrooms": "2", "Bathrooms": "2", "Sleeps": "4", "page_slug": "Barrett-4-15"}]})
            if path == "/" and url.params.get("act") == "checkavailability":
                assert url.params["obj[Adults]"] == "2" and url.params["obj[PropID]"] in ("1", "2", "3")
                if url.params["obj[Arrival]"] == "10/16/2027":
                    return json_reply({"Error": "Arrival date is beyond the maximum notice period. Please call to book."})
                return json_reply(VRP_QUOTE)
        if host == "www.rescms.example":                     # an old link that 404s, and the company's sitemap with addresses
            if path == "/old":
                return html("<title>Page not found</title>", 404)
            if path == "/sitemap.xml":
                return httpx.Response(200, text="<sitemapindex><sitemap><loc>https://www.rescms.example/sitemap-1.xml</loc></sitemap></sitemapindex>",
                                      headers={"content-type": "application/xml"})
            if path == "/sitemap-1.xml":
                return httpx.Response(200, text="<urlset><url><loc>https://www.rescms.example/rentals/a</loc></url>"
                                                "<url><loc>https://www.rescms.example/rentals/b</loc></url><url><loc>https://www.rescms.example/blog/x</loc></url></urlset>",
                                      headers={"content-type": "application/xml"})
            if path in ("/rentals/a", "/rentals/b"):
                street = "43 Gulf Shore Drive" if path.endswith("a") else "112 Savelle Drive"
                return html(RESCMS_PAGE.replace('"eid":"261"', f'"eid":"{261 if path.endswith("a") else 262}"') +
                            f'<script>{{"field_location":{{"und":[{{"lid":"1","street":"{street}","additional":"","city":"Santa Rosa Beach",'
                            '"latitude":"30.3324","longitude":"-86.1756"}]}}</script><div class="rc-lodging-beds rc-lodging-detail">5 Bedrooms</div>'
                            '<div class="rc-lodging-baths rc-lodging-detail">5 Baths</div>')
            if path == "/rescms/ajax/item/pricing/simple":
                return json_reply({"status": 1, "content": RESCMS_PRICE, "reveals": ""})
            if path == "/rescms/ajax/item/pricing/quote":
                return json_reply({"status": 1, "content": RESCMS_QUOTE, "reveals": ""})
        if host == "qvr.example":
            if path == "/vacation_rentals/a/":
                return html(QVR_PAGE)
            if path == "/wp-admin/admin-ajax.php":
                return json_reply(QVR_ERROR if url.params["action"] == "q4vr_stay" else QVR_AVAILABILITY)
        if host in ("www.guard.example", "www.guard2.example"):
            with self.lock:
                count = sum(r.url.host == host for r in self.seen)
            if self.refuse_after and count > self.refuse_after:
                return html("Forbidden", 403)
            if path.startswith("/rentals/"):
                return html(TRACK_PAGE % "194")
            if path == "/ajax/quote":
                return html(TRACK_QUOTE)
        raise AssertionError(f"Beklenmeyen istek: {request.method} {url}")


def test_address_fallback_reads_the_company_sitemap_and_records_the_method(tmp_path):
    sites = [site("rescms.example", "rescms", inventory={"source": "sitemap", "url": "https://www.rescms.example/sitemap.xml", "pattern": r"/rentals/"})]
    listings = [bd(1, "https://www.rescms.example/old", address="43 Gulf Shore Dr.", bedrooms=5, lat=30.3324, lon=-86.1756),
                bd(2, "https://www.rescms.example/old", address="7 Nowhere Lane", bedrooms=5),
                bd(3, "https://www.rescms.example/old", address="112 Savelle Dr.", bedrooms=4)]
    mock = NewSites()
    result = run(tmp_path, mock, sites, listings)
    rows = {r["lodging_id"]: r for r in result.records}
    assert (rows[1]["page_status"], rows[1]["match_method"], rows[1]["link_status"], rows[1]["site_listing_id"]) == ("matched", "address", "not_found", "261")
    assert "43 gulf shore dr" in rows[1]["match_note"] and rows[1]["page_url"] == "https://www.rescms.example/rentals/a"
    assert (rows[2]["page_status"], rows[2]["match_method"]) == ("not_found", None) and "aday yok" in rows[2]["match_note"]
    assert rows[3]["match_method"] is None and "4 oda" in rows[3]["match_note"]                            # 5 bedrooms on the site
    assert quotes_of(result)[(1, "winter")]["total"] == 1396.21 and (2, "winter") not in quotes_of(result)
    company = result.related["companies"][0]
    assert company["inventory_count"] == 2 and len(company["inventory_raw_sha256"]) == 4                   # index, map, two pages
    assert company["match_counts"] == {"link": 0, "address": 1, "location": 0}
    assert not any(r.url.path == "/blog/x" for r in mock.seen)
    assert sum(r.url.path == "/rentals/a" for r in mock.seen) == 1                                        # the page read for the list is reused


def test_own_inventory_skips_other_communities_and_homes_already_on_bookdirect(tmp_path):
    sites = [site("vrp.example", "vrp", inventory={"source": "platform", "origin": "https://www.vrp.example"}, own_region_id="alys-beach",
                  own_city="Alys Beach")]
    listings = [bd(10, "https://www.vrp.example/vrp/unit/Five_Main-2-15/", bedrooms=3, regions=("alys-beach",)),
                bd(11, "https://other.example/x", address="9 Somerset St", bedrooms=2, regions=("alys-beach",))]
    result = run(tmp_path, NewSites(), sites, listings)
    own = result.related["own_listings"]
    assert [(o["site_listing_id"], o["region_id"], o["address"]) for o in own] == [("1", "alys-beach", "103 North Charles Street")]
    company = result.related["companies"][0]
    assert (company["own_count"], company["own_outside"], company["own_on_bookdirect"]) == (1, 1, 2)
    own_quotes = {q["window_key"]: q for q in result.related["own_quotes"]}
    assert own_quotes["winter"]["total"] == 14768.32 and own_quotes["winter"]["adults"] == 2
    assert (own_quotes["fall-2027"]["status"], own_quotes["fall-2027"]["available"]) == ("no_price", None)
    assert quotes_of(result)[(10, "winter")]["total"] == 14768.32 and result.metadata["own_listings"] == 1


def test_published_rent_is_kept_apart_from_the_quotes(tmp_path):
    result = run(tmp_path, NewSites(), [site("qvr.example", "qvr")], [bd(20, "https://qvr.example/vacation_rentals/a/")])
    quotes = quotes_of(result)
    assert {k[1]: q["status"] for k, q in quotes.items()} == {"winter": "no_price", "fall-2027": "no_price"}
    assert "not authorized" in quotes[(20, "winter")]["message"] and quotes[(20, "winter")]["total"] is None
    published = {p["window_key"]: p for p in result.related["published"]}
    assert set(published) == {"winter"}                    # fall 2027 crosses two seasons (and the second has no rate)
    assert (published["winter"]["rent_low"], published["winter"]["rent_high"], published["winter"]["rate_period"]) == (1925.0, 4536.0, "night")
    assert "vergi ve ücretler hariç" in published["winter"]["basis"]


def test_guest_count_is_stored_and_the_bedroom_rule_respects_capacity(tmp_path):
    seen = []
    def handler(request):
        seen.append(request)
        return NewSites()(request)
    sites = [site("rescms.example", "rescms", guest_rule="bedrooms_x2"), site("guard.example", "track")]
    listings = [bd(1, "https://www.rescms.example/rentals/a", bedrooms=4, sleeps=6), bd(2, "https://www.guard.example/rentals/9", bedrooms=5)]
    result = run(tmp_path, handler, sites, listings)
    quotes = quotes_of(result)
    assert (quotes[(1, "winter")]["adults"], quotes[(1, "winter")]["children"]) == (6, 0)          # 4 x 2 = 8, capped at 6
    assert {r.url.params["rcav[adult]"] for r in seen if r.url.path.endswith("/pricing/simple")} == {"6"}
    assert (quotes[(2, "winter")]["adults"], quotes[(2, "winter")]["children"]) == (None, None)    # Track's request has no guest field
    assert ar.guests_for({"guest_rule": "two_adults"}, 6, 12) == {"adults": 2, "children": 0}
    assert ar.guests_for({"guest_rule": "bedrooms_x2"}, 1, None) == {"adults": 2, "children": 0}
    assert ar.guests_for({"guest_rule": "bedrooms_x2"}, None, 8) == {"adults": 2, "children": 0}


class Browser:
    """A visible-browser stand-in: forwards requests to the synthetic sites and records them."""
    kind = "browser"

    def __init__(self, handler):
        self.handler, self.closed = handler, False

    def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
        request = httpx.Request(method, url, params=params, data=data, json=json_body, headers=headers)
        response = self.handler(request)
        return response.status_code, str(request.url), dict(response.headers), response.content

    def close(self):
        self.closed = True


def test_protected_sites_use_the_browser_six_seconds_apart_one_at_a_time_and_stop_at_the_first_refusal(tmp_path, monkeypatch):
    pauses = []
    monkeypatch.setattr(ar, "pause", lambda seconds, canceled: pauses.append(round(seconds)))
    mock = NewSites(refuse_after=3)
    opened = []
    def verifier(domain, url, canceled, timeout):
        opened.append(domain)
        return Browser(mock)
    sites = [site("guard.example", "track", protected=1), site("guard2.example", "track", protected=1)]
    listings = [bd(i, f"https://www.{d}/rentals/{i}") for d, ids in (("guard.example", (1, 2, 3)), ("guard2.example", (4,))) for i in ids]
    result = run(tmp_path, mock, sites, listings, verifier=verifier)
    companies = {c["domain"]: c for c in result.related["companies"]}
    guarded = companies["guard.example"]
    assert guarded["status"] == "stopped_blocked" and "yeniden denenmedi" in guarded["message"] and guarded["protected"] == 1
    assert guarded["request_count"] == 4                     # page, 2 quotes, the next page refused: no retry, no home-page check
    assert [r.url.path for r in mock.seen if r.url.host == "www.guard.example"][-1] == "/rentals/2"
    assert companies["guard2.example"]["status"] == "done" and sorted(opened) == ["guard.example", "guard2.example"]
    assert pauses and set(pauses) == {6}                      # every gap between two requests to one protected site
    hosts = [r.url.host for r in mock.seen]
    first = hosts[0]
    assert hosts == [first] * hosts.count(first) + [h for h in hosts if h != first]       # one protected company at a time
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert {e["transport"] for e in manifest["responses"]} == {"browser"}                 # never plain HTTP to a protected site
    rows = {r["lodging_id"]: r for r in result.records}
    assert rows[3]["page_status"] == "not_queried" and "durduruldu" in rows[3]["message"]


class Waiter:
    """A browser stand-in with the end-of-run wait: `clear` are the sites the user verifies during the wait."""

    def __init__(self, handler, challenged, clear):
        self.handler, self.challenged, self.clear = handler, set(challenged), set(clear)
        self.events = []

    def __call__(self, domain, url, canceled, timeout):
        self.events.append(("open", domain, timeout))
        return None if domain in self.challenged else Browser(self.handler)

    def wait_all(self, sites, canceled, timeout, waiting=None):
        self.events.append(("wait_all", tuple(sorted(sites)), timeout))
        if waiting:
            waiting(", ".join(sorted(sites)))
            waiting(None)
        self.challenged -= self.clear
        return set(sites) & self.clear


def test_a_site_waiting_for_verification_is_left_for_the_end_and_one_wait_covers_it(tmp_path, monkeypatch):
    monkeypatch.setattr(ar, "PROTECTED_GAP", 0)
    mock = NewSites()
    sites = [site("guard.example", "track", protected=1), site("guard2.example", "track", protected=1)]
    listings = [bd(1, "https://www.guard.example/rentals/1"), bd(2, "https://www.guard2.example/rentals/2")]
    waiter, waits = Waiter(mock, {"guard.example"}, {"guard.example"}), []
    result = run(tmp_path, mock, sites, listings, verifier=waiter, waiting=waits.append)
    assert waiter.events == [("open", "guard.example", 20), ("open", "guard2.example", 20),
                             ("wait_all", ("guard.example",), 15 * 60), ("open", "guard.example", 20)]     # the waiting site goes last
    assert waits == ["guard.example", None]
    companies = {c["domain"]: c for c in result.related["companies"]}
    assert companies["guard.example"]["status"] == "done" and companies["guard.example"]["matched_count"] == 1
    assert {(q["lodging_id"], q["window_key"]) for q in result.related["quotes"]} == {(1, "winter"), (1, "fall-2027"), (2, "winter"), (2, "fall-2027")}
    assert [m["host"] for m in result.related["browser_hosts"]] == ["guard.example"]

    skipped = run(tmp_path / "b", NewSites(), sites, listings, verifier=Waiter(NewSites(), {"guard.example"}, set()))
    companies = {c["domain"]: c for c in skipped.related["companies"]}
    assert (companies["guard.example"]["status"], companies["guard.example"]["verification"]) == ("verification_timeout", "timeout")
    assert companies["guard2.example"]["status"] == "done"
    rows = {r["lodging_id"]: r for r in skipped.records}
    assert rows[1]["page_status"] == "not_queried" and "süresinde tamamlanmadı" in rows[1]["message"]


def test_a_host_marked_once_is_read_only_with_the_browser_and_the_mark_is_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(ar, "PROTECTED_GAP", 0)
    from studio.sources import browser_verification as bv
    db = Database(tmp_path / "studio.sqlite3"); db.initialize()
    with db.connect() as con:
        bv.mark_hosts(con, [{"host": "www.guard.example", "url": "https://www.guard.example/rentals/1", "reason": "doğrulama sayfası"}], "test")
    with db.connect() as con:
        bv.mark_hosts(con, [{"host": "guard.example", "url": "https://www.guard.example/rentals/2", "reason": "doğrulama sayfası"}], "test")
        row = dict(con.execute("SELECT * FROM browser_hosts").fetchone())
    assert db.context("30a").browser_hosts == ("guard.example",) and row["url"].endswith("/rentals/2") and row["first_seen_at"] <= row["last_seen_at"]
    mock, opened = NewSites(), []
    def verifier(domain, url, canceled, timeout):
        opened.append(domain)
        return Browser(mock)
    config = {"sites": [site("guard.example", "track")], "windows": WINDOWS, "browser_hosts": db.context("30a").browser_hosts,
              "input": {"run_id": "lodging-run", "searched_on": "2026-10-07", "listings": [bd(1, "https://www.guard.example/rentals/1")]}}
    with httpx.Client(transport=httpx.MockTransport(lambda request: pytest.fail(f"plain HTTP to {request.url}"))) as client:
        result = ar.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config, client=client, verifier=verifier,
                            today=TODAY)
    assert opened == ["guard.example"] and result.related["companies"][0]["protected"] == 1
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert {e["transport"] for e in manifest["responses"]} == {"browser"}


def test_the_browser_is_started_like_an_ordinary_application_and_reused(tmp_path, monkeypatch):
    from studio.sources import browser_verification as bv
    command = bv.launch_command("C:/Chrome/chrome.exe", tmp_path / "profile")
    assert command == ["C:/Chrome/chrome.exe", f"--user-data-dir={tmp_path / 'profile'}", "--remote-debugging-port=0"]
    assert not any(flag.startswith(("--enable-automation", "--disable-blink-features", "--headless", "--remote-debugging-pipe",
                                    "--disable-extensions", "--no-sandbox", "--user-agent", "--lang")) for flag in command)
    assert bv.profile_root().name == "30a-studio" and bv.profile_root().parent.name == "tarayici-profili"
    monkeypatch.setattr(bv, "find_browser", lambda: tmp_path / "chrome.exe")
    profile, spawned = tmp_path / "profile", []
    def spawn(cmd):
        spawned.append(cmd)
        (profile / "DevToolsActivePort").write_text("9555\n/devtools/browser/abc\n", encoding="utf-8")
    endpoint, launched = bv.ensure_browser(profile, spawn=spawn, check=lambda url: url == "http://127.0.0.1:9555", wait=2)
    assert (endpoint, launched) == ("http://127.0.0.1:9555", True) and spawned[0][1:] == [f"--user-data-dir={profile}", "--remote-debugging-port=0"]
    endpoint, launched = bv.ensure_browser(profile, spawn=spawn, check=lambda url: True, wait=2)
    assert (endpoint, launched) == ("http://127.0.0.1:9555", False) and len(spawned) == 1        # an open browser is reused, never opened twice


def test_the_end_of_run_wait_lists_the_sites_once_and_times_out(monkeypatch):
    from studio.sources import browser_verification as bv
    class Page:
        def __init__(self, looks):
            self.looks = list(looks)
        def title(self):
            return ""
        def content(self):
            return self.looks.pop(0) if len(self.looks) > 1 else self.looks[0]
    challenge, normal = "<title>Just a moment...</title>", "<title>Grill</title><h1>Grill</h1>"
    clock = iter(range(0, 10_000, 100))
    monkeypatch.setattr(bv.time, "monotonic", lambda: next(clock))
    waits = []
    cleared = bv.wait_for_user({"a.example": Page([challenge, normal]), "b.example": Page([challenge])}, lambda: False, 900, waits.append,
                               sleep=lambda s: None)
    assert cleared == {"a.example"} and waits == ["a.example, b.example", None]


def test_a_block_page_stops_a_protected_company_before_any_request(tmp_path):
    from studio.sources.browser_verification import SiteBlocked
    def verifier(domain, url, canceled, timeout):
        raise SiteBlocked("guard.example: Attention Required!")
    mock = NewSites()
    result = run(tmp_path, mock, [site("guard.example", "track", protected=1)], [bd(1, "https://www.guard.example/rentals/1")], verifier=verifier)
    company = result.related["companies"][0]
    assert company["status"] == "stopped_blocked" and "engel sayfası" in company["message"] and mock.seen == []
    unavailable = run(tmp_path / "b", mock, [site("guard.example", "track", protected=1)], [bd(1, "https://www.guard.example/rentals/1")])
    assert unavailable.related["companies"][0]["status"] == "verification_unavailable" and mock.seen == []


# --- Storage, summary, configuration and migration ----------------------------------------------------------------------

def test_fresh_database_has_v12_configuration_window_and_nws_method(tmp_path):
    db = Database(tmp_path / "studio.sqlite3"); db.initialize()
    context = db.context("30a")
    sites = {s["domain"]: s for s in context.agency["sites"]}
    assert len(sites) == len(thirty_a.AGENCY_SITES) + len(thirty_a.AGENCY_SITES_V12)
    assert sites["oversee.us"]["protected"] == 1 and sites["oversee.us"]["inventory"] == {"source": "platform", "origin": "https://oversee.us"}
    assert sites["grayt30avacations.com"]["aliases"] == ["royaldestinations.com"] and sites["benchmark30a.com"]["guest_rule"] == "two_adults"
    assert (sites["alysbeach.com"]["own_region_id"], sites["alysbeach.com"]["own_city"]) == ("alys-beach", "Alys Beach")
    assert [w["window_key"] for w in context.lodging["windows"]][-1] == "fall-2027"
    nws = next(s for s in db.sources() if s["url"] == "https://www.weather.gov/")
    assert nws["method"] == "API"
    with db.connect() as con:
        for statement in ("UPDATE destination_agency_sites SET guest_rule='everyone' WHERE domain='oversee.us'",
                          "UPDATE destination_agency_sites SET aliases='x' WHERE domain='oversee.us'",
                          "UPDATE destination_agency_sites SET own_city=NULL WHERE domain='alysbeach.com'",
                          "UPDATE destination_agency_sites SET own_region_id='nowhere' WHERE domain='alysbeach.com'"):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute(statement)


def make_v11(path):
    """A v11 database with one agency-lodging-rates/1 run (one ResCMS and one Track listing) and the old NWS defaults."""
    from studio.migration_v11 import upgrade_v11
    from tests.test_agency_rates import make_v10
    make_v10(path)
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        con.execute("BEGIN IMMEDIATE"); upgrade_v11(con); con.commit()
        source = con.execute("SELECT id FROM sources WHERE url LIKE '%kiralama-sirketleri'").fetchone()[0]
        con.execute("""INSERT INTO sources VALUES ('nws','National Weather Service','https://www.weather.gov/','Hava','Tüm 30A','Belirlenecek',
            'Haftalık',?,1,1,'2026-09-01','2026-09-01','30a',NULL)""",
                    ("Hava verisi için başlangıç kaynağı. Bölge koordinatları ve veri uçları sonraki aşamada belirlenecek.",))
        con.execute("""INSERT INTO sources VALUES ('nws2','Kullanıcının kopyası','https://www.weather.gov/?x','Hava','Tüm 30A','Belirlenecek',
            'Haftalık','Kullanıcı notu',1,1,'2026-09-01','2026-09-01','30a',NULL)""")
        con.execute("INSERT INTO jobs(id,kind,title,status,created_at,source_id,destination_id) VALUES ('aj','source_collection','old','done','now',?,'30a')", (source,))
        con.execute("""INSERT INTO source_runs(id,source_id,job_id,status,connector_name,connector_version,destination_id,metadata)
            VALUES ('aj',?,'aj','done','agency-lodging-rates','agency-lodging-rates/1','30a','{}')""", (source,))
        con.execute("INSERT INTO agency_rate_snapshots VALUES ('aj','lj','2026-10-08',5,2)")
        con.execute("INSERT INTO agency_rate_windows VALUES ('aj','winter-2027','Kış 2027','2027-01-16','2027-01-23',7,'queried')")
        for domain, adapter in (("benchmark30a.com", "rescms"), ("30aescapes.com", "track")):
            con.execute("INSERT INTO agency_rate_companies VALUES ('aj',?,?,?,'done',1,1,1,1,2,NULL,NULL)", (domain, domain, adapter))
        for lodging_id, domain in ((7, "benchmark30a.com"), (8, "30aescapes.com")):
            con.execute("""INSERT INTO agency_rate_listings VALUES ('aj',?,?,3,'["seaside"]',?,?,?,'matched',?,200,?,NULL)""",
                        (lodging_id, f"L{lodging_id}", f"https://www.{domain}/x", domain, domain, f"https://www.{domain}/x", str(lodging_id)))
            con.execute("""INSERT INTO agency_rate_quotes (run_id,lodging_id,window_key,status,available,rent,total,queried_at,queried_url,raw_sha256)
                VALUES ('aj',?,'winter-2027','priced',1,1000,1200,'t','https://x.example/q','["a"]')""", (lodging_id,))
        con.commit()


def test_v11_to_v12_migration_backfills_old_runs_and_adds_configuration(tmp_path):
    path = tmp_path / "studio.sqlite3"; make_v11(path)
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 11
        before = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in table_counts(con)}
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        assert con.execute("PRAGMA user_version").fetchone()[0] == 12
        assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        counts = table_counts(con)
        for table in ("agency_rate_own_listings", "agency_rate_own_quotes", "agency_rate_published"):
            assert counts[table] == 0
        assert counts["destination_agency_sites"] == len(thirty_a.AGENCY_SITES) + len(thirty_a.AGENCY_SITES_V12)
        assert counts["destination_lodging_windows"] == len(thirty_a.LODGING_WINDOWS) + 1
        rows = {r["lodging_id"]: dict(r) for r in con.execute("SELECT * FROM agency_rate_listings")}
        assert {i: (r["match_method"], r["link_status"]) for i, r in rows.items()} == {7: ("link", "matched"), 8: ("link", "matched")}
        quotes = {r["lodging_id"]: (r["adults"], r["children"]) for r in con.execute("SELECT * FROM agency_rate_quotes")}
        assert quotes == {7: (2, 0), 8: (None, None)}                       # v1 sent two adults on ResCMS, no guest field on Track
        companies = {r["domain"]: (r["protected"], r["guest_rule"]) for r in con.execute("SELECT * FROM agency_rate_companies")}
        assert set(companies.values()) == {(0, "two_adults")}
        nws = con.execute("SELECT method, notes FROM sources WHERE url='https://www.weather.gov/'").fetchone()
        assert nws["method"] == "API" and nws["notes"].startswith("30A koridorundaki")
        assert con.execute("SELECT method FROM sources WHERE id='nws2'").fetchone()[0] == "Belirlenecek"     # only the NWS default row
        for table in ("jobs", "source_runs", "agency_rate_snapshots", "agency_rate_windows", "lodging_listings"):
            assert [tuple(r) for r in con.execute(f'SELECT * FROM "{table}" ORDER BY rowid')] == [tuple(r) for r in before[table]]
    backup, = (tmp_path / "backups").glob("*-v11-*.sqlite3")
    with sqlite3.connect(backup) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 11
    Database(path).initialize()                                                              # idempotent
    with sqlite3.connect(path) as con:
        assert table_counts(con)["destination_agency_sites"] == counts["destination_agency_sites"]


def test_v11_to_v12_failure_rolls_back_everything(tmp_path, monkeypatch):
    from studio import database
    path = tmp_path / "studio.sqlite3"; make_v11(path)
    with sqlite3.connect(path) as con:
        before = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in table_counts(con)}
    original = database.upgrade_v12
    def fail(con): original(con); raise RuntimeError("after all DDL, backfill and configuration")
    with monkeypatch.context() as m:
        m.setattr(database, "upgrade_v12", fail)
        with pytest.raises(RuntimeError):
            Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 11
        assert {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in table_counts(con)} == before
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 12


def test_summary_counts_methods_own_inventory_and_published_rents_apart(tmp_path):
    db = Database(tmp_path / "studio.sqlite3"); db.initialize()
    sites = [site("rescms.example", "rescms", inventory={"source": "sitemap", "url": "https://www.rescms.example/sitemap.xml", "pattern": r"/rentals/"}),
             site("vrp.example", "vrp", inventory={"source": "platform", "origin": "https://www.vrp.example"}, own_region_id="alys-beach", own_city="Alys Beach"),
             site("qvr.example", "qvr")]
    listings = [bd(1, "https://www.rescms.example/old", address="43 Gulf Shore Dr.", bedrooms=5, regions=("alys-beach",)),
                bd(2, "https://www.rescms.example/rentals/a", bedrooms=3, regions=("alys-beach",)),
                bd(3, "https://qvr.example/vacation_rentals/a/", regions=("alys-beach",))]
    result = run(tmp_path, NewSites(), sites, listings)
    connector = ar.AgencyRatesConnector()
    with db.connect() as con:
        con.execute("PRAGMA foreign_keys=OFF")          # the synthetic run has no Book>Direct lodging run behind it
        con.execute("INSERT INTO jobs(id,kind,title,status,created_at,destination_id) VALUES ('r','source_collection','t','done','now','30a')")
        con.execute("""INSERT INTO source_runs(id,job_id,status,connector_name,connector_version,destination_id,metadata)
            VALUES ('r','r','done','agency-lodging-rates','agency-lodging-rates/2','30a','{}')""")
        connector.store_records(con, "r", result.records, result.related)
        summary = ar.summarize(con, "r", ["alys-beach"], {"alys-beach": "Alys Beach"})
        listing_view = ar.region_listings(con, "r", "alys-beach")
    cell = next(c for c in summary["cells"] if c["window_key"] == "winter")
    assert cell["priced_count"] == 2 and cell["by_method"] == {"link": 1, "address": 1, "location": 0}
    assert cell["total_median"] == 1396.21                                                 # the published rent is not in the totals
    assert cell["published"] == {"count": 1, "low_median": 1925.0, "high_median": 4536.0}
    assert cell["own_listing_count"] == 3 and cell["own"]["priced_count"] == 3 and cell["own"]["total_median"] == 14768.32     # none of the three is on Book>Direct here
    assert summary["coverage"]["methods"] == {"link": 2, "address": 1, "location": 0}      # matched listings (one link without a quote price) and summary["coverage"]["own_listings"] == 3
    assert "2 yetişkin" in summary["guest_label"] and "kendi envanteri" in summary["source_note"]
    assert listing_view["own"][0]["quotes"]["winter"]["total"] == 14768.32
    assert next(l for l in listing_view["listings"] if l["lodging_id"] == 3)["published"]["winter"]["rent_high"] == 4536.0
