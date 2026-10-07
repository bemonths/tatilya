"""Beach access -> neighborhood mapping layer: committed file, loader, API and generator. No network."""
import csv
import json
import math
import re
from pathlib import Path

import httpx

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
    subdivisions = gen.read_subdivisions(thirty_a.BEACH_SUBDIVISIONS)
    table = gen.read_name_table(thirty_a.SUBDIVISION_NEIGHBORHOODS)
    assert set(subdivisions) == {row['external_id'] for row in rows}
    by_id = {row['external_id']: row for row in rows}
    for row in rows:
        inside = gen.inside_result(subdivisions[row['external_id']], table)
        adjacent = gen.adjacent_result(subdivisions[row['external_id']], table, inside)
        if row['method'] == bn.METHOD_OFFICIAL:
            assert row['source'] == gen.OFFICIAL_SOURCE and not row['ambiguous'] and row['note']
        elif row['method'] == bn.METHOD_COUNTY:
            assert inside['status'] == 'atandi' and inside['region_id'] == row['region_id']
            assert row['source'].startswith(thirty_a.COUNTY_SUBDIVISION_LAYER + ' (sorgu ')
        elif row['method'] == bn.METHOD_COUNTY_ADJACENT:
            assert inside['status'] != 'atandi' and adjacent['status'] == 'atandi' and adjacent['region_id'] == row['region_id']
            assert row['source'].startswith(thirty_a.COUNTY_SUBDIVISION_LAYER + ' (sorgu ')
            assert all(float(r['mesafe_m']) <= gen.ADJACENT_METERS for r in adjacent['rows'])
        elif row['method'] == bn.METHOD_NEIGHBORS:
            west, east = re.fullmatch(r'komşu erişimler ([0-9a-f]{24}) ve ([0-9a-f]{24})', row['source']).groups()
            assert {by_id[west]['method'], by_id[east]['method']} <= {bn.METHOD_OFFICIAL, bn.METHOD_COUNTY, bn.METHOD_COUNTY_ADJACENT}
            assert by_id[west]['region_id'] == by_id[east]['region_id'] == row['region_id']
            assert by_id[west]['beach_name'] in row['note'] and by_id[east]['beach_name'] in row['note']
        else:
            assert row['method'] == bn.METHOD_DERIVED and inside['status'] != 'atandi' and adjacent['status'] != 'atandi'
            assert re.fullmatch(r'[0-9a-f]{32}', row['source']) and row['note'].startswith('En yakın temsilî nokta')
    assert len({row['source'] for row in rows if row['method'] == bn.METHOD_DERIVED}) == 1
    assert {row['method'] for row in rows} == set(bn.METHOD_LABELS)


def test_committed_subdivision_files_are_consistent():
    subdivisions = gen.read_subdivisions(thirty_a.BEACH_SUBDIVISIONS)
    table = gen.read_name_table(thirty_a.SUBDIVISION_NEIGHBORHOODS)
    for rows in subdivisions.values():
        for row in rows:
            assert row['katman_url'] == thirty_a.COUNTY_SUBDIVISION_LAYER and row['sorgu_zamani'].endswith('+00:00')
            if row['iliski'] != 'sonucsuz':
                assert 0 <= float(row['mesafe_m']) <= gen.NEAR_METERS and row['poligon_kimligi']
            if row['iliski'] == 'iceride':
                assert float(row['mesafe_m']) == 0
    returned = {row['alt_bolum_adi'] for rows in subdivisions.values() for row in rows}
    # The table only holds names the query actually returned; no invented spellings.
    assert set(table) <= returned
    assert {'SEAGROVE ENDEAVORS', 'SEASIDE LAND AND DEVELOPMENT', 'VILLAS AT SANTA ROSA BEACH THE'}.isdisjoint(table)


