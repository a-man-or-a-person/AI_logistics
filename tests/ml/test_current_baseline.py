import csv

from backend.data_processor import calculate_rub_per_km
from ml.data.loader import PULSE_COLUMNS
from ml.experiments.current_baseline import calculate_baseline


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(price, distance, trips, **overrides):
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": "origin-1",
            "shipment_point_region": "Origin region",
            "shipment_point_name_town": "Origin town",
            "delivery_point_locality_fias_id": "destination-1",
            "delivery_point_region_unified": "Ленинградская область",
            "delivery_point_town": "Destination town",
            "period_id": "202601",
            "period_type": "retro",
            "bid_count": str(trips),
            "units": str(price),
            "price_type": "spot",
            "route_length": str(distance),
        }
    )
    row.update(overrides)
    return row


def test_backend_compatible_baseline_matches_production_formula(tmp_path):
    source = tmp_path / "pulse.csv"
    rows = [_row(100, 10, 1), _row(300, 20, 3)]
    _write_csv(source, rows)

    report = calculate_baseline(source, destination_region="Ленинградская область")
    production_records = [
        {"price": float(row["units"]), "route_length": float(row["route_length"])}
        for row in rows
    ]

    assert report["overall"]["backend_compatible_rub_per_km"] == round(
        calculate_rub_per_km(production_records), 4
    )
    assert report["overall"]["trip_weighted_rub_per_km"] == 14.2857
    assert report["overall"]["trip_count"] == 4


def test_baseline_filters_period_and_price_type(tmp_path):
    source = tmp_path / "pulse.csv"
    _write_csv(
        source,
        [
            _row(100, 10, 1),
            _row(300, 20, 3, period_type="forecast", price_type="tender"),
        ],
    )

    report = calculate_baseline(source, period_types={"retro"}, price_types={"spot"})

    assert report["overall"]["record_count"] == 1
    assert report["overall"]["backend_compatible_rub_per_km"] == 10
