import logging

from sqlalchemy.orm import Session

from app.config import config
from app.models import Notification

logger = logging.getLogger(config.SERVICE_NAME)

POI_BOGOTA_LAT = 4.7110
POI_BOGOTA_LON = -74.0721
PROXIMITY_THRESHOLD = 0.02


def generate_notification(vehicle_id: str, latitude: float, longitude: float) -> str:
    lat_diff = abs(latitude - POI_BOGOTA_LAT)
    lon_diff = abs(longitude - POI_BOGOTA_LON)

    if lat_diff <= PROXIMITY_THRESHOLD and lon_diff <= PROXIMITY_THRESHOLD:
        return f"Vehículo {vehicle_id} llegó al punto de entrega en Bogotá"
    return f"Vehículo {vehicle_id} transitando en coordenadas ({latitude:.4f}, {longitude:.4f})"


def process_location_event(event_data: dict, db: Session) -> None:
    vehicle_id = event_data["vehicle_id"]
    latitude = event_data["latitude"]
    longitude = event_data["longitude"]

    message = generate_notification(vehicle_id, latitude, longitude)

    notification = Notification(
        vehicle_id=vehicle_id,
        message=message,
    )
    db.add(notification)
    db.commit()
    logger.info("Notification saved: %s", message)
