from __future__ import annotations

import csv
import json

import pytest

from backend.app import app
from backend.clustering_api import set_clustering_service
from backend.product_modes import default_product_mode_catalog
from backend.services.boundary_provider import BoundaryProvider
from backend.services.clustering_service import ClusteringRequest, ClusteringService
from ml.clustering.base import ClusterPoint
from ml.clustering.bear_volume_zones import BearVolumeZoneDetector
from ml.clustering.bear_zones import BearZoneDetector
from ml.clustering.geo_cost import GeoCostClusterer
from ml.clustering.geo_volume import GeoVolumeClusterer
from ml.clustering.geographic import GeographicClusterer
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
def mode_eligibility_files(tmp_path):
    source = tmp_path / "eligibility-pulse.csv"
    cache = tmp_path / "eligibility-coords.json"
    rows = [
        _row("a", "A", price="1000", trips="20"),
        _row("b", "B", price="1100", trips="20"),
        _row("c", "C", price="1200", trips="20"),
        _row("economic-missing", "Economic Missing", price="", trips="20"),
        _row("zero-volume", "Zero Volume", price="1300", trips="0"),
        _row("unresolved", "Unresolved", price="1400", trips="20"),
    ]
    _write_csv(source, rows)
    cache.write_text(
        json.dumps(
            {
                "A::Region A": [55.00, 37.00],
                "B::Region A": [55.01, 37.01],
                "C::Region A": [55.02, 37.02],
                "Economic Missing::Region A": [55.03, 37.03],
                "Zero Volume::Region A": [55.04, 37.04],
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
def product_client_factory():
    def factory(source, cache, **service_kwargs):
        service = ClusteringService(
            source,
            coordinate_cache_path=cache,
            **service_kwargs,
        )
        set_clustering_service(service)
        app.config.update(TESTING=True)
        return app.test_client()

    yield factory
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
    assert payload["k"] == {"min": 2, "max": 20, "default": 5, "modes": ["auto", "manual"]}
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
    assert payload["geo_cost_weights"]["default"] == {
        "geography": 0.7,
        "economics": 0.3,
    }
    assert payload["geo_volume_weights"]["default"] == {
        "geography": 0.7,
        "volume": 0.3,
    }
    assert payload["bear_thresholds"]["zone_options"] == [
        0.2,
        0.25,
        0.3,
        0.35,
        0.4,
        0.5,
    ]
    assert payload["defaults"] == {
        "period_types": ["current"],
        "price_types": ["spot"],
        "mode": "geography",
        "k_mode": "auto",
    }
    assert payload["destination_regions"] == ["Region A", "Region B"]
    assert payload["facets"]["vehicle_types"] == [{"value": "tent", "count": 6}]
    assert origins.status_code == 200
    assert len(origins.get_json()) == 1
    assert set(origins.get_json()[0]) == {"fias_id", "name", "region", "trip_count"}


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("geography", {"k_mode": "auto", "n_clusters": "auto"}),
        (
            "geo_cost",
            {
                "k_mode": "auto",
                "n_clusters": "auto",
                "geography_weight": 0.7,
                "economics_weight": 0.3,
            },
        ),
        (
            "geo_volume",
            {
                "k_mode": "auto",
                "n_clusters": "auto",
                "geography_weight": 0.7,
                "volume_weight": 0.3,
            },
        ),
        (
            "bear_zones",
            {"bear_threshold": 0.35, "singleton_threshold": 0.7},
        ),
        (
            "bear_volume_zones",
            {"volume_threshold": 0.35, "singleton_threshold": 0.7},
        ),
    ],
)
def test_preview_normalizes_each_mode_default(product_client, mode, expected):
    payload = _payload(mode=mode)
    payload.pop("parameters")

    response = product_client.post("/api/clustering/preview", json=payload)

    assert response.status_code == 200
    assert response.get_json()["analysis"]["parameters"] == expected


@pytest.mark.parametrize(
    ("change", "code", "message"),
    [
        (
            {"mode": "unknown"},
            "INVALID_REQUEST",
            "Неподдерживаемый mode: unknown.",
        ),
        (
            {"parameters": []},
            "INVALID_REQUEST",
            "parameters должен быть объектом.",
        ),
    ],
)
def test_mode_request_shape_has_stable_error_envelope(product_client, change, code, message):
    response = product_client.post("/api/clustering/run", json=_payload(**change))

    assert response.status_code == 400
    assert response.get_json() == {"ok": False, "code": code, "error": message}


def test_run_returns_ui_contract_and_reports_unresolved(product_client):
    response = product_client.post("/api/clustering/run", json=_payload())
    result = response.get_json()

    assert response.status_code == 200
    assert set(result) == {
        "ok",
        "analysis",
        "contains_forecast",
        "data_quality",
        "warnings",
        "metrics",
        "graph_metrics",
        "regional_stats",
        "regional_economics",
        "regional_volume",
        "regional_weighted_rub_per_km",
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


class RecordingClusterer:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.algorithm = delegate.algorithm
        self.calls: list[tuple[tuple[str, ...], dict, object]] = []

    def fit(self, points, parameters):
        self.calls.append(
            (
                tuple(point.id for point in points),
                {key: value for key, value in parameters.items() if key != "spatial_graph"},
                parameters["spatial_graph"],
            )
        )
        return self.delegate.fit(points, parameters)


class ConnectivityViolatingClusterer:
    algorithm = "connectivity_probe"

    def fit(self, points, parameters):
        raise AssertionError("characterized connectivity violation")


class TrackingProductModeCatalog:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.selections: list[str] = []
        self.operations: list[str] = []

    def select(self, mode_id, parameters):
        self.selections.append(mode_id)
        return self.delegate.select(mode_id, parameters)

    def evaluate(self, selection, dataset, operation):
        self.operations.append(operation)
        return self.delegate.evaluate(selection, dataset, operation)


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
    assert all(
        set(point.__slots__) >= {"id", "name", "region", "x", "y", "trip_count"}
        for point in clusterer.points
    )


def test_partition_modes_route_through_catalog_while_bear_modes_stay_on_old_path(product_files):
    source, cache = product_files
    service = ClusteringService(source, coordinate_cache_path=cache)
    catalog = TrackingProductModeCatalog(
        default_product_mode_catalog(
            geography_clusterer=service.clusterers["geography"],
            geo_cost_clusterer=service.clusterers["geo_cost"],
            geo_volume_clusterer=service.clusterers["geo_volume"],
        )
    )
    service.product_mode_catalog = catalog
    parameters = {
        "geography": {"k_mode": "manual", "n_clusters": 2},
        "geo_cost": {
            "k_mode": "manual",
            "n_clusters": 2,
            "geography_weight": 0.7,
            "economics_weight": 0.3,
        },
        "geo_volume": {
            "k_mode": "manual",
            "n_clusters": 2,
            "geography_weight": 0.7,
            "volume_weight": 0.3,
        },
    }

    for mode, mode_parameters in parameters.items():
        request = ClusteringRequest.from_payload(
            _payload(mode=mode, parameters=mode_parameters),
            product_mode_catalog=catalog,
        )
        service.preview(request)
        service.run(request)
    for mode, mode_parameters in {
        "bear_zones": {"bear_threshold": 0.35, "singleton_threshold": 0.7},
        "bear_volume_zones": {"volume_threshold": 0.35, "singleton_threshold": 0.7},
    }.items():
        request = ClusteringRequest.from_payload(
            _payload(mode=mode, parameters=mode_parameters),
            product_mode_catalog=catalog,
        )
        service.preview(request)
        service.run(request)

    assert catalog.selections == ["geography", "geo_cost", "geo_volume"]
    assert catalog.operations == ["preview", "run"] * 3


def test_geography_adapter_path_matches_legacy_geography_product_output(product_files):
    source, cache = product_files
    service = ClusteringService(source, coordinate_cache_path=cache)
    request = ClusteringRequest.from_payload(_payload())
    locations, report = service._locations(request)
    projection = service._projection(locations)
    legacy_points = service._ml_input(locations, projection, include_economics=False)
    graph, _ = service._spatial_graph(legacy_points)
    legacy_result = GeographicClusterer().fit(
        legacy_points,
        {
            "spatial_graph": graph,
            "n_clusters": request.n_clusters,
            "k_min": 2,
            "k_max": 20,
        },
    )
    legacy_output = service._result_json(request, locations, report, legacy_result, "success")

    adapter_output = service.run(request)

    assert request.parameters() == {
        "k_mode": "manual",
        "n_clusters": 2,
    }
    assert adapter_output == legacy_output


@pytest.mark.parametrize(
    ("mode", "clusterer_factory", "parameters"),
    [
        (
            "geo_cost",
            GeoCostClusterer,
            {
                "k_mode": "manual",
                "n_clusters": 2,
                "geography_weight": 0.7,
                "economics_weight": 0.3,
            },
        ),
        (
            "geo_volume",
            GeoVolumeClusterer,
            {
                "k_mode": "manual",
                "n_clusters": 2,
                "geography_weight": 0.7,
                "volume_weight": 0.3,
            },
        ),
    ],
)
def test_business_adapter_paths_match_legacy_product_output_and_graph(
    product_files, mode, clusterer_factory, parameters
):
    source, cache = product_files
    recorder = RecordingClusterer(clusterer_factory())
    service = ClusteringService(
        source,
        coordinate_cache_path=cache,
        clusterers={mode: recorder},
    )
    request = ClusteringRequest.from_payload(
        _payload(mode=mode, parameters=parameters),
        product_mode_catalog=service.product_mode_catalog,
    )
    locations, report = service._locations(request)
    projection = service._projection(locations)
    spatial_points = service._ml_input(locations, projection, include_economics=False)
    full_graph, _ = service._spatial_graph(spatial_points)
    if mode == "geo_cost":
        economic_points = service._ml_input(locations, projection, include_economics=True)
        legacy_points = [
            point
            for point in economic_points
            if point.trip_count > 0
            and point.weighted_price is not None
            and point.weighted_rub_per_km is not None
        ]
        legacy_graph = full_graph.induced_subgraph({point.id for point in legacy_points})
    else:
        legacy_points = spatial_points
        legacy_graph = full_graph
    algorithm_parameters = {
        "spatial_graph": legacy_graph,
        "n_clusters": 2,
        "k_min": 2,
        "k_max": 20,
        "geography_weight": 0.7,
        ("economics_weight" if mode == "geo_cost" else "volume_weight"): 0.3,
    }
    legacy_result = clusterer_factory().fit(legacy_points, algorithm_parameters)
    legacy_output = service._result_json(request, locations, report, legacy_result, "success")

    adapter_output = service.run(request)

    adapter_ids, adapter_parameters, adapter_graph = recorder.calls[0]
    assert adapter_ids == tuple(point.id for point in legacy_points)
    assert adapter_parameters == {
        key: value for key, value in algorithm_parameters.items() if key != "spatial_graph"
    }
    assert adapter_graph.node_ids == legacy_graph.node_ids
    assert adapter_graph.edges == legacy_graph.edges
    assert adapter_output == legacy_output


def test_product_modes_preserve_eligibility_and_spatial_topology(
    mode_eligibility_files,
):
    source, cache = mode_eligibility_files
    recorders = {
        "geography": RecordingClusterer(GeographicClusterer()),
        "geo_cost": RecordingClusterer(GeoCostClusterer()),
        "geo_volume": RecordingClusterer(GeoVolumeClusterer()),
        "bear_zones": RecordingClusterer(BearZoneDetector()),
        "bear_volume_zones": RecordingClusterer(BearVolumeZoneDetector()),
    }
    service = ClusteringService(
        source,
        coordinate_cache_path=cache,
        clusterers=recorders,
    )
    parameters = {
        "geography": {"k_mode": "manual", "n_clusters": 2},
        "geo_cost": {
            "k_mode": "manual",
            "n_clusters": 2,
            "geography_weight": 0.7,
            "economics_weight": 0.3,
        },
        "geo_volume": {
            "k_mode": "manual",
            "n_clusters": 2,
            "geography_weight": 0.7,
            "volume_weight": 0.3,
        },
        "bear_zones": {"bear_threshold": 0.35, "singleton_threshold": 0.7},
        "bear_volume_zones": {
            "volume_threshold": 0.35,
            "singleton_threshold": 0.7,
        },
    }

    for mode, mode_parameters in parameters.items():
        service.run(ClusteringRequest.from_payload(_payload(mode=mode, parameters=mode_parameters)))

    expected_ids = {
        "geography": {"a", "b", "c", "economic-missing", "zero-volume"},
        "geo_volume": {"a", "b", "c", "economic-missing", "zero-volume"},
        "geo_cost": {"a", "b", "c"},
        "bear_zones": {"a", "b", "c"},
        "bear_volume_zones": {"a", "b", "c", "economic-missing"},
    }
    for mode, ids in expected_ids.items():
        assert set(recorders[mode].calls[0][0]) == ids

    expected_parameters = {
        "geography": {"n_clusters": 2, "k_min": 2, "k_max": 20},
        "geo_cost": {
            "n_clusters": 2,
            "k_min": 2,
            "k_max": 20,
            "geography_weight": 0.7,
            "economics_weight": 0.3,
        },
        "geo_volume": {
            "n_clusters": 2,
            "k_min": 2,
            "k_max": 20,
            "geography_weight": 0.7,
            "volume_weight": 0.3,
        },
        "bear_zones": {"bear_threshold": 0.35, "singleton_threshold": 0.7},
        "bear_volume_zones": {
            "volume_threshold": 0.35,
            "singleton_threshold": 0.7,
        },
    }
    for mode, mode_parameters in expected_parameters.items():
        assert recorders[mode].calls[0][1] == mode_parameters

    graphs = {mode: recorder.calls[0][2] for mode, recorder in recorders.items()}
    full_edges = {frozenset((edge.first_id, edge.second_id)) for edge in graphs["geography"].edges}
    assert graphs["geography"].audit["node_count"] == 5
    assert graphs["geo_volume"].edges == graphs["geography"].edges
    for mode in ("geo_cost", "bear_zones", "bear_volume_zones"):
        graph = graphs[mode]
        ids = expected_ids[mode]
        edges = {frozenset((edge.first_id, edge.second_id)) for edge in graph.edges}
        assert graph.parameters["induced_subgraph"] is True
        assert graph.audit["induced_from_node_count"] == 5
        assert edges == {edge for edge in full_edges if edge <= ids}


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
    ("mode", "clusterer_factory", "explicit_parameters"),
    [
        (
            "geo_cost",
            GeoCostClusterer,
            {
                "k_mode": "auto",
                "n_clusters": "auto",
                "geography_weight": 0.7,
                "economics_weight": 0.3,
            },
        ),
        (
            "geo_volume",
            GeoVolumeClusterer,
            {
                "k_mode": "auto",
                "n_clusters": "auto",
                "geography_weight": 0.7,
                "volume_weight": 0.3,
            },
        ),
    ],
)
def test_equivalent_normalized_mode_parameters_share_result_cache(
    product_files, mode, clusterer_factory, explicit_parameters
):
    source, cache = product_files
    clusterer = RecordingClusterer(clusterer_factory())
    service = ClusteringService(
        source,
        coordinate_cache_path=cache,
        clusterers={mode: clusterer},
    )
    implicit_payload = _payload(mode=mode)
    implicit_payload.pop("parameters")
    implicit = ClusteringRequest.from_payload(implicit_payload)
    explicit = ClusteringRequest.from_payload(
        _payload(mode=mode, parameters=explicit_parameters)
    )

    first = service.run(implicit)
    second = service.run(explicit)

    assert implicit == explicit
    assert first == second
    assert len(clusterer.calls) == 1


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
    response = product_client.post("/api/clustering/run", json=_payload(parameters=parameters))
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


def test_runtime_infeasible_manual_k_has_stable_product_error(product_client):
    response = product_client.post(
        "/api/clustering/run",
        json=_payload(parameters={"k_mode": "manual", "n_clusters": 20}),
    )

    assert response.status_code == 422
    assert response.get_json()["code"] == "INVALID_CLUSTER_COUNT"
    assert response.get_json()["error"].startswith("K=20 невозможно для ")


def test_geo_cost_without_valid_economics_has_stable_product_error(
    tmp_path, product_client_factory
):
    source = tmp_path / "missing-economics.csv"
    cache = tmp_path / "missing-economics-coords.json"
    _write_csv(
        source,
        [
            _row("a", "A", price=""),
            _row("b", "B", price=""),
        ],
    )
    cache.write_text(
        json.dumps({"A::Region A": [55.0, 37.0], "B::Region A": [55.01, 37.01]}),
        encoding="utf-8",
    )
    client = product_client_factory(source, cache)

    response = client.post(
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

    assert response.status_code == 422
    assert response.get_json() == {
        "ok": False,
        "code": "INSUFFICIENT_ECONOMICS",
        "error": "Недостаточно точек с валидными price, route_length и ₽/км.",
    }


def test_connectivity_violation_has_stable_http_semantics(product_files, product_client_factory):
    source, cache = product_files
    client = product_client_factory(
        source,
        cache,
        clusterers={"geography": ConnectivityViolatingClusterer()},
    )

    response = client.post("/api/clustering/run", json=_payload())

    assert response.status_code == 422
    assert response.get_json() == {
        "ok": False,
        "code": "CONNECTIVITY_VIOLATION",
        "error": "characterized connectivity violation",
    }


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


@pytest.mark.parametrize(
    ("mode", "parameters", "expected"),
    [
        *[
            (
                "geo_cost",
                {"geography_weight": geography, "economics_weight": feature},
                {
                    "k_mode": "auto",
                    "n_clusters": "auto",
                    "geography_weight": geography,
                    "economics_weight": feature,
                },
            )
            for geography, feature in ((0.8, 0.2), (0.7, 0.3), (0.6, 0.4))
        ],
        *[
            (
                "geo_volume",
                {"geography_weight": geography, "volume_weight": feature},
                {
                    "k_mode": "auto",
                    "n_clusters": "auto",
                    "geography_weight": geography,
                    "volume_weight": feature,
                },
            )
            for geography, feature in ((0.8, 0.2), (0.7, 0.3), (0.6, 0.4))
        ],
        *[
            (
                "bear_zones",
                {"bear_threshold": threshold},
                {"bear_threshold": threshold, "singleton_threshold": 0.7},
            )
            for threshold in (0.2, 0.25, 0.3, 0.35, 0.4, 0.5)
        ],
        *[
            (
                "bear_volume_zones",
                {"volume_threshold": threshold},
                {"volume_threshold": threshold, "singleton_threshold": 0.7},
            )
            for threshold in (0.2, 0.25, 0.3, 0.35, 0.4, 0.5)
        ],
    ],
)
def test_advertised_mode_presets_are_accepted_and_normalized(
    product_client, mode, parameters, expected
):
    response = product_client.post(
        "/api/clustering/preview",
        json=_payload(mode=mode, parameters=parameters),
    )

    assert response.status_code == 200
    assert response.get_json()["analysis"]["parameters"] == expected


@pytest.mark.parametrize(
    "mode",
    ["geography", "geo_cost", "geo_volume", "bear_zones", "bear_volume_zones"],
)
def test_each_mode_rejects_unknown_parameter_keys(product_client, mode):
    response = product_client.post(
        "/api/clustering/run",
        json=_payload(mode=mode, parameters={"unexpected": True}),
    )

    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_MODE_PARAMETERS"


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
    point = next(item for item in response.get_json()["points"] if item["id"] == "economic-missing")
    assert point["status"] == "economic_unavailable"
    assert point["cluster_id"] is None


@pytest.mark.parametrize(
    ("mode", "parameters"),
    [
        (
            "bear_zones",
            {"bear_threshold": 0.35, "singleton_threshold": 0.7},
        ),
        (
            "bear_volume_zones",
            {"volume_threshold": 0.35, "singleton_threshold": 0.7},
        ),
    ],
)
def test_bear_no_bears_is_a_successful_product_result(
    tmp_path, product_client_factory, mode, parameters
):
    source = tmp_path / f"{mode}-flat.csv"
    cache = tmp_path / f"{mode}-flat-coords.json"
    _write_csv(
        source,
        [
            _row("a", "A", price="1000", trips="10"),
            _row("b", "B", price="1000", trips="10"),
            _row("c", "C", price="1000", trips="10"),
        ],
    )
    cache.write_text(
        json.dumps(
            {
                "A::Region A": [55.0, 37.0],
                "B::Region A": [55.01, 37.01],
                "C::Region A": [55.02, 37.02],
            }
        ),
        encoding="utf-8",
    )
    client = product_client_factory(source, cache)

    response = client.post(
        "/api/clustering/run",
        json=_payload(mode=mode, parameters=parameters),
    )
    result = response.get_json()

    assert response.status_code == 200
    assert result["status"] == "no_bears"
    assert result["clusters"] == []
    assert {point["status"] for point in result["points"]} == {"ordinary"}


@pytest.mark.parametrize(
    ("mode", "parameters", "expected_status"),
    [
        (
            "bear_zones",
            {"bear_threshold": 0.35, "singleton_threshold": 0.7},
            "bear_candidate",
        ),
        (
            "bear_volume_zones",
            {"volume_threshold": 0.35, "singleton_threshold": 0.7},
            "bear_volume_candidate",
        ),
    ],
)
def test_unassigned_bear_candidates_keep_product_status(
    tmp_path, product_client_factory, mode, parameters, expected_status
):
    source = tmp_path / f"{mode}-candidate.csv"
    cache = tmp_path / f"{mode}-candidate-coords.json"
    _write_csv(
        source,
        [
            _row("low-a", "Low A", price="1000", trips="10"),
            _row("low-b", "Low B", price="1000", trips="10"),
            _row("candidate", "Candidate", price="2200", trips="18"),
        ],
    )
    cache.write_text(
        json.dumps(
            {
                "Low A::Region A": [55.0, 37.0],
                "Low B::Region A": [55.01, 37.01],
                "Candidate::Region A": [55.02, 37.02],
            }
        ),
        encoding="utf-8",
    )
    client = product_client_factory(source, cache)

    response = client.post(
        "/api/clustering/run",
        json=_payload(mode=mode, parameters=parameters),
    )
    result = response.get_json()
    candidate = next(point for point in result["points"] if point["id"] == "candidate")

    assert response.status_code == 200
    assert result["status"] == "no_bears"
    assert candidate["status"] == expected_status
    assert candidate["cluster_id"] == -1


def test_geo_cost_warning_order_and_quality_semantics(tmp_path, product_client_factory):
    source = tmp_path / "warning-semantics.csv"
    cache = tmp_path / "warning-semantics-coords.json"
    _write_csv(
        source,
        [
            _row("a", "A", price="1000", trips="20"),
            _row(
                "b",
                "B",
                price="1100",
                trips="20",
                period="forecast",
                price_type="tender",
            ),
            _row("economic-missing", "Economic Missing", price="", trips="20"),
            _row("unresolved", "Unresolved", price="1200", trips="20"),
        ],
    )
    cache.write_text(
        json.dumps(
            {
                "A::Region A": [55.0, 37.0],
                "B::Region A": [55.01, 37.01],
                "Economic Missing::Region A": [55.02, 37.02],
            }
        ),
        encoding="utf-8",
    )
    client = product_client_factory(source, cache)

    response = client.post(
        "/api/clustering/run",
        json=_payload(
            period_types=["current", "forecast"],
            mode="geo_cost",
            parameters={
                "k_mode": "manual",
                "n_clusters": 2,
                "geography_weight": 0.7,
                "economics_weight": 0.3,
            },
        ),
    )
    result = response.get_json()

    assert response.status_code == 200
    assert [warning["code"] for warning in result["warnings"]] == [
        "CONTAINS_FORECAST",
        "MIXED_ECONOMIC_SEGMENTS",
        "COORDINATE_INCOMPLETE",
        "ECONOMIC_UNAVAILABLE",
    ]
    assert result["data_quality"]["contains_forecast"] is True
    assert result["data_quality"]["economic_unavailable_points"] == 1
    assert result["data_quality"]["unresolved_points"] == 1


def test_compare_uses_fixed_fact_only_contract(product_client, product_service):
    payload = _payload()
    payload.pop("mode")
    payload.pop("parameters")
    response = product_client.post("/api/clustering/compare", json=payload)
    result = response.get_json()
    service_result = product_service.compare(payload)

    assert response.status_code == 200
    assert result["winner"] is None
    assert set(result["results"]) == {
        "geography",
        "geo_cost",
        "geo_volume",
        "bear_zones",
        "bear_volume_zones",
    }
    assert list(service_result["results"]) == [
        "geography",
        "geo_cost",
        "geo_volume",
        "bear_zones",
        "bear_volume_zones",
    ]
    assert result["results"]["geography"]["analysis"]["parameters"]["k_mode"] == "auto"
    assert result["results"]["geo_cost"]["analysis"]["parameters"]["economics_weight"] == 0.3
    assert result["results"]["geo_volume"]["analysis"]["parameters"]["volume_weight"] == 0.3
    assert result["results"]["bear_zones"]["analysis"]["parameters"]["bear_threshold"] == 0.35
    assert (
        result["results"]["bear_volume_zones"]["analysis"]["parameters"]["volume_threshold"] == 0.35
    )
    filters = {
        json.dumps(mode_result["analysis"]["filters"], sort_keys=True)
        for mode_result in result["results"].values()
    }
    point_ids = {
        tuple(point["id"] for point in mode_result["points"])
        for mode_result in result["results"].values()
    }
    assert len(filters) == 1
    assert len(point_ids) == 1


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
    assert client.get("/api/records?town=A&region=Region&type=shipment").status_code == 200
    assert client.get("/api/ml-cluster").status_code == 400
