import {spawn} from 'node:child_process';
import {readFile, writeFile, appendFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const root = new URL('./', import.meta.url);
const profile = new URL(`../../.scratch/pf-live-edge-${Date.now()}/`, root);
const browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ['--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=0',
    `--user-data-dir=${fileURLToPath(profile)}`, 'about:blank'],
  {windowsHide: true, stdio: ['ignore', 'ignore', 'pipe']});
let diagnostics = '', socket, id = 0;
browser.stderr.on('data', chunk => diagnostics += chunk);
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const pending = new Map(), requests = [], responses = [], evidence = [];
let failNextRevision = false, failNextRun = false, failNextSummary = false, failNextRows = false;
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
      responses.push({id: reply.params.requestId, url: reply.params.response.url, status: reply.params.response.status, headers: reply.params.response.headers, fromDiskCache: reply.params.response.fromDiskCache});
    } else if (reply.method === 'Network.loadingFinished') {
      const response = responses.find(item => item.id === reply.params.requestId);
      if (response) {try {response.body = JSON.parse((await send('Network.getResponseBody', {requestId: response.id})).body);} catch {}}
    } else if (reply.method === 'Fetch.requestPaused') {
      const requestId = reply.params.requestId;
      if ((failNextRevision && reply.params.request.url.endsWith('/revision')) || (failNextRun && reply.params.request.url.endsWith('/run')) || (failNextSummary && reply.params.request.url.endsWith('/point-origins')) || (failNextRows && reply.params.request.url.endsWith('/point-rows'))) {
        failNextSummary = false; failNextRows = false;
        failNextRun = false; failNextRevision = false;
        await send('Fetch.fulfillRequest', {requestId, responseCode: 503,
          responseHeaders: [{name: 'Content-Type', value: 'application/json'}],
          body: Buffer.from(JSON.stringify({ok: false, code: 'NETWORK_TEST', error: 'Synthetic refresh failure'})).toString('base64')});
      } else await send('Fetch.continueRequest', {requestId});
    }
  });
  await send('Network.enable');
  await send('Fetch.enable', {patterns: [{urlPattern: '*/api/clustering/*', requestStage: 'Request'}]});
  await send('Emulation.setDeviceMetricsOverride', {width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false});
  await send('Emulation.setFocusEmulationEnabled', {enabled: true});
  evidence.push({environment: await send('Browser.getVersion')});
  await send('Page.navigate', {url:'http://127.0.0.1:5069'});
  await waitFor("document.querySelector('.combo-option') && document.getElementById('options-status').classList.contains('hidden')");
  const setRegion = async value => {
    await click('#cluster-region'); await key('Home','Home',36); await key('ArrowDown','ArrowDown',40); await key('Enter','Enter',13);
    await waitFor(`document.getElementById('cluster-region').value === ${JSON.stringify(value)} && !document.getElementById('btn-run-clustering').disabled`);
  };
  const lastBody = path => responses.filter(r=>r.url.endsWith('/'+path)).at(-1)?.body;
  const lastPayload = path => JSON.parse(requests.filter(r=>r.url.endsWith('/'+path)).at(-1).postData);
  const openPoint = async (id='synthetic-00') => {
    if (!await evaluate(`document.querySelector('[data-point-id="${id}"]')`)) await click('.cluster-card');
    await click(`[data-point-id="${id}"]`); await pause(450);
  };
  const count = path => requests.filter(r => r.url.endsWith('/' + path)).length;
  const fixture = path => fetch('http://127.0.0.1:5069/fixture/' + path, {method: 'POST'}).then(r => r.json());
  const stats = () => fetch('http://127.0.0.1:5069/fixture/stats').then(r => r.json());
  await click('#all-origins'); await setRegion('Region A'); await run();
  const initial = lastBody('run');
  assert.equal(initial.analysis.origin_fiases.length, 34);
  await openPoint(); await click('[data-origin-fias="a"]');
  assert.equal(lastBody('point-rows').rows.length, 50);
  await record('01-original-all-detail', {snapshot: initial.data_snapshot, origins: 34, rows: 50});
  const runCount = count('run'), loads = (await stats()).loads;
  await run();
  assert.equal(count('run'), runCount); assert.equal(count('revision'), 1);
  assert.equal((await stats()).loads, loads);
  assert.ok(responses.filter(r => r.url.endsWith('/revision')).every(r => r.headers['Cache-Control'] === 'no-store' && !r.fromDiskCache));
  await record('02-validated-cache-hit', {runs: count('run'), revisionChecks: count('revision'), loads});
  await openPoint(); await click('[data-origin-fias="a"]');
  const context = await evaluate("document.getElementById('result-context').textContent");
  await fixture('replace'); failNextRun = true; await run();
  assert.equal(count('run'), runCount + 1);
  assert.equal(lastBody('revision').available[0], false);
  assert.equal(await evaluate("document.getElementById('result-context').textContent"), context);
  assert.equal(await evaluate("document.getElementById('analysis-stale').classList.contains('hidden')"), false);
  assert.equal(await evaluate("document.querySelectorAll('[data-origin-fias]').length"), 0);
  assert.equal(await evaluate("document.querySelectorAll('.pulse-table tbody tr').length"), 0);
  await record('03-weekly-replacement-failed-refresh', {oldSnapshot: initial.data_snapshot,
    revision: lastBody('revision'), frozenContextPreserved: true, oldDetailsBlocked: true});
  await run();
  const fresh = lastBody('run');
  assert.notEqual(fresh.data_snapshot, initial.data_snapshot);
  assert.equal(fresh.analysis.origin_fiases.length, 35);
  assert.ok(fresh.analysis.origin_fiases.includes('new'));
  await openPoint(); await click('[data-origin-fias="new"]');
  assert.equal(lastBody('point-rows').rows.length, 1);
  assert.equal(lastBody('point-rows').rows[0].origin_fias, 'new');
  await record('04-all-refreshed-new-origin', {snapshot: fresh.data_snapshot, origins: 35,
    detail: lastBody('point-rows'), request: lastPayload('point-rows')});
  await click('#compare-modes'); await waitFor("document.querySelector('[data-comparison-mode]')"); await pause(500);
  const comparison = lastBody('compare');
  assert.equal(Object.keys(comparison.results).length, 5);
  for (const result of Object.values(comparison.results)) assert.equal(result.data_snapshot, fresh.data_snapshot);
  await click('[data-show-on-map="geography"]');
  const compares = count('compare');
  await click('#compare-modes'); await pause(500);
  assert.equal(count('compare'), compares); assert.equal(lastBody('revision').available.every(Boolean), true);
  await click('[data-show-on-map="geography"]');
  await record('05-validated-five-mode-comparison', {compareRequests: compares, variants: Object.keys(comparison.results)});
  await fixture('evict');
  await click('#compare-modes'); await pause(600);
  assert.equal(count('compare'), compares + 1);
  assert.ok(lastBody('revision').available.every(value => value === false));
  await click('[data-show-on-map="geography"]');
  await record('06-eviction-comparison-refresh', {revision: lastBody('revision'), compareRequests: count('compare')});
  await fixture('restart'); const beforeRestart = count('run'); await run();
  assert.equal(count('run'), beforeRestart + 1);
  assert.equal(lastBody('revision').data_snapshot, fresh.data_snapshot);
  assert.equal(lastBody('revision').available[0], false);
  await record('07-restart-same-revision', {revision: lastBody('revision'), freshRun: true});
  const beforeFailure = count('run'); failNextRevision = true; await run();
  assert.equal(count('run'), beforeFailure);
  assert.equal(await evaluate("document.getElementById('analysis-form-error').classList.contains('hidden')"), false);
  await record('08-revision-network-failure', {cachedNotPublished: true, runs: count('run')});
  await run(); assert.equal(count('run'), beforeFailure);
  await record('09-network-retry-valid-cache', {runs: count('run'), revision: lastBody('revision')});
  // A second atomic replacement tests a cached comparison without a preceding detail rejection.
  await click('#compare-modes'); await pause(500); await click('[data-show-on-map="geography"]');
  const beforeCompareChange = count('compare');
  await fixture('replace');
  await click('#compare-modes'); await pause(600);
  assert.equal(count('compare'), beforeCompareChange + 1);
  assert.ok(lastBody('revision').available.every(value => value === false));
  await record('10-comparison-source-replacement', {compareRequests: count('compare'), revision: lastBody('revision')});
  await click('[data-show-on-map="geography"]');
  // Native comparison switches preserve P2 form state and do not request new clustering.
  const switchCount = count('compare') + count('run');
  await click('#compare-modes'); await pause(500);
  await click('[data-comparison-mode="bear_volume_zones"]');
  await click('[data-show-on-map="geography"]');
  await click('#cluster-periods input[value="retro"]');
  assert.equal(await evaluate("document.querySelector('input[name=\"analysis-mode\"]:checked').value"), 'geography');
  assert.equal(count('compare') + count('run'), switchCount);
  await record('11-p2-frozen-mode-switch', {selected: 'geography', clusteringRequestsUnchanged: true});
  await click('#cluster-periods input[value="retro"]');
  await click('label:has(input[name="k-mode"][value="manual"])');
  await click('#manual-k');
  await send('Input.dispatchKeyEvent', {type:'keyDown',key:'a',code:'KeyA',modifiers:2,windowsVirtualKeyCode:65});
  await send('Input.dispatchKeyEvent', {type:'keyUp',key:'a',code:'KeyA',modifiers:2,windowsVirtualKeyCode:65});
  await send('Input.insertText',{text:'7'}); await key('Tab','Tab',9);
  await fixture('hold');
  await click('#btn-run-clustering');
  for (let attempt=0; attempt<100; attempt++) {
    if ((await (await fetch('http://127.0.0.1:5069/fixture/held')).json()).entered) break;
    if(attempt===99) throw Error('Calculation did not enter the hold');
    await pause(100);
  }
  const beforeInflightSnapshot = lastBody('revision').data_snapshot;
  await fixture('replace'); await fixture('release');
  await waitFor("!document.getElementById('btn-run-clustering').disabled"); await pause(400);
  assert.equal(lastBody('run').code, 'STALE_DATA_SNAPSHOT');
  assert.equal(await evaluate("document.getElementById('analysis-stale').classList.contains('hidden')"), false);
  await record('12-source-change-inflight-calculation', {validated: beforeInflightSnapshot,
    response: lastBody('run'), oldFrozenDisplayStale: true});
  await writeFile(new URL('live-observations.json', root), JSON.stringify(evidence, null, 2));
  await writeFile(new URL('network.json', root), JSON.stringify({requests, responses}, null, 2));
  console.log('PASS: 12 real Flask/Edge checkpoints, no page reload after CSV replacements');
} finally {
  if (socket?.readyState === 1) {await send('Browser.close').catch(() => {}); socket.close();}
  if (browser.pid && browser.exitCode === null && browser.signalCode === null) browser.kill();
}
