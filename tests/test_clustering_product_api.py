from __future__ import annotations

import csv
import json

import pytest

from backend.app import app
from backend.clustering_api import set_clustering_service
from backend.services.boundary_provider import BoundaryProvider
from backend.services.clustering_service import ClusteringRequest, ClusteringService
from ml.clustering.base import ClusterPoint
from ml.clustering.kmeans import KMeansClusterer
from ml.data.loader import PULSE_COLUMNS


def _row(
    destination: str,
    name: str,
    *,
    origin: str = "origin-1",
    origin_name: str = "Origin Town",
    region: str = "Region A",
    period: str = "current",
    price_type: str = "spot",
    price: str = "1000",
    trips: str = "20",
    vehicle: str = "tent",
    tonnage: str = "20",
) -> dict[str, str]:
    row = {column: "" for column in PULSE_COLUMNS}
    row.update(
        {
            "shipment_point_locality_fias_id": origin,
            "shipment_point_name_town": origin_name,
            "shipment_point_region": "Origin Region",
            "delivery_point_locality_fias_id": destination,
            "delivery_point_region_unified": region,
            "delivery_point_town": name,
            "period_id": "202608",
            "period_type": period,
            "bid_count": trips,
            "units": price,
            "price_type": price_type,
            "route_length": "100",
            "vehicle_body_type": vehicle,
            "tonnage_id": tonnage,
        }
    )
    return row


def _write_csv(path, rows) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture()
def product_files(tmp_path):
    source = tmp_path / "pulse.csv"
    cache = tmp_path / "coords.json"
    rows = [
        _row("a", "A", price="1000"),
        _row("b", "B", price="900"),
        _row("c", "C", price="5000", price_type="tender"),
        _row("d", "D", period="retro"),
        _row("economic-missing", "Economic Missing", price=""),
        _row("unresolved", "Unresolved", trips="3"),
        _row("other-origin", "Other Origin Destination", origin="origin-2"),
        _row("other-region", "Other Region Destination", region="Region B"),
    ]
    _write_csv(source, rows)
    cache.write_text(
        json.dumps(
            {
                "A::Region A": [55.00, 37.00],
                "B::Region A": [55.01, 37.01],
                "C::Region A": [55.02, 37.02],
                "D::Region A": [55.03, 37.03],
                "Economic Missing::Region A": [55.025, 37.025],
                "Other Origin Destination::Region A": [55.04, 37.04],
                "Other Region Destination::Region B": [56.0, 38.0],
            }
        ),
        encoding="utf-8",
    )
    return source, cache


@pytest.fixture()
def product_service(product_files):
    source, cache = product_files
    return ClusteringService(source, coordinate_cache_path=cache)


@pytest.fixture()
def product_client(product_service):
    set_clustering_service(product_service)
    app.config.update(TESTING=True)
    yield app.test_client()
    set_clustering_service(None)


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def _payload(**changes):
    payload = {
        "origin_fias": "origin-1",
        "destination_region": "Region A",
        "period_types": ["current"],
        "price_types": ["spot", "tender"],
        "mode": "geography",
        "parameters": {"k_mode": "manual", "n_clusters": 2},
    }
    payload.update(changes)
    return payload


def test_options_and_searchable_origin_catalog(product_client):
    options = product_client.get(
        "/api/clustering/options?origin_fias=origin-1&destination_region=Region%20A"
    )
    origins = product_client.get("/api/clustering/origins?q=origin&limit=1")

    assert options.status_code == 200
    payload = options.get_json()
    assert payload["ok"] is True
    assert payload["modes"] == [
        "geography",
        "geo_cost",
        "geo_volume",
        "bear_zones",
        "bear_volume_zones",
    ]
    assert payload["k"] == {
        "min": 2, "max": 20, "default": 5, "modes": ["auto", "manual"]
    }
    assert payload["bear_thresholds"]["zone_default"] == 0.35
    assert payload["bear_thresholds"]["singleton_default"] == 0.70
    assert payload["bear_thresholds"]["singleton_fixed"] is True
    assert payload["bear_volume_thresholds"] == payload["bear_thresholds"]
    assert payload["geo_cost_weights"]["presets"] == [
        {"geography": 0.8, "economics": 0.2},
        {"geography": 0.7, "economics": 0.3},
        {"geography": 0.6, "economics": 0.4},
    ]
    assert payload["geo_volume_weights"]["presets"] == [
        {"geography": 0.8, "volume": 0.2},
        {"geography": 0.7, "volume": 0.3},
        {"geography": 0.6, "volume": 0.4},
    ]
    assert payload["destination_regions"] == ["Region A", "Region B"]
    assert payload["facets"]["vehicle_types"] == [{"value": "tent", "count": 6}]
    assert origins.status_code == 200
    assert len(origins.get_json()) == 1
    assert set(origins.get_json()[0]) == {"fias_id", "name", "region", "trip_count"}


