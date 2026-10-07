"""Sequential HTTPS reads for the climate connectors; every completed response is kept with a manifest.

Generic core: allowed hosts, size limits and accepted content types come from the calling connector.
"""
import hashlib
import json
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from .base import CollectionCanceled, SourceError

USER_AGENT = "30AStudio/0.8 (+https://github.com/bemonths/tatilya)"
RETRY_SECONDS, REQUEST_GAP = 0.5, 0.2


def check(canceled):
    if canceled():
        raise CollectionCanceled()


def pause(seconds, canceled):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        check(canceled)
        time.sleep(min(0.05, max(0, end - time.monotonic())))


class Reader:
    """GET with one retry for network errors and 5xx; 404 can be accepted as a recorded 'missing' answer."""

    def __init__(self, client, manifest_path, canceled, *, connector, hosts, max_bytes, label):
        self.client, self.path, self.canceled = client, manifest_path, canceled
        self.hosts, self.max_bytes, self.label = frozenset(hosts), max_bytes, label
        self.manifest = {"connector": connector, "responses": []}
        self.request_gap, self.retry_seconds = REQUEST_GAP, RETRY_SECONDS

    def checked(self, url, base=None):
        try:
            if not isinstance(url, str) or any(ord(c) < 32 for c in url) or "\\" in url:
                raise ValueError()
            parts = urlsplit(urljoin(base, url) if base else url)
            if (parts.scheme != "https" or parts.hostname not in self.hosts or parts.username is not None
                    or parts.password is not None or parts.port not in (None, 443)):
                raise ValueError()
            return urlunsplit(("https", parts.hostname, parts.path or "/", parts.query, ""))
        except ValueError as exc:
            raise SourceError(f"{self.label} geçersiz veya izin verilmeyen bir adres döndürdü. İstek yapılmadı.") from exc

    def save(self, requested, response, body, suffix, note):
        sequence = len(self.manifest["responses"]) + 1
        relative = f"responses/{sequence:04d}{suffix}"
        target = self.path.parent / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        stamp = datetime.now(timezone.utc).isoformat()
        self.manifest["fetched_at"] = stamp
        self.manifest["responses"].append({
            "sequence": sequence, "note": note, "requested_url": requested, "final_url": str(response.url),
            "status": response.status_code, "content_type": response.headers.get("content-type"), "fetched_at": stamp,
            "raw_file": relative, "raw_sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
        temporary = self.path.with_suffix(".tmp")
        temporary.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def get(self, url, *, suffix, note, content_types, params=None, allow_missing=False):
        """Return (body bytes, final url), or (None, final url) for an accepted 404."""
        original = self.checked(url)
        if params:
            original = str(httpx.URL(original, params=params))
        for attempt in range(2):
            current = original
            try:
                for hop in range(4):
                    check(self.canceled)
                    pause(self.request_gap, self.canceled)
                    with self.client.stream("GET", current, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as response:
                        chunks, size = [], 0
                        for part in response.iter_bytes():
                            check(self.canceled)
                            size += len(part)
                            if size > self.max_bytes:
                                raise SourceError(f"{self.label} yanıtı boyut sınırını aştı.")
                            chunks.append(part)
                        body = b"".join(chunks)
                        self.save(current, response, body, suffix if response.status_code == 200 else ".txt", note)
                        if response.status_code in (301, 302, 303, 307, 308):
                            if hop == 3 or not response.headers.get("location"):
                                raise SourceError(f"{self.label} yönlendirme sınırı aşıldı veya hedef eksik.")
                            current = self.checked(response.headers["location"], current)
                            continue
                        if response.status_code == 404 and allow_missing:
                            return None, str(response.url)
                        if response.status_code == 429:
                            raise SourceError(f"{self.label} istek sınırına ulaştı (429). Daha sonra deneyin.")
                        if response.status_code >= 500:
                            if attempt == 0:
                                break
                            raise SourceError(f"{self.label} sunucu hatası döndürdü; daha sonra deneyin.")
                        if response.status_code != 200:
                            raise SourceError(f"{self.label} okunamadı (HTTP {response.status_code}).")
                        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                        if content_type not in content_types:
                            raise SourceError(f"{self.label} beklenen içerik türünü döndürmedi ({content_type or 'belirtilmemiş'}).")
                        return body, str(response.url)
            except (httpx.NetworkError, httpx.TimeoutException) as exc:
                if attempt == 1:
                    raise SourceError(f"{self.label} kaynağına bağlanılamadı veya zaman aşımı oluştu.") from exc
            except httpx.HTTPError as exc:
                raise SourceError(f"{self.label} HTTP yanıtı geçersiz.") from exc
            pause(self.retry_seconds, self.canceled)
        raise SourceError(f"{self.label} isteği tamamlanamadı.")


def make_client():
    return httpx.Client(timeout=httpx.Timeout(60, connect=10), verify=True)
