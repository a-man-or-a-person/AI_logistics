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
        "algorithm": "kmeans",
        "parameters": {"n_clusters": 2, "weight_mode": "none"},
    }
    payload.update(changes)
    return payload


def test_options_and_searchable_origin_catalog(product_client):
    options = product_client.get("/api/clustering/options?origin_fias=origin-1")
    origins = product_client.get("/api/clustering/origins?q=origin&limit=1")

    assert options.status_code == 200
    assert options.get_json() == {
        "ok": True,
        "source": "pulse",
        "algorithms": ["kmeans"],
        "weight_modes": ["none", "trip_count"],
        "period_types": ["retro", "current", "forecast"],
        "price_types": ["spot", "tender"],
        "destination_regions": ["Region A", "Region B"],
    }
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
        "territorial_metrics",
        "points",
        "clusters",
        "zones",
    }
    assert result["analysis"]["algorithm"] == "kmeans"
    assert result["analysis"]["parameters"] == {"n_clusters": 2, "weight_mode": "none"}
    assert result["data_quality"]["locations_total"] == 4
    assert result["data_quality"]["coordinates_resolved"] == 3
    assert result["data_quality"]["coordinates_unresolved"] == 1
    unresolved = next(point for point in result["points"] if point["id"] == "unresolved")
    assert unresolved["lat"] is None
    assert unresolved["lon"] is None
    assert unresolved["cluster_id"] is None
    assert result["zones"] == {
        "available": False,
        "status": "boundary_unavailable",
        "geojson": None,
    }
    assert result["territorial_metrics"] is None


class CapturingClusterer:
    algorithm = "kmeans"

    def __init__(self) -> None:
        self.points: list[ClusterPoint] = []
        self.delegate = KMeansClusterer()

    def fit(self, points, parameters):
        self.points = points
        return self.delegate.fit(points, parameters)


def test_geography_only_ml_input_never_receives_price(product_files):
    source, cache = product_files
    clusterer = CapturingClusterer()
    service = ClusteringService(
        source,
        coordinate_cache_path=cache,
        clusterers={"kmeans": clusterer},
    )
    service.run(ClusteringRequest.from_payload(_payload()))

    assert clusterer.points
    assert all(point.weighted_price is None for point in clusterer.points)
    assert all(point.weighted_rub_per_km is None for point in clusterer.points)
    assert all(set(point.__slots__) >= {"id", "name", "region", "x", "y", "trip_count"} for point in clusterer.points)


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
        _payload(parameters={"n_clusters": 2, "weight_mode": "none"}, **change)
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
    "parameters",
    [
        {"n_clusters": 1, "weight_mode": "none"},
        {"n_clusters": 11, "weight_mode": "none"},
        {"n_clusters": 2, "weight_mode": "price"},
        {"n_clusters": 2, "weight_mode": "none", "auto": True},
    ],
)
def test_invalid_parameters_return_400(product_client, parameters):
    response = product_client.post(
        "/api/clustering/run", json=_payload(parameters=parameters)
    )
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_REQUEST"


def test_insufficient_points_is_a_clear_validation_response(product_client):
    response = product_client.post(
        "/api/clustering/run",
        json=_payload(
            period_types=["retro"],
            parameters={"n_clusters": 2, "weight_mode": "none"},
        ),
    )
    assert response.status_code == 422
    assert response.get_json()["code"] == "INSUFFICIENT_POINTS"
    assert "Доступно: 1" in response.get_json()["error"]


def test_boundary_available_uses_territorialize(product_files, tmp_path):
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

    assert result["zones"]["available"] is True
    assert result["zones"]["status"] == "available"
    assert result["zones"]["geojson"]["features"]
    assert result["territorial_metrics"]["coverage_pct"] == 100
    assert result["territorial_metrics"]["overlap_pct"] == 0


def test_legacy_map_endpoints_remain_available(client):
    assert client.get("/api/points").status_code == 200
    assert client.get(
        "/api/records?town=A&region=Region&type=shipment"
    ).status_code == 200
