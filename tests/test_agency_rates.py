"""Rental company prices from the companies' own sites: adapters, url matching, per-company isolation, verification, storage, API.

Synthetic pages in the platforms' real shapes through httpx.MockTransport only; suite-wide no_real_http prevents internet access.
"""
import json
import sqlite3
import threading
from datetime import date
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Database
from studio.destinations import thirty_a
from studio.sources import agency_adapters as aa
from studio.sources import agency_rates as ar
from studio.sources.base import CollectionCanceled, SourceError
from tests.legacy import AGENCY_URL, V11_TABLES, V12_TABLES
from tests.test_beaches import HEADERS, finished
from tests.test_climate import table_counts
from tests import test_lodging as tl

TODAY = date(2026, 10, 8)
WINDOWS = [{"window_key": "past", "label": "Geçmiş", "checkin": "2026-01-03", "checkout": "2026-01-10"},
           {"window_key": "fall", "label": "Sonbahar", "checkin": "2026-10-17", "checkout": "2026-10-24"},
           {"window_key": "winter", "label": "Kış", "checkin": "2027-01-16", "checkout": "2027-01-23"}]
SITES = [{"domain": "rescms.example", "company": "ResCMS Rentals", "adapter": "rescms", "enabled": 1},
         {"domain": "track.example", "company": "Track Getaways", "adapter": "track", "enabled": 1},
         {"domain": "stream.example", "company": "Stream Cottages", "adapter": "streamline", "enabled": 1},
         {"domain": "router.example", "company": "Router Realty", "adapter": "vr_router", "enabled": 1}]

RESCMS_PAGE = """<html><body><script>jQuery.extend(Drupal.settings, {"rcItemAvailForm":[{"id":null,"df":"mm\\/dd\\/yy",
"txt":{"sd":"Please select","mns":"night minimum stay"},"mns":"1","tdd":0,"tdc":"7","sub":false,"eid":"261",
"avail":[{"b":"2026-10-08","e":"2027-12-31","a":"1","q":"1","s":"1","x":""}],
"restr":[{"b":"2026-10-08","e":"2026-12-31","t":null,"mn":2,"mx":null,"i":null},{"b":"2027-01-01","e":"2027-03-31","t":6,"mn":3,"mx":null,"i":null}],
"turn":[{"b":"2026-10-09","e":"2026-10-09","t":"X"}]}]});</script></body></html>"""
RESCMS_PRICE = ('<div class="rc-item-pricing"><div class="rc-item-price"><span class="rcav-dates">Sat Jan 16 - Sat Jan 23, 2027</span>'
                '<span class="rc-price">$1,247</span><a href="/rescms/ajax/item/pricing/quote?rcav%5Bbegin%5D=01/16/2027&amp;rcav%5Bend%5D=01/23/2027'
                '&amp;rcav%5Beid%5D=261&amp;rcav%5BIDs%5D%5B8%5D%5B0%5D=2261-210212" data-rc-ua="{}" class="rc-item-quote-link">Show Detailed Quote</a></div></div>')
RESCMS_QUOTE = """<div class="rc-item-quote"><table><tbody>
 <tr class="line-item odd"><td>Lodging: 19 Moonlit Shores Ln<br /></td><td class="amount">$705.99</td></tr>
 <tr class="line-item even"><td>Cleaning Fee<br /></td><td class="amount">$325.00</td></tr>
 <tr class="line-item odd"><td>Damage Waiver<br /></td><td class="amount">$125.00</td></tr>
 <tr class="line-item even"><td>Booking Fee<br /></td><td class="amount">$90.63</td></tr>
 <tr class="line-item forced-choice declined odd"><td>Travel Insurance (optional) <span class="line-item-extra">*Declined*</span><br /><span class="line-item-desc"><p>Premium 7.75%</p></span></td><td class="amount">$100.34</td></tr>
 <tr class="sub-total even"><th>Sub-Total</th><td class="amount"><b>$1,246.62</b></td></tr>
 <tr class="tax odd"><th>Tax</th><td class="amount"><b>$149.59</b></td></tr>
 <tr class="total even"><th>Total</th><td class="amount"><b>$1,396.21</b></td></tr>
</tbody></table></div>"""
TRACK_PAGE = """<form id="pdpDatesForm"><input type="hidden" name="propertyID" value="%s"><input type="hidden" name="roomTypeID" value="">
<input type="hidden" name="propertyName" value="Mirasol &amp; Blue"><input type="hidden" name="hash" value=""></form>
<script>var siteFolder = '/'; var siteURLEnding = '';</script>"""
TRACK_QUOTE = """<form name="quoteForm" id="quoteForm"><ul class="pdp-quote-list">
<li class="pdp-quote-item"><span class="pdp-quote-item-text">Rent</span><span class="pdp-quote-item-price" data-price="2303.0000">$2,303<sup>.00</sup></span></li>
<li class="pdp-quote-item pdp-quote-item-toggle"><span class="pdp-quote-item-toggle-group"><button type="button"><span class="pdp-quote-item-toggle-group">
<span class="pdp-quote-item-text">Fees</span></span><span class="pdp-quote-item-price" data-price="689">$689<sup>.00</sup></span></button></span>
<ul class="pdp-quote-item-toggle-list">
<li class="pdp-quote-item"><span class="pdp-quote-item-group"><span class="pdp-quote-item-text">Cleaning Fee</span></span><span class="pdp-quote-item-price" data-price="380.0000">$380</span></li>
<li class="pdp-quote-item"><span class="pdp-quote-item-group"><span class="pdp-quote-item-text">Reservation Fee</span></span><span class="pdp-quote-item-price" data-price="210.0000">$210</span></li>
<li class="pdp-quote-item"><span class="pdp-quote-item-group"><span class="pdp-quote-item-text">Damage Waiver</span></span><span class="pdp-quote-item-price" data-price="99.0000">$99</span></li>
</ul></li>
<li class="pdp-quote-item"><span class="pdp-quote-item-text">Taxes</span><span class="pdp-quote-item-price" data-price="347.16">$347<sup>.16</sup></span></li>
<li class="pdp-quote-item pdp-quote-total"><span class="pdp-quote-item-text">Total</span><span class="pdp-quote-item-price" data-price="3339.16">$3,339<sup>.16</sup></span></li>
</ul></form>"""
TRACK_QUOTE_NO_FEES = """<ul class="pdp-quote-list"><li class="pdp-quote-item"><span class="pdp-quote-item-text">Rent</span><span class="pdp-quote-item-price" data-price="1729.15">$1,729</span></li>
<li class="pdp-quote-item"><span class="pdp-quote-item-text">Taxes</span><span class="pdp-quote-item-price" data-price="207.50">$207</span></li>
<li class="pdp-quote-item pdp-quote-total"><span class="pdp-quote-item-text">Total</span><span class="pdp-quote-item-price" data-price="1936.65">$1,936</span></li></ul>"""
STREAM_PAGE = """<script>var streamlinecoreConfig = {"ajaxUrl":"https:\\/\\/stream.example\\/wp-admin\\/admin-ajax.php","nonce":"x"};</script>
<div ng-init="getRatesDetails(411533)"></div>"""
STREAM_PRICE = {"data": {"unit_id": 411533, "price": 16912, "coupon_discount": 0, "total": 19044.04, "currency": "USD",
                         "required_fees": [{"id": 1, "name": "Damage Fee", "value": 30}, {"id": 2, "name": "Reservation Fee", "value": 69}],
                         "optional_fees": [{"id": 3, "name": "Travel Insurance", "value": 1475.91, "active": 0}],
                         "taxes_details": [{"id": 4, "name": "Bed Tax", "value": 847.1}, {"id": 5, "name": "State Rental Tax", "value": 1185.94}],
                         "reservation_days": [{"date": f"01/{d}/2027", "price": 2416} for d in range(16, 23)]}}
