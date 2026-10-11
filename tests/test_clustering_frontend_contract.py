from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_xlsx_transport_returns_exact_binary_and_safe_attachment():
    source = _read('frontend/js/api.js').replace('export ', '')
    actual = _run_node_script(f"""
      globalThis.window = {{location: {{origin: 'http://localhost'}}}};
      {source}
      const bytes = Uint8Array.from([80,75,3,4,1,2,3,4,80,75,5,6,...Array(18).fill(0)]);
      let request;
      globalThis.fetch = async (url, options) => {{
        request = {{url, ...options, body: JSON.parse(options.body)}};
        return new Response(bytes, {{headers: {{
          'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'Content-Disposition': 'attachment; filename="saved.xlsx"', 'X-Request-ID': 'binary-test',
        }}}});
      }};
      const result = await exportClustering({{data_snapshot:'s1'}});
      console.log(JSON.stringify({{bytes:[...new Uint8Array(await result.blob.arrayBuffer())],
        filename:result.filename, requestId:result.requestId, cache:request.cache,
        method:request.method, body:request.body}}));
    """)
    assert actual == {'bytes': [80, 75, 3, 4, 1, 2, 3, 4, 80, 75, 5, 6] + [0] * 18,
                      'filename': 'saved.xlsx', 'requestId': 'binary-test', 'cache': 'no-store',
                      'method': 'POST', 'body': {'data_snapshot': 's1'}}


@pytest.mark.parametrize('failure,code', [('network', 'EXPORT_CONNECTION_ERROR'),
    ('timeout', 'EXPORT_TIMEOUT'), ('cancel', 'AbortError'), ('preabort', 'AbortError'),
    ('typed', 'EXPORT_FAILED'), ('mime', 'INVALID_EXPORT_RESPONSE'),
    ('partial', 'INVALID_EXPORT_RESPONSE'), ('attachment', 'INVALID_EXPORT_RESPONSE')])
def test_xlsx_transport_failures_never_return_download(failure, code):
    source = _read('frontend/js/api.js').replace('export ', '')
    actual = _run_node_script(f"""
      globalThis.window={{location:{{origin:'http://localhost'}}}};
      {source}
      const failure={json.dumps(failure)}, caller=new AbortController();
      let expire, called=false;
      if(failure==='timeout') globalThis.setTimeout=callback=>{{expire=callback;return 1;}};
      if(failure==='preabort') caller.abort();
      globalThis.fetch=async(url,init)=>{{
        called=true;
        if(failure==='network') throw new TypeError('Failed to fetch');
        if(failure==='timeout' || failure==='cancel') {{
          failure==='timeout' ? expire() : caller.abort();
          throw new DOMException('Aborted','AbortError');
        }}
        if(failure==='typed') return new Response(JSON.stringify({{code:'EXPORT_FAILED',error:'Safe writer failure'}}),
          {{status:500,headers:{{'Content-Type':'application/json','X-Request-ID':'req-123'}}}});
        return new Response('partial',{{headers:{{'Content-Type':failure==='mime'?'application/json':
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'Content-Disposition':failure==='attachment'?'inline':'attachment; filename="safe.xlsx"'}}}});
      }};
      try {{await exportClustering({{}},{{signal:caller.signal}});console.log('{{"download":true}}');}}
      catch(error) {{console.log(JSON.stringify({{code:typeof error.code==='string'?error.code:error.name,message:error.message,requestId:error.requestId,called}}));}}
    """)
    assert actual['code'] == code, actual
    if failure == 'typed':
        assert actual['message'] == 'Safe writer failure' and actual['requestId'] == 'req-123'
    if failure == 'preabort':
        assert actual['called'] is False


@pytest.mark.parametrize('attachment,filename', [
    ('attachment; filename="../unsafe.xlsx"', 'clustering.xlsx'),
    ('attachment; filename="C:\\unsafe.xlsx"', 'clustering.xlsx'),
    ('attachment; filename="NUL.xlsx"', 'clustering.xlsx'),
    ('attachment; filename="unsafe.exe"', 'clustering.xlsx'),
    ("attachment; filename*=UTF-8''%D0%A2%D0%B0%D0%B1%D0%BB%D0%B8%D1%86%D0%B0.xlsx", 'Таблица.xlsx'),
    ("attachment; filename*=UTF-8''%ZZ; filename=backup.xlsx", 'backup.xlsx'),
])
def test_xlsx_attachment_filename_cannot_create_a_path(attachment, filename):
    source = _read('frontend/js/api.js').replace('export ', '')
    actual = _run_node_script(f"""
      globalThis.window={{location:{{origin:'http://localhost'}}}};
      {source}
      globalThis.fetch=async()=>new Response(Uint8Array.from([80,75,3,4,80,75,5,6,...Array(18).fill(0)]),
        {{headers:{{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition':{json.dumps(attachment)}}}}});
      console.log(JSON.stringify({{filename:(await exportClustering({{}})).filename}}));
    """)
    assert actual['filename'] == filename


def _edge_path() -> str | None:
    executable = shutil.which("msedge")
    if executable:
        return executable
    candidates = (
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    )
    return next((str(path) for path in candidates if path.exists()), None)


def _run_browser_script(script: str) -> dict:
    edge = _edge_path()
    if edge is None:
        if os.environ.get("REQUIRE_FRONTEND_BROWSER") == "1":
            raise RuntimeError("Required Edge browser is unavailable")
        pytest.skip("A browser JavaScript runtime is required for the frontend contract")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        page = root / "frontend-contract.html"
        profile = root / "profile"
        page.write_text(
            f'<!doctype html><meta charset="utf-8"><body><script>{script}</script></body>',
            encoding="utf-8",
        )
        return _run_node_script(f"""
          import {{spawn}} from 'node:child_process';
          import {{readFile}} from 'node:fs/promises';
          const browser = spawn({json.dumps(edge)}, [
            '--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=0',
            {json.dumps(f'--user-data-dir={profile}')}, 'about:blank',
          ], {{windowsHide: true, stdio: ['ignore', 'ignore', 'pipe']}});
          let diagnostics = '';
          browser.stderr.on('data', chunk => {{diagnostics += chunk;}});
          browser.on('error', error => {{diagnostics += error.message;}});
          const pause = () => new Promise(resolve => setTimeout(resolve, 50));
          let socket;
          let deadline;
          try {{
            await Promise.race([
              new Promise((_, reject) => {{
                deadline = setTimeout(() => reject(new Error('Edge execution timed out')), 20000);
              }}),
              (async () => {{
            let port;
            for (let attempt = 0; attempt < 200 && !port; attempt++) {{
              try {{ port = (await readFile({json.dumps(str(profile / 'DevToolsActivePort'))}, 'utf8')).split('\\n')[0]; }} catch {{ await pause(); }}
            }}
            if (!port) throw new Error('Edge startup failed: ' + diagnostics);
            const tabs = await (await fetch(`http://127.0.0.1:${{port}}/json/list`)).json();
            socket = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl);
            await new Promise((resolve, reject) => {{
              socket.addEventListener('open', resolve, {{once: true}});
              socket.addEventListener('error', reject, {{once: true}});
            }});
            let id = 0;
            const pending = new Map();
            socket.addEventListener('message', event => {{
              const reply = JSON.parse(event.data);
              if (!reply.id) return;
              const request = pending.get(reply.id);
              pending.delete(reply.id);
              reply.error ? request.reject(reply.error) : request.resolve(reply.result);
            }});
            const send = (method, params = {{}}) => new Promise((resolve, reject) => {{
              pending.set(++id, {{resolve, reject}});
              socket.send(JSON.stringify({{id, method, params}}));
            }});
            // Headless focus must be deterministic for the existing keyboard assertions.
            await send('Emulation.setDeviceMetricsOverride', {{width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false}});
            await send('Emulation.setFocusEmulationEnabled', {{enabled: true}});
            await send('Page.navigate', {{url: {json.dumps(page.as_uri())}}});
            for (let attempt = 0; attempt < 200; attempt++) {{
              const reply = await send('Runtime.evaluate', {{expression: 'document.body?.dataset.result', returnByValue: true}});
              if (reply.result.value) {{ console.log(reply.result.value); break; }}
              if (attempt === 199) throw new Error('Frontend browser script produced no result');
              await pause();
            }}
            await send('Browser.close');
              }})(),
            ]);
          }} finally {{
            clearTimeout(deadline);
            socket?.close();
            if (browser.pid && browser.exitCode === null && browser.signalCode === null) {{
              const closed = new Promise(resolve => browser.once('close', resolve));
              browser.kill();
              await closed;
            }}
          }}
        """)


