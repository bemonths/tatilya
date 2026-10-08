"""Synthetic HTML only; suite-wide no_real_http prevents internet access."""
import copy
import hashlib
import json
import sqlite3
from html import escape
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Database
from studio.destinations.thirty_a import NEIGHBORHOOD_EXCLUDED, REGIONS, SEEDS
from studio.migration_v6 import upgrade_v6
from studio.sources import neighborhoods as n
from studio.sources.base import CollectionCanceled, CollectionResult, SourceError
from studio.sources.registry import DEFAULT_REGISTRY
from tests.test_beaches import HEADERS, finished
from tests.test_destinations import add_destination, make_v5
from tests.test_studio import payload
from tests.legacy import ADDED_SOURCE_URLS, V8_TABLES, V10_TABLES

FIXTURES = Path(__file__).parent / 'fixtures/neighborhoods'
INDEX = (FIXTURES / 'index.html').read_text(encoding='utf-8')
PAGE = (FIXTURES / 'page.html').read_text(encoding='utf-8')
CANONICAL = [{'id': identifier, 'name': name} for identifier, name in REGIONS]
INTRO = '<div class="copious"><h3>Synthetic short line.</h3><br /><p class="p1"><span class="s1">{name} first synthetic paragraph &amp; more.</span></p>\n<p class="p1">Second synthetic paragraph.</p></div>'


def location(index, name, **changes):
    item = {'id': f'{0x5bc000 + index:024x}', 'name': name, 'permalink': name.lower().replace(' ', '-'),
            'description': f'Synthetic summary for {name}.', 'modified': f'2025-0{1 + index % 9}-01T10:00:00+0000',
            'lat': f'{30.36 - index * 0.006:.6f}', 'lng': f'{-86.30 + index * 0.022:.6f}', 'image': '/userfiles/synthetic.jpg',
            'Activity': [{'object': {'name': tag, 'icon': '/img/synthetic.svg'}, 'properties': []}
                         for tag in (['Walkable', 'Family'] if index % 2 else ['Tranquil'])]}
    return {**item, **changes}


def directory():
    """16 records in a non-geographic order: 13 canonical neighborhoods plus 3 out of scope."""
    canonical = [location(i, name) for i, (_, name) in enumerate(REGIONS)]
    excluded = [location(20 + i, name, lng=f'{-86.40 + i * 0.01:.6f}') for i, name in enumerate(NEIGHBORHOOD_EXCLUDED)]
    return [*canonical[7:], excluded[0], *canonical[:7][::-1], *excluded[1:]]


def index_html(items=None):
    return INDEX.replace('{{LOCATIONS}}', json.dumps(directory() if items is None else items))


def page_html(name, copy=None):
    return PAGE.replace('{{NAME}}', escape(name)).replace('{{COPY}}', INTRO.format(name=escape(name)) if copy is None else copy)


def response(html, status=200, headers=None):
    return httpx.Response(status, text=html, headers=headers or {'content-type': 'text/html; charset=UTF-8'})


class SiteMock:
    def __init__(self, items=None, pages=None):
        self.items = directory() if items is None else items
        self.pages = {} if pages is None else pages
        self.seen = []

    def __call__(self, request):
        self.seen.append(request)
        assert request.url.host in n.HOSTS and request.url.scheme == 'https'
        if request.url.path == '/neighborhoods/':
            return response(index_html(self.items))
        slug = request.url.path.removeprefix('/neighborhoods/').strip('/')
        item = next(item for item in self.items if item['permalink'] == slug)
        assert item['name'] not in NEIGHBORHOOD_EXCLUDED
        return response(self.pages.get(item['name'], page_html(item['name'])))


@pytest.fixture(autouse=True)
def no_delay(monkeypatch):
    monkeypatch.setattr(n, 'REQUEST_GAP', 0)
    monkeypatch.setattr(n, 'RETRY_SECONDS', 0)


def run_mock(tmp_path, handler=None, canceled=lambda: False, regions=CANONICAL):
    with httpx.Client(transport=httpx.MockTransport(handler or SiteMock())) as client:
        return n.collect(tmp_path / 'manifest.json', lambda *args: None, canceled, client=client, regions=regions)


