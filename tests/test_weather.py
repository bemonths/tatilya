from studio.destinations.thirty_a import ANCHORS, ANCHOR_PROVENANCE
"""Synthetic NWS responses only; no real HTTP in this module or pytest suite."""
import copy
import hashlib
import json
import sqlite3

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Database
from studio.migrations import upgrade_v3
from studio.sources import beaches, weather
from studio.sources.base import CollectionCanceled, SourceError
from studio.sources.registry import DEFAULT_REGISTRY, ConnectorRegistry
from tests.legacy import make_legacy_db, without_added_snapshot
from tests.test_beaches import HEADERS, finished


def forecast(hourly=False):
    return {'properties': {'generatedAt': '2026-09-30T08:00:00+00:00', 'updateTime': '2026-09-30T02:00:00-05:00',
        'periods': [{'number': n+1, 'name': 'Tonight' if not hourly else '',
            'startTime': f'2026-09-30T{10+n:02d}:00:00-05:00', 'endTime': f'2026-09-30T{11+n:02d}:00:00-05:00',
            'isDaytime': True, 'temperature': 80 if n == 0 else None, 'temperatureUnit': 'F', 'temperatureTrend': None,
            'probabilityOfPrecipitation': {'value': 0 if n == 0 else None, 'unitCode': 'wmoUnit:percent'},
            'relativeHumidity': {'value': 0 if n == 0 else None}, 'dewpoint': {'value': None, 'unitCode': 'wmoUnit:degC'},
            'windSpeed': '5 mph', 'windDirection': 'NE', 'icon': None,
            'shortForecast': 'Sunny', 'detailedForecast': 'Synthetic test forecast'} for n in range(3 if hourly else 2)]}}


def points():
    return {'properties': {'cwa': 'TAE', 'gridX': 1, 'gridY': 2, 'timeZone': 'America/Chicago',
        'forecast': weather.API_ROOT + '/gridpoints/TAE/1,2/forecast',
        'forecastHourly': weather.API_ROOT + '/gridpoints/TAE/1,2/forecast/hourly',
        'forecastGridData': weather.API_ROOT + '/gridpoints/TAE/1,2',
        'forecastZone': weather.API_ROOT + '/zones/forecast/FLZ108',
        'county': weather.API_ROOT + '/zones/county/FLC131',
        'observationStations': weather.API_ROOT + '/gridpoints/TAE/1,2/stations'}}


def alerts(empty=False):
    return {'features': [] if empty else [{'id': 'https://api.weather.gov/alerts/test-id', 'properties': {
        'id': 'test-id', 'event': 'Test Event', 'headline': 'Synthetic alert', 'areaDesc': 'Test area',
        'severity': 'Moderate', 'certainty': 'Likely', 'urgency': 'Expected', 'effective': '2026-09-30T10:00:00-05:00',
        'onset': None, 'expires': '2026-10-01T10:00:00-05:00', 'ends': None, 'status': 'Actual',
        'messageType': 'Alert', 'description': 'Synthetic description', 'instruction': None}}]}


class NWSMock:
    def __init__(self, empty=False):
        self.seen = []
        self.empty = empty
    def __call__(self, request):
        self.seen.append(request)
        assert request.url.host == 'api.weather.gov' and request.url.scheme == 'https'
        assert request.headers['user-agent'] == weather.HEADERS['User-Agent']
        assert request.headers['accept'] == 'application/geo+json'
        if request.url.path.startswith('/points/'):
            data = points()
        elif request.url.path.endswith('/hourly'):
            data = forecast(True)
        elif request.url.path.endswith('/forecast'):
            data = forecast()
        else:
            assert request.url.path == '/alerts/active'
            data = alerts(self.empty)
        return httpx.Response(200, headers={'content-type': 'application/geo+json'}, json=data)


def run_mock(tmp_path, handler=None, canceled=lambda: False):
    with httpx.Client(transport=httpx.MockTransport(handler or NWSMock())) as client:
        return weather.collect(tmp_path / 'source.json', lambda *args: None, canceled, client=client, anchors=ANCHORS)


