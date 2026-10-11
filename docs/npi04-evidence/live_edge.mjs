import {spawn} from 'node:child_process';
import {readFile, writeFile, appendFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const root = new URL('../../.scratch/npi04-evidence/', import.meta.url);
const profile = new URL(`live-edge-${Date.now()}/`, root);
const browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ['--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=0',
    `--user-data-dir=${fileURLToPath(profile)}`, 'about:blank'],
  {windowsHide: true, stdio: ['ignore', 'ignore', 'pipe']});
let diagnostics = '', socket, id = 0;
browser.stderr.on('data', chunk => diagnostics += chunk);
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const pending = new Map(), requests = [], responses = [], evidence = [];
let failNextRun = false;
const send = (method, params = {}) => new Promise((resolve, reject) => {
  pending.set(++id, {resolve, reject}); socket.send(JSON.stringify({id, method, params}));
});
const evaluate = async expression => {
  const reply = await send('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
  if (reply.exceptionDetails) throw Error(JSON.stringify(reply.exceptionDetails));
  return reply.result.value;
};
const waitFor = async expression => {
  for (let i = 0; i < 100; i++) {if (await evaluate(expression)) return; await pause(100);}
  throw Error(`Timeout: ${expression}`);
};
const click = async selector => {
  await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)}),r=e.getBoundingClientRect();if(r.top<60||r.bottom>innerHeight)e.scrollIntoView({block:'center',behavior:'instant'});})()`);
  await pause(200);
  const rect = await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw Error('Missing '+${JSON.stringify(selector)});const r=e.getBoundingClientRect();return{x:r.x+r.width/2,y:(Math.max(60,r.top)+Math.min(innerHeight,r.bottom))/2}})()`);
  await send('Input.dispatchMouseEvent', {type: 'mouseMoved', ...rect});
  await send('Input.dispatchMouseEvent', {type: 'mousePressed', button: 'left', clickCount: 1, ...rect});
  await send('Input.dispatchMouseEvent', {type: 'mouseReleased', button: 'left', clickCount: 1, ...rect});
  await pause(200);
};
const key = async (key, code = key, vk = 0) => {
  await send('Input.dispatchKeyEvent', {type: 'keyDown', key, code, windowsVirtualKeyCode: vk,
    ...(key === 'Enter' ? {text: '\r', unmodifiedText: '\r'} : {})});
  await send('Input.dispatchKeyEvent', {type: 'keyUp', key, code, windowsVirtualKeyCode: vk});
  await pause(120);
};
const shot = async name => {
  const result = await send('Page.captureScreenshot', {format: 'png'});
  await writeFile(new URL(`${name}.png`, root), Buffer.from(result.data, 'base64'));
};
const record = async (scenario, facts) => {
  evidence.push({scenario, facts}); await shot(scenario); console.log(JSON.stringify({scenario, facts}));
};
const selectOrigin = async (name, keyboard = false) => {
  await click('#cluster-origin');
  await send('Input.insertText', {text: name});
  await pause(400);
  await waitFor(`document.querySelector('.combo-option')?.textContent.includes(${JSON.stringify(name)})`);
  if (keyboard) {
    await key('ArrowDown', 'ArrowDown', 40);
    console.log('Keyboard focus: ' + await evaluate("document.activeElement.outerHTML"));
    await key('Enter', 'Enter', 13);
  }
  else await click('.combo-option');
  await waitFor("!document.getElementById('clustering-controls').classList.contains('options-loading')");
};
const run = async () => {
  await send('Input.dispatchMouseEvent', {type: 'mouseWheel', x: 150, y: 500, deltaY: 3000, deltaX: 0});
  await pause(300);
  await click('#btn-run-clustering');
  await waitFor("!document.getElementById('btn-run-clustering').disabled"); await pause(400);
};
const showPointRows = async () => {
  await click('.cluster-card'); await click('[data-point-id]');
  await click('.pulse-details summary'); await pause(350);
};
try {
  let port;
  for (let i = 0; i < 200 && !port; i++) {
    try {port = (await readFile(new URL('DevToolsActivePort', profile), 'utf8')).split('\n')[0];}
    catch {await pause(50);}
  }
  if (!port) throw Error(diagnostics);
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {socket.addEventListener('open', resolve, {once: true}); socket.addEventListener('error', reject, {once: true});});
  socket.addEventListener('message', async event => {
    const reply = JSON.parse(event.data);
    if (reply.id) {
      const task = pending.get(reply.id); pending.delete(reply.id);
      reply.error ? task.reject(reply.error) : task.resolve(reply.result);
    } else if (reply.method === 'Network.requestWillBeSent' && reply.params.request.url.includes('/api/clustering/')) {
      requests.push({id: reply.params.requestId, ...reply.params.request});
    } else if (reply.method === 'Network.responseReceived' && reply.params.response.url.includes('/api/clustering/')) {
      responses.push({id: reply.params.requestId, url: reply.params.response.url, status: reply.params.response.status});
    } else if (reply.method === 'Network.loadingFinished') {
      const response = responses.find(item => item.id === reply.params.requestId);
      if (response) {try {response.body = JSON.parse((await send('Network.getResponseBody', {requestId: response.id})).body);} catch {}}
    } else if (reply.method === 'Fetch.requestPaused') {
      const requestId = reply.params.requestId;
      if (failNextRun && reply.params.request.url.endsWith('/run')) {
        failNextRun = false;
        await send('Fetch.fulfillRequest', {requestId, responseCode: 503,
          responseHeaders: [{name: 'Content-Type', value: 'application/json'}],
          body: Buffer.from(JSON.stringify({ok: false, code: 'NETWORK_TEST', error: 'Synthetic refresh failure'})).toString('base64')});
      } else await send('Fetch.continueRequest', {requestId});
    }
  });
  await send('Network.enable');
  await send('Fetch.enable', {patterns: [{urlPattern: '*/api/clustering/run', requestStage: 'Request'}]});
  await send('Emulation.setDeviceMetricsOverride', {width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false});
  await send('Emulation.setFocusEmulationEnabled', {enabled: true});
  evidence.push({environment: await send('Browser.getVersion')});
  await send('Page.navigate', {url: 'http://127.0.0.1:5064'});
  await waitFor("document.querySelector('.combo-option') && document.getElementById('options-status').classList.contains('hidden')");
  await run();
  assert.match(await evaluate("document.getElementById('analysis-form-error').textContent"), /хотя бы одно/);
  await record('01-empty-validation', {requests: requests.filter(r => r.url.endsWith('/run')).length});
  await selectOrigin('Synthetic Alpha', true);
  await click('#cluster-region'); await key('ArrowDown', 'ArrowDown', 40); await key('Enter', 'Enter', 13);
  await waitFor("document.getElementById('cluster-region').value === 'Region A' && !document.getElementById('btn-run-clustering').disabled");
  await selectOrigin('Synthetic Beta');
  await run();
  const union = responses.filter(r => r.url.endsWith('/run')).at(-1).body;
  assert.deepEqual(union.analysis.origin_fiases, ['synthetic-a', 'synthetic-b']);
  assert.equal(union.points.length, 12); assert.equal(new Set(union.points.map(p => p.fias_id)).size, 12);
  assert.ok(union.points.every(p => p.trip_count === 40 && p.weighted_route_length === 250));
  assert.equal(union.data_quality.trip_count_total, 480);
  assert.equal(await evaluate("document.querySelectorAll('.cluster-table-panel tbody tr').length"), union.cluster_table.rows.length);
  await record('02-union-map-table', {points: 12, machines: 480, route: 250, clusters: union.clusters.length,
    request: JSON.parse(requests.filter(r => r.url.endsWith('/run')).at(-1).postData)});
  const frozenContext = await evaluate("document.getElementById('result-context').textContent");
  await click('#cluster-region'); await key('Home', 'Home', 36); await key('Enter', 'Enter', 13);
  await waitFor("document.getElementById('cluster-region').value === '' && !document.getElementById('btn-run-clustering').disabled");
  assert.equal(await evaluate("document.getElementById('result-context').textContent"), frozenContext);
  assert.equal(await evaluate("document.getElementById('analysis-stale').classList.contains('hidden')"), false);
  await record('02b-frozen-region-edit', {region: '', savedRegion: 'Region A', preserved: true});
  await click('#cluster-region'); await key('ArrowDown', 'ArrowDown', 40); await key('Enter', 'Enter', 13);
  await waitFor("document.getElementById('cluster-region').value === 'Region A' && !document.getElementById('btn-run-clustering').disabled");
  await click('#cluster-origin'); await send('Input.insertText', {text: 'Missing Synthetic Origin'}); await pause(500);
  assert.equal(await evaluate("document.querySelectorAll('.combo-option').length"), 0);
  assert.equal(await evaluate("document.querySelectorAll('[data-remove-origin]').length"), 2);
  await record('02c-search-independent-selection', {suggestions: 0, selectedOrigins: 2});
  await send('Input.dispatchKeyEvent', {type: 'keyDown', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2});
  await send('Input.dispatchKeyEvent', {type: 'keyUp', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2});
  await key('Backspace', 'Backspace', 8); await pause(400); await key('Escape', 'Escape', 27);
  await click('#cluster-periods input[value="retro"]');
  assert.equal(await evaluate("document.getElementById('result-context').textContent"), frozenContext);
  assert.equal(await evaluate("document.getElementById('analysis-stale').classList.contains('hidden')"), false);
  await showPointRows();
  const frozenRows = JSON.parse(requests.filter(r => r.url.endsWith('/point-rows')).at(-1).postData);
  assert.deepEqual(frozenRows.period_types, ['current']);
  assert.deepEqual(frozenRows.origin_fiases, ['synthetic-a', 'synthetic-b']);
  assert.equal(frozenRows.mode, 'geography');
  await record('03-frozen-detail', {frozenRows, renderedRows: await evaluate("document.querySelectorAll('.pulse-table tbody tr').length")});
  await run();
  const bothPeriods = responses.filter(r => r.url.endsWith('/run')).at(-1).body;
  assert.equal(bothPeriods.data_quality.trip_count_total, 600);
  await record('04-filter-recalculation', {machines: 600, snapshot: bothPeriods.data_snapshot});
  await click('#compare-modes');
  await waitFor("document.querySelectorAll('[data-comparison-mode]').length === 5");
  const compareCount = requests.filter(r => r.url.endsWith('/compare')).length;
  const runCount = requests.filter(r => r.url.endsWith('/run')).length;
  for (const mode of ['geo_cost', 'geo_volume', 'bear_zones', 'bear_volume_zones', 'geography']) {
    await click(`[data-comparison-mode="${mode}"]`);
    assert.equal(await evaluate("document.querySelector('input[name=analysis-mode]:checked').value"), mode);
  }
  assert.equal(requests.filter(r => r.url.endsWith('/compare')).length, compareCount);
  assert.equal(requests.filter(r => r.url.endsWith('/run')).length, runCount);
  const comparison = responses.filter(r => r.url.endsWith('/compare')).at(-1).body;
  assert.equal(comparison.winner, null);
  await record('05-five-mode-comparison', {compareCount, runCount, modes: Object.keys(comparison.results), winner: comparison.winner});
  await click('#close-comparison');
  await click('#cluster-periods input[value="retro"]');
  assert.equal(await evaluate("document.querySelector('input[name=analysis-mode]:checked').value"), 'geography');
  await record('06-p2-return-form', {mode: 'geography', stale: true});
  await run();
  await selectOrigin('Synthetic Gamma'); await run();
  const three = responses.filter(r => r.url.endsWith('/run')).at(-1).body;
  assert.equal(three.analysis.origin_coverage.find(o => o.fias_id === 'synthetic-c').zero_match, true);
  assert.match(await evaluate("document.getElementById('result-context').textContent"), /Без строк.*Synthetic Gamma/);
  await record('07-three-origins-zero-match', {origins: three.analysis.origin_fiases, coverage: three.analysis.origin_coverage});
  await click('#cluster-periods input[value="retro"]');
  await click('#cluster-periods input[value="current"]');
  await click('#cluster-prices input[value="tender"]'); await click('#cluster-prices input[value="spot"]');
  await run();
  assert.match(await evaluate("document.getElementById('analysis-form-error').textContent"), /NO_DATA/);
  assert.equal(await evaluate("document.getElementById('inspector-result').classList.contains('hidden')"), false);
  await record('08-no-data-preserves-result', {error: await evaluate("document.getElementById('analysis-form-error').textContent")});
  await click('#cluster-periods input[value="current"]'); await click('#cluster-periods input[value="retro"]');
  await click('#cluster-prices input[value="spot"]'); await click('#cluster-prices input[value="tender"]');
  await click('[data-remove-origin="synthetic-c"]'); await waitFor("!document.getElementById('btn-run-clustering').disabled"); await run();
  await showPointRows();
  await appendFile(new URL('synthetic.csv', root), '\n');
  await click('#point-details-close');
  const stalePoint = await evaluate("[...document.querySelectorAll('[data-point-id]')].at(-1).dataset.pointId");
  await click(`[data-point-id="${stalePoint}"]`); await click('.pulse-details summary');
  await waitFor("document.querySelector('.pulse-state')?.textContent.includes('Пересчитайте')");
  assert.ok(responses.some(r => r.status === 409 && r.body?.code === 'STALE_DATA_SNAPSHOT'));
  await record('09-p1-rejected-snapshot', {rejected: union.data_snapshot});
  failNextRun = true; await run();
  assert.match(await evaluate("document.getElementById('analysis-form-error').textContent"), /Synthetic refresh failure/);
  assert.equal(await evaluate("document.getElementById('analysis-stale').classList.contains('hidden')"), false);
  await record('10-p1-failed-refresh', {preserved: true});
  await run(); await showPointRows();
  const refreshed = responses.filter(r => r.url.endsWith('/run') && r.status === 200).at(-1).body;
  assert.notEqual(refreshed.data_snapshot, union.data_snapshot);
  assert.equal(responses.filter(r => r.url.endsWith('/point-rows')).at(-1).status, 200);
  await record('11-p1-recovered', {snapshot: refreshed.data_snapshot});
  await click('#compare-modes'); await waitFor("document.querySelectorAll('[data-comparison-mode]').length === 5");
  const freshComparison = responses.filter(r => r.url.endsWith('/compare')).at(-1).body;
  assert.ok(Object.values(freshComparison.results).every(result => result.data_snapshot === refreshed.data_snapshot));
  await click('[data-comparison-mode="geo_cost"]'); await click('[data-comparison-mode="geography"]');
  await record('11b-p1-comparison-recovered', {snapshot: refreshed.data_snapshot, freshCompare: true});
  await click('#close-comparison');
  await showPointRows();
  await fetch('http://127.0.0.1:5064/fixture/evict', {method: 'POST'});
  await click('#point-details-close'); await showPointRows();
  // A cached loaded page is intentionally retained. Choose another point to hit the evicted server result.
  await click('#point-details-close');
  const pointButtons = await evaluate("[...document.querySelectorAll('[data-point-id]')].map(b=>b.dataset.pointId)");
  await click(`[data-point-id="${pointButtons.at(-1)}"]`); await click('.pulse-details summary');
  await waitFor("document.querySelector('.pulse-state')?.textContent.includes('недоступен')");
  await record('12-result-unavailable', {explicitRecovery: true});
  await run();
  assert.equal(await evaluate("document.getElementById('analysis-stale').classList.contains('hidden')"), true);
  await record('13-result-recalculated', {snapshot: responses.filter(r => r.url.endsWith('/run') && r.status === 200).at(-1).body.data_snapshot});
  await click('[data-remove-origin="synthetic-b"]');
  // Delete uses an actual browser keyboard event on the remaining remove button.
  await click('#cluster-origin'); await key('Escape', 'Escape', 27); await key('Tab', 'Tab', 9);
  await key('Delete', 'Delete', 46);
  await pause(300);
  await record('14-keyboard-removal', {tokens: await evaluate("document.querySelectorAll('[data-remove-origin]').length"),
    focus: await evaluate("document.activeElement.id"), focusOutline: await evaluate("getComputedStyle(document.activeElement).outlineStyle")});
  assert.equal(await evaluate("document.querySelectorAll('[data-remove-origin]').length"), 0);
  for (let i = 0; i < 40 && await evaluate("document.activeElement.id !== 'btn-run-clustering'"); i++) await key('Tab', 'Tab', 9);
  assert.equal(await evaluate("document.activeElement.id"), 'btn-run-clustering');
  await key('Enter', 'Enter', 13);
  assert.match(await evaluate("document.getElementById('analysis-form-error').textContent"), /хотя бы одно/);
  await record('15-keyboard-calculate', {focus: 'btn-run-clustering', visibleValidation: true});
  await writeFile(new URL('live-results.json', root), JSON.stringify({status: 'PASS', evidence, requests, responses}, null, 2));
  console.log('LIVE ACCEPTANCE PASS');
} catch (error) {
  if (socket) await shot('failure');
  await writeFile(new URL('live-results.json', root), JSON.stringify({status: 'FAIL', error: String(error), evidence, requests, responses}, null, 2));
  throw error;
} finally {
  if (socket) {await send('Browser.close').catch(() => {}); socket.close();}
  if (browser.exitCode === null) browser.kill();
}
