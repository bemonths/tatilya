"""Book>Direct lodging search snapshots: which listings a dated search shows, with size and the price fields the source gives.

Destination-independent: Book>Direct runs the "Stay" front ends of several tourism bureaus. The clone host, the mapping of
the clone's location filters to canonical regions and the sample date windows come from SQLite configuration.
A search result is a labelled snapshot of one date window, never a full inventory.

The front end's public client key is read from the clone's current front-end bundle on every run (the versioned bundle
path is resolved from the entry HTML), kept in memory only and never written to a file, the database, a raw record or a log.
"""
import gzip
import hashlib
import json
import re
import statistics
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from .base import CollectionCanceled, CollectionResult, SourceError
from .climate_http import Reader, check, make_client, pause
from .price_history import annotate_windows, compare, season_groups
from .windows import monthly_windows

CONNECTOR_VERSION = "bookdirect-lodging/2"
API_HOST = "admin.bookdirect.net"
FRONT_SUFFIX = ".bookdirect.net"
BASE_HREF = re.compile(r'<base\s+href="(/[0-9A-Za-z_./-]*)"')
BUNDLE_SRC = re.compile(r'<script[^>]+src="([^"]*bookdirect[^"]*\.js)"')
CLIENT_KEY = re.compile(r'auth_token\s*:\s*"([^"\\]{8,200})"')
REQUEST_GAP = 1.25          # seconds between sequential requests
PER_PAGE = 50
MAX_PAGES = 100             # per window and location filter
# The front end asks again while an answer is pending, waiting 1 s + 0.75 s x attempt, up to 20 times; we stop after 5.
LIVE_BATCH, LIVE_ATTEMPTS, LIVE_PAUSE, LIVE_BACKOFF = 50, 5, 1.0, 0.75
CALENDAR_DAYS = 365
# A search whose total changes between its pages (a listing added or removed meanwhile) is read again from page 1, after a pause.
SEARCH_ATTEMPTS, SEARCH_RETRY_PAUSE = 3, 20.0
CALENDAR_MISSING = (400, 404, 422)   # a listing whose calendar the source does not serve is recorded, not a failed run
MAX_BYTES = 8_000_000
JSON_TYPES = {"application/json"}
SCOPE = ("Book>Direct aramalarında belirli tarihlerde görünen ilanlar; tam envanter değildir. Fiyatlar kaynağa göre en düşük müsait "
         "günlük fiyata dayanır; vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.")
PRICE_SOURCES = ("liste", "canli", "takvim")


def is_front_host(host):
    return isinstance(host, str) and host.endswith(FRONT_SUFFIX) and host != API_HOST and re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)*", host) is not None


def source_host(url):
    """The clone front-end host of a source URL like https://<clone>.bookdirect.net/, or None."""
    match = re.fullmatch(r"https://([a-z0-9.-]+)/?", url or "")
    return match.group(1) if match and is_front_host(match.group(1)) else None


