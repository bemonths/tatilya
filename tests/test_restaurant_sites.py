"""Restaurant facts from the businesses' own sites (restaurant-sites/1): structured data, menus and prices, classification,
price level, reservations, closures, reviewed readings, isolation, cancel, the browser pass, storage and API.

Synthetic pages through httpx.MockTransport only; suite-wide no_real_http prevents internet access.
"""
import csv
import hashlib
import json
import zlib

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.sources import restaurant_sites as rs
from studio.sources import restaurants as r
from studio.sources.base import CollectionCanceled, SourceError
from tests import test_restaurants as tr

SECTIONS = rs.load_sections()


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(rs, "REQUEST_GAP", 0)
    monkeypatch.setattr(rs, "BROWSER_GAP", 0)
    monkeypatch.setattr(rs, "PROTECTED_GAP", 0)
    monkeypatch.setattr(tr.r, "REQUEST_GAP", 0)
    monkeypatch.setattr(tr.r, "RETRY_SECONDS", 0)


def make_pdf(lines):
    """A one-page PDF with the given text lines (Helvetica), small enough to build by hand."""
    content = "BT /F1 11 Tf 50 760 Td 14 TL " + " ".join(f"({line.replace('(', '').replace(')', '')}) Tj T*" for line in lines) + " ET"
    stream = zlib.compress(content.encode("latin-1"))
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
               b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    body, offsets = b"%PDF-1.4\n", []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body += b"%d 0 obj\n" % number + obj + b"\nendobj\n"
    xref = len(body)
    body += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    return body + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)


HOME = """<html><head><title>Coast &amp; Table | Santa Rosa Beach</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Restaurant","name":"Coast & Table","priceRange":"$$",
"openingHoursSpecification":[{"@type":"OpeningHoursSpecification","dayOfWeek":["Monday","Tuesday","Wednesday","Thursday"],"opens":"11:00","closes":"21:00"},
{"@type":"OpeningHoursSpecification","dayOfWeek":"https://schema.org/Friday","opens":"11:00","closes":"22:00"}],
"hasMenu":"https://restaurant.example/menus/kids.pdf"}</script></head><body>
<nav><a href="/dinner-menu">Dinner Menu</a> <a href="/menu-board.jpg">Menu board</a> <a href="https://www.getbento.com/?utm_source=footer">powered by BentoBox</a>
<a href="https://www.opentable.com/r/coast-table">Reserve a table</a> <a href="/contact">Contact &amp; Hours</a> <a href="/careers">Careers</a></nav>
<p>Enjoy our outdoor patio seating overlooking the gulf. Call us at (850) 555-0100.</p></body></html>"""
DINNER = """<html><head><title>Dinner</title></head><body><h1>Dinner Menu</h1>
<h2>STARTERS</h2><p>Calamari 14</p><p>Smoked Fish Dip ........ 12</p>
<h2>E N T R É E S</h2>
<h3>Grilled Grouper</h3><p>rice, succotash, lemon aioli</p><p>$34</p>
<p>Shrimp &amp; Grits ...... 26</p><p>Pork Chop 31</p><p>Seared Scallops 38</p><p>8oz Filet 52</p><p>Local Catch MKT</p>
<p>add shrimp 6</p><h2>SOUPS</h2><p>Seafood Gumbo cup 9 | bowl 14</p>
<h2>DESSERTS</h2><p>Key Lime Pie 10</p><p>Open daily 11am - 9pm</p></body></html>"""
CONTACT = """<html><body><h2>Hours</h2><p>Mon - Thu 11am - 9pm</p><p>Fri &amp; Sat 11am - 10pm</p><p>Sun Closed</p>
<p>We do not take reservations. Dogs welcome on the patio!</p></body></html>"""


class Sites:
    def __init__(self):
        self.seen = []

    def __call__(self, request):
        self.seen.append(request)
        host, path = request.url.host, request.url.path
        if host == "restaurant.example":
            if path in ("/", "/menu"):
                return httpx.Response(200, text=HOME, headers={"content-type": "text/html"})
            if path == "/dinner-menu":
                return httpx.Response(200, text=DINNER, headers={"content-type": "text/html"})
            if path == "/contact":
                return httpx.Response(200, text=CONTACT, headers={"content-type": "text/html"})
            if path == "/menus/kids.pdf":
                return httpx.Response(200, content=make_pdf(["KIDS", "Chicken Tenders 9", "Grilled Cheese 8"]), headers={"content-type": "application/pdf"})
            if path == "/menu-board.jpg":
                return httpx.Response(200, content=b"\xff\xd8\xff synthetic menu board", headers={"content-type": "image/jpeg"})
        if host == "closed.example":
            return httpx.Response(200, text="<title>Old Spot</title><h1>Old Spot</h1><p>After 20 years we have permanently closed. Thank you!</p>",
                                  headers={"content-type": "text/html"})
        if host == "season.example":
            return httpx.Response(200, text="<title>Shave Ice</title><p>Shave Ice is closed for the season. See you in March!</p>",
                                  headers={"content-type": "text/html"})
        if host == "parked.example":
            return httpx.Response(200, text="<title>parked.example</title><p>This domain is for sale!</p>", headers={"content-type": "text/html"})
        if host == "guarded.example":
            return httpx.Response(403, text="<title>Just a moment...</title><div id='cf-chl-widget'></div>", headers={"content-type": "text/html"})
        if host == "broken.example":
            raise httpx.ConnectError("synthetic")
        if host == "www.facebook.com":
            return httpx.Response(200, text="<title>Log in to Facebook</title>", headers={"content-type": "text/html"})
        raise AssertionError(f"Beklenmeyen istek: {request.url}")


