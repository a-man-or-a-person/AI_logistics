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
