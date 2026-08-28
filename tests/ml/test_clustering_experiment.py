import csv
import json

from ml.experiments.clustering_experiment import run_kmeans_sweep


def test_kmeans_sweep_writes_zones_when_approved_boundary_is_supplied(tmp_path):
    locations = tmp_path / "locations.json"
    locations.write_text(
        json.dumps(
            [
                {
                    "id": "a",
                    "name": "A",
                    "region": "R",
                    "latitude": 59.93,
                    "longitude": 30.03,
                    "shipment_count": 2,
                },
                {
                    "id": "b",
                    "name": "B",
                    "region": "R",
                    "latitude": 59.97,
                    "longitude": 30.17,
                    "shipment_count": 3,
                },
            ]
        ),
        encoding="utf-8",
    )
    boundary = tmp_path / "boundary.geojson"
    boundary.write_text(
        json.dumps(
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [30.0, 59.9],
                        [30.2, 59.9],
                        [30.2, 60.0],
                        [30.0, 60.0],
                        [30.0, 59.9],
                    ]
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "output"

    leaderboard = run_kmeans_sweep(
        locations,
        output_dir=output,
        k_values=[2],
        boundary_path=boundary,
        weight_mode="none",
        cell_size_m=2_000,
    )

    assert leaderboard[0]["polygon_coverage_pct"] >= 99.999
    assert leaderboard[0]["polygon_overlap_pct"] == 0
    assert (output / "kmeans_k2" / "zones.geojson").exists()
    metrics = json.loads((output / "kmeans_k2" / "metrics.json").read_text())
    assert metrics["territorialization_metrics"]["zone_count"] == 2
    with (output / "leaderboard.csv").open(encoding="utf-8-sig", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert float(row["polygon_coverage_pct"]) >= 99.999
