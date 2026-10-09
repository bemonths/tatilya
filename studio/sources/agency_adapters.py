"""Rental-platform adapters for the agency rate collector: find the platform's listing identity on a company listing page and
ask the price/availability display the site's own front end asks, for one date window.

Destination-independent: an adapter knows a reservation platform or a company front end's public price display (ResCMS,
Track, Streamline, "vacation-rentals/router", VRPConnect, ...), never a destination. Which company site uses which adapter comes
from the destination configuration. Only fields the site shows are filled; everything else stays None. Amounts are the site's
own numbers; sums and checks are labelled as ours.

Every quote() receives the guest count (adults, children) and returns it under "guests" when the price request carried it, or
None when the site's price request has no guest field. An adapter may also read the company's own listing list (inventory())
and the listing details a page shows (unit_fields()) for the address/location matching in agency_matching.
"""
import json
import re
from datetime import date
from html import unescape
from urllib.parse import urlencode, urljoin, urlsplit

from .agency_matching import json_ld_unit, normalize_address, number
from .html_tree import Tree

DEFAULT_GUESTS = {"adults": 2, "children": 0}     # two adults, no children or pets unless the company configuration says otherwise


class AdapterError(Exception):
    """The site answered in a shape the adapter does not recognise; recorded per quote, never fatal for the run."""


