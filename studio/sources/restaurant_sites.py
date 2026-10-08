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
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from .base import CollectionCanceled, CollectionResult, SourceError
from .climate_http import check, pause

CONNECTOR_VERSION = "restaurant-sites/1"
SOURCE_QUERY = "kaynak=isletme-siteleri"
SECTIONS_TABLE = Path(__file__).with_name("menu_sections.csv")
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36 "
              "30AStudio/0.12 (+https://github.com/bemonths/tatilya)")
REQUEST_GAP = 2.0               # seconds between two requests to the same host
WORKERS = 6
MAX_BYTES = 20_000_000
MAX_DOCUMENTS = 10              # menu documents read per restaurant
MAX_INFO_PAGES = 3              # hours / contact / about pages read per restaurant
MAX_REDIRECTS = 5
PROGRESS_EVERY = 2.0

SITE_STATUSES = ("working", "not_found", "closed_permanently", "closed_season", "other_business", "unreachable", "social_login", "no_site")
FIELDS = ("hours", "reservation", "kids_menu", "outdoor_seating", "water_view", "dog_friendly", "site_price_range")
METHODS = ("yapısal veri", "sayfa metni", "PDF metni", "platform verisi", "görüntüden okundu", "bağlantı")
MENU_TYPES = ("dinner", "lunch", "general", "brunch", "breakfast", "kids", "drinks", "dessert", "happy_hour")
MAIN_PRIORITY = ("dinner", "lunch", "general", "brunch", "breakfast")      # the main meal menu the price level is computed from
SECTION_CLASSES = ("ana_yemek", "baslangic", "salata_corba", "tatli", "icecek", "cocuk", "yan_urun", "diger")
PRICE_LEVELS = ((15, "$"), (25, "$$"), (40, "$$$"), (float("inf"), "$$$$"))
MIN_MAIN_PRICES = 5
SOCIAL_HOSTS = ("facebook.com", "instagram.com", "fb.com", "tiktok.com", "x.com", "twitter.com")
RESERVATION_PLATFORMS = {"opentable.com": "OpenTable", "resy.com": "Resy", "exploretock.com": "Tock", "sevenrooms.com": "SevenRooms",
                         "tables.toasttab.com": "Toast Tables", "resos.com": "resOS", "tablein.com": "Tablein", "yelp.com/reservations": "Yelp"}
MENU_PLATFORMS = {"toasttab.com": "Toast", "square.site": "Square", "squareup.com": "Square", "popmenu.com": "Popmenu", "getbento.com": "BentoBox",
                  "spothopperapp.com": "SpotHopper", "spothopper.com": "SpotHopper", "chownow.com": "ChowNow", "olo.com": "Olo",
                  "clover.com": "Clover", "menufy.com": "Menufy", "order.online": "DoorDash Storefront", "singleplatform.com": "SinglePlatform",
                  "menu.app": "Menu.app", "beyondmenu.com": "BeyondMenu", "touchbistro.com": "TouchBistro", "owner.com": "Owner.com"}
MENU_WORD = re.compile(r"\bmenus?\b|\bdinner\b|\blunch\b|\bbrunch\b|\bbreakfast\b|\bkids\b|\bchildren'?s\b|\bdrinks?\b|\bcocktails?\b|\bwine list\b|"
                       r"\bdesserts?\b|\bhappy hour\b|\bfood\b|\beat\b|\border online\b", re.I)
INFO_WORD = re.compile(r"\bhours\b|\bcontact\b|\blocation|\bvisit\b|\babout\b|\bfaq\b|\bfind us\b", re.I)
TYPE_WORDS = (("happy_hour", r"happy hour"), ("kids", r"\bkids?\b|\bchildren'?s?\b|\blittle ones\b"), ("dessert", r"\bdesserts?\b|\bsweets\b"),
              ("drinks", r"\bdrinks?\b|\bcocktails?\b|\bwine\b|\bbeer\b|\bbar menu\b|\bbeverages?\b|\bspirits\b"),
              ("brunch", r"\bbrunch\b"), ("breakfast", r"\bbreakfast\b"), ("lunch", r"\blunch\b"), ("dinner", r"\bdinner\b|\bsupper\b|\bevening\b"))
