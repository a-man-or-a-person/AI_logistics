from __future__ import annotations

import csv
import json

import pytest

from backend.app import app
from backend.clustering_api import set_clustering_service
from backend.product_modes import default_product_mode_catalog
from backend.services.clustering_service import ClusteringRequest, ClusteringService
from ml.clustering.base import summarize_assignments
from ml.data.loader import PULSE_COLUMNS


def _row(
    destination: str,
    name: str,
    *,
    price: str,
    route_length: str,
    trips: str,
) -> dict[str, str]:
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": "origin-1",
            "shipment_point_name_town": "Origin",
            "shipment_point_region": "Origin Region",
            "delivery_point_locality_fias_id": destination,
            "delivery_point_region_unified": "Region A",
            "delivery_point_town": name,
            "period_id": "202608",
            "period_type": "current",
            "bid_count": trips,
            "units": price,
            "price_type": "spot",
            "route_length": route_length,
            "vehicle_body_type": "tent",
            "tonnage_id": "20",
        }
    )
    return row


class FixedClusterer:
    algorithm = "fixed"

    def __init__(self) -> None:
        self.calls = 0

    def fit(self, points, parameters):
        self.calls += 1
        assignments = {
            point.id: 0 if point.id in {"a", "b", "c", "e"} else 1 for point in points
        }
        return summarize_assignments(
            points,
            assignments,
            algorithm=self.algorithm,
            parameters={key: value for key, value in parameters.items() if key != "spatial_graph"},
        )


@pytest.fixture()
def table_service(tmp_path):
    source = tmp_path / "pulse.csv"
    cache = tmp_path / "coords.json"
    rows = [
        _row("a", "A", price="1000", route_length="100", trips="2"),
        _row("a", "A", price="2000", route_length="200", trips="1"),
        _row("b", "B", price="3000", route_length="100", trips="1"),
        _row("c", "C", price="5000", route_length="", trips="4"),
        _row("d", "D", price="", route_length="200", trips="2"),
        _row("e", "E", price="1000.05", route_length="100", trips="1"),
    ]
    with source.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    cache.write_text(
        json.dumps(
            {
                "A::Region A": [55.00, 37.00],
                "B::Region A": [55.01, 37.01],
                "C::Region A": [55.02, 37.02],
                "D::Region A": [55.03, 37.03],
                "E::Region A": [55.04, 37.04],
            }
        ),
        encoding="utf-8",
    )
    clusterer = FixedClusterer()
    catalog = default_product_mode_catalog(geography_clusterer=clusterer)
    service = ClusteringService(
        source,
        coordinate_cache_path=cache,
        product_mode_catalog=catalog,
    )
    set_clustering_service(service)
    app.config.update(TESTING=True)
    yield service, clusterer, app.test_client(), cache
    set_clustering_service(None)


def _request(mode="geography", parameters=None):
    return ClusteringRequest.from_payload(_payload(mode, parameters))


def _payload(mode="geography", parameters=None):
    return {
        "origin_fias": "origin-1",
        "destination_region": "Region A",
        "period_types": ["current"],
        "price_types": ["spot"],
        "mode": mode,
        "parameters": parameters or {"k_mode": "manual", "n_clusters": 2},
    }


def test_run_exposes_hand_calculated_cluster_table_from_cached_assignments(table_service):
    _, clusterer, client, _ = table_service

    first_response = client.post("/api/clustering/run", json=_payload())
    second_response = client.post("/api/clustering/run", json=_payload())
    first = first_response.get_json()
    second = second_response.get_json()

    assert first_response.status_code == second_response.status_code == 200
    assert first == second
    assert clusterer.calls == 1
    assert len(first["data_snapshot"]) == 64
    assert first["cluster_table"]["supported"] is True
    assert first["cluster_table"]["period_types"] == ["current"]
    assert first["cluster_table"]["methodology"] == {
        "version": "product_cluster_table_v1",
        "distributions": "unweighted_destination_points",
        "weighted_values": "metric_valid_trip_count",
    }

    assert [row["cluster_id"] for row in first["cluster_table"]["rows"]] == [0, 1]
    row = first["cluster_table"]["rows"][0]
    assert row["point_ids"] == ["a", "b", "c", "e"]
    assert row["point_count"] == 4
    assert row["trip_count"] == 9
    assert row["trip_share"] == pytest.approx(9 / 11)
    assert row["weighted_route_length"] == pytest.approx(120)
    assert row["price"] == pytest.approx(
        {
            "min": 1000.05,
            "median": (4000 / 3 + 3000) / 2,
            "weighted": 28000.05 / 9,
            "max": 5000,
        }
    )
    assert row["rub_per_km"] == pytest.approx(
        {"min": 10, "median": 10.0005, "weighted": 70.0005 / 5, "max": 30}
    )
    assert row["coverage"] == {
        "route_length": {
            "valid_points": 3,
            "total_points": 4,
            "valid_trip_count": 5,
            "total_trip_count": 9,
        },
        "price": {
            "valid_points": 4,
            "total_points": 4,
            "valid_trip_count": 9,
            "total_trip_count": 9,
        },
        "rub_per_km": {
            "valid_points": 3,
            "total_points": 4,
            "valid_trip_count": 5,
            "total_trip_count": 9,
        },
    }
    assert row["economic_coverage"] == {
        "valid_points": 3,
        "total_points": 4,
        "valid_trip_count": 5,
        "total_trip_count": 9,
    }

    missing = first["cluster_table"]["rows"][1]
    assert missing["weighted_route_length"] == 200
    assert missing["price"] == {"min": None, "median": None, "weighted": None, "max": None}
    assert missing["rub_per_km"] == {
        "min": None,
        "median": None,
        "weighted": None,
        "max": None,
    }
    point = next(point for point in first["points"] if point["id"] == "a")
    assert point["weighted_route_length"] == pytest.approx(400 / 3)
    assert point["valid_route_length_trip_count"] == 3
    assert point["valid_price_trip_count"] == 3
    assert point["valid_rub_per_km_trip_count"] == 3
    assert point["active_period_count"] == 1
    assert point["period_types"] == ["current"]
    rounding_boundary = next(point for point in first["points"] if point["id"] == "e")
    assert rounding_boundary["weighted_price"] == 1000.05
    assert rounding_boundary["weighted_rub_per_km"] == pytest.approx(10.0005)