def install_mock(monkeypatch, handler):
    original = weather.collect
    def collect(path, progress, canceled, *, anchors):
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            return original(path, progress, canceled, client=client, anchors=anchors)
    monkeypatch.setattr(weather, 'collect', collect)


def start(client):
    source = next(s for s in client.get('/api/sources').json() if s['url'] == weather.SOURCE_URL)
    response = client.post('/api/jobs', json={'kind': 'source_collection', 'source_id': source['id']})
    assert response.status_code == 202
    return finished(client, response.json()['id'])


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr(weather, 'RETRY_SECONDS', 0)


def test_anchors_exact_and_registry_metadata(tmp_path):
    assert [(a['anchor_key'], a['latitude'], a['longitude'], a['source_beach_external_id']) for a in ANCHORS] == [
        ('west', 30.35548, -86.2638, '5c81ab02f836f9166348e96c'),
        ('central', 30.3167, -86.12845, '5c81a5acf836f90dc03cccca'),
        ('east', 30.2713, -85.99579, '5c81a6a2f836f9166348e961')]
    assert 'mahalle merkezleri değildir' in ANCHOR_PROVENANCE['scope']
    assert len(DEFAULT_REGISTRY.connectors) == 7
    with TestClient(create_app(tmp_path)) as client:
        for rows in (client.get('/api/sources').json(), client.get('/api/bootstrap').json()['sources']):
            s = next(s for s in rows if s['url'] == weather.SOURCE_URL)
            assert s['connector'] == {'name': 'nws-weather', 'version': 'nws-weather/1', 'method': 'API'}
            beach = next(s for s in rows if s['url'] == beaches.SOURCE_URL)
            assert beach['connector']['method'] == 'JSON'
        assert client.get('/api/health').json()['version'] == '0.8.0'


def test_full_collection_counts_nulls_dedupe_provenance_and_raw(tmp_path):
    handler = NWSMock()
    result = run_mock(tmp_path, handler)
    assert len(handler.seen) == 12
    assert [r.url.path.split('/')[1] for r in handler.seen[:4]] == ['points', 'gridpoints', 'gridpoints', 'alerts']
    assert len(result.records) == 15
    assert result.metadata['anchors'] == 3
    assert result.metadata['forecast_period_count'] == 6 and result.metadata['hourly_period_count'] == 9
    assert result.metadata['alert_count'] == 1
    assert result.source_updated == '2026-09-30T02:00:00-05:00'
    assert result.metadata['source_timestamps']['west']['hourly']['generatedAt'] == '2026-09-30T08:00:00+00:00'
    assert result.records[0]['precipitation_probability'] == 0
    assert result.records[1]['precipitation_probability'] is None
    assert result.records[1]['temperature'] is None
    assert result.records[2]['relative_humidity'] == 0
    assert result.records[3]['relative_humidity'] is None
    assert result.records[2]['dewpoint'] is None and result.records[2]['dewpoint_unit'] == 'wmoUnit:degC'
    assert result.records[0]['start_time'] == '2026-09-30T10:00:00-05:00'
    assert result.related['locations'][0]['time_zone'] == 'America/Chicago'
    assert result.related['alerts'][0]['anchor_keys'] == ['west', 'central', 'east']
    raw = json.loads((tmp_path / 'source.json').read_text(encoding='utf-8'))
    assert len(raw['responses']) == 12
    assert [r['sequence'] for r in raw['responses']] == list(range(1, 13))
    assert all(raw['responses'][0]['anchor'][k]==v for k,v in ANCHORS[0].items())
    assert json.loads(raw['responses'][0]['body']) == points()


def test_empty_alerts_are_success(tmp_path):
    result = run_mock(tmp_path, NWSMock(empty=True))
    assert result.related['alerts'] == [] and result.metadata['alert_count'] == 0


@pytest.mark.parametrize('url', ['https://evil.example/forecast', 'http://api.weather.gov/f',
    'https://user:pass@api.weather.gov/f', 'https://api.weather.gov.evil.example/f',
    'https://api.weather.gov:444/f', 'https://api.weather.gov:bad/f', 'https://[broken/f', None])
