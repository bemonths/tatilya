"""Road distances and estimated driving times on the OpenStreetMap road network (GÖREV-20; docs/M19-YOL-MESAFESI.md).
© OpenStreetMap katkıcıları, ODbL.

Generic core: the area, the highway types and their default speeds, the access rules, the snap limit and the extra destinations
(for 30A the two airport terminals) come from the destination configuration in SQLite (`destination_road_networks`). One Overpass
query per run downloads the drivable ways of the area; its raw answer is kept with SHA-256. The fastest routes are computed here, in
the program (studio.sources.road_graph), from every listing of the latest lodging run to every daily-need point of the latest
daily-need run, every public beach access of the latest beach run and every extra destination; per listing and category the point
nearest by road is stored, with the great-circle distance to that same point and to the point nearest in a straight line.

No API key, no routing service. Driving time is length ÷ speed (the way's `maxspeed`, else the configured default of its type); no
traffic, signals or turns: "OpenStreetMap yol ağına göre, trafik hesaba katılmadan tahmini sürüş süresi". Nothing here is a walking
distance.
"""
import json
import statistics
from datetime import datetime, timezone

from . import road_graph
from .base import CollectionResult, SourceError
from .climate_http import Reader, check, make_client, pause
from .geo import distance_km

CONNECTOR_VERSION = "openstreetmap-road-network/1"
SOURCE_URL = "https://www.openstreetmap.org/?kaynak=yol-agi"
OVERPASS_HOST = "overpass-api.de"
OVERPASS_URL = f"https://{OVERPASS_HOST}/api/interpreter"
ATTRIBUTION = "© OpenStreetMap katkıcıları, ODbL"
MAX_BYTES = 120_000_000
MILE_KM = 1.609344
BUSY_WAITS = (30, 60, 120, 240)        # seconds waited before asking again when the public Overpass server is at capacity
BUSY_STATUSES = (429, 502, 503, 504)
DISTANCE_LABEL = "OpenStreetMap yol ağına göre, yol üzerinden mesafe"
TIME_LABEL = "OpenStreetMap yol ağına göre, trafik hesaba katılmadan tahmini sürüş süresi"
BEACH_KEY = "beach"
BEACH_LABEL = "Halka açık plaj erişimi (ilçe listesi)"
NOTE = ("Yol mesafesi ve süre, OpenStreetMap yol ağında programın hesapladığı en hızlı yolun uzunluğu ve süresidir (bizim hesabımız). Süre, "
        "yolun hız sınırından (maxspeed), o yoksa yol türünün yapılandırmadaki varsayılan hızından hesaplanır; trafik, ışık ve dönüş "
        "beklemesi yoktur. 'En yakın' nokta yol mesafesine göre seçilir; kuş uçuşu değer yanında durur. Yürüme mesafesi değildir.")


def overpass_query(area, highway_types):
    bbox = f"{area['south']},{area['west']},{area['north']},{area['east']}"
    kinds = "|".join(sorted(highway_types))
    return f'[out:json][timeout:180];way["highway"~"^({kinds})$"]({bbox})->.r;.r out body qt;.r >;out skel qt;'


def download(reader, query, canceled, waits=BUSY_WAITS):
    """The one road query; when the public server answers "at capacity" it is asked again after growing waits."""
    for attempt, wait in enumerate((0, *waits)):
        pause(wait, canceled)
        try:
            body, _ = reader.get(OVERPASS_URL, suffix=".json", note="yol ağı", content_types={"application/json"}, params={"data": query})
            return body
        except SourceError:
            last = reader.manifest["responses"][-1]["status"] if reader.manifest["responses"] else None
            if last not in BUSY_STATUSES or attempt == len(waits):
                raise
    raise SourceError("Overpass API yol ağı sorgusunu yanıtlamadı.")