def restaurant(identifier, name, url, phone="(850) 555-0100"):
    return {"external_id": f"/listing/{identifier}/", "name": name, "website_url": url, "phone": phone, "address_line_1": "10 Coast Lane",
            "city": "Santa Rosa Beach"}


def config(restaurants, tmp_path, readings=()):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "readings.csv"
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["external_id", "menu_url", "raw_sha256", "menu_type", "menu_title", "section", "name",
                                                    "price_text", "price", "price_rule", "okundu"])
        writer.writeheader()
        for row in readings:
            writer.writerow(row)
    return {"input": {"run_id": "directory-run", "restaurants": restaurants}, "menu_readings": path, "site_overrides": None}


def run(tmp_path, restaurants, mock=None, canceled=lambda: False, readings=(), browser=False, waiting=None):
    with httpx.Client(transport=httpx.MockTransport(mock or Sites())) as client:
        return rs.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, canceled, config=config(restaurants, tmp_path, readings),
                          client=client, browser=browser, waiting=waiting)


def related(result, external_id):
    pick = lambda kind: [x for x in result.related[kind] if x["external_id"] == external_id]
    site = next(s for s in result.records if s["external_id"] == external_id)
    return site, {f["field"]: f for f in pick("facts")}, pick("menus"), pick("items")


# --- Parsing ---------------------------------------------------------------------------------------------------------------

def test_structured_data_hours_menu_link_and_site_price_range():
    objects = rs.json_ld(HOME)
    days, text = rs.schema_hours(objects)
    assert days == {0: "11:00–21:00", 1: "11:00–21:00", 2: "11:00–21:00", 3: "11:00–21:00", 4: "11:00–22:00"}
    assert "Friday 11:00–22:00" in text and objects[0]["priceRange"] == "$$"
    assert rs.parse_hours_text("Mon - Thu 11am - 9pm · Fri, Sat 11am - 10pm · Sun Closed") == {
        0: "11:00–21:00", 1: "11:00–21:00", 2: "11:00–21:00", 3: "11:00–21:00", 4: "11:00–22:00", 5: "11:00–22:00", 6: "kapalı"}
    assert rs.parse_hours_text("Open daily 7:30 AM - 3 PM") == {d: "07:30–15:00" for d in range(7)}
    assert rs.parse_hours_text("Hours vary by season") == {}


def test_menu_prices_sections_lowest_size_market_and_skipped_add_ons():
    items = rs.parse_menu(rs.html_lines(DINNER))
    by_name = {i["name"]: i for i in items}
    assert by_name["Calamari"]["price"] == 14 and by_name["Smoked Fish Dip"]["price"] == 12
    assert by_name["Grilled Grouper"]["price"] == 34 and by_name["Grilled Grouper"]["section"] == "E N T R É E S"   # a dish written as a heading
    assert (by_name["Seafood Gumbo"]["price"], by_name["Seafood Gumbo"]["price_rule"]) == (9.0, "lowest")
    assert (by_name["Local Catch"]["price"], by_name["Local Catch"]["price_text"], by_name["Local Catch"]["price_rule"]) == (None, "MKT", "market")
    assert "add shrimp" not in {n.lower() for n in by_name} and not any("Open daily" in n for n in by_name)
    assert rs.classify("E N T R É E S", SECTIONS) == "ana_yemek" and rs.classify("STARTERS", SECTIONS) == "baslangic"
    assert rs.classify("R E D W I N E", SECTIONS) == "icecek" and rs.classify("Red Snapper Platters", SECTIONS) == "ana_yemek"
    assert rs.classify("Kids Burgers", SECTIONS) == "cocuk" and rs.classify("Soups & Salads", SECTIONS) == "salata_corba"
    assert rs.item_class({"section": None, "name": "Fish Tacos"}, "general", SECTIONS) == ("ana_yemek", "name")
    assert rs.item_class({"section": "VIEW PDF", "name": "Caesar Salad"}, "general", SECTIONS) == ("salata_corba", "name")
    assert rs.item_class({"section": None, "name": "Chicken Tenders"}, "kids", SECTIONS) == ("cocuk", "menu")
    assert rs.menu_line("Feta15 ......") == "Feta 15" and rs.menu_line("Oysters MKT*") == "Oysters MKT"


