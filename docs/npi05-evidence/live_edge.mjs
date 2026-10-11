import {spawn} from 'node:child_process';
import {readFile, writeFile, appendFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const root = new URL('../../.scratch/npi05-evidence/', import.meta.url);
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
  await send('Page.navigate', {url: 'http://127.0.0.1:5065'});
  await waitFor("document.querySelector('.combo-option') && document.getElementById('options-status').classList.contains('hidden')");
  await run();
  assert.equal(requests.filter(r => r.url.endsWith('/run')).length, 0);
  await record('01-empty-manual', {implicitAll: false});
  await click('#all-origins');
  await waitFor("!document.getElementById('cluster-region').disabled");
  await run();
  assert.match(await evaluate("document.getElementById('analysis-form-error').textContent"), /регион/);
  await record('02-all-needs-region', {runRequests: 0});
  const setRegion = async value => {
    await click('#cluster-region');
    await key('Home', 'Home', 36);
    if (value === 'Region A') await key('ArrowDown', 'ArrowDown', 40);
    if (value === 'Region B') {await key('ArrowDown', 'ArrowDown', 40); await key('ArrowDown', 'ArrowDown', 40);}
    await key('Enter', 'Enter', 13);
    await waitFor(`document.getElementById('cluster-region').value === ${JSON.stringify(value)} && !document.getElementById('btn-run-clustering').disabled`);
  };
  await setRegion('Region A');
  await run();
  const all = responses.filter(r => r.url.endsWith('/run')).at(-1).body;
  const allPayload = JSON.parse(requests.filter(r => r.url.endsWith('/run')).at(-1).postData);
  assert.equal(allPayload.all_origins, true); assert.ok(!('origin_fiases' in allPayload));
  assert.equal(all.analysis.origin_fiases.length, 36);
  assert.ok(all.analysis.origin_fiases.includes('synthetic-o35'));
  assert.ok(!all.analysis.origin_fiases.includes('synthetic-foreign'));
  assert.equal(all.points.length, 12); assert.equal(all.data_quality.trip_count_total, 876);
  assert.ok(all.points.every(p => p.trip_count === 73));
  assert.equal(await evaluate("document.getElementById('analysis-stale').classList.contains('hidden')"), true);
  assert.equal(await evaluate("document.querySelectorAll('.cluster-table-panel tbody tr').length"), all.cluster_table.rows.length);
  await click('#result-context details summary');
  const savedContext = await evaluate("document.getElementById('result-context').textContent");
  assert.match(savedContext, /Все отправления/); assert.match(savedContext, /synthetic-o35/);
  assert.match(savedContext, /Без строк/);
  await record('03-all-map-table', {origins: 36, destinations: 12, sourceRows: 456, machines: 876,
    suggestionLimit: 30, zeroMatch: all.analysis.origin_coverage.filter(o => o.zero_match), request: allPayload,
    response: {intent: all.analysis.selection_intent, frozen: all.analysis.frozen_request, snapshot: all.data_snapshot}});
  const suggestion = await (await fetch('http://127.0.0.1:5065/api/clustering/origins?limit=30&destination_region=Region%20A')).json();
  const explicitPayload = {...allPayload, origin_fiases: all.analysis.origin_fiases}; delete explicitPayload.all_origins;
  const explicit = await (await fetch('http://127.0.0.1:5065/api/clustering/run', {method:'POST',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify(explicitPayload)})).json();
  assert.equal(suggestion.length, 30);
  assert.ok(all.analysis.origin_fiases.some(id => !suggestion.some(o => o.fias_id === id)));
  assert.deepEqual(explicit.points, all.points); assert.deepEqual(explicit.clusters, all.clusters);
  assert.deepEqual(explicit.cluster_table, all.cluster_table);
  await record('04-equivalent-explicit-set', {suggestions: suggestion.length, identicalPointsClustersTable: true});
  await setRegion('Region B');
  assert.equal(await evaluate("document.getElementById('result-context').textContent"), savedContext);
  assert.equal(await evaluate("document.getElementById('analysis-stale').classList.contains('hidden')"), false);
  await showPointRows();
  const frozenRows = JSON.parse(requests.filter(r => r.url.endsWith('/point-rows')).at(-1).postData);
  assert.deepEqual(frozenRows.origin_fiases, all.analysis.origin_fiases); assert.ok(!frozenRows.all_origins);
  assert.equal(frozenRows.destination_region, 'Region A'); assert.equal(frozenRows.mode, 'geography');
  await record('05-frozen-detail-region-edit', {request: frozenRows, noAllResolution: true});
  await run();
  const regionalB = responses.filter(r => r.url.endsWith('/run')).at(-1).body;
  assert.deepEqual(regionalB.analysis.origin_fiases, ['synthetic-foreign']);
  await record('06-region-switch', {region: 'Region B', origins: regionalB.analysis.origin_fiases});
  await setRegion('Region A'); await run();
  await click('#compare-modes');
  await waitFor("document.querySelectorAll('[data-comparison-mode]').length === 5");
  const comparison = responses.filter(r => r.url.endsWith('/compare')).at(-1).body;
  assert.equal(Object.keys(comparison.results).length, 5);
  for (const result of Object.values(comparison.results)) {
    assert.equal(result.analysis.origin_fiases.length, 36); assert.deepEqual(result.analysis.selection_intent, {all_origins:true});
  }
  await click('[data-comparison-mode="bear_volume_zones"]');
  await click('[data-comparison-mode="geography"]'); await click('#close-comparison');
  const comparisonCount = requests.filter(r => r.url.endsWith('/compare')).length;
  await click('#compare-modes'); await pause(300); await click('#close-comparison');
  assert.equal(requests.filter(r => r.url.endsWith('/compare')).length, comparisonCount);
  assert.match(await evaluate("document.getElementById('result-context').textContent"), /Все отправления/);
  await click('#cluster-periods input[value="retro"]');
  assert.equal(await evaluate("document.querySelector('input[name=\"analysis-mode\"]:checked').value"), 'geography');
  assert.match(await evaluate("document.getElementById('preview-mode').textContent"), /географии/);
  await record('07-cached-all-p2', {fiveModes: true, requestFreeSwitches: true, allLabel: true, archiveEditMode: 'geography'});
  await click('#cluster-periods input[value="current"]');
  await click('#cluster-prices input[value="spot"]'); await click('#cluster-prices input[value="tender"]');
  const beforeFailure = await evaluate("document.getElementById('result-context').textContent");
  await run();
  assert.equal(responses.filter(r => r.url.endsWith('/run')).at(-1).body.code, 'NO_DATA');
  assert.equal(await evaluate("document.getElementById('result-context').textContent"), beforeFailure);
  await record('08-no-data-frozen', {error: 'NO_DATA', previousContextPreserved: true});
  await click('#cluster-periods input[value="retro"]'); await click('#cluster-periods input[value="current"]');
  await click('#cluster-prices input[value="tender"]'); await click('#cluster-prices input[value="spot"]');
  await run();
  await fetch('http://127.0.0.1:5065/fixture/add-origin', {method:'POST'});
  assert.equal(all.analysis.origin_fiases.length, 36);
  await showPointRows();
  // Use a different destination from the previously cached page to request the backend.
  await click('[data-point-id="synthetic-01"]'); await click('.pulse-details summary'); await pause(400);
  const stale = responses.filter(r => r.url.endsWith('/point-rows')).at(-1).body;
  assert.equal(stale.code, 'STALE_DATA_SNAPSHOT');
  assert.match(await evaluate("document.getElementById('result-context').textContent"), /36/);
  assert.ok(!(await evaluate("document.getElementById('result-context').textContent")).includes('synthetic-new'));
  await record('09-source-added-frozen-set', {savedOrigins: 36, newOriginExcluded: true, error: stale.code});
  failNextRun = true; await run();
  assert.match(await evaluate("document.getElementById('analysis-form-error').textContent"), /Synthetic refresh failure/);
  await record('10-failed-fresh-run', {oldResultVisible: true, stale: true});
  await run();
  const refreshed = responses.filter(r => r.url.endsWith('/run')).at(-1).body;
  assert.equal(refreshed.analysis.origin_fiases.length, 37);
  assert.ok(refreshed.analysis.origin_fiases.includes('synthetic-new'));
  assert.notEqual(refreshed.data_snapshot, all.data_snapshot);
  await record('11-fresh-all-generation', {origins: 37, newSnapshot: refreshed.data_snapshot, oldSnapshot: all.data_snapshot});
  await click('#compare-modes'); await waitFor("document.querySelectorAll('[data-comparison-mode]').length === 5");
  await click('#close-comparison');
  assert.ok(requests.filter(r => r.url.endsWith('/compare')).length > comparisonCount);
  await fetch('http://127.0.0.1:5065/fixture/evict', {method:'POST'});
  await showPointRows();
  assert.equal(responses.filter(r => r.url.endsWith('/point-rows')).at(-1).body.code, 'RESULT_UNAVAILABLE');
  await record('12-evicted-frozen-result', {error: 'RESULT_UNAVAILABLE'});
  await run();
  await record('13-eviction-recalculation', {origins: responses.filter(r => r.url.endsWith('/run')).at(-1).body.analysis.origin_fiases.length});
  await click('#all-origins'); await pause(350);
  assert.equal(await evaluate("document.getElementById('cluster-origin').disabled"), false);
  await selectOrigin('Synthetic Origin 00', true); await setRegion('Region A');
  await selectOrigin('Synthetic Origin 01'); await run();
  const manual = JSON.parse(requests.filter(r => r.url.endsWith('/run')).at(-1).postData);
  assert.deepEqual(manual.origin_fiases, ['synthetic-o00','synthetic-o01']); assert.ok(!manual.all_origins);
  assert.ok(!(await evaluate("document.getElementById('result-context').textContent")).includes('Все отправления'));
  await record('14-back-to-manual', {request: manual, explicitLabel: true});
  await click('#all-origins'); await pause(400);
  await click('#all-origins'); await pause(400);
  assert.equal(await evaluate("document.querySelectorAll('[data-remove-origin]').length"), 2);
  await click('#all-origins');
  await key(' ', 'Space', 32);
  assert.equal(await evaluate("document.getElementById('all-origins').checked"), false);
  await key(' ', 'Space', 32);
  assert.equal(await evaluate("document.getElementById('all-origins').checked"), true);
  await record('15-keyboard-all', {spaceToggle: true, manualSelectionRetained: true});
  await waitFor("!document.getElementById('clustering-controls').classList.contains('options-loading')");
  await send('Input.dispatchMouseEvent', {type:'mouseWheel',x:150,y:500,deltaY:3000,deltaX:0});
  await pause(300);
  await click('#btn-run-clustering'); await key('Enter','Enter',13); await pause(400);
  await record('15b-keyboard-calculate', {all:true, keyboardSubmit:true});
  await click('#btn-reset-clustering'); await pause(300);
  assert.equal(await evaluate("document.getElementById('all-origins').checked"), false);
  assert.equal(await evaluate("document.querySelectorAll('[data-remove-origin]').length"), 0);
  await record('17-reset', {all:false, origins:0});
  for (const width of [1366, 1100, 390]) {
    await send('Emulation.setDeviceMetricsOverride', {width, height:900, deviceScaleFactor:1, mobile:false});
    if (width === 390) await click('#mobile-controls-btn');
    await click('#all-origins-hint');
    const box = await evaluate("(()=>{const r=document.querySelector('.all-origins-control').getBoundingClientRect();return {left:r.left,right:r.right,width:innerWidth}})()");
    assert.ok(box.left >= 0 && box.right <= box.width);
    await record(`16-layout-${width}`, box);
  }
  await send('Emulation.setDeviceMetricsOverride', {width:1600,height:1000,deviceScaleFactor:1,mobile:false});
  await writeFile(new URL('live-observations.json', root), JSON.stringify(evidence,null,2));
  await writeFile(new URL('live-network.json', root), JSON.stringify({requests,responses},null,2));
} finally {
  await writeFile(new URL('live-observations.json', root), JSON.stringify(evidence,null,2));
  await writeFile(new URL('live-network.json', root), JSON.stringify({requests,responses},null,2));
  if (socket?.readyState === 1) {await send('Browser.close').catch(()=>{}); socket.close();}
  if (browser.exitCode === null && browser.signalCode === null) browser.kill();
}