def test_response_endpoint_rejected_before_following(tmp_path, url):
    seen = []
    def handler(request):
        seen.append(request)
        data = points(); data['properties']['forecast'] = url
        return httpx.Response(200, headers={'content-type': 'application/geo+json'}, json=data)
    with pytest.raises(SourceError, match='API adresi'):
        run_mock(tmp_path, handler)
    assert len(seen) == 1


@pytest.mark.parametrize('field,bad', [('gridX', '1'), ('cwa', None), ('timeZone', None), ('timeZone', ''), ('forecastHourly', None)])
def test_points_required_fields(field, bad):
    data = points(); data['properties'][field] = bad
    with pytest.raises(SourceError):
        weather.parse_location(data, ANCHORS[0])


@pytest.mark.parametrize('change', ['empty', 'duplicate', 'time', 'naive', 'percent', 'daytime'])
def test_forecast_validation(change):
    data = forecast()
    row = data['properties']['periods'][0]
    if change == 'empty': data['properties']['periods'] = []
    if change == 'duplicate': data['properties']['periods'].append(copy.deepcopy(row))
    if change == 'time': row['endTime'] = row['startTime']
    if change == 'naive': row['startTime'] = '2026-09-30T10:00:00'
    if change == 'percent': row['probabilityOfPrecipitation']['value'] = 101
    if change == 'daytime': row['isDaytime'] = 'yes'
    with pytest.raises(SourceError): weather.parse_forecast(data, 'west', 'period')


@pytest.mark.parametrize('status,mime,content,match', [(200, 'application/json', b'{', 'JSON'),
    (200, 'text/html', b'{}', 'içerik'), (200, 'application/json', b'[]', 'nesne'),
    (429, 'application/json', b'{}', '429'), (403, 'application/json', b'{}', '403')])
def test_http_invalid_response_no_retry(tmp_path, status, mime, content, match):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={'content-type': mime}, content=content)
    with pytest.raises(SourceError, match=match): run_mock(tmp_path, handler)
    assert len(calls) == 1
    assert len(json.loads((tmp_path / 'source.json').read_text(encoding='utf-8'))['responses']) == 1


def test_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(weather, 'MAX_BYTES', 100)
    with pytest.raises(SourceError, match='boyut'):
        run_mock(tmp_path, lambda r: httpx.Response(200, headers={'content-type': 'application/json'}, content=b'x'*101))


@pytest.mark.parametrize('mode', ['timeout', 'network', '5xx'])
def test_bounded_retries(tmp_path, mode):
    calls = []
    def handler(request):
        calls.append(request)
        if mode == 'timeout': raise httpx.ReadTimeout('synthetic')
        if mode == 'network': raise httpx.ConnectError('synthetic')
        return httpx.Response(503)
    with pytest.raises(SourceError): run_mock(tmp_path, handler)
    assert len(calls) == 2


def test_retry_success_and_redirect_safety(tmp_path):
    base = NWSMock(); calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1: return httpx.Response(503)
        if len(calls) == 2: return httpx.Response(301, headers={'location': '/points/30.35548,-86.2638'})
        return base(request)
    assert len(run_mock(tmp_path, handler).records) == 15 and len(calls) == 14
    calls.clear()
    def unsafe(request):
        calls.append(request)
        return httpx.Response(302, headers={'location': 'https://evil.example'})
    with pytest.raises(SourceError): run_mock(tmp_path, unsafe)
    assert len(calls) == 1


def test_redirect_loop_bounded(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={'location': '/loop'})
    with pytest.raises(SourceError, match='yönlendirme sınırı'): run_mock(tmp_path, handler)
    assert len(calls) == 4


def test_cancel_before_and_during_collection(tmp_path):
    handler = NWSMock()
    with pytest.raises(CollectionCanceled): run_mock(tmp_path, handler, lambda: True)
    assert handler.seen == []
    with pytest.raises(CollectionCanceled): run_mock(tmp_path, handler, lambda: len(handler.seen) >= 2)
    assert len(handler.seen) == 2
    assert (tmp_path / 'source.json').is_file()


