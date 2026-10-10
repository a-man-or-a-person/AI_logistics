from __future__ import annotations

import csv
import json

import pytest
from test_clustering_product_api import _row

from backend.app import app
from backend.clustering_api import set_clustering_service
from backend.services.clustering_service import ClusteringService
from ml.data.loader import PULSE_COLUMNS


@pytest.fixture()
def union_client(tmp_path):
    source, cache = tmp_path / "pulse.csv", tmp_path / "coords.json"
    rows = [
        _row("x", "X", origin="a", trips="10", price="1000", route_length="100"),
        _row("x", "X", origin="b", trips="30", price="6000", route_length="300"),
        _row("x", "X", origin="b", trips="20", price="", route_length=""),
        _row("y", "Y", origin="a", trips="5", price="", route_length="200"),
        _row("z", "Z", origin="b", trips="5", price="1000", route_length="100"),
        _row("w", "W", origin="a", trips="5", price="1000", route_length="100"),
        _row("x", "X", origin="c", origin_name="a Warehouse", trips="999", price="1000", price_type="tender"),
    ]
    for row in rows:
        if row["shipment_point_locality_fias_id"] == "a":
            row["shipment_point_name_town"] = "b Warehouse"
    rows[1]["shipment_point_region"] = "B Region"
    rows[2]["shipment_point_region"] = ""
    with source.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    cache.write_text(json.dumps({f"{name}::Region A": coords for name, coords in
        zip("XYZW", ([55, 37], [55.01, 37], [55.01, 37.01], [55, 37.01]), strict=True)}),
        encoding="utf-8")
    service = ClusteringService(source, coordinate_cache_path=cache)
    set_clustering_service(service)
    app.config.update(TESTING=True)
    yield app.test_client(), service
    set_clustering_service(None)


def payload(**changes):
    return {"origin_fiases": ["a", "b"], "destination_region": "Region A",
        "period_types": ["current"], "price_types": ["spot"],
        "vehicle_types": [], "tonnage_ids": [], "mode": "geography",
        "parameters": {"k_mode": "manual", "n_clusters": 2}, **changes}


def test_union_is_canonical_and_pools_raw_valid_weights(union_client):
    client, _ = union_client
    first = client.post("/api/clustering/run", json=payload())
    assert first.status_code == 200, first.get_json()
    result = first.get_json()
    for origins in (["b", "a"], ["b", "a", "a", " b "]):
        assert client.post("/api/clustering/run", json=payload(origin_fiases=origins)).get_json() == result
    assert result["analysis"]["origin_fiases"] == ["a", "b"]
    assert result["analysis"]["origin"] is None
    assert result["analysis"]["selection_intent"] == {"origin_fiases": ["a", "b"]}
    assert len(result["points"]) == 4
    x = next(point for point in result["points"] if point["id"] == "x")
    assert x["trip_count"] == 60
    assert result["data_quality"]["source_row_count"] == 6
    assert x["weighted_route_length"] == 250
    assert x["valid_route_length_trip_count"] == 40
    assert x["weighted_price"] == 4750
    assert x["valid_price_trip_count"] == 40
    assert x["weighted_rub_per_km"] == 17.5
    assert x["valid_rub_per_km_trip_count"] == 40
    assert sum(row["trip_count"] for row in result["cluster_table"]["rows"]) == 75



@pytest.mark.parametrize("endpoint", ["preview", "run", "compare"])
def test_union_surfaces_and_scalar_parity(union_client, endpoint):
    client, _ = union_client
    scalar = payload()
    scalar.pop("origin_fiases")
    scalar["origin_fias"] = "a"
    single = payload(origin_fiases=["a"])
    old = client.post(f"/api/clustering/{endpoint}", json=scalar)
    new = client.post(f"/api/clustering/{endpoint}", json=single)
    assert new.status_code == old.status_code == 200, new.get_json()
    # Compare dataset echoes canonical selection, independent of scalar wire spelling.
    assert new.get_json() == old.get_json()
    if endpoint == "compare":
        union = client.post("/api/clustering/compare", json=payload()).get_json()
        assert union["winner"] is None
        assert set(union["results"]) == {"geography", "geo_cost", "geo_volume", "bear_zones", "bear_volume_zones"}
        assert all(r["analysis"]["origin_fiases"] == ["a", "b"] for r in union["results"].values())
        assert len({r["data_snapshot"] for r in union["results"].values()}) == 1