def test_run_returns_ui_contract_and_reports_unresolved(product_client):
    response = product_client.post("/api/clustering/run", json=_payload())
    result = response.get_json()

    assert response.status_code == 200
    assert set(result) >= {
        "analysis",
        "data_quality",
        "metrics",
        "points",
        "clusters",
        "outliers",
        "status",
    }
    assert result["analysis"]["mode"] == "geography"
    assert result["analysis"]["parameters"]["n_clusters"] == 2
    assert result["data_quality"]["locations_total"] == 5
    assert result["data_quality"]["coordinates_resolved"] == 4
    assert result["data_quality"]["coordinates_unresolved"] == 1
    assert result["data_quality"]["economic_valid_points"] == 3
    assert result["data_quality"]["economic_unavailable_points"] == 1
    assert set(result["data_quality"]) >= {
        "destination_points_total",
        "resolved_points",
        "unresolved_points",
        "point_coverage_pct",
        "trip_weight_coverage_pct",
        "trip_count_resolved",
        "source_row_count",
        "excluded_missing_fias",
        "contains_forecast",
        "mixed_price_segments",
        "mixed_vehicle_segments",
        "mixed_tonnage_segments",
    }
    unresolved = next(point for point in result["points"] if point["id"] == "unresolved")
    assert unresolved["lat"] is None
    assert unresolved["lon"] is None
    assert unresolved["cluster_id"] is None
    assert "zones" not in result


class CapturingClusterer:
    algorithm = "kmeans"

    def __init__(self) -> None:
        self.points: list[ClusterPoint] = []
        self.calls = 0
        self.delegate = KMeansClusterer()

    def fit(self, points, parameters):
        self.calls += 1
        self.points = points
        return self.delegate.fit(points, parameters)


def test_geography_only_ml_input_never_receives_price(product_files):
    source, cache = product_files
    clusterer = CapturingClusterer()
    service = ClusteringService(
        source,
        coordinate_cache_path=cache,
        clusterers={"geography": clusterer},
    )
    service.run(ClusteringRequest.from_payload(_payload()))

    assert clusterer.points
    assert all(point.weighted_price is None for point in clusterer.points)
    assert all(point.weighted_rub_per_km is None for point in clusterer.points)
    assert all(set(point.__slots__) >= {"id", "name", "region", "x", "y", "trip_count"} for point in clusterer.points)


def test_result_cache_reuses_repository_and_calculation(product_files):
    source, cache = product_files
    clusterer = CapturingClusterer()
    service = ClusteringService(
        source,
        coordinate_cache_path=cache,
        clusterers={"geography": clusterer},
    )
    request = ClusteringRequest.from_payload(_payload())

    first = service.run(request)
    second = service.run(request)

    assert first == second
    assert clusterer.calls == 1
    assert service.repository is not None
    assert service.repository.load_count == 1
    assert len(service._result_cache) == 1


@pytest.mark.parametrize(
    ("change", "expected_ids"),
    [
        ({"origin_fias": "origin-2"}, {"other-origin"}),
        ({"destination_region": "Region B"}, {"other-region"}),
        ({"period_types": ["retro"]}, {"d"}),
        ({"price_types": ["tender"]}, {"c"}),
    ],
)
def test_product_filters_restrict_the_dataset(product_service, change, expected_ids):
    request = ClusteringRequest.from_payload(
        _payload(parameters={"k_mode": "manual", "n_clusters": 2}, **change)
    )
    preview = product_service.preview(request)
    assert {point["id"] for point in preview["points"]} == expected_ids


def test_same_request_has_deterministic_assignments(product_service):
    request = ClusteringRequest.from_payload(_payload())
    first = product_service.run(request)
    second = product_service.run(request)

    first_assignments = {point["id"]: point["cluster_id"] for point in first["points"]}
    second_assignments = {point["id"]: point["cluster_id"] for point in second["points"]}
    assert first_assignments == second_assignments