def test_pdf_menu_text_is_read():
    lines = rs.pdf_lines(make_pdf(["ENTREES", "Grilled Grouper 34", "Filet 52"]))
    assert [t for _, t in lines] == ["ENTREES", "Grilled Grouper 34", "Filet 52"]
    assert [(i["section"], i["name"], i["price"]) for i in rs.parse_menu(lines)] == [("ENTREES", "Grilled Grouper", 34.0), ("ENTREES", "Filet", 52.0)]


@pytest.mark.parametrize("median,level", [(14.99, "$"), (15, "$$"), (24.99, "$$"), (25, "$$$"), (39.99, "$$$"), (40, "$$$$")])
def test_price_level_boundaries(median, level):
    assert rs.price_level({"count": 5, "median": median}) == level


def test_price_level_needs_five_main_prices_and_counts_only_main_dishes():
    four = [{"section_class": "ana_yemek", "price": p} for p in (20, 22, 24, 26)] + [{"section_class": "baslangic", "price": 12}]
    assert rs.main_stats(four) == {"count": 4, "median": 23.0, "min": 20, "max": 26} and rs.price_level(rs.main_stats(four)) is None
    five = four + [{"section_class": "ana_yemek", "price": 30}, {"section_class": "ana_yemek", "price": None}]
    assert rs.price_level(rs.main_stats(five)) == "$$" and rs.main_stats(five)["count"] == 5


# --- Collection ------------------------------------------------------------------------------------------------------------

def test_collects_menus_facts_and_provenance(tmp_path):
    readings = []
    board = b"\xff\xd8\xff synthetic menu board"
    readings.append({"external_id": "/listing/coast-table/", "menu_url": "https://restaurant.example/menu-board.jpg",
                     "raw_sha256": hashlib.sha256(board).hexdigest(), "menu_type": "lunch", "menu_title": "Lunch board", "section": "SANDWICHES",
                     "name": "Grouper Sandwich", "price_text": "$18", "price": "18", "price_rule": "single", "okundu": "2026-10-08"})
    result = run(tmp_path, [restaurant("coast-table", "Coast & Table", "https://restaurant.example/")], readings=readings)
    site, facts, menus, items = related(result, "/listing/coast-table/")
    assert (site["site_status"], site["site_source"], site["http_status"]) == ("working", "directory", 200)
    assert facts["hours"]["method"] == "yapısal veri" and facts["hours"]["data"]["Fri"] == "11:00–22:00"
    assert (facts["reservation"]["value"], facts["reservation"]["detail"], facts["reservation"]["method"]) == ("online", "OpenTable", "bağlantı")
    assert facts["outdoor_seating"]["value"] == "yes" and facts["water_view"]["value"] == "yes" and facts["dog_friendly"]["value"] == "yes"
    assert facts["site_price_range"]["value"] == "$$" and facts["kids_menu"]["value"] == "yes"
    for fact in facts.values():
        assert fact["source_url"].startswith("https://restaurant.example/") and len(fact["raw_sha256"]) == 64 and fact["fetched_at"]
    kinds = {m["url"].rsplit("/", 1)[-1]: m for m in menus}
    assert (kinds["dinner-menu"]["menu_type"], kinds["dinner-menu"]["status"], kinds["dinner-menu"]["method"]) == ("dinner", "read", "sayfa metni")
    assert (kinds["kids.pdf"]["format"], kinds["kids.pdf"]["menu_type"], kinds["kids.pdf"]["method"]) == ("pdf", "kids", "PDF metni")
    assert (kinds["menu-board.jpg"]["format"], kinds["menu-board.jpg"]["method"], kinds["menu-board.jpg"]["menu_type"]) == ("image", "görüntüden okundu", "lunch")
    assert not any("getbento" in m["url"] or "careers" in m["url"] for m in menus)            # a platform credit and other pages are not menus
    view = rs.restaurant_view(site, list(facts.values()), menus, items, ["santa-rosa-beach"])
    assert view["main_menu_type"] == "dinner" and view["main"] == {"count": 5, "median": 34.0, "min": 26.0, "max": 52.0} and view["price_level"] == "$$$"
    board_item = next(i for i in items if i["name"] == "Grouper Sandwich")
    assert board_item["method"] == "görüntüden okundu" and board_item["section_class"] == "ana_yemek"
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["connector"] == "restaurant-sites/1" and len(manifest["responses"]) == result.metadata["request_count"]


