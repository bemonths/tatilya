"""Existing schema-5 source binding and non-destructive startup repair."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.connector_defaults import OLD_RESTAURANT_NOTE, RESTAURANT_NOTE
from studio.database import Database
from studio.sources import restaurants as r, beaches, weather
from studio.sources.registry import DEFAULT_REGISTRY
from studio.sources.url_identity import https_source_identity
from tests.test_beaches import finished
from tests.test_restaurants import DirectoryMock, install_mock, make_v4

VARIANTS = [f'https://{host}/listings/culinary-experiences{slash}'
            for host in ('www.visitsouthwalton.com', 'visitsouthwalton.com') for slash in ('/', '')]
UNSAFE = [
    r.SOURCE_URL+'?page=1', r.SOURCE_URL+'?', r.SOURCE_URL+'#section', r.SOURCE_URL+'#',
    r.SOURCE_URL.replace('https:', 'http:'), r.SOURCE_URL.replace('www.visitsouthwalton.com', 'example.org'),
    r.SOURCE_URL.replace('www.visitsouthwalton.com', 'www.visitsouthwalton.com.evil.example'),
    r.SOURCE_URL.replace('https://', 'https://user:password@'),
    r.SOURCE_URL.replace('https://', 'https://@'),
    r.SOURCE_URL.replace('.com/', '.com:444/'), r.SOURCE_URL.replace('.com/', '.com:invalid/'),
    r.SOURCE_URL.replace('.com/', '.com:/'), r.SOURCE_URL+'extra',
    r.SOURCE_URL.replace('/listings/', '/other/../listings/'),
    r.SOURCE_URL.replace('/listings/', '//listings/'),
    r.SOURCE_URL.replace('culinary', '%63ulinary'),
    r.SOURCE_URL.replace('https://', 'https://evil.example\\@'),
    '\n'+r.SOURCE_URL, r.SOURCE_URL.replace('www.', 'www.\t'), 'https://[broken/', '', None,
]


@pytest.mark.parametrize('url', VARIANTS + [r.SOURCE_URL.replace('.com/', '.com:443/'), r.SOURCE_URL.replace('https://www.', 'HTTPS://WWW.')])
def test_restaurant_source_variants_bind(url):
    connector = DEFAULT_REGISTRY.for_source({'destination_id':'30a','url': url})
    assert connector.name == 'south-walton-restaurants'
    assert connector.version == 'south-walton-restaurants/2'
    assert connector.method == 'HTML'


@pytest.mark.parametrize('url', UNSAFE)
def test_unsafe_or_different_source_identity_is_rejected(url):
    assert not r.RestaurantsConnector().supports({'destination_id':'30a','url': url})


def test_identity_helper_accepts_only_explicit_aliases_and_preserves_other_connectors():
    aliases = {'directory.example': 'directory.example', 'www.directory.example': 'directory.example'}
    assert https_source_identity('https://www.directory.example/places/', host_aliases=aliases) == ('directory.example', '/places')
    assert https_source_identity('https://other.example/places', host_aliases=aliases) is None
    for module, connector in ((beaches, beaches.BeachesConnector()), (weather, weather.WeatherConnector())):
        assert connector.supports({'destination_id':'30a','url': module.SOURCE_URL})
        assert not connector.supports({'destination_id':'30a','url': module.SOURCE_URL.rstrip('/')})
        assert not connector.supports({'destination_id':'30a','url': module.SOURCE_URL.replace('www.', '')})


def existing_v5(tmp_path, url, method='Belirlenecek', notes=OLD_RESTAURANT_NOTE, enabled=1):
    db = Database(tmp_path/'studio.sqlite3'); db.initialize()
    source = next(s for s in db.sources() if s['url'] == r.SOURCE_URL)
    with db.connect() as con:
        con.execute('UPDATE sources SET url=?,method=?,notes=?,name=?,category=?,region=?,cadence=?,enabled=?,version=9 WHERE id=?',
                    (url,method,notes,'My restaurant source','Genel','Seaside','Aylık',enabled,source['id']))
        con.execute('CREATE TABLE repair_writes (source_id TEXT)')
        con.execute('CREATE TRIGGER track_source_update AFTER UPDATE ON sources BEGIN INSERT INTO repair_writes VALUES (NEW.id); END')
        assert con.execute('PRAGMA user_version').fetchone()[0] == 12
    return db, db.source(source['id'])


def history_and_writes(db):
    with db.connect() as con:
        return (con.execute('SELECT * FROM source_history ORDER BY id').fetchall(),
                con.execute('SELECT COUNT(*) FROM repair_writes').fetchone()[0])


@pytest.mark.parametrize('url', VARIANTS)
def test_existing_v5_repairs_defaults_binds_api_and_collects(tmp_path, monkeypatch, url):
    db, before = existing_v5(tmp_path, url)
    all_before = db.sources(); history_before, _ = history_and_writes(db)
    monkeypatch.setattr(r,'REQUEST_GAP',0); install_mock(monkeypatch,DirectoryMock())
    with TestClient(create_app(tmp_path)) as client:
        source = next(s for s in client.get('/api/sources').json() if s['id'] == before['id'])
        assert source.pop('connector') == {'name':'south-walton-restaurants','version':'south-walton-restaurants/2','method':'HTML'}
        assert source == {**before,'method':'HTML','notes':RESTAURANT_NOTE}
        assert db.sources() == [{**s,'method':'HTML','notes':RESTAURANT_NOTE} if s['id']==before['id'] else s for s in all_before]
        response = client.post('/api/jobs',json={'kind':'source_collection','source_id':before['id']},headers={'X-Studio-Request':'1'})
        assert response.status_code == 202
        assert finished(client,response.json()['id'])['status'] == 'done'
        bootstrap = client.get('/api/bootstrap').json()
        assert next(s for s in bootstrap['sources'] if s['id']==before['id'])['connector']['method']=='HTML'
    assert history_and_writes(db) == (history_before,1)
    db.initialize(); db.initialize()
    assert history_and_writes(db) == (history_before,1)
    assert db.source(before['id']) == {**before,'method':'HTML','notes':RESTAURANT_NOTE}
    with db.connect() as con: assert con.execute('PRAGMA user_version').fetchone()[0] == 12


@pytest.mark.parametrize('method', ['API','JSON','HTML','Belirlenecek'])
@pytest.mark.parametrize('notes', ['My edited note', OLD_RESTAURANT_NOTE])
@pytest.mark.parametrize('enabled', [0,1])
def test_repair_preserves_user_fields_and_is_idempotent(tmp_path,method,notes,enabled):
    db,before=existing_v5(tmp_path,VARIANTS[-1],method,notes,enabled)
    history_before,_=history_and_writes(db)
    expected={**before,'method':'HTML' if method=='Belirlenecek' else method,
              'notes':RESTAURANT_NOTE if notes==OLD_RESTAURANT_NOTE else notes}
    db.initialize()
    assert db.source(before['id'])==expected
    writes=int(expected!=before)
    assert history_and_writes(db)==(history_before,writes)
    db.initialize()
    assert history_and_writes(db)==(history_before,writes)
    assert db.source(before['id'])==expected


@pytest.mark.parametrize('url', [u for u in UNSAFE if isinstance(u,str)])
def test_repair_does_not_touch_nonmatching_sources(tmp_path,url):
    db,before=existing_v5(tmp_path,url)
    db.initialize()
    assert db.source(before['id'])==before
    assert history_and_writes(db)[1]==0


def test_correct_defaults_never_issue_update(tmp_path):
    db,before=existing_v5(tmp_path,VARIANTS[0],method='HTML',notes=RESTAURANT_NOTE)
    db.initialize();db.initialize()
    assert db.source(before['id'])==before
    assert history_and_writes(db)[1]==0


def test_note_repair_requires_exact_old_default(tmp_path):
    db,before=existing_v5(tmp_path,VARIANTS[-1],method='HTML',notes=OLD_RESTAURANT_NOTE+' ')
    db.initialize()
    assert db.source(before['id'])==before
    assert history_and_writes(db)[1]==0


def test_v4_upgrade_also_reconciles_url_variants(tmp_path):
    path=tmp_path/'studio.sqlite3';make_v4(path)
    with sqlite3.connect(path) as con:
        con.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    ('food','User name',VARIANTS[-1],'Genel','Seaside','Belirlenecek','Aylık',OLD_RESTAURANT_NOTE,1,7,'old','old'))
    db=Database(path);db.initialize()
    assert db.source('food')['method']=='HTML' and db.source('food')['notes']==RESTAURANT_NOTE
    backup,=(tmp_path/'backups').glob('*.sqlite3')
    with sqlite3.connect(backup) as con:
        assert con.execute("SELECT method,notes FROM sources WHERE id='food'").fetchone()==('Belirlenecek',OLD_RESTAURANT_NOTE)
