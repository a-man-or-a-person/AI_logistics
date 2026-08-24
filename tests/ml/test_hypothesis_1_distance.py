import csv

from ml.data.internal import INTERNAL_COLUMNS
from ml.data.loader import PULSE_COLUMNS
from ml.experiments.hypothesis_1_distance import evaluate_distance_hypothesis


def _write(path, columns, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_distance_hypothesis_calculates_variants_and_metrics(tmp_path):
    pulse = tmp_path / "pulse.csv"
    internal = tmp_path / "internal.csv"
    pulse_row = {column: "" for column in PULSE_COLUMNS}
    pulse_row.update(
        {
            "shipment_point_locality_fias_id": "origin-1",
            "shipment_point_region": "Origin region",
            "delivery_point_locality_fias_id": "destination-1",
            "delivery_point_region_unified": "Ленинградская область",
            "delivery_point_town": "Town",
            "period_id": "202608",
            "period_type": "current",
            "bid_count": "2",
            "units": "1000",
            "price_type": "tender",
            "route_length": "100",
        }
    )
    _write(pulse, PULSE_COLUMNS, [pulse_row])
    _write(
        internal,
        INTERNAL_COLUMNS,
        [
            {
                "origin_fias": "origin-1",
                "destination_fias": "destination-1",
                "destination_region": "Ленинградская область",
                "period_id": "202608",
                "route_length": "120",
                "trip_count": "3",
                "reference_price": "1200",
            }
        ],
    )

    report, predictions = evaluate_distance_hypothesis(
        pulse,
        internal,
        destination_region="Ленинградская область",
        origin_fias="origin-1",
    )

    assert report["coverage"]["matched_pct"] == 100
    assert report["variants"]["adjusted_c"]["metrics"]["wape_pct"] == 0
    assert report["decision_gate"]["ready"] is True
    assert predictions[0]["adjusted_c_price"] == 1200