def test_union_options_facets_and_zero_match(union_client):
    client, _ = union_client
    response = client.get("/api/clustering/options?origin_fiases=b&origin_fiases=a&origin_fiases=a&destination_region=Region+A")
    assert response.status_code == 200
    assert response.get_json()["facets"]["price_types"] == [{"value": "spot", "count": 6}]
    result = client.post("/api/clustering/run", json=payload(origin_fiases=["a", "b", "c"])).get_json()
    assert result["analysis"]["origin_coverage"][-1] == {"fias_id": "c", "source_row_count": 0, "trip_count": 0, "zero_match": True}


def test_rich_detail_is_bound_to_saved_mode_and_rows(union_client):
    client, service = union_client
    result = client.post("/api/clustering/run", json=payload()).get_json()
    detail = {**payload(), "data_snapshot": result["data_snapshot"], "destination_fias": "x"}
    response = client.post("/api/clustering/point-rows", json=detail)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["total"] == 3
    assert {r["origin_fias"] for r in data["rows"]} == {"a", "b"}
    assert {r["origin_region"] for r in data["rows"]} == {"Origin Region", "B Region", None}
    assert len({r["source_row_id"] for r in data["rows"]}) == 3
    cluster = next(p["cluster_id"] for p in result["points"] if p["id"] == "x")
    assert all(r["cluster_id"] == cluster and r["destination_fias"] == "x" for r in data["rows"])
    b = client.post("/api/clustering/point-rows", json={**detail, "detail_origin_fias": "b"}).get_json()
    assert b["total"] == 2
    assert all(r["origin_fias"] == "b" for r in b["rows"])
    for changed in ({"parameters": {"k_mode": "manual", "n_clusters": 3}}, {"mode": "geo_volume"}, {"origin_fiases": ["a"]}):
        error = client.post("/api/clustering/point-rows", json={**detail, **changed})
        assert error.status_code == 409
        assert error.get_json()["code"] == "RESULT_UNAVAILABLE"
    service._result_cache.clear()  # Simulate the existing LRU eviction, never rerun on detail.
    error = client.post("/api/clustering/point-rows", json=detail)
    assert error.status_code == 409
    assert error.get_json()["code"] == "RESULT_UNAVAILABLE"


@pytest.mark.parametrize("endpoint", ["run", "preview", "compare"])
@pytest.mark.parametrize("change,status,code", [
    ({"origin_fiases": []}, 400, "INVALID_REQUEST"),
    ({"origin_fiases": None}, 400, "INVALID_REQUEST"),
    ({"origin_fiases": "a"}, 400, "INVALID_REQUEST"),
    ({"origin_fiases": ["a", ""]}, 400, "INVALID_REQUEST"),
    ({"origin_fiases": ["a", 1]}, 400, "INVALID_REQUEST"),
    ({"origin_fias": "a"}, 400, "INVALID_REQUEST"),
    ({"all_origins": True}, 400, "INVALID_REQUEST"),
    ({"origin_fiases": ["unknown"]}, 422, "UNKNOWN_ORIGIN"),
    ({"destination_region": "unknown"}, 422, "UNKNOWN_DESTINATION_REGION"),
    ({"vehicle_types": ["absent"]}, 422, "NO_DATA"),
])
def test_union_errors_keep_request_id(union_client, endpoint, change, status, code):
    client, _ = union_client
    response = client.post(f"/api/clustering/{endpoint}", json=payload(**change),
                           headers={"X-Request-ID": "union-invalid"})
    assert response.status_code == status, response.get_json()
    assert response.get_json()["code"] == code
    assert response.headers["X-Request-ID"] == "union-invalid"


