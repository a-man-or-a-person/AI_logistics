from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


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
        pytest.skip("A browser JavaScript runtime is required for the frontend contract")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        page = root / "frontend-contract.html"
        profile = root / "profile"
        page.write_text(f"<!doctype html><body><script>{script}</script></body>", encoding="utf-8")
        completed = subprocess.run(
            [
                edge,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                f"--user-data-dir={profile}",
                "--dump-dom",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    match = re.search(r'data-result="([^"]+)"', completed.stdout)
    assert match is not None, completed.stdout
    return json.loads(match.group(1).replace("&quot;", '"'))


def _run_node_script(script: str) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "frontend-contract.mjs"
        path.write_text(script, encoding="utf-8")
        completed = subprocess.run(
            ["node", str(path)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    return json.loads(completed.stdout)


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
            "origin_fias": "",
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
      function requestSignature(value) {{ return JSON.stringify(value); }}
      {controller}
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
      const page = {{rows: document.querySelectorAll('.pulse-table tbody tr').length, closed: !document.querySelector('.pulse-details').open, more: Boolean(document.querySelector('[data-pulse-more]')), missingMachines: document.querySelector('.pulse-table tbody tr td:nth-child(9)').textContent, pointMachines: document.querySelector('.point-facts').textContent.includes('Машины')}};
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
