from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_territorial_controls_match_canonical_mvp():
    html = _read("frontend/index.html")

    for required in (
        'id="cluster-origin"',
        'id="cluster-origin-options"',
        'id="cluster-region"',
        'id="cluster-periods"',
        'id="cluster-prices"',
        'id="cluster-k-value"',
        'name="cluster-weight-mode"',
    ):
        assert required in html
    for removed in (
        "cluster-mode",
        "Auto K",
        "geo_cost",
        "bear_zones",
        "Сравнить режимы",
        "ATI",
    ):
        assert removed not in html


def test_frontend_uses_only_canonical_clustering_api():
    api = _read("frontend/js/api.js")
    app = _read("frontend/js/app.js")

    assert "/api/clustering/options" in api
    assert "/api/clustering/origins" in api
    assert "postClustering('preview'" in api
    assert "postClustering('run'" in api
    assert "/api/ml-cluster" not in api
    assert "/api/clustering/compare" not in api
    assert "previewClustering" in app
    assert "runClustering" in app


def test_product_map_supports_raw_points_and_approved_zones():
    app = _read("frontend/js/app.js")
    map_module = _read("frontend/js/map.js")
    renderer = map_module.split(
        "export function renderClusteringPoints", maxsplit=1
    )[1].split("function mlClusterStyleFunction", maxsplit=1)[0]

    assert "renderClusteringPoints(preview)" in app
    assert "result.zones?.available" in renderer
    assert "ol.format.GeoJSON" in renderer
    assert "ol.geom.Point" in renderer
    assert "polygonCoords" not in renderer


def test_stale_state_and_data_quality_are_first_class():
    html = _read("frontend/index.html")
    app = _read("frontend/js/app.js")

    assert 'id="analysis-stale"' in html
    assert 'id="quality-unresolved-list"' in html
    assert "requestSignature" in app
    assert "result.zones.available" in app
    assert "coordinates_unresolved" in app


def test_clustering_app_references_existing_dom_ids():
    html = _read("frontend/index.html")
    app = _read("frontend/js/app.js")
    html_ids = set(re.findall(r'id="([^"]+)"', html))
    referenced_ids = set(re.findall(r"\$\('([^']+)'\)", app))

    assert referenced_ids - html_ids == set()