def targets_of(inputs, settings):
    """Every destination the listings are measured to: daily-need points, public beach accesses and the configured extra points."""
    targets = []
    for point in inputs.get("points") or ():
        targets.append({"target_key": point["point_id"], "category_key": point["category_key"], "kind": "poi", "name": point.get("name") or point.get("brand"),
                        "latitude": point["latitude"], "longitude": point["longitude"]})
    for beach in inputs.get("beaches") or ():
        targets.append({"target_key": f"{BEACH_KEY}/{beach['external_id']}", "category_key": BEACH_KEY, "kind": "beach", "name": beach["name"],
                        "latitude": beach["latitude"], "longitude": beach["longitude"]})
    for extra in settings.get("extra_points") or ():
        targets.append({"target_key": f"extra/{extra['key']}", "category_key": f"extra:{extra['key']}", "kind": "extra", "name": extra["label"],
                        "latitude": extra["latitude"], "longitude": extra["longitude"]})
    return targets


def length_checks(graph, settings):
    """Known road lengths against the network's (each named way counted once along its mapped length)."""
    results = []
    for item in settings.get("length_checks") or ():
        km = sum(graph.refs.get(ref, 0.0) for ref in item["refs"])
        miles = km / MILE_KM
        results.append({"label": item["label"], "refs": item["refs"], "expected_miles": item["expected_miles"], "osm_miles": round(miles, 3),
                        "difference_percent": round((miles - item["expected_miles"]) / item["expected_miles"] * 100, 1) if km else None,
                        "source": item.get("source"), "reference_id": item.get("reference_id")})
    return results


def measure(graph, listings, targets, settings, progress=None, canceled=lambda: False):
    """(nearest rows, targets with snap and reach counts, counts). For every listing tied to the network and every category, the
    target nearest by road with the trip's km and minutes, the great-circle km to it and the great-circle-nearest target."""
    limit = settings["snap_limit_m"] / 1000.0
    snap_rate = 1.0 / (settings["snap_speed_mph"] * MILE_KM)
    origins = {}
    for listing in listings:
        if listing.get("latitude") is None or listing.get("longitude") is None:
            continue
        snapped = graph.snap(listing["latitude"], listing["longitude"], limit)
        if snapped:
            origins[listing["lodging_id"]] = (listing, snapped)
    best, crow_best = {}, {}
    for number, target in enumerate(targets):
        check(canceled)
        snapped = graph.snap(target["latitude"], target["longitude"], limit)
        target["snap_m"] = round(snapped["leg_km"] * 1000, 1) if snapped else None
        target["reached_count"] = 0
        category = target["category_key"]
        table = graph.to_target(snapped) if snapped else None
        for lodging_id, (listing, origin) in origins.items():
            crow = distance_km(listing["latitude"], listing["longitude"], target["latitude"], target["longitude"])
            key = (lodging_id, category)
            if key not in crow_best or crow < crow_best[key][0]:
                crow_best[key] = (crow, target["target_key"])
            trip = graph.trip(origin, snapped, table, snap_rate) if snapped else None
            if trip is None:
                continue
            target["reached_count"] += 1
            km, hours = trip
            if km < crow:
                if crow - km > 1e-6:
                    raise SourceError("Yol mesafesi kuş uçuşu mesafeden kısa çıktı; hesap kaydedilmedi.")
                km = crow
            if key not in best or (km, hours) < (best[key]["road_km"], best[key]["minutes"] / 60.0):
                best[key] = {"lodging_id": lodging_id, "category_key": category, "target_key": target["target_key"], "road_km": km,
                             "minutes": hours * 60.0, "crow_km": crow, "snap_m": round(origin["leg_km"] * 1000, 1)}
        if progress:
            progress(number + 1, len(targets))
    rows = []
    for key, row in best.items():
        crow, crow_key = crow_best[key]
        crow_same = round(row["crow_km"], 4)
        rows.append({**row, "road_km": max(round(row["road_km"], 4), crow_same), "minutes": round(row["minutes"], 2), "crow_km": crow_same,
                     "crow_nearest_key": crow_key, "crow_nearest_km": round(crow, 4)})
    rows.sort(key=lambda r: (r["lodging_id"], r["category_key"]))
    measured = {row["lodging_id"] for row in rows}
    return rows, targets, {"listing_count": len(listings), "tied_count": len(origins), "measured_count": len(measured)}


