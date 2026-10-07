"""NOAA NCEI U.S. Climate Normals 1991–2020 (monthly) through NCEI's keyless data access API.

Destination-independent: the stations come from the destination's climate configuration in SQLite.
NCEI's robots.txt disallows /data*; this connector only uses /access/services/data/v1.
"""
import json
import math

from .base import CollectionResult, SourceError
from .climate_http import Reader, check, make_client
from .url_identity import https_source_identity

SOURCE_URL = "https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals"
API_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
DATASET = "normals-monthly-1991-2020"
HOSTS = frozenset({"www.ncei.noaa.gov"})
SOURCE_IDENTITY = https_source_identity(SOURCE_URL, host_aliases={"www.ncei.noaa.gov": "www.ncei.noaa.gov"})
CONNECTOR_VERSION = "ncei-climate-normals/1"
MAX_BYTES = 5_000_000
# Exact NCEI element codes (verified against the API on 7 Oct 2026) with the unit the source uses.
ELEMENTS = {
    "MLY-TAVG-NORMAL": ("Aylık ortalama sıcaklık", "°F"),
    "MLY-TMAX-NORMAL": ("Aylık ortalama en yüksek sıcaklık", "°F"),
    "MLY-TMIN-NORMAL": ("Aylık ortalama en düşük sıcaklık", "°F"),
    "MLY-PRCP-NORMAL": ("Aylık toplam yağış", "inç"),
    "MLY-PRCP-AVGNDS-GE010HI": ("Yağışı en az 0,10 inç olan gün sayısı", "gün"),
    "MLY-TMAX-AVGNDS-GRTH090": ("En yüksek sıcaklığı en az 90°F olan gün sayısı", "gün"),
    "MLY-TMIN-AVGNDS-LSTH032": ("En düşük sıcaklığı en çok 32°F olan gün sayısı", "gün"),
}
# NCEI uses large negative sentinels for special values; they are kept as NULL, never as numbers.
SENTINEL_LIMIT = -5555


def text(value):
    return " ".join(value.split()) if isinstance(value, str) else None


def number(value, label):
    cleaned = text(value)
    if not cleaned:
        return None
    try:
        parsed = float(cleaned)
    except ValueError as exc:
        raise SourceError(f"İklim normali değeri okunamadı: {label}.") from exc
    if not math.isfinite(parsed):
        raise SourceError(f"İklim normali değeri geçersiz: {label}.")
    return None if parsed <= SENTINEL_LIMIT else parsed


def parse(content, stations):
    """Return (records, station rows, sentinel count) for the configured normals stations."""
    try:
        data = json.loads(content)
    except ValueError as exc:
        raise SourceError("NCEI yanıtı JSON olarak okunamadı.") from exc
    if not isinstance(data, list):
        raise SourceError("NCEI yanıtı beklenen liste biçiminde değil.")
    grouped = {}
    for row in data:
        if not isinstance(row, dict) or not isinstance(row.get("STATION"), str):
            raise SourceError("NCEI yanıtında istasyon kimliği olmayan satır var.")
        grouped.setdefault(row["STATION"].strip(), []).append(row)
    records, station_rows, sentinels = [], [], 0
    for station in stations:
        rows = grouped.get(station["station_id"])
        if not rows:
            raise SourceError(f"{station['station_id']} için normal verisi dönmedi; istasyon kimliği kontrol edilmeli.")
        months = {}
        for row in rows:
            try:
                month = int(str(row.get("DATE", "")).strip())
            except ValueError as exc:
                raise SourceError("NCEI yanıtında ay alanı okunamadı.") from exc
            if not 1 <= month <= 12 or month in months:
                raise SourceError("NCEI yanıtında ay alanı geçersiz veya yinelenmiş.")
            months[month] = row
        if sorted(months) != list(range(1, 13)):
            raise SourceError(f"{station['station_id']} için 12 ayın normali dönmedi.")
        first = months[1]
        station_rows.append({
            "station_id": station["station_id"], "station_key": station["station_key"], "role": station["role"],
            "label": station["label"], "source_name": text(first.get("NAME")), "latitude": number(first.get("LATITUDE"), "enlem"),
            "longitude": number(first.get("LONGITUDE"), "boylam"), "elevation_m": number(first.get("ELEVATION"), "yükseklik"),
            "distance_km": station["distance_km"]})
        for month, row in sorted(months.items()):
            for element, (_, unit) in ELEMENTS.items():
                raw = row.get(element)
                value = number(raw, element)
                if value is None and text(raw) and float(text(raw)) <= SENTINEL_LIMIT:
                    sentinels += 1
                years = text(row.get(f"years_{element}"))
                records.append({
                    "station_id": station["station_id"], "month": month, "element": element, "value": value, "unit": unit,
                    "completeness_flag": text(row.get(f"comp_flag_{element}")) or None,
                    "measurement_flag": text(row.get(f"meas_flag_{element}")) or None,
                    "years": int(years) if years and years.isdigit() else None})
    return records, station_rows, sentinels


