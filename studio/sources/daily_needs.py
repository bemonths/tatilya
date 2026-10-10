"""Daily-need points from OpenStreetMap (Overpass API): big supermarkets and local or gourmet markets, convenience stores, pharmacies,
emergency departments, urgent care and bicycle rental, for the destination's configured area and categories. © OpenStreetMap
katkıcıları, ODbL.

Generic core: the area (a bounding box) and the categories (OpenStreetMap tag sets, optionally a brand list and "verified only") come
from the destination configuration in SQLite; one small Overpass query per run, its raw answer kept with SHA-256. Reviewed point files
(a person checks the chains' store locators and the hospital systems' location pages; column `kategori`) confirm OpenStreetMap points,
add what OpenStreetMap lacks with the file's source label ("zincirin kendi sitesi", "kurumun kendi sitesi") and report closed places;
in a verified-only category an OpenStreetMap point no reviewed row confirms is left out and reported.

Distances are computed when read: great-circle ("kuş uçuşu") from each listing of the latest lodging run to the nearest point of
each category and to the nearest public beach access of the county list; nothing about walking routes is claimed.
"""
import csv
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

from .base import CollectionResult, SourceError
from .climate_http import Reader, make_client
from .geo import distance_km

CONNECTOR_VERSION = "openstreetmap-daily-needs/1"
SOURCE_URL = "https://www.openstreetmap.org/?kaynak=gunluk-ihtiyac"
OVERPASS_HOST = "overpass-api.de"
OVERPASS_URL = f"https://{OVERPASS_HOST}/api/interpreter"
ATTRIBUTION = "© OpenStreetMap katkıcıları, ODbL"
MAX_BYTES = 10_000_000
MILE_KM = 1.609344
MATCH_KM = 0.4                 # a chain's store and an OpenStreetMap store of the same brand this close are the same store
CHAIN_STATUSES = ("açık", "kapalı", "bölgede mağaza yok", "okunamadı")
DISTANCE_LABEL = "kuş uçuşu (yol üzerinden değil)"
BEACH_NOTE = ("Plaj erişimi ölçüsü yalnız ilçenin halka açık erişim listesine göredir; Seaside, WaterColor, Alys Beach, Rosemary Beach gibi "
              "toplulukların kendi misafirlerine açık özel erişimleri dahil değildir.")


def overpass_query(area, categories):
    bbox = f"{area['south']},{area['west']},{area['north']},{area['east']}"
    clauses = []
    for category in categories:
        for tags in category["filters"]:
            selector = "".join(f'["{key}"="{value}"]' for key, value in tags.items())
            clause = f"nwr{selector}({bbox});"
            if clause not in clauses:                 # two categories may share a tag set (big and local supermarkets)
                clauses.append(clause)
    return f"[out:json][timeout:90];({''.join(clauses)});out center tags;"


def words(text):
    """Lower-case words of a name, apostrophes dropped and hyphens as spaces ("Winn-Dixie" -> "winn dixie", "Trader Joe's" -> "trader joes")."""
    return " ".join(re.sub(r"[^0-9a-z ]+", " ", (text or "").lower().replace("'", "").replace("’", "")).split())


def has_brand(brands, *texts):
    """Whether one of the brand names appears as whole words in one of the texts (brand, name, operator)."""
    haystack = [f" {words(t)} " for t in texts if t]
    return any(f" {words(brand)} " in text for brand in brands for text in haystack)


def category_of(tags, categories):
    """The first category one of whose tag sets the element carries in full and, when the category lists brands, whose brand, name or
    operator carries one of them; None when none."""
    for category in categories:
        if any(all(tags.get(key) == value for key, value in wanted.items()) for wanted in category["filters"]):
            if category.get("brands") and not has_brand(category["brands"], tags.get("brand"), tags.get("name"), tags.get("operator")):
                continue
            return category["category_key"]
    return None


def address(tags):
    street = " ".join(v for v in (tags.get("addr:housenumber"), tags.get("addr:street")) if v)
    parts = [street, tags.get("addr:unit"), tags.get("addr:city"), tags.get("addr:state"), tags.get("addr:postcode")]
    return ", ".join(p for p in parts if p) or None