class KeyedReader(Reader):
    """Reader that never stores a body containing the client key and keeps responses gzip-compressed.

    The manifest is flushed every few responses and at the end; raw_sha256 is the hash of the uncompressed body.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret = None
        self.request_gap = REQUEST_GAP
        self.unsaved = 0

    def save(self, requested, response, body, suffix, note):
        sequence = len(self.manifest["responses"]) + 1
        stamp = datetime.now(timezone.utc).isoformat()
        entry = {"sequence": sequence, "note": note, "requested_url": requested, "final_url": str(response.url),
                 "status": response.status_code, "content_type": response.headers.get("content-type"), "fetched_at": stamp,
                 "raw_sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        if self.secret and self.secret.encode() in body or note == "front-end-bundle":
            entry["raw_file"] = None
            entry["withheld"] = "Yanıt ön yüzün istemci anahtarını içerdiği için saklanmadı."
        else:
            relative = f"responses/{sequence:05d}{suffix}.gz"
            target = self.path.parent / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(gzip.compress(body, mtime=0))
            entry["raw_file"], entry["compression"] = relative, "gzip"
        self.manifest["fetched_at"] = stamp
        self.manifest["responses"].append(entry)
        self.unsaved += 1
        if self.unsaved >= 25:
            self.flush()

    def scrub(self):
        """Drop any stored response that turns out to contain the key (responses saved before the key was known)."""
        for entry in self.manifest["responses"]:
            if entry.get("raw_file"):
                target = self.path.parent / entry["raw_file"]
                if self.secret.encode() in gzip.decompress(target.read_bytes()):
                    target.unlink()
                    entry["raw_file"] = None
                    entry["withheld"] = "Yanıt ön yüzün istemci anahtarını içerdiği için saklanmadı."

    def flush(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(self.manifest, ensure_ascii=False, indent=1)
        if self.secret and self.secret in text:
            raise SourceError("Ham kayıt istemci anahtarını içeriyor; yazılmadı.")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(self.path)
        self.unsaved = 0


def parse_json(body, label):
    try:
        return json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise SourceError(f"Book>Direct {label} yanıtı JSON değil.") from exc


def number(value, label, *, integer=False, allow_none=True):
    """Source numbers arrive as numbers or numeric strings; empty values stay NULL."""
    if value in (None, ""):
        if allow_none:
            return None
        raise SourceError(f"Book>Direct {label} boş.")
    if isinstance(value, bool):
        raise SourceError(f"Book>Direct {label} sayı değil.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SourceError(f"Book>Direct {label} sayı değil: {value!r}.") from exc
    if result != result or result in (float("inf"), float("-inf")) or result < 0 and label not in ("boylam", "enlem"):
        raise SourceError(f"Book>Direct {label} geçersiz: {value!r}.")
    if integer:
        if result != int(result):
            raise SourceError(f"Book>Direct {label} tam sayı değil: {value!r}.")
        return int(result)
    return result


def text(value):
    return value.strip() or None if isinstance(value, str) else None


def web_url(value):
    """The listing's own page as published (the rental company's site); anything that is not an http(s) URL stays NULL."""
    value = text(value)
    return value if value and len(value) <= 2048 and re.match(r"https?://[^\s]+$", value) else None


def int_list(value, label):
    if value is None:
        return []
    if not isinstance(value, list) or any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise SourceError(f"Book>Direct {label} listesi beklenen biçimde değil.")
    return value


def usd(record):
    currency = record.get("currency")
    return number(currency.get("USD"), "USD fiyatı") if isinstance(currency, dict) else None


def parse_clone(body):
    data = parse_json(body, "yapılandırma")
    try:
        clone = data["data"]["clone"]
        groups = clone["group"]["sub_groups"]
        categories = clone["categories"]
        amenities = clone["amenities"]
    except (KeyError, TypeError) as exc:
        raise SourceError("Book>Direct yapılandırmasında konum, kategori veya olanak listesi yok.") from exc
    def table(items, name_key, label):
        result = {}
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or isinstance(item.get("id"), bool) or not isinstance(item.get("id"), int) or not text(item.get(name_key)):
                raise SourceError(f"Book>Direct yapılandırmasındaki {label} kaydı beklenen biçimde değil.")
            if item["id"] in result:
                raise SourceError(f"Book>Direct yapılandırmasında yinelenen {label} kimliği: {item['id']}.")
            result[item["id"]] = text(item[name_key])
        if not result:
            raise SourceError(f"Book>Direct yapılandırmasında {label} yok.")
        return result
    locations = table(groups, "name", "konum")
    if len(set(locations.values())) != len(locations):
        raise SourceError("Book>Direct yapılandırmasında aynı adlı birden fazla konum var.")
    category_names = table(categories, "title", "kategori")
    defaults = [item["id"] for item in categories if item.get("default") is True]
    if len(defaults) != 1:
        raise SourceError("Book>Direct yapılandırmasında tek bir varsayılan kategori bulunamadı.")
    return {"locations": locations, "categories": category_names, "default_category": defaults[0],
            "amenities": table(amenities, "name", "olanak")}


def parse_listing(item, clone):
    if not isinstance(item, dict) or not isinstance(item.get("lodging"), dict):
        raise SourceError("Book>Direct arama sonucunda ilan kaydı beklenen biçimde değil.")
    record = item["lodging"]
    identifier = record.get("id")
    if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier <= 0 or not text(record.get("title")):
        raise SourceError("Book>Direct ilanında kimlik veya ad yok.")
    latitude, longitude = number(record.get("latitude"), "enlem"), number(record.get("longitude"), "boylam")
    if latitude is not None and not -90 <= latitude <= 90 or longitude is not None and not -180 <= longitude <= 180:
        raise SourceError(f"Book>Direct ilanının koordinatı aralık dışında ({identifier}).")
    categories = int_list(record.get("category_ids"), "kategori")
    amenities = int_list(record.get("amenity_ids"), "olanak")
    live_enabled = record.get("live_rates_enabled")
    if live_enabled not in (True, False, None):
        raise SourceError(f"Book>Direct ilanında live_rates_enabled beklenen biçimde değil ({identifier}).")
    listing = {"lodging_id": identifier, "title": text(record["title"]), "category_ids": categories,
               "category_names": [clone["categories"].get(c, f"bilinmeyen kategori {c}") for c in categories],
               "address": text(record.get("address")), "city": text(record.get("city")), "state": text(record.get("state")),
               "zip_code": text(record.get("zip_code")), "latitude": latitude, "longitude": longitude,
               "bedrooms": number(record.get("bedrooms"), "yatak odası"), "bathrooms": number(record.get("bathrooms"), "banyo"),
               "sleeps": number(record.get("sleeps"), "kapasite", integer=True),
               "amenities": [clone["amenities"].get(a, f"bilinmeyen olanak {a}") for a in amenities],
               "res_engine": text(record.get("res_engine")), "source_location_id": number(record.get("location_id"), "konum", integer=True),
               "url": web_url(record.get("url")), "phone": text(record.get("phone")), "toll_free": text(record.get("toll_free")),
               "hide_rate_calendar": int(bool(record.get("hide_rate_calendar"))), "live_rates_enabled": int(bool(live_enabled))}
    min_stays = record.get("min_stays")
    result = {"lodging_id": identifier, "average_rate": number(record.get("average_rate"), "ortalama fiyat"),
              "average_rate_usd": usd(record), "los": number(record.get("los"), "minimum gece", integer=True),
              "liveness": number(record.get("liveness"), "canlılık", integer=True), "live_rates_enabled": int(bool(live_enabled)),
              "min_stays": None if min_stays in (None, "", []) else json.dumps(min_stays, ensure_ascii=False, sort_keys=True)}
    return listing, result


def month_summary(rates):
    """Per month: priced days, lowest, median and highest nightly price and the most common minimum stay."""
    months = {}
    for day, price, los in rates:
        months.setdefault(day[:7], []).append((price, los))
    result = []
    for month, values in sorted(months.items()):
        prices = [price for price, _ in values]
        stays = Counter(los for _, los in values if los is not None)
        common = min(stays, key=lambda los: (-stays[los], los)) if stays else None
        result.append({"month": month, "priced_days": len(prices), "min_rate": min(prices), "median_rate": round(statistics.median(prices), 2),
                       "max_rate": max(prices), "common_los": common})
    return result


def parse_calendar(body):
    """[(YYYY-MM-DD, nightly USD price, minimum stay)] for days with a price; days without a price are skipped."""
    data = parse_json(body, "fiyat takvimi")
    try:
        items = data["data"]["rates"]
    except (KeyError, TypeError) as exc:
        raise SourceError("Book>Direct fiyat takviminde 'rates' listesi yok.") from exc
    if not isinstance(items, list) or len(items) > CALENDAR_DAYS + 31:
        raise SourceError("Book>Direct fiyat takvimi beklenen biçimde değil.")
    result, seen = [], set()
    for item in items:
        day = item.get("date") if isinstance(item, dict) else None
        try:
            date.fromisoformat(day)
        except (TypeError, ValueError) as exc:
            raise SourceError("Book>Direct fiyat takviminde tarih okunamadı.") from exc
        if day in seen:
            raise SourceError(f"Book>Direct fiyat takviminde yinelenen gün: {day}.")
        seen.add(day)
        price = usd(item)
        if price is None:
            price = number(item.get("price"), "takvim fiyatı")
        if price is not None:
            result.append((day, price, number(item.get("los"), "takvim minimum gece", integer=True)))
    return sorted(result)


def window_rate(calendar, checkin, checkout):
    """Mean nightly calendar price over a window's nights, only when every night has a price."""
    prices = {day: (price, los) for day, price, los in calendar}
    nights = [(checkin + timedelta(days=offset)).isoformat() for offset in range((checkout - checkin).days)]
    found = [prices[night] for night in nights if night in prices]
    complete = len(found) == len(nights)
    stays = [los for _, los in found if los is not None]
    return {"nights": len(nights), "priced_nights": len(found),
            "mean_rate": round(sum(price for price, _ in found) / len(found), 2) if complete else None,
            "max_los": max(stays) if stays else None}