def money(value):
    """'$1,246.62', '1246.62', 1246.62 -> 1246.62; a bracketed or minus amount is negative; anything else -> None."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = unescape(str(value)).strip().replace("−", "-")
    negative = text.startswith("-") or text.startswith("(") and text.endswith(")")
    digits = re.sub(r"[^0-9.]", "", text)
    if not digits or digits.count(".") > 1:
        return None
    return round(-float(digits) if negative else float(digits), 2)


def currency_of(text):
    return "USD" if "$" in (text or "") else None


def us_date(day, padded=True):
    return day.strftime("%m/%d/%Y") if padded else f"{day.month}/{day.day}/{day.year}"


def clean(text):
    return re.sub(r"\s+", " ", unescape(text or "")).strip() or None


def plain_text(fragment):
    return clean(re.sub(r"<[^>]+>", " ", fragment or ""))


def first_line(node):
    lines = [line.strip() for line in node.text().splitlines() if line.strip()]
    return re.sub(r"\s+", " ", lines[0]) if lines else ""


def breakdown(rent, fees, taxes, total, *, tax_items=None, excluded=None, nightly=None, currency=None):
    """Common quote shape. Cleaning is any fee the site labels as cleaning; the other fees keep their own names and amounts.

    total_includes_* are set only when the site's own total equals rent + fees + taxes within a dollar (our check);
    otherwise they stay None, because the site did not say what its total contains.
    """
    cleaning = [f for f in fees if re.search(r"clean", f["name"], re.I)]
    others = [f for f in fees if f not in cleaning]
    fee_sum = round(sum(f["amount"] for f in fees), 2) if fees else None
    tax_sum = taxes if taxes is not None else (round(sum(t["amount"] for t in tax_items), 2) if tax_items else None)
    parts = [rent] + [f["amount"] for f in fees] + ([tax_sum] if tax_sum is not None else [])
    adds_up = total is not None and rent is not None and abs(sum(parts) - total) <= 1.0
    return {"status": "priced", "available": 1, "rent": rent,
            "cleaning_fee": round(sum(f["amount"] for f in cleaning), 2) if cleaning else None,
            "other_fees": round(sum(f["amount"] for f in others), 2) if others else None,
            "fees": fees or None, "taxes": tax_sum, "tax_items": tax_items or None, "total": total,
            "total_includes_fees": (1 if fees else 0) if adds_up else None, "total_includes_taxes": (1 if tax_sum is not None else 0) if adds_up else None,
            "excluded_items": excluded or None, "nightly_rates": nightly or None, "currency": currency, "fee_sum": fee_sum}


def outcome(status, message=None, *, available=None, min_stay=None):
    return {"status": status, "available": available, "message": message, "min_stay": min_stay}


def stay_message(message):
    """Site text about a minimum stay ('4 night minimum', 'minimum stay of 7 nights') -> (status, nights)."""
    text = message or ""
    if re.search(r"minimum|min\.? stay|at least", text, re.I):
        nights = re.search(r"(\d+)\s*(?:-\s*)?nights?", text, re.I)
        return "restricted", int(nights.group(1)) if nights else None
    return "unavailable", None


# --- ResCMS (Drupal rescms module) ---------------------------------------------------------------------------------------

def _setting(segment, key, *, numeric=False):
    """First value of a key in a JSON or single-quoted JavaScript object; numeric=True skips non-numeric values of the same key
    (the settings also carry a text table where 'mns' is a label, not a number)."""
    for match in re.finditer(r"['\"]%s['\"]\s*:\s*(null|true|false|!0|!1|-?\d+|['\"][^'\"]*['\"]|\[[^\]]*\])" % re.escape(key), segment):
        raw = match.group(1)
        if raw in ("null", "false", "!1"):
            value = None
        elif raw in ("true", "!0"):
            value = True
        elif raw.startswith("["):
            value = [int(v) for v in re.findall(r"\d+", raw)]
        else:
            raw = raw.strip("'\"")
            value = int(raw) if re.fullmatch(r"-?\d+", raw) else raw or None
        if not numeric or isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _ranges(segment, key, fields):
    """The rcItemAvailForm arrays (restr, avail) in either JSON or single-quoted JavaScript form."""
    start = re.search(r"['\"]%s['\"]\s*:\s*\[" % key, segment)
    if not start:
        return []
    depth, end = 1, start.end()
    while end < len(segment) and depth:
        depth += {"[": 1, "]": -1}.get(segment[end], 0)
        end += 1
    body = segment[start.end():end - 1]
    rows = []
    for item in re.finditer(r"\{([^{}]*)\}", body):
        text = item.group(1)
        begin, end = _setting(text, "b"), _setting(text, "e")
        if not (isinstance(begin, str) and isinstance(end, str)):
            continue
        rows.append({"b": begin, "e": end, **{name: _setting(text, name) for name in fields}})
    return rows


class ResCMS:
    """Drupal ResCMS sites: the listing page carries the item's entity id and its stay rules; the front end asks
    /rescms/ajax/item/pricing/simple for availability and a price, then the "detailed quote" link for the breakdown."""

    name = "rescms"
    sends_guests = True

    def parse_page(self, html, url):
        anchor = html.find("rcItemAvailForm")
        if anchor < 0:
            return None
        segment = html[anchor:anchor + 400_000]
        eid = _setting(segment, "eid", numeric=True)
        if not isinstance(eid, int):
            return None
        turn_default = _setting(segment, "td", numeric=True)
        return {"site_id": str(eid), "origin": f"{urlsplit(url).scheme}://{urlsplit(url).netloc}", "page_url": url,
                "min_stay_default": _setting(segment, "mns", numeric=True), "turn_default": turn_default,
                "restr": _ranges(segment, "restr", ("t", "mn")), "avail": _ranges(segment, "avail", ("a",))}

    def rules(self, info, checkin):
        """Minimum stay and allowed check-in weekdays (ISO 1=Mon..7=Sun) for a check-in date, as the page's date picker applies them."""
        day = checkin.isoformat()
        rule = next((r for r in info["restr"] if r["b"] <= day <= r["e"]), None)
        min_stay = rule["mn"] if rule and isinstance(rule.get("mn"), int) and rule["mn"] > 0 else info["min_stay_default"]
        turn = rule.get("t") if rule else None
        if turn is None and info["turn_default"]:
            turn = info["turn_default"]
        days = None if turn in (None, 0) or turn == [0] else sorted(set(turn if isinstance(turn, list) else [turn]))
        return (min_stay if isinstance(min_stay, int) and min_stay > 0 else None), days

    def unit_fields(self, html):
        """The listing's own location (Drupal field_location: street, city, coordinates) and the bedroom/bath/occupancy lines."""
        found = {}
        location = re.search(r'"field_location":\{"und":\[\{(.*?)\}\]', html)
        if location:
            body = location.group(1)
            for key, target in (("street", "address"), ("additional", "address2"), ("city", "city")):
                value = re.search(r'"%s":"((?:[^"\\]|\\.)*)"' % key, body)
                if value and value.group(1).strip():
                    found[target] = json.loads(f'"{value.group(1)}"').strip()
            for key in ("latitude", "longitude"):
                value = re.search(r'"%s":"(-?[0-9.]+)"' % key, body)
                if value and number(value.group(1)):
                    found[key] = number(value.group(1))
        beds = re.search(r'rc-lodging-beds[^>]*>\s*([0-9.]+)\s*Bed', html)
        baths = re.search(r'rc-lodging-baths[^>]*>\s*([0-9.]+)\s*Bath', html)
        sleeps = re.search(r'"Occupancy"\s*:\s*"?(\d+)', html)
        found.update({k: number(m.group(1)) for k, m in (("bedrooms", beds), ("bathrooms", baths), ("sleeps", sleeps)) if m})
        if found.get("address2"):
            found["address"] = f"{found.get('address') or ''} {found.pop('address2')}".strip()
        return found

    def quote(self, session, info, window, guests=DEFAULT_GUESTS):
        checkin, checkout = window["checkin_date"], window["checkout_date"]
        min_stay, days = self.rules(info, checkin)
        params = {"rcav[begin]": us_date(checkin), "rcav[end]": us_date(checkout), "rcav[flex_type]": "d", "rcav[adult]": str(guests["adults"]),
                  "rcav[child]": str(guests["children"]), "rcav[eid]": info["site_id"]}
        headers = {"X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*; q=0.01", "Referer": info["page_url"]}
        simple = session.request("GET", info["origin"] + "/rescms/ajax/item/pricing/simple", params=params, headers=headers,
                                 note=f"rescms-simple-{info['site_id']}-{window['window_key']}")
        rules = {"min_stay": min_stay, "checkin_days": days, "rule_source": "sayfa" if min_stay or days else None}
        if simple.status != 200:
            raise AdapterError(f"Fiyat isteği HTTP {simple.status} döndü.")
        content = _json_content(simple.text)
        if "rc-na" in content:
            return {**outcome("unavailable", plain_text(content), available=0), **rules, "replies": [simple]}
        link = re.search(r'<a href="([^"]*pricing/quote\?[^"]*)"[^>]*class="rc-item-quote-link"', content)
        if not link:
            return {**outcome("no_price", plain_text(content)), **rules, "replies": [simple]}
        href = unescape(link.group(1))
        detail = session.request("GET", urljoin(info["origin"] + "/", href), headers=headers,
                                 note=f"rescms-quote-{info['site_id']}-{window['window_key']}")
        if detail.status != 200:
            raise AdapterError(f"Ayrıntılı fiyat isteği HTTP {detail.status} döndü.")
        return {**self.parse_quote(_json_content(detail.text)), **rules, "replies": [simple, detail]}

    @staticmethod
    def parse_quote(content):
        """Line items, sub-total, tax and total of the detailed quote. Optional items ("forced-choice" rows such as travel
        insurance) count as fees only when the site's own sub-total includes them; a "declined" row never does."""
        tree = Tree(content).root
        rent, fees, optional, taxes, total, subtotal, excluded, currency = None, [], [], [], None, None, [], None
        for row in tree.find("tr"):
            classes = row.attrs.get("class", "").split()
            cells = [c for c in row.children if getattr(c, "tag", None) in ("td", "th")]
            amount_cell = next((c for c in cells if "amount" in c.attrs.get("class", "").split()), cells[-1] if cells else None)
            if not cells or amount_cell is None:
                continue
            label, amount_text = first_line(cells[0]), clean(amount_cell.text()) or ""
            amount = money(amount_text)
            currency = currency or currency_of(amount_text)
            if "total" in classes:
                total = amount
            elif "sub-total" in classes:
                subtotal = amount
            elif "tax" in classes:
                if amount is not None:
                    taxes.append({"name": label or "Tax", "amount": amount})
            elif "line-item" in classes:
                if amount is None:
                    continue
                if "declined" in classes:
                    excluded.append({"name": label, "amount": amount, "reason": "sitede isteğe bağlı, seçilmemiş"})
                elif rent is None and re.match(r"(lodging|rent|rental|accommodation)\b", label, re.I):
                    rent = amount
                elif "forced-choice" in classes or re.search(r"\(optional\)", label, re.I):
                    optional.append({"name": label, "amount": amount})
                else:
                    fees.append({"name": label, "amount": amount})
        if rent is None and total is None:
            raise AdapterError("Ayrıntılı fiyat tablosunda kira veya toplam satırı yok.")
        included = included_optional(rent, fees, optional, subtotal)
        fees.extend(o for o in optional if o in included)      # part of this price: the site's sub-total counts them
        excluded.extend({**o, "reason": "sitede isteğe bağlı; sitenin ara toplamına dahil değil"} for o in optional if o not in included)
        return breakdown(rent, fees, None, total, tax_items=taxes, excluded=excluded, currency=currency)


def included_optional(rent, fees, optional, subtotal):
    """The optional items the site's own sub-total includes: the one subset of them that makes rent + fees + subset equal the
    sub-total (within a dollar). No sub-total, no matching subset or more than one matching subset: none is counted."""
    if not optional or subtotal is None or len(optional) > 6:
        return []
    base = (rent or 0) + sum(f["amount"] for f in fees)
    matches = []
    for mask in range(1 << len(optional)):
        subset = [o for i, o in enumerate(optional) if mask >> i & 1]
        if abs(base + sum(o["amount"] for o in subset) - subtotal) <= 1.0:
            matches.append(subset)
    return matches[0] if len(matches) == 1 else []


