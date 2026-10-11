from __future__ import annotations

import csv

import pytest
import test_origin_union_api
from test_clustering_product_api import _row

from ml.data.loader import PULSE_COLUMNS

union_client = test_origin_union_api.union_client
payload = test_origin_union_api.payload


def test_point_summary_reconciles_contributors_with_saved_pooled_point(union_client):
    client, _ = union_client
    run = client.post('/api/clustering/run', json=payload(origin_fiases=['a', 'b', 'c'])).get_json()
    response = client.post('/api/clustering/point-origins', json={
        **run['analysis']['frozen_request'], 'data_snapshot': run['data_snapshot'],
        'destination_fias': 'x'}, headers={'X-Request-ID': 'summary'})
    assert response.status_code == 200, response.get_json()
    assert response.headers['X-Request-ID'] == 'summary'
    summary = response.get_json()
    assert summary['data_snapshot'] == run['data_snapshot']
    point = next(p for p in run['points'] if p['id'] == 'x')
    assert summary['cluster_id'] == point['cluster_id']
    origins = {o['origin_fias']: o for o in summary['origins']}
    assert set(origins) == {'a', 'b'}
    a, b = origins['a'], origins['b']
    assert (a['trip_count'], a['source_row_count'], a['weighted_route_length'],
            a['weighted_price'], a['weighted_rub_per_km']) == (10, 1, 100, 1000, 10)
    assert (b['trip_count'], b['source_row_count'], b['weighted_route_length'],
            b['weighted_price'], b['weighted_rub_per_km']) == (50, 2, 300, 6000, 20)
    assert (a['valid_route_length_trip_count'], a['valid_price_trip_count']) == (10, 10)
    assert (b['valid_route_length_trip_count'], b['valid_price_trip_count']) == (30, 30)
    assert b['origin_regions'] == ['B Region', None]
    assert a['origin_name'] == 'b Warehouse'
    assert sum(o['trip_count'] for o in origins.values()) == point['trip_count'] == 60
    assert point['weighted_route_length'] == 250
    assert point['weighted_price'] == 4750
    assert run['analysis']['origin_coverage'][-1]['zero_match'] is True


def detail_request(run, destination='x'):
    return {**run['analysis']['frozen_request'], 'data_snapshot': run['data_snapshot'],
            'destination_fias': destination}


def test_summary_uses_independent_valid_weights_and_preserves_missing_metrics(union_client):
    client, service = union_client
    with service.source_path.open('a', encoding='utf8', newline='') as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerow(
            _row('x', 'X', origin='b', trips='20', price='4500', route_length=''))
    run = client.post('/api/clustering/run', json=payload()).get_json()
    request = detail_request(run)
    origins = client.post('/api/clustering/point-origins', json=request).get_json()['origins']
    b = origins[1]
    assert (b['trip_count'], b['weighted_route_length'], b['weighted_price'], b['weighted_rub_per_km']) == (70, 300, 5400, 20)
    assert (b['valid_route_length_trip_count'], b['valid_price_trip_count'], b['valid_rub_per_km_trip_count']) == (30, 50, 30)
    y = client.post('/api/clustering/point-origins', json=detail_request(run, 'y')).get_json()['origins']
    assert len(y) == 1 and y[0]['origin_fias'] == 'a'
    assert (y[0]['trip_count'], y[0]['weighted_route_length'], y[0]['weighted_price'],
            y[0]['valid_route_length_trip_count'], y[0]['valid_price_trip_count']) == (5, 200, None, 5, 0)
    point = next(p for p in run['points'] if p['id'] == 'x')
    assert (point['trip_count'], point['weighted_route_length'], point['weighted_price']) == (80, 250, pytest.approx(4666.666666666667))
    assert sum(o['valid_price_trip_count'] for o in origins) == point['valid_price_trip_count'] == 60
    assert sum(row['trip_count'] for row in run['cluster_table']['rows']) == 95