def collect(raw_path, progress, canceled, *, config, regions, client=None, today=None):
    """Search every configured window x location filter, ask live rates and read each listing's price calendar once."""
    if not config:
        raise SourceError("Bu destinasyon için konaklama (Book>Direct) yapılandırması yok.")
    clone_host = config["clone_host"]
    if not is_front_host(clone_host):
        raise SourceError("Konaklama yapılandırmasındaki Book>Direct adresi geçersiz.")
    region_names = {region["id"]: region["name"] for region in regions}
    mapping = dict(config["locations"])
    if not mapping or any(region_id not in region_names for region_id in mapping.values()):
        raise SourceError("Konaklama konum eşlemesi destinasyonun bölgeleriyle uyuşmuyor.")
    today = today or datetime.now(timezone.utc).date()
    # a window rule gives the windows of the run day (GÖREV-10: 12 monthly weeks); otherwise the configured fixed windows
    configured = monthly_windows(today, config["window_rule"]) if config.get("window_rule") else config["windows"]
    windows = [{**window, "checkin_date": date.fromisoformat(window["checkin"]), "checkout_date": date.fromisoformat(window["checkout"])}
               for window in configured]
    if not windows:
        raise SourceError("Konaklama için örnek tarih penceresi yapılandırılmamış.")
    for window in windows:
        window["nights"] = (window["checkout_date"] - window["checkin_date"]).days
        window["status"] = "skipped_past" if window["checkin_date"] < today else "searched"
    active = [window for window in windows if window["status"] == "searched"]
    if not active:
        raise SourceError("Bütün örnek tarih pencereleri geçmişte kaldı; yapılandırmaya yeni tarihler eklenmeli.")

    owns = client is None
    client = client or make_client()
    reader = KeyedReader(client, raw_path, canceled, connector=CONNECTOR_VERSION, hosts={clone_host, API_HOST}, max_bytes=MAX_BYTES,
                         label="Book>Direct")
    api = f"https://{API_HOST}/hs4/api/v1/clones/{clone_host}"
    try:
        progress(1, "Book>Direct ön yüzü okunuyor.")
        entry, entry_url = reader.get(f"https://{clone_host}/", suffix=".html", note="front-end-entry", content_types={"text/html"})
        page = entry.decode("utf-8", errors="replace")
        bases, scripts = BASE_HREF.findall(page), BUNDLE_SRC.findall(page)
        if len(bases) != 1 or len(set(scripts)) != 1:
            raise SourceError("Book>Direct giriş sayfasında sürüm yolu veya ön yüz paketi bulunamadı; sayfa değişmiş olabilir.")
        base_url = reader.checked(bases[0], entry_url)
        bundle, _ = reader.get(reader.checked(scripts[0], base_url), suffix=".js", note="front-end-bundle",
                               content_types={"application/javascript", "text/javascript", "application/x-javascript"})
        keys = set(CLIENT_KEY.findall(bundle.decode("utf-8", errors="replace")))
        del bundle
        if len(keys) != 1:
            raise SourceError("Ön yüz paketindeki istemci anahtarı tanımı beklenen biçimde değil; istek yapılmadı.")
        reader.secret = keys.pop()
        reader.scrub()
        headers = {"Authorization": f"Token token={reader.secret}", "Accept": "application/json"}

        def call(path, note, params=None, missing=()):
            body, _ = reader.get(api + path, suffix=".json", note=note, content_types=JSON_TYPES, params=params, headers=headers,
                                 allow_missing=bool(missing), missing=missing)
            return body

        progress(3, "Konum filtreleri ve kategoriler okunuyor.")
        clone = parse_clone(call("/show.json", "show", {"locale": "en"}))
        by_name = {name: identifier for identifier, name in clone["locations"].items()}
        missing = sorted(name for name in mapping if name not in by_name)
        if missing:
            raise SourceError(f"Book>Direct konum listesinde yapılandırılmış konum bulunamadı: {', '.join(missing)}.")
        unmapped = sorted(name for name in by_name if name not in mapping)
        filters = sorted(((by_name[name], name, region_id) for name, region_id in mapping.items()), key=lambda item: item[1])

        listings, results, filter_rows = {}, {}, []
        steps = len(active) * len(filters)
        for index, window in enumerate(active):
            for position, (location_id, location_name, region_id) in enumerate(filters):
                done = index * len(filters) + position
                progress(5 + int(35 * done / steps), f"{window['label']}: {location_name} aranıyor.")
                total, pages, rows = search(call, window, location_id, location_name, clone, canceled)
                for listing, result in rows:
                    known = listings.get(listing["lodging_id"])
                    if known and known["title"] != listing["title"]:
                        raise SourceError(f"Book>Direct aynı ilan kimliğini farklı adlarla verdi ({listing['lodging_id']}).")
                    listings.setdefault(listing["lodging_id"], listing)
                    results[(window["window_key"], location_id, listing["lodging_id"])] = {
                        **result, "window_key": window["window_key"], "location_id": location_id, "position": len(results),
                        "live_status": "not_requested", "live_average_rate_usd": None, "live_los": None, "live_liveness": None, "live_attempts": 0}
                filter_rows.append({"window_key": window["window_key"], "location_id": location_id, "location_name": location_name,
                                    "region_id": region_id, "region_name": region_names[region_id], "total_count": total, "page_count": pages})

        live_requests = 0
        for index, window in enumerate(active):
            progress(40 + int(15 * index / len(active)), f"{window['label']}: canlı fiyatlar soruluyor.")
            ids = sorted({key[2] for key, row in results.items() if key[0] == window["window_key"] and needs_live(row)})
            answers, live_requests = live_rates(call, window, ids, live_requests, canceled)
            for key, row in results.items():
                if key[0] == window["window_key"] and key[2] in ids:
                    answer = answers.get(key[2])
                    row.update({"live_status": "answered" if answer else "no_answer", "live_attempts": answer["attempts"] if answer else 1,
                                **({"live_average_rate_usd": answer["rate"], "live_los": answer["los"], "live_liveness": answer["liveness"]} if answer else {})})

        calendars, months, calendar_windows = [], [], []
        start, end = today, today + timedelta(days=CALENDAR_DAYS)
        # The front end shows no rate calendar for listings with hide_rate_calendar; those are not asked (GOREV-08).
        ordered = [lodging_id for lodging_id in sorted(listings) if not listings[lodging_id]["hide_rate_calendar"]]
        hidden_calendars = len(listings) - len(ordered)
        for index, lodging_id in enumerate(ordered):
            if index % 10 == 0:
                progress(55 + int(40 * index / max(1, len(ordered))), f"Fiyat takvimleri okunuyor ({index}/{len(ordered)}).")
            body = call(f"/lodgings/{lodging_id}/rates.json", f"rates-{lodging_id}",
                        {"per_page": CALENDAR_DAYS, "checkin": start.strftime("%Y%m%d"), "checkout": end.strftime("%Y%m%d"), "locale": "en"},
                        missing=CALENDAR_MISSING)
            if body is None:
                calendars.append({"lodging_id": lodging_id, "status": "unavailable", "requested_from": start.isoformat(),
                                  "requested_to": end.isoformat(), "priced_days": 0})
                continue
            calendar = parse_calendar(body)
            calendars.append({"lodging_id": lodging_id, "status": "read", "requested_from": start.isoformat(), "requested_to": end.isoformat(),
                              "priced_days": len(calendar)})
            months.extend({"lodging_id": lodging_id, **row} for row in month_summary(calendar))
            for window in active:
                calendar_windows.append({"lodging_id": lodging_id, "window_key": window["window_key"],
                                         **window_rate(calendar, window["checkin_date"], window["checkout_date"])})
        check(canceled)
        reader.flush()
        request_count = len(reader.manifest["responses"])
        snapshot = {"clone_host": clone_host, "front_end_path": bases[0], "default_category_id": clone["default_category"],
                    "searched_on": today.isoformat(), "request_count": request_count, "listing_count": len(listings)}
        window_rows = [{key: window[key] for key in ("window_key", "label", "checkin", "checkout", "nights", "status")} for window in windows]
        priced = {"liste": sum(row["average_rate_usd"] is not None or row["average_rate"] is not None for row in results.values()),
                  "canli": sum(row["live_average_rate_usd"] is not None for row in results.values()),
                  "takvim_ilan": sum(row["priced_days"] > 0 for row in calendars)}
        metadata = {"clone_host": clone_host, "front_end_path": bases[0], "searched_on": today.isoformat(),
                    "window_rule": config.get("window_rule"),
                    "windows": [{k: w[k] for k in ("window_key", "label", "checkin", "checkout", "status")} for w in windows],
                    "skipped_past_windows": [w["window_key"] for w in windows if w["status"] == "skipped_past"],
                    "location_filters": [{"location_id": f[0], "location_name": f[1], "region_id": f[2]} for f in filters],
                    "unmapped_locations": unmapped, "search_rows": len(results), "listing_count": len(listings),
                    "live_rate_requests": live_requests, "request_count": request_count, "priced": priced,
                    "calendars_read": len(calendars), "calendars_skipped_hidden": hidden_calendars, "scope": SCOPE}
        progress(97, f"{len(listings)} benzersiz ilan, {len(results)} arama satırı ve {len(calendars)} fiyat takvimi kaydediliyor.")
        related = {"snapshot": snapshot, "windows": window_rows, "filters": filter_rows, "results": list(results.values()),
                   "calendars": calendars, "months": months, "calendar_windows": calendar_windows}
        return CollectionResult([listings[i] for i in sorted(listings)], len(listings), len(unmapped), None, metadata, related)
    finally:
        try:
            reader.flush()
        except SourceError:
            pass
        if owns:
            client.close()


