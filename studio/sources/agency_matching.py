"""Matching a Book>Direct listing to a rental company's own listing list when the Book>Direct link does not reach the listing.

Destination-independent. Two methods, both strict; a listing that does not meet one exactly stays unmatched:

- address: the same normalized street number + street name (common abbreviations and the 30A road names are unified), the same
  unit number when either side has one, the same number of bedrooms, and exactly one such candidate in the company's list. When
  both sides carry coordinates they must also lie within ADDRESS_SANITY_M of each other.
- location (only when the company's list gives no street address): at most LOCATION_MATCH_M apart, the same bedrooms and
  bathrooms, and exactly one unit with those values within LOCATION_UNIQUE_M. Not used where another Book>Direct listing lies
  within LOCATION_MATCH_M (buildings with many units).

A listing's title is never used to match; it is only written to the record.
"""
import html as html_module
import json
import math
import re

LOCATION_MATCH_M = 15.0
LOCATION_UNIQUE_M = 50.0
ADDRESS_SANITY_M = 2000.0

DIRECTIONS = {"east": "e", "west": "w", "north": "n", "south": "s", "northeast": "ne", "northwest": "nw", "southeast": "se",
              "southwest": "sw"}
# Street-type words and a few common name words, in their USPS abbreviations. Both sides go through the same table.
WORDS = {
    "street": "st", "drive": "dr", "avenue": "ave", "av": "ave", "road": "rd", "lane": "ln", "boulevard": "blvd", "circle": "cir",
    "court": "ct", "place": "pl", "trail": "trl", "terrace": "ter", "parkway": "pkwy", "alley": "aly", "square": "sq", "cove": "cv",
    "point": "pt", "crossing": "xing", "highway": "hwy", "bend": "bnd", "landing": "lndg", "green": "grn", "plaza": "plz",
    "ridge": "rdg", "trace": "trce", "view": "vw", "vista": "vis", "grove": "grv", "harbor": "hbr", "heights": "hts", "lake": "lk",
    "meadow": "mdw", "meadows": "mdws", "mountain": "mtn", "mount": "mt", "fort": "ft", "island": "is", "isle": "is", "pass": "pass",
    "way": "way", "wy": "way", "walk": "walk", "path": "path", "run": "run", "row": "row", "loop": "loop", "park": "park",
    "hollow": "holw", "estates": "ests", "village": "vlg", "beach": "bch",
}
STREET_TYPES = {"st", "dr", "ave", "rd", "ln", "blvd", "cir", "ct", "pl", "trl", "ter", "pkwy", "aly", "sq", "cv", "pt", "xing", "hwy",
                "bnd", "lndg", "plz", "rdg", "trce", "way", "walk", "path", "run", "row", "loop", "holw", "pass", "vw", "grn", "mdws"}
ROAD_WORDS = {"scenic", "county", "cty", "co", "c", "cr", "hwy", "highway", "road", "rd", "state", "sr"}
UNIT_MARKERS = {"unit", "apt", "apartment", "ste", "suite", "#", "no", "number"}


def tokens(text):
    text = html_module.unescape(text or "").lower()
    text = text.replace("#", " # ")
    text = re.sub(r"[.,;:()\"'’/\\-]", " ", text)
    return [t for t in text.split() if t]


def normalize_address(text):
    """'2381 W County Highway 30a #5' -> ('2381', 'w 30a', '5'); None when there is no leading street number.

    Unit: what follows a unit marker (Unit, Apt, Suite, #) or what follows the street once the street ended with a street type or
    the 30A road. Building words (Bldg) stay in the unit text."""
    parts = tokens(text)
    if not parts or not re.fullmatch(r"\d+[a-z]?", parts[0]):
        return None
    number, rest = parts[0], parts[1:]
    # 30A in every spelling: drop the road words right before it ("County Highway 30A", "CR 30A", "Scenic Hwy 30A").
    words = []
    index = 0
    while index < len(rest):
        token = rest[index]
        if token == "30" and index + 1 < len(rest) and rest[index + 1] == "a":
            token, index = "30a", index + 1
        if token == "30a":
            while words and words[-1] in ROAD_WORDS:
                words.pop()
        words.append(token)
        index += 1
    street, unit, ended, in_unit = [], [], False, False
    for token in words:
        if token in UNIT_MARKERS:
            in_unit = True
            continue
        if in_unit or ended:
            unit.append(token)
            continue
        short = DIRECTIONS.get(token) or WORDS.get(token, token)
        street.append(short)
        if short in STREET_TYPES or short == "30a":
            ended = True
    if not street:
        return None
    return number, " ".join(street), " ".join(unit) or None


def same_rooms(a, b):
    return a is not None and b is not None and abs(float(a) - float(b)) < 0.01


def distance_m(lat1, lon1, lat2, lon2):
    radius = 6_371_008.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(h)))


def has_point(item):
    return item.get("latitude") is not None and item.get("longitude") is not None