def install_mock(monkeypatch, handler):
    original = n.collect
    def collect(path, progress, canceled, *, regions=None):
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            return original(path, progress, canceled, client=client, regions=regions)
    monkeypatch.setattr(n, 'collect', collect)


def start(client):
    source = next(s for s in client.get('/api/sources').json() if s['url'] == n.SOURCE_URL)
    result = client.post('/api/jobs', json={'kind': 'source_collection', 'source_id': source['id']}, headers=HEADERS)
    assert result.status_code == 202, result.text
    return finished(client, result.json()['id'])


def make_v6(path):
    make_v5(path)
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        con.execute('BEGIN IMMEDIATE'); upgrade_v6(con)


# --- Directory and page parsing ---------------------------------------------------------------

def test_sixteen_records_select_thirteen_and_exclude_three(tmp_path):
    mock = SiteMock(); batch = run_mock(tmp_path, mock)
    assert batch.total_count == 16 and batch.excluded_count == 3 and len(batch.records) == 13
    assert [record['canonical_region_id'] for record in batch.records] == [identifier for identifier, _ in REGIONS]
    assert batch.metadata['excluded_neighborhoods'] == sorted(NEIGHBORHOOD_EXCLUDED)
    assert batch.metadata['unknown_neighborhoods'] == [] and batch.metadata['alias_matches'] == {}
    assert batch.metadata['source_record_count'] == 16 and batch.metadata['page_count'] == 13
    assert batch.metadata['target_neighborhood_count'] == 13 and batch.metadata['tag_count'] == 3
    assert batch.metadata['page_intro_missing_count'] == 0
    # Excluded neighborhoods are never fetched; one directory request plus one page per target.
    assert len(mock.seen) == 14
    assert all(request.url.path.strip('/').split('/')[-1] not in ('miramar-beach', 'seascape', 'sandestin') for request in mock.seen)
    assert batch.source_updated == max(record['source_modified'] for record in batch.records)
    record = batch.records[0]
    assert record['external_id'] == f'{0x5bc000:024x}' and record['name'] == 'Dune Allen'
    assert record['page_url'] == 'https://www.visitsouthwalton.com/neighborhoods/dune-allen/'
    assert record['latitude'] == 30.36 and record['longitude'] == -86.3
    assert record['tags'] == ['Tranquil'] and record['summary'] == 'Synthetic summary for Dune Allen.'
    assert record['page_intro'] == 'Dune Allen first synthetic paragraph & more.\n\nSecond synthetic paragraph.'


