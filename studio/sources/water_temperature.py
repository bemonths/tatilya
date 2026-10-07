"""NOAA NDBC historical standard meteorological annual files -> monthly sea water temperature (WTMP).

Destination-independent: stations and the first year to try come from the destination's climate configuration.
Raw 6-minute (or hourly) values are not stored in the database; the annual files are kept with SHA-256.
Year-month means are our calculation from NOAA data, not an official NOAA product.
"""
import gzip
import json
import math
from datetime import datetime, timezone

from .base import CollectionResult, SourceError
from .climate_http import Reader, check, make_client
from .url_identity import https_source_identity

SOURCE_URL = "https://www.ndbc.noaa.gov/"
FILE_URL = "https://www.ndbc.noaa.gov/data/historical/stdmet/{station}h{year}.txt.gz"
HOSTS = frozenset({"www.ndbc.noaa.gov"})
SOURCE_IDENTITY = https_source_identity(SOURCE_URL, host_aliases={"www.ndbc.noaa.gov": "www.ndbc.noaa.gov"})
CONNECTOR_VERSION = "ndbc-water-temperature/1"
MAX_BYTES = 30_000_000
# NDBC fills missing values with 99, 999 or 9999 depending on the column width.
MISSING_MARKERS = (99.0, 999.0, 9999.0)
# A year-month enters the multi-year mean only with at least this many days that have data.
MIN_DAYS = 20
GZIP_TYPES = {"application/x-gzip", "application/gzip", "application/octet-stream"}


def missing(value):
    return any(math.isclose(value, marker) for marker in MISSING_MARKERS)


def parse_year(body, label):
    """Return {(year, month): [sum, count, set(days)]} and counts for one annual file."""
    try:
        text = gzip.decompress(body).decode("latin-1")
    except (OSError, EOFError) as exc:
        raise SourceError(f"{label} dosyası açılamadı (gzip).") from exc
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise SourceError(f"{label} dosyası boş.")
    names = lines[0].lstrip("#").upper().split()
    if "WTMP" not in names or len(names) < 5:
        raise SourceError(f"{label} dosyasında WTMP sütunu bulunamadı; biçim değişmiş olabilir.")
    column = names.index("WTMP")
    buckets, valid, absent = {}, 0, 0
    for number, line in enumerate(lines[1:], 2):
        if line.startswith("#"):
            continue
        tokens = line.split()
        if len(tokens) != len(names):
            raise SourceError(f"{label} dosyasının {number}. satırı beklenen sütun sayısında değil.")
        try:
            year, month, day = int(tokens[0]), int(tokens[1]), int(tokens[2])
            value = float(tokens[column])
        except ValueError as exc:
            raise SourceError(f"{label} dosyasının {number}. satırı okunamadı.") from exc
        year += 1900 if year < 100 else 0
        if not 1 <= month <= 12 or not 1 <= day <= 31 or not math.isfinite(value):
            raise SourceError(f"{label} dosyasının {number}. satırında geçersiz tarih veya değer var.")
        if missing(value):
            absent += 1
            continue
        bucket = buckets.setdefault((year, month), [0.0, 0, set()])
        bucket[0] += value
        bucket[1] += 1
        bucket[2].add(day)
        valid += 1
    return buckets, valid, absent


def monthly_summary(rows, min_days=MIN_DAYS):
    """Multi-year monthly mean of year-month means that have at least min_days days with data (each year weighs equally)."""
    summary = []
    for month in range(1, 13):
        used = sorted((row for row in rows if row["month"] == month and row["day_count"] >= min_days), key=lambda row: row["year"])
        summary.append({"month": month, "mean_c": round(sum(row["mean_c"] for row in used) / len(used), 2) if used else None,
                        "years_used": len(used), "first_year": used[0]["year"] if used else None,
                        "last_year": used[-1]["year"] if used else None,
                        "excluded_year_months": sum(1 for row in rows if row["month"] == month and row["day_count"] < min_days)})
    return summary