ROUTER_PAGE = """<script>const app = {props: {unitId: String}, data: {unitId: '3151-268932'}};
axios.post('https://www.router.example/vacation-rentals' + '/router/', {call: 'getPrice'});</script>"""
ROUTER_PRICE = {"apiError": None, "errorMsg": None, "isAvailable": True, "rent": 2800, "discount": 0,
                "fees": [{"name": "Housekeeping, Damage Ins, Admin ", "amount": 660}],
                "taxes": [{"name": "Florida State Tax", "amount": 242.2}, {"name": "Walton County Tax", "amount": 173}],
                "travelInsurance": None, "damageProtection": None, "bookingTotal": 3875.2, "dueNow": 1937.6,
                "extraneousPricing": [{"name": "Optional Travel Insurance", "amount": 269.33}]}
CHALLENGE = '<html><head><title>Just a moment...</title></head><body><div id="challenge-platform"></div></body></html>'


def html(text, status=200, **headers):
    return httpx.Response(status, text=text, headers={"content-type": "text/html; charset=utf-8", **headers})


def json_reply(payload, status=200):
    return httpx.Response(status, json=payload, headers={"content-type": "application/json"})


class Sites:
    """All synthetic company sites; records every request (thread-safe append)."""

    def __init__(self, before=None):
        self.seen, self.before = [], before
        self.lock = threading.Lock()

    def __call__(self, request):
        with self.lock:
            self.seen.append(request)
            count = len(self.seen)
        if self.before:
            self.before(count, request)
        url, host, path = request.url, request.url.host, request.url.path
        if host == "www.rescms.example":
            if path == "/rentals/a":
                return html(RESCMS_PAGE)
            if path == "/rentals/old":
                return html("<h1>Page not found</h1>", 404)
            if path == "/rentals/home":
                return httpx.Response(302, headers={"location": "/"})
            if path == "/":
                return html("<html><title>Home</title></html>")
            if path == "/rentals/soft404":
                return html("<html><head><title>Pages Not Found | ResCMS Rentals</title></head><body>gone</body></html>")
            if path == "/rentals/moved":
                return httpx.Response(301, headers={"location": "https://other.example/x"})
            if path == "/rescms/ajax/item/pricing/simple":
                assert url.params["rcav[eid]"] == "261" and url.params["rcav[adult]"] == "2"
                if url.params["rcav[begin]"] == "10/17/2026":
                    return json_reply({"status": 1, "content": '<span class="rc-na">Not Available</span>', "reveals": ""})
                assert url.params["rcav[begin]"] in ("01/16/2027", "03/13/2027", "07/10/2027", "10/16/2027")
                return json_reply({"status": 1, "content": RESCMS_PRICE, "reveals": ""})
            if path == "/rescms/ajax/item/pricing/quote":
                assert url.params["rcav[IDs][8][0]"] == "2261-210212"
                return json_reply({"status": 1, "content": RESCMS_QUOTE, "reveals": ""})
        if host == "www.track.example":
            if path.startswith("/rentals/"):
                return html(TRACK_PAGE % path.rsplit("/", 1)[1])
            if path == "/ajax/quote":
                form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
                assert request.method == "POST" and form["propertyName"] == "Mirasol & Blue"
                if form["checkin"] == "10/17/2026":
                    return html("No")
                if form["propertyID"] == "195":
                    return html('<div class="alert-sm alert-danger p-3 mb-3">This property has a <b>4 night</b> minimum for the selected dates.</div>')
                return html(TRACK_QUOTE if form["propertyID"] == "194" else TRACK_QUOTE_NO_FEES)
        if host == "stream.example":
            if path == "/Rentals/Seaforth/":
                return html(STREAM_PAGE)
            if path == "/wp-admin/admin-ajax.php":
                assert url.params["action"] == "streamlinecore-api-request" and request.method == "POST"
                call = json.loads(url.params["params"])
                if call["methodName"] == "VerifyPropertyAvailability":
                    if call["params"]["startdate"] == "10/17/2026":
                        return json_reply({"status": {"code": "E0031", "description": "We have no inventory available for the selected dates."}})
                    return json_reply({"data": {"id": 411533, "message": None}})
                assert call["methodName"] == "GetPreReservationPrice" and call["params"]["separate_taxes"] == 1
                return json_reply(STREAM_PRICE)
        if host == "www.router.example":
            if path == "/vacation-rentals/rental/3151-268932/":
                return html(ROUTER_PAGE)
            if path == "/vacation-rentals/router/":
                body = json.loads(request.content)
                assert body["call"] == "getPrice" and body["unitId"] == "3151-268932" and body["nights"] == 7
                if body["arrive"] == "10/17/2026":
                    return json_reply({"apiError": False, "isAvailable": False, "rent": 0, "fees": [], "taxes": [], "bookingTotal": 0,
                                       "errorMsg": "The unit 3151-268932 is unavailable for these dates (10/17/2026 - 10/23/2026)."})
                assert body["arrive"] in ("1/16/2027", "3/13/2027", "7/10/2027", "10/16/2027") and body["depart"] in ("1/23/2027", "3/20/2027", "7/17/2027", "10/23/2027")
                return json_reply(ROUTER_PRICE)
        if host == "www.drupal.example":
            if path == "/rentals/gone":            # an unpublished listing: Drupal's themed 403 page with a CAPTCHA form widget
                return html('<title>Access denied | Drupal Rentals</title><div class="bt-alerts-recaptcha" data-sitekey="x"></div>', 403)
            if path == "/":
                return html("<title>Drupal Rentals</title>")
            return html(RESCMS_PAGE.replace('"eid":"261"', '"eid":"77"'))
        if host == "www.blocked.example":
            return html("Forbidden", 403)
        if host == "www.broken.example":
            return html("Server error", 500)
        if host == "www.challenge.example":
            return html(CHALLENGE, 403, **{"cf-mitigated": "challenge"})
        raise AssertionError(f"Beklenmeyen istek: {request.method} {url}")


