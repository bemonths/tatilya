import json
import sqlite3
import hashlib

import httpx
import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Database, Conflict
from studio.destinations.thirty_a import ANCHORS
from studio.sources import beaches, neighborhoods, restaurants, weather
from studio.sources.registry import DEFAULT_REGISTRY
from studio.migrations import upgrade_v5
from tests.test_restaurants import make_v4
from tests.test_studio import payload
from tests.test_beaches import HEADERS, finished
from tests.test_weather import NWSMock


def add_destination(db, identifier='test-coast', enabled=1):
    with db.connect() as con:
        con.execute('INSERT INTO destinations VALUES (?,?,?, ?,1,?,?)',
                    (identifier,identifier,'Synthetic tests only',enabled,'old','old'))
        con.execute('INSERT INTO regions VALUES (?,?,?,0)',(identifier+'-downtown','Downtown',identifier))
        con.execute('INSERT INTO destination_weather_anchors VALUES (?,?,?,?,?,?,?,0,1)',
                    (identifier,'test-point','Test point',38.3,-122.3,None,None))


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path),headers=HEADERS) as client:
        add_destination(client.app.state.db)
        add_destination(client.app.state.db,'third-coast')
        add_destination(client.app.state.db,'disabled-coast',0)
        yield client


def test_fresh_profile_and_scoped_unique_constraints(client):
    db=client.app.state.db
    assert len(db.sources())==15
    assert len(db.context().canonical_regions)==13 and len(db.context().weather_anchors)==3
    assert db.context().destination['name']=='30A'
    with db.connect() as con:
        assert con.execute('PRAGMA user_version').fetchone()[0]==17
        assert not con.execute('PRAGMA foreign_key_check').fetchall()
        con.execute("INSERT INTO regions VALUES ('30a-downtown','Downtown','30a',99)")
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO regions VALUES ('duplicate','Downtown','test-coast',1)")
        con.execute("INSERT INTO entities VALUES ('a','place','Shared name',NULL,NULL,NULL,'old','old','30a')")
        con.execute("INSERT INTO entities VALUES ('b','place','Shared name',NULL,NULL,NULL,'old','old','test-coast')")
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("UPDATE entities SET canonical_region_id='seaside' WHERE id='b'")
    for destination in ('test-coast','third-coast'):
        result=client.post('/api/sources',json=payload(destination_id=destination,url=weather.SOURCE_URL,region='Downtown'))
        assert result.status_code==201,result.text
        assert result.json()['scope_region_id']==destination+'-downtown'
        assert client.post('/api/sources',json=payload(destination_id=destination,url=weather.SOURCE_URL)).status_code==409


@pytest.mark.parametrize('endpoint',['bootstrap','sources','jobs','collections','source-runs','weather-runs','restaurant-runs','neighborhood-runs','beach-neighborhoods','events'])
@pytest.mark.parametrize('destination',['missing','disabled-coast'])
def test_unknown_or_disabled_is_not_silent_default(client,endpoint,destination):
    assert client.get(f'/api/{endpoint}?destination_id={destination}').status_code==404


def test_source_crud_context_required_immutable_and_region_scope(client):
    data=payload();data.pop('destination_id')
    assert client.post('/api/sources',json=data).status_code==422
    assert client.post('/api/sources',json=payload(destination_id='test-coast',scope_region_id='seaside')).status_code==409
    source=client.post('/api/sources',json=payload(destination_id='test-coast',region='Downtown')).json()
    assert source['scope_region_id']=='test-coast-downtown'
    body=payload(destination_id='30a',expected_version=1)
    assert client.put('/api/sources/'+source['id'],json=body).status_code==409
    body=payload(destination_id='test-coast',expected_version=1,enabled=False,notes='keep my notes',region='Unknown custom place')
    archived=client.put('/api/sources/'+source['id'],json=body).json()
    assert archived['destination_id']=='test-coast' and not archived['enabled']
    assert archived['scope_region_id'] is None and archived['region']=='Unknown custom place'
    assert all(s['id']!=source['id'] for s in client.get('/api/sources').json())
    assert client.get('/api/sources?destination_id=test-coast').json()[0]['id']==source['id']


def test_bootstrap_lists_audit_and_job_constraints_isolated(client):
    db=client.app.state.db
    source=db.save_source(payload(destination_id='test-coast'))
    job=finished(client,client.post('/api/jobs',json={'destination_id':'test-coast'}).json()['id'])
    assert job['destination_id']=='test-coast'
    assert job['result']['checked']==1 and job['result']['findings'][0]['source_id']==source['id']
    data=client.get('/api/bootstrap?destination_id=test-coast').json()
    assert data['selected_destination']['id']=='test-coast'
    assert len(data['sources'])==1 and len(data['jobs'])==1
    assert [r['name'] for r in data['canonical_regions']]==['Downtown']
    assert data['collections']==data['restaurant_runs']==data['weather_runs']==data['neighborhood_runs']==[]
    assert all(j['id']!=job['id'] for j in client.get('/api/jobs').json())
    a=db.add_job(destination_id='30a');b=db.add_job(destination_id='test-coast')
    assert a!=b
    with pytest.raises(Conflict): db.add_job(destination_id='test-coast')
    db.update_job(a,status='done');db.update_job(b,status='done')


@pytest.mark.parametrize('module,connector',[(beaches,beaches.BeachesConnector()),(restaurants,restaurants.RestaurantsConnector()),(neighborhoods,neighborhoods.NeighborhoodsConnector())])
def test_specific_connector_never_binds_other_destination(client,module,connector):
    assert connector.supports({'url':module.SOURCE_URL,'destination_id':'30a'})
    assert not connector.supports({'url':module.SOURCE_URL,'destination_id':'test-coast'})
    assert not connector.supports({'url':module.SOURCE_URL})
    source=client.post('/api/sources',json=payload(destination_id='test-coast',url=module.SOURCE_URL)).json()
    row=client.get('/api/sources?destination_id=test-coast').json()[0]
    assert row['connector'] is None
    assert client.post('/api/jobs',json={'kind':'source_collection','source_id':source['id']}).status_code==409