def test_unknown_stays_unknown_and_no_only_when_the_site_says_it(tmp_path):
    quiet = {"/": "<title>Quiet Cafe</title><h1>Quiet Cafe</h1><p>Coffee and pastries. No pets allowed inside.</p>"}
    def handler(request):
        if request.url.host == "quiet.example":
            return httpx.Response(200, text=quiet.get(request.url.path, "<h1>?</h1>"), headers={"content-type": "text/html"})
        return Sites()(request)
    result = run(tmp_path, [restaurant("quiet", "Quiet Cafe", "https://quiet.example/")], handler)
    _, facts, menus, items = related(result, "/listing/quiet/")
    assert set(facts) == {"dog_friendly"} and facts["dog_friendly"]["value"] == "no"                       # stated; nothing else is "no"
    assert menus == [] and items == []


def test_closures_parked_domains_social_pages_and_missing_sites(tmp_path):
    restaurants = [restaurant("old", "Old Spot", "https://closed.example/"), restaurant("ice", "Shave Ice", "https://season.example/"),
                   restaurant("parked", "Parked", "https://parked.example/"), restaurant("fb", "Social Grill", "https://www.facebook.com/socialgrill"),
                   restaurant("none", "No Site", None), restaurant("down", "Down Cafe", "https://broken.example/")]
    result = run(tmp_path, restaurants)
    statuses = {s["external_id"].split("/")[2]: s["site_status"] for s in result.records}
    assert statuses == {"old": "closed_permanently", "ice": "closed_season", "parked": "other_business", "fb": "social_login", "none": "no_site",
                        "down": "unreachable"}
    assert result.excluded_count == 1 and result.metadata["site_statuses"]["working"] == 0


def test_an_image_reading_for_another_image_is_not_used(tmp_path):
    readings = [{"external_id": "/listing/coast-table/", "menu_url": "https://restaurant.example/menu-board.jpg", "raw_sha256": "0" * 64,
                 "menu_type": "lunch", "menu_title": "", "section": "", "name": "Old Sandwich", "price_text": "$9", "price": "9",
                 "price_rule": "single", "okundu": "2025-01-01"}]
    result = run(tmp_path, [restaurant("coast-table", "Coast & Table", "https://restaurant.example/")], readings=readings)
    _, _, menus, items = related(result, "/listing/coast-table/")
    board = next(m for m in menus if m["url"].endswith("menu-board.jpg"))
    assert board["status"] == "image_unread" and "okuması yok" in board["message"] and not any(i["name"] == "Old Sandwich" for i in items)


def test_photos_menus_without_prices_and_text_pdfs_without_prices(tmp_path):
    photo, wine = b"\xff\xd8\xff a plate of pasta", b"\xff\xd8\xff wine list, no prices"
    steam = make_pdf(["CHOOSE YOUR SHELLFISH", "extra 2.00/lb to steam", "MILD butter, hot sauce, old bay seasoning on every order",
                      "SPICY same as mild but with a kick of cayenne and lemon", "LEMON GARLIC lemon juice, butter, garlic greek seasoning",
                      "SIDES new potatoes, corn on the cob, smoked sausage link", "DESSERTS key lime pie, banana pudding, chocolate lush"])
    pages = {"/": '<title>Plain Cafe</title><h1>Plain Cafe</h1><a href="/m/menu-photo.jpg">Menu photo</a> <a href="/m/menu-wine.jpg">Wine menu</a>'
                  ' <a href="/m/steam-menu.pdf">Steam menu</a>'}
    def handler(request):
        path = request.url.path
        if path in pages:
            return httpx.Response(200, text=pages[path], headers={"content-type": "text/html"})
        body = {"/m/menu-photo.jpg": photo, "/m/menu-wine.jpg": wine, "/m/steam-menu.pdf": steam}.get(path)
        if body is None:
            return httpx.Response(404, text="<h1>Not found</h1>", headers={"content-type": "text/html"})
        return httpx.Response(200, content=body, headers={"content-type": "application/pdf" if path.endswith(".pdf") else "image/jpeg"})
    base = {"external_id": "/listing/plain/", "section": "", "name": "", "price_text": "", "price": "", "price_rule": "", "okundu": "2026-10-08"}
    readings = [{**base, "menu_url": "https://plain.example/m/menu-photo.jpg", "raw_sha256": hashlib.sha256(photo).hexdigest(),
                 "menu_type": "menü değil", "menu_title": ""},
                {**base, "menu_url": "https://plain.example/m/menu-wine.jpg", "raw_sha256": hashlib.sha256(wine).hexdigest(),
                 "menu_type": "drinks", "menu_title": "Wine List"}]
    result = run(tmp_path, [restaurant("plain", "Plain Cafe", "https://plain.example/")], handler, readings=readings)
    _, _, menus, items = related(result, "/listing/plain/")
    by_file = {m["url"].rsplit("/", 1)[-1]: m for m in menus}
    assert "menu-photo.jpg" not in by_file and items == []                      # a reviewed photo is not a menu
    assert (by_file["menu-wine.jpg"]["status"], by_file["menu-wine.jpg"]["method"], by_file["menu-wine.jpg"]["menu_type"]) == (
        "no_items", "görüntüden okundu", "drinks") and "fiyat yazmıyor" in by_file["menu-wine.jpg"]["message"]
    assert (by_file["steam-menu.pdf"]["status"], by_file["steam-menu.pdf"]["method"]) == ("no_items", "PDF metni")   # text, but no prices


