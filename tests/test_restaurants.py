from studio.destinations.thirty_a import ANCHORS, ANCHOR_PROVENANCE
"""Synthetic HTML only; suite-wide no_real_http prevents internet access."""
import copy
import hashlib
import json
import sqlite3
from pathlib import Path
from html import escape
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.catalog import SEEDS
from studio.database import Database
from studio.migrations import upgrade_v4
from studio.sources import restaurants as r, weather
from studio.sources.base import SourceError, CollectionCanceled, CollectionResult
from studio.sources.registry import DEFAULT_REGISTRY
from tests.test_beaches import finished
from tests.test_weather import make_v3, snapshot_tables, NWSMock
from tests.legacy import make_legacy_db, without_added_snapshot

FIXTURES = Path(__file__).parent / 'fixtures/restaurants'
DETAIL = (FIXTURES / 'detail.html').read_text(encoding='utf-8-sig')
MINIMAL = (FIXTURES / 'minimal.html').read_text(encoding='utf-8-sig')
LABELS = [*r.REGION_MAP, *sorted(r.EXCLUDED)]
VALUES = {name: f'opaque-{i}' for i, name in enumerate(LABELS)}


def listing(neighborhood=None, cards=(), pager='', empty=False):
    options = ''.join(f'<option value="{value}" {"selected" if name == neighborhood else ""}>{name}</option>' for name, value in VALUES.items())
    html = (FIXTURES / 'listing.html').read_text(encoding='utf-8-sig')
    return (html.replace('{{NEIGHBORHOODS}}', options).replace('{{BUSINESS_SELECTED}}', 'selected' if neighborhood else '')
            .replace('{{CARDS}}', ''.join(f'<a href="{escape(url)}"><div class="card-inner"><h5>{escape(name)}</h5></div></a>' for url, name in cards))
            .replace('{{EMPTY}}', '<p>No results found.</p>' if empty else '').replace('{{PAGER}}', pager))


def response(html, status=200, headers=None):
    return httpx.Response(status, text=html, headers=headers or {'content-type': 'text/html; charset=UTF-8'})


class DirectoryMock:
    def __init__(self): self.seen = []
    def __call__(self, request):
        self.seen.append(request)
        assert request.url.host in r.HOSTS
        if request.url.path.startswith('/listing/'):
            return response(DETAIL if request.url.path == '/listing/coast-table/' else MINIMAL)
        q = parse_qs(request.url.query.decode())
        if not q: return response(listing())
        assert q['businessType'] == ['restaurants']
        neighborhood = next(name for name, value in VALUES.items() if q['Neighborhood'] == [value])
        assert neighborhood not in r.EXCLUDED
        if neighborhood == 'Dune Allen':
            if q.get('page') == ['2']:
                return response(listing(neighborhood, [('/listing/coast-table/?duplicate=yes#fragment', 'Coast & Table'), ('/listing/minimal/', 'Minimal Cafe')], '<ul class="pager"><li><a href="/listings/culinary-experiences/">1</a></li><li><a class="active" href="?page=2">2</a></li></ul>'))
            # Back-links resolve to the already visited first page; only explicit next loops fail.
            return response(listing(neighborhood, [('/listing/coast-table/', 'Coast & Table')], '<ul class="pager"><li><a class="active" href="/listings/culinary-experiences/">1</a></li><li class="next"><a href="?page=2">Next</a></li></ul>'))
        if neighborhood == 'Gulf Place': return response(listing(neighborhood, [('/listing/coast-table/', 'Coast & Table')]))
        return response(listing(neighborhood, empty=True))


@pytest.fixture(autouse=True)
def no_delay(monkeypatch):
    monkeypatch.setattr(r, 'REQUEST_GAP', 0)
    monkeypatch.setattr(r, 'RETRY_SECONDS', 0)


def run_mock(tmp_path, handler=None, canceled=lambda: False):
    with httpx.Client(transport=httpx.MockTransport(handler or DirectoryMock())) as client:
        return r.collect(tmp_path / 'manifest.json', lambda *args: None, canceled, client=client)