def _json_content(text):
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise AdapterError("ResCMS yanıtı JSON değil.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("content"), str):
        raise AdapterError("ResCMS yanıtında içerik alanı yok.")
    return data["content"]


# --- Track (bookingEngine on the company's own domain) -----------------------------------------------------------------

class Track:
    """Track bookingEngine pages: hidden propertyID fields on the page; the front end posts them with the dates to ajax/quote
    and shows the returned HTML price breakdown, 'No' for unavailable dates or an alert text (e.g. a minimum stay).

    The page also carries the listing's availability calendar (td.available / booked / check-in / check-out with data-date);
    its date picker only lets a visitor choose free nights. Some Track sites price any dates in ajax/quote without checking
    availability (seen on panhandlegetaways.com, 8 Oct 2026), so a window whose nights the page calendar shows as taken is
    recorded as unavailable from that calendar and not priced."""

    name = "track"
    sends_guests = False        # the page's quote request carries no guest count
    FIELDS = ("propertyID", "roomTypeID", "propertyName", "hash")
    TAKEN = ("booked", "check-in")      # a night that starts someone else's stay; a check-out morning leaves the night free

    def parse_page(self, html, url):
        fields = {}
        for tag in re.findall(r"<input[^>]+>", html):
            name = re.search(r'name="([^"]+)"', tag)
            value = re.search(r'value="([^"]*)"', tag)
            if name and name.group(1) in self.FIELDS and 'type="hidden"' in tag and name.group(1) not in fields:
                fields[name.group(1)] = unescape(value.group(1)) if value else ""
        if not re.fullmatch(r"\d+", fields.get("propertyID") or ""):
            return None
        folder = re.search(r"siteFolder\s*=\s*'([^']*)'", html)
        ending = re.search(r"siteURLEnding\s*=\s*'([^']*)'", html)
        calendar = {}
        for classes, day in re.findall(r'<td class="([^"]*)" data-date="(\d{2}/\d{2}/\d{4})"', html):
            month, dom, year = day.split("/")
            calendar[f"{year}-{month}-{dom}"] = classes.split()
        return {"site_id": fields["propertyID"], "fields": fields, "page_url": url, "calendar": calendar,
                "quote_url": urljoin(url, (folder.group(1) if folder else "/") + "ajax/quote" + (ending.group(1) if ending else ""))}

    def taken_nights(self, info, window):
        """Nights of the window the page calendar shows as taken, or None when the calendar does not cover every night."""
        calendar = info.get("calendar") or {}
        nights = [date.fromordinal(window["checkin_date"].toordinal() + n).isoformat() for n in range(window["nights"])]
        if not all(night in calendar for night in nights):
            return None
        return [night for night in nights if any(mark in calendar[night] for mark in self.TAKEN)]

    def quote(self, session, info, window, guests=DEFAULT_GUESTS):
        taken = self.taken_nights(info, window)
        if taken:
            return {**outcome("unavailable", f"İlan sayfasının müsaitlik takvimi bu pencerenin {len(taken)} gecesini dolu gösteriyor "
                                             f"({taken[0]} …); fiyat sorulmadı.", available=0), "replies": []}
        reply = session.request("POST", info["quote_url"], data={"checkin": us_date(window["checkin_date"]), "checkout": us_date(window["checkout_date"]),
                                                                **info["fields"]},
                                headers={"X-Requested-With": "XMLHttpRequest", "Referer": info["page_url"]},
                                note=f"track-quote-{info['site_id']}-{window['window_key']}")
        if reply.status != 200:
            raise AdapterError(f"Fiyat isteği HTTP {reply.status} döndü.")
        text = reply.text.strip()
        if text == "No":
            return {**outcome("unavailable", "Sorry, this property is not available for the selected dates.", available=0), "replies": [reply]}
        if text == "API Error":
            return {**outcome("error", "Site: there was a problem retrieving availability info for this property."), "replies": [reply]}
        if "pdp-quote-list" in text:
            return {**self.parse_quote(text), "replies": [reply]}
        message = plain_text(text)
        status, nights = stay_message(message)
        if not message:
            raise AdapterError("Fiyat yanıtı boş.")
        return {**outcome(status, message, available=0 if status == "unavailable" else None, min_stay=nights),
                "rule_source": "yanıt" if nights else None, "replies": [reply]}

    @staticmethod
    def parse_quote(text):
        tree = Tree(text).root
        lists = tree.find("ul", cls="pdp-quote-list")
        if not lists:
            raise AdapterError("Fiyat dökümü listesi yok.")
        items = []
        for item in (c for c in lists[0].children if getattr(c, "tag", None) == "li"):
            price = next(iter(item.find("span", cls="pdp-quote-item-price")), None)
            label = next(iter(item.find("span", cls="pdp-quote-item-text")), None)
            sub = item.find("ul", cls="pdp-quote-item-toggle-list")
            if label is None or price is None:
                continue
            entry = {"name": clean(label.text()), "amount": money(price.attrs.get("data-price")), "total": "pdp-quote-total" in item.attrs.get("class", ""),
                     "parts": [{"name": clean(next(iter(li.find("span", cls="pdp-quote-item-text"))).text()),
                                "amount": money(next(iter(li.find("span", cls="pdp-quote-item-price"))).attrs.get("data-price"))}
                               for li in (sub[0].find("li") if sub else []) if li.find("span", cls="pdp-quote-item-text") and li.find("span", cls="pdp-quote-item-price")]}
            items.append(entry)
        rent = next((i["amount"] for i in items if not i["total"] and re.match(r"rent\b|lodging", i["name"] or "", re.I)), None)
        total = next((i["amount"] for i in items if i["total"]), None)
        fees, taxes = [], []
        for item in items:
            if item["total"] or item["amount"] == rent and re.match(r"rent\b|lodging", item["name"] or "", re.I):
                continue
            target = taxes if re.search(r"tax", item["name"] or "", re.I) else fees
            target.extend(item["parts"] or [{"name": item["name"], "amount": item["amount"]}])
        if rent is None and total is None:
            raise AdapterError("Fiyat dökümünde kira veya toplam yok.")
        return breakdown(rent, [f for f in fees if f["amount"] is not None], None, total,
                         tax_items=[t for t in taxes if t["amount"] is not None], currency=currency_of(text))


# --- Streamline (WordPress streamline-core plugin) -------------------------------------------------------------------------

class Streamline:
    """Streamline plugin pages: the unit id and the site's admin-ajax address are on the page. The front end first asks
    VerifyPropertyAvailability (a 'status' answer is the site's refusal text), then GetPreReservationPrice with separate taxes."""

    name = "streamline"
    sends_guests = True

    def parse_page(self, html, url):
        unit = re.search(r"getRatesDetails\((\d+)\)|getCalendarDataNew\((\d+)\)", html)
        ajax = re.search(r'streamlinecoreConfig\s*=\s*\{"ajaxUrl":"([^"]+)"', html)
        if not unit or not ajax:
            return None
        return {"site_id": next(g for g in unit.groups() if g), "ajax_url": ajax.group(1).replace("\\/", "/"), "page_url": url}

    def call(self, session, info, method, params, note):
        reply = session.request("POST", info["ajax_url"], params={"action": "streamlinecore-api-request",
                                                                 "params": json.dumps({"methodName": method, "params": params})},
                                headers={"Content-Type": "application/json", "Referer": info["page_url"]}, note=note)
        if reply.status != 200:
            raise AdapterError(f"{method} HTTP {reply.status} döndü.")
        try:
            data = json.loads(reply.text)
        except ValueError as exc:
            raise AdapterError(f"{method} yanıtı JSON değil.") from exc
        if not isinstance(data, dict):
            raise AdapterError(f"{method} yanıtı beklenen biçimde değil.")
        return reply, data

    def inventory(self, session, origin, options):
        """Every unit the plugin lists (GetPropertyListWordPress): id, page, coordinates, bedrooms and bathrooms (full + ½ per half
        bath). The list has no address field; its location name is taken as the street address only when it is one (a street
        number first, optionally after "Name |"), so a company whose location names are addresses matches by address."""
        ajax_url = origin + "/wp-admin/admin-ajax.php"
        reply, data = self.call(session, {"ajax_url": ajax_url, "page_url": origin + "/"}, "GetPropertyListWordPress", {}, "streamline-inventory")
        rows = (data.get("data") or {}).get("property") if isinstance(data.get("data"), dict) else None
        if not isinstance(rows, list):
            raise AdapterError("GetPropertyListWordPress yanıtında ilan listesi yok.")
        units = []
        for row in rows:
            if not isinstance(row, dict) or not str(row.get("id") or "").isdigit():
                continue
            page = urljoin(origin + "/", (row.get("seo_page_name") or "").strip("/") + "/")
            full, half = number(row.get("bathrooms_number")), number(row.get("half_bathroom_count")) or 0
            location = (clean(row.get("location_name")) or "").split("|")[-1].strip()
            units.append({"site_id": str(row["id"]), "url": page, "title": clean(row.get("name")),
                          "address": location if normalize_address(location) else None, "city": clean(row.get("city")),
                          "latitude": number(row.get("latitude")), "longitude": number(row.get("longitude")),
                          "bedrooms": number(row.get("bedrooms_number")), "bathrooms": None if full is None else full + 0.5 * half,
                          "sleeps": number(row.get("max_occupants")),
                          "info": {"site_id": str(row["id"]), "ajax_url": ajax_url, "page_url": page}})
        return units, [reply]

    def quote(self, session, info, window, guests=DEFAULT_GUESTS):
        base = {"unit_id": int(info["site_id"]), "startdate": us_date(window["checkin_date"]), "enddate": us_date(window["checkout_date"]),
                "occupants": guests["adults"], "occupants_small": guests["children"], "pets": 0}
        first, data = self.call(session, info, "VerifyPropertyAvailability", {**base, "use_room_type_logic": 0, "include_coupon_information": 1},
                                f"streamline-verify-{info['site_id']}-{window['window_key']}")
        status = data.get("status")
        if isinstance(status, dict):
            message = clean(f"{status.get('description') or ''} ({status.get('code') or 'kod yok'})")
            kind, nights = stay_message(status.get("description"))
            return {**outcome(kind, message, available=0 if kind == "unavailable" else None, min_stay=nights),
                    "rule_source": "yanıt" if nights else None, "replies": [first]}
        second, data = self.call(session, info, "GetPreReservationPrice", {**base, "separate_taxes": 1},
                                 f"streamline-price-{info['site_id']}-{window['window_key']}")
        if isinstance(data.get("status"), dict):
            return {**outcome("no_price", clean(data["status"].get("description"))), "replies": [first, second]}
        body = data.get("data")
        if not isinstance(body, dict) or money(body.get("price")) is None:
            raise AdapterError("GetPreReservationPrice yanıtında fiyat yok.")
        fees = [{"name": clean(f.get("name")) or "Fee", "amount": money(f.get("value"))} for f in body.get("required_fees") or [] if isinstance(f, dict)]
        taxes = [{"name": clean(t.get("name")) or "Tax", "amount": money(t.get("value"))} for t in body.get("taxes_details") or [] if isinstance(t, dict)]
        optional = [{"name": clean(f.get("name")), "amount": money(f.get("value")), "reason": "sitede isteğe bağlı, seçilmemiş"}
                    for f in body.get("optional_fees") or [] if isinstance(f, dict) and not f.get("active")]
        nightly = [{"date": _iso(d.get("date")), "price": money(d.get("price"))} for d in body.get("reservation_days") or [] if isinstance(d, dict)]
        rent = money(body.get("price"))
        discount = money(body.get("coupon_discount")) or 0
        if discount:
            fees.append({"name": "Coupon discount", "amount": -abs(discount)})
        result = breakdown(rent, [f for f in fees if f["amount"] is not None], None, money(body.get("total")),
                           tax_items=[t for t in taxes if t["amount"] is not None], excluded=optional,
                           nightly=[n for n in nightly if n["date"] and n["price"] is not None], currency=clean(body.get("currency")))
        return {**result, "replies": [first, second]}


def _iso(text):
    match = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", text or "")
    return f"{match.group(3)}-{match.group(1)}-{match.group(2)}" if match else None


# --- "vacation-rentals/router" WordPress sites ----------------------------------------------------------------------------

class VacationRentalsRouter:
    """Sites whose front end posts {call: 'getPrice', unitId, people, arrive, depart, nights} to /vacation-rentals/router/ and
    shows rent, fees, taxes and bookingTotal; an unavailable answer carries isAvailable=false and the site's errorMsg."""

    name = "vr_router"
    sends_guests = True

    def parse_page(self, html, url):
        unit = re.search(r"unitId['\"]?\s*[:=]\s*['\"]([0-9]+-[0-9]+|[0-9]+|[0-9a-f]{24})['\"]", html) or re.search(r"/vacation-rentals/rental/([0-9]+-[0-9]+)/", url)
        router = re.search(r"['\"](https?://[^'\"]+/vacation-rentals)['\"]\s*\+\s*['\"]/router/['\"]", html)
        if not unit or "/vacation-rentals/router/" not in html and not router:
            return None
        origin = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}"
        return {"site_id": unit.group(1), "router_url": (router.group(1) + "/router/") if router else origin + "/vacation-rentals/router/", "page_url": url}

    def unit_fields(self, html):
        """propDetails on the listing page: street address (+ address2), city, coordinates ('geocode'), bedrooms, bathrooms (full and
        three-quarter baths count as full, a half bath as ½) and sleeps."""
        match = re.search(r"propDetails\s*:\s*\{", html)
        try:
            data = json.JSONDecoder().raw_decode(html, match.end() - 1)[0] if match else None
        except ValueError:
            data = None
        if not isinstance(data, dict):
            return json_ld_unit(html)
        geocode = re.fullmatch(r"\s*(-?[0-9.]+)\s*,\s*(-?[0-9.]+)\s*", str(data.get("geocode") or ""))
        full, half, three = number(data.get("bath")), number(data.get("half_bath")) or 0, number(data.get("three_fourths_bath")) or 0
        address = " ".join(part for part in (clean(data.get("address")), clean(data.get("address2"))) if part) or None
        return {"address": address, "city": clean(data.get("city")), "latitude": number(geocode.group(1)) if geocode else None,
                "longitude": number(geocode.group(2)) if geocode else None, "bedrooms": number(data.get("bed")),
                "bathrooms": None if full is None else full + three + 0.5 * half, "sleeps": number(data.get("sleeps")),
                "title": clean(data.get("prop_name"))}

    def quote(self, session, info, window, guests=DEFAULT_GUESTS):
        reply = session.request("POST", info["router_url"], json={"call": "getPrice", "unitId": info["site_id"], "people": guests["adults"] + guests["children"],
                                                                 "arrive": us_date(window["checkin_date"], padded=False),
                                                                 "depart": us_date(window["checkout_date"], padded=False), "nights": window["nights"],
                                                                 "optIn": False, "promoCode": "", "sdpBool": False},
                                headers={"Accept": "application/json, text/plain, */*", "Referer": info["page_url"]},
                                note=f"router-price-{info['site_id']}-{window['window_key']}")
        if reply.status != 200:
            raise AdapterError(f"Fiyat isteği HTTP {reply.status} döndü.")
        try:
            data = json.loads(reply.text)
        except ValueError as exc:
            raise AdapterError("getPrice yanıtı JSON değil.") from exc
        if not isinstance(data, dict):
            raise AdapterError("getPrice yanıtı beklenen biçimde değil.")
        if data.get("apiError"):
            return {**outcome("error", clean(data.get("errorMsg")) or "Site fiyat servisinde hata bildirdi."), "replies": [reply]}
        if data.get("isAvailable") is False:
            kind, nights = stay_message(data.get("errorMsg"))
            return {**outcome(kind, clean(data.get("errorMsg")), available=0 if kind == "unavailable" else None, min_stay=nights),
                    "rule_source": "yanıt" if nights else None, "replies": [reply]}
        if data.get("isAvailable") is not True:
            raise AdapterError("getPrice yanıtında müsaitlik bilgisi yok.")
        fees = [{"name": clean(f.get("name")) or "Fee", "amount": money(f.get("amount"))} for f in data.get("fees") or [] if isinstance(f, dict)]
        taxes = [{"name": clean(t.get("name")) or "Tax", "amount": money(t.get("amount"))} for t in data.get("taxes") or [] if isinstance(t, dict)]
        for key, label in (("travelInsurance", "Travel insurance"), ("damageProtection", "Damage protection")):
            if isinstance(data.get(key), dict) and money(data[key].get("amount")):
                fees.append({"name": clean(data[key].get("name")) or label, "amount": money(data[key].get("amount"))})
        discount = money(data.get("discount")) or 0
        if discount:
            fees.append({"name": "Discount", "amount": -abs(discount)})
        excluded = [{"name": clean(e.get("name")), "amount": money(e.get("amount")), "reason": "sitede ayrı gösterilen isteğe bağlı kalem"}
                    for e in data.get("extraneousPricing") or [] if isinstance(e, dict)]
        result = breakdown(money(data.get("rent")), [f for f in fees if f["amount"] is not None], None, money(data.get("bookingTotal")),
                           tax_items=[t for t in taxes if t["amount"] is not None], excluded=excluded, currency="USD")
        return {**result, "replies": [reply]}