def search(call, window, location_id, location_name, clone, canceled=lambda: False):
    """All pages of one window x location filter; a changing total or an incomplete page set is read again from page 1 (up to
    SEARCH_ATTEMPTS times, SEARCH_RETRY_PAUSE apart), then fails: no partial result is kept."""
    for attempt in range(SEARCH_ATTEMPTS):
        if attempt:
            pause(SEARCH_RETRY_PAUSE, canceled)
        params = {"per_page": PER_PAGE, "checkin": window["checkin_date"].strftime("%Y%m%d"), "checkout": window["checkout_date"].strftime("%Y%m%d"),
                  "category_ids[]": clone["default_category"], "group_ids[]": location_id, "sort": "title", "direction": "asc", "locale": "en"}
        rows, totals, page, pages = {}, set(), 1, None
        while True:
            data = parse_json(call("/lodgings.json", f"lodgings-{window['window_key']}-{location_id}-p{page}", {**params, "page": page}), "arama")
            try:
                request, items = data["request"], data["data"]["lodgings"]
                total, pages, current = request["total_count"], request["total_pages"], request["current_page"]
            except (KeyError, TypeError) as exc:
                raise SourceError("Book>Direct arama yanıtında sayfa bilgisi veya ilan listesi yok.") from exc
            if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in (total, pages, current)) or not isinstance(items, list):
                raise SourceError("Book>Direct arama yanıtının sayfa bilgisi beklenen biçimde değil.")
            if current != page or pages > MAX_PAGES or len(items) > PER_PAGE:
                raise SourceError(f"Book>Direct {location_name} araması beklenmeyen sayfa döndürdü ({current}/{pages}).")
            totals.add(total)
            for item in items:
                listing, result = parse_listing(item, clone)
                rows.setdefault(listing["lodging_id"], (listing, result))
            if page >= pages:
                break
            page += 1
        if len(totals) == 1 and len(rows) == total:
            return total, pages, list(rows.values())
    raise SourceError(f"Book>Direct {location_name} araması ({window['label']}) tutarlı bir sonuç vermedi: sayfalar arasında toplam değişti "
                      f"veya {len(rows)} ilan okunup {sorted(totals)} bildirildi. Kısmi sonuç kaydedilmedi.")


