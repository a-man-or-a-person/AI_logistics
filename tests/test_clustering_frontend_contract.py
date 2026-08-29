from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_product_controls_replace_legacy_clustering_controls():
    html = _read("frontend/index.html")

    for required in (
        'id="cluster-origin"',
        'id="cluster-region"',
        'id="cluster-mode"',
        'id="cluster-periods"',
        'id="cluster-prices"',
        'id="cluster-vehicles"',
        'id="cluster-tonnages"',
    ):
        assert required in html
    for removed in ("ml-type-control", "ml-weight", "ml-seed", "K-Means"):
        assert removed not in html


def test_frontend_uses_product_api_and_keeps_legacy_backend_only():
    api = _read("frontend/js/api.js")
    app = _read("frontend/js/app.js")

    assert "/api/clustering/options" in api
    assert "/api/clustering/run" in api
    assert "/api/clustering/compare" in api
    assert "/api/ml-cluster" not in api
    assert "runClustering" in app
    assert "compareClusteringModes" in app


def test_product_map_is_point_based_and_has_no_polygon_flow():
    app = _read("frontend/js/app.js")
    map_module = _read("frontend/js/map.js")

    assert "renderClusteringPoints" in app
    product_renderer = map_module.split(
        "export function renderClusteringPoints", maxsplit=1
    )[1].split("function mlClusterStyleFunction", maxsplit=1)[0]
    assert "ol.geom.Point" in product_renderer
    assert "ol.geom.Polygon" not in product_renderer


def test_client_cache_signature_includes_product_context():
    module = _read("frontend/js/clustering.js")

    for field in (
        "origin_fias",
        "destination_region",
        "period_types",
        "price_types",
        "vehicle_types",
        "tonnage_ids",
        "parameters",
    ):
        assert field in module
    assert "best_mode" not in module


def test_clustering_app_references_existing_dom_ids():
    html = _read("frontend/index.html")
    app = _read("frontend/js/app.js")
    html_ids = set(re.findall(r'id="([^"]+)"', html))
    referenced_ids = set(re.findall(r"\$\('([^']+)'\)", app))

    assert referenced_ids - html_ids == set()
