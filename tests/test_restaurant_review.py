"""GÖREV-10 restaurant price level review: structured menus (schema.org, Toast data, ohbz menus), menus in tabs, parser fixes,
add-on / drink / kids rules, reviewed item classes, small plates and fixed-price menus, reviewed readings of pages and PDFs and the
one-line reason for a restaurant without a price level.

Synthetic pages through httpx.MockTransport only; suite-wide no_real_http prevents internet access.
"""
import csv
import json

import httpx

from studio.sources import restaurant_sites as rs
from tests.test_restaurant_sites import SECTIONS, fast, make_pdf, related, restaurant  # noqa: F401  (fast: autouse fixture)

POPMENU_HOME = """<html><head><title>Paradis</title><script type="application/ld+json" id="pm-schema-graph">{"@context":"https://schema.org","@graph":[
{"@type":"Restaurant","@id":"#r","name":"Paradis","hasMenu":[{"@id":"#menu-1"}]},
{"@type":"Menu","@id":"#menu-1","name":"Dinner Menu","url":"https://paradis.example/menu#menu=dinner-menu","hasMenuSection":[
 {"@type":"MenuSection","name":"Starters","hasMenuItem":[{"@type":"MenuItem","name":"Diver Scallops","offers":{"@type":"Offer","price":"25.0"}}]},
 {"@type":"MenuSection","name":"Entrées","hasMenuItem":[
  {"@type":"MenuItem","name":"Grouper","offers":{"@type":"Offer","price":"44.0"}},
  {"@type":"MenuItem","name":"Filet","offers":[{"@type":"Offer","price":"58"},{"@type":"Offer","price":"52"}]},
  {"@type":"MenuItem","name":"Chef Special"},
  {"@type":"MenuItem","name":"Duck","offers":{"@type":"Offer","price":"41"}},
  {"@type":"MenuItem","name":"Snapper","offers":{"@type":"Offer","price":"46"}},
  {"@type":"MenuItem","name":"Lamb","offers":{"@type":"Offer","price":"0"}},
  {"@type":"MenuItem","name":"Pasta","offers":{"@type":"Offer","price":"34"}}]}]}]}</script></head>
<body><h1>Paradis</h1><p>Rosemary Beach. (850) 555-0100</p></body></html>"""


def site_mock(pages):
    """pages: {url: (content type, body)}; anything else is 404."""
    def handler(request):
        url = str(request.url)
        if url in pages:
            kind, body = pages[url]
            return httpx.Response(200, content=body if isinstance(body, bytes) else body.encode("utf-8"), headers={"content-type": kind})
        return httpx.Response(404, text="not found", headers={"content-type": "text/html"})
    return handler


def collect(tmp_path, restaurants, pages, *, readings=(), overrides=(), item_classes=()):
    tmp_path.mkdir(parents=True, exist_ok=True)
    reading_path, override_path, class_path = tmp_path / "readings.csv", tmp_path / "sites.csv", tmp_path / "classes.csv"
    for path, fields, rows in ((reading_path, ["external_id", "menu_url", "raw_sha256", "menu_type", "menu_title", "section", "name", "price_text",
                                               "price", "price_rule", "okundu", "yontem"], readings),
                               (override_path, ["external_id", "name", "site_url", "kanit", "kaynak", "kontrol_tarihi", "menu_urls",
                                                "ana_yemek_sunmuyor", "seviye_notu"], overrides),
                               (class_path, ["external_id", "ad", "kalem", "fiyat_metni", "sinif", "not", "kontrol_tarihi"], item_classes)):
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fields})
    config = {"input": {"run_id": "directory-run", "restaurants": restaurants}, "menu_readings": reading_path, "site_overrides": override_path,
              "item_classes": class_path}
    with httpx.Client(transport=httpx.MockTransport(site_mock(pages))) as client:
        return rs.collect(tmp_path / "raw" / "manifest.json", lambda *a: None, lambda: False, config=config, client=client, browser=False)


