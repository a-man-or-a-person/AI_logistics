from shapely.geometry import Polygon

from ml.clustering.base import ClusterPoint, summarize_assignments
from ml.spatial.projection import LocalProjection
from ml.spatial.territorialize import territorialize


def test_grid_territorializer_covers_boundary_without_overlap():
    boundary = Polygon(
        [
            (30.0, 59.9),
            (30.2, 59.9),
            (30.2, 60.0),
            (30.0, 60.0),
            (30.0, 59.9),
        ]
    )
    projection = LocalProjection(59.95, 30.1)
    first_xy = projection.project(59.95, 30.03)
    second_xy = projection.project(59.95, 30.17)
    points = [
        ClusterPoint("a", "A", "R", *first_xy, shipment_count=2),
        ClusterPoint("b", "B", "R", *second_xy, shipment_count=3),
    ]
    clusters = summarize_assignments(
        points,
        {"a": 0, "b": 1},
        algorithm="test",
        parameters={},
    )

    result = territorialize(points, clusters, boundary, projection, cell_size_m=2_000)

    assert result.metrics["coverage_pct"] >= 99.999
    assert result.metrics["overlap_pct"] == 0
    assert result.metrics["zone_count"] == 2
    assert len(result.zones_geojson["features"]) == 2


def test_territorializer_assigns_full_area_even_when_input_has_noise():
    boundary = Polygon(
        [(30.0, 59.9), (30.1, 59.9), (30.1, 60.0), (30.0, 60.0), (30.0, 59.9)]
    )
    projection = LocalProjection(59.95, 30.05)
    stable_xy = projection.project(59.95, 30.02)
    noise_xy = projection.project(59.95, 30.08)
    points = [
        ClusterPoint("stable", "Stable", "R", *stable_xy),
        ClusterPoint("noise", "Noise", "R", *noise_xy),
    ]
    clusters = summarize_assignments(
        points,
        {"stable": 0, "noise": -1},
        algorithm="density-test",
        parameters={},
    )

    result = territorialize(points, clusters, boundary, projection, cell_size_m=2_000)

    assert result.metrics["coverage_pct"] >= 99.999
    assert result.metrics["zone_count"] == 1
    assert result.zones_geojson["features"][0]["properties"]["assignment_source"] == (
        "inferred_nearest_medoid_grid"
    )
