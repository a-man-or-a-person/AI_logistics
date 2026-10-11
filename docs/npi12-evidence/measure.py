"""Deterministic synthetic All capacity observations, never a production SLA."""
import csv
import ctypes
import json
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

started = time.perf_counter()
root = Path.cwd()
sys.path[:0] = [str(root), str(root / 'tests')]
from test_clustering_product_api import _row  # noqa: E402
from test_origin_union_api import payload, union_client  # noqa: E402
from test_xlsx_export_api import append_rows, export_request, open_xlsx  # noqa: E402

from backend.app import app  # noqa: E402
from backend.clustering_api import set_clustering_service  # noqa: E402
from backend.services.clustering_service import ClusteringService  # noqa: E402
from ml.data.loader import PULSE_COLUMNS  # noqa: E402


def memory_mib():
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('peak', 'working', 'pool_peak', 'pool',
                                                'nonpaged_peak', 'nonpaged', 'page', 'page_peak')]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi')
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    assert psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return {'working_mib': round(counters.working / 2**20, 2), 'peak_mib': round(counters.peak / 2**20, 2)}


runtime = root / '.scratch/npi12-measure'
runtime.mkdir(parents=True, exist_ok=True)
report = {'import_seconds': time.perf_counter() - started, 'math': {}, 'scales': []}
with tempfile.TemporaryDirectory(dir=runtime) as directory:
    fixture = union_client.__wrapped__(Path(directory))
    client, service = next(fixture)
    try:
        append_rows(service, [_row('x', 'X', origin='b', trips='20', price='4500', route_length='')])
        result = client.post('/api/clustering/run', json=payload()).get_json()
        x = next(p for p in result['points'] if p['id'] == 'x')
        # Hand arithmetic: distance (10*100+30*300)/40; price (10*1000+30*6000+20*4500)/60.
        assert x['trip_count'] == 80
        assert x['weighted_route_length'] == 250 and x['valid_route_length_trip_count'] == 40
        assert abs(x['weighted_price'] - 4666.666666666667) < 1e-9
        assert x['valid_price_trip_count'] == 60
        assert x['weighted_rub_per_km'] == 17.5 and x['valid_rub_per_km_trip_count'] == 40
        response = client.post('/api/clustering/export', json=export_request(result))
        assert response.status_code == 200
        names, sheets = open_xlsx(response.data)
        rows = [dict(zip(s[0], row, strict=True)) for s in sheets[1:-1] for row in s[1:]]
        assert len(rows) == len({r['source_row_id'] for r in rows}) == 7
        assert sum(r['trip_count'] for r in rows) == 95
        report['math'] = {'status': 'PASS', 'point': x, 'source_rows': 7, 'machines': 95,
                          'sheets': names, 'route_numerator': 10000, 'price_numerator': 280000,
                          'rate_numerator': 700, 'valid_weights': {'route': 40, 'price': 60, 'rate': 40}}
    finally:
        next(fixture, None)

for origins, destinations, repetitions in ((34, 12, 1), (100, 100, 2), (150, 300, 2)):
    source, coords = runtime / 'pulse.csv', runtime / 'coords.json'
    with source.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        for origin in range(origins):
            for destination in range(destinations):
                for _ in range(repetitions):
                    writer.writerow(_row(f'd{destination:04}', f'Destination {destination}',
                                         origin=f'o{origin:04}', trips='1', price='1000', route_length='100'))
    coords.write_text(json.dumps({f'Destination {i}::Region A': [55 + i // 20 * .02, 37 + i % 20 * .02]
                                 for i in range(destinations)}), encoding='utf8')
    t = time.perf_counter()
    service = ClusteringService(source, coordinate_cache_path=coords)
    set_clustering_service(service)
    app.config['TESTING'] = True
    client = app.test_client()
    response = client.get('/api/clustering/options?all_origins=true&destination_region=Region+A')
    assert response.status_code == 200
    catalog_seconds = time.perf_counter() - t
    request = payload(all_origins=True, parameters={'k_mode': 'auto', 'n_clusters': 'auto'})
    request.pop('origin_fiases')
    t = time.perf_counter()
    response = client.post('/api/clustering/run', json=request)
    run_seconds = time.perf_counter() - t
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert len(result['analysis']['origin_fiases']) == origins and len(result['points']) == destinations
    row_count = origins * destinations * repetitions
    assert result['data_quality']['source_row_count'] == row_count
    assigned = [p for p in result['points'] if p['cluster_id'] is not None and p['cluster_id'] >= 0]
    assigned_rows = origins * len(assigned) * repetitions
    assert sum(r['trip_count'] for r in result['cluster_table']['rows']) == assigned_rows
    t = time.perf_counter()
    response = client.post('/api/clustering/export', json=export_request(result))
    export_seconds = time.perf_counter() - t
    assert response.status_code == 200, response.get_json()
    content = response.data
    t = time.perf_counter()
    _, sheets = open_xlsx(content)
    reopened_rows = sum(len(s) - 1 for s in sheets[1:-1])
    assert reopened_rows == assigned_rows
    item = {'origins': origins, 'destinations': destinations, 'source_rows': row_count,
            'assigned_destinations': len(assigned), 'excluded_source_rows': row_count - assigned_rows,
            'catalog_load_seconds': catalog_seconds, 'run_seconds': run_seconds,
            'export_seconds': export_seconds, 'reopen_seconds': time.perf_counter() - t,
            'workbook_bytes': len(content), 'reopened_rows': reopened_rows, **memory_mib()}
    report['scales'].append(item)
    (root / 'docs/npi12-evidence/measurements.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(item), flush=True)
set_clustering_service(None)
