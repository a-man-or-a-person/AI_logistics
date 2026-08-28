import json

import pytest

from ml.spatial.boundaries import load_region_boundary


def _polygon(min_x: float, min_y: float, max_x: float, max_y: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_x, min_y],
                [max_x, min_y],
                [max_x, max_y],
                [min_x, max_y],
                [min_x, min_y],
            ]
        ],
    }


def test_boundary_loader_selects_exact_region_and_dissolves_parts(tmp_path):
    source = tmp_path / "regions.geojson"
    source.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "Ленинградская область"},
                        "geometry": _polygon(29.0, 59.0, 30.0, 60.0),
                    },
                    {
                        "type": "Feature",
                        "properties": {"name": "ленинградская ОБЛАСТЬ"},
                        "geometry": _polygon(30.0, 59.0, 31.0, 60.0),
                    },
                    {
                        "type": "Feature",
                        "properties": {"name": "Другой регион"},
                        "geometry": _polygon(40.0, 50.0, 41.0, 51.0),
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    boundary = load_region_boundary(source, region_name="Ленинградская область")

    assert boundary.bounds == (29.0, 59.0, 31.0, 60.0)
    assert boundary.area == pytest.approx(2.0)


def test_boundary_loader_requires_selector_for_multi_feature_file(tmp_path):
    source = tmp_path / "regions.geojson"
    source.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {}, "geometry": _polygon(1, 1, 2, 2)},
                    {"type": "Feature", "properties": {}, "geometry": _polygon(3, 3, 4, 4)},
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="region_name is required"):
        load_region_boundary(source)


def test_boundary_loader_rejects_non_wgs84_coordinates(tmp_path):
    source = tmp_path / "boundary.geojson"
    source.write_text(json.dumps(_polygon(500_000, 6_000_000, 501_000, 6_001_000)))

    with pytest.raises(ValueError, match="WGS84"):
        load_region_boundary(source)
