"""Restaurant facts from the businesses' own websites: site status, menus and menu prices, opening hours, reservations, kids
menu, outdoor seating, water view and dogs.

Generic core: reading a business site, finding its menus (HTML pages, PDFs, images, menu/ordering platform pages the business
publishes), schema.org structured data, reservation-platform recognition, menu price parsing and the menu-section
classification table (menu_sections.csv) are destination-independent. The destination supplies the restaurant list (its latest
directory run: name, website, phone, address, neighborhoods) and two reviewed files: the official site found by a web search
when the directory has none or a broken one (accepted only when the site shows the same address or phone), and the menu items
read by a person from image menus (each tied to the image's SHA-256, labelled "görüntüden okundu").

Nothing is inferred beyond what a page says: an amenity a site does not mention is unknown, never "no"; "no" is recorded only
when the site says it. Every stored value keeps its page url, access time, raw SHA-256 and method label. Requests to one host are
sequential and REQUEST_GAP seconds apart; several restaurants are read side by side; one site's failure never stops the others.
Derived numbers (main-dish medians, price level) are computed when read and labelled as ours.
"""
import base64
import csv
import gzip
import hashlib
import html as html_module
import io
import json
import re
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode, urljoin, urlsplit, urlunsplit

import httpx

from .base import CollectionCanceled, CollectionResult, SourceError
from .browser_verification import FINAL_WAIT_SECONDS, GRACE_SECONDS, host_key, mark_hosts
from .climate_http import check, pause

CONNECTOR_VERSION = "restaurant-sites/1"
SOURCE_QUERY = "kaynak=isletme-siteleri"
SECTIONS_TABLE = Path(__file__).with_name("menu_sections.csv")
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36 "
              "30AStudio/0.12 (+https://github.com/bemonths/tatilya)")
REQUEST_GAP = 2.0               # seconds between two requests to the same host
WORKERS = 6
MAX_BYTES = 20_000_000
MAX_DOCUMENTS = 12              # menu pages and documents fetched per restaurant
MAX_INFO_PAGES = 3              # hours / contact / about pages read per restaurant
MAX_REDIRECTS = 5
PROGRESS_EVERY = 2.0

SITE_STATUSES = ("working", "not_found", "closed_permanently", "closed_season", "other_business", "unreachable", "social_login", "no_site")
FIELDS = ("hours", "reservation", "kids_menu", "outdoor_seating", "water_view", "dog_friendly", "site_price_range", "review_note")
METHODS = ("yapısal veri", "sayfa metni", "PDF metni", "platform verisi", "görüntüden okundu", "elle okundu", "bağlantı", "gözden geçirme")
MENU_TYPES = ("dinner", "lunch", "general", "brunch", "breakfast", "kids", "drinks", "dessert", "happy_hour", "catering", "special")
MAIN_PRIORITY = ("dinner", "lunch", "general", "brunch", "breakfast")      # the main meal menu the price level is computed from
# kucuk_tabak: tapas / small plates (their median is shown apart, never as mains); sabit_menu: a fixed price per person (prix fixe,
# tasting menu), kept apart from the main-dish median.
SECTION_CLASSES = ("ana_yemek", "baslangic", "salata_corba", "kucuk_tabak", "sabit_menu", "tatli", "icecek", "cocuk", "yan_urun", "diger")
# An add-on, extra, topping, sauce or side is never a main dish, whatever section it is printed in.
ADDON_NAME = re.compile(r"^(?:add|\+|sub|substitute|side of|extra|toppings?|sauces?|upgrade|make it|additional|each additional|gourmet toppings?|"
                        r"all side choices|side choices?)\b|\bcrust available\b|\bgluten[- ]free (?:crust|option|bun|bread)\b", re.I)
# A drink or a kids' item by its own name is never a main dish, whatever section a page's layout put it in (GÖREV-10 review of the
# main dishes under $8: drinks and toppings read under a pizza heading).
DRINK_NAME = re.compile(r"^(?:coffee|espresso|cappuccino|latte|(?:hot |iced |sweet |bottled sweet )?tea|coke|diet coke|coca[- ]cola|sprite|fanta|"
                        r"(?:diet )?dr\.? pepper|root beer|lemonade|(?:orange |apple )?juice|(?:chocolate )?milk|sodas?|(?:32 oz )?fountain drinks?|"
                        r"bottled drinks|(?:bottled |spring )?water|fronte bottles spring water|san pellegrino(?: mineral water)?|(?:asst\.? )?gatorade|"
                        r"beers?|beverages?|(?:domestic|imported|italian|craft) (?:draft|bottled?|bottles|beer)s?(?: & (?:draft|bottled?|bottles))?|"
                        r"refills?|red bull)$", re.I)
KIDS_NAME = re.compile(r"^(?:kids?'?|kid's|children'?s)\b", re.I)
PRICE_LEVELS = ((15, "$"), (25, "$$"), (40, "$$$"), (float("inf"), "$$$$"))
MIN_MAIN_PRICES = 5
SOCIAL_HOSTS = ("facebook.com", "instagram.com", "fb.com", "tiktok.com", "x.com", "twitter.com")
RESERVATION_PLATFORMS = {"opentable.com": "OpenTable", "resy.com": "Resy", "exploretock.com": "Tock", "sevenrooms.com": "SevenRooms",
                         "tables.toasttab.com": "Toast Tables", "resos.com": "resOS", "tablein.com": "Tablein", "yelp.com/reservations": "Yelp"}
MENU_PLATFORMS = {"toasttab.com": "Toast", "square.site": "Square", "squareup.com": "Square", "popmenu.com": "Popmenu", "getbento.com": "BentoBox",
                  "spothopperapp.com": "SpotHopper", "spothopper.com": "SpotHopper", "chownow.com": "ChowNow", "olo.com": "Olo",
                  "clover.com": "Clover", "menufy.com": "Menufy", "order.online": "DoorDash Storefront", "singleplatform.com": "SinglePlatform",
                  "ohbz.com": "ohbz", "toast.site": "Toast",
                  "menu.app": "Menu.app", "beyondmenu.com": "BeyondMenu", "touchbistro.com": "TouchBistro", "owner.com": "Owner.com"}
MENU_WORD = re.compile(r"\bmenus?\b|\bdinner\b|\blunch\b|\bbrunch\b|\bbreakfast\b|\bkids\b|\bchildren'?s\b|\bdrinks?\b|\bcocktails?\b|\bwine list\b|"
                       r"\bdesserts?\b|\bhappy hour\b|\bfood\b|\beat\b|\border online\b|\btapas\b", re.I)
INFO_WORD = re.compile(r"\bhours\b|\bcontact\b|\blocation|\bvisit\b|\babout\b|\bfaq\b|\bfind us\b", re.I)
# Pages of a menu platform that are not a menu: one dish of an ordering menu (the whole menu is on the ordering page), legal pages.
NOT_MENU_PAGE = re.compile(r"/item-[^/]*_[0-9a-f]{8}-|[?&]item=|/(?:privacy|terms|terms-of-service|rewardssignup|rewardslookup|egiftcards?|giftcards?)\b", re.I)
TYPE_WORDS = (("special", r"thanksgiving|christmas|\bholiday|new year|valentine|easter|mother'?s day|father'?s day"),
              ("catering", r"\bcatering\b"), ("happy_hour", r"happy hour"), ("kids", r"\bkids?\b|\bchildren'?s?\b|\blittle ones\b"),
              ("dessert", r"\bdesserts?\b|\bsweets\b"),
              ("drinks", r"\bdrinks?\b|\bcocktails?\b|\bwine\b|\bbeer\b|\bbar menu\b|\bbeverages?\b|\bspirits\b"),
              ("brunch", r"\bbrunch\b"), ("breakfast", r"\bbreakfast\b"), ("lunch", r"\blunch\b"), ("dinner", r"\bdinner\b|\bsupper\b|\bevening\b"))
PARKED = re.compile(r"domain (?:is|may be) for sale|buy this domain|this domain has expired|domain name (?:is )?for sale|parked (?:free|domain)|"
                    r"hugedomains|sedo domain parking|is for sale!", re.I)
PARKING_SCRIPT = re.compile(r"sk-park\.php|parkingcrew\.net|bodis\.com/|sedoparking\.com|window\.park\s*=", re.I)
CLOSED_FOR_GOOD = re.compile(r"permanently closed|closed permanently|(?:we|restaurant) (?:have|has) (?:permanently )?closed (?:our|its) doors|"
                             r"closed for good|thank you for \d+ (?:wonderful )?years", re.I)
CLOSED_SEASON = re.compile(r"closed for the (?:season|winter|off[- ]season)|seasonal(?:ly)? closed|closed for (?:our )?(?:winter|seasonal) break|"
                           r"closed until (?:spring|march|april|february|may)\b", re.I)
NO_RESERVATIONS = re.compile(r"(?:do not|don'?t|does not|doesn'?t|cannot|can'?t) (?:take|accept|offer) reservations|no reservations|"
                             r"reservations are not (?:accepted|available|taken)|first[- ]come,? first[- ]served|walk[- ]ins? only", re.I)
WAITLIST = re.compile(r"\bjoin (?:the|our) (?:wait ?list|waitlist)|\bwait ?list\b|\bget in line\b|\bnowait\b", re.I)
PHONE_RESERVATIONS = re.compile(r"(?:call|phone)(?: us)? (?:for|to make|to book) (?:a |your )?reservations?|reservations?(?: are)? (?:by|via|over the) "
                                r"(?:phone|telephone)|for reservations,? (?:please )?call|reservations:?\s*\(?\d{3}\)?[\s.-]?\d{3}", re.I)
OUTDOOR = re.compile(r"outdoor (?:seating|dining|patio|deck|bar|courtyard)|\bpatio\b|\bcourtyard\b|al ?fresco|\brooftop\b|beer garden|"
                     r"outside (?:seating|dining)|deck seating|open[- ]air", re.I)
NO_OUTDOOR = re.compile(r"no outdoor seating|indoor seating only", re.I)
WATER_VIEW = re.compile(r"(?:gulf|ocean|bay|lake|water|beach|sunset)[- ]?(?:front|views?)\b|overlook(?:s|ing) (?:the )?(?:gulf|bay|lake|water|ocean|beach)|"
                        r"\bwaterfront\b|\bbeachfront\b|on the (?:water|bay|beach|lake)\b|views? of the (?:gulf|bay|lake|water|ocean)", re.I)
DOGS = re.compile(r"dog[- ]friendly|pet[- ]friendly|dogs? (?:are )?welcome|bring (?:your|the) (?:dog|pup|pooch)|pups? (?:are )?welcome|"
                  r"four[- ]legged (?:friends|guests)", re.I)
NO_DOGS = re.compile(r"no (?:dogs|pets)(?: allowed| permitted)?\b|pets are not (?:allowed|permitted)|service animals only", re.I)
KIDS_TEXT = re.compile(r"kids'? menu|children'?s menu|kid'?s menu|menu for (?:kids|children)|kids eat", re.I)
NO_KIDS = re.compile(r"no (?:kids|children'?s) menu", re.I)
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
DAY_NAMES = {"mon": 0, "monday": 0, "mo": 0, "tue": 1, "tues": 1, "tuesday": 1, "tu": 1, "wed": 2, "weds": 2, "wednesday": 2, "we": 2,
             "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "th": 3, "fri": 4, "friday": 4, "fr": 4, "sat": 5, "saturday": 5, "sa": 5,
             "sun": 6, "sunday": 6, "su": 6}
SCHEMA_DAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(text):
    return re.sub(r"\s+", " ", html_module.unescape(text or "")).strip()


def host_of(url):
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def on_host(url, suffixes):
    host = host_of(url)
    return any(host == s or host.endswith("." + s) for s in suffixes)


def platform_of(url, table):
    host, path = host_of(url), urlsplit(url).path.lower()
    for key, name in table.items():
        domain, _, prefix = key.partition("/")
        if (host == domain or host.endswith("." + domain)) and path.startswith("/" + prefix if prefix else "/"):
            return name
    return None


# --- Reading pages -----------------------------------------------------------------------------------------------------------

class Document:
    def __init__(self, url, final_url, status, content_type, body, sha256, fetched_at, note):
        self.url, self.final_url, self.status, self.content_type, self.body = url, final_url, status, content_type, body
        self.sha256, self.fetched_at, self.note = sha256, fetched_at, note

    @property
    def kind(self):
        kind = (self.content_type or "").split(";")[0].strip().lower()
        if kind == "application/pdf" or self.body[:5] == b"%PDF-":
            return "pdf"
        if kind.startswith("image/"):
            return "image"
        if "html" in kind or self.body.lstrip()[:1] == b"<":
            return "html"
        return "other"

    @property
    def text(self):
        return self.body.decode("utf-8", errors="replace")


class RawStore:
    def __init__(self, path):
        self.path, self.lock = path, threading.Lock()
        self.manifest = {"connector": CONNECTOR_VERSION, "responses": []}

    def save(self, *, restaurant, requested, final_url, status, content_type, body, note):
        digest = hashlib.sha256(body).hexdigest()
        with self.lock:
            sequence = len(self.manifest["responses"]) + 1
            relative = f"responses/{sequence:06d}.gz"
            target = self.path.parent / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(gzip.compress(body, mtime=0))
            stamp = now()
            self.manifest["fetched_at"] = stamp
            self.manifest["responses"].append({"sequence": sequence, "restaurant": restaurant, "note": note, "requested_url": requested,
                                               "final_url": final_url, "status": status, "content_type": content_type, "fetched_at": stamp,
                                               "raw_file": relative, "compression": "gzip", "raw_sha256": digest, "bytes": len(body)})
            if sequence % 25 == 0:
                self._flush()
        return digest, stamp

    def flush(self):
        with self.lock:
            self._flush()

    def _flush(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        temporary.replace(self.path)

    @property
    def count(self):
        with self.lock:
            return len(self.manifest["responses"])


class HostPacer:
    """At most one request at a time per host, REQUEST_GAP seconds apart, across all workers."""

    def __init__(self):
        self.lock, self.hosts = threading.Lock(), {}

    def slot(self, host):
        with self.lock:
            return self.hosts.setdefault(host, {"lock": threading.Lock(), "last": None})


class Fetcher:
    def __init__(self, client, store, pacer, canceled):
        self.client, self.store, self.pacer, self.canceled = client, store, pacer, canceled
        self.cache, self.cache_lock = {}, threading.Lock()

    def get(self, url, *, restaurant, note):
        """GET with redirects followed (each hop kept). Returns Document or raises httpx.HTTPError / SourceError. Restaurants that
        share a page (one site for several locations) read it once in a run: a later request gets the same document."""
        with self.cache_lock:
            lock = self.cache.setdefault(url, {"lock": threading.Lock(), "document": None})
        with lock["lock"]:
            if lock["document"] is None or lock["document"].status not in (200,):
                lock["document"] = self.fetch(url, restaurant=restaurant, note=note)
            return lock["document"]

    def fetch(self, url, *, restaurant, note):
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            check(self.canceled)
            parts = urlsplit(current)
            if parts.scheme not in ("http", "https") or not parts.hostname:
                raise SourceError("Geçersiz adres.")
            slot = self.pacer.slot(parts.hostname.lower())
            with slot["lock"]:
                if slot["last"] is not None:
                    pause(max(0.0, REQUEST_GAP - (time.monotonic() - slot["last"])), self.canceled)
                try:
                    status, headers, body = self.send(current)
                finally:
                    slot["last"] = time.monotonic()
            content_type = headers.get("content-type")
            digest, stamp = self.store.save(restaurant=restaurant, requested=current, final_url=current, status=status,
                                            content_type=content_type, body=body, note=note)
            if status in (301, 302, 303, 307, 308) and headers.get("location"):
                current = urljoin(current, headers["location"])
                continue
            return Document(url, current, status, content_type, body, digest, stamp, note)
        raise SourceError("Yönlendirme sınırı aşıldı.")

    def send(self, url):
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/pdf,image/*;q=0.8,*/*;q=0.5",
                   "Accept-Language": "en-US,en;q=0.9"}
        with self.client.stream("GET", url, headers=headers, follow_redirects=False) as response:
            chunks, size = [], 0
            for part in response.iter_bytes():
                size += len(part)
                if size > MAX_BYTES:
                    raise SourceError("Yanıt boyut sınırını aştı.")
                chunks.append(part)
            return response.status_code, {k.lower(): v for k, v in response.headers.items()}, b"".join(chunks)