def test_nested_headings_cart_counters_and_addresses_are_not_dishes():
    html = ('<div class="menu-section-title"><h3>Lunch</h3></div><p>Turkey Wrap 14</p><p>Your Cart $0.00</p><p>Skip to content 0</p>'
            '<p>1 Review 1</p><p>Suite 101</p><p>1777 East County Hwy 30A 120</p><p>Oct 8</p><p>Club Sandwich $13</p>')
    items = rs.parse_menu(rs.html_lines(html))
    assert [(i["section"], i["name"], i["price"]) for i in items] == [("Lunch", "Turkey Wrap", 14.0), ("Lunch", "Club Sandwich", 13.0)]
    popmenu = [("h", "Appetizers"), ("h", "Pizza Bread"), ("p", "A quarter of a muffaletta roll topped with house marinara and mozzarella"),
               ("p", "*contains sesame seeds"), ("p", "1 likes"), ("p", "$12.00"), ("h", "Fries"), ("p", "$8.00"), ("p", "/"), ("p", "$16"),
               ("p", "Buffalo Style 1")]
    assert [(i["section"], i["name"], i["price"]) for i in rs.parse_menu(popmenu)] == [("Appetizers", "Pizza Bread", 12.0), ("Appetizers", "Fries", 8.0)]


def test_a_moved_page_falls_back_to_the_home_page_and_shared_pages_are_read_once(tmp_path):
    pages = {"/": "<title>Big Breakfast</title><h1>Big Breakfast</h1><a href='/menu'>Menu</a>",
             "/menu": "<h2>ENTREES</h2><p>Biscuit Plate 14</p>"}
    def handler(request):
        if request.url.host == "moved.example":
            if request.url.path in pages:
                return httpx.Response(200, text=pages[request.url.path], headers={"content-type": "text/html"})
            return httpx.Response(404, text="<h1>Not found</h1>", headers={"content-type": "text/html"})
        return Sites()(request)
    sites = Sites()
    def counting(request):
        sites.seen.append(request)
        return handler(request)
    result = run(tmp_path, [restaurant("big", "Big Breakfast", "https://moved.example/locations/inlet-beach"),
                            restaurant("coast-a", "Coast & Table", "https://restaurant.example/"),
                            restaurant("coast-b", "Coast & Table Seaside", "https://restaurant.example/")], counting)
    site, _, menus, items = related(result, "/listing/big/")
    assert site["site_status"] == "working" and "Dizindeki sayfa bulunamadı (HTTP 404" in site["status_note"]
    assert [i["name"] for i in items] == ["Biscuit Plate"]
    homes = [r for r in sites.seen if r.url.host == "restaurant.example" and r.url.path == "/"]
    assert len(homes) == 1                                        # two restaurants, one shared home page
    assert related(result, "/listing/coast-b/")[0]["site_status"] == "working"


def test_a_plain_refusal_is_tried_in_the_browser_and_a_definite_answer_wins(tmp_path):
    class Refusing(StandInSession):
        def current(self):
            self.looks += 1
            return 404, self.url, "text/html", b"<title>Page not found</title>"
    def handler(request):
        if request.url.host == "refuse.example":
            return httpx.Response(403, text="<h1>Forbidden</h1>", headers={"content-type": "text/html"})
        return Sites()(request)
    session = Refusing({})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        pages = rs.BrowserPages(None, lambda: False, opener=lambda profile: session)
        rows = [restaurant("refuse", "Refuse Grill", "https://refuse.example/")]
        result = rs.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config(rows, tmp_path), client=client, browser=pages)
    site = related(result, "/listing/refuse/")[0]
    assert session.looks >= 1 and site["site_status"] == "not_found"          # the browser's 404 is more than "unreachable"


def test_curly_quoted_names_pizza_pies_and_drinks_menus():
    items = rs.parse_menu([("p", "Kids Menu"), ("p", "“Horn Island” Chicken Fingers 13"), ("p", "“Ship Island” Bowtie Pasta & Sauce 10")])
    assert [(i["name"], i["price"]) for i in items] == [("“Horn Island” Chicken Fingers", 13.0), ("“Ship Island” Bowtie Pasta & Sauce", 10.0)]
    assert rs.classify("amici 30A signature neapolitan pizza pies", SECTIONS) == "ana_yemek" and rs.classify("Pies", SECTIONS) == "tatli"
    assert rs.classify("little amici's (ages 12 and under)", SECTIONS) == "cocuk" and rs.classify("dessert cocktails", SECTIONS) == "icecek"
    assert rs.item_class({"section": "Frozen", "name": "Cookie Colada"}, "drinks", SECTIONS) == ("icecek", "menu")
    assert rs.item_class({"section": "Frozen", "name": "Cookie Colada"}, "general", SECTIONS) == ("diger", "section")