def listing(lodging_id, url, *, bedrooms=3, regions=("seaside",), title=None):
    return {"lodging_id": lodging_id, "title": title or f"Listing {lodging_id}", "url": url, "bedrooms": bedrooms, "region_ids": list(regions)}


def standard_listings():
    return [listing(10, "https://www.rescms.example/rentals/a", title="Same page"),
            listing(11, "https://www.rescms.example/rentals/a", title="Completely different title", regions=("seagrove",)),
            listing(12, "https://www.rescms.example/rentals/old"),
            listing(13, "https://www.rescms.example/rentals/home"),
            listing(14, "https://www.rescms.example/rentals/moved"),
            listing(15, "https://www.rescms.example/rentals/soft404"),
            listing(20, "https://www.track.example/rentals/194", bedrooms=5),
            listing(21, "https://www.track.example/rentals/195", bedrooms=2),
            listing(22, "https://www.track.example/rentals/196", bedrooms=4),
            listing(30, "https://stream.example/Rentals/Seaforth/", bedrooms=6, regions=("rosemary-beach",)),
            listing(40, "https://www.router.example/vacation-rentals/rental/3151-268932/", bedrooms=1),
            listing(50, None), listing(51, "https://unknown.example/rentals/x")]


def config(listings=None, sites=SITES, windows=WINDOWS):
    return {"sites": sites, "windows": windows, "input": {"run_id": "lodging-run", "searched_on": "2026-10-07",
                                                          "listings": standard_listings() if listings is None else listings}}


def run(tmp_path, mock=None, *, canceled=lambda: False, verifier=None, waiting=None, **changes):
    with httpx.Client(transport=httpx.MockTransport(mock or Sites())) as client:
        return ar.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, canceled, config=config(**changes), client=client,
                          verifier=verifier, waiting=waiting, today=TODAY)


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(ar, "REQUEST_GAP", 0)
    monkeypatch.setattr(ar, "RETRY_PAUSE", 0)
    monkeypatch.setattr(tl.bl, "REQUEST_GAP", 0)
    monkeypatch.setattr(tl.bl, "LIVE_PAUSE", 0)
    monkeypatch.setattr(tl.bl, "LIVE_BACKOFF", 0)


def quotes_of(result):
    return {(q["lodging_id"], q["window_key"]): q for q in result.related["quotes"]}


# --- Adapters ------------------------------------------------------------------------------------------------------

def test_rescms_page_rules_and_detailed_quote():
    info = aa.ResCMS().parse_page(RESCMS_PAGE, "https://www.rescms.example/rentals/a")
    assert info["site_id"] == "261" and info["min_stay_default"] == 1 and info["origin"] == "https://www.rescms.example"
    assert aa.ResCMS().rules(info, date(2026, 10, 17)) == (2, None)
    assert aa.ResCMS().rules(info, date(2027, 1, 16)) == (3, [6])           # 6 = Saturday (ISO), as the page's date picker reads it
    assert aa.ResCMS().rules(info, date(2027, 6, 1)) == (1, None)           # outside every range: the page default
    single = RESCMS_PAGE.replace('"', "'").replace("'mns':'1'", "'mns':'2'")  # the same settings as a single-quoted JS object
    assert aa.ResCMS().parse_page(single, "https://x.example/y")["min_stay_default"] == 2
    assert aa.ResCMS().parse_page("<html>no settings</html>", "https://x.example/") is None
    quote = aa.ResCMS.parse_quote(RESCMS_QUOTE)
    assert (quote["rent"], quote["cleaning_fee"], quote["other_fees"], quote["taxes"], quote["total"]) == (705.99, 325.0, 215.63, 149.59, 1396.21)
    assert quote["fees"] == [{"name": "Cleaning Fee", "amount": 325.0}, {"name": "Damage Waiver", "amount": 125.0}, {"name": "Booking Fee", "amount": 90.63}]
    assert quote["excluded_items"][0]["amount"] == 100.34 and "*Declined*" in quote["excluded_items"][0]["name"]
    assert (quote["total_includes_fees"], quote["total_includes_taxes"], quote["currency"]) == (1, 1, "USD")


def test_rescms_optional_items_follow_the_sites_own_subtotal():
    def table(subtotal, total):
        return f"""<table><tbody>
 <tr class="line-item odd"><td>Lodging: Eagle's Nest<br /></td><td class="amount">$9,275.00</td></tr>
 <tr class="line-item even"><td>Cleaning Fee<br /></td><td class="amount">$600.00</td></tr>
 <tr class="line-item forced-choice odd"><td>Travel Insurance (optional)<p>The plan cost includes the premium.</p></td><td class="amount">$780.66</td></tr>
 <tr class="sub-total even"><th>Sub-Total</th><td class="amount"><b>{subtotal}</b></td></tr>
 <tr class="tax odd"><th>Tax</th><td class="amount"><b>$1,203.48</b></td></tr>
 <tr class="total even"><th>Total</th><td class="amount"><b>{total}</b></td></tr></tbody></table>"""
    left_out = aa.ResCMS.parse_quote(table("$9,875.00", "$11,078.48"))            # the site's sub-total leaves the insurance out
    assert left_out["fees"] == [{"name": "Cleaning Fee", "amount": 600.0}] and left_out["other_fees"] is None
    assert left_out["excluded_items"][0]["name"] == "Travel Insurance (optional)" and "ara toplamına dahil değil" in left_out["excluded_items"][0]["reason"]
    assert (left_out["total_includes_fees"], left_out["total_includes_taxes"]) == (1, 1)
    included = aa.ResCMS.parse_quote(table("$10,655.66", "$11,859.14"))           # the sub-total includes it: part of the price
    assert [f["name"] for f in included["fees"]] == ["Cleaning Fee", "Travel Insurance (optional)"] and included["excluded_items"] is None
    assert included["total_includes_fees"] == 1
    # Two optional rows (seen on homeownerscollection.com): the sub-total counts the community fee but not the insurance
    two = table("$9,975.00", "$11,178.48").replace(
        '<tr class="sub-total', '<tr class="line-item even"><td>Seaside A&amp;E Fee (Optional)<br /></td><td class="amount">$100.00</td></tr>\n<tr class="sub-total')
    mixed = aa.ResCMS.parse_quote(two)
    assert [f["name"] for f in mixed["fees"]] == ["Cleaning Fee", "Seaside A&E Fee (Optional)"]
    assert [e["name"] for e in mixed["excluded_items"]] == ["Travel Insurance (optional)"] and mixed["total_includes_taxes"] == 1
    assert aa.included_optional(100, [], [{"name": "a", "amount": 5}, {"name": "b", "amount": 5}], 105) == []    # two subsets fit: none counted