# --- Page text, links and structured data ------------------------------------------------------------------------------------

JS_BUILT = re.compile(r"__NEXT_DATA__|data-reactroot|id=\"root\"></div>|id=\"app\"></div>|ng-app|wix-thunderbolt|popmenu|toasttab", re.I)
HEADING_CLASS = re.compile(r'class="[^"]*(?:menu[-_ ]?section[-_ ]?(?:title|name|header|heading)|section[-_ ]?(?:title|header|heading)|'
                           r'category[-_ ]?(?:title|name|header|heading)|group[-_ ]?(?:title|name)|menu-title|menu-heading)[^"]*"', re.I)


def html_lines(html):
    """The page as text lines: ('h', heading) for h1-h6 and section-title elements, ('p', text) otherwise."""
    text = re.sub(r"(?is)<!--.*?-->|<(script|style|noscript|svg|template|head)\b.*?</\1>", " ", html)
    def heading(match):
        inner = clean(re.sub(r"<[^>]+>", " ", match.group(2)))
        return f"\n§H§{inner}\n" if inner else "\n"
    text = re.sub(r"(?is)<(h[1-6])\b[^>]*>(.*?)</\1>", heading, text)
    text = re.sub(r"(?is)<(div|span|p|dt|li|strong|b)\b([^>]*" + HEADING_CLASS.pattern + r"[^>]*)>(.*?)</\1>",
                  lambda m: f"\n§H§{clean(re.sub(r'<[^>]+>', ' ', m.group(3)))}\n", text)
    text = re.sub(r"(?i)<br\s*/?>|</?(?:p|div|li|ul|ol|tr|td|th|table|tbody|thead|section|article|header|footer|main|aside|nav|dt|dd|dl|"
                  r"figure|figcaption|blockquote|form|label|button|option)\b[^>]*>", "\n", text)
    text = html_module.unescape(re.sub(r"<[^>]+>", " ", text))
    lines = []
    for raw in text.split("\n"):
        line = clean(raw)
        if not line:
            continue
        if line.startswith("§H§"):
            heading = clean(line.replace("§H§", " "))           # a heading element inside another one leaves a second marker
            if heading:
                lines.append(("h", heading))
        else:
            lines.append(("p", clean(line.replace("§H§", " "))))
    return lines


def page_title(html):
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    return clean(match.group(1)) if match else ""


def links(html, base):
    """(text, absolute url) of every link and of image/document sources named 'menu'."""
    found = []
    for match in re.finditer(r'(?is)<a\b([^>]*)>(.*?)</a>', html):
        href = re.search(r'href\s*=\s*["\']([^"\'#][^"\']*)["\']', match.group(1))
        if not href:
            continue
        target = urljoin(base, html_module.unescape(href.group(1).strip()))
        if not target.startswith(("http://", "https://")):
            continue
        label = clean(re.sub(r"<[^>]+>", " ", match.group(2))) or clean(" ".join(re.findall(r'(?:title|aria-label|alt)\s*=\s*["\']([^"\']+)', match.group(0))))
        found.append((label, target))
    for match in re.finditer(r'(?is)<(?:iframe|embed|object)\b[^>]*?(?:src|data)\s*=\s*["\']([^"\']+)["\'][^>]*>', html):
        if re.search(r"menu", match.group(0), re.I):
            target = urljoin(base, html_module.unescape(match.group(1).strip()))
            if target.startswith(("http://", "https://")):
                found.append(("menu", target))
    return found


def json_ld(html):
    """schema.org objects of food businesses (Restaurant, FoodEstablishment, BarOrPub, CafeOrCoffeeShop, ...)."""
    kinds = {"Restaurant", "FoodEstablishment", "BarOrPub", "CafeOrCoffeeShop", "Bakery", "Brewery", "Winery", "FastFoodRestaurant",
             "IceCreamShop", "LocalBusiness", "Distillery"}
    found = []
    def walk(node):
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            kind = node.get("@type")
            if set(kind if isinstance(kind, list) else [kind]) & kinds:
                found.append(node)
            for key in ("@graph", "mainEntity", "itemListElement"):
                if key in node:
                    walk(node[key])
    for block in re.findall(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html):
        try:
            walk(json.loads(block.strip()))
        except ValueError:
            continue
    return found


def schema_menus(html, base):
    """Menus a page publishes as schema.org structured data (Menu > MenuSection > MenuItem with offers), as
    [{'name', 'url', 'items': [{'section', 'name', 'price_text', 'price', 'price_rule'}]}]. The price is the offer's price as
    published (several offers: the lowest, 'lowest'); an item without a priced offer is left out, as on a printed menu."""
    menus = []

    def kinds(node):
        kind = node.get("@type")
        return set(kind if isinstance(kind, list) else [kind])

    def items_of(node, section, out):
        if isinstance(node, list):
            for child in node:
                items_of(child, section, out)
            return
        if not isinstance(node, dict):
            return
        if "MenuSection" in kinds(node):
            section = clean(node.get("name")) or section
        if "MenuItem" in kinds(node):
            offers = node.get("offers")
            offers = offers if isinstance(offers, list) else [offers] if offers else []
            published = []
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                for key in ("price", "lowPrice"):
                    raw = offer.get(key)
                    try:
                        value = float(str(raw).replace("$", "").replace(",", "").strip())
                    except (TypeError, ValueError):
                        continue
                    if value > 0:
                        published.append((value, str(raw).strip()))
                        break
            name = clean(node.get("name"))
            if name and published:
                values = sorted(published)
                out.append({"section": section, "name": name, "price_text": " / ".join(text for _, text in published), "price": values[0][0],
                            "price_rule": "lowest" if len(values) > 1 else "single"})
        for key in ("hasMenuSection", "hasMenuItem"):
            if key in node:
                items_of(node[key], section, out)

    def walk(node):
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            if "Menu" in kinds(node):
                items = []
                items_of([node.get("hasMenuSection") or [], node.get("hasMenuItem") or []], None, items)
                if items:
                    url = node.get("url") if isinstance(node.get("url"), str) else None
                    menus.append({"name": clean(node.get("name")) or None, "url": urljoin(base, url) if url else None, "items": items})
                return
            for key in ("@graph", "hasMenu", "menu", "mainEntity", "itemListElement"):
                if key in node:
                    walk(node[key])

    for block in re.findall(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html):
        try:
            walk(json.loads(block.strip()))
        except ValueError:
            continue
    return menus


def tab_panels(html):
    """[(label, panel html)] of a page that shows its menus in tabs (role="tab" naming a role="tabpanel"; BentoBox and other site
    builders): each tab is read as its own menu, so a kids or holiday tab never mixes into the dinner menu. Carousel buttons
    ("1 of 7") are not tabs."""
    labels = {}
    for tag in re.findall(r'(?is)<(?:a|button|li)\b[^>]*\brole="tab"[^>]*>', html):
        controls = re.search(r'aria-controls="([^"]+)"', tag)
        label = re.search(r'aria-label="([^"]*)"', tag)
        if controls and label and not re.fullmatch(r"\d+ of \d+", clean(label.group(1))):
            labels[controls.group(1)] = clean(label.group(1))
    if len(labels) < 2:
        return []
    starts = []
    for match in re.finditer(r'(?is)<(?:section|div)\b[^>]*\brole="tabpanel"[^>]*>', html):
        ident = re.search(r'\bid="([^"]+)"', match.group(0))
        if ident and ident.group(1) in labels:
            starts.append((match.start(), labels[ident.group(1)]))
    panels = []
    for index, (start, label) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else min(len(html), start + 400_000)
        panels.append((label, html[start:end]))
    return panels if len(panels) >= 2 else []


MHM_ITEM = re.compile(r'(?is)<div[^>]*class="item\b[^"]*"[^>]*data-source="mhm"[^>]*>')
MHM_SECTION = re.compile(r'(?is)<div[^>]*class="mo-name\b[^"]*"[^>]*>(.*?)</div>')


SP_TOKEN = re.compile(r'(?is)<h2[^>]*class="menu-title"[^>]*>(.*?)</h2>|<div class="title">\s*<h3[^>]*>(.*?)</h3>'
                      r'|<div class="menu(?:\s[^"]*)?"\s+id="menu-(\d+)"[^>]*>|<div class="item(?:\s[^"]*)?"[^>]*>')
SP_WIDGET = re.compile(r'(?is)<script\b[^>]*\bsrc\s*=\s*["\'](?:https?:)?//menus\.singleplatform\.com/widget[^>]*>')
IFRAME_SRC = re.compile(r'(?is)<iframe\b[^>]*?\bsrc\s*=\s*["\']([^"\']+)["\']')


def singleplatform_menus(html):
    """Menus of a SinglePlatform menu page (places.singleplatform.com/<place>/menu_widget: the frame its widget shows on many
    restaurant sites). Each menu title starts a menu, each section title a section; an item is priced only by the price in its own
    title row ('+ …' add-on rows under it are not items, an item without a price is left out). Same shape as schema_menus."""
    if 'class="item-title-row"' not in html:
        return []
    names = {m.group(1): clean(re.sub(r"<[^>]+>", " ", m.group(2))) or None
             for m in re.finditer(r'(?is)<div[^>]*class="menu-name[^"]*"[^>]*toggle="#menu-(\d+)"[^>]*>(.*?)</div>', html)}
    tokens = list(SP_TOKEN.finditer(html))
    menus, current, section, title = [], None, None, None
    for index, token in enumerate(tokens):
        if token.group(1) is not None:          # the shown menu's title (a page of several menus names them in its menu list)
            title = clean(re.sub(r"<[^>]+>", " ", token.group(1))) or None
            continue
        if token.group(3) is not None:          # one menu of the page
            current, section = {"name": names.get(token.group(3)) or title, "url": None, "items": []}, None
            menus.append(current)
            continue
        if token.group(2) is not None:
            section = clean(re.sub(r"<[^>]+>", " ", token.group(2))) or None
            continue
        block = html[token.end():tokens[index + 1].start() if index + 1 < len(tokens) else len(html)]
        row = re.search(r'(?is)<div class="item-title-row">(.*?)</div>', block)
        name = re.search(r'(?is)<h4[^>]*class="item-title"[^>]*>(.*?)</h4>', row.group(1)) if row else None
        if not name:
            continue
        name_text = clean(re.sub(r"<[^>]+>", " ", name.group(1)))
        price_text = " / ".join(t for t in (clean(re.sub(r"<[^>]+>", " ", m)) for m in re.findall(r'(?is)<span[^>]*class="price"[^>]*>(.*?)</span>', row.group(1))) if t)
        values = [v for v in (float(x) for x in re.findall(r"\d{1,4}(?:\.\d{1,2})?", price_text.replace(",", ""))) if v > 0]
        if not name_text or not values or ADDON_NAME.match(name_text):
            continue
        if current is None:
            current = {"name": title, "url": None, "items": []}
            menus.append(current)
        current["items"].append({"section": section, "name": name_text, "price_text": price_text, "price": min(values),
                                 "price_rule": "lowest" if len(values) > 1 else "single"})
    return [m for m in menus if m["items"]]


def embedded_menus(html, base):
    """Menus a page embeds instead of linking: the SinglePlatform widget script (its menu frame is a plain page at
    places.singleplatform.com/<place>/menu_widget with the widget's own attributes) and frames whose address is a menu platform
    (ohbz, SinglePlatform, Toast...). Returned as (label, url) menu links, so they are fetched directly, without a browser."""
    found = []
    for tag in SP_WIDGET.finditer(html):
        attrs = {k.lower(): html_module.unescape(v) for k, v in re.findall(r'data-([a-z_]+)\s*=\s*["\']([^"\']*)["\']', tag.group(0))}
        if attrs.get("location"):
            query = urlencode({k: attrs[k] for k in ("api_key", "display_menu") if attrs.get(k)}, safe=",")      # the widget's own form
            found.append(("SinglePlatform menüsü", f"https://places.singleplatform.com/{quote(attrs['location'])}/menu_widget" + (f"?{query}" if query else "")))
    for match in IFRAME_SRC.finditer(html):
        src = urljoin(base, html_module.unescape(match.group(1).strip()))
        if src.startswith("http") and platform_of(src, MENU_PLATFORMS):
            found.append(("gömülü menü", src))
    return found


