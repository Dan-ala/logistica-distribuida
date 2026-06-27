from datetime import datetime

from pydantic import BaseModel, Field


class LocationUpdateRequest(BaseModel):
    vehicle_id: str = Field(..., description="Vehicle identifier")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timestamp: datetime


class LocationUpdateResponse(BaseModel):
    event_id: str
    message: str