def test_generic_weather_run_api_raw_hash_and_failure_preserves_previous(tmp_path, monkeypatch):
    handler = NWSMock(); install_mock(monkeypatch, handler)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        job = start(client)
        assert job['status'] == 'done' and job['kind'] == 'source_collection'
        assert client.get('/api/jobs').json()[0]['source_name'] == 'National Weather Service'
        assert job['result']['connector_name'] == 'nws-weather'
        identifier = job['id']
        snapshot = client.get(f'/api/weather-runs/{identifier}').json()
        assert len(snapshot['forecast_periods']) == 6 and len(snapshot['hourly_periods']) == 9
        assert len(snapshot['locations']) == 3 and len(snapshot['alerts']) == 1
        assert len(snapshot['alerts'][0]['anchor_keys']) == 3
        assert snapshot['run']['record_count'] == 15 and snapshot['run']['metadata']['alert_count'] == 1
        assert snapshot['diff']['available'] is False and 'kayan' in snapshot['diff']['reason']
        assert client.get(f'/api/source-runs/{identifier}/diff').json() == snapshot['diff']
        raw = client.get(f'/api/weather-runs/{identifier}/raw')
        assert raw.status_code == 200 and raw.json()['connector'] == 'nws-weather/1'
        assert hashlib.sha256(raw.content).hexdigest() == snapshot['run']['raw_sha256']
        assert (tmp_path / snapshot['run']['raw_path']).read_bytes() == raw.content
        assert client.get('/api/collections').json() == []
        assert client.get(f'/api/collections/{identifier}').status_code == 404
        assert client.get('/api/weather-runs/missing').status_code == 404
        # Partial responses succeed, then a required hourly forecast fails.
        original = handler.__class__.__call__
        def broken(self, request):
            if request.url.path.endswith('/hourly'): return httpx.Response(503)
            return original(self, request)
        monkeypatch.setattr(NWSMock, '__call__', broken)
        failed = start(client)
        assert failed['status'] == 'failed'
        assert len(client.get('/api/weather-runs').json()) == 1
        assert client.get(f'/api/weather-runs/{identifier}').json() == snapshot
        assert client.get(f"/api/weather-runs/{failed['id']}").status_code == 404
        with client.app.state.db.connect() as con:
            assert con.execute('SELECT COUNT(*) FROM weather_locations WHERE run_id=?', (failed['id'],)).fetchone()[0] == 0
            con.execute('UPDATE source_runs SET raw_path=? WHERE id=?', ('../outside.json', identifier))
        assert client.get(f'/api/weather-runs/{identifier}/raw').status_code == 404


def test_domain_transaction_rolls_back(tmp_path, monkeypatch):
    install_mock(monkeypatch, NWSMock())
    class BrokenWeather(weather.WeatherConnector):
        def store_records(self, con, run_id, records, related=None):
            super().store_records(con, run_id, records, related)
            raise RuntimeError('synthetic domain failure')
    with TestClient(create_app(tmp_path, ConnectorRegistry([BrokenWeather()])), headers=HEADERS) as client:
        job = start(client)
        assert job['status'] == 'failed'
        with client.app.state.db.connect() as con:
            for table in ('weather_locations', 'weather_forecast_periods', 'weather_alerts', 'weather_alert_anchors'):
                assert con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
        run = client.app.state.db.source_run(job['id'])
        assert run['record_count'] == 0 and run['raw_sha256']


def make_v3(path):
    make_legacy_db(path)
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('BEGIN IMMEDIATE')
        upgrade_v3(con)
        con.execute("INSERT INTO entities VALUES ('e1','hotel','Test',NULL,NULL,NULL,'now','now')")
        con.execute("INSERT INTO entity_sources(entity_id,source_id,external_id) VALUES ('e1','source-a','external')")


def snapshot_tables(con):
    return {name: [row[:{'sources':12,'jobs':12,'source_runs':17,'regions':2,'entities':8}.get(name,len(row))] for row in con.execute(f'SELECT * FROM {name} ORDER BY rowid').fetchall()] for name in (
        'sources', 'source_history', 'jobs', 'source_runs', 'beach_records', 'regions', 'entities', 'entity_sources')}