@pytest.mark.parametrize('mode', ['geography', 'geo_cost', 'geo_volume', 'bear_zones', 'bear_volume_zones'])
def test_summary_and_origin_detail_join_exact_saved_membership(union_client, mode):
    client, _ = union_client
    run = client.post('/api/clustering/run', json=payload(mode=mode, parameters={})).get_json()
    for point in run['points']:
        request = detail_request(run, point['id'])
        summary = client.post('/api/clustering/point-origins', json=request).get_json()
        assert (summary['cluster_id'], summary['status']) == (point['cluster_id'], point['status'])
        assert sum(o['trip_count'] for o in summary['origins']) == point['trip_count']
        for origin in summary['origins']:
            rows = client.post('/api/clustering/point-rows', json={**request, 'detail_origin_fias': origin['origin_fias']}).get_json()
            assert rows['total'] == origin['source_row_count']
            assert all(r['cluster_id'] == point['cluster_id'] and r['origin_fias'] == origin['origin_fias'] for r in rows['rows'])


@pytest.mark.parametrize('change,status,code', [
    ({'origin_fiases': ['a']}, 409, 'RESULT_UNAVAILABLE'),
    ({'mode': 'geo_volume'}, 409, 'RESULT_UNAVAILABLE'),
    ({'parameters': {'k_mode': 'manual', 'n_clusters': 3}}, 409, 'RESULT_UNAVAILABLE'),
    ({'destination_fias': 'missing'}, 422, 'UNKNOWN_DESTINATION_POINT'),
    ({'data_snapshot': 'old'}, 409, 'STALE_DATA_SNAPSHOT'),
    ({'all_origins': True}, 400, 'INVALID_REQUEST'),
])
def test_summary_never_substitutes_a_result(union_client, change, status, code):
    client, _ = union_client
    run = client.post('/api/clustering/run', json=payload()).get_json()
    response = client.post('/api/clustering/point-origins', json={**detail_request(run), **change})
    assert response.status_code == status
    assert response.get_json()['code'] == code


def test_summary_requires_saved_context_and_rejects_eviction_and_new_generation(union_client):
    client, service = union_client
    scalar = payload()
    scalar.pop('origin_fiases')
    scalar['origin_fias'] = 'a'
    run = client.post('/api/clustering/run', json=scalar).get_json()
    request = {**scalar, 'data_snapshot': run['data_snapshot'], 'destination_fias': 'x'}
    assert client.post('/api/clustering/point-origins', json=request).get_json()['origins'][0]['trip_count'] == 10
    for name in ('mode', 'parameters', 'period_types'):
        incomplete = dict(request)
        incomplete.pop(name)
        assert client.post('/api/clustering/point-origins', json=incomplete).status_code == 400
    service._result_cache.clear()
    assert client.post('/api/clustering/point-origins', json=request).get_json()['code'] == 'RESULT_UNAVAILABLE'
    client.post('/api/clustering/run', json=scalar)
    with service.source_path.open('a', encoding='utf8') as stream:
        stream.write('\n')
    assert client.post('/api/clustering/point-origins', json=request).get_json()['code'] == 'STALE_DATA_SNAPSHOT'


@pytest.mark.parametrize('generation', ['source', 'coordinates'])
def test_summary_rejects_generation_change_during_read(union_client, monkeypatch, generation):
    client, service = union_client
    run = client.post('/api/clustering/run', json=payload()).get_json()
    read = service.repository.source_rows
    def change(**kwargs):
        rows = read(**kwargs)
        path = service.source_path if generation == 'source' else service.coordinate_cache_path
        with path.open('a', encoding='utf8') as stream:
            stream.write('\n')
        return rows
    monkeypatch.setattr(service.repository, 'source_rows', change)
    response = client.post('/api/clustering/point-origins', json=detail_request(run))
    assert response.status_code == 409 and response.get_json()['code'] == 'STALE_DATA_SNAPSHOT'


def test_all_summary_uses_complete_frozen_set_and_never_caps_contributors(union_client):
    client, service = union_client
    with service.source_path.open('a', encoding='utf8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writerows(_row('x', 'X', origin=f'extra-{i:02}', trips='1', price='2000', route_length='200') for i in range(31))
    request = payload()
    request.pop('origin_fiases')
    run = client.post('/api/clustering/run', json={**request, 'all_origins': True}).get_json()
    assert len(run['analysis']['origin_fiases']) == 34
    assert len(client.get('/api/clustering/origins?limit=30').get_json()) == 30
    summary = client.post('/api/clustering/point-origins', json=detail_request(run)).get_json()
    assert len(summary['origins']) == 33
    assert sum(o['trip_count'] for o in summary['origins']) == 91
    point = next(p for p in run['points'] if p['id'] == 'x')
    assert point['weighted_route_length'] == pytest.approx(228.16901408450704)
    assert point['valid_route_length_trip_count'] == 71
