"""Headed Edge + real Flask, synthetic Pulse; reopen actual browser downloads."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from flask import request
from werkzeug.serving import make_server

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root), str(root / 'tests')]

from test_clustering_product_api import _row  # noqa: E402
from test_origin_union_api import union_client  # noqa: E402
from test_xlsx_export_api import append_rows, open_xlsx  # noqa: E402

import backend.data_processor as data_processor  # noqa: E402
import backend.services.clustering_service as service_module  # noqa: E402
from backend.app import app  # noqa: E402
from backend.clustering_api import set_clustering_service  # noqa: E402
from backend.services.clustering_service import ClusteringService  # noqa: E402

runtime = root / '.scratch/npi11-live'
runtime.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=runtime) as directory:
    fixture = union_client.__wrapped__(Path(directory))
    _, service = next(fixture)
    os.environ['LOGISTICS_CSV_FILE'] = str(service.source_path)
    data_processor.CSV_FILE = str(service.source_path)
    append_rows(service, [_row('x', 'X', origin='b', trips='20', price='4500', route_length='')])
    append_rows(service, [_row('x', 'X', origin='a', trips='1', price='', route_length='', origin_name='=1+1') for _ in range(60)])
    control = {'service': service, 'failure': None}
    original_writer = service_module.write_workbook

    def controlled_writer(*args):
        failure, control['failure'] = control['failure'], None
        if failure == 'writer':
            raise OSError('Synthetic resource failure')
        output = original_writer(*args)
        if failure == 'during':
            append_rows(control['service'], [_row('x', 'X', origin='new', trips='1')])
        return output

    service_module.write_workbook = controlled_writer

    @app.after_request
    def attachment_checksum(response):
        if request.path == '/api/clustering/export' and response.status_code == 200:
            attachment = response.response.file
            position = attachment.tell()
            response.headers['X-Fixture-SHA256'] = hashlib.file_digest(attachment, 'sha256').hexdigest()
            attachment.seek(position)
        return response

    @app.post('/fixture/fail/<kind>')
    def fail(kind):
        assert kind in ('writer', 'during')
        control['failure'] = kind
        return {'ok': True}

    @app.post('/fixture/change')
    def change():
        append_rows(control['service'], [_row('x', 'X', origin='new', trips='1')])
        return {'ok': True}

    @app.post('/fixture/restart')
    def restart():
        control['service'] = ClusteringService(service.source_path, coordinate_cache_path=service.coordinate_cache_path)
        set_clustering_service(control['service'])
        return {'ok': True}

    server = make_server('127.0.0.1', 0, app, threaded=True)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    env = {**os.environ, 'NPI11_BASE': f'http://127.0.0.1:{server.server_port}',
           'NPI11_DOWNLOADS': str(runtime.resolve())}
    try:
        subprocess.run(['node', str(Path(__file__).with_name('live_edge.mjs'))], env=env, check=True, timeout=240)
        network = json.loads(Path(__file__).with_name('network.json').read_text(encoding='utf8'))
        observations = []
        for item in network['downloads']:
            path = runtime / item['guid']
            content = path.read_bytes()
            names, sheets = open_xlsx(content)
            context = dict(sheets[-1][1:])
            frozen = json.loads(context['frozen_request'])
            records = [dict(zip(sheet[0], row, strict=True)) for sheet in sheets[1:-1] for row in sheet[1:]]
            mode = frozen['mode']
            saved = item['saved']
            assert frozen == saved['analysis']['frozen_request']
            assert context['data_snapshot'] == saved['data_snapshot']
            assert json.loads(context['selection_intent']) == saved['analysis']['selection_intent']
            assert [row[0] for row in sheets[0][1:]] == item['tableLabels']
            assert sheets[0][0] == item['headers']
            if not item.get('after_change'):
                assert len(records) == len({r['source_row_id'] for r in records}) == (65 if mode == 'geo_cost' else 67)
                assert sum(r['trip_count'] for r in records) == (145 if mode == 'geo_cost' else 155)
                x = [r for r in records if r['destination_fias'] == 'x']
                assert sum(r['trip_count'] for r in x) == 140
                assert sum(r['route_length'] * r['trip_count'] for r in x if r['route_length']) == 10000
                assert sum(r['price'] * r['trip_count'] for r in x if r['price']) == 280000
                assert sum(r['rub_per_km'] * r['trip_count'] for r in x if r['rub_per_km']) == 700
                assert sum(r['origin_name'] == '=1+1' for r in records) == 60
            assigned = {p['id']: p['cluster_id'] for p in saved['points'] if p['cluster_id'] is not None and p['cluster_id'] >= 0}
            assert all(r['cluster_id'] == f"Кластер {assigned[r['destination_fias']] + 1}" for r in records)
            observations.append({'filename': item['suggestedFilename'], 'bytes': len(content),
                'sha256': hashlib.sha256(content).hexdigest(), 'mode': mode, 'sheets': names,
                'rows': len(records), 'unique_ids': len({r['source_row_id'] for r in records}),
                'intent': saved['analysis']['selection_intent'], 'sort': json.loads(context['table_sort']),
                'independent_reopen': 'PASS: ZIP CRC/XML values/types, exact table headers/order, membership, frozen context, no formulas/macros/external links'})
        assert len(observations) >= 5
        Path(__file__).with_name('workbook-inspection.json').write_text(json.dumps(observations, ensure_ascii=False, indent=2), encoding='utf8')
        print(json.dumps({'inspected_downloads': len(observations), 'status': 'PASS'}))
    finally:
        server.shutdown()
        worker.join()
        next(fixture, None)
        service_module.write_workbook = original_writer