def json_of(reply, what):
    try:
        return json.loads(reply.text)
    except ValueError as exc:
        raise AdapterError(f"{what} yanıtı JSON değil.") from exc


def origin_of(url):
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def site_answer(message):
    """A site's refusal text -> (status, min_stay). A date the company has not opened for booking yet is 'no_price'."""
    text = clean(message) or ""
    if re.search(r"maximum notice|beyond the|too far|not (?:yet )?(?:open|available) for booking|rates? (?:are )?not (?:yet )?available", text, re.I):
        return "no_price", None
    return stay_message(text)


def refusal(message, replies, **extra):
    status, nights = site_answer(message)
    return {**outcome(status, clean(message), available=0 if status == "unavailable" else None, min_stay=nights),
            "rule_source": "yanıt" if nights else None, "replies": replies, **extra}


# --- VRPConnect (Gueststream "vrp" WordPress plugin) ---------------------------------------------------------------------

class VRP:
    """VRPConnect pages (/vrp/unit/<name>-<id>-<n>): the page's #bookingform carries the unit id and the field names the front end
    sends; its checkAvailability asks /?vrpjax=1&act=checkavailability with the form and shows the returned charges. The plugin's
    search (act=search, json) lists every unit with street address, city, coordinates, bedrooms and bathrooms."""

    name = "vrp"
    sends_guests = True

    def parse_page(self, html, url):
        form = re.search(r'<form[^>]+id="bookingform"[^>]*>(.*?)</form>', html, re.S | re.I)
        if not form:
            return None
        fields = {}
        for tag in re.findall(r"<(?:input|select)[^>]*>", form.group(1)):
            name = re.search(r'name="([^"]+)"', tag)
            value = re.search(r'value="([^"]*)"', tag)
            if name and name.group(1).startswith(("obj[", "search[")) and name.group(1) not in fields:
                fields[name.group(1)] = unescape(value.group(1)) if value and tag.startswith("<input") else ""
        if not re.fullmatch(r"\d+", fields.get("obj[PropID]") or ""):
            return None
        return {"site_id": fields["obj[PropID]"], "fields": fields, "page_url": url, "origin": origin_of(url)}

    def quote(self, session, info, window, guests=DEFAULT_GUESTS):
        fields = dict(info["fields"])
        fields.update({"obj[Arrival]": us_date(window["checkin_date"]), "obj[Departure]": us_date(window["checkout_date"])})
        adults = "obj[Adults]" if "obj[Adults]" in fields else "search[Adults]"
        children = "obj[Children]" if "obj[Children]" in fields else "search[Children]"
        fields.update({adults: str(guests["adults"]), children: str(guests["children"])})
        if "obj[Pets]" in fields:
            fields["obj[Pets]"] = "No Pets"
        reply = session.request("GET", f"{info['origin']}/?vrpjax=1&act=checkavailability&par=1&{urlencode(fields)}",
                                headers={"Accept": "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest",
                                         "Referer": info["page_url"]}, note=f"vrp-quote-{info['site_id']}-{window['window_key']}")
        if reply.status != 200:
            raise AdapterError(f"Fiyat isteği HTTP {reply.status} döndü.")
        data = json_of(reply, "checkavailability")
        if not isinstance(data, dict):
            raise AdapterError("checkavailability yanıtı beklenen biçimde değil.")
        if data.get("Error"):
            return refusal(data["Error"], [reply])
        return {**self.parse_quote(data), "replies": [reply]}

    @staticmethod
    def parse_quote(data):
        charges = [c for c in data.get("Charges") or [] if isinstance(c, dict)]
        details = data.get("BookDetails") if isinstance(data.get("BookDetails"), dict) else {}
        tax_names = {clean(t.get("Description")) for t in details.get("tax") or [] if isinstance(t, dict)}
        rent, fees, taxes = None, [], []
        for charge in charges:
            label, amount = clean(charge.get("Description")) or "", money(charge.get("Amount"))
            if amount is None:
                continue
            if rent is None and re.fullmatch(r"rent|rental|lodging", label, re.I):
                rent = amount
            elif label in tax_names or re.search(r"\btax\b", label, re.I):
                taxes.append({"name": label, "amount": amount})
            else:
                fees.append({"name": label, "amount": amount})
        total = money(data.get("TotalCost"))
        if rent is None and total is None:
            raise AdapterError("checkavailability yanıtında kira veya toplam yok.")
        insurance = money(data.get("InsuranceAmount"))
        excluded = [{"name": "Travel insurance", "amount": insurance, "reason": "sitede isteğe bağlı; sitenin toplamına dahil değil"}] if insurance else []
        return breakdown(rent, fees, None, total, tax_items=taxes, excluded=excluded, currency="USD")

    def inventory(self, session, origin, options):
        query = {"vrpjax": "1", "act": "search", "search[json]": "1", "search[limit]": "1000", "search[show]": "1000",
                 "search[showmax]": "true", "showmax": "true"}
        reply = session.request("GET", f"{origin}/?{urlencode(query)}", headers={"Accept": "application/json"}, note="vrp-inventory")
        if reply.status != 200:
            raise AdapterError(f"İlan listesi HTTP {reply.status} döndü.")
        if "data-vrp-unitid" in reply.text:
            return self.inventory_cards(reply, origin), [reply]
        data = json_of(reply, "VRP arama")
        rows = data.get("results") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise AdapterError("VRP arama yanıtında ilan listesi yok.")
        if isinstance(data.get("count"), int) and data["count"] > len(rows):
            raise AdapterError(f"VRP arama yanıtı {data['count']} ilandan yalnız {len(rows)} tanesini verdi; liste eksik.")
        units = []
        for row in rows:
            if not isinstance(row, dict) or not str(row.get("id") or "").isdigit() or not row.get("page_slug"):
                continue
            units.append({"site_id": str(row["id"]), "url": f"{origin}/vrp/unit/{row['page_slug']}", "title": clean(row.get("Name")),
                          "address": clean(row.get("Address1")), "city": clean(row.get("City")), "latitude": number(row.get("lat")),
                          "longitude": number(row.get("long")), "bedrooms": number(row.get("Bedrooms")), "bathrooms": number(row.get("Bathrooms")),
                          "sleeps": number(row.get("Sleeps")), "info": None})
        return units, [reply]

    def inventory_cards(self, reply, origin):
        """Some themes answer the search with HTML result cards instead of JSON (seen on oversee.us): every card carries the unit
        in data-vrp-* attributes (unit id, page, street address, city, coordinates, beds, baths, sleeps)."""
        units = []
        for card in re.findall(r"<div\b[^>]*\bdata-vrp-unitid=[^>]*>", reply.text, re.S):
            value = lambda key: (lambda m: unescape(m.group(1)) if m else None)(re.search(rf'data-vrp-{key}="([^"]*)"', card))
            unit_id, url = value("unitid"), value("url")
            if not unit_id or not unit_id.isdigit() or not url:
                continue
            address, city = clean(value("address")), clean(value("city"))
            if address and city:       # "3604 E. Co Hwy 30A A-8 Santa Rosa Beach, FL": the street line without its city and state
                address = re.sub(rf"[\s,]+{re.escape(city)}\s*,?\s*(?:[A-Z]{{2}}\.?)?$", "", address, flags=re.I)
            units.append({"site_id": unit_id, "url": urljoin(origin + "/", url), "title": clean(value("name")),
                          "address": address, "city": city, "latitude": number(value("latitude")),
                          "longitude": number(value("longitude")), "bedrooms": number(value("beds")), "bathrooms": number(value("baths")),
                          "sleeps": number(value("sleeps")), "info": None})
        if not units:
            raise AdapterError("VRP arama yanıtında ilan kartı yok.")
        return units