PARKED = re.compile(r"domain (?:is|may be) for sale|buy this domain|this domain has expired|domain name (?:is )?for sale|parked (?:free|domain)|"
                    r"hugedomains|sedo domain parking|is for sale!", re.I)
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

    def get(self, url, *, restaurant, note):
        """GET with redirects followed (each hop kept). Returns Document or raises httpx.HTTPError / SourceError."""
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
            if line[3:].strip():
                lines.append(("h", line[3:].strip()))
        else:
            lines.append(("p", line))
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
            texts.append(f"{', '.join(clean(str(n)).rsplit('/', 1)[-1] for n in names)} {opens}–{closes}")
        hours = item.get("openingHours")
        for entry in hours if isinstance(hours, list) else ([hours] if isinstance(hours, str) else []):
            texts.append(clean(entry))
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
ITEM_LINE = re.compile(r"^(?P<name>(?:[A-Za-z\"'(¡¿#&½]|\d+(?:/\d+)?\s?(?:oz|lb|pc|piece|dozen|doz)?\.?\s?[A-Za-z])[^$]{1,90}?)\s*(?:[.\-–—…·:|]{2,}\s*|\s[-–—|:]\s|\s)"
                       r"(?P<prices>\$?\s?\d{1,3}(?:\.\d{1,2})?(?:\s*(?:/|\||or|,|-)\s*\$?\s?\d{1,3}(?:\.\d{1,2})?){0,3}\+?)\s*$")
PRICE_ONLY = re.compile(r"^(?:[A-Za-z ]{0,12}\s)?\$?\s?\d{1,3}(?:\.\d{1,2})?(?:\s*(?:/|\||or|,|-)\s*(?:[A-Za-z ]{0,12}\s)?\$?\s?\d{1,3}(?:\.\d{1,2})?){0,3}\+?$")
SIZE_PRICES = re.compile(r"^(?P<name>.+?)\s+(?P<sizes>(?:(?:cup|bowl|half|full|small|large|reg(?:ular)?|single|double|glass|bottle|\d+\s?(?:pc|oz|piece|ct)s?|"
                         r"6\"|12\"|8\"|10\"|14\"|16\")\s*\$?\s?\d{1,3}(?:\.\d{1,2})?\s*[/|,]?\s*){2,})$", re.I)
MARKET = re.compile(r"\b(?:market price|mkt\.?|mp|m\.p\.|market)\s*$", re.I)
NOT_PRICE_UNIT = re.compile(r"\d\s*(?:oz|lb|lbs|pc|pcs|pieces?|ct|count|inch|in\.|\"|%|am|pm|a\.m|p\.m|calories|cal|years?|yrs?|ft|miles?)\b", re.I)
SKIP_NAME = re.compile(r"^(?:add|sub|substitute|make it|upgrade|\+|with|w/|extra|choice of|choose|served|includes?|gratuity|tax|price|prices)\b", re.I)
PHONE = re.compile(r"\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}")
# Buttons and counters menu platforms print between dishes ("1 likes", "Order Online", "0 0 0").
NOISE = re.compile(r"^(?:\d+\s+likes?|\d+(?:\s+\d+)+|order online|order now|add to (?:cart|order|bag)|view details|completed loading.*|"
                   r"n/a|sold out|popular|new|gluten[- ]free|gf|v|vg|df)$", re.I)
TWIN_PRICE = re.compile(r"\$(\d{1,3}(?:\.\d{2})?)\s+\$\1(?=\s|$)")


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
    return clean(text)


