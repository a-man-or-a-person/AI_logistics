"""Real localhost Flask download, synthetic Pulse only; independently reopen OOXML."""
import hashlib
import json
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from werkzeug.serving import make_server

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root), str(root / 'tests')]

from test_clustering_product_api import _row  # noqa: E402
from test_origin_union_api import payload, union_client  # noqa: E402
from test_xlsx_export_api import append_rows, export_request, open_xlsx  # noqa: E402

from backend.app import app  # noqa: E402

runtime = root / '.scratch/npi10-runtime'
runtime.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=runtime) as directory:
    fixture = union_client.__wrapped__(Path(directory))
    _, service = next(fixture)
    append_rows(service, [_row('x', 'X', origin=f'000{i:03}', trips='1') for i in range(120)])
    append_rows(service, [_row('x', 'X', origin='a', trips='1', origin_name='=1+1', price='1000.05') for _ in range(60)])
    server = make_server('127.0.0.1', 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}/api/clustering'

    def post(endpoint, data):
        return urllib.request.urlopen(urllib.request.Request(base + endpoint,
            data=json.dumps(data).encode(), headers={'Content-Type': 'application/json', 'X-Request-ID': 'npi10-real-http'}), timeout=30)

    try:
        request = payload()
        request.pop('origin_fiases')
        started = time.perf_counter()
        with post('/run', {**request, 'all_origins': True}) as response:
            run = json.load(response)
        calculation_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        with post('/export', export_request(run)) as response:
            headers = dict(response.headers)
            content = response.read()
        export_ms = (time.perf_counter() - started) * 1000
        path = runtime / 'downloaded-product.xlsx'
        path.write_bytes(content)
        names, sheets = open_xlsx(path.read_bytes())
        records = [dict(zip(sheet[0], row, strict=True)) for sheet in sheets[1:-1] for row in sheet[1:]]
        assert len(records) == len({r['source_row_id'] for r in records}) == 186
        assert sum(r['trip_count'] for r in records) == 255
        assert sum(row[2] for row in sheets[0][1:]) == 255
        assert sum(r['origin_name'] == '=1+1' for r in records) == 60
        observations = {'transport': 'real localhost Flask HTTP', 'fixture': 'synthetic only',
            'origins': len(run['analysis']['origin_fiases']), 'destinations': len(run['points']),
            'source_rows': len(records), 'unique_row_ids': len({r['source_row_id'] for r in records}),
            'machines': 255, 'sheets': names, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
            'headers': headers, 'calculation_ms': calculation_ms, 'export_ms': export_ms,
            'structural_check': 'ZIP CRC, sheet XML, types/values, no formulas/macros/external links; independent stdlib reader',
            'limits': 'Synthetic counts/timings; production capacity and human Excel acceptance unverified'}
        (root / 'docs/npi10-evidence/http-download.json').write_text(json.dumps(observations, ensure_ascii=False, indent=2), encoding='utf8')
        print(json.dumps(observations))
    finally:
        server.shutdown()
        thread.join()
        next(fixture, None)
