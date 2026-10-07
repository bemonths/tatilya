import time

import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Conflict, Database

HEADERS = {"X-Studio-Request": "1"}


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as session:
        yield session


def payload(**changes):
    return {"destination_id":"30a", "name": "Deneme kaynağı", "url": "https://example.org/30a", "category": "Konaklama",
            "region": "Rosemary Beach", "method": "HTML", "cadence": "Haftalık",
            "notes": "Konaklama türü, fiyat ve tarih", "enabled": True, **changes}


def editable(source, **changes):
    keys = ["name", "url", "category", "region", "method", "cadence", "notes", "enabled"]
    return {**{key: source[key] for key in keys}, "expected_version": source["version"], **changes}


def wait_job(client, identifier, timeout=30):
    """Same bounded polling as tests.test_beaches.finished, through the public jobs API."""
    deadline = time.monotonic() + timeout
    while True:
        job = next(item for item in client.get("/api/jobs").json() if item["id"] == identifier)
        if job["status"] not in ("queued", "running"):
            return job
        if time.monotonic() >= deadline:
            pytest.fail(f"İş {timeout} sn içinde tamamlanmadı: {job['status']} · {job['message']}")
        time.sleep(0.02)


def test_sources_survive_restart_and_seed_is_not_duplicated(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        assert len(client.get("/api/sources").json()) == 12
        result = client.post("/api/sources", json=payload())
        assert result.status_code == 201
        identifier = result.json()["id"]
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        sources = client.get("/api/sources").json()
        assert len(sources) == 13
        assert next(source for source in sources if source["id"] == identifier)["notes"] == payload()["notes"]


def test_edit_archive_restore_and_history(client):
    source = client.post("/api/sources", json=payload()).json()
    url = f"/api/sources/{source['id']}"
    source = client.put(url, json=editable(source, name="Güncellenmiş kaynak", enabled=False)).json()
    assert source["name"] == "Güncellenmiş kaynak"
    assert source["enabled"] == 0
    assert source["version"] == 2
    source = client.put(url, json=editable(source, enabled=True)).json()
    assert source["enabled"] == 1
    assert source["version"] == 3
    with client.app.state.db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM source_history WHERE source_id=?", (source["id"],)).fetchone()[0] == 3


def test_stale_edit_does_not_overwrite(client):
    source = client.post("/api/sources", json=payload()).json()
    url = f"/api/sources/{source['id']}"
    assert client.put(url, json=editable(source, name="Yeni ad")).status_code == 200
    assert client.put(url, json=editable(source, name="Eski pencereden ad")).status_code == 409
    assert client.app.state.db.source(source["id"])["name"] == "Yeni ad"


def test_duplicate_normalized_url(client):
    assert client.post("/api/sources", json=payload(url="https://EXAMPLE.ORG/30a#one")).status_code == 201
    assert client.post("/api/sources", json=payload(url="https://example.org/30a#two")).status_code == 409


@pytest.mark.parametrize("change", [
    {"destination_id":"30a","url": "javascript:alert(1)"}, {"destination_id":"30a","url": "file:///C:/private"},
    {"destination_id":"30a","url": "https://user:password@example.org"}, {"name": " "}, {"category": "Bilinmeyen"},
])
def test_invalid_source_rejected(client, change):
    assert client.post("/api/sources", json=payload(**change)).status_code == 422
    assert len(client.get("/api/sources").json()) == 12


def test_missing_source_update(client):
    assert client.put("/api/sources/missing", json={**payload(), "expected_version": 1}).status_code == 404


def test_audit_is_persistent_and_does_not_change_source_records(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        before = client.get("/api/sources").json()
        response = client.post("/api/jobs", json={"kind": "catalog_audit"})
        assert response.status_code == 202
        job = wait_job(client, response.json()["id"])
        assert job["status"] == "done"
        assert job["result"]["checked"] == 12
        assert job["result"]["needs_attention"] == 4
        assert client.get("/api/sources").json() == before
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        assert client.get("/api/jobs").json()[0]["result"] == job["result"]


def test_cancellation_wins_over_late_worker_result(tmp_path):
    db = Database(tmp_path / "test.sqlite3")
    db.initialize()
    identifier = db.add_job()
    assert db.update_job(identifier, status="running")
    assert db.update_job(identifier, status="canceled")
    assert not db.update_job(identifier, status="done", progress=100, result={"checked": 7})
    assert db.job(identifier)["status"] == "canceled"
    assert db.job(identifier)["result"] is None


def test_duplicate_active_job_and_restart_recovery(tmp_path):
    db = Database(tmp_path / "test.sqlite3")
    db.initialize()
    identifier = db.add_job()
    with pytest.raises(Conflict):
        db.add_job()
    db.recover_jobs()
    assert db.job(identifier)["status"] == "interrupted"
    assert db.add_job() != identifier


def test_no_enabled_sources_cannot_start_audit(client):
    for source in client.get("/api/sources").json():
        assert client.put(f"/api/sources/{source['id']}", json=editable(source, enabled=False)).status_code == 200
    assert client.post("/api/jobs", json={"kind": "catalog_audit"}).status_code == 409


def test_cross_origin_and_missing_request_marker_rejected(client):
    assert client.post("/api/sources", json=payload(), headers={"Origin": "https://example.org"}).status_code == 403
    assert client.post("/api/sources", json=payload(), headers={"X-Studio-Request": ""}).status_code == 403


def test_unknown_job_and_invalid_kind(client):
    assert client.post("/api/jobs/missing/cancel").status_code == 404
    assert client.post("/api/jobs", json={"kind": "run_shell"}).status_code == 422