KEPT_TAGS = ("name", "brand", "operator", "shop", "amenity", "healthcare", "emergency", "service:bicycle:rental", "opening_hours", "website",
             "addr:housenumber", "addr:street", "addr:city", "addr:postcode", "check_date", "disused:shop", "disused:amenity")


def parse(body, categories):
    """(points, osm timestamp) from an Overpass JSON answer; elements of no configured category are left out."""
    try:
        data = json.loads(body)
        elements = data["elements"]
    except (ValueError, KeyError, TypeError) as exc:
        raise SourceError("Overpass yanıtı beklenen JSON biçiminde değil.") from exc
    if not isinstance(elements, list):
        raise SourceError("Overpass yanıtında öğe listesi yok.")
    points, seen = [], set()
    for element in elements:
        if not isinstance(element, dict) or element.get("type") not in ("node", "way", "relation"):
            continue
        tags = element.get("tags") or {}
        key = category_of(tags, categories)
        if key is None:
            continue
        center = element if element["type"] == "node" else element.get("center") or {}
        latitude, longitude = center.get("lat"), center.get("lon")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            continue
        point_id = f"{element['type']}/{element['id']}"
        if point_id in seen:
            continue
        seen.add(point_id)
        points.append({"point_id": point_id, "category_key": key, "name": tags.get("name"), "brand": tags.get("brand"),
                       "latitude": float(latitude), "longitude": float(longitude), "source": "openstreetmap", "osm_type": element["type"],
                       "osm_id": int(element["id"]), "tags": {k: tags[k] for k in KEPT_TAGS if k in tags}, "address": address(tags),
                       "source_url": f"https://www.openstreetmap.org/{element['type']}/{element['id']}", "checked_on": None, "note": None})
    stamp = (data.get("osm3s") or {}).get("timestamp_osm_base") if isinstance(data, dict) else None
    return points, stamp


def read_reviewed(path, categories, default_category=None):
    """Rows of a reviewed point file (a chain's store locator, a hospital system's location pages), each with its category
    (`kategori`; the brand category when the file has no such column, as the GÖREV-10 supermarket file)."""
    if not path or not Path(path).is_file():
        return []
    with open(path, encoding="utf-8-sig") as handle:
        rows = [dict(r) for r in csv.DictReader(handle)]
    keys = {c["category_key"] for c in categories}
    for row in rows:
        if row.get("durum") not in CHAIN_STATUSES:
            raise SourceError(f"Gözden geçirilmiş nokta dosyasında bilinmeyen durum: {row.get('durum')!r} ({Path(path).name}).")
        row["kategori"] = (row.get("kategori") or default_category or "").strip()
        if row["kategori"] not in keys:
            raise SourceError(f"Gözden geçirilmiş nokta dosyasında yapılandırmada olmayan kategori: {row['kategori']!r} ({Path(path).name}).")
    return rows


def read_chain_checks(path, categories=None):
    """GÖREV-10 name kept for callers: the supermarket chain file read with the brand category as default."""
    categories = categories or [{"category_key": "big_supermarket"}]
    default = next((c["category_key"] for c in categories if c.get("brands")), categories[0]["category_key"])
    return read_reviewed(path, categories, default)


def same_brand(chain, point):
    """A reviewed row's chain or system and an OpenStreetMap point: the chain's name in the point's brand, name or operator, or the
    point's first word in the chain's name ("Sacred Heart Hospital ..." and "Ascension Sacred Heart")."""
    if has_brand([chain], point.get("brand"), point.get("name"), point.get("operator") or (point.get("tags") or {}).get("operator")):
        return True
    text = words(" ".join(v for v in (point.get("brand"), point.get("name")) if v))
    return bool(text) and text.split()[0] in words(chain).split()


