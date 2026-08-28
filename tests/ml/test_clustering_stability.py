import json

from ml.experiments.clustering_experiment import run_kmeans_sweep


def test_sweep_compares_weight_modes_and_writes_stability_gate(tmp_path):
    locations = tmp_path / "locations.json"
    locations.write_text(
        json.dumps(
            [
                {
                    "id": str(index),
                    "name": str(index),
                    "region": "R",
                    "latitude": 59 + (index // 3) * 0.2,
                    "longitude": 30 + (index % 3) * 0.2,
                    "shipment_count": 100 if index == 0 else 1,
                }
                for index in range(6)
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "output"

    leaderboard = run_kmeans_sweep(
        locations, output_dir=output, k_values=[2], weight_mode="both", stability_runs=3
    )

    assert {row["weight_mode"] for row in leaderboard} == {"none", "shipment_count"}
    assert all(row["stability_mean_ari"] is not None for row in leaderboard)
    assert all(row["weight_sensitivity_ari"] is not None for row in leaderboard)
    gate = json.loads((output / "decision_gate_clustering.json").read_text())
    assert gate["shortlist"]
    assert "wape" not in json.dumps(gate).casefold()


def test_polygon_does_not_change_point_assignments(tmp_path):
    locations = tmp_path / "locations.json"
    locations.write_text(
        json.dumps(
            [
                {"id": "a", "name": "A", "region": "R", "latitude": 59.93, "longitude": 30.03, "shipment_count": 2},
                {"id": "b", "name": "B", "region": "R", "latitude": 59.97, "longitude": 30.17, "shipment_count": 3},
            ]
        ),
        encoding="utf-8",
    )
    boundary = tmp_path / "boundary.geojson"
    boundary.write_text(
        json.dumps({"type": "Polygon", "coordinates": [[[30, 59.9], [30.2, 59.9], [30.2, 60], [30, 60], [30, 59.9]]]}),
        encoding="utf-8",
    )
    no_boundary = tmp_path / "plain"
    with_boundary = tmp_path / "zones"
    run_kmeans_sweep(locations, output_dir=no_boundary, k_values=[2], weight_mode="none")
    run_kmeans_sweep(
        locations,
        output_dir=with_boundary,
        k_values=[2],
        weight_mode="none",
        boundary_path=boundary,
    )
    plain = (no_boundary / "kmeans_k2" / "assignments.csv").read_text(encoding="utf-8-sig")
    zoned = (with_boundary / "kmeans_k2" / "assignments.csv").read_text(encoding="utf-8-sig")
    assert plain == zoned
