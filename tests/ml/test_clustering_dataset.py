import csv

from ml.data.clustering_dataset import build_clustering_routes
from ml.data.loader import PULSE_COLUMNS


def _write(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(period_type, units, bid_count="999"):
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": "origin-a",
            "shipment_point_region": "Origin",
            "delivery_point_locality_fias_id": "destination-a",
            "delivery_point_region_unified": "Region A",
            "delivery_point_town": "Town A",
            "period_id": "202601",
            "period_type": period_type,
            "units": str(units),
            "bid_count": bid_count,
            "price_type": "tender",
            "route_length": "100",
        }
    )
    return row


def test_clustering_dataset_excludes_forecast_and_aggregates_units(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(source, [_row("current", 2), _row("retro", 3), _row("forecast", 1000)])

    routes, audit = build_clustering_routes(source)

    assert len(routes) == 1
    assert routes[0].shipment_count == 5
    assert audit["forecast_rows_excluded"] == 1
    assert audit["shipment_count_total"] == 5
    assert audit["contract"]["diagnostic_only"] == ["bid_count", "confidence"]


def test_unknown_period_type_is_not_silently_included(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(source, [_row("future_kind", 10)])

    routes, audit = build_clustering_routes(source)

    assert routes == []
    assert audit["unsupported_period_type_rows_excluded"] == 1
