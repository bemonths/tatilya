import csv
import io
import json
import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Database
from studio.sources import beaches

HEADERS = {"X-Studio-Request": "1"}


def point(**changes):
    return {"id": "coast-1", "name": "Test access", "city": "Santa Rosa Beach", "type": "neighborhood",
            "address": "100 Test Road", "lat": 30.35, "lng": -86.14, "features": [], **changes}


def page(*records):
    data = ",\n".join(json.dumps(record) for record in records)
    return ('<html><script>function initMarkers(){ var data = [' + data +
            ',];}</script><p>Latest map update: Sep 21, 2026 6:56:10 pm</p></html>').encode()


def run_job(client):
    source = next(source for source in client.get("/api/sources").json() if source["url"] == beaches.SOURCE_URL)
    response = client.post("/api/jobs", json={"kind": "beach_collection", "source_id": source["id"]})
    assert response.status_code == 202
    return response.json()["id"]


def finished(client, identifier, timeout=30):
    """Poll until the job leaves queued/running. The generous upper bound only matters on a loaded machine;
    a finished job still returns on the first check, and the state is read once more at the deadline."""
    deadline = time.monotonic() + timeout
    while True:
        job = client.app.state.db.job(identifier)
        if job["status"] not in ("queued", "running"):
            return job
        if time.monotonic() >= deadline:
            pytest.fail(f"Veri toplama işi {timeout} sn içinde bitmedi: {job['status']} · {job['message']}")
        time.sleep(.02)


def fake_collector(content):
    def collect(path, progress, canceled):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return beaches.parse_page(content)
    return collect


def test_scope_missing_amenities_trailing_comma_and_provenance():
    content = page(point(), point(id="miramar", city="Miramar Beach"), point(id="bay", type="bays-lakes"),
                   point(id="coast-2", city="Inlet Beach", features=["Parking", "Parking", "Restrooms"]))
    batch = beaches.parse_page(content)
    assert (batch.total_count, len(batch.records), batch.excluded_count) == (4, 2, 2)
    assert batch.records[0]["features"] == []
    assert batch.records[0]["city"] == "Santa Rosa Beach"
    assert batch.records[1]["features"] == ["Parking", "Restrooms"]
    assert not hasattr(batch, "raw_sha256")
    assert batch.source_updated == "Sep 21, 2026 6:56:10 pm"


@pytest.mark.parametrize("content", [
    b"<html>Structure changed</html>", b"function initMarkers(){var data=[];}",
    b"function initMarkers(){var data=[{", page(point(), point()), page(point(lat=True)),
    page(point(lng=0)), page(point(name="")), page(point(features="Parking")),
    page(point(type="new-kind")), page(point(city="Miramar Beach")),
    b"function initMarkers(){var data=[alert('must never execute')];}",
])
def test_changed_invalid_or_empty_source_rejected(content):
    with pytest.raises(beaches.SourceError):
        beaches.parse_page(content)


def test_http_collect_saves_exact_source(tmp_path):
    content = page(point())
    seen, progress = [], []
    def transport(request):
        seen.append(str(request.url))
        return httpx.Response(200, headers={"content-type": "text/html"}, content=content)
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        batch = beaches.collect(tmp_path / "raw.html", lambda *args: progress.append(args), lambda: False, client=client)
    assert seen == [beaches.SOURCE_URL]
    assert (tmp_path / "raw.html").read_bytes() == content
    assert len(batch.records) == 1
    assert progress[-1][0] == 85


@pytest.mark.parametrize("status,content_type,body", [
    (429, "text/html", b"rate limit"), (302, "text/html", b"redirect"),
    (403, "text/html", b"denied"), (200, "application/json", b"{}"),
    (200, "text/html", b"x" * (beaches.MAX_BYTES + 1)),
], ids=["rate-limit", "redirect", "forbidden", "wrong-type", "oversized"])
def test_http_failures_stop_without_replacing_source(tmp_path, status, content_type, body):
    requests = []
    def transport(request):
        requests.append(request)
        return httpx.Response(status, headers={"content-type": content_type}, content=body)
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(beaches.SourceError):
            beaches.collect(tmp_path / "raw.html", lambda *args: None, lambda: False, client=client)
    assert len(requests) == 1
    assert not (tmp_path / "raw.html").exists()