def test_v3_migration_preserves_every_table_and_raw_with_backup(tmp_path):
    path = tmp_path / 'studio.sqlite3'; make_v3(path)
    with sqlite3.connect(path) as con: before = snapshot_tables(con)
    raw = (tmp_path / 'raw/old-success/source.html').read_bytes()
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 8
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
        assert without_added_snapshot(snapshot_tables(con)) == before
    backup, = (tmp_path / 'backups').glob('*.sqlite3')
    with sqlite3.connect(backup) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 3
        assert snapshot_tables(con) == before
    assert (tmp_path / 'raw/old-success/source.html').read_bytes() == raw
    Database(path).initialize()
    assert len(list((tmp_path / 'backups').glob('*.sqlite3'))) == 1


@pytest.mark.parametrize('version', [0, 1, 2])
def test_fresh_and_legacy_upgrade_chains(tmp_path, version):
    path = tmp_path / 'studio.sqlite3'
    if version: make_legacy_db(path, version)
    db = Database(path); db.initialize()
    with db.connect() as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 8
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
        for table in ('weather_locations', 'weather_forecast_periods', 'weather_alerts', 'weather_alert_anchors'):
            assert con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
        if version == 2: assert con.execute('SELECT COUNT(*) FROM beach_records').fetchone()[0] == 1


def test_v4_migration_failure_rolls_back(tmp_path, monkeypatch):
    from studio import migrations
    path = tmp_path / 'studio.sqlite3'; make_v3(path)
    original = migrations.execute_schema
    def fail(con, sql):
        original(con, sql)
        raise RuntimeError('synthetic failure')
    monkeypatch.setattr(migrations, 'execute_schema', fail)
    with pytest.raises(RuntimeError): Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 3
        assert con.execute("SELECT name FROM sqlite_master WHERE name='weather_locations'").fetchone() is None
        assert con.execute('SELECT COUNT(*) FROM beach_records').fetchone()[0] == 1



def test_source_updated_uses_source_offsets_and_fallback(tmp_path):
    base = NWSMock()
    count = 0
    def handler(request):
        nonlocal count
        response = base(request)
        if request.url.path.endswith('/forecast'):
            count += 1
            body = forecast()
            body['properties']['updateTime'] = ['2026-09-30T05:00:00-05:00', '2026-09-30T14:00:00+03:00', None][count-1]
            body['properties']['generatedAt'] = '2026-09-30T10:30:00+00:00'
            return httpx.Response(200, headers={'content-type': 'application/geo+json'}, json=body)
        return response
    result = run_mock(tmp_path, handler)
    assert result.source_updated == '2026-09-30T14:00:00+03:00'


def test_missing_source_timestamps_stay_null(tmp_path):
    base = NWSMock()
    def handler(request):
        response = base(request)
        if request.url.path.endswith(('/forecast', '/hourly')):
            body = response.json()
            body['properties']['generatedAt'] = None
            body['properties']['updateTime'] = None
            return httpx.Response(200, headers={'content-type': 'application/geo+json'}, json=body)
        return response
    assert run_mock(tmp_path, handler).source_updated is None


def test_weather_foreign_keys_and_separate_run_history(tmp_path, monkeypatch):
    install_mock(monkeypatch, NWSMock())
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        first = start(client)
        snapshot = client.get(f"/api/weather-runs/{first['id']}").json()
        second = start(client)
        assert [r['id'] for r in client.get('/api/weather-runs').json()] == [second['id'],first['id']]
        assert client.get(f"/api/weather-runs/{first['id']}").json() == snapshot
        with client.app.state.db.connect() as con:
            assert con.execute('PRAGMA foreign_key_check').fetchall() == []
            with pytest.raises(sqlite3.IntegrityError):
                con.execute('INSERT INTO weather_alert_anchors VALUES (?,?,?)', (first['id'], 'missing-alert', 'west'))
            with pytest.raises(sqlite3.IntegrityError):
                con.execute('INSERT INTO weather_alert_anchors VALUES (?,?,?)', (first['id'], 'test-id', 'missing-anchor'))
            with pytest.raises(sqlite3.IntegrityError):
                con.execute("UPDATE weather_forecast_periods SET anchor_key='missing-anchor' WHERE run_id=?", (first['id'],))