def test_committed_file_is_package_data():
    import tomllib
    config = tomllib.loads((Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text(encoding='utf-8'))
    assert 'destinations/*.csv' in config['tool']['setuptools']['package-data']['studio']
    assert BEACH_NEIGHBORHOOD_MAPPING.parent == Path(thirty_a.__file__).parent


# --- Loader ----------------------------------------------------------------------------------------

def test_loader_reads_rows_labels_and_tolerates_bom(tmp_path):
    rows = [ROW, {**ROW, 'external_id': 'b' * 24, 'bolge_id': 'seagrove', 'yontem': 'turetim_en_yakin_mahalle_noktasi',
                  'kaynak': 'c' * 32, 'not': 'Synthetic note', 'belirsiz': 'evet'},
            {**ROW, 'external_id': 'd' * 24, 'bolge_id': 'grayton-beach', 'yontem': 'ilce_alt_bolum',
             'kaynak': thirty_a.COUNTY_SUBDIVISION_LAYER + ' (sorgu 2026-10-07)', 'not': 'Walton County Subdivision Boundaries'}]
    for encoding in ('utf-8', 'utf-8-sig'):
        loaded = bn.load(write_csv(tmp_path / f'{encoding}.csv', rows, encoding=encoding), CANONICAL)
        assert [row['region_name'] for row in loaded] == ['Seaside', 'Seagrove', 'Grayton Beach']
        assert [row['method_label'] for row in loaded] == ['resmî rehber', 'program türetimi', 'ilçe alt bölüm verisi']
        assert [row['ambiguous'] for row in loaded] == [False, True, False]
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
        assert layer['methods'] == bn.METHOD_LABELS and layer['methods']['ilce_alt_bolum_yakin'] == 'ilçe alt bölüm verisi (bitişik)'
        assert layer['methods']['komsu_tutarliligi'] == 'komşu erişimlerle tutarlı'
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
    mapping, validation, conflicts = gen.build(beaches_, EAST, official, 'd' * 32)
    assert [row['plaj_adi'] for row in mapping] == ['West', 'East', 'Official']
    assert [row['bolge_id'] for row in mapping] == ['seacrest', 'inlet-beach', 'seacrest']
    assert [row['yontem'] for row in mapping] == [bn.METHOD_DERIVED, bn.METHOD_DERIVED, bn.METHOD_OFFICIAL]
    assert mapping[0]['kaynak'] == 'd' * 32 and mapping[2]['kaynak'] == gen.OFFICIAL_SOURCE and mapping[2]['not'] == 'başlık: Seacrest'
    assert 'İlçe alt bölüm sorgusu bu erişim için yapılmadı.' in mapping[0]['not']
    assert validation == [{'external_id': 'c' * 24, 'plaj_adi': 'Official', 'resmi_bolge_id': 'seacrest',
                           'ilce_bolge_id': '', 'ilce_sonuc': 'sonucsuz', 'ilce_yakin_bolge_id': '', 'ilce_yakin_sonuc': 'sonucsuz',
                           'komsu_bolge_id': '', 'komsu_sonuc': 'sonucsuz', 'turetilen_bolge_id': 'inlet-beach', 'turetme_sonuc': 'farkli',
                           'zincir_yontem': bn.METHOD_DERIVED, 'zincir_bolge_id': 'inlet-beach', 'zincir_sonuc': 'farkli'}]
    assert conflicts == []


LAYER = thirty_a.COUNTY_SUBDIVISION_LAYER
TABLE = {'SEAGROVE 1ST ADD': 'seagrove', 'SEAGROVE 3RD ADD': 'seagrove', 'SEASIDE S/D': 'seaside',
         'ROSEMARY BEACH PH 1': 'rosemary-beach', 'ALYS BEACH PH 2': 'alys-beach'}


def sub(identifier, name, relation='iceride', distance='0', polygon='7', number='15-3S-19-25070'):
    empty = relation == 'sonucsuz'
    return {'external_id': identifier, 'alt_bolum_adi': name, 'alt_bolum_numarasi': '' if empty else number,
            'poligon_kimligi': '' if empty else polygon, 'iliski': relation, 'mesafe_m': '' if empty else distance,
            'katman_url': LAYER, 'sorgu_zamani': '2026-10-07T10:36:38+00:00'}


@pytest.mark.parametrize('rows,status,region', [
    ([sub('x', 'SEAGROVE 1ST ADD')], 'atandi', 'seagrove'),
    ([sub('x', 'INFORMATION ONLY'), sub('x', 'SEAGROVE 1ST ADD', polygon='8')], 'atandi', 'seagrove'),
    ([sub('x', 'SUGARWOOD S/D')], 'tabloda_yok', None),
    ([sub('x', 'SEAGROVE 1ST ADD', 'yakin', '6.3')], 'yok', None),
    ([sub('x', '', 'sonucsuz')], 'yok', None),
    ([], 'sorgu_yok', None),
    ([sub('x', 'SEAGROVE 1ST ADD'), sub('x', 'SEASIDE S/D', polygon='8')], 'karisik', None),
    ([sub('x', 'ROSEMARY BEACH PH 1')], 'celiski', None),
    ([sub('x', 'ALYS BEACH PH 2')], 'celiski', None),
])
def test_inside_rule_only_named_polygons_containing_the_point(rows, status, region):
    result = gen.inside_result(rows, TABLE)
    assert result['status'] == status and result['region_id'] == region


@pytest.mark.parametrize('distance,status', [('29.9', 'atandi'), ('30.0', 'atandi'), ('30.1', 'yok'), ('74.9', 'yok')])
def test_adjacent_rule_30_metre_boundary(distance, status):
    rows = [sub('x', 'SEAGROVE 1ST ADD', 'yakin', distance)]
    result = gen.adjacent_result(rows, TABLE, gen.inside_result(rows, TABLE))
    assert result['status'] == status and result['region_id'] == ('seagrove' if status == 'atandi' else None)


def test_adjacent_rule_works_inside_unnamed_polygon_but_not_inside_named_one():
    rows = [sub('x', 'INFORMATION ONLY'), sub('x', 'SUGARWOOD S/D', polygon='8'), sub('x', 'SEAGROVE 3RD ADD', 'yakin', '12.0', '9')]
    inside = gen.inside_result(rows, TABLE)
    assert inside['status'] == 'tabloda_yok'
    adjacent = gen.adjacent_result(rows, TABLE, inside)
    assert (adjacent['status'], adjacent['region_id']) == ('atandi', 'seagrove')
    named_inside = [sub('x', 'SEASIDE S/D'), sub('x', 'SEAGROVE 3RD ADD', 'yakin', '12.0', '9')]
    inside = gen.inside_result(named_inside, TABLE)
    assert inside['region_id'] == 'seaside'
    assert gen.adjacent_result(named_inside, TABLE, inside)['status'] == 'uygulanmaz'


def test_adjacent_rule_with_two_neighborhoods_gives_no_result():
    rows = [sub('x', 'SEAGROVE 1ST ADD', 'yakin', '8.0'), sub('x', 'SEASIDE S/D', 'yakin', '25.0', '8'),
            sub('x', 'SEASIDE S/D', 'yakin', '45.0', '9')]
    result = gen.adjacent_result(rows, TABLE, gen.inside_result(rows, TABLE))
    assert (result['status'], result['region_id'], result['regions']) == ('karisik', None, ['seagrove', 'seaside'])
    notes = ' '.join(gen.county_notes(rows, gen.inside_result(rows, TABLE), result, TABLE))
    assert 'farklı mahallelere bağlanan poligonlar var' in notes and 'bitişik kural sonuç vermedi' in notes
    # Only 30 m counts: the farther Seaside polygon alone would not block a Seagrove result.
    rows = [sub('x', 'SEAGROVE 1ST ADD', 'yakin', '8.0'), sub('x', 'SEASIDE S/D', 'yakin', '45.0', '9')]
    assert gen.adjacent_result(rows, TABLE, gen.inside_result(rows, TABLE))['region_id'] == 'seagrove'


WEST_EAST = [hood('seaside', -86.137546), hood('seagrove', -86.108829), hood('seacrest', -86.0403), hood('alys-beach', -86.0306),
             hood('rosemary-beach', -86.0161), hood('inlet-beach', -86.008)]


def beach(letter, name, longitude):
    return {'external_id': letter * 24, 'name': name, 'longitude': longitude}


def test_method_order_neighbors_and_derived_fallback():
    beaches_ = [beach('a', 'A inside', -86.140), beach('b', 'B between', -86.139), beach('c', 'C adjacent', -86.138),
                beach('d', 'D between other', -86.137), beach('e', 'E official', -86.136), beach('f', 'F no east', -86.135)]
    subdivisions = {'a' * 24: [sub('a' * 24, 'SEAGROVE 1ST ADD')], 'b' * 24: [sub('b' * 24, 'SUGARWOOD S/D')],
                    'c' * 24: [sub('c' * 24, 'SEAGROVE 3RD ADD', 'yakin', '9.6')], 'd' * 24: [sub('d' * 24, '', 'sonucsuz')],
                    'e' * 24: [sub('e' * 24, '', 'sonucsuz')], 'f' * 24: [sub('f' * 24, '', 'sonucsuz')]}
    official = {'e' * 24: {'region_id': 'seaside', 'note': 'başlık: Seaside'}}
    mapping, validation, conflicts = gen.build(beaches_, WEST_EAST, official, 'd' * 32, subdivisions, TABLE)
    by = {row['plaj_adi']: row for row in mapping}
    assert (by['A inside']['bolge_id'], by['A inside']['yontem']) == ('seagrove', bn.METHOD_COUNTY)
    assert (by['C adjacent']['bolge_id'], by['C adjacent']['yontem']) == ('seagrove', bn.METHOD_COUNTY_ADJACENT)
    assert '9.6 m' in by['C adjacent']['not'] and by['C adjacent']['kaynak'] == f'{LAYER} (sorgu 2026-10-07)'
    # Both sourced neighbours agree: Seagrove.
    assert (by['B between']['bolge_id'], by['B between']['yontem']) == ('seagrove', bn.METHOD_NEIGHBORS)
    assert by['B between']['kaynak'] == f"komşu erişimler {'a' * 24} ve {'c' * 24}"
    assert 'A inside' in by['B between']['not'] and 'C adjacent' in by['B between']['not']
    # Neighbours disagree (Seagrove vs official Seaside): fall back to the derived method.
    assert by['D between other']['yontem'] == bn.METHOD_DERIVED and 'Komşu tutarlılığı sonuç vermedi: batıda' in by['D between other']['not']
    # Nothing sourced to the east: no neighbour result.
    assert by['F no east']['yontem'] == bn.METHOD_DERIVED and 'yalnız bir tarafta kaynaklı erişim var' in by['F no east']['not']
    assert conflicts == []
    # Official access: later methods are only reported; its sourced neighbours are C (Seagrove) and nothing east.
    assert validation[0]['komsu_sonuc'] == 'sonucsuz' and validation[0]['zincir_yontem'] == bn.METHOD_DERIVED


def test_neighbors_do_not_chain_from_neighbor_results():
    beaches_ = [beach('a', 'A', -86.140), beach('b', 'B', -86.139), beach('c', 'C', -86.138), beach('d', 'D', -86.137)]
    subdivisions = {'a' * 24: [sub('a' * 24, 'SEAGROVE 1ST ADD')], 'b' * 24: [sub('b' * 24, '', 'sonucsuz')],
                    'c' * 24: [sub('c' * 24, '', 'sonucsuz')], 'd' * 24: [sub('d' * 24, 'SEAGROVE 1ST ADD')]}
    mapping, _, _ = gen.build(beaches_, WEST_EAST, {}, 'd' * 32, subdivisions, TABLE)
    assert [row['yontem'] for row in mapping] == [bn.METHOD_COUNTY, bn.METHOD_NEIGHBORS, bn.METHOD_NEIGHBORS, bn.METHOD_COUNTY]
    assert {row['kaynak'] for row in mapping[1:3]} == {f"komşu erişimler {'a' * 24} ve {'d' * 24}"}


def test_rosemary_and_alys_never_assigned_by_any_method():
    beaches_ = [beach('a', 'Inside Rosemary', -86.017), beach('b', 'Adjacent Alys', -86.031), beach('c', 'Seacrest', -86.041),
                beach('d', 'Inlet', -86.006)]
    subdivisions = {'a' * 24: [sub('a' * 24, 'ROSEMARY BEACH PH 1')], 'b' * 24: [sub('b' * 24, 'ALYS BEACH PH 2', 'yakin', '5.0')],
                    'c' * 24: [sub('c' * 24, '', 'sonucsuz')], 'd' * 24: [sub('d' * 24, '', 'sonucsuz')]}
    official = {'c' * 24: {'region_id': 'seacrest', 'note': 'x'}, 'd' * 24: {'region_id': 'inlet-beach', 'note': 'y'}}
    mapping, _, conflicts = gen.build(beaches_, WEST_EAST, official, 'd' * 32, subdivisions, TABLE)
    by = {row['plaj_adi']: row for row in mapping}
    assert by['Inside Rosemary']['bolge_id'] not in gen.NO_PUBLIC_ACCESS and by['Adjacent Alys']['bolge_id'] not in gen.NO_PUBLIC_ACCESS
    assert 'Resmî rehberle çelişki' in by['Inside Rosemary']['not'] and 'Resmî rehberle çelişki' in by['Adjacent Alys']['not']
    assert [(c['plaj_adi'], c['bolge_id']) for c in conflicts] == [('Adjacent Alys', 'alys-beach'), ('Inside Rosemary', 'rosemary-beach')]
    # Inside the Rosemary polygon: the adjacent rule does not apply; neighbours disagree, so the derived method decides.
    assert by['Inside Rosemary']['yontem'] == bn.METHOD_DERIVED and by['Adjacent Alys']['yontem'] == bn.METHOD_DERIVED


def test_compare_lists_region_and_method_changes():
    previous = [{'external_id': 'a', 'plaj_adi': 'A', 'bolge_id': 'seaside', 'yontem': bn.METHOD_DERIVED},
                {'external_id': 'b', 'plaj_adi': 'B', 'bolge_id': 'seagrove', 'yontem': bn.METHOD_DERIVED},
                {'external_id': 'c', 'plaj_adi': 'C', 'bolge_id': 'seacrest', 'yontem': bn.METHOD_DERIVED}]
    current = [{'external_id': 'a', 'plaj_adi': 'A', 'bolge_id': 'seagrove', 'yontem': bn.METHOD_COUNTY_ADJACENT},
               {'external_id': 'b', 'plaj_adi': 'B', 'bolge_id': 'seagrove', 'yontem': bn.METHOD_NEIGHBORS},
               {'external_id': 'c', 'plaj_adi': 'C', 'bolge_id': 'seacrest', 'yontem': bn.METHOD_DERIVED},
               {'external_id': 'd', 'plaj_adi': 'D', 'bolge_id': 'seacrest', 'yontem': bn.METHOD_DERIVED}]
    assert gen.compare(previous, current) == [
        {'external_id': 'a', 'plaj_adi': 'A', 'onceki_bolge_id': 'seaside', 'onceki_yontem': bn.METHOD_DERIVED, 'yeni_bolge_id': 'seagrove', 'yeni_yontem': bn.METHOD_COUNTY_ADJACENT, 'degisen': 'bolge+yontem'},
        {'external_id': 'b', 'plaj_adi': 'B', 'onceki_bolge_id': 'seagrove', 'onceki_yontem': bn.METHOD_DERIVED, 'yeni_bolge_id': 'seagrove', 'yeni_yontem': bn.METHOD_NEIGHBORS, 'degisen': 'yontem'},
        {'external_id': 'd', 'plaj_adi': 'D', 'onceki_bolge_id': '', 'onceki_yontem': '', 'yeni_bolge_id': 'seacrest', 'yeni_yontem': bn.METHOD_DERIVED, 'degisen': 'bolge+yontem'}]


def test_subdivision_and_name_table_readers_reject_doubt(tmp_path):
    good = write_csv(tmp_path / 'sub.csv', [sub('a' * 24, 'SEAGROVE 1ST ADD'), sub('a' * 24, 'INFORMATION ONLY', 'yakin', '12.5', '8'),
                                            sub('b' * 24, '', 'sonucsuz')], gen.SUBDIVISION_COLUMNS)
    assert {key: len(rows) for key, rows in gen.read_subdivisions(good).items()} == {'a' * 24: 2, 'b' * 24: 1}
    for rows, columns in (([sub('a' * 24, 'X')], gen.SUBDIVISION_COLUMNS[:-1]),
                          ([{**sub('a' * 24, 'X'), 'iliski': 'icinde'}], gen.SUBDIVISION_COLUMNS),
                          ([sub('a' * 24, 'X', 'iceride', '3.0')], gen.SUBDIVISION_COLUMNS),
                          ([sub('a' * 24, 'X', 'yakin', '80.0')], gen.SUBDIVISION_COLUMNS),
                          ([sub('a' * 24, 'X', 'yakin', 'uzak')], gen.SUBDIVISION_COLUMNS),
                          ([sub('a' * 24, 'X'), sub('a' * 24, '', 'sonucsuz')], gen.SUBDIVISION_COLUMNS),
                          ([{**sub('a' * 24, '', 'sonucsuz'), 'poligon_kimligi': '5'}], gen.SUBDIVISION_COLUMNS)):
        with pytest.raises(SystemExit):
            gen.read_subdivisions(write_csv(tmp_path / 'bad.csv', rows, columns))
    table = write_csv(tmp_path / 'table.csv', [['SEAGROVE 1ST ADD', 'seagrove', 'adında SEAGROVE geçiyor']], gen.TABLE_COLUMNS)
    assert gen.read_name_table(table) == {'SEAGROVE 1ST ADD': 'seagrove'}
    for rows in ([['SEAGROVE 1ST ADD', 'seagrove', 'x'], ['SEAGROVE 1ST ADD', 'seaside', 'y']],
                 [['MIRAMAR S/D', 'miramar-beach', 'x']], [['SEAGROVE 1ST ADD', 'seagrove', ' ']], [['', 'seagrove', 'x']]):
        with pytest.raises(SystemExit):
            gen.read_name_table(write_csv(tmp_path / 'bad-table.csv', rows, gen.TABLE_COLUMNS))


def ring_around(lon, lat, dx_m, size_m=20):
    """Square polygon whose west edge is dx_m metres east of the point."""
    kx, ky = 111320 * math.cos(math.radians(lat)), 110574
    x0, x1 = lon + dx_m / kx, lon + (dx_m + size_m) / kx
    y0, y1 = lat - size_m / ky, lat + size_m / ky
    return [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]


def test_query_records_inside_and_every_polygon_within_75_m(tmp_path):
    beaches_ = [{'external_id': 'a' * 24, 'name': 'Inside', 'latitude': 30.31, 'longitude': -86.14},
                {'external_id': 'b' * 24, 'name': 'Near', 'latitude': 30.31, 'longitude': -86.13},
                {'external_id': 'c' * 24, 'name': 'Far', 'latitude': 30.31, 'longitude': -86.12}]
    seen = []

    def handler(request):
        seen.append(request)
        params = dict(request.url.params)
        assert request.url.path.endswith('/FeatureServer/13/query') and request.url.host == 'services1.arcgis.com'
        assert params['geometryType'] == 'esriGeometryPoint' and params['spatialRel'] == 'esriSpatialRelIntersects'
        assert params['inSR'] == '4326' and json.loads(params['geometry'])['spatialReference'] == {'wkid': 4326}
        assert 'SUBDIVISION_NUMBER' in params['outFields']
        point = json.loads(params['geometry'])
        x, y = point['x'], point['y']
        if 'distance' not in params:
            assert params['returnGeometry'] == 'false'
            features = [{'attributes': {'OBJECTID': 5, 'OWNER_NAME': 'SEAGROVE 1ST ADD ', 'SUBDIVISION_NUMBER': '15-3S-19-25070'}}] if x == -86.14 else []
        else:
            assert params['units'] == 'esriSRUnit_Meter' and float(params['distance']) >= gen.NEAR_METERS and params['outSR'] == '4326'
            if x == -86.14:
                features = [{'attributes': {'OBJECTID': 5, 'OWNER_NAME': 'SEAGROVE 1ST ADD', 'SUBDIVISION_NUMBER': '15-3S-19-25070'}, 'geometry': {'rings': ring_around(x, y, -10)}},
                            {'attributes': {'OBJECTID': 6, 'OWNER_NAME': 'SEAGROVE 3RD ADD', 'SUBDIVISION_NUMBER': None}, 'geometry': {'rings': ring_around(x, y, 20)}}]
            elif x == -86.13:
                features = [{'attributes': {'OBJECTID': 9, 'OWNER_NAME': 'INFORMATION ONLY', 'SUBDIVISION_NUMBER': '1'}, 'geometry': {'rings': ring_around(x, y, 12)}},
                            {'attributes': {'OBJECTID': 8, 'OWNER_NAME': 'SEAGROVE 3RD ADD', 'SUBDIVISION_NUMBER': '2'}, 'geometry': {'rings': ring_around(x, y, 12)}},
                            {'attributes': {'OBJECTID': 7, 'OWNER_NAME': 'FARTHER S/D', 'SUBDIVISION_NUMBER': '3'}, 'geometry': {'rings': ring_around(x, y, 60)}}]
            else:
                features = [{'attributes': {'OBJECTID': 4, 'OWNER_NAME': 'TOO FAR', 'SUBDIVISION_NUMBER': '4'}, 'geometry': {'rings': ring_around(x, y, 90)}}]
        return httpx.Response(200, json={'features': features})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rows = gen.query_subdivisions(beaches_, client, tmp_path / 'raw', pause=0)
    assert [(r['external_id'][0], r['alt_bolum_adi'], r['alt_bolum_numarasi'], r['poligon_kimligi'], r['iliski'], r['mesafe_m']) for r in rows] == [
        ('a', 'SEAGROVE 1ST ADD', '15-3S-19-25070', '5', 'iceride', '0'), ('a', 'SEAGROVE 3RD ADD', '', '6', 'yakin', '20.0'),
        ('b', 'SEAGROVE 3RD ADD', '2', '8', 'yakin', '12.0'), ('b', 'INFORMATION ONLY', '1', '9', 'yakin', '12.0'),
        ('b', 'FARTHER S/D', '3', '7', 'yakin', '60.0'), ('c', '', '', '', 'sonucsuz', '')]
    assert all(r['katman_url'] == LAYER and r['sorgu_zamani'] for r in rows)
    assert len(seen) == 6 and len(list((tmp_path / 'raw').iterdir())) == 6


def test_query_errors_stop_generation(tmp_path):
    beach_ = [{'external_id': 'a' * 24, 'name': 'A', 'latitude': 30.31, 'longitude': -86.14}]
    for response in (httpx.Response(500, text='down'), httpx.Response(200, json={'error': {'code': 400, 'message': 'bad'}}),
                     httpx.Response(200, json={'unexpected': True})):
        with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
            with pytest.raises(SystemExit):
                gen.query_subdivisions(beach_, client, tmp_path / 'raw', pause=0)


def test_polygon_distance_in_meters():
    rings = ring_around(-86.13, 30.31, 25)
    assert abs(gen.polygon_distance(30.31, -86.13, rings) - 25) < 0.05


def test_generator_end_to_end_reads_db_read_only_and_writes_loadable_file(tmp_path, monkeypatch):
    monkeypatch.setattr(n, 'REQUEST_GAP', 0)
    db = Database(tmp_path / 'studio.sqlite3'); db.initialize()
    source = next(s for s in db.sources() if s['url'] == beaches.SOURCE_URL)
    connector = beaches.BeachesConnector()
    beach_run = db.add_job('source_collection', 'Beaches', source['id'], connector)
    ids = [f'{0xabc0 + i:024x}' for i in range(4)]
    batch = beaches.parse_page(page(point(id=ids[0], name='West access', lng=-86.29), point(id=ids[1], name='Official access', lng=-86.145),
                                    point(id=ids[2], name='Middle access', lng=-86.10), point(id=ids[3], name='East access', lng=-86.061)))
    db.complete_source_run(beach_run, batch, connector)
    (tmp_path / 'hoods').mkdir()
    hood_run = save_run(db, run_mock(tmp_path / 'hoods').records)
    preview = preview_csv(tmp_path / 'preview.csv', [[ids[0], 'West access', '', ''], [ids[1], 'Official access', 'Seaside', gen.OFFICIAL_PREFIX + 'başlık: Seaside'],
                                                     [ids[2], 'Middle access', '', ''], [ids[3], 'East access', '', '']])
    subdivisions = write_csv(tmp_path / 'sub.csv', [sub(ids[0], 'VIZCAYA AT DUNE ALLEN S/D'), sub(ids[1], 'SEASIDE S/D'),
                                                    sub(ids[2], 'SEASIDE S/D', 'yakin', '30.0'), sub(ids[3], '', 'sonucsuz')], gen.SUBDIVISION_COLUMNS)
    table = write_csv(tmp_path / 'table.csv', [['VIZCAYA AT DUNE ALLEN S/D', 'dune-allen', 'adında DUNE ALLEN geçiyor'],
                                               ['SEASIDE S/D', 'seaside', 'adında SEASIDE geçiyor']], gen.TABLE_COLUMNS)
    previous = write_csv(tmp_path / 'v2.csv', [{**ROW, 'external_id': ids[0], 'bolge_id': 'gulf-place', 'yontem': bn.METHOD_DERIVED, 'kaynak': 'e' * 32}])
    before = (tmp_path / 'studio.sqlite3').read_bytes()
    out, check, diff = tmp_path / 'mapping.csv', tmp_path / 'check.csv', tmp_path / 'diff.csv'
    mapping, validation, conflicts, changes = gen.main(['--data-dir', str(tmp_path), '--resmi', str(preview), '--cikti', str(out),
                                                        '--dogrulama', str(check), '--alt-bolum', str(subdivisions), '--alt-bolum-tablosu', str(table),
                                                        '--onceki', str(previous), '--fark', str(diff)])
    assert (tmp_path / 'studio.sqlite3').read_bytes() == before
    rows = bn.load(out, CANONICAL)
    assert [(row['beach_name'], row['region_id'], row['method']) for row in rows] == [
        ('West access', 'dune-allen', bn.METHOD_COUNTY), ('Official access', 'seaside', bn.METHOD_OFFICIAL),
        ('Middle access', 'seaside', bn.METHOD_COUNTY_ADJACENT), ('East access', 'inlet-beach', bn.METHOD_DERIVED)]
    assert rows[3]['source'] == hood_run and 'Daha yakın Rosemary Beach' in rows[3]['note'] and 'Alys Beach' in rows[3]['note']
    with open(check, encoding='utf-8') as handle:
        assert [(row['external_id'], row['ilce_sonuc'], row['zincir_yontem']) for row in csv.DictReader(handle)] == [(ids[1], 'ayni', bn.METHOD_COUNTY)]
    with open(diff, encoding='utf-8') as handle:
        assert [(row['plaj_adi'], row['onceki_bolge_id'], row['yeni_bolge_id'], row['yeni_yontem']) for row in csv.DictReader(handle)][0] == (
            'West access', 'gulf-place', 'dune-allen', bn.METHOD_COUNTY)
    assert len(validation) == 1 and len(mapping) == 4 and conflicts == [] and len(changes) == 4


def test_generator_network_only_on_request(tmp_path, monkeypatch):
    monkeypatch.setattr(gen, 'read_inputs', lambda *args: ('beach-run', [{'external_id': 'a' * 24, 'name': 'A', 'latitude': 30.31, 'longitude': -86.14}],
                                                             'hood-run', WEST_EAST))
    with pytest.raises(SystemExit, match='--ham'):
        gen.main(['--data-dir', str(tmp_path), '--ilce-sorgula'])
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={'features': [{'attributes': {'OBJECTID': 3, 'OWNER_NAME': 'SEAGROVE 1ST ADD', 'SUBDIVISION_NUMBER': '1'}}]})
    out = tmp_path / 'sub.csv'
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        monkeypatch.setattr(gen, 'QUERY_GAP', 0)
        rows = gen.main(['--data-dir', str(tmp_path), '--ilce-sorgula', '--ham', str(tmp_path / 'raw'), '--yalniz-sorgu', '--alt-bolum', str(out)], client=client)
    assert len(calls) == 2 and [row['iliski'] for row in rows] == ['iceride']
    assert {key: len(value) for key, value in gen.read_subdivisions(out).items()} == {'a' * 24: 1}
