from __future__ import annotations

import csv

import pytest
import test_origin_union_api
from test_clustering_product_api import _row

from backend.clustering_api import set_clustering_service
from backend.services.clustering_service import ClusteringService
from ml.data.loader import PULSE_COLUMNS

union_client = test_origin_union_api.union_client
payload = test_origin_union_api.payload


def all_payload(**changes):
    request = payload(**changes)
    request.pop("origin_fiases")
    return {**request, "all_origins": True}


def test_all_resolves_complete_region_before_common_filters(union_client):
    client, _ = union_client
    suggestions = client.get("/api/clustering/origins?q=b+Warehouse&limit=1").get_json()
    assert [origin["fias_id"] for origin in suggestions] == ["a"]
    response = client.post("/api/clustering/run", json=all_payload())
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert result["analysis"]["origin_fiases"] == ["a", "b", "c"]
    assert result["analysis"]["selection_intent"] == {"all_origins": True}
    assert result["analysis"]["origin_coverage"][-1] == {
        "fias_id": "c", "source_row_count": 0, "trip_count": 0, "zero_match": True,
    }
    x = next(point for point in result["points"] if point["id"] == "x")
    assert (x["trip_count"], x["weighted_route_length"], x["valid_route_length_trip_count"]) == (60, 250, 40)
    assert result["data_quality"]["source_row_count"] == 6


@pytest.mark.parametrize("endpoint", ["preview", "compare"])
def test_all_preview_and_compare_keep_resolved_context(union_client, endpoint):
    client, _ = union_client
    response = client.post(f"/api/clustering/{endpoint}", json=all_payload())
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    results = body["results"].values() if endpoint == "compare" else [body]
    for result in results:
        assert result["analysis"]["origin_fiases"] == ["a", "b", "c"]
        assert result["analysis"]["selection_intent"] == {"all_origins": True}
        assert result["analysis"]["frozen_request"]["origin_fiases"] == ["a", "b", "c"]
    if endpoint == "compare":
        assert body["winner"] is None
        assert len(body["results"]) == 5
        assert len({result["data_snapshot"] for result in body["results"].values()}) == 1