def test_one_site_failing_does_not_stop_the_others_and_cancel_stops_all(tmp_path, monkeypatch):
    original = rs.RestaurantRun.structured
    def explode(self, document, html):
        if "closed" in document.final_url:
            raise RuntimeError("synthetic parser bug")
        return original(self, document, html)
    monkeypatch.setattr(rs.RestaurantRun, "structured", explode)
    result = run(tmp_path, [restaurant("coast-table", "Coast & Table", "https://restaurant.example/"), restaurant("old", "Old Spot", "https://closed.example/")])
    statuses = {s["external_id"]: (s["site_status"], s["status_note"]) for s in result.records}
    assert statuses["/listing/coast-table/"][0] == "working" and "synthetic parser bug" in statuses["/listing/old/"][1]
    with pytest.raises(CollectionCanceled):
        run(tmp_path / "c", [restaurant("coast-table", "Coast & Table", "https://restaurant.example/")], canceled=lambda: True)
    with pytest.raises(SourceError, match="Önce restoran dizini"):
        run(tmp_path / "d", [])


class StandInSession:
    """A visible-browser stand-in: the first page shows a verification page, the next look shows the site."""

    def __init__(self, pages):
        self.pages, self.looks, self.closed = pages, 0, False

    def goto(self, url):
        self.url = url
        return self.current()

    def current(self):
        self.looks += 1
        if "guarded.example" in self.url and self.looks == 1:
            return 403, self.url, "text/html", b"<title>Just a moment...</title>"
        body = self.pages.get(httpx.URL(self.url).path, "<h1>?</h1>")
        return 200, self.url, "text/html", body.encode()

    def request(self, url):
        return 200, url, "application/pdf", make_pdf(["Kids 7"])

    def close(self):
        self.closed = True


def test_a_closed_browser_window_keeps_the_first_reading_and_the_run_completes(tmp_path):
    class TargetClosedError(Exception):
        pass

    class Closed(StandInSession):
        def goto(self, url):
            raise TargetClosedError("Page.goto: Target page, context or browser has been closed")

        def close(self):
            raise TargetClosedError("BrowserContext.close: Target page, context or browser has been closed")

    rows = [restaurant("guarded", "Guarded Grill", "https://guarded.example/"), restaurant("guarded2", "Guarded Two", "https://guarded.example/two")]
    with httpx.Client(transport=httpx.MockTransport(Sites())) as client:
        pages = rs.BrowserPages(None, lambda: False, opener=lambda profile: Closed({}))
        result = rs.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config(rows, tmp_path), client=client, browser=pages)
    for key in ("/listing/guarded/", "/listing/guarded2/"):
        site = related(result, key)[0]
        assert site["site_status"] == "unreachable" and "Tarayıcı penceresi kapandığı için" in site["status_note"]


class Verifying(StandInSession):
    """guarded.example keeps its verification page until the user completes it during the end-of-run wait (when `clear`)."""

    def __init__(self, pages, clear):
        super().__init__(pages)
        self.clear, self.verified, self.order = clear, False, []

    def goto(self, url):
        self.url = url
        self.order.append(("goto", httpx.URL(url).host))
        return self.current()

    def current(self):
        self.looks += 1
        if "guarded.example" in self.url and not self.verified:
            return 403, self.url, "text/html", b"<title>Just a moment...</title>"
        body = self.pages.get(httpx.URL(self.url).path, "<h1>?</h1>")
        return 200, self.url, "text/html", body.encode()

    def wait_all(self, sites, canceled, timeout, waiting):
        self.order.append(("wait_all", tuple(sorted(sites)), timeout))
        if waiting:
            waiting(", ".join(sorted(sites)))
            waiting(None)
        self.verified = self.clear
        return set(sites) if self.clear else set()


