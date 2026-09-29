"""Visit South Walton harita noktaları. Sayfanın JavaScript'i çalıştırılmaz."""
import json
import math
import re
import time
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from .base import CollectionResult, SourceError, CollectionCanceled

SOURCE_URL = "https://www.visitsouthwalton.com/beach-bay-access-locations/"
ALLOWED_HOSTS = frozenset({"visitsouthwalton.com", "www.visitsouthwalton.com"})
PARSER_VERSION = "south-walton-beaches/2"
MAX_BYTES = 5_000_000
COASTAL_CITIES = frozenset({"Santa Rosa Beach", "Grayton Beach", "Seacrest", "Inlet Beach"})
COASTAL_TYPES = frozenset({"regional", "neighborhood"})
SCOPE = "Kaynakta Santa Rosa Beach, Grayton Beach, Seacrest veya Inlet Beach olarak listelenen bölgesel ve mahalle plaj erişimleri. Miramar ve koy/göl noktaları kapsam dışında."
FEATURE_LABELS = {
    "Parking": "Otopark", "Restrooms": "Tuvalet", "Water Fountain": "İçme suyu çeşmesi",
    "Seasonal Lifeguards": "Sezonluk cankurtaran", "Beach Conditions Flag": "Deniz durumu bayrağı",
    "ADA Accessible Boardwalk": "Erişilebilir yürüyüş yolu", "ADA Accessible Parking": "Erişilebilir otopark",
    "ADA Accessible Restrooms": "Erişilebilir tuvalet", "Beach Wheelchairs Available": "Plaj tekerlekli sandalyesi",
    "Vendor Managed": "İşletmeci yönetimi", "Picnic Pavilion": "Piknik çardağı", "Picnic Area": "Piknik alanı",
    "Boat Launch": "Tekne indirme", "Kayak Launch": "Kano indirme", "Dock": "İskele", "Pier": "İskele",
    "Fishing Pier": "Balıkçılık iskelesi", "Playground": "Oyun alanı", "Basketball": "Basketbol",
    "Hiking Trails": "Yürüyüş parkurları",
}


BeachBatch = CollectionResult


