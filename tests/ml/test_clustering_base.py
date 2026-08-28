import pytest

from ml.clustering.base import ClusterPoint, summarize_assignments


def test_cluster_result_has_centroid_medoid_shipment_count_and_noise():
    points = [
        ClusterPoint("a", "A", "R", 0, 0, 2),
        ClusterPoint("b", "B", "R", 2, 0, 3),
        ClusterPoint("c", "C", "R", 10, 0, 5),
    ]

    result = summarize_assignments(
        points,
        {"a": 0, "b": 0, "c": -1},
        algorithm="test",
        parameters={"k": 1},
    )

    assert result.clusters[0].centroid == (1, 0)
    assert result.clusters[0].medoid_point_id == "a"
    assert result.clusters[0].shipment_count == 5
    assert result.clusters[0].shipment_share == 0.5
    assert result.noise_point_ids == ("c",)


def test_assignments_must_cover_exactly_all_points():
    points = [ClusterPoint("a", "A", "R", 0, 0)]

    with pytest.raises(ValueError, match="Assignments mismatch"):
        summarize_assignments(points, {}, algorithm="test", parameters={})


def test_cluster_economics_use_trip_count_weight():
    points = [
        ClusterPoint("a", "A", "R", 0, 0, 1, 1000, 10),
        ClusterPoint("b", "B", "R", 1, 0, 3, 2000, 20),
    ]

    result = summarize_assignments(
        points, {"a": 0, "b": 0}, algorithm="test", parameters={}
    )

    assert result.clusters[0].trip_count == 4
    assert result.clusters[0].weighted_price == 1750
    assert result.clusters[0].weighted_rub_per_km == 17.5