def merge_reviewed(points, rows, categories, source_label="zincirin kendi sitesi"):
    """(points with the reviewed file's additions and notes, check rows with their outcome). An open place OpenStreetMap also has
    (by `osm_id`, or the same brand within MATCH_KM in the same category) confirms that point; one OpenStreetMap lacks is added with
    the file's source label; a closed one is noted on the OpenStreetMap point; a chain whose site could not be read leaves a note on
    its OpenStreetMap points. In a category that counts only confirmed points (verified_only), an OpenStreetMap point no row
    confirms is left out of the points and reported."""
    by_id = {p["point_id"]: p for p in points}
    checks, confirmed = [], set()
    for row in rows:
        category = row["kategori"]
        latitude = float(row["enlem"]) if row.get("enlem") else None
        longitude = float(row["boylam"]) if row.get("boylam") else None
        osm = by_id.get((row.get("osm_id") or "").strip())
        if osm is None and latitude is not None and row["durum"] in ("açık", "kapalı"):
            near = [p for p in points if p["category_key"] == category and p["source"] == "openstreetmap" and same_brand(row["zincir"], p)
                    and distance_km(latitude, longitude, p["latitude"], p["longitude"]) <= MATCH_KM]
            osm = min(near, key=lambda p: distance_km(latitude, longitude, p["latitude"], p["longitude"])) if near else None
        if row["durum"] == "açık" and osm is not None:
            outcome = "osm_ile_ayni"
            confirmed.add(osm["point_id"])
            osm["note"] = " ".join(v for v in (osm.get("note"), f"{row['zincir']} sitesinde doğrulandı ({row.get('kontrol_tarihi')}).") if v)
        elif row["durum"] == "açık":
            if latitude is None or longitude is None:
                raise SourceError(f"Gözden geçirilmiş nokta dosyasında koordinatsız açık yer: {row['zincir']} · {row['magaza']}.")
            outcome = "eklendi"
            prefix = "zincir" if source_label == "zincirin kendi sitesi" else "kurum"
            points.append({"point_id": f"{prefix}/{row['zincir']}/{row['magaza']}", "category_key": category, "name": row["magaza"],
                           "brand": row["zincir"], "latitude": latitude, "longitude": longitude, "source": source_label,
                           "osm_type": None, "osm_id": None, "tags": None, "address": row.get("adres") or None, "source_url": row.get("magaza_url") or None,
                           "checked_on": row.get("kontrol_tarihi") or None,
                           "note": " ".join(v for v in (row.get("not"), f"Koordinat: {row['koordinat_kaynagi']}." if row.get("koordinat_kaynagi") else None) if v) or None})
        elif row["durum"] == "kapalı" and osm is not None:
            outcome = "osmde_var_zincirde_kapali"
            osm["note"] = f"{row['zincir']} sitesinde kapalı görünüyor ({row.get('kontrol_tarihi')})."
        elif row["durum"] == "okunamadı":
            outcome = "okunamadi"
            for point in points:
                if point["category_key"] == category and point["source"] == "openstreetmap" and same_brand(row["zincir"], point):
                    point["note"] = " ".join(v for v in (point.get("note"), f"{row['zincir']} sitesi bu bilgisayardan doğrulanamadı ({row.get('kontrol_tarihi')}).") if v)
        else:
            outcome = "bolgede_yok"
        checks.append({"category_key": category, "chain": row["zincir"], "store": row["magaza"], "address": row.get("adres") or None,
                       "latitude": latitude, "longitude": longitude, "store_url": row.get("magaza_url") or None, "checked_on": row.get("kontrol_tarihi"),
                       "status": row["durum"], "osm_point_id": osm["point_id"] if osm else None, "outcome": outcome, "note": row.get("not") or None})
    return points, checks, confirmed


def drop_unconfirmed(points, checks, categories, confirmed):
    """verified_only categories keep only the OpenStreetMap points a reviewed row confirmed; the others are reported."""
    verified_only = {c["category_key"] for c in categories if c.get("verified_only")}
    kept = []
    for point in points:
        if point["category_key"] in verified_only and point["source"] == "openstreetmap" and point["point_id"] not in confirmed:
            checks.append({"category_key": point["category_key"], "chain": "OpenStreetMap",
                           "store": f"{point.get('name') or 'adı yok'} · {point['point_id']}", "address": point.get("address"), "latitude": point["latitude"],
                           "longitude": point["longitude"], "store_url": point.get("source_url"), "checked_on": None, "status": "açık",
                           "osm_point_id": point["point_id"], "outcome": "osm_dogrulanamadi",
                           "note": "OpenStreetMap'te var; resmî kaynakta doğrulanamadı, ölçülere girmedi."})
            continue
        kept.append(point)
    return kept, checks