def view_of(result, external_id):
    site, facts, menus, items = related(result, external_id)
    return rs.restaurant_view(site, list(facts.values()), menus, items, [])


# --- Structured menus ------------------------------------------------------------------------------------------------------

def test_schema_org_menu_items_with_offers_lowest_price_and_no_unpriced_items():
    menus = rs.schema_menus(POPMENU_HOME, "https://paradis.example/")
    assert [m["name"] for m in menus] == ["Dinner Menu"] and menus[0]["url"] == "https://paradis.example/menu#menu=dinner-menu"
    items = {i["name"]: i for i in menus[0]["items"]}
    assert set(items) == {"Diver Scallops", "Grouper", "Filet", "Duck", "Snapper", "Pasta"}      # no offer / price 0: left out
    assert (items["Filet"]["price"], items["Filet"]["price_rule"], items["Filet"]["price_text"]) == (52.0, "lowest", "58 / 52")
    assert items["Grouper"]["section"] == "Entrées" and items["Diver Scallops"]["section"] == "Starters"


def test_structured_menu_on_the_home_page_gives_a_level_without_any_menu_link(tmp_path):
    result = collect(tmp_path, [restaurant("paradis", "Paradis", "https://paradis.example/")],
                     {"https://paradis.example/": ("text/html", POPMENU_HOME)})
    view = view_of(result, "/listing/paradis/")
    menu = view["menus"][0]
    assert (menu["method"], menu["menu_type"], menu["url"]) == ("yapısal veri", "dinner", "https://paradis.example/menu#menu=dinner-menu")
    assert view["main"] == {"count": 5, "median": 44.0, "min": 34.0, "max": 52.0} and view["price_level"] == "$$$$"


def test_toast_ordering_page_data_menus_with_groups_and_sizes():
    state = {"ROOT_QUERY": {"menus": [{"__typename": "Menu", "id": "m1", "name": "Food", "groups": [
        {"__typename": "MenuGroup", "name": "Sandwiches", "items": [{"__typename": "MenuItem", "name": "Club", "prices": [14.5]},
                                                                      {"__typename": "MenuItem", "name": "Melt", "prices": [12, 16]},
                                                                      {"__typename": "MenuItem", "name": "Gift card", "prices": []}],
         "subgroups": [{"__typename": "MenuGroup", "name": "Wraps", "items": [{"__typename": "MenuItem", "name": "Veggie Wrap", "prices": [11]}]}]}]}]}}
    html = f"<script>window.__OO_STATE__ = {json.dumps(state)};</script>"
    menus = rs.toast_menus(html)
    assert [(i["section"], i["name"], i["price"], i["price_rule"]) for i in menus[0]["items"]] == [
        ("Sandwiches", "Club", 14.5, "single"), ("Sandwiches", "Melt", 12.0, "lowest"), ("Wraps", "Veggie Wrap", 11.0, "single")]


def test_ohbz_menu_items_by_their_attributes_with_block_titles():
    html = ("""<div class="mo-name">ENTREES</div><div class="item " data-source="mhm"><span class="name" aria-label="Item name: Grits a Ya Ya">"""
            """</span><span class="price" aria-label="Price: Shrimp 28 | Grouper 48"></span></div>"""
            """<div class="item " data-source="mhm"><span class="name" aria-label="Item name: Add Shrimp"></span><span aria-label="Price: 9"></span></div>"""
            """<div class="mo-name">SALADS</div><div class="item " data-source="mhm"><span aria-label="Item name: Wedge"></span>"""
            """<span aria-label="Price: 14"></span></div>""")
    items = rs.mhm_menus(html)[0]["items"]
    assert [(i["section"], i["name"], i["price"], i["price_rule"]) for i in items] == [("ENTREES", "Grits a Ya Ya", 28.0, "lowest"), ("SALADS", "Wedge", 14.0, "single")]


