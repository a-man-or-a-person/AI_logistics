"""Repeat existing headed acceptance drivers against the combined candidate."""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('scenario', choices=['navigation', 'freshness', 'medoid', 'selection', 'all'])
args = parser.parse_args()
root = Path.cwd()
sources = {'navigation': ('npi08', 5068, 5078), 'freshness': ('pulse-freshness', 5069, 5079),
           'medoid': ('npi09', 5069, 5080), 'selection': ('npi04', 5064, 5081),
           'all': ('npi05', 5065, 5083)}
name, old_port, port = sources[args.scenario]
original = root / 'docs' / f'{name}-evidence'
output = root / 'docs/npi12-evidence' / args.scenario
output.mkdir(parents=True, exist_ok=True)
server = original.joinpath('live_server.py').read_text(encoding='utf8')
driver = original.joinpath('live_edge.mjs').read_text(encoding='utf8')
server = server.replace(f'port={old_port}', f'port={port}')
server = server.replace(f'.scratch/{name}', f'.scratch/npi12-{args.scenario}')
driver = driver.replace(f':{old_port}', f':{port}')
driver = driver.replace("const root = new URL('./', import.meta.url);",
                        f'const root = new URL({json.dumps(output.as_uri() + "/")});')
driver = driver.replace("const root=new URL('./',import.meta.url);",
                        f'const root=new URL({json.dumps(output.as_uri() + "/")});')
driver = driver.replace('../../.scratch/', '../../../.scratch/')
driver = driver.replace("document.querySelector('[data-point-id=\"${id}\"]')`)",
                        "document.querySelector('[data-point-id=\"${id}\"]')?.offsetParent`)")
driver = driver.replace("['--headless=new', ", "[")
driver = driver.replace(f"const root = new URL('../../../.scratch/{name}-evidence/', import.meta.url);",
                        f'const root = new URL({json.dumps(output.as_uri() + "/")});')
driver = driver.replace('const profile = new URL(`live-edge-${Date.now()}/`, root);',
                        'const profile = new URL(`../../../.scratch/npi12-' + args.scenario + '-edge-${Date.now()}/`, root);')
if args.scenario == 'all':
    driver = driver.replace("const stale = responses.filter(r => r.url.endsWith('/point-rows')).at(-1).body;",
                            "const stale = responses.filter(r => r.url.endsWith('/point-origins')).at(-1).body;")
    driver = driver.replace("responses.filter(r => r.url.endsWith('/point-rows')).at(-1).body.code, 'RESULT_UNAVAILABLE'",
                            "responses.filter(r => r.url.endsWith('/point-origins')).at(-1).body.code, 'RESULT_UNAVAILABLE'")
    driver = driver.replace("  await setRegion('Region A');\n  await run();", """
  await setRegion('Region A');
  await click('details.multi-select:has(#cluster-vehicles) summary');
  await click('#cluster-vehicles input[value="tent"]');
  await click('details.multi-select:has(#cluster-tonnages) summary');
  await click('#cluster-tonnages input[value="20"]');
  await run();""", 1)
    driver = driver.replace('  assert.equal(allPayload.all_origins, true);',
                            "  assert.deepEqual(allPayload.vehicle_types,['tent']);assert.deepEqual(allPayload.tonnage_ids,['20']);\n  assert.equal(allPayload.all_origins, true);")
if args.scenario in ('selection', 'all'):
    driver = driver.replace("document.querySelector('.pulse-state')?.textContent.includes('Пересчитайте')",
                            "document.querySelector('.origin-summary')?.textContent.includes('Пересчитайте')")
    driver = driver.replace("document.querySelector('.pulse-state')?.textContent.includes('недоступен')",
                            "document.querySelector('.origin-summary')?.textContent.includes('недоступен')")
if args.scenario == 'selection':
    driver = driver.replace("new URL('synthetic.csv', root)",
                            f'new URL({json.dumps((root / ".scratch/npi12-selection-evidence/synthetic.csv").as_uri())})')
    driver = driver.replace("document.querySelector('.pulse-state')?.textContent.includes('Пересчитайте')",
                            "document.querySelector('.origin-summary')?.textContent.includes('Пересчитайте')")
    driver = driver.replace("document.querySelector('.pulse-state')?.textContent.includes('недоступен')",
                            "document.querySelector('.origin-summary')?.textContent.includes('недоступен')")
    driver = driver.replace("await click('.cluster-card'); await click('[data-point-id]');",
                            "if(!await evaluate(\"document.querySelector('[data-point-id]')?.offsetParent\"))"
                            "await click('#cluster-table-panel tbody tr button'); await click('[data-point-id]');")
