import json
import sqlite3
import threading

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Database, Conflict
from studio.regions import REGIONS
from studio.sources import beaches
from studio.sources.base import CollectionResult
from studio.sources.registry import ConnectorRegistry, DEFAULT_REGISTRY
from tests.legacy import make_legacy_db, without_added_sources
from tests.test_beaches import HEADERS, point, page, fake_collector, finished
from tests.test_studio import payload


def source_id(client):
    return next(source["id"] for source in client.get("/api/sources").json() if source["url"] == beaches.SOURCE_URL)


def collect(client, identifier=None):
    response = client.post("/api/jobs", json={"kind": "source_collection", "source_id": identifier or source_id(client)})
    assert response.status_code == 202, response.text
    job = finished(client, response.json()["id"])
    return job, client.app.state.db.source_run(job["id"])


def test_v02_migration_preserves_all_user_data_and_raw_files(tmp_path):
    path = tmp_path / "studio.sqlite3"
    make_legacy_db(path)
    db = Database(path)
    with db.connect() as con:
        sources_before = [{**dict(r),"destination_id":"30a","scope_region_id":None} for r in con.execute("SELECT * FROM sources ORDER BY created_at,name")]
    with db.connect() as con:
        history_before = [tuple(row) for row in con.execute("SELECT * FROM source_history")]
        record_before = tuple(con.execute("SELECT * FROM beach_records").fetchone())
        job_before = dict(con.execute("SELECT * FROM jobs WHERE id='old-success'").fetchone())
    db.initialize()
    assert without_added_sources(db.sources()) == sources_before
    run = db.source_run("old-success")
    assert run["source_id"] == "source-a" and run["job_id"] == "old-success"
    assert run["connector_version"] == "south-walton-beaches/1"
    assert run["status"] == "done" and run["record_count"] == run["excluded_count"] == 1
    assert run["metadata"]["total_count"] == 2
    assert run["fetched_at"] == "2026-09-02" and run["started_at"] is None
    assert db.source_run("old-failed")["source_id"] is None
    assert db.source_run("old-failed")["metadata"]["source_identity_unknown"]
    assert db.source_run("old-canceled")["status"] == "canceled"
    with db.connect() as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 8
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        assert [tuple(row) for row in con.execute("SELECT * FROM source_history")] == history_before
        assert tuple(con.execute("SELECT * FROM beach_records").fetchone()) == (*record_before, "Santa Rosa Beach", None)
        job_after = dict(con.execute("SELECT * FROM jobs WHERE id='old-success'").fetchone())
        for key in ("id", "title", "message", "log", "result", "created_at", "finished_at"):
            assert job_after[key] == job_before[key]
        assert job_after["source_id"] == "source-a" and job_after["kind"] == "source_collection"
        assert con.execute("PRAGMA foreign_key_list(beach_records)").fetchall()[1][2] == "source_runs"
    assert (tmp_path / run["raw_path"]).read_text(encoding="utf-8") == "Sentetik eski ham kaynak"
    backups = list((tmp_path / "backups").glob("*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM beach_records").fetchone()[0] == 1
    db.initialize()
    assert len(db.source_runs()) == 3 and without_added_sources(db.sources()) == sources_before
    assert len(list((tmp_path / "backups").glob("*.sqlite3"))) == 1


def test_failed_migration_rolls_back(tmp_path, monkeypatch):
    from studio import migrations
    path = tmp_path / "studio.sqlite3"
    make_legacy_db(path)
    original = migrations.execute_schema
    def fail_after_ddl(con, sql):
        original(con, sql)
        raise RuntimeError("Simulated migration interruption")
    with monkeypatch.context() as scoped:
        scoped.setattr(migrations, "execute_schema", fail_after_ddl)
        with pytest.raises(RuntimeError):
            Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 1
        assert "source_id" not in [row[1] for row in con.execute("PRAGMA table_info(jobs)")]
        assert con.execute("SELECT COUNT(*) FROM beach_records").fetchone()[0] == 1
    Database(path).initialize()
    assert Database(path).source_run("old-success")["record_count"] == 1


def test_generic_job_success_and_failure_are_source_linked(tmp_path, monkeypatch):
    monkeypatch.setattr(beaches, "collect", fake_collector(page(point())))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        job, run = collect(client)
        assert job["kind"] == "source_collection" and job["source_id"] == source_id(client)
        assert run["status"] == "done" and run["job_id"] == job["id"]
        assert run["source_id"] == job["source_id"] and run["record_count"] == 1
        assert run["started_at"] <= run["finished_at"] and run["raw_sha256"]
        assert run["raw_path"] and run["fetched_at"]
        record = client.get(f"/api/source-runs/{run['id']}").json()["records"][0]
        assert record["source_region_text"] == "Santa Rosa Beach" and record["canonical_region_id"] is None
        good = run["id"]
        monkeypatch.setattr(beaches, "collect", fake_collector(b"Page structure changed"))
        failed, failed_run = collect(client)
        assert failed["status"] == failed_run["status"] == "failed"
        assert failed_run["source_id"] == source_id(client)
        assert failed_run["record_count"] == 0 and failed_run["error_message"]
        assert failed_run["raw_path"] and failed_run["raw_sha256"] and failed_run["fetched_at"]
        assert len(client.get("/api/collections").json()) == 1
        assert client.get(f"/api/source-runs/{good}").json()["records"] == [record]
        assert len(client.get("/api/source-runs", params={"source_id": source_id(client)}).json()) == 2
        assert client.get("/api/source-runs", params={"source_id": "unknown"}).json() == []
        assert client.get("/api/source-runs/missing/diff").status_code == 404
        assert client.get("/api/source-runs/missing").status_code == 404
        assert not client.get(f"/api/source-runs/{failed['id']}/diff").json()["available"]


def test_cancellation_and_restart_keep_runs_consistent(tmp_path, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def delayed(path, progress, canceled):
        entered.set()
        assert release.wait(3)
        return fake_collector(page(point()))(path, progress, canceled)
    monkeypatch.setattr(beaches, "collect", delayed)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        try:
            job = client.post("/api/jobs", json={"kind": "source_collection", "source_id": source_id(client)}).json()
            assert entered.wait(2)
            assert client.post(f"/api/jobs/{job['id']}/cancel").status_code == 200
        finally:
            release.set()
    db = Database(tmp_path / "studio.sqlite3")
    assert db.source_run(job["id"])["status"] == "canceled"
    assert db.run_records(job["id"]) == [] and db.collections() == []
    connector = DEFAULT_REGISTRY.by_name("south-walton-beaches")
    pending = db.add_job("source_collection", "Restart test", source_id=job["source_id"], connector=connector)
    db.recover_jobs()
    assert db.job(pending)["status"] == db.source_run(pending)["status"] == "interrupted"


def test_diff_is_scoped_immutable_and_ignores_feature_order(tmp_path, monkeypatch):
    original = page(point(id="keep", features=["Parking", "Restrooms"]), point(id="change"), point(id="remove"))
    updated = page(point(id="keep", features=["Restrooms", "Parking"]), point(id="change", address="Changed"), point(id="add"))
    monkeypatch.setattr(beaches, "collect", fake_collector(original))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        first, _ = collect(client)
        snapshot = client.get(f"/api/collections/{first['id']}").json()
        assert not snapshot["diff"]["available"]
        monkeypatch.setattr(beaches, "collect", fake_collector(b"broken"))
        collect(client)
        monkeypatch.setattr(beaches, "collect", fake_collector(updated))
        second, _ = collect(client)
        result = client.get(f"/api/source-runs/{second['id']}/diff").json()
        assert result == {"available": True, "previous_run_id": first["id"], "added": 1, "removed": 1, "changed": 1, "unchanged": 1,
                          "previous_connector_version": beaches.PARSER_VERSION,
                          "connector_version": beaches.PARSER_VERSION, "connector_version_changed": False}
        third, _ = collect(client)
        assert client.get(f"/api/source-runs/{third['id']}/diff").json()["unchanged"] == 3
        assert client.get(f"/api/source-runs/{second['id']}/diff").json() == result
        assert client.get(f"/api/collections/{first['id']}").json() == snapshot
        with client.app.state.db.connect() as con:
            other = client.app.state.db.save_source(payload())
            con.execute("UPDATE source_runs SET source_id=? WHERE id=?", (other["id"], second["id"]))
        assert not client.get(f"/api/source-runs/{second['id']}/diff").json()["available"]


class TestConnector:
    __test__ = False
    name, version, raw_filename = "test-connector", "1", "source.txt"

    def supports(self, source):
        return source["url"] == "https://example.org/30a"

    def collect(self, source, raw_path, progress, canceled, *, context):
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text("Synthetic test response", encoding="utf-8")
        return CollectionResult([{"external_id": "test-id", "value": 12}], 1, 0, None)

    def store_records(self, con, run_id, records, related=None):
        con.execute("CREATE TABLE IF NOT EXISTS test_domain(run_id TEXT,external_id TEXT,value INTEGER)")
        con.executemany("INSERT INTO test_domain VALUES (?,?,?)", [(run_id, record["external_id"], record["value"]) for record in records])

    def read_records(self, con, run_id):
        return [dict(row) for row in con.execute("SELECT * FROM test_domain WHERE run_id=?", (run_id,))]

    def comparison_value(self, record):
        return {"value": record["value"]}


def test_second_connector_needs_no_job_or_app_special_case(tmp_path):
    registry = ConnectorRegistry([*DEFAULT_REGISTRY.connectors, TestConnector()])
    assert registry.for_source({"destination_id":"30a","url": beaches.SOURCE_URL}).name == "south-walton-beaches"
    assert registry.for_source({"destination_id":"30a","url": "https://unknown.example"}) is None
    with TestClient(create_app(tmp_path, registry), headers=HEADERS) as client:
        source = client.post("/api/sources", json=payload()).json()
        job, run = collect(client, source["id"])
        assert job["status"] == "done" and run["connector_name"] == "test-connector"
        assert client.get(f"/api/source-runs/{run['id']}").json()["records"][0]["value"] == 12
        assert client.get("/api/collections").json() == []
        listed_job = client.get("/api/jobs").json()[0]
        assert listed_job["source_name"] == source["name"]
        audit = client.post("/api/jobs", json={"kind": "catalog_audit"}).json()
        assert finished(client, audit["id"])["source_id"] is None


def test_domain_failure_rolls_back_and_diagnostic_excludes_secret(tmp_path):
    class FailingConnector(TestConnector):
        def store_records(self, con, run_id, records, related=None):
            super().store_records(con, run_id, records)
            raise RuntimeError("password=private-test-password token=ghp_private_test_token")
    with TestClient(create_app(tmp_path, ConnectorRegistry([FailingConnector()])), headers=HEADERS) as client:
        source = client.post("/api/sources", json=payload()).json()
        job, run = collect(client, source["id"])
        assert job["status"] == run["status"] == "failed"
        assert run["record_count"] == 0
        with client.app.state.db.connect() as con:
            assert con.execute("SELECT name FROM sqlite_master WHERE name='test_domain'").fetchone() is None
            stored = con.execute("SELECT diagnostic FROM jobs WHERE id=?", (job["id"],)).fetchone()[0]
            info = json.loads(stored)
            assert info["exception_type"] == "RuntimeError" and info["traceback"]
            assert "private_test_token" not in stored and "private-test-password" not in stored
        assert "diagnostic" not in client.get("/api/jobs").text
        assert "private-test-password" not in json.dumps(job)


def test_regions_and_entity_integrity_without_auto_matching(tmp_path):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    with db.connect() as con:
        assert [tuple(row) for row in con.execute("SELECT id,name FROM regions ORDER BY rowid")] == list(REGIONS)
        assert len(REGIONS) == 13
        assert con.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 0
        con.execute("INSERT INTO entities VALUES ('entity-1','hotel','The Pearl',NULL,NULL,NULL,'now','now','30a')")
        ids = [source["id"] for source in db.sources()][:2]
        con.execute("INSERT INTO entity_sources(entity_id,source_id,external_id) VALUES ('entity-1',?,'external-a')", (ids[0],))
        con.execute("INSERT INTO entity_sources(entity_id,source_id,external_id) VALUES ('entity-1',?,'external-b')", (ids[1],))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO entity_sources(entity_id,source_id,external_id) VALUES ('missing',?,'invalid')", (ids[0],))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO entity_sources(entity_id,source_id,external_id) VALUES ('entity-1',?,'external-a')", (ids[0],))
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("UPDATE entities SET canonical_region_id='invented' WHERE id='entity-1'")
        con.execute("UPDATE entities SET canonical_region_id='rosemary-beach' WHERE id='entity-1'")
        assert con.execute("SELECT COUNT(*) FROM entity_sources").fetchone()[0] == 2


def test_redirect_same_host_accepted(tmp_path):
    seen = []
    def respond(request):
        seen.append(str(request.url))
        if len(seen) == 1:
            return httpx.Response(301, headers={"location": "/new-beach-map/"})
        return httpx.Response(200, headers={"content-type": "text/html"}, content=page(point()))
    with httpx.Client(transport=httpx.MockTransport(respond), follow_redirects=True) as client:
        result = beaches.collect(tmp_path / "raw.html", lambda *args: None, lambda: False, client=client)
    assert len(result.records) == 1 and seen == [beaches.SOURCE_URL, "https://www.visitsouthwalton.com/new-beach-map/"]


@pytest.mark.parametrize("destination", ["https://other.example/map", "https://other.visitsouthwalton.com/map",
    "//www.visitsouthwalton.com.evil.example/map", "http://www.visitsouthwalton.com/map",
    "https://user:password@www.visitsouthwalton.com/map", "https://www.visitsouthwalton.com:8443/map"])
def test_redirect_cross_host_or_unsafe_rejected_without_request(tmp_path, destination):
    seen = []
    def respond(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"location": destination})
    with httpx.Client(transport=httpx.MockTransport(respond), follow_redirects=True) as client:
        with pytest.raises(beaches.SourceError, match="Yönlendirme izlenmedi"):
            beaches.collect(tmp_path / "raw.html", lambda *args: None, lambda: False, client=client)
    assert seen == [beaches.SOURCE_URL]