def test_a_site_still_verifying_is_left_for_the_end_one_wait_then_read_or_skipped_and_marked(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "pause", lambda seconds, canceled: None)
    pages = {"/": "<title>Guarded Grill</title><h1>Guarded Grill</h1><a href='/menu'>Menu</a>", "/menu": "<h2>ENTREES</h2><p>Fish 20</p>"}
    def handler(request):
        if request.url.host == "render.example":
            return httpx.Response(200, text="<title>Render</title><div id=\"root\"></div><a href='/menu'>Menu</a>", headers={"content-type": "text/html"})
        return Sites()(request)
    rows = [restaurant("guarded", "Guarded Grill", "https://guarded.example/"), restaurant("render", "Render Cafe", "https://render.example/")]
    for clear in (True, False):
        session, waits = Verifying({**pages, "/menu": pages["/menu"]}, clear), []
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            browser = rs.BrowserPages(None, lambda: False, waiting=waits.append, opener=lambda profile: session, grace=0)
            result = rs.collect(tmp_path / str(clear) / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config(rows, tmp_path / str(clear)),
                                client=client, browser=browser)
        waited = [i for i, e in enumerate(session.order) if e[0] == "wait_all"]
        assert len(waited) == 1 and session.order[waited[0]][1:] == (("guarded.example",), 15 * 60)
        assert ("goto", "render.example") in session.order[:waited[0]]           # the other restaurants are read before the wait
        assert waits == ["guarded.example", None]
        site, _, _, items = related(result, "/listing/guarded/")
        if clear:
            assert site["site_status"] == "working" and [i["name"] for i in items] == ["Fish"]
        else:
            assert site["site_status"] == "unreachable" and "15 dk içinde tamamlanmadı" in site["status_note"]
        assert [m["host"] for m in result.related["browser_hosts"]] == ["guarded.example"]


def test_a_known_browser_host_is_never_asked_with_plain_http(tmp_path):
    session = StandInSession({"/": "<title>Guarded Grill</title><h1>Guarded Grill</h1><a href='/menu'>Menu</a>", "/menu": "<h2>ENTREES</h2><p>Fish 20</p>"})
    session.looks = 1                                         # no verification page this time: the profile kept the cookie
    def handler(request):
        if request.url.host == "guarded.example":
            pytest.fail(f"plain HTTP to {request.url}")
        return Sites()(request)
    rows = [restaurant("guarded", "Guarded Grill", "https://guarded.example/")]
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        browser = rs.BrowserPages(None, lambda: False, opener=lambda profile: session)
        result = rs.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False,
                            config={**config(rows, tmp_path), "browser_hosts": ("guarded.example",)}, client=client, browser=browser)
    site, _, _, items = related(result, "/listing/guarded/")
    assert site["site_status"] == "working" and [i["name"] for i in items] == ["Fish"] and "daha önce doğrulama gösteren site" in site["status_note"]


def test_a_verification_page_is_read_again_in_the_browser_and_the_user_wait_is_shown(tmp_path, monkeypatch):
    monkeypatch.setattr(rs, "VERIFY_TIMEOUT", 60)
    monkeypatch.setattr(rs, "pause", lambda seconds, canceled: None)
    session = StandInSession({"/": "<title>Guarded Grill</title><h1>Guarded Grill</h1><a href='/menu'>Menu</a>",
                              "/menu": "<h2>ENTREES</h2><p>Fish 20</p><p>Steak 30</p>"})
    waits = []
    with httpx.Client(transport=httpx.MockTransport(Sites())) as client:
        pages = rs.BrowserPages(None, lambda: False, waiting=waits.append, opener=lambda profile: session)    # the run's own raw store is used
        rows = [restaurant("guarded", "Guarded Grill", "https://guarded.example/")]
        result = rs.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config(rows, tmp_path), client=client, browser=pages)
    site, _, menus, items = related(result, "/listing/guarded/")
    assert site["site_status"] == "working" and "görünür tarayıcıyla okundu" in site["status_note"]
    assert [i["name"] for i in items] == ["Fish", "Steak"] and menus[0]["status"] == "read"
    assert "guarded.example" in pages.protected
    manifest = json.loads((tmp_path / "raw" / "manifest.json").read_text(encoding="utf-8"))
    assert any(e["note"].endswith("(tarayıcı)") for e in manifest["responses"]) and any(e["status"] == 403 for e in manifest["responses"])


def test_each_connector_names_its_own_verification_wait():
    from studio.sources import agency_rates
    assert (rs.RestaurantSitesConnector.verify_minutes, agency_rates.AgencyRatesConnector.verify_minutes) == (15, 15)   # the one end-of-run wait


