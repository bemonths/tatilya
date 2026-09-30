"""NWS official API: sequential point/grid forecasts and active alerts, no API key."""
import json
import math
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import httpx

from .base import CollectionResult, SourceError, CollectionCanceled
from .weather_anchors import ANCHORS, ANCHOR_PROVENANCE

SOURCE_URL = "https://www.weather.gov/"
API_ROOT = "https://api.weather.gov"
HEADERS = {"User-Agent": "30AStudio/0.4 (+https://github.com/bemonths/tatilya)", "Accept": "application/geo+json"}
MAX_BYTES = 5_000_000
RETRY_SECONDS = 0.5


def checked_url(value):
    try:
        if not isinstance(value, str) or any(ord(c) < 33 for c in value) or "\\" in value:
            raise ValueError()
        parts = urlsplit(value)
        if (parts.scheme != "https" or parts.hostname != "api.weather.gov" or
                parts.username is not None or parts.password is not None or
                parts.port not in (None, 443) or parts.fragment):
            raise ValueError()
    except ValueError as exc:
        raise SourceError("NWS geçersiz veya izin verilmeyen bir API adresi döndürdü. İstek yapılmadı.") from exc
    return value


def check_canceled(canceled):
    if canceled():
        raise CollectionCanceled()


def timestamp(value, nullable=False):
    if value is None and nullable:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise SourceError("NWS tarih/saat alanı geçersiz veya saat dilimi eksik.") from exc
    return value  # Preserve the exact source offset, not the computer's timezone.