def parse_menu(lines):
    """Menu items from text lines: [{'section', 'name', 'price_text', 'price', 'price_rule'}]. Several sizes or portions: the lowest
    price is used ('lowest'); 'market price' keeps its text and no number ('market'). A line that is only a description with the
    price at its end takes the short name line above it as the item name. A heading directly followed by its price (sites that
    write each dish name as a heading) is an item of the section above it, not a new section."""
    items, section, pending, headed = [], None, None, None

    def emit(name, price_text, values, *, market=False, under=None):
        nonlocal pending, headed, section
        if headed is not None and under is headed:
            section = headed[1]                   # the heading was a dish name: its section is the one above
        items.append({"section": section, "name": name, "price_text": price_text, "price": None if market else min(values),
                      "price_rule": "market" if market else ("lowest" if len(values) > 1 else "single")})
        pending, headed = None, None

    for kind, line in lines:
        text = menu_line(line)
        if not text or NOISE.match(text):
            continue
        twin = TWIN_PRICE.search(text)
        if twin and kind != "h":
            text = f"${twin.group(1)}"            # "...lime juice$12 $12 Mashed avocado..." (description, price, description again)
        if kind == "h" or heading_like(text) and not ITEM_LINE.match(text) and not MARKET.search(text):
            if len(text) <= 60 and not PHONE.search(text):
                headed = (text, section)
                section, pending = text, None
            continue
        if PHONE.search(text) or re.search(r"\b\d{1,2}(?::\d{2})?\s*[ap]\.?m\b", text, re.I) and not re.search(r"\$", text):
            pending = None if pending and not looks_like_description(pending) else pending
            continue
        if pending and not looks_like_description(pending):
            name_above, under_h = pending, None
        elif headed:
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
        if PRICE_ONLY.match(text) and not NOT_PRICE_UNIT.search(text):
            values = money_values(text)
            if values and name_above:
                emit(name_above, text, values, under=under_h)
            else:
                pending = None
            continue
        if MARKET.fullmatch(text) and name_above:
            emit(name_above, text, [], market=True, under=under_h)
            continue
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
    text = unicodedata.normalize("NFKD", clean(section)).encode("ascii", "ignore").decode().lower().replace("&", " & ")
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


def item_class(item, kind, table):
    """(class, basis) of a menu item: its section heading by the table ('section'); when the heading gives no class (no heading,
    or one the table does not know), the item's own name by the same table ('name'). Items of a kids menu are 'cocuk'."""
    klass, basis = classify(item.get("section"), table), "section"
    if klass == "diger":
        by_name = classify(item.get("name"), [row for row in table if not (len(row) == 3 and row[2])])
        if by_name != "diger":
            klass, basis = by_name, "name"
    if kind == "kids" and klass in ("ana_yemek", "diger"):
        klass, basis = "cocuk", "menu"
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


