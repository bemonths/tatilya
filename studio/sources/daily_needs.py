"""Daily-need points from OpenStreetMap (Overpass API): supermarkets and grocery stores, convenience stores, pharmacies, urgent care
and bicycle rental, for the destination's configured area and categories. © OpenStreetMap katkıcıları, ODbL.

Generic core: the area (a bounding box) and the categories (OpenStreetMap tag sets) come from the destination configuration in
SQLite; one small Overpass query per run, its raw answer kept with SHA-256. Supermarkets are cross-checked by a person against the
chains' own store locators (a reviewed destination file): a store the chain's site lists that OpenStreetMap lacks is added as a
point labelled "zincirin kendi sitesi"; an OpenStreetMap store the chain's site shows as closed is reported.

Distances are computed when read: great-circle ("kuş uçuşu") from each listing of the latest lodging run to the nearest point of
each category and to the nearest public beach access of the county list; nothing about walking routes is claimed.
"""
import csv
import json
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
            clauses.append(f"nwr{selector}({bbox});")
    return f"[out:json][timeout:90];({''.join(clauses)});out center tags;"


def category_of(tags, categories):
    """The first category one of whose tag sets the element carries in full; None when none."""
    for category in categories:
        if any(all(tags.get(key) == value for key, value in wanted.items()) for wanted in category["filters"]):
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


def read_chain_checks(path):
    if not path or not Path(path).is_file():
        return []
    with open(path, encoding="utf-8-sig") as handle:
        rows = [dict(r) for r in csv.DictReader(handle)]
    for row in rows:
        if row.get("durum") not in CHAIN_STATUSES:
            raise SourceError(f"Zincir mağaza dosyasında bilinmeyen durum: {row.get('durum')!r}.")
    return rows


def same_brand(chain, point):
    words = chain.lower().replace("'", "")
    text = " ".join(v for v in (point.get("brand"), point.get("name")) if v).lower().replace("'", "")
    return words in text or (text and text.split()[0] in words.split())


def merge_chain_checks(points, rows, supermarket_key="supermarket"):
    """(points with the chain sites' additions, check rows with their outcome)."""
    by_id = {p["point_id"]: p for p in points}
    checks = []
    for row in rows:
        latitude = float(row["enlem"]) if row.get("enlem") else None
        longitude = float(row["boylam"]) if row.get("boylam") else None
        osm = by_id.get((row.get("osm_id") or "").strip())
        if osm is None and latitude is not None and row["durum"] in ("açık", "kapalı"):
            near = [p for p in points if p["category_key"] == supermarket_key and same_brand(row["zincir"], p)
                    and distance_km(latitude, longitude, p["latitude"], p["longitude"]) <= MATCH_KM]
            osm = min(near, key=lambda p: distance_km(latitude, longitude, p["latitude"], p["longitude"])) if near else None
        if row["durum"] == "açık" and osm is not None:
            outcome = "osm_ile_ayni"
        elif row["durum"] == "açık":
            if latitude is None or longitude is None:
                raise SourceError(f"Zincir mağaza dosyasında koordinatsız açık mağaza: {row['zincir']} · {row['magaza']}.")
            outcome = "eklendi"
            points.append({"point_id": f"zincir/{row['zincir']}/{row['magaza']}", "category_key": supermarket_key, "name": row["magaza"],
                           "brand": row["zincir"], "latitude": latitude, "longitude": longitude, "source": "zincirin kendi sitesi",
                           "osm_type": None, "osm_id": None, "tags": None, "address": row.get("adres") or None, "source_url": row.get("magaza_url") or None,
                           "checked_on": row.get("kontrol_tarihi") or None, "note": row.get("not") or None})
        elif row["durum"] == "kapalı" and osm is not None:
            outcome = "osmde_var_zincirde_kapali"
            osm["note"] = f"{row['zincir']} sitesinde kapalı görünüyor ({row.get('kontrol_tarihi')})."
        elif row["durum"] == "bölgede mağaza yok":
            outcome = "bolgede_yok"
        else:
            outcome = "okunamadi" if row["durum"] == "okunamadı" else "bolgede_yok"
        checks.append({"chain": row["zincir"], "store": row["magaza"], "address": row.get("adres") or None, "latitude": latitude,
                       "longitude": longitude, "store_url": row.get("magaza_url") or None, "checked_on": row.get("kontrol_tarihi"),
                       "status": row["durum"], "osm_point_id": osm["point_id"] if osm else None, "outcome": outcome, "note": row.get("not") or None})
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
        progress(70, f"{len(points)} nokta okundu; zincir mağaza kontrolü ekleniyor.")
        points, checks = merge_chain_checks(points, read_chain_checks(config.get("chain_checks")))
        today = (today or datetime.now(timezone.utc).date()).isoformat()
        counts = {c["category_key"]: sum(p["category_key"] == c["category_key"] for p in points) for c in categories}
        metadata = {"area": area, "categories": [{k: c[k] for k in ("category_key", "label")} for c in categories], "query": query,
                    "osm_timestamp": stamp, "request_count": len(reader.manifest["responses"]), "point_counts": counts,
                    "chain_checks": len(checks), "added_from_chains": sum(c["outcome"] == "eklendi" for c in checks), "attribution": ATTRIBUTION}
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
        con.executemany("""INSERT INTO poi_chain_checks (run_id,chain,store,address,latitude,longitude,store_url,checked_on,status,osm_point_id,outcome,note)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, c["chain"], c["store"], c["address"], c["latitude"], c["longitude"], c["store_url"], c["checked_on"], c["status"],
              c["osm_point_id"], c["outcome"], c["note"]) for c in related.get("checks", [])])

    def read_records(self, con, run_id):
        return [dict(r) for r in con.execute("SELECT * FROM poi_points WHERE run_id=? ORDER BY category_key, name", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Daily-need point diff is disabled.")