def test_track_quote_groups_fees_and_keeps_missing_fields_null():
    info = aa.Track().parse_page(TRACK_PAGE % "194", "https://www.track.example/rentals/194")
    assert info["site_id"] == "194" and info["quote_url"] == "https://www.track.example/ajax/quote"
    assert info["fields"]["propertyName"] == "Mirasol & Blue"
    assert aa.Track().parse_page("<input type='hidden' name='other' value='1'>", "https://x.example/") is None
    quote = aa.Track.parse_quote(TRACK_QUOTE)
    assert (quote["rent"], quote["cleaning_fee"], quote["other_fees"], quote["taxes"], quote["total"]) == (2303.0, 380.0, 309.0, 347.16, 3339.16)
    assert [f["name"] for f in quote["fees"]] == ["Cleaning Fee", "Reservation Fee", "Damage Waiver"]
    bare = aa.Track.parse_quote(TRACK_QUOTE_NO_FEES)
    assert (bare["cleaning_fee"], bare["other_fees"], bare["fees"], bare["excluded_items"], bare["nightly_rates"]) == (None, None, None, None, None)
    assert (bare["total_includes_fees"], bare["total_includes_taxes"]) == (0, 1)
    with pytest.raises(aa.AdapterError):
        aa.Track.parse_quote('<ul class="pdp-quote-list"></ul>')


def test_streamline_and_router_pages():
    info = aa.Streamline().parse_page(STREAM_PAGE, "https://stream.example/Rentals/Seaforth/")
    assert info == {"site_id": "411533", "ajax_url": "https://stream.example/wp-admin/admin-ajax.php", "page_url": "https://stream.example/Rentals/Seaforth/"}
    router = aa.VacationRentalsRouter().parse_page(ROUTER_PAGE, "https://www.router.example/vacation-rentals/rental/3151-268932/")
    assert router["site_id"] == "3151-268932" and router["router_url"] == "https://www.router.example/vacation-rentals/router/"
    assert aa.VacationRentalsRouter().parse_page("<html>results</html>", "https://www.router.example/vacation-rentals/results/") is None


def test_money_and_stay_messages():
    assert aa.money("$1,246.62") == 1246.62 and aa.money("-$100.00") == -100.0 and aa.money("($5)") == -5.0
    assert aa.money("Call") is None and aa.money(None) is None and aa.money(True) is None and aa.money(242.199999) == 242.2
    assert aa.stay_message("This property has a 4 night minimum for the selected dates.") == ("restricted", 4)
    assert aa.stay_message("Minimum stay is 7 nights") == ("restricted", 7)
    assert aa.stay_message("Unit has no availability for the dates specified.") == ("unavailable", None)


# --- Collection ----------------------------------------------------------------------------------------------------

def test_listings_are_matched_only_by_their_link(tmp_path):
    mock = Sites()
    result = run(tmp_path, mock)
    rows = {r["lodging_id"]: r for r in result.records}
    assert {i: rows[i]["page_status"] for i in rows} == {10: "matched", 11: "matched", 12: "not_found", 13: "no_listing", 14: "off_site", 15: "not_found",
                                                         20: "matched", 21: "matched", 22: "matched", 30: "matched", 40: "matched",
                                                         50: "no_url", 51: "no_adapter"}
    assert rows[10]["site_listing_id"] == rows[11]["site_listing_id"] == "261"           # the link, not the (different) title
    assert rows[13]["page_url"] == "https://www.rescms.example/" and rows[14]["page_url"] == "https://other.example/x"
    assert rows[12]["http_status"] == 404 and rows[50]["domain"] is None and rows[51]["url_host"] == "unknown.example"
    assert rows[15]["http_status"] == 200 and "Pages Not Found" in rows[15]["message"]          # a "not found" page served with 200
    pages = [r for r in mock.seen if r.url.path == "/rentals/a"]
    assert len(pages) == 1                                                                 # one page read for a shared link
    assert not any(r.url.host == "other.example" or r.url.host == "unknown.example" for r in mock.seen)
    simple = [r for r in mock.seen if r.url.path.endswith("/pricing/simple")]
    assert len(simple) == 2                                                                # fall + winter once, reused for both listings
    quotes = quotes_of(result)
    assert quotes[(10, "winter")]["total"] == quotes[(11, "winter")]["total"] == 1396.21
    assert not any(q["window_key"] == "past" for q in result.related["quotes"])
    assert not any("01/03/2026" in str(r.url) or b"01/03/2026" in r.content for r in mock.seen)     # past window never asked
    assert {w["window_key"]: w["status"] for w in result.related["windows"]} == {"past": "skipped_past", "fall": "queried", "winter": "queried"}
    assert result.excluded_count == 2 and result.metadata["page_statuses"]["matched"] == 7


def test_each_platform_unavailable_priced_and_rules(tmp_path):
    quotes = quotes_of(run(tmp_path))
    fall = {lodging: quotes[(lodging, "fall")] for lodging in (10, 20, 30, 40)}
    assert {k: (q["status"], q["available"]) for k, q in fall.items()} == {10: ("unavailable", 0), 20: ("unavailable", 0), 30: ("unavailable", 0),
                                                                            40: ("unavailable", 0)}
    assert "no inventory" in fall[30]["message"] and "E0031" in fall[30]["message"] and fall[40]["message"].startswith("The unit")
    assert all(q["total"] is None and q["rent"] is None and q["fees"] is None for q in fall.values())
    assert (fall[10]["min_stay"], fall[10]["checkin_days"], fall[10]["rule_source"]) == (2, None, "sayfa")
    rescms = quotes[(10, "winter")]
    assert (rescms["status"], rescms["available"], rescms["min_stay"], rescms["checkin_days"]) == ("priced", 1, 3, [6])
    assert len(rescms["raw_sha256"]) == 2 and rescms["queried_url"].startswith("https://www.rescms.example/rescms/ajax/item/pricing/quote?")
    track = quotes[(20, "winter")]
    assert (track["rent"], track["cleaning_fee"], track["total"], track["min_stay"]) == (2303.0, 380.0, 3339.16, None)
    rule = quotes[(21, "winter")]
    assert (rule["status"], rule["available"], rule["min_stay"], rule["rule_source"], rule["total"]) == ("restricted", None, 4, "yanıt", None)
    assert quotes[(22, "winter")]["fees"] is None and quotes[(22, "winter")]["total"] == 1936.65
    stream = quotes[(30, "winter")]
    assert (stream["rent"], stream["other_fees"], stream["cleaning_fee"], stream["taxes"], stream["total"]) == (16912.0, 99.0, None, 2033.04, 19044.04)
    assert len(stream["nightly_rates"]) == 7 and stream["nightly_rates"][0] == {"date": "2027-01-16", "price": 2416.0}
    assert stream["excluded_items"][0]["name"] == "Travel Insurance" and stream["total_includes_taxes"] == 1
    router = quotes[(40, "winter")]
    assert (router["rent"], router["other_fees"], router["taxes"], router["total"], router["currency"]) == (2800.0, 660.0, 415.2, 3875.2, "USD")
    assert router["excluded_items"][0]["amount"] == 269.33