@pytest.mark.parametrize("endpoint", ["run", "preview", "compare"])
def test_omitted_origin_never_selects_all(union_client, endpoint):
    client, _ = union_client
    request = payload()
    request.pop("origin_fiases")
    assert client.post(f"/api/clustering/{endpoint}", json=request).status_code == 400


@pytest.mark.parametrize("endpoint", ["run", "preview", "compare"])
@pytest.mark.parametrize("generation", ["source", "coordinates"])
def test_generation_race_never_publishes_success(union_client, monkeypatch, endpoint, generation):
    client, service = union_client
    evaluate = service.product_mode_catalog.evaluate
    changed = False
    def race(*args, **kwargs):
        nonlocal changed
        result = evaluate(*args, **kwargs)
        if not changed:
            path = service.source_path if generation == "source" else service.coordinate_cache_path
            with path.open("a", encoding="utf-8") as stream:
                stream.write("\n")
            changed = True
        return result
    monkeypatch.setattr(service.product_mode_catalog, "evaluate", race)
    response = client.post(f"/api/clustering/{endpoint}", json=payload())
    assert response.status_code == 409, response.get_json()
    assert response.get_json()["code"] == "STALE_DATA_SNAPSHOT"


def test_detail_uses_exact_membership_and_generation(union_client, monkeypatch):
    client, service = union_client
    run = client.post("/api/clustering/run", json=payload(mode="geo_cost")).get_json()
    detail = {**payload(mode="geo_cost"), "data_snapshot": run["data_snapshot"], "destination_fias": "y"}
    result = client.post("/api/clustering/point-rows", json=detail).get_json()
    assert result["rows"][0]["cluster_id"] is None
    assert result["rows"][0]["status"] == "economic_unavailable"
    outside = client.post("/api/clustering/point-rows", json={**detail, "detail_origin_fias": "c"})
    assert outside.status_code == 422
    assert outside.get_json()["code"] == "UNKNOWN_ORIGIN"
    missing = client.post("/api/clustering/point-rows", json={**detail, "destination_fias": "unknown"})
    assert missing.status_code == 422
    rows = service.repository.source_rows
    def race(**kwargs):
        result = rows(**kwargs)
        with service.source_path.open("a", encoding="utf-8") as stream:
            stream.write("\n")
        return result
    monkeypatch.setattr(service.repository, "source_rows", race)
    response = client.post("/api/clustering/point-rows", json=detail)
    assert response.status_code == 409
    assert response.get_json()["code"] == "STALE_DATA_SNAPSHOT"


def test_real_modes_share_pooled_full_graph_and_keep_bear_semantics(union_client, monkeypatch):
    client, service = union_client
    datasets = []
    graphs = []
    evaluate = service.product_mode_catalog.evaluate
    build = service.graph_builder.build
    def record_dataset(selection, dataset, operation):
        datasets.append(dataset)
        return evaluate(selection, dataset, operation)
    def record_graph(points):
        graph = build(points)
        graphs.append(graph)
        return graph
    monkeypatch.setattr(service.product_mode_catalog, "evaluate", record_dataset)
    monkeypatch.setattr(service.graph_builder, "build", record_graph)
    response = client.post("/api/clustering/compare", json=payload())
    assert response.status_code == 200, response.get_json()
    assert len(graphs) == 1
    assert len(datasets) == 5
    assert all(dataset.spatial_graph is graphs[0] for dataset in datasets)
    assert set(graphs[0].node_ids) == {"w", "x", "y", "z"}
    results = response.get_json()["results"]
    assert results["geo_cost"]["points"][1:]
    assert next(p for p in results["geo_cost"]["points"] if p["id"] == "y")["status"] == "economic_unavailable"
    assert results["bear_zones"]["status"] == "no_bears"
    assert results["bear_volume_zones"]["status"] == "success"
    assert results["bear_volume_zones"]["clusters"][0]["point_ids"] == ["x"]
    assert all(results[mode]["cluster_table"] == {"supported": False} for mode in ("bear_zones", "bear_volume_zones"))


