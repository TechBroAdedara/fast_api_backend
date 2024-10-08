# Pydantic models
from datetime import datetime

from pydantic import BaseModel, EmailStr


class GeofenceCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius: float
    fence_type: str
    start_time: datetime
    end_time: datetime

    class Config:
        from_attributes = True

class CreateUserRequest(BaseModel):
    email: EmailStr
    user_matric: str
    username: str
    password: str
    role: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    role: str | None = None
    user_matric: str | None = None