# --- Company front ends with their own public quote services -------------------------------------------------------------

class PropertyQuoteV3:
    """A Vue front end (seen on southernresorts.com) whose listing page carries booking-data with the property id; choosing dates
    posts {unitId, arrivalDate, departureDate, occupants, promoCode, applyAutoPromoCode} to /property/v3/quote and shows the
    rent, fee and tax sections. A promotion the site applies by itself is kept as a negative line with its code."""

    name = "property_quote"
    sends_guests = True

    def parse_page(self, html, url):
        data = re.search(r'booking-data="([^"]+)"', html)
        try:
            info = json.loads(unescape(data.group(1))).get("propertyInfo") if data else None
        except ValueError:
            info = None
        if not isinstance(info, dict) or not str(info.get("propertyId") or "").isdigit():
            return None
        return {"site_id": str(info["propertyId"]), "page_url": url, "origin": origin_of(url)}

    def unit_fields(self, html):
        return json_ld_unit(html)

    def quote(self, session, info, window, guests=DEFAULT_GUESTS):
        body = {"unitId": info["site_id"], "arrivalDate": window["checkin_date"].isoformat(), "departureDate": window["checkout_date"].isoformat(),
                "occupants": {"adults": guests["adults"], "children": guests["children"], "pets": 0}, "promoCode": "", "applyAutoPromoCode": True}
        reply = session.request("POST", info["origin"] + "/property/v3/quote", json=body,
                                headers={"Accept": "*/*", "Referer": info["page_url"]}, note=f"v3-quote-{info['site_id']}-{window['window_key']}")
        try:
            data = json.loads(reply.text)
        except ValueError:
            data = None
        if reply.status != 200 or not isinstance(data, dict) or not isinstance(data.get("quote"), dict):
            messages = self.messages(data)
            if messages:
                return refusal(" ".join(messages), [reply])
            raise AdapterError(f"Fiyat isteği HTTP {reply.status} döndü; yanıtta fiyat yok.")
        return {**self.parse_quote(data["quote"]), "replies": [reply]}

    @staticmethod
    def messages(data):
        if not isinstance(data, dict):
            return []
        found = []
        for key in ("errors", "messages", "quoteErrors", "message", "error", "title", "detail"):
            value = data.get(key)
            if isinstance(value, str):
                found.append(value)
            elif isinstance(value, list):
                found.extend(str(v.get("message") if isinstance(v, dict) else v) for v in value)
            elif isinstance(value, dict):
                found.extend(str(v[0] if isinstance(v, list) and v else v) for v in value.values())
        return [clean(m) for m in found if clean(m)]

    @staticmethod
    def parse_quote(quote):
        sections = quote.get("sections") if isinstance(quote.get("sections"), dict) else {}
        def items(name):
            section = sections.get(name) if isinstance(sections.get(name), dict) else {}
            return section, [{"name": clean(i.get("label")), "amount": money(i.get("value"))} for i in section.get("items") or []
                             if isinstance(i, dict) and money(i.get("value")) is not None]
        rent_section, _ = items("rent")
        _, fees = items("fees")
        _, taxes = items("taxes")
        promo = quote.get("promoCode") if isinstance(quote.get("promoCode"), dict) else {}
        discount = money(quote.get("promoDiscount")) or 0
        if discount and promo.get("valid"):
            fees.append({"name": f"Promotion {clean(promo.get('name')) or ''} ({clean(quote.get('promoType')) or 'site'})".replace("  ", " "),
                         "amount": -abs(discount)})
        rent, total = money(rent_section.get("total")), money(quote.get("total"))
        if rent is None and total is None:
            raise AdapterError("Fiyat yanıtında kira veya toplam yok.")
        insurance = money(quote.get("travelInsurance"))
        excluded = [{"name": "Travel insurance", "amount": insurance, "reason": "sitede isteğe bağlı; sitenin toplamına dahil değil"}] if insurance else []
        return breakdown(rent, fees, None, total, tax_items=taxes, excluded=excluded, currency=currency_of(str(quote.get("total"))))