def mhm_menus(html):
    """Menu items of a menu designed on ohbz.com (embedded by many restaurant sites): each dish is an element whose attributes name
    it and its price (aria-label="Item name: …", aria-label="Price: …"); its section is the block title before it (class mo-name),
    when the design has one. Same shape as schema_menus; one menu per page."""
    sections = [(m.start(), clean(re.sub(r"<[^>]+>", " ", m.group(1)))) for m in MHM_SECTION.finditer(html)]
    starts = [m.start() for m in MHM_ITEM.finditer(html)]
    items = []
    for index, start in enumerate(starts):
        block = html[start:starts[index + 1] if index + 1 < len(starts) else start + 6000]
        name = re.search(r'aria-label="Item name:\s*([^"]*)"', block)
        price = re.search(r'aria-label="Price:\s*([^"]*)"', block)
        if name:
            name_text = clean(html_module.unescape(name.group(1)))
        else:                                       # print-style designs: <span class="name"> and data-pv="16" price entries
            span = re.search(r'(?is)<(span|div)[^>]*class="name"[^>]*>(.*?)</\1>', block)
            name_text = clean(re.sub(r"<[^>]+>", " ", html_module.unescape(span.group(2)))) if span else ""
        if price:
            price_text = clean(html_module.unescape(price.group(1)))
        else:
            entries = (clean(re.sub(r"<[^>]+>", " ", html_module.unescape(v))) for v in re.findall(r'data-pv="([^"]*)"', block))
            price_text = " / ".join(v for v in entries if v)
        values = [float(v) for v in re.findall(r"\d{1,4}(?:\.\d{1,2})?", price_text.replace(",", ""))]
        values = [v for v in values if v > 0]
        if not name_text or not values or ADDON_NAME.match(name_text):
            continue
        section = next((title for position, title in reversed(sections) if position < start and title), None)
        items.append({"section": section, "name": name_text, "price_text": price_text, "price": min(values),
                      "price_rule": "lowest" if len(values) > 1 else "single"})
    return [{"name": None, "url": None, "items": items}] if items else []


def toast_menus(html):
    """Menus of a Toast online-ordering page from the page's own data (window.__APOLLO_STATE__ / __OO_STATE__: Menu > groups >
    items with prices), in the same shape as schema_menus. Several prices (sizes) give the lowest ('lowest')."""
    states = []
    for match in re.finditer(r"window\.__(?:APOLLO|OO)_STATE__\s*=\s*", html):
        try:
            states.append(json.JSONDecoder().raw_decode(html, match.end())[0])
        except ValueError:
            continue
    menus, seen = [], set()
    for state in states:
        menus += toast_state_menus(state, seen)
    return menus


def toast_state_menus(state, seen):
    def resolve(node):
        return state.get(node["__ref"], {}) if isinstance(node, dict) and "__ref" in node else node

    def group(node, section, out, depth=0):
        node = resolve(node)
        if not isinstance(node, dict) or depth > 4:
            return
        section = clean(node.get("name")) or section
        for item in node.get("items") or []:
            item = resolve(item)
            if not isinstance(item, dict):
                continue
            prices = sorted(p for p in item.get("prices") or [] if isinstance(p, (int, float)) and not isinstance(p, bool) and p > 0)
            name = clean(item.get("name"))
            if name and prices:
                out.append({"section": section, "name": name, "price_text": " / ".join(f"{p:.2f}" for p in prices), "price": float(prices[0]),
                            "price_rule": "lowest" if len(prices) > 1 else "single"})
        for child in (node.get("subgroups") or []) + (node.get("children") or []):
            group(child, section, out, depth + 1)

    menus = []

    def walk(node, depth=0):
        if depth > 12:
            return
        if isinstance(node, list):
            for child in node:
                walk(child, depth + 1)
        elif isinstance(node, dict):
            if node.get("__typename") == "Menu" and node.get("groups"):
                key = node.get("id") or node.get("guid") or node.get("name")
                if key not in seen:
                    seen.add(key)
                    items = []
                    for child in node["groups"]:
                        group(child, None, items)
                    if items:
                        menus.append({"name": clean(node.get("name")) or None, "url": None, "items": items})
                return
            for child in node.values():
                walk(child, depth + 1)

    walk(state)
    return menus


def hours_text(text):
    """Hours as written for display: comma-separated parts the source left empty are dropped (", Tu 17:00-21:00," -> "Tu 17:00-21:00");
    a text with no part left is empty."""
    return ", ".join(part.strip() for part in (text or "").split(",") if part.strip())


def schema_hours(objects):
    """{day index: 'HH:MM–HH:MM' or 'kapalı'} and the verbatim text from openingHoursSpecification / openingHours."""
    days, texts = {}, []
    for item in objects:
        for spec in (item.get("openingHoursSpecification") or []) if isinstance(item.get("openingHoursSpecification"), list) else \
                ([item["openingHoursSpecification"]] if isinstance(item.get("openingHoursSpecification"), dict) else []):
            if not isinstance(spec, dict):
                continue
            names = spec.get("dayOfWeek")
            names = names if isinstance(names, list) else [names]
            opens, closes = clean(str(spec.get("opens") or "")), clean(str(spec.get("closes") or ""))
            for name in names:
                day = SCHEMA_DAYS.get(clean(str(name)).rsplit("/", 1)[-1].lower())
                if day is not None and opens and closes:
                    span = f"{opens[:5]}–{closes[:5]}"
                    days[day] = f"{days[day]}, {span}" if day in days and span not in days[day] else span
            texts.append(hours_text(f"{', '.join(clean(str(n)).rsplit('/', 1)[-1] for n in names)} {opens}–{closes}"))
        hours = item.get("openingHours")
        for entry in hours if isinstance(hours, list) else ([hours] if isinstance(hours, str) else []):
            texts.append(hours_text(clean(entry)))
            parsed = parse_hours_text(entry)
            for day, value in parsed.items():
                days.setdefault(day, value)
    return days, " · ".join(t for t in texts if t)


TIME = r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?\s*m\.?|(\d{1,2}):(\d{2})|\bnoon\b|\bmidnight\b"
DAY_RANGE = re.compile(r"\b(mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday|s)?|thu(?:r(?:s(?:day)?)?)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?|mo|tu|we|th|fr|sa|su)\b"
                       r"(?:\s*(?:-|–|—|to|through|thru)\s*\b(mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday|s)?|thu(?:r(?:s(?:day)?)?)?|fri(?:day)?|sat(?:urday)?|"
                       r"sun(?:day)?|mo|tu|we|th|fr|sa|su)\b)?", re.I)


def clock(match):
    text = match.group(0).lower()
    if "noon" in text:
        return "12:00"
    if "midnight" in text:
        return "24:00"
    if match.group(1):
        hour, minute, half = int(match.group(1)), int(match.group(2) or 0), match.group(3).lower()
        if hour > 12 or minute > 59:
            return None
        hour = hour % 12 + (12 if half == "p" else 0)
        return f"{hour:02d}:{minute:02d}"
    hour, minute = int(match.group(4)), int(match.group(5))
    return f"{hour:02d}:{minute:02d}" if hour <= 24 and minute <= 59 else None


def parse_hours_text(text):
    """'Mon-Thu 11am-9pm, Fri & Sat 11am - 10pm, Sun Closed' -> {0: '11:00–21:00', ..., 6: 'kapalı'}; {} when not readable."""
    result = {}
    source = clean(text).replace("&", ",")
    if re.search(r"\b(?:open )?daily\b|\bevery ?day\b|\b7 days\b", source, re.I) and not DAY_RANGE.search(source):
        times = [clock(m) for m in re.finditer(TIME, source, re.I)]
        times = [t for t in times if t]
        if len(times) >= 2:
            return {day: f"{times[0]}–{times[1]}" for day in range(7)}
    matches = list(DAY_RANGE.finditer(source))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        segment = source[match.end():end]
        first = DAY_NAMES[match.group(1).lower()]
        last = DAY_NAMES[match.group(2).lower()] if match.group(2) else first
        span = list(range(first, last + 1)) if last >= first else list(range(first, 7)) + list(range(0, last + 1))
        if re.search(r"\bclosed\b", segment, re.I):
            value = "kapalı"
        else:
            times = [t for t in (clock(m) for m in re.finditer(TIME, segment, re.I)) if t]
            if len(times) < 2:
                # a list such as "Mon, Tue: 5pm-9pm" shares the next segment's hours
                continue
            value = ", ".join(f"{times[i]}–{times[i + 1]}" for i in range(0, len(times) - 1, 2))
        for day in span:
            result.setdefault(day, value)
        # days listed just before this one without their own times take the same hours ("Mon, Tue 5pm-9pm")
        back = index - 1
        while back >= 0 and not re.search(TIME + r"|closed", source[matches[back].end():matches[back + 1].start()], re.I):
            first_b = DAY_NAMES[matches[back].group(1).lower()]
            last_b = DAY_NAMES[matches[back].group(2).lower()] if matches[back].group(2) else first_b
            for day in range(first_b, last_b + 1):
                result.setdefault(day, value)
            back -= 1
    return result


def hours_from_lines(lines):
    """The verbatim hours text a page shows near an 'Hours' heading or line, and its per-day reading."""
    for index, (kind, line) in enumerate(lines):
        if not re.search(r"\bhours\b|\bopen daily\b|\bhours of operation\b", line, re.I) or len(line) > 160:
            continue
        block = []
        if re.search(TIME, line, re.I) and DAY_RANGE.search(line) or re.search(r"open daily", line, re.I) and re.search(TIME, line, re.I):
            block.append(line)
        for _, follow in lines[index + 1:index + 12]:
            if (DAY_RANGE.search(follow) or re.search(r"\bdaily\b|\bclosed\b|\bseason", follow, re.I) or re.search(TIME, follow, re.I)) and len(follow) <= 120:
                block.append(follow)
            elif block:
                break
        if block:
            text = " · ".join(block)
            return text, parse_hours_text(text)
    return None, {}


# --- Menus -----------------------------------------------------------------------------------------------------------------

PRICE_TOKEN = r"\$?\s?\d{1,3}(?:\.\d{1,2})?"
ITEM_LINE = re.compile(r"^(?P<name>(?:[A-Za-z\"'(¡¿#&½“‘]|\d+(?:/\d+)?\s?(?:oz|lb|pc|piece|dozen|doz)?\.?\s?[A-Za-z])[^$]{1,90}?)\s*(?:[.\-–—…·:|]{2,}\s*|\s[-–—|:]\s|\s)"
                       r"(?P<prices>\$?\s?\d{1,3}(?:\.\d{1,2})?(?:\s*(?:/|\||or|,|-)\s*\$?\s?\d{1,3}(?:\.\d{1,2})?){0,3}\+?)\s*$")
PRICE_ONLY = re.compile(r"^(?:[A-Za-z ]{0,12}\s)?\$?\s?\d{1,3}(?:\.\d{1,2})?(?:\s*(?:/|\||or|,|-)\s*(?:[A-Za-z ]{0,12}\s)?\$?\s?\d{1,3}(?:\.\d{1,2})?){0,3}\+?$")
SIZE_PRICES = re.compile(r"^(?P<name>.+?)\s+(?P<sizes>(?:(?:cup|bowl|half|full|small|large|reg(?:ular)?|single|double|glass|bottle|\d+\s?(?:pc|oz|piece|ct)s?|"
                         r"6\"|12\"|8\"|10\"|14\"|16\")\s*\$?\s?\d{1,3}(?:\.\d{1,2})?\s*[/|,]?\s*){2,})$", re.I)
MARKET = re.compile(r"\b(?:market price|mkt\.?|mp|m\.p\.|market)\s*$", re.I)
NOT_PRICE_UNIT = re.compile(r"\d\s*(?:oz|lb|lbs|pc|pcs|pieces?|ct|count|inch|in\.|\"|%|am|pm|a\.m|p\.m|calories|cal|years?|yrs?|ft|miles?)\b", re.I)
SKIP_NAME = re.compile(r"^(?:\*|(?:may )?contains?\b|gluten[- ]free (?:buns?|bread|crust|option)|add|sub|substitute|make it|upgrade|\+|with|w/|extra|choice of|choose|served|includes?|gratuity|tax|price|prices|"
                       r"(?:your )?cart|skip to (?:main )?content|check (?:gift card )?balance|suite|ste\.?|"
                       r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\.?|\d+\s+(?:reviews?|likes?|ratings?))\b|"
                       r"^.*\b(?:county (?:hwy|highway|road)|hwy 30a|highway 30a)\b|"     # an address line is not a dish
                       r"^(?:dinner|lunch|brunch|breakfast|kids|dessert|drinks?|happy hour|bar|wine)\s+menu$", re.I)    # nor a menu's title
PHONE = re.compile(r"\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}")
# Buttons and counters menu platforms print between dishes ("1 likes", "Order Online", "0 0 0").
NOISE = re.compile(r"^(?:\d+\s+(?:likes?|reviews?|ratings?)|\d+(?:\s+\d+)+|order online|order now|add to (?:cart|order|bag)|view details|completed loading.*|"
                   r"n/a|sold out|popular|new|gluten[- ]free|gf|v|vg|df)$", re.I)
NUTRITION = re.compile(r"nutrition(?:al)? (?:information|facts)|total fat \(g\)|sodium \(mg\)|calories\s+total fat", re.I)
NAME_DASH = re.compile(r"^([A-Z][^-–—,]{1,60}?)\*?\s+[-–—]\s+\S")
MIXED_HEADING = re.compile(r"^[A-Z][A-Z'’&]+(?: [A-Z'’&]+)*(?: [a-z][a-z'’&+]*)+$")
TWIN_PRICE = re.compile(r"\$(\d{1,3}(?:\.\d{2})?)\s+\$\1(?=\s|$)")


def same_page(first, second):
    """The same page: scheme, 'www.', a trailing slash and the fragment do not matter; the query does."""
    def key(url):
        parts = urlsplit((url or "").strip())
        return (parts.netloc.lower().removeprefix("www."), parts.path.rstrip("/").lower(), parts.query)
    return bool(first and second) and key(first) == key(second)


