"""Beach access -> neighborhood mapping layer: committed file, loader, API and generator. No network."""
import csv
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from studio.app import create_app
from studio.database import Database
from studio.destinations import beach_neighborhoods as bn, thirty_a
from studio.destinations.thirty_a import BEACH_NEIGHBORHOOD_MAPPING, REGIONS
from studio.sources import beaches, neighborhoods as n
from tests.test_beaches import HEADERS, page, point
from tests.test_destinations import add_destination
from tests.test_neighborhoods import run_mock, save_run
from tools import plaj_mahalle_esleme as gen

CANONICAL = [{'id': identifier, 'name': name} for identifier, name in REGIONS]
PREVIEW = Path(__file__).resolve().parents[1] / 'docs/gorevler/GOREV-02/plaj-mahalle-onizleme.csv'
ROW = {'external_id': 'a' * 24, 'plaj_adi': 'Synthetic access', 'bolge_id': 'seaside', 'yontem': 'resmi_rehber',
       'kaynak': 'https://example.org/guide (yayın 2023-05-04)', 'not': '', 'belirsiz': 'hayır'}


def write_csv(path, rows, columns=bn.COLUMNS, encoding='utf-8'):
    with open(path, 'w', encoding=encoding, newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(columns)
        writer.writerows([[row.get(column, '') for column in columns] if isinstance(row, dict) else row for row in rows])
    return path


# --- Committed mapping file ------------------------------------------------------------------------

def test_committed_mapping_is_valid_and_follows_the_method():
    rows = bn.load(BEACH_NEIGHBORHOOD_MAPPING, CANONICAL)
    assert rows and len({row['external_id'] for row in rows}) == len(rows)
    assert not [row for row in rows if row['region_id'] in gen.NO_PUBLIC_ACCESS]
    with open(PREVIEW, encoding='utf-8') as handle:
        preview = {row['external_id']: row['kaynagin_verdigi_mahalle'] for row in csv.DictReader(handle)}
    names = dict(REGIONS)
    official = {row['external_id']: names[row['region_id']] for row in rows if row['method'] == bn.METHOD_OFFICIAL}
    assert official == {identifier: name for identifier, name in preview.items() if name}
    assert {row['external_id'] for row in rows} == set(preview)
    for row in rows:
        if row['method'] == bn.METHOD_OFFICIAL:
            assert row['source'] == gen.OFFICIAL_SOURCE and not row['ambiguous'] and row['note']
        else:
            assert re.fullmatch(r'[0-9a-f]{32}', row['source']) and row['note'].startswith('En yakın temsilî nokta')
            assert row['method_label'] == 'program türetimi'
    assert len({row['source'] for row in rows if row['method'] == bn.METHOD_DERIVED}) == 1


def test_committed_file_is_package_data():
    import tomllib
    config = tomllib.loads((Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text(encoding='utf-8'))
    assert 'destinations/*.csv' in config['tool']['setuptools']['package-data']['studio']
    assert BEACH_NEIGHBORHOOD_MAPPING.parent == Path(thirty_a.__file__).parent


# --- Loader ----------------------------------------------------------------------------------------

def test_loader_reads_rows_labels_and_tolerates_bom(tmp_path):
    rows = [ROW, {**ROW, 'external_id': 'b' * 24, 'bolge_id': 'seagrove', 'yontem': 'turetim_en_yakin_mahalle_noktasi',
                  'kaynak': 'c' * 32, 'not': 'Synthetic note', 'belirsiz': 'evet'}]
    for encoding in ('utf-8', 'utf-8-sig'):
        loaded = bn.load(write_csv(tmp_path / f'{encoding}.csv', rows, encoding=encoding), CANONICAL)
        assert [row['region_name'] for row in loaded] == ['Seaside', 'Seagrove']
        assert [row['method_label'] for row in loaded] == ['resmî rehber', 'program türetimi']
        assert [row['ambiguous'] for row in loaded] == [False, True]
        assert loaded[0]['note'] is None and loaded[1]['note'] == 'Synthetic note'
    assert bn.load(write_csv(tmp_path / 'empty.csv', []), CANONICAL) == []


@pytest.mark.parametrize('rows,columns,match', [
    ([ROW], bn.COLUMNS[:-1], 'sütunları'),
    ([ROW], (*bn.COLUMNS, 'extra'), 'sütunları'),
    ([[*ROW.values(), 'extra']], bn.COLUMNS, 'sütun sayısı'),
    ([list(ROW.values())[:-1]], bn.COLUMNS, 'sütun sayısı'),
    ([{**ROW, 'external_id': 'NOT-AN-ID'}], bn.COLUMNS, 'kimliği geçersiz'),
    ([ROW, ROW], bn.COLUMNS, 'birden fazla'),
    ([{**ROW, 'bolge_id': 'miramar-beach'}], bn.COLUMNS, 'bölge kimliği'),
    ([{**ROW, 'yontem': 'tahmin'}], bn.COLUMNS, 'yöntem'),
    ([{**ROW, 'belirsiz': 'yes'}], bn.COLUMNS, 'evet veya hayır'),
    ([{**ROW, 'kaynak': ' '}], bn.COLUMNS, 'boş'),
    ([{**ROW, 'plaj_adi': ''}], bn.COLUMNS, 'boş'),
])
def test_loader_rejects_invalid_files(tmp_path, rows, columns, match):
    with pytest.raises(bn.MappingError, match=match):
        bn.load(write_csv(tmp_path / 'mapping.csv', rows, columns), CANONICAL)


def test_loader_rejects_missing_or_undecodable_file(tmp_path):
    with pytest.raises(bn.MappingError, match='okunamadı'):
        bn.load(tmp_path / 'missing.csv', CANONICAL)
    broken = tmp_path / 'broken.csv'; broken.write_bytes(','.join(bn.COLUMNS).encode() + b'\n\xff\xfe\xfa')
    with pytest.raises(bn.MappingError, match='okunamadı'):
        bn.load(broken, CANONICAL)


# --- API -------------------------------------------------------------------------------------------

def test_api_serves_mapping_for_30a_only(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        add_destination(client.app.state.db)
        layer = client.get('/api/beach-neighborhoods').json()
        assert layer['available'] and layer['file'] == BEACH_NEIGHBORHOOD_MAPPING.name
        assert layer['methods'] == {'resmi_rehber': 'resmî rehber', 'turetim_en_yakin_mahalle_noktasi': 'program türetimi'}
        assert layer['rows'] == bn.load(BEACH_NEIGHBORHOOD_MAPPING, CANONICAL)
        assert client.get('/api/bootstrap').json()['beach_neighborhoods'] == layer
        other = client.get('/api/beach-neighborhoods?destination_id=test-coast').json()
        assert other == {'available': False, 'reason': 'Bu destinasyon için plaj–mahalle eşleme dosyası yok.', 'rows': []}
        assert client.get('/api/bootstrap?destination_id=test-coast').json()['beach_neighborhoods'] == other
        assert client.get('/api/beach-neighborhoods?destination_id=missing').status_code == 404


def test_broken_mapping_file_is_reported_and_app_keeps_working(tmp_path, monkeypatch):
    broken = write_csv(tmp_path / 'broken.csv', [{**ROW, 'bolge_id': 'unknown'}])
    monkeypatch.setattr(thirty_a, 'BEACH_NEIGHBORHOOD_MAPPING', broken)
    with TestClient(create_app(tmp_path / 'data'), headers=HEADERS) as client:
        layer = client.get('/api/beach-neighborhoods').json()
        assert not layer['available'] and 'bölge kimliği' in layer['reason'] and layer['rows'] == []
        assert client.get('/api/bootstrap').status_code == 200


def test_mapping_never_touches_beach_records(tmp_path):
    db = Database(tmp_path / 'studio.sqlite3'); db.initialize()
    source = next(s for s in db.sources() if s['url'] == beaches.SOURCE_URL)
    connector = beaches.BeachesConnector()
    run = db.add_job('source_collection', 'Beaches', source['id'], connector)
    db.complete_source_run(run, beaches.parse_page(page(point(id='5c81ab02f836f9166348e96c'))), connector)
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        assert client.get('/api/beach-neighborhoods').json()['available']
        record, = client.get(f'/api/source-runs/{run}').json()['records']
        assert record['canonical_region_id'] is None and 'region_id' not in record and 'method' not in record


# --- Generator -------------------------------------------------------------------------------------

def hood(region_id, longitude):
    return {'region_id': region_id, 'longitude': longitude}


EAST = [hood('seacrest', -86.0403), hood('alys-beach', -86.0306), hood('rosemary-beach', -86.0161), hood('inlet-beach', -86.008)]


def test_nearest_skips_no_public_access_neighborhoods_and_explains():
    result = gen.nearest(-86.016, EAST)
    assert result['chosen']['region_id'] == 'inlet-beach' and result['runner_up']['region_id'] == 'seacrest'
    assert [skipped['region_id'] for skipped, _ in result['skipped']] == ['rosemary-beach']
    note = gen.derived_note(result)
    assert 'Inlet Beach' in note and 'Daha yakın Rosemary Beach' in note and 'halka açık plaj erişimi' in note
    between = gen.nearest(-86.03, EAST)
    assert between['chosen']['region_id'] == 'seacrest'
    assert [skipped['region_id'] for skipped, _ in between['skipped']] == ['alys-beach']


@pytest.mark.parametrize('longitude,ambiguous', [(-86.1235, True), (-86.1244, True), (-86.1250, False), (-86.1300, False), (-86.1100, False)])
def test_ambiguity_threshold_between_two_assignable_candidates(longitude, ambiguous):
    result = gen.nearest(longitude, [hood('seaside', -86.137546), hood('seagrove', -86.108829)])
    assert result['ambiguous'] is ambiguous
    assert ('0.003° altında' in gen.derived_note(result)) is ambiguous


def test_nearest_needs_two_assignable_points():
    with pytest.raises(SystemExit):
        gen.nearest(-86.02, [hood('alys-beach', -86.03), hood('rosemary-beach', -86.016), hood('inlet-beach', -86.008)])


def preview_csv(path, rows):
    return write_csv(path, rows, ('external_id', 'ad', 'kaynagin_verdigi_mahalle', 'kaynak'))


def test_official_rows_are_taken_as_they_are_and_doubt_stops(tmp_path):
    evidence = gen.OFFICIAL_PREFIX + 'başlık: Seaside; eşleşme: ad'
    path = preview_csv(tmp_path / 'p.csv', [['a' * 24, 'One', 'Seaside', evidence], ['b' * 24, 'Two', '', '']])
    assert gen.official_rows(path, {'a' * 24, 'b' * 24}) == {'a' * 24: {'region_id': 'seaside', 'note': 'başlık: Seaside; eşleşme: ad'}}
    for rows, ids in (([['c' * 24, 'X', 'Seaside', evidence]], {'a' * 24}),
                      ([['a' * 24, 'X', 'Miramar Beach', evidence]], {'a' * 24}),
                      ([['a' * 24, 'X', 'Seaside', 'Başka bir kaynak']], {'a' * 24})):
        with pytest.raises(SystemExit):
            gen.official_rows(preview_csv(tmp_path / 'bad.csv', rows), ids)


def test_build_orders_west_to_east_and_validates_official_rows():
    beaches_ = [{'external_id': 'b' * 24, 'name': 'East', 'longitude': -86.016},
                {'external_id': 'a' * 24, 'name': 'West', 'longitude': -86.04},
                {'external_id': 'c' * 24, 'name': 'Official', 'longitude': -86.009}]
    official = {'c' * 24: {'region_id': 'seacrest', 'note': 'başlık: Seacrest'}}
    mapping, validation = gen.build(beaches_, EAST, official, 'd' * 32)
    assert [row['plaj_adi'] for row in mapping] == ['West', 'East', 'Official']
    assert [row['bolge_id'] for row in mapping] == ['seacrest', 'inlet-beach', 'seacrest']
    assert [row['yontem'] for row in mapping] == [bn.METHOD_DERIVED, bn.METHOD_DERIVED, bn.METHOD_OFFICIAL]
    assert mapping[0]['kaynak'] == 'd' * 32 and mapping[2]['kaynak'] == gen.OFFICIAL_SOURCE and mapping[2]['not'] == 'başlık: Seacrest'
    assert validation == [{'external_id': 'c' * 24, 'plaj_adi': 'Official', 'resmi_bolge_id': 'seacrest', 'turetilen_bolge_id': 'inlet-beach',
                           'ayni': 'hayır', 'boylam_farki': '0.0010', 'sonraki_aday': 'seacrest', 'sonraki_fark': '0.0313',
                           'belirsiz': 'hayır', 'atlanan': ''}]


def test_generator_end_to_end_reads_db_read_only_and_writes_loadable_file(tmp_path, monkeypatch):
    monkeypatch.setattr(n, 'REQUEST_GAP', 0)
    db = Database(tmp_path / 'studio.sqlite3'); db.initialize()
    source = next(s for s in db.sources() if s['url'] == beaches.SOURCE_URL)
    connector = beaches.BeachesConnector()
    beach_run = db.add_job('source_collection', 'Beaches', source['id'], connector)
    ids = [f'{0xabc0 + i:024x}' for i in range(3)]
    batch = beaches.parse_page(page(point(id=ids[0], name='West access', lng=-86.29), point(id=ids[1], name='Official access', lng=-86.145),
                                    point(id=ids[2], name='East access', lng=-86.061)))
    db.complete_source_run(beach_run, batch, connector)
    (tmp_path / 'hoods').mkdir()
    hood_run = save_run(db, run_mock(tmp_path / 'hoods').records)
    preview = preview_csv(tmp_path / 'preview.csv', [[ids[0], 'West access', '', ''], [ids[1], 'Official access', 'Seaside', gen.OFFICIAL_PREFIX + 'başlık: Seaside'],
                                                     [ids[2], 'East access', '', '']])
    before = (tmp_path / 'studio.sqlite3').read_bytes()
    out, check = tmp_path / 'mapping.csv', tmp_path / 'check.csv'
    mapping, validation = gen.main(['--data-dir', str(tmp_path), '--resmi', str(preview), '--cikti', str(out), '--dogrulama', str(check)])
    assert (tmp_path / 'studio.sqlite3').read_bytes() == before
    rows = bn.load(out, CANONICAL)
    assert [(row['beach_name'], row['region_id'], row['method']) for row in rows] == [
        ('West access', 'dune-allen', bn.METHOD_DERIVED), ('Official access', 'seaside', bn.METHOD_OFFICIAL), ('East access', 'inlet-beach', bn.METHOD_DERIVED)]
    assert rows[0]['source'] == hood_run and 'Daha yakın Rosemary Beach' in rows[2]['note'] and 'Alys Beach' in rows[2]['note']
    with open(check, encoding='utf-8') as handle:
        assert [row['external_id'] for row in csv.DictReader(handle)] == [ids[1]]
    assert len(validation) == 1 and len(mapping) == 3
