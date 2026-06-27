from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "outbox_pending" in data


def test_update_location_success():
    payload = {
        "vehicle_id": "TEST-001",
        "latitude": 4.7110,
        "longitude": -74.0721,
        "timestamp": datetime.now().isoformat(),
    }
    response = client.post(
        "/locations/update",
        json=payload,
        headers={"Idempotency-Key": "test-key-001"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["event_id"] is not None
    assert "processed" in data["message"]


def test_update_location_idempotent():
    payload = {
        "vehicle_id": "TEST-002",
        "latitude": 4.7110,
        "longitude": -74.0721,
        "timestamp": datetime.now().isoformat(),
    }
    response = client.post(
        "/locations/update",
        json=payload,
        headers={"Idempotency-Key": "test-key-idemp"},
    )
    assert response.status_code == 201

    response2 = client.post(
        "/locations/update",
        json=payload,
        headers={"Idempotency-Key": "test-key-idemp"},
    )
    assert response2.status_code in (200, 201)


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


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