def flat(text):
    import unicodedata
    text = unicodedata.normalize("NFKD", html_module.unescape(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def shown(text, name, price_text, window=240):
    """True when the page text shows the item's name and, near it (before or after), its price as read."""
    body, needle, price = flat(text), flat(name), flat(price_text)
    if not needle:
        return False
    start = body.find(needle)
    while start >= 0:
        if not price or price in body[max(0, start - window):start + len(needle) + window]:
            return True
        start = body.find(needle, start + 1)
    return False


def money_values(text):
    return [float(v) for v in re.findall(r"(\d{1,3}(?:\.\d{1,2})?)", text.replace("$", " "))]


def looks_like_description(line):
    """Ingredient or description lines: long, several commas, or starting in lowercase (dish names start with a capital)."""
    return len(line) > 70 or line.count(",") >= 2 or line[:1].islower() or ("," in line and len(line) > 30)


def heading_like(line):
    letters = re.sub(r"[^A-Za-z]", "", line)
    return 2 <= len(line) <= 40 and letters and letters.isupper() and not re.search(r"\d{2,}", line)


def menu_line(line):
    """A menu line with dot leaders, price asterisks and a price glued to the last word normalized: 'Feta15 ......' -> 'Feta 15'."""
    text = clean(line).replace("…", "...")
    text = re.sub(r"[\s.·_]{3,}$", "", text)
    text = re.sub(r"\s*[.·_]{3,}\s*", "  ", text)
    text = re.sub(r"(\d|\bMKT|\bMP)\*+$", r"\1", text, flags=re.I)
    text = re.sub(r"([A-Za-z\)])(\d{1,3}(?:\.\d{2})?)$", r"\1 \2", text)
    text = re.sub(r"(\$\s?\d{1,3}),(\d{2})\b", r"\1.\2", text)      # "$11,00": a price the browser wrote with a decimal comma
    if re.search(r"(?:\d|\bMKT|\bMP)\s*$", text, re.I):
        text = re.sub(r"^\*+\s*(?=[A-Za-z\"'“‘(])", "", text)     # "*Simply Grilled Grouper 38": the mark of a raw / gluten-free dish
    return clean(text)


def parse_menu(lines, known=None):
    """Menu items from text lines: [{'section', 'name', 'price_text', 'price', 'price_rule'}]. Several sizes or portions: the lowest
    price is used ('lowest'); 'market price' keeps its text and no number ('market'). A line that is only a description with the
    price at its end takes the short name line above it as the item name. A heading directly followed by its price (sites that
    write each dish name as a heading) is an item of the section above it, not a new section, unless known(heading) says it is a
    section heading of the reviewed table ("SEAFOOD DINNERS" followed by "MKT" on menus that print the price before the name)."""
    items, section, pending, headed = [], None, None, None

    def emit(name, price_text, values, *, market=False, under=None):
        nonlocal pending, headed, section
        if headed is not None and under is headed:
            section = headed[1]                   # the heading was a dish name: its section is the one above
        if (not market and min(values) < 1.5) or "$" in name or SKIP_NAME.match(name) or re.fullmatch(r"[\d\W]+", name):
            pending, headed = None, None                  # "$0.00" / "1": a cart, a counter or an add-on; "Cup $11 Bowl $14": a price line
            return
        items.append({"section": section, "name": name, "price_text": price_text, "price": None if market else min(values),
                      "price_rule": "market" if market else ("lowest" if len(values) > 1 else "single")})
        pending, headed = None, None

    if NUTRITION.search(" ".join(t for _, t in lines[:400])):
        return []                                 # a nutrition table (calories, fat, sodium per dish): its numbers are not prices
    for kind, line in lines:
        text = menu_line(line)
        if not text or text in ("$", "USD") or NOISE.match(text) or len(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", text)) >= 6:
            continue                              # a table row of many numbers is not a dish with its price
        twin = TWIN_PRICE.search(text)
        if twin and kind != "h":
            text = f"${twin.group(1)}"            # "...lime juice$12 $12 Mashed avocado..." (description, price, description again)
        if (kind == "h" or heading_like(text) and not ITEM_LINE.match(text) and not MARKET.search(text)
                or known and MIXED_HEADING.match(text) and known(text)):          # "TO FEAST large plates"
            if ADDON_NAME.match(text) and re.search(r"\+\s?\$?\d", text):
                continue                          # "ADD EGG +2 | ADD PORK BELLY +4": the section's add-on prices, not a new section
            if SKIP_NAME.match(text) and not ADDON_NAME.match(text):
                continue                          # "SERVED WITH A CHOICE OF ONE SIDE": a note in capitals, not a new section
            # an add-on heading without prices ("ADD-ONS", "EXTRAS") is a section: its items are add-ons, never mains
            if len(text) <= 60 and not PHONE.search(text):
                headed = (text, section)
                section, pending = text, None
            continue
        if PHONE.search(text) or re.search(r"\b\d{1,2}(?::\d{2})?\s*[ap]\.?m\b", text, re.I) and not re.search(r"\$", text):
            pending = None if pending and not looks_like_description(pending) else pending
            continue
        if pending and not looks_like_description(pending):
            name_above, under_h = pending, None
        elif pending and NAME_DASH.match(pending):
            # "BEC* - Benton's Bacon, Egg, Cheddar Cheese" with the price on the next line: the name is before the dash
            name_above, under_h = NAME_DASH.match(pending).group(1).rstrip("* "), None
        elif headed and not (known and known(headed[0])):
            name_above, under_h = headed[0], headed
        else:
            name_above, under_h = None, None
        market = MARKET.search(text)
        if market and len(text) - len(market.group(0)) > 2:
            name = clean(text[:market.start()]).rstrip(".-–—…·:| ")
            if name_above and (looks_like_description(name) or "," in name):
                emit(name_above, market.group(0).strip(), [], market=True, under=under_h)
            elif name and not SKIP_NAME.match(name):
                emit(name, market.group(0).strip(), [], market=True)
            continue
        sized = SIZE_PRICES.match(text)
        if sized and not SKIP_NAME.match(sized.group("name")):
            values = money_values(re.sub(r"\d+\s?(?:pc|oz|piece|ct)s?|\d+\"", " ", sized.group("sizes"), flags=re.I))
            if values:
                emit(clean(sized.group("name")), clean(sized.group("sizes")), values)
                continue
        item = ITEM_LINE.match(text)
        if item and not NOT_PRICE_UNIT.search(text[item.start("prices") - 1:]) and not SKIP_NAME.match(item.group("name")):
            values = money_values(item.group("prices"))
            name = clean(item.group("name")).rstrip(".-–—…·:| ")
            under = None
            if name_above and (looks_like_description(name) or "," in name):
                under, name = under_h, name_above                 # "Arugula*" / "E.V.O.O., Fresh Lemon, Shaved Pecorino 14"
            if values and name and not re.fullmatch(r"[\d\W]+", name):
                emit(name, clean(item.group("prices")), values, under=under)
                continue
        label = re.sub(r"[\d$.,/|\s+-]+$", "", text).strip()
        if PRICE_ONLY.match(text) and label and SKIP_NAME.match(label):
            continue                              # "DINNER MENU 23": a menu title with a stray number
        if PRICE_ONLY.match(text) and not NOT_PRICE_UNIT.search(text):
            values = money_values(text)
            if values and name_above:
                emit(name_above, text, values, under=under_h)
            else:
                pending = None
            continue
        if MARKET.fullmatch(text):
            if name_above:
                emit(name_above, text, [], market=True, under=under_h)
            continue                              # a lone "MKT" printed before its dish name is not a name
        if SKIP_NAME.match(text):
            continue
        if not looks_like_description(text):
            headed = None                         # a plain name line after the heading: the heading was a section
        if pending is None or (looks_like_description(pending) and not looks_like_description(text)):
            pending = text if len(text) <= 90 else None
    return items


def load_sections(path=SECTIONS_TABLE):
    """(pattern, class, exact) rows of the reviewed table, in order; an exact row applies only when it is the whole heading."""
    with open(path, encoding="utf-8") as handle:
        rows = [(row["kalip"].strip().lower(), row["sinif"].strip(), (row.get("tam") or "").strip() == "1") for row in csv.DictReader(handle)
                if row["kalip"].strip()]
    unknown = {kind for _, kind, _ in rows} - set(SECTION_CLASSES)
    if unknown:
        raise SourceError(f"Menü bölüm tablosunda bilinmeyen sınıf: {', '.join(sorted(unknown))}.")
    return rows


def heading_text(section):
    """A heading as plain lowercase words: accents dropped, letter-spaced words joined ('R E D W I N E' -> 'redwine')."""
    import unicodedata
    text = re.sub(r"['’‘`´]", "", clean(section))            # "CHEF’S FEATURE" and "chef's feature" are the same words
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower().replace("&", " & ")
    if re.fullmatch(r"(?:[a-z0-9] ){2,}[a-z0-9](?: .*)?", text):
        text = re.sub(r"\b([a-z0-9]) (?=[a-z0-9]\b)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip(" :")


def classify(section, table):
    """The class of a menu section heading by the reviewed table: first row whose pattern appears as whole words (after
    heading_text); 'diger' otherwise."""
    if not section:
        return "diger"
    heading = heading_text(section)
    spaced = re.fullmatch(r"(?:[A-Za-z0-9] ){2,}[A-Za-z0-9].*", clean(section)) is not None      # letter-spaced: words ran together
    for row in table:
        pattern, kind, exact = row if len(row) == 3 else (*row, False)
        plain = heading_text(pattern)
        if exact:
            if heading == plain or heading.replace(" ", "") == plain.replace(" ", ""):
                return kind
            continue
        if re.search(r"(?<![a-z])" + re.escape(plain) + r"(?![a-z])", heading):
            return kind
        if spaced and len(plain) >= 3 and plain.replace(" ", "") in heading.replace(" ", ""):
            return kind
    return "diger"


def item_class(item, kind, table, reviewed=None):
    """(class, basis) of a menu item: a reviewer's class for this item of this restaurant ('review'); an add-on, extra, topping,
    sauce or side by its name ('add …', '+ …', 'sub …', 'side of …', 'additional topping') is 'yan_urun', a drink by its name
    'icecek' and a kids' item by its name 'cocuk' ('name'); otherwise its section heading by the table ('section'); when the heading
    gives no class (no heading, or one the table does not know), the item's own name by the same table ('name'). Items of a kids
    menu are 'cocuk'; items of a drinks menu that neither heading nor name classifies are 'icecek'."""
    name = clean(item.get("name") or "")
    if reviewed and (name, clean(item.get("price_text") or "")) in reviewed:
        return reviewed[(name, clean(item.get("price_text") or ""))], "review"
    if reviewed and (name, "") in reviewed:
        return reviewed[(name, "")], "review"
    if ADDON_NAME.search(name) and (ADDON_NAME.match(name) or (item.get("price") or 0) < 8):
        return "yan_urun", "name"
    if DRINK_NAME.match(name):
        return "icecek", "name"
    if KIDS_NAME.match(name):
        return "cocuk", "name"
    if ADDON_NAME.match(clean(item.get("section") or "")):
        return "yan_urun", "section"                  # items under "Add Protein", "Extras" …
    klass, basis = classify(item.get("section"), table), "section"
    if klass == "diger":
        by_name = classify(item.get("name"), [row for row in table if not (len(row) == 3 and row[2])])
        if by_name != "diger":
            klass, basis = by_name, "name"
    if kind == "kids" and klass in ("ana_yemek", "diger"):
        klass, basis = "cocuk", "menu"
    elif kind == "drinks" and klass == "diger":
        klass, basis = "icecek", "menu"
    return klass, basis


def menu_type(*texts):
    joined = " ".join(t for t in texts if t)
    for kind, pattern in TYPE_WORDS:
        if re.search(pattern, joined, re.I):
            return kind
    return "general"


def pdf_lines(body):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(body))
    lines = []
    for page in reader.pages[:12]:
        try:
            text = page.extract_text() or ""
        except Exception:
            continue
        for raw in text.splitlines():
            line = clean(raw)
            if line:
                lines.append(("p", line))
    return lines


def main_stats(items, klass="ana_yemek"):
    """Count, median, lowest and highest of the main-dish prices (section class ana_yemek, a number); another class with klass."""
    prices = sorted(i["price"] for i in items if i.get("section_class") == klass and i.get("price") is not None and i["price"] > 0)
    if not prices:
        return {"count": 0, "median": None, "min": None, "max": None}
    return {"count": len(prices), "median": round(statistics.median(prices), 2), "min": prices[0], "max": prices[-1]}


def price_level(stats):
    """Our classification of the main-dish median: under $15 '$', $15–25 '$$', $25–40 '$$$', $40 and over '$$$$'; None under 5 prices."""
    if stats["count"] < MIN_MAIN_PRICES or stats["median"] is None:
        return None
    return next(level for limit, level in PRICE_LEVELS if stats["median"] < limit)


# --- One restaurant --------------------------------------------------------------------------------------------------------

def same_business(text, restaurant):
    """True when the page names the restaurant (its name words) or shows its phone number."""
    digits = re.sub(r"\D", "", restaurant.get("phone") or "")[-10:]
    if digits and digits in re.sub(r"\D", "", text):
        return True
    words = [w for w in re.findall(r"[a-z0-9]+", clean(restaurant["name"]).lower().replace("&", " ")) if w not in
             ("the", "and", "of", "at", "on", "a", "restaurant", "cafe", "café", "bar", "grill", "kitchen", "30a")]
    flat = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return bool(words) and all(re.search(r"\b" + re.escape(w) + r"\b", flat) for w in words[:3])


class RestaurantRun:
    def __init__(self, fetcher, restaurant, override, readings, sections, item_reviews=None):
        self.fetcher, self.restaurant, self.override, self.readings, self.sections = fetcher, restaurant, override, readings, sections
        self.item_reviews = item_reviews or {}     # {(item name, price text or ""): class} a reviewer set for this restaurant
        self.site = {"external_id": restaurant["external_id"], "name": restaurant["name"], "site_url": None, "site_source": "none",
                     "site_status": "no_site", "final_url": None, "http_status": None, "status_note": None, "fetched_at": None,
                     "raw_sha256": None, "page_count": 0}
        self.facts, self.menus, self.items = {}, [], []
        self.read_pages = []           # (document, lines) of every HTML page read for this restaurant
        self.schema_menus = []         # menu urls the structured data names
        self.needs_browser = None      # 'challenge' (verification page) or 'refused' (plain HTTP refused): the blocked host in a browser
        self.blocked_hosts = {}        # host -> {'reason', 'url'}: answered plain HTTP with a verification page or a refusal
        self.js_menus = False
        self.challenged = []           # (host, url) of a menu or info page that kept its verification page (the restaurant goes on)
        self.seen_schema = set()       # structured-data menus already recorded (the same menu is published on several pages)

    def get(self, url, note):
        document = self.fetcher.get(url, restaurant=self.restaurant["external_id"], note=note)
        self.site["page_count"] += 1
        return document

    def note_block(self, document):
        """A page whose host answered plain HTTP with a verification page or a refusal: only that host is read with the browser in
        the second pass (the browser is used only where a site blocks plain requests). True when the page was such a block."""
        if document.status in (403, 429, 503) and document.kind == "html" and CHALLENGE.search(document.text[:40000]):
            reason = "challenge"
        elif document.status in (403, 429):
            reason = "refused"
        else:
            return False
        for url in {document.url, document.final_url} - {None}:
            self.blocked_hosts.setdefault(host_key(url), {"reason": reason, "url": url})
        self.needs_browser = self.needs_browser or reason
        return True

    def fact(self, field, value, document, method, *, detail=None, link_url=None, data=None, replace=False):
        if field in self.facts and not replace:
            return
        self.facts[field] = {"field": field, "value": value, "detail": detail, "link_url": link_url, "data": data,
                             "source_url": document.final_url, "fetched_at": document.fetched_at, "raw_sha256": document.sha256, "method": method}

    def run(self):
        restaurant = self.restaurant
        url = (self.override or {}).get("site_url") or restaurant.get("website_url")
        if not url:
            self.site["status_note"] = "Dizinde web sitesi yok ve gözden geçirilmiş bir resmî site kaydı yok."
            return self
        self.site.update({"site_url": url, "site_source": "review" if (self.override or {}).get("site_url") else "directory"})
        try:
            home = self.get(url, "site-home")
        except (httpx.HTTPError, SourceError) as exc:
            self.site.update({"site_status": "unreachable", "status_note": f"Siteye ulaşılamadı: {type(exc).__name__}"})
            if isinstance(exc, httpx.RemoteProtocolError):
                # the server dropped the plain request without an answer (seen on Cloudflare sites that let a browser in): a block
                self.blocked_hosts.setdefault(host_key(url), {"reason": "refused", "url": url})
                self.needs_browser = self.needs_browser or "refused"
            return self
        self.site.update({"final_url": home.final_url, "http_status": home.status, "fetched_at": home.fetched_at, "raw_sha256": home.sha256})
        if on_host(home.final_url, SOCIAL_HOSTS):
            self.site.update({"site_status": "social_login", "status_note": "Sosyal medya sayfası; giriş yapmadan içerik okunmadı."})
            return self
        moved = None
        root = f"{urlsplit(home.final_url).scheme}://{urlsplit(home.final_url).netloc}/"
        if home.status in (404, 410) and urlsplit(home.final_url).path not in ("", "/"):
            try:
                again = self.get(root, "site-home")
            except (httpx.HTTPError, SourceError):
                again = None
            if again is not None and again.status == 200 and again.kind == "html":
                moved, home = home, again             # the directory's page is gone; the site itself answers
                self.site.update({"final_url": home.final_url, "http_status": home.status, "fetched_at": home.fetched_at, "raw_sha256": home.sha256})
        if home.status in (404, 410):
            self.site.update({"site_status": "not_found", "status_note": f"Site HTTP {home.status} döndü."})
            return self
        if home.status != 200 or home.kind != "html":
            challenged = home.status in (403, 429, 503) and CHALLENGE.search(home.text[:40000] if home.kind == "html" else "")
            self.site.update({"site_status": "unreachable", "status_note": (f"Site düz HTTP isteğine doğrulama sayfası gösterdi (HTTP {home.status})."
                              if challenged else f"Site HTTP {home.status} ({home.content_type}) döndü.")})
            self.note_block(home)                      # a real browser may be let in where a plain request was blocked
            return self
        html = home.text
        frame = re.search(r'(?is)<frameset\b.*?<frame\b[^>]*?\bsrc\s*=\s*["\']([^"\']+)["\']', html)
        if frame and len(clean(re.sub(r"<[^>]+>", " ", html))) < 400:
            # the domain only frames the real site (an old forwarding page): the framed site is the restaurant's site
            try:
                framed = self.get(urljoin(home.final_url, html_module.unescape(frame.group(1))), "site-home")
            except (httpx.HTTPError, SourceError):
                framed = None
            if framed is not None and framed.status == 200 and framed.kind == "html":
                home = framed
                html = home.text
                self.site.update({"final_url": home.final_url, "http_status": home.status, "fetched_at": home.fetched_at, "raw_sha256": home.sha256})
        lines = html_lines(html)
        flat = " ".join(t for _, t in lines)
        if PARKED.search(flat) or PARKED.search(page_title(html)) or PARKING_SCRIPT.search(html[:60000]):
            self.site.update({"site_status": "other_business", "status_note": "Alan adı satılık / park edilmiş sayfa."})
            return self
        notes = []
        if moved is not None:
            notes.append(f"Dizindeki sayfa bulunamadı (HTTP {moved.status}: {moved.final_url}); sitenin ana sayfası okundu.")
        if not same_business(page_title(html) + " " + flat, restaurant):
            notes.append("Ana sayfada işletmenin adı ya da telefonu görünmedi; site yine de okundu.")
        self.site["status_note"] = " ".join(notes) or None
        self.site["site_status"] = "working"
        self.read_pages.append((home, lines))
        self.structured(home, html)
        self.structured_menus(home, html, home)
        found = links(html, home.final_url) + self.schema_menus + embedded_menus(html, home.final_url)
        if platform_of(home.final_url, MENU_PLATFORMS):
            found = [("menu", home.final_url)] + found        # the site is an ordering page: the page itself is the menu
        menu_targets, info_targets = self.targets(found, home.final_url)
        reviewed = [u.strip() for u in ((self.override or {}).get("menu_urls") or "").split(";") if u.strip()]
        menu_targets = [("gözden geçirilmiş menü bağlantısı", u) for u in reviewed] + [t for t in menu_targets if t[1] not in reviewed]
        for label, target in info_targets[:MAX_INFO_PAGES]:
            try:
                page = self.get(target, "site-info")
            except (httpx.HTTPError, SourceError):
                continue
            except VerificationDeferred as wait:
                self.challenged.append((wait.host, wait.url))
                continue
            if page.status == 200 and page.kind == "html":
                self.read_pages.append((page, html_lines(page.text)))
                self.structured(page, page.text)
                self.structured_menus(page, page.text, home)
            else:
                self.note_block(page)
        self.read_menus(menu_targets, home)
        self.text_facts()
        if (not self.needs_browser and not any(m["status"] == "read" for m in self.menus)
                and (self.js_menus or any(m["status"] == "no_items" and m["platform"] for m in self.menus) or not self.menus and len(flat) < 600)):
            # the menu is probably drawn with JavaScript; the browser is used only where a site blocks plain requests (user decision,
            # 9 October 2026), so it stays unread and the note says why
            self.site["status_note"] = (f"{self.site['status_note'] or ''} Menü fiyatları sayfanın düz HTML'inde yok (JavaScript ile "
                                        "çiziliyor olabilir); tarayıcı yalnız engel olduğunda kullanıldığı için tarayıcıyla okunmadı.").strip()
        return self

    def targets(self, found, base):
        site = host_of(base)
        menus, infos, seen = [], [], set()
        for label, target in found:
            key = target.split("#")[0]
            if key in seen:
                continue
            path = urlsplit(target).path.lower()
            platform = platform_of(target, MENU_PLATFORMS)
            reservation = platform_of(target, RESERVATION_PLATFORMS)
            if reservation:
                continue
            if platform and urlsplit(target).path.strip("/") == "" and not urlsplit(target).netloc.lower().removeprefix("www.").count(".") > 1:
                continue                          # "powered by" credit to the platform's own home page, not a menu
            if NOT_MENU_PAGE.search(urlsplit(target).path + "?" + urlsplit(target).query) or host_of(target) == "pos.toasttab.com":
                continue                          # one dish of an ordering menu, or the platform's legal pages
            same_site = host_of(target) == site
            is_doc = re.search(r"\.(pdf|jpe?g|png|webp)$", path)
            menu_like = MENU_WORD.search(label) or re.search(r"menu|dinner|lunch|brunch|breakfast|kids|drink|cocktail|dessert|happy-hour|\bfood\b|\beats?\b", path)
            if platform or (menu_like and (same_site or is_doc)) or (is_doc and re.search(r"menu", path + " " + label, re.I)):
                if re.search(r"/(?:cart|checkout|account|login|signin|gift|careers?|jobs)\b", path):
                    continue
                seen.add(key)
                menus.append((label, target))
            elif same_site and INFO_WORD.search(label + " " + path) and not is_doc:
                seen.add(key)
                infos.append((label, target))
        menus.sort(key=lambda lt: (0 if re.search(r"dinner|lunch|menu", lt[0] + lt[1], re.I) else 1))
        return menus, infos

    def read_menus(self, targets, home):
        queue, seen, documents, fetched = list(targets), set(), set(), 0
        while queue and fetched < MAX_DOCUMENTS:
            label, target = queue.pop(0)
            key = target.split("#")[0]
            if key in seen:
                continue
            seen.add(key)
            fetched += 1
            try:
                document = self.get(target, "menu")
            except (httpx.HTTPError, SourceError) as exc:
                self.add_menu(target, label, home, None, "error", f"Okunamadı: {type(exc).__name__}")
                continue
            except VerificationDeferred as wait:
                # only the restaurant's own home page waits for the user; a menu or ordering page that keeps its check is left unread
                self.challenged.append((wait.host, wait.url))
                self.add_menu(target, label, home, None, "error", f"Sayfa doğrulama istedi ({wait.host}); okunmadı.")
                continue
            if document.sha256 in documents or document.final_url.split("#")[0] in seen and document.final_url.split("#")[0] != key:
                continue                          # the same document under another link
            documents.add(document.sha256)
            seen.add(document.final_url.split("#")[0])
            if document.status != 200:
                blocked = self.note_block(document)
                self.add_menu(target, label, home, document, "error", f"HTTP {document.status}" +
                              (f" ({host_key(document.final_url)} düz isteği engelledi)" if blocked else ""))
                continue
            if document.kind == "html":
                html = document.text
                lines = html_lines(html)
                self.read_pages.append((document, lines))
                self.structured(document, html)
                title = page_title(html)
                platform = platform_of(document.final_url, MENU_PLATFORMS)
                reading = self.reviewed_reading(target, label or title, home, document, " ".join(t for _, t in lines), "html")
                queue.extend((label or "gömülü menü", url) for _, url in embedded_menus(html, document.final_url) if url.split("#")[0] not in seen)
                if reading is True or self.structured_menus(document, html, home, label=label):
                    continue                          # a person's reading of this page, or the menus it publishes as structured data
                tabs = [(name, parse_menu(html_lines(part), self.known_heading)) for name, part in tab_panels(html)]
                if any(found for _, found in tabs):
                    for name, found in tabs:          # menus shown in tabs: each tab is a menu of its own
                        if found:
                            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                            self.add_menu(target, name, home, document, "read", reading, items=found, platform=platform,
                                          method="platform verisi" if platform else "sayfa metni", title=title, menu_kind=menu_type(name),
                                          url=f"{document.final_url.split('#')[0]}#{slug}")
                    continue
                items = parse_menu(lines, self.known_heading)
                if items:
                    self.add_menu(target, label or title, home, document, "read", reading, items=items, platform=platform,
                                  method="platform verisi" if platform else "sayfa metni", title=title)
                elif not platform:
                    # a menu hub page: its own menu links (same site, documents or platforms) are read next
                    _, more = None, [(l, t) for l, t in links(html, document.final_url)
                                     if (MENU_WORD.search(l) or re.search(r"\.pdf$|\.(jpe?g|png)$|menu", t, re.I)) and t.split("#")[0] not in seen]
                    sub, _ = self.targets(more, document.final_url)
                    images = self.menu_images(html, document.final_url)
                    if sub or images:
                        queue.extend(sub + [(l, t) for l, t in images if t.split("#")[0] not in seen])
                        continue
                    self.add_menu(target, label or title, home, document, "no_items", "Sayfada fiyatlı menü kalemi bulunamadı.", title=title)
                    if len(" ".join(t for _, t in lines)) < 1500 or JS_BUILT.search(html):
                        self.js_menus = True          # a menu page with little text: probably drawn by JavaScript
                else:
                    self.add_menu(target, label or title, home, document, "no_items",
                                  "Platform sayfası tarayıcı çalıştırmadan fiyat göstermiyor.", platform=platform, title=title)
            elif document.kind == "pdf":
                try:
                    lines = pdf_lines(document.body)
                except Exception as exc:
                    self.add_menu(target, label, home, document, "error", f"PDF açılamadı: {type(exc).__name__}", fmt="pdf")
                    continue
                text = " ".join(t for _, t in lines)
                reading = self.reviewed_reading(target, label, home, document, text, "pdf")
                if reading is True:
                    continue
                items = parse_menu(lines, self.known_heading)
                if items:
                    self.add_menu(target, label, home, document, "read", reading, items=items, method="PDF metni", fmt="pdf",
                                  text=" ".join(t for _, t in lines[:40]))
                elif len(text) >= 200 and not any(r["raw_sha256"] == document.sha256 for r in self.readings):
                    # the PDF has a text layer but no prices in it: there is nothing for a reader to add
                    self.add_menu(target, label, home, document, "no_items", "PDF metninde fiyatlı menü kalemi bulunamadı.", method="PDF metni",
                                  fmt="pdf", text=text[:400])
                else:
                    self.image_or_unread(target, label, home, document, "pdf")
            elif document.kind == "image":
                self.image_or_unread(target, label, home, document, "image")
            else:
                self.add_menu(target, label, home, document, "error", f"Desteklenmeyen içerik türü: {document.content_type}")

    def known_heading(self, heading):
        """A section heading printed in capitals that the reviewed table knows ("SEAFOOD DINNERS"); a dish name set as a heading
        ("Grilled Grouper") is not one."""
        return bool(heading_like(heading) or MIXED_HEADING.match(heading)) and classify(heading, self.sections) != "diger"

    def structured_menus(self, document, html, home, label=None):
        """The menus a page publishes as schema.org data (Popmenu, Toast and many site builders put the whole menu there). A menu
        seen on several pages of the site is recorded once. True when the page publishes any."""
        found = ([(m, "yapısal veri") for m in schema_menus(html, document.final_url)] + [(m, "platform verisi") for m in toast_menus(html)]
                 + [(m, "platform verisi") for m in mhm_menus(html)] + [(m, "platform verisi") for m in singleplatform_menus(html)])
        title = page_title(html)
        for menu, method in found:
            key = (menu["name"], tuple((i["section"], i["name"], i["price"]) for i in menu["items"]))
            if key in self.seen_schema:
                continue
            self.seen_schema.add(key)
            slug = re.sub(r"[^a-z0-9]+", "-", (menu["name"] or "").lower()).strip("-")
            url = menu["url"] or (f"{document.final_url.split('#')[0]}#{slug}" if len(found) > 1 and slug else document.final_url)
            self.add_menu(url, menu["name"] or label or title, home, document, "read", None, items=menu["items"],
                          platform=platform_of(document.final_url, MENU_PLATFORMS), method=method, url=url,
                          menu_kind=menu_type(menu["name"] or label or title,
                                              urlsplit(url).path.replace("-", " ") + " " + urlsplit(url).fragment.replace("-", " ")))
        return bool(found)

    def reviewed_reading(self, target, label, home, document, text, fmt):
        """A person's reading of this menu page or PDF (reviewed file, method 'elle okundu'), used instead of the parser when it is
        the same document (SHA-256) or the same page whose text in this run still shows every name read with its price.
        True when used; otherwise None, or a note for the parser's menu when the page no longer shows what was read."""
        rows = [r for r in self.readings if (r.get("yontem") or "").strip() == "elle okundu"
                and (r["raw_sha256"] == document.sha256 or same_page(r["menu_url"], document.final_url) or same_page(r["menu_url"], target))]
        if not rows:
            return None
        priced = [r for r in rows if (r.get("name") or "").strip()]
        same = any(r["raw_sha256"] == document.sha256 for r in rows)
        if not same:
            missing = [r for r in priced if not shown(text, r["name"], r["price_text"])]
            if missing:
                return (f"Elle okuma ({rows[0]['okundu']}) bu çekimdeki belgeyle uyuşmadı ({len(missing)}/{len(priced)} kalem sayfada yok); "
                        "ayrıştırıcının okuması kullanıldı.")
        items = [{"section": r["section"] or None, "name": r["name"], "price_text": r["price_text"],
                  "price": float(r["price"]) if r.get("price") not in (None, "") else None,
                  "price_rule": r.get("price_rule") or ("market" if not r.get("price") else "single")} for r in priced]
        note = (f"Elle okundu ({rows[0]['okundu']}); " + ("aynı belge (SHA-256)." if same else
                f"okunan kopya SHA-256 {rows[0]['raw_sha256'][:12]}…; adlar ve fiyatlar bu çekimdeki belgede doğrulandı."))
        self.add_menu(target, label or rows[0].get("menu_title"), home, document, "read" if items else "no_items",
                      note if items else f"{note} Menüde fiyat yazmıyor.", items=items, method="elle okundu", fmt=fmt,
                      menu_kind=rows[0].get("menu_type") or None)
        return True

    def menu_images(self, html, base):
        images = []
        for match in re.finditer(r'(?is)<img\b[^>]*?src\s*=\s*["\']([^"\']+)["\'][^>]*>', html):
            name = urlsplit(urljoin(base, html_module.unescape(match.group(1)))).path.rsplit("/", 1)[-1]
            if (re.search(r"menu", name, re.I) and not re.search(r"logo|icon|favicon|banner", name, re.I)
                    and re.search(r"\.(jpe?g|png|webp)(?:\?|$)", match.group(1), re.I)):
                alt = re.search(r'alt\s*=\s*["\']([^"\']*)', match.group(0), re.I)
                images.append((clean(alt.group(1)) if alt else "menu image", urljoin(base, html_module.unescape(match.group(1)))))
        return images[:4]

    def image_or_unread(self, target, label, home, document, fmt):
        rows = [r for r in self.readings if r["raw_sha256"] == document.sha256]
        if rows and all((r.get("menu_type") or "").strip() == "menü değil" for r in rows):
            return                                # a reviewer saw this image: a photo or a logo, not a menu
        rows = [r for r in rows if (r.get("menu_type") or "").strip() != "menü değil"]
        priced = [r for r in rows if (r.get("name") or "").strip()]
        if priced:
            items = [{"section": r["section"] or None, "name": r["name"], "price_text": r["price_text"],
                      "price": float(r["price"]) if r.get("price") not in (None, "") else None,
                      "price_rule": r.get("price_rule") or ("market" if not r.get("price") else "single")} for r in priced]
            self.add_menu(target, label or rows[0].get("menu_title"), home, document, "read", None, items=items, method="görüntüden okundu",
                          fmt=fmt, menu_kind=rows[0].get("menu_type") or None)
        elif rows:
            # a reviewer read the image: it is a menu, but it prints no prices (a row with an empty name says so)
            self.add_menu(target, label or rows[0].get("menu_title"), home, document, "no_items", "Görüntü okundu; menüde fiyat yazmıyor.",
                          method="görüntüden okundu", fmt=fmt, menu_kind=rows[0].get("menu_type") or None)
        else:
            reason = ("Görüntü menü; gözden geçirme dosyasında bu görüntünün okuması yok." if fmt == "image" else
                      "PDF'te metin yok (taranmış görüntü); gözden geçirme dosyasında okuması yok.")
            self.add_menu(target, label, home, document, "image_unread", reason, fmt=fmt)

    def add_menu(self, target, label, home, document, status, message, *, items=(), platform=None, method=None, fmt=None, title=None, text=None,
                 menu_kind=None, url=None):
        menu_id = len(self.menus) + 1
        kind = menu_kind or menu_type(label, urlsplit(target).path.replace("-", " ").replace("_", " "), title, text if text and len(text) < 400 else None)
        if kind == "drinks" and items:
            # "Oyster Bar Menu", "Food & Drinks": a menu called a drinks menu whose own headings are mostly food is a general menu
            own = [item_class(item, "general", self.sections, self.item_reviews)[0] for item in items]
            if sum(k == "icecek" for k in own) * 2 < len(own) and sum(k in ("ana_yemek", "baslangic", "salata_corba", "kucuk_tabak") for k in own):
                kind = "general"
        if fmt is None:
            fmt = "platform" if platform else (document.kind if document is not None and document.kind in ("html", "pdf", "image") else "html")
        self.menus.append({"menu_id": menu_id, "url": url or (document.final_url if document else target), "format": fmt, "menu_type": kind,
                           "title": clean(label or title or "")[:200] or None, "platform": platform, "linked_from": home.final_url,
                           "fetched_at": document.fetched_at if document else None, "raw_sha256": document.sha256 if document else None,
                           "method": method, "status": status, "message": message, "item_count": len(items)})
        for position, item in enumerate(items, 1):
            section_class, basis = item_class(item, kind, self.sections, self.item_reviews)
            self.items.append({**item, "menu_id": menu_id, "position": position, "section_class": section_class, "class_basis": basis, "method": method})

    def structured(self, document, html):
        objects = json_ld(html)
        if not objects:
            return
        days, text = schema_hours(objects)
        if text:
            self.fact("hours", "stated", document, "yapısal veri", detail=text, data={DAYS[d]: v for d, v in sorted(days.items())} or None)
        for item in objects:
            price = item.get("priceRange")
            if isinstance(price, str) and clean(price):
                self.fact("site_price_range", clean(price), document, "yapısal veri")
            reservations = item.get("acceptsReservations")
            if isinstance(reservations, str) and reservations.startswith("http"):
                platform = platform_of(reservations, RESERVATION_PLATFORMS)
                self.fact("reservation", "online", document, "yapısal veri", detail=platform or "çevrim içi", link_url=reservations)
            elif reservations in (False, "False", "false", "No", "no"):
                self.fact("reservation", "not_taken", document, "yapısal veri", detail="acceptsReservations: false")
            for key in ("hasMenu", "menu"):
                value = item.get(key)
                url = value if isinstance(value, str) else value.get("url") if isinstance(value, dict) else None
                if url and url.startswith("http") and url not in [u for _, u in self.schema_menus]:
                    self.schema_menus.append(("menu", url))

    def text_facts(self):
        """Reservation, kids menu, outdoor seating, water view, dogs and closure from the pages read for this restaurant."""
        for document, lines in self.read_pages:
            text = " ".join(t for _, t in lines)
            if CLOSED_FOR_GOOD.search(text) and self.site["site_status"] == "working":
                self.site.update({"site_status": "closed_permanently", "status_note": f"Site: …{CLOSED_FOR_GOOD.search(text).group(0)}…"})
            elif CLOSED_SEASON.search(text) and self.site["site_status"] == "working":
                self.site.update({"site_status": "closed_season", "status_note": f"Site: …{CLOSED_SEASON.search(text).group(0)}…"})
            for label, target in links(document.text, document.final_url) if document.kind == "html" else ():
                platform = platform_of(target, RESERVATION_PLATFORMS)
                if platform:
                    self.fact("reservation", "online", document, "bağlantı", detail=platform, link_url=target)
            for field, positive, negative in (("outdoor_seating", OUTDOOR, NO_OUTDOOR), ("water_view", WATER_VIEW, None), ("dog_friendly", DOGS, NO_DOGS),
                                              ("kids_menu", KIDS_TEXT, NO_KIDS)):
                if negative is not None and negative.search(text):
                    self.fact(field, "no", document, "sayfa metni", detail=negative.search(text).group(0))
                elif positive.search(text):
                    self.fact(field, "yes", document, "sayfa metni", detail=positive.search(text).group(0))
            if "reservation" not in self.facts:
                for value, pattern in (("waitlist", WAITLIST), ("phone", PHONE_RESERVATIONS), ("not_taken", NO_RESERVATIONS)):
                    match = pattern.search(text)
                    if match:
                        self.fact("reservation", value, document, "sayfa metni", detail=match.group(0))
                        break
            if "hours" not in self.facts:
                verbatim, days = hours_from_lines(lines)
                if verbatim:
                    self.fact("hours", "stated", document, "sayfa metni", detail=verbatim, data={DAYS[d]: v for d, v in sorted(days.items())} or None)
        if "kids_menu" not in self.facts:
            kids = next((m for m in self.menus if m["menu_type"] == "kids"), None) or next(
                (m for m in self.menus if any(i["menu_id"] == m["menu_id"] and i["section_class"] == "cocuk" for i in self.items)), None)
            if kids:
                self.facts["kids_menu"] = {"field": "kids_menu", "value": "yes", "detail": kids["title"] or "çocuk menüsü", "link_url": kids["url"],
                                           "data": None, "source_url": kids["url"], "fetched_at": kids["fetched_at"], "raw_sha256": kids["raw_sha256"],
                                           "method": kids["method"] or "bağlantı"}


# --- Collection --------------------------------------------------------------------------------------------------------------

def read_reviewed(path, key):
    if not path or not Path(path).is_file():
        return {}
    with open(path, encoding="utf-8-sig") as handle:
        rows = [dict(r) for r in csv.DictReader(handle)]
    grouped = {}
    for row in rows:
        grouped.setdefault(row[key], []).append(row)
    return grouped


# The interstitial verification page only. Ordinary pages of Cloudflare sites also load /cdn-cgi/challenge-platform/scripts/jsd/...,
# and contact forms carry a Turnstile box (cf-chl-widget-..., "Verify you are human"); neither is a verification page and neither
# may make the browser pass wait.
CHALLENGE = re.compile(r"<title>\s*Just a moment\.\.\.|cf_chl_opt|/cdn-cgi/challenge-platform/h/[a-z]/orchestrate/|Checking your browser before|"
                       r"Checking if the site connection is secure", re.I)
BLOCKED = re.compile(r"Sorry, you have been blocked|You are unable to access|Attention Required! \| Cloudflare|Edge IP Restricted", re.I)
DOCUMENT_PATH = re.compile(r"\.(?:pdf|jpe?g|png|webp|gif)(?:$|\?)", re.I)
BROWSER_GAP = 3.0               # seconds between two browser page loads on the same host
PROTECTED_GAP = 6.0             # the same on a site that showed a verification page
VERIFY_TIMEOUT = FINAL_WAIT_SECONDS   # the one wait at the end of the run for the sites left for the user (15 min)


class VerificationDeferred(Exception):
    """The page still shows a verification page after the grace period: the restaurant is read again at the end of the run."""

    def __init__(self, host, url):
        super().__init__(host)
        self.host, self.url = host, url


class RoutedPages:
    """The second pass of one restaurant: only hosts that blocked plain HTTP (a verification page or a refusal) are read with the
    browser; every other page is fetched directly as in the first pass (the plain fetcher's cache answers it without a new request).
    A host that blocks only now is added and read with the browser too."""

    def __init__(self, plain, browser, blocked):
        self.plain, self.browser, self.blocked = plain, browser, set(blocked)

    def get(self, url, *, restaurant, note):
        if host_key(url) in self.blocked:
            return self.browser.get(url, restaurant=restaurant, note=note)
        document = self.plain.get(url, restaurant=restaurant, note=note)
        if document.status in (403, 429, 503) and (document.status != 503 or document.kind == "html" and CHALLENGE.search(document.text[:40000])):
            self.blocked.update(host_key(u) for u in (document.url, document.final_url) if u)
            return self.browser.get(url, restaurant=restaurant, note=note)
        return document


class BrowserPages:
    """The second pass: pages rendered in the computer's own browser (studio.sources.browser_verification: installed Chrome started
    as an ordinary application, one persistent profile, reached over CDP), one page at a time. Used only for hosts that blocked plain
    HTTP in this run (a verification page or a refusal); see RoutedPages. A verification
    page that does not clear within the grace period leaves the restaurant for the end of the run; a block page stops that site."""

    def __init__(self, store, canceled, waiting=None, profile=None, opener=None, grace=None):
        self.store, self.canceled, self.waiting = store, canceled, waiting
        self.profile = profile
        self.opener = opener                     # tests inject a stand-in: opener(profile) -> object with goto, current, request, wait_all
        self.grace = GRACE_SECONDS if grace is None else grace
        self.session = None
        self.last = {}
        self.protected = set()

    def start(self):
        if self.session is None:
            self.session = (self.opener or CdpPages)(self.profile)
        return self.session

    def close(self):
        if self.session is not None:
            try:
                self.session.close()
            except Exception:
                pass
            finally:
                self.session = None

    def get(self, url, *, restaurant, note):
        host = (urlsplit(url).hostname or "").lower()
        gap = PROTECTED_GAP if host in self.protected else BROWSER_GAP
        if host in self.last:
            pause(max(0.0, gap - (time.monotonic() - self.last[host])), self.canceled)
        session = self.start()
        try:
            if DOCUMENT_PATH.search(urlsplit(url).path):
                status, final, content_type, body = session.request(url)
            else:
                status, final, content_type, body = session.goto(url)
                text = body.decode("utf-8", errors="replace")[:40000]
                if CHALLENGE.search(text):
                    self.protected.add(host)
                    status, final, content_type, body = self.grace_period(session, host, url)
                elif BLOCKED.search(text):
                    raise SourceError(f"Site engel sayfası gösterdi ({host}).")
        finally:
            self.last[host] = time.monotonic()
        digest, stamp = self.store.save(restaurant=restaurant, requested=url, final_url=final, status=status, content_type=content_type,
                                        body=body, note=f"{note} (tarayıcı)")
        return Document(url, final, status, content_type, body, digest, stamp, f"{note} (tarayıcı)")

    def grace_period(self, session, host, url):
        """Most verification pages clear by themselves in a real browser; one that does not is left for the end of the run."""
        deadline = time.monotonic() + self.grace
        while True:
            check(self.canceled)
            status, final, content_type, body = session.current()
            text = body.decode("utf-8", errors="replace")[:40000]
            if BLOCKED.search(text):
                raise SourceError(f"Site engel sayfası gösterdi ({host}).")
            if not CHALLENGE.search(text):
                return 200 if status in (403, 503, None) else status, final, content_type, body
            if time.monotonic() >= deadline:
                raise VerificationDeferred(host, url)
            pause(2.0, self.canceled)

    def wait_all(self, sites, timeout):
        """The one end-of-run wait: sites {host: url} open in tabs, the job lists them once; returns the hosts that opened."""
        return self.start().wait_all(sites, self.canceled, timeout, self.waiting)


DISMISS_POPUPS = """() => {
  const visible = el => { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden' && el.getClientRects().length > 0; };
  const dialogs = [...document.querySelectorAll('[role="dialog"],[role="alertdialog"],[aria-modal="true"],dialog[open]')].filter(visible);
  let clicked = 0;
  for (const dialog of dialogs) {
    const close = [...dialog.querySelectorAll('button,[role="button"]')].filter(visible).find(b => {
      const label = (b.getAttribute('aria-label') || b.getAttribute('title') || '').trim();
      const text = (b.textContent || '').trim();
      return /\\b(close|dismiss)\\b/i.test(label) || /^(close|dismiss|no,? thanks|×|✕|✖|x)$/i.test(text);
    });
    if (close) { close.click(); clicked += 1; }
  }
  return {dialogs: dialogs.length, clicked};
}"""


class CdpPages:
    """One tab of the computer's own browser (see BrowserPages); pages load with the browser's own navigation."""

    def __init__(self, profile):
        from .browser_verification import ChromeSession
        self.session = ChromeSession(profile)
        self.page = self.session.new_page()
        self.response = None

    def goto(self, url):
        try:
            self.response = self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as exc:
            if "Download is starting" in str(exc):
                return self.request(url)
            if WINDOW_CLOSED.search(f"{type(exc).__name__} {exc}"):
                raise
            raise httpx.NetworkError(str(exc)[:200]) from exc
        try:
            self.page.wait_for_load_state("networkidle", timeout=5_000)
        except Exception:
            pass
        self.dismiss()
        self.scroll()
        return self.current()

    def dismiss(self):
        """Close a pop-up window the page opened over its content (an ordering site's location chooser, a newsletter box): Escape,
        then only the pop-up's own close button (aria-label or text "Close", "Dismiss", "No thanks", "×"). Nothing else on the page is
        clicked: no ordering, location or cookie-consent choice is made."""
        try:
            if CHALLENGE.search(self.page.content()[:40000]):
                return None
            self.page.keyboard.press("Escape")
            time.sleep(0.5)
            result = self.page.evaluate(DISMISS_POPUPS)
            if result and result.get("clicked"):
                time.sleep(1.0)
            return result
        except Exception as exc:
            if WINDOW_CLOSED.search(f"{type(exc).__name__} {exc}"):
                raise
            return None

    def scroll(self, step=800, limit=60):
        """Scroll down the page as a reader would, so menus that load their sections as they come into view are on the page."""
        try:
            if CHALLENGE.search(self.page.content()[:40000]):
                return
            position = 0
            for _ in range(limit):
                position += step
                self.page.evaluate(f"window.scrollTo(0, {position})")
                time.sleep(0.4)
                if position >= self.page.evaluate("document.body ? document.body.scrollHeight : 0"):
                    break
            time.sleep(0.8)
        except Exception as exc:
            if WINDOW_CLOSED.search(f"{type(exc).__name__} {exc}"):
                raise

    def current(self):
        """The page as the browser shows it; a menu embedded in a frame (SinglePlatform, Wix menus) is appended in a <section> naming
        the frame's address, so the stored copy holds what the reader saw."""
        status = self.response.status if self.response is not None else None
        content_type = (self.response.headers.get("content-type") if self.response is not None else None) or "text/html"
        html = self.page.content()
        for frame in self.page.frames[1:]:
            try:
                if frame.url.startswith("http"):
                    html += f'\n<section data-frame="{html_module.escape(frame.url)}">{frame.content()}</section>'
            except Exception as exc:
                if WINDOW_CLOSED.search(f"{type(exc).__name__} {exc}"):
                    raise
        return status, self.page.url, content_type, html.encode("utf-8")

    def request(self, url):
        """A document (PDF, image) from inside the page with the browser's fetch; when the page may not read it (another origin
        without CORS), the browser opens it in a tab of its own."""
        from .browser_verification import FETCH
        try:
            answer = self.page.evaluate(FETCH, {"url": url, "method": "GET", "headers": {}, "body": None})
            return answer["status"], answer["url"] or url, answer["headers"].get("content-type"), base64.b64decode(answer["body"])
        except Exception:
            pass
        tab = self.session.new_page()
        try:
            response = tab.goto(url, wait_until="load", timeout=60_000)
            if response is None:
                raise httpx.NetworkError("Belge açılamadı.")
            return response.status, response.url, response.headers.get("content-type"), response.body()
        except httpx.HTTPError:
            raise
        except Exception as exc:
            raise httpx.NetworkError(str(exc)[:200]) from exc
        finally:
            try:
                tab.close()
            except Exception:
                pass

    def wait_all(self, sites, canceled, timeout, waiting):
        from .browser_verification import wait_for_user
        tabs = {}
        for host, url in sites.items():
            tab = self.session.new_page()
            try:
                tab.goto(url, wait_until="domcontentloaded", timeout=60_000)
            except Exception:
                pass
            tabs[host] = tab
        try:
            return wait_for_user(tabs, canceled, timeout, waiting)
        finally:
            for tab in tabs.values():
                try:
                    tab.close()
                except Exception:
                    pass

    def close(self):
        self.session.close()


def browser_available():
    from .browser_verification import available
    return available()


WINDOW_CLOSED = re.compile(r"TargetClosedError|has been closed|Browser closed|Connection closed", re.I)
BROWSER_REASONS = {"challenge": "doğrulama sayfası", "render": "JavaScript ile çizilen menü", "refused": "düz HTTP isteği reddedildi",
                   "known": "daha önce doğrulama gösteren site"}
KNOWN_STATUS = {"working": 3, "not_found": 2, "closed_permanently": 2, "closed_season": 2, "other_business": 2, "social_login": 1, "no_site": 1,
                "unreachable": 0}


def better(second, first):
    """True when the browser pass read more of the restaurant than plain HTTP did (a definite answer such as 'not found' also beats
    an unreachable site)."""
    def score(run):
        return (KNOWN_STATUS[run.site["site_status"]], sum(m["status"] == "read" for m in run.menus), len(run.items), len(run.facts))
    return score(second) > score(first)


def item_classes(path):
    """{external_id: {(item name, price text or ""): class}} from the reviewed item-class file (GÖREV-10: main dishes under $8 checked
    one by one); an unknown class is an error."""
    result = {}
    for external_id, rows in read_reviewed(path, "external_id").items():
        for row in rows:
            klass = (row.get("sinif") or "").strip()
            if klass not in SECTION_CLASSES:
                raise SourceError(f"Kalem sınıfı dosyasında bilinmeyen sınıf: {klass!r}.")
            result.setdefault(external_id, {})[(clean(row["kalem"]), clean(row.get("fiyat_metni") or ""))] = klass
    return result


def review_note(run):
    """A reviewer's note from the reviewed site file, kept as a fact labelled 'gözden geçirme': 'ana_yemek_sunmuyor' (a coffee,
    dessert, ice cream or drinks place; the text says what kind) or 'seviye_notu' (why the site gives no price level)."""
    row = run.override or {}
    for column, value in (("ana_yemek_sunmuyor", "no_mains"), ("seviye_notu", "note")):
        text = clean(row.get(column) or "")
        if text:
            run.facts["review_note"] = {"field": "review_note", "value": value, "detail": text, "link_url": None, "data": None,
                                        "source_url": row.get("site_url") or run.site["site_url"], "fetched_at": row.get("kontrol_tarihi") or None,
                                        "raw_sha256": None, "method": "gözden geçirme"}


def collect(raw_path, progress, canceled, *, config, client=None, waiting=None, browser=None):
    """Read every restaurant's own site once (its pages, menus and documents) and return the facts with their provenance.

    First pass: plain HTTP for every site (also one that showed a verification page in an earlier run), several restaurants side by
    side. Second pass (when the computer's browser is available), one restaurant at a time: only for restaurants where a host of
    theirs blocked plain HTTP (a verification page or a refusal, on the home page or a menu page), and only that host's pages are
    read with the browser (RoutedPages); a menu that merely needs JavaScript is not opened in the browser (user decision,
    9 October 2026). The second reading replaces the first only when it read more. A site still verifying after the grace period is left for the
    end: then the waiting sites open in tabs, the job lists them once and waits VERIFY_TIMEOUT for the user."""
    restaurants = (config.get("input") or {}).get("restaurants") if config else None
    if not restaurants:
        raise SourceError("Önce restoran dizini toplanmalı: işletme siteleri son restoran çekimindeki kayıtlardan okunur.")
    overrides = {k: v[0] for k, v in read_reviewed(config.get("site_overrides"), "external_id").items()}
    readings = read_reviewed(config.get("menu_readings"), "external_id")
    item_reviews = item_classes(config.get("item_classes"))
    sections = load_sections(config.get("sections") or SECTIONS_TABLE)
    store, pacer = RawStore(raw_path), HostPacer()
    owns = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(30, connect=15), verify=True)
    fetcher = Fetcher(client, store, pacer, canceled)
    done, lock, last = [0], threading.Lock(), [0.0]
    marks = {}
    progress(1, f"{len(restaurants)} restoranın kendi sitesi okunacak.")

    def one(restaurant):
        run = RestaurantRun(fetcher, restaurant, overrides.get(restaurant["external_id"]), readings.get(restaurant["external_id"], []), sections,
                            item_reviews.get(restaurant["external_id"]))
        try:
            run.run()        # every site is asked directly first, also one that showed a verification page before (user decision, 9 Oct 2026)
        except CollectionCanceled:
            raise
        except Exception as exc:          # one site's failure never stops the others
            run.site.update({"site_status": run.site["site_status"] if run.site["site_status"] != "no_site" else "unreachable",
                             "status_note": f"Beklenmeyen hata: {type(exc).__name__}: {str(exc)[:160]}"})
        with lock:
            done[0] += 1
            if time.monotonic() - last[0] > PROGRESS_EVERY or done[0] == len(restaurants):
                last[0] = time.monotonic()
                progress(2 + int(93 * done[0] / len(restaurants)), f"{done[0]}/{len(restaurants)} restoran · {restaurant['name']}")
        return run

    try:
        with ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="30a-restaurant") as pool:
            futures = [pool.submit(one, r) for r in restaurants]
            failures = [f.exception() for f in futures]
        if any(isinstance(e, CollectionCanceled) for e in failures) or canceled():
            raise CollectionCanceled()
        for error in failures:
            if error is not None:
                raise error
        runs = [f.result() for f in futures]
        store.flush()
        for run in runs:
            for host, block in run.blocked_hosts.items():
                if block["reason"] == "challenge":
                    marks[host] = {"host": host, "url": block["url"], "reason": "doğrulama sayfası"}
        second = [index for index, run in enumerate(runs) if run.needs_browser]
        if second and browser is not False and (browser is not None or browser_available()):
            pages = browser if browser is not None and not isinstance(browser, bool) else BrowserPages(store, canceled, waiting)
            if pages.store is None:
                pages.store = store
            if pages.waiting is None:
                pages.waiting = waiting
            deferred = []
            try:
                for count, index in enumerate(second, 1):
                    check(canceled)
                    first = runs[index]
                    progress(95, f"Tarayıcıyla ikinci okuma {count}/{len(second)} · {first.restaurant['name']}")
                    retry = RestaurantRun(RoutedPages(fetcher, pages, first.blocked_hosts), first.restaurant, first.override, first.readings,
                                          sections, first.item_reviews)
                    try:
                        retry.run()
                    except CollectionCanceled:
                        raise
                    except VerificationDeferred as wait:
                        marks[host_key(wait.url)] = {"host": host_key(wait.url), "url": wait.url, "reason": "doğrulama sayfası"}
                        deferred.append((index, wait.host, wait.url))
                        continue
                    except Exception as exc:
                        if WINDOW_CLOSED.search(f"{type(exc).__name__} {exc}"):
                            # the browser window was closed: the rest keep their first (plain HTTP) reading
                            for later in second[count - 1:]:
                                runs[later].site["status_note"] = (f"{runs[later].site['status_note'] or ''} Tarayıcı penceresi kapandığı için "
                                                                   f"tarayıcıyla ikinci okuma yapılmadı.").strip()
                            break
                        first.site["status_note"] = f"{first.site['status_note'] or ''} Tarayıcıyla okuma başarısız: {type(exc).__name__}: {str(exc)[:120]}".strip()
                        continue
                    for host, url in retry.challenged:
                        marks[host_key(url)] = {"host": host_key(url), "url": url, "reason": "doğrulama sayfası"}
                    if better(retry, first):
                        retry.site["status_note"] = (f"{retry.site['status_note'] or ''} Sayfalar görünür tarayıcıyla okundu "
                                                     f"({BROWSER_REASONS[first.needs_browser]}).").strip()
                        runs[index] = retry
                    else:
                        first.site["status_note"] = f"{first.site['status_note'] or ''} Tarayıcıyla okuma daha fazla bilgi vermedi.".strip()
                if deferred:
                    hosts = {}
                    for _, host, url in deferred:
                        hosts.setdefault(host, url)
                    progress(96, f"Doğrulama bekleyen siteler: {', '.join(sorted(hosts))}.")
                    cleared = pages.wait_all(hosts, VERIFY_TIMEOUT)
                    for index, host, _ in deferred:
                        first = runs[index]
                        if host not in cleared:
                            first.site["status_note"] = (f"{first.site['status_note'] or ''} Doğrulama sayfası {VERIFY_TIMEOUT // 60} dk içinde "
                                                         f"tamamlanmadı ({host}); tarayıcıyla okunamadı.").strip()
                            continue
                        retry = RestaurantRun(RoutedPages(fetcher, pages, first.blocked_hosts), first.restaurant, first.override,
                                              first.readings, sections, first.item_reviews)
                        try:
                            retry.run()
                        except CollectionCanceled:
                            raise
                        except Exception as exc:
                            first.site["status_note"] = (f"{first.site['status_note'] or ''} Doğrulamadan sonra tarayıcıyla okuma başarısız: "
                                                         f"{type(exc).__name__}: {str(exc)[:120]}").strip()
                            continue
                        if better(retry, first):
                            retry.site["status_note"] = (f"{retry.site['status_note'] or ''} Sayfalar doğrulamadan sonra tarayıcıyla okundu.").strip()
                            runs[index] = retry
            finally:
                if isinstance(pages, BrowserPages):
                    pages.close()
            store.flush()
        for run in runs:
            review_note(run)
        sites = [r.site for r in runs]
        facts = [{"external_id": r.site["external_id"], **f} for r in runs for f in r.facts.values()]
        menus = [{"external_id": r.site["external_id"], **m} for r in runs for m in r.menus]
        items = [{"external_id": r.site["external_id"], **i} for r in runs for i in r.items]
        statuses = {s: sum(x["site_status"] == s for x in sites) for s in SITE_STATUSES}
        snapshot = {"restaurant_run_id": config["input"]["run_id"], "checked_on": datetime.now(timezone.utc).date().isoformat(),
                    "request_count": store.count, "restaurant_count": len(sites)}
        hosts = sorted(marks.values(), key=lambda m: m["host"])
        metadata = {**snapshot, "site_statuses": statuses, "menu_count": len(menus), "menus_read": sum(m["status"] == "read" for m in menus),
                    "item_count": len(items), "fact_count": len(facts), "overrides": len(overrides),
                    "readings": sum(len(v) for v in readings.values()), "browser_hosts": hosts}
        progress(97, f"{len(sites)} restoran, {len(menus)} menü ve {len(items)} menü kalemi kaydediliyor.")
        return CollectionResult(sites, len(sites), statuses["no_site"], None, metadata,
                                {"snapshot": snapshot, "facts": facts, "menus": menus, "items": items, "browser_hosts": hosts})
    finally:
        try:
            store.flush()
        except OSError:
            pass
        if owns:
            client.close()


# --- Summaries computed when read ----------------------------------------------------------------------------------------------

def restaurant_view(site, facts, menus, items, regions):
    """One restaurant with its facts, menus, the main menu chosen for the price level and our main-dish numbers."""
    by_menu = {}
    for item in items:
        by_menu.setdefault(item["menu_id"], []).append(item)
    best = None
    for kind in MAIN_PRIORITY:
        typed = [m for m in menus if m["menu_type"] == kind and m["status"] == "read"]
        typed.sort(key=lambda m: -main_stats(by_menu.get(m["menu_id"], []))["count"])
        if typed and main_stats(by_menu.get(typed[0]["menu_id"], []))["count"]:
            best = typed[0]
            break
    stats = main_stats(by_menu.get(best["menu_id"], [])) if best else {"count": 0, "median": None, "min": None, "max": None}
    # tapas / small plates: from the main menu, or else the meal menu with the most priced small plates; shown apart, never a level
    small_menu = best if best and main_stats(by_menu.get(best["menu_id"], []), "kucuk_tabak")["count"] else max(
        (m for m in menus if m["menu_type"] in MAIN_PRIORITY and m["status"] == "read"),
        key=lambda m: main_stats(by_menu.get(m["menu_id"], []), "kucuk_tabak")["count"], default=None)
    small = main_stats(by_menu.get(small_menu["menu_id"], []), "kucuk_tabak") if small_menu else main_stats([], "kucuk_tabak")
    fixed = [{"name": i["name"], "price_text": i["price_text"], "price": i["price"], "menu_url": next((m["url"] for m in menus if m["menu_id"] == i["menu_id"]), None)}
             for i in items if i.get("section_class") == "sabit_menu" and i.get("price") is not None]
    view = {**site, "regions": regions, "facts": {f["field"]: f for f in facts}, "menus": menus, "main_menu_id": best["menu_id"] if best else None,
            "main_menu_type": best["menu_type"] if best else None, "main_menu_url": best["url"] if best else None, "main": stats,
            "price_level": price_level(stats), "small_plates": small, "small_plates_menu_url": small_menu["url"] if small["count"] else None,
            "fixed_menus": fixed}
    if (view["facts"].get("review_note") or {}).get("value") == "note":
        view["price_level"] = None       # a reviewer read the site and wrote why no level can be given (e.g. the menu read is another
                                         # business's): that decision holds until the reviewed file changes
    view["level_reason"] = level_reason(view)
    return view


SITE_REASONS = {"not_found": "site bulunamadı (sayfa yok)", "closed_permanently": "sitesine göre kalıcı olarak kapanmış",
                "closed_season": "sitesine göre sezon için kapalı", "other_business": "alan adı başka bir işletmede ya da satılık",
                "unreachable": "sitesine ulaşılamadı", "social_login": "yalnız sosyal medya sayfası var (giriş gerekiyor)",
                "no_site": "web sitesi yok"}
MENU_STATUS_REASONS = {"image_unread": "menü görüntüsü okunmadı", "error": "menü sayfası açılamadı", "no_items": "menüde fiyat bulunamadı"}


def level_reason(view):
    """One line saying why a restaurant has no price level (None when it has one). A reviewer's note (reviewed site file) comes
    first: 'ana yemek sunmuyor' for coffee, dessert, ice cream and drinks places, or a reason read on the site."""
    if view["price_level"]:
        return None
    note = view["facts"].get("review_note")
    if note and note["value"] == "no_mains" and not view["main"]["count"]:
        return f"ana yemek sunmuyor ({note['detail']})"
    if note and note["value"] == "note":
        return note["detail"]
    if view["site_status"] != "working":
        return SITE_REASONS.get(view["site_status"], view["site_status"])
    if not view["main"]["count"] and view["small_plates"]["count"]:
        return "tapas / küçük tabak menüsü, ana yemek bölümü yok (küçük tabak ortancası ayrı verilir)"
    if "JavaScript ile çiziliyor" in (view.get("status_note") or "") and not view["main"]["count"]:
        return "menü fiyatları sayfanın düz HTML'inde yok (JavaScript ile çiziliyor olabilir); tarayıcı yalnız engelde kullanıldığı için okunmadı"
    menus = view["menus"]
    if not menus:
        return "sitede menü bulunamadı"
    if not any(m["status"] == "read" for m in menus):
        return "menü okunamadı: " + ", ".join(sorted({MENU_STATUS_REASONS.get(m["status"], m["status"]) for m in menus}))
    count = view["main"]["count"]
    if count == 0:
        return "okunan menülerde fiyatlı ana yemek yok"
    return f"5'ten az fiyatlı ana yemek ({count})"


def load(con, run_id):
    snapshot = con.execute("SELECT * FROM restaurant_site_snapshots WHERE run_id=?", (run_id,)).fetchone()
    if not snapshot:
        return None, []
    regions = {}
    for row in con.execute("""SELECT r.external_id, r.canonical_region_id FROM restaurant_regions r WHERE r.run_id=?""", (snapshot["restaurant_run_id"],)):
        if row["canonical_region_id"]:
            regions.setdefault(row["external_id"], []).append(row["canonical_region_id"])
    facts, menus, items = {}, {}, {}
    for row in con.execute("SELECT * FROM restaurant_facts WHERE run_id=?", (run_id,)):
        fact = {**dict(row), "data": json.loads(row["data"]) if row["data"] else None}
        if fact["field"] == "hours":
            # runs before GÖREV-13 stored the empty days of a site's text (", , Tu 17:00-21:00"); they are not written, and an hours
            # fact with neither a day nor any text says nothing
            fact["detail"] = hours_text(fact["detail"]) or None
            if not fact["detail"] and not fact["data"]:
                continue
        facts.setdefault(row["external_id"], []).append(fact)
    for row in con.execute("SELECT * FROM restaurant_menus WHERE run_id=? ORDER BY external_id, menu_id", (run_id,)):
        menus.setdefault(row["external_id"], []).append(dict(row))
    for row in con.execute("SELECT * FROM restaurant_menu_items WHERE run_id=? ORDER BY external_id, menu_id, position", (run_id,)):
        items.setdefault(row["external_id"], []).append(dict(row))
    views = [restaurant_view(dict(site), facts.get(site["external_id"], []), menus.get(site["external_id"], []), items.get(site["external_id"], []),
                             sorted(set(regions.get(site["external_id"], []))))
             for site in con.execute("SELECT * FROM restaurant_sites WHERE run_id=? ORDER BY name, external_id", (run_id,))]
    return dict(snapshot), views


def summarize(con, run_id, region_order=(), region_names=None):
    snapshot, views = load(con, run_id)
    if snapshot is None:
        return None
    order = {region: index for index, region in enumerate(region_order)}
    names = region_names or {}
    regions = sorted({r for v in views for r in v["regions"]}, key=lambda r: (order.get(r, len(order)), r))
    rows = []
    for region in regions:
        members = [v for v in views if region in v["regions"]]
        medians = [v["main"]["median"] for v in members if v["price_level"]]
        rows.append({"region_id": region, "region_name": names.get(region, region), "restaurant_count": len(members),
                     "levels": {level: sum(v["price_level"] == level for v in members) for _, level in PRICE_LEVELS},
                     "median_of_medians": round(statistics.median(medians), 2) if medians else None,
                     "online_reservation": sum((v["facts"].get("reservation") or {}).get("value") == "online" for v in members),
                     "kids_menu": sum((v["facts"].get("kids_menu") or {}).get("value") == "yes" for v in members),
                     "no_information": sum(v["site_status"] != "working" or (not v["menus"] and not v["facts"]) for v in members)})
    listing = [{k: v[k] for k in ("external_id", "name", "site_url", "site_status", "status_note", "regions", "price_level", "main", "main_menu_type",
                                  "main_menu_url", "level_reason", "small_plates", "fixed_menus")} | {"reservation": (v["facts"].get("reservation") or {}).get("value"),
                                                       "reservation_platform": (v["facts"].get("reservation") or {}).get("detail"),
                                                       "kids_menu": (v["facts"].get("kids_menu") or {}).get("value"),
                                                       "menu_count": len(v["menus"]), "menus_read": sum(m["status"] == "read" for m in v["menus"])}
               for v in views]
    statuses = {s: sum(v["site_status"] == s for v in views) for s in SITE_STATUSES}
    return {"snapshot": snapshot, "regions": rows, "restaurants": listing, "statuses": statuses,
            "coverage": {"restaurants": len(views), "working": statuses["working"], "with_menu": sum(bool(v["menus"]) for v in views),
                         "with_prices": sum(v["main"]["count"] > 0 for v in views), "with_level": sum(bool(v["price_level"]) for v in views),
                         "with_hours": sum("hours" in v["facts"] for v in views), "with_reservation": sum("reservation" in v["facts"] for v in views)},
            "level_note": ("Fiyat seviyesi bizim sınıflamamızdır: işletmenin kendi sitesindeki en kapsamlı ana öğün menüsünde (akşam, yoksa öğle, "
                           "yoksa genel, yoksa brunch, yoksa kahvaltı) ana yemek fiyatlarının ortancası $15 altı '$', $15–25 '$$', $25–40 '$$$', "
                           "$40 ve üstü '$$$$'; 5'ten az ana yemek fiyatı varsa hesaplanmaz. Ek malzeme, ekstra ve yan ürünler ana yemek sayılmaz; "
                           "tapas / küçük tabaklar ve kişi başı sabit fiyatlı menüler ayrı verilir."),
            "hours_note": f"Çalışma saatleri: işletmenin sitesinde {snapshot['checked_on']} tarihinde yazan."}


def restaurant_detail(con, run_id, external_id):
    snapshot, views = load(con, run_id)
    if snapshot is None:
        return None
    view = next((v for v in views if v["external_id"] == external_id), None)
    if view is None:
        return None
    items = [dict(r) for r in con.execute("SELECT * FROM restaurant_menu_items WHERE run_id=? AND external_id=? ORDER BY menu_id, position",
                                           (run_id, external_id))]
    return {**view, "items": items, "snapshot": snapshot}


def source_host(url):
    """The directory host of a restaurant-sites source URL (…/listings/culinary-experiences/?kaynak=isletme-siteleri), or None."""
    match = re.fullmatch(r"https://(www\.visitsouthwalton\.com)/listings/culinary-experiences/\?" + re.escape(SOURCE_QUERY), url or "")
    return match.group(1) if match else None


def dumps(value):
    return None if value is None else json.dumps(value, ensure_ascii=False)


class RestaurantSitesConnector:
    uses_verification = True
    verify_minutes = VERIFY_TIMEOUT // 60
    name = "restaurant-sites"
    version = CONNECTOR_VERSION
    raw_filename = "manifest.json"
    method = "HTML/PDF"
    diff_enabled = False
    diff_reason = "İşletme siteleri tarihli okumalardır; sürümler arası fark özeti yerine her sürüm kendi kaynaklarıyla okunur."
    inputs = ("restaurant_records",)

    def supports(self, source):
        return source_host(source.get("url")) is not None

    def collect(self, source, raw_path, progress, canceled, *, context, waiting=None):
        if not context.restaurants:
            raise SourceError("Bu destinasyon için restoran yapılandırması yok.")
        return collect(raw_path, progress, canceled, config={**context.restaurants, "browser_hosts": context.browser_hosts}, waiting=waiting)

    def store_records(self, con, run_id, records, related=None):
        snapshot = related["snapshot"]
        con.execute("INSERT INTO restaurant_site_snapshots (run_id,restaurant_run_id,checked_on,request_count,restaurant_count) VALUES (?,?,?,?,?)",
                    (run_id, snapshot["restaurant_run_id"], snapshot["checked_on"], snapshot["request_count"], snapshot["restaurant_count"]))
        con.executemany("""INSERT INTO restaurant_sites (run_id,external_id,name,site_url,site_source,site_status,final_url,http_status,status_note,fetched_at,
            raw_sha256,page_count) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, s["external_id"], s["name"], s["site_url"], s["site_source"], s["site_status"], s["final_url"], s["http_status"], s["status_note"],
              s["fetched_at"], s["raw_sha256"], s["page_count"]) for s in records])
        con.executemany("""INSERT INTO restaurant_facts (run_id,external_id,field,value,detail,link_url,data,source_url,fetched_at,raw_sha256,method)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, f["external_id"], f["field"], f["value"], f["detail"], f["link_url"], dumps(f["data"]), f["source_url"], f["fetched_at"],
              f["raw_sha256"], f["method"]) for f in related["facts"]])
        con.executemany("""INSERT INTO restaurant_menus (run_id,external_id,menu_id,url,format,menu_type,title,platform,linked_from,fetched_at,raw_sha256,
            method,status,message,item_count) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, m["external_id"], m["menu_id"], m["url"], m["format"], m["menu_type"], m["title"], m["platform"], m["linked_from"], m["fetched_at"],
              m["raw_sha256"], m["method"], m["status"], m["message"], m["item_count"]) for m in related["menus"]])
        con.executemany("""INSERT INTO restaurant_menu_items (run_id,external_id,menu_id,position,section,section_class,class_basis,name,price_text,price,
            price_rule,method) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, i["external_id"], i["menu_id"], i["position"], i["section"], i["section_class"], i["class_basis"], i["name"], i["price_text"],
              i["price"], i["price_rule"], i["method"]) for i in related["items"]])
        mark_hosts(con, related.get("browser_hosts", []), CONNECTOR_VERSION)

    def read_records(self, con, run_id):
        return [dict(r) for r in con.execute("SELECT * FROM restaurant_sites WHERE run_id=? ORDER BY name, external_id", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Restaurant site diff is disabled.")
