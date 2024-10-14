from datetime import datetime

from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    role: str | None = None
    user_matric: str | None = None
