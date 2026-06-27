import logging
import uuid
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import exists

from app.config import config
from app.database import get_db, init_db
from app.models import Location
from app.schemas import LocationUpdateRequest, LocationUpdateResponse
from app.publisher import EventPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(config.SERVICE_NAME)

app = FastAPI(title="Tracking Service", version="1.0.0")
publisher = EventPublisher()


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized")


@app.on_event("shutdown")
def on_shutdown():
    publisher.close()


@app.get("/health")
def health():
    return {"status": "ok", "service": config.SERVICE_NAME}


@app.post("/locations/update", response_model=LocationUpdateResponse, status_code=201)
def update_location(
    request: LocationUpdateRequest,
    db: Session = Depends(get_db),
):
    event_id = str(uuid.uuid4())

    idempotency_key = f"{request.vehicle_id}_{int(request.timestamp.timestamp())}"
    existing = db.query(exists().where(Location.event_id == idempotency_key)).scalar()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate event (idempotency key already exists)",
        )

    location = Location(
        vehicle_id=request.vehicle_id,
        latitude=request.latitude,
        longitude=request.longitude,
        recorded_at=request.timestamp,
        event_id=idempotency_key,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    logger.info("Saved location for vehicle %s", request.vehicle_id)

    event = {
        "event_id": event_id,
        "event_type": "LOCATION_UPDATED",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "vehicle_id": request.vehicle_id,
            "latitude": request.latitude,
            "longitude": request.longitude,
        },
    }

    published = publisher.publish(event)
    if not published:
        logger.error("Event publication failed for %s", event_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to publish event to message broker",
        )

    return LocationUpdateResponse(
        event_id=event_id,
        message=f"Location for {request.vehicle_id} processed",
    )