def test_transient_error_retried_once(tmp_path, monkeypatch):
    requests = []
    monkeypatch.setattr(beaches.time, "sleep", lambda _: None)
    def transport(request):
        requests.append(request)
        return httpx.Response(503 if len(requests) == 1 else 200, headers={"content-type": "text/html"}, content=page(point()))
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        result = beaches.collect(tmp_path / "raw.html", lambda *args: None, lambda: False, client=client)
    assert len(requests) == 2 and len(result.records) == 1


def test_cancellation_before_network(tmp_path):
    def unexpected(request):
        pytest.fail("İptal sonrası ağ isteği yapılmamalı")
    with httpx.Client(transport=httpx.MockTransport(unexpected)) as client:
        with pytest.raises(beaches.CollectionCanceled):
            beaches.collect(tmp_path / "raw.html", lambda *args: None, lambda: True, client=client)


def test_snapshots_export_restart_and_failed_collection_preserve_data(tmp_path, monkeypatch):
    first_page = page(point(name="=Test formula", features=["Parking"]))
    monkeypatch.setattr(beaches, "collect", fake_collector(first_page))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        first = run_job(client)
        assert finished(client, first)["status"] == "done"
        monkeypatch.setattr(beaches, "collect", fake_collector(page(point(name="Changed access"))))
        second = run_job(client)
        assert finished(client, second)["status"] == "done"
        assert len(client.get("/api/collections").json()) == 2
        assert client.get(f"/api/collections/{first}").json()["records"][0]["name"] == "=Test formula"
        exported = client.get(f"/api/collections/{first}/export.csv")
        assert exported.content.startswith(b"\xef\xbb\xbf")
        rows = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig")), delimiter=";"))
        assert rows[1][1] == "'=Test formula"
        assert rows[1][6] == "-86.14"
        assert rows[1][7] == "Otopark"
        assert rows[1][8] == beaches.SOURCE_URL
        raw = client.get(f"/api/collections/{first}/raw")
        assert raw.content == first_page
        assert "text/plain" in raw.headers["content-type"]
        monkeypatch.setattr(beaches, "collect", fake_collector(b"Unexpected page"))
        failed = run_job(client)
        assert finished(client, failed)["status"] == "failed"
        assert len(client.get("/api/collections").json()) == 2
        assert client.get("/api/collections/missing").status_code == 404
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        assert [entry["id"] for entry in client.get("/api/collections").json()] == [second, first]
        assert client.get(f"/api/collections/{second}").json()["records"][0]["name"] == "Changed access"


def test_duplicate_job_and_late_canceled_result_cannot_publish(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def held_collector(path, progress, canceled):
        entered.set()
        assert release.wait(3)
        return beaches.parse_page(page(point()))
    monkeypatch.setattr(beaches, "collect", held_collector)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        try:
            identifier = run_job(client)
            assert entered.wait(2)
            source = next(source for source in client.get("/api/sources").json() if source["url"] == beaches.SOURCE_URL)
            assert client.post("/api/jobs", json={"kind": "beach_collection", "source_id": source["id"]}).status_code == 409
            assert client.post(f"/api/jobs/{identifier}/cancel").json()["status"] == "canceled"
        finally:
            release.set()
    db = Database(tmp_path / "studio.sqlite3")
    assert db.job(identifier)["status"] == "canceled"
    assert db.collections() == []


def test_unsupported_source_is_never_fetched(tmp_path, monkeypatch):
    def unexpected(*args):
        pytest.fail("Desteklenmeyen kaynak için toplayıcı çalışmamalı")
    monkeypatch.setattr(beaches, "collect", unexpected)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        source = next(source for source in client.get("/api/sources").json() if source["url"] != beaches.SOURCE_URL)
        assert client.post("/api/jobs", json={"kind": "beach_collection", "source_id": source["id"]}).status_code == 409
        assert client.post("/api/jobs", json={"kind": "beach_collection"}).status_code == 422
        assert client.post("/api/jobs", json={"kind": "beach_collection", "source_id": "missing"}).status_code == 409


def test_migration_keeps_existing_sources_and_jobs(tmp_path):
    from tests.legacy import make_legacy_db, without_v7_source
    db = Database(tmp_path / "studio.sqlite3")
    make_legacy_db(db.path, version=1)
    with db.connect() as con:
        original = [{**dict(r),"destination_id":"30a","scope_region_id":None} for r in con.execute("SELECT * FROM sources ORDER BY created_at,name")]
    db.initialize()
    assert without_v7_source(db.sources()) == original
    assert db.job("old-success")["result"] == {"included": 1}
    assert db.collections() == []