def collect(raw_path, progress, canceled, *, config, client=None, today=None, waits=BUSY_WAITS):
    if not config or not config.get("settings"):
        raise SourceError("Bu destinasyon için yol ağı yapılandırılmamış.")
    settings, inputs = config["settings"], config.get("input")
    if not inputs or not inputs.get("listings"):
        raise SourceError("Yol mesafesi için önce bir konaklama çekimi gerekir (ilanlar ve koordinatları oradan gelir).")
    targets = targets_of(inputs, settings)
    if not targets:
        raise SourceError("Yol mesafesi ölçülecek nokta yok: önce günlük ihtiyaç noktaları ya da plaj erişimleri toplanmalı.")
    owns = client is None
    client = client or make_client()
    reader = Reader(client, raw_path, canceled, connector=CONNECTOR_VERSION, hosts={OVERPASS_HOST}, max_bytes=MAX_BYTES, label="Overpass API")
    try:
        progress(3, "OpenStreetMap yol ağı indiriliyor (Overpass API, tek sorgu).")
        query = overpass_query(settings["area"], settings["speeds_mph"])
        body = download(reader, query, canceled, waits)
        progress(30, "Yol ağı okundu; grafik kuruluyor.")
        try:
            nodes, ways, _, stamp = road_graph.parse(body)
        except road_graph.RoadDataError as exc:
            raise SourceError(str(exc)) from exc
        graph = road_graph.build(nodes, ways, settings)
        if not graph.segments:
            raise SourceError("Overpass yanıtında yapılandırılmış türde yol yok.")
        progress(40, f"{graph.way_count} yol, {round(graph.km)} km; {len(inputs['listings'])} ilandan {len(targets)} noktaya yollar hesaplanıyor.")
        rows, targets, counts = measure(graph, inputs["listings"], targets, settings,
                                        lambda done, total: progress(40 + int(55 * done / total), f"Yollar hesaplanıyor: {done}/{total} nokta."), canceled)
        today = (today or datetime.now(timezone.utc).date()).isoformat()
        checks = length_checks(graph, settings)
        snapshot = {"settings": settings, "queried_on": today, "osm_timestamp": stamp, "request_count": len(reader.manifest["responses"]),
                    "way_count": graph.way_count, "node_count": len(graph.ids), "network_km": round(graph.km, 1),
                    "maxspeed_km": round(graph.speed_sources["maxspeed"], 1), "lodging_run_id": inputs.get("lodging_run_id"),
                    "poi_run_id": inputs.get("poi_run_id"), "beach_run_id": inputs.get("beach_run_id"), **counts,
                    "target_count": len(targets), "checks": checks}
        metadata = {"area": settings["area"], "query": query, "osm_timestamp": stamp, "request_count": snapshot["request_count"],
                    "way_count": graph.way_count, "network_km": snapshot["network_km"], "maxspeed_km": snapshot["maxspeed_km"],
                    "lodging_run_id": snapshot["lodging_run_id"], "poi_run_id": snapshot["poi_run_id"], "beach_run_id": snapshot["beach_run_id"],
                    **counts, "target_count": len(targets), "length_checks": checks, "attribution": ATTRIBUTION}
        progress(97, f"{counts['measured_count']} ilanın yol mesafeleri kaydediliyor.")
        return CollectionResult(rows, len(rows), counts["listing_count"] - counts["measured_count"], stamp, metadata,
                                {"snapshot": snapshot, "targets": targets})
    finally:
        if owns:
            client.close()


# --- Measures read back -----------------------------------------------------------------------------------------------------------

def latest_run(con, destination_id):
    return con.execute("""SELECT r.id FROM source_runs r JOIN road_snapshots s ON s.run_id=r.id WHERE r.destination_id=? AND r.status='done'
        ORDER BY r.rowid DESC LIMIT 1""", (destination_id,)).fetchone()


