from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_product_workspace_contains_all_v1_controls():
    html = _read("frontend/index.html")
    for required in (
        'id="app-nav"',
        'id="data-map-view"',
        'id="clustering-controls"',
        'id="clustering-map"',
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
    assert "Одиночная аномально дорогая точка определяется при +70%." in html
    assert "Одиночная аномально объёмная точка определяется при +70%." in html


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
    renderer = map_module.split(
        "export function renderClusteringPoints", maxsplit=1
    )[1].split("function mlClusterStyleFunction", maxsplit=1)[0]

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
    assert "singletonThreshold: 0.70" in state
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
