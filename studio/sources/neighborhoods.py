"""Visit South Walton neighborhood directory: embedded JSON index plus one page per neighborhood.

Only the 13 canonical 30A neighborhoods are stored. A source name is linked to a canonical region by
exact name or by the explicit alias table in the 30A profile; addresses and coordinates are never used
to infer a neighborhood. The coordinates are the source's representative point, not a neighborhood center.
"""
import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from .base import CollectionCanceled, CollectionResult, SourceError
from .html_tree import Node, Tree
from .url_identity import https_source_identity
from ..destinations.thirty_a import NEIGHBORHOOD_ALIASES, NEIGHBORHOOD_EXCLUDED, REGIONS

SOURCE_URL = "https://www.visitsouthwalton.com/neighborhoods/"
HOSTS = frozenset({"www.visitsouthwalton.com", "visitsouthwalton.com"})
SOURCE_HOST_ALIASES = {host: "visitsouthwalton.com" for host in HOSTS}
SOURCE_IDENTITY = https_source_identity(SOURCE_URL, host_aliases=SOURCE_HOST_ALIASES)
CONNECTOR_VERSION = "south-walton-neighborhoods/1"
MAX_BYTES, MAX_RECORDS = 5_000_000, 100
RETRY_SECONDS, REQUEST_GAP = 0.5, 0.1
USER_AGENT = "30AStudio/0.7 (+https://github.com/bemonths/tatilya)"
ID_PATTERN = re.compile(r"[0-9a-f]{24}")
SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# Plausibility bounds for South Walton; a point outside them means the source data changed.
LATITUDE_RANGE, LONGITUDE_RANGE = (29.5, 31.5), (-87.5, -85.0)
SCOPE = ("Visit South Walton mahalle dizinindeki 13 kanonik 30A mahallesi. Miramar Beach, Seascape ve Sandestin kapsam dışı. "
         "Koordinatlar kaynağın temsilî noktasıdır, mahalle merkezi değildir.")


def clean(value):
    return " ".join(value.split())


def check(canceled):
    if canceled():
        raise CollectionCanceled()


def pause(seconds, canceled):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        check(canceled)
        time.sleep(min(0.05, max(0, end - time.monotonic())))


def checked_url(value, base=SOURCE_URL):
    try:
        if not isinstance(value, str) or any(ord(c) < 32 for c in value) or "\\" in value:
            raise ValueError()
        parts = urlsplit(urljoin(base, value))
        if (parts.scheme != "https" or parts.hostname not in HOSTS or parts.username is not None
                or parts.password is not None or parts.port not in (None, 443)):
            raise ValueError()
        return urlunsplit(("https", parts.hostname, parts.path or "/", parts.query, ""))
    except ValueError as exc:
        raise SourceError("Mahalle kaynağı geçersiz veya izin verilmeyen bir adres döndürdü. İstek yapılmadı.") from exc


def page_url(permalink):
    return f"https://www.visitsouthwalton.com/neighborhoods/{permalink}/"


def same_path(url, expected):
    return urlsplit(url).path.rstrip("/") == urlsplit(expected).path.rstrip("/")


def coordinate(value, bounds, label):
    try:
        number = float(value) if isinstance(value, str) else value
    except ValueError:
        number = None
    if type(number) not in (int, float) or not math.isfinite(number) or not bounds[0] <= number <= bounds[1]:
        raise SourceError(f"Mahalle kaydında geçersiz veya bölge dışında {label} var.")
    return float(number)


