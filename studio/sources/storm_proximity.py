"""NOAA NHC HURDAT2 (Atlantic best track) -> tropical cyclone passages near a destination's coastal corridor.

Destination-independent: the corridor (a great-circle segment) and the radii come from SQLite configuration.
Method: 1-hour linear interpolation between track points; only tropical and subtropical stages (TD, TS, HU, SD, SS)
count: per storm the closest distance to the corridor; per radius the first time the track enters the corridor buffer,
and the highest wind while inside -> class. A storm that was inside a radius only in other stages (EX, LO, WV, DB) is
kept but flagged and stays out of every count. All counts are our calculation from NOAA data, not an NHC product.
"""
import json
import math
import re
from datetime import datetime, timedelta, timezone

from .base import CollectionResult, SourceError
from .climate_http import Reader, check, make_client
from .geo import KM_PER_NMI, Segment
from .url_identity import https_source_identity

SOURCE_URL = "https://www.nhc.noaa.gov/data/"
HOSTS = frozenset({"www.nhc.noaa.gov"})
SOURCE_IDENTITY = https_source_identity(SOURCE_URL, host_aliases={"www.nhc.noaa.gov": "www.nhc.noaa.gov"})
CONNECTOR_VERSION = "hurdat2-storm-proximity/2"
# The Atlantic file is linked from the NHC data page; its name changes with every release.
FILE_LINK = re.compile(r'href="(/data/hurdat/hurdat2-(\d{4})-(\d{4})-(\d{6})\.txt)"')
HEADER = re.compile(r"[A-Z]{2}\d{6}")
MAX_PAGE_BYTES, MAX_FILE_BYTES = 2_000_000, 40_000_000
STEP = timedelta(hours=1)
# Saffir-Simpson based classes by the highest sustained wind (kt) while inside the radius.
CLASSES = (("MH", 96), ("HU", 64), ("TS", 34), ("TD", 0))
CLASS_LABELS = {"TD": "tropikal depresyon", "TS": "tropikal fırtına", "HU": "kasırga", "MH": "büyük kasırga"}
# HURDAT2 status codes of tropical and subtropical stages (manager decision, GOREV-06). EX, LO, WV and DB never count.
TROPICAL_STATUSES = frozenset({"TD", "TS", "HU", "SD", "SS"})


def storm_class(wind):
    if wind is None:
        return None
    return next(name for name, limit in CLASSES if wind >= limit)


def coordinate(value, positive, negative, limit, label):
    value = value.strip()
    if len(value) < 2 or value[-1] not in (positive, negative):
        raise SourceError(f"HURDAT2 {label} okunamadı: {value!r}.")
    try:
        number = float(value[:-1])
    except ValueError as exc:
        raise SourceError(f"HURDAT2 {label} okunamadı: {value!r}.") from exc
    if not 0 <= number <= limit:
        raise SourceError(f"HURDAT2 {label} aralık dışında: {value!r}.")
    return number if value[-1] == positive else -number