def parse_page(content: bytes) -> BeachBatch:
    if len(content) > MAX_BYTES:
        raise SourceError("Kaynak sayfası beklenen boyutu aşıyor.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceError("Kaynak metninin kodlaması okunamadı.") from exc
    match = re.search(r"function\s+initMarkers\s*\(\s*\)\s*\{\s*(?:var|let|const)\s+data\s*=\s*\[", text)
    if not match:
        raise SourceError("Kaynak sayfasında beklenen harita verisi bulunamadı. Önceki başarılı kayıtlar korundu.")
    position = match.end()
    decoder = json.JSONDecoder()
    raw_records = []
    try:
        while True:
            while text[position].isspace():
                position += 1
            if text[position] == "]":
                break
            item, position = decoder.raw_decode(text, position)
            raw_records.append(item)
            if len(raw_records) > 2000:
                raise SourceError("Kaynakta beklenenden fazla kayıt var; bağlayıcı kontrol edilmeli.")
            while text[position].isspace():
                position += 1
            if text[position] == ",":
                position += 1
            elif text[position] != "]":
                raise ValueError("Beklenmeyen ayırıcı")
    except (IndexError, ValueError) as exc:
        raise SourceError("Harita verisinin biçimi değişmiş veya sayfa eksik. Önceki kayıtlar korundu.") from exc
    if not raw_records:
        raise SourceError("Kaynak boş bir kayıt listesi döndürdü. Önceki kayıtlar korundu.")
    records, seen = [], set()
    for item in raw_records:
        if not isinstance(item, dict):
            raise SourceError("Kaynakta beklenmeyen bir kayıt biçimi var.")
        for field in ("id", "name", "city", "type", "address"):
            if not isinstance(item.get(field), str) or not item[field].strip() or len(item[field]) > 1000:
                raise SourceError(f"Kaynak kaydında zorunlu alan eksik veya geçersiz: {field}.")
        if item["id"] in seen:
            raise SourceError("Kaynakta yinelenen kayıt kimliği var. Önceki kayıtlar korundu.")
        seen.add(item["id"])
        if item["type"] not in ("regional", "neighborhood", "bays-lakes"):
            raise SourceError("Kaynak yeni bir erişim türü içeriyor; bağlayıcı güncellenmeli.")
        latitude, longitude = item.get("lat"), item.get("lng")
        if (type(latitude) not in (int, float) or type(longitude) not in (int, float)
                or not math.isfinite(latitude) or not math.isfinite(longitude)
                or not 30 <= latitude <= 31 or not -87 <= longitude <= -85):
            raise SourceError("Kaynak kaydında geçersiz veya bölge dışında koordinat var.")
        features = item.get("features")
        if not isinstance(features, list) or any(not isinstance(feature, str) or len(feature) > 160 for feature in features):
            raise SourceError("Kaynak kaydının olanak listesi okunamadı.")
        if item["city"].strip() not in COASTAL_CITIES or item["type"] not in COASTAL_TYPES:
            continue
        records.append({"external_id": item["id"], "name": item["name"].strip(), "city": item["city"].strip(),
                        "address": item["address"].strip(), "latitude": latitude, "longitude": longitude,
                        "access_type": item["type"], "features": list(dict.fromkeys(feature.strip() for feature in features))})
    if not records:
        raise SourceError("Seçilen 30A kıyı kapsamına uyan kayıt bulunamadı. Önceki kayıtlar korundu.")
    updated_match = re.search(r"Latest map update:\s*(?:<[^>]+>\s*)*([^<\r\n]+)", text)
    source_updated = unescape(updated_match.group(1)).strip() if updated_match else None
    return BeachBatch(records, len(raw_records), len(raw_records)-len(records), source_updated)


def collect(raw_path: Path, progress, canceled, *, client=None) -> BeachBatch:
    """Tek sayfa, en fazla iki deneme. Testlerde HTTP istemcisi enjekte edilebilir."""
    owns_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(20, connect=10), follow_redirects=False,
                                    headers={"User-Agent": "30AStudio/0.3 (local source collection)", "Accept": "text/html"})
    try:
        content = None
        for attempt in range(2):
            if canceled():
                raise CollectionCanceled()
            progress(10, "South Walton plaj erişim sayfası okunuyor.")
            try:
                url = SOURCE_URL
                for redirect_count in range(4):
                    if canceled():
                        raise CollectionCanceled()
                    with client.stream("GET", url, follow_redirects=False) as response:
                        if response.status_code in (301, 302, 303, 307, 308):
                            try:
                                target = urljoin(url, response.headers.get("location", ""))
                                parts = urlsplit(target)
                                target_port = parts.port
                            except ValueError as exc:
                                raise SourceError("Kaynak geçersiz bir yönlendirme adresi döndürdü.") from exc
                            if (parts.hostname not in ALLOWED_HOSTS or parts.scheme != "https"
                                    or parts.username is not None or parts.password is not None or target_port not in (None, 443)):
                                raise SourceError("Kaynak başka bir alan adına veya güvenli olmayan adrese yönlendirdi. Yönlendirme izlenmedi.")
                            if not response.headers.get("location") or redirect_count == 3:
                                raise SourceError("Kaynağın yönlendirmesi eksik veya yönlendirme sınırı aşıldı.")
                            url = target
                            continue
                        if response.status_code == 429:
                            raise SourceError("Kaynak istekleri sınırlandırdı. Daha sonra yeniden deneyin.")
                        response.raise_for_status()
                        if "html" not in response.headers.get("content-type", "").lower():
                            raise SourceError("Kaynak beklenen HTML sayfasını döndürmedi.")
                        chunks, size = [], 0
                        for chunk in response.iter_bytes():
                            if canceled():
                                raise CollectionCanceled()
                            size += len(chunk)
                            if size > MAX_BYTES:
                                raise SourceError("Kaynak sayfası boyut sınırını aştı.")
                            chunks.append(chunk)
                        content = b"".join(chunks)
                        break
                break
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt == 0:
                    progress(12, "Kaynak geçici hata verdi. Bir kez yeniden deneniyor.")
                else:
                    raise SourceError(f"Kaynak HTTP {exc.response.status_code} döndürdü. Önceki kayıtlar korundu.") from exc
            except httpx.RemoteProtocolError as exc:
                raise SourceError("Kaynak geçersiz bir HTTP veya yönlendirme yanıtı döndürdü.") from exc
            except httpx.RequestError as exc:
                if attempt == 1:
                    raise SourceError("Kaynağa bağlanılamadı. İnternet bağlantısını kontrol edip yeniden deneyin.") from exc
                progress(12, "Bağlantı kurulamadı. Bir kez yeniden deneniyor.")
            for _ in range(10):
                if canceled():
                    raise CollectionCanceled()
                time.sleep(0.1)
        if canceled():
            raise CollectionCanceled()
        if content is None:
            raise SourceError("Kaynak okunamadı.")
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(content)
        progress(50, "Ham sayfa kaydedildi. Harita noktaları ayrıştırılıyor.")
        batch = parse_page(content)
        if canceled():
            raise CollectionCanceled()
        progress(85, f"{batch.total_count} harita noktası okundu; {len(batch.records)} kıyı kaydı seçildi.")
        return batch
    finally:
        if owns_client:
            client.close()


class BeachesConnector:
    name = "south-walton-beaches"
    version = PARSER_VERSION
    raw_filename = "source.html"

    def supports(self, source):
        return source["url"] == SOURCE_URL

    def collect(self, source, raw_path, progress, canceled):
        result = collect(raw_path, progress, canceled)
        result.metadata.update(scope=SCOPE)
        return result

    def store_records(self, con, run_id, records):
        for record in records:
            con.execute("""INSERT INTO beach_records
                (run_id,external_id,name,city,address,latitude,longitude,access_type,features,source_region_text,canonical_region_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,NULL)""", (
                    run_id, record["external_id"], record["name"], record["city"], record["address"],
                    record["latitude"], record["longitude"], record["access_type"],
                    json.dumps(record["features"], ensure_ascii=False), record["city"]))

    def read_records(self, con, run_id):
        records = []
        for row in con.execute("SELECT * FROM beach_records WHERE run_id=? ORDER BY longitude,name", (run_id,)):
            record = dict(row)
            record["features"] = json.loads(record["features"])
            records.append(record)
        return records

    def comparison_value(self, record):
        return {**{key: record[key] for key in ("name", "address", "city", "source_region_text", "latitude", "longitude", "access_type")},
                "features": sorted(set(record["features"]))}