def test_generic_nws_uses_each_destinations_db_anchors(client,tmp_path,monkeypatch):
    db=client.app.state.db
    observed={}
    original=weather.collect
    def collect(path,progress,canceled,*,anchors):
        requests=[]
        mock=NWSMock()
        def handler(req):
            requests.append(str(req.url));return mock(req)
        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            result=original(path,progress,canceled,anchors=anchors,client=transport)
        observed[anchors[0]['label']]=requests
        return result
    monkeypatch.setattr(weather,'collect',collect)
    runs=[]
    for destination in ('30a','test-coast'):
        source=next((s for s in db.sources(destination) if s['url']==weather.SOURCE_URL),None)
        source=source or db.save_source(payload(destination_id=destination,url=weather.SOURCE_URL))
        assert DEFAULT_REGISTRY.for_source(source).name=='nws-weather'
        response=client.post('/api/jobs',json={'kind':'source_collection','source_id':source['id'],'destination_id':destination})
        job=finished(client,response.json()['id']);assert job['status']=='done',job
        run=db.source_run(job['id']);assert run['destination_id']==destination
        runs.append(run)
        raw=client.get('/api/weather-runs/'+run['id']+'/raw')
        assert raw.status_code==200 and hashlib.sha256(raw.content).hexdigest()==run['raw_sha256']
        assert [r['id'] for r in client.get('/api/weather-runs?destination_id='+destination).json()]==[run['id']]
        assert [r['id'] for r in client.get('/api/source-runs?destination_id='+destination).json()]==[run['id']]
        assert client.get('/api/weather-runs/'+run['id']).json()['run']['destination_id']==destination
    assert any('/points/38.3,-122.3' in url for url in observed['Test point'])
    assert all('/points/30.' not in url for url in observed['Test point'])
    assert len([u for u in observed['Batı 30A'] if '/points/' in u])==3
    assert all('/points/38.' not in u for u in observed['Batı 30A'])


def test_empty_weather_configuration_fails_without_http(client,monkeypatch,tmp_path):
    db=client.app.state.db
    with db.connect() as con: con.execute("UPDATE destination_weather_anchors SET enabled=0 WHERE destination_id='test-coast'")
    with pytest.raises(weather.SourceError,match='örnek noktası'):
        weather.WeatherConnector().collect({'destination_id':'test-coast'},tmp_path/'raw.json',lambda *args:None,lambda:False,context=db.context('test-coast'))


def test_diff_does_not_compare_another_destination_even_same_source(client):
    db=client.app.state.db
    source=next(s for s in db.sources() if s['url']==beaches.SOURCE_URL)
    connector=beaches.BeachesConnector()
    before=db.add_job('source_collection','Before',source['id'],connector)
    db.update_job(before,status='done')
    # Simulate historical provenance belonging elsewhere; IDs alone are insufficient.
    with db.connect() as con: con.execute("UPDATE source_runs SET destination_id='test-coast' WHERE id=?",(before,))
    after=db.add_job('source_collection','After',source['id'],connector)
    db.update_job(after,status='done')
    assert db.run_diff(after)['previous_run_id'] is None


def make_v5(path):
    make_v4(path)
    with sqlite3.connect(path) as con:
        con.row_factory=sqlite3.Row;con.execute('BEGIN IMMEDIATE');upgrade_v5(con)


def test_v5_migration_preserves_old_fields_backup_and_rollback(tmp_path,monkeypatch):
    from studio import database
    path=tmp_path/'studio.sqlite3';make_v5(path)
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO sources VALUES ('archived','Manual','https://manual.example/','Genel','Seaside','API','Aylık','My custom notes',0,9,'old','old')")
        con.execute("INSERT INTO source_history(source_id,saved_at,snapshot) VALUES ('archived','old','{}')")
        before=con.execute("SELECT * FROM sources WHERE id='archived'").fetchone()
        con.execute("INSERT INTO entities VALUES ('entity','place','Downtown','seaside',NULL,NULL,'old','old')")
    original=database.upgrade_v6
    def fail(con):original(con);raise RuntimeError('after all DDL')
    with monkeypatch.context() as m:
        m.setattr(database,'upgrade_v6',fail)
        with pytest.raises(RuntimeError): Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0]==5
        assert con.execute("SELECT * FROM sources WHERE id='archived'").fetchone()==before
        assert not con.execute("SELECT name FROM sqlite_master WHERE name='destinations'").fetchall()
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0]==17
        row=con.execute("SELECT * FROM sources WHERE id='archived'").fetchone()
        assert row[:len(before)]==before and row[-2:]==('30a','seaside')
        assert con.execute("SELECT destination_id FROM entities WHERE id='entity'").fetchone()[0]=='30a'
        assert con.execute('SELECT COUNT(*) FROM source_history WHERE source_id="archived"').fetchone()[0]==1
        assert not con.execute('PRAGMA foreign_key_check').fetchall()
        assert {r[0] for r in con.execute('SELECT DISTINCT destination_id FROM jobs')}=={'30a'}
        assert {r[0] for r in con.execute('SELECT DISTINCT destination_id FROM source_runs')}=={'30a'}
        assert con.execute('SELECT COUNT(*) FROM destination_weather_anchors').fetchone()[0]==3
    for backup in (tmp_path/'backups').glob('*.sqlite3'):
        with sqlite3.connect(backup) as con: assert con.execute('PRAGMA user_version').fetchone()[0]==5
