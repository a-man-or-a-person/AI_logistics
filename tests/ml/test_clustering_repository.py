import csv
import json

import pytest

from ml.data.clustering_dataset import build_clustering_routes
from ml.data.clustering_repository import ClusteringRepository
from ml.data.loader import PULSE_COLUMNS


def _row(
    destination,
    name,
    *,
    period="current",
    period_id="202608",
    price="1000",
    trips="2",
    route_length="100",
    tech_load_ts="",
):
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": "origin-1",
            "shipment_point_name_town": "Origin Town",
            "shipment_point_region": "Origin Region",
            "delivery_point_locality_fias_id": destination,
            "delivery_point_region_unified": "Region A",
            "delivery_point_town": name,
            "period_id": period_id,
            "period_type": period,
            "bid_count": trips,
            "units": price,
            "price_type": "tender",
            "route_length": route_length,
            "vehicle_body_type": "tent",
            "tonnage_id": "7",
            "tech_load_ts": tech_load_ts,
        }
    )
    return row


def _write(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def test_product_repository_matches_research_aggregation(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(
        source,
        [
            _row("a", "A", price="1000", trips="2"),
            _row("a", "A", period="forecast", price="3000", trips="4"),
            _row("b", "B", price="2000", trips="3"),
        ],
    )
    repository = ClusteringRepository(source)

    product_routes, product_report = repository.aggregate(
        origin_fias="origin-1",
        destination_region="Region A",
        period_types={"current", "forecast"},
        price_types={"tender"},
        vehicle_types={"tent"},
        tonnage_ids={"7"},
    )
    research_routes, research_report = build_clustering_routes(
        source,
        origin_fias="origin-1",
        destination_region="Region A",
        period_types={"current", "forecast"},
        price_types={"tender"},
        vehicle_types={"tent"},
        tonnage_ids={"7"},
    )

    assert product_routes == research_routes
    assert product_report["filtered_source_rows"] == research_report["filtered_source_rows"]
    assert product_routes[0].weighted_price == pytest.approx(7000 / 3)
    assert product_routes[0].trip_count == 6
    assert repository.load_count == 1


def test_repository_options_and_fingerprint_invalidation(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(source, [_row("a", "A")])
    repository = ClusteringRepository(source)

    options = repository.options("origin-1", "Region A")
    assert options["origins"][0]["name"] == "Origin Town"
    assert options["facets"]["vehicle_types"] == [{"value": "tent", "count": 1}]
    assert repository.load_count == 1

    _write(source, [_row("a", "A"), _row("b", "B")])
    assert len(repository.options()["origins"]) == 1
    assert repository.load_count == 2


def test_repository_does_not_read_coordinate_cache(tmp_path):
    source = tmp_path / "pulse.csv"
    cache = tmp_path / "coords.json"
    _write(source, [_row("a", "A")])
    cache.write_text(json.dumps({"A::Region A": [1, 2]}), encoding="utf-8")
    before = cache.read_bytes()

    ClusteringRepository(source).options()

    assert cache.read_bytes() == before


def test_source_rows_preserve_warnings_and_have_stable_newest_first_order(tmp_path):
    source = tmp_path / "pulse.csv"
    _write(
        source,
        [
            _row("a", "A", period_id="bad", price="10"),
            _row("a", "A", period_id="202608", price="20"),
            _row("a", "A", period_id="202609", price="30", tech_load_ts="2026-09-01"),
            _row("a", "A", period_id="202609", price="40", tech_load_ts="2026-09-02"),
            _row("a", "A", period_id="202609", price="50", tech_load_ts="2026-09-02"),
            _row("a", "A", period_id="202609", price="70", tech_load_ts="broken"),
            _row("a", "A", period_id="202609", price="80"),
            _row("a", "A", period_id="", price="60", route_length="broken"),
        ],
    )
    repository = ClusteringRepository(source)

    rows = repository.source_rows(
        origin_fias="origin-1",
        destination_region="Region A",
        destination_fias="a",
        period_types={"current"},
        price_types={"tender"},
        vehicle_types={"tent"},
        tonnage_ids={"7"},
    )

    assert [row.price for row in rows] == [50, 40, 30, 80, 70, 20, 60, 10]
    assert rows[0].source_row_number > rows[1].source_row_number
    assert rows[-2].validation_errors == ("invalid_route_length",)
    assert rows[-1].validation_errors == ("invalid_period_id",)
    assert rows[4].validation_errors == ("invalid_tech_load_ts",)