if args.scenario == 'freshness':
    marker = "app.run(host='127.0.0.1', port=5079, use_reloader=False)"
    server = server.replace(marker, "@app.post('/fixture/coordinates')\n"
        "def change_coordinates():\n"
        "    current = json.loads(coords.read_text(encoding='utf8'))\n"
        "    current['Synthetic Destination 00::Region A'][1] += .001\n"
        "    coords.write_text(json.dumps(current), encoding='utf8')\n"
        "    return {'ok': True}\n\n" + marker)
    marker = "  await writeFile(new URL('live-observations.json', root)"
    extra = """
  await run();const beforeCoordinate=lastBody('run').data_snapshot;
  await click('#compare-modes');await waitFor("document.querySelectorAll('[data-comparison-mode]').length===5");
  await click('[data-show-on-map="geography"]');
  await fixture('coordinates');failNextRun=true;await run();
  assert.notEqual(lastBody('revision').data_snapshot,beforeCoordinate);
  assert.ok(lastBody('revision').available.every(v=>v===false));
  assert.equal(await evaluate("document.getElementById('btn-export-clustering').getAttribute('aria-disabled')"),'true');
  await record('13-coordinate-cache-rejected',{oldSnapshot:beforeCoordinate,revision:lastBody('revision'),exportBlocked:true});
  await run();assert.notEqual(lastBody('run').data_snapshot,beforeCoordinate);
  await record('14-coordinate-fresh-recovery',{snapshot:lastBody('run').data_snapshot});
"""
    driver = driver.replace(marker, extra + marker)
if args.scenario == 'navigation':
    driver = driver.replace('  failNextSummary=true;',
                            '  await click(\'[data-clustering-layer="labels"]\');\n  failNextSummary=true;')
    server = server.replace("app.run(host='127.0.0.1', port=5078, use_reloader=False)",
                            "import run\nsys.argv = ['run.py', '--no-browser', '--port', '5078']\n"
                            "print('NPI12_DOCUMENTED_ENTRYPOINT', run.__file__, flush=True)\nrun.main()")
    # Separate repeat of historical scenario12 includes the next submitted mode.
    marker = "await click('#cluster-periods input[value=\"retro\"]');\n  await fetch"
    driver = driver.replace(marker, "await run(); assert.equal(lastPayload('run').mode,'geography');\n"
        "  await record('historical-12-p2-next-submitted-mode',{mode:'geography',checked:'geography'});\n  " + marker)
    # A distinct second conflict/recovery, using native Enter, closes historical16.
    marker = "  // Region and price edits also leave the displayed saved summary unchanged."
    extra = """
  const before16=lastBody('run').data_snapshot;
  await fetch('http://127.0.0.1:5078/fixture/add-origin',{method:'POST'});
  await click('#point-details-close');
  const p16=lastBody('run').points.find(p=>p.id==='synthetic-03');
  await click(`[data-cluster-id="${p16.cluster_id}"]`);await click('[data-point-id="synthetic-03"]');
  await waitFor("document.querySelector('.origin-summary').textContent.includes('Пересчитайте')");
  await evaluate("document.getElementById('btn-run-clustering').focus()");
  await key('Enter','Enter',13);
  await waitFor("!document.getElementById('btn-run-clustering').disabled");await pause(400);
  assert.notEqual(lastBody('run').data_snapshot,before16);
  await openPoint();await waitFor("document.querySelector('[data-origin-fias=\\"a\\"]')");
  await click('[data-origin-fias="a"]');await waitFor("document.querySelectorAll('.pulse-table tbody tr').length===50");
  await record('historical-16-keyboard-fresh-recovery',{newSnapshot:lastBody('run').data_snapshot,oldSnapshot:before16,rows:50});
"""
    driver = driver.replace(marker, extra + marker)
runtime = root / '.scratch/npi12-drivers' / args.scenario
runtime.mkdir(parents=True, exist_ok=True)
server_path, driver_path = runtime / 'server.py', runtime / 'edge.mjs'
server_path.write_text(server, encoding='utf8')
driver_path.write_text(driver, encoding='utf8')
with output.joinpath('server.txt').open('w', encoding='utf8') as log:
    process = subprocess.Popen([sys.executable, str(server_path)], stdout=log, stderr=log,
                               env={**os.environ, 'PYTHONUTF8': '1'})
    try:
        for _ in range(150):
            assert process.poll() is None, 'Synthetic server stopped before startup'
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(.2)
        else:
            raise TimeoutError('Synthetic Flask startup')
        with output.joinpath('driver.txt').open('w', encoding='utf8') as driver_log:
            subprocess.run(['node', str(driver_path)], stdout=driver_log, stderr=driver_log,
                           check=True, timeout=300)
    finally:
        process.terminate()
        process.wait(timeout=10)
print(json.dumps({'scenario': args.scenario, 'status': 'PASS'}))
