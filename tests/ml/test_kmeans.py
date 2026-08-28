from ml.clustering.base import ClusterPoint
from ml.clustering.kmeans import KMeansClusterer


def test_kmeans_uses_only_metric_coordinates_and_is_reproducible():
    points = [
        ClusterPoint("a", "A", "R", 0, 0, 10),
        ClusterPoint("b", "B", "R", 10, 0, 1),
        ClusterPoint("c", "C", "R", 1000, 1000, 10),
        ClusterPoint("d", "D", "R", 1010, 1000, 1),
    ]
    parameters = {"n_clusters": 2, "weight_mode": "none", "random_state": 42}

    first = KMeansClusterer().fit(points, parameters)
    second = KMeansClusterer().fit(points, parameters)

    assert first.point_assignments == second.point_assignments
    assert len(first.clusters) == 2
    assert first.metrics["point_coverage_pct"] == 100
    assert "polygon_coverage_pct" not in first.metrics


def test_kmeans_rejects_unknown_weight_mode():
    points = [
        ClusterPoint("a", "A", "R", 0, 0),
        ClusterPoint("b", "B", "R", 1, 1),
    ]

    try:
        KMeansClusterer().fit(points, {"n_clusters": 2, "weight_mode": "price"})
    except ValueError as error:
        assert "weight_mode" in str(error)
    else:
        raise AssertionError("Unknown weight mode must be rejected")