def test_raw_manifest_keeps_every_response_with_hashes(tmp_path):
    run_mock(tmp_path)
    manifest = json.loads((tmp_path / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['connector'] == n.CONNECTOR_VERSION and manifest['source_url'] == n.SOURCE_URL
    assert len(manifest['responses']) == 14
    assert [entry['request_kind'] for entry in manifest['responses']] == ['index', *['page'] * 13]
    for i, entry in enumerate(manifest['responses'], 1):
        assert entry['sequence'] == i and entry['status'] == 200
        assert entry['requested_url'].startswith('https://www.visitsouthwalton.com/neighborhoods/')
        assert hashlib.sha256((tmp_path / entry['raw_file']).read_bytes()).hexdigest() == entry['raw_sha256']


def test_missing_target_neighborhood_fails_run(tmp_path):
    items = [item for item in directory() if item['name'] != 'Seacrest']
    with pytest.raises(SourceError, match='Seacrest'):
        run_mock(tmp_path, SiteMock(items))


@pytest.mark.parametrize('content', [
    INDEX.replace('{{LOCATIONS}}', '[{"id": "broken"'),
    INDEX.replace('{{LOCATIONS}}', '{"not": "a list"}'),
    INDEX.replace('{{LOCATIONS}}', '[]'),
    INDEX.replace('var locations', 'var places').replace('{{LOCATIONS}}', '[]'),
    INDEX.replace('{{LOCATIONS}}', '[];\n\tvar locations = []'),
])
def test_broken_or_ambiguous_directory_json_fails(content):
    with pytest.raises(SourceError):
        n.parse_index(content)


def test_broken_json_fails_collection_and_publishes_nothing(tmp_path, monkeypatch):
    install_mock(monkeypatch, lambda request: response(INDEX.replace('{{LOCATIONS}}', '[{"id": ')))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        job = start(client)
        assert job['status'] == 'failed' and 'okunamadı' in job['message']
        assert client.get('/api/neighborhood-runs').json() == []
        assert (tmp_path / 'raw' / job['id'] / 'manifest.json').is_file()


def test_duplicate_source_id_fails():
    items = directory(); items[1] = {**items[1], 'id': items[0]['id']}
    with pytest.raises(SourceError, match='yinelenen kaynak kimliği'):
        n.parse_index(index_html(items))


@pytest.mark.parametrize('field,value', [
    ('id', 'NOT-HEX'), ('id', None), ('name', ' '), ('permalink', '../escape'), ('permalink', 'Upper'),
    ('lat', 'north'), ('lat', '45.0'), ('lng', None), ('lng', 'NaN'), ('description', 7), ('modified', ['x']),
    ('Activity', {'object': 'x'}), ('Activity', [{'object': None}]), ('Activity', [{'object': {'name': ''}}]),
])
def test_invalid_record_fields_fail(field, value):
    items = directory(); items[0] = {**items[0], field: value}
    with pytest.raises(SourceError):
        n.parse_index(index_html(items))


def test_optional_summary_modified_and_tags_stay_null_or_empty():
    items = directory()
    items[0] = {**items[0], 'description': None, 'modified': None, 'Activity': None}
    items[1] = {**items[1], 'description': '   '}
    entries = {entry['name']: entry for entry in n.parse_index(index_html(items))}
    assert entries[items[0]['name']]['summary'] is None and entries[items[0]['name']]['source_modified'] is None
    assert entries[items[0]['name']]['tags'] == []
    assert entries[items[1]['name']]['summary'] is None


def test_page_without_intro_text_is_null(tmp_path):
    batch = run_mock(tmp_path, SiteMock(pages={'Seaside': page_html('Seaside', copy=''),
                                               'Grayton Beach': page_html('Grayton Beach', copy='<div class="copious"><h3>Only a heading.</h3></div>')}))
    records = {record['name']: record for record in batch.records}
    assert records['Seaside']['page_intro'] is None and records['Grayton Beach']['page_intro'] is None
    assert batch.metadata['page_intro_missing_count'] == 2
    assert records['Seagrove']['page_intro'] is not None


def test_intro_without_paragraph_tags_keeps_loose_text_but_not_heading():
    html = page_html('Seaside', copy='<div class="copious"><h3>Heading line.</h3>Loose  synthetic <b>text</b>.</div>')
    assert n.parse_page(html, 'Seaside') == 'Loose synthetic text .'


@pytest.mark.parametrize('html,match', [
    (page_html('Seaside').replace('id="neighborhood-hero"', 'id="changed"'), 'yapısı'),
    (page_html('Seaside').replace('<span>Seaside</span>', ''), 'ad bulunamadı'),
    (page_html('Seagrove'), 'uyuşmuyor'),
    (page_html('Seaside', copy=INTRO.format(name='Seaside') * 2), 'birden fazla'),
])
def test_page_structure_and_identity_changes_fail(html, match):
    with pytest.raises(SourceError, match=match):
        n.parse_page(html, 'Seaside')


def test_alias_spelling_links_to_canonical_region(tmp_path):
    items = [{**item, 'name': 'Watercolor'} if item['name'] == 'WaterColor' else item for item in directory()]
    batch = run_mock(tmp_path, SiteMock(items))
    record = next(record for record in batch.records if record['canonical_region_id'] == 'watercolor')
    assert record['name'] == 'Watercolor'
    assert batch.metadata['alias_matches'] == {'Watercolor': 'WaterColor'}


def test_two_source_records_for_one_neighborhood_fail():
    entries = n.parse_index(index_html([*directory(), location(40, 'Blue Mountain')]))
    with pytest.raises(SourceError, match='aynı kanonik mahalleye'):
        n.select_targets(entries, CANONICAL)


def test_unknown_extra_neighborhood_is_out_of_scope_and_reported(tmp_path):
    batch = run_mock(tmp_path, SiteMock([*directory(), location(41, 'Synthetic Harbor')]))
    assert len(batch.records) == 13 and batch.excluded_count == 4
    assert batch.metadata['unknown_neighborhoods'] == ['Synthetic Harbor']
    assert 'Synthetic Harbor' in batch.metadata['excluded_neighborhoods']


def test_names_are_never_inferred_from_coordinates_or_permalink(tmp_path):
    # A record with a canonical-looking permalink and point but a different name is not linked.
    items = [{**item, 'name': 'Seaside Village'} if item['name'] == 'Seaside' else item for item in directory()]
    with pytest.raises(SourceError, match='Seaside'):
        run_mock(tmp_path, SiteMock(items))


# --- HTTP safety ---------------------------------------------------------------------------------

@pytest.mark.parametrize('url', ['http://www.visitsouthwalton.com/neighborhoods/', 'https://evil.example/', 'https://www.visitsouthwalton.com.evil.example/',
                                 'https://user@www.visitsouthwalton.com/', 'https://www.visitsouthwalton.com:444/', 'https://www.visitsouthwalton.com\\@evil.example/'])
def test_unsafe_redirect_rejected_before_follow(tmp_path, url):
    seen = []
    def handler(request): seen.append(request); return httpx.Response(302, headers={'location': url})
    with pytest.raises(SourceError): run_mock(tmp_path, handler)
    assert len(seen) == 1


@pytest.mark.parametrize('status,content_type,match', [(429, 'text/html', '429'), (404, 'text/html', '404'), (200, 'application/json', 'HTML')])
def test_http_failure(tmp_path, status, content_type, match):
    with pytest.raises(SourceError, match=match): run_mock(tmp_path, lambda request: response('{}', status, {'content-type': content_type}))


def test_response_size_and_redirect_limits(tmp_path, monkeypatch):
    monkeypatch.setattr(n, 'MAX_BYTES', 10)
    with pytest.raises(SourceError, match='boyut'): run_mock(tmp_path, lambda request: response('a' * 11))
    calls = []
    def handler(request): calls.append(request); return httpx.Response(302, headers={'location': n.SOURCE_URL})
    monkeypatch.setattr(n, 'MAX_BYTES', 5_000_000)
    with pytest.raises(SourceError, match='yönlendirme sınırı'): run_mock(tmp_path, handler)
    assert len(calls) == 4


def test_record_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(n, 'MAX_RECORDS', 15)
    with pytest.raises(SourceError, match='fazla kayıt'): run_mock(tmp_path)


@pytest.mark.parametrize('failure', ['500', 'timeout', 'network'])
def test_retry_once(tmp_path, failure):
    calls = []; base = SiteMock()
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            if failure == '500': return response('temporary', 500)
            raise (httpx.ReadTimeout if failure == 'timeout' else httpx.ConnectError)('synthetic')
        return base(request)
    assert len(run_mock(tmp_path, handler).records) == 13
    assert calls[0].url == calls[1].url


@pytest.mark.parametrize('failure', ['500', 'timeout'])
def test_retry_exhausted(tmp_path, failure):
    calls = []
    def handler(request):
        calls.append(request)
        if failure == '500': return response('failed', 500)
        raise httpx.ReadTimeout('synthetic')
    with pytest.raises(SourceError): run_mock(tmp_path, handler)
    assert len(calls) == 2


def test_apex_redirect_followed_but_page_identity_change_fails(tmp_path):
    calls = []; base = SiteMock()
    def apex(request):
        calls.append(request)
        if len(calls) == 1: return httpx.Response(301, headers={'location': n.SOURCE_URL.replace('www.', '')})
        return base(request)
    assert len(run_mock(tmp_path, apex).records) == 13
    assert calls[1].url.host == 'visitsouthwalton.com'
    def moved(request):
        if request.url.path == '/neighborhoods/seaside/': return httpx.Response(302, headers={'location': '/neighborhoods/seagrove/'})
        return base(request)
    with pytest.raises(SourceError, match='kimliğini değiştirdi'): run_mock(tmp_path, moved)
    def moved_index(request):
        if request.url.path == '/neighborhoods/': return httpx.Response(302, headers={'location': '/beach-bay-access-locations/'})
        return response(index_html())
    with pytest.raises(SourceError, match='başka bir sayfaya'): run_mock(tmp_path, moved_index)


def test_cancel_before_start_and_during_page_reads(tmp_path):
    with pytest.raises(CollectionCanceled): run_mock(tmp_path, canceled=lambda: True)
    base = SiteMock(); pages = 0
    def handler(request):
        nonlocal pages
        pages += request.url.path != '/neighborhoods/'
        return base(request)
    with pytest.raises(CollectionCanceled): run_mock(tmp_path, handler, canceled=lambda: pages >= 3)
    assert pages == 3


def test_empty_region_configuration_fails_without_http(tmp_path):
    def handler(request): pytest.fail('İstek yapılmamalı')
    with pytest.raises(SourceError, match='boş'): run_mock(tmp_path, handler, regions=[])


# --- Database, API and diff ----------------------------------------------------------------------

def test_fresh_seed_binds_connector_and_bootstrap(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        data = client.get('/api/bootstrap').json()
        source = next(s for s in data['sources'] if s['url'] == n.SOURCE_URL)
        assert source['method'] == 'HTML' and source['category'] == 'Genel' and source['destination_id'] == '30a'
        assert 'videoda aynen kullanılmaz' in source['notes']
        assert source['connector'] == {'name': n.NeighborhoodsConnector.name, 'version': n.CONNECTOR_VERSION, 'method': 'HTML'}
        assert data['neighborhood_runs'] == []
        assert data['neighborhood_connector']['name'] == 'south-walton-neighborhoods'
        assert 'temsilî noktası' in data['neighborhood_connector']['scope']
        assert DEFAULT_REGISTRY.for_source(source).diff_enabled
        with client.app.state.db.connect() as con:
            assert con.execute('PRAGMA user_version').fetchone()[0] == 11
            assert con.execute('SELECT COUNT(*) FROM sources WHERE url=?', (n.SOURCE_URL,)).fetchone()[0] == 1


def test_api_records_west_to_east_raw_download_and_rollback(tmp_path, monkeypatch):
    install_mock(monkeypatch, SiteMock())
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        job = start(client); assert job['status'] == 'done', job
        assert job['result']['connector_name'] == 'south-walton-neighborhoods'
        identifier = job['id']; db = client.app.state.db
        result = client.get('/api/neighborhood-runs/' + identifier).json()
        records = result['records']
        assert len(records) == 13 and [r['canonical_region_id'] for r in records] == [i for i, _ in REGIONS]
        assert [r['longitude'] for r in records] == sorted(r['longitude'] for r in records)
        assert records[5]['canonical_region_name'] == 'WaterColor' and records[0]['tags'] == ['Tranquil']
        assert result['run']['record_count'] == 13 and result['run']['excluded_count'] == 3
        assert result['run']['metadata']['total_count'] == 16
        assert result['diff'] == {'available': False, 'previous_run_id': None, 'reason': 'Önceki başarılı sürüm yok.'}
        assert [run['id'] for run in client.get('/api/neighborhood-runs').json()] == [identifier]
        raw = client.get(f'/api/neighborhood-runs/{identifier}/raw')
        assert raw.status_code == 200 and hashlib.sha256(raw.content).hexdigest() == result['run']['raw_sha256']
        assert client.get('/api/neighborhood-runs/missing').status_code == 404
        assert client.get('/api/restaurant-runs/' + identifier).status_code == 404
        # Failure after records are inserted inside the transaction publishes nothing.
        original = n.NeighborhoodsConnector.store_records
        def fail(self, con, run_id, records, related=None):
            original(self, con, run_id, records, related); raise RuntimeError('synthetic after insert')
        monkeypatch.setattr(n.NeighborhoodsConnector, 'store_records', fail)
        failed = start(client); assert failed['status'] == 'failed'
        assert client.get('/api/neighborhood-runs/' + failed['id']).status_code == 404
        assert client.get('/api/neighborhood-runs/' + identifier).json() == result
        with db.connect() as con:
            assert con.execute('SELECT COUNT(*) FROM neighborhood_records WHERE run_id=?', (failed['id'],)).fetchone()[0] == 0
            assert con.execute('SELECT COUNT(*) FROM neighborhood_records').fetchone()[0] == 13
            private = tmp_path / 'private/manifest.json'; private.parent.mkdir(); private.write_text('private', encoding='utf-8')
            con.execute('UPDATE source_runs SET raw_path=? WHERE id=?', ('private/manifest.json', identifier))
        assert client.get(f'/api/neighborhood-runs/{identifier}/raw').status_code == 404
        with db.connect() as con: con.execute('UPDATE source_runs SET raw_path=? WHERE id=?', (f'raw/{failed["id"]}/manifest.json', identifier))
        assert client.get(f'/api/neighborhood-runs/{identifier}/raw').status_code == 404


def test_failed_page_and_canceled_job_keep_previous_version(tmp_path, monkeypatch):
    pages = {}
    install_mock(monkeypatch, SiteMock(pages=pages))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        good = start(client); assert good['status'] == 'done'
        pages['Seaside'] = '<html>changed</html>'
        failed = start(client); assert failed['status'] == 'failed' and 'yapısı' in failed['message']
        with client.app.state.db.connect() as con:
            assert con.execute('SELECT COUNT(*) FROM neighborhood_records').fetchone()[0] == 13
        assert [run['id'] for run in client.get('/api/neighborhood-runs').json()] == [good['id']]


def test_null_intro_published_as_null(tmp_path, monkeypatch):
    install_mock(monkeypatch, SiteMock(pages={'Seaside': page_html('Seaside', copy='')}))
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        job = start(client); assert job['status'] == 'done'
        snapshot = client.get('/api/neighborhood-runs/' + job['id']).json()
        records = {record['name']: record for record in snapshot['records']}
        assert records['Seaside']['page_intro'] is None and records['Seagrove']['page_intro']
        assert snapshot['run']['metadata']['page_intro_missing_count'] == 1
        with client.app.state.db.connect() as con:
            assert con.execute("SELECT COUNT(*) FROM neighborhood_records WHERE page_intro IS NULL").fetchone()[0] == 1
            assert con.execute("SELECT COUNT(*) FROM neighborhood_records WHERE page_intro=''").fetchone()[0] == 0


def test_cancel_job_through_api_publishes_nothing(tmp_path, monkeypatch):
    import threading
    release = threading.Event(); entered = threading.Event(); base = SiteMock()
    def handler(request):
        if request.url.path != '/neighborhoods/':
            entered.set(); release.wait(30)
        return base(request)
    install_mock(monkeypatch, handler)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        source = next(s for s in client.get('/api/sources').json() if s['url'] == n.SOURCE_URL)
        identifier = client.post('/api/jobs', json={'kind': 'source_collection', 'source_id': source['id']}).json()['id']
        try:
            assert entered.wait(30)
            assert client.post(f'/api/jobs/{identifier}/cancel').json()['status'] == 'canceled'
        finally:
            release.set()
        job = finished(client, identifier)
        assert job['status'] == 'canceled'
        assert client.get('/api/neighborhood-runs').json() == []
        with client.app.state.db.connect() as con:
            assert con.execute('SELECT COUNT(*) FROM neighborhood_records').fetchone()[0] == 0


def save_run(db, records, connector=None):
    connector = connector or n.NeighborhoodsConnector()
    source = next(s for s in db.sources() if s['url'] == n.SOURCE_URL)
    identifier = db.add_job('source_collection', 'Neighborhoods', source_id=source['id'], connector=connector)
    db.complete_source_run(identifier, CollectionResult(records, len(records), 0, None, {}), connector)
    return identifier


def test_diff_by_neighborhood_id_ignores_modified_stamp_and_tag_order(tmp_path):
    db = Database(tmp_path / 'studio.sqlite3'); db.initialize()
    base = run_mock(tmp_path).records
    save_run(db, base[:12])
    after = copy.deepcopy(base[1:])
    after[0]['source_modified'] = '2030-01-01T00:00:00+0000'  # CMS stamp only: unchanged
    assert after[1]['tags'] == ['Tranquil']
    after[1]['tags'] = ['Family', 'Tranquil']                 # new source tag: changed
    assert len(after[2]['tags']) == 2
    after[2]['tags'] = list(reversed(after[2]['tags']))        # order only: unchanged
    after[3]['page_intro'] = None                             # intro disappeared: changed
    diff = db.run_diff(save_run(db, after))
    assert {k: diff[k] for k in ('added', 'removed', 'changed', 'unchanged')} == {
        'added': 1, 'removed': 1, 'changed': 2, 'unchanged': 9}
    assert not diff['connector_version_changed']


def test_diff_reports_connector_version_change(tmp_path):
    db = Database(tmp_path / 'studio.sqlite3'); db.initialize()
    records = run_mock(tmp_path).records
    save_run(db, records)
    class Next(n.NeighborhoodsConnector): version = 'south-walton-neighborhoods/2'
    diff = db.run_diff(save_run(db, records, Next()))
    assert diff['connector_version_changed'] and diff['unchanged'] == 13


def test_schema_constraints(tmp_path):
    db = Database(tmp_path / 'studio.sqlite3'); db.initialize()
    connector = n.NeighborhoodsConnector(); records = run_mock(tmp_path).records
    identifier = save_run(db, records)
    with db.connect() as con:
        for statement in ("UPDATE neighborhood_records SET tags='broken'", "UPDATE neighborhood_records SET tags='{}'",
                          "UPDATE neighborhood_records SET canonical_region_id='unknown'",
                          "UPDATE neighborhood_records SET latitude=95", "UPDATE neighborhood_records SET run_id='missing'"):
            with pytest.raises(sqlite3.IntegrityError): con.execute(statement)
        with pytest.raises(sqlite3.IntegrityError):
            connector.store_records(con, identifier, [{**records[0], 'external_id': 'f' * 24}])
        columns = {row['name']: row['notnull'] for row in con.execute('PRAGMA table_info(neighborhood_records)')}
        assert columns['summary'] == columns['page_intro'] == columns['source_modified'] == 0


# --- Migration and destination isolation ----------------------------------------------------------

def test_v6_to_v7_migration_adds_table_and_source_with_backup(tmp_path):
    path = tmp_path / 'studio.sqlite3'; make_v6(path)
    with sqlite3.connect(path) as con:
        tables_before = {row[0]: con.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0]
                         for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        sources_before = con.execute('SELECT * FROM sources ORDER BY rowid').fetchall()
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        # The upgrade chain continues to v8 (climate) and v10 (lodging); v7's own additions are checked here.
        assert con.execute('PRAGMA user_version').fetchone()[0] == 11
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
        tables_after = {row[0]: con.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0]
                        for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert tables_after == {**tables_before, 'neighborhood_records': 0, **V8_TABLES, **V10_TABLES,
                                'sources': tables_before['sources'] + len(ADDED_SOURCE_URLS)}
        sources_after = con.execute('SELECT * FROM sources ORDER BY rowid').fetchall()
        assert sources_after[:len(sources_before)] == sources_before
        name, url, category, notes, method = next(seed for seed in SEEDS if seed[1] == n.SOURCE_URL)
        added = next(row for row in sources_after if row[2] == n.SOURCE_URL)
        assert added[1:10] == (name, url, category, 'Tüm 30A', method, 'Haftalık', notes, 1, 1)
        assert added[12:] == ('30a', None)
    backup, = (tmp_path / 'backups').glob('*.sqlite3')
    with sqlite3.connect(backup) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 6
        assert con.execute('SELECT * FROM sources ORDER BY rowid').fetchall() == sources_before
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM sources WHERE url=?', (n.SOURCE_URL,)).fetchone()[0] == 1
    assert len(list((tmp_path / 'backups').glob('*.sqlite3'))) == 1


def test_v6_to_v7_failure_rolls_back_everything(tmp_path, monkeypatch):
    from studio import database
    path = tmp_path / 'studio.sqlite3'; make_v6(path)
    with sqlite3.connect(path) as con:
        before = {table: con.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall() for table in ('sources', 'jobs', 'source_runs', 'beach_records')}
    original = database.upgrade_v7
    def fail(con): original(con); raise RuntimeError('after all DDL and source insert')
    with monkeypatch.context() as m:
        m.setattr(database, 'upgrade_v7', fail)
        with pytest.raises(RuntimeError): Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 6
        assert con.execute("SELECT name FROM sqlite_master WHERE name='neighborhood_records'").fetchone() is None
        assert {table: con.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall() for table in before} == before
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 11
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []


@pytest.mark.parametrize('url,enabled', [(n.SOURCE_URL, 0), ('https://visitsouthwalton.com/neighborhoods', 1)])
def test_v7_never_duplicates_an_existing_neighborhood_source(tmp_path, url, enabled):
    path = tmp_path / 'studio.sqlite3'; make_v6(path)
    with sqlite3.connect(path) as con:
        con.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            'mine', 'My neighborhoods', url, 'Genel', 'Seaside', 'Belirlenecek', 'Aylık', 'My notes', enabled, 3, 'old', 'old', '30a', 'seaside'))
        before = con.execute("SELECT * FROM sources WHERE id='mine'").fetchone()
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        rows = con.execute("SELECT * FROM sources WHERE url LIKE '%/neighborhoods%'").fetchall()
        assert rows == [before]


def test_connector_never_binds_other_destination(tmp_path):
    connector = n.NeighborhoodsConnector()
    assert connector.supports({'url': n.SOURCE_URL, 'destination_id': '30a'})
    assert connector.supports({'url': 'https://visitsouthwalton.com/neighborhoods', 'destination_id': '30a'})
    for source in ({'url': n.SOURCE_URL, 'destination_id': 'test-coast'}, {'url': n.SOURCE_URL},
                   {'url': n.SOURCE_URL + 'seaside/', 'destination_id': '30a'}, {'url': 'http://www.visitsouthwalton.com/neighborhoods/', 'destination_id': '30a'}):
        assert not connector.supports(source)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        add_destination(db)
        created = client.post('/api/sources', json=payload(destination_id='test-coast', url=n.SOURCE_URL)).json()
        assert client.get('/api/sources?destination_id=test-coast').json()[0]['connector'] is None
        assert client.post('/api/jobs', json={'kind': 'source_collection', 'source_id': created['id']}).status_code == 409
        assert client.get('/api/neighborhood-runs?destination_id=test-coast').json() == []
        assert client.get('/api/bootstrap?destination_id=test-coast').json()['neighborhood_runs'] == []
        assert client.get('/api/neighborhood-runs?destination_id=missing').status_code == 404


def test_runs_listed_only_for_their_destination(tmp_path, monkeypatch):
    install_mock(monkeypatch, SiteMock())
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        db = client.app.state.db
        add_destination(db)
        job = start(client); assert job['status'] == 'done'
        assert [run['id'] for run in client.get('/api/neighborhood-runs?destination_id=30a').json()] == [job['id']]
        assert client.get('/api/neighborhood-runs?destination_id=test-coast').json() == []
        # A run moved to another destination never becomes this destination's diff baseline.
        with db.connect() as con: con.execute("UPDATE source_runs SET destination_id='test-coast' WHERE id=?", (job['id'],))
        second = start(client); assert second['status'] == 'done'
        assert db.run_diff(second['id'])['previous_run_id'] is None
