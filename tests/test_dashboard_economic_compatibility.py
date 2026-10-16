"""Independent constants for the approved presentation source; no semantic migration."""

import csv
import json

import pytest
from test_product_cluster_table import FixedClusterer, _request, _row

from backend.product_modes import default_product_mode_catalog
from backend.services.clustering_service import ClusteringService
from ml.data.loader import PULSE_COLUMNS


def _result(tmp_path, values):
    source, cache = tmp_path / "pulse.csv", tmp_path / "coords.json"
    with source.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(
            _row(destination, destination.upper(), price=price, route_length=route, trips=trips)
            for destination, price, route, trips in values
        )
    cache.write_text(json.dumps({"A::Region A": [55, 37], "B::Region A": [55.01, 37]}),
                     encoding="utf-8")
    return ClusteringService(
        source, coordinate_cache_path=cache,
        product_mode_catalog=default_product_mode_catalog(geography_clusterer=FixedClusterer()),
    ).run(_request())


def test_partial_machine_coverage_preserves_both_canonical_and_legacy_means(tmp_path):
    result = _result(tmp_path, [
        ("a", "100", "10", "10"), ("a", "", "", "90"),
        ("b", "300", "10", "10"),
    ])
    row = result["cluster_table"]["rows"][0]
    legacy = result["clusters"][0]
    assert row["point_ids"] == legacy["point_ids"] == ["a", "b"]
    assert (row["point_count"], row["trip_count"]) == (2, 110)
    assert row["weighted_route_length"] == 10
    assert row["price"] == {"min": 100, "median": 200, "weighted": 200, "max": 300}
    assert row["rub_per_km"] == {"min": 10, "median": 20, "weighted": 20, "max": 30}
    assert legacy["weighted_price"] == pytest.approx(118.18181818181819)
    assert legacy["weighted_rub_per_km"] == pytest.approx(11.818181818181818)
    expected = {"valid_points": 2, "total_points": 2,
                "valid_trip_count": 20, "total_trip_count": 110}
    assert row["economic_coverage"] == expected
    assert row["coverage"] == dict.fromkeys(["route_length", "price", "rub_per_km"], expected)


@pytest.mark.parametrize(("values", "price", "route", "rate", "valid", "total"), [
    ([("a", "100", "10", "1"), ("b", "300", "30", "3")], 250, 25, 10, (4, 4, 4), 4),
    ([("a", "100", "10", "1"), ("b", "300", "20", "1")], 200, 15, 12.5, (2, 2, 2), 2),
    ([("a", "100", "10", "1"), ("b", "300", "", "3")], 250, 10, 10, (4, 1, 1), 4),
    ([("a", "", "", "2"), ("b", "bad", "bad", "3")], None, None, None, (0, 0, 0), 5),
    ([("a", "0", "-10", "2"), ("b", "-300", "0", "3")], None, None, None, (0, 0, 0), 5),
    ([("a", "100", "10", "0"), ("b", "300", "20", "-3"),
      ("a", "100", "10", "bad")], None, None, None, (0, 0, 0), 0),
])
def test_metric_valid_denominators_and_unavailable_values(
    tmp_path, values, price, route, rate, valid, total,
):
    row = _result(tmp_path, values)["cluster_table"]["rows"][0]
    assert row["price"]["weighted"] == price
    assert row["weighted_route_length"] == route
    assert row["rub_per_km"]["weighted"] == rate
    assert row["trip_count"] == total
    assert tuple(row["coverage"][metric]["valid_trip_count"]
                 for metric in ["price", "route_length", "rub_per_km"]) == valid
    assert all(item["total_trip_count"] == total for item in row["coverage"].values())
    if rate == 12.5:
        assert row["price"]["weighted"] / row["weighted_route_length"] == pytest.approx(13.333333333333334)
    if total == 0:
        assert row["trip_share"] is None