def collect(raw_path, progress, canceled, *, stations, client=None):
    stations = [station for station in stations if station["kind"] == "normals"]
    if not stations:
        raise SourceError("Bu destinasyon için iklim normali istasyonu yapılandırılmamış.")
    owns = client is None
    client = client or make_client()
    reader = Reader(client, raw_path, canceled, connector=CONNECTOR_VERSION, hosts=HOSTS, max_bytes=MAX_BYTES, label="NCEI iklim normalleri")
    try:
        progress(10, f"NCEI 1991–2020 aylık normalleri isteniyor ({len(stations)} istasyon).")
        params = {"dataset": DATASET, "stations": ",".join(s["station_id"] for s in stations), "startDate": "0001-01-01",
                  "endDate": "9996-12-31", "dataTypes": ",".join(ELEMENTS), "includeAttributes": "true",
                  "includeStationName": "true", "includeStationLocation": "1", "format": "json"}
        body, _ = reader.get(API_URL, suffix=".json", note="normals-monthly-1991-2020", content_types={"application/json"}, params=params)
        check(canceled)
        try:
            content = body.decode("utf-8-sig")
        except UnicodeError as exc:
            raise SourceError("NCEI yanıtının karakter kodlaması geçersiz.") from exc
        records, station_rows, sentinels = parse(content, stations)
        missing = sum(record["value"] is None for record in records)
        metadata = {"dataset": DATASET, "elements": list(ELEMENTS), "stations": [s["station_id"] for s in stations],
                    "missing_values": missing, "sentinel_values": sentinels,
                    "scope": "NOAA NCEI 1991–2020 aylık iklim normalleri; destinasyonun yapılandırılmış istasyonları."}
        progress(95, f"{len(station_rows)} istasyon için {len(records)} normal değeri okundu ({missing} değer kaynakta yok).")
        return CollectionResult(records, len(records), 0, None, metadata, {"stations": station_rows})
    finally:
        if owns:
            client.close()


class ClimateNormalsConnector:
    name = "ncei-climate-normals"
    version = CONNECTOR_VERSION
    raw_filename = "manifest.json"
    method = "API"
    diff_enabled = False
    diff_reason = "İklim normalleri on yılda bir üretilen durağan bir üründür; sürümler arası kayıt farkı özeti gösterilmiyor."

    def supports(self, source):
        return https_source_identity(source["url"], host_aliases={"www.ncei.noaa.gov": "www.ncei.noaa.gov"}) == SOURCE_IDENTITY

    def collect(self, source, raw_path, progress, canceled, *, context):
        return collect(raw_path, progress, canceled, stations=context.climate_stations)

    def store_records(self, con, run_id, records, related=None):
        for station in (related or {}).get("stations", []):
            con.execute("""INSERT INTO climate_normal_stations (run_id,station_id,station_key,role,label,source_name,latitude,
                longitude,elevation_m,distance_km) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (run_id, station["station_id"], station["station_key"], station["role"], station["label"], station["source_name"],
                 station["latitude"], station["longitude"], station["elevation_m"], station["distance_km"]))
        for record in records:
            con.execute("""INSERT INTO climate_normal_values (run_id,station_id,month,element,value,unit,completeness_flag,
                measurement_flag,years) VALUES (?,?,?,?,?,?,?,?,?)""",
                (run_id, record["station_id"], record["month"], record["element"], record["value"], record["unit"],
                 record["completeness_flag"], record["measurement_flag"], record["years"]))

    def read_records(self, con, run_id):
        return [dict(row) for row in con.execute(
            "SELECT * FROM climate_normal_values WHERE run_id=? ORDER BY station_id, month, element", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Climate normals diff is disabled.")

    def read_snapshot(self, con, run_id):
        stations = [dict(row) for row in con.execute(
            "SELECT * FROM climate_normal_stations WHERE run_id=? ORDER BY distance_km, station_id", (run_id,))]
        return {"stations": stations, "values": self.read_records(con, run_id),
                "elements": [{"code": code, "label": label, "unit": unit} for code, (label, unit) in ELEMENTS.items()]}