def test_redirect_loop_bounded(tmp_path):
    seen = []
    def respond(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"location": "/loop"})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(beaches.SourceError, match="sınırı"):
            beaches.collect(tmp_path / "raw.html", lambda *args: None, lambda: False, client=client)
    assert len(seen) == 4


def test_source_job_dedup_is_per_source_and_source_snapshot_is_checked(tmp_path):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    first = db.save_source(payload())
    second = db.save_source(payload(url="https://example.org/second"))
    connector = TestConnector()
    a = db.add_job("source_collection", "First", first["id"], connector, first["version"])
    with pytest.raises(Conflict):
        db.add_job("source_collection", "Duplicate", first["id"], connector, first["version"])
    b = db.add_job("source_collection", "Other source", second["id"], connector, second["version"])
    assert a != b and len(db.source_runs()) == 2
    db.update_job(a, status="canceled")
    db.save_source({**first, "name": "Changed source"}, first["id"], first["version"])
    with pytest.raises(Conflict, match="Kaynak değişti"):
        db.add_job("source_collection", "Stale request", first["id"], connector, first["version"])
    assert len(db.source_runs()) == 2


def test_generic_unsupported_source_and_registry_constraints(tmp_path):
    assert len(DEFAULT_REGISTRY.connectors) == 7
    with pytest.raises(ValueError, match="benzersiz"):
        ConnectorRegistry([TestConnector(), TestConnector()])
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        source = client.post("/api/sources", json=payload()).json()
        response = client.post("/api/jobs", json={"kind": "source_collection", "source_id": source["id"]})
        assert response.status_code == 409
        assert response.json()["detail"] == "Bu kaynak için henüz veri toplayıcı bağlanmadı."
        assert client.get("/api/source-runs").json() == []


def test_malformed_redirect_is_a_readable_source_error(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
            302, headers={"location": "https://www.visitsouthwalton.com:invalid/map"}))) as client:
        with pytest.raises(beaches.SourceError, match="geçersiz"):
            beaches.collect(tmp_path / "raw.html", lambda *args: None, lambda: False, client=client)
