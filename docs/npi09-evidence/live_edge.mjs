import {spawn} from 'node:child_process';
import {readFile, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const root = new URL('./', import.meta.url);
const profile = new URL(`../../.scratch/npi09-live-edge-${Date.now()}/`, root);
const browser = spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ['--disable-gpu', '--no-first-run', '--remote-debugging-port=0',
    `--user-data-dir=${fileURLToPath(profile)}`, 'about:blank'],
  {windowsHide: true, stdio: ['ignore', 'ignore', 'pipe']});
let diagnostics = '', socket, id = 0;
browser.stderr.on('data', chunk => diagnostics += chunk);
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const pending = new Map(), requests = [], responses = [], evidence = [];
let failNextRun = false, failNextSummary = false, failNextRows = false, holdNextRows=false, heldRowRequest;
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
      if(reply.params.request.url.endsWith('/js/ol.js')) {
        const body=await send('Fetch.getResponseBody',{requestId});
        const source=body.base64Encoded?Buffer.from(body.body,'base64').toString():body.body;
        await send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/javascript'}],
          body:Buffer.from(source+';ol.Map=new Proxy(ol.Map,{construct(target,args){const map=Reflect.construct(target,args);window.fixtureMap=map;return map}});').toString('base64')});return;
      }
      if(holdNextRows && reply.params.request.url.endsWith('/point-rows')) {holdNextRows=false;heldRowRequest=requestId;return;}
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
  await send('Fetch.enable', {patterns: [{urlPattern: '*/api/clustering/*', requestStage: 'Request'},{urlPattern:'*/js/ol.js',requestStage:'Response'}]});
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
    if (!await evaluate(`document.querySelector('[data-point-id="${id}"]')?.offsetParent`)) await click('.cluster-card');
    await click(`[data-point-id="${id}"]`); await pause(450);
  };
  await click('#all-origins'); await setRegion('Region A'); await run();
  const first=lastBody('run');
  assert.equal(first.points.length,13);assert.equal(first.data_quality.source_row_count,25);
  const labels = async () => evaluate(`(()=>{const m=fixtureMap,l=m.getLayers().getArray().find(l=>l.getSource()?.getFeatures?.().some(f=>f.get('isProductLabel')));return l?l.getSource().getFeatures().filter(f=>f.get('isProductLabel')).map(f=>({cluster:f.get('clusterId'),text:l.getStyle()(f).getText().getText(),coordinates:ol.proj.toLonLat(f.getGeometry().getCoordinates())})):[]})()`);
  const check = async result => {
    const rendered=await labels(); assert.equal(rendered.length,result.clusters.length);
    for(const c of result.clusters){
      const r=c.representative,p=result.points.find(p=>p.id===r.point_id);
      assert.ok(c.point_ids.includes(r.point_id));assert.equal(p.cluster_id,c.cluster_id);
      assert.notEqual(r.point_id,'p12');assert.deepEqual([r.lat,r.lon],[p.lat,p.lon]);
      const label=rendered.find(l=>l.cluster===c.cluster_id);
      assert.ok(Math.abs(label.coordinates[0]-r.lon)<1e-9 && Math.abs(label.coordinates[1]-r.lat)<1e-9);
      const expected=(r.name && r.name!=='<missing>'?r.name:'Название недоступно')+' · FIAS: '+r.point_id;
      assert.ok(label.text.endsWith(expected));
      await click(`[data-cluster-id="${c.cluster_id}"]`);
      assert.equal(await evaluate("document.querySelector('#cluster-detail-metrics .metric-row strong').textContent"),expected);
      assert.ok(await evaluate("document.querySelector('#cluster-detail-metrics .metric-row').textContent.includes('Временный ориентир (medoid)')"));
      await click('#cluster-detail-metrics .help');
      await record(`mode-${result.analysis.mode}-cluster-${c.cluster_id}`,{representative:r,map:label,expected,memberIds:c.point_ids});
      await click('#cluster-details-close');
    }
    return rendered;
  };
  await check(first);
  await record('01-real-geography',{sourceRows:25,points:13,unresolved:first.points.find(p=>p.id==='p12'),table:first.cluster_table});
  await click('#compare-modes'); await waitFor("document.querySelectorAll('[data-comparison-mode]').length===5");
  const comparison=lastBody('compare');const counts=()=>requests.filter(r=>r.url.endsWith('/run')||r.url.endsWith('/compare')).length;
  const before=counts();
  for(const mode of ['geography','geo_cost','geo_volume','bear_zones','bear_volume_zones']){
    await click(`[data-show-on-map="${mode}"]`);
    await check(comparison.results[mode]);
    await click('#compare-modes');await waitFor("document.querySelectorAll('[data-comparison-mode]').length===5");
  }
  assert.equal(counts(),before);
  await record('02-request-free-five-mode-comparison',{clusterCounts:Object.fromEntries(Object.entries(comparison.results).map(([m,r])=>[m,r.clusters.length])),requestFree:true});
  await click('[data-comparison-mode="bear_volume_zones"]');await click('#close-comparison');
  const volume=comparison.results.bear_volume_zones;
  await click('.cluster-card');
  assert.equal(await evaluate("document.querySelector('#cluster-detail-metrics .metric-row strong').textContent"),'Название недоступно · FIAS: p0');
  await record('03-missing-name-real-member',{representative:volume.clusters[0].representative,explicitUnavailable:true});
  // Native map label click retains cluster selection, then native point/source/up controls.
  await pause(700);
  const r=volume.clusters[0].representative;
  const labelPixel=await evaluate(`(()=>{const m=fixtureMap,p=m.getPixelFromCoordinate(ol.proj.fromLonLat([${r.lon},${r.lat}])),b=m.getTargetElement().getBoundingClientRect();return{x:b.x+p[0],y:b.y+p[1]-18}})()`);
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',...labelPixel});
  await send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...labelPixel});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...labelPixel});await pause(300);
  assert.equal(await evaluate("document.getElementById('cluster-details').classList.contains('hidden')"),false);
  await click('[data-point-id="p0"]');await waitFor("document.querySelector('[data-origin-fias=\"a\"]')");
  await click('[data-origin-fias="a"]');await waitFor("document.querySelector('.pulse-table tbody tr')");
  const navCount=counts(),mapBefore=await evaluate("[fixtureMap.getView().getCenter(),fixtureMap.getView().getZoom()]");
  await record('04-origin-rows',{row:lastBody('point-rows').rows[0],representative:volume.clusters[0].representative});
  await click('[data-point-summary]');
  assert.equal(await evaluate('document.activeElement.dataset.originFias'),'a');
  await key('Enter','Enter',13);
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9,modifiers:8});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9,modifiers:8});
  assert.equal(await evaluate("document.activeElement.hasAttribute('data-point-summary')"),true);
  await key('Enter','Enter',13);
  await click('#point-details-close');
  assert.equal(counts(),navCount);assert.deepEqual(await evaluate("[fixtureMap.getView().getCenter(),fixtureMap.getView().getZoom()]"),mapBefore);
  assert.equal(await evaluate('document.activeElement.dataset.pointId'),'p0');
  await record('05-native-keyboard-drill-up',{focusedPoint:'p0',shiftTabEnterUp:true,noReclustering:true,mapPreserved:true});
  // Return to saved Geography for non-city name, form edits, and generation rejection.
  await click('#compare-modes');await waitFor("document.querySelectorAll('[data-comparison-mode]').length===5");
  await click('[data-comparison-mode="geography"]');await click('#close-comparison');
  const geo=comparison.results.geography,c=geo.clusters[0];
  await click(`[data-cluster-id="${c.cluster_id}"]`);
  const text=await evaluate("document.querySelector('#cluster-detail-metrics .metric-row strong').textContent");
  const frozenLabels=await labels(),table=await evaluate("document.querySelector('#cluster-table-panel tbody').textContent");
  await click('#cluster-periods input[value="retro"]');
  assert.equal(await evaluate("document.querySelector('#cluster-detail-metrics .metric-row strong').textContent"),text);
  assert.deepEqual(await labels(),frozenLabels);assert.equal(await evaluate("document.querySelector('#cluster-table-panel tbody').textContent"),table);
  await record('06-frozen-form-edit',{text,frozenLabels,tableUnchanged:true,stale:await evaluate("!document.getElementById('analysis-stale').classList.contains('hidden')")});
  await fetch('http://127.0.0.1:5069/fixture/change-source',{method:'POST'});
  const p=c.point_ids.find(id=>id!=='p0');await click(`[data-point-id="${p}"]`);
  await waitFor("document.querySelector('.origin-summary').textContent.includes('Пересчитайте')");
  assert.equal(lastBody('point-origins').code,'STALE_DATA_SNAPSHOT');assert.deepEqual(await labels(),frozenLabels);
  await record('07-rejected-source-frozen-medoid',{error:lastBody('point-origins'),labels:frozenLabels});
  await click('#cluster-periods input[value="retro"]');await run();
  const fresh=lastBody('run');assert.notEqual(fresh.data_snapshot,geo.data_snapshot);await check(fresh);
  await record('08-fresh-recalculation',{oldSnapshot:geo.data_snapshot,newSnapshot:fresh.data_snapshot,origins:fresh.analysis.origin_fiases});
} finally {
  await writeFile(new URL('live-observations.json', root),JSON.stringify(evidence,null,2));
  await writeFile(new URL('live-network.json',root),JSON.stringify({requests,responses},null,2));
  if(socket?.readyState===1){await send('Browser.close').catch(()=>{});socket.close();}
  if(browser.exitCode===null&&browser.signalCode===null)browser.kill();
}