class ExceptionalStay:
    """Pages with the exceptionalStay front end (seen on exclusive30a.com): unitData.unitID on the page; the quote box asks
    GET /quote with the dates and guest counts and shows rent, required charges, taxes and grandTotal. Add-ons and travel
    insurance offered in the same answer are not part of grandTotal."""

    name = "exceptional_stay"
    sends_guests = True

    def parse_page(self, html, url):
        unit = re.search(r"unitData\s*=\s*\{\s*['\"]unitID['\"]\s*:\s*(\d+)", html)
        if not unit or "exceptionalStay" not in html and "/website/assets/js/main.js" not in html:
            return None
        return {"site_id": unit.group(1), "page_url": url, "origin": origin_of(url)}

    def unit_fields(self, html):
        return json_ld_unit(html)

    def quote(self, session, info, window, guests=DEFAULT_GUESTS):
        params = {"arrival": window["checkin_date"].isoformat(), "departure": window["checkout_date"].isoformat(), "pid": info["site_id"],
                  "numberOfAdult": str(guests["adults"]), "numberOfChild": str(guests["children"]), "numberOfPets": "0", "travelInsurance": "",
                  "promoCode": "", "action": "", "compositePropertyID": "", "nights": str(window["nights"]), "min_nights_stay_req": ""}
        reply = session.request("GET", info["origin"] + "/quote", params=params,
                                headers={"Accept": "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest",
                                         "Referer": info["page_url"]}, note=f"es-quote-{info['site_id']}-{window['window_key']}")
        if reply.status != 200:
            raise AdapterError(f"Fiyat isteği HTTP {reply.status} döndü.")
        data = json_of(reply, "quote")
        body = data.get("body") if isinstance(data, dict) and isinstance(data.get("body"), dict) else data
        if not isinstance(body, dict):
            raise AdapterError("quote yanıtı beklenen biçimde değil.")
        if body.get("result") != "success":
            return refusal(body.get("message") or body.get("error") or "Site fiyat vermedi.", [reply])
        return {**self.parse_quote(body), "replies": [reply]}

    @staticmethod
    def parse_quote(body):
        fees = [{"name": clean(c.get("displayName") or c.get("name")), "amount": money(c.get("value"))} for c in body.get("otherChargesItemized") or []
                if isinstance(c, dict) and (c.get("isRequired") or c.get("type") == "required") and money(c.get("value")) is not None]
        service = money(body.get("serviceFeeTotal")) or 0
        if service:
            fees.append({"name": "Service fee", "amount": service})
        discount = money(body.get("discount")) or 0
        if discount:
            fees.append({"name": "Discount", "amount": -abs(discount)})
        rent, total = money(body.get("guestDiscountedRent") or body.get("nightlyRates")), money(body.get("grandTotal"))
        if rent is None and total is None:
            raise AdapterError("quote yanıtında kira veya toplam yok.")
        return breakdown(rent, fees, money(body.get("taxes")), total, currency="USD")


