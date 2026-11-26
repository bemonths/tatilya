"""Reading a Gatsby site's own data files (HEDEF-01, 26 November 2026: visitsouthwalton.com was rebuilt with Gatsby; the map points,
the neighbourhoods and the listings are no longer in the page's HTML).

A Gatsby page's data is public, static JSON the page itself loads for every visitor:
- `/page-data/<path>/page-data.json`: the page's own query result (`result.data`), its template (`componentChunkName`) and the hashes
  of the site-wide static queries it uses (`staticQueryHashes`);
- `/page-data/sq/d/<hash>.json`: one static query's result (`data`).
To find which static query holds a key (e.g. `allBeachAccess`) without asking all of them, the template's own script (named in the
page's `window.___chunkMapping`) is read: the hashes it names are asked first; the others only when none of them has the key.

`fetch(url) -> bytes` is the collector's own request (its client, its host check, its pace); every answer is returned with its address
so the collector keeps the raw copies.
"""
import json
import re
from urllib.parse import urlsplit

from .base import SourceError

CHUNKS = re.compile(r'window\.___chunkMapping="(.*?)";', re.S)


def page_data_url(page_url):
    parts = urlsplit(page_url)
    path = parts.path.strip("/") or "index"
    return f"{parts.scheme}://{parts.netloc}/page-data/{path}/page-data.json"


def chunk_files(page_html):
    """The template scripts named in the page (`window.___chunkMapping`): {chunk name: [paths]}."""
    match = CHUNKS.search(page_html or "")
    if not match:
        return {}
    try:
        return json.loads(match.group(1).encode("utf-8").decode("unicode_escape"))
    except (ValueError, UnicodeDecodeError):
        return {}


def json_of(body, what):
    try:
        return json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise SourceError(f"{what} JSON olarak okunamadı; site yapısı değişmiş olabilir.") from exc


def page_data(fetch, page_url):
    """(page-data dict, raw) of a page."""
    url = page_data_url(page_url)
    body = fetch(url)
    data = json_of(body, "Sayfa verisi (page-data.json)")
    if not isinstance(data, dict) or not isinstance(data.get("result"), dict):
        raise SourceError("Sayfa verisinde beklenen 'result' alanı yok; site yapısı değişmiş olabilir.")
    return data, (url, body)


def static_query(fetch, page_url, page_html, key, *, data=None):
    """The static query result holding `key` (its `data` dict) and every raw answer read for it: [(url, bytes)]."""
    raws = []
    if data is None:
        data, raw = page_data(fetch, page_url)
        raws.append(raw)
    hashes = [str(h) for h in data.get("staticQueryHashes") or [] if re.fullmatch(r"\d{1,20}", str(h))]
    if not hashes:
        raise SourceError("Sayfa verisinde statik sorgu listesi yok; site yapısı değişmiş olabilir.")
    first = []
    files = chunk_files(page_html).get(data.get("componentChunkName") or "") or []
    origin = "{0.scheme}://{0.netloc}".format(urlsplit(page_url))
    if files:
        script = fetch(origin + files[0])
        raws.append((origin + files[0], script))
        text = script.decode("utf-8", errors="replace")
        first = [h for h in hashes if h in text]
    for value in first + [h for h in hashes if h not in first]:
        url = f"{origin}/page-data/sq/d/{value}.json"
        body = fetch(url)
        raws.append((url, body))
        answer = json_of(body, "Statik sorgu")
        if isinstance(answer, dict) and isinstance(answer.get("data"), dict) and key in answer["data"]:
            return answer["data"], raws
    raise SourceError(f"Sitenin statik sorgularında '{key}' bulunamadı; site yapısı değişmiş olabilir.")


def nodes(container):
    """`{"edges": [{"node": …}]}` or `{"nodes": […]}` → the list of nodes."""
    if not isinstance(container, dict):
        return []
    if isinstance(container.get("nodes"), list):
        return [n for n in container["nodes"] if isinstance(n, dict)]
    return [e["node"] for e in container.get("edges") or [] if isinstance(e, dict) and isinstance(e.get("node"), dict)]