def test_all_options_and_regional_suggestions_exclude_other_region(union_client):
    client, service = union_client
    with service.source_path.open("a", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerow(
            _row("x", "X", origin="outside", region="Other Region", trips="10000"))
    suggestions = client.get("/api/clustering/origins?destination_region=Region+A&limit=100").get_json()
    assert {item["fias_id"] for item in suggestions} == {"a", "b", "c"}
    response = client.get("/api/clustering/options?all_origins=true&destination_region=Region+A")
    assert response.status_code == 200, response.get_json()
    options = response.get_json()
    assert [item["fias_id"] for item in options["origins"]] == ["a", "b", "c"]
    assert options["facets"]["price_types"] == [{"value": "spot", "count": 6}, {"value": "tender", "count": 1}]


def test_compare_resolves_all_once_for_five_modes(union_client, monkeypatch):
    client, service = union_client
    options = service.repository.options
    resolutions = []
    def catalog(*args, **kwargs):
        if kwargs.get("destination_region") == "Region A":
            resolutions.append(kwargs)
        return options(*args, **kwargs)
    monkeypatch.setattr(service.repository, "options", catalog)
    response = client.post("/api/clustering/compare", json=all_payload())
    assert response.status_code == 200, response.get_json()
    assert len(resolutions) == 1


@pytest.mark.parametrize("endpoint", ["run", "preview", "compare"])
@pytest.mark.parametrize("changes,status,code", [
    ({"all_origins": False}, 400, "INVALID_REQUEST"),
    ({"all_origins": None}, 400, "INVALID_REQUEST"),
    ({"all_origins": "true"}, 400, "INVALID_REQUEST"),
    ({"all_origins": 1}, 400, "INVALID_REQUEST"),
    ({"origin_fias": "a"}, 400, "INVALID_REQUEST"),
    ({"origin_fiases": []}, 400, "INVALID_REQUEST"),
    ({"origin_fiases": ["a"]}, 400, "INVALID_REQUEST"),
    ({"destination_region": ""}, 400, "INVALID_REQUEST"),
    ({"destination_region": None}, 400, "INVALID_REQUEST"),
    ({"destination_region": "unknown"}, 422, "UNKNOWN_DESTINATION_REGION"),
    ({"vehicle_types": ["absent"]}, 422, "NO_DATA"),
])
def test_all_invalid_requests_are_typed(union_client, endpoint, changes, status, code):
    client, _ = union_client
    response = client.post(f"/api/clustering/{endpoint}", json={**all_payload(), **changes},
                           headers={"X-Request-ID": "regional-invalid"})
    assert response.status_code == status, response.get_json()
    assert response.get_json()["code"] == code
    assert response.headers["X-Request-ID"] == "regional-invalid"


@pytest.mark.parametrize("query", [
    "all_origins=false&destination_region=Region+A", "all_origins=1&destination_region=Region+A",
    "all_origins=&destination_region=Region+A", "all_origins=true",
    "all_origins=true&origin_fias=a&destination_region=Region+A",
    "all_origins=true&origin_fiases=a&destination_region=Region+A",
])
def test_all_options_reject_invalid_selectors(union_client, query):
    client, _ = union_client
    response = client.get(f"/api/clustering/options?{query}")
    assert response.status_code == 400
    assert response.get_json()["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("first_all", [True, False])
def test_same_set_cache_reuse_preserves_intent_and_exact_detail(union_client, monkeypatch, first_all):
    client, service = union_client
    explicit = payload(origin_fiases=["c", "b", "a", "a"])
    first = all_payload() if first_all else explicit
    second = explicit if first_all else all_payload()
    saved = client.post("/api/clustering/run", json=first).get_json()
    def no_calculation(*args, **kwargs):
        pytest.fail("Saved result/detail must reuse calculation, never rerun")
    monkeypatch.setattr(service.product_mode_catalog, "evaluate", no_calculation)
    reused = client.post("/api/clustering/run", json=second).get_json()
    assert reused["analysis"]["selection_intent"] == (
        {"origin_fiases": ["a", "b", "c"]} if first_all else {"all_origins": True})
    assert saved["analysis"]["selection_intent"] == (
        {"all_origins": True} if first_all else {"origin_fiases": ["a", "b", "c"]})
    assert reused["points"] == saved["points"]
    assert reused["cluster_table"] == saved["cluster_table"]
    frozen = saved["analysis"]["frozen_request"]
    assert frozen["origin_fiases"] == ["a", "b", "c"]
    assert "all_origins" not in frozen
    detail = {**frozen, "data_snapshot": saved["data_snapshot"], "destination_fias": "x"}
    response = client.post("/api/clustering/point-rows", json=detail)
    assert response.status_code == 200, response.get_json()
    rows = response.get_json()["rows"]
    cluster = next(point["cluster_id"] for point in saved["points"] if point["id"] == "x")
    assert len(rows) == 3
    assert {row["origin_fias"] for row in rows} == {"a", "b"}
    assert all(row["cluster_id"] == cluster for row in rows)
    response = client.post("/api/clustering/point-rows", json={**detail,
        "origin_fiases": ["a", "b", "c", "outside"]})
    assert response.status_code == 409
    assert response.get_json()["code"] == "RESULT_UNAVAILABLE"
    implicit = dict(detail)
    implicit.pop("origin_fiases")
    response = client.post("/api/clustering/point-rows", json={**implicit, "all_origins": True})
    assert response.status_code == 400


def test_all_recalculation_resolves_new_generation_without_expanding_saved_detail(union_client):
    client, service = union_client
    saved = client.post("/api/clustering/run", json=all_payload()).get_json()
    detail = {**saved["analysis"]["frozen_request"], "data_snapshot": saved["data_snapshot"],
              "destination_fias": "x"}
    with service.source_path.open("a", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerow(_row("x", "X", origin="d", trips="10"))
    response = client.post("/api/clustering/point-rows", json=detail)
    assert response.status_code == 409
    assert response.get_json()["code"] == "STALE_DATA_SNAPSHOT"
    new = client.post("/api/clustering/run", json=all_payload()).get_json()
    assert new["analysis"]["origin_fiases"] == ["a", "b", "c", "d"]
    assert saved["analysis"]["origin_fiases"] == ["a", "b", "c"]
    assert new["data_snapshot"] != saved["data_snapshot"]
    assert client.post("/api/clustering/point-rows", json=detail).status_code == 409
    new_detail = {**new["analysis"]["frozen_request"], "data_snapshot": new["data_snapshot"],
                  "destination_fias": "x"}
    assert client.post("/api/clustering/point-rows", json=new_detail).get_json()["total"] == 4


@pytest.mark.parametrize("endpoint", ["run", "preview", "compare", "options"])
@pytest.mark.parametrize("failure", ["source", "coordinates", "catalog"])
def test_all_catalog_failure_or_generation_race_never_returns_partial_success(union_client, monkeypatch, endpoint, failure):
    client, service = union_client
    options = service.repository.options
    changed = False
    def catalog(*args, **kwargs):
        nonlocal changed
        result = options(*args, **kwargs)
        if kwargs.get("destination_region") and not changed:
            changed = True
            if failure == "catalog":
                raise OSError("Synthetic catalog read failure")
            path = service.source_path if failure == "source" else service.coordinate_cache_path
            with path.open("a", encoding="utf-8") as stream:
                stream.write("\n")
        return result
    monkeypatch.setattr(service.repository, "options", catalog)
    response = (client.get("/api/clustering/options?all_origins=true&destination_region=Region+A")
                if endpoint == "options" else client.post(f"/api/clustering/{endpoint}", json=all_payload()))
    assert response.status_code == (500 if failure == "catalog" else 409), response.get_json()
    assert response.get_json()["code"] == ("INTERNAL_ERROR" if failure == "catalog" else "STALE_DATA_SNAPSHOT")
    assert "results" not in response.get_json()


def test_all_includes_origins_beyond_maximum_search_page_in_sorted_order(union_client):
    client, service = union_client
    with service.source_path.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        for index in reversed(range(105)):
            writer.writerow(_row("x", "X", origin=f"extra-{index:03d}", price_type="tender"))
        writer.writerow(_row("x", "X", origin="outside", region="Other Region"))
    assert len(client.get("/api/clustering/origins?destination_region=Region+A&limit=100").get_json()) == 100
    expected = ["a", "b", "c"] + [f"extra-{index:03d}" for index in range(105)]
    response = client.post("/api/clustering/run", json=all_payload())
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["analysis"]["origin_fiases"] == expected
    assert len(response.get_json()["analysis"]["origin_coverage"]) == 108
    assert client.post("/api/clustering/run", json=all_payload()).get_json() == response.get_json()


def test_all_compare_shares_full_graph_and_keeps_mode_semantics(union_client, monkeypatch):
    client, service = union_client
    datasets = []
    evaluate = service.product_mode_catalog.evaluate
    def observe(selection, dataset, operation):
        datasets.append(dataset)
        return evaluate(selection, dataset, operation)
    monkeypatch.setattr(service.product_mode_catalog, "evaluate", observe)
    response = client.post("/api/clustering/compare", json=all_payload())
    assert response.status_code == 200, response.get_json()
    assert len(datasets) == 5
    assert all(dataset.spatial_graph is datasets[0].spatial_graph for dataset in datasets)
    assert set(datasets[0].spatial_graph.node_ids) == {"w", "x", "y", "z"}
    results = response.get_json()["results"]
    assert results["bear_zones"]["status"] == "no_bears"
    assert results["bear_volume_zones"]["clusters"][0]["point_ids"] == ["x"]
    assert next(point for point in results["geo_cost"]["points"] if point["id"] == "y")["status"] == "economic_unavailable"
    for mode in ("bear_zones", "bear_volume_zones"):
        assert results[mode]["cluster_table"] == {"supported": False}


@pytest.mark.parametrize("endpoint", ["run", "preview", "compare"])
def test_all_generation_change_during_evaluation_is_rejected(union_client, monkeypatch, endpoint):
    client, service = union_client
    evaluate = service.product_mode_catalog.evaluate
    def race(*args, **kwargs):
        result = evaluate(*args, **kwargs)
        with service.source_path.open("a", encoding="utf-8") as stream:
            stream.write("\n")
        return result
    monkeypatch.setattr(service.product_mode_catalog, "evaluate", race)
    response = client.post(f"/api/clustering/{endpoint}", json=all_payload())
    assert response.status_code == 409
    assert response.get_json()["code"] == "STALE_DATA_SNAPSHOT"


def test_all_detail_after_restart_requires_saved_result(union_client):
    client, service = union_client
    saved = client.post("/api/clustering/run", json=all_payload()).get_json()
    set_clustering_service(ClusteringService(service.source_path,
        coordinate_cache_path=service.coordinate_cache_path))
    detail = {**saved["analysis"]["frozen_request"], "data_snapshot": saved["data_snapshot"],
              "destination_fias": "x"}
    response = client.post("/api/clustering/point-rows", json=detail)
    assert response.status_code == 409
    assert response.get_json()["code"] == "RESULT_UNAVAILABLE"


def test_injected_catalog_all_refreshes_after_source_generation_change(union_client):
    client, service = union_client
    from ml.data.loader import iter_records
    injected = ClusteringService(service.source_path, coordinate_cache_path=service.coordinate_cache_path,
        records_factory=lambda: iter_records(service.source_path))
    set_clustering_service(injected)
    first = client.post("/api/clustering/run", json=all_payload()).get_json()
    assert first["analysis"]["origin_fiases"] == ["a", "b", "c"]
    with service.source_path.open("a", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerow(_row("x", "X", origin="d"))
    second = client.post("/api/clustering/run", json=all_payload()).get_json()
    assert second["analysis"]["origin_fiases"] == ["a", "b", "c", "d"]


def test_injected_all_options_are_destination_scoped_with_union_facets(union_client):
    client, service = union_client
    from ml.data.loader import iter_records
    with service.source_path.open("a", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerow(
            _row("x", "X", origin="outside", region="Other Region"))
    set_clustering_service(ClusteringService(service.source_path,
        coordinate_cache_path=service.coordinate_cache_path,
        records_factory=lambda: iter_records(service.source_path)))
    response = client.get("/api/clustering/options?all_origins=true&destination_region=Region+A")
    assert response.status_code == 200, response.get_json()
    assert {origin["fias_id"] for origin in response.get_json()["origins"]} == {"a", "b", "c"}
    assert response.get_json()["facets"]["price_types"] == [
        {"value": "spot", "count": 6}, {"value": "tender", "count": 1}]


@pytest.mark.parametrize("injected", [False, True])
def test_all_options_use_normalized_region_for_catalog_and_facets(union_client, injected):
    client, service = union_client
    if injected:
        from ml.data.loader import iter_records
        set_clustering_service(ClusteringService(service.source_path,
            coordinate_cache_path=service.coordinate_cache_path,
            records_factory=lambda: iter_records(service.source_path)))
    response = client.get("/api/clustering/options?all_origins=true&destination_region=%20Region%20A%20")
    assert response.status_code == 200, response.get_json()
    assert {origin["fias_id"] for origin in response.get_json()["origins"]} == {"a", "b", "c"}
    assert response.get_json()["facets"]["price_types"] == [
        {"value": "spot", "count": 6}, {"value": "tender", "count": 1}]


def test_all_empty_source_catalog_has_typed_unknown_region(union_client):
    client, service = union_client
    with service.source_path.open("w", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writeheader()
    response = client.post("/api/clustering/run", json=all_payload())
    assert response.status_code == 422
    assert response.get_json()["code"] == "UNKNOWN_DESTINATION_REGION"