def test_menus_in_tabs_are_separate_menus_and_kids_tab_never_counts_as_mains(tmp_path):
    page = """<html><head><title>Perfect Pig</title></head><body><ul class="tabs-nav">
    <a id="tab-dinner" href="#dinner" role="tab" aria-controls="dinner" aria-label="Dinner">Dinner</a>
    <a id="tab-kids" href="#kids" role="tab" aria-controls="kids" aria-label="Kids">Kids</a></ul>
    <button role="tab" aria-label="1 of 3" aria-controls="slick-1">1</button>
    <section id="dinner" class="tabs-panel" role="tabpanel"><h3>Entrees</h3><p>Shrimp and Grits $ 32</p><p>Salmon $ 38</p><p>Filet $ 48</p>
    <p>Pork Chop $ 36</p><p>Chicken $ 29</p></section>
    <section id="kids" class="tabs-panel" role="tabpanel"><h3>Lunch &amp; Dinner</h3><p>Grits $ 5.50</p><p>Grilled Cheese $ 9</p></section>
    <footer>(850) 555-0100</footer></body></html>"""
    result = collect(tmp_path, [restaurant("pig", "Perfect Pig", "https://pig.example/")],
                     {"https://pig.example/": ("text/html", "<html><title>Perfect Pig</title><a href='/location/seagrove/'>Menus</a>(850) 555-0100</html>"),
                      "https://pig.example/location/seagrove/": ("text/html", page)})
    view = view_of(result, "/listing/pig/")
    kinds = {m["title"]: m["menu_type"] for m in view["menus"]}
    assert kinds == {"Dinner": "dinner", "Kids": "kids"}
    assert view["main"]["count"] == 5 and view["main"]["median"] == 36.0 and view["price_level"] == "$$$"


# --- Parser fixes ----------------------------------------------------------------------------------------------------------

def test_raw_mark_dash_names_mixed_case_headings_notes_and_lone_market_price():
    known = lambda heading: bool(rs.heading_like(heading) or rs.MIXED_HEADING.match(heading)) and rs.classify(heading, SECTIONS) != "diger"
    lines = [("h", "ENTREES"), ("p", "*Simply Grilled Grouper 38"), ("p", "*Gluten Free Items"),
             ("p", "TO FEAST large plates"), ("p", "PAN SEARED FRESH SALMON 38"),
             ("p", "BEC* - Benton's Bacon, Egg, Cheddar Cheese"), ("p", "13"),
             ("p", "SEAFOOD DINNERS"), ("p", "SERVED FRIED, GRILLED OR BLACKENED. CHOICE OF TWO SIDES."), ("p", "MKT"), ("p", "Fish of the Day"), ("p", "MKT"),
             ("p", "SANDWICHES, TACOS, AND SUCH"), ("p", "SERVED WITH A CHOICE OF ONE SIDE"), ("p", "Fish Tacos $17"),
             ("p", "$"), ("p", "Topsail Club"), ("p", "$11,00")]
    items = [(i["section"], i["name"], i["price"]) for i in rs.parse_menu(lines, known)]
    assert items == [("ENTREES", "Simply Grilled Grouper", 38.0), ("TO FEAST large plates", "PAN SEARED FRESH SALMON", 38.0),
                     ("TO FEAST large plates", "BEC", 13.0), ("SEAFOOD DINNERS", "Fish of the Day", None),
                     ("SANDWICHES, TACOS, AND SUCH", "Fish Tacos", 17.0), ("SANDWICHES, TACOS, AND SUCH", "Topsail Club", 11.0)]


