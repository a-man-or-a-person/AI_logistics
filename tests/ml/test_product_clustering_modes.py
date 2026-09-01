from dataclasses import replace

from ml.clustering.base import ClusterPoint
from ml.clustering.bear_volume_zones import BearVolumeZoneDetector
from ml.clustering.bear_zones import BearZoneDetector
from ml.clustering.geo_cost import GeoCostClusterer
from ml.clustering.geo_volume import GeoVolumeClusterer
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


def test_auto_k_sweeps_to_20_without_selecting_search_ceiling():
    points = [
        _point(f"{group}-{offset}", group * 100 + offset)
        for group in range(3)
        for offset in range(10)
    ]

    result = GeographicClusterer().fit(
        points, {"n_clusters": "auto", "k_max": 20}
    )
    candidates = result.parameters["auto_k_candidates"]

    assert candidates[-1]["k"] == 20
    assert result.parameters["n_clusters"] < 20
    assert all("tiny_cluster_share" in candidate for candidate in candidates)
    assert sum(candidate["selected"] for candidate in candidates) == 1


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
    assert sorted(result.metrics["cluster_weighted_rub_per_km"]) == [100, 300]
    assert result.metrics["within_cluster_weighted_rubkm_variance"] == 0
    assert result.metrics["between_cluster_weighted_rubkm_variance"] == 10000


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


def test_geo_volume_uses_log_volume_and_preserves_connectivity():
    points = [
        _point("a", 0, trips=10),
        _point("b", 1, trips=10),
        _point("c", 3, trips=80),
        _point("d", 4, trips=80),
    ]

    result = GeoVolumeClusterer().fit(
        points,
        {"n_clusters": 2, "geography_weight": 0.6, "volume_weight": 0.4},
    )

    assert result.mode == "geo_volume"
    assert result.parameters["volume_transform"] == "log1p"
    assert result.parameters["volume_weight"] == 0.4
    assert result.metrics["connectivity_violations"] == 0
    assert result.metrics["regional_mean_trip_count"] == 45
    assert sorted(result.metrics["cluster_mean_trip_count"]) == [10, 80]
    assert all(cluster.connected is True for cluster in result.clusters)


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


def test_bear_zone_accepts_trip_count_one():
    points = [
        _point("low-a", 0, trips=50, rate=100),
        _point("low-b", 1, trips=50, rate=100),
        _point("high-a", 2, trips=1, rate=300),
        _point("high-b", 3, trips=1, rate=300),
    ]

    result = BearZoneDetector().fit(points, {})

    zone = next(cluster for cluster in result.clusters if cluster.cluster_type == "bear_zone")
    assert zone.point_ids == ("high-a", "high-b")
    assert zone.trip_count == 2
    assert "min_trip_count" not in result.parameters


def test_connected_expensive_points_are_not_filtered_by_volume():
    points = _bear_points()
    points[-2] = replace(points[-2], trip_count=1)
    points[-1] = replace(points[-1], trip_count=2)

    result = BearZoneDetector().fit(points, {})

    assert any(cluster.cluster_type == "bear_zone" for cluster in result.clusters)


def test_singleton_70_percent_does_not_require_min_trip_count():
    points = [
        _point("low-a", 0, trips=50, rate=100),
        _point("low-b", 1, trips=50, rate=100),
        _point("high", 2, trips=1, rate=300),
    ]

    result = BearZoneDetector().fit(points, {})

    singleton = next(
        cluster
        for cluster in result.clusters
        if cluster.cluster_type == "expensive_singleton"
    )
    assert singleton.point_ids == ("high",)
    assert singleton.trip_count == 1
    assert "singleton_min_trip_count" not in result.parameters


def test_trip_count_changes_weighted_rate_but_not_eligibility():
    points = [
        _point("low-a", 0, trips=50, rate=100),
        _point("low-b", 1, trips=50, rate=100),
        _point("high-a", 2, trips=1, rate=300),
        _point("high-b", 3, trips=1, rate=300),
    ]
    changed = [
        replace(point, trip_count=2 if point.id.startswith("high") else point.trip_count)
        for point in points
    ]

    first = BearZoneDetector().fit(points, {})
    second = BearZoneDetector().fit(changed, {})

    assert first.point_assignments["high-a"] >= 0
    assert second.point_assignments["high-a"] >= 0
    assert first.regional_weighted_rub_per_km != second.regional_weighted_rub_per_km


def test_trip_count_zero_does_not_create_division_error():
    points = [
        _point("low-a", 0, trips=50, rate=100),
        _point("low-b", 1, trips=50, rate=100),
        ClusterPoint("zero", "zero", "R", 2, 0, 0, None, None),
    ]

    result = BearZoneDetector().fit(points, {})
    geography = GeographicClusterer().fit(points, {"n_clusters": 2})

    assert result.point_assignments["zero"] == -1
    assert geography.point_assignments["zero"] >= 0


def test_connected_high_volume_points_create_volume_zone():
    points = [
        _point("low-a", 0, trips=10),
        _point("low-b", 1, trips=10),
        _point("high-a", 2, trips=40),
        _point("high-b", 3, trips=40),
    ]

    result = BearVolumeZoneDetector().fit(points, {})

    zone = next(
        cluster
        for cluster in result.clusters
        if cluster.cluster_type == "bear_volume_zone"
    )
    assert zone.point_ids == ("high-a", "high-b")
    assert zone.relative_volume_delta >= 0.35
    assert result.metrics["connectivity_violations"] == 0


def test_high_volume_singleton_uses_fixed_70_percent_threshold():
    points = [
        _point("low-a", 0, trips=10),
        _point("low-b", 1, trips=10),
        _point("high", 100, trips=100),
    ]

    result = BearVolumeZoneDetector().fit(points, {})

    singleton = next(
        cluster
        for cluster in result.clusters
        if cluster.cluster_type == "high_volume_singleton"
    )
    assert singleton.point_ids == ("high",)
    assert singleton.relative_volume_delta >= 0.70