@pytest.mark.parametrize("mode", ["geography", "geo_cost", "geo_volume", "bear_zones", "bear_volume_zones"])
def test_response_contains_reusable_normalized_frozen_request(union_client, mode):
    client, _ = union_client
    run_payload = payload(mode=mode, parameters={})
    result = client.post("/api/clustering/run", json=run_payload).get_json()
    frozen = result["analysis"]["frozen_request"]
    assert frozen["mode"] == mode
    assert frozen["origin_fiases"] == ["a", "b"]
    response = client.post("/api/clustering/point-rows", json={**frozen,
        "data_snapshot": result["data_snapshot"], "destination_fias": "x"})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["total"] == 3


def test_injected_records_union_uses_same_aggregation(union_client):
    client, service = union_client
    from ml.data.loader import iter_records
    injected = ClusteringService(service.source_path, coordinate_cache_path=service.coordinate_cache_path,
        records_factory=lambda: iter_records(service.source_path))
    set_clustering_service(injected)
    response = client.post("/api/clustering/run", json=payload())
    assert response.status_code == 200, response.get_json()
    assert next(p for p in response.get_json()["points"] if p["id"] == "x")["weighted_route_length"] == 250


def test_rich_detail_requires_frozen_mode_and_parameters(union_client):
    client, _ = union_client
    result = client.post("/api/clustering/run", json=payload(parameters={})).get_json()
    detail = {**payload(parameters={}), "data_snapshot": result["data_snapshot"], "destination_fias": "x"}
    for omitted in ("mode", "parameters"):
        request = dict(detail)
        request.pop(omitted)
        assert client.post("/api/clustering/point-rows", json=request).status_code == 400