def install_mock(monkeypatch, handler):
    original = r.collect
    def collect(path, progress, canceled, *, regions=None):
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            return original(path, progress, canceled, client=client, regions=regions)
    monkeypatch.setattr(r, 'collect', collect)


def start(client):
    source = next(s for s in client.get('/api/sources').json() if s['url'] == r.SOURCE_URL)
    response = client.post('/api/jobs', json={'kind': 'source_collection', 'source_id': source['id']}, headers={'X-Studio-Request': '1'})
    assert response.status_code == 202
    return finished(client, response.json()['id'])


def make_v4(path):
    make_v3(path)
    with sqlite3.connect(path) as con:
        con.execute('BEGIN IMMEDIATE'); upgrade_v4(con)


def test_registry_and_fresh_seed(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        data = client.get('/api/bootstrap').json()
        source = next(s for s in data['sources'] if s['url'] == r.SOURCE_URL)
        assert source['method'] == 'HTML'
        assert 'Menü ve fiyat' in source['notes']
        assert source['connector'] == {'name': r.RestaurantsConnector.name, 'version': r.RestaurantsConnector.version, 'method': 'HTML'}
        assert DEFAULT_REGISTRY.for_source(source).diff_enabled
        assert data['restaurant_runs'] == []
        with client.app.state.db.connect() as con:
            assert con.execute('PRAGMA user_version').fetchone()[0] == 10


@pytest.mark.parametrize('version', [1, 2, 3, 4])
def test_upgrade_chain(tmp_path, version):
    path = tmp_path / 'studio.sqlite3'
    if version == 4: make_v4(path)
    elif version == 3: make_v3(path)
    else: make_legacy_db(path, version)
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 10
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
        assert con.execute('SELECT COUNT(*) FROM restaurant_records').fetchone()[0] == 0
        assert con.execute('SELECT COUNT(*) FROM restaurant_regions').fetchone()[0] == 0
    backup, = (tmp_path / 'backups').glob('*.sqlite3')
    with sqlite3.connect(backup) as con: assert con.execute('PRAGMA user_version').fetchone()[0] == version


OLD_NOTE = 'Restoran dizini. Menü ve fiyatlar için işletmelerin kendi sayfaları ayrıca incelenecek.'
@pytest.mark.parametrize('method,note,url,expected_method,changed', [
    ('Belirlenecek', OLD_NOTE, r.SOURCE_URL, 'HTML', True),
    ('API', OLD_NOTE, r.SOURCE_URL, 'API', True),
    ('Belirlenecek', 'My note', r.SOURCE_URL, 'HTML', False),
    ('JSON', 'My note', r.SOURCE_URL, 'JSON', False),
    ('Belirlenecek', OLD_NOTE+' ', r.SOURCE_URL, 'HTML', False),
    ('Belirlenecek', OLD_NOTE, r.SOURCE_URL+'other/', 'Belirlenecek', False),
])
def test_seed_updates_are_exact_and_independent(tmp_path, method, note, url, expected_method, changed):
    path = tmp_path / 'studio.sqlite3'; make_v4(path)
    with sqlite3.connect(path) as con:
        con.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', ('food','My source',url,'Yeme içme','Tüm 30A',method,'Aylık',note,0,7,'before','before'))
        before = con.execute("SELECT * FROM sources WHERE id='food'").fetchone()
    db = Database(path); db.initialize()
    after = db.source('food')
    assert after['method'] == expected_method
    expected_note=next(seed[3] for seed in SEEDS if seed[1]==r.SOURCE_URL) if changed else note
    assert after['notes']==expected_note
    assert (after['name'],after['version'],after['enabled'],after['updated_at']) == ('My source',7,0,'before')
    backup, = (tmp_path / 'backups').glob('*.sqlite3')
    with sqlite3.connect(backup) as con: assert con.execute("SELECT * FROM sources WHERE id='food'").fetchone() == before


def test_v4_preserves_beach_weather_entities_and_raw(tmp_path):
    path = tmp_path / 'studio.sqlite3'; make_v4(path)
    db = Database(path)
    # Seed a weather run using the existing generic transaction, before upgrading to v5.
    with db.connect() as con:
        con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", ('nws','NWS',weather.SOURCE_URL,'Hava','Tüm 30A','API','Haftalık','Weather',1,1,'now','now'))
    source = db.source('nws'); connector = weather.WeatherConnector()
    identifier='weather-before-upgrade'
    with db.connect() as con:
        con.execute("INSERT INTO jobs(id,kind,title,status,created_at,source_id) VALUES (?,'source_collection','Weather snapshot','queued','now',?)",(identifier,source['id']))
        con.execute("INSERT INTO source_runs(id,source_id,job_id,status,connector_name,connector_version) VALUES (?,?,?,'queued',?,?)",(identifier,source['id'],identifier,connector.name,connector.version))
    with httpx.Client(transport=httpx.MockTransport(NWSMock())) as client:
        batch = weather.collect(tmp_path/'weather.json',lambda *args:None,lambda:False,client=client,anchors=ANCHORS)
    db.record_raw_artifact(identifier,tmp_path/'weather.json')
    db.complete_source_run(identifier,batch,connector)
    tables = ('weather_locations','weather_forecast_periods','weather_alerts','weather_alert_anchors')
    def snapshot(con): return {**snapshot_tables(con), **{t:con.execute(f'SELECT * FROM {t} ORDER BY rowid').fetchall() for t in tables}}
    with sqlite3.connect(path) as con: before = snapshot(con)
    raw = {str(p.relative_to(tmp_path)):p.read_bytes() for p in tmp_path.rglob('*.html')}
    weather_raw = (tmp_path/'weather.json').read_bytes()
    db.initialize()
    with sqlite3.connect(path) as con: assert without_added_snapshot(snapshot(con)) == before
    backup, = (tmp_path/'backups').glob('*.sqlite3')
    with sqlite3.connect(backup) as con: assert snapshot(con) == before
    assert all((tmp_path/name).read_bytes() == body for name,body in raw.items())
    assert (tmp_path/'weather.json').read_bytes() == weather_raw
    db.initialize(); assert len(list((tmp_path/'backups').glob('*.sqlite3'))) == 1


def test_migration_failure_rolls_back(tmp_path, monkeypatch):
    from studio import migrations
    path=tmp_path/'studio.sqlite3';make_v4(path)
    original=migrations.execute_schema
    def fail(con,sql): original(con,sql);raise RuntimeError('failure after DDL')
    monkeypatch.setattr(migrations,'execute_schema',fail)
    with pytest.raises(RuntimeError): Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 4
        assert con.execute("SELECT name FROM sqlite_master WHERE name='restaurant_records'").fetchone() is None
        assert con.execute('SELECT COUNT(*) FROM beach_records').fetchone()[0] == 1


def test_filters_identity_pagination_and_details():
    filters = r.parse_filters(listing())
    assert len(r.REGION_MAP) == 13 and len(filters['neighborhoods']) == 16
    assert filters['business']['value'] == 'restaurants'
    assert filters['neighborhood_param'] == 'Neighborhood' and filters['business_param'] == 'businessType'
    cards,pages,next_pages=r.parse_listing(listing('Dune Allen',[('/listing/coast-table/?x=1#f','Coast & Table')],'<ul class="pager"><li class="next"><a href="?page=2">Next</a></li></ul>'),r.SOURCE_URL,filters,'Dune Allen')
    assert cards[0]['external_id'] == '/listing/coast-table/'
    assert len(pages)==1 and next_pages==pages and 'businessType=restaurants' in pages[0]
    record=r.parse_detail(DETAIL,cards[0]['listing_url'],['Gulf Place','Dune Allen','Dune Allen'])
    assert record['name']=='Coast & Table' and record['description']=='Fresh & local. Lunch by the coast.'
    assert [record[k] for k in ('address_line_1','address_line_2','city','state','postal_code')]==['10 Coast Lane','Suite 2','Santa Rosa Beach','FL','32459']
    assert record['phone']=='(850) 555-0100' and record['email']=='Hello@example.org'
    assert record['website_url']=='https://restaurant.example/menu'
    assert record['cuisines']==['American','Seafood'] and record['meals_served']==['Dinner','Lunch']
    assert record['amenities']==['Outdoor Seating','Private Dining Capacity: 24','Private Dining Spaces']
    assert record['regions']==[{'source_neighborhood':n,'canonical_region_id':r.REGION_MAP[n]} for n in ['Dune Allen','Gulf Place']]


def test_optional_fields_null():
    record=r.parse_detail(MINIMAL,'/listing/minimal/',['Seaside'])
    assert all(record[k] is None for k in ('address_line_1','address_line_2','city','state','postal_code','phone','email','website_url'))
    assert record['amenities']==record['cuisines']==record['meals_served']==[]


@pytest.mark.parametrize('html', [listing().replace('Restaurants','No restaurants'),listing().replace('Dune Allen','Unknown'),listing().replace('name="Neighborhood"',''),listing().replace('method="get"','method="post"'),'<html>changed</html>'])
def test_filter_structure_changes_fail(html):
    with pytest.raises(SourceError):r.parse_filters(html)


@pytest.mark.parametrize('html', [DETAIL.replace('id="listing-hero"','id="changed"'),DETAIL.replace('class="details"','class="changed"'),DETAIL.replace('<h1>Coast &amp; Table</h1>','<h1></h1>')])
def test_detail_structure_changes_fail(html):
    with pytest.raises(SourceError):r.parse_detail(html,'/listing/coast-table/',['Seaside'])


def test_unapplied_filter_fails():
    with pytest.raises(SourceError,match='uygulamadı'):r.parse_listing(listing(),r.SOURCE_URL,r.parse_filters(listing()),'Dune Allen')


def test_pagination_loop_and_conflicting_id(tmp_path):
    base=DirectoryMock()
    def loop(req):
        if 'Neighborhood' in str(req.url):return response(listing('Dune Allen',[('/listing/coast-table/','Coast & Table')],'<ul class="pager"><li class="next"><a href="/listings/culinary-experiences/">Next</a></li></ul>'))
        return base(req)
    with pytest.raises(SourceError,match='döngü'):run_mock(tmp_path,loop)
    def conflict(req):
        if 'Neighborhood' in str(req.url):return response(listing('Dune Allen',[('/listing/coast-table/','One'),('/listing/coast-table/?dup=1','Another')]))
        return base(req)
    with pytest.raises(SourceError,match='farklı adlarla'):run_mock(tmp_path,conflict)


def test_collect_dedup_relations_raw_hashes_and_no_external_fetch(tmp_path):
    mock=DirectoryMock(); batch=run_mock(tmp_path,mock)
    assert len(batch.records)==2 and batch.source_updated is None
    assert batch.metadata['target_neighborhood_count']==13
    assert batch.metadata['listing_page_count']==14 and batch.metadata['duplicate_count']==2
    assert batch.metadata['neighborhood_counts']['Dune Allen']==2
    assert set(batch.metadata['neighborhood_counts']).isdisjoint(r.EXCLUDED)
    assert len([req for req in mock.seen if req.url.path.startswith('/listing/')])==2
    manifest=json.loads((tmp_path/'manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['responses'])==17
    for i,entry in enumerate(manifest['responses'],1):
        assert entry['sequence']==i and entry['status']==200
        assert hashlib.sha256((tmp_path/entry['raw_file']).read_bytes()).hexdigest()==entry['raw_sha256']
        assert entry['requested_url'].startswith('https://www.visitsouthwalton.com/')
    assert len(batch.records[0]['regions'])==2


@pytest.mark.parametrize('url', ['http://www.visitsouthwalton.com/','https://evil.example/','https://www.visitsouthwalton.com.evil.example/','https://user@www.visitsouthwalton.com/','https://www.visitsouthwalton.com:444/','https://www.visitsouthwalton.com\\@evil.example/'])
def test_unsafe_redirect_rejected_before_follow(tmp_path,url):
    seen=[]
    def handler(req):seen.append(req);return httpx.Response(302,headers={'location':url})
    with pytest.raises(SourceError):run_mock(tmp_path,handler)
    assert len(seen)==1


@pytest.mark.parametrize('status,content_type,match', [(429,'text/html','429'),(403,'text/html','403'),(200,'application/json','HTML')])
def test_http_failure(tmp_path,status,content_type,match):
    with pytest.raises(SourceError,match=match):run_mock(tmp_path,lambda req:response('{}',status,{'content-type':content_type}))


def test_response_size_and_redirect_limits(tmp_path,monkeypatch):
    monkeypatch.setattr(r,'MAX_BYTES',10)
    with pytest.raises(SourceError,match='boyut'):run_mock(tmp_path,lambda req:response('a'*11))
    calls=[]
    def handler(req):calls.append(req);return httpx.Response(302,headers={'location':r.SOURCE_URL})
    with pytest.raises(SourceError,match='yönlendirme sınırı'):run_mock(tmp_path,handler)
    assert len(calls)==4


@pytest.mark.parametrize('failure', ['500','timeout','network'])
def test_retry_once(tmp_path,failure):
    calls=[];base=DirectoryMock()
    def handler(req):
        calls.append(req)
        if len(calls)==1:
            if failure=='500':return response('temporary',500)
            raise (httpx.ReadTimeout if failure=='timeout' else httpx.ConnectError)('synthetic')
        return base(req)
    assert len(run_mock(tmp_path,handler).records)==2
    assert calls[0].url==calls[1].url


@pytest.mark.parametrize('failure', ['500','timeout'])
def test_retry_exhausted(tmp_path,failure):
    calls=[]
    def handler(req):
        calls.append(req)
        if failure=='500':return response('failed',500)
        raise httpx.ReadTimeout('synthetic')
    with pytest.raises(SourceError):run_mock(tmp_path,handler)
    assert len(calls)==2


def test_cancellation_and_bounds(tmp_path,monkeypatch):
    with pytest.raises(CollectionCanceled):run_mock(tmp_path,canceled=lambda:True)
    monkeypatch.setattr(r,'MAX_PAGES',1)
    with pytest.raises(SourceError,match='sayfalama üst'):run_mock(tmp_path)
    monkeypatch.setattr(r,'MAX_PAGES',100);monkeypatch.setattr(r,'MAX_DETAILS',1)
    with pytest.raises(SourceError,match='detay üst'):run_mock(tmp_path)


def test_api_raw_hash_rollback_and_previous_run(tmp_path,monkeypatch):
    mock=DirectoryMock();install_mock(monkeypatch,mock)
    with TestClient(create_app(tmp_path)) as client:
        job=start(client);assert job['status']=='done'
        identifier=job['id']; db=client.app.state.db
        result=client.get('/api/restaurant-runs/'+identifier).json()
        assert len(result['records'])==2 and result['run']['source_updated'] is None
        assert client.get('/api/restaurant-runs').json()[0]['id']==identifier
        raw=client.get(f'/api/restaurant-runs/{identifier}/raw')
        assert hashlib.sha256(raw.content).hexdigest()==result['run']['raw_sha256']
        assert client.get('/api/restaurant-runs/missing').status_code==404
        assert client.get('/api/weather-runs/'+identifier).status_code==404
        # Fail after records/relations have actually been inserted inside the transaction.
        original=r.RestaurantsConnector.store_records
        def fail(self,con,run_id,records,related=None):
            original(self,con,run_id,records,related);raise RuntimeError('synthetic after insert')
        monkeypatch.setattr(r.RestaurantsConnector,'store_records',fail)
        failed=start(client);assert failed['status']=='failed'
        assert client.get('/api/restaurant-runs/'+failed['id']).status_code==404
        assert client.get('/api/restaurant-runs/'+identifier).json()==result
        with db.connect() as con:
            for table in ('restaurant_records','restaurant_regions'):
                assert con.execute(f'SELECT COUNT(*) FROM {table} WHERE run_id=?',(failed['id'],)).fetchone()[0]==0
            private=tmp_path/'private/manifest.json';private.parent.mkdir();private.write_text('private',encoding='utf-8')
            con.execute('UPDATE source_runs SET raw_path=? WHERE id=?',('private/manifest.json',identifier))
        assert client.get(f'/api/restaurant-runs/{identifier}/raw').status_code==404
        # Even another run's valid manifest is outside this run's raw directory.
        with db.connect() as con:con.execute('UPDATE source_runs SET raw_path=? WHERE id=?',(f'raw/{failed["id"]}/manifest.json',identifier))
        assert client.get(f'/api/restaurant-runs/{identifier}/raw').status_code==404


def test_detail_failure_publishes_nothing(tmp_path,monkeypatch):
    base=DirectoryMock()
    def handler(req):
        return response('<html>changed</html>') if req.url.path=='/listing/minimal/' else base(req)
    install_mock(monkeypatch,handler)
    with TestClient(create_app(tmp_path)) as client:
        job=start(client);assert job['status']=='failed'
        with client.app.state.db.connect() as con:
            for t in ('restaurant_records','restaurant_regions'):assert con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]==0


def test_diff_all_categories_and_order_insensitivity(tmp_path):
    db=Database(tmp_path/'studio.sqlite3');db.initialize();connector=r.RestaurantsConnector()
    source=next(s for s in db.sources() if s['url']==r.SOURCE_URL)
    base=r.parse_detail(DETAIL,'/listing/base/',['Gulf Place','Dune Allen'])
    def record(slug):return {**copy.deepcopy(base),'external_id':f'/listing/{slug}/','listing_url':r.checked_url(f'/listing/{slug}/')}
    def save(records):
        identifier=db.add_job('source_collection','Restaurants',source_id=source['id'],connector=connector)
        db.complete_source_run(identifier,CollectionResult(records,len(records),0,None,{}),connector)
        return identifier
    save([record('same'),record('change'),record('remove')])
    same=record('same')
    for field in ('regions','cuisines','meals_served','amenities'):same[field].reverse()
    changed=record('change');changed['phone']='New phone'
    current=save([same,changed,record('add')]);diff=db.run_diff(current)
    assert {k:diff[k] for k in ('added','removed','changed','unchanged')}==dict(added=1,removed=1,changed=1,unchanged=1)
    assert not diff['connector_version_changed']
    changed['regions']=changed['regions'][:1]
    assert connector.comparison_value(changed)!=connector.comparison_value(record('change'))


def test_schema_json_and_relation_constraints(tmp_path):
    db=Database(tmp_path/'studio.sqlite3');db.initialize();connector=r.RestaurantsConnector()
    source=next(s for s in db.sources() if s['url']==r.SOURCE_URL)
    identifier=db.add_job('source_collection','Restaurants',source_id=source['id'],connector=connector)
    record=r.parse_detail(DETAIL,'/listing/base/',['Dune Allen'])
    with db.connect() as con:
        connector.store_records(con,identifier,[record])
        with pytest.raises(sqlite3.IntegrityError):con.execute("UPDATE restaurant_records SET cuisines='broken'")
        with pytest.raises(sqlite3.IntegrityError):con.execute("UPDATE restaurant_records SET cuisines='{}'")
        with pytest.raises(sqlite3.IntegrityError):con.execute("UPDATE restaurant_regions SET canonical_region_id='unknown'")
        with pytest.raises(sqlite3.IntegrityError):con.execute("UPDATE restaurant_regions SET external_id='/listing/missing/'")

def test_discovered_query_names_are_not_hardcoded(tmp_path):
    base=DirectoryMock()
    def handler(req):
        # Translate only inside the synthetic server; connector must send discovered names.
        query=dict(req.url.params)
        if query:
            assert 'hood' in query and 'kind' in query
            query['Neighborhood']=query.pop('hood');query['businessType']=query.pop('kind')
        translated=httpx.Request('GET',req.url.copy_with(query=str(httpx.QueryParams(query)).encode()))
        result=base(translated)
        return response(result.text.replace('name="Neighborhood"','name="hood"').replace('name="businessType"','name="kind"'))
    assert len(run_mock(tmp_path,handler).records)==2


def test_blank_restaurants_value_and_wrong_pagination_filter_fail():
    with pytest.raises(SourceError,match='filtre değeri'):
        r.parse_filters(listing().replace('value="restaurants"','value=""'))
    filters=r.parse_filters(listing())
    content=listing('Dune Allen',[('/listing/coast-table/','Coast & Table')],'<ul class="pager"><li><a href="?businessType=catering">Next</a></li></ul>')
    with pytest.raises(SourceError,match='filtresini değiştirdi'):r.parse_listing(content,r.SOURCE_URL,filters,'Dune Allen')


def test_apex_redirect_is_followed_without_rewriting_host(tmp_path):
    calls=[];base=DirectoryMock()
    def handler(req):
        calls.append(req)
        if len(calls)==1:return httpx.Response(302,headers={'location':r.SOURCE_URL.replace('www.','')})
        return base(req)
    assert len(run_mock(tmp_path,handler).records)==2
    assert calls[1].url.host=='visitsouthwalton.com'


def test_cancel_during_response_and_detail_identity_change(tmp_path):
    canceled=False
    def handler(req):
        nonlocal canceled
        canceled=True
        return response(listing())
    with pytest.raises(CollectionCanceled):run_mock(tmp_path,handler,lambda:canceled)
    base=DirectoryMock()
    def redirected(req):
        if req.url.path=='/listing/coast-table/':return httpx.Response(302,headers={'location':'/listing/minimal/'})
        return base(req)
    with pytest.raises(SourceError,match='kimliğini değiştirdi'):run_mock(tmp_path,redirected)


def test_duplicate_detail_name_conflict_and_invalid_website(tmp_path):
    base=DirectoryMock()
    def handler(req):
        result=base(req)
        return response(result.text.replace('<h1>Coast &amp; Table</h1>','<h1>Wrong business</h1>'))
    with pytest.raises(SourceError,match='adı uyuşmuyor'):run_mock(tmp_path,handler)
    with pytest.raises(SourceError,match='web sitesi'):
        r.parse_detail(DETAIL.replace('https://restaurant.example/menu','javascript:alert(1)'),'/listing/coast-table/',['Dune Allen'])


def test_description_block_spacing_and_entities():
    html=DETAIL.replace('Fresh &amp; local. <p>Lunch by the coast.</p>','<p>First &amp; fresh.</p><p>Second paragraph.</p>')
    assert r.parse_detail(html,'/listing/coast-table/',['Dune Allen'])['description']=='First & fresh. Second paragraph.'

def test_multiple_selected_filters_and_missing_card_structure_fail():
    filters=r.parse_filters(listing())
    content=listing('Dune Allen',[('/listing/coast-table/','Coast & Table')])
    with pytest.raises(SourceError,match='uygulamadı'):
        r.parse_listing(content.replace('value="catering"','value="catering" selected'),r.SOURCE_URL,filters,'Dune Allen')
    with pytest.raises(SourceError,match='yapısı değişti'):
        r.parse_listing(listing('Dune Allen',empty=True).replace('card-deck','changed'),r.SOURCE_URL,filters,'Dune Allen')

DESCRIPTION_BLOCK = '<div class="description"><h5>Description</h5>Fresh &amp; local. <p>Lunch by the coast.</p></div>'

@pytest.mark.parametrize('replacement', ['', '<div class="description"><h5>Description</h5> \n &nbsp; <p> </p></div>'])
def test_missing_or_blank_description_is_none(replacement):
    html = DETAIL.replace(DESCRIPTION_BLOCK, replacement)
    html = '<meta name="description" content="Generic tourism text">' + html
    record = r.parse_detail(html, '/listing/coast-table/', ['Dune Allen'])
    assert record['description'] is None
    assert record['name'] == 'Coast & Table'
    assert record['phone'] == '(850) 555-0100'


def test_ambiguous_description_fails():
    with pytest.raises(SourceError, match='birden fazla'):
        r.parse_detail(DETAIL.replace(DESCRIPTION_BLOCK, DESCRIPTION_BLOCK * 2), '/listing/coast-table/', ['Dune Allen'])


@pytest.mark.parametrize('broken', ['hero', 'name', 'details'])
def test_missing_description_does_not_relax_required_structure(broken):
    html = DETAIL.replace(DESCRIPTION_BLOCK, '')
    if broken == 'hero': html = html.replace('id="listing-hero"', 'id="changed"')
    elif broken == 'name': html = html.replace('<h1>Coast &amp; Table</h1>', '<h1> </h1>')
    else: html = html.replace('class="details"', 'class="changed"')
    with pytest.raises(SourceError): r.parse_detail(html, '/listing/coast-table/', ['Dune Allen'])


@pytest.mark.parametrize('initial_schema', [0, 4])
def test_nullable_description_published_to_db_api_and_metadata(tmp_path, monkeypatch, initial_schema):
    path = tmp_path / 'studio.sqlite3'
    if initial_schema:
        make_v4(path)
        with sqlite3.connect(path) as con:
            con.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (
                'food', 'South Walton · Restoranlar', r.SOURCE_URL, 'Yeme içme', 'Tüm 30A',
                'Belirlenecek', 'Haftalık', OLD_NOTE, 1, 1, 'before', 'before'))
    base = DirectoryMock()
    def handler(req):
        result = base(req)
        return response(result.text.replace(DESCRIPTION_BLOCK, ''))
    install_mock(monkeypatch, handler)
    with TestClient(create_app(tmp_path)) as client:
        job = start(client)
        assert job['status'] == 'done'
        snapshot = client.get('/api/restaurant-runs/' + job['id']).json()
        records = {rec['external_id']: rec for rec in snapshot['records']}
        assert records['/listing/coast-table/']['description'] is None
        assert records['/listing/minimal/']['description'] == 'A small cafe.'
        assert snapshot['run']['metadata']['description_missing_count'] == 1
        assert snapshot['run']['record_count'] == 2
        with client.app.state.db.connect() as con:
            assert con.execute('PRAGMA user_version').fetchone()[0] == 10
            description_column = next(row for row in con.execute('PRAGMA table_info(restaurant_records)') if row['name'] == 'description')
            assert description_column['notnull'] == 0
            assert con.execute('SELECT COUNT(*) FROM restaurant_records WHERE run_id=? AND description IS NULL', (job['id'],)).fetchone()[0] == 1
            assert con.execute("SELECT COUNT(*) FROM restaurant_records WHERE description='' ").fetchone()[0] == 0


def test_description_missing_count_zero_when_complete(tmp_path):
    assert run_mock(tmp_path).metadata['description_missing_count'] == 0


def test_description_null_transitions_are_diff_changes(tmp_path):
    db = Database(tmp_path / 'studio.sqlite3'); db.initialize()
    connector = r.RestaurantsConnector()
    source = next(s for s in db.sources() if s['url'] == r.SOURCE_URL)
    record = r.parse_detail(DETAIL, '/listing/coast-table/', ['Dune Allen'])
    def save(description):
        identifier = db.add_job('source_collection', 'Restaurants', source_id=source['id'], connector=connector)
        db.complete_source_run(identifier, CollectionResult([{**record, 'description': description}], 1, 0, None, {}), connector)
        return identifier
    save(None)
    for description in ('New source description', None):
        diff = db.run_diff(save(description))
        assert diff['changed'] == 1 and diff['unchanged'] == 0
        assert diff['added'] == diff['removed'] == 0
    assert db.run_diff(save(None))['unchanged'] == 1