def text(value, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise SourceError("NWS metin alanı beklenen biçimde değil.")
    return value


def number(value, percent=False):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise SourceError("NWS sayısal alanı beklenen biçimde değil.")
    if percent and not 0 <= value <= 100:
        raise SourceError("NWS yüzde alanı 0–100 aralığında değil.")
    return value


def quantity(value, percent=False):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SourceError("NWS ölçüm alanı beklenen biçimde değil.")
    return number(value.get("value"), percent)


def properties(body):
    if not isinstance(body, dict) or not isinstance(body.get("properties"), dict):
        raise SourceError("NWS yanıtında properties alanı eksik.")
    return body["properties"]


def parse_location(body, anchor):
    p = properties(body)
    if not isinstance(p.get("cwa"), str) or not re.fullmatch(r"[A-Z]{3}", p["cwa"]):
        raise SourceError("NWS ofis kodu eksik veya geçersiz.")
    if any(type(p.get(key)) is not int for key in ("gridX", "gridY")):
        raise SourceError("NWS grid koordinatları eksik veya geçersiz.")
    zone = text(p.get("timeZone"))
    if not re.fullmatch(r"[A-Za-z_+-]+(?:/[A-Za-z0-9_+-]+)+", zone):
        raise SourceError("NWS saat dilimi eksik veya geçersiz.")
    result = {**anchor, "cwa": p["cwa"], "grid_x": p["gridX"], "grid_y": p["gridY"], "time_zone": zone}
    for field, key in (("forecast_url", "forecast"), ("forecast_hourly_url", "forecastHourly"),
                       ("forecast_grid_data_url", "forecastGridData"), ("forecast_zone_url", "forecastZone"),
                       ("county_url", "county"), ("observation_stations_url", "observationStations")):
        value = p.get(key)
        result[field] = checked_url(value) if value is not None or key in ("forecast", "forecastHourly") else None
    return result


def parse_forecast(body, anchor_key, kind):
    p = properties(body)
    periods = p.get("periods")
    if not isinstance(periods, list) or not periods:
        raise SourceError("NWS gerekli tahmin dönemlerini döndürmedi; çekim yayımlanmadı.")
    records, seen = [], set()
    for entry in periods:
        if not isinstance(entry, dict):
            raise SourceError("NWS tahmin dönemi geçersiz.")
        start, end = timestamp(entry.get("startTime")), timestamp(entry.get("endTime"))
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        if datetime.fromisoformat(end.replace("Z", "+00:00")) <= start_dt or start_dt in seen:
            raise SourceError("NWS tahmin dönemleri tekrarlı veya zaman aralığı geçersiz.")
        seen.add(start_dt)
        daytime = entry.get("isDaytime")
        if daytime is not None and type(daytime) is not bool:
            raise SourceError("NWS gündüz/gece alanı geçersiz.")
        period_number = entry.get("number")
        if period_number is not None and type(period_number) is not int:
            raise SourceError("NWS dönem numarası geçersiz.")
        dewpoint = entry.get("dewpoint")
        record = {"anchor_key": anchor_key, "forecast_kind": kind, "external_id": f"{anchor_key}:{kind}:{start}",
                  "number": period_number, "name": text(entry.get("name"), True),
                  "start_time": start, "end_time": end, "is_daytime": daytime,
                  "temperature": number(entry.get("temperature")), "temperature_unit": text(entry.get("temperatureUnit"), True),
                  "temperature_trend": text(entry.get("temperatureTrend"), True),
                  "precipitation_probability": quantity(entry.get("probabilityOfPrecipitation"), True),
                  "relative_humidity": quantity(entry.get("relativeHumidity"), True), "dewpoint": quantity(dewpoint),
                  "dewpoint_unit": text(dewpoint.get("unitCode"), True) if isinstance(dewpoint, dict) else None,
                  "wind_speed": text(entry.get("windSpeed"), True), "wind_direction": text(entry.get("windDirection"), True),
                  "icon_url": text(entry.get("icon"), True), "short_forecast": text(entry.get("shortForecast")),
                  "detailed_forecast": text(entry.get("detailedForecast"), True)}
        records.append(record)
    stamps = {key: timestamp(p.get(key), True) for key in ("generatedAt", "updateTime")}
    return records, stamps


ALERT_FIELDS = {"event": "event", "headline": "headline", "area_desc": "areaDesc", "severity": "severity",
                "certainty": "certainty", "urgency": "urgency", "effective": "effective", "onset": "onset",
                "expires": "expires", "ends": "ends", "status": "status", "message_type": "messageType",
                "description": "description", "instruction": "instruction"}


def parse_alerts(body):
    if not isinstance(body, dict) or not isinstance(body.get("features"), list):
        raise SourceError("NWS uyarı listesi eksik veya geçersiz.")
    alerts = []
    for entry in body["features"]:
        p = properties(entry)
        identifier = text(p.get("id") or entry.get("id"))
        if not identifier:
            raise SourceError("NWS uyarı kimliği eksik.")
        alert = {"alert_id": identifier}
        for field, key in ALERT_FIELDS.items():
            alert[field] = (timestamp(p.get(key), True) if field in ("effective", "onset", "expires", "ends")
                            else text(p.get(key), field != "event"))
        alerts.append(alert)
    return alerts


class APIReader:
    def __init__(self, client, raw_path, canceled):
        self.client, self.raw_path, self.canceled = client, raw_path, canceled
        self.bundle = {"connector": "nws-weather/1", "provenance": ANCHOR_PROVENANCE, "responses": []}

    def save(self, anchor, kind, url, response, content):
        self.bundle["responses"].append({"sequence": len(self.bundle["responses"]) + 1,
            "anchor": anchor, "request_kind": kind, "url": url, "status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "fetched_at": datetime.now(timezone.utc).isoformat(), "body": content.decode("utf-8", errors="replace")})
        self.raw_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.raw_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.bundle, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.raw_path)

    def get(self, url, anchor, kind):
        original = checked_url(url)
        for attempt in range(2):
            check_canceled(self.canceled)
            current = original
            try:
                for redirect in range(4):
                    check_canceled(self.canceled)
                    with self.client.stream("GET", current, headers=HEADERS, follow_redirects=False) as response:
                        chunks, length = [], 0
                        for chunk in response.iter_bytes():
                            check_canceled(self.canceled)
                            length += len(chunk)
                            if length > MAX_BYTES:
                                raise SourceError("NWS yanıtı 5 MB boyut sınırını aştı.")
                            chunks.append(chunk)
                        content = b"".join(chunks)
                        self.save(anchor, kind, str(response.url), response, content)
                        if response.status_code in (301, 302, 303, 307, 308):
                            if redirect == 3 or not response.headers.get("location"):
                                raise SourceError("NWS yönlendirme sınırı aşıldı veya adres eksik.")
                            try:
                                current = checked_url(urljoin(current, response.headers["location"]))
                            except ValueError as exc:
                                raise SourceError("NWS yönlendirme adresi geçersiz.") from exc
                            continue
                        if response.status_code == 429:
                            raise SourceError("NWS istek sınırına ulaşıldı (429). Daha sonra yeniden deneyin.")
                        if response.status_code >= 500:
                            if attempt == 0:
                                break
                            raise SourceError("NWS sunucusu geçici hata döndürdü. Daha sonra yeniden deneyin.")
                        if response.status_code != 200:
                            raise SourceError(f"NWS isteği tamamlanamadı (HTTP {response.status_code}).")
                        mime = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                        if mime not in ("application/geo+json", "application/json", "application/ld+json"):
                            raise SourceError("NWS beklenen JSON içerik türünü döndürmedi.")
                        try:
                            body = json.loads(content)
                        except (ValueError, UnicodeError) as exc:
                            raise SourceError("NWS geçerli JSON döndürmedi.") from exc
                        if not isinstance(body, dict):
                            raise SourceError("NWS JSON yanıtı nesne olmalı.")
                        return body
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == 1:
                    raise SourceError("NWS bağlantısı kurulamadı veya zaman aşımına uğradı.") from exc
            except httpx.HTTPError as exc:
                raise SourceError("NWS HTTP yanıtı okunamadı.") from exc
            # Short interruptible bounded retry; no Retry-After or unbounded wait.
            deadline = time.monotonic() + RETRY_SECONDS
            while time.monotonic() < deadline:
                check_canceled(self.canceled)
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        raise SourceError("NWS isteği tamamlanamadı.")


def collect(raw_path, progress, canceled, *, client=None):
    owns_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(20, connect=10), verify=True)
    reader = APIReader(client, raw_path, canceled)
    locations, records, alerts, anchor_stamps = [], [], {}, {}
    try:
        for index, anchor in enumerate(ANCHORS):
            check_canceled(canceled)
            key = anchor["anchor_key"]
            point = f"{anchor['latitude']},{anchor['longitude']}"
            progress(5 + index * 28, f"{anchor['label']} · NWS grid bilgisi okunuyor.")
            location = parse_location(reader.get(f"{API_ROOT}/points/{point}", anchor, "points"), anchor)
            locations.append(location)
            stamps = {}
            for kind, url_key in (("period", "forecast_url"), ("hourly", "forecast_hourly_url")):
                rows, stamps[kind] = parse_forecast(reader.get(location[url_key], anchor, kind), key, kind)
                records.extend(rows)
            anchor_stamps[key] = stamps
            url = f"{API_ROOT}/alerts/active?point={point}"
            for page in range(5):
                body = reader.get(url, anchor, "alerts")
                for alert in parse_alerts(body):
                    # First occurrence retained; all raw responses remain auditable.
                    existing = alerts.setdefault(alert["alert_id"], {**alert, "anchor_keys": []})
                    if key not in existing["anchor_keys"]:
                        existing["anchor_keys"].append(key)
                pagination = body.get("pagination") or {}
                if not isinstance(pagination, dict):
                    raise SourceError("NWS uyarı sayfalama bilgisi geçersiz.")
                following = pagination.get("next")
                if not following:
                    break
                if page == 4:
                    raise SourceError("NWS uyarı sayfalama sınırı aşıldı; eksik veri yayımlanmadı.")
                url = checked_url(following)
        check_canceled(canceled)
        source_stamps = [entry["period"]["updateTime"] or entry["period"]["generatedAt"] for entry in anchor_stamps.values()]
        source_updated = max((s for s in source_stamps if s), key=lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")), default=None)
        metadata = {"anchors": len(locations), "forecast_period_count": sum(r["forecast_kind"] == "period" for r in records),
                    "hourly_period_count": sum(r["forecast_kind"] == "hourly" for r in records), "alert_count": len(alerts),
                    "source_timestamps": anchor_stamps, "anchor_provenance": ANCHOR_PROVENANCE}
        progress(90, f"{len(records)} tahmin dönemi ve {len(alerts)} uyarı doğrulandı.")
        return CollectionResult(records, len(records), 0, source_updated, metadata,
                                {"locations": locations, "alerts": list(alerts.values())})
    finally:
        if owns_client:
            client.close()


def insert_row(con, table, run_id, row):
    # Table and field names are internal constants/normalized keys, never API text.
    fields = ["run_id", *row.keys()]
    con.execute(f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", [run_id, *row.values()])


class WeatherConnector:
    name, version, method = "nws-weather", "nws-weather/1", "API"
    raw_filename, diff_enabled = "source.json", False

    def supports(self, source):
        return source["url"] == SOURCE_URL

    def collect(self, source, raw_path, progress, canceled):
        return collect(raw_path, progress, canceled)

    def store_records(self, con, run_id, records, related=None):
        for location in related["locations"]:
            insert_row(con, "weather_locations", run_id, location)
        for record in records:
            insert_row(con, "weather_forecast_periods", run_id, record)
        for alert in related["alerts"]:
            insert_row(con, "weather_alerts", run_id, {k: v for k, v in alert.items() if k != "anchor_keys"})
            for key in alert["anchor_keys"]:
                insert_row(con, "weather_alert_anchors", run_id, {"alert_id": alert["alert_id"], "anchor_key": key})

    def read_records(self, con, run_id):
        return [dict(row) for row in con.execute("SELECT * FROM weather_forecast_periods WHERE run_id=? ORDER BY anchor_key,forecast_kind,start_time", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Rolling forecast diff is disabled.")

    def read_snapshot(self, con, run_id):
        records = self.read_records(con, run_id)
        alerts = [dict(row) for row in con.execute("SELECT * FROM weather_alerts WHERE run_id=? ORDER BY alert_id", (run_id,))]
        for alert in alerts:
            alert["anchor_keys"] = [row[0] for row in con.execute("SELECT anchor_key FROM weather_alert_anchors WHERE run_id=? AND alert_id=? ORDER BY anchor_key", (run_id, alert["alert_id"]))]
        return {"locations": [dict(row) for row in con.execute("SELECT * FROM weather_locations WHERE run_id=? ORDER BY longitude", (run_id,))],
                "forecast_periods": [r for r in records if r["forecast_kind"] == "period"],
                "hourly_periods": [r for r in records if r["forecast_kind"] == "hourly"], "alerts": alerts}
