from ml.clustering.base import ClusterPoint
from ml.experiments.clustering_modes import run_clustering_modes


def test_runner_uses_one_context_and_does_not_choose_winner(tmp_path):
    points = [
        ClusterPoint(str(index), str(index), "R", index, 0, 10, 1000, 100 + index)
        for index in range(6)
    ]
    filters = {
        "origin_fias": "origin",
        "destination_region": "R",
        "period_types": ["current", "forecast"],
        "price_types": ["spot", "tender"],
        "vehicle_types": ["tent"],
        "tonnage_ids": ["7"],
    }

    report = run_clustering_modes(
        points, filters=filters, output_dir=tmp_path, n_clusters=2
    )

    assert report["winner"] is None
    assert len(report["results"]["geo_cost_sensitivity"]) == 3
    assert {
        item["parameters"]["economics_weight"]
        for item in report["results"]["geo_cost_sensitivity"]
    } == {0.2, 0.3, 0.4}
    assert report["results"]["geography"]["contains_forecast"] is True
    assert report["results"]["geography"]["mixed_tariff_segments"] is True
    assert report["results"]["geography"]["warnings"] == [
        "contains_forecast",
        "mixed_tariff_segments",
    ]
    assert all(
        cluster["connected"] is True
        for cluster in report["results"]["geography"]["clusters"]
    )
    assert all(
        cluster["point_ids"]
        for cluster in report["results"]["geography"]["clusters"]
    )
    assert set(report["graph_study"]) == {"delaunay", "mutual_knn"}
    assert len(report["graph_pruning_sensitivity"]) == 6
    assert report["metadata"]["graph_threshold_m"] > 0
    assert [
        row["bear_threshold_pct"]
        for row in report["bear_threshold_sensitivity"]
    ] == [20, 25, 30, 35, 40, 50]
    assert "winner" not in report["bear_threshold_sensitivity"][0]
    assert (tmp_path / "clustering_modes.json").exists()