def needs_live(row):
    """Like the front end's get_live_rate_ids: ask unless the search already gave a price that is not pending (liveness 1).

    The front end only looks at listings whose search row carries a liveness value; we also ask the listings the source marks
    live_rates_enabled, so a live price is not missed when the search row leaves liveness empty.
    """
    has_price = row["average_rate_usd"] is not None or row["average_rate"] is not None
    return (bool(row["live_rates_enabled"]) or row["liveness"] is not None) and (row["liveness"] == 1 or not has_price)


def live_rates(call, window, ids, request_count, canceled):
    """Ask the live-rate service like the front end: repeat for pending answers up to LIVE_ATTEMPTS times."""
    answers, pending = {}, list(ids)
    for attempt in range(1, LIVE_ATTEMPTS + 1):
        if not pending:
            break
        if attempt > 1:
            pause(LIVE_PAUSE + LIVE_BACKOFF * (attempt - 1), canceled)
        still = []
        for batch_index in range(0, len(pending), LIVE_BATCH):
            batch = pending[batch_index:batch_index + LIVE_BATCH]
            body = call("/lodgings/live_rates.json", f"live-{window['window_key']}-a{attempt}-b{batch_index // LIVE_BATCH + 1}",
                        {"checkin": window["checkin_date"].strftime("%Y%m%d"), "checkout": window["checkout_date"].strftime("%Y%m%d"),
                         "lodging_ids[]": batch, "current_page": batch_index // LIVE_BATCH + 1, "attempt": attempt})
            request_count += 1
            data = parse_json(body, "canlı fiyat")
            rows = data.get("data", {}).get("live_rates") if isinstance(data, dict) and isinstance(data.get("data"), dict) else None
            if not isinstance(rows, list):
                raise SourceError("Book>Direct canlı fiyat yanıtında 'live_rates' listesi yok.")
            for row in rows:
                if not isinstance(row, dict) or row.get("lodging_id") not in batch:
                    continue
                liveness = number(row.get("liveness"), "canlılık", integer=True)
                answers[row["lodging_id"]] = {"rate": usd(row) if usd(row) is not None else number(row.get("average_rate"), "canlı fiyat"),
                                              "los": number(row.get("los"), "canlı minimum gece", integer=True), "liveness": liveness,
                                              "attempts": attempt}
                if liveness:     # the front end keeps asking while liveness is set and not 0 (pending)
                    still.append(row["lodging_id"])
        pending = still
    return answers, request_count


# --- Summaries computed when read -----------------------------------------------------------------------------------

def quartiles(values):
    values = sorted(values)
    if not values:
        return None, None, None
    if len(values) == 1:
        return values[0], values[0], values[0]
    q1, median, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return round(q1, 2), round(median, 2), round(q3, 2)


def price_of(row, calendar):
    """The listing's nightly price for a window and where it came from.

    A current live answer (liveness 0) comes first, as the front end replaces the search price with it; then the search
    (list) price, then any other live answer, then the mean of a fully priced calendar window.
    """
    if row["live_average_rate_usd"] is not None and row.get("live_liveness") == 0:
        return row["live_average_rate_usd"], "canli"
    if row["average_rate_usd"] is not None or row["average_rate"] is not None:
        return (row["average_rate_usd"] if row["average_rate_usd"] is not None else row["average_rate"]), "liste"
    if row["live_average_rate_usd"] is not None:
        return row["live_average_rate_usd"], "canli"
    if calendar and calendar["mean_rate"] is not None:
        return calendar["mean_rate"], "takvim"
    return None, None


def summarize(con, run_id, region_order=()):
    """Region x window summary and monthly calendar medians of one run; nothing here is stored."""
    snapshot = con.execute("SELECT * FROM lodging_snapshots WHERE run_id=?", (run_id,)).fetchone()
    if not snapshot:
        return None
    windows = [dict(row) for row in con.execute("SELECT * FROM lodging_windows WHERE run_id=? ORDER BY checkin", (run_id,))]
    filters = [dict(row) for row in con.execute("SELECT * FROM lodging_filters WHERE run_id=?", (run_id,))]
    listings = {row["lodging_id"]: decode_listing(row) for row in con.execute("SELECT * FROM lodging_listings WHERE run_id=?", (run_id,))}
    calendars = {(row["lodging_id"], row["window_key"]): dict(row) for row in con.execute("SELECT * FROM lodging_calendar_windows WHERE run_id=?", (run_id,))}
    regions = {}
    for row in filters:
        regions.setdefault(row["region_id"], {"region_id": row["region_id"], "region_name": row["region_name"], "filters": set()})["filters"].add(row["location_name"])
    order = {region: index for index, region in enumerate(region_order)}
    region_list = sorted(regions.values(), key=lambda r: (order.get(r["region_id"], len(order)), r["region_name"]))
    region_of = {(row["window_key"], row["location_id"]): row["region_id"] for row in filters}
    seen = {}
    for row in con.execute("SELECT * FROM lodging_search_results WHERE run_id=? ORDER BY position", (run_id,)):
        key = (region_of[(row["window_key"], row["location_id"])], row["window_key"])
        seen.setdefault(key, {}).setdefault(row["lodging_id"], dict(row))
    default_category = snapshot["default_category_id"]
    cells, region_prices = [], {}
    for region in region_list:
        for window in windows:
            rows = seen.get((region["region_id"], window["window_key"]), {})
            cell = {"region_id": region["region_id"], "window_key": window["window_key"], "status": window["status"], "listing_count": len(rows)}
            if window["status"] == "searched":
                members = [listings[i] for i in rows]
                categories = Counter(name for listing in members
                                     for cid, name in zip(listing["category_ids"], listing["category_names"]) if cid != default_category)
                bedrooms = [m["bedrooms"] for m in members if m["bedrooms"] is not None]
                sleeps = [m["sleeps"] for m in members if m["sleeps"] is not None]
                prices, sources = [], Counter()
                for lodging_id, row in rows.items():
                    price, source = price_of(row, calendars.get((lodging_id, window["window_key"])))
                    if price is not None:
                        prices.append(price)
                        sources[source] += 1
                q1, median, q3 = quartiles(prices)
                region_prices[(region["region_id"], window["window_key"])] = prices
                cell.update({"categories": dict(categories.most_common()), "no_category": sum(1 for m in members if not any(c != default_category for c in m["category_ids"])),
                             "bedrooms_known": len(bedrooms), "bedrooms_median": float(statistics.median(bedrooms)) if bedrooms else None,
                             "bedrooms_4_plus_share": round(sum(b >= 4 for b in bedrooms) / len(bedrooms), 3) if bedrooms else None,
                             "bedroom_buckets": bedroom_buckets(bedrooms), "sleeps_median": float(statistics.median(sleeps)) if sleeps else None,
                             "priced_count": len(prices), "priced_share": round(len(prices) / len(rows), 3) if rows else None,
                             "price_sources": {name: sources.get(name, 0) for name in PRICE_SOURCES},
                             "price_q1": q1, "price_median": median, "price_q3": q3})
            cells.append(cell)
    monthly = []
    members_by_region = {}
    for (region_id, _), rows in seen.items():
        members_by_region.setdefault(region_id, set()).update(rows)
    month_rows = {}
    for row in con.execute("SELECT lodging_id, month, median_rate FROM lodging_rate_months WHERE run_id=?", (run_id,)):
        month_rows.setdefault(row["lodging_id"], []).append((row["month"], row["median_rate"]))
    for region in region_list:
        per_month = {}
        for lodging_id in members_by_region.get(region["region_id"], ()):
            for month, median in month_rows.get(lodging_id, []):
                per_month.setdefault(month, []).append(median)
        for month, values in sorted(per_month.items()):
            monthly.append({"region_id": region["region_id"], "month": month, "listing_count": len(values),
                            "median_rate": round(statistics.median(values), 2)})
    windows = annotate_windows(windows, snapshot["searched_on"])
    region_ids = [r["region_id"] for r in region_list]
    members = {}
    for (region_id, _), rows in seen.items():
        members.setdefault(region_id, set()).update(rows)
    return {"snapshot": dict(snapshot), "windows": windows,
            "regions": [{**r, "filters": sorted(r["filters"])} for r in region_list], "cells": cells, "monthly": monthly,
            "label": label(snapshot["searched_on"]), "seasons": season_groups(region_ids, windows, region_prices),
            "comparison": previous_comparison(con, run_id, region_ids, members, snapshot["searched_on"])}


def run_nightly(con, run_id):
    """Searched windows and each listing's nightly price per window (price_of) of one run."""
    windows = [dict(r) for r in con.execute("SELECT * FROM lodging_windows WHERE run_id=? AND status='searched' ORDER BY checkin", (run_id,))]
    calendars = {(r["lodging_id"], r["window_key"]): dict(r) for r in con.execute("SELECT * FROM lodging_calendar_windows WHERE run_id=?", (run_id,))}
    prices = {}
    for row in con.execute("SELECT * FROM lodging_search_results WHERE run_id=? ORDER BY position", (run_id,)):
        key = (row["lodging_id"], row["window_key"])
        if key not in prices or prices[key] is None:
            prices[key] = price_of(dict(row), calendars.get(key))[0]
    return windows, {k: v for k, v in prices.items() if v is not None}


def previous_comparison(con, run_id, regions, members, searched_on):
    """Same-week comparison (nightly price as in price_of) with the latest earlier run of the destination that searched a same week."""
    current = con.execute("SELECT rowid, destination_id FROM source_runs WHERE id=?", (run_id,)).fetchone()
    if not current:
        return None
    windows, prices = run_nightly(con, run_id)
    dates = {(w["checkin"], w["checkout"]) for w in windows}
    for row in con.execute("""SELECT s.run_id, s.searched_on FROM lodging_snapshots s JOIN source_runs r ON r.id=s.run_id
            WHERE r.status='done' AND r.destination_id=? AND r.rowid<? ORDER BY r.rowid DESC""", (current["destination_id"], current["rowid"])):
        earlier_windows, earlier_prices = run_nightly(con, row["run_id"])
        if not dates & {(w["checkin"], w["checkout"]) for w in earlier_windows}:
            continue
        result = compare(regions, {"windows": earlier_windows, "prices": earlier_prices},
                         {"windows": windows, "prices": prices, "members": members}, row["searched_on"], searched_on)
        return {**result, "earlier_run_id": row["run_id"], "earlier_queried_on": row["searched_on"], "basis": "gecelik fiyat (Book>Direct)"}
    return None


def label(searched_on):
    return (f"{searched_on} tarihinde yapılan aramada görünen ilanlar; tam envanter değildir; fiyatlar kaynağa göre en düşük müsait günlük "
            "fiyata dayanır, vergi ve ücretlerin dahil olup olmadığı kaynakta belirtilmiyor.")


def bedroom_buckets(values):
    buckets = Counter("stüdyo" if v < 1 else "6+" if v >= 6 else str(int(v)) for v in values)
    return {name: buckets.get(name, 0) for name in ("stüdyo", "1", "2", "3", "4", "5", "6+")}


def decode_listing(row):
    result = dict(row)
    for key in ("category_ids", "category_names", "amenities"):
        result[key] = json.loads(result[key])
    return result


def region_listings(con, run_id, region_id):
    """Listings seen under a region's filters with their per-window search rows, calendar windows and monthly calendar."""
    filters = {(row["window_key"], row["location_id"]): row["location_name"] for row in con.execute(
        "SELECT * FROM lodging_filters WHERE run_id=? AND region_id=?", (run_id, region_id))}
    if not filters:
        return None
    rows = {}
    for row in con.execute("SELECT * FROM lodging_search_results WHERE run_id=? ORDER BY position", (run_id,)):
        if (row["window_key"], row["location_id"]) in filters:
            entry = rows.setdefault(row["lodging_id"], {"windows": {}, "filters": set()})
            entry["filters"].add(filters[(row["window_key"], row["location_id"])])
            entry["windows"].setdefault(row["window_key"], dict(row))
    calendars = {(row["lodging_id"], row["window_key"]): dict(row) for row in con.execute("SELECT * FROM lodging_calendar_windows WHERE run_id=?", (run_id,))}
    result = []
    for row in con.execute("SELECT * FROM lodging_listings WHERE run_id=? ORDER BY title, lodging_id", (run_id,)):
        if row["lodging_id"] not in rows:
            continue
        listing = decode_listing(row)
        entry = rows[row["lodging_id"]]
        windows = {}
        for window_key, search_row in entry["windows"].items():
            price, source = price_of(search_row, calendars.get((row["lodging_id"], window_key)))
            windows[window_key] = {**search_row, "price": price, "price_source": source,
                                   "calendar": calendars.get((row["lodging_id"], window_key))}
        listing.update({"filters": sorted(entry["filters"]), "windows": windows,
                        "calendar": dict(con.execute("SELECT * FROM lodging_calendars WHERE run_id=? AND lodging_id=?", (run_id, row["lodging_id"])).fetchone() or {}),
                        "months": [dict(m) for m in con.execute("SELECT month,priced_days,min_rate,median_rate,max_rate,common_los FROM lodging_rate_months "
                                                                 "WHERE run_id=? AND lodging_id=? ORDER BY month", (run_id, row["lodging_id"]))]})
        result.append(listing)
    return result


class BookDirectLodgingConnector:
    name = "bookdirect-lodging"
    version = CONNECTOR_VERSION
    produces = "lodging_listings"           # the agency rate collector reads the latest run's listings
    raw_filename = "manifest.json"
    method = "JSON"
    diff_enabled = False
    diff_reason = "Konaklama aramaları tarihe bağlı anlık görüntülerdir; sürümler arası ilan farkı envanter değişikliği sayılmamalı."

    def supports(self, source):
        return source_host(source.get("url")) is not None

    def collect(self, source, raw_path, progress, canceled, *, context):
        config = context.lodging
        if config and config["clone_host"] != source_host(source["url"]):
            raise SourceError("Kaynağın Book>Direct adresi destinasyonun konaklama yapılandırmasıyla uyuşmuyor.")
        return collect(raw_path, progress, canceled, config=config, regions=context.canonical_regions)

    def store_records(self, con, run_id, records, related=None):
        related = related or {}
        snapshot = related["snapshot"]
        con.execute("""INSERT INTO lodging_snapshots (run_id,clone_host,front_end_path,default_category_id,searched_on,request_count,listing_count)
            VALUES (?,?,?,?,?,?,?)""", (run_id, snapshot["clone_host"], snapshot["front_end_path"], snapshot["default_category_id"],
                                        snapshot["searched_on"], snapshot["request_count"], snapshot["listing_count"]))
        con.executemany("INSERT INTO lodging_windows (run_id,window_key,label,checkin,checkout,nights,status) VALUES (?,?,?,?,?,?,?)",
                        [(run_id, w["window_key"], w["label"], w["checkin"], w["checkout"], w["nights"], w["status"]) for w in related["windows"]])
        con.executemany("""INSERT INTO lodging_filters (run_id,window_key,location_id,location_name,region_id,region_name,total_count,page_count)
            VALUES (?,?,?,?,?,?,?,?)""", [(run_id, f["window_key"], f["location_id"], f["location_name"], f["region_id"], f["region_name"],
                                           f["total_count"], f["page_count"]) for f in related["filters"]])
        con.executemany("""INSERT INTO lodging_listings (run_id,lodging_id,title,category_ids,category_names,address,city,state,zip_code,latitude,
            longitude,bedrooms,bathrooms,sleeps,amenities,res_engine,source_location_id,hide_rate_calendar,live_rates_enabled,url,phone,toll_free)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, r["lodging_id"], r["title"], json.dumps(r["category_ids"]), json.dumps(r["category_names"], ensure_ascii=False), r["address"],
              r["city"], r["state"], r["zip_code"], r["latitude"], r["longitude"], r["bedrooms"], r["bathrooms"], r["sleeps"],
              json.dumps(r["amenities"], ensure_ascii=False), r["res_engine"], r["source_location_id"], r["hide_rate_calendar"],
              r["live_rates_enabled"], r["url"], r["phone"], r["toll_free"]) for r in records])
        con.executemany("""INSERT INTO lodging_search_results (run_id,window_key,location_id,lodging_id,position,average_rate,average_rate_usd,los,
            liveness,live_rates_enabled,min_stays,live_status,live_average_rate_usd,live_los,live_liveness,live_attempts)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, r["window_key"], r["location_id"], r["lodging_id"], r["position"], r["average_rate"], r["average_rate_usd"], r["los"],
              r["liveness"], r["live_rates_enabled"], r["min_stays"], r["live_status"], r["live_average_rate_usd"], r["live_los"],
              r["live_liveness"], r["live_attempts"]) for r in related["results"]])
        con.executemany("INSERT INTO lodging_calendars (run_id,lodging_id,status,requested_from,requested_to,priced_days) VALUES (?,?,?,?,?,?)",
                        [(run_id, c["lodging_id"], c["status"], c["requested_from"], c["requested_to"], c["priced_days"]) for c in related["calendars"]])
        con.executemany("""INSERT INTO lodging_rate_months (run_id,lodging_id,month,priced_days,min_rate,median_rate,max_rate,common_los)
            VALUES (?,?,?,?,?,?,?,?)""", [(run_id, m["lodging_id"], m["month"], m["priced_days"], m["min_rate"], m["median_rate"], m["max_rate"],
                                           m["common_los"]) for m in related["months"]])
        con.executemany("""INSERT INTO lodging_calendar_windows (run_id,lodging_id,window_key,nights,priced_nights,mean_rate,max_los)
            VALUES (?,?,?,?,?,?,?)""", [(run_id, c["lodging_id"], c["window_key"], c["nights"], c["priced_nights"], c["mean_rate"], c["max_los"])
                                        for c in related["calendar_windows"]])

    def read_records(self, con, run_id):
        return [decode_listing(row) for row in con.execute("SELECT * FROM lodging_listings WHERE run_id=? ORDER BY title, lodging_id", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Lodging snapshot diff is disabled.")
