"""Rental-platform adapters for the agency rate collector: find the platform's listing identity on a company listing page and
ask the price/availability display the site's own front end asks, for one date window.

Destination-independent: an adapter knows a reservation platform (ResCMS, Track, Streamline, "vacation-rentals/router"), never a
company. Which company site uses which adapter comes from the destination configuration. Only fields the site shows are
filled; everything else stays None. Amounts are the site's own numbers; sums and checks are labelled as ours.
"""
import json
import re
from datetime import date
from html import unescape
from urllib.parse import urljoin, urlsplit

from .html_tree import Tree

GUESTS = 2          # the price display asks for a guest count; two adults, no children or pets


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

    def quote(self, session, info, window):
        checkin, checkout = window["checkin_date"], window["checkout_date"]
        min_stay, days = self.rules(info, checkin)
        params = {"rcav[begin]": us_date(checkin), "rcav[end]": us_date(checkout), "rcav[flex_type]": "d", "rcav[adult]": str(GUESTS),
                  "rcav[child]": "0", "rcav[eid]": info["site_id"]}
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
        tree = Tree(content).root
        rent, fees, taxes, total, excluded, currency = None, [], [], None, [], None
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
                else:
                    fees.append({"name": label, "amount": amount})
        if rent is None and total is None:
            raise AdapterError("Ayrıntılı fiyat tablosunda kira veya toplam satırı yok.")
        return breakdown(rent, fees, None, total, tax_items=taxes, excluded=excluded, currency=currency)


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

    def quote(self, session, info, window):
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

    def quote(self, session, info, window):
        base = {"unit_id": int(info["site_id"]), "startdate": us_date(window["checkin_date"]), "enddate": us_date(window["checkout_date"]),
                "occupants": GUESTS, "occupants_small": 0, "pets": 0}
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

    def parse_page(self, html, url):
        unit = re.search(r"unitId['\"]?\s*[:=]\s*['\"]([0-9]+-[0-9]+|[0-9]+)['\"]", html) or re.search(r"/vacation-rentals/rental/([0-9]+-[0-9]+)/", url)
        router = re.search(r"['\"](https?://[^'\"]+/vacation-rentals)['\"]\s*\+\s*['\"]/router/['\"]", html)
        if not unit or "/vacation-rentals/router/" not in html and not router:
            return None
        origin = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}"
        return {"site_id": unit.group(1), "router_url": (router.group(1) + "/router/") if router else origin + "/vacation-rentals/router/", "page_url": url}

    def quote(self, session, info, window):
        reply = session.request("POST", info["router_url"], json={"call": "getPrice", "unitId": info["site_id"], "people": GUESTS,
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


ADAPTERS = {adapter.name: adapter for adapter in (ResCMS(), Track(), Streamline(), VacationRentalsRouter())}
