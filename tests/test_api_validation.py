import pytest

import backend.app as app_module
import backend.ml_clustering as clustering_module
from backend.app import app


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_points_rejects_unknown_period(client):
    response = client.get("/api/points?period_types=unknown")

    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_ml_rejects_unknown_town_type(client):
    response = client.get("/api/ml-cluster?region=Москва&town_type=unknown")

    assert response.status_code == 400


def test_ml_rejects_unknown_weight_mode(client):
    response = client.get(
        "/api/ml-cluster?region=Москва&town_type=shipment&weight_mode=price"
    )

    assert response.status_code == 400


@pytest.mark.parametrize("value", ["invalid", "1", "11"])
def test_ml_rejects_invalid_k(client, value):
    response = client.get(
        f"/api/ml-cluster?region=Москва&town_type=shipment&k={value}"
    )

    assert response.status_code == 400


def test_regeocode_rejects_non_string_payload(client):
    response = client.post("/api/regeocode", json={"town": 123, "region": []})

    assert response.status_code == 400


def test_ml_does_not_mix_other_periods_into_filtered_bid_count(client, monkeypatch):
    captured_points = []
    towns = {
        "A::Test": {
            "town": "A",
            "region": "Test",
            "records": [
                {"period_type": "retro", "price_type": "spot", "price": 100, "route_length": 10, "bid_count": 5},
                {"period_type": "current", "price_type": "tender", "price": 100, "route_length": 10, "bid_count": 100},
            ],
        },
        "B::Test": {
            "town": "B",
            "region": "Test",
            "records": [
                {"period_type": "current", "price_type": "tender", "price": 200, "route_length": 20, "bid_count": 200},
            ],
        },
    }

    monkeypatch.setattr(
        app_module,
        "load_data",
        lambda: {"shipment_towns": towns, "delivery_towns": {}},
    )
    monkeypatch.setattr(app_module, "geocode_town", lambda *_args, **_kwargs: (55.0, 37.0))

    def fake_cluster(points, **_kwargs):
        captured_points.extend(points)
        return {"clusters": [{"total_bids": sum(p["bid_count"] for p in points)}], "k": 1}

    monkeypatch.setattr(clustering_module, "cluster_points", fake_cluster)

    response = client.get(
        "/api/ml-cluster?region=Test&town_type=shipment&period_types=retro&price_types=spot,tender"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["region_total_bids"] == 5
    assert payload["data_quality"] == {
        "total_points": 2,
        "used_points": 2,
        "excluded_no_coordinates": 0,
    }
    assert payload["clusters"][0]["total_bids"] == 5
    assert {point["town"]: point["bid_count"] for point in captured_points} == {"A": 5, "B": 0}
    assert {point["town"]: point["cluster_weight"] for point in captured_points} == {"A": 5, "B": 1}
