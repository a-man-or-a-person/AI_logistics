import {spawn} from 'node:child_process';
import {readFile, writeFile, appendFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const root = new URL('../../.scratch/npi07-evidence/', import.meta.url);
const profile = new URL(`live-edge-${Date.now()}/`, root);
const browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ['--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=0',
    `--user-data-dir=${fileURLToPath(profile)}`, 'about:blank'],
  {windowsHide: true, stdio: ['ignore', 'ignore', 'pipe']});
let diagnostics = '', socket, id = 0;
browser.stderr.on('data', chunk => diagnostics += chunk);
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const pending = new Map(), requests = [], responses = [], evidence = [];
let failNextRun = false, failNextSummary = false, failNextRows = false;
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
      if ((failNextRun && reply.params.request.url.endsWith('/run')) || (failNextSummary && reply.params.request.url.endsWith('/point-origins')) || (failNextRows && reply.params.request.url.endsWith('/point-rows'))) {
        failNextSummary = false; failNextRows = false;
        failNextRun = false;
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
  await send('Page.navigate', {url:'http://127.0.0.1:5067'});
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
  await click('#all-origins'); await setRegion('Region A'); await run();
  const all = lastBody('run');
  assert.equal(all.analysis.origin_fiases.length,34); assert.equal(all.points.length,12);
  assert.equal(all.data_quality.trip_count_total,611);
  assert.equal(all.analysis.origin_coverage.find(o=>o.fias_id==='c').zero_match,true);
  const x=all.points.find(p=>p.id==='synthetic-00'); assert.equal(x.trip_count,171);
  assert.ok(Math.abs(x.weighted_route_length-169.46564885496184)<1e-9);
  await record('01-all-combined',{origins:34,points:12,sourceRows:119,machines:611,point:x,
    clusterTable:all.cluster_table, zeroMatch:all.analysis.origin_coverage.find(o=>o.fias_id==='c')});
  failNextSummary=true; await openPoint();
  await waitFor("document.querySelector('[data-origins-retry]')");
  await record('02-summary-network-error',{retry:true});
  await click('[data-origins-retry]');
  await waitFor("document.querySelectorAll('[data-origin-fias]').length === 33");
  const summary=lastBody('point-origins');
  assert.equal(summary.origins.length,33); assert.equal(summary.cluster_id,x.cluster_id);
  assert.equal(summary.origins.find(o=>o.origin_fias==='a').trip_count,70);
  assert.equal(summary.origins.find(o=>o.origin_fias==='b').weighted_price,5400);
  assert.deepEqual(summary.origins.find(o=>o.origin_fias==='b').origin_regions,['B Region',null]);
  await record('03-summary-retry-success',{summary,request:lastPayload('point-origins')});
  const bottom=await evaluate("document.querySelector('#cluster-table-panel tbody').textContent");
  await click('[data-origin-fias="a"]');
  await waitFor("document.querySelectorAll('.pulse-table tbody tr').length === 50");
  const first=lastBody('point-rows'); assert.equal(first.total,61);
  assert.ok(first.rows.every(r=>r.origin_fias==='a'&&r.destination_fias==='synthetic-00'&&r.period_id==='202609'));
  assert.equal(lastPayload('point-rows').detail_origin_fias,'a');
  await record('04-origin-first-page',{count:50,total:61,request:lastPayload('point-rows'),ids:first.rows.map(r=>r.source_row_id)});
  await click('[data-pulse-more]');
  await waitFor("document.querySelectorAll('.pulse-table tbody tr').length === 61");
  const second=lastBody('point-rows'); assert.equal(second.offset,50);
  assert.equal(new Set([...first.rows,...second.rows].map(r=>r.source_row_id)).size,61);
  assert.equal(second.rows.at(-1).period_id,'202608');
  assert.equal(await evaluate("document.querySelector('#cluster-table-panel tbody').textContent"),bottom);
  await record('05-origin-paging',{rows:61,offset:50,stableUniqueIds:true,newestFirst:true,bottomTableUnchanged:true});
  failNextRows=true; await click('[data-origin-fias="b"]'); await waitFor("document.querySelector('[data-pulse-retry]')");
  await record('06-rows-network-error',{retry:true});
  await click('[data-pulse-retry]'); await waitFor("document.querySelectorAll('.pulse-table tbody tr').length===3");
  assert.ok(lastBody('point-rows').rows.every(r=>r.origin_fias==='b'));
  assert.deepEqual(new Set(lastBody('point-rows').rows.map(r=>r.origin_region)),new Set(['B Region',null]));
  // Focus by mouse, switch with Tab/Enter: native contributor button receives real keyboard input.
  await click('[data-origin-fias="a"]'); await key('Tab','Tab',9);
  const focus=await evaluate("document.activeElement.dataset.originFias"); assert.equal(focus,'b');
  await key('Enter','Enter',13);
  assert.equal(await evaluate("document.querySelector('[data-origin-fias=\"b\"]').getAttribute('aria-pressed')"),'true');
  await record('07-keyboard-origin',{focus,enteredOrigin:'b',realKeyboard:true,actualRowRegions:['B Region',null]});
  const summaryText=await evaluate("document.querySelector('.origin-summary').textContent");
  const rowText=await evaluate("document.querySelector('.pulse-table tbody').textContent");
  const count=requests.filter(r=>r.url.endsWith('/point-origins')||r.url.endsWith('/point-rows')).length;
  await click('#cluster-periods input[value="retro"]');
  await click('.mode-geo_cost');
  await click('#all-origins'); await selectOrigin('Synthetic a',true);
  assert.equal(await evaluate("document.querySelector('.origin-summary').textContent"),summaryText);
  assert.equal(await evaluate("document.querySelector('.pulse-table tbody').textContent"),rowText);
  assert.equal(requests.filter(r=>r.url.endsWith('/point-origins')||r.url.endsWith('/point-rows')).length,count);
  assert.equal(await evaluate("document.getElementById('analysis-stale').classList.contains('hidden')"),false);
  await record('08-frozen-form-edits',{unchangedSummaryAndRows:true,noDetailRequests:true,edits:['origins','periods','mode']});
  // Restore All and current filter, then use existing comparison to verify P2.
  await click('#all-origins'); await click('#cluster-periods input[value="retro"]');
  await setRegion('Region A'); await click('.mode-geography'); await run();
  await click('#compare-modes'); await waitFor("document.querySelectorAll('[data-comparison-mode]').length===5");
  const runs=requests.filter(r=>r.url.endsWith('/run')).length, compares=requests.filter(r=>r.url.endsWith('/compare')).length;
  await click('[data-comparison-mode="bear_volume_zones"]'); await click('[data-comparison-mode="geography"]'); await click('#close-comparison');
  await click('#cluster-periods input[value="retro"]');
  assert.equal(await evaluate("document.querySelector('input[name=\"analysis-mode\"]:checked').value"),'geography');
  assert.equal(requests.filter(r=>r.url.endsWith('/run')).length,runs);
  assert.equal(requests.filter(r=>r.url.endsWith('/compare')).length,compares);
  await openPoint(); await waitFor("document.querySelector('[data-origin-fias=\"a\"]')");
  await record('09-cached-comparison-p2',{requestFree:true,mode:'geography',summaryRestored:true});
  await click('#cluster-periods input[value="retro"]');
  await fetch('http://127.0.0.1:5067/fixture/add-origin',{method:'POST'});
  // Choose an uncached destination through its cluster.
  const target=all.points.find(p=>p.id==='synthetic-01');
  await click('#point-details-close');
  await click(`[data-cluster-id="${target.cluster_id}"]`); await click('[data-point-id="synthetic-01"]');
  await waitFor("document.querySelector('.origin-summary').textContent.includes('Пересчитайте')");
  assert.equal(lastBody('point-origins').code,'STALE_DATA_SNAPSHOT');
  await record('10-p1-source-rejected',{oldOrigins:34,error:'STALE_DATA_SNAPSHOT',noNewOrigin:true});
  failNextRun=true; await run();
  assert.ok(await evaluate("document.getElementById('analysis-form-error').textContent.includes('Synthetic refresh failure')"));
  await record('11-p1-refresh-failure',{oldResultVisible:true});
  await run(); const fresh=lastBody('run');
  assert.equal(fresh.analysis.origin_fiases.length,35); assert.notEqual(fresh.data_snapshot,all.data_snapshot);
  await openPoint(); await click('[data-origin-fias="a"]'); await waitFor("document.querySelectorAll('.pulse-table tbody tr').length===50");
  await record('12-p1-fresh-recovery',{origins:35,newSnapshot:fresh.data_snapshot,oldSnapshot:all.data_snapshot,rows:50});
  await fetch('http://127.0.0.1:5067/fixture/evict',{method:'POST'});
  await click('#point-details-close');
  const t=fresh.points.find(p=>p.id==='synthetic-01');
  await click(`[data-cluster-id="${t.cluster_id}"]`); await click('[data-point-id="synthetic-01"]');
  await waitFor("document.querySelector('.origin-summary').textContent.includes('недоступен')");
  assert.equal(lastBody('point-origins').code,'RESULT_UNAVAILABLE');
  await record('13-eviction-recovery-required',{error:'RESULT_UNAVAILABLE',noSummaryRetry:true});
  await run(); await openPoint(); await waitFor("document.querySelector('[data-origin-fias=\"a\"]')");
  await record('14-eviction-recalculated',{successfulFreshSummary:true});
  // Region and price edits also leave the displayed saved summary unchanged.
  const before=await evaluate("document.querySelector('.origin-summary').textContent");
  await click('#cluster-prices input[value="tender"]');
  await click('#cluster-region'); await key('Home','Home',36); await key('Enter','Enter',13); await pause(350);
  assert.equal(await evaluate("document.querySelector('.origin-summary').textContent"),before);
  await record('15-region-price-frozen',{region:'',summaryUnchanged:true});
} finally {
  await writeFile(new URL('live-observations.json', root),JSON.stringify(evidence,null,2));
  await writeFile(new URL('live-network.json',root),JSON.stringify({requests,responses},null,2));
  if(socket?.readyState===1){await send('Browser.close').catch(()=>{});socket.close();}
  if(browser.exitCode===null&&browser.signalCode===null)browser.kill();
}