def category_labels(con, snapshot, settings):
    labels = {}
    if snapshot["poi_run_id"]:
        row = con.execute("SELECT categories FROM poi_snapshots WHERE run_id=?", (snapshot["poi_run_id"],)).fetchone()
        for category in json.loads(row["categories"]) if row else ():
            labels[category["category_key"]] = category["label"]
    labels[BEACH_KEY] = BEACH_LABEL
    for extra in settings.get("extra_points") or ():
        labels[f"extra:{extra['key']}"] = extra["label"]
    return labels


def summarize(con, run_id, region_order=(), region_names=None):
    """Per region of the run's lodging run and per category: the median road distance and driving time of its listings to the point
    nearest by road, the median great-circle distance to the point nearest in a straight line (the same listings), and the share of
    listings within one road mile. Medians and shares are our calculation."""
    snapshot = con.execute("SELECT * FROM road_snapshots WHERE run_id=?", (run_id,)).fetchone()
    if not snapshot:
        return None
    snapshot = {**dict(snapshot), "settings": json.loads(snapshot["settings"]), "checks": json.loads(snapshot["checks"])}
    settings = snapshot["settings"]
    labels = category_labels(con, snapshot, settings)
    destination = con.execute("SELECT destination_id FROM source_runs WHERE id=?", (run_id,)).fetchone()["destination_id"]
    regions = {}
    if snapshot["lodging_run_id"]:
        for row in con.execute("""SELECT DISTINCT r.lodging_id, f.region_id FROM lodging_search_results r JOIN lodging_filters f
                ON f.run_id=r.run_id AND f.window_key=r.window_key AND f.location_id=r.location_id WHERE r.run_id=?""", (snapshot["lodging_run_id"],)):
            regions.setdefault(row["region_id"], set()).add(row["lodging_id"])
    by_listing = {}
    for row in con.execute("SELECT * FROM road_nearest WHERE run_id=?", (run_id,)):
        by_listing.setdefault(row["lodging_id"], {})[row["category_key"]] = row
    targets = [dict(r) for r in con.execute("SELECT * FROM road_targets WHERE run_id=? ORDER BY category_key, name", (run_id,))]
    names = {t["target_key"]: t["name"] for t in targets}
    order = {r: i for i, r in enumerate(region_order)}
    region_names = region_names or {}
    keys = [k for k in labels if any(t["category_key"] == k for t in targets)]
    table = []
    for region in sorted(regions, key=lambda r: (order.get(r, len(order)), r)):
        members = [by_listing[i] for i in regions[region] if i in by_listing]
        row = {"region_id": region, "region_name": region_names.get(region, region), "listing_count": len(regions[region]),
               "measured_count": len(members), "measures": {}}
        for key in keys:
            found = [m[key] for m in members if key in m]
            if not found:
                row["measures"][key] = {"count": 0, "road_median_km": None, "road_median_mi": None, "minutes_median": None,
                                        "crow_median_km": None, "crow_median_mi": None, "within_1mi_share": None, "changed_share": None,
                                        "most_common": None}
                continue
            road = statistics.median(f["road_km"] for f in found)
            crow = statistics.median(f["crow_nearest_km"] for f in found)
            common = statistics.mode(f["target_key"] for f in found)
            row["measures"][key] = {
                "count": len(found), "road_median_km": round(road, 3), "road_median_mi": round(road / MILE_KM, 2),
                "minutes_median": round(statistics.median(f["minutes"] for f in found), 1),
                "crow_median_km": round(crow, 3), "crow_median_mi": round(crow / MILE_KM, 2),
                "within_1mi_share": round(sum(f["road_km"] <= MILE_KM for f in found) / len(found), 3),
                "changed_share": round(sum(f["target_key"] != f["crow_nearest_key"] for f in found) / len(found), 3),
                "most_common": {"target_key": common, "name": names.get(common), "share": round(sum(f["target_key"] == common for f in found) / len(found), 3)}}
        table.append(row)
    latest = {
        "lodging": con.execute("""SELECT r.id FROM source_runs r JOIN lodging_snapshots s ON s.run_id=r.id WHERE r.destination_id=? AND r.status='done'
            ORDER BY r.rowid DESC LIMIT 1""", (destination,)).fetchone(),
        "poi": con.execute("""SELECT r.id FROM source_runs r JOIN poi_snapshots s ON s.run_id=r.id WHERE r.destination_id=? AND r.status='done'
            ORDER BY r.rowid DESC LIMIT 1""", (destination,)).fetchone()}
    stale = [label for label, key in (("konaklama çekimi", "lodging"), ("günlük ihtiyaç çekimi", "poi"))
             if latest[key] and snapshot[f"{key}_run_id"] and latest[key]["id"] != snapshot[f"{key}_run_id"]]
    return {"snapshot": snapshot, "labels": labels, "categories": keys, "targets": targets, "regions": table,
            "stale_inputs": stale, "attribution": ATTRIBUTION, "distance_label": DISTANCE_LABEL, "time_label": TIME_LABEL, "note": NOTE,
            "speeds_mph": settings["speeds_mph"], "unmeasured_count": snapshot["listing_count"] - snapshot["measured_count"]}


