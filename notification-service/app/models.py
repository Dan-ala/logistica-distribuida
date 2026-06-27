import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(String(50), nullable=False, index=True)
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
