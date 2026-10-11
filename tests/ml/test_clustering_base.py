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


def test_medoid_is_unweighted_real_member_not_centroid_or_largest_volume():
    # Distance sums at x=0,2,10 are 12,10,18; centroid=4, largest volume is x=10.
    points = [ClusterPoint("a", "A", "R", 0, 0, 1),
              ClusterPoint("b", "село B", "R", 2, 0, 1),
              ClusterPoint("c", "C", "R", 10, 0, 999),
              ClusterPoint("noise", "N", "R", 2, 0, 1000)]
    for _ in range(3):
        result = summarize_assignments(points, {"a":0, "b":0, "c":0, "noise":-1}, algorithm="test", parameters={})
        summary = result.clusters[0]
        assert summary.medoid_point_id == "b"
        assert summary.medoid == (2, 0)
        assert summary.centroid == (4, 0)
        assert summary.point_ids == ("a", "b", "c")


@pytest.mark.parametrize("coordinates", [[(0, 0)], [(0, 0), (2, 0)], [(0, 0), (0, 0)]])
def test_medoid_singleton_and_ties_keep_first_existing_order(coordinates):
    points = [ClusterPoint(str(i), "P", "R", x, y) for i, (x, y) in enumerate(coordinates)]
    for _ in range(3):
        summary = summarize_assignments(points, {p.id:0 for p in points}, algorithm="test", parameters={}).clusters[0]
        assert summary.medoid_point_id == "0"
        assert summary.medoid == (0, 0)


def test_no_assigned_members_means_no_representative():
    result = summarize_assignments([ClusterPoint("a", "A", "R", 0, 0)], {"a":-1}, algorithm="test", parameters={})
    assert result.clusters == ()
    assert result.noise_point_ids == ("a",)