def test_add_on_drink_kids_and_add_protein_items_are_never_mains_and_review_classes_win():
    def klass(name, section="Pizza", price=3.0, reviewed=None):
        return rs.item_class({"section": section, "name": name, "price": price, "price_text": f"${price:.2f}"}, "general", SECTIONS, reviewed)
    assert klass("Each Additional Topping") == ("yan_urun", "name") and klass("Cauliflower Crust Available", price=4) == ("yan_urun", "name")
    assert klass("Original or Thin Crust Gluten Free Option (small)") == ("yan_urun", "name")
    assert klass("Diet Dr. Pepper") == ("icecek", "name") and klass("Imported draft", price=6) == ("icecek", "name")
    assert klass("San Pellegrino Mineral Water") == ("icecek", "name") and klass("Kids Dog Only", "Hot Dogs", 7) == ("cocuk", "name")
    assert klass("Chicken", "Add Protein", 5.49) == ("yan_urun", "section")
    assert klass("Margherita", price=20) == ("ana_yemek", "section")
    reviewed = {("Bacon", "$2.00"): "yan_urun", ("Sushi", ""): "baslangic"}
    assert klass("Bacon", "Old Southern Breakfast", 2.0, reviewed) == ("yan_urun", "review")
    assert klass("Sushi", "C 7. Mackerel", 6.0, reviewed) == ("baslangic", "review")
    assert klass("Bacon Cheeseburger", "Burgers", 16.0, reviewed) == ("ana_yemek", "section")


def test_reviewed_item_class_file_is_applied_by_the_collector(tmp_path):
    page = "<html><title>Biscuits</title>(850) 555-0100<h2>Breakfast</h2><p>Bacon $2.00</p>" + "".join(
        f"<p>Biscuit {n} $ {10 + n}</p>" for n in range(5)) + "</html>"
    result = collect(tmp_path, [restaurant("biscuit", "Biscuits", "https://biscuit.example/")],
                     {"https://biscuit.example/": ("text/html", "<html><title>Biscuits</title><a href='/menu'>Menu</a>(850) 555-0100</html>"),
                      "https://biscuit.example/menu": ("text/html", page)},
                     item_classes=[{"external_id": "/listing/biscuit/", "kalem": "Bacon", "fiyat_metni": "$2.00", "sinif": "yan_urun"}])
    _, _, _, items = related(result, "/listing/biscuit/")
    bacon = next(i for i in items if i["name"] == "Bacon")
    assert (bacon["section_class"], bacon["class_basis"]) == ("yan_urun", "review")
    assert view_of(result, "/listing/biscuit/")["main"]["min"] == 10.0


def test_frameset_page_follows_the_framed_site_and_parking_scripts_mark_another_business(tmp_path):
    framed = "<html><title>Summer</title><frameset rows='100%,*'><frame src='https://summer.example/'></frameset></html>"
    home = "<html><title>Summer Kitchen</title><a href='/menu'>Menu</a>(850) 555-0100</html>"
    menu = "<html><h2>Lunch</h2>" + "".join(f"<p>Sandwich {n} $ {15 + n}</p>" for n in range(5)) + "</html>"
    parked = "<html><head><script src='https://parked.example/sk-park.php?pid=9'></script></head><body></body></html>"
    result = collect(tmp_path, [restaurant("summer", "Summer Kitchen", "http://skcafe.example/"), restaurant("pub", "Old Pub", "http://pub.example/")],
                     {"http://skcafe.example/": ("text/html", framed), "https://summer.example/": ("text/html", home),
                      "https://summer.example/menu": ("text/html", menu), "http://pub.example/": ("text/html", parked)})
    site, _, menus, items = related(result, "/listing/summer/")
    assert site["final_url"] == "https://summer.example/" and menus[0]["url"] == "https://summer.example/menu" and len(items) == 5
    assert related(result, "/listing/pub/")[0]["site_status"] == "other_business"


# --- Small plates, fixed-price menus, reasons -----------------------------------------------------------------------------

