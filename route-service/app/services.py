import logging
from sqlalchemy.orm import Session

from app.config import config
from app.models import Route

logger = logging.getLogger(config.SERVICE_NAME)

COST_PER_KM = 2000.0
BASE_LAT = 4.7110
BASE_LON = -74.0721


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def process_location_event(event_data: dict, db: Session) -> None:
    vehicle_id = event_data["vehicle_id"]
    latitude = event_data["latitude"]
    longitude = event_data["longitude"]

    distance = calculate_distance(BASE_LAT, BASE_LON, latitude, longitude)
    cost = round(distance * COST_PER_KM, 2)

    route = Route(
        vehicle_id=vehicle_id,
        distance=distance,
        cost=cost,
    )
    db.add(route)
    db.commit()
    logger.info("Route saved: vehicle=%s, distance=%.2f km, cost=%.2f", vehicle_id, distance, cost)
