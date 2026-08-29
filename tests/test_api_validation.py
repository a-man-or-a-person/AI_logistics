import pytest

from backend.app import app


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_points_rejects_unknown_period(client):
    response = client.get("/api/points?period_types=unknown")

    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_records_reject_unknown_price_type(client):
    response = client.get(
        "/api/records?town=A&region=R&type=shipment&price_types=unknown"
    )

    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_regeocode_rejects_non_string_payload(client):
    response = client.post("/api/regeocode", json={"town": 123, "region": []})

    assert response.status_code == 400