def _run_node_script(script: str) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "frontend-contract.mjs"
        path.write_text(script, encoding="utf-8")
        completed = subprocess.run(
            ["node", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.mark.parametrize("mode", ["geography", "geo_cost", "geo_volume", "bear_zones", "bear_volume_zones"])
@pytest.mark.parametrize("name,expected", [
    ("деревня Ориентир <&>", "деревня Ориентир <&> · FIAS: member-b"),
    ("<missing>", "Название недоступно · FIAS: member-b"),
    ("", "Название недоступно · FIAS: member-b"),
    ("Synthetic" * 30, "Synthetic" * 30 + " · FIAS: member-b"),
])
def test_saved_medoid_name_and_id_are_visible_in_cluster_inspector(mode, name, expected):
    representative_id = "01234567-89ab-cdef-0123-456789abcdef"
    expected = expected.replace("member-b", representative_id)
    formatters = _read("frontend/js/clustering/formatters.js").replace("export ", "")
    inspector = re.sub(r"^import .*?;\n", "", _read("frontend/js/clustering/inspector.js"), flags=re.MULTILINE).replace("export ", "")
    html = re.search(r"<body[^>]*>([\s\S]*?)</body>", _read("frontend/index.html"))[1]
    html = re.sub(r"<script[\s\S]*?</script>", "", html)
    actual = _run_browser_script(f"""
      document.head.innerHTML += '<style>' + {json.dumps(_read('frontend/css/style.css'))} + '</style>';
      document.body.innerHTML = {json.dumps(html)};
      {formatters}
      {inspector}
      const cluster = {{cluster_id:0, point_ids:['member-a',{json.dumps(representative_id)}], point_count:2,
        medoid_point_id:{json.dumps(representative_id)}, representative:{{type:'medoid', point_id:{json.dumps(representative_id)}, name:{json.dumps(name)}}}}};
      const result = {{status:'success', analysis:{{mode:{json.dumps(mode)}, parameters:{{}}, filters:{{}}}},
        clusters:[cluster], points:[], data_quality:{{}}, metrics:{{}}, graph_metrics:{{}}}};
      const state = {{result:{{data:result}}, form:{{mode:'unrelated', destinationRegion:'Changed'}}, ui:{{selectedCluster:0}}}};
      renderInspector(state);
      const row = document.querySelector('#cluster-detail-metrics .metric-row');
      document.body.dataset.result = JSON.stringify({{label:row.querySelector('span').textContent,
        value:row.querySelector('strong').textContent, injected:!!row.querySelector('strong > *'),
        fits:row.scrollWidth <= row.clientWidth}});
    """)
    assert actual["value"] == expected
    assert "Временный ориентир (medoid)" in actual["label"]
    assert actual["injected"] is False
    assert actual["fits"] is True


@pytest.mark.parametrize("mode,prefix", [("geography", "C1"), ("geo_cost", "C1"), ("geo_volume", "C1"), ("bear_zones", "B1"), ("bear_volume_zones", "V1")])
@pytest.mark.parametrize("name,expected", [("село Ориентир", "село Ориентир"), ("<missing>", "Название недоступно")])
def test_map_medoid_label_is_at_saved_member_not_centroid(mode, prefix, name, expected):
    formatters = _read("frontend/js/clustering/formatters.js").replace("export ", "")
    map_module = re.sub(r"^import .*?;\n", "", _read("frontend/js/map.js"), flags=re.MULTILINE).replace("export ", "")
    actual = _run_browser_script(f"""
      {_read('frontend/js/ol.js')}
      {formatters}
      {map_module}
      document.body.innerHTML = '<div id="map" style="width:800px;height:600px"></div><div id="popup"><div id="popup-content"></div><button id="popup-closer"></button></div>';
      const map = initMap('map');
      const points = [{{id:'member-a', lat:55, lon:37, cluster_id:0}},
        {{id:'member-b', lat:55, lon:37.02, cluster_id:0}},
        {{id:'unresolved', lat:null, lon:null, cluster_id:null}}];
      const cluster = {{cluster_id:0, point_ids:['member-a','member-b'], medoid_point_id:'member-b',
        centroid:{{x:0,y:0}}, representative:{{point_id:'member-b', name:{json.dumps(name)}, lat:55, lon:37.02}}}};
      const result = {{analysis:{{mode:{json.dumps(mode)}}}, points, clusters:[cluster]}};
      renderClusteringPoints(result);
      const layer = map.getLayers().getArray().find(l => l.getSource()?.getFeatures?.().some(f => f.get('isProductLabel')));
      const label = layer.getSource().getFeatures().find(f => f.get('isProductLabel'));
      const style = layer.getStyle()(label);
      const coordinates = ol.proj.toLonLat(label.getGeometry().getCoordinates());
      const text = style.getText().getText();
      renderClusteringPoints({{...result, clusters:[]}});
      document.body.dataset.result = JSON.stringify({{text, coordinates,
        labelsAfterEmpty:layer.getSource().getFeatures().filter(f => f.get('isProductLabel')).length}});
    """)
    assert actual["text"] == f"{prefix} · medoid\n{expected} · FIAS: member-b"
    assert actual["coordinates"] == pytest.approx([37.02, 55])
    assert actual["labelsAfterEmpty"] == 0



def test_all_intent_is_explicit_and_resolution_does_not_make_form_stale():
    module = _read("frontend/js/clustering/state.js").replace("export ", "")
    actual = _run_node_script(f"""
      {module}
      const form = {{allOrigins: true, origins: [{{fias_id: 'a'}}], destinationRegion: 'R',
        periodTypes: ['current'], priceTypes: ['spot'], vehicleTypes: [], tonnageIds: [],
        mode: 'geography', kMode: 'auto'}};
      const request = buildRequest(form);
      const frozen = {{...request, origin_fiases: ['a', 'b', 'outside-suggestions']}};
      delete frozen.all_origins;
      const result = {{status: 'success', data_snapshot: 's', analysis: {{frozen_request: frozen,
        selection_intent: {{all_origins: true}}}}}};
      const state = {{form, result: {{cache: new Map()}}, ui: {{}}}};
      setResult(state, result, request);
      const unchanged = !isResultStale(state);
      form.allOrigins = false;
      form.origins = frozen.origin_fiases.map(fias_id => ({{fias_id}}));
      console.log(JSON.stringify({{selector: request.all_origins, mixed: 'origin_fiases' in request,
        unchanged, switched: isResultStale(state), frozen: result.analysis.frozen_request.origin_fiases,
        intent: state.result.requestSnapshot.all_origins,
        separateCache: requestSignature(request) !== requestSignature(buildRequest(form))}}));
    """)
    assert actual == {"selector": True, "mixed": False, "unchanged": True, "switched": True,
                      "frozen": ["a", "b", "outside-suggestions"], "intent": True, "separateCache": True}

def test_explicit_origin_set_requests_are_canonical_and_freeze_independent_of_form():
    module = _read("frontend/js/clustering/state.js").replace("export ", "")
    actual = _run_node_script(f"""
      {module}
      const form = {{origins: [{{fias_id: 'b'}}, {{fias_id: 'a'}}, {{fias_id: 'b'}}],
        destinationRegion: 'R', periodTypes: ['current'], priceTypes: ['spot'],
        vehicleTypes: [], tonnageIds: [], mode: 'geography', kMode: 'auto'}};
      const request = buildRequest(form);
      const state = {{form, result: {{cache: new Map()}}, ui: {{}}}};
      setResult(state, {{status: 'success', data_snapshot: 's'}}, request);
      form.origins = [{{fias_id: 'a'}}];
      console.log(JSON.stringify({{
        selected: request.origin_fiases,
        scalar: 'origin_fias' in request,
        saved: state.result.requestSnapshot.origin_fiases,
        stale: isResultStale(state),
        canonical: requestSignature(request) === requestSignature(buildRequest({{...form,
          origins: [{{fias_id: 'a'}}, {{fias_id: 'b'}}]}})),
        empty: datasetSnapshot({{...form, origins: []}}).origin_fiases,
        legacy: datasetSnapshot({{...form, origins: undefined, origin: {{fias_id: 'a'}}}}).origin_fias,
      }}));
    """)
    assert actual == {
        "selected": ["a", "b"], "scalar": False, "saved": ["a", "b"],
        "stale": True, "canonical": True, "empty": [], "legacy": "a",
    }


def test_unavailable_result_invalidates_equivalent_comparison_copy_only():
    module = _read("frontend/js/clustering/state.js").replace("export ", "")
    assert _run_node_script(f"""
      {module}
      const request = {{origin_fiases: ['a', 'b'], destination_region: 'R',
        mode: 'geography', parameters: {{k_mode: 'auto', n_clusters: 'auto'}}}};
      const saved = {{data_snapshot: 's', analysis: {{mode: 'geography', frozen_request: request}}}};
      const copy = JSON.parse(JSON.stringify(saved));
      const other = {{...saved, analysis: {{mode: 'geo_volume', frozen_request: {{...request, mode: 'geo_volume'}}}}}};
      const detailKey = result => requestSignature({{...result.analysis.frozen_request,
        data_snapshot: 's', destination_fias: 'x'}});
      const state = {{result: {{data: saved, cache: new Map([['run', saved], ['copy', copy], ['other', other]])}},
        comparison: {{cache: new Map([['compare', {{results: {{geography: copy, geo_volume: other}}}}]]),
          results: {{geography: copy, geo_volume: other}}}},
        ui: {{pointRows: new Map([[detailKey(saved), {{status: 'success'}}], [detailKey(other), {{status: 'success'}}]])}}}};
      rejectUnavailableResult(state, saved);
      console.log(JSON.stringify({{keys: [...state.result.cache.keys()],
        variants: Object.keys(state.comparison.results), comparisons: state.comparison.cache.size,
        details: [...state.ui.pointRows.values()].map(detail => detail.status)}}));
    """) == {"keys": ["other"], "variants": ["geo_volume"], "comparisons": 0, "details": ["unavailable", "success"]}


def _product_workspace_script(actions: str) -> str:
    from backend.product_modes import default_product_mode_catalog

    capabilities = [item.as_dict() for item in default_product_mode_catalog().manifest()]
    html = re.search(r"<body[^>]*>([\s\S]*?)</body>", _read("frontend/index.html"))[1]
    html = re.sub(r"<script[\s\S]*?</script>", "", html)
    modules = []
    for filename in ("api", "clustering/state", "clustering/formatters", "clustering/controls",
                     "clustering/inspector", "clustering/table", "clustering/comparison",
                     "clustering/controller"):
        source = re.sub(r"^import[\s\S]*?;\n", "", _read(f"frontend/js/{filename}.js"), flags=re.MULTILINE)
        exports = re.findall(r"export (?:async )?(?:function|const) (\w+)", source)
        assignments = ";".join(f"globalThis.{name} = {name}" for name in exports)
        modules.append("{" + source.replace("export ", "") + assignments + "}")
    return f"""
      document.body.innerHTML = {json.dumps(html)};
      const origins = [{{fias_id: 'b', name: 'Beta', region: 'South'}},
        {{fias_id: 'a', name: 'Alpha', region: 'North'}}];
      const requests = [];
      const options = {{ok: true, mode_capabilities: {json.dumps(capabilities)},
        defaults: {{mode: 'geography', period_types: ['current'], price_types: ['spot']}},
        destination_regions: ['R'], period_types: ['current', 'retro'],
        price_types: ['spot', 'tender'], vehicle_types: [], tonnage_ids: []}};
      let failRun = false, failSearch = false, failRows = false, holdOptions = false, holdSearch = false;
      let revision = 's1', failRevision = false, available = true, revisionErrorCode = 'INTERNAL_ERROR';
      const heldOptions = [];
      const heldSearch = [];
      let originRegions = null;
      globalThis.fetch = async (url, init = {{}}) => {{
        const path = String(url).split('/api/clustering/')[1];
        const payload = init.body ? JSON.parse(init.body) : null;
        requests.push({{path, payload}});
        if (holdOptions && path.startsWith('options')) await new Promise(resolve => heldOptions.push(resolve));
        if (holdSearch && path.startsWith('origins')) await new Promise(resolve => heldSearch.push(resolve));
        let data = options, status = 200;
        if (path === 'revision') {{
          data = {{ok: true, data_snapshot: revision, available: payload.results.map(() => available)}};
          if (failRevision) {{status = 503; data = {{code: revisionErrorCode, error: 'Revision offline'}};}}
        }}
        if (originRegions && path.startsWith('options?')) {{
          const params = new URLSearchParams(path.split('?')[1]);
          const selected = params.getAll('origin_fiases');
          const regions = [...new Set(selected.flatMap(id => originRegions[id] || []))];
          data = {{...options, destination_regions: regions}};
          if (params.get('destination_region') && !regions.includes(params.get('destination_region'))) {{
            status = 422; data = {{code: 'UNKNOWN_DESTINATION_REGION', error: 'Region unavailable'}};
          }}
        }}
        if (path.startsWith('origins')) {{
          data = path.includes('q=missing') ? [] : origins;
          if (failSearch) {{status = 500; data = {{error: 'Catalog offline'}};}}
        }}
        if (path === 'run' || path === 'compare') {{
          data = {{ok: true, status: 'success', data_snapshot: revision,
            analysis: {{mode: payload.mode, parameters: {{k_mode: 'auto', n_clusters: 2}},
              origins, origin_fiases: ['a', 'b'], origin: null, destination_region: 'R',
              filters: {{period_types: ['current'], price_types: ['spot']}},
              selection_intent: payload.all_origins ? {{all_origins: true}} : {{origin_fiases: payload.origin_fiases}},
              frozen_request: payload.all_origins ? {{...payload, all_origins: undefined, origin_fiases: ['a', 'b']}} : payload,
              origin_coverage: [{{fias_id: 'a', zero_match: true}}]}},
            data_quality: {{}}, points: [{{id: 'x', fias_id: 'x', name: 'X', trip_count: 40}}],
            clusters: [], cluster_table: {{supported: true, rows: []}}}};
          if (path === 'compare') data = {{ok: true, results: Object.fromEntries(options.mode_capabilities.map(item => [item.id, {{...data, analysis: {{...data.analysis, mode: item.id, frozen_request: {{...data.analysis.frozen_request, mode: item.id, parameters: {{k_mode: 'auto', n_clusters: 'auto'}}}}}}}}]))}};
          if (failRun) {{status = 422; data = {{error: 'No data matches the selected filters.', code: 'NO_DATA'}};}}
        }}
        if (path === 'point-origins') {{
          data = {{ok: true, origins: [{{origin_fias: 'b', origin_name: 'Beta', origin_regions: ['South'],
            trip_count: 40, weighted_route_length: 300, weighted_price: 6000,
            valid_route_length_trip_count: 30, valid_price_trip_count: 30, warnings: []}}]}};
        }}
        if (path === 'point-rows') {{
          data = {{ok: true, rows: [], total: 0, has_more: false}};
          if (failRows) {{status = 409; data = {{code: 'RESULT_UNAVAILABLE', error: 'Saved result evicted'}};}}
        }}
        return {{ok: status === 200, status, json: async () => structuredClone(data)}};
      }};
      function clearClusteringResult() {{}}
      function renderClusteringPoints() {{}}
      function setMlResultStale() {{}}
      function highlightCluster() {{}}
      function hoverCluster() {{}}
      function setClusteringLayers() {{}}
      function focusClusteringPoint() {{}}
      {''.join(modules)}
      (async () => {{
        const workspace = await initClustering();
        const pause = () => new Promise(resolve => setTimeout(resolve, 280));
        const input = document.getElementById('cluster-origin');
        const choose = async id => {{
          input.value = '';
          input.dispatchEvent(new Event('input', {{bubbles: true}}));
          await pause();
          document.querySelector(`[data-origin-index="${{origins.findIndex(o => o.fias_id === id)}}"]`).click();
          await pause();
        }};
        {actions}
      }})().catch(error => {{document.body.dataset.result = JSON.stringify({{error: String(error)}});}});
    """


def test_saved_table_download_ignores_form_and_preserves_selection_and_sort():
    actual = _run_browser_script(_product_workspace_script("""
      await choose('a');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles:true})); await pause();
      const transport = globalThis.fetch;
      const blob = new Blob([Uint8Array.from([80,75,3,4,1,2,3,4,80,75,5,6,...Array(18).fill(0)])]);
      let downloads = 0, revoked = 0, exportPayload;
      URL.createObjectURL = value => {if(value.size === blob.size) downloads++; return 'blob:synthetic';};
      URL.revokeObjectURL = () => revoked++;
      HTMLAnchorElement.prototype.click = function() {this.dataset.clicked='true';};
      globalThis.fetch = async (url, init) => {
        if(String(url).endsWith('/export')) {
          exportPayload = JSON.parse(init.body);
          return new Response(blob, {headers:{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition':'attachment; filename="saved.xlsx"'}});
        }
        const response = await transport(url,init);
        const data = await response.json();
        if(String(url).endsWith('/run')) data.cluster_table.rows = [{cluster_id:0,trip_count:40}];
        return {...response,json:async()=>data};
      };
      document.getElementById('btn-run-clustering').click(); await pause();
      const s = workspace.getState(), saved = s.result.data;
      s.ui.selectedCluster = 0; s.ui.selectedPoint = 'x'; s.ui.tableSort = {key:'price.min',direction:'asc'};
      s.ui.tableOpen = false;
      const mode = document.querySelector('input[value="bear_zones"]');
      mode.checked=true; mode.dispatchEvent(new Event('change',{bubbles:true}));
      const button = document.getElementById('btn-export-clustering');
      button.focus(); button.click(); button.click(); await pause();
      await new Promise(resolve=>setTimeout(resolve,1100));
      document.body.dataset.result=JSON.stringify({exportPayload,downloads,revoked,
        sameResult:s.result.data===saved,point:s.ui.selectedPoint,cluster:s.ui.selectedCluster,
        sort:s.ui.tableSort,open:s.ui.tableOpen,focus:document.activeElement.id,
        status:document.getElementById('export-status').textContent,
        runs:requests.filter(r=>r.path==='run').length});
    """))
    assert 'error' not in actual, actual
    assert actual['exportPayload']['mode'] == 'geography'
    assert actual['exportPayload']['origin_fiases'] == ['a']
    assert actual['exportPayload']['selection_intent'] == {'origin_fiases': ['a']}
    assert actual['exportPayload']['table_sort'] == {'key': 'price.min', 'direction': 'asc'}
    assert actual['sameResult'] and actual['point'] == 'x' and actual['cluster'] == 0
    assert actual['sort'] == {'key': 'price.min', 'direction': 'asc'} and not actual['open']
    assert actual['downloads'] == actual['revoked'] == actual['runs'] == 1
    assert actual['focus'] == 'btn-export-clustering'
    assert 'передан' in actual['status']


@pytest.mark.parametrize('action', ['cancel', 'reset', 'hide', 'pagehide', 'run', 'comparison', 'replacement'])
def test_cancelled_export_late_response_cannot_download(action):
    actual = _run_browser_script(_product_workspace_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      const transport=globalThis.fetch;
      let release, signal, downloads=0;
      URL.createObjectURL=()=>{{downloads++;return 'blob:synthetic';}};
      globalThis.fetch=async(url,init)=>{{
        if(String(url).endsWith('/export')) {{
          signal=init.signal;await new Promise(resolve=>release=resolve);
          return new Response(Uint8Array.from([80,75,3,4,80,75,5,6,...Array(18).fill(0)]),
            {{headers:{{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
              'Content-Disposition':'attachment; filename="saved.xlsx"'}}}});
        }}
        const response=await transport(url,init), data=await response.json();
        if(String(url).endsWith('/run')) data.cluster_table.rows=[{{cluster_id:0,trip_count:40}}];
        return {{...response,json:async()=>data}};
      }};
      document.getElementById('btn-run-clustering').click();await pause();
      const saved=workspace.getState().result.data;
      document.getElementById('btn-export-clustering').click();await pause();
      const loading=document.getElementById('export-status').textContent;
      const action={json.dumps(action)};
      if(action==='cancel') document.getElementById('btn-cancel-export').click();
      if(action==='reset') document.getElementById('btn-reset-clustering').click();
      if(action==='hide') workspace.hide();
      if(action==='pagehide') window.dispatchEvent(new Event('pagehide'));
      if(action==='run') document.getElementById('btn-run-clustering').click();
      if(action==='comparison') document.getElementById('compare-modes').click();
      if(action==='replacement') {{workspace.getState().result.data={{...saved}};workspace.show();}}
      await pause();release();await pause();
      document.body.dataset.result=JSON.stringify({{downloads,aborted:signal.aborted,loading,
        busy:document.getElementById('export-controls').getAttribute('aria-busy'),
        success:document.getElementById('export-status').textContent.includes('передан')}});
    """))
    assert 'error' not in actual, actual
    assert actual['downloads'] == 0 and actual['aborted'] and not actual['success']
    assert actual['busy'] == 'false' and 'Подготавливаем' in actual['loading']


@pytest.mark.parametrize('code', ['EXPORT_FAILED', 'STALE_DATA_SNAPSHOT', 'RESULT_UNAVAILABLE'])
def test_export_error_retry_preserves_saved_result_and_rejects_bad_cache(code):
    actual = _run_browser_script(_product_workspace_script(f"""
      await choose('a');
      const region=document.getElementById('cluster-region');
      region.value='R';region.dispatchEvent(new Event('change',{{bubbles:true}}));await pause();
      const transport=globalThis.fetch;
      let exports=0;
      globalThis.fetch=async(url,init)=>{{
        if(String(url).endsWith('/export')) {{exports++;return new Response(JSON.stringify({{code:{json.dumps(code)},error:'Safe failure'}}),
          {{status:409,headers:{{'X-Request-ID':'req-safe'}}}});}}
        const response=await transport(url,init),data=await response.json();
        if(String(url).endsWith('/run')) data.cluster_table.rows=[{{cluster_id:0,trip_count:40}}];
        return {{...response,json:async()=>data}};
      }};
      document.getElementById('btn-run-clustering').click();await pause();
      const s=workspace.getState(),saved=s.result.data;
      document.getElementById('btn-export-clustering').focus();
      document.getElementById('btn-export-clustering').click();await pause();
      const status=document.getElementById('export-status').textContent;
      const disabled=document.getElementById('btn-export-clustering').getAttribute('aria-disabled');
      document.getElementById('btn-export-clustering').click();await pause();
      document.body.dataset.result=JSON.stringify({{exports,disabled,status,
        preserved:s.result.data===saved,rejected:s.rejectedSnapshots.has(saved.data_snapshot),
        unavailable:s.unavailableResults.has(saved),runs:requests.filter(r=>r.path==='run').length,
        focus:document.activeElement.id}});
    """))
    assert 'error' not in actual, actual
    assert actual['preserved'] and actual['runs'] == 1
    assert code in actual['status'] and 'req-safe' in actual['status']
    assert actual['focus'] == 'btn-export-clustering'
    assert actual['exports'] == (2 if code == 'EXPORT_FAILED' else 1)
    assert actual['disabled'] == ('false' if code == 'EXPORT_FAILED' else 'true')
    assert actual['rejected'] == (code == 'STALE_DATA_SNAPSHOT')
    assert actual['unavailable'] == (code == 'RESULT_UNAVAILABLE')



@pytest.mark.parametrize('operation', ['run', 'compare'])
@pytest.mark.parametrize('change', ['unchanged', 'source', 'restart', 'network', 'race'])
def test_calculation_validates_frontend_cache_before_acceptance(operation, change):
    actual = _run_browser_script(_product_workspace_script(f"""
      await choose('a');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {{bubbles: true}})); await pause();
      const perform = () => document.getElementById({json.dumps('btn-run-clustering' if operation == 'run' else 'compare-modes')}).click();
      perform(); await pause();
      const saved = workspace.getState().result.data;
      window.dispatchEvent(new CustomEvent('clustering-point-select', {{detail: {{pointId: 'x'}}}})); await pause();
      document.querySelector('.pulse-details summary').click(); await pause();
      if ({json.dumps(change)} === 'source') revision = 's2';
      if ({json.dumps(change)} === 'restart') available = false;
      if ({json.dumps(change)} === 'network') failRevision = true;
      if ({json.dumps(change)} === 'race') {{failRevision = true; revisionErrorCode = 'STALE_DATA_SNAPSHOT'; revision = 's2';}}
      if ({json.dumps(change)} === 'source' || {json.dumps(change)} === 'restart') failRun = true;
      perform(); await pause();
      const s = workspace.getState();
      const snapshot = s.result.data.data_snapshot;
      const kept = s.result.data === saved;
      const stale = isResultStale(s);
      const detailsSafe = [...s.ui.pointRows.values(), ...s.ui.pointOrigins.values()]
        .every(d => !['success', 'loading'].includes(d.status));
      const counts = () => requests.filter(r => r.path === {json.dumps(operation)}).length;
      const failedCount = counts();
      const checks = requests.filter(r => r.path === 'revision').length;
      const errorVisible = {json.dumps(operation)} === 'run'
        ? !document.getElementById('analysis-form-error').classList.contains('hidden')
        : s.comparison.status === 'error';
      failRun = false; failRevision = false; available = true;
      if ({json.dumps(change)} !== 'unchanged') {{perform(); await pause();}}
      document.body.dataset.result = JSON.stringify({{checks, failedCount, kept, snapshot, stale,
        detailsSafe, errorVisible, finalCount: counts(), finalSnapshot: s.result.data.data_snapshot}});
    """))
    assert 'error' not in actual, actual
    assert actual['checks'] == 1
    assert actual['kept'] and actual['snapshot'] == 's1'
    assert actual['failedCount'] == (2 if change in ('source', 'restart') else 1)
    assert actual['stale'] == (change in ('source', 'restart', 'race'))
    assert actual['detailsSafe'] == (change in ('source', 'restart', 'race'))
    assert actual['errorVisible'] == (change != 'unchanged')
    assert actual['finalCount'] == (1 if change in ('unchanged', 'network') else 2 if change == 'race' else 3)
    assert actual['finalSnapshot'] == ('s2' if change in ('source', 'race') else 's1')


@pytest.mark.parametrize('replacement', ['reset', 'repeat'])
def test_cancelled_revision_cannot_publish_or_invalidate_a_new_workspace(replacement):
    actual = _run_browser_script(_product_workspace_script(f"""
      await choose('a');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {{bubbles: true}})); await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      const transport = globalThis.fetch;
      let release, signal;
      globalThis.fetch = async (url, init) => {{
        if (String(url).endsWith('/revision') && !release) {{
          signal = init.signal;
          return new Promise(resolve => {{release = () => resolve({{ok: true,
            json: async () => ({{ok: true, data_snapshot: 'obsolete', available: [false]}})}});}});
        }}
        return transport(url, init);
      }};
      document.getElementById('btn-run-clustering').click(); await pause();
      if ({json.dumps(replacement)} === 'reset') document.getElementById('btn-reset-clustering').click();
      else {{
        revision = 's2';
        document.getElementById('clustering-controls').dispatchEvent(new Event('submit', {{bubbles: true, cancelable: true}}));
        await pause();
      }}
      release(); await pause();
      const s = workspace.getState();
      document.body.dataset.result = JSON.stringify({{aborted: signal.aborted,
        snapshot: s.result.data?.data_snapshot ?? null,
        obsoleteRejected: s.rejectedSnapshots.has('obsolete'), enabled: !document.getElementById('btn-run-clustering').disabled,
        error: s.result.error}});
    """))
    assert actual == {'aborted': True, 'snapshot': None if replacement == 'reset' else 's2',
                      'obsoleteRejected': False, 'enabled': True, 'error': None}


@pytest.mark.parametrize('operation', ['run', 'compare'])
def test_source_change_after_revision_during_calculation_rejects_frozen_details(operation):
    actual = _run_browser_script(_product_workspace_script(f"""
      await choose('a');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {{bubbles: true}})); await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      const saved = workspace.getState().result.data;
      window.dispatchEvent(new CustomEvent('clustering-point-select', {{detail: {{pointId: 'x'}}}})); await pause();
      document.querySelector('.pulse-details summary').click(); await pause();
      const transport = globalThis.fetch;
      globalThis.fetch = async (url, init) => String(url).endsWith('/' + {json.dumps(operation)})
        ? {{ok: false, status: 409, json: async () => ({{ok: false, code: 'STALE_DATA_SNAPSHOT', error: 'Source changed during calculation'}})}}
        : transport(url, init);
      if ({json.dumps(operation)} === 'run') document.querySelector('#cluster-periods input[value="retro"]').click();
      document.getElementById({json.dumps('btn-run-clustering' if operation == 'run' else 'compare-modes')}).click(); await pause();
      const s = workspace.getState();
      document.body.dataset.result = JSON.stringify({{kept: s.result.data === saved,
        rejected: s.rejectedSnapshots.has('s1'),
        cachesEmpty: !s.result.cache.size && !s.comparison.cache.size,
        summariesAndRowsBlocked: [...s.ui.pointOrigins.values(), ...s.ui.pointRows.values()].every(d => d.status === 'stale'),
        revisionSucceeded: requests.some(r => r.path === 'revision'), stale: isResultStale(s)}});
    """))
    assert actual == {'kept': True, 'rejected': True, 'cachesEmpty': True,
                      'summariesAndRowsBlocked': True, 'revisionSucceeded': True, 'stale': True}


def test_all_control_requires_region_and_uses_explicit_all_options_run_and_frozen_detail():
    actual = _run_browser_script(_product_workspace_script("""
      const all = document.getElementById('all-origins');
      if (!all) throw Error('Explicit All control missing');
      all.click(); await pause();
      document.getElementById('clustering-controls').dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
      const regionRequired = document.getElementById('analysis-form-error').textContent.includes('регион');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles: true})); await pause();
      const preview = document.getElementById('filter-route').textContent;
      document.getElementById('clustering-controls').dispatchEvent(new Event('submit', {bubbles: true, cancelable: true})); await pause();
      const saved = document.getElementById('result-context').textContent;
      const unchanged = document.getElementById('analysis-stale').classList.contains('hidden');
      document.querySelector('#cluster-periods input[value="retro"]').click();
      window.dispatchEvent(new CustomEvent('clustering-point-select', {detail: {pointId: 'x'}}));
      const details = document.querySelector('.pulse-details'); details.open = true; details.dispatchEvent(new Event('toggle')); await pause();
      const run = requests.find(r => r.path === 'run')?.payload;
      const rows = requests.find(r => r.path === 'point-rows')?.payload;
      all.click(); await pause();
      document.body.dataset.result = JSON.stringify({regionRequired, selector: run?.all_origins,
        mixed: run ? 'origin_fiases' in run : true,
        optionsAll: requests.some(r => r.path.includes('all_origins=true') && r.path.includes('destination_region=R')),
        previewAll: preview.includes('Все отправления') && preview.includes('R'), savedAll: saved.includes('Все отправления'),
        unchanged, frozen: rows?.origin_fiases, rowsAll: !!rows?.all_origins, savedUnchanged: saved === document.getElementById('result-context').textContent,
        manualEnabled: !input.disabled, manualEmpty: document.querySelectorAll('[data-remove-origin]').length === 0});
    """))
    assert actual == {"regionRequired": True, "selector": True, "mixed": False, "optionsAll": True,
                      "previewAll": True, "savedAll": True, "unchanged": True, "frozen": ["a", "b"],
                      "rowsAll": False, "savedUnchanged": True, "manualEnabled": True, "manualEmpty": True}

def test_cached_all_comparison_keeps_intent_after_manual_form_edit():
    actual = _run_browser_script(_product_workspace_script("""
      document.getElementById('all-origins').click(); await pause();
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles: true})); await pause();
      document.getElementById('compare-modes').click(); await pause();
      const allRequest = requests.find(r => r.path === 'compare')?.payload;
      document.getElementById('close-comparison').click();
      document.getElementById('all-origins').click(); await pause();
      await choose('a');
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles: true})); await pause();
      document.querySelector('[data-comparison-mode="geo_volume"]').click(); await pause();
      const saved = workspace.getState().result.requestSnapshot;
      const oldAll = document.getElementById('result-context').textContent.includes('Все отправления');
      const editedStale = !document.getElementById('analysis-stale').classList.contains('hidden');
      document.getElementById('all-origins').click(); await pause();
      document.getElementById('compare-modes').click(); await pause();
      document.body.dataset.result = JSON.stringify({all: allRequest?.all_origins,
        savedAll: saved.all_origins, mixed: 'origin_fiases' in saved,
        oldAll, editedStale, comparisons: requests.filter(r => r.path === 'compare').length,
        current: !workspace.getState().result.requestSnapshot.origin_fiases,
        unchanged: document.getElementById('analysis-stale').classList.contains('hidden')});
    """))
    assert actual == {"all": True, "savedAll": True, "mixed": False, "oldAll": True,
                      "editedStale": True, "comparisons": 1, "current": True, "unchanged": True}


def test_all_late_options_after_region_change_reset_or_manual_switch_are_ignored():
    actual = _run_browser_script(_product_workspace_script("""
      options.destination_regions = ['R', 'S'];
      await choose('a');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles: true})); await pause();
      document.getElementById('all-origins').click(); await pause();
      holdOptions = true;
      region.value = 'S'; region.dispatchEvent(new Event('change', {bubbles: true})); await pause();
      document.getElementById('all-origins').click(); await pause();
      holdOptions = false;
      heldOptions.splice(0).forEach(resolve => resolve()); await pause();
      const manual = !input.disabled && document.querySelectorAll('[data-remove-origin]').length === 1;
      const currentRegion = region.value;
      document.getElementById('all-origins').click(); await pause();
      holdOptions = true;
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles: true})); await pause();
      document.getElementById('btn-reset-clustering').click();
      holdOptions = false;
      heldOptions.splice(0).forEach(resolve => resolve()); await pause();
      document.body.dataset.result = JSON.stringify({manual, currentRegion,
        all: document.getElementById('all-origins').checked, region: region.value,
        runEnabled: !document.getElementById('btn-run-clustering').disabled,
        statusHidden: document.getElementById('options-status').classList.contains('hidden')});
    """))
    assert actual == {"manual": True, "currentRegion": "S", "all": False, "region": "",
                      "runEnabled": True, "statusHidden": True}


def test_origin_tokens_survive_search_and_submit_the_union_with_keyboard_removal():
    actual = _run_browser_script(_product_workspace_script("""
      await choose('b');
      const popupClosed = document.getElementById('cluster-origin-options').classList.contains('hidden');
      document.getElementById('cluster-region').value = 'R';
      document.getElementById('cluster-region').dispatchEvent(new Event('change', {bubbles: true}));
      await pause();
      await choose('a');
      input.value = 'missing';
      input.dispatchEvent(new Event('input', {bubbles: true}));
      await pause();
      const tokens = [...document.querySelectorAll('[data-remove-origin]')];
      const selected = tokens.map(button => button.dataset.removeOrigin);
      const route = document.getElementById('filter-route').textContent;
      document.getElementById('btn-run-clustering').click();
      await pause();
      const submitted = requests.find(request => request.path === 'run')?.payload;
      const remove = tokens.find(button => button.dataset.removeOrigin === 'b');
      remove?.focus();
      remove?.dispatchEvent(new KeyboardEvent('keydown', {key: 'Delete', bubbles: true}));
      await pause();
      document.body.dataset.result = JSON.stringify({selected, route, popupClosed,
        origins: submitted?.origin_fiases, region: submitted?.destination_region,
        optionsUnion: requests.some(request => request.path.includes('origin_fiases=a&origin_fiases=b')),
        remaining: [...document.querySelectorAll('[data-remove-origin]')].map(button => button.dataset.removeOrigin),
        frozen: document.getElementById('result-context').textContent.includes('Alpha')
          && document.getElementById('result-context').textContent.includes('Beta'),
        stale: !document.getElementById('analysis-stale').classList.contains('hidden'),
      });
    """))
    assert actual == {
        "selected": ["b", "a"], "route": "Beta, Alpha → R", "popupClosed": True,
        "origins": ["a", "b"], "region": "R", "optionsUnion": True,
        "remaining": ["a"], "frozen": True, "stale": True,
    }


def test_union_point_rows_use_exact_saved_request_after_form_edits():
    actual = _run_browser_script(_product_workspace_script("""
      await choose('b'); await choose('a');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles: true}));
      await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      const saved = requests.find(request => request.path === 'run').payload;
      document.querySelector('#cluster-periods input[value="retro"]').click();
      window.dispatchEvent(new CustomEvent('clustering-point-select', {detail: {pointId: 'x'}}));
      document.querySelector('.pulse-details summary').click();
      await pause();
      const payload = requests.find(request => request.path === 'point-rows')?.payload;
      document.body.dataset.result = JSON.stringify({origins: payload?.origin_fiases,
        periods: payload?.period_types, mode: payload?.mode, parameters: payload?.parameters,
        snapshot: payload?.data_snapshot, destination: payload?.destination_fias,
        scalar: payload ? 'origin_fias' in payload : true,
        frozen: saved.period_types, stale: !document.getElementById('analysis-stale').classList.contains('hidden')});
    """))
    assert actual == {
        "origins": ["a", "b"], "periods": ["current"], "mode": "geography",
        "parameters": {"k_mode": "auto", "n_clusters": "auto"}, "snapshot": "s1",
        "destination": "x", "scalar": False, "frozen": ["current"], "stale": True,
    }


def test_no_data_and_catalog_errors_keep_selected_origins_and_saved_result_visible():
    actual = _run_browser_script(_product_workspace_script("""
      document.getElementById('btn-run-clustering').click();
      const empty = document.getElementById('analysis-form-error').textContent;
      await choose('b'); await choose('a');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles: true})); await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      const context = document.getElementById('result-context').textContent;
      const zeroMatch = context.includes('Без строк по выбранным фильтрам: Alpha');
      document.querySelector('#cluster-periods input[value="retro"]').click();
      failRun = true;
      document.getElementById('btn-run-clustering').click(); await pause();
      const noData = document.getElementById('analysis-form-error').textContent;
      const visible = !document.getElementById('inspector-result').classList.contains('hidden');
      failSearch = true;
      input.value = 'offline'; input.dispatchEvent(new Event('input', {bubbles: true})); await pause();
      document.body.dataset.result = JSON.stringify({empty, zeroMatch, noData, visible,
        contextPreserved: document.getElementById('result-context').textContent === context,
        catalog: document.getElementById('cluster-origin-meta').textContent.includes('Catalog offline'),
        selected: document.querySelectorAll('[data-remove-origin]').length,
        tableVisible: !document.getElementById('cluster-table-panel').classList.contains('hidden')});
    """))
    assert actual == {
        "empty": "Выберите хотя бы одно отправление из списка.", "zeroMatch": True,
        "noData": "NO_DATA: No data matches the selected filters.", "visible": True,
        "contextPreserved": True, "catalog": True, "selected": 2, "tableVisible": True,
    }


def test_evicted_union_result_requires_fresh_calculation_without_rejecting_valid_generation():
    actual = _run_browser_script(_product_workspace_script("""
      await choose('b'); await choose('a');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles: true})); await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      failRows = true;
      window.dispatchEvent(new CustomEvent('clustering-point-select', {detail: {pointId: 'x'}}));
      document.querySelector('.pulse-details summary').click(); await pause();
      const recovery = document.querySelector('.pulse-state')?.textContent.includes('Пересчитайте');
      const retry = Boolean(document.querySelector('[data-pulse-retry]'));
      failRows = false;
      document.getElementById('btn-run-clustering').click(); await pause();
      window.dispatchEvent(new CustomEvent('clustering-point-select', {detail: {pointId: 'x'}}));
      document.querySelector('.pulse-details summary').click(); await pause();
      document.body.dataset.result = JSON.stringify({recovery, retry,
        runs: requests.filter(request => request.path === 'run').length,
        rows: requests.filter(request => request.path === 'point-rows').length,
        success: document.querySelector('.pulse-state')?.textContent.includes('нет строк'),
        stale: !document.getElementById('analysis-stale').classList.contains('hidden')});
    """))
    assert actual == {"recovery": True, "retry": False, "runs": 2, "rows": 2, "success": True, "stale": False}


def test_reset_during_union_options_loading_ignores_late_response_and_restores_controls():
    actual = _run_browser_script(_product_workspace_script("""
      await choose('b');
      holdOptions = true;
      input.value = ''; input.dispatchEvent(new Event('input', {bubbles: true})); await pause();
      document.querySelector('[data-origin-index="1"]').click(); await pause();
      const loading = document.getElementById('clustering-controls').classList.contains('options-loading');
      document.getElementById('btn-reset-clustering').focus();
      document.getElementById('btn-reset-clustering').click();
      heldOptions.forEach(resolve => resolve()); await pause();
      document.body.dataset.result = JSON.stringify({loading,
        busy: document.getElementById('clustering-controls').classList.contains('options-loading'),
        compareDisabled: document.getElementById('compare-modes').disabled,
        statusHidden: document.getElementById('options-status').classList.contains('hidden'),
        origins: document.querySelectorAll('[data-remove-origin]').length,
        region: document.getElementById('cluster-region').value});
    """))
    assert actual == {"loading": True, "busy": False, "compareDisabled": False,
                      "statusHidden": True, "origins": 0, "region": ""}


def test_removing_last_origin_serving_region_refreshes_available_destination_regions():
    actual = _run_browser_script(_product_workspace_script("""
      originRegions = {a: ['R'], b: ['S']};
      await choose('a');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles: true})); await pause();
      await choose('b');
      document.querySelector('[data-remove-origin="a"]').click(); await pause();
      document.body.dataset.result = JSON.stringify({region: region.value,
        available: [...region.options].map(option => option.value),
        selected: [...document.querySelectorAll('[data-remove-origin]')].map(button => button.dataset.removeOrigin),
        error: !document.getElementById('analysis-form-error').classList.contains('hidden'),
        enabled: !region.disabled});
    """))
    assert actual == {"region": "", "available": ["", "S"], "selected": ["b"], "error": False, "enabled": True}


def test_late_origin_search_cannot_reopen_popup_after_selection_or_escape():
    actual = _run_browser_script(_product_workspace_script("""
      await choose('b');
      input.focus(); holdSearch = true;
      input.value = 'Alpha'; input.dispatchEvent(new Event('input', {bubbles: true})); await pause();
      document.querySelector('[data-origin-index="1"]').click(); await pause();
      const afterChoice = document.getElementById('cluster-origin-options').classList.contains('hidden');
      heldSearch.splice(0).forEach(resolve => resolve()); await pause();
      const afterLateChoice = document.getElementById('cluster-origin-options').classList.contains('hidden');
      input.value = 'Beta'; input.dispatchEvent(new Event('input', {bubbles: true})); await pause();
      input.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
      heldSearch.splice(0).forEach(resolve => resolve()); await pause();
      document.body.dataset.result = JSON.stringify({afterChoice, afterLateChoice,
        afterEscape: document.getElementById('cluster-origin-options').classList.contains('hidden'),
        selected: document.querySelectorAll('[data-remove-origin]').length});
    """))
    assert actual == {"afterChoice": True, "afterLateChoice": True, "afterEscape": True, "selected": 2}


@pytest.fixture(scope="module")
def point_detail_presentations():
    formatters = _read("frontend/js/clustering/formatters.js").replace("export ", "")
    inspector = re.sub(
        r"^import .*?;\n", "", _read("frontend/js/clustering/inspector.js"), flags=re.MULTILINE,
    ).replace("export ", "")
    shell = "".join(
        f'<div id="{item}"></div>' for item in (
            "inspector-empty", "inspector-result", "result-status", "result-title",
            "result-subtitle", "result-total-trips", "result-outliers", "result-warnings",
            "result-context", "result-quality", "result-metrics", "point-details",
            "cluster-list", "cluster-details",
        )
    )
    return _run_browser_script(f"""
      {formatters}
      {inspector}
      document.body.innerHTML = {json.dumps(shell)};
      const point = {{id: 'a', fias_id: 'a', name: 'A', lat: 1, lon: 1,
        trip_count: 5, status: 'assigned', weighted_route_length: 100,
        period_types: ['current'], weighted_price: null, weighted_rub_per_km: null,
        regional_weighted_rub_per_km: null, relative_rate_delta: null}};
      const saved = (mode, periods) => ({{status: 'success',
        analysis: {{mode, parameters: {{k_mode: 'manual', n_clusters: 2}},
          filters: {{period_types: periods}}}},
        data_quality: {{}}, points: [point], clusters: [], cluster_table: {{supported: true}}}});
      const geography = saved('geography', ['current', 'forecast']);
      const cost = saved('geo_cost', ['retro']);
      const volume = saved('geo_volume', ['current']);
      const state = {{form: {{periodTypes: ['current', 'forecast']}},
        result: {{data: geography}}, ui: {{selectedPoint: 'a', selectedCluster: null}}}};
      const capture = () => {{
        renderInspector(state);
        return Object.fromEntries(Array.from(document.querySelectorAll('.point-facts > div'))
          .map(row => [row.querySelector('dt').textContent, row.querySelector('dd').textContent]));
      }};
      const selected = capture();
      state.form.periodTypes = ['retro'];
      const edited = capture();
      const switched = [];
      for (const result of [cost, volume, geography]) {{
        state.result.data = result;
        switched.push(capture());
      }}
      const missing = {{}};
      for (const result of [geography, cost, volume]) {{
        state.result.data = result;
        missing[result.analysis.mode] = capture();
      }}
      Object.assign(point, {{weighted_price: 1234, weighted_rub_per_km: 12.5,
        regional_weighted_rub_per_km: 12.5, relative_rate_delta: 0}});
      const valid = capture();
      const bear = {{}};
      for (const mode of ['bear_zones', 'bear_volume_zones']) {{
        state.result.data = saved(mode, ['forecast']);
        state.result.data.cluster_table = {{supported: false}};
        const populated = capture();
        Object.assign(point, {{weighted_price: null, weighted_rub_per_km: null,
          regional_weighted_rub_per_km: null, relative_rate_delta: null}});
        bear[mode] = {{populated, missing: capture(), pulse: !!document.querySelector('.pulse-details')}};
        Object.assign(point, {{weighted_price: 1234, weighted_rub_per_km: 12.5,
          regional_weighted_rub_per_km: 12.5, relative_rate_delta: 0}});
      }}
      document.body.dataset.result = JSON.stringify({{selected, edited, switched, missing, valid, bear}});
    """)


def test_point_detail_shows_selected_periods_instead_of_observed_periods(point_detail_presentations):
    assert point_detail_presentations["selected"]["Периоды"] == "Текущий, Прогноз Pulse"


def test_point_detail_keeps_result_periods_after_form_edit(point_detail_presentations):
    assert point_detail_presentations["edited"]["Периоды"] == "Текущий, Прогноз Pulse"


def test_point_detail_switches_saved_result_period_context(point_detail_presentations):
    assert [row["Периоды"] for row in point_detail_presentations["switched"]] == [
        "Архив", "Текущий", "Текущий, Прогноз Pulse",
    ]


@pytest.mark.parametrize("mode", ["geography", "geo_cost", "geo_volume"])
def test_point_detail_shows_missing_economic_metrics(point_detail_presentations, mode):
    facts = point_detail_presentations["missing"][mode]
    for label in ("Средневзвешенная цена", "Средневзвешенный ₽/км", "Региональный ₽/км", "Отклонение"):
        assert facts.get(label) == "—"


def test_point_detail_preserves_valid_economics_and_zero_deviation(point_detail_presentations):
    facts = point_detail_presentations["valid"]
    assert facts["Средневзвешенная цена"] == "1\u00a0234 ₽"
    assert facts["Средневзвешенный ₽/км"] == "12,5 ₽/км"
    assert facts["Региональный ₽/км"] == "12,5 ₽/км"
    assert facts["Отклонение"] == "0%"
    assert facts["Маршрут"] == "100 км"
    assert facts["Машины"] == "5"


@pytest.mark.parametrize("mode", ["bear_zones", "bear_volume_zones"])
def test_point_detail_preserves_bear_presentation(point_detail_presentations, mode):
    bear = point_detail_presentations["bear"][mode]
    assert not bear["pulse"]
    for facts in (bear["populated"], bear["missing"]):
        assert facts["Перевозки"] == "5"
        assert not {"Машины", "Маршрут", "Периоды"}.intersection(facts)
    labels = {"Средневзвешенная цена", "Средневзвешенный ₽/км", "Региональный ₽/км", "Отклонение"}
    assert not labels.intersection(bear["missing"])
    if mode == "bear_zones":
        assert bear["populated"]["Средневзвешенная цена"] == "1\u00a0234 ₽"
        assert bear["populated"]["Отклонение"] == "0%"
    else:
        assert not labels.intersection(bear["populated"])


def test_product_workspace_contains_all_v1_controls():
    html = _read("frontend/index.html")
    for required in (
        'id="app-nav"',
        'id="data-map-view"',
        'id="clustering-controls"',
        'id="clustering-map"',
        'id="clustering-center"',
        'id="cluster-table-panel"',
        'id="clustering-inspector"',
        'id="comparison-view"',
        'id="cluster-origin"',
        'id="cluster-region"',
        'id="cluster-periods"',
        'id="cluster-prices"',
        'id="cluster-vehicles"',
        'id="cluster-tonnages"',
        'id="mode-cards"',
        'id="cost-weight-options"',
        'id="volume-weight-options"',
        'id="bear-threshold-options"',
        'id="bear-volume-threshold-options"',
        'id="bear-singleton-threshold"',
        'id="bear-volume-singleton-threshold"',
        'id="result-quality"',
        'id="result-warnings"',
        'id="point-details"',
        'id="analysis-preview"',
        'id="result-context"',
        'id="comparison-context"',
        'id="options-status"',
        'id="loading-sub"',
    ):
        assert required in html
    assert "ATI" not in html
    assert "Запустить ML" not in html
    assert 'id="singleton-threshold"' not in html
    assert "Одиночная аномально дорогая точка определяется при +" in html
    assert "Одиночная аномально объёмная точка определяется при +" in html


def test_clustering_is_modular_and_uses_product_api_adapter():
    api = _read("frontend/js/api.js")
    app = _read("frontend/js/app.js")
    controller = _read("frontend/js/clustering/controller.js")

    assert "/api/clustering/options" in api
    assert "/api/clustering/origins" in api
    assert "postClustering('preview'" in api
    assert "postClustering('run'" in api
    assert "postClustering('compare'" in api
    assert "postClustering('point-rows'" in api
    assert "runClusteringComparison" in api
    assert "/api/ml-cluster" not in controller
    assert "initClustering" in app
    assert "buildRequest" in controller


def test_product_map_is_strictly_points_only():
    map_module = _read("frontend/js/map.js")
    renderer = map_module.split("export function renderClusteringPoints", maxsplit=1)[1].split(
        "function mlClusterStyleFunction", maxsplit=1
    )[0]

    assert "ol.geom.Point" in renderer
    assert "GeoJSON" not in renderer
    assert "isMlPolygon" not in renderer
    assert "C${" in renderer
    assert "B${" in renderer
    assert "analysisMode" in renderer
    assert "_productPointPopup" in map_module


def test_state_supports_snapshots_warnings_and_selection():
    state = _read("frontend/js/clustering/state.js")
    controller = _read("frontend/js/clustering/controller.js")

    for required in (
        "datasetSnapshot",
        "buildRequest",
        "semanticallyEqual",
        "isResultStale",
        "isComparisonStale",
        "warningKinds",
        "requestSignature",
        "selectedCluster",
        "selectedPoint",
    ):
        assert required in state
    assert "setMlResultStale" in controller
    assert "runClusteringComparison" in controller
    assert "state.ui.selectedPoint = pointId" in controller
    assert "focusClusteringPoint(pointId)" in controller
    assert "contextualDefault" in controller


def test_stale_copy_matches_the_frozen_product_wording():
    html = _read("frontend/index.html")

    assert "Параметры анализа изменены" in html
    assert "Результат рассчитан для предыдущих настроек." in html


def test_product_controls_include_mode_specific_presets_and_fixed_compare():
    state = _read("frontend/js/clustering/state.js")
    controls = _read("frontend/js/clustering/controls.js")
    controller = _read("frontend/js/clustering/controller.js")
    comparison = _read("frontend/js/clustering/comparison.js")

    assert "costWeight" in state
    assert "geography_weight" in state
    assert "economics_weight" in state
    assert "volumeWeight" in state
    assert "volume_weight" in state
    assert "bearVolumeThreshold" in state
    assert "volume_threshold" in state
    assert "cost-weight" in controls
    assert "volume-weight" in controls
    assert "bear-threshold" in controls
    assert "bear-volume-threshold" in controls
    assert "singletonThreshold: value('bear_zones', 'singleton_threshold')" in state
    assert "response.results" in controller
    assert "onShowMap" in controller
    assert "data-show-on-map" in comparison
    assert "winner" not in comparison.casefold()
    assert "recommended" not in comparison.casefold()


def test_segmented_radio_inputs_are_anchored_to_their_visible_labels():
    css = _read("frontend/css/style.css")

    assert ".segmented label{position:relative" in css
    assert ".segmented input{inset:0;width:100%;height:100%" in css
    assert ".segmented input:focus-visible+span" in css
    assert ".preset-grid span b" in css
    assert "html{overflow:clip;overscroll-behavior:none}" in css
    assert "#app{position:fixed;inset:0;overflow:clip}" in css
    assert ".check-chip{position:relative" in css


def test_preview_loading_and_comparison_keep_product_context_visible():
    html = _read("frontend/index.html")
    controls = _read("frontend/js/clustering/controls.js")
    controller = _read("frontend/js/clustering/controller.js")
    comparison = _read("frontend/js/clustering/comparison.js")

    assert "Источник: Pulse" in html
    assert "Сравниваем пять режимов…" in html
    assert "preview-periods" in controls
    assert "Рассчитываем зоны…" in controller
    assert "contextDisplay" in controller
    assert "Экономическое покрытие" in comparison
    assert "Между кластерами" in comparison
    assert "Geo / Volume" in comparison


def test_clustering_modules_reference_existing_dom_ids():
    html = _read("frontend/index.html")
    modules = "\n".join(
        _read(path)
        for path in (
            "frontend/js/app.js",
            "frontend/js/clustering/controller.js",
            "frontend/js/clustering/controls.js",
            "frontend/js/clustering/inspector.js",
            "frontend/js/clustering/comparison.js",
        )
    )
    html_ids = set(re.findall(r'id="([^"]+)"', html))
    referenced_ids = set(re.findall(r"\$\('([^']+)'\)", modules))
    assert referenced_ids - html_ids == set()


def test_frontend_honors_published_capabilities_when_compatibility_values_drift():
    edge = _edge_path()
    if edge is None:
        pytest.skip("A browser JavaScript runtime is required for the frontend contract")

    compatibility = {
        "modes": ["geography", "geo_cost", "geo_volume", "bear_zones", "bear_volume_zones"],
        "defaults": {"mode": "geography", "k_mode": "auto"},
        "k": {"min": 2, "max": 20, "default": 5, "modes": ["auto", "manual"]},
        "geo_cost_weights": {
            "default": {"geography": 0.7, "economics": 0.3},
            "presets": [{"geography": 0.7, "economics": 0.3}],
        },
        "geo_volume_weights": {
            "default": {"geography": 0.7, "volume": 0.3},
            "presets": [{"geography": 0.7, "volume": 0.3}],
        },
        "bear_thresholds": {
            "zone_default": 0.35,
            "zone_options": [0.35],
            "singleton_default": 0.7,
            "singleton_fixed": True,
        },
        "bear_volume_thresholds": {
            "zone_default": 0.35,
            "zone_options": [0.35],
            "singleton_default": 0.7,
            "singleton_fixed": True,
        },
    }
    order = ["bear_zones", "geography", "geo_cost", "bear_volume_zones", "geo_volume"]
    parameters = {
        "geography": [
            {
                "name": "k_mode",
                "kind": "choice",
                "default": "manual",
                "choices": ["auto", "manual"],
            },
            {
                "name": "n_clusters",
                "kind": "cluster_count",
                "default": "auto",
                "min": 7,
                "max": 11,
                "manual_default": 9,
            },
        ],
        "geo_cost": [
            {
                "name": "economics_weight",
                "kind": "choice",
                "default": 0.41,
                "choices": [0.41, 0.59],
            },
        ],
        "geo_volume": [
            {"name": "volume_weight", "kind": "choice", "default": 0.43, "choices": [0.43, 0.57]},
        ],
        "bear_zones": [
            {"name": "bear_threshold", "kind": "choice", "default": 0.44, "choices": [0.44, 0.55]},
            {
                "name": "singleton_threshold",
                "kind": "choice",
                "default": 0.73,
                "choices": [0.73],
                "fixed": True,
            },
        ],
        "bear_volume_zones": [
            {"name": "volume_threshold", "kind": "choice", "default": 0.46, "choices": [0.46]},
            {
                "name": "singleton_threshold",
                "kind": "choice",
                "default": 0.73,
                "choices": [0.73],
                "fixed": True,
            },
        ],
    }
    compatibility["mode_capabilities"] = [
        {
            "id": mode,
            "parameters": parameters[mode],
            "presets": [{"economics_weight": 0.41}] if mode == "geo_cost" else [],
            "semantic_dimensions": (
                ["geography", "economics"] if mode == "geography" else ["geography"]
            ),
            "result_kind": "zones" if mode == "geography" else "partition",
            "comparison": {"supported": mode != "geo_volume", "parameters": {}},
        }
        for mode in order
    ]
    state_module = _read("frontend/js/clustering/state.js").replace("export ", "")
    controls_module = re.sub(
        r"^import .*?;\n",
        "",
        _read("frontend/js/clustering/controls.js"),
        flags=re.MULTILINE,
    ).replace("export ", "")
    script = f"""
      {state_module}
      const MODE_LABELS = {{}};
      const PERIOD_LABELS = {{}};
      const PRICE_LABELS = {{}};
      const escapeHtml = value => String(value ?? '');
      document.body.innerHTML = {json.dumps("".join(f'<div id="{item}"></div>' for item in ("cluster-periods", "cluster-prices", "cluster-vehicles", "cluster-tonnages", "mode-cards", "cost-weight-options", "volume-weight-options", "bear-threshold-options", "bear-volume-threshold-options", "bear-singleton-threshold", "bear-volume-singleton-threshold")) + '<input id="manual-k">')};
      {controls_module}
      const state = createClusteringState({json.dumps(compatibility)});
      renderOptionControls(state);
      const incompleteOptions = JSON.parse(JSON.stringify({json.dumps(compatibility)}));
      delete incompleteOptions.mode_capabilities;
      let missingCapabilitiesError = null;
      try {{
        createClusteringState(incompleteOptions);
      }} catch (error) {{
        missingCapabilitiesError = error.message;
      }}
      const actual = {{
        modes: state.modeCapabilities.map(item => item.id),
        renderedModes: [...document.querySelectorAll('input[name="analysis-mode"]')].map(item => item.value),
        comparisonModes: state.comparisonModeIds,
        kMode: state.form.kMode,
        kLimits: [modeParameter(state.modeCapabilities, 'geography', 'n_clusters').min,
                  modeParameter(state.modeCapabilities, 'geography', 'n_clusters').max],
        renderedKLimits: [Number(document.getElementById('manual-k').min), Number(document.getElementById('manual-k').max)],
        renderedCostPresets: [...document.querySelectorAll('input[name="cost-weight"]')].map(item => Number(item.value)),
        renderedBearThresholds: [...document.querySelectorAll('input[name="bear-threshold"]')].map(item => Number(item.value)),
        renderedSingleton: Number(document.getElementById('bear-singleton-threshold').textContent),
        costWeight: state.form.costWeight,
        manualK: state.form.k,
        bearThreshold: state.form.bearThreshold,
        singletonThreshold: state.form.singletonThreshold,
        geographyWarnings: warningKinds({{...state.form, mode: 'geography', periodTypes: ['current'], priceTypes: ['spot', 'tender']}}, state.modeCapabilities),
        geographyResultKind: modeResultKind(state.modeCapabilities, 'geography'),
        missingCapabilitiesError,
        request: buildRequest({{...state.form, mode: 'geo_cost'}}, 'geo_cost'),
      }};
      document.body.dataset.result = JSON.stringify(actual);
    """
    actual = _run_browser_script(script)
    assert actual == {
        "modes": order,
        "renderedModes": order,
        "comparisonModes": ["bear_zones", "geography", "geo_cost", "bear_volume_zones"],
        "kMode": "manual",
        "kLimits": [7, 11],
        "renderedKLimits": [7, 11],
        "renderedCostPresets": [0.41],
        "renderedBearThresholds": [0.44, 0.55],
        "renderedSingleton": 73,
        "costWeight": 0.41,
        "manualK": 9,
        "bearThreshold": 0.44,
        "singletonThreshold": 0.73,
        "geographyWarnings": ["mixed_segment"],
        "geographyResultKind": "zones",
        "missingCapabilitiesError": "Product mode capabilities are required",
        "request": {
            "origin_fiases": [],
            "destination_region": "",
            "period_types": ["current"],
            "price_types": ["spot"],
            "vehicle_types": [],
            "tonnage_ids": [],
            "mode": "geo_cost",
            "parameters": {
                "k_mode": "manual",
                "n_clusters": 9,
                "geography_weight": 0.59,
                "economics_weight": 0.41,
            },
        },
    }


def test_cluster_table_renders_and_interacts_through_the_product_ui_seam():
    table = re.sub(
        r"^import .*?;\n",
        "",
        _read("frontend/js/clustering/table.js"),
        flags=re.MULTILINE,
    ).replace("export ", "")
    result = {
        "status": "success",
        "analysis": {"mode": "geography"},
        "cluster_table": {
            "supported": True,
            "period_types": ["current", "forecast"],
            "methodology": {
                "version": "product_cluster_table_v1",
                "distributions": "unweighted_destination_points",
                "weighted_values": "metric_valid_trip_count",
            },
            "rows": [
                {
                    "cluster_id": 2,
                    "point_count": 4,
                    "trip_count": 9,
                    "trip_share": 0.81818,
                    "weighted_route_length": 120.05,
                    "price": {"min": 0, "median": 2166.525, "weighted": 3111.116, "max": 5000},
                    "rub_per_km": {"min": 10, "median": 10.0005, "weighted": 14.0001, "max": 30},
                    "economic_coverage": {
                        "valid_points": 3, "total_points": 4,
                        "valid_trip_count": 5, "total_trip_count": 9,
                    },
                    "coverage": {
                        "price": {"valid_points": 4, "total_points": 4, "valid_trip_count": 8, "total_trip_count": 9},
                        "rub_per_km": {"valid_points": 3, "total_points": 4, "valid_trip_count": 5, "total_trip_count": 9},
                    },
                },
                {
                    "cluster_id": 0,
                    "point_count": 1,
                    "trip_count": 2,
                    "trip_share": 0.18182,
                    "weighted_route_length": 200,
                    "price": {"min": None, "median": None, "weighted": None, "max": None},
                    "rub_per_km": {"min": None, "median": None, "weighted": None, "max": None},
                    "economic_coverage": {
                        "valid_points": 0, "total_points": 1,
                        "valid_trip_count": 0, "total_trip_count": 2,
                    },
                },
            ],
        },
    }
    shell = '<section id="cluster-table-panel" class="hidden"></section>'
    script = f"""
      const MODE_LABELS = {{geography: 'По географии', geo_cost: 'География + стоимость', geo_volume: 'География + объём'}};
      const PERIOD_LABELS = {{retro: 'Архив', current: 'Текущий', forecast: 'Прогноз'}};
      const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, char => ({{'&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'}})[char]);
      {table}
      document.body.innerHTML = {json.dumps(shell)};
      const state = {{
        result: {{status: 'success', data: {json.dumps(result)}}},
        ui: {{tableOpen: true, tableSort: {{key: 'trip_count', direction: 'desc'}}, selectedCluster: null}},
      }};
      const events = [];
      const handlers = {{
        isStale: () => true,
        onToggle: open => events.push(['toggle', open]),
        onSort: (key, direction) => {{ state.ui.tableSort = {{key, direction}}; render(); }},
        onClusterHover: id => events.push(['hover', id]),
        onClusterSelect: id => events.push(['select', id]),
      }};
      const render = () => renderClusterTable(state, handlers);
      render();
      const panel = document.getElementById('cluster-table-panel');
      const initial = {{
        hidden: panel.classList.contains('hidden'),
        stale: panel.classList.contains('stale'),
        headers: panel.querySelectorAll('thead th').length,
        rowIds: [...panel.querySelectorAll('tbody tr')].map(row => Number(row.dataset.clusterId)),
        firstCells: [...panel.querySelector('tbody tr').children].map(cell => cell.textContent.trim()),
        periods: [...panel.querySelectorAll('.cluster-table-period')].map(item => item.textContent.trim()),
        methodology: panel.querySelector('.cluster-table-methodology').textContent.replace(/\\s+/g, ' ').trim(),
        coverageTitle: panel.querySelector('tbody tr td:last-child').title,
        sort: panel.querySelector('[data-sort-key="trip_count"]').closest('th').getAttribute('aria-sort'),
        selectedRows: panel.querySelectorAll('tbody tr.selected').length,
      }};
      panel.querySelector('[data-sort-key="price.min"]').click();
      const sorted = [...panel.querySelectorAll('tbody tr')].map(row => Number(row.dataset.clusterId));
      const row = panel.querySelector('tbody tr');
      row.dispatchEvent(new MouseEvent('mouseenter'));
      row.querySelector('button').focus();
      row.querySelector('button').click();
      panel.querySelector('[data-table-toggle]').click();
      state.result.data.cluster_table = {{supported: false}};
      render();
      document.body.dataset.result = JSON.stringify({{
        initial, sorted, events, unsupportedHidden: panel.classList.contains('hidden'),
      }});
    """

    assert _run_browser_script(script) == {
        "initial": {
            "hidden": False,
            "stale": True,
            "headers": 14,
            "rowIds": [2, 0],
            "firstCells": [
                "Кластер 3", "4", "9", "81,8%", "120,1 км", "0 ₽", "2 167 ₽",
                "3 111 ₽", "5 000 ₽", "10,0 ₽/км", "10,0 ₽/км", "14,0 ₽/км",
                "30,0 ₽/км", "75,0% точек · 55,6% машин",
            ],
            "periods": ["Текущий", "Прогноз Pulse"],
            "methodology": (
                "Методика расчёта Min, медиана и max рассчитаны по точкам назначения без весов. "
                "Средневзвешенные значения учитывают машины только с доступной метрикой. "
                "Пропуски не превращаются в нули и отражены в покрытии. "
                "Периоды: Текущий, Прогноз Pulse. "
                "Режим: По географии — экономика показана описательно и не влияла на разбиение."
            ),
            "coverageTitle": (
                "Покрытие: 3/4 точек; 5/9 машин; цена: 4/4 точек, 8/9 машин; "
                "₽/км: 3/4 точек, 5/9 машин"
            ),
            "sort": "descending",
            "selectedRows": 0,
        },
        "sorted": [2, 0],
        "events": [["hover", 2], ["hover", 2], ["select", 2], ["toggle", False], ["hover", None]],
        "unsupportedHidden": True,
    }


def test_cluster_formula_help_is_visible_on_hover_and_keyboard_focus_without_clipping():
    table = re.sub(
        r"^import .*?;\n", "", _read("frontend/js/clustering/table.js"), flags=re.MULTILINE
    ).replace("export ", "")
    formatters = _read("frontend/js/clustering/formatters.js").replace("export ", "")
    css = _read("frontend/css/style.css")
    script = f"""
      const {{escapeHtml, MODE_LABELS, PERIOD_LABELS}} = (() => {{
        {formatters}
        return {{escapeHtml, MODE_LABELS, PERIOD_LABELS}};
      }})();
      {table}
      document.head.insertAdjacentHTML('beforeend', '<style>' + {json.dumps(css)} + '</style>');
      document.body.innerHTML = '<div class="clustering-center" style="width:700px;height:800px">'
        + '<div style="flex:1"></div><section id="cluster-table-panel" class="cluster-table-panel"></section></div>';
      const state = {{result: {{status: 'success', data: {{
        analysis: {{mode: 'geography'}},
        cluster_table: {{supported: true, period_types: ['current'], rows: [{{cluster_id: 0}}]}},
      }}}}, ui: {{tableOpen: true}}}};
      const render = () => renderClusterTable(state, {{
        onSort: (key, direction) => {{state.ui.tableSort = {{key, direction}}; render();}},
        onToggle: open => {{state.ui.tableOpen = open; render();}},
      }});
      render();
      const panel = document.getElementById('cluster-table-panel');
      let help = panel.querySelector('[data-sort-key="price.weighted"]').closest('th').querySelector('.cluster-table-help');
      help.scrollIntoView();
      function visibleHelp() {{
        const tip = document.getElementById(help.getAttribute('aria-describedby'));
        if (!tip) return null;
        const rect = tip.getBoundingClientRect();
        const style = getComputedStyle(tip);
        const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
        return {{
          text: tip.textContent.trim(), role: tip.getAttribute('role'),
          readable: rect.width > 0 && rect.height > 0 && style.visibility === 'visible'
            && style.display !== 'none' && Number(style.opacity) > 0 && parseFloat(style.fontSize) >= 12,
          inViewport: rect.left >= 0 && rect.right <= innerWidth && rect.top >= 0 && rect.bottom <= innerHeight,
          unclipped: hit === tip || tip.contains(hit),
        }};
      }}
      help.dispatchEvent(new MouseEvent('mouseenter'));
      const hover = visibleHelp();
      help.dispatchEvent(new MouseEvent('mouseleave'));
      const hiddenAfterLeave = !visibleHelp()?.readable;
      help.focus();
      const focus = visibleHelp();
      help.dispatchEvent(new KeyboardEvent('keydown', {{key: 'Escape', bubbles: true}}));
      const hiddenAfterEscape = !visibleHelp()?.readable;
      help.blur();
      const hiddenAfterBlur = !visibleHelp()?.readable;
      const focusPriceHelp = () => {{
        help = panel.querySelector('[data-sort-key="price.weighted"]').closest('th').querySelector('.cluster-table-help');
        help.focus();
        return visibleHelp();
      }};
      panel.querySelector('[data-sort-key="price.weighted"]').click();
      const afterSort = focusPriceHelp();
      panel.querySelector('[data-table-toggle]').click();
      const collapsedHasNoTooltip = !panel.querySelector('.cluster-table-tooltip:popover-open');
      panel.querySelector('[data-table-toggle]').click();
      const afterReopen = focusPriceHelp();
      const supportedModes = ['geography', 'geo_cost', 'geo_volume'].map(mode => {{
        state.result.data = {{...state.result.data, analysis: {{mode}}}};
        render();
        return focusPriceHelp();
      }});
      const allMetrics = [...panel.querySelectorAll('.cluster-table-help')].map(trigger => {{
        help = trigger;
        help.scrollIntoView();
        help.focus();
        const snapshot = visibleHelp();
        return snapshot.readable && snapshot.inViewport && snapshot.unclipped;
      }});
      panel.querySelector('.cluster-table-scroll').dispatchEvent(new Event('scroll'));
      const hiddenAfterScroll = !visibleHelp()?.readable;
      const bearModes = ['bear_zones', 'bear_volume_zones'].map(mode => {{
        state.result.data = {{analysis: {{mode}}, cluster_table: {{supported: false}}}};
        render();
        return panel.classList.contains('hidden') && !panel.querySelector('[role="tooltip"]');
      }});
      document.body.dataset.result = JSON.stringify({{
        hover, focus, hiddenAfterLeave, hiddenAfterBlur, hiddenAfterEscape,
        afterSort, collapsedHasNoTooltip, afterReopen, supportedModes, allMetrics, hiddenAfterScroll, bearModes,
      }});
    """
    expected = {
        "text": "Сумма (цена точки × машины с доступной ценой) / сумма машин с доступной ценой. Пропуски исключены; при отсутствии данных — «—».",
        "role": "tooltip",
        "readable": True,
        "inViewport": True,
        "unclipped": True,
    }
    assert _run_browser_script(script) == {
        "hover": expected, "focus": expected, "hiddenAfterLeave": True, "hiddenAfterBlur": True,
        "hiddenAfterEscape": True, "afterSort": expected, "collapsedHasNoTooltip": True,
        "afterReopen": expected, "supportedModes": [expected] * 3,
        "allMetrics": [True] * 12, "hiddenAfterScroll": True, "bearModes": [True, True],
    }


def test_cluster_table_lifecycle_uses_the_existing_result_state():
    table = re.sub(
        r"^import .*?;\n",
        "",
        _read("frontend/js/clustering/table.js"),
        flags=re.MULTILINE,
    ).replace("export ", "")
    script = f"""
      const MODE_LABELS = {{geography: 'По географии', geo_cost: 'География + стоимость', geo_volume: 'География + объём'}};
      const PERIOD_LABELS = {{current: 'Текущий'}};
      const escapeHtml = value => String(value ?? '');
      {table}
      document.body.innerHTML = '<section id="cluster-table-panel"></section>';
      const panel = document.getElementById('cluster-table-panel');
      const state = {{result: {{status: 'empty', data: null}}, ui: {{tableVisible: true, tableOpen: true}}}};
      const render = () => renderClusterTable(state, {{}});
      render();
      const beforeRunHidden = panel.classList.contains('hidden');
      const result = mode => ({{
        analysis: {{mode}},
        cluster_table: {{supported: true, period_types: ['current'], methodology: {{}}, rows: []}},
      }});
      const supportedModes = ['geography', 'geo_cost', 'geo_volume'].map(mode => {{
        state.result = {{status: 'success', data: result(mode)}};
        render();
        return !panel.classList.contains('hidden');
      }});
      const emptyText = panel.querySelector('.cluster-table-state').textContent.trim();
      state.result.status = 'loading';
      render();
      const loading = {{visible: !panel.classList.contains('hidden'), busy: panel.getAttribute('aria-busy')}};
      state.result = {{status: 'success', data: result('geography')}};
      delete state.result.data.cluster_table.rows;
      render();
      const invalidText = panel.querySelector('.cluster-table-state.error').textContent.trim();
      state.result = {{status: 'error', data: null}};
      render();
      document.body.dataset.result = JSON.stringify({{
        beforeRunHidden, supportedModes, emptyText, loading, invalidText,
        failedRunHidden: panel.classList.contains('hidden'),
      }});
    """

    assert _run_browser_script(script) == {
        "beforeRunHidden": True,
        "supportedModes": [True, True, True],
        "emptyText": "В результате нет кластеров для таблицы.",
        "loading": {"visible": True, "busy": "true"},
        "invalidText": "Некорректные данные таблицы.",
        "failedRunHidden": True,
    }


def test_cluster_table_controller_handlers_keep_map_inspector_and_panel_in_sync():
    controller = re.sub(
        r"^import[\s\S]*?;\n",
        "",
        _read("frontend/js/clustering/controller.js"),
        flags=re.MULTILINE,
    ).replace("export ", "")
    script = f"""
      const calls = {{renders: 0, map: [], hover: [], inspector: [], runs: 0}};
      let tableHandlers;
      function renderClusterTable(currentState, handlers) {{
        calls.renders += 1;
        tableHandlers = handlers;
      }}
      function isResultStale() {{ return false; }}
      function highlightCluster(id, focus) {{ calls.map.push([id, focus]); }}
      function hoverCluster(id) {{ calls.hover.push(id); }}
      function renderInspector(currentState) {{ calls.inspector.push(currentState.ui.selectedCluster); }}
      function runClustering() {{ calls.runs += 1; }}
      {controller}
      state = {{
        ui: {{tableOpen: true, hoveredCluster: null, selectedCluster: null, selectedPoint: null}},
        result: {{data: {{}}}},
      }};
      renderClusterTableState();
      tableHandlers.onToggle(false);
      const collapsed = state.ui.tableOpen;
      tableHandlers.onToggle(true);
      const reopened = state.ui.tableOpen;
      tableHandlers.onClusterHover(3);
      tableHandlers.onClusterSelect(3);
      document.body.dataset.result = JSON.stringify({{
        collapsed, reopened,
        selected: state.ui.selectedCluster,
        hovered: state.ui.hoveredCluster,
        calls,
      }});
    """

    assert _run_browser_script(script) == {
        "collapsed": False,
        "reopened": True,
        "selected": 3,
        "hovered": 3,
        "calls": {
            "renders": 4,
            "map": [[3, True]],
            "hover": [3],
            "inspector": [3],
            "runs": 0,
        },
    }


def test_point_rows_are_lazy_paginated_retryable_and_cancelled_on_selection_change():
    state_module = _read("frontend/js/clustering/state.js").replace("export ", "")
    controller = re.sub(
        r"^import[\s\S]*?;\n",
        "",
        _read("frontend/js/clustering/controller.js"),
        flags=re.MULTILINE,
    ).replace("export ", "")
    script = f"""
      const requests = [];
      let renders = 0;
      function fetchClusteringPointRows(payload, options) {{
        let resolve, reject;
        const promise = new Promise((yes, no) => {{ resolve = yes; reject = no; }});
        requests.push({{payload, signal: options.signal, resolve, reject}});
        return promise;
      }}
      function renderInspector() {{ renders += 1; }}
      function focusClusteringPoint() {{}}
      function highlightCluster() {{}}
      function renderClusterTable() {{}}
      {state_module}
      {controller}
      renderAll = () => {{}};
      const result = {{
        data_snapshot: 'snapshot-1',
        cluster_table: {{supported: true}},
        analysis: {{mode: 'geography', origin: {{fias_id: 'origin-1'}}, destination_region: 'Region A', filters: {{period_types: ['current'], price_types: ['spot'], vehicle_types: [], tonnage_ids: []}}}},
        points: [{{id: 'a', fias_id: 'a'}}, {{id: 'b', fias_id: 'b'}}], clusters: [],
      }};
      state = {{
        result: {{data: result}},
        ui: {{selectedPoint: null, pointRows: new Map()}},
      }};
      selectPoint('a');
      const lazyCount = requests.length;
      const firstPromise = loadPointRows();
      const loading = pointRowsForSelection().status;
      requests[0].resolve({{rows: Array.from({{length: 50}}, (_, index) => ({{source_row_id: String(index)}})), total: 51, has_more: true}});
      await firstPromise;
      const first = [pointRowsForSelection().rows.length, pointRowsForSelection().hasMore];
      const morePromise = loadPointRows();
      requests[1].resolve({{rows: [{{source_row_id: '50'}}], total: 51, has_more: false}});
      await morePromise;
      const finished = [pointRowsForSelection().rows.length, pointRowsForSelection().hasMore];
      result.analysis.filters.price_types = ['tender'];
      selectPoint('a');
      const cacheIsolation = pointRowsForSelection().rows.length;
      const cancelledPromise = loadPointRows({{restart: true}});
      selectPoint('b');
      const cancelled = requests[2].signal.aborted;
      requests[2].resolve({{rows: [{{source_row_id: 'wrong'}}], total: 1, has_more: false}});
      await cancelledPromise;
      const noLeak = pointRowsForSelection().rows.length;
      const failedPromise = loadPointRows();
      requests[3].reject(Object.assign(new Error('offline'), {{code: 'NETWORK'}}));
      await failedPromise;
      const failed = pointRowsForSelection().status;
      const retryPromise = loadPointRows();
      requests[4].resolve({{rows: [], total: 0, has_more: false}});
      await retryPromise;
      const stalePromise = loadPointRows({{restart: true}});
      requests[5].reject(Object.assign(new Error('stale'), {{code: 'STALE_DATA_SNAPSHOT'}}));
      await stalePromise;
      console.log(JSON.stringify({{
        lazyCount, loading,
        first, finished,
        cancelled, noLeak, cacheIsolation, failed,
        retried: requests.length === 6,
        stale: pointRowsForSelection().status,
        offsets: requests.map(item => item.payload.offset),
        renders,
      }}));
    """

    assert _run_node_script(script) == {
        "lazyCount": 0,
        "loading": "loading",
        "first": [50, True],
        "finished": [51, False],
        "cancelled": True,
        "noLeak": 0,
        "cacheIsolation": 0,
        "failed": "error",
        "retried": True,
        "stale": "stale",
        "offsets": [0, 50, 0, 0, 0, 0],
        "renders": 14,
    }


def test_stale_form_keeps_open_pulse_request_on_the_frozen_result():
    controller = re.sub(
        r"^import[\s\S]*?;\n",
        "",
        _read("frontend/js/clustering/controller.js"),
        flags=re.MULTILINE,
    ).replace("export ", "")
    script = f"""
      const document = {{
        getElementById: () => ({{value: '2'}}),
        querySelector: selector => ({{
          value: selector.includes('analysis-mode') ? 'geography' : '0.3',
        }}),
      }};
      const requests = [];
      function fetchClusteringPointRows(payload, options) {{
        let resolve;
        const promise = new Promise(yes => {{ resolve = yes; }});
        requests.push({{signal: options.signal, resolve}});
        return promise;
      }}
      function renderInspector() {{}}
      function focusClusteringPoint() {{}}
      function highlightCluster() {{}}
      function renderClusterTable() {{}}
      function requestSignature(value) {{ return JSON.stringify(value); }}
      function readChecks() {{ return []; }}
      function modeParameter() {{ return null; }}
      {controller}
      const result = {{
        data_snapshot: 'snapshot-1',
        cluster_table: {{supported: true}},
        analysis: {{origin: {{fias_id: 'origin-1'}}, destination_region: 'Region A', filters: {{period_types: ['current'], price_types: ['spot'], vehicle_types: [], tonnage_ids: []}}}},
        points: [{{id: 'a', fias_id: 'a'}}], clusters: [],
      }};
      state = {{
        form: {{periodTypes: ['current'], priceTypes: ['spot'], vehicleTypes: [], tonnageIds: [], mode: 'geography', kMode: 'auto', k: 2, costWeight: 0.3, volumeWeight: 0.3, bearThreshold: 0.35, bearVolumeThreshold: 0.35, singletonThreshold: 0.7}},
        modeCapabilities: [],
        result: {{data: result}},
        ui: {{selectedPoint: 'a', selectedCluster: null, pointRows: new Map()}},
      }};
      const pending = loadPointRows();
      const detail = pointRowsForSelection();
      syncForm({{target: {{name: 'price-type'}}}});
      const preserved = !requests[0].signal.aborted && detail.open && detail.status === 'loading';
      requests[0].resolve({{rows: [{{source_row_id: '1'}}], total: 1, has_more: false}});
      await pending;
      console.log(JSON.stringify({{preserved, status: detail.status, rows: detail.rows.length}}));
    """

    assert _run_node_script(script) == {"preserved": True, "status": "success", "rows": 1}


def test_cached_comparison_keeps_form_mode_and_presets_after_filter_edit():
    from backend.product_modes import default_product_mode_catalog

    options = {
        "mode_capabilities": [mode.as_dict() for mode in default_product_mode_catalog().manifest()],
        "period_types": ["current", "retro"], "price_types": ["spot"],
    }
    modules = []
    for name in ("formatters", "state", "controls", "comparison", "controller"):
        source = re.sub(r"^import[\s\S]*?;\n", "", _read(f"frontend/js/clustering/{name}.js"), flags=re.MULTILINE)
        source = source.replace("export ", "").replace("const $ = id => document.getElementById(id);", "")
        modules.append(source)
    shell = re.sub(r"<script[\s\S]*?</script>", "", _read("frontend/index.html"))
    script = f"""
      const $ = id => document.getElementById(id);
      {''.join(modules)}
      document.body.innerHTML = {json.dumps(shell)};
      const options = {json.dumps(options)};
      const runs = []; let compares = 0;
      const fetchClusteringOptions = async () => options;
      const fetchClusteringOrigins = async () => [{{fias_id: 'origin', name: 'Origin'}}];
      const renderClusteringPoints = () => {{}}, setMlResultStale = () => {{}};
      const renderClusterTable = current => $('cluster-table-panel').classList.toggle('hidden', !current.ui.tableVisible);
      const renderInspector = current => {{
        $('result-title').textContent = current.result.data?.analysis.mode || '';
        $('result-context').textContent = JSON.stringify(current.result.requestSnapshot);
      }};
      const saved = {{results: {{}}}};
      for (const mode of ['geography', 'geo_cost', 'geo_volume', 'bear_zones', 'bear_volume_zones']) {{
        saved.results[mode] = {{status: 'success', data_snapshot: 'saved', points: [], clusters: [],
          analysis: {{mode, origin: {{fias_id: 'origin'}}, parameters: {{k_mode: 'auto', n_clusters: 3, economics_weight: 0.3,
            volume_weight: 0.3, bear_threshold: 0.35, volume_threshold: 0.35}}}},
          cluster_table: {{supported: !mode.startsWith('bear')}}, data_quality: {{}}}};
      }}
      const runClustering = async request => {{runs.push(request); return saved.results[request.mode];}};
      const runClusteringComparison = async () => {{compares++; return saved;}};
      const fetchClusteringRevision = async results => ({{data_snapshot: 'saved', available: results.map(() => true)}});
      (async () => {{
        await initClustering();
        const q = selector => document.querySelector(selector);
        const click = async selector => {{q(selector).click(); for (let i=0; i<10; i++) await Promise.resolve();}};
        const checked = name => q('input[name="' + name + '"]:checked')?.value;
        const observe = () => [checked('analysis-mode'), $('preview-mode').textContent, q('.mode-card.selected input').value];
        await click('[data-origin-index="0"]');
        $('cluster-region').add(new Option('Region A', 'Region A'));
        $('cluster-region').value = 'Region A';
        $('cluster-region').dispatchEvent(new Event('change', {{bubbles: true}}));
        for (let i=0; i<10; i++) await Promise.resolve();
        await click('.mode-bear_volume_zones'); await click('#btn-run-clustering');
        await click('#compare-modes'); await click('[data-show-on-map="geography"]');
        const before = observe(), frozen = $('result-context').textContent;
        await click('#cluster-periods input[value="retro"]');
        const after = observe(), unchanged = frozen === $('result-context').textContent;
        const stale = !$('analysis-stale').classList.contains('hidden');
        await click('#btn-run-clustering'); const submitted = runs.at(-1);
        await click('#cluster-periods input[value="retro"]');
        for (const [mode, name, value] of [
          ['geo_cost', 'cost-weight', '0.4'], ['geo_volume', 'volume-weight', '0.2'],
          ['bear_zones', 'bear-threshold', '0.5'], ['bear_volume_zones', 'bear-volume-threshold', '0.2'],
        ]) {{ await click('.mode-' + mode); await click('input[name="' + name + '"][value="' + value + '"]'); }}
        await click('.mode-geography'); await click('input[name="k-mode"][value="manual"]');
        $('manual-k').value = '7'; $('manual-k').dispatchEvent(new Event('input', {{bubbles: true}}));
        await click('#compare-modes'); const restored = [];
        for (const [mode, name] of [
          ['geo_cost', 'cost-weight'], ['geo_volume', 'volume-weight'],
          ['bear_zones', 'bear-threshold'], ['bear_volume_zones', 'bear-volume-threshold'], ['geography', 'k-mode'],
        ]) {{
          await click('[data-comparison-mode="' + mode + '"]');
          await click('#cluster-periods input[value="retro"]');
          restored.push([checked('analysis-mode'), checked(name), checked('k-mode'), $('manual-k').value]);
          await click('#cluster-periods input[value="retro"]');
        }}
        await click('[data-show-on-map="geography"]'); const count = runs.length;
        await click('#btn-run-clustering'); const reused = count === runs.length;
        await click('.mode-geo_cost'); const explicit = [checked('analysis-mode'), $('result-title').textContent];
        document.body.dataset.result = JSON.stringify({{before, after, unchanged, stale,
          submitted: [submitted.mode, submitted.period_types], restored, reused, explicit, compares}});
      }})().catch(error => {{document.body.dataset.result = JSON.stringify({{error: String(error)}});}});
    """
    result = _run_browser_script(script)
    assert "error" not in result, result
    assert result["before"] == result["after"] == ["geography", "По географии", "geography"]
    assert result["unchanged"] and result["stale"]
    assert result["submitted"] == ["geography", ["current", "retro"]]
    assert result["restored"] == [
        ["geo_cost", "0.3", "auto", "3"], ["geo_volume", "0.3", "auto", "3"],
        ["bear_zones", "0.35", "auto", "3"], ["bear_volume_zones", "0.35", "auto", "3"],
        ["geography", "auto", "auto", "3"],
    ]
    assert result["reused"] and result["compares"] == 1
    assert result["explicit"] == ["geo_cost", "geography"]


def test_cached_comparison_switches_the_active_product_result_without_recalculation():
    state_module = re.sub(
        r"^import .*?;\n",
        "",
        _read("frontend/js/clustering/state.js"),
        flags=re.MULTILINE,
    ).replace("export ", "")
    controller = re.sub(
        r"^import[\s\S]*?;\n",
        "",
        _read("frontend/js/clustering/controller.js"),
        flags=re.MULTILINE,
    ).replace("export ", "")
    script = f"""
      const elements = new Map();
      const element = id => elements.get(id) || elements.set(id, {{
        textContent: '',
        classList: {{toggle() {{}}, add() {{}}, remove() {{}}}},
      }}).get(id);
      globalThis.document = {{getElementById: element}};
      globalThis.window = {{dispatchEvent() {{}}}};
      const MODE_LABELS = {{}}, PERIOD_LABELS = {{}}, PRICE_LABELS = {{}};
      const maps = [], tables = [], inspectors = [], pointRequests = [];
      let compareRequests = 0, runRequests = 0;
      function renderFormState() {{}}
      function renderOptionControls() {{}}
      function renderErrorState() {{}}
      function renderComparison() {{}}
      function renderClusteringPoints(result) {{ maps.push(result.analysis.mode); }}
      function renderClusterTable(currentState) {{
        tables.push([
          currentState.result.data.analysis.mode,
          currentState.ui.tableVisible,
          currentState.result.data.cluster_table?.rows?.[0]?.cluster_id ?? null,
        ]);
      }}
      function renderInspector(currentState) {{ inspectors.push(currentState.result.data.analysis.mode); }}
      function setMlResultStale() {{}}
      function clearClusteringResult() {{}}
      function focusClusteringPoint() {{}}
      function highlightCluster() {{}}
      function hoverCluster() {{}}
      function setClusteringLayers() {{}}
      function readChecks() {{ return []; }}
      function runClustering() {{ runRequests += 1; }}
      function fetchClusteringPointRows(payload, options) {{
        let resolve;
        const promise = new Promise(yes => {{ resolve = yes; }});
        pointRequests.push({{payload, signal: options.signal, resolve}});
        return promise;
      }}
      const comparisonResult = (mode, supported, clusterId) => ({{
        status: 'success',
        data_snapshot: 'snapshot-1',
        analysis: {{
          mode,
          origin: {{fias_id: 'origin-1'}},
          destination_region: 'Region A',
          filters: {{period_types: ['current'], price_types: ['spot'], vehicle_types: [], tonnage_ids: []}},
          parameters: mode === 'geo_cost'
            ? {{k_mode: 'auto', n_clusters: 2, economics_weight: 0.3}}
            : mode === 'geo_volume'
              ? {{k_mode: 'auto', n_clusters: 2, volume_weight: 0.3}}
              : mode === 'bear_zones'
                ? {{bear_threshold: 0.35}}
                : mode === 'bear_volume_zones'
                  ? {{volume_threshold: 0.35}}
                  : {{k_mode: 'auto', n_clusters: 2}},
        }},
        points: [{{id: `${{mode}}-point`, fias_id: `${{mode}}-point`, cluster_id: clusterId}}],
        clusters: [{{cluster_id: clusterId}}],
        cluster_table: supported
          ? {{
              supported: true,
              period_types: mode === 'geo_cost' ? ['forecast'] : mode === 'geo_volume' ? ['current', 'forecast'] : ['current'],
              methodology: {{version: mode}},
              rows: [{{cluster_id: clusterId, economic_coverage: {{valid_points: clusterId}}}}],
            }}
          : {{supported: false}},
      }});
      const response = {{
        results: Object.fromEntries([
          ['geography', comparisonResult('geography', true, 1)],
          ['geo_cost', comparisonResult('geo_cost', true, 2)],
          ['geo_volume', comparisonResult('geo_volume', true, 3)],
          ['bear_zones', comparisonResult('bear_zones', false, 4)],
          ['bear_volume_zones', comparisonResult('bear_volume_zones', false, 5)],
        ]),
      }};
      async function runClusteringComparison() {{ compareRequests += 1; return response; }}
      {state_module}
      {controller}
      const capabilities = Object.keys(response.results).map(id => ({{
        id,
        comparison: {{supported: true}},
        parameters: id.startsWith('geo') || id === 'geography'
          ? [{{name: 'k_mode', default: 'auto'}}, {{name: 'n_clusters', manual_default: 2}}]
          : [{{name: 'singleton_threshold', default: 0.75}}],
      }}));
      state = createClusteringState({{mode_capabilities: capabilities, defaults: {{mode: 'geography'}}}});
      Object.assign(state.form, {{
        origin: {{fias_id: 'origin-1', name: 'Origin'}}, destinationRegion: 'Region A',
        periodTypes: ['current'], priceTypes: ['spot'],
      }});
      await runComparison();
      const order = Object.keys(state.comparison.results);
      state.ui.selectedCluster = 1;
      state.ui.selectedPoint = 'geography-point';
      const pendingRows = loadPointRows();
      const oldPointRowsKey = pointRowsKey();
      activateComparisonMode('geo_cost');
      const selectionAfterSwitch = [state.ui.selectedCluster, state.ui.selectedPoint];
      const pulseCancelled = pointRequests[0].signal.aborted;
      pointRequests[0].resolve({{rows: [{{source_row_id: 'old'}}], total: 1, has_more: false}});
      await pendingRows;
      const leakedPointRows = state.ui.pointRows.get(oldPointRowsKey).rows.length;
      const snapshots = [];
      for (const mode of ['geo_cost', 'geo_volume', 'bear_zones', 'bear_volume_zones', 'geography']) {{
        activateComparisonMode(mode);
        snapshots.push([
          state.comparison.activeMode,
          state.result.data.analysis.mode,
          state.ui.tableVisible,
          state.result.data.cluster_table?.rows?.[0]?.cluster_id ?? null,
          state.result.data.cluster_table?.period_types?.join('+') ?? null,
          state.result.data.cluster_table?.methodology?.version ?? null,
          state.result.data.cluster_table?.rows?.[0]?.economic_coverage?.valid_points ?? null,
          `${{state.ui.tableSort.key}}:${{state.ui.tableSort.direction}}`,
        ]);
      }}
      state.form.periodTypes = ['forecast'];
      activateComparisonMode('geo_volume');
      console.log(JSON.stringify({{
        compareRequests, runRequests, order,
        snapshots, maps, selectionAfterSwitch, pulseCancelled, leakedPointRows,
        stale: isComparisonStale(state) && isResultStale(state),
        lastTable: tables.at(-1), lastInspector: inspectors.at(-1),
      }}));
    """

    assert _run_node_script(script) == {
        "compareRequests": 1,
        "runRequests": 0,
        "order": ["geography", "geo_cost", "geo_volume", "bear_zones", "bear_volume_zones"],
        "snapshots": [
            ["geo_cost", "geo_cost", True, 2, "forecast", "geo_cost", 2, "trip_count:desc"],
            ["geo_volume", "geo_volume", True, 3, "current+forecast", "geo_volume", 3, "trip_count:desc"],
            ["bear_zones", "bear_zones", False, None, None, None, None, "trip_count:desc"],
            ["bear_volume_zones", "bear_volume_zones", False, None, None, None, None, "trip_count:desc"],
            ["geography", "geography", True, 1, "current", "geography", 1, "trip_count:desc"],
        ],
        "maps": ["geography", "geo_cost", "geo_cost", "geo_volume", "bear_zones", "bear_volume_zones", "geography", "geo_volume"],
        "selectionAfterSwitch": [None, None],
        "pulseCancelled": True,
        "leakedPointRows": 0,
        "stale": True,
        "lastTable": ["geo_volume", True, 3],
        "lastInspector": "geo_volume",
    }


@pytest.mark.parametrize("late_error", [False, True])
@pytest.mark.parametrize("late_kind,replacement", [
    (kind, replacement) for kind in ("run", "compare") for replacement in ("cached", "reset", "fresh")
] + [("compare", "comparison_tab")])
def test_cancelled_calculation_cannot_replace_new_context(late_kind, late_error, replacement):
    state_module = _read("frontend/js/clustering/state.js").replace("export ", "")
    controller = re.sub(
        r"^import[\s\S]*?;\n", "", _read("frontend/js/clustering/controller.js"),
        flags=re.MULTILINE,
    ).replace("export ", "")
    script = f"""
      import assert from 'node:assert/strict';
      const elements = new Map();
      globalThis.document = {{getElementById: id => {{
        if (!elements.has(id)) elements.set(id, {{disabled: false, value: '', textContent: '',
          classList: {{add() {{}}, remove() {{}}, toggle() {{}}}},
              setAttribute() {{}}, replaceChildren() {{}}, querySelector() {{return this;}}}});
        return elements.get(id);
      }}}};
      globalThis.Option = class {{}};
      const MODE_LABELS = {{}}, PERIOD_LABELS = {{}}, PRICE_LABELS = {{}};
      const renderFormState = () => {{}}, renderOptionControls = () => {{}};
      const renderErrorState = () => {{}}, renderComparison = () => {{}};
      const renderClusteringPoints = () => {{}}, clearClusteringResult = () => {{}};
      const renderClusterTable = () => {{}}, renderInspector = () => {{}};
      const setMlResultStale = () => {{}};
      const pending = [];
      function request(payload, options) {{
        return new Promise((resolve, reject) => pending.push({{resolve, reject, signal: options.signal}}));
      }}
      const runClustering = request, runClusteringComparison = request;
      const fetchClusteringRevision = async results => ({{data_snapshot: results[0].data_snapshot,
        available: results.map(() => true)}});
      {state_module}
      {controller}
      const options = {{mode_capabilities: [{{id: 'geography', comparison: {{supported: true}},
        parameters: [{{name: 'k_mode', default: 'auto'}}, {{name: 'n_clusters', manual_default: 2}}]}}]}};
      state = createClusteringState(options);
      Object.assign(state.form, {{origin: {{fias_id: 'o'}}, destinationRegion: 'R'}});
      const result = snapshot => ({{status: 'success', data_snapshot: snapshot,
        analysis: {{mode: 'geography', origin: {{fias_id: 'o'}}, destination_region: 'R',
          filters: datasetSnapshot(state.form), parameters: {{k_mode: 'auto'}}}},
        cluster_table: {{supported: true}}, points: [], clusters: []}});
      const old = result('old'), fresh = result('fresh');
      if ({json.dumps(replacement)} === 'comparison_tab') {{
        state.comparison.context = datasetSnapshot(state.form);
        state.comparison.results = {{geography: old}};
        setResult(state, old, buildRequest(state.form));
        state.form.destinationRegion = 'New Region';
      }}
      const first = {json.dumps(late_kind)} === 'run' ? executeRun() : runComparison();
      for (let i = 0; i < 5; i++) await Promise.resolve();
      if ({json.dumps(replacement)} === 'comparison_tab') {{
        activateComparisonMode('geography');
        assert.equal(pending[0].signal.aborted, false, 'old tab cannot cancel new comparison');
        assert.equal(state.result.requestSnapshot.destination_region, 'R', 'old result keeps frozen context');
        assert.equal(isResultStale(state), true);
      }} else if ({json.dumps(replacement)} === 'reset') reset();
      else {{
        if ({json.dumps(replacement)} === 'cached') state.result.cache.set(requestSignature(buildRequest(state.form)), fresh);
        const next = executeRun();
        for (let i = 0; i < 5; i++) await Promise.resolve();
        if ({json.dumps(replacement)} === 'fresh') {{
          pending[1].resolve(fresh);
        }}
        await next;
      }}
      assert.equal(pending[0].signal.aborted, {json.dumps(replacement)} !== 'comparison_tab', 'request cancellation');
      if ({json.dumps(late_error)}) pending[0].reject(new Error('late error'));
      else pending[0].resolve({json.dumps(late_kind)} === 'run' ? old : {{results: {{geography: {json.dumps(replacement)} === 'comparison_tab' ? fresh : old}}}});
      await first;
      assert.equal(state.result.data, {json.dumps(replacement)} === 'reset' ? null
        : {json.dumps(replacement)} === 'comparison_tab' && {json.dumps(late_error)} ? old : fresh);
      assert.equal(state.result.error, null);
      assert.equal(document.getElementById('btn-run-clustering').disabled, false);
      console.log(JSON.stringify({{safe: true}}));
    """
    assert _run_node_script(script) == {"safe": True}


def test_rejected_snapshot_invalidation_preserves_unrelated_cached_data():
    state_module = _read("frontend/js/clustering/state.js").replace("export ", "")
    script = f"""
      import assert from 'node:assert/strict';
      {state_module}
      const state = createClusteringState({{mode_capabilities: [{{id: 'geography'}}]}});
      const rejected = {{data_snapshot: 'rejected'}}, valid = {{data_snapshot: 'valid'}};
      state.result.cache.set('bad', rejected);
      state.result.cache.set('good', valid);
      state.comparison.cache.set('bad', {{results: {{geography: rejected}}}});
      state.comparison.cache.set('good', {{results: {{geography: valid}}}});
      state.comparison.results = {{geography: rejected, geo_cost: valid}};
      const goodRows = {{status: 'success', rows: [{{source_row_id: 'good'}}]}};
      state.ui.pointRows.set(requestSignature({{data_snapshot: 'valid'}}), goodRows);
      rejectDataSnapshot(state, 'rejected');
      assert.equal(state.result.cache.get('good'), valid);
      assert.equal(state.comparison.cache.get('good').results.geography, valid);
      assert.equal(state.comparison.results.geo_cost, valid);
      assert.equal(state.ui.pointRows.get(requestSignature({{data_snapshot: 'valid'}})), goodRows);
      assert.throws(() => setResult(state, rejected, {{}}), {{code: 'STALE_DATA_SNAPSHOT'}});
      setResult(state, valid, {{}});
      assert.equal(state.result.data, valid);
      console.log(JSON.stringify({{isolated: true}}));
    """
    assert _run_node_script(script) == {"isolated": True}


def test_point_rows_render_all_inspector_states_and_leave_bear_unchanged():
    inspector = re.sub(
        r"^import .*?;\n",
        "",
        _read("frontend/js/clustering/inspector.js"),
        flags=re.MULTILINE,
    ).replace("export ", "")
    shell = "".join(
        f'<div id="{item}"></div>'
        for item in (
            "inspector-empty", "inspector-result", "result-status", "result-title",
            "result-subtitle", "result-total-trips", "result-outliers", "result-warnings",
            "result-context", "result-quality", "result-metrics", "point-details",
            "cluster-list", "cluster-details",
        )
    )
    script = f"""
      const MODE_LABELS = {{geography: 'География', bear_zones: 'Медвежьи зоны'}};
      const PERIOD_LABELS = {{current: 'Текущий'}};
      const escapeHtml = value => String(value ?? '');
      const fmt = value => String(value ?? 0);
      const decimal = value => value == null ? '—' : String(value);
      const km = value => value == null ? '—' : `${{value}} км`;
      const rubKm = value => value == null ? '—' : `${{value}} ₽/км`;
      const percent = value => value == null ? '—' : `${{value * 100}}%`;
      const clusterLabel = () => '';
      {inspector}
      document.body.innerHTML = {json.dumps(shell)};
      const point = {{id: 'a', fias_id: 'a', name: 'A', lat: 1, lon: 1, trip_count: 5, cluster_id: 0, status: 'assigned', weighted_route_length: 100, period_types: ['current'], data_quality_flags: ['invalid_units']}};
      const result = {{status: 'success', data_snapshot: 'snapshot', analysis: {{mode: 'geography', parameters: {{k_mode: 'manual', n_clusters: 2}}, origin: {{fias_id: 'o', name: 'O'}}, destination_region: 'R', filters: {{period_types: ['current']}}}}, data_quality: {{}}, warnings: [], metrics: {{}}, graph_metrics: {{}}, outliers: [], clusters: [], points: [point], cluster_table: {{supported: true}}}};
      const rows = Array.from({{length: 50}}, (_, index) => ({{source_row_id: String(index), period_id: '202610', period_type: 'current', price_type: 'spot', vehicle_type: 'tent', tonnage_id: '20', price: 100, route_length: 10, rub_per_km: 10, trip_count: index ? 1 : null, warnings: index ? [] : ['invalid_bid_count']}}));
      const state = {{result: {{data: result}}, ui: {{selectedCluster: null, selectedPoint: 'a', pointRows: new Map([['cache-key', {{status: 'success', rows, total: 51, hasMore: true, open: false}}]])}}}};
      const handlers = {{pointRowsKey: () => 'cache-key'}};
      renderInspector(state, handlers);
      const page = {{rows: document.querySelectorAll('.pulse-table tbody tr').length, closed: !document.querySelector('.pulse-details').open, more: Boolean(document.querySelector('[data-pulse-more]')), missingMachines: document.querySelector('.pulse-table tbody tr td:nth-child(11)').textContent, pointMachines: document.querySelector('.point-facts').textContent.includes('Машины')}};
      state.ui.pointRows.set('cache-key', {{status: 'loading', rows: [], total: null, hasMore: false, open: true}});
      renderInspector(state, handlers);
      const loading = document.querySelector('.pulse-state')?.getAttribute('role');
      state.ui.pointRows.set('cache-key', {{status: 'error', error: 'offline', rows: [], total: null, hasMore: false, open: true}});
      renderInspector(state, handlers);
      const retry = Boolean(document.querySelector('[data-pulse-retry]'));
      state.ui.pointRows.set('cache-key', {{status: 'stale', rows: [], total: null, hasMore: false, open: true}});
      renderInspector(state, handlers);
      const stale = document.querySelector('.pulse-state')?.textContent.includes('Пересчитайте');
      result.analysis.mode = 'bear_zones';
      result.analysis.parameters = {{bear_threshold: 0.35}};
      result.cluster_table = {{supported: false}};
      renderInspector(state, handlers);
      const bear = {{pulse: Boolean(document.querySelector('.pulse-details')), trips: document.querySelector('.point-facts').textContent.includes('Перевозки')}};
      document.body.dataset.result = JSON.stringify({{page, loading, retry, stale, bear}});
    """

    assert _run_browser_script(script) == {
        "page": {
            "rows": 50,
            "closed": True,
            "more": True,
            "missingMachines": "—",
            "pointMachines": True,
        },
        "loading": "status",
        "retry": True,
        "stale": True,
        "bear": {"pulse": False, "trips": True},
    }


def test_origin_summary_selects_frozen_origin_rows_and_keeps_table():
    actual = _run_browser_script(_product_workspace_script("""
      await choose('b'); await choose('a');
      const region = document.getElementById('cluster-region');
      region.value = 'R'; region.dispatchEvent(new Event('change', {bubbles: true})); await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      const table = document.getElementById('cluster-table-panel').innerHTML;
      window.dispatchEvent(new CustomEvent('clustering-point-select', {detail: {pointId: 'x'}}));
      await pause();
      const contributor = document.querySelector('[data-origin-fias="b"]');
      if (!contributor) throw Error('Origin summary missing');
      contributor.focus(); contributor.click(); await pause();
      const detail = requests.find(r => r.path === 'point-rows').payload;
      const sameTable = table === document.getElementById('cluster-table-panel').innerHTML;
      document.querySelector('#cluster-periods input[value="retro"]').click(); await pause();
      document.body.dataset.result = JSON.stringify({origin: detail.detail_origin_fias,
        origins: detail.origin_fiases, periods: detail.period_types,
        summary: requests.filter(r => r.path === 'point-origins').length,
        selected: document.querySelector('[data-origin-fias="b"]').getAttribute('aria-pressed'),
        table: sameTable,
        stale: !document.getElementById('analysis-stale').classList.contains('hidden')});
    """))
    assert actual == {'origin': 'b', 'origins': ['a', 'b'], 'periods': ['current'],
                      'summary': 1, 'selected': 'true', 'table': True, 'stale': True}


def test_origin_summary_and_detail_cancel_late_responses_and_reject_all_related_caches():
    state_module = _read("frontend/js/clustering/state.js").replace("export ", "")
    controller = re.sub(r"^import[\s\S]*?;\n", "", _read("frontend/js/clustering/controller.js"), flags=re.MULTILINE).replace("export ", "")
    actual = _run_node_script(f"""
      const summaries = [], pages = [];
      function pendingRequest(list, payload, options) {{
        let resolve, reject; const promise = new Promise((yes,no) => {{resolve=yes; reject=no}});
        list.push({{payload, signal: options.signal, resolve, reject}}); return promise;
      }}
      function fetchClusteringPointOrigins(payload, options) {{return pendingRequest(summaries,payload,options)}}
      function fetchClusteringPointRows(payload, options) {{return pendingRequest(pages,payload,options)}}
      function renderInspector() {{}} function focusClusteringPoint() {{}}
      function highlightCluster() {{}}
      function renderClusterTable() {{}}
      {state_module}
      {controller}
      renderAll = () => {{}};
      const frozen = {{origin_fiases:['a','b','c'], destination_region:'R', mode:'geography', parameters:{{}},
        period_types:['current'], price_types:['spot'], vehicle_types:[], tonnage_ids:[]}};
      const result = {{data_snapshot:'s', analysis:{{frozen_request:frozen}}, cluster_table:{{supported:true}}, points:[{{id:'x'}},{{id:'y'}}]}};
      state = {{result:{{data:result, cache:new Map()}}, ui:{{pointRows:new Map(), pointOrigins:new Map()}}}};
      selectPoint('x'); const first = summaries[0];
      selectPoint('y'); const cancelled = first.signal.aborted;
      first.resolve({{origins:[{{origin_fias:'wrong'}}]}});
      summaries[1].reject(Error('offline')); await new Promise(r=>setTimeout(r,0));
      const error = state.ui.pointOrigins.get(pointOriginsKey()).status;
      const retry = loadPointOrigins(); summaries[2].resolve({{origins:[{{origin_fias:'b'}}]}}); await retry;
      state.ui.selectedOrigin='a'; const late = loadPointRows();
      state.ui.selectedOrigin='b'; const next = loadPointRows();
      pages[0].resolve({{rows:[{{source_row_id:'wrong'}}],total:1,has_more:false}}); await late;
      pages[1].resolve({{rows:[{{source_row_id:'b-1'}}],total:1,has_more:false}}); await next;
      const noLeak = pointRowsForSelection().rows.map(r=>r.source_row_id);
      const originKey = pointRowsKey();
      rejectUnavailableResult(state,result);
      const unavailable = [state.ui.pointRows.get(originKey).status, state.ui.pointOrigins.get(pointOriginsKey()).status];
      rejectDataSnapshot(state,'s');
      const stale = [state.ui.pointRows.get(originKey).status, state.ui.pointOrigins.get(pointOriginsKey()).status];
      console.log(JSON.stringify({{cancelled,error,noLeak,unavailable,stale,
        origins:pages[1].payload.origin_fiases, detail:pages[1].payload.detail_origin_fias,
        summaryRows:state.ui.pointOrigins.get(pointOriginsKey()).origins}}));
    """)
    assert actual == {'cancelled': True, 'error': 'error', 'noLeak': ['b-1'],
                      'unavailable': ['unavailable', 'unavailable'], 'stale': ['stale', 'stale'],
                      'origins': ['a', 'b', 'c'], 'detail': 'b', 'summaryRows': [{'origin_fias': 'b'}]}


def test_cached_origin_selection_renders_the_selected_origin_without_refetch():
    script = _product_workspace_script("""
      await choose('b'); await choose('a');
      const region=document.getElementById('cluster-region'); region.value='R';
      region.dispatchEvent(new Event('change',{bubbles:true})); await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'x'}})); await pause();
      document.querySelector('[data-origin-fias="b"]').click(); await pause();
      document.querySelector('[data-origin-fias="a"]').click(); await pause();
      const before=requests.filter(r=>r.path==='point-rows').length;
      document.querySelector('[data-origin-fias="b"]').focus();
      document.querySelector('[data-origin-fias="b"]').click(); await pause();
      document.body.dataset.result=JSON.stringify({selected:document.querySelector('[data-origin-fias="b"]').getAttribute('aria-pressed'),
        context:document.querySelector('.pulse-details').textContent.includes('b → x'),
        requestFree:before===requests.filter(r=>r.path==='point-rows').length,
        focus:document.activeElement.dataset.originFias});
    """)
    script = script.replace("origins: [{origin_fias: 'b'", "origins: [{origin_fias:'a',origin_name:'Alpha',trip_count:10,warnings:[]},{origin_fias: 'b'")
    assert _run_browser_script(script) == {'selected':'true','context':True,'requestFree':True,'focus':'b'}

def test_drill_up_origin_returns_to_point_without_requests_or_context_changes():
    assert _run_browser_script(_product_workspace_script("""
      await choose('b'); await choose('a');
      const region = document.getElementById('cluster-region'); region.value='R';
      region.dispatchEvent(new Event('change',{bubbles:true})); await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'x'}})); await pause();
      document.querySelector('[data-origin-fias="b"]').click(); await pause();
      const saved=workspace.getState().result.data;
      workspace.getState().ui.tableSort={key:'point_count',direction:'asc'};
      workspace.getState().ui.tableOpen=false;
      const before=requests.length;
      const up=document.querySelector('[data-point-summary]');
      if(!up || !up.textContent.includes('К сводке точки')) {document.body.dataset.result=JSON.stringify({error:'Missing return to point summary'}); return;}
      up.focus(); up.click(); await pause();
      const ui=workspace.getState().ui;
      document.body.dataset.result=JSON.stringify({point:ui.selectedPoint,origin:ui.selectedOrigin,
        same:saved===workspace.getState().result.data,sort:ui.tableSort,open:ui.tableOpen,
        requestFree:before===requests.length,focus:document.activeElement.dataset.originFias,
        rowsClosed:!document.querySelector('.pulse-details').open});
    """)) == {'point':'x','origin':None,'same':True,'sort':{'key':'point_count','direction':'asc'},
                'open':False,'requestFree':True,'focus':'b','rowsClosed':True}

def _drill_workspace_script(actions):
    script = _product_workspace_script(actions)
    return script.replace("let failRun = false", "let holdRows=false; const heldRows=[]; let failRun=false").replace("if (path === 'point-rows') {", "if (path === 'point-rows') { if(holdRows) await new Promise(resolve=>heldRows.push(resolve));").replace("points: [{id: 'x', fias_id: 'x', name: 'X', trip_count: 40}]",
        "points: [{id:'x',fias_id:'x',name:'X',trip_count:40,cluster_id:0},"
        "{id:'y',fias_id:'y',name:'Y',trip_count:10,cluster_id:1},"
        "{id:'outside',fias_id:'outside',name:'Outside',trip_count:1,cluster_id:null}]") .replace(
        "clusters: [], cluster_table:",
        "clusters: [{cluster_id:0,point_ids:['x'],point_count:1,trip_count:40},{cluster_id:1,point_ids:['y'],point_count:1,trip_count:10}], cluster_table:")


@pytest.mark.parametrize('parent', ['different', 'overview', 'unassigned'])
def test_parent_navigation_clears_descendants_and_ignores_late_rows(parent):
    actions = """
      await choose('b'); const region=document.getElementById('cluster-region'); region.value='R';
      region.dispatchEvent(new Event('change',{bubbles:true})); await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'x',clusterId:0}})); await pause();
      const old=workspace.getState().result.data;
      holdRows=true;
      document.querySelector('[data-origin-fias="b"]').click(); await pause();
      const before=requests.filter(r=>r.path==='run'||r.path==='compare').length;
      PARENT_ACTION
      holdRows=false; heldRows.forEach(resolve=>resolve());
      await pause();
      const ui=workspace.getState().ui;
      document.body.dataset.result=JSON.stringify({cluster:ui.selectedCluster,point:ui.selectedPoint,
        origin:ui.selectedOrigin,same:old===workspace.getState().result.data,
        requestFree:before===requests.filter(r=>r.path==='run'||r.path==='compare').length});
    """.replace('PARENT_ACTION', {
        'different': "document.querySelector('#cluster-points'); document.querySelector('#cluster-list [data-cluster-id=\"1\"]').click();",
        'overview': "document.getElementById('cluster-details-close').click();",
        'unassigned': "window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'outside'}}));",
    }[parent])
    assert _run_browser_script(_drill_workspace_script(actions)) == {
        'cluster': 1 if parent == 'different' else None,
        'point': 'outside' if parent == 'unassigned' else None, 'origin': None,
        'same': True, 'requestFree': True}


def test_drill_up_point_restores_parent_focus_and_reuses_frozen_origin_pages():
    assert _run_browser_script(_drill_workspace_script("""
      await choose('a'); await choose('b');
      const region=document.getElementById('cluster-region'); region.value='R';
      region.dispatchEvent(new Event('change',{bubbles:true})); await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      document.querySelector('#cluster-list [data-cluster-id="0"]').click();
      document.querySelector('[data-point-id="x"]').click(); await pause();
      document.querySelector('[data-origin-fias="b"]').click(); await pause();
      document.querySelector('#cluster-periods input[value="retro"]').click();
      const before=requests.length;
      document.querySelector('[data-point-summary]').click();
      document.getElementById('point-details-close').click();
      const parentFocus=document.activeElement.dataset.pointId;
      const ui=workspace.getState().ui;
      const atParent=[ui.selectedCluster,ui.selectedPoint,ui.selectedOrigin];
      document.querySelector('[data-point-id="x"]').click(); await pause();
      document.querySelector('[data-origin-fias="b"]').click(); await pause();
      document.body.dataset.result=JSON.stringify({parentFocus,atParent,
        requestFree:before===requests.length,origin:ui.selectedOrigin,
        stale:!document.getElementById('analysis-stale').classList.contains('hidden'),
        frozen:workspace.getState().result.data.analysis.frozen_request.period_types});
    """)) == {'parentFocus':'x','atParent':[0,None,None],'requestFree':True,
               'origin':'b','stale':True,'frozen':['current']}


def test_drill_up_pooled_rows_keeps_summary_focus_after_cancelled_response():
    assert _run_browser_script(_drill_workspace_script("""
      await choose('b'); const region=document.getElementById('cluster-region'); region.value='R';
      region.dispatchEvent(new Event('change',{bubbles:true})); await pause();
      document.getElementById('btn-run-clustering').click(); await pause();
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'x'}})); await pause();
      holdRows=true;
      document.querySelector('.pulse-details summary').focus();
      document.querySelector('.pulse-details summary').click();
      const loadingFocus=document.activeElement.matches('.pulse-details summary');
      document.querySelector('[data-point-summary]').click();
      holdRows=false; heldRows.forEach(resolve=>resolve()); await pause();
      document.body.dataset.result=JSON.stringify({loadingFocus,
        parentFocus:document.activeElement.matches('.pulse-details summary'),
        closed:!document.querySelector('.pulse-details').open,
        point:workspace.getState().ui.selectedPoint,
        rowRequests:requests.filter(r=>r.path==='point-rows').length});
    """)) == {'loadingFocus':True,'parentFocus':True,'closed':True,'point':'x','rowRequests':1}


def test_drill_up_preserves_bottom_table_scroll_and_selection():
    script=_drill_workspace_script("""
      const css=document.createElement('style'); css.textContent='.cluster-table-scroll{width:100px;height:40px;overflow:auto}.cluster-table-scroll table{min-width:900px}'; document.head.append(css);
      await choose('b'); const region=document.getElementById('cluster-region');region.value='R';
      region.dispatchEvent(new Event('change',{bubbles:true}));await pause();
      document.getElementById('btn-run-clustering').click();await pause();
      const scroll=document.querySelector('.cluster-table-scroll');scroll.scrollLeft=75;scroll.scrollTop=10;
      const position=[scroll.scrollLeft,scroll.scrollTop];
      window.dispatchEvent(new CustomEvent('clustering-point-select',{detail:{pointId:'x'}}));await pause();
      document.getElementById('point-details-close').click();
      const after=document.querySelector('.cluster-table-scroll');
      document.body.dataset.result=JSON.stringify({position,after:[after.scrollLeft,after.scrollTop],
        selected:document.querySelector('#cluster-table-panel tr[data-cluster-id="0"]').classList.contains('selected')});
    """).replace('cluster_table: {supported: true, rows: []}',
      'cluster_table: {supported:true,rows:[{cluster_id:0,point_count:1,trip_count:40},{cluster_id:1,point_count:1,trip_count:10}]}')
    actual=_run_browser_script(script)
    assert actual['position'][0] == 75
    assert actual['after'] == actual['position']
    assert actual['selected'] is True