def parse_index(content):
    """Return validated directory entries in source order; any structural doubt fails the run."""
    found = list(re.finditer(r"\bvar\s+locations\s*=\s*", content))
    if len(found) != 1:
        raise SourceError("Mahalle dizininde beklenen gömülü veri bulunamadı. Önceki kayıtlar korundu.")
    try:
        data, _ = json.JSONDecoder().raw_decode(content, found[0].end())
    except ValueError as exc:
        raise SourceError("Mahalle dizinindeki gömülü veri okunamadı; biçim değişmiş olabilir.") from exc
    if not isinstance(data, list) or not data:
        raise SourceError("Mahalle dizini boş veya beklenmeyen biçimde.")
    if len(data) > MAX_RECORDS:
        raise SourceError("Mahalle dizininde beklenenden fazla kayıt var; toplayıcı kontrol edilmeli.")
    entries, ids, names = [], set(), set()
    for item in data:
        if not isinstance(item, dict):
            raise SourceError("Mahalle dizininde beklenmeyen bir kayıt biçimi var.")
        identifier, name, permalink = item.get("id"), item.get("name"), item.get("permalink")
        if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier):
            raise SourceError("Mahalle kaydında kaynak kimliği eksik veya geçersiz.")
        if not isinstance(name, str) or not clean(name) or len(name) > 200:
            raise SourceError("Mahalle kaydında ad eksik veya geçersiz.")
        if not isinstance(permalink, str) or not SLUG_PATTERN.fullmatch(permalink):
            raise SourceError("Mahalle kaydında sayfa bağlantısı (permalink) geçersiz.")
        if identifier in ids:
            raise SourceError("Mahalle dizininde yinelenen kaynak kimliği var. Önceki kayıtlar korundu.")
        name = clean(name)
        if name in names:
            raise SourceError("Mahalle dizininde aynı ad birden fazla kayıtta geçiyor.")
        ids.add(identifier)
        names.add(name)
        summary = item.get("description")
        if summary is not None and not isinstance(summary, str):
            raise SourceError("Mahalle kaydının kısa tanıtımı okunamadı.")
        modified = item.get("modified")
        if modified is not None and not isinstance(modified, str):
            raise SourceError("Mahalle kaydının değişiklik zamanı okunamadı.")
        activities = item.get("Activity") or []
        if not isinstance(activities, list):
            raise SourceError("Mahalle kaydının etiket listesi okunamadı.")
        tags = []
        for activity in activities:
            source_tag = activity.get("object") if isinstance(activity, dict) else None
            label = source_tag.get("name") if isinstance(source_tag, dict) else None
            if not isinstance(label, str) or not clean(label) or len(label) > 100:
                raise SourceError("Mahalle kaydında geçersiz bir etiket var.")
            tags.append(clean(label))
        entries.append({
            "external_id": identifier, "name": name, "permalink": permalink, "page_url": page_url(permalink),
            "summary": clean(summary) or None if summary else None,
            "latitude": coordinate(item.get("lat"), LATITUDE_RANGE, "enlem"),
            "longitude": coordinate(item.get("lng"), LONGITUDE_RANGE, "boylam"),
            "tags": sorted(set(tags)), "source_modified": clean(modified) or None if modified else None,
        })
    return entries


def select_targets(entries, regions):
    """Link entries to canonical regions by exact name or explicit alias; everything else is out of scope."""
    canonical = {region["name"]: region for region in regions}
    selected, excluded, unknown, aliases = {}, [], [], {}
    for entry in entries:
        name = entry["name"]
        region_name = name if name in canonical else NEIGHBORHOOD_ALIASES.get(name)
        if region_name in canonical:
            if region_name in selected:
                raise SourceError(f"Birden fazla kaynak kaydı aynı kanonik mahalleye bağlanıyor: {region_name}.")
            if region_name != name:
                aliases[name] = region_name
            selected[region_name] = (entry, canonical[region_name])
        else:
            excluded.append(name)
            if name not in NEIGHBORHOOD_EXCLUDED:
                unknown.append(name)
    missing = [region["name"] for region in regions if region["name"] not in selected]
    if missing:
        raise SourceError(f"Hedef mahalle kaynak dizininde bulunamadı: {', '.join(missing)}. Önceki kayıtlar korundu.")
    targets = [selected[region["name"]] for region in regions]
    return targets, sorted(excluded), sorted(unknown), aliases


