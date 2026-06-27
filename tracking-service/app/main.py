import json
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import exists

from app.config import config
from app.database import get_db, init_db
from app.models import Location, IdempotencyKey, Outbox
from app.schemas import LocationUpdateRequest, LocationUpdateResponse, HealthResponse
from app.outbox import OutboxPoller
from app.compensation import CompensationConsumer
from app.metrics import metrics_endpoint
from shared.logging_config import setup_logging
from shared.event_config import (
    ROUTING_KEY_LOCATION_UPDATED,
    EVENT_TYPE_LOCATION_UPDATED,
)

logger = setup_logging(config.SERVICE_NAME)

app = FastAPI(title="Tracking Service", version="1.1.0")
outbox_poller = OutboxPoller()
compensation_consumer = CompensationConsumer()


@app.on_event("startup")
def on_startup():
    init_db()
    outbox_poller.start()
    compensation_consumer.start()
    logger.info("Service started", extra={"service": config.SERVICE_NAME})


@app.on_event("shutdown")
def on_shutdown():
    outbox_poller.stop()
    compensation_consumer.stop()
    logger.info("Service stopped")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    pending = outbox_poller.get_pending_count()
    return HealthResponse(
        status="ok",
        service=config.SERVICE_NAME,
        outbox_pending=pending,
    )


@app.get("/metrics")
def metrics():
    return metrics_endpoint()


@app.post("/locations/update", response_model=LocationUpdateResponse, status_code=201)
def update_location(
    request: LocationUpdateRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    idempotency_key = http_request.headers.get("Idempotency-Key") or str(uuid.uuid4())

    existing_key = db.query(IdempotencyKey).filter(
        IdempotencyKey.idempotency_key == idempotency_key
    ).first()
    if existing_key:
        return JSONResponse(
            status_code=200,
            content=LocationUpdateResponse(
                event_id=existing_key.response_body or idempotency_key,
                message="Duplicate request (idempotency key)",
            ).model_dump(),
        )

    location_event_id = f"{request.vehicle_id}_{int(request.timestamp.timestamp())}"
    existing = db.query(exists().where(Location.event_id == location_event_id)).scalar()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate event for this vehicle and timestamp",
        )

    event_id = str(uuid.uuid4())

    location = Location(
        vehicle_id=request.vehicle_id,
        latitude=request.latitude,
        longitude=request.longitude,
        recorded_at=request.timestamp,
        event_id=location_event_id,
        uuid_event_id=event_id,
        status="PENDING",
    )
    db.add(location)

    event_payload = {
        "event_id": event_id,
        "event_type": EVENT_TYPE_LOCATION_UPDATED,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "vehicle_id": request.vehicle_id,
            "latitude": request.latitude,
            "longitude": request.longitude,
        },
    }

    outbox_entry = Outbox(
        event_id=event_id,
        event_type=EVENT_TYPE_LOCATION_UPDATED,
        routing_key=ROUTING_KEY_LOCATION_UPDATED,
        body=json.dumps(event_payload, default=str),
        status="PENDING",
    )
    db.add(outbox_entry)

    idempotency_record = IdempotencyKey(
        idempotency_key=idempotency_key,
        response_status=201,
        response_body=event_id,
    )
    db.add(idempotency_record)

    db.commit()

    logger.info(
        "Location saved for vehicle %s (event_id=%s, idempotency_key=%s)",
        request.vehicle_id, event_id, idempotency_key,
    )

    return LocationUpdateResponse(
        event_id=event_id,
        message=f"Location for {request.vehicle_id} processed",
        status="PENDING",
    )