def test_raw_responses_are_kept_with_hashes(tmp_path):
    import gzip
    import hashlib
    result = run(tmp_path)
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["connector"] == "agency-lodging-rates/2" and len(manifest["responses"]) == result.metadata["request_count"]
    for entry in manifest["responses"]:
        body = gzip.decompress((tmp_path / "raw" / entry["raw_file"]).read_bytes())
        assert hashlib.sha256(body).hexdigest() == entry["raw_sha256"]
    post = next(e for e in manifest["responses"] if e["note"].startswith("track-quote-194-winter"))
    assert post["method"] == "POST" and post["request_body"]["checkin"] == "01/16/2027"
    hashes = {e["raw_sha256"] for e in manifest["responses"]}
    assert all(set(q["raw_sha256"]) <= hashes for q in result.related["quotes"])


def test_one_company_failing_does_not_stop_the_others(tmp_path, monkeypatch):
    monkeypatch.setattr(ar, "ERROR_LIMIT", 2)
    sites = SITES + [{"domain": "broken.example", "company": "Broken", "adapter": "rescms", "enabled": 1},
                     {"domain": "blocked.example", "company": "Blocked", "adapter": "track", "enabled": 1}]
    extra = [listing(60 + i, f"https://www.broken.example/rentals/{i}") for i in range(3)] + \
            [listing(70 + i, f"https://www.blocked.example/rentals/{i}") for i in range(4)]
    original = aa.VacationRentalsRouter.parse_page
    def explode(self, html_text, url):
        raise RuntimeError("synthetic adapter bug")
    monkeypatch.setattr(aa.VacationRentalsRouter, "parse_page", explode)
    mock = Sites()
    result = run(tmp_path, mock, sites=sites, listings=standard_listings() + extra)
    companies = {c["domain"]: c for c in result.related["companies"]}
    assert companies["broken.example"]["status"] == "stopped_errors" and companies["broken.example"]["request_count"] == 2
    # each refused page is followed by one look at the home page, which is refused too
    assert companies["blocked.example"]["status"] == "stopped_blocked" and companies["blocked.example"]["request_count"] == 6
    assert companies["router.example"]["status"] == "failed" and "synthetic adapter bug" in companies["router.example"]["message"]
    assert {companies[d]["status"] for d in ("rescms.example", "track.example", "stream.example")} == {"done"}
    rows = {r["lodging_id"]: r for r in result.records}
    assert rows[62]["page_status"] == "not_queried" and "ulaşılamadı" in rows[62]["message"]
    assert rows[73]["page_status"] == "not_queried" and [rows[70 + i]["page_status"] for i in range(3)] == ["blocked"] * 3
    assert quotes_of(result)[(30, "winter")]["status"] == "priced"
    assert [r.url.path for r in mock.seen if r.url.host == "www.blocked.example"] == ["/rentals/0", "/", "/rentals/1", "/", "/rentals/2", "/"]
    monkeypatch.setattr(aa.VacationRentalsRouter, "parse_page", original)


def test_one_refused_listing_page_is_not_a_site_block_or_a_verification(tmp_path):
    opened = []
    sites = [{"domain": "drupal.example", "company": "Drupal Rentals", "adapter": "rescms", "enabled": 1}]
    listings = [listing(90 + i, f"https://www.drupal.example/rentals/{name}") for i, name in enumerate(["gone", "a", "gone2"])]
    def handler(request):
        if request.url.path == "/rentals/gone2":
            request = httpx.Request("GET", str(request.url).replace("gone2", "gone"))
        if request.url.path.startswith("/rescms/"):
            return json_reply({"status": 1, "content": '<span class="rc-na">Not Available</span>', "reveals": ""})
        return Sites()(request)
    result = run(tmp_path, handler, sites=sites, listings=listings, verifier=lambda *a: opened.append(a))
    rows = {r["lodging_id"]: r for r in result.records}
    assert opened == []                                                     # a CAPTCHA widget on a 403 page is not a verification page
    assert [rows[i]["page_status"] for i in (90, 91, 92)] == ["blocked", "matched", "blocked"]
    assert "ana sayfası normal yanıt veriyor" in rows[90]["message"] and rows[91]["site_listing_id"] == "77"
    assert result.related["companies"][0]["status"] == "done"
    assert not ar.CHALLENGE.search('<div class="bt-alerts-recaptcha"></div><title>Access denied</title>')
    assert ar.CHALLENGE.search("<title>Just a moment...</title>") and ar.CHALLENGE.search('<script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1?ray=1"></script>')


def test_track_page_calendar_decides_availability_before_any_price_request(tmp_path):
    from datetime import date as day, timedelta
    def cell(d, mark):
        return f'<td class="{mark}" data-date="{d.strftime("%m/%d/%Y")}"><span>{d.day}</span></td>'
    fall = [day(2026, 10, 17) + timedelta(n) for n in range(7)]
    winter = [day(2027, 1, 16) + timedelta(n) for n in range(7)]
    calendar = "".join(cell(d, "booked" if d == day(2026, 10, 20) else "available") for d in fall)
    calendar += "".join(cell(d, "check-out" if d == winter[0] else "available") for d in winter)   # a check-out morning leaves the night free
    page = TRACK_PAGE % "194" + calendar
    seen = []
    def handler(request):
        seen.append(request)
        if request.url.path == "/rentals/194":
            return html(page)
        return Sites()(request)
    result = run(tmp_path, handler, listings=[listing(20, "https://www.track.example/rentals/194")])
    quotes = quotes_of(result)
    assert (quotes[(20, "fall")]["status"], quotes[(20, "fall")]["available"]) == ("unavailable", 0)
    assert "takvimi bu pencerenin 1 gecesini dolu" in quotes[(20, "fall")]["message"]
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    page_hash = next(e["raw_sha256"] for e in manifest["responses"] if e["note"] == "listing-page")
    assert quotes[(20, "fall")]["raw_sha256"] == [page_hash] and quotes[(20, "fall")]["queried_url"] == "https://www.track.example/rentals/194"
    assert quotes[(20, "winter")]["status"] == "priced" and quotes[(20, "winter")]["total"] == 3339.16
    posts = [parse_qs(r.content.decode())["checkin"][0] for r in seen if r.method == "POST"]
    assert posts == ["01/16/2027"]                                          # the fall window was never priced
    info = aa.Track().parse_page(page, "https://www.track.example/rentals/194")
    assert aa.Track().taken_nights(info, {"checkin_date": day(2027, 3, 13), "nights": 7}) is None   # not on the calendar: ask the site