def merge_chain_checks(points, rows, categories=None):
    """GÖREV-10 shape kept for callers and tests: one reviewed file of the chain label; returns (points, checks)."""
    categories = categories or [{"category_key": rows[0]["kategori"] if rows and rows[0].get("kategori") else "big_supermarket"}]
    for row in rows:
        row.setdefault("kategori", categories[0]["category_key"])
        if not row["kategori"]:
            row["kategori"] = categories[0]["category_key"]
    points, checks, _ = merge_reviewed(points, rows, categories)
    return points, checks


def collect(raw_path, progress, canceled, *, config, client=None, today=None):
    if not config or not config.get("area") or not config.get("categories"):
        raise SourceError("Bu destinasyon için günlük ihtiyaç alanı ve kategorileri yapılandırılmamış.")
    area, categories = config["area"], config["categories"]
    owns = client is None
    client = client or make_client()
    reader = Reader(client, raw_path, canceled, connector=CONNECTOR_VERSION, hosts={OVERPASS_HOST}, max_bytes=MAX_BYTES, label="Overpass API")
    try:
        progress(5, "OpenStreetMap (Overpass API) sorgulanıyor: tek sorgu.")
        query = overpass_query(area, categories)
        body, _ = reader.get(OVERPASS_URL, suffix=".json", note="overpass", content_types={"application/json"}, params={"data": query})
        points, stamp = parse(body, categories)
        progress(70, f"{len(points)} nokta okundu; gözden geçirilmiş zincir ve kurum kontrolleri ekleniyor.")
        files = list(config.get("reviewed_files") or ())
        if config.get("chain_checks") and not any(str(path) == str(config["chain_checks"]) for path, _ in files):
            files.insert(0, (config["chain_checks"], "zincirin kendi sitesi"))
        brand_category = next((c["category_key"] for c in categories if c.get("brands")), categories[0]["category_key"])
        checks, confirmed = [], set()
        for path, label in files:
            points, found, ok = merge_reviewed(points, read_reviewed(path, categories, brand_category), categories, label)
            checks += found
            confirmed |= ok
        points, checks = drop_unconfirmed(points, checks, categories, confirmed)
        today = (today or datetime.now(timezone.utc).date()).isoformat()
        counts = {c["category_key"]: sum(p["category_key"] == c["category_key"] for p in points) for c in categories}
        metadata = {"area": area, "categories": [{k: c[k] for k in ("category_key", "label")} for c in categories], "query": query,
                    "osm_timestamp": stamp, "request_count": len(reader.manifest["responses"]), "point_counts": counts,
                    "chain_checks": len(checks), "added_from_chains": sum(c["outcome"] == "eklendi" for c in checks),
                    "osm_unconfirmed": sum(c["outcome"] == "osm_dogrulanamadi" for c in checks), "attribution": ATTRIBUTION}
        snapshot = {"area": area, "categories": categories, "queried_on": today, "osm_timestamp": stamp,
                    "request_count": len(reader.manifest["responses"]), "element_count": sum(p["source"] == "openstreetmap" for p in points),
                    "chain_check_count": len(checks)}
        progress(95, f"{len(points)} günlük ihtiyaç noktası kaydediliyor.")
        return CollectionResult(points, len(points), 0, stamp, metadata, {"snapshot": snapshot, "checks": checks})
    finally:
        if owns:
            client.close()


# --- Measures computed when read ------------------------------------------------------------------------------------------------

def nearest(latitude, longitude, points):
    best = None
    for point in points:
        km = distance_km(latitude, longitude, point["latitude"], point["longitude"])
        if best is None or km < best[0]:
            best = (km, point)
    return best


