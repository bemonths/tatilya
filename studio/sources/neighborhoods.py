"""Visit South Walton neighborhood directory: embedded JSON index plus one page per neighborhood.

Only the 13 canonical 30A neighborhoods are stored. A source name is linked to a canonical region by
exact name or by the explicit alias table in the 30A profile; addresses and coordinates are never used
to infer a neighborhood. The coordinates are the source's representative point, not a neighborhood center.

HEDEF-01 (26 Nov 2026): visitsouthwalton.com was rebuilt with Gatsby; the directory page has no embedded `locations` list any more.
Its neighbourhoods come from the site's own public API (`/api/beach/neighborhood/all/`, the call the site's menu makes; the user
approved reading it on 26 Nov 2026). On 27 Nov 2026 that answer carried no coordinates (no lat/lng field) and an empty `activity`
list: the reader then stops with a clear error and keeps the raw answer; it never writes a coordinate the source does not give.
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
CONNECTOR_VERSION = "south-walton-neighborhoods/2"     # /2: the rebuilt site's API (HEDEF-01)
MAX_BYTES, MAX_RECORDS = 5_000_000, 100
API_URL = "https://www.visitsouthwalton.com/api/beach/neighborhood/all/?_sort=sort&_lang=en&_joinLang=en"
API_GAP, MAX_API_BYTES = 8.0, 20_000_000
GATSBY_MARK = re.compile(r'<div\s+id="___gatsby"')
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


def html_text(value):
    if not isinstance(value, str):
        return None
    if "<" in value:
        value = Tree(value).root.text()
    return clean(value) or None


def parse_api(answer):
    """The rebuilt site's neighbourhood list (HEDEF-01) as directory entries; a coordinate the answer lacks stays None."""
    if (not isinstance(answer, dict) or answer.get("errorCode") or answer.get("errorMessage")
            or not isinstance(answer.get("data"), list)):
        raise SourceError("Sitenin mahalle API cevabı beklenen biçimde değil; site yapısı değişmiş olabilir.")
    data = answer["data"]
    if not data:
        raise SourceError("Sitenin mahalle API'si boş liste döndürdü. Önceki kayıtlar korundu.")
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
        name = clean(name)
        if identifier in ids or name in names:
            raise SourceError("Mahalle dizininde yinelenen kaynak kimliği veya ad var. Önceki kayıtlar korundu.")
        ids.add(identifier)
        names.add(name)
        activities = item.get("activity") or []
        if not isinstance(activities, list):
            raise SourceError("Mahalle kaydının etiket listesi okunamadı.")
        tags = []
        for activity in activities:
            label = activity if isinstance(activity, str) else ((activity.get("object") or {}).get("name") if isinstance(activity, dict) else None)
            if not isinstance(label, str) or not clean(label) or len(label) > 100:
                raise SourceError("Mahalle kaydında geçersiz bir etiket var.")
            tags.append(clean(label))
        lat, lng = item.get("lat", item.get("latitude")), item.get("lng", item.get("longitude"))
        modified = item.get("modified")
        entries.append({
            "external_id": identifier, "name": name, "permalink": permalink, "page_url": page_url(permalink),
            "summary": html_text(item.get("description")),
            "latitude": None if lat is None else coordinate(lat, LATITUDE_RANGE, "enlem"),
            "longitude": None if lng is None else coordinate(lng, LONGITUDE_RANGE, "boylam"),
            "tags": sorted(set(tags)), "source_modified": clean(modified) or None if isinstance(modified, str) else None,
            # the neighbourhood page's intro is the record's own `introduction` field now (no page is read)
            "page_intro": html_text(item.get("introduction")),
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
        relative = f"api/{sequence:04d}.json" if kind == "api" else f"{'pages' if kind == 'page' else 'index'}/{sequence:04d}.html"
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
        api = kind == "api"
        original = checked_url(url)
        for attempt in range(2):
            current = original
            try:
                for hop in range(4):
                    check(self.canceled)
                    pause(API_GAP if api else REQUEST_GAP, self.canceled)
                    with self.client.stream("GET", current, follow_redirects=False,
                                            headers={"User-Agent": USER_AGENT, "Accept": "application/json" if api else "text/html"}) as response:
                        chunks, size = [], 0
                        for part in response.iter_bytes():
                            check(self.canceled)
                            size += len(part)
                            if size > (MAX_API_BYTES if api else MAX_BYTES):
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
                        if api:
                            if content_type != "application/json":
                                raise SourceError("Sitenin mahalle API'si JSON döndürmedi; site yapısı değişmiş olabilir.")
                            try:
                                return json.loads(body.decode("utf-8-sig")), str(response.url)
                            except (UnicodeError, ValueError) as exc:
                                raise SourceError("Sitenin mahalle API cevabı JSON olarak okunamadı.") from exc
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


def borrowed_coordinates(targets, previous):
    """HEDEF-02 (the manager's decision, 27 November 2026): the rebuilt site's neighbourhood API gives no coordinates. A neighbourhood
    whose record lacks them takes the coordinates of the same source's previous record with the same name (the old directory's own
    map pins); every other field is the new API's. Returns {name: note} for the borrowed ones; a name with no previous record keeps
    None (and the run stops as before)."""
    notes = {}
    if not previous or not previous.get("by_name"):
        return notes
    for entry, region in targets:
        if entry["latitude"] is not None and entry["longitude"] is not None:
            continue
        # the same name; else the record the old directory tied to the same neighbourhood by its name (e.g. "Watercolor"/"WaterColor")
        old = previous["by_name"].get(entry["name"]) or (previous.get("by_region") or {}).get(region["id"])
        if old is None:
            continue
        entry["latitude"], entry["longitude"] = old["latitude"], old["longitude"]
        notes[entry["name"]] = f"koordinat: aynı kaynağın {previous['date']} kaydından"
    return notes


def collect(raw_path, progress, canceled, *, client=None, regions=None, previous=None):
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
        rebuilt = "var locations" not in content and bool(GATSBY_MARK.search(content))
        if rebuilt:          # HEDEF-01: the rebuilt site; its own neighbourhood API
            progress(10, "Site yenilenmiş: sitenin kendi mahalle listesi okunuyor (API).")
            answer, _ = reader.get(API_URL, "api")
            entries = parse_api(answer)
        else:
            entries = parse_index(content)
        targets, excluded, unknown, aliases = select_targets(entries, regions)
        records = []
        borrowed = borrowed_coordinates(targets, previous) if rebuilt else {}
        if rebuilt:
            lacking = [entry["name"] for entry, _ in targets if entry["latitude"] is None or entry["longitude"] is None]
            if lacking:
                raise SourceError("Sitenin yeni mahalle verisinde koordinat (enlem/boylam) yok: " + ", ".join(lacking)
                                  + ". Kaynağın vermediği koordinat yazılmaz; mahalle kayıtları güncellenmedi, önceki kayıtlar korundu. "
                                  "Ham cevap çekim klasöründe saklandı.")
            records = [{**entry, "canonical_region_id": region["id"]} for entry, region in targets]
            targets = []
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
        if rebuilt:
            metadata.update(kaynak_bicimi="beach-neighborhood-api", page_count=0)
        if borrowed:        # HEDEF-02: which records' coordinates came from the same source's earlier run
            metadata["koordinat_kaynagi"] = {"run_id": previous["run_id"], "tarih": previous["date"], "notlar": borrowed,
                                             "aciklama": "Sitenin yeni mahalle API'si koordinat vermiyor; bu mahallelerin enlem/boylamı aynı "
                                                         "kaynağın önceki kaydından, mahalle adıyla eşleşerek alındı. Öbür alanlar yeni API'den."}
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

    inputs = ("neighborhood_coordinates",)       # HEDEF-02: the same source's previous coordinates (the new API has none)

    def collect(self, source, raw_path, progress, canceled, *, context):
        previous = (context.neighborhoods or {}).get("previous")
        return collect(raw_path, progress, canceled, regions=context.canonical_regions, previous=previous)

    def store_records(self, con, run_id, records, related=None):
        for record in records:
            con.execute(f"""INSERT INTO neighborhood_records (run_id,external_id,{','.join(self.FIELDS)},tags)
                VALUES ({','.join('?' * (len(self.FIELDS) + 3))})""",
                (run_id, record["external_id"], *(record[field] for field in self.FIELDS),
                 json.dumps(record["tags"], ensure_ascii=False)))

    def read_records(self, con, run_id):
        row = con.execute("SELECT metadata FROM source_runs WHERE id=?", (run_id,)).fetchone()
        notes = ((json.loads(row["metadata"]) if row and row["metadata"] else {}).get("koordinat_kaynagi") or {}).get("notlar") or {}
        records = []
        for row in con.execute("""SELECT n.*, r.name AS canonical_region_name FROM neighborhood_records n
                LEFT JOIN regions r ON r.id=n.canonical_region_id WHERE n.run_id=? ORDER BY n.longitude, n.name""", (run_id,)):
            record = dict(row)
            record["tags"] = json.loads(record["tags"])
            record["koordinat_notu"] = notes.get(record["name"])          # HEDEF-02: None when the record's own source gave them
            records.append(record)
        return records

    def comparison_value(self, record):
        # The CMS modification stamp alone is not a content change.
        return {**{field: record[field] for field in self.FIELDS if field != "source_modified"}, "tags": sorted(set(record["tags"]))}
