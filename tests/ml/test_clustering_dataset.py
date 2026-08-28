import csv

import pytest

from ml.data.clustering_dataset import build_clustering_routes
from ml.data.loader import PULSE_COLUMNS


def _write(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(
    period_type,
    price,
    bid_count,
    *,
    price_type="tender",
    vehicle="tent",
    tonnage="7",
):
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
            "units": str(price),
            "bid_count": str(bid_count),
            "price_type": price_type,
            "route_length": "100",
            "vehicle_body_type": vehicle,
            "tonnage_id": tonnage,
        }
    )
    return row


def test_destination_economics_are_weighted_by_trip_count_and_include_forecast(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(
        source,
        [
            _row("current", 1000, 2),
            _row("retro", 2000, 3),
            _row("forecast", 4000, 5),
        ],
    )

    routes, audit = build_clustering_routes(
        source, origin_fias="origin-a", destination_region="Region A"
    )

    assert len(routes) == 1
    assert routes[0].trip_count == 10
    assert routes[0].weighted_price == 2800
    assert routes[0].weighted_rub_per_km == 28
    assert audit["metadata"]["contains_forecast"] is True
    assert audit["contract"]["price_source"] == "Pulse.units"
    assert audit["contract"]["trip_count_source"] == "Pulse.bid_count"


def test_period_and_segment_filters_are_multiselect(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(
        source,
        [
            _row("current", 1000, 2, price_type="tender", vehicle="tent", tonnage="7"),
            _row("forecast", 3000, 4, price_type="spot", vehicle="box", tonnage="10"),
        ],
    )

    routes, audit = build_clustering_routes(
        source,
        origin_fias="origin-a",
        destination_region="Region A",
        period_types={"current"},
        price_types={"tender", "other"},
        vehicle_types={"tent", "other"},
        tonnage_ids={"7", "20"},
    )

    assert routes[0].trip_count == 2
    assert routes[0].weighted_price == 1000
    assert audit["metadata"]["contains_forecast"] is False


def test_single_origin_and_destination_region_are_required(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(source, [_row("current", 1000, 2)])

    with pytest.raises(ValueError, match="origin_fias"):
        build_clustering_routes(source, destination_region="Region A")
    with pytest.raises(ValueError, match="destination_region"):
        build_clustering_routes(source, origin_fias="origin-a")


def test_missing_destination_fias_is_counted_and_not_guessed(tmp_path):
    source = tmp_path / "pulse.csv"
    missing = _row("current", 1000, 2)
    missing["delivery_point_locality_fias_id"] = ""
    _write(source, [_row("current", 1000, 2), missing])

    routes, audit = build_clustering_routes(
        source, origin_fias="origin-a", destination_region="Region A"
    )

    assert len(routes) == 1
    assert audit["excluded_missing_fias_rows"] == 1
