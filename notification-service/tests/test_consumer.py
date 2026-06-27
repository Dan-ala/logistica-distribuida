from app.services import generate_notification


def test_notification_arrival():
    msg = generate_notification("CAR-001", 4.7110, -74.0721)
    assert "llegó al punto de entrega" in msg


def test_notification_transit():
    msg = generate_notification("CAR-001", 4.6000, -74.0500)
    assert "transitando" in msg