@pytest.mark.parametrize(
    "mode",
    [
        "geography",
        "geo_cost",
        "geo_volume",
        "bear_zones",
        "bear_volume_zones",
    ],
)
def test_all_product_modes_use_one_canonical_contract(product_client, mode):
    parameters = {"k_mode": "manual", "n_clusters": 2}
    if mode == "geo_cost":
        parameters.update(geography_weight=0.70, economics_weight=0.30)
    elif mode == "geo_volume":
        parameters.update(geography_weight=0.70, volume_weight=0.30)
    elif mode == "bear_zones":
        parameters = {"bear_threshold": 0.35, "singleton_threshold": 0.70}
    elif mode == "bear_volume_zones":
        parameters = {"volume_threshold": 0.35, "singleton_threshold": 0.70}
    response = product_client.post(
        "/api/clustering/run",
        json=_payload(mode=mode, parameters=parameters),
    )
    result = response.get_json()

    assert response.status_code == 200
    assert result["analysis"]["mode"] == mode
    assert result["status"] in {"success", "no_bears"}
    assert "zones" not in result
    assert all("status" in point for point in result["points"])
    if mode in {"geo_cost", "bear_zones"}:
        assert result["regional_weighted_rub_per_km"] is not None
    if mode in {"geo_volume", "bear_volume_zones"}:
        assert result["metrics"]["regional_mean_trip_count"] > 0


def test_vehicle_and_tonnage_are_canonical_filters(product_service):
    request = ClusteringRequest.from_payload(
        _payload(vehicle_types=["missing"], tonnage_ids=["20"])
    )
    result = product_service.preview(request)

    assert result["points"] == []
    assert result["analysis"]["filters"]["vehicle_types"] == ["missing"]


@pytest.mark.parametrize(
    ("parameters", "code"),
    [
        ({"k_mode": "manual", "n_clusters": 1}, "INVALID_CLUSTER_COUNT"),
        ({"k_mode": "manual", "n_clusters": 21}, "INVALID_CLUSTER_COUNT"),
        ({"k_mode": "manual", "n_clusters": 2, "weight_mode": "price"}, "INVALID_MODE_PARAMETERS"),
        ({"k_mode": "manual", "n_clusters": 2, "auto": True}, "INVALID_MODE_PARAMETERS"),
    ],
)
def test_invalid_parameters_return_stable_code(product_client, parameters, code):
    response = product_client.post(
        "/api/clustering/run", json=_payload(parameters=parameters)
    )
    assert response.status_code == 400
    assert response.get_json()["code"] == code


def test_insufficient_points_is_a_clear_validation_response(product_client):
    response = product_client.post(
        "/api/clustering/run",
        json=_payload(
            period_types=["retro"],
            parameters={"k_mode": "manual", "n_clusters": 2},
        ),
    )
    assert response.status_code == 422
    assert response.get_json()["code"] == "INSUFFICIENT_POINTS"
    assert response.get_json()["error"]


def test_mode_presets_and_fixed_singleton_validation(product_client):
    valid = product_client.post(
        "/api/clustering/run",
        json=_payload(
            mode="geo_cost",
            parameters={
                "k_mode": "manual",
                "n_clusters": 2,
                "geography_weight": 0.6,
                "economics_weight": 0.4,
            },
        ),
    )
    bad_weight = product_client.post(
        "/api/clustering/run",
        json=_payload(
            mode="geo_cost",
            parameters={
                "k_mode": "manual",
                "n_clusters": 2,
                "geography_weight": 0.5,
                "economics_weight": 0.5,
            },
        ),
    )
    bad_singleton = product_client.post(
        "/api/clustering/run",
        json=_payload(
            mode="bear_zones",
            parameters={"bear_threshold": 0.35, "singleton_threshold": 0.8},
        ),
    )
    bad_bear_threshold = product_client.post(
        "/api/clustering/run",
        json=_payload(
            mode="bear_zones",
            parameters={"bear_threshold": 0.33, "singleton_threshold": 0.70},
        ),
    )
    bad_volume_weight = product_client.post(
        "/api/clustering/run",
        json=_payload(
            mode="geo_volume",
            parameters={
                "k_mode": "manual",
                "n_clusters": 2,
                "geography_weight": 0.5,
                "volume_weight": 0.5,
            },
        ),
    )
    bad_volume_threshold = product_client.post(
        "/api/clustering/run",
        json=_payload(
            mode="bear_volume_zones",
            parameters={"volume_threshold": 0.33, "singleton_threshold": 0.70},
        ),
    )

    assert valid.status_code == 200
    assert valid.get_json()["analysis"]["parameters"]["economics_weight"] == 0.4
    assert bad_weight.status_code == 400
    assert bad_weight.get_json()["code"] == "INVALID_MODE_PARAMETERS"
    assert bad_singleton.status_code == 400
    assert bad_singleton.get_json()["code"] == "INVALID_MODE_PARAMETERS"
    assert bad_bear_threshold.status_code == 400
    assert bad_bear_threshold.get_json()["code"] == "INVALID_MODE_PARAMETERS"
    assert bad_volume_weight.status_code == 400
    assert bad_volume_weight.get_json()["code"] == "INVALID_MODE_PARAMETERS"
    assert bad_volume_threshold.status_code == 400
    assert bad_volume_threshold.get_json()["code"] == "INVALID_MODE_PARAMETERS"


