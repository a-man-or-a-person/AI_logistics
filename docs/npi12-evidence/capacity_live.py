"""Reuse the browser download driver on the measured 90,000-row safe fixture."""
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

root = Path.cwd()
sys.path[:0] = [str(root), str(root / 'tests')]
source, coords = root / '.scratch/npi12-measure/pulse.csv', root / '.scratch/npi12-measure/coords.json'
os.environ['LOGISTICS_CSV_FILE'] = str(source)
from test_xlsx_export_api import open_xlsx  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from backend.app import app  # noqa: E402
from backend.clustering_api import set_clustering_service  # noqa: E402
from backend.services.clustering_service import ClusteringService  # noqa: E402

service = ClusteringService(source, coordinate_cache_path=coords)
set_clustering_service(service)
output = root / 'docs/npi12-evidence/capacity'
output.mkdir(parents=True, exist_ok=True)
runtime = root / '.scratch/npi12-capacity'
runtime.mkdir(parents=True, exist_ok=True)
script = root.joinpath('docs/npi11-evidence/live_edge.mjs').read_text(encoding='utf8')
script = script[:script.index("  await click('#all-origins');")]
script = script.replace("const root=new URL('./',import.meta.url)", f'const root=new URL({json.dumps(output.as_uri() + "/")})')
script = script.replace('../../.scratch/npi11-edge-', '../../../.scratch/npi12-capacity-edge-')
script = script.replace('i<120', 'i<400')
script += """
  await click('#all-origins');await pause(200);
  await evaluate("(()=>{const r=document.getElementById('cluster-region');r.value='Region A';r.dispatchEvent(new Event('change',{bubbles:true}));})()");
  await waitFor("!document.getElementById('btn-run-clustering').disabled");
  const startRun=performance.now();await run();saved=last('run');assert.ok(saved);
  assert.equal(saved.analysis.origin_fiases.length,150);assert.equal(saved.points.length,300);
  assert.equal(saved.data_quality.source_row_count,90000);
  const runMilliseconds=performance.now()-startRun;
  const startExport=performance.now();await download();const exportMilliseconds=performance.now()-startExport;
  await record('90k-browser-complete');
  await writeFile(new URL('network.json',root),JSON.stringify({requests,responses,downloads},null,2));
  await writeFile(new URL('timings.json',root),JSON.stringify({runMilliseconds,exportMilliseconds,origins:150,destinations:300,sourceRows:90000},null,2));
  await send('Browser.close');
} finally {socket?.close();if(browser.exitCode===null)browser.kill();}
"""
driver = runtime / 'edge.mjs'
driver.write_text(script, encoding='utf8')
server = make_server('127.0.0.1', 0, app, threaded=True)
worker = threading.Thread(target=server.serve_forever, daemon=True)
worker.start()
try:
    env = {**os.environ, 'NPI11_BASE': f'http://127.0.0.1:{server.server_port}', 'NPI11_DOWNLOADS': str(runtime)}
    subprocess.run(['node', str(driver)], env=env, check=True, timeout=180)
    network = json.loads(output.joinpath('network.json').read_text(encoding='utf8'))
    assert len(network['downloads']) == 1
    content = runtime.joinpath(network['downloads'][0]['guid']).read_bytes()
    names, sheets = open_xlsx(content)
    records = [dict(zip(s[0], row, strict=True)) for s in sheets[1:-1] for row in s[1:]]
    assert len(records) == len({r['source_row_id'] for r in records}) == 90000
    assert sum(r['trip_count'] for r in records) == 90000
    output.joinpath('reopened.json').write_text(json.dumps({'status': 'PASS', 'bytes': len(content),
        'unique_rows': 90000, 'machines': 90000, 'sheets': names}), encoding='utf8')
finally:
    server.shutdown()
    worker.join()