def main_stats(items):
    """Count, median, lowest and highest of the main-dish prices (section class ana_yemek, a number)."""
    prices = sorted(i["price"] for i in items if i.get("section_class") == "ana_yemek" and i.get("price") is not None and i["price"] > 0)
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
    def __init__(self, fetcher, restaurant, override, readings, sections):
        self.fetcher, self.restaurant, self.override, self.readings, self.sections = fetcher, restaurant, override, readings, sections
        self.site = {"external_id": restaurant["external_id"], "name": restaurant["name"], "site_url": None, "site_source": "none",
                     "site_status": "no_site", "final_url": None, "http_status": None, "status_note": None, "fetched_at": None,
                     "raw_sha256": None, "page_count": 0}
        self.facts, self.menus, self.items = {}, [], []
        self.read_pages = []           # (document, lines) of every HTML page read for this restaurant
        self.schema_menus = []         # menu urls the structured data names
        self.needs_browser = None      # 'challenge' (verification page) or 'render' (menus built with JavaScript): read again in a browser

    def get(self, url, note):
        document = self.fetcher.get(url, restaurant=self.restaurant["external_id"], note=note)
        self.site["page_count"] += 1
        return document

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
        self.site.update({"site_url": url, "site_source": "review" if self.override else "directory"})
        try:
            home = self.get(url, "site-home")
        except (httpx.HTTPError, SourceError) as exc:
            self.site.update({"site_status": "unreachable", "status_note": f"Siteye ulaşılamadı: {type(exc).__name__}"})
            return self
        self.site.update({"final_url": home.final_url, "http_status": home.status, "fetched_at": home.fetched_at, "raw_sha256": home.sha256})
        if on_host(home.final_url, SOCIAL_HOSTS):
            self.site.update({"site_status": "social_login", "status_note": "Sosyal medya sayfası; giriş yapmadan içerik okunmadı."})
            return self
        if home.status in (404, 410):
            self.site.update({"site_status": "not_found", "status_note": f"Site HTTP {home.status} döndü."})
            return self
        if home.status != 200 or home.kind != "html":
            challenged = home.status in (403, 429, 503) and CHALLENGE.search(home.text[:40000] if home.kind == "html" else "")
            self.site.update({"site_status": "unreachable", "status_note": (f"Site düz HTTP isteğine doğrulama sayfası gösterdi (HTTP {home.status})."
                              if challenged else f"Site HTTP {home.status} ({home.content_type}) döndü.")})
            if challenged:
                self.needs_browser = "challenge"
            return self
        html = home.text
        lines = html_lines(html)
        flat = " ".join(t for _, t in lines)
        if PARKED.search(flat) or PARKED.search(page_title(html)):
            self.site.update({"site_status": "other_business", "status_note": "Alan adı satılık / park edilmiş sayfa."})
            return self
        if not same_business(page_title(html) + " " + flat, restaurant):
            self.site["status_note"] = "Ana sayfada işletmenin adı ya da telefonu görünmedi; site yine de okundu."
        self.site["site_status"] = "working"
        self.read_pages.append((home, lines))
        self.structured(home, html)
        found = links(html, home.final_url) + self.schema_menus
        menu_targets, info_targets = self.targets(found, home.final_url)
        for label, target in info_targets[:MAX_INFO_PAGES]:
            try:
                page = self.get(target, "site-info")
            except (httpx.HTTPError, SourceError):
                continue
            if page.status == 200 and page.kind == "html":
                self.read_pages.append((page, html_lines(page.text)))
                self.structured(page, page.text)
        self.read_menus(menu_targets, home)
        self.text_facts()
        if not any(m["status"] == "read" for m in self.menus) and (not self.menus or any(m["status"] == "no_items" for m in self.menus)):
            self.needs_browser = self.needs_browser or "render"
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
            same_site = host_of(target) == site
            is_doc = re.search(r"\.(pdf|jpe?g|png|webp)$", path)
            menu_like = MENU_WORD.search(label) or re.search(r"menu|dinner|lunch|brunch|breakfast|kids|drink|cocktail|dessert|happy-hour", path)
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
        queue, seen, documents = list(targets), set(), set()
        while queue and len(self.menus) < MAX_DOCUMENTS:
            label, target = queue.pop(0)
            key = target.split("#")[0]
            if key in seen:
                continue
            seen.add(key)
            try:
                document = self.get(target, "menu")
            except (httpx.HTTPError, SourceError) as exc:
                self.add_menu(target, label, home, None, "error", f"Okunamadı: {type(exc).__name__}")
                continue
            if document.sha256 in documents or document.final_url.split("#")[0] in seen and document.final_url.split("#")[0] != key:
                continue                          # the same document under another link
            documents.add(document.sha256)
            seen.add(document.final_url.split("#")[0])
            if document.status != 200:
                self.add_menu(target, label, home, document, "error", f"HTTP {document.status}")
                continue
            if document.kind == "html":
                html = document.text
                lines = html_lines(html)
                self.read_pages.append((document, lines))
                self.structured(document, html)
                title = page_title(html)
                items = parse_menu(lines)
                platform = platform_of(document.final_url, MENU_PLATFORMS)
                if items:
                    self.add_menu(target, label or title, home, document, "read", None, items=items, platform=platform,
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
                else:
                    self.add_menu(target, label or title, home, document, "no_items",
                                  "Platform sayfası tarayıcı çalıştırmadan fiyat göstermiyor.", platform=platform, title=title)
            elif document.kind == "pdf":
                try:
                    lines = pdf_lines(document.body)
                except Exception as exc:
                    self.add_menu(target, label, home, document, "error", f"PDF açılamadı: {type(exc).__name__}", fmt="pdf")
                    continue
                items = parse_menu(lines)
                if items:
                    self.add_menu(target, label, home, document, "read", None, items=items, method="PDF metni", fmt="pdf",
                                  text=" ".join(t for _, t in lines[:40]))
                else:
                    self.image_or_unread(target, label, home, document, "pdf")
            elif document.kind == "image":
                self.image_or_unread(target, label, home, document, "image")
            else:
                self.add_menu(target, label, home, document, "error", f"Desteklenmeyen içerik türü: {document.content_type}")

    def menu_images(self, html, base):
        images = []
        for match in re.finditer(r'(?is)<img\b[^>]*?src\s*=\s*["\']([^"\']+)["\'][^>]*>', html):
            if re.search(r"menu", match.group(0), re.I) and re.search(r"\.(jpe?g|png|webp)(?:\?|$)", match.group(1), re.I):
                alt = re.search(r'alt\s*=\s*["\']([^"\']*)', match.group(0), re.I)
                images.append((clean(alt.group(1)) if alt else "menu image", urljoin(base, html_module.unescape(match.group(1)))))
        return images[:4]

    def image_or_unread(self, target, label, home, document, fmt):
        rows = [r for r in self.readings if r["raw_sha256"] == document.sha256]
        if rows:
            items = [{"section": r["section"] or None, "name": r["name"], "price_text": r["price_text"],
                      "price": float(r["price"]) if r.get("price") not in (None, "") else None,
                      "price_rule": r.get("price_rule") or ("market" if not r.get("price") else "single")} for r in rows]
            self.add_menu(target, label or rows[0].get("menu_title"), home, document, "read", None, items=items, method="görüntüden okundu",
                          fmt=fmt, menu_kind=rows[0].get("menu_type") or None)
        else:
            reason = ("Görüntü menü; gözden geçirme dosyasında bu görüntünün okuması yok." if fmt == "image" else
                      "PDF'te metin yok (taranmış görüntü); gözden geçirme dosyasında okuması yok.")
            self.add_menu(target, label, home, document, "image_unread", reason, fmt=fmt)

    def add_menu(self, target, label, home, document, status, message, *, items=(), platform=None, method=None, fmt=None, title=None, text=None,
                 menu_kind=None):
        menu_id = len(self.menus) + 1
        kind = menu_kind or menu_type(label, urlsplit(target).path.replace("-", " ").replace("_", " "), title, text if text and len(text) < 400 else None)
        if fmt is None:
            fmt = "platform" if platform else (document.kind if document is not None and document.kind in ("html", "pdf", "image") else "html")
        self.menus.append({"menu_id": menu_id, "url": document.final_url if document else target, "format": fmt, "menu_type": kind,
                           "title": clean(label or title or "")[:200] or None, "platform": platform, "linked_from": home.final_url,
                           "fetched_at": document.fetched_at if document else None, "raw_sha256": document.sha256 if document else None,
                           "method": method, "status": status, "message": message, "item_count": len(items)})
        for position, item in enumerate(items, 1):
            section_class, basis = item_class(item, kind, self.sections)
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


CHALLENGE = re.compile(r"Just a moment\.\.\.|cf-chl-|/cdn-cgi/challenge-platform|Verify you are human|Checking your browser before|"
                       r"Checking if the site connection is secure", re.I)
BLOCKED = re.compile(r"Sorry, you have been blocked|You are unable to access|Attention Required! \| Cloudflare|Edge IP Restricted", re.I)
DOCUMENT_PATH = re.compile(r"\.(?:pdf|jpe?g|png|webp|gif)(?:$|\?)", re.I)
BROWSER_GAP = 3.0               # seconds between two browser page loads on the same host
PROTECTED_GAP = 6.0             # the same on a site that answered plain HTTP with a verification page
VERIFY_TIMEOUT = 15 * 60


class BrowserPages:
    """The second pass: pages rendered in the computer's Chrome (or Edge) with a persistent profile in a visible window, one page
    at a time. Used for sites that answer plain HTTP with a verification page and for menus a site or platform builds with
    JavaScript. A verification page is left to the user (the job shows which site waits); a block page stops that site."""

    def __init__(self, store, canceled, waiting=None, profile=None, opener=None):
        self.store, self.canceled, self.waiting = store, canceled, waiting
        self.profile = profile
        self.opener = opener                     # tests inject a stand-in: opener() -> object with goto(url) and request(url)
        self.session = None
        self.last = {}
        self.protected = set()

    def start(self):
        if self.session is None:
            self.session = (self.opener or PlaywrightSession)(self.profile)
        return self.session

    def close(self):
        if self.session is not None:
            try:
                self.session.close()
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
                    status, final, content_type, body = self.wait_for_user(session, host, url)
                elif BLOCKED.search(text):
                    raise SourceError(f"Site engel sayfası gösterdi ({host}).")
        finally:
            self.last[host] = time.monotonic()
        digest, stamp = self.store.save(restaurant=restaurant, requested=url, final_url=final, status=status, content_type=content_type,
                                        body=body, note=f"{note} (tarayıcı)")
        return Document(url, final, status, content_type, body, digest, stamp, f"{note} (tarayıcı)")

    def wait_for_user(self, session, host, url):
        """Most verification pages clear by themselves in a real browser; otherwise the user completes it in the window."""
        deadline, announced = time.monotonic() + VERIFY_TIMEOUT, False
        try:
            while True:
                check(self.canceled)
                status, final, content_type, body = session.current()
                text = body.decode("utf-8", errors="replace")[:40000]
                if BLOCKED.search(text):
                    raise SourceError(f"Site engel sayfası gösterdi ({host}).")
                if not CHALLENGE.search(text):
                    return 200 if status in (403, 503, None) else status, final, content_type, body
                if time.monotonic() > deadline:
                    raise SourceError(f"Doğrulama süresinde tamamlanmadı ({host}).")
                if not announced and time.monotonic() > deadline - VERIFY_TIMEOUT + 20 and self.waiting:
                    self.waiting(host)
                    announced = True
                pause(3.0, self.canceled)
        finally:
            if announced and self.waiting:
                self.waiting(None)


class PlaywrightSession:
    """One visible Chrome/Edge window with a persistent profile; pages are loaded with the browser's own navigation."""

    def __init__(self, profile):
        from playwright.sync_api import sync_playwright
        from .browser_verification import profile_root
        self.playwright = sync_playwright().start()
        root = Path(profile) if profile else profile_root() / "restoranlar"
        root.mkdir(parents=True, exist_ok=True)
        self.context = None
        for channel in ("chrome", "msedge"):
            try:
                self.context = self.playwright.chromium.launch_persistent_context(str(root), channel=channel, headless=False, no_viewport=True,
                                                                                 locale="en-US")
                break
            except Exception:
                self.context = None
        if self.context is None:
            self.playwright.stop()
            raise SourceError("Görünür tarayıcı (Chrome/Edge) açılamadı.")
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.response = None

    def goto(self, url):
        try:
            self.response = self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as exc:
            if "Download is starting" in str(exc):
                return self.request(url)
            raise httpx.NetworkError(str(exc)[:200]) from exc
        try:
            self.page.wait_for_load_state("networkidle", timeout=12_000)
        except Exception:
            pass
        return self.current()

    def current(self):
        status = self.response.status if self.response is not None else None
        content_type = (self.response.headers.get("content-type") if self.response is not None else None) or "text/html"
        return status, self.page.url, content_type, self.page.content().encode("utf-8")

    def request(self, url):
        response = self.context.request.get(url, timeout=60_000)
        return response.status, response.url, response.headers.get("content-type"), response.body()

    def close(self):
        try:
            self.context.close()
        finally:
            self.playwright.stop()


def browser_available():
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


def better(second, first):
    """True when the browser pass read more of the restaurant than plain HTTP did."""
    def score(run):
        return (run.site["site_status"] == "working", sum(m["status"] == "read" for m in run.menus), len(run.items), len(run.facts))
    return score(second) > score(first)


def collect(raw_path, progress, canceled, *, config, client=None, waiting=None, browser=None):
    """Read every restaurant's own site once (its pages, menus and documents) and return the facts with their provenance.

    First pass: plain HTTP, several restaurants side by side. Second pass (when a browser is available): the restaurants whose site
    answered with a verification page or whose menus did not show prices without JavaScript, one at a time in the visible browser;
    the second reading replaces the first only when it read more."""
    restaurants = (config.get("input") or {}).get("restaurants") if config else None
    if not restaurants:
        raise SourceError("Önce restoran dizini toplanmalı: işletme siteleri son restoran çekimindeki kayıtlardan okunur.")
    overrides = {k: v[0] for k, v in read_reviewed(config.get("site_overrides"), "external_id").items()}
    readings = read_reviewed(config.get("menu_readings"), "external_id")
    sections = load_sections(config.get("sections") or SECTIONS_TABLE)
    store, pacer = RawStore(raw_path), HostPacer()
    owns = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(30, connect=15), verify=True)
    fetcher = Fetcher(client, store, pacer, canceled)
    done, lock, last = [0], threading.Lock(), [0.0]
    progress(1, f"{len(restaurants)} restoranın kendi sitesi okunacak.")

    def one(restaurant):
        run = RestaurantRun(fetcher, restaurant, overrides.get(restaurant["external_id"]), readings.get(restaurant["external_id"], []), sections)
        try:
            run.run()
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
        second = [index for index, run in enumerate(runs) if run.needs_browser]
        if second and browser is not False and (browser is not None or browser_available()):
            pages = browser if browser is not None and not isinstance(browser, bool) else BrowserPages(store, canceled, waiting)
            if pages.store is None:
                pages.store = store
            try:
                for count, index in enumerate(second, 1):
                    check(canceled)
                    first = runs[index]
                    progress(95, f"Tarayıcıyla ikinci okuma {count}/{len(second)} · {first.restaurant['name']}")
                    retry = RestaurantRun(pages, first.restaurant, first.override, first.readings, sections)
                    try:
                        retry.run()
                    except CollectionCanceled:
                        raise
                    except Exception as exc:
                        first.site["status_note"] = f"{first.site['status_note'] or ''} Tarayıcıyla okuma başarısız: {type(exc).__name__}: {str(exc)[:120]}".strip()
                        continue
                    if better(retry, first):
                        retry.site["status_note"] = (f"{retry.site['status_note'] or ''} Sayfalar görünür tarayıcıyla okundu "
                                                     f"({'doğrulama sayfası' if first.needs_browser == 'challenge' else 'JavaScript ile çizilen menü'}).").strip()
                        runs[index] = retry
                    else:
                        first.site["status_note"] = f"{first.site['status_note'] or ''} Tarayıcıyla okuma daha fazla bilgi vermedi.".strip()
            finally:
                if isinstance(pages, BrowserPages):
                    pages.close()
            store.flush()
        sites = [r.site for r in runs]
        facts = [{"external_id": r.site["external_id"], **f} for r in runs for f in r.facts.values()]
        menus = [{"external_id": r.site["external_id"], **m} for r in runs for m in r.menus]
        items = [{"external_id": r.site["external_id"], **i} for r in runs for i in r.items]
        statuses = {s: sum(x["site_status"] == s for x in sites) for s in SITE_STATUSES}
        snapshot = {"restaurant_run_id": config["input"]["run_id"], "checked_on": datetime.now(timezone.utc).date().isoformat(),
                    "request_count": store.count, "restaurant_count": len(sites)}
        metadata = {**snapshot, "site_statuses": statuses, "menu_count": len(menus), "menus_read": sum(m["status"] == "read" for m in menus),
                    "item_count": len(items), "fact_count": len(facts), "overrides": len(overrides),
                    "readings": sum(len(v) for v in readings.values())}
        progress(97, f"{len(sites)} restoran, {len(menus)} menü ve {len(items)} menü kalemi kaydediliyor.")
        return CollectionResult(sites, len(sites), statuses["no_site"], None, metadata,
                                {"snapshot": snapshot, "facts": facts, "menus": menus, "items": items})
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
    return {**site, "regions": regions, "facts": {f["field"]: f for f in facts}, "menus": menus, "main_menu_id": best["menu_id"] if best else None,
            "main_menu_type": best["menu_type"] if best else None, "main_menu_url": best["url"] if best else None, "main": stats,
            "price_level": price_level(stats)}


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
        facts.setdefault(row["external_id"], []).append({**dict(row), "data": json.loads(row["data"]) if row["data"] else None})
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
                                  "main_menu_url")} | {"reservation": (v["facts"].get("reservation") or {}).get("value"),
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
                           "$40 ve üstü '$$$$'; 5'ten az ana yemek fiyatı varsa hesaplanmaz."),
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
        return collect(raw_path, progress, canceled, config=context.restaurants, waiting=waiting)

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

    def read_records(self, con, run_id):
        return [dict(r) for r in con.execute("SELECT * FROM restaurant_sites WHERE run_id=? ORDER BY name, external_id", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Restaurant site diff is disabled.")