def parse_hurdat2(text):
    """Return storms: {storm_id, name, season, fixes: [(time, status, latitude, longitude, wind or None)]}."""
    lines = [line for line in text.splitlines() if line.strip()]
    storms, index = [], 0
    while index < len(lines):
        header = [part.strip() for part in lines[index].split(",")]
        if len(header) < 3 or not HEADER.fullmatch(header[0]) or not header[2].isdigit():
            raise SourceError(f"HURDAT2 {index + 1}. satırda fırtına başlığı bekleniyordu.")
        storm_id, name, count = header[0], header[1], int(header[2])
        if count == 0 or index + count >= len(lines):
            raise SourceError(f"HURDAT2 {storm_id} için iz satırı sayısı tutmuyor.")
        fixes = []
        for offset in range(1, count + 1):
            parts = [part.strip() for part in lines[index + offset].split(",")]
            if len(parts) < 8 or HEADER.fullmatch(parts[0]):
                raise SourceError(f"HURDAT2 {storm_id} iz satırları eksik ({index + offset + 1}. satır).")
            try:
                when = datetime.strptime(parts[0] + parts[1].zfill(4), "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
                wind = int(parts[6])
            except ValueError as exc:
                raise SourceError(f"HURDAT2 {storm_id} iz satırı okunamadı ({index + offset + 1}. satır).") from exc
            fixes.append((when, parts[3], coordinate(parts[4], "N", "S", 90, "enlem"), coordinate(parts[5], "E", "W", 180, "boylam"),
                          wind if wind >= 0 else None))
        if any(later[0] <= earlier[0] for earlier, later in zip(fixes, fixes[1:])):
            raise SourceError(f"HURDAT2 {storm_id} iz zamanları sıralı değil.")
        storms.append({"storm_id": storm_id, "name": name, "season": int(storm_id[4:8]), "fixes": fixes})
        index += count + 1
    if not storms:
        raise SourceError("HURDAT2 dosyasında fırtına bulunamadı.")
    return storms


def hourly(fixes):
    """Track points every hour between consecutive fixes (linear in latitude, longitude and wind), plus the last fix."""
    points = []
    for (t0, status, lat0, lon0, wind0), (t1, _, lat1, lon1, wind1) in zip(fixes, fixes[1:]):
        span = (t1 - t0).total_seconds()
        current = t0
        while current < t1:
            fraction = (current - t0).total_seconds() / span
            wind = wind0 + (wind1 - wind0) * fraction if wind0 is not None and wind1 is not None else (wind0 if current == t0 else None)
            points.append((current, lat0 + (lat1 - lat0) * fraction, lon0 + (lon1 - lon0) * fraction, wind, status))
            current += STEP
    last = fixes[-1]
    points.append((last[0], last[2], last[3], last[4], last[1]))
    return points


def summary(points, radius_km):
    """First point inside the radius, highest known wind inside (with its stage) and the closest distance of the points."""
    inside = [point for point in points if point[1] <= radius_km]
    if not inside:
        return None
    winds = [(point[2], point[3]) for point in inside if point[2] is not None]
    top = max(winds, key=lambda item: item[0]) if winds else (None, None)
    # Floor keeps the stored wind and its class consistent (thresholds are whole knots).
    return inside[0][0], math.floor(top[0]) if top[0] is not None else None, top[1]


def passages(storms, corridor, radii_nmi):
    """Per storm and radius: first entry into the corridor buffer, closest distance and highest wind inside.

    Only points whose stage is tropical or subtropical count; interpolated points carry the stage of the fix that
    starts their interval. A storm inside a radius only in other stages is returned with non_tropical_only=1,
    no class, and values measured on those other stages, so it stays visible but out of every count.
    """
    segment = Segment((corridor["west_latitude"], corridor["west_longitude"]), (corridor["east_latitude"], corridor["east_longitude"]))
    largest = max(radii_nmi) * KM_PER_NMI
    results = []
    for storm in storms:
        # Cheap screen on the fixes: consecutive fixes are at most a few hundred km apart.
        if min(segment.distance_km(lat, lon) for _, _, lat, lon, _ in storm["fixes"]) > largest + 1500:
            continue
        points = [(time, segment.distance_km(lat, lon), wind, status) for time, lat, lon, wind, status in hourly(storm["fixes"])]
        tropical = [point for point in points if point[3] in TROPICAL_STATUSES]
        for radius in sorted(radii_nmi):
            radius_km = radius * KM_PER_NMI
            found = summary(tropical, radius_km)
            flagged = found is None
            if flagged:
                found = summary(points, radius_km)
                if found is None:
                    continue
            entry, max_wind, status = found
            closest = min(point[1] for point in (points if flagged else tropical))
            results.append({"storm_id": storm["storm_id"], "name": storm["name"], "season": storm["season"], "radius_nmi": radius,
                            "first_entry_time": entry.strftime("%Y-%m-%dT%H:%MZ"), "first_entry_month": entry.month,
                            "closest_km": round(closest, 1), "closest_nmi": round(closest / KM_PER_NMI, 1),
                            "max_wind_kt": max_wind, "storm_class": None if flagged else storm_class(max_wind),
                            "status_at_max": status, "non_tropical_only": int(flagged)})
    return results


def monthly_counts(records, radius, first_season=None, last_season=None):
    """Storms per first-entry month and class for one radius and an optional season range (each storm once).

    Records flagged non_tropical_only never count.
    """
    table = {month: {"TD": 0, "TS": 0, "HU": 0, "MH": 0, "bilinmiyor": 0} for month in range(1, 13)}
    for record in records:
        if record["radius_nmi"] != radius or record.get("non_tropical_only"):
            continue
        if (first_season and record["season"] < first_season) or (last_season and record["season"] > last_season):
            continue
        table[record["first_entry_month"]][record["storm_class"] or "bilinmiyor"] += 1
    return table


def collect(raw_path, progress, canceled, *, corridor, client=None):
    if not corridor:
        raise SourceError("Bu destinasyon için kasırga kıyı koridoru yapılandırılmamış.")
    radii = corridor["radii_nmi"]
    if not radii or any(not isinstance(r, (int, float)) or r <= 0 for r in radii):
        raise SourceError("Kasırga yarıçapları geçersiz.")
    owns = client is None
    client = client or make_client()
    reader = Reader(client, raw_path, canceled, connector=CONNECTOR_VERSION, hosts=HOSTS, max_bytes=MAX_FILE_BYTES, label="NHC HURDAT2")
    try:
        progress(5, "NHC veri sayfasından güncel HURDAT2 dosya adı okunuyor.")
        page, final = reader.get(SOURCE_URL, suffix=".html", note="nhc-data-page", content_types={"text/html"})
        links = sorted(set(FILE_LINK.findall(page.decode("utf-8", errors="replace"))))
        if len(links) != 1:
            raise SourceError("NHC veri sayfasında tek bir Atlantik HURDAT2 bağlantısı bulunamadı; sayfa değişmiş olabilir.")
        path = links[0][0]
        file_name = path.rsplit("/", 1)[1]
        progress(20, f"{file_name} indiriliyor.")
        body, _ = reader.get(reader.checked(path, final), suffix=".txt", note=file_name, content_types={"text/plain"})
        check(canceled)
        try:
            text = body.decode("ascii")
        except UnicodeError as exc:
            raise SourceError("HURDAT2 dosyasının karakter kodlaması beklenmiyor.") from exc
        progress(45, "Fırtına izleri ayrıştırılıyor.")
        storms = parse_hurdat2(text)
        check(canceled)
        progress(60, f"{len(storms)} fırtına için koridor mesafesi hesaplanıyor.")
        records = passages(storms, corridor, radii)
        check(canceled)
        seasons = [storm["season"] for storm in storms]
        metadata = {"hurdat_file": file_name, "hurdat_url": f"https://www.nhc.noaa.gov{path}", "storm_count": len(storms),
                    "first_season": min(seasons), "last_season": max(seasons), "radii_nmi": list(radii),
                    "passages": {str(radius): sum(r["radius_nmi"] == radius and not r["non_tropical_only"] for r in records) for radius in radii},
                    "non_tropical_only": {str(radius): sum(r["radius_nmi"] == radius and r["non_tropical_only"] for r in records) for radius in radii},
                    "tropical_statuses": sorted(TROPICAL_STATUSES),
                    "scope": "NOAA NHC HURDAT2 Atlantik izleri; yalnız tropikal ve subtropikal evreler (TD, TS, HU, SD, SS) sayılır; "
                             "koridor mesafesi, ilk giriş ve sınıf bizim hesabımızdır."}
        related = {"corridor": {**{key: corridor[key] for key in ("label", "west_latitude", "west_longitude", "west_reference",
                                                                     "east_latitude", "east_longitude", "east_reference")},
                                "radii_nmi": list(radii), "hurdat_file": file_name, "storm_count": len(storms),
                                "first_season": min(seasons), "last_season": max(seasons)}}
        counted = {r["storm_id"] for r in records if not r["non_tropical_only"]}
        progress(95, f"{len(storms)} fırtınadan {len(counted)} tanesi tropikal/subtropikal evrede koridora {max(radii)} deniz mili içinden geçti.")
        return CollectionResult(records, len(storms), 0, None, metadata, related)
    finally:
        if owns:
            client.close()


class StormProximityConnector:
    name = "hurdat2-storm-proximity"
    version = CONNECTOR_VERSION
    raw_filename = "manifest.json"
    method = "Dosya"
    diff_enabled = False
    diff_reason = "Kasırga geçişleri her HURDAT2 sürümünden yeniden hesaplanan geçmiş kayıtlardır; sürümler arası kayıt farkı özeti gösterilmiyor."
    tropical_statuses = TROPICAL_STATUSES

    def supports(self, source):
        return https_source_identity(source["url"], host_aliases={"www.nhc.noaa.gov": "www.nhc.noaa.gov"}) == SOURCE_IDENTITY

    def collect(self, source, raw_path, progress, canceled, *, context):
        return collect(raw_path, progress, canceled, corridor=context.storm_corridor)

    def store_records(self, con, run_id, records, related=None):
        corridor = (related or {}).get("corridor")
        if corridor:
            con.execute("""INSERT INTO storm_corridor_snapshots (run_id,label,west_latitude,west_longitude,west_reference,east_latitude,
                east_longitude,east_reference,radii_nmi,hurdat_file,storm_count,first_season,last_season) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, corridor["label"], corridor["west_latitude"], corridor["west_longitude"], corridor["west_reference"],
                 corridor["east_latitude"], corridor["east_longitude"], corridor["east_reference"], json.dumps(corridor["radii_nmi"]),
                 corridor["hurdat_file"], corridor["storm_count"], corridor["first_season"], corridor["last_season"]))
        for record in records:
            con.execute("""INSERT INTO storm_passages (run_id,storm_id,name,season,radius_nmi,first_entry_time,first_entry_month,
                closest_km,closest_nmi,max_wind_kt,storm_class,status_at_max,non_tropical_only) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, record["storm_id"], record["name"], record["season"], record["radius_nmi"], record["first_entry_time"],
                 record["first_entry_month"], record["closest_km"], record["closest_nmi"], record["max_wind_kt"],
                 record["storm_class"], record["status_at_max"], record.get("non_tropical_only", 0)))

    def read_records(self, con, run_id):
        return [dict(row) for row in con.execute(
            "SELECT * FROM storm_passages WHERE run_id=? ORDER BY radius_nmi, first_entry_time, storm_id", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Storm passage diff is disabled.")

    def read_snapshot(self, con, run_id):
        row = con.execute("SELECT * FROM storm_corridor_snapshots WHERE run_id=?", (run_id,)).fetchone()
        corridor = dict(row) if row else None
        if corridor:
            corridor["radii_nmi"] = json.loads(corridor["radii_nmi"])
        return {"corridor": corridor, "passages": self.read_records(con, run_id), "class_labels": CLASS_LABELS,
                "tropical_statuses": sorted(TROPICAL_STATUSES)}