def test_distinct_identical_source_rows_are_not_deduplicated(union_client):
    client, service = union_client
    with service.source_path.open("r", encoding="utf-8-sig", newline="") as stream:
        duplicate = list(csv.DictReader(stream))[0]
    with service.source_path.open("a", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerow(duplicate)
    run = client.post("/api/clustering/run", json=payload(origin_fiases=["a", "b", "a"])).get_json()
    x = next(p for p in run["points"] if p["id"] == "x")
    assert x["trip_count"] == 70
    detail = client.post("/api/clustering/point-rows", json={**run["analysis"]["frozen_request"],
        "data_snapshot": run["data_snapshot"], "destination_fias": "x"}).get_json()
    assert detail["total"] == 4
    assert len({r["source_row_id"] for r in detail["rows"]}) == 4


def test_union_cluster_table_reconstructs_metric_valid_weights(union_client):
    client, _ = union_client
    result = client.post("/api/clustering/run", json=payload()).get_json()
    rows = {tuple(row["point_ids"]): row for row in result["cluster_table"]["rows"]}
    wx = rows[("w", "x")]
    assert wx["trip_count"] == 65
    assert wx["weighted_route_length"] == pytest.approx(233.33333333333333)
    assert wx["price"]["weighted"] == pytest.approx(4333.333333333333)
    assert wx["rub_per_km"]["weighted"] == pytest.approx(16.666666666666667)
    assert wx["coverage"]["route_length"]["valid_trip_count"] == 45
    assert wx["coverage"]["route_length"]["total_trip_count"] == 65
    yz = rows[("y", "z")]
    assert yz["weighted_route_length"] == 150
    assert yz["price"]["weighted"] == 1000
    assert yz["coverage"]["price"]["valid_trip_count"] == 5
    assert yz["coverage"]["route_length"]["valid_trip_count"] == 10


@pytest.mark.parametrize("mode", ["geography", "geo_cost", "geo_volume"])
def test_union_metrics_keep_independent_denominators(union_client, mode):
    client, service = union_client
    with service.source_path.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    records[2]["units"] = "2000"  # Price-valid machines with no route or rate.
    with service.source_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    response = client.post("/api/clustering/run", json=payload(mode=mode))
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    x = next(point for point in result["points"] if point["id"] == "x")
    assert x["trip_count"] == 60
    assert x["weighted_route_length"] == 250  # 10000 / 40, not / 60.
    assert x["weighted_price"] == pytest.approx(3833.3333333333335)  # 230000 / 60.
    assert x["weighted_rub_per_km"] == 17.5  # 700 / 40, not price / mean route.
    assert (x["valid_route_length_trip_count"], x["valid_price_trip_count"],
            x["valid_rub_per_km_trip_count"]) == (40, 60, 40)
    y = next(point for point in result["points"] if point["id"] == "y")
    assert y["weighted_route_length"] == 200
    assert y["valid_route_length_trip_count"] == 5
    assert y["weighted_price"] is y["weighted_rub_per_km"] is None
    assert y["status"] == ("economic_unavailable" if mode == "geo_cost" else "normal")
    if mode == "geography":
        wx = next(row for row in result["cluster_table"]["rows"] if row["point_ids"] == ["w", "x"])
        assert wx["weighted_route_length"] == pytest.approx(233.33333333333333)
        assert wx["price"] == pytest.approx({"min": 1000, "median": 2416.666666666667,
                                            "weighted": 3615.3846153846152, "max": 3833.3333333333335})
        assert wx["rub_per_km"] == pytest.approx({"min": 10, "median": 13.75,
                                                 "weighted": 16.666666666666668, "max": 17.5})
        assert wx["coverage"]["route_length"] == {"valid_points": 2, "total_points": 2,
                                                   "valid_trip_count": 45, "total_trip_count": 65}
        assert wx["coverage"]["price"]["valid_trip_count"] == 65
        assert wx["coverage"]["rub_per_km"]["valid_trip_count"] == 45


@pytest.mark.parametrize("field,value", [
    ("route_length", ""), ("route_length", "0"), ("route_length", "-10"),
    ("route_length", "invalid"), ("route_length", "NaN"),
    ("bid_count", ""), ("bid_count", "0"), ("bid_count", "-2"), ("bid_count", "invalid"),
])
def test_union_unavailable_route_is_null_with_zero_valid_weight(union_client, field, value):
    client, service = union_client
    with service.source_path.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    for row in records:
        row[field] = value
    with service.source_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    response = client.post("/api/clustering/run", json=payload())
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert len(result["points"]) == 4
    assert all(point["weighted_route_length"] is None
               and point["valid_route_length_trip_count"] == 0 for point in result["points"])
    for row in result["cluster_table"]["rows"]:
        assert row["weighted_route_length"] is None
        assert row["coverage"]["route_length"]["valid_points"] == 0
        assert row["coverage"]["route_length"]["valid_trip_count"] == 0
        assert row["coverage"]["route_length"]["total_trip_count"] == row["trip_count"]
    assert all(point["weighted_rub_per_km"] is None for point in result["points"])


@pytest.mark.parametrize("origins,route,valid,total", [
    (["a"], 100, 10, 10), (["b"], 300, 30, 50), (["a", "b"], 250, 40, 60),
])
def test_scalar_and_union_route_constants(union_client, origins, route, valid, total):
    client, _ = union_client
    request = payload(origin_fiases=origins)
    result = client.post("/api/clustering/run", json=request).get_json()
    x = next(point for point in result["points"] if point["id"] == "x")
    assert (x["weighted_route_length"], x["valid_route_length_trip_count"], x["trip_count"]) == (route, valid, total)
    if len(origins) == 1:
        request.pop("origin_fiases")
        request["origin_fias"] = origins[0]
        assert client.post("/api/clustering/run", json=request).get_json() == result


def test_union_periods_and_segments_change_route_numerator_and_denominator(union_client):
    client, service = union_client
    extras = [
        _row("x", "X", origin="a", period="retro", price_type="tender", trips="5", route_length="500"),
        _row("x", "X", origin="b", period="forecast", trips="10", price="8000", route_length="400"),
        _row("x", "X", origin="a", vehicle="van", tonnage="10", trips="100", route_length="900"),
    ]
    with service.source_path.open("a", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerows(extras)
    cases = [
        ({}, 250, 40, 60, 233.33333333333333, False),
        ({"period_types": ["current", "forecast"]}, 280, 50, 70, 263.6363636363636, True),
        ({"period_types": ["current", "retro"], "price_types": ["spot", "tender"]},
         277.77777777777777, 45, 65, 260, False),
        ({"vehicle_types": [], "tonnage_ids": ["20", "10"]}, 714.2857142857143, 140, 160, 693.1034482758621, False),
    ]
    for changes, mean, valid, total, cluster_mean, forecast in cases:
        request = payload(**{"vehicle_types": ["tent"], "tonnage_ids": ["20"], **changes})
        response = client.post("/api/clustering/run", json=request)
        assert response.status_code == 200, response.get_json()
        result = response.get_json()
        x = next(point for point in result["points"] if point["id"] == "x")
        assert x["weighted_route_length"] == pytest.approx(mean)
        assert (x["valid_route_length_trip_count"], x["trip_count"]) == (valid, total)
        assert result["contains_forecast"] is forecast
        assert result["cluster_table"]["period_types"] == sorted(request["period_types"])
        assert result["cluster_table"]["methodology"]["weighted_values"] == "metric_valid_trip_count"
        wx = next(row for row in result["cluster_table"]["rows"] if row["point_ids"] == ["w", "x"])
        assert wx["weighted_route_length"] == pytest.approx(cluster_mean)
        assert wx["coverage"]["route_length"]["valid_trip_count"] == valid + 5
        assert wx["coverage"]["route_length"]["total_trip_count"] == total + 5


@pytest.mark.parametrize("query,code,status", [
    ("origin_fiases=&destination_region=Region+A", "INVALID_REQUEST", 400),
    ("origin_fias=a&origin_fiases=b", "INVALID_REQUEST", 400),
    ("all_origins=true", "INVALID_REQUEST", 400),
    ("origin_fiases=unknown", "UNKNOWN_ORIGIN", 422),
    ("origin_fiases=a&destination_region=unknown", "UNKNOWN_DESTINATION_REGION", 422),
])
def test_options_reject_invalid_selection(union_client, query, code, status):
    client, _ = union_client
    response = client.get("/api/clustering/options?" + query)
    assert response.status_code == status
    assert response.get_json()["code"] == code


def test_detail_restart_and_stale_snapshot_fail_without_reclustering(union_client, monkeypatch):
    client, service = union_client
    result = client.post("/api/clustering/run", json=payload()).get_json()
    detail = {**result["analysis"]["frozen_request"], "data_snapshot": result["data_snapshot"], "destination_fias": "x"}
    restarted = ClusteringService(service.source_path, coordinate_cache_path=service.coordinate_cache_path)
    def no_clustering(*args, **kwargs):
        raise AssertionError("Detail must never recluster")
    monkeypatch.setattr(restarted.product_mode_catalog, "evaluate", no_clustering)
    set_clustering_service(restarted)
    response = client.post("/api/clustering/point-rows", json=detail)
    assert response.status_code == 409
    assert response.get_json()["code"] == "RESULT_UNAVAILABLE"
    with service.coordinate_cache_path.open("a", encoding="utf-8") as stream:
        stream.write("\n")
    response = client.post("/api/clustering/point-rows", json=detail)
    assert response.status_code == 409
    assert response.get_json()["code"] == "STALE_DATA_SNAPSHOT"



def test_union_bear_cost_positive_and_volume_no_bears(union_client):
    client, service = union_client
    with service.source_path.open("r", encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    records[4]["units"] = "100000"
    for row in records[:3]:
        row["bid_count"] = "1"
    for row in records[3:6]:
        row["bid_count"] = "3"
    with service.source_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    for threshold in (0.2, 0.35, 0.5):
        cost = client.post("/api/clustering/run", json=payload(mode="bear_zones",
            parameters={"bear_threshold": threshold})).get_json()
        assert cost["status"] == "success"
        assert any(c["point_ids"] == ["z"] for c in cost["clusters"])
        volume = client.post("/api/clustering/run", json=payload(mode="bear_volume_zones",
            parameters={"volume_threshold": threshold})).get_json()
        assert volume["status"] == "no_bears"
        assert volume["clusters"] == []


def test_union_pagination_and_saved_filters_do_not_leak(union_client):
    client, service = union_client
    with service.source_path.open("r", encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    records += [_row("x", "X", origin="a" if i % 2 else "b", period_id="202609") for i in range(60)]
    records += [_row("x", "X", origin="a", vehicle="reefer", trips="999")]
    with service.source_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    result = client.post("/api/clustering/run", json=payload(vehicle_types=["tent"], tonnage_ids=["20"])).get_json()
    detail = {**result["analysis"]["frozen_request"], "data_snapshot": result["data_snapshot"], "destination_fias": "x"}
    page1 = client.post("/api/clustering/point-rows", json={**detail, "limit": 999}).get_json()
    page2 = client.post("/api/clustering/point-rows", json={**detail, "offset": 50}).get_json()
    assert page1["total"] == page2["total"] == 63
    assert page1["limit"] == 50 and page1["has_more"]
    assert len(page2["rows"]) == 13 and not page2["has_more"]
    assert len({r["source_row_id"] for r in page1["rows"] + page2["rows"]}) == 63
    assert all(r["period_id"] == "202609" for r in page1["rows"])
    assert all(r["vehicle_type"] == "tent" and r["origin_fias"] in {"a", "b"} for r in page1["rows"] + page2["rows"])
    changed = client.post("/api/clustering/point-rows", json={**detail, "vehicle_types": []})
    assert changed.status_code == 409
    assert changed.get_json()["code"] == "RESULT_UNAVAILABLE"



def test_origin_display_uses_exact_identity_not_search_suggestion(union_client):
    client, _ = union_client
    result = client.post("/api/clustering/run", json=payload()).get_json()
    assert [(o["fias_id"], o["name"]) for o in result["analysis"]["origins"]] == [
        ("a", "b Warehouse"), ("b", "Origin Town")]



@pytest.mark.parametrize("cached", [False, True])
def test_generation_change_during_result_copy_is_rejected(union_client, monkeypatch, cached):
    import backend.services.clustering_service as module
    client, service = union_client
    if cached:
        assert client.post("/api/clustering/run", json=payload()).status_code == 200
    deepcopy = module.copy.deepcopy
    changed = False
    def race(value, *args, **kwargs):
        nonlocal changed
        result = deepcopy(value, *args, **kwargs)
        if not changed and isinstance(value, dict) and "data_snapshot" in value:
            with service.source_path.open("a", encoding="utf-8") as stream:
                stream.write("\n")
            changed = True
        return result
    monkeypatch.setattr(module.copy, "deepcopy", race)
    response = client.post("/api/clustering/run", json=payload())
    assert response.status_code == 409, response.get_json()
    assert response.get_json()["code"] == "STALE_DATA_SNAPSHOT"
    assert not service._result_cache



def test_injected_options_preserves_scalar_and_union_regions(union_client):
    from ml.data.loader import iter_records
    client, service = union_client
    injected = ClusteringService(service.source_path, coordinate_cache_path=service.coordinate_cache_path,
        records_factory=lambda: iter_records(service.source_path))
    set_clustering_service(injected)
    for selector in ("origin_fias=a", "origin_fiases=a&origin_fiases=b"):
        result = client.get("/api/clustering/options?" + selector + "&destination_region=Region+A")
        assert result.status_code == 200
        assert result.get_json()["destination_regions"] == ["Region A"]