class RoadNetworkConnector:
    name = "openstreetmap-road-network"
    version = CONNECTOR_VERSION
    raw_filename = "manifest.json"
    method = "API"
    diff_enabled = False
    diff_reason = "Yol mesafeleri çekim anındaki yol ağı, ilanlar ve noktalarla hesaplanır; sürümler arası fark özeti yerine her sürüm kendi girdileriyle okunur."
    follows = ("bookdirect-lodging", "openstreetmap-daily-needs")     # due again when its listings or points have a newer run
    inputs = ("lodging_listings", "road_inputs")     # the listings are the origins: a batch skips this when its lodging run failed

    def supports(self, source):
        return (source.get("url") or "") == SOURCE_URL

    def collect(self, source, raw_path, progress, canceled, *, context):
        return collect(raw_path, progress, canceled, config=context.road_network)

    def store_records(self, con, run_id, records, related=None):
        snapshot = related["snapshot"]
        con.execute("""INSERT INTO road_snapshots (run_id,settings,queried_on,osm_timestamp,request_count,way_count,node_count,network_km,maxspeed_km,
            lodging_run_id,poi_run_id,beach_run_id,listing_count,tied_count,measured_count,target_count,checks) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (run_id, json.dumps(snapshot["settings"], ensure_ascii=False), snapshot["queried_on"], snapshot["osm_timestamp"],
                     snapshot["request_count"], snapshot["way_count"], snapshot["node_count"], snapshot["network_km"], snapshot["maxspeed_km"],
                     snapshot["lodging_run_id"], snapshot["poi_run_id"], snapshot["beach_run_id"], snapshot["listing_count"], snapshot["tied_count"],
                     snapshot["measured_count"], snapshot["target_count"], json.dumps(snapshot["checks"], ensure_ascii=False)))
        con.executemany("""INSERT INTO road_targets (run_id,target_key,category_key,kind,name,latitude,longitude,snap_m,reached_count)
            VALUES (?,?,?,?,?,?,?,?,?)""", [(run_id, t["target_key"], t["category_key"], t["kind"], t["name"], t["latitude"], t["longitude"],
                                             t["snap_m"], t["reached_count"]) for t in related["targets"]])
        con.executemany("""INSERT INTO road_nearest (run_id,lodging_id,category_key,target_key,road_km,minutes,crow_km,crow_nearest_key,crow_nearest_km,snap_m)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", [(run_id, r["lodging_id"], r["category_key"], r["target_key"], r["road_km"], r["minutes"], r["crow_km"],
                                               r["crow_nearest_key"], r["crow_nearest_km"], r["snap_m"]) for r in records])

    def read_records(self, con, run_id):
        return [dict(r) for r in con.execute("SELECT * FROM road_nearest WHERE run_id=? ORDER BY lodging_id, category_key", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Road distance diff is disabled.")