def test_tapas_only_menu_gives_small_plate_median_and_no_level(tmp_path):
    menu = "<html><title>Tapas</title><h2>para picar</h2><p>Olives 8</p><p>Bread 9</p><h2>tapas</h2>" + "".join(
        f"<p>Tapa {n} {12 + n}</p>" for n in range(5)) + "<h2>Desserts</h2><p>Flan 9</p></html>"
    result = collect(tmp_path, [restaurant("crema", "La Crema", "https://crema.example/")],
                     {"https://crema.example/": ("text/html", "<html><title>La Crema</title><a href='/tapas'>Tapas</a>(850) 555-0100</html>"),
                      "https://crema.example/tapas": ("text/html", menu)})
    view = view_of(result, "/listing/crema/")
    assert view["price_level"] is None and view["main"]["count"] == 0
    assert view["small_plates"] == {"count": 7, "median": 13.0, "min": 8.0, "max": 16.0}
    assert view["level_reason"].startswith("tapas / küçük tabak menüsü")


def test_prix_fixe_is_kept_apart_from_the_main_dish_median(tmp_path):
    menu = ("<html><title>Dinner</title><h2>Entrees</h2>" + "".join(f"<p>Dish {n} {30 + n}</p>" for n in range(5)) +
            "<h2>Three Course Dinner</h2><p>Chef's Menu 95</p></html>")
    result = collect(tmp_path, [restaurant("roux", "Roux", "https://roux.example/")],
                     {"https://roux.example/": ("text/html", "<html><title>Roux</title><a href='/dinner'>Dinner Menu</a>(850) 555-0100</html>"),
                      "https://roux.example/dinner": ("text/html", menu)})
    view = view_of(result, "/listing/roux/")
    assert view["main"]["max"] == 34.0 and view["price_level"] == "$$$"
    assert [(f["name"], f["price"]) for f in view["fixed_menus"]] == [("Chef's Menu", 95.0)]


def test_review_notes_give_the_reason_and_a_level_still_wins(tmp_path):
    pages = {"https://coffee.example/": ("text/html", "<html><title>Coffee</title><p>Espresso bar</p>(850) 555-0100</html>"),
             "https://quiet.example/": ("text/html", "<html><title>Quiet</title><a href='/menu'>Menu</a>(850) 555-0100</html>"),
             "https://quiet.example/menu": ("text/html", "<html><h2>Entrees</h2><p>Grouper</p><p>Filet</p></html>")}
    result = collect(tmp_path, [restaurant("coffee", "Coffee", "https://coffee.example/"), restaurant("quiet", "Quiet", "https://quiet.example/")],
                     pages, overrides=[{"external_id": "/listing/coffee/", "name": "Coffee", "ana_yemek_sunmuyor": "kahve dükkânı",
                                        "kontrol_tarihi": "2026-10-09"},
                                       {"external_id": "/listing/quiet/", "name": "Quiet", "seviye_notu": "sitedeki menüde ana yemek fiyatları yazmıyor"}])
    coffee, quiet = view_of(result, "/listing/coffee/"), view_of(result, "/listing/quiet/")
    assert coffee["level_reason"] == "ana yemek sunmuyor (kahve dükkânı)" and coffee["facts"]["review_note"]["method"] == "gözden geçirme"
    assert quiet["level_reason"] == "sitedeki menüde ana yemek fiyatları yazmıyor"
    assert rs.level_reason({**coffee, "price_level": "$"}) is None


def test_reasons_for_missing_menus_unreadable_menus_and_few_mains():
    base = {"price_level": None, "facts": {}, "site_status": "working", "small_plates": {"count": 0}, "menus": [], "main": {"count": 0}}
    assert rs.level_reason(base) == "sitede menü bulunamadı"
    assert rs.level_reason({**base, "site_status": "unreachable"}) == "sitesine ulaşılamadı"
    assert rs.level_reason({**base, "menus": [{"status": "image_unread"}]}) == "menü okunamadı: menü görüntüsü okunmadı"
    assert rs.level_reason({**base, "menus": [{"status": "read"}]}) == "okunan menülerde fiyatlı ana yemek yok"
    assert rs.level_reason({**base, "menus": [{"status": "read"}], "main": {"count": 3}}) == "5'ten az fiyatlı ana yemek (3)"
    assert rs.menu_type("Thanksgiving To Go") == "special" and rs.menu_type("Catering menu") == "catering"