def summarize(con, run_id, region_order=(), region_names=None):
    """Points of one run, and per region of the latest lodging run the median great-circle distance of its listings to the nearest
    point of each category and to the nearest public beach access, with the share of listings within one mile."""
    snapshot = con.execute("SELECT * FROM poi_snapshots WHERE run_id=?", (run_id,)).fetchone()
    if not snapshot:
        return None
    categories = json.loads(snapshot["categories"])
    points = [{**dict(r), "tags": json.loads(r["tags"]) if r["tags"] else None}
              for r in con.execute("SELECT * FROM poi_points WHERE run_id=? ORDER BY category_key, name", (run_id,))]
    checks = [dict(r) for r in con.execute("SELECT * FROM poi_chain_checks WHERE run_id=? ORDER BY chain, store", (run_id,))]
    destination = con.execute("SELECT destination_id FROM source_runs WHERE id=?", (run_id,)).fetchone()["destination_id"]
    lodging = con.execute("""SELECT r.id, s.searched_on FROM source_runs r JOIN lodging_snapshots s ON s.run_id=r.id
        WHERE r.destination_id=? AND r.status='done' ORDER BY r.rowid DESC LIMIT 1""", (destination,)).fetchone()
    beach = con.execute("""SELECT c.id FROM collections c JOIN source_runs r ON r.id=c.id WHERE r.destination_id=? AND r.status='done'
        ORDER BY r.rowid DESC LIMIT 1""", (destination,)).fetchone()
    beaches = [dict(r) for r in con.execute("SELECT external_id, name, latitude, longitude FROM beach_records WHERE run_id=?", (beach["id"],))] if beach else []
    restaurants = {}
    directory = con.execute("""SELECT id FROM source_runs WHERE destination_id=? AND connector_name='south-walton-restaurants' AND status='done'
        ORDER BY rowid DESC LIMIT 1""", (destination,)).fetchone()
    if directory:
        for row in con.execute("SELECT canonical_region_id, COUNT(DISTINCT external_id) n FROM restaurant_regions WHERE run_id=? GROUP BY canonical_region_id",
                               (directory["id"],)):
            restaurants[row["canonical_region_id"]] = row["n"]
    regions, listings, missing = {}, [], 0
    if lodging:
        for row in con.execute("""SELECT DISTINCT r.lodging_id, f.region_id FROM lodging_search_results r JOIN lodging_filters f
                ON f.run_id=r.run_id AND f.window_key=r.window_key AND f.location_id=r.location_id WHERE r.run_id=?""", (lodging["id"],)):
            regions.setdefault(row["region_id"], set()).add(row["lodging_id"])
        rows = {r["lodging_id"]: dict(r) for r in con.execute("SELECT lodging_id, latitude, longitude FROM lodging_listings WHERE run_id=?", (lodging["id"],))}
        by_category = {c["category_key"]: [p for p in points if p["category_key"] == c["category_key"]] for c in categories}
        measures = {}
        for lodging_id, row in rows.items():
            if row["latitude"] is None or row["longitude"] is None:
                missing += 1
                continue
            entry = {}
            for key, members in [*by_category.items(), ("beach", beaches)]:
                found = nearest(row["latitude"], row["longitude"], members) if members else None
                entry[key] = (round(found[0], 3), found[1].get("point_id") or found[1].get("external_id")) if found else None
            measures[lodging_id] = entry
        listings = measures
    order = {r: i for i, r in enumerate(region_order)}
    names = region_names or {}
    keys = [c["category_key"] for c in categories] + ["beach"]
    table = []
    for region in sorted(regions, key=lambda r: (order.get(r, len(order)), r)):
        members = [listings[i] for i in regions[region] if i in listings]
        row = {"region_id": region, "region_name": names.get(region, region), "listing_count": len(regions[region]), "measured_count": len(members),
               "restaurant_count": restaurants.get(region), "measures": {}}
        for key in keys:
            values = [m[key][0] for m in members if m.get(key)]
            row["measures"][key] = {"median_km": round(statistics.median(values), 3) if values else None,
                                    "median_mi": round(statistics.median(values) / MILE_KM, 2) if values else None,
                                    "within_1mi_share": round(sum(v <= MILE_KM for v in values) / len(values), 3) if values else None,
                                    "count": len(values)}
        table.append(row)
    labels = {c["category_key"]: c["label"] for c in categories}
    labels["beach"] = "Halka açık plaj erişimi (ilçe listesi)"
    return {"snapshot": dict(snapshot), "categories": categories, "labels": labels, "points": points, "checks": checks, "regions": table,
            "lodging_run_id": lodging["id"] if lodging else None, "lodging_searched_on": lodging["searched_on"] if lodging else None,
            "beach_run_id": beach["id"] if beach else None, "beach_count": len(beaches), "missing_coordinates": missing,
            "attribution": ATTRIBUTION, "distance_label": DISTANCE_LABEL, "beach_note": BEACH_NOTE,
            "note": ("OpenStreetMap'e göre, kuş uçuşu mesafe (yol üzerinden hesaplanmadı; 'yürüme mesafesi' denmez). Mahalle, ilanın Book>Direct "
                     "konum filtresinden gelir. Ortanca ve 1 mil içindeki ilan payı bizim hesabımızdır.")}


