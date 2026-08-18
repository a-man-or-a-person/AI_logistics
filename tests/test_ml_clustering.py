from copy import deepcopy

from backend.ml_clustering import cluster_points


def test_clustering_does_not_mutate_input_coordinates():
    points = [
        {"town": "A", "lat": 55.0, "lon": 37.0, "rub_per_km": 50, "bid_count": 1},
        {"town": "B", "lat": 55.0, "lon": 37.0, "rub_per_km": 60, "bid_count": 1},
        {"town": "C", "lat": 56.0, "lon": 38.0, "rub_per_km": 70, "bid_count": 1},
    ]
    original = deepcopy(points)

    result = cluster_points(points, k=2)

    assert result["k"] == 2
    assert points == original
    returned = {point["town"]: point for cluster in result["clusters"] for point in cluster["points"]}
    assert returned["B"]["lat"] == 55.0
    assert returned["B"]["lon"] == 37.0


def test_technical_weight_is_not_included_in_total_bids():
    points = [
        {
            "town": "With data",
            "lat": 55.0,
            "lon": 37.0,
            "rub_per_km": 50,
            "bid_count": 10,
            "cluster_weight": 10,
        },
        {
            "town": "Without data",
            "lat": 56.0,
            "lon": 38.0,
            "rub_per_km": 0,
            "cluster_rub_per_km": 55,
            "bid_count": 0,
            "cluster_weight": 1,
        },
    ]

    result = cluster_points(points, k=2)

    assert sum(cluster["total_bids"] for cluster in result["clusters"]) == 10