# --- Reviewed readings of pages and PDFs ------------------------------------------------------------------------------------

def reading(external_id, url, sha, section, name, price_text):
    return {"external_id": external_id, "menu_url": url, "raw_sha256": sha, "menu_type": "dinner", "menu_title": "Dinner", "section": section,
            "name": name, "price_text": price_text, "price": price_text.replace("$", "").strip(), "price_rule": "single", "okundu": "2026-10-09",
            "yontem": "elle okundu"}


def test_a_page_reading_is_used_when_the_page_still_shows_every_name_and_price(tmp_path):
    menu = "<html><h1>Dinner</h1><p>$ 62</p><p>FILET</p><p>$ 62</p><p>$ 49</p><p>LOBSTER CAMPANELLE</p><p>$ 49</p></html>"
    rows = [reading("/listing/pescado/", "https://pescado.example/dinner-menu/", "old-copy-sha", "Entrées", "FILET", "$ 62"),
            reading("/listing/pescado/", "https://pescado.example/dinner-menu/", "old-copy-sha", "Entrées", "LOBSTER CAMPANELLE", "$ 49")]
    pages = {"https://pescado.example/": ("text/html", "<html><title>Pescado</title><a href='/dinner-menu'>Dinner</a>(850) 555-0100</html>"),
             "https://pescado.example/dinner-menu": ("text/html", menu)}
    result = collect(tmp_path, [restaurant("pescado", "Pescado", "https://pescado.example/")], pages, readings=rows)
    _, _, menus, items = related(result, "/listing/pescado/")
    assert (menus[0]["method"], menus[0]["menu_type"], menus[0]["status"]) == ("elle okundu", "dinner", "read")
    assert "doğrulandı" in menus[0]["message"] and [(i["section"], i["name"], i["method"]) for i in items] == [
        ("Entrées", "FILET", "elle okundu"), ("Entrées", "LOBSTER CAMPANELLE", "elle okundu")]
    changed = {**pages, "https://pescado.example/dinner-menu": ("text/html", menu.replace("$ 62", "$ 64"))}
    result = collect(tmp_path / "again", [restaurant("pescado", "Pescado", "https://pescado.example/")], changed, readings=rows)
    _, _, menus, _ = related(result, "/listing/pescado/")
    assert menus[0]["method"] != "elle okundu" and "uyuşmadı (1/2" in menus[0]["message"]


def test_a_pdf_reading_matches_by_its_sha_even_when_the_text_lacks_the_headings(tmp_path):
    pdf = make_pdf(["Grilled Grouper", "Succotash, Basmati Rice 43", "Roasted Salmon", "Lentils 34"])
    import hashlib
    sha = hashlib.sha256(pdf).hexdigest()
    rows = [reading("/listing/bud/", "https://bud.example/old-name.pdf", sha, "ENTRÉES", "Grilled Grouper", "43"),
            reading("/listing/bud/", "https://bud.example/old-name.pdf", sha, "ENTRÉES", "Roasted Salmon", "34")]
    result = collect(tmp_path, [restaurant("bud", "Bud", "https://bud.example/")],
                     {"https://bud.example/": ("text/html", "<html><title>Bud</title><a href='/dinner.pdf'>Dinner menu</a>(850) 555-0100</html>"),
                      "https://bud.example/dinner.pdf": ("application/pdf", pdf)}, readings=rows)
    _, _, menus, items = related(result, "/listing/bud/")
    assert menus[0]["format"] == "pdf" and "aynı belge" in menus[0]["message"]
    assert [(i["section"], i["section_class"]) for i in items] == [("ENTRÉES", "ana_yemek"), ("ENTRÉES", "ana_yemek")]
