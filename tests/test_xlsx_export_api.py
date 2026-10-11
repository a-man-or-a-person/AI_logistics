"""Export acceptance through HTTP and an independent OOXML reader."""
import csv
import io
import json
import xml.etree.ElementTree as ET
import zipfile

import pytest
import test_origin_union_api
from test_clustering_product_api import _row

from ml.data.loader import PULSE_COLUMNS

payload = test_origin_union_api.payload
union_client = test_origin_union_api.union_client

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def open_xlsx(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        names = [s.attrib['name'] for s in ET.fromstring(archive.read('xl/workbook.xml')).findall('s:sheets/s:sheet', NS)]
        sheets = []
        for index in range(len(names)):
            root = ET.fromstring(archive.read(f'xl/worksheets/sheet{index + 1}.xml'))
            assert not root.findall('.//s:f', NS)
            rows = []
            for row in root.findall('s:sheetData/s:row', NS):
                values = []
                for cell in row.findall('s:c', NS):
                    if cell.attrib.get('t') == 'inlineStr':
                        values.append(''.join(t.text or '' for t in cell.findall('.//s:t', NS)))
                    else:
                        value = cell.find('s:v', NS)
                        values.append(float(value.text) if value is not None else None)
                rows.append(values)
            sheets.append(rows)
        assert not any('externalLink' in name or 'vba' in name.lower() for name in archive.namelist())
        return names, sheets


def export_request(run, **changes):
    return {**run['analysis']['frozen_request'], 'data_snapshot': run['data_snapshot'],
            'table_sort': {'key': 'trip_count', 'direction': 'desc'}, **changes}


def test_export_opens_and_explains_exact_saved_source_rows(union_client):
    client, _ = union_client
    run = client.post('/api/clustering/run', json=payload(origin_fiases=['a', 'b', 'c'])).get_json()
    response = client.post('/api/clustering/export', json=export_request(run), headers={'X-Request-ID': 'xlsx-test'})
    assert response.status_code == 200, response.get_json()
    assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert '.xlsx' in response.headers['Content-Disposition']
    assert response.headers['X-Request-ID'] == 'xlsx-test'
    names, sheets = open_xlsx(response.data)
    assert names[0] == 'Кластеры' and names[-1] == 'Контекст'
    assert sheets[0][0] == ['Кластер', 'Точки', 'Машины', 'Доля машин', 'Маршрут',
        'Мин. цена', 'Медианная цена', 'Ср.-взв. цена', 'Макс. цена',
        'Мин. ₽/км', 'Медианный ₽/км', 'Ср.-взв. ₽/км', 'Макс. ₽/км', 'Покрытие экономики']
    records = [dict(zip(sheet[0], row, strict=True)) for sheet in sheets[1:-1] for row in sheet[1:]]
    assert len(records) == len({r['source_row_id'] for r in records}) == 6
    assert sum(r['trip_count'] for r in records) == 75
    assert {r['origin_fias'] for r in records} == {'a', 'b'}
    assert any(r['price'] is None for r in records)
    assert all(',0%' in row[-1] for row in sheets[0][1:])
    x = [r for r in records if r['destination_fias'] == 'x']
    assert sum(r['trip_count'] for r in x) == 60
    assert {r['origin_region'] for r in x} == {'Origin Region', 'B Region', 'Регион погрузки не определён'}
    detail_ids = set()
    for point in run['points']:
        detail = client.post('/api/clustering/point-rows', json={**export_request(run), 'destination_fias': point['id']}).get_json()
        detail_ids.update(r['source_row_id'] for r in detail['rows'])
    assert {r['source_row_id'] for r in records} == detail_ids


@pytest.mark.parametrize('sort', [None, {}, {'key': [], 'direction': 'asc'},
    {'key': 'price', 'direction': 'asc'}, {'key': 'trip_count', 'direction': []}])
def test_invalid_sort_is_safe_typed_validation(union_client, sort):
    client, _ = union_client
    run = client.post('/api/clustering/run', json=payload()).get_json()
    response = client.post('/api/clustering/export', json=export_request(run, table_sort=sort))
    assert response.status_code == 400 and response.get_json()['code'] == 'INVALID_REQUEST'


@pytest.mark.parametrize('first_all', [True, False])
def test_all_and_manual_cache_reuse_preserves_both_saved_intents(union_client, first_all):
    client, _ = union_client
    all_request = payload()
    all_request.pop('origin_fiases')
    if not first_all:
        client.post('/api/clustering/run', json=payload(origin_fiases=['a', 'b', 'c']))
    all_run = client.post('/api/clustering/run', json={**all_request, 'all_origins': True}).get_json()
    manual = client.post('/api/clustering/run', json=all_run['analysis']['frozen_request']).get_json()
    ambiguous = client.post('/api/clustering/export', json=export_request(all_run))
    assert ambiguous.status_code == 400 and ambiguous.get_json()['code'] == 'INVALID_REQUEST'
    for run in (all_run, manual):
        response = client.post('/api/clustering/export', json=export_request(run, selection_intent=run['analysis']['selection_intent']))
        assert response.status_code == 200
        _, sheets = open_xlsx(response.data)
        assert json.loads(dict(sheets[-1][1:])['selection_intent']) == run['analysis']['selection_intent']


def append_rows(service, rows):
    with service.source_path.open('a', encoding='utf8', newline='') as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerows(rows)


def exported_records(response):
    assert response.status_code == 200, response.get_json()
    names, sheets = open_xlsx(response.data)
    return names, sheets, [dict(zip(sheet[0], row, strict=True)) for sheet in sheets[1:-1] for row in sheet[1:]]


def test_full_pages_literal_cells_precision_types_and_collision_mapping(union_client):
    client, service = union_client
    labels = ['=1+1', '+SUM(A1)', '-2+3', '@SUM(A1)', 'https://example.test', 'Регион погрузки не определён',
              "bad[]:*?/\\" + 'Я' * 60, "bad[]:*?/\\" + 'Я' * 59 + 'Ь', 'A' * 28 + "'B"]
    extra = []
    for i in range(60):
        row = _row('x', 'X', origin='a', origin_name=labels[i % len(labels)], trips='1',
                   price='1000.05' if i == 0 else '0', period_id='000123', tonnage='007',
                   tech_load_ts='2026-09-01T12:34:56+03:00')
        row['shipment_point_region'] = labels[i % len(labels)]
        extra.append(row)
    append_rows(service, extra)
    run = client.post('/api/clustering/run', json=payload()).get_json()
    names, sheets, records = exported_records(client.post('/api/clustering/export', json=export_request(run)))
    assert len(records) == len({r['source_row_id'] for r in records}) == 66
    assert sum(r['trip_count'] for r in records) == 135
    added = [r for r in records if r['period_id'] == '000123']
    assert len(added) == 60
    assert added[0]['tonnage_id'] == '007'
    assert all(r['source_timestamp'] == '2026-09-01T12:34:56+03:00' for r in added)
    assert {r['origin_name'] for r in added} == set(labels)
    assert sum(r['price'] == 0 for r in added) == 59
    assert next(r['price'] for r in added if r['price']) == 1000.05
    assert all(len(n) <= 31 and not any(c in n for c in '[]:*?/\\') for n in names)
    assert len({n.casefold() for n in names}) == len(names)
    context = dict(sheets[-1][1:])
    mapping = [json.loads(v) for k, v in context.items() if k.startswith('sheet:')]
    assert {m['origin_region'] for m in mapping} == set(labels) | {'Origin Region', 'B Region', None}
    assert 'conflicting_origin_regions:a' in context
    with zipfile.ZipFile(io.BytesIO(client.post('/api/clustering/export', json=export_request(run)).data)) as archive:
        assert not any(b'<hyperlink' in archive.read(n) for n in archive.namelist() if n.endswith('.xml'))
        for n in archive.namelist():
            if n.endswith('.xml'):
                ET.fromstring(archive.read(n))
        formats = archive.read('xl/styles.xml').decode()
        assert '0.0%' in formats and '₽' in formats


@pytest.mark.parametrize('mode', ['geography', 'geo_cost', 'geo_volume'])
def test_modes_reconcile_independent_valid_denominators_and_unassigned(union_client, mode):
    client, service = union_client
    append_rows(service, [_row('x', 'X', origin='b', trips='20', price='4500', route_length='')])
    run = client.post('/api/clustering/run', json=payload(mode=mode, parameters={})).get_json()
    _, sheets, records = exported_records(client.post('/api/clustering/export', json=export_request(run)))
    x = [r for r in records if r['destination_fias'] == 'x']
    assert sum(r['trip_count'] for r in x) == 80
    assert sum(r['route_length'] * r['trip_count'] for r in x if r['route_length']) == 10000
    assert sum(r['trip_count'] for r in x if r['route_length']) == 40
    assert sum(r['price'] * r['trip_count'] for r in x if r['price']) == 280000
    assert sum(r['trip_count'] for r in x if r['price']) == 60
    assert sum(r['rub_per_km'] * r['trip_count'] for r in x if r['rub_per_km']) == 700
    assert sum(r['trip_count'] for r in x if r['rub_per_km']) == 40
    summary = client.post('/api/clustering/point-origins', json={**export_request(run), 'destination_fias': 'x'}).get_json()['origins']
    assert [o['valid_price_trip_count'] for o in summary] == [10, 50]
    context = dict(sheets[-1][1:])
    assert json.loads(context['frozen_request'])['mode'] == mode
    assert ('y' not in {r['destination_fias'] for r in records}) == (mode == 'geo_cost')
    if mode == 'geo_cost':
        assert {p['destination_fias']: p['status'] for p in json.loads(context['exclusions'])} == {'y': 'economic_unavailable', 'z': 'spatial_outlier'}
    assert sum(row[2] for row in sheets[0][1:]) == (85 if mode == 'geo_cost' else 95)


def test_regional_all_resolved_set_beyond_suggestions_and_zero_match(union_client):
    client, service = union_client
    append_rows(service, [_row('x', 'X', origin=f'000{i:03}', trips='1') for i in range(120)])
    request = payload()
    request.pop('origin_fiases')
    run = client.post('/api/clustering/run', json={**request, 'all_origins': True}).get_json()
    assert len(client.get('/api/clustering/origins?limit=100').get_json()) == 100
    _, sheets, records = exported_records(client.post('/api/clustering/export', json=export_request(run)))
    assert len(records) == 126
    assert len({r['origin_fias'] for r in records}) == 122
    context = dict(sheets[-1][1:])
    assert len(json.loads(context['frozen_request'])['origin_fiases']) == 123
    assert json.loads(context['selection_intent']) == {'all_origins': True}
    assert json.loads(context['origin_coverage'])[-1]['zero_match'] is True


@pytest.mark.parametrize('change,status,code', [
    ({'data_snapshot': 'old'}, 409, 'STALE_DATA_SNAPSHOT'),
    ({'origin_fiases': ['a']}, 409, 'RESULT_UNAVAILABLE'),
    ({'mode': 'geo_volume'}, 409, 'RESULT_UNAVAILABLE'),
    ({'parameters': {'k_mode': 'manual', 'n_clusters': 3}}, 409, 'RESULT_UNAVAILABLE'),
    ({'selection_intent': {'all_origins': True}}, 400, 'INVALID_REQUEST'),
    ({'all_origins': True}, 400, 'INVALID_REQUEST'),
])
def test_export_does_not_substitute_saved_identity(union_client, change, status, code):
    client, _ = union_client
    run = client.post('/api/clustering/run', json=payload()).get_json()
    response = client.post('/api/clustering/export', json=export_request(run, **change))
    assert response.status_code == status and response.get_json()['code'] == code
    assert 'Content-Disposition' not in response.headers


@pytest.mark.parametrize('mode', ['bear_zones', 'bear_volume_zones'])
def test_bear_export_is_explicitly_unsupported(union_client, mode):
    client, _ = union_client
    run = client.post('/api/clustering/run', json=payload(mode=mode, parameters={})).get_json()
    response = client.post('/api/clustering/export', json=export_request(run))
    assert response.status_code == 422 and response.get_json()['code'] == 'EXPORT_UNSUPPORTED'


@pytest.mark.parametrize('change', ['eviction', 'restart', 'source', 'coordinates'])
def test_unavailable_or_stale_export_never_reruns(union_client, change):
    from backend.clustering_api import set_clustering_service
    from backend.services.clustering_service import ClusteringService
    client, service = union_client
    run = client.post('/api/clustering/run', json=payload()).get_json()
    if change == 'eviction':
        service._result_cache.clear()
    elif change == 'restart':
        set_clustering_service(ClusteringService(service.source_path, coordinate_cache_path=service.coordinate_cache_path))
    else:
        path = service.source_path if change == 'source' else service.coordinate_cache_path
        with path.open('a', encoding='utf8') as stream:
            stream.write('\n')
    response = client.post('/api/clustering/export', json=export_request(run))
    assert response.status_code == 409
    assert response.get_json()['code'] == ('RESULT_UNAVAILABLE' if change in ('eviction', 'restart') else 'STALE_DATA_SNAPSHOT')


@pytest.mark.parametrize('moment', ['read', 'complete'])
@pytest.mark.parametrize('generation', ['source', 'coordinates'])
def test_generation_replacement_during_export_discards_whole_file(union_client, monkeypatch, moment, generation):
    import backend.services.clustering_service as module
    client, service = union_client
    run = client.post('/api/clustering/run', json=payload()).get_json()
    path = service.source_path if generation == 'source' else service.coordinate_cache_path
    def replace_file():
        replacement = path.with_suffix('.replacement')
        replacement.write_bytes(path.read_bytes() + b'\n')
        replacement.replace(path)
    if moment == 'read':
        original = service.repository.source_rows
        def raced(**kwargs):
            rows = original(**kwargs)
            replace_file()
            return rows
        monkeypatch.setattr(service.repository, 'source_rows', raced)
    else:
        original = module.write_workbook
        def raced(*args):
            file = original(*args)
            replace_file()
            return file
        monkeypatch.setattr(module, 'write_workbook', raced)
    response = client.post('/api/clustering/export', json=export_request(run))
    assert response.status_code == 409 and response.get_json()['code'] == 'STALE_DATA_SNAPSHOT'
    assert 'Content-Disposition' not in response.headers


@pytest.mark.parametrize('problem,code', [('empty', 'EXPORT_INCONSISTENT_DATA'), ('partial', 'EXPORT_INCONSISTENT_DATA'), ('write', 'EXPORT_FAILED')])
def test_incomplete_data_and_writer_failures_are_safe_json(union_client, monkeypatch, problem, code):
    import xlsxwriter
    client, service = union_client
    run = client.post('/api/clustering/run', json=payload()).get_json()
    if problem in ('empty', 'partial'):
        original = service.repository.source_rows
        monkeypatch.setattr(service.repository, 'source_rows', lambda **kwargs: [] if problem == 'empty' else (original(**kwargs)[1:] if kwargs['destination_fias'] == 'x' else original(**kwargs)))
    else:
        def fail(*args):
            raise OSError('PRIVATE C:/secret/source.csv token=secret')
        monkeypatch.setattr(xlsxwriter.Workbook, 'close', fail)
    response = client.post('/api/clustering/export', json=export_request(run), headers={'X-Request-ID': 'failed'})
    assert response.status_code == (409 if problem != 'write' else 500)
    assert response.get_json()['code'] == code and response.headers['X-Request-ID'] == 'failed'
    assert b'secret' not in response.data and 'Content-Disposition' not in response.headers


def test_comparison_variants_and_scalar_frozen_identity(union_client):
    client, _ = union_client
    comparison = client.post('/api/clustering/compare', json=payload()).get_json()
    for mode, run in comparison['results'].items():
        response = client.post('/api/clustering/export', json=export_request(run))
        if mode.startswith('bear'):
            assert response.status_code == 422
            continue
        _, sheets, records = exported_records(response)
        assert json.loads(dict(sheets[-1][1:])['frozen_request']) == run['analysis']['frozen_request']
        assert {r['destination_fias'] for r in records} == {p for row in run['cluster_table']['rows'] for p in row['point_ids']}
    scalar = payload()
    scalar.pop('origin_fiases')
    scalar['origin_fias'] = 'a'
    run = client.post('/api/clustering/run', json=scalar).get_json()
    _, _, records = exported_records(client.post('/api/clustering/export', json={**scalar,
        'data_snapshot': run['data_snapshot'], 'table_sort': {'key': 'cluster_id', 'direction': 'asc'}}))
    assert len(records) == 3 and {r['origin_fias'] for r in records} == {'a'}


@pytest.mark.parametrize('value', ['x' * 32768, 'nan', 'inf'], ids=['long-text', 'nan', 'inf'])
def test_unserializable_source_fails_without_truncation_or_partial_attachment(union_client, value):
    client, service = union_client
    row = _row('x', 'X', origin='a', origin_name=value if value.startswith('x') else 'A',
               price=value if not value.startswith('x') else '1000')
    append_rows(service, [row])
    run = client.post('/api/clustering/run', json=payload()).get_json()
    assert run.get('ok'), run
    response = client.post('/api/clustering/export', json=export_request(run))
    if value == 'nan':
        _, _, records = exported_records(response)
        assert any(r['price'] is None for r in records)
        return
    assert response.status_code == 500 and response.get_json()['code'] == 'EXPORT_FAILED'
    assert 'Content-Disposition' not in response.headers


def test_table_sort_uses_raw_values_null_last_and_cluster_ties(union_client):
    client, _ = union_client
    run = client.post('/api/clustering/run', json=payload(parameters={'k_mode': 'manual', 'n_clusters': 4})).get_json()
    # Singleton x/w/y/z: route250/100/200/100; x4750, w/z1000, y unavailable.
    expected = [('weighted_route_length', 'asc', ['Кластер 2', 'Кластер 3', 'Кластер 4', 'Кластер 1']),
                ('price.weighted', 'desc', ['Кластер 1', 'Кластер 2', 'Кластер 3', 'Кластер 4'])]
    for key, direction, labels in expected:
        _, sheets, _ = exported_records(client.post('/api/clustering/export', json=export_request(run,
            table_sort={'key': key, 'direction': direction})))
        assert [row[0] for row in sheets[0][1:]] == labels


def test_missing_frozen_fields_are_rejected(union_client):
    client, _ = union_client
    run = client.post('/api/clustering/run', json=payload()).get_json()
    for key in ('mode', 'parameters', 'data_snapshot', 'table_sort', 'period_types', 'price_types', 'vehicle_types', 'tonnage_ids'):
        request = export_request(run)
        request.pop(key)
        response = client.post('/api/clustering/export', json=request)
        assert response.status_code == 400 and response.get_json()['code'] == 'INVALID_REQUEST'


def test_truncated_region_apostrophe_is_a_legal_sheet_name(union_client):
    client, service = union_client
    row = _row('x', 'X', origin='a', trips='1', period_id='202612')
    row['shipment_point_region'] = 'A' * 28 + "'B"
    append_rows(service, [row])
    run = client.post('/api/clustering/run', json=payload()).get_json()
    names, _, records = exported_records(client.post('/api/clustering/export', json=export_request(run)))
    assert all(not name.endswith("'") for name in names)
    assert any(r['origin_region'] == row['shipment_point_region'] for r in records)
