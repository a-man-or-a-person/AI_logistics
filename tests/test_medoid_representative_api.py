import csv
import json

import pytest
from test_clustering_product_api import _row

from backend.app import app
from backend.clustering_api import set_clustering_service
from backend.services.clustering_service import ClusteringService
from ml.data.loader import PULSE_COLUMNS


@pytest.fixture()
def medoid_client(tmp_path):
    source, cache = tmp_path / "pulse.csv", tmp_path / "coords.json"
    rows, coordinates = [], {}
    for i in range(12):
        name = "" if i == 0 else f"село Synthetic {i}"
        rows.append(_row(f"p{i}", name, origin="a", trips="500" if i == 0 else "10",
                         price="100000" if i == 1 else "1000", route_length="100"))
        coordinates[f"{name or '<missing>'}::Region A"] = [55 + (i // 4) * .04, 37 + (i % 4) * .04]
    rows.append(_row("unresolved", "деревня без координат", origin="a", trips="9999", price="20000"))
    with source.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=PULSE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    cache.write_text(json.dumps(coordinates), encoding="utf-8")
    set_clustering_service(ClusteringService(source, coordinate_cache_path=cache))
    app.config.update(TESTING=True)
    yield app.test_client(), source
    set_clustering_service(None)


def test_all_five_modes_keep_medoid_geometry_and_saved_membership(medoid_client):
    client, source = medoid_client
    request = {"origin_fiases":["a"], "destination_region":"Region A",
               "period_types":["current"], "price_types":["spot"]}
    response = client.post("/api/clustering/compare", json=request)
    assert response.status_code == 200, response.get_json()
    comparison = response.get_json()
    assert len(comparison["results"]) == 5
    for mode, result in comparison["results"].items():
        assert result["clusters"], mode
        points = {p["id"]:p for p in result["points"]}
        for cluster in result["clusters"]:
            rep = cluster["representative"]
            member = points[rep["point_id"]]
            assert rep["type"] == "medoid"
            assert rep["point_id"] == cluster["medoid_point_id"]
            assert rep["point_id"] in cluster["point_ids"]
            assert member["cluster_id"] == cluster["cluster_id"]
            assert rep["point_id"] != "unresolved"
            assert (rep["name"], rep["lat"], rep["lon"]) == (member["name"], member["lat"], member["lon"])
            detail = {**result["analysis"]["frozen_request"], "data_snapshot":result["data_snapshot"],
                      "destination_fias":rep["point_id"]}
            rows = client.post("/api/clustering/point-rows", json=detail)
            assert rows.status_code == 200, rows.get_json()
            assert {r["cluster_id"] for r in rows.get_json()["rows"]} == {cluster["cluster_id"]}
        assert result["cluster_table"]["supported"] == (mode in {"geography", "geo_cost", "geo_volume"})
    rep = comparison["results"]["bear_volume_zones"]["clusters"][0]["representative"]
    assert rep == {"type":"medoid", "point_id":"p0", "name":"<missing>", "lat":55, "lon":37}
    assert comparison["results"]["bear_zones"]["clusters"][0]["representative"]["point_id"] == "p1"
    assert client.post("/api/clustering/compare", json=request).get_json() == comparison
    saved = comparison["results"]["geography"]
    original = json.dumps(saved, sort_keys=True)
    with source.open("a", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=PULSE_COLUMNS).writerow(_row("new", "New", origin="a"))
    stale = client.post("/api/clustering/point-rows", json={**saved["analysis"]["frozen_request"],
                        "data_snapshot":saved["data_snapshot"], "destination_fias":saved["clusters"][0]["medoid_point_id"]})
    assert stale.status_code == 409
    assert stale.get_json()["code"] == "STALE_DATA_SNAPSHOT"
    assert json.dumps(saved, sort_keys=True) == original
