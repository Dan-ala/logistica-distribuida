import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(String(50), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False)
    event_id = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
