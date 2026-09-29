import hashlib
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.diagnostics import diagnostic
from studio.sources import beaches
from studio.sources.base import CollectionResult
from studio.sources.registry import ConnectorRegistry, DEFAULT_REGISTRY
from tests.legacy import make_legacy_db
from tests.test_beaches import HEADERS, page, point, fake_collector
from tests.test_foundation import TestConnector, collect
from tests.test_studio import payload


def test_generic_metadata_and_disk_hash(tmp_path):
    with TestClient(create_app(tmp_path, ConnectorRegistry([*DEFAULT_REGISTRY.connectors, TestConnector()])), headers=HEADERS) as client:
        source = client.post('/api/sources', json=payload()).json()
        for sources in (client.get('/api/sources').json(), client.get('/api/bootstrap').json()['sources']):
            connected = next(row for row in sources if row['id'] == source['id'])
            assert connected['connector'] == {'name': 'test-connector', 'version': '1'}
            assert any(row['connector'] is None for row in sources)
        job, run = collect(client, source['id'])
        assert job['result']['connector_name'] == 'test-connector'
        raw = (tmp_path / run['raw_path']).read_bytes()
        assert raw == b'Synthetic test response'
        assert run['raw_sha256'] == hashlib.sha256(raw).hexdigest()
        assert 'raw_sha256' not in CollectionResult.__dataclass_fields__


def test_migrated_run_compares_across_connector_versions(tmp_path, monkeypatch):
    make_legacy_db(tmp_path / 'studio.sqlite3')
    monkeypatch.setattr(beaches, 'collect', fake_collector(page(point())))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        source = next(row for row in db.sources() if row['id'] == 'source-a')
        db.save_source({**source, 'enabled': True}, source['id'], source['version'])
        job, run = collect(client, source['id'])
        diff = client.get(f"/api/source-runs/{run['id']}/diff").json()
        assert diff['available'] and diff['previous_run_id'] == 'old-success'
        assert diff['previous_connector_version'] == 'south-walton-beaches/1'
        assert diff['connector_version'] == beaches.PARSER_VERSION
        assert diff['connector_version_changed'] is True
        assert client.get(f"/api/collections/{run['id']}").json()['diff'] == diff


@pytest.mark.parametrize('origin,destination', [
    ('www.visitsouthwalton.com', 'visitsouthwalton.com'),
    ('visitsouthwalton.com', 'www.visitsouthwalton.com'),
])
def test_allowlisted_redirect_both_directions(tmp_path, monkeypatch, origin, destination):
    monkeypatch.setattr(beaches, 'SOURCE_URL', f'https://{origin}/map')
    seen = []
    def respond(request):
        seen.append(str(request.url))
        if len(seen) == 1:
            return httpx.Response(301, headers={'location': f'https://{destination}:443/new-map'})
        return httpx.Response(200, headers={'content-type': 'text/html'}, content=page(point()))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = beaches.collect(tmp_path / 'raw.html', lambda *args: None, lambda: False, client=client)
    assert len(result.records) == 1
    assert seen == [f'https://{origin}/map', f'https://{destination}/new-map']


@pytest.mark.parametrize('message,secrets', [
    ('password=mysecret token=abc123', ['mysecret', 'abc123']),
    ('Authorization: Bearer bearer-secret api_key=key-secret', ['bearer-secret', 'key-secret']),
    ('authorization=Bearer bearer-secret', ['bearer-secret']),
    ('{"password": "space secret", "api_key": "key secret"}', ['space secret', 'key secret']),
    ("token='quoted secret' API-KEY: key-secret", ['quoted secret', 'key-secret']),
    ('request https://user:pass123@host.example/path failed', ['user:', 'pass123']),
    ('keys ghp_test_secret sk-test-secret github_pat_test_secret', ['ghp_test_secret', 'sk-test-secret', 'github_pat_test_secret']),
    ('x' * 490 + ' token=' + 'a' * 100, ['a' * 3]),
])
def test_diagnostic_redacts_before_truncating(message, secrets):
    info = diagnostic(RuntimeError(message))
    assert len(info['technical_message']) <= 500
    for secret in secrets:
        assert secret not in json.dumps(info)
    assert '[RE' in info['technical_message']


def test_diagnostic_preserves_plain_message_and_only_trace_locations():
    private_local = 'must-not-leak'
    try:
        raise RuntimeError('database is locked')
    except RuntimeError as exc:
        info = diagnostic(exc)
    assert info['technical_message'] == 'database is locked'
    assert info['exception_type'] == 'RuntimeError'
    assert info['traceback']
    assert all(set(frame) == {'file', 'line', 'function'} for frame in info['traceback'])
    assert all(frame['file'] == Path(frame['file']).name for frame in info['traceback'])
    assert private_local not in json.dumps(info)


def test_safe_diagnostic_is_internal_db_only(tmp_path):
    class LockedConnector(TestConnector):
        def store_records(self, con, run_id, records):
            raise RuntimeError('database is locked')
    with TestClient(create_app(tmp_path, ConnectorRegistry([LockedConnector()])), headers=HEADERS) as client:
        source = client.post('/api/sources', json=payload()).json()
        job, run = collect(client, source['id'])
        with client.app.state.db.connect() as con:
            info = json.loads(con.execute('SELECT diagnostic FROM jobs WHERE id=?', (job['id'],)).fetchone()[0])
        assert info['technical_message'] == 'database is locked'
        for endpoint in ('/api/jobs', '/api/bootstrap', f"/api/source-runs/{run['id']}"):
            text = client.get(endpoint).text
            assert 'database is locked' not in text and 'technical_message' not in text