class AsmxGetQuote:
    """Rental pages (seen on destinvacation.com) whose calendar posts {RentalId, Arrival, Departure, PromoCode} to
    /service.asmx/GetQuote and shows the returned charges (rent, cleaning, resort fees, tax, total). The request has no guest field."""

    name = "asmx_quote"
    sends_guests = False

    def parse_page(self, html, url):
        rental = re.search(r"rentalId\s*:\s*(\d+)", html)
        if not rental or "/service.asmx" not in html and "property-calendar" not in html:
            return None
        return {"site_id": rental.group(1), "page_url": url, "origin": origin_of(url)}

    def unit_fields(self, html):
        return json_ld_unit(html)

    def quote(self, session, info, window, guests=DEFAULT_GUESTS):
        body = {"RentalId": int(info["site_id"]), "Arrival": us_date(window["checkin_date"], padded=False),
                "Departure": us_date(window["checkout_date"], padded=False), "PromoCode": ""}
        reply = session.request("POST", info["origin"] + "/service.asmx/GetQuote", json=body,
                                headers={"Accept": "application/json, text/javascript, */*; q=0.01", "Referer": info["page_url"]},
                                note=f"asmx-quote-{info['site_id']}-{window['window_key']}")
        if reply.status != 200:
            raise AdapterError(f"Fiyat isteği HTTP {reply.status} döndü.")
        data = json_of(reply, "GetQuote")
        result = data.get("d") if isinstance(data, dict) else None
        if not isinstance(result, dict):
            raise AdapterError("GetQuote yanıtı beklenen biçimde değil.")
        if not result.get("IsAvailable"):
            return refusal(result.get("Message") or "Not available", [reply])
        rent, total, taxes, fees = None, None, None, []
        for charge in result.get("Charge") or []:
            if not isinstance(charge, dict):
                continue
            label, amount = clean(charge.get("Charge")) or "", money(charge.get("Amount"))
            if amount is None or re.search(r"deposit|due", label, re.I):
                continue
            if re.fullmatch(r"total", label, re.I):
                total = amount
            elif re.fullmatch(r"tax(es)?", label, re.I):
                taxes = amount
            elif rent is None and re.match(r"rent", label, re.I):
                rent = amount
            else:
                fees.append({"name": label, "amount": amount})
        if rent is None and total is None:
            raise AdapterError("GetQuote yanıtında kira veya toplam yok.")
        return {**breakdown(rent, fees, taxes, total, currency="USD"), "replies": [reply]}


