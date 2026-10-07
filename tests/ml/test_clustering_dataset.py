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
    destination="destination-a",
    period_id="202601",
    price_type="tender",
    route_length="100",
    vehicle="tent",
    tonnage="7",
):
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": "origin-a",
            "shipment_point_region": "Origin",
            "delivery_point_locality_fias_id": destination,
            "delivery_point_region_unified": "Region A",
            "delivery_point_town": "Town A",
            "period_id": period_id,
            "period_type": period_type,
            "units": str(price),
            "bid_count": str(bid_count),
            "price_type": price_type,
            "route_length": route_length,
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


def test_single_source_row_preserves_route_length_at_destination_grain(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(source, [_row("current", 1200, 3, route_length="150")])

    routes, _ = build_clustering_routes(
        source, origin_fias="origin-a", destination_region="Region A"
    )

    assert routes[0].weighted_route_length == 150
    assert routes[0].valid_route_length_trip_count == 3


def test_destination_metrics_keep_independent_hand_calculated_denominators(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(
        source,
        [
            _row("current", 1000, 2, route_length="100"),
            _row("retro", 2000, 1, route_length="200"),
            _row("forecast", 3000, 3, route_length=""),
            _row("current", "", 4, route_length="400"),
            _row("current", 9000, 0, route_length="900"),
        ],
    )

    routes, _ = build_clustering_routes(
        source, origin_fias="origin-a", destination_region="Region A"
    )

    route = routes[0]
    assert route.trip_count == 10
    assert route.weighted_route_length == pytest.approx(2000 / 7)
    assert route.weighted_price == pytest.approx(13000 / 6)
    assert route.weighted_rub_per_km == 10
    assert route.valid_route_length_trip_count == 7
    assert route.valid_price_trip_count == 6
    assert route.valid_rub_per_km_trip_count == 3


def test_destination_metrics_are_null_without_positive_metric_weight(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(
        source,
        [
            _row("current", "bad", 2, route_length="bad"),
            _row("current", 1000, 0, route_length="100"),
            _row("current", 1000, -3, route_length="100"),
        ],
    )

    routes, _ = build_clustering_routes(
        source, origin_fias="origin-a", destination_region="Region A"
    )

    route = routes[0]
    assert route.trip_count == 2
    assert route.weighted_route_length is None
    assert route.weighted_price is None
    assert route.weighted_rub_per_km is None
    assert route.valid_route_length_trip_count == 0
    assert route.valid_price_trip_count == 0
    assert route.valid_rub_per_km_trip_count == 0
    assert "invalid_units" in route.data_quality_flags
    assert "invalid_route_length" in route.data_quality_flags


def test_zero_and_negative_metric_values_do_not_become_values_or_weights(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(
        source,
        [
            _row("current", 0, 2, route_length="100"),
            _row("current", -10, 3, route_length="100"),
            _row("current", 100, 4, route_length="0"),
            _row("current", 100, 5, route_length="-2"),
        ],
    )

    routes, _ = build_clustering_routes(
        source, origin_fias="origin-a", destination_region="Region A"
    )

    route = routes[0]
    assert route.weighted_route_length == 100
    assert route.valid_route_length_trip_count == 5
    assert route.weighted_price == 100
    assert route.valid_price_trip_count == 9
    assert route.weighted_rub_per_km is None
    assert route.valid_rub_per_km_trip_count == 0


def test_destination_rows_are_sorted_by_fias_not_input_order(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(
        source,
        [
            _row("current", 1000, 1, destination="z-destination"),
            _row("current", 1000, 1, destination="a-destination"),
        ],
    )

    routes, _ = build_clustering_routes(
        source, origin_fias="origin-a", destination_region="Region A"
    )

    assert [route.destination_fias for route in routes] == [
        "a-destination",
        "z-destination",
    ]


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
