from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_update_location_invalid_data():
    payload = {
        "vehicle_id": "",
        "latitude": 100,
        "longitude": 200,
        "timestamp": "invalid",
    }
    response = client.post("/locations/update", json=payload)
    assert response.status_code == 422


def test_update_location_missing_fields():
    payload = {
        "vehicle_id": "CAR-001",
    }
    response = client.post("/locations/update", json=payload)
    assert response.status_code == 422