class Wander:
    """Websites built on Wander's SaaS (seen on 30abeachstays.com): the page's <html data-website-id> and the property id in the
    url; the booking box posts the stay to api.wander.com .../listings/<id>/estimate and shows the total (amounts in cents)."""

    name = "wander"
    sends_guests = True
    api_hosts = ("api.wander.com",)
    API = "https://api.wander.com/saas/website/listings/{}/estimate"

    def parse_page(self, html, url):
        website = re.search(r'<html[^>]+data-website-id="(\d+)"', html)
        unit = re.search(r"/property/(\d+)(?:/|$)", url)
        if not website or not unit:
            return None
        return {"site_id": unit.group(1), "website_id": website.group(1), "page_url": url, "origin": origin_of(url)}

    def unit_fields(self, html):
        return json_ld_unit(html)

    def quote(self, session, info, window, guests=DEFAULT_GUESTS):
        body = {"checkIn": window["checkin_date"].isoformat(), "checkOut": window["checkout_date"].isoformat(), "paymentType": "FULL",
                "pricingSurface": "CALENDAR", "numberOfGuests": guests["adults"] + guests["children"], "numberOfPets": 0}
        reply = session.request("POST", self.API.format(info["site_id"]), json=body,
                                headers={"Accept": "application/json", "X-Website-Id": info["website_id"], "X-Wander-Client": "wander-customer-website",
                                         "Origin": info["origin"], "Referer": info["page_url"]},
                                note=f"wander-estimate-{info['site_id']}-{window['window_key']}")
        try:
            data = json.loads(reply.text)
        except ValueError:
            data = None
        estimate = data.get("estimate") if isinstance(data, dict) else None
        if reply.status != 200 or not isinstance(estimate, dict):
            message = data.get("message") if isinstance(data, dict) else None
            code = data.get("code") if isinstance(data, dict) else None
            if code == "DATES_NOT_BOOKABLE":       # the site does not say why (booked, rules or not open): no price, availability unknown
                return {**outcome("no_price", f"Site: {message or ''} ({code}); tarihler bu sitede rezerve edilemiyor."), "replies": [reply]}
            if message:
                return refusal(f"{message} ({code})" if code else message, [reply])
            raise AdapterError(f"Fiyat isteği HTTP {reply.status} döndü; yanıtta fiyat yok.")
        cents = lambda value: None if money(value) is None else round(money(value) / 100, 2)
        rent, with_fees = cents(estimate.get("totalNightsPrice")), cents(estimate.get("totalWithFees"))
        taxes_block = estimate.get("taxes") if isinstance(estimate.get("taxes"), dict) else {}
        tax_items = [{"name": clean(t.get("name")) or "Tax", "amount": cents(t.get("amount"))} for t in taxes_block.get("breakdown") or []
                     if isinstance(t, dict) and cents(t.get("amount")) is not None]
        fees = []
        if rent is not None and with_fees is not None and round(with_fees - rent, 2):
            fees.append({"name": "Fees (the site's single fee total)", "amount": round(with_fees - rent, 2)})
        coupon = cents(estimate.get("couponOff")) or 0
        if coupon:
            fees.append({"name": "Coupon", "amount": -abs(coupon)})
        result = breakdown(rent, fees, cents(taxes_block.get("total")), cents(estimate.get("total")), tax_items=tax_items,
                           currency=clean(data.get("currency")))
        return {**result, "replies": [reply]}


class Q4VR:
    """WordPress sites with the Q4VR plugin (Escapia; seen on yourfriendatthebeach.com). The page's search form asks admin-ajax
    action=q4vr_stay for a stay; the date picker reads q4vr_availability, which also carries the site's published nightly rent
    range per season (base_rate, taxes and fees excluded). The range is kept apart as a published rent, never as a quote."""

    name = "qvr"         # Q4VR (digits are not allowed in adapter names)
    sends_guests = True

    def parse_page(self, html, url):
        unit = re.search(r'name="unit_code"\s+value="([0-9]+-[0-9]+)"', html) or re.search(r'id="unitCode"[^>]*value="([0-9]+-[0-9]+)"', html)
        ajax = re.search(r'VRAjax\s*=\s*\{"ajaxurl":"([^"]+)"', html)
        if not unit or not ajax:
            return None
        return {"site_id": unit.group(1), "ajax_url": ajax.group(1).replace("\\/", "/"), "page_url": url, "origin": origin_of(url)}

    def unit_fields(self, html):
        return json_ld_unit(html)

    def quote(self, session, info, window, guests=DEFAULT_GUESTS):
        params = {"post_type": "vacation_rental", "s": "", "action": "q4vr_stay", "unit_code": info["site_id"],
                  "start_date": us_date(window["checkin_date"]), "end_date": us_date(window["checkout_date"]),
                  "guests": f"{guests['adults']},{guests['children']},0"}
        reply = session.request("GET", info["ajax_url"], params=params, headers={"Accept": "application/json", "Referer": info["page_url"]},
                                note=f"q4vr-stay-{info['site_id']}-{window['window_key']}")
        if reply.status != 200:
            raise AdapterError(f"Fiyat isteği HTTP {reply.status} döndü.")
        data = json_of(reply, "q4vr_stay")
        content = data.get("data") if isinstance(data, dict) else None
        if not isinstance(content, str):
            raise AdapterError("q4vr_stay yanıtında içerik yok.")
        errors = re.findall(r'class="[^"]*stay-error-list-item[^"]*"[^>]*>(.*?)</li>', content, re.S)
        if errors:
            message = "; ".join(plain_text(e) for e in errors)
            if re.search(r"not authorized", message, re.I):
                return {**outcome("no_price", f"Sitenin fiyat servisi hata verdi: {message}"), "replies": [reply]}
            return refusal(message, [reply])
        return {**outcome("no_price", "Sitenin fiyat yanıtı tanınmadı; fiyat alınmadı."), "replies": [reply]}

    def published(self, session, info, windows):
        """{window_key: published rent row} from the date picker's seasons: a window counts only when its whole stay lies in one season."""
        reply = session.request("GET", info["ajax_url"], params={"action": "q4vr_availability", "unit_code": info["site_id"]},
                                headers={"Accept": "application/json", "Referer": info["page_url"]}, note=f"q4vr-availability-{info['site_id']}")
        if reply.status != 200:
            raise AdapterError(f"Takvim isteği HTTP {reply.status} döndü.")
        data = json_of(reply, "q4vr_availability")
        seasons = (data.get("data") or {}).get("minimumNights") if isinstance(data, dict) and isinstance(data.get("data"), dict) else None
        rows = {}
        for window in windows:
            first, last = window["checkin_date"].isoformat(), date.fromordinal(window["checkout_date"].toordinal() - 1).isoformat()
            season = next((s for s in seasons or [] if isinstance(s, dict) and (s.get("start_date") or "") <= first and last <= (s.get("end_date") or "")), None)
            if not season:
                continue
            amounts = [money(part) for part in re.findall(r"\$[0-9,]+(?:\.\d+)?", season.get("base_rate") or "")]
            amounts = [a for a in amounts if a]
            if not amounts or (season.get("type") or "").lower() not in ("nightly", "weekly"):
                continue
            weekly = (season.get("type") or "").lower() == "weekly"
            low, high = min(amounts), max(amounts)
            factor = window["nights"] / 7 if weekly else window["nights"]
            rows[window["window_key"]] = {
                "season_start": season.get("start_date"), "season_end": season.get("end_date"), "rate_text": clean(season.get("base_rate")),
                "rate_period": "week" if weekly else "night", "rent_low": round(low * factor, 2), "rent_high": round(high * factor, 2),
                "basis": (f"Sitenin {season.get('start_date')}–{season.get('end_date')} sezonu için yayımladığı "
                          f"{'haftalık' if weekly else 'gecelik'} kira aralığı {clean(season.get('base_rate'))}; pencere tutarı = aralık × "
                          f"{'gece/7' if weekly else 'gece sayısı'} (bizim hesabımız; vergi ve ücretler hariç)."),
                "source_url": reply.url, "raw_sha256": [reply.sha256]}
        return rows


ADAPTERS = {adapter.name: adapter for adapter in (ResCMS(), Track(), Streamline(), VacationRentalsRouter(), VRP(), PropertyQuoteV3(),
                                                  ExceptionalStay(), AsmxGetQuote(), Wander(), Q4VR())}