def test_an_ordinary_page_behind_cloudflare_is_not_a_verification_page(tmp_path):
    normal = ("<html><head><title>Coast Grill</title></head><body><h1>Coast Grill</h1><script>(function(){var a=document.createElement('script');"
              "a.src='/cdn-cgi/challenge-platform/scripts/jsd/main.js';document.head.appendChild(a)})();</script></body></html>")
    challenge = ("<html><head><title>Just a moment...</title></head><body><script>window._cf_chl_opt={cType:'managed'};</script>"
                 "<script src='/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1?ray=1'></script></body></html>")
    turnstile = ("<html><head><title>Contact - Coast Grill</title></head><body><form><div id='cf-chl-widget-a1b2c'><iframe "
                 "src='https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/b/turnstile/if/ov2/av0/rcv/x'></iframe></div>"
                 "<label>Verify you are human</label></form></body></html>")          # a contact form's Turnstile box
    assert rs.CHALLENGE.search(normal) is None and rs.CHALLENGE.search(turnstile) is None and rs.CHALLENGE.search(challenge)
    from studio.sources import agency_rates, browser_verification
    assert agency_rates.CHALLENGE.search(normal) is None and browser_verification.CHALLENGE.search(normal) is None
    assert agency_rates.CHALLENGE.search(challenge) and browser_verification.CHALLENGE.search(challenge)

    class Normal(StandInSession):
        def current(self):
            self.looks += 1
            return 200, self.url, "text/html", normal.encode()

    session, waits = Normal({}), []
    store = rs.RawStore(tmp_path / "raw" / "manifest.json")
    pages = rs.BrowserPages(store, lambda: False, waiting=waits.append, opener=lambda profile: session)
    document = pages.get("https://coast.example/", restaurant="/listing/coast/", note="site-home")
    assert (document.status, session.looks, waits) == (200, 1, []) and "coast.example" not in pages.protected


# --- Storage, API and migration -----------------------------------------------------------------------------------------------

def site_mock(request):
    if request.url.host in r.HOSTS:
        return tr.DirectoryMock()(request)
    return Sites()(request)


def install(monkeypatch):
    original = rs.collect
    def collect(path, progress, canceled, *, config, waiting=None, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(site_mock)) as client:
            return original(path, progress, canceled, config={**config, "menu_readings": None}, client=client, waiting=waiting, browser=False)
    monkeypatch.setattr(rs, "collect", collect)


def start_sites(client):
    source = next(s for s in client.get("/api/sources").json() if s["url"].endswith("?kaynak=isletme-siteleri"))
    response = client.post("/api/jobs", json={"kind": "source_collection", "source_id": source["id"]}, headers={"X-Studio-Request": "1"})
    assert response.status_code == 202
    return tr.finished(client, response.json()["id"])


def test_api_stores_summarizes_and_rolls_back(tmp_path, monkeypatch):
    tr.install_mock(monkeypatch, tr.DirectoryMock())
    install(monkeypatch)
    with TestClient(create_app(tmp_path)) as client:
        early = start_sites(client)
        assert early["status"] == "failed" and "Önce restoran dizini" in early["message"]
        assert tr.start(client)["status"] == "done"
        job = start_sites(client)
        assert job["status"] == "done", job["message"]
        boot = client.get("/api/bootstrap").json()
        assert [r["id"] for r in boot["restaurant_site_runs"]] == [job["id"]] and boot["restaurant_site_connector"]["name"] == "restaurant-sites"
        data = client.get(f"/api/restaurant-site-runs/{job['id']}").json()
        assert data["coverage"]["restaurants"] == 2 and data["statuses"]["working"] == 1 and data["statuses"]["no_site"] == 1
        coast = next(x for x in data["restaurants"] if x["name"] == "Coast & Table")
        assert (coast["price_level"], coast["main"]["median"], coast["reservation"], coast["kids_menu"]) == ("$$$", 34.0, "online", "yes")
        regions = {x["region_id"]: x for x in data["regions"]}
        assert regions["dune-allen"]["levels"]["$$$"] == 1 and regions["dune-allen"]["online_reservation"] == 1
        assert regions["dune-allen"]["median_of_medians"] == 34.0 and "bizim sınıflamamızdır" in data["level_note"]
        detail = client.get(f"/api/restaurant-site-runs/{job['id']}/restaurant", params={"external_id": "/listing/coast-table/"}).json()
        assert detail["facts"]["hours"]["data"]["Mon"] == "11:00–21:00" and any(i["name"] == "Grilled Grouper" for i in detail["items"])
        assert client.get(f"/api/restaurant-site-runs/{job['id']}/restaurant", params={"external_id": "/listing/none/"}).status_code == 404
        raw = client.get(f"/api/restaurant-site-runs/{job['id']}/raw")
        assert raw.status_code == 200 and json.loads(raw.content)["connector"] == "restaurant-sites/1"
        original = rs.RestaurantSitesConnector.store_records
        def fail(self, con, run_id, records, related=None):
            original(self, con, run_id, records, related); raise RuntimeError("synthetic after insert")
        monkeypatch.setattr(rs.RestaurantSitesConnector, "store_records", fail)
        failed = start_sites(client)
        assert failed["status"] == "failed"
        with client.app.state.db.connect() as con:
            for table in ("restaurant_site_snapshots", "restaurant_sites", "restaurant_facts", "restaurant_menus", "restaurant_menu_items"):
                assert con.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id=?", (failed["id"],)).fetchone()[0] == 0
                assert con.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id=?", (job["id"],)).fetchone()[0] > 0
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