@pytest.mark.parametrize(
    ("mode", "parameters", "expected_point_ids"),
    [
        (
            "geography",
            {"k_mode": "manual", "n_clusters": 2},
            {"a", "b", "c", "d", "e"},
        ),
        (
            "geo_cost",
            {
                "k_mode": "manual",
                "n_clusters": 2,
                "geography_weight": 0.7,
                "economics_weight": 0.3,
            },
            {"a", "b"},
        ),
        (
            "geo_volume",
            {
                "k_mode": "manual",
                "n_clusters": 2,
                "geography_weight": 0.7,
                "volume_weight": 0.3,
            },
            {"a", "b", "c", "d", "e"},
        ),
    ],
)
def test_partition_mode_table_uses_exact_result_membership(
    table_service, mode, parameters, expected_point_ids
):
    service, _, _, _ = table_service

    result = service.run(_request(mode, parameters))

    table = result["cluster_table"]
    assert table["supported"] is True
    assert {point_id for row in table["rows"] for point_id in row["point_ids"]} == (
        expected_point_ids
    )
    assert {row["cluster_id"]: row["point_ids"] for row in table["rows"]} == {
        cluster["cluster_id"]: cluster["point_ids"] for cluster in result["clusters"]
    }
    assert table["rows"] == sorted(
        table["rows"], key=lambda row: (-row["trip_count"], row["cluster_id"])
    )


@pytest.mark.parametrize(
    ("mode", "parameters"),
    [
        ("bear_zones", {"bear_threshold": 0.35, "singleton_threshold": 0.7}),
        (
            "bear_volume_zones",
            {"volume_threshold": 0.35, "singleton_threshold": 0.7},
        ),
    ],
)
def test_bear_results_explicitly_leave_cluster_table_unsupported(
    table_service, mode, parameters
):
    service, _, _, _ = table_service

    result = service.run(_request(mode, parameters))

    assert result["cluster_table"] == {"supported": False}


def test_equivalent_filter_order_reuses_the_same_table_result(table_service):
    service, clusterer, _, _ = table_service
    first_payload = {
        "origin_fias": "origin-1",
        "destination_region": "Region A",
        "period_types": ["current", "retro"],
        "price_types": ["spot", "tender"],
        "mode": "geography",
        "parameters": {"k_mode": "manual", "n_clusters": 2},
    }
    second_payload = {
        **first_payload,
        "period_types": ["retro", "current"],
        "price_types": ["tender", "spot"],
    }

    first = service.run(ClusteringRequest.from_payload(first_payload))
    second = service.run(ClusteringRequest.from_payload(second_payload))

    assert first == second
    assert clusterer.calls == 1


def test_snapshot_change_invalidates_the_cached_table_result(table_service):
    service, clusterer, _, cache = table_service
    first = service.run(_request())
    coordinates = json.loads(cache.read_text(encoding="utf-8"))
    coordinates["A::Region A"] = [55.001, 37.001]
    cache.write_text(json.dumps(coordinates), encoding="utf-8")

    second = service.run(_request())

    assert first["data_snapshot"] != second["data_snapshot"]
    assert clusterer.calls == 2


def test_zero_machine_denominator_returns_null_share_and_stable_cluster_order(tmp_path):
    source = tmp_path / "zero.csv"
    cache = tmp_path / "zero-coords.json"
    with source.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(
            [
                _row("a", "A", price="1000", route_length="100", trips="0"),
                _row("d", "D", price="1000", route_length="100", trips="0"),
            ]
        )
    cache.write_text(
        json.dumps({"A::Region A": [55.0, 37.0], "D::Region A": [55.01, 37.01]}),
        encoding="utf-8",
    )
    clusterer = FixedClusterer()
    service = ClusteringService(
        source,
        coordinate_cache_path=cache,
        product_mode_catalog=default_product_mode_catalog(geography_clusterer=clusterer),
    )

    rows = service.run(_request())["cluster_table"]["rows"]

    assert [row["cluster_id"] for row in rows] == [0, 1]
    assert [row["trip_share"] for row in rows] == [None, None]
    assert all(row["weighted_route_length"] is None for row in rows)
