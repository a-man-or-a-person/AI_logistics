from dataclasses import replace

from ml.clustering.base import ClusterPoint
from ml.clustering.bear_zones import BearZoneDetector
from ml.clustering.geo_cost import GeoCostClusterer
from ml.clustering.geographic import GeographicClusterer
from ml.spatial.graph import SpatialGraphBuilder


def _point(identifier, x, y=0, *, trips=10, rate=100):
    return ClusterPoint(
        identifier,
        identifier,
        "R",
        x,
        y,
        trips,
        rate * 100,
        rate,
    )


def test_geography_is_connected_deterministic_and_economics_independent():
    points = [_point(str(index), index) for index in range(6)]
    graph = SpatialGraphBuilder().build(points)
    clusterer = GeographicClusterer()

    first = clusterer.fit(points, {"n_clusters": 2, "spatial_graph": graph})
    economic_changes = [
        replace(point, trip_count=1000 - index, weighted_rub_per_km=9999 - index)
        for index, point in enumerate(points)
    ]
    second = clusterer.fit(
        economic_changes,
        {"n_clusters": 2, "spatial_graph": SpatialGraphBuilder().build(economic_changes)},
    )

    assert first.point_assignments == second.point_assignments
    assert first.metrics["connectivity_violations"] == 0
    assert first.parameters["k_mode"] == "manual"


def test_geography_auto_k_and_spatial_outlier():
    points = [_point(str(index), index) for index in range(5)]
    points.append(_point("far", 100))

    result = GeographicClusterer().fit(points, {"n_clusters": "auto", "k_max": 4})

    assert result.point_assignments["far"] == -1
    assert {"point_id": "far", "type": "spatial_outlier"} in result.outliers
    assert result.parameters["auto_k_candidates"]


def test_geo_cost_preserves_connectivity_and_reports_70_30():
    points = [
        _point("a", 0, rate=100),
        _point("b", 1, rate=100),
        _point("c", 2, rate=300),
        _point("d", 3, rate=300),
    ]

    result = GeoCostClusterer().fit(
        points,
        {"n_clusters": 2, "geography_weight": 0.7, "economics_weight": 0.3},
    )

    assert result.metrics["connectivity_violations"] == 0
    assert result.parameters["geography_weight"] == 0.7
    assert result.parameters["economics_weight"] == 0.3
    assert result.regional_weighted_rub_per_km == 200


def test_cost_changes_merge_priority_without_changing_spatial_edges():
    points = [
        _point("a", 0, rate=100),
        _point("b", 1, rate=100),
        _point("c", 3, rate=100),
        _point("d", 4, rate=500),
    ]
    graph = SpatialGraphBuilder().build(points)

    geography = GeographicClusterer().fit(
        points, {"n_clusters": 2, "spatial_graph": graph}
    )
    geo_cost = GeoCostClusterer().fit(
        points,
        {
            "n_clusters": 2,
            "spatial_graph": graph,
            "geography_weight": 0.6,
            "economics_weight": 0.4,
        },
    )

    assert geography.point_assignments != geo_cost.point_assignments
    assert geo_cost.point_assignments["a"] == geo_cost.point_assignments["c"]
    assert geo_cost.point_assignments["d"] != geo_cost.point_assignments["c"]
    assert geo_cost.metrics["edge_count"] == geography.metrics["edge_count"]


def test_equal_cost_distant_components_never_merge():
    points = [
        _point("a", 0),
        _point("b", 1),
        _point("c", 100),
        _point("d", 101),
    ]

    result = GeoCostClusterer().fit(points, {"n_clusters": 2})

    assert result.point_assignments["a"] == result.point_assignments["b"]
    assert result.point_assignments["c"] == result.point_assignments["d"]
    assert result.point_assignments["a"] != result.point_assignments["c"]


def _bear_points():
    return [
        _point("low-a", 0, trips=20, rate=100),
        _point("low-b", 1, trips=20, rate=100),
        _point("low-c", 2, trips=20, rate=100),
        _point("high-a", 3, trips=3, rate=200),
        _point("high-b", 4, trips=3, rate=200),
    ]


def test_connected_expensive_points_create_valid_bear_zone():
    result = BearZoneDetector().fit(_bear_points(), {})

    zones = [cluster for cluster in result.clusters if cluster.cluster_type == "bear_zone"]
    assert len(zones) == 1
    assert zones[0].point_count == 2
    assert zones[0].relative_rate_delta >= 0.35
    assert result.metrics["connectivity_violations"] == 0


def test_low_volume_spike_does_not_seed_zone_and_singleton_is_candidate():
    points = [
        _point("low-a", 0, trips=50, rate=100),
        _point("low-b", 1, trips=50, rate=100),
        _point("spike", 2, trips=1, rate=300),
    ]

    result = BearZoneDetector().fit(points, {})

    assert not result.clusters
    assert any(
        item["point_id"] == "spike"
        and item["type"] == "low_reliability_candidate"
        for item in result.outliers
    )


def test_70_percent_singleton_stays_candidate_without_volume_default():
    points = [
        _point("low-a", 0, trips=50, rate=100),
        _point("low-b", 1, trips=50, rate=100),
        _point("high", 2, trips=5, rate=300),
    ]

    result = BearZoneDetector().fit(points, {})

    assert any(
        item["point_id"] == "high" and item["type"] == "singleton_candidate"
        for item in result.outliers
    )
    assert result.parameters["singleton_min_trip_count"] is None