def parse_page(content, expected_name):
    """Return the neighborhood page's intro text, or None when the page has no intro block."""
    root = Tree(content).root
    heroes = root.find(id="neighborhood-hero")
    if len(heroes) != 1:
        raise SourceError("Mahalle sayfasının yapısı değişti.")
    titles = heroes[0].find(cls="hero-title")
    headings = titles[0].find("h1") if len(titles) == 1 else []
    spans = headings[0].find("span") if len(headings) == 1 else []
    if len(spans) != 1 or not clean(spans[0].text()):
        raise SourceError("Mahalle sayfasında ad bulunamadı; sayfa yapısı değişti.")
    if clean(spans[0].text()) != expected_name:
        raise SourceError("Mahalle sayfasındaki ad dizindeki adla uyuşmuyor; kimlik doğrulanamadı.")
    blocks = heroes[0].find(cls="copious")
    if len(blocks) > 1:
        raise SourceError("Mahalle tanıtım alanının yapısı belirsiz; birden fazla blok bulundu.")
    if not blocks:
        return None
    paragraphs = [clean(p.text()) for p in blocks[0].find("p")]
    paragraphs = [p for p in paragraphs if p]
    if not paragraphs:
        loose = clean(" ".join(c.text() if isinstance(c, Node) else c for c in blocks[0].children
                               if not isinstance(c, Node) or c.tag not in ("h1", "h2", "h3", "h4", "h5", "h6", "script", "style")))
        paragraphs = [loose] if loose else []
    return "\n\n".join(paragraphs) or None


class Reader:
    """Sequential HTTPS reads with one retry; every completed response is kept with a manifest."""

    def __init__(self, client, path, canceled):
        self.client, self.path, self.canceled = client, path, canceled
        self.manifest = {"connector": CONNECTOR_VERSION, "source_url": SOURCE_URL, "responses": []}

    def save(self, requested, response, body, kind, neighborhood):
        sequence = len(self.manifest["responses"]) + 1
        relative = f"{'pages' if kind == 'page' else 'index'}/{sequence:04d}.html"
        target = self.path.parent / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        stamp = datetime.now(timezone.utc).isoformat()
        self.manifest["fetched_at"] = stamp
        self.manifest["responses"].append({
            "sequence": sequence, "request_kind": kind, "neighborhood": neighborhood, "requested_url": requested,
            "final_url": str(response.url), "status": response.status_code,
            "content_type": response.headers.get("content-type"), "fetched_at": stamp, "raw_file": relative,
            "raw_sha256": hashlib.sha256(body).hexdigest()})
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def get(self, url, kind, neighborhood=None):
        original = checked_url(url)
        for attempt in range(2):
            current = original
            try:
                for hop in range(4):
                    check(self.canceled)
                    pause(REQUEST_GAP, self.canceled)
                    with self.client.stream("GET", current, follow_redirects=False,
                                            headers={"User-Agent": USER_AGENT, "Accept": "text/html"}) as response:
                        chunks, size = [], 0
                        for part in response.iter_bytes():
                            check(self.canceled)
                            size += len(part)
                            if size > MAX_BYTES:
                                raise SourceError("Mahalle yanıtı boyut sınırını aştı.")
                            chunks.append(part)
                        body = b"".join(chunks)
                        self.save(current, response, body, kind, neighborhood)
                        if response.status_code in (301, 302, 303, 307, 308):
                            if hop == 3 or not response.headers.get("location"):
                                raise SourceError("Mahalle yönlendirme sınırı aşıldı veya hedef eksik.")
                            current = checked_url(response.headers["location"], current)
                            continue
                        if response.status_code == 429:
                            raise SourceError("Mahalle kaynağı istek sınırına ulaştı (429). Daha sonra deneyin.")
                        if response.status_code >= 500:
                            if attempt == 0:
                                break
                            raise SourceError("Mahalle kaynağı sunucu hatası döndürdü; daha sonra deneyin.")
                        if response.status_code != 200:
                            raise SourceError(f"Mahalle kaynağı okunamadı (HTTP {response.status_code}).")
                        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                        if content_type not in ("text/html", "application/xhtml+xml"):
                            raise SourceError("Mahalle kaynağı beklenen HTML içerik türünü döndürmedi.")
                        try:
                            return body.decode("utf-8-sig"), str(response.url)
                        except UnicodeError as exc:
                            raise SourceError("Mahalle sayfasının karakter kodlaması geçersiz.") from exc
            except (httpx.NetworkError, httpx.TimeoutException) as exc:
                if attempt == 1:
                    raise SourceError("Mahalle kaynağına bağlanılamadı veya zaman aşımı oluştu.") from exc
            except httpx.HTTPError as exc:
                raise SourceError("Mahalle kaynağının HTTP yanıtı geçersiz.") from exc
            pause(RETRY_SECONDS, self.canceled)
        raise SourceError("Mahalle isteği tamamlanamadı.")


