import csv
import json

import pytest

from backend.app import app
from backend.clustering_api import set_clustering_service
from ml.clustering.service import ClusteringRequest, ProductClusteringService
from ml.data.clustering_repository import ClusteringRepository
from ml.data.loader import PULSE_COLUMNS


def _row(
    destination,
    name,
    *,
    price="1000",
    distance="100",
    trips="20",
    period="current",
    price_type="tender",
    vehicle="tent",
    tonnage="7",
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
            "period_id": "202608",
            "period_type": period,
            "bid_count": trips,
            "units": price,
            "price_type": price_type,
            "route_length": distance,
            "vehicle_body_type": vehicle,
            "tonnage_id": tonnage,
        }
    )
    return row


def _write(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture()
def product_service(tmp_path):
    source = tmp_path / "pulse.csv"
    cache = tmp_path / "coords.json"
    rows = [
        _row("low-a", "Low A"),
        _row("low-b", "Low B"),
        _row("high-a", "High A", price="3000", trips="1"),
        _row("high-b", "High B", price="3000", trips="1"),
        _row("candidate", "Candidate", price="1800", trips="1", period="forecast"),
        _row("no-econ", "No Econ", price="", trips="2", price_type="spot", vehicle="box", tonnage="10"),
        _row("unresolved", "Unresolved", trips="3"),
    ]
    _write(source, rows)
    coordinates = {
        "Low A::Region A": [55.00, 37.00],
        "Low B::Region A": [55.01, 37.01],
        "High A::Region A": [55.02, 37.02],
        "High B::Region A": [55.03, 37.03],
        "Candidate::Region A": [57.00, 40.00],
        "No Econ::Region A": [55.04, 37.04],
    }
    cache.write_text(json.dumps(coordinates), encoding="utf-8")
    service = ProductClusteringService(
        ClusteringRepository(source), coordinate_cache_path=cache
    )
    service.fixture_source = source
    service.fixture_cache = cache
    return service


@pytest.fixture()
def product_client(product_service):
    set_clustering_service(product_service)
    app.config.update(TESTING=True)
    yield app.test_client()
    set_clustering_service(None)


def _payload(mode="geography", *, periods=None, parameters=None):
    return {
        "origin_fias": "origin-1",
        "destination_region": "Region A",
        "mode": mode,
        "filters": {
            "period_types": periods or ["current", "forecast"],
            "price_types": ["tender", "spot"],
            "vehicle_types": ["tent", "box"],
            "tonnage_ids": ["7", "10"],
        },
        "parameters": parameters or {"k_mode": "auto"},
    }


def test_options_are_contextual_and_expose_ui_schema(product_client):
    response = product_client.get(
        "/api/clustering/options?origin_fias=origin-1&destination_region=Region%20A"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["modes"]["bear_zones"]["uses_k"] is False
    assert payload["destination_regions"] == ["Region A"]
    assert {item["value"] for item in payload["facets"]["period_types"]} == {
        "current",
        "forecast",
    }
    assert payload["defaults"]["coordinate_policy"] == "accepted_existing_cache_v1"


def test_geography_endpoint_and_product_contract(product_client):
    response = product_client.post("/api/clustering/run", json=_payload())
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["mode"] == "geography"
    assert payload["parameters"]["selected_k"] <= 20
    assert all(cluster["connected"] for cluster in payload["clusters"])
    assert payload["data_quality"]["coordinate_policy"] == "accepted_existing_cache_v1"
    assert payload["data_quality"]["unresolved_points"] == 1
    assert "incomplete_coordinate_coverage" in payload["warnings"]
    assert "contains_forecast" in payload["warnings"]
    assert any(point["status"] == "unresolved" for point in payload["points"])


def test_geography_manual_k(product_client):
    response = product_client.post(
        "/api/clustering/run",
        json=_payload(parameters={"k_mode": "manual", "n_clusters": 2}),
    )
    assert response.status_code == 200
    assert response.get_json()["parameters"]["selected_k"] == 2


def test_geo_cost_default_and_missing_economics_are_reported(product_client):
    response = product_client.post(
        "/api/clustering/run",
        json=_payload("geo_cost", parameters={"k_mode": "auto"}),
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["parameters"]["geography_weight"] == 0.7
    assert payload["parameters"]["economics_weight"] == 0.3
    assert "economic_points_excluded" in payload["warnings"]
    excluded = next(point for point in payload["points"] if point["id"] == "no-econ")
    assert excluded["status"] == "economic_unavailable"
    assert all(cluster["connected"] for cluster in payload["clusters"])


def test_bear_has_no_trip_gate_and_candidate_is_visible(product_client):
    response = product_client.post(
        "/api/clustering/run",
        json=_payload(
            "bear_zones",
            parameters={"bear_threshold_pct": 35, "singleton_threshold_pct": 70},
        ),
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert "min_trip_count" not in payload["parameters"]
    assert any(
        cluster["trip_count"] in {1, 2}
        for cluster in payload["clusters"]
        if cluster["cluster_type"] in {"bear_zone", "expensive_singleton"}
    )
    candidate = next(point for point in payload["points"] if point["id"] == "candidate")
    assert candidate["status"] == "bear_candidate"


def test_bear_rejects_k(product_client):
    response = product_client.post(
        "/api/clustering/run",
        json=_payload("bear_zones", parameters={"n_clusters": 3}),
    )
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({**_payload(), "mode": "unknown"}, 400),
        ({**_payload(), "filters": {"period_types": []}}, 400),
        (_payload(parameters={"k_mode": "manual", "n_clusters": 100}), 400),
        (
            _payload(
                "bear_zones",
                parameters={"bear_threshold_pct": -1, "singleton_threshold_pct": 70},
            ),
            400,
        ),
    ],
)
def test_request_validation(product_client, payload, status):
    response = product_client.post("/api/clustering/run", json=payload)
    assert response.status_code == status
    assert response.get_json()["ok"] is False


def test_unknown_origin_and_region(product_client):
    unknown_origin = _payload()
    unknown_origin["origin_fias"] = "missing"
    origin_response = product_client.post("/api/clustering/run", json=unknown_origin)
    unknown_region = _payload()
    unknown_region["destination_region"] = "Missing"
    region_response = product_client.post("/api/clustering/run", json=unknown_region)

    assert origin_response.status_code == 422
    assert origin_response.get_json()["code"] == "UNKNOWN_ORIGIN"
    assert region_response.status_code == 422
    assert region_response.get_json()["code"] == "UNKNOWN_DESTINATION_REGION"


def test_same_request_hits_result_cache(product_service):
    request = ClusteringRequest.from_payload(_payload())
    first = product_service.run(request)
    second = product_service.run(request)

    assert first["cache"]["result_hit"] is False
    assert second["cache"]["result_hit"] is True
    assert product_service.repository.load_count == 1


def test_changed_dataset_and_coordinate_cache_invalidate_result(product_service):
    request = ClusteringRequest.from_payload(_payload())
    product_service.run(request)
    source = product_service.fixture_source
    cache = product_service.fixture_cache

    with source.open("a", encoding="utf-8") as stream:
        stream.write("\n")
    after_dataset = product_service.run(request)
    cache.write_text(cache.read_text(encoding="utf-8") + " ", encoding="utf-8")
    after_coordinates = product_service.run(request)

    assert after_dataset["cache"]["result_hit"] is False
    assert after_coordinates["cache"]["result_hit"] is False
    assert product_service.repository.load_count == 2


def test_strict_coordinates_never_modify_cache_or_use_region_center(product_service):
    before = product_service.fixture_cache.read_bytes()
    result = product_service.run(ClusteringRequest.from_payload(_payload()))

    unresolved = next(point for point in result["points"] if point["id"] == "unresolved")
    assert unresolved["latitude"] is None
    assert unresolved["longitude"] is None
    assert product_service.fixture_cache.read_bytes() == before


def test_compare_returns_no_winner(product_client):
    payload = _payload()
    payload.pop("mode")
    response = product_client.post("/api/clustering/compare", json=payload)
    result = response.get_json()

    assert response.status_code == 200
    assert result["winner"] is None
    assert {row["mode"] for row in result["comparison"]} == {
        "geography",
        "geo_cost",
        "bear_zones",
    }
