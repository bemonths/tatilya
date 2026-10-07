"""Seed refresh is restricted to exact historical defaults during v3 -> v4."""
import sqlite3

import pytest

from studio.database import Database
from studio.sources.climate_normals import SOURCE_URL as NORMALS_URL
from studio.sources.storm_proximity import SOURCE_URL as STORMS_URL
from studio.sources.water_temperature import SOURCE_URL as WATER_URL
from tests.test_weather import make_v3
from tests.legacy import make_legacy_db

NWS = 'https://www.weather.gov/'
BEACH = 'https://www.visitsouthwalton.com/beach-bay-access-locations/'
OLD_NOTE = 'Hava verisi için başlangıç kaynağı. Bölge koordinatları ve veri uçları sonraki aşamada belirlenecek.'
NEW_NOTE = '30A koridorundaki batı, orta ve doğu örnek noktaları için NWS tahminleri ve aktif hava uyarıları. Forecast, saatlik forecast ve aktif alert verileri api.weather.gov üzerinden toplanır.'


@pytest.mark.parametrize('notes,method,url,expected_notes,expected_method', [
    (OLD_NOTE, 'Belirlenecek', NWS, NEW_NOTE, 'API'),
    ('Kullanıcının hava notu', 'Belirlenecek', NWS, 'Kullanıcının hava notu', 'API'),
    (OLD_NOTE, 'HTML', NWS, NEW_NOTE, 'HTML'),
    ('Kullanıcının hava notu', 'HTML', NWS, 'Kullanıcının hava notu', 'HTML'),
    (OLD_NOTE + ' ', 'API', NWS, OLD_NOTE + ' ', 'API'),
    (OLD_NOTE, 'Belirlenecek', 'https://www.weather.gov/other', OLD_NOTE, 'Belirlenecek'),
])
def test_migration_updates_only_exact_nws_defaults(tmp_path, notes, method, url, expected_notes, expected_method):
    path = tmp_path / 'studio.sqlite3'; make_v3(path)
    with sqlite3.connect(path) as con:
        con.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (
            'nws', 'Custom name', url, 'Hava', 'Tüm 30A', method, 'Aylık', notes, 0, 7, 'created', 'updated'))
        before = con.execute("SELECT * FROM sources WHERE id='nws'").fetchone()
        history = con.execute('SELECT * FROM source_history').fetchall()
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        after = con.execute("SELECT * FROM sources WHERE id='nws'").fetchone()
        expected = list(before); expected[5] = expected_method; expected[7] = expected_notes
        assert list(after) == expected + ["30a",None]
        assert con.execute('SELECT * FROM source_history').fetchall() == history
        assert con.execute('PRAGMA user_version').fetchone()[0] == 9
    backup, = (tmp_path / 'backups').glob('*.sqlite3')
    with sqlite3.connect(backup) as con:
        assert con.execute("SELECT * FROM sources WHERE id='nws'").fetchone() == before
    Database(path).initialize()
    assert Database(path).source('nws')['notes'] == expected_notes


@pytest.mark.parametrize('method,expected', [('Belirlenecek', 'JSON'), ('HTML', 'HTML'), ('API', 'API')])
def test_migration_beach_method_preserves_user_choice(tmp_path, method, expected):
    path = tmp_path / 'studio.sqlite3'; make_v3(path)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE sources SET method=? WHERE id='source-a'", (method,))
    db = Database(path); before = db.source('source-a'); db.initialize()
    assert db.source('source-a') == {**before, 'method': expected, 'destination_id':'30a','scope_region_id':None}


def test_fresh_seed_methods_and_nws_description(tmp_path):
    db = Database(tmp_path / 'studio.sqlite3'); db.initialize()
    sources = {s['url']: s for s in db.sources()}
    assert sources[NWS]['method'] == 'API' and sources[NWS]['notes'] == NEW_NOTE
    assert sources[BEACH]['method'] == 'JSON'
    climate = {NORMALS_URL: 'API', WATER_URL: 'Dosya', STORMS_URL: 'Dosya'}
    assert {url: sources[url]['method'] for url in climate} == climate
    assert all(s['method'] == 'Belirlenecek' for url, s in sources.items() if url not in (NWS, BEACH, "https://www.visitsouthwalton.com/listings/culinary-experiences/", "https://www.visitsouthwalton.com/neighborhoods/", *climate))


def test_v2_chain_also_refreshes_default_beach_method(tmp_path):
    path = tmp_path / 'studio.sqlite3'; make_legacy_db(path)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE sources SET method='Belirlenecek' WHERE id='source-a'")
    db = Database(path); db.initialize()
    assert db.source('source-a')['method'] == 'JSON'
    assert len(db.run_records('old-success')) == 1
