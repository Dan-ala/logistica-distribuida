from app.services import calculate_distance


def test_distance_zero():
    d = calculate_distance(4.7110, -74.0721, 4.7110, -74.0721)
    assert d == 0.0


def test_distance_bogota_to_medellin():
    d = calculate_distance(4.7110, -74.0721, 6.2476, -75.5658)
    assert 240 < d < 250


def test_cost_calculation():
    from app.services import COST_PER_KM
    distance = 15.0
    cost = distance * COST_PER_KM
    assert cost == 30000.0