def address_match(listing, units):
    """('matched', unit, note) / ('ambiguous', None, note) / ('none', None, note) / ('unusable', None, note) by the address rule."""
    key = normalize_address(listing.get("address"))
    if key is None:
        return "unusable", None, "Book>Direct adresi sokak numarasıyla başlamıyor."
    if listing.get("bedrooms") is None:
        return "unusable", None, "Book>Direct ilanında oda sayısı yok."
    number, street, unit = key
    candidates = []
    for item in units:
        other = normalize_address(item.get("address"))
        if other is None or other[0] != number or other[1] != street:
            continue
        if (unit or other[2]) and unit != other[2]:
            continue
        if not same_rooms(listing["bedrooms"], item.get("bedrooms")):
            continue
        candidates.append(item)
    shown = f"{number} {street}" + (f" #{unit}" if unit else "")
    if not candidates:
        return "none", None, f"Adres eşlemesi: '{shown}', {listing['bedrooms']:g} oda için şirket listesinde aday yok."
    if len(candidates) > 1:
        return "ambiguous", None, f"Adres eşlemesi belirsiz: '{shown}' için {len(candidates)} aday."
    found = candidates[0]
    if has_point(listing) and has_point(found):
        gap = distance_m(listing["latitude"], listing["longitude"], found["latitude"], found["longitude"])
        if gap > ADDRESS_SANITY_M:
            return "none", None, f"Adres aynı ama iki taraftaki koordinatlar {gap / 1000:.1f} km uzak; eşlenmedi."
    return "matched", found, f"Adres: '{shown}', {listing['bedrooms']:g} oda; şirket ilanı: {found.get('address')}."


def crowded(listing, all_listings):
    """True when another Book>Direct listing lies within LOCATION_MATCH_M (a building with several units)."""
    if not has_point(listing):
        return False
    return any(other["lodging_id"] != listing["lodging_id"] and has_point(other)
               and distance_m(listing["latitude"], listing["longitude"], other["latitude"], other["longitude"]) <= LOCATION_MATCH_M
               for other in all_listings)


def location_match(listing, units, all_listings):
    """('matched', unit, note) / ('ambiguous'|'none'|'unusable'|'crowded', None, note) by the location rule."""
    if not has_point(listing):
        return "unusable", None, "Book>Direct ilanında koordinat yok."
    if listing.get("bedrooms") is None or listing.get("bathrooms") is None:
        return "unusable", None, "Book>Direct ilanında oda veya banyo sayısı yok."
    if crowded(listing, all_listings):
        return "crowded", None, f"Aynı {LOCATION_MATCH_M:g} m içinde başka Book>Direct ilanı var (çok daireli yapı); konum yöntemi kullanılmadı."
    near = []
    for item in units:
        if not has_point(item) or not same_rooms(listing["bedrooms"], item.get("bedrooms")) or not same_rooms(listing["bathrooms"], item.get("bathrooms")):
            continue
        gap = distance_m(listing["latitude"], listing["longitude"], item["latitude"], item["longitude"])
        if gap <= LOCATION_UNIQUE_M:
            near.append((gap, item))
    rooms = f"{listing['bedrooms']:g} oda / {listing['bathrooms']:g} banyo"
    if len(near) > 1:
        return "ambiguous", None, f"Konum eşlemesi belirsiz: {LOCATION_UNIQUE_M:g} m içinde {rooms} olan {len(near)} şirket ilanı."
    if not near or near[0][0] > LOCATION_MATCH_M:
        return "none", None, f"Konum eşlemesi: {LOCATION_MATCH_M:g} m içinde {rooms} olan şirket ilanı yok."
    gap, found = near[0]
    return "matched", found, f"Konum: {gap:.1f} m, {rooms}; şirket ilanı: {found.get('title') or found.get('url')}."


# --- Listing details read from a company's own listing page ----------------------------------------------------------------

def number(value):
    try:
        return float(str(value).strip()) if value not in (None, "") else None
    except ValueError:
        return None


def json_ld_unit(text):
    """Street address, coordinates, bedrooms, bathrooms and capacity of the lodging a page describes in schema.org JSON-LD
    (VacationRental / Accommodation and kin). An Organization or LocalBusiness address (the company office) is never used."""
    lodging_types = {"VacationRental", "Accommodation", "House", "Apartment", "SingleFamilyResidence", "Residence", "Suite", "Room",
                     "LodgingReservation"}
    found = {}

    def walk(node):
        if isinstance(node, list):
            for child in node:
                walk(child)
            return
        if not isinstance(node, dict):
            return
        kind = node.get("@type")
        kinds = set(kind if isinstance(kind, list) else [kind])
        if kinds & lodging_types:
            address = node.get("address")
            if isinstance(address, dict) and address.get("streetAddress") and "address" not in found:
                found["address"] = html_module.unescape(str(address["streetAddress"])).strip()
                found["city"] = address.get("addressLocality")
            geo = node.get("geo")
            if isinstance(geo, dict) and "latitude" not in found and number(geo.get("latitude")) is not None:
                found["latitude"], found["longitude"] = number(geo.get("latitude")), number(geo.get("longitude"))
            for key, target in (("numberOfBedrooms", "bedrooms"), ("numberOfBathroomsTotal", "bathrooms")):
                value = node.get(key)
                value = value.get("value") if isinstance(value, dict) else value
                if number(value) is not None and target not in found:
                    found[target] = number(value)
            occupancy = node.get("occupancy")
            if isinstance(occupancy, dict) and number(occupancy.get("maxValue")) is not None and "sleeps" not in found:
                found["sleeps"] = number(occupancy.get("maxValue"))
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', text, re.S | re.I):
        try:
            walk(json.loads(block.strip()))
        except ValueError:
            continue
    return found
