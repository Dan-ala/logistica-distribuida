import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Route(Base):
    __tablename__ = "routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(String(50), nullable=False, index=True)
    distance = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    event_id = Column(String(100), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="COMPLETED")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