def listing_measures(con, run_id, lodging_id):
    """One listing's nearest point of each category (name, source, distance) for its detail view."""
    data = summarize(con, run_id)
    if data is None:
        return None
    row = con.execute("SELECT latitude, longitude FROM lodging_listings WHERE run_id=? AND lodging_id=?", (data["lodging_run_id"], lodging_id)).fetchone()
    if not row or row["latitude"] is None:
        return {"lodging_id": lodging_id, "measures": None}
    result = {}
    for category in data["categories"]:
        members = [p for p in data["points"] if p["category_key"] == category["category_key"]]
        found = nearest(row["latitude"], row["longitude"], members) if members else None
        result[category["category_key"]] = {"km": round(found[0], 3), "mi": round(found[0] / MILE_KM, 2), "name": found[1]["name"],
                                            "source": found[1]["source"]} if found else None
    return {"lodging_id": lodging_id, "measures": result}


class DailyNeedsConnector:
    name = "openstreetmap-daily-needs"
    version = CONNECTOR_VERSION
    raw_filename = "manifest.json"
    method = "API"
    diff_enabled = False
    diff_reason = "OpenStreetMap noktaları tarihli okumalardır; sürümler arası fark özeti yerine her sürüm kendi kaynağıyla okunur."

    def supports(self, source):
        return (source.get("url") or "") == SOURCE_URL

    def collect(self, source, raw_path, progress, canceled, *, context):
        return collect(raw_path, progress, canceled, config=context.daily_needs)

    def store_records(self, con, run_id, records, related=None):
        snapshot = related["snapshot"]
        con.execute("""INSERT INTO poi_snapshots (run_id,area,categories,queried_on,osm_timestamp,request_count,element_count,chain_check_count)
            VALUES (?,?,?,?,?,?,?,?)""", (run_id, json.dumps(snapshot["area"]), json.dumps(snapshot["categories"], ensure_ascii=False),
                                          snapshot["queried_on"], snapshot["osm_timestamp"], snapshot["request_count"], snapshot["element_count"],
                                          snapshot["chain_check_count"]))
        con.executemany("""INSERT INTO poi_points (run_id,point_id,category_key,name,brand,latitude,longitude,source,osm_type,osm_id,tags,address,
            source_url,checked_on,note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, p["point_id"], p["category_key"], p["name"], p["brand"], p["latitude"], p["longitude"], p["source"], p["osm_type"], p["osm_id"],
              json.dumps(p["tags"], ensure_ascii=False) if p["tags"] is not None else None, p["address"], p["source_url"], p["checked_on"], p["note"])
             for p in records])
        con.executemany("""INSERT INTO poi_chain_checks (run_id,chain,store,address,latitude,longitude,store_url,checked_on,status,osm_point_id,outcome,note,
            category_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, c["chain"], c["store"], c["address"], c["latitude"], c["longitude"], c["store_url"], c["checked_on"], c["status"],
              c["osm_point_id"], c["outcome"], c["note"], c.get("category_key")) for c in related.get("checks", [])])

    def read_records(self, con, run_id):
        return [dict(r) for r in con.execute("SELECT * FROM poi_points WHERE run_id=? ORDER BY category_key, name", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Daily-need point diff is disabled.")