def collect(raw_path, progress, canceled, *, client=None, regions=None):
    regions = list(regions) if regions is not None else [{"id": identifier, "name": name} for identifier, name in REGIONS]
    if not regions:
        raise SourceError("Mahalle bölge yapılandırması boş.")
    owns_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(20, connect=10), verify=True)
    reader = Reader(client, raw_path, canceled)
    try:
        progress(5, "Visit South Walton mahalle dizini okunuyor.")
        content, final = reader.get(SOURCE_URL, "index")
        if not same_path(final, SOURCE_URL):
            raise SourceError("Mahalle dizini başka bir sayfaya yönlendirildi.")
        entries = parse_index(content)
        targets, excluded, unknown, aliases = select_targets(entries, regions)
        records = []
        for index, (entry, region) in enumerate(targets):
            check(canceled)
            progress(15 + int(75 * index / len(targets)), f"{entry['name']} sayfası okunuyor ({index + 1}/{len(targets)}).")
            html, final = reader.get(entry["page_url"], "page", entry["name"])
            if not same_path(final, entry["page_url"]):
                raise SourceError("Mahalle sayfası yönlendirmesi kaynak kimliğini değiştirdi.")
            records.append({**entry, "canonical_region_id": region["id"], "page_intro": parse_page(html, entry["name"])})
        check(canceled)
        modified = [record["source_modified"] for record in records if record["source_modified"]]
        metadata = {
            "scope": SCOPE, "target_neighborhood_count": len(regions), "source_record_count": len(entries),
            "page_count": len(records), "excluded_neighborhoods": excluded, "unknown_neighborhoods": unknown,
            "alias_matches": aliases, "tag_count": len({tag for record in records for tag in record["tags"]}),
            "page_intro_missing_count": sum(record["page_intro"] is None for record in records),
        }
        progress(95, f"{len(entries)} mahalle kaydı okundu; {len(records)} kanonik mahalle seçildi.")
        return CollectionResult(records, len(entries), len(entries) - len(records), max(modified) if modified else None, metadata)
    finally:
        if owns_client:
            client.close()


class NeighborhoodsConnector:
    name = "south-walton-neighborhoods"
    version = CONNECTOR_VERSION
    raw_filename = "manifest.json"
    method = "HTML"
    diff_enabled = True
    FIELDS = ("name", "permalink", "page_url", "canonical_region_id", "summary", "latitude", "longitude", "source_modified", "page_intro")

    def supports(self, source):
        return (source.get("destination_id") == "30a"
                and https_source_identity(source["url"], host_aliases=SOURCE_HOST_ALIASES) == SOURCE_IDENTITY)

    def collect(self, source, raw_path, progress, canceled, *, context):
        return collect(raw_path, progress, canceled, regions=context.canonical_regions)

    def store_records(self, con, run_id, records, related=None):
        for record in records:
            con.execute(f"""INSERT INTO neighborhood_records (run_id,external_id,{','.join(self.FIELDS)},tags)
                VALUES ({','.join('?' * (len(self.FIELDS) + 3))})""",
                (run_id, record["external_id"], *(record[field] for field in self.FIELDS),
                 json.dumps(record["tags"], ensure_ascii=False)))

    def read_records(self, con, run_id):
        records = []
        for row in con.execute("""SELECT n.*, r.name AS canonical_region_name FROM neighborhood_records n
                LEFT JOIN regions r ON r.id=n.canonical_region_id WHERE n.run_id=? ORDER BY n.longitude, n.name""", (run_id,)):
            record = dict(row)
            record["tags"] = json.loads(record["tags"])
            records.append(record)
        return records

    def comparison_value(self, record):
        # The CMS modification stamp alone is not a content change.
        return {**{field: record[field] for field in self.FIELDS if field != "source_modified"}, "tags": sorted(set(record["tags"]))}
