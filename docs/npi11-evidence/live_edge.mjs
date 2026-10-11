import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';

const root=new URL('./',import.meta.url), base=process.env.NPI11_BASE;
const profile=new URL(`../../.scratch/npi11-edge-${Date.now()}/`,root);
const browser=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ['--disable-gpu','--no-first-run','--remote-debugging-port=0',`--user-data-dir=${fileURLToPath(profile)}`,'about:blank'],
  {windowsHide:true,stdio:['ignore','ignore','pipe']});
let socket,id=0,diagnostics='',saved,expected,hold=false,held,offline=false;
browser.stderr.on('data',chunk=>diagnostics+=chunk);
const pending=new Map(),requests=[],responses=[],downloads=[],evidence=[],finished=new Set();
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const send=(method,params={})=>new Promise((resolve,reject)=>{pending.set(++id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});
const evaluate=async expression=>{
  const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
  if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;
};
const waitFor=async expression=>{for(let i=0;i<120;i++){if(await evaluate(expression))return;await pause(100);}throw Error('Timeout: '+expression);};
const click=async selector=>{
  await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'center',behavior:'instant'})`);
  await pause(100);
  const p=await evaluate(`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return{x:r.x+r.width/2,y:r.bottom<=60?r.y+r.height/2:(Math.max(60,r.top)+Math.min(innerHeight,r.bottom))/2}})()`);
  console.log('click '+selector+' '+JSON.stringify(p)+' hit '+await evaluate(`document.elementFromPoint(${p.x},${p.y})?.outerHTML.slice(0,200)`));
  await send('Input.dispatchMouseEvent',{type:'mouseMoved',...p});
  await send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...p});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...p});await pause(150);
};
const key=async(key,code,vk)=>{
  await send('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:vk,...(key==='Enter'?{text:'\r'}:{})});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:vk});await pause(150);
};
const record=async name=>{
  const facts=await evaluate(`({status:document.getElementById('export-status').textContent,focus:document.activeElement.id,tableHidden:document.getElementById('cluster-table-panel').classList.contains('hidden'),collapsed:document.getElementById('cluster-table-panel').classList.contains('collapsed')})`);
  evidence.push({name,facts});
  const shot=await send('Page.captureScreenshot',{format:'png'});
  await writeFile(new URL(name+'.png',root),Buffer.from(shot.data,'base64'));
  console.log(JSON.stringify({name,facts}));
};
const run=async()=>{await click('#btn-run-clustering');await waitFor("!document.getElementById('btn-run-clustering').disabled");await pause(300);};
const last=path=>responses.filter(r=>r.url.endsWith('/'+path)&&r.body?.ok).at(-1)?.body;
const countRuns=()=>requests.filter(r=>/\/(run|compare)$/.test(r.url)).length;
const prepare=async()=>{
  expected={saved,headers:await evaluate("[...document.querySelectorAll('#cluster-table-panel thead button')].map(e=>e.textContent)"),
    tableLabels:await evaluate("[...document.querySelectorAll('#cluster-table-panel tbody tr th button')].map(e=>e.textContent)")};
};
const download=async(keyboard=false,after_change=false)=>{
  const before=countRuns(),n=downloads.length;await prepare();expected.after_change=after_change;
  if(keyboard){await evaluate("document.getElementById('btn-export-clustering').focus()");await key('Enter','Enter',13);}
  else await click('#btn-export-clustering');
  await waitFor("document.getElementById('export-controls').getAttribute('aria-busy')==='false'");
  for(let i=0;i<100&&(!downloads[n]||!finished.has(downloads[n].guid));i++)await pause(100);
  assert.equal(downloads.length,n+1);assert.ok(finished.has(downloads[n].guid));assert.equal(countRuns(),before);
  await pause(150);return downloads[n];
};
const fixture=async path=>{assert.ok((await fetch(base+'/fixture/'+path,{method:'POST'})).ok);};
try{
  let port;for(let i=0;i<200&&!port;i++){try{port=(await readFile(new URL('DevToolsActivePort',profile),'utf8')).split('\n')[0];}catch{await pause(50);}}
  if(!port)throw Error(diagnostics);
  const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
  socket.addEventListener('message',async event=>{
    const r=JSON.parse(event.data);
    if(r.id){const p=pending.get(r.id);pending.delete(r.id);r.error?p.reject(r.error):p.resolve(r.result);return;}
    if(r.method==='Network.requestWillBeSent'&&r.params.request.url.includes('/api/clustering/')) requests.push({id:r.params.requestId,...r.params.request});
    if(r.method==='Network.responseReceived'&&r.params.response.url.includes('/api/clustering/')) responses.push({id:r.params.requestId,...r.params.response});
    if(r.method==='Network.loadingFinished'){
      const response=responses.find(item=>item.id===r.params.requestId);
      if(response){try{
        const b=await send('Network.getResponseBody',{requestId:response.id});
        if(response.mimeType==='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'){
          response.bodyUnavailable=b.body.length===0;
        }else response.body=JSON.parse(b.body);
      }catch(error){response.bodyError=String(error);}}
    }
    if(r.method==='Browser.downloadWillBegin') downloads.push({...r.params,...expected});
    if(r.method==='Browser.downloadProgress'&&r.params.state==='completed')finished.add(r.params.guid);
    if(r.method==='Fetch.requestPaused'){
      if(hold){held=r.params.requestId;hold=false;}
      else if(offline){offline=false;await send('Fetch.failRequest',{requestId:r.params.requestId,errorReason:'ConnectionReset'});}
      else await send('Fetch.continueRequest',{requestId:r.params.requestId});
    }
  });
  await send('Page.enable');await send('Network.enable');
  await send('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:process.env.NPI11_DOWNLOADS,eventsEnabled:true});
  await send('Fetch.enable',{patterns:[{urlPattern:'*/api/clustering/export',requestStage:'Request'}]});
  await send('Emulation.setDeviceMetricsOverride',{width:1600,height:1100,deviceScaleFactor:1,mobile:false});
  await send('Emulation.setFocusEmulationEnabled',{enabled:true});
  evidence.push({environment:await send('Browser.getVersion'),base,headed:true,fixture:'synthetic only'});
  await send('Page.navigate',{url:base});
  await waitFor("document.getElementById('status-text').textContent==='Данные готовы'");
  await click('#all-origins');await pause(300);
  await evaluate("(()=>{const r=document.getElementById('cluster-region');r.value='Region A';r.dispatchEvent(new Event('change',{bubbles:true}));})()");
  await waitFor("!document.getElementById('btn-run-clustering').disabled");await run();saved=last('run');
  if(!saved){await record('debug-startup');console.log(JSON.stringify(await evaluate("({all:document.getElementById('all-origins').checked,region:document.getElementById('cluster-region').value,error:document.getElementById('analysis-form-error').textContent,disabled:document.getElementById('cluster-region').disabled})")));console.log(JSON.stringify(requests));}assert.ok(saved);
  await click('[data-sort-key="weighted_route_length"]');
  await click('[data-table-toggle]');
  await download(true);await record('01-keyboard-sorted-collapsed-all');
  assert.equal(requests.filter(r=>r.url.endsWith('/export')).at(-1).postData.includes('"all_origins":true'),true);
  await click('input[name="analysis-mode"][value="bear_zones"]');
  await download();await record('02-form-edited-frozen-geography');
  assert.equal(requests.filter(r=>r.url.endsWith('/export')).at(-1).postData.includes('"mode":"geography"'),true);
  // Compare on the same selected dataset; cached modes are activated using actual UI buttons.
  await click('#compare-modes');await waitFor("document.querySelectorAll('[data-show-on-map]').length===5");await pause(250);
  const comparison=last('compare');assert.ok(comparison);
  for(const mode of ['geo_cost','geo_volume','geography','bear_zones','bear_volume_zones']){
    await click(`[data-show-on-map="${mode}"]`);saved=comparison.results[mode];
    if(mode.startsWith('bear')){
      assert.equal(await evaluate("document.getElementById('btn-export-clustering').getAttribute('aria-disabled')"),'true');
      await record('mode-'+mode+'-unsupported');
    }else{await download();await record('mode-'+mode+'-download');}
    await click('#compare-modes');await waitFor("document.querySelectorAll('[data-show-on-map]').length===5");
  }
  await click('[data-show-on-map="geo_cost"]');saved=comparison.results.geo_cost;
  await click('input[name="analysis-mode"][value="bear_volume_zones"]');
  await download();await record('03-cached-cost-after-bear-edit');
  // Equivalent manual selection after All must keep its independently observed intent.
  await click('#all-origins');
  for(let i=0;i<3;i++){
    await click('#cluster-origin');await evaluate("(()=>{const e=document.getElementById('cluster-origin');e.value='';e.dispatchEvent(new Event('input',{bubbles:true}));})()");await pause(400);
    await waitFor("document.querySelectorAll('.combo-option').length===3");
    await click(`.combo-option[data-origin-index="${i}"]`);await pause(350);
  }
  await evaluate("(()=>{const r=document.getElementById('cluster-region');r.value='Region A';r.dispatchEvent(new Event('change',{bubbles:true}));})()");await pause(300);
  await click('input[name="analysis-mode"][value="geography"]');await run();saved=last('run');
  await download();assert.ok(saved.analysis.selection_intent.origin_fiases);await record('04-equivalent-manual-intent');
  const n=downloads.length;
  await fixture('fail/writer');await click('#btn-export-clustering');await waitFor("document.getElementById('export-status').textContent.includes('EXPORT_FAILED')");await record('05-writer-error-retry');
  assert.equal(downloads.length,n);await download();
  offline=true;await click('#btn-export-clustering');await waitFor("document.getElementById('export-status').textContent.includes('EXPORT_CONNECTION_ERROR')");await record('06-connection-error');assert.equal(downloads.length,n+1);
  for(const action of ['cancel','hide','run']){
    hold=true;held=null;await click('#btn-export-clustering');
    for(let i=0;i<100&&!held;i++)await pause(50);assert.ok(held);await record('pending-'+action);
    if(action==='cancel')await click('#btn-cancel-export');
    if(action==='hide'){await click('[data-view="data"]');await click('[data-view="clustering"]');}
    if(action==='run'){await click('input[name="analysis-mode"][value="geo_volume"]');await run();saved=last('run');}
    await send('Fetch.continueRequest',{requestId:held}).catch(()=>{});await pause(500);
    assert.equal(downloads.length,n+1);await record('cancelled-'+action);
  }
  await fixture('fail/during');await click('#btn-export-clustering');await waitFor("document.getElementById('export-status').textContent.includes('STALE_DATA_SNAPSHOT')");
  await record('07-source-changed-during-generation');assert.equal(downloads.length,n+1);
  assert.equal(await evaluate("document.getElementById('btn-export-clustering').getAttribute('aria-disabled')"),'true');
  await run();saved=last('run');await download(false,true);await record('08-fresh-recovery');
  await fixture('change');await click('#btn-export-clustering');await waitFor("document.getElementById('export-status').textContent.includes('STALE_DATA_SNAPSHOT')");await record('09-source-changed-before-export');
  await run();saved=last('run');await fixture('restart');await click('#btn-export-clustering');await waitFor("document.getElementById('export-status').textContent.includes('RESULT_UNAVAILABLE')");await record('10-restart-unavailable');
  await run();saved=last('run');await download(false,true);await record('11-restart-recovery');
  await pause(400);
  await writeFile(new URL('network.json',root),JSON.stringify({requests,responses,downloads},null,2));
  await writeFile(new URL('live-observations.json',root),JSON.stringify(evidence,null,2));
  for(const file of downloads){
    const data=await readFile(process.env.NPI11_DOWNLOADS+'/'+file.guid);
    const sha=createHash('sha256').update(data).digest('hex');
    assert.ok(responses.some(r=>Object.entries(r.headers).some(([key,value])=>key.toLowerCase()==='x-fixture-sha256'&&value===sha)), 'download must equal server attachment bytes');
  }
  await writeFile(new URL('network.json',root),JSON.stringify({requests,responses,downloads},null,2));
  await writeFile(new URL('live-observations.json',root),JSON.stringify(evidence,null,2));
  await send('Browser.close');
}finally{
  socket?.close();if(browser.exitCode===null)browser.kill();
}