def test_network_errors_are_retried_once_then_recorded(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.host == "www.track.example" and len([c for c in calls if c.url.host == "www.track.example"]) == 1:
            raise httpx.ConnectError("synthetic drop")
        return Sites()(request)
    result = run(tmp_path, handler, listings=[listing(20, "https://www.track.example/rentals/194")])
    assert {r["lodging_id"]: r["page_status"] for r in result.records} == {20: "matched"}
    assert sum(c.url.path == "/rentals/194" for c in calls) == 2


def test_verification_waits_for_the_user_then_continues_in_the_same_session(tmp_path):
    events, opened = [], []

    class BrowserLike:
        kind = "browser"
        closed = False
        def send(self, method, url, *, params=None, data=None, json_body=None, headers=None):
            request = httpx.Request(method, url, params=params, data=data, json=json_body, headers=headers)
            response = Sites()(httpx.Request(method, str(request.url).replace("challenge.example", "track.example"), content=request.content,
                                             headers=request.headers))
            return response.status_code, str(request.url), dict(response.headers), response.content
        def close(self):
            self.closed = True

    browser = BrowserLike()
    def verifier(domain, url, canceled, timeout):
        opened.append((domain, url, timeout))
        events.append(("verifier", domain))
        return browser
    sites = SITES + [{"domain": "challenge.example", "company": "Guarded", "adapter": "track", "enabled": 1}]
    result = run(tmp_path, sites=sites, verifier=verifier, waiting=lambda site: events.append(("waiting", site)),
                 listings=[listing(80, "https://www.challenge.example/rentals/194"), listing(81, "https://www.challenge.example/rentals/195")])
    assert opened == [("challenge.example", "https://www.challenge.example/rentals/194", 20)]      # cleared within the grace period
    assert events == [("verifier", "challenge.example")]                                            # no wait for the user
    assert result.related["browser_hosts"] == [{"host": "challenge.example", "url": "https://www.challenge.example/rentals/194",
                                                "reason": "doğrulama sayfası"}]
    company = result.related["companies"][0]
    assert (company["status"], company["verification"]) == ("done", "completed") and browser.closed
    assert quotes_of(result)[(80, "winter")]["total"] == 3339.16 and quotes_of(result)[(81, "winter")]["status"] == "restricted"
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert [e["transport"] for e in manifest["responses"]][:2] == ["http", "browser"]       # the challenge, then the verified session


def test_verification_timeout_or_no_browser_skips_only_that_company(tmp_path):
    sites = SITES + [{"domain": "challenge.example", "company": "Guarded", "adapter": "track", "enabled": 1}]
    listings = [listing(80, "https://www.challenge.example/rentals/194"), listing(30, "https://stream.example/Rentals/Seaforth/")]
    timed_out = run(tmp_path / "a", sites=sites, verifier=lambda *a: None, listings=listings)
    companies = {c["domain"]: c for c in timed_out.related["companies"]}
    assert (companies["challenge.example"]["status"], companies["challenge.example"]["verification"]) == ("verification_timeout", "timeout")
    assert companies["stream.example"]["status"] == "done"
    assert {r["lodging_id"]: r["page_status"] for r in timed_out.records}[80] == "not_queried"
    unavailable = run(tmp_path / "b", sites=sites, verifier=None, listings=listings)
    assert {c["domain"]: c["status"] for c in unavailable.related["companies"]}["challenge.example"] == "verification_unavailable"


def test_cancel_stops_every_company(tmp_path):
    calls = []
    with pytest.raises(CollectionCanceled):
        run(tmp_path, Sites(before=lambda count, request: calls.append(count)), canceled=lambda: len(calls) >= 4)
    assert len(calls) <= 4 + ar.WORKERS


def test_configuration_errors_fail_without_requests(tmp_path):
    mock = Sites()
    with pytest.raises(SourceError, match="Önce konaklama aramaları toplanmalı"):
        run(tmp_path, mock, listings=[])
    with pytest.raises(SourceError, match="bilinmeyen uyarlayıcı: nope"):
        run(tmp_path, mock, sites=[{"domain": "x.example", "company": "X", "adapter": "nope", "enabled": 1}])
    with pytest.raises(SourceError, match="geçmişte kaldı"):
        run(tmp_path, mock, windows=WINDOWS[:1])
    assert mock.seen == []


@pytest.mark.parametrize("url,supported", [
    (AGENCY_URL, True), ("https://visitsouthwalton.bookdirect.net/", False), ("https://admin.bookdirect.net/?kaynak=kiralama-sirketleri", False),
    ("https://visitsouthwalton.bookdirect.net/?kaynak=kiralama-sirketleri&x=1", False), ("https://www.benchmark30a.com/", False),
])
def test_connector_supports_only_its_marked_source(url, supported):
    assert ar.AgencyRatesConnector().supports({"url": url}) is supported


def test_summary_buckets_and_label():
    assert [ar.bucket_of(v) for v in (0, 1, 2, 2.5, 3, 4, 5, 9, None)] == ["1-2", "1-2", "1-2", None, "3", "4", "5+", "5+", None]
    priced = {"status": "priced", "total": 100.0, "total_includes_taxes": 1, "total_includes_fees": 1}
    assert "zorunlu ücretleri ve vergileri içerir" in ar.total_label([priced], "2026-10-08")
    assert "1/2 fiyatta" in ar.total_label([priced, {**priced, "total_includes_taxes": None}], "2026-10-08")
    assert "fiyat alınamadı" in ar.total_label([], "2026-10-08")


# --- Database, jobs, API, migration --------------------------------------------------------------------------------

LODGING_DATA = {2565: [tl.lodging(10, "Seaside cottage", 2565, url="https://www.rescms.example/rentals/a", bedrooms=3),
                       tl.lodging(20, "Seaside house", 2565, url="https://www.track.example/rentals/194", bedrooms=5),
                       tl.lodging(21, "Seaside studio", 2565, url="https://www.track.example/rentals/195", bedrooms=2),
                       tl.lodging(22, "Seaside cabin", 2565, url="https://www.track.example/rentals/196", bedrooms=4),
                       tl.lodging(50, "No link", 2565, url=None)],
                2449: [tl.lodging(30, "Rosemary cottage", 2449, url="https://stream.example/Rentals/Seaforth/", bedrooms=6)],
                62708: [tl.lodging(40, "Dune Allen house", 62708, url="https://www.router.example/vacation-rentals/rental/3151-268932/", bedrooms=1),
                        tl.lodging(12, "Old link", 62708, url="https://www.rescms.example/rentals/old")]}


def install(monkeypatch, mock, verifier=None):
    original = ar.collect
    def collect(path, progress, canceled, **kwargs):
        kwargs.pop("verifier", None)
        with httpx.Client(transport=httpx.MockTransport(mock)) as client:
            return original(path, progress, canceled, client=client, today=TODAY, verifier=verifier, **kwargs)
    monkeypatch.setattr(ar, "collect", collect)


def use_test_sites(db, sites=SITES):
    with db.connect() as con:
        con.execute("DELETE FROM destination_agency_sites")
        con.executemany("INSERT INTO destination_agency_sites (destination_id,domain,company,adapter,enabled,sort_order) VALUES ('30a',?,?,?,?,?)",
                        [(s["domain"], s["company"], s["adapter"], s["enabled"], i) for i, s in enumerate(sites)])


def test_api_collects_stores_and_summarizes(tmp_path, monkeypatch):
    tl.install(monkeypatch, tl.BookDirectMock(LODGING_DATA), today=TODAY)
    install(monkeypatch, Sites())
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        use_test_sites(db)
        early = tl.start(client, url=AGENCY_URL)
        assert early["status"] == "failed" and "Önce konaklama aramaları toplanmalı" in early["message"]
        lodging = tl.start(client)
        assert lodging["status"] == "done", lodging["message"]
        source = next(s for s in client.get("/api/sources").json() if s["url"] == AGENCY_URL)
        assert source["connector"] == {"name": "agency-lodging-rates", "version": "agency-lodging-rates/2", "method": "HTML/JSON"}
        job = tl.start(client, url=AGENCY_URL)
        assert job["status"] == "done", job["message"]
        assert db.job(job["id"])["waiting_for"] is None
        boot = client.get("/api/bootstrap").json()
        assert [r["id"] for r in boot["agency_runs"]] == [job["id"]] and len(boot["agency_connector"]["sites"]) == 4
        data = client.get(f"/api/agency-rate-runs/{job['id']}").json()
        assert data["snapshot"]["lodging_run_id"] == lodging["id"] and data["snapshot"]["queried_on"] == "2026-10-08"
        assert [w["window_key"] for w in data["windows"]] == ["fall-2026", "winter-2027", "spring-break-2027", "summer-2027", "fall-2027"]
        assert [r["region_id"] for r in data["regions"]] == ["dune-allen", "seaside", "rosemary-beach"]       # west to east
        assert data["regions"][1]["region_name"] == "Seaside"
        cells = {(c["region_id"], c["window_key"]): c for c in data["cells"]}
        fall = cells[("seaside", "fall-2026")]
        assert (fall["listing_count"], fall["linked_count"], fall["queried_count"], fall["priced_count"], fall["available_share"]) == (5, 4, 4, 0, 0.0)
        winter = cells[("seaside", "winter-2027")]
        # 10: ResCMS 1396.21, 20: Track 3339.16, 22: Track 1936.65 priced; 21: 4-night minimum (availability unknown)
        assert (winter["queried_count"], winter["priced_count"], winter["priced_share"], winter["available_known"], winter["available_share"]) == (4, 3, 0.75, 3, 1.0)
        assert (winter["total_q1"], winter["total_median"], winter["total_q3"]) == (1666.43, 1936.65, 2637.9)
        assert winter["nightly_median"] == round(1729.15 / 7, 2)
        assert winter["bedrooms"] == {"1-2": {"count": 0, "median": None}, "3": {"count": 1, "median": 1396.21}, "4": {"count": 1, "median": 1936.65},
                                      "5+": {"count": 1, "median": 3339.16}}
        assert cells[("rosemary-beach", "winter-2027")]["bedrooms"]["5+"] == {"count": 1, "median": 19044.04}
        assert data["coverage"]["listings"] == 8 and data["coverage"]["matched"] == 6 and data["coverage"]["not_found"] == 1
        assert data["coverage"]["no_url"] == 1 and data["coverage"]["priced_listings"] == 5 and data["coverage"]["regions_with_price"] == 3
        assert "2026-10-08 tarihinde sorgulanan" in data["label"] and "vergileri" in data["label"]
        assert {c["domain"]: c["status"] for c in data["companies"]} == {d["domain"]: "done" for d in SITES}
        listings = client.get(f"/api/agency-rate-runs/{job['id']}/listings?region_id=seaside").json()["listings"]
        first = next(l for l in listings if l["lodging_id"] == 10)
        assert first["company"] == "ResCMS Rentals" and first["quotes"]["winter-2027"]["fees"][0]["name"] == "Cleaning Fee"
        assert first["quotes"]["fall-2026"]["status"] == "unavailable" and first["region_ids"] == ["seaside"]
        assert client.get(f"/api/agency-rate-runs/{job['id']}/listings?region_id=nowhere").json()["listings"] == []
        raw = client.get(f"/api/agency-rate-runs/{job['id']}/raw")
        assert raw.status_code == 200 and json.loads(raw.content)["connector"] == "agency-lodging-rates/2"
        assert client.get(f"/api/agency-rate-runs/{lodging['id']}").status_code == 404
        with db.connect() as con:
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
            assert con.execute("SELECT COUNT(*) FROM agency_rate_quotes WHERE run_id=?", (job["id"],)).fetchone()[0] == 6 * 5


def test_job_shows_which_site_waits_for_verification(tmp_path, monkeypatch):
    tl.install(monkeypatch, tl.BookDirectMock({2565: [tl.lodging(80, "Guarded", 2565, url="https://www.challenge.example/rentals/194")]}), today=TODAY)
    seen = []
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        use_test_sites(db, [{"domain": "challenge.example", "company": "Guarded", "adapter": "track", "enabled": 1}])
        def verifier(domain, url, canceled, timeout):
            job = next(j for j in db.jobs() if j["status"] == "running")
            seen.append((job["waiting_for"], job["message"]))
            return None
        install(monkeypatch, Sites(), verifier=verifier)
        assert tl.start(client)["status"] == "done"
        job = tl.start(client, url=AGENCY_URL)
        assert job["status"] == "done"
        assert seen[0][0] is None                                     # the grace look: the site is left for the end
        assert seen[1][0] == "challenge.example" and "Kullanıcı doğrulaması bekleniyor: challenge.example" in seen[1][1] and "(en çok 15 dk)" in seen[1][1]
        assert db.job(job["id"])["waiting_for"] is None and any("Doğrulama beklemesi bitti" in e["text"] for e in db.job(job["id"])["log"])
        summary = client.get(f"/api/agency-rate-runs/{job['id']}").json()
        assert summary["companies"][0]["status"] == "verification_timeout"


def test_waits_are_cleared_and_hidden_once_the_job_ends(tmp_path):
    db = Database(tmp_path / "studio.sqlite3"); db.initialize()
    identifier = db.add_job()
    assert db.update_job(identifier, status="running", waiting_for="site.example")
    assert db.job(identifier)["waiting_for"] == "site.example" and db.jobs()[0]["waiting_for"] == "site.example"
    db.update_job(identifier, status="canceled", message="İş iptal edildi.")
    assert db.job(identifier)["waiting_for"] is None                   # an ended job never shows a wait
    assert not db.update_job(identifier, waiting_for="")              # clearing still removes the row
    with db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM job_waits").fetchone()[0] == 0


def test_failure_after_insert_rolls_back_and_keeps_previous_run(tmp_path, monkeypatch):
    tl.install(monkeypatch, tl.BookDirectMock(LODGING_DATA), today=TODAY)
    install(monkeypatch, Sites())
    tables = ("agency_rate_snapshots", "agency_rate_windows", "agency_rate_companies", "agency_rate_listings", "agency_rate_quotes")
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        use_test_sites(client.app.state.db)
        assert tl.start(client)["status"] == "done"
        good = tl.start(client, url=AGENCY_URL); assert good["status"] == "done"
        original = ar.AgencyRatesConnector.store_records
        def fail(self, con, run_id, records, related=None):
            original(self, con, run_id, records, related); raise RuntimeError("synthetic after insert")
        monkeypatch.setattr(ar.AgencyRatesConnector, "store_records", fail)
        failed = tl.start(client, url=AGENCY_URL); assert failed["status"] == "failed"
        assert [r["id"] for r in client.get("/api/agency-rate-runs").json()] == [good["id"]]
        with client.app.state.db.connect() as con:
            for table in tables:
                assert con.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id=?", (failed["id"],)).fetchone()[0] == 0
                assert con.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id=?", (good["id"],)).fetchone()[0] > 0


def test_cancel_job_through_api_publishes_nothing(tmp_path, monkeypatch):
    release, entered = threading.Event(), threading.Event()
    def before(count, request):
        if count == 3:
            entered.set(); release.wait(30)
    tl.install(monkeypatch, tl.BookDirectMock(LODGING_DATA), today=TODAY)
    install(monkeypatch, Sites(before=before))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        use_test_sites(client.app.state.db)
        assert tl.start(client)["status"] == "done"
        source = next(s for s in client.get("/api/sources").json() if s["url"] == AGENCY_URL)
        identifier = client.post("/api/jobs", json={"kind": "source_collection", "source_id": source["id"]}).json()["id"]
        try:
            assert entered.wait(30)
            assert client.post(f"/api/jobs/{identifier}/cancel").json()["status"] == "canceled"
        finally:
            release.set()
        assert finished(client, identifier)["status"] == "canceled"
        assert client.get("/api/agency-rate-runs").json() == []
        with client.app.state.db.connect() as con:
            assert con.execute("SELECT COUNT(*) FROM agency_rate_listings").fetchone()[0] == 0


def test_fresh_database_has_agency_sites_and_source(tmp_path):
    db = Database(tmp_path / "studio.sqlite3"); db.initialize()
    agency = db.context("30a").agency
    assert [(s["domain"], s["company"], s["adapter"]) for s in agency["sites"]] == list(thirty_a.AGENCY_SITES + thirty_a.AGENCY_SITES_V12)
    assert "input" not in agency
    assert db.context("30a", inputs=("lodging_listings",)).agency["input"] is None         # no lodging run yet
    source = next(s for s in db.sources() if s["url"] == AGENCY_URL)
    assert (source["method"], source["category"]) == ("HTML", "Konaklama")
    with db.connect() as con:
        insert = "INSERT INTO destination_agency_sites (destination_id,domain,company,adapter,enabled,sort_order) VALUES "
        for statement in (insert + "('30a','www.example.com','X','track',1,0)", insert + "('30a','Example.com','X','track',1,0)",
                          insert + "('30a','example.com','X','Track-2',1,0)", insert + "('30a','example.com',' ','track',1,0)"):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute(statement)


def make_v10(path):
    """A v10 database with one Book>Direct lodging run (bookdirect-lodging/1 rows have no url columns)."""
    from studio.migration_v10 import upgrade_v10
    from studio.migration_v9 import upgrade_v9
    from tests.test_climate import make_v8
    make_v8(path)
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        con.execute("BEGIN IMMEDIATE"); upgrade_v9(con); upgrade_v10(con); con.commit()
        source = con.execute("SELECT id FROM sources WHERE url=?", (tl.URL,)).fetchone()[0]
        con.execute("INSERT INTO jobs(id,kind,title,status,created_at,source_id,destination_id) VALUES ('lj','source_collection','old','done','now',?,'30a')", (source,))
        con.execute("""INSERT INTO source_runs(id,source_id,job_id,status,connector_name,connector_version,destination_id,metadata)
            VALUES ('lj',?,'lj','done','bookdirect-lodging','bookdirect-lodging/1','30a','{}')""", (source,))
        con.execute("INSERT INTO lodging_snapshots VALUES ('lj','visitsouthwalton.bookdirect.net','/x/',103,'2026-10-07',3,1)")
        con.execute("""INSERT INTO lodging_listings (run_id,lodging_id,title,category_ids,category_names,amenities,hide_rate_calendar,live_rates_enabled)
            VALUES ('lj',7,'Old listing','[]','[]','[]',0,0)""")
        con.commit()


def test_v10_to_v11_migration_adds_agency_tables_source_and_keeps_rows(tmp_path):
    path = tmp_path / "studio.sqlite3"; make_v10(path)
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 10
        before = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in table_counts(con)}
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 12
        assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        counts = table_counts(con)
        assert counts == {**{t: len(rows) for t, rows in before.items()}, **V11_TABLES, **V12_TABLES, "destination_lodging_windows": 5,
                          "sources": len(before["sources"]) + 2}
        after = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in before}
        changed = ("sources", "lodging_listings", "destination_lodging_windows")
        unchanged = {t: r for t, r in after.items() if t not in changed}
        assert unchanged == {t: r for t, r in before.items() if t not in changed}
        assert after["destination_lodging_windows"][:4] == before["destination_lodging_windows"]        # v12 adds Fall 2027
        assert after["lodging_listings"] == [row + (None, None, None) for row in before["lodging_listings"]]
        assert after["sources"][:len(before["sources"])] == before["sources"] and after["sources"][-2][2] == AGENCY_URL
    backup, = (tmp_path / "backups").glob("*-v10-*.sqlite3")
    with sqlite3.connect(backup) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 10
    Database(path).initialize()                                                              # idempotent: nothing added twice
    with sqlite3.connect(path) as con:
        assert table_counts(con)["sources"] == len(before["sources"]) + 2 and table_counts(con)["destination_agency_sites"] == 24


def test_v10_to_v11_failure_rolls_back_everything(tmp_path, monkeypatch):
    from studio import database
    path = tmp_path / "studio.sqlite3"; make_v10(path)
    with sqlite3.connect(path) as con:
        before = {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in table_counts(con)}
    original = database.upgrade_v11
    def fail(con): original(con); raise RuntimeError("after all DDL, configuration and source inserts")
    with monkeypatch.context() as m:
        m.setattr(database, "upgrade_v11", fail)
        with pytest.raises(RuntimeError):
            Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 10
        assert table_counts(con).keys() == before.keys()
        assert {table: con.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall() for table in before} == before
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 12
