from datetime import datetime

from pydantic import BaseModel, EmailStr


class CreateUserRequest(BaseModel):
    email: EmailStr
    user_matric: str
    username: str
    password: str
    role: str

    class Config:
        from_attributes = True