def collect(raw_path, progress, canceled, *, stations, client=None, last_year=None):
    stations = [station for station in stations if station["kind"] == "water_temperature"]
    if not stations:
        raise SourceError("Bu destinasyon için deniz suyu sıcaklığı istasyonu yapılandırılmamış.")
    last_year = last_year or datetime.now(timezone.utc).year - 1
    owns = client is None
    client = client or make_client()
    reader = Reader(client, raw_path, canceled, connector=CONNECTOR_VERSION, hosts=HOSTS, max_bytes=MAX_BYTES, label="NDBC yıllık dosyası")
    try:
        records, station_rows, totals = [], [], {"valid": 0, "missing": 0}
        years_total = sum(max(0, last_year - (s.get("first_year") or last_year + 1) + 1) for s in stations)
        done = 0
        for station in stations:
            first_year = station.get("first_year")
            if not first_year or first_year > last_year:
                raise SourceError(f"{station['station_id']} için ilk yıl yapılandırılmamış.")
            buckets, found, absent_years = {}, [], []
            for year in range(first_year, last_year + 1):
                check(canceled)
                progress(5 + int(85 * done / max(1, years_total)), f"{station['station_id']} {year} yıllık dosyası okunuyor.")
                done += 1
                body, _ = reader.get(FILE_URL.format(station=station["station_id"].lower(), year=year), suffix=".txt.gz",
                                     note=f"{station['station_id']} {year}", content_types=GZIP_TYPES, allow_missing=True)
                if body is None:
                    absent_years.append(year)
                    continue
                parsed, valid, absent = parse_year(body, f"{station['station_id']} {year}")
                found.append(year)
                totals["valid"] += valid
                totals["missing"] += absent
                for key, (total, count, days) in parsed.items():
                    bucket = buckets.setdefault(key, [0.0, 0, set()])
                    bucket[0] += total
                    bucket[1] += count
                    bucket[2] |= days
            if not found:
                raise SourceError(f"{station['station_id']} için hiç yıllık dosya bulunamadı.")
            for (year, month), (total, count, days) in sorted(buckets.items()):
                records.append({"station_id": station["station_id"], "year": year, "month": month,
                                "mean_c": round(total / count, 3), "observation_count": count, "day_count": len(days)})
            station_rows.append({"station_id": station["station_id"], "station_key": station["station_key"], "role": station["role"],
                                 "label": station["label"], "latitude": station["latitude"], "longitude": station["longitude"],
                                 "distance_km": station["distance_km"], "first_year": first_year, "last_year": last_year,
                                 "years_found": found, "years_missing": absent_years})
        check(canceled)
        metadata = {"stations": [row["station_id"] for row in station_rows], "years_found": {r["station_id"]: r["years_found"] for r in station_rows},
                    "years_missing": {r["station_id"]: r["years_missing"] for r in station_rows}, "valid_observations": totals["valid"],
                    "missing_observations": totals["missing"], "min_days": MIN_DAYS,
                    "scope": "NOAA NDBC tarihî standart meteoroloji yıllık dosyalarından WTMP; yıl-ay ortalamaları bizim hesabımızdır."}
        progress(95, f"{len(records)} yıl-ay ortalaması hesaplandı ({totals['valid']} gözlem).")
        return CollectionResult(records, len(records), 0, None, metadata, {"stations": station_rows})
    finally:
        if owns:
            client.close()


class WaterTemperatureConnector:
    name = "ndbc-water-temperature"
    version = CONNECTOR_VERSION
    raw_filename = "manifest.json"
    method = "Dosya"
    diff_enabled = False
    diff_reason = "Deniz suyu sıcaklığı aylık ortalamaları geçmiş yıllık dosyalardan hesaplanır; sürümler arası kayıt farkı özeti gösterilmiyor."

    def supports(self, source):
        return https_source_identity(source["url"], host_aliases={"www.ndbc.noaa.gov": "www.ndbc.noaa.gov"}) == SOURCE_IDENTITY

    def collect(self, source, raw_path, progress, canceled, *, context):
        return collect(raw_path, progress, canceled, stations=context.climate_stations)

    def store_records(self, con, run_id, records, related=None):
        for station in (related or {}).get("stations", []):
            con.execute("""INSERT INTO water_temperature_stations (run_id,station_id,station_key,role,label,latitude,longitude,
                distance_km,first_year,last_year,years_found,years_missing) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, station["station_id"], station["station_key"], station["role"], station["label"], station["latitude"],
                 station["longitude"], station["distance_km"], station["first_year"], station["last_year"],
                 json.dumps(station["years_found"]), json.dumps(station["years_missing"])))
        for record in records:
            con.execute("""INSERT INTO water_temperature_months (run_id,station_id,year,month,mean_c,observation_count,day_count)
                VALUES (?,?,?,?,?,?,?)""", (run_id, record["station_id"], record["year"], record["month"], record["mean_c"],
                                           record["observation_count"], record["day_count"]))

    def read_records(self, con, run_id):
        return [dict(row) for row in con.execute(
            "SELECT * FROM water_temperature_months WHERE run_id=? ORDER BY station_id, year, month", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Water temperature diff is disabled.")

    def read_snapshot(self, con, run_id):
        stations = []
        for row in con.execute("SELECT * FROM water_temperature_stations WHERE run_id=? ORDER BY distance_km, station_id", (run_id,)):
            station = dict(row)
            station["years_found"], station["years_missing"] = json.loads(station["years_found"]), json.loads(station["years_missing"])
            stations.append(station)
        months = self.read_records(con, run_id)
        return {"stations": stations, "months": months, "min_days": MIN_DAYS,
                "summary": {station["station_id"]: monthly_summary([m for m in months if m["station_id"] == station["station_id"]])
                            for station in stations}}