def test_request_id_is_echoed_for_success_and_validation_error(product_client):
    success = product_client.post(
        "/api/clustering/run",
        json=_payload(),
        headers={"X-Request-ID": "qa-clustering-42"},
    )
    invalid = product_client.post(
        "/api/clustering/run",
        json=_payload(parameters={"k_mode": "manual", "n_clusters": 1}),
    )

    assert success.headers["X-Request-ID"] == "qa-clustering-42"
    assert invalid.headers["X-Request-ID"]
    assert invalid.get_json()["code"] == "INVALID_CLUSTER_COUNT"


def test_geo_cost_returns_economic_unavailable_points(product_client):
    response = product_client.post(
        "/api/clustering/run",
        json=_payload(
            mode="geo_cost",
            parameters={
                "k_mode": "manual",
                "n_clusters": 2,
                "geography_weight": 0.7,
                "economics_weight": 0.3,
            },
        ),
    )

    assert response.status_code == 200
    point = next(
        item for item in response.get_json()["points"] if item["id"] == "economic-missing"
    )
    assert point["status"] == "economic_unavailable"
    assert point["cluster_id"] is None


def test_compare_uses_fixed_fact_only_contract(product_client):
    payload = _payload()
    payload.pop("mode")
    payload.pop("parameters")
    response = product_client.post("/api/clustering/compare", json=payload)
    result = response.get_json()

    assert response.status_code == 200
    assert result["winner"] is None
    assert set(result["results"]) == {
        "geography",
        "geo_cost",
        "geo_volume",
        "bear_zones",
        "bear_volume_zones",
    }
    assert result["results"]["geography"]["analysis"]["parameters"]["k_mode"] == "auto"
    assert result["results"]["geo_cost"]["analysis"]["parameters"]["economics_weight"] == 0.3
    assert result["results"]["geo_volume"]["analysis"]["parameters"]["volume_weight"] == 0.3
    assert result["results"]["bear_zones"]["analysis"]["parameters"]["bear_threshold"] == 0.35
    assert result["results"]["bear_volume_zones"]["analysis"]["parameters"]["volume_threshold"] == 0.35


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"origin_fias": "missing"}, "UNKNOWN_ORIGIN"),
        ({"destination_region": "missing"}, "UNKNOWN_DESTINATION_REGION"),
        ({"vehicle_types": ["missing"]}, "NO_DATA"),
    ],
)
def test_stable_scope_and_empty_error_codes(product_client, change, code):
    response = product_client.post("/api/clustering/run", json=_payload(**change))
    assert response.status_code == 422
    assert response.get_json()["code"] == code


def test_product_result_remains_points_only_when_boundary_exists(product_files, tmp_path):
    source, cache = product_files
    boundary_file = tmp_path / "boundaries.geojson"
    boundary_file.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "Region A"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [36.9, 54.9],
                                    [37.2, 54.9],
                                    [37.2, 55.2],
                                    [36.9, 55.2],
                                    [36.9, 54.9],
                                ]
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    service = ClusteringService(
        source,
        coordinate_cache_path=cache,
        boundary_provider=BoundaryProvider(boundary_file),
    )

    result = service.run(ClusteringRequest.from_payload(_payload()))

    assert "zones" not in result
    assert "territorial_metrics" not in result
    assert result["points"]


def test_legacy_map_endpoints_remain_available(client):
    assert client.get("/api/points").status_code == 200
    assert client.get(
        "/api/records?town=A&region=Region&type=shipment"
    ).status_code == 200
    assert client.get("/api/ml-cluster").status_code == 400
