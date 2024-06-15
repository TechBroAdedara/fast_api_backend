# Pydantic models
from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class GeofenceCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius: float
    fenceType: str
    start_time: datetime
    end_time: datetime

